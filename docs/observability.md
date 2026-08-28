# Observability and evidence capture

Defines how Stillair is observed during commissioning, which signal is authoritative for
each claim, and how electrical waveforms join the existing synchronized evidence bundle.
This document owns the measurement architecture. Test limits remain in
[`testing/test-matrix.csv`](../testing/test-matrix.csv), motor behavior remains in
[`controls.md`](controls.md), and circuit details remain in [`electrical.md`](electrical.md).

## Measurement principles

- No single observer proves the motor is healthy. Controller telemetry, physical speed,
  electrical waveforms, input power, and audio answer different questions.
- Preserve disagreement. Hall and MCF FG are reported separately; neither is averaged into
  the other. A disagreement is evidence about a sensor, tracker, or estimator failure.
- A capture is not valid unless its configuration, time basis, command, load, direction,
  supply, and dropped-data status are recoverable from the artifact.
- The simulator validates protocol and harness behavior only. It provides no evidence about
  sensorless startup, current waveform, torque, vibration, or acoustics.
- Instrumentation never weakens a safety path. The physical cutoff remains reachable, the
  rotor remains restrained for bench work, and the controller's independent permission and
  overspeed chains remain active unless a specific guarded test says otherwise.

## Signal inventory and authority

| Observer | What it measures | Normal cadence | Authority and limitations |
|---|---|---:|---|
| PCB-02 physical Hall | One physical rotor edge per revolution | Edge timed | Primary shaft-speed authority above 140 RPM and an independent check everywhere else. A missing marker or cable can look like zero speed. |
| MCF FG | Electrical commutation-derived speed, configured at 20 pulses/revolution for the 20-pole-pair GL100 | Edge timed | Primary controller-speed and stop evidence; can agree with a bad estimator because it comes from the drive. |
| Supervisor telemetry | State, fault, on/off, target, ramped command, FG RPM, Hall RPM, duty, actual/requested direction, released minimum, configuration verdict, and dropped-frame count | 1–100 Hz | Behavioral record and pass/fail input. The `dropped` field makes serial loss visible. It is not an independent physical observer. |
| MCF register samples | Speed feedback, estimator angle, q-axis/current-loop values, VM and decoded fault registers | Test-specific | Diagnostic evidence for commutation, handoff, model, and fault cause. Sampling is intrusive enough that retained scripts bound its rate and duration. |
| IR camera | Gross motion, direction, stalls, rotor position, and synchronized microphone audio | 30 fps plus audio | Independent gross-motion authority. Optical RPM is accepted through 140 RPM; known orientation-specific tracker slip above that prevents precise high-speed use. |
| USB condenser microphone | Tonal and broadband motor/controller sound; planned 24-bit/96 kHz capture | Audio sample rate | Acoustic comparison only when position, gain, room state, speed, and load are matched. An independently supported close position just outside the future housing envelope preserves one reference through exposed tuning and final housing validation. It cannot localize motor versus controller without electrical correlation or an A/B change. |
| Kasa Utility Plug | Wall voltage, current, power, and energy | 1 Hz | Whole-system input power and long-run drift. It cannot resolve phase current or PWM behavior. |
| OWON VDS1022I | Two analog voltage waveforms | Up to 100 MS/s in 5 kpoint frames | Electrical waveform observer selected 2026-08-20. It is 8-bit and its continuous-stream behavior is unqualified until measured. USB isolation protects the host boundary; the two BNC channel grounds are still common. |
| ZEEWEII DSO3D12 | Two displayed analog waveforms | Manual capture | Local visual fallback. Its USB-C connection is treated as charging only; no raw computer acquisition path is assumed. Operate from battery when connected to the motor system. |
| Motor NTC | Stationary GL100/MC-100 motor-mount temperature | Slow | J4 and the purchased ring-lug NTC exist, but firmware acquisition remains TODO. Until implemented, read the divider with an external meter/logger or use an independent attached temperature logger for release thermal tests. |

The reusable host path is `firmware/scripts/08-flash-and-unloaded-profile.sh`. It aligns the
motor log, camera/audio, physical tracking, Hall/FG telemetry, and wall-power evidence, and
fails closed when a required observer disappears. Loaded commissioning should extend this
bundle rather than inventing a separate timing convention.

## J8 scope header

J8 is a DNP 2 x 5, 1.27 mm header. Populate the selected SparkFun 15362 header or probe the
bare pads. The fabricated schematic and board, not connector orientation guessed from a
photograph, control the pin numbers:

| Pin | Net | Domain | Primary use |
|---:|---|---|---|
| 1 | VM24 | Power | Bus insertion, running ripple, cutoff, coast, and regeneration |
| 2 | PGND | Power ground | VM24 reference only |
| 3 | 3V3 | Logic rail | Rail integrity and digital reference |
| 4 | +12V_TACH | Tach rail | Analog overspeed supply integrity |
| 5 | DRVOFF | Logic | Actual drive-disable command |
| 6 | SPEED | Logic/PWM | Speed-command waveform |
| 7 | FG | 3.3 V open-drain logic | MCF commutation-derived speed |
| 8 | NFAULT | 3.3 V open-drain logic | MCF aggregate fault indication |
| 9 | SOX | MCF analog | Internal phase-current-sense amplifier output |
| 10 | AGND | Analog ground | SOX and quiet logic reference |

J8 intentionally does not expose U, V, or W. Phase measurements use the motor connector or
dedicated probe points only with the protection described below.

## OWON VDS1022I commissioning

The selected instrument is specifically the **VDS1022I**, not the non-isolated VDS1022.
OWON specifies two channels, 25 MHz bandwidth, 100 MS/s maximum sampling, 8-bit conversion,
5 kpoint record length, hardware triggering, SCPI support, and isolated USB. The community
[`OWON-VDS1022`](https://github.com/florentbr/OWON-VDS1022) project provides an Apple-silicon
macOS application and a Python API for direct frame acquisition. The
[manufacturer product page](https://www.owon.co.jp/products_info.asp?ProductID=6) is the
specification source.

Before using it as release evidence:

1. Confirm the case and USB enumeration identify `VDS1022I`.
2. Install the community application/API on the commissioning Mac and retain the exact
   version or commit in the capture metadata.
3. Run zero and gain calibration against a trusted DC reference and the probe-compensation
   output. Record residual zero offset and channel-to-channel gain difference.
4. Verify both channel grounds are common with power removed. USB isolation does not imply
   channel-to-channel isolation.
5. Exercise normal and single hardware triggering at the intended voltage ranges.
6. Characterize repeated-frame acquisition. Record sample rate, points/frame, host arrival
   times, and API errors while observing a stable clock. Unless phase continuity or device
   timestamps prove otherwise, treat the interval between frames as unknown dead time.
7. Deliberately stall the host reader and confirm the recorder exposes the loss. A logger
   that silently concatenates gapped frames must not label the result continuous.

The 5 kpoint memory is adequate for short triggered PWM and current snapshots. At 100 MS/s it
covers only 50 microseconds, about 1.25 cycles of the selected 25 kHz PWM. Use lower sample
rates for commutation/envelope views and the maximum rate only for switching detail.

### Recorder contract

The first host recorder should preserve raw ADC samples in a compact binary format and write
a sidecar manifest containing:

- UTC start time and host monotonic start time;
- scope model/serial, software/API version, channel ranges, coupling, probe attenuation,
  sample rate, frame length, trigger source/level/slope, and calibration record;
- J8 net and reference ground connected to each channel;
- motor profile, MCF image identifier or full capture, supply, rotor/load revision,
  direction, camera-to-motor offset, and room/microphone state;
- every frame's host arrival time, device timestamp if one exists, sequence number if one
  exists, and any overrun, timeout, or discontinuity flag.

Conversion to CSV, plots, FFTs, and spectrograms happens after capture. CSV is not the raw
storage format for long runs.

## Safe hookup classes

### Low-voltage J8 signals

- **SOX:** channel tip to J8.9, ground to J8.10 AGND. Use the smallest range that contains
  the waveform without clipping. Keep the pair short and twisted.
- **FG, nFAULT, DRVOFF, SPEED, or 3V3:** channel tip to the selected signal, ground to
  J8.10 AGND. Do not enable any scope or adapter pull-up that changes the board signal.
- **+12V_TACH:** use a x10 probe if required by the selected vertical range; reference AGND.

### VM24

Probe J8.1 relative to J8.2 PGND with a correctly configured x10 probe. The normal transient
target is at most 35 V and 40 V rejects the design. Verify the probe and scope range cover the
possible excursion before applying power.

### Motor phases

Never connect a scope ground clip to U, V, or W. The VDS1022I's isolated USB does not make
its two BNC inputs independently floating. Direct phase-to-phase or phase-to-ground work
requires a properly rated differential probe or another validated isolated measurement
method. Until that equipment exists, SOX is the phase-current observer and VM24 is the bus
observer.

## Standard capture recipes

### Startup and sensorless handoff

- Analog 1: SOX to AGND.
- Analog 2: SPEED or FG to AGND.
- Concurrent evidence: 10 Hz supervisor stream, estimator samples where the retained
  profile calls for them, physical Hall, camera video, dedicated-microphone audio, and wall power.
- Trigger: SPEED/FG transition or SOX threshold before releasing DRVOFF.
- Look for: current acquisition, repeated align attempts, discontinuity at open-to-closed
  loop handoff, current limiting, missed FG, direction error, and a tonal event aligned with
  current distortion.

### Loaded steady-speed acoustic comparison

- Analog 1: SOX to AGND.
- Analog 2: VM24 through x10 to PGND, or FG to AGND when exact electrical-cycle alignment is
  more useful than bus ripple.
- Hold camera/microphone position and gain fixed. Compare candidates at measured Hall speed,
  not merely equal command.
- Retain time waveform, current-envelope spectrum, microphone spectrum, Hall/FG stability,
  duty, and wall power for the same settled window.

### Close microphone and camera use

- The planned Razer Seiren V3 Mini is a directional side-address microphone: point its front/logo
  face at the motor or nearest acoustic opening, not its top. Record raw 24-bit/96 kHz WAV with
  automatic gain, voice isolation, gates, compression, EQ, and vendor processing disabled.
- Preferred source-diagnostic placement is on an independent stand or boom, close to the motor but
  just outside the future housing envelope and outside the main blade downwash. Choose the position
  so the motor damping and housing can be installed later without moving the microphone. Isolate the
  support from the fan structure, strain-relieve the USB cable separately, and begin with low input
  gain. A fan-mounted microphone can turn housing vibration into an apparent airborne tone.
- Capture stopped-but-powered and fully unpowered baselines without moving the microphone. Preserve
  unsmoothed spectra and spectrograms; a close microphone is comparative evidence, not a calibrated
  absolute-SPL meter.
- Keep the only dedicated microphone fixed through the exposed golden reference, all controller
  candidates, the exposed finalist, and the final damped housing capture. Do not perform a formal
  bed-position microphone A/B; Michael's direct listening from bed supplies the final subjective
  judgment while the fixed close capture preserves diagnostic comparability.
- Camera is selective rather than mandatory. Set it up for the first instrumented session because
  the rough startup and intermittent chirp can benefit from motion and rotor-position correlation.
  Hall and FG already establish steady-speed stability, so omit video from later ordinary acoustic
  plateaus if the baseline shows that it adds no evidence. Use at least 30 fps for startup,
  reversal, suspected contact, or a chirp that may repeat at a particular rotor position.
- Camera audio is never an acoustic-comparison source when the dedicated microphone is present.
  Leaving it enabled can provide a convenient synchronization track: a clap, startup sound, or the
  same chirp can align dedicated audio to video frames. If a visible synchronization cue provides
  the required alignment, camera audio may be ignored or disabled.

### Cutoff, stop, and regenerative transient

- Analog 1: VM24 through x10 to PGND.
- Analog 2: DRVOFF, FG, or nFAULT to the matching ground.
- Use single trigger and enough pre-trigger history to include the command edge.
- This capture supports DRV-09 and the mandatory VM scope gate. It does not authorize a
  phase probe connection.

## Evidence hierarchy for decisions

1. Safety and fault conclusions require the hardware state plus decoded controller status.
2. Shaft-speed conclusions use physical Hall first, then MCF FG, with camera as the gross
   motion guard.
3. Current-waveform conclusions use SOX only after its configured gain and offset are
   recorded.
4. Acoustic conclusions require matched measured speed, load, direction, microphone setup,
   and room state.
5. A scope frame proves only its captured interval. It cannot prove a long run was clean
   unless acquisition continuity was itself demonstrated.

Retained results belong in `testing/`; reusable acquisition and analysis code belongs in
`firmware/scripts/`. Do not embed one-off measurements in this architecture document.

The reusable loaded entry point is `firmware/scripts/09-run-loaded-profile.sh`. It records all
sources into one run directory with nanosecond wall-clock anchors and a hashed evidence manifest.
The OWON helper pins the `florentbr/OWON-VDS1022` Python API at commit
`4c67805713906c20b4414b4225fd293adea4cb05`. Its 5,000-sample acquisitions are explicitly discrete
frames with unknown inter-frame data; the JSONL index retains each arrival gap so no later analysis
can mistake this mode for gap-free streaming. The initial SOX/FG recipe is a safe preflight starting
point, not a calibrated setup: confirm the VDS1022I model, common-ground connections, range, offset,
trigger, and clipping on the installed hardware before releasing the motor run.

The installed-scope preflight on 2026-08-28 identified VDS1022I serial `VDS1022I26190076`, hardware
version `V5.0.1`, and repeatable 5,000-sample frames at about 249,940 sample/s through the commissioning
USB hub. With a 5 V range, a centered `0.5` offset clips the 3.3 V FG high at 2.5 V. The retained
SOX/FG recipe therefore uses offset `0.2`, which measured the stationary FG high at 3.24--3.32 V and
keeps the nominal 0--3.3 V signals inside the approximately -1 to +4 V window.
