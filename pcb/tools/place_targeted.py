"""Targeted placement: put each part as close as legally possible to a target.

Usage: place_targeted.py spec.json out.json

spec.json:
{
  "region": [x0, y0, x1, y1],
  "context_plans": ["/tmp/plan_a.json", ...],   # accepted plans (obstacles)
  "fixed": {"REF": [x, y, rot]},                 # pre-seeded members (placed as-is)
  "order": [["REF", tx, ty, rot], ...]           # placement order with targets
}

Each part scans outward from its target in 0.25 mm rings for the nearest anchor
whose courtyard (anchor=centre approximation, rot-swapped) fits: inside region,
0.15 from everything placed/context/pinned, outside hole keepouts, on board.
"""

import json
import math
import sys

sys.path.insert(0, "/Users/michael/Code/stillair/pcb/tools")
import board_model

spec = json.load(open(sys.argv[1]))
parts = board_model.load()
GROUPS = json.load(open("/Users/michael/Code/stillair/pcb/pcb-01/placement/groups.json"))
rx0, ry0, rx1, ry1 = spec["region"]

# obstacle boxes: pinned parts + all context plan members at planned spots
obstacles = []
for ref in GROUPS["pinned"]:
    if ref in parts:
        obstacles.append(parts[ref].abs_box())
for pf in spec.get("context_plans", []):
    for ref, val in json.load(open(pf)).items():
        x, y, rot = val
        w, h = parts[ref].size
        if (rot - parts[ref].rot) % 180 == 90:
            w, h = h, w
        obstacles.append((x - w / 2, y - h / 2, x + w / 2, y + h / 2))

placed = {}


def size_at(ref, rot):
    w, h = parts[ref].size
    if (rot - parts[ref].rot) % 180 == 90:
        w, h = h, w
    return w, h


def ok(ref, x, y, rot):
    w, h = size_at(ref, rot)
    A = (x - w / 2, y - h / 2, x + w / 2, y + h / 2)
    if A[0] < rx0 or A[1] < ry0 or A[2] > rx1 or A[3] > ry1:
        return False
    if A[0] < board_model.BOARD[0] or A[2] > board_model.BOARD[2] \
       or A[1] < board_model.BOARD[1] or A[3] > board_model.BOARD[3]:
        return False
    for hx, hy in board_model.HOLES:
        cx = min(max(hx, A[0]), A[2])
        cy = min(max(hy, A[1]), A[3])
        if math.hypot(cx - hx, cy - hy) < board_model.HOLE_R:
            return False
    G = 0.15
    for B in obstacles:
        if A[0] < B[2] + G and B[0] < A[2] + G and A[1] < B[3] + G and B[1] < A[3] + G:
            return False
    return True


for ref, val in spec.get("fixed", {}).items():
    x, y, rot = val
    if not ok(ref, x, y, rot):
        print(f"WARNING fixed {ref} at ({x},{y}) is not legal")
    placed[ref] = [x, y, rot]
    w, h = size_at(ref, rot)
    obstacles.append((x - w / 2, y - h / 2, x + w / 2, y + h / 2))

failed = []
for ref, tx, ty, rot in spec["order"]:
    best = None
    r = 0.0
    while r <= 25 and best is None:
        steps = max(1, int(2 * math.pi * r / 0.25)) if r else 1
        for i in range(steps):
            th = 2 * math.pi * i / steps
            x = round((tx + r * math.cos(th)) * 4) / 4
            y = round((ty + r * math.sin(th)) * 4) / 4
            for rr in (rot, rot + 90):
                if ok(ref, x, y, rr):
                    best = [x, y, rr]
                    break
            if best:
                break
        r += 0.25
    if best is None:
        failed.append(ref)
        continue
    placed[ref] = best
    w, h = size_at(ref, best[2])
    obstacles.append((best[0] - w / 2, best[1] - h / 2, best[0] + w / 2, best[1] + h / 2))

print("failed:", failed if failed else "none")
json.dump(placed, open(sys.argv[2], "w"), indent=0)
print(f"placed {len(placed)} parts -> {sys.argv[2]}")
