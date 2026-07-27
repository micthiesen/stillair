//! MCF8316D configuration interface.
//!
//! The supervisor talks to the MCF8316D over I²C for configuration and diagnostics only;
//! the MCF commutates phases and limits current on its own. Register-level starting values
//! live in `docs/controls.md` > "Initial MCF8316D configuration"; they are commissioning
//! seeds that MPET plus scoped measurements replace before EEPROM release.
//!
//! **The 24-bit control-word wire format is deliberately not implemented here yet.** The
//! encoding is D-generation-specific and getting a bit position wrong writes garbage into a
//! motor controller. It lands once it has been checked against the datasheet directly, and
//! the bus stays abstract until then: [`RegisterBus`] speaks addresses and values, so
//! everything built on top of it is already testable.

use crate::speed::MilliRpm;

/// Provisional register seeds (measured values win — see docs/controls.md).
pub mod seeds {
    /// MOTOR_RES seed: 1.35 Ω (phase-neutral, from 2.65 Ω line-to-line star).
    pub const MOTOR_RES: u8 = 0xB1;
    /// MOTOR_IND seed: 1.20 mH (phase-neutral, from 2.35 mH line-to-line star).
    pub const MOTOR_IND: u8 = 0xAE;
    /// MOTOR_BEMF_CONST seed: 320 mV/electrical-Hz. Unverified convention;
    /// treat strictly as a V1 commissioning guess.
    pub const MOTOR_BEMF_CONST: u8 = 0xCA;
    /// MAX_SPEED: decimal 360 = 60 electrical Hz = 180 mechanical RPM
    /// (TI scaling: electrical Hz = MAX_SPEED / 6). Verify against silicon rev.
    pub const MAX_SPEED: u16 = 0x0168;
}

/// TI's `MAX_SPEED` register scaling: electrical Hz = `MAX_SPEED` / 6.
pub const MAX_SPEED_PER_ELECTRICAL_HZ: u32 = 6;

/// Convert a `MAX_SPEED` register value to the mechanical speed it represents.
pub fn max_speed_to_milli_rpm(max_speed: u16, pole_pairs: u32) -> MilliRpm {
    if pole_pairs == 0 {
        return MilliRpm::ZERO;
    }
    // milli-RPM = (MAX_SPEED / 6) electrical Hz × 60 s/min ÷ pole pairs × 1000
    let numerator = u64::from(max_speed) * 60 * 1_000;
    let denominator = u64::from(MAX_SPEED_PER_ELECTRICAL_HZ) * u64::from(pole_pairs);
    MilliRpm((numerator / denominator).min(u64::from(u32::MAX)) as u32)
}

/// Inverse of [`max_speed_to_milli_rpm`], for deriving the register value from a limit.
pub fn milli_rpm_to_max_speed(rpm: MilliRpm, pole_pairs: u32) -> u16 {
    let numerator =
        u64::from(rpm.0) * u64::from(MAX_SPEED_PER_ELECTRICAL_HZ) * u64::from(pole_pairs);
    let denominator = 60 * 1_000;
    (numerator / denominator).min(u64::from(u16::MAX)) as u16
}

/// Abstract access to the MCF's register space.
///
/// Implemented over I²C on the target and by a fake in tests. Addresses and values are
/// passed through unencoded; framing is the implementation's problem.
// The auto-trait leakage the lint warns about is irrelevant here: the only implementors
// are a concrete I²C bus on the target and a fake in tests, neither of which is ever held
// across a `Send` boundary.
#[allow(async_fn_in_trait)]
pub trait RegisterBus {
    type Error;

    /// Read one register.
    async fn read(&mut self, address: u16) -> Result<u32, Self::Error>;

    /// Write one register. Callers that need the write to have stuck must read it back —
    /// this makes no such guarantee on its own.
    async fn write(&mut self, address: u16, value: u32) -> Result<(), Self::Error>;
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config;

    #[test]
    fn the_seeded_max_speed_is_the_documented_180_rpm_ceiling() {
        let rpm = max_speed_to_milli_rpm(seeds::MAX_SPEED, config::POLE_PAIRS);
        assert_eq!(rpm, MilliRpm::from_rpm(config::RPM_MCF_LIMIT));
    }

    #[test]
    fn max_speed_round_trips() {
        let limit = MilliRpm::from_rpm(config::RPM_MCF_LIMIT);
        let register = milli_rpm_to_max_speed(limit, config::POLE_PAIRS);
        assert_eq!(register, seeds::MAX_SPEED);
        assert_eq!(max_speed_to_milli_rpm(register, config::POLE_PAIRS), limit);
    }

    #[test]
    fn zero_pole_pairs_does_not_divide_by_zero() {
        assert_eq!(max_speed_to_milli_rpm(seeds::MAX_SPEED, 0), MilliRpm::ZERO);
    }
}
