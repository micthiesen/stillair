# State

Fast-moving work state and chosen next step. This records the work, not machine state or
uncommitted changes. Durable findings live in the linked docs.

Last updated: **2026-07-30** (routing session 4: PCB-01 copper is DONE — J8 taps, B.Cu
AGND fill, full AGND + 3V3 stitch sweeps, starved thermals fixed, waivers re-triaged.
Zero unconnected, zero non-waived DRC.)

## Now

- **PCB-01 routing and fills are 100% complete.** This session closed the J8.1/J8.2 plane
  taps, created the B.Cu `agnd-bcu` fill, swept all 87 AGND + 29 3V3 stitch items
  (rules-based sweep by Michael, headless DRC validation per chunk), trimmed the antenna
  keepout that was swallowing U2's ground column, scoped the `.kicad_dru` mounting-hole
  rule, and resolved all 5 starved thermals via solid zone connections. Final baseline
  (documented in `pcb/pcb-01/placement/waivers.md`): **unconnected 0, starved_thermal
  0**, clearance 6 / courtyards 18 / lib 7+4 all triaged-and-waived, silk 199/199/5
  pending. Whys → [electrical.md](electrical.md) "Routing notes".
- **Remaining on PCB-01**: (1) scripted silkscreen sweep (Claude, KiCad closed — the
  199/199/5 silk classes); (2) fab-output pass (gerbers/pos/BOM via the /pcb
  manufacture path).
- **Mechanical/ordering unchanged**: motor in transit; SP-100 waits on measurements.

## Next

**Silk sweep, then fab outputs.** The silk sweep is scripted cleanup of reference-text
overlaps (KiCad must be closed); then `export_manufacturing_package` for the JLCPCB
bundle. After that PCB-01 is order-ready and PCB-02 (Hall daughterboard) capture is the
natural follow-on so both boards share one fab order.

## Candidates Not Chosen

- **Motor-arrival release sprint**: measurement checklist → SP-100 → MC-100/RH-100 CNC
  batch. Becomes Next the day the GL100 box arrives.
- **PCB-02 Hall daughterboard capture** — small board, unblocks the fab order bundle;
  natural follow-on to the PCB-01 fab-output pass.
- **TEMP_SENSE firmware implementation** — parked with `TODO(temp-sense)` in
  `app/src/matter.rs`.
- **Blade materials + first prints**; **mount mockup** — carried, fully parallel.

## Learned Recently

- **Two new /pcb quirks** (`.kicad_dru` conditions match text fields — scope with
  `B.Type == 'Pad'`; rule areas can silently swallow a module's own pads) →
  `.claude/skills/pcb/SKILL.md`.
- **Rules-based sweeps beat coordinate lists for dense stitch work**: give trace/via
  sizes + the plane-geography rules (which L2/L3 region is under which x/y band) and
  let Michael chase airwires on canvas; validate with the headless DRC diff per save.
  Coordinate-by-coordinate instructions stopped being useful once the board got dense.
- **All fill/stitch decisions** (island stitching, keepout trim, solid thermals) →
  [electrical.md](electrical.md) "Routing notes (2026-07, in progress)".
