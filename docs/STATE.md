# State

Fast-moving work state and chosen next step. This records the work, not machine state or
uncommitted changes. Durable findings live in the linked docs.

Last updated: **2026-07-30** (session 5: PCB-01 ORDERED from JLCPCB — order
**W2026073105230212**, $354.07 incl. DHL Express: 5 boards, 2 assembled, Standard PCBA,
4-layer 2 oz outer ENIG, POFV vias.)

## Now

- **PCB-01 is at the fab.** 60/60 BOM lines matched (two order-time pool-shortage swaps:
  4.7k → C105871, 562k → C4323390 — recorded in `pcb/pcb-01/fab/lcsc-map.csv`). Placement
  preview polarity-checked (D1–D9 verified against the board file; D2's vertical
  orientation confirmed). U1 (MCF QFN) had no preview model — its orientation rides on
  the "Confirm Parts Placement" engineer review; verify the render crop against the
  board file when JLCPCB emails it, before approving.
- **In-flight watch**: DFM/engineering review may email about the J2/J6 edge overhangs
  and rail-adjacent parts (intentional — confirm); DHL will send a tax-payment link.
- **Hand-populate on arrival**: C1, C2, C34, J1, J2, U8. **C34 needs a DigiKey 0603
  100 nF 1% C0G/U2J added to the next DigiKey order** (nothing suitable at JLCPCB).
- **Owner lean recorded**: if PCB-01 fits the housing and works, V1 likely becomes the
  permanent board — no V2 unless desired. Keeps the electrical.md "decide after V1
  bring-up" gate, but the default flipped from "V2 later" to "V1 is probably it".
- **Mechanical/ordering unchanged**: motor in transit; SP-100 waits on measurements.

## Next

**PCB-02 Hall daughterboard capture** (18 × 8 mm DRV5033 carrier, own KiCad project in
`pcb/pcb-02/`, spec in electrical.md "PCB-02"). Pure desk work, fully parallel with the
board order in transit; it ships as its own small order (V1 went out separately). The
`jlc_fab.py` pattern generalizes — parameterize or copy it for pcb-02.

## Candidates Not Chosen

- **Motor-arrival release sprint**: measurement checklist → SP-100 → MC-100/RH-100 CNC
  batch. Becomes Next the day the GL100 box arrives.
- **TEMP_SENSE firmware implementation** — parked with `TODO(temp-sense)` in
  `app/src/matter.rs`.
- **Blade materials + first prints**; **mount mockup** — carried, fully parallel.
- **Bring-up prep** (commissioning scripts against the real board) — becomes relevant
  when boards + DigiKey C34 arrive.

## Learned Recently

- **Konnect manufacturing/validation tools are not fab-ready** (inch-unit CPL, no LCSC
  column, drill-as-directory, validator misreads the board) → /pcb skill; fab exports
  are Claude-driven via `pcb/tools/jlc_fab.py`.
- **jlcsearch.tscircuit.com is the LCSC-lookup workaround** for JS-opaque JLCPCB pages
  (raw JSON, basic/extended + stock; resistance param wants raw ohms). JLC SMT-pool
  stock ≠ LCSC marketplace stock, and the order-page matcher is the final word — two
  deep-stock parts still came up short there.
- **JLCPCB order-flow facts** (2026-07-30): impedance stackup picker locks copper
  weights — leave "Specify Stackup"/impedance off and set outer/inner copper directly;
  min-via-hole option must match the drill file (board has 0.2 mm drills → 0.2 mm
  tier); Standard PCBA forces ≥70 mm width → auto edge rails + depanel service;
  saved-page HTML decodes selections via the `cur` class.
- **All sourcing decisions + substitution rationale** → electrical.md "Fabrication" +
  `pcb/pcb-01/fab/lcsc-map.csv`.
