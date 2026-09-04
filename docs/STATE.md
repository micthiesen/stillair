# State

Fast-moving work state and chosen next step. Durable findings live in the linked design,
commissioning, BOM, and test documents.

Last updated: **2026-09-03** (JLCPCB impedance proposal received; clarification required.)

## Now

- **PCB-03 is ordered from JLCPCB as W2026090305011104 for $17 shipped.** The order is five bare
  39.75 x 21.00 mm boards plus a top-side stencil. The bridge is ERC-clean, DRC-clean, and fully
  routed with a filled B.Cu AGND plane. The three retained display/bridge checks in
  [pcb-03.md](pcb-03.md) are now first-article validation gates, not order blockers. The main unknown
  is whether the display accepts a 5000-byte RAM write split across SC18IS606 chip-select cycles.
- **PCB-03 hand-assembly parts are ordered from DigiKey as 101388939.** The exact SC18IS606PWJ is
  backordered with stock expected 2026-10-02; there is no validated drop-in substitute. The order
  intentionally excludes the host connector, e-paper display, and PH contacts already in stock.
  Increased spare quantities are recorded in [bom.csv](../bom/bom.csv).
- **The PCB-03 display is ordered from AliExpress as 8213753300045333.** Verify on arrival that it
  is the black/white Waveshare 1.54-inch 200 x 200 V2 module, identified as HINK-E0154A05 /
  WFC0000CZ07, before running the first-article gates.
- **JLCPCB support accepted the PCB-03 paste-layer addition.** The initially uploaded bare-board
  ZIP did not contain `F.Paste`; support confirmed they would add the supplied top-side paste layer
  to order `W2026090305011104` for its stencil.
- **PCB-01 V2 is ordered from JLCPCB as W2026083117295494.** The order is five 88 x 64 mm
  boards with two top-side Standard PCBAs. The release package remains in
  `pcb/pcb-01-v2/fab/`; routing, ERC, DRC, production silkscreen, BOM/CPL, and four rounds of
  three complete adversarial reviews were clean before submission.
- **JLCPCB's returned USB impedance proposal is not ready to approve.** Eira confirmed on
  2026-09-04 that the simulation uses adjacent plane L2 and 2 oz outer / 1 oz inner copper, clearing
  those questions. Engineering could not locate the third J4-to-U13 geometry. A fresh read of the
  released board and matching Gerbers confirms the two 3.170 mm, 0.200 mm F.Cu runs exist at
  x=111.250 and x=112.750 mm, giving 1.500 mm center spacing and 1.300 mm copper-edge gap. Send the
  marked crop and require its production geometry and Si9000e result before approval.
- **Production approval remains gated on JLCPCB's returned files.** Do not approve until CAM and
  placement output explicitly preserves all twelve U1 epoxy-filled and copper-capped POFV holes,
  U3 pads 4/5 solder-mask-defined apertures, the 97 ohm USB requirement, finished 88 x 64 mm
  outline, and every critical orientation listed in
  [ORDERING.md](../pcb/pcb-01-v2/fab/ORDERING.md).
- **All hand-population parts for both V2 PCBAs are ordered from DigiKey as 101316601.** The
  no-stock-assumption order contains four `EEU-FR1H471` capacitors and two each of
  `43045-0200`, `43650-0300`, `B3B-PH-K-S(LF)(SN)`, and `LM2907M/NOPB`.
- **The V1 USB quality complaint remains with JLCPCB support.** One assembled V1 board works over
  native USB, while the affected board never produces an attach event despite valid rails,
  boot-mode tests, connector reflow, and no USB-line short. Support received the schematic and
  electrical findings; destructive removal of the hidden-pad U2 module was declined.
- **V2 commissioning starts only after delivery and hand population.** The first article must pass
  native-USB enumeration, ROM download, flash, reboot, runtime CLI qualification, and the retained
  commissioning matrix before installation or loaded tuning.

## Next

Send Eira the marked J4-to-U13 crop and request its production geometry and Si9000e result. Then
review the revised calculation, final engineering DFM, and later parts-placement output against
every gate in
[ORDERING.md](../pcb/pcb-01-v2/fab/ORDERING.md). Approve production only when the returned outputs
and written confirmations are complete.

## Candidates Not Chosen

- **Approve JLCPCB production without inspecting returned files:** rejected. POFV, the U3 mask
  apertures, controlled impedance, and placement orientation are fabrication-dependent properties
  that the submitted design files alone cannot prove the factory retained.
- **Begin V2 commissioning before the orders arrive:** impossible. Commissioning requires one
  completed PCBA with C1, C2, J1, J2, J3, and U8 installed.
- **Resume final loaded tuning on V1:** deferred. The retained 50-170 RPM release remains valid;
  source-level tuning resumes after a communicating V2 controller is installed.

## Learned Recently

- PCB-03 architecture, connector pinout, firmware contract, final routed geometry, ordering
  checklist, and first-article validation gates: [pcb-03.md](pcb-03.md),
  [pcb-03/placement](../pcb/pcb-03/placement/), and
  [PCB-03 ORDERING.md](../pcb/pcb-03/fab/ORDERING.md).
- Final V2 order settings, live-part constraints, hand inventory, CAM gates, and placement checks:
  [ORDERING.md](../pcb/pcb-01-v2/fab/ORDERING.md).
- JLCPCB and DigiKey order identifiers and purchase status: [bom.csv](../bom/bom.csv) and
  [bom/README.md](../bom/README.md).
- Exact POFV, mask, stack, impedance, routing, and reviewed DRC authority:
  [pcb-01-v2.md](pcb-01-v2.md) and [pcb-01-v2/README.md](../pcb/pcb-01-v2/README.md).
- Native-USB first-article qualification gate:
  [controls.md](controls.md#commissioning-interface-and-build-policy).
