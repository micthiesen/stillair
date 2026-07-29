"""Global check of merged placement plans against the live board.

Usage: check_plan.py plan1.json plan2.json ...
Loads the board (pinned parts at their real positions), overlays every plan's
proposed positions, and reports courtyard overlaps, board-edge and hole-keepout
violations, and any movable part not covered by a plan.
"""

import json
import math
import sys

sys.path.insert(0, "/Users/michael/Code/stillair/pcb/tools")
import board_model

parts = board_model.load()
GROUPS = json.load(open("/Users/michael/Code/stillair/pcb/pcb-01/placement/groups.json"))

boxes = {}
for ref in GROUPS["pinned"]:
    if ref in parts:
        boxes[ref] = parts[ref].abs_box()

planned = {}
for f in sys.argv[1:]:
    for ref, val in json.load(open(f)).items():
        x, y, rot = val
        w, h = parts[ref].size
        if (rot - parts[ref].rot) % 180 == 90:
            w, h = h, w
        boxes[ref] = (x - w / 2, y - h / 2, x + w / 2, y + h / 2)
        planned[ref] = val

uncovered = sorted(set(parts) - set(boxes))
if uncovered:
    print("NOT covered by any plan (still parked):", uncovered)

# Edge waivers are PER-SIDE: only the mating face of a right-angle connector may
# overhang, and only toward off-board. A blanket per-ref waiver here once masked
# J2 pads hanging fully off the board (wrong rotation). "l/r/t/b" = allowed side.
EDGE_WAIVER = {"J1": "l", "J2": "b"}

bad = 0
refs = sorted(boxes)
for i, a in enumerate(refs):
    A = boxes[a]
    w = EDGE_WAIVER.get(a, "")
    over = []
    if A[0] < board_model.BOARD[0] - 0.01 and "l" not in w:
        over.append("l")
    if A[1] < board_model.BOARD[1] - 0.01 and "t" not in w:
        over.append("t")
    if A[2] > board_model.BOARD[2] + 0.01 and "r" not in w:
        over.append("r")
    if A[3] > board_model.BOARD[3] + 0.01 and "b" not in w:
        over.append("b")
    if over and not a.startswith("H"):
        print(f"EDGE {a} ({''.join(over)}): {tuple(round(v,2) for v in A)}")
        bad += 1
    for hx, hy in board_model.HOLES:
        cx = min(max(hx, A[0]), A[2])
        cy = min(max(hy, A[1]), A[3])
        if not a.startswith("H") and math.hypot(cx - hx, cy - hy) < board_model.HOLE_R - 0.01:
            print(f"HOLE {a} near ({hx},{hy})")
            bad += 1
    for b in refs[i + 1:]:
        B = boxes[b]
        if A[0] < B[2] and B[0] < A[2] and A[1] < B[3] and B[1] < A[3]:
            if a.startswith("H") and b == "U2" or b.startswith("H") and a == "U2":
                continue  # documented H4/antenna waiver
            print(f"OVERLAP {a} x {b}")
            bad += 1
print(f"{bad} violations; {len(planned)} planned, {len(boxes)} total boxes")
sys.exit(1 if bad else 0)
