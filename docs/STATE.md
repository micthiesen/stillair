# State

Fast-moving work state and chosen next step. This records the work, not machine state or
uncommitted changes. Durable findings live in the linked docs.

Last updated: **2026-07-27** (BP-100 printed blade designed, modelled in OnShape, and
exported; blade docs/BOM synced. Next remains the V1 schematic — unchanged and untouched.)

## Now

- **The firmware is done and runs on real hardware.** `firmware/` is three crates:
  `stillair-core` (`no_std`, zero esp-\* deps, sans-I/O, **171 host tests**), `firmware/cli`
  (the tuning harness, driving a board or an in-process simulator), and `firmware/app` (the
  C6 binary). Supervisor, MCF8316D wire format, tuning console, boot-time configuration gate,
  and the Matter control plane are implemented, reviewed, and flashed. **Matter is verified
  end to end against Apple Home** (0–100% slider, on/off, reverse; the mapping onto
  [35, 170] RPM confirmed on silicon, CTL-12). The fan pairs but correctly refuses to spin:
  with no MCF8316D on the bus, `SafeBoot` holds — everything left in firmware is gated on
  real hardware.
- **The blade is redesigned: BP-100 replaces the birch flat plate** (this session, accepted).
  Cambered NACA 6407 sections, 17°→8.5° baked-in twist, slim root with mid-span max chord,
  raked proplet tip, Ø3 CF-rod spar (cut to 318 mm), two printed segments scarf-joined at
  r330 in aero/LW-PLA. Full spec + OnShape build path: [blade-v2.md](blade-v2.md); parametric
  generator `cad/bp100_sections.fs`; both segments exported to `cad/BP-100.step`. The
  BA-10/12/14 pitch family collapses to a single flat **BA-00 (undesigned — now the blade
  path's blocker)**; pitch changes are reprints via the feature's `PITCH_OFFSET` input.
  Print/rod strength validation is owner-scope.
- **MP-100 is ordered — the first custom part committed to metal.** JLCCNC, SUS304, qty 1,
  ~$130; rev A STEP + PDF in [`cad/`](../cad/). **On arrival: check flatness with a
  straightedge before drilling the ceiling** — JLC holds no form tolerances.
- **Mount work can start** ([build.md](build.md) > "Mount build-first plan"): mockup first,
  then ST-100/SP-100/KD-100 are fully spec'd and motor-independent. GL100 + parts en route;
  CubeMars bearing email sent 2026-07-27 (Gate 01 awaiting reply). Anchors are Simpson Titen
  HD with the full ESR-2713 basis in [install.md](install.md).

## Next

**Capture the V1 controller schematic in KiCad** (`pcb/`). Every remaining firmware unknown —
register values, the golden image, sensorless startup tuning, the analog trip calibration — is
gated on having an MCF8316D to talk to, so the board is the single thing standing between
here and a fan that turns. Follow [electrical.md](electrical.md) SCH-01–SCH-07 **as amended by
the review** (delayed `/PRE` RC + Schmitt, corrected reverse-polarity FET orientation, LM2907
fixes, GPIO7/15 routes, GPIO8/9 pull-ups, 22 µF module bulk, NTC/VBUS circuits); order config
and footprint sourcing in `pcb/README.md`. Not hardware-gated.

Then, once a real MCF8316D exists: **capture the golden image.** The gate is built and holds;
`stillair --port … config capture` prints the table, and until it is filled in every telemetry
frame and CSV row honestly reports `config: unverified`.

## Candidates Not Chosen

- **BA-00 flat blade adapter design** (new): flat plate mating the BP-100 pad (four M5 at
  r130/r180, y+10/−30) to RH-100's unchanged stations. Small, motor-independent, and now the
  only designed-parts gap in the blade path — good parallel work alongside the PCB.
- **Blade materials + first prints**: order the Ø3 CF rods and an LW-PLA spool
  ([bom.csv](../bom/bom.csv)), print a segment set from `cad/BP-100.step`, owner strength
  validation. Longest blade-path lead alongside the PPA-CF adapter qualification.
- **Mount mockup + first metal** (MDF/printed plate-standoff-carrier mockup; order
  plate/rod/17-4PH stock; fab ST-100/SP-100/KD-100). Owner-driven and fully parallel with the
  PCB.
- **Motor release checks** when the GL100 arrives (pilot-register rotating-surface
  confirmation, axial-length tolerance measurement). Hardware-gated on delivery.
- **Non-concurrent Matter commissioning** (`run` instead of `run_coex`) — a lever held in
  reserve for coexistence scan flakiness, not a task.

## Learned Recently

- **The BP-100 design and why each choice fell out of the low-Re aero** (thin cambered
  section, washout, slim root, proplet tip, scarf segmentation) →
  [blade-v2.md](blade-v2.md); envelope re-derived there, superseding the 12°-flat numbers in
  [mechanical.md](mechanical.md).
- **A straight spar must anchor on the camber line, not the chord line** — a cambered
  section's material sits above its chord line, so a rod anchored there misses the blade
  entirely; and the proplet run-in ends the channel at r430 → [blade-v2.md](blade-v2.md)
  "Coordinates" / "Spar and segmentation"; check script `cad/bp100_envelope_check.py`.
- **Root-closure lofts tangent to a still-growing chord bulge outward** — rejected in favor
  of a vertical plan-view corner trim; and **nut pockets on a twisted root need per-row floor
  depths** → [blade-v2.md](blade-v2.md) "Root corners" / "Root fitting".
- **OnShape workflow**: a small FeatureScript generating sections from a station table beat
  both library airfoil features (no 6%-camber-at-40% profiles in the HAVF library) and
  hand-drawn chord sketches; station array order is sketch-id-stable only if appends go last
  → `cad/bp100_sections.fs`.
- **Supersessions recorded**: [parts.md](parts.md) (BL-100/LS-100/BA as fallback),
  [decisions.md](decisions.md) rotor row, [bom.csv](../bom/bom.csv) (rod + LW-PLA lines,
  BA-00 note).
