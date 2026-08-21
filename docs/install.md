# Installation

> **Final integration resumed by explicit owner request on 2026-08-20.** MP-100 installation,
> tether proof, and catcher proof remain accepted complete and must not be reopened. The active
> work is mounting the remaining fan assembly and electronics from below, including permanent
> 24 V, Hall, motor, and service-USB routing for ceiling-mounted loaded commissioning.

Site: 11-storey concrete condo, ceiling slab possibly post-tensioned (treat as PT until
proven otherwise); existing bolts of unknown type in the slab. Anchor engineering basis:
ICC-ES ESR-2713 (Simpson Titen HD), design strengths in cracked concrete at f'c 2500 psi —
the correct conservative assumption for a suspended slab soffit.

**Site status 2026-08-20:** MP-100 is installed on the ceiling (owner report), with all three
ST-100 standoffs and SP-100 spindle in place. The two primary holes and primary plate mount
are complete. `INS-01` is accepted as passed against the documented anchor and spacer stack.
No further anchor, plate, tether, or catcher proof is required.

## Active remaining integration

The next session should guide Michael one physical step at a time. Work from an unpowered
system until every stationary cable is supported and every moving clearance is visible:

1. Preassemble the motor to MC-100 and establish the motor/Hall harness exits before the
   overhead lift.
2. Attach MC-100 to the installed ST-100 standoffs, then install RH-100 and the completed rotor
   using the released fastener stacks in `parts.md`.
3. Complete the already-qualified central capture stack without reopening its proof basis.
4. Mount PCB-01 and PCB-02, connect 24 V, phases, and Hall, then secure each stationary cable
   independently of its connector.
5. Route a quality long USB cable from PCB-01 J6 to an operator position outside the rotor
   sweep. USB is data-only. Strain-relieve it to stationary structure and use an active
   extension only if the passive link proves unreliable.
6. With power still off, inspect full hand-rotation clearance, connector seating, cable reach,
   and strain relief. Then continuity-check the installed harnesses before loaded power-up.

Loaded MPET and tuning follow this installation as a separate commissioning step. The installed
ceiling position is the selected loaded-test location because it provides the final mechanical
support, rotor load, cable lengths, ceiling interaction, and room acoustics. The USB oscilloscope
is optional additional evidence if it arrives in time; its safe hookups are in
[`observability.md`](observability.md).

**Historical tether note:** the original MP-100 clearance at X0, Y-82 was only
sqrt(65^2 + 82^2) = 104.6 mm from either primary center, conflicting with the documented
>=190 mm basis. Michael resolved and tested the final tether arrangement outside the active
project plan. Its location and termination are not managed here.

## Anchor selection

Demand per primary anchor (two on 130 mm centers, from the design envelope of 1.25 kN
vertical / 0.30 kN lateral / 60 N·m overturning / 8 N·m torque): ~1.09 kN tension,
~0.21 kN shear. True sustained dead tension is only ~25–40 N per anchor for a 5–8 kg
assembly. Tether requirement: the calculated dynamic catch peak with ≥2× margin (order
1–2 kN for the ~4–5 kg retained mass over 15–20 mm slack — see parts.md).

- **Primary anchors: 2× Simpson Titen HD 3/8 × 3 in (`THD37300H`)** — design tension
  3.57 kN cracked (pullout-governed) vs 1.09 kN demand = **3.3× margin**; 70 mm drilled
  hole; min slab 102 mm; 130 mm centers clear the 76 mm minimum spacing; reaches full
  embedment through plate + 3 mm spacer with 3.7 mm to spare. Heavy flat washers over the
  11 × 20 mm slots. Install per Simpson's instructions (drill per ESR, socket/impact
  drive — screw anchors have no set torque like wedge anchors).
- **Tether anchor: Titen HD 3/8 × 4 in (`THD37400H`)** — 7.81 kN, covering both load bases
  unconditionally; 89 mm hole; min slab 127 mm. **Simplification path**: if the
  calculated/tested catch peak is ≤ ~1.7 kN, a third `THD37300H` (3.57 kN, ≥2× margin)
  covers it and all three anchors become one part at one 70 mm hole depth. Keep ≥190 mm
  from the primaries; terminate in a forged shoulder eyebolt or rated eye nut (never a
  bent-wire eye); proof-test in place.
- **Service rule**: Titen HDs are torqued once and never fully removed (ESR-2713 §4.3
  permits a one-turn backout only; screw-formed concrete threads are a consumable
  interface). The design already services at the carrier-to-standoff M6 joint from below —
  the anchors and plate stay on the ceiling.
- **Tether termination (historical options)**: a rated pad-eye under the THD37400H head or
  a Titen HD rod-hanger with a forged 3/8-16 shoulder eyebolt were the documented options.
  Final selection and installation are owner-managed.

## Mounting sequence

Titen HDs are through-fixture fasteners — the plate and anchors go up together (the screw
head + washer clamps the plate; there is no set-stud-first step as with wedge anchors):

1. **Bench-assemble everything that needs ceiling-face access**:

   - Put MP-100 ceiling-face-up. Insert SP-100 (the center capture spindle) from that side,
     seat its flange fully in the double-D recess with metal bearing directly on the pocket
     shoulder, and leave the long shank hanging down. It cannot be added after anchoring.
   - Add three tiny, spaced dots of non-corrosive neutral-cure RTV across the ceiling-side
     perimeter seam between the seated flange and MP-100. Do not put silicone under the
     flange or on its structural bearing face. Cure fully in air per the product instructions,
     then tap/shake the unit to confirm there is no metallic click. The RTV is removable
     anti-rattle restraint only; capture loads remain metal-on-metal through the shoulder.
   - Install three ST-100 standoffs with three M6 × 16 A4 flat-head screws inserted from the
     ceiling face. The fourth standoff is a spare. Tighten to the released joint requirement;
     verify each countersunk head is flush or slightly below the ceiling face.
   - Keep the unit ceiling-face-up until the RTV cures; flipping the plate can release
     SP-100 before then. The hard spacers leave clearance above MP-100, so the slab does not
     directly clamp the flange after installation.
   - Do not add MC-100/motor, rotor, catcher nut stack, electronics, cable clamps, or housing
     yet. All remain accessible from below and only make the overhead lift heavier.

2. Mark the two primary drill spots via the plate or the PLA template (the 11 × 20 slots
   absorb ±4–5 mm). Tether work is outside this archived sequence.
   Drill **without the plate** using a 3/8 in carbide bit meeting ANSI B212.15 (bit nominal
   matches the anchor — never substitute a 10 mm metric bit, the thread engagement assumes
   ANSI tolerance), depth-stopped at ~75 mm (primaries) /
   ~95–100 mm (tether), then brush/blow clean per Simpson's instructions. Tooling: M12 Fuel
   hammer drill (3404) in hammer mode with a **straight-shank** ANSI B212.15 carbide
   percussion bit — Makita B-68812 3/8 × 6 in (verify ANSI marking and ≥100 mm flute length
   on arrival). This is the straight-shank option for the 3404's 3-jaw chuck. If renting an
   SDS-plus rotary hammer instead, use an ANSI B212.15 SDS-plus bit; SDS bits do not fit the
   3404. Expect slow going in tower slab:
   peck-drill to clear dust and cool the tip; if a hole barely progresses, rent an SDS-plus
   rotary hammer instead of forcing it. The M12 impact driver (no axial percussion — cannot
   drill) **drives** the anchors via a 9/16 in socket.
3. Offer up the plate unit. At each primary location, place the loose hard-spacer washer
   between MP-100 and the ceiling, then drive the Titen HD through its room-side washer and
   plate slot (stack: head -> washer -> plate -> hard spacer -> ceiling). The spacers are
   added during the lift, not attached during bench assembly.
   **Length/stack budget**: the 3 in screws have 12.7 mm of fixture budget above the
   63.5 mm minimum embedment — plate 6 mm leaves ≤6.7 mm for washer + spacers combined.
   Use standard-thickness washers (~2.5 mm) and only as much spacer as the finish demands
   (≤~4 mm); if more shimming is needed, step up to a 3-1/2 in screw rather than thinning
   the embedment. Hardware: Prime-Line 9080006 USS 3/8 × 1 in OD zinc washers — one under
   each head, one as the hard spacer per anchor (2.5 mm covers the ~1–2 mm ceiling texture
   plus any slightly-proud countersunk M6 heads on the plate's ceiling face); stack =
   11 mm of the 12.7 mm budget. Drill ~75 mm for the primaries, ~95–100 mm for the 4 in
   tether ("too deep" costs nothing; too-shallow driving stalls the screw proud of the
   plate).
4. Stack from below: carrier (motor pre-bolted, wires through the window) onto the
   standoffs (M6 × 20 + wedge washers), hub + rotor onto the motor face, KD-100 +
   castellated nut + cotter onto the spindle (no counter-hold needed — the double-D pocket
   keys the spindle; rotate the *nut* to align a castellation with the cotter hole), then
   electronics and housing. Service
   reverses this from below; anchors are never touched.

## Sources

ESR-2713 (icc-es.org) · Simpson Titen HD installation instructions.
