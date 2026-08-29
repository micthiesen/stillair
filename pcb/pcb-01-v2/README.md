# PCB-01 V2 KiCad project

Fresh, intentionally unpopulated KiCad project for the PCB-01 V2 controller. The frozen capture and
layout authority is [`docs/pcb-01-v2.md`](../../docs/pcb-01-v2.md). Do not copy V1 placement,
routing, zones, outline, mounting coordinates, probe map, or DRC waivers into this project.

Konnect project rules are committed in `.konnect/project.json`. A new Codex task started from this
repository loads the project-scoped Konnect server from `.codex/config.toml`; Claude Code uses the
same server through the repository `.mcp.json`.

The agent can create and edit the complete schematic, assign footprints, validate ERC, generate and
compare netlists, launch KiCad, place and move board footprints through IPC, render the board, run
headless DRC with schematic parity, and review the saved design. KiCad 10.0.4 and Konnect 0.2.1 do
not expose a headless Update PCB from Schematic operation. After each schematic change that affects
the board, use KiCad's **Tools > Update PCB from Schematic (F8)**, apply the update, and save before
continuing board placement.
