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
4. **Integrate the physical assembly**: fit PCB-02 and the owner-made Hall bracket, install
   the hub and rotor, make EB-100 around the populated PCB and real cable bends, then balance
   and check runout.
5. **Workshop mechanical proof**: after MEC-05 balance/runout passes, secure the rotor to an
   external drive in a cleared work area. Start at the lowest useful speed and advance only
   while it remains smooth. Disconnect the GL100 phases from PCB-01. PCB-01 and PCB-02 may
   remain powered for Hall telemetry, in which case the analog overspeed lock is expected to
   latch near 200 RPM; that only revokes PCB drive and does not stop the external drive. Use
   Hall telemetry or the drive's own speed readout for the 216 RPM, two-minutes-per-direction
   proof. Watch and listen continuously, stop between directions, and inspect before
   continuing. This is not a ceiling test and requires no safety bypass.
6. **Ceiling-mounted loaded commissioning**: use the installed plate for loaded MPET,
   startup tuning, the 180 RPM controller-limit check, representative starts, stable-speed
   checks through 170 RPM, essential shutdown behavior, and the eight-hour thermal run.
   Michael executes this installed work after the earlier gates pass. The real 200 RPM
   analog-trip run remains restrained bare-motor work, never an overhead loaded test.

Electronics is the immediate dependency. Mechanical dry-fit and firmware preparation can
proceed in parallel, but powered motor work waits for the no-motor board checks.

## Final test locations and control path

| Stage | Location and configuration | Allowed work |
|---|---|---|
| Board bring-up | Desk; motor phases disconnected | Rails, current draw, permission latch, watchdog, power recovery, console, and injected tach tests |
| Bare motor | Desk; GL100 rigidly restrained; no hub or blades | R/L measurements, manual-spin BEMF, feedback/stop behavior, explicitly released limited rotation, and the separate physical analog-trip test; no unloaded MPET |
| Rotor preparation | Unpowered assembly | Retention, hand clearance, balance, and runout |
| Mechanical proof | Secured external-drive setup in a cleared work area | First powered full-rotor work and 216 RPM proof in both directions, using Hall telemetry or the drive readout |
| Loaded commissioning | Final assembly on the installed ceiling plate | Loaded MPET and tuning, golden-image capture, then normal-range starts/speeds through 170 RPM under the 180 RPM ceiling, shutdown checks, and thermal run |

Whenever PCB-01 drives the motor, use the normal safety firmware. During the external-drive
proof its motor phases remain disconnected; PCB-01 may be powered only to report Hall data.
The host `stillair` CLI remains the commissioning harness for scripts, telemetry,
configuration work, and record capture; the simulator proves the harness but never the motor.
Before loaded commissioning, add a controlled MPET command and procedure to that interface.
Do not create a general permissive or safety-bypass firmware build for routine testing.

## Practical workshop test policy

This is a one-off personal DIY build, so the procedures name the tools and people that will
actually be present. They do not assume a separate vibration sensor, optical tachometer,
remote interlock, second operator, or engineered containment fixture.

- Start every new powered configuration at the lowest useful speed. Watch and listen
  continuously, and stop immediately for visible wobble, increasing vibration, rubbing,
  unusual sound, loose hardware, a walking setup, or disagreement between diagnostics.
- Use the controller's reported `fg_mrpm` and `hall_mrpm`, PCB-02 Hall telemetry during an
  external-drive run, or the external drive's credible speed readout. A separate optical
  tachometer is not required. Observation judges balance and behavior, not exact RPM.
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

> Populate and inspect both boards, build and continuity-check the harnesses, then pass
> PCB-01 through PCB-04 and TACH-01 without the motor.

Recommended work blocks:

- **30 to 60 minutes:** populate PCB-02 (U1, C1, J1).
- **60 to 120 minutes:** populate PCB-01 (C1, C2, C34, J1, J2, U8, and the F1 bridge).
- **30 to 60 minutes:** build, label, pull-test, and continuity-check the first harnesses.
- **60 to 120 minutes:** perform first power and the board-only safety-chain checks.

## Completed and owner-managed

The ceiling plate, primary anchors, spacers, spindle, standoffs, tether proof, and central
catcher proof are accepted complete by owner report. Michael owns all remaining installation
and installed commissioning. Agents must not suggest, audit, schedule, or prompt for ceiling
installation, tether, or catcher work unless explicitly asked.

## Future only on explicit request

Do not suggest, schedule, or use these as blockers unless Michael explicitly asks to resume
one: ENC-100 cosmetic housing, TEMP_SENSE firmware, intentional-imbalance testing,
exhaustive start matrices, exhaustive acoustic testing, network/Matter resilience testing,
and exhaustive fault permutations.
