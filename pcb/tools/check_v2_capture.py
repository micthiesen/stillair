#!/usr/bin/env python3
"""Compare PCB-01 V2's exported schematic netlist with its frozen specification.

The specification remains authoritative. This checker parses the component schedule and
named-net tables directly from docs/pcb-01-v2.md, so capture validation does not depend on a
second hand-maintained ratsnest. Export a KiCad s-expression netlist first:

    kicad-cli sch export netlist -o /tmp/pcb-01-v2.net \
      pcb/pcb-01-v2/pcb-01-v2.kicad_sch
    python3 pcb/tools/check_v2_capture.py /tmp/pcb-01-v2.net

Mounting holes H1-H4 are board-only mechanics and are excluded from schematic parity.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "docs" / "pcb-01-v2.md"


def expand_refs(text: str) -> set[str]:
    refs: set[str] = set()
    for item in text.replace("`", "").split(","):
        item = item.strip()
        match = re.fullmatch(r"([A-Z]+)(\d+)(?:-([A-Z]+)?(\d+))?", item)
        if not match:
            continue
        prefix, start_s, end_prefix, end_s = match.groups()
        start = int(start_s)
        if end_s is None:
            refs.add(f"{prefix}{start}")
            continue
        if end_prefix and end_prefix != prefix:
            raise ValueError(f"mixed-prefix reference range: {item}")
        end = int(end_s)
        refs.update(f"{prefix}{number}" for number in range(start, end + 1))
    return refs


def markdown_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def scheduled_refs(spec: str) -> tuple[set[str], set[str]]:
    section = spec.split("## Exact component schedule", 1)[1].split(
        "## Exact connectivity and ratsnest", 1
    )[0]
    schematic: set[str] = set()
    mechanical: set[str] = set()
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        cells = markdown_cells(line)
        if not cells or not re.match(r"^[A-Z]+\d", cells[0].replace("`", "")):
            continue
        refs = expand_refs(cells[0])
        for ref in refs:
            (mechanical if ref.startswith("H") else schematic).add(ref)
    return schematic, mechanical


ENDPOINT = re.compile(
    r"\b([A-Z]+)(\d+)\.(\d+)(?:-((?:[A-Z]+\d+\.)?\d+))?(?:/tab)?"
)


def expand_endpoints(text: str) -> set[str]:
    endpoints: set[str] = set()
    for match in ENDPOINT.finditer(text.replace("`", "")):
        prefix, ref_s, pin_s, tail = match.groups()
        ref_number = int(ref_s)
        pin_number = int(pin_s)
        if tail is None:
            endpoints.add(f"{prefix}{ref_number}.{pin_number}")
            continue
        if "." not in tail:
            end_pin = int(tail)
            endpoints.update(
                f"{prefix}{ref_number}.{pin}"
                for pin in range(pin_number, end_pin + 1)
            )
            continue
        end_ref_text, end_pin_text = tail.split(".", 1)
        end_match = re.fullmatch(r"([A-Z]+)(\d+)", end_ref_text)
        if not end_match:
            raise ValueError(f"invalid endpoint range tail: {match.group(0)}")
        end_prefix, end_ref_s = end_match.groups()
        end_ref_number = int(end_ref_s)
        end_pin = int(end_pin_text)
        if end_prefix != prefix:
            raise ValueError(f"mixed-prefix endpoint range: {match.group(0)}")
        if end_ref_number == ref_number:
            endpoints.update(
                f"{prefix}{ref_number}.{pin}"
                for pin in range(pin_number, end_pin + 1)
            )
        elif end_pin == pin_number:
            endpoints.update(
                f"{prefix}{number}.{pin_number}"
                for number in range(ref_number, end_ref_number + 1)
            )
        else:
            raise ValueError(f"ambiguous endpoint range: {match.group(0)}")
    return endpoints


def expected_nets(spec: str, refs: set[str]) -> dict[str, set[str]]:
    section = spec.split("## Exact connectivity and ratsnest", 1)[1].split(
        "## Test and service access", 1
    )[0]
    nets: dict[str, set[str]] = {}
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        cells = markdown_cells(line)
        if len(cells) != 2:
            continue
        net = cells[0].replace("`", "")
        if not re.fullmatch(r"[+/A-Z0-9_]+", net):
            continue
        endpoints = expand_endpoints(cells[1])
        if endpoints:
            nets[net] = endpoints

    assigned = {endpoint for endpoints in nets.values() for endpoint in endpoints}
    for ref in refs:
        if ref.startswith("C") and f"{ref}.2" not in assigned:
            nets.setdefault("AGND", set()).add(f"{ref}.2")
    return nets


def balanced_items(text: str, head: str) -> list[str]:
    items: list[str] = []
    cursor = 0
    while True:
        start = text.find(head, cursor)
        if start < 0:
            return items
        depth = 0
        end = start
        quoted = False
        escaped = False
        while end < len(text):
            char = text[end]
            if quoted:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    quoted = False
            elif char == '"':
                quoted = True
            elif char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    items.append(text[start : end + 1])
                    cursor = end + 1
                    break
            end += 1
        else:
            raise ValueError(f"unterminated item starting with {head!r}")


def actual_netlist(path: Path) -> tuple[set[str], dict[str, set[str]]]:
    text = path.read_text()
    components_section = text.split("\n\t(components", 1)[1].split("\n\t(libparts", 1)[0]
    refs = {
        match.group(1)
        for block in balanced_items(components_section, "(comp")
        if (match := re.search(r'\(ref "([^"]+)"\)', block))
    }

    nets_section = text.split("\n\t(nets", 1)[1]
    nets: dict[str, set[str]] = {}
    for block in balanced_items(nets_section, "(net"):
        name_match = re.search(r'\(name "([^"]+)"\)', block)
        if not name_match:
            continue
        endpoints = set()
        for node in balanced_items(block, "(node"):
            ref_match = re.search(r'\(ref "([^"]+)"\)', node)
            pin_match = re.search(r'\(pin "([^"]+)"\)', node)
            if ref_match and pin_match:
                endpoints.add(f"{ref_match.group(1)}.{pin_match.group(1)}")
        nets[name_match.group(1)] = endpoints
    return refs, nets


def report_set(title: str, values: set[str]) -> int:
    if not values:
        return 0
    print(f"{title} ({len(values)}):")
    print("  " + ", ".join(sorted(values)))
    return len(values)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("netlist", type=Path)
    args = parser.parse_args()

    spec = SPEC.read_text()
    expected_refs, mechanical_refs = scheduled_refs(spec)
    expected = expected_nets(spec, expected_refs)
    actual_refs, actual = actual_netlist(args.netlist)
    actual = {
        name: endpoints
        for name, endpoints in actual.items()
        if not name.startswith("unconnected-(")
    }

    failures = 0
    failures += report_set("Missing schematic references", expected_refs - actual_refs)
    failures += report_set("Unexpected schematic references", actual_refs - expected_refs)

    for name in sorted(expected):
        wanted = expected[name]
        present = actual.get(name, set())
        failures += report_set(f"{name}: missing endpoints", wanted - present)
        failures += report_set(f"{name}: unexpected endpoints", present - wanted)
    failures += report_set("Unexpected named nets", set(actual) - set(expected))

    print(
        f"Checked {len(expected_refs)} schematic refs, {len(mechanical_refs)} board-only refs, "
        f"{len(expected)} named nets, and {sum(map(len, expected.values()))} endpoints."
    )
    if failures:
        print(f"FAIL: {failures} parity differences")
        return 1
    print("PASS: exported schematic matches the frozen PCB-01 V2 schedule and ratsnest")
    return 0


if __name__ == "__main__":
    sys.exit(main())
