//! Stillair ceiling-fan supervisor firmware (stub).
//!
//! Runs on the ESP32-C6-MINI-1-H4 on the custom 78 × 58 mm controller board.
//! The supervisor configures the MCF8316D over I²C and commands speed/direction;
//! it never switches motor phases. The full behavioral contract lives in
//! `docs/controls.md`; the board pinout lives in `docs/electrical.md` (SCH-04).
//!
//! GPIO map (starting assignment; recheck strap behavior before PCB capture):
//!
//! | GPIO    | Signal                  |
//! |---------|-------------------------|
//! | 0 / 1   | SDA / SCL (MCF I²C)     |
//! | 2       | SPEED PWM               |
//! | 3       | DIR                     |
//! | 12 / 13 | USB D− / D+             |
//! | 14      | NTC ADC (optional)      |
//! | 16 / 17 | UART TX / RX            |
//! | 18      | permission ARM_PULSE    |
//! | 19      | watchdog heartbeat      |
//! | 20      | MCF FG                  |
//! | 21      | MCF nFAULT              |
//! | 22      | 3.3 V PGOOD             |
//! | 23      | watchdog WDO diagnostic |

#![no_std]
#![no_main]
// Stub scaffolding: modules define the eventual API surface before anything
// consumes it. Remove once the hardware interfaces are wired up.
#![allow(dead_code)]

use embassy_time::{Duration, Timer};
use esp_backtrace as _;
use esp_hal::timer::timg::TimerGroup;

mod config;
mod mcf8316;
mod state;

esp_bootloader_esp_idf::esp_app_desc!();

#[esp_rtos::main]
async fn main(spawner: embassy_executor::Spawner) {
    esp_println::logger::init_logger_from_env();

    let peripherals = esp_hal::init(esp_hal::Config::default());

    // Heap is only needed once the radio (Wi-Fi / HomeKit) comes online.
    esp_alloc::heap_allocator!(size: 72 * 1024);

    let timg0 = TimerGroup::new(peripherals.TIMG0);
    let sw_int =
        esp_hal::interrupt::software::SoftwareInterruptControl::new(peripherals.SW_INTERRUPT);
    esp_rtos::start(timg0.timer0, sw_int.software_interrupt0);

    log::info!("stillair supervisor boot (stub)");

    // TODO: bring up the hardware interfaces once the V1 board exists:
    //   - I²C to the MCF8316D (GPIO0/1) and initial register verification
    //   - watchdog heartbeat output on GPIO19 (2 Hz, serviced on the falling edge)
    //   - SPEED PWM (GPIO2), DIR (GPIO3), ARM_PULSE (GPIO18), MCU_CLEAR_N
    //   - FG (GPIO20), nFAULT (GPIO21), PGOOD (GPIO22), WDO (GPIO23) inputs
    //   - Wi-Fi + local HomeKit (esp-radio / embassy-net are already in the dep tree)

    spawner.spawn(supervisor_task().unwrap());
    spawner.spawn(heartbeat_task().unwrap());
}

/// Drives the fan state machine. Stub: ticks the (empty) supervisor.
#[embassy_executor::task]
async fn supervisor_task() {
    let mut supervisor = state::Supervisor::new();
    loop {
        supervisor.tick();
        Timer::after(Duration::from_millis(100)).await;
    }
}

/// Will service the TPS3435 watchdog (2 Hz square wave on GPIO19). The watchdog
/// starts monitoring immediately at power-up; until firmware arms the permission
/// latch that is safe because U5 powers up cleared. Stub: logs instead of toggling.
#[embassy_executor::task]
async fn heartbeat_task() {
    let half_period = Duration::from_hz(u64::from(config::WATCHDOG_HEARTBEAT_HZ) * 2);
    let mut ticks: u32 = 0;
    loop {
        // TODO: toggle the GPIO19 heartbeat output here.
        ticks = ticks.wrapping_add(1);
        if ticks.is_multiple_of(config::WATCHDOG_HEARTBEAT_HZ * 2 * 30) {
            log::info!("heartbeat alive ({ticks} half-periods)");
        }
        Timer::after(half_period).await;
    }
}
