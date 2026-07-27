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
- **Mount work can start** (see [build.md](build.md) > "Mount build-first plan"): mockup
  first, then ST-100/SP-100/KD-100/BL-100/LS-100 are fully spec'd and motor-independent;
  MP-100 is now released too (2026-07-27: ENC tab clocking locked at 45/105/165/225/285/345°,
  clamshell split on the 135°–315° axis, and the mid-plate cable slot deleted in favour of a
  15° rim entry + P-clip strain relief, after the supply was confirmed as a surface run and
  plate rotation as free); the adapter filament
  qualification is the longest non-motor-gated path.
- **Control plane locked**: Matter over Wi-Fi (rs-matter). Orders in; GL100 + parts en
  route; CubeMars bearing email sent 2026-07-27 (Gate 01 awaiting reply).
- **Owner direction (2026-07-27)**: only ESP32-C6 dev boards are on hand, so the near-term
  program is all of the firmware plus a motor-tuning/telemetry harness, built out *before*
  the V1 board exists and driven by Claude Code once it does. Phases: **A** core split
  (done) → **B** full state machine → **C** tuning harness → **D** rs-matter → bring-up.
- **Phase A landed (2026-07-27).** `firmware/` is now two crates: `stillair-core`
  (`no_std`, zero esp-\* deps, sans-I/O — takes an injected `Millis` plus sampled `Inputs`,
  returns `Action`s) and `firmware/app` (the C6 binary, its own workspace, its own target).
  The supervisor state machine is real, not a stub: all seven states, the permission
  lifecycle, the stopped criterion, FG/Hall plausibility, and the ramp, under 51 host tests
  that run on a laptop in milliseconds — including the 10 s and 120 s holds. CI grew a
  `core` job (fmt + clippy + **tests**) alongside `app` (fmt + clippy + release build).
  Console framing decided: everything on USB-serial-JTAG, protocol lines are `@`-prefixed
  newline-delimited JSON, one mutexed writer so logs cannot interleave mid-line.
- **Five reviewers found real bugs in phase A, all fixed**: `duty_for` returned full scale
  at the MCF ceiling (2048 into an 11-bit register aliases to zero — maximum command would
  have *stopped* the fan), `whole_rpm()` overflowed on the saturated tach value the crate
  itself manufactures, and `set_released_min` could panic the control loop via inverted
  `clamp` bounds. Four test gaps closed (ALARM path, bare-`On` resume, floor-raising, and
  the arm-settle branch that a 100 ms bench tick stepped straight over).

## Next

**Phase B: finish the state machine and the MCF register path.** Two strands. (1) Every
remaining row of [controls.md](controls.md) > "Failure behavior" gets implemented and
tested — I²C hang/9-clock recovery, MIN_VM undervoltage while running (DRV-09), thermal
OTW/TSD, ESP-reboot-while-powered. (2) The MCF8316D 24-bit control word, which phase A
deliberately left unimplemented rather than guessed: `RegisterBus` is abstract today, and
until it is real, **fault recovery does not work end-to-end** (`ClearMcfFault` is a log
line, so a latched MCF fault survives the supervisor's clear and the restart fails safe via
the 15 s `NoRotation` timeout). Verify the encoding against the datasheet directly — a
wrong bit position writes garbage into a motor controller. Not hardware-gated.

Also in phase B, before Wi-Fi exists: move the control loop and heartbeat onto a
higher-priority interrupt executor. It changes nothing today and must be structural *before*
Matter tasks are spawned, or a hung network task starves the heartbeat and turns network
loss into a watchdog stop — the exact inversion of the contract.

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
