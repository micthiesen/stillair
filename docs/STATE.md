# State

Fast-moving work state and chosen next step. Durable findings live in the linked design,
commissioning, BOM, and test documents.

Last updated: **2026-08-28** (PCB-01 removed for bench diagnosis after MCF communication loss.)

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
- **The remaining work is finite and ordered.** The microphone, OWON, Kasa plug, Ubiquiti camera,
  and ESP are connected through the commissioning setup. Rather than duplicate setup, acoustic and
  electrical tuning will run as one instrumented batch, beginning with an untouched-golden baseline.
  Source tuning happens on the exposed assembly; the decided 2 mm butyl/film motor and upper-housing
  damping is installed afterward as a passive improvement and verified without changing the tune.
  Michael will then make a cleaner Hall-board mount and complete the owner-designed cosmetic housing
  and printed power-cable conduit.
- **The final loaded tune is authorized to run autonomously.** When Michael says `next`, `begin the
  loaded tune`, or equivalent, that is the launch signal and confirms that the room is clear, he is
  continuously watching, and the immediate physical cutoff is available. Codex may control the fan,
  power cycle through the available control path, flash firmware, stage volatile MCF settings, run
  scripts, and use the connected instruments without routine permission prompts. Existing hardware
  protections and the released 50--170 RPM envelope remain mandatory.
- **The fail-closed baseline runner is prepared.** `firmware/scripts/09-run-loaded-profile.sh`
  validates the 50--170 RPM profile, requires the EEPROM-verified golden image, fixed microphone,
  OWON, camera, Hall/FG, telemetry, and Kasa evidence, and emits a hashed run manifest. Dry-run and
  simulated acquisition checks pass. Static preflight on 2026-08-28 qualified the USB hub, Kasa,
  VDS1022I frame capture, FG probe, fixed 24-bit/96 kHz microphone, and the private Ubiquiti RTSP
  path. It corrected the 5 V scope offset from 0.5 to 0.2 so 3.3 V FG no longer clips. Dynamic SOX,
  FG, camera-guard, and cross-source timing checks remain open because the installed firmware could
  not read the MCF8316D during the preflight; confirm the physical controller-power path before any
  motion. `10-run-loaded-candidate.sh` now provides matched, hashed runs
  for named PWM-frequency, dead-time-compensation, and gate-slew candidates. Each operation restores
  the complete golden base, changes one reviewed field in volatile shadow, verifies preserved bits,
  uses a distinct `tuning` verdict that cannot activate unloaded-only current behavior, and has no
  EEPROM commit path. Host simulation, all-candidate readback tests, and the app build pass; this
  firmware has not yet been flashed to the installed controller. Arbitrary raw register writes
  remain non-runnable.
- **PCB-01 is down on the bench and must be diagnosed before tuning resumes.** During instrument
  preflight, the ESP booted but the MCF8316D returned address NACK after the built-in wake pulse,
  recovery-address scan, explicit `fault clear`, and an extended full power removal. This began
  before a later visible spark while J8 was being cleaned, so the spark does not explain the
  original MCF loss but may have added damage. The board is now clean, discharged, and connected
  only to data-only USB, which cannot power or enumerate the ESP by itself. Do not reapply ordinary
  24 V until unpowered short checks pass; then use a current-limited bench supply and verify rails
  before attempting firmware communication.
- **PCB-01 probing is now a retained, board-verified workflow.** [`probing.md`](probing.md) and
  `pcb/pcb-01/probe-map.json` contain component-relative locations for all 28 test points, connector
  pin views, ground domains, expected readings, one-probe-at-a-time instructions, and temporary
  pigtail criteria. `pcb/tools/probe_guide.py` prints the exact hookup/report contract and verifies
  the retained map against the board file.
- **TP4 is physically unavailable on this V1 board.** Its AGND test-point ring detached during the
  initial unpowered resistance checks on 2026-08-28. Do not probe, solder, or attach a pigtail to
  TP4. The retained map and generated instructions now use TP26 as default AGND and TP28 as backup.
- **Unpowered measurements localize the communication failure to the MCF internal rails.** With USB
  and 24 V removed, VM24-to-PGND measured 30--40 MOhm and board 3V3-to-AGND measured about 900 MOhm,
  ruling out hard shorts on the input and main logic rail. MCF_AVDD at TP7 measured about 5 Ohm to
  TP26 AGND and buzzed in both polarities; MCF_DVDD at TP8 measured about 3 Ohm to TP26. Two shorted
  MCF-generated rails make U1 internal damage much more likely than one failed bypass capacitor.
  Do not power the board. Before replacing U1, remove C14 and C15 while unpowered and remeasure TP7
  and TP8 to exclude the two rail bypass capacitors conclusively.
- **The physical goal is paused until the full observability suite is available and Michael resumes
  it.** No blind acoustic or performance iteration should run meanwhile. With Michael watching a
  clear fan and holding the cutoff, bounded flashing and commissioning checks remain authorized if
  they do not claim missing evidence and the currently active provisional firmware is restored
  afterward.

## Next

Repair PCB-01 on the bench before any installed work or tuning. Keep it unpowered; remove C14 and
C15 and remeasure TP7/TP8 to distinguish bypass-capacitor shorts from the leading U1 internal-failure
diagnosis. Replace U1 if either short remains with its bypass capacitor absent. After repair, use a
current-limited 24 V bench source, establish input current and TP5 3V3, then verify TP7 MCF_AVDD and
TP8 MCF_DVDD before interpreting I2C. Do not return the board overhead until the ESP enumerates, the
MCF responds, configuration verifies, and a stopped no-motor bench soak passes.

After the controller is healthy, the remaining observability tools are present, and Michael
explicitly resumes the goal, run the autonomous synchronized loaded-tuning batch on the exposed assembly.
Mount the dedicated microphone independently, close to the motor but just outside the future housing
envelope, so it can remain fixed for the entire sequence. Hook up and qualify scope, Hall/FG,
telemetry, Kasa power, and selective camera capture once; then record the untouched golden reference
before changing a controller setting. Diagnose and optimize chirps, rough startup/handoff,
electrical/commutation tones, regulation, current waveform, and avoidable power loss until further
safe changes produce no measurable improvement. Promote nothing until the finalist repeats the full
applicable release checks. After the exposed finalist is captured, install the decided damping and
completed housing without changing the tune or mic, then repeat the close-mic acoustic ladder and
final mechanical/thermal checks. No formal bed-position recording is planned; Michael's listening
from bed is the final subjective check. The ordered contract and autonomy boundaries are in
[loaded-tuning-2026-08-21.md](../testing/loaded-tuning-2026-08-21.md).

## Remaining Roadmap

1. **Autonomous synchronized loaded tune:** after the OWON arrives, qualify one fixed instrumentation
   setup, capture the exposed untouched-golden baseline, and exhaust meaningful startup, acoustic,
   regulation, waveform, and efficiency candidates. Freeze only the best repeatable result, then
   validate the passive damping and completed housing with the same fixed close microphone.
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
- **Damping and housing before source tuning:** rejected. The exposed assembly provides the clearest
  diagnostic signal; passive treatment follows the frozen source-level finalist and is verified as
  an additional improvement without changing the controller configuration.
- **Formal bed-position microphone A/B:** rejected. Moving the only dedicated microphone weakens the
  complete-sequence comparison; keep it close and fixed, then use Michael's direct listening from
  bed for the final user-facing judgment.
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
