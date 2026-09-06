#!/usr/bin/env python3
"""Tests for the tscircuit/KiCad handoff boundary; requires only Python stdlib."""

from __future__ import annotations

import contextlib
import copy
import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tscircuit_handoff as handoff


def component(stable_id: str, ref: str, pads: list[str], x: float = 0) -> dict:
    return {
        "stable_id": stable_id,
        "ref": ref,
        "value": ref,
        "symbol": f"test:{ref}",
        "fields": {"MPN": f"MPN-{ref}"},
        "footprint": {
            "tscircuit": f"test_{ref.lower()}",
            "kicad": f"Test:{ref}",
            "pad_numbers": pads,
        },
        "placement": {
            "x_mm": x,
            "y_mm": 0,
            "rotation_deg": 0,
            "side": "front",
        },
    }


def manifest() -> dict:
    return {
        "schema_version": 1,
        "board": {
            "stable_id": "pcb-03",
            "width_mm": 39.75,
            "height_mm": 21,
            "layer_count": 2,
            "coordinate_system": "center-x-right-y-up",
            "kicad_origin_mm": [50, 54.5],
            "outline": {
                "kind": "rectangle",
                "center_mm": [0, 0],
                "width_mm": 39.75,
                "height_mm": 21,
            },
            "holes": [
                {"stable_id": "pcb03.h2", "ref": "U2", "x_mm": 5, "y_mm": 0, "drill_mm": 2.2},
                {"stable_id": "pcb03.h1", "ref": "U1", "x_mm": -5, "y_mm": 0, "drill_mm": 2.2},
            ],
            "specs": {"copper_oz": 1, "thickness_mm": 1.6},
        },
        "versions": {
            "node": "24.0.0",
            "tscircuit": "0.0.test",
            "circuit_json_to_kicad": "0.0.test",
            "bun": "1.2.test",
        },
        "components": [
            component("pcb03.u2", "U2", ["1", "2", "3"], 5),
            component("pcb03.u1", "U1", ["1", "2", "3"], -5),
        ],
        "nets": [
            {
                "stable_id": "pcb03.net.ground",
                "name": "AGND",
                "endpoints": [
                    {"component": "pcb03.u2", "pad": "1"},
                    {"component": "pcb03.u1", "pad": "1"},
                ],
            },
            {
                "stable_id": "pcb03.net.data",
                "name": "DATA",
                "endpoints": [
                    {"component": "pcb03.u2", "pad": "2"},
                    {"component": "pcb03.u1", "pad": "2"},
                ],
            },
        ],
    }


def augmentation() -> dict:
    return {
        "schema_version": 1,
        "board_id": "pcb-03",
        "operations": [
            {
                "id": "pcb03.kicad.coordinates",
                "kind": "coordinate_transform",
                "owner": "kicad",
                "target": {},
                "params": {
                    "tscircuit_center_mm": [0, 0],
                    "kicad_center_mm": [0, 0],
                    "x_axis": "same",
                    "y_axis": "invert",
                },
            },
            {
                "id": "pcb03.kicad.ground-zone",
                "kind": "zone",
                "owner": "kicad",
                "target": {"net_stable_id": "pcb03.net.ground"},
                "params": {"layer": "B.Cu", "clearance_mm": 0.25},
            }
        ],
    }


def snapshot(routed: bool = False, source_owned: dict | None = None) -> dict:
    if source_owned is None:
        source_owned = {
            "components": [
                {
                    "stable_id": "pcb03.u1",
                    "ref": "U1",
                    "value": "U1",
                    "footprint": "Test:U1",
                    "uuid": "uuid-u1",
                    "placement": {
                        "position_mm": [-5, 0],
                        "rotation_deg": 0,
                        "side": "front",
                    },
                    "pads": [
                        {"number": "1", "net": "AGND"},
                        {"number": "2", "net": "DATA"},
                        {"number": "3", "net": ""},
                    ],
                },
                {
                    "stable_id": "pcb03.u2",
                    "ref": "U2",
                    "value": "U2",
                    "footprint": "Test:U2",
                    "uuid": "uuid-u2",
                    "placement": {
                        "position_mm": [5, 0],
                        "rotation_deg": 0,
                        "side": "front",
                    },
                    "pads": [
                        {"number": "1", "net": "AGND"},
                        {"number": "2", "net": "DATA"},
                        {"number": "3", "net": ""},
                    ],
                },
            ],
            "outline": [
                {"start_mm": [-19.875, -10.5], "end_mm": [19.875, -10.5]},
                {"start_mm": [19.875, -10.5], "end_mm": [19.875, 10.5]},
                {"start_mm": [19.875, 10.5], "end_mm": [-19.875, 10.5]},
                {"start_mm": [-19.875, 10.5], "end_mm": [-19.875, -10.5]},
            ],
            "holes": [
                {"footprint_ref": "U1", "position_mm": [-5, 0], "drill_mm": [2.2, 2.2]},
                {"footprint_ref": "U2", "position_mm": [5, 0], "drill_mm": [2.2, 2.2]},
            ],
        }
    return {
        "board_id": "pcb-03",
        "routed": routed,
        "source_owned": source_owned,
        "kicad_owned": {
            "tracks": "tracks-sha",
            "vias": "vias-sha",
            "zones": "zones-sha",
            "rules": "rules-sha",
        },
        "uuid_map": {"pcb03.u1": "00000000-0000-0000-0000-000000000001"},
        "schematic_owned": {
            "components": [
                {"ref": "U1", "value": "U1", "footprint": "Test:U1", "symbol": "test:U1", "manufacturer_part_number": "MPN-U1", "datasheet": "", "pins": ["1", "2", "3"]},
                {"ref": "U2", "value": "U2", "footprint": "Test:U2", "symbol": "test:U2", "manufacturer_part_number": "MPN-U2", "datasheet": "", "pins": ["1", "2", "3"]},
            ],
            "nets": [
                {"name": "AGND", "endpoints": [["U1", "1"], ["U2", "1"]]},
                {"name": "DATA", "endpoints": [["U1", "2"], ["U2", "2"]]},
            ],
        },
    }


def lock_for(source: dict, augment: dict | None = None, snap: dict | None = None) -> dict:
    normalized = handoff.normalize_manifest(source)
    aug = handoff.validate_augmentation(augment or augmentation(), normalized)
    normalized_snapshot = handoff.normalize_snapshot(snap or snapshot(), "pcb-03")
    return {
        "schema_version": 1,
        "board_id": "pcb-03",
        "manifest": normalized,
        "manifest_sha256": handoff.digest(normalized),
        "augmentation": aug,
        "augmentation_sha256": handoff.digest(aug),
        "snapshot": normalized_snapshot,
        "snapshot_sha256": handoff.digest(normalized_snapshot),
    }


def schematic_netlist_xml() -> str:
    normalized = handoff.normalize_manifest(manifest())
    components = []
    for item in normalized["components"]:
        pins = "".join(f'<pin num="{pad}"/>' for pad in item["footprint"]["pad_numbers"])
        components.append(
            f'<comp ref="{item["ref"]}"><value>{item["value"]}</value>'
            f'<footprint>{item["footprint"]["kicad"]}</footprint>'
            f'<fields><field name="MPN">{item["fields"]["MPN"]}</field></fields>'
            f'<libsource lib="test" part="{item["ref"]}"/>'
            f'<units><unit><pins>{pins}</pins></unit></units></comp>'
        )
    component_by_id = {item["stable_id"]: item for item in normalized["components"]}
    nets = []
    for code, net in enumerate(normalized["nets"], 1):
        nodes = "".join(
            f'<node ref="{component_by_id[endpoint["component"]]["ref"]}" pin="{endpoint["pad"]}"/>'
            for endpoint in net["endpoints"]
        )
        nets.append(f'<net code="{code}" name="/{net["name"]}">{nodes}</net>')
    return "<export><components>" + "".join(components) + "</components><nets>" + "".join(nets) + "</nets></export>"


def kicad_report(violations: list[dict] | None = None) -> dict:
    return {
        "ignored_checks": [],
        "included_severities": ["error", "warning"],
        "unconnected_items": [],
        "violations": violations or [],
    }


class ManifestTests(unittest.TestCase):
    def test_normalization_is_stable_and_sorts_identity_sets(self) -> None:
        raw = manifest()
        first = handoff.normalize_manifest(raw)
        raw["components"].reverse()
        raw["nets"].reverse()
        raw["nets"][1]["endpoints"].reverse()
        raw["board"]["holes"].reverse()
        second = handoff.normalize_manifest(raw)
        self.assertEqual(first, second)
        self.assertEqual(handoff.digest(first), handoff.digest(second))
        self.assertEqual([item["stable_id"] for item in first["components"]], ["pcb03.u1", "pcb03.u2"])

    def test_requires_explicit_versions_and_refs(self) -> None:
        raw = manifest()
        del raw["versions"]["node"]
        with self.assertRaisesRegex(handoff.HandoffError, "node"):
            handoff.normalize_manifest(raw)
        raw = manifest()
        raw["components"][0]["ref"] = "U?"
        with self.assertRaisesRegex(handoff.HandoffError, "explicit reference"):
            handoff.normalize_manifest(raw)

    def test_rejects_unknown_and_multiply_connected_pads(self) -> None:
        raw = manifest()
        raw["nets"][1]["endpoints"][0] = {"component": "pcb03.u2", "pad": "99"}
        with self.assertRaisesRegex(handoff.HandoffError, "unknown pad"):
            handoff.normalize_manifest(raw)
        raw = manifest()
        raw["nets"][1]["endpoints"][0] = {"component": "pcb03.u2", "pad": "1"}
        with self.assertRaisesRegex(handoff.HandoffError, "appears in both"):
            handoff.normalize_manifest(raw)

    def test_validates_declarative_augmentation_targets_and_ownership(self) -> None:
        normalized = handoff.normalize_manifest(manifest())
        result = handoff.validate_augmentation(augmentation(), normalized)
        self.assertEqual(
            {operation["kind"] for operation in result["operations"]},
            {"coordinate_transform", "zone"},
        )
        bad = augmentation()
        bad["operations"][0]["target"] = {"net_stable_id": "missing"}
        with self.assertRaisesRegex(handoff.HandoffError, "unknown net"):
            handoff.validate_augmentation(bad, normalized)
        bad = augmentation()
        bad["operations"][0]["params"] = {"component_placement": [1, 2]}
        with self.assertRaisesRegex(handoff.HandoffError, "tscircuit-owned"):
            handoff.validate_augmentation(bad, normalized)

    def test_normalizes_pcbnew_snapshot_fixture_with_stable_ids_and_hashes(self) -> None:
        raw = {
            "components": [
                {
                    "ref": "U2",
                    "value": "U2",
                    "footprint": "Test:U2",
                    "uuid": "uuid-u2",
                    "placement": {"position_mm": [75.925, 63.125], "rotation_deg": 180, "side": "front"},
                    "pads": [{"number": "3", "net": ""}, {"number": "2", "net": "DATA"}, {"number": "1", "net": "AGND"}],
                },
                {
                    "ref": "U1",
                    "value": "U1",
                    "footprint": "Test:U1",
                    "uuid": "uuid-u1",
                    "placement": {"position_mm": [65.75, 63.375], "rotation_deg": 180, "side": "front"},
                    "pads": [{"number": "1", "net": "AGND"}, {"number": "2", "net": "DATA"}, {"number": "3", "net": ""}],
                },
            ],
            "outline": [{"uuid": "edge-1", "start_mm": [50, 54.5], "end_mm": [89.75, 54.5]}],
            "holes": [],
            "tracks": [{"uuid": "track-1", "net": "DATA"}],
            "vias": [],
            "zones": [{"uuid": "zone-1", "net": "AGND"}],
            "graphics": [{"uuid": "text-1", "text": "HOST"}],
            "rules": [{"path": "pcb-03.kicad_dru", "sha256": "a" * 64}],
        }
        result = handoff.normalize_kicad_snapshot_data(
            raw, handoff.normalize_manifest(manifest()), True
        )
        self.assertEqual(result["uuid_map"], {"pcb03.u1": "uuid-u1", "pcb03.u2": "uuid-u2"})
        self.assertEqual(result["source_owned"]["components"][0]["stable_id"], "pcb03.u1")
        self.assertEqual(result["kicad_owned"]["tracks"]["sha256"], handoff.digest(raw["tracks"]))
        self.assertTrue(result["routed"])

    def test_snapshot_fixture_rejects_unknown_or_missing_refs(self) -> None:
        raw = {
            "components": [], "outline": [], "holes": [], "tracks": [],
            "vias": [], "zones": [], "graphics": [], "rules": [],
        }
        with self.assertRaisesRegex(handoff.HandoffError, "missing manifest references"):
            handoff.normalize_kicad_snapshot_data(
                raw, handoff.normalize_manifest(manifest()), False
            )

    def test_semantic_parity_checks_source_owned_board_state(self) -> None:
        normalized = handoff.normalize_manifest(manifest())
        augment = handoff.validate_augmentation(augmentation(), normalized)
        accepted = handoff.normalize_snapshot(snapshot(), "pcb-03")
        self.assertEqual(handoff.parity_errors(accepted, normalized, augment), [])

        mutations = [
            ("pad net", lambda value: value["source_owned"]["components"][0]["pads"][0].update(net="DATA")),
            ("position", lambda value: value["source_owned"]["components"][0]["placement"]["position_mm"].__setitem__(0, -4)),
            ("rotation", lambda value: value["source_owned"]["components"][0]["placement"].update(rotation_deg=90)),
            ("side", lambda value: value["source_owned"]["components"][0]["placement"].update(side="back")),
            ("outline", lambda value: value["source_owned"]["outline"][0]["start_mm"].__setitem__(0, -20)),
            ("hole position", lambda value: value["source_owned"]["holes"][0]["position_mm"].__setitem__(0, -4)),
            ("hole drill", lambda value: value["source_owned"]["holes"][0]["drill_mm"].__setitem__(0, 2.5)),
            ("extra hole", lambda value: value["source_owned"]["holes"].append(copy.deepcopy(value["source_owned"]["holes"][0]))),
        ]
        for label, mutate in mutations:
            with self.subTest(label=label):
                changed = copy.deepcopy(accepted)
                mutate(changed)
                self.assertTrue(handoff.parity_errors(changed, normalized, augment))

    def test_schematic_hierarchy_and_netlist_parity_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="stillair-schematic-test-") as raw_dir:
            root = Path(raw_dir)
            top = root / "board.kicad_sch"
            top.write_text('(property "Sheetfile" "main.kicad_sch")')
            with self.assertRaisesRegex(handoff.HandoffError, "missing referenced file"):
                handoff.validate_schematic_hierarchy(top, root)
            (root / "main.kicad_sch").write_text("(kicad_sch)")
            self.assertEqual(len(handoff.validate_schematic_hierarchy(top, root)), 2)

    def test_schematic_metadata_is_extracted_and_declared_differences_are_strict(self) -> None:
        with tempfile.TemporaryDirectory(prefix="stillair-schematic-fields-") as raw_dir:
            netlist = Path(raw_dir) / "board.xml"
            netlist.write_text(schematic_netlist_xml())
            schematic = handoff.schematic_snapshot_from_netlist(netlist)
            self.assertEqual(
                schematic["components"][0]["manufacturer_part_number"], "MPN-U1"
            )
            self.assertEqual(schematic["components"][0]["symbol"], "test:U1")
            changed = copy.deepcopy(schematic)
            changed["components"][0]["symbol"] = "exporter:generated"
            aug = augmentation()
            aug["operations"].append(
                {
                    "id": "pcb03.cleanup",
                    "kind": "schematic_cleanup",
                    "owner": "kicad",
                    "target": {},
                    "params": {
                        "allowed_initial_erc_types": ["endpoint_off_grid"],
                        "allowed_initial_semantic_differences": ["symbol_id"],
                        "verification": "clean",
                    },
                }
            )
            normalized = handoff.normalize_manifest(manifest())
            normalized_aug = handoff.validate_augmentation(aug, normalized)
            declared = []
            self.assertEqual(
                handoff.schematic_snapshot_parity_errors(
                    changed, normalized, normalized_aug,
                    declared_differences=declared,
                ),
                [],
            )
            self.assertEqual(declared[0]["category"], "symbol_id")
            self.assertTrue(
                handoff.schematic_snapshot_parity_errors(
                    changed, normalized, normalized_aug, strict_fields=True
                )
            )

    def test_native_handoff_is_explicitly_macos_only(self) -> None:
        handoff.require_native_handoff_platform("darwin")
        with self.assertRaisesRegex(handoff.HandoffError, "macOS only"):
            handoff.require_native_handoff_platform("linux")

    def test_required_review_renders_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="stillair-render-test-") as raw_dir:
            root = Path(raw_dir)
            empty = root / "empty.pdf"
            empty.write_bytes(b"")
            with self.assertRaisesRegex(handoff.HandoffError, "missing or empty"):
                handoff.require_render_files([empty], root)

            netlist = root / "netlist.xml"
            netlist.write_text(schematic_netlist_xml())
            normalized = handoff.normalize_manifest(manifest())
            augment = handoff.validate_augmentation(augmentation(), normalized)
            self.assertEqual(
                handoff.schematic_netlist_parity_errors(netlist, normalized, augment), []
            )
            extra = schematic_netlist_xml().replace(
                "</components>",
                '<comp ref="X1"><value>X</value><units><unit><pins><pin num="1"/></pins></unit></units></comp></components>',
            )
            netlist.write_text(extra)
            self.assertTrue(
                handoff.schematic_netlist_parity_errors(netlist, normalized, augment)
            )
            netlist.write_text("<export><components/><nets/></export>")
            self.assertTrue(
                handoff.schematic_netlist_parity_errors(netlist, normalized, augment)
            )

    def test_initial_drc_policy_allows_only_declared_categories(self) -> None:
        normalized = handoff.normalize_manifest(manifest())
        augment = handoff.validate_augmentation(augmentation(), normalized)
        with self.assertRaisesRegex(handoff.HandoffError, "undeclared"):
            handoff.validate_initial_check_report(
                kicad_report([{"type": "silk_overlap"}]),
                augment,
                False,
            )
        augment["operations"].extend(
            [
                {"id": "silk", "kind": "silkscreen", "owner": "kicad", "target": {}, "params": {}},
                {"id": "routing", "kind": "fabrication_note", "owner": "kicad", "target": {}, "params": {"category": "routing"}},
            ]
        )
        handoff.validate_initial_check_report(
            {**kicad_report([{"type": "silk_overlap"}]),
             "unconnected_items": [{"description": "unrouted"}]},
            augment,
            False,
        )
        with self.assertRaisesRegex(handoff.HandoffError, "clearance"):
            handoff.validate_initial_check_report(
                kicad_report([{"type": "clearance"}]),
                augment,
                False,
            )
        with self.assertRaisesRegex(handoff.HandoffError, "omitted required severities"):
            handoff.validate_initial_check_report(
                {**kicad_report(), "included_severities": ["error"]}, augment, False
            )
        with self.assertRaisesRegex(handoff.HandoffError, "undeclared ignored checks"):
            handoff.validate_initial_check_report(
                {
                    **kicad_report(),
                    "ignored_checks": [{"key": "missing_courtyard"}],
                },
                augment,
                False,
            )


class PlanTests(unittest.TestCase):
    def test_routed_state_cannot_hide_extracted_copper(self) -> None:
        extracted = {"tracks": [{"uuid": "track"}], "vias": []}
        self.assertTrue(handoff.derive_routed_state(extracted, None))
        with self.assertRaisesRegex(handoff.HandoffError, "contradicts"):
            handoff.derive_routed_state(extracted, False)

    def test_classifies_stable_identity_ecos(self) -> None:
        old = handoff.normalize_manifest(manifest())
        changed = manifest()
        changed["components"][0]["placement"]["x_mm"] = 6
        changed["components"][1]["value"] = "new-value"
        changed["nets"][1]["name"] = "RENAMED_DATA"
        changed = handoff.normalize_manifest(changed)
        kinds = {item["kind"] for item in handoff.classify_changes(old, changed)}
        self.assertEqual(kinds, {"placement", "value", "net_rename"})

    def test_routed_board_blocks_placement_and_logical_ecos(self) -> None:
        changed = manifest()
        changed["components"][0]["placement"]["x_mm"] = 6
        changed["nets"][1]["name"] = "RENAMED_DATA"
        plan = handoff.build_plan(
            handoff.normalize_manifest(changed),
            handoff.validate_augmentation(augmentation(), handoff.normalize_manifest(changed)),
            lock_for(manifest(), snap=snapshot(routed=True)),
            handoff.normalize_snapshot(snapshot(routed=True), "pcb-03"),
            False,
            False,
        )
        self.assertTrue(plan["blocked"])
        self.assertIn("--allow-routed-placement", " ".join(plan["blockers"]))
        self.assertIn("--allow-routed-eco", " ".join(plan["blockers"]))

    def test_explicit_routed_overrides_unblock_known_changes(self) -> None:
        changed = manifest()
        changed["components"][0]["placement"]["x_mm"] = 6
        changed["nets"][1]["name"] = "RENAMED_DATA"
        normalized = handoff.normalize_manifest(changed)
        plan = handoff.build_plan(
            normalized,
            handoff.validate_augmentation(augmentation(), normalized),
            lock_for(manifest(), snap=snapshot(routed=True)),
            handoff.normalize_snapshot(snapshot(routed=True), "pcb-03"),
            True,
            True,
        )
        self.assertFalse(plan["blocked"])
        self.assertEqual(plan["overall_risk"], "high")

    def test_kicad_source_owned_drift_always_blocks(self) -> None:
        normalized = handoff.normalize_manifest(manifest())
        plan = handoff.build_plan(
            normalized,
            handoff.validate_augmentation(augmentation(), normalized),
            lock_for(manifest()),
            handoff.normalize_snapshot(snapshot(source_owned={"placements": "changed-in-kicad"}), "pcb-03"),
            True,
            True,
        )
        self.assertTrue(plan["blocked"])
        self.assertEqual(plan["drift"][0]["kind"], "kicad_source_owned_drift")

    def test_corrupt_embedded_lock_is_rejected(self) -> None:
        normalized = handoff.normalize_manifest(manifest())
        lock = lock_for(manifest())
        lock["manifest"]["components"][0]["value"] = "tampered"
        with self.assertRaisesRegex(handoff.HandoffError, "checksum"):
            handoff.build_plan(
                normalized,
                handoff.validate_augmentation(augmentation(), normalized),
                lock,
                None,
                False,
                False,
            )

    def test_corrupt_embedded_snapshot_is_rejected(self) -> None:
        normalized = handoff.normalize_manifest(manifest())
        lock = lock_for(manifest())
        lock["snapshot"]["routed"] = True
        with self.assertRaisesRegex(handoff.HandoffError, "snapshot checksum"):
            handoff.build_plan(
                normalized,
                handoff.validate_augmentation(augmentation(), normalized),
                lock,
                None,
                False,
                False,
            )

    def test_augmentation_authorizes_only_changed_operation_categories(self) -> None:
        normalized = handoff.normalize_manifest(manifest())
        changed_augmentation = augmentation()
        changed_augmentation["operations"][1]["params"]["clearance_mm"] = 0.3
        plan = handoff.build_plan(
            normalized,
            handoff.validate_augmentation(changed_augmentation, normalized),
            lock_for(manifest()),
            snapshot(),
            False,
            False,
        )
        self.assertEqual(plan["authorized_kicad_owned_changes"], ["zones"])


class CliTests(unittest.TestCase):
    def write_json(self, root: Path, name: str, value: object) -> Path:
        path = root / name
        path.write_text(json.dumps(value))
        return path

    def test_accept_then_clean_plan_for_pcb03(self) -> None:
        with tempfile.TemporaryDirectory(prefix="stillair-handoff-test-") as raw_dir:
            root = Path(raw_dir)
            manifest_path = self.write_json(root, "manifest.json", manifest())
            augmentation_path = self.write_json(root, "augmentation.json", augmentation())
            snapshot_path = self.write_json(root, "snapshot.json", snapshot())
            render_entries = []
            for name in ("review.svg", "review.pdf", "review.png"):
                render = root / name
                render.write_bytes(name.encode())
                render_entries.append(
                    {
                        "path": name,
                        "sha256": hashlib.sha256(name.encode()).hexdigest(),
                    }
                )
            generated_entries = []
            for name in ("pcb-03.kicad_pcb", "pcb-03.kicad_sch"):
                generated = root / name
                generated.write_bytes(name.encode())
                generated_entries.append(
                    {
                        "path": name,
                        "sha256": hashlib.sha256(name.encode()).hexdigest(),
                    }
                )
            receipt_path = self.write_json(
                root,
                "receipt.json",
                {
                    "board_id": "pcb-03",
                    "manifest_sha256": handoff.digest(handoff.normalize_manifest(manifest())),
                    "augmentation_sha256": handoff.digest(
                        handoff.validate_augmentation(
                            augmentation(), handoff.normalize_manifest(manifest())
                        )
                    ),
                    "staged_snapshot_sha256": handoff.digest(
                        handoff.normalize_snapshot(snapshot(), "pcb-03")
                    ),
                    "versions": handoff.normalize_manifest(manifest())["versions"],
                    "tool_fingerprints": {"fake": {}},
                    "footprint_fingerprints": {"Test:U1": {}},
                    "generated_kicad": generated_entries,
                    "parity_verified": True,
                    "kicad_parse_verified": True,
                    "review_renders": render_entries,
                    "schematic_declared_differences": [],
                },
            )
            lock_path = root / "handoff.lock.json"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(handoff.main(["accept", str(manifest_path), "--augmentation", str(augmentation_path), "--snapshot", str(snapshot_path), "--receipt", str(receipt_path), "--lock", str(lock_path)]), 0)
                self.assertEqual(handoff.main(["plan", str(manifest_path), "--augmentation", str(augmentation_path), "--snapshot", str(snapshot_path), "--lock", str(lock_path)]), 0)
            self.assertTrue(lock_path.is_file())

    def test_accept_rejects_staged_kicad_mutation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="stillair-accept-hash-") as raw_dir:
            root = Path(raw_dir)
            staged = root / "board.kicad_pcb"
            staged.write_text("validated")
            receipt = {
                "generated_kicad": [
                    {
                        "path": staged.name,
                        "sha256": hashlib.sha256(b"validated").hexdigest(),
                    },
                    {
                        "path": "board.kicad_sch",
                        "sha256": hashlib.sha256(b"schematic").hexdigest(),
                    },
                ]
            }
            (root / "board.kicad_sch").write_text("schematic")
            receipt_path = self.write_json(root, "receipt.json", receipt)
            handoff.verify_generated_kicad(receipt, receipt_path)
            staged.write_text("mutated after stage")
            with self.assertRaisesRegex(handoff.HandoffError, "changed after validation"):
                handoff.verify_generated_kicad(receipt, receipt_path)

    def test_strict_schematic_cleanup_gate_requires_fields_and_clean_erc(self) -> None:
        with tempfile.TemporaryDirectory(prefix="stillair-cleanup-gate-") as raw_dir:
            root = Path(raw_dir)
            manifest_path = self.write_json(root, "manifest.json", manifest())
            augmentation_path = self.write_json(root, "augmentation.json", augmentation())
            schematic_path = root / "board.kicad_sch"
            schematic_path.write_text("(kicad_sch)")
            fake_cli = root / "kicad-cli"
            fake_cli.write_text("#!/bin/sh\nexit 0\n")
            fake_cli.chmod(0o755)
            generated_xml = schematic_netlist_xml()
            generated_erc = kicad_report()

            def fake_run(command: list[str], cwd: Path, env: dict[str, str]) -> dict:
                output = Path(command[command.index("--output") + 1])
                if "netlist" in command:
                    output.write_text(generated_xml)
                else:
                    output.write_text(json.dumps(generated_erc))
                return {"argv": command, "returncode": 0, "stderr": "", "stdout": ""}

            def run_gate() -> int:
                with contextlib.redirect_stdout(io.StringIO()), mock.patch.object(
                    handoff, "run_staged_command", side_effect=fake_run
                ):
                    return handoff.main(
                        [
                            "verify-schematic-cleanup", str(manifest_path),
                            "--augmentation", str(augmentation_path),
                            "--schematic", str(schematic_path),
                            "--kicad-cli", str(fake_cli),
                        ]
                    )

            self.assertEqual(run_gate(), 0)
            generated_xml = schematic_netlist_xml().replace("MPN-U1", "wrong")
            self.assertEqual(run_gate(), 1)
            generated_xml = schematic_netlist_xml()
            generated_erc = kicad_report([{"type": "endpoint_off_grid"}])
            self.assertEqual(run_gate(), 1)
            generated_erc = {**kicad_report(), "included_severities": ["error"]}
            self.assertEqual(run_gate(), 1)
            generated_erc = {
                **kicad_report(),
                "ignored_checks": [{"key": "hidden_failure"}],
            }
            self.assertEqual(run_gate(), 1)

    def test_initial_export_is_task_staged_and_production_is_unchanged(self) -> None:
        with tempfile.TemporaryDirectory(prefix="stillair-handoff-test-") as raw_dir:
            root = Path(raw_dir)
            source = root / "source"
            production = root / "production"
            stages = root / "stages"
            source.mkdir()
            production.mkdir()
            production_board = production / "pcb-03.kicad_pcb"
            production_board.write_text("production-sentinel")
            manifest_path = self.write_json(source, "manifest.json", manifest())
            helper = source / "fake_export.py"
            helper.write_text(
                "import os, pathlib, sys\n"
                "stage=pathlib.Path(os.environ['STILLAIR_HANDOFF_STAGE'])\n"
                "(stage/'build-ran').write_text(sys.argv[1])\n"
                "if sys.argv[1]=='export':\n"
                " (stage/'pcb-03.kicad_pcb').write_text('staged board')\n"
                " (stage/'pcb-03.kicad_sch').write_text('(kicad_sch)')\n"
            )
            command_build = json.dumps([sys.executable, str(helper), "build"])
            command_export = json.dumps([sys.executable, str(helper), "export"])
            augmentation_path = self.write_json(source, "augmentation.json", augmentation())
            footprint_root = root / "footprints"
            footprint_root.mkdir()
            for item in handoff.normalize_manifest(manifest())["components"]:
                library, name = item["footprint"]["kicad"].split(":", 1)
                library_path = footprint_root / f"{library}.pretty"
                library_path.mkdir(exist_ok=True)
                (library_path / f"{name}.kicad_mod").write_text("footprint")
            converter = source / "node_modules" / "circuit-json-to-kicad"
            (converter / "dist").mkdir(parents=True)
            (converter / "package.json").write_text(json.dumps({"version": "0.0.test"}))
            (converter / "dist" / "index.js").write_text("export {}")
            fake_tool = root / "fake-kicad-tool"
            fake_tool.write_text("#!/bin/sh\nexit 0\n")
            fake_tool.chmod(0o755)

            real_run = handoff.run_staged_command

            def fake_run(command: list[str], cwd: Path, env: dict[str, str]) -> dict:
                if command[0] == sys.executable:
                    return real_run(command, cwd, env)
                if "augment-staged" in command:
                    return {"argv": command, "returncode": 0, "stderr": "", "stdout": ""}
                if "snapshot-kicad" in command:
                    output = Path(command[command.index("--output") + 1])
                    output.write_text(json.dumps(snapshot()))
                    return {"argv": command, "returncode": 0, "stderr": "", "stdout": ""}
                if "drc" in command or "erc" in command:
                    output = Path(command[command.index("--output") + 1])
                    output.write_text(json.dumps(kicad_report()))
                    return {"argv": command, "returncode": 0, "stderr": "", "stdout": ""}
                if "netlist" in command:
                    output = Path(command[command.index("--output") + 1])
                    output.write_text(schematic_netlist_xml())
                    return {"argv": command, "returncode": 0, "stderr": "", "stdout": ""}
                if "svg" in command:
                    output = Path(command[command.index("--output") + 1])
                    output.mkdir(parents=True)
                    (output / "pcb-03.svg").write_text("<svg/>")
                    return {"argv": command, "returncode": 0, "stderr": "", "stdout": ""}
                if "pdf" in command or "render" in command:
                    output = Path(command[command.index("--output") + 1])
                    output.parent.mkdir(parents=True, exist_ok=True)
                    output.write_bytes(b"render")
                    return {"argv": command, "returncode": 0, "stderr": "", "stdout": ""}
                raise AssertionError(f"unexpected command: {command}")

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout), mock.patch.object(
                handoff, "run_staged_command", side_effect=fake_run
            ), mock.patch.object(
                handoff,
                "executable_fingerprint",
                return_value={"path": "fake", "returncode": 0, "sha256": "0" * 64, "version": "fake"},
            ), mock.patch.object(
                handoff, "resolve_executable", return_value=fake_tool
            ):
                result = handoff.main([
                    "stage", str(manifest_path),
                    "--augmentation", str(augmentation_path),
                    "--build-command", command_build,
                    "--export-command", command_export,
                    "--production-dir", str(production),
                    "--kicad-cli", str(fake_tool),
                    "--kicad-python", str(fake_tool),
                    "--footprint-root", str(footprint_root),
                    "--source-dir", str(source),
                    "--staging-root", str(stages),
                ])
            self.assertEqual(result, 0)
            stage = Path(stdout.getvalue().strip().splitlines()[-1])
            self.assertTrue((stage / "pcb-03.kicad_pcb").is_file())
            self.assertTrue((stage / "handoff-receipt.json").is_file())
            self.assertEqual(production_board.read_text(), "production-sentinel")

            with contextlib.redirect_stdout(io.StringIO()):
                overlap = handoff.main([
                    "stage", str(manifest_path),
                    "--augmentation", str(augmentation_path),
                    "--build-command", command_build,
                    "--export-command", command_export,
                    "--production-dir", str(production),
                    "--staging-root", str(production),
                ])
            self.assertEqual(overlap, 1)

    def test_preservation_check_detects_changed_routes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="stillair-handoff-test-") as raw_dir:
            root = Path(raw_dir)
            normalized = handoff.normalize_manifest(manifest())
            augment = handoff.validate_augmentation(augmentation(), normalized)
            plan = handoff.build_plan(
                normalized, augment, lock_for(manifest()), snapshot(), False, False
            )
            plan_path = self.write_json(root, "plan.json", plan)
            before_path = self.write_json(root, "before.json", snapshot(routed=True))
            changed = copy.deepcopy(snapshot(routed=True))
            changed["kicad_owned"]["tracks"] = "different"
            after_path = self.write_json(root, "after.json", changed)
            with contextlib.redirect_stdout(io.StringIO()):
                result = handoff.main(["verify-preservation", "--plan", str(plan_path), "--before-snapshot", str(before_path), "--after-snapshot", str(after_path)])
            self.assertEqual(result, 1)

    def test_preservation_requires_target_source_state(self) -> None:
        with tempfile.TemporaryDirectory(prefix="stillair-handoff-test-") as raw_dir:
            root = Path(raw_dir)
            changed = manifest()
            changed["components"][0]["placement"]["x_mm"] = 6
            normalized = handoff.normalize_manifest(changed)
            augment = handoff.validate_augmentation(augmentation(), normalized)
            plan = handoff.build_plan(
                normalized, augment, lock_for(manifest()), snapshot(), False, False
            )
            plan_path = self.write_json(root, "plan.json", plan)
            before_path = self.write_json(root, "before.json", snapshot())
            after_path = self.write_json(root, "after.json", snapshot())
            with contextlib.redirect_stdout(io.StringIO()):
                result = handoff.main([
                    "verify-preservation", "--plan", str(plan_path),
                    "--before-snapshot", str(before_path),
                    "--after-snapshot", str(after_path),
                ])
            self.assertEqual(result, 1)

    def test_preservation_requires_planned_symbol_change(self) -> None:
        with tempfile.TemporaryDirectory(prefix="stillair-handoff-test-") as raw_dir:
            root = Path(raw_dir)
            changed = manifest()
            changed["components"][0]["symbol"] = "test:Replacement"
            normalized = handoff.normalize_manifest(changed)
            augment = handoff.validate_augmentation(augmentation(), normalized)
            plan = handoff.build_plan(
                normalized, augment, lock_for(manifest()), snapshot(), True, True
            )
            paths = {
                name: self.write_json(root, f"{name}.json", value)
                for name, value in {
                    "plan": plan,
                    "before": snapshot(),
                    "after": snapshot(),
                }.items()
            }
            with contextlib.redirect_stdout(io.StringIO()):
                result = handoff.main([
                    "verify-preservation", "--plan", str(paths["plan"]),
                    "--before-snapshot", str(paths["before"]),
                    "--after-snapshot", str(paths["after"]),
                ])
            self.assertEqual(result, 1)

    def test_refuses_lock_path_with_protected_suffix(self) -> None:
        with tempfile.TemporaryDirectory(prefix="stillair-handoff-test-") as raw_dir:
            path = Path(raw_dir) / "not-a-lock.kicad_pcb"
            with self.assertRaisesRegex(handoff.HandoffError, "protected"):
                handoff.atomic_write_json(path, {})


if __name__ == "__main__":
    unittest.main()
