#!/usr/bin/env python3
"""Generate the JLCPCB fabrication + assembly package for PCB-01.

Outputs into pcb/pcb-01/fab/:
  gerbers/            individual gerber + drill files (kicad-cli)
  pcb-01-gerbers.zip  the zip to upload on the JLCPCB quote page
  bom-jlcpcb.csv      assembly BOM  (Comment, Designator, Footprint, LCSC Part #)
  cpl-jlcpcb.csv      pick-and-place (Designator, Mid X, Mid Y, Layer, Rotation)

The assembly files contain only the JLCPCB-assembled subset: DNP parts, bare-pad
"components" (test points, Tag-Connect, net tie, solder jumper) and the
hand-populated lines (HAND_SOLDER below) are excluded. Rerun after any board or
schematic change; kicad-cli reads the saved files, so save/refill zones first.
"""

import csv
import io
import subprocess
import sys
import zipfile
from pathlib import Path

KICAD_CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
ROOT = Path(__file__).resolve().parents[1] / "pcb-01"
BOARD = ROOT / "pcb-01.kicad_pcb"
SCHEMATIC = ROOT / "pcb-01.kicad_sch"
OUT = ROOT / "fab"

GERBER_LAYERS = (
    "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,"
    "F.Silkscreen,B.Silkscreen,F.Paste,B.Paste,Edge.Cuts"
)

# Bare pads / fitted-but-no-part refs, never in assembly files.
NO_PART_PREFIXES = ("TP",)
NO_PART_REFS = {"J7", "NT1", "JP1"}
# DNP flags are inconsistent in the schematic (intrinsic dnp vs a DNP property),
# so exclude by explicit ref too.
DNP_REFS = {"C6", "C32", "C36", "C37", "C38", "C39", "C40", "F1", "J8"}
# Hand-populated at the bench (THT, or parts already in hand / not LCSC-stocked).
# Keep in sync with docs/electrical.md "Fabrication".
# C1/C2: Panasonic FR authenticity (DigiKey stock in hand). J1/J2: Molex in hand.
# U8: LM2907 effectively dead on LCSC (~55 under the MX reel code); DigiKey qty 3 in hand.
# C34: 100nF 1% C0G 0603 (LM2907 charge-pump timing, overspeed-chain gain) does not
# exist in the JLC catalog in any 0603 form; hand-solder a DigiKey C0G/U2J part.
HAND_SOLDER = {"C1", "C2", "C34", "J1", "J2", "U8"}

# (Comment, Footprint) -> LCSC number, merged over empty schematic LCSC fields.
# Durable home for capture-time-undecided sourcing; see lcsc-map.csv Note column
# for substitution rationale. Schematic LCSC fields, where set, win.
LCSC_MAP_FILE = OUT / "lcsc-map.csv"


def run(*args: str) -> None:
    subprocess.run([KICAD_CLI, *args], check=True, capture_output=True, text=True)


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
    zip_path = OUT / "pcb-01-gerbers.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(gdir.iterdir()):
            z.write(f, f.name)
    print(f"wrote {zip_path.relative_to(ROOT)} ({len(list(gdir.iterdir()))} files)")


def export_bom() -> None:
    raw = OUT / "bom-raw.csv"
    run(
        "sch", "export", "bom",
        "--fields", "Value,Reference,Footprint,LCSC",
        "--labels", "Comment,Designator,Footprint,LCSC Part #",
        "--group-by", "Value,Footprint",
        "-o", str(raw),
        str(SCHEMATIC),
    )
    lcsc_map: dict[tuple[str, str], str] = {}
    if LCSC_MAP_FILE.exists():
        with open(LCSC_MAP_FILE, newline="") as f:
            for row in csv.DictReader(f):
                lcsc_map[(row["Comment"], row["Footprint"])] = row["LCSC"]
    rows, missing = [], []
    with open(raw, newline="") as f:
        for row in csv.DictReader(f):
            # kicad-cli compresses runs to "R4-R7"; re-expand for filtering.
            refs = expand_refs(row["Designator"])
            keep = [r for r in refs if not excluded(r)]
            if not keep:
                continue
            row["Designator"] = ",".join(keep)
            if not row["LCSC Part #"]:
                row["LCSC Part #"] = lcsc_map.get(
                    (row["Comment"], row["Footprint"]), ""
                )
            if not row["LCSC Part #"]:
                missing.append(f"{row['Designator']} ({row['Comment']})")
            rows.append(row)
    raw.unlink()
    out = OUT / "bom-jlcpcb.csv"
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["Comment", "Designator", "Footprint", "LCSC Part #"])
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out.relative_to(ROOT)} ({len(rows)} lines)")
    if missing:
        print(f"  !! {len(missing)} lines missing LCSC numbers:")
        for m in missing:
            print(f"     {m}")


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


def export_cpl() -> None:
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
        for row in csv.DictReader(f):
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
    out = OUT / "cpl-jlcpcb.csv"
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        w.writeheader()
        w.writerows(rows)
    sides = {r["Layer"] for r in rows}
    print(f"wrote {out.relative_to(ROOT)} ({len(rows)} parts, sides: {sorted(sides)})")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    export_gerbers()
    export_bom()
    export_cpl()
    print("done", file=sys.stderr)
