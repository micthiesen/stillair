"""Extract review artifacts from the BOARD file (the source of truth):
a netlist markdown (components + per-net pin lists) and a positions dump.

Usage: extract_netlist.py <out-netlist.md> [out-positions.txt]
Used by the board-truth review loop (see the /pcb skill)."""
import re
import sys
from collections import defaultdict

sys.path.insert(0, "/Users/michael/Code/stillair/pcb/tools")
import board_model

text = open(board_model.BOARD_FILE).read()
parts = board_model.load()

props = {}
for m in re.finditer(r'\(footprint "([^"]+)"(.*?)\n\t\)', text, re.S):
    blk = m.group(2)
    ref_m = re.search(r'\(property "Reference" "([^"]+)"', blk)
    if not ref_m:
        continue
    ref = ref_m.group(1)
    d = {}
    for pm in re.finditer(r'\(property "([^"]+)" "([^"]*)"', blk):
        d[pm.group(1)] = pm.group(2)
    d["dnp"] = "(dnp yes)" in blk or re.search(r'\(attr[^)]*\bdnp\b', blk) is not None
    props[ref] = d

out = []
out.append("# PCB-01 board-extracted netlist (source of truth: pcb-01.kicad_pcb)")
out.append("# Generated read-only from the board file. Pad numbers are footprint pad")
out.append("# numbers; map them to pin FUNCTIONS via the part's datasheet.")
out.append("")
out.append("## Components  (ref | value | footprint | fields)")
out.append("")


def sortkey(r):
    m = re.match(r"([A-Za-z]+)(\d+)", r)
    return (m.group(1), int(m.group(2))) if m else (r, 0)


for ref in sorted(parts, key=sortkey):
    p = parts[ref]
    d = props.get(ref, {})
    extra = []
    for k in ("MPN", "LCSC", "Note"):
        if d.get(k):
            extra.append(f"{k}={d[k]}")
    if d.get("dnp"):
        extra.append("DNP")
    out.append(
        f"{ref} | {d.get('Value','?')} | {p.lib_id} | {' '.join(extra)}"
    )

out.append("")
out.append("## Nets  (net -> ref.pad list)")
out.append("")
nets = defaultdict(list)
for ref in sorted(parts, key=sortkey):
    for num, net, _, _ in parts[ref].pads:
        if net:
            nets[net].append(f"{ref}.{num}")
for net in sorted(nets):
    out.append(f"{net}: {', '.join(nets[net])}")

path = sys.argv[1]
open(path, "w").write("\n".join(out) + "\n")
print(f"{len(parts)} parts, {len(nets)} nets -> {path}")

if len(sys.argv) > 2:
    lines = [
        f"{r} {parts[r].anchor[0]:.2f} {parts[r].anchor[1]:.2f} rot {parts[r].rot:g}"
        for r in sorted(parts, key=sortkey)
    ]
    open(sys.argv[2], "w").write(
        "PCB-01 part positions (mm, KiCad frame, Y down). "
        f"Board x {board_model.BOARD[0]}-{board_model.BOARD[2]}, "
        f"y {board_model.BOARD[1]}-{board_model.BOARD[3]}.\n" + "\n".join(lines) + "\n"
    )
    print(f"{len(lines)} positions -> {sys.argv[2]}")
