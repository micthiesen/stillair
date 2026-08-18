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
5. **Guarded mechanical proof**: after MEC-05 balance/runout passes, use the released
   external-drive fixture and barrier for the first powered full-rotor work: 216 RPM for two
   minutes in each direction. This is not a ceiling test.
6. **Ceiling-mounted loaded commissioning**: use the installed plate for loaded MPET,
   startup tuning, the 180 RPM controller-limit check, representative starts, stable-speed
   checks through 170 RPM, essential shutdown behavior, and the eight-hour thermal run.
   Michael executes this installed work after the earlier gates pass. The real 200 RPM
   analog-trip run remains guarded bare-motor work, never an overhead loaded test.

Electronics is the immediate dependency. Mechanical dry-fit and firmware preparation can
proceed in parallel, but powered motor work waits for the no-motor board checks.

## Final test locations and control path

| Stage | Location and configuration | Allowed work |
|---|---|---|
| Board bring-up | Desk; motor phases disconnected | Rails, current draw, permission latch, watchdog, power recovery, console, and injected tach tests |
| Bare motor | Desk; GL100 rigidly restrained and guarded; no hub or blades | R/L measurements, manual-spin BEMF, feedback/stop behavior, explicitly released limited rotation, and the separately guarded physical analog-trip test; no unloaded MPET |
| Rotor preparation | Unpowered assembly | Retention, hand clearance, balance, and runout |
| Mechanical proof | Separate guarded fixture with external drive | First powered full-rotor work and 216 RPM proof in both directions |
| Loaded commissioning | Final assembly on the installed ceiling plate | Loaded MPET and tuning, golden-image capture, then normal-range starts/speeds through 170 RPM under the 180 RPM ceiling, shutdown checks, and thermal run |

Use the normal safety firmware throughout. The host `stillair` CLI remains the commissioning
harness for scripts, telemetry, configuration work, and record capture; the simulator proves
the harness but never the motor. Before loaded commissioning, add a controlled MPET command
and procedure to that interface. Do not create a general permissive or safety-bypass firmware
build for routine testing.

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
