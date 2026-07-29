# Group: tach

Region (absolute board mm, Y down): x 112..127, y 79..94

## Intent

Analog tach chain, now allowed in the antenna band (copper keepout stays; parts are low-profile so RF impact accepted). U8 LM2907 SOIC-14 central-west (pin1 top-left going CCW; left column pins 1-7 at its west edge, right column 8-14 east). Level shift at NW: Q3 2N7002 (pad1=gate=HALL_TACH, pad2=source=AGND, pad3=drain) + R43 (100k gate pulldown) + R44 (10k drain pullup to +12V_TACH) + R45 (100R drain->U8 pin 1). C34 (100nF 1% timing, U8 pin 2 to AGND) TIGHT to pin 2 - most critical cap in the group. R46/R47 (10k/10k TACH_BIAS divider) + C33 (100nF) at pin 11. Rscale: R48 (562k) + RV1 trimmer (rheostat) from pin 3, RV1 adjustable from above - keep its screw clear. C35 (2.2uF C2 filter) at pin 3; C36-C40 are DNP alternates - tidy row near C35. R49 (10k emitter load) at pin 5. Trip stage east: U9 TLV1701 (pin1=IN+ VREF, pin3=IN- via R51 47k from VTACH, pin4=OUT=OVERSPEED_N, pin5=V+ 3V3, pin2=V-), D9 BAT54S clamp (pad3=common) at IN-, C41 (100nF) at U9 V+, R52/R53 (VREF divider 10k/35.7k), R54 (90.9k hysteresis OVERSPEED_N->VREF), R50 (10k OVERSPEED_N pullup), R42 (10k TACH_PGOOD pullup, same node). TP21=HALL_TACH, TP22=VTACH, TP23=VREF. Avoid the H4 hole keepout (circle r4 at (122,56) is far north of you; H2 keepout circle r4 at (122,102) is south of you - both outside this region).

## Members (courtyard size at CURRENT rotation; rotating 90/270 swaps w/h)

| ref | w x h | rot | pads (num:net at local offset) |
|---|---|---|---|
| U8 | 7.50 x 9.26 | 0 | 1:/SCH-06 Hall Tach/LM_TACHIN@(-2.5,-3.8); 2:/SCH-06 Hall Tach/TACH_CP1@(-2.5,-2.5); 3:/SCH-06 Hall Tach/VTACH_RAW@(-2.5,-1.3); 4:/SCH-06 Hall Tach/VTACH_RAW@(-2.5,+0.0); 5:VTACH@(-2.5,+1.3); 6:unconnected-(U8-NC-Pad6)@(-2.5,+2.5); 7:unconnected-(U8-NC-Pad7)@(-2.5,+3.8); 8:+12V_TACH@(+2.5,+3.8); 9:+12V_TACH@(+2.5,+2.5); 10:VTACH@(+2.5,+1.3); 11:/SCH-06 Hall Tach/TACH_BIAS@(+2.5,+0.0); 12:AGND@(+2.5,-1.3); 13:unconnected-(U8-NC-Pad13)@(+2.5,-2.5); 14:unconnected-(U8-NC-Pad14)@(+2.5,-3.8) |
| C33 | 2.95 x 1.45 | 0 | 1:/SCH-06 Hall Tach/TACH_BIAS@(-0.8,+0.0); 2:AGND@(+0.8,+0.0) |
| C34 | 2.95 x 1.45 | 0 | 1:/SCH-06 Hall Tach/TACH_CP1@(-0.8,+0.0); 2:AGND@(+0.8,+0.0) |
| C32 | 2.02 x 1.12 | 0 | 1:/SCH-06 Hall Tach/LM_TACHIN@(-0.5,+0.0); 2:AGND@(+0.5,+0.0) |
| C35 | 3.40 x 1.95 | 0 | 1:/SCH-06 Hall Tach/VTACH_RAW@(-0.9,+0.0); 2:AGND@(+0.9,+0.0) |
| C36 | 3.40 x 1.95 | 0 | 1:/SCH-06 Hall Tach/VTACH_RAW@(-0.9,+0.0); 2:AGND@(+0.9,+0.0) |
| C37 | 3.40 x 1.95 | 0 | 1:/SCH-06 Hall Tach/VTACH_RAW@(-0.9,+0.0); 2:AGND@(+0.9,+0.0) |
| C38 | 3.40 x 1.95 | 0 | 1:/SCH-06 Hall Tach/VTACH_RAW@(-0.9,+0.0); 2:AGND@(+0.9,+0.0) |
| C39 | 3.40 x 1.95 | 0 | 1:/SCH-06 Hall Tach/VTACH_RAW@(-0.9,+0.0); 2:AGND@(+0.9,+0.0) |
| C40 | 3.40 x 1.95 | 0 | 1:/SCH-06 Hall Tach/VTACH_RAW@(-0.9,+0.0); 2:AGND@(+0.9,+0.0) |
| R43 | 2.06 x 1.14 | 0 | 1:HALL_TACH@(-0.5,+0.0); 2:AGND@(+0.5,+0.0) |
| R44 | 2.06 x 1.14 | 0 | 1:+12V_TACH@(-0.5,+0.0); 2:/SCH-06 Hall Tach/TACH_DRAIN@(+0.5,+0.0) |
| R45 | 2.06 x 1.14 | 0 | 1:/SCH-06 Hall Tach/TACH_DRAIN@(-0.5,+0.0); 2:/SCH-06 Hall Tach/LM_TACHIN@(+0.5,+0.0) |
| R46 | 2.06 x 1.14 | 0 | 1:+12V_TACH@(-0.5,+0.0); 2:/SCH-06 Hall Tach/TACH_BIAS@(+0.5,+0.0) |
| R47 | 2.06 x 1.14 | 0 | 1:/SCH-06 Hall Tach/TACH_BIAS@(-0.5,+0.0); 2:AGND@(+0.5,+0.0) |
| R48 | 2.06 x 1.14 | 0 | 1:/SCH-06 Hall Tach/VTACH_RAW@(-0.5,+0.0); 2:/SCH-06 Hall Tach/RSCALE_MID@(+0.5,+0.0) |
| RV1 | 4.30 x 5.00 | 0 | 1:/SCH-06 Hall Tach/RSCALE_MID@(+1.2,-1.4); 2:AGND@(+0.0,+1.4); 3:AGND@(-1.2,-1.4) |
| Q3 | 3.96 x 3.50 | 0 | 1:HALL_TACH@(-0.9,-0.9); 2:AGND@(-0.9,+0.9); 3:/SCH-06 Hall Tach/TACH_DRAIN@(+0.9,+0.0) |
| U9 | 4.20 x 3.50 | 0 | 1:VREF@(-1.1,-0.9); 2:AGND@(-1.1,+0.0); 3:/SCH-06 Hall Tach/TLV_INN@(-1.1,+0.9); 4:OVERSPEED_N@(+1.1,+0.9); 5:3V3@(+1.1,-0.9) |
| D9 | 3.96 x 3.50 | 0 | 1:AGND@(-0.9,-0.9); 2:3V3@(-0.9,+0.9); 3:/SCH-06 Hall Tach/TLV_INN@(+0.9,+0.0) |
| C41 | 2.02 x 1.12 | 0 | 1:3V3@(-0.5,+0.0); 2:AGND@(+0.5,+0.0) |
| R42 | 2.06 x 1.14 | 0 | 1:3V3@(-0.5,+0.0); 2:OVERSPEED_N@(+0.5,+0.0) |
| R49 | 2.06 x 1.14 | 0 | 1:VTACH@(-0.5,+0.0); 2:AGND@(+0.5,+0.0) |
| R50 | 2.06 x 1.14 | 0 | 1:3V3@(-0.5,+0.0); 2:OVERSPEED_N@(+0.5,+0.0) |
| R51 | 2.06 x 1.14 | 0 | 1:VTACH@(-0.5,+0.0); 2:/SCH-06 Hall Tach/TLV_INN@(+0.5,+0.0) |
| R52 | 2.06 x 1.14 | 0 | 1:3V3@(-0.5,+0.0); 2:VREF@(+0.5,+0.0) |
| R53 | 2.06 x 1.14 | 0 | 1:VREF@(-0.5,+0.0); 2:AGND@(+0.5,+0.0) |
| R54 | 2.06 x 1.14 | 0 | 1:OVERSPEED_N@(-0.5,+0.0); 2:VREF@(+0.5,+0.0) |
| TP21 | 2.00 x 2.00 | 0 | 1:HALL_TACH@(+0.0,+0.0) |
| TP22 | 2.00 x 2.00 | 0 | 1:VTACH@(+0.0,+0.0) |
| TP23 | 2.00 x 2.00 | 0 | 1:VREF@(+0.0,+0.0) |

## Pinned obstacles in/near the region (absolute boxes - do not overlap)

| ref | box |
|---|---|
| J7 | (104.5,76.5)-(111.5,80.5) |
| J8 | (124.5,92.0)-(127.3,98.6) |

## Output contract

Return ONLY a JSON object: {"REF": [x, y, rot], ...} for every member.
x,y are the footprint ANCHOR position in absolute board mm. The courtyard
box is centred on the anchor only approximately; assume anchor = courtyard
centre and keep 0.15 mm slack between neighbouring courtyards. rot must be
0, 90, 180, or 270 (90/270 swaps the courtyard w/h). Every courtyard fully
inside the region; no overlaps among members or with the obstacle boxes.
