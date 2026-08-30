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


def approved_exception(violation: dict[str, Any]) -> str | None:
    """Return the waiver rationale only for one exact approved finding."""
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
