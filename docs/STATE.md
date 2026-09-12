# State

Last updated: **2026-09-12** (shared handoff pad preservation; hardware status unchanged).

## Now

- **PCB-01 V2's PCB file is confirmed; the assembly DFM passes review.** The live order page
  confirms PCB approval. All 119 factory parts match the release, and IC pin 1, diode bands,
  transistor orientation, connector direction, and placement pass. Library-origin differences
  for U2/U3/J4 were resolved geometrically. Michael may confirm assembly; that approval is not
  yet reported. See [placement-review/README.md](../pcb/pcb-01-v2/fab/placement-review/README.md).
  Chian's explicit U1 POFV confirmation and CAM checks remain in
  [production-review/README.md](../pcb/pcb-01-v2/fab/production-review/README.md).
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

Michael may reply to JLCPCB confirming the reviewed polarity/placement DFM for
`SMT026083161536_Y8`. Then await production/delivery and perform hand population and first-article
qualification under [ORDERING.md](../pcb/pcb-01-v2/fab/ORDERING.md).

Both the factory's POFV process confirmation and intended assembly placement now have retained
evidence. Recheck only if a later revision changes the reviewed data; hardware qualification still
requires the delivered boards.

## Candidates Not Chosen

- **Repeat the impedance clarification:** answered by revised calculations and CAM metadata;
  revisit only if the relevant geometry, copper, or stack changes.
- **Repeat the POFV request:** Chian explicitly confirmed all three requested process details.
- **Begin V2 commissioning or resume loaded tuning now:** delivery, hand population, and a
  communicating qualified V2 controller are prerequisites.

## Learned Recently

- Crystal Shim's shared handoff review corrected repeated physical-pad net assignment
  and parity checking. All 30 handoff tests pass, and native USB augmentation preserves
  all four shell connections. Existing released boards were not changed. See
  [pcb-workflow.md](pcb-workflow.md).
- CAM evidence, checks and their limits, download recovery, and submitted POFV request:
  [production-review/README.md](../pcb/pcb-01-v2/fab/production-review/README.md).
- Revised three-section USB calculations and copper/reference confirmation:
  [PCB-01 V2 ORDERING.md](../pcb/pcb-01-v2/fab/ORDERING.md).
- PCB-03 shipment and stencil status: [PCB-03 ORDERING.md](../pcb/pcb-03/fab/ORDERING.md).
- PCB authority, handoff and ECO rules: [pcb-workflow.md](pcb-workflow.md).
- Orders, backorders, and inventory: [bom.csv](../bom/bom.csv) and [bom/README.md](../bom/README.md).
