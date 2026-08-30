#!/usr/bin/env python3
"""Generate the JLCPCB fabrication (+ assembly) package for a Stillair board.

Usage: jlc_fab.py [pcb-01|pcb-01-v2|pcb-02] [--assembly-only]
                                            (default pcb-01)

Outputs into pcb/<board>/fab/:
  gerbers/              individual gerber + drill files (kicad-cli)
  <board>-gerbers.zip   the zip to upload on the JLCPCB quote page
  bom-jlcpcb.csv        assembly BOM   } only for boards with assembly=True
  cpl-jlcpcb.csv        pick-and-place } (PCB-02 is a bare-board order)

The assembly files contain only the JLCPCB-assembled subset: DNP parts, bare-pad
"components" (test points, Tag-Connect, net tie, solder jumper) and the
hand-populated lines (hand_solder below) are excluded. Rerun after any board or
schematic change; kicad-cli reads the saved files, so save/refill zones first.
"""

import argparse
from collections import Counter
import csv
import html
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

KICAD_CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
KICAD_PYTHON = "/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3"
KICAD_PYTHONPATH = "/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/lib/python3.9/site-packages"
KICAD_FRAMEWORKS = "/Applications/KiCad/KiCad.app/Contents/Frameworks"
RSVG_CONVERT = "/opt/homebrew/bin/rsvg-convert"
PDFUNITE = "/opt/homebrew/bin/pdfunite"

BOARDS = {
    "pcb-01": {
        # 4-layer controller, Standard PCBA top side.
        "layers": (
            "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,"
            "F.Silkscreen,B.Silkscreen,F.Paste,B.Paste,Edge.Cuts"
        ),
        "assembly": True,
        # Bare pads / fitted-but-no-part refs, never in assembly files.
        "no_part_prefixes": ("TP",),
        "no_part_refs": {"J7", "NT1", "JP1"},
        # DNP flags are inconsistent in the schematic (intrinsic dnp vs a DNP
        # property), so exclude by explicit ref too.
        "dnp_refs": {"C6", "C32", "C36", "C37", "C38", "C39", "C40", "F1", "J8"},
        # Hand-populated at the bench (THT, or parts already in hand / not
        # LCSC-stocked). Keep in sync with docs/electrical.md "Fabrication".
        # C1/C2: Panasonic FR authenticity (DigiKey stock in hand). J1/J2: Molex
        # in hand. U8: LM2907 effectively dead on LCSC (~55 under the MX reel
        # code); DigiKey qty 3 in hand. C34: 100nF 1% C0G 0603 (LM2907
        # charge-pump timing) has no 0603 form in the JLC catalog; DigiKey.
        "hand_solder": {"C1", "C2", "C34", "J1", "J2", "U8"},
        "require_lcsc": False,
        "require_mpn": False,
    },
    "pcb-01-v2": {
        # 4-layer controller, Standard PCBA top side.  This is intentionally a
        # fresh schedule: no V1 DNP/Tag-Connect/jumper exclusions apply.
        "layers": (
            "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,"
            "F.Silkscreen,B.Silkscreen,F.Paste,B.Paste,Edge.Cuts"
        ),
        "assembly": True,
        # Exact no-part refs frozen in docs/pcb-01-v2.md. Fiducials use the
        # conventional FID prefix and are never purchase/PnP items.
        "no_part_prefixes": ("FID",),
        "no_part_refs": {
            "NT1",
            *(f"TP{n}" for n in range(1, 32)),
            *(f"H{n}" for n in range(1, 5)),
        },
        # Optional USB tuning shunts are pads only unless signal-integrity
        # measurements justify fitting them.
        "dnp_refs": {"C44", "C45"},
        # Complete V2 hand-populated set. J3 has an LCSC number but the frozen
        # assembly split still requires hand soldering. Native USB J4 and both
        # ESD arrays U13/U14 are JLCPCB-assembled.
        "hand_solder": {"C1", "C2", "J1", "J2", "J3", "U8"},
        "require_lcsc": True,
        "require_mpn": True,
    },
    "pcb-02": {
        # 2-layer Hall daughterboard: bare boards, hand-assembled from parts in
        # hand (DRV5033 x3, 100 nF strip, S3B-PH-K-S via DigiKey).
        "layers": (
            "F.Cu,B.Cu,F.Mask,B.Mask,"
            "F.Silkscreen,B.Silkscreen,F.Paste,B.Paste,Edge.Cuts"
        ),
        "assembly": False,
        "no_part_prefixes": (),
        "no_part_refs": set(),
        "dnp_refs": set(),
        "hand_solder": set(),
        "require_lcsc": False,
        "require_mpn": False,
    },
}

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("board", nargs="?", choices=sorted(BOARDS), default="pcb-01")
parser.add_argument(
    "--assembly-only",
    action="store_true",
    help="generate and validate BOM/CPL without pre-route Gerber export",
)
ARGS = parser.parse_args()

BOARD_NAME = ARGS.board
CFG = BOARDS[BOARD_NAME]
ROOT = Path(__file__).resolve().parents[1] / BOARD_NAME
BOARD = ROOT / f"{BOARD_NAME}.kicad_pcb"
SCHEMATIC = ROOT / f"{BOARD_NAME}.kicad_sch"
OUT = ROOT / "fab"

GERBER_LAYERS = CFG["layers"]
NO_PART_PREFIXES = CFG["no_part_prefixes"]
NO_PART_REFS = CFG["no_part_refs"]
DNP_REFS = CFG["dnp_refs"]
HAND_SOLDER = CFG["hand_solder"]

# (Comment, Footprint) -> LCSC number, merged over empty schematic LCSC fields.
# Durable home for capture-time-undecided sourcing; see lcsc-map.csv Note column
# for substitution rationale. Schematic LCSC fields, where set, win.
LCSC_MAP_FILE = OUT / "lcsc-map.csv"


def run(*args: str) -> None:
    subprocess.run([KICAD_CLI, *args], check=True, capture_output=True, text=True)


def assert_v2_release_ready() -> None:
    """Refuse to emit orderable V2 Gerbers from an unrouted or failing board."""
    with tempfile.TemporaryDirectory(prefix="stillair-pcb01-v2-release-") as temp_dir:
        report_path = Path(temp_dir) / "drc.json"
        run(
            "pcb", "drc",
            "--severity-all",
            "--format", "json",
            "-o", str(report_path),
            str(BOARD),
        )
        report = json.loads(report_path.read_text())
    violations = report.get("violations", [])
    unconnected = report.get("unconnected_items", [])
    if violations or unconnected:
        kinds = Counter(item.get("type", "unknown") for item in violations)
        raise RuntimeError(
            "PCB-01 V2 release gate failed: "
            f"{len(violations)} DRC violations ({dict(sorted(kinds.items()))}) and "
            f"{len(unconnected)} unconnected items. Route the board, refill all zones, "
            "resolve every DRC item, then rerun without --assembly-only. No Gerbers "
            "were exported."
        )


def excluded(ref: str) -> bool:
    if ref in NO_PART_REFS or ref in DNP_REFS or ref in HAND_SOLDER:
        return True
    return any(
        ref.startswith(p) and ref[len(p) :].isdigit() for p in NO_PART_PREFIXES
    )


def export_gerbers() -> None:
    gdir = OUT / "gerbers"
    gdir.mkdir(parents=True, exist_ok=True)
    for old in gdir.iterdir():
        old.unlink()
    run(
        "pcb", "export", "gerbers",
        "--layers", GERBER_LAYERS,
        "--subtract-soldermask",
        "--no-x2",
        "-o", str(gdir) + "/",
        str(BOARD),
    )
    run(
        "pcb", "export", "drill",
        "--format", "excellon",
        "--excellon-units", "mm",
        "--generate-map", "--map-format", "gerberx2",
        "-o", str(gdir) + "/",
        str(BOARD),
    )
    zip_path = OUT / f"{BOARD_NAME}-gerbers.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(gdir.iterdir()):
            z.write(f, f.name)
    print(f"wrote {zip_path.relative_to(ROOT)} ({len(list(gdir.iterdir()))} files)")


def refs_from_rows(rows: list[dict[str, str]], field: str) -> list[str]:
    return [ref for row in rows for ref in expand_refs(row[field])]


def assert_ref_partition(
    rows: list[dict[str, str]],
    field: str,
    expected: set[str],
    forbidden: set[str],
    artifact: str,
) -> None:
    counts = Counter(refs_from_rows(rows, field))
    duplicates = sorted(ref for ref, count in counts.items() if count != 1)
    missing = sorted(expected - counts.keys())
    unexpected = sorted(counts.keys() - expected)
    leaked = sorted(counts.keys() & forbidden)
    if duplicates or missing or unexpected or leaked:
        raise RuntimeError(
            f"{artifact} reference coverage failed: duplicates={duplicates}, "
            f"missing={missing}, unexpected={unexpected}, excluded={leaked}"
        )


def load_source_map() -> dict[tuple[str, str], dict[str, str]]:
    source_map: dict[tuple[str, str], dict[str, str]] = {}
    if not LCSC_MAP_FILE.exists():
        return source_map
    with open(LCSC_MAP_FILE, newline="") as f:
        for row in csv.DictReader(f):
            key = (row["Comment"], row["Footprint"])
            if key in source_map:
                raise RuntimeError(f"duplicate source-map key: {key}")
            source_map[key] = row
    return source_map


def export_bom() -> tuple[set[str], set[str]]:
    raw = OUT / "bom-raw.csv"
    run(
        "sch", "export", "bom",
        "--fields", "Value,Reference,Footprint,MPN,LCSC",
        "--labels", "Comment,Designator,Footprint,MPN,LCSC Part #",
        "--group-by", "Value,Footprint",
        "-o", str(raw),
        str(SCHEMATIC),
    )
    source_map = load_source_map()
    rows, missing_lcsc, missing_mpn = [], [], []
    hand_rows = []
    with open(raw, newline="") as f:
        raw_rows = list(csv.DictReader(f))
        all_schematic_refs = set(refs_from_rows(raw_rows, "Designator"))
        for row in raw_rows:
            # kicad-cli compresses runs to "R4-R7"; re-expand for filtering.
            refs = expand_refs(row["Designator"])
            mapped = source_map.get((row["Comment"], row["Footprint"]), {})
            if not row["MPN"]:
                row["MPN"] = mapped.get("MPN", "")
            if not row["LCSC Part #"]:
                row["LCSC Part #"] = mapped.get("LCSC", "")
            hands = [r for r in refs if r in HAND_SOLDER]
            if hands:
                hand_rows.append({**row, "Designator": ",".join(hands)})
            keep = [r for r in refs if not excluded(r)]
            if not keep:
                continue
            row["Designator"] = ",".join(keep)
            if not row["LCSC Part #"]:
                missing_lcsc.append(f"{row['Designator']} ({row['Comment']})")
            if not row["MPN"]:
                missing_mpn.append(f"{row['Designator']} ({row['Comment']})")
            rows.append(row)
    raw.unlink()

    expected = {ref for ref in all_schematic_refs if not excluded(ref)}
    forbidden = all_schematic_refs - expected
    assert_ref_partition(rows, "Designator", expected, forbidden, "assembly BOM")

    out = OUT / "bom-jlcpcb.csv"
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["Comment", "Designator", "Footprint", "LCSC Part #"],
            lineterminator="\n",
        )
        w.writeheader()
        w.writerows(
            {key: row[key] for key in w.fieldnames}
            for row in rows
        )
    print(f"wrote {out.relative_to(ROOT)} ({len(rows)} lines)")

    manifest = OUT / "assembly-manifest.csv"
    manifest_fields = ["Comment", "Designator", "Footprint", "MPN", "LCSC Part #"]
    with open(manifest, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=manifest_fields, lineterminator="\n")
        w.writeheader()
        w.writerows({key: row[key] for key in manifest_fields} for row in rows)
    print(f"wrote {manifest.relative_to(ROOT)} ({len(rows)} lines)")

    hand = OUT / "hand-manifest.csv"
    with open(hand, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=manifest_fields, lineterminator="\n")
        w.writeheader()
        w.writerows({key: row[key] for key in manifest_fields} for row in hand_rows)
    hand_refs = set(refs_from_rows(hand_rows, "Designator"))
    if hand_refs != HAND_SOLDER:
        raise RuntimeError(
            f"hand manifest coverage failed: missing={sorted(HAND_SOLDER - hand_refs)}, "
            f"unexpected={sorted(hand_refs - HAND_SOLDER)}"
        )
    print(f"wrote {hand.relative_to(ROOT)} ({len(hand_refs)} refs)")

    if missing_lcsc:
        print(f"  !! {len(missing_lcsc)} lines missing LCSC numbers:")
        for m in missing_lcsc:
            print(f"     {m}")
        if CFG["require_lcsc"]:
            raise RuntimeError("machine-assembly BOM has missing LCSC numbers")
    if missing_mpn:
        print(f"  !! {len(missing_mpn)} lines have no frozen MPN:")
        for m in missing_mpn:
            print(f"     {m}")
        if CFG["require_mpn"]:
            raise RuntimeError("machine-assembly BOM has missing MPNs")
    return expected, forbidden


def expand_refs(field: str) -> list[str]:
    """Expand 'R4-R7,R28' into ['R4','R5','R6','R7','R28']."""
    out: list[str] = []
    for part in field.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-")
            prefix = "".join(c for c in a if not c.isdigit())
            out.extend(f"{prefix}{n}" for n in range(int(a[len(prefix):]), int(b[len(prefix):]) + 1))
        else:
            out.append(part)
    return out


def export_cpl(expected: set[str], forbidden: set[str]) -> None:
    raw = OUT / "cpl-raw.csv"
    run(
        "pcb", "export", "pos",
        "--format", "csv",
        "--units", "mm",
        "--side", "both",
        "-o", str(raw),
        str(BOARD),
    )
    rows = []
    with open(raw, newline="") as f:
        raw_rows = list(csv.DictReader(f))
        board_refs = {row["Ref"] for row in raw_rows}
        board_forbidden = forbidden | {ref for ref in board_refs if excluded(ref)}
        unknown = sorted(board_refs - expected - board_forbidden)
        if unknown:
            raise RuntimeError(f"board contains unclassified footprint refs: {unknown}")
        for row in raw_rows:
            ref = row["Ref"]
            if excluded(ref):
                continue
            rows.append(
                {
                    "Designator": ref,
                    "Mid X": row["PosX"],
                    "Mid Y": row["PosY"],
                    "Layer": "Top" if row["Side"] == "top" else "Bottom",
                    "Rotation": row["Rot"],
                }
            )
    raw.unlink()
    assert_ref_partition(rows, "Designator", expected, board_forbidden, "CPL")
    out = OUT / "cpl-jlcpcb.csv"
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["Designator", "Mid X", "Mid Y", "Layer", "Rotation"],
            lineterminator="\n",
        )
        w.writeheader()
        w.writerows(rows)
    sides = {r["Layer"] for r in rows}
    print(f"wrote {out.relative_to(ROOT)} ({len(rows)} parts, sides: {sorted(sides)})")


def write_v2_fabrication_notes() -> None:
    """Emit order-critical process notes that Gerber/Excellon cannot encode."""
    env = dict(os.environ)
    env["DYLD_FRAMEWORK_PATH"] = KICAD_FRAMEWORKS
    env["PYTHONPATH"] = KICAD_PYTHONPATH
    result = subprocess.run(
        [
            KICAD_PYTHON,
            str(Path(__file__).with_name("pofv_locations.py")),
            str(BOARD),
            "U1",
            "41",
            "--expected-count", "12",
            "--expected-hole-mm", "0.30",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    pofv = json.loads(result.stdout)
    with open(OUT / "pofv-locations.csv", "w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["Reference", "Pad", "X mm", "Y mm", "Finished hole mm", "Process"])
        for row in pofv:
            writer.writerow([
                row["reference"], row["pad"], f"{row['x_mm']:.2f}", f"{row['y_mm']:.2f}",
                f"{row['hole_mm']:.2f}", "filled+copper-capped POFV",
            ])

    note = """# PCB-01 V2 fabrication notes

These requirements are not conveyed reliably by Gerber and Excellon alone. Paste the two quoted
lines into the JLCPCB order remarks and require production-file confirmation before approval.

> POFV REQUIRED: Fill and copper-cap the twelve 0.30 mm plated holes inside U1 exposed pad 41.
> Treat only the coordinates in pofv-locations.csv as POFV, even if Excellon calls them component
> drills. They are tented on both outer masks. Do not leave resin exposed and do not open the mask.

> U3 PADS 4/5 ARE SOLDER-MASK-DEFINED: Preserve the submitted 0.08 mm mask overlap on all sides.
> Do not convert pads 4/5 to NSMD or expand their mask apertures during CAM.

Order and production-file checks:

- 88 x 64 mm, four layers, 1.6 mm, 2 oz outer copper, 1 oz inner copper, ENIG.
- FR-4 Tg >= 150 C, green solder mask, white silkscreen.
- Select filled and capped vias / POFV. The KiCad stackup records filling and capping as enabled.
- Standard PCBA, top side only. Use bom-jlcpcb.csv and cpl-jlcpcb.csv.
- Confirm every U1 POFV coordinate and both U3 SMD mask apertures in JLC's production files.
- Do not approve manufacturing until routing is complete, zones are refilled, DRC has zero
  unconnected items, and a fresh non-assembly-only package has been generated.
"""
    (OUT / "fabrication-notes.md").write_text(note)
    print("wrote fab/fabrication-notes.md and fab/pofv-locations.csv")


def natural_ref_key(ref: str) -> tuple[str, int]:
    match = re.fullmatch(r"([^0-9]+)([0-9]+)", ref)
    return (match.group(1), int(match.group(2))) if match else (ref, 0)


def write_v2_assembly_locator() -> None:
    """Generate a readable, reproducible four-page component-side locator."""
    positions = OUT / "assembly-locator-positions.csv"
    run(
        "pcb", "export", "pos",
        "--format", "csv",
        "--units", "mm",
        "--side", "both",
        "-o", str(positions),
        str(BOARD),
    )
    with open(positions, newline="") as f:
        rows = list(csv.DictReader(f))
    if {row["Side"] for row in rows} != {"top"}:
        raise RuntimeError("assembly locator expects every PCB-01 V2 footprint on the top side")
    for row in rows:
        row["x"] = float(row["PosX"])
        row["y"] = abs(float(row["PosY"]))

    quadrants = [
        ("NW", 50.0, 94.0, 50.0, 82.0),
        ("NE", 94.0, 138.0, 50.0, 82.0),
        ("SW", 50.0, 94.0, 82.0, 114.0),
        ("SE", 94.0, 138.0, 82.0, 114.0),
    ]
    pdfs = []
    located_refs = set()
    for name, xmin, xmax, ymin, ymax in quadrants:
        selected = [
            row for row in rows
            if xmin <= row["x"] < xmax and ymin <= row["y"] < ymax
        ]
        selected.sort(key=lambda row: natural_ref_key(row["Ref"]))
        selected_refs = {row["Ref"] for row in selected}
        duplicates = located_refs & selected_refs
        if duplicates:
            raise RuntimeError(f"assembly locator duplicates refs: {sorted(duplicates)}")
        located_refs.update(selected_refs)
        page_w, page_h = 297.0, 210.0
        panel_x, panel_y, panel_w = 12.0, 28.0, 158.0
        panel_h = panel_w * (ymax - ymin) / (xmax - xmin)
        sx = panel_w / (xmax - xmin)
        sy = panel_h / (ymax - ymin)

        marker_positions = []
        marker_data = []
        offsets = [(0, 0), (5, 0), (-5, 0), (0, 5), (0, -5), (5, 5),
                   (-5, 5), (5, -5), (-5, -5), (10, 0), (-10, 0), (0, 10), (0, -10)]
        for index, row in enumerate(selected, start=1):
            ax = panel_x + (row["x"] - xmin) * sx
            ay = panel_y + (row["y"] - ymin) * sy
            mx, my = ax, ay
            for dx, dy in offsets:
                cx = min(max(ax + dx, panel_x + 2.5), panel_x + panel_w - 2.5)
                cy = min(max(ay + dy, panel_y + 2.5), panel_y + panel_h - 2.5)
                if all((cx - px) ** 2 + (cy - py) ** 2 >= 25 for px, py in marker_positions):
                    mx, my = cx, cy
                    break
            marker_positions.append((mx, my))
            marker_data.append((index, row, ax, ay, mx, my))

        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{page_w}mm" height="{page_h}mm" viewBox="0 0 {page_w} {page_h}">',
            '<rect width="297" height="210" fill="white"/>',
            f'<text x="12" y="12" font-family="sans-serif" font-size="6" font-weight="700">PCB-01 V2 assembly locator, {name}</text>',
            '<text x="12" y="20" font-family="sans-serif" font-size="3.5">Revision V2 | component-side (top) view | coordinates in mm | generated from current .kicad_pcb</text>',
            f'<rect x="{panel_x}" y="{panel_y}" width="{panel_w}" height="{panel_h}" fill="#f5f6f2" stroke="#20231f" stroke-width="0.7"/>',
        ]
        for gx in range(int(xmin // 10) * 10, int(xmax) + 1, 10):
            if xmin <= gx <= xmax:
                px = panel_x + (gx - xmin) * sx
                parts.append(f'<line x1="{px:.2f}" y1="{panel_y}" x2="{px:.2f}" y2="{panel_y + panel_h:.2f}" stroke="#c9ccc5" stroke-width="0.25"/>')
                parts.append(f'<text x="{px + 1:.2f}" y="{panel_y + 4:.2f}" font-family="monospace" font-size="2.4">X{gx}</text>')
        for gy in range(int(ymin // 10) * 10, int(ymax) + 1, 10):
            if ymin <= gy <= ymax:
                py = panel_y + (gy - ymin) * sy
                parts.append(f'<line x1="{panel_x}" y1="{py:.2f}" x2="{panel_x + panel_w:.2f}" y2="{py:.2f}" stroke="#c9ccc5" stroke-width="0.25"/>')
                parts.append(f'<text x="{panel_x + 1:.2f}" y="{py - 1:.2f}" font-family="monospace" font-size="2.4">Y{gy}</text>')
        for index, row, ax, ay, mx, my in marker_data:
            parts.append(f'<circle cx="{ax:.2f}" cy="{ay:.2f}" r="0.8" fill="#232722"/>')
            if abs(ax - mx) > 0.1 or abs(ay - my) > 0.1:
                parts.append(f'<line x1="{ax:.2f}" y1="{ay:.2f}" x2="{mx:.2f}" y2="{my:.2f}" stroke="#657064" stroke-width="0.35"/>')
            parts.append(f'<circle cx="{mx:.2f}" cy="{my:.2f}" r="2.35" fill="white" stroke="#2f5b3c" stroke-width="0.55"/>')
            parts.append(f'<text x="{mx:.2f}" y="{my + 0.85:.2f}" text-anchor="middle" font-family="sans-serif" font-size="2.5" font-weight="700">{index}</text>')

        table_x, table_y = 177.0, 29.0
        rows_per_column = 30
        for index, row, *_ in marker_data:
            column = (index - 1) // rows_per_column
            line = (index - 1) % rows_per_column
            x = table_x + column * 55.0
            y = table_y + line * 5.5
            value = row["Val"] if len(row["Val"]) <= 20 else row["Val"][:19] + "…"
            parts.append(f'<circle cx="{x}" cy="{y}" r="1.7" fill="white" stroke="#2f5b3c" stroke-width="0.4"/>')
            parts.append(f'<text x="{x}" y="{y + 0.62}" text-anchor="middle" font-family="sans-serif" font-size="1.9" font-weight="700">{index}</text>')
            parts.append(f'<text x="{x + 3.2}" y="{y - 0.1}" font-family="sans-serif" font-size="2.4" font-weight="700">{html.escape(row["Ref"])}</text>')
            parts.append(f'<text x="{x + 3.2}" y="{y + 2.1}" font-family="sans-serif" font-size="1.8" fill="#5d625c">{html.escape(value)}</text>')
        parts.append('</svg>')

        svg = OUT / f"assembly-locator-{name.lower()}.svg"
        pdf = OUT / f"assembly-locator-{name.lower()}.pdf"
        svg.write_text("\n".join(parts))
        subprocess.run([RSVG_CONVERT, "-f", "pdf", "-o", str(pdf), str(svg)], check=True)
        pdfs.append(pdf)

    expected_refs = {row["Ref"] for row in rows}
    if located_refs != expected_refs:
        raise RuntimeError(
            f"assembly locator ref mismatch; missing={sorted(expected_refs - located_refs)}, "
            f"extra={sorted(located_refs - expected_refs)}"
        )
    subprocess.run([PDFUNITE, *(str(pdf) for pdf in pdfs), str(OUT / "assembly-locator.pdf")], check=True)
    print("wrote fab/assembly-locator.pdf (four readable component-side quadrant pages)")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    if BOARD_NAME == "pcb-01-v2" and not ARGS.assembly_only:
        assert_v2_release_ready()
    if BOARD_NAME == "pcb-01-v2":
        write_v2_fabrication_notes()
        write_v2_assembly_locator()
    if not ARGS.assembly_only:
        export_gerbers()
    if CFG["assembly"]:
        expected_refs, forbidden_refs = export_bom()
        export_cpl(expected_refs, forbidden_refs)
    else:
        print("bare-board order: skipping assembly BOM/CPL")
    print("done", file=sys.stderr)
