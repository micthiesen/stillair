# Group: mcf_west

Region (absolute board mm, Y down): x 74..82, y 80..101

## Intent

West flank of U1 (MCF8316D, pinned at (85,88), pins 1-12 on its west edge x=82.9, pin1=DVDD at north end going south: DVDD,FB_BK,GND_BK,SW_BK,CPL,CPH,CP,VM,VM,VM,PGND at y84.9..90.4). L1 (buck inductor, pinned at (76,93)) and C16 (buck out 22uF) form the buck loop with SW_BK/FB_BK/GND_BK pins: C16 directly south of or beside L1, loop tight. C12 (1uF CP-to-VM) and C13 (47nF CPH-CPL) are charge-pump caps: as close to pins 6/7/8 as possible. C15 (1uF DVDD) tight to pin 1. R8/R9/R10 (BRAKE/DIR/SPEED pulldowns to AGND, pins 35/34/28 on... those pins are actually on the symbol west but on the FOOTPRINT they are south-west corner pins 21,28,30-35 region) - place along the south of the region. TP8=MCF_DVDD near C15, TP16=MCF_EXT_WD.

## Members (courtyard size at CURRENT rotation; rotating 90/270 swaps w/h)

| ref | w x h | rot | pads (num:net at local offset) |
|---|---|---|---|
| C12 | 2.95 x 1.45 | 0 | 1:/SCH-03 MCF Power Stage/MCF_CP@(-0.8,+0.0); 2:VM24@(+0.8,+0.0) |
| C13 | 3.40 x 1.95 | 0 | 1:/SCH-03 MCF Power Stage/MCF_CPH@(-0.9,+0.0); 2:/SCH-03 MCF Power Stage/MCF_CPL@(+0.9,+0.0) |
| C15 | 2.95 x 1.45 | 0 | 1:MCF_DVDD@(-0.8,+0.0); 2:AGND@(+0.8,+0.0) |
| C16 | 4.60 x 3.20 | 0 | 1:/SCH-03 MCF Power Stage/MCF_BUCK@(-1.5,+0.0); 2:AGND@(+1.5,+0.0) |
| R8 | 2.06 x 1.14 | 0 | 1:/SCH-03 MCF Power Stage/MCF_BRAKE@(-0.5,+0.0); 2:AGND@(+0.5,+0.0) |
| R9 | 2.06 x 1.14 | 0 | 1:DIR@(-0.5,+0.0); 2:AGND@(+0.5,+0.0) |
| R10 | 2.06 x 1.14 | 0 | 1:SPEED@(-0.5,+0.0); 2:AGND@(+0.5,+0.0) |
| TP8 | 2.00 x 2.00 | 0 | 1:MCF_DVDD@(+0.0,+0.0) |
| TP16 | 2.00 x 2.00 | 0 | 1:MCF_EXT_WD@(+0.0,+0.0) |

## Pinned obstacles in/near the region (absolute boxes - do not overlap)

| ref | box |
|---|---|
| J2 | (83.5,100.1)-(94.5,113.9) |
| U1 | (82.3,83.8)-(87.7,91.7) |
| L1 | (72.6,89.7)-(79.4,96.3) |
| C6 | (62.3,82.8)-(72.7,93.2) |

## Output contract

Return ONLY a JSON object: {"REF": [x, y, rot], ...} for every member.
x,y are the footprint ANCHOR position in absolute board mm. The courtyard
box is centred on the anchor only approximately; assume anchor = courtyard
centre and keep 0.15 mm slack between neighbouring courtyards. rot must be
0, 90, 180, or 270 (90/270 swaps the courtyard w/h). Every courtyard fully
inside the region; no overlaps among members or with the obstacle boxes.
