# Tscircuit authoring

## Project shape

Use the shared pinned toolchain in `pcb/package.json`. A board's authoritative files live in
`pcb/<board>/design/`:

- `<board>.circuit.tsx`: circuit and schematic source;
- `design-manifest.ts`: stable identities, part metadata, pin maps, exact footprint mappings,
  and the normalized handoff input;
- `board-spec.ts`: physical and fabrication specification;
- `manual-edits.json`: reviewed viewer edits, when used;
- `kicad-augment.json`: declared downstream work;
- `handoff.lock.json`: accepted handoff baseline, created only at handoff.

Raw Circuit JSON and rendered/build artifacts belong under ignored `dist/` paths.

## Modeling rules

- Use exact fixed refs. Do not allow automatic annotation in authoritative source.
- Keep `stable_id` immutable even if a ref is deliberately renamed.
- Use `kicad:<library>/<footprint>` strings when the exact KiCad library footprint is known.
- Record the expected pad-number set separately so handoff can reject a footprint mismatch.
- Put `pcbX`, `pcbY`, `pcbRotation`, and `layer` in source. If viewer moves are accepted, commit
  the resulting manual edits and ensure the normalized manifest reflects them.
- Use centered coordinates with X right and Y up. Declare the affine transform to KiCad explicitly
  in the board specification. Do not infer it from current part locations.
- Name every electrical net. Mark unused IC pins intentionally and preserve them in parity checks.
- Separate schematic sections and place them deliberately enough to review visually.
- Use tscircuit traces as connectivity. Autorouted copper is a review aid unless the board's
  release contract explicitly makes it production authority.

## Required checks

Run the pinned local CLI, not `bunx` against an unpinned release:

```bash
cd pcb
bun run typecheck
bun run check:pcb-03
bun run build:pcb-03
bun run handoff:pcb-03
```

Also run `tsci check source`, `netlist`, `pin_specification`, `schematic-placement`, and
`placement` against a new board. Inspect the schematic and PCB renders; passing JSON checks do not
prove readable schematic layout, connector direction, courtyard clearance, or useful placement.

## Viewer

Run `cd pcb && bun run dev:pcb-03` for the validation board. The viewer is local because it must
read and update the checkout's source/manual edits. Hosting it or wrapping it in an MCP is not part
of the initial workflow. Add that only if remote review or structured edit automation becomes a
real requirement.
