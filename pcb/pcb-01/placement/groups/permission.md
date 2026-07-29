# Group: permission

Region (absolute board mm, Y down): x 94..104, y 79..98

## Intent

Safety permission latch. U5 (SN74LVC1G74 latch) central. Q2 2N7002K (pad1=gate, pad2=source=AGND, pad3=drain=DRVOFF) at the region WEST edge - its drain net DRVOFF runs to U1 pin 21 on U1's east edge, keep that run short. R26 (1k U5.Q->gate) + R27 (100k gate pulldown) at Q2. R28 (4.7k DRVOFF pullup to MCF_AVDD) near Q2. R24 (100R ARM_PULSE series) + R25 (100k CLK pulldown) at U5's CLK side. Wired-OR: R29 (10k pullup) + five BAT54H diodes D3-D7 (pad1=cathode=fault source, pad2=anode=U5_CLR_OR node) in a tidy bank feeding U10 (Schmitt buffer) -> U5 CLR. C22 (100nF) tight to U10 VCC. D7's cathode goes to SW3 manual-clear button (pinned at south edge (97,101.5)) - put D7/R30 nearest SW3. TP10=U5_CLR_OR, TP11=U5_Q, TP24=OVERSPEED_N, TP27=PGND probe.

## Members (courtyard size at CURRENT rotation; rotating 90/270 swaps w/h)

| ref | w x h | rot | pads (num:net at local offset) |
|---|---|---|---|
| U5 | 5.95 x 2.95 | 0 | 1:/SCH-05 Permission + Watchdog/U5_CLK@(-1.9,-1.0); 2:3V3@(-1.9,-0.3); 3:unconnected-(U5-~{Q}-Pad3)@(-1.9,+0.3); 4:AGND@(-1.9,+1.0); 5:U5_Q@(+1.9,+1.0); 6:/SCH-05 Permission + Watchdog/U5_CLR_BUF@(+1.9,+0.3); 7:3V3@(+1.9,-0.3); 8:3V3@(+1.9,-1.0) |
| U10 | 3.00 x 2.30 | 0 | 1:unconnected-(U10-NC-Pad1)@(-0.8,-0.7); 2:U5_CLR_OR@(-0.8,+0.0); 3:AGND@(-0.8,+0.7); 4:/SCH-05 Permission + Watchdog/U5_CLR_BUF@(+0.8,+0.7); 5:3V3@(+0.8,-0.7) |
| Q2 | 3.96 x 3.50 | 0 | 1:/SCH-05 Permission + Watchdog/Q2_GATE@(-0.9,-0.9); 2:AGND@(-0.9,+0.9); 3:DRVOFF@(+0.9,+0.0) |
| C22 | 2.02 x 1.12 | 0 | 1:3V3@(-0.5,+0.0); 2:AGND@(+0.5,+0.0) |
| R24 | 2.06 x 1.14 | 0 | 1:ARM_PULSE@(-0.5,+0.0); 2:/SCH-05 Permission + Watchdog/U5_CLK@(+0.5,+0.0) |
| R25 | 2.06 x 1.14 | 0 | 1:/SCH-05 Permission + Watchdog/U5_CLK@(-0.5,+0.0); 2:AGND@(+0.5,+0.0) |
| R26 | 2.06 x 1.14 | 0 | 1:U5_Q@(-0.5,+0.0); 2:/SCH-05 Permission + Watchdog/Q2_GATE@(+0.5,+0.0) |
| R27 | 2.06 x 1.14 | 0 | 1:/SCH-05 Permission + Watchdog/Q2_GATE@(-0.5,+0.0); 2:AGND@(+0.5,+0.0) |
| R28 | 2.06 x 1.14 | 0 | 1:MCF_AVDD@(-0.5,+0.0); 2:DRVOFF@(+0.5,+0.0) |
| R29 | 2.06 x 1.14 | 0 | 1:3V3@(-0.5,+0.0); 2:U5_CLR_OR@(+0.5,+0.0) |
| R30 | 2.06 x 1.14 | 0 | 1:3V3@(-0.5,+0.0); 2:/SCH-05 Permission + Watchdog/SW_CLR@(+0.5,+0.0) |
| D3 | 4.81 x 2.40 | 0 | 1:PGOOD@(-1.6,+0.0); 2:U5_CLR_OR@(+1.6,+0.0) |
| D4 | 4.81 x 2.40 | 0 | 1:WDO@(-1.6,+0.0); 2:U5_CLR_OR@(+1.6,+0.0) |
| D5 | 4.81 x 2.40 | 0 | 1:OS_LOCK_OK@(-1.6,+0.0); 2:U5_CLR_OR@(+1.6,+0.0) |
| D6 | 4.81 x 2.40 | 0 | 1:MCU_CLEAR_N@(-1.6,+0.0); 2:U5_CLR_OR@(+1.6,+0.0) |
| D7 | 4.81 x 2.40 | 0 | 1:/SCH-05 Permission + Watchdog/SW_CLR@(-1.6,+0.0); 2:U5_CLR_OR@(+1.6,+0.0) |
| TP10 | 2.00 x 2.00 | 0 | 1:U5_CLR_OR@(+0.0,+0.0) |
| TP11 | 2.00 x 2.00 | 0 | 1:U5_Q@(+0.0,+0.0) |
| TP24 | 2.00 x 2.00 | 0 | 1:OVERSPEED_N@(+0.0,+0.0) |
| TP27 | 2.00 x 2.00 | 0 | 1:PGND@(+0.0,+0.0) |

## Pinned obstacles in/near the region (absolute boxes - do not overlap)

| ref | box |
|---|---|
| J2 | (83.5,100.1)-(94.5,113.9) |
| J7 | (104.5,76.5)-(111.5,80.5) |
| SW3 | (91.9,98.0)-(102.1,105.0) |

## Output contract

Return ONLY a JSON object: {"REF": [x, y, rot], ...} for every member.
x,y are the footprint ANCHOR position in absolute board mm. The courtyard
box is centred on the anchor only approximately; assume anchor = courtyard
centre and keep 0.15 mm slack between neighbouring courtyards. rot must be
0, 90, 180, or 270 (90/270 swaps the courtyard w/h). Every courtyard fully
inside the region; no overlaps among members or with the obstacle boxes.
