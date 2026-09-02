# PCB-03 JLCPCB bare-board ordering

Regenerate immediately before upload:

```bash
python3 pcb/tools/jlc_fab.py pcb-03
```

Upload only `pcb-03-gerbers.zip` on JLCPCB's PCB quote page. Do not select PCB assembly, do not
upload a BOM or placement file, and do not order a stencil.

Verify that the generated package still matches the checked source:

```bash
cd pcb/pcb-03
shasum -a 256 -c fab/release-manifest.sha256
```

## Order gate

Do not submit the order until all three bench gates in `docs/pcb-03.md` pass:

1. Freeze and verify the exact monochrome Waveshare 1.54-inch V2 display revision at 3.3 V.
2. Prove the SC18IS606 can update it using four 1024-byte chunks and one 904-byte chunk despite
   chip select toggling between chunks.
3. Prove PCA9536 slow-ramp and brownout recovery always regains control of both reset lines.

## PCB settings

- Base material: FR-4
- Layers: 2
- Dimensions: nominal 39.75 x 21.00 mm. KiCad's job file reports 39.80 x 21.05 mm because it
  includes the 0.05 mm Edge.Cuts stroke; accept JLCPCB's automatic Gerber detection.
- Different designs: 1
- Delivery format: Single PCB
- Quantity: 5
- Thickness: 1.6 mm
- Copper weight: 1 oz
- Solder mask: Green
- Silkscreen: White
- Surface finish: Lead-free HASL
- Via covering: Tented
- Minimum via hole: 0.30 mm
- Gold fingers: No
- Castellated holes: No
- Edge plating: No
- Impedance control: No
- Remove order number: Yes, if offered
- Electrical test: Fully tested / flying probe

The board has ordinary through vias, through-hole JST headers, and two 2.2 mm non-plated M2 holes.
It requires no controlled impedance, blind or buried vias, via filling, special stackup, or other
fabrication notes.

## Quote-page checks

- Confirm the preview shows one closed rectangular outline, nominally 39.75 x 21.00 mm. A detected
  39.80 x 21.05 mm extent is the expected Edge.Cuts-stroke result.
- Confirm two copper layers and two 2.2 mm non-plated mounting holes.
- Confirm both side-entry connector openings face outward.
- Confirm the back pinout legends are readable from the back and do not overlap holes or pads.
- Stop after adding the bare PCB to the cart. Decline PCB assembly and stencil prompts.
