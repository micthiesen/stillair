#!/usr/bin/env python3
"""Verified existing-field replacement through Konnect's local MCP transport.

This module only parses protected files. Konnect produces the replacement bytes;
the wrapper checks them before publishing. It never serializes KiCad objects.
An explicit leaf schematic is required. Reference changes, new properties and
symbol flags (including BOM/position exclusion) are deliberately unsupported.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path


class SchematicError(ValueError):
    """A requested edit cannot be verified safely."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse(data: bytes) -> list:
    """Read an S-expression without a writer; retain exact atom/string tokens."""
    text = data.decode("utf-8")
    tokens = []
    pos = 0
    while pos < len(text):
        char = text[pos]
        if char.isspace():
            pos += 1
            continue
        if char in "()":
            tokens.append(char)
            pos += 1
            continue
        start = pos
        if char == '"':
            pos += 1
            while pos < len(text):
                if text[pos] == "\\":
                    pos += 2
                elif text[pos] == '"':
                    pos += 1
                    break
                else:
                    pos += 1
            else:
                raise SchematicError("Unterminated schematic string")
            token = text[start:pos]
            try:
                json.loads(token)
            except json.JSONDecodeError as exc:
                raise SchematicError("Unsupported schematic string escaping") from exc
            if pos < len(text) and not (text[pos].isspace() or text[pos] in "()"):
                raise SchematicError("Missing separator after schematic string")
        else:
            while pos < len(text) and not text[pos].isspace() and text[pos] not in '()"':
                pos += 1
            token = text[start:pos]
            if not token:
                raise SchematicError("Invalid schematic token")
        tokens.append(token)
    stack = []
    roots = []
    for token in tokens:
        if token == "(":
            node = []
            (stack[-1] if stack else roots).append(node)
            stack.append(node)
        elif token == ")":
            if not stack:
                raise SchematicError("Unbalanced schematic parentheses")
            stack.pop()
        elif stack:
            stack[-1].append(token)
        else:
            raise SchematicError("Unexpected token outside schematic root")
    if stack or len(roots) != 1 or not roots[0] or roots[0][0] != "kicad_sch":
        raise SchematicError("Expected one complete kicad_sch root")
    return roots[0]


def children(node: list, key: str) -> list:
    return [item for item in node if isinstance(item, list) and item and item[0] == key]


def string(token: str) -> str:
    if not isinstance(token, str) or not token.startswith('"'):
        raise SchematicError("Expected quoted schematic property")
    try:
        value = json.loads(token)
    except json.JSONDecodeError as exc:
        raise SchematicError("Malformed schematic property") from exc
    if not isinstance(value, str):
        raise SchematicError("Expected string property")
    return value


def safe_string(value: object, name: str) -> str:
    # Konnect 0.2.1 finds the first quote and inserts unescaped values. Reject
    # both old and new values that could confuse that implementation.
    if not isinstance(value, str) or any(c in value for c in '\\"') or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise SchematicError(f"{name} must be a string without quotes, backslashes or control characters")
    return value


def properties(symbol: list) -> dict:
    result = {}
    for item in children(symbol, "property"):
        if len(item) < 3:
            raise SchematicError("Malformed symbol property")
        name = string(item[1])
        if name in result:
            raise SchematicError(f"Duplicate symbol property: {name}")
        result[name] = item
    return result


def expected_edit(before: bytes, edits: object) -> tuple[list, list]:
    """Validate requests and build an in-memory comparison, never file text."""
    tree = copy.deepcopy(parse(before))
    if children(tree, "sheet"):
        raise SchematicError("Pass a leaf sheet, not a root containing hierarchical sheets")
    symbols = {}
    for symbol in children(tree, "symbol"):
        if not children(symbol, "lib_id"):
            continue
        props = properties(symbol)
        if "Reference" not in props:
            raise SchematicError("Placed symbol has no Reference")
        reference = string(props["Reference"][2])
        if reference in symbols:
            raise SchematicError(f"Ambiguous multi-unit or duplicate reference: {reference}")
        symbols[reference] = props
    if not isinstance(edits, list) or not edits:
        raise SchematicError("edits must be a non-empty array")
    seen = set()
    normalized = []
    forbidden = {"Reference", "in_bom", "on_board", "dnp", "exclude_from_sim", "exclude_from_bom", "exclude_from_pos_files"}
    for edit in edits:
        if not isinstance(edit, dict) or set(edit) - {"reference", "fields"}:
            raise SchematicError("Each edit accepts only reference and fields")
        reference = safe_string(edit.get("reference"), "reference")
        if not reference or reference in seen:
            raise SchematicError(f"Empty or repeated edit reference: {reference}")
        seen.add(reference)
        if reference not in symbols:
            raise SchematicError(f"Reference {reference} is absent from this leaf schematic; pass its actual sheet file")
        fields = edit.get("fields")
        if not isinstance(fields, dict) or not fields:
            raise SchematicError("fields must be a non-empty object of existing properties")
        for field, value in fields.items():
            safe_string(field, "field name")
            if not field or field in forbidden:
                raise SchematicError(f"Unsupported field or symbol flag: {field}")
            if field not in symbols[reference]:
                raise SchematicError(f"Existing property {reference}.{field} not found")
            safe_string(string(symbols[reference][field][2]), f"old {reference}.{field}")
            safe_string(value, f"new {reference}.{field}")
            symbols[reference][field][2] = json.dumps(value, ensure_ascii=False)
        normalized.append({"reference": reference, "fields": fields})
    return tree, normalized


def command(value: str) -> list[str]:
    try:
        argv = json.loads(value)
    except json.JSONDecodeError as exc:
        raise SchematicError("Command must be a JSON argv array") from exc
    if not isinstance(argv, list) or not argv or not all(isinstance(x, str) and x for x in argv):
        raise SchematicError("Command must be a non-empty JSON argv array of strings")
    return argv


def konnect_batch(argv: list[str], schematic: Path, edits: list, timeout: float) -> dict:
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2024-11-05", "capabilities": {},
            "clientInfo": {"name": "verified-kicad-schematic", "version": "1"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {
            "name": "load_toolset", "arguments": {"name": "sch_batch"}}},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {
            "name": "batch_edit_schematic_components", "arguments": {
                "schematic": str(schematic), "edits": edits}}},
    ]
    try:
        completed = subprocess.run(argv, input="".join(json.dumps(x) + "\n" for x in requests),
                                   capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SchematicError(f"Konnect invocation failed: {exc}") from exc
    if completed.returncode:
        raise SchematicError(f"Konnect exited {completed.returncode}: {completed.stderr[-2000:]}")
    responses = {}
    try:
        for line in completed.stdout.splitlines():
            response = json.loads(line)
            if not isinstance(response, dict):
                raise SchematicError("Konnect returned a non-object response")
            if "id" in response:
                if response["id"] in responses:
                    raise SchematicError("Konnect returned a repeated response ID")
                responses[response["id"]] = response
    except (json.JSONDecodeError, TypeError) as exc:
        raise SchematicError("Invalid Konnect protocol output") from exc
    for identifier in (1, 2, 3):
        response = responses.get(identifier, {})
        if not isinstance(response.get("result"), dict) or "error" in response or response["result"].get("isError"):
            raise SchematicError(f"Konnect request {identifier} failed: {response}")
    result = responses[3]["result"]
    content = result.get("content", [])
    if not isinstance(content, list) or not all(isinstance(x, dict) for x in content):
        raise SchematicError("Konnect returned invalid content blocks")
    texts = [x.get("text") for x in content if x.get("type") == "text"]
    try:
        payload = json.loads(texts[0]) if len(texts) == 1 else None
    except (json.JSONDecodeError, TypeError) as exc:
        raise SchematicError("Konnect returned an invalid batch result") from exc
    if not isinstance(payload, dict) or payload.get("errors") != [] or payload.get("updated_count") != len(edits):
        raise SchematicError(f"Konnect batch was incomplete: {payload}")
    updated = payload.get("updated", [])
    if not isinstance(updated, list) or not all(isinstance(x, dict) for x in updated) or len(updated) != len(edits) or {x.get("reference") for x in updated} != {x["reference"] for x in edits}:
        raise SchematicError("Konnect updated references do not match the request")
    return {"server": responses[1]["result"].get("serverInfo"), "result": payload}


def native_netlist(argv: list[str], schematic: Path, output: Path, timeout: float) -> bytes:
    try:
        completed = subprocess.run(argv + ["sch", "export", "netlist", "--format", "kicadxml",
                                          "--output", str(output), str(schematic)],
                                   capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SchematicError(f"KiCad netlist export failed: {exc}") from exc
    if completed.returncode or not output.is_file():
        raise SchematicError(f"KiCad rejected schematic: {completed.stderr[-2000:]}")
    try:
        nets = ET.parse(output).getroot().find("nets")
    except ET.ParseError as exc:
        raise SchematicError("KiCad produced an invalid netlist") from exc
    if nets is None:
        raise SchematicError("KiCad netlist has no nets section")
    return ET.tostring(nets)


def apply(schematic: Path, request: dict, konnect: list[str], kicad_cli: list[str], timeout: float = 60) -> dict:
    if not isinstance(request, dict) or set(request) != {"schema_version", "before_sha256", "edits"} or type(request["schema_version"]) is not int or request["schema_version"] != 1:
        raise SchematicError("Request requires schema_version=1, before_sha256 and edits only")
    if schematic.is_symlink() or not schematic.is_file() or schematic.suffix != ".kicad_sch":
        raise SchematicError("schematic must be a regular .kicad_sch file, not a symlink")
    schematic = schematic.absolute()
    if list(schematic.parent.glob("*.lck")):
        raise SchematicError("A KiCad lock exists beside this schematic; close its editor before applying")
    before = schematic.read_bytes()
    before_hash = digest(before)
    if request["before_sha256"] != before_hash:
        raise SchematicError("Stale before_sha256; schematic changed since this request was prepared")
    expected, edits = expected_edit(before, request["edits"])
    with tempfile.TemporaryDirectory(prefix="kicad-schematic-") as scratch_name:
        scratch = Path(scratch_name)
        original = scratch / "before" / schematic.name
        candidate = scratch / "after" / schematic.name
        original.parent.mkdir()
        candidate.parent.mkdir()
        shutil.copy2(schematic, original)
        shutil.copy2(schematic, candidate)
        receipt = konnect_batch(konnect, candidate, edits, timeout)
        after = candidate.read_bytes()
        if parse(after) != expected:
            raise SchematicError("Konnect changed undeclared semantics or failed exact property readback; nothing published")
        if native_netlist(kicad_cli, original, scratch / "before.xml", timeout) != native_netlist(kicad_cli, candidate, scratch / "after.xml", timeout):
            raise SchematicError("Native net connectivity changed; nothing published")
        if schematic.is_symlink() or schematic.read_bytes() != before:
            raise SchematicError("Schematic changed during verification; nothing published")
        # Copy only the independently verified Konnect-produced bytes. No
        # S-expression writer exists in this module. Atomic rename avoids a
        # partially copied schematic on interruption or full storage.
        descriptor, temp_name = tempfile.mkstemp(prefix=".verified-schematic-", dir=schematic.parent)
        os.close(descriptor)
        temp_path = Path(temp_name)
        try:
            shutil.copy2(candidate, temp_path)
            with temp_path.open("rb") as stream:
                os.fsync(stream.fileno())
            if schematic.is_symlink() or schematic.read_bytes() != before:
                raise SchematicError("Schematic changed before publication; nothing published")
            os.replace(temp_path, schematic)
        finally:
            temp_path.unlink(missing_ok=True)
    return {"schema_version": 1, "schematic": str(schematic), "before_sha256": before_hash,
            "after_sha256": digest(after), "edits": edits, "konnect": receipt,
            "semantic_preservation": True, "native_net_connectivity_preserved": True}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("schematic", type=Path, help="Actual leaf sheet containing the references")
    parser.add_argument("request", type=Path, help="Hash-bound existing-property edits JSON")
    parser.add_argument("--konnect-command", default='["konnect"]', help="JSON argv array for installed Konnect stdio binary")
    parser.add_argument("--kicad-cli-command", default='["kicad-cli"]', help="JSON argv array for KiCad CLI")
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    try:
        if not math.isfinite(args.timeout) or args.timeout <= 0:
            raise SchematicError("timeout must be positive")
        if args.receipt.suffix != ".json" or args.receipt.is_symlink() or args.receipt.resolve() == args.request.resolve():
            raise SchematicError("receipt must be a separate regular JSON output path")
        if args.receipt.exists() and not args.receipt.is_file():
            raise SchematicError("receipt output is not a regular file")
        if not args.receipt.parent.is_dir():
            raise SchematicError("receipt output directory must already exist")
        receipt = apply(args.schematic, json.loads(args.request.read_text()), command(args.konnect_command),
                        command(args.kicad_cli_command), args.timeout)
        args.receipt.write_text(json.dumps(receipt, indent=2) + "\n")
    except (SchematicError, OSError, json.JSONDecodeError) as exc:
        parser.exit(1, f"error: {exc}\n")
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
