#!/usr/bin/env python3
"""Read filled/capped plated-hole coordinates from an actual KiCad footprint."""

import argparse
import json

import pcbnew


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("board")
parser.add_argument("reference")
parser.add_argument("pad")
parser.add_argument("--expected-count", type=int, required=True)
parser.add_argument("--expected-hole-mm", type=float, required=True)
args = parser.parse_args()

board = pcbnew.LoadBoard(args.board)
footprint = board.FindFootprintByReference(args.reference)
if footprint is None:
    raise SystemExit(f"missing footprint {args.reference}")

holes = []
for pad in footprint.Pads():
    drill = pad.GetDrillSize()
    drill_mm = pcbnew.ToMM(min(drill.x, drill.y))
    if pad.GetNumber() != args.pad or drill_mm <= 0:
        continue
    if abs(drill_mm - args.expected_hole_mm) > 0.001:
        raise SystemExit(
            f"{args.reference}.{args.pad} drill is {drill_mm:.3f} mm, "
            f"expected {args.expected_hole_mm:.3f} mm"
        )
    layers = pad.GetLayerSet()
    if layers.Contains(pcbnew.F_Mask) or layers.Contains(pcbnew.B_Mask):
        raise SystemExit(f"{args.reference}.{args.pad} POFV hole is not tented on both outer masks")
    pos = pad.GetPosition()
    holes.append(
        {
            "reference": args.reference,
            "pad": args.pad,
            "x_mm": round(pcbnew.ToMM(pos.x), 3),
            "y_mm": round(pcbnew.ToMM(pos.y), 3),
            "hole_mm": round(drill_mm, 3),
        }
    )

holes.sort(key=lambda row: (row["x_mm"], row["y_mm"]))
if len(holes) != args.expected_count:
    raise SystemExit(
        f"found {len(holes)} drilled {args.reference}.{args.pad} pads, "
        f"expected {args.expected_count}"
    )
print(json.dumps(holes))
