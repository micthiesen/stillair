# Group: ldo

Region (absolute board mm, Y down): x 105..121.5, y 94..102.5

## Intent

Protected 12V tach rail. Power flows: VM24 -> R39 (47R 1W 2512, give it a little breathing room for heat) -> U4 TPS7A1601 MSOP-8 (pin8=IN west-ish, pin1=OUT, pin3=PG, pin7=DELAY, pin4+EP=GND) -> +12V_TACH north to the tach group. C26 (10uF 63V) + C27 (100nF) input caps tight to IN; C28 (10uF 25V) + C29 (100nF) output caps tight to OUT. R40/R41 (910k/100k 0.1% FB divider) + C30 (10nF feed-forward) compact at FB. C31 (10nF DELAY) at pin 7. TP6=+12V_TACH. Obstacles: J8 scope header (pinned, box (115,99.6)-(119,102.5) intrudes at your south edge), H2 hole keepout circle r4 at (122,102) clips your SE corner.

## Members (courtyard size at CURRENT rotation; rotating 90/270 swaps w/h)

| ref | w x h | rot | pads (num:net at local offset) |
|---|---|---|---|
| U4 | 6.36 x 3.60 | 0 | :-@(-0.4,-0.5); :-@(-0.4,+0.5); :-@(+0.4,-0.5); :-@(+0.4,+0.5); 1:+12V_TACH@(-2.1,-1.0); 2:/SCH-06 Hall Tach/TACH_FB@(-2.1,-0.3); 3:OVERSPEED_N@(-2.1,+0.3); 4:AGND@(-2.1,+1.0); 5:/SCH-06 Hall Tach/TACH_LDO_IN@(+2.1,+1.0); 6:unconnected-(U4-NC-Pad6)@(+2.1,+0.3); 7:/SCH-06 Hall Tach/TACH_DELAY@(+2.1,-0.3); 8:/SCH-06 Hall Tach/TACH_LDO_IN@(+2.1,-1.0); 9:AGND@(-0.6,-0.7); 9:AGND@(-0.6,+0.7) |
| R39 | 7.65 x 3.85 | 0 | 1:VM24@(-3.0,+0.0); 2:/SCH-06 Hall Tach/TACH_LDO_IN@(+3.0,+0.0) |
| C26 | 4.60 x 3.20 | 0 | 1:/SCH-06 Hall Tach/TACH_LDO_IN@(-1.5,+0.0); 2:AGND@(+1.5,+0.0) |
| C27 | 3.40 x 1.95 | 0 | 1:/SCH-06 Hall Tach/TACH_LDO_IN@(-0.9,+0.0); 2:AGND@(+0.9,+0.0) |
| C28 | 4.60 x 3.20 | 0 | 1:+12V_TACH@(-1.5,+0.0); 2:AGND@(+1.5,+0.0) |
| C29 | 2.95 x 1.45 | 0 | 1:+12V_TACH@(-0.8,+0.0); 2:AGND@(+0.8,+0.0) |
| C30 | 2.95 x 1.45 | 0 | 1:+12V_TACH@(-0.8,+0.0); 2:/SCH-06 Hall Tach/TACH_FB@(+0.8,+0.0) |
| C31 | 2.02 x 1.12 | 0 | 1:/SCH-06 Hall Tach/TACH_DELAY@(-0.5,+0.0); 2:AGND@(+0.5,+0.0) |
| R40 | 2.06 x 1.14 | 0 | 1:+12V_TACH@(-0.5,+0.0); 2:/SCH-06 Hall Tach/TACH_FB@(+0.5,+0.0) |
| R41 | 2.06 x 1.14 | 0 | 1:/SCH-06 Hall Tach/TACH_FB@(-0.5,+0.0); 2:AGND@(+0.5,+0.0) |
| TP6 | 2.00 x 2.00 | 0 | 1:+12V_TACH@(+0.0,+0.0) |

## Pinned obstacles in/near the region (absolute boxes - do not overlap)

| ref | box |
|---|---|
| J3 | (99.9,102.6)-(108.1,107.5) |
| J4 | (108.9,102.6)-(115.1,107.5) |
| SW3 | (91.9,98.0)-(102.1,105.0) |
| H2 | (119.9,99.9)-(124.1,104.1) |

Mounting-hole keepout: circle r=4.0 at (122.0,102.0) - keep courtyards outside it.

## Output contract

Return ONLY a JSON object: {"REF": [x, y, rot], ...} for every member.
x,y are the footprint ANCHOR position in absolute board mm. The courtyard
box is centred on the anchor only approximately; assume anchor = courtyard
centre and keep 0.15 mm slack between neighbouring courtyards. rot must be
0, 90, 180, or 270 (90/270 swaps the courtyard w/h). Every courtyard fully
inside the region; no overlaps among members or with the obstacle boxes.
