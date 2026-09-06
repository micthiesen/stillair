# PCB source and handoff authority

## Decision

Every new Stillair board starts in tscircuit. Its committed source remains authoritative for parts,
pin maps, metadata, schematic connectivity, named nets, board dimensions and holes, declared board
specifications, and component placement. The local viewer is the normal placement-review loop.

KiCad is the downstream production environment. It owns interactive routing, vias, zones and plane
fills, detailed stackup and impedance configuration, net classes and custom rules, special
mask/paste or via-process treatment, final production silkscreen, ERC/DRC, and fabrication outputs.
These differences are declared per board rather than existing as undocumented edits.

This boundary is based on the pinned toolchain's present limits. Tscircuit's code model and viewer
make schematic and placement iteration faster, but its autorouting and KiCad/Gerber export do not
yet cover all production controller requirements. In particular, direct multilayer Gerber output,
copper-pour/cutout preservation, advanced routing rules, controlled impedance, and special process
details still require downstream verification.

## Initial handoff

The source is compiled to Circuit JSON, normalized into a stable manifest, rendered, and checked.
The handoff tool exports a KiCad seed into a task-specific staging directory. It never writes an
existing production `.kicad_*` file. Before adoption, the staged seed is compared with the source
for electrical refs, values, pin sets, nets and endpoints, board footprints and pad sets, outline,
holes, positions, sides, rotations, and connector direction. Missing schematic symbol-library,
footprint-property, MPN, and datasheet metadata is an explicit cleanup augmentation, not silent
parity. KiCad must parse the complete project and produce reviewable renders.

The pinned exporter currently omits hierarchical child sheets and mishandles repeated power/ground
rail symbols. The repository wrapper uses the exporter's public multi-file API and converts those
rails to same-named global labels in memory before export. The tscircuit source is unchanged. A
KiCad XML netlist must then prove exact schematic refs, pin sets, and net endpoints.

Parsing is not the same as a clean design check. The stage records any declared pre-route DRC and
ERC categories and rejects every undeclared category. PCB-03 currently needs downstream schematic
grid/library/metadata/no-connect cleanup, production silkscreen cleanup, and routing. ERC must be clean
before routing starts. The `verify-schematic-cleanup` gate also requires exact symbols, values,
footprints, MPNs, Datasheets, pins, and nets after cleanup. DRC plus unconnected-item counts must be
clean before fabrication.

The native handoff is currently a macOS gate because the repository uses KiCad's bundled pcbnew
Python runtime. Linux CI runs source checks, exporter hierarchy tests, and handoff unit tests; it
does not replace the local KiCad parse, semantic-parity, and render gate.

The accepted handoff lock records source and tool fingerprints, immutable part identities,
reference mappings, coordinate transform, and the accepted logical/placement state. Board-specific
downstream requirements live in `design/kicad-augment.json`.

## Updates after routing

A routed board is never regenerated from scratch. A source change is compared with the accepted
lock and emitted as an ECO plan. Moves and endpoint changes are guarded after routing. Footprint,
pad-map, layer, hole, outline, and coordinate-transform changes are destructive and require explicit
acknowledgement.

Accepted ECOs are applied through KiCad GUI, Konnect, or KiCad's native API. A semantic snapshot
before and after must prove that unrelated tracks, vias, zones, graphics, rules, and UUID-bound
waivers were preserved. Source-owned domains are then compared back to tscircuit, ERC/DRC and
renders are reviewed, and the lock is updated last.

Direct placement adjustment in KiCad is not a second authority. It must be imported as a proposed
patch to the tscircuit placement, rebuilt, and passed through the same ECO plan.

## Toolchain updates

Tscircuit and its KiCad exporter are exact-version dependencies in `pcb/package.json` and
`bun.lock`. Upgrade them together in a dedicated change. Before accepting an upgrade:

1. review upstream release notes and open exporter issues relevant to the boards in this repo;
2. run TypeScript and handoff unit tests;
3. rebuild every committed validation board and compare normalized manifests;
4. regenerate PCB and schematic renders and inspect them;
5. stage fresh KiCad exports, parse them with the installed KiCad CLI, and compare semantic
   snapshots with the prior exporter output;
6. reject unexplained pin, net, footprint, coordinate, rotation, outline, or hole changes.

Do not update an accepted production-board handoff lock merely to silence tool-version drift. A
version change becomes an ECO only when the intended generated result changes.

## Existing boards

PCB-01, PCB-01 V2, PCB-02, and the released PCB-03 predate this decision and remain
KiCad-authoritative. They are not regenerated. PCB-03 is recreated under `pcb/pcb-03/design/` as a
validation fixture to prove the new workflow through the handoff boundary against a small released
board with known-good netlist, geometry, ERC, and DRC evidence.
