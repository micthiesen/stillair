---
name: konnect
description: "Route Stillair KiCad work through its supported Konnect, project-script, or GUI path. Use for schematic, PCB, library, or .kicad_* tasks; read /pcb for board work."
---

# Konnect — Operating Rules

## Authority And Safe Channels

**Read `/pcb` before board work.** It records the operations Konnect corrupts on KiCad 10 and the
project scripts that safely make narrow board edits with KiCad closed. Use Konnect for supported
schematic and library operations, those named scripts for their documented transformations, and
KiCad's GUI for project settings and schematic-to-board sync.

Do not make ad hoc textual edits to KiCad object graphs. A project script is allowed only for the
file and transformation it explicitly validates.

## Protected Files — NEVER Edit Directly

- `*.kicad_sch` — schematic sheets
- `*.kicad_pcb` — PCB layout
- `*.kicad_pro` — project configuration
- `*.kicad_sym` / `*.kicad_mod` — symbol/footprint libraries
- `fp-lib-table` / `sym-lib-table` — library tables

Route these files according to `/pcb`; do not assume Konnect supports every operation.

## The Three Channels

### Channel 1: Supported writes

Prefer Konnect when it exposes a safe operation. Use `/pcb` scripts for their named board
transformations and the GUI for project settings or operations the MCP cannot perform safely. If
Konnect is unavailable, continue independent analysis or GUI work and ask for help only when the
remaining operation truly requires it.

### Channel 2: Exported netlists/BOMs (for reads and analysis)

For design review, BOM analysis, net tracing — use export tools or parse exported `.net`/BOM/CSV files, not the source files directly.

### Channel 3: Read-only file inspection (last resort)

Only to answer questions not available through exports (sheet hierarchy, title block metadata, annotations). Read with file-reading tools, but never modify.

## Standard Workflow

1. **Identify the project** — locate the `.kicad_pro` file
2. **Classify the task** — query/export, supported Konnect write, `/pcb` script, or GUI
3. **Load only the toolset needed** when using Konnect
4. **Execute** through the selected safe channel
6. **Verify** — re-query the design to confirm the change landed correctly

## Decision Tree

| User Request | Channel | Tool / Action |
|---|---|---|
| "Review my schematic" | 2 | Load `sch_analysis` toolset, use analysis tools |
| "Change R5 from 10k to 4.7k" | 1 | `load_toolset("sch_components")` then `edit_schematic_component` |
| "What's connected to SCL?" | 2 | `load_toolset("sch_analysis")` then `get_net_connections` |
| "Add a 100nF cap to U3 VCC" | 1 | `load_toolset("sch_components")` + `load_toolset("sch_wiring")` |
| "Rename net /CLK to /SYS_CLK" | 1 | Warn about downstream effects, then MCP tools |
| "Run DRC" | `/pcb` | Headless `kicad-cli` DRC against the waiver baseline |
| "Export Gerbers" | `/kicad-manufacture` | Run the project fabrication script |
| "Just patch line 247 of the .kicad_sch" | REFUSE | Explain risks, offer MCP alternative |
| "Add ESD protection to USB lines" | 1 | `load_toolset("sch_components")` + `load_toolset("sch_wiring")` |
| "Check if board is ready for fab" | `/pcb` + `/kicad-manufacture` | Headless DRC and project fab checks |

## KiCAD 10 IPC API Reality

**PCB Editor (pcbnew):** Full CRUD via NNG + protobuf. Real-time communication with running KiCAD instance. Create, read, update, delete any PCB item with immediate UI refresh. **Requires KiCAD to be running.**

**Schematic Editor (eeschema):** No item-level IPC API. Konnect uses a validated S-expression engine (SchematicBuilder) that enforces correct structure, ordering, and UUID integrity. File-based — **does not require KiCAD to be running.**

**Symbol/Footprint Libraries:** No IPC API. Edited through Konnect's S-expression engine with full validation.

**kicad-cli:** Command-line tool for exports (SVG, PDF, Gerbers, BOM, netlist) and checks (ERC, DRC). Does not require KiCAD GUI.

## Discovery — Finding Available Tools

Konnect uses a meta-tool router pattern with 185 tools across 18 toolsets. Tools are loaded on demand to keep the context focused.

```
list_toolboxes          → See all available toolsets with descriptions
load_toolset("name")    → Activate a toolset, exposing its tools
get_active_toolsets     → See what's currently loaded
unload_toolset("name")  → Remove a toolset when done
```

### Available Toolsets

| Category | Toolsets |
|----------|----------|
| Project | project |
| Schematic | sch_components, sch_wiring, sch_analysis, sch_batch, sch_export, sch_hierarchy |
| PCB | pcb_board, pcb_components, pcb_routing, pcb_export |
| Library | library |
| Integration | integration (JLCPCB parts, Freerouting, datasheets) |
| Verification & Review | verification, design_review |
| Config | config |
| Templates | templates |
| Manufacturing | manufacturing |

## Design Rules Quick Reference

| Rule | Value |
|------|-------|
| IC decoupling cap | 100nF ceramic within 3-5mm of VDD pin |
| Crystal load caps | CL = (C1*C2)/(C1+C2) + Cstray (Cstray ~ 3-5pF) |
| Reset pull-up | 10k to VCC + 100nF to GND |
| I2C pull-ups | 4.7k (standard), 2.2k (fast), 1k (fast+) — one set per bus |
| LED resistor | R = (VCC - Vf) / If |

## Common Library IDs

| Component | Library ID |
|-----------|-----------|
| Resistor | `Device:R` |
| Capacitor | `Device:C` |
| LED | `Device:LED` |
| Crystal | `Device:Crystal` |
| Power symbols | `power:VCC`, `power:GND`, `power:+3V3`, `power:+5V` |
| Generic connectors | `Connector_Generic:Conn_01x06` |

## Tool Usage Pattern

```
1. list_toolboxes                          → discover what's available
2. load_toolset("sch_components")          → activate component tools
3. add_schematic_component (repeat)        → place parts
4. load_toolset("sch_wiring")              → activate wiring tools
5. connect_pins / add_wire / add_schematic_net_label → wire the circuit
6. load_toolset("verification")            → activate checks
7. run_erc / run_design_review             → validate the design
```

## Refusing Direct Edits

When a request calls for an ad hoc edit outside the supported channels, explain the concrete file
integrity risk and use the nearest supported Konnect, script, or GUI operation. The original request
already authorizes that equivalent repository change.
