# Loaded tuning, 2026-08-21

The first ceiling-mounted powered work began with the retained unloaded image in volatile shadow,
with Michael continuously observing the clear room and holding the physical cutoff. Serial
telemetry and Kasa wall power were recorded; no camera was available. No loaded MPET was performed.

## Installed Hall and first motion

- The first hand-rotation trial proved the mounted Hall signal but exposed that the board was
  still running firmware from before the five-second Hall-estimate expiry fix. The current
  qualified binary was flashed while the controller remained in unverified SafeBoot.
- Two slow hand revolutions on current firmware produced clean edge-period estimates and the
  Hall speed returned to zero after the five-second quiet window. The bridge remained disabled.
- A scripted 35 RPM loaded start then acquired cleanly, settled at about 35.5 RPM on both FG
  and Hall, looked smooth by owner report, and stopped normally. Startup wall power peaked at
  4.43 W and the steady 35 RPM input was about 1.55 W.

## Apple Home sweep

- Matter commissioned successfully to `SyNet-2G` and the `Uno Condo` Apple Home. Fabric and
  network state persisted; the controller obtained `10.10.1.25` and Apple subscriptions opened.
- A later start commanded from Apple Home at 35--40 RPM rocked back and forth without acquiring.
  Raising the slider to exactly 10% commanded 47.27 RPM and acquired cleanly. This makes 35 RPM
  an unsuitable released loaded floor despite the earlier successful start; 50 RPM is the
  provisional floor with a small margin.
- Michael increased the slider gradually through the range. Motion remained solid by owner
  report, Hall and FG stayed in close agreement, no controller fault appeared, and 100% mapped
  to 170 RPM. Wall power peaked at only 5.03 W.
- Downward Matter targets reached the supervisor, but the 1.5 RPM/s ramp made the response look
  stuck after the fast manual sweep. Wall power fell from about 5.03 W to 3.69 W before Michael
  cut Kasa power. The cutoff registered cleanly. The next candidate uses the already-released
  upper commissioning rate of 3 RPM/s.

## Released candidate

- Released minimum: 50 RPM.
- Acceleration/deceleration: 3 RPM/s.
- Retain the qualified unloaded MCF values as the loaded candidate rather than introducing an
  unmeasured MPET result.
- Use the MCF digital-speed override for both provisional and verified operation. The physical
  1 kHz SPEED input did not produce motion after the image first became verified; digital control
  is the path exercised by every successful loaded run.

## Start, range, and endurance evidence

- The 50 RPM / 3 RPM/s candidate completed three consecutive cold-position starts before a fourth
  run reported `BusUnreachable`. After a power cycle it completed four more consecutive starts.
- The bus fault was a stale-reader timeout: the high-rate Matter/Wi-Fi work could starve the MCF
  status task on the shared thread executor. Moving MCF service to its own priority-2 interrupt
  executor, below the priority-3 safety loop and above network work, removed the failure. An
  approximately eight-minute hold remained physically healthy through a USB telemetry pause, and
  an independent ten-minute 50 RPM endurance run completed with no fault. FG stayed near
  49.5--50.3 RPM, Hall stayed centered near 50 RPM, and steady wall power was about 1.67--1.77 W.
- A fixed command ladder reached about 50, 100, and 170 RPM with Hall/FG agreement and no fault.
  The down-ramp command now changes at 3 RPM/s, but the loaded rotor's observed coast from 170 to
  about 106 RPM took over 50 seconds. Explicit Off remained clean.

## Golden image and final boot proof

- A complete 24-register loaded image was captured and committed once while stopped. EEPROM
  recomputed the read-only parity bit in several words, so the stored post-commit values, not the
  volatile pre-commit parity bits, are the golden comparison.
- The first capture also exposed an EEPROM-latched trap: live `DEVICE_CONFIG1.I2C_TARGET_ADDR`
  read as zero even though the part was responding at its factory address. That capture moved the
  part to reserved target `0x00` after reboot. Recovery now probes `0x00`, and the golden image
  explicitly stores target `0x01`; a second commit restored the normal address.
- A cold power cycle found the MCF at `0x01`, reported the stored configuration verified and fault
  status clean, restored both Matter fabrics, and returned to stopped operation without staging.
- In verified mode, `pct 1` then acquired the loaded rotor and held for three minutes at about
  51.1 RPM FG / 50.2 RPM Hall with no fault and about 1.7--1.8 W steady input. After a further full
  Kasa power cycle, the image and Apple Home state restored again; another 1% start and one-minute
  hold ended at 51.1 RPM FG / 50.4 RPM Hall and stopped cleanly to zero.

## Provisional-use boundary

This release establishes reliable starts and continuous operation at the 50 RPM floor, continuous
Apple Home control through 170 RPM, responsive command changes, independent Hall/FG agreement,
clean stopping, and persistence. Loaded MPET, randomized multi-voltage start matrices, fixed loaded
plateaus, acoustic assessment from bed, and long maximum-speed thermal endurance remain later
qualification work; they are not claims made by this commissioning result.

## Owner observations after provisional use

- The current loaded tune is too loud for the intended above-bed overnight use even though its
  speed regulation and visible motion are solid. Acoustic reduction is the primary tuning goal.
- An occasional squeak is audible. Its source is not yet identified; preserve it as a symptom
  rather than assuming bearing lubrication. The next capture should test whether it is periodic
  with rotor angle, confined to startup, correlated with SOX/current distortion, or independent of
  drive state before any lubricant or mechanical intervention is chosen.
- Acceleration from rest is not subjectively smooth. The next session should capture the complete
  align/open-loop/handoff sequence and tune startup separately from steady-state acoustic changes.

## Next loaded-tuning session

- Planned microphone: Razer Seiren V3 Mini or equivalent raw 24-bit/96 kHz USB condenser, mounted
  on the stationary upper housing about 2--3 inches from the motor with compliant isolation. Keep
  gain, orientation, and position fixed; capture a stopped-room baseline and lossless WAV.
- Use the OWON VDS1022I on J8 SOX plus FG/SPEED or VM24 according to the recipe in
  [`docs/observability.md`](../docs/observability.md). First qualify frame timing and retain the
  raw samples and sidecar metadata before using it as continuous evidence.
- Synchronize microphone audio, supervisor telemetry, Hall/FG, Kasa power, and scope frames. Begin
  with the current golden image as the A/B reference; run loaded MPET as a captured comparison,
  never as an automatic EEPROM replacement.
- A camera is optional for ordinary steady-state work because Hall/FG already show stable motion.
  Add it when diagnosing the rough start or if the squeak repeats with rotor position; it remains
  useful for gross direction/reversal and visible rub, not as the primary high-speed tachometer.
- Candidate order: characterize the reference; localize the squeak; inspect startup current and
  handoff; compare startup parameters; then compare steady-state PWM/commutation candidates at
  matched measured speeds. Commit a new golden image only after the selected candidate repeats the
  low-speed starts, acoustic ladder, stop, and persistence checks.
