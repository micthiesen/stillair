"""Generate per-group placement briefs (markdown) from groups.json + the board.

Each brief carries: the region, the member table (ref, courtyard size at current
rotation, pads with nets), pinned obstacles intersecting the region, and the
hand-written circuit intent. Output: pcb/pcb-01/placement/groups/<name>.md
"""

import json
import sys

sys.path.insert(0, "/Users/michael/Code/stillair/pcb/tools")
import board_model

GROUPS = json.load(open("/Users/michael/Code/stillair/pcb/pcb-01/placement/groups.json"))
parts = board_model.load()
OUT_DIR = "/Users/michael/Code/stillair/pcb/pcb-01/placement/groups"

pinned = GROUPS["pinned"]

for name, g in GROUPS["groups"].items():
    rx0, ry0, rx1, ry1 = g["region"]
    lines = [f"# Group: {name}", "",
             f"Region (absolute board mm, Y down): x {rx0}..{rx1}, y {ry0}..{ry1}", "",
             "## Intent", "", g["intent"], "",
             "## Members (courtyard size at CURRENT rotation; rotating 90/270 swaps w/h)", "",
             "| ref | w x h | rot | pads (num:net at local offset) |", "|---|---|---|---|"]
    for ref in g["members"]:
        p = parts[ref]
        w, h = p.size
        pads = "; ".join(f"{n}:{net or '-'}@({dx:+.1f},{dy:+.1f})" for n, net, dx, dy in p.pads[:14])
        lines.append(f"| {ref} | {w:.2f} x {h:.2f} | {p.rot:g} | {pads} |")
    obst = []
    for ref in pinned:
        if ref not in parts:
            continue
        A = parts[ref].abs_box()
        if A[0] < rx1 + 3 and rx0 - 3 < A[2] and A[1] < ry1 + 3 and ry0 - 3 < A[3]:
            obst.append(f"| {ref} | ({A[0]:.1f},{A[1]:.1f})-({A[2]:.1f},{A[3]:.1f}) |")
    if obst:
        lines += ["", "## Pinned obstacles in/near the region (absolute boxes - do not overlap)",
                  "", "| ref | box |", "|---|---|"] + obst
    for hx, hy in board_model.HOLES:
        if rx0 - 5 < hx < rx1 + 5 and ry0 - 5 < hy < ry1 + 5:
            lines.append(f"\nMounting-hole keepout: circle r=4.0 at ({hx},{hy}) - keep courtyards outside it.")
    lines += ["", "## Output contract", "",
              "Return ONLY a JSON object: {\"REF\": [x, y, rot], ...} for every member.",
              "x,y are the footprint ANCHOR position in absolute board mm. The courtyard",
              "box is centred on the anchor only approximately; assume anchor = courtyard",
              "centre and keep 0.15 mm slack between neighbouring courtyards. rot must be",
              "0, 90, 180, or 270 (90/270 swaps the courtyard w/h). Every courtyard fully",
              "inside the region; no overlaps among members or with the obstacle boxes."]
    open(f"{OUT_DIR}/{name}.md", "w").write("\n".join(lines) + "\n")
    print(name, len(g["members"]), "members")
