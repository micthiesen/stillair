---
name: kicad-manufacture
description: "Generate and validate downstream KiCad fabrication outputs for a Stillair board. Use for Gerbers, drill, JLCPCB, BOM/CPL, assembly files, production export, or ordering."
---

# KiCad fabrication

Fabrication begins only after the `/pcb` routed-KiCad review passes. For a tscircuit-first board,
also require current source-to-KiCad parity and every required `design/kicad-augment.json` item to
be implemented and verified.

Use `python3 pcb/tools/jlc_fab.py <board>` from the repository root. The board profile in that script
defines expected layers, assembly mode, DNP/no-part/hand-solder sets, LCSC policy, and output path.
Add or review a board profile rather than copying the script. Keep board-specific exceptions narrow
and documented.

Before export:

- save the KiCad project and refill zones;
- run the board's ERC/DRC path and account for only exact reviewed waivers;
- confirm zero unconnected items;
- verify outline, drills, stackup/copper, impedance requirements, mask/paste exceptions, special
  vias, critical orientations, and component side;
- verify the configured Gerber layer set and assembly split against the current order contract.

After export, inspect the archive contents, drill tool table, board/copper renders, BOM/CPL, and
release manifest. The fab house's live quote and DFM output are authority for current capabilities
and prices. Recheck current rules before ordering; do not use retained generic minimum tables as a
substitute.

Do not use Konnect's manufacturing package or validator. They have produced structurally wrong
outputs and false-ready reports on these KiCad 10 projects. `kicad-cli`, the project scripts, and
artifact inspection are the release path.

On the JLCPCB order page, confirm placement for every assembled design, check pin 1 and polarity in
the preview, and review returned CAM/engineering output against the board's ordering document before
approval.
