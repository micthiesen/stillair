#!/bin/bash
set -euo pipefail

kicad_contents="/Applications/KiCad/KiCad.app/Contents"
kicad_python="$kicad_contents/Frameworks/Python.framework/Versions/3.9/Resources/Python.app/Contents/MacOS/Python"
kicad_site_packages="$kicad_contents/Frameworks/Python.framework/Versions/3.9/lib/python3.9/site-packages"

if [[ ! -x "$kicad_python" ]]; then
    echo "KiCad's bundled Python was not found at $kicad_python" >&2
    exit 1
fi

export DYLD_FRAMEWORK_PATH="$kicad_contents/Frameworks${DYLD_FRAMEWORK_PATH:+:$DYLD_FRAMEWORK_PATH}"
export DYLD_LIBRARY_PATH="$kicad_contents/Frameworks${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}"
export PYTHONPATH="$kicad_site_packages${PYTHONPATH:+:$PYTHONPATH}"

exec "$kicad_python" "$@"
