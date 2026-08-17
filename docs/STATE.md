# State

Fast-moving work state and chosen next step. This records the work, not machine state or
uncommitted changes. Durable findings live in the linked docs.

Last updated: **2026-08-17** (owner simplified the remaining integration scope; ceiling
installation, tether, and catcher work are complete or owner-managed.)

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
- **Build-critical procurement is closed.** Two loose `DMP6023LE-13` spares and optional
  SparkFun `15362` scope headers are not active work. M2 hardware and crimpers remain owner
  stock; BR-100 remains owner-fabricated and untracked. Do not reopen procurement,
  incoming inspection, or CubeMars correspondence unless Michael explicitly asks.
- **MP-100 ceiling installation is complete** (owner-reported 2026-08-17), with all three
  ST-100 standoffs and SP-100 spindle installed. `INS-01` is accepted as passed against the
  documented stack. The tether and central catcher tests are also owner-reported passes
  (`INS-02`, `MEC-04`). Michael owns all remaining installation work; do not plan, suggest,
  audit, or prompt for ceiling installation, tether, or catcher work.
- **The streamlined printable integration binder is ready** at
  `output/pdf/stillair-integration-field-guides.pdf`, with editable source in
  `docs/field-guides/`. It covers only the active electronics, mechanical integration,
  firmware, balance, guarded proof-speed, representative-start, and thermal tracks.

## Next

Work from [integration.md](integration.md). Electronics is the main dependency spine; the
immediate checkpoint is both boards populated and PCB-01 passing its first no-motor
power/safety checks. Then complete motor integration, balance, controller tuning, essential
hardware safety checks, guarded proof speed, representative starts, and the thermal run.

## Candidates Not Chosen

- **EB-100 PCB-bracket CAD** — wait until PCB-01's omitted connectors are populated so the
  bracket and cable bends are designed around physical geometry; pairs naturally with the
  owner's BR-100 hand-fab.
- **Rotor balance/runout** — blade manufacturing and qualification passed; MEC-05 remains
  before any powered rotor run.

## Future Only On Explicit Request

Do not suggest, schedule, or use these as blockers unless Michael explicitly asks to resume
one: ENC-100 cosmetic housing, TEMP_SENSE firmware, intentional-imbalance testing,
exhaustive start matrices, exhaustive acoustic testing, network/Matter resilience testing,
and exhaustive fault permutations. Installation, tether, and catcher work are owner-managed
and must not be surfaced as project tasks.

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
- **Scope simplification** (owner, 2026-08-17): MP-100 installation, tether proof, and
  catcher proof accepted complete; remaining installation is owner-managed. Cosmetic
  housing, TEMP_SENSE, imbalance, and exhaustive test variants are future-only and must not
  be prompted → integration.md, install.md, decisions.md, test matrix, field-guide binder.
