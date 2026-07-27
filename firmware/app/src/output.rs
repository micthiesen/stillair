//! The single writer for everything that leaves the board over USB.
//!
//! **Why this exists rather than just calling `esp_println!`.** That macro takes
//! `esp-sync`'s raw lock, which on RISC-V clears the global interrupt-enable bit — not a
//! priority mask, a full core-level disable. It then writes the FIFO byte by byte and, if
//! the FIFO is full because nothing is draining the other end, busy-spins tens of thousands
//! of iterations *with interrupts still off*. That would mask the Priority3 interrupt the
//! control loop, the watchdog heartbeat, and both tach counters run on.
//!
//! Streaming telemetry made that a routine event instead of a rare one: a host that pauses
//! a tuning script, or a terminal that disconnects mid-capture, is enough to fill the FIFO.
//! The contract says a stalled console must degrade to "the fan keeps its speed"; printing
//! through a global interrupt disable would instead have let it stop the fan.
//!
//! So every line — protocol frames *and* log records — goes into a bounded queue, and one
//! task drains it through the async driver, which waits on an interrupt rather than
//! spinning. If the host stops reading, the queue fills and lines are dropped and counted.
//! Losing telemetry is the correct thing to lose.

use core::fmt::Write as _;
use core::sync::atomic::{AtomicU32, Ordering};

use embassy_sync::blocking_mutex::raw::CriticalSectionRawMutex;
use embassy_sync::channel::Channel;
use embedded_io_async::Write as _;
use esp_hal::usb_serial_jtag::UsbSerialJtagTx;
use esp_hal::Async;
use stillair_core::console::Line;

/// Queue depth. Deep enough to ride out a brief stall at the highest useful telemetry rate,
/// shallow enough that a host which has genuinely gone away is noticed quickly.
const QUEUE: usize = 24;

static LINES: Channel<CriticalSectionRawMutex, Line, QUEUE> = Channel::new();

/// Lines discarded because the host was not reading. Surfaced so a capture with a gap in it
/// is identifiable as such rather than quietly short.
static DROPPED: AtomicU32 = AtomicU32::new(0);

/// Queue one line. Never blocks, never disables interrupts, safe from any priority.
pub fn line(line: Line) {
    if LINES.try_send(line).is_err() {
        DROPPED.fetch_add(1, Ordering::Relaxed);
    }
}

/// How many lines have been dropped for want of a reader.
pub fn dropped() -> u32 {
    DROPPED.load(Ordering::Relaxed)
}

/// Drains the queue to the link.
#[embassy_executor::task]
pub async fn writer_task(mut tx: UsbSerialJtagTx<'static, Async>) {
    loop {
        let mut line = LINES.receive().await;
        // The newline goes in the same buffer as the payload so one line is one write, and
        // nothing can be interleaved into the middle of a frame.
        let _ = line.push('\n');
        let _ = tx.write_all(line.as_bytes()).await;
    }
}

/// Routes `log` records through the same queue as protocol frames.
///
/// One writer is what makes the `@` prefix sufficient: with two, a log record could land in
/// the middle of a JSON frame and a host would see neither.
struct QueueLogger;

impl log::Log for QueueLogger {
    fn enabled(&self, _: &log::Metadata<'_>) -> bool {
        true
    }

    fn log(&self, record: &log::Record<'_>) {
        let mut text = Line::new();
        // A truncated log line is acceptable; a truncated protocol frame would not be, which
        // is why frames are sized to fit rather than trimmed.
        let _ = write!(text, "[{}] {}", record.level(), record.args());
        line(text);
    }

    fn flush(&self) {}
}

static LOGGER: QueueLogger = QueueLogger;

/// Install the queue logger. Call before anything logs.
pub fn init(level: log::LevelFilter) {
    let _ = log::set_logger(&LOGGER);
    log::set_max_level(level);
}
