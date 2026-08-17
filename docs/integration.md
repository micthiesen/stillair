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
5. **Bench release**: verify the 180 RPM controller limit and 200 RPM analog trip, complete
   the guarded 216 RPM proof, run the reduced representative-start set, verify stable speed
   and essential shutdown behavior, then complete the eight-hour thermal run.

Electronics is the immediate dependency. Mechanical dry-fit and firmware preparation can
proceed in parallel, but powered motor work waits for the no-motor board checks.

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
