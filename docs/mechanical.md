# Mechanical design

> **Temporary**: the original interactive envelope and stack diagrams are still viewable at
> https://stillair-fan-design.syas.chatgpt.site/mechanical (requires ChatGPT auth). Remove this
> link once the OnShape model reproduces them.

A fixed assembly with explicit motor gates. The GL100 structure is dimensioned part by part in
[parts.md](parts.md); this doc covers the envelope, the vertical stack, rotor geometry, and
the independent retention paths. Only purchased-motor measurements, slab conditions, and
qualification results remain release-dependent.

## Envelope

Baseline: 44 in diameter, 60 RPM typical operating point, 8.1 in nearest-surface gap, 12°
pitch. 42 in remains the airflow/handling fallback; 170 RPM is the user maximum.

| Parameter | Value |
|---|---|
| Rotor diameter | 44 in |
| Nearest-surface gap to ceiling | 8.1 in |
| Nominal pitch | 12° |
| Wall-tip clearance | 5.5 in / side |
| Tip speed (60 RPM) | 3.5 m/s |
| Blade pitch plane | 8.8 in down |
| Lowest blade surface | 9.4 in down |

Wall-clearance deviation: 44 in leaves 5.5 in to each wall, below common 18-inch guidance. No
useful fan fits that guidance in this 55-inch space. Do not exceed 44 in, and keep 42 in
available if wall-flow testing is poor.

## Vertical stack

Z = 0 is the finished ceiling; positive Z points down. Everything stays inside 10 inches
(254 mm absolute). The 138 mm standoffs place the GL100 stationary face at Z152; its 34.2 mm
body ends at Z186.2, and the blade center plane is Z223.5. Across 10°, 12°, and 14° adapters,
the upper blade surface stays 8.00–8.17 in from the ceiling and the lowest point stays
9.43–9.60 in down.

| Interface | Z, mm |
|---|---:|
| Ceiling and plate top | 0.0 |
| Ceiling plate underside | 6.0 |
| Vertical PCB range | 25.0–103.0 |
| Motor carrier top | 144.0 |
| Carrier underside / GL100 stationary face | 152.0 |
| GL100 rotating face | 186.2 |
| Rotor hub top / underside | 186.2 / 194.2 |
| Catcher disk top / underside | 196.7 / 200.7 |
| Blade radial center plane | 223.5 |
| Lowest blade at 10° / 12° / 14° | 239.4 / 241.6 / 243.8 |
| Absolute lowest permitted point | 254.0 |

At the 132 mm maximum chord and 9 mm thickness, the upper blade point is Z207.6 at 10°,
Z205.4 at 12°, and Z203.2 at 14°.

## Coordinate system

- Rotor axis: X0, Y0.
- Blade centerlines: 0°, 120°, 240°.
- Standoff centerlines: 90°, 210°, 330°.
- Hall magnet: r68 at 30°. Counterweight: r68 at 210°.

## Primary structure

Simple plates, posts, and one turned spindle (full dimensions in [parts.md](parts.md)):

- **MP-100 ceiling plate** — Ø210 × 6 mm 304 stainless. Two 11 × 20 mm anchor slots on 130 mm
  centers, three Ø6.6 standoff holes on Ø150 PCD, Ø16.2 spindle opening, separate tether
  opening, and a P-clip strain-relief tapping pair at 15° (no cable slot — the supply is a
  surface run entering at the housing rim; see [parts.md](parts.md) "Cable entry").
- **ST-100 standoffs** — three Ø16 × 138 mm 6061-T6 posts, M6 × 1 tapped ≥12 mm both ends.
- **MC-100 motor carrier** — Ø188 × 8 mm 6061-T6. Standoff holes on Ø150 PCD, 4 × Ø4.5 on the
  GL100 Ø60 PCD, Ø20.5 spindle clearance, tether pair, Hall mount, verified wire window.
- **RH-100 rotor hub** — Ø200 × 8 mm 6061-T6. Ø20.5 captured aperture, four
  underside-countersunk Ø4.5 holes on the GL100 Ø50 PCD for subflush M4 flat-heads, measured
  pilot ring, three dowel-registered adapter stations, retained tach magnet.

**Motor screw-depth rule**: rear M4 threads are officially 6 mm maximum; output-face M4
threads are 3.5 mm maximum. The baseline uses M4 × 12 through a 1.5 mm carrier counterbore
and M4 × 10 through the 8 mm hub. Both engagements must be physically measured before
machining release.

## Rotor geometry

> **Superseded 2026-07-27**: the rotor now uses printed BP-100 cambered-airfoil blades with
> CF-rod spars, baked-in 17°→8.5° twist, and a single flat adapter — see
> [blade-v2.md](blade-v2.md) (which re-derives the vertical envelope; the 12° "nominal
> pitch" in the envelope table above belongs to this superseded flat blade). The birch
> geometry below is retained as the fallback.

Three 9 mm birch blades on printed pitch adapters. Cut four, finish all four identically,
select the best-balanced three, keep the fourth as a ready spare. The symmetric edge treatment
supports reverse operation.

| Radius, mm | Chord, mm | Intent |
|---:|---:|---|
| 110 | 115 | Aerodynamic root and printed root stop |
| 180 | 122 | Inner load-spreader line |
| 320 | 132 | Maximum chord |
| 420 | 128 | Begin gradual taper |
| 500 | 108 | Tip transition |
| 558.8 | 92 | Exact 44-inch radius; R20 tip corners |

- **BA-10/12/14 adapters** — qualified CF-PPA, approx r52–205 with a y±25 hub base and wider
  blade saddle, printed flat on the hub base. Four M5 hub bolts plus two Ø5 dowels; four M5
  blade bolts at r135/r185 and y±25.
- **Metal load spreaders** — two 65 × 15 × 2 mm 6061 straps per blade, each bridging a 50 mm
  tangential bolt pair on the upper face. No printed thread or heat-set insert carries the
  primary load.

## Independent retention

Two secondary load paths:

1. **Central catcher** (SP-100 + KD-100) protects against GL100 bearing/rotor retention
   failure and four-M4 hub release. 17-4PH Ø16 flanged spindle with a Z196.7 shoulder, M12
   lower thread, Ø50 × 4 mm 316 catcher disk, castellated nut, and cotter. The flange carries
   two 30.0 mm across-flats keyed into a matching double-D pocket in MP-100, so the nut
   torques from below with no counter-hold. The spindle passes
   through the GL100 Ø30 bore without normal contact (Ø20.5 hub aperture gives 2.25 mm radial
   gap per side; 2.5 ±0.5 mm axial gap to the disk). The M4 hub screws are 0.1–0.2 mm
   subflush; verify ≥2.0 mm worst-case clearance to every rotating surface. Static proof to
   1.25 kN, then dynamically catch the final mass off-ceiling, including an off-axis/tilted
   drop case (pure-axial is the optimistic assumption).
2. **Whole-assembly tether** protects against the plate, standoffs, and primary anchors as a
   group. At least 4.5 kN complete-system rating, 15–20 mm slack, separate concrete anchor,
   and a rated two-hole fitting at MC-100. Calculate impact energy and dynamically catch the
   final assembly on a representative fixture.

## Motor release gates

Measure these before ordering motor-dependent metal:

- **Face ownership** — confirm Ø50/M4 rotates and Ø60/M4 is stationary.
- **Bore + pilot** — measure both bore faces and identify which surfaces rotate.
- **Thread depth** — depth-pin both M4 patterns before selecting final screws.
- **Wire exit** — import the current STEP and locate the rear lead window and flat annuli.
- **Bearing load** — obtain axial/radial/inertia basis or accept it as documented residual risk.

## Proof and quality targets

| Item | Value |
|---|---|
| Runaway load case | 270 RPM (calculation basis, raised from 250 in 2026-07 review — supply-power bound; never dynamically tested) |
| Guarded rotor proof | 216 RPM × 2 min/direction |
| Installed adapter proof | 500 N radial each |
| Batch destructive test | >1.0 kN |
| Hub OD runout | ≤0.10 mm TIR |
| Blade first-moment mismatch | ≤0.5% |
