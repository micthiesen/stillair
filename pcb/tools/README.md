# PCB tools

`tscircuit_handoff.py` is the new-board boundary. It validates normalized authoritative source,
stages the one-time KiCad export, records an accepted lock, and plans later ECOs without writing a
production KiCad project.

Acceptance is byte-bound to every staged `.kicad_*` file listed in `handoff-receipt.json`. Moving
the complete stage directory is safe, but changing its board, root schematic, or child schematic
after staging makes `accept` fail. Native staging and acceptance are currently macOS-only.

The initial exporter fixture may retain only the differences explicitly declared by
`schematic_cleanup`; its receipt lists each reference, expected value, and observed value. After
performing that cleanup in KiCad, run this against the current root schematic before routing or
fabrication:

```bash
python3 pcb/tools/tscircuit_handoff.py verify-schematic-cleanup \
  pcb/dist/pcb-03/design/design-manifest.normalized.json \
  --augmentation pcb/pcb-03/design/kicad-augment.json \
  --schematic /path/to/current/root.kicad_sch \
  --output /path/to/schematic-cleanup-report.json
```

The command invokes the discovered `kicad-cli` itself and derives the XML netlist and JSON ERC in
one temporary run, so separately supplied or stale reports cannot pass. It requires error and
warning severities, rejects ignored checks unless the augmentation declares their exact keys, and
then requires exact references, values, symbol IDs, footprints, MPNs, Datasheets, pin sets, net
endpoints, and a clean ERC result. A failing report must not be used to start routing.

`check_drc.py`, `jlc_fab.py`, `refill_zones.py`, `render_board.sh`, `probe_guide.py`, and the
board-specific `pcbnew` augmentation scripts are downstream KiCad tools. Their writes use KiCad's
native API and must follow the protected-file and preservation checks in the `/pcb` and `konnect`
skills.

The PCB-01 placement planners (`board_model.py`, `check_moves.py`, `check_plan.py`,
`make_briefs.py`, `park_unplaced.py`, `place_targeted.py`, and `validate_group.py`) are retained only
as legacy analysis/history. They are not an authoring or update path for a tscircuit-first board.
The two scripts that directly rewrote protected KiCad text were removed; git history retains them.
