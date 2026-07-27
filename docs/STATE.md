# State

Fast-moving work state and chosen next step. This records the work, not machine state or
uncommitted changes. Durable findings live in the linked docs.

Last updated: **2026-07-27** (six-thread research round integrated: MCF variant, GPIO map,
bearings, JLCPCB/KiCad, filament, Vancouver anchors/approvals).

## Now

- **Design de-risked substantially by desk research.** MCF swapped to plain
  `MCF8316DVRGFR` (identical silicon; unlocks JLCPCB assembly); 35 RPM sensorless floor
  confirmed comfortably feasible; GPIO map verified against the module datasheet (NTC moved
  to GPIO6, ALARM added on GPIO14); EXT_WD wired into the safety story; anchors selected
  with ~7× margin; Gate 06 reduced to strata approval + one confirming email to the City.
  Homes: [electrical.md](electrical.md), [controls.md](controls.md),
  [install.md](install.md).
- **Control plane locked: Matter over Wi-Fi via rs-matter + rs-matter-embassy** (Apple
  Home). Open product question: whether Apple Home renders `AirflowDirection` (fallback: a
  second On/Off "reverse" endpoint). [controls.md](controls.md) > "Home integration".
- **Procurement state**: wall-box chain, supply, connectors, cable, and the GL100 ordered
  (connector order verified as the corrected single-row Micro-Fit parts). BOM carries LCSC
  numbers, lifecycle notes, and the anchor candidates. LM2907 thin stock → buy spares with
  the V1 order. Blade adapters: Bambu PPA-CF on the project's X2D
  ([parts.md](parts.md)).
- **Firmware scaffold compiles, CI-guarded.** No business logic; contract in
  [controls.md](controls.md).
- **Nothing fabricated.** Motor-dependent metal gates on measuring the purchased GL100; the
  V1 PCB gates on KiCad capture; anchors gate on the slab scan.

## Next

**Capture the V1 controller schematic in KiCad** (`pcb/`), following
[electrical.md](electrical.md) SCH-01 through SCH-07 (now including EXT_WD, ALARM→GPIO14,
DEV_MODE standby, and the D-generation pinout notes). Order config and footprint sourcing
are pre-researched in `pcb/README.md`. It gates the V1 board order, which gates motor tuning
and every V1-to-V2 test. Not hardware-gated.

## Candidates Not Chosen

- **Start the strata/slab paper trail** (request structural drawings; the Gate 06 email to
  the City). Cheap, long-lead, fully parallel — checklist in [install.md](install.md).
  (The CubeMars bearing-data email was **sent 2026-07-27**; Gate 01 is awaiting their
  reply — see [parts.md](parts.md).)
- **rs-matter devkit spike** → commission into Apple Home, then a Fan endpoint to answer
  the AirflowDirection question. ESP32-C6 dev boards are already on hand, so this is
  startable any time.
- **Motor release checks** (faces, thread depths, bores, STEP import) as soon as the GL100
  arrives — unblocks motor-dependent metal in CAD.
- **OnShape modeling of motor-independent parts** (plate, standoffs, blades). Startable, off
  the critical path.

## Learned Recently

- **MCF8316DVRGFR ≡ DULV minus UL paperwork; D silicon has no known errata; 35 RPM is easy
  for this motor; EXT_WD/ALARM/SPEED-sleep/EEPROM rules** → [electrical.md](electrical.md)
  SCH-03/05, [controls.md](controls.md).
- **GPIO14 has no ADC on the C6** — map verified and corrected (NTC→GPIO6, ALARM→GPIO14) →
  [electrical.md](electrical.md) SCH-04.
- **No public GL-series bearing data; axial hang trivial, overturning moment is the real
  ask; external thrust bearing is the fallback** → [parts.md](parts.md).
- **KB-TZ2 3/8 in SS ~7× margin; adhesive anchors carry overhead-sustained penalties; strata
  approval is the one hard requirement; cord-and-plug 24 V likely needs no permit** →
  [install.md](install.md).
- **JLCPCB 2 oz outer / ENIG orderable (trace/space 0.15 mm caveat, POFV vias paid); MCF +
  TPSM365 footprints need Ultra Librarian, most others are in KiCad official libs** →
  `pcb/README.md`.
- **Bambu PPA-CF selected; creep/fatigue/Z data doesn't exist anywhere, so the empirical
  qualification plan is the release evidence** → [parts.md](parts.md).
- **The pre-repo research file survives at `~/.research/ceiling-fan.md`** (now banner-linked
  here); it yielded the Micro-Fit connector correction and the purchasing split.
