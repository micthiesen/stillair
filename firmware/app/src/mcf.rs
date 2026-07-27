//! The MCF8316D I²C driver: the concrete [`RegisterBus`] behind `stillair-core`'s framing.
//!
//! The wire format itself lives in `stillair_core::mcf8316`, where it is unit-tested against
//! TI's published example packets. This module is only transport: it moves those bytes,
//! checks the CRC coming back, and reports failure honestly so the supervisor can decide
//! what a silent drive means.

use embassy_sync::blocking_mutex::raw::CriticalSectionRawMutex;
use embassy_sync::signal::Signal;
use embassy_time::{Duration, Timer};
use esp_hal::i2c::master::{Error as I2cError, I2c};
use esp_hal::Async;
use stillair_core::mcf8316::{
    self, reg, value_from_bytes32, verify_read, write_frame, CrcMismatch, FaultStatus, RegisterBus,
};
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
