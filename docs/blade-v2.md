# BP-100 printed blade (v3 — integrated root)

> **Status: v3 accepted and modelled in OnShape 2026-07-28.** v3 deletes the blade adapter
> entirely: the blade root is a flat mounting rectangle, printed as part of the blade, that
> bolts straight to RH-100's stations. Supersedes same-week v2 (separate pad + flat BA-00
> adapter — git holds that revision) and the original BL-100 birch blade + LS-100 spreaders
> + BA-10/12/14 pitch family (their [parts.md](parts.md) sections remain as the fallback).
> Segments export to `cad/BP-100.step` when re-exported (the committed STEP is still v2 —
> re-export pending).

A 3D-printed blade (aero/LW-PLA class filament; material for the loaded root print is the
owner's call) with a Ø3 mm carbon-fiber rod spar, cambered low-Reynolds airfoil sections,
spanwise twist baked in, and an integrated root plate. Overall diameter ~Ø1116 mm (44.0 in
do-not-exceed; the plan-view tip trim lands the apex just inside r558.8). Structural
validation of the print + rod + bolted root is explicitly the owner's responsibility and out
of scope here; this doc owns geometry, aero intent, and the OnShape build path.

## Why this shape

- **Reynolds number is tiny**: 28k at max chord at 60 RPM, 78k at 170 RPM. Thin (6–8%)
  cambered sections are what this regime wants. Section: **NACA 6407** (6% camber at 40%, 7%
  thick) — enough camber to work at low Re, enough thickness to swallow the rod at the
  30%-chord max-thickness point.
- **Twist is baked in** (16.7° at r120 → 8.5° tip): washout evens the spanwise loading;
  overall pitch is a print variant via the `PITCH_OFFSET` feature input, not an adapter.
- **Hugger-gap note (2026-07-27 raise)**: the ~119 mm ceiling gap restricts inflow, which
  raises every station's effective angle of attack. Rather than pre-guessing new twist, tune
  at commissioning: if low-RPM airflow is weak or flow noise appears, reprint at
  `PITCH_OFFSET` −1° to −2°.
- **Planform from loading**: chord peaks mid-span (118 at r250), slim root, straight
  30%-chord spar line → mild natural scimitar.
- **Tip**: chord collapses to a rounded, **downward-drooped** proplet (zr −3/−6/−6.4). v2
  raked the tip *up*, but after the raise the up-rake sat exactly in the intake throat — the
  narrow annulus at the rotor perimeter all intake air passes through; drooping opens the
  throat and sheds the tip vortex away from the ceiling.
- **Cambered = directional**: forward (LE-first, suction side up) optimized; reverse
  degraded-but-functional by accepted trade.
- **No adapter (v3)**: with the root printed into the blade, a separate bolted adapter added
  a joint, a part, and a qualification program while gaining nothing. RH-100 is unchanged —
  the blade consumes its stations directly.

## Coordinates

Blade-local frame: **origin on the rotor axis at the pitch plane, X radial outboard, Z up
toward the ceiling, Y toward the leading edge.** Project Z (ceiling-down) = **124.2 −
Z_local** (pitch plane = hub underside 118.2 + 6, the rectangle mid-thickness; driven by
`#hubBottom + 6 mm` in OnShape, `#standoffLen` = 62). Sections anchor to the spar at the
**camber-line point above 30% chord** (0.05625 c above the chord line — chord-line anchoring
puts a straight rod outside the material; caught 2026-07-27). Twist rotates the LE toward
the ceiling.

## Station table

| r | chord | twist | ys | zr |
|---:|---:|---:|---:|---:|
| 120 | 81 | 16.7° | 0 | 0 |
| 180 | 100 | 15.0° | 0 | 0 |
| 250 | 118 | 13.0° | 0 | 0 |
| 330 | 112 | 11.5° | 0 | 0 |
| 420 | 94 | 10.0° | 0 | 0 |
| 500 | 76 | 9.0° | 0 | −3 |
| 556 | 40 | 8.5° | −6 | −6 |
| 557.5 | 18 | 8.5° | −7 | −6.4 |

The first station moved r110 → r120 (v3) to give the root transition 24 mm of run; the end
station is deliberately moderate (v2's c14/ys−10/zr−8 hook was unloftable even with guides)
— the plan-view tip rounding comes from a manual trim, not the station.

## Root (the hub joint, replacing the adapter)

- **Rectangle**: r52–r96 × y±25 × 12.0 thick, top face flush on the RH-100 underside
  (Z118.2). Inner end is a concave arc r52 centered on the axis — the three roots form a
  broken ring around the catcher. Outer corners reach r99.2, inside the hub's Ø200
  silhouette.
- **Bolts**: four M5 A4-80 from above through the hub's Ø5.5 stations (r62/r88, y±15) into
  **hex-nut pockets in the rectangle underside** (8.1 across-flats × 5.0 deep, ISO 4032
  nuts, all-metal prevailing class). No printed thread carries load.
- **Dowels**: the blade prints **integrated Ø5 pins** on its top face at (r66, y0), (r86,
  y0), engaging RH-100's existing blind dowel holes (owner decision 2026-07-28; steel
  dowels deleted). Registration + shear in plastic is owner-scope like the rest of the
  print's strength.
- **Balance**: no pocket (v2's Ø15 pocket deleted). First-moment matching (≤0.5%, carried
  from BL-100 practice) via stick-on weights on the rectangle underside if needed.
- **Transition**: guided loft r96 → r120 (see build sequence). Aero inboard of r120 is
  negligible (thrust/span ~ r²), so the flat rectangle costs nothing measurable.

## Spar and segmentation

- Rod channel Ø3.4 at rectangle mid-thickness, **r56–r430**; rod cut to **374 mm** from the
  400 mm stock. Inner end leaves a 4 mm cap to the r52 arc; outer end is where the drooping
  proplet run-in drops the loft off the straight rod line (wall dies ~r460 — check script).
- **Scarf joint at r330** unchanged from v2: split plane through (330, 0) rotated 30° about
  Z, segB joint face offset −0.10 mm for glue clearance, rod bridges the joint. SegA
  (rectangle + transition + blade to r330, ~280 mm) and segB (~229 mm) both fit the X2D.

## Envelope compliance (checked 2026-07-28, `cad/bp100_envelope_check.py`)

- Upper surface worst Z118.8 (r250) — ceiling gap 4.68 in, the accepted hugger deviation
  ([decisions.md](decisions.md)).
- Lower surface worst **Z149.2** (r250) — ~11 mm above the ~160 cabinet-door line, far
  inside the Z254 envelope floor. The blade is the lowest thing in the assembly (spindle
  end Z142 is above it).
- Rod walls ≥1.36 mm (r120) over the whole channel span; 1.42 mm at r430.
- Blade tops (Z118.8, sweeping r ≥ 110) vs the future ENC-100 wall (r ≤ 106): ~4 mm radial
  — the binding constraint for the housing design (see parts.md ENC-100).
- Mass: est. 130–150 g/blade in foaming PLA + 5 g rod (hub/catcher sized for the heavier
  birch rotor).

## OnShape build sequence (v3, as built)

The generator is `cad/bp100_sections.fs` — **four features** in one Feature Studio, all
taking the same dialog values (**Pitch plane depth = `#hubBottom + 6 mm`**, Pitch offset,
TE thickness 0.6):

1. **Root rectangle** (manual): sketch on the hub underside — r52 center-point arc, y±25
   lines, x=96 closer; extrude down 12, New. Then Ø5.5 through-holes projected from the
   hub's stations, hex nut pockets (8.1 AF × 5.0) from below, integrated dowel pins on top.
2. **"BP-100 airfoil sections"**: all 8 station sketches.
3. **"BP-100 root guides"**: four 3D splines, rectangle end-face corners → exact r120
   section points, smoothstep-eased so they leave the slab tangent. An unguided
   face-to-spline loft twists; manual loft connections don't fix it (2026-07-28).
4. **Main loft**: profiles = station sketches **r120…r557.5**, guides = the five curves
   from **"BP-100 span guides"** (LE, both TE ends, mid-chord upper/lower, through exact
   section points at every profile with dense samples through the taper). One guided loft
   end-to-end — two lofts meeting at r500 always left a planform crease.
5. **Transition loft**: rectangle end face → main loft's r120 end face, the four root
   guides as Guides, Add (fuses slab + blade).
6. **Tip finish** (manual, by eye): top-view sketch — smooth arc leaving the LE silhouette
   ~r548, apex ≤ r558.2, back to the TE; extrude-remove through-all; **full-round fillet**
   the cut wall (fall back to R1 edge fillets if it refuses).
7. **"BP-100 spar channel"**: Ø3.4, r56–430.
8. **Scarf split** at r330 (30° plane), Move Face segB −0.10.
9. Rename **BP-100 segA / segB**, circular pattern ×3 about Z.
10. Re-export `cad/BP-100.step` from the finished segments.

## Open items

- **Re-export `cad/BP-100.step`** (committed STEP is v2 geometry).
- Print orientation + material for the loaded root (LW-PLA vs PPA-CF for segA), and the
  whole strength/qualification program: owner-scope. The parts.md adapter qualification
  content (filament research, hot/humid + fatigue matrix) now applies to the blade root
  print.
- `PITCH_OFFSET` tuning for the hugger gap at commissioning (see "Why this shape").
- Record the as-built tip apex radius (owner drew the trim arc by eye; target ≤ r558.2).
