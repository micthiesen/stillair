//! Stillair ceiling-fan supervisor firmware.
//!
//! Runs on the ESP32-C6-WROOM-1-N8 on the custom PCB-01 V2 controller board.
//! The supervisor configures the MCF8316D over I²C and commands speed/direction;
//! it never switches motor phases. The behavioral contract lives in `docs/controls.md`
//! and is implemented — and unit-tested on the host — in `stillair-core`; this crate is
//! only the wiring that turns that contract into GPIO edges.
//!
//! GPIO map (verified against the ESP32-C6-WROOM-1 datasheet; GPIO15 is the only strap
//! pin used — its JTAG-select strap is ignored with default eFuses and the external
//! pull-up satisfies its no-float requirement):
//!
//! | GPIO    | Signal                       |
//! |---------|------------------------------|
//! | 0 / 1   | SDA / SCL (MCF I²C)          |
//! | 2       | SPEED PWM                    |
//! | 3       | DIR                          |
//! | 6       | TEMP_SDA                     |
//! | 7       | HALL_TACH sense (plausibility check input) |
//! | 10      | MCF ALARM (active-high)      |
//! | 11      | TEMP_SCL                     |
//! | 12 / 13 | USB D− / D+                  |
//! | 15      | MCU_CLEAR_N (open-drain out) |
//! | 16 / 17 | NC                           |
//! | 18      | permission ARM_PULSE         |
//! | 19      | watchdog heartbeat           |
//! | 20      | MCF FG                       |
//! | 21      | MCF nFAULT                   |
//! | 22      | 3.3 V PGOOD                  |
//! | 23      | watchdog WDO diagnostic      |

#![no_std]
#![no_main]

use core::sync::atomic::{AtomicBool, AtomicU32, Ordering};

use embassy_time::{Duration, Instant, Timer};
use esp_backtrace as _;
use esp_hal::gpio::{DriveMode, Input, InputConfig, Level, Output, OutputConfig, Pull};
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
use stillair_core::mcf8316::{self, reg};
use stillair_core::mcf_config::{self, ConfigCheck, ConfigFault};
use stillair_core::speed;
use stillair_core::state::{Command, FanState, Inputs, StatusRead, Supervisor};
use stillair_core::time::Millis;

mod board;
mod console;
mod matter;
mod mcf;
mod output;
mod wifi_diag;

use board::{
    Board, FG_PULSES, HALL_LAST_EDGE_MS, HALL_PERIOD_MS, HALL_PULSES, PGOOD_FELL, PGOOD_HIGH,
};
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

/// True only while main holds MCU_CLEAR_N asserted during hardware initialization.
///
/// The MCF's stored external watchdog can already be active when it wakes, so its shared
/// heartbeat pin must toggle during a slow address sweep. This flag permits that boot-only
/// service while drive is independently impossible. Once the real control task exists, the
/// heartbeat again advances only when [`CONTROL_LOOP_BEAT`] does.
static BOOT_INHIBIT_ACTIVE: AtomicBool = AtomicBool::new(true);

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

/// MCF register service runs above Matter/Wi-Fi but below the safety-critical control loop.
///
/// A commissioned Matter stack can keep the thread-mode executor busy for longer than the
/// supervisor's status-freshness deadline. Giving the bounded software-I2C task its own middle
/// priority prevents network work from looking like a dead motor-controller bus, while Priority3
/// control and watchdog work can still preempt every register transaction.
static MCF_EXECUTOR: StaticCell<InterruptExecutor<2>> = StaticCell::new();

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
    // Start asserted. This matters on an ESP-only reset: the external latch can retain an
    // earlier permission state while the MCU reboots. Open-drain means firmware can only
    // revoke permission, never force it on. Safe boot releases the line only after SPEED is
    // confirmed back at zero following the MCF wake/recovery sequence.
    let mut clear_n = Output::new(peripherals.GPIO15, Level::Low, open_drain);
    let heartbeat = Output::new(peripherals.GPIO19, Level::Low, push_pull);

    // Start the heartbeat before probing the MCF. A stored external-watchdog configuration
    // may already be live after SPEED wakes the device, and a changed I2C target can make the
    // bounded address sweep longer than its 1000 ms window. During this early service
    // MCU_CLEAR_N is held low, so heartbeat activity cannot accompany drive permission.
    let control = CONTROL_EXECUTOR
        .init(InterruptExecutor::new(sw_int.software_interrupt1))
        .start(Priority::Priority3);
    control.spawn(heartbeat_task(heartbeat).unwrap());
    let mcf_executor = MCF_EXECUTOR
        .init(InterruptExecutor::new(sw_int.software_interrupt2))
        .start(Priority::Priority2);

    // Inputs. No internal pulls: the board provides them.
    let floating = InputConfig::default().with_pull(Pull::None);
    let pgood = Input::new(peripherals.GPIO22, floating);
    PGOOD_HIGH.store(pgood.is_high(), Ordering::Release);
    let nfault = Input::new(peripherals.GPIO21, floating);
    let alarm = Input::new(peripherals.GPIO10, floating);
    let fg = Input::new(peripherals.GPIO20, floating);
    let hall = Input::new(peripherals.GPIO7, floating);

    // SPEED-pin PWM. 11-bit at 1 kHz, inside the MCF's `SPEED_RANGE_SEL` = 0h band.
    let ledc = LEDC.init(Ledc::new(peripherals.LEDC));
    ledc.set_global_slow_clock(LSGlobalClkSource::APBClk);
    let speed_timer = SPEED_TIMER.init(ledc.timer::<LowSpeed>(timer::Number::Timer0));
    speed_timer
        .configure(timer::config::Config {
            duty: timer::config::Duty::Duty11Bit,
            clock_source: timer::LSClockSource::APBClk,
            frequency: Rate::from_hz(config::SPEED_CARRIER_HZ),
        })
        .expect("SPEED carrier must be configurable at 1 kHz / 11 bit");

    let mut speed = ledc.channel(channel::Number::Channel0, peripherals.GPIO2);
    speed
        .configure(channel::config::Config {
            timer: speed_timer,
            duty_pct: 0,
            drive_mode: DriveMode::PushPull,
        })
        .expect("SPEED channel must configure");

    let mut speed = board::SpeedPwm::new(speed);
    // The MCF8316D requires a 100 us pause after every I2C byte. The ESP packet engine cannot
    // express that timing, so this small dedicated software bus owns GPIO0/1 and inserts the
    // pause exactly while preserving normal-speed data bits and protocol CRC.
    let mut mcf = Mcf::new(
        peripherals.GPIO0,
        peripherals.GPIO1,
        mcf8316::DEFAULT_TARGET_ID,
    );

    // First try the expected target at zero SPEED. A controller already in standby answers
    // here and needs no wake command. If it does not answer, recover a stored sleep mode by
    // holding SPEED high beyond TI's 5 ms maximum wake interval, then sweep in case EEPROM
    // also changed the target address. MCU_CLEAR_N stays asserted throughout, so no phase
    // output can be enabled even though SPEED is temporarily near full scale.
    let mut wake_used = false;
    let target = if mcf.probe_current().await {
        Some(mcf8316::DEFAULT_TARGET_ID)
    } else if speed.hold_wake_for_configuration() {
        wake_used = true;
        Timer::after(Duration::from_millis(config::MCF_WAKE_HOLD_MS)).await;
        mcf.probe().await
    } else {
        None
    };
    match target {
        Some(target) => log::info!("MCF8316D found at I2C target {target:#04x}"),
        None => log::error!("no MCF8316D on the I2C bus; status reads will fail"),
    }
    let standby = match target {
        Some(_) => mcf_config::ensure_standby(&mut mcf).await,
        None => Err(mcf_config::ConfigFault::Unreadable {
            address: mcf8316::reg::DEVICE_CONFIG2,
        }),
    };
    match standby {
        Ok(true) => log::warn!("MCF sleep mode cleared in volatile shadow for commissioning"),
        Ok(false) => log::info!("MCF standby mode already active"),
        Err(error) => log::error!("MCF standby recovery failed: {error:?}"),
    }
    if !speed.idle_after_configuration() {
        // `clear_n` deliberately remains asserted. Starting the supervisor with a stale
        // near-full SPEED command would let a later arm produce an uncontrolled start,
        // because its duty cache correctly assumes hardware began at zero.
        panic!("SPEED could not be returned to zero after MCF wake");
    }

    if wake_used {
        // A high speed command while DRVOFF is asserted can latch the expected start-failed
        // diagnostic. Clear that recovery artifact only after SPEED is confirmed zero. A
        // real standing condition reasserts, and permission remains revoked for the full
        // supervisor safe-boot hold before any user command can arm the drive.
        match mcf.clear_faults().await {
            Ok(()) => Timer::after(Duration::from_millis(250)).await,
            Err(error) => log::error!("failed to clear MCF wake diagnostic: {error:?}"),
        }
    }
    clear_n.set_high();

    let verdict = match standby {
        Ok(_) => mcf_config::check(&mut mcf, mcf_config::IMAGE).await,
        Err(error) => ConfigCheck::Failed(error),
    };
    match verdict {
        ConfigCheck::Verified => log::info!("MCF stored configuration verified"),
        ConfigCheck::Unverified => log::warn!(
            "MCF configuration is not runnable: use `config stage` for volatile bench \
             commissioning, or capture the tuned golden image"
        ),
        ConfigCheck::Provisional => {
            log::warn!("MCF volatile first-spin configuration staged; EEPROM unchanged")
        }
        other => log::error!("MCF stored configuration check failed: {other:?}"),
    }
    mcf::publish_verdict(verdict);

    let board = Board::new(dir, arm, clear_n, speed, nfault, alarm);

    // Everything else that must keep running when the network does not.
    control.spawn(fg_task(fg).unwrap());
    control.spawn(hall_task(hall).unwrap());
    control.spawn(pgood_task(pgood).unwrap());
    control.spawn(control_task(board).unwrap());
    BOOT_INHIBIT_ACTIVE.store(false, Ordering::Release);

    // Status and bounded register service must outlive stalls in Matter/Wi-Fi, but remain
    // preemptible by the Priority3 control and watchdog path.
    mcf_executor.spawn(mcf_task(mcf).unwrap());
    // The tuning console and network stack remain on the thread-mode executor. PCB-01 V2
    // exposes the C6's native USB Serial/JTAG peripheral; GPIO12/13 remain dedicated to it.
    let (console_rx, console_tx) = UsbSerialJtag::new(peripherals.USB_DEVICE)
        .into_async()
        .split();
    spawner.spawn(output::writer_task(console_tx).unwrap());
    spawner.spawn(console::console_task(console_rx).unwrap());
    spawner.spawn(console::stream_task().unwrap());
    spawner.spawn(wifi_diag::sample_task().unwrap());

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
        let config_service = console::config_service_active();
        while let Ok(command) = console::COMMANDS.try_receive() {
            if !config_service {
                supervisor.command(command);
            }
        }
        if config_service && supervisor.state() != FanState::Fault {
            supervisor.command(Command::Off);
        }
        if console::take_mpet_abort() {
            supervisor.command(Command::AbortMpet);
        }

        let mut inputs: Inputs = board.inputs();
        // The MCF shadow registers disappear with its rail even if USB keeps the ESP alive.
        // Invalidate both provisional and stored verdicts on the falling edge. A provisional
        // image must be staged again; a stored image must be checked again after power returns.
        let pgood_fell = PGOOD_FELL.swap(false, Ordering::AcqRel);
        if pgood_fell {
            mcf::invalidate_current_profile_readiness();
        }
        let verdict = mcf_config::after_pgood_loss(pgood_fell, mcf::verdict());
        if verdict != mcf::verdict() {
            mcf::publish_verdict(verdict);
        }
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
            on: supervisor.commanded_on(),
            target: supervisor.target(),
            commanded: supervisor.commanded(),
            measured_fg: supervisor.measured(),
            measured_hall: supervisor.measured_hall(),
            duty: speed::duty_for(supervisor.commanded()),
            direction: supervisor.direction(),
            requested_direction: supervisor.requested_direction(),
            released_min: supervisor.released_min(),
            config: supervisor.config(),
            dropped: output::dropped(),
        });

        CONTROL_LOOP_BEAT.fetch_add(1, Ordering::Relaxed);
        Timer::after(CONTROL_TICK).await;
    }
}

/// Tracks the MCF rail independently of the 50 ms control-loop sampling cadence.
#[embassy_executor::task]
async fn pgood_task(mut pgood: Input<'static>) {
    // Close the startup gap between the initial sample and this task beginning to await
    // edges. If the rail fell during that interval, preserve it as a falling event.
    let high = pgood.is_high();
    if PGOOD_HIGH.swap(high, Ordering::AcqRel) && !high {
        PGOOD_FELL.store(true, Ordering::Release);
    }
    loop {
        pgood.wait_for_any_edge().await;
        let high = pgood.is_high();
        PGOOD_HIGH.store(high, Ordering::Release);
        if !high {
            PGOOD_FELL.store(true, Ordering::Release);
        }
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
        if BOOT_INHIBIT_ACTIVE.load(Ordering::Acquire) {
            heartbeat.toggle();
            continue;
        }
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
/// Deliberately on the middle-priority executor: I²C is slow and can hang, so Priority3 control
/// and watchdog work must always preempt it. Keeping it above thread-mode Matter/Wi-Fi prevents
/// network work from starving status freshness. A bus that stops answering shows up to the
/// supervisor as accumulating `BusError`s, which becomes a stop after
/// [`config::BUS_FAILURES_BEFORE_FAULT`] — the drive is not commanded by something that can
/// no longer interrogate it.
async fn service_digital_speed_override(
    mcf_device: &mut Mcf,
    last_digital_speed: &mut Option<u32>,
    digital_speed_healthy: &mut bool,
) {
    match mcf::service_digital_speed(mcf_device, last_digital_speed).await {
        Ok(()) if !*digital_speed_healthy => {
            log::info!("MCF digital speed writes recovered");
            *digital_speed_healthy = true;
        }
        Ok(()) => {}
        Err(error) if *digital_speed_healthy => {
            log::warn!("MCF digital speed write failed: {error:?}");
            *digital_speed_healthy = false;
            mcf::invalidate_current_profile_readiness();
            let fault = match error {
                mcf::BusError::ReadbackMismatch => ConfigFault::Mismatch {
                    address: reg::ALGO_DEBUG1,
                },
                _ => ConfigFault::Unreadable {
                    address: reg::ALGO_DEBUG1,
                },
            };
            mcf::publish_verdict(ConfigCheck::Failed(fault));
        }
        Err(_) => {
            mcf::invalidate_current_profile_readiness();
        }
    }
}

#[embassy_executor::task]
async fn mcf_task(mut mcf: Mcf) {
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
    let mut last_digital_speed = None;
    let mut last_current_profile = None;
    let mut digital_speed_healthy = true;

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

        // Abort first if both signals raced: a stop/fault must win over a stale start.
        if mcf::MPET_ABORT_REQUEST.try_take().is_some() {
            mcf::MPET_START_REQUEST.reset();
            match mcf.abort_mpet().await {
                Ok(()) => log::info!("MPET aborted"),
                Err(error) => log::error!("MPET abort failed: {error:?}"),
            }
        } else if mcf::MPET_START_REQUEST.try_take().is_some() {
            match mcf.start_mpet(mcf::mpet_command()).await {
                Ok(()) => log::info!("MPET started; results remain in shadow until committed"),
                Err(error) => {
                    log::error!("MPET start failed: {error:?}");
                    console::request_mpet_abort();
                }
            }
        }

        // Console register accesses are serviced between status polls, so a tuning session
        // never has to wait a full poll interval for an answer.
        service_access(&mut mcf).await;

        if let Err(error) = mcf::service_current_profile(&mut mcf, &mut last_current_profile).await
        {
            log::warn!("MCF current-profile write failed: {error:?}");
        }

        // An internal MCF reset can reload EEPROM without dropping PGOOD. One critical
        // provisional word is enough to detect that all-shadow reset cheaply; a mismatch
        // revokes operation within the next 200 ms status interval.
        if mcf::verdict() == ConfigCheck::Provisional {
            let check = mcf_config::check_provisional_sentinel(&mut mcf).await;
            if check != ConfigCheck::Provisional {
                mcf::publish_verdict(check);
            }
        } else if mcf::verdict() == ConfigCheck::Tuning {
            let check = match mcf::tuning_candidate() {
                Some(candidate) => {
                    mcf_config::check_loaded_candidate_sentinel(&mut mcf, candidate).await
                }
                None => ConfigCheck::Unverified,
            };
            if check != ConfigCheck::Tuning {
                mcf::publish_verdict(check);
            }
        }

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
            // Check the 20 Hz firmware ramp at every 50 ms service slice. An unchanged word
            // performs no I²C, while a change no longer waits behind an entire status cycle.
            service_digital_speed_override(
                &mut mcf,
                &mut last_digital_speed,
                &mut digital_speed_healthy,
            )
            .await;
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
        let edge_ms = Instant::now().as_millis() as u32;
        let previous = HALL_LAST_EDGE_MS.swap(edge_ms, Ordering::Relaxed);
        if previous != 0 {
            HALL_PERIOD_MS.store(edge_ms.wrapping_sub(previous), Ordering::Relaxed);
        }
        HALL_PULSES.fetch_add(1, Ordering::Relaxed);
    }
}

/// Monotonic milliseconds since boot, in the form `stillair-core` expects.
fn now() -> Millis {
    Millis(Instant::now().as_millis())
}
