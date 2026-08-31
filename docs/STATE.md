# State

Fast-moving work state and chosen next step. Durable findings live in the linked design,
commissioning, BOM, and test documents.

Last updated: **2026-08-31** (PCB-01 V2 submission package completed.)

## Now

- **PCB-01 V2 is provisionally ready to order from JLCPCB.** Routing, zone fill, production
  silkscreen, assembly metadata, and the generated submission package are complete. ERC is zero;
  schematic parity is 159 refs, 78 nets, and 411 endpoints; the probe map covers 31 test points and
  four connectors; DRC has zero active violations and zero unconnected items with 21 exact
  UUID-bound reviewed exceptions. See [pcb-01-v2.md](pcb-01-v2.md) and the
  [board README](../pcb/pcb-01-v2/README.md).
- **The release package is in `pcb/pcb-01-v2/fab/`.** It contains the 14-file Gerber/drill ZIP,
  55-group machine BOM, exact 119-reference top-side CPL, six-reference hand manifest, POFV and
  impedance attachments, placement/orientation guides, release hashes, and the complete
  [JLCPCB ordering checklist](../pcb/pcb-01-v2/fab/ORDERING.md). Four rounds of three complete
  adversarial reviews converged with no remaining useful finding.
- **The order uses JLC's current `JLC041621-7628` build and a 97 ohm USB target.** The routed
  0.20/0.20 mm pairs calculate to 96.85 ohm, inside the USB 2.0 tolerance. Twelve U1 pad-41 holes
  require explicit epoxy-filled and copper-capped POFV; U3 pads 4/5 retain their submitted
  solder-mask-defined apertures. Production-file confirmation is mandatory for these three quoted
  requirements.
- **V2 commissioning uses native USB only.** GPIO12/13 carry D-/D+ through J4; GPIO16/17 are
  unconnected. BOOT plus RESET provides deterministic ROM recovery. The first article still
  requires USB enumeration, ROM-download, flash, reboot, and runtime CLI qualification. See
  [controls.md](controls.md#commissioning-interface-and-build-policy).
- **The installed fan retains its provisional 50-170 RPM loaded release.** Final source-level
  tuning remains deferred until a communicating controller is installed. Evidence and the saved
  future objective are in [loaded-tuning-2026-08-21.md](../testing/loaded-tuning-2026-08-21.md)
  and [final-loaded-tuning-goal.md](../testing/final-loaded-tuning-goal.md).

## Next

Physically count the board-only hand stock listed in `fab/ORDERING.md`, regenerate the package once
immediately before upload, and place the JLCPCB order for five boards with two top-side Standard
PCBAs. Turn automatic substitutions off, request Confirm Parts Placement, attach the POFV and USB
files, and do not approve production until JLC's CAM output confirms all twelve POFV holes, both U3
mask-defined pads, the 97 ohm USB requirement, and every critical orientation.

## Candidates Not Chosen

- **Retrace USB for nominal 90 ohm:** rejected. JLC's live stack calculates the existing short
  full-speed pair at 96.85 ohm, safely inside the USB 2.0 90 ohm +/-15% range.
- **Have JLC populate the tall connectors, bulk capacitors, or LM2907:** rejected. C1, C2, J1, J2,
  J3, and U8 remain the exact six hand-installed references.
- **Resume loaded tuning now:** deferred until the assembled V2 controller communicates with the
  installed fan.

## Learned Recently

- Final V2 order settings, live-part constraints, hand inventory, CAM approvals, and placement
  checks: [ORDERING.md](../pcb/pcb-01-v2/fab/ORDERING.md).
- Exact POFV, mask, stack, impedance, routing, and reviewed DRC authority:
  [pcb-01-v2.md](pcb-01-v2.md) and [pcb-01-v2/README.md](../pcb/pcb-01-v2/README.md).
- Native-USB decision and first-article qualification gate:
  [pcb-01-v2-service-interface-review.md](pcb-01-v2-service-interface-review.md) and
  [controls.md](controls.md#commissioning-interface-and-build-policy).
