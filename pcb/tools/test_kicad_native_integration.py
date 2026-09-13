"""Native KiCad scratch-only tests; no product paths or vendor files are written.

Run: sh pcb/tools/kicad_python.sh pcb/tools/test_kicad_native_integration.py
Host Python deliberately skips these tests if pcbnew/wx are unavailable.
"""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import uuid

import kicad_native as native

NATIVE_AVAILABLE = importlib.util.find_spec("pcbnew") is not None and importlib.util.find_spec("wx") is not None


def uid():
    return str(uuid.uuid4())


def create_fixture(folder):
    """Create a complete tiny PCB/project solely through KiCad's native API."""
    p = native._runtime()
    board_path = folder / "fixture.kicad_pcb"
    project_path = board_path.with_suffix(".kicad_pro")
    manager = p.GetSettingsManager()
    # A new project has no file yet; LoadProject false creates its native model.
    manager.LoadProject(str(project_path), False)
    project = manager.GetProject(str(project_path))
    if not manager.SaveProject(str(project_path), project):
        raise RuntimeError("Could not create native fixture project")
    manager.UnloadProject(project, False)
    manager.LoadProject(str(project_path), False)
    project = manager.GetProject(str(project_path))
    board = p.BOARD()
    board.SetFileName(str(board_path))
    # Newly constructed BOARD lacks parser-initialized design settings. Native
    # save/load initializes them before attaching a project (KiCad 10 SWIG).
    p.SaveBoard(str(board_path), board)
    board = p.LoadBoard(str(board_path))
    board.SetProject(project)
    for name in ("GND", "VCC", "SIGNAL"):
        board.Add(p.NETINFO_ITEM(board, name))
    fp = p.FOOTPRINT(board)
    fp.SetReference("U1")
    fp.SetValue("NativeFixture")
    fp.SetField("MPN", "ORIGINAL-MPN")
    fp.SetPosition(native._vector(p, [22, 20]))
    for number, net_name, position in (("1", "GND", [20, 20]), ("2", "VCC", [24, 20])):
        pad = p.PAD(fp)
        pad.SetNumber(number)
        pad.SetPosition(native._vector(p, position))
        pad.SetSize(native._vector(p, [1.2, 1.2]))
        pad.SetShape(p.PAD_SHAPE_RECT)
        pad.SetAttribute(p.PAD_ATTRIB_SMD)
        pad.SetLayerSet(p.PAD.SMDMask())
        pad.SetNet(board.FindNet(net_name))
        fp.Add(pad)
    board.Add(fp)
    corners = [[10, 10], [40, 10], [40, 40], [10, 40]]
    for index in range(4):
        shape = p.PCB_SHAPE(board)
        shape.SetShape(p.SHAPE_T_SEGMENT)
        shape.SetLayer(p.Edge_Cuts)
        shape.SetStart(native._vector(p, corners[index]))
        shape.SetEnd(native._vector(p, corners[(index + 1) % 4]))
        shape.SetWidth(p.FromMM(.05))
        board.Add(shape)
    track = p.PCB_TRACK(board)
    track.SetStart(native._vector(p, [16, 15]))
    track.SetEnd(native._vector(p, [18, 15]))
    track.SetWidth(p.FromMM(.3))
    track.SetLayer(p.F_Cu)
    track.SetNet(board.FindNet("SIGNAL"))
    board.Add(track)
    via = p.PCB_VIA(board)
    via.SetPosition(native._vector(p, [18, 15]))
    via.SetWidth(p.FromMM(.6))
    via.SetDrill(p.FromMM(.3))
    via.SetViaType(p.VIATYPE_THROUGH)
    via.SetLayerPair(p.F_Cu, p.B_Cu)
    via.SetNet(board.FindNet("SIGNAL"))
    board.Add(via)
    zone = p.ZONE(board)
    zone.SetZoneName("Fixture ground")
    zone.SetLayer(p.F_Cu)
    zone.SetNet(board.FindNet("GND"))
    zone.Outline().NewOutline()
    for x, y in [[11, 11], [39, 11], [39, 39], [11, 39]]:
        zone.Outline().Append(p.FromMM(x), p.FromMM(y))
    zone.SetLocalClearance(p.FromMM(.2))
    zone.SetMinThickness(p.FromMM(.2))
    zone.SetThermalReliefGap(p.FromMM(.3))
    zone.SetThermalReliefSpokeWidth(p.FromMM(.3))
    board.Add(zone)
    board.SynchronizeNetsAndNetClasses(False)
    board.BuildConnectivity()
    if not p.ZONE_FILLER(board).Fill(board.Zones()):
        raise RuntimeError("Fixture native fill failed")
    if not p.SaveBoard(str(board_path), board):
        raise RuntimeError("Fixture native save failed")
    manager.SaveProjectCopy(str(project_path), project)
    board = None
    manager.UnloadProject(project, False)
    # Normalize the new native project once, including its empty root-sheet
    # metadata, before using this saved baseline in preservation tests.
    with native.NativeProject(board_path) as session:
        session.save(save_project=True)
    return board_path


@unittest.skipUnless(NATIVE_AVAILABLE, "requires KiCad bundled Python with pcbnew/wx")
class NativeIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = tempfile.TemporaryDirectory(prefix="kicad-native-integration-base-")
        cls.template = create_fixture(Path(cls.base.name).resolve())

    @classmethod
    def tearDownClass(cls):
        cls.base.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="kicad-native-integration-")
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name).resolve()
        for name in native.project_files(self.template):
            shutil.copy2(self.template.parent / name, self.folder / name)
        self.board = self.folder / self.template.name
        self.initial = self.read()

    def read(self):
        with native.NativeProject(self.board) as session:
            return session.readback()

    def apply(self, operations, validator=None):
        return native.apply_transaction(self.board, {"schema_version": 1,
            "before_files": native.project_files(self.board), "operations": operations}, validator=validator)

    def field_op(self):
        fp = next(iter(self.initial["footprints"]))
        return {"op": "field", "uuid": fp, "name": "MPN", "from": "ORIGINAL-MPN", "to": "UPDATED-MPN"}

    def test_field_replacement_has_one_property_and_preserves_geometry(self):
        receipt = self.apply([self.field_op()])
        after = self.read()
        fp = next(iter(after["footprints"]))
        expected = copy.deepcopy(self.initial)
        expected["footprints"][fp]["fields"]["MPN"] = "UPDATED-MPN"
        self.assertEqual(after, expected)
        with native.NativeProject(self.board) as session:
            fields = [f for f in next(iter(session.board.GetFootprints())).GetFields() if str(f.GetName()) == "MPN"]
            self.assertEqual(len(fields), 1)
        self.assertEqual(receipt["validation"]["status"], "not_run")
        self.assertIn(self.board.name, receipt["published_files"])

    def test_value_and_mpn_can_change_in_one_batch_without_duplicate_fields(self):
        mpn = self.field_op()
        self.apply([mpn, {**mpn, "name": "Value", "from": "NativeFixture", "to": "UPDATED-VALUE"}])
        fp = self.read()["footprints"][mpn["uuid"]]
        self.assertEqual(fp["fields"]["Value"], "UPDATED-VALUE")
        self.assertEqual(fp["fields"]["MPN"], "UPDATED-MPN")

    def test_pad_paste_keeps_copper_mask_net_and_drill(self):
        pad = next(iter(self.initial["pads"]))
        before = self.initial["pads"][pad]
        target = {"paste_layers": [], "margin_mm": -.05, "margin_ratio": -.1}
        self.apply([{"op": "pad_paste", "uuid": pad, "from": before["paste"], "to": target}])
        after = self.read()
        expected = copy.deepcopy(self.initial)
        expected["pads"][pad]["paste"] = target
        expected["pads"][pad]["layers"] = [layer for layer in before["layers"] if layer not in ("F.Paste", "B.Paste")]
        self.assertEqual(after, expected)

    def test_group_move_transforms_only_explicit_geometry(self):
        fp = next(iter(self.initial["footprints"]))
        track = next(iter(self.initial["tracks"]))
        via = next(iter(self.initial["vias"]))
        before = self.initial["footprints"][fp]["pose"]
        self.apply([{"op": "footprint_move", "uuid": fp, "from": before,
            "to": {"position_mm": [24, 23], "rotation_deg": 90}, "associated_uuids": [track, via]}])
        after = self.read()
        self.assertEqual(after["zones"], self.initial["zones"])
        self.assertEqual(after["drawings"], self.initial["drawings"])
        self.assertEqual(after["footprints"][fp]["pose"], {"position_mm": [24, 23], "rotation_deg": 90})
        self.assertEqual(after["vias"][via]["position_mm"], [19, 27])
        self.assertEqual(after["tracks"][track]["end_mm"], [19, 27])

    def test_exact_track_add_delete_and_wrong_net_rejection(self):
        new_id = uid()
        geometry = {"net": "SIGNAL", "layer": "B.Cu", "start_mm": [18, 15], "end_mm": [20, 15], "width_mm": .3}
        self.apply([{"op": "track_add", "uuid": new_id, "geometry": geometry}])
        hashes = native.project_files(self.board)
        wrong = {**geometry, "net": "VCC"}
        with self.assertRaisesRegex(native.NativeError, "geometry/net differs"):
            self.apply([{"op": "track_delete", "uuid": new_id, "geometry": wrong}])
        self.assertEqual(native.project_files(self.board), hashes)
        self.apply([{"op": "track_delete", "uuid": new_id, "geometry": geometry}])
        self.assertEqual(self.read(), self.initial)

    def test_via_add_delete_preserves_tenting(self):
        new_id = uid()
        geometry = {"net": "GND", "position_mm": [30, 30], "diameter_mm": .8, "drill_mm": .4,
                    "layers": ["F.Cu", "B.Cu"], "via_type": native._runtime().VIATYPE_THROUGH,
                    "front_tenting": 1, "back_tenting": 1}
        self.apply([{"op": "via_add", "uuid": new_id, "geometry": geometry}])
        self.assertEqual(self.read()["vias"][new_id], geometry)
        self.apply([{"op": "via_delete", "uuid": new_id, "geometry": geometry}])
        self.assertEqual(self.read(), self.initial)

    def test_zone_add_update_and_group_translation(self):
        zone_id, original = next(iter(self.initial["zones"].items()))
        updated = {**original, "clearance_mm": .4, "priority": 2}
        self.apply([{"op": "zone_update", "uuid": zone_id, "from": original, "to": updated}])
        new_id = uid()
        added = {**original, "name": "Back ground", "layers": ["B.Cu"]}
        self.apply([{"op": "zone_add", "uuid": new_id, "to": added}])
        self.assertEqual(self.read()["zones"], {zone_id: updated, new_id: added})
        fp = next(iter(self.initial["footprints"]))
        self.apply([{"op": "footprint_move", "uuid": fp, "from": self.initial["footprints"][fp]["pose"],
            "to": {"position_mm": [23, 21], "rotation_deg": 0}, "associated_uuids": [zone_id]}])
        self.assertEqual(self.read()["zones"][zone_id]["outline_mm"], [[12, 12], [40, 12], [40, 40], [12, 40]])
        self.assertEqual(self.read()["zones"][new_id], added)

    def test_outline_and_text_native_round_trip(self):
        edges = self.initial["drawings"]
        text_id = uid()
        text = {"text": "GND", "position_mm": [30, 35], "layer": "F.Silkscreen", "size_mm": [1, 1],
                "thickness_mm": .15, "rotation_deg": 0, "mirrored": False}
        self.apply([{"op": "outline_rectangle", "uuids": list(edges), "from": edges,
                     "bounds_mm": [9, 9, 41, 41], "width_mm": .05},
                    {"op": "text_add", "uuid": text_id, "to": text}])
        target = {**text, "text": "POWER", "rotation_deg": 90}
        self.apply([{"op": "text_update", "uuid": text_id, "from": text, "to": target}])
        self.assertEqual(self.read()["drawings"][text_id], {"kind": "text", **target})
        self.assertEqual(set(self.read()["drawings"]), set(edges) | {text_id})

    def test_project_netclass_is_saved_without_collateral_settings(self):
        original = self.initial["netclasses"]["Default"]
        target = {**original, "track_width_mm": .7, "via_diameter_mm": .8, "via_drill_mm": .4}
        receipt = self.apply([{"op": "netclass_update", "name": "Default", "from": original, "to": target}])
        self.assertEqual(self.read()["netclasses"]["Default"], target)
        self.assertIn("fixture.kicad_pro", receipt["published_files"])

    def test_ignored_native_setter_is_rejected_before_save(self):
        hashes = native.project_files(self.board)
        with patch.object(native, "_apply", return_value=None):
            with self.assertRaisesRegex(native.NativeError, "differed from declared result"):
                self.apply([self.field_op()])
        self.assertEqual(native.project_files(self.board), hashes)

    def test_wrong_requested_paste_copper_layer_is_rejected(self):
        hashes = native.project_files(self.board)
        pad_id, pad = next(iter(self.initial["pads"].items()))
        with self.assertRaisesRegex(native.NativeError, "Only F.Paste/B.Paste"):
            self.apply([{"op": "pad_paste", "uuid": pad_id, "from": pad["paste"],
                         "to": {"paste_layers": ["F.Cu"], "margin_mm": None, "margin_ratio": None}}])
        self.assertEqual(native.project_files(self.board), hashes)

    def test_unknown_net_and_late_invalid_operation_leave_all_files_unchanged(self):
        hashes = native.project_files(self.board)
        bad = {"op": "track_add", "uuid": uid(), "geometry": {"net": "UNKNOWN_NET", "layer": "F.Cu",
                "start_mm": [10, 10], "end_mm": [12, 12], "width_mm": .3}}
        with self.assertRaisesRegex(native.NativeError, "Unknown native net"):
            self.apply([self.field_op(), bad])
        self.assertEqual(native.project_files(self.board), hashes)
        self.assertEqual(self.read(), self.initial)

    def test_stale_plan_and_native_uuid_collision_fail(self):
        hashes = native.project_files(self.board)
        plan = {"schema_version": 1, "before_files": hashes, "operations": [self.field_op()]}
        self.apply([self.field_op()])
        with self.assertRaisesRegex(native.NativeError, "Stale"):
            native.apply_transaction(self.board, plan)
        collision = {"op": "track_add", "uuid": next(iter(self.initial["pads"])), "geometry": {
            "net": "GND", "layer": "F.Cu", "start_mm": [10, 10], "end_mm": [11, 11], "width_mm": .3}}
        with self.assertRaisesRegex(native.NativeError, "already exists"):
            self.apply([collision])

    def test_read_only_allows_saved_locked_board_but_never_save_or_fill(self):
        hashes = native.project_files(self.board)
        (self.folder / "~fixture.kicad_pro.lck").touch()
        with native.NativeProject(self.board, read_only=True) as session:
            self.assertEqual(session.readback(), self.initial)
            for operation in (session.save, session.fill):
                with self.assertRaisesRegex(native.NativeError, "Read-only"):
                    operation()
        self.assertEqual(native.project_files(self.board), hashes)

    def test_validator_failure_and_candidate_mutation_never_publish(self):
        hashes = native.project_files(self.board)
        def reject(_):
            raise native.NativeError("source parity failure")
        with self.assertRaisesRegex(native.NativeError, "source parity"):
            self.apply([self.field_op()], reject)
        self.assertEqual(native.project_files(self.board), hashes)
        def mutate(candidate):
            with native.NativeProject(candidate) as session:
                next(iter(session.board.GetFootprints())).SetValue("MUTATED BY VALIDATOR")
                session.save()
            return {"passed": True, "bad_validator": True}
        with self.assertRaisesRegex(native.NativeError, "Validator modified"):
            self.apply([self.field_op()], mutate)
        self.assertEqual(native.project_files(self.board), hashes)

    def test_validator_must_explicitly_pass_without_findings(self):
        hashes = native.project_files(self.board)
        for result in (None, False, {}, {"passed": False}, {"passed": True, "findings": ["bad"]}):
            with self.subTest(result=result):
                with self.assertRaisesRegex(native.NativeError, "explicitly report"):
                    self.apply([self.field_op()], lambda _: result)
                self.assertEqual(native.project_files(self.board), hashes)
        receipt = self.apply([self.field_op()], lambda _: {"passed": True, "findings": [], "errors": []})
        self.assertEqual(receipt["validation"]["status"], "passed")

    @unittest.skipUnless(shutil.which("kicad-cli"), "kicad-cli required for actual native short-circuit probe")
    def test_actual_drc_rejects_short_on_candidate_before_publication(self):
        hashes = native.project_files(self.board)
        def reject_short(candidate):
            output = candidate.parent / "short-drc.json"
            result = subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json", "--output", str(output), str(candidate)],
                                    capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(result.stderr)
            report = json.loads(output.read_text())
            shorts = [v for v in report["violations"] if "short" in v["type"]]
            if shorts:
                raise native.NativeError("DRC rejected intentional short: " + shorts[0]["type"])
            self.fail("Deliberately crossing VCC pad with GND did not produce native DRC short")
        short = {"op": "track_add", "uuid": uid(), "geometry": {"net": "GND", "layer": "F.Cu",
                  "start_mm": [20, 20], "end_mm": [24, 20], "width_mm": .5}}
        with self.assertRaisesRegex(native.NativeError, "DRC rejected intentional short"):
            self.apply([short], reject_short)
        self.assertEqual(native.project_files(self.board), hashes)


if __name__ == "__main__":
    unittest.main()
