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
use crate::mcf8316::{FaultStatus, McfCondition};
use crate::mcf_config::{ConfigCheck, ConfigFault};
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
    /// nFAULT asserted but the status registers have not been read (or could not be), so
    /// the cause is unknown. Once a status read lands, [`FaultReason::Mcf`] names it.
    McfFault,
    /// ALARM asserted with no decoded status behind it.
    McfAlarm,
    /// A decoded MCF fault-status condition — undervoltage, thermal, lock, and so on.
    Mcf(McfCondition),
    /// The MCF has been unreachable over I²C for [`config::BUS_FAILURES_BEFORE_FAULT`]
    /// consecutive attempts. Bus recovery is the caller's job; the supervisor's job is to
    /// stop trusting a drive it can no longer interrogate.
    BusUnreachable,
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
    /// The MCF's stored configuration is not the one this firmware is qualified against —
    /// or the device says its own EEPROM is unusable. Every limit the supervisor layers on
    /// top (the 180 RPM stored ceiling, latched fault responses, the external watchdog) lives
    /// in that configuration, so running without it is running without them.
    ConfigUnverified(ConfigFault),
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
pub const MAX_ACTIONS: usize = 6;

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
    /// What the last attempt to read the MCF's fault-status registers produced.
    pub mcf_status: StatusRead,
    /// The standing verdict on the MCF's stored configuration. Unlike [`Inputs::mcf_status`]
    /// this is a level, not an event: it is produced once at boot (and again after anything
    /// writes the configuration block) and holds until something changes it.
    pub config: ConfigCheck,
    pub fg_pulses: u32,
    pub hall_pulses: u32,
}

/// The outcome of a fault-status register read.
///
/// Distinguishing "not read this tick" from "read and clean" matters: the status registers
/// are polled far more slowly than the pins are sampled, and a stale-but-clean read must not
/// be mistaken for evidence that a freshly asserted nFAULT is spurious.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum StatusRead {
    /// No read completed since the last poll. Carries no information either way.
    #[default]
    Stale,
    /// Both registers read cleanly.
    Fresh(FaultStatus),
    /// The read failed. Repeated failures are themselves a fault.
    BusError,
}

impl Default for Inputs {
    /// A healthy, stationary board whose configuration has been checked and matches.
    fn default() -> Self {
        Self {
            pgood: true,
            mcf_fault: false,
            mcf_alarm: false,
            mcf_status: StatusRead::Stale,
            config: ConfigCheck::Verified,
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
    /// Consecutive failed status reads. Reset by any successful one.
    bus_failures: u32,
    /// When a status read last produced *any* verdict, success or failure. Distinguishes a
    /// quiet bus from a reader that has stopped running.
    last_status_at: Millis,
    /// Latest configuration verdict, kept so telemetry can report it without the caller
    /// having to carry the input through separately.
    config: ConfigCheck,
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
            bus_failures: 0,
            last_status_at: now,
            config: inputs.config,
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

    /// The independent Hall estimate. Reported alongside [`Supervisor::measured`] rather
    /// than blended into it: the two disagreeing is the Hall-loss diagnosis.
    pub const fn measured_hall(&self) -> MilliRpm {
        self.tach.measured_hall()
    }

    pub const fn direction(&self) -> Direction {
        self.applied_direction
    }

    /// The standing verdict on the MCF's stored configuration, for telemetry. Reported on
    /// every frame rather than logged once at boot: a bench capture taken against an
    /// unverified configuration should say so in the capture itself.
    pub const fn config(&self) -> ConfigCheck {
        self.config
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
        self.observe_bus(now, inputs);
        self.config = inputs.config;

        let mut actions = Actions::new();

        if self.state == FanState::Fault {
            self.poll_fault(now, &mut actions);
            return actions;
        }

        // Fault sources outrank every state transition below.
        if let Some(reason) = self.external_fault(now, inputs) {
            self.enter_fault(now, reason, &mut actions);
            return actions;
        }

        match self.state {
            FanState::SafeBoot => self.poll_safe_boot(now, inputs, &mut actions),
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
    fn poll_safe_boot(&mut self, now: Millis, inputs: &Inputs, actions: &mut Actions) {
        if now.since(self.state_entered) < config::SAFE_BOOT_HOLD_MS || !inputs.pgood {
            return;
        }
        // The hold is over, so an MCF fault that is still asserted has had the full ten
        // seconds (and any CLR_FLT its 200 ms) to clear and has not. Report it once here
        // rather than bouncing through Fault on every tick of the hold.
        if let Some(reason) = self.mcf_fault_source(now, inputs) {
            self.enter_fault(now, reason, actions);
            return;
        }
        // "Stored configuration verified" — the last clause of the contract's safe-boot step,
        // and the reason `SafeBoot` is a state rather than a delay. The check runs on the I²C
        // task while the hold elapses, so by here it has normally already answered.
        match inputs.config {
            ConfigCheck::Failed(fault) => {
                self.enter_fault(now, FaultReason::ConfigUnverified(fault), actions);
                return;
            }
            // No verdict yet. Wait, but not forever: a supervisor sitting in `SafeBoot`
            // reporting nothing is indistinguishable from a board that will not boot.
            ConfigCheck::Pending => {
                if now.since(self.state_entered)
                    >= config::SAFE_BOOT_HOLD_MS + config::CONFIG_CHECK_GRACE_MS
                {
                    self.enter_fault(
                        now,
                        FaultReason::ConfigUnverified(ConfigFault::TimedOut),
                        actions,
                    );
                }
                return;
            }
            // `Unverified` proceeds deliberately: until a golden image has been captured
            // from a real device there is nothing to compare against, and the harness has to
            // be usable in order to capture one. It is carried in every telemetry frame so
            // the distinction is never invisible.
            ConfigCheck::Verified | ConfigCheck::Unverified => {}
        }
        self.transition(FanState::IdleOff, now);
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

    /// Is the drive armed, or on its way to being disarmed? These are the states in which
    /// losing sight of the MCF actually matters.
    const fn armed(&self) -> bool {
        matches!(
            self.state,
            FanState::Starting | FanState::Running | FanState::Stopping | FanState::Reversing
        )
    }

    /// Fault sources that originate at the MCF, as opposed to at our own board.
    ///
    /// Kept separate from [`Supervisor::external_fault`] because [`FanState::SafeBoot`]
    /// deliberately *suppresses* these and re-checks them once, at its exit. Evaluating them
    /// every 50 ms through the hold would make a fault-clear impossible to land: CLR_FLT
    /// takes up to 200 ms to take effect, so the fan would re-fault four ticks after the
    /// user's command, silently consuming it and demanding another. Suppressing for the
    /// hold gives the clear ten seconds to work, and a fault that survives that is a real
    /// one worth reporting.
    fn mcf_fault_source(&self, now: Millis, inputs: &Inputs) -> Option<FaultReason> {
        // A decoded status outranks the pins: both nFAULT and ALARM say only "something",
        // and the registers say what. This also catches the conditions that reach neither
        // pin — MIN_VM undervoltage is reported but not actionable, and thermal shutdown
        // auto-recovers by silicon design and so may clear nFAULT before we look.
        if let StatusRead::Fresh(status) = inputs.mcf_status {
            if let Some(condition) = status.condition() {
                return Some(FaultReason::Mcf(condition));
            }
        }
        if inputs.mcf_fault {
            return Some(FaultReason::McfFault);
        }
        if inputs.mcf_alarm {
            return Some(FaultReason::McfAlarm);
        }
        // One failed read is a transient; the bus is allowed to be retried and recovered.
        // Only sustained silence means the drive can no longer be interrogated, and a drive
        // we cannot interrogate is one we must not keep commanding.
        if self.bus_failures >= config::BUS_FAILURES_BEFORE_FAULT {
            return Some(FaultReason::BusUnreachable);
        }
        // Counting *failures* is not enough. If whatever performs the reads stops running
        // at all — starved by a lower-priority task, deadlocked, panicked — no failure is
        // ever reported and the count never moves, so total silence would look exactly like
        // "nothing new since last tick". Time is the only thing that distinguishes them.
        if self.armed() && now.since(self.last_status_at) >= config::STATUS_STALE_TIMEOUT_MS {
            return Some(FaultReason::BusUnreachable);
        }
        None
    }

    fn external_fault(&self, now: Millis, inputs: &Inputs) -> Option<FaultReason> {
        if self.state != FanState::SafeBoot {
            if let Some(reason) = self.mcf_fault_source(now, inputs) {
                return Some(reason);
            }
            // In SafeBoot a low rail is not yet a fault — it is exactly what SafeBoot is
            // waiting on, and staying put is the safe response.
            if !inputs.pgood {
                return Some(FaultReason::RailLoss);
            }
            // A verdict can turn bad after boot: the console's `config apply` re-checks when
            // it is done, and a write that did not stick lands here. Outside `SafeBoot` there
            // is no hold left to wait through, so it is a fault immediately.
            if let ConfigCheck::Failed(fault) = inputs.config {
                return Some(FaultReason::ConfigUnverified(fault));
            }
        }
        None
    }

    /// Track bus health so the fault sources above can act on it.
    fn observe_bus(&mut self, now: Millis, inputs: &Inputs) {
        match inputs.mcf_status {
            StatusRead::BusError => {
                self.bus_failures = self.bus_failures.saturating_add(1);
                self.last_status_at = now;
            }
            StatusRead::Fresh(_) => {
                self.bus_failures = 0;
                self.last_status_at = now;
            }
            // Carries no information: it neither absolves a growing failure count nor
            // counts as one. Only the clock notices sustained staleness.
            StatusRead::Stale => {}
        }
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
    use crate::mcf8316::{controller_fault, gate_fault};

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
        /// The simulated I2C status reader. Healthy and reporting a clean device by
        /// default, because that is what the supervisor requires in order to stay armed —
        /// an armed drive with no status verdict at all is a fault by design.
        reader: Reader,
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

    /// What the simulated status-reading task is doing.
    #[derive(Debug, Clone, Copy)]
    enum Reader {
        /// Running and reporting this status.
        Ok(FaultStatus),
        /// Running, but every read fails.
        Failing,
        /// Not running at all — publishes nothing, ever. Starved, deadlocked, or panicked.
        Dead,
    }

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
                reader: Reader::Ok(FaultStatus::default()),
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

            // The reader runs on its own, slower cadence, exactly as the real task does.
            self.inputs.mcf_status = if self.now.0.is_multiple_of(config::STATUS_POLL_MS) {
                match self.reader {
                    Reader::Ok(status) => StatusRead::Fresh(status),
                    Reader::Failing => StatusRead::BusError,
                    Reader::Dead => StatusRead::Stale,
                }
            } else {
                StatusRead::Stale
            };

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

        /// Set what the simulated reader reports from now on. Persistent, like a latched
        /// fault, rather than a single injected reading.
        fn report_status(&mut self, status: FaultStatus) {
            self.reader = Reader::Ok(status);
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
    fn safe_boot_waits_for_a_configuration_verdict_then_proceeds() {
        // The check runs concurrently with the hold on a real board, so this is the ordinary
        // case: a verdict that lands late but within the grace window costs nothing.
        let mut bench = Bench::new();
        bench.inputs.config = ConfigCheck::Pending;
        bench.run_ms(config::SAFE_BOOT_HOLD_MS + config::CONFIG_CHECK_GRACE_MS / 2);
        assert_eq!(
            bench.supervisor.state(),
            FanState::SafeBoot,
            "left SafeBoot without a verdict on the stored configuration"
        );

        bench.inputs.config = ConfigCheck::Verified;
        bench.tick();
        assert_eq!(bench.supervisor.state(), FanState::IdleOff);
    }

    #[test]
    fn a_verdict_that_never_arrives_faults_rather_than_hanging_in_safe_boot() {
        // A supervisor parked in SafeBoot reporting nothing looks exactly like a board that
        // will not boot; the whole point of a fault is that it says which.
        let mut bench = Bench::new();
        bench.inputs.config = ConfigCheck::Pending;
        bench.run_until(
            config::SAFE_BOOT_HOLD_MS + config::CONFIG_CHECK_GRACE_MS * 3,
            "Fault",
            |s| s.state() == FanState::Fault,
        );
        assert_eq!(
            bench.supervisor.fault(),
            Some(FaultReason::ConfigUnverified(ConfigFault::TimedOut))
        );
    }

    #[test]
    fn a_failed_configuration_check_never_reaches_idle() {
        // Every limit the supervisor layers on top of lives in that configuration, so a
        // mismatch means the layers below it are unknown.
        let fault = ConfigFault::Mismatch { address: 0x08A };
        let mut bench = Bench::new();
        bench.inputs.config = ConfigCheck::Failed(fault);
        bench.run_until(config::SAFE_BOOT_HOLD_MS + 5_000, "Fault", |s| {
            s.state() == FanState::Fault
        });
        assert_eq!(
            bench.supervisor.fault(),
            Some(FaultReason::ConfigUnverified(fault))
        );
        assert!(bench.saw(Action::ClearPermission));

        // And clearing it does not get past the gate either — a bad configuration does not
        // heal on its own, so the fan stays down until the configuration is fixed.
        bench.supervisor.command(Command::Off);
        bench.run_ms(config::SAFE_BOOT_HOLD_MS * 2);
        assert_eq!(bench.supervisor.state(), FanState::Fault);
    }

    #[test]
    fn an_unverified_configuration_runs_but_says_so() {
        // Before a golden image has been captured there is nothing to compare against, and
        // the harness has to work in order to capture one. The distinction must still be
        // visible in telemetry rather than silently equal to "verified".
        let mut bench = Bench::new();
        bench.inputs.config = ConfigCheck::Unverified;
        bench.boot();
        bench.run_at(40);
        assert_eq!(bench.supervisor.config(), ConfigCheck::Unverified);
        assert_ne!(bench.supervisor.config(), ConfigCheck::Verified);
    }

    #[test]
    fn a_configuration_that_goes_bad_after_boot_stops_the_fan() {
        // `config apply` re-checks when it finishes, so a write that did not stick shows up
        // here. There is no hold left to wait through outside SafeBoot.
        let mut bench = Bench::new();
        bench.boot();
        bench.run_at(40);
        let fault = ConfigFault::DeviceEeprom;
        bench.inputs.config = ConfigCheck::Failed(fault);
        bench.tick();
        assert_eq!(
            bench.supervisor.fault(),
            Some(FaultReason::ConfigUnverified(fault))
        );
        assert!(bench.saw(Action::ClearPermission));
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
    fn undervoltage_while_running_stops_the_fan() {
        // DRV-09: windmilling BEMF back-feed can lift VM above the 18 V auto-recovery
        // point and chatter the drive, so a MIN_VM report is a stop, not a wait — even
        // though the MCF recovers from it on its own.
        let mut bench = Bench::new();
        bench.boot();
        bench.run_at(40);
        bench.take_log();

        bench.report_status(FaultStatus::new(0, controller_fault::MTR_UNDER_VOLTAGE));
        bench.run_until(config::STATUS_POLL_MS * 3, "Fault", |s| {
            s.state() == FanState::Fault
        });
        assert_eq!(
            bench.supervisor.fault(),
            Some(FaultReason::Mcf(McfCondition::Undervoltage))
        );
        assert!(bench.saw(Action::ClearPermission));
        assert!(bench.saw(Action::SetSpeedDuty(SpeedDuty::ZERO)));
    }

    #[test]
    fn a_thermal_report_is_a_stop_even_though_shutdown_auto_recovers() {
        // TSD auto-recovers by silicon design and cannot be latched, so firmware must not
        // wait for a latch that will never hold.
        for bit in [gate_fault::OTW, gate_fault::OTS] {
            let mut bench = Bench::new();
            bench.boot();
            bench.run_at(40);
            bench.report_status(FaultStatus::new(bit, 0));
            bench.run_until(config::STATUS_POLL_MS * 3, "Fault", |s| {
                s.state() == FanState::Fault
            });
            assert_eq!(
                bench.supervisor.fault(),
                Some(FaultReason::Mcf(McfCondition::Overtemperature)),
                "gate bit {bit:#010x}"
            );

            // And it stays stopped once the thermal condition clears on its own.
            bench.report_status(FaultStatus::default());
            bench.run_ms(30_000);
            assert_eq!(bench.supervisor.state(), FanState::Fault);
        }
    }

    #[test]
    fn a_motor_lock_report_stops_the_fan() {
        let mut bench = Bench::new();
        bench.boot();
        bench.run_at(40);
        bench.report_status(FaultStatus::new(0, controller_fault::ABN_SPEED));
        bench.run_until(config::STATUS_POLL_MS * 3, "Fault", |s| {
            s.state() == FanState::Fault
        });
        assert_eq!(
            bench.supervisor.fault(),
            Some(FaultReason::Mcf(McfCondition::MotorLock))
        );
    }

    #[test]
    fn a_decoded_status_outranks_the_bare_fault_pin() {
        // Precedence *within one snapshot*: nFAULT says only "something", the registers say
        // what. Driven directly rather than through the bench, because the reader's slower
        // cadence would otherwise decide which arrives first.
        let mut bench = Bench::new();
        bench.boot();
        bench.run_at(40);

        let inputs = Inputs {
            mcf_fault: true,
            mcf_status: StatusRead::Fresh(FaultStatus::new(gate_fault::OCP, 0)),
            ..bench.inputs
        };
        bench.supervisor.poll(bench.now.plus_ms(50), &inputs);
        assert_eq!(
            bench.supervisor.fault(),
            Some(FaultReason::Mcf(McfCondition::Overcurrent))
        );
    }

    #[test]
    fn fault_source_precedence_holds_for_every_adjacent_pair() {
        // Each case sets two sources at once and names which must be reported. Without
        // this, reordering the checks in `mcf_fault_source` would pass every other test.
        let decoded = StatusRead::Fresh(FaultStatus::new(gate_fault::OTW, 0));
        let cases = [
            (
                Inputs {
                    mcf_status: decoded,
                    mcf_alarm: true,
                    ..Inputs::default()
                },
                FaultReason::Mcf(McfCondition::Overtemperature),
                "decoded status over ALARM",
            ),
            (
                Inputs {
                    mcf_fault: true,
                    mcf_alarm: true,
                    ..Inputs::default()
                },
                FaultReason::McfFault,
                "nFAULT over ALARM",
            ),
            (
                Inputs {
                    mcf_alarm: true,
                    pgood: false,
                    ..Inputs::default()
                },
                FaultReason::McfAlarm,
                "ALARM over rail loss",
            ),
        ];

        for (inputs, expected, what) in cases {
            let mut bench = Bench::new();
            bench.boot();
            bench.run_at(40);
            bench.supervisor.poll(bench.now.plus_ms(50), &inputs);
            assert_eq!(bench.supervisor.fault(), Some(expected), "{what}");
        }
    }

    #[test]
    fn transient_bus_failures_are_tolerated_but_sustained_ones_are_not() {
        let mut bench = Bench::new();
        bench.boot();
        bench.run_at(40);

        // Four failures out of the five it takes: the fan keeps running.
        bench.reader = Reader::Failing;
        bench.run_ms(config::STATUS_POLL_MS * (u64::from(config::BUS_FAILURES_BEFORE_FAULT) - 1));
        assert_eq!(
            bench.supervisor.state(),
            FanState::Running,
            "a transient bus error must not stop the fan"
        );

        // One good read resets the count, so an intermittent bus never accumulates.
        bench.report_status(FaultStatus::default());
        bench.run_ms(config::STATUS_POLL_MS * 2);
        assert_eq!(bench.supervisor.state(), FanState::Running);

        bench.reader = Reader::Failing;
        bench.run_until(config::STATUS_POLL_MS * 20, "Fault", |s| {
            s.state() == FanState::Fault
        });
        assert_eq!(bench.supervisor.fault(), Some(FaultReason::BusUnreachable));
        assert!(bench.saw(Action::ClearPermission));
    }

    #[test]
    fn a_status_reader_that_stops_running_is_caught_by_time_not_by_failures() {
        // The failure counter only moves when a read actually fails. A reader that is
        // starved, deadlocked, or dead reports nothing at all, so silence must be caught
        // by the clock or it looks exactly like "nothing new this tick" forever.
        let mut bench = Bench::new();
        bench.boot();
        bench.run_at(40);

        bench.reader = Reader::Dead;
        bench.run_ms(config::STATUS_STALE_TIMEOUT_MS / 2);
        assert_eq!(
            bench.supervisor.state(),
            FanState::Running,
            "faulted before the staleness deadline"
        );

        bench.run_until(config::STATUS_STALE_TIMEOUT_MS * 2, "Fault", |s| {
            s.state() == FanState::Fault
        });
        assert_eq!(bench.supervisor.fault(), Some(FaultReason::BusUnreachable));
    }

    #[test]
    fn a_stale_tick_alone_never_faults_a_healthy_bus() {
        // Most ticks are stale by construction — the reader is ten times slower than the
        // control loop. Staleness between good reads must count for nothing.
        let mut bench = Bench::new();
        bench.boot();
        bench.run_at(40);
        bench.run_ms(config::STATUS_STALE_TIMEOUT_MS * 5);
        assert_eq!(bench.supervisor.state(), FanState::Running);
        assert_eq!(bench.supervisor.fault(), None);
    }

    #[test]
    fn a_stale_status_does_not_mask_a_freshly_asserted_fault_pin() {
        let mut bench = Bench::new();
        bench.boot();
        bench.run_at(40);
        // A clean read, then the pin asserts before the next read lands.
        bench.report_status(FaultStatus::default());
        bench.tick();
        bench.inputs.mcf_status = StatusRead::Stale;
        bench.inputs.mcf_fault = true;
        bench.tick();
        assert_eq!(bench.supervisor.fault(), Some(FaultReason::McfFault));
    }

    #[test]
    fn a_reboot_while_powered_lands_off_and_never_resumes() {
        // The rotor is still windmilling from before the reboot; 24 V never dropped.
        let mut bench = Bench::new();
        bench.rotor_follows = false;
        bench.rotor = MilliRpm::from_rpm(80);
        bench.inputs.fg_pulses = 12_345;
        bench.inputs.hall_pulses = 617;
        bench.supervisor = Supervisor::new(bench.now, &bench.inputs);

        bench.run_ms(config::SAFE_BOOT_HOLD_MS * 3);
        // It pays the hold and settles in off, not in whatever it was doing before.
        assert_eq!(bench.supervisor.state(), FanState::IdleOff);
        assert_eq!(bench.supervisor.commanded(), MilliRpm::ZERO);
        assert!(!bench.saw(Action::ArmPulse), "resumed after a reboot");

        // And the windmilling rotor it woke up to does not become a start.
        bench.run_ms(60_000);
        assert!(!bench.saw(Action::ArmPulse));
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
