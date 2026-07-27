//! The ESP32-C6 side of the supervisor: pins, PWM, and applying [`Action`]s.
//!
//! This module is the only place that knows a GPIO exists. Everything above it works in
//! terms of the sans-I/O contract in `stillair-core`, which is why that contract is
//! testable on a laptop and this file is not.

use core::sync::atomic::{AtomicU32, Ordering};

use embedded_hal::pwm::SetDutyCycle;
use esp_hal::gpio::{Input, Level, Output};
use esp_hal::ledc::{channel, LowSpeed};
use stillair_core::state::{Action, Direction, Inputs, StatusRead};

/// The SPEED-pin PWM channel, made movable between executors.
///
/// `Channel` is not `Send` because it holds a shared reference to the LEDC timer, which has
/// interior mutability and so is not `Sync`. That bound is about *sharing*; what we do is
/// *move*. The channel is configured once in `main`, handed to the control task exactly
/// once at startup, and thereafter touched only by that task — no second owner and no
/// concurrent access ever exist.
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
}

/// Free-running tach edge counters, incremented by the edge tasks and sampled by the
/// control loop. Relaxed ordering is sufficient: these are counters, not a handshake, and
/// the supervisor only ever asks whether they advanced.
pub static FG_PULSES: AtomicU32 = AtomicU32::new(0);
pub static HALL_PULSES: AtomicU32 = AtomicU32::new(0);

/// Minimum ARM_PULSE width. The permission latch needs a clean, deliberate edge; the
/// datasheet minimum is 10 µs and this is generously above it.
const ARM_PULSE_US: u32 = 50;

/// How long MCU_CLEAR_N is held low to revoke permission.
const CLEAR_PULSE_US: u32 = 100;

/// Everything the supervisor drives or samples.
pub struct Board {
    dir: Output<'static>,
    arm: Output<'static>,
    /// Open-drain, idle high. Pulling it low revokes drive permission at the latch;
    /// firmware can never assert permission this way, only remove it.
    clear_n: Output<'static>,
    speed: SpeedPwm,
    pgood: Input<'static>,
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
        pgood: Input<'static>,
        nfault: Input<'static>,
        alarm: Input<'static>,
    ) -> Self {
        Self {
            dir,
            arm,
            clear_n,
            speed,
            pgood,
            nfault,
            alarm,
        }
    }

    /// Sample every supervisor input at one instant.
    pub fn inputs(&self) -> Inputs {
        Inputs {
            pgood: self.pgood.is_high(),
            mcf_fault: self.nfault.is_low(),
            mcf_alarm: self.alarm.is_high(),
            // Filled in by the control loop from the I2C task; the pins say nothing
            // about it.
            mcf_status: StatusRead::Stale,
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
                // Deliberately *not* `Channel::set_duty`, which takes whole percent: 1%
                // steps are 1.8 RPM, far too coarse to tune a fan whose whole range starts
                // at 35 RPM. `SetDutyCycle` writes the raw 11-bit value the supervisor
                // already works in.
                //
                // `duty_for` already clamps below full scale; clamping again against what
                // the peripheral reports keeps the two from drifting apart if the timer is
                // ever reconfigured to a different resolution.
                let max = self.speed.0.max_duty_cycle().saturating_sub(1);
                // Never silently dropped: the supervisor caches the last duty it emitted
                // and will not re-send an unchanged value, so a swallowed failure would
                // leave the SPEED pin at a stale duty — including a nonzero one on the
                // stop and fault paths — with nothing to notice it.
                if let Err(error) = self.speed.0.set_duty_cycle(duty.0.min(max)) {
                    log::error!("SPEED duty write failed ({error:?}); pin may be stale");
                }
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
        }
    }
}

/// Busy-wait for microsecond-scale pulse widths.
fn blocking_delay_us(us: u32) {
    let deadline =
        esp_hal::time::Instant::now() + esp_hal::time::Duration::from_micros(u64::from(us));
    while esp_hal::time::Instant::now() < deadline {}
}
