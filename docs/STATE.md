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
  MP-100 waits on the cable-slot angle + ENC tab clocking decisions; the adapter filament
  qualification is the longest non-motor-gated path.
- **Control plane locked**: Matter over Wi-Fi (rs-matter). Orders in; GL100 + parts en
  route; CubeMars bearing email sent 2026-07-27 (Gate 01 awaiting reply).
- Firmware scaffold compiles, CI-guarded; contract now includes stop criterion and
  plausibility constants. **It is not testable**: one `no_std` binary crate with
  `test = false` and `build.target` pinned to RISC-V, so `cargo test` cannot run at all
  even though `state.rs` / `config.rs` / `mcf8316.rs` are pure logic.
- **Owner direction (2026-07-27)**: only ESP32-C6 dev boards are on hand, so the near-term
  program is all of the firmware plus a motor-tuning/telemetry harness, built out *before*
  the V1 board exists and driven by Claude Code once it does.

## Next

**Split `firmware/` into a host-testable core plus a target app, and land the first real
state-machine slice on top of it.** A `stillair-core` crate (`no_std`, zero esp-\* deps)
takes the state machine, MCF register encode/decode, speed mappings (percent↔RPM,
duty↔RPM, FG↔RPM) and tach/plausibility logic behind narrow hardware traits with an
injected clock; `app/` keeps the esp-hal wiring and the RISC-V target (root workspace on
the host target, `exclude = ["app"]`, app carries its own `.cargo/config.toml`). Prove the
boundary by implementing SafeBoot → IdleOff → Starting → Running against a fake platform,
with host tests for the 10 s DRVOFF hold and the permission lifecycle.

Why this first: every other firmware candidate (full state machine, console protocol,
simulator, CLI) needs this trait boundary, and a core with no esp-\* deps is immune to the
`[patch.crates-io]` churn the rs-matter adoption will bring. Contract:
[controls.md](controls.md) > "Required state behavior" + "Firmware safety architecture".
Not hardware-gated.

Rough order after that: full state machine (every failure-table row as a test) → tuning
harness (device console + `tools/stillair` CLI + simulator) → rs-matter → real bring-up.

## Candidates Not Chosen

- **Tuning + telemetry harness** — device-side line console (`reg read/write`, `run <rpm>`,
  `dir`, `state`, `stream on <hz>` → CSV telemetry), a host CLI sharing `stillair-core` for
  the protocol and register encoding, and a simulator implementing the same hardware traits
  so the loop runs with no board. One CLI subcommand per `testing/test-matrix.csv` row with
  machine-readable pass/fail is the Claude-Code-friendly part. Waits on the core split
  (otherwise the protocol layer gets written twice). **Caveat to carry forward**: a
  simulator validates the harness, never the sensorless tuning.
- **rs-matter devkit spike** (dev boards on hand; answers the AirflowDirection question).
  The one candidate worth running genuinely in parallel — shares nothing with the core
  split, and it is the biggest external unknown (git deps, patch pinning, BLE
  commissioning, flash persistence).
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
