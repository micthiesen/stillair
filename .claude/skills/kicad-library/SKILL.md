---
name: kicad-library
description: Create or update Stillair KiCad symbols, footprints, and project libraries through Konnect. Use for part searches, custom library items, pin mapping, footprint work, and library registration.
argument-hint: "[component or library task]"
---

# KiCad Library Work

Use Konnect's `library` toolset for library writes. Do not hand-edit `.kicad_sym`, `.kicad_mod`,
`sym-lib-table`, or `fp-lib-table`. Read `/pcb` as well when the part is entering a Stillair board.

Search installed symbol and footprint libraries first. Reuse an item when its pin numbers,
electrical types, package dimensions, and orientation match the exact datasheet. Create a custom
item only when those facts differ or the package is absent. A matching name alone is not evidence.

For a custom symbol, derive every pin number, name, type, and hidden power pin from the datasheet.
Include `Reference`, `Value`, `Footprint`, `Datasheet`, and known `MPN`/`LCSC` fields. Arrange the
symbol for review and mark pin 1.

For a custom footprint, use the recommended land pattern rather than a package estimate. Verify pad
numbers and physical orientation against the symbol. Include fabrication outline, courtyard,
silkscreen, reference, value, and a pin-1 mark. Check paste, mask, exposed-pad, thermal-via, slot,
and mounting-tab requirements explicitly. Use the KiCad/IPC footprint naming shape and a 0.25 mm
courtyard clearance unless the datasheet or assembly process requires more.

Use project scope for Stillair-specific libraries. Use global scope only for an intentionally shared
library. After writing, re-query the item and compare its pin/pad map and dimensions with the
datasheet. Confirm registration from the project. Report datasheet ambiguity instead of guessing.
