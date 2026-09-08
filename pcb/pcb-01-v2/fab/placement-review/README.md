# PCBA placement and polarity review, 2026-09-07

## Verdict

The shown DFM for `SMT026083161536_Y8` passes the placement/polarity review. No correction is
required. Michael may confirm it to JLCPCB. No assembly approval or reply was submitted by the
agent. The authenticated order page now shows the PCB production file as **Confirmed**, while
assembly is Pending and awaiting the email response.

Review combined native KiCad pad extraction, the released orientation drawings, independent IC
and discrete-device checks, the emailed image, and the live DFM's component and package data.

## Retained evidence

- `jlc-dfm.png`: supplied 1778 x 1474 image; SHA-256
  `4e52a0c6db225b7a15c2d5958db3682f9cdc68ff9ffdd2808f33bb6ce737dfa1`.
- `factory-bom.zip`: live `Smt_Hw_Bom_Merge` download, containing the factory reference list,
  original coordinates, adjusted coordinates, rotation conventions, package UUIDs, and mount flags.
- `factory-preview.zip`: live `Smt_Hw_Web_File` download, containing the CAM preview geometry.
- `factory-packages.json`: the public package geometries requested by the live DFM viewer.
- `cpl-comparison.json`: full 119-reference comparison, including raw origin/rotation differences
  resolved below. Raw differences in this file are not unresolved placement failures.

Live DFM was opened from the order's **DFM Analysis** link. All 119 unique assembled designators
match `cpl-jlcpcb.csv` and the exact LCSC codes in `assembly-manifest.csv`. All are enabled on top;
there are zero bottom-side parts, missing references, or extra references. The original coordinates
and rotations retained by the factory match the submitted CPL exactly.

## Polarity and direction

Directions refer to the component-side image with J4 at the top.

| References | Required and shown orientation | Result |
| --- | --- | --- |
| U1 | Pin 1 northwest; white package dot northwest | Pass |
| U2 | Pin 1 northeast; antenna east toward board edge | Pass |
| U3, U4, U5, U6, U7, U9, U10, U11, U12 | Pin 1 northwest | Pass |
| U13 | Pin 1 southwest, USB_DP | Pass |
| U14 | Pin 1 northeast, USB_CC1 | Pass |
| D1, D3, D4, D5, D6, D7, D8 | Cathode band west | Pass |
| D2 | Cathode band south; anode north | Pass |
| D9 | Pin 1 northwest; lone lead east | Pass |
| Q1 | Gate/pin 1 southwest; drain tab north | Pass |
| Q2 | Gate/pin 1 northwest; lone drain lead east | Pass |
| Q3 | Gate/pin 1 southwest; lone drain lead north | Pass |
| J4 | Opening north toward board edge | Pass |
| RV1 | Pin 1 northeast; wiper south; screw southwest | Pass |
| SW1, SW2, SW3 | Contact rows and body align with horizontal pad pairs | Pass |

U13 and U14 intentionally face opposite directions, matching the dedicated released callout.
All factory-installed capacitors are nonpolar ceramic MLCCs; their pink dots are library pin
markers, not electrical polarity requirements. Resistors and L1 are nonpolar. The six hand-installed
references C1, C2, J1, J2, J3, U8 are correctly absent, as are DNP C44/C45.

## Coordinate differences resolved

Factory CAM coordinates use `x=x_CPL-50`, `y=y_CPL+119` in mm (CPL Y is negative). For 116 of 119
parts the adjusted placement reference lies within 0.01 mm of this transform. Three packages use
different reference origins; raw rotations also differ by library convention. Their geometry,
not matching raw angle numbers, determines correct placement:

- **U2:** raw adjusted X differs by -2.98465 mm. Transforming the actual factory package places
  all 28 perimeter pins within 0.01036 mm of their native pad centers, with antenna east. The
  package reference is near the electrical-pin/non-antenna center, rather than the entire module
  centroid. The factory model's nine inner ground squares differ from native lands by about
  0.2495 mm in Y; both are 0.8 mm squares with ground-contact overlap. This is a library-land
  difference, not evidence to shift the component away from its aligned perimeter pins.
- **U3:** raw adjusted Y differs by +0.57101 mm. All eleven transformed library pads map to
  their corresponding native lands. Land dimensions/centers differ by up to about 0.1002 mm;
  terminal-facing edges align (pad 2 inner X edge 84.649848 versus native 84.650 mm; pad 9 south
  Y edge 60.341516 versus native 60.350 mm). The factory body drawing also differs by about
  0.204 mm from native F.Fab artwork. These are drawing/reference differences, not the apparent
  0.571 mm whole-component shift.
- **J4:** raw adjusted Y differs by -1.20699 mm. Using the actual contact-metal polygons in
  `customData.pinsInfo[].weldingID`, all sixteen contacts fall inside their intended copper pads.
  Individual signal lead centers differ by at most 0.00022 mm in X and 0.00516 mm in Y. Shell
  stakes fit their slots and the model pegs fit nominal hole clearance. Mouth faces north. The
  library's recommended PAD centers are not identical to physical contact centers.

## Interpretation and sources

This confirms the intended assembly placement represented by this DFM and its part list. It does
not certify the eventual solder joints or actual reel markings. Some tiny model surfaces, notably
U3/U12, do not show a separately legible physical pin-1 mark; their DFM pin-1 markers and mapped
package geometry agree with the released design.

The discrete reviewer checked primary polarity/package drawings:
[MMSZ5242B](https://www.diodes.com/datasheet/download/MMSZ5242B.pdf),
[SMCJ24A](https://www.diodes.com/datasheet/download/SMCJ24A.pdf),
[Vishay BAT54W](https://www.vishay.com/docs/86409/bat54w-g.pdf),
[BAT54SLT1G](https://www.onsemi.com/pdf/datasheet/bat54slt1-d.pdf),
[DMP6023LE](https://www.diodes.com/datasheet/download/DMP6023LE.pdf),
[2N7002K](https://www.diodes.com/datasheet/download/2N7002K.pdf), and
[Bourns 3224](https://www.bourns.com/pdfs/3224.pdf).
Vishay BAT54W datasheet terminal numbering differs from KiCad's generic diode numbering; compare
the cathode band and electrical polarity, not those numbers directly.
