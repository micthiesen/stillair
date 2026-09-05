---
name: kicad-review
description: Review Stillair KiCad schematics and boards with the project's proven checks. Use for ERC, DRC, design audits, pre-fabrication review, and validation after fixes.
argument-hint: "[what to review]"
---

# KiCad Design Review

Read `/pcb` before reviewing a board. Konnect's schematic analysis is useful; its board DRC and
manufacturing validator are not authoritative on this KiCad 10 project.

For schematics, use supported Konnect analysis to check orphan items, shorts, suspicious single-pin
nets, ERC, decoupling, rails, connector pin maps, and protection. Compare the result with
`docs/electrical.md`, `bom/bom.csv`, and the safety invariants in `CLAUDE.md`. Treat a shorted rail,
wrong connector mapping, missing safety path, or output conflict as critical.

For boards, use the saved board and `/pcb`: extract fresh artifacts and renders, run
`kicad-cli pcb drc --format json --severity-all`, compare every class with
`pcb/<board>/placement/waivers.md`, inspect copper/edge/hole/antenna/grounding/phase-current and
connector-orientation issues individually, and run the named placement and geometry checks.

Do not use `get_drc_violations` or `validate_for_manufacturing` as a release verdict. They have
misread a routed four-layer board as empty and ready. Pre-fabrication review also uses
`/kicad-manufacture` and its generated BOM, CPL, and Gerber checks.

Classify findings as critical, warning, or suggestion by consequence. Name the affected reference,
net, layer, rule, and evidence. When review is part of authorized implementation, fix supported
issues and rerun checks. For review-only requests, report without changing the design. Never hide a
new error inside an old broad waiver.
