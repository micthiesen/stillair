//! A simulated supervisor, speaking the same console protocol as a real board.
//!
//! **What this is for and what it is not for.** It runs the *actual* `Supervisor` from
//! `stillair-core` against a toy motor, so it exercises the harness end to end — the
//! protocol, the CLI, the CSV output, the pass/fail logic — with no hardware. It says
//! nothing whatsoever about sensorless startup, acoustics, or whether any register value is
//! right. Treat a green run here as "the test script works", never as "the fan works".
//!
//! Time is simulated and runs as fast as the CPU allows, so a ten-second safe-boot hold or
//! a hundred-start sweep costs milliseconds. Every timestamp reported is simulated.

use std::collections::VecDeque;
use std::future::Future;
use std::io;
use std::pin::pin;
use std::task::{Context, Poll, Waker};
use std::time::Duration;

use stillair_core::config;
use stillair_core::console::{self, ConfigOp, MpetOp, Reply, Request, Telemetry, WifiDiagnostics};
use stillair_core::matter;
use stillair_core::mcf8316::{reg, FaultStatus, MpetReport, RegisterBus};
use stillair_core::mcf_config;
use stillair_core::speed::{self, MilliRpm};
use stillair_core::state::{Action, Command, FanState, Inputs, StatusRead, Supervisor};
use stillair_core::time::Millis;

use crate::link::Link;

/// Drive a future that cannot actually await anything.
///
/// [`SimBus`] answers from a `Vec` and never yields, so one poll always resolves. This exists
/// so the simulator runs the *real* `mcf_config` code rather than a second implementation of
/// it that could agree with the tests while disagreeing with the firmware.
fn block_on<F: Future>(future: F) -> F::Output {
    let mut future = pin!(future);
    match future
        .as_mut()
        .poll(&mut Context::from_waker(Waker::noop()))
    {
        Poll::Ready(value) => value,
        Poll::Pending => panic!("the simulated register file must never pend"),
    }
}

/// The simulator's register file, behind the same trait the I²C driver implements.
struct SimBus<'a>(&'a mut Vec<(u16, u32)>);

impl RegisterBus for SimBus<'_> {
    type Error = core::convert::Infallible;

    async fn read(&mut self, address: u16) -> Result<u32, Self::Error> {
        Ok(self
            .0
            .iter()
            .find(|(known, _)| *known == address)
            .map(|(_, value)| *value)
            .unwrap_or(0))
    }

    async fn write(&mut self, address: u16, value: u32) -> Result<(), Self::Error> {
        // ALGO_CTRL1 commands are write-only and self-clearing on silicon. Keeping them in
        // the register file would make the real completion polling fail only in simulation.
        if address == reg::ALGO_CTRL1 {
            self.0.retain(|(known, _)| *known != address);
            return Ok(());
        }
        self.0.retain(|(known, _)| *known != address);
        self.0.push((address, value));
        Ok(())
    }

    async fn delay_ms(&mut self, _milliseconds: u32) {}
}

/// Control-loop period, matching the firmware's.
const TICK_MS: u64 = 50;

/// First-order lag between commanded and actual rotor speed, standing in for rotor inertia.
/// A real 44-inch rotor is far slower to respond than this; the number exists so the model
/// is not instantaneous, not because it is calibrated.
const ROTOR_LAG_MS: u64 = 800;

pub struct Simulator {
    supervisor: Supervisor,
    now: Millis,
    inputs: Inputs,
    /// Actual rotor speed, lagging the command.
    rotor: MilliRpm,
    fg_residual: u64,
    hall_residual: u64,
    /// Register file. Reads and writes land here; nothing interprets them.
    registers: Vec<(u16, u32)>,
    mpet_started_at: Option<Millis>,
    stream_period_ms: Option<u64>,
    next_stream_at: Millis,
    outbox: VecDeque<String>,
}

impl Default for Simulator {
    fn default() -> Self {
        Self::new()
    }
}

impl Simulator {
    pub fn new() -> Self {
        let now = Millis::ZERO;
        let registers = Vec::new();
        // The empty simulated register file represents unknown factory state, not a known
        // mismatch against the captured golden image. Start `Unverified`; an explicit check
        // can classify its zeroes as a mismatch, and an explicit stage can make it Provisional.
        let inputs = Inputs {
            config: mcf_config::ConfigCheck::Unverified,
            ..Inputs::default()
        };
        Self {
            supervisor: Supervisor::new(now, &inputs),
            now,
            inputs,
            rotor: MilliRpm::ZERO,
            fg_residual: 0,
            hall_residual: 0,
            registers,
            mpet_started_at: None,
            stream_period_ms: None,
            next_stream_at: Millis::ZERO,
            outbox: VecDeque::new(),
        }
    }

    fn telemetry(&self) -> Telemetry {
        Telemetry {
            uptime_ms: self.now.0,
            state: self.supervisor.state(),
            fault: self.supervisor.fault(),
            on: self.supervisor.commanded_on(),
            target: self.supervisor.target(),
            commanded: self.supervisor.commanded(),
            measured_fg: self.supervisor.measured(),
            measured_hall: self.supervisor.measured_hall(),
            duty: speed::duty_for(self.supervisor.commanded()),
            direction: self.supervisor.direction(),
            requested_direction: self.supervisor.requested_direction(),
            released_min: self.supervisor.released_min(),
            config: self.supervisor.config(),
            // Nothing can be dropped: the simulator hands lines straight to the caller.
            dropped: 0,
        }
    }

    /// Advance one control tick of simulated time.
    fn tick(&mut self) {
        self.now = self.now.plus_ms(TICK_MS);

        // Rotor chases the command with a first-order lag.
        let target = self.supervisor.commanded();
        let delta = i64::from(target.0) - i64::from(self.rotor.0);
        let step = delta * TICK_MS as i64 / ROTOR_LAG_MS as i64;
        let step = if step == 0 { delta.signum() } else { step };
        self.rotor = MilliRpm((i64::from(self.rotor.0) + step).max(0) as u32);

        // Tach edges for however far it turned.
        let travel = u64::from(self.rotor.0) * TICK_MS;
        const SCALE: u64 = 60_000 * 1_000;
        self.fg_residual += travel * u64::from(config::FG_PULSES_PER_REV);
        self.inputs.fg_pulses = self
            .inputs
            .fg_pulses
            .wrapping_add((self.fg_residual / SCALE) as u32);
        self.fg_residual %= SCALE;
        self.hall_residual += travel * u64::from(config::HALL_PULSES_PER_REV);
        self.inputs.hall_pulses = self
            .inputs
            .hall_pulses
            .wrapping_add((self.hall_residual / SCALE) as u32);
        self.hall_residual %= SCALE;

        // A healthy simulated I2C reader, on the same cadence the firmware uses.
        self.inputs.mcf_status = if self.now.0.is_multiple_of(config::STATUS_POLL_MS) {
            StatusRead::Fresh(FaultStatus::default())
        } else {
            StatusRead::Stale
        };

        // Observe service actions even though ordinary arm/pin actions have no simulated
        // hardware to reach. This keeps MPET scripts honest about admission and abort flow.
        for action in self.supervisor.poll(self.now, &self.inputs) {
            match action {
                Action::StartMpet => self.mpet_started_at = Some(self.now),
                Action::AbortMpet => self.mpet_started_at = None,
                _ => {}
            }
        }

        if let Some(period) = self.stream_period_ms {
            if self.now >= self.next_stream_at {
                self.next_stream_at = self.now.plus_ms(period);
                self.emit(&Reply::Telemetry(self.telemetry()));
            }
        }
    }

    fn emit(&mut self, reply: &Reply<'_>) {
        // Strip the prefix: `Link::receive` returns bodies, and the simulator stands in for
        // the link rather than for the wire.
        let line = reply.to_line();
        self.outbox
            .push_back(line.trim_start_matches(console::PREFIX).to_string());
    }

    fn register(&self, address: u16) -> u32 {
        self.registers
            .iter()
            .find(|(known, _)| *known == address)
            .map(|(_, value)| *value)
            .unwrap_or(0)
    }

    fn stopped_for_write(&self) -> bool {
        matches!(
            self.supervisor.state(),
            FanState::IdleOff | FanState::SafeBoot | FanState::Fault
        )
    }

    fn operation_ready(&self) -> bool {
        self.inputs.config.permits_operation()
    }

    fn refuse_unconfigured_command(&mut self, command: Command) -> bool {
        if !command.starts_drive() || self.operation_ready() {
            return false;
        }
        self.emit(&Reply::Error(
            "stage or verify the MCF configuration before running",
        ));
        true
    }

    /// Configuration operations, run through the real `mcf_config` code against the
    /// simulated register file.
    fn config(&mut self, operation: ConfigOp) {
        match operation {
            ConfigOp::Dump => {
                for (_, address) in reg::configuration() {
                    let value = self.register(address);
                    self.emit(&Reply::Register { address, value });
                }
                self.emit(&Reply::Ok);
            }
            ConfigOp::Check | ConfigOp::Stage | ConfigOp::Apply => {
                let mut written = 0;
                let mut unchanged = 0;
                let check = match operation {
                    ConfigOp::Apply => {
                        let (applied, check) = block_on(mcf_config::apply(
                            &mut SimBus(&mut self.registers),
                            mcf_config::IMAGE,
                        ));
                        written = applied.written;
                        unchanged = applied.unchanged;
                        check
                    }
                    ConfigOp::Stage => {
                        let (applied, check) =
                            block_on(mcf_config::stage(&mut SimBus(&mut self.registers)));
                        written = applied.written;
                        unchanged = applied.unchanged;
                        check
                    }
                    ConfigOp::Check => {
                        if self.inputs.config == mcf_config::ConfigCheck::Provisional {
                            block_on(mcf_config::check_provisional(&mut SimBus(
                                &mut self.registers,
                            )))
                        } else {
                            block_on(mcf_config::check(
                                &mut SimBus(&mut self.registers),
                                mcf_config::IMAGE,
                            ))
                        }
                    }
                    ConfigOp::Dump => unreachable!(),
                };
                self.inputs.config = check;
                self.emit(&Reply::Config {
                    check,
                    written,
                    unchanged,
                });
            }
        }
    }

    fn dispatch(&mut self, request: Request) {
        match request {
            Request::State => {
                let telemetry = self.telemetry();
                self.emit(&Reply::Telemetry(telemetry));
            }
            Request::Wifi => self.emit(&Reply::Wifi(WifiDiagnostics {
                connected: false,
                rssi_dbm: None,
                weakest_rssi_dbm: None,
                samples: 0,
                sample_failures: 0,
                disconnects: 0,
                last_ok_ms: None,
            })),
            Request::Run(rpm) => {
                let command = Command::SetSpeed(rpm);
                if self.refuse_unconfigured_command(command) {
                    return;
                }
                self.supervisor.command(command);
                self.emit(&Reply::Ok);
            }
            Request::Percent(percent) => {
                let released_min = self.supervisor.released_min();
                let command = matter::command_for_percent(percent, released_min);
                if self.refuse_unconfigured_command(command) {
                    return;
                }
                self.supervisor.command(command);
                self.emit(&Reply::Ok);
            }
            Request::Stop => {
                self.supervisor.command(Command::Off);
                self.emit(&Reply::Ok);
            }
            Request::Disarm => {
                self.supervisor.command(Command::Disarm);
                self.emit(&Reply::Ok);
            }
            Request::SetDirection(direction) => {
                self.supervisor.command(Command::SetDirection(direction));
                self.emit(&Reply::Ok);
            }
            Request::ClearFault => {
                self.supervisor.command(Command::Off);
                self.emit(&Reply::Ok);
            }
            Request::Stream(rate) => {
                self.stream_period_ms = rate.map(|hz| (1_000 / u64::from(hz)).max(TICK_MS));
                self.next_stream_at = self.now;
                self.emit(&Reply::Ok);
            }
            Request::RegRead(address) => {
                let value = self.register(address);
                self.emit(&Reply::Register { address, value });
            }
            Request::RegWrite { address, value } => {
                if !stillair_core::mcf8316::is_configuration(address) {
                    self.emit(&Reply::Error(
                        "raw writes are limited to the volatile configuration shadow",
                    ));
                    return;
                }
                if !self.stopped_for_write() {
                    self.emit(&Reply::Error("registers are writable only while stopped"));
                    return;
                }
                // The same core call the firmware makes, so a configuration write
                // invalidates the verdict here exactly as it does on a board (CTL-10).
                if let Ok(Some(check)) = block_on(mcf_config::write_and_recheck(
                    &mut SimBus(&mut self.registers),
                    address,
                    value,
                    mcf_config::IMAGE,
                )) {
                    self.inputs.config = check;
                }
                self.emit(&Reply::Ok);
            }
            Request::Config(ConfigOp::Stage | ConfigOp::Apply) if !self.stopped_for_write() => self
                .emit(&Reply::Error(
                    "configuration registers are writable only while stopped",
                )),
            Request::Config(operation) => self.config(operation),
            Request::Mpet(operation) => match operation {
                MpetOp::Start | MpetOp::Electrical => {
                    let command = Command::StartMpet;
                    if self.refuse_unconfigured_command(command) {
                        return;
                    }
                    self.supervisor.command(command);
                    self.emit(&Reply::Ok);
                }
                MpetOp::Abort => {
                    self.supervisor.command(Command::AbortMpet);
                    self.mpet_started_at = None;
                    self.emit(&Reply::Ok);
                }
                MpetOp::Status => {
                    let complete = self
                        .mpet_started_at
                        .is_some_and(|started| self.now.since(started) >= 500);
                    self.emit(&Reply::Mpet(MpetReport {
                        status: if complete {
                            stillair_core::mcf8316::MPET_COMPLETE_MASK
                        } else {
                            0
                        },
                        motor_params: 0x1122_3300,
                        current_pi: 0x4455_6600,
                        speed_pi: 0x7788_9900,
                    }))
                }
            },
            Request::Help => {
                for line in console::HELP {
                    eprintln!("{line}");
                }
                self.emit(&Reply::Ok);
            }
        }
    }
}

impl Link for Simulator {
    fn send(&mut self, line: &str) -> io::Result<()> {
        match console::parse(line) {
            Ok(request) => self.dispatch(request),
            Err(error) => {
                let message = error.as_str();
                self.emit(&Reply::Error(message));
            }
        }
        Ok(())
    }

    fn receive(&mut self, timeout: Duration) -> io::Result<Option<String>> {
        if let Some(line) = self.outbox.pop_front() {
            return Ok(Some(line));
        }
        // "Timeout" is a budget of simulated time, spent as fast as the CPU allows.
        let budget_ms = timeout.as_millis() as u64;
        let deadline = self.now.plus_ms(budget_ms);
        while self.now < deadline {
            self.tick();
            if let Some(line) = self.outbox.pop_front() {
                return Ok(Some(line));
            }
        }
        Ok(None)
    }

    fn describe(&self) -> String {
        "simulator".to_string()
    }

    fn elapsed(&self) -> Duration {
        Duration::from_millis(self.now.0)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::link::field;

    /// Drive the simulator until `predicate` holds for a telemetry frame, or give up.
    fn run_until(
        sim: &mut Simulator,
        budget_ms: u64,
        predicate: impl Fn(&str) -> bool,
    ) -> Option<String> {
        sim.send("stream on 20").unwrap();
        let _ = sim.receive(Duration::from_millis(10)).unwrap();
        let deadline = sim.now.plus_ms(budget_ms);
        while sim.now < deadline {
            if let Some(line) = sim.receive(Duration::from_millis(1_000)).unwrap() {
                if predicate(&line) {
                    return Some(line);
                }
            }
        }
        None
    }

    fn staged_simulator() -> Simulator {
        let mut sim = Simulator::new();
        sim.send("config stage").unwrap();
        let reply = sim.receive(Duration::from_millis(10)).unwrap().unwrap();
        assert_eq!(field(&reply, "ok"), Some("true"));
        assert_eq!(field(&reply, "config"), Some("provisional"));
        sim
    }

    #[test]
    fn an_unconfigured_simulator_stays_in_safe_boot() {
        let mut sim = Simulator::new();
        for command in ["run 35", "pct 50", "mpet start"] {
            sim.send(command).unwrap();
            let reply = sim.receive(Duration::from_millis(10)).unwrap().unwrap();
            assert_eq!(field(&reply, "ok"), Some("false"), "{command}");
        }
        let frame = run_until(&mut sim, 30_000, |line| {
            field(line, "state") == Some("idle_off")
        });
        assert!(frame.is_none(), "factory configuration was allowed to run");
        assert_eq!(sim.supervisor.state(), FanState::SafeBoot);
        assert_eq!(sim.supervisor.config(), mcf_config::ConfigCheck::Unverified);
    }

    #[test]
    fn staging_allows_idle_only_after_the_safe_boot_hold() {
        let mut sim = staged_simulator();
        let frame = run_until(&mut sim, 30_000, |line| {
            field(line, "state") == Some("idle_off")
        });
        assert!(frame.is_some(), "never reached idle_off");
        assert!(sim.now.0 >= config::SAFE_BOOT_HOLD_MS);
    }

    #[test]
    fn checking_a_staged_image_preserves_the_provisional_verdict() {
        let mut sim = staged_simulator();
        sim.send("config check").unwrap();
        let reply = sim.receive(Duration::from_millis(10)).unwrap().unwrap();
        assert_eq!(field(&reply, "ok"), Some("true"));
        assert_eq!(field(&reply, "config"), Some("provisional"));
    }

    #[test]
    fn a_run_command_reaches_the_commanded_speed() {
        let mut sim = staged_simulator();
        run_until(&mut sim, 30_000, |line| {
            field(line, "state") == Some("idle_off")
        })
        .expect("idle");
        sim.send("run 60").unwrap();
        let frame = run_until(&mut sim, 300_000, |line| {
            field(line, "cmd_mrpm") == Some("60000")
        });
        assert!(frame.is_some(), "never reached 60 RPM");
        assert_eq!(field(frame.as_ref().unwrap(), "state"), Some("running"));
    }

    #[test]
    fn a_bad_command_is_rejected_rather_than_ignored() {
        let mut sim = staged_simulator();
        sim.send("frobnicate").unwrap();
        let reply = sim.receive(Duration::from_millis(10)).unwrap().unwrap();
        assert_eq!(field(&reply, "ok"), Some("false"));
        assert_eq!(field(&reply, "error"), Some("unknown command"));
    }

    #[test]
    fn registers_round_trip_by_name() {
        let mut sim = staged_simulator();
        sim.send("reg write ISD_CONFIG 0x12345678").unwrap();
        sim.receive(Duration::from_millis(10)).unwrap();
        sim.send("reg read ISD_CONFIG").unwrap();
        let reply = sim.receive(Duration::from_millis(10)).unwrap().unwrap();
        assert_eq!(field(&reply, "value"), Some("305419896"));
        assert_eq!(field(&reply, "name"), Some("ISD_CONFIG"));
    }

    #[test]
    fn writes_are_refused_while_the_simulated_fan_is_running() {
        let mut sim = staged_simulator();
        run_until(&mut sim, 30_000, |line| {
            field(line, "state") == Some("idle_off")
        })
        .expect("idle");
        sim.send("run 60").unwrap();
        run_until(&mut sim, 300_000, |line| {
            field(line, "state") == Some("running")
        })
        .expect("running");

        sim.send("reg write ISD_CONFIG 0x12345678").unwrap();
        let raw = sim.receive(Duration::from_millis(10)).unwrap().unwrap();
        assert_eq!(field(&raw, "ok"), Some("false"));
        sim.send("config apply").unwrap();
        let apply = sim.receive(Duration::from_millis(10)).unwrap().unwrap();
        assert_eq!(field(&apply, "ok"), Some("false"));
    }

    #[test]
    fn raw_control_writes_are_refused_even_while_stopped() {
        let mut sim = staged_simulator();
        sim.send("reg write ALGO_CTRL1 0x8A500000").unwrap();
        let reply = sim.receive(Duration::from_millis(10)).unwrap().unwrap();
        assert_eq!(field(&reply, "ok"), Some("false"));
        assert_eq!(sim.inputs.config, mcf_config::ConfigCheck::Provisional);
    }

    #[test]
    fn the_simulator_enforces_the_same_speed_ceiling_as_the_firmware() {
        // It runs the real Supervisor, so the limits are not re-implemented here and
        // cannot drift from the ones under test.
        let mut sim = staged_simulator();
        run_until(&mut sim, 30_000, |line| {
            field(line, "state") == Some("idle_off")
        })
        .expect("idle");
        sim.send("run 500").unwrap();
        let ceiling = (config::RPM_USER_MAX * 1_000).to_string();
        let frame = run_until(&mut sim, 600_000, |line| {
            field(line, "cmd_mrpm") == Some(ceiling.as_str())
        });
        assert!(frame.is_some(), "never settled at the user maximum");
    }

    #[test]
    fn a_direction_change_goes_through_reversing() {
        let mut sim = staged_simulator();
        run_until(&mut sim, 30_000, |line| {
            field(line, "state") == Some("idle_off")
        })
        .expect("idle");
        sim.send("run 40").unwrap();
        run_until(&mut sim, 300_000, |line| {
            field(line, "state") == Some("running")
        })
        .expect("running");
        sim.send("dir rev").unwrap();
        assert!(
            run_until(&mut sim, 60_000, |line| field(line, "state")
                == Some("reversing"))
            .is_some(),
            "never entered reversing"
        );
        assert!(
            run_until(&mut sim, 300_000, |line| field(line, "dir") == Some("rev")).is_some(),
            "never applied the new direction"
        );
    }

    #[test]
    fn state_is_the_same_shape_whether_streamed_or_asked_for() {
        let mut sim = Simulator::new();
        sim.send("state").unwrap();
        let asked = sim.receive(Duration::from_millis(10)).unwrap().unwrap();
        assert_eq!(field(&asked, "type"), Some("telemetry"));
        for key in [
            "t",
            "state",
            "fault",
            "cmd_mrpm",
            "fg_mrpm",
            "hall_mrpm",
            "duty",
            "dir",
        ] {
            assert!(field(&asked, key).is_some(), "missing {key}");
        }
    }

    #[test]
    fn state_derives_from_the_real_supervisor_not_a_reimplementation() {
        // Guards against the simulator drifting into its own state machine: the frame must
        // agree with what the embedded Supervisor reports directly.
        let mut sim = staged_simulator();
        run_until(&mut sim, 30_000, |line| {
            field(line, "state") == Some("idle_off")
        })
        .expect("idle");
        sim.send("state").unwrap();
        let frame = sim.receive(Duration::from_millis(10)).unwrap().unwrap();
        assert_eq!(
            field(&frame, "state"),
            Some(console::state_name(sim.supervisor.state()))
        );
        assert_eq!(
            field(&frame, "cmd_mrpm"),
            Some(sim.supervisor.commanded().0.to_string().as_str())
        );
    }
}
