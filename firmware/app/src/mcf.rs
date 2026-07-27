//! The MCF8316D I²C driver: the concrete [`RegisterBus`] behind `stillair-core`'s framing.
//!
//! The wire format itself lives in `stillair_core::mcf8316`, where it is unit-tested against
//! TI's published example packets. This module is only transport: it moves those bytes,
//! checks the CRC coming back, and reports failure honestly so the supervisor can decide
//! what a silent drive means.

use core::cell::Cell;
use core::sync::atomic::{AtomicU32, Ordering};

use embassy_sync::blocking_mutex::raw::CriticalSectionRawMutex;
use embassy_sync::blocking_mutex::CriticalSectionMutex;
use embassy_sync::mutex::Mutex;
use embassy_sync::signal::Signal;
use embassy_time::{with_timeout, Duration, Timer};
use esp_hal::i2c::master::{Error as I2cError, I2c};
use esp_hal::Async;
use stillair_core::console::Reply;
use stillair_core::mcf8316::{
    self, reg, value_from_bytes32, verify_read, write_frame, CrcMismatch, FaultStatus, RegisterBus,
};
use stillair_core::mcf_config::{self, ConfigCheck};
use stillair_core::state::StatusRead;

/// Latest fault-status read, published by the I²C task and consumed by the control loop.
///
/// A `Signal` rather than a shared cell on purpose: taking it leaves nothing behind, so the
/// control loop naturally sees [`StatusRead::Stale`] when no new read has landed instead of
/// re-reading an old verdict as if it were current.
pub static STATUS: Signal<CriticalSectionRawMutex, StatusRead> = Signal::new();

/// Raised by the control loop when the supervisor emits `ClearMcfFault`, serviced by the
/// I²C task. Crossing tasks like this keeps the blocking-free control loop free of I²C.
pub static CLEAR_FAULT_REQUEST: Signal<CriticalSectionRawMutex, ()> = Signal::new();

/// The standing verdict on the MCF's stored configuration.
///
/// A level rather than a `Signal`: the control loop reads it on every tick and must keep
/// seeing the last verdict, not [`ConfigCheck::Pending`] on the ticks in between. It starts
/// pending, which is what holds `SafeBoot` until the I²C task has actually looked.
static VERDICT: CriticalSectionMutex<Cell<ConfigCheck>> =
    CriticalSectionMutex::new(Cell::new(ConfigCheck::Pending));

/// The latest configuration verdict, for the control loop.
pub fn verdict() -> ConfigCheck {
    VERDICT.lock(|cell| cell.get())
}

/// Record a verdict. Called by the boot-time check and by every configuration operation.
pub fn publish_verdict(check: ConfigCheck) {
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
    /// Write the golden image, then verify it.
    ConfigApply,
    /// Emit the whole EEPROM configuration block, one register per line.
    ConfigDump,
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

    let deadline = deadline_for(access);
    loop {
        match with_timeout(deadline, ACCESS_REPLY.wait()).await {
            // A reply from an abandoned earlier request: discard it and keep waiting for
            // ours rather than reporting it as ours.
            Ok((answered, _)) if answered != generation => continue,
            Ok((_, reply)) => return reply,
            Err(_) => return Err("register access timed out"),
        }
    }
}

/// How long to wait for an answer, by how much work the access is.
///
/// One deadline for all of them would have to be the longest, and a five-second wait for a
/// single register read turns a wedged bus into a console that appears to have hung.
fn deadline_for(access: Access) -> Duration {
    match access {
        // A configuration write is EEPROM-backed at roughly 750 ms (`docs/controls.md`) —
        // already past the plain-write budget on its own — and it is followed by a full
        // re-verification pass over the block. Budgeting it as an ordinary write would report
        // "register access timed out" for an operation that completed correctly, on exactly
        // the bench workflow this feature exists for. An operator who believes that and
        // retries burns another cycle of 20k-cycle EEPROM endurance.
        Access::Write { address, .. } if mcf8316::is_configuration(address) => {
            Duration::from_secs(10)
        }
        Access::Read(_) | Access::Write { .. } => Duration::from_millis(500),
        // Two dozen reads apiece.
        Access::ConfigCheck | Access::ConfigDump => Duration::from_secs(5),
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
            let check = mcf_config::check(mcf, mcf_config::IMAGE).await;
            publish_verdict(check);
            Ok(Answer::Config {
                check,
                written: 0,
                unchanged: 0,
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
    }
}

/// Why a register access failed.
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum BusError {
    /// The transfer itself failed: NACK, arbitration loss, timeout, stuck bus.
    Transfer(I2cError),
    /// The device answered, but the CRC over its reply did not match. Treated as a failure
    /// rather than retried silently — a wrong checksum means either the bus is corrupting
    /// data or our framing is wrong, and neither should reach the state machine as truth.
    Crc(CrcMismatch),
}

impl From<I2cError> for BusError {
    fn from(error: I2cError) -> Self {
        Self::Transfer(error)
    }
}

/// A configured connection to the MCF8316D.
pub struct Mcf {
    i2c: I2c<'static, Async>,
    /// 7-bit target address. Default 0x01, but changeable in EEPROM, so this is discovered
    /// by [`Mcf::probe`] rather than assumed.
    target: u8,
    crc: bool,
}

impl Mcf {
    /// Wrap a bus with CRC enabled. CRC costs one byte per transaction and turns silent
    /// corruption into a reported failure, which is worth far more than the byte on a
    /// device that commands a motor.
    pub fn new(i2c: I2c<'static, Async>, target: u8) -> Self {
        Self {
            i2c,
            target,
            crc: true,
        }
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

    /// Attempt to free a bus a confused target is holding low.
    ///
    /// The standard nine-clock recovery needs to bit-bang SCL, which means taking the pins
    /// back from the peripheral. That is not expressible with the pins owned by [`I2c`], so
    /// what this does instead is reset the controller's own state machine by re-issuing a
    /// transfer after a pause — enough for a controller-side hang, not enough for a target
    /// holding SDA down.
    ///
    /// The supervisor does not depend on this working: [`BusError`]s accumulate and become
    /// `BusUnreachable`, which stops the fan and requires a power cycle. That is the
    /// documented fallback, and it is the safe one.
    pub async fn recover(&mut self) {
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
            .write_read_async(self.target, &control, &mut reply[..len])
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
        self.i2c.write_async(self.target, &frame).await?;
        Ok(())
    }
}
