# State

Fast-moving work state and chosen next step. Durable findings live in the linked design,
commissioning, BOM, and test documents.

Last updated: **2026-08-31** (PCB-01 V2 and hand-population parts ordered.)

## Now

- **PCB-01 V2 is ordered from JLCPCB as W2026083117295494.** The order is five 88 x 64 mm
  boards with two top-side Standard PCBAs. The release package remains in
  `pcb/pcb-01-v2/fab/`; routing, ERC, DRC, production silkscreen, BOM/CPL, and four rounds of
  three complete adversarial reviews were clean before submission.
- **Production approval is still gated on JLCPCB's returned files.** Do not approve until CAM and
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

Review every JLCPCB CAM, DFM, parts-placement, or support response against the exact approval gates
in [ORDERING.md](../pcb/pcb-01-v2/fab/ORDERING.md). Approve production only when those outputs are
correct, then wait for JLCPCB order `W2026083117295494` and DigiKey order `101316601` to arrive.

This is the only remaining pre-delivery action because the design, submission package, assembly
part set, and orders are complete.

## Candidates Not Chosen

- **Approve JLCPCB production without inspecting returned files:** rejected. POFV, the U3 mask
  apertures, controlled impedance, and placement orientation are fabrication-dependent properties
  that the submitted design files alone cannot prove the factory retained.
- **Begin V2 commissioning before the orders arrive:** impossible. Commissioning requires one
  completed PCBA with C1, C2, J1, J2, J3, and U8 installed.
- **Resume final loaded tuning on V1:** deferred. The retained 50-170 RPM release remains valid;
  source-level tuning resumes after a communicating V2 controller is installed.

## Learned Recently

- Final V2 order settings, live-part constraints, hand inventory, CAM gates, and placement checks:
  [ORDERING.md](../pcb/pcb-01-v2/fab/ORDERING.md).
- JLCPCB and DigiKey order identifiers and purchase status: [bom.csv](../bom/bom.csv) and
  [bom/README.md](../bom/README.md).
- Exact POFV, mask, stack, impedance, routing, and reviewed DRC authority:
  [pcb-01-v2.md](pcb-01-v2.md) and [pcb-01-v2/README.md](../pcb/pcb-01-v2/README.md).
- Native-USB first-article qualification gate:
  [controls.md](controls.md#commissioning-interface-and-build-policy).
