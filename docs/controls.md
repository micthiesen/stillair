# Motor-control contract

An implementation contract, not firmware. Application code lives in
[`firmware/`](../firmware/) (Rust, `no_std`, ESP32-C6); this doc defines what it must do.

## Selected hardware

- Motor: CubeMars GL100 KV10, 24 V, 20 pole pairs.
- Controller: custom 78 × 58 mm V1/V2 board around MCF8316DVRGFR (no TI evaluation module;
  swapped from the ULV variant 2026-07 — see [electrical.md](electrical.md) SCH-03).
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

Enter R/L/Ke manually as the primary values (nonzero MOTOR_RES/MOTOR_IND/MOTOR_BEMF_CONST
disables the corresponding MPET steps), and use MPET only as a cross-check **with the blades
mounted** — MPET's known failure modes (garbage Ke, missing Kp/Ki) occur on unloaded motors,
and the rotor is our load. Independently scope line-to-line BEMF while manually spinning.
Measured values replace the provisional registers before final EEPROM release.

**Headroom check during tuning**: at 170 RPM the BEMF is roughly 17 V against the 24 V bus —
the tightest margin in the system with flux weakening disabled. A 20% error in the Ke
convention (phase vs line) erases it, so pin the convention down against measured BEMF
before releasing the top speed.

**Low-speed feasibility (researched 2026-07)**: 35 RPM is 11.7 electrical Hz, and this
motor's ~300 mV/electrical-Hz BEMF constant is 7–70× the MCF's entire handoff-threshold menu
— closed-loop stability at the target minimum is comfortably in range (TI's "not ideal"
territory starts around two orders of magnitude less signal). Expect the tuning effort to go
into startup smoothness instead: align startup can kick the rotor backward; IPD startup
avoids that (see the IPD retry caveat in electrical.md). App notes: SLLA665 (handoff),
SLLU335 (gradual-startup recipes).

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
  (With AVS on, deceleration rate is governed by AVS rather than CL_DEC — fine for a fan.)
- Acceleration/deceleration: begin near 1.5 mechanical RPM/s.
- Configure standby mode (DEV_MODE = 0b), not sleep: the SPEED pin doubles as WAKE, and in
  sleep mode an idle-low SPEED pin kills I²C after SLEEP_ENTRY_TIME.
- Set every configurable fault mode to latched Hi-Z (0h) and OCP_MODE to latched —
  **except `EXT_WDT_FAULT_MODE`, whose encoding is inverted: 1b = latched Hi-Z** (0b is
  report-only). The only non-latchable paths are IPD start-attempt retry (electrical.md)
  and FET thermal shutdown, which auto-recovers by silicon design (see the failure table).
- **Speed input** (added 2026-07 review — previously unconfigured): `SPEED_MODE` = 01b (PWM
  duty on the SPEED pin), carrier in the 10–350 Hz band for 11-bit resolution (e.g.
  200 Hz), duty → speed mapping = duty × MAX_SPEED (35 RPM = 19.4%, 170 RPM = 94.4% of the
  180 RPM ceiling), and the I²C speed/DIR override bits left off so the pins are
  authoritative.
- **External watchdog** (previously unconfigured — without these the EXT_WD path silently
  doesn't exist): `EXT_WDT_EN` = 1, input mode = pin, `EXT_WDT_CONFIG` = 1000 ms,
  `EXT_WDT_FAULT_MODE` = 1b.
- `ALARM_PIN_EN` = 1 (ALARM → GPIO14). Note this moves report-only faults to ALARM
  exclusively; actionable faults still assert nFAULT.
- `AUTO_RETRY_TIMES` = 0 (no automatic retries anywhere).
- **Startup and resync** (previously unconfigured; the Starting state is unimplementable
  without them): `MTR_STARTUP` = IPD preferred (avoids align reverse-kick; accepts the
  documented start-attempt retry) with align as fallback; ISD/resync enables set for clean
  windmilling restart (DRV-06); `DIR_CHANGE_MODE` = full stop sequence.
- `FG_DIV` = 1h (20 pulses/rev; see electrical.md).
- EEPROM discipline: write only with the motor stopped and the device idle/faulted, VM ≥ 6 V
  throughout, ~750 ms per write (poll completion), 20k-cycle endurance so never write on a
  power-up path; an interrupted write is caught by CRC at next boot and EEP_FAULT_MODE = 0b
  holds Hi-Z. The register map is D-generation-specific — never reuse A1/C dumps.

## Electrical control contract

- Runtime commands: PWM speed (GPIO2), DIR (GPIO3), ARM_PULSE (GPIO18), and open-drain
  MCU_CLEAR_N (GPIO15). Firmware never drives DRVOFF directly.
- Feedback: FG (GPIO20), HALL_TACH sense (GPIO7), nFAULT (GPIO21), ALARM (GPIO14), 3.3 V
  PGOOD (GPIO22), watchdog WDO diagnostic (GPIO23), and optional temperature (GPIO6).
- Configuration and diagnostics: I²C to the MCF8316D (24-bit control-word protocol;
  bus-scan the target address at first bring-up).
- Convert FG using 20 pole pairs and FG_DIV = 1h (20 pulses/rev). Verify the conversion
  against an independent optical tachometer during commissioning (the optical tach is a
  bench instrument, never a state-machine input).
- The MCF commutates phases and limits current. The ESP32 never commutates phases.
- `nFAULT` is diagnostic, not an asynchronous clear input to the external permission latch.
  Configure MCF lock/fault responses to latched Hi-Z.
- `CLR_FLT` may be issued **only** in response to a fresh user command — never
  automatically (DRV-08 tests this).
- TI specifies DRVOFF should remain high for at least 10 seconds for safe operation
  (datasheet §7.5.1; verified verbatim). Enforce this after power-up and every
  permission-clearing event before re-arming.
- **Stopped criterion** (previously undefined): "verified stopped" = no FG edge for 5 s AND
  no Hall edge for 5 s after commanding zero. Constants live in firmware `config.rs`.

## Firmware safety architecture (2026-07 review — these rules are load-bearing; the
hardware guarantees silently depend on them)

- The 2 Hz watchdog heartbeat is **bit-banged from a supervisory task that attests
  control-loop liveness before each toggle** — never generated by a free-running hardware
  peripheral (LEDC/timer), which would keep feeding both watchdogs through a CPU hang.
- ARM_PULSE is a deliberate software-sequenced pulse (idle low, drive high ≥10 µs, return
  low) — never peripheral-driven. After a WDO pulse ends, any stray rising edge would
  re-arm the latch.
- Motor control + heartbeat run on a **higher-priority (interrupt) executor** than the
  Matter/Wi-Fi tasks: a hung network stack must degrade to the network-loss row (fan keeps
  its speed), and only a hung control task produces the watchdog row (fan stops).
- Boot never restores a running state: regardless of persisted Matter attributes, power-on
  is always IdleOff with speed zero (no StartUpOnOff semantics).
- **Permission lifecycle** (decided 2026-07; the dossier left it ambiguous): a normal stop
  *does* revoke permission via MCU_CLEAR_N, so every restart re-arms and pays the 10 s
  DRVOFF hold. This is a deliberate safety-over-UX choice — restarting the fan from Apple
  Home takes up to ~10 s. Reversal inherits the same sequence. If the UX proves
  unacceptable, changing it is a design decision for decisions.md, not an implementation
  shortcut.
- **Percent → RPM mapping** (previously undefined): PercentSetting 0 = Off; 1–100 maps
  linearly onto [released minimum, 170 RPM]; PercentCurrent reports the actual value;
  FanMode On without a percent write resumes the last non-zero setting. The released
  minimum is a config constant (it may rise after qualification), never hardcoded.
- **Hall/FG plausibility**: pre-arm asserts both channels quiet (consistent with stopped —
  it cannot detect sensor loss); the running check stops the fan if FG is nonzero while
  Hall stays quiet for N revolutions (N ≈ 5). This is the only backstop for the documented
  Hall-cable/magnet single-point failure.

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
| Physical cutoff opened | Remove 24 V power and coast. On any MIN_VM/undervoltage report while running, firmware zeroes speed and revokes permission — windmill BEMF back-feed through the body diodes can otherwise lift VM above the 18 V auto-recovery point and chatter the drive (bench-verify in DRV-09). |
| Power restored | Remain off until a new user command and safe arm sequence. |
| Direction command while moving | Do not switch DIR until verified stopped (per the stopped criterion). |
| MCF thermal warning or FET thermal shutdown | TSD_FET auto-recovers by silicon design and cannot be latched. Firmware treats any OTW/TSD report (nFAULT/ALARM) as a stop: zero speed, revoke permission, fresh command required. |
| I²C bus hang / stuck-low | Attempt 9-clock SCL recovery and MCF re-init; if a latched MCF fault is unclearable, remain stopped and surface a service condition (power cycle clears). |
| ESP reboot (brownout, internal WDT) while 24 V stays up | Boot to IdleOff, speed zero; never auto-resume. Windmilling rotor at reboot is handled by ISD/resync on the next commanded start. |

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
