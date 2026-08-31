#!/usr/bin/env python3
"""Extract absolute pad geometry and net names for assembly-orientation callouts."""

import argparse
import json

import pcbnew


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("board")
parser.add_argument("references", nargs="+")
args = parser.parse_args()

board = pcbnew.LoadBoard(args.board)
result = []
for reference in args.references:
    footprint = board.FindFootprintByReference(reference)
    if footprint is None:
        raise SystemExit(f"missing footprint {reference}")
    pads = []
    for pad in footprint.Pads():
        position = pad.GetPosition()
        size = pad.GetSize()
        pads.append({
            "number": pad.GetNumber(),
            "net": pad.GetNetname(),
            "x_mm": round(pcbnew.ToMM(position.x), 4),
            "y_mm": round(pcbnew.ToMM(position.y), 4),
            "width_mm": round(pcbnew.ToMM(size.x), 4),
            "height_mm": round(pcbnew.ToMM(size.y), 4),
        })
    pads.sort(key=lambda item: item["number"])
    position = footprint.GetPosition()
    result.append({
        "reference": reference,
        "value": footprint.GetValue(),
        "x_mm": round(pcbnew.ToMM(position.x), 4),
        "y_mm": round(pcbnew.ToMM(position.y), 4),
        "rotation_degrees": footprint.GetOrientationDegrees(),
        "pads": pads,
    })

print(json.dumps(result))
