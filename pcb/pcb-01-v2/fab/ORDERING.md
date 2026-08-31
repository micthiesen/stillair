# PCB-01 V2 JLCPCB ordering and final assembly

This file is the operator checklist for the generated PCB-01 V2 package. Regenerate the package
with `python3 pcb/tools/jlc_fab.py pcb-01-v2` immediately before upload. Do not reuse files from an
earlier board revision.

After the last regeneration, verify that the operator files still match the checked source:

```bash
cd pcb/pcb-01-v2
shasum -a 256 -c fab/release-manifest.sha256
```

## Upload files

- PCB fabrication: `pcb-01-v2-gerbers.zip`
- Assembly BOM: `bom-jlcpcb.csv`
- Component placement: `cpl-jlcpcb.csv`
- Attach `pofv-location-map.pdf`, `pofv-locations.csv`, and `impedance-requirements.csv` to the
  order, or send them to JLCPCB support against the order number before approval if the form has no
  attachment field.
- Keep `fabrication-notes.md`, `assembly-orientation.pdf`,
  `assembly-orientation-u13-u14.pdf`, `assembly-preview-3d.png`, `assembly-locator.pdf`, and this
  checklist open while reviewing the detected board and placement previews.

## Recommended order

- PCB quantity: 5
- PCBA quantity: 2, both top-side Standard assembly
- Purpose: one primary machine-populated board and one spare, while keeping three bare boards.
  The low-stock exact ICs have enough current inventory for two assembled boards plus normal
  attrition. Recheck the live counts at upload.

PCB form settings:

- Single PCB, 88 x 64 mm, 4 layers
- FR-4, Tg at least 150 C
- 1.6 mm finished thickness
- Outer copper 2 oz, inner copper 1 oz
- Green solder mask, white silkscreen
- ENIG surface finish
- Minimum via-hole tier: 0.30 mm. The submitted drill file has no via below 0.30 mm.
- Impedance control on. Select JLC041621-7628 and verify the production stack matches the exact
  build in `fabrication-notes.md`; set 2 oz outer and 1 oz inner copper.
- Specify 97 ohm differential for both via-free 0.20 mm/0.20 mm F.Cu USB sections: `USB_DP` /
  `USB_DN` from J4 through U13 to R58/R59 and `USB_D_MCU_P` / `USB_D_MCU_N` from R58/R59 to U2.
  JLC's live calculator gives 96.85 ohm for this geometry, inside USB 2.0's 90 ohm +/-15% range.
  Attach `impedance-requirements.csv` and require CAM confirmation.
- Select epoxy-filled and copper-capped vias. The twelve U1 holes are component-pad drills, so the
  generic via option is not sufficient by itself. Attach the POFV map and coordinate CSV, paste the
  exact POFV remark, and obtain explicit CAM confirmation for those twelve holes.
- Require production-file confirmation before approval.

PCBA form settings:

- Standard PCBA, top side only
- Upload the exact BOM and CPL above
- Turn automatic part substitution off globally. Approve a proposed substitution only after an
  exact schematic, footprint, package, rating, and datasheet review and update the source map first.
- Select JLCPCB's `Confirm Parts Placement` service. Do not release assembly until the confirmed
  production placement matches the submitted CPL, silkscreen, and orientation artifacts.
- Accept JLCPCB's required 5 mm process rails on two sides because one board dimension is below
  70 mm. Select factory rail removal/depanel service if offered. In the production preview, confirm
  the finished PCB remains 88 x 64 mm and the rails, tooling holes, and V-cuts remain outside the
  submitted outline and copper.

Paste all three quoted requirements from `fabrication-notes.md` into the order remarks. Confirm all
twelve U1 POFV coordinates, both U3 solder-mask-defined pads, and the 97 ohm USB requirement in the
production files before approval.

## Placement-preview checks

The visual JLCPCB placement preview is authoritative. Raw CPL rotation numbers are not. Check every
polarized or pin-1-sensitive part against `assembly-orientation.pdf`, which contains F.Fab package
outlines and numbered pads. Its pages are the whole-board overview followed by NW, NE, SW, and SE
quadrants. Use `assembly-preview-3d.png` for body and connector direction and
`assembly-locator.pdf` only to find dense references. Pay particular attention to:

- U1 pin 1 and exposed-pad alignment
- U2 antenna end toward the `ANTENNA KEEP CLEAR` board edge
- U3 pin 1 and the asymmetric module pad field
- U4 through U7 and U9 through U14 pin 1
- U13 and U14 against `assembly-orientation-u13-u14.pdf`; its red pads and channel-net table remove
  the ambiguity caused by their overlapping package outlines in the whole-board plot
- D1 through D9 cathode orientation
- Q1 through Q3 package orientation
- J4 USB-C opening toward the board edge

Reject unexplained body shifts, mirrored parts, connector openings facing inward, or polarity marks
that disagree with `assembly-orientation.pdf`. Review any JLCPCB DFM email and the final production render before
approving manufacture.

## Live machine-part audit

The generated 55-line BOM contains 52 unique JLCPCB part numbers. On 2026-08-31, every number had a
live detail page, nonzero stock, SMT Assembly support, and Standard PCBA support. R39 was changed from
out-of-stock `C723713` to `C3000771` (`FRC2512F47R0TS`), an equal 47 ohm, 1%, 1 W, 200 V, 2512 part.

Recheck these constrained lines immediately before upload:

| Ref | JLCPCB part | Exact part | Stock on 2026-08-31 |
| --- | --- | --- | ---: |
| U3 | C18208843 | TPSM365R6V3RDNR | 10 |
| U4 | C6886485 | TPS7A1601ADGNR | 14, 12 available to order |
| U7 | C6339182 | TPS3435CAKAGDDFR | 14 |
| R54 | C2079068 | CPF0402B90K9E1 | 17, 16 available to order |
| U1 | C47122159 | MCF8316DVRGFR | 48, 39 available to order |

D2's BOM value is the generic `SMCJ24A`; JLCPCB part `C135154` is the valid tape-and-reel ordering
part `SMCJ24A-13-F` with the required SMC, 24 V unidirectional, 1.5 kW specification.

## Parts installed by hand

JLCPCB must leave only these six references unpopulated:

| Ref | Part | Needed per completed board |
| --- | --- | ---: |
| C1, C2 | Panasonic EEU-FR1H471, 470 uF 50 V | 2 |
| J1 | Molex 43045-0200 power header | 1 |
| J2 | Molex 43650-0300 motor header | 1 |
| J3 | JST B3B-PH-K-S(LF)(SN) Hall header | 1 |
| U8 | TI LM2907M/NOPB, SOIC-14 | 1 |

The repository records the original V1 purchases, not the current loose-bin count. Both V1 PCBAs
could have consumed all four capacitors, both J1 headers, both J2 headers, two J3 headers supplied
through assembly, and two of the three LM2907 devices. Before submitting two V2 PCBAs, physically
confirm this complete board-only stock set:

- 4 x Panasonic `EEU-FR1H471`
- 2 x Molex `43045-0200`
- 2 x Molex `43650-0300`
- 2 x JST `B3B-PH-K-S(LF)(SN)`
- 2 x TI `LM2907M/NOPB`

If the V1 builds consumed their planned parts, expect to buy all four capacitors and all six
connectors, plus one LM2907 if the recorded single loose spare is still present. Physical count is
the authority.

The complete no-stock-assumption set was ordered from DigiKey on 2026-08-31 as **101316601**:
4 x `EEU-FR1H471`, and 2 x each `43045-0200`, `43650-0300`, `B3B-PH-K-S(LF)(SN)`, and
`LM2907M/NOPB`. Receipt of that order supersedes the loose-bin count as the board-completion gate.

Install U8 before the tall through-hole parts. Align its pin 1 with the front silkscreen dot and the
back `U8 PIN 1` cue. Install C1/C2 with their positive leads at the front `+` marks. Confirm J1, J2,
and J3 pin numbering against the printed pinouts before soldering.
