"""Failure tests for evidence freshness and acceptance prerequisites; no KiCad needed."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pcb_workflow as workflow


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pcb-workflow-tests-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repo"
        self.root.mkdir()
        self.run = Path(self.temp.name) / "run"
        self.write("pcb/native/board.kicad_pcb", "board")
        self.write("pcb/native/board.kicad_sch", "schematic")
        self.write("pcb/native/board.kicad_pro", "{}")
        self.write("pcb/source/board.tsx", "authoritative source")
        self.write("pcb/manifest.json", "{}")
        self.write("pcb/augmentation.json", "{}")
        self.write("pcb/lock.json", "{}")
        self.write("pcb/profiles.json", "{}")
        self.write("docs/contract.md", "dimensions")
        self.write("docs/target.png", "visual")
        self.config = {"schema_version": 1, "readiness_profiles": "pcb/profiles.json",
            "native_python": ["python3"], "boards": {"sample": {
                "native_dir": "pcb/native", "basename": "board", "manifest": "pcb/manifest.json",
                "augmentation": "pcb/augmentation.json", "lock": "pcb/lock.json",
                "source_cwd": "pcb", "source_roots": ["pcb/source"],
                "build": ["builder"], "source_checks": [["check", "electrical"]],
                "contract": ["docs/contract.md"], "visual_targets": ["docs/target.png"]}}}
        self.write("pcb/workflow.json", json.dumps(self.config))
        self.flow = workflow.Workflow(self.root, "pcb/workflow.json", "sample")

    def write(self, path, text):
        dest = self.root / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text)
        return dest

    def validated(self):
        evidence = self.flow.evidence(self.run)
        render = self.run / "renders/board.svg"
        render.parent.mkdir()
        render.write_text("<svg/>")
        snapshot = evidence.put({"board_id": "sample"})
        checks = {
            "source": {"passed": True, "commands": [evidence.put({"argv": c, "returncode": 0})
                for c in [self.flow.spec["build"]] + self.flow.spec["source_checks"]]},
            "strict_erc": {"passed": True},
            "source_parity": {"passed": True, "snapshot": snapshot},
            "drc": {"passed": True},
            "preparation": {"passed": True, "findings": [], "checks": [{"id": "geometry", "passed": True}]},
            "renders": {"passed": True, "files": {"renders/board.svg": workflow.sha(render)}}}
        report = {"schema_version": 1, "board": "sample", "passed": True,
                  "native_files": workflow.native_hashes(self.flow.native),
                  "inputs": self.flow.fingerprints(), "checks": {k: evidence.put(v) for k,v in checks.items()},
                  "snapshot": snapshot, "manifest": evidence.put({}), "augmentation": evidence.put({})}
        data = {"schema_version": 1, "board": "sample", "stage": "validated", "validation": evidence.put(report)}
        evidence.write_index(data)
        return evidence, data, report

    def test_content_objects_deduplicate_and_detect_corruption(self):
        evidence = self.flow.evidence(self.run)
        key = evidence.put({"b": 2, "a": 1})
        self.assertEqual(key, evidence.put({"a": 1, "b": 2}))
        (evidence.objects / (key + ".json")).write_text("{}")
        with self.assertRaisesRegex(workflow.WorkflowError, "modified"):
            evidence.get(key)

    def test_evidence_traversal_is_rejected(self):
        evidence = self.flow.evidence(self.run)
        with self.assertRaises(workflow.WorkflowError):
            evidence.get("../run")
        for path in (self.root, self.flow.native / "evidence", self.root / "pcb/source/evidence"):
            with self.subTest(path=path), self.assertRaises(workflow.WorkflowError):
                self.flow.evidence(path)

    def test_missing_source_root_is_not_an_empty_success(self):
        self.flow.spec["source_roots"] = ["absent"]
        with self.assertRaisesRegex(workflow.WorkflowError, "missing"):
            self.flow.fingerprints()

    def test_read_only_checker_cannot_mutate_native(self):
        evidence = self.flow.evidence(self.run)
        command = [sys.executable, "-c", "from pathlib import Path; Path('pcb/native/board.kicad_pcb').write_text('changed')"]
        with self.assertRaisesRegex(workflow.WorkflowError, "changed native"):
            self.flow.command(command, evidence, "bad checker")

    def test_failed_command_records_actual_failure(self):
        evidence = self.flow.evidence(self.run)
        with self.assertRaisesRegex(workflow.WorkflowError, "failed"):
            self.flow.command([sys.executable, "-c", "raise SystemExit(3)"], evidence, "checker")
        record = json.loads(next(evidence.objects.glob("*.json")).read_text())
        self.assertEqual(record["returncode"], 3)

    def test_current_report_is_usable(self):
        evidence, _, _ = self.validated()
        self.flow.checked_validation(evidence)

    def test_source_native_profile_and_tool_changes_invalidate(self):
        evidence, _, _ = self.validated()
        for path in ("pcb/source/board.tsx", "pcb/native/board.kicad_pcb", "pcb/profiles.json", "pcb/tools/new_checker.py"):
            dest = self.root / path
            old = dest.read_text() if dest.exists() else None
            self.write(path, "changed")
            with self.subTest(path=path), self.assertRaisesRegex(workflow.WorkflowError, "stale"):
                self.flow.checked_validation(evidence)
            if old is None:
                dest.unlink()
            else:
                dest.write_text(old)

    def test_render_mutation_invalidates_review(self):
        evidence, _, _ = self.validated()
        (self.run / "renders/board.svg").write_text("different")
        with self.assertRaisesRegex(workflow.WorkflowError, "render"):
            self.flow.checked_validation(evidence)

    def test_passed_boolean_does_not_replace_gate_set(self):
        evidence, data, report = self.validated()
        del report["checks"]["strict_erc"]
        data["validation"] = evidence.put(report)
        evidence.write_index(data)
        with self.assertRaisesRegex(workflow.WorkflowError, "required checks"):
            self.flow.checked_validation(evidence)

    def test_wrong_source_command_set_rejected(self):
        evidence, data, report = self.validated()
        report["checks"]["source"] = evidence.put({"passed": True, "commands": []})
        data["validation"] = evidence.put(report)
        evidence.write_index(data)
        with self.assertRaisesRegex(workflow.WorkflowError, "command set"):
            self.flow.checked_validation(evidence)

    def test_failed_revalidation_cannot_reuse_old_success(self):
        evidence, _, _ = self.validated()
        with patch.object(self.flow, "command", side_effect=workflow.WorkflowError("failed")):
            with self.assertRaises(workflow.WorkflowError):
                self.flow.validate(self.run)
        data = evidence.index()
        self.assertEqual(data["stage"], "failed")
        self.assertNotIn("validation", data)
        with self.assertRaisesRegex(workflow.WorkflowError, "complete validation"):
            self.flow.checked_validation(evidence)

    def test_source_edit_during_build_is_rejected(self):
        evidence = self.flow.evidence(self.run)
        def build(*_):
            self.write("pcb/source/board.tsx", "concurrent edit")
            return "command"
        with patch.object(self.flow, "command", side_effect=build):
            with self.assertRaisesRegex(workflow.WorkflowError, "during source build"):
                self.flow.build_source(evidence)

    def test_source_edit_during_acceptance_preserves_authoritative_lock(self):
        evidence, data, _ = self.validated()
        original = self.flow.path("lock").read_bytes()
        review = {"validation": data["validation"], "unresolved_findings": []}
        data.update(stage="reviewed", review=evidence.put(review), plan=evidence.put({}),
                    before_snapshot=evidence.put({}), baseline_lock_sha256=workflow.sha(self.flow.path("lock")))
        evidence.write_index(data)
        def accept_command(command, *_):
            candidate = Path(command[command.index("--lock") + 1])
            candidate.write_text('{"new": "lock"}')
            Path(command[command.index("--receipt") + 1]).write_text('{}')
            self.write("pcb/source/board.tsx", "concurrent edit")
        with patch.object(self.flow, "command", side_effect=accept_command):
            with self.assertRaisesRegex(workflow.WorkflowError, "during acceptance"):
                self.flow.accept(self.run)
        self.assertEqual(self.flow.path("lock").read_bytes(), original)
        self.assertEqual(evidence.index()["stage"], "failed")

    def test_known_checker_limitation_cannot_swallow_new_output(self):
        import hashlib
        evidence = self.flow.evidence(self.run)
        command = [sys.executable, "-c", "print('known limitation'); raise SystemExit(1)"]
        limitation = {"argv": command, "returncode": 1,
            "stdout_sha256": hashlib.sha256(b"known limitation\n").hexdigest(),
            "stderr_sha256": hashlib.sha256(b"").hexdigest(), "reason": "fixture",
            "countercheck": "native_drc_and_preparation"}
        self.flow.command(command, evidence, "fixture", expected_limitation=limitation)
        limitation["stdout_sha256"] = "0" * 64
        with self.assertRaisesRegex(workflow.WorkflowError, "failed"):
            self.flow.command(command, evidence, "fixture", expected_limitation=limitation)

    def test_accept_requires_baseline_and_review(self):
        self.validated()
        with self.assertRaisesRegex(workflow.WorkflowError, "baseline"):
            self.flow.accept(self.run)

    def test_review_binds_current_validation_and_all_scopes(self):
        evidence, data, _ = self.validated()
        review = {"reviewer": "test reviewer", "validation": data["validation"],
                  "scopes": {k: "Inspected fixture evidence" for k in workflow.REVIEW_SCOPES}, "unresolved_findings": []}
        path = self.write("review.json", json.dumps(review))
        self.flow.review(self.run, path)
        self.assertEqual(evidence.index()["stage"], "reviewed")
        review["validation"] = "0" * 64
        path.write_text(json.dumps(review))
        with self.assertRaisesRegex(workflow.WorkflowError, "bind"):
            self.flow.review(self.run, path)

    def test_accepted_status_detects_later_native_edits(self):
        evidence, data, _ = self.validated()
        self.write("pcb/lock.json", "new lock")
        data.update(stage="accepted", accepted_lock_sha256=workflow.sha(self.flow.path("lock")),
                    acceptance=evidence.put({}), review=evidence.put({}))
        evidence.write_index(data)
        self.flow.status(self.run)
        self.write("pcb/native/board.kicad_pcb", "later routing")
        with self.assertRaisesRegex(workflow.WorkflowError, "stale"):
            self.flow.status(self.run)

    def test_wrong_board_run_rejected(self):
        with self.assertRaises(workflow.WorkflowError):
            self.flow.assert_run({"schema_version": 1, "board": "other"})


if __name__ == "__main__":
    unittest.main()
