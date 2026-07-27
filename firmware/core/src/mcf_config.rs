//! The MCF8316D configuration image: what the device must be holding before the fan runs.
//!
//! `docs/controls.md` > "Initial MCF8316D configuration" describes the configuration in
//! words — latched fault modes, `SPEED_RANGE_SEL` = 1h, IPD startup, a 180 RPM stored
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
/// **Empty on purpose.** No device has been captured yet — the MCF8316D is on the unbuilt V1
/// board, and the values in `docs/controls.md` are commissioning seeds, not measurements. An
/// image invented from those seeds would be worse than none: [`check`] would pass against a
/// fiction and `SafeBoot`'s "stored configuration verified" clause would read as satisfied
/// while verifying nothing.
///
/// While it is empty, [`check`] reports [`ConfigCheck::Unverified`] rather than
/// [`ConfigCheck::Verified`], the supervisor runs but says so, and every telemetry frame and
/// CSV row carries that fact. Filling it in is a bench step, not a code change:
///
/// ```text
/// stillair --port /dev/tty.usbmodem1101 config capture
/// ```
///
/// prints this table from a live device, ready to paste.
pub const IMAGE: &[Setting] = &[];

/// Why a configuration check failed.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ConfigFault {
    /// The device reports its own EEPROM as errored or locked. Its stored configuration is
    /// not trustworthy no matter what our read-back says, because an interrupted EEPROM
    /// write is caught by the MCF's CRC and held at Hi-Z (`docs/controls.md`).
    DeviceEeprom,
    /// A register did not read back as [`IMAGE`] requires.
    Mismatch { address: u16 },
    /// The register could not be read at all.
    Unreadable { address: u16 },
    /// The check did not finish in time. Reported by the supervisor, not by [`check`].
    TimedOut,
}

/// The verdict on the device's stored configuration.
///
/// Four values rather than a `bool` because "we have not checked yet", "there is nothing to
/// check against yet", and "we checked and it is right" are three genuinely different things,
/// and collapsing the middle one into either neighbour is how a safety gate becomes theatre.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum ConfigCheck {
    /// The check has not produced a verdict yet. `SafeBoot` waits for one.
    #[default]
    Pending,
    /// The device's own integrity bits are clean, but [`IMAGE`] is empty, so nothing was
    /// compared. The fan runs — the harness has to be usable before there is anything to
    /// capture — and every frame it emits carries this so a bench capture records that it was
    /// taken against an unverified configuration.
    Unverified,
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
        matches!(self, Self::Unverified | Self::Verified)
    }

    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Pending => "pending",
            Self::Unverified => "unverified",
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
pub async fn apply<B: RegisterBus>(bus: &mut B, image: &[Setting]) -> Result<Applied, ConfigFault> {
    let mut applied = Applied::default();

    for setting in image {
        let read = bus
            .read(setting.address)
            .await
            .map_err(|_| ConfigFault::Unreadable {
                address: setting.address,
            })?;
        if setting.matches(read) {
            applied.unchanged += 1;
            continue;
        }
        bus.write(setting.address, setting.merge(read))
            .await
            .map_err(|_| ConfigFault::Mismatch {
                address: setting.address,
            })?;
        applied.written += 1;
    }

    // Re-read everything rather than trusting the writes. `RegisterBus::write` promises
    // nothing about the value sticking, and a configuration that silently did not take is the
    // failure this whole module exists to make impossible.
    match check(bus, image).await {
        ConfigCheck::Verified | ConfigCheck::Unverified => Ok(applied),
        ConfigCheck::Failed(fault) => Err(fault),
        ConfigCheck::Pending => unreachable!("check never returns Pending"),
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
        reads: usize,
        writes: usize,
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
        let applied = block_on(apply(&mut bus, &image)).expect("apply");
        assert_eq!(
            applied,
            Applied {
                written: 1,
                unchanged: 1
            }
        );
        assert_eq!(bus.writes, 1, "wrote a register that was already correct");
        assert_eq!(bus.registers[&B], 0x2222);
    }

    #[test]
    fn apply_preserves_the_bits_a_masked_setting_does_not_claim() {
        let image = [Setting::masked("A", A, 0x0000_FF00, 0x0000_AB00)];
        let mut bus = FakeBus::with(&[(A, 0x1234_56FF)]);
        block_on(apply(&mut bus, &image)).expect("apply");
        assert_eq!(bus.registers[&A], 0x1234_ABFF);
    }

    #[test]
    fn apply_fails_when_a_write_does_not_stick() {
        // The failure the read-back pass exists for: the bus accepts the write and the
        // register does not change. Without verification this returns success.
        let image = [Setting::whole("A", A, 0x1111)];
        let mut bus = FakeBus::with(&[(A, 0)]);
        bus.write_ignored = Some(A);
        assert_eq!(
            block_on(apply(&mut bus, &image)),
            Err(ConfigFault::Mismatch { address: A })
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
        assert_eq!(
            block_on(apply(&mut bus, &image)),
            Err(ConfigFault::Mismatch { address: A })
        );
        assert!(
            !bus.registers.contains_key(&B),
            "kept configuring past a refused write"
        );
    }

    #[test]
    fn verdicts_gate_operation_as_documented() {
        assert!(!ConfigCheck::Pending.permits_operation());
        assert!(!ConfigCheck::Failed(ConfigFault::DeviceEeprom).permits_operation());
        assert!(ConfigCheck::Unverified.permits_operation());
        assert!(ConfigCheck::Verified.permits_operation());

        assert!(!ConfigCheck::Pending.settled());
        assert!(ConfigCheck::Unverified.settled());
        assert!(ConfigCheck::Verified.settled());
        assert!(ConfigCheck::Failed(ConfigFault::TimedOut).settled());
    }
}
