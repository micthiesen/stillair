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
use esp_hal::i2c::master::{Config as I2cConfig, I2c};
use esp_hal::interrupt::Priority;
use esp_hal::ledc::channel::ChannelIFace;
use esp_hal::ledc::timer::TimerIFace;
use esp_hal::ledc::{channel, timer, LSGlobalClkSource, Ledc, LowSpeed};
use esp_hal::time::Rate;
use esp_hal::timer::timg::TimerGroup;
use esp_hal::usb::usb_serial_jtag::UsbSerialJtag;
use esp_rtos::embassy::InterruptExecutor;
use static_cell::StaticCell;
use stillair_core::config;
use stillair_core::console::Telemetry;
use stillair_core::mcf8316;
use stillair_core::mcf_config::{self, ConfigCheck};
use stillair_core::speed;
use stillair_core::state::{Inputs, StatusRead, Supervisor};
use stillair_core::time::Millis;

mod board;
mod console;
mod matter;
mod mcf;
mod output;

use board::{Board, FG_PULSES, HALL_PULSES};
use mcf::{service_access, Mcf};

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

/// The control loop, the heartbeat, and the tach counters run here, above everything else.
///
/// This split is structural rather than a convention to remember. Once the Matter/Wi-Fi
/// tasks exist on the thread-mode executor, a hung network stack must degrade to the
/// network-loss row of the failure table (the fan keeps its speed) — not starve the
/// heartbeat and trip the watchdog, which would stop the fan. Establishing the higher
/// priority *before* those tasks exist is the only way that stays true by construction.
static CONTROL_EXECUTOR: StaticCell<InterruptExecutor<1>> = StaticCell::new();

#[esp_rtos::main]
async fn main(spawner: embassy_executor::Spawner) {
    // Not `esp_println::logger`: every line, log or protocol, goes through one queue and
    // one async writer. See `output.rs` for why printing from a critical section is not an
    // option once telemetry streams.
    output::init(log::LevelFilter::Info);

    let peripherals = esp_hal::init(esp_hal::Config::default());

    // Sized for Wi-Fi + BLE coexistence plus the ~4 KB of x509 work rs-matter's attestation
    // path allocates. The supervisor itself allocates nothing — everything on the control
    // path is statically sized — so this whole heap belongs to the radio and Matter.
    esp_alloc::heap_allocator!(size: 100 * 1024);

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

    let board = Board::new(
        dir,
        arm,
        clear_n,
        board::SpeedPwm::new(speed),
        pgood,
        nfault,
        alarm,
    );

    // MCF configuration and diagnostics. 100 kHz: the device clock-stretches while it
    // services its own interrupts, and there is nothing here worth hurrying.
    let i2c = I2c::new(
        peripherals.I2C0,
        I2cConfig::default().with_frequency(Rate::from_khz(100)),
    )
    .expect("I2C0 must configure")
    .with_sda(peripherals.GPIO0)
    .with_scl(peripherals.GPIO1)
    .into_async();

    // Everything that must keep running when the network does not.
    let control = CONTROL_EXECUTOR
        .init(InterruptExecutor::new(sw_int.software_interrupt1))
        .start(Priority::Priority3);
    control.spawn(fg_task(fg).unwrap());
    control.spawn(hall_task(hall).unwrap());
    control.spawn(heartbeat_task(heartbeat).unwrap());
    control.spawn(control_task(board).unwrap());

    // Diagnostics, the tuning console, and (later) the network stack live on the
    // thread-mode executor, below the control loop.
    spawner.spawn(mcf_task(Mcf::new(i2c, mcf8316::DEFAULT_TARGET_ID)).unwrap());
    let (usb_rx, usb_tx) = UsbSerialJtag::new(peripherals.USB_DEVICE)
        .into_async()
        .split();
    spawner.spawn(output::writer_task(usb_tx).unwrap());
    spawner.spawn(console::console_task(usb_rx).unwrap());
    spawner.spawn(console::stream_task().unwrap());

    // Matter runs to the end of `main`, which *is* the thread-mode executor's own task —
    // below the control loop's Priority3 interrupt executor by construction. Everything the
    // fan needs to stay safe has already been spawned above and keeps running regardless of
    // what the network stack does, which is the network-loss row of the failure table.
    matter::run(
        peripherals.RNG,
        peripherals.ADC1,
        peripherals.WIFI,
        peripherals.BT,
        peripherals.FLASH,
    )
    .await;
}

/// Drives the fan state machine. All the decisions live in `stillair-core`; this loop only
/// samples pins, hands time and inputs in, and applies whatever comes back.
#[embassy_executor::task]
async fn control_task(mut board: Board) {
    let initial = board.inputs();
    let mut supervisor = Supervisor::new(now(), &initial);
    let mut reported = supervisor.state();

    loop {
        while let Ok(command) = console::COMMANDS.try_receive() {
            supervisor.command(command);
        }

        let mut inputs: Inputs = board.inputs();
        // Absent a fresh read this stays `Stale`, which the supervisor treats as carrying
        // no information — neither evidence of a fault nor evidence of health.
        inputs.mcf_status = mcf::STATUS.try_take().unwrap_or(StatusRead::Stale);
        // A level, not an event: the last verdict stands until something changes it.
        inputs.config = mcf::verdict();

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

        console::publish(Telemetry {
            uptime_ms: now().0,
            state: supervisor.state(),
            fault: supervisor.fault(),
            target: supervisor.target(),
            commanded: supervisor.commanded(),
            measured_fg: supervisor.measured(),
            measured_hall: supervisor.measured_hall(),
            duty: speed::duty_for(supervisor.commanded()),
            direction: supervisor.direction(),
            released_min: supervisor.released_min(),
            config: supervisor.config(),
            dropped: output::dropped(),
        });

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

/// Polls the MCF's fault-status registers and services fault-clear requests.
///
/// Deliberately on the lower-priority executor: I²C is slow, can hang, and is never on the
/// path that keeps the fan safe. A bus that stops answering shows up to the supervisor as
/// accumulating `BusError`s, which becomes a stop after
/// [`config::BUS_FAILURES_BEFORE_FAULT`] — the drive is not commanded by something that can
/// no longer interrogate it.
#[embassy_executor::task]
async fn mcf_task(mut mcf: Mcf) {
    match mcf.probe().await {
        Some(target) => log::info!("MCF8316D found at I2C target {target:#04x}"),
        None => log::error!("no MCF8316D on the I2C bus; status reads will fail"),
    }

    // The last clause of the contract's safe-boot step. `SafeBoot` is holding for ten seconds
    // regardless, and this is a handful of register reads, so the check is free in wall-clock
    // terms — but until it publishes a verdict the supervisor will not leave SafeBoot, which
    // is what makes "stored configuration verified" a gate rather than a comment.
    let verdict = mcf_config::check(&mut mcf, mcf_config::IMAGE).await;
    match verdict {
        ConfigCheck::Verified => log::info!("MCF stored configuration verified"),
        ConfigCheck::Unverified => log::warn!(
            "MCF stored configuration NOT verified: no golden image has been captured yet \
             (`config dump` on a tuned device, then fill in mcf_config::IMAGE)"
        ),
        other => log::error!("MCF stored configuration check failed: {other:?}"),
    }
    mcf::publish_verdict(verdict);

    // What the last poll reported, so a standing condition is logged once rather than five
    // times a second.
    //
    // Found by running this on a bare dev board with no MCF on the bus: every failed read
    // emitted a warning, and at a 200 ms poll that flooded the bounded output queue and
    // evicted the telemetry frames saying what the fan was actually doing. A log that
    // destroys the record during exactly the condition you are trying to diagnose is worse
    // than no log. The supervisor gets every reading regardless — this only decides what a
    // human is told.
    let mut reported = None;

    loop {
        // `try_take` rather than `signaled()` + `reset()`: the control loop runs as a
        // higher-priority interrupt and can signal between those two calls, in which case
        // the reset would silently discard a request the user explicitly made.
        if mcf::CLEAR_FAULT_REQUEST.try_take().is_some() {
            match mcf.clear_faults().await {
                // Latched faults can take up to 200 ms to clear; the supervisor's
                // ten-second safe-boot hold covers that with room to spare.
                Ok(()) => log::info!("CLR_FLT issued"),
                Err(error) => log::error!("CLR_FLT failed: {error:?}"),
            }
        }

        // Console register accesses are serviced between status polls, so a tuning session
        // never has to wait a full poll interval for an answer.
        service_access(&mut mcf).await;

        let outcome = mcf.fault_status().await;
        // A repeat of the previous verdict says nothing new; a different one always does.
        let changed = reported != Some(outcome);
        reported = Some(outcome);

        match outcome {
            Ok(status) => {
                if changed {
                    if status.any() {
                        log::warn!(
                            "MCF fault status gate {:#010x} controller {:#010x} -> {:?}",
                            status.gate,
                            status.controller,
                            status.condition()
                        );
                    } else {
                        log::info!("MCF status clean");
                    }
                }
                mcf::STATUS.signal(StatusRead::Fresh(status));
            }
            Err(error) => {
                if changed {
                    log::warn!("MCF status read failing: {error:?}");
                }
                mcf::STATUS.signal(StatusRead::BusError);
                mcf.recover().await;
            }
        }

        // Split so a console access is picked up promptly rather than at the poll edge.
        for _ in 0..4 {
            service_access(&mut mcf).await;
            Timer::after(Duration::from_millis(config::STATUS_POLL_MS / 4)).await;
        }
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
