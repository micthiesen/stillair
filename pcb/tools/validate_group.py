"""Validate an agent-proposed group layout before applying it.

Usage: validate_group.py <group_name> <proposal.json>
proposal.json: {"REF": [x, y, rot], ...}

Checks (anchor treated as courtyard centre, matching the brief contract):
region containment, member-member clearance >= 0.1, pinned-obstacle clearance,
mounting-hole keepouts. Exit 0 clean; prints violations otherwise.
"""

import json
import math
import sys

sys.path.insert(0, "/Users/michael/Code/stillair/pcb/tools")
import board_model

name, proposal_file = sys.argv[1], sys.argv[2]
GROUPS = json.load(open("/Users/michael/Code/stillair/pcb/pcb-01/placement/groups.json"))
g = GROUPS["groups"][name]
prop = json.load(open(proposal_file))
parts = board_model.load()
rx0, ry0, rx1, ry1 = g["region"]

def box_at(ref, x, y, rot):
    p = parts[ref]
    w, h = p.size
    if (rot - p.rot) % 180 == 90:
        w, h = h, w
    return (x - w / 2, y - h / 2, x + w / 2, y + h / 2)

bad = []
boxes = {}
missing = [r for r in g["members"] if r not in prop]
extra = [r for r in prop if r not in g["members"]]
if missing:
    bad.append(f"missing members: {missing}")
if extra:
    bad.append(f"unknown refs: {extra}")

for ref, (x, y, rot) in prop.items():
    if ref not in parts:
        continue
    if rot % 90 != 0:
        bad.append(f"{ref}: rot {rot} not multiple of 90")
    boxes[ref] = box_at(ref, x, y, rot)
    A = boxes[ref]
    if A[0] < rx0 - 0.01 or A[1] < ry0 - 0.01 or A[2] > rx1 + 0.01 or A[3] > ry1 + 0.01:
        bad.append(f"{ref}: outside region box=({A[0]:.2f},{A[1]:.2f},{A[2]:.2f},{A[3]:.2f})")
    for hx, hy in board_model.HOLES:
        cx = min(max(hx, A[0]), A[2])
        cy = min(max(hy, A[1]), A[3])
        if math.hypot(cx - hx, cy - hy) < board_model.HOLE_R:
            bad.append(f"{ref}: inside hole keepout ({hx},{hy})")

refs = sorted(boxes)
for i, a in enumerate(refs):
    A = boxes[a]
    for b in refs[i + 1:]:
        B = boxes[b]
        if A[0] < B[2] + 0.1 and B[0] < A[2] + 0.1 and A[1] < B[3] + 0.1 and B[1] < A[3] + 0.1:
            ox = min(A[2], B[2]) - max(A[0], B[0])
            oy = min(A[3], B[3]) - max(A[1], B[1])
            if ox > -0.1 and oy > -0.1:
                bad.append(f"{a} x {b}: overlap/too close (ox={ox:.2f}, oy={oy:.2f})")

for pref in GROUPS["pinned"]:
    if pref not in parts:
        continue
    P = parts[pref].abs_box()
    for ref, A in boxes.items():
        if A[0] < P[2] and P[0] < A[2] and A[1] < P[3] and P[1] < A[3]:
            bad.append(f"{ref} overlaps pinned {pref}")

if bad:
    print(f"{name}: {len(bad)} violations")
    for b in bad[:25]:
        print(" -", b)
    sys.exit(1)
print(f"{name}: clean ({len(boxes)} members)")
