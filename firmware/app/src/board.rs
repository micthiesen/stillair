//! The ESP32-C6 side of the supervisor: pins, PWM, and applying [`Action`]s.
//!
//! This module is the only place that knows a GPIO exists. Everything above it works in
//! terms of the sans-I/O contract in `stillair-core`, which is why that contract is
//! testable on a laptop and this file is not.

use core::sync::atomic::{AtomicBool, AtomicU32, Ordering};

use embedded_hal::pwm::SetDutyCycle;
use esp_hal::gpio::{Input, Level, Output};
use esp_hal::ledc::{channel, LowSpeed};
use stillair_core::config;
use stillair_core::mcf_config::ConfigCheck;
use stillair_core::state::{Action, Direction, Inputs, StatusRead};

/// The SPEED-pin PWM channel, made movable between executors.
///
/// `Channel` is not `Send` because it holds `&'static pac::ledc::RegisterBlock` — a PAC
/// register block backed by `UnsafeCell`, and therefore not `Sync`, so a shared reference to
/// it is not `Send`. (It also holds a reference to the timer, but that is not what the
/// compiler objects to; verified by removing this impl and reading the error.)
///
/// That bound is about *sharing*; what we do is *move*. The LEDC block, the timer, and the
/// channel are all configured in `main` on the thread-mode executor **before** the interrupt
/// executor is started, so no higher-priority context exists yet during setup. The channel
/// is then moved by value into the control task and touched only there. `StaticCell::init`
/// makes a second timer reference impossible, and the borrow checker forbids reusing the
/// timer binding after `configure` takes it.
///
/// This is the one unsafe assertion in the firmware, and it is load-bearing: the duty write
/// is on the safety path (it is how a stop and a fault reach the hardware), so it must live
/// on the high-priority executor alongside the rest of the control loop rather than being
/// delegated to a task the network can starve.
pub struct SpeedPwm(channel::Channel<'static, LowSpeed>);

// SAFETY: moved once at startup into a single task; never shared, never accessed from two
// contexts. If a second user of the LEDC channel is ever introduced, this must go.
unsafe impl Send for SpeedPwm {}

impl SpeedPwm {
    pub fn new(channel: channel::Channel<'static, LowSpeed>) -> Self {
        Self(channel)
    }

    /// Hold SPEED/WAKE high while safe-boot makes the MCF's volatile shadow use standby.
    ///
    /// One count below full scale is effectively a continuous high at 1 kHz while avoiding
    /// the LEDC full-scale alias-to-zero edge case. The hardware permission latch is still
    /// cleared throughout this boot-only operation, so DRVOFF keeps every MOSFET Hi-Z.
    pub fn hold_wake_for_configuration(&mut self) -> bool {
        let duty = self.0.max_duty_cycle().saturating_sub(1);
        self.set_raw(duty, "MCF wake")
    }

    /// Return the SPEED pin to its normal stopped command before the control loop starts.
    pub fn idle_after_configuration(&mut self) -> bool {
        self.set_raw(0, "MCF wake release")
    }

    fn set_raw(&mut self, duty: u16, operation: &'static str) -> bool {
        match self.0.set_duty_cycle(duty) {
            Ok(()) => true,
            Err(error) => {
                log::error!("{operation} SPEED duty write failed ({error:?})");
                false
            }
        }
    }
}

/// Free-running tach edge counters, incremented by the edge tasks and sampled by the
/// control loop. Relaxed ordering is sufficient: these are counters, not a handshake, and
/// the supervisor only ever asks whether they advanced.
pub static FG_PULSES: AtomicU32 = AtomicU32::new(0);
pub static HALL_PULSES: AtomicU32 = AtomicU32::new(0);
/// Current PGOOD level and a sticky falling-edge latch, maintained by `pgood_task`.
pub static PGOOD_HIGH: AtomicBool = AtomicBool::new(false);
pub static PGOOD_FELL: AtomicBool = AtomicBool::new(false);

/// Minimum ARM_PULSE width. The permission latch needs a clean, deliberate edge; the
/// datasheet minimum is 10 µs and this is generously above it.
const ARM_PULSE_US: u32 = 50;

/// How long MCU_CLEAR_N is held low to revoke permission.
const CLEAR_PULSE_US: u32 = 100;

/// Worst-case blocking one `poll` can inflict on the interrupt executor: every action in a
/// full buffer being a pulse. This runs at elevated priority and does not yield, so it
/// delays the heartbeat toggle and both tach edge services for its duration.
const MAX_BLOCKING_US: u32 = if ARM_PULSE_US > CLEAR_PULSE_US {
    ARM_PULSE_US
} else {
    CLEAR_PULSE_US
} * stillair_core::state::MAX_ACTIONS as u32;

// The heartbeat half-period is the tightest thing this can eat into; anything approaching it
// would start costing watchdog margin. Two orders of magnitude of headroom, checked at
// compile time so growing a pulse width or the action buffer cannot silently erode it.
/// Heartbeat half-period, in microseconds.
const HEARTBEAT_HALF_PERIOD_US: u64 = 1_000_000 / (config::WATCHDOG_HEARTBEAT_HZ as u64 * 2);
const _: () = assert!(MAX_BLOCKING_US as u64 * 100 < HEARTBEAT_HALF_PERIOD_US);

/// Everything the supervisor drives or samples.
pub struct Board {
    dir: Output<'static>,
    arm: Output<'static>,
    /// Open-drain, idle high. Pulling it low revokes drive permission at the latch;
    /// firmware can never assert permission this way, only remove it.
    clear_n: Output<'static>,
    speed: SpeedPwm,
    /// nFAULT is active low; [`Board::inputs`] normalises it.
    nfault: Input<'static>,
    alarm: Input<'static>,
}

impl Board {
    pub fn new(
        dir: Output<'static>,
        arm: Output<'static>,
        clear_n: Output<'static>,
        speed: SpeedPwm,
        nfault: Input<'static>,
        alarm: Input<'static>,
    ) -> Self {
        Self {
            dir,
            arm,
            clear_n,
            speed,
            nfault,
            alarm,
        }
    }

    /// Sample every supervisor input at one instant.
    pub fn inputs(&self) -> Inputs {
        Inputs {
            pgood: PGOOD_HIGH.load(Ordering::Acquire),
            mcf_fault: self.nfault.is_low(),
            mcf_alarm: self.alarm.is_high(),
            // Both filled in by the control loop from the I2C task; the pins say nothing
            // about either.
            mcf_status: StatusRead::Stale,
            config: ConfigCheck::Pending,
            fg_pulses: FG_PULSES.load(Ordering::Relaxed),
            hall_pulses: HALL_PULSES.load(Ordering::Relaxed),
        }
    }

    /// Apply one supervisor action.
    ///
    /// The pulses block for tens of microseconds rather than awaiting a timer: they are
    /// shorter than the executor's scheduling granularity, and ARM_PULSE in particular
    /// must be a single deliberate software-sequenced edge, never something a peripheral
    /// or a preempted task could leave half-finished.
    pub fn apply(&mut self, action: Action) {
        match action {
            Action::ArmPulse => {
                self.arm.set_high();
                blocking_delay_us(ARM_PULSE_US);
                self.arm.set_low();
            }
            Action::ClearPermission => {
                self.clear_n.set_low();
                blocking_delay_us(CLEAR_PULSE_US);
                self.clear_n.set_high();
            }
            Action::SetSpeedDuty(duty) => {
                // Live commissioning proved that the MCF sees the physical PWM waveform but
                // decodes its duty as zero. Keep that pin at zero while the provisional image
                // uses the volatile I2C override. This also makes an unexpected MCF reset safe:
                // its default analog-input mode sees a stopped command, not an averaged PWM.
                if let Err(error) = self.speed.0.set_duty_cycle(0) {
                    log::error!("SPEED zero write failed ({error:?}); pin may be stale");
                }
                crate::mcf::set_digital_speed(duty);
            }
            Action::SetDirection(direction) => self.dir.set_level(match direction {
                Direction::Forward => Level::Low,
                Direction::Reverse => Level::High,
            }),
            Action::ClearMcfFault => {
                // Handed to the I²C task rather than performed here: the control loop must
                // not block on a bus that may be exactly what is broken.
                crate::mcf::CLEAR_FAULT_REQUEST.signal(());
            }
            Action::StartMpet => crate::mcf::MPET_START_REQUEST.signal(()),
            Action::AbortMpet => crate::mcf::MPET_ABORT_REQUEST.signal(()),
        }
    }
}

/// Busy-wait for microsecond-scale pulse widths.
fn blocking_delay_us(us: u32) {
    let deadline =
        esp_hal::time::Instant::now() + esp_hal::time::Duration::from_micros(u64::from(us));
    while esp_hal::time::Instant::now() < deadline {}
}
