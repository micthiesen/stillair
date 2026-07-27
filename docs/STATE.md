# State

Fast-moving work state and chosen next step. This records the work, not machine state or
uncommitted changes. Durable findings live in the linked docs.

Last updated: **2026-07-27** (13-agent review + adversarial fix-verification pass both
integrated; anchors re-selected to Simpson Titen HD after owner cost research).

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
  plausibility constants.

## Next

**Capture the V1 controller schematic in KiCad** (`pcb/`), following
[electrical.md](electrical.md) SCH-01 through SCH-07 as amended by the review (delayed
`/PRE`, Schmitt buffers, corrected FET orientation, LM2907 fixes, GPIO7/15, GPIO8/9
pull-ups, 22 µF module bulk, NTC/VBUS circuits). Order config and footprint sourcing are in
`pcb/README.md`. Not hardware-gated.

## Candidates Not Chosen

- **Mount mockup + first metal** (MDF/printed plate-standoff-carrier mockup; order plate/
  rod/17-4PH stock; fab ST-100/SP-100/KD-100). Owner-driven, fully parallel with KiCad.
- **Strata/slab paper trail + City email** ([install.md](install.md)). Cheap, long-lead.
- **rs-matter devkit spike** (dev boards on hand; answers the AirflowDirection question).
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
