//! The device end of the tuning console.
//!
//! Transport and plumbing only — every parsing and formatting decision lives in
//! `stillair_core::console`, where it is host-tested. This module reads lines off the
//! USB-serial-JTAG link, routes each request to whichever task owns the thing it asks
//! about, and prints the reply.
//!
//! Replies go out through [`crate::output`], the single bounded queue that every line — log
//! or protocol — passes through. One writer is what keeps a log record from landing in the
//! middle of a JSON frame, and the `@` prefix does the rest: a host tool reads `@` lines as
//! protocol and passes everything else through as logs.

use core::sync::atomic::{AtomicU32, Ordering};

use embassy_sync::blocking_mutex::raw::CriticalSectionRawMutex;
use embassy_sync::blocking_mutex::CriticalSectionMutex;
use embassy_sync::channel::Channel;
use embassy_time::{Duration, Timer};
use embedded_io_async::Read;
use esp_hal::usb::usb_serial_jtag::UsbSerialJtagRx;
use esp_hal::Async;
use portable_atomic::AtomicBool;
use stillair_core::console::{self, ConfigOp, Reply, Request, Telemetry};
use stillair_core::matter;
use stillair_core::state::{Command, FanState};

use crate::mcf;

/// Console → control loop. Bounded and non-blocking to send into: a wedged control loop
/// must never be able to block the console, which is the thing you would be using to find
/// out why it is wedged.
pub static COMMANDS: Channel<CriticalSectionRawMutex, Command, 4> = Channel::new();

/// Latest telemetry, republished by the control loop every tick.
static TELEMETRY: CriticalSectionMutex<core::cell::Cell<Option<Telemetry>>> =
    CriticalSectionMutex::new(core::cell::Cell::new(None));

/// Telemetry stream rate, 0 when off.
static STREAM_HZ: AtomicU32 = AtomicU32::new(0);

/// Set once the control loop has published at least one snapshot.
static TELEMETRY_READY: AtomicBool = AtomicBool::new(false);

/// Called by the control loop after every poll.
pub fn publish(telemetry: Telemetry) {
    TELEMETRY.lock(|cell| cell.set(Some(telemetry)));
    TELEMETRY_READY.store(true, Ordering::Relaxed);
}

pub fn latest() -> Option<Telemetry> {
    TELEMETRY.lock(|cell| cell.get())
}

/// Longest request line accepted. Anything longer is a malformed line, not a command.
const LINE_LIMIT: usize = 96;

/// Reads and services console requests.
#[embassy_executor::task]
pub async fn console_task(mut rx: UsbSerialJtagRx<'static, Async>) {
    let mut line: heapless::String<LINE_LIMIT> = heapless::String::new();
    let mut overflowed = false;
    let mut chunk = [0u8; 32];

    emit(&Reply::Ok);

    loop {
        let read = match rx.read(&mut chunk).await {
            Ok(read) => read,
            Err(_) => continue,
        };

        for byte in &chunk[..read] {
            match byte {
                b'\n' | b'\r' => {
                    if overflowed {
                        // Never act on a line we only partly saw — a truncated `run 1700`
                        // is a very different command from `run 170`.
                        emit(&Reply::Error("line too long"));
                    } else if !line.is_empty() {
                        dispatch(line.as_str()).await;
                    }
                    line.clear();
                    overflowed = false;
                }
                _ => {
                    if line.push(*byte as char).is_err() {
                        overflowed = true;
                    }
                }
            }
        }
    }
}

/// Emits telemetry while a stream is running. Separate from the reader so a stream never
/// competes with, or delays, an incoming command.
#[embassy_executor::task]
pub async fn stream_task() {
    let mut last_emitted: Option<u64> = None;
    loop {
        let hz = STREAM_HZ.load(Ordering::Relaxed);
        if hz == 0 {
            Timer::after(Duration::from_millis(100)).await;
            continue;
        }
        // Emit only genuinely new snapshots. The control loop republishes at its own
        // cadence, so a faster stream request would otherwise duplicate the same instant
        // several times over — and a duplicate looks exactly like an independent sample in
        // a CSV, which would misrepresent what was actually measured.
        if let Some(telemetry) = latest() {
            if Some(telemetry.uptime_ms) != last_emitted {
                last_emitted = Some(telemetry.uptime_ms);
                emit(&Reply::Telemetry(telemetry));
            }
        }
        Timer::after(Duration::from_hz(u64::from(hz))).await;
    }
}

async fn dispatch(line: &str) {
    let request = match console::parse(line) {
        Ok(request) => request,
        Err(error) => {
            emit(&Reply::Error(error.as_str()));
            return;
        }
    };

    match request {
        Request::State => match latest() {
            Some(telemetry) => emit(&Reply::Telemetry(telemetry)),
            None if TELEMETRY_READY.load(Ordering::Relaxed) => {
                emit(&Reply::Error("telemetry unavailable"))
            }
            None => emit(&Reply::Error("control loop has not run yet")),
        },
        Request::Run(rpm) => command(Command::SetSpeed(rpm)),
        // Routed through the same mapping the Matter handler uses, so a script exercises the
        // percent path rather than a console-only imitation of it.
        Request::Percent(percent) => match latest() {
            Some(telemetry) => {
                command(matter::command_for_percent(percent, telemetry.released_min))
            }
            None => emit(&Reply::Error("control loop has not run yet")),
        },
        Request::Stop => command(Command::Off),
        Request::SetDirection(direction) => command(Command::SetDirection(direction)),
        // Any user command licenses a fault clear; `Off` is the one that cannot also start
        // the fan as a side effect of clearing it.
        Request::ClearFault => command(Command::Off),
        Request::Stream(rate) => {
            STREAM_HZ.store(rate.unwrap_or(0), Ordering::Relaxed);
            emit(&Reply::Ok);
        }
        Request::RegRead(address) => match mcf::request_read(address).await {
            Ok(value) => emit(&Reply::Register { address, value }),
            Err(error) => emit(&Reply::Error(error)),
        },
        Request::RegWrite { address, value } => {
            if let Some(refusal) = refuse_write(address) {
                emit(&Reply::Error(refusal));
            } else {
                match mcf::request_write(address, value).await {
                    Ok(()) => emit(&Reply::Ok),
                    Err(error) => emit(&Reply::Error(error)),
                }
            }
        }
        Request::Config(operation) => config(operation).await,
        Request::Help => {
            for text in console::HELP {
                let mut help = console::Line::new();
                let _ = core::fmt::Write::write_str(&mut help, text);
                crate::output::line(help);
            }
            emit(&Reply::Ok);
        }
    }
}

/// Run a configuration operation and report its outcome.
///
/// **`config apply` stalls the whole console for as long as it runs** (up to a minute against
/// EEPROM), because `console_task` does not read the next line until `dispatch` returns. That
/// is deliberate rather than overlooked: `refuse_write` confines an apply to `IdleOff`,
/// `SafeBoot`, or `Fault`, so there is no spinning rotor to command during the stall and
/// nothing a `stop` could usefully do. If responsiveness during an apply ever matters, this
/// is the place to move off the line-reader task.
async fn config(operation: ConfigOp) {
    let access = match operation {
        ConfigOp::Check => mcf::Access::ConfigCheck,
        ConfigOp::Dump => mcf::Access::ConfigDump,
        ConfigOp::Apply => {
            // The same gate as a raw configuration write, for the same reasons: EEPROM
            // discipline, and the fact that `MAX_SPEED` decides what every clamped duty
            // means. `CONFIG_FIRST` stands in for the block as a whole.
            if let Some(refusal) = refuse_write(stillair_core::mcf8316::reg::CONFIG_FIRST) {
                emit(&Reply::Error(refusal));
                return;
            }
            mcf::Access::ConfigApply
        }
    };

    match mcf::request_config(access).await {
        Ok(mcf::Answer::Config {
            check,
            written,
            unchanged,
        }) => emit(&Reply::Config {
            check,
            written,
            unchanged,
        }),
        // A dump has already emitted one register line per register; this only closes it
        // out. The host knows how many to expect — it shares `reg::configuration()` — so a
        // dump cut short by a bus error is caught there rather than needing a count here,
        // which would be indistinguishable from one more register line.
        Ok(mcf::Answer::Value(_)) => emit(&Reply::Ok),
        Err(error) => emit(&Reply::Error(error)),
    }
}

/// Why a register write must not happen right now, if it must not.
///
/// Raw register access is a bench capability that sits outside every supervisor safeguard —
/// `run` is clamped, `reg write` is not. Two of those registers decide what a clamped duty
/// actually means (`MAX_SPEED`) or how faults are handled at all (`FAULT_CONFIG*`), so
/// writing them under a spinning rotor could defeat the layered limits from the outside.
/// The configuration block is also EEPROM-backed, and the datasheet requires writes happen
/// only with the motor stopped and the device idle or faulted.
fn refuse_write(address: u16) -> Option<&'static str> {
    if !stillair_core::mcf8316::is_configuration(address) {
        return None;
    }
    match latest().map(|telemetry| telemetry.state) {
        Some(FanState::IdleOff | FanState::SafeBoot | FanState::Fault) => None,
        Some(_) => Some("configuration registers are writable only while stopped"),
        None => Some("state unknown; refusing a configuration write"),
    }
}

fn command(command: Command) {
    // `try_send`, never `send`: a full queue means the control loop is not draining, and
    // blocking here would take the console down with it.
    if COMMANDS.try_send(command).is_err() {
        emit(&Reply::Error("control loop not accepting commands"));
        return;
    }
    emit(&Reply::Ok);
}

fn emit(reply: &Reply<'_>) {
    crate::output::line(reply.to_line());
}
