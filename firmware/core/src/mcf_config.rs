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
/// **Empty on purpose.** No tuned device has been captured yet; the values in
/// `docs/controls.md` are commissioning seeds, not measurements. An
/// image invented from those seeds would be worse than none: [`check`] would pass against a
/// fiction and `SafeBoot`'s "stored configuration verified" clause would read as satisfied
/// while verifying nothing.
///
/// While it is empty, [`check`] reports [`ConfigCheck::Unverified`] rather than
/// [`ConfigCheck::Verified`], the supervisor remains in `SafeBoot`, and every telemetry frame
/// and CSV row carries that fact. Filling it in is a bench step, not a code change:
///
/// ```text
/// stillair --port /dev/cu.usbmodem101 config capture
/// ```
///
/// prints this table from a live device, ready to paste.
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
pub const IMAGE: &[Setting] = &[];

/// Volatile-only first-spin configuration for the unloaded GL100 commissioning bench.
///
/// This is deliberately separate from [`IMAGE`]. It uses vendor motor data and conservative
/// first-spin gains, not values qualified with the final rotor, so it must never be committed
/// to EEPROM or described as the golden configuration. `config stage` writes these settings
/// to the MCF shadow registers and a power cycle erases them.
///
/// Values are lower-31-bit register words from MCF8316D SLLSFX9A Tables 8-5 through 8-32;
/// bit 31 is the silicon's read-only parity bit. The 0.5 A speed-loop seed uses TI tuning-guide
/// equations Kp = Iq / maximum electrical Hz and Ki = 0.1 Kp, rounded down to Kp=0.008 and
/// Ki=0.0008. It is only a controlled first-spin starting point.
pub const PROVISIONAL_SENTINEL: Setting =
    Setting::masked("CLOSED_LOOP4", 0x08E, 0x7FFF_FFFF, 0x50C2_0168);

pub const PROVISIONAL_IMAGE: &[Setting] = &[
    Setting::masked("MOTOR_STARTUP1", 0x084, 0x7FFF_FFFF, 0x22E4_0004),
    Setting::masked("MOTOR_STARTUP2", 0x086, 0x7FFF_FFFF, 0x1101_C002),
    Setting::masked("CLOSED_LOOP1", 0x088, 0x7FFF_FFFF, 0x0003_0108),
    Setting::masked("CLOSED_LOOP2", 0x08A, 0x7FFF_FFFF, 0x0000_B1AE),
    Setting::masked("CLOSED_LOOP3", 0x08C, 0x7FFF_FFFF, 0x6500_0004),
    PROVISIONAL_SENTINEL,
    Setting::masked("FAULT_CONFIG1", 0x090, 0x7FFF_FFFF, 0x12A8_0000),
    Setting::masked("FAULT_CONFIG2", 0x092, 0x7FFF_FFFF, 0x7000_47C0),
    Setting::masked("INT_ALGO_1", 0x0A0, 0x7FFF_FFFF, 0x000A_0000),
    Setting::masked("INT_ALGO_2", 0x0A2, 0x7FFF_FFFF, 0x0000_0000),
    Setting::masked("PIN_CONFIG", 0x0A4, 0x7FFF_FFFF, 0x0020_0041),
    Setting::masked("DEVICE_CONFIG2", 0x0A8, 0x7FFF_FFFF, 0x0000_001F),
    Setting::masked("PERI_CONFIG1", 0x0AA, 0x7FFF_FFFF, 0x0022_0000),
    Setting::masked("GD_CONFIG1", 0x0AC, 0x7FFF_FFFF, 0x0001_0000),
];

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
/// Five values rather than a `bool` because "we have not checked yet", "there is nothing to
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
        matches!(self, Self::Provisional | Self::Verified)
    }

    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Pending => "pending",
            Self::Unverified => "unverified",
            Self::Provisional => "provisional",
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

/// Cheaply detect an MCF reset that silently reloaded EEPROM while its rail stayed high.
///
/// CLOSED_LOOP4 contains both nonzero speed-loop gains and the 180 RPM ceiling, and reset
/// silicon does not reproduce this word. The full image is still checked by `config stage`
/// and an explicit `config check`; this sentinel runs on every status cycle.
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
    fn the_committed_image_is_empty_until_a_device_is_captured() {
        // A guard against an image being invented from the commissioning seeds in
        // docs/controls.md. When this fails, it should be because a real capture landed —
        // and then the every-value-is-masked test below starts doing the real work.
        assert!(
            IMAGE.is_empty(),
            "IMAGE has entries; they must come from `config capture` on a real device"
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
    fn provisional_words_match_the_reviewed_datasheet_transcription() {
        let expected = [
            (0x084, 0x22E4_0004),
            (0x086, 0x1101_C002),
            (0x088, 0x0003_0108),
            (0x08A, 0x0000_B1AE),
            (0x08C, 0x6500_0004),
            (0x08E, 0x50C2_0168),
            (0x090, 0x12A8_0000),
            (0x092, 0x7000_47C0),
            (0x0A0, 0x000A_0000),
            (0x0A2, 0x0000_0000),
            (0x0A4, 0x0020_0041),
            (0x0A8, 0x0000_001F),
            (0x0AA, 0x0022_0000),
            (0x0AC, 0x0001_0000),
        ];
        assert_eq!(PROVISIONAL_IMAGE.len(), expected.len());
        for (setting, (address, value)) in PROVISIONAL_IMAGE.iter().zip(expected) {
            assert_eq!(setting.address, address, "{} address", setting.name);
            assert_eq!(setting.mask, 0x7FFF_FFFF, "{} parity mask", setting.name);
            assert_eq!(setting.value, value, "{} value", setting.name);
            assert!(crate::mcf8316::is_configuration(setting.address));
        }
        // Either zero re-enters implicit MPET on a normal speed command.
        let kp_code =
            ((PROVISIONAL_IMAGE[4].value & 0x7) << 7) | ((PROVISIONAL_IMAGE[5].value >> 24) & 0x7F);
        let ki_code = (PROVISIONAL_IMAGE[5].value >> 14) & 0x03FF;
        assert_ne!(kp_code, 0);
        assert_ne!(ki_code, 0);

        let startup1 = PROVISIONAL_IMAGE[0].value;
        assert_eq!((startup1 >> 29) & 0x3, 1, "double align");
        assert_eq!((startup1 >> 25) & 0xF, 1, "1 A/s align ramp");
        assert_eq!((startup1 >> 21) & 0xF, 7, "750 ms align time");
        assert_eq!((startup1 >> 17) & 0xF, 2, "0.5 A align current");
        assert_eq!((startup1 >> 2) & 0x1, 1, "Iq ramp enabled");

        let startup2 = PROVISIONAL_IMAGE[1].value;
        assert_eq!((startup2 >> 27) & 0xF, 2, "0.5 A open-loop current");
        assert_eq!((startup2 >> 23) & 0xF, 2, "1 electrical Hz/s A1");
        assert_eq!((startup2 >> 19) & 0xF, 0, "zero A2");
        assert_eq!((startup2 >> 18) & 0x1, 0, "manual handoff");
        assert_eq!(
            (startup2 >> 13) & 0x1F,
            0xE,
            "15 percent of 180 RPM is a 27 RPM handoff"
        );
        assert_eq!(startup2 & 0x7, 2, "0.1 degree/ms theta ramp");

        let fault1 = PROVISIONAL_IMAGE[6].value;
        assert_eq!((fault1 >> 27) & 0xF, 2, "0.5 A closed-loop current");
        assert_eq!((fault1 >> 23) & 0xF, 5, "2 A hardware lock threshold");
        assert_eq!((fault1 >> 19) & 0xF, 5, "2 A software lock threshold");

        let fault2 = PROVISIONAL_IMAGE[7].value;
        assert_eq!((fault2 >> 28) & 0x7, 0x7, "all three motor locks enabled");
        assert_eq!(
            (fault2 >> 13) & 0x7,
            2,
            "2 microsecond hardware-current deglitch"
        );

        let int_algo1 = PROVISIONAL_IMAGE[8].value;
        assert_eq!((int_algo1 >> 17) & 0x7, 5, "1 V automatic-handoff floor");

        let peri_config1 = PROVISIONAL_IMAGE[12].value;
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
        // check() while leaving that copper inert. Trivially satisfied while IMAGE is
        // empty; the day a capture lands, this names what it must cover.
        if IMAGE.is_empty() {
            return;
        }
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
        for verdict in [ConfigCheck::Provisional, ConfigCheck::Verified] {
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
        assert!(ConfigCheck::Verified.permits_operation());

        assert!(!ConfigCheck::Pending.settled());
        assert!(ConfigCheck::Unverified.settled());
        assert!(ConfigCheck::Provisional.settled());
        assert!(ConfigCheck::Verified.settled());
        assert!(ConfigCheck::Failed(ConfigFault::TimedOut).settled());
    }
}
