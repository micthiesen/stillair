//! The device end of the tuning console.
//!
//! Transport and plumbing only — every parsing and formatting decision lives in
//! `stillair_core::console`, where it is host-tested. This module reads lines off the
//! USB-serial-JTAG link, routes each request to whichever task owns the thing it asks
//! about, and prints the reply.
//!
//! Replies go out through `esp-println`, deliberately: it takes a lock per call, so
//! emitting a whole protocol line in one `println!` makes it atomic against log output from
//! other tasks. That is what keeps a log line from landing in the middle of a JSON frame.
//! The `@` prefix does the rest — a host tool reads `@` lines as protocol and passes
//! everything else through as logs.

use core::sync::atomic::{AtomicU32, Ordering};

use embassy_sync::blocking_mutex::raw::CriticalSectionRawMutex;
use embassy_sync::blocking_mutex::CriticalSectionMutex;
use embassy_sync::channel::Channel;
use embassy_time::{Duration, Timer};
use embedded_io_async::Read;
use esp_hal::usb_serial_jtag::UsbSerialJtagRx;
use esp_hal::Async;
use portable_atomic::AtomicBool;
use stillair_core::console::{self, ParseError, Reply, Request, Telemetry};
use stillair_core::state::Command;

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

fn latest() -> Option<Telemetry> {
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
    loop {
        let hz = STREAM_HZ.load(Ordering::Relaxed);
        if hz == 0 {
            Timer::after(Duration::from_millis(100)).await;
            continue;
        }
        if let Some(telemetry) = latest() {
            emit(&Reply::Telemetry(telemetry));
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
        Request::RegWrite { address, value } => match mcf::request_write(address, value).await {
            Ok(()) => emit(&Reply::Ok),
            Err(error) => emit(&Reply::Error(error)),
        },
        Request::Help => {
            for line in console::HELP {
                esp_println::println!("{line}");
            }
            emit(&Reply::Ok);
        }
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
    esp_println::println!("{}", reply.to_line());
}

/// Reports a parse failure without a request. Used by the transport for framing errors.
pub fn reject(error: ParseError) {
    emit(&Reply::Error(error.as_str()));
}
