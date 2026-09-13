"""Host-only tests for native transaction guards and publication failure paths.

The tiny byte fixtures are deliberately not KiCad object graphs; no native API
loads them. Real native serialization is exercised by the integration suite.
"""
import copy
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import uuid

import kicad_native as native


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="kicad-native-unit-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.board = self.root / "fixture.kicad_pcb"
        self.board.write_bytes(b"mock board input; never parsed")
        self.board.with_suffix(".kicad_pro").write_bytes(b"mock project input; never parsed")
        self.uid = str(uuid.uuid4())
        self.operation = {"op": "field", "uuid": self.uid, "name": "MPN", "from": "A", "to": "B"}
        self.plan = {"schema_version": 1, "before_files": native.project_files(self.board),
                     "operations": [self.operation]}

    def test_accepts_complete_hash_bound_plan(self):
        self.assertEqual(native.validate_transaction(self.board, self.plan), self.board)

    def test_rejects_stale_additional_dependency(self):
        dependency = self.root / "declaration.json"
        dependency.write_text("before")
        self.plan["before_files"][dependency.name] = native.sha256(dependency)
        dependency.write_text("after")
        with self.assertRaisesRegex(native.NativeError, "Stale"):
            native.validate_transaction(self.board, self.plan)

    def test_requires_adjacent_rule_and_library_hashes(self):
        (self.root / "fixture.kicad_dru").write_bytes(b"mock rules; never parsed")
        with self.assertRaisesRegex(native.NativeError, "omits"):
            native.validate_transaction(self.board, self.plan)

    def test_child_schematic_is_required_and_outside_hierarchy_rejected(self):
        root = self.board.with_suffix(".kicad_sch")
        root.write_text('(property "Sheetfile" "child.kicad_sch")')
        child = self.root / "child.kicad_sch"
        child.write_bytes(b"mock child sheet; never parsed by KiCad")
        hashes = native.project_files(self.board)
        self.assertIn(child.name, hashes)
        self.plan["before_files"] = hashes
        native.validate_transaction(self.board, self.plan)
        del self.plan["before_files"][child.name]
        with self.assertRaisesRegex(native.NativeError, "omits"):
            native.validate_transaction(self.board, self.plan)
        root.write_text('(property "Sheetfile" "../escape.kicad_sch")')
        with self.assertRaisesRegex(native.NativeError, "escapes"):
            native.project_files(self.board)

    def test_unrelated_project_settings_cannot_change(self):
        before = {"board": {"design_settings": {"drc_exclusions": ["specific"]}},
                  "net_settings": {"classes": [{"name": "Default", "track_width": .25}]}}
        after = copy.deepcopy(before)
        after["board"]["design_settings"]["drc_exclusions"] = []
        with self.assertRaisesRegex(native.NativeError, "undeclared project"):
            native._assert_project_json(before, after, [self.operation])

    def test_all_editor_lock_variants_reject(self):
        for suffix in (".kicad_pro", ".kicad_pcb", ".kicad_sch"):
            lock = self.root / ("~fixture" + suffix + ".lck")
            with self.subTest(suffix=suffix):
                lock.touch()
                with self.assertRaisesRegex(native.NativeError, "editor lock"):
                    native.validate_transaction(self.board, self.plan)
                lock.unlink()

    def test_unknown_operation_and_fields_fail_closed(self):
        for op in ({"op": "stackup"}, {**self.operation, "guess": True}):
            with self.subTest(op=op):
                self.plan["operations"] = [op]
                with self.assertRaises(native.NativeError):
                    native.validate_transaction(self.board, self.plan)

    def test_duplicate_field_and_group_selector_rejected(self):
        self.plan["operations"] = [self.operation, copy.deepcopy(self.operation)]
        with self.assertRaisesRegex(native.NativeError, "Duplicate selector"):
            native.validate_transaction(self.board, self.plan)
        move = {"op": "footprint_move", "uuid": str(uuid.uuid4()),
                "from": {"position_mm": [0, 0], "rotation_deg": 0},
                "to": {"position_mm": [1, 1], "rotation_deg": 0}, "associated_uuids": [self.uid]}
        second = {**move, "uuid": str(uuid.uuid4())}
        self.plan["operations"] = [move, second]
        with self.assertRaisesRegex(native.NativeError, "Duplicate selector"):
            native.validate_transaction(self.board, self.plan)

    def test_unsafe_paths_symlinks_and_digest_rejected(self):
        for path in ("../other.kicad_pcb", "/other.kicad_pcb", "./fixture.kicad_pcb"):
            with self.subTest(path=path):
                plan = copy.deepcopy(self.plan)
                plan["before_files"][path] = "a" * 64
                with self.assertRaises(native.NativeError):
                    native.validate_transaction(self.board, plan)
        linked = self.root / "linked.kicad_pcb"
        linked.symlink_to(self.board)
        with self.assertRaisesRegex(native.NativeError, "Symlinked"):
            native.project_files(linked)
        self.plan["before_files"][self.board.name] = "g" * 64
        with self.assertRaisesRegex(native.NativeError, "Invalid SHA256"):
            native.validate_transaction(self.board, self.plan)

    def test_nan_and_boolean_pose_rejected(self):
        for value in (float("nan"), float("inf"), True):
            self.plan["operations"] = [{"op": "footprint_move", "uuid": self.uid,
                "from": {"position_mm": [0, 0], "rotation_deg": 0},
                "to": {"position_mm": [value, 1], "rotation_deg": 0}, "associated_uuids": []}]
            with self.assertRaisesRegex(native.NativeError, "finite number"):
                native.validate_transaction(self.board, self.plan)

    def test_noncanonical_and_nil_uuid_rejected(self):
        for uid in (self.uid.upper(), "00000000-0000-0000-0000-000000000000", "not-a-uuid"):
            self.operation["uuid"] = uid
            with self.assertRaisesRegex(native.NativeError, "UUID"):
                native.validate_transaction(self.board, self.plan)

    def test_transaction_lock_rejects_parallel_tool_writer(self):
        with native._transaction_lock(self.board):
            with self.assertRaisesRegex(native.NativeError, "transaction lock"):
                with native._transaction_lock(self.board):
                    self.fail("second writer acquired lock")
        self.assertFalse((self.root / ".fixture.native-transaction.lock").exists())

    def test_receipt_existing_path_and_wrong_suffix_preflight(self):
        for path in (self.board, self.root / "output.txt"):
            with self.assertRaisesRegex(native.NativeError, "output_receipt"):
                native.apply_transaction(self.board, self.plan, path)


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="kicad-publication-unit-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.candidate = self.root / "candidate"
        self.recovery = self.root / "before"
        self.source = self.root / "source"
        for path in (self.candidate, self.recovery, self.source):
            path.mkdir()
        self.before, self.after = {}, {}
        for name in ("fixture.kicad_pcb", "fixture.kicad_pro"):
            for path in (self.recovery, self.source):
                (path / name).write_bytes(b"old mock")
            (self.candidate / name).write_bytes(b"new mock")
            self.before[name] = native.sha256(self.source / name)
            self.after[name] = native.sha256(self.candidate / name)
        self.board = self.source / "fixture.kicad_pcb"

    def publish(self):
        return native._publish(self.board, self.candidate, self.before, self.after, self.recovery)

    def test_success_replaces_only_changed_files(self):
        self.assertEqual(set(self.publish()), set(self.before))
        self.assertEqual(native.project_files(self.board), self.after)
        self.assertEqual(sorted(p.name for p in self.source.iterdir()), sorted(self.before))

    def test_second_replace_failure_rolls_back_first(self):
        real_replace = native.os.replace
        count = 0
        def fail_second(source, target):
            nonlocal count
            count += 1
            if count == 2:
                raise OSError("injected disk failure")
            return real_replace(source, target)
        with patch.object(native.os, "replace", side_effect=fail_second):
            with self.assertRaisesRegex(OSError, "disk failure"):
                self.publish()
        self.assertEqual(native.project_files(self.board), self.before)

    def test_rollback_preserves_external_edit_and_exposes_recovery(self):
        real_replace = native.os.replace
        count = 0
        def concurrent_edit(source, target):
            nonlocal count
            count += 1
            if count == 2:
                self.board.write_bytes(b"concurrent mock edit")
                raise OSError("injected disk failure")
            return real_replace(source, target)
        with patch.object(native.os, "replace", side_effect=concurrent_edit):
            with self.assertRaisesRegex(native.NativeError, "recovery retained"):
                self.publish()
        self.assertEqual(self.board.read_bytes(), b"concurrent mock edit")

    def test_new_native_dependency_prevents_publication(self):
        (self.source / "fixture.kicad_dru").write_bytes(b"new mock dependency; never parsed")
        with self.assertRaisesRegex(native.NativeError, "inventory changed"):
            self.publish()
        self.assertEqual(native.sha256(self.board), self.before[self.board.name])

    def test_stale_before_publication_never_replaces_another_file(self):
        self.board.write_bytes(b"new external edit")
        with self.assertRaisesRegex(native.NativeError, "Source changed"):
            self.publish()
        self.assertEqual(native.sha256(self.board.with_suffix(".kicad_pro")), self.before["fixture.kicad_pro"])


if __name__ == "__main__":
    unittest.main()
