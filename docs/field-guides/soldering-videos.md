# SMD soldering video references

These videos support the hand-population maps on sheets 1A and 1B of the printable field
guide. The board maps remain authoritative for component identity, orientation, and order.
The videos are for learning the hand technique.

## Watch in this order

1. [EEVblog #186: Soldering Tutorial Part 3, Surface Mount](https://www.youtube.com/watch?v=b9FC9fAlfQE)
   is the best complete introduction. Watch for one-pad tacking, IC alignment, drag
   soldering, solder-wick cleanup, paste, and hot-air reflow. This covers nearly every new
   technique needed for PCB-01 U8/C34 and PCB-02 U1/C1.
2. [PACE: Fine Pitch QFP Install with MiniWave Tip](https://www.youtube.com/watch?v=jJescBRDyMQ)
   is the clearest close-up of the tack-and-drag motion. Focus on aligning the package,
   tacking opposite corners, adding flux, keeping pressure off the leads, and drawing the
   solder bead along a row. The package shown has four rows; U8 is easier because it has
   only two. PACE also provides the [matching written procedure](https://paceworldwide.com/node/442).
3. [EEVblog #997: How To Solder Surface Mount Components](https://www.youtube.com/watch?v=hoLf8gvvXXU)
   is a shorter refresher. The practical drag/dab demonstration starts around 3:36.
4. [EEVblog #415: SMD Stencil Reflow Soldering Tutorial](https://www.youtube.com/watch?v=qyDRHI4YeMI)
   shows paste quantity, placement, heating, and how joints change when reflow completes.
   It uses a stencil, but for the tiny bare PCB-02 population the useful lessons are paste
   volume and reflow behavior. Apply tiny syringe deposits rather than copying the stencil
   workflow.

## Map the techniques to these boards

- **PCB-01 U8 (SOIC-14):** use an iron, flux, and thin solder wire. Align pin 1, tack one
  corner, recheck every lead over its pad, then tack the diagonally opposite corner. Flux
  both rows and drag-solder them. Remove bridges with fresh flux and solder wick.
- **PCB-01 C34 (1206 over a 0603 site):** tin one pad lightly, hold the part in position,
  reheat that pad to tack it, then solder the other end. Return to the first end only if its
  joint needs refreshing.
- **PCB-02 C1 and U1 (0603 and SOT-23):** use tiny paste deposits and controlled electronics
  hot air, or use the same one-pad tack method with a fine iron tip. Paste should cover the
  pads without forming tall blobs.
- **Bridge cleanup:** add flux, lay clean wick over the bridge, touch the iron to the wick,
  and lift iron and wick together as soon as solder flows. Do not scrub or pull on a cold
  joint.

The right-angle through-hole connectors and radial capacitors use ordinary through-hole
soldering, so they are intentionally not covered here.
