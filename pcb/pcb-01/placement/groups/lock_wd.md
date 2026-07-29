# Group: lock_wd

Region (absolute board mm, Y down): x 104..112, y 79..94

## Intent

North half: U6 persistent lock (second 1G74) + its delayed-preset chain: R31 (100k) -> C23 (10uF RC) -> U11 Schmitt -> U6 /PRE, with D8 (pad1=cathode=PGOOD, pad2=anode=RC node) discharge diode; keep R31/C23/D8/U11 a compact chain, C24 (100nF) tight to U11 VCC. J7 (pinned obstacle at (107.5,78.5), courtyard (104-111, 76.5-80.5)) intrudes at your NW corner. South half: U7 TPS3435 watchdog with C25 (100nF) tight to VDD, R32/R33 (SET0/1 to AGND) beside it, R34 (MR pullup), R35 (WD-EN pullup), R36 (100R heartbeat->WDI), R37 (10k WDO pullup), R38 (100R heartbeat->MCF EXT_WD; EXT_WD is U1 pin 32 to the WEST - put R38 at the west edge). TP15=WD_MR.

## Members (courtyard size at CURRENT rotation; rotating 90/270 swaps w/h)

| ref | w x h | rot | pads (num:net at local offset) |
|---|---|---|---|
| U6 | 5.95 x 2.95 | 0 | 1:AGND@(-1.9,-1.0); 2:3V3@(-1.9,-0.3); 3:unconnected-(U6-~{Q}-Pad3)@(-1.9,+0.3); 4:AGND@(-1.9,+1.0); 5:OS_LOCK_OK@(+1.9,+1.0); 6:OVERSPEED_N@(+1.9,+0.3); 7:/SCH-05 Permission + Watchdog/U6_PRE_BUF@(+1.9,-0.3); 8:3V3@(+1.9,-1.0) |
| U11 | 3.00 x 2.30 | 0 | 1:unconnected-(U11-NC-Pad1)@(-0.8,-0.7); 2:/SCH-05 Permission + Watchdog/U6_PRE_RC@(-0.8,+0.0); 3:AGND@(-0.8,+0.7); 4:/SCH-05 Permission + Watchdog/U6_PRE_BUF@(+0.8,+0.7); 5:3V3@(+0.8,-0.7) |
| C23 | 3.40 x 1.95 | 0 | 1:/SCH-05 Permission + Watchdog/U6_PRE_RC@(-0.9,+0.0); 2:AGND@(+0.9,+0.0) |
| C24 | 2.02 x 1.12 | 0 | 1:3V3@(-0.5,+0.0); 2:AGND@(+0.5,+0.0) |
| R31 | 2.06 x 1.14 | 0 | 1:3V3@(-0.5,+0.0); 2:/SCH-05 Permission + Watchdog/U6_PRE_RC@(+0.5,+0.0) |
| D8 | 4.81 x 2.40 | 0 | 1:PGOOD@(-1.6,+0.0); 2:/SCH-05 Permission + Watchdog/U6_PRE_RC@(+1.6,+0.0) |
| U7 | 4.20 x 3.50 | 0 | 1:/SCH-05 Permission + Watchdog/SET0@(-1.1,-1.0); 2:WD_MR@(-1.1,-0.3); 3:/SCH-05 Permission + Watchdog/U7_WDI@(-1.1,+0.3); 4:AGND@(-1.1,+1.0); 5:/SCH-05 Permission + Watchdog/SET1@(+1.1,+1.0); 6:/SCH-05 Permission + Watchdog/WD_EN@(+1.1,+0.3); 7:WDO@(+1.1,-0.3); 8:3V3@(+1.1,-1.0) |
| C25 | 2.02 x 1.12 | 0 | 1:3V3@(-0.5,+0.0); 2:AGND@(+0.5,+0.0) |
| R32 | 2.06 x 1.14 | 0 | 1:/SCH-05 Permission + Watchdog/SET0@(-0.5,+0.0); 2:AGND@(+0.5,+0.0) |
| R33 | 2.06 x 1.14 | 0 | 1:/SCH-05 Permission + Watchdog/SET1@(-0.5,+0.0); 2:AGND@(+0.5,+0.0) |
| R34 | 2.06 x 1.14 | 0 | 1:3V3@(-0.5,+0.0); 2:WD_MR@(+0.5,+0.0) |
| R35 | 2.06 x 1.14 | 0 | 1:3V3@(-0.5,+0.0); 2:/SCH-05 Permission + Watchdog/WD_EN@(+0.5,+0.0) |
| R36 | 2.06 x 1.14 | 0 | 1:WD_HEARTBEAT@(-0.5,+0.0); 2:/SCH-05 Permission + Watchdog/U7_WDI@(+0.5,+0.0) |
| R37 | 2.06 x 1.14 | 0 | 1:3V3@(-0.5,+0.0); 2:WDO@(+0.5,+0.0) |
| R38 | 2.06 x 1.14 | 0 | 1:WD_HEARTBEAT@(-0.5,+0.0); 2:MCF_EXT_WD@(+0.5,+0.0) |
| TP15 | 2.00 x 2.00 | 0 | 1:WD_MR@(+0.0,+0.0) |

## Pinned obstacles in/near the region (absolute boxes - do not overlap)

| ref | box |
|---|---|
| J7 | (104.5,76.5)-(111.5,80.5) |

## Output contract

Return ONLY a JSON object: {"REF": [x, y, rot], ...} for every member.
x,y are the footprint ANCHOR position in absolute board mm. The courtyard
box is centred on the anchor only approximately; assume anchor = courtyard
centre and keep 0.15 mm slack between neighbouring courtyards. rot must be
0, 90, 180, or 270 (90/270 swaps the courtyard w/h). Every courtyard fully
inside the region; no overlaps among members or with the obstacle boxes.
