//! MCF8316D configuration interface (stub).
//!
//! The supervisor talks to the MCF8316D over I²C (GPIO0/1) for configuration and
//! diagnostics only; the MCF commutates phases and limits current on its own.
//! Register-level starting values live in `docs/controls.md` > "Initial MCF8316D
//! configuration"; they are commissioning seeds that MPET + scoped measurements
//! replace before EEPROM release.

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

/// Driver handle. Stub: gains an I²C bus + register read/write/verify once the
/// V1 board exists.
pub struct Mcf8316 {}

impl Mcf8316 {
    pub fn new() -> Self {
        // TODO: take the esp-hal I²C peripheral; verify device presence; apply
        // and read back the full configuration (latched Hi-Z faults, no auto
        // retry, AVS on, flux weakening + overmodulation off, 1.5 A limits,
        // 50 W bus power limit, 40 kHz PWM).
        Self {}
    }
}
