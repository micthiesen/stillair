# Group: mcf_east

Region (absolute board mm, Y down): x 88.5..94, y 72..84

## Intent

East/north flank of U1 (pinned at (85,88); its footprint east edge x=87.1 carries pins 21-32 south-to-north: DRVOFF,NC*4,AGND,AVDD,SPEED,FG,SDA,SCL,EXT_WD at y85..91; north edge carries pins 33-40). C14 (1uF AVDD bypass) as close to the region's west edge / U1 pin 27 as possible. R4/R5 (FG/nFAULT 4.7k pullups to 3V3), R6/R7 (SDA/SCL 4.7k pullups): tidy pairs. TP12=DRVOFF, TP7=MCF_AVDD, TP17=NFAULT, TP18=SDA, TP19=SCL, TP20=FG in an accessible probe row.

## Members (courtyard size at CURRENT rotation; rotating 90/270 swaps w/h)

| ref | w x h | rot | pads (num:net at local offset) |
|---|---|---|---|
| C14 | 2.95 x 1.45 | 0 | 1:MCF_AVDD@(-0.8,+0.0); 2:AGND@(+0.8,+0.0) |
| R4 | 2.06 x 1.14 | 0 | 1:3V3@(-0.5,+0.0); 2:FG@(+0.5,+0.0) |
| R5 | 2.06 x 1.14 | 0 | 1:3V3@(-0.5,+0.0); 2:NFAULT@(+0.5,+0.0) |
| R6 | 2.06 x 1.14 | 0 | 1:3V3@(-0.5,+0.0); 2:SDA@(+0.5,+0.0) |
| R7 | 2.06 x 1.14 | 0 | 1:3V3@(-0.5,+0.0); 2:SCL@(+0.5,+0.0) |
| TP7 | 2.00 x 2.00 | 0 | 1:MCF_AVDD@(+0.0,+0.0) |
| TP12 | 2.00 x 2.00 | 0 | 1:DRVOFF@(+0.0,+0.0) |
| TP17 | 2.00 x 2.00 | 0 | 1:NFAULT@(+0.0,+0.0) |
| TP18 | 2.00 x 2.00 | 0 | 1:SDA@(+0.0,+0.0) |
| TP19 | 2.00 x 2.00 | 0 | 1:SCL@(+0.0,+0.0) |
| TP20 | 2.00 x 2.00 | 0 | 1:FG@(+0.0,+0.0) |

## Pinned obstacles in/near the region (absolute boxes - do not overlap)

| ref | box |
|---|---|
| U1 | (82.3,83.8)-(87.7,91.7) |

## Output contract

Return ONLY a JSON object: {"REF": [x, y, rot], ...} for every member.
x,y are the footprint ANCHOR position in absolute board mm. The courtyard
box is centred on the anchor only approximately; assume anchor = courtyard
centre and keep 0.15 mm slack between neighbouring courtyards. rot must be
0, 90, 180, or 270 (90/270 swaps the courtyard w/h). Every courtyard fully
inside the region; no overlaps among members or with the obstacle boxes.
