"""Apply footprint positions to the board file in one pass, then verify.

WARNING on rotation: pad (at x y angle) angles in .kicad_pcb are ABSOLUTE
(footprint angle + pad-local angle). When --rot changes a footprint's angle by
delta, this script adds the same delta to every pad angle in that footprint,
matching what KiCad's own rotate does. Graphics (fp_line/rect/circle) use
footprint-local coords and need no correction.

Usage: python3 apply_positions.py moves.json [--rot rotmoves.json]

moves.json: {"REF": [x, y], ...} in mm (KiCad frame). Only the footprint-level
"(at x y [rot])" line of each named footprint is rewritten; rotation is
preserved unless --rot supplies {"REF": angle}. After writing, the board is
re-parsed by kicad-cli (drc run with a throwaway report); a parse failure
restores the backup and exits non-zero.

KiCad MUST be closed while this runs (single-writer rule).
"""

import json
import re
import shutil
import subprocess
import sys

BOARD_FILE = "/Users/michael/Code/stillair/pcb/pcb-01/pcb-01.kicad_pcb"
KICAD_CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"


def main():
    moves = json.load(open(sys.argv[1]))
    rots = {}
    if "--rot" in sys.argv:
        rots = json.load(open(sys.argv[sys.argv.index("--rot") + 1]))

    text = open(BOARD_FILE).read()
    backup = BOARD_FILE + ".bak"
    shutil.copy(BOARD_FILE, backup)

    applied = []

    def patch_block(m):
        blk = m.group(0)
        ref_m = re.search(r'\(property "Reference" "([^"]+)"', blk)
        if not ref_m:
            return blk
        ref = ref_m.group(1)
        if ref not in moves and ref not in rots:
            return blk
        at_m = re.search(r'(\n\t\t\(at )([\-\d.]+) ([\-\d.]+)((?: [\-\d.]+)?\))', blk)
        if not at_m:
            return blk
        x, y = moves.get(ref, (float(at_m.group(2)), float(at_m.group(3))))
        tail = at_m.group(4)
        blk2 = blk
        if ref in rots:
            old_rot = float((at_m.group(4) or " )").strip(" )") or 0)
            delta = (rots[ref] - old_rot) % 360
            tail = f" {rots[ref]:g})"
            if delta:
                def fix_pad(pm):
                    base = float(pm.group(4) or 0)
                    na = (base + delta) % 360
                    return f'{pm.group(1)}(at {pm.group(2)} {pm.group(3)}{f" {na:g}" if na else ""})'
                blk2 = re.sub(r'(\(pad "[^"]*" \w+ \w+\s*)\(at ([\-\d.]+) ([\-\d.]+)(?: ([\-\d.]+))?\)',
                              fix_pad, blk)
                at_m2 = re.search(r'(\n\t\t\(at )([\-\d.]+) ([\-\d.]+)((?: [\-\d.]+)?\))', blk2)
                applied.append(ref)
                return blk2[:at_m2.start()] + f"{at_m2.group(1)}{x:g} {y:g}{tail}" + blk2[at_m2.end():]
        new_at = f"{at_m.group(1)}{x:g} {y:g}{tail}"
        applied.append(ref)
        # Also shift pad/graphic coords? No - they are footprint-local; only the
        # anchor moves. KiCad recomputes everything else on load.
        return blk[:at_m.start()] + new_at + blk[at_m.end():]

    text = re.sub(r'\(footprint "[^"]+"(?:.*?)\n\t\)', patch_block, text, flags=re.S)
    open(BOARD_FILE, "w").write(text)

    missing = sorted(set(moves) - set(applied))
    if missing:
        print("WARNING not found on board:", missing)

    res = subprocess.run(
        [KICAD_CLI, "pcb", "drc", "--output", "/tmp/apply-verify.json",
         "--format", "json", BOARD_FILE],
        capture_output=True, text=True,
    )
    if "Failed to load board" in res.stdout + res.stderr or res.returncode == 3:
        shutil.copy(backup, BOARD_FILE)
        print("PARSE FAILED - board restored from backup")
        sys.exit(1)
    print(f"applied {len(applied)} positions; board parses OK")


if __name__ == "__main__":
    main()
