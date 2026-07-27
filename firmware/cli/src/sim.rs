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
use stillair_core::console::{self, ConfigOp, Reply, Request, Telemetry};
use stillair_core::matter;
use stillair_core::mcf8316::{reg, FaultStatus, RegisterBus};
use stillair_core::mcf_config;
use stillair_core::speed::{self, MilliRpm};
use stillair_core::state::{Command, Inputs, StatusRead, Supervisor};
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
        self.0.retain(|(known, _)| *known != address);
        self.0.push((address, value));
        Ok(())
    }
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
        let mut registers = Vec::new();
        // Run the real boot-time check against the (empty) simulated register file. It
        // reports `Unverified`, which is the truth: a simulator says nothing about what any
        // register on a real MCF8316D contains, and every frame it emits will say so.
        let inputs = Inputs {
            config: block_on(mcf_config::check(
                &mut SimBus(&mut registers),
                mcf_config::IMAGE,
            )),
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
            commanded: self.supervisor.commanded(),
            measured_fg: self.supervisor.measured(),
            measured_hall: self.supervisor.measured_hall(),
            duty: speed::duty_for(self.supervisor.commanded()),
            direction: self.supervisor.direction(),
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

        // The supervisor's own actions are applied by observing `commanded()` above; the
        // rest (arm pulses, permission) have no simulated hardware to reach.
        let _ = self.supervisor.poll(self.now, &self.inputs);

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
            ConfigOp::Check | ConfigOp::Apply => {
                let mut written = 0;
                let mut unchanged = 0;
                let check = if operation == ConfigOp::Apply {
                    let (applied, check) = block_on(mcf_config::apply(
                        &mut SimBus(&mut self.registers),
                        mcf_config::IMAGE,
                    ));
                    written = applied.written;
                    unchanged = applied.unchanged;
                    check
                } else {
                    block_on(mcf_config::check(
                        &mut SimBus(&mut self.registers),
                        mcf_config::IMAGE,
                    ))
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
            Request::Run(rpm) => {
                self.supervisor.command(Command::SetSpeed(rpm));
                self.emit(&Reply::Ok);
            }
            Request::Percent(percent) => {
                let released_min = self.supervisor.released_min();
                self.supervisor
                    .command(matter::command_for_percent(percent, released_min));
                self.emit(&Reply::Ok);
            }
            Request::Stop => {
                self.supervisor.command(Command::Off);
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
                // CLR_FLT is write-only and self-clearing on real silicon, so the model
                // does not store it — otherwise a read-back would show a bit the device
                // never holds.
                if address == reg::ALGO_CTRL1 {
                    self.emit(&Reply::Ok);
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
            Request::Config(operation) => self.config(operation),
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

    #[test]
    fn the_simulator_boots_into_idle_after_the_hold() {
        let mut sim = Simulator::new();
        let frame = run_until(&mut sim, 30_000, |line| {
            field(line, "state") == Some("idle_off")
        });
        assert!(frame.is_some(), "never reached idle_off");
        // And it took at least the documented hold to get there.
        assert!(sim.now.0 >= config::SAFE_BOOT_HOLD_MS);
    }

    #[test]
    fn a_run_command_reaches_the_commanded_speed() {
        let mut sim = Simulator::new();
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
        let mut sim = Simulator::new();
        sim.send("frobnicate").unwrap();
        let reply = sim.receive(Duration::from_millis(10)).unwrap().unwrap();
        assert_eq!(field(&reply, "ok"), Some("false"));
        assert_eq!(field(&reply, "error"), Some("unknown command"));
    }

    #[test]
    fn registers_round_trip_by_name() {
        let mut sim = Simulator::new();
        sim.send("reg write ISD_CONFIG 0x12345678").unwrap();
        sim.receive(Duration::from_millis(10)).unwrap();
        sim.send("reg read ISD_CONFIG").unwrap();
        let reply = sim.receive(Duration::from_millis(10)).unwrap().unwrap();
        assert_eq!(field(&reply, "value"), Some("305419896"));
        assert_eq!(field(&reply, "name"), Some("ISD_CONFIG"));
    }

    #[test]
    fn the_simulator_enforces_the_same_speed_ceiling_as_the_firmware() {
        // It runs the real Supervisor, so the limits are not re-implemented here and
        // cannot drift from the ones under test.
        let mut sim = Simulator::new();
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
        let mut sim = Simulator::new();
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
        let mut sim = Simulator::new();
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
