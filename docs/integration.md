# Integration map

How the finished parts become a commissioned fan. This is the execution map; detailed
requirements remain in the linked design docs and `testing/test-matrix.csv`.

## The dependency spine

These stages are intentionally sequential. Finishing one materially reduces risk or rework
in the next.

1. **Complete PCB-01 and PCB-02**: hand-populate the omitted parts and make the first power,
   motor, Hall, and programming cables.
2. **Prove PCB-01 without the motor**: rails, current draw, DRVOFF, permission latch,
   watchdog, power recovery, console access, and the injected Hall/tach chain.
3. **Tune the bare motor**: connect the GL100 with no blades, run MPET plus independent
   checks, capture the golden MCF image, prove starts/stops/reversal, and scope VM transients.
4. **Integrate the physical assembly**: fit the Hall bracket and PCB-02, install the hub and
   catcher, make EB-100 around the populated PCB and real cable bends, then make ENC-100
   around the final bracket and routing.
5. **Prove the complete rotor off-ceiling**: balance/runout, capture and tether proof, guarded
   proof speed, intentional imbalance, full-rotor controls, acoustics, and thermal testing.
6. **Install and commission**: permanently mount the plate only after bench release, stack
   the proven assembly from below, then perform limited-speed installed commissioning.

Do not install blades for stage 3. Do not design ENC-100 before EB-100 and cable routing are
real. Do not permanently mount the ceiling plate before the off-ceiling proof work is done.

## Tracks available now

| Track | Can do now | Natural stopping point | What it unlocks |
|---|---|---|---|
| Electronics | Populate PCB-01/02; build first cables; start board-only tests | PCB-01..04 and TACH-01 pass | Motor tuning, Hall fit-up, every powered test |
| Ceiling preparation | Choose plate orientation; use the PLA MP-100 template to measure and mark; drill and clean the two primary holes | Two primary holes ready, no anchors installed | Removes site uncertainty before final install |
| Mechanical fit-up | Dry-fit MP/SP/ST/MC/RH/KD; make balance slugs; plan the guarded bench fixture | Non-powered stack fits cleanly | Hall bracket, rotor balance, proof setup |
| Firmware and test prep | Finish simulator scripts, bench-stim sequence, cable sheets, and later TEMP_SENSE | Repeatable commands and recorded procedures | Faster, less error-prone commissioning |

These are not four equal project branches. Electronics remains the main spine. Ceiling work
is genuinely independent until installation. Mechanical fit-up can proceed without powered
electronics, but BR-100 validation needs the Hall board and EB-100 should follow connector
population. Firmware/test preparation is useful whenever hands-on energy is low.

## Ceiling track: current boundary

Site drilling is approved and the concrete check is complete. No holes have been drilled.
A full-size PLA print of MP-100 is available as a lightweight marking template.

- The two primary centers at X +/-65 mm can be oriented, marked, drilled, and cleaned now.
- Leave the Titen HD anchors out until permanent plate installation. Their concrete threads
  are a one-install interface, and the plate/spindle/standoff unit must go up with them.
- **Do not mark or drill the tether hole from the PLA plate yet.** MP-100's tether clearance
  at X0, Y-82 is about 105 mm from either primary center, but `install.md` currently requires
  at least 190 mm anchor spacing. The tether termination and routing are also still open.
  Resolve those together before creating the third hole.

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

> Both boards are populated, the two primary ceiling holes are ready, and PCB-01 passes its
> first no-motor power and safety checks.

At that checkpoint, the next work becomes much narrower: bare-motor tuning, the Hall
assembly, and the actual PCB bracket.
