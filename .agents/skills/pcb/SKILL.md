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
   Establish the visual direction before detailed placement, then put exact dimensions,
   mounting, connector exits, layer roles and assembly limits in the canonical specification.
   Retain useful images as references; generated component details are not circuit requirements.
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

## Complete preparation, then accept once

The shared [PCB tools](../../../pcb/tools/README.md) provide capability discovery,
native transactions, verified schematic-field batches, preparation audits and the
`begin` → `plan` → `apply` → `validate` → `review` → `accept` lifecycle. The coordinator
requires a project-owned workflow and readiness profile. Stillair's released boards
remain KiCad-authoritative, and no new profile is implied by installing these tools.
Keep using the established board-specific commands until a profile is deliberately
configured for a compatible adopted source handoff. Never copy another project's
geometry, routing limits or release evidence to make a profile pass.

Before assigning implementation, enumerate the entire routing-preparation result:
schematic fields and exclusions, source/native parity, physical stack, planes and
pours, vias, trunk and bounded escape widths, native DRC, paste/stencil provisions,
service labels and export settings. Put project facts in the readiness profile and
augmentation declaration. Do not add circuits or standards through a generic
checklist. Machine checks cannot prove physical calibration or visual inspection.

Prefer verified `kicad_native.py` and `kicad_schematic.py` operations over repeated
GUI actions or board-specific scripts. Inspect actual installed capabilities before
selecting a write path. Use scratch projects for capability probes and verify saved
results; a schema advertising a feature is not proof it works. Unsupported operations
remain explicit and use an established native/GUI path while independent work
continues. Existing authorization applies; a tool limitation is not a new approval
requirement.

Run the full preparation audit before final review and acceptance. Review current
renders and evidence through the agreed design, schematic, placement/copper and
assembly/process scopes. Focus on correctness within the authorized design. Use one
final acceptance after all required checks and findings close. Keep the small run
index with its content-addressed evidence; source, native, profile or checker changes
invalidate stale validation/review. Canonical specs describe the current target;
STATE points to the current receipt.

## Post-handoff updates

Tscircuit remains authoritative, but a routed production board is never overwritten by a fresh
export.

1. Build and normalize the new source manifest.
2. Compare it with `design/handoff.lock.json` and generate an ECO plan.
3. Review adds, removals, ref/value changes, net endpoint changes, footprint changes, moves,
   rotations, holes, outline, and board-spec changes.
4. Review preservation for component moves/rotations after routing and footprint, layer, hole
   or outline changes. Existing user authorization governs reversible repository changes;
   do not reopen an already authorized change merely because it needs a guarded operation.
5. Apply an accepted ECO through KiCad GUI, verified Konnect, or KiCad's native API. Never patch a
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
