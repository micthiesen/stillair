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

/// Speed ceiling stored in the MCF8316D itself (mechanical RPM).
pub const RPM_MCF_LIMIT: u32 = 180;

/// Independent analog overspeed trip, nominal rising threshold (mechanical RPM).
pub const RPM_ANALOG_TRIP: u32 = 200;

/// Initial acceleration/deceleration ramp, mechanical RPM per second.
pub const RAMP_RPM_PER_S: f32 = 1.5;

/// DRVOFF must remain high this long after power-up or any permission-clearing
/// fault before re-arming (TI safe-operation requirement).
pub const SAFE_BOOT_HOLD_SECS: u32 = 10;

/// TPS3435 heartbeat rate on GPIO19. The watchdog services on the falling edge
/// and times out after 1.6 s nominal.
pub const WATCHDOG_HEARTBEAT_HZ: u32 = 2;
