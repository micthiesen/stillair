#!/usr/bin/env python3
"""Extend PCB-01 V2's In1 PGND island through the phase-output corridor.

This prevents the surrounding AGND plane from filling beneath the U1-to-J2
phase routes while preserving the sole AGND/PGND connection at NT1. KiCad must
be closed while this runs.
"""

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

import pcbnew


KICAD_CLI = Path("/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")
ZONE_NAME = "In1 PGND island"
RULE_AREA_NAME = "PGND motor routing"
OUTLINE = (
    (50.3, 60.0),
    (74.0, 60.0),
    (74.0, 62.0),
    (78.2, 62.0),
    (78.2, 67.0),
    (74.0, 67.0),
    (74.0, 74.5),
    (80.0, 74.5),
    (80.0, 79.5),
    (74.0, 79.5),
    (74.0, 84.4),
    (77.3, 84.4),
    (77.3, 84.8),
    (82.6, 84.8),
    (82.6, 86.2),
    (80.8, 86.2),
    (80.8, 96.4),
    (82.0, 96.4),
    (82.0, 96.9),
    (92.4, 96.9),
    (92.4, 113.7),
    (80.8, 113.7),
    (80.8, 103.5),
    (76.0, 103.5),
    (76.0, 98.0),
    (77.0, 98.0),
    (77.0, 87.0),
    (50.3, 87.0),
)
RULE_OUTLINE = (
    (50.0, 59.7),
    (80.3, 59.7),
    (80.3, 84.7),
    (82.9, 84.7),
    (82.9, 86.5),
    (81.1, 86.5),
    (81.1, 96.1),
    (82.3, 96.1),
    (82.3, 96.6),
    (92.4, 96.6),
    (92.4, 113.7),
    (80.8, 113.7),
    (80.8, 103.8),
    (75.7, 103.8),
    (75.7, 98.3),
    (50.0, 98.3),
)


def point(x: float, y: float) -> pcbnew.VECTOR2I:
    return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("board", type=Path)
    args = parser.parse_args()
    board_path = args.board.resolve()

    with tempfile.TemporaryDirectory(prefix="stillair-extend-pgnd-") as tmp:
        backup = Path(tmp) / board_path.name
        shutil.copy2(board_path, backup)
        board = pcbnew.LoadBoard(str(board_path))
        matches = [zone for zone in board.Zones() if zone.GetZoneName() == ZONE_NAME]
        if len(matches) != 1:
            raise SystemExit(f"expected one zone named {ZONE_NAME!r}, found {len(matches)}")
        zone = matches[0]
        if zone.GetLayer() != pcbnew.In1_Cu or zone.GetNetname() != "PGND":
            raise SystemExit(f"{ZONE_NAME!r} is not the expected In1.Cu PGND zone")

        zone.RemoveAllContours()
        zone.SetLocalClearance(pcbnew.FromMM(0.30))
        outline = zone.Outline()
        index = outline.NewOutline()
        for x, y in OUTLINE:
            outline.Append(point(x, y), index)

        rule_matches = [zone for zone in board.Zones() if zone.GetZoneName() == RULE_AREA_NAME]
        if len(rule_matches) != 1 or not rule_matches[0].GetIsRuleArea():
            raise SystemExit(f"expected one rule area named {RULE_AREA_NAME!r}")
        rule_area = rule_matches[0]
        rule_area.RemoveAllContours()
        rule_outline = rule_area.Outline()
        rule_index = rule_outline.NewOutline()
        for x, y in RULE_OUTLINE:
            rule_outline.Append(point(x, y), rule_index)

        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
        pcbnew.SaveBoard(str(board_path), board)
        verify = subprocess.run(
            [
                str(KICAD_CLI),
                "pcb",
                "drc",
                "--format",
                "json",
                "--output",
                str(Path(tmp) / "drc.json"),
                str(board_path),
            ],
            capture_output=True,
            text=True,
        )
        output = verify.stdout + verify.stderr
        if "Failed to load board" in output or verify.returncode == 3:
            shutil.copy2(backup, board_path)
            raise SystemExit("PGND extension produced an unreadable board; original restored")

    print(f"extended {ZONE_NAME} in {board_path}")


if __name__ == "__main__":
    main()
