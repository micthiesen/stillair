# Mechanical design

> **Temporary**: the original interactive envelope and stack diagrams are still viewable at
> https://stillair-fan-design.syas.chatgpt.site/mechanical (requires ChatGPT auth). Remove this
> link once the OnShape model reproduces them.

A fixed assembly with explicit motor gates. The GL100 structure is dimensioned part by part in
[parts.md](parts.md); this doc covers the envelope, the vertical stack, rotor geometry, and
the independent retention paths. Only purchased-motor measurements, slab conditions, and
qualification results remain release-dependent.

## Envelope

Baseline: 44 in diameter, 60 RPM typical operating point, ~4.5 in nearest-surface gap
(hugger regime — deliberate, see below), BP-100 twisted blade. 42 in remains the
airflow/handling fallback; 170 RPM is the user maximum.

| Parameter | Value |
|---|---|
| Rotor diameter | 43.94 in (Ø~1116; 44.0 in do-not-exceed) |
| Nearest-surface gap to ceiling | 4.68 in (118.8 mm) |
| Wall-tip clearance | 5.5 in / side |
| Tip speed (60 RPM) | 3.5 m/s |
| Blade pitch plane | 4.89 in (124.2 mm) down |
| Lowest blade surface | 5.87 in (149.2 mm) down — the assembly's lowest point |

**2026-07-27/28 raise**: the rotor was raised ~99 mm (blade bottom 248.5 → 149.2) so open
cabinet doors (~160 mm line) clear the blades — a hard collision constraint that arrived
after the original envelope was chosen. Realized as: standoffs 138 → **62** and the blade
adapter **deleted** (BP-100 v3 integrates the root, [blade-v2.md](blade-v2.md); the interim
84 mm/flat-BA-00 step lasted one day). Aero cost of the ~0.106 D ceiling gap and the RPM
compensation are recorded in [decisions.md](decisions.md) > Accepted deviations.

Wall-clearance deviation: 44 in leaves 5.5 in to each wall, below common 18-inch guidance. No
useful fan fits that guidance in this 55-inch space. Do not exceed 44 in, and keep 42 in
available if wall-flow testing is poor.

## Vertical stack

Z = 0 is the finished ceiling; positive Z points down. Everything stays inside 10 inches
(254 mm absolute). The 62 mm standoffs place the GL100 stationary face at Z76; its 34.2 mm
body ends at Z110.2, and the blade pitch plane is Z124.2 (the mid-thickness of the blade's
root rectangle, bolted flush to the hub underside). The blade tops (Z118.8) rise above the
root plane *beside* the mechanism — the rotor sweeps r ≥ ~96, outboard of every stationary
part below the plate, and the plate/housing sit well above. The spindle end (Z144, central,
r ≤ 11) is above the lowest blade surface, so the blades set the assembly's lowest point.

| Interface | Z, mm |
|---|---:|
| Ceiling and plate top | 0.0 |
| Ceiling plate underside | 6.0 |
| PCB envelope (horizontal under the plate; see [electrical.md](electrical.md)) | ~12–35 |
| Motor carrier top | 68.0 |
| Carrier underside / GL100 stationary face | 76.0 |
| GL100 rotating face | 110.2 |
| Rotor hub top / underside | 110.2 / 118.2 |
| Highest blade surface | 118.8 |
| Blade root rectangle (top flush on hub) | 118.2–130.2 |
| Catcher disk top / underside | 120.7 / 126.7 |
| Blade pitch plane (rod axis) | 124.2 |
| Castellated nut → cotter → spindle end | 126.7 → 139.2 → 144.0 |
| Lowest blade surface | 149.2 |
| Absolute lowest permitted point | 254.0 |

## Coordinate system

- Rotor axis: X0, Y0.
- Blade centerlines: 0°, 120°, 240°.
- Standoff centerlines: 90°, 210°, 330°.
- Tach stations: r76 on the three arm/blade-station lines, one per arm — one N52 magnet
  + two mass-matched brass slugs, balanced by three-fold symmetry (moved from
  r68 @ 30°/210° in the 2026-07-28 RH-100 spoke restyle). The stationary Hall sensor
  line stays 30°, sensing radius r76.
- Phase-lead window: r45.6 at 315° (clocked 2026-07-27 from the GL100 STEP: pad-to-bolt-hole
  offset is a fixed 44.43°, bolt holes on the axes, so the pad lands on ~45° diagonals; 315°
  keeps the Hall corridor at 30° clear and shortens the phase-lead run to the PCB side).

> **OnShape model frame**: the existing OnShape document is rotated **180° about Z** relative
> to this table (tether at +Y in the model, −Y here; lone standoff at −Y). Discovered
> 2026-07-27; kept as-is because the model is internally consistent. Convert with
> *model angle = doc angle + 180°*; Variable Studio angles (`#phaseClock`) are model-frame.

## Primary structure

Simple plates, posts, and one turned spindle (full dimensions in [parts.md](parts.md)):

- **MP-100 ceiling plate** — Ø210 × 6 mm 304 stainless. Two 11 × 20 mm anchor slots on 130 mm
  centers, three Ø6.6 standoff holes on Ø150 PCD, Ø16.2 spindle opening, separate tether
  opening, and a P-clip strain-relief tapping pair at 15° (no cable slot — the supply is a
  surface run entering at the housing rim; see [parts.md](parts.md) "Cable entry").
- **ST-100 standoffs** — three Ø16 × 62 mm 6061-T6 posts, M6 × 1 tapped ≥12 mm both ends
  (shortened from 138 in the 2026-07-27/28 raise).
- **MC-100 motor carrier** — Ø180 × 8 mm 6061-T6. Standoff holes on Ø150 PCD, 4 × Ø4.5 on the
  GL100 Ø60 PCD, Ø20.5 spindle clearance, tether pair, Hall mount, verified wire window.
- **RH-100 rotor hub** — Ø200 × 8 mm 6061-T6. Ø20.5 captured aperture, four
  underside-countersunk Ø4.5 holes on the GL100 Ø50 PCD for subflush M4 flat-heads, measured
  pilot ring, three dowel-registered blade-root stations (BP-100 v3 blades bolt directly,
  their printed pins engaging the dowel holes), retained tach magnet.

**Motor screw-depth rule**: rear M4 threads are officially 6 mm maximum; output-face M4
threads are 3.5 mm maximum. The baseline uses M4 × 12 through a 1.5 mm carrier counterbore
and M4 × 10 through the 8 mm hub. Both engagements must be physically measured before
machining release.

## Rotor geometry

> **Superseded 2026-07-27/28**: the rotor now uses printed BP-100 v3 cambered-airfoil
> blades with CF-rod spars, baked-in twist, and an **integrated root** bolted straight to
> the hub (no adapter at all) — see [blade-v2.md](blade-v2.md); pitch plane now Z124.2. The
> birch geometry below is retained as the fallback.

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
   failure and four-M4 hub release. 17-4PH Ø16 flanged spindle with a Z120.7 shoulder, M12
   lower thread, Ø50 × 6 mm purchased stainless catcher disk (2026-07-28: an Amazon
   lathe-machined washer replaced the custom 4 mm laser part; stack re-based in
   [parts.md](parts.md)), castellated nut, and cotter. The flange carries
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
| Installed blade-root joint proof | 500 N radial each (was "adapter proof"; the printed root joint inherits it) |
| Batch destructive test | >1.0 kN |
| Hub OD runout | ≤0.10 mm TIR |
| Blade first-moment mismatch | ≤0.5% |
