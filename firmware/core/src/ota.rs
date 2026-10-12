//! Over-the-air update policy: when the fan must stand down, when a reset is safe, and what
//! evidence lets a freshly updated image confirm itself.
//!
//! The update transport and boot-slot bookkeeping live in `esp-lan-ota`; this module owns only
//! the fan-specific decisions, so they are host-tested like the rest of the contract.
//!
//! An update ends in a software reset, and a reset lands in off (`docs/controls.md`), so a new
//! upload is accepted only while the fan is already stopped (or faulted) with no standing On
//! intent, and the fan is held off until the reset. Flash erases, which run with interrupts
//! masked, therefore never overlap a spinning or spinning-down motor.

use crate::config;
use crate::mcf_config::ConfigCheck;
use crate::state::{Command, FanState};

/// How long a new image may take to prove itself before it resets and the bootloader rolls
/// back to the previous one. Generous: Wi-Fi association, CASE and a controller's next poll
/// all have to happen, and an unnecessary rollback only costs another push.
pub const CONFIRM_TIMEOUT_SECS: u64 = 600;

/// How long to wait for the fan to reach a reset-safe state before resetting anyway. A
/// controlled stop is preferred, but an ESP-only reset is already a case the hardware handles:
/// boot holds MCU_CLEAR_N asserted and the external watchdog revokes drive on a missed beat.
pub const QUIESCE_TIMEOUT_SECS: u64 = 60;

/// Control-loop iterations that must complete before confirmation: past the safe-boot hold,
/// so the supervisor has run its own rail, watchdog and configuration checks.
pub const MIN_CONTROL_BEATS: u32 =
    ((config::SAFE_BOOT_HOLD_MS + 5_000) / config::CONTROL_TICK_MS) as u32;

/// Successful MCF status reads required: ten seconds of the 200 ms poll.
pub const MIN_MCF_STATUS_READS: u32 = (10_000 / config::STATUS_POLL_MS) as u32;

/// Is a software reset now equivalent to a power cycle with the fan off?
///
/// `Fault` qualifies: permission is already revoked and speed is zero.
pub const fn reset_safe(state: FanState) -> bool {
    matches!(
        state,
        FanState::SafeBoot | FanState::IdleOff | FanState::Fault
    )
}

/// May a new upload begin? Only once the fan is stopped or faulted and nobody asked for it to
/// run; the host's `Begin` is answered `Busy` (and retried) until then.
pub const fn accepts_upload(state: FanState, on: bool) -> bool {
    matches!(state, FanState::Fault) || (reset_safe(state) && !on)
}

/// The command that moves the fan toward a reset-safe state, if one is needed.
///
/// Never sent in `Fault`: any user command acknowledges a fault, and an update must not
/// silently clear one. `Off` also cancels a pending or running MPET.
pub const fn quiesce_command(state: FanState, on: bool) -> Option<Command> {
    if matches!(state, FanState::Fault) {
        return None;
    }
    if on || !reset_safe(state) {
        Some(Command::Off)
    } else {
        None
    }
}

/// What this boot has demonstrated so far. Every counter starts at zero on reset, so all of
/// it is evidence about the running image.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Evidence {
    /// Completed control-loop iterations.
    pub control_beats: u32,
    /// Successful MCF fault-status reads.
    pub mcf_status_reads: u32,
    /// The most recent MCF status read failed.
    pub mcf_status_failing: bool,
    /// The supervisor's state, from the latest telemetry; `None` before the first frame.
    pub state: Option<FanState>,
    pub config: ConfigCheck,
    /// The station is associated (RSSI readable).
    pub wifi_connected: bool,
    /// Matter requests served on the application endpoint (fan or OTA cluster). Proves IP,
    /// an operational CASE session and the interaction model, end to end.
    pub matter_requests: u32,
}

/// The first thing a new image has not yet demonstrated.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Missing {
    ControlLoop,
    McfStatus,
    /// Still in `SafeBoot`, or no telemetry yet.
    SafeBoot,
    Faulted,
    Config,
    Wifi,
    MatterRequest,
}

impl Missing {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::ControlLoop => "control loop not yet past safe boot",
            Self::McfStatus => "MCF status reads not healthy",
            Self::SafeBoot => "supervisor still in safe boot",
            Self::Faulted => "supervisor faulted",
            Self::Config => "MCF configuration does not permit operation",
            Self::Wifi => "Wi-Fi not associated",
            Self::MatterRequest => "no Matter request served",
        }
    }
}

/// May the running image mark itself good?
///
/// Requires the whole product working: the control loop and MCF bus alive, the supervisor out
/// of safe boot without a fault on a configuration that permits operation, and Matter serving
/// requests. A build that breaks any of these never confirms and is rolled back.
pub const fn check(evidence: &Evidence) -> Result<(), Missing> {
    if evidence.control_beats < MIN_CONTROL_BEATS {
        return Err(Missing::ControlLoop);
    }
    if evidence.mcf_status_reads < MIN_MCF_STATUS_READS || evidence.mcf_status_failing {
        return Err(Missing::McfStatus);
    }
    match evidence.state {
        None | Some(FanState::SafeBoot) => return Err(Missing::SafeBoot),
        Some(FanState::Fault) => return Err(Missing::Faulted),
        Some(_) => {}
    }
    if !evidence.config.permits_operation() {
        return Err(Missing::Config);
    }
    if !evidence.wifi_connected {
        return Err(Missing::Wifi);
    }
    if evidence.matter_requests == 0 {
        return Err(Missing::MatterRequest);
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::mcf_config::ConfigFault;

    const HEALTHY: Evidence = Evidence {
        control_beats: MIN_CONTROL_BEATS,
        mcf_status_reads: MIN_MCF_STATUS_READS,
        mcf_status_failing: false,
        state: Some(FanState::IdleOff),
        config: ConfigCheck::Verified,
        wifi_connected: true,
        matter_requests: 1,
    };

    #[test]
    fn a_working_device_confirms() {
        assert_eq!(check(&HEALTHY), Ok(()));
        let running = Evidence {
            state: Some(FanState::Running),
            ..HEALTHY
        };
        assert_eq!(check(&running), Ok(()));
    }

    #[test]
    fn confirmation_waits_past_the_safe_boot_hold() {
        assert!(u64::from(MIN_CONTROL_BEATS) * config::CONTROL_TICK_MS > config::SAFE_BOOT_HOLD_MS);
        let early = Evidence {
            control_beats: MIN_CONTROL_BEATS - 1,
            ..HEALTHY
        };
        assert_eq!(check(&early), Err(Missing::ControlLoop));
        for state in [None, Some(FanState::SafeBoot)] {
            assert_eq!(
                check(&Evidence { state, ..HEALTHY }),
                Err(Missing::SafeBoot)
            );
        }
    }

    #[test]
    fn every_broken_subsystem_blocks_confirmation() {
        let cases = [
            (
                Evidence {
                    mcf_status_reads: MIN_MCF_STATUS_READS - 1,
                    ..HEALTHY
                },
                Missing::McfStatus,
            ),
            (
                Evidence {
                    mcf_status_failing: true,
                    ..HEALTHY
                },
                Missing::McfStatus,
            ),
            (
                Evidence {
                    state: Some(FanState::Fault),
                    ..HEALTHY
                },
                Missing::Faulted,
            ),
            (
                Evidence {
                    config: ConfigCheck::Unverified,
                    ..HEALTHY
                },
                Missing::Config,
            ),
            (
                Evidence {
                    config: ConfigCheck::Failed(ConfigFault::Unreadable { address: 0 }),
                    ..HEALTHY
                },
                Missing::Config,
            ),
            (
                Evidence {
                    wifi_connected: false,
                    ..HEALTHY
                },
                Missing::Wifi,
            ),
            (
                Evidence {
                    matter_requests: 0,
                    ..HEALTHY
                },
                Missing::MatterRequest,
            ),
        ];
        for (evidence, missing) in cases {
            assert_eq!(check(&evidence), Err(missing), "{evidence:?}");
        }
    }

    #[test]
    fn only_stopped_or_faulted_states_are_reset_safe() {
        for state in [FanState::SafeBoot, FanState::IdleOff, FanState::Fault] {
            assert!(reset_safe(state), "{state:?}");
        }
        for state in [
            FanState::Starting,
            FanState::Running,
            FanState::MpetArming,
            FanState::Mpet,
            FanState::Stopping,
            FanState::Reversing,
        ] {
            assert!(!reset_safe(state), "{state:?}");
        }
    }

    #[test]
    fn quiesce_stops_drive_and_cancels_intent() {
        assert_eq!(quiesce_command(FanState::Running, true), Some(Command::Off));
        assert_eq!(quiesce_command(FanState::Mpet, false), Some(Command::Off));
        assert_eq!(
            quiesce_command(FanState::Reversing, true),
            Some(Command::Off)
        );
        // A standing On intent would restart the fan after safe boot: cancel it.
        assert_eq!(
            quiesce_command(FanState::SafeBoot, true),
            Some(Command::Off)
        );
        assert_eq!(quiesce_command(FanState::IdleOff, true), Some(Command::Off));
        assert_eq!(quiesce_command(FanState::IdleOff, false), None);
        // Stopping with intent already off still needs nothing new, but re-sending Off is
        // harmless and keeps the rule simple.
        assert_eq!(
            quiesce_command(FanState::Stopping, false),
            Some(Command::Off)
        );
    }

    #[test]
    fn uploads_wait_for_a_stopped_fan_without_on_intent() {
        assert!(accepts_upload(FanState::IdleOff, false));
        assert!(accepts_upload(FanState::SafeBoot, false));
        assert!(accepts_upload(FanState::Fault, false));
        // Faulted drive is revoked; a stale On intent cannot restart it before the reset.
        assert!(accepts_upload(FanState::Fault, true));
        assert!(!accepts_upload(FanState::IdleOff, true));
        assert!(!accepts_upload(FanState::SafeBoot, true));
        for state in [
            FanState::Starting,
            FanState::Running,
            FanState::MpetArming,
            FanState::Mpet,
            FanState::Stopping,
            FanState::Reversing,
        ] {
            assert!(!accepts_upload(state, false), "{state:?}");
        }
    }

    #[test]
    fn quiesce_never_acknowledges_a_fault() {
        assert_eq!(quiesce_command(FanState::Fault, true), None);
        assert_eq!(quiesce_command(FanState::Fault, false), None);
    }
}
