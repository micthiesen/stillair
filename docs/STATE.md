# State

Fast-moving work state and chosen next step. This records the work, not machine state or
uncommitted changes. Durable findings live in the linked docs.

Last updated: **2026-07-30** (session 5: PCB-01 fab-output pass DONE — JLCPCB package
generated + fully LCSC-sourced; order walkthrough delivered, order placement with
Michael in progress.)

## Now

- **PCB-01 is order-ready.** Pre-fab DRC exactly matches the waivers.md baseline
  (0 unconnected). `pcb/tools/jlc_fab.py` generates the whole JLCPCB package headless
  into `pcb/pcb-01/fab/`: 14-file gerber zip, 60-line assembly BOM (every line has an
  LCSC number), 120-part top-side-only CPL. Konnect's own manufacturing tools proved
  broken for this (see /pcb skill); kicad-cli via the script is the path.
- **Sourcing decided and recorded** (electrical.md "Fabrication"): Standard PCBA
  (ESP32-C6 is "Standard Only"), owner-approved substitutions in
  `pcb/pcb-01/fab/lcsc-map.csv` (1%-for-0.1% on R48/R53 — RV1 calibration absorbs;
  X5R-for-X7R bypass; Vishay BAT54W for BAT54H). Hand-solder set: C1, C2, C34, J1,
  J2, U8. **C34 needs a DigiKey 0603 100 nF 1% C0G/U2J added to the next order.**
  bom.csv updated: RV1 is the SMD 3224W-1-204E (3296Y pieces = bench spares).
- **Low-stock watch items at order time**: MCF8316D (10 in JLC SMT pool), TPS7A1601
  (8), TPS3435 (60), SM04B-SRSS-TB (59), USB4105 (295), 90.9k 0.1% (79). If one dries
  up mid-order, JLCPCB part-matching offers alternates or Global Sourcing.
- **Mechanical/ordering unchanged**: motor in transit; SP-100 waits on measurements.

## Next

**Place the JLCPCB order** (Michael in the browser, Claude advising): upload
`fab/pcb-01-gerbers.zip`, options per electrical.md "Fabrication" (4-layer 7628,
1.6 mm, 2 oz outer/1 oz inner — confirm 2 oz outer is offered on the live 4-layer
form, ENIG, POFV via covering), Standard PCBA single-side ×2 boards, upload
BOM + CPL, review part matches against lcsc-map.csv notes, fix rotations in the
placement preview (diodes/ICs are the usual suspects), tick "Confirm Parts
Placement". Then **PCB-02 Hall daughterboard capture** — decide at checkout whether
to hold the PCB-01 order a session to bundle shipping, or ship separately (small
board, cheap second shipment).

## Candidates Not Chosen

- **Motor-arrival release sprint**: measurement checklist → SP-100 → MC-100/RH-100 CNC
  batch. Becomes Next the day the GL100 box arrives.
- **PCB-02 Hall daughterboard capture** — folded into Next as the follow-on; only its
  bundling-vs-separate-shipment question remains open.
- **TEMP_SENSE firmware implementation** — parked with `TODO(temp-sense)` in
  `app/src/matter.rs`.
- **Blade materials + first prints**; **mount mockup** — carried, fully parallel.

## Learned Recently

- **Konnect manufacturing/validation tools are not fab-ready** (inch-unit CPL, no LCSC
  column, drill-as-directory, validator misreads the board) → /pcb skill; fab exports
  are now Claude-driven via `pcb/tools/jlc_fab.py`.
- **jlcsearch.tscircuit.com is the LCSC-lookup workaround** for the JS-opaque
  JLCPCB/LCSC pages (raw JSON, basic/extended + stock; resistance param wants raw ohms).
  JLC SMT-pool stock ≠ LCSC marketplace stock — trust the smaller number for assembly.
- **JLCPCB current rules** (researched 2026-07-30): Standard PCBA $25 setup +
  $1.50/unique-part feeder (basic and extended alike); Economic is single-side,
  ≤30 pcs, no "Standard Only" parts; THT hand-solder service $3.50 + ~$0.017/joint;
  min 5 bare boards; "Confirm Parts Placement" is cheap insurance — tick it.
- **All sourcing decisions + substitution rationale** → electrical.md "Fabrication" +
  `pcb/pcb-01/fab/lcsc-map.csv`.
