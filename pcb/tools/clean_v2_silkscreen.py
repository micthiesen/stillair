#!/usr/bin/env python3
"""Apply the intentional PCB-01 V2 production silkscreen cleanup.

The cleanup keeps functional labels, removes orphaned one-character assembly
markers, and hides references that cannot be printed legibly in the dense USB
front end. KiCad must be closed while this runs.
"""

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pcbnew


KICAD_CLI = Path("/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")
CHECK_DRC = Path(__file__).resolve().with_name("check_drc.py")
MIN_SILK_WIDTH_MM = 0.15
LOGO_GROUP = "STILLAIR_PRODUCTION_SILK_V1"


def point(x: float, y: float) -> pcbnew.VECTOR2I:
    return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def configure_text(
    item: pcbnew.PCB_TEXT,
    text: str,
    x: float,
    y: float,
    *,
    layer: int,
    size: float = 1.0,
    thickness: float = MIN_SILK_WIDTH_MM,
    angle: float = 0.0,
) -> None:
    item.SetText(text)
    item.SetPosition(point(x, y))
    item.SetTextAngleDegrees(angle)
    item.SetTextSize(point(size, size))
    item.SetTextThickness(pcbnew.FromMM(thickness))
    item.SetLayer(layer)
    item.SetMirrored(layer == pcbnew.B_SilkS)


def ensure_board_text(
    board: pcbnew.BOARD,
    aliases: set[str],
    desired: str,
    x: float,
    y: float,
    *,
    layer: int,
    size: float = 1.0,
    thickness: float = MIN_SILK_WIDTH_MM,
    angle: float = 0.0,
) -> pcbnew.PCB_TEXT:
    matches = [
        item
        for item in board.GetDrawings()
        if isinstance(item, pcbnew.PCB_TEXT) and item.GetText() in aliases | {desired}
    ]
    if len(matches) > 1:
        raise SystemExit(f"found multiple silk labels for {desired!r}")
    item = matches[0] if matches else pcbnew.PCB_TEXT(board)
    if not matches:
        board.Add(item)
    configure_text(
        item,
        desired,
        x,
        y,
        layer=layer,
        size=size,
        thickness=thickness,
        angle=angle,
    )
    return item


def add_line(
    board: pcbnew.BOARD,
    group: pcbnew.PCB_GROUP,
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    layer: int,
    width: float = 0.20,
) -> None:
    shape = pcbnew.PCB_SHAPE(board)
    shape.SetShape(pcbnew.SHAPE_T_SEGMENT)
    shape.SetStart(point(*start))
    shape.SetEnd(point(*end))
    shape.SetWidth(pcbnew.FromMM(width))
    shape.SetLayer(layer)
    board.Add(shape)
    group.AddItem(shape)


def add_circle(
    board: pcbnew.BOARD,
    group: pcbnew.PCB_GROUP,
    center: tuple[float, float],
    radius: float,
    *,
    layer: int,
    width: float = 0.20,
    filled: bool = False,
) -> None:
    shape = pcbnew.PCB_SHAPE(board)
    shape.SetShape(pcbnew.SHAPE_T_CIRCLE)
    shape.SetCenter(point(*center))
    shape.SetEnd(point(center[0] + radius, center[1]))
    shape.SetWidth(pcbnew.FromMM(width))
    shape.SetFilled(filled)
    shape.SetLayer(layer)
    board.Add(shape)
    group.AddItem(shape)


def add_pin1_dot(
    board: pcbnew.BOARD,
    group: pcbnew.PCB_GROUP,
    footprint: pcbnew.FOOTPRINT,
) -> None:
    pads = [pad for pad in footprint.Pads() if pad.GetNumber() == "1"]
    if len(pads) != 1:
        raise SystemExit(
            f"expected one pin-1 pad on {footprint.GetReference()}, found {len(pads)}"
        )
    center = footprint.GetPosition()
    pad = pads[0].GetPosition()
    dx = pcbnew.ToMM(pad.x - center.x)
    dy = pcbnew.ToMM(pad.y - center.y)
    length = math.hypot(dx, dy)
    if length == 0:
        raise SystemExit(f"pin 1 is centered on {footprint.GetReference()}")
    offset = 0.70
    x = pcbnew.ToMM(pad.x) + offset * dx / length
    y = pcbnew.ToMM(pad.y) + offset * dy / length
    add_circle(
        board,
        group,
        (x, y),
        0.25,
        layer=pcbnew.F_SilkS,
        width=0.20,
        filled=True,
    )


def rebuild_owned_graphics(board: pcbnew.BOARD, footprints: dict[str, pcbnew.FOOTPRINT]) -> None:
    groups = [group for group in board.Groups() if group.GetName() == LOGO_GROUP]
    if len(groups) > 1:
        raise SystemExit(f"found multiple {LOGO_GROUP} groups")
    if groups:
        members = list(groups[0].GetItems())
        if len(members) != 12:
            raise SystemExit(
                f"{LOGO_GROUP} is incomplete: expected 12 members, found {len(members)}"
            )
        return

    group = pcbnew.PCB_GROUP(board)
    group.SetName(LOGO_GROUP)
    board.Add(group)

    # Three compact outlined blades and a hub form the project-owned fan mark.
    cx, cy = 78.0, 57.0
    add_circle(board, group, (cx, cy), 0.45, layer=pcbnew.B_SilkS)
    for angle_deg in (0.0, 120.0, 240.0):
        a = math.radians(angle_deg)
        p1 = (cx + 0.55 * math.cos(a - 0.30), cy + 0.55 * math.sin(a - 0.30))
        p2 = (cx + 2.15 * math.cos(a + 0.05), cy + 2.15 * math.sin(a + 0.05))
        p3 = (cx + 1.55 * math.cos(a + 0.55), cy + 1.55 * math.sin(a + 0.55))
        add_line(board, group, p1, p2, layer=pcbnew.B_SilkS)
        add_line(board, group, p2, p3, layer=pcbnew.B_SilkS)
        add_line(board, group, p3, p1, layer=pcbnew.B_SilkS)

    add_pin1_dot(board, group, footprints["U1"])
    add_pin1_dot(board, group, footprints["U8"])


def enforce_minimum_silk(board: pcbnew.BOARD) -> None:
    minimum = pcbnew.FromMM(MIN_SILK_WIDTH_MM)
    for item in board.GetDrawings():
        if item.GetLayer() not in {pcbnew.F_SilkS, pcbnew.B_SilkS}:
            continue
        if isinstance(item, pcbnew.PCB_TEXT) and item.GetTextThickness() < minimum:
            item.SetTextThickness(minimum)
        elif isinstance(item, pcbnew.PCB_SHAPE) and item.GetWidth() < minimum:
            item.SetWidth(minimum)
    for footprint in board.GetFootprints():
        ref = footprint.Reference()
        if ref.IsVisible() and ref.GetLayer() in {pcbnew.F_SilkS, pcbnew.B_SilkS}:
            if ref.GetTextThickness() < minimum:
                ref.SetTextThickness(minimum)
        value = footprint.Value()
        if value.IsVisible() and value.GetLayer() in {pcbnew.F_SilkS, pcbnew.B_SilkS}:
            if value.GetTextThickness() < minimum:
                value.SetTextThickness(minimum)
        for item in footprint.GraphicalItems():
            if item.GetLayer() not in {pcbnew.F_SilkS, pcbnew.B_SilkS}:
                continue
            if hasattr(item, "GetTextThickness") and item.GetTextThickness() < minimum:
                item.SetTextThickness(minimum)
            elif isinstance(item, pcbnew.PCB_SHAPE) and item.GetWidth() < minimum:
                item.SetWidth(minimum)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("board", type=Path)
    args = parser.parse_args()
    board_path = args.board.resolve()

    if subprocess.run(["pgrep", "-x", "pcbnew"], capture_output=True).returncode == 0:
        raise SystemExit("KiCad PCB Editor is open; close it before changing silkscreen")

    source_hash = file_hash(board_path)

    with tempfile.TemporaryDirectory(prefix="stillair-clean-silk-") as tmp:
        stage_dir = Path(tmp)
        staged_board = stage_dir / board_path.name
        for suffix in (".kicad_pcb", ".kicad_pro", ".kicad_dru"):
            source = board_path.with_suffix(suffix)
            if source.exists():
                shutil.copy2(source, stage_dir / source.name)
        board = pcbnew.LoadBoard(str(board_path))
        footprints = {fp.GetReference(): fp for fp in board.GetFootprints()}
        drawings = list(board.GetDrawings())

        hidden_refs = {"J4", "U13", "U14", "R58", "R59", "R60", "R61", "C44", "C45"}
        missing = sorted(hidden_refs - footprints.keys())
        if missing:
            raise SystemExit(f"missing expected footprints: {', '.join(missing)}")
        for ref in hidden_refs:
            footprints[ref].Reference().SetVisible(False)

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
            elif label in {"ANTENNA", "ANTENNA KEEP CLEAR", "ANTENNA\nKEEP CLEAR"}:
                item.SetText("ANTENNA\nKEEP CLEAR")
                item.SetPosition(point(136.5, 78.5))
                item.SetTextAngleDegrees(90.0)
                item.SetLayer(pcbnew.F_SilkS)
                item.SetMirrored(False)
                seen.add("ANTENNA")
            elif label in text_moves:
                new_label, x, y, angle = text_moves[label]
                item.SetText(new_label)
                item.SetPosition(point(x, y))
                item.SetTextAngleDegrees(angle)
                item.SetLayer(pcbnew.F_SilkS)
                item.SetMirrored(False)
                seen.add(label)
        missing_text = sorted((text_moves.keys() | {"ANTENNA"}) - seen)
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
                item.SetTextThickness(pcbnew.FromMM(MIN_SILK_WIDTH_MM))
                compact_seen.add(label)
            elif label in {"J1 POWER", "J1 POWER\n1:+24 2:PGND"}:
                item.SetText("J1 POWER\n1:+24 2:PGND")
                item.SetPosition(point(62.0, 70.2))
                item.SetTextSize(point(0.8, 0.8))
                item.SetTextThickness(pcbnew.FromMM(MIN_SILK_WIDTH_MM))
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
                "text": "J2 MOTOR",
                "x": 97.5,
                "y": 105.0,
                "angle": 90.0,
            },
            "J3": {
                "aliases": {"J3 HALL", "J3 HALL\n1:3V3"},
                "text": "J3 HALL",
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
            label.SetTextThickness(pcbnew.FromMM(MIN_SILK_WIDTH_MM))
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
        pinout.SetTextThickness(pcbnew.FromMM(MIN_SILK_WIDTH_MM))
        pinout.SetMirrored(True)

        bottom_labels = {
            "TP18 SDA": (94.0, 81.0),
            "TP19 SCL": (94.0, 84.0),
            "TP20 FG": (94.0, 87.0),
            "J2 3:U 2:V 1:W": (104.0, 106.0),
            "PHASES: DIFF PROBE ONLY": (105.0, 110.0),
        }
        for label, (x, y) in bottom_labels.items():
            ensure_board_text(
                board,
                set(),
                label,
                x,
                y,
                layer=pcbnew.B_SilkS,
                size=0.8,
            )

        ensure_board_text(
            board,
            {"PCB-01 V2 TEST POINT MAP"},
            "PCB-01 V2 TEST POINT MAP",
            101.0,
            60.0,
            layer=pcbnew.B_SilkS,
            size=0.9,
        )
        ensure_board_text(
            board,
            set(),
            "STILLAIR",
            86.5,
            57.0,
            layer=pcbnew.B_SilkS,
            size=1.4,
            thickness=0.20,
        )
        ensure_board_text(
            board,
            set(),
            "U8 PIN 1",
            119.0,
            87.0,
            layer=pcbnew.B_SilkS,
            size=0.8,
        )

        rebuild_owned_graphics(board, footprints)
        enforce_minimum_silk(board)

        pcbnew.SaveBoard(str(staged_board), board)
        pcbnew.LoadBoard(str(staged_board))
        verify = subprocess.run(
            [
                str(KICAD_CLI),
                "pcb",
                "drc",
                "--format",
                "json",
                "--output",
                str(stage_dir / "drc.json"),
                str(staged_board),
            ],
            capture_output=True,
            text=True,
        )
        output = verify.stdout + verify.stderr
        if "Failed to load board" in output or verify.returncode == 3:
            raise SystemExit("silkscreen cleanup produced an unreadable staged board")
        report = json.loads((stage_dir / "drc.json").read_text())
        silk_types = {
            "silk_edge_clearance",
            "silk_over_copper",
            "silk_overlap",
            "text_height",
            "text_thickness",
        }
        silk_findings = [
            violation
            for violation in report.get("violations", [])
            if violation.get("type") in silk_types
        ]
        if silk_findings:
            details = []
            for finding in silk_findings:
                items = "; ".join(
                    f"{item.get('description', 'item')} @ {item.get('pos', {})}"
                    for item in finding.get("items", [])
                )
                details.append(
                    f"{finding.get('type')}: {finding.get('description', '')} [{items}]"
                )
            raise SystemExit(
                f"staged silkscreen has {len(silk_findings)} DRC finding(s):\n"
                + "\n".join(details)
            )

        project_check = subprocess.run(
            [str(CHECK_DRC), str(staged_board)],
            capture_output=True,
            text=True,
        )
        if project_check.returncode != 0:
            raise SystemExit(
                "staged board failed reviewed DRC:\n"
                + project_check.stdout
                + project_check.stderr
            )
        if file_hash(board_path) != source_hash:
            raise SystemExit("source board changed while staged silkscreen was being validated")
        os.replace(staged_board, board_path)

    print(f"cleaned production silkscreen in {board_path}")


if __name__ == "__main__":
    main()
