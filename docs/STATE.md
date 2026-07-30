# State

Fast-moving work state and chosen next step. This records the work, not machine state or
uncommitted changes. Durable findings live in the linked docs.

Last updated: **2026-07-30** (session 4 wrap: PCB-01 layout is FINISHED — copper, fills,
stitching, scripted routing audit, silkscreen. Zero unconnected, zero non-waived DRC.
Only the fab-output pass remains.)

## Now

- **PCB-01 layout is complete and fully triaged.** Copper: J8 plane taps, B.Cu `agnd-bcu`
  fill, all 116 AGND+3V3 stitch items closed (rules-based sweep by Michael, headless DRC
  diff per save), antenna keepout trimmed off U2's ground column, `.kicad_dru` scoped,
  starved thermals solid-connected. Audit: RAW24 haul widened to class size, BUCK_SW got
  a B.Cu pour keepout (fill gap 0.30 → 1.14 mm). Silk: ~100 refs relocated via
  `pcb/tools/silk_sweep.py` + render-guided hand fixes; 45 refs hidden (42 passives +
  TP21/TP24/R42 — provably no room at the 0.8 mm minimum). Final baseline in
  `pcb/pcb-01/placement/waivers.md`; whys in [electrical.md](electrical.md) "Routing
  notes".
- **The scripted-audit pattern paid off**: width-vs-netclass, tach-region purity,
  SW-vs-fill proximity, and antenna-strip checks found two real DRC-invisible issues in
  ~15 min; a Sonnet review swarm was considered and rejected (agents are weak at raw
  trace-geometry reasoning — audits + DRC beat them here).
- **Mechanical/ordering unchanged**: motor in transit; SP-100 waits on measurements.

## Next

**Fab-output pass for PCB-01**: gerbers/pos/BOM via the /pcb manufacture path
(`export_manufacturing_package`; first export is done together per the skill's
ask-before-doing note, and needs KiCad open). This makes PCB-01 order-ready. PCB-02
(Hall daughterboard) capture is the natural follow-on so both boards share one fab
order.

## Candidates Not Chosen

- **Motor-arrival release sprint**: measurement checklist → SP-100 → MC-100/RH-100 CNC
  batch. Becomes Next the day the GL100 box arrives.
- **PCB-02 Hall daughterboard capture** — small board, unblocks the fab order bundle;
  natural follow-on to the fab-output pass.
- **TEMP_SENSE firmware implementation** — parked with `TODO(temp-sense)` in
  `app/src/matter.rs`.
- **Blade materials + first prints**; **mount mockup** — carried, fully parallel.

## Learned Recently

- **Rules-not-coordinates for dense canvas work** + silk-sweep tooling and its quirks
  (absolute property-text angles, 0.8 mm text floor, hollow outline interiors hiding
  labels under modules, headless render-inspection recipe) → `.claude/skills/pcb/SKILL.md`.
- **`.kicad_dru` conditions match text fields** (scope with `B.Type == 'Pad'`) and
  **rule areas can swallow a module's own pads** → `.claude/skills/pcb/SKILL.md`.
- **All copper/fill/audit decisions** (stitch geography, keepout trim, solid thermals,
  RAW24/BUCK_SW audit fixes, unlabeled TP21/TP24) →
  [electrical.md](electrical.md) "Routing notes"; residual waivers →
  `pcb/pcb-01/placement/waivers.md`.
