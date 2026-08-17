# Integration map

How the finished parts become a commissioned fan. This is the execution map; detailed
requirements remain in the linked design docs and `testing/test-matrix.csv`.

For bench and installation use, print
`output/pdf/stillair-integration-field-guides.pdf`. Its sheets 0A through 6B turn this map
into concise checklists and diagrams. A HOLD badge is a hard boundary, not a prompt to fill
in missing engineering at the work site.

## The dependency spine

These stages are intentionally sequential. Finishing one materially reduces risk or rework
in the next.

1. **Complete PCB-01 and PCB-02**: hand-populate the omitted parts and make the first power,
   motor, Hall, and programming cables.
2. **Prove PCB-01 without the motor**: rails, current draw, DRVOFF, permission latch,
   watchdog, power recovery, console access, and the injected Hall/tach chain.
3. **Characterize the bare motor**: connect the GL100 with no blades, independently measure
   R, L, and manual-spin BEMF, prove the safe console/control path, and scope the permitted
   VM transients. Do not run MPET unloaded: `controls.md` requires the representative final
   rotor because unloaded MPET can produce bad Ke/Kp/Ki. Capture the golden MCF image only
   after that loaded cross-check.
4. **Integrate the physical assembly**: fit the Hall bracket and PCB-02, install the hub and
   catcher, make EB-100 around the populated PCB and real cable bends, then make ENC-100
   around the final bracket and routing.
5. **Prove the complete rotor off-ceiling**: balance/runout, capture and tether proof, guarded
   proof speed, intentional imbalance, full-rotor controls, acoustics, and thermal testing.
6. **Install and commission**: MP-100 was permanently mounted early on 2026-08-17 with its
   standoffs and spindle. After bench release, stack only the proven assembly from below,
   then perform limited-speed installed commissioning.

Do not install blades for stage 3; MPET and the final golden image therefore occur after the
representative rotor is assembled, before full-rotor proof. Do not design ENC-100 before
EB-100 and cable routing are real. The ceiling plate was mounted before the off-ceiling
proof work; do not extend that sequencing departure by adding the motor, carrier, or rotor
to it before their required bench proof is complete.

## Tracks available now

| Track | Can do now | Natural stopping point | What it unlocks |
|---|---|---|---|
| Electronics | Populate PCB-01/02; build first cables; start board-only tests | PCB-01..04 and TACH-01 pass | Motor tuning, Hall fit-up, every powered test |
| Ceiling preparation | **Complete 2026-08-17:** two primary holes drilled and MP-100 installed with ST-100s and SP-100 | Record the installed primary-anchor stack for INS-01; tether stays on HOLD | Ceiling-side plate work complete |
| Mechanical fit-up | Dry-fit MP/SP/ST/MC/RH/KD; make balance slugs; plan the guarded bench fixture | Non-powered stack fits cleanly | Hall bracket, rotor balance, proof setup |
| Firmware and test prep | Finish simulator scripts, bench-stim sequence, cable sheets, and later TEMP_SENSE | Repeatable commands and recorded procedures | Faster, less error-prone commissioning |

These are not four equal project branches. Electronics remains the main spine. Ceiling work
is genuinely independent until installation. Mechanical fit-up can proceed without powered
electronics, but BR-100 validation needs the Hall board and EB-100 should follow connector
population. Firmware/test preparation is useful whenever hands-on energy is low.

## Ceiling track: installed state

MP-100 was installed on 2026-08-17 (owner report), with the three ST-100 standoffs and
SP-100 spindle already in the plate. The two primary holes and primary mounting operation
are complete.

- Record the installed primary anchor model, washer/hard-spacer stack, hole spacing and
  depth/embedment basis, and confirm the plate bears on the hard spacers rather than ceiling
  finish. This closes the documentation portion of `INS-01`; do not disturb the anchors to
  obtain it.
- **Do not mark or drill the tether hole from the PLA plate yet.** MP-100's tether clearance
  at X0, Y-82 is about 105 mm from either primary center, but `install.md` currently requires
  at least 190 mm anchor spacing. The tether termination and routing are also still open.
  Resolve those together before creating the third hole.

## Before MP-100 is anchored

This is a one-way assembly boundary. MP-100's ceiling face becomes inaccessible after the
two primary Titen HDs clamp it to the slab.

Bench-assemble this plate unit before the overhead lift:

1. Put MP-100 ceiling-face-up.
2. Insert **SP-100, the center capture spindle**, from the ceiling side. Seat its flange
   fully in the double-D recess with the flats engaged, metal flange bearing directly on
   the pocket shoulder, and the long shank hanging downward.
3. Add **three tiny, spaced dots of non-corrosive neutral-cure RTV across the top perimeter
   seam** between the flange and MP-100. Do not put silicone under the flange or coat the
   bearing face. Let it cure fully in air per the product instructions before installation.
   This is a removable anti-rattle restraint only; the metal shoulder remains the complete
   capture load path.
4. Install the **three ST-100 standoffs** using **three M6 × 16 A4 flat-head screws from the
   ceiling face**. Use three standoffs; the fourth is a spare. Tighten to the released joint
   requirement and confirm all three countersunk heads are flush or slightly below the
   ceiling face.
5. After the RTV cures, gently tap and shake the plate unit. SP-100 must remain fully seated
   without a metallic click. Keep it ceiling-face-up before cure so the spindle cannot fall
   out. The hard spacers leave clearance to the slab, so the ceiling does not clamp the
   flange after installation.

During the overhead lift, each primary stack is Titen head, washer, MP-100, hard spacer,
then ceiling. The loose hard spacers are positioned at that time, not permanently attached
to the bench-built plate unit.

Leave these off until the plate is anchored: MC-100 and motor, RH-100 and blades, KD-100 /
castellated nut / cotter, EB-100 and electronics, cable clamps, and ENC-100. They all install
from below. Tether hardware is excluded from this checklist until its location and
termination conflict is resolved.

## Pick by available energy

- **10 to 20 minutes, low focus**: lay out the exact PCB-02 parts and tools, or hold the PLA
  template up and choose the fan/cable-entry orientation without marking.
- **30 to 60 minutes, careful bench work**: populate PCB-02 (U1, C1, J1).
- **60 to 120 minutes, careful bench work**: populate PCB-01 (C1, C2, C34, J1, J2, U8,
  and the F1 bridge).
- **20 to 40 minutes, physical but clean**: level the PLA template, mark only the two primary
  centers, and record their room references so the orientation is reproducible.
- **30 to 60 minutes, physical and dirty**: drill and clean only the two primary holes with
  the documented bit and depth stop.

## Immediate definition of progress

The next project checkpoint is not "integrated fan." It is:

> Both boards are populated and PCB-01 passes its first no-motor power and safety checks.

At that checkpoint, the next work becomes much narrower: bare-motor tuning, the Hall
assembly, and the actual PCB bracket.
