"""Exact geometric model of a KiCad 10 board for placement tooling.

Parses footprint anchors, rotations, courtyard bounding boxes (preferred; falls
back to pad extents), and per-pad net assignments straight from the .kicad_pcb
S-expressions. Read-only. All coordinates in mm, KiCad frame (Y down).

Rotation convention (verified empirically on this board): a footprint stored at
angle R maps local (x, y) -> global (x cosR + y sinR, -x sinR + y cosR).
"""

import math
import os
import re

# Override with STILLAIR_BOARD to run against another board (e.g. pcb-02).
# The envelope/keepout constants below are PCB-01's; geometry checks that use
# them are only meaningful there.
BOARD_FILE = os.environ.get(
    "STILLAIR_BOARD", "/Users/michael/Code/stillair/pcb/pcb-01/pcb-01.kicad_pcb"
)

# Board envelope and fixed keepouts (docs/electrical.md PCB-01 definition).
BOARD = (50.6, 50.6, 127.4, 107.4)  # courtyard-legal region, 0.6 inside the edge
HOLES = [(56.0, 102.0), (122.0, 102.0), (56.0, 56.0), (122.0, 56.0)]
HOLE_R = 4.0  # O8 copper/component exclusion around each mounting hole


class Part:
    def __init__(self, ref, anchor, rot, box, pads, lib_id):
        self.ref = ref
        self.anchor = anchor  # (x, y)
        self.rot = rot
        self.box = box  # (x0, y0, x1, y1) relative to anchor
        self.pads = pads  # list of (pad_number, net_name, gx_rel, gy_rel)
        self.lib_id = lib_id

    def abs_box(self, at=None):
        a = at or self.anchor
        b = self.box
        return (a[0] + b[0], a[1] + b[1], a[0] + b[2], a[1] + b[3])

    @property
    def size(self):
        return (self.box[2] - self.box[0], self.box[3] - self.box[1])


def _rot_xy(x, y, r):
    return (x * math.cos(r) + y * math.sin(r), -x * math.sin(r) + y * math.cos(r))


def load(board_file=BOARD_FILE):
    text = open(board_file).read()
    parts = {}
    for m in re.finditer(r'\(footprint "([^"]+)"(.*?)\n\t\)', text, re.S):
        lib_id, blk = m.group(1), m.group(2)
        ref_m = re.search(r'\(property "Reference" "([^"]+)"', blk)
        at_m = re.search(r'\n\t\t\(at ([\-\d.]+) ([\-\d.]+)(?: ([\-\d.]+))?\)', blk)
        if not ref_m or not at_m:
            continue
        ref = ref_m.group(1)
        anchor = (float(at_m.group(1)), float(at_m.group(2)))
        rot = float(at_m.group(3) or 0)
        r = math.radians(rot)

        # Walk each (fp_* ...) item with balanced parens and test its OWN layer
        # tag. A lookahead regex here once matched silk geometry against the
        # NEXT item's CrtYd tag, under-measuring courtyards by up to 0.34 mm.
        xs, ys = [], []
        idx = 0
        while True:
            i = blk.find("(fp_", idx)
            if i < 0:
                break
            depth, j = 0, i
            while True:
                if blk[j] == "(":
                    depth += 1
                elif blk[j] == ")":
                    depth -= 1
                if depth == 0:
                    break
                j += 1
            item = blk[i:j + 1]
            idx = j + 1
            if '.CrtYd"' not in item:
                continue
            if item.startswith("(fp_circle"):
                c = re.search(
                    r'\(center ([\-\d.]+) ([\-\d.]+)\)\s*\(end ([\-\d.]+) ([\-\d.]+)\)',
                    item,
                )
                cx, cy, ex, ey = map(float, c.groups())
                rad = math.hypot(ex - cx, ey - cy)
                gx, gy = _rot_xy(cx, cy, r)
                xs += [gx - rad, gx + rad]
                ys += [gy - rad, gy + rad]
            else:
                for sx, sy in re.findall(
                    r'\((?:start|end|mid|xy) ([\-\d.]+) ([\-\d.]+)\)', item
                ):
                    gx, gy = _rot_xy(float(sx), float(sy), r)
                    xs.append(gx)
                    ys.append(gy)
        used_crtyd = bool(xs)
        if not used_crtyd:
            xs, ys = [], []

        pads = []
        for p in re.finditer(
            r'\(pad "([^"]*)" \w+ \w+\s*\(at ([\-\d.]+) ([\-\d.]+)(?: ([\-\d.]+))?\)\s*'
            r'\(size ([\d.]+) ([\d.]+)\)',
            blk,
        ):
            num, px, py, prot_s, w, h = p.groups()
            nxt = blk.find('(pad "', p.end())
            window = blk[p.end():nxt if nxt != -1 else p.end() + 900]
            net_m = re.search(r'\(net (?:\d+ )?"([^"]+)"\)?', window)
            net = net_m.group(1) if net_m else ""
            px, py, w, h = float(px), float(py), float(w), float(h)
            prot = float(prot_s or 0)
            gx, gy = _rot_xy(px, py, r)
            pads.append((num, net or "", round(gx, 3), round(gy, 3)))
            if not used_crtyd:
                hw, hh = (h / 2, w / 2) if (prot % 180) == 90 else (w / 2, h / 2)
                pm = 0.2
                xs += [gx - hw - pm, gx + hw + pm]
                ys += [gy - hh - pm, gy + hh + pm]
        if not xs:
            continue
        mg = 0.05
        box = (min(xs) - mg, min(ys) - mg, max(xs) + mg, max(ys) + mg)
        parts[ref] = Part(ref, anchor, rot, box, pads, lib_id)
    return parts


def overlaps(parts, ignore_pairs=()):
    """All courtyard-box overlaps between parts. ignore_pairs: set of frozensets."""
    refs = sorted(parts)
    out = []
    for i, a in enumerate(refs):
        A = parts[a].abs_box()
        for b in refs[i + 1:]:
            if frozenset((a, b)) in ignore_pairs:
                continue
            B = parts[b].abs_box()
            if A[0] < B[2] and B[0] < A[2] and A[1] < B[3] and B[1] < A[3]:
                out.append((a, b))
    return out


def violations(parts, movable=None):
    """Board-edge and mounting-hole-keepout violations for the given refs."""
    out = []
    for ref in (movable or parts):
        p = parts[ref]
        A = p.abs_box()
        if A[0] < BOARD[0] or A[1] < BOARD[1] or A[2] > BOARD[2] or A[3] > BOARD[3]:
            out.append((ref, "board-edge"))
        for hx, hy in HOLES:
            cx = min(max(hx, A[0]), A[2])
            cy = min(max(hy, A[1]), A[3])
            if math.hypot(cx - hx, cy - hy) < HOLE_R:
                out.append((ref, f"hole-keepout ({hx},{hy})"))
    return out
