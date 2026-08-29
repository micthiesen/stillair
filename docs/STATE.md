# State

Fast-moving work state and chosen next step. Durable findings live in the linked design,
commissioning, BOM, and test documents.

Last updated: **2026-08-28** (JLCPCB quality complaint submitted for replacement PCB-01 U2 USB failure.)

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
- **The replacement PCB-01 has passed its unpowered hand-population checks and basic power rails.** C34 continuity to
  U8 pin 2 and AGND passed with no short. U8's +12V_TACH, AGND, VTACH, and intentional internal-net
  connections passed continuity checks, and +12V_TACH did not short to AGND. At 18 V with a 0.25 A
  limit, input current settled near 0.023 A, TP5 was 3.328 V, TP25 was 2.480 V, and ESP_EN was about
  3.3 V. Native USB still produced no macOS enumeration after known cables, connector orientations,
  forced ROM boot, Mac restart, and J6 pin reflow. R20/R21 each measured about 21 Ohm with no data-line
  short. U2's hidden USB joints or U2 itself remain the leading fault; UART0 on J7 is the fallback.
  `firmware/scripts/check_board_usb.py` is the authoritative permission-independent recheck. A DSD
  TECH SH-U09C2 FT232RNL USB-UART adapter is ordered. Fast domestic TC2030 cables were unavailable;
  the fallback is a lightweight prewired 6-pin JST-SH pigtail soldered once to J7 pins 2-6, with J7.1
  (board 3V3) deliberately left disconnected and the cable strain-relieved before use.
- **A JLCPCB PCBA quality complaint is pending for the replacement board's U2 USB failure.** The
  complaint was submitted on 2026-08-28 at 19:39:21 against SMT job
  `SMT026073063521-12177845A` in order `W2026073105230212`. It identifies one defective U2 as a
  component-function failure, not owner-repairable, with the design conforming to the datasheet,
  and requests a replacement PCBA. Four board photos and `IMG_3587.mov` were attached. JLCPCB's
  independently reloaded result page showed `Submitted` / `Processing` and promised a response
  within 24 hours; the site displayed no separate case number.
- **PCB-01 probing is now a retained, board-verified workflow.** [`probing.md`](probing.md) and
  `pcb/pcb-01/probe-map.json` contain component-relative locations for all 28 test points, connector
  pin views, ground domains, expected readings, one-probe-at-a-time instructions, and temporary
  pigtail criteria. `pcb/tools/probe_guide.py` prints the exact hookup/report contract and verifies
  the retained map against the board file.
- **TP4 detached only on the failed PCB-01.** Its AGND ring broke during the initial unpowered
  resistance checks on 2026-08-28. TP4 on the replacement board is intact, accessible, and valid
  for bench checks. Installed tuning leads still use TP26 by default because it is near USB/J8.
- **The fixed tuning leads are installed with physical colors that override earlier draft colors:**
  J8.9 SOX is black, TP20 FG is yellow, and TP26 AGND is blue. OWON CH1 remains on SOX, CH2 remains
  on FG, and both common grounds use TP26 for the entire unloaded and loaded tuning campaign. Do not
  move or rewire the scope during tuning.
- **The failed PCB-01 remains quarantined with apparent MCF internal-rail shorts.** With USB and
  24 V removed, VM24-to-PGND measured 30--40 MOhm and board 3V3-to-AGND measured about 900 MOhm,
  while MCF_AVDD measured about 5 Ohm and MCF_DVDD about 3 Ohm to AGND. Do not power the failed
  board. C14/C15 removal remains the optional conclusive postmortem; it is not part of replacement
  board qualification.
- **The physical goal is paused until the replacement board qualifies and Michael resumes it.** No
  blind acoustic or performance iteration should run meanwhile. With Michael watching a
  clear fan and holding the cutoff, bounded flashing and commissioning checks remain authorized if
  they do not claim missing evidence and the currently active provisional firmware is restored
  afterward.

## Next

Qualify the replacement PCB-01 beside the fan before reinstalling it. Use a current-limited 24 V
source for a brief no-motor check: establish input current and TP5 3V3, verify TP7 MCF_AVDD and TP8
MCF_DVDD, confirm ESP enumeration and MCF communication, and verify the active provisional firmware.
If those pass, connect the motor and perform the next unloaded start with the normal safety chain and
Michael watching the clear assembly. Do not begin tuning or return the board overhead until this
unloaded qualification passes.

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
