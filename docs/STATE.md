# State

Fast-moving work state and chosen next step. This records the work, not machine state or
uncommitted changes. Durable findings live in the linked docs.

Last updated: **2026-08-17** (MP-100 ceiling plate installed with the three ST-100
standoffs and SP-100 spindle in place; tether work remains on HOLD.)

## Now

- **All fabricated parts are received**: both JLCPCB runs (PCB-01
  **W2026073105230212**, 2 assembled + 3 bare; PCB-02 **W2026073108244536**, 5 bare)
  and all JLCCNC parts, including MP-100, four ST-100s, and batch
  **W2026080301372216** (SP-100 / MC-100 / RH-100). Owner accepted the delivered parts
  as received on 2026-08-14; no separate incoming-inspection pass is planned. SP-100 is
  **SUS304**; RH-100 used the **±0.05 tier** for the measured-bore pilot fit.
- **Arrived 2026-08-01**: GL100 motor, the full Accu fastener set, Titen HD anchors,
  DigiKey 374750597 (salesorder 100668200). Measured: axial 34.2–34.3 (nominal stands,
  stack derived), KD-100 t = 3.38 → SP-100 cross-hole Z136.6, bore Ø29.99–30.00 →
  pilot Ø29.85. All caliper-clearable fabrication gates closed (parts.md).
- **Design deltas this weekend** (all in parts.md): MR-100 caps deleted — epoxy is the
  retention; Hall sensor line moved to the standoff bisector ("150°", relational def
  controls); RH-100 blade stations owner-customized (released STEP is interface truth;
  blade root is owner-managed); BR-100 will be owner hand-fabbed, not designed in repo.
- **Consolidated DigiKey reorder received 2026-08-14**: **100888768**, 27 warehouse lines,
  CAD $200.98 after tax. It replaces cancelled orders **100616913** and **100723632**.
  Final quantities and four same-footprint substitutions are in `bom/README.md` and
  `bom.csv`; owner accepted the received order as complete.
- **BP-100 blade manufacturing and blade-root qualification are complete** (owner,
  2026-08-14). MEC-01/02/02B passed. Assembled rotor balance/runout remains open under
  MEC-05.
- **Build-critical procurement is closed.** Only two non-blocking loose `DMP6023LE-13`
  spares and optional SparkFun `15362` scope headers remain unsourced.
  M2 hardware and crimpers remain owner stock; BR-100 remains owner-fabbed/untracked. The
  other open loose end is the CubeMars bearing email (sent 2026-07-27, unanswered — chase
  or accept as Gate 01 residual risk).
- **MP-100 is installed on the ceiling** (owner-reported 2026-08-17), with all three ST-100
  standoffs and SP-100 spindle preinstalled. The two primary holes and primary plate mount
  are therefore complete. `INS-01` remains open until the installed anchor model,
  washer/spacer stack, spacing, embedment, and plate seating are recorded. Do not drill the
  tether hole yet: the plate clearance is ~105 mm from each primary, conflicting with
  install.md's >=190 mm anchor spacing, and the tether termination/routing is still open.
- **The 16-page printable integration binder is ready** at
  `output/pdf/stillair-integration-field-guides.pdf`, with editable source in
  `docs/field-guides/`. Sheets 0A through 6B cover the parallel electronics, ceiling,
  mechanical, firmware, qualification, installation, and sign-off tracks. Unreleased work
  is explicitly marked HOLD.

## Next

Work from [integration.md](integration.md). Ceiling preparation and primary plate mounting
are complete. Electronics is the main dependency spine; the immediate checkpoint is both
boards populated and PCB-01 passing its first no-motor power/safety checks. Mechanical
fit-up and firmware/test preparation can continue in parallel; do not stack the motor or
rotor onto the installed plate before the required off-ceiling proof work.

## Candidates Not Chosen

- **EB-100 PCB-bracket CAD** — wait until PCB-01's omitted connectors are populated so the
  bracket and cable bends are designed around physical geometry; pairs naturally with the
  owner's BR-100 hand-fab.
- **TEMP_SENSE firmware** — hardware complete; still parked with `TODO(temp-sense)` in
  `app/src/matter.rs`.
- **Rotor balance/runout** — blade manufacturing and qualification passed; MEC-05 remains
  before any powered rotor run.

## Learned Recently

- **Canada distributor terms + placed consolidated order** (DigiKey CAD is DDP; USD is
  CPT; 100888768 has 27 immediate lines after trimming contingency spares, four
  substitutions, two pins) → bom/README.md, bom.csv.
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
- **All remaining arrivals + BP-100 manufacturing completion** → STATE.md, bom/README.md,
  bom.csv, parts.md, blade-v2.md.
- **Integration dependency map + energy-sized work menu; ceiling approval/template and
  tether-spacing conflict** → integration.md, install.md.
- **Printable field-guide review** surfaced and recorded the loaded-rotor MPET requirement,
  unverified golden-image gate, proof-procedure and tether holds, SUS304 SP-100 truth,
  M3 cable-clamp taps, 10 nF C31 delay capacitor, and 30-second tach settling requirement
  → field-guide binder plus integration.md, parts.md, electrical.md, install.md, and the
  test matrix.
- **Ceiling plate installed** (owner, 2026-08-17): MP-100 is on the slab with the three
  ST-100 standoffs and SP-100 spindle in place; tether drilling/termination and the detailed
  `INS-01` installation record remain open → integration.md, install.md.
