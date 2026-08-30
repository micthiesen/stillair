#!/usr/bin/env python3
"""Trim PCB-01 V2's B.Cu AGND plane out of the power and motor regions.

The concave boundary preserves the analog/control return plane and the U1
exposed-pad area while keeping the single AGND/PGND connection at NT1.
KiCad must be closed while this runs.
"""

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

import pcbnew


KICAD_CLI = Path("/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")
ZONE_NAME = "B.Cu AGND plane"
OUTLINE = (
    (50.3, 50.3),
    (137.6, 50.3),
    (137.6, 113.7),
    (93.2, 113.7),
    (93.2, 96.6),
    (81.1, 96.6),
    (81.1, 86.5),
    (82.9, 86.5),
    (82.9, 84.7),
    (80.3, 84.7),
    (80.3, 59.7),
    (50.3, 59.7),
)


def point(x: float, y: float) -> pcbnew.VECTOR2I:
    return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("board", type=Path)
    args = parser.parse_args()
    board_path = args.board.resolve()

    with tempfile.TemporaryDirectory(prefix="stillair-trim-agnd-") as tmp:
        backup = Path(tmp) / board_path.name
        shutil.copy2(board_path, backup)
        board = pcbnew.LoadBoard(str(board_path))
        matches = [zone for zone in board.Zones() if zone.GetZoneName() == ZONE_NAME]
        if len(matches) != 1:
            raise SystemExit(f"expected one zone named {ZONE_NAME!r}, found {len(matches)}")

        zone = matches[0]
        if zone.GetLayer() != pcbnew.B_Cu or zone.GetNetname() != "AGND":
            raise SystemExit(f"{ZONE_NAME!r} is not the expected B.Cu AGND zone")
        zone.RemoveAllContours()
        outline = zone.Outline()
        index = outline.NewOutline()
        for x, y in OUTLINE:
            outline.Append(point(x, y), index)

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
            raise SystemExit("AGND trim produced an unreadable board; original restored")

    print(f"trimmed {ZONE_NAME} in {board_path}")


if __name__ == "__main__":
    main()
