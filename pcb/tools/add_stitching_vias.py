#!/usr/bin/env python3
"""Add named-net stitching vias to a KiCad board using KiCad's native API.

Input JSON is a list of objects with net, x, y, diameter, and drill values in
millimetres. KiCad must be closed while this runs.
"""

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import pcbnew


KICAD_CLI = Path("/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")


def mm(value: float) -> int:
    return pcbnew.FromMM(value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("board", type=Path)
    parser.add_argument("vias", type=Path)
    parser.add_argument(
        "--replace-all",
        action="store_true",
        help="remove every existing via before adding the requested stitching vias",
    )
    args = parser.parse_args()
    board_path = args.board.resolve()
    requests = json.loads(args.vias.read_text())

    with tempfile.TemporaryDirectory(prefix="stillair-add-vias-") as tmp:
        backup = Path(tmp) / board_path.name
        shutil.copy2(board_path, backup)
        board = pcbnew.LoadBoard(str(board_path))
        nets = board.GetNetsByName()
        existing = list(board.GetTracks())
        added = 0

        if args.replace_all:
            for item in existing[:]:
                if isinstance(item, pcbnew.PCB_VIA):
                    board.Remove(item)
                    existing.remove(item)

        for request in requests:
            net_name = request["net"]
            if net_name not in nets:
                raise SystemExit(f"unknown net: {net_name}")
            x, y = float(request["x"]), float(request["y"])
            point = pcbnew.VECTOR2I(mm(x), mm(y))
            duplicate = any(
                isinstance(item, pcbnew.PCB_VIA)
                and item.GetPosition() == point
                and item.GetNetname() == net_name
                for item in existing
            )
            if duplicate:
                continue

            via = pcbnew.PCB_VIA(board)
            via.SetPosition(point)
            via.SetWidth(mm(float(request["diameter"])))
            via.SetDrill(mm(float(request["drill"])))
            via.SetNet(nets[net_name])
            board.Add(via)
            existing.append(via)
            added += 1

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
            raise SystemExit("via insertion produced an unreadable board; original restored")

    print(f"added {added} stitching vias to {board_path}")


if __name__ == "__main__":
    main()
