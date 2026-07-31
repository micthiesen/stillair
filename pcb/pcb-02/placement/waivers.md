# PCB-02 DRC waivers baseline

Reference for the routing-session DRC diff loop (same workflow as PCB-01: Michael saves,
Claude runs `kicad-cli pcb drc --format json --severity-all` and diffs type counts against
this file).

Baseline after placement, before routing (2026-07-30):

| Type | Count | Why it's accepted |
|---|---|---|
| `silk_edge_clearance` | 8 | All are J1's own body outline crossing the two long board edges: the S3B-PH-K silk/courtyard is 8.9 mm across on an 8.0 mm board. The physical body is 7.9 mm and sits fully on board (0.05 mm per side) — the spec's 8 mm width was chosen around exactly this. Cosmetic. |

Unconnected items: 5 at baseline (the unrouted ratsnest: 3V3 ×2, AGND ×2, HALL_TACH ×1).
Must be 0 when routing is done.

**Routed state (2026-07-30): 8 silk_edge_clearance, 0 unconnected, nothing else** —
exactly the baseline. Routing: 3V3 north F.Cu run, HALL_TACH south F.Cu run, AGND via
B.Cu pour with vias at C1.2/U1.3 (J1.3 joins the pour as a through-hole).

Review-swarm placement notes (2026-07-30, accepted as-is):
- J1's body back face sits ~0.05 mm inside the x=74 edge (flush-at-edge convention,
  same as PCB-01's right-angle connectors); its courtyard extends 0.45 mm past the edge
  on the mating side only. Real-part tolerance may leave the housing a hair proud of
  the edge — harmless plastic over air; the cable mates in free air, not through a panel.
- H1 hardware is constrained: bare pan head or washer ≤Ø4.5 (standard Ø5 washer comes
  within ~0.33 mm of U1 pin 3's solder joint). Documented in electrical.md.

Anything outside this table — especially any class touching copper, edge, or holes — gets
triaged item by item, never lumped into "residual noise" (PCB-01 lesson).
