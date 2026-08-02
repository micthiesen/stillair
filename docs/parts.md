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

> **Status 2026-08-01 (motor in hand)**: current revision **confirmed** (Ø106.8 × 34.2;
> axial length measured 34.2–34.3 across clockings). Face ownership **confirmed**: Ø50/M4
> rotates (output face), Ø60/M4 and Ø100/M2.5 are stationary, and the bore surface rotates
> with the Ø50 face — so the RH-100 pilot mates a rotating surface, as the catcher's
> clean-drop assumption requires. Owner decision (2026-08-01): with the revision confirmed,
> STEP-derived geometry (hole positions, PCDs, wire-exit location) is trusted as-is and
> thread depths are verified at assembly rather than pre-measured — bench measurement is
> reserved for dimensions feeding non-adjustable machined features (KD-100 thickness →
> SP-100 cross-hole; pilot bore ID → RH-100 pilot OD, owner's call).

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

**Status: sent to info@cubemars.com on 2026-07-27** (the question list below, plus written
confirmation of the M4 face ownership/thread depths and allowable M4 installation torque).
Awaiting reply.

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

> **Status: ORDERED 2026-07-27** (JLCCNC, SUS304, brushed, qty 1, ~$130). Rev A files are
> [`cad/MP-100_revA.step`](../cad/MP-100_revA.step) and
> [`cad/MP-100_revA.pdf`](../cad/MP-100_revA.pdf) — the first custom part committed to metal.
> Any change from here is a rev B, not an edit.

- Ø210 × 6.0 mm 304 stainless disk, flat within 0.30 mm, brushed and passivated.
  **Passivation is not on JLCCNC's finish list for 304** — the ordered part is brushed only.
  304 self-passivates in air; do it with a citric-acid kit if the spec is to be met literally.
- Two 11 × 20 mm radial anchor slots centered at X±65, Y0 (130 mm anchor centers).
- Three Ø6.6 standoff holes on Ø150 PCD at 90°, 210°, 330°, countersunk from the ceiling face
  for M6 flat-head screws.
- Center spindle opening Ø16.2; top-face flange recess Ø34.2 × 3.1 deep, cut as a **double-D
  pocket**: two parallel flats **30.4 mm across** (+0.3/−0.0), normal to Y, giving 0.2–0.35 mm
  clearance per side on SP-100's 30.0 mm flats (band widened 2026-07-27 from +0.1/+0.2 so the
  feature lands inside a shop's standard ±0.1 and needs no tight-tolerance surcharge; even at
  the loose end the rotational slack is ~1.3°, irrelevant for anti-rotation). This keys the spindle against rotation so the
  M12 castellated nut can be torqued from below with no counter-hold (2026-07-27).
- Separate tether-anchor clearance at X0, Y−82: 14 × 22 mm.
- Cable entry: **none in the plate** (the 12 × 20 mm slot was deleted 2026-07-27 — see
  "Cable entry" below). Instead, two M4 × 0.7 tapped holes on 20 mm pitch in the underside
  at r88, straddling the **15°** line, for a P-clip strain relief.
- EB-100 mounting: two M3 × 0.5 tapped holes at X35, Y±15 from the underside; keep clear of
  ceiling anchors and spindle recess.
- ENC-100 mounting: six M3 tapped holes at r96, **clocked 45°/105°/165°/225°/285°/345°**
  (locked 2026-07-27; see "ENC-100 tab clocking" below for the margin table and the rejected
  alternatives).
- **All ten underside taps are M3 × 0.5, blind: 3.5 mm thread depth, 5.0 mm drill depth**,
  leaving a 1.0 mm floor in the 6.0 mm plate (specified 2026-07-27; thread cut from 4.0 mm
  and the cable pair from M4 on 2026-07-27 to satisfy JLCCNC's blind-tap DFM rule, which
  wants ≥ half the nominal diameter left unthreaded at the bottom — 3.5 + 1.5 in a 5.0 drill
  meets it exactly for M3, where M4 would not). None break through — a through-tapped hole
  lets an over-length screw protrude into the ceiling seating interface. One tap size across
  all ten holes is also one tool and one setup.
  Cable-clamp tap centres in Cartesian, for CAD: **(87.03, 13.01)** and **(81.88, 32.25)**.
- Hard metal spacers bypass any soft ceiling finish.

Anchor gate: the slots accept nominal M10 or 3/8-inch hardware. Selected candidate (2026-07,
~7× tension margin in cracked concrete): Hilti KB-TZ2 3/8 in stainless at hef 2 in — full
numbers, tether anchor, and the pre-drill verification checklist in
[install.md](install.md). Not released until the slab is verified per that checklist.

## ST-100 carrier standoffs

> **Status: ORDERED 2026-07-28** (JLCCNC, 6061-T6 clear anodized, qty 4, $101.79). Rev A
> files are [`cad/ST-100_revA.step`](../cad/ST-100_revA.step) and
> [`cad/ST-100_revA.pdf`](../cad/ST-100_revA.pdf). Any change from here is a rev B.

Three Ø16.0 × 62.0 ±0.10 mm 6061-T6 posts, end squareness 0.05 mm, M6 × 1 tapped at least
12 mm deep at both ends. (Shortened from 138.0 in the 2026-07-27/28 rotor raise — see
[mechanical.md](mechanical.md) > Envelope; the vertical-PCB assumption that sized the 138
moved with it, see [electrical.md](electrical.md).)

> **No off-the-shelf substitute exists (searched 2026-07-28)**: every configurable catalog
> standoff line caps below 62 mm — MISUMI tapped spacers hard-cap at 50 mm (and offer 2017,
> not 6061), McMaster's only aluminum M6 female-female standoff is 52 mm hex, Accu's
> threaded-spacer catalog has no aluminum at all. Stays CNC; a simple lathe part anyway.

- Top: M6 × 16 A4-80 flat-head screws through MP-100, at least 9 mm engagement after countersink.
- Bottom: **M6 × 20** A4-80 socket screws through MC-100 with wedge-locking washers
  (lengthened from M6 × 18 in the 2026-07 review: socket length is measured under the head,
  and a wedge-lock *pair* is ~3.5 mm, leaving only ~6.5 mm engagement at 18 mm — below the
  1.5×D guideline for aluminum threads; 20 mm restores ~8.5 mm with the pair, which is
  **accepted at 1.4×D** given the tiny joint loads and the joint-analysis torque, with the
  actual washer-stack thickness stated on the drawing; washer stacks ≤3 mm reach the full
  9 mm guideline).

Fabrication callouts (pre-order check 2026-07-28):

- **Tap drill Ø5.0 × 15.5 mm deep, thread M6 × 1 − 6H × 12.0 mm min, both ends.** The
  15.5 drill satisfies JLCCNC's blind-tap DFM rule (≥ 0.5 × nominal Ø unthreaded below the
  thread: 12 + 3 = 15 min). Two 15.5 drills in a 62 part leave a 31 mm solid web — no
  break-through risk.
- Screw-bottoming check passes with margin: worst protrusion into the tap is ~10 mm (top
  M6 × 16 flat-head through the countersunk 6 mm plate; bottom M6 × 20 through 8 mm MC-100
  plus the wedge-lock pair) against 12 mm of thread.
- Thread-entry chamfer 0.5 × 45°; break all edges.
- The 62.0 ±0.10 length and 0.05 end squareness are tighter than ISO 2768-mK, so they are
  drawing/remark callouts — and per the MP-100 precedent JLCCNC treats those as advisory,
  not contractual. Both are natural lathe outcomes (three parts faced in one setup match
  closely); **verify on arrival with calipers and a square before mounting**, as with the
  MP-100 flatness check.
- Tap concentricity to the OD is deliberately uncontrolled — the joint locates through the
  Ø6.6 clearance holes in both plates, which absorb ordinary drill wander.
- Qty: 3 required; order 4–5 (turned-part marginal cost is small and a dropped or
  cross-threaded spare otherwise costs a full shipping cycle).

## MC-100 stationary motor carrier

- Ø180 × 8.0 mm 6061-T6, clear anodized (OD trimmed 188 → 180, 2026-07-28 owner tweak in
  OnShape; rim past the Ø16 standoff posts is 7 mm, tether-hole edge margin ~9.7 mm, ENC-100
  internal clearance improves).
- Motor interface flat within 0.08 mm; runout to axis within 0.08 mm TIR.
- Three Ø6.6 holes on Ø150 PCD at 90°, 210°, 330°.
- Four Ø4.5 holes on Ø60 PCD, clocked from the current GL100 STEP. Counterbore Ø7.5 × 1.5
  from above.
- Center clearance Ø20.5.
- Two Ø8.5 tether holes at X±7, Y−76.
- Two Hall-bracket M3 × 0.5 tapped through holes (no counterbore/countersink — heads bear
  on BR-100's slotted feet) on 12 mm pitch at r71, on the **150° line — the bisector
  between two adjacent ST-100 standoff holes** (owner move 2026-08-01, from 30°: the
  sensor angle is free since the magnet sweeps the full r76 circle; clearances unchanged —
  60° to each adjacent standoff bolt head, 15° min to the nearest ENC-100 tab, ~74° to the
  phase window. Angular labels are frame-ambiguous across model sketches — the controlling
  definition is the standoff-bisector, not the number).
- Nominal phase-lead window 20 × 12 R3; final location from the STEP and physical motor.
- Use four M4 × 12 A4-80 screws. The counterbore produces approximately 5.5 mm motor-thread
  engagement against the official 6.0 mm maximum. Verify first.

## SP-100 capture spindle

- One-piece 17-4PH H1150 stainless, passivated.
- Ø16.0 shank; Ø34 × 3.0 upper flange; straightness 0.10 mm; concentricity 0.05 mm TIR.
- Ø16 shank runs from Z3 to the disk shoulder at Z120.7.
- M12 × 1.75 thread from Z120.7 to **Z142.0** (21.3 mm long), with the runout inside the
  Z120.7 shoulder. (A same-day 2026-07-28 excursion to Z144.0 for a 6 mm Amazon washer was
  reverted when the DIN 440 4 mm washer was selected instead.)
- **Ø3.2 cotter cross-hole, centreline at Z136.6** (**set 2026-08-01 from the measured
  washer: t = 3.38 → Z = 3.38 + 133.2 = 136.58, drawn as 136.6**; supersedes the 4.0-nominal
  Z137.2), perpendicular to the flange flats.
- (All Z values shifted −76 total in the 2026-07-27/28 rotor raise with the shortened
  ST-100; the bottom-end geometry is unchanged relative to the hub. In OnShape these dims
  are driven by `#hubBottom` expressions.)

### SP-100 bottom-end stack (derived 2026-07-27)

Both dimensions above were previously "approximately Z218" and an unlocated Ø3.2 hole, so
the part could not be drawn. They derive from the retaining nut, fixed here as a **DIN 935
M12 A4 castellated nut** (s 19.0, total height m 15.0, unslotted height m′ 10.0, six 3.2 mm
slots) with an **ISO 1234 3.2 × 32 A4 split pin** (trim legs to suit). The nut installs
bearing-face-up against KD-100, castellated crown downward.

| Z, mm | Feature |
|---:|---|
| 120.7 | Ø16→M12 shoulder; thread starts. KD-100 clamps up against this face |
| 120.7–124.7 | KD-100, 4.0 mm nominal (DIN 440 band 3.4–4.6), its Ø13.5 bore over the thread |
| 124.7 | Nut bearing face |
| 124.7–134.7 | Nut unslotted body (m′ = 10.0) |
| 134.7–139.7 | Castellated crown, 5.0 mm of slot depth |
| **137.2** | **Cotter cross-hole centreline** (nominal at t = 4.0; **machine at Z136.6 per measured t = 3.38**) — mid-band |
| 142.0 | Thread ends, 2.3 mm (>1 pitch) below the crown |

- The hole is centred in the 5.0 mm slot band so the cotter has material both sides. The
  DIN 440 washer's ±0.6 thickness band would eat the 0.9 mm margins at its extremes, so
  the cross-hole Z is **set from the measured washer thickness** (Z = t + 133.2) before
  SP-100 is machined — with a measured t, the remaining stack tolerance (shoulder position,
  nut m′) is back to ~±0.2 and the hole stays comfortably inside the band.
  **Measured 2026-08-01: t = 3.38 mm → Z136.6** (slot band 134.08–139.08 at that t; the
  hole is dead-center with 2.5 mm both sides). Single washer measured; the three are one
  stamping batch, so siblings track within a few hundredths — any of them installs. Thread
  end stays Z142.0 (now 2.9 mm past the crown; more margin, not less).
- Six castellations on a 1.75 mm pitch give **0.292 mm of axial adjustment per index step**,
  so worst-case seating error after aligning a slot is 0.146 mm. Rotate the *nut* to find
  alignment; the spindle is keyed and does not turn.
- Cross-hole clocking is set perpendicular to the flange flats so the drawing is
  deterministic; nothing depends on it (a castellated nut aligns to any hole angle).
- Ø3.2 through a Ø12 thread leaves 4.4 mm of material each side. The nut hangs at r ≤ 11 in
  free space — RH-100 ends at Z118.2 above it, and the blade roots start at r52.
- **Anti-rotation (dimensioned 2026-07-27; supersedes the 2026-07 review's wrench-flat
  note)**: two parallel flats on the flange OD, **30.0 mm across flats** (−0.1/−0.2),
  symmetric about the axis, cut through the full 3.0 mm flange thickness, flat faces normal
  to Y. Flat depth 2.0 mm per side, chord width 16.0 mm; break the flat/OD corners.
  MP-100's recess is a **matching double-D pocket** (see MP-100 above), so the plate keys
  the spindle against rotation permanently and **no counter-hold is required** when torquing
  the M12 nut. 30.0 mm is a standard wrench size, so the flats still take a wrench on the
  bench.
- Why keyed rather than wrenched: the flange is bench-assembled into a recess that opens
  toward the ceiling, but the castellated nut goes on at install step 4, *after* the plate is
  anchored — by then the flange is sandwiched against the slab and unreachable, and the only
  exposed shank is the 2.5 mm capture gap. Wrench flats alone would have solved the bench
  case and left the real one unsolved.
- Load check (both trivial, recorded so the flats are not re-litigated): flats cost 6% of the
  flange bearing annulus (701.7 → 658.5 mm², **1.9 MPa** at the 1.25 kN static proof); the
  flat/pocket interface sees **13.9 MPa** reacting 20 N·m of nut torque across 2 × 48 mm².
- Bench note: before ceiling install, nothing retains the spindle axially in the recess — use
  a simple holding fixture (recess-up, spindle hanging through a hole) when handling.
- The upper flange sits captive in MP-100 (the Ø34.2→Ø16.2 bore step is a real internal
  shoulder — retention is self-contained in the plate, not ceiling-dependent). The disk
  seats on the machined Z120.7 shoulder, so the capture gap is not set by loose washers.
- The spindle passes through MC-100, the GL100 bore, and RH-100 without normal contact.

## RH-100 captured rotor hub

- Ø200 × 8.0 mm 6061-T6, flat within 0.08 mm and OD concentric to pilot within 0.05 mm TIR.
- **Restyled 2026-07-28 (owner, in OnShape)**: no longer a full disk — a three-arm spoke
  plate, arms on the 0/120/240 station lines out to r100 with sculpted concave waists
  between. All interfaces unchanged (center bore, Ø50 PCD, pilot, stations); final outline
  lives in the OnShape model and exports at drawing release (the restyle prompted moving
  the tach stations onto the arms — see "Tach features"); flatness/TIR specs apply to what
  remains.
- Center hole Ø20.5.
- Four Ø4.5 holes on Ø50 PCD with 90° countersinks from the underside for ISO 10642 M4 × 10
  A4-80 flat-head screws. Install heads 0.1–0.2 mm subflush. Nominal motor engagement is
  2.0 mm, below the official 3.5 mm maximum.
- Top annular pilot protrudes 1.5 mm into the motor bore. Keep pilot ID Ø20.5. Final OD is
  the measured mating diameter minus 0.10–0.20 mm diametrical clearance. **Released
  2026-08-01: bore measured Ø29.99–30.00 → pilot OD Ø29.85 (band 29.80–29.90).**
- Three blade-root stations at 0°, 120°, 240°. Each station: Ø5.5 through-holes at local
  (r62,y−15), (r62,y+15), (r88,y−15), (r88,y+15); blind Ø5 H7 × 4 deep dowel holes at
  (r66,y0) and (r86,y0). **v3 (2026-07-28): the BP-100 blade bolts here directly** — its
  printed Ø5 pins engage the dowel holes (steel dowels deleted), M5 bolts from above into
  nut pockets in the blade root.

Tach features:

- **Three identical stations, one per arm (moved 2026-07-28)**: **Ø6.45 × 3.35** blind
  pockets in the top face at **r76 on the three arm/station centerlines** (0/120/240).
  (Resized 2026-07-28 from Ø6.10 × 3.15 for the purchased imperial magnet — Ø6.35 × 3.18,
  1/4 × 1/8 in; metric 6 × 3 N52 proved uneconomic to source in Canada.) The
  spoke restyle removed material at the old 30°/210° waist positions, and an
  opposite-the-magnet counterweight can never sit on an arm — so instead one station holds
  the Ø6.35 × 3.18 axially magnetized N52 disk and the other two hold brass slugs trimmed to
  the same installed mass: three equal masses at 120° spacing balance by symmetry, and the
  Hall still sees exactly one magnet per revolution (brass is non-magnetic). r76 centers
  between the r66/r86 dowel holes on the arm centerline (10 mm clear of each).
- Each station: a 14 radial × 8 tangential × 0.8 mm 316 retaining cap (MR-100 ×3), fixed by
  **two axial M2 × 5 screws through the cap's radial-end ears into tapped holes in the hub
  top face** (reworded 2026-07 review: "radial" describes the ear positions, not the screw
  axis).
- **CW slugs are not same-size copies**: a same-size brass copy is ~13% heavier than the
  magnet (brass 8.5 vs NdFeB ~7.5 g/cm³); trim to ~Ø6.35 × 2.8 mm to match (cut from
  1/4 in rod), and confirm the resulting ~0.55 mm bondline gap
  under the slug-side caps is within the adhesive's rated thickness (non-structural).
- Match complete retained masses within 0.01 g across all three stations. Adhesive controls
  rattle only; it is not retention.

## KD-100 catcher disk

- **Purchased part (final selection 2026-07-28)**: **Accu HDW-M12-A4** — DIN 440 washer,
  A4, **Ø44 OD × Ø13.5 ID × 4.0 nominal** (DIN 440 thickness band 3.4–4.6), stamped, ~$7
  each, qty 3 in the Accu fastener order. Supersedes the same-day Amazon Ø50 × Ø12 × 6
  machined-washer pick (cancelled: the Ø12 bore was a zero-clearance fit on M12 and it
  added a vendor; the Ø13.5 DIN 440 bore clears properly). The 4.0 thickness restores the
  original bottom-end stack derivation (cotter Z137.2, thread end Z142.0).
- **OD 44 vs the original Ø50 spec**: radial engagement over the Ø20.5 hub aperture is
  11.75 mm/side (was 14.75) — still ample, and the mandatory 1.25 kN static proof is the
  release evidence either way. The disk edge (r22) still marginally overlaps the Ø50-PCD
  screw-head annulus, so the RH-100 subflush-head requirement stands.
- **On-arrival checks**: confirm austenitic stainless (barely/non-magnetic), check
  flatness (stamped part, no flatness guarantee — reject visible dish/burr), and **measure
  actual thickness**: the DIN 440 band is wide (±0.6), so set SP-100's cross-hole from the
  measured value (hole Z = measured t + 133.2; 4.0 nominal → Z137.2) before the spindle is
  machined. Washers arrive long before SP-100 is cut, so this costs nothing.
  **Measured 2026-08-01: t = 3.38 mm → cross-hole Z136.6** (recorded in the SP-100 section).
- Disk top seats at Z120.7, 2.5 ±0.5 mm below RH-100.
- The Ø50 disk edge crosses the Ø50 motor-screw PCD, so the RH-100 screw heads must be
  subflush. Measure the running gap to the lowest rotating screw or surface, not only the
  nominal hub underside.
- Retain with a DIN 935 M12 A4 castellated nut and an ISO 1234 3.2 × 32 A4 split pin through
  SP-100's Z137.2 cross-hole; the nut clamps KD-100 up against the Z120.7 shoulder. Full
  stack in "SP-100 bottom-end stack".
- Static proof the complete disk, nut, spindle, and plate path to 1.25 kN.
- There must be no normal-operation witness marks after maximum-speed and imbalance tests.

## BR-100 Hall bracket

- 0.8–1.0 mm 304 stainless Z-bracket with a folded return flange.
- Two 3.4 × 8 mm adjustment slots on 12 mm pitch at MC-100 (±2 mm adjustment).
- DRV5033 sensing face downward at **r76** on the **150° line** (owner move 2026-08-01,
  from 30° — see the MC-100 Hall-bracket holes: the controlling definition is the bisector
  between two adjacent ST-100 standoff holes; the magnet sweeps the full r76 circle so any
  angle senses).
- Nominal sensing-face-to-magnet-cap gap 2.5 mm; qualify 1.5–4.0 mm.
- Sensor face is approximately Z106.9 (hub top Z110.2 − 0.8 mm cap − 2.5 mm gap;
  re-derive exactly when BR-100 is drawn); final leg offsets depend on the GL100 wire
  exit and daughterboard footprint.
- PCB-02 datum facts (board captured/placed 2026-07-30, see electrical.md): the Hall
  element sits 4.5 mm from H1 along the M2 hole centerline (holes 6 mm apart, Ø2.2,
  board 24 × 8 mm) with zero cross-axis offset; the gap spec is measured to the SOT-23's
  outer face. The JST connector at the outer end is the tallest rotor-facing feature
  (~4.5 mm) and its housing/cable extend past the board edge — the bracket provides all
  cable strain relief and must clear J1's height, not just the sensor's.

## Blade root-joint qualification (BA-00 deleted)

> **No adapter exists anymore.** BA-00 (designed 2026-07-27) was deleted 2026-07-28 when
> BP-100 v3 integrated the mounting plate into the blade print ([blade-v2.md](blade-v2.md)):
> the blade root rectangle bolts straight to RH-100's stations with four M5 into nut pockets
> in the root, and printed Ø5 pins engage the hub's dowel holes. What survives here is the
> material research and the qualification program, retargeted at the **blade root print
> (segA)** — read "adapter" below as "blade root". Loads are small (blade centrifugal ~15 N
> at 170 RPM plus gravity moment); pins take shear, bolts clamp, no printed thread carries
> load. Filament for the loaded root is the owner's call (the aero/LW-PLA blade body vs the
> qualified CF-PPA below — segA material selection is part of the strength program).

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

> **Superseded 2026-07-27 by the BP-100 printed blade with CF-rod spar — see
> [blade-v2.md](blade-v2.md) (accepted, modelled in OnShape).** BL-100, LS-100, and the
> BA pitch family are all superseded (the BA family collapsed to BA-00, then BA-00 itself
> was deleted 2026-07-28 — v3 blades bolt directly to RH-100); RH-100 is unaffected. This
> section is retained as the fallback design.

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

- PCB is 78 × 58 × 1.6 mm, **mounted horizontally under the plate** (~Z12–35): the
  2026-07-27/28 raise leaves a 62 mm interior (Z6–Z68), which kills both vertical
  orientations (78-along-Z needed 97; 58-along-Z needed 77+). EB-100 becomes a horizontal
  bracket/standoff arrangement off the same MP-100 taps — redesign details at bracket
  design time. See [electrical.md](electrical.md) > PCB-01 mechanical definition.
- PCB mounting holes are (6,6), (72,6), (6,52), (72,52) mm from the board's lower-left.
- Reserve 110 × 80 × 25 mm including connectors and cable bends, with 8 mm service clearance
  beyond power and motor edges.
- EB-100 is a 1.5 mm bent 5052 bracket (or print) fixed to MP-100 at two M3 points and
  supporting the PCB on four M3 standoffs (6–8 mm; holes isolated from circuit ground). Add a
  secondary metal retention lanyard and independent clamps for DC input, phases, Hall cable,
  and programming harness.
- ENC-100 is a white two-part clamshell: Ø212 top, taper to Ø200 over 25 mm, Ø194 minimum
  inside, **~124 mm tall (was 178; re-derive against the shortened stack when designed —
  deferred anyway)**, 3 mm walls and ribs, six M3 closure screws, and six M3 top tabs fixed
  to MP-100, three per half.
- **Split plane locked (2026-07-27): the 135°–315° axis.** The removable half spans
  315°→135° and carries tabs 345/45/105; the fixed half spans 135°→315° with tabs
  165/225/285. Dropping the removable half exposes the whole PCB (vertical in the Y0 plane,
  X35–93) face-on without disturbing the tether run at 270°. Rejected: 15°/195° puts the
  seam coplanar with the PCB so the board straddles it; 75°/255° passes within 15° of both
  the 90° standoff and the tether. The ENC-100 cable notch must sit entirely within one
  half, never on the seam — satisfied by the 15° cable entry, 60° clear of the 315° seam.
- Use UL94 V-0 polymer or qualify an equivalent enclosure fire test. Each clamshell half also
  gets an independent flexible metal lanyard rated at least 100 N to MP-100.
- Provide at least 1200 mm² combined free vent area, connector access, and an RF window
  (nonmetallic, ≥15 mm spatial clearance to the antenna).
- Cable notch: 14 × 8 mm on the **15°** line, **open at the top rim** (not a closed hole) so
  the removable half separates from a cable clamped to MP-100. See "Cable entry" above.
- Housing bottom clearance must be re-derived at design time; the fixed numbers from the
  138 mm stack (end Z178 / nothing below Z200) are void. **New constraint from the raise:
  blade tops at Z115.2 sweep r ≥ 110 while the housing wall sits at r ≤ 106 — only ~4 mm
  radial gap in the band where they overlap in height. The housing likely must end above
  ~Z112 at full diameter or taper inward below it.**

## Tether and design loads

- Separate anchor below the MP-100 tether clearance.
- Complete tether path rated **at least the calculated dynamic catch peak with ≥2× margin**,
  15–20 mm slack. Provenance note (2026-07): the earlier "≥4.5 kN" was a dossier default,
  not a derived requirement — first-principles for the ~4–5 kg retained mass over 20 mm on
  a stiff cable path gives a peak on the order of 1–2 kN (stiffness-dominated; compute from
  measured slack and validate with the mandated dynamic catch test). 4.5 kN remains a
  reasonable free floor for the cable/fittings (1/8 in 7×19 breaks at ~7.6 kN); the anchor
  is sized against the calculated peak.
- Lower thimble and rated fitting engage both MC-100 Ø8.5 holes.
- The tether retains carrier, motor, hub, rotor, and housing if the plate or all standoffs
  fail. It must not terminate only on MP-100.
- Ceiling design envelope: 1.25 kN vertical, 0.30 kN lateral, 60 N·m overturning, 8 N·m
  reaction torque.
- Credible controller-bypass runaway/load case: **270 RPM** (raised from 250 in the 2026-07
  review: the 60 W supply bounds terminal runaway at ~260–270 RPM via the N³ aero-power
  law, and the analog trip only guarantees lock by ~245 RPM for bounded ramps — see
  electrical.md's two-tier trip claim).
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

## Fabrication defaults (2026-07 review — a fabricator will ask)

- Default tolerance block: **ISO 2768-mK** for all dimensions not individually toleranced.
- Internal corner radii on MP-100's anchor slots and tether clearance: **R2
  minimum** (laser/waterjet cannot cut sharp internal corners; LS-100/BL-100 already
  specify theirs). The tether clearance slot's 14 mm dimension is **radial**, 22 mm
  tangential.
- Surface finish where not stated (ST-100, RH-100, SP-100, KD-100): machined finish
  acceptable; add anodize/passivation callouts at drawing release if desired.
- The former "housing ends at Z178 / nothing below Z200" rule is void after the 2026-07-27
  raise; the ENC-100 bottom limit is re-derived at housing design time (see the blade-top
  radial-gap constraint in the ENC-100 section).
- **MP-100 is released for fabrication as of 2026-07-27.** Both former blockers are gone:
  ENC-100 tab clocking is locked below, and the cable-slot angle dissolved once the supply
  was confirmed as a surface run (see "Cable entry").

### Cable entry (locked 2026-07-27)

Site fact: power reaches the fan as a **surface run** along the ceiling from the wall, not
from a junction box above. That kills the mid-plate slot. MP-100's top face is clamped
against the ceiling through a ~2.5 mm hard spacer, so no cable can reach a closed slot from
above; the cable must pass the assembly at the outer rim, where the ENC-100 top edge
(Ø212, r106) already carries its 14 × 8 mm notch.

What the plate needs at that angle is **strain relief, not a hole**. The mains cable is
clamped to MP-100 (permanent structure) via a P-clip on two M4 tapped holes; ENC-100's notch
is clearance only. Clamping to the housing instead would put live wiring under load every
time a clamshell half is dropped for service.

**Angle: 15°**, with ENC-100's notch on the same line. Chosen for internal cleanliness, since
free plate rotation means the whole feature pattern is clocked toward the conduit at install
(the angle is an orientation choice on the ceiling, not a machining input):

- 15° is the centre of the 345°/45° tab gap and the nearest clean window to J1 at the PCB's
  top edge — a ~26 mm lateral run off the Y0 plane.
- Clearance to the nearest anchor washer is ~21 mm at worst-case ±5 mm drill error.
- Rejected: **135°** is geometrically cleanest but sits on the clamshell seam; **255°** comes
  within 12.8 mm of the tether slot; **75°/315°** give ~19.5 mm and sit further from J1.

The notch falls in the removable clamshell half (315°→135°). That is fine **provided the
ENC-100 notch stays open at the top rim** — the half then separates radially from a cable
that remains clamped to the plate. A closed hole here would trap the cable and is a defect.

### ENC-100 tab clocking (locked 2026-07-27)

Six M3 tapped holes at r96, clocked **45/105/165/225/285/345°**. Verified clearances,
measured from the M3 hole edge (Ø3.4) to the nearest feature:

| Keepout | Governing pair | Clearance |
|---|---|---|
| ST-100 standoff (Ø16 post at r75) | tab 105° vs standoff 90° | 20.8 mm |
| Anchor washer (1 in OD, worst ±5 mm drill error) | tab 345° vs anchor at X+65 | ~19 mm |
| Tether clearance slot (14 radial × 22 tangential at X0, Y−82) | tab 285° vs slot corner (11, −89) | **12.6 mm** |

12.6 mm is the controlling number, not the ≥20 mm this doc previously claimed — the earlier
figure checked the standoffs and anchors but not the tether slot. It is still ample in 6 mm
304 plate; recorded so nobody re-derives it or trusts the wrong number.

Rejected alternatives (same r96, same 60° spacing, different phase):

- **30°-family** (30/90/…) — tabs land directly on all three standoffs: ~9 mm.
- **0°-family** (0/60/…) — tab at 0° sits 6.6 mm from the anchor washer.
- **20°-family** — tab at 260° sits 7.9 mm from the tether slot corner.
- **15°-family** — mirrors the 45-family exactly (same 12.6 mm tether minimum); no gain, and
  it does not admit a split plane that clears the PCB as cleanly.

## Fabricated-part register

| ID | Qty | Part | Baseline | Process |
|---|---:|---|---|---|
| MP-100 | 1 | Ceiling plate | Ø210 × 6, 304 SS | Laser/waterjet + machine |
| ST-100 | 3 | Carrier standoff | Ø16 × 62, 6061-T6 | Turn + tap M6 |
| MC-100 | 1 | Motor carrier | Ø180 × 8, 6061-T6 | CNC mill |
| SP-100 | 1 | Capture spindle | Ø16 flanged, 17-4PH | CNC turn + cross-drill |
| RH-100 | 1 | Rotor hub | Ø200 × 8, 6061-T6 | CNC mill/turn |
| KD-100 | 1 | Catcher disk | Ø44 × Ø13.5 × 4, DIN 440 A4 | Purchased (Accu HDW-M12-A4) |
| BR-100 | 1 | Hall bracket | 0.8–1.0 mm 304 SS | Laser + bend |
| MR-100 | 3 | Magnet / slug retaining cap | 14 × 8 × 0.8, 316 SS | Laser |
| CW-100 | 2 | Matched balance slugs | Brass, mass-trimmed | Turn + trim |
| BL-100 | 4 | Wood blade | 9 mm Baltic birch | CNC router |
| LS-100 | 6 | Load spreader | 65 × 15 × 2, 6061 | Laser/waterjet |
| EB-100 | 1 | PCB bracket | 1.5 mm 5052 or print | Bend or print |
| ENC-100 | 1 pair | Housing clamshell | White PC/FR polymer | Print |

## Fabrication gates

Do not release motor-dependent metal until:

- ~~The purchased motor matches the current Ø106.8 × 34.2 geometry~~ — **confirmed
  2026-08-01** on the physical motor.
- ~~The current STEP is imported~~ — done (the OnShape model is built on it).
- ~~Rotating and stationary faces are identified~~ — **confirmed 2026-08-01**: Ø50/M4
  rotates; Ø60/M4 and Ø100/M2.5 stationary.
- ~~Front and rear M4 depths are measured~~ — **waived 2026-08-01 (owner)**: verified at
  assembly instead (a bottoming screw is felt at hand-torque; fix is a washer or shorter
  screw). The subflush-head and engagement notes on MC-100/RH-100 stand as assembly checks.
- ~~Bore ownership~~ — **confirmed 2026-08-01: the bore rotates with the Ø50 face**, so
  the RH-100 pilot register mates only rotating surfaces (2026-07 review: if the
  ~0.1 mm-clearance pilot faced a stationary feature, a bearing failure would bind there
  before the 2.25 mm spindle float is used, defeating the clean-drop assumption behind
  the catcher).
- ~~Axial body-length tolerance measured and capture-gap stack derived~~ — **closed
  2026-08-01**: measured 34.2–34.3 across clockings (+0.1/−0.0 vs nominal). Stack for the
  2.5 ±0.5 mm gap: motor +0.1/−0.0 (measured) + ST-100 ±0.10 + MC-100 ±0.1 + RH-100 ±0.1
  + SP-100 shoulder ±0.1 → worst-case straight sum ~2.0–2.9 mm, inside the 2.0–3.0 band
  (RSS ~2.3–2.7). KD-100 thickness does not enter (the disk seats on the machined Z120.7
  shoulder). Nominal 34.2 stands in the model — no Variable Studio change. The ≥2.0 mm
  screw clearance holds at worst case *only* with the RH-100 heads subflush — that
  requirement stands.
- ~~The pilot diameter is derived from the physical motor~~ — **closed 2026-08-01**:
  rotating bore measured Ø29.99–30.00 → pilot OD released at Ø29.85 (29.80–29.90).
- ~~The phase-wire exit is located~~ — **trusted from the STEP (owner decision
  2026-08-01,** revision confirmed).
- Bearing ratings are obtained or accepted as documented residual risk.
- PCB connector and heat-management geometry are frozen.
- Hall sensing is validated with the actual motor, magnet, cap, and bracket.
- Concrete and anchor conditions are established.
