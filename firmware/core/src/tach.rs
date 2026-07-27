//! Rotor speed sensing and the plausibility rules built on it.
//!
//! Two independent channels report rotation: the MCF's FG output at 20 pulses/rev, and
//! the rotor Hall at 1 pulse/rev (the same pickup the analog overspeed chain integrates).
//! Neither is trusted alone. Their disagreement is the only backstop for the documented
//! Hall-cable/magnet single-point failure, and their joint silence is the definition of
//! "verified stopped" that gates every direction change (`docs/controls.md`).

use crate::config;
use crate::speed::{milli_rpm_from_pulses, MilliRpm};
use crate::time::Millis;

/// One pulse-counting input, tracked as a monotonic total plus a windowed rate.
#[derive(Debug, Clone, Copy)]
struct Channel {
    pulses_per_rev: u32,
    /// Last raw counter value seen from hardware. Free-running and allowed to wrap.
    last_raw: u32,
    /// Wrap-corrected running total, so callers can compare snapshots safely.
    total: u64,
    last_change: Millis,
    window_start: Millis,
    window_pulses: u32,
    estimate: MilliRpm,
}

impl Channel {
    fn new(pulses_per_rev: u32, raw: u32, now: Millis) -> Self {
        Self {
            pulses_per_rev,
            last_raw: raw,
            total: 0,
            last_change: now,
            window_start: now,
            window_pulses: 0,
            estimate: MilliRpm::ZERO,
        }
    }

    /// Fold a new raw counter reading in; returns how many pulses arrived.
    fn update(&mut self, raw: u32, now: Millis) -> u32 {
        let delta = raw.wrapping_sub(self.last_raw);
        self.last_raw = raw;
        self.total = self.total.saturating_add(u64::from(delta));
        if delta > 0 {
            self.last_change = now;
        }
        self.window_pulses = self.window_pulses.saturating_add(delta);

        let window = now.since(self.window_start);
        if window >= config::SPEED_ESTIMATE_WINDOW_MS {
            self.estimate = milli_rpm_from_pulses(self.window_pulses, window, self.pulses_per_rev);
            self.window_start = now;
            self.window_pulses = 0;
        }
        delta
    }

    fn silent_for(&self, now: Millis) -> u64 {
        now.since(self.last_change)
    }
}

/// Both tach channels, plus the cross-check between them.
#[derive(Debug, Clone, Copy)]
pub struct Tach {
    fg: Channel,
    hall: Channel,
    /// FG pulses accumulated since the last Hall edge. The Hall-loss detector.
    fg_since_hall: u32,
}

impl Tach {
    pub fn new(fg_raw: u32, hall_raw: u32, now: Millis) -> Self {
        Self {
            fg: Channel::new(config::FG_PULSES_PER_REV, fg_raw, now),
            hall: Channel::new(config::HALL_PULSES_PER_REV, hall_raw, now),
            fg_since_hall: 0,
        }
    }

    pub fn update(&mut self, fg_raw: u32, hall_raw: u32, now: Millis) {
        let fg_delta = self.fg.update(fg_raw, now);
        let hall_delta = self.hall.update(hall_raw, now);
        if hall_delta > 0 {
            self.fg_since_hall = 0;
        } else {
            self.fg_since_hall = self.fg_since_hall.saturating_add(fg_delta);
        }
    }

    /// Wrap-corrected FG total. Snapshot it and compare later to ask "did the rotor move
    /// at all since then?" without inventing a motion-detection window.
    pub const fn fg_total(&self) -> u64 {
        self.fg.total
    }

    pub const fn hall_total(&self) -> u64 {
        self.hall.total
    }

    /// Best available speed estimate, from FG (20× the resolution of the Hall channel).
    pub const fn measured(&self) -> MilliRpm {
        self.fg.estimate
    }

    /// The independent Hall estimate, for telemetry and for eyeballing FG agreement.
    pub const fn measured_hall(&self) -> MilliRpm {
        self.hall.estimate
    }

    /// "Verified stopped": neither channel has produced an edge for the full quiet
    /// window. This is the gate on every direction change, and on arming.
    pub fn is_quiet(&self, now: Millis) -> bool {
        self.fg.silent_for(now) >= config::STOPPED_QUIET_MS
            && self.hall.silent_for(now) >= config::STOPPED_QUIET_MS
    }

    /// FG says the rotor is turning while the Hall channel has stayed silent for more
    /// than the allowed number of revolutions — the Hall pickup, its magnet, or its cable
    /// has failed, and the analog overspeed chain is therefore blind. The fan must stop.
    pub const fn hall_implausible(&self) -> bool {
        self.fg_since_hall > config::HALL_PLAUSIBILITY_REVS * config::FG_PULSES_PER_REV
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn spin(tach: &mut Tach, now: &mut Millis, revs: u32, ms_per_rev: u64) {
        let mut fg = tach.fg.last_raw;
        let mut hall = tach.hall.last_raw;
        for _ in 0..revs {
            for _ in 0..config::FG_PULSES_PER_REV {
                fg = fg.wrapping_add(1);
                *now = now.plus_ms(ms_per_rev / u64::from(config::FG_PULSES_PER_REV));
                tach.update(fg, hall, *now);
            }
            hall = hall.wrapping_add(1);
            tach.update(fg, hall, *now);
        }
    }

    #[test]
    fn silence_on_both_channels_is_verified_stopped() {
        let mut now = Millis::ZERO;
        let tach = Tach::new(0, 0, now);
        assert!(
            !tach.is_quiet(now),
            "quiet cannot be true the instant we look"
        );
        now = now.plus_ms(config::STOPPED_QUIET_MS - 1);
        assert!(!tach.is_quiet(now));
        now = now.plus_ms(1);
        assert!(tach.is_quiet(now));
    }

    #[test]
    fn a_single_fg_edge_restarts_the_quiet_window() {
        let mut now = Millis::ZERO;
        let mut tach = Tach::new(0, 0, now);
        now = now.plus_ms(config::STOPPED_QUIET_MS);
        assert!(tach.is_quiet(now));
        tach.update(1, 0, now);
        assert!(!tach.is_quiet(now));
        now = now.plus_ms(config::STOPPED_QUIET_MS);
        assert!(tach.is_quiet(now));
    }

    #[test]
    fn a_single_hall_edge_alone_also_blocks_quiet() {
        let mut now = Millis::ZERO;
        let mut tach = Tach::new(0, 0, now);
        now = now.plus_ms(config::STOPPED_QUIET_MS);
        tach.update(0, 1, now);
        assert!(!tach.is_quiet(now));
    }

    #[test]
    fn healthy_rotation_never_looks_implausible() {
        let mut now = Millis::ZERO;
        let mut tach = Tach::new(0, 0, now);
        spin(&mut tach, &mut now, 50, 1_000);
        assert!(!tach.hall_implausible());
        assert_eq!(tach.fg_total(), 50 * u64::from(config::FG_PULSES_PER_REV));
        assert_eq!(tach.hall_total(), 50);
    }

    #[test]
    fn fg_turning_without_hall_edges_trips_the_plausibility_check() {
        let now = Millis::ZERO;
        let mut tach = Tach::new(0, 0, now);
        let allowed = config::HALL_PLAUSIBILITY_REVS * config::FG_PULSES_PER_REV;
        for pulse in 1..=allowed {
            tach.update(pulse, 0, now);
            assert!(!tach.hall_implausible(), "tripped early at pulse {pulse}");
        }
        tach.update(allowed + 1, 0, now);
        assert!(tach.hall_implausible());
    }

    #[test]
    fn a_hall_edge_resets_the_implausibility_accumulator() {
        let now = Millis::ZERO;
        let mut tach = Tach::new(0, 0, now);
        let allowed = config::HALL_PLAUSIBILITY_REVS * config::FG_PULSES_PER_REV;
        tach.update(allowed, 0, now);
        tach.update(allowed, 1, now);
        tach.update(allowed * 2, 1, now);
        assert!(!tach.hall_implausible());
    }

    #[test]
    fn fg_and_hall_estimates_agree_on_a_healthy_rotor() {
        let mut now = Millis::ZERO;
        let mut tach = Tach::new(0, 0, now);
        // 1000 ms per rev = 60 RPM.
        spin(&mut tach, &mut now, 10, 1_000);
        assert_eq!(tach.measured().whole_rpm(), 60);
        assert_eq!(tach.measured_hall().whole_rpm(), 60);
    }

    #[test]
    fn counters_that_wrap_do_not_produce_a_speed_spike() {
        let mut now = Millis::ZERO;
        let mut tach = Tach::new(u32::MAX - 2, 0, now);
        now = now.plus_ms(config::SPEED_ESTIMATE_WINDOW_MS);
        // Three pulses that happen to straddle the u32 boundary.
        tach.update(0, 0, now);
        assert_eq!(tach.fg_total(), 3);
        assert!(tach.measured().whole_rpm() < 60);
    }
}
