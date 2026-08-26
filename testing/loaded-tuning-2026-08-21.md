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

- The fan subsequently ran perfectly all night at the 1% setting (the 50 RPM released floor) by
  owner report. At that setting its motor/electrical noise was minimal and almost inaudible, so the
  provisional floor is already usable for sleep despite the remaining acoustic work.
- Higher settings have a consistent coil-whine/electrical tonal character. Treat this steady tone
  separately from the intermittent event during capture: compare its frequency, harmonics, and
  sidebands against PWM, commutation, electrical angle, SOX, speed, and load at matched RPM.
- The occasional sound is better described as a short chirp-like event than a generic squeak. Its
  source is not yet identified; preserve it as a symptom rather than assuming bearing lubrication.
  The next capture should test whether chirps are periodic with rotor angle, confined to startup or
  target changes, correlated with SOX/current distortion, or independent of drive state before any
  lubricant or mechanical intervention is chosen.
- Acceleration from rest is not subjectively smooth. The next session should capture the complete
  align/open-loop/handoff sequence and tune startup separately from steady-state acoustic changes.

## Synchronized loaded-tuning plan

The dedicated microphone has arrived and is usable; the OWON is expected roughly seven days later.
Because physical setup is easier to batch and the current golden image is already pleasant in use,
defer candidate tuning until the scope is present. A short microphone shakedown may verify format,
gain, mounting, and clipping, but it is not the formal reference and changes no motor setting.

Source tuning uses the exposed assembly. The decided 2 mm butyl/film automotive damping panels on
the motor and inside the stationary upper housing are a later passive improvement, not part of
finding the controller tune. Install them only after the exposed finalist has been captured, without
changing that finalist, then measure the completed assembly as a separate final-system validation.

### Launch and autonomous authority

Michael has preauthorized the upcoming run. Saying `next`, `begin the loaded tune`, or equivalent
is the launch signal and confirms that the installed fan is clear, he is continuously watching it,
and the immediate physical cutoff is available. After the one-time physical hookup is validated,
Codex may autonomously issue speed, direction, and stop commands; power cycle through the available
control path; flash firmware; stage and restore volatile MCF configurations; run acquisition and
analysis scripts; and use the connected microphone, scope, camera, Hall/FG, telemetry, and Kasa
power evidence. Routine candidate choices and repeat runs do not require additional permission.

Autonomy does not permit bypassing a hardware protection, exceeding the released 50--170 RPM range,
changing direction before verified stop, continuing after loss of human observation or the cutoff,
or guessing through a physical probe or mechanical intervention. Codex owns all software and
instrument automation; Michael performs only unavoidable physical hookups and the later damping and
housing installation, with one-step instructions when needed.

- Use the Razer Seiren V3 Mini or equivalent raw 24-bit/96 kHz USB condenser on an independent
  support, close to the motor but just outside the future housing envelope. Aim the front/logo face
  at the motor or nearest future opening. Keep gain, orientation, and room position fixed from the
  exposed golden baseline through the completed-housing capture; record stopped-room baselines and
  lossless WAV.
- At the start of the instrumented session, synchronize microphone audio, SOX plus FG/SPEED or VM24,
  supervisor telemetry, Hall/FG, and Kasa power. Capture the untouched current golden image with the
  dedicated mic fixed at the close-motor position **before changing any setting**. Confirm the
  captures are usable before beginning candidate work; the source baseline cannot be reconstructed
  honestly afterward.
- Set up the available camera for startup and the intermittent chirp. It is useful for detecting
  rough align/open-loop/handoff motion, visible contact, and rotor-position correlation. Hall/FG
  already establish steady-state stability, so video is not required for every acoustic plateau;
  omit it from ordinary steady-state captures. The dedicated microphone is the only acoustic
  authority. Camera audio may remain enabled solely to align video frames with dedicated-mic audio;
  never use it to compare candidates.
- First qualify scope frame timing and retain raw samples plus sidecar metadata. Use the synchronized
  evidence to distinguish electrical/commutation tones from mechanical radiation and to correlate
  transient chirps with SOX/current distortion, command transitions, or rotor position.
- Continue recording and judging every audible noise mode. During exposed source tuning, prioritize
  the intermittent chirp and rough startup sequence, then persistent narrowband tones that track
  PWM, commutation, electrical frequency, or current distortion. Capture broadband blade/airflow
  noise in the same ladder so it is not hidden, while treating it as a controller-tuning target only
  if synchronized evidence shows that a drive candidate changes it.
- Candidate order: characterize the reference; separate the steady electrical whine from transient
  chirps; localize the chirp; inspect startup current and handoff; compare startup parameters; then
  compare steady-state PWM/commutation candidates at matched measured speeds. Continue until every
  meaningful safe parameter family has either improved the result or been rejected by evidence and
  further changes produce no measurable improvement. Commit a new golden image only after the
  selected candidate repeats the low-speed starts, acoustic ladder, stop, persistence, both-direction
  behavior, and applicable endurance and fault checks.
- Keep the dedicated microphone fixed after the exposed finalist capture. Install the motor damping
  and completed upper housing with its interior damping without changing the controller tune, then
  repeat the close-mic acoustic ladder plus final mechanical and thermal qualification. Resume
  controller tuning only if the completed assembly exposes an objectionable sound that synchronized
  evidence ties to the controller. Skip a formal bed-position microphone capture; Michael's direct
  listening from bed is the final subjective acceptance check.
- Run loaded MPET as a captured comparison only, never as an automatic EEPROM replacement. Promote
  a candidate only if it improves the matched acoustic result and repeats all release checks.

### Prepared acquisition path

The pre-hardware automation is ready as of 2026-08-26. `09-run-loaded-profile.sh` validates and
runs `51-loaded-golden-baseline.txt` in verified-golden mode, rejects configuration mutation and
speeds outside 50--170 RPM, records the fixed microphone at 24-bit/96 kHz, captures timestamped
discrete OWON frames, and bundles camera, controller, Hall/FG, Kasa, audio, and scope evidence in a
hashed manifest. Its hardware-free validation and simulated scope path pass. No physical baseline
has been recorded: the OWON, microphone, camera, and controller were not attached during this
preparation, so device enumeration, microphone gain/clipping, scope range/offset, trigger quality,
probe grounds, and cross-source timing still require the one-time watched hookup.

The prepared entry point intentionally cannot mutate the loaded golden image. After the untouched
reference is secured, each candidate must be generated in volatile shadow with an explicit reviewed
change and its own evidence run. The current firmware does not treat an arbitrary raw register write
as runnable configuration; it invalidates the configuration verdict. Keep that guard. Add or adjust
a narrowly scoped candidate mechanism only after the baseline shows which parameter family the
synchronized evidence justifies testing.
