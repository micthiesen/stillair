---
name: pcb
description: >
  Drive KiCad PCB work for the Stillair controller boards through the Konnect MCP server.
  Covers schematic capture from docs/electrical.md + bom/bom.csv, symbol/footprint sourcing,
  netlist/connection work, board setup and design rules, ERC/DRC, design review, and fab
  exports. Use whenever the task touches KiCad, Konnect, a .kicad_* file, the schematic, the
  board, footprints, ERC/DRC, or JLCPCB fabrication outputs. TRIGGER on "schematic", "kicad",
  "konnect", "PCB", "footprint", "ERC", "DRC", "gerber", "capture the board", "/pcb".
user_invocable: true
---

# PCB (KiCad + Konnect)

The controller board is captured in KiCad and driven by **Konnect**, an MCP server that
exposes 185 tools over the KiCad 10 project. This skill is the operating manual: who does
what, how to start a session, and the quirks we have paid for already.

> **Living document.** Konnect is young and the agent/human split is provisional. When you
> learn a quirk, a working recipe, or that a task turned out to be easier or harder than the
> split below assumes, edit this file in the same session. Do not ask first.

## Ground truth lives in the repo, not the board

The board is a *transcription* of a design that is already fully specified. Never invent a
value, a part, or a pin assignment at capture time — look it up:

| Question | Source |
|---|---|
| What circuit is this, what values, what pinout | [docs/electrical.md](../../../docs/electrical.md) — blocks SCH-01…SCH-07 |
| Which exact MPN, and is it ordered | [bom/bom.csv](../../../bom/bom.csv) |
| Where does the footprint/symbol come from | [pcb/README.md](../../../pcb/README.md) — sourcing notes |
| Mechanical envelope, holes, orientation | docs/electrical.md > "PCB-01 mechanical definition", docs/parts.md > EB-100 |
| Zones, layer stack, RF keepout | docs/electrical.md > "PCB-02 placement and layers" |
| Safety properties that must survive layout | CLAUDE.md > "Design invariants" |

If the docs and the board disagree, the docs win until Michael says otherwise — and then the
doc gets updated in the same commit as the board.

## Boards

| Designator | What | KiCad project |
|---|---|---|
| PCB-01 | 78 × 58 mm V1/V2 controller, 4-layer | `pcb/pcb-01/pcb-01.kicad_pro` |
| PCB-02 | 18 × 8 mm DRV5033 Hall daughterboard | not started; own project, same fab order |

## Division of labor

The split follows what each side is actually good at, not what the tools technically allow.
Konnect *can* place and route; we still don't let it.

**Claude does** — the deterministic, spec-driven, verifiable half:

- Schematic capture: place symbols, wire by pin name, net labels, power symbols, hierarchical
  sheets. This is a transcription of docs/electrical.md and is exactly the kind of tedium that
  should never touch a human hand.
- Symbol and footprint sourcing and registration, including flagging the ones pcb/README.md
  marks as needing Ultra Librarian + datasheet verification.
- Cross-checking the schematic against `bom/bom.csv` — every placed part has an MPN, an LCSC
  number where one exists, and a matching BOM line.
- Board setup from spec: stackup, layer names, net classes, design rules, board outline,
  mounting holes, keepouts.
- All validation: ERC, DRC, `run_design_review`, `audit_decoupling`, `audit_power_rails`,
  `audit_connections`, `check_bom_health`, `validate_for_manufacturing`.
- Reading the board back and answering questions about it (what's on this net, what's the
  clearance here, is this rail decoupled).
- JLCPCB part search and stocked-alternative suggestions.

**Michael does** — the parts that need eyes on a canvas:

- **Component placement.** Zones come from the spec, but the actual arrangement is a spatial
  judgment call.
- **Routing.** All of it, including copper pours. Konnect has routing tools and a Freerouting
  bridge; we are not using them for this board.
- **Starting and exporting the project**, plus anything that means clicking through a KiCad
  dialog once.

**Ask before doing** — reasonable either way, so raise it rather than assume:

- Modifying an existing placement or an existing route.
- Anything that changes the outline, the hole pattern, or the layer stack after they are set.
- Running fab exports. `export_manufacturing_package` makes this cheap, so this may well move
  to Claude once we've done one by hand — update this file when it does.

## Starting a session

1. **Confirm the MCP is live**: call `list_toolboxes`. If Konnect's tools are absent, stop and
   tell Michael — never fall back to editing `.kicad_*` files as text.
2. **Load the project config**: `load_user_config`, then `get_effective_config` with
   `project_dir` = `pcb/pcb-01`. Project rules live in `pcb/pcb-01/.konnect/project.json` and
   are committed; they encode the JLCPCB constraints and the safety-critical routing rules.
3. **Load only the toolsets you need** (`load_toolset`), and `unload_toolset` when switching
   tasks. Only `project` and `config` are loaded at startup; the other 16 are on demand.
4. **For any PCB (not schematic) operation, KiCad must be running** with the board open and
   the IPC API enabled — see the quirks below. Ask Michael to open it; he'll say when it's up.

## Toolsets

| Category | Toolsets |
|---|---|
| Project | `project` (create/open/save/snapshot, schematic viewer) |
| Schematic | `sch_components`, `sch_wiring`, `sch_analysis`, `sch_batch`, `sch_export`, `sch_hierarchy` |
| PCB | `pcb_board`, `pcb_components`, `pcb_routing`, `pcb_export` |
| Library | `library` |
| Integration | `integration` (JLCPCB parts DB, Freerouting, datasheet URLs) |
| Verification | `verification`, `design_review` |
| Config | `config` |
| Templates | `templates` (reference circuits — treat as a sanity check, not a source) |
| Manufacturing | `manufacturing` |

Use `sch_batch` for bulk placement and wiring: a block like SCH-05 is dozens of calls
one-at-a-time and a handful batched.

`open_schematic_viewer` renders a live auto-refreshing SVG — open it before a long capture run
so Michael can watch the block appear instead of reviewing it at the end.

## Quirks (add to this list)

- **Never text-edit `.kicad_sch` / `.kicad_pcb` / `.kicad_sym` / `.kicad_mod` / `fp-lib-table`
  / `sym-lib-table`.** They are object graphs with UUIDs and cross-references; a `sed` breaks
  them silently. Everything goes through Konnect. `.kicad_pro` is JSON and tolerates careful
  edits, but prefer the MCP there too.
- **Schematic tools are file-based; PCB tools are not.** Schematic edits go through Konnect's
  S-expression engine and work with KiCad closed. PCB tools speak the KiCad 10 IPC API over a
  socket and need KiCad **running** with the board open and the API enabled
  (Preferences → Plugins → Enable API). `check_kicad_ui` tells you which world you're in.
- **Never run `konnect init`.** It installs 6 skills + 2 agents into `~/.claude/` and patches
  `~/.claude/settings.json` — the first is rulesync-generated output that gets wiped on the
  next regenerate, the second is hand-managed and gets rewritten with reordered keys and no
  trailing newline. It also runs on `konnect init --help`, since that subcommand takes no
  flags. Those files are already vendored here (below); re-running would duplicate them
  globally and dirty the dotfiles repo.
- **Konnect's own skills live in this repo**, not in `~/.claude/`: `konnect` (the never-edit
  rules), `kicad-schematic`, `kicad-pcb`, `kicad-review`, `kicad-manufacture`,
  `kicad-library`, plus two agents in `.claude/agents/`. They carry the per-toolset call
  recipes and reference tables (trace widths, JLCPCB rules, error taxonomy) that this skill
  deliberately does not duplicate. Read them for *how*; read this one for *what and who*.
  They came from Konnect v0.2.1 — on a Konnect upgrade, diff them against a fresh
  `konnect init` in a scratch `CLAUDE_CONFIG_DIR` rather than installing over the top.
- **The pre-PCB-IPC hook is project-scoped**, in `.claude/settings.json`. It fires before
  placement/routing tool calls to remind that KiCad must be open. Konnect wants to install it
  globally; keep it here.
- **macOS needs explicit paths.** `~/Library/Application Support/konnect/config.toml` sets
  `kicad_cli` (inside the .app bundle) and `ipc_address`. Already written; recreate it if
  Konnect starts failing on exports.
- **Two different config files.** `config.toml` is server settings (paths, transport).
  `config.json` in the same directory is *design* preferences (fab house, default passives) and
  is what `load_user_config` returns. Project overrides go to `<project>/.konnect/project.json`.
- **The user-level defaults are wrong for this board** out of the box: `layer_count: 2`, no
  design rules. PCB-01 is 4-layer with 2 oz outer copper, which raises min trace/space to
  0.15–0.16 mm. Always prefer the project config.
- **KiCad 10 writes a `.history/` directory** containing its own nested git repo. It is
  gitignored; leave it alone.
- **`kicad-cli` on PATH is Homebrew's** (`/opt/homebrew/bin/kicad-cli`) and may not match the
  app. Konnect is configured to use the bundle's.

## Safety invariants that constrain layout and capture

These come from CLAUDE.md and docs/electrical.md. They are not style preferences — a board
that violates them is wrong even if ERC and DRC pass:

- The analog overspeed chain (Hall → LM2907 → TLV1701 → U6 lock) must work with no firmware
  and no MCF participation. Nothing in that path may route through the ESP32-C6.
- Firmware never drives DRVOFF directly and never commutates. The permission latch is
  hardware; the MCU can only revoke.
- Only a low-voltage power cycle resets the overspeed lock. No net may offer another path.
- Ground: L2 is continuous AGND under logic and RF, with a local PGND island only under the
  motor stage, joined once beside the MCF through a wide net tie. Keep phases, both switch
  nodes, and motor-current return out of the tach region.
- No copper under the ESP antenna on any layer; Espressif's all-layer keepout applies.
- The four Ø3.2 mm mounting holes are isolated from circuit ground, with an Ø8 mm
  copper-and-component exclusion around each.
- Every test point in docs/electrical.md > "Test points" gets a real pad. V1 is deliberately
  over-instrumented; do not economize.

## Finishing

PCB work commits and pushes straight to `main` like everything else in this repo. Bundle the
board, the doc updates it implies, and any BOM status changes into one push. When a value in
docs/ marked provisional gets settled by capture, update the doc and the board together.
