"""Park all non-pinned footprints in a neat grid off the board's right edge.

Pinned parts (connectors, zone-anchor ICs, radials, holes) keep their positions.
Everything else lines up at x >= 140 sorted by reference, so the board canvas
shows only deliberately-placed parts. Emits park_moves.json for apply_positions.
"""

import json
import sys

sys.path.insert(0, "/Users/michael/Code/stillair/pcb/tools")
import board_model

PINNED = {
    "J1", "J2", "J3", "J4", "J5", "J6", "J7", "J8",
    "U1", "U2", "U3", "L1", "C1", "C2", "C6", "SW3",
    "H1", "H2", "H3", "H4",
}

parts = board_model.load()
movable = sorted(r for r in parts if r not in PINNED)

moves = {}
x, y = 140.0, 50.0
row_h = 0.0
for ref in movable:
    w, h = parts[ref].size
    if x + w > 200:
        x = 140.0
        y += row_h + 1.5
        row_h = 0.0
    b = parts[ref].box
    moves[ref] = [round(x - b[0], 2), round(y - b[1], 2)]
    x += w + 1.5
    row_h = max(row_h, h)

json.dump(moves, open("/tmp/park_moves.json", "w"))
print(f"parked {len(moves)} parts; grid ends at y={y + row_h:.0f}")
