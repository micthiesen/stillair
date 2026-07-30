#!/bin/bash
# Render the board to PNG for visual review. Usage: render_board.sh [out.png]
# Override the board with STILLAIR_BOARD (defaults to PCB-01).
set -e
BOARD="${STILLAIR_BOARD:-/Users/michael/Code/stillair/pcb/pcb-01/pcb-01.kicad_pcb}"
OUT="${1:-/tmp/pcb01-render.png}"
SVG="$(mktemp /tmp/pcb01-XXXX.svg)"
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli pcb export svg \
  --output "$SVG" --layers F.Cu,B.Cu,Edge.Cuts,F.SilkS --page-size-mode 2 \
  "$BOARD" >/dev/null 2>&1
rsvg-convert -w 1900 -o "$OUT" "$SVG"
rm -f "$SVG"
echo "$OUT"
