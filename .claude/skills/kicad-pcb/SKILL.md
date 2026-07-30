---
name: kicad-pcb
description: |
  Workflow skill for KiCAD PCB layout and routing. Triggers on: "layout the board",
  "route traces", "PCB", "place footprints", "copper pour", "board outline", "differential pair",
  "board setup", "track width", "via", "zone", "design rules", "stackup", "silkscreen".
argument-hint: "[layout task]"
---

# PCB Layout (Stillair) — read /pcb instead

> **Gutted 2026-07-30 (Konnect re-scope after PCB-01 shipped to fab).** The original Konnect
> skill here prescribed a Konnect-driven layout workflow this project explicitly does not use,
> and several of its recipes are actively destructive on KiCad 10. The settled division of
> labor, the placement toolkit, the DRC loop, and the full quirks list live in the **/pcb**
> skill — go there. What remains below is only the danger list, kept where the old advice
> used to be so it can't be resurrected by accident.

## Never do these (each one verified harmful on PCB-01)

- **`create_netclass`, `assign_net_to_class`, `set_design_rules`, `add_layer` — never, on any
  KiCad 10 board.** They write KiCad-5-era S-expressions; the board then fails to parse
  entirely. Net classes and design rules are JSON in `.kicad_pro`
  (`net_settings.classes` + `netclass_patterns`, `board.design_settings.rules`); edit that
  file directly and verify with a full-parse `kicad-cli pcb drc` afterward.
- **Do not layout/route through Konnect at all on this project.** Placement is planned in
  scripts (`pcb/tools/`: `board_model.py`, `apply_positions.py`, `place_targeted.py`,
  `check_plan.py`) and applied via file writes with KiCad closed; routing and pours are
  Michael's, on canvas, with Claude running headless DRC diffs per save
  (`kicad-cli pcb drc --format json --severity-all` vs the baseline in
  `pcb/pcb-01/placement/waivers.md`).
- **`run_drc` via Konnect / IPC is not the gate** — the headless CLI DRC is, and it checks
  the *saved* fill state: refill zones (`B`) + save before trusting it.
- The old skill's "via defaults" included micro vias — JLCPCB fabs none, and a stray
  `via micro` passes normal DRC while being unmanufacturable (see /pcb quirks).

## Still fine

`set_board_size`, `add_mounting_hole`, and the read-only pcb queries work. Custom DRC rules
go in `pcb-01.kicad_dru` (plain text, safe to edit; scope object matches with
`B.Type == 'Pad'` — see /pcb).
