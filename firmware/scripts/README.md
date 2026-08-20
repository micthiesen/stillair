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

`08-flash-and-unloaded-profile.sh` builds, flashes, power-cycles, stages the volatile image,
and runs one of those profiles. `STILLAIR_CAMERA_URL` is required for synchronized recording
and physical-motion analysis. The credential-bearing URL is fed to FFmpeg through a private
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
Every run stages and read-back-verifies the volatile MCF image; `STILLAIR_SKIP_FLASH=1` skips
only the ESP build/flash and is therefore safe after a fan-supply power cycle. Timestamped dwell
profiles also align their camera motion and 1 Hz AC power samples to the same motor timeline, so
`analyze_profile_plateaus.py` and `analyze_profile_power.py` report physical regulation and input
power for the same settled windows. Use
`utility-plug.sh status|on|off|cycle` for manual control and `utility-plug.sh log --for SECONDS`
for 1 Hz AC voltage/current/power evidence. The controller runs inside the Boris Homebridge
container, where Kasa credentials already live, refuses any device other than the pinned Utility
Plug identity and address, and reconnects boundedly after transient TPAP failures without running
periodic rediscovery through an active evidence stream.

Before the golden image exists, script 03 begins with `config stage`. This loads and
read-back-verifies the reviewed GL100 first-spin settings in volatile shadow only. It must be
repeated after every motor-power cycle, and it never commits EEPROM. A fresh unverified
controller remains in `SafeBoot`; this prevents zero factory speed-loop gains from invoking
implicit MPET on an ordinary run command. Script 02 remains on hold until the volatile image
has also been reviewed for loaded MPET.

Scripts 04 through 06 are loaded release tests. They begin with `config check` and require the
committed golden image; staging the provisional image there would overwrite loaded tuning.

`02-mpet-and-capture.txt` prints the raw extraction result and then a paste-ready configuration
image. Review that capture before committing or applying it. MPET itself updates shadow
registers only and does not spend an EEPROM cycle.

The current 35 RPM first rung is the design target, not a qualified motor number. If the real
motor cannot start or run smoothly there, stop and raise the released minimum before continuing
the ladder. Do not edit firmware merely to make a script pass against an unsuitable provisional
number.
