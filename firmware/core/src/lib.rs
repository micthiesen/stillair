//! Stillair supervisor logic, with no dependency on any hardware.
//!
//! Everything the fan's behavioral contract (`docs/controls.md`) specifies lives here as
//! plain, deterministic Rust: the state machine, the speed conversions, the tachometer
//! plausibility rules, and the MCF8316D register encoding. The crate is sans-I/O — it
//! consumes sampled [`state::Inputs`] plus a monotonic timestamp and emits
//! [`state::Action`]s for a caller to apply. Nothing here blocks, sleeps, or touches a
//! peripheral, which is what makes the whole contract testable on a laptop.
//!
//! The ESP32-C6 wiring that turns those actions into GPIO edges lives in `../app`.

#![cfg_attr(not(test), no_std)]

pub mod config;
pub mod mcf8316;
pub mod speed;
pub mod state;
pub mod tach;
pub mod time;
