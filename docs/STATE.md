# State

Fast-moving work state and chosen next step. This records the work, not machine state or
uncommitted changes. Durable findings live in the linked docs.

Last updated: **2026-07-28** (full OnShape assembly model built and *animated* — the fan
spins on a revolute mate; rotor raised ~99 mm for cabinet doors; BP-100 v3 integrated-root
blade replaces blade + adapter; all docs swept.)

## Now

- **The firmware is done and runs on real hardware.** `firmware/` is three crates:
  `stillair-core` (`no_std`, zero esp-\* deps, sans-I/O, **171 host tests**), `firmware/cli`
  (the tuning harness), and `firmware/app` (the C6 binary). Supervisor, MCF8316D wire
  format, tuning console, configuration gate, and the Matter control plane are implemented
  and **verified end to end against Apple Home** (CTL-12). Everything left is gated on a
  real MCF8316D.
- **The full assembly model exists in OnShape and moves.** All fabricated parts are
  modelled in one Part Studio in world coordinates, variable-driven (`#standoffLen` 62,
  `#hubBottom`, `#pilotOD`, `#gl100Len`, `#hallGap`, `#phaseClock` 135.57°, `#phaseR`):
  MP-100 + derived GL100 (clocked), SP-100, ST-100 ×3, MC-100 with phase window, RH-100,
  KD-100 + castellated nut (capture-gap section check passed), three BP-100 v3 blades. An
  Assembly with a fixed stationary group and a revolute mate animates the rotor. **The
  OnShape model frame is rotated 180° about Z vs the docs**
  ([mechanical.md](mechanical.md) > Coordinate system).
- **The rotor was raised ~99 mm to clear cabinet doors** (hard constraint): ST-100 138 →
  62 mm, adapter deleted, blade bottom Z149.2, ceiling gap 4.68 in — an accepted
  hugger-regime deviation with RPM headroom as the compensation
  ([decisions.md](decisions.md)). PCB mounting is now horizontal-only
  ([electrical.md](electrical.md)).
- **BP-100 v3: the blade adapter no longer exists.** The blade prints an integrated root
  rectangle bolting straight to RH-100 (M5 into nut pockets, printed Ø5 dowel pins, no
  balance pocket), guided lofts from a four-feature FS generator, drooped proplet, scarf
  segmentation kept at r330, rod cut 374. Spec: [blade-v2.md](blade-v2.md). The BA-00
  filament research + qualification now target the root print
  ([parts.md](parts.md) > "Blade root-joint qualification").
- **RH-100 was restyled by the owner to a three-arm spoke plate**, which forced the tach
  redesign: **three identical stations at r76 on the arm centerlines** (one N52 magnet, two
  mass-matched brass slugs — balanced by three-fold symmetry, one Hall pulse/rev); sensing
  radius and MC-100 bracket holes moved r68 → r76 ([parts.md](parts.md),
  [mechanical.md](mechanical.md), [electrical.md](electrical.md)).
- **MP-100 is ordered** (JLCCNC, SUS304; check flatness on arrival). Mount work can start;
  CubeMars bearing email (Gate 01) still awaiting reply.

## Next

**Capture the V1 controller schematic in KiCad** (`pcb/`) — the standing decision now that
the assembly model has served its purpose (integration mistakes caught: the phase-window
clocking, the ENC-100 blade-top constraint, the PCB orientation). It is the critical path
to a fan that turns; every remaining firmware unknown is gated on a real MCF8316D. Follow
[electrical.md](electrical.md) SCH-01–SCH-07 as amended; order config and footprint
sourcing in `pcb/README.md`. Once a real MCF8316D exists: capture the golden image
(`stillair --port … config capture`).

Small model remainders, do opportunistically (tracked, not blocking): re-export
`cad/BP-100.step` (committed STEP is v2 geometry), the unmodeled hub screws (M4 flat-heads
below RH-100, M5 blade bolts) if wanted for visuals, and the step-9 clearance extras
(BR-100 Hall bracket at the new r76 line, MR-100 caps + M2 taps, EB-100 + horizontal PCB
envelope).

## Candidates Not Chosen

- **Blade materials + first prints**: order the Ø3 CF rods (cut 374) and an LW-PLA spool
  ([bom.csv](../bom/bom.csv)); segA material call (LW-PLA vs qualified PPA-CF) is part of
  the owner's strength program. Print 4 sets, select 3.
- **Mount mockup + first metal** (MDF/printed mockup at the new 62 mm stack; order
  plate/rod/17-4PH stock; fab ST-100/SP-100/KD-100). Fully parallel with the PCB.
- **Motor release checks** when the GL100 arrives (face ownership, pilot measurement,
  thread depths) — hardware-gated.
- **Non-concurrent Matter commissioning** (`run` vs `run_coex`) — a held lever, not a task.

## Learned Recently

- **Guided lofts**: dissimilar-profile lofts twist and seamed lofts crease; FS-generated
  guide curves through exact section points fix both → [CLAUDE.md](../CLAUDE.md) >
  "Building in OnShape together", implemented in `cad/bp100_sections.fs` (4 features, all
  driven by `#hubBottom + 6 mm`).
- **The v3 integrated root and why the adapter died** → [blade-v2.md](blade-v2.md); the
  qualification program's new target → [parts.md](parts.md).
- **The raise and the hugger trade-off numbers** → [decisions.md](decisions.md) > Accepted
  deviations; new stack tables → [mechanical.md](mechanical.md).
- **New ENC-100 constraint**: blade tops sweep r ≥ 110 at Z118.8 vs housing wall r ≤ 106 —
  ~4 mm radial → [parts.md](parts.md) ENC-100 section.
- **OnShape model frame is doc frame + 180° about Z**; phase window at doc 315° / model
  135.57° from the STEP's fixed 44.43° pad-to-bolt offset → [mechanical.md](mechanical.md).
- **Supersessions**: BA-00 deleted (parts.md, decisions.md, BOM, MEC-01/02/02B/07 test
  rows); ST-100 62 mm everywhere; PCB horizontal-only (electrical.md).
