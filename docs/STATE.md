# State

Last updated: **2026-09-14** (V1 credit-request draft approved and copied; session wrapped).

## Now

- **PCB-01 V2 is in production, per Michael's 2026-09-14 report.** Five boards and two top-side
  Standard PCBAs are on JLCPCB W2026083117295494; hand parts are on DigiKey 101316601.
  The prior assembly DFM passed review, and the factory's POFV confirmation is retained.
  See [ORDERING.md](../pcb/pcb-01-v2/fab/ORDERING.md),
  [placement review](../pcb/pcb-01-v2/fab/placement-review/README.md), and
  [production review](../pcb/pcb-01-v2/fab/production-review/README.md).
- **V1's USB complaint remains open.** Paul is checking repair feasibility and offered covered
  repair/shipping/duties if feasible. Michael prefers credit or a discount against V2 without
  returning V1. Michael approved the [reply draft](jlcpcb-v1-credit-request.md), which was copied
  to his clipboard and verified. Sending is not confirmed; no repair or credit is agreed.
  Complaint evidence and the latest offer are in [bom/README.md](../bom/README.md).
- **PCB-03 boards and stencil have shipped; parts and display remain pending.** Shipping and the
  accepted paste-layer addition are in [PCB-03 ORDERING.md](../pcb/pcb-03/fab/ORDERING.md).
  DigiKey 101388939 includes the backordered SC18IS606PWJ; AliExpress display order is
  8213753300045333. Retain the first-article gates in [pcb-03.md](pcb-03.md).
- **New boards use the validated tscircuit-to-KiCad workflow.** Existing released boards remain
  KiCad-authoritative. The PCB-03 fixture is an initial handoff with declared downstream cleanup
  and routing work, not a fabrication-ready replacement. See [pcb-workflow.md](pcb-workflow.md).
- **V2 commissioning awaits delivery and hand population.** Native USB, ROM download, flash,
  reboot, runtime CLI, and commissioning checks precede installation and loaded tuning; see
  [controls.md](controls.md#commissioning-interface-and-build-policy).

## Next

Await V2 delivery, then perform hand population and first-article qualification under
[ORDERING.md](../pcb/pcb-01-v2/fab/ORDERING.md). This carries forward the existing delivery and
commissioning plan now that Michael reports production is underway.

Factory process and placement evidence is retained. Hardware qualification requires delivered
boards; the V1 complaint can proceed separately through the approved credit-request draft.
Michael has the draft on his clipboard; await his send confirmation or JLCPCB response before
recording further complaint progress.

## Candidates Not Chosen

- **Repeat the impedance clarification:** answered by revised calculations and CAM metadata;
  revisit only if the relevant geometry, copper, or stack changes.
- **Repeat the POFV request:** Chian explicitly confirmed all three requested process details.
- **Return V1 for repair:** Michael prefers credit toward V2; no return is authorized.
- **Begin V2 commissioning or resume loaded tuning now:** delivery, hand population, and a
  communicating qualified V2 controller are prerequisites.

## Learned Recently

- V1's conditional repair offer and missing U2 X-ray inspection: [bom/README.md](../bom/README.md).
- Exact approved credit request and verified clipboard handoff: [reply draft](jlcpcb-v1-credit-request.md).
- Owner-reported V2 production: [PCB-01 V2 ORDERING.md](../pcb/pcb-01-v2/fab/ORDERING.md).
- Shared native transactions, guarded schematic fields, preparation audits, and lifecycle helpers:
  [PCB tools](../pcb/tools/README.md); project adoption limits in [pcb-workflow.md](pcb-workflow.md).
- CAM and placement evidence: [production review](../pcb/pcb-01-v2/fab/production-review/README.md)
  and [placement review](../pcb/pcb-01-v2/fab/placement-review/README.md).
- Orders, backorders, and inventory: [bom.csv](../bom/bom.csv) and [bom/README.md](../bom/README.md).
