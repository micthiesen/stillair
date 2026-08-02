# State

Fast-moving work state and chosen next step. This records the work, not machine state or
uncommitted changes. Durable findings live in the linked docs.

Last updated: **2026-08-02** (session 7 wrap: motor arrived and was measured, the
motor-gated CNC batch — SP-100/MC-100/RH-100 — was designed to rev A and **ordered**.)

## Now

- **All motor-gated metal is ordered**: JLCCNC **W2026080301372216**, $204.44 shipped
  (SP-100 $82.76 / MC-100 $48.83 / RH-100 $42.08). Rev A drawings + STEPs in `cad/`.
  SP-100 went in **SUS304** (JLCCNC has no 17-4PH; margin math + anti-seize install note
  in parts.md), RH-100 on the **±0.05 tier** so the measured-bore pilot fit is
  contractual. Per-part on-arrival checks are in each parts.md status block.
- **Arrived 2026-08-01**: GL100 motor, the full Accu fastener set, Titen HD anchors,
  DigiKey 374750597 (salesorder 100668200). Measured: axial 34.2–34.3 (nominal stands,
  stack derived), KD-100 t = 3.38 → SP-100 cross-hole Z136.6, bore Ø29.99–30.00 →
  pilot Ø29.85. All caliper-clearable fabrication gates closed (parts.md).
- **Design deltas this weekend** (all in parts.md): MR-100 caps deleted — epoxy is the
  retention; Hall sensor line moved to the standoff bisector ("150°", relational def
  controls); RH-100 blade stations owner-customized (released STEP is interface truth;
  blade root is owner-managed); BR-100 will be owner hand-fabbed, not designed in repo.
- **Parcels in flight**: PCB-01 (JLCPCB W2026073105230212, DHL — 2 assembled + 3 bare),
  PCB-02 (W2026073108244536), DigiKey **100723632**, and now the CNC batch. Watches:
  PCB-01 engineering review (J2/J6 overhangs intentional; verify MCF pin-1 corner in the
  placement render), CNC review may flag the SP-100 PDF's 17-4PH note (answer: per order
  config, SUS304).
- **Open loose ends**: CubeMars bearing email (sent 2026-07-27, unanswered — chase or
  accept as Gate 01 residual risk); Amazon M2 kit + Micro-Fit-capable crimper still
  unbought (fold into any Amazon order).

## Next

**Bring-up prep, so the bench is ready the day the DHL box lands** (restored: it was the
Next before the motor arrived and is still fully desk-work, blocked on nothing).
Concretely: commissioning scripts against `--sim` for the PCB-01..03 test rows, the
tach-chain bench-stim plan (square-wave injection at J3/HALL_TACH per TACH-01), the cable
build sheets (J1 power, J3 Hall straight-through per TACH-06), and the hand-solder
sequence for arrival (C1, C2, C34-bridge, J1, J2, U8, F1 bridge). Reference:
testing/test-matrix.csv + electrical.md "Fabrication".

## Candidates Not Chosen

- **EB-100 PCB-bracket CAD** — fully unblocked now (motor in hand, wire exit real,
  PCB-01 mounting facts documented); pairs naturally with the owner's BR-100 hand-fab.
- **TEMP_SENSE firmware** — hardware complete; still parked with `TODO(temp-sense)` in
  `app/src/matter.rs`.
- **Blade prints (BP-100)** — owner print-engineering; materials + CF rods in hand/inbound.
- **On-arrival check sessions** — each parcel has its checklist (parts.md status blocks,
  STATE watches); becomes the day's work whenever a box lands.

## Learned Recently

- **GL100 measurements + gate closures** (axial stack, washer → Z136.6, bore → pilot
  Ø29.85; face/bore ownership confirmed) → parts.md "GL100 release checks" +
  "Fabrication gates".
- **Owner verification philosophy** (measure only what feeds non-adjustable machined
  features or safety assumptions; adapt at install otherwise) → CLAUDE.md.
- **Drawing pass as model audit + frame-ambiguity gotcha** (caught M5-default
  counterbores and stale Ø6.1 pockets; angles mirror across sketch frames — define
  clockings relationally) → CLAUDE.md OnShape section.
- **MR-100 deletion + epoxy retention rationale**; **SUS304 substitution margin math**;
  **±0.05-tier reasoning for the pilot** → parts.md.
- **Order log + arrivals** (100668200 = 374750597; W2026080301372216 contents) →
  bom/README.md, bom.csv.
