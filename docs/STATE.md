# State

Fast-moving work state and chosen next step. Durable findings live in the linked design,
commissioning, BOM, and test documents.

Last updated: **2026-08-20** (restrained unloaded motor tuning and endurance.)

## Now

- **Fabrication, procurement, blade-root qualification, PCB hand population, harnesses, and
  the owner-managed ceiling work are complete.** MP-100, all three ST-100 standoffs, and the
  SP-100 spindle are installed. Tether and catcher work are owner-reported complete and must
  not be reopened or managed here. BP-100 manufacturing and MEC-01/02/02B passed. Remaining
  physical installation belongs to Michael.
- **PCB-01 and PCB-02 are powered and integrated.** The 18 V no-motor bring-up, all measured
  rails, ESP flashing, sustained MCF software-I2C transport, no-motor permission/fault revoke,
  Hall harness polarity, physical magnet switching, and live Hall telemetry passed. Wiring
  conventions remain in [electrical.md](electrical.md) and the harness records.
- **Factory-default motor operation is now correctly blocked.** The first connected command
  entered implicit MPET because R/L/Ke and speed PI were zero. Only `provisional` or `verified`
  configuration may run. `config stage` writes and read-back-verifies the reviewed unloaded
  image in volatile shadow without issuing an EEPROM commit; a power cycle returns to
  `unverified` SafeBoot.
- **Restrained unloaded tuning is complete.** The selected volatile image uses double align,
  0.5 A open loop, manual handoff at 18 RPM nominal, Ke `0xC0`, Kp 0.008, Ki 0.0016, 25 kHz
  PWM, and a read-back-verified 0.25 A acquisition to 0.125 A settling to 0.25 A running
  current profile. Startup,
  handoff, 35–170 RPM, both directions, four repeated starts/stops, descending commands, and
  normal floor-to-coast stopping all passed without faults.
- **Objective top-speed endurance passed on the intended 24 V supply.** Ten minutes at
  170 RPM had zero fault, stall, or reversal; endpoint Hall/FG were 170.940/171.597 RPM.
  Mean wall draw was 2.8077 W, maximum 2.882 W, and the last minute was 0.0085 W below the
  first. Matched-speed audio selected 25 kHz: the former 3.36 kHz whine fell to the room
  floor without the stronger audible tone introduced by 20 kHz. Full results and rejected
  candidates are in [unloaded-tuning-2026-08-20.md](../testing/unloaded-tuning-2026-08-20.md).
- **The reusable harness is in place.** `firmware/scripts/08-flash-and-unloaded-profile.sh`
  coordinates firmware, volatile staging, serial telemetry, Kasa Utility Plug power logging,
  IR video, physical rotor tracking, an explicit camera-to-motor time offset, fail-closed
  plateau scoring, and independently verified plug cutoff. The retained profiles
  cover startup, forward/reverse ladders, repeated starts, acoustic comparison, precise Hall
  timing, and 170 RPM endurance.
- **No unloaded configuration has been committed to EEPROM.** `IMAGE` remains empty on
  purpose. Loaded MPET and final-rotor tuning remain separate future gates; the current work
  freezes only the best unloaded volatile image.

## Next

Freeze the completed unloaded campaign: run full host/target/Python verification and the
requested ultracheck, fix surviving findings, then commit and push the qualified image,
harness, and retained evidence. Loaded MPET and loaded tuning remain a separate later gate.

## Candidates Not Chosen

- **EEPROM commit**: not for the unloaded image. Commit only the reviewed loaded golden image.
- **More current to cure 170 RPM at 19.4 V**: rejected by live diagnostics; voltage, not
  current authority, is the limiting factor.
- **EB-100 PCB-bracket CAD**: defer until Michael explicitly resumes that owner-managed work.

## Future Only On Explicit Request

Do not suggest, schedule, or use these as blockers unless Michael explicitly asks to resume
one: ENC-100 cosmetic housing, TEMP_SENSE firmware, intentional-imbalance testing, exhaustive
start matrices, exhaustive acoustic testing, network/Matter resilience testing, and exhaustive
fault permutations. Installation, tether, catcher, and PCB bracket work are owner-managed and
must not be surfaced as project tasks.
