# State

Last updated: **2026-09-07** (production files downloaded; U1 POFV confirmation requested).

## Now

- **PCB-01 V2 awaits written U1 POFV confirmation.** Michael submitted the factory's
  confirmation/modification form. The CAM archive and targeted checks are retained in
  [production-review/README.md](../pcb/pcb-01-v2/fab/production-review/README.md). Outline, rails,
  impedance metadata, protected U3 mask apertures, and twelve U1 hole locations passed; epoxy
  filling/copper capping remains unconfirmed. Assembly placement is a separate later review.
- **PCB-01 V2 and hand-population parts are ordered.** Five boards and two top-side Standard PCBAs
  are on JLCPCB W2026083117295494; hand parts are on DigiKey 101316601. Release and approval
  requirements remain in [ORDERING.md](../pcb/pcb-01-v2/fab/ORDERING.md).
- **PCB-03 boards and stencil have shipped; parts and display remain pending.** Shipping and the
  accepted paste-layer addition are in [PCB-03 ORDERING.md](../pcb/pcb-03/fab/ORDERING.md).
  DigiKey 101388939 includes the backordered SC18IS606PWJ; AliExpress display order is
  8213753300045333. Retain exact display-revision, split-write chip-select, and reset-recovery
  first-article gates in [pcb-03.md](pcb-03.md).
- **New boards use the validated tscircuit-to-KiCad workflow.** Existing released boards remain
  KiCad-authoritative. The PCB-03 fixture is an initial handoff with declared downstream cleanup
  and routing work, not a fabrication-ready replacement. See [pcb-workflow.md](pcb-workflow.md).
- **V1's USB complaint remains open; V2 commissioning awaits delivery and hand population.**
  Complaint history is in [bom/README.md](../bom/README.md). Native USB, ROM download, flash,
  reboot, runtime CLI, and commissioning checks precede installation and loaded tuning; see
  [controls.md](controls.md#commissioning-interface-and-build-policy).

## Next

Review JLCPCB's reply to the submitted U1 POFV request and any revised production files, then
review the later parts-placement output using [ORDERING.md](../pcb/pcb-01-v2/fab/ORDERING.md).

The twelve holes are present, but explicit process confirmation is needed to establish epoxy
filling and copper capping. Preserve the checks already completed; a fee or generic order status
is not confirmation of the process. Production approval remains pending.

## Candidates Not Chosen

- **Repeat the impedance clarification:** answered by revised calculations and CAM metadata;
  revisit only if the relevant geometry, copper, or stack changes.
- **Approve based solely on hole presence or the extra fee:** neither establishes POFV treatment.
- **Begin V2 commissioning or resume loaded tuning now:** delivery, hand population, and a
  communicating qualified V2 controller are prerequisites.

## Learned Recently

- CAM evidence, checks and their limits, download recovery, and submitted POFV request:
  [production-review/README.md](../pcb/pcb-01-v2/fab/production-review/README.md).
- Revised three-section USB calculations and copper/reference confirmation:
  [PCB-01 V2 ORDERING.md](../pcb/pcb-01-v2/fab/ORDERING.md).
- PCB-03 shipment and stencil status: [PCB-03 ORDERING.md](../pcb/pcb-03/fab/ORDERING.md).
- PCB authority, handoff and ECO rules: [pcb-workflow.md](pcb-workflow.md).
- Orders, backorders, and inventory: [bom.csv](../bom/bom.csv) and [bom/README.md](../bom/README.md).
