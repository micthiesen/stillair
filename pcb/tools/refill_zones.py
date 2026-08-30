#!/usr/bin/env python3
"""Refill every copper zone in a KiCad board using KiCad's native API.

KiCad must be closed while this runs. The board is saved only after a
successful fill, and the original is restored if KiCad cannot reload it.
"""

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

import pcbnew


KICAD_CLI = Path("/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("board", type=Path)
    parser.add_argument("--zone", help="zone name whose island policy should be updated")
    parser.add_argument(
        "--min-island-area",
        type=float,
        help="remove disconnected fills smaller than this area in square millimetres",
    )
    args = parser.parse_args()
    board_path = args.board.resolve()

    with tempfile.TemporaryDirectory(prefix="stillair-refill-zones-") as tmp:
        backup = Path(tmp) / board_path.name
        shutil.copy2(board_path, backup)

        board = pcbnew.LoadBoard(str(board_path))
        if args.zone or args.min_island_area is not None:
            if not args.zone or args.min_island_area is None:
                raise SystemExit("--zone and --min-island-area must be used together")
            matches = [zone for zone in board.Zones() if zone.GetZoneName() == args.zone]
            if len(matches) != 1:
                raise SystemExit(f"expected one zone named {args.zone!r}, found {len(matches)}")
            matches[0].SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_AREA)
            matches[0].SetMinIslandArea(int(args.min_island_area * 1_000_000_000_000))
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
            raise SystemExit("zone refill produced an unreadable board; original restored")

    print(f"refilled {len(board.Zones())} zones in {board_path}")


if __name__ == "__main__":
    main()
