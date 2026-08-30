"""Silk sweep for PCB-01: relocate flagged Reference fields to clear spots.

Parses the board, builds an obstacle model (pads, silk graphics, ref texts,
board edge), then for each DRC-flagged ref searches a ring of candidate
positions around its footprint's bounding box and writes the best clear spot
back into the file (only the property's `(at ...)` line changes).
"""
import json, re, math, os, sys

BOARD = os.environ.get(
    "STILLAIR_BOARD", "/Users/michael/Code/stillair/pcb/pcb-01/pcb-01.kicad_pcb"
)
DRC_JSON = sys.argv[1]
APPLY = "--apply" in sys.argv

txt = open(BOARD).read()

# ---------- flagged refs from DRC ----------
d = json.load(open(DRC_JSON))
flagged = {}
for v in d["violations"]:
    if not (v["type"].startswith("silk") or v["type"] == "text_height"):
        continue
    for i in v["items"]:
        m = re.search(r"Reference field of (\S+)", i["description"])
        if m:
            flagged[m.group(1)] = flagged.get(m.group(1), 0) + 1

# ---------- parse footprints ----------
def blocks(text, token):
    out = []
    for m in re.finditer(r"\(%s\b" % token, text):
        start = m.start(); depth = 0; i = start
        while i < len(text):
            if text[i] == "(": depth += 1
            elif text[i] == ")":
                depth -= 1
                if depth == 0: break
            i += 1
        out.append((start, i + 1, text[start:i + 1]))
    return out

def rot_xy(x, y, deg):
    r = math.radians(deg)
    return x * math.cos(r) - y * math.sin(r), x * math.sin(r) + y * math.cos(r)

class FP:
    pass

fps = {}
for start, end, b in blocks(txt, "footprint"):
    rm = re.search(r'\(property "Reference" "([^"]+)"', b)
    if not rm: continue
    f = FP(); f.ref = rm.group(1); f.start = start; f.end = end; f.block = b
    at = re.search(r'\(at ([\-\d.]+) ([\-\d.]+)(?: ([\-\d.]+))?\)', b)
    f.ax, f.ay = float(at.group(1)), float(at.group(2))
    f.rot = float(at.group(3) or 0)
    # KiCad Y axis is inverted vs math convention: local->abs uses -rot
    # pads: absolute boxes (pad at is local; pad angle absolute — irrelevant for box approx)
    f.pads = []
    for pm in re.finditer(r'\(pad "[^"]*"[^(]*\(at ([\-\d.]+) ([\-\d.]+)(?: [\-\d.]+)?\)\s*\(size ([\d.]+) ([\d.]+)\)', b):
        px, py, sx, sy = map(float, pm.groups())
        dx, dy = rot_xy(px, py, -f.rot)
        r = max(sx, sy) / 2  # conservative circle-ish box
        f.pads.append((f.ax + dx, f.ay + dy, max(sx, sy), max(sx, sy)))
    # silk graphics on F.Silkscreen: collect abs bboxes
    f.silk = []
    for gm in re.finditer(r'\(fp_(line|rect|circle|arc|poly)\b(.*?)\n\t\t\)', b, re.S):
        kind, gb = gm.group(1), gm.group(2)
        if '"F.Silkscreen"' not in gb: continue
        pts = [(float(a), float(c)) for a, c in re.findall(r'\((?:start|end|mid|center|xy) ([\-\d.]+) ([\-\d.]+)\)', gb)]
        if not pts: continue
        w = re.search(r'\(width ([\d.]+)\)', gb)
        wd = float(w.group(1)) if w else 0.12
        apts = []
        for lx, ly in pts:
            dx, dy = rot_xy(lx, ly, -f.rot)
            apts.append((f.ax + dx, f.ay + dy))
        xs = [p[0] for p in apts]; ys = [p[1] for p in apts]
        if kind == "circle" and len(apts) >= 2:
            r = math.hypot(apts[1][0] - apts[0][0], apts[1][1] - apts[0][1])
            f.silk.append((apts[0][0] - r, apts[0][1] - r, apts[0][0] + r, apts[0][1] + r))
        else:
            f.silk.append((min(xs) - wd, min(ys) - wd, max(xs) + wd, max(ys) + wd))
    # Reference property: at + size + rot
    pm = re.search(r'\(property "Reference" "[^"]*"\s*\(at ([\-\d.]+) ([\-\d.]+)(?: ([\-\d.]+))?\)', b)
    f.rat = (float(pm.group(1)), float(pm.group(2)), float(pm.group(3) or 0))
    sm = re.search(r'\(property "Reference".*?\(size ([\d.]+) ([\d.]+)\)', b, re.S)
    f.tsize = (float(sm.group(1)), float(sm.group(2))) if sm else (1.0, 1.0)
    f.hidden = bool(re.search(r'\(property "Reference" "[^"]*"\s*\(at [^)]*\)\s*(?:\(unlocked yes\)\s*)?\(layer "[^"]*"\)\s*\(hide yes\)', b))
    fps[f.ref] = f

def text_abs(f):
    dx, dy = rot_xy(f.rat[0], f.rat[1], -f.rot)
    return f.ax + dx, f.ay + dy

def text_box(f, cx, cy, tr):
    label = f.ref
    w = 0.95 * f.tsize[0] * len(label) + 0.3
    h = 1.4 * f.tsize[1]
    if tr % 180 == 90: w, h = h, w
    return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)

def fp_bbox(f):
    xs, ys = [f.ax], [f.ay]
    for px, py, sx, sy in f.pads:
        xs += [px - sx / 2, px + sx / 2]; ys += [py - sy / 2, py + sy / 2]
    for b0, b1, b2, b3 in f.silk:
        xs += [b0, b2]; ys += [b1, b3]
    return min(xs), min(ys), max(xs), max(ys)

def overlap(a, b, m=0.0):
    return not (a[2] + m < b[0] or b[2] + m < a[0] or a[3] + m < b[1] or b[3] + m < a[1])

EDGE = (50.0, 50.0, 128.0, 108.0)
obstacles = []          # (box, tag)
for f in fps.values():
    for px, py, sx, sy in f.pads:
        obstacles.append(((px - sx / 2, py - sy / 2, px + sx / 2, py + sy / 2), "pad:" + f.ref))
    for sb in f.silk:
        obstacles.append((sb, "silk:" + f.ref))
text_obs = {}
for f in fps.values():
    if f.hidden: continue
    cx, cy = text_abs(f)
    text_obs[f.ref] = text_box(f, cx, cy, f.rat[2])

def spot_clear(ref, box):
    for ob, tag in obstacles:
        if overlap(box, ob, 0.18):
            return False
    for r2, tb in text_obs.items():
        if r2 != ref and overlap(box, tb, 0.15):
            return False
    if box[0] < EDGE[0] + 0.3 or box[1] < EDGE[1] + 0.3 or box[2] > EDGE[2] - 0.3 or box[3] > EDGE[3] - 0.3:
        return False
    return True

def tbox_sz(ref, cx, cy, tr, sz):
    w = 0.95 * sz * len(ref) + 0.3
    h = 1.4 * sz
    if tr % 180 == 90: w, h = h, w
    return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)

order = sorted(flagged, key=lambda r: -flagged[r])
moves, unresolved = {}, []
for ref in order:
    f = fps.get(ref)
    if f is None:
        unresolved.append((ref, "not found")); continue
    x0, y0, x1, y1 = fp_bbox(f)
    cxf, cyf = (x0 + x1) / 2, (y0 + y1) / 2
    best = None; best_sz = None
    for sz in (1.0, 0.8):
        rng = 32 if ref.startswith('TP') else 21
        for dist in [0.2 + 0.15 * k for k in range(rng)]:
            cands = []
            for tr in (0, 90):
                w = 0.95 * sz * len(ref) + 0.3
                h = 1.4 * sz
                if tr == 90: w, h = h, w
                # slide along top/bottom edges
                nx = max(2, int((x1 - x0) / 0.4) + 1)
                for k in range(nx + 1):
                    cx = x0 + (x1 - x0) * k / nx
                    cands.append((cx, y0 - dist - h / 2, tr))
                    cands.append((cx, y1 + dist + h / 2, tr))
                # slide along left/right edges
                ny = max(2, int((y1 - y0) / 0.4) + 1)
                for k in range(ny + 1):
                    cy = y0 + (y1 - y0) * k / ny
                    cands.append((x0 - dist - w / 2, cy, tr))
                    cands.append((x1 + dist + w / 2, cy, tr))
                # corners
                cands += [(x0 - dist - w / 2, y0 - dist - h / 2, tr), (x1 + dist + w / 2, y0 - dist - h / 2, tr),
                          (x0 - dist - w / 2, y1 + dist + h / 2, tr), (x1 + dist + w / 2, y1 + dist + h / 2, tr)]
            ok = [(cx, cy, tr) for cx, cy, tr in cands if spot_clear(ref, tbox_sz(ref, cx, cy, tr, sz))]
            if ok:
                best = min(ok, key=lambda c: math.hypot(c[0] - cxf, c[1] - cyf))
                best_sz = sz
                break
        if best: break
    if best is None:
        unresolved.append((ref, "no clear spot within ~3.4mm even at 0.6")); continue
    cx, cy, tr = best
    dx, dy = cx - f.ax, cy - f.ay
    rx, ry = rot_xy(dx, dy, f.rot)   # abs->local uses +rot
    moves[ref] = (round(rx, 3), round(ry, 3), tr, cx, cy, best_sz)
    text_obs[ref] = tbox_sz(ref, cx, cy, tr, best_sz)

print(f"flagged {len(flagged)} refs; placed {len(moves)}; unresolved {len(unresolved)}")
for r, why in unresolved:
    print("  UNRESOLVED:", r, "-", why)

if APPLY:
    new = txt
    changed = 0
    for ref, (rx, ry, tr, cx, cy, sz) in moves.items():
        f = fps[ref]
        # locate this footprint's Reference property block in the CURRENT text
        pstart = new.index('(property "Reference" "%s"' % ref)
        depth = 0; i = pstart
        while i < len(new):
            if new[i] == "(": depth += 1
            elif new[i] == ")":
                depth -= 1
                if depth == 0: break
            i += 1
        block = new[pstart:i + 1]
        tri = int(tr) if tr == int(tr) else tr
        nb = re.sub(r'\(at [\-\d.]+ [\-\d.]+(?: [\-\d.]+)?\)',
                    '(at %s %s %s)' % (rx, ry, tri), block, count=1)
        th = 0.15 if sz >= 1.0 else 0.12
        nb = re.sub(r'\(size [\d.]+ [\d.]+\)', '(size %s %s)' % (sz, sz), nb, count=1)
        nb = re.sub(r'\(thickness [\d.]+\)', '(thickness %s)' % th, nb, count=1)
        if nb != block:
            new = new[:pstart] + nb + new[i + 1:]
            changed += 1
        else:
            print("  WRITE-MISS:", ref)
    open(BOARD, "w").write(new)
    print(f"applied {changed} moves to {BOARD}")
