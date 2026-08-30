#!/usr/bin/env python3
"""Create the PCB-01 V2 U2 exposed-pad AGND island on In2.Cu.

The higher-priority island prevents the surrounding 3V3 plane from leaving an
isolated sliver between U2's exposed-pad ground vias. KiCad must be closed.
"""

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

import pcbnew


KICAD_CLI = Path("/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")
ZONE_NAME = "In2 U2 EP AGND island"


def point(x: float, y: float) -> pcbnew.VECTOR2I:
    return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("board", type=Path)
    args = parser.parse_args()
    board_path = args.board.resolve()

    with tempfile.TemporaryDirectory(prefix="stillair-u2-ep-zone-") as tmp:
        backup = Path(tmp) / board_path.name
        shutil.copy2(board_path, backup)
        board = pcbnew.LoadBoard(str(board_path))
        nets = board.GetNetsByName()
        matches = [zone for zone in board.Zones() if zone.GetZoneName() == ZONE_NAME]
        if len(matches) > 1:
            raise SystemExit(f"found multiple zones named {ZONE_NAME!r}")

        zone = matches[0] if matches else pcbnew.ZONE(board)
        zone.SetZoneName(ZONE_NAME)
        zone.SetLayer(pcbnew.In2_Cu)
        zone.SetNet(nets["AGND"])
        zone.SetAssignedPriority(7)
        zone.SetLocalClearance(pcbnew.FromMM(0.25))
        zone.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        zone.SetMinThickness(pcbnew.FromMM(0.25))
        zone.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        zone.RemoveAllContours()
        outline = zone.Outline()
        index = outline.NewOutline()
        for x, y in ((120.1, 72.05), (123.5, 72.05), (123.5, 75.45), (120.1, 75.45)):
            outline.Append(point(x, y), index)
        if not matches:
            board.Add(zone)

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
            raise SystemExit("U2 EP zone produced an unreadable board; original restored")

    print(f"created {ZONE_NAME} in {board_path}")


if __name__ == "__main__":
    main()
