//! MCF8316D configuration interface.
//!
//! The supervisor talks to the MCF8316D over I²C for configuration and diagnostics only;
//! the MCF commutates phases and limits current on its own. Register-level starting values
//! live in `docs/controls.md` > "Initial MCF8316D configuration"; they are commissioning
//! seeds that MPET plus scoped measurements replace before EEPROM release.
//!
//! The 24-bit control-word wire format is implemented here, derived from primary sources
//! rather than inferred — a wrong bit position writes garbage into a motor controller:
//!
//! - **MCF8316D datasheet SLLSFX9A** (Dec 2024, rev. May 2025) §7.6.2.1 Table 7-10 for the
//!   control-word field layout, Table 7-11 for `DLEN`, §7.6.2.2/7.6.2.3 for the transaction
//!   sequences and byte order, and Tables 7-12/7-13/7-14 for worked packet examples.
//! - **App note SLLA662**, *How to Program I²C for MCx83xx Device Family* (March 2025), for
//!   the CRC-8 parameters and its verification vector.
//! - §9.3.1 for `ALGO_CTRL1` (offset `0xEA`) and the `CLR_FLT` bit.
//!
//! Every encoding claim below is pinned by a test against TI's own published example bytes,
//! so a transcription error fails the build rather than the bench.

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

/// Register offsets used by the supervisor. These are `MEM_ADDR` values; all of them sit in
/// `MEM_SEC` = 0h / `MEM_PAGE` = 0h, the only section external users may touch
/// (datasheet §7.6.2.1). Every one is a 32-bit register.
pub mod reg {
    /// Gate-driver fault status (§9.1.1).
    pub const GATE_DRIVER_FAULT_STATUS: u16 = 0x0E0;
    /// Controller fault status (§9.1.2).
    pub const CONTROLLER_FAULT_STATUS: u16 = 0x0E2;
    /// System status (§9.2.1).
    pub const ALGO_STATUS: u16 = 0x0E4;
    /// Device control, home of `CLR_FLT` (§9.3.1).
    pub const ALGO_CTRL1: u16 = 0x0EA;
}

/// Value written to [`reg::ALGO_CTRL1`] to clear latched faults.
///
/// `CLR_FLT` is bit 29 and `CLR_FLT_RETRY_COUNT` is bit 28 (§9.3.1, Table 9-13). The
/// datasheet requires writing both together to also zero the automatic-retry counter; we
/// configure `AUTO_RETRY_TIMES` = 0 so the counter is moot, but writing the documented pair
/// costs nothing and keeps this correct if that ever changes.
///
/// Both bits are write-only and self-clearing, so this is a fire-and-forget write — reading
/// it back proves nothing. Latched faults can take **up to 200 ms** to clear afterwards
/// (§8.x note); the supervisor's ten-second safe-boot hold covers that comfortably.
pub const CLR_FLT_COMMAND: u32 = (1 << 29) | (1 << 28);

/// Default 7-bit I²C target address (SLLA662 §2.1). Configurable in `DEVICE_CONFIG1` and
/// only effective after an EEPROM write plus a power cycle, so bus-scan at first bring-up
/// rather than trusting this.
pub const DEFAULT_TARGET_ID: u8 = 0x01;

/// Width of the data phase, encoded in the control word's `DLEN` field (Table 7-11).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DataLen {
    Bits16 = 0b00,
    Bits32 = 0b01,
    /// Treated by the device as two successive 32-bit accesses, the second at `addr + 2`.
    Bits64 = 0b10,
}

impl DataLen {
    /// Number of data bytes on the wire.
    pub const fn bytes(self) -> usize {
        match self {
            Self::Bits16 => 2,
            Self::Bits32 => 4,
            Self::Bits64 => 8,
        }
    }
}

/// Direction of the access, encoded in `OP_R/W` (control word bit 23).
///
/// Note this is *not* the I²C R/W bit: every MCF8316D transaction begins by writing the
/// control word, so the I²C direction bit in the first byte is always 0 (§7.6.2.1).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Op {
    Write = 0,
    Read = 1,
}

/// The 24-bit control word that opens every MCF8316D transaction.
///
/// Layout (Table 7-10): `OP_R/W` CW23, `CRC_EN` CW22, `DLEN` CW21:20, `MEM_SEC` CW19:16,
/// `MEM_PAGE` CW15:12, `MEM_ADDR` CW11:0.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ControlWord {
    pub op: Op,
    pub crc: bool,
    pub len: DataLen,
    /// Only the low 12 bits are meaningful; higher bits belong to MEM_SEC/MEM_PAGE, which
    /// are always zero for externally accessible memory.
    pub address: u16,
}

impl ControlWord {
    /// A 32-bit access, the width of every register this firmware touches.
    pub const fn reg32(op: Op, address: u16, crc: bool) -> Self {
        Self {
            op,
            crc,
            len: DataLen::Bits32,
            address,
        }
    }

    /// The three control-word bytes, in transmission order (most significant first).
    pub const fn bytes(self) -> [u8; 3] {
        let word = ((self.op as u32) << 23)
            | ((self.crc as u32) << 22)
            | ((self.len as u32) << 20)
            // MEM_SEC (19:16) and MEM_PAGE (15:12) are zero for all externally
            // addressable memory, so the address contributes only its low 12 bits.
            | ((self.address as u32) & 0x0FFF);
        [(word >> 16) as u8, (word >> 8) as u8, word as u8]
    }
}

/// CRC-8 over an MCF8316D packet.
///
/// CCITT polynomial x⁸ + x² + x + 1 (0x07), initialised to 0xFF, MSB-first within each byte
/// (SLLA662 §2.2.1). The covered bytes differ by direction: a write covers
/// `{target,0} ‖ control word ‖ data`, a read covers `{target,0} ‖ control word ‖ {target,1}
/// ‖ data`.
pub fn crc8(bytes: &[u8]) -> u8 {
    let mut crc: u8 = 0xFF;
    for byte in bytes {
        crc ^= byte;
        for _ in 0..8 {
            crc = if crc & 0x80 != 0 {
                (crc << 1) ^ 0x07
            } else {
                crc << 1
            };
        }
    }
    crc
}

/// Encode a 32-bit register value into its four data bytes.
///
/// **Least significant byte first** (§7.6.2.2 step 4a) — the opposite of the control word's
/// byte order, which is the single easiest thing to get backwards here.
pub const fn data_bytes32(value: u32) -> [u8; 4] {
    value.to_le_bytes()
}

/// Decode four data bytes read back from the device, LSB first.
pub const fn value_from_bytes32(bytes: [u8; 4]) -> u32 {
    u32::from_le_bytes(bytes)
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

    // The control-word tests below reproduce TI's own published packets byte for byte. They
    // exist so a transcription error in the encoding fails `cargo test` rather than being
    // discovered by a motor controller receiving a write it never should have.

    #[test]
    fn datasheet_table_7_12_thirty_two_bit_write() {
        // "Example for 32-bit Write Operation: Address – 0x00000080, Data – 0x1234ABCD"
        // with CRC enabled. Published control-word bytes: 0x50 0x00 0x80.
        let cw = ControlWord::reg32(Op::Write, 0x080, true);
        assert_eq!(cw.bytes(), [0x50, 0x00, 0x80]);
        // "While sending data bytes, the LSB byte is sent first."
        assert_eq!(data_bytes32(0x1234_ABCD), [0xCD, 0xAB, 0x34, 0x12]);
    }

    #[test]
    fn datasheet_table_7_14_thirty_two_bit_read() {
        // Same address and CRC setting, read instead of write: 0xD0 0x00 0x80.
        let cw = ControlWord::reg32(Op::Read, 0x080, true);
        assert_eq!(cw.bytes(), [0xD0, 0x00, 0x80]);
        // Read-back bytes arrive LSB first and must reassemble to the published value.
        assert_eq!(value_from_bytes32([0xCD, 0xAB, 0x34, 0x12]), 0x1234_ABCD);
    }

    #[test]
    fn datasheet_table_7_13_sixty_four_bit_write() {
        // Only DLEN differs from Table 7-12: published bytes 0x60 0x00 0x80.
        let cw = ControlWord {
            op: Op::Write,
            crc: true,
            len: DataLen::Bits64,
            address: 0x080,
        };
        assert_eq!(cw.bytes(), [0x60, 0x00, 0x80]);
    }

    #[test]
    fn disabling_crc_clears_only_bit_22() {
        assert_eq!(
            ControlWord::reg32(Op::Write, 0x080, false).bytes(),
            [0x10, 0x00, 0x80]
        );
    }

    #[test]
    fn the_address_field_cannot_bleed_into_mem_sec_or_mem_page() {
        // MEM_SEC and MEM_PAGE must stay 0h: every other value is reserved. A caller
        // passing a full 16-bit address must not be able to set them.
        let cw = ControlWord::reg32(Op::Read, 0xFFFF, false);
        let [high, mid, low] = cw.bytes();
        assert_eq!(high & 0x0F, 0, "MEM_SEC was not zero");
        assert_eq!(mid & 0xF0, 0, "MEM_PAGE was not zero");
        assert_eq!((mid & 0x0F, low), (0x0F, 0xFF));
    }

    #[test]
    fn every_register_the_supervisor_uses_fits_the_address_field() {
        for address in [
            reg::GATE_DRIVER_FAULT_STATUS,
            reg::CONTROLLER_FAULT_STATUS,
            reg::ALGO_STATUS,
            reg::ALGO_CTRL1,
        ] {
            assert!(address <= 0x0FFF, "{address:#05x} overflows MEM_ADDR");
        }
    }

    #[test]
    fn crc8_matches_the_app_note_verification_vector() {
        // SLLA662 §2.2.1: "For input byte of 0x12, the CRC byte becomes 0x8D from the
        // initial value of 0xFF."
        assert_eq!(crc8(&[0x12]), 0x8D);
    }

    #[test]
    fn crc8_is_order_sensitive_and_covers_every_byte() {
        // A CRC that ignored its input, or that folded bytes commutatively, would still
        // pass the single-byte vector above.
        assert_ne!(crc8(&[0x12, 0x34]), crc8(&[0x34, 0x12]));
        assert_ne!(crc8(&[0x12, 0x34]), crc8(&[0x12]));
    }

    #[test]
    fn the_clear_fault_command_sets_both_documented_bits() {
        // §9.3.1 Table 9-13: CLR_FLT is bit 29, CLR_FLT_RETRY_COUNT is bit 28.
        assert_eq!(CLR_FLT_COMMAND, 0x3000_0000);
    }

    #[test]
    fn data_length_byte_counts_match_the_encoding() {
        assert_eq!((DataLen::Bits16 as u8, DataLen::Bits16.bytes()), (0b00, 2));
        assert_eq!((DataLen::Bits32 as u8, DataLen::Bits32.bytes()), (0b01, 4));
        assert_eq!((DataLen::Bits64 as u8, DataLen::Bits64.bytes()), (0b10, 8));
    }
}
