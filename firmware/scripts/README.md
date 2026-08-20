# Commissioning scripts

Build the host harness once, then run each file against the same long USB harness used for
bench or ceiling work:

```sh
cd firmware
cargo build
target/debug/stillair --port /dev/cu.usbmodem2101 script scripts/01-board-smoke.txt
```

Run them in number order when their hardware is available. A failed command stops the file
and returns a non-zero exit. `wait speed` requires three consecutive FG samples in range, so
crossing a setpoint during a ramp does not count as arrival. CSV-producing steps write to
stdout; redirect the whole run when you want to keep it.

Before the golden image exists, script 03 begins with `config stage`. This loads and
read-back-verifies the reviewed GL100 first-spin settings in volatile shadow only. It must be
repeated after every motor-power cycle, and it never commits EEPROM. A fresh unverified
controller remains in `SafeBoot`; this prevents zero factory speed-loop gains from invoking
implicit MPET on an ordinary run command. Script 02 remains on hold until the volatile image
has also been reviewed for loaded MPET.

Scripts 04 through 06 are release tests. They begin with `config check` and require the
committed golden image; staging the provisional image there would overwrite loaded tuning.

`02-mpet-and-capture.txt` prints the raw extraction result and then a paste-ready configuration
image. Review that capture before committing or applying it. MPET itself updates shadow
registers only and does not spend an EEPROM cycle.

The current 35 RPM first rung is the design target, not a qualified motor number. If the real
motor cannot start or run smoothly there, stop and raise the released minimum before continuing
the ladder. Do not edit firmware merely to make a script pass against an unsuitable provisional
number.
