//! Stillair ceiling-fan supervisor firmware.
//!
//! Runs on the ESP32-C6-MINI-1-H4 on the custom 78 × 58 mm controller board.
//! The supervisor configures the MCF8316D over I²C and commands speed/direction;
//! it never switches motor phases. The behavioral contract lives in `docs/controls.md`
//! and is implemented — and unit-tested on the host — in `stillair-core`; this crate is
//! only the wiring that turns that contract into GPIO edges.
//!
//! GPIO map (verified against the ESP32-C6-MINI-1 datasheet; GPIO15 is the only strap
//! pin used — its JTAG-select strap is ignored with default eFuses and the external
//! pull-up satisfies its no-float requirement):
//!
//! | GPIO    | Signal                       |
//! |---------|------------------------------|
//! | 0 / 1   | SDA / SCL (MCF I²C)          |
//! | 2       | SPEED PWM                    |
//! | 3       | DIR                          |
//! | 6       | NTC ADC (optional, ADC1_CH6) |
//! | 7       | HALL_TACH sense (plausibility check input) |
//! | 12 / 13 | USB D− / D+                  |
//! | 14      | MCF ALARM (active-high)      |
//! | 15      | MCU_CLEAR_N (open-drain out) |
//! | 16 / 17 | UART TX / RX                 |
//! | 18      | permission ARM_PULSE         |
//! | 19      | watchdog heartbeat           |
//! | 20      | MCF FG                       |
//! | 21      | MCF nFAULT                   |
//! | 22      | 3.3 V PGOOD                  |
//! | 23      | watchdog WDO diagnostic      |

#![no_std]
#![no_main]

use core::sync::atomic::{AtomicU32, Ordering};

use embassy_time::{Duration, Instant, Timer};
use esp_backtrace as _;
use esp_hal::gpio::{DriveMode, Input, InputConfig, Level, Output, OutputConfig, Pull};
use esp_hal::ledc::channel::ChannelIFace;
use esp_hal::ledc::timer::TimerIFace;
use esp_hal::ledc::{channel, timer, LSGlobalClkSource, Ledc, LowSpeed};
use esp_hal::time::Rate;
use esp_hal::timer::timg::TimerGroup;
use static_cell::StaticCell;
use stillair_core::config;
use stillair_core::state::{Inputs, Supervisor};
use stillair_core::time::Millis;

mod board;

use board::{Board, FG_PULSES, HALL_PULSES};

esp_bootloader_esp_idf::esp_app_desc!();

/// Control-loop cadence. Fast enough that the ramp is smooth and a fault is acted on
/// promptly, slow enough to be nowhere near the watchdog's 1.6 s window.
const CONTROL_TICK: Duration = Duration::from_millis(50);

/// Incremented by the control loop on every completed poll. The heartbeat task refuses to
/// toggle unless this has advanced, which is what makes the watchdog attest control-loop
/// liveness rather than merely CPU liveness (`docs/controls.md` > "Firmware safety
/// architecture").
static CONTROL_LOOP_BEAT: AtomicU32 = AtomicU32::new(0);

static LEDC: StaticCell<Ledc<'static>> = StaticCell::new();
static SPEED_TIMER: StaticCell<timer::Timer<'static, LowSpeed>> = StaticCell::new();

#[esp_rtos::main]
async fn main(spawner: embassy_executor::Spawner) {
    esp_println::logger::init_logger_from_env();

    let peripherals = esp_hal::init(esp_hal::Config::default());

    // Heap is only needed once the radio (Wi-Fi / Matter) comes online.
    esp_alloc::heap_allocator!(size: 72 * 1024);

    let timg0 = TimerGroup::new(peripherals.TIMG0);
    let sw_int =
        esp_hal::interrupt::software::SoftwareInterruptControl::new(peripherals.SW_INTERRUPT);
    esp_rtos::start(timg0.timer0, sw_int.software_interrupt0);

    log::info!("stillair supervisor boot");

    // Outputs. Every one powers up in its safe state: no direction change, no permission
    // request, and permission actively revocable.
    let push_pull = OutputConfig::default();
    let open_drain = OutputConfig::default().with_drive_mode(DriveMode::OpenDrain);

    let dir = Output::new(peripherals.GPIO3, Level::Low, push_pull);
    let arm = Output::new(peripherals.GPIO18, Level::Low, push_pull);
    // Idle high (released). Open-drain so it can only ever pull the latch's clear line
    // down — firmware cannot drive permission on.
    let clear_n = Output::new(peripherals.GPIO15, Level::High, open_drain);
    let heartbeat = Output::new(peripherals.GPIO19, Level::Low, push_pull);

    // Inputs. No internal pulls: the board provides them.
    let floating = InputConfig::default().with_pull(Pull::None);
    let pgood = Input::new(peripherals.GPIO22, floating);
    let nfault = Input::new(peripherals.GPIO21, floating);
    let alarm = Input::new(peripherals.GPIO14, floating);
    let fg = Input::new(peripherals.GPIO20, floating);
    let hall = Input::new(peripherals.GPIO7, floating);

    // SPEED-pin PWM. 11-bit at 200 Hz, inside the MCF's `SPEED_RANGE_SEL` = 1h band.
    let ledc = LEDC.init(Ledc::new(peripherals.LEDC));
    ledc.set_global_slow_clock(LSGlobalClkSource::APBClk);
    let speed_timer = SPEED_TIMER.init(ledc.timer::<LowSpeed>(timer::Number::Timer0));
    speed_timer
        .configure(timer::config::Config {
            duty: timer::config::Duty::Duty11Bit,
            clock_source: timer::LSClockSource::APBClk,
            frequency: Rate::from_hz(config::SPEED_CARRIER_HZ),
        })
        .expect("SPEED carrier must be configurable at 200 Hz / 11 bit");

    let mut speed = ledc.channel(channel::Number::Channel0, peripherals.GPIO2);
    speed
        .configure(channel::config::Config {
            timer: speed_timer,
            duty_pct: 0,
            drive_mode: DriveMode::PushPull,
        })
        .expect("SPEED channel must configure");

    let board = Board::new(dir, arm, clear_n, speed, pgood, nfault, alarm);

    spawner.spawn(fg_task(fg).unwrap());
    spawner.spawn(hall_task(hall).unwrap());
    spawner.spawn(heartbeat_task(heartbeat).unwrap());
    spawner.spawn(control_task(board).unwrap());

    // TODO(phase C/D): Wi-Fi + Matter via rs-matter-embassy, and the tuning console.
    // Both must run on a *lower*-priority executor than the control loop and heartbeat
    // above, so a hung network stack degrades to "fan keeps its speed" rather than to a
    // watchdog stop (docs/controls.md > "Firmware safety architecture").
}

/// Drives the fan state machine. All the decisions live in `stillair-core`; this loop only
/// samples pins, hands time and inputs in, and applies whatever comes back.
#[embassy_executor::task]
async fn control_task(mut board: Board) {
    let initial = board.inputs();
    let mut supervisor = Supervisor::new(now(), &initial);
    let mut reported = supervisor.state();

    loop {
        let inputs: Inputs = board.inputs();
        for action in supervisor.poll(now(), &inputs) {
            board.apply(action);
        }

        if supervisor.state() != reported {
            reported = supervisor.state();
            log::info!(
                "state {:?} cmd {} rpm measured {} rpm fault {:?}",
                reported,
                supervisor.commanded().whole_rpm(),
                supervisor.measured().whole_rpm(),
                supervisor.fault()
            );
        }

        CONTROL_LOOP_BEAT.fetch_add(1, Ordering::Relaxed);
        Timer::after(CONTROL_TICK).await;
    }
}

/// Services the TPS3435 watchdog (2 Hz square wave on GPIO19).
///
/// Deliberately bit-banged, and deliberately conditional: a free-running peripheral would
/// keep feeding the watchdog straight through a hung control loop, which is exactly the
/// failure the watchdog exists to catch. If the control loop stops advancing its beat, the
/// toggling stops, the TPS3435 pulses WDO, and the hardware latch revokes drive permission
/// without firmware's involvement.
#[embassy_executor::task]
async fn heartbeat_task(mut heartbeat: Output<'static>) {
    let half_period = Duration::from_hz(u64::from(config::WATCHDOG_HEARTBEAT_HZ) * 2);
    let mut last_beat = CONTROL_LOOP_BEAT.load(Ordering::Relaxed);

    loop {
        Timer::after(half_period).await;
        let beat = CONTROL_LOOP_BEAT.load(Ordering::Relaxed);
        if beat == last_beat {
            // Say nothing, do nothing: letting the watchdog time out *is* the response.
            continue;
        }
        last_beat = beat;
        heartbeat.toggle();
    }
}

/// MCF FG, 20 pulses per mechanical revolution. 57 Hz at the 170 RPM ceiling.
#[embassy_executor::task]
async fn fg_task(mut fg: Input<'static>) {
    loop {
        fg.wait_for_rising_edge().await;
        FG_PULSES.fetch_add(1, Ordering::Relaxed);
    }
}

/// Rotor Hall, one pulse per revolution — the same pickup the analog overspeed chain
/// integrates. Counted here only for the plausibility cross-check; the overspeed
/// guarantee does not depend on this task, or on firmware at all.
#[embassy_executor::task]
async fn hall_task(mut hall: Input<'static>) {
    loop {
        hall.wait_for_rising_edge().await;
        HALL_PULSES.fetch_add(1, Ordering::Relaxed);
    }
}

/// Monotonic milliseconds since boot, in the form `stillair-core` expects.
fn now() -> Millis {
    Millis(Instant::now().as_millis())
}
