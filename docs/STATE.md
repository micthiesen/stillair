# State

Fast-moving work state and chosen next step. Durable findings live in the linked design,
commissioning, BOM, and test documents.

Last updated: **2026-08-21** (provisional operation complete; microphone-first refinement next.)

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
- **The remaining work is finite and ordered.** A microphone-only tune comes first when the mic
  arrives, followed by a scope-assisted electrical refinement when the OWON arrives in roughly one
  to two weeks. Then Michael will make a cleaner Hall-board mount and verify the sensor again before
  completing the owner-designed cosmetic housing and printed power-cable conduit.

## Next

Run the microphone-first loaded tune. Record the current golden reference at the close motor and bed
positions, separate steady electrical whine from transient chirps, and use synchronized Hall/FG,
telemetry, Kasa power, and selective video to compare conservative acoustic and startup candidates.
Preserve the qualified image until a candidate repeats the release checks. The ordered session
contract is in
[loaded-tuning-2026-08-21.md](../testing/loaded-tuning-2026-08-21.md).

## Remaining Roadmap

1. **Microphone-first loaded tune:** use the 24-bit/96 kHz mic as soon as it arrives. Set up a
   camera for rough startup and possible rotor-position correlation of chirps; Hall/FG remain the
   steady-speed authority, so video need not accompany every plateau.
2. **Scope-assisted refinement:** when the OWON VDS1022I arrives, correlate SOX/electrical frames
   with the retained audio signatures, telemetry, Hall/FG, and power. Revisit the first-pass tune
   only where the electrical evidence supports a better candidate, then qualify the final image.
3. **Final Hall-board mount:** make the cleaner permanent bracket, then repeat physical retention,
   gap, hand-rotation pulse, and driven Hall/FG agreement checks (`TACH-03B`).
4. **Owner-led finish:** Michael will artfully create the cosmetic housing and printed conduit for
   the power cable. Their design details stay outside this project; record only completion and any
   final fan-clearance, retention, or cable-routing verification that affects operation.

## Candidates Not Chosen

- **Lubricating before diagnosis:** deferred. The intermittent chirp may be bearing, contact,
  structural, or commutation-related; correlate it with rotor angle, drive state, and SOX before
  intervening.
- **Camera as a mandatory steady-speed observer:** rejected. Hall/FG already cover stability; use
  video only where startup motion, reversal, contact, or rotor-position correlation adds evidence.
- **Loaded tuning on an improvised bench rig:** rejected. The installed ceiling assembly is the
  actual support, rotor load, cable, acoustic, and airflow environment.
- **Replacing the golden image directly from loaded MPET:** rejected. Preserve the qualified image
  as the A/B reference and promote only a fully repeated candidate.

## Learned Recently

- Loaded commissioning, persistence proof, owner acoustic observations, and the next candidate
  order: [loaded-tuning-2026-08-21.md](../testing/loaded-tuning-2026-08-21.md).
- Apple Home uses `PercentCurrent` for the interactive slider, so it must mirror the requested
  target rather than the physical ramp: [controls.md](controls.md).
- Microphone placement, conditional camera use, and scope/audio synchronization:
  [observability.md](observability.md).
- Retained unloaded tuning and acoustic baseline:
  [unloaded-tuning-2026-08-20.md](../testing/unloaded-tuning-2026-08-20.md).
