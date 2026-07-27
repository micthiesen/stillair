# PCB handoff (V1 / V2 controller)

> **Temporary**: the original schematic-block and placement-zone diagrams are still viewable at
> https://stillair-fan-design.syas.chatgpt.site/electrical (requires ChatGPT auth). Remove this
> link once the KiCad schematic is captured.

Defines the V1 and V2 controller board for the CubeMars GL100 KV10. This is a circuit and
layout brief, not a released design: capture and peer-review the final schematic in
[`pcb/`](../pcb/) (KiCad), verify footprints, run ERC/DRC, and compare the MCF power stage
directly with TI's reference layout.

## Architecture

```text
GST60A24-P1J, 24 V / 2.5 A / 60 W
  -> 3 A source fuse -> physical cutoff -> 18/2 feed
  -> reverse PMOS -> SMCJ24A -> 2 x 470 uF / 50 V
       +-> MCF8316D -> GL100 phases U/V/W
       +-> TPSM365R6V3 -> 3.3 V -> ESP32-C6 + latch + watchdog + comparator
       +-> TPS7A1601A -> 12.049 V -> LM2907 analog tach

Rotor magnet -> DRV5033 -> LM2907 -> TLV1701
             -> hardware permission latch /CLR -> DRVOFF
```

The custom V1 board replaces the TI evaluation module. V1 is deliberately roomy and
instrumented (full USB, direct I²C, scope header, test pads, rework links, manual
clear/DRVOFF controls); V2 keeps the same outline and mounting holes and removes only
development features proven unnecessary.

## PCB-01 mechanical definition

- Outline: 78.0 × 58.0 mm, R3 corners.
- Construction: four-layer FR-4, 1.6 mm.
- Copper: 2 oz outer, 1 oz inner.
- Finish: ENIG.
- Mounting: four Ø3.2 mm NPTH at (6,6), (72,6), (6,52), (72,52) mm from the lower-left
  (66 × 46 mm hole rectangle). Keep all copper and components outside an Ø8 mm circle around
  each hole; use 6–8 mm M3 standoffs and leave the holes isolated from circuit ground.
- Keep V2 on the same outline and hole pattern. Do not shrink V2; the spare area buys thermal
  copper, probe access, connector clearance, and RF separation without changing the housing.

**Open V2 option — horizontal donut board.** Once the housing exists, V2 may instead become an
annular board mounted horizontally around the spindle, replacing the same-outline rule and the
EB-100 bracket entirely. Geometry that makes it viable: between the plate underside (Z6) and
the carrier top (Z144) the housing interior is a Ø194 cylinder that is empty except for the
Ø16 spindle, the three Ø16 standoffs at r75, the tether run near Y−82, and the cable drop. The
low-risk shape is ID Ø30–40 (generous non-contact clearance around the spindle) × OD ≤Ø130,
entirely inside the standoff circle — ~12,500 mm², nearly 3× the rectangle — leaving a wide
annular air path at the wall for the housing's ≥1200 mm² venting (a wider board with standoff
slots needs its own vent slots instead). Mount on three M3 bosses tapped into the MC-100
carrier top, which also puts J2 beside the motor's phase-lead window. Zones translate to
angular separation: MCF power stage at one clock position, tach/analog 120–180° away.

Open questions if pursued: RF first — the board sits sandwiched between the stainless plate
above and the carrier/motor below, so the ESP module goes at the outer rim, antenna facing
radially out through the plastic wall, clocked away from standoffs/tether, sitting mid-gap
(Z ~60–90) to keep the 15 mm metal clearance; verify with a real RSSI check. Connectors face
up/down, so all service means dropping the housing (acceptable for a dev-stripped V2).

The real cost: the V1→V2 plan inherits V1's validated layout, and a donut V2 is a new layout —
the layout-sensitive results (PCB-02 bus transients, TACH calibration/noise floor, thermal,
RF) need a partial re-run instead of being inherited. Decide only after V1 bring-up and a
housing prototype; V1 stays the rectangle regardless, and if the donut is chosen, delete
EB-100 from the parts register rather than carrying both.

**Fabrication**: boards will be ordered from JLCPCB. Whether JLCPCB also sources and
assembles the components (PCBA) or the board is hand-populated is TBD; check part
availability in the JLCPCB/LCSC catalog during KiCad capture so the decision stays open.

## SCH-01 24 V input

Source chain:

```text
GST60A24-P1J -> Switchcraft 721A -> 3 A ATO fuse
-> 5 A / 28 VDC cutoff -> Belden 5300UE 18/2 -> J1
```

The 18 AWG feed is good for a total source-to-board run of at most 20 ft (published 6.5
Ω/1000 ft gives about 0.65 V round-trip drop at 2.5 A over 20 ft). For a longer run, retain
16 AWG in the conduit and transition to short 18 AWG pigtails with a listed, insulated splice
before the Micro-Fit contacts.

Reverse-polarity protection with `DMP6023LE-13` (−60 V P-channel MOSFET):

- Drain to `RAW24`, source to `VM24`.
- Gate to AGND through 10 kΩ; gate to source through 100 kΩ.
- `MMSZ5242B` 12 V zener, cathode at source and anode at gate.

On `VM24`:

- `SMCJ24A`, cathode to VM24 and anode to PGND.
- 2 × Panasonic `EEU-FR1H471`, 470 µF / 50 V low-ESR bulk (940 µF total).
- 2 × 10 µF / 50 V X7R plus 100 nF / 50 V immediately beside the MCF VM/PGND current loop.

**Mandatory V1 scope gate**: the SMCJ24A maximum published clamp is 38.9 V, only 1.1 V below
the MCF8316D's 40 V absolute maximum. V1 must scope VM during insertion, cutoff, coast, stall
release, and reversal with the final cable and rotor. Normal transient target is ≤35 V; any
observed excursion to 40 V rejects the design and requires revised energy management.

**Energy rule**: the TVS is not a rotor brake. Enable MCF AVS, use 1–3 RPM/s deceleration,
coast by default, and never reverse until the rotor is stopped.

The source supply is 60 W. A 90 W brick is only a fallback if measured startup or transient
behavior shows the GST60 is inadequate.

## SCH-02 3.3 V logic rail

`TPSM365R6V3RDNR`, fixed 3.3 V / 600 mA, 65 V input:

- Input: 2.2 µF / 100 V X7R plus 100 nF / 100 V.
- Output: 2 × 22 µF / 10–16 V X7R.
- CVCC: 1 µF / 16 V. BIAS: directly to the 3.3 V output.
- PGOOD: 10 kΩ pull-up to 3.3 V, routed into the permission-clear path.
- Provide a MODE/SYNC selection jumper for PFM versus forced-PWM qualification.

Do not substitute a 36 V-rated regulator behind a TVS that may clamp near 39 V.

## SCH-03 MCF8316D power stage

`MCF8316DVRGFR`; follow TI's pinout and reference-layout loop geometry literally.

Variant note (researched 2026-07): swapped from `MCF8316DULVRGFR`. Datasheet Table 4-1 shows
the only differences are the UL 60730-1 recognition and an on-die Self Test Library (STL
command/status bits) that requires MCU-driven BIST to mean anything; silicon, pinout,
register map, and motor control are identical. This design's safety case is the external
hardware chain, and the plain D is LCSC-stocked for JLCPCB assembly. Capture with the
**D-generation pinout** — pins 36–39 (DACOUT1/DACOUT2/SOX/ALARM) differ from the A1, and the
D register map differs from A1/C (use TI's C→D conversion tool mindset; never reuse A1
register dumps or community drivers untranslated).

- VM pins 9–11 to VM24. OUTA 13/14 → U, OUTB 16/17 → V, OUTC 19/20 → W.
- PGND pins 12/15/18 joined locally. Exposed pad to AGND with a dense thermal-via array
  (≥12 vias).

| Connection | Starting value | Purpose |
|---|---|---|
| CP → VM | 1 µF, 16 V X7R | Charge-pump reservoir |
| CPH ↔ CPL | 47 nF, 50 V X7R | Flying capacitor |
| AVDD → AGND | 1 µF, 10 V X7R | Analog rail bypass |
| DVDD → DGND | 1 µF, ≥6.3 V X7R | Digital rail bypass |
| SW_BK → FB_BK | 47 µH Coilcraft LPS4018-473MRB | MCF auxiliary buck |
| FB_BK → GND_BK | 22 µF, 10 V X7R | Buck output |
| FG, nFAULT | 4.7 kΩ pull-ups to 3.3 V | Open-drain outputs |
| SDA, SCL | 4.7 kΩ pull-ups to 3.3 V | Configuration bus |

### GL100 commissioning seeds

CubeMars publishes 2.650 Ω line-to-line resistance and 2.350 mH inductance for the star
motor: begin with phase-neutral 1.325 Ω and 1.175 mH. Full register seeds and the
measured-data gate live in [controls.md](controls.md). FG cannot be divided to exactly one
pulse per revolution for 20 pole pairs; divide by 10 for two pulses/revolution if useful for
diagnostics. FG is not the independent overspeed channel.

## SCH-04 ESP32-C6 supervisor

`ESP32-C6-MINI-1-H4` (4 MB in-package flash, −40 to 105 °C; preferred over the
normal-temperature N4 variant). Supervision and the Matter bridge stay separate from
commutation: the
ESP configures the MCF through I²C and sends speed/direction commands; it never switches
motor phases.

- 10 µF + 100 nF at 3.3 V.
- 10 kΩ + 1 µF on EN; reset and boot buttons.
- 100 Ω series on SPEED, DIR, ARM_PULSE, and the watchdog heartbeat.
- DNP isolation links on I²C.
- USB-C native D−/D+ through 22 Ω, `TPD2EUSB30` ESD, 5.1 kΩ on CC1/CC2. VBUS is sense/test
  only and never powers the fan.

GPIO map, verified against the ESP32-C6-MINI-1 datasheet v1.5 (2026-07): every pin below is
exposed on the module (the MINI-1 exposes GPIO0–9 and 12–23) and none is a strap pin. The C6
straps are GPIO4, 5, 8, 9, and 15 — keep them free of unreviewed pulls. The original plan's
GPIO14 NTC input was wrong (C6 ADC1 lives only on GPIO0–6; GPIO14 has no ADC), so the NTC
moved to GPIO6 — a non-strap pin whose JTAG-default function (MTCK) is inactive unless
deliberately re-fused.

| GPIO | Signal | Note |
|---|---|---|
| 0 / 1 | SDA / SCL | MCF configuration bus |
| 2 | SPEED PWM | |
| 3 | DIR | |
| 6 | NTC ADC | optional temperature; ADC1_CH6 |
| 12 / 13 | USB D− / D+ | native USB (fixed-function pins) |
| 14 | MCF ALARM | push-pull active-high fault companion to nFAULT (was spare) |
| 16 / 17 | UART TX / RX | U0TXD / U0RXD defaults |
| 18 | permission ARM_PULSE | hardware safety handshake |
| 19 | watchdog heartbeat | hardware safety handshake |
| 20 | MCF FG | |
| 21 | MCF nFAULT | diagnostic |
| 22 | 3.3 V PGOOD | diagnostic |
| 23 | watchdog WDO | diagnostic |

Two module caveats: ADC range/accuracy specs only apply to modules with packaging-label PW
number ≥ PW-2023-06 (check the date code before trusting NTC accuracy); and only GPIO0–7
have LP aliases, so deep-sleep wake sources, if ever wanted, must come from that range (the
NTC on 6 and I²C on 0/1 qualify; GPIO18–23 cannot wake).

## SCH-05 hardware permission and watchdog

Firmware can enable the bridge; it cannot keep it enabled after a fault.

U5 permission latch, `SN74LVC1G74DCTR`:

- VCC 3.3 V; D to 3.3 V; `/PRE` 10 kΩ pull-up.
- CLK from ESP ARM_PULSE through 100 Ω with 100 kΩ pulldown.
- `/CLR` 10 kΩ pull-up and 100 nF to ground.
- Q through 1 kΩ to a `2N7002K` gate with 100 kΩ gate-source pulldown; MOSFET source to AGND,
  drain to MCF DRVOFF; DRVOFF 4.7 kΩ pull-up to MCF AVDD.
- Feed 3.3 V PGOOD, TPS3435 WDO, `OS_LOCK_OK`, `MCU_CLEAR_N`, and the manual-clear button
  into `/CLR` through individual BAT54H diodes (anode at `/CLR`). `MCU_CLEAR_N` is an ESP
  open-drain output with 10 kΩ pull-up: firmware can revoke permission but cannot override
  any fault.

U6 persistent safety lock, second `SN74LVC1G74DCTR`:

- VCC 3.3 V; D high; CLK low.
- `/PRE` from 3.3 V PGOOD (PGOOD low during power-up presets Q high/healthy).
- `/CLR` receives `OVERSPEED_N` and `TACH_PGOOD_N` as active-low wired fault sources.
- Q is `OS_LOCK_OK` and clears U5 when low.
- There is no firmware or network-side reset path to U6. After overspeed or tach-rail loss, only a
  full low-voltage power cycle presets it healthy again, and U5 still requires a fresh user
  command afterward.

Do not connect MCF nFAULT directly to asynchronous `/CLR` until its DRVOFF/startup
interaction is characterized. Keep it diagnostic and configure every configurable motor fault
to latched Hi-Z. V1 must run a fault-by-fault matrix (FET thermal recovery, buck thermal/OCP
reset, phase loss, lock, overcurrent, undervoltage); any condition that can re-energize the
motor without a new command is a V2 blocker and requires a dedicated persistent hardware
fault-lock input.

Watchdog: `TPS3435CAKAGDDFR`, fixed-time **pinout C** in SOT-23-8 (not pin- or
footprint-compatible with TPS3431; capture by exact orderable part number):

| Pin | Name | Connection |
|---:|---|---|
| 1 | SET0 | 10 kΩ to GND (1× timeout) |
| 2 | MR | 10 kΩ to 3.3 V; test pad only |
| 3 | WDI | 2 Hz, 50% duty ESP heartbeat through 100 Ω; service is the falling edge |
| 4 | GND | AGND |
| 5 | SET1 | 10 kΩ to GND (1× timeout) |
| 6 | WD-EN | 10 kΩ to 3.3 V so firmware cannot disable the watchdog |
| 7 | WDO | 10 kΩ pull-up to 3.3 V, then BAT54H into U5 `/CLR`; also to GPIO23 |
| 8 | VDD | 3.3 V with 100 nF local bypass |

With SET[1:0] = 00 the timeout is 1.6 s nominal ±10%. The device has no startup delay and
begins monitoring immediately; early WDO pulses before firmware boots are safe because U5
already powers up cleared and firmware cannot arm until its heartbeat is running. WDO is
active-low open-drain and asserts for 200 ms after a timeout; U5 converts that pulse into a
held-off motor state. WDO clears motor permission but does not reset the ESP.

Wire the same 2 Hz heartbeat into the MCF's **EXT_WD input (pin 32)** through a separate
100 Ω resistor, with the EXT_WDT fault response configured to latched Hi-Z — a second
zero-extra-parts "MCU died → motor Hi-Z" path inside the driver itself. Test both watchdog
consumers independently; do not merge their inputs after the resistors.

Also route the MCF's **ALARM output (pin 39** — push-pull, active-high, enabled via
ALARM_PIN_EN**)** to the spare ESP GPIO14: it is an opposite-polarity companion to the
open-drain nFAULT, so a stuck-low nFAULT line can't silently hide faults. Diagnostic only,
like nFAULT.

One IPD caveat for the fault matrix: if IPD startup (MTR_STARTUP = 10b) is used to avoid
align reverse-kick, IPD faults are hard-wired retry (not latchable) — a failed *start
attempt* re-attempts. This is distinct from a running-fault auto-restart; document it as
accepted behavior or use align startup if even that is unacceptable.

Firmware may arm only after all fault sources are healthy, configuration is complete, the
requested speed is zero, watchdog service is live, and DRVOFF has remained high for at least
10 seconds.

## SCH-06 independent Hall tach

One physical revolution becomes one analog safety decision. A single captive magnet avoids
the dangerous half-speed failure mode of a two-magnet tach; an equal-mass nonmagnetic slug at
180° restores balance.

Hall daughterboard (18 × 8 mm):

- `DRV5033FAQDBZR`, 3.3 V, 100 nF local bypass, open-drain output with 10 kΩ pull-up on the
  main board.
- JST-PH: 3.3 V, HALL_TACH, AGND.
- Sensor element and captive 6 × 3 mm N52 magnet both at r68.0 ±0.5 mm; south pole toward the
  package (verify polarity before closing the cap); magnet face parallel to the Hall PCB.
- Axial gap 2.5 mm nominal, adjustable 1.5–4.0 mm.

With the marker removed, run the GL100 through 0–180 RPM in both directions and require zero
Hall pulses from the motor magnets. With it installed, require exactly one pulse per
mechanical revolution. Any false pulse requires moving both sensor and marker to r82 in CAD,
not filtering or firmware compensation.

### Protected 12 V tach rail

Do not power the LM2907 from VM24 (its 28 V maximum is too close to the supply tolerance and
below the TVS clamp).

```text
VM24 -> 47 Ω / 0.25 W -> TPS7A1601ADGNR -> +12V_TACH (12.049 V nominal)
```

- LDO input: 10 µF / 63 V X7R + 100 nF / 100 V. EN tied to the filtered input.
- Feedback: 910 kΩ top, 100 kΩ bottom, both 0.1%. Feed-forward 10 nF / 50 V C0G output→FB.
- Output: 10 µF / 25 V X7R + 100 nF / 25 V.
- PG: 10 kΩ pull-up to 3.3 V, named `TACH_PGOOD_N`, routed to U6 `/CLR`.
- DELAY: 100 nF to AGND for a qualified startup delay.
- Connect both LM2907 pin 9 V+ and pin 8 collector only to +12V_TACH.

### LM2907M-14

- `HALL_TACH` drives a 2N7002 gate with 100 kΩ pulldown; the drain is pulled to +12V_TACH by
  10 kΩ and feeds pin 1 TACH+ through 100 Ω (optional 1 nF C0G to AGND). This level shift
  keeps 3.3 V from driving an unpowered LM2907.
- Pin 11 TACH−: 6.0 V from a 10 kΩ / 10 kΩ divider on +12V_TACH, bypassed by 100 nF.
- C1: 100 nF, 1% C0G, pins 2 to 3.
- Rscale: 562 kΩ 0.1% plus a 200 kΩ sealed ten-turn trimmer as a rheostat (wiper tied to one
  end), adjusted to approximately 656.1 kΩ total.
- C2: provisional 4.7 µF / 16 V X7R from pin 3 to AGND, with DNP alternatives for 0.47, 1.0,
  2.2, 3.3, and 6.8 µF. Final value selected by ripple and dynamic-trip testing.
- Pin 4 to pin 3; pin 10 to pin 5; pin 5 is buffered VTACH. Pins 6, 7, 13, 14 no connection.
- Nominal conversion after calibration: 13.175 mV/RPM.

Supply note: the LM2907 is TI-active (verified 2026-07) but it is the last monolithic F-to-V
family and stock is thin everywhere; buy spares with the V1 order. If supply ever dries up,
the fallback is a discrete charge-pump + comparator redesign of this stage, not a drop-in
(LM2917 variants change the input threshold architecture).

### TLV1701 trip stage

- Supply 3.3 V with 100 nF bypass.
- VTACH through 47.0 kΩ to the inverting input; BAT54S clamps at that input to 3.3 V and AGND.
- VREF: 10.0 kΩ from 3.3 V, 35.7 kΩ to AGND, both 0.1%.
- Hysteresis: 90.9 kΩ 0.1% from `OVERSPEED_N` to VREF.
- `OVERSPEED_N`: 10.0 kΩ pull-up to 3.3 V.
- Nominal trip 200.0 RPM rising; raw comparator reset 180.2 RPM. U6 remains locked after raw
  reset until low-voltage power is cycled.

Calibration and qualification: with the bridge disabled, inject a 0–3.3 V square wave into
HALL_TACH, allow at least 20 seconds settling, adjust for trip at 3.333 Hz, and verify raw
reset near 3.000 Hz. Then reproduce the fastest credible 170-to-runaway ramp with the final
rotor inertia and require U6 to lock before 240 RPM; the 4.7 µF C2 is not released by steady
calibration alone. Compare Hall pulses against MCF FG before every arm and while running: an
open Hall cable or missing magnet looks like zero speed and is a documented single-point
failure of the independent channel, so supervisory plausibility logic must stop the fan.

## Unused pins and safe defaults

- MCF BRAKE: 10 kΩ pulldown to AGND when unused.
- MCF DIR: 10 kΩ pulldown plus 100 Ω from the ESP.
- MCF SPEED: 100 kΩ pulldown plus 100 Ω from the ESP. **Sleep gotcha**: SPEED doubles as the
  WAKE pin; if it idles low past SLEEP_ENTRY_TIME in sleep mode, the device sleeps and stops
  ACKing I²C. Configure standby mode (DEV_MODE = 0b, I²C stays alive) since our idle state
  holds speed at zero — this masquerades as an I²C failure otherwise.
- TPS7A1601 EN: filtered input; PG pulled to 3.3 V; DELAY 100 nF; NC open.
- USB VBUS: high-value divider to an optional ESP sense input or a labeled test pad only; it
  never joins 3.3 V.
- All unused ESP pins: no pull unless the current module datasheet requires one.

## SCH-07 connectors

| Ref | Part | Pinout |
|---|---|---|
| J1 POWER | Molex Micro-Fit 43045-0200 (dual-row, right-angle) | 1 RAW24, 2 0V |
| J2 MOTOR | Molex Micro-Fit 43650-0300 (single-row, right-angle) | 1 U, 2 V, 3 W |
| J3 HALL | JST B3B-PH-K-S | 1 3V3, 2 HALL_TACH, 3 AGND |
| J4 TEMP | JST B2B-PH-K-S | 1 TEMP_SENSE, 2 AGND |
| J5 I2C | JST-SH 4-pin | GND, 3V3, SDA, SCL |
| J6 USB-C | GCT USB4105-GF-A | Native USB data; VBUS sense only |
| J7 PROGRAM | TC2030 footprint | 3V3, TX, RX, EN, BOOT, GND |
| J8 SCOPE | DNP 2×5, 1.27 mm | VM, rails, controls, FG, nFAULT, SOX |

Locking power and phase contacts must be rated at least 5 A/contact even though released
phase current is 1.5 A.

## PCB-02 placement and layers

Zones (x/y in mm from the board lower-left):

- Input + bulk: x 0–22.
- MCF8316D: x 20–50, y 4–35, motor connector adjacent.
- 3.3 V regulation: x 27–47, y 39–54.
- Tach + safety: x 50–76, y 4–27.
- ESP32-C6: antenna at the outward board edge; service/test headers along the remaining edge.

Layers:

- **L1** — components, short MCF switching loops, ≥2–3 mm 2 oz VM/phase pours, connectors.
  At least 12 thermal vias under/around the MCF exposed pad.
- **L2** — continuous AGND below logic and RF; local PGND island only under the motor stage,
  joined once beside the MCF through a wide net tie.
- **L3** — VM24 and 3.3 V distribution with ground fill. No copper under the ESP antenna.
- **L4** — quiet signals and ground. Keep phases, both switch nodes, and motor-current return
  out of the tachometer region.

Guidance: keep bulk capacitors within 10–15 mm of the MCF power return; keep the TPSM input
loop compact; route Hall and VTACH over uninterrupted AGND away from OUTA/B/C and switch
nodes. RF boundary: the ESP antenna sits at the board edge with the Espressif all-layer
keepout; the printed housing provides a nonmetallic window and at least 15 mm spatial
clearance to motor, hub, plate, wiring, and fasteners.

## Test points

Expose RAW24, VM24, PGND, AGND, 3V3, +12V_TACH, AVDD, DVDD, PGOOD, latch `/CLR`, latch Q,
DRVOFF, TPS3435 WDI/WDO/WD-EN/MR, MCF watchdog, nFAULT, SDA/SCL, FG, HALL_TACH, VTACH, VREF,
OVERSPEED_N, and OUTA/B/C. Include probe grounds, BOOT/RESET, direct I²C access, zero-ohm
isolation links around watchdog and analog fault paths, a spare bulk-cap footprint, and an
optional DNP input-fuse footprint.

## V1-to-V2 gates

V2 is not released until V1 passes:

1. MPET plus independent R, L, and BEMF confirmation.
2. At least 100 starts per direction at 35 and 40 RPM across 23.3, 24.0, and 24.7 V.
3. Stable sensorless operation through the intended range.
4. 1.5 A and 50 W limiting without supply hiccup.
5. VM transient tests with reviewed margin below 40 V.
6. GL100 stray-field immunity before marker installation.
7. Analog trip calibration and latency measurement.
8. Latch truth-table tests for brownout, watchdog, overspeed, manual clear, and restoration.
9. Proof that no condition automatically rearms the fan.
10. Eight-hour maximum-speed thermal run.
11. AVS and deceleration validation before considering active braking.
12. Emergency cutoff and reversal tests with the full rotor.

## Primary references

- MCF8316D datasheet: https://www.ti.com/lit/ds/symlink/mcf8316d.pdf
- MCF83xx open-to-closed-loop handoff tuning (SLLA665): https://www.ti.com/lit/an/slla665/slla665.pdf
- MCF8316A tuning guide (SLLU335, gradual-startup recipes): https://www.ti.com/lit/pdf/sllu335
- TIDA-010951 24 V sensorless FOC fan reference design: https://www.ti.com/lit/ug/tiduf84/tiduf84.pdf
- TPSM365R6: https://www.ti.com/lit/ds/symlink/tpsm365r6.pdf
- TPS7A16: https://www.ti.com/lit/ds/symlink/tps7a16.pdf
- TPS3435: https://www.ti.com/lit/ds/symlink/tps3435.pdf
- LM2907: https://www.ti.com/lit/ds/symlink/lm2907-n.pdf
- TLV1701: https://www.ti.com/product/TLV1701
- DRV5033: https://www.ti.com/product/DRV5033/part-details/DRV5033FAQDBZR
- ESP32-C6 PCB layout guide: https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32c6/pcb-layout-design.html
