# State

Fast-moving work state and chosen next step. This records the work, not machine state or
uncommitted changes. Durable findings live in the linked docs.

Last updated: **2026-07-27** (13-agent review + adversarial fix-verification pass both
integrated; anchors re-selected to Simpson Titen HD after owner cost research; Next
redirected to the firmware/harness program at owner request).

## Now

- **The full-design review is done and its fixes are in.** Thirteen reviewers (per-block
  datasheet verification, end-to-end path traces, mount/rotor) found four circuit-level
  blockers — all now fixed in [electrical.md](electrical.md): the U6 power-up preset race
  (found independently by four agents; fixed with a delayed-`/PRE` RC + Schmitt), the
  reversed reverse-polarity MOSFET, the LM2907 timing cap on the wrong node, and two
  missing GPIO routes (MCU_CLEAR_N → GPIO15, HALL sense → GPIO7). The overspeed claim was
  re-scoped to a two-tier guarantee (mechanical basis raised to 270 RPM), and the firmware
  contract gained the load-bearing safety-architecture rules (bit-banged heartbeat,
  executor priority, permission lifecycle with the 10 s restart cost, percent mapping) in
  [controls.md](controls.md). Seven new test rows landed in `testing/test-matrix.csv`.
- **What the review validated**: every MCF register hex is a correct D-generation encoding;
  the analog trip arithmetic is right to three digits; the Z-stack and all mount hole
  patterns are mutually consistent; the 3.3 V budget has 35% headroom; connector mating
  pairs verified. The dossier's architecture is sound — its errors were concentrated in
  wiring details and unstated firmware assumptions.
- **MP-100 is ordered — the first custom part committed to metal (2026-07-27).** JLCCNC,
  SUS304, brushed, qty 1, ~$130. Rev A STEP + PDF are in [`cad/`](../cad/) exactly as sent.
  Getting there closed three paper decisions and one real defect: ENC tab clocking locked at
  45/105/165/225/285/345° with the clamshell split on the 135°–315° axis; the mid-plate cable
  slot **deleted** in favour of a 15° rim entry + P-clip strain relief once the supply was
  confirmed as a surface run and plate rotation as free; SP-100's anti-rotation dimensioned as
  a keyed double-D flange rather than wrench flats; and all ten taps standardised to M3 to
  satisfy JLCCNC's blind-tap rule. **On arrival: check flatness with a straightedge before
  drilling the ceiling** — JLC holds no form tolerances.
- **Mount work can start** (see [build.md](build.md) > "Mount build-first plan"): mockup
  first, then ST-100/SP-100/KD-100/BL-100/LS-100 are fully spec'd and motor-independent; the
  adapter filament qualification is the longest non-motor-gated path.
- **Control plane locked**: Matter over Wi-Fi (rs-matter). Orders in; GL100 + parts en
  route; CubeMars bearing email sent 2026-07-27 (Gate 01 awaiting reply).
- **Owner direction (2026-07-27)**: only ESP32-C6 dev boards are on hand, so the near-term
  program is all of the firmware plus a motor-tuning/telemetry harness, built out *before*
  the V1 board exists and driven by Claude Code once it does. Phases: **A** core split
  (done) → **B** full state machine → **C** tuning harness → **D** rs-matter → bring-up.
- **Phases A and B landed (2026-07-27).** `firmware/` is now two crates: `stillair-core`
  (`no_std`, zero esp-\* deps, sans-I/O — takes an injected `Millis` plus sampled `Inputs`,
  returns `Action`s) and `firmware/app` (the C6 binary, its own workspace, its own target).
  The supervisor state machine is real, not a stub: all seven states, the permission
  lifecycle, the stopped criterion, FG/Hall plausibility, and the ramp, under 51 host tests
  that run on a laptop in milliseconds — including the 10 s and 120 s holds. CI grew a
  `core` job (fmt + clippy + **tests**) alongside `app` (fmt + clippy + release build).
  Console framing decided: everything on USB-serial-JTAG, protocol lines are `@`-prefixed
  newline-delimited JSON, one mutexed writer so logs cannot interleave mid-line.
- **Phase B**: the MCF8316D I²C wire format (derived from datasheet SLLSFX9A §7.6.2 and app
  note SLLA662, with tests pinned byte-for-byte to TI's published example packets), a real
  I²C driver with CRC verified on every read, decoded fault-status reporting from 0xE0/0xE2,
  and the interrupt-executor split — control loop, heartbeat, and tach counters at
  Priority3, diagnostics and future Matter tasks below them. **85 host tests.**
- **Phase C landed (2026-07-27): the tuning harness.** A console protocol in core
  (plain-text requests, `@`-prefixed JSON replies), a device console task, and
  `firmware/cli` building `stillair` — which drives either a board (`--port`) or an
  in-process simulator (`--sim`) running the real `Supervisor` in simulated time. All 24
  EEPROM config registers and 38 RAM registers are addressable by name. **126 tests.**
  Usage and the `script` caveat are in [CLAUDE.md](../CLAUDE.md) > "Driving the fan".
- **The phase C review found a critical one**: `esp_println` takes a lock that clears the
  *global* interrupt-enable bit and then busy-waits when the USB FIFO is full — so streaming
  telemetry to a host that stopped reading could stall the Priority3 control loop and
  heartbeat, i.e. exactly invert the contract the executor split exists to enforce. All
  output (protocol *and* logs) now goes through one bounded queue drained by a single async
  writer; when the host stops reading, lines are dropped, counted, and the count is carried
  in every telemetry frame so a capture with a gap is identifiable as one.
- **The stored-configuration gate is real now (2026-07-27).** `SafeBoot` no longer exits
  until the I²C task has produced a verdict on the MCF's stored configuration, and a `failed`
  verdict is a fault before or after boot. The image is a captured golden block of whole
  32-bit register values rather than invented bit fields — `stillair … config capture` prints
  it — and until one is captured the verdict is honestly `unverified`, which rides in every
  telemetry frame and CSV row so a capture taken against an unqualified device says so. Any
  `reg write` into the EEPROM block re-checks automatically. Details in
  [controls.md](controls.md) > "Stored-configuration verification"; new rows CTL-08/09/10.
- **The Matter FanControl mapping landed in `stillair-core`** (`matter.rs`, no rs-matter
  dependency): `FanMode`, `PercentSetting`, `AirflowDirection` → supervisor commands, reusing
  `speed::percent_to_rpm` rather than a second copy of the arithmetic. `pct <0-100>` on the
  console drives the same path Apple Home will. **162 tests.**
- **The firmware now runs on a real ESP32-C6 dev board (2026-07-27).** Flashed, booted, and
  driven over USB serial JTAG with the CLI. It found a defect the simulator could not: the
  I²C status-read warning fired every 200 ms against an absent MCF, flooding the bounded
  output queue and evicting telemetry frames (`dropped` climbed 16 → 62 in fifteen seconds) —
  exactly when the record matters most. Status logging is now transition-only; re-flashed and
  confirmed `dropped: 0`. **The bare dev board cannot leave `SafeBoot`** (GPIO22 PGOOD floats
  low, and floating-means-bad is the correct fail-safe reading); jumpering is documented in
  [CLAUDE.md](../CLAUDE.md).
- **Reviewers found real bugs in every phase, all fixed**: `duty_for` returned full scale
  at the MCF ceiling (2048 into an 11-bit register aliases to zero — maximum command would
  have *stopped* the fan), `whole_rpm()` overflowed on the saturated tach value the crate
  itself manufactures, and `set_released_min` could panic the control loop via inverted
  `clamp` bounds. Four test gaps closed (ALARM path, bare-`On` resume, floor-raising, and
  the arm-settle branch that a 100 ms bench tick stepped straight over).

## Next

**Finish the rs-matter integration in `app/`.** The mapping half is done and tested in
`stillair-core`; what remains is the transport: `EmbassyWifiMatterStack` on the **thread-mode**
executor (never on `control`), a FanControl handler chained onto the endpoint, BLE
commissioning with the QR to the console, and `SeqMapKvBlobStore` persistence so a reboot does
not re-commission. See "Phase D findings" below for the pin table and the two blockers already
cleared.

Then, once a real MCF8316D exists: **capture the golden image.** The gate is built and holds;
`stillair --port … config capture` prints the table, and until it is filled in every frame
honestly reports `config: unverified`.

## Phase D findings (2026-07-27, from a build spike against the real crates)

- **Our dependency versions already match rs-matter-embassy's own esp example exactly** —
  esp-hal ~1.1, esp-rtos 0.3, esp-radio 0.18, esp-alloc 0.10, esp-println 0.17,
  esp-backtrace 0.19, esp-bootloader-esp-idf 0.5, embassy-executor 0.10, embassy-time 0.5,
  embassy-sync 0.8. No version skew to fight.
- **But it pins every esp-\* crate to an unreleased esp-hal git rev**
  (`esp-rs/esp-hal` rev `10e48dd74837bae4be663a7d1825d12875363727`) via `[patch.crates-io]`.
  Adopting Matter means adopting that rev for the whole app crate, which is the real cost.
- **`mbedtls` is not merely undesirable, it does not build here.** `mbedtls-rs-sys` drives
  CMake at a riscv32-esp-elf C cross-compiler; Apple clang cannot target riscv32 and the
  build dies in `CMakeTestCCompiler`. `rustcrypto` is rs-matter-embassy's *default* and the
  examples opt out of it — so the pure-Rust preference in CLAUDE.md is now also the only
  option that compiles without an ESP-IDF C toolchain.
- The repo moved: `sysgrok/rs-matter-embassy` 301-redirects to **`ivmarkov/rs-matter-embassy`**.
- The examples' `.cargo/config.toml` sets `build-std`, which is nightly-only; the build got
  well past dependency compilation on **stable** regardless, so it appears not to be required.
- **The C6 Wi-Fi example builds clean on stable with `rustcrypto`** (52 s once deps are
  cached), so the toolchain question is closed and iteration is cheap.
- rs-matter arrives via `rs-matter-stack` 0.1 from crates.io (not a git dep of its own).
- **rs-matter 0.2.0 has no FanControl cluster and no Fan device type.** `src/dm/clusters/app/`
  covers on_off, level_control, color_control, chime, camera and webrtc — nothing at 0x0202,
  and `devices.rs` has no `DEV_TYPE_FAN`. `rs-matter-codegen` generates clusters from the
  Matter IDL but is explicitly an internal build-time dependency, not a user-facing generator.
  So the hand-written FanControl handler the dossier planned is **required**, not a
  preference. `on_off.rs` is the template to follow: a `…Hooks` trait for device logic behind
  a generated cluster shell.
- Shape to copy from `light_wifi.rs`: statically allocated `EmbassyWifiMatterStack<BUMP_SIZE,
  ()>` (~35–50 KB, `BUMP_SIZE` 20000, heap 100 KB), `EspWifiDriver::new(WIFI, BT)`,
  `stack.run_coex(...)` with an `EmptyHandler.chain(EpClMatcher…)` per cluster plus a
  `DescHandler` per endpoint, and `TrngSource` feeding a reseeding CSPRNG.

## Candidates Not Chosen

- **Phase C, the tuning + telemetry harness** — device-side line console (`reg read/write`,
  `run <rpm>`, `dir`, `state`, `stream on <hz>` → CSV telemetry), a host CLI sharing
  `stillair-core` for the protocol and register encoding, and a simulator implementing the
  same hardware boundary so the loop runs with no board. One CLI subcommand per
  `testing/test-matrix.csv` row with machine-readable pass/fail is the Claude-Code-friendly
  part. Waits on phase B: the console's most valuable command is register read/write, which
  needs the control word. **Caveat to carry forward**: a simulator validates the harness,
  never the sensorless tuning.
- **rs-matter devkit spike** (dev boards on hand; answers the AirflowDirection question).
  The one candidate worth running genuinely in parallel — shares nothing with the core, and
  it is the biggest external unknown (git deps, patch pinning, BLE commissioning, flash
  persistence).
- **Capture the V1 controller schematic in KiCad** (`pcb/`), following
  [electrical.md](electrical.md) SCH-01–SCH-07 as amended by the review (delayed `/PRE`,
  Schmitt buffers, corrected FET orientation, LM2907 fixes, GPIO7/15, GPIO8/9 pull-ups,
  22 µF module bulk, NTC/VBUS circuits). Order config and footprint sourcing in
  `pcb/README.md`. Was the previous Next; still on the critical path to real hardware and
  fully parallel with all firmware work.
- **Mount mockup + first metal** (MDF/printed plate-standoff-carrier mockup; order plate/
  rod/17-4PH stock; fab ST-100/SP-100/KD-100). Owner-driven, fully parallel.
- **Motor release checks** when the GL100 arrives (now includes the pilot-register
  rotating-surface confirmation and the axial-length tolerance measurement).
- **Blade adapter filament qualification** — startable as soon as PPA-CF is ordered;
  longest non-motor-gated path.

- **The fix-verification pass caught two defective fixes** before capture: the
  reverse-polarity FET "correction" had inverted a correct circuit (reverted, with a
  do-not-fix-again note in electrical.md SCH-01) and the delayed-`/PRE` RC values couldn't
  meet their own delay claim (resized 100 kΩ/10 µF with corner math; TPS7A16 DELAY cut to
  10 nF; glitch-immunity claim rewritten honestly). Plus: `SPEED_RANGE_SEL` = 1h added,
  BAT54H qty 6, TACH-01B quantified. Lesson: review fixes need the same adversarial
  verification as the original design.
- **Anchors re-selected (owner-driven)**: Simpson Titen HD 3/8 × 3 primaries + 3/8 × 4
  tether (~$120 total vs ~$2000 Hilti retail), full ESR-2713 basis in
  [install.md](install.md); owner's 1/4 × 1-7/8 proposal rejected on embedment arithmetic;
  tether load re-based from the dossier's 4.5 kN default to the calculated dynamic peak.

## Learned Recently

- **Review round-up (2026-07-27)**: all findings, fixes, and residual-risk decisions →
  [electrical.md](electrical.md) (SCH-01/02/03/04/05/06, PCB-02, two-tier trip),
  [controls.md](controls.md) (config completeness, firmware safety architecture, new
  failure rows), [parts.md](parts.md) (SP-100 flats, M6×20, magnet-cap rewording, CW-100
  trim, fabrication defaults, new gates), [build.md](build.md) (mount build-first plan),
  `testing/test-matrix.csv` (PCB-03C/D/E, TACH-04/05, CTL-04, DRV-09).
- **A 1 pulse/rev tach cannot guarantee tight overspeed overshoot** against fast ramps; the
  supply-power bound is the real backstop → electrical.md two-tier claim, 270 RPM basis.
- **The dossier's failure mode is wiring/config detail, not architecture** — worth
  remembering for any remaining unreviewed corners.
