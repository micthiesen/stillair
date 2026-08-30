#!/usr/bin/env python3
"""Create PCB-01 V2's compact F.Cu VM24 landing beside U1.

The landing gives U1.9-U1.11 and the nearby VM24 capacitors a broad local
connection, then drops into the In2 VM24 plane through three power vias.
KiCad must be closed while this runs.
"""

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

import pcbnew


KICAD_CLI = Path("/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")
ZONE_NAME = "F.Cu U1 VM24 landing"
OUTLINE = (
    (77.25, 92.95),
    (79.10, 92.95),
    (79.10, 94.40),
    (79.45, 94.80),
    (82.05, 94.80),
    (82.05, 96.55),
    (81.00, 96.55),
    (81.00, 99.70),
    (78.20, 99.70),
    (78.20, 94.25),
    (77.25, 94.05),
)
VIA_POSITIONS = ((79.75, 95.75), (79.75, 97.50), (79.75, 99.25))
LEGACY_VIA_POSITIONS = ((79.75, 96.00), (79.75, 97.00), (79.75, 98.00))


def mm(value: float) -> int:
    return pcbnew.FromMM(value)


def point(x: float, y: float) -> pcbnew.VECTOR2I:
    return pcbnew.VECTOR2I(mm(x), mm(y))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("board", type=Path)
    args = parser.parse_args()
    board_path = args.board.resolve()

    with tempfile.TemporaryDirectory(prefix="stillair-u1-vm24-landing-") as tmp:
        backup = Path(tmp) / board_path.name
        shutil.copy2(board_path, backup)
        board = pcbnew.LoadBoard(str(board_path))
        nets = board.GetNetsByName()
        vm24 = nets["VM24"]

        matches = [zone for zone in board.Zones() if zone.GetZoneName() == ZONE_NAME]
        if len(matches) > 1:
            raise SystemExit(f"found multiple zones named {ZONE_NAME!r}")
        zone = matches[0] if matches else pcbnew.ZONE(board)
        zone.SetZoneName(ZONE_NAME)
        zone.SetLayer(pcbnew.F_Cu)
        zone.SetNet(vm24)
        zone.SetAssignedPriority(8)
        zone.SetLocalClearance(mm(0.25))
        zone.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        zone.SetMinThickness(mm(0.25))
        zone.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        zone.RemoveAllContours()
        outline = zone.Outline()
        index = outline.NewOutline()
        for x, y in OUTLINE:
            outline.Append(point(x, y), index)
        if not matches:
            board.Add(zone)

        existing = list(board.GetTracks())
        legacy_positions = [point(x, y) for x, y in LEGACY_VIA_POSITIONS]
        for item in existing[:]:
            if (
                isinstance(item, pcbnew.PCB_VIA)
                and item.GetNetname() == "VM24"
                and any(item.GetPosition() == position for position in legacy_positions)
            ):
                board.Remove(item)
                existing.remove(item)

        added_vias = 0
        for x, y in VIA_POSITIONS:
            position = point(x, y)
            duplicate = any(
                isinstance(item, pcbnew.PCB_VIA)
                and item.GetPosition() == position
                and item.GetNetname() == "VM24"
                for item in existing
            )
            if duplicate:
                continue
            via = pcbnew.PCB_VIA(board)
            via.SetPosition(position)
            via.SetWidth(mm(1.00))
            via.SetDrill(mm(0.50))
            via.SetNet(vm24)
            board.Add(via)
            existing.append(via)
            added_vias += 1

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
            raise SystemExit("VM24 landing produced an unreadable board; original restored")

    print(f"created {ZONE_NAME}; added {added_vias} vias in {board_path}")


if __name__ == "__main__":
    main()
