# Integration map

How the finished parts become a working fan. Detailed requirements remain in the linked
design docs and `testing/test-matrix.csv`.

For bench work, print `output/pdf/stillair-integration-field-guides.pdf`. It contains only
the active electronics, mechanical integration, firmware, balance, proof-speed, start, and
thermal sheets. A HOLD badge means an active prerequisite is unresolved.

## Active dependency spine

1. **Complete PCB-01 and PCB-02**: hand-populate the omitted parts and make the power,
   motor, Hall, and programming cables.
2. **Prove PCB-01 without the motor**: verify rails, current draw, DRVOFF, the permission
   latch, watchdog, power recovery, console access, and the injected Hall/tach chain.
3. **Characterize the bare motor**: independently measure R, L, and manual-spin BEMF, then
   prove the safe console/control path and permitted VM transients. Do not run MPET unloaded;
   use the representative rotor for MPET and the final golden-image cross-check.
4. **Integrate the physical assembly on the installed plate**: fit PCB-02 and the owner-made
   Hall bracket, install the hub and rotor, make EB-100 around the populated PCB and real cable
   bends, route and strain-relieve the long USB service lead, then check retention, hand
   clearance, balance, and runout with power removed.
5. **Ceiling-mounted loaded commissioning**: use the installed plate for loaded MPET,
   startup tuning, the 180 RPM controller-limit check, representative starts, stable-speed
   checks through 170 RPM, essential shutdown behavior, and the eight-hour thermal run.
   Start at the lowest useful speed with the cutoff reachable, watch and listen continuously,
   and increase only after each step is smooth. The real 200 RPM analog-trip run remains
   restrained bare-motor work, never an overhead loaded test.

Electronics is the immediate dependency. Mechanical dry-fit and firmware preparation can
proceed in parallel, but powered motor work waits for the no-motor board checks.

## Final test locations and control path

| Stage | Location and configuration | Allowed work |
|---|---|---|
| Board bring-up | Desk; motor phases disconnected | Rails, current draw, permission latch, watchdog, power recovery, console, and injected tach tests |
| Bare motor | Desk; GL100 rigidly restrained; no hub or blades | R/L measurements, manual-spin BEMF, feedback/stop behavior, explicitly released limited rotation, and the separate physical analog-trip test; no unloaded MPET |
| Rotor preparation | Unpowered assembly | Retention, hand clearance, balance, and runout |
| Installed mechanical check | Final assembly on the installed ceiling plate, power removed | Retention, hand clearance, balance, runout, harness routing, and strain relief |
| Loaded commissioning | Final assembly on the installed ceiling plate | First powered full-rotor work at the lowest useful speed, then loaded MPET and tuning, golden-image capture, normal-range starts/speeds through 170 RPM under the 180 RPM ceiling, shutdown checks, and thermal run |

Whenever PCB-01 drives the motor, use the normal safety firmware. The host `stillair` CLI
remains the commissioning harness for scripts, telemetry,
configuration work, and record capture; the simulator proves the harness but never the motor.
Use the numbered sequences in `firmware/scripts/`. Controlled MPET is `mpet run`: it enters
an explicit service state from `IdleOff`, uses the ordinary permission and fault paths,
reports the raw result registers, aborts on its deadline, and leaves results uncommitted for
review and capture.
Until the loaded golden image is committed, each motor-power cycle begins `unverified` in
`SafeBoot`. Scripts 02 and 03 first execute `config stage`, verify the volatile first-spin
image, and require a separate fresh run command. Staging never writes EEPROM. Release scripts
04 through 06 instead require `config check` against the committed golden image. A normal
start command must never be issued directly against factory defaults because zero speed-loop
gains invoke the MCF's implicit MPET path.
Do not create a general permissive or safety-bypass firmware build for routine testing.

## Practical workshop test policy

This is a one-off personal DIY build, so the procedures name the tools and people that will
actually be present. They do not assume a separate vibration sensor, optical tachometer,
remote interlock, second operator, or engineered containment fixture.

- Start every new powered configuration at the lowest useful speed. Watch and listen
  continuously, and stop immediately for visible wobble, increasing vibration, rubbing,
  unusual sound, loose hardware, a walking setup, or disagreement between diagnostics.
- Use the controller's reported `fg_mrpm` and `hall_mrpm`. A separate optical tachometer is
  not required. Observation judges balance and behavior, not exact RPM.
- Keep people and loose objects out of the rotor plane. Keep an ordinary power switch,
  low-voltage cutoff, or plug reachable from outside the sweep. Removing power makes the
  rotor coast; it is not an instant brake.
- Record the speed source and the actual setup used. A result that depends on unavailable
  equipment is not a valid instruction for this project.

For ceiling work, connect the laptop to PCB-01 J6 with a quality long USB cable; use an active
USB extension if the passive link is unreliable. USB carries communication only, so PCB-01
still uses the fused 24 V path. Keep USB outside the rotor sweep and strain-relieve it. Keep
the motor, Hall, and 24 V harnesses at their intended final lengths. Place the low-voltage
cutoff within reach from outside the sweep; the accessible mains plug is a backup power
disconnect, not a rotor brake.

## Current checkpoint

> Install the finished motor, rotor, Hall board, and controller onto the existing ceiling plate;
> establish permanent harness strain relief and a serviceable long-USB path; then perform the
> unpowered clearance and continuity checks in [`install.md`](install.md).

The ceiling plate, primary anchors, spacers, spindle, standoffs, tether proof, and central
catcher proof remain accepted complete by owner report and are not reopened. Michael explicitly
resumed project assistance for the remaining physical integration on 2026-08-20. He performs the
physical steps while the agent guides one step at a time. Loaded MPET and tuning are the following
checkpoint, on the installed ceiling assembly rather than an improvised loaded bench rig.

## Future only on explicit request

Do not suggest, schedule, or use these as blockers unless Michael explicitly asks to resume
one: ENC-100 cosmetic housing, V1 TEMP_SENSE firmware, intentional-imbalance testing,
exhaustive start matrices, exhaustive acoustic testing, network/Matter resilience testing,
exhaustive fault permutations, tether rework, catcher rework, or PCB-bracket CAD.
