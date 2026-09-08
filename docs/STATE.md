# State

Last updated: **2026-09-07** (U1 POFV confirmed; reviewed PCB production file may be approved).

## Now

- **PCB-01 V2's outstanding U1 POFV question is cleared.** Chian explicitly confirmed epoxy
  filling/copper capping, the top aperture open, and no bottom openings, already included in the
  current production file. Michael intends to approve; actual approval is not yet reported.
  The CAM archive, factory confirmation, and targeted checks are retained in
  [production-review/README.md](../pcb/pcb-01-v2/fab/production-review/README.md). Outline, rails,
  impedance metadata, protected U3 mask apertures, and twelve U1 hole locations passed.
  Assembly placement is a separate later review.
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

Michael may approve the reviewed PCB production file. Review the later parts-placement output
using [ORDERING.md](../pcb/pcb-01-v2/fab/ORDERING.md).

The factory's explicit written confirmation now establishes the requested fill/cap process.
Preserve completed checks and assess any subsequently revised files against the retained archive.

## Candidates Not Chosen

- **Repeat the impedance clarification:** answered by revised calculations and CAM metadata;
  revisit only if the relevant geometry, copper, or stack changes.
- **Repeat the POFV request:** Chian explicitly confirmed all three requested process details.
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
