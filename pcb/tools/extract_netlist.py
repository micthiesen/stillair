"""Extract review artifacts from the BOARD file (the source of truth):
a netlist markdown (components + per-net pin lists) and a positions dump.

Usage: extract_netlist.py [--board board.kicad_pcb] <out-netlist.md> [out-positions.txt]
Used by the board-truth review loop (see the /pcb skill)."""
import argparse
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, "/Users/michael/Code/stillair/pcb/tools")
import board_model

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--board", type=Path, default=Path(board_model.BOARD_FILE))
parser.add_argument("out_netlist", type=Path)
parser.add_argument("out_positions", nargs="?", type=Path)
args = parser.parse_args()


def safe_write(path: Path, content: str) -> None:
    protected_suffixes = {".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_sym"}
    if path.suffix.lower() in protected_suffixes:
        raise SystemExit(f"refusing to overwrite KiCad source file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(content)
    os.replace(temporary, path)


text = args.board.read_text()
parts = board_model.load(str(args.board))

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
out.append(f"# Board-extracted netlist (source of truth: {args.board.name})")
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

safe_write(args.out_netlist, "\n".join(out) + "\n")
print(f"{len(parts)} parts, {len(nets)} nets -> {args.out_netlist}")

if args.out_positions:
    lines = [
        f"{r} {parts[r].anchor[0]:.2f} {parts[r].anchor[1]:.2f} rot {parts[r].rot:g}"
        for r in sorted(parts, key=sortkey)
    ]
    safe_write(
        args.out_positions,
        f"Part positions from {args.board.name} (mm, KiCad frame, Y down).\n"
        + "\n".join(lines)
        + "\n",
    )
    print(f"{len(lines)} positions -> {args.out_positions}")
