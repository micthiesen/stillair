# Production-file review, 2026-09-07

Order `W2026083117295494`, PCB job `Y8-12177845A`, assembly `SMT026083161536-12177845A`.

## Evidence and findings

`2026-09-07-jlcpcb-production.zip` is the unmodified 4,462,522-byte authenticated download.
SHA-256: `8312b1b6e856da0d860cf55d4d4389c77a769aa38c311ff671a09dd33e2066e9`.
ZIP integrity passed. CAM Gerbers are in `ok/`; the ODB++ archive is `ok/12177845a_y8.tgz`.
These are returned factory evidence, not replacements for the released KiCad files or Gerbers.

- ODB++ `steps/edit/profile` is 88 x 64 mm. The `set` panel is 88 x 74 mm with 5 mm top/bottom
  process rails. Comparing submitted Gerbers with set CAM in mm requires
  `x_cam=x_submitted-50`, `y_cam=y_submitted+119` (submitted Gerber Y is negative).
- `misc/ImpedanceInfo` records all three approved width/edge-gap settings: `10.77/14.82 mil`,
  `12.87/38.30 mil`, and `12.87/46.18 mil`, each targeting 97 ohm on `tl/l2`.
- Parsed CAM `ts` and submitted `F_Mask.gts` confirm U3 pads 4/5 retain the 1.34 x 1.84 mm openings
  to Gerber rounding precision. Their board-local lower-left positions are `(33.630,50.055)` and
  `(36.030,50.055)` mm after removing the rail offset. Other nearby openings were enlarged by CAM;
  these protected apertures were preserved.
- Parsed CAM `drl` confirms all twelve 0.30 mm U1 pad 41 holes at the submitted CSV coordinates.
  Hole presence does not prove epoxy filling and copper capping. Inspected tools/metadata did not
  explicitly establish that treatment.

This was a targeted geometry/metadata check, not exhaustive copper/netlist equivalence, verification
of every compensated CAM trace width, or final assembly orientation review. The customer-facing
phrase "everything else looks good" must not be interpreted as proof those additional checks ran.
The separate Confirm Parts Placement gate remains outstanding.

## Submitted request

Michael reported submitting the confirmation/modification request on 2026-09-07. Prepared text:

> I have reviewed the production files and they look good. Before approving, I need confirmation
> that all twelve 0.30 mm holes inside U1 exposed pad 41 will be epoxy-filled and copper-capped
> (POFV), as specified in the previously submitted pofv-locations.csv and pofv-location-map.pdf.
>
> Please keep U1 pad 41's top solder-mask aperture open and add no bottom mask openings for these holes.
>
> This is the only outstanding item. If this treatment is already included, no modification is
> needed; please confirm it in writing.

`PCB-01-V2-POFV-support.zip` contains the existing PDF map and coordinate CSV from `fab/`.
A verified copy was supplied on Synology's `overflow` share for phone access. Actual attachment
upload was not independently verified. Michael mentioned a $2 cutting/remarks fee but asked to
disregard speculation about its purpose; the fee is not evidence of POFV treatment.

Await written confirmation, then compare any revised files with this archive and the release.
Do not repeat answered impedance questions unless the relevant geometry, stack, or copper changes.
No production approval was submitted by the agent.

## Download recovery

The first phone download was a 110-byte JSON error (`code:500`, `data:null`). The logged-in browser
download succeeded. **Confirm Production file** opens the review form; approval requires a separate
choice and Submit. Read the Download Production file anchor's actual href and fetch its bytes in
the authenticated page. Browser-control exposes `fs` and `Buffer` directly; `require` is unavailable.
Verify ZIP integrity before treating a download as production evidence.

## Factory confirmation received

Chian subsequently confirmed in writing that all twelve 0.30 mm via-in-pad holes inside U1
exposed pad 41 are filled with non-conductive epoxy and copper-capped; the top pad aperture remains
open and no bottom mask openings were added. Chian explicitly states that the treatment was
already included in the current production file. This clears the POFV process question; the
earlier review had not established the treatment, rather than proving it absent.

The accompanying [image](pofv-confirmation.png) identifies U1 and the correct 3 x 4 hole array,
with an arrow to the CAM `sk` layer. The written statement, not the screenshot alone, confirms
the fill/cap process. Michael may approve the reviewed PCB production file on this basis.
Actual approval has not yet been reported; assembly placement remains a separate later check.
