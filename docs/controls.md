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

### Commissioning interface and build policy

Use the normal safety firmware for both bare-motor and ceiling-mounted loaded work. The host
`stillair` CLI is the commissioning harness: it keeps multi-step scripts in one session,
streams telemetry, checks and captures the configuration, and returns nonzero on a failed
step. A separate permissive firmware build would create a second safety behavior to validate
and is not the default plan.

The CLI exposes MPET as the bounded `mpet run` host operation. It starts only from
`IdleOff`, keeps the SPEED command at zero, arms through the normal permission latch, waits
for the MCF's four completion flags, prints the raw result registers, clears `MPET_CMD`, and
revokes permission. A fault takes the same revoke-and-abort path. Results remain in shadow;
MPET never commits EEPROM automatically. A 130-second device-side timeout also aborts and
faults if the host disappears. Run
`firmware/scripts/02-mpet-and-capture.txt` only with the loaded rotor. MPET remains a
cross-check; independent R/L/manual-spin BEMF measurements remain primary.

During ceiling commissioning, use PCB-01 J6 and a quality long USB cable to keep the laptop
and operator outside the rotor sweep; use an active extension if the passive link is
unreliable. USB supplies communication only because J6 VBUS does not power the board. Route
and strain-relieve the cable outside all moving geometry, and keep the physical low-voltage
cutoff reachable without entering the sweep.

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
  Safe boot first probes the expected target at zero SPEED, so a controller already in standby
  receives no wake command. If that read fails, recovery uses the firmware's
  `MCF_WAKE_HOLD_MS` interval, clears only DEV_MODE in the volatile shadow, verifies the bit,
  returns SPEED to zero, and clears the expected wake-under-DRVOFF start diagnostic. MCU_CLEAR_N
  is held low throughout, so this remains safe across an ESP-only reset where the external
  permission latch may retain its prior state. Recovery does not commit EEPROM; the reviewed
  golden image must still store DEV_MODE = 0b. The watchdog heartbeat starts in a boot-inhibit
  mode before the I2C address probe, because an already-configured MCF watchdog is live after
  wake; MCU_CLEAR_N remains low until SPEED is zero. Once the control task starts, heartbeat
  service again requires observed control-loop progress.
- Drive the MCF I2C bus through the dedicated GPIO0/1 software transport. Ordinary bits run
  near 100 kHz, followed by an explicit `MCF_I2C_INTERBYTE_US` (110 us) SCL-low hold after
  every byte ACK or NACK. TI requires at least 100 us between bytes, which the ESP hardware
  packet engine cannot insert. Slowing that engine to 5 kHz and 2.5 kHz still produced
  intermittent NACKs on the real board because a slow bit period is not the specified pause.
  The transport permits the MCF's documented clock stretching up to its 4.66 ms internal
  timeout. Protocol CRC and nine-clock bus recovery remain enabled.
- Set every configurable fault mode to latched Hi-Z (0h) and OCP_MODE to latched —
  **except `EXT_WDT_FAULT_MODE`, whose encoding is inverted: 1b = latched Hi-Z** (0b is
  report-only). The only non-latchable paths are IPD start-attempt retry (electrical.md)
  and FET thermal shutdown, which auto-recovers by silicon design (see the failure table).
- **Speed input** (added 2026-07 review — previously unconfigured): `SPEED_MODE` = 01b (PWM
  duty on the SPEED pin) **and `SPEED_RANGE_SEL` = 1h** (the 10–325 Hz low band; the
  register defaults to the 325 Hz–95 kHz band, in which a 200 Hz carrier would silently be
  out of range). Carrier: 200 Hz (11-bit resolution holds for 10–350 Hz per the resolution
  table). Duty → speed mapping = duty × MAX_SPEED (35 RPM = 19.4%, 170 RPM = 94.4% of the
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
  throughout, then write `0x8A500000` to `ALGO_CTRL1`, wait at least 750 ms, and poll until
  that register self-clears. Firmware commits one changed shadow block once, then verifies
  the entire image by read-back. Endurance is 20k cycles, so never write on a
  power-up path; an interrupted write is caught by CRC at next boot and EEP_FAULT_MODE = 0b
  holds Hi-Z. The register map is D-generation-specific — never reuse A1/C dumps.

## Electrical control contract

- Runtime commands: PWM speed (GPIO2), DIR (GPIO3), ARM_PULSE (GPIO18), and open-drain
  MCU_CLEAR_N (GPIO15). Firmware never drives DRVOFF directly.
- Feedback: FG (GPIO20), HALL_TACH sense (GPIO7), nFAULT (GPIO21), ALARM (GPIO14), 3.3 V
  PGOOD (GPIO22), watchdog WDO diagnostic (GPIO23), and optional temperature (GPIO6).
- Configuration and diagnostics: I²C to the MCF8316D (24-bit control-word protocol;
  bus-scan the target address at first bring-up).
- Convert FG using 20 pole pairs and FG_DIV = 1h (20 pulses/rev). Cross-check reported FG
  against the independent PCB-02 Hall channel during motor-driven commissioning. During an
  external-drive proof, use PCB-02 Hall telemetry or the drive's own speed readout. No
  separate optical tachometer is assumed.
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

## Derived firmware requirements (2026-07-27, from implementing the above)

Decisions the contract implied but did not state. Constants live in `firmware/core/src/config.rs`
and each is covered by a host test in `firmware/core/src/state.rs`.

- **Start supervision**: if the rotor produces no FG edge within `START_TIMEOUT_MS` (15 s) of
  the ramp beginning, the start failed — permission never took, the rotor is jammed, or the
  analog lock is latched — and the supervisor faults rather than commanding into a dead
  drive. Not a TI requirement; without it a failed arm looks identical to a very slow start
  forever.
- **A windmilling rotor delays a start, it does not race it.** The pre-arm quiet rule and the
  ISD/resync windmill-restart configuration read as being in tension; they are not. Firmware
  waits for both channels to go quiet before arming, so a coasting rotor simply postpones the
  start; ISD/resync covers the residual case where the rotor is still creeping below tach
  resolution when the MCF is enabled. If the rotor never goes quiet within
  `START_QUIET_TIMEOUT_MS` (120 s), that is a service condition, not a wait.
- **Resuming mid-stop does not re-arm.** Turning the fan back on while it is ramping down is
  a speed change, not a restart: permission has not been revoked yet, so the supervisor
  returns to Running without the 10 s cost. A *reversal* is explicitly excluded — it must
  reach a verified stop, because its whole purpose is to flip DIR from standstill.
- **Speed resolution**: the SPEED-pin duty is written as the raw 11-bit value, not as whole
  percent. Percent steps are 1.8 RPM against a range that starts at 35 RPM — too coarse to
  tune. Duty is also clamped one below full scale, since an 11-bit register holds 0..=2047
  and writing 2048 would wrap to zero (the fan stopping at maximum command).
- **The watchdog heartbeat is conditional, not merely bit-banged.** The control loop
  increments a beat counter on every completed poll and the heartbeat task refuses to toggle
  unless it advanced. A bit-banged-but-unconditional toggle would still feed the watchdog
  through a hung control loop, which is the exact failure the watchdog exists to catch. This
  gating lives in the app crate (`firmware/app/src/main.rs`) and is therefore **not** covered
  by a host test — unlike every other item in this section, it is verified only by CTL-02.

### Hardware-derived gap

- **No golden image has been captured yet**, so the boot-time configuration gate below
  reports `unverified` rather than `verified`. The mechanism is real and the gate holds; what
  is missing is a device to capture from. See "Stored-configuration verification" below.

### MCF8316D I²C wire format (verified 2026-07-27 against primary sources)

Derived from datasheet **SLLSFX9A** §7.6.2 (Tables 7-10 through 7-14) and app note
**SLLA662** §2. Encoded in `firmware/core/src/mcf8316.rs`, with tests reproducing TI's own
example packets byte for byte.

- Every transaction opens by *writing* a 24-bit control word, so the I²C direction bit in
  the first byte is always 0 — even for a register read, which then issues a repeated start.
- Control word: `OP_R/W` CW23 (read = 1, write = 0), `CRC_EN` CW22, `DLEN` CW21:20
  (00 = 16-bit, 01 = 32-bit, 10 = 64-bit), `MEM_SEC` CW19:16, `MEM_PAGE` CW15:12, `MEM_ADDR`
  CW11:0. All externally addressable memory (EEPROM and RAM) is `MEM_SEC` = `MEM_PAGE` = 0h;
  every other value is reserved.
- **Byte order is mixed and is the easiest thing here to get backwards**: the control word
  goes out most-significant byte first, the data bytes least-significant byte first.
- CRC-8, when enabled: CCITT polynomial 0x07, init 0xFF, MSB-first per byte. A write covers
  `{target,0} ‖ control word ‖ data`; a read also includes `{target,1}` before the data.
  Verification vector: input byte 0x12 → 0x8D.
- Registers the supervisor uses: `GATE_DRIVER_FAULT_STATUS` 0xE0, `CONTROLLER_FAULT_STATUS`
  0xE2, `ALGO_STATUS` 0xE4, `ALGO_CTRL1` 0xEA. All 32-bit.
- `CLR_FLT` is `ALGO_CTRL1` bit 29, written together with `CLR_FLT_RETRY_COUNT` bit 28 —
  value `0x30000000`. Both are write-only and self-clearing, so read-back proves nothing,
  and a latched fault can take **up to 200 ms** to clear (the 10 s safe-boot hold covers it).
- Allow at least 100 µs between bytes, and expect clock stretching (SLLA662 §3.1).
- Default target ID is 0x01, changeable only via EEPROM plus a power cycle — bus-scan at
  first bring-up rather than trusting it.
- Each raised SCL edge permits clock stretching through the MCF's documented 4.66 ms internal
  timeout. A line still held low after 5 ms fails the transfer. Recovery sends nine SCL pulses
  and STOP before a follow-up status read; sustained failures still become `BusUnreachable`
  and revoke permission.

### Stored-configuration verification (2026-07-27)

The last clause of the safe-boot step ("stored configuration verified") is enforced by
`firmware/core/src/mcf_config.rs`, and it is why `SafeBoot` is a state rather than a delay.

- **The image is a list of whole 32-bit register values, not named fields.** Bit-level field
  layouts for the configuration block are deliberately not encoded in firmware — a wrong bit
  position writes garbage into a motor controller, and the tables above are commissioning
  seeds rather than transcribed silicon. A golden image sidesteps the question: capture the
  whole EEPROM block off a device that has been tuned and qualified, commit those values, and
  read-back-verify them at every boot forever after. A `mask` field covers the in-between
  case, a field derived at the bench inside a register still being explored.
- **Verified at boot, never written at boot.** The EEPROM discipline above (motor stopped,
  device idle or faulted, 20k-cycle endurance) makes a power-up write path unacceptable, and
  whether a configuration write lands in a volatile shadow or burns an EEPROM cycle is a
  bench question, not an assumption. `config apply` therefore exists as a deliberate console
  operation, gated on the fan being stopped; boot only reads. It writes changed shadow
  registers, performs one explicit `ALGO_CTRL1` commit, waits the required 750 ms, polls for
  the self-clearing zero with a two-second bound, and only then verifies by read-back. A
  service interlock first forces and confirms a stopped supervisor state, then rejects or
  drains concurrent normal commands until the write finishes, so a stale telemetry snapshot
  cannot race a Matter start.
- **The device's own verdict outranks ours.** The check reads `CONTROLLER_FAULT_STATUS` first
  and fails on `EEPROM_ERR` / `EEPROM_WRITE_LOCK` / `EEPROM_READ_LOCK`. The MCF CRCs its
  EEPROM at boot; if that failed, no amount of read-back agreement from us redeems the block.
- **Four verdicts, not a boolean.** `pending` holds `SafeBoot` (with a
  `CONFIG_CHECK_GRACE_MS` timeout, because a supervisor parked in `SafeBoot` reporting
  nothing is indistinguishable from a board that will not boot); `failed` is a fault, before
  or after boot; `verified` proceeds. `unverified` — the device is healthy but **no image has
  been captured yet** — also proceeds, because the harness has to be usable in order to
  capture one, and it rides in every telemetry frame and CSV row so a capture taken against
  an unverified configuration is identifiable as one six months later.
- **A configuration write invalidates the verdict.** Any successful `reg write` into
  `0x080..=0x0AE` re-runs the check automatically rather than leaving a stale `verified`
  standing. Raw writes change shadow only and deliberately do not spend an EEPROM cycle.
  During bench derivation against an empty image this is harmless; once an image exists,
  deliberately diverging from it stops the fan, which is the point. Persistence happens only
  through the reviewed `config apply` path.
- **Capturing the image is a bench step, not a code change**:
  `stillair --port … config capture` prints a paste-ready table. The host knows how many
  registers to expect (it shares `reg::configuration()` with the firmware), so a dump cut
  short by a bus error fails rather than producing a silently partial image.

### Matter cluster mapping (2026-07-27)

`firmware/core/src/matter.rs` holds the FanControl (cluster 514) mapping — `FanMode`,
`PercentSetting`, `AirflowDirection` — as plain host-tested Rust with **no rs-matter
dependency**, for the same reason the state machine is sans-I/O: it is the part that can be
wrong, and being wrong means the fan runs at a speed nobody asked for. The rs-matter handler
in `app/` is transport around it.

- The percentage arithmetic is `speed::percent_to_rpm`, not a second copy, so the Matter
  slider and the SPEED-pin duty cannot disagree about what "60%" means.
- `FanMode` On and Auto carry no speed and resume the last non-zero setting; Low/Medium/High
  are 33/66/100%, and the reported mode's bucket boundaries sit midway between them so a mode
  a controller writes reports back as itself.
- `pct <0-100>` on the console drives this same path, so a tuning script exercises the
  mapping Apple Home will use rather than only the RPM path that bypasses it.

### Matter implementation notes (2026-07-27, from building it)

The stack runs on the ESP32-C6 and commissions over BLE; `firmware/app/src/matter.rs` is the
endpoint, `firmware/core/src/matter.rs` the mapping it delegates every decision to.

- **rs-matter generates the FanControl cluster from the CSA's own normative IDL** (attribute
  IDs, enums, TLV, the `ClusterHandler` trait) but ships no *handler* for it, because a handler
  is device logic. So the hand-written handler the dossier planned was required — but only the
  logic, not the encoding, which is a far smaller and safer job than it sounded.
- **Advertised features are only what the fan is**: `AIRFLOW_DIRECTION` and nothing else.
  `MULTI_SPEED` would add a second, coarser speed axis fighting the percentage one; `ROCKING`
  and `WIND` are mechanisms this fan does not have; `STEP` is a stepped-remote idiom.
  Advertising a feature that cannot be honoured is how a controller ends up sending commands
  that silently do nothing.
- **Every reported attribute is derived from supervisor telemetry, never cached in the
  handler.** The first version kept a Matter-private copy of the requested state, on the
  reasoning that `PercentSetting` is the controller's rather than the fan's. That is true, but
  the controller is not its only source: the serial tuning console writes the same commands
  into the same channel, and a fault clears the request outright. A cache has no path back
  from either, so it would sit reporting "High" at a fan that faulted an hour ago, and
  re-reporting would only re-serve the stale value. Deriving makes the divergence
  unrepresentable. The derivation lives in `stillair-core` (`matter::reported`) so it is
  host-tested — the app crate has no tests, which is precisely how the cache slipped through.
- **`PercentSetting` is what was asked for; `PercentCurrent` follows reported speed, in
  every state.** A fan ramping down after an Off is still moving air for a minute or more, so
  reporting zero the instant the command lands would claim it had stopped while it was plainly
  still turning. Direction reports the *requested* value, because the applied one lags a
  reversal by the whole stop-verify-flip-restart sequence and a toggle that springs back for a
  minute reads as a device that ignored you. `Smart` (deprecated) is accepted as Auto.
- **Subscribers are refreshed from the handler's `run` hook**, which `rs-matter` drives for
  every handler in the chain, at a 2 s cadence, and it compares the *whole* reported snapshot
  rather than only the measured speed. Only a write bumps a cluster's data version, so without
  this a controller would show the speed it asked for and never the speed reached — and
  watching only what Matter itself wrote would miss every console-issued command and every
  fault.
- **The bridge is non-blocking in both directions**: writes `try_send` into the same bounded
  channel the tuning console uses, reads come from the telemetry snapshot. A wedged Matter task
  cannot block the supervisor, and a wedged supervisor cannot block Matter — which is the
  network-loss row of the failure table holding by construction rather than by care.
- **Persistence is flash-backed** (`SeqMapKvBlobStore` into the first NVS partition, found by
  reading the partition table rather than by a hardcoded offset), so a power cut does not demand
  re-commissioning from Apple Home.
- **No Identify cluster.** The Fan device type nominally mandates it and a ceiling fan has
  nothing to flash; rs-matter's own examples omit it too. Revisit if a controller objects.
- **A Matter startup failure degrades to local control rather than panicking.** A panic takes
  the whole binary down, control loop included, and stops a fan that was running perfectly
  well — the opposite of the network-loss row. Losing Matter must lose only Matter.
- Test attestation credentials, so Apple Home shows "Uncertified Accessory" and adds it anyway.
- **Commission with the phone joined to a 2.4 GHz SSID.** Apple Home has no network picker: it
  hands the device whatever network the phone is on, and the C6 has no 5 GHz radio. Handing it
  a 5 GHz-only SSID fails with `NoAccessPointFound` / `NoNetworkInterface` and surfaces in the
  app only as "Pairing Failed" — the device log is the only place the real cause appears. The
  phone can return to 5 GHz afterwards; the fan keeps its own credentials.
- Apple writes `DefaultOTAProviders` (OTA Requestor, cluster 0x2A) during setup and is content
  with `UnsupportedCluster`, since rs-matter has no Matter OTA yet.
- Measured on the C6 at first boot: Matter stack 78 KB, bump allocator 13.3 KB of 20 KB used,
  100 KB heap, 2.19 MB image (53% of the partition). `BUMP_SIZE` is the number to raise if the
  stack panics during initialisation.
- **Coexistence scanning is unreliable.** Two consecutive commissioning attempts scanned 4 and
  then 1 network. If a join ever fails with `NoAccessPointFound` against an SSID that
  definitely exists on 2.4 GHz, the lever is non-concurrent commissioning — `stack.run()`
  instead of `run_coex()`, which drops BLE before joining Wi-Fi. It costs a larger `BUMP_SIZE`
  (bigger futures) and reportedly breaks Alexa, so it stays unused until something needs it.

### Building the Matter firmware (2026-07-27)

- **Our dependency versions already match rs-matter-embassy's own esp example exactly** —
  esp-hal ~1.1, esp-rtos 0.3, esp-radio 0.18, esp-alloc 0.10, esp-println 0.17,
  esp-backtrace 0.19, esp-bootloader-esp-idf 0.5, embassy-executor 0.10, embassy-time 0.5,
  embassy-sync 0.8. No version skew to fight; the cost is the `[patch.crates-io]` pin table
  (see CLAUDE.md > "Firmware conventions"), which moves every esp-\* crate to an unreleased
  esp-hal git rev.
- Adopting that rev needed exactly one change in our own code: `usb_serial_jtag` moved under
  `esp_hal::usb`.
- **`esp-alloc`'s `compat` feature is mandatory**, not optional: esp-radio's BLE half is a C
  blob that will not link without C-compatible `malloc`/`free`. It is a default feature, so a
  `default-features = false` line silently removes it and the failure appears only at link.
- The examples' `.cargo/config.toml` sets `build-std`, which is nightly-only. It is **not
  required** — the whole tree builds on stable without it.
- rs-matter arrives via `rs-matter-stack` from crates.io, not as a git dependency of its own.
- The shape to copy from `light_wifi.rs`: a statically allocated `EmbassyWifiMatterStack`,
  `EspWifiDriver::new(WIFI, BT)`, `stack.run_coex(...)` with an `EmptyHandler.chain(EpClMatcher…)`
  per cluster plus a `DescHandler` per endpoint, and `TrngSource` feeding a reseeding CSPRNG.

### Fault reporting and bus health (2026-07-27)

- **A decoded status outranks the pins.** `nFAULT` and `ALARM` each say only "something"; the
  fault-status registers (0xE0/0xE2) say what. Both are read every 200 ms and reduced to one
  reportable condition. Supply faults deliberately outrank the locks they cause — an
  undervoltage also trips a lock, and naming the lock sends the owner to the wrong subsystem.
- **`SafeBoot` suppresses MCF fault sources and re-checks them once at its exit.** Evaluating
  them throughout the hold makes a fault-clear impossible to land: CLR_FLT takes up to 200 ms,
  so the fan would re-fault four control ticks after the user's command, silently consuming
  it. Suppressing for the hold gives the clear the full ten seconds; a fault that survives
  that is reported once. This also absorbs the MCF's own power-up transients.
- **Losing sight of the drive is a fault, and there are two ways to lose it.** Five
  consecutive failed reads is one. The other is silence: a reader that has stopped running
  reports no failures at all, so the counter never moves and total starvation would look
  exactly like "nothing new this tick". `STATUS_STALE_TIMEOUT_MS` catches that, but only
  while armed — before arming there is nothing being commanded to protect.
- **CRC is enabled on every transaction and verified on every read.** A mismatch is a
  reported failure, never a silent retry: it means either the bus is corrupting data or our
  framing is wrong, and neither may reach the state machine as truth.

### Ready-made commissioning sequences

The numbered files in [`firmware/scripts/`](../firmware/scripts/) are the executable test
flow. They cover board-only diagnostics, loaded MPET plus capture, unloaded low-speed smoke,
the loaded speed ladder, reversal, and an observed run. `wait speed` requires three
consecutive FG samples within tolerance, so merely crossing a setpoint during a ramp cannot
pass a step. The same files run against `--sim` to validate protocol and sequencing, but a
simulator pass says nothing about motor constants or physical behavior.

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
6. **Reverse**: ramp to zero, verify the stopped criterion (no FG edge and no Hall edge for
   5 seconds), coast, change DIR, then restart.
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
  handler — on/off, `PercentSetting` (continuous speed), and `AirflowDirection` for reverse.
  **Confirmed against Apple Home on real hardware (2026-07-27)**: it renders a continuous
  0–100% speed slider, an on/off control, **and a reverse button** — so `AirflowDirection` is
  surfaced and the second On/Off "reverse mode" endpoint that was held as a fallback is not
  needed. A slider left at 61% arrived as a 116.8 RPM target, matching the documented linear
  map onto [35, 170] exactly. Expose actual RPM, stall, overtemperature, or controller fault
  only if straightforward.
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
