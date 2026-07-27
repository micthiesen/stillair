//! Fan supervisor state machine (stub).
//!
//! Required behavior is defined in `docs/controls.md` > "Required state behavior"
//! and "Failure behavior". Nothing here drives hardware yet.

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
    /// Maintain the last local speed even if HomeKit/Wi-Fi disappears.
    Running,
    /// Ramp to zero and coast (never brake into the supply).
    Stopping,
    /// Ramp to zero, verify near-zero FG, coast, flip DIR, then restart.
    Reversing,
    /// Hi-Z, permission cleared where applicable, diagnostics exposed; a fresh
    /// user command is required to leave.
    Fault,
}

/// Commands arriving from HomeKit (or local control).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Command {
    Off,
    /// Target speed in mechanical RPM, clamped to the released user range.
    SetSpeed(u32),
    SetDirection(Direction),
}

pub struct Supervisor {
    state: FanState,
}

impl Supervisor {
    pub fn new() -> Self {
        Self {
            state: FanState::SafeBoot,
        }
    }

    pub fn state(&self) -> FanState {
        self.state
    }

    /// Advance the state machine. Stub: stays in SafeBoot until the hardware
    /// interfaces exist.
    pub fn tick(&mut self) {
        // TODO: implement the transition rules from docs/controls.md, including:
        // - SafeBoot exit only after the 10 s DRVOFF hold + healthy fault sources
        // - power restoration lands in IdleOff (never auto-restart)
        // - reversal only via Stopping with verified near-zero speed
        // - FG vs HALL_TACH plausibility check before every arm and while running
    }

    /// Handle a user command. Stub.
    pub fn handle(&mut self, command: Command) {
        let _ = command;
        // TODO: route commands per state; power-on command is zero and disabled.
    }
}
