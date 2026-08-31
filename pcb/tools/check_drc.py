#!/usr/bin/env python3
"""Run KiCad PCB DRC and apply the project's exact, reviewed waivers.

With no argument this checks PCB-01 V2. A check passes only when no active
violations and no unconnected items remain. The raw KiCad report can be kept
with ``--output``; the saved report includes an ``approved_exceptions`` list.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BOARD = ROOT / "pcb" / "pcb-01-v2" / "pcb-01-v2.kicad_pcb"
KICAD_CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"

U1_PGND_ESCAPE_VIAS = {
    "00c9df8f-6534-4f1a-82f6-0c783a800139",
    "382e4761-3678-4adc-b1b2-a4ecf64ef4e7",
    "d8da97b9-c052-4dcd-b5a8-6fd048024160",
}

APPROVED_VIA_FINDINGS = {
    "drill_out_of_range": "actual 0.3000 mm",
    "via_diameter": "actual 0.6000 mm",
}

U1_PGND_REASON = (
    "U1 PGND escape via: 0.60/0.30 mm is required by the 0.50 mm pin pitch; "
    "the 1.5 A motor limit is shared across three PGND returns"
)

# Exact track-width exceptions reviewed against the final routed geometry on
# 2026-08-30.  Keying by UUID keeps this list narrow: a replacement or newly
# narrowed track is not silently accepted even when it occupies the same area.
APPROVED_TRACK_WIDTHS = {
    # U1 PGND pad escapes.  Each neck is no wider than U1's 0.25 mm land and
    # is at most 0.211 mm long before reaching a dedicated PGND escape via.
    "6c310186-ce07-49d0-a796-fc1d41827ef1": (
        "PGND", "0.2500 mm", "U1 PGND pad-width neck to dedicated escape via"
    ),
    "6f30cc55-1880-41cb-9fd2-4ab279c0026b": (
        "PGND", "0.2500 mm", "U1 PGND pad-width neck to dedicated escape via"
    ),
    "fdde0ddb-03b2-4c73-8c31-3a32e7f1bf8e": (
        "PGND", "0.2500 mm", "U1 PGND pad-width neck to dedicated escape via"
    ),
    # NT1 carries only the analog/control return across the deliberate
    # AGND/PGND single-point bridge, not motor phase or bulk-return current.
    "8998e197-ff38-4e28-8de0-94dd3cd115b7": (
        "PGND", "1.5000 mm", "NT1 single-point ground-bridge connection"
    ),
    # Local 3V3 land escapes.  These are bounded by the receiving IC/passive
    # lands and widen immediately; none is a distribution-rail segment.
    "0628982a-c644-4c43-bce3-643d6338f13b": (
        "3V3", "0.2000 mm", "local 3V3 pad escape"
    ),
    "1cbc401b-adab-47c5-b99a-32f11e36808f": (
        "3V3", "0.2500 mm", "local 3V3 pad escape"
    ),
    "30882b3b-d354-4077-92cf-3263c1283d80": (
        "3V3", "0.3000 mm", "local 3V3 pad escape"
    ),
    "35e2d750-3883-40ae-b9c1-73e50b9ffe95": (
        "3V3", "0.3000 mm", "local 3V3 pad escape"
    ),
    "5bdbada6-447b-4356-a8a5-6ecdca8f0e8a": (
        "3V3", "0.3000 mm", "local 3V3 pad escape"
    ),
    "690275af-d416-42dc-9790-7f56bec37253": (
        "3V3", "0.2500 mm", "local 3V3 pad escape"
    ),
    "69183a7d-8b13-4dfb-bfc3-e7591c088ef9": (
        "3V3", "0.2500 mm", "local 3V3 pad escape"
    ),
    "d4cdf896-23d7-43a1-b128-e8387cfd08ad": (
        "3V3", "0.3000 mm", "local 3V3 pad escape"
    ),
    "fe38e5d0-4c37-4e9c-ac88-5a999469d008": (
        "3V3", "0.3000 mm", "local 3V3 pad escape"
    ),
    # C3's two short spokes terminate directly in 1.00/0.50 mm PGND vias.
    "24d16590-2554-42c5-ae7c-9972b35989a9": (
        "PGND", "0.5000 mm", "C3 local PGND capacitor-to-via spoke"
    ),
    "2a4932e8-32aa-4e09-bfe6-558f284e5f9c": (
        "PGND", "0.5000 mm", "C3 local PGND capacitor-to-via spoke"
    ),
}


def approved_exception(violation: dict[str, Any]) -> str | None:
    """Return the waiver rationale only for one exact approved finding."""
    if violation.get("type") == "track_width":
        items = violation.get("items", [])
        if len(items) != 1:
            return None
        item = items[0]
        approved = APPROVED_TRACK_WIDTHS.get(item.get("uuid"))
        if approved is None:
            return None
        net, actual_width, reason = approved
        if not item.get("description", "").startswith(f"Track [{net}] "):
            return None
        if f"actual {actual_width}" not in violation.get("description", ""):
            return None
        return reason

    expected_measurement = APPROVED_VIA_FINDINGS.get(violation.get("type"))
    items = violation.get("items", [])
    if expected_measurement is None or len(items) != 1:
        return None
    item = items[0]
    if item.get("uuid") not in U1_PGND_ESCAPE_VIAS:
        return None
    if item.get("description") != "Via [PGND] on F.Cu - B.Cu":
        return None
    if expected_measurement not in violation.get("description", ""):
        return None
    return U1_PGND_REASON


def partition_violations(
    violations: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    active: list[dict[str, Any]] = []
    approved: list[dict[str, Any]] = []
    for violation in violations:
        reason = approved_exception(violation)
        if reason is None:
            active.append(violation)
        else:
            approved.append({**violation, "exception_reason": reason})
    return active, approved


def item_summary(item: dict[str, Any]) -> str:
    position = item.get("pos")
    if not position:
        return item.get("description", "unknown item")
    return (
        f"{item.get('description', 'unknown item')} "
        f"@ {position.get('x')},{position.get('y')}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("board", nargs="?", type=Path, default=DEFAULT_BOARD)
    parser.add_argument(
        "--output",
        type=Path,
        help="write the filtered JSON report to this path",
    )
    args = parser.parse_args()
    board = args.board.resolve()

    with tempfile.TemporaryDirectory(prefix="stillair-drc-") as temp_dir:
        raw_report = Path(temp_dir) / "drc.json"
        subprocess.run(
            [
                KICAD_CLI,
                "pcb",
                "drc",
                "--severity-all",
                "--format",
                "json",
                "--output",
                str(raw_report),
                str(board),
            ],
            check=True,
        )
        report = json.loads(raw_report.read_text())

    active, approved = partition_violations(report.get("violations", []))
    unconnected = report.get("unconnected_items", [])
    report["violations"] = active
    report["approved_exceptions"] = approved

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")

    print(
        f"{board}: {len(active)} active violation(s), "
        f"{len(unconnected)} unconnected item(s), "
        f"{len(approved)} approved exception(s)"
    )
    for violation in active:
        items = " | ".join(item_summary(item) for item in violation.get("items", []))
        print(f"ERROR {violation.get('type', 'unknown')}: {violation.get('description', '')}")
        if items:
            print(f"  {items}")
    if approved:
        print("Approved exceptions:")
        for violation in approved:
            item = violation["items"][0]
            print(
                f"  {violation['type']}: {item_summary(item)} "
                f"[{item['uuid']}]"
            )

    if active or unconnected:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
