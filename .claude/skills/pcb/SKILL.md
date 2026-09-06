---
name: pcb
description: "Build and maintain Stillair PCBs with tscircuit as the authority through schematic, board specification, and component placement, then hand off to KiCad for routing and fabrication-only work. Use whenever the task touches a PCB, schematic, components, footprints, placement, KiCad, Konnect, ERC/DRC, Gerbers, or fabrication."
---

# PCB workflow

## Authority

For every new board, committed tscircuit source owns:

- stable component IDs and reference designators;
- values, pin maps, MPN and supplier metadata, and footprint selection;
- schematic connectivity and named nets;
- board outline, dimensions, holes, layer count, and declared fabrication specifications;
- component X/Y position, side, rotation, and tscircuit-native constraints;
- base silkscreen and committed manual placement edits.

`docs/*.md` and `bom/bom.csv` remain the requirements authority. Generated Circuit JSON, SVG,
PNG, and KiCad seed files are derived outputs.

KiCad owns only the downstream features that tscircuit cannot yet carry reliably:

- production routes, vias, zones, and plane fills;
- detailed stackup, impedance settings, net classes, and custom DRC rules;
- special mask, paste, via fill/cap, and other fabrication-process exceptions;
- final production silkscreen, ERC/DRC evidence, Gerbers, drill, BOM, and CPL.

Every KiCad-owned addition must be named in the board's `design/kicad-augment.json`. An
undocumented manual difference is drift, not an exception.

PCB-01, PCB-01 V2, PCB-02, and the released PCB-03 remain legacy KiCad-authoritative boards.
Do not regenerate them. PCB-03's `design/` directory is the validation fixture for this workflow
through the initial KiCad handoff boundary.

## New-board procedure

1. Read the board requirements, relevant safety invariants, BOM rows, and current project state.
2. Create `pcb/<board>/design/` from the PCB-03 pattern. Pin the tscircuit version in
   `pcb/package.json` and `bun.lock`; never depend on `latest`.
3. Define exact parts and pin maps. Give every part an immutable `stable_id`, fixed ref, exact
   KiCad footprint mapping, and explicit pad-number set. Never guess a footprint or pinout.
4. Author and review the schematic in TSX. Run source, netlist, pin, and schematic-placement
   checks before doing physical placement.
5. Define the board specification and place every part explicitly. Use the local viewer to
   iterate, and commit `manual-edits.json` if viewer placement is adopted.
6. Run the project validation and render both schematic and PCB views. Inspect the renders.
7. Run the handoff planner. Before routing begins, export a new KiCad seed into a staging
   directory and validate it. Adopt the seed once, then create the accepted handoff lock.
8. Apply declared augmentations in KiCad. Run `verify-schematic-cleanup` and require exact strict
   schematic parity plus clean ERC before routing. Then route in KiCad and run final DRC and
   fabrication checks. Never make tscircuit's autorouter the production routing authority for a
   controller.

Read [tscircuit-authoring.md](references/tscircuit-authoring.md) while authoring. Read
[kicad-handoff.md](references/kicad-handoff.md) before export or any later update. Read
[review.md](references/review.md) before declaring a design or handoff complete.

## Post-handoff updates

Tscircuit remains authoritative, but a routed production board is never overwritten by a fresh
export.

1. Build and normalize the new source manifest.
2. Compare it with `design/handoff.lock.json` and generate an ECO plan.
3. Review adds, removals, ref/value changes, net endpoint changes, footprint changes, moves,
   rotations, holes, outline, and board-spec changes.
4. Treat a component move or rotation after routing as guarded. Treat footprint, layer, hole, or
   outline changes as destructive. Require explicit acknowledgement before applying either class.
5. Apply an accepted ECO through KiCad GUI, Konnect, or KiCad's native API. Never patch a
   production `.kicad_*` file as text.
6. Snapshot the KiCad board before and after. Prove unrelated track, via, zone, rule, graphic,
   and UUID-bound waiver state is unchanged.
7. Compare KiCad refs, values, footprint pad sets, nets, placement, outline, and holes back to the
   tscircuit manifest. Only declared augmentations may differ.
8. Update the handoff lock only after parity, ERC, DRC, and renders pass.

If placement was adjusted directly in KiCad, import it as an explicit proposed patch to the
authoritative tscircuit placement or manual-edits file, rebuild, and plan the ECO. Never silently
bless KiCad placement drift.

## Protected KiCad files

Do not edit `*.kicad_sch`, `*.kicad_pcb`, `*.kicad_pro`, `*.kicad_sym`, `*.kicad_mod`,
`sym-lib-table`, or `fp-lib-table` with text manipulation. The approved tscircuit exporter may
create a new seed only in staging. All later writes go through KiCad, Konnect, or KiCad's native
API and are verified afterward. Load the `konnect` skill for this downstream phase.

## Completion boundary

A tscircuit design is ready for KiCad handoff only when the source checks pass, both renders were
inspected, the normalized manifest matches the requirements, footprint/pad mappings are exact,
and the augmentation manifest is complete. A board is ready for fabrication only after the
downstream KiCad review and the `kicad-manufacture` procedure pass.
