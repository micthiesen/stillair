# PCB tools

The shared native/workflow helpers are available for future source/native changes.
Stillair has not configured `pcb/workflow.json` or a readiness profile for them.
Installing the tools does not migrate or reaccept PCB-01, PCB-01 V2, PCB-02 or the
released PCB-03. These remain KiCad-authoritative and use their existing commands
and release evidence. Do not copy Crystal Shim's profiles or geometry here.

## One checked change lifecycle

Agree on the visual direction before detailed placement, then record dimensions,
mounting, connector directions, layer roles and assembly limits in canonical specs.
Keep images as references; they do not select circuitry or exact component geometry.
Define every required preparation check before assigning implementation so paste,
service labels and export requirements do not reopen an otherwise finished handoff.

| Stage | Result |
| --- | --- |
| `doctor` | Installed capabilities and project configuration are checked before choosing an automation path. Unsupported operations stay explicit. |
| `begin` | Retains the adopted lock, native file hashes and before snapshot. Begin before editing the native project. |
| `plan` | Rebuilds source, compares the accepted baseline and records the complete target/ECO with its input hashes. |
| `draft-transaction` | Drafts same-side placement changes only and rejects every other plan change. Review associated track/via/zone UUIDs explicitly. A draft is not application or acceptance. |
| `apply` | Runs the supported native transaction against the bound before state, saves and reopens the candidate, then verifies saved readback. |
| `validate` | Runs source checks, strict ERC, source/native parity, fresh native DRC, the complete preparation profile and fresh renders. It does not modify production native files. |
| `review` | Records actual inspection of the current validation/renders across visual contract, schematics, placement/copper and assembly/process. |
| `accept` | Rechecks current inputs, complete checks and resolved review, then advances the existing handoff lock once. |
| `status` | Reports the retained stage; a prior success does not excuse changed inputs. |

The coordinator is `pcb_workflow.py`; run `python3 pcb/tools/pcb_workflow.py --help`
for its current flags. `begin` through `accept` coordinates an ECO to an adopted
source/native handoff. First adoption still uses the staged `tscircuit_handoff.py`
export and acceptance path. A standalone `validate` can audit an existing configured
board but cannot invent the baseline and plan needed for acceptance.

Review can be performed by the agent or owner within existing authorization. The
review record names the reviewer, binds the exact validation object and records
concrete findings/evidence in all four scopes. The tool cannot inspect a picture
or resolve an electrical question on the reviewer's behalf. Apply corrections,
validate again and review the new evidence before final acceptance. Tool failures
and unsupported capabilities do not create new permission gates.

The review JSON has this shape. Replace each placeholder with actual inspection
findings and the current `validation` value from `run.json`:

```json
{
  "validation": "<current validation object SHA-256>",
  "reviewer": "<reviewer name>",
  "scopes": {
    "visual_contract": "<visual and dimensional findings>",
    "schematics": "<schematic and electrical findings>",
    "placement_and_copper": "<placement and layer render findings>",
    "assembly_and_process": "<paste, labels, stack and order findings>"
  },
  "unresolved_findings": []
}
```

## Evidence and configuration

A run has a small `run.json` index and `objects/<sha256>.json` evidence objects.
Identical retained JSON content shares an object within that run. Keep the index,
referenced objects and reviewed renders together. Do not copy repeated full
snapshots into successive closure reports or substitute a bare `passed: true`.
The coordinator binds source, native project files, canonical contracts, reference
images, profiles and checker code. A changed input or modified evidence invalidates
stale validation/review. Canonical docs describe the current target; STATE points to
the current acceptance and remaining routing/commissioning work.

`pcb/workflow.json` and `pcb/tools/readiness-profiles.json` are project-owned.
They select board paths, source commands, specification/image inputs and exact
preparation requirements. They are not shared copies. A missing or unsupported
profile is an explicit configuration failure, never a skipped audit or inherited
permission to use another board's limits.

A reviewed source-checker limitation, when a project needs one, binds the exact
command, nonzero exit code, stdout digest and stderr digest. Its raw failure and
reason remain in the evidence, with required native counterchecks. Any changed
output fails closed. This is an accounted-for checker limitation, not a clean source
check or permission to ignore further findings. Never inherit another project's
limitation record.

`pcb_readiness.py` performs read-only checks of geometry, physical stack, planes,
vias, native rules, routing policy, paste, labels and declared exclusions. It uses
native geometry plus saved settings where SWIG lacks a readable API. Profiles
must declare all supported check categories. Project callbacks retain specialized
checks without embedding product rules in the generic engine. This is preparation
validation, not zero-unconnected routed acceptance or physical commissioning.
Inspect the declared assembly/export contract during final review as well.

## Verified write helpers and limits

Prefer a supported helper over GUI repetition or a new board-specific script.
Discover capabilities first and test uncertainty on explicit scratch copies.
Never infer support from the name of a tool or from a success flag alone.

| Operation | Supported path and limit |
| --- | --- |
| Footprint moves and associated copper; rectangular outlines | `kicad_native.py`, with UUID-bound from/to geometry and explicitly associated items. |
| Pad paste, existing footprint fields, labels | Verified native transaction operations with saved readback. |
| Straight tracks, through vias, simple zones | Verified native operations; complex zone holes, blind/buried/microvias and arbitrary geometry are not implied. |
| Existing netclass sizes | Verified native settings operation; netclass assignment changes are not currently supported. |
| Interactive router preferences | No verified native writer. The in-memory board settings do not prove the GUI session preference was saved in `.kicad_prl`. |
| Existing schematic Value, MPN, Description, Datasheet and Footprint | `kicad_schematic.py`, one explicit leaf sheet and existing string properties only. |
| Schematic Reference rename, new properties, BOM/position/DNP flags | Not supported by the schematic bridge. Use an independently verified operation or the GUI and recheck parity. |
| Physical stack materials/thickness | No verified automated writer in these helpers. KiCad 10 SWIG exposes an opaque stack descriptor; enabling layers does not set the physical stack. |
| Custom-rule file installation | No verified native installer in the helper. Use the supported GUI path; native CLI DRC verifies the installed adjacent rules. |
| Footprint replacement | Not implemented by the generic native transaction. Requires source-aware footprint/pad identity mapping and a verified application path. |

Read exact operations with:

```sh
sh pcb/tools/kicad_python.sh pcb/tools/kicad_native.py capabilities
python3 pcb/tools/kicad_schematic.py --help
```

Use `sh pcb/tools/kicad_python.sh pcb/tools/kicad_native.py inspect --board PATH`
to obtain UUIDs, exact current states and input hashes without writing a discovery
script. The returned saved state supplies transaction `from` values.

Native transactions bind every project input in `before_files`, preflight the whole
batch, load the actual project settings, fill, save and reopen a scratch candidate,
and compare each requested result and saved readback before publication. Native publication replaces files
individually; it is not atomic across a project. Transaction/editor locks and stale
hash checks protect known concurrent changes. Keep the project closed during an
apply. A publication failure attempts guarded rollback and retains recovery files
when it cannot restore safely. Read the reported state instead of retrying blindly.
A native-application receipt alone does not prove electrical correctness, DRC or
acceptance; the external validator and workflow gates establish those separately.

Schematic batches use Konnect's local stdio MCP binary, not an external account.
The wrapper runs the batch on a scratch leaf, verifies every requested property
and the entire semantic tree, compares fresh native net connectivity, and atomically
publishes only verified Konnect-produced bytes. It refuses ambiguous/duplicate
properties, missing fields, partial results, stale inputs and unexpected changes.
Quotes, backslashes and control characters in edited old/new values are deliberately
unsupported while the installed upstream string handling remains unsafe.

Example request for an existing leaf property:

```json
{
  "schema_version": 1,
  "before_sha256": "<SHA-256 of the current leaf schematic>",
  "edits": [{"reference": "J1", "fields": {"MPN": "NEW-PART-NUMBER"}}]
}
```

Pass this JSON to `kicad_schematic.py leaf.kicad_sch request.json --receipt receipt.json`.
Use `--konnect-command` and `--kicad-cli-command` with JSON argv arrays to select the
installed executables. A root schematic containing hierarchical sheets is not the
leaf containing a component. All wrappers use argv arrays rather than shell code.

The [shared Konnect skill](../../.agents/skills/konnect/SKILL.md#choose-the-write-path-before-implementation)
links the inspected 0.2.1 implementation: single-component `fields` are ignored,
annotation appends duplicate keys, batch edits can partially succeed or corrupt
quoting, and design/layer-rule setters write the wrong KiCad 10 locations. These
are measured limits, not reasons to repeat the same failing calls.

## Stillair commands and existing handoff

Use the local PCB-03 source checks and established board-specific tools below.
Before enabling the coordinator, define a Stillair-owned profile for a compatible
adopted source handoff, supported readiness checks, canonical specifications and
actual runtime commands. Missing configuration is explicit; no released board has
been implicitly audited by this sync.

The generic stdlib suites run without a board:

```sh
python3 -m unittest discover -s pcb/tools -p 'test_kicad_*.py'
python3 -m unittest discover -s pcb/tools -p 'test_pcb_*.py'
```

Native integration tests require an installed KiCad runtime and use scratch
projects. Record actual runtime evidence separately from skipped tests.

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
one temporary run, so separately supplied or stale reports cannot pass. It requires error,
warning and excluded severities, rejects ignored checks and any excluded finding, and
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
