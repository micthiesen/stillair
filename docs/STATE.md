# State

Fast-moving work state and chosen next step. Durable findings live in the linked design,
commissioning, BOM, and test documents.

Last updated: **2026-08-21** (provisional operation complete; acoustic/startup refinement next.)

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
- **The remaining user-facing problem is acoustic and transitional.** Michael reports that the
  current tune is too loud above the bed, occasionally squeaks, and does not ramp smoothly from
  rest. Visible steady-state jitter is no longer material. These observations are recorded in the
  loaded-tuning report and `DRV-02`/`DRV-04` in
  [test-matrix.csv](../testing/test-matrix.csv).
- **A Home slider feedback hotfix is built and host-tested, but not yet flashed.** Both Matter
  percentage attributes now report the requested target instead of feeding intermediate ramp speed
  back into Apple Home, so a long press-and-drag remains continuously adjustable. The controller
  was not enumerating over USB after the build; installed-device validation remains open in
  `CTL-11`.
- **The next evidence stack is chosen.** Planned close 24-bit/96 kHz USB microphone audio, OWON
  VDS1022I SOX/electrical frames, Hall/FG, telemetry, and Kasa power share one timeline. Camera is
  conditional on startup/reversal, suspected contact, or a rotor-position-correlated squeak. The
  capture contract is in [observability.md](observability.md).

## Next

Flash and validate the Home slider hotfix on the installed controller, including an extended
press-and-drag while the fan is still ramping. Then run the full loaded acoustic and startup
refinement session: establish the current golden reference, localize the intermittent squeak before
considering lubrication, capture the align/open-loop/handoff current and motion, compare startup
candidates, then reduce steady-state motor/controller noise at matched measured speeds. Loaded MPET
is a measured comparison, not an automatic replacement. The ordered session contract is in
[loaded-tuning-2026-08-21.md](../testing/loaded-tuning-2026-08-21.md).

## Candidates Not Chosen

- **Lubricating before diagnosis:** deferred. The squeak may be bearing, contact, structural, or
  commutation-related; correlate it with rotor angle, drive state, and SOX before intervening.
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
