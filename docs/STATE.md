# State

Fast-moving work state and chosen next step. Durable findings live in the linked design,
commissioning, BOM, and test documents.

Last updated: **2026-08-30** (PCB-01 V2 handed off for manual routing.)

## Now

- **PCB-01 V2 is ready for manual routing.** The 88 x 64 mm native-USB board has 166 top-side
  footprints, the exact 78-net/411-endpoint ratsnest, four-layer rules, zones, keepouts,
  fiducials, silkscreen, probe map, and JLCPCB assembly metadata. ERC and parity pass. Pre-route
  DRC contains only 328 expected unconnected items and one expected isolated In2 3V3 warning.
  Four USB-focused and four holistic review rounds converged. See
  [pcb-01-v2.md](pcb-01-v2.md) and [pcb-01-v2/README.md](../pcb/pcb-01-v2/README.md).
- **Michael is routing PCB-01 V2 now.** The concise order, widths, vias, and completion checks are
  in the [interactive routing checklist](https://mcp.syas.ca/boris/artifacts/art_eon2bpkmslvmtf6wfpa).
  Michael is now routing by board context rather than following that artifact; do not update it.
  The assistant should answer specific routing questions against the saved KiCad project and its
  design rules, not reconstruct intent from memory. Do not start a checkpoint review until asked.
  At that review, inspect every ignored DRC item individually, including size findings: judge what
  physically fits and the actual electrical, clearance, and manufacturing requirement rather than
  accepting the ignore or enforcing the nominal class mechanically.
- **V2 commissioning uses native USB only.** GPIO12/13 carry D-/D+ through J4; GPIO16/17 are
  unconnected. BOOT plus RESET provides deterministic ROM recovery. The assembled first article
  still requires USB enumeration, ROM-download, flash, reboot, and runtime CLI qualification. See
  [controls.md](controls.md#commissioning-interface-and-build-policy).
- **The installed fan retains its provisional 50--170 RPM loaded release.** Final source-level
  tuning remains deferred until a communicating controller is installed. Evidence and the saved
  future objective are in [loaded-tuning-2026-08-21.md](../testing/loaded-tuning-2026-08-21.md)
  and [final-loaded-tuning-goal.md](../testing/final-loaded-tuning-goal.md).

## Next

Michael routes PCB-01 V2 in the order and widths in the interactive checklist. Preserve the
encoded rule areas and keepouts. After routing, refill zones and require zero unconnected items
and zero unexplained DRC violations using `python3 pcb/tools/check_drc.py`, then run
`python3 pcb/tools/jlc_fab.py pcb-01-v2` and inspect
the Gerbers, drill map, BOM, CPL, POFV notes, and assembly locator before ordering.

This is the shortest path to a fabrication-ready controller, and the exporter refuses to create
orderable Gerbers until the final DRC gate passes. Routing authority and checks are in
[pcb-01-v2/README.md](../pcb/pcb-01-v2/README.md).

## Candidates Not Chosen

- **Retain FTDI as a V2 backup:** rejected. It adds powered-off back-power and adapter/harness
  uncertainty without improving the ESP32-C6 ROM recovery path.
- **Resume loaded tuning now:** deferred until the routed V2 is assembled and communicating.
- **Install damping or the upper housing now:** deferred until the exposed controller tune is
  frozen, so passive treatment does not obscure source-level diagnosis.

## Learned Recently

- Ready-to-route V2 project, routing vocabulary, manufacturing gate, and repeated implemented-board
  reviews: [pcb-01-v2/README.md](../pcb/pcb-01-v2/README.md) and [pcb-01-v2.md](pcb-01-v2.md).
- Native-USB decision, recovery sequence, and first-article qualification gate:
  [pcb-01-v2-service-interface-review.md](pcb-01-v2-service-interface-review.md) and
  [controls.md](controls.md#commissioning-interface-and-build-policy).
- Repeatable `pcbnew` scripts use `pcb/tools/kicad_python.sh`; Konnect transport and KiCad Python
  recovery details live in the project [PCB skill](../.claude/skills/pcb/SKILL.md).
- Loaded-fan evidence and the deferred final-tuning contract:
  [loaded-tuning-2026-08-21.md](../testing/loaded-tuning-2026-08-21.md) and
  [final-loaded-tuning-goal.md](../testing/final-loaded-tuning-goal.md).
