#!/usr/bin/env python3
"""Apply the intentional PCB-01 V2 production silkscreen cleanup.

The cleanup keeps functional labels, removes orphaned one-character assembly
markers, and hides references that cannot be printed legibly in the dense USB
front end. KiCad must be closed while this runs.
"""

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

import pcbnew


KICAD_CLI = Path("/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")


def point(x: float, y: float) -> pcbnew.VECTOR2I:
    return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("board", type=Path)
    args = parser.parse_args()
    board_path = args.board.resolve()

    with tempfile.TemporaryDirectory(prefix="stillair-clean-silk-") as tmp:
        backup = Path(tmp) / board_path.name
        shutil.copy2(board_path, backup)
        board = pcbnew.LoadBoard(str(board_path))
        footprints = {fp.GetReference(): fp for fp in board.GetFootprints()}
        drawings = board.GetDrawings()

        hidden_refs = {"J4", "U13", "U14", "R58", "R59", "R60", "R61", "C44", "C45"}
        missing = sorted(hidden_refs - footprints.keys())
        if missing:
            raise SystemExit(f"missing expected footprints: {', '.join(missing)}")
        for ref in hidden_refs:
            footprints[ref].Reference().SetVisible(False)

        # U1's vendor body rectangle lies over every perimeter pad, so it cannot
        # be manufactured on silkscreen. Courtyard and Fab outlines remain.
        u1 = footprints["U1"]
        for item in list(u1.GraphicalItems()):
            if item.GetLayer() == pcbnew.F_SilkS:
                u1.Remove(item)

        # The old standalone K and 1 markers were detached from their parts and
        # visually ambiguous. Footprint-native polarity and pin-1 marks remain.
        for item in drawings:
            if isinstance(item, pcbnew.PCB_TEXT) and item.GetText() in {"K", "1"}:
                board.Remove(item)

        text_moves = {
            "RESET": ("RESET", 98.8, 70.8, 90.0),
            "BOOT": ("BOOT", 103.5, 72.0, 0.0),
            "SDA": ("SDA", 68.0, 109.5, 0.0),
            "SCL": ("SCL", 74.0, 109.0, 0.0),
            "FG": ("FG", 79.5, 109.5, 0.0),
            "CLEAR": ("CLEAR", 105.2, 110.0, 90.0),
            "USB DATA ONLY": ("USB DATA ONLY", 120.2, 55.5, 90.0),
            "J1 24V REQD": ("J1 24V REQD", 121.5, 55.5, 90.0),
        }
        seen = set()
        for item in drawings:
            if not isinstance(item, pcbnew.PCB_TEXT):
                continue
            label = item.GetText()
            if label in {
                "TP18",
                "TP19",
                "TP20",
                "DIFF PROBE ONLY",
                "3:U 2:V 1:W",
            }:
                board.Remove(item)
            elif label in text_moves:
                new_label, x, y, angle = text_moves[label]
                item.SetText(new_label)
                item.SetPosition(point(x, y))
                item.SetTextAngleDegrees(angle)
                item.SetLayer(pcbnew.F_SilkS)
                item.SetMirrored(False)
                seen.add(label)
        missing_text = sorted(text_moves.keys() - seen)
        if missing_text:
            raise SystemExit(f"missing expected board text: {', '.join(missing_text)}")

        compact_top_labels = {
            "TP9",
            "TP10",
            "TP11",
            "TP12",
            "TP13",
            "TP14",
            "TP16",
            "TP30",
            "TP31",
        }
        compact_seen = set()
        j1_seen = False
        for item in list(board.GetDrawings()):
            if not isinstance(item, pcbnew.PCB_TEXT):
                continue
            label = item.GetText()
            if label in compact_top_labels and item.GetLayer() == pcbnew.F_SilkS:
                item.SetTextSize(point(0.8, 0.8))
                item.SetTextThickness(pcbnew.FromMM(0.12))
                compact_seen.add(label)
            elif label in {"J1 POWER", "J1 POWER\n1:+24 2:PGND"}:
                item.SetText("J1 POWER\n1:+24 2:PGND")
                item.SetPosition(point(62.0, 70.2))
                item.SetTextSize(point(0.8, 0.8))
                item.SetTextThickness(pcbnew.FromMM(0.12))
                j1_seen = True
            elif label == "1:+24 2:PGND":
                board.Remove(item)
        if compact_seen != compact_top_labels:
            missing_labels = sorted(compact_top_labels - compact_seen)
            raise SystemExit(f"missing expected top-edge labels: {', '.join(missing_labels)}")
        if not j1_seen:
            raise SystemExit("missing expected J1 POWER label")

        connector_labels = {
            "J2": {
                "aliases": {"J2 MOTOR", "J2 MOTOR\n3:U 2:V 1:W"},
                "text": "J2 MOTOR\n3:U 2:V 1:W",
                "x": 97.5,
                "y": 105.0,
                "angle": 90.0,
            },
            "J3": {
                "aliases": {"J3 HALL", "J3 HALL\n1:3V3"},
                "text": "J3 HALL\n1:3V3",
                "x": 128.0,
                "y": 104.0,
                "angle": 0.0,
            },
        }
        for name, config in connector_labels.items():
            matches = [
                item
                for item in board.GetDrawings()
                if isinstance(item, pcbnew.PCB_TEXT) and item.GetText() in config["aliases"]
            ]
            if len(matches) != 1:
                raise SystemExit(f"expected one {name} connector label, found {len(matches)}")
            label = matches[0]
            label.SetText(config["text"])
            label.SetPosition(point(config["x"], config["y"]))
            label.SetTextAngleDegrees(config["angle"])
            label.SetTextSize(point(0.8, 0.8))
            label.SetTextThickness(pcbnew.FromMM(0.12))
            label.SetLayer(pcbnew.F_SilkS)
            label.SetMirrored(False)

        # Preserve J3's required signal-order marking on the uncluttered back
        # silkscreen. It remains readable before connector installation without
        # consuming the compact tach-supply routing channel on the front.
        pinout_text = "1:3V3 2:HALL 3:GND"
        pinout_items = [
            item
            for item in board.GetDrawings()
            if isinstance(item, pcbnew.PCB_TEXT) and item.GetText() == pinout_text
        ]
        if len(pinout_items) > 1:
            raise SystemExit(f"found multiple {pinout_text!r} labels")
        if pinout_items:
            pinout = pinout_items[0]
        else:
            pinout = pcbnew.PCB_TEXT(board)
            pinout.SetText(pinout_text)
            board.Add(pinout)
        pinout.SetLayer(pcbnew.B_SilkS)
        pinout.SetPosition(point(118.0, 106.5))
        pinout.SetTextAngleDegrees(0.0)
        pinout.SetTextSize(point(0.8, 0.8))
        pinout.SetTextThickness(pcbnew.FromMM(0.12))
        pinout.SetMirrored(True)

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
            raise SystemExit("silkscreen cleanup produced an unreadable board; original restored")

    print(f"cleaned production silkscreen in {board_path}")


if __name__ == "__main__":
    main()
