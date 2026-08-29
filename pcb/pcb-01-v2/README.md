# PCB-01 V2 KiCad project

Fresh, intentionally unpopulated KiCad project for the PCB-01 V2 controller. The frozen capture and
layout authority is [`docs/pcb-01-v2.md`](../../docs/pcb-01-v2.md). Do not copy V1 placement,
routing, zones, outline, mounting coordinates, probe map, or DRC waivers into this project.

The reusable project setup is complete:

- 4-layer, 1.6 mm stackup: 2 oz outer copper, 1 oz inner copper, with In1.Cu and In2.Cu
  classified as power-plane layers.
- Board minimums: 0.20 mm clearance and track width, 0.60/0.30 mm via, 0.30 mm
  copper-to-hole clearance, and 0.25 mm copper-to-edge clearance.
- Default net class: 0.20 mm clearance and track width, 0.60/0.30 mm via.
- Project symbol fields: `MPN`, `LCSC`, `Note`, and `DNP`.
- Empty project-local `pcb01-v2-parts` symbol and footprint libraries are registered.

The schematic, outline, holes, components, nets, placement, and routing remain intentionally empty.

Konnect project rules are committed in `.konnect/project.json`. A new Codex task started from this
repository loads the project-scoped Konnect server from `.codex/config.toml`; Claude Code uses the
same server through the repository `.mcp.json`.

The agent can create and edit the complete schematic, assign footprints, validate ERC, generate and
compare netlists, launch KiCad, place and move board footprints through IPC, render the board, run
headless DRC with schematic parity, and review the saved design. KiCad 10.0.4 and Konnect 0.2.1 do
not expose a headless Update PCB from Schematic operation, but the agent can operate F8 through the
KiCad GUI. Open `pcb-01-v2.kicad_pro`, launch the Schematic Editor from the project manager's
**Tools** menu or large button, then minimize the project-manager window so yabai gives the editor
the full tile. After each schematic change that affects the board, run **Tools > Update PCB from
Schematic (F8)** in the project-owned Schematic Editor, apply the update, and save before continuing
board placement. Do not launch a `.kicad_sch` or `.kicad_pcb` file directly: that creates a
stand-alone editor and breaks the project bridge.

Codex can perform this GUI workflow directly with its approved macOS permissions. Verify the final
window state with:

```bash
python3 pcb/tools/kicad_window_state.py pcb/pcb-01-v2/pcb-01-v2.kicad_pro
```
