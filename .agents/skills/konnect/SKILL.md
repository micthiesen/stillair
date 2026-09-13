---
name: konnect
description: "Safety rules for downstream work on an existing KiCad project: handoff/ECO application, routing, zones, DRC, fabrication, or any mutation of .kicad_* files. Tscircuit authoring alone does not trigger this skill."
---

# Safe KiCad mutation

KiCad files are serialized object graphs with UUIDs and cross-references. Never modify
`*.kicad_sch`, `*.kicad_pcb`, `*.kicad_pro`, `*.kicad_sym`, `*.kicad_mod`, `sym-lib-table`, or
`fp-lib-table` with text manipulation.

The only allowed write channels are:

1. the pinned tscircuit exporter creating a new initial seed in a staging directory;
2. KiCad GUI;
3. a verified Konnect operation;
4. KiCad's native API, followed by saving through KiCad.

After initial adoption, never export over the production board. Tscircuit changes become an ECO
plan and are applied through channels 2 through 4. A board-specific script that rewrites KiCad text
is historical migration code, not an allowed channel.

Prefer `kicad-cli` exports or semantic snapshots for reads. Read source files directly only when an
export cannot answer the question, and never write them.

Before each Konnect PCB mutation (placing, moving, or rotating components; routing
traces, differential pairs, or pad-to-pad connections; adding vias; or refilling
zones), run the installed guard and stop if it fails:

```bash
~/Documents/KiCad/10.0/3rdparty/plugins/com_github_mixelpixx_konnect/bin/konnect skill pre-pcb-ipc
```

## Choose the write path before implementation

Run the project's workflow `doctor` and inspect the native helper's capabilities
before planning automation. Tool names and schemas are not capability evidence.
Use `pcb/tools/kicad_native.py` for its verified native operations and
`pcb/tools/kicad_schematic.py` for its verified existing-field subset. Runtime
commands are configurable; do not assume one installation path works on every host.
These helpers do not replace source/ECO, preservation or release checks.

Probe uncertain operations only on isolated project copies, with explicit paths
and hashes. Never test a capability against the user's open production board.
Prefer a complete declared transaction and saved readback over a succession of
unverified writes. Load the project settings before native board operations or
zone fill, then save through KiCad; loading only a board omits project rules.

The schematic bridge runs a local Konnect batch on a scratch leaf schematic,
compares the complete semantic tree and fresh native netlists, and publishes only
verified Konnect-produced bytes. It does not serialize KiCad files. Its request is
bound to the current file hash and it refuses duplicate/missing properties,
partial results, collateral changes and stale/concurrent input.

Supported fields are existing string properties such as Value, MPN, Description,
Datasheet and Footprint. Reference changes, new properties, BOM/position/DNP flags,
hierarchical-root edits, and unsafe quote/backslash/control content are unsupported.
Pass the actual leaf sheet containing the references. Resolve source parity after
field changes; successful file editing is not design acceptance.

Konnect 0.2.1 has verified defects:

- [Single-component editing](https://github.com/mixelpixx/Konnect/blob/3fac62638dd17cc98e1004e0b80cc62d12bfe943/crates/konnect-core/src/tools/sch_components.rs#L424)
  advertises `fields` but never processes it. An empty changes list can be returned
  with success.
- [Annotation](https://github.com/mixelpixx/Konnect/blob/3fac62638dd17cc98e1004e0b80cc62d12bfe943/crates/konnect-core/src/tools/sch_components.rs#L903)
  appends a property even when that key exists. Do not use it to replace an MPN.
- [Batch editing](https://github.com/mixelpixx/Konnect/blob/3fac62638dd17cc98e1004e0b80cc62d12bfe943/crates/konnect-core/src/tools/sch_batch.rs#L559)
  handles existing fields but can write a partial result or malformed quoting.
  Use the guarded bridge, not an unchecked batch success flag.
- [Design/layer-rule setters](https://github.com/mixelpixx/Konnect/blob/3fac62638dd17cc98e1004e0b80cc62d12bfe943/crates/konnect-core/src/tools/verification.rs#L290)
  write constraints into PCB setup rather than the correct KiCad 10 settings/rule
  locations. Do not use them.

Physical stack details and custom-rule installation require an explicitly verified
write path. An opaque SWIG object or an unimplemented IPC message is not one.
Treat these as reported capability limits, use the established native/GUI path for
that operation, and continue independent work. Do not retry an unreliable operation
or invent a protected-file text patch. Existing user authorization still applies;
capability limits do not introduce approval requirements.

## Apply and verify

For each write:

1. identify the exact project and its authorized source handoff/ECO plan;
2. retain the before hashes, geometry and rules, including existing routes;
3. apply only declared supported operations, using scratch-first batches;
4. re-query saved files and prove requested changes plus unrelated-state preservation;
5. run source parity, strict ERC, native DRC and the full preparation audit;
6. inspect current renders and resolve correctness findings, then accept once.

The preparation audit covers stack, planes/pours, vias, netclass trunk sizes and
bounded pad escapes, paste/stencil, service labels and declared exclusions before
the final acceptance. Project profiles supply limits; generic tools do not add
components, circuits or fabrication requirements. Record one current acceptance
index with hash-bound evidence. A changed design/profile/checker invalidates old
validation and review; a passed tool result alone never proves routing or fabrication
readiness.

Konnect availability does not make every operation safe. Use only operations already verified on
the installed KiCad/Konnect versions. Use the KiCad GUI when project settings or an MCP operation is
unreliable. Never use Konnect's manufacturing validator or manufacturing-package exporter for a
release decision.
