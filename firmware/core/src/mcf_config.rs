//! The MCF8316D configuration image: what the device must be holding before the fan runs.
//!
//! `docs/controls.md` > "Initial MCF8316D configuration" describes the configuration in
//! words — latched fault modes, `SPEED_RANGE_SEL` = 0h, qualified startup, a 180 RPM stored
//! ceiling. This module is the machinery that makes those words checkable against silicon,
//! and [`IMAGE`] is where the values themselves live.
//!
//! **Why the image is a list of whole register values rather than named fields.** Bit-level
//! field layouts for the configuration block were never transcribed into this crate (see
//! `mcf8316::reg`), because a wrong bit position writes garbage into a motor controller and
//! we have no primary source open for those tables. A golden image sidesteps that entirely:
//! capture the whole block off a device that has been tuned and qualified, commit those 32-bit
//! values, and verify them by read-back forever after. Knowing *why* bit 17 is set is not
//! required to know that it must be. The `mask` field is there for the in-between state — a
//! field whose meaning has been derived at the bench, in a register whose remaining bits are
//! still being explored.
//!
//! **The image is verified at boot, never written at boot.** Two reasons. Writes to
//! `0x080..=0x0AE` are subject to the EEPROM discipline in `docs/controls.md` (motor stopped,
//! device idle or faulted, 20k-cycle endurance), and whether a register write lands in a
//! volatile shadow or burns an EEPROM cycle is exactly the sort of thing that must be
//! established on a bench rather than assumed on a power-up path. So [`apply`] exists, and is
//! a deliberate console operation; [`check`] is what runs at boot.

use crate::mcf8316::{controller_fault, reg, RegisterBus};

/// One register's required contents.
///
/// `value` carries only the bits `mask` selects; everything outside the mask is ignored on
/// both sides of the comparison, so a partially-understood register can still be pinned down
/// as far as it is understood.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Setting {
    pub name: &'static str,
    pub address: u16,
    pub mask: u32,
    pub value: u32,
}

impl Setting {
    /// The whole register must equal `value`. What a captured golden image is made of.
    pub const fn whole(name: &'static str, address: u16, value: u32) -> Self {
        Self {
            name,
            address,
            mask: u32::MAX,
            value,
        }
    }

    /// Only the masked bits must match. For fields derived one at a time at the bench.
    pub const fn masked(name: &'static str, address: u16, mask: u32, value: u32) -> Self {
        Self {
            name,
            address,
            mask,
            // Masking here rather than trusting the caller means `value` can be written as
            // the literal from the datasheet table without also having to pre-shift it out
            // of the bits the mask excludes.
            value: value & mask,
        }
    }

    /// Does a register read back satisfy this setting?
    pub const fn matches(&self, read: u32) -> bool {
        read & self.mask == self.value
    }

    /// The value to write, preserving every bit the setting does not claim.
    pub const fn merge(&self, read: u32) -> u32 {
        (read & !self.mask) | self.value
    }
}

/// The configuration the fan is qualified against.
///
/// # Capture checklist (2026-07 board-truth review)
///
/// The PCB-01 wiring makes specific register fields load-bearing; a capture that leaves
/// them at their reset defaults leaves the corresponding copper inert. The image must pin,
/// at minimum (tests below enforce the register coverage):
///
/// - **`PIN_CONFIG`** — `SPEED_MODE` = 01b (PWM duty command; reset default is analog, and
///   the board drives SPEED with a 1 kHz LEDC PWM) and `ALARM_PIN_EN` = 1 (the ALARM →
///   GPIO14 thermal-stop path is wired and unit-tested but dead until enabled).
/// - **`PERI_CONFIG1`** — `SPEED_RANGE_SEL` = 0h (325 Hz–100 kHz duty band; the 1 kHz
///   command carrier sits well inside it).
/// - **`GD_CONFIG1`** — `OTW_REP` = 1 (thermal warnings must reach ALARM).
/// - **`CLOSED_LOOP4.MAX_SPEED`** — the 180 RPM stored ceiling; [`max_speed_setting`]
///   builds this entry so the masked value and the speed ladder stay in one place.
/// - **`DEVICE_CONFIG2`** — external-watchdog fields, *only* with a satisfiable window:
///   the board heartbeat is fixed at [`crate::config::WATCHDOG_HEARTBEAT_HZ`] (rising edge
///   every 500 ms), so GPIO tickle mode requires `EXT_WDT_CONFIG` = 3h (1000 ms). 2h
///   (500 ms) is edge-on-deadline and faults on jitter; 0h/1h can never pass — and 0h is
///   the chip's reset default. The `ext_wdt` test below fails the build on a bad capture.
pub const IMAGE: &[Setting] = LOADED_IMAGE;

/// Golden image captured from the stopped, ceiling-loaded controller on 2026-08-21.
///
/// The retained unloaded candidate supplied the tuned fields, then the installed fan qualified
/// repeated 50 RPM starts, the complete 50--170 RPM range, Hall/FG agreement, and a ten-minute
/// 50 RPM endurance hold with Matter online. Unlike [`UNLOADED_IMAGE`], this capture pins the
/// complete configuration block exactly as read from silicon.
pub const LOADED_IMAGE: &[Setting] = &[
    Setting::whole("ISD_CONFIG", 0x080, 0x64f3_4ca0),
    Setting::whole("REV_DRIVE_CONFIG", 0x082, 0xa820_0000),
    Setting::whole("MOTOR_STARTUP1", 0x084, 0xa2e6_0000),
    Setting::whole("MOTOR_STARTUP2", 0x086, 0x1101_28ab),
    Setting::whole("CLOSED_LOOP1", 0x088, 0x3e01_810c),
    Setting::whole("CLOSED_LOOP2", 0x08a, 0x8000_b1ae),
    Setting::whole("CLOSED_LOOP3", 0x08c, 0xe000_0004),
    Setting::whole("CLOSED_LOOP4", 0x08e, 0xd0c2_0168),
    Setting::whole("FAULT_CONFIG1", 0x090, 0x0aa8_4000),
    Setting::whole("FAULT_CONFIG2", 0x092, 0xb1c0_47c0),
    Setting::whole("REF_PROFILES1", 0x094, 0x0000_0000),
    Setting::whole("REF_PROFILES2", 0x096, 0x0000_0000),
    Setting::whole("REF_PROFILES3", 0x098, 0x8000_0002),
    Setting::whole("REF_PROFILES4", 0x09a, 0x8006_8000),
    Setting::whole("REF_PROFILES5", 0x09c, 0x8000_0010),
    Setting::whole("REF_PROFILES6", 0x09e, 0x0000_0000),
    Setting::whole("INT_ALGO_1", 0x0a0, 0x800e_0000),
    Setting::whole("INT_ALGO_2", 0x0a2, 0x0000_0000),
    Setting::whole("PIN_CONFIG", 0x0a4, 0x8020_0041),
    // TARGET_ID is EEPROM-latched and the live capture reported zero while silicon still
    // answered at the prior 0x01 address. Pin the documented default explicitly so replaying
    // the capture cannot move the device onto reserved address 0x00 after a power cycle.
    Setting::whole("DEVICE_CONFIG1", 0x0a6, 0x0010_0001),
    Setting::whole("DEVICE_CONFIG2", 0x0a8, 0x8000_001f),
    Setting::whole("PERI_CONFIG1", 0x0aa, 0x0022_0000),
    Setting::whole("GD_CONFIG1", 0x0ac, 0x8001_0003),
    Setting::whole("GD_CONFIG2", 0x0ae, 0x0084_0000),
];

/// Frozen volatile configuration qualified on the unloaded GL100 commissioning bench.
///
/// This is deliberately separate from [`IMAGE`]. It uses vendor motor data and conservative
/// unloaded commissioning gains, not values qualified with the final rotor, so it must never
/// be committed to EEPROM or described as the golden configuration. `config stage` writes
/// these settings to the MCF shadow registers and a power cycle erases them. Loaded tuning uses
/// the separate complete [`LOADED_IMAGE`] rather than editing or deleting this retained baseline.
///
/// Values are lower-31-bit register words from MCF8316D SLLSFX9A Tables 8-5 through 8-32;
/// bit 31 is the silicon's read-only parity bit. Speed-loop gains and current headroom are
/// iterated against synchronized physical-motion, phase-current, and supply-current traces.
pub const PROVISIONAL_SENTINEL: Setting =
    Setting::masked("CLOSED_LOOP4", 0x08E, 0x7FFF_FFFF, 0x50C2_0168);

/// Staged FAULT_CONFIG1 word and its reviewed runtime variants. Only ILIMIT differs.
pub const ACQUISITION_FAULT_CONFIG1: u32 = 0x0AA8_4000;
pub const SETTLING_FAULT_CONFIG1: u32 = 0x02A8_4000;
pub const RUNNING_FAULT_CONFIG1: u32 = 0x0AA8_4000;

pub const UNLOADED_IMAGE: &[Setting] = &[
    Setting::masked("MOTOR_STARTUP1", 0x084, 0x7FFF_FFFF, 0x22E6_0000),
    Setting::masked("MOTOR_STARTUP2", 0x086, 0x7FFF_FFFF, 0x1101_28AB),
    Setting::masked(
        "CLOSED_LOOP1",
        0x088,
        0x7FFF_FFFF,
        0x0000_0108
            | crate::mcf8316::fields::CL_ACC_NO_LIMIT
            | crate::mcf8316::fields::PWM_FREQ_OUT_25_KHZ
            | crate::mcf8316::fields::DEADTIME_COMP_EN,
    ),
    // The stationary B7/B4 model and both one-variable isolations were worse than the
    // vendor 1.35-ohm / 1.20-mH phase model.
    Setting::masked("CLOSED_LOOP2", 0x08A, 0x7FFF_FFFF, 0x0000_B1AE),
    Setting::masked("CLOSED_LOOP3", 0x08C, 0x7FFF_FFFF, 0x6000_0004),
    PROVISIONAL_SENTINEL,
    Setting::masked(
        "FAULT_CONFIG1",
        0x090,
        0x7FFF_FFFF,
        ACQUISITION_FAULT_CONFIG1,
    ),
    Setting::masked("FAULT_CONFIG2", 0x092, 0x7FFF_FFFF, 0x31C0_47C0),
    Setting::masked("INT_ALGO_1", 0x0A0, 0x7FFF_FFFF, 0x000E_0000),
    Setting::masked("INT_ALGO_2", 0x0A2, 0x7FFF_FFFF, 0x0000_0000),
    Setting::masked("PIN_CONFIG", 0x0A4, 0x7FFF_FFFF, 0x0020_0041),
    Setting::masked(
        "DEVICE_CONFIG1",
        0x0A6,
        0x7FFF_FFFF,
        crate::mcf8316::fields::BUS_VOLT_30_V,
    ),
    Setting::masked("DEVICE_CONFIG2", 0x0A8, 0x7FFF_FFFF, 0x0000_001F),
    Setting::masked("PERI_CONFIG1", 0x0AA, 0x7FFF_FFFF, 0x0022_0000),
    // The reset 0.15 V/A gain became unstable within 20 s at 140 RPM after the final rig
    // rebuild. The maximum 1.2 V/A gain outlasted the lower settings, so retain it while
    // isolating motor-model candidates.
    Setting::masked(
        "GD_CONFIG1",
        0x0AC,
        0x7FFF_FFFF,
        0x0001_0000 | crate::mcf8316::fields::CSA_GAIN_1P2_V_PER_A,
    ),
];

/// The image currently staged by `config stage`.
///
/// Kept as an alias so loaded commissioning can point staging at a separate candidate while
/// [`UNLOADED_IMAGE`] remains available for A/B comparison and regression diagnosis.
pub const PROVISIONAL_IMAGE: &[Setting] = UNLOADED_IMAGE;

/// A reviewed one-field experiment derived from the complete loaded golden image.
///
/// These are deliberately named values rather than arbitrary words. Each candidate changes
/// only a field whose layout has already been transcribed from the TI datasheet and leaves
/// the 180 RPM ceiling, fault behavior, motor model, startup sequence, and board-interface
/// fields identical to [`LOADED_IMAGE`]. The operation is volatile and cannot commit EEPROM.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TuneCandidate {
    Pwm20Khz,
    Pwm25Khz,
    Pwm30Khz,
    Pwm40Khz,
    Pwm50Khz,
    Pwm60Khz,
    DeadtimeOff,
    DeadtimeOn,
    Slew125VPerUs,
    Slew200VPerUs,
}

impl TuneCandidate {
    pub const ALL: &[Self] = &[
        Self::Pwm20Khz,
        Self::Pwm25Khz,
        Self::Pwm30Khz,
        Self::Pwm40Khz,
        Self::Pwm50Khz,
        Self::Pwm60Khz,
        Self::DeadtimeOff,
        Self::DeadtimeOn,
        Self::Slew125VPerUs,
        Self::Slew200VPerUs,
    ];

    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Pwm20Khz => "pwm-20khz",
            Self::Pwm25Khz => "pwm-25khz",
            Self::Pwm30Khz => "pwm-30khz",
            Self::Pwm40Khz => "pwm-40khz",
            Self::Pwm50Khz => "pwm-50khz",
            Self::Pwm60Khz => "pwm-60khz",
            Self::DeadtimeOff => "deadtime-off",
            Self::DeadtimeOn => "deadtime-on",
            Self::Slew125VPerUs => "slew-125v-us",
            Self::Slew200VPerUs => "slew-200v-us",
        }
    }

    pub fn from_name(name: &str) -> Option<Self> {
        Self::ALL
            .iter()
            .copied()
            .find(|candidate| candidate.as_str().eq_ignore_ascii_case(name))
    }

    pub const fn setting(self) -> Setting {
        use crate::mcf8316::fields;

        match self {
            Self::Pwm20Khz => Setting::masked(
                "CLOSED_LOOP1.PWM_FREQ_OUT",
                0x088,
                fields::PWM_FREQ_OUT_MASK,
                fields::PWM_FREQ_OUT_20_KHZ,
            ),
            Self::Pwm25Khz => Setting::masked(
                "CLOSED_LOOP1.PWM_FREQ_OUT",
                0x088,
                fields::PWM_FREQ_OUT_MASK,
                fields::PWM_FREQ_OUT_25_KHZ,
            ),
            Self::Pwm30Khz => Setting::masked(
                "CLOSED_LOOP1.PWM_FREQ_OUT",
                0x088,
                fields::PWM_FREQ_OUT_MASK,
                fields::PWM_FREQ_OUT_30_KHZ,
            ),
            Self::Pwm40Khz => Setting::masked(
                "CLOSED_LOOP1.PWM_FREQ_OUT",
                0x088,
                fields::PWM_FREQ_OUT_MASK,
                fields::PWM_FREQ_OUT_40_KHZ,
            ),
            Self::Pwm50Khz => Setting::masked(
                "CLOSED_LOOP1.PWM_FREQ_OUT",
                0x088,
                fields::PWM_FREQ_OUT_MASK,
                fields::PWM_FREQ_OUT_50_KHZ,
            ),
            Self::Pwm60Khz => Setting::masked(
                "CLOSED_LOOP1.PWM_FREQ_OUT",
                0x088,
                fields::PWM_FREQ_OUT_MASK,
                fields::PWM_FREQ_OUT_60_KHZ,
            ),
            Self::DeadtimeOff => Setting::masked(
                "CLOSED_LOOP1.DEADTIME_COMP_EN",
                0x088,
                fields::DEADTIME_COMP_EN,
                0,
            ),
            Self::DeadtimeOn => Setting::masked(
                "CLOSED_LOOP1.DEADTIME_COMP_EN",
                0x088,
                fields::DEADTIME_COMP_EN,
                fields::DEADTIME_COMP_EN,
            ),
            Self::Slew125VPerUs => Setting::masked(
                "GD_CONFIG1.SLEW_RATE",
                reg::GD_CONFIG1,
                fields::SLEW_RATE_MASK,
                fields::SLEW_RATE_125_V_PER_US,
            ),
            Self::Slew200VPerUs => Setting::masked(
                "GD_CONFIG1.SLEW_RATE",
                reg::GD_CONFIG1,
                fields::SLEW_RATE_MASK,
                fields::SLEW_RATE_200_V_PER_US,
            ),
        }
    }
}

/// Put the live configuration shadow into standby mode without committing EEPROM.
///
/// A device previously stored in sleep mode stops acknowledging I2C while SPEED is low.
/// The board firmware holds SPEED high while calling this function, then returns it to zero
/// only after the `DEV_MODE` bit has read back clear. This is intentionally separate from
/// [`apply`]: it changes one volatile shadow bit to make commissioning possible and never
/// issues an EEPROM commit.
pub async fn ensure_standby<B: RegisterBus>(bus: &mut B) -> Result<bool, ConfigFault> {
    let address = reg::DEVICE_CONFIG2;
    let current = bus
        .read(address)
        .await
        .map_err(|_| ConfigFault::Unreadable { address })?;
    let standby = current & !crate::mcf8316::fields::DEV_MODE_SLEEP;
    if standby == current {
        return Ok(false);
    }

    bus.write(address, standby)
        .await
        .map_err(|_| ConfigFault::Mismatch { address })?;
    match bus.read(address).await {
        Ok(readback) if readback & crate::mcf8316::fields::DEV_MODE_SLEEP == 0 => Ok(true),
        Ok(_) => Err(ConfigFault::Mismatch { address }),
        Err(_) => Err(ConfigFault::Unreadable { address }),
    }
}

/// The `CLOSED_LOOP4.MAX_SPEED` image entry for a given stored ceiling, claiming only the
/// 14 `MAX_SPEED` bits (Table 8-10) so the bench-tuned speed-loop gains in the same
/// register stay unclaimed until they are captured.
pub const fn max_speed_setting(max_speed: u16) -> Setting {
    Setting::masked(
        "CLOSED_LOOP4.MAX_SPEED",
        reg::CLOSED_LOOP4,
        crate::mcf8316::fields::MAX_SPEED_MASK,
        max_speed as u32,
    )
}

/// Why a configuration check failed.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ConfigFault {
    /// The device reports its own EEPROM as errored or locked. Its stored configuration is
    /// not trustworthy no matter what our read-back says, because an interrupted EEPROM
    /// write is caught by the MCF's CRC and held at Hi-Z (`docs/controls.md`).
    DeviceEeprom,
    /// A register did not read back as the image being checked requires.
    Mismatch { address: u16 },
    /// The register could not be read at all.
    Unreadable { address: u16 },
    /// Shadow values were written, but the explicit EEPROM commit did not complete and
    /// self-clear within the bounded confirmation window.
    CommitUnconfirmed,
    /// The commit command or its completion poll could not reach the device.
    CommitUnreadable,
    /// The check did not finish in time. Reported by the supervisor, not by [`check`].
    TimedOut,
}

/// The device's configuration-readiness verdict, covering both volatile and stored images.
///
/// Distinct values rather than a `bool` because "we have not checked yet", "there is nothing to
/// check against yet", and "we checked and it is right" are three genuinely different things,
/// and collapsing the middle one into either neighbour is how a safety gate becomes theatre.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum ConfigCheck {
    /// The check has not produced a verdict yet. `SafeBoot` waits for one.
    #[default]
    Pending,
    /// The device's own integrity bits are clean, but [`IMAGE`] is empty, so nothing was
    /// compared. The fan remains in `SafeBoot`; inspection and staging commands stay
    /// available, and every telemetry frame records the unverified verdict.
    Unverified,
    /// The reviewed first-spin image is present in volatile shadow registers. This permits
    /// bench operation but is intentionally lost at the next MCF power cycle.
    Provisional,
    /// A reviewed one-field candidate derived from the loaded golden image is present in
    /// volatile shadow. Unlike `Provisional`, this does not activate unloaded-only runtime
    /// current-profile changes, so a candidate comparison changes exactly its named field.
    Tuning,
    /// Every setting in [`IMAGE`] read back as required.
    Verified,
    Failed(ConfigFault),
}

impl ConfigCheck {
    /// Has a verdict landed at all?
    pub const fn settled(self) -> bool {
        !matches!(self, Self::Pending)
    }

    /// May the supervisor leave `SafeBoot` on this verdict?
    pub const fn permits_operation(self) -> bool {
        matches!(self, Self::Provisional | Self::Tuning | Self::Verified)
    }

    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Pending => "pending",
            Self::Unverified => "unverified",
            Self::Provisional => "provisional",
            Self::Tuning => "tuning",
            Self::Verified => "verified",
            Self::Failed(_) => "failed",
        }
    }
}

/// Bits that mean the device cannot vouch for its own stored configuration.
const EEPROM_SUSPECT: u32 = controller_fault::EEPROM_ERR
    | controller_fault::EEPROM_WRITE_LOCK
    | controller_fault::EEPROM_READ_LOCK;

/// Verify the device's stored configuration. Reads only; safe on any power-up path.
///
/// The device's own verdict is consulted first and outranks ours: it CRCs its EEPROM at boot,
/// and if that check failed then the block we are about to read is already known-bad. Nothing
/// we could observe agreeing would redeem it.
pub async fn check<B: RegisterBus>(bus: &mut B, image: &[Setting]) -> ConfigCheck {
    let status = match bus.read(reg::CONTROLLER_FAULT_STATUS).await {
        Ok(status) => status,
        Err(_) => {
            return ConfigCheck::Failed(ConfigFault::Unreadable {
                address: reg::CONTROLLER_FAULT_STATUS,
            })
        }
    };
    if status & EEPROM_SUSPECT != 0 {
        return ConfigCheck::Failed(ConfigFault::DeviceEeprom);
    }

    if image.is_empty() {
        return ConfigCheck::Unverified;
    }

    for setting in image {
        match bus.read(setting.address).await {
            Ok(read) if setting.matches(read) => {}
            Ok(_) => {
                return ConfigCheck::Failed(ConfigFault::Mismatch {
                    address: setting.address,
                })
            }
            Err(_) => {
                return ConfigCheck::Failed(ConfigFault::Unreadable {
                    address: setting.address,
                })
            }
        }
    }
    ConfigCheck::Verified
}

/// What [`apply`] did.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct Applied {
    /// Settings that needed a write.
    pub written: u16,
    /// Settings the device already satisfied, which are left untouched — on a block with
    /// 20k-cycle endurance, not writing is a feature.
    pub unchanged: u16,
}

/// Write every setting the device does not already satisfy, then verify the lot by read-back.
///
/// Read-modify-write, so a masked setting cannot clobber the bits around it. This is a bench
/// operation: callers must gate it on the motor being stopped (the console does), and it is
/// deliberately not on the boot path.
/// Returns the verdict rather than a `Result`, and it is the one this function's own read-back
/// pass produced — so a caller that needs to publish it does not have to run a second full pass
/// over the block to learn what this one already established.
///
pub async fn apply<B: RegisterBus>(bus: &mut B, image: &[Setting]) -> (Applied, ConfigCheck) {
    let (applied, write_failure) = write_shadow(bus, image).await;
    if let Some(failure) = write_failure {
        return (applied, failure);
    }

    if applied.written != 0 {
        match commit(bus).await {
            Ok(true) => {}
            Ok(false) => return (applied, ConfigCheck::Failed(ConfigFault::CommitUnconfirmed)),
            Err(_) => return (applied, ConfigCheck::Failed(ConfigFault::CommitUnreadable)),
        }
    }

    // Re-read everything rather than trusting the writes. `RegisterBus::write` promises
    // nothing about the value sticking, and a configuration that silently did not take is the
    // failure this whole module exists to make impossible.
    (applied, check(bus, image).await)
}

/// Stage the provisional commissioning image in volatile shadow registers only.
///
/// No EEPROM command is issued. A successful full read-back is reported as
/// [`ConfigCheck::Provisional`] so it cannot be confused with the persistent golden image.
pub async fn stage<B: RegisterBus>(bus: &mut B) -> (Applied, ConfigCheck) {
    let (applied, check) = write_volatile_image(bus, PROVISIONAL_IMAGE).await;
    let verdict = match check {
        ConfigCheck::Verified => ConfigCheck::Provisional,
        other => other,
    };
    (applied, verdict)
}

/// Re-read the fixed provisional image without rewriting it.
pub async fn check_provisional<B: RegisterBus>(bus: &mut B) -> ConfigCheck {
    match check(bus, PROVISIONAL_IMAGE).await {
        ConfigCheck::Verified => ConfigCheck::Provisional,
        other => other,
    }
}

/// Re-read a loaded one-field candidate against its golden base.
pub async fn check_loaded_candidate<B: RegisterBus>(
    bus: &mut B,
    candidate: TuneCandidate,
) -> ConfigCheck {
    let status = match bus.read(reg::CONTROLLER_FAULT_STATUS).await {
        Ok(status) => status,
        Err(_) => {
            return ConfigCheck::Failed(ConfigFault::Unreadable {
                address: reg::CONTROLLER_FAULT_STATUS,
            })
        }
    };
    if status & EEPROM_SUSPECT != 0 {
        return ConfigCheck::Failed(ConfigFault::DeviceEeprom);
    }

    let override_setting = candidate.setting();
    for golden in LOADED_IMAGE {
        match bus.read(golden.address).await {
            Ok(read) if golden.address == override_setting.address => {
                let preserved_mask = golden.mask & !override_setting.mask;
                if read & preserved_mask != golden.value & preserved_mask
                    || !override_setting.matches(read)
                {
                    return ConfigCheck::Failed(ConfigFault::Mismatch {
                        address: golden.address,
                    });
                }
            }
            Ok(read) if golden.matches(read) => {}
            Ok(_) => {
                return ConfigCheck::Failed(ConfigFault::Mismatch {
                    address: golden.address,
                })
            }
            Err(_) => {
                return ConfigCheck::Failed(ConfigFault::Unreadable {
                    address: golden.address,
                })
            }
        }
    }
    ConfigCheck::Tuning
}

/// Restore the loaded golden image in volatile shadow, apply one reviewed field override,
/// and verify both the override and every preserved golden bit. Never commits EEPROM.
pub async fn stage_loaded_candidate<B: RegisterBus>(
    bus: &mut B,
    candidate: TuneCandidate,
) -> (Applied, ConfigCheck) {
    let (mut applied, base_check) = write_volatile_image(bus, LOADED_IMAGE).await;
    if base_check != ConfigCheck::Verified {
        return (applied, base_check);
    }

    let candidate_image = [candidate.setting()];
    let (override_applied, write_failure) = write_shadow(bus, &candidate_image).await;
    applied.written += override_applied.written;
    applied.unchanged += override_applied.unchanged;
    if let Some(failure) = write_failure {
        return (applied, failure);
    }
    (applied, check_loaded_candidate(bus, candidate).await)
}

/// Cheaply detect a reset or loss of the selected candidate between full checks.
pub async fn check_loaded_candidate_sentinel<B: RegisterBus>(
    bus: &mut B,
    candidate: TuneCandidate,
) -> ConfigCheck {
    for setting in [PROVISIONAL_SENTINEL, candidate.setting()] {
        match bus.read(setting.address).await {
            Ok(value) if setting.matches(value) => {}
            Ok(_) => {
                return ConfigCheck::Failed(ConfigFault::Mismatch {
                    address: setting.address,
                })
            }
            Err(_) => {
                return ConfigCheck::Failed(ConfigFault::Unreadable {
                    address: setting.address,
                })
            }
        }
    }
    ConfigCheck::Tuning
}

/// Cheaply detect an MCF reset that silently reloaded EEPROM while its rail stayed high.
///
/// CLOSED_LOOP4 contains both nonzero speed-loop gains and the 180 RPM ceiling, and reset
/// silicon does not reproduce this reviewed word. The full image is still
/// checked by `config stage` and an explicit `config check`; this sentinel runs on every
/// status cycle.
pub async fn check_provisional_sentinel<B: RegisterBus>(bus: &mut B) -> ConfigCheck {
    match bus.read(PROVISIONAL_SENTINEL.address).await {
        Ok(value) if PROVISIONAL_SENTINEL.matches(value) => ConfigCheck::Provisional,
        Ok(_) => ConfigCheck::Failed(ConfigFault::Mismatch {
            address: PROVISIONAL_SENTINEL.address,
        }),
        Err(_) => ConfigCheck::Failed(ConfigFault::Unreadable {
            address: PROVISIONAL_SENTINEL.address,
        }),
    }
}

/// Invalidate configuration readiness when the MCF rail falls while the ESP remains alive.
pub const fn after_pgood_loss(pgood_fell: bool, current: ConfigCheck) -> ConfigCheck {
    if pgood_fell {
        ConfigCheck::Unverified
    } else {
        current
    }
}

async fn write_volatile_image<B: RegisterBus>(
    bus: &mut B,
    image: &[Setting],
) -> (Applied, ConfigCheck) {
    if image.is_empty() {
        return (Applied::default(), ConfigCheck::Unverified);
    }
    let (applied, write_failure) = write_shadow(bus, image).await;
    if let Some(failure) = write_failure {
        return (applied, failure);
    }
    (applied, check(bus, image).await)
}

async fn write_shadow<B: RegisterBus>(
    bus: &mut B,
    image: &[Setting],
) -> (Applied, Option<ConfigCheck>) {
    let mut applied = Applied::default();

    for setting in image {
        let read = match bus.read(setting.address).await {
            Ok(read) => read,
            Err(_) => {
                let address = setting.address;
                return (
                    applied,
                    Some(ConfigCheck::Failed(ConfigFault::Unreadable { address })),
                );
            }
        };
        if setting.matches(read) {
            applied.unchanged += 1;
            continue;
        }
        if bus
            .write(setting.address, setting.merge(read))
            .await
            .is_err()
        {
            let address = setting.address;
            return (
                applied,
                Some(ConfigCheck::Failed(ConfigFault::Mismatch { address })),
            );
        }
        applied.written += 1;
    }

    (applied, None)
}

/// Write one register on an operator's behalf, re-verifying the image if it landed in the
/// configuration block.
///
/// This is *behaviour*, not transport, which is why it lives in the core crate and is called
/// identically by the firmware and the simulator. A bench write into `0x080..=0x0AE`
/// invalidates whatever verdict was standing, and leaving a stale `Verified` in place
/// afterwards would be a safety gate vouching for a configuration the device is no longer
/// holding. Doing it automatically rather than trusting the operator to remember `config
/// check` is the point — the dangerous case is the one nobody thinks to check.
///
/// `Ok(None)` means the address was outside the configuration block, so no verdict changed.
pub async fn write_and_recheck<B: RegisterBus>(
    bus: &mut B,
    address: u16,
    value: u32,
    image: &[Setting],
) -> Result<Option<ConfigCheck>, B::Error> {
    bus.write(address, value).await?;
    if !crate::mcf8316::is_configuration(address) {
        return Ok(None);
    }
    Ok(Some(check(bus, image).await))
}

/// Commit the shadow configuration once, wait TI's minimum programming interval, then poll
/// the self-clearing command register. `false` is distinct from a bus error: the device kept
/// answering but never confirmed that the persistent write completed.
async fn commit<B: RegisterBus>(bus: &mut B) -> Result<bool, B::Error> {
    const POLL_MS: u32 = 25;
    const TIMEOUT_MS: u32 = 2_000;

    bus.write(reg::ALGO_CTRL1, crate::mcf8316::EEPROM_WRITE_COMMAND)
        .await?;
    bus.delay_ms(crate::mcf8316::EEPROM_WRITE_MIN_MS).await;

    let mut waited = crate::mcf8316::EEPROM_WRITE_MIN_MS;
    loop {
        if bus.read(reg::ALGO_CTRL1).await? == 0 {
            return Ok(true);
        }
        if waited >= TIMEOUT_MS {
            return Ok(false);
        }
        bus.delay_ms(POLL_MS).await;
        waited += POLL_MS;
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use core::future::Future;
    use core::pin::pin;
    use core::task::{Context, Poll, Waker};
    use std::collections::HashMap;

    /// Drive a future that is known not to await anything real.
    ///
    /// The fake bus below completes synchronously, so a single poll always resolves. A loop
    /// with a no-op waker would spin forever on a future that genuinely pended; panicking
    /// says which of the two happened.
    fn block_on<F: Future>(future: F) -> F::Output {
        let mut future = pin!(future);
        let waker = Waker::noop();
        match future.as_mut().poll(&mut Context::from_waker(waker)) {
            Poll::Ready(value) => value,
            Poll::Pending => panic!("the fake bus must never pend"),
        }
    }

    /// A register file that can be told to misbehave.
    #[derive(Default)]
    struct FakeBus {
        registers: HashMap<u16, u32>,
        /// Reads of this address fail.
        read_fails: Option<u16>,
        /// Writes of this address fail.
        write_fails: Option<u16>,
        /// Writes of this address are accepted and silently discarded, the way a locked or
        /// unwritable register behaves.
        write_ignored: Option<u16>,
        /// Leave the EEPROM command set after delays, simulating a commit that never ends.
        commit_stuck: bool,
        reads: usize,
        writes: usize,
        delayed_ms: u32,
    }

    impl FakeBus {
        fn with(pairs: &[(u16, u32)]) -> Self {
            Self {
                registers: pairs.iter().copied().collect(),
                ..Self::default()
            }
        }
    }

    impl RegisterBus for FakeBus {
        type Error = ();

        async fn read(&mut self, address: u16) -> Result<u32, ()> {
            self.reads += 1;
            if self.read_fails == Some(address) {
                return Err(());
            }
            Ok(self.registers.get(&address).copied().unwrap_or(0))
        }

        async fn write(&mut self, address: u16, value: u32) -> Result<(), ()> {
            self.writes += 1;
            if self.write_fails == Some(address) {
                return Err(());
            }
            if self.write_ignored != Some(address) {
                self.registers.insert(address, value);
            }
            Ok(())
        }

        async fn delay_ms(&mut self, milliseconds: u32) {
            self.delayed_ms += milliseconds;
            if !self.commit_stuck
                && self.registers.get(&reg::ALGO_CTRL1)
                    == Some(&crate::mcf8316::EEPROM_WRITE_COMMAND)
            {
                self.registers.insert(reg::ALGO_CTRL1, 0);
            }
        }
    }

    const A: u16 = 0x080;
    const B: u16 = 0x082;

    #[test]
    fn an_empty_image_is_unverified_rather_than_verified() {
        // The distinction this whole enum exists for: passing a check that compared nothing
        // would make the SafeBoot clause read as satisfied while guaranteeing nothing.
        let mut bus = FakeBus::default();
        assert_eq!(block_on(check(&mut bus, &[])), ConfigCheck::Unverified);
        assert_ne!(ConfigCheck::Unverified, ConfigCheck::Verified);
    }

    #[test]
    fn ensure_standby_clears_only_dev_mode_without_committing() {
        use crate::mcf8316::fields::DEV_MODE_SLEEP;

        let original = 0xA5A5_0000 | DEV_MODE_SLEEP;
        let mut bus = FakeBus::with(&[(reg::DEVICE_CONFIG2, original)]);
        assert_eq!(block_on(ensure_standby(&mut bus)), Ok(true));
        assert_eq!(
            bus.registers[&reg::DEVICE_CONFIG2],
            original & !DEV_MODE_SLEEP
        );
        assert_eq!(bus.writes, 1, "volatile change must be one shadow write");
        assert_eq!(
            bus.registers.get(&reg::ALGO_CTRL1),
            None,
            "standby recovery must not issue an EEPROM commit"
        );
    }

    #[test]
    fn ensure_standby_does_not_rewrite_an_awake_device() {
        let mut bus = FakeBus::with(&[(reg::DEVICE_CONFIG2, 0x1234_0000)]);
        assert_eq!(block_on(ensure_standby(&mut bus)), Ok(false));
        assert_eq!(bus.writes, 0);
    }

    #[test]
    fn ensure_standby_rejects_an_ignored_shadow_write() {
        use crate::mcf8316::fields::DEV_MODE_SLEEP;

        let mut bus = FakeBus::with(&[(reg::DEVICE_CONFIG2, DEV_MODE_SLEEP)]);
        bus.write_ignored = Some(reg::DEVICE_CONFIG2);
        assert_eq!(
            block_on(ensure_standby(&mut bus)),
            Err(ConfigFault::Mismatch {
                address: reg::DEVICE_CONFIG2
            })
        );
    }

    #[test]
    fn the_committed_image_is_the_complete_loaded_capture() {
        assert_eq!(IMAGE, LOADED_IMAGE);
        assert_eq!(IMAGE.len(), reg::configuration().count());
    }

    #[test]
    fn loaded_candidates_claim_only_reviewed_acoustic_fields() {
        use crate::mcf8316::fields;

        for candidate in TuneCandidate::ALL {
            let setting = candidate.setting();
            let allowed = match setting.address {
                0x088 => {
                    setting.mask == fields::PWM_FREQ_OUT_MASK
                        || setting.mask == fields::DEADTIME_COMP_EN
                }
                reg::GD_CONFIG1 => setting.mask == fields::SLEW_RATE_MASK,
                _ => false,
            };
            assert!(
                allowed,
                "{} touches an unreviewed field",
                candidate.as_str()
            );
            assert_eq!(setting.value & !setting.mask, 0);
        }
    }

    #[test]
    fn host_and_firmware_candidate_names_cannot_drift() {
        let host_names = include_str!("../../scripts/loaded-tune-candidates.txt");
        assert_eq!(host_names.lines().count(), TuneCandidate::ALL.len());
        for candidate in TuneCandidate::ALL {
            assert!(
                host_names.lines().any(|name| name == candidate.as_str()),
                "{} is absent from the host allowlist",
                candidate.as_str()
            );
        }
    }

    #[test]
    fn a_loaded_candidate_restores_golden_then_changes_only_its_mask() {
        let candidate = TuneCandidate::Pwm30Khz;
        let override_setting = candidate.setting();
        let mut bus = FakeBus::default();
        bus.registers.insert(reg::CONTROLLER_FAULT_STATUS, 0);
        bus.registers.insert(0x080, 0xDEAD_BEEF);

        let (_, verdict) = block_on(stage_loaded_candidate(&mut bus, candidate));
        assert_eq!(verdict, ConfigCheck::Tuning);
        for golden in LOADED_IMAGE {
            let read = bus.registers.get(&golden.address).copied().unwrap_or(0);
            if golden.address == override_setting.address {
                assert!(override_setting.matches(read));
                assert_eq!(
                    read & !override_setting.mask,
                    golden.value & !override_setting.mask
                );
            } else {
                assert!(
                    golden.matches(read),
                    "{} did not return to golden",
                    golden.name
                );
            }
        }
        assert_eq!(
            bus.registers.get(&reg::ALGO_CTRL1),
            None,
            "a tuning candidate must never issue the EEPROM command"
        );
    }

    #[test]
    fn every_named_loaded_candidate_round_trips_without_an_eeprom_command() {
        for candidate in TuneCandidate::ALL {
            let mut bus = FakeBus::default();
            bus.registers.insert(reg::CONTROLLER_FAULT_STATUS, 0);
            for golden in LOADED_IMAGE {
                bus.registers.insert(golden.address, golden.value);
            }
            let (_, verdict) = block_on(stage_loaded_candidate(&mut bus, *candidate));
            assert_eq!(verdict, ConfigCheck::Tuning, "{}", candidate.as_str());
            assert_eq!(
                block_on(check_loaded_candidate(&mut bus, *candidate)),
                ConfigCheck::Tuning,
                "{}",
                candidate.as_str()
            );
            assert_eq!(
                bus.registers.get(&reg::ALGO_CTRL1),
                None,
                "{} issued an EEPROM command",
                candidate.as_str()
            );
        }
    }

    #[test]
    fn a_candidate_override_that_does_not_stick_is_not_runnable() {
        let candidate = TuneCandidate::Pwm30Khz;
        let mut bus = FakeBus::default();
        bus.registers.insert(reg::CONTROLLER_FAULT_STATUS, 0);
        for golden in LOADED_IMAGE {
            bus.registers.insert(golden.address, golden.value);
        }
        bus.write_ignored = Some(candidate.setting().address);
        let (_, verdict) = block_on(stage_loaded_candidate(&mut bus, candidate));
        assert_eq!(
            verdict,
            ConfigCheck::Failed(ConfigFault::Mismatch {
                address: candidate.setting().address
            })
        );
    }

    #[test]
    fn the_loaded_candidate_sentinel_detects_shadow_reload() {
        let candidate = TuneCandidate::Pwm30Khz;
        let mut bus = FakeBus::default();
        bus.registers.insert(reg::CONTROLLER_FAULT_STATUS, 0);
        for golden in LOADED_IMAGE {
            bus.registers.insert(golden.address, golden.value);
        }
        let setting = candidate.setting();
        let current = bus.registers[&setting.address];
        bus.registers
            .insert(setting.address, setting.merge(current));
        assert_eq!(
            block_on(check_loaded_candidate_sentinel(&mut bus, candidate)),
            ConfigCheck::Tuning
        );

        let golden = LOADED_IMAGE
            .iter()
            .find(|item| item.address == setting.address)
            .unwrap();
        bus.registers.insert(setting.address, golden.value);
        assert_eq!(
            block_on(check_loaded_candidate_sentinel(&mut bus, candidate)),
            ConfigCheck::Failed(ConfigFault::Mismatch {
                address: setting.address
            })
        );
    }

    #[test]
    fn every_image_entry_is_a_configuration_register_with_a_masked_value() {
        // Runs against whatever IMAGE holds, so a bad capture is caught the day it lands.
        for setting in IMAGE {
            assert!(
                crate::mcf8316::is_configuration(setting.address),
                "{} is not in the configuration block",
                setting.name
            );
            assert_eq!(
                setting.value & !setting.mask,
                0,
                "{} carries bits outside its mask",
                setting.name
            );
            assert_ne!(setting.mask, 0, "{} claims no bits at all", setting.name);
        }
    }

    #[test]
    fn unloaded_words_match_the_reviewed_datasheet_transcription() {
        let expected = [
            (0x084, 0x22E6_0000),
            (0x086, 0x1101_28AB),
            (0x088, 0x3E01_810C),
            (0x08A, 0x0000_B1AE),
            (0x08C, 0x6000_0004),
            (0x08E, 0x50C2_0168),
            (0x090, ACQUISITION_FAULT_CONFIG1),
            (0x092, 0x31C0_47C0),
            (0x0A0, 0x000E_0000),
            (0x0A2, 0x0000_0000),
            (0x0A4, 0x0020_0041),
            (0x0A6, 0x0000_0001),
            (0x0A8, 0x0000_001F),
            (0x0AA, 0x0022_0000),
            (0x0AC, 0x0001_0003),
        ];
        assert_eq!(UNLOADED_IMAGE.len(), expected.len());
        for (setting, (address, value)) in UNLOADED_IMAGE.iter().zip(expected) {
            assert_eq!(setting.address, address, "{} address", setting.name);
            assert_eq!(
                crate::mcf8316::reg::by_name(setting.name),
                Some(setting.address),
                "{} register-map address",
                setting.name
            );
            assert_eq!(setting.mask, 0x7FFF_FFFF, "{} parity mask", setting.name);
            assert_eq!(setting.value, value, "{} value", setting.name);
            assert!(crate::mcf8316::is_configuration(setting.address));
        }
        // Either zero re-enters implicit MPET on a normal speed command.
        let kp_code =
            ((UNLOADED_IMAGE[4].value & 0x7) << 7) | ((UNLOADED_IMAGE[5].value >> 24) & 0x7F);
        let ki_code = (UNLOADED_IMAGE[5].value >> 14) & 0x03FF;
        assert_ne!(kp_code, 0);
        assert_ne!(ki_code, 0);

        let startup1 = UNLOADED_IMAGE[0].value;
        assert_eq!((startup1 >> 29) & 0x3, 1, "double align");
        assert_eq!((startup1 >> 25) & 0xF, 1, "1 A/s align ramp");
        assert_eq!((startup1 >> 21) & 0xF, 7, "750 ms align time");
        assert_eq!((startup1 >> 17) & 0xF, 3, "1 A align current");
        assert_eq!(
            (startup1 >> 2) & 0x1,
            0,
            "Iq ramp disabled because it traps later speed changes on this motor"
        );

        let startup2 = UNLOADED_IMAGE[1].value;
        assert_eq!((startup2 >> 27) & 0xF, 2, "0.5 A open-loop current");
        assert_eq!((startup2 >> 23) & 0xF, 2, "1 electrical Hz/s A1");
        assert_eq!((startup2 >> 19) & 0xF, 0, "zero A2");
        assert_eq!((startup2 >> 18) & 0x1, 0, "manual handoff");
        assert_eq!(
            (startup2 >> 13) & 0x1F,
            0x9,
            "10 percent of 180 RPM is an 18 RPM handoff"
        );
        assert_eq!((startup2 >> 8) & 0x1F, 0x8, "90 degree align angle");
        assert_eq!(
            (startup2 >> 4) & 0xF,
            0xA,
            "5 percent first-cycle frequency"
        );
        assert_eq!(
            (startup2 >> 3) & 0x1,
            1,
            "start open loop at the configured first-cycle frequency"
        );
        assert_eq!(startup2 & 0x7, 3, "0.15 degree/ms theta ramp");

        let closed_loop1 = UNLOADED_IMAGE[2].value;
        assert_eq!(
            closed_loop1 & crate::mcf8316::fields::CL_ACC_MASK,
            crate::mcf8316::fields::CL_ACC_NO_LIMIT,
            "firmware owns the single acceleration ramp"
        );
        assert_ne!(
            closed_loop1 & crate::mcf8316::fields::DEADTIME_COMP_EN,
            0,
            "TI-recommended dead-time compensation must not silently return to reset zero"
        );
        assert_eq!(
            closed_loop1 & crate::mcf8316::fields::PWM_FREQ_OUT_MASK,
            crate::mcf8316::fields::PWM_FREQ_OUT_25_KHZ,
            "25 kHz acoustically qualified phase PWM"
        );
        assert_ne!(closed_loop1 & (1 << 3), 0, "AVS baseline remains enabled");

        let fault1 = UNLOADED_IMAGE[6].value;
        assert_eq!((fault1 >> 27) & 0xF, 1, "0.25 A startup current");
        assert_eq!((fault1 >> 23) & 0xF, 5, "2 A hardware lock threshold");
        assert_eq!((fault1 >> 19) & 0xF, 5, "2 A software lock threshold");
        assert_eq!(
            RUNNING_FAULT_CONFIG1 & !crate::mcf8316::fields::ILIMIT_MASK,
            ACQUISITION_FAULT_CONFIG1 & !crate::mcf8316::fields::ILIMIT_MASK,
            "the running profile may change only ILIMIT"
        );
        assert_eq!(
            RUNNING_FAULT_CONFIG1 & crate::mcf8316::fields::ILIMIT_MASK,
            crate::mcf8316::fields::ILIMIT_0P25_A
        );
        assert_eq!(
            SETTLING_FAULT_CONFIG1 & !crate::mcf8316::fields::ILIMIT_MASK,
            ACQUISITION_FAULT_CONFIG1 & !crate::mcf8316::fields::ILIMIT_MASK,
            "the settling profile may change only ILIMIT"
        );
        assert_eq!(
            SETTLING_FAULT_CONFIG1 & crate::mcf8316::fields::ILIMIT_MASK,
            crate::mcf8316::fields::ILIMIT_0P125_A
        );
        let closed_loop3 = UNLOADED_IMAGE[4].value;
        let closed_loop4 = UNLOADED_IMAGE[5].value;
        assert_eq!(
            ((closed_loop3 & 0x7) << 7) | ((closed_loop4 >> 24) & 0x7F),
            0x250,
            "0.008 speed-loop Kp"
        );
        assert_eq!((closed_loop4 >> 14) & 0x3FF, 0x308, "0.0016 speed-loop Ki");

        let device_config1 = UNLOADED_IMAGE[11].value;
        assert_eq!(
            device_config1 & crate::mcf8316::fields::BUS_VOLT_MASK,
            crate::mcf8316::fields::BUS_VOLT_30_V,
            "24 V supply requires the 30 V measurement range"
        );
        assert_eq!(
            IMAGE
                .iter()
                .find(|setting| setting.address == reg::DEVICE_CONFIG1)
                .unwrap()
                .value
                & crate::mcf8316::fields::I2C_TARGET_ADDR_MASK,
            u32::from(crate::mcf8316::DEFAULT_TARGET_ID) << 20,
            "golden image must preserve the documented I2C target across power cycles"
        );
        let device_config2 = UNLOADED_IMAGE[12].value;
        assert_eq!(
            device_config2 & crate::mcf8316::fields::DYNAMIC_VOLTAGE_GAIN_EN,
            0,
            "dynamic voltage gain selected the same 30 V range and regressed startup"
        );
        assert_eq!(
            device_config2 & crate::mcf8316::fields::DYNAMIC_CSA_GAIN_EN,
            0
        );
        let pin_config = UNLOADED_IMAGE[10].value;
        assert_eq!(pin_config & crate::mcf8316::fields::VDC_FILTER_MASK, 0);

        let gd_config1 = UNLOADED_IMAGE[14].value;
        assert_eq!(gd_config1 & crate::mcf8316::fields::SLEW_RATE_MASK, 0);
        assert_eq!(
            gd_config1 & crate::mcf8316::fields::CSA_GAIN_MASK,
            crate::mcf8316::fields::CSA_GAIN_1P2_V_PER_A,
            "maximum current gain outlasted the lower-gain candidates"
        );

        let fault2 = UNLOADED_IMAGE[7].value;
        assert_eq!(
            (fault2 >> 28) & 0x7,
            0x3,
            "abnormal-BEMF and no-motor locks enabled; false-prone abnormal-speed lock disabled"
        );
        assert_eq!(
            (fault2 >> 22) & 0x7,
            7,
            "70 percent abnormal-BEMF tolerance"
        );
        assert_eq!(
            (fault2 >> 13) & 0x7,
            2,
            "2 microsecond hardware-current deglitch"
        );

        let int_algo1 = UNLOADED_IMAGE[8].value;
        assert_eq!((int_algo1 >> 17) & 0x7, 7, "1.5 V automatic-handoff floor");

        let peri_config1 = UNLOADED_IMAGE[13].value;
        assert_eq!(
            (peri_config1 >> 9) & 0x1,
            0,
            "normal 325 Hz-100 kHz SPEED input band"
        );
        assert!((325..=100_000).contains(&crate::config::SPEED_CARRIER_HZ));
    }

    #[test]
    fn a_captured_image_pins_every_register_the_board_wiring_depends_on() {
        // The capture checklist in [`IMAGE`]'s doc, enforced: PCB-01 wires SPEED as PWM,
        // ALARM into the thermal-stop path, and carries the 180 RPM stored ceiling — all
        // dead at register reset defaults. An image that omits these registers passes
        // check() while leaving that copper inert.
        for required in [
            reg::PIN_CONFIG,
            reg::PERI_CONFIG1,
            reg::GD_CONFIG1,
            reg::CLOSED_LOOP4,
        ] {
            assert!(
                IMAGE.iter().any(|s| s.address == required),
                "captured image does not pin register {required:#05x} (see the capture \
                 checklist on IMAGE)"
            );
        }
    }

    #[test]
    fn ext_wdt_gpio_mode_requires_a_window_the_heartbeat_can_satisfy() {
        // The round-3 board review's cross-subsystem trap: EXT_WD is wired to the same
        // fixed heartbeat as the TPS3435, a rising edge every
        // 1000 / WATCHDOG_HEARTBEAT_HZ ms. The MCF's GPIO tickle windows are 100/200/500/
        // 1000 ms and the reset default is 100 ms — enabling GPIO tickle with any window
        // that does not comfortably exceed the heartbeat period faults the instant the
        // feature turns on. "Comfortably" = strictly greater than the edge period, which
        // at 2 Hz admits only the 1000 ms window (500 ms is edge-on-deadline).
        use crate::mcf8316::fields::*;

        let edge_period_ms = 1_000 / crate::config::WATCHDOG_HEARTBEAT_HZ;
        for setting in IMAGE {
            if setting.address != reg::DEVICE_CONFIG2 {
                continue;
            }
            let claims = |bits: u32| setting.mask & bits == bits;
            let gpio_wdt_enabled = claims(EXT_WDT_EN | EXT_WDT_INPUT_MODE_GPIO)
                && setting.value & EXT_WDT_EN != 0
                && setting.value & EXT_WDT_INPUT_MODE_GPIO != 0;
            if !gpio_wdt_enabled {
                continue;
            }
            assert!(
                claims(EXT_WDT_CONFIG_MASK),
                "{}: enables GPIO watchdog tickle without claiming EXT_WDT_CONFIG — the \
                 reset window is 100 ms, which the {edge_period_ms} ms heartbeat can never \
                 satisfy",
                setting.name
            );
            let window_ms = EXT_WDT_GPIO_WINDOW_MS
                [((setting.value & EXT_WDT_CONFIG_MASK) >> EXT_WDT_CONFIG_SHIFT) as usize];
            assert!(
                window_ms > edge_period_ms,
                "{}: EXT_WDT_CONFIG selects a {window_ms} ms window but the heartbeat's \
                 rising edge lands every {edge_period_ms} ms — the watchdog would fault \
                 immediately (or on the first jitter)",
                setting.name
            );
        }
    }

    #[test]
    fn the_max_speed_setting_encodes_the_stored_ceiling_and_nothing_else() {
        use crate::mcf8316::{max_speed_to_milli_rpm, seeds};

        let setting = max_speed_setting(seeds::MAX_SPEED);
        assert_eq!(setting.address, reg::CLOSED_LOOP4);
        // The seed value means 180 RPM through the documented scaling; the setting must
        // carry it verbatim inside the mask.
        assert_eq!(
            max_speed_to_milli_rpm(seeds::MAX_SPEED, crate::config::POLE_PAIRS),
            crate::speed::MilliRpm(crate::config::RPM_MCF_LIMIT * 1_000)
        );
        assert_eq!(setting.value, u32::from(seeds::MAX_SPEED));
        // Kp/Ki live in the same register's upper bits; a register whose gains are already
        // bench-tuned must still match, and a wrong ceiling must still fail.
        assert!(setting.matches(0xDEAD_C000 | u32::from(seeds::MAX_SPEED)));
        assert!(!setting.matches(0xDEAD_C000 | u32::from(seeds::MAX_SPEED + 6)));
    }

    #[test]
    fn a_matching_image_verifies() {
        let image = [Setting::whole("A", A, 0x1234_5678)];
        let mut bus = FakeBus::with(&[(A, 0x1234_5678)]);
        assert_eq!(block_on(check(&mut bus, &image)), ConfigCheck::Verified);
    }

    #[test]
    fn a_single_wrong_bit_fails_the_check() {
        let image = [Setting::whole("A", A, 0x1234_5678)];
        let mut bus = FakeBus::with(&[(A, 0x1234_5679)]);
        assert_eq!(
            block_on(check(&mut bus, &image)),
            ConfigCheck::Failed(ConfigFault::Mismatch { address: A })
        );
    }

    #[test]
    fn a_masked_setting_ignores_the_bits_it_does_not_claim() {
        // The in-between state: one field derived, the rest of the register still unknown.
        let image = [Setting::masked("A", A, 0x0000_00F0, 0x0000_0030)];
        let mut bus = FakeBus::with(&[(A, 0xDEAD_BE3F)]);
        assert_eq!(block_on(check(&mut bus, &image)), ConfigCheck::Verified);

        let mut bus = FakeBus::with(&[(A, 0xDEAD_BE4F)]);
        assert_eq!(
            block_on(check(&mut bus, &image)),
            ConfigCheck::Failed(ConfigFault::Mismatch { address: A })
        );
    }

    #[test]
    fn masked_construction_drops_bits_outside_the_mask() {
        let setting = Setting::masked("A", A, 0x0000_00F0, 0xFFFF_FFFF);
        assert_eq!(setting.value, 0x0000_00F0);
        assert!(setting.matches(0x0000_00F0));
        assert_eq!(setting.merge(0x1234_5605), 0x1234_56F5);
    }

    #[test]
    fn the_devices_own_eeprom_verdict_outranks_our_readback() {
        // Every image register happens to read back correctly, but the device says its
        // stored configuration failed its own CRC. Agreeing with a known-bad block is not
        // verification.
        let image = [Setting::whole("A", A, 7)];
        for bit in [
            controller_fault::EEPROM_ERR,
            controller_fault::EEPROM_WRITE_LOCK,
            controller_fault::EEPROM_READ_LOCK,
        ] {
            let mut bus = FakeBus::with(&[(A, 7), (reg::CONTROLLER_FAULT_STATUS, bit)]);
            assert_eq!(
                block_on(check(&mut bus, &image)),
                ConfigCheck::Failed(ConfigFault::DeviceEeprom),
                "bit {bit:#010x}"
            );
        }
    }

    #[test]
    fn an_unrelated_fault_bit_does_not_condemn_the_configuration() {
        // Only the EEPROM bits speak to the stored configuration. A motor lock latched from
        // the previous run must not read as a corrupt EEPROM.
        let image = [Setting::whole("A", A, 7)];
        let mut bus = FakeBus::with(&[
            (A, 7),
            (reg::CONTROLLER_FAULT_STATUS, controller_fault::ABN_SPEED),
        ]);
        assert_eq!(block_on(check(&mut bus, &image)), ConfigCheck::Verified);
    }

    #[test]
    fn an_unreadable_register_fails_with_its_address() {
        let image = [Setting::whole("A", A, 7), Setting::whole("B", B, 9)];
        let mut bus = FakeBus::with(&[(A, 7), (B, 9)]);
        bus.read_fails = Some(B);
        assert_eq!(
            block_on(check(&mut bus, &image)),
            ConfigCheck::Failed(ConfigFault::Unreadable { address: B })
        );

        // And a bus that cannot even be asked about its own status fails before reading a
        // single configuration register, rather than reporting a mismatch it never saw.
        let mut bus = FakeBus {
            read_fails: Some(reg::CONTROLLER_FAULT_STATUS),
            ..FakeBus::default()
        };
        assert_eq!(
            block_on(check(&mut bus, &image)),
            ConfigCheck::Failed(ConfigFault::Unreadable {
                address: reg::CONTROLLER_FAULT_STATUS
            })
        );
    }

    #[test]
    fn apply_writes_only_what_is_wrong() {
        let image = [
            Setting::whole("A", A, 0x1111),
            Setting::whole("B", B, 0x2222),
        ];
        let mut bus = FakeBus::with(&[(A, 0x1111), (B, 0)]);
        let (applied, check) = block_on(apply(&mut bus, &image));
        assert_eq!(
            applied,
            Applied {
                written: 1,
                unchanged: 1
            }
        );
        assert_eq!(check, ConfigCheck::Verified);
        assert_eq!(bus.writes, 2, "expected one shadow write and one commit");
        assert!(
            bus.delayed_ms >= crate::mcf8316::EEPROM_WRITE_MIN_MS,
            "read back before TI's minimum EEPROM interval"
        );
        assert_eq!(bus.registers[&B], 0x2222);
    }

    #[test]
    fn apply_does_not_burn_an_eeprom_cycle_when_everything_matches() {
        let image = [Setting::whole("A", A, 0x1111)];
        let mut bus = FakeBus::with(&[(A, 0x1111)]);
        let (applied, check) = block_on(apply(&mut bus, &image));
        assert_eq!(applied.written, 0);
        assert_eq!(check, ConfigCheck::Verified);
        assert_eq!(bus.writes, 0);
        assert_eq!(bus.delayed_ms, 0);
    }

    #[test]
    fn stage_writes_and_verifies_without_an_eeprom_commit() {
        let image = [
            Setting::whole("A", A, 0x1111),
            Setting::whole("B", B, 0x2222),
        ];
        let mut bus = FakeBus::with(&[(A, 0), (B, 0x2222)]);
        let (applied, check) = block_on(write_volatile_image(&mut bus, &image));
        assert_eq!(
            applied,
            Applied {
                written: 1,
                unchanged: 1
            }
        );
        assert_eq!(check, ConfigCheck::Verified);
        assert_eq!(bus.writes, 1, "stage issued an EEPROM command");
        assert_eq!(bus.delayed_ms, 0, "stage entered the EEPROM delay path");
        assert_eq!(bus.registers[&A], 0x1111);
        assert!(!bus.registers.contains_key(&reg::ALGO_CTRL1));
    }

    #[test]
    fn public_stage_authorizes_only_the_fixed_provisional_image() {
        let mut bus = FakeBus::default();
        let (applied, check) = block_on(stage(&mut bus));
        assert_eq!(usize::from(applied.written), PROVISIONAL_IMAGE.len() - 1);
        assert_eq!(applied.unchanged, 1);
        assert_eq!(check, ConfigCheck::Provisional);
        assert_eq!(bus.writes, PROVISIONAL_IMAGE.len() - 1);
        assert_eq!(bus.delayed_ms, 0);
        assert!(!bus.registers.contains_key(&reg::ALGO_CTRL1));
    }

    #[test]
    fn provisional_sentinel_detects_a_shadow_reset() {
        let mut bus = FakeBus::with(&[(PROVISIONAL_SENTINEL.address, PROVISIONAL_SENTINEL.value)]);
        assert_eq!(
            block_on(check_provisional_sentinel(&mut bus)),
            ConfigCheck::Provisional
        );
        bus.registers.insert(PROVISIONAL_SENTINEL.address, 0);
        assert_eq!(
            block_on(check_provisional_sentinel(&mut bus)),
            ConfigCheck::Failed(ConfigFault::Mismatch {
                address: PROVISIONAL_SENTINEL.address
            })
        );
    }

    #[test]
    fn a_motor_rail_falling_edge_invalidates_any_runnable_verdict() {
        for verdict in [
            ConfigCheck::Provisional,
            ConfigCheck::Tuning,
            ConfigCheck::Verified,
        ] {
            assert_eq!(after_pgood_loss(true, verdict), ConfigCheck::Unverified);
            assert_eq!(after_pgood_loss(false, verdict), verdict);
        }
    }

    #[test]
    fn an_empty_provisional_image_cannot_authorize_operation() {
        let mut bus = FakeBus::default();
        let (applied, check) = block_on(write_volatile_image(&mut bus, &[]));
        assert_eq!(applied, Applied::default());
        assert_eq!(check, ConfigCheck::Unverified);
        assert_eq!(bus.writes, 0);
    }

    #[test]
    fn apply_fails_if_the_eeprom_command_never_self_clears() {
        let image = [Setting::whole("A", A, 0x1111)];
        let mut bus = FakeBus::with(&[(A, 0)]);
        bus.commit_stuck = true;
        let (_, check) = block_on(apply(&mut bus, &image));
        assert_eq!(check, ConfigCheck::Failed(ConfigFault::CommitUnconfirmed));
        assert!(bus.delayed_ms >= 2_000);
    }

    #[test]
    fn apply_distinguishes_a_commit_bus_failure() {
        let image = [Setting::whole("A", A, 0x1111)];
        let mut bus = FakeBus::with(&[(A, 0)]);
        bus.write_fails = Some(reg::ALGO_CTRL1);
        let (_, check) = block_on(apply(&mut bus, &image));
        assert_eq!(check, ConfigCheck::Failed(ConfigFault::CommitUnreadable));
    }

    #[test]
    fn apply_preserves_the_bits_a_masked_setting_does_not_claim() {
        let image = [Setting::masked("A", A, 0x0000_FF00, 0x0000_AB00)];
        let mut bus = FakeBus::with(&[(A, 0x1234_56FF)]);
        block_on(apply(&mut bus, &image));
        assert_eq!(bus.registers[&A], 0x1234_ABFF);
    }

    #[test]
    fn apply_fails_when_a_write_does_not_stick() {
        // The failure the read-back pass exists for: the bus accepts the write and the
        // register does not change. Without verification this returns success.
        let image = [Setting::whole("A", A, 0x1111)];
        let mut bus = FakeBus::with(&[(A, 0)]);
        bus.write_ignored = Some(A);
        let (applied, check) = block_on(apply(&mut bus, &image));
        assert_eq!(applied.written, 1, "believed it had written the register");
        assert_eq!(
            check,
            ConfigCheck::Failed(ConfigFault::Mismatch { address: A }),
            "reported success for a write that did not stick"
        );
    }

    #[test]
    fn apply_reports_a_refused_write_rather_than_continuing() {
        let image = [
            Setting::whole("A", A, 0x1111),
            Setting::whole("B", B, 0x2222),
        ];
        let mut bus = FakeBus::with(&[]);
        bus.write_fails = Some(A);
        let (_, check) = block_on(apply(&mut bus, &image));
        assert_eq!(
            check,
            ConfigCheck::Failed(ConfigFault::Mismatch { address: A })
        );
        assert!(
            !bus.registers.contains_key(&B),
            "kept configuring past a refused write"
        );
    }

    #[test]
    fn a_configuration_write_invalidates_a_standing_verdict() {
        // The bench hazard this exists for: derive a bit field with `reg write`, walk away,
        // and a `Verified` from before the write is still standing while the device holds
        // something else entirely.
        let image = [Setting::whole("A", A, 0x1111)];
        let mut bus = FakeBus::with(&[(A, 0x1111)]);
        assert_eq!(block_on(check(&mut bus, &image)), ConfigCheck::Verified);

        let verdict = block_on(write_and_recheck(&mut bus, A, 0x2222, &image));
        assert_eq!(
            verdict,
            Ok(Some(ConfigCheck::Failed(ConfigFault::Mismatch {
                address: A
            }))),
            "a write that diverged from the image left the old verdict standing"
        );
        assert_eq!(
            bus.registers[&A], 0x2222,
            "the write itself must still land"
        );
        assert_eq!(
            bus.writes, 1,
            "an exploratory shadow write also committed EEPROM"
        );
        assert_eq!(
            bus.delayed_ms, 0,
            "a raw shadow write entered the commit path"
        );
    }

    #[test]
    fn a_write_outside_the_configuration_block_changes_no_verdict() {
        // RAM registers are written constantly during tuning; re-verifying the EEPROM block
        // on every one of them would be two dozen wasted reads apiece.
        let image = [Setting::whole("A", A, 0x1111)];
        let mut bus = FakeBus::with(&[(A, 0x1111)]);
        let before = bus.reads;
        assert_eq!(
            block_on(write_and_recheck(&mut bus, reg::ALGO_CTRL1, 7, &image)),
            Ok(None)
        );
        assert_eq!(
            bus.reads, before,
            "re-verified after a non-configuration write"
        );
        assert_eq!(bus.registers[&reg::ALGO_CTRL1], 7);
    }

    #[test]
    fn a_failed_write_is_reported_rather_than_re_verified() {
        let image = [Setting::whole("A", A, 0x1111)];
        let mut bus = FakeBus {
            write_fails: Some(A),
            ..FakeBus::default()
        };
        assert_eq!(
            block_on(write_and_recheck(&mut bus, A, 0x2222, &image)),
            Err(())
        );
    }

    #[test]
    fn verdicts_gate_operation_as_documented() {
        assert!(!ConfigCheck::Pending.permits_operation());
        assert!(!ConfigCheck::Failed(ConfigFault::DeviceEeprom).permits_operation());
        assert!(!ConfigCheck::Unverified.permits_operation());
        assert!(ConfigCheck::Provisional.permits_operation());
        assert!(ConfigCheck::Tuning.permits_operation());
        assert!(ConfigCheck::Verified.permits_operation());

        assert!(!ConfigCheck::Pending.settled());
        assert!(ConfigCheck::Unverified.settled());
        assert!(ConfigCheck::Provisional.settled());
        assert!(ConfigCheck::Tuning.settled());
        assert!(ConfigCheck::Verified.settled());
        assert!(ConfigCheck::Failed(ConfigFault::TimedOut).settled());
    }
}
