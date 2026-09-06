# KiCad handoff and ECOs

## Initial handoff

The handoff command must export into a task-specific staging directory, never the production board
directory. Validate these before adoption:

- exact electrical refs, values, and pin sets;
- schematic symbol, footprint-property, MPN, and datasheet differences only when an exact cleanup
  augmentation declares how they will be restored from the source manifest;
- footprint pad-number sets against part definitions;
- net endpoint multiset, including intentional unconnected pins;
- board dimensions, outline, holes, positions, sides, rotations, and connector directions;
- source and tool version fingerprints;
- KiCad parse, ERC, pre-route DRC, and schematic/PCB renders.

The native pcbnew handoff currently runs on macOS with the installed KiCad bundle. CI validates the
source, multi-file exporter wrapper, and pure handoff logic, but it is not a substitute for this
local KiCad gate.

Record the explicit coordinate transform. Tscircuit uses centered X-right/Y-up coordinates. KiCad
uses X-right/Y-down in this project. Record stable ID to ref and KiCad symbol/footprint UUID mapping
when the staged seed is adopted.

The board package's `handoff:<board>` command prints the stage directory only after hierarchy,
KiCad parsing, declared-finding policy, schematic netlist parity, and board parity pass. After the
reviewed seed is actually adopted, create `design/handoff.lock.json` with:

```bash
python3 tools/tscircuit_handoff.py accept \
  dist/<board>/design/design-manifest.normalized.json \
  --augmentation <board>/design/kicad-augment.json \
  --snapshot <stage>/staged-kicad-snapshot.json \
  --receipt <stage>/handoff-receipt.json \
  --lock <board>/design/handoff.lock.json
```

Do not create a lock for a validation-only stage that was not adopted as the production seed.
Acceptance binds the lock to the exact bytes of every generated KiCad board and schematic in the
stage receipt. After applying declared schematic cleanup to the adopted KiCad project, run the
`verify-schematic-cleanup` command documented in `pcb/tools/README.md`. It requires exact symbol,
field, pin, and net parity plus a clean ERC report. Do not start routing until it passes.

## Augmentation manifest

`kicad-augment.json` is the contract for downstream-only behavior. It names each required category,
why tscircuit does not own it, how it is applied, and how it is verified. Common categories are
stackup, controlled impedance, net classes, custom DRC rules, zones, special vias, mask/paste
exceptions, production silkscreen, routing, and fabrication exports.

No category may be marked complete merely because KiCad can represent it. Verification must query
the saved board or inspect a generated artifact.

## Updating after routing starts

Generate an ECO plan from the new source manifest and accepted lock. Never fully regenerate over
the production board. Apply only reviewed operations through KiCad GUI, Konnect, or the native API.

Risk classes:

- normal: value, field, or net-name-only change with unchanged endpoints;
- guarded: add/remove component, endpoint change, move, or rotation after routing;
- destructive: footprint/pad map, layer count, hole, outline, or coordinate-transform change.

Before applying, take a semantic snapshot of routes, vias, zones, graphics, stackup/rules, and UUIDs.
After applying, compare that state and reject unexplained changes. Then compare the source-owned
domains back to the new manifest, run ERC/DRC, and inspect renders. Update the lock last.

The removed direct-text board writers are historical board-specific migrations retained only in
git history, not an allowed ECO mechanism. Do not restore or run them on a new-board workflow.
