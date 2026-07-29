# Group: input

Region (absolute board mm, Y down): x 51.5..74, y 60..87

## Intent

24V entry chain: J1 (pinned, left edge, pin1=RAW24 upper) -> F1 (DNP bridge fuse) -> Q1 reverse PMOS (pad2=drain=RAW24, pad3=source=VM24) -> VM24 joins C1/C2 bulk (pinned radials) then flows east to the MCF. Keep the RAW24->Q1->VM24 path short and wide. Gate network R1 (10k to AGND), R2 (100k gate-source), D1 zener (pad1=cathode=VM24, pad2=anode=gate) cluster tight at Q1's gate. D2 SMCJ24A TVS (pad1=cathode=VM24, pad2=anode=PGND) adjacent to the VM24 node. C3/C4 10uF + C5 100nF are the MCF-loop ceramics: place at the region's EAST edge so they sit beside U1's VM pins. TP1=RAW24 near J1, TP2=VM24, TP3=PGND probe-accessible.

## Members (courtyard size at CURRENT rotation; rotating 90/270 swaps w/h)

| ref | w x h | rot | pads (num:net at local offset) |
|---|---|---|---|
| F1 | 4.55 x 2.25 | 0 | 1:/SCH-07 Connectors/RAW24_IN@(-1.4,+0.0); 2:RAW24@(+1.4,+0.0) |
| Q1 | 8.90 x 7.30 | 0 | 1:/SCH-01 24V Input/PMOS_GATE@(-3.1,-2.3); 2:RAW24@(-3.1,+0.0); 2:RAW24@(+3.1,+0.0); 3:VM24@(-3.1,+2.3) |
| R1 | 2.06 x 1.14 | 0 | 1:/SCH-01 24V Input/PMOS_GATE@(-0.5,+0.0); 2:AGND@(+0.5,+0.0) |
| R2 | 2.06 x 1.14 | 0 | 1:VM24@(-0.5,+0.0); 2:/SCH-01 24V Input/PMOS_GATE@(+0.5,+0.0) |
| D1 | 4.81 x 2.40 | 0 | 1:VM24@(-1.6,+0.0); 2:/SCH-01 24V Input/PMOS_GATE@(+1.6,+0.0) |
| D2 | 9.91 x 6.80 | 0 | 1:VM24@(-3.4,+0.0); 2:PGND@(+3.4,+0.0) |
| C3 | 4.60 x 3.20 | 0 | 1:VM24@(-1.5,+0.0); 2:PGND@(+1.5,+0.0) |
| C4 | 4.60 x 3.20 | 0 | 1:VM24@(-1.5,+0.0); 2:PGND@(+1.5,+0.0) |
| C5 | 2.95 x 1.45 | 0 | 1:VM24@(-0.8,+0.0); 2:PGND@(+0.8,+0.0) |
| TP1 | 2.00 x 2.00 | 0 | 1:RAW24@(+0.0,+0.0) |
| TP2 | 2.00 x 2.00 | 0 | 1:VM24@(+0.0,+0.0) |
| TP3 | 2.00 x 2.00 | 0 | 1:PGND@(+0.0,+0.0) |

## Pinned obstacles in/near the region (absolute boxes - do not overlap)

| ref | box |
|---|---|
| J1 | (47.0,74.9)-(60.8,83.1) |
| L1 | (72.6,89.7)-(79.4,96.3) |
| C1 | (56.8,60.8)-(67.2,71.2) |
| C2 | (67.9,60.8)-(78.3,71.2) |
| C6 | (62.3,82.8)-(72.7,93.2) |
| H3 | (53.9,53.9)-(58.1,58.1) |

Mounting-hole keepout: circle r=4.0 at (56.0,56.0) - keep courtyards outside it.

## Output contract

Return ONLY a JSON object: {"REF": [x, y, rot], ...} for every member.
x,y are the footprint ANCHOR position in absolute board mm. The courtyard
box is centred on the anchor only approximately; assume anchor = courtyard
centre and keep 0.15 mm slack between neighbouring courtyards. rot must be
0, 90, 180, or 270 (90/270 swaps the courtyard w/h). Every courtyard fully
inside the region; no overlaps among members or with the obstacle boxes.
