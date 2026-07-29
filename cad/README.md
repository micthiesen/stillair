# CAD

Fabrication outputs for the custom mechanical parts: 2D profiles for laser/waterjet (MP-100,
KD-100, MR-100, LS-100, BR-100 flat pattern), CNC files (MC-100, RH-100, SP-100, BL-100
router files), and print files (BA-10/12/14, ENC-100, optionally EB-100).

The full 3D assembly is modeled in **OnShape** and does not live in this repo; export STEP/PDF
here when parts approach fabrication release. Dimensioned specs for every part:
[../docs/parts.md](../docs/parts.md). Do not release motor-dependent metal before the
fabrication gates at the bottom of that doc clear.

## Released files

| Part | Files | Status |
|---|---|---|
| MP-100 | `MP-100_revA.step`, `MP-100_revA.pdf` | Ordered 2026-07-27, JLCCNC |
| ST-100 | `ST-100_revA.step`, `ST-100_revA.pdf` | Ordered 2026-07-28, JLCCNC |

Name every export `<PART>_rev<X>.<ext>` and commit it **as sent**. The point is that a later
revision diffs against the geometry that was actually quoted, not against the live OnShape
model, which keeps moving.

## Ordering at JLCCNC

Learned ordering MP-100 (2026-07-27). The CNC service is **jlccnc.com**, separate from the
PCB side.

**Send two files.** A STEP (AP214) drives the instant quote and the geometry; a **PDF drawing**
carries everything a STEP cannot hold — threads, tolerances, finish, and face assignment.
JLC's review engineers cross-check the two by hand and will query any disagreement.

**Attach the PDF twice.** Once as the general 2D drawing, and again to the `+ Add file` slot
that appears under **Threads → Yes**. That slot is the "tapping document" and it is easy to
miss; with Threads set to Yes and no file, tapped holes get quoted as plain drills.

**Dialog settings that worked** (adapt material/finish per part):

| Field | MP-100 value | Note |
|---|---|---|
| Material | Stainless Steel → SUS304 | Aluminum 6061 is the sticky default — verify on the quote line, stainless runs 2–3× the price |
| Surface Finish | Brushing | Anodizing is aluminium-only; passivation is not offered for 304 |
| Tightest Tolerance | ±0.10 mm | Only buy ±0.05 if a callout truly needs it |
| Appearance | Standard | Ra 1.6 is not worth paying for on a hidden part |
| Threads | Yes + PDF attached | See above |
| Sub-assembly | No | |

**Their DFM rules that shaped the design** (worth designing to up front rather than
answering a query about later):

- Blind tapped holes want **≥ half the nominal diameter left unthreaded** at the bottom.
  This is what drove MP-100's ten taps to M3 × 0.5 at 3.5 mm thread in a 5.0 mm drill; M4
  needs 2.0 mm of run-out and could not get it inside a 6 mm plate.
- Effective thread length **≤ 3 × hole diameter**.
- Tapped holes must sit in the interior of the part, clear of edges.
- Default tolerance is **±0.1 mm** if the drawing states none — tighter than ISO 2768-m, so
  a 2768 block is a ceiling, not a floor.

**What JLC does not hold: form tolerances.** Flatness, runout, concentricity and true
position are quoted to nothing. They live in the PDF as intent and must be inspected on
arrival. This is the reason SP-100 (0.05 mm concentricity TIR) and MC-100/RH-100 (0.08 mm
flatness and TIR) are poor fits for JLC even though MP-100 was a good one.

**Drawing checklist** (what MP-100's PDF carries):

1. Views labelled `CEILING FACE` and `UNDERSIDE` in words, plus a note assigning every
   one-sided feature to a face. A flat disc looks identical from both sides.
2. A hole table with signed X/Y per hole. Coordinates cannot be mirrored the way
   "6× at 45°, 60° spacing" can.
3. A note fixing the angular datum and direction in prose, as mirror insurance.
4. A note that the hole table covers tapped holes only, if through-holes are dimensioned
   on the views instead.
5. ISO 2768-mK block, form tolerances, minimum internal corner radii, material and finish.

**Turned-part modeling + drawing notes** (learned on ST-100 rev A, 2026-07-28):

- Model the thread-entry chamfer as the Hole feature's **countersink** (Ø7 × 90° for M6):
  it exports in the STEP and lands in the drawing's hole callout automatically.
- Second-end tap on a turned part: **Mid plane** between the end faces + **Feature mirror**
  of the Hole feature — one edit drives both ends.
- In OnShape's tapped-Hole dialog the tap fields (Tapped depth, Tap clearance) are below
  the fold — scroll; the visible 13.44/90° pair is the countersink, not the thread.
- Drawings: the **Datum** tool attaches to the OD silhouette edge or the Ø dimension; the
  **Geometric tolerance** tool only attaches its leader *during placement* (hover-click the
  edge while the dialog is open) — a frame placed floating cannot be attached afterwards.
- Fill the title block TITLE/DWG NO fields before export (left empty on ST-100 rev A;
  harmless, but the shop sees it).

**Gotcha that cost a rebuild:** OnShape hole tables snap their origin to real geometry, so
an under-constrained centre bore silently offsets every coordinate in the table. MP-100's
bore sat 0.64 mm low in Y and the table inherited it. If the table's origin will not snap
where it should, suspect the model, not the drawing — and check that the base sketch is
fully defined before trusting any exported coordinate.
