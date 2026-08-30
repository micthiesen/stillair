# PCB-01 V2 KiCad project

Production-intent KiCad 10 project for the 88 x 64 mm PCB-01 V2 controller. The schematic,
footprints, exact ratsnest, four-layer board setup, placement, rule areas, copper zones, keepouts,
fiducials, silkscreen, and assembly metadata are complete. All 166 footprints are on the component
side. Tracks are intentionally absent. The only two vias are the adjacent AGND returns for the USB
ESD arrays, so the next operation is manual routing.

The frozen circuit and layout authority is
[`docs/pcb-01-v2.md`](../../docs/pcb-01-v2.md). Do not import V1 routing, placement, zones, probe
coordinates, or DRC waivers.

## Open and route

Open `pcb-01-v2.kicad_pro` and route in the PCB Editor. The concise interactive routing checklist is
<https://mcp.syas.ca/boris/artifacts/art_eon2bpkmslvmtf6wfpa>.

Use the deliberately small routing vocabulary encoded in `pcb-01-v2.kicad_dru`:

| Use | Track | Via |
|---|---:|---:|
| Signals and sensitive analog | 0.20 mm | 0.60/0.30 mm |
| Local rails and 3V3 | 0.50 mm | 0.60/0.30 mm |
| RAW24, VM24, and PGND | 2.00 mm | 1.00/0.50 mm |
| PHASE_U/V/W | 2.00 mm | none |
| USB D+/D- pair | 0.20 mm, 0.20 mm gap | none |

The only narrower power exceptions are the named, tightly bounded U1 and U3 pad-escape areas. The
rules require the complete track item to remain inside the area. Widen immediately after the pad.
U1's three PGND returns use reviewed 0.60/0.30 mm escape vias because its 0.50 mm pin pitch cannot
fit the ordinary 1.00/0.50 mm power via while preserving phase clearance. The headless DRC wrapper
waives only the diameter and drill findings for those three exact via UUIDs.
Do not weaken or delete the PGND routing boundary, antenna keepout, 0.80 mm noisy-to-sensitive
clearance, mounting-hole keepouts, or fiducial keepouts to complete routing.

The stack is 1.6 mm FR-4, four layers, with 2 oz outer and 1 oz inner copper. In1.Cu is the AGND
plane. In2.Cu contains the 3V3 region and motor-region copper defined in the board. Ordinary minimum
clearance is 0.20 mm; 24 V and motor-phase clearance is 0.25 mm; copper-to-edge is 0.50 mm.

## Current verification state

- ERC: zero violations.
- Schematic parity: 159 refs, 78 named nets, and 411 endpoints match the frozen schedule.
- Board: 166 top-side footprints, zero tracks, and two intentional USB-ESD AGND vias.
- Pre-route DRC: 328 expected unconnected items and one expected `isolated_copper` warning from the
  wholly unrouted In2 3V3 region; no other violation.
- Probe map: 31 test points and four pin-mapped connectors match the board.
- Assembly export: 55 machine BOM lines, 119 top-side CPL placements, and six hand refs.

After routing, refill all zones and require zero unconnected items and zero unexplained DRC
violations. The current isolated-copper warning must also disappear when its connections are
routed.

Useful checks from the repository root:

```bash
kicad-cli sch erc pcb/pcb-01-v2/pcb-01-v2.kicad_sch
python3 pcb/tools/check_drc.py
kicad-cli sch export netlist --output /tmp/pcb-01-v2.net pcb/pcb-01-v2/pcb-01-v2.kicad_sch
python3 pcb/tools/check_v2_capture.py /tmp/pcb-01-v2.net
python3 pcb/tools/probe_guide.py --map pcb/pcb-01-v2/probe-map.json \
  --board pcb/pcb-01-v2/pcb-01-v2.kicad_pcb --verify-board
python3 pcb/tools/jlc_fab.py pcb-01-v2 --assembly-only
```

## Fabrication handoff

The tracked `fab/` directory contains the exact LCSC map, assembly/hand manifests, machine BOM,
CPL, POFV coordinates, fabrication notes, and a generated four-page assembly locator. U1's twelve
0.30 mm pad-41 holes require filled-and-capped POFV and outer-mask tenting; the coordinates are
derived and validated from the current board each time the generator runs. U3 pads 4 and 5 are
mask-defined and require JLC engineering confirmation.

Do not run a release export or order this unrouted board. After routing and the zero-unconnected DRC
gate, run `python3 pcb/tools/jlc_fab.py pcb-01-v2`, inspect the generated Gerbers, drill map, BOM,
CPL, POFV notes, and assembly locator, then apply the order requirements in
`fab/fabrication-notes.md`.
