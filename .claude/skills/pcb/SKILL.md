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

**Claude also does placement** (updated 2026-07-29 after the PCB-01 first pass): the working
pattern is *plan in scripts + subagents, apply via file*. The toolkit lives in `pcb/tools/`
(`board_model.py` exact courtyard/pad/net parser, `apply_positions.py` bulk file writes with
parse verification, `place_targeted.py` spiral placement toward a target pin,
`check_plan.py`/`validate_group.py` geometry checks, `make_briefs.py` per-group agent briefs,
`render_board.sh`). Group definitions and regions: `pcb/pcb-01/placement/groups.json`.
Sonnet subagents plan one coupled subcircuit each from a generated brief and return JSON —
they never touch the board, so no locking is needed; the orchestrator validates each plan,
solves cross-group conflicts, and applies everything in one file write (KiCad closed).
Learned limits: agents handle ~10-20-part groups well but blow the 64k output cap or
degenerate into brute-force on 30-part analog groups — use `place_targeted.py` for those;
IPC moves are fine for <20 interactive nudges but far too slow for bulk.

**The board-truth review loop** (established 2026-07-29, caught 4 blockers the spec-derived
capture could never catch — including a bug that was *in the spec itself*): after capture and
placement, run swarms of Sonnet review agents against artifacts extracted FROM THE BOARD
(`pcb/tools/extract_netlist.py out.md [positions.txt]`), with `docs/` and the schematic
explicitly off-limits to the agents (the board was derived from them — checking against them
is circular). Agents get a functional brief (what the product must do, not how it's wired),
fetch datasheets themselves, and map every pad number to a pin function independently.
Lenses: per-subsystem pin-by-pin, logical-path traces, value/orientation sweeps, sequencing
walks, placement physics (with the positions file), firmware cross-checks (GPIO map, register
image), and a completeness critic. Then: integrate fixes (schematic-side via Konnect, Michael
runs F8 to sync the board, Claude places new/changed parts), sweep the spec + BOM + TODOs,
re-extract, and re-run with a brief addendum listing fixes-to-verify and accepted-tradeoffs
(so they don't get re-flagged). Loop until only nits/accepted items come back. Round-1
lesson: demand primary sources — one agent's web-search summary had BAT54H's pinout backwards
and only reading the actual datasheet page corrected it.

**Michael does** — the parts that need eyes on a canvas:

- **Routing.** All of it, including copper pours. Konnect has routing tools and a Freerouting
  bridge; we are not using them for this board.
- **Placement review/fine-tune** on Claude's first pass, especially the MCF switching loops
  vs TI's reference layout and anything housing-related.
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
- **The vendored Konnect agents pinned a dead model** (`claude-sonnet-4-20250514`), which made
  every `kicad-schematic-build-agent` / `kicad-design-review-agent` launch die at startup with
  an API error. Fixed to `claude-sonnet-5` (2026-07-28); on a Konnect upgrade re-check the
  `model:` frontmatter of both files in `.claude/agents/`.
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
- **Custom symbol libraries: placement only resolves the installed-symbols dir.**
  `register_symbol_library` (project or global scope) makes `search_symbols` work, but
  `add_schematic_component` still errors "library not found" — it only reads
  `KICAD10_SYMBOL_DIR`. Fix: symlink the project `.kicad_sym` into
  `/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols/` (re-create after KiCad
  updates). The project lib is `pcb/pcb-01/pcb01-parts.kicad_sym`.
- **`batch_connect_to_net` writes local net labels only** (no `label_type` option). For a
  cross-sheet net, convert exactly one label per sheet to a global label:
  `delete_schematic_net_label` at the pin coords, then `add_schematic_net_label` with
  `label_type: global_label` at the same coords. Wiring convention on this board: label-based
  connectivity (labels sit directly on pin endpoints), local labels for intra-sheet nets,
  one global label per cross-sheet net per sheet, net names exactly as in docs/electrical.md.
- **`add_schematic_component` silently drops its `footprint` parameter** — the call echoes the
  value back but never writes it (confirmed via `get_schematic_component`). Always set
  footprints afterward with `batch_edit_schematic_components`.
- **`edit_schematic_component` renames the Reference property but not the `instances` block**
  — the per-instance `(reference "…")` keeps its old value, and KiCad's netlister uses the
  instance, not the property. Symptom: renamed power flags showed up in Update-PCB as bogus
  components "01".."04" with no footprint. Fix by patching the instance reference (scripted
  text edit; see scratchpad fix_flag_instances.py pattern), then verify with
  `kicad-cli sch export netlist` + grep. Prefer `add_power_symbol` over placing
  `power:PWR_FLAG` with `add_schematic_component` in the first place.
- **`batch_edit_schematic_components` cannot create new fields**, only update existing ones
  (Value/Footprint work; a new `MPN` errors "Field not found"). Create fields one at a time
  with `add_component_annotation`. Fields in use: `MPN`, `LCSC`, `Note`, `DNP`.
- **`download_jlcpcb_database` 404s** in Konnect v0.2.1 (upstream data URL moved), so
  `search_jlcpcb_parts` has no local DB. Verify LCSC part numbers by web search or at order
  time; JLCPCB/LCSC part pages are JS-rendered and WebFetch-opaque.
- **KiCad 10 renamed transistor symbols**: `Device:Q_PMOS_GDS` etc. are gone; `Device:Q_PMOS`
  has *letter* pin numbers (G/D/S) that cannot map to numeric footprint pads. Use the
  `Transistor_FET:Q_PMOS_<order>` variants, which kept numeric pins (e.g. `Q_PMOS_GDS` for
  SOT-223 1=G 2=D+tab 3=S).
- **`Device:D_TVS` is bidirectional** (pins A1/A2). For a unidirectional TVS (SMCJ24A) use
  `Device:D_Zener` so cathode/anode are explicit (KiCad diode convention: pin 1 = K).
- **`validate_component_connections` flags `no_connect`-typed pins too** — every NC pin still
  needs an explicit `add_no_connect` flag at its coordinates.
- **Pad angles in `.kicad_pcb` are ABSOLUTE** (footprint rot + pad-local rot). Changing a
  footprint's rotation by editing only its `(at x y rot)` line silently mis-orients every
  pad's copper — `pcb/tools/apply_positions.py --rot` handles the pad-angle delta correctly;
  never rotate via a bare file edit.
- **The MCF8316D RGF land pattern's (4.8)/(6.8) dims are pad-CENTERLINE spans** (columns at
  ±2.4, rows ±3.4, pads 0.6×0.25) — deriving centers from "overall minus pad length" puts
  the corner pads into collision. Footprint fixed 2026-07-29 against drawing 4224999/B.
- **`get_schematic_view` writes an SVG to `$TMPDIR`** (KiCad 10 CLI has no bitmap export);
  convert with `rsvg-convert -w 1800 -o out.png <svg>` and Read the PNG to inspect.
- **NEVER use `add_layer`, `set_design_rules`, `create_netclass`, or `assign_net_to_class` on
  a KiCad 10 board — they corrupt it.** All four write KiCad-5-era S-expressions:
  `add_layer` nests malformed entries inside F.Cu's line with colliding layer IDs, and the
  others insert `(min_clearance …)` / `(netclass …)` tokens the KiCad 10 parser rejects — the
  board then fails to load entirely. In KiCad 10, design rules and net classes live in the
  `.kicad_pro` JSON (`board.design_settings.rules`, `net_settings.classes` +
  `netclass_patterns`), and a 4-layer stack is `(4 "In1.Cu" power)` / `(6 "In2.Cu" power)` as
  siblings in the layers block. Edit the `.kicad_pro` JSON directly (it is not an
  object-graph file) and verify with `kicad-cli pcb drc` afterward, which is a full parse.
  `set_board_size` and `add_mounting_hole` are fine.
- **Custom DRC rules go in `pcb-01.kicad_dru`** (plain-text rules file, safe to edit): the
  Ø8 mounting-hole copper keepout lives there as a `physical_clearance` rule against H1-H4.
- **Right-angle connectors: verify the mating face points OFF-board and every pad is
  ON-board, per placement.** A blanket "connectors legitimately overhang" edge waiver in
  check_plan.py masked J2 placed rotated 90° wrong — mating face pointing into the board
  interior, pin 3's THT pad fully off the board edge. Waivers are now per-side
  (`EDGE_WAIVER` in check_plan.py: only the mating-face side may overhang). Rule of thumb:
  right-angle THT/SMD headers sit with body fully on board and face flush at the edge; only
  courtyard grace beyond the face may cross Edge.Cuts.
- **Triage every DRC class by name before calling it cosmetic.** `copper_edge_clearance` is
  never cosmetic — the J2 defect above appeared in the final DRC report but was lumped into
  the "residual noise" summary. Silk/courtyard classes may be noise; anything touching
  copper, edge, or holes gets looked at item by item.
- **The gap checker doesn't model rotation changes.** `aes_check.py`-style pre-checks build
  boxes from the *current* stored rotation; a move that also rotates a non-square part
  reports false overlaps (or misses real ones). Hand-verify the rot-swapped box for those
  parts, or apply rot first and re-check.
- **Schematic→board sync after file-based schematic edits is Michael running F8**
  (Update PCB from Schematic) — kicad-cli has no headless equivalent. New components land
  wherever he drops them (fine, anywhere); Claude re-places them from the file afterward.
  "No net found for pad MP" warnings during F8 are connector mounting tabs — benign.
- **`add_component_annotation` takes `key`/`value`** (not `property_name`/`property_value`).

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
