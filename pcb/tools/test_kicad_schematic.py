#!/usr/bin/env python3
"""Failure-oriented tests for the guarded Konnect field-edit bridge."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kicad_schematic as bridge


FIXTURE = b'''(kicad_sch (version 20260306) (uuid "root")
 (lib_symbols (symbol "Example:R" (property "Reference" "R")))
 (symbol (lib_id "Example:R") (uuid "symbol-1") (at 1 2 0)
  (in_bom yes) (on_board yes) (dnp no)
  (property "Reference" "R1" (at 1 2 0))
  (property "Value" "10k" (at 1 3 0))
  (property "MPN" "OLD" (at 1 4 0))
  (property "Description" "Original" (at 1 5 0))
  (pin "1" (uuid "pin-1")) (pin "2" (uuid "pin-2")))
 (wire (pts (xy 1 2) (xy 3 4)) (uuid "wire-1")))'''


class SchematicBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "test.kicad_sch"
        self.path.write_bytes(FIXTURE)
        self.request = {"schema_version": 1, "before_sha256": bridge.digest(FIXTURE),
                        "edits": [{"reference": "R1", "fields": {"Value": "12k", "MPN": "NEW"}}]}

    def apply(self):
        return bridge.apply(self.path, self.request, ["test-konnect"], ["test-kicad"])

    @staticmethod
    def successful_batch(_argv, candidate, _edits, _timeout):
        candidate.write_bytes(candidate.read_bytes().replace(b'"10k"', b'"12k"').replace(b'"OLD"', b'"NEW"'))
        return {"test": True}

    def test_success_changes_only_requested_properties(self):
        with mock.patch.object(bridge, "konnect_batch", side_effect=self.successful_batch), \
             mock.patch.object(bridge, "native_netlist", return_value=b"<nets />"):
            result = self.apply()
        self.assertEqual(result["before_sha256"], bridge.digest(FIXTURE))
        self.assertEqual(result["after_sha256"], bridge.digest(self.path.read_bytes()))
        self.assertEqual(bridge.parse(self.path.read_bytes()), bridge.expected_edit(FIXTURE, self.request["edits"])[0])

    def test_stale_request_stops_before_tool_invocation(self):
        self.path.write_bytes(FIXTURE + b"\n")
        with mock.patch.object(bridge, "konnect_batch") as tool, self.assertRaisesRegex(bridge.SchematicError, "Stale"):
            self.apply()
        tool.assert_not_called()

    def test_bad_requests_are_rejected_before_tool_invocation(self):
        invalid = [
            [{"reference": "R1", "fields": {"MPN": 'bad " quote'}}],
            [{"reference": "R1", "fields": {"MPN": "bad\\escape"}}],
            [{"reference": "R1", "fields": {"MPN": "bad\nline"}}],
            [{"reference": "R1", "fields": {"NEW_FIELD": "value"}}],
            [{"reference": "R1", "fields": {"on_board": "no"}}],
            [{"reference": "R1", "fields": {"Reference": "R2"}}],
            [{"reference": "R1", "value": "12k"}],
            self.request["edits"] * 2,
        ]
        for edits in invalid:
            with self.subTest(edits=edits), mock.patch.object(bridge, "konnect_batch") as tool:
                self.request["edits"] = edits
                with self.assertRaises(bridge.SchematicError):
                    self.apply()
                tool.assert_not_called()
                self.assertEqual(self.path.read_bytes(), FIXTURE)

    def test_duplicates_and_root_sheets_are_not_ambiguous_targets(self):
        variants = [
            FIXTURE.replace(b'(pin "1"', b'(property "MPN" "DUPLICATE") (pin "1"'),
            FIXTURE.replace(b'(lib_symbols', b'(sheet (property "Sheetfile" "child.kicad_sch")) (lib_symbols'),
        ]
        for data in variants:
            with self.subTest(data=data), self.assertRaises(bridge.SchematicError):
                bridge.expected_edit(data, self.request["edits"])

    def test_partial_or_collateral_changes_never_publish(self):
        def partial(_argv, candidate, _edits, _timeout):
            candidate.write_bytes(candidate.read_bytes().replace(b'"10k"', b'"12k"'))
            return {}

        def collateral(*args):
            self.successful_batch(*args)
            candidate = args[1]
            candidate.write_bytes(candidate.read_bytes().replace(b'"pin-1"', b'"different-pin"'))
            return {}

        for behavior in (partial, collateral):
            with self.subTest(behavior=behavior), mock.patch.object(bridge, "konnect_batch", side_effect=behavior):
                with self.assertRaisesRegex(bridge.SchematicError, "undeclared semantics"):
                    self.apply()
                self.assertEqual(self.path.read_bytes(), FIXTURE)

    def test_native_rejection_or_connectivity_change_never_publishes(self):
        for side_effect in (bridge.SchematicError("Native parse failed"), [b"<nets />", b"<nets><net /></nets>"]):
            with self.subTest(side_effect=side_effect), \
                 mock.patch.object(bridge, "konnect_batch", side_effect=self.successful_batch), \
                 mock.patch.object(bridge, "native_netlist", side_effect=side_effect):
                with self.assertRaises(bridge.SchematicError):
                    self.apply()
                self.assertEqual(self.path.read_bytes(), FIXTURE)

    def test_concurrent_file_edit_is_preserved(self):
        def concurrent(*args):
            self.path.write_bytes(FIXTURE + b"\n")
            return self.successful_batch(*args)

        with mock.patch.object(bridge, "konnect_batch", side_effect=concurrent), \
             mock.patch.object(bridge, "native_netlist", return_value=b"<nets />"):
            with self.assertRaisesRegex(bridge.SchematicError, "changed during verification"):
                self.apply()
        self.assertEqual(self.path.read_bytes(), FIXTURE + b"\n")

    def test_protocol_rejects_partial_success_even_with_false_is_error(self):
        payload = {"errors": ["Field absent"], "updated_count": 1,
                   "updated": [{"reference": "R1", "changes": ["Value changed"]}]}
        responses = [
            {"jsonrpc": "2.0", "id": 1, "result": {"serverInfo": {"version": "0.2.1"}}},
            {"jsonrpc": "2.0", "id": 2, "result": {"isError": False}},
            {"jsonrpc": "2.0", "id": 3, "result": {"isError": False,
                "content": [{"type": "text", "text": json.dumps(payload)}]}},
        ]
        completed = mock.Mock(returncode=0, stderr="", stdout="\n".join(json.dumps(x) for x in responses))
        with mock.patch.object(bridge.subprocess, "run", return_value=completed), \
             self.assertRaisesRegex(bridge.SchematicError, "incomplete"):
            bridge.konnect_batch(["test"], self.path, self.request["edits"], 10)


if __name__ == "__main__":
    unittest.main()
