# Motor-control contract

An implementation contract, not firmware. Application code lives in
[`firmware/`](../firmware/) (Rust, `no_std`, ESP32-C6); this doc defines what it must do.

## Selected hardware

- Motor: CubeMars GL100 KV10, 24 V, 20 pole pairs.
- Controller: custom 78 × 58 mm V1/V2 board around MCF8316DULVRGFR (no TI evaluation module).
- Supervisor: ESP32-C6-MINI-1-H4 (same 4 MB capacity and footprint as N4, but −40 to 105 °C
  instead of −40 to 85 °C).
- Supply: Mean Well GST60A24-P1J, 24 V / 2.5 A / 60 W.
- Independent overspeed: one-pulse rotor Hall tach, LM2907, TLV1701 comparator, hardware
  permission latch (see [electrical.md](electrical.md)).

## Measured-data gate

CubeMars publishes 2.650 Ω line resistance, 2.350 mH line inductance, 1.030 N·m/A torque
constant, 102.4 V/krpm BEMF, and 20 pole pairs. For a star connection, begin with 1.325 Ω and
1.175 mH phase-neutral. CubeMars does not state the amplitude/phase convention needed to
translate its BEMF number into TI's phase-neutral peak convention, so treat 320
mV/electrical-Hz as an unverified V1 commissioning guess.

Run MPET on the purchased GL100 and scope line-to-line BEMF while manually spinning it. The
measured R, L, and BEMF values replace the provisional register values before final EEPROM
release.

## Initial MCF8316D configuration

- Provisional `MOTOR_RES`: `0xB1` (1.35 Ω; measured value wins).
- Provisional `MOTOR_IND`: `0xAE` (1.20 mH; measured value wins).
- Provisional `MOTOR_BEMF_CONST`: `0xCA` (320 mV/electrical-Hz; measured value wins).
- Pole pairs: 20.
- PWM frequency: 40 kHz starting point.
- Open-loop current limit: 1.5 A (`0x4`). Closed-loop current limit: 1.5 A (`0x4`).
- Lock-detection current limits: 2.0 A (`0x5`), latched Hi-Z response, no automatic retry.
- Bus power limiting enabled, initial maximum 50 W (`0x400`).
- Stored maximum speed: 180 mechanical RPM = 60 electrical Hz = decimal 360 (`0x0168`) using
  TI's `electrical Hz = MAX_SPEED / 6` scaling. Verify against the exact silicon revision.
- Maximum VM: 28 V, latched. Minimum VM: 18 V, automatic recovery.
- Disable flux weakening and overmodulation.
- Enable AVS. Coast for normal stops; avoid deliberate regeneration into the desktop supply.
- Acceleration/deceleration: begin near 1.5 mechanical RPM/s.

## Electrical control contract

- Runtime commands: PWM speed, DIR, ARM_PULSE, and open-drain MCU_CLEAR_N. Firmware never
  drives DRVOFF directly.
- Feedback: FG, nFAULT, 3.3 V PGOOD, watchdog diagnostic, and optional temperature.
- Configuration and diagnostics: I²C to the MCF8316D.
- Convert FG using 20 pole pairs and the configured FG divider. Verify the conversion against
  an independent optical tachometer.
- The MCF commutates phases and limits current. The ESP32 never commutates phases.
- `nFAULT` is diagnostic, not an asynchronous clear input to the external permission latch.
  Configure MCF lock/fault responses to latched Hi-Z.
- TI specifies DRVOFF should remain high for at least 10 seconds for safe operation. Enforce
  this after power-up and permission-clearing faults before re-arming.

## Independent limits

- Qualification target user range: 35–170 RPM. Test 30, 35, and 40 RPM; release the minimum
  no lower than the lowest point that passes the complete start and acoustic matrix.
- MCF speed ceiling: 180 RPM.
- Hardware analog overspeed: calibrate 200 RPM nominal rising and 180 RPM nominal reset.
  Across voltage and temperature, trip must remain above 190 RPM and at or below 220 RPM.
- Analog overspeed or tach-rail loss clears a persistent hardware safety lock. Raw reset does
  not restore it; only a low-voltage power cycle can, followed by the normal 10-second safe
  boot and a fresh command.
- Acceleration and deceleration: begin at 1–3 RPM/s.
- Power-on command: zero and disabled.
- Direction changes only after ramping to zero and verifying the rotor is stopped.

## Required state behavior

1. **Safe boot**: hold DRVOFF high for at least 10 seconds while rails, watchdog, limits, and
   stored configuration are verified.
2. **Idle off**: output disabled and speed command zero.
3. **Start**: set direction only while stopped, arm permission, release DRVOFF, ramp slowly.
4. **Run**: maintain the last local speed when the Matter controller or Wi-Fi disappears.
5. **Normal stop**: ramp to zero and coast.
6. **Reverse**: ramp to zero, verify near-zero FG and optical-tach behavior, coast, change
   DIR, then restart.
7. **Fault**: enter Hi-Z, clear permission where applicable, expose diagnostics, and require
   a fresh user command.

## Failure behavior

| Event | Required result |
|---|---|
| Matter controller or Wi-Fi unavailable | Continue at the last locally held speed and direction. |
| ESP32 hang | TPS3435 pulses WDO low after 1.6 s nominal; U5 clears permission and DRVOFF rises. WDO does not reset the ESP. |
| MCF lock, overcurrent, or blocked rotor | MCF enters latched Hi-Z; supervisor reports the fault and requires a fresh command. |
| Analog overspeed or 12 V tach-rail loss | Persistent hardware lock clears without ESP32 or MCF speed participation and requires a power cycle. |
| Physical cutoff opened | Remove 24 V power and coast. |
| Power restored | Remain off until a new user command and safe arm sequence. |
| Direction command while moving | Do not switch DIR until verified stopped. |

## Home integration

- First release: **Matter over Wi-Fi** using
  [rs-matter](https://github.com/project-chip/rs-matter) (pure-Rust, `no_std`, no-alloc, the
  official project-chip implementation, Matter 1.6) with
  [rs-matter-embassy](https://github.com/sysgrok/rs-matter-embassy) as the bare-metal Embassy
  integration, controlled from Apple Home. This replaces the original HAP/HomeKit plan: no
  maintained `no_std` HAP implementation exists, and Matter keeps the stack pure Rust while
  getting Google/Alexa/Home Assistant support for free.
- Device: Matter Fan device type (0x002B) with a hand-written FanControl (cluster 514)
  handler — on/off, `PercentSetting` (continuous speed; Apple Home renders 0–100% fan speed
  well), and `AirflowDirection` for reverse. Whether Apple Home surfaces AirflowDirection is
  unconfirmed; the proven fallback is a second small On/Off endpoint ("reverse mode") that
  flips direction. Expose actual RPM, stall, overtemperature, or controller fault only if
  straightforward.
- Commissioning: BLE (the `trouble` pure-Rust host over esp-radio) with the QR code printed
  to serial. rs-matter's test attestation credentials are fine for a personal device — Apple
  Home shows an "Uncertified Accessory" warning; add anyway. Use the flash-backed persistence
  store so a reboot doesn't require re-commissioning.
- A HomePod or Apple TV acts as the Matter hub for automations/remote access; iOS 18+ can
  commission and locally control without one (useful on the bench).
- No cloud, account, presets, or internet dependency. Network loss keeps the last local speed.
- Integration notes: rs-matter-embassy is a **git dependency** (its crates.io release is a
  placeholder); mirror its examples' `[patch.crates-io]` esp-hal pin table rather than
  fighting version skew. Prefer the `rustcrypto` feature over the vendored-mbedtls default to
  stay pure Rust. rs-matter has **no Matter OTA yet** — keep the UART/USB programming path
  (J6/J7) accessible on the installed unit.
- The ESP32-C6 leaves an 802.15.4 path open, and rs-matter-embassy supports Thread on C6, but
  Matter-over-Thread is not a first-release requirement.

## Qualification

Use the final motor and representative rotor inertia. Require 100 randomized-position starts
in both directions at 30, 35, and 40 RPM and at 23.3, 24.0, and 24.7 V. Require no tonal
motor/controller noise at the released sleep speed, an eight-hour 170 RPM thermal run, clean
windmilling restart, verified lock/current behavior, verified 180 RPM MCF clamp, calibrated
independent 200 RPM trip, and safe power/fault behavior. The actual minimum speed is released
only after every corresponding start and acoustic test passes. Full matrix:
[../testing/test-matrix.csv](../testing/test-matrix.csv).
