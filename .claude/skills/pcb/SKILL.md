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
| PCB-01 V1 | Released 78 × 58 mm controller, 4-layer | `pcb/pcb-01/pcb-01.kicad_pro` |
| PCB-01 V2 | Fresh controller redesign, 4-layer; outline follows placement | `pcb/pcb-01-v2/pcb-01-v2.kicad_pro` |
| PCB-02 | 24 × 8 mm DRV5033 Hall daughterboard, 2-layer | `pcb/pcb-02/pcb-02.kicad_pro` (own small fab order; grown from spec'd 18 × 8 on 2026-07-30) |

PCB-01 V2 is a fresh project, not a copy of V1. Its sole circuit/layout authority is
`docs/pcb-01-v2.md`; V1 is evidence only. Load `pcb/pcb-01-v2/.konnect/project.json` for its
constraints. Do not transfer the V1 outline, holes, placement, routes, zones, probe map, or DRC
waivers.

## Konnect scope — settled 2026-07-30, after PCB-01 shipped to fab

The keep/kill review after the first full board: **Konnect is the schematic engine, and only
that.** Its file-based schematic tools captured all 7 sheets / ~170 components with KiCad
closed and have no kicad-cli equivalent (the CLI cannot place a symbol, draw a wire, or edit
a field) — that alone justifies keeping it, and it's the workhorse for PCB-02. Everything
board-side lost to alternatives or is broken: board setup corrupts KiCad 10 files
(quirks below), placement lost to `pcb/tools/`, routing is Michael's, DRC is headless
kicad-cli, and the manufacturing/validation tools are verifiably wrong (see
/kicad-manufacture). Operating rule: **load `sch_*`, `library`, `project`, `config`,
`design_review` freely; never load `pcb_routing` or `manufacturing`; treat `pcb_board` /
`verification` as read-only-and-suspect.** The vendored kicad-pcb and kicad-manufacture
skills were rewritten to match; kicad-review carries a scope note. On a Konnect upgrade,
re-test the broken tools before widening this.

## Board playbook — the end-to-end phase order (distilled from PCB-01)

"Let's do the next board" means this sequence; each phase's how-to is detailed later in this
file. Scale the ceremony to the board — PCB-02 (1 IC, ~5 parts) gets the same *order* but a
fraction of the agent fan-out PCB-01's 170 parts needed.

1. **Schematic capture** (Konnect, KiCad closed): transcribe from docs/electrical.md +
   bom/bom.csv; MPN/LCSC/DNP fields as you go; label-based wiring convention.
2. **Schematic validation**: `run_erc` + `find_orphan_items` / `find_shorted_nets` /
   `find_single_pin_nets`, cross-check against bom.csv.
3. **Board setup** (KiCad GUI): outline and mounting holes through safe board operations;
   stackup, constraints, and net classes through Board Setup (never the broken Konnect rule
   tools or direct `.kicad_pro` edits); `.kicad_dru` for custom rules; verify with a headless
   DRC parse.
4. **Placement**: plan in `pcb/tools/` scripts (+ per-group Sonnet planners only when the
   board is big enough to need them), apply via file write, validate with check_plan-style
   geometry checks. Michael fine-tunes on canvas.
5. **Board-truth review loop** (the quality gate that caught what nothing else did):
   extract netlist/positions FROM the board, Sonnet review swarm with docs off-limits,
   integrate fixes, re-extract, re-run with a fixes-to-verify addendum, loop until only
   nits return. Size the swarm to the board.
6. **Routing** (Michael, on canvas): rules-not-coordinates briefs; Claude runs the
   headless-DRC-diff-per-save loop and maintains the waivers baseline in
   `pcb/<board>/placement/waivers.md`.
7. **Silk + final render check**: `silk_sweep.py` fixpoint + render-guided hand fixes;
   eyeball a final render.
8. **Fab package + order**: /kicad-manufacture procedure (`jlc_fab.py`, lcsc-map,
   pre-flight DRC diff), then the JLCPCB walkthrough — Michael clicks, Claude reviews
   saved order pages offline and verifies polarities from the board file on request.
9. **Record + wrap**: sourcing decisions → electrical.md + lcsc-map notes; order → bom.csv;
   STATE.md; commit/push.

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
- **For dense stitch/fill work, give Michael RULES, not coordinates** (learned on the
  2026-07-30 fill session): trace/via sizes + the plane geography (which L2/L3 region is
  under which x/y band, where a bare via reaches a plane vs needs visible fill) and let him
  chase airwires on canvas; Claude validates each save with a headless DRC diff. Coordinate
  lists stop being useful once the board is dense — he asked for exactly this switch, and
  the 116-airwire sweep went faster than any scripted chunk.
- **During an interactive routing session, keep board work in the main agent.** It owns all
  KiCad inspection and protected-file changes, DRC, placement, routing guidance, judgment,
  triage, and verification. Dispatch routine documentation and routing-artifact maintenance
  fire-and-forget to background agents with precise briefs so Michael can keep routing; surface
  their results only when they change what he needs to do.
- **Placement review/fine-tune** on Claude's first pass, especially the MCF switching loops
  vs TI's reference layout and anything housing-related.
- **Starting and exporting the project**, plus anything that means clicking through a KiCad
  dialog once.

**Ask before doing** — reasonable either way, so raise it rather than assume:

- Modifying an existing placement or an existing route.
- Anything that changes the outline, the hole pattern, or the layer stack after they are set.
- ~~Running fab exports~~ — moved to Claude 2026-07-30 at Michael's request: run
  `python3 pcb/tools/jlc_fab.py` (headless kicad-cli; writes gerber zip + JLCPCB BOM/CPL
  to `pcb/pcb-01/fab/`, merging `fab/lcsc-map.csv` for parts without schematic LCSC
  fields). Do NOT use Konnect's `export_manufacturing_package`: its "jlcpcb" BOM lacks
  the LCSC column, its position file is inches with KiCad headers, and `drill.drl`
  comes out as a directory. `validate_for_manufacturing` is equally shallow (read the
  routed 4-layer board as "2 layers, 0 nets" and said READY) — the real pre-fab gate is
  the headless DRC diff against `placement/waivers.md`.

## Starting a session

1. **Confirm the MCP is live**: call `list_toolboxes`. If Konnect's tools are absent, stop and
   tell Michael — never fall back to editing `.kicad_*` files as text.
2. **Load the project config**: `load_user_config`, then `get_effective_config` with the exact
   target project directory (`pcb/pcb-01`, `pcb/pcb-01-v2`, or `pcb/pcb-02`). Project rules live
   in that directory's `.konnect/project.json` and are committed; they encode the board-specific
   JLCPCB constraints and safety-critical routing rules.
3. **Load only the toolsets you need** (`load_toolset`), and `unload_toolset` when switching
   tasks. Only `project` and `config` are loaded at startup; the other 16 are on demand.
   If a toolset reports loaded but its tools do not appear in the harness inventory, call the
   configured Konnect server over its stdio MCP transport. Retrying load/unload does not expose
   tools the harness omitted; all protected KiCad writes must still go through Konnect.
4. **For any PCB (not schematic) operation, KiCad must be running** with the board open and
   the IPC API enabled — see the quirks below. Launch it through the project-manager workflow
   below when host GUI permissions are available; ask Michael only when automation is blocked.

When the task needs KiCad's GUI, read
[references/kicad-gui.md](references/kicad-gui.md). It covers project-owned editor launch,
window cleanup, the yabai audit, Codex-hosted macOS automation, and the fresh-project
scaffold checklist. Codex may launch and operate KiCad directly when the host permissions are
available; Michael does not need to repeat routine setup clicks.

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

- **`kicad-cli pcb drc` does not refill zones** — it checks against the fill saved in the
  file. A via added after the last `B` shows as a 0.000 mm clearance + hole_clearance pair
  against the zone it pierces. Refill (`B`) + save in KiCad, then re-run. Routing-session
  loop that works: Michael saves, Claude runs the project's headless checker. For PCB-01 V2
  use `python3 pcb/tools/check_drc.py`; it applies only the reviewed U1 PGND escape-via
  exceptions and fails on every other violation or unconnected item. Older boards without a
  wrapper use `kicad-cli pcb drc --format json --severity-all` and the documented baseline in
  `placement/waivers.md`.
- **Net-tie footprints need a via per pad before the tie exists.** NetTie pads are F.Cu-only;
  if the tied nets live on inner planes, the tie is vapor until each pad gets a via into its
  plane. No DRC *violation* fires for this — it appears only as unconnected-items ratsnest,
  so check the unconnected list for the net-tie ref explicitly during routing validation.
- **Zone dialog reuses the last zone's name** — drawing a second zone right after the first
  silently inherits its name (nets are set per-zone and stay correct). Check names in the
  Zone Manager after creating several zones; misnamed ground zones make DRC reports lie to
  the reader.
- **An unfill-all saved to disk looks like mass destruction in headless DRC**: every
  zone-only-connected stitch via flags `via_dangling` (66 at once on PCB-01) and the plane
  nets' unconnected counts explode. Before diagnosing, check `grep -c filled_polygon
  file.kicad_pcb` — zero means the fills are simply absent; `B` + save restores everything.
- **Duplicate-numbered pads are NOT connected for DRC/ratsnest purposes.** Tact switches
  whose two pin-1 pads are internally one leg still need a copper join pad-to-pad (SW1, SW2,
  SW3 all did) or the net reports unconnected forever.
- **Accidental micro vias pass the normal via-diameter check** — micro vias have their own
  (smaller) minimum, so a stray 0.3/0.1 `via micro` hides among legal vias while being
  unmanufacturable at JLCPCB (no micro vias at all, and F.Cu→B.Cu span is invalid anyway).
  If a via looks undersized but doesn't flag, check its *type* in properties.
- **A duplicate track segment lying exactly on top of a longer same-net segment is
  invisible and un-clickable** — clicking always selects the long twin, and the cleanup tool
  doesn't remove it, but DRC flags it `track_dangling`. Grab it with a tiny drag-box that
  fully encloses only the stub (box-select takes only fully-enclosed items).
- **Board Setup constraint edits, like net classes, must be verified to have landed in the
  file.** The 0.4/0.2 min-via decision was documented in electrical.md but the board still
  carried 0.5 min diameter a session later; 11 legal vias flagged before the constraint was
  actually entered. After any Board Setup change, confirm via a headless DRC diff.

- **Never text-edit `.kicad_sch` / `.kicad_pcb` / `.kicad_pro` / `.kicad_sym` /
  `.kicad_mod` / `fp-lib-table` / `sym-lib-table`.** They are protected KiCad sources with
  cross-references and tool-owned structure. Use Konnect or KiCad's GUI and verify the saved
  result.
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
- **Run repo scripts that import `pcbnew` through `pcb/tools/kicad_python.sh`.** System Python
  cannot load KiCad's app-private module with `PYTHONPATH` alone; the wrapper supplies KiCad's
  bundled interpreter, site-packages, and framework paths.
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
  board then fails to load entirely. Configure layers, stackup, design rules, and net classes
  in KiCad's Board Setup dialog, then verify with `kicad-cli pcb drc`, which is a full parse.
  `set_board_size` and `add_mounting_hole` are fine.
- **`add_board_text` writes valid KiCad 10 `gr_text` but omits `(justify mirror)` on back
  layers** (verified on PCB-02, 2026-07-30) — B.SilkS text comes out readable from the
  FRONT, i.e. mirrored on the physical part. Follow up with a scripted patch adding
  `(justify mirror)` inside the effects block (see scratchpad fix_pcb02_bsilk.py), then
  DRC-parse and render `--mirror` to eyeball. Otherwise the tool is safe: correct syntax,
  uuid included, file-based with KiCad closed.
- **`add_mounting_hole` writes a dangling lib id and thin geometry** (found on PCB-02,
  2026-07-30): it names the footprint `MountingHole:MountingHole_<drill>mm`, which exists in
  KiCad's library only for some diameters (2.2 mm doesn't — the real name is
  `MountingHole_2.2mm_M2`), gives the NPTH pad a 0.5 mm annular keepout the library doesn't
  have, and omits the courtyard + Cmts screw-head circles entirely — so placement checks
  can't see the screw head. DRC flags it as `lib_footprint_issues`. Fix pattern: scripted
  file patch (lib id, pad size to match lib, add the two fp_circles with uuids), then a
  headless DRC parse to verify — see scratchpad fix_pcb02_holes.py from that session.
- **Custom DRC rules go in `pcb-01.kicad_dru`** (plain-text rules file, safe to edit): the
  Ø8 mounting-hole copper keepout lives there as a `physical_clearance` rule against H1-H4.
- **`memberOfFootprint()` in `.kicad_dru` conditions matches the footprint's TEXT fields
  too** — the H1-H4 rule fired between a legal stitch via and H4's silkscreen *reference
  text*. Scope the object side with `B.Type == 'Pad'` (done 2026-07-30).
- **Rule areas drawn with margin can swallow a module's own pads.** The antenna keepout
  at x 121 covered U2's east ground-pad column (x 121.9), making those pads impossible to
  legally connect (tracks/vias not_allowed; pads allowed — so no violation warns you,
  the pads just can't be reached). When drawing a keepout next to a module, check its
  edge against the module's pad coordinates, not its courtyard.
- **Silkscreen ref cleanup is scripted: `pcb/tools/silk_sweep.py`** (KiCad closed). It
  parses flagged Reference fields from a headless DRC JSON, grid/ring-searches clear
  spots (pads + silk + other texts + edge as obstacles), and rewrites only the property
  `(at)`/`(size)` lines. Run it as a fixpoint loop against successive DRC JSONs; it
  stalls at the truly-impossible refs, which get hidden (passives) or hand-placed from
  renders (TPs/ICs). Quirks paid for: **property text angles are stored ABSOLUTE** like
  pad angles (don't add the footprint rotation); **board min text height (0.8) forbids
  shrinking below it** — text_height violations, not a free escape; **footprint outline
  interiors look like free space to bbox models** — fp_line outlines have hollow
  interiors, and labels placed "inside" a module outline end up under the soldered part
  (TP13/R42/D9 all did this; only the render caught it). Always eyeball a final render.
- **Render-inspection recipe** (headless): `kicad-cli pcb export svg --layers
  "F.Cu,F.Silkscreen,Edge.Cuts" --fit-page-to-board --exclude-drawing-sheet
  --black-and-white`, then `rsvg-convert -w 4600` and crop with `sips -c h w
  --cropOffset y x` (px = (mm − 50) × width/78 for PCB-01). Good enough to hand-place
  silk labels and sanity-check dense areas without opening KiCad.
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
- **Schematic-to-board sync after file-based schematic edits uses the KiCad GUI to run F8**
  (Update PCB from Schematic); kicad-cli has no headless equivalent. Follow
  [references/kicad-gui.md](references/kicad-gui.md): close stand-alone editors, open the
  `.kicad_pro`, launch Schematic Editor from the project manager, minimize the manager, and
  audit the window state. New components land wherever the update drops them (fine, anywhere);
  the agent re-places them from the file afterward.
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
