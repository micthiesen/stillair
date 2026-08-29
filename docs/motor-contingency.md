# Motor performance contingency

Defines how to decide whether the CubeMars GL100 KV10 is unsuitable, what evidence must be
preserved before changing it, and the lowest-disruption fallback paths. This is a contingency,
not a decision to replace the motor. The current baseline remains GL100 plus MCF8316D and must
finish loaded commissioning before a replacement path opens.

## Current baseline and success criteria

The GL100 is a 24 V, 20-pole-pair, star-wound gimbal motor with a 30 mm bore, 3.0 N m rated
torque at 130 RPM, 7.7 N m peak torque, 223 RPM published no-load speed, 2.650 ohm
line-to-line resistance, 2.350 mH line-to-line inductance, and 698 g mass. The installed
mechanics use its 106.8 x 34.2 mm envelope, 50 mm rotating M4 pattern, 60 mm stationary M4
pattern, bore, wire exit, and face ownership. [`parts.md`](parts.md) owns those interfaces.

The motor system is acceptable only when the final loaded rotor demonstrates:

- repeatable starts in both directions at every released speed and supply corner;
- stable operation throughout the released 35–170 RPM target range, or a deliberately
  raised released minimum supported by the test matrix;
- no identifiable motor/controller/bearing/structural tone at the released sleep speed;
- no fault, stall, reversal, current saturation, worsening jitter, or supply collapse;
- the required eight-hour 170 RPM thermal result, with RMS phase current normally below
  0.8 A, investigation above 1.0 A, motor below 70 degrees C, and the installed PCB-01 V1 below
  85 degrees C; PCB-01 V2 instead uses its separate 75 degrees C U2-area gate;
- clean stop, cutoff, windmilling restart, and reversal behavior; and
- preserved 180 RPM MCF ceiling and independently calibrated analog overspeed protection.

The exact release rows and sign-offs live in [`testing/test-matrix.csv`](../testing/test-matrix.csv).
The restrained unloaded campaign already passed 35–170 RPM in both directions, repeated
starts/stops, 25 kHz acoustic selection, and ten minutes at 170 RPM. Those results are in
[`testing/unloaded-tuning-2026-08-20.md`](../testing/unloaded-tuning-2026-08-20.md); they do
not substitute for loaded evidence.

## Do not misclassify the failure

“The motor is noisy” is not a diagnosis. Classify the symptom before buying hardware:

| Failure class | Distinguishing evidence | First response |
|---|---|---|
| Individual motor defect | Roughness or tone while unpowered and hand-turned; abnormal winding R/L symmetry; same controller/config behaves differently with another GL100 | Inspect bearings, fasteners, runout, phase symmetry, and if necessary A/B a second GL100 |
| Controller or tuning tone | Audio line moves with PWM frequency, observer gains, current waveform, modulation, dead-time compensation, or handoff settings | Continue bounded loaded tuning and correlate microphone with SOX/FG |
| Sensorless incompatibility | Repeatable handoff loss, angle/current discontinuity, low-speed stall, or load-sensitive hunting after R/L/Ke and current-loop values are verified | Bench the same motor on an independent MCF EVM, then consider a different control algorithm or rotor sensing |
| Insufficient torque or voltage authority | Duty or current saturates, measured speed falls under load, VM remains healthy, and the required torque exceeds the released limit | Confirm aerodynamic load and supply drop; then change rotor demand, current architecture, or motor |
| Thermal inadequacy | Temperature or current exceeds release limits at stable speed without a correctable mechanical rub or tuning defect | Confirm sensor placement and losses; reduce load/speed or select a more suitable motor |
| Bearing or structural path | Tone follows shaft speed rather than PWM/electrical frequency; runout, axial play, rubbing, or mounting sensitivity is measurable | Correct mounting, balance, clearance, or use the documented external-bearing torque-only coupling |
| Aerodynamic or room interaction | Tone/instability exists only with blades, changes with orientation/ceiling gap, and lacks corresponding current distortion | Treat as rotor/installation behavior, not a motor replacement trigger |

Use [`observability.md`](observability.md) for the required synchronized measurements. Do not
reject the GL100 from a microphone recording alone.

## Evidence required before opening a fallback

Freeze one reproducible failing profile and one known-good comparison profile. Preserve:

- complete MCF configuration and decoded fault registers;
- target, commanded, Hall, FG, duty, direction, and dropped-frame telemetry;
- SOX waveform with its configured gain and offset;
- VM24 waveform for any current, speed, cutoff, or supply-authority claim;
- matched-speed camera/audio and wall-power logs;
- load revision, blade orientation, balance/runout, supply/cable, ambient temperature, and
  motor temperature method;
- phase-to-phase resistance and inductance symmetry with the motor disconnected; and
- whether the symptom follows motor speed, electrical frequency, PWM frequency, load,
  direction, or a specific physical orientation.

A replacement decision should name the failed acceptance row and show that safe tuning space
was exhausted or that further tuning cannot address the observed failure class.

## Escalation order

### 1. Rule out an individual GL100 defect

This is the cheapest mechanically exact test. Inspect mounting preload, screw depth, rotor
rub, bearing feel, axial/radial play, phase connector contact, phase R/L balance, and BEMF
symmetry. If the evidence still points to the motor, test a second GL100 with the same
controller image and representative load before redesigning the drive or mechanics.

A like-for-like replacement preserves every machined interface, rotor plane, catcher path,
Hall bracket, firmware pole count, supply, and safety limit.

### 2. Isolate the custom board from the control algorithm

Use an **MCF8316DEVM** as a guarded bench diagnostic, not as an installed controller. TI's
[MCF8316DEVM](https://www.ti.com/lit/ug/sllu393/sllu393.pdf) uses the same MCF8316D class of
sensorless FOC, accepts 4.5–35 V, drives up to 8 A peak, and exposes Motor Studio through its
onboard interface MCU.

This test answers whether the symptom follows:

- the GL100 and MCF algorithm even with TI's known hardware/GUI path; or
- Stillair's PCB layout, register translation, firmware transport, supply path, or selected
  configuration.

It does not test an alternative commutation algorithm. If both boards reproduce the same
loaded symptom at equivalent settings, proceed to a genuinely different control path.

### 3. Bypass the MCF with a daughterboard while retaining the GL100

This is the preferred architectural contingency for controller-generated noise or a
sensorless mismatch because it preserves all completed mechanics. On the bench, unplug the
GL100 from PCB-01 J2 and connect its three phases to the daughterboard rather than cutting
traces or modifying the assembled controller.

Any daughterboard intended beyond diagnosis must provide:

- 24 V nominal operation with measured transient margin;
- at least the released 1.5 A continuous phase-current envelope and adequate startup peak;
- three-phase output, current measurement, direction, speed/torque command, and useful fault
  status;
- a hardware enable/Hi-Z input that the existing permission chain can revoke without
  firmware cooperation;
- stopped verification and a speed signal that the supervisor can cross-check against the
  independent one-pulse Hall;
- no automatic restart after fault or power restoration;
- configurable current, speed, acceleration, and regeneration limits; and
- a reviewed path that keeps the independent Hall-to-analog overspeed lock authoritative.

The existing PCB may remain the low-voltage power, ESP/Matter, physical-Hall, watchdog,
permission, and overspeed supervisor only if the new power stage cannot bypass those safety
functions. A bench module that requires software to stop is not an installable substitute.

#### Candidate daughterboard architectures

| Architecture | What it buys | Cost and risk | Position |
|---|---|---|---|
| DRV8316 plus motor-control MCU | Same 4.5–35 V, integrated-FET 8 A peak class, built-in current sensing, but full choice of sensored/sensorless FOC or sinusoidal control in firmware | New real-time motor firmware, current-loop validation, and safety integration | Leading compact path if the fixed MCF algorithm is the limitation. TI documents the [DRV8316](https://www.ti.com/product/DRV8316) as a 3x/6x PWM power stage for external control. |
| STSPIN32G4 plus external MOSFETs | Mature STM32G4 motor-control MCU, sensored or sensorless FOC, 5.5–75 V gate-driver range, strong diagnostic flexibility | Larger board, external FET power stage, highest firmware and hardware effort | Robust development fallback when maximum algorithm control matters more than compactness. See [STSPIN32G4](https://www.st.com/en/motor-drivers/stspin32g4.html). |
| MCT8316Z with three commutation Hall signals | Code-free, integrated-FET, sensored trapezoidal operation; removes sensorless estimation | Requires three valid rotor-position sensors and trapezoidal torque ripple may be more audible than FOC | Simpler electrical fallback, but acoustically lower priority. TI documents 4.5–35 V and 8 A peak for the [MCT8316Z](https://www.ti.com/product/MCT8316Z). |
| Commodity RC/robot ESC | Fast and inexpensive bench comparison | Usually optimized for much higher electrical speed, poorly documented low-speed startup, unclear regeneration, no compatible hard-disable contract | Diagnostic only unless its complete control and safety behavior is documented and qualified. |

Do not select a new IC merely because its evaluation board spins the unloaded motor. It must
pass the same loaded acoustic, startup, speed, thermal, cutoff, fault, and overspeed matrix.

### 4. Add rotor-position sensing if sensorless operation is the blocker

The existing PCB-02 Hall produces one pulse per mechanical revolution. It is an independent
tachometer and overspeed input, **not** a commutation sensor. Sensored trapezoidal or sensored
FOC requires either:

- three Hall states correctly phased to the motor's electrical angle; or
- a sufficiently resolved absolute/incremental encoder with a qualified index/alignment
  procedure.

The GL100 has 20 pole pairs, so 120 electrical degrees corresponds to 6 mechanical degrees,
but that conversion does not define a workable Hall placement by itself. External leakage
field, sensor radius, polarity, hysteresis, mounting tolerance, and phase sequence must be
mapped experimentally. An encoder may be cleaner electrically but competes with the central
bore, rotating hub, and non-contact catcher. Either route is a mechanical and safety change,
not a firmware-only modification.

### 5. Replace the motor architecture

Only open this path if the GL100 itself fails torque, thermal, bearing, or acoustic
requirements, or if every acceptable drive path requires disproportionate complexity.

#### Replacement motor requirements

A candidate must document or demonstrate:

- 24 V operation and a winding naturally suited to approximately 35–170 RPM without flux
  weakening;
- at least 1.0 N m continuous torque across the released upper-speed region, with measured
  margin over the final rotor demand;
- low cogging and sinusoidal-drive compatibility appropriate for sleep acoustics;
- phase resistance, phase inductance, BEMF/Kv, pole pairs, current, torque-speed curve,
  temperature limit, and rotor inertia;
- compatible or adaptable stationary and rotating interfaces, wire exit, total axial
  envelope, and a through-bore or alternate independent catcher path;
- bearing arrangement, continuous axial/radial load, overturning moment, and retention basis
  appropriate to a hanging rotor; and
- either proven low-speed sensorless behavior or a documented position-sensor interface.

Avoid selecting by rated torque alone. High-Kv motors can meet torque only by requiring much
more current at the same slow direct-drive operating point, increasing copper loss and making
quiet low-speed control harder.

#### Known mechanical fallback: CubeMars GL80 KV30

The GL80 remains a documented comparison, not a drop-in replacement. CubeMars publishes
24 V, 1 N m rated torque, 0.356 N m/A torque constant, 21 pole pairs, 87 x 22.3 mm envelope,
and 30 Kv class operation. At the estimated 0.7–0.8 N m rotor load it needs roughly
2.0–2.25 A plus losses, versus roughly 0.68–0.78 A for the GL100. That exceeds the present
1.5 A released current architecture and sacrifices the GL100's natural speed match.

Using it would require concentric stationary and rotating adapters or new MC-100/RH-100
revisions, new motor parameters and FG conversion for 21 pole pairs, current/thermal
requalification, wire/connector review, and renewed catcher/clearance/runout proof. Its
smaller size and mass are real benefits, but it is not the quietest low-risk electrical
fallback.

An integrated ceiling-fan motor/driver assembly may be acoustically proven and simpler as a
product, but it is likely to force a new hub, carrier, vertical stack, safety interface, and
control strategy. Treat it as a new fan architecture rather than a daughterboard swap.

## Change-impact checklist

Before buying any non-identical motor or installable driver, disposition every affected
interface:

| Area | Required review |
|---|---|
| Mechanics | MC-100, RH-100, rotor plane, housing, wire exit, fasteners, runout, balance, Hall bracket, bearing load, catcher clearance, tether-retained mass |
| Electrical | Supply power, fuse, connector/contact current, VM transients, phase wiring, current sensing, thermal sensing, EMI, board thermals |
| Control | R/L/Ke, pole pairs, FG scaling, startup/handoff, direction, speed ramps, current/speed limits, stop, reversal, windmilling |
| Safety | Hardware permission revoke, fault latching, power-restoration-off, independent Hall/analog overspeed, physical cutoff, regeneration |
| Qualification | Full loaded start matrix, acoustic ladder, endurance, thermal, cutoff, fault, overspeed, rotor proof, and installed clearances |

No replacement inherits the GL100's qualification results merely because it fits an adapter.

## Decision record template

When a contingency is opened, add a dated section to this document containing:

1. Failed acceptance row and reproducible profile.
2. Evidence bundle paths and exact hardware/configuration.
3. Failure classification from the table above.
4. Corrective tuning or mechanical checks attempted and their outcomes.
5. Selected fallback, why lower-disruption paths failed, and affected interfaces.
6. New qualification rows or limits required before release.

Until such a record exists, the selected system remains GL100 plus MCF8316D.
