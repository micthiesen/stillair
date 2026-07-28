# State

Fast-moving work state and chosen next step. This records the work, not machine state or
uncommitted changes. Durable findings live in the linked docs.

Last updated: **2026-07-27** (BP-100 printed blade designed, modelled in OnShape, and
exported; blade docs/BOM synced. Next changed by owner decision: build out the full OnShape
assembly model before the V1 schematic — visualizing integration early is cheap insurance.)

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

**Build out the full assembly model in OnShape** (owner decision 2026-07-27; the document
already holds MP-100 + three patterned BP-100 blades — 6 parts). Everything below is
dimensioned in [parts.md](parts.md); the point is to see the integrated stack early and catch
interface mistakes while they cost nothing. ENC-100 housing and cabling are **deliberately
deferred** — they depend on everything else settling. Per-session working style:
[CLAUDE.md](../CLAUDE.md) > "Building in OnShape together".

**Progress 2026-07-27 (same day, later session): steps 1–7 are modelled** (GL100 derived +
clocked, Variable Studio live with `#pilotOD`/`#gl100Len`/`#hallGap`/`#phaseClock`/`#phaseR`,
SP-100, ST-100 ×3, MC-100 with phase window, RH-100 with stations + tach pockets, KD-100 +
castellated nut; capture-gap section check passed). Mid-build the owner requested a **99.8 mm
rotor raise** to clear cabinet doors — docs rewritten (stack: standoffs 84, flat BA-00,
blade bottom Z148.7; deviation in [decisions.md](decisions.md)); the OnShape model still has
the *old* heights pending the update sequence: set `#standoffLen` = 84, re-drive motor
transform + hub plane from variables, shorten SP-100 sketch dims (shoulder 142.7 / end 164 /
hole 159.2), translate blades +99.8, then model BA-00 (now designed, parts.md) and pattern.
Note: the OnShape model frame is rotated 180° about Z vs the docs
([mechanical.md](mechanical.md) > Coordinate system).

Order (each step is the reference geometry for the one after):

1. **Import the official GL100 STEP** (links at the top of [parts.md](parts.md)) — every
   motor interface clocks off it, but treat it as *reference-only* (it gets superseded by
   physical measurement; don't boolean against it or mate structurally to its faces). At the
   same time create a **Variable Studio** holding every provisional/motor-gated number
   (`#pilotOD` 29.8, `#gl100Len` 34.2, wire-window clocking, Hall gap …) and dimension
   MC-100/RH-100 sketches from the variables — a bench measurement then lands as a one-line
   edit. Working style: [CLAUDE.md](../CLAUDE.md) > "Building in OnShape together".
2. **SP-100 spindle** — revolve + 30.0 AF double-D flats + Ø3.2 cross-hole; fully
   dimensioned in parts.md. Seat its flange in MP-100's double-D pocket; this establishes
   the centerline stack (Z196.7 shoulder, thread to Z218).
3. **ST-100 standoffs** ×3 (Ø16 × 138 on Ø150 PCD at 90/210/330°) — trivial; they set
   MC-100's plane at Z152.
4. **MC-100 motor carrier** — Ø188 × 8; clock the Ø60 M4 pattern and the phase-lead window
   from the imported STEP.
5. **Seat the GL100**: stationary rear face (Ø60/M4) up against MC-100, M4 × 12 from above;
   rotating front face (Ø50/M4) at Z186.2.
6. **RH-100 rotor hub** on the rotating face — M4 × 10 flat-heads from below, subflush;
   pilot OD stays provisional (nominal 29.8, motor-measured before fab). Includes the three
   adapter stations and tach pockets.
7. **KD-100 catcher disk + DIN 935 castellated nut** on the spindle end — then *visually
   verify* the 2.5 ±0.5 mm capture gap and the ≥2.0 mm screw-head clearance in section view.
8. **BA-00 adapter — design first, then model** (the one open design task in the chain):
   hub side mates RH-100's stations (four Ø5.5 at r62/r88 y±15 + two dowels), blade side
   mates the BP-100 pad (four M5 at r130/r180 y+10/−30, pad underside Z240). "Flat" applies
   to the blade interface only — the part must drop ~46 mm from the hub underside (Z194.2)
   to the pad, so it's a riser/drop arm; geometry TBD. Record the finished design in
   [blade-v2.md](blade-v2.md) + [parts.md](parts.md), CF-PPA per the BOM.
9. **Clearance extras** once the stack exists: BR-100 Hall bracket + magnet caps (Hall gap
   2.5 nominal), EB-100 bracket + the 78 × 58 PCB envelope — these are for visual clash
   checks more than fabrication.

Assembly practice: keep fabricated parts in Part Studios and compose in an OnShape Assembly
using the Z-stack table in [mechanical.md](mechanical.md); pattern blades/adapters/standoffs
in the assembly, not the Part Studios.

**After (or in parallel): capture the V1 controller schematic in KiCad** (`pcb/`) — still the
critical path to a fan that turns; every remaining firmware unknown is gated on a real
MCF8316D. Follow [electrical.md](electrical.md) SCH-01–SCH-07 as amended by the review; order
config and footprint sourcing in `pcb/README.md`. Then, once a real MCF8316D exists: **capture
the golden image** (`stillair --port … config capture`).

## Candidates Not Chosen

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
