# Part specifications (CAD handoff)

> **Temporary**: the original dimensioned drawing diagrams (assembly section, plate/carrier/hub
> top views, blade plan, capture detail) are still viewable at
> https://stillair-fan-design.syas.chatgpt.site/drawings (requires ChatGPT auth). Remove this
> link once the OnShape model reproduces them.

Dimensioned starting design for every fabricated part, one step before production drawings.
Z = 0 at the finished ceiling, positive Z down (see [mechanical.md](mechanical.md) for the
stack and coordinate system). Import the current CubeMars GL100 STEP and physically verify
every motor-dependent dimension before ordering machined parts. Final models are built in
OnShape; exports and 2D fabrication files land in [`cad/`](../cad/).

GL100 sources (use the current Ø106.8 × 34.2 mm revision, **not** the older Ø95 × 37.1 mm
drawing):

- Product page: https://www.cubemars.com/product/gl100-kv10-gimbal-motor.html
- Official 2D drawing: https://www.cubemars.com/data/cms/202602/gl100-gimbal-motor-2d-drawing.pdf
- Official STEP package: https://www.cubemars.com/data/cms/202602/gl100-gimbal-motor-3d-drawing.zip

## GL100 release checks

- Official envelope: Ø106.8 × 34.2 mm, Ø30 bore, 698 g, 20 pole pairs.
- Front interface: 4 × M4 on Ø50 PCD, 3.5 mm maximum thread depth.
- Rear inner interface: 4 × M4 on Ø60 PCD, 6.0 mm maximum depth.
- Rear outer interface: 6 × M2.5 on Ø100 PCD, 4.0 mm maximum depth.
- Confirm that Ø50/M4 is the rotating output face and Ø60/M4 is stationary.
- Measure both bore faces, determine which bore surfaces rotate, and depth-pin both M4 patterns.
- Import the STEP to locate the wire exit, steps, chamfers, contact annuli, and face ownership.
- Obtain or disposition the continuous axial/radial load, overturning moment, external rotor
  inertia, and bearing-life basis for vertical-axis operation.
- Do not use the Ø100/M2.5 pattern structurally until its ownership is physically confirmed.

### Bearing-data request (Gate 01, researched 2026-07)

No public bearing or load data exists for the GL series (checked every storefront and
CubeMars' guides; their technical-support page hosts full manuals for the AK actuator line
but nothing for GL, and they do publish load ratings for actuators — so a direct ask is
precedented, via info@cubemars.com). What the research could bound:

- The ~20–30 N axial hang (2–3 kg rotor) is almost certainly trivial: any plausible bearing
  in a Ø106.8 × 34.2 housing with a Ø30 bore carries multi-kN catalog ratings.
- The genuine unknowns are **overturning-moment capacity** (blade imbalance loads react as an
  edge-load couple across whatever bearing spacing exists inside a 34.2 mm pancake) and
  whether it's a single bearing or a spaced pair.
- 35–170 RPM continuous duty is favorable for bearing fatigue life (few load cycles per unit
  time).
- Additional published data found: rotor inertia 2310 g·cm², IP45, −20 to 50 °C operating
  range, Kv 9.3 RPM/V.

Questions to send CubeMars: (1) bearing type/part number/quantity/axial spacing in the
current GL100 revision; (2) continuous axial (thrust) rating, axis vertical; (3) continuous
radial rating; (4) allowable overturning moment and its evaluation radius; (5) documented
L10 life at 35–170 RPM under ~30 N axial; (6) precedent continuously-rotating hanging
deployments (radar heads) and whether mass rode on the motor bearings; (7) whether they
recommend an external thrust bearing for hanging loads; (8) whether a GL-series mechanical
manual exists like the AK-series ones.

Fallback if data never comes (this gives Gate 01's "independently rated bearing path"
concrete shape): an external thrust/slew bearing carries the rotor weight and moment, and
the GL100 transmits torque only through a non-structural coupling.

## MP-100 ceiling plate

- Ø210 × 6.0 mm 304 stainless disk, flat within 0.30 mm, brushed and passivated.
- Two 11 × 20 mm radial anchor slots centered at X±65, Y0 (130 mm anchor centers).
- Three Ø6.6 standoff holes on Ø150 PCD at 90°, 210°, 330°, countersunk from the ceiling face
  for M6 flat-head screws.
- Center spindle opening Ø16.2; top-face flange recess Ø34.2 × 3.1 deep.
- Separate tether-anchor clearance at X0, Y−82: 14 × 22 mm.
- Cable entry: 12 × 20 mm radiused slot, angle coordinated with the wall conduit.
- EB-100 mounting: two M3 × 0.5 tapped holes at X35, Y±15 from the underside; keep clear of
  ceiling anchors and spindle recess.
- ENC-100 mounting: six M3 stationary attachment points equally distributed around r96,
  clocked clear of standoffs, anchors, and cable entries after the clamshell split is frozen.
- Hard metal spacers bypass any soft ceiling finish.

Anchor gate: the slots accept nominal M10 or 3/8-inch hardware. Selected candidate (2026-07,
~7× tension margin in cracked concrete): Hilti KB-TZ2 3/8 in stainless at hef 2 in — full
numbers, tether anchor, and the pre-drill verification checklist in
[install.md](install.md). Not released until the slab is verified per that checklist.

## ST-100 carrier standoffs

Three Ø16.0 × 138.0 ±0.10 mm 6061-T6 posts, end squareness 0.05 mm, M6 × 1 tapped at least
12 mm deep at both ends.

- Top: M6 × 16 A4-80 flat-head screws through MP-100, at least 9 mm engagement after countersink.
- Bottom: M6 × 18 A4-80 socket screws through MC-100, approximately 10 mm engagement, with
  locking washers.

## MC-100 stationary motor carrier

- Ø188 × 8.0 mm 6061-T6, clear anodized.
- Motor interface flat within 0.08 mm; runout to axis within 0.08 mm TIR.
- Three Ø6.6 holes on Ø150 PCD at 90°, 210°, 330°.
- Four Ø4.5 holes on Ø60 PCD, clocked from the current GL100 STEP. Counterbore Ø7.5 × 1.5
  from above.
- Center clearance Ø20.5.
- Two Ø8.5 tether holes at X±7, Y−76.
- Two Hall-bracket M3 holes on 12 mm pitch near r63, angle 30°.
- Nominal phase-lead window 20 × 12 R3; final location from the STEP and physical motor.
- Use four M4 × 12 A4-80 screws. The counterbore produces approximately 5.5 mm motor-thread
  engagement against the official 6.0 mm maximum. Verify first.

## SP-100 capture spindle

- One-piece 17-4PH H1150 stainless, passivated.
- Ø16.0 shank; Ø34 × 3.0 upper flange; straightness 0.10 mm; concentricity 0.05 mm TIR.
- Ø16 shank runs from Z3 to the disk shoulder at Z196.7.
- M12 × 1.75 thread from Z196.7 to approximately Z218.
- Ø3.2 cross-hole for a castellated nut and cotter.
- The upper flange sits captive in MP-100. The disk seats on the machined Z196.7 shoulder, so
  the capture gap is not set by loose washers.
- The spindle passes through MC-100, the GL100 bore, and RH-100 without normal contact.

## RH-100 captured rotor hub

- Ø200 × 8.0 mm 6061-T6, flat within 0.08 mm and OD concentric to pilot within 0.05 mm TIR.
- Center hole Ø20.5.
- Four Ø4.5 holes on Ø50 PCD with 90° countersinks from the underside for ISO 10642 M4 × 10
  A4-80 flat-head screws. Install heads 0.1–0.2 mm subflush. Nominal motor engagement is
  2.0 mm, below the official 3.5 mm maximum.
- Top annular pilot protrudes 1.5 mm into the motor bore. Keep pilot ID Ø20.5. Final OD is
  the measured mating diameter minus 0.10–0.20 mm diametrical clearance. Do not release a
  nominal 29.8 mm unverified.
- Three adapter stations at 0°, 120°, 240°. Each station: Ø5.5 through-holes at local
  (r62,y−15), (r62,y+15), (r88,y−15), (r88,y+15); blind Ø5 H7 × 4 deep dowel holes at
  (r66,y0) and (r86,y0), dowels protruding 3 mm.

Tach features:

- One Ø6.10 × 3.15 blind pocket at r68, 30°, for a 6 × 3 mm axially magnetized N52 disk.
- One 14 radial × 8 tangential × 0.8 mm 316 retaining cap, fixed by two radial M2 × 5 screws.
- Identical pocket and cap at r68, 210°, with a brass counterweight (CW-100).
- Match complete retained masses within 0.01 g. Adhesive controls rattle only; it is not
  retention.

## KD-100 catcher disk

- Ø50 × 4.0 mm 316 stainless, Ø13 center hole, R0.5 edge, flat within 0.10 mm.
- Disk top seats at Z196.7, 2.5 ±0.5 mm below RH-100.
- The Ø50 disk edge crosses the Ø50 motor-screw PCD, so the RH-100 screw heads must be
  subflush. Measure the running gap to the lowest rotating screw or surface, not only the
  nominal hub underside.
- Retain with an M12 castellated nut and cotter through SP-100.
- Static proof the complete disk, nut, spindle, and plate path to 1.25 kN.
- There must be no normal-operation witness marks after maximum-speed and imbalance tests.

## BR-100 Hall bracket

- 0.8–1.0 mm 304 stainless Z-bracket with a folded return flange.
- Two 3.4 × 8 mm adjustment slots on 12 mm pitch at MC-100 (±2 mm adjustment).
- DRV5033 sensing face downward at r68 on the 30° line.
- Nominal sensing-face-to-magnet-cap gap 2.5 mm; qualify 1.5–4.0 mm.
- Sensor face is approximately Z182.9; final leg offsets depend on the GL100 wire exit and
  daughterboard footprint.

## BA-10 / BA-12 / BA-14 printed adapters

Three identical adapters per installed pitch set.

- Qualified CF-PPA preferred; CF-PA12 only after equivalent testing.
- **Filament selection (researched 2026-07)**: primary **Bambu Lab PPA-CF** (true PPA + CF;
  168 MPa XY tensile, 208 MPa flexural, HDT 227 °C at 0.45 MPa, ~1.3% moisture saturation —
  about 66% lower than standard PA6-CF). The project printer is a Bambu **X2D**, which
  officially supports PPA-CF: its 300 °C nozzle runs the 280–310 °C band's lower-mid range
  (Bambu's own profile territory), and the 65 °C actively heated chamber directly helps the
  layer-adhesion/Z-strength concern that matters most for these parts. Procedure: dry 100–140 °C / 8–12 h before printing (never above 160 °C),
  print 280–310 °C nozzle / 100–120 °C bed / full enclosure / <100 mm/s on PEI; anneal
  120–140 °C for 6–12 h, but validate annealing on the actual adapter geometry in the
  production orientation first — Bambu warns some geometries warp or lose toughness.
  Backups: 3DXTech CarbonX CF-HTN (more chamber-forgiving) or Siraya Tech Fibreheart PPA-CF
  (easiest to print, lowest strength; confirm its annealing procedure from the TDS). CF-PA12
  only wins if every CF-PPA fails hot/humid conditioning.
- **Why qualification is empirical**: no vendor or literature data exists for year-scale
  creep, 10⁶-cycle fatigue of chopped-fiber filament, or Z-axis (layer-adhesion) strength —
  every TDS reports XY coupons only. Witness coupons must therefore be printed in the actual
  flat-on-hub-base production orientation, and the hot/humid sustained-load conditioning +
  fatigue matrix below is the release evidence, not datasheet numbers.
- Pitch 10°, 12°, or 14°, ±0.25°.
- Approximate radial envelope r52–205.
- Hub base y±25, at least 10 mm thick; the saddle widens to the blade chord and is at least
  12 mm thick.
- At least 8 mm material around holes and R8 minimum base transitions.
- Hub face matches RH-100: four Ø5.5 holes and two Ø5.20 × 3.2 deep dowel sockets.
- Use M5 × 30 A4-80 through-bolts, washers, and all-metal prevailing nuts at the hub.
- Blade saddle centered on Z223.5, with a shallow root stop at r110.
- Four Ø5.5 holes normal to the saddle at r135/r185, y±25. Use M5 × 35 A4-80 bolts and metal
  load spreaders.
- Print flat on the hub base with dried filament, specified annealing, and solid material
  around holes and dowels.

Qualification:

- Condition representative adapters using the filament supplier's hot/humid procedure while
  carrying the calculated sustained service load.
- Run at least 10⁶ combined centrifugal, bending, and torsion cycles at the documented
  maximum service-load envelope.
- Proof every installed adapter to 500 N radial; repeat after environmental and fatigue
  conditioning.
- Destructively test one representative from every material/process batch above 1.0 kN.
- Reject cracking, delamination, pitch change, hole elongation, or permanent set.

## BL-100 wooden blades

Cut and finish four, select three, keep one spare.

- 9 mm Baltic birch plywood, thickness ±0.25 mm, planform ±0.50 mm, holes ±0.15 mm.
- Root r110.0; tip r558.8; exact rotor Ø1117.6 mm / 44.0 in.
- Symmetric chord stations r/chord in mm: 110/115, 180/122, 320/132, 420/128, 500/108,
  558.8/92.
- Curvature-continuous spline, R20 minimum tip corners, approximately R3 symmetric treatment
  on both long edges, at least 4.8 mm edge thickness.
- Four Ø5.5 holes at r135/r185, y±25. Drill in one indexed jig and reseal all hole walls.

## LS-100 load spreaders

Six 65 × 15 × 2 mm 6061-T6 straps, two Ø5.5 holes on 50 mm pitch, R3 corners. Two lie on each
blade upper face and bridge the inner and outer tangential bolt pairs.

## EB-100 PCB bracket and ENC-100 housing

- PCB is 78 × 58 × 1.6 mm and mounts vertically with its 78 mm dimension along Z.
- PCB range Z25–103 in the radial plane Y0, spanning X35–93, component envelope inside
  Y±12.5. The ESP antenna is at the X+93 outward edge.
- PCB mounting holes are (6,6), (72,6), (6,52), (72,52) mm from the board's lower-left.
- Reserve 110 × 80 × 25 mm including connectors and cable bends, with 8 mm service clearance
  beyond power and motor edges.
- EB-100 is a 1.5 mm bent 5052 bracket (or print) fixed to MP-100 at two M3 points and
  supporting the PCB on four M3 standoffs (6–8 mm; holes isolated from circuit ground). Add a
  secondary metal retention lanyard and independent clamps for DC input, phases, Hall cable,
  and programming harness.
- ENC-100 is a white two-part clamshell: Ø212 top, taper to Ø200 over 25 mm, Ø194 minimum
  inside, 178 mm tall, 3 mm walls and ribs, six M3 closure screws, and six M3 top tabs fixed
  to MP-100, three per half.
- Use UL94 V-0 polymer or qualify an equivalent enclosure fire test. Each clamshell half also
  gets an independent flexible metal lanyard rated at least 100 N to MP-100.
- Provide at least 1200 mm² combined free vent area, a 14 × 8 mm cable notch, connector
  access, and an RF window (nonmetallic, ≥15 mm spatial clearance to the antenna).
- Housing ends at Z178, leaving 8.2 mm to the rotating hub. Nothing projects below Z200.

## Tether and design loads

- Separate anchor below the MP-100 tether clearance.
- Complete tether path rated at least 4.5 kN with 15–20 mm slack.
- Lower thimble and rated fitting engage both MC-100 Ø8.5 holes.
- The tether retains carrier, motor, hub, rotor, and housing if the plate or all standoffs
  fail. It must not terminate only on MP-100.
- Ceiling design envelope: 1.25 kN vertical, 0.30 kN lateral, 60 N·m overturning, 8 N·m
  reaction torque.
- Credible controller-bypass runaway/load case: 250 RPM.
- Guarded rotor proof: 216 RPM, two minutes per direction. Do not conduct this test over the
  bed. Use an external guarded drive; if the installed drive must be used, a written
  two-person temporary-limit-bypass procedure is required, followed by restoration and
  independent re-verification of the 180/200 RPM limits before the rotor leaves the fixture.
- Calculate catcher and tether impact energy from the final retained mass and measured slack.
  Perform guarded off-ceiling dynamic catch tests on the complete catcher and tether
  assemblies, including all fittings and carrier attachments; static ratings alone are not
  release evidence.

## Fastener release practice

- Motor M4 torque remains a release gate until thread material, measured engagement, and
  CubeMars' allowable installation torque are known. Use a calibrated torque driver,
  compatible removable threadlocker, and witness marks.
- ST-100 M6 joints use the joint-analysis torque recorded on the drawing plus compatible
  wedge-locking washers. Do not infer torque from a generic stainless table without checking
  aluminum thread bearing stress.
- Replace cotters, prevailing nuts, distorted lock washers, and any one-time locking hardware
  after removal. Record all critical-joint torque and witness-mark inspection during
  commissioning.

## Final tolerance targets

| Target | Value |
|---|---|
| Ceiling to highest blade | 203.2–207.6 mm |
| Lowest component | ≤ Z254 |
| Housing-to-rotating-hub axial clearance | ≥8.0 mm |
| Hub-to-catcher axial gap | 2.5 ±0.5 mm |
| Lowest rotating screw/surface to catcher | ≥2.0 mm at worst tolerance |
| Spindle-to-hub radial gap | 2.25 mm nominal per side |
| Other stationary bracket-to-rotor clearance | ≥2.0 mm (except the Hall gap) |
| Hall gap | 2.5 mm nominal, qualified 1.5–4.0 mm |
| Hub OD assembled runout | ≤0.10 mm TIR |
| Blade-tip radial mismatch | ≤0.5 mm before balancing |
| Adapter pitch mismatch | ≤0.25° |
| Selected blade mass mismatch | ≤0.5 g target |
| Selected blade first-moment mismatch | ≤0.5% target |
| Magnet/counterweight installed mass mismatch | ≤0.01 g |

## Fabricated-part register

| ID | Qty | Part | Baseline | Process |
|---|---:|---|---|---|
| MP-100 | 1 | Ceiling plate | Ø210 × 6, 304 SS | Laser/waterjet + machine |
| ST-100 | 3 | Carrier standoff | Ø16 × 138, 6061-T6 | Turn + tap M6 |
| MC-100 | 1 | Motor carrier | Ø188 × 8, 6061-T6 | CNC mill |
| SP-100 | 1 | Capture spindle | Ø16 flanged, 17-4PH | CNC turn + cross-drill |
| RH-100 | 1 | Rotor hub | Ø200 × 8, 6061-T6 | CNC mill/turn |
| KD-100 | 1 | Catcher disk | Ø50 × 4, 316 SS | Laser + machine |
| BR-100 | 1 | Hall bracket | 0.8–1.0 mm 304 SS | Laser + bend |
| MR-100 | 2 | Magnet / counterweight cap | 14 × 8 × 0.8, 316 SS | Laser |
| CW-100 | 1 | Matched counterweight | Brass, mass-trimmed | Turn + trim |
| BA-10/12/14 | 3/set | Blade adapter | CF-PPA, 10°/12°/14° | Qualified print |
| BL-100 | 4 | Wood blade | 9 mm Baltic birch | CNC router |
| LS-100 | 6 | Load spreader | 65 × 15 × 2, 6061 | Laser/waterjet |
| EB-100 | 1 | PCB bracket | 1.5 mm 5052 or print | Bend or print |
| ENC-100 | 1 pair | Housing clamshell | White PC/FR polymer | Print |

## Fabrication gates

Do not release motor-dependent metal until:

- The purchased motor matches the current Ø106.8 × 34.2 geometry.
- The current STEP is imported.
- Rotating and stationary faces are identified.
- Front and rear M4 depths are measured.
- Bore diameters and bore ownership are established.
- The pilot diameter is derived from the physical motor.
- The phase-wire exit is located.
- Bearing ratings are obtained or accepted as documented residual risk.
- PCB connector and heat-management geometry are frozen.
- Hall sensing is validated with the actual motor, magnet, cap, and bracket.
- Concrete and anchor conditions are established.
