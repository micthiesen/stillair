# State

Fast-moving work state and chosen next step. This records the work, not machine state or
uncommitted changes. Durable findings live in the linked docs.

Last updated: **2026-08-01** (arrival day: GL100 motor, Accu fasteners, Titen HD
anchors, and DigiKey 374750597 — salesorder 100668200 — all received; the
motor-arrival release sprint is now Next.)

## Now

- **Arrived 2026-08-01**: the GL100 motor (RobotShop), the complete Accu fastener set
  (incl. KD-100 washers, castellated nut, Nord-Locks), the ohcanadasupply.ca Titen HD
  anchors, and DigiKey 374750597 (salesorder **100668200** on the packing slip — the
  LCSC-gap ICs, bulk caps, USB-C, JST housings/contacts, Qwiic cable). Still in flight:
  PCB-01 (JLCPCB W2026073105230212, DHL — 2 assembled + 3 bare), PCB-02
  (JLCPCB W2026073108244536, Global Standard Direct Line), and DigiKey **100723632**
  ($62.33, 24 lines; contents in bom/README.md).
- **PCB-02 is design-complete**: captured, placed, routed (DRC exactly at the
  `pcb/pcb-02/placement/waivers.md` baseline), swarm-reviewed (no board changes — all
  findings became docs), back-silk probe legend, fab package via the generalized
  `pcb/tools/jlc_fab.py pcb-02`. M2 datum (7,4)/(13,4) is the BR-100 bracket reference.
- **C34 decision locked**: 0603/0805 class-1 100 nF does not exist anywhere
  (permittivity limit); KEMET C1206C104K3GACTU ×4 ordered, hand-bridged onto the 0603
  site. X7R drop-in is bring-up fallback only. Full rationale: electrical.md
  "Fabrication".
- **In-flight watch (PCB-01)**: engineering review may ask about the intentional J2/J6
  edge overhangs (confirm); DHL emails a tax link; **check U1's MCF pin-1 corner against
  the board file when the Confirm-Parts-Placement render arrives** — it was unverifiable
  in the preview. J2 spare headers in 100723632 are backordered (not bring-up-critical).
- **Two small non-DigiKey purchases remain, both hardware**: an Amazon M2 kit
  (screws/nylocks/≤Ø4.5 washers/1–3 mm spacers — DigiKey's M2 catalog verified bare)
  and a Micro-Fit-capable crimper (Amazon IWISS-class ~$30 beats the $400 Molex tool;
  covers the JST PH crimps too). Fold into any Amazon order.
- **Mechanical unchanged**: SP-100 waits on measured motor axial length; MC-100/RH-100/
  BR-100 wait on motor gates; blades are owner print-engineering (eSUN PLA-LWT + CF rods
  now ordered).

## Next

**Motor-arrival release sprint** (promoted per the standing rule — the GL100 box
arrived 2026-08-01): the caliper measurement session against the parts.md "GL100
release checks" + "Fabrication gates" lists (axial length, face ownership, M4 depths,
bore/pilot mating diameter, wire-exit clocking, KD-100 measured thickness, fastener
on-arrival checks), measured values into the OnShape Variable Studio, then SP-100
release (needs axial length + washer t) and the MC-100/RH-100 CNC batch. Bearing data
(CubeMars email, sent 2026-07-27) is still the one gate calipers can't clear.

## Candidates Not Chosen

- **Bring-up prep** (previous Next, still fully desk-work and unblocked): commissioning
  scripts against `--sim` for the PCB-01..03 test rows, the tach-chain bench-stim plan
  (TACH-01), cable build sheets (J1 power, J3 Hall straight-through per TACH-06), and
  the arrival hand-solder sequence (C1, C2, C34-bridge, J1, J2, U8, F1 bridge).
  Reference: testing/test-matrix.csv + electrical.md "Fabrication".
- **BR-100 bracket + EB-100 standoff CAD**: now unblocked datum-wise (PCB-02 holes,
  element offset, J1 height all documented in parts.md/electrical.md), but sensibly
  waits for the motor so the wire-exit clocking is real.
- **TEMP_SENSE firmware** — hardware side now complete (NTC ordered); still parked with
  `TODO(temp-sense)` in `app/src/matter.rs`.
- **Blade materials + first prints; mount mockup** — carried, owner-driven.

## Learned Recently

- **PCB-02 build + board-truth review findings** (gap datum = SOT-23 face, element
  0.4 mm behind it; BR-100 handoff facts; H1 washer ≤Ø4.5; harness continuity TACH-06;
  series-R declined; omnipolar clarification) → electrical.md daughterboard section,
  parts.md BR-100, testing/test-matrix.csv.
- **C34 physics + bridge decision** → electrical.md "Fabrication", bom.csv.
- **Final-order swarm findings** (board-#2 J1/J2 headers, EB-100 standoffs never
  bought, J4 NTC never selected, C1/C2 zero-margin qty, 0.1% tach-resistor spares,
  C2 DNP-ladder stock, M2-not-at-DigiKey, crimper gap) → bom.csv lines + notes,
  electrical.md.
- **DigiKey cart mechanics** (Bulk Add silently drops multi-packaging MPNs; use
  `-1-ND`/`CT-ND` numbers; verify lines after add) → bom/README.md.
- **Konnect `add_board_text` quirk** (valid KiCad 10 output but no `(justify mirror)`
  on back layers) and **`add_mounting_hole` quirks** (dangling lib id, no courtyard)
  → /pcb skill.
- **JLCPCB shipping split** (Global Standard Direct Line for cheap non-blocking
  parcels — AliExpress-style consolidated clearance, ≤$99 declared; DHL for expensive
  blocking ones — best brokerage schedule) → bom/README.md order log context.
