#!/usr/bin/env python3
"""One checked PCB change lifecycle; native application lives in kicad_native.

All commands are argv arrays, never shell fragments. Validation is read-only for
native projects. Evidence blobs are addressed by content; run.json is the small
index. Acceptance rechecks current inputs and never trusts an isolated passed flag.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import tscircuit_handoff as handoff
import kicad_native

VERSION = 1
CHECKS = {"source", "strict_erc", "source_parity", "drc", "preparation", "renders"}
REVIEW_SCOPES = {"visual_contract", "schematics", "placement_and_copper", "assembly_and_process"}
NATIVE_SUFFIXES = {".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_prl", ".kicad_dru", ".kicad_sym", ".kicad_mod"}


class WorkflowError(ValueError):
    pass


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def relative_path(root, value):
    if not isinstance(value, str) or not value or Path(value).is_absolute() or ".." in Path(value).parts:
        raise WorkflowError(f"Expected repository-relative path: {value!r}")
    result = root / value
    if not result.resolve().is_relative_to(root.resolve()):
        raise WorkflowError(f"Path escapes repository: {value}")
    return result


def argv(value):
    if not isinstance(value, list) or not value or not all(isinstance(x, str) and x for x in value):
        raise WorkflowError("Commands must be nonempty argv arrays")
    return value


def native_hashes(native):
    result = {}
    for path in sorted(native.rglob("*")):
        rel = path.relative_to(native)
        if any(x in {"evidence", "review-renders", ".history"} or x.endswith("-backups") for x in rel.parts):
            continue
        if path.suffix in NATIVE_SUFFIXES or path.name in {"fp-lib-table", "sym-lib-table"}:
            if path.is_symlink() or not path.is_file():
                raise WorkflowError(f"Native input must be a regular file: {path}")
            result[str(rel)] = sha(path)
    if not result:
        raise WorkflowError("Native project is empty")
    return result


class Evidence:
    def __init__(self, directory):
        self.path = Path(directory).resolve()
        self.path.mkdir(parents=True, exist_ok=True)
        self.objects = self.path / "objects"
        self.objects.mkdir(exist_ok=True)
        if self.objects.is_symlink():
            raise WorkflowError("Evidence objects cannot be a symlink")

    def put(self, value):
        data = handoff.canonical_json(value).encode()
        digest = hashlib.sha256(data).hexdigest()
        target = self.objects / f"{digest}.json"
        if target.exists():
            if target.is_symlink() or target.read_bytes() != data:
                raise WorkflowError("Evidence object checksum collision or corruption")
        else:
            with target.open("xb") as handle:
                handle.write(data)
        return digest

    def get(self, digest):
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise WorkflowError("Invalid evidence object identity")
        path = self.objects / f"{digest}.json"
        if path.is_symlink() or not path.is_file() or sha(path) != digest:
            raise WorkflowError(f"Missing or modified evidence object: {digest}")
        return json.loads(path.read_text())

    def materialize(self, digest, name):
        value = self.get(digest)
        target = self.path / name
        handoff.atomic_write_json(target, value)
        return target

    def write_index(self, data):
        handoff.atomic_write_json(self.path / "run.json", data)

    def index(self):
        return handoff.read_json(self.path / "run.json")


class Workflow:
    def __init__(self, root, config, board):
        self.root = Path(root).resolve()
        self.config_path = relative_path(self.root, config)
        self.config = handoff.read_json(self.config_path)
        if self.config.get("schema_version") != VERSION or not isinstance(self.config.get("boards"), dict):
            raise WorkflowError("Unsupported workflow configuration")
        if board not in self.config["boards"]:
            raise WorkflowError(f"Board has no workflow profile: {board}")
        self.name = board
        self.spec = self.config["boards"][board]
        for key in ("native_dir", "basename", "manifest", "augmentation", "lock", "source_cwd"):
            if not isinstance(self.spec.get(key), str) or not self.spec[key]:
                raise WorkflowError(f"Missing board profile field: {key}")
        if Path(self.spec["basename"]).name != self.spec["basename"]:
            raise WorkflowError("Invalid native basename")
        for key in ("source_roots", "source_checks", "contract", "visual_targets"):
            if not isinstance(self.spec.get(key), list) or not self.spec[key]:
                raise WorkflowError(f"Missing nonempty profile list: {key}")
        argv(self.spec["build"])
        for command in self.spec["source_checks"]:
            argv(command)
        self.python = argv(self.config["native_python"])
        self.native = self.path("native_dir")
        self.board = self.native / (self.spec["basename"] + ".kicad_pcb")
        self.schematic = self.board.with_suffix(".kicad_sch")
        self.profiles = relative_path(self.root, self.config["readiness_profiles"])
        for path in (self.board, self.schematic, self.board.with_suffix(".kicad_pro"), self.path("lock")):
            if not path.is_file():
                raise WorkflowError(f"Required project input missing: {path}")

    def path(self, key):
        return relative_path(self.root, self.spec[key])

    def evidence(self, directory, *, new=False):
        path = Path(directory).resolve()
        if path == self.root or path.is_relative_to(self.native) or self.native.is_relative_to(path):
            raise WorkflowError("Evidence must be outside the native project and its ancestors")
        for source in self.spec["source_roots"]:
            if path.is_relative_to(relative_path(self.root, source).resolve()):
                raise WorkflowError("Evidence cannot be written into authoritative source")
        if new and path.exists() and any(path.iterdir()):
            raise WorkflowError("Begin requires a new empty evidence directory")
        return Evidence(path)

    def fingerprints(self, *, include_lock=True, include_manifest=True):
        paths = {self.config_path, self.profiles, self.path("augmentation")}
        if include_manifest:
            paths.add(self.path("manifest"))
        if include_lock:
            paths.add(self.path("lock"))
        for name in self.spec["contract"] + self.spec["visual_targets"]:
            path = relative_path(self.root, name)
            if not path.is_file() or path.stat().st_size == 0:
                raise WorkflowError(f"Missing design contract or visual reference: {name}")
            paths.add(path)
        for source in self.spec["source_roots"]:
            path = relative_path(self.root, source)
            if not path.exists():
                raise WorkflowError(f"Source input missing: {source}")
            candidates = [path] if path.is_file() else path.rglob("*")
            for item in candidates:
                if not item.is_file() or "evidence" in item.relative_to(self.root).parts:
                    continue
                if item.name == "handoff.lock.json":
                    continue
                paths.add(item)
        # Bind executable checker code too, including project-specific hooks.
        for item in (self.root / "pcb/tools").glob("*.py"):
            paths.add(item)
        for item in (self.root / "pcb/tools").glob("*.json"):
            paths.add(item)
        for item in (self.root / "pcb/tools").glob("*.sh"):
            paths.add(item)
        result = {str(p.relative_to(self.root)): sha(p) for p in sorted(paths)}
        # --root may point at a copied project; bind the running orchestrator as
        # well as the configured project's child tools.
        for path in (Path(__file__), Path(handoff.__file__), Path(kicad_native.__file__)):
            result["@runtime/" + path.name] = sha(path)
        return result

    def build_source(self, evidence):
        before = self.fingerprints(include_manifest=False)
        command = self.command(self.spec["build"], evidence, "build source manifest", self.path("source_cwd"))
        if before != self.fingerprints(include_manifest=False):
            raise WorkflowError("Authoritative inputs changed during source build")
        return command

    def command(self, command, evidence, label, cwd=None, expected_limitation=None):
        before = native_hashes(self.native)
        try:
            completed = subprocess.run(argv(command), cwd=cwd or self.root, capture_output=True, text=True)
        except OSError as exc:
            raise WorkflowError(f"Could not run {label}: {exc}") from exc
        record = {"argv": command, "returncode": completed.returncode,
                  "stdout": completed.stdout, "stderr": completed.stderr}
        if expected_limitation is not None and completed.returncode:
            identity = {"argv": command, "returncode": completed.returncode,
                        "stdout_sha256": hashlib.sha256(completed.stdout.encode()).hexdigest(),
                        "stderr_sha256": hashlib.sha256(completed.stderr.encode()).hexdigest()}
            if (all(expected_limitation.get(k) == v for k, v in identity.items())
                    and expected_limitation.get("reason") and expected_limitation.get("countercheck") == "native_drc_and_preparation"):
                record["reviewed_limitation"] = expected_limitation
        reference = evidence.put(record)
        if native_hashes(self.native) != before:
            raise WorkflowError(f"Read-only command changed native project: {label}")
        if completed.returncode and "reviewed_limitation" not in record:
            raise WorkflowError(f"{label} failed; command evidence {reference}: {(completed.stderr or completed.stdout)[-1000:]}")
        print(f"{'reviewed checker limitation' if completed.returncode else 'passed'}: {label}", flush=True)
        return reference

    def snapshot(self, evidence, manifest, augmentation, label):
        man = evidence.materialize(evidence.put(manifest), label + "-manifest.json")
        aug = evidence.materialize(evidence.put(augmentation), label + "-augmentation.json")
        xml = evidence.path / (label + ".xml")
        self.command(["kicad-cli", "sch", "export", "netlist", "--format", "kicadxml", "--output", str(xml), str(self.schematic)], evidence, label + " netlist")
        target = evidence.path / (label + "-snapshot.json")
        self.command(self.python + ["pcb/tools/tscircuit_handoff.py", "snapshot-kicad", str(self.board), str(man), "--augmentation", str(aug), "--schematic-netlist", str(xml), "--rules", str(self.board.with_suffix(".kicad_pro")), "--rules", str(self.board.with_suffix(".kicad_dru")), "-o", str(target)], evidence, label + " source/native parity")
        value = handoff.read_json(target)
        reference = evidence.put(value)
        for temporary in (man, aug, xml, target):
            temporary.unlink()
        return reference

    def begin(self, directory):
        evidence = self.evidence(directory, new=True)
        lock = handoff.read_json(self.path("lock"))
        before = native_hashes(self.native)
        snapshot = self.snapshot(evidence, lock["manifest"], lock["augmentation"], "before")
        if native_hashes(self.native) != before:
            raise WorkflowError("Native project changed while beginning ECO")
        data = {"schema_version": VERSION, "board": self.name, "stage": "begun",
                "baseline_lock_sha256": sha(self.path("lock")), "before_native": before,
                "before_snapshot": snapshot, "baseline_manifest": evidence.put(lock["manifest"]),
                "baseline_augmentation": evidence.put(lock["augmentation"])}
        evidence.write_index(data)
        return data

    def plan(self, directory, allow_routed_eco=False, allow_routed_placement=False):
        evidence = self.evidence(directory)
        data = evidence.index()
        self.assert_run(data)
        if data.get("stage") not in {"begun", "planned"}:
            raise WorkflowError("Plan requires begun or planned run")
        if data["before_native"] != native_hashes(self.native) or data["baseline_lock_sha256"] != sha(self.path("lock")):
            raise WorkflowError("Native project or comparison lock changed since begin")
        self.build_source(evidence)
        manifest = handoff.load_manifest(self.path("manifest"))
        augmentation = handoff.load_augmentation(self.path("augmentation"), manifest)
        plan = handoff.build_plan(manifest, augmentation, handoff.read_json(self.path("lock")), evidence.get(data["before_snapshot"]), allow_routed_eco, allow_routed_placement)
        data.update(stage="planned", plan=evidence.put(plan), target_inputs=self.fingerprints(),
                    allow_routed_eco=allow_routed_eco, allow_routed_placement=allow_routed_placement)
        data.pop("validation", None)
        data.pop("review", None)
        evidence.write_index(data)
        if plan["blocked"]:
            raise WorkflowError("ECO blocked: " + "; ".join(plan["blockers"]))
        return plan

    def assert_run(self, data):
        if data.get("schema_version") != VERSION or data.get("board") != self.name:
            raise WorkflowError("Run belongs to another board or schema")

    def doctor(self, directory):
        evidence = self.evidence(directory)
        command = self.command(self.python + ["pcb/tools/kicad_native.py", "capabilities"], evidence, "native capabilities")
        result = json.loads(evidence.get(command)["stdout"])
        result["workflow_profile"] = self.name
        result["design_contract"] = self.spec["contract"]
        result["visual_targets"] = self.spec["visual_targets"]
        result["schematic_field_wrapper"] = "pcb/tools/kicad_schematic.py: existing fields on explicit leaf sheets"
        result["preparation_profile"] = str(self.profiles.relative_to(self.root))
        evidence.put(result)
        return result

    def planned(self, evidence):
        data = evidence.index()
        self.assert_run(data)
        if data.get("stage") != "planned" or "plan" not in data:
            raise WorkflowError("Native application requires a planned run")
        plan = evidence.get(data["plan"])
        if plan.get("blocked") or data["target_inputs"] != self.fingerprints():
            raise WorkflowError("Plan is blocked or stale; regenerate before application")
        if data["before_native"] != native_hashes(self.native):
            raise WorkflowError("Native files changed since planning")
        return data, plan

    def draft_transaction(self, directory, output):
        evidence = self.evidence(directory)
        data, plan = self.planned(evidence)
        before = evidence.get(data["before_snapshot"])
        components = handoff.by_id(before["source_owned"]["components"])
        augmentation = handoff.load_augmentation(self.path("augmentation"), handoff.load_manifest(self.path("manifest")))
        operations, unsupported = [], []
        for change in plan["changes"]:
            if change["kind"] != "placement" or change["before"]["side"] != change["after"]["side"]:
                unsupported.append({"kind": change["kind"], "target": change["target"]})
                continue
            component = components[change["target"]]
            target = change["after"]
            operations.append({"op": "footprint_move", "uuid": component["uuid"],
                "from": {k: component["placement"][k] for k in ("position_mm", "rotation_deg")},
                "to": {"position_mm": list(handoff.source_to_kicad_xy(target["x_mm"], target["y_mm"], augmentation)),
                       "rotation_deg": target["rotation_deg"]},
                "associated_uuids": []})
        result = {"schema_version": VERSION, "before_files": kicad_native.project_files(self.board), "operations": operations}
        # Never silently produce a partial ECO. Complex changes need an explicit
        # native transaction, source-aware library work or the capability fallback.
        if unsupported:
            raise WorkflowError("Automatic draft only covers same-side placement: " + json.dumps(unsupported))
        if not operations:
            raise WorkflowError("Plan has no placement edits to draft")
        output = Path(output).resolve()
        if output.is_relative_to(self.native) or output == self.path("lock"):
            raise WorkflowError("Transaction must be outside the native project and lock")
        handoff.atomic_write_json(output, result)
        return {"stage": "drafted", "transaction": str(output), "operations": len(operations),
                "required_review": "Review explicit associated_uuids for attached tracks/vias/zones before applying"}

    def apply(self, directory, transaction_path):
        evidence = self.evidence(directory)
        data, _ = self.planned(evidence)
        transaction = handoff.read_json(Path(transaction_path))
        kicad_native.validate_transaction(self.board, transaction)
        request = evidence.materialize(evidence.put(transaction), "transaction.json")
        receipt = evidence.path / "application.json"
        data.update(stage="applying")
        data.pop("validation", None)
        data.pop("review", None)
        evidence.write_index(data)
        command = self.python + ["pcb/tools/kicad_native.py", "apply", "--board", str(self.board),
                                "--transaction", str(request), "--receipt", str(receipt)]
        try:
            completed = subprocess.run(command, cwd=self.root, capture_output=True, text=True)
            evidence.put({"argv": command, "returncode": completed.returncode,
                          "stdout": completed.stdout, "stderr": completed.stderr})
            if completed.returncode:
                raise WorkflowError("Native application failed: " + completed.stderr[-1500:])
            application = handoff.read_json(receipt)
            data.update(stage="applied", application=evidence.put(application), applied_native=native_hashes(self.native))
            if self.fingerprints() != data["target_inputs"]:
                raise WorkflowError("Source inputs changed during application; native edit remains unaccepted")
        except Exception as exc:
            data.update(stage="failed", error=str(exc))
            evidence.write_index(data)
            raise
        evidence.write_index(data)
        request.unlink()
        receipt.unlink()
        return data

    def validate(self, directory):
        evidence = self.evidence(directory)
        data = evidence.index() if (evidence.path / "run.json").exists() else {"schema_version": VERSION, "board": self.name}
        self.assert_run(data)
        # Invalidating an older success happens before running any command.
        data.update(stage="validating")
        data.pop("validation", None)
        data.pop("review", None)
        evidence.write_index(data)
        before = native_hashes(self.native)
        checks = {}
        try:
            commands = [self.build_source(evidence)]
            inputs = self.fingerprints()
            commands.extend(self.command(c, evidence, "source " + str(i + 1), self.path("source_cwd"),
                self.spec.get("source_check_limitations", {}).get(str(i))) for i, c in enumerate(self.spec["source_checks"]))
            checks["source"] = evidence.put({"passed": True, "commands": commands})
            cleanup = evidence.path / "cleanup.json"
            self.command(["python3", "pcb/tools/tscircuit_handoff.py", "verify-schematic-cleanup", str(self.path("manifest")), "--augmentation", str(self.path("augmentation")), "--schematic", str(self.schematic), "-o", str(cleanup)], evidence, "strict schematic ERC and fields")
            checks["strict_erc"] = evidence.put(handoff.read_json(cleanup))
            cleanup.unlink()
            manifest = handoff.load_manifest(self.path("manifest"))
            augmentation = handoff.load_augmentation(self.path("augmentation"), manifest)
            snapshot = self.snapshot(evidence, manifest, augmentation, "after")
            checks["source_parity"] = evidence.put({"passed": True, "snapshot": snapshot})
            drc = evidence.path / "drc.json"
            self.command(["kicad-cli", "pcb", "drc", "--refill-zones", "--schematic-parity", "--severity-all", "--format", "json", "-o", str(drc), str(self.board)], evidence, "native copper DRC")
            report = handoff.read_json(drc)
            required = {"violations", "schematic_parity", "unconnected_items", "included_severities"}
            if not required <= set(report) or not {"error", "warning", "exclusion"} <= set(report["included_severities"]):
                raise WorkflowError("DRC omitted required findings or severities")
            # Exact reviewed exclusions come from the separately validated profile policy.
            profiles = handoff.read_json(self.profiles)
            profile = profiles["boards"][self.name]
            policy_path = relative_path(self.root, profile["policy"])
            policy = handoff.read_json(policy_path)["boards"][self.name]
            allowed = policy.get("native_drc_exclusions", [])
            failures = [v for v in report["violations"] + report["schematic_parity"]
                        if not (v.get("excluded") is True and {k: v.get(k) for k in ("type", "description", "severity", "items")} in allowed)]
            if failures:
                raise WorkflowError(f"Native DRC has {len(failures)} unwaived findings")
            checks["drc"] = evidence.put({"passed": True, "report": report, "unconnected": len(report["unconnected_items"])})
            drc.unlink()
            audit = evidence.path / "preparation.json"
            self.command(self.python + ["pcb/tools/pcb_readiness.py", "--board", self.name, "--profiles", str(self.profiles), "--root", str(self.root), "--board-path", str(self.board), "--manifest", str(self.path("manifest")), "--output", str(audit)], evidence, "complete native preparation")
            prepared = handoff.read_json(audit)
            if prepared.get("passed") is not True or prepared.get("findings") != [] or not prepared.get("checks"):
                raise WorkflowError("Preparation audit is incomplete or failed")
            checks["preparation"] = evidence.put(prepared)
            audit.unlink()
            render_dir = evidence.path / "renders"
            if render_dir.is_symlink():
                raise WorkflowError("Render directory cannot be a symlink")
            if render_dir.exists():
                shutil.rmtree(render_dir)
            render_dir.mkdir()
            self.command(["kicad-cli", "sch", "export", "svg", "-o", str(render_dir / "schematic") + "/", str(self.schematic)], evidence, "schematic review renders")
            layers = "F.Cu,In1.Cu,In2.Cu,B.Cu" if manifest["board"]["layer_count"] == 4 else "F.Cu,B.Cu"
            layers += ",F.Paste,B.Paste,F.Mask,B.Mask,F.SilkS,B.SilkS,F.Fab,B.Fab"
            self.command(["kicad-cli", "pcb", "export", "svg", "--layers", layers, "--common-layers", "Edge.Cuts", "--mode-multi", "--page-size-mode", "2", "--exclude-drawing-sheet", "-o", str(render_dir / "board") + "/", str(self.board)], evidence, "PCB layer review renders")
            renders = {str(p.relative_to(evidence.path)): sha(p) for p in sorted(render_dir.rglob("*.svg")) if p.stat().st_size}
            if len(renders) < len(layers.split(",")) + 1:
                raise WorkflowError("Required schematic and board renders missing")
            checks["renders"] = evidence.put({"passed": True, "files": renders})
            if before != native_hashes(self.native) or inputs != self.fingerprints():
                raise WorkflowError("Inputs changed during validation")
            validation = {"schema_version": VERSION, "board": self.name, "passed": True,
                          "native_files": before, "inputs": inputs, "checks": checks,
                          "snapshot": snapshot, "manifest": evidence.put(manifest),
                          "augmentation": evidence.put(augmentation)}
            data.update(stage="validated", validation=evidence.put(validation))
        except Exception as exc:
            data.update(stage="failed", error=str(exc), completed_checks=checks)
            evidence.write_index(data)
            raise
        evidence.write_index(data)
        return validation

    def checked_validation(self, evidence):
        data = evidence.index()
        self.assert_run(data)
        if data.get("stage") not in {"validated", "reviewed"}:
            raise WorkflowError("A complete validation is required")
        report = evidence.get(data.get("validation"))
        if report.get("schema_version") != VERSION or report.get("board") != self.name or report.get("passed") is not True or set(report.get("checks", {})) != CHECKS:
            raise WorkflowError("Validation lacks required checks")
        if report["native_files"] != native_hashes(self.native) or report["inputs"] != self.fingerprints():
            raise WorkflowError("Validation is stale: source, native files, profile or tooling changed")
        for name, digest in report["checks"].items():
            check = evidence.get(digest)
            if check.get("passed") is not True:
                raise WorkflowError(f"Required check did not pass: {name}")
            if name == "source":
                records = [evidence.get(command) for command in check["commands"]]
                if [r["argv"] for r in records] != [self.spec["build"]] + self.spec["source_checks"]:
                    raise WorkflowError("Source command set does not match board profile")
                for i, record in enumerate(records):
                    if record["returncode"] != 0:
                        limitation = self.spec.get("source_check_limitations", {}).get(str(i - 1))
                        if not limitation or record.get("reviewed_limitation") != limitation:
                            raise WorkflowError("Source command failed")
                        identity = {"argv": record["argv"], "returncode": record["returncode"],
                                    "stdout_sha256": hashlib.sha256(record["stdout"].encode()).hexdigest(),
                                    "stderr_sha256": hashlib.sha256(record["stderr"].encode()).hexdigest()}
                        if any(limitation.get(k) != v for k, v in identity.items()):
                            raise WorkflowError("Checker limitation no longer matches exact finding output")
            if name == "preparation" and (check.get("findings") != [] or not check.get("checks") or any(c.get("passed") is not True for c in check["checks"])):
                raise WorkflowError("Incomplete preparation audit")
        for key in ("manifest", "augmentation", "snapshot"):
            evidence.get(report[key])
        if evidence.get(report["checks"]["source_parity"])["snapshot"] != report["snapshot"]:
            raise WorkflowError("Source parity snapshot does not match validation")
        for name, digest in evidence.get(report["checks"]["renders"])["files"].items():
            path = relative_path(evidence.path, name)
            if not path.is_file() or sha(path) != digest:
                raise WorkflowError("Reviewed render missing or modified")
        return data, report

    def status(self, directory):
        evidence = self.evidence(directory)
        data = evidence.index()
        self.assert_run(data)
        if data.get("stage") in {"validated", "reviewed"}:
            self.checked_validation(evidence)
        elif data.get("stage") == "accepted":
            report = evidence.get(data["validation"])
            expected = dict(report["inputs"])
            expected[self.spec["lock"]] = data["accepted_lock_sha256"]
            if expected != self.fingerprints() or report["native_files"] != native_hashes(self.native):
                raise WorkflowError("Accepted evidence is stale: inputs changed after acceptance")
            evidence.get(data["acceptance"])
            evidence.get(data["review"])
        return {k: v for k, v in data.items() if k not in {"before_native", "target_inputs"}}

    def review(self, directory, review_path):
        evidence = self.evidence(directory)
        data, report = self.checked_validation(evidence)
        review = handoff.read_json(Path(review_path))
        if review.get("validation") != data["validation"] or set(review.get("scopes", {})) != REVIEW_SCOPES:
            raise WorkflowError("Review must bind this validation and every required scope")
        if not isinstance(review.get("reviewer"), str) or not review["reviewer"].strip():
            raise WorkflowError("Named reviewer required; the tool cannot claim visual inspection")
        if any(not isinstance(v, str) or not v.strip() for v in review["scopes"].values()):
            raise WorkflowError("Each review scope needs its concrete finding or evidence")
        if review.get("unresolved_findings") != []:
            raise WorkflowError("Resolve review findings before acceptance")
        data.update(stage="reviewed", review=evidence.put(review))
        evidence.write_index(data)
        return data

    def accept(self, directory):
        evidence = self.evidence(directory)
        data, report = self.checked_validation(evidence)
        if data.get("stage") != "reviewed" or "plan" not in data or "before_snapshot" not in data:
            raise WorkflowError("Acceptance requires an ECO baseline, plan and completed review")
        review = evidence.get(data["review"])
        if review["validation"] != data["validation"] or review["unresolved_findings"]:
            raise WorkflowError("Review is stale or unresolved")
        if data["baseline_lock_sha256"] != sha(self.path("lock")):
            raise WorkflowError("Comparison lock changed since begin")
        files = {name: evidence.materialize(digest, name + ".json") for name, digest in {
            "manifest": report["manifest"], "augmentation": report["augmentation"],
            "plan": data["plan"], "before": data["before_snapshot"],
            "after": report["snapshot"], "cleanup": report["checks"]["strict_erc"]}.items()}
        receipt = evidence.path / "acceptance.json"
        # Validate against an isolated comparison lock. The authoritative lock
        # advances only after live source/native hashes have been checked again.
        candidate_lock = evidence.path / "candidate-lock.json"
        handoff.atomic_write_json(candidate_lock, handoff.read_json(self.path("lock")))
        command = self.python + ["pcb/tools/tscircuit_handoff.py", "accept-eco", str(files["manifest"]),
            "--augmentation", str(files["augmentation"]), "--lock", str(candidate_lock),
            "--plan", str(files["plan"]), "--before-snapshot", str(files["before"]),
            "--after-snapshot", str(files["after"]), "--board", str(self.board),
            "--schematic", str(self.schematic), "--cleanup-receipt", str(files["cleanup"]), "--receipt", str(receipt)]
        for flag in ("allow_routed_eco", "allow_routed_placement"):
            if data.get(flag):
                command.append("--" + flag.replace("_", "-"))
        self.command(command, evidence, "final ECO acceptance checks")
        if report["inputs"] != self.fingerprints() or report["native_files"] != native_hashes(self.native):
            data.update(stage="failed", error="Inputs changed during acceptance; authoritative lock was not advanced")
            evidence.write_index(data)
            raise WorkflowError(data["error"])
        handoff.atomic_write_json(self.path("lock"), handoff.read_json(candidate_lock))
        data.update(stage="accepted", acceptance=evidence.put(handoff.read_json(receipt)),
                    accepted_lock_sha256=sha(self.path("lock")))
        # One portable index includes all gates/review rather than more full snapshots.
        evidence.write_index(data)
        for path in files.values():
            path.unlink()
        receipt.unlink()
        candidate_lock.unlink()
        return data


def main(args=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["doctor", "begin", "plan", "draft-transaction", "apply", "validate", "review", "accept", "status"])
    parser.add_argument("board")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--config", default="pcb/workflow.json")
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--review", type=Path)
    parser.add_argument("--transaction", type=Path, help="Explicit native transaction for apply, or output path for draft-transaction")
    parser.add_argument("--allow-routed-eco", action="store_true")
    parser.add_argument("--allow-routed-placement", action="store_true")
    options = parser.parse_args(args)
    try:
        flow = Workflow(options.root, options.config, options.board)
        if options.command == "plan":
            result = flow.plan(options.run, options.allow_routed_eco, options.allow_routed_placement)
        elif options.command == "review":
            if not options.review:
                raise WorkflowError("review requires --review JSON")
            result = flow.review(options.run, options.review)
        elif options.command in {"apply", "draft-transaction"}:
            if not options.transaction:
                raise WorkflowError(options.command + " requires --transaction JSON")
            result = getattr(flow, options.command.replace("-", "_"))(options.run, options.transaction)
        elif options.command == "status":
            result = flow.status(options.run)
        else:
            result = getattr(flow, options.command)(options.run)
        print(json.dumps(result if options.command in {"doctor", "status", "draft-transaction"} else
                         {"board": options.board, "command": options.command,
                          "stage": result.get("stage", options.command), "passed": True}, indent=2))
        return 0
    except (WorkflowError, handoff.HandoffError, OSError, KeyError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
