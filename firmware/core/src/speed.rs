//! Speed representations and the conversions between them.
//!
//! Four units meet in this project and confusing them is the easiest way to command the
//! wrong speed: Matter's `PercentSetting` (1–100 over the *released* user range),
//! mechanical RPM, MCF SPEED-pin duty (a fraction of the stored 180 RPM ceiling), and FG
//! pulse counts. Everything crosses through [`MilliRpm`].

use crate::config;

/// Mechanical shaft speed in thousandths of an RPM. Integer throughout — the C6 has no
/// FPU, and milli-RPM resolves the 35–170 RPM range far past anything the fan can hold.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Default)]
pub struct MilliRpm(pub u32);

impl MilliRpm {
    pub const ZERO: Self = Self(0);

    pub const fn from_rpm(rpm: u32) -> Self {
        Self(rpm * 1_000)
    }

    pub const fn is_zero(self) -> bool {
        self.0 == 0
    }

    /// Rounded to the nearest whole RPM, for logs and telemetry.
    pub const fn whole_rpm(self) -> u32 {
        (self.0 + 500) / 1_000
    }
}

/// Duty commanded on the MCF SPEED pin, in units of 1/[`config::SPEED_DUTY_FULL_SCALE`].
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Default)]
pub struct SpeedDuty(pub u16);

impl SpeedDuty {
    pub const ZERO: Self = Self(0);
}

/// Convert a mechanical speed command into SPEED-pin duty.
///
/// `SPEED_MODE` = 01b means commanded speed = duty × `MAX_SPEED`, and `MAX_SPEED` is the
/// stored 180 RPM ceiling. Speeds above that ceiling clamp rather than wrap; the MCF
/// enforces the same limit independently, and the analog chain enforces 200 RPM above
/// both.
pub fn duty_for(rpm: MilliRpm) -> SpeedDuty {
    let ceiling = config::RPM_MCF_LIMIT * 1_000;
    let clamped = rpm.0.min(ceiling);
    let duty = (u64::from(clamped) * u64::from(config::SPEED_DUTY_FULL_SCALE)) / u64::from(ceiling);
    SpeedDuty(duty as u16)
}

/// Matter `PercentSetting` → speed. 0 means Off (hence `None`); 1–100 maps linearly onto
/// `[released_min, RPM_USER_MAX]`, so 1 is exactly the released minimum and 100 is exactly
/// the user maximum.
///
/// `released_min` is a parameter, never a constant: the actual minimum is released only
/// after the start and acoustic matrix passes and may land above the 35 RPM target.
pub fn percent_to_rpm(percent: u8, released_min: MilliRpm) -> Option<MilliRpm> {
    if percent == 0 {
        return None;
    }
    let percent = u32::from(percent.min(100));
    let min = released_min.0;
    let span = (config::RPM_USER_MAX * 1_000).saturating_sub(min);
    Some(MilliRpm(min + (span * (percent - 1)) / 99))
}

/// Inverse of [`percent_to_rpm`], for reporting `PercentCurrent`. Rounds to nearest, and
/// never reports 0 for a nonzero speed (0 is reserved for Off).
pub fn rpm_to_percent(rpm: MilliRpm, released_min: MilliRpm) -> u8 {
    if rpm.is_zero() {
        return 0;
    }
    let min = released_min.0;
    let span = (config::RPM_USER_MAX * 1_000).saturating_sub(min);
    if span == 0 {
        return 100;
    }
    let above = rpm.0.saturating_sub(min);
    let pct = 1 + (above * 99 + span / 2) / span;
    pct.min(100) as u8
}

/// Integrate a pulse count into a speed estimate.
///
/// Used for both tach channels: FG at 20 pulses/rev and the rotor Hall at 1 pulse/rev.
/// Returns zero for a zero-length window rather than dividing by it.
pub fn milli_rpm_from_pulses(pulses: u32, window_ms: u64, pulses_per_rev: u32) -> MilliRpm {
    if window_ms == 0 || pulses_per_rev == 0 {
        return MilliRpm::ZERO;
    }
    // revs/min × 1000 = pulses / ppr / (window_ms / 60_000) × 1000
    let numerator = u64::from(pulses) * 60_000_000;
    let denominator = u64::from(pulses_per_rev) * window_ms;
    MilliRpm((numerator / denominator).min(u64::from(u32::MAX)) as u32)
}

/// A rate-limited approach to a target speed.
///
/// Accumulates elapsed time rather than converting each tick independently, so the ramp
/// rate is honoured exactly regardless of how coarsely or irregularly the control loop
/// polls — a 10 ms tick at 1.5 RPM/s would otherwise truncate to zero movement forever.
#[derive(Debug, Clone, Copy)]
pub struct Ramp {
    current: MilliRpm,
    target: MilliRpm,
    residual_ms: u64,
}

impl Ramp {
    pub const fn new() -> Self {
        Self {
            current: MilliRpm::ZERO,
            target: MilliRpm::ZERO,
            residual_ms: 0,
        }
    }

    pub fn set_target(&mut self, target: MilliRpm) {
        self.target = target;
    }

    pub const fn current(&self) -> MilliRpm {
        self.current
    }

    pub const fn target(&self) -> MilliRpm {
        self.target
    }

    pub const fn at_target(&self) -> bool {
        self.current.0 == self.target.0
    }

    /// Force the ramp back to a standstill. Only legal where the rotor is known stopped.
    pub fn reset(&mut self) {
        self.current = MilliRpm::ZERO;
        self.target = MilliRpm::ZERO;
        self.residual_ms = 0;
    }

    /// Advance by `dt_ms` and return the new commanded speed.
    pub fn step(&mut self, dt_ms: u64) -> MilliRpm {
        if self.at_target() {
            self.residual_ms = 0;
            return self.current;
        }
        self.residual_ms = self.residual_ms.saturating_add(dt_ms);
        let step = (self.residual_ms * u64::from(config::RAMP_MILLI_RPM_PER_S)) / 1_000;
        if step == 0 {
            return self.current;
        }
        // Consume only the time the emitted step actually paid for, so truncation
        // accumulates instead of being discarded.
        let consumed = (step * 1_000) / u64::from(config::RAMP_MILLI_RPM_PER_S);
        self.residual_ms = self.residual_ms.saturating_sub(consumed);

        let step = step.min(u64::from(u32::MAX)) as u32;
        self.current = if self.current < self.target {
            MilliRpm(self.current.0.saturating_add(step).min(self.target.0))
        } else {
            MilliRpm(self.current.0.saturating_sub(step).max(self.target.0))
        };
        self.current
    }
}

impl Default for Ramp {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const MIN: MilliRpm = MilliRpm::from_rpm(35);

    #[test]
    fn duty_maps_speed_onto_the_stored_ceiling() {
        assert_eq!(duty_for(MilliRpm::ZERO), SpeedDuty(0));
        // 170 of 180 RPM = 94.4% of full scale.
        assert_eq!(duty_for(MilliRpm::from_rpm(170)), SpeedDuty(1934));
        assert_eq!(duty_for(MilliRpm::from_rpm(180)), SpeedDuty(2048));
    }

    #[test]
    fn duty_clamps_above_the_stored_ceiling_instead_of_wrapping() {
        assert_eq!(duty_for(MilliRpm::from_rpm(500)), SpeedDuty(2048));
    }

    #[test]
    fn percent_zero_is_off_and_the_endpoints_are_exact() {
        assert_eq!(percent_to_rpm(0, MIN), None);
        assert_eq!(percent_to_rpm(1, MIN), Some(MilliRpm::from_rpm(35)));
        assert_eq!(percent_to_rpm(100, MIN), Some(MilliRpm::from_rpm(170)));
    }

    #[test]
    fn percent_mapping_is_monotonic_and_stays_in_the_user_range() {
        let mut previous = MilliRpm::ZERO;
        for percent in 1..=100u8 {
            let rpm = percent_to_rpm(percent, MIN).unwrap();
            assert!(rpm >= previous, "percent {percent} went backwards");
            assert!(rpm >= MilliRpm::from_rpm(35));
            assert!(rpm <= MilliRpm::from_rpm(config::RPM_USER_MAX));
            previous = rpm;
        }
    }

    #[test]
    fn percent_round_trips_through_rpm() {
        for percent in 1..=100u8 {
            let rpm = percent_to_rpm(percent, MIN).unwrap();
            assert_eq!(rpm_to_percent(rpm, MIN), percent, "percent {percent}");
        }
        assert_eq!(rpm_to_percent(MilliRpm::ZERO, MIN), 0);
    }

    #[test]
    fn percent_honours_a_released_minimum_above_the_target() {
        let released = MilliRpm::from_rpm(45);
        assert_eq!(percent_to_rpm(1, released), Some(MilliRpm::from_rpm(45)));
        assert_eq!(percent_to_rpm(100, released), Some(MilliRpm::from_rpm(170)));
    }

    #[test]
    fn pulses_convert_at_both_tach_ratios() {
        // 20 FG pulses in one second = one rev/s = 60 RPM.
        assert_eq!(
            milli_rpm_from_pulses(20, 1_000, config::FG_PULSES_PER_REV),
            MilliRpm::from_rpm(60)
        );
        // The rotor Hall is one pulse per rev.
        assert_eq!(
            milli_rpm_from_pulses(1, 1_000, config::HALL_PULSES_PER_REV),
            MilliRpm::from_rpm(60)
        );
    }

    #[test]
    fn pulses_over_a_zero_window_do_not_divide_by_zero() {
        assert_eq!(
            milli_rpm_from_pulses(5, 0, config::FG_PULSES_PER_REV),
            MilliRpm::ZERO
        );
    }

    #[test]
    fn ramp_honours_the_rate_regardless_of_tick_size() {
        for tick in [1u64, 7, 10, 100, 250] {
            let mut ramp = Ramp::new();
            ramp.set_target(MilliRpm::from_rpm(100));
            let mut elapsed = 0;
            while !ramp.at_target() {
                ramp.step(tick);
                elapsed += tick;
                assert!(elapsed < 200_000, "tick {tick} never converged");
            }
            // 100 RPM at 1.5 RPM/s is 66.7 s; allow one tick of quantisation.
            let expected = 100_000 * 1_000 / u64::from(config::RAMP_MILLI_RPM_PER_S);
            assert!(
                elapsed >= expected && elapsed <= expected + tick,
                "tick {tick} took {elapsed} ms, expected ~{expected} ms"
            );
        }
    }

    #[test]
    fn ramp_never_exceeds_the_rate_over_any_interval() {
        let mut ramp = Ramp::new();
        ramp.set_target(MilliRpm::from_rpm(170));
        let mut previous = MilliRpm::ZERO;
        for _ in 0..1_000 {
            let now = ramp.step(100);
            let delta = now.0 - previous.0;
            assert!(delta <= config::RAMP_MILLI_RPM_PER_S / 10, "step {delta}");
            previous = now;
        }
    }

    #[test]
    fn ramp_descends_to_zero_and_stops_there() {
        let mut ramp = Ramp::new();
        ramp.set_target(MilliRpm::from_rpm(50));
        while !ramp.at_target() {
            ramp.step(100);
        }
        ramp.set_target(MilliRpm::ZERO);
        while !ramp.at_target() {
            ramp.step(100);
        }
        assert_eq!(ramp.current(), MilliRpm::ZERO);
        ramp.step(100);
        assert_eq!(ramp.current(), MilliRpm::ZERO);
    }
}
