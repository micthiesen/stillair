//! The Matter FanControl mapping: cluster attributes in, supervisor commands out.
//!
//! Cluster 514 (0x0202) is what Apple Home actually drives — `FanMode`, `PercentSetting`,
//! `AirflowDirection` — and `docs/controls.md` > "Percent → RPM mapping" is the contract for
//! turning those into fan behaviour. The mapping lives here, in the host-testable crate,
//! rather than inside the rs-matter handler in `app/`, for the same reason the state machine
//! does: it is the part that can be *wrong*, and being wrong means the fan runs at a speed
//! nobody asked for. The rs-matter handler is transport.
//!
//! The percentage arithmetic itself is [`speed::percent_to_rpm`] and [`speed::rpm_to_percent`],
//! not a second copy of it — the SPEED-pin duty and the Matter slider must agree about what
//! "60%" means, and the only way to guarantee that is for there to be one implementation.
//!
//! Nothing here depends on rs-matter, deliberately. That crate arrives as a git dependency
//! with a `[patch.crates-io]` pin table (`docs/controls.md` > "Home integration"), and the
//! rule that keeps `stillair-core` buildable on a laptop forever is that no such dependency
//! reaches it. The numeric attribute encodings below are from the Matter Application Cluster
//! specification §4.4; the wire encoding of them is rs-matter's job.

use crate::console::Telemetry;
use crate::speed::{self, MilliRpm};
use crate::state::{Command, Direction};

/// `FanMode`, attribute 0x0000. The discrete steps a controller may send instead of a
/// percentage — Apple Home renders a continuous slider, but other controllers do not.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FanMode {
    Off = 0,
    Low = 1,
    Medium = 2,
    High = 3,
    /// "On" carries no speed: it means resume, which is exactly [`Command::On`].
    On = 4,
    /// Auto has no meaning for a fan with nothing to be automatic about, so it is accepted
    /// and treated as On rather than rejected — refusing a mode the cluster advertises would
    /// present as a broken accessory.
    Auto = 5,
}

impl FanMode {
    pub const fn from_raw(raw: u8) -> Option<Self> {
        match raw {
            0 => Some(Self::Off),
            1 => Some(Self::Low),
            2 => Some(Self::Medium),
            3 => Some(Self::High),
            4 => Some(Self::On),
            5 => Some(Self::Auto),
            // 6 is the deprecated Smart mode, and anything above it is not in the spec.
            _ => None,
        }
    }

    pub const fn as_raw(self) -> u8 {
        self as u8
    }

    /// The percentage a discrete mode stands for. `None` for the modes that carry no speed.
    pub const fn percent(self) -> Option<u8> {
        match self {
            Self::Off => Some(0),
            Self::Low => Some(33),
            Self::Medium => Some(66),
            Self::High => Some(100),
            Self::On | Self::Auto => None,
        }
    }
}

/// `AirflowDirection`, attribute 0x000B.
///
/// Whether Apple Home surfaces this at all is unconfirmed (`docs/controls.md` > "Home
/// integration"); the fallback is a second On/Off endpoint that flips direction. Either way
/// it lands on the same [`Direction`], so the fallback is a wiring change in `app/` and not a
/// behavioural one.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum AirflowDirection {
    /// The power-on direction, and the one every reported default falls back to.
    #[default]
    Forward = 0,
    Reverse = 1,
}

impl AirflowDirection {
    pub const fn from_raw(raw: u8) -> Option<Self> {
        match raw {
            0 => Some(Self::Forward),
            1 => Some(Self::Reverse),
            _ => None,
        }
    }

    pub const fn as_raw(self) -> u8 {
        self as u8
    }

    pub const fn to_direction(self) -> Direction {
        match self {
            Self::Forward => Direction::Forward,
            Self::Reverse => Direction::Reverse,
        }
    }

    pub const fn from_direction(direction: Direction) -> Self {
        match direction {
            Direction::Forward => Self::Forward,
            Direction::Reverse => Self::Reverse,
        }
    }
}

/// Everything the FanControl cluster reports, derived from one telemetry snapshot.
///
/// **Derived, never cached.** An earlier version of the handler kept its own copy of the
/// requested state, reasoning that `PercentSetting` is the controller's rather than the fan's.
/// That is true, but the controller is not its only source: the serial tuning console writes
/// the same commands into the same channel, and a fault clears the request outright. A cache
/// has no path back from either, so it would sit reporting "High" at a fan that faulted an
/// hour ago — and re-reporting would only re-serve the stale value. Deriving makes the
/// divergence unrepresentable, and puts the logic somewhere it can be tested without a radio.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct Reported {
    /// `PercentSetting`: what was asked for. Zero when the fan is off, because the standing
    /// speed is retained across an Off so a bare `On` can resume it.
    pub setting: u8,
    /// `PercentCurrent`: what the tachometer measures, in every state. A fan ramping down
    /// after an Off is still moving air for a minute or more, and reporting zero the instant
    /// the command lands would claim it had stopped when it plainly has not.
    pub current: u8,
    /// The direction *asked for*. The applied direction lags a reversal by the whole
    /// stop-verify-flip-restart sequence, and a toggle that springs back for a minute reads
    /// as a device that ignored you.
    pub direction: AirflowDirection,
    /// Whether the fan is meant to be on at all.
    pub on: bool,
}

/// Derive the reported attributes from a telemetry snapshot.
pub fn reported(telemetry: &Telemetry) -> Reported {
    Reported {
        setting: if telemetry.on {
            speed::rpm_to_percent(telemetry.target, telemetry.released_min)
        } else {
            0
        },
        current: speed::rpm_to_percent(telemetry.measured_fg, telemetry.released_min),
        direction: AirflowDirection::from_direction(telemetry.requested_direction),
        on: telemetry.on,
    }
}

/// The `FanMode` to report for a snapshot.
pub fn reported_mode(reported: Reported) -> FanMode {
    mode_for(reported.on, reported.setting)
}

/// What a `PercentSetting` write becomes. 0 is Off, not a speed of zero.
pub fn command_for_percent(percent: u8, released_min: MilliRpm) -> Command {
    match speed::percent_to_rpm(percent, released_min) {
        Some(rpm) => Command::SetSpeed(rpm),
        None => Command::Off,
    }
}

/// What a `FanMode` write becomes.
pub fn command_for_mode(mode: FanMode, released_min: MilliRpm) -> Command {
    match mode.percent() {
        Some(percent) => command_for_percent(percent, released_min),
        // On and Auto carry no speed, so they resume the last non-zero setting — precisely
        // the contract's "FanMode On without a percent write" clause.
        None => Command::On,
    }
}

/// What a `AirflowDirection` write becomes.
pub const fn command_for_direction(direction: AirflowDirection) -> Command {
    Command::SetDirection(direction.to_direction())
}

/// The `FanMode` to report back for a fan running at `percent`.
///
/// Reported as the nearest discrete step rather than always `On`, so a controller that shows
/// mode buttons highlights the one matching the speed. `Off` whenever the fan is not running,
/// regardless of the standing speed setting — the contract's "power-on is always off" rule
/// makes the stored setting a memory, not a state.
pub fn mode_for(running: bool, percent: u8) -> FanMode {
    if !running || percent == 0 {
        return FanMode::Off;
    }
    match percent {
        // The boundaries sit midway between the discrete modes' own percentages (33/66/100),
        // so a mode written by a controller reports back as the mode it wrote.
        1..=49 => FanMode::Low,
        50..=82 => FanMode::Medium,
        _ => FanMode::High,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config;
    use crate::state::FanState;

    fn min() -> MilliRpm {
        MilliRpm::from_rpm(config::RPM_USER_MIN_TARGET)
    }

    fn snapshot() -> Telemetry {
        Telemetry {
            uptime_ms: 0,
            state: FanState::Running,
            fault: None,
            on: true,
            target: MilliRpm::from_rpm(100),
            commanded: MilliRpm::from_rpm(100),
            measured_fg: MilliRpm::from_rpm(100),
            measured_hall: MilliRpm::from_rpm(100),
            duty: crate::speed::SpeedDuty(0),
            direction: Direction::Forward,
            requested_direction: Direction::Forward,
            released_min: MilliRpm::from_rpm(config::RPM_USER_MIN_TARGET),
            config: crate::mcf_config::ConfigCheck::Verified,
            dropped: 0,
        }
    }

    #[test]
    fn a_stopped_fan_reports_off_however_it_was_stopped() {
        // The bug this replaced a cache to prevent: a fault (or a `stop` typed at the serial
        // console, which never goes through Matter at all) leaves the standing speed setting
        // in place so a bare `On` can resume it. Reporting the setting as though it were the
        // state would show "High" in Apple Home at a fan that faulted an hour ago.
        let mut telemetry = snapshot();
        telemetry.on = false;
        telemetry.state = FanState::Fault;
        telemetry.fault = Some(crate::state::FaultReason::NoRotation);
        telemetry.measured_fg = MilliRpm::ZERO;

        let reported = reported(&telemetry);
        assert_eq!(reported.setting, 0);
        assert!(!reported.on);
        assert_eq!(reported_mode(reported), FanMode::Off);
        // ...while the standing target is still there for a resume.
        assert_eq!(telemetry.target, MilliRpm::from_rpm(100));
    }

    #[test]
    fn a_fan_ramping_down_still_reports_the_air_it_is_moving() {
        // `PercentCurrent` comes off the tachometer in every state. At 1.5 RPM/s a stop from
        // 170 RPM takes nearly two minutes, and reporting 0 the instant the command lands
        // would tell the user it had stopped while it was plainly still turning over the bed.
        let mut telemetry = snapshot();
        telemetry.on = false;
        telemetry.state = FanState::Stopping;
        telemetry.measured_fg = MilliRpm::from_rpm(150);

        let reported = reported(&telemetry);
        assert_eq!(reported.setting, 0, "the setting is off");
        assert!(reported.current > 80, "but it is still moving air");
    }

    #[test]
    fn a_reversal_reports_the_direction_asked_for_immediately() {
        // A reversal ramps to zero, verifies stopped, flips DIR and restarts — a minute or
        // more. Reporting the applied direction would spring the controller's toggle back.
        let mut telemetry = snapshot();
        telemetry.requested_direction = Direction::Reverse;
        telemetry.direction = Direction::Forward;
        assert_eq!(reported(&telemetry).direction, AirflowDirection::Reverse);
    }

    #[test]
    fn a_speed_set_from_the_console_is_reported_to_matter() {
        // The console writes into the same command channel Matter does. Anything that only
        // tracked Matter's own writes would never see this.
        let mut telemetry = snapshot();
        telemetry.on = true;
        telemetry.target = speed::percent_to_rpm(42, min()).unwrap();
        assert_eq!(reported(&telemetry).setting, 42);
    }

    #[test]
    fn percent_zero_is_off_rather_than_a_speed_of_zero() {
        // The difference matters: `SetSpeed(0)` and `Off` reach the same place, but a fan
        // that reports 0% while "on" is a state Apple Home renders as a broken accessory.
        assert_eq!(command_for_percent(0, min()), Command::Off);
        assert_eq!(
            command_for_percent(1, min()),
            Command::SetSpeed(MilliRpm::from_rpm(config::RPM_USER_MIN_TARGET))
        );
    }

    #[test]
    fn the_mapping_is_the_one_in_speed_not_a_second_copy() {
        // If these ever disagree, the Matter slider and the SPEED-pin duty would be working
        // from different ideas of what a percentage means.
        for percent in 1..=100u8 {
            assert_eq!(
                command_for_percent(percent, min()),
                Command::SetSpeed(speed::percent_to_rpm(percent, min()).unwrap()),
                "{percent}%"
            );
        }
    }

    #[test]
    fn discrete_modes_become_speeds_and_on_resumes() {
        assert_eq!(command_for_mode(FanMode::Off, min()), Command::Off);
        assert_eq!(command_for_mode(FanMode::On, min()), Command::On);
        assert_eq!(
            command_for_mode(FanMode::Auto, min()),
            Command::On,
            "Auto must not be silently dropped"
        );

        for mode in [FanMode::Low, FanMode::Medium, FanMode::High] {
            let percent = mode.percent().expect("a percentage");
            assert_eq!(
                command_for_mode(mode, min()),
                command_for_percent(percent, min()),
                "{mode:?}"
            );
        }
    }

    #[test]
    fn discrete_modes_are_ordered_and_distinct() {
        let speed = |mode: FanMode| match command_for_mode(mode, min()) {
            Command::SetSpeed(rpm) => rpm,
            other => panic!("{mode:?} produced {other:?}"),
        };
        assert!(speed(FanMode::Low) < speed(FanMode::Medium));
        assert!(speed(FanMode::Medium) < speed(FanMode::High));
    }

    #[test]
    fn a_mode_written_by_a_controller_reports_back_as_itself() {
        // The round trip a controller actually performs: write FanMode, read PercentCurrent,
        // read FanMode. Landing on a different mode than the one written makes the buttons
        // flicker between states.
        for mode in [FanMode::Low, FanMode::Medium, FanMode::High] {
            let percent = mode.percent().unwrap();
            let rpm = speed::percent_to_rpm(percent, min()).unwrap();
            let reported = speed::rpm_to_percent(rpm, min());
            assert_eq!(mode_for(true, reported), mode, "{mode:?} at {reported}%");
        }
    }

    #[test]
    fn a_stopped_fan_reports_off_whatever_its_stored_setting() {
        assert_eq!(mode_for(false, 100), FanMode::Off);
        assert_eq!(mode_for(false, 0), FanMode::Off);
        assert_eq!(mode_for(true, 0), FanMode::Off);
        assert_eq!(mode_for(true, 1), FanMode::Low);
        assert_eq!(mode_for(true, 100), FanMode::High);
    }

    #[test]
    fn direction_maps_both_ways_without_losing_a_value() {
        for direction in [Direction::Forward, Direction::Reverse] {
            let attribute = AirflowDirection::from_direction(direction);
            assert_eq!(attribute.to_direction(), direction);
            assert_eq!(
                command_for_direction(attribute),
                Command::SetDirection(direction)
            );
        }
    }

    #[test]
    fn attribute_encodings_round_trip_and_reject_what_is_not_in_the_spec() {
        for raw in 0..=5u8 {
            assert_eq!(
                FanMode::from_raw(raw).expect("a defined mode").as_raw(),
                raw
            );
        }
        // 6 is the deprecated Smart mode; the cluster we advertise does not include it.
        assert_eq!(FanMode::from_raw(6), None);
        assert_eq!(FanMode::from_raw(255), None);

        for raw in 0..=1u8 {
            let direction = AirflowDirection::from_raw(raw).expect("a defined direction");
            assert_eq!(direction.as_raw(), raw);
        }
        assert_eq!(AirflowDirection::from_raw(2), None);
    }

    #[test]
    fn no_percentage_a_controller_can_send_escapes_the_layered_limits() {
        // The Matter surface must not be a way around the limits the rest of the system
        // enforces — including the out-of-spec values a misbehaving controller can put in a
        // u8. `Supervisor::command` clamps too; this fails in a test rather than on a rotor.
        for percent in 0..=255u8 {
            if let Command::SetSpeed(rpm) = command_for_percent(percent, min()) {
                assert!(rpm.whole_rpm() <= config::RPM_USER_MAX, "{percent}%");
                assert!(rpm.whole_rpm() < config::RPM_MCF_LIMIT, "{percent}%");
                assert!(rpm >= min(), "{percent}% fell below the released minimum");
            }
        }
    }

    #[test]
    fn a_raised_released_minimum_moves_the_whole_slider() {
        // Qualification may release a floor above the 35 RPM target; the bottom of the
        // slider must move with it rather than becoming dead travel.
        let raised = MilliRpm::from_rpm(55);
        assert_eq!(command_for_percent(1, raised), Command::SetSpeed(raised));
        for percent in 1..=100u8 {
            let Command::SetSpeed(rpm) = command_for_percent(percent, raised) else {
                panic!("{percent}% was not a speed");
            };
            assert!(rpm >= raised, "{percent}%");
        }
    }
}
