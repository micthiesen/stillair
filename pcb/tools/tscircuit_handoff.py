#!/usr/bin/env python3
"""Fail-closed tscircuit to KiCad handoff and ECO planner.

This tool never edits a production KiCad source file.  It normalizes the
manifest emitted by the TypeScript design, stages an initial KiCad export in a
new temporary directory, records an accepted handoff lock, and plans later
ECOs.  A separate KiCad GUI/IPC operation applies an approved plan.

The source manifest is deliberately independent of Circuit JSON's generated
IDs.  Every component and net has an explicit immutable ``stable_id``.

Typical use:

  tscircuit_handoff.py normalize design-manifest.json -o manifest.normalized.json
  tscircuit_handoff.py stage manifest.normalized.json \
      --augmentation kicad-augmentation.json \
      --build-command '["bun","run","build:pcb-03"]' \
      --export-command '["bun","run","export:kicad:pcb-03"]'
  tscircuit_handoff.py accept manifest.normalized.json \
      --augmentation kicad-augmentation.json --snapshot kicad-snapshot.json \
      --lock handoff.lock.json
  tscircuit_handoff.py plan manifest.normalized.json \
      --augmentation kicad-augmentation.json --snapshot kicad-snapshot.json \
      --lock handoff.lock.json -o eco-plan.json

Native staging, snapshot, augmentation, and acceptance are supported on macOS
only until pcbnew runtime discovery is verified on Linux and Windows.

Build/export commands receive STILLAIR_HANDOFF_STAGE, STILLAIR_HANDOFF_MANIFEST,
and STILLAIR_HANDOFF_AUGMENTATION.  They must put every generated ``.kicad_*``
file below STILLAIR_HANDOFF_STAGE.  Existing production KiCad files are hashed
before and after both commands and any change fails the stage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterable, Optional, Union


SCHEMA_VERSION = 1
PROTECTED_SUFFIXES = {
    ".kicad_pcb",
    ".kicad_sch",
    ".kicad_pro",
    ".kicad_sym",
    ".kicad_mod",
}
PROTECTED_BASENAMES = {"fp-lib-table", "sym-lib-table"}
REQUIRED_VERSIONS = {"tscircuit", "circuit_json_to_kicad", "node"}
REF_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*[0-9]+$")
RISK_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3}
ALLOWED_AUGMENTATIONS = {
    "coordinate_transform",
    "custom_rule",
    "fabrication_note",
    "footprint_override",
    "impedance",
    "keepout",
    "mask_override",
    "net_alias",
    "net_class",
    "paste_override",
    "pofv",
    "schematic_cleanup",
    "silkscreen",
    "stackup",
    "zone",
}
ALLOWED_INITIAL_SCHEMATIC_DIFFERENCES = {
    "datasheet",
    "manufacturer_part_number",
    "symbol_id",
    "value_format",
}
ROUTED_BLOCKED_CHANGES = {
    "board_spec",
    "component_add",
    "component_remove",
    "footprint",
    "net_add",
    "net_endpoints",
    "net_remove",
    "net_rename",
    "pad_set",
    "reference",
    "symbol",
}


class HandoffError(ValueError):
    """A validation or safety gate failed."""


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoffError(f"cannot read JSON {path}: {exc}") from exc


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def is_protected_path(path: Path) -> bool:
    return (
        path.suffix.lower() in PROTECTED_SUFFIXES
        or ".kicad_" in path.name.lower()
        or path.name in PROTECTED_BASENAMES
    )


def atomic_write_json(path: Path, value: Any) -> None:
    if is_protected_path(path):
        raise HandoffError(f"refusing to write protected KiCad source: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temp, path)


def require_object(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise HandoffError(f"{where} must be an object")
    return value


def require_list(value: Any, where: str) -> list[Any]:
    if not isinstance(value, list):
        raise HandoffError(f"{where} must be an array")
    return value


def require_string(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HandoffError(f"{where} must be a non-empty string")
    return value.strip()


def finite_number(value: Any, where: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise HandoffError(f"{where} must be a number")
    result = float(value)
    if not math.isfinite(result):
        raise HandoffError(f"{where} must be finite")
    return result


def normalize_number(value: Any, where: str) -> Union[int, float]:
    number = finite_number(value, where)
    return int(number) if number.is_integer() else number


def ensure_json_value(value: Any, where: str) -> Any:
    """Reject values JSON accepts loosely (NaN/Infinity) and canonicalize maps."""
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return normalize_number(value, where)
    if isinstance(value, list):
        return [ensure_json_value(item, f"{where}[]") for item in value]
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise HandoffError(f"{where} has a non-string key")
        return {
            key: ensure_json_value(value[key], f"{where}.{key}")
            for key in sorted(value)
        }
    raise HandoffError(f"{where} contains unsupported value {type(value).__name__}")


def normalize_placement(raw: Any, where: str) -> dict[str, Any]:
    placement = require_object(raw, where)
    side = placement.get("side", "front")
    if side not in {"front", "back"}:
        raise HandoffError(f"{where}.side must be front or back")
    return {
        "rotation_deg": normalize_number(
            finite_number(placement.get("rotation_deg", 0), f"{where}.rotation_deg") % 360,
            f"{where}.rotation_deg",
        ),
        "side": side,
        "x_mm": normalize_number(placement.get("x_mm"), f"{where}.x_mm"),
        "y_mm": normalize_number(placement.get("y_mm"), f"{where}.y_mm"),
    }


def normalize_manifest(raw: Any) -> dict[str, Any]:
    root = require_object(raw, "manifest")
    schema = root.get("schema_version", SCHEMA_VERSION)
    if schema != SCHEMA_VERSION:
        raise HandoffError(f"unsupported manifest schema_version {schema!r}")

    board_raw = require_object(root.get("board"), "manifest.board")
    board_id = require_string(board_raw.get("stable_id"), "manifest.board.stable_id")
    width = normalize_number(board_raw.get("width_mm"), "manifest.board.width_mm")
    height = normalize_number(board_raw.get("height_mm"), "manifest.board.height_mm")
    if width <= 0 or height <= 0:
        raise HandoffError("manifest.board width and height must be positive")
    layers = board_raw.get("layer_count")
    if not isinstance(layers, int) or isinstance(layers, bool) or layers < 2:
        raise HandoffError("manifest.board.layer_count must be an integer >= 2")
    coordinate_system = board_raw.get("coordinate_system", "center-x-right-y-up")
    if coordinate_system not in {"center-x-right-y-up"}:
        raise HandoffError(
            "manifest.board.coordinate_system must be center-x-right-y-up"
        )
    board = {
        "coordinate_system": coordinate_system,
        "height_mm": height,
        "layer_count": layers,
        "specs": ensure_json_value(board_raw.get("specs", {}), "manifest.board.specs"),
        "stable_id": board_id,
        "width_mm": width,
    }
    if "kicad_origin_mm" in board_raw:
        origin = require_list(board_raw["kicad_origin_mm"], "manifest.board.kicad_origin_mm")
        if len(origin) != 2:
            raise HandoffError("manifest.board.kicad_origin_mm must contain [x, y]")
        board["kicad_origin_mm"] = [
            normalize_number(origin[0], "manifest.board.kicad_origin_mm[0]"),
            normalize_number(origin[1], "manifest.board.kicad_origin_mm[1]"),
        ]
    holes = []
    seen_hole_ids: set[str] = set()
    seen_hole_refs: set[str] = set()
    for index, raw_hole in enumerate(
        require_list(board_raw.get("holes", []), "manifest.board.holes")
    ):
        where = f"manifest.board.holes[{index}]"
        hole = require_object(raw_hole, where)
        stable_id = require_string(hole.get("stable_id"), f"{where}.stable_id")
        ref = require_string(hole.get("ref"), f"{where}.ref")
        if stable_id in seen_hole_ids or ref in seen_hole_refs:
            raise HandoffError(f"duplicate board hole identity at {where}")
        seen_hole_ids.add(stable_id)
        seen_hole_refs.add(ref)
        drill = normalize_number(hole.get("drill_mm"), f"{where}.drill_mm")
        if drill <= 0:
            raise HandoffError(f"{where}.drill_mm must be positive")
        holes.append(
            {
                "drill_mm": drill,
                "ref": ref,
                "stable_id": stable_id,
                "x_mm": normalize_number(hole.get("x_mm"), f"{where}.x_mm"),
                "y_mm": normalize_number(hole.get("y_mm"), f"{where}.y_mm"),
            }
        )
    board["holes"] = sorted(holes, key=lambda item: item["stable_id"])
    if "outline" in board_raw:
        board["outline"] = ensure_json_value(board_raw["outline"], "manifest.board.outline")

    versions_raw = require_object(root.get("versions"), "manifest.versions")
    versions = {
        require_string(key, "manifest.versions key"): require_string(
            value, f"manifest.versions.{key}"
        )
        for key, value in versions_raw.items()
    }
    missing_versions = sorted(REQUIRED_VERSIONS - versions.keys())
    if missing_versions:
        raise HandoffError(
            "manifest.versions is missing required tool versions: "
            + ", ".join(missing_versions)
        )

    components = []
    stable_ids: set[str] = set()
    references: set[str] = set()
    pads_by_id: dict[str, set[str]] = {}
    for index, item in enumerate(require_list(root.get("components"), "manifest.components")):
        where = f"manifest.components[{index}]"
        component = require_object(item, where)
        stable_id = require_string(component.get("stable_id"), f"{where}.stable_id")
        ref = require_string(component.get("ref"), f"{where}.ref")
        if not REF_RE.fullmatch(ref):
            raise HandoffError(f"{where}.ref is not an explicit reference: {ref!r}")
        if stable_id in stable_ids:
            raise HandoffError(f"duplicate component stable_id {stable_id!r}")
        if ref in references:
            raise HandoffError(f"duplicate component reference {ref!r}")
        stable_ids.add(stable_id)
        references.add(ref)

        footprint_raw = require_object(component.get("footprint"), f"{where}.footprint")
        pads = [require_string(pad, f"{where}.footprint.pad_numbers[]") for pad in require_list(footprint_raw.get("pad_numbers"), f"{where}.footprint.pad_numbers")]
        if len(pads) != len(set(pads)):
            raise HandoffError(f"{where}.footprint.pad_numbers contains duplicates")
        pads_by_id[stable_id] = set(pads)
        footprint = {
            "kicad": require_string(footprint_raw.get("kicad"), f"{where}.footprint.kicad"),
            "pad_numbers": sorted(pads),
            "tscircuit": require_string(footprint_raw.get("tscircuit"), f"{where}.footprint.tscircuit"),
        }
        if "kicad_sha256" in footprint_raw:
            sha = require_string(footprint_raw["kicad_sha256"], f"{where}.footprint.kicad_sha256")
            if not re.fullmatch(r"[0-9a-f]{64}", sha):
                raise HandoffError(f"{where}.footprint.kicad_sha256 must be lowercase SHA-256")
            footprint["kicad_sha256"] = sha

        normalized = {
            "fields": ensure_json_value(component.get("fields", {}), f"{where}.fields"),
            "footprint": footprint,
            "placement": normalize_placement(component.get("placement"), f"{where}.placement"),
            "ref": ref,
            "stable_id": stable_id,
            "value": require_string(component.get("value"), f"{where}.value"),
        }
        if "symbol" in component:
            normalized["symbol"] = require_string(component["symbol"], f"{where}.symbol")
        components.append(normalized)
    components.sort(key=lambda item: item["stable_id"])

    nets = []
    net_ids: set[str] = set()
    net_names: set[str] = set()
    used_endpoints: dict[tuple[str, str], str] = {}
    for index, item in enumerate(require_list(root.get("nets"), "manifest.nets")):
        where = f"manifest.nets[{index}]"
        net = require_object(item, where)
        stable_id = require_string(net.get("stable_id"), f"{where}.stable_id")
        name = require_string(net.get("name"), f"{where}.name")
        if stable_id in net_ids:
            raise HandoffError(f"duplicate net stable_id {stable_id!r}")
        if name in net_names:
            raise HandoffError(f"duplicate net name {name!r}")
        net_ids.add(stable_id)
        net_names.add(name)
        endpoints = []
        for endpoint_index, endpoint_raw in enumerate(require_list(net.get("endpoints"), f"{where}.endpoints")):
            endpoint_where = f"{where}.endpoints[{endpoint_index}]"
            endpoint = require_object(endpoint_raw, endpoint_where)
            component_id = require_string(endpoint.get("component"), f"{endpoint_where}.component")
            pad = require_string(endpoint.get("pad"), f"{endpoint_where}.pad")
            if component_id not in stable_ids:
                raise HandoffError(f"{endpoint_where} references unknown component {component_id!r}")
            if pad not in pads_by_id[component_id]:
                raise HandoffError(f"{endpoint_where} references unknown pad {component_id}.{pad}")
            key = (component_id, pad)
            if key in used_endpoints:
                raise HandoffError(
                    f"endpoint {component_id}.{pad} appears in both "
                    f"{used_endpoints[key]!r} and {stable_id!r}"
                )
            used_endpoints[key] = stable_id
            endpoints.append({"component": component_id, "pad": pad})
        nets.append({
            "endpoints": sorted(endpoints, key=lambda value: (value["component"], value["pad"])),
            "name": name,
            "stable_id": stable_id,
        })
    nets.sort(key=lambda item: item["stable_id"])

    result = {
        "board": board,
        "components": components,
        "nets": nets,
        "schema_version": SCHEMA_VERSION,
        "versions": dict(sorted(versions.items())),
    }
    if "metadata" in root:
        result["metadata"] = ensure_json_value(root["metadata"], "manifest.metadata")
    return result


def validate_augmentation(raw: Any, manifest: dict[str, Any]) -> dict[str, Any]:
    root = require_object(raw, "augmentation")
    if root.get("schema_version", SCHEMA_VERSION) != SCHEMA_VERSION:
        raise HandoffError("unsupported augmentation schema_version")
    board_id = require_string(root.get("board_id"), "augmentation.board_id")
    if board_id != manifest["board"]["stable_id"]:
        raise HandoffError(
            f"augmentation board_id {board_id!r} does not match manifest board"
        )
    component_ids = {item["stable_id"] for item in manifest["components"]}
    net_ids = {item["stable_id"] for item in manifest["nets"]}
    seen: set[str] = set()
    operations = []
    for index, raw_operation in enumerate(require_list(root.get("operations", []), "augmentation.operations")):
        where = f"augmentation.operations[{index}]"
        operation = require_object(raw_operation, where)
        operation_id = require_string(operation.get("id"), f"{where}.id")
        if operation_id in seen:
            raise HandoffError(f"duplicate augmentation operation id {operation_id!r}")
        seen.add(operation_id)
        kind = require_string(operation.get("kind"), f"{where}.kind")
        if kind not in ALLOWED_AUGMENTATIONS:
            raise HandoffError(f"{where}.kind is not supported: {kind!r}")
        if operation.get("owner", "kicad") != "kicad":
            raise HandoffError(f"{where}.owner must be kicad")
        target = require_object(operation.get("target", {}), f"{where}.target")
        component_id = target.get("component_stable_id")
        if component_id is not None and component_id not in component_ids:
            raise HandoffError(f"{where} targets unknown component {component_id!r}")
        net_id = target.get("net_stable_id")
        if net_id is not None and net_id not in net_ids:
            raise HandoffError(f"{where} targets unknown net {net_id!r}")
        params = require_object(operation.get("params", {}), f"{where}.params")
        for key in (
            "allowed_initial_drc_ignored_checks",
            "allowed_initial_erc_ignored_checks",
        ):
            if key in params:
                values = require_list(params[key], f"{where}.params.{key}")
                if not all(isinstance(item, str) and item for item in values):
                    raise HandoffError(f"{where}.params.{key} must contain strings")
        forbidden = {"board_outline", "component_placement", "schematic", "source_netlist"} & params.keys()
        if forbidden:
            raise HandoffError(
                f"{where} attempts to override tscircuit-owned fields: {sorted(forbidden)}"
            )
        if kind == "net_alias":
            if net_id is None:
                raise HandoffError(f"{where} net_alias requires target.net_stable_id")
            require_string(params.get("source_name"), f"{where}.params.source_name")
            require_string(params.get("kicad_name"), f"{where}.params.kicad_name")
        elif kind == "coordinate_transform":
            for key in ("tscircuit_center_mm", "kicad_center_mm"):
                point = require_list(params.get(key), f"{where}.params.{key}")
                if len(point) != 2:
                    raise HandoffError(f"{where}.params.{key} must contain [x, y]")
                finite_number(point[0], f"{where}.params.{key}[0]")
                finite_number(point[1], f"{where}.params.{key}[1]")
            if params.get("x_axis") != "same" or params.get("y_axis") != "invert":
                raise HandoffError(
                    f"{where} must map x_axis=same and y_axis=invert"
                )
        elif kind == "stackup":
            if params.get("layer_count") != manifest["board"]["layer_count"]:
                raise HandoffError(
                    f"{where}.params.layer_count must match the tscircuit board spec"
                )
            for key in ("copper_weight_oz", "thickness_mm"):
                if finite_number(params.get(key), f"{where}.params.{key}") <= 0:
                    raise HandoffError(f"{where}.params.{key} must be positive")
        elif kind == "zone" and net_id is None:
            raise HandoffError(f"{where} zone requires target.net_stable_id")
        elif kind == "schematic_cleanup":
            categories = require_list(
                params.get("allowed_initial_erc_types"),
                f"{where}.params.allowed_initial_erc_types",
            )
            if not categories or not all(isinstance(item, str) and item for item in categories):
                raise HandoffError(
                    f"{where}.params.allowed_initial_erc_types must contain strings"
                )
            require_string(params.get("verification"), f"{where}.params.verification")
            semantic_differences = require_list(
                params.get("allowed_initial_semantic_differences", []),
                f"{where}.params.allowed_initial_semantic_differences",
            )
            unknown_differences = sorted(
                set(semantic_differences) - ALLOWED_INITIAL_SCHEMATIC_DIFFERENCES
            )
            if unknown_differences or not all(
                isinstance(item, str) and item for item in semantic_differences
            ):
                raise HandoffError(
                    f"{where}.params.allowed_initial_semantic_differences contains "
                    f"unsupported values: {unknown_differences}"
                )
        operations.append({
            "id": operation_id,
            "kind": kind,
            "owner": "kicad",
            "params": ensure_json_value(params, f"{where}.params"),
            "target": ensure_json_value(target, f"{where}.target"),
        })
    return {
        "board_id": board_id,
        "operations": sorted(operations, key=lambda operation: operation["id"]),
        "schema_version": SCHEMA_VERSION,
    }


def empty_augmentation(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "board_id": manifest["board"]["stable_id"],
        "operations": [],
        "schema_version": SCHEMA_VERSION,
    }


def load_manifest(path: Path) -> dict[str, Any]:
    return normalize_manifest(read_json(path))


def load_augmentation(path: Optional[Path], manifest: dict[str, Any]) -> dict[str, Any]:
    return validate_augmentation(read_json(path), manifest) if path else empty_augmentation(manifest)


def by_id(items: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {item["stable_id"]: item for item in items}


def change(kind: str, target: str, before: Any, after: Any, risk: str, reason: str) -> dict[str, Any]:
    return {
        "after": after,
        "before": before,
        "kind": kind,
        "reason": reason,
        "risk": risk,
        "target": target,
    }


def classify_changes(old: dict[str, Any], new: dict[str, Any]) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    old_components, new_components = by_id(old["components"]), by_id(new["components"])
    for stable_id in sorted(old_components.keys() | new_components.keys()):
        previous, current = old_components.get(stable_id), new_components.get(stable_id)
        if previous is None:
            changes.append(change("component_add", stable_id, None, current, "high", "adds a footprint and schematic endpoints"))
            continue
        if current is None:
            changes.append(change("component_remove", stable_id, previous, None, "high", "can orphan existing copper"))
            continue
        scalar_fields = {
            "ref": ("reference", "high", "changes the KiCad identity link"),
            "value": ("value", "low", "changes component metadata"),
            "symbol": ("symbol", "high", "changes the schematic symbol"),
            "fields": ("fields", "low", "changes component metadata"),
            "placement": ("placement", "medium", "moves or rotates a footprint"),
        }
        for field, (kind, risk, reason) in scalar_fields.items():
            if previous.get(field) != current.get(field):
                changes.append(change(kind, stable_id, previous.get(field), current.get(field), risk, reason))
        old_footprint, new_footprint = previous["footprint"], current["footprint"]
        if old_footprint["pad_numbers"] != new_footprint["pad_numbers"]:
            changes.append(change("pad_set", stable_id, old_footprint["pad_numbers"], new_footprint["pad_numbers"], "high", "changes the electrical pad contract"))
        old_identity = {key: value for key, value in old_footprint.items() if key != "pad_numbers"}
        new_identity = {key: value for key, value in new_footprint.items() if key != "pad_numbers"}
        if old_identity != new_identity:
            changes.append(change("footprint", stable_id, old_identity, new_identity, "high", "can invalidate land geometry and attached copper"))

    old_nets, new_nets = by_id(old["nets"]), by_id(new["nets"])
    for stable_id in sorted(old_nets.keys() | new_nets.keys()):
        previous, current = old_nets.get(stable_id), new_nets.get(stable_id)
        if previous is None:
            changes.append(change("net_add", stable_id, None, current, "high", "adds a logical net"))
            continue
        if current is None:
            changes.append(change("net_remove", stable_id, previous, None, "high", "can orphan routed copper"))
            continue
        if previous["name"] != current["name"]:
            changes.append(change("net_rename", stable_id, previous["name"], current["name"], "high", "must preserve net identity through KiCad update"))
        if previous["endpoints"] != current["endpoints"]:
            changes.append(change("net_endpoints", stable_id, previous["endpoints"], current["endpoints"], "high", "changes electrical connectivity"))

    if old["board"] != new["board"]:
        changes.append(change("board_spec", new["board"]["stable_id"], old["board"], new["board"], "high", "changes board-owned geometry or fabrication constraints"))
    if old.get("metadata") != new.get("metadata"):
        changes.append(change("metadata", "manifest", old.get("metadata"), new.get("metadata"), "low", "changes source metadata only"))
    if old["versions"] != new["versions"]:
        changes.append(change("tool_versions", "manifest", old["versions"], new["versions"], "low", "changes the pinned generator toolchain"))
    return changes


def normalize_snapshot(raw: Any, board_id: str) -> dict[str, Any]:
    root = require_object(raw, "snapshot")
    if require_string(root.get("board_id"), "snapshot.board_id") != board_id:
        raise HandoffError("snapshot board_id does not match manifest")
    routed = root.get("routed", False)
    if not isinstance(routed, bool):
        raise HandoffError("snapshot.routed must be boolean")
    result = {
        "board_id": board_id,
        "routed": routed,
        "source_owned": ensure_json_value(root.get("source_owned", {}), "snapshot.source_owned"),
        "kicad_owned": ensure_json_value(root.get("kicad_owned", {}), "snapshot.kicad_owned"),
    }
    if "uuid_map" in root:
        result["uuid_map"] = ensure_json_value(root["uuid_map"], "snapshot.uuid_map")
    if "schematic_owned" in root:
        result["schematic_owned"] = ensure_json_value(
            root["schematic_owned"], "snapshot.schematic_owned"
        )
    return result


def normalize_kicad_snapshot_data(
    raw: Any,
    manifest: dict[str, Any],
    routed: bool,
) -> dict[str, Any]:
    """Normalize pcbnew-extracted data and bind refs to source stable IDs.

    This pure function is also the test seam: the pcbnew adapter gathers plain
    JSON values, while all identity checks and hashing are exercised without
    requiring KiCad in unit tests.
    """
    extracted = require_object(raw, "extracted KiCad snapshot")
    expected_components = {item["ref"]: item for item in manifest["components"]}
    expected = {
        ref: item["stable_id"] for ref, item in expected_components.items()
    }
    components = []
    seen_refs: set[str] = set()
    uuid_map: dict[str, str] = {}
    for index, raw_component in enumerate(
        require_list(extracted.get("components"), "extracted.components")
    ):
        where = f"extracted.components[{index}]"
        item = require_object(raw_component, where)
        ref = require_string(item.get("ref"), f"{where}.ref")
        if ref not in expected:
            raise HandoffError(f"KiCad contains reference absent from manifest: {ref}")
        if ref in seen_refs:
            raise HandoffError(f"KiCad contains duplicate reference: {ref}")
        seen_refs.add(ref)
        stable_id = expected[ref]
        uuid = require_string(item.get("uuid"), f"{where}.uuid")
        uuid_map[stable_id] = uuid
        pads = []
        for pad in require_list(item.get("pads"), f"{where}.pads"):
            pad_obj = require_object(pad, f"{where}.pads[]")
            pads.append(
                {
                    "net": str(pad_obj.get("net", "")),
                    "number": str(pad_obj.get("number", "")),
                }
            )
        expected_component = expected_components[ref]
        observed_pad_set = {pad["number"] for pad in pads}
        expected_pad_set = set(expected_component["footprint"]["pad_numbers"])
        if observed_pad_set != expected_pad_set:
            raise HandoffError(
                f"KiCad pad set for {ref} differs from manifest: "
                f"expected={sorted(expected_pad_set)}, observed={sorted(observed_pad_set)}"
            )
        observed_footprint = require_string(
            item.get("footprint"), f"{where}.footprint"
        )
        if observed_footprint != expected_component["footprint"]["kicad"]:
            raise HandoffError(
                f"KiCad footprint for {ref} differs from manifest: "
                f"expected={expected_component['footprint']['kicad']!r}, "
                f"observed={observed_footprint!r}"
            )
        observed_value = require_string(item.get("value"), f"{where}.value")
        if observed_value != expected_component["value"]:
            raise HandoffError(
                f"KiCad value for {ref} differs from manifest: "
                f"expected={expected_component['value']!r}, observed={observed_value!r}"
            )
        components.append(
            {
                "footprint": observed_footprint,
                "pads": sorted(pads, key=lambda pad: (pad["number"], pad["net"])),
                "placement": ensure_json_value(item.get("placement"), f"{where}.placement"),
                "ref": ref,
                "stable_id": stable_id,
                "uuid": uuid,
                "value": observed_value,
            }
        )
    missing = sorted(set(expected) - seen_refs)
    if missing:
        raise HandoffError(f"KiCad is missing manifest references: {', '.join(missing)}")
    components.sort(key=lambda item: item["stable_id"])

    outline = ensure_json_value(extracted.get("outline", []), "extracted.outline")
    holes = ensure_json_value(extracted.get("holes", []), "extracted.holes")
    source_owned = {
        "components": components,
        "holes": sorted(holes, key=canonical_json),
        "outline": sorted(outline, key=canonical_json),
    }
    kicad_owned = {}
    for key in ("tracks", "vias", "zones", "graphics", "rules"):
        details = ensure_json_value(extracted.get(key, []), f"extracted.{key}")
        if isinstance(details, list):
            details = sorted(details, key=canonical_json)
        kicad_owned[key] = {"details": details, "sha256": digest(details)}
    return {
        "board_id": manifest["board"]["stable_id"],
        "kicad_owned": kicad_owned,
        "routed": routed,
        "source_owned": source_owned,
        "uuid_map": dict(sorted(uuid_map.items())),
    }


def coordinate_transform(augmentation: dict[str, Any]) -> dict[str, Any]:
    transforms = [
        operation
        for operation in augmentation["operations"]
        if operation["kind"] == "coordinate_transform"
    ]
    if len(transforms) != 1:
        raise HandoffError(
            "augmentation must contain exactly one coordinate_transform operation"
        )
    return transforms[0]["params"]


def source_to_kicad_xy(
    x_mm: float,
    y_mm: float,
    augmentation: dict[str, Any],
) -> list[Union[int, float]]:
    transform = coordinate_transform(augmentation)
    source_center = transform["tscircuit_center_mm"]
    kicad_center = transform["kicad_center_mm"]
    return [
        normalize_number(kicad_center[0] + x_mm - source_center[0], "KiCad x"),
        normalize_number(kicad_center[1] - (y_mm - source_center[1]), "KiCad y"),
    ]


def _close(left: float, right: float, tolerance_mm: float = 0.002) -> bool:
    return abs(float(left) - float(right)) <= tolerance_mm


def _normalized_net_name(name: str, aliases: dict[str, str]) -> str:
    if not name or name.startswith("unconnected-("):
        return ""
    normalized = name.lstrip("/")
    return aliases.get(normalized, normalized)


def parity_errors(
    snapshot: dict[str, Any],
    manifest: dict[str, Any],
    augmentation: dict[str, Any],
) -> list[str]:
    """Compare all tscircuit-owned board semantics with a KiCad snapshot."""
    errors: list[str] = []
    aliases = {
        operation["target"]["net_stable_id"]: operation["params"]["kicad_name"]
        for operation in augmentation["operations"]
        if operation["kind"] == "net_alias"
    }
    source_aliases = {
        operation["params"]["source_name"]: operation["params"]["kicad_name"]
        for operation in augmentation["operations"]
        if operation["kind"] == "net_alias"
    }
    expected_pad_nets: dict[tuple[str, str], str] = {}
    for net in manifest["nets"]:
        expected_name = aliases.get(net["stable_id"], net["name"])
        for endpoint in net["endpoints"]:
            expected_pad_nets[(endpoint["component"], endpoint["pad"])] = expected_name

    expected_components = by_id(manifest["components"])
    actual_components = {
        item["stable_id"]: item for item in snapshot["source_owned"]["components"]
    }
    if set(expected_components) != set(actual_components):
        errors.append(
            "component stable IDs differ: "
            f"expected={sorted(expected_components)}, actual={sorted(actual_components)}"
        )
    for stable_id in sorted(expected_components.keys() & actual_components.keys()):
        expected = expected_components[stable_id]
        actual = actual_components[stable_id]
        if expected["ref"] != actual["ref"]:
            errors.append(f"{stable_id} reference differs")
        if expected["value"] != actual["value"]:
            errors.append(f"{expected['ref']} value differs")
        if expected["footprint"]["kicad"] != actual["footprint"]:
            errors.append(f"{expected['ref']} footprint differs")
        actual_pads = {
            pad["number"]: _normalized_net_name(pad["net"], source_aliases)
            for pad in actual["pads"]
        }
        expected_pads = set(expected["footprint"]["pad_numbers"])
        if expected_pads != set(actual_pads):
            errors.append(f"{expected['ref']} pad set differs")
        for pad_number in sorted(expected_pads & set(actual_pads)):
            expected_net = expected_pad_nets.get((stable_id, pad_number), "")
            if actual_pads[pad_number] != expected_net:
                errors.append(
                    f"{expected['ref']}.{pad_number} net differs: "
                    f"expected={expected_net!r}, actual={actual_pads[pad_number]!r}"
                )

        expected_position = source_to_kicad_xy(
            expected["placement"]["x_mm"],
            expected["placement"]["y_mm"],
            augmentation,
        )
        actual_placement = actual["placement"]
        actual_position = actual_placement.get("position_mm", [])
        if len(actual_position) != 2 or not all(
            _close(expected_position[index], actual_position[index]) for index in range(2)
        ):
            errors.append(
                f"{expected['ref']} position differs: "
                f"expected={expected_position}, actual={actual_position}"
            )
        expected_rotation = expected["placement"]["rotation_deg"] % 360
        actual_rotation = float(actual_placement.get("rotation_deg", -1)) % 360
        if not _close(expected_rotation, actual_rotation, 0.001):
            errors.append(
                f"{expected['ref']} rotation differs: "
                f"expected={expected_rotation}, actual={actual_rotation}"
            )
        if expected["placement"]["side"] != actual_placement.get("side"):
            errors.append(f"{expected['ref']} side differs")

    outline = snapshot["source_owned"]["outline"]
    outline_points = []
    for item in outline:
        for key in ("start_mm", "end_mm"):
            point = item.get(key)
            if isinstance(point, list) and len(point) == 2:
                outline_points.append(point)
    source_outline = manifest["board"].get("outline")
    if not isinstance(source_outline, dict) or source_outline.get("kind") != "rectangle":
        errors.append("only a rectangular source outline can currently be parity-checked")
    elif not outline_points:
        errors.append("KiCad snapshot has no measurable Edge.Cuts outline")
    else:
        center = source_outline.get("center_mm", [0, 0])
        expected_center = source_to_kicad_xy(center[0], center[1], augmentation)
        width = float(source_outline.get("width_mm", manifest["board"]["width_mm"]))
        height = float(source_outline.get("height_mm", manifest["board"]["height_mm"]))
        expected_extents = [
            expected_center[0] - width / 2,
            expected_center[1] - height / 2,
            expected_center[0] + width / 2,
            expected_center[1] + height / 2,
        ]
        actual_extents = [
            min(point[0] for point in outline_points),
            min(point[1] for point in outline_points),
            max(point[0] for point in outline_points),
            max(point[1] for point in outline_points),
        ]
        if not all(_close(expected_extents[index], actual_extents[index]) for index in range(4)):
            errors.append(
                f"board outline differs: expected={expected_extents}, actual={actual_extents}"
            )

    unmatched_holes = list(snapshot["source_owned"]["holes"])
    for expected in manifest["board"]["holes"]:
        ref = expected["ref"]
        expected_position = source_to_kicad_xy(
            expected["x_mm"], expected["y_mm"], augmentation
        )
        matches = []
        for index, actual in enumerate(unmatched_holes):
            position = actual.get("position_mm", [])
            drill = actual.get("drill_mm", [])
            if (
                actual.get("footprint_ref") == ref
                and len(position) == 2
                and all(_close(expected_position[axis], position[axis]) for axis in range(2))
                and len(drill) == 2
                and all(_close(expected["drill_mm"], value) for value in drill)
            ):
                matches.append(index)
        if len(matches) != 1:
            errors.append(
                f"{ref} NPTH identity differs: expected one hole at "
                f"{expected_position} drill {expected['drill_mm']}, found {len(matches)}"
            )
        else:
            unmatched_holes.pop(matches[0])
    if unmatched_holes:
        errors.append(f"KiCad has {len(unmatched_holes)} unexpected NPTH hole(s)")
    return errors


def validate_schematic_hierarchy(root_schematic: Path, stage: Path) -> list[Path]:
    """Resolve every KiCad hierarchical sheet and reject escapes or omissions."""
    pending = [root_schematic.resolve()]
    seen: set[Path] = set()
    while pending:
        schematic = pending.pop()
        if schematic in seen:
            continue
        if not schematic.is_relative_to(stage.resolve()):
            raise HandoffError(f"schematic hierarchy escapes staging: {schematic}")
        if not schematic.is_file():
            raise HandoffError(f"schematic hierarchy is missing referenced file: {schematic}")
        seen.add(schematic)
        try:
            content = schematic.read_text()
        except (OSError, UnicodeDecodeError) as exc:
            raise HandoffError(f"cannot read staged schematic {schematic}: {exc}") from exc
        for filename in re.findall(r'\(property\s+"Sheetfile"\s+"([^"]+)"', content):
            child = (schematic.parent / filename).resolve()
            if child not in seen:
                pending.append(child)
    return sorted(seen)


def schematic_netlist_parity_errors(
    netlist_path: Path,
    manifest: dict[str, Any],
    augmentation: dict[str, Any],
) -> list[str]:
    """Compare a KiCad XML netlist with authoritative schematic semantics."""
    actual = schematic_snapshot_from_netlist(netlist_path)
    return schematic_snapshot_parity_errors(actual, manifest, augmentation)


def schematic_snapshot_from_netlist(netlist_path: Path) -> dict[str, Any]:
    try:
        root = ET.parse(netlist_path).getroot()
    except (OSError, ET.ParseError) as exc:
        raise HandoffError(f"cannot parse KiCad XML netlist {netlist_path}: {exc}") from exc
    components = []
    for item in root.findall("./components/comp"):
        libsource = item.find("libsource")
        fields = {
            field.get("name", ""): field.text or ""
            for field in item.findall("./fields/field")
            if field.get("name")
        }
        properties = {
            prop.get("name", ""): prop.get("value", prop.text or "")
            for prop in item.findall("./property")
            if prop.get("name")
        }
        metadata = {**fields, **properties}
        components.append({
            "datasheet": metadata.get("Datasheet", metadata.get("datasheet", "")),
            "footprint": item.findtext("footprint") or "",
            "manufacturer_part_number": metadata.get(
                "MPN", metadata.get("Manufacturer Part Number", "")
            ),
            "pins": sorted({pin.get("num", "") for pin in item.findall("./units/unit/pins/pin")}),
            "ref": item.get("ref", ""),
            "symbol": "" if libsource is None else f"{libsource.get('lib', '')}:{libsource.get('part', '')}",
            "value": item.findtext("value") or "",
        })
    nets = []
    for net in root.findall("./nets/net"):
        name = net.get("name", "").lstrip("/")
        if name.startswith("unconnected-("):
            continue
        nets.append({
            "name": name,
            "endpoints": sorted((node.get("ref", ""), node.get("pin", "")) for node in net.findall("node")),
        })
    return {
        "components": sorted(components, key=lambda item: item["ref"]),
        "nets": sorted(nets, key=lambda item: item["name"]),
    }


def schematic_snapshot_parity_errors(
    schematic: dict[str, Any],
    manifest: dict[str, Any],
    augmentation: dict[str, Any],
    *,
    strict_fields: bool = False,
    declared_differences: Optional[list[dict[str, str]]] = None,
) -> list[str]:
    expected_by_ref = {
        item["ref"]: item
        for item in manifest["components"]
        if item["footprint"]["pad_numbers"]
    }
    actual_by_ref = {item["ref"]: item for item in schematic["components"]}
    errors = []
    footprint_overrides = {
        operation["target"].get("component_stable_id"): operation["params"].get("kicad_footprint")
        for operation in augmentation["operations"]
        if operation["kind"] == "footprint_override"
    }
    allowed_initial = {
        category
        for operation in augmentation["operations"]
        if operation["kind"] == "schematic_cleanup"
        for category in operation["params"].get(
            "allowed_initial_semantic_differences", []
        )
    }

    def compare_field(
        ref: str, category: str, expected: str, actual: str, allowed: bool = False
    ) -> None:
        if expected == actual:
            return
        if not strict_fields and (allowed or category in allowed_initial):
            if declared_differences is not None:
                declared_differences.append(
                    {
                        "actual": actual,
                        "category": category,
                        "expected": expected,
                        "ref": ref,
                    }
                )
            return
        errors.append(
            f"schematic {ref} {category} differs: expected={expected!r}, actual={actual!r}"
        )
    if set(expected_by_ref) != set(actual_by_ref):
        errors.append(
            "schematic refs differ: "
            f"expected={sorted(expected_by_ref)}, actual={sorted(actual_by_ref)}"
        )
    for ref in sorted(expected_by_ref.keys() & actual_by_ref.keys()):
        expected = expected_by_ref[ref]
        actual_component = actual_by_ref[ref]
        raw_value = actual_component["value"]
        compare_field(
            ref,
            "value_format",
            expected["value"],
            raw_value,
            raw_value.removesuffix("Ω") == expected["value"],
        )
        compare_field(
            ref,
            "footprint",
            expected["footprint"]["kicad"],
            actual_component.get("footprint", ""),
            footprint_overrides.get(expected["stable_id"])
            == expected["footprint"]["kicad"],
        )
        compare_field(
            ref,
            "symbol_id",
            expected.get("symbol", ""),
            actual_component.get("symbol", ""),
        )
        expected_fields = expected.get("fields", {})
        compare_field(
            ref,
            "manufacturer_part_number",
            str(
                expected_fields.get(
                    "manufacturer_part_number", expected_fields.get("MPN", "")
                )
            ),
            actual_component.get("manufacturer_part_number", ""),
        )
        compare_field(
            ref,
            "datasheet",
            str(expected_fields.get("datasheet_url", expected_fields.get("Datasheet", ""))),
            actual_component.get("datasheet", ""),
        )
        pins = set(actual_component["pins"])
        if pins != set(expected["footprint"]["pad_numbers"]):
            errors.append(f"schematic {ref} pin set differs")

    source_aliases = {
        operation["target"]["net_stable_id"]: operation["params"]["source_name"]
        for operation in augmentation["operations"]
        if operation["kind"] == "net_alias"
    }
    expected_nets = {}
    components_by_id = by_id(manifest["components"])
    for net in manifest["nets"]:
        name = source_aliases.get(net["stable_id"], net["name"])
        expected_nets[name] = sorted(
            (components_by_id[endpoint["component"]]["ref"], endpoint["pad"])
            for endpoint in net["endpoints"]
        )
    actual_nets = {net["name"]: [tuple(endpoint) for endpoint in net["endpoints"]] for net in schematic["nets"]}
    if expected_nets != actual_nets:
        errors.append("schematic net names or endpoints differ")
    return errors


def stage_board_alias_errors(
    snapshot: dict[str, Any],
    manifest: dict[str, Any],
    augmentation: dict[str, Any],
) -> list[str]:
    """Require the staged board to retain exporter names used by its schematic."""
    aliases = {
        operation["target"]["net_stable_id"]: operation["params"]["source_name"]
        for operation in augmentation["operations"]
        if operation["kind"] == "net_alias"
    }
    expected = {}
    for net in manifest["nets"]:
        for endpoint in net["endpoints"]:
            expected[(endpoint["component"], endpoint["pad"])] = aliases.get(
                net["stable_id"], net["name"]
            )
    errors = []
    for component in snapshot["source_owned"]["components"]:
        for pad in component["pads"]:
            actual = _normalized_net_name(pad["net"], {})
            wanted = expected.get((component["stable_id"], pad["number"]), "")
            if actual != wanted:
                errors.append(
                    f"staged board {component['ref']}.{pad['number']} net differs: "
                    f"expected={wanted!r}, actual={actual!r}"
                )
    return errors


def assert_parity(
    snapshot: dict[str, Any],
    manifest: dict[str, Any],
    augmentation: dict[str, Any],
) -> None:
    errors = parity_errors(snapshot, manifest, augmentation)
    if errors:
        raise HandoffError("KiCad/source parity failed:\n- " + "\n- ".join(errors))


def _maybe_call(obj: Any, names: tuple[str, ...], default: Any = None) -> Any:
    for name in names:
        method = getattr(obj, name, None)
        if callable(method):
            try:
                return method()
            except (AttributeError, TypeError, RuntimeError):
                continue
    return default


def _uuid(item: Any) -> str:
    value = _maybe_call(item, ("GetUuid",), None)
    if value is None:
        value = getattr(item, "m_Uuid", None)
    formatted = _maybe_call(value, ("AsString", "Format"), None) if value is not None else None
    return "" if value is None else str(formatted if formatted is not None else value)


def _point_mm(pcbnew: Any, point: Any) -> list[Union[int, float]]:
    return [
        normalize_number(pcbnew.ToMM(point.x), "pcbnew point x"),
        normalize_number(pcbnew.ToMM(point.y), "pcbnew point y"),
    ]


def _size_mm(pcbnew: Any, size: Any) -> list[Union[int, float]]:
    return [
        normalize_number(pcbnew.ToMM(size.x), "pcbnew size x"),
        normalize_number(pcbnew.ToMM(size.y), "pcbnew size y"),
    ]


def _orientation_degrees(item: Any) -> Union[int, float]:
    direct = _maybe_call(item, ("GetOrientationDegrees",), None)
    if direct is not None:
        return normalize_number(float(direct) % 360, "footprint rotation")
    angle = _maybe_call(item, ("GetOrientation",), None)
    degrees = _maybe_call(angle, ("AsDegrees",), 0)
    return normalize_number(float(degrees) % 360, "footprint rotation")


def _layer_name(board: Any, item: Any) -> str:
    layer = _maybe_call(item, ("GetLayer",), None)
    if layer is None:
        return ""
    try:
        return str(board.GetLayerName(layer))
    except (AttributeError, TypeError, RuntimeError):
        return str(layer)


def _footprint_id(footprint: Any) -> str:
    value = _maybe_call(footprint, ("GetFPID",), None)
    formatted = _maybe_call(value, ("Format", "GetUniStringLibId"), None)
    return str(formatted if formatted is not None else value)


def _bbox_mm(pcbnew: Any, item: Any) -> list[Union[int, float]]:
    box = _maybe_call(item, ("GetBoundingBox",), None)
    if box is None:
        return []
    position = _maybe_call(box, ("GetPosition",), None)
    size = _maybe_call(box, ("GetSize",), None)
    return _point_mm(pcbnew, position) + _size_mm(pcbnew, size)


def _zone_outline_mm(
    pcbnew: Any, zone: Any
) -> list[list[list[Union[int, float]]]]:
    shape = _maybe_call(zone, ("Outline", "GetOutline"), None)
    if shape is None:
        return []
    count = _maybe_call(shape, ("OutlineCount",), 0)
    outlines = []
    for index in range(int(count or 0)):
        try:
            contour = shape.COutline(index)
            point_count = int(contour.PointCount())
            outlines.append(
                [_point_mm(pcbnew, contour.CPoint(point)) for point in range(point_count)]
            )
        except (AttributeError, TypeError, RuntimeError):
            return []
    return outlines


def extract_kicad_data(
    board_path: Path,
    rules_paths: list[Path],
) -> dict[str, Any]:
    """Read a saved board through pcbnew without modifying or saving it."""
    try:
        import pcbnew  # type: ignore[import-not-found]
    except ImportError as exc:
        raise HandoffError(
            "pcbnew is unavailable; run snapshot-kicad through pcb/tools/kicad_python.sh"
        ) from exc
    try:
        board = pcbnew.LoadBoard(str(board_path.resolve()))
    except Exception as exc:  # pcbnew exception types are not stable across KiCad releases
        raise HandoffError(f"KiCad could not load board {board_path}: {exc}") from exc
    if board is None:
        raise HandoffError(f"KiCad could not load board {board_path}")

    components = []
    holes = []
    for footprint in board.GetFootprints():
        ref = str(footprint.GetReference())
        pads = []
        for pad in footprint.Pads():
            pad_number = str(pad.GetNumber())
            if pad_number:
                pads.append({"number": pad_number, "net": str(pad.GetNetname())})
            attribute = _maybe_call(pad, ("GetAttribute",), None)
            npth = getattr(pcbnew, "PAD_ATTRIB_NPTH", object())
            if attribute == npth or "NPTH" in str(attribute).upper():
                holes.append(
                    {
                        "footprint_ref": ref,
                        "pad": pad_number,
                        "position_mm": _point_mm(pcbnew, pad.GetPosition()),
                        "drill_mm": _size_mm(pcbnew, pad.GetDrillSize()),
                        "uuid": _uuid(pad),
                    }
                )
        components.append(
            {
                "footprint": _footprint_id(footprint),
                "pads": pads,
                "placement": {
                    "position_mm": _point_mm(pcbnew, footprint.GetPosition()),
                    "rotation_deg": _orientation_degrees(footprint),
                    "side": "back" if _layer_name(board, footprint).startswith("B.") else "front",
                },
                "ref": ref,
                "uuid": _uuid(footprint),
                "value": str(footprint.GetValue()),
            }
        )

    tracks = []
    vias = []
    for item in board.GetTracks():
        is_via = isinstance(item, pcbnew.PCB_VIA)
        width = item.GetWidth(item.TopLayer()) if is_via else item.GetWidth()
        common = {
            "layer": _layer_name(board, item),
            "net": str(_maybe_call(item, ("GetNetname",), "")),
            "position_mm": _point_mm(pcbnew, item.GetPosition()),
            "uuid": _uuid(item),
            "width_mm": normalize_number(pcbnew.ToMM(width), "track width"),
        }
        if is_via:
            drill = _maybe_call(item, ("GetDrillValue",), 0)
            common.update(
                {
                    "drill_mm": normalize_number(pcbnew.ToMM(drill), "via drill"),
                    "layer_pair": [
                        str(board.GetLayerName(item.TopLayer())),
                        str(board.GetLayerName(item.BottomLayer())),
                    ],
                }
            )
            vias.append(common)
        else:
            common.update(
                {
                    "start_mm": _point_mm(pcbnew, item.GetStart()),
                    "end_mm": _point_mm(pcbnew, item.GetEnd()),
                }
            )
            tracks.append(common)

    zones = []
    for zone in board.Zones():
        layers = []
        layer_set = _maybe_call(zone, ("GetLayerSet",), None)
        sequence = _maybe_call(layer_set, ("Seq",), []) if layer_set is not None else []
        for layer in sequence or []:
            layers.append(str(board.GetLayerName(layer)))
        zones.append(
            {
                "bbox_mm": _bbox_mm(pcbnew, zone),
                "layers": sorted(layers),
                "name": str(_maybe_call(zone, ("GetZoneName",), "")),
                "net": str(_maybe_call(zone, ("GetNetname",), "")),
                "outline_mm": _zone_outline_mm(pcbnew, zone),
                "priority": _maybe_call(zone, ("GetAssignedPriority", "GetPriority"), 0),
                "uuid": _uuid(zone),
            }
        )

    outline = []
    graphics = []
    for drawing in board.GetDrawings():
        detail = {
            "bbox_mm": _bbox_mm(pcbnew, drawing),
            "class": type(drawing).__name__,
            "layer": _layer_name(board, drawing),
            "uuid": _uuid(drawing),
        }
        text = _maybe_call(drawing, ("GetText",), None)
        if text is not None:
            detail["text"] = str(text)
        for key, names in (
            ("start_mm", ("GetStart",)),
            ("end_mm", ("GetEnd",)),
            ("position_mm", ("GetPosition",)),
        ):
            point = _maybe_call(drawing, names, None)
            if point is not None:
                detail[key] = _point_mm(pcbnew, point)
        if detail["layer"] == "Edge.Cuts":
            outline.append(detail)
        else:
            graphics.append(detail)

    settings = board.GetDesignSettings()
    board_setup: dict[str, Any] = {
        "copper_layer_count": int(board.GetCopperLayerCount()),
    }
    thickness = _maybe_call(board, ("GetBoardThickness",), None)
    if thickness is not None:
        board_setup["thickness_mm"] = normalize_number(
            pcbnew.ToMM(thickness), "board thickness"
        )
    for output_key, attribute in (
        ("minimum_clearance_mm", "m_MinClearance"),
        ("minimum_track_width_mm", "m_TrackMinWidth"),
        ("minimum_via_size_mm", "m_ViasMinSize"),
        ("minimum_via_drill_mm", "m_MinThroughDrill"),
        ("minimum_hole_to_hole_mm", "m_HoleToHoleMin"),
    ):
        value = getattr(settings, attribute, None)
        if value is not None:
            board_setup[output_key] = normalize_number(
                pcbnew.ToMM(value), f"board setup {output_key}"
            )
    rules = [{"board_setup": board_setup}]
    for path in rules_paths:
        resolved = path.resolve()
        if not resolved.is_file():
            raise HandoffError(f"rules file does not exist: {resolved}")
        rules.append(
            {
                "path": str(resolved),
                "sha256": hashlib.sha256(resolved.read_bytes()).hexdigest(),
            }
        )
    return {
        "components": components,
        "graphics": graphics,
        "holes": holes,
        "outline": outline,
        "rules": rules,
        "tracks": tracks,
        "vias": vias,
        "zones": zones,
    }


def augment_staged_board(
    board_path: Path,
    manifest: dict[str, Any],
    augmentation: dict[str, Any],
    footprint_root: Path,
) -> None:
    """Apply source authority to a new staged seed through KiCad's native API."""
    stage_value = os.environ.get("STILLAIR_HANDOFF_STAGE")
    if not stage_value:
        raise HandoffError("augment-staged requires STILLAIR_HANDOFF_STAGE")
    stage = Path(stage_value).resolve()
    board_path = board_path.resolve()
    if not board_path.is_relative_to(stage):
        raise HandoffError("augment-staged refuses a board outside its staging directory")
    try:
        import pcbnew  # type: ignore[import-not-found]
    except ImportError as exc:
        raise HandoffError(
            "pcbnew is unavailable; run augment-staged through pcb/tools/kicad_python.sh"
        ) from exc
    board = pcbnew.LoadBoard(str(board_path))
    if board is None:
        raise HandoffError(f"KiCad could not load staged board {board_path}")

    transform = coordinate_transform(augmentation)
    desired_center = transform["kicad_center_mm"]
    edge_points = []
    for drawing in board.GetDrawings():
        if _layer_name(board, drawing) != "Edge.Cuts":
            continue
        for names in (("GetStart",), ("GetEnd",)):
            point = _maybe_call(drawing, names, None)
            if point is not None:
                edge_points.append(_point_mm(pcbnew, point))
    if not edge_points:
        raise HandoffError("staged board has no measurable Edge.Cuts")
    current_center = [
        (min(point[0] for point in edge_points) + max(point[0] for point in edge_points)) / 2,
        (min(point[1] for point in edge_points) + max(point[1] for point in edge_points)) / 2,
    ]
    delta = pcbnew.VECTOR2I(
        pcbnew.FromMM(desired_center[0] - current_center[0]),
        pcbnew.FromMM(desired_center[1] - current_center[1]),
    )
    for drawing in board.GetDrawings():
        drawing.Move(delta)
    for zone in board.Zones():
        zone.Move(delta)

    aliases = {
        operation["target"]["net_stable_id"]: operation["params"]["source_name"]
        for operation in augmentation["operations"]
        if operation["kind"] == "net_alias"
    }
    pad_nets: dict[tuple[str, str], str] = {}
    for net in manifest["nets"]:
        net_name = aliases.get(net["stable_id"], net["name"])
        for endpoint in net["endpoints"]:
            pad_nets[(endpoint["component"], endpoint["pad"])] = net_name

    nets_by_name = {str(name): net for name, net in board.GetNetsByName().items()}

    def get_net(name: str) -> Any:
        if name in nets_by_name:
            return nets_by_name[name]
        net = pcbnew.NETINFO_ITEM(board, name)
        board.Add(net)
        nets_by_name[name] = net
        return net

    footprints_by_ref = {
        str(footprint.GetReference()): footprint for footprint in board.GetFootprints()
    }
    expected_refs = {component["ref"] for component in manifest["components"]}
    unexpected = sorted(set(footprints_by_ref) - expected_refs)
    missing = sorted(expected_refs - set(footprints_by_ref))
    if unexpected or missing:
        raise HandoffError(
            f"staged footprint refs differ: missing={missing}, unexpected={unexpected}"
        )

    for component in manifest["components"]:
        lib_id = component["footprint"]["kicad"]
        if ":" not in lib_id:
            raise HandoffError(f"invalid KiCad footprint library ID {lib_id!r}")
        library, footprint_name = lib_id.split(":", 1)
        library_path = footprint_root / f"{library}.pretty"
        replacement = pcbnew.FootprintLoad(str(library_path), footprint_name)
        if replacement is None:
            raise HandoffError(
                f"cannot load official footprint {lib_id} from {library_path}"
            )
        old = footprints_by_ref[component["ref"]]
        board.Remove(old)
        library_id = pcbnew.LIB_ID()
        library_id.SetLibNickname(pcbnew.UTF8(library))
        library_id.SetLibItemName(pcbnew.UTF8(footprint_name))
        replacement.SetFPID(library_id)
        replacement.SetReference(component["ref"])
        replacement.SetValue(component["value"])
        position = source_to_kicad_xy(
            component["placement"]["x_mm"],
            component["placement"]["y_mm"],
            augmentation,
        )
        replacement.SetPosition(
            pcbnew.VECTOR2I(pcbnew.FromMM(position[0]), pcbnew.FromMM(position[1]))
        )
        replacement.SetOrientationDegrees(component["placement"]["rotation_deg"])
        board.Add(replacement)
        if component["placement"]["side"] == "back":
            replacement.Flip(replacement.GetPosition(), False)
        actual_pads = {str(pad.GetNumber()): pad for pad in replacement.Pads() if str(pad.GetNumber())}
        expected_pads = set(component["footprint"]["pad_numbers"])
        if set(actual_pads) != expected_pads:
            raise HandoffError(
                f"official footprint pad set differs for {component['ref']}: "
                f"expected={sorted(expected_pads)}, actual={sorted(actual_pads)}"
            )
        for pad_number, pad in actual_pads.items():
            net_name = pad_nets.get((component["stable_id"], pad_number), "")
            if net_name:
                pad.SetNet(get_net(net_name))
            else:
                pad.SetNetCode(0)

    pcbnew.SaveBoard(str(board_path), board)


def command_augment_staged(args: argparse.Namespace) -> int:
    require_native_handoff_platform()
    manifest = load_manifest(args.manifest)
    augmentation = load_augmentation(args.augmentation, manifest)
    augment_staged_board(args.board, manifest, augmentation, args.footprint_root)
    print(f"augmented staged KiCad board {args.board}")
    return 0


def build_plan(
    manifest: dict[str, Any],
    augmentation: dict[str, Any],
    lock: dict[str, Any],
    snapshot: Optional[dict[str, Any]],
    allow_routed_eco: bool,
    allow_routed_placement: bool,
) -> dict[str, Any]:
    if lock.get("schema_version") != SCHEMA_VERSION:
        raise HandoffError("unsupported or missing handoff lock schema_version")
    if lock.get("board_id") != manifest["board"]["stable_id"]:
        raise HandoffError("handoff lock board_id does not match manifest")
    old_manifest = normalize_manifest(lock.get("manifest"))
    if lock.get("manifest_sha256") != digest(old_manifest):
        raise HandoffError("handoff lock manifest checksum is stale or corrupt")
    changes = classify_changes(old_manifest, manifest)
    old_augmentation = lock.get("augmentation", empty_augmentation(old_manifest))
    old_augmentation = validate_augmentation(old_augmentation, old_manifest)
    if lock.get("augmentation_sha256") != digest(old_augmentation):
        raise HandoffError("handoff lock augmentation checksum is stale or corrupt")
    locked_snapshot = normalize_snapshot(
        lock.get("snapshot"), manifest["board"]["stable_id"]
    )
    if lock.get("snapshot_sha256") != digest(locked_snapshot):
        raise HandoffError("handoff lock snapshot checksum is stale or corrupt")
    if old_augmentation != augmentation:
        changes.append(change("augmentation", manifest["board"]["stable_id"], old_augmentation, augmentation, "high", "changes KiCad-owned augmentation instructions"))

    authorized_kicad_owned_changes: set[str] = set()
    if {item["kind"] for item in changes} & {
        "component_add", "component_remove", "footprint", "placement", "reference", "value"
    }:
        authorized_kicad_owned_changes.add("graphics")
    if old_augmentation != augmentation:
        old_operations = {operation["id"]: operation for operation in old_augmentation["operations"]}
        new_operations = {operation["id"]: operation for operation in augmentation["operations"]}
        changed_operation_ids = {
            operation_id
            for operation_id in old_operations.keys() | new_operations.keys()
            if old_operations.get(operation_id) != new_operations.get(operation_id)
        }
        operation_kinds = {
            operation["kind"]
            for operation_id in changed_operation_ids
            for operation in (old_operations.get(operation_id), new_operations.get(operation_id))
            if operation is not None
        }
        if operation_kinds & {"zone", "keepout"}:
            authorized_kicad_owned_changes.add("zones")
        if operation_kinds & {"custom_rule", "impedance", "net_class", "stackup"}:
            authorized_kicad_owned_changes.add("rules")
        if operation_kinds & {
            "fabrication_note", "keepout", "mask_override", "paste_override", "pofv", "silkscreen"
        }:
            authorized_kicad_owned_changes.add("graphics")

    routed = bool(lock.get("snapshot", {}).get("routed", False))
    drift: list[dict[str, Any]] = []
    if snapshot is not None:
        routed = snapshot["routed"]
        accepted_source_owned = lock.get("snapshot", {}).get("source_owned", {})
        if snapshot["source_owned"] != accepted_source_owned:
            drift.append({
                "accepted": accepted_source_owned,
                "current": snapshot["source_owned"],
                "kind": "kicad_source_owned_drift",
                "reason": "KiCad source-owned state changed outside the accepted tscircuit handoff",
            })

    blockers = []
    if drift:
        blockers.append("resolve or explicitly import KiCad source-owned drift before applying an ECO")
    if routed:
        kinds = {item["kind"] for item in changes}
        if "placement" in kinds and not allow_routed_placement:
            blockers.append("routed board placement changes require --allow-routed-placement")
        high_impact = sorted((kinds & ROUTED_BLOCKED_CHANGES) - {"placement"})
        if high_impact and not allow_routed_eco:
            blockers.append(
                "routed board logical/geometry ECO requires --allow-routed-eco: "
                + ", ".join(high_impact)
            )
        if "augmentation" in kinds and not allow_routed_eco:
            blockers.append("routed board augmentation changes require --allow-routed-eco")

    overall = max((item["risk"] for item in changes), key=lambda risk: RISK_ORDER[risk], default="none")
    return {
        "augmentation_sha256": digest(augmentation),
        "authorized_kicad_owned_changes": sorted(authorized_kicad_owned_changes),
        "blocked": bool(blockers),
        "blockers": blockers,
        "board_id": manifest["board"]["stable_id"],
        "changes": changes,
        "current_manifest_sha256": digest(manifest),
        "drift": drift,
        "locked_manifest_sha256": lock.get("manifest_sha256"),
        "overall_risk": overall,
        "routed": routed,
        "schema_version": SCHEMA_VERSION,
        "target_augmentation": augmentation,
        "target_manifest": manifest,
    }


def hash_protected_tree(
    root: Path,
    excluded_roots: Iterable[Path] = (),
) -> dict[str, str]:
    if not root.exists():
        return {}
    result = {}
    excluded = [path.resolve() for path in excluded_roots]
    for path in sorted(root.rglob("*")):
        resolved = path.resolve()
        if any(resolved.is_relative_to(exclusion) for exclusion in excluded):
            continue
        if path.is_file() and is_protected_path(path):
            result[str(path.resolve())] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def parse_command(value: str, where: str) -> list[str]:
    try:
        command = json.loads(value)
    except json.JSONDecodeError as exc:
        raise HandoffError(f"{where} must be a JSON argv array: {exc}") from exc
    if not isinstance(command, list) or not command or not all(isinstance(item, str) and item for item in command):
        raise HandoffError(f"{where} must be a non-empty JSON array of strings")
    return command


def run_staged_command(command: list[str], cwd: Path, env: dict[str, str]) -> dict[str, Any]:
    completed = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True)
    receipt = {
        "argv": command,
        "returncode": completed.returncode,
        "stderr": completed.stderr,
        "stdout": completed.stdout,
    }
    if completed.returncode:
        raise HandoffError(
            f"staged command failed ({completed.returncode}): {command!r}\n"
            + completed.stdout
            + completed.stderr
        )
    return receipt


def resolve_executable(value: Optional[Path], name: str, candidates: Iterable[Path]) -> Path:
    paths = ([value] if value else []) + list(candidates)
    discovered = shutil.which(name)
    if discovered:
        paths.append(Path(discovered))
    for path in paths:
        if path is None:
            continue
        resolved = path.resolve()
        if resolved.is_file() and os.access(resolved, os.X_OK):
            return resolved
    raise HandoffError(f"cannot discover executable {name}; pass --{name.replace('_', '-')}")


def resolve_footprint_root(value: Optional[Path]) -> Path:
    candidates = [
        value,
        Path("/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"),
        Path("/usr/share/kicad/footprints"),
        Path("/usr/local/share/kicad/footprints"),
    ]
    for candidate in candidates:
        if candidate is not None and candidate.resolve().is_dir():
            return candidate.resolve()
    raise HandoffError("cannot discover KiCad footprint libraries; pass --footprint-root")


def executable_fingerprint(path: Path, version_args: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        [str(path), *version_args], capture_output=True, text=True
    )
    return {
        "path": str(path),
        "returncode": completed.returncode,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "version": (completed.stdout or completed.stderr).strip(),
    }


def require_native_handoff_platform(platform: str = sys.platform) -> None:
    """Fail closed where this repo has no verified pcbnew runtime discovery."""
    if platform != "darwin":
        raise HandoffError(
            "native KiCad handoff is currently supported on macOS only; "
            "Linux/Windows may run exporter-only tests but must not stage or accept"
        )


def require_render_files(paths: Iterable[Path], stage: Path) -> list[dict[str, str]]:
    artifacts = []
    for path in sorted(set(paths)):
        if not path.is_file() or path.stat().st_size == 0:
            raise HandoffError(f"required KiCad review render is missing or empty: {path}")
        resolved = path.resolve()
        if not resolved.is_relative_to(stage.resolve()):
            raise HandoffError(f"KiCad review render escapes staging: {path}")
        artifacts.append(
            {
                "path": str(resolved.relative_to(stage.resolve())),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    if not artifacts:
        raise HandoffError("KiCad did not produce required review renders")
    return artifacts


def verify_receipt_renders(receipt: dict[str, Any], receipt_path: Path) -> None:
    renders = require_list(receipt.get("review_renders"), "receipt.review_renders")
    if not renders:
        raise HandoffError("receipt does not contain required KiCad review renders")
    suffixes = set()
    for index, raw in enumerate(renders):
        item = require_object(raw, f"receipt.review_renders[{index}]")
        relative = Path(require_string(item.get("path"), f"receipt.review_renders[{index}].path"))
        if relative.is_absolute() or ".." in relative.parts:
            raise HandoffError("receipt review render path must stay below the receipt directory")
        path = receipt_path.resolve().parent / relative
        expected_hash = require_string(
            item.get("sha256"), f"receipt.review_renders[{index}].sha256"
        )
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
            raise HandoffError(f"receipt review render is missing or changed: {relative}")
        suffixes.add(path.suffix.lower())
    if not {".svg", ".pdf", ".png"} <= suffixes:
        raise HandoffError("receipt must prove schematic SVG/PDF and PCB PNG renders")


def verify_generated_kicad(receipt: dict[str, Any], receipt_path: Path) -> None:
    """Bind acceptance to the exact staged KiCad files recorded by stage."""
    entries = require_list(receipt.get("generated_kicad"), "receipt.generated_kicad")
    if not entries:
        raise HandoffError("receipt does not contain staged KiCad file hashes")
    suffixes = set()
    seen = set()
    for index, raw in enumerate(entries):
        item = require_object(raw, f"receipt.generated_kicad[{index}]")
        relative = Path(
            require_string(item.get("path"), f"receipt.generated_kicad[{index}].path")
        )
        if relative.is_absolute() or ".." in relative.parts or relative in seen:
            raise HandoffError("receipt KiCad paths must be unique and stay below staging")
        seen.add(relative)
        path = receipt_path.resolve().parent / relative
        if path.is_symlink() or not path.is_file() or not is_protected_path(path):
            raise HandoffError(f"receipt staged KiCad file is missing or invalid: {relative}")
        expected_hash = require_string(
            item.get("sha256"), f"receipt.generated_kicad[{index}].sha256"
        )
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
            raise HandoffError(f"staged KiCad file changed after validation: {relative}")
        suffixes.add(path.suffix.lower())
    if not {".kicad_pcb", ".kicad_sch"} <= suffixes:
        raise HandoffError("receipt must bind both staged board and schematic files")


def validate_initial_check_report(
    report: Any, augmentation: dict[str, Any], schematic: bool
) -> dict[str, Any]:
    root = require_object(report, "KiCad check report")
    severities = set(
        require_list(root.get("included_severities"), "KiCad report included_severities")
    )
    missing_severities = {"error", "warning"} - severities
    if missing_severities:
        raise HandoffError(
            "KiCad check omitted required severities: "
            + ", ".join(sorted(missing_severities))
        )
    ignored_key = (
        "allowed_initial_erc_ignored_checks"
        if schematic
        else "allowed_initial_drc_ignored_checks"
    )
    allowed_ignored = {
        key
        for operation in augmentation["operations"]
        for key in operation["params"].get(ignored_key, [])
    }
    ignored = {
        require_string(
            require_object(item, "KiCad report ignored check").get("key"),
            "KiCad report ignored check key",
        )
        for item in require_list(root.get("ignored_checks"), "KiCad report ignored_checks")
    }
    undeclared_ignored = sorted(ignored - allowed_ignored)
    if undeclared_ignored:
        raise HandoffError(
            "KiCad check contains undeclared ignored checks: "
            + ", ".join(undeclared_ignored)
        )
    allowed = set()
    if schematic:
        for operation in augmentation["operations"]:
            if operation["kind"] == "schematic_cleanup":
                allowed.update(operation["params"]["allowed_initial_erc_types"])
    if not schematic and any(
        operation["kind"] == "silkscreen" for operation in augmentation["operations"]
    ):
        allowed.update(
            {
                "nonmirrored_text_on_back_layer", "silk_edge_clearance",
                "silk_over_copper", "silk_overlap", "text_height", "text_thickness",
            }
        )
    violations = []
    def collect(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "violations":
                    violations.extend(require_list(child, "KiCad report violations"))
                else:
                    collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)
    collect(root)
    categories = [
        str(require_object(item, "KiCad report violation").get("type", "<missing>"))
        for item in violations
    ]
    unknown = sorted({category for category in categories if category not in allowed})
    routing_declared = any(
        operation["kind"] == "fabrication_note"
        and operation["params"].get("category") == "routing"
        for operation in augmentation["operations"]
    )
    unconnected = require_list(
        root.get("unconnected_items", []), "KiCad report unconnected_items"
    )
    if unconnected and (schematic or not routing_declared):
        unknown.append("unconnected_items")
    if unknown:
        raise HandoffError(
            "KiCad check contains undeclared initial finding types: "
            + ", ".join(sorted(set(unknown)))
        )
    counts = {category: categories.count(category) for category in sorted(set(categories))}
    if unconnected:
        counts["unconnected_items"] = len(unconnected)
    return {
        "clean": not counts,
        "declared_findings": counts,
        "parsed": True,
    }


def command_normalize(args: argparse.Namespace) -> int:
    manifest = load_manifest(args.manifest)
    if args.augmentation:
        validate_augmentation(read_json(args.augmentation), manifest)
    atomic_write_json(args.output, manifest)
    print(f"normalized {manifest['board']['stable_id']} -> {args.output} ({digest(manifest)})")
    return 0


def command_stage(args: argparse.Namespace) -> int:
    require_native_handoff_platform()
    manifest = load_manifest(args.manifest)
    augmentation = load_augmentation(args.augmentation, manifest)
    stage_parent = args.staging_root.resolve() if args.staging_root else None
    if stage_parent:
        stage_parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f"stillair-{manifest['board']['stable_id']}-handoff-", dir=stage_parent))
    staged_manifest = stage / "source-manifest.normalized.json"
    staged_augmentation = stage / "kicad-augmentation.normalized.json"
    atomic_write_json(staged_manifest, manifest)
    atomic_write_json(staged_augmentation, augmentation)

    repo_root = Path(__file__).resolve().parents[2]
    source_root = args.source_dir.resolve()
    production_root = args.production_dir.resolve()
    generated_root = (repo_root / "pcb" / "dist").resolve()
    for excluded_root in (stage_parent, generated_root):
        if excluded_root is not None and (
            production_root.is_relative_to(excluded_root)
            or excluded_root.is_relative_to(production_root)
        ):
            raise HandoffError(
                "staging/generated-output root must not overlap --production-dir"
            )
    protected_roots = []
    for root in (repo_root, source_root, production_root):
        if root not in protected_roots:
            protected_roots.append(root)

    def protected_state() -> dict[str, str]:
        state = {}
        excluded = [stage, generated_root]
        for root in protected_roots:
            state.update(hash_protected_tree(root, excluded_roots=excluded))
        return state

    production_before = protected_state()
    env = dict(os.environ)
    env.update({
        "STILLAIR_HANDOFF_AUGMENTATION": str(staged_augmentation),
        "STILLAIR_HANDOFF_BOARD": manifest["board"]["stable_id"],
        "STILLAIR_HANDOFF_MANIFEST": str(staged_manifest),
        "STILLAIR_HANDOFF_STAGE": str(stage),
    })
    cwd = source_root
    def run_guarded(command: list[str], command_cwd: Path) -> dict[str, Any]:
        try:
            result = run_staged_command(command, command_cwd, env)
        except HandoffError as command_error:
            if protected_state() != production_before:
                raise HandoffError(
                    "a staged command modified protected KiCad source while failing; "
                    "inspect and revert it\n" + str(command_error)
                ) from command_error
            raise
        if protected_state() != production_before:
            raise HandoffError(
                "a staged command modified protected KiCad source; inspect and revert it"
            )
        return result

    commands = []
    commands.append(run_guarded(parse_command(args.build_command, "--build-command"), cwd))
    commands.append(run_guarded(parse_command(args.export_command, "--export-command"), cwd))

    generated = []
    for path in sorted(stage.rglob("*")):
        if path.is_file() and is_protected_path(path):
            if path.is_symlink() or not path.resolve().is_relative_to(stage):
                raise HandoffError(
                    f"staged KiCad output escapes its staging directory: {path}"
                )
            generated.append({
                "path": str(path.relative_to(stage)),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            })
    required = {".kicad_pcb", ".kicad_sch"}
    present = {Path(item["path"]).suffix.lower() for item in generated}
    if not required <= present:
        raise HandoffError(
            "initial export did not stage both .kicad_pcb and .kicad_sch files"
        )
    boards = [stage / item["path"] for item in generated if Path(item["path"]).suffix == ".kicad_pcb"]
    schematics = [stage / item["path"] for item in generated if Path(item["path"]).suffix == ".kicad_sch"]
    if len(boards) != 1:
        raise HandoffError(
            f"initial export must stage exactly one .kicad_pcb; found {len(boards)}"
        )
    root_schematic = boards[0].with_suffix(".kicad_sch")
    if root_schematic not in schematics:
        raise HandoffError(
            f"initial export is missing root schematic {root_schematic.name}"
        )
    hierarchy = validate_schematic_hierarchy(root_schematic, stage)

    kicad_python = resolve_executable(
        args.kicad_python,
        "kicad_python",
        (Path(__file__).resolve().parent / "kicad_python.sh",),
    )
    footprint_root = resolve_footprint_root(args.footprint_root)
    commands.append(
        run_guarded(
            [
                str(kicad_python),
                str(Path(__file__).resolve()),
                "augment-staged",
                str(boards[0]),
                str(staged_manifest),
                "--augmentation",
                str(staged_augmentation),
                "--footprint-root",
                str(footprint_root),
            ],
            stage,
        )
    )

    cli = resolve_executable(
        args.kicad_cli,
        "kicad-cli",
        (Path("/opt/homebrew/bin/kicad-cli"),),
    )
    kicad_checks = []
    for generated_path in boards + [root_schematic]:
        if generated_path.suffix == ".kicad_pcb":
            report = stage / f"{generated_path.stem}-initial-drc.json"
            command = [
                str(cli), "pcb", "drc", "--format", "json",
                "--output", str(report), str(generated_path),
            ]
        else:
            report = stage / f"{generated_path.stem}-initial-erc.json"
            command = [
                str(cli), "sch", "erc", "--format", "json",
                "--output", str(report), str(generated_path),
            ]
        check = run_guarded(command, stage)
        parsed_report = read_json(report)
        check.update(validate_initial_check_report(
            parsed_report, augmentation, generated_path.suffix == ".kicad_sch"
        ))
        check["report"] = str(report.relative_to(stage))
        check["report_sha256"] = digest(parsed_report)
        kicad_checks.append(check)

    schematic_netlist = stage / "staged-schematic.netlist.xml"
    commands.append(
        run_guarded(
            [
                str(cli), "sch", "export", "netlist", "--format", "kicadxml",
                "--output", str(schematic_netlist), str(root_schematic),
            ],
            stage,
        )
    )
    schematic = schematic_snapshot_from_netlist(schematic_netlist)
    schematic_declared_differences: list[dict[str, str]] = []
    schematic_errors = schematic_snapshot_parity_errors(
        schematic,
        manifest,
        augmentation,
        declared_differences=schematic_declared_differences,
    )
    if schematic_errors:
        raise HandoffError(
            "KiCad schematic/source parity failed:\n- "
            + "\n- ".join(schematic_errors)
        )

    render_dir = stage / "review-renders"
    render_dir.mkdir()
    schematic_svg_dir = render_dir / "schematic-svg"
    commands.append(
        run_guarded(
            [
                str(cli), "sch", "export", "svg", "--output",
                str(schematic_svg_dir), str(root_schematic),
            ],
            stage,
        )
    )
    schematic_pdf = render_dir / "schematic.pdf"
    commands.append(
        run_guarded(
            [
                str(cli), "sch", "export", "pdf", "--output",
                str(schematic_pdf), str(root_schematic),
            ],
            stage,
        )
    )
    pcb_render = render_dir / "pcb-top.png"
    commands.append(
        run_guarded(
            [
                str(cli), "pcb", "render", "--output", str(pcb_render),
                "--side", "top", "--quality", "high", str(boards[0]),
            ],
            stage,
        )
    )
    review_renders = require_render_files(
        [*schematic_svg_dir.glob("*.svg"), schematic_pdf, pcb_render], stage
    )
    if not any(item["path"].endswith(".svg") for item in review_renders):
        raise HandoffError("KiCad did not produce a schematic SVG review render")

    staged_snapshot = stage / "staged-kicad-snapshot.json"
    commands.append(
        run_guarded(
            [
                str(kicad_python),
                str(Path(__file__).resolve()),
                "snapshot-kicad",
                str(boards[0]),
                str(staged_manifest),
                "--augmentation",
                str(staged_augmentation),
                "--schematic-netlist",
                str(schematic_netlist),
                "--output",
                str(staged_snapshot),
                "--unrouted",
            ],
            stage,
        )
    )
    snapshot = normalize_snapshot(
        read_json(staged_snapshot), manifest["board"]["stable_id"]
    )
    assert_parity(snapshot, manifest, augmentation)
    alias_errors = stage_board_alias_errors(snapshot, manifest, augmentation)
    if alias_errors:
        raise HandoffError(
            "staged board/schematic net-name parity failed:\n- "
            + "\n- ".join(alias_errors)
        )

    # Augmentation intentionally changes the staged board, so record final bytes.
    generated = []
    for path in sorted(stage.rglob("*")):
        if path.is_file() and is_protected_path(path):
            if path.is_symlink() or not path.resolve().is_relative_to(stage):
                raise HandoffError(
                    f"final staged KiCad output escapes its staging directory: {path}"
                )
            generated.append(
                {
                    "path": str(path.relative_to(stage)),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            )
    footprint_fingerprints = {}
    for component in manifest["components"]:
        library, footprint_name = component["footprint"]["kicad"].split(":", 1)
        footprint_path = footprint_root / f"{library}.pretty" / f"{footprint_name}.kicad_mod"
        if not footprint_path.is_file():
            raise HandoffError(f"official footprint source is missing: {footprint_path}")
        footprint_fingerprints[component["footprint"]["kicad"]] = {
            "path": str(footprint_path),
            "sha256": hashlib.sha256(footprint_path.read_bytes()).hexdigest(),
        }
    tool_fingerprints = {
        "kicad_cli": executable_fingerprint(cli, ["--version"]),
        "kicad_python": executable_fingerprint(kicad_python, ["--version"]),
    }
    for name in ("bun", "tsci"):
        candidates = (source_root / "node_modules" / ".bin" / name,)
        path = resolve_executable(None, name, candidates)
        tool_fingerprints[name] = executable_fingerprint(path, ["--version"])
    converter_package = source_root / "node_modules/circuit-json-to-kicad/package.json"
    converter_code = source_root / "node_modules/circuit-json-to-kicad/dist/index.js"
    if not converter_package.is_file() or not converter_code.is_file():
        raise HandoffError("pinned circuit-json-to-kicad package is unavailable")
    tool_fingerprints["circuit_json_to_kicad"] = {
        "package_sha256": hashlib.sha256(converter_package.read_bytes()).hexdigest(),
        "code_sha256": hashlib.sha256(converter_code.read_bytes()).hexdigest(),
        "version": require_string(read_json(converter_package).get("version"), "converter version"),
    }
    receipt = {
        "augmentation_sha256": digest(augmentation),
        "board_id": manifest["board"]["stable_id"],
        "commands": commands,
        "generated_kicad": generated,
        "footprint_fingerprints": dict(sorted(footprint_fingerprints.items())),
        "kicad_parse_checks": kicad_checks,
        "kicad_parse_verified": True,
        "manifest_sha256": digest(manifest),
        "parity_verified": True,
        "review_renders": review_renders,
        "schema_version": SCHEMA_VERSION,
        "staged_snapshot": str(staged_snapshot.relative_to(stage)),
        "staged_snapshot_sha256": digest(snapshot),
        "stage": str(stage),
        "versions": manifest["versions"],
        "tool_fingerprints": tool_fingerprints,
        "schematic_declared_differences": schematic_declared_differences,
    }
    atomic_write_json(stage / "handoff-receipt.json", receipt)
    print(stage)
    return 0


def command_accept(args: argparse.Namespace) -> int:
    require_native_handoff_platform()
    manifest = load_manifest(args.manifest)
    augmentation = load_augmentation(args.augmentation, manifest)
    snapshot = normalize_snapshot(read_json(args.snapshot), manifest["board"]["stable_id"])
    assert_parity(snapshot, manifest, augmentation)
    if "schematic_owned" not in snapshot:
        raise HandoffError("snapshot is missing required schematic_owned semantics")
    declared_differences: list[dict[str, str]] = []
    schematic_errors = schematic_snapshot_parity_errors(
        snapshot["schematic_owned"], manifest, augmentation,
        declared_differences=declared_differences,
    )
    if schematic_errors:
        raise HandoffError("schematic/source parity failed:\n- " + "\n- ".join(schematic_errors))
    receipt = require_object(read_json(args.receipt), "receipt")
    require_object(receipt.get("tool_fingerprints"), "receipt.tool_fingerprints")
    require_object(receipt.get("footprint_fingerprints"), "receipt.footprint_fingerprints")
    verify_generated_kicad(receipt, args.receipt)
    verify_receipt_renders(receipt, args.receipt)
    if (
        receipt.get("board_id") != manifest["board"]["stable_id"]
        or receipt.get("manifest_sha256") != digest(manifest)
        or receipt.get("augmentation_sha256") != digest(augmentation)
        or receipt.get("versions") != manifest["versions"]
        or receipt.get("staged_snapshot_sha256") != digest(snapshot)
        or not receipt.get("parity_verified")
        or not receipt.get("kicad_parse_verified")
        or receipt.get("schematic_declared_differences") != declared_differences
    ):
        raise HandoffError(
            "staging receipt does not prove matching manifest, augmentation, snapshot, parity, and KiCad parse"
        )
    lock = {
        "augmentation": augmentation,
        "augmentation_sha256": digest(augmentation),
        "board_id": manifest["board"]["stable_id"],
        "manifest": manifest,
        "manifest_sha256": digest(manifest),
        "schema_version": SCHEMA_VERSION,
        "snapshot": snapshot,
        "snapshot_sha256": digest(snapshot),
        "initial_handoff_receipt_sha256": digest(receipt),
    }
    atomic_write_json(args.lock, lock)
    print(f"accepted {lock['board_id']} handoff -> {args.lock}")
    return 0


def command_snapshot_kicad(args: argparse.Namespace) -> int:
    require_native_handoff_platform()
    manifest = load_manifest(args.manifest)
    augmentation = load_augmentation(args.augmentation, manifest)
    rule_files = list(args.rules)
    for suffix in (".kicad_pro", ".kicad_dru"):
        candidate = args.board.with_suffix(suffix)
        if candidate.is_file() and candidate not in rule_files:
            rule_files.append(candidate)
    extracted = extract_kicad_data(args.board, rule_files)
    routed = derive_routed_state(extracted, args.routed)
    snapshot = normalize_kicad_snapshot_data(extracted, manifest, routed)
    snapshot["schematic_owned"] = schematic_snapshot_from_netlist(
        args.schematic_netlist
    )
    return finish_snapshot_kicad(snapshot, manifest, augmentation, args.output)


def derive_routed_state(extracted: dict[str, Any], requested: Optional[bool]) -> bool:
    copper_present = bool(extracted["tracks"] or extracted["vias"])
    if requested is False and copper_present:
        raise HandoffError("--unrouted contradicts extracted tracks or vias")
    return copper_present if requested is None else requested


def finish_snapshot_kicad(
    snapshot: dict[str, Any],
    manifest: dict[str, Any],
    augmentation: dict[str, Any],
    output: Path,
) -> int:
    assert_parity(snapshot, manifest, augmentation)
    atomic_write_json(output, snapshot)
    print(
        f"snapshotted {snapshot['board_id']} -> {output} "
        f"({len(snapshot['source_owned']['components'])} components, "
        f"routed={str(snapshot['routed']).lower()})"
    )
    return 0


def command_plan(args: argparse.Namespace) -> int:
    manifest = load_manifest(args.manifest)
    augmentation = load_augmentation(args.augmentation, manifest)
    lock = require_object(read_json(args.lock), "handoff lock")
    snapshot = normalize_snapshot(read_json(args.snapshot), manifest["board"]["stable_id"]) if args.snapshot else None
    plan = build_plan(
        manifest,
        augmentation,
        lock,
        snapshot,
        args.allow_routed_eco,
        args.allow_routed_placement,
    )
    if args.output:
        atomic_write_json(args.output, plan)
    print(json.dumps(plan, indent=2, sort_keys=True))
    return 2 if plan["blocked"] else 0


def command_verify_preservation(args: argparse.Namespace) -> int:
    plan = require_object(read_json(args.plan), "plan")
    before = normalize_snapshot(read_json(args.before_snapshot), require_string(plan.get("board_id"), "plan.board_id"))
    after = normalize_snapshot(read_json(args.after_snapshot), plan["board_id"])
    errors = []
    target_manifest = normalize_manifest(plan.get("target_manifest"))
    target_augmentation = validate_augmentation(
        plan.get("target_augmentation"), target_manifest
    )
    errors.extend(parity_errors(after, target_manifest, target_augmentation))
    if "schematic_owned" not in after:
        errors.append("after snapshot is missing schematic_owned semantics")
    else:
        errors.extend(
            schematic_snapshot_parity_errors(
                after["schematic_owned"], target_manifest, target_augmentation,
                strict_fields=True,
            )
        )
    planned_symbol_targets = {
        item["target"] for item in plan.get("changes", []) if item.get("kind") == "symbol"
    }
    if planned_symbol_targets and "schematic_owned" in before and "schematic_owned" in after:
        refs_by_id = {item["stable_id"]: item["ref"] for item in target_manifest["components"]}
        before_symbols = {item["ref"]: item.get("symbol", "") for item in before["schematic_owned"]["components"]}
        after_symbols = {item["ref"]: item.get("symbol", "") for item in after["schematic_owned"]["components"]}
        for stable_id in sorted(planned_symbol_targets):
            ref = refs_by_id.get(stable_id, stable_id)
            if before_symbols.get(ref) == after_symbols.get(ref):
                errors.append(f"schematic symbol ECO was not applied for {ref}")
    authorized = set(
        require_list(
            plan.get("authorized_kicad_owned_changes", []),
            "plan.authorized_kicad_owned_changes",
        )
    )
    for category in sorted(set(before["kicad_owned"]) | set(after["kicad_owned"])):
        if category not in authorized and before["kicad_owned"].get(category) != after["kicad_owned"].get(category):
            errors.append(f"unauthorized KiCad-owned {category} change")
    if plan.get("blocked"):
        errors.append("the ECO plan is blocked")
    report = {
        "board_id": plan["board_id"],
        "errors": errors,
        "kicad_owned_before_sha256": digest(before["kicad_owned"]),
        "kicad_owned_after_sha256": digest(after["kicad_owned"]),
        "passed": not errors,
        "schema_version": SCHEMA_VERSION,
    }
    if args.output:
        atomic_write_json(args.output, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not errors else 1


def command_verify_schematic_cleanup(args: argparse.Namespace) -> int:
    """Require authoritative schematic fields/nets and a clean ERC before routing."""
    require_native_handoff_platform()
    manifest = load_manifest(args.manifest)
    augmentation = load_augmentation(args.augmentation, manifest)
    root_schematic = args.schematic.resolve()
    if not root_schematic.is_file() or root_schematic.suffix != ".kicad_sch":
        raise HandoffError(f"root schematic is missing or invalid: {root_schematic}")
    validate_schematic_hierarchy(root_schematic, root_schematic.parent)
    cli = resolve_executable(
        args.kicad_cli, "kicad-cli", (Path("/opt/homebrew/bin/kicad-cli"),)
    )
    source_before = hash_protected_tree(root_schematic.parent)
    commands = []
    with tempfile.TemporaryDirectory(prefix="stillair-schematic-cleanup-") as raw_dir:
        temporary = Path(raw_dir)
        netlist_path = temporary / "schematic.netlist.xml"
        erc_path = temporary / "schematic-erc.json"
        environment = dict(os.environ)
        commands.append(
            run_staged_command(
                [
                    str(cli), "sch", "export", "netlist", "--format", "kicadxml",
                    "--output", str(netlist_path), str(root_schematic),
                ],
                root_schematic.parent,
                environment,
            )
        )
        commands.append(
            run_staged_command(
                [
                    str(cli), "sch", "erc", "--format", "json",
                    "--output", str(erc_path), str(root_schematic),
                ],
                root_schematic.parent,
                environment,
            )
        )
        if hash_protected_tree(root_schematic.parent) != source_before:
            raise HandoffError("KiCad cleanup verification modified protected source files")
        schematic = schematic_snapshot_from_netlist(netlist_path)
        errors = schematic_snapshot_parity_errors(
            schematic, manifest, augmentation, strict_fields=True
        )
        erc_report = read_json(erc_path)
        check = validate_initial_check_report(erc_report, augmentation, schematic=True)
        if not check["clean"]:
            errors.append(
                "schematic ERC is not clean: "
                + ", ".join(
                    f"{kind}={count}"
                    for kind, count in check["declared_findings"].items()
                )
            )
        netlist_sha256 = hashlib.sha256(netlist_path.read_bytes()).hexdigest()
        erc_sha256 = hashlib.sha256(erc_path.read_bytes()).hexdigest()
    report = {
        "board_id": manifest["board"]["stable_id"],
        "commands": commands,
        "errors": errors,
        "passed": not errors,
        "schema_version": SCHEMA_VERSION,
        "root_schematic": str(root_schematic),
        "root_schematic_sha256": hashlib.sha256(root_schematic.read_bytes()).hexdigest(),
        "schematic_netlist_sha256": netlist_sha256,
        "erc_report_sha256": erc_sha256,
    }
    if args.output:
        atomic_write_json(args.output, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not errors else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    normalize = subparsers.add_parser("normalize", help="validate and canonicalize a source manifest")
    normalize.add_argument("manifest", type=Path)
    normalize.add_argument("-o", "--output", type=Path, required=True)
    normalize.add_argument("--augmentation", type=Path)
    normalize.set_defaults(function=command_normalize)

    stage = subparsers.add_parser("stage", help="build and export an initial KiCad handoff in a new staging directory")
    stage.add_argument("manifest", type=Path)
    stage.add_argument("--augmentation", type=Path)
    stage.add_argument("--build-command", required=True, help="JSON argv array")
    stage.add_argument("--export-command", required=True, help="JSON argv array")
    stage.add_argument("--production-dir", type=Path, required=True, help="tree whose existing KiCad sources must remain byte-identical")
    stage.add_argument("--kicad-cli", type=Path, help="parse-check executable; discovered from PATH by default")
    stage.add_argument("--kicad-python", type=Path, help="Python executable with pcbnew bindings; defaults to tools/kicad_python.sh")
    stage.add_argument("--footprint-root", type=Path, help="root containing KiCad *.pretty footprint libraries; common paths are discovered")
    stage.add_argument("--source-dir", type=Path, default=Path.cwd())
    stage.add_argument("--staging-root", type=Path)
    stage.set_defaults(function=command_stage)

    accept = subparsers.add_parser("accept", help="record a reviewed handoff as the committed comparison lock")
    accept.add_argument("manifest", type=Path)
    accept.add_argument("--augmentation", type=Path)
    accept.add_argument("--snapshot", type=Path, required=True)
    accept.add_argument("--receipt", type=Path, required=True)
    accept.add_argument("--lock", type=Path, required=True)
    accept.set_defaults(function=command_accept)

    snapshot = subparsers.add_parser(
        "snapshot-kicad",
        help="read a saved production board through pcbnew and emit semantic state",
    )
    snapshot.add_argument("board", type=Path)
    snapshot.add_argument("manifest", type=Path)
    snapshot.add_argument("--augmentation", type=Path, required=True)
    snapshot.add_argument("--schematic-netlist", type=Path, required=True)
    snapshot.add_argument("--rules", type=Path, action="append", default=[])
    snapshot.add_argument("-o", "--output", type=Path, required=True)
    routed_group = snapshot.add_mutually_exclusive_group()
    routed_group.add_argument("--routed", dest="routed", action="store_true")
    routed_group.add_argument("--unrouted", dest="routed", action="store_false")
    snapshot.set_defaults(function=command_snapshot_kicad, routed=None)

    augment = subparsers.add_parser(
        "augment-staged",
        help="apply source placement and official footprints to a staged board via pcbnew",
    )
    augment.add_argument("board", type=Path)
    augment.add_argument("manifest", type=Path)
    augment.add_argument("--augmentation", type=Path, required=True)
    augment.add_argument("--footprint-root", type=Path, required=True)
    augment.set_defaults(function=command_augment_staged)

    plan = subparsers.add_parser("plan", help="classify source changes and enforce routed-board safety gates")
    plan.add_argument("manifest", type=Path)
    plan.add_argument("--augmentation", type=Path)
    plan.add_argument("--snapshot", type=Path, required=True)
    plan.add_argument("--lock", type=Path, required=True)
    plan.add_argument("-o", "--output", type=Path)
    plan.add_argument("--allow-routed-eco", action="store_true")
    plan.add_argument("--allow-routed-placement", action="store_true")
    plan.set_defaults(function=command_plan)

    verify = subparsers.add_parser("verify-preservation", help="prove an applied ECO preserved KiCad-owned geometry")
    verify.add_argument("--plan", type=Path, required=True)
    verify.add_argument("--before-snapshot", type=Path, required=True)
    verify.add_argument("--after-snapshot", type=Path, required=True)
    verify.add_argument("-o", "--output", type=Path)
    verify.set_defaults(function=command_verify_preservation)

    cleanup = subparsers.add_parser(
        "verify-schematic-cleanup",
        help="require strict source parity and clean ERC before routing/fabrication",
    )
    cleanup.add_argument("manifest", type=Path)
    cleanup.add_argument("--augmentation", type=Path)
    cleanup.add_argument("--schematic", type=Path, required=True)
    cleanup.add_argument("--kicad-cli", type=Path, help="discovered from PATH by default")
    cleanup.add_argument("-o", "--output", type=Path)
    cleanup.set_defaults(function=command_verify_schematic_cleanup)
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.function(args)
    except HandoffError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
