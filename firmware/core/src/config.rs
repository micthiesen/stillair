//! Fixed control limits from the design contract (`docs/controls.md`).
//!
//! These are firmware-side mirrors of independently enforced limits: the MCF8316D
//! stores its own 180 RPM ceiling, and the analog tach chain trips at 200 RPM
//! without any firmware participation. Firmware must never rely on itself as the
//! only limit.

/// Motor pole pairs (GL100 KV10).
pub const POLE_PAIRS: u32 = 20;

/// Qualification target user range, RPM. The released minimum may end up higher;
/// it is gated on the full start + acoustic matrix (`testing/test-matrix.csv`).
pub const RPM_USER_MIN_TARGET: u32 = 35;
pub const RPM_USER_MAX: u32 = 170;

/// Speed ceiling stored in the MCF8316D itself (mechanical RPM). Also the full-scale
/// of the SPEED-pin duty mapping: commanded speed = duty × MAX_SPEED.
pub const RPM_MCF_LIMIT: u32 = 180;

/// Independent analog overspeed trip, nominal rising threshold (mechanical RPM).
pub const RPM_ANALOG_TRIP: u32 = 200;

/// Initial acceleration/deceleration ramp, thousandths of a mechanical RPM per second
/// (= 1.5 RPM/s, per docs/controls.md). Expressed in integer milli-RPM because the
/// ESP32-C6 is RV32IMAC with no hardware FPU — soft-float in the control loop buys
/// nothing here.
pub const RAMP_MILLI_RPM_PER_S: u32 = 1_500;

/// DRVOFF must remain high this long after power-up or any permission-clearing
/// fault before re-arming (TI safe-operation requirement).
pub const SAFE_BOOT_HOLD_SECS: u64 = 10;
pub const SAFE_BOOT_HOLD_MS: u64 = SAFE_BOOT_HOLD_SECS * 1_000;

/// TPS3435 heartbeat rate on GPIO19. The watchdog services on the falling edge
/// and times out after 1.6 s nominal. MUST be bit-banged by a task that attests
/// control-loop liveness — never a free-running peripheral (docs/controls.md >
/// "Firmware safety architecture").
pub const WATCHDOG_HEARTBEAT_HZ: u32 = 2;

/// "Verified stopped" criterion: no FG edge AND no Hall edge for this long after
/// commanding zero speed (docs/controls.md).
pub const STOPPED_QUIET_SECS: u64 = 5;
pub const STOPPED_QUIET_MS: u64 = STOPPED_QUIET_SECS * 1_000;

/// Running plausibility: stop the fan if FG is nonzero while the Hall channel
/// stays quiet for this many revolutions (Hall-loss single-point backstop).
pub const HALL_PLAUSIBILITY_REVS: u32 = 5;

/// FG pulses per mechanical revolution, with `FG_DIV` = 1h (docs/electrical.md).
pub const FG_PULSES_PER_REV: u32 = 20;

/// The rotor Hall tach is deliberately one pulse per revolution — the same signal the
/// analog overspeed chain integrates.
pub const HALL_PULSES_PER_REV: u32 = 1;

/// Settling time between arming the permission latch and commanding a nonzero speed.
/// Covers the latch propagating to DRVOFF; not a datasheet number, just slack.
pub const ARM_SETTLE_MS: u64 = 50;

/// Device-side backstop for an abandoned MPET host session. The host normally uses a
/// 120-second deadline and aborts first; this ensures a disconnected laptop cannot leave
/// extraction armed indefinitely.
pub const MPET_TIMEOUT_MS: u64 = 130_000;

/// Firmware-defined start supervision: if the rotor shows no FG motion this long after
/// the ramp begins, the start failed (permission never took, rotor jammed, or the
/// analog lock is latched) and the supervisor faults rather than commanding into a
/// dead drive. Derived requirement, not from TI.
pub const START_TIMEOUT_MS: u64 = 15_000;

/// A start is gated on both tach channels being quiet (the pre-arm plausibility rule).
/// A windmilling rotor therefore delays a start; if it has not gone quiet within this
/// long, report a service condition instead of waiting forever.
pub const START_QUIET_TIMEOUT_MS: u64 = 120_000;

/// Full scale of the SPEED-pin PWM duty command, in duty units. 11 bits is the
/// resolution the 200 Hz carrier holds per TI's resolution table.
pub const SPEED_DUTY_FULL_SCALE: u16 = 2_048;

/// The largest duty that is actually *writable*. An 11-bit duty register holds 0..=2047;
/// writing full scale aliases to zero, so a maximum command would stop the fan.
pub const SPEED_DUTY_MAX: u16 = SPEED_DUTY_FULL_SCALE - 1;

/// SPEED-pin PWM carrier, Hz. Must sit inside the `SPEED_RANGE_SEL` = 1h band
/// (10–325 Hz); the register's default band would put this silently out of range.
pub const SPEED_CARRIER_HZ: u32 = 200;

/// Window over which FG pulses are integrated into a speed estimate. At the 35 RPM
/// target this is ~12 FG pulses, enough for a stable reading.
pub const SPEED_ESTIMATE_WINDOW_MS: u64 = 1_000;

/// Consecutive failed MCF status reads before the supervisor treats the drive as
/// unreachable and stops. One failure is a transient worth retrying (and worth a bus
/// recovery attempt); sustained silence means we are commanding something we can no longer
/// interrogate. At the status-poll interval this is a little under a second.
pub const BUS_FAILURES_BEFORE_FAULT: u32 = 5;

/// How often the fault-status registers are read. Far slower than the pin sampling in the
/// control loop, because the pins are the fast path and this is the diagnosis.
pub const STATUS_POLL_MS: u64 = 200;

/// How long past the safe-boot hold the supervisor will wait for a verdict on the MCF's
/// stored configuration before treating the silence as a failed check.
///
/// The check runs on the I²C task, concurrently with the ten-second hold, and is a handful of
/// register reads — so it has finished long before the hold ends unless something is wrong.
/// The grace exists so a slow bus is not mistaken for a bad configuration; waiting forever is
/// not an option, because a supervisor stuck in `SafeBoot` with no fault reported looks
/// exactly like a board that will not boot.
pub const CONFIG_CHECK_GRACE_MS: u64 = 5_000;

/// How long the supervisor will run armed without *any* status verdict — success or
/// failure — before treating the drive as unreachable.
///
/// Counting failures alone is not enough: a reader that has stopped running altogether
/// reports nothing, so the failure count never moves and total silence would be
/// indistinguishable from "nothing new this tick". Ten poll intervals is generous enough to
/// ride out a slow bus and short enough that a starved or dead reader is caught quickly.
pub const STATUS_STALE_TIMEOUT_MS: u64 = STATUS_POLL_MS * 10;

// The layered-limit invariant, checked when the crate compiles rather than trusted: the
// user maximum sits under the MCF's stored ceiling, which sits under the analog trip. Any
// edit that inverts them fails the build instead of quietly removing a layer.
const _: () = assert!(RPM_USER_MIN_TARGET < RPM_USER_MAX);
const _: () = assert!(RPM_USER_MAX < RPM_MCF_LIMIT);
const _: () = assert!(RPM_MCF_LIMIT < RPM_ANALOG_TRIP);
