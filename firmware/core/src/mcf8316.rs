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

/// Bits of [`reg::GATE_DRIVER_FAULT_STATUS`] (§9.1.1, Table 9-3). Only the ones the
/// supervisor acts on or reports are named; the rest are per-phase overcurrent detail that
/// `OCP` already summarises.
pub mod gate_fault {
    /// Logic OR of every gate-driver fault bit.
    pub const DRIVER_FAULT: u32 = 1 << 31;
    pub const OCP: u32 = 1 << 28;
    /// Supply (VM) overvoltage.
    pub const OVP: u32 = 1 << 26;
    /// Overtemperature *warning* — advisory in silicon, a stop for us.
    pub const OTW: u32 = 1 << 23;
    /// Overtemperature shutdown. Auto-recovers by silicon design and cannot be latched.
    pub const OTS: u32 = 1 << 22;
    pub const BUCK_OCP: u32 = 1 << 13;
    pub const BUCK_UV: u32 = 1 << 12;
    /// Charge-pump undervoltage.
    pub const VCP_UV: u32 = 1 << 11;
}

/// Bits of [`reg::CONTROLLER_FAULT_STATUS`] (§9.1.2).
pub mod controller_fault {
    /// Logic OR of every controller fault bit.
    pub const CONTROLLER_FAULT: u32 = 1 << 31;
    pub const IPD_FREQ_FAULT: u32 = 1 << 29;
    pub const IPD_T1_FAULT: u32 = 1 << 28;
    pub const IPD_T2_FAULT: u32 = 1 << 27;
    pub const MPET_IPD_FAULT: u32 = 1 << 25;
    pub const MPET_BEMF_FAULT: u32 = 1 << 24;
    /// Abnormal-speed motor lock.
    pub const ABN_SPEED: u32 = 1 << 23;
    /// Abnormal-BEMF motor lock.
    pub const ABN_BEMF: u32 = 1 << 22;
    /// No motor / loss of phase.
    pub const NO_MTR: u32 = 1 << 21;
    /// Summary of the motor-lock conditions.
    pub const MTR_LCK: u32 = 1 << 20;
    pub const LOCK_LIMIT: u32 = 1 << 19;
    pub const HW_LOCK_LIMIT: u32 = 1 << 18;
    /// Configurable undervoltage on VM — the windmill/back-feed case of DRV-09.
    pub const MTR_UNDER_VOLTAGE: u32 = 1 << 17;
    /// Configurable overvoltage on VM.
    pub const MTR_OVER_VOLTAGE: u32 = 1 << 16;
    pub const EEPROM_WRITE_LOCK: u32 = 1 << 11;
    pub const EEPROM_READ_LOCK: u32 = 1 << 10;
    /// CRC fault in an I²C packet — our own framing is wrong if this ever sets.
    pub const I2C_CRC_FAULT: u32 = 1 << 6;
    pub const EEPROM_ERR: u32 = 1 << 5;
    pub const BOOT_STL_FAULT: u32 = 1 << 4;
    /// The MCF's own watchdog timed out (the EXT_WDT path).
    pub const WATCHDOG_FAULT: u32 = 1 << 3;
    pub const CPU_RESET_FAULT: u32 = 1 << 2;
    pub const WWDT_FAULT: u32 = 1 << 1;

    /// Every condition that means "the rotor is not turning the way it was told to".
    pub const ANY_LOCK: u32 = ABN_SPEED | ABN_BEMF | NO_MTR | MTR_LCK | LOCK_LIMIT | HW_LOCK_LIMIT;
    /// Every condition that means "the start attempt itself failed".
    pub const ANY_START: u32 =
        IPD_FREQ_FAULT | IPD_T1_FAULT | IPD_T2_FAULT | MPET_IPD_FAULT | MPET_BEMF_FAULT;
}

/// A decoded snapshot of both fault-status registers.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct FaultStatus {
    pub gate: u32,
    pub controller: u32,
}

/// What the MCF is complaining about, reduced to the distinctions the supervisor's response
/// and the failure table actually turn on.
///
/// Ordered by how specific the diagnosis is, not by severity: every one of these produces
/// the same response (speed zero, permission revoked, fresh command required), so the only
/// job of this enum is to tell the owner what happened.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum McfCondition {
    /// Bus undervoltage. Windmilling BEMF back-feed can lift VM above the auto-recovery
    /// point and chatter the drive, which is why this is a stop and not a wait (DRV-09).
    Undervoltage,
    Overvoltage,
    /// OTW or OTS. TSD auto-recovers by silicon design and cannot be latched, so firmware
    /// treats any thermal report as a stop rather than trusting the latch.
    Overtemperature,
    Overcurrent,
    /// Abnormal speed/BEMF, loss of phase, or a lock current limit.
    MotorLock,
    /// The start attempt failed (IPD or MPET).
    StartFailed,
    /// The MCF's own external-watchdog timeout fired.
    McfWatchdog,
    /// EEPROM error or lock — the stored configuration cannot be trusted.
    Eeprom,
    /// The MCF rejected one of our packets' CRC: our framing is wrong, not the motor.
    ProtocolError,
    /// A fault bit is set that none of the above covers.
    Unclassified,
}

impl FaultStatus {
    pub const fn new(gate: u32, controller: u32) -> Self {
        Self { gate, controller }
    }

    /// True if either register reports anything at all.
    pub const fn any(self) -> bool {
        self.gate != 0 || self.controller != 0
    }

    /// Reduce the two registers to a single reportable condition.
    ///
    /// Order matters only for reporting. Supply problems come first because they explain
    /// everything downstream of them — an undervoltage will also trip a lock, and naming
    /// the lock would send the owner looking at the wrong thing.
    pub const fn condition(self) -> Option<McfCondition> {
        use controller_fault as cf;
        use gate_fault as gf;

        if !self.any() {
            return None;
        }
        if self.controller & cf::MTR_UNDER_VOLTAGE != 0
            || self.gate & (gf::BUCK_UV | gf::VCP_UV) != 0
        {
            return Some(McfCondition::Undervoltage);
        }
        if self.controller & cf::MTR_OVER_VOLTAGE != 0 || self.gate & gf::OVP != 0 {
            return Some(McfCondition::Overvoltage);
        }
        if self.gate & (gf::OTW | gf::OTS) != 0 {
            return Some(McfCondition::Overtemperature);
        }
        if self.gate & (gf::OCP | gf::BUCK_OCP) != 0 {
            return Some(McfCondition::Overcurrent);
        }
        if self.controller & cf::ANY_LOCK != 0 {
            return Some(McfCondition::MotorLock);
        }
        if self.controller & cf::ANY_START != 0 {
            return Some(McfCondition::StartFailed);
        }
        if self.controller & (cf::WATCHDOG_FAULT | cf::WWDT_FAULT | cf::CPU_RESET_FAULT) != 0 {
            return Some(McfCondition::McfWatchdog);
        }
        if self.controller & (cf::EEPROM_ERR | cf::EEPROM_WRITE_LOCK | cf::EEPROM_READ_LOCK) != 0 {
            return Some(McfCondition::Eeprom);
        }
        if self.controller & cf::I2C_CRC_FAULT != 0 {
            return Some(McfCondition::ProtocolError);
        }
        Some(McfCondition::Unclassified)
    }
}

/// Longest payload: three control-word bytes, four data bytes, one CRC byte.
pub const MAX_FRAME: usize = 8;

/// The I²C payload for a register write, ready to hand to a bus that supplies the address
/// byte itself.
///
/// `target` is the 7-bit address. When CRC is enabled the checksum covers `{target, 0}`
/// followed by this payload, so the address byte is folded in here even though the bus
/// transmits it separately.
pub fn write_frame(
    target: u8,
    address: u16,
    value: u32,
    crc: bool,
) -> heapless::Vec<u8, MAX_FRAME> {
    let mut frame = heapless::Vec::new();
    let control = ControlWord::reg32(Op::Write, address, crc);
    // Capacity is MAX_FRAME by construction: 3 + 4 + 1.
    let _ = frame.extend_from_slice(&control.bytes());
    let _ = frame.extend_from_slice(&data_bytes32(value));
    if crc {
        let mut covered = heapless::Vec::<u8, { MAX_FRAME + 1 }>::new();
        let _ = covered.push(target << 1);
        let _ = covered.extend_from_slice(&frame);
        let _ = frame.push(crc8(&covered));
    }
    frame
}

/// The bytes a read's CRC is computed over: `{target,0} ‖ control word ‖ {target,1} ‖ data`.
///
/// Note the address byte appears twice with different direction bits — the write that sends
/// the control word, then the repeated-start read that collects the data.
pub fn read_crc_input(target: u8, address: u16, data: [u8; 4]) -> heapless::Vec<u8, 9> {
    let mut covered = heapless::Vec::new();
    let _ = covered.push(target << 1);
    let _ = covered.extend_from_slice(&ControlWord::reg32(Op::Read, address, true).bytes());
    let _ = covered.push((target << 1) | 1);
    let _ = covered.extend_from_slice(&data);
    covered
}

/// The addresses to try when locating the device, most likely first.
///
/// `TARGET_ID` lives in EEPROM and only takes effect after a power cycle, so a board whose
/// address was changed will not answer at the default. The sweep is the datasheet's own
/// fallback. Pure and ordered so it can be checked without a bus.
pub fn probe_candidates(current: u8) -> impl Iterator<Item = u8> {
    // The general sweep covers the non-reserved range. Note the default address (0x01) is
    // itself reserved and so falls outside it — which is exactly why it has to be tried
    // explicitly up front rather than left to the sweep.
    const FIRST: u8 = 0x08;
    const LAST: u8 = 0x77;
    let head = [current, DEFAULT_TARGET_ID];
    let head_len = if current == DEFAULT_TARGET_ID { 1 } else { 2 };
    head.into_iter()
        .take(head_len)
        .chain((FIRST..=LAST).filter(move |candidate| *candidate != current))
}

/// Check a read's CRC byte and unpack its value.
///
/// Lives here rather than in the transport so the compare-and-classify step — the part that
/// decides whether a reply is trustworthy — is exercised by host tests, not only by a bus.
pub fn verify_read(target: u8, address: u16, reply: [u8; 5]) -> Result<u32, CrcMismatch> {
    let data = [reply[0], reply[1], reply[2], reply[3]];
    let expected = crc8(&read_crc_input(target, address, data));
    if expected != reply[4] {
        return Err(CrcMismatch {
            expected,
            received: reply[4],
        });
    }
    Ok(value_from_bytes32(data))
}

/// A reply whose checksum did not match what its bytes imply.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct CrcMismatch {
    pub expected: u8,
    pub received: u8,
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

    #[test]
    fn a_write_frame_is_control_word_then_lsb_first_data() {
        // Table 7-12's packet again, this time assembled end to end without CRC.
        let frame = write_frame(0x60, 0x080, 0x1234_ABCD, false);
        assert_eq!(&frame[..], &[0x10, 0x00, 0x80, 0xCD, 0xAB, 0x34, 0x12]);
    }

    #[test]
    fn a_crc_enabled_write_frame_appends_a_checksum_over_the_address_byte_too() {
        let frame = write_frame(0x60, 0x080, 0x1234_ABCD, true);
        assert_eq!(frame.len(), 8);
        assert_eq!(&frame[..7], &[0x50, 0x00, 0x80, 0xCD, 0xAB, 0x34, 0x12]);
        // The checksum must include the {target,0} byte the bus sends separately.
        let expected = crc8(&[0xC0, 0x50, 0x00, 0x80, 0xCD, 0xAB, 0x34, 0x12]);
        assert_eq!(frame[7], expected);
        assert_ne!(
            frame[7],
            crc8(&[0x50, 0x00, 0x80, 0xCD, 0xAB, 0x34, 0x12]),
            "address byte was omitted from the checksum"
        );
    }

    #[test]
    fn a_read_checksum_covers_the_address_byte_in_both_directions() {
        let covered = read_crc_input(0x60, 0x080, [0xCD, 0xAB, 0x34, 0x12]);
        assert_eq!(
            &covered[..],
            &[0xC0, 0xD0, 0x00, 0x80, 0xC1, 0xCD, 0xAB, 0x34, 0x12]
        );
    }

    #[test]
    fn a_clean_status_reports_no_condition() {
        assert_eq!(FaultStatus::default().condition(), None);
        assert!(!FaultStatus::default().any());
    }

    #[test]
    fn supply_faults_outrank_the_locks_they_cause() {
        // An undervoltage will also trip a lock; naming the lock would send the owner
        // looking at the motor instead of the supply.
        let status = FaultStatus::new(
            gate_fault::DRIVER_FAULT,
            controller_fault::CONTROLLER_FAULT
                | controller_fault::MTR_UNDER_VOLTAGE
                | controller_fault::MTR_LCK
                | controller_fault::ABN_SPEED,
        );
        assert_eq!(status.condition(), Some(McfCondition::Undervoltage));
    }

    #[test]
    fn each_documented_bit_group_decodes_to_its_own_condition() {
        use controller_fault as cf;
        use gate_fault as gf;
        let cases = [
            (0, cf::MTR_UNDER_VOLTAGE, McfCondition::Undervoltage),
            (gf::OVP, 0, McfCondition::Overvoltage),
            (gf::OTW, 0, McfCondition::Overtemperature),
            (gf::OTS, 0, McfCondition::Overtemperature),
            (gf::OCP, 0, McfCondition::Overcurrent),
            (0, cf::NO_MTR, McfCondition::MotorLock),
            (0, cf::ABN_BEMF, McfCondition::MotorLock),
            (0, cf::HW_LOCK_LIMIT, McfCondition::MotorLock),
            (0, cf::IPD_T1_FAULT, McfCondition::StartFailed),
            (0, cf::MPET_BEMF_FAULT, McfCondition::StartFailed),
            (0, cf::WATCHDOG_FAULT, McfCondition::McfWatchdog),
            (0, cf::EEPROM_ERR, McfCondition::Eeprom),
            (0, cf::I2C_CRC_FAULT, McfCondition::ProtocolError),
        ];
        for (gate, controller, expected) in cases {
            let status = FaultStatus::new(gate, controller);
            assert_eq!(
                status.condition(),
                Some(expected),
                "gate {gate:#010x} controller {controller:#010x}"
            );
        }
    }

    #[test]
    fn condition_precedence_holds_for_every_adjacent_pair() {
        use controller_fault as cf;
        use gate_fault as gf;
        // Each case sets two groups at once and names the winner. Testing groups one at a
        // time cannot detect a reordering — whichever branch matches is the only candidate.
        let cases = [
            (
                0,
                cf::MTR_UNDER_VOLTAGE | cf::MTR_OVER_VOLTAGE,
                McfCondition::Undervoltage,
            ),
            (gf::OVP | gf::OTW, 0, McfCondition::Overvoltage),
            (gf::OTW | gf::OCP, 0, McfCondition::Overtemperature),
            (gf::OCP, cf::NO_MTR, McfCondition::Overcurrent),
            (0, cf::MTR_LCK | cf::IPD_T1_FAULT, McfCondition::MotorLock),
            (
                0,
                cf::IPD_T1_FAULT | cf::WATCHDOG_FAULT,
                McfCondition::StartFailed,
            ),
            (
                0,
                cf::WATCHDOG_FAULT | cf::EEPROM_ERR,
                McfCondition::McfWatchdog,
            ),
            (0, cf::EEPROM_ERR | cf::I2C_CRC_FAULT, McfCondition::Eeprom),
        ];
        for (gate, controller, expected) in cases {
            assert_eq!(
                FaultStatus::new(gate, controller).condition(),
                Some(expected),
                "gate {gate:#010x} controller {controller:#010x}"
            );
        }
    }

    #[test]
    fn every_bit_in_a_group_decodes_to_that_group() {
        use controller_fault as cf;
        use gate_fault as gf;
        // Exhaustive over the named bits, so an OR mistyped as an AND or a constant
        // swapped between groups fails here rather than on the bench.
        let groups: [(&[(u32, u32)], McfCondition); 7] = [
            (
                &[
                    (0, cf::MTR_UNDER_VOLTAGE),
                    (gf::BUCK_UV, 0),
                    (gf::VCP_UV, 0),
                ],
                McfCondition::Undervoltage,
            ),
            (
                &[(0, cf::MTR_OVER_VOLTAGE), (gf::OVP, 0)],
                McfCondition::Overvoltage,
            ),
            (&[(gf::OTW, 0), (gf::OTS, 0)], McfCondition::Overtemperature),
            (
                &[(gf::OCP, 0), (gf::BUCK_OCP, 0)],
                McfCondition::Overcurrent,
            ),
            (
                &[
                    (0, cf::ABN_SPEED),
                    (0, cf::ABN_BEMF),
                    (0, cf::NO_MTR),
                    (0, cf::MTR_LCK),
                    (0, cf::LOCK_LIMIT),
                    (0, cf::HW_LOCK_LIMIT),
                ],
                McfCondition::MotorLock,
            ),
            (
                &[
                    (0, cf::IPD_FREQ_FAULT),
                    (0, cf::IPD_T1_FAULT),
                    (0, cf::IPD_T2_FAULT),
                    (0, cf::MPET_IPD_FAULT),
                    (0, cf::MPET_BEMF_FAULT),
                ],
                McfCondition::StartFailed,
            ),
            (
                &[
                    (0, cf::WATCHDOG_FAULT),
                    (0, cf::WWDT_FAULT),
                    (0, cf::CPU_RESET_FAULT),
                ],
                McfCondition::McfWatchdog,
            ),
        ];
        for (bits, expected) in groups {
            for (gate, controller) in bits {
                assert_eq!(
                    FaultStatus::new(*gate, *controller).condition(),
                    Some(expected),
                    "gate {gate:#010x} controller {controller:#010x}"
                );
            }
        }
    }

    #[test]
    fn probe_tries_the_current_address_then_the_default_then_sweeps() {
        let candidates: std::vec::Vec<u8> = probe_candidates(0x60).collect();
        assert_eq!(&candidates[..3], &[0x60, DEFAULT_TARGET_ID, 0x08]);
        assert_eq!(*candidates.last().unwrap(), 0x77);
        // The current address is tried once, up front, not again mid-sweep.
        assert_eq!(candidates.iter().filter(|c| **c == 0x60).count(), 1);
        // Nothing reserved leaks into the sweep.
        assert!(candidates[1..]
            .iter()
            .all(|c| *c == DEFAULT_TARGET_ID || (0x08..=0x77).contains(c)));
    }

    #[test]
    fn probe_does_not_try_the_default_address_twice() {
        let candidates: std::vec::Vec<u8> = probe_candidates(DEFAULT_TARGET_ID).collect();
        assert_eq!(
            candidates
                .iter()
                .filter(|c| **c == DEFAULT_TARGET_ID)
                .count(),
            1
        );
        assert_eq!(candidates[0], DEFAULT_TARGET_ID);
    }

    #[test]
    fn a_read_with_a_good_checksum_yields_its_value() {
        let data = [0xCD, 0xAB, 0x34, 0x12];
        let crc = crc8(&read_crc_input(0x60, 0x080, data));
        let reply = [data[0], data[1], data[2], data[3], crc];
        assert_eq!(verify_read(0x60, 0x080, reply), Ok(0x1234_ABCD));
    }

    #[test]
    fn a_read_with_a_bad_checksum_is_rejected_rather_than_returned() {
        // The value is perfectly well-formed; only the checksum disagrees. Returning it
        // anyway would hand corrupted state to a motor-control state machine.
        let data = [0xCD, 0xAB, 0x34, 0x12];
        let good = crc8(&read_crc_input(0x60, 0x080, data));
        let reply = [data[0], data[1], data[2], data[3], good ^ 0xFF];
        assert_eq!(
            verify_read(0x60, 0x080, reply),
            Err(CrcMismatch {
                expected: good,
                received: good ^ 0xFF,
            })
        );
    }

    #[test]
    fn a_read_checksum_is_bound_to_its_address() {
        // The same bytes read from a different register must not validate — otherwise a
        // mis-addressed reply would be accepted as the register we asked for.
        let data = [0xCD, 0xAB, 0x34, 0x12];
        let crc = crc8(&read_crc_input(0x60, 0x0E0, data));
        let reply = [data[0], data[1], data[2], data[3], crc];
        assert!(verify_read(0x60, 0x0E0, reply).is_ok());
        assert!(verify_read(0x60, 0x0E2, reply).is_err());
    }

    #[test]
    fn an_unrecognised_fault_bit_is_still_a_fault() {
        // A summary bit alone, with no detail bit set, must not decode to "healthy".
        let status = FaultStatus::new(gate_fault::DRIVER_FAULT, 0);
        assert_eq!(status.condition(), Some(McfCondition::Unclassified));
    }
}
