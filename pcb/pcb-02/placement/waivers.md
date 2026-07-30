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

Anything outside this table — especially any class touching copper, edge, or holes — gets
triaged item by item, never lumped into "residual noise" (PCB-01 lesson).
