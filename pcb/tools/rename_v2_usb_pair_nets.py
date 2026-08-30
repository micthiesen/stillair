#!/usr/bin/env python3
"""Give both PCB-01 V2 USB segments KiCad differential-pair suffixes.

The schematic labels are changed through Konnect first. This companion updates
the existing board net objects without changing any pad membership or routing.
KiCad must be closed while this runs.
"""

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

import pcbnew


KICAD_CLI = Path("/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")
RENAMES = {
    "/SCH-04 Supervisor + Service/USB_DP_MCU": "/SCH-04 Supervisor + Service/USB_D_MCU_P",
    "/SCH-04 Supervisor + Service/USB_DN_MCU": "/SCH-04 Supervisor + Service/USB_D_MCU_N",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("board", type=Path)
    args = parser.parse_args()
    board_path = args.board.resolve()

    with tempfile.TemporaryDirectory(prefix="stillair-usb-net-rename-") as tmp:
        backup = Path(tmp) / board_path.name
        shutil.copy2(board_path, backup)
        board = pcbnew.LoadBoard(str(board_path))
        nets = board.GetNetsByName()
        for old, new in RENAMES.items():
            if new in nets and old not in nets:
                continue
            if old not in nets:
                raise SystemExit(f"missing expected board net {old!r}")
            if new in nets:
                raise SystemExit(f"both old and new board nets exist for {old!r}")
            nets[old].SetNetname(new)

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
            raise SystemExit("USB net rename produced an unreadable board; original restored")

    print(f"renamed {len(RENAMES)} USB pair nets in {board_path}")


if __name__ == "__main__":
    main()
