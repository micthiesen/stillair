# SMD soldering video references

These videos support the hand-population maps on sheets 1A and 1B of the printable field
guide. The board maps remain authoritative for component identity, orientation, and order.
The videos are for learning the hand technique.

## Short watch list

1. [EEVblog #997: How To Solder Surface Mount Components, 17:37](https://www.youtube.com/watch?v=hoLf8gvvXXU)
   is the main overview. The practical drag/dab demonstration starts around 3:36 and covers
   the basic iron-and-wire approach used throughout this build.
2. [PACE: Fine Pitch QFP Install with MiniWave Tip, 2:30](https://www.youtube.com/watch?v=jJescBRDyMQ)
   is a close-up of the tack-and-drag motion. Focus on aligning the package, tacking
   opposite corners, adding flux, keeping pressure off the leads, and drawing the solder
   bead along a row. The package shown has four rows; U8 is easier because it has only two.
3. [Hand soldering 0603 components, 4:00](https://www.youtube.com/watch?v=fqHleZjTaH8)
   is the relevant one-pad-tack demonstration for PCB-02 C1. The same method applies to
   PCB-01 C34, even though C34 is physically larger and bridges an undersized footprint.

## Map the techniques to these boards

- **PCB-01 U8 (SOIC-14):** use an iron, flux, and thin solder wire. Align pin 1, tack one
  corner, recheck every lead over its pad, then tack the diagonally opposite corner. Flux
  both rows and drag-solder them. Remove bridges with fresh flux and solder wick.
- **PCB-01 C34 (1206 over a 0603 site):** tin one pad lightly, hold the part in position,
  reheat that pad to tack it, then solder the other end. Return to the first end only if its
  joint needs refreshing.
- **PCB-02 C1 and U1 (0603 and SOT-23):** use a fine iron tip, thin solder wire, and flux.
  Tack one pad or lead, align the part, then solder the remaining pads. Reflow the tack last
  if it needs more solder or a cleaner fillet.
- **Bridge cleanup:** add flux, lay clean wick over the bridge, touch the iron to the wick,
  and lift iron and wick together as soon as solder flows. Do not scrub or pull on a cold
  joint.

The right-angle through-hole connectors and radial capacitors use ordinary through-hole
soldering, so they are intentionally not covered here. Paste, a stencil, and hot air are
also unnecessary for this build plan.
