# Commissioning scripts

Build the host harness once, then run each file against the same long USB harness used for
bench or ceiling work:

```sh
cd firmware
cargo build
target/debug/stillair --port /dev/cu.usbmodem2101 script scripts/01-board-smoke.txt
```

The numbered release scripts 01 through 06 remain the normal commissioning flow. The retained
unloaded-tuning profiles are evidence-oriented bench tests:

- `18-unloaded-startup-camera.txt`: one complete 35 RPM start, hold, and normal stop.
- `22-unloaded-timestamped-ladder.txt`: both rising and falling speed plateaus.
- `23-unloaded-reverse-ladder.txt`: reverse startup, range, and normal stop.
- `25-unloaded-start-repeatability.txt`: two complete starts and stops per direction.
- `26-unloaded-100-endurance.txt`: ten-minute continuous midrange hold.
- `27-unloaded-140-endurance.txt`: five-minute upper-range hold for the 19.4 V bench source.
- `29-unloaded-100-estimator.txt`: known-stable 24 V observer/current reference point.
- `30-unloaded-24v-ceiling-diagnostics.txt`: guarded 100/140/160/170 RPM ladder with an
  observer/current sample at every rung.
- `31-unloaded-acoustic-threshold.txt`: guarded 100/120/130/140 RPM comparison used when a
  candidate changes high-speed commutation noise; it deliberately stops below 160 RPM.
- `32-unloaded-speed-pi-candidate.txt`: shorter 100/130/140 RPM A/B profile for iterating one
  speed-loop gain while retaining a stable reference and pre-threshold control.
- `33-unloaded-140-observer-onset.txt`: continuous q-axis/BEMF observer capture through the
  apparent 140 RPM optical-hunting onset; precise Hall timing later proved it was tracker slip.
- `47-unloaded-full-range-tach.txt`: 100/140/160/170 RPM plateaus with sampled Hall
  edge-period estimates and MCF FG as the shaft-speed authorities.
- `48-unloaded-pwm-acoustic-candidate.txt` and `49-unloaded-pwm-top-speed-candidate.txt`:
  matched-speed camera-audio, Hall, FG, and wall-power comparisons for PWM tuning.
- `50-unloaded-170-endurance.txt`: ten-minute worst-case unloaded hold at the user ceiling.

A failed command stops a file and returns non-zero. `wait speed` requires both the commanded
ramp and three consecutive FG samples in range, so merely crossing a setpoint does not count
as arrival. `dwell` requires a live 1 Hz telemetry heartbeat and a continuously running state
while an external camera and power logger gather the continuous evidence.

`08-flash-and-unloaded-profile.sh` is the common synchronized acquisition runner. Its default
`STILLAIR_CONFIG_MODE=stage` preserves the unloaded workflow: it builds, flashes, power-cycles,
stages the volatile image, and runs one of those profiles. `STILLAIR_CAMERA_URL` is required for
synchronized recording and physical-motion analysis. The credential-bearing URL is fed to FFmpeg through a private
file descriptor rather than exposed in its arguments or logs. The wrapper waits for a real
camera frame and a live Utility Plug power sample, retains camera audio when the stream provides
it, records the camera-to-motor offset, and fails if the camera, plug logger, controller
telemetry, tracking, or a relevant direction/stall/plateau gate fails. Optical speed is scored
through 140 RPM. Above that, repeatable orientation-specific tracker slips make precise Hall
edge timing and MCF FG the speed authorities while the camera remains the gross-motion guard.
Its deadline is
derived from the selected profile, so endurance profiles do not need a manual timeout override.
Any failed command releases the serial client, attempts controller disarm, then independently
switches off the exact Kasa `Utility Plug`; a successful run leaves the 24 V supply available.
An unloaded run stages and read-back-verifies the volatile MCF image. A loaded reference run uses
`STILLAIR_CONFIG_MODE=verified`, requires the stored golden image to verify, and refuses to replace
a failed baseline with a staged image. `STILLAIR_SKIP_FLASH=1` skips only the ESP build/flash.
Timestamped dwell
profiles also align their camera motion and 1 Hz AC power samples to the same motor timeline, so
`analyze_profile_plateaus.py` and `analyze_profile_power.py` report physical regulation and input
power for the same settled windows. Use
`utility-plug.sh status|on|off|cycle` for manual control and `utility-plug.sh log --for SECONDS`
for 1 Hz AC voltage/current/power evidence. The controller runs inside the Boris Homebridge
container, where Kasa credentials already live, refuses any device other than the pinned Utility
Plug identity and address, and reconnects boundedly after transient TPAP failures without running
periodic rediscovery through an active evidence stream.

`check-mcf-presence.sh` is the safe repeated check after connector cleanup or probing. It powers
the controller, holds one serial connection through boot, passes only when the MCF8316D answers the
firmware's wake-and-address scan, and returns Kasa power off on every exit. Override automatic board
port detection with `STILLAIR_PORT=/dev/cu.usbmodem...` when needed.

`check_board_usb.py` is the permission-independent native-USB check. It passes only when macOS's
live I/O Registry contains exactly one ESP32-C6 USB Serial/JTAG device (VID `0x303a`, PID `0x1001`)
continuously for 0.5 seconds. Serial `/dev` nodes are reported separately and do not decide the
enumeration result. Run it while connecting or resetting the board:

```sh
firmware/scripts/check_board_usb.py
```

Exit 0 means enumerated, 1 means not detected during the polling window, 2 means ambiguous or
unstable, and 3 means the host probe itself failed. A nonzero result never claims which hardware
element caused the failure.

For recovery or A/B work, script 03 begins with `config stage`. This loads and
read-back-verifies the reviewed GL100 first-spin settings in volatile shadow only. It must be
repeated after every motor-power cycle, and it never commits EEPROM. A fresh unverified
controller remains in `SafeBoot`; this prevents zero factory speed-loop gains from invoking
implicit MPET on an ordinary run command. Script 02 remains on hold until the volatile image
has also been reviewed for loaded MPET.

Scripts 04 through 06 are loaded release tests. They begin with `config check` and require the
committed golden image; staging the provisional image there would overwrite loaded tuning.

## Autonomous loaded reference

`09-run-loaded-profile.sh` is the fail-closed entry point for the first exposed loaded capture.
It validates the profile before connecting to hardware, forces verified-golden mode, and requires
the fixed dedicated microphone, OWON capture, camera motion guard, controller telemetry, physical
Hall/FG, and Utility Plug evidence. It defaults to `51-loaded-golden-baseline.txt`, which measures
50, 60, 80, 120, and 170 RPM and returns to verified `idle_off`. It will not accept `config stage`,
`config apply`, raw register writes, an out-of-range speed, an unsafe direction change, or a profile
that lacks a final stopped-state proof.

```sh
STILLAIR_DRY_RUN=1 scripts/09-run-loaded-profile.sh

STILLAIR_CAMERA_URL='rtsps://…' \
STILLAIR_SCOPE_ISOLATED_CONFIRMED=1 \
scripts/09-run-loaded-profile.sh
```

When `STILLAIR_CAMERA_URL` is unset, the runner reads the RTSP URL from
`${XDG_CONFIG_HOME:-$HOME/.config}/stillair/camera-url` or the path named by
`STILLAIR_CAMERA_URL_FILE`. Keep that file outside the repository and readable only by its owner.

The microphone defaults to the AVFoundation device name `Razer Seiren V3 Mini`; override
`STILLAIR_AUDIO_DEVICE` if the enumerated name differs. Audio is retained as mono 24-bit/96 kHz
WAV and analyzed at 48 kHz, preserving comparison bands through 20 kHz. The scope recipe defaults
to `scope-loaded-startup.json`: SOX and FG at 250 ksample/s in discrete 5,000-sample frames. Its
range, offset, ground references, and isolated VDS1022I model must be physically confirmed before
setting `STILLAIR_SCOPE_ISOLATED_CONFIRMED=1`. The capture uses the Python API from
`florentbr/OWON-VDS1022` pinned at commit `4c67805713906c20b4414b4225fd293adea4cb05`; it records
inter-frame arrival gaps and never describes the frames as continuous acquisition.

Each successful run prints a `run_dir` under `STILLAIR_EVIDENCE_ROOT` (default `/tmp`). Its
`manifest.json` records the git commit, timing anchors, configuration mode, file sizes, and SHA-256
hashes for every retained file, including each scope frame. A missing or malformed required source
fails the run. Both loaded wrappers require the repository to remain clean and on the same commit
for the complete run, so the recorded commit identifies the firmware source rather than merely the
latest nearby revision. The baseline entry point deliberately captures the untouched golden reference only. Loaded
candidate generation remains a separate tuning step.

After the untouched reference is secured, run one allowlisted golden-derived candidate with the
same evidence stack and matched ladder:

```sh
STILLAIR_DRY_RUN=1 scripts/10-run-loaded-candidate.sh pwm-30khz

STILLAIR_CAMERA_URL='rtsps://…' \
STILLAIR_SCOPE_ISOLATED_CONFIRMED=1 \
scripts/10-run-loaded-candidate.sh pwm-30khz
```

`10-run-loaded-candidate.sh` accepts `pwm-20khz`, `pwm-25khz`, `pwm-30khz`, `pwm-40khz`,
`pwm-50khz`, `pwm-60khz`, `deadtime-off`, `deadtime-on`, `slew-125v-us`, or `slew-200v-us`.
It verifies the stored golden image before evidence collection, then `config tune` restores that
complete image in volatile shadow, changes exactly the named reviewed field, rechecks the preserved
golden bits, and reports the distinct `config=tuning` verdict. The matched motor profile is
`52-loaded-acoustic-candidate.txt`. The run manifest records the candidate name, application time,
and device reply. No candidate path can commit EEPROM. Retain the golden run as the A/B control and
never promote a finalist until it repeats the release gates.

`02-mpet-and-capture.txt` prints the raw extraction result and then a paste-ready configuration
image. Review that capture before committing or applying it. MPET itself updates shadow
registers only and does not spend an EEPROM cycle.

The 35 RPM design target was rejected for loaded use after one arbitrary-position start rocked
without acquiring. The provisional released floor is 50 RPM; scripts that retain a 35 RPM bench
rung are unloaded evidence profiles, not the user operating contract.
