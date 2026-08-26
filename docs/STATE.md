# State

Fast-moving work state and chosen next step. Durable findings live in the linked design,
commissioning, BOM, and test documents.

Last updated: **2026-08-26** (final acoustic configuration and tuning priorities recorded.)

## Now

- **The complete ceiling assembly is installed and accepted by owner report.** Installed wiring,
  Hall sensing, catcher clearance, fastener stacks, hand rotation, and the permanent 24 V feed are
  complete. Details remain in [install.md](install.md) and [parts.md](parts.md).
- **The fan has a persistent provisional 50--170 RPM operating release.** The loaded golden MCF
  image verifies from EEPROM at target `0x01`; Apple Home, Wi-Fi, and both Matter fabrics survive
  cold power cycles. Nine 50 RPM starts and a fault-free ten-minute low-speed hold passed with
  Hall/FG agreement and about 1.7 W steady input.
- **Control-path defects found during commissioning are fixed.** MCF service now runs above network
  work, verified operation uses the loaded-qualified digital-speed path, target-address recovery
  covers `0x00`, and EEPROM parity is compared against post-commit values. Evidence and rejected
  paths are in [loaded-tuning-2026-08-21.md](../testing/loaded-tuning-2026-08-21.md).
- **The released 1% sleep setting passed an overnight owner run.** It ran perfectly all night at
  the 50 RPM floor and was minimally audible. Remaining acoustic work is concentrated at higher
  settings: a consistent coil-whine/electrical tone plus occasional short chirp-like events. The
  start from rest also remains subjectively rough; visible steady-state jitter is no longer
  material. Details are in the loaded-tuning report and `DRV-02`/`DRV-04` in
  [test-matrix.csv](../testing/test-matrix.csv).
- **The Home slider feedback hotfix is installed and accepted.** Both Matter percentage
  attributes report the requested target instead of feeding intermediate ramp speed back into
  Apple Home. Michael confirmed that an extended press-and-drag stayed with his finger while live
  telemetry recorded multiple changing targets during the physical ramp; details are in `CTL-11`.
- **Wi-Fi RF diagnostics are queued for the next firmware flash.** The USB console's new `wifi`
  command reports current and weakest RSSI, signal quality, sampling failures, disconnects, and
  last-success time without exposing SSID, credentials, scans, or a new LAN listener. The installed
  image does not contain this yet.
- **The provisional automation intent is occupied-by-default.** After final startup and endurance
  qualification, a confirmed arrival should start forward 1%; temperature may later boost to 20%
  and return to 1%, while manual Off, faults, reboots, and power restoration remain no-start gates.
- **The remaining work is finite and ordered.** The microphone has arrived and is usable; the OWON
  is expected in roughly seven days. Rather than duplicate setup, acoustic and electrical tuning
  will run as one instrumented batch after it arrives, beginning with an untouched-golden baseline.
  Michael will first install the decided 2 mm butyl/film damping panels on the motor and inside the
  upper housing, making that damped assembly the fixed physical baseline for all final comparisons.
  Then Michael will make a cleaner Hall-board mount and verify the sensor again before completing
  the owner-designed cosmetic housing and printed power-cable conduit.

## Next

After the OWON arrives and the damping panels are installed, run one synchronized loaded-tuning
batch. Before changing any controller setting, record the current golden reference with the
dedicated mic fixed at the close-motor position, plus scope, Hall/FG, telemetry, Kasa power, and
selective camera video. Keep the physical acoustic configuration and mic fixed through every
source-level comparison. Still evaluate every noise mode, prioritizing chirps and rough startup,
then persistent electrical/commutation tones that remain audible at the bed; treat residual housing
resonance and broadband airflow as lower controller-tuning priorities unless synchronized evidence
shows a candidate changes them. After selecting and close-capturing a finalist, move the mic once
to the bed and compare the restored golden image against the still-volatile finalist. Use the
camera microphone only as an optional synchronization track, never as acoustic comparison evidence.
Preserve the qualified image until a candidate repeats the release checks. The ordered contract is in
[loaded-tuning-2026-08-21.md](../testing/loaded-tuning-2026-08-21.md).

## Remaining Roadmap

1. **Synchronized loaded tune:** after the OWON arrives, capture the untouched golden baseline,
   then compare acoustic and startup candidates with dedicated-mic audio, SOX/electrical frames,
   telemetry, Hall/FG, Kasa power, and selective camera video. The camera is for startup, contact,
   and rotor-position evidence; its microphone is synchronization-only. Keep the dedicated mic at
   the close position until a finalist exists, then move it once for the final bed-position A/B.
2. **Final Hall-board mount:** make the cleaner permanent bracket, then repeat physical retention,
   gap, hand-rotation pulse, and driven Hall/FG agreement checks (`TACH-03B`).
3. **Owner-led finish:** Michael will artfully create the two-motion cosmetic housing specified in
   [housing.md](housing.md) and the printed conduit for the power cable. Aesthetic form and detailed
   CAD remain owner-controlled; the repo retains acoustic, thermal, sensing, clearance, retention,
   and cable-routing interfaces.

## Candidates Not Chosen

- **Lubricating before diagnosis:** deferred. The intermittent chirp may be bearing, contact,
  structural, or commutation-related; correlate it with rotor angle, drive state, and SOX before
  intervening.
- **Camera as a mandatory steady-speed observer:** rejected. Hall/FG already cover stability; use
  video only where startup motion, reversal, contact, or rotor-position correlation adds evidence.
- **Separate microphone-only tuning pass:** rejected after the microphone arrived. A short setup
  shakedown is fine, but the fan is already usable and the scope is only about seven days away, so
  one baseline-first synchronized batch avoids duplicated setup and ambiguous causal conclusions.
- **Loaded tuning on an improvised bench rig:** rejected. The installed ceiling assembly is the
  actual support, rotor load, cable, acoustic, and airflow environment.
- **Replacing the golden image directly from loaded MPET:** rejected. Preserve the qualified image
  as the A/B reference and promote only a fully repeated candidate.

## Learned Recently

- Provisional delayed-away, manual-override, vacation, and gated comfort automation behavior:
  [home-automation.md](home-automation.md).
- Loaded commissioning, persistence proof, owner acoustic observations, and the next candidate
  order: [loaded-tuning-2026-08-21.md](../testing/loaded-tuning-2026-08-21.md).
- Apple Home uses `PercentCurrent` for the interactive slider, so it must mirror the requested
  target rather than the physical ramp: [controls.md](controls.md).
- Microphone placement, conditional camera use, and scope/audio synchronization:
  [observability.md](observability.md).
- Retained unloaded tuning and acoustic baseline:
  [unloaded-tuning-2026-08-20.md](../testing/unloaded-tuning-2026-08-20.md).
