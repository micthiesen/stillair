#!/usr/bin/env python3
"""Guarded native KiCad transactions. Run with kicad_python.sh for pcbnew.

No KiCad text is generated or patched. The transaction document is ordinary JSON:
``schema_version: 1, before_files: {relative_filename: sha256}, operations: [...]``.
Use ``project_files(board)`` to bind every native project input. ``readback()``
provides exact ``from`` states for updates; see OPERATION_KEYS and the tests for
examples. A geometry UUID can be targeted only once (including group members). Distinct
Value/MPN fields on one footprint may share a batch; the same field cannot.

All operations are preflighted against the original in-memory candidate before
any mutation. A copy is natively saved, reopened, compared with the intended
readback, then passed to an optional ``validator(candidate_board_path)``. The
validator must raise on failure or return a JSON object with ``passed: true``.
Any present ``errors`` or ``findings`` list must be empty. It may not
modify any candidate input. This is the integration point for source parity,
DRC, readiness, renders and project-specific checks. Without a validator this
receipt proves native application, NOT electrical correctness or acceptance.

Publication replaces individual files; it is NOT atomic across multiple files.
A transaction lock coordinates this tool, editor locks and input hashes reject
known concurrent changes. On publication failure only unchanged published files
are rolled back; recovery copies are retained if rollback is incomplete. An
external writer can still race the final check, so keep the project closed.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import tempfile
import uuid as uuid_module
from contextlib import contextmanager


class NativeError(ValueError):
    """A plan, capability, native readback or publication requirement failed."""


OPERATION_KEYS = {
    "footprint_move": {"op", "uuid", "from", "to", "associated_uuids"},
    "pad_paste": {"op", "uuid", "from", "to"},
    "field": {"op", "uuid", "name", "from", "to"},
    "track_add": {"op", "uuid", "geometry"},
    "track_delete": {"op", "uuid", "geometry"},
    "via_add": {"op", "uuid", "geometry"},
    "via_delete": {"op", "uuid", "geometry"},
    "zone_add": {"op", "uuid", "to"},
    "zone_update": {"op", "uuid", "from", "to"},
    "outline_rectangle": {"op", "uuids", "from", "bounds_mm", "width_mm"},
    "text_add": {"op", "uuid", "to"},
    "text_update": {"op", "uuid", "from", "to"},
    "netclass_update": {"op", "name", "from", "to"},
}
UNAVAILABLE = {
    "schematic_fields": "No verified schematic native mutation API; use a verified connector or KiCad GUI.",
    "physical_stack": "Native physical stack serialization is not verified by this engine.",
    "custom_rules": "No verified native rule-file writer; this engine never writes .kicad_dru text.",
    "footprint_replace": "Requires a source-aware footprint and pad identity mapping.",
    "netclass_assignments": "Only existing netclass sizes are supported; assignment mutation is not verified.",
    "blind_buried_microvias": "Only through vias are supported.",
    "router_preferences": "GUI choices live in .kicad_prl; BOARD_DESIGN_SETTINGS values do not prove saved GUI preferences.",
    "complex_zone_update": "Zone updates require one simple outline, polygon fill and no holes.",
}
_NATIVE_RUNTIME = None
_NATIVE_ACTIVE = set()


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _json_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def _keys(value, expected, label):
    if not isinstance(value, dict) or set(value) != expected:
        raise NativeError(f"{label} requires exactly: {', '.join(sorted(expected))}")


def _number(value, label, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise NativeError(f"{label} must be a finite number")
    if positive and value <= 0:
        raise NativeError(f"{label} must be positive")
    return value


def _point(value, label):
    if not isinstance(value, list) or len(value) != 2:
        raise NativeError(f"{label} must be [x, y] in mm")
    for v in value:
        _number(v, label)


def _uuid(value):
    try:
        if str(uuid_module.UUID(value)) != value or uuid_module.UUID(value).int == 0:
            raise ValueError()
    except (ValueError, TypeError, AttributeError):
        raise NativeError(f"Invalid canonical nonzero UUID: {value!r}") from None
    return value


def _path(path):
    original = Path(path).absolute()
    if original.is_symlink():
        raise NativeError(f"Symlinked board is not supported: {original}")
    original = original.resolve()
    if original.suffix != ".kicad_pcb" or not original.is_file():
        raise NativeError(f"Expected an existing .kicad_pcb: {original}")
    if original.with_suffix(".kicad_pro").is_symlink():
        raise NativeError("Symlinked adjacent project is not supported")
    if not original.with_suffix(".kicad_pro").is_file():
        raise NativeError("The adjacent .kicad_pro is required for project-aware native operations")
    return original


def _check_editor_locks(board):
    for suffix in (".kicad_pcb", ".kicad_sch", ".kicad_pro"):
        native = board.with_suffix(suffix)
        for name in (f"~{native.name}.lck", native.name + ".lck"):
            if (board.parent / name).exists():
                raise NativeError(f"Project editor lock exists: {board.parent / name}; close KiCad first")


def project_files(board_path):
    """Hash direct project inputs and adjacent local libraries, never evidence trees.

    Include extra inputs in before_files when an external validator depends on
    them. All supplied inputs are copied and guarded, but only board/project may
    be published. Referenced libraries outside this directory are not copied.
    """
    board = _path(board_path)
    root = board.parent
    paths = {board, board.with_suffix(".kicad_pro")}
    for suffix in (".kicad_sch", ".kicad_dru", ".kicad_prl"):
        candidate = board.with_suffix(suffix)
        if candidate.exists():
            paths.add(candidate)
    for name in ("fp-lib-table", "sym-lib-table"):
        if (root / name).exists():
            paths.add(root / name)
    # Reuse the existing hierarchy guard rather than omitting child sheets or
    # maintaining another schematic parser. Direct siblings are native inputs
    # too; referenced nested sheets are resolved and constrained to this root.
    from tscircuit_handoff import validate_schematic_hierarchy, HandoffError
    for schematic in root.glob("*.kicad_sch"):
        try:
            paths.update(validate_schematic_hierarchy(schematic, root))
        except HandoffError as exc:
            raise NativeError(str(exc)) from exc
    paths.update(root.glob("*.kicad_sym"))
    for library in root.glob("*.pretty"):
        paths.update(library.rglob("*.kicad_mod"))
    for path in paths:
        if path.is_symlink() or path != path.resolve() or not path.is_file():
            raise NativeError(f"Native project input is not a regular canonical file: {path}")
    return {str(p.relative_to(root)): sha256(p) for p in sorted(paths)}


def validate_transaction(board_path, transaction):
    """Pure Python plan/file validation; does not import pcbnew or save anything."""
    board = _path(board_path)
    _check_editor_locks(board)
    _keys(transaction, {"schema_version", "before_files", "operations"}, "transaction")
    if type(transaction["schema_version"]) is not int or transaction["schema_version"] != 1:
        raise NativeError("Unsupported transaction schema_version")
    hashes = transaction["before_files"]
    if not isinstance(hashes, dict) or not hashes:
        raise NativeError("before_files must contain project input SHA256 hashes")
    for name, expected in hashes.items():
        if not isinstance(name, str):
            raise NativeError("before_files names must be relative strings")
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts or str(relative) != name:
            raise NativeError(f"Unsafe before_files path: {name}")
        target = board.parent / relative
        if target != target.resolve() or not target.is_file():
            raise NativeError(f"Missing or symlinked before_files input: {name}")
        if not isinstance(expected, str) or len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
            raise NativeError(f"Invalid SHA256 for {name}")
        if sha256(target) != expected:
            raise NativeError(f"Stale transaction input: {name}")
    if not set(project_files(board)).issubset(hashes):
        raise NativeError("before_files omits a native project/rule/library input")
    operations = transaction["operations"]
    if not isinstance(operations, list) or not operations:
        raise NativeError("operations must be a nonempty list")
    selectors = set()
    for operation in operations:
        if not isinstance(operation, dict) or operation.get("op") not in OPERATION_KEYS:
            raise NativeError(f"Unknown/unsupported operation: {operation!r}")
        op = operation["op"]
        _keys(operation, OPERATION_KEYS[op], op)
        claimed = []
        if "uuid" in operation:
            identifier = _uuid(operation["uuid"])
            claimed.append("field:" + identifier + ":" + str(operation["name"]) if op == "field" else identifier)
        if op == "footprint_move":
            members = operation["associated_uuids"]
            if not isinstance(members, list):
                raise NativeError("associated_uuids must be an explicit list")
            claimed.extend(_uuid(member) for member in members)
            for name in ("from", "to"):
                pose = operation[name]
                _keys(pose, {"position_mm", "rotation_deg"}, "footprint pose")
                _point(pose["position_mm"], "footprint position")
                if not 0 <= _number(pose["rotation_deg"], "rotation_deg") < 360:
                    raise NativeError("rotation_deg must be in [0, 360)")
        if op == "outline_rectangle":
            if not isinstance(operation["uuids"], list) or len(operation["uuids"]) != 4:
                raise NativeError("outline_rectangle requires four exact UUIDs")
            claimed.extend(_uuid(uid) for uid in operation["uuids"])
            bounds = operation["bounds_mm"]
            if not isinstance(bounds, list) or len(bounds) != 4:
                raise NativeError("bounds_mm must be [left, top, right, bottom]")
            for v in bounds:
                _number(v, "outline bounds")
            if bounds[2] <= bounds[0] or bounds[3] <= bounds[1]:
                raise NativeError("Rectangle bounds must have positive area")
            _number(operation["width_mm"], "outline width", True)
        if op == "netclass_update":
            if not isinstance(operation["name"], str) or not operation["name"]:
                raise NativeError("netclass name must be nonempty")
            claimed.append("netclass:" + operation["name"])
        if op == "field" and (operation["name"] not in ("Value", "MPN") or
                              not isinstance(operation["to"], str) or
                              (operation["from"] is not None and not isinstance(operation["from"], str))):
            raise NativeError("field supports explicit Value/MPN string replacement only")
        for selector in claimed:
            if selector in selectors:
                raise NativeError(f"Duplicate selector in batch: {selector}")
            selectors.add(selector)
    return board


def _runtime():
    global _NATIVE_RUNTIME
    if _NATIVE_RUNTIME is None:
        try:
            import pcbnew
            import wx
        except ImportError as exc:
            raise NativeError("Run through pcb/tools/kicad_python.sh; pcbnew and wx are required") from exc
        app = wx.GetApp() or wx.App(False)
        _NATIVE_RUNTIME = (pcbnew, app, wx.LogNull())
    return _NATIVE_RUNTIME[0]


def capabilities():
    """Known operations, with unavailable capabilities stated rather than guessed."""
    try:
        pcbnew = _runtime()
        version = str(pcbnew.GetBuildVersion())
        available = True
    except NativeError:
        version, available = None, False
    return {"schema_version": 1, "pcbnew_available": available, "kicad_version": version,
            "verified_kicad_versions": ["10.0.5"],
            "supported_operations": sorted(OPERATION_KEYS), "unavailable": UNAVAILABLE,
            "requires_closed_project": True, "requires_external_acceptance_checks": True,
            "publication": "per-file replacement with guarded rollback, not multi-file atomic"}


def _uid(item):
    return str(item.m_Uuid.AsString())


def _mm(pcbnew, value):
    return round(pcbnew.ToMM(value), 6)


def _xy(pcbnew, point):
    return [_mm(pcbnew, point.x), _mm(pcbnew, point.y)]


def _optional_mm(pcbnew, value):
    return None if value is None else _mm(pcbnew, value)


def _layers(board, item):
    return sorted(str(board.GetLayerName(layer)) for layer in item.GetLayerSet().Seq())


def _pose(pcbnew, item):
    return {"position_mm": _xy(pcbnew, item.GetPosition()),
            "rotation_deg": round(float(item.GetOrientationDegrees()) % 360, 6)}


def _paste(board, pcbnew, pad):
    return {"paste_layers": [layer for layer in _layers(board, pad) if layer in ("F.Paste", "B.Paste")],
            "margin_mm": _optional_mm(pcbnew, pad.GetLocalSolderPasteMargin()),
            "margin_ratio": pad.GetLocalSolderPasteMarginRatio()}


def _track(board, pcbnew, item):
    data = {"net": str(item.GetNetname()), "layer": str(board.GetLayerName(item.GetLayer())),
            "start_mm": _xy(pcbnew, item.GetStart()), "end_mm": _xy(pcbnew, item.GetEnd()),
            "width_mm": _mm(pcbnew, item.GetWidth())}
    if isinstance(item, pcbnew.PCB_ARC):
        data["mid_mm"] = _xy(pcbnew, item.GetMid())
    return data


def _via(board, pcbnew, item):
    return {"net": str(item.GetNetname()), "position_mm": _xy(pcbnew, item.GetPosition()),
            "diameter_mm": _mm(pcbnew, item.GetWidth(item.TopLayer())),
            "drill_mm": _mm(pcbnew, item.GetDrillValue()),
            "layers": [str(board.GetLayerName(item.TopLayer())), str(board.GetLayerName(item.BottomLayer()))],
            "via_type": int(item.GetViaType()),
            "front_tenting": int(item.GetFrontTentingMode()), "back_tenting": int(item.GetBackTentingMode())}


def _zone(board, pcbnew, item):
    outline = item.Outline()
    contours = [[_xy(pcbnew, outline.COutline(i).CPoint(j))
                 for j in range(outline.COutline(i).PointCount())]
                for i in range(outline.OutlineCount())]
    return {"net": str(item.GetNetname()), "layers": _layers(board, item),
            "name": str(item.GetZoneName()), "outline_mm": contours[0] if len(contours) == 1 else contours,
            "simple_outline": len(contours) == 1 and outline.HoleCount(0) == 0,
            "rule_area": bool(item.GetIsRuleArea()), "fill_mode": int(item.GetFillMode()),
            "clearance_mm": _optional_mm(pcbnew, item.GetLocalClearance()),
            "min_thickness_mm": _mm(pcbnew, item.GetMinThickness()),
            "thermal_gap_mm": _mm(pcbnew, item.GetThermalReliefGap()),
            "thermal_spoke_mm": _mm(pcbnew, item.GetThermalReliefSpokeWidth()),
            "pad_connection": int(item.GetPadConnection()), "island_removal": int(item.GetIslandRemovalMode()),
            "priority": int(item.GetAssignedPriority()),
            "keepout": {key: bool(getattr(item, method)()) for key, method in KEEPOUT_GETTERS.items()}}


KEEPOUT_GETTERS = {"tracks": "GetDoNotAllowTracks", "vias": "GetDoNotAllowVias", "pads": "GetDoNotAllowPads",
                   "footprints": "GetDoNotAllowFootprints", "zone_fills": "GetDoNotAllowZoneFills"}
NETCLASS_METHODS = {"track_width_mm": "TrackWidth", "clearance_mm": "Clearance", "via_diameter_mm": "ViaDiameter",
                   "via_drill_mm": "ViaDrill", "diff_pair_width_mm": "DiffPairWidth", "diff_pair_gap_mm": "DiffPairGap",
                   "diff_pair_via_gap_mm": "DiffPairViaGap"}


def _netclass(pcbnew, item):
    return {key: _mm(pcbnew, getattr(item, "Get" + suffix)()) for key, suffix in NETCLASS_METHODS.items()}


def _text(board, pcbnew, item):
    return {"text": str(item.GetText()), "position_mm": _xy(pcbnew, item.GetPosition()),
            "layer": str(board.GetLayerName(item.GetLayer())), "size_mm": _xy(pcbnew, item.GetTextSize()),
            "thickness_mm": _mm(pcbnew, item.GetTextThickness()),
            "rotation_deg": round(float(item.GetTextAngle().AsDegrees()) % 360, 6),
            "mirrored": bool(item.IsMirrored())}


def _shape(board, pcbnew, item):
    return {"shape": int(item.GetShape()), "layer": str(board.GetLayerName(item.GetLayer())),
            "start_mm": _xy(pcbnew, item.GetStart()), "end_mm": _xy(pcbnew, item.GetEnd()),
            "width_mm": _mm(pcbnew, item.GetWidth())}


class NativeProject:
    """A closed, existing project loaded through the native SettingsManager.

    Keep this context alive while accessing objects. Saving is explicit; exit
    unloads WITHOUT saving. Use apply_transaction for production changes because
    this low-level session alone does not isolate or validate a mutation.
    """
    def __init__(self, board_path, read_only=False):
        self.read_only = read_only
        self.path = _path(board_path)
        self.project_path = self.path.with_suffix(".kicad_pro")
        self.board = self.project = self.manager = self.pcbnew = None

    def __enter__(self):
        if not self.read_only:
            _check_editor_locks(self.path)
        if self.project_path in _NATIVE_ACTIVE:
            raise NativeError("A native session for this project is already active")
        p = self.pcbnew = _runtime()
        self.manager = p.GetSettingsManager()
        try:
            if not self.manager.LoadProject(str(self.project_path), False):
                raise NativeError(f"Native project load failed: {self.project_path}")
            self.project = self.manager.GetProject(str(self.project_path))
            self.board = p.LoadBoard(str(self.path))
            if self.project is None or self.board is None:
                raise NativeError("KiCad returned no board/project")
            self.board.SetProject(self.project)
            _NATIVE_ACTIVE.add(self.project_path)
            return self
        except Exception:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *_):
        self.board = None
        if self.project is not None:
            self.manager.UnloadProject(self.project, False)
        self.project = None
        _NATIVE_ACTIVE.discard(self.project_path)

    def fill(self):
        if self.read_only:
            raise NativeError("Read-only native session cannot refill")
        self.board.SynchronizeNetsAndNetClasses(False)
        self.board.BuildConnectivity()
        if not self.pcbnew.ZONE_FILLER(self.board).Fill(self.board.Zones()):
            raise NativeError("Project-aware native zone fill failed")

    def save(self, save_project=False):
        if self.read_only:
            raise NativeError("Read-only native session cannot save")
        _check_editor_locks(self.path)
        if not self.pcbnew.SaveBoard(str(self.path), self.board):
            raise NativeError("Native SaveBoard failed")
        if save_project:
            # SaveProjectCopy has a void return in KiCad 10. Verify by readback,
            # not by treating its None result as failure or trusting SaveProject.
            self.manager.SaveProjectCopy(str(self.project_path), self.project)
            if not self.project_path.is_file():
                raise NativeError("Native SaveProjectCopy produced no project")
            json.loads(self.project_path.read_text())

    def capabilities(self):
        return capabilities()

    def items(self):
        """Exact UUID lookup with cross-category duplicate detection."""
        result = {}
        def add(item, kind):
            uid = _uid(item)
            if uid in result:
                raise NativeError(f"Duplicate native UUID: {uid}")
            result[uid] = (kind, item)
        for fp in self.board.GetFootprints():
            add(fp, "footprint")
            for pad in fp.Pads():
                add(pad, "pad")
            for item in fp.GraphicalItems():
                add(item, "footprint_graphic")
            for item in fp.GetFields():
                add(item, "footprint_field")
        for item in self.board.GetTracks():
            add(item, "via" if isinstance(item, self.pcbnew.PCB_VIA) else "track")
        for item in self.board.Zones():
            add(item, "zone")
        for item in self.board.GetDrawings():
            add(item, "text" if isinstance(item, self.pcbnew.PCB_TEXT) else "drawing")
        for item in self.board.Groups():
            add(item, "group")
        return result

    def readback(self):
        """Stable native geometry/settings readback; not a schematic/DRC report."""
        b, p = self.board, self.pcbnew
        result = {"footprints": {}, "pads": {}, "tracks": {}, "vias": {}, "zones": {}, "drawings": {}}
        for fp in b.GetFootprints():
            result["footprints"][_uid(fp)] = {"ref": str(fp.GetReference()), "pose": _pose(p, fp),
                "layer": str(b.GetLayerName(fp.GetLayer())), "fpid": str(fp.GetFPID().GetUniStringLibId()),
                "fields": {str(f.GetName()): str(f.GetText()) for f in fp.GetFields()},
                "attributes": int(fp.GetAttributes())}
            for pad in fp.Pads():
                result["pads"][_uid(pad)] = {"footprint_uuid": _uid(fp), "number": str(pad.GetNumber()),
                    "net": str(pad.GetNetname()), "position_mm": _xy(p, pad.GetPosition()),
                    "rotation_deg": round(float(pad.GetOrientationDegrees()) % 360, 6),
                    "size_mm": _xy(p, pad.GetSize()), "drill_mm": _xy(p, pad.GetDrillSize()),
                    "drill_shape": int(pad.GetDrillShape()), "shape": int(pad.GetShape()),
                    "attribute": int(pad.GetAttribute()), "layers": _layers(b, pad), "paste": _paste(b, p, pad),
                    "mask_margin_mm": _optional_mm(p, pad.GetLocalSolderMaskMargin())}
        for item in b.GetTracks():
            kind = "vias" if isinstance(item, p.PCB_VIA) else "tracks"
            result[kind][_uid(item)] = _via(b, p, item) if kind == "vias" else _track(b, p, item)
        for item in b.Zones():
            result["zones"][_uid(item)] = _zone(b, p, item)
        for item in b.GetDrawings():
            if isinstance(item, p.PCB_TEXT):
                data = {"kind": "text", **_text(b, p, item)}
            elif isinstance(item, p.PCB_SHAPE):
                data = {"kind": "shape", **_shape(b, p, item)}
            else:
                data = {"kind": str(item.GetClass()), "layer": str(b.GetLayerName(item.GetLayer()))}
            result["drawings"][_uid(item)] = data
        ns = b.GetDesignSettings().m_NetSettings
        result["netclasses"] = {"Default": _netclass(p, ns.GetDefaultNetclass())}
        result["netclasses"].update({str(name): _netclass(p, c) for name, c in ns.GetNetclasses().items()})
        result["copper_layers"] = int(b.GetCopperLayerCount())
        return result


def _layer(session, name, copper=False):
    if not isinstance(name, str):
        raise NativeError("Layer names must be strings")
    layer = session.board.GetLayerID(name)
    if layer < 0 or not session.board.IsLayerEnabled(layer):
        raise NativeError(f"Unknown or disabled layer: {name}")
    if copper and not session.pcbnew.IsCopperLayer(layer):
        raise NativeError(f"Expected copper layer: {name}")
    return layer


def _net(session, name, empty=False):
    if not isinstance(name, str) or (not name and not empty):
        raise NativeError("Copper requires an explicit nonempty existing net")
    net = session.board.FindNet(name)
    if net is None or str(net.GetNetname()) != name:
        raise NativeError(f"Unknown native net: {name}")
    return net


def _positive_mm(value, name):
    _number(value, name, True)
    if value < 0.000001:
        raise NativeError(f"{name} is below native nanometre precision")


def _validate_geometry(session, kind, data):
    expected = ({"net", "layer", "start_mm", "end_mm", "width_mm"} if kind == "track" else
                {"net", "position_mm", "diameter_mm", "drill_mm", "layers", "via_type", "front_tenting", "back_tenting"})
    _keys(data, expected, kind + " geometry")
    _net(session, data["net"])
    if kind == "track":
        _layer(session, data["layer"], True)
        _point(data["start_mm"], "track start")
        _point(data["end_mm"], "track end")
        if data["start_mm"] == data["end_mm"]:
            raise NativeError("Zero-length track is not supported")
        _positive_mm(data["width_mm"], "track width")
    else:
        _point(data["position_mm"], "via position")
        for field in ("diameter_mm", "drill_mm"):
            _positive_mm(data[field], field)
        if data["drill_mm"] >= data["diameter_mm"]:
            raise NativeError("Via diameter must exceed its drill")
        if data["layers"] != ["F.Cu", "B.Cu"] or data["via_type"] != session.pcbnew.VIATYPE_THROUGH:
            raise NativeError("Only F.Cu/B.Cu through vias are supported")
        for field in ("front_tenting", "back_tenting"):
            if type(data[field]) is not int or data[field] not in (0, 1, 2):
                raise NativeError("Unsupported via tenting enum")


def _validate_zone(session, data):
    expected = {"net", "layers", "name", "outline_mm", "simple_outline", "rule_area", "fill_mode",
                "clearance_mm", "min_thickness_mm", "thermal_gap_mm", "thermal_spoke_mm", "pad_connection",
                "island_removal", "priority", "keepout"}
    _keys(data, expected, "zone state")
    if data["simple_outline"] is not True or data["fill_mode"] != session.pcbnew.ZONE_FILL_MODE_POLYGONS:
        raise NativeError("Only simple polygon-fill zones are supported")
    if type(data["rule_area"]) is not bool or not isinstance(data["name"], str):
        raise NativeError("Zone rule_area/name types are invalid")
    _net(session, data["net"], empty=data["rule_area"])
    layers = data["layers"]
    if not isinstance(layers, list) or not layers or layers != sorted(set(layers)):
        raise NativeError("Zone layers must be a sorted nonempty unique list")
    for name in layers:
        _layer(session, name, True)
    points = data["outline_mm"]
    if not isinstance(points, list) or len(points) < 3:
        raise NativeError("Zone requires at least three polygon vertices")
    for point in points:
        _point(point, "zone vertex")
    if len(set(tuple(v) for v in points)) != len(points):
        raise NativeError("Zone vertices must be unique (do not repeat closing vertex)")
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(points, points[1:] + points[:1]))
    if area == 0:
        raise NativeError("Zone outline has zero signed area")
    for field in ("clearance_mm", "min_thickness_mm", "thermal_gap_mm", "thermal_spoke_mm"):
        if data[field] is None and field == "clearance_mm":
            continue
        if _number(data[field], field) < 0 or (field == "min_thickness_mm" and data[field] == 0):
            raise NativeError(f"Invalid zone {field}")
    for field, values in (("pad_connection", (-1, 0, 1, 2, 3)), ("island_removal", (0, 1, 2))):
        if type(data[field]) is not int or data[field] not in values:
            raise NativeError(f"Unsupported {field}")
    if type(data["priority"]) is not int or data["priority"] < 0:
        raise NativeError("Zone priority must be a nonnegative integer")
    _keys(data["keepout"], set(KEEPOUT_GETTERS), "zone keepout")
    if any(type(value) is not bool for value in data["keepout"].values()):
        raise NativeError("Keepout values must be boolean")


def _validate_text(session, data):
    _keys(data, {"text", "position_mm", "layer", "size_mm", "thickness_mm", "rotation_deg", "mirrored"}, "text state")
    if not isinstance(data["text"], str) or type(data["mirrored"]) is not bool:
        raise NativeError("Text content/mirroring types are invalid")
    layer = _layer(session, data["layer"])
    if session.pcbnew.IsCopperLayer(layer) or data["layer"] in ("Edge.Cuts", "F.Mask", "B.Mask", "F.Paste", "B.Paste"):
        raise NativeError("Service labels must be on silk/fabrication/documentation layers")
    _point(data["position_mm"], "text position")
    _point(data["size_mm"], "text size")
    for value in data["size_mm"]:
        _positive_mm(value, "text size")
    _positive_mm(data["thickness_mm"], "text thickness")
    if not 0 <= _number(data["rotation_deg"], "text rotation") < 360:
        raise NativeError("Text rotation must be in [0, 360)")


def _preflight(session, operations):
    items, snapshot = session.items(), session.readback()
    for operation in operations:
        op = operation["op"]
        uid = operation.get("uuid")
        pair = items.get(uid)
        if op.endswith("_add"):
            if uid in items:
                raise NativeError(f"Added UUID already exists in native board: {uid}")
        elif uid is not None and pair is None:
            raise NativeError(f"Native UUID not found: {uid}")
        if op == "footprint_move":
            if pair[0] != "footprint" or snapshot["footprints"][uid]["pose"] != operation["from"]:
                raise NativeError("footprint_move source pose/type differs")
            for member in operation["associated_uuids"]:
                if member not in items or items[member][0] not in ("track", "via", "zone"):
                    raise NativeError("Associated group members must be exact existing track/via/zone UUIDs")
        elif op == "pad_paste":
            if pair[0] != "pad" or snapshot["pads"][uid]["paste"] != operation["from"]:
                raise NativeError("pad_paste source/type differs")
            data = operation["to"]
            _keys(data, {"paste_layers", "margin_mm", "margin_ratio"}, "paste state")
            if not isinstance(data["paste_layers"], list) or data["paste_layers"] != sorted(set(data["paste_layers"])) or any(
                    name not in ("F.Paste", "B.Paste") for name in data["paste_layers"]):
                raise NativeError("Only F.Paste/B.Paste layer membership may change")
            for field in ("margin_mm", "margin_ratio"):
                if data[field] is not None:
                    _number(data[field], field)
        elif op == "field":
            if pair[0] != "footprint" or snapshot["footprints"][uid]["fields"].get(operation["name"]) != operation["from"]:
                raise NativeError("field source/type differs")
            fields = [f for f in pair[1].GetFields() if str(f.GetName()) == operation["name"]]
            if len(fields) > 1:
                raise NativeError("Duplicate existing footprint field requires explicit cleanup")
        elif op.startswith("track_") or op.startswith("via_"):
            kind = op.split("_")[0]
            _validate_geometry(session, kind, operation["geometry"])
            if op.endswith("_delete") and (pair[0] != kind or snapshot[kind + "s"][uid] != operation["geometry"]):
                raise NativeError(f"Exact {kind} deletion geometry/net differs")
        elif op.startswith("zone_"):
            _validate_zone(session, operation["to"])
            if op == "zone_update":
                if pair[0] != "zone" or snapshot["zones"][uid] != operation["from"]:
                    raise NativeError("zone_update source/type differs")
                _validate_zone(session, operation["from"])
                if operation["from"]["rule_area"] != operation["to"]["rule_area"]:
                    raise NativeError("Changing between keepout and copper-zone types is unsupported")
        elif op == "outline_rectangle":
            existing = {key: value for key, value in snapshot["drawings"].items() if value.get("layer") == "Edge.Cuts"}
            if any(item.GetLayer() == session.pcbnew.Edge_Cuts for fp in session.board.GetFootprints() for item in fp.GraphicalItems()):
                raise NativeError("Outline includes footprint-owned Edge.Cuts")
            before = operation["from"]
            if before is None:
                if existing or any(key in items for key in operation["uuids"]):
                    raise NativeError("New rectangle requires no existing Edge.Cuts and unused UUIDs")
            elif before != existing or set(existing) != set(operation["uuids"]) or any(
                    value.get("shape") != session.pcbnew.SHAPE_T_SEGMENT for value in existing.values()):
                raise NativeError("Rectangle replacement must bind all four existing straight Edge.Cuts")
        elif op.startswith("text_"):
            _validate_text(session, operation["to"])
            if op == "text_update" and (pair[0] != "text" or snapshot["drawings"][uid] != {"kind": "text", **operation["from"]}):
                raise NativeError("text_update source/type differs")
        elif op == "netclass_update":
            if snapshot["netclasses"].get(operation["name"]) != operation["from"]:
                raise NativeError("Existing netclass source differs or name is unknown")
            _keys(operation["to"], set(NETCLASS_METHODS), "netclass state")
            for key, value in operation["to"].items():
                _number(value, key)
                if value <= 0 and value != -0.000001:
                    raise NativeError("Netclass sizes must be positive or native unset sentinel -0.000001")
            if 0 < operation["to"]["via_diameter_mm"] <= operation["to"]["via_drill_mm"]:
                raise NativeError("Netclass via diameter must exceed drill")
    return items, snapshot


def _vector(p, point):
    return p.VECTOR2I(p.FromMM(point[0]), p.FromMM(point[1]))


def _set_layers(session, item, names):
    layer_set = session.pcbnew.LSET()
    for name in names:
        layer_set.AddLayer(_layer(session, name))
    item.SetLayerSet(layer_set)


def _set_zone(session, item, data):
    p = session.pcbnew
    item.SetZoneName(data["name"])
    item.SetIsRuleArea(data["rule_area"])
    item.SetNet(_net(session, data["net"], empty=data["rule_area"]))
    _set_layers(session, item, data["layers"])
    outline = item.Outline()
    outline.RemoveAllContours()
    outline.NewOutline()
    for x, y in data["outline_mm"]:
        outline.Append(p.FromMM(x), p.FromMM(y))
    item.SetFillMode(data["fill_mode"])
    for key, method in (("clearance_mm", "SetLocalClearance"), ("min_thickness_mm", "SetMinThickness"),
                        ("thermal_gap_mm", "SetThermalReliefGap"), ("thermal_spoke_mm", "SetThermalReliefSpokeWidth")):
        getattr(item, method)(None if data[key] is None else p.FromMM(data[key]))
    item.SetPadConnection(data["pad_connection"])
    item.SetIslandRemovalMode(data["island_removal"])
    item.SetAssignedPriority(data["priority"])
    for key, getter in KEEPOUT_GETTERS.items():
        getattr(item, getter.replace("Get", "Set", 1))(data["keepout"][key])
    item.SetNeedRefill(True)


def _set_text(session, item, data):
    p = session.pcbnew
    item.SetText(data["text"])
    item.SetPosition(_vector(p, data["position_mm"]))
    item.SetLayer(_layer(session, data["layer"]))
    item.SetTextSize(_vector(p, data["size_mm"]))
    item.SetTextThickness(p.FromMM(data["thickness_mm"]))
    item.SetTextAngle(p.EDA_ANGLE(data["rotation_deg"], p.DEGREES_T))
    item.SetMirrored(data["mirrored"])


def _apply(session, operations, items):
    b, p = session.board, session.pcbnew
    for operation in operations:
        op, uid = operation["op"], operation.get("uuid")
        item = items.get(uid, (None, None))[1]
        if op == "footprint_move":
            old, new = operation["from"], operation["to"]
            origin = _vector(p, old["position_mm"])
            delta = _vector(p, [new["position_mm"][i] - old["position_mm"][i] for i in range(2)])
            angle = p.EDA_ANGLE(new["rotation_deg"] - old["rotation_deg"], p.DEGREES_T)
            for member in operation["associated_uuids"]:
                other = items[member][1]
                other.Rotate(origin, angle)
                other.Move(delta)
            item.SetPosition(_vector(p, new["position_mm"]))
            item.SetOrientation(p.EDA_ANGLE(new["rotation_deg"], p.DEGREES_T))
        elif op == "pad_paste":
            data = operation["to"]
            names = [name for name in _layers(b, item) if name not in ("F.Paste", "B.Paste")]
            _set_layers(session, item, names + data["paste_layers"])
            item.SetLocalSolderPasteMargin(None if data["margin_mm"] is None else p.FromMM(data["margin_mm"]))
            item.SetLocalSolderPasteMarginRatio(data["margin_ratio"])
        elif op == "field":
            # Native SetField replaces by name, unlike an annotation operation
            # which can append a duplicate property with the same name.
            item.SetField(operation["name"], operation["to"])
        elif op in ("track_delete", "via_delete"):
            b.RemoveNative(item)
        elif op in ("track_add", "via_add"):
            data = operation["geometry"]
            item = p.PCB_TRACK(b) if op == "track_add" else p.PCB_VIA(b)
            item.m_Uuid.Clone(p.KIID(uid))
            item.SetNet(_net(session, data["net"]))
            if op == "track_add":
                item.SetLayer(_layer(session, data["layer"], True))
                item.SetStart(_vector(p, data["start_mm"]))
                item.SetEnd(_vector(p, data["end_mm"]))
                item.SetWidth(p.FromMM(data["width_mm"]))
            else:
                item.SetPosition(_vector(p, data["position_mm"]))
                item.SetWidth(p.FromMM(data["diameter_mm"]))
                item.SetDrill(p.FromMM(data["drill_mm"]))
                item.SetViaType(p.VIATYPE_THROUGH)
                item.SetLayerPair(p.F_Cu, p.B_Cu)
                item.SetFrontTentingMode(data["front_tenting"])
                item.SetBackTentingMode(data["back_tenting"])
            b.Add(item)
        elif op.startswith("zone_"):
            if op == "zone_add":
                item = p.ZONE(b)
                item.m_Uuid.Clone(p.KIID(uid))
                b.Add(item)
            _set_zone(session, item, operation["to"])
        elif op == "outline_rectangle":
            x0, y0, x1, y1 = operation["bounds_mm"]
            corners = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
            for index, edge_uid in enumerate(operation["uuids"]):
                edge = items.get(edge_uid, (None, None))[1]
                if edge is None:
                    edge = p.PCB_SHAPE(b)
                    edge.m_Uuid.Clone(p.KIID(edge_uid))
                    edge.SetShape(p.SHAPE_T_SEGMENT)
                    edge.SetLayer(p.Edge_Cuts)
                    b.Add(edge)
                edge.SetStart(_vector(p, corners[index]))
                edge.SetEnd(_vector(p, corners[(index + 1) % 4]))
                edge.SetWidth(p.FromMM(operation["width_mm"]))
        elif op.startswith("text_"):
            if op == "text_add":
                item = p.PCB_TEXT(b)
                item.m_Uuid.Clone(p.KIID(uid))
                b.Add(item)
            _set_text(session, item, operation["to"])
        elif op == "netclass_update":
            ns = b.GetDesignSettings().m_NetSettings
            item = ns.GetDefaultNetclass() if operation["name"] == "Default" else ns.GetNetclasses()[operation["name"]]
            for key, suffix in NETCLASS_METHODS.items():
                getattr(item, "Set" + suffix)(p.FromMM(operation["to"][key]))


def _transformed(point, old, new):
    angle = math.radians(new["rotation_deg"] - old["rotation_deg"])
    x, y = point[0] - old["position_mm"][0], point[1] - old["position_mm"][1]
    return [round(new["position_mm"][0] + x * math.cos(angle) + y * math.sin(angle), 6),
            round(new["position_mm"][1] - x * math.sin(angle) + y * math.cos(angle), 6)]


def _expected_readback(session, before, operations):
    """Compute declared results independently of native setters, preserving rest.

    A post-setter snapshot alone would certify ignored setters or clamping. This
    expected state also makes undeclared changes to represented geometry fail.
    """
    expected = copy.deepcopy(before)
    for operation in operations:
        op, uid = operation["op"], operation.get("uuid")
        if op == "footprint_move":
            old, new = operation["from"], operation["to"]
            expected["footprints"][uid]["pose"] = copy.deepcopy(new)
            for pad in expected["pads"].values():
                if pad["footprint_uuid"] == uid:
                    pad["position_mm"] = _transformed(pad["position_mm"], old, new)
                    pad["rotation_deg"] = round((pad["rotation_deg"] + new["rotation_deg"] - old["rotation_deg"]) % 360, 6)
            for member in operation["associated_uuids"]:
                if member in expected["tracks"]:
                    track = expected["tracks"][member]
                    for key in ("start_mm", "end_mm", "mid_mm"):
                        if key in track:
                            track[key] = _transformed(track[key], old, new)
                elif member in expected["vias"]:
                    via = expected["vias"][member]
                    via["position_mm"] = _transformed(via["position_mm"], old, new)
                else:
                    zone = expected["zones"][member]
                    if not zone["simple_outline"]:
                        raise NativeError("Group moves currently require simple zone outlines")
                    zone["outline_mm"] = [_transformed(point, old, new) for point in zone["outline_mm"]]
        elif op == "field":
            expected["footprints"][uid]["fields"][operation["name"]] = operation["to"]
        elif op == "pad_paste":
            pad = expected["pads"][uid]
            pad["paste"] = copy.deepcopy(operation["to"])
            pad["layers"] = sorted([layer for layer in pad["layers"] if layer not in ("F.Paste", "B.Paste")] + operation["to"]["paste_layers"])
        elif op in ("track_add", "via_add"):
            data = copy.deepcopy(operation["geometry"])
            if op == "track_add":
                data["layer"] = str(session.board.GetLayerName(_layer(session, data["layer"])))
            expected["tracks" if op == "track_add" else "vias"][uid] = data
        elif op in ("track_delete", "via_delete"):
            del expected["tracks" if op == "track_delete" else "vias"][uid]
        elif op.startswith("zone_"):
            expected["zones"][uid] = copy.deepcopy(operation["to"])
        elif op.startswith("text_"):
            data = copy.deepcopy(operation["to"])
            data["layer"] = str(session.board.GetLayerName(_layer(session, data["layer"])))
            expected["drawings"][uid] = {"kind": "text", **data}
        elif op == "outline_rectangle":
            x0, y0, x1, y1 = operation["bounds_mm"]
            corners = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
            for index, edge_uid in enumerate(operation["uuids"]):
                expected["drawings"][edge_uid] = {"kind": "shape", "shape": session.pcbnew.SHAPE_T_SEGMENT,
                    "layer": "Edge.Cuts", "start_mm": corners[index], "end_mm": corners[(index + 1) % 4],
                    "width_mm": operation["width_mm"]}
        elif op == "netclass_update":
            expected["netclasses"][operation["name"]] = copy.deepcopy(operation["to"])
    return expected


def _assert_project_json(before, after, operations):
    """A netclass edit cannot alter exclusions, severities, assignments or minima."""
    expected = copy.deepcopy(before)
    for operation in operations:
        if operation["op"] != "netclass_update":
            continue
        classes = expected.get("net_settings", {}).get("classes", [])
        matches = [item for item in classes if item.get("name") == operation["name"]]
        if len(matches) != 1:
            raise NativeError("Existing project JSON does not uniquely represent the requested netclass")
        for key, value in operation["to"].items():
            json_key = key.removesuffix("_mm")
            if value == -0.000001:
                matches[0].pop(json_key, None)
            else:
                matches[0][json_key] = value
    if expected != after:
        raise NativeError("Native save changed undeclared project JSON settings")


def _changes(before, after):
    changes = []
    for category in sorted(set(before) | set(after)):
        left, right = before.get(category), after.get(category)
        if isinstance(left, dict) and isinstance(right, dict):
            for key in sorted(set(left) | set(right)):
                if left.get(key) != right.get(key):
                    changes.append({"category": category, "selector": key, "before": left.get(key), "after": right.get(key)})
        elif left != right:
            changes.append({"category": category, "before": left, "after": right})
    return changes


@contextmanager
def _transaction_lock(board):
    lock = board.parent / ("." + board.stem + ".native-transaction.lock")
    try:
        descriptor = os.open(str(lock), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise NativeError(f"Another native transaction lock exists: {lock}") from None
    try:
        with os.fdopen(descriptor, "w") as handle:
            handle.write(str(os.getpid()) + "\n")
        yield
    finally:
        lock.unlink()


def _publish(board, candidate_root, before_files, after_files, recovery_root):
    """Bounded rollback never overwrites a concurrent edit after our publication."""
    changed = [name for name in after_files if before_files[name] != after_files[name]]
    prepared, published = {}, []
    try:
        for name in changed:
            target = board.parent / name
            descriptor, temporary = tempfile.mkstemp(prefix="." + target.name + ".native-", dir=str(target.parent))
            os.close(descriptor)
            prepared[name] = Path(temporary)
            shutil.copy2(candidate_root / name, temporary)
        _check_editor_locks(board)
        if not set(project_files(board)).issubset(before_files):
            raise NativeError("Native input inventory changed before publication")
        for name, expected in before_files.items():
            if sha256(board.parent / name) != expected:
                raise NativeError(f"Source changed before publication: {name}")
        for name in changed:
            # Recheck this file immediately before replacement; not a filesystem
            # compare-and-swap, hence the documented requirement to close editors.
            if sha256(board.parent / name) != before_files[name]:
                raise NativeError(f"Source changed during publication: {name}")
            os.replace(prepared[name], board.parent / name)
            published.append(name)
    except Exception as exc:
        failures = []
        for name in reversed(published):
            target = board.parent / name
            try:
                if sha256(target) != after_files[name]:
                    raise NativeError("concurrent edit after publication")
                shutil.copy2(recovery_root / name, target)
            except Exception as rollback_error:
                failures.append(f"{name}: {rollback_error}")
        if failures:
            raise NativeError(f"Partial publication; recovery retained at {recovery_root}: {'; '.join(failures)}") from exc
        raise
    finally:
        for path in prepared.values():
            path.unlink(missing_ok=True)
    return changed


def apply_transaction(board_path, transaction, output_receipt=None, validator=None):
    """Natively apply a hash-bound batch; validate on saved copy before publication.

    ``validator(Path)`` runs against the candidate .kicad_pcb and its adjacent
    project, rules and copied local libraries. Raise on failure or return a dict
    with passed=True and no nonempty findings/errors; no truthiness coercion.
    Receipt writes never target a native input or existing file.
    """
    board = validate_transaction(board_path, transaction)
    receipt_path = None if output_receipt is None else Path(output_receipt).resolve()
    if receipt_path is not None:
        if receipt_path.exists() or receipt_path.suffix != ".json" or receipt_path != receipt_path.resolve():
            raise NativeError("output_receipt must be a new canonical .json path")
    if validator is not None and not callable(validator):
        raise NativeError("validator must be callable")
    before_files = dict(transaction["before_files"])
    scratch = Path(tempfile.mkdtemp(prefix="kicad-native-transaction-"))
    candidate_root, recovery_root = scratch / "candidate", scratch / "before"
    completed = False
    try:
        with _transaction_lock(board):
            validate_transaction(board, transaction)
            for root in (candidate_root, recovery_root):
                for name in before_files:
                    (root / name).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(board.parent / name, root / name)
                    if sha256(root / name) != before_files[name]:
                        raise NativeError(f"Input changed while copying: {name}")
            candidate = candidate_root / board.name
            native_inventory = set(project_files(candidate))
            project_before = json.loads(candidate.with_suffix(".kicad_pro").read_text())
            with NativeProject(candidate) as native:
                items, before = _preflight(native, transaction["operations"])
                expected = _expected_readback(native, before, transaction["operations"])
                _apply(native, transaction["operations"], items)
                native.fill()
                intended = native.readback()
                if expected != intended:
                    raise NativeError("Native setters differed from declared result: " + json.dumps(_changes(expected, intended))[:3000])
                native.items()  # reject duplicate IDs, including newly added ones
                native.save(save_project=any(op["op"] == "netclass_update" for op in transaction["operations"]))
                version = str(native.pcbnew.GetBuildVersion())
            with NativeProject(candidate) as saved:
                actual = saved.readback()
                saved.items()
            if intended != actual:
                raise NativeError("Native saved readback differs from intended state: " + json.dumps(_changes(intended, actual))[:3000])
            _assert_project_json(project_before, json.loads(candidate.with_suffix(".kicad_pro").read_text()), transaction["operations"])
            if set(project_files(candidate)) != native_inventory:
                raise NativeError("Native save changed the project input inventory")
            permitted = {board.name, board.with_suffix(".kicad_pro").name}
            after_files = {name: sha256(candidate_root / name) for name in before_files}
            if any(after_files[name] != expected for name, expected in before_files.items() if name not in permitted):
                raise NativeError("Native save changed an undeclared project input")
            validation = {"status": "not_run", "scope": "Native application only; external acceptance checks required"}
            if validator is not None:
                evidence = validator(candidate)
                json.dumps(evidence, allow_nan=False)
                if not isinstance(evidence, dict) or evidence.get("passed") is not True or any(
                        key in evidence and evidence[key] != [] for key in ("errors", "findings")):
                    raise NativeError("Validator must explicitly report passed=true with no findings/errors")
                validation = {"status": "passed", "evidence": evidence}
                if set(project_files(candidate)) != native_inventory or any(sha256(candidate_root / name) != expected for name, expected in after_files.items()):
                    raise NativeError("Validator modified candidate inputs; validation must be read-only")
            receipt = {"schema_version": 1, "kind": "native-kicad-transaction", "board": board.name,
                       "kicad_version": version, "transaction_sha256": _json_hash(transaction),
                       "before_files": before_files, "after_files": after_files,
                       "readback_before_sha256": _json_hash(before), "readback_after_sha256": _json_hash(actual),
                       "changes": _changes(before, actual), "validation": validation,
                       "publication": "per-file replacement; guarded rollback on failure; not multi-file atomic"}
            receipt["published_files"] = _publish(board, candidate_root, before_files, after_files, recovery_root)
            if receipt_path is not None:
                receipt_path.parent.mkdir(parents=True, exist_ok=True)
                # Exclusive creation avoids replacing a concurrent result. If it
                # fails after publication, report committed outputs via recovery.
                with receipt_path.open("x") as handle:
                    json.dump(receipt, handle, indent=2, sort_keys=True, allow_nan=False)
                    handle.write("\n")
            completed = True
            return receipt
    except Exception as exc:
        current = {name: sha256(board.parent / name) if (board.parent / name).is_file() else None for name in before_files}
        if current != before_files:
            raise NativeError(f"Transaction failed with changed source files; recovery retained at {scratch}: {exc}") from exc
        raise
    finally:
        if completed or all((board.parent / name).is_file() and sha256(board.parent / name) == digest for name, digest in before_files.items()):
            shutil.rmtree(scratch)


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("capabilities", help="Report verified operations and unavailable write channels")
    inputs = commands.add_parser("inputs", help="Hash native project inputs for before_files")
    inputs.add_argument("--board", required=True, type=Path)
    inspect = commands.add_parser("inspect", help="Read saved native states for exact transaction selectors/from values")
    inspect.add_argument("--board", required=True, type=Path)
    apply = commands.add_parser("apply", help="Apply an unaccepted native edit, pending external checks")
    apply.add_argument("--board", required=True, type=Path)
    apply.add_argument("--transaction", required=True, type=Path)
    apply.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "capabilities":
            result = capabilities()
        elif args.command == "inputs":
            result = project_files(args.board)
        elif args.command == "inspect":
            before = project_files(args.board)
            with NativeProject(args.board, read_only=True) as project:
                result = {"before_files": before, "readback": project.readback()}
            if project_files(args.board) != before:
                raise NativeError("Project changed during inspection")
        else:
            result = apply_transaction(args.board, json.loads(args.transaction.read_text()), args.receipt)
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    except (NativeError, OSError, json.JSONDecodeError) as exc:
        parser.exit(2, f"ERROR: {exc}\n")


if __name__ == "__main__":
    main()
