#!/usr/bin/env python3
"""Add compact PGND drops and phase-pair landings below PCB-01 V2 U1.

The bottom edge of U1 interleaves three phase pairs with PGND pads.  These
F.Cu zones join each same-phase pad pair immediately, fan the three phases
toward their matching J2 pins, and drop each PGND pad into the In1 PGND
island without putting a ground bar across the phase corridor.

KiCad must be closed when this script writes the live board.  It is safe to
run repeatedly: named zones are updated in place and existing matching vias
are reused.
"""

import argparse
import math
import shutil
import subprocess
import tempfile
from pathlib import Path

import pcbnew


KICAD_CLI = Path("/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")

# The standard 1.00/0.50 mm POWER24 vias fit below the 0.50 mm-pitch phase
# pads when their centers sit 0.70 mm below the pad edges.  Their short barrels
# land directly in the In1 PGND island; no PGND track crosses the F.Cu phase
# corridor.
PGND_VIAS = (
    (81.75, 98.40),
    (83.25, 98.40),
    (84.75, 98.40),
)

ZONES = {
    "F.Cu U1 PGND12 drop": {
        "net": "PGND",
        "outline": (
            (81.300, 96.625),
            (81.875, 96.625),
            (81.875, 97.950),
            (82.250, 98.100),
            (82.250, 98.900),
            (81.250, 98.900),
            (81.300, 98.100),
            (81.300, 96.875),
        ),
    },
    "F.Cu U1 PGND15 drop": {
        "net": "PGND",
        "outline": (
            (83.125, 97.100),
            (83.375, 97.100),
            (83.375, 97.750),
            (83.750, 98.050),
            (83.750, 98.900),
            (82.750, 98.900),
            (82.850, 98.050),
            (83.125, 97.750),
        ),
    },
    "F.Cu U1 PGND18 drop": {
        "net": "PGND",
        "outline": (
            (84.625, 97.100),
            (84.875, 97.100),
            (84.875, 97.750),
            (85.250, 98.050),
            (85.250, 98.900),
            (84.250, 98.900),
            (84.350, 98.050),
            (84.625, 97.750),
        ),
    },
    "F.Cu U1 PHASE_U landing": {
        "net": "PHASE_U",
        "outline": (
            (82.125, 97.100),
            (82.875, 97.100),
            (82.875, 98.550),
            (83.500, 99.150),
            (83.500, 100.500),
            (81.500, 100.500),
            (81.500, 99.150),
            (82.125, 98.550),
        ),
    },
    "F.Cu U1 PHASE_V landing": {
        "net": "PHASE_V",
        "outline": (
            (83.625, 97.100),
            (84.375, 97.100),
            (84.375, 98.550),
            (86.250, 99.500),
            (86.250, 100.500),
            (84.250, 100.500),
            (84.250, 99.500),
            (83.625, 98.550),
        ),
    },
    "F.Cu U1 PHASE_W landing": {
        "net": "PHASE_W",
        "outline": (
            (85.125, 97.100),
            (85.875, 97.100),
            (85.875, 98.550),
            (89.000, 99.500),
            (89.000, 100.500),
            (87.000, 100.500),
            (87.000, 99.500),
            (85.125, 98.550),
        ),
    },
}

IN2_NPTH_KEEPOUTS = {
    "J1 NPTH In2 clearance": (52.18, 77.00),
    "J2 NPTH In2 clearance": (85.50, 108.82),
}


def mm(value: float) -> int:
    return pcbnew.FromMM(value)


def point(x: float, y: float) -> pcbnew.VECTOR2I:
    return pcbnew.VECTOR2I(mm(x), mm(y))


def set_outline(zone: pcbnew.ZONE, vertices: tuple[tuple[float, float], ...]) -> None:
    zone.RemoveAllContours()
    polygon = zone.Outline()
    index = polygon.NewOutline()
    for x, y in vertices:
        polygon.Append(point(x, y), index)


def upsert_zone(board: pcbnew.BOARD, name: str, spec: dict) -> tuple[pcbnew.ZONE, bool]:
    matches = [zone for zone in board.Zones() if zone.GetZoneName() == name]
    if len(matches) > 1:
        raise SystemExit(f"found multiple zones named {name!r}")
    created = not matches
    zone = matches[0] if matches else pcbnew.ZONE(board)
    zone.SetZoneName(name)
    zone.SetLayer(pcbnew.F_Cu)
    zone.SetNet(board.GetNetsByName()[spec["net"]])
    zone.SetAssignedPriority(9)
    zone.SetLocalClearance(mm(0.25))
    zone.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    zone.SetMinThickness(mm(0.15))
    zone.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    set_outline(zone, spec["outline"])
    if created:
        board.Add(zone)
    return zone, created


def upsert_in2_npth_keepout(
    board: pcbnew.BOARD, name: str, center: tuple[float, float]
) -> tuple[pcbnew.ZONE, bool]:
    matches = [zone for zone in board.Zones() if zone.GetZoneName() == name]
    if len(matches) > 1:
        raise SystemExit(f"found multiple rule areas named {name!r}")
    created = not matches
    zone = matches[0] if matches else pcbnew.ZONE(board)
    zone.SetZoneName(name)
    zone.SetLayer(pcbnew.In2_Cu)
    zone.SetIsRuleArea(True)
    zone.SetDoNotAllowFootprints(False)
    zone.SetDoNotAllowPads(False)
    zone.SetDoNotAllowTracks(False)
    zone.SetDoNotAllowVias(False)
    zone.SetDoNotAllowZoneFills(True)
    # The locating holes are 3.00 mm.  A 1.81 mm, 32-sided boundary keeps
    # every polygon edge just beyond the required 0.30 mm copper clearance.
    cx, cy = center
    vertices = tuple(
        (
            cx + 1.81 * math.cos(2.0 * math.pi * index / 32),
            cy + 1.81 * math.sin(2.0 * math.pi * index / 32),
        )
        for index in range(32)
    )
    set_outline(zone, vertices)
    if created:
        board.Add(zone)
    return zone, created


def add_pgnd_vias(board: pcbnew.BOARD) -> int:
    existing = list(board.GetTracks())
    pgnd = board.GetNetsByName()["PGND"]
    added = 0
    for x, y in PGND_VIAS:
        position = point(x, y)
        duplicate = any(
            isinstance(item, pcbnew.PCB_VIA)
            and item.GetPosition() == position
            and item.GetNetname() == "PGND"
            for item in existing
        )
        if duplicate:
            continue
        via = pcbnew.PCB_VIA(board)
        via.SetPosition(position)
        via.SetWidth(mm(1.00))
        via.SetDrill(mm(0.50))
        via.SetNet(pgnd)
        board.Add(via)
        existing.append(via)
        added += 1
    return added


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("board", type=Path)
    args = parser.parse_args()
    board_path = args.board.resolve()

    with tempfile.TemporaryDirectory(prefix="stillair-u1-bottom-landings-") as tmp:
        backup = Path(tmp) / board_path.name
        shutil.copy2(board_path, backup)
        board = pcbnew.LoadBoard(str(board_path))
        zone_results = [upsert_zone(board, name, spec) for name, spec in ZONES.items()]
        landing_zones = [zone for zone, _created in zone_results]
        created_zones = sum(created for _zone, created in zone_results)
        keepout_results = [
            upsert_in2_npth_keepout(board, name, center)
            for name, center in IN2_NPTH_KEEPOUTS.items()
        ]
        created_zones += sum(created for _zone, created in keepout_results)
        added_vias = add_pgnd_vias(board)
        vm24_planes = [
            zone for zone in board.Zones() if zone.GetZoneName() == "In2 VM24 region"
        ]
        if len(vm24_planes) != 1:
            raise SystemExit(
                f"expected one In2 VM24 region, found {len(vm24_planes)}"
            )
        vm24_plane = vm24_planes[0]
        # Through-via holes need the board-wide 0.30 mm copper clearance.  The
        # older 0.25 mm local setting otherwise overrides that rule on refill.
        vm24_plane.SetLocalClearance(mm(0.30))
        pcbnew.ZONE_FILLER(board).Fill([*landing_zones, vm24_plane])
        pcbnew.SaveBoard(str(board_path), board)

        drc_path = Path(tmp) / "drc.json"
        verify = subprocess.run(
            [
                str(KICAD_CLI),
                "pcb",
                "drc",
                "--format",
                "json",
                "--severity-all",
                "--output",
                str(drc_path),
                str(board_path),
            ],
            capture_output=True,
            text=True,
        )
        output = verify.stdout + verify.stderr
        if "Failed to load board" in output or verify.returncode == 3:
            shutil.copy2(backup, board_path)
            raise SystemExit("U1 bottom landings produced an unreadable board; original restored")

    print(
        f"updated U1 bottom landings in {board_path}; "
        f"created {created_zones} zones and added {added_vias} PGND vias"
    )


if __name__ == "__main__":
    main()
