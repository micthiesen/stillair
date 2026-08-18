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

`02-mpet-and-capture.txt` prints the raw extraction result and then a paste-ready configuration
image. Review that capture before committing or applying it. MPET itself updates shadow
registers only and does not spend an EEPROM cycle.

The current 35 RPM first rung is the design target, not a qualified motor number. If the real
motor cannot start or run smoothly there, stop and raise the released minimum before continuing
the ladder. Do not edit firmware merely to make a script pass against an unsuitable provisional
number.
