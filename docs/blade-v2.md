# BP-100 printed blade (V2 blade redesign)

> **Status: proposed 2026-07-27, not yet accepted.** When accepted this supersedes the BL-100
> birch flat-plate blade and collapses the BA-10/12/14 pitch-adapter family to a single flat
> adapter (BA-00, undesigned). BL-100/LS-100 stay in [parts.md](parts.md) until then.

A two-segment 3D-printed blade (aero/LW-PLA class filament) with a Ø3 mm carbon-fiber rod
spar, cambered low-Reynolds airfoil sections, spanwise twist baked in, and a slim root.
Overall diameter stays exactly 44 in (tip r558.8). Structural validation of the print + rod
approach is explicitly the owner's responsibility and out of scope here; this doc owns
geometry, aero intent, and the OnShape build path.

## Why this shape

- **Reynolds number is tiny**: 28k at max chord at 60 RPM, 78k at 170 RPM. In this regime
  thick airfoils are actively bad; thin (6–8%) sections with real camber are what indoor-flight
  and HVLS practice uses. Section: **NACA 6407** (6% camber at 40%, 7% thick) — enough camber
  to work at low Re, enough thickness to swallow the rod at the 30%-chord max-thickness point.
- **Twist is baked in** (17° root → 8.5° tip): local blade speed grows with radius, so
  constant pitch over-loads the root and under-loads the tip. Washout evens the loading, and
  overall pitch becomes a blade print variant instead of an adapter variant (see
  `PITCH_OFFSET` below).
- **Planform from loading, not from a router**: chord peaks at mid-span (r250) and tapers both
  ways. Inboard span contributes little thrust (thrust per unit span scales like r²), so the
  fat root of the flat blade bought nothing; a slim root costs almost no airflow and reads far
  lighter visually. The **straight 30%-chord line is the spar axis**, so with the tapering
  chord the trailing edge naturally sweeps forward toward the tip — a mild scimitar that falls
  out of the aero rather than being styled on.
- **Tip**: chord collapses to a raked, rounded tip raised 8 mm toward the ceiling over the
  last ~55 mm (a gentle proplet). Softens the tip vortex at trivial cost and replaces the old
  R20 safety corners with an everywhere-rounded end.
- **Cambered = directional**: forward (LE-first, suction side toward the ceiling) is the
  optimized direction; reverse still functions for destratification at reduced efficiency.
  This is the accepted trade (2026-07-27) and retires the symmetric-edge requirement.

## Coordinates

Blade-local frame used by this doc and the Part Studio: **origin on the rotor axis at the
blade pitch plane, X radial outboard, Z up toward the ceiling, Y toward the leading edge.**
Project Z (ceiling-down) = 223.5 − Z_local. The spar/pitch axis is the X axis; every section
is anchored to it at its 30%-chord point. Twist rotates the LE toward the ceiling (+Z_local).

## Station table

| r, mm | Chord, mm | Twist, ° | t_max, mm | Anchor y-shift, mm | Z-raise, mm | Role |
|---:|---:|---:|---:|---:|---:|---|
| 110 | 78 | 17.0 | 5.5 | 0 | 0 | Root section |
| 180 | 100 | 15.0 | 7.0 | 0 | 0 | Root fitting outboard end |
| 250 | 118 | 13.0 | 8.3 | 0 | 0 | Max chord |
| 330 | 112 | 11.5 | 7.8 | 0 | 0 | Segment joint |
| 420 | 94 | 10.0 | 6.6 | 0 | 0 | |
| 500 | 76 | 9.0 | 5.3 | 0 | 3 | Tip run-in starts |
| 556 | 40 | 8.5 | 2.8 | −6 | 6 | Rake + proplet |
| 557.5 | 14 | 8.5 | 1.0 | −10 | 8 | Micro-station; full-round cap to r558.8 |

Anchor y-shift slides the section's 30%-chord point aft (−Y) of the spar axis; nonzero only
in the tip rake. Z-raise lifts the section toward the ceiling for the proplet. Intermediate
chords/twists come from the loft — do not spline extra stations.

**Pitch variants**: a single Variable Studio scalar `PITCH_OFFSET` (default 0°) added to every
station twist regenerates the whole blade at ±2° etc. This replaces the BA-10/12/14 family;
commissioning pitch changes are reprints.

## Section: NACA 6407, normalized coordinates

Spline through these (x/c, y/c) points in order (TE → upper → LE → lower → TE); x measured
from the LE along the chord, y toward the ceiling. Prefer the public "NACA 4-series airfoil"
custom FeatureScript (enter 6407) and keep this table as the fallback / cross-check.

```
1.0000 -0.0000   0.9893 0.0031   0.9574 0.0118   0.9058 0.0251   0.8364 0.0411
0.7521 0.0577    0.6565 0.0729   0.5537 0.0848   0.4483 0.0922   0.3441 0.0936
0.2461 0.0860    0.1599 0.0709   0.0895 0.0514   0.0382 0.0311   0.0080 0.0132
0.0000 0.0000    0.0138 -0.0067  0.0483 -0.0065  0.1015 -0.0010  0.1710 0.0078
0.2539 0.0171    0.3469 0.0242   0.4472 0.0270   0.5508 0.0274   0.6525 0.0256
0.7479 0.0215    0.8327 0.0160   0.9032 0.0101   0.9561 0.0048   0.9889 0.0013
1.0000 0.0000
```

## Spar and segmentation

- **Spar**: one Ø3 × 400 mm pultruded CF rod, **cut to 358 mm**, occupying a Ø3.4 mm channel
  on the spar axis from r112 to r470. Outboard of r470 the section gets too thin for
  ≥1 mm channel walls; the unsupported tip span carries trivial load. Adhesive bond along the
  full channel at assembly.
- **Two segments**, joined at r330 (near max chord, deepest glue face):
  - **Segment A** r110→r330 (220 mm) including the root fitting.
  - **Segment B** r330→r558.8 (229 mm) with the channel blind-ended at r470.
  - **Joint**: a single flat scarf plane through (r330, y0), rotated 30° about the Z axis so
    the seam runs diagonally across the chord (~130 mm seam, ~2.4× the glue area of a butt
    joint). The rod crosses the joint and self-aligns it; the non-normal plane keys the two
    halves against relative rotation about the rod. Model B's joint face with **0.10 mm
    clearance offset**; glue fills it.
  - Assembly: slide the rod fully into A from the joint face, wet the channel and scarf, seat
    B over the protruding rod.
- Both segments print with span vertical (joint face / root face on the bed), ≤230 mm tall —
  fits the X2D trivially. Seam lands as a deliberate diagonal feature line, not a scar.

## Root fitting (the adapter interface)

The blade slims toward the root; the structure is a boss under the airfoil, directly on the
rod span, so the (out-of-scope) BA-00 flat adapter clamps where the spar is:

- **Pad**: underside flat at **Z_local −16.5** (project Z240.0), footprint r118–r192,
  y +18 to −40, R8 perimeter transitions blending into the airfoil body. At r110 the airfoil's
  own lower surface reaches Z239.5, so the pad is nearly flush at the root and proud further
  out.
- **Bolts**: four Ø5.5 vertical through-holes at **r130/r180, y +10/−30** (two rows parallel
  to the spar, straddling it; the old y±25 pattern no longer fits the slim root — this
  pattern is the adapter's to match, RH-100 is untouched). Top side: hex-nut pockets for M5
  all-metal prevailing nuts, sunk normal to Z. Hardware from below should be flat/low-head;
  everything below Z240 (plate + heads) has 14 mm of budget to the Z254 floor.
- **Balance pocket**: Ø15 × 2 mm blind pocket in the pad underside near (r155, y−10) for
  stick-on trim weights, concealed by the adapter plate. First-moment matching spec (≤0.5%)
  carries over from BL-100.
- The r110 root end face is a clean rounded closure of the airfoil — with the slim root the
  old printed "root stop" ledge is replaced by the pad/adapter interface itself.

## Envelope compliance (checked 2026-07-27)

Computed from the station table with twist about the 30% anchor (script:
[`cad/bp100_envelope_check.py`](../cad/bp100_envelope_check.py), rerun if stations change):

- Upper surface worst case Z211.6 (r250) — inside the ≥Z203.2 ceiling-gap floor; the raised
  tip reaches Z211.8.
- Lower surface worst case Z242.1 (r250); root pad Z240.0 + below-pad hardware ≤ Z254 ✓.
- Tip radius exactly 558.8 (44.0 in) — do not exceed.
- Estimated mass ~130–150 g per blade in foaming PLA + 5 g rod, vs ~320 g birch — roughly
  halves rotor mass and stored energy; hub/catcher specs unchanged (they were sized for the
  heavier rotor).

## OnShape build sequence

1. **Variable Studio** `blade-vars`: `R_TIP = 558.8`, `ROD_D = 3.4`, `PITCH_OFFSET = 0°`,
   plus per-station chord/twist arrays mirroring the station table.
2. **Part Studio**, blade-local frame (origin = rotor axis at pitch plane, X radial, Z to
   ceiling). Sketch `spar` on Top: construction line (110, 0) → (558.8, 0).
3. **Station planes**: offset planes from Right at each station radius (8 planes).
4. **Sections**: on each plane, the NACA 4-series custom feature — code 6407, chord and
   twist (+`PITCH_OFFSET`) per table, rotation about the 30%-chord point, that point placed
   at (y = anchor-shift, z = Z-raise), LE toward +Y, upper surface toward +Z. Fallback: spline
   the 31-point table into a station sketch, then scale/rotate/translate per station.
5. **Main loft**: sections r110 → r500, no end conditions. Verify with curvature combs /
   zebra; if the mid-span looks starved between r250 and r330, add LE/TE guide splines
   through the section endpoints rather than extra stations.
6. **Tip loft**: continue r500 → r556 → r557.5 in one loft (tangent to the main loft), then
   **full-round fillet** the r557.5 end face. Confirm the rounded end reaches r558.8; adjust
   the micro-station chord if the fillet falls short.
7. **Root pad**: sketch the pad footprint on an offset plane at Z −16.5, extrude up **to
   next face** into the airfoil body (add), R8 fillets on the perimeter blend.
8. **Holes**: four Ø5.5 through-all at r130/r180 × y+10/−30; hex pockets on the top exit
   faces; Ø15 × 2 balance pocket in the pad underside.
9. **Spar channel**: sketch Ø`ROD_D` on the r112 station plane centered on the spar axis,
   extrude-remove to r470.
10. **Split**: plane through (330, 0, 0) rotated 30° about Z; Split part → segments A and B.
    Offset B's joint face −0.10 mm (Move Face) for glue clearance.
11. **Checks**: section > measure wall at r420–r470 around the channel (≥1.0 mm), verify
    Z_local extremes against the envelope numbers above, mass properties per segment.
12. **Export**: STL per segment (A root-face down, B joint-face down), into `cad/` as
    `BP-100_segA` / `BP-100_segB` once accepted; print 4 blade sets, select 3, keep a spare,
    per the BL-100 practice.

## Open items

- BA-00 flat adapter design (out of scope here): flat plate mating the pad, four M5 at
  r130/r180 y+10/−30, plus whatever hub-side geometry RH-100's stations demand. RH-100 is
  unchanged.
- LS-100 load spreaders are a wood-blade artifact; whether the printed pad wants washer
  plates is the adapter/strength owner's call.
- Structural validation of print + rod (owner's scope): if it changes wall/channel geometry,
  update the station table and re-run the envelope check.
- Acoustic/flow check at commissioning: the twist schedule is an aero estimate, not measured
  data; treat twist and `PITCH_OFFSET` like the other provisional commissioning numbers.
