---
name: kicad-schematic
description: Capture or edit Stillair KiCad schematics through supported Konnect tools. Use for symbols, wiring, labels, power rails, annotation, and schematic validation.
argument-hint: "[circuit description or task]"
---

# KiCad Schematic Work

Use Konnect for schematic writes; do not hand-edit `.kicad_sch`. Read `/pcb` first for board-level
work because it owns the full capture, review, and schematic-to-board flow.

Load only the needed schematic and library toolsets. Search for the exact part, inspect its pin map,
and verify pin numbers against the datasheet before wiring. Place related blocks together, use named
net labels for shared signals, and use KiCad power symbols for rails. Keep symbols and wire endpoints
on the 1.27 mm schematic grid so connections serialize and validate correctly.

Batch repeated operations only when every item has the same shape. Use individual operations where
position, pin mapping, or connectivity differs. Preserve `docs/electrical.md`, `bom/bom.csv`, and
the design invariants in `CLAUDE.md`; update the owning evidence with any intentional substitution.

Save the project at stable milestones. After edits, annotate changed references, validate connections, find orphan items, shorts, and
suspicious single-pin nets, then run ERC. Re-query changed nets and components. A deliberate
exception needs a concrete rationale in maintained docs or waivers. For schematic-to-board updates,
follow `/pcb` and [`../pcb/references/kicad-gui.md`](../pcb/references/kicad-gui.md) for the F8 GUI step.
