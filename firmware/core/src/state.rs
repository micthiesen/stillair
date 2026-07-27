//! The fan supervisor state machine.
//!
//! Sans-I/O by construction: [`Supervisor::poll`] takes the current time and a snapshot of
//! the input pins, and returns the [`Action`]s the caller should apply. It never sleeps,
//! never touches a peripheral, and never reads a clock of its own, so every clause of
//! `docs/controls.md` > "Required state behavior" and "Failure behavior" is exercisable in
//! a unit test — including the ten-second holds, which cost a test nothing.
//!
//! Two invariants are structural rather than incidental, and must survive any refactor:
//! firmware never drives DRVOFF (it can only *request* permission with [`Action::ArmPulse`]
//! and *revoke* it with [`Action::ClearPermission`]), and every permission-clearing event
//! routes back through [`FanState::SafeBoot`] so the TI ten-second hold is paid again.

use heapless::Vec;

use crate::config;
use crate::speed::{self, MilliRpm, Ramp, SpeedDuty};
use crate::tach::Tach;
use crate::time::Millis;

/// Rotation direction. Changes only while verified stopped.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Direction {
    Forward,
    Reverse,
}

/// Top-level supervisor states, one per contract clause.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FanState {
    /// Hold DRVOFF high for at least `config::SAFE_BOOT_HOLD_SECS` while rails,
    /// watchdog, limits, and stored MCF configuration are verified.
    SafeBoot,
    /// Output disabled, speed command zero.
    IdleOff,
    /// Direction set while stopped, permission armed, DRVOFF released, slow ramp.
    Starting,
    /// Maintain the last local speed even if the Matter controller/Wi-Fi disappears.
    Running,
    /// Ramp to zero and coast (never brake into the supply).
    Stopping,
    /// Ramp to zero, verify near-zero FG, coast, flip DIR, then restart.
    Reversing,
    /// Hi-Z, permission cleared where applicable, diagnostics exposed; a fresh
    /// user command is required to leave.
    Fault,
}

/// Why the supervisor faulted. Reported, never acted on differently — every fault has the
/// same response (permission revoked, speed zero, fresh command required).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FaultReason {
    /// nFAULT asserted: MCF lock, overcurrent, blocked rotor, overtemperature.
    McfFault,
    /// ALARM asserted: a report-only MCF condition, treated as a stop regardless.
    McfAlarm,
    /// 3.3 V PGOOD dropped while running.
    RailLoss,
    /// FG says the rotor is turning while the Hall channel is silent — the Hall pickup,
    /// magnet, or cable has failed and the analog overspeed chain is blind.
    HallImplausible,
    /// Commanded a start but the rotor never moved: permission never took, the rotor is
    /// jammed, or the analog safety lock is latched (which only a power cycle clears).
    NoRotation,
    /// The rotor would not go quiet, so the start could never be armed.
    NeverStopped,
}

/// Commands arriving from the Matter controller (or local control).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Command {
    Off,
    /// FanMode On without a percent write: resume the last non-zero setting.
    On,
    /// Target speed in mechanical RPM, clamped to the released user range.
    /// Matter PercentSetting 1–100 maps linearly onto [released minimum, 170].
    SetSpeed(MilliRpm),
    SetDirection(Direction),
}

/// What the supervisor wants the caller to do. The caller applies these in order.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Action {
    /// Request drive permission: a software-sequenced pulse on ARM_PULSE (idle low, high
    /// for at least 10 µs, back low). Never peripheral-driven — after a WDO pulse ends, a
    /// stray rising edge would re-arm the latch.
    ArmPulse,
    /// Revoke drive permission by pulling the open-drain MCU_CLEAR_N low.
    ClearPermission,
    /// Set the SPEED-pin PWM duty.
    SetSpeedDuty(SpeedDuty),
    /// Set the DIR pin. Only ever emitted while verified stopped.
    SetDirection(Direction),
    /// Issue CLR_FLT over I²C. Only ever emitted in response to a fresh user command.
    ClearMcfFault,
}

/// Room for the largest single-poll burst (direction + duty + arm, plus slack).
const MAX_ACTIONS: usize = 6;

/// Actions emitted by one [`Supervisor::poll`].
pub type Actions = Vec<Action, MAX_ACTIONS>;

/// A snapshot of the supervisor's input pins, sampled by the caller.
///
/// The tach fields are free-running cumulative edge counters and are allowed to wrap; the
/// supervisor corrects for that. WDO is deliberately absent: the watchdog acts on the
/// hardware permission latch directly, so it is a diagnostic, not a control input.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Inputs {
    /// 3.3 V PGOOD, active high.
    pub pgood: bool,
    /// nFAULT asserted, normalised to active-high by the caller.
    pub mcf_fault: bool,
    /// ALARM asserted, active high.
    pub mcf_alarm: bool,
    pub fg_pulses: u32,
    pub hall_pulses: u32,
}

impl Default for Inputs {
    /// A healthy, stationary board.
    fn default() -> Self {
        Self {
            pgood: true,
            mcf_fault: false,
            mcf_alarm: false,
            fg_pulses: 0,
            hall_pulses: 0,
        }
    }
}

/// What the user has asked for, independent of what the fan is currently doing.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct Desired {
    on: bool,
    /// Last non-zero speed setting, resumed by a bare `On`.
    speed: MilliRpm,
    direction: Direction,
}

pub struct Supervisor {
    state: FanState,
    state_entered: Millis,
    last_poll: Millis,
    fault: Option<FaultReason>,
    /// Set by any user command while faulted; consumed by the next poll. This is what
    /// makes CLR_FLT strictly command-driven rather than automatic.
    fault_ack: bool,
    desired: Desired,
    /// The direction actually latched on the DIR pin.
    applied_direction: Direction,
    released_min: MilliRpm,
    ramp: Ramp,
    tach: Tach,
    /// Last duty emitted, so a steady speed does not re-emit an action every tick.
    last_duty: SpeedDuty,
    /// FG total at the moment the current start began, for start supervision.
    start_fg_mark: u64,
}

impl Supervisor {
    /// Build a supervisor in [`FanState::SafeBoot`]. Boot never restores a running state:
    /// regardless of persisted Matter attributes, power-on is always off at zero speed.
    pub fn new(now: Millis, inputs: &Inputs) -> Self {
        Self {
            state: FanState::SafeBoot,
            state_entered: now,
            last_poll: now,
            fault: None,
            fault_ack: false,
            desired: Desired {
                on: false,
                speed: MilliRpm::from_rpm(config::RPM_USER_MIN_TARGET),
                direction: Direction::Forward,
            },
            applied_direction: Direction::Forward,
            released_min: MilliRpm::from_rpm(config::RPM_USER_MIN_TARGET),
            ramp: Ramp::new(),
            tach: Tach::new(inputs.fg_pulses, inputs.hall_pulses, now),
            last_duty: SpeedDuty::ZERO,
            start_fg_mark: 0,
        }
    }

    pub const fn state(&self) -> FanState {
        self.state
    }

    pub const fn fault(&self) -> Option<FaultReason> {
        self.fault
    }

    /// The speed currently commanded to the MCF (the ramp output, not the user's target).
    pub const fn commanded(&self) -> MilliRpm {
        self.ramp.current()
    }

    /// The measured rotor speed, for `PercentCurrent` and telemetry.
    pub const fn measured(&self) -> MilliRpm {
        self.tach.measured()
    }

    pub const fn direction(&self) -> Direction {
        self.applied_direction
    }

    /// The released minimum speed, the bottom of the Matter percent mapping. Raised (never
    /// lowered) as qualification releases it; it is configuration, not a constant.
    pub const fn released_min(&self) -> MilliRpm {
        self.released_min
    }

    /// Raise (or restore) the released minimum. The value is itself clamped into
    /// `[RPM_USER_MIN_TARGET, RPM_USER_MAX]` rather than trusted: a floor above the user
    /// maximum would invert `clamp_speed`'s bounds, and `u32::clamp` panics when `min >
    /// max` — a caller typo would take the control loop down.
    pub fn set_released_min(&mut self, released_min: MilliRpm) {
        self.released_min = MilliRpm(released_min.0.clamp(
            config::RPM_USER_MIN_TARGET * 1_000,
            config::RPM_USER_MAX * 1_000,
        ));
        // A standing setting below a newly raised floor must come up with it, or a bare
        // `On` would resume a speed that is no longer released.
        self.desired.speed = self.clamp_speed(self.desired.speed);
    }

    /// Record a user command. Commands only ever change *intent*; every transition and
    /// every action happens in [`Supervisor::poll`], which keeps the machine deterministic
    /// and the tests honest.
    pub fn command(&mut self, command: Command) {
        // Any fresh user command is what licenses a fault clear.
        if self.state == FanState::Fault {
            self.fault_ack = true;
        }
        match command {
            Command::Off => self.desired.on = false,
            Command::On => self.desired.on = true,
            Command::SetSpeed(speed) => {
                if speed.is_zero() {
                    self.desired.on = false;
                } else {
                    self.desired.speed = self.clamp_speed(speed);
                    self.desired.on = true;
                }
            }
            Command::SetDirection(direction) => self.desired.direction = direction,
        }
    }

    /// Advance the state machine. Call at a steady cadence; the ramp integrates whatever
    /// interval it is actually given.
    pub fn poll(&mut self, now: Millis, inputs: &Inputs) -> Actions {
        let dt = now.since(self.last_poll);
        self.last_poll = now;
        self.tach.update(inputs.fg_pulses, inputs.hall_pulses, now);

        let mut actions = Actions::new();

        if self.state == FanState::Fault {
            self.poll_fault(now, &mut actions);
            return actions;
        }

        // Fault sources outrank every state transition below.
        if let Some(reason) = self.external_fault(inputs) {
            self.enter_fault(now, reason, &mut actions);
            return actions;
        }

        match self.state {
            FanState::SafeBoot => self.poll_safe_boot(now, inputs),
            FanState::IdleOff => self.poll_idle(now, &mut actions),
            FanState::Starting => self.poll_starting(now, dt, &mut actions),
            FanState::Running => self.poll_running(now, dt, &mut actions),
            FanState::Stopping | FanState::Reversing => {
                self.poll_winding_down(now, dt, &mut actions)
            }
            FanState::Fault => unreachable!("handled above"),
        }

        actions
    }

    // -- states ---------------------------------------------------------------------

    /// Hold for the full TI window, then require healthy rails before proceeding. A rail
    /// that never comes good simply keeps us here, which is already the safe outcome.
    fn poll_safe_boot(&mut self, now: Millis, inputs: &Inputs) {
        if now.since(self.state_entered) >= config::SAFE_BOOT_HOLD_MS && inputs.pgood {
            self.transition(FanState::IdleOff, now);
        }
    }

    fn poll_idle(&mut self, now: Millis, actions: &mut Actions) {
        if !self.desired.on || self.desired.speed.is_zero() {
            self.state_entered = now;
            return;
        }
        // Pre-arm plausibility: both channels must agree the rotor is stationary. A
        // windmilling rotor therefore delays a start rather than being caught mid-spin.
        if self.tach.is_quiet(now) {
            self.begin_start(now, actions);
        } else if now.since(self.state_entered) >= config::START_QUIET_TIMEOUT_MS {
            self.enter_fault(now, FaultReason::NeverStopped, actions);
        }
    }

    fn poll_starting(&mut self, now: Millis, dt: u64, actions: &mut Actions) {
        if !self.desired.on || self.desired.speed.is_zero() {
            self.transition(FanState::Stopping, now);
            return;
        }
        let elapsed = now.since(self.state_entered);
        if elapsed < config::ARM_SETTLE_MS {
            return;
        }
        self.ramp.set_target(self.desired.speed);
        self.advance_ramp(dt, actions);

        if self.tach.fg_total() > self.start_fg_mark {
            self.transition(FanState::Running, now);
        } else if elapsed >= config::START_TIMEOUT_MS {
            self.enter_fault(now, FaultReason::NoRotation, actions);
        }
    }

    fn poll_running(&mut self, now: Millis, dt: u64, actions: &mut Actions) {
        if self.tach.hall_implausible() {
            self.enter_fault(now, FaultReason::HallImplausible, actions);
            return;
        }
        if !self.desired.on || self.desired.speed.is_zero() {
            self.transition(FanState::Stopping, now);
            return;
        }
        if self.desired.direction != self.applied_direction {
            self.transition(FanState::Reversing, now);
            return;
        }
        self.ramp.set_target(self.desired.speed);
        self.advance_ramp(dt, actions);
    }

    /// [`FanState::Stopping`] and [`FanState::Reversing`] differ only in what happens after
    /// the rotor is verified stopped, and that difference falls out of `desired` on its own
    /// — so they share one body.
    fn poll_winding_down(&mut self, now: Millis, dt: u64, actions: &mut Actions) {
        // Resuming mid-stop is safe and much better UX: permission has not been revoked
        // yet, so this is just a speed change. A reversal must not take this path — its
        // whole point is to reach a verified stop first.
        if self.state == FanState::Stopping
            && self.desired.on
            && !self.desired.speed.is_zero()
            && self.desired.direction == self.applied_direction
        {
            self.transition(FanState::Running, now);
            return;
        }

        self.ramp.set_target(MilliRpm::ZERO);
        self.advance_ramp(dt, actions);

        if !self.ramp.current().is_zero() || !self.tach.is_quiet(now) {
            return;
        }
        // A normal stop revokes permission. Every restart therefore re-arms and pays the
        // ten-second DRVOFF hold — a deliberate safety-over-UX choice (docs/controls.md).
        self.push(actions, Action::ClearPermission);
        self.transition(FanState::SafeBoot, now);
    }

    fn poll_fault(&mut self, now: Millis, actions: &mut Actions) {
        if !self.fault_ack {
            return;
        }
        self.fault_ack = false;
        self.fault = None;
        self.push(actions, Action::ClearMcfFault);
        self.transition(FanState::SafeBoot, now);
    }

    // -- helpers --------------------------------------------------------------------

    fn external_fault(&self, inputs: &Inputs) -> Option<FaultReason> {
        if inputs.mcf_fault {
            return Some(FaultReason::McfFault);
        }
        if inputs.mcf_alarm {
            return Some(FaultReason::McfAlarm);
        }
        // In SafeBoot a low rail is not yet a fault — it is exactly what SafeBoot is
        // waiting on, and staying put is the safe response.
        if !inputs.pgood && self.state != FanState::SafeBoot {
            return Some(FaultReason::RailLoss);
        }
        None
    }

    fn begin_start(&mut self, now: Millis, actions: &mut Actions) {
        // Legal here and only here: the tach has just confirmed the rotor is stationary.
        if self.desired.direction != self.applied_direction {
            self.applied_direction = self.desired.direction;
            self.push(actions, Action::SetDirection(self.applied_direction));
        }
        self.ramp.reset();
        self.emit_duty(SpeedDuty::ZERO, actions);
        self.push(actions, Action::ArmPulse);
        self.start_fg_mark = self.tach.fg_total();
        self.transition(FanState::Starting, now);
    }

    fn enter_fault(&mut self, now: Millis, reason: FaultReason, actions: &mut Actions) {
        self.fault = Some(reason);
        self.fault_ack = false;
        self.ramp.reset();
        // Revoke first, then zero the command. Ordering matters twice over: revoking
        // permission alone already stops the drive regardless of what duty is on the SPEED
        // pin, and putting the safety-critical action at the head of the buffer means it
        // survives even if some future path overflows the rest.
        self.push(actions, Action::ClearPermission);
        self.emit_duty(SpeedDuty::ZERO, actions);
        self.transition(FanState::Fault, now);
    }

    fn advance_ramp(&mut self, dt: u64, actions: &mut Actions) {
        let commanded = self.ramp.step(dt);
        self.emit_duty(speed::duty_for(commanded), actions);
    }

    fn emit_duty(&mut self, duty: SpeedDuty, actions: &mut Actions) {
        if duty == self.last_duty {
            return;
        }
        self.last_duty = duty;
        self.push(actions, Action::SetSpeedDuty(duty));
    }

    fn transition(&mut self, state: FanState, now: Millis) {
        self.state = state;
        self.state_entered = now;
        if state == FanState::SafeBoot {
            self.ramp.reset();
            self.last_duty = SpeedDuty::ZERO;
        }
    }

    fn clamp_speed(&self, speed: MilliRpm) -> MilliRpm {
        MilliRpm(
            speed
                .0
                .clamp(self.released_min.0, config::RPM_USER_MAX * 1_000),
        )
    }

    /// Actions are bounded by construction: the largest burst any path emits is three
    /// (direction + duty + arm, in `begin_start`) against a buffer of [`MAX_ACTIONS`], and
    /// the host tests walk every path. A full buffer therefore means a code change went
    /// past the audited maximum — the debug assertion catches that in test, and on the
    /// target the action is dropped rather than panicking the control loop. Safety-critical
    /// actions are pushed first so a drop can only ever lose a lower-stakes one.
    fn push(&mut self, actions: &mut Actions, action: Action) {
        let pushed = actions.push(action).is_ok();
        debug_assert!(pushed, "action buffer overflow: {action:?}");
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A test bench that owns the clock, the simulated input pins, and a crude rotor.
    ///
    /// The rotor tracks the commanded speed instantly, which is wildly optimistic as a
    /// motor model and exactly right as a state-machine harness: it lets a test isolate
    /// the supervisor's behaviour from any question of how the real motor responds. Tests
    /// that need a *misbehaving* rotor set `rotor_follows = false` and drive `rotor` by
    /// hand.
    struct Bench {
        supervisor: Supervisor,
        now: Millis,
        inputs: Inputs,
        rotor: MilliRpm,
        /// When false the rotor ignores the command — a jam, a coast, or a dead drive.
        rotor_follows: bool,
        /// When false the Hall channel emits nothing, simulating the documented
        /// magnet/cable single-point failure.
        hall_alive: bool,
        /// Control-loop period. Coarse by default so long-horizon tests stay fast, but
        /// adjustable: a tick coarser than a timing threshold makes the branch guarding it
        /// unreachable, which would let the test suite pass over dead code.
        tick_ms: u64,
        fg_residual: u64,
        hall_residual: u64,
        log: std::vec::Vec<Action>,
    }

    /// milli-RPM × ms × pulses-per-rev, per pulse.
    const PULSE_SCALE: u64 = 60_000 * 1_000;

    impl Bench {
        const TICK_MS: u64 = 100;

        fn new() -> Self {
            let now = Millis::ZERO;
            let inputs = Inputs::default();
            Self {
                supervisor: Supervisor::new(now, &inputs),
                now,
                inputs,
                rotor: MilliRpm::ZERO,
                rotor_follows: true,
                hall_alive: true,
                tick_ms: Self::TICK_MS,
                fg_residual: 0,
                hall_residual: 0,
                log: std::vec::Vec::new(),
            }
        }

        /// Advance one control tick, generating tach edges for the current rotor speed.
        fn tick(&mut self) -> Actions {
            self.now = self.now.plus_ms(self.tick_ms);
            let travel = u64::from(self.rotor.0) * self.tick_ms;

            self.fg_residual += travel * u64::from(config::FG_PULSES_PER_REV);
            self.inputs.fg_pulses = self
                .inputs
                .fg_pulses
                .wrapping_add((self.fg_residual / PULSE_SCALE) as u32);
            self.fg_residual %= PULSE_SCALE;

            if self.hall_alive {
                self.hall_residual += travel * u64::from(config::HALL_PULSES_PER_REV);
                self.inputs.hall_pulses = self
                    .inputs
                    .hall_pulses
                    .wrapping_add((self.hall_residual / PULSE_SCALE) as u32);
                self.hall_residual %= PULSE_SCALE;
            }

            let actions = self.supervisor.poll(self.now, &self.inputs);
            self.log.extend(actions.iter().copied());
            if self.rotor_follows {
                self.rotor = self.supervisor.commanded();
            }
            actions
        }

        fn run_ms(&mut self, ms: u64) {
            for _ in 0..(ms / self.tick_ms) {
                self.tick();
            }
        }

        /// Advance until `predicate` holds, or fail after `limit_ms`.
        fn run_until(
            &mut self,
            limit_ms: u64,
            what: &str,
            predicate: impl Fn(&Supervisor) -> bool,
        ) {
            let deadline = self.now.plus_ms(limit_ms);
            while self.now < deadline {
                self.tick();
                if predicate(&self.supervisor) {
                    return;
                }
            }
            panic!(
                "never reached {what} within {limit_ms} ms (state {:?}, fault {:?})",
                self.supervisor.state(),
                self.supervisor.fault()
            );
        }

        fn boot(&mut self) {
            self.run_until(config::SAFE_BOOT_HOLD_MS + 1_000, "IdleOff", |s| {
                s.state() == FanState::IdleOff
            });
        }

        /// Drive to `rpm` and settle there, from a booted, idle bench.
        fn run_at(&mut self, rpm: u32) {
            self.supervisor
                .command(Command::SetSpeed(MilliRpm::from_rpm(rpm)));
            self.run_until(300_000, "Running", |s| s.state() == FanState::Running);
            self.run_until(300_000, "target speed", |s| {
                s.commanded() == MilliRpm::from_rpm(rpm)
            });
        }

        fn saw(&self, action: Action) -> bool {
            self.log.contains(&action)
        }

        fn take_log(&mut self) -> std::vec::Vec<Action> {
            core::mem::take(&mut self.log)
        }
    }

    #[test]
    fn safe_boot_holds_the_full_ti_window_before_reaching_idle() {
        let mut bench = Bench::new();
        bench.run_ms(config::SAFE_BOOT_HOLD_MS - Bench::TICK_MS);
        assert_eq!(bench.supervisor.state(), FanState::SafeBoot);
        bench.tick();
        assert_eq!(bench.supervisor.state(), FanState::IdleOff);
    }

    #[test]
    fn a_command_during_safe_boot_does_not_shorten_the_hold() {
        let mut bench = Bench::new();
        bench.supervisor.command(Command::On);
        bench.run_ms(config::SAFE_BOOT_HOLD_MS - Bench::TICK_MS);
        assert_eq!(bench.supervisor.state(), FanState::SafeBoot);
        assert!(
            !bench.saw(Action::ArmPulse),
            "armed during the safe-boot hold"
        );
    }

    #[test]
    fn safe_boot_will_not_exit_while_the_rail_is_down() {
        let mut bench = Bench::new();
        bench.inputs.pgood = false;
        bench.run_ms(config::SAFE_BOOT_HOLD_MS * 3);
        assert_eq!(bench.supervisor.state(), FanState::SafeBoot);
        bench.inputs.pgood = true;
        bench.tick();
        assert_eq!(bench.supervisor.state(), FanState::IdleOff);
    }

    #[test]
    fn boot_never_auto_starts() {
        let mut bench = Bench::new();
        bench.boot();
        bench.run_ms(30_000);
        assert_eq!(bench.supervisor.state(), FanState::IdleOff);
        assert!(!bench.saw(Action::ArmPulse));
    }

    #[test]
    fn a_start_arms_permission_and_reaches_running() {
        let mut bench = Bench::new();
        bench.boot();
        bench.take_log();
        bench.run_at(60);
        assert!(bench.saw(Action::ArmPulse), "never requested permission");
        assert!(!bench.saw(Action::ClearPermission));
    }

    #[test]
    fn a_start_is_blocked_until_both_tach_channels_are_quiet() {
        let mut bench = Bench::new();
        bench.boot();
        // A windmilling rotor: turning, but never commanded.
        bench.rotor_follows = false;
        bench.rotor = MilliRpm::from_rpm(40);
        bench.supervisor.command(Command::On);
        bench.run_ms(20_000);
        assert_eq!(bench.supervisor.state(), FanState::IdleOff);
        assert!(
            !bench.saw(Action::ArmPulse),
            "armed against a spinning rotor"
        );

        bench.rotor = MilliRpm::ZERO;
        bench.run_until(config::STOPPED_QUIET_MS + 1_000, "Starting", |s| {
            s.state() != FanState::IdleOff
        });
        assert!(bench.saw(Action::ArmPulse));
    }

    #[test]
    fn a_rotor_that_never_goes_quiet_eventually_faults() {
        let mut bench = Bench::new();
        bench.boot();
        bench.rotor_follows = false;
        bench.rotor = MilliRpm::from_rpm(40);
        bench.supervisor.command(Command::On);
        bench.run_until(config::START_QUIET_TIMEOUT_MS + 5_000, "Fault", |s| {
            s.state() == FanState::Fault
        });
        assert_eq!(bench.supervisor.fault(), Some(FaultReason::NeverStopped));
    }

    #[test]
    fn a_commanded_start_that_never_turns_faults_instead_of_driving_blind() {
        let mut bench = Bench::new();
        bench.boot();
        bench.rotor_follows = false; // jammed, or permission never took
        bench.supervisor.command(Command::On);
        bench.run_until(config::START_TIMEOUT_MS + 5_000, "Fault", |s| {
            s.state() == FanState::Fault
        });
        assert_eq!(bench.supervisor.fault(), Some(FaultReason::NoRotation));
        assert!(bench.saw(Action::ClearPermission));
    }

    #[test]
    fn the_ramp_rate_is_honoured_from_a_standing_start() {
        let mut bench = Bench::new();
        bench.boot();
        bench
            .supervisor
            .command(Command::SetSpeed(MilliRpm::from_rpm(60)));
        bench.run_until(120_000, "60 RPM", |s| {
            s.commanded() == MilliRpm::from_rpm(60)
        });
        // 60 RPM at 1.5 RPM/s is 40 s; the arm settle adds a tick or two.
        let expected = 60_000 * 1_000 / u64::from(config::RAMP_MILLI_RPM_PER_S);
        assert!(
            bench.now.0 >= config::SAFE_BOOT_HOLD_MS + expected,
            "reached speed in {} ms, faster than the ramp allows",
            bench.now.0
        );
    }

    #[test]
    fn a_normal_stop_revokes_permission_and_pays_the_hold_again() {
        let mut bench = Bench::new();
        bench.boot();
        bench.run_at(40);
        bench.take_log();

        bench.supervisor.command(Command::Off);
        bench.run_until(120_000, "SafeBoot", |s| s.state() == FanState::SafeBoot);
        assert!(
            bench.saw(Action::ClearPermission),
            "a normal stop must revoke permission"
        );

        let at_revoke = bench.now;
        bench.run_until(config::SAFE_BOOT_HOLD_MS + 5_000, "IdleOff", |s| {
            s.state() == FanState::IdleOff
        });
        assert!(
            bench.now.since(at_revoke) >= config::SAFE_BOOT_HOLD_MS,
            "restart skipped the ten-second hold"
        );
    }

    #[test]
    fn a_stop_does_not_complete_until_the_rotor_is_verified_stopped() {
        let mut bench = Bench::new();
        bench.boot();
        bench.run_at(40);

        // Coast: the command reaches zero but the rotor keeps turning.
        bench.rotor_follows = false;
        bench.supervisor.command(Command::Off);
        bench.run_until(60_000, "zero command", |s| s.commanded().is_zero());
        bench.run_ms(30_000);
        assert_eq!(bench.supervisor.state(), FanState::Stopping);

        bench.rotor = MilliRpm::ZERO;
        bench.run_until(config::STOPPED_QUIET_MS + 1_000, "SafeBoot", |s| {
            s.state() == FanState::SafeBoot
        });
    }

    #[test]
    fn turning_back_on_mid_stop_resumes_without_re_arming() {
        let mut bench = Bench::new();
        bench.boot();
        bench.run_at(60);
        bench.supervisor.command(Command::Off);
        bench.run_ms(2_000);
        assert_eq!(bench.supervisor.state(), FanState::Stopping);
        bench.take_log();

        bench.supervisor.command(Command::On);
        bench.tick();
        assert_eq!(bench.supervisor.state(), FanState::Running);
        assert!(
            !bench.saw(Action::ArmPulse),
            "re-armed a still-permitted drive"
        );
    }

    #[test]
    fn a_direction_change_while_running_stops_first_and_re_arms() {
        let mut bench = Bench::new();
        bench.boot();
        bench.run_at(40);
        bench.take_log();

        bench
            .supervisor
            .command(Command::SetDirection(Direction::Reverse));
        bench.tick();
        assert_eq!(bench.supervisor.state(), FanState::Reversing);
        assert_eq!(
            bench.supervisor.direction(),
            Direction::Forward,
            "DIR flipped before the rotor stopped"
        );

        bench.run_until(200_000, "Running again", |s| s.state() == FanState::Running);
        assert_eq!(bench.supervisor.direction(), Direction::Reverse);

        let log = bench.take_log();
        let dir_at = log
            .iter()
            .position(|a| *a == Action::SetDirection(Direction::Reverse))
            .expect("DIR was never set");
        let clear_at = log
            .iter()
            .position(|a| *a == Action::ClearPermission)
            .expect("permission was never revoked");
        let arm_at = log
            .iter()
            .position(|a| *a == Action::ArmPulse)
            .expect("permission was never re-armed");
        assert!(
            clear_at < dir_at,
            "DIR changed before permission was revoked"
        );
        assert!(dir_at < arm_at, "re-armed before DIR was set");
    }

    #[test]
    fn a_reversal_is_not_short_circuited_by_turning_back_on() {
        let mut bench = Bench::new();
        bench.boot();
        bench.run_at(40);
        bench
            .supervisor
            .command(Command::SetDirection(Direction::Reverse));
        bench.tick();
        assert_eq!(bench.supervisor.state(), FanState::Reversing);

        bench.supervisor.command(Command::On);
        bench.tick();
        assert_eq!(
            bench.supervisor.state(),
            FanState::Reversing,
            "a reversal must reach a verified stop"
        );
    }

    #[test]
    fn nfault_stops_the_fan_and_requires_a_fresh_command() {
        let mut bench = Bench::new();
        bench.boot();
        bench.run_at(40);
        bench.take_log();

        bench.inputs.mcf_fault = true;
        bench.tick();
        assert_eq!(bench.supervisor.state(), FanState::Fault);
        assert_eq!(bench.supervisor.fault(), Some(FaultReason::McfFault));
        assert!(bench.saw(Action::ClearPermission));
        assert!(bench.saw(Action::SetSpeedDuty(SpeedDuty::ZERO)));

        // No amount of waiting leaves Fault on its own.
        bench.inputs.mcf_fault = false;
        bench.run_ms(60_000);
        assert_eq!(bench.supervisor.state(), FanState::Fault);
        assert!(
            !bench.saw(Action::ClearMcfFault),
            "cleared without a command"
        );

        bench.supervisor.command(Command::Off);
        bench.tick();
        assert!(bench.saw(Action::ClearMcfFault));
        assert_eq!(bench.supervisor.state(), FanState::SafeBoot);
    }

    #[test]
    fn a_dead_hall_channel_stops_the_fan() {
        let mut bench = Bench::new();
        bench.boot();
        bench.run_at(60);

        bench.hall_alive = false;
        bench.run_until(60_000, "Fault", |s| s.state() == FanState::Fault);
        assert_eq!(bench.supervisor.fault(), Some(FaultReason::HallImplausible));
        assert!(bench.saw(Action::ClearPermission));
    }

    #[test]
    fn the_alarm_pin_stops_the_fan_and_requires_a_fresh_command() {
        // ALARM carries the report-only conditions that never reach nFAULT — including the
        // OTW/TSD thermal reports the failure table requires be treated as a stop.
        let mut bench = Bench::new();
        bench.boot();
        bench.run_at(40);
        bench.take_log();

        bench.inputs.mcf_alarm = true;
        bench.tick();
        assert_eq!(bench.supervisor.state(), FanState::Fault);
        assert_eq!(bench.supervisor.fault(), Some(FaultReason::McfAlarm));
        assert!(bench.saw(Action::ClearPermission));

        bench.inputs.mcf_alarm = false;
        bench.run_ms(30_000);
        assert_eq!(
            bench.supervisor.state(),
            FanState::Fault,
            "left Fault without a command"
        );

        bench.supervisor.command(Command::Off);
        bench.tick();
        assert_eq!(bench.supervisor.state(), FanState::SafeBoot);
    }

    #[test]
    fn losing_the_rail_while_running_is_a_fault() {
        let mut bench = Bench::new();
        bench.boot();
        bench.run_at(40);
        bench.inputs.pgood = false;
        bench.tick();
        assert_eq!(bench.supervisor.fault(), Some(FaultReason::RailLoss));
    }

    #[test]
    fn a_bare_on_resumes_the_last_non_zero_speed() {
        // The constructor's default happens to equal the qualification minimum, so this
        // has to use a distinctly different speed or a regression that reset the stored
        // setting on Off would be invisible.
        let resumed = 90;
        assert_ne!(resumed, config::RPM_USER_MIN_TARGET);

        let mut bench = Bench::new();
        bench.boot();
        bench.run_at(resumed);
        bench.supervisor.command(Command::Off);
        bench.run_until(300_000, "IdleOff", |s| s.state() == FanState::IdleOff);

        bench.supervisor.command(Command::On);
        bench.run_until(300_000, "resumed speed", |s| {
            s.commanded() == MilliRpm::from_rpm(resumed)
        });
    }

    #[test]
    fn raising_the_released_minimum_lifts_a_standing_setting_with_it() {
        let mut bench = Bench::new();
        bench.boot();
        bench
            .supervisor
            .command(Command::SetSpeed(MilliRpm::from_rpm(40)));
        bench.supervisor.command(Command::Off);

        // Qualification releases a higher floor than the standing 40 RPM setting.
        bench.supervisor.set_released_min(MilliRpm::from_rpm(55));
        bench.supervisor.command(Command::On);
        bench.run_until(300_000, "the new floor", |s| {
            s.commanded() == MilliRpm::from_rpm(55)
        });
    }

    #[test]
    fn a_released_minimum_above_the_user_maximum_is_refused_rather_than_inverting() {
        // `clamp_speed` would panic on inverted bounds, taking the control loop down.
        let mut bench = Bench::new();
        bench
            .supervisor
            .set_released_min(MilliRpm::from_rpm(config::RPM_USER_MAX + 50));
        assert_eq!(
            bench.supervisor.released_min(),
            MilliRpm::from_rpm(config::RPM_USER_MAX)
        );
        bench.boot();
        bench.run_at(config::RPM_USER_MAX);
    }

    #[test]
    fn the_arm_settle_delay_holds_the_speed_command_at_zero() {
        // A tick coarser than ARM_SETTLE_MS would step straight over this branch, so the
        // bench runs fine-grained here on purpose.
        let mut bench = Bench::new();
        bench.boot();
        bench.tick_ms = 10;
        assert!(bench.tick_ms < config::ARM_SETTLE_MS);
        bench.take_log();

        bench
            .supervisor
            .command(Command::SetSpeed(MilliRpm::from_rpm(60)));
        bench.run_until(1_000, "Starting", |s| s.state() == FanState::Starting);
        let armed_at = bench.now;

        let mut held = 0;
        loop {
            bench.tick();
            if bench.now.since(armed_at) >= config::ARM_SETTLE_MS {
                break;
            }
            assert_eq!(
                bench.supervisor.commanded(),
                MilliRpm::ZERO,
                "ramped before the permission latch settled"
            );
            held += 1;
        }
        assert!(held > 0, "the settle branch was never actually exercised");
        bench.run_until(5_000, "ramping", |s| !s.commanded().is_zero());
    }

    #[test]
    fn speed_commands_are_clamped_to_the_released_user_range() {
        let mut bench = Bench::new();
        bench.boot();
        bench
            .supervisor
            .command(Command::SetSpeed(MilliRpm::from_rpm(500)));
        bench.run_until(300_000, "top speed", |s| {
            s.commanded() == MilliRpm::from_rpm(config::RPM_USER_MAX)
        });
        bench.run_ms(30_000);
        assert_eq!(
            bench.supervisor.commanded(),
            MilliRpm::from_rpm(config::RPM_USER_MAX),
            "commanded past the user maximum"
        );
    }

    #[test]
    fn a_speed_below_the_released_minimum_is_raised_to_it() {
        let mut bench = Bench::new();
        bench.boot();
        bench.supervisor.set_released_min(MilliRpm::from_rpm(45));
        bench
            .supervisor
            .command(Command::SetSpeed(MilliRpm::from_rpm(20)));
        bench.run_until(120_000, "released minimum", |s| {
            s.commanded() == MilliRpm::from_rpm(45)
        });
        bench.run_ms(10_000);
        assert_eq!(bench.supervisor.commanded(), MilliRpm::from_rpm(45));
    }

    #[test]
    fn network_loss_is_simply_the_absence_of_commands() {
        // The contract's "keep the last local speed" is a property of the machine having
        // no timeout on commands at all. Assert that absence directly.
        let mut bench = Bench::new();
        bench.boot();
        bench.run_at(40);
        bench.run_ms(600_000);
        assert_eq!(bench.supervisor.state(), FanState::Running);
        assert_eq!(bench.supervisor.commanded(), MilliRpm::from_rpm(40));
    }
}
