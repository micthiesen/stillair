# State

Fast-moving work state and chosen next step. This records the work, not machine state or
uncommitted changes. Durable findings live in the linked docs.

Last updated: **2026-07-30** (session 5 wrap: PCB-01 ordered from JLCPCB, Konnect
re-scoped to schematic-only.)

## Now

- **PCB-01 is at the fab**: JLCPCB order **W2026073105230212**, $354.07 incl. DHL —
  5 boards, 2 assembled (Standard PCBA, top side), 4-layer 2 oz outer / 1 oz inner
  ENIG, POFV vias, 0.2 mm min-via tier. 60/60 BOM lines matched; two order-time
  pool-shortage swaps (4.7k → C105871, 562k → C4323390) are in
  `pcb/pcb-01/fab/lcsc-map.csv`. Full option set + sourcing rationale:
  [electrical.md](electrical.md) "Fabrication" + the /kicad-manufacture skill.
- **In-flight watch**: engineering review may ask about the intentional J2/J6 edge
  overhangs (confirm); DHL emails a tax link; **U1's orientation was unverifiable in
  the preview (no model)** — when the Confirm-Parts-Placement render arrives, check
  the MCF pin-1 corner against the board file before approving.
- **Bench work queued for arrival**: hand-solder C1, C2, C34, J1, J2, U8; bridge F1's
  pads. **Next DigiKey order must include C34** (0603 100 nF C0G/U2J, 5% fine — see
  electrical.md) plus a 100 nF 0603 strip for PCB-02. Nothing else is unpurchased
  electrically.
- **Owner lean recorded**: if PCB-01 fits the housing and works, V1 likely becomes the
  permanent board — no V2 unless desired (electrical.md's decide-after-bring-up gate
  stands; the default flipped).
- **Konnect verdict settled**: schematic engine only — kept for capture, everything
  board/fab-side runs on kicad-cli + `pcb/tools/`. Vendored skills rewritten to match.
- **Mechanical/ordering unchanged**: motor in transit; SP-100 waits on measurements.

## Next

**PCB-02 routing** (capture, board setup, and placement done 2026-07-30: `pcb/pcb-02/`,
ERC clean, DRC clean apart from the J1-silk-over-edge waivers in
`pcb/pcb-02/placement/waivers.md`; M2 datum settled at board-local (7,4)/(13,4) —
H2 moved 1 mm west at placement for washer clearance, electrical.md updated). Michael
routes the three nets in KiCad (expect ~1 via, or 0 if AGND rides a B.Cu pour); Claude
runs the DRC-diff-per-save loop against the waivers baseline. Then generalize
`pcb/tools/jlc_fab.py` for the fab package; it ships as its own small order.

## Candidates Not Chosen

- **Motor-arrival release sprint**: measurement checklist → SP-100 → MC-100/RH-100 CNC
  batch. Becomes Next the day the GL100 box arrives.
- **Bring-up prep** (commissioning scripts against the real board; tach-chain bench
  stim via J3 square-wave injection) — becomes relevant when boards + C34 arrive.
- **TEMP_SENSE firmware implementation** — parked with `TODO(temp-sense)` in
  `app/src/matter.rs`.
- **Blade materials + first prints**; **mount mockup** — carried, fully parallel.

## Learned Recently

- **Konnect re-scope** (schematic-only doctrine, which toolsets to never load, why) →
  /pcb skill "Konnect scope"; /kicad-pcb gutted to a danger list; /kicad-manufacture
  rewritten around `pcb/tools/jlc_fab.py`; /kicad-review scoped schematic-good /
  board-superseded.
- **JLCPCB order-flow facts** (stackup picker locks copper — set weights directly;
  min-via tier must match the drill file; Standard-PCBA rails/depanel; THT hand-solder
  service; Confirm Parts Placement; `cur`-class offline page decoding; DHL for
  Canada) → /kicad-manufacture skill.
- **jlcsearch.tscircuit.com** as the LCSC catalog workaround + SMT-pool-vs-marketplace
  stock distinction → /kicad-manufacture skill.
- **All sourcing/substitution decisions** (incl. C34's dielectric-over-tolerance call
  and the AliExpress counterfeit rationale) → electrical.md "Fabrication" +
  `pcb/pcb-01/fab/lcsc-map.csv`.
