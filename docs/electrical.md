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
the carrier top (Z68 after the 2026-07-27/28 stack shortening) the housing interior is a Ø194
cylinder that is empty except for the
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
(Z ~30–50 in the shortened interior) to keep the 15 mm metal clearance; verify with a real RSSI check. Connectors face
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

- **Drain to `RAW24`, source to `VM24`** — the dossier's original orientation, which is the
  canonical P-FET reverse-protection circuit (TI SLVA139 class). Review history: a first
  review pass "corrected" this to source-at-input, claiming body-diode inrush stress; an
  adversarial verification pass then proved that swap wrong and it was reverted. In the
  correct orientation the body diode conducts only for the sub-millisecond until the cap
  bank reaches ~3 V and the channel enhances (charge through the diode ≈ 3 mC, far inside
  surge ratings), and under reverse polarity the diode blocks. In the swapped orientation
  reverse current flows freely through the body diode — no protection at all. Do not
  "fix" this again.
- Gate to AGND through 10 kΩ; gate to source through 100 kΩ.
- `MMSZ5242B` 12 V zener, cathode at source and anode at gate. The zener is load-bearing,
  not optional: without it the divider drives Vgs to ≈ −22 V, past the ±20 V absolute
  maximum.

On `VM24`:

- `SMCJ24A`, cathode to VM24 and anode to PGND.
- 2 × Panasonic `EEU-FR1H471`, 470 µF / 50 V low-ESR bulk (940 µF total).
- 2 × 10 µF / 50 V X7R plus 100 nF / 50 V immediately beside the MCF VM/PGND current loop.

TVS standoff note (2026-07 review): the GST60A24's tolerance is ±3%, so worst-case
continuous output (24.72 V) slightly exceeds the SMCJ24A's 24 V standoff rating. This is
**accepted deliberately**: minimum breakdown (~26.7 V) still clears it, and the "fix"
(SMCJ26A) raises the maximum clamp to ~42 V — above the MCF's 40 V ceiling, which is the
margin that actually matters. Fuse note: the ordered 3 A fast-blow has ~10× I²t margin
against inrush at the full 20 ft cable run but shrinks toward ~1.4× on a short bench run;
if bench nuisance-blows occur, substitute a 3 A time-delay fuse rather than uprating.

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
- Output: 2 × 22 µF X7R, **16–25 V rated in 1206/1210** — the datasheet floor is 40 µF
  *effective*, and small-case 10 V parts derate below it at 3.3 V DC bias (TI's own BOM uses
  25 V 1210).
- CVCC: 1 µF / 16 V. BIAS: directly to the 3.3 V output.
- **EN: tie to VM24** (or a UVLO divider) — the datasheet forbids floating it.
- PGOOD: 10 kΩ pull-up to 3.3 V, routed into the permission-clear path.
- MODE/SYNC selection via a 3-pad jumper to GND (auto/PFM, default) or 3.3 V (forced PWM) —
  the pin must never float; an unpopulated 2-pad jumper is an invalid state.
- Power budget (verified 2026-07): worst-case simultaneous 3.3 V load ≈ 391 mA (Wi-Fi TX
  peak 382 mA dominates; BLE/Wi-Fi coex time-multiplexes and does not add) vs 600 mA rating
  — adequate with ~35% headroom. J5/J7 export 3.3 V to bench tools; the headroom covers
  typical probes.

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
| CPH ↔ CPL | 47 nF, **100 V** X7R | Flying capacitor (datasheet wants ≥2× VM; 50 V gave only 4% margin at nominal bus) |
| AVDD → AGND | 1 µF, 10 V X7R | Analog rail bypass |
| DVDD → DGND | 1 µF, ≥6.3 V X7R | Digital rail bypass |
| SW_BK → FB_BK | 47 µH Coilcraft LPS4018-473MRB | MCF auxiliary buck. **Verify Isat ≥ 910 mA** (the buck OCP max) before capture — the LPS4018's saturation rating is likely below it; a same-value LPS5030/XAL40xx-class part closes the gap |
| FB_BK → GND_BK | 22 µF, 10 V X7R | Buck output |
| FG, nFAULT | 4.7 kΩ pull-ups to 3.3 V | Open-drain outputs |
| SDA, SCL | 4.7 kΩ pull-ups to 3.3 V | Configuration bus |

### GL100 commissioning seeds

CubeMars publishes 2.650 Ω line-to-line resistance and 2.350 mH inductance for the star
motor: begin with phase-neutral 1.325 Ω and 1.175 mH. Full register seeds and the
measured-data gate live in [controls.md](controls.md). FG cannot be divided to exactly one
pulse per revolution for 20 pole pairs. **Configure FG_DIV = 1h (divide-by-1): 20
pulses/revolution**, 11.7 Hz at 35 RPM — FG is contract-critical for stop verification and
the FG-vs-Hall plausibility check, and /1 gives an order of magnitude better supervisory
resolution and latency than the previously suggested /10. FG is not the independent
overspeed channel.

I²C note: the MCF is not a plain SMBus device — every transaction starts with a 24-bit
control word (R/W, CRC enable, data length, memory section/page/address). No factory-default
7-bit target address is explicitly stated in the datasheet (examples use 0x60); bus-scan at
first bring-up rather than assuming.

## SCH-04 ESP32-C6 supervisor

`ESP32-C6-MINI-1-H4` (4 MB in-package flash, −40 to 105 °C; preferred over the
normal-temperature N4 variant). Supervision and the Matter bridge stay separate from
commutation: the
ESP configures the MCF through I²C and sends speed/direction commands; it never switches
motor phases.

- 22 µF + 100 nF at 3.3 V (bumped from 10 µF to match Espressif's reference design; Wi-Fi
  TX bursts peak ~382 mA).
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
| 2 | SPEED PWM | 10–350 Hz carrier band (11-bit resolution) |
| 3 | DIR | |
| 6 | NTC ADC | optional temperature; ADC1_CH6 |
| 7 | HALL_TACH sense | 3.3 V-domain Hall input for the FG-vs-Hall plausibility check (added 2026-07 review — the check was unimplementable without it); non-strap, JTAG-inactive by default |
| 12 / 13 | USB D− / D+ | native USB (fixed-function pins) |
| 14 | MCF ALARM | push-pull active-high fault companion to nFAULT |
| 15 | MCU_CLEAR_N | open-drain out, 10 kΩ pull-up (added 2026-07 review — it had no pin). Strap reviewed: GPIO15's JTAG-select strap is ignored with default eFuses, and the pull-up satisfies "don't float" |
| 16 / 17 | UART TX / RX | U0TXD / U0RXD defaults |
| 18 | permission ARM_PULSE | hardware safety handshake; software-sequenced pulse only |
| 19 | watchdog heartbeat | hardware safety handshake; bit-banged only (see controls.md) |
| 20 | MCF FG | FG_DIV = 1h, 20 pulses/rev |
| 21 | MCF nFAULT | diagnostic |
| 22 | 3.3 V PGOOD | diagnostic |
| 23 | watchdog WDO | diagnostic |

Boot-strap hardware (2026-07 review): add a **10 kΩ pull-up to 3.3 V on GPIO8** — download
boot requires GPIO8 = 1 while GPIO9 = 0, GPIO8 floats with no internal pull, and Espressif's
own reference design adds this resistor; without it, flashing via J7 is unreliable. Add an
external 10 kΩ pull-up on GPIO9 as well (the internal ~45 kΩ is weak for a motor board with
an exposed header). Layout note: GPIO18 (ARM_PULSE) and GPIO19 (heartbeat) are adjacent —
a solder bridge turns the heartbeat into an automatic re-arm clock; separate them in layout
or route with care.

NTC circuit (was unspecified): 10 kΩ 1% from 3.3 V to GPIO6, 10 kΩ NTC from GPIO6 to AGND,
100 nF at the pin (Espressif's ADC filter recommendation), ADC at 11 dB attenuation
(0–3300 mV, ±40 mV). VBUS sense divider (was unspecified): 100 kΩ / 100 kΩ to a test pad or
ADC pin — 5.25 V max lands at 2.6 V, inside the 3.3 V limit.

Two module caveats: ADC range/accuracy specs apply only to chips manufactured on/after
shielding-case date code **212023** or modules assembled on/after bar-code D/C **2321**
(corrected 2026-07 — the earlier "PW-2023-06" format was a dossier fabrication; check the
real date code before trusting NTC accuracy). And only GPIO0–7 have LP aliases, so
deep-sleep wake sources, if ever wanted, must come from that range (the NTC on 6, HALL on 7,
and I²C on 0/1 qualify; GPIO18–23 cannot wake). J7 programming note: there is deliberately
no on-board auto-reset network — the TC2030 jig must drive EN and BOOT (GPIO9) directly.

## SCH-05 hardware permission and watchdog

Firmware can enable the bridge; it cannot keep it enabled after a fault.

U5 permission latch, `SN74LVC1G74DCTR`:

- VCC 3.3 V; D to 3.3 V; **`/PRE` tied directly to VCC** (2026-07 review: through a
  resistor, an open pull-up leaves `/PRE` floating and a subsequent fault's both-asserted
  state would force Q *high* — the fault would enable drive).
- CLK from ESP ARM_PULSE through 100 Ω with 100 kΩ pulldown.
- `/CLR` 10 kΩ pull-up, **no capacitor** (2026-07 review: the previous 100 nF gave
  millisecond edges, ~5 orders outside the LVC1G74's 10 ns/V input transition-rate spec — a
  metastability window on safety logic). Buffer `/CLR` through an `SN74LVC1G17` Schmitt
  gate so the slow diode-OR node presents a clean edge.
- Q through 1 kΩ to a `2N7002K` gate with 100 kΩ gate-source pulldown; MOSFET source to AGND,
  drain to MCF DRVOFF; DRVOFF 4.7 kΩ pull-up to MCF AVDD.
- Feed 3.3 V PGOOD, TPS3435 WDO, `OS_LOCK_OK`, `MCU_CLEAR_N`, and the manual-clear button
  into the `/CLR` wired-OR node through individual BAT54H diodes — anodes at the wired-OR
  node (which feeds the `SN74LVC1G17` buffer, not the `/CLR` pin directly), cathodes at
  each active-low source. Six BAT54H total including U6's `/PRE` discharge diode.
  `MCU_CLEAR_N` is an ESP open-drain output with 10 kΩ pull-up: firmware can revoke
  permission but cannot override any fault.
- U6's own `/CLR` node (the OVERSPEED_N / TACH_PGOOD_N wire-OR) is deliberately
  **unbuffered** despite its slow ~µs edges: U6's CLK is tied low, so the clock-vs-async
  race that motivates the U5 Schmitt cannot occur, and slow-edge glitching on an async
  clear only re-asserts the state it is already entering. Documented waiver, not an
  oversight.

U6 persistent safety lock, second `SN74LVC1G74DCTR`:

- VCC 3.3 V; D high; CLK low.
- **`/PRE` from *delayed* PGOOD** — a 2026-07 review fix for a confirmed dead-on-arrival
  race (found independently by four reviewers): as originally drawn (`/PRE` from raw
  PGOOD), PGOOD releases ~5.5 ms after the 3.3 V rail while `TACH_PGOOD_N` on `/CLR` stays
  asserted for the TPS7A16's deliberate 60–120 ms DELAY, so `/PRE` released first, the
  '1G74 latched Q low, and with CLK grounded nothing could ever set it again — the fan
  could never arm, and every power cycle replayed the race. Fix: PGOOD → RC (**100 kΩ
  pull-up, 10 µF** — the values matter; a first-pass 10 kΩ/22 µF could only deliver
  ~115–195 ms against the Schmitt VT+ corners and did not close the race at datasheet
  corners) → `SN74LVC1G17` Schmitt buffer → `/PRE`, with a discharge diode (anode at the RC
  node, cathode at PGOOD) so power-down re-asserts preset promptly. Corner math: charging
  from the ~0.35 V clamp, delay = 0.55–1.1 s across the LVC1G17 VT+ range (1.6–2.1 V) —
  dwarfed by the 10 s safe boot. On the other side, **reduce the TPS7A16 DELAY cap from
  100 nF to 10 nF** (~12 ms typical): its I_DELAY spec has no minimum, so the slow corner
  is formally unbounded, and margin comes from the ~50× ratio rather than a bounded
  worst case. PCB-03D still tests the ordering on real hardware.
- Glitch behavior, stated honestly (a first-pass claim of ~300 ms glitch immunity was
  wrong): `/PRE` *asserts* at the start of a PGOOD dip via the discharge diode — the RC
  delays release, not assertion — so any dip longer than the ~ms diode-discharge time
  presets U6 healthy. Prompt power-down assert and long glitch immunity are mutually
  exclusive in this topology. Accepted because a PGOOD dip also clears U5 through its own
  diode and a fresh user command plus the 10 s hold are still required before any restart;
  the residual (a mid-coast brownout erasing the overspeed latch after the rotor has slowed)
  is documented rather than defended.
- `/CLR` receives `OVERSPEED_N` and `TACH_PGOOD_N` as active-low wired fault sources (both
  verified open-collector/open-drain, so the direct wire-OR is valid; no diodes needed).
- Q is `OS_LOCK_OK` and clears U5 when low.
- There is no firmware or network-side reset path to U6. After overspeed or tach-rail loss,
  only a genuine power cycle (long enough to discharge the `/PRE` RC) presets it healthy
  again, and U5 still requires a fresh user command afterward. During a simultaneous
  overspeed + brownout both async inputs assert (a nonstable '1G74 state); safety holds
  because PGOOD independently clears U5 through its own diode.

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
100 Ω resistor — a second zero-extra-parts "MCU died → motor Hi-Z" path inside the driver
itself. Required registers (2026-07 review; without these the path silently doesn't exist):
`EXT_WDT_EN` = 1, input mode = pin, **`EXT_WDT_CONFIG` = 1000 ms** (the tickle is the
rising edge every 500 ms, so 500 ms is zero-margin and 100/200 ms fault instantly), and
**`EXT_WDT_FAULT_MODE` = 1b** = latched Hi-Z — note this field's encoding is *inverted*
relative to the other fault modes (0b = report-only). Test both watchdog consumers
independently; do not merge their inputs after the resistors.

Residual risks in the permission chain, documented deliberately (2026-07 review):

- **WDO is a 200 ms pulse, not a latch**: pathological-but-alive firmware could re-arm 200 ms
  after every watchdog trip (run/coast oscillation). Mitigated by the MCF EXT_WDT latched
  Hi-Z (above) catching a truly stopped heartbeat, and by the firmware rules in controls.md
  (bit-banged heartbeat, software-sequenced ARM_PULSE).
- **Single-point failures that force drive enabled**: a drain-source-shorted 2N7002K (or a
  DRVOFF-to-GND solder defect) holds DRVOFF low regardless of every latch; an open DRVOFF
  pull-up leaves an undefined CMOS input; an open BAT54H silently disconnects one fault
  source from `/CLR` (latent until demanded). Accepted as residual risk — the remaining
  cover is the MCF's internal limits — with per-path verification rows in the test matrix.
- Diode-OR low-level margin: worst-case source VOL + BAT54H VF stacks to ~0.6–0.75 V
  against VIL 0.8 V; real currents sit near 0.4–0.5 V. Thin on paper, fine in practice;
  re-check at temperature extremes during V1.

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
- C1: 100 nF, 1% C0G, **pin 2 (CP1) to AGND** (corrected 2026-07 review: the dossier said
  "pins 2 to 3", which dumps the ±180 µA pump current into the output filter node and voids
  the K-factor/linearity specs — both TI application figures ground the timing cap).
- Rscale: 562 kΩ 0.1% plus a 200 kΩ sealed ten-turn trimmer as a rheostat (wiper tied to one
  end), adjusted to approximately 656.1 kΩ total. Pin 3 carries only Rscale ∥ C2 to AGND.
- C2: provisional **2.2 µF** / 16 V X7R from pin 3 to AGND (baseline moved from 4.7 µF by
  the 2026-07 timing analysis — see the two-tier trip claim below), with DNP alternatives
  for 0.47, 1.0, 3.3, 4.7, and 6.8 µF. Final value selected by ripple and dynamic-trip
  testing.
- Pin 4 to pin 3; pin 10 to pin 5; **10 kΩ emitter load from pin 5 to AGND** (added 2026-07
  review: without it the follower has no pull-down path below the input clamp and
  falling-speed response is unspecified). Pin 5 is buffered VTACH. **Pin 12 to AGND.**
  Pins 6, 7, 13, 14 no connection.
- Nominal conversion after calibration: 13.175 mV/RPM. (Exact threshold model: with the
  open-collector output the rising trip computes to 199.6 RPM, not 200.0; the Rscale trim
  absorbs the difference.)
- 47 Ω dropper: rate **1 W** (an LDO current-limit fault dissipates up to ~7.5 W
  transiently in a 0.25 W part; 1 W survives indefinitely at the limited current).

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

**Two-tier trip claim** (re-scoped by the 2026-07 timing analysis — the original blanket
"locked before 240 RPM" does not survive arithmetic): a 1 pulse/rev tach at 3.3 Hz updates
every ~300 ms, and the C2 filter lag adds τ = Rscale·C2 (3.1 s at 4.7 µF, 1.4 s at 2.2 µF).

- **Tier 1 — bounded ramps** (speed-limit failure with the 1.5 A current limit intact,
  ~30 RPM/s worst case): the analog trip locks before ~245 RPM with C2 = 2.2 µF. This is
  what the dynamic-latency test qualifies, with the ramp rate written into the acceptance
  limit.
- **Tier 2 — fast misconfiguration** (current limit also maxed, ~120 RPM/s): no realizable
  C2 catches it inside 240 RPM (the 300 ms sampling delay alone eats 36 RPM). The bound is
  physical: the 60 W supply caps terminal runaway at ~260–270 RPM (aero power ∝ N³), the
  trip still fires and latches, and the mechanical design basis is raised to 270 RPM to
  cover it. A V2 option if a hard guarantee is ever wanted: a retriggerable-monostable
  period detector (any Hall period < 250 ms trips within one revolution, no averaging).

Calibration: with the bridge disabled, inject a square wave into HALL_TACH **at a
representative ~1–3% duty cycle, not 50%** (2026-07 review: the real magnet arc gives
~4 ms pulses at 200 RPM, marginal against the LM2907 charge-pump slew at min-spec pump
current — 50%-duty calibration masks it; also measure the actual Hall pulse width vs speed
during commissioning). Allow at least 30 seconds settling, adjust for trip at 3.333 Hz, and
verify raw reset near 3.000 Hz. Bench note: bladeless motor-only runs accelerate far faster
than any filter can track — rely on MCF current/power limits, not the analog trip, when no
rotor is fitted.

Compare Hall pulses against MCF FG **on GPIO7** while running: an open Hall cable or
missing magnet looks like zero speed and is a documented single-point failure of the
independent channel, so supervisory plausibility logic must stop the fan (contract in
controls.md; note the pre-arm check can only assert both-channels-quiet — sensor-loss
detection necessarily happens in the running state).

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
clearance to motor, hub, plate, **carrier**, wiring, and fasteners (2026-07 geometry check:
all antenna positions along the board clear 15 mm with ≥19 mm actual margin).

Physical orientation: **horizontal under the plate** (settled by the 2026-07-27/28 rotor
raise; the 2026-07 review's vertical mount needed 97 mm and the interior is now 62 mm,
plate underside Z6 to carrier top Z68 — both vertical orientations are dead). The board
mounts flat, component envelope ~Z12–35, off-center beside the spindle flange within the
Ø194 interior; EB-100 becomes a horizontal standoff arrangement off the same MP-100 taps.
Open items for the bracket redesign: antenna placement keeping ≥15 mm spatial clearance to
the plate above (verify against the metal-clearance rule — mid-height standoffs help),
J1/power near the 15° cable entry, tach/safety zone near the Hall bracket, nothing
overhanging the Ø194 interior, corner-margin tolerance stack carried in CAD.

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
