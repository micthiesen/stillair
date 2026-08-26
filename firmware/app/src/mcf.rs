//! The MCF8316D I²C driver: the concrete [`RegisterBus`] behind `stillair-core`'s framing.
//!
//! The wire format itself lives in `stillair_core::mcf8316`, where it is unit-tested against
//! TI's published example packets. This module is only transport: it moves those bytes,
//! checks the CRC coming back, and reports failure honestly so the supervisor can decide
//! what a silent drive means.

use core::cell::Cell;
use core::sync::atomic::{AtomicBool, AtomicU16, AtomicU32, AtomicU8, Ordering};

use embassy_sync::blocking_mutex::raw::CriticalSectionRawMutex;
use embassy_sync::blocking_mutex::CriticalSectionMutex;
use embassy_sync::mutex::Mutex;
use embassy_sync::signal::Signal;
use embassy_time::{with_timeout, Duration, Timer};
use esp_hal::delay::Delay;
use esp_hal::gpio::{DriveMode, Flex, InputConfig, OutputConfig, Pin, Pull};
use esp_hal::time::Instant as HalInstant;
use stillair_core::config;
use stillair_core::console::Reply;
use stillair_core::mcf8316::{
    self, reg, value_from_bytes32, verify_read, write_frame, CrcMismatch, FaultStatus, MpetReport,
    RegisterBus,
};
use stillair_core::mcf_config::{self, ConfigCheck};
use stillair_core::speed::{mcf_digital_speed_word, SpeedDuty};
use stillair_core::state::{CurrentProfile, StatusRead};

/// Latest fault-status read, published by the I²C task and consumed by the control loop.
///
/// A `Signal` rather than a shared cell on purpose: taking it leaves nothing behind, so the
/// control loop naturally sees [`StatusRead::Stale`] when no new read has landed instead of
/// re-reading an old verdict as if it were current.
pub static STATUS: Signal<CriticalSectionRawMutex, StatusRead> = Signal::new();

/// Raised by the control loop when the supervisor emits `ClearMcfFault`, serviced by the
/// I²C task. Crossing tasks like this keeps the blocking-free control loop free of I²C.
pub static CLEAR_FAULT_REQUEST: Signal<CriticalSectionRawMutex, ()> = Signal::new();
pub static MPET_START_REQUEST: Signal<CriticalSectionRawMutex, ()> = Signal::new();
pub static MPET_ABORT_REQUEST: Signal<CriticalSectionRawMutex, ()> = Signal::new();

/// Latest supervisor-owned speed reference for the volatile I2C commissioning override.
///
/// The high-priority control task publishes this while holding the physical SPEED pin at zero.
/// The I2C task may lag by one service interval, but stop/fault revokes the hardware permission
/// latch synchronously before publishing zero, so bus latency can never keep drive permission on.
static DIGITAL_SPEED_DUTY: AtomicU16 = AtomicU16::new(0);
static CURRENT_PROFILE: AtomicU8 = AtomicU8::new(CurrentProfile::Acquisition as u8);
static CURRENT_PROFILE_READY: AtomicBool = AtomicBool::new(false);
static MPET_COMMAND: AtomicU32 = AtomicU32::new(mcf8316::MPET_START_COMMAND);

pub fn set_mpet_command(command: u32) {
    MPET_COMMAND.store(command, Ordering::Release);
}

pub fn mpet_command() -> u32 {
    MPET_COMMAND.load(Ordering::Acquire)
}

pub fn set_digital_speed(duty: SpeedDuty) {
    DIGITAL_SPEED_DUTY.store(duty.0.min(config::SPEED_DUTY_MAX), Ordering::Release);
}

pub fn set_current_profile(profile: CurrentProfile) {
    CURRENT_PROFILE.store(profile as u8, Ordering::Release);
    if profile == CurrentProfile::Acquisition {
        CURRENT_PROFILE_READY.store(false, Ordering::Release);
    }
}

pub fn current_profile_ready() -> bool {
    CURRENT_PROFILE_READY.load(Ordering::Acquire)
}

/// Forget readiness tied to the previous MCF power epoch.
pub fn invalidate_current_profile_readiness() {
    CURRENT_PROFILE_READY.store(false, Ordering::Release);
}

/// Apply the reviewed live ILIMIT variant without disturbing the other protection fields.
///
/// The staged image starts with a brief 0.25 A acquisition ceiling. Tach-confirmed rotation
/// requests a 0.125 A settling ceiling, and stable tracking restores 0.25 A for the operating
/// range. Stop and fault paths request acquisition again before another arm is possible.
/// Read-back keeps an ignored shadow write from looking done.
pub async fn service_current_profile(
    mcf: &mut Mcf,
    last_written: &mut Option<CurrentProfile>,
) -> Result<(), BusError> {
    if verdict() != ConfigCheck::Provisional {
        *last_written = None;
        CURRENT_PROFILE_READY.store(false, Ordering::Release);
        return Ok(());
    }
    let profile = match CURRENT_PROFILE.load(Ordering::Acquire) {
        value if value == CurrentProfile::Settling as u8 => CurrentProfile::Settling,
        value if value == CurrentProfile::Running as u8 => CurrentProfile::Running,
        _ => CurrentProfile::Acquisition,
    };
    if *last_written == Some(profile) {
        if profile == CurrentProfile::Acquisition {
            CURRENT_PROFILE_READY.store(true, Ordering::Release);
        }
        return Ok(());
    }
    let desired = match profile {
        CurrentProfile::Acquisition => mcf_config::ACQUISITION_FAULT_CONFIG1,
        CurrentProfile::Settling => mcf_config::SETTLING_FAULT_CONFIG1,
        CurrentProfile::Running => mcf_config::RUNNING_FAULT_CONFIG1,
    };
    if profile == CurrentProfile::Acquisition {
        // Every new acquisition request must earn readiness from a fresh readback. Clear it
        // before the first fallible bus operation so read, write, and readback errors all
        // leave startup inhibited rather than preserving readiness from an earlier run.
        CURRENT_PROFILE_READY.store(false, Ordering::Release);
    }
    let address = reg::FAULT_CONFIG1;
    let mask = mcf8316::fields::ILIMIT_MASK;
    let current = mcf.read(address).await?;
    let next = (current & !mask) | (desired & mask);
    if next != current {
        mcf.write(address, next).await?;
    }
    let readback = mcf.read(address).await?;
    if readback & mask != desired & mask {
        return Err(BusError::ReadbackMismatch);
    }
    *last_written = Some(profile);
    if profile == CurrentProfile::Acquisition {
        CURRENT_PROFILE_READY.store(true, Ordering::Release);
    }
    Ok(())
}

/// Apply the latest normalized speed through TI's volatile `ALGO_DEBUG1` override.
///
/// The override is the loaded-qualified speed path for both provisional and verified images.
/// A non-runnable verdict writes zero and selects the physical SPEED pin again. Failed writes
/// are retried because `last_written` advances only after the bus accepts the command.
pub async fn service_digital_speed(
    mcf: &mut Mcf,
    last_written: &mut Option<u32>,
) -> Result<(), BusError> {
    let word = if verdict().permits_operation() {
        mcf_digital_speed_word(SpeedDuty(DIGITAL_SPEED_DUTY.load(Ordering::Acquire)))
    } else {
        0
    };
    if *last_written == Some(word) {
        return Ok(());
    }
    mcf.write(reg::ALGO_DEBUG1, word).await?;
    if mcf.read(reg::ALGO_DEBUG1).await? != word {
        return Err(BusError::ReadbackMismatch);
    }
    *last_written = Some(word);
    Ok(())
}

/// The standing verdict on the MCF's stored configuration.
///
/// A level rather than a `Signal`: the control loop reads it on every tick and must keep
/// seeing the last verdict, not [`ConfigCheck::Pending`] on the ticks in between. It starts
/// pending, which is what holds `SafeBoot` until the I²C task has actually looked.
static VERDICT: CriticalSectionMutex<Cell<ConfigCheck>> =
    CriticalSectionMutex::new(Cell::new(ConfigCheck::Pending));
static TUNE_CANDIDATE: CriticalSectionMutex<Cell<Option<mcf_config::TuneCandidate>>> =
    CriticalSectionMutex::new(Cell::new(None));

/// The latest configuration verdict, for the control loop.
pub fn verdict() -> ConfigCheck {
    VERDICT.lock(|cell| cell.get())
}

/// Record a verdict. Called by the boot-time check and by every configuration operation.
pub fn publish_verdict(check: ConfigCheck) {
    if check != ConfigCheck::Tuning {
        TUNE_CANDIDATE.lock(|cell| cell.set(None));
    }
    VERDICT.lock(|cell| cell.set(check));
}

pub fn tuning_candidate() -> Option<mcf_config::TuneCandidate> {
    TUNE_CANDIDATE.lock(|cell| cell.get())
}

fn publish_tuning(candidate: mcf_config::TuneCandidate, check: ConfigCheck) {
    TUNE_CANDIDATE.lock(|cell| {
        cell.set((check == ConfigCheck::Tuning).then_some(candidate));
    });
    VERDICT.lock(|cell| cell.set(check));
}

/// A register access asked for by the console.
#[derive(Debug, Clone, Copy)]
pub enum Access {
    Read(u16),
    Write {
        address: u16,
        value: u32,
    },
    /// Re-run the configuration check.
    ConfigCheck,
    /// Stage the reviewed first-spin image in volatile shadow registers.
    ConfigStage,
    /// Stage one reviewed loaded-field candidate in volatile shadow registers.
    ConfigTune(mcf_config::TuneCandidate),
    /// Write the golden image, then verify it.
    ConfigApply,
    /// Emit the whole EEPROM configuration block, one register per line.
    ConfigDump,
    /// Read the extraction flags and all result registers as one report.
    MpetStatus,
    /// Clear MPET_CMD and confirm the bus accepted the write.
    MpetAbort,
}

/// What an [`Access`] produced.
#[derive(Debug, Clone, Copy)]
pub enum Answer {
    /// A register's value, or the number of registers a dump emitted.
    Value(u32),
    Config {
        check: ConfigCheck,
        written: u16,
        unchanged: u16,
    },
    Mpet(MpetReport),
    MpetAborted,
}

/// Requests and replies carry a generation so a reply cannot be misattributed.
///
/// Without it, a request that hits its timeout leaves its transaction still in flight; the
/// lock is released, a second request starts waiting, and the first request's late reply
/// satisfies it. The console would then report one register's value under another's name —
/// exactly the kind of confident wrong answer a tuning harness must never give.
static ACCESS_REQUEST: Signal<CriticalSectionRawMutex, (u32, Access)> = Signal::new();
static ACCESS_REPLY: Signal<CriticalSectionRawMutex, (u32, Result<Answer, &'static str>)> =
    Signal::new();
static ACCESS_GENERATION: AtomicU32 = AtomicU32::new(0);

/// Guards the request/reply pair so two callers cannot interleave and read each other's
/// answers. There is only ever one console, but a mutex costs nothing and makes that a
/// property of the code rather than of the wiring.
static ACCESS_LOCK: Mutex<CriticalSectionRawMutex, ()> = Mutex::new(());

/// Read a register on behalf of the console. Times out rather than hanging: a wedged bus
/// must not take the console down with it.
pub async fn request_read(address: u16) -> Result<u32, &'static str> {
    match exchange(Access::Read(address)).await? {
        Answer::Value(value) => Ok(value),
        Answer::Config { .. } => Err("wrong answer for a register read"),
        Answer::Mpet(_) => Err("wrong answer for a register read"),
        Answer::MpetAborted => Err("wrong answer for a register read"),
    }
}

/// Write a register on behalf of the console.
pub async fn request_write(address: u16, value: u32) -> Result<(), &'static str> {
    exchange(Access::Write { address, value }).await.map(|_| ())
}

/// Run a configuration operation on behalf of the console.
pub async fn request_config(access: Access) -> Result<Answer, &'static str> {
    exchange(access).await
}

async fn exchange(access: Access) -> Result<Answer, &'static str> {
    let _guard = ACCESS_LOCK.lock().await;
    let generation = ACCESS_GENERATION
        .fetch_add(1, Ordering::Relaxed)
        .wrapping_add(1);
    ACCESS_REPLY.reset();
    ACCESS_REQUEST.signal((generation, access));

    match with_timeout(deadline_for(access), async {
        loop {
            match ACCESS_REPLY.wait().await {
                // A reply from an abandoned earlier request: discard it and keep waiting for
                // ours rather than reporting it as ours.
                (answered, _) if answered != generation => continue,
                (_, reply) => break reply,
            }
        }
    })
    .await
    {
        Ok(reply) => reply,
        Err(_) => Err("register access timed out"),
    }
}

/// How long to wait for an answer, by how much work the access is.
///
/// One deadline for all of them would have to be the longest, and a five-second wait for a
/// single register read turns a wedged bus into a console that appears to have hung.
fn deadline_for(access: Access) -> Duration {
    match access {
        // A configuration shadow write is followed by a full image re-check. It does not
        // commit EEPROM, but it still needs the multi-register budget.
        Access::Write { address, .. } if mcf8316::is_configuration(address) => {
            Duration::from_secs(10)
        }
        Access::Read(_) | Access::Write { .. } | Access::MpetAbort => Duration::from_millis(500),
        // Two dozen reads apiece.
        Access::ConfigCheck | Access::ConfigDump | Access::MpetStatus => Duration::from_secs(5),
        Access::ConfigStage | Access::ConfigTune(_) => Duration::from_secs(10),
        // Reads, writes and re-reads two dozen EEPROM-backed registers.
        Access::ConfigApply => Duration::from_secs(60),
    }
}

/// Service a pending console register access, if there is one.
pub async fn service_access(mcf: &mut Mcf) {
    let Some((generation, access)) = ACCESS_REQUEST.try_take() else {
        return;
    };
    let reply = match access {
        Access::Read(address) => mcf.read(address).await.map(Answer::Value).map_err(describe),
        // The re-verification that a configuration write implies lives in the core crate, so
        // the simulator performs it identically and it is covered by host tests.
        Access::Write { address, value } => {
            match mcf_config::write_and_recheck(mcf, address, value, mcf_config::IMAGE).await {
                Ok(verdict) => {
                    if let Some(verdict) = verdict {
                        publish_verdict(verdict);
                    }
                    Ok(Answer::Value(0))
                }
                Err(error) => Err(describe(error)),
            }
        }
        Access::ConfigCheck => {
            let check = match verdict() {
                ConfigCheck::Provisional => mcf_config::check_provisional(mcf).await,
                ConfigCheck::Tuning => match tuning_candidate() {
                    Some(candidate) => mcf_config::check_loaded_candidate(mcf, candidate).await,
                    None => ConfigCheck::Unverified,
                },
                _ => mcf_config::check(mcf, mcf_config::IMAGE).await,
            };
            publish_verdict(check);
            Ok(Answer::Config {
                check,
                written: 0,
                unchanged: 0,
            })
        }
        Access::ConfigStage => {
            let (applied, check) = mcf_config::stage(mcf).await;
            publish_verdict(check);
            Ok(Answer::Config {
                check,
                written: applied.written,
                unchanged: applied.unchanged,
            })
        }
        Access::ConfigTune(candidate) => {
            let (applied, check) = mcf_config::stage_loaded_candidate(mcf, candidate).await;
            publish_tuning(candidate, check);
            Ok(Answer::Config {
                check,
                written: applied.written,
                unchanged: applied.unchanged,
            })
        }
        Access::ConfigApply => {
            // `apply` verifies by read-back and hands back the verdict it produced, so there
            // is no second pass here; the verdict already reflects the device as it now is.
            let (applied, check) = mcf_config::apply(mcf, mcf_config::IMAGE).await;
            publish_verdict(check);
            Ok(Answer::Config {
                check,
                written: applied.written,
                unchanged: applied.unchanged,
            })
        }
        Access::ConfigDump => dump(mcf).await.map(Answer::Value).map_err(describe),
        Access::MpetStatus => mcf.mpet_status().await.map(Answer::Mpet).map_err(describe),
        Access::MpetAbort => mcf
            .abort_mpet()
            .await
            .map(|()| Answer::MpetAborted)
            .map_err(describe),
    };
    ACCESS_REPLY.signal((generation, reply));
}

/// Emit the whole EEPROM configuration block, one protocol line per register.
///
/// The lines go straight to the output queue rather than back through the reply channel:
/// there are two dozen of them, and they are the raw material a golden image is captured
/// from (`stillair config capture`), not an answer to be interpreted.
async fn dump(mcf: &mut Mcf) -> Result<u32, BusError> {
    let mut count = 0;
    for (_, address) in reg::configuration() {
        let value = mcf.read(address).await?;
        crate::output::line(Reply::Register { address, value }.to_line());
        count += 1;
    }
    Ok(count)
}

const fn describe(error: BusError) -> &'static str {
    match error {
        BusError::Transfer(_) => "i2c transfer failed",
        BusError::Crc(_) => "reply failed its checksum",
        BusError::ReadbackMismatch => "register write failed read-back",
    }
}

/// Failures reported by the dedicated MCF software I2C bus.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SoftI2cError {
    AddressNack,
    DataNack,
    ClockHeldLow,
}

/// Two-wire controller with the MCF8316D's required pause after every byte.
///
/// The ESP hardware packet engine cannot insert that pause. GPIO0/1 are dedicated to this
/// one target, so a compact single-controller implementation is both sufficient and easier
/// to audit than pretending a globally slow SCL clock is the same timing requirement.
struct SoftI2c {
    sda: Flex<'static>,
    scl: Flex<'static>,
    delay: Delay,
}

impl SoftI2c {
    fn new(sda: impl Pin + 'static, scl: impl Pin + 'static) -> Self {
        let input = InputConfig::default().with_pull(Pull::None);
        let output = OutputConfig::default().with_drive_mode(DriveMode::OpenDrain);

        let mut sda = Flex::new(sda);
        sda.apply_input_config(&input);
        sda.set_input_enable(true);
        sda.apply_output_config(&output);
        sda.set_high();
        sda.set_output_enable(true);

        let mut scl = Flex::new(scl);
        scl.apply_input_config(&input);
        scl.set_input_enable(true);
        scl.apply_output_config(&output);
        scl.set_high();
        scl.set_output_enable(true);

        Self {
            sda,
            scl,
            delay: Delay::new(),
        }
    }

    fn half_period(&self) {
        self.delay.delay_micros(config::MCF_I2C_HALF_PERIOD_US);
    }

    fn release_clock(&mut self) -> Result<(), SoftI2cError> {
        self.scl.set_high();
        let released_at = HalInstant::now();
        while self.scl.is_low() {
            if released_at.elapsed().as_micros() >= config::MCF_I2C_CLOCK_STRETCH_TIMEOUT_US {
                return Err(SoftI2cError::ClockHeldLow);
            }
        }
        self.half_period();
        Ok(())
    }

    fn pull_clock_low(&mut self) {
        self.scl.set_low();
        self.half_period();
    }

    fn interbyte_hold(&self) {
        // Every caller enters with SCL low. Keeping it low makes the pause unambiguous and
        // prevents a target from mistaking line movement for another START or STOP. This is
        // deliberately a busy wait: yielding the thread-mode executor here let radio startup
        // stretch 110 us beyond the MCF's own 4.66 ms clock-low timeout.
        self.delay.delay_micros(config::MCF_I2C_INTERBYTE_US);
    }

    fn start(&mut self) -> Result<(), SoftI2cError> {
        self.sda.set_high();
        self.half_period();
        self.release_clock()?;
        self.sda.set_low();
        self.half_period();
        self.pull_clock_low();
        Ok(())
    }

    fn stop(&mut self) -> Result<(), SoftI2cError> {
        self.sda.set_low();
        self.half_period();
        let clock = self.release_clock();
        // Even if SCL is still held low, release SDA rather than leaving both bus lines low.
        // The caller preserves the original transfer error and the recovery path can then
        // issue clock pulses without fighting our own output.
        self.sda.set_high();
        self.half_period();
        clock
    }

    fn finish<T>(&mut self, result: Result<T, SoftI2cError>) -> Result<T, SoftI2cError> {
        let stopped = self.stop();
        match (result, stopped) {
            (Err(error), _) | (Ok(_), Err(error)) => Err(error),
            (Ok(value), Ok(())) => Ok(value),
        }
    }

    async fn write_byte(&mut self, byte: u8) -> Result<bool, SoftI2cError> {
        for bit in (0..8).rev() {
            if byte & (1 << bit) == 0 {
                self.sda.set_low();
            } else {
                self.sda.set_high();
            }
            self.half_period();
            self.release_clock()?;
            self.pull_clock_low();
        }

        self.sda.set_high();
        self.half_period();
        self.release_clock()?;
        let acknowledged = self.sda.is_low();
        self.pull_clock_low();
        self.interbyte_hold();
        Ok(acknowledged)
    }

    async fn read_byte(&mut self, acknowledge: bool) -> Result<u8, SoftI2cError> {
        self.sda.set_high();
        let mut byte = 0;
        for _ in 0..8 {
            self.half_period();
            self.release_clock()?;
            byte = (byte << 1) | u8::from(self.sda.is_high());
            self.pull_clock_low();
        }

        if acknowledge {
            self.sda.set_low();
        } else {
            self.sda.set_high();
        }
        self.half_period();
        self.release_clock()?;
        self.pull_clock_low();
        self.sda.set_high();
        self.interbyte_hold();
        Ok(byte)
    }

    async fn write(&mut self, target: u8, bytes: &[u8]) -> Result<(), SoftI2cError> {
        let mut result = self.start();
        if result.is_ok() {
            result = match self.write_byte(target << 1).await {
                Ok(true) => Ok(()),
                Ok(false) => Err(SoftI2cError::AddressNack),
                Err(error) => Err(error),
            };
        }
        for &byte in bytes {
            if result.is_err() {
                break;
            }
            result = match self.write_byte(byte).await {
                Ok(true) => Ok(()),
                Ok(false) => Err(SoftI2cError::DataNack),
                Err(error) => Err(error),
            };
        }
        self.finish(result)
    }

    async fn write_read(
        &mut self,
        target: u8,
        written: &[u8],
        read: &mut [u8],
    ) -> Result<(), SoftI2cError> {
        if let Err(error) = self.start() {
            return self.finish(Err(error));
        }
        match self.write_byte(target << 1).await {
            Ok(true) => {}
            Ok(false) => return self.finish(Err(SoftI2cError::AddressNack)),
            Err(error) => return self.finish(Err(error)),
        }
        for &byte in written {
            match self.write_byte(byte).await {
                Ok(true) => {}
                Ok(false) => return self.finish(Err(SoftI2cError::DataNack)),
                Err(error) => return self.finish(Err(error)),
            }
        }

        if let Err(error) = self.start() {
            return self.finish(Err(error));
        }
        match self.write_byte((target << 1) | 1).await {
            Ok(true) => {}
            Ok(false) => return self.finish(Err(SoftI2cError::AddressNack)),
            Err(error) => return self.finish(Err(error)),
        }
        let last = read.len().saturating_sub(1);
        for (index, byte) in read.iter_mut().enumerate() {
            *byte = match self.read_byte(index != last).await {
                Ok(byte) => byte,
                Err(error) => return self.finish(Err(error)),
            };
        }
        self.finish(Ok(()))
    }

    async fn recover(&mut self) {
        // Release SDA, then give a target stranded mid-byte nine chances to finish before
        // generating STOP. Failure is harmless here: the following status read reports it.
        self.sda.set_high();
        for _ in 0..9 {
            self.scl.set_low();
            self.half_period();
            if self.release_clock().is_err() {
                break;
            }
            self.pull_clock_low();
        }
        let _ = self.stop();
        self.interbyte_hold();
    }
}

/// Why a register access failed.
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum BusError {
    /// The transfer itself failed: NACK, arbitration loss, timeout, stuck bus.
    Transfer(SoftI2cError),
    /// The device answered, but the CRC over its reply did not match. Treated as a failure
    /// rather than retried silently — a wrong checksum means either the bus is corrupting
    /// data or our framing is wrong, and neither should reach the state machine as truth.
    Crc(CrcMismatch),
    /// The transfer succeeded but the shadow register did not retain the requested field.
    ReadbackMismatch,
}

impl From<SoftI2cError> for BusError {
    fn from(error: SoftI2cError) -> Self {
        Self::Transfer(error)
    }
}

/// A configured connection to the MCF8316D.
pub struct Mcf {
    i2c: SoftI2c,
    /// 7-bit target address. Default 0x01, but changeable in EEPROM, so this is discovered
    /// by [`Mcf::probe`] rather than assumed.
    target: u8,
    crc: bool,
}

impl Mcf {
    /// Wrap a bus with CRC enabled. CRC costs one byte per transaction and turns silent
    /// corruption into a reported failure, which is worth far more than the byte on a
    /// device that commands a motor.
    pub fn new(sda: impl Pin + 'static, scl: impl Pin + 'static, target: u8) -> Self {
        Self {
            i2c: SoftI2c::new(sda, scl),
            target,
            crc: true,
        }
    }

    /// Confirm the currently selected target without sweeping the address space.
    ///
    /// Safe boot uses this at zero SPEED before deciding whether the chip actually needs a
    /// WAKE pulse. Avoiding an unnecessary pulse matters because a high speed command while
    /// DRVOFF is asserted can legitimately latch a start-failed diagnostic.
    pub async fn probe_current(&mut self) -> bool {
        self.read(reg::GATE_DRIVER_FAULT_STATUS).await.is_ok()
    }

    /// Find the device by reading a known register at each candidate address.
    ///
    /// The datasheet's own recovery procedure for a device whose target ID was changed in
    /// EEPROM. A bare address ACK would be cheaper but proves less: this confirms the device
    /// speaks the control-word protocol, not merely that something is on the bus.
    pub async fn probe(&mut self) -> Option<u8> {
        let original = self.target;
        for candidate in mcf8316::probe_candidates(original) {
            self.target = candidate;
            if self.read(reg::GATE_DRIVER_FAULT_STATUS).await.is_ok() {
                return Some(candidate);
            }
        }
        // Restore rather than leaving the last address tried in place. Otherwise a device
        // that simply was not ready yet would be addressed at 0x77 for the rest of the
        // power cycle, and every subsequent read would fail for the wrong reason.
        self.target = original;
        None
    }

    /// Read both fault-status registers as one snapshot.
    pub async fn fault_status(&mut self) -> Result<FaultStatus, BusError> {
        let gate = self.read(reg::GATE_DRIVER_FAULT_STATUS).await?;
        let controller = self.read(reg::CONTROLLER_FAULT_STATUS).await?;
        Ok(FaultStatus::new(gate, controller))
    }

    /// Issue CLR_FLT. Write-only and self-clearing, so there is nothing to verify by
    /// reading back; the proof is that the fault-status registers clear within ~200 ms.
    pub async fn clear_faults(&mut self) -> Result<(), BusError> {
        self.write(reg::ALGO_CTRL1, mcf8316::CLR_FLT_COMMAND).await
    }

    pub async fn start_mpet(&mut self, command: u32) -> Result<(), BusError> {
        self.write(reg::ALGO_DEBUG2, command).await
    }

    pub async fn abort_mpet(&mut self) -> Result<(), BusError> {
        self.write(reg::ALGO_DEBUG2, mcf8316::MPET_ABORT_COMMAND)
            .await
    }

    pub async fn mpet_status(&mut self) -> Result<MpetReport, BusError> {
        Ok(MpetReport {
            status: self.read(reg::ALGO_STATUS_MPET).await?,
            motor_params: self.read(reg::MTR_PARAMS).await?,
            current_pi: self.read(reg::CURRENT_PI).await?,
            speed_pi: self.read(reg::SPEED_PI).await?,
        })
    }

    /// Attempt to free a bus a confused target is holding low.
    ///
    /// The supervisor does not depend on this working: [`BusError`]s accumulate and become
    /// `BusUnreachable`, which stops the fan and requires a power cycle. That is the
    /// documented fallback, and it is the safe one.
    pub async fn recover(&mut self) {
        self.i2c.recover().await;
        Timer::after(Duration::from_millis(10)).await;
        let _ = self.fault_status().await;
    }
}

impl RegisterBus for Mcf {
    type Error = BusError;

    async fn read(&mut self, address: u16) -> Result<u32, BusError> {
        // Every transaction opens by *writing* the control word; the data phase is a
        // repeated-start read, which is exactly what `write_read` performs.
        let control = mcf8316::ControlWord::reg32(mcf8316::Op::Read, address, self.crc).bytes();
        let mut reply = [0u8; 5];
        let len = 4 + usize::from(self.crc);
        self.i2c
            .write_read(self.target, &control, &mut reply[..len])
            .await?;

        if self.crc {
            // Verification lives in the core crate so the compare-and-classify step is
            // covered by host tests rather than only by a real bus.
            return verify_read(self.target, address, reply).map_err(BusError::Crc);
        }
        Ok(value_from_bytes32([reply[0], reply[1], reply[2], reply[3]]))
    }

    async fn write(&mut self, address: u16, value: u32) -> Result<(), BusError> {
        let frame = write_frame(self.target, address, value, self.crc);
        self.i2c.write(self.target, &frame).await?;
        Ok(())
    }

    async fn delay_ms(&mut self, milliseconds: u32) {
        Timer::after(Duration::from_millis(u64::from(milliseconds))).await;
    }
}
