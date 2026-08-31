#!/usr/bin/env python3
"""Synchronize reviewed PCB-01 V2 footprint metadata with the schematic source.

This uses pcbnew's file API on a staged copy, validates the result, and atomically
replaces the board only after the reviewed DRC still passes. KiCad must be closed.
"""

import argparse
import hashlib
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pcbnew


CHECK_DRC = Path(__file__).resolve().with_name("check_drc.py")
EXPECTED_VALUES = {"U8": "LM2907M/NOPB"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("board", type=Path)
    args = parser.parse_args()
    board_path = args.board.resolve()

    if subprocess.run(["pgrep", "-x", "pcbnew"], capture_output=True).returncode == 0:
        raise SystemExit("KiCad PCB Editor is open; close it before synchronizing metadata")

    source_hash = digest(board_path)
    with tempfile.TemporaryDirectory(prefix="stillair-v2-release-metadata-") as tmp:
        stage_dir = Path(tmp)
        staged_board = stage_dir / board_path.name
        for suffix in (".kicad_pcb", ".kicad_pro", ".kicad_dru"):
            source = board_path.with_suffix(suffix)
            if source.exists():
                shutil.copy2(source, stage_dir / source.name)

        board = pcbnew.LoadBoard(str(board_path))
        footprints = {fp.GetReference(): fp for fp in board.GetFootprints()}
        missing = sorted(EXPECTED_VALUES.keys() - footprints.keys())
        if missing:
            raise SystemExit(f"missing expected footprint(s): {', '.join(missing)}")
        for reference, value in EXPECTED_VALUES.items():
            footprints[reference].SetValue(value)

        pcbnew.SaveBoard(str(staged_board), board)
        reloaded = pcbnew.LoadBoard(str(staged_board))
        actual = {fp.GetReference(): fp.GetValue() for fp in reloaded.GetFootprints()}
        wrong = {
            reference: (value, actual.get(reference))
            for reference, value in EXPECTED_VALUES.items()
            if actual.get(reference) != value
        }
        if wrong:
            raise SystemExit(f"staged metadata verification failed: {wrong}")

        check = subprocess.run(
            [str(CHECK_DRC), str(staged_board)],
            capture_output=True,
            text=True,
        )
        if check.returncode != 0:
            raise SystemExit("staged board failed reviewed DRC:\n" + check.stdout + check.stderr)
        if digest(board_path) != source_hash:
            raise SystemExit("source board changed while staged metadata was being validated")
        os.replace(staged_board, board_path)

    print(f"synchronized release metadata in {board_path}")


if __name__ == "__main__":
    main()
