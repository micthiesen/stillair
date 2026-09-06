---
name: konnect
description: "Safety rules for downstream work on an existing KiCad project: handoff/ECO application, routing, zones, DRC, fabrication, or any mutation of .kicad_* files. Tscircuit authoring alone does not trigger this skill."
---

# Safe KiCad mutation

KiCad files are serialized object graphs with UUIDs and cross-references. Never modify
`*.kicad_sch`, `*.kicad_pcb`, `*.kicad_pro`, `*.kicad_sym`, `*.kicad_mod`, `sym-lib-table`, or
`fp-lib-table` with text manipulation.

The only allowed write channels are:

1. the pinned tscircuit exporter creating a new initial seed in a staging directory;
2. KiCad GUI;
3. a verified Konnect operation;
4. KiCad's native API, followed by saving through KiCad.

After initial adoption, never export over the production board. Tscircuit changes become an ECO
plan and are applied through channels 2 through 4. A board-specific script that rewrites KiCad text
is historical migration code, not an allowed channel.

Prefer `kicad-cli` exports or semantic snapshots for reads. Read source files directly only when an
export cannot answer the question, and never write them.

For each write:

1. identify the exact project and confirm the source handoff/ECO plan;
2. snapshot KiCad-owned geometry and rules when routes exist;
3. apply only the declared operation;
4. re-query the saved design;
5. verify source parity, preserved route/zone/rule state, ERC/DRC, and renders as appropriate.

Konnect availability does not make every operation safe. Use only operations already verified on
the installed KiCad/Konnect versions. Use the KiCad GUI when project settings or an MCP operation is
unreliable. Never use Konnect's manufacturing validator or manufacturing-package exporter for a
release decision.
