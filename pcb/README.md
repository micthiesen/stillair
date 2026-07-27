# PCB

KiCad project for the 78 × 58 mm V1/V2 controller board (schematic capture, layout, fab
outputs). Not started yet; the complete circuit-level handoff (outline, schematic blocks,
starting values, pinouts, placement zones, layer plan, test points) is
[../docs/electrical.md](../docs/electrical.md), and the V1-to-V2 gate list is at the bottom
of that doc.

Fabrication is planned through JLCPCB; JLCPCB assembly vs hand-population is TBD (prefer
footprints/parts in the LCSC catalog where it doesn't compromise the design, so the PCBA
option stays open). The Hall daughterboard (18 × 8 mm, DRV5033) is a second tiny board that
should ride in the same order/panel. A possible V2 reshape to a horizontal donut board is
noted in the handoff doc.
