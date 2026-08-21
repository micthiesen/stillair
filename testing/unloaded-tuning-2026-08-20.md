# Unloaded motor tuning, 2026-08-20

This is the retained evidence for the restrained bare GL100 commissioning campaign. The motor
area was clear and continuously monitored with an immediate physical cutoff. A 30 fps IR camera
tracked the unique radial arm while precise Hall edge timing, MCF FG, and Kasa wall power were
logged concurrently. Hall is the shaft-speed authority above 140 RPM: the flexible outer
magnet/tape stick and even the inner optical line have orientation-specific tracking slips at
high speed. The camera remains the independent authority for gross motion, direction, stalls,
and synchronized audio. Earlier 19.4 V DPS-150 results remain below as supporting history.

## Best provisional configuration

These values are the best **unloaded** volatile image. They are not the loaded golden image and
have not been committed to MCF EEPROM. The complete setting table is frozen in firmware as
`mcf_config::UNLOADED_IMAGE`. Loaded tuning must use a separate candidate constant so this
baseline remains available for A/B comparison and regression diagnosis.

| Function | Selected value | Evidence |
|---|---:|---|
| Phase resistance / inductance | `0xB1` / `0xAE` | Vendor line-line values converted to star phase values; loaded measurement still wins. |
| BEMF constant | `0xC0`, 210 mV/electrical-Hz | TI Table 7-4 nearest value to synchronized live estimates: 211.5 at 100 RPM and about 207–211 at 140 RPM on 24 V. |
| Startup | double align, 750 ms, 1 A align | Deterministic on the low-inertia bare rotor; only small positioning ticks. |
| Open-loop ramp | 0.5 A, 1 electrical-Hz/s | Smooth acquisition and repeatable manual handoff in both directions. |
| Handoff | manual 10% of stored maximum (18 RPM nominal), 0.15 degree/ms theta ramp | Repeated clean takeover in both directions. |
| Speed PI | Kp 0.008, Ki 0.0016 | Lower Ki, higher Kp, and Ke variants produced no camera-measured improvement. |
| Closed-loop current | 0.25 A acquisition, 0.125 A settling, 0.25 A running | Brief acquisition authority is retained until Hall confirms roughly 10 RPM. The lower settling ceiling prevents overshoot; firmware restores 0.25 A only after at least 35 RPM tracks within 5 RPM for 2 s. Every transition is read-back verified. |
| Closed-loop ramp | firmware-owned 1.5 mechanical RPM/s; MCF `CL_ACC` unlimited | Removing the duplicate MCF ramp leaves one deterministic acceleration owner. |
| PWM frequency | 25 kHz | Former 3.36 kHz whine falls to the room floor at 160/170 RPM without the stronger 1.36 kHz tone seen at 20 kHz. |
| Modulation | continuous SVM, dead-time compensation enabled | TI's acoustic guidance; the first 24 V ceiling run exposed severe hunting and audible crackle with compensation accidentally left at reset zero. |
| Stored maximum | 180 RPM nominal (`0x0168`) | Still provisional pending the 24 V physical-ceiling ladder. |

`MOTOR_STARTUP1=0x22E60000`, `MOTOR_STARTUP2=0x110128AB`,
`CLOSED_LOOP2=0x0000B1AE`, `CLOSED_LOOP3=0x60000004`,
`CLOSED_LOOP4=0x50C20168`, acquisition/running `FAULT_CONFIG1=0x0AA84000`, and settling
`FAULT_CONFIG1=0x02A84000`. Bit 31 is the MCF's read-only parity indication and is not part of
the written value.

The selected modulation word is `CLOSED_LOOP1=0x3E01810C` (25 kHz, no inner acceleration
limit, AVS, and dead-time compensation). The earlier `0x00030108` word omitted
`DEADTIME_COMP_EN`; it is retained only as failed-run history and must not be staged again.

## Results on the intended 24 V supply

- Forward sampled Hall-period telemetry at 25 kHz measured 160.394 RPM with 0.314 RPM
  standard deviation and 170.289 RPM with 0.665 RPM standard deviation. MCF FG agreed within
  0.1 RPM and no fault
  appeared.
- The reverse 35/60/100/140/170 RPM ladder, descending 140/60 RPM commands, and normal stop
  passed. Camera plateaus through 140 RPM were within 1.7 RPM, with no stall or unintended
  direction change; Hall/FG qualified the high-speed plateau.
- Four more starts and stops passed, two per direction. The four 35 RPM camera errors were
  0.06 to 0.61 RPM, and steady wall draw was 1.51 W in either direction.
- Ten minutes at 170 RPM passed with zero fault, stall, or unintended reversal. Endpoint Hall
  was 170.940 RPM and FG was 171.597 RPM. Mean wall draw was 2.8077 W, maximum 2.882 W, and
  the last full minute was 0.0085 W below the first. The controlled stop reached `IdleOff`.
- PWM candidates were compared with matched-speed audio, Hall, FG, and wall power. At
  160/170 RPM, the high-frequency band was -25.97/-25.13 dB at 25 kHz versus -23.98/-16.26
  dB at 30 kHz and -12.25/-11.52 dB at 40 kHz. The 50 and 60 kHz candidates were still
  louder. 20 kHz was only 0.8 to 1 dB lower broadly but introduced a much stronger 1.36 kHz
  tone and left its switching fundamental at the edge of hearing, so 25 kHz was retained.
- Listening separated two sounds after the camera rig was made incapable of rubbing the
  motor: a faint steady winding/bearing-like machinery sound, and an intermittent cyclical
  electrical hum resembling GPU coil whine. The latter tracked the tunable spectral tones
  and was materially suppressed at 25 kHz; the former persisted as the unloaded mechanical
  baseline rather than being misclassified as commutation instability.

## Results at the 19.4 V bench limit

- Final 35 RPM startup: 35.675 RPM camera mean, 0.778 RPM rolling standard deviation, no
  reverse or stall, 82.92 mA peak input. The alignment tick is expected; acquisition and
  closed-loop takeover are continuous.
- Timestamped forward ladder physically measured 35.4, 60.6, 100.2 to 101.5, and about
  142 to 143 RPM after settling. Rising and falling plateaus were fault-free. A 170 RPM
  command was voltage-limited to about 153.4 RPM with 6.8 RPM variation; the MCF estimator
  still reported 170 RPM while q-axis voltage saturated. Raising current did not improve it.
- Reverse startup and the 35/60/100/140 RPM ladder passed. The first reverse normal-stop test
  exposed sensorless regulation being extended to 3 RPM; firmware now ramps only to the
  35 RPM released floor, commands zero/coast, and waits for verified stop. The hardware
  regression then returned cleanly to `IdleOff` with no MCF fault.
- Four complete starts and normal stops passed, two in each direction, with no fault or
  voltage sag and 83.57 mA peak input.
- Ten-minute 100 RPM endurance: 599 scored seconds, exact physical 100.776 RPM, zero stalls
  or reverse frames, and no minute-to-minute drift (100.62 to 100.94 RPM exact). Supply was
  19.400 V with zero sag; peak input was 82.65 mA and the steady input-current mean was about
  69.6 mA.
- Five-minute 140 RPM endurance: 299 scored seconds, exact physical 142.475 RPM, zero stalls
  or reverse frames, and no minute-to-minute drift (142.14 to 142.95 RPM exact). Supply was
  19.400 V with zero sag and peak input was 85.65 mA. This stable +2.5 RPM offset is not yet
  calibrated because 140 RPM is close to voltage saturation on the reduced bench bus.

The rolling camera-speed estimate includes line-detection noise (about 1.1 RPM at 100 and
2.2 RPM at 140); exact revolutions over each full plateau are the accuracy metric. Per-minute
exact averages show that neither run developed thermal drift or worsening physical jitter.

## Rejected candidates and conclusions

- Factory-zero R/L/Ke/speed PI entered implicit MPET and failed with `0x81000000`; an ordinary
  unloaded run must never be permitted from an unverified image.
- Static 0.25 A throughout closed-loop startup produced a large initial overshoot. The
  read-back-verified sequence retains 0.25 A only for initial observer acquisition, drops to
  0.125 A once Hall confirms roughly 10 RPM, and restores 0.25 A after stable 35 RPM tracking.
- Enabling `IQ_RAMP_EN` trapped later reference changes on this motor and was removed.
- Automatic handoff at the available BEMF thresholds and later manual handoffs either jumped
  or tripped abnormal BEMF. The selected 18 RPM manual transition is repeatable.
- Kp 0.012 did not improve synchronized physical regulation. An early `0xC0` Ke and Ki
  0.0008 trial at 19.4 V was acoustically inconclusive; the 24 V observer and 140 RPM hunting
  required both to be revisited independently. More current did not cure the 170 RPM
  reduced-voltage saturation.
- IPD was not used on the low-inertia bare rotor. Double align is deterministic without a
  saliency assumption; final loaded startup remains a separate observed decision.

## Conclusion

The restrained unloaded configuration is qualified across startup, handoff, 35–170 RPM,
both directions, repeated starts/stops, top-speed acoustics, and ten-minute top-speed
endurance. It remains a volatile unloaded image. Loaded MPET and loaded tuning are a separate
later gate and must not overwrite this evidence without a new qualification campaign.
