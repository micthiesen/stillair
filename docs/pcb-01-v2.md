# PCB-01 V2 design specification

Status: **design baseline for schematic capture and layout**. This document replaces the former
contingency brief. It is the controlling electrical and PCB handoff for PCB-01 V2. Exact footprint
positions, board dimensions, trace geometry, via positions, and zone polygons are deliberately left
to the KiCad placement and routing pass. Everything else is frozen here.

V2 is a one-off controller redesign, not a productionization exercise. It preserves the V1 motor,
power, Hall-cable, drive-permission, watchdog, and independent overspeed behavior. It removes V1
development interfaces that were awkward or redundant and makes the remaining service access safe
to use repeatedly.

## Scope and authority

- This specification controls the V2 component selection, pin assignments, net names, ratsnest,
  external interfaces, board technology, layout constraints, assembly split, and validation.
- `docs/electrical.md` remains the detailed rationale and V1 record. Where it describes a V2 outline,
  mounting coordinates, USB, J7, J8, C34, F1, C36-C40, or the ESP32-C6-MINI-1, this document wins.
- `docs/controls.md` remains the behavioral firmware contract. The GPIO changes here win.
- The V1 KiCad board is evidence, not a template. Do not clone its placement or carry its DRC waivers
  into V2.
- Connector compatibility is required only for J1 POWER, J2 MOTOR, and J3 HALL. Their orientation may
  change. V1 outline, holes, board position, and every other connector may change.
- The board stays rectangular and should be smaller than 78 x 58 mm if the placement remains clean.
  Do not force a size target. Freeze the outline around the completed placement with comfortable
  connector, antenna, probe, hand-soldering, and mounting clearances.

## Frozen design decisions

### Preserve

- 24 V input, reverse-polarity PMOS, VM transient clamp, 940 uF bulk capacitance, TPSM365R6 3.3 V
  supply, and the protected TPS7A1601 12 V tach supply.
- `MCF8316DVRGFR`, the proven U/V/W cable mapping, and its D-generation register map.
- Firmware-independent `DRV5033 -> LM2907 -> TLV1701 -> U6` overspeed shutdown.
- U5 drive-permission latch, U6 power-cycle-only safety lock, TPS3435 window watchdog, MCF external
  watchdog, active-low fault wired-OR, and Q2 open-drain control of MCF `DRVOFF`.
- MCF I2C telemetry, FG, Hall plausibility, ALARM, nFAULT, SOX, WDO diagnostics, on-board digital
  chamber-temperature telemetry, and physical RESET, BOOT, and permission-clear buttons.
- Four copper layers, 2 oz outer copper, 1 oz inner copper, ENIG, top-side SMD assembly, separate
  AGND and PGND domains, and one explicit net-tie join.

### Change

- U2 becomes `ESP32-C6-WROOM-1-N8`. Its castellated joints are inspectable and reworkable. GPIO14 is
  not exposed, so MCF ALARM moves from GPIO14 to GPIO10. All other used GPIOs retain their functions.
  This N8 module is rated to 85 C rather than V1's 105 C. Its measured local board temperature must
  remain at or below 75 C in the closed housing, preserving 10 C margin; otherwise select and source
  an approved 105 C WROOM variant before capture rather than waiving the limit.
- J5 becomes a keyed 5-pin JST PH service connector carrying AGND, TX, RX, active-low RTS, and
  active-low DTR. It carries no board power.
- Q4 and R55-R56 implement Espressif's two-transistor RTS/DTR automatic BOOT/RESET circuit. R57 adds
  470 ohm series resistance at UART RX. Direct RESET and BOOT buttons remain.
- C34 becomes a true 1206, 100 nF, 50 V, C0G, 1% JLCPCB-assembled part.
- U3 pin 11 MODE/SYNC connects directly to AGND, selecting the proven default PFM mode.
- Test access becomes labelled plated through-holes grouped along accessible edges. Phase outputs
  are measured at J2 only with a rated differential probe.
- U12 becomes a `TMP1075DGKR` digital temperature sensor on a dedicated GPIO6/GPIO11 I2C bus. It
  measures the chamber at a thermally quiet board edge without consuming an ESP ADC channel or
  sharing the MCF recovery bus.
- Mounting remains four M3 clearance holes near the corners, but coordinates and outline follow
  placement.

### Delete

- C6 spare bulk footprint, C32 unused optional LM2907 input capacitor, and the never-populated
  C36-C40 five-footprint 0805 alternate filter-capacitor array beside U1. Do not carry their pads,
  DNP records, or placement reservation into V2.
- F1 and its bridge. The wall-box 3 A ATO fuse remains the source protection boundary.
- Native USB J6, the V1 U12 USB-protection function, R21, the V1 USB function/value of R20, V1
  R55-R58, CC resistors, VBUS divider, VBUS test point, and all USB/VBUS nets. The R20 designator is
  not deleted: U12, R20, and new V2 R55-R57 are reassigned below.
- J7 Tag-Connect, J8 debug header, and the external JST-SH I2C connector previously called J5. SDA
  and SCL remain available as edge test holes.
- J4 and the external NTC input. V1 R19 and R20 are reassigned as U12 bus pull-ups.
- Duplicate ground test pads and every V1 placement-only DRC waiver.

The USB deletion is intentional. V2 recovery and the runtime console use UART. Before ordering, the
service circuit must pass the UART qualification below using a development module or engineering
board. Failure blocks fabrication; it does not add USB back by default.

## External interfaces

Pin numbers are schematic/footprint pad numbers viewed at the board header. Silkscreen must show
connector name, pin 1, and signal order. Cable drawings must state the same view.

| Ref | Exact board part and mating family | Pinout | Requirement |
|---|---|---|---|
| J1 POWER | Molex `43045-0200`, Micro-Fit 3.0 right-angle | 1 `RAW24`, 2 `PGND` | Preserve existing cable exactly |
| J2 MOTOR | Molex `43650-0300`, Micro-Fit 3.0 right-angle | 1 `PHASE_W`, 2 `PHASE_V`, 3 `PHASE_U` | Preserve existing cable exactly |
| J3 HALL | JST `B3B-PH-K-S(LF)(SN)`, PH 2.0 mm, PHR-3 mate | 1 `3V3`, 2 `HALL_TACH`, 3 `AGND` | Preserve existing cable exactly |
| J5 SERVICE | JST `B5B-PH-K-S(LF)(SN)`, `C157993`, PHR-5 mate | 1 `AGND`, 2 `UART_TX`, 3 `UART_RX_CONN`, 4 `RTS_N`, 5 `DTR_N` | No power; accessible edge |

J5 directions are from the board perspective: pin 2 is output, pin 3 is input. Adapter VCC must be
absent or unconnected. Label the cable `GND TX RX RTS DTR` with board-perspective directions.

The specified service adapter is FTDI `UMFT231XA-01`, a 3.3 V full-handshake UART module. The V1
DSD TECH SH-U09C2 is incompatible because it does not expose DTR. Build the PHR-5 cable as follows:
adapter GND to J5.1, adapter RXD to J5.2, adapter TXD to J5.3, adapter RTS# to J5.4, and adapter DTR#
to J5.5. Leave FTDI V3OUT, VCC, VBUS, and every other pin unconnected. Keep the module's default
3.3 V VCCIO configuration and use a data-capable USB Mini-B cable. Its default USB identity is
VID:PID `0403:6015`; do not reuse the current SH-U09C2/FT232 `0403:6001` identity.

### Automatic programming

Q4 follows the ESP32-C6 DevKitC v1.3 anti-reset reference circuit, including its cross-coupled
emitters and 10 k base resistors. Q4A is collector 3, emitter 4, base 5. Q4B is collector 6,
emitter 1, base 2. Confirm this onsemi SOT-363 Style 1 mapping in the symbol and footprint.

| RTS_N | DTR_N | ESP_EN | ESP_BOOT | Result |
|---:|---:|---|---|---|
| 1 | 1 | released | released | normal run |
| 0 | 1 | low | released | reset asserted |
| 1 | 0 | released | low | download strap asserted |
| 0 | 0 | released | released | no continuous reset |

## Functional architecture

### Power and motor stage

J1.1 connects directly to `RAW24`. Q1 uses the proven ideal-diode orientation: drain/tab `RAW24`,
source `VM24`, gate `PMOS_GATE`. R1 pulls the gate to AGND, R2 pulls it to source, and D1 clamps
gate-to-source with cathode at VM24. D2 clamps VM24 to PGND. C1-C5 provide 940 uF bulk plus ceramic
bypass. There is no local fuse or fuse-shaped bridge.

U3 is the fixed 3.3 V TPSM365R6. VM24 feeds VIN and EN, MODE/SYNC goes directly to AGND, BIAS goes
to 3V3, and PGOOD drives `PGOOD` through its pull-up. Preserve TI reference-layout loops.

Use the D-generation `MCF8316DVRGFR`. Pins 9-11 take VM24; pins 12,15,18 return to PGND; exposed pad
41 returns to AGND. Route the three paired half-bridges directly to J2 in frozen W/V/U order.
`SPEED` remains because it also supplies MCF wake during recovery. Normal speed command is I2C;
firmware holds PWM command at zero because loaded V1 commissioning showed PWM decoded as zero.

### ESP32-C6 supervisor

U2 is powered only from 3V3. EN has R11 10 k pull-up, C19 1 uF to AGND, SW1 to AGND, and Q4 reset.
GPIO9 has R12 10 k pull-up, SW2 to AGND, and Q4 BOOT control. GPIO8 retains R13 10 k pull-up.

| U2 pad | ESP signal | V2 net/function |
|---:|---|---|
| 1,28,29 | GND/EP | AGND with dense stitching |
| 2 | 3V3 | 3V3 |
| 3 | EN | `ESP_EN` |
| 4,5 | GPIO4,5 | no connect |
| 6 | GPIO6 | `TEMP_SDA` |
| 7 | GPIO7 | `HALL_TACH` |
| 8 | GPIO0 | `ESP_SDA` |
| 9 | GPIO1 | `ESP_SCL` |
| 10 | GPIO8 | `ESP_GPIO8` pull-up only |
| 11 | GPIO10 | `ALARM`, moved from GPIO14 |
| 12 | GPIO11 | `TEMP_SCL` |
| 13,14 | GPIO12,13 | no connect |
| 15 | GPIO9 | `ESP_BOOT` |
| 16 | GPIO18 | `ARM_PULSE` |
| 17 | GPIO19 | `WD_HEARTBEAT` |
| 18 | GPIO20 | `FG` |
| 19 | GPIO21 | `NFAULT` |
| 20 | GPIO22 | `PGOOD` |
| 21 | GPIO23 | `WDO` diagnostic |
| 22 | NC | no connect |
| 23 | GPIO15 | `MCU_CLEAR_N`, open-drain |
| 24 | GPIO17/RXD0 | `UART_RX` through R57 |
| 25 | GPIO16/TXD0 | `UART_TX` |
| 26 | GPIO3 | `ESP_DIR` |
| 27 | GPIO2 | `ESP_SPEED` |

### Digital chamber temperature

U12 is TI `TMP1075DGKR`, a 12-bit local digital sensor powered from 3V3. Connect SDA pin 1 to
`TEMP_SDA`, SCL pin 2 to `TEMP_SCL`, GND pin 4 to AGND, V+ pin 8 to 3V3, and address pins A2/A1/A0
pins 5/6/7 to AGND. This fixes the 7-bit address at `0x48`. R19 and R20 pull TEMP_SDA and TEMP_SCL
to 3V3 with 4.7 k each. C20 is U12's local 100 nF bypass from V+ to AGND. ALERT pin 3 is no-connect:
chamber temperature is diagnostic telemetry and has no authority over U5, U6, DRVOFF, speed limits,
or drive permission.

U12 measures air temperature plus residual local-board heating, not remote motor temperature. Its
placement and validation below make it the defined chamber-temperature proxy. The TEMP_SDA/TEMP_SCL bus is
electrically separate from the GPIO0/GPIO1 MCF bus, so U12 cannot see MCF control words, CRC bytes,
or address-recovery sweeps and cannot hold the motor-controller bus low. R6/R7 and R16/R17 retain
their existing MCF-bus functions only.

### Permission, watchdog, and persistent lock

- U5 D and active-low PRE tie high. ARM_PULSE passes R24 to CLK; R25 holds CLK low. U5_CLR_OR goes
  through U10 to active-low CLR. U5 Q drives Q2 through R26; R27 holds Q2 off. Q2 can pull DRVOFF
  low but cannot force it high. R28 pulls DRVOFF to MCF_AVDD.
- D3-D7 anodes join U5_CLR_OR; cathodes connect to PGOOD, WDO, OS_LOCK_OK, MCU_CLEAR_N, and SW_CLR.
  SW3 and R30 generate SW_CLR. MCF nFAULT remains diagnostic only.
- U6 D ties high, CLK low, active-low CLR is OVERSPEED_N, and Q is OS_LOCK_OK. PRE releases only after
  the R31/C23 delay passes U11. D8 rapidly discharges it when PGOOD falls. Only low-voltage power
  cycling resets a tripped lock.
- U7 uses the fixed 1.6 s `CAKAG` timeout. One heartbeat fans through separate R36/R38 to U7 WDI and
  MCF EXT_WD. WDO clears U5 through D4 and reaches GPIO23.

Firmware never drives DRVOFF or commutates phases. It revokes permission through open-drain
MCU_CLEAR_N and requests it only with bounded ARM_PULSE.

### Hall and independent overspeed

J3 supplies the Hall board. R43 is the 10 k pull-up. Q3 level-shifts the open-drain Hall signal to
the protected 12 V LM2907 input; R44 loads the drain and R45 limits input current. C32 is deleted.

U4 creates 12.049 V nominal through R39. Its DELAY capacitor is 10 nF. U4 PG is open-drain on
OVERSPEED_N, so tach-supply loss clears U6 like a comparator trip. U8 converts one Hall pulse per
revolution to voltage. C34 is the charge-pump timing capacitor; R48/RV1 set scale; C35 is the only
ripple capacitor. U9 compares VTACH with VREF and R54 adds hysteresis. D9 clamps its input. Adjust
for 200 RPM trip and verify raw comparator reset near 180 RPM; U6 remains latched until power cycle.

RV1 is a one-time engineering calibration control for the independent analog overspeed threshold,
not a user speed control. Its adjustment absorbs LM2907 timing, divider, and component tolerances.
Leave it accessible for bring-up, label it `OVERSPEED CAL`, record the final setting and measured
trip/reset speeds, then apply a removable witness mark across the screw and body after calibration.
Calibrate with bridge drive disabled while injecting HALL_TACH. Observe raw `OVERSPEED_N` at TP15:
sweep upward to record trip, then downward to record the raw comparator reset even though U6 remains
latched. Do not infer raw reset from DRVOFF or OS_LOCK_OK. After each complete sweep, power-cycle the
low-voltage rails, confirm U6 re-arms, and only then begin the next trim trial.

## Exact component schedule

All components are populated unless marked hand or mechanical. There are no DNP option footprints.
LCSC identifiers freeze the intended item. Substitution requires review and a spec update first.

### Capacitors

| Refs | Qty | Exact requirement | Footprint | Source/MPN |
|---|---:|---|---|---|
| C1,C2 | 2 | 470 uF, 50 V, low-ESR, 105 C | `Capacitor_THT:CP_Radial_D10.0mm_P5.00mm` | Panasonic `EEU-FR1H471`, hand |
| C3,C4 | 2 | 10 uF, 50 V, X7R, 10% | 1210 | `C2918502` |
| C5 | 1 | 100 nF, 50 V, X7R, 10% | 0603 | `C14663` |
| C7 | 1 | 2.2 uF, 100 V, X7R, 10% | 1210 | `C153036` |
| C8,C27 | 2 | 100 nF, 100 V, X7R, 10% | 0805 | `C28233` |
| C9,C10,C17 | 3 | 22 uF, 25 V, X7R, 10% | 1210 | `C309062` |
| C11,C12,C14,C15 | 4 | 1 uF, 50 V, X5R, 10% | 0603 | `C15849` |
| C13 | 1 | 47 nF, 100 V, X7R, 10% | 0805 | `C107126` |
| C16 | 1 | 22 uF, 25 V, X7R, 10% | 1210 | `C309062` |
| C18,C22,C24,C25,C41-C43 | 7 | 100 nF, 16 V, X7R, 10% | 0402 | Samsung `CL05B104KO5NNNC`, `C1525` |
| C20 | 1 | 100 nF, 16 V, X7R, 10%; U12 local bypass | 0402 | Samsung `CL05B104KO5NNNC`, `C1525` |
| C19 | 1 | 1 uF, 25 V, X5R, 10% | 0402 | `C52923` |
| C23 | 1 | 10 uF, 25 V, X5R, 10% | 0805 | `C15850` |
| C26 | 1 | 10 uF, 63 V, X7R, 10% | 1210 | Murata, `C437568` |
| C28 | 1 | 10 uF, 25 V, X7R, 10% | 1210 | `C39232` |
| C29,C33 | 2 | 100 nF, 50 V, X7R, 10% | 0603 | `C14663` |
| C30 | 1 | 10 nF, 50 V, C0G, 5% | 0603 | Murata `GRM1885C1H103JA01D`, `C85973` |
| C31 | 1 | 10 nF, 50 V, X7R, 10% | 0402 | `C15195` |
| C34 | 1 | 100 nF, 50 V, C0G, 1% | 1206 | Murata `GCM31C5C1H104FA16L`, `C1864297` |
| C35 | 1 | 2.2 uF, 50 V, X5R, 10% | 0805 | `C377773` |

### Resistors, potentiometer, and inductor

Unqualified 0402 resistors are 1%, at least 1/16 W.

| Refs | Qty | Value/function | Footprint | Exact source |
|---|---:|---|---|---|
| R1,R3,R8,R9,R11-R13,R18,R29-R35,R37,R42-R44,R46,R47,R49,R50,R55,R56 | 25 | 10 k | 0402 | `0402WGF1002TCE`, `C25744` |
| R2,R10,R25,R27,R31 | 5 | 100 k | 0402 | `C25741` |
| R4-R7,R19,R20,R28 | 7 | 4.7 k | 0402 | Yageo `RC0402FR-074K7L`, `C105871` |
| R14,R15,R24,R36,R38,R45 | 6 | 100 ohm | 0402 | `C25076` |
| R16,R17 | 2 | 0 ohm I2C isolation links | 0402 | `C17168` |
| R26 | 1 | 1 k | 0402 | `C11702` |
| R39 | 1 | 47 ohm, 1 W, 1% | 2512 | `RC2512FK-0747RL`, `C723713` |
| R40 | 1 | 910 k, 0.1% | 0402 | `RE0402BRE07910KL`, `C3921007` |
| R41 | 1 | 100 k, 0.1% | 0402 | `RT0402BRD07100KL`, `C852472` |
| R48 | 1 | 562 k, 1% | 0402 | Vishay `CRCW0402562KFKED`, `C4323390` |
| R51 | 1 | 47.0 k, 0.1% | 0402 | `RT0402BRD0747KL`, `C728561` |
| R52 | 1 | 10.0 k, 0.1% | 0402 | `RT0402BRD0710KL`, `C190095` |
| R53 | 1 | 35.7 k, 1% | 0402 | `FRC0402F3572TS`, `C2998133`; RV1 absorbs tolerance |
| R54 | 1 | 90.9 k, 0.1% | 0402 | `CPF0402B90K9E1`, `C2079068` |
| R57 | 1 | 470 ohm UART RX series | 0402 | `0402WGF4700TCE`, `C25117` |
| RV1 | 1 | 200 k, 10-turn | Bourns 3224W | `3224W-1-204E`, `C55072` |
| L1 | 1 | 47 uH | SWPA6045S | `SWPA6045S470MT`, `C36414` |

### Semiconductors, ICs, connectors, and mechanics

| Refs | Exact MPN | Footprint/package | Source/assembly |
|---|---|---|---|
| D1 | Diodes Inc. `MMSZ5242B-7-F` | SOD-123 | `C500776` |
| D2 | `SMCJ24A` | SMC | `C135154` |
| D3-D8 | Vishay `BAT54W-G3-08` | SOD-123 | `C3313038`; proven V1 substitute |
| D9 | onsemi `BAT54SLT1G` | SOT-23 | `C19726` |
| Q1 | `DMP6023LE-13` | SOT-223, tab=2 | `C154901` |
| Q2,Q3 | `2N7002K-7` | SOT-23 | `C85047` |
| Q4 | onsemi `BC847BDW1T1G` | SOT-363 Style 1 | `C82368` |
| U1 | TI `MCF8316DVRGFR` | VQFN-40 RGF + EP | `C47122159` |
| U2 | Espressif `ESP32-C6-WROOM-1-N8` | official 29-pad land pattern | `C5366877` |
| U3 | TI `TPSM365R6V3RDNR` | RDN-11 | `C18208843` |
| U4 | TI `TPS7A1601ADGNR` | MSOP-8 EP | `C6886485` |
| U5,U6 | TI `SN74LVC1G74DCTR` | DCT-8 | `C840104` |
| U7 | TI `TPS3435CAKAGDDFR` | SOT-23-8 | `C6339182` |
| U8 | TI `LM2907M-14/NOPB` | SOIC-14 | in hand, hand solder |
| U9 | TI `TLV1701AIDBVR` | SOT-23-5 | `C130035` |
| U10,U11 | TI `SN74LVC1G17DCKR` | SC-70-5 | `C10425` |
| U12 | TI `TMP1075DGKR` | `Package_SO:VSSOP-8_3x3mm_P0.65mm` (DGK) | `C2864807`; JLCPCB assembled |
| J1 | Molex `43045-0200` | exact right-angle footprint | hand |
| J2 | Molex `43650-0300` | exact right-angle footprint | hand |
| J3 | JST `B3B-PH-K-S(LF)(SN)` | vertical PH 1x3 | `C131339`, hand |
| J5 | JST `B5B-PH-K-S(LF)(SN)` | vertical PH 1x5 | `C157993`, hand |
| SW1-SW3 | C&K `PTS645SK43SMTR92LFS` | PTS645 SMD | `C221871`, RESET/BOOT/CLEAR |
| NT1 | copper net-tie, no purchased part | two 2.0 mm F.Cu pads | excluded from BOM |
| TP1-TP31 | bare plated test holes | custom 2.4 mm pad, 1.0 mm finished hole | no component |
| H1-H4 | M3 clearance | 3.2 mm NPTH, no annulus | mechanical, positions deferred |

Custom U1, U2, U3, U5/U6, NT1, and test-hole footprints require explicit pin/pad review. Explicitly
review U12's standard DGK symbol-to-pad mapping. U2 must reproduce Espressif's current land pattern
and antenna keepout, not adapt the V1 MINI footprint.

## Exact connectivity and ratsnest

This is the complete V2 named-net membership. Passive pin numbers matter even for non-polar parts.
Pins absent here are in the explicit no-connect statements or duplicate power/EP connections above.

### Input, rails, and grounds

| Net | Required endpoints |
|---|---|
| `RAW24` | J1.1, Q1.2/tab, TP1.1 |
| `PMOS_GATE` | D1.2 anode, Q1.1, R1.1, R2.2 |
| `VM24` | Q1.3, D1.1 cathode, D2.1, C1.1,C2.1,C3.1,C4.1,C5.1,C7.1,C8.1,C12.2, R2.1,R39.1, U1.9-U1.11, U3.2,U3.3, TP2.1 |
| `PGND` | J1.2, D2.2, C1.2-C5.2, U1.12,U1.15,U1.18, NT1.1, TP3.1 |
| `AGND` | all logic/analog capacitor ground pins; J3.3,J5.1; Q2.2,Q3.2; R1.2,R8.2-R10.2,R25.2,R27.2,R32.2,R33.2,R41.2,R47.2,R49.2,R53.2; RV1.2,RV1.3; SW1.2,SW2.2,SW3.2; U1.2,U1.4,U1.26,U1.41; U2.1,U2.28,U2.29; U3.10,U3.11; U4.4,U4.9; U5.4; U6.1,U6.4; U7.4; U8.12; U9.2; U10.3; U11.3; U12.4-U12.7; NT1.2; TP4.1 |
| `3V3` | C9.1,C10.1,C17.1,C18.1,C20.1,C22.1,C24.1,C25.1,C41.1,C42.1,C43.1; D9.2; J3.1; R4.1-R7.1,R11.1-R13.1,R18.1-R20.1,R29.1-R31.1,R34.1,R35.1,R37.1,R42.1,R43.2,R50.1,R52.1; U2.2; U3.4,U3.9; U5.2,U5.7,U5.8; U6.2,U6.8; U7.8; U9.5; U10.5; U11.5; U12.8; TP5.1 |
| `U3_VCC` | C11.1, R3.1, U3.8 |
| `PGOOD` | R3.2, D3.1, D8.1, U2.20, U3.1, TP9.1 |

Every scheduled capacitor not assigned another pin-2 net has pin 2 on AGND. NT1 is the only
AGND-to-PGND connection. Each pad gets its own nearby through-via to its inner-plane domain.
U3 pins 5, 6, and 7 are no-connects.

### MCF stage and controls

| Net | Required endpoints |
|---|---|
| `BUCK_SW` | U1.5, L1.1 |
| `MCF_BUCK` | L1.2, C16.1, U1.3 |
| `MCF_CP` | U1.8, C12.1 |
| `MCF_CPH` | U1.7, C13.1 |
| `MCF_CPL` | U1.6, C13.2 |
| `MCF_AVDD` | U1.27, C14.1, R28.1, TP7.1 |
| `MCF_DVDD` | U1.1, C15.1, TP8.1 |
| `MCF_BRAKE` | U1.35, R8.1 |
| `PHASE_U` | U1.13,U1.14,J2.3 |
| `PHASE_V` | U1.16,U1.17,J2.2 |
| `PHASE_W` | U1.19,U1.20,J2.1 |
| `ESP_SDA` | U2.8, R16.1 |
| `SDA` | R16.2, R6.2, U1.30, TP18.1 |
| `ESP_SCL` | U2.9, R17.1 |
| `SCL` | R17.2, R7.2, U1.31, TP19.1 |
| `ESP_SPEED` | U2.27, R14.1 |
| `SPEED` | R14.2, R10.1, U1.28, TP25.1 |
| `ESP_DIR` | U2.26, R15.1 |
| `DIR` | R15.2, R9.1, U1.34 |
| `FG` | U1.29, U2.18, R4.2, TP20.1 |
| `NFAULT` | U1.40, U2.19, R5.2, TP17.1 |
| `ALARM` | U1.39, U2.11, TP26.1 |
| `SOX` | U1.38, TP24.1 |
| `DRVOFF` | U1.21, Q2.3, R28.2, TP12.1 |
| `MCF_EXT_WD` | U1.32, R38.2, TP16.1 |

U1 pins 22-25, 33, 36, and 37 are no-connects. U1 EP41 is AGND and gets at least 12 filled-and-
capped thermal vias, 0.30 mm drill, distributed across the pad, matching the proven V1 footprint.

### ESP service

| Net | Required endpoints |
|---|---|
| `ESP_EN` | U2.3, R11.2, C19.1, SW1.1, Q4.3 |
| `ESP_BOOT` | U2.15, R12.2, SW2.1, Q4.6 |
| `ESP_GPIO8` | U2.10, R13.2 |
| `TEMP_SDA` | U2.6, R19.2, U12.1, TP30.1 |
| `TEMP_SCL` | U2.12, R20.2, U12.2, TP31.1 |
| `HALL_TACH` | U2.7, J3.2, Q3.1, R43.1, TP21.1 |
| `UART_TX` | U2.25, J5.2 |
| `UART_RX_CONN` | J5.3, R57.1 |
| `UART_RX` | R57.2, U2.24 |
| `RTS_N` | J5.4, Q4.4, R56.1 |
| `DTR_N` | J5.5, Q4.1, R55.1 |
| `AUTO_EN_B` | R55.2, Q4.5 |
| `AUTO_BOOT_B` | R56.2, Q4.2 |
| `ARM_PULSE` | U2.16, R24.1 |
| `WD_HEARTBEAT` | U2.17, R36.1, R38.1, TP13.1 |
| `MCU_CLEAR_N` | U2.23, R18.2, D6.1 |
| `WDO` | U2.21, U7.7, R37.2, D4.1, TP14.1 |

U2 pads 4,5,13,14,22 and U12 pin 3 are no-connects. No copper, vias, components, or test points
may enter the official antenna keepout except allowed module pads.

### Permission and watchdog

| Net | Required endpoints |
|---|---|
| `U5_CLK` | R24.2, R25.1, U5.1 |
| `U5_Q` | U5.5, R26.1, TP11.1 |
| `Q2_GATE` | R26.2, R27.1, Q2.1 |
| `SW_CLR` | R30.2, SW3.1, D7.1 |
| `U5_CLR_OR` | D3.2,D4.2,D5.2,D6.2,D7.2,R29.2,U10.2,TP10.1 |
| `U5_CLR_BUF` | U10.4, U5.6 |
| `SET0` | U7.1, R32.1 |
| `SET1` | U7.5, R33.1 |
| `WD_MR` | U7.2, R34.2, TP27.1 |
| `U7_WDI` | R36.2, U7.3, TP28.1 |
| `WD_EN` | R35.2, U7.6, TP29.1 |
| `OS_LOCK_OK` | U6.5, D5.1 |
| `U6_PRE_RC` | R31.2, C23.1, D8.2, U11.2 |
| `U6_PRE_BUF` | U11.4, U6.7 |

U5.3 and U6.3 inverted Q are no-connects. C42/C43 sit directly at U5/U6. U7 is configured SET0=0,
SET1=0, MR high, WD_EN high, and WDO pulled high. U10.1 and U11.1 are no-connects.

### Protected tach and analog overspeed

| Net | Required endpoints |
|---|---|
| `TACH_LDO_IN` | R39.2, C26.1, C27.1, U4.5,U4.8 |
| `TACH_FB` | U4.2, R40.2, R41.1, C30.2 |
| `TACH_DELAY` | U4.7, C31.1 |
| `+12V_TACH` | U4.1, C28.1,C29.1,C30.1, R40.1,R44.1,R46.1, U8.8,U8.9, TP6.1 |
| `TACH_DRAIN` | Q3.3, R44.2, R45.1 |
| `LM_TACHIN` | R45.2, U8.1 |
| `TACH_CP1` | U8.2, C34.1 |
| `VTACH_RAW` | U8.3,U8.4, R48.1, C35.1 |
| `RSCALE_MID` | R48.2, RV1.1 |
| `VTACH` | U8.5,U8.10, R49.1,R51.1, TP22.1 |
| `TACH_BIAS` | U8.11, R46.2,R47.1,C33.1 |
| `TLV_INN` | U9.3, R51.2, D9.3 |
| `VREF` | U9.1, R52.2,R53.1,R54.2, TP23.1 |
| `OVERSPEED_N` | U4.3, U9.4, U6.6, R42.2,R50.2,R54.1, TP15.1 |

U4.6 and U8.6/U8.7/U8.13/U8.14 are no-connects. U8.12 is AGND. D9.1 is AGND and D9.2 is 3V3.
C34.2 and C35.2 return directly to AGND.

`OVERSPEED_N` is deliberately one open-drain wired-OR node with two independent low sources: U9.4
for analog overspeed and U4.3 for loss of the protected tach supply. The name is retained for V1
continuity. Validation must stimulate and observe each source separately even though they share the
node; no separate `TACH_PGOOD_N` net exists.

## Test and service access

TP1-TP31 use 2.4 mm copper, 1.0 mm finished plated hole, no paste, and mask opening both sides. Keep
at least 2.54 mm center spacing and clearance for a miniature hook clip or 24-28 AWG pigtail. Print
full net names. Group by subsystem; exact edge and order follow routing.

| TP | Signal | TP | Signal | TP | Signal |
|---:|---|---:|---|---:|---|
| 1 | RAW24 | 10 | U5_CLR_OR | 19 | SCL |
| 2 | VM24 | 11 | U5_Q | 20 | FG |
| 3 | PGND | 12 | DRVOFF | 21 | HALL_TACH |
| 4 | AGND | 13 | WD_HEARTBEAT | 22 | VTACH |
| 5 | 3V3 | 14 | WDO | 23 | VREF |
| 6 | +12V_TACH | 15 | OVERSPEED_N | 24 | SOX |
| 7 | MCF_AVDD | 16 | MCF_EXT_WD | 25 | SPEED |
| 8 | MCF_DVDD | 17 | NFAULT |  |  |
| 9 | PGOOD | 18 | SDA |  |  |
| 26 | ALARM | 27 | WD_MR | 28 | U7_WDI |
| 29 | WD_EN | 30 | TEMP_SDA | 31 | TEMP_SCL |

J5 supplies UART access and SW1/SW2 direct EN/BOOT. Do not add phase pads or use an earth-grounded
scope on a phase. Use a rated differential probe at J2.

## Board technology and rules

- Rectangular FR-4, 1.6 mm nominal, Tg at least 150 C.
- F.Cu/B.Cu 2 oz, In1/In2 1 oz; ENIG, green mask, white silk, plated through vias.
- Minimum copper-to-edge 0.25 mm except intentional connector body overhang. Minimum signal track
  0.20 mm and every via, including filled-and-capped thermal via-in-pad, uses at least 0.30 mm drill.
  The standard via is 0.60/0.30 mm. No blind, buried, stacked, or microvias.
- Minimum plated-hole edge to track/copper clearance is 0.30 mm on every layer. The 0.20/0.25 mm
  class clearances below apply only where no plated hole is involved and the chosen fab permits them.
- Put every component on the front. All SMD parts use front-side assembly only; the named hand parts
  C1, C2, J1-J3, and J5 retain their through-hole footprints. B.Cu carries no components.
- Filled-and-capped via-in-pad is required under U1 EP and U4 EP if used there. Confirm JLC POFV.
- Record actual copper weights in KiCad instead of the V1 generic 0.035 mm on all layers.

Layer use: F.Cu components and local loops; In1 continuous AGND except compact PGND motor island;
In2 broad VM24 and 3V3 regions; B.Cu AGND pour plus unavoidable signals. No plane split beneath a
fast or sensitive signal.

| Class | Nets | Track | Via | Clearance | Additional rule |
|---|---|---:|---:|---:|---|
| PHASE | PHASE_U/V/W | 2.0 mm trunk | 1.0/0.5 mm | 0.25 mm | prefer pours; explicit U1 escape below |
| POWER24 | RAW24, VM24, PGND high current | 2.0 mm min | 1.0/0.5 mm arrays | 0.25 mm | size for 3 A and transient |
| RAIL3V3 | 3V3 | 0.50 mm | 0.60/0.30 mm | 0.20 mm | neck only at pads |
| TACH12V | TACH_LDO_IN, +12V_TACH | 0.40 mm | 0.60/0.30 mm | 0.20 mm | away from RF and phases |
| ANALOG | Hall/LM2907/VTACH/VREF | 0.25 mm | 0.60/0.30 mm | 0.20 mm | uninterrupted AGND return |
| CONTROL | remaining logic/service | 0.20 mm | 0.60/0.30 mm | 0.20 mm | ARM and heartbeat separated |

DRC must reject high-current neckdowns, antenna-keepout copper, domain bypass around NT1, unfilled
zones, and unconnected items. V1 waiver counts do not transfer.

Each U1 phase pad may use a 0.30 mm F.Cu neck for at most 1.0 mm measured from the pad edge. Merge
the two same-phase pad necks immediately into a 2.0 mm or wider trunk/pour. The escape may not use a
via; after the merge there are no neckdowns or layer changes to J2. This is the only PHASE width
exception and must be encoded as a scoped rule area rather than weakening the net class.

## Placement and routing organization

Exact coordinates are deferred. These relationships are mandatory.

1. Group J1, Q1, D1, D2, C1-C5, and U1 VM entry as one power region. J1 reaches an edge without its
   cable crossing service pads. Place C1 and C2 parallel with at least 12.1 mm center-to-center
   spacing. Their unchanged 10.6 mm footprint courtyards must have at least 1.5 mm edge clearance,
   exactly 1.0 mm more than V1's measured 11.1 mm centers and 0.5 mm courtyard gap, so normally
   inserted cans remain upright rather than touching and tilting.
2. Put U1 beside J2. Route paired half-bridges directly, parallel, one layer, to J2 in W/V/U order.
3. Limit the PGND island to bulk/TVS returns, MCF power grounds, phase current, J1 return, and NT1. No
   Hall, tach, MCU, watchdog, or RF circuit goes over it.
4. Preserve U3 reference loops. Group U5-U7, U10/U11, Q2, and passives near U1 DRVOFF but outside
   switching current.
5. Group J3, Q3, U4, U8, U9, RV1, and analog passives over uninterrupted AGND. RV1 and VTACH/VREF
   remain accessible installed.
6. Put U2 on an outward edge, antenna away from motor, aluminum plate, fasteners, bulk capacitors,
   connectors, and cables. Keep the official all-layer keepout and at least 15 mm free space ahead.
7. Put U12 and C20 at a quiet outer edge exposed to chamber air, outside the antenna keepout and
   away from U1, U3, Q1, R39, bulk capacitors, phase copper, and enclosure contact points. Keep U12
   at least 5 mm from the U2 body and 10 mm from those heat sources where placement permits. Do not
   put it beneath a connector or cable. Keep C20 at U12 pins 8/4, route TEMP_SDA/TEMP_SCL together
   over AGND with R19/R20 nearby,
   and avoid broad power copper beneath or immediately around U12 that would conduct local heat into
   the sensor. Do not split the AGND return plane to thermally isolate it.
8. Group J5, SW1, SW2, Q4, and R55-R57 at an accessible edge. Put SW3 where it is deliberate but not
   accidentally pressed while probing.
   Reserve at least 18 mm normal to the board above J5 for the mated PHR-5 housing and contacts, plus
   a 12 mm lateral cable-bend corridor in the chosen exit direction. Keep that volume clear of the
   enclosure, screws, buttons, probe approach, and other cable bundles inside the 110 x 80 x 25 mm
   controller envelope.
9. Group TP1-TP31 along accessible edges. A point may use the nearest edge rather than a long route.
   Sensitive analog test stubs must be minimal.
10. Put H1-H4 near final corners with screw, washer, standoff, and tool keepouts. Coordinates follow
   placement and the housing support pattern.
11. Reserve at least 8 mm beyond power/motor mating faces. Preserve iron access to hand parts.

Silk must label connectors and pin 1, RESET/BOOT/CLEAR, RV1 as `OVERSPEED CAL` with trip-increase and
trip-decrease direction, TP nets, W/V/U, power polarity, board name/revision, and
`PHASES: DIFFERENTIAL PROBE ONLY`. Every polarized part and cable interface must be unambiguous.

## Firmware feasibility contract

- Move MCF ALARM from GPIO14 to GPIO10. Keep every other used GPIO assignment above.
- Keep software I2C on GPIO0/1, 110 us inter-byte delay, stored address 0x01, recovery probe at 0x00.
- Keep GPIO2/SPEED for MCF wake/recovery. Normal speed command remains I2C.
- Keep one 2 Hz logical heartbeat to U7 and MCF through separate resistors. Keep GPIO18 ARM and
  GPIO19 heartbeat distinct.
- Keep GPIO15 MCU_CLEAR_N open-drain and safe through power-up/reset/panic/unconfigured states.
- UART0 GPIO16/17 becomes the only flash/recovery/runtime-console transport. Remove native-USB
  firmware after J5 qualification.
- Support J5 auto-download truth table and manual RESET/BOOT.
- Update `enter_uart_bootloader.py` and the runtime serial link to drive both RTS_N and DTR_N
  explicitly. Define port-open, port-close, error, interrupted-flash, and process-exit cleanup so both
  lines return to the released state. Qualify all four truth-table states and repeated runtime reopen.
- Add exact `0403:6015` FT231X discovery and selection tests in both the bootloader helper and runtime
  link. Retaining `0403:6001` support for V1 is allowed, but V2 selection must not silently choose an
  unrelated FTDI device when more than one is present.
- Update the app board wiring, controls pin table/comments, and ALARM-path tests for GPIO10 before V2
  firmware qualification. The existing GPIO14 implementation is V1-only.
- Keep the current MCF-owned `SoftI2c` dedicated to GPIO0/GPIO1, preserving its full target discovery,
  control-word, CRC, recovery, and 110 us inter-byte behavior. Create a separate standard-mode I2C
  controller/service on GPIO6 TEMP_SDA and GPIO11 TEMP_SCL at 100 kHz. It writes pointer `0x00` to
  U12 address `0x48`, repeated-start reads two bytes MSB first, interprets bits 15:4 as
  signed two's-complement units of 0.0625 C, converts to milli-C by rounding half-milli values away
  from zero, and rejects replies with nonzero bits 3:0 or values outside -55 C to 125 C. No U12
  transaction may use the MCF transport, and no MCF transaction may use TEMP_SDA/TEMP_SCL. A U12
  NACK, malformed value, or physically stuck temperature bus must not increment MCF bus-failure
  accounting, initiate MCF address recovery, or change drive state.
- Poll U12 once per second after allowing at least 35 ms after power/reset for its first conversion.
  This covers the 27.5 ms default period at +10% variation plus 0.3 ms reset-to-conversion start
  without accepting the indistinguishable reset value of 0 C as a measurement. Add
  `chamber_temp_milli_c: Option<i32>` to core/app telemetry and render it as JSON integer milli-C when
  valid or JSON `null` after any failed/malformed read. Add a final `chamber_temp_milli_c` CSV column;
  render `null` as an empty field. Tests must cover positive, negative, zero, first-conversion delay,
  NACK, malformed/out-of-range data, JSON, CSV, and proof that sensor errors do not enter MCF fault
  accounting, including reads attempted immediately before and at the 35 ms boundary. Do not
  configure ALERT or add temperature-based drive, speed, or permission behavior.
- Preserve D-generation MCF settings, standby not sleep, ALARM_PIN_EN, OTW_REP, EXT_WDT enabled as
  GPIO tickle, 1000 ms timeout, and latched Hi-Z watchdog fault action.

## Assembly and sourcing

- JLC assembles all top-side SMD except U8. U8 is always supplied from the in-hand stock and hand
  soldered. The complete hand-part set is C1, C2, J1-J3, J5, and U8.
- C34 is machine assembled. There are no bridges, jumper-shaped fuses, or DNP option parts.
- NT1 is copper, not a purchase item. Keep it in connectivity checks and exclude it from purchase/PnP.
- Fab BOM includes exact MPN and LCSC fields. PnP includes every JLC ref and no hand refs. The hand
  manifest names every excluded populated ref.
- Before order, update canonical `bom/bom.csv` and the generated V2 fab/LCSC maps to match this
  schedule. V1 BOM rows remain historical evidence and must not be used to order V2.
- Before V2 service, replace or explicitly version every operator artifact that currently names J7,
  SH-U09C2, the switched RTS harness, or V1 TP numbering: `docs/build.md`, `docs/probing.md`,
  `docs/controls.md`, `docs/housing.md`, `docs/observability.md`, `docs/integration.md`,
  `testing/test-matrix.csv`, `firmware/scripts/README.md`, every source/reference/generator under
  `docs/field-guides/` (including `soldering-videos.md`), all generated printable service/rebuild
  sheets, and the probe map. Keep V1 J4/NTC, 85 C board limit, GPIO6, service, and probe instructions
  explicitly labelled for V1; never present or regenerate them as V2 instructions. Build a
  separately titled V2 operator package. In particular, the current `TACH-01` row is V1-only: its
  V2 replacement must require observing TP15 `OVERSPEED_N` for the upward trip and downward raw
  comparator reset, prohibit using DRVOFF or OS_LOCK_OK as raw-reset evidence, and require a
  low-voltage power cycle plus confirmed U6 re-arm after every complete sweep before another RV1
  trim trial.
- Before V2 fab export, add a `pcb-01-v2` project/config to `pcb/tools/jlc_fab.py` so the exact command
  `python3 pcb/tools/jlc_fab.py pcb-01-v2` reads `pcb/pcb-01-v2`, includes machine-assembled C34,
  excludes only the exact hand parts and copper/no-part refs in this schedule, and emits V2 Gerbers,
  drill, BOM, CPL, and LCSC map under `pcb/pcb-01-v2/fab/`. V1 hardcoded C34/J7/J8/JP1/DNP
  exclusions may not affect V2. This is a future capture/release gate, not a claim that the current
  V1-only generator already supports V2.
- Recheck stock before order. Shortage does not authorize changing value, tolerance, dielectric,
  package, pinout, or safety behavior. Record an approved substitute here first.
- Order at least two assembled boards. Inspect U2 castellations, U1/QFN and thermal fill, U4 EP,
  polarity, connector pin 1, and net-tie copper before power.

## Validation gates

These validate the specified design and do not invite unrelated safety expansion.

### Capture and layout

- Check every IC symbol against current manufacturer data, especially U1,U2,U4,U5/U6,U7,Q4,U8,
  U12. Confirm the DGK top-view pin order, address straps, `0x48` address, and ALERT no-connect.
- Machine-compare the KiCad exported netlist with this ratsnest. Confirm every scheduled ref appears
  exactly once and every schematic ref is scheduled.
- Confirm J1/J2/J3 footprint numbering against existing cables and Q4 symbol/footprint/truth table.
- ERC: zero unexplained errors/warnings. DRC: zero unconnected and zero unexplained violations.
- Verify actual stackup, through-via-only rule, high-current neck checks, POFV, all-layer antenna
  keepout, and the single NT1 crossing.
- Before capture/layout validation, set the V2 Konnect project's accessible-test-point rule to the
  complete `TP1` through `TP31` set. Any scaffold or rule that stops at TP29 predates the dedicated
  temperature bus and is incomplete; TP30 TEMP_SDA and TP31 TEMP_SCL must receive the same edge-
  access validation as every other test hole.
- Render front/back copper, mask, silk, drill map, and component-side 3D view. Inspect connector
  orientation, cables, probes, screws, hand access, antenna, phases, and return continuity.
- Machine-check C1/C2 center spacing at or above 12.1 mm and courtyard edge clearance at or above
  1.5 mm; confirm the component-side render shows both cans parallel and independently insertable.
- Create a V2-specific probe map with the final layout, ground references, installed-access notes,
  and component-side render at `pcb/pcb-01-v2/probe-map.json`. The V1 map is prohibited because TP
  numbers are deliberately reassigned. Before V2 layout release, implement `--board` and `--map`
  arguments in `probe_guide.py` so the exact V2 gate is
  `pcb/tools/probe_guide.py --board pcb/pcb-01-v2/pcb-01-v2.kicad_pcb --map pcb/pcb-01-v2/probe-map.json --verify-board`.
  Its help/target validation and generated orientation text must come from the selected map rather
  than hardcoded J6/J7/J8 or TP1-TP28 data. Fabrication remains blocked until that command passes and
  its fresh component-side render is inspected. This command is intentionally not runnable before
  the V2 KiCad project, map, and tool arguments are created; it is an implementation gate, not a
  claim about the current V1-only tool.

### Engineering-board bring-up

1. No motor/Hall: resistance, polarity, reverse PMOS, VM24, 3V3, +12V_TACH, AVDD, DVDD, PGOOD,
   DRVOFF, and both ground domains.
2. J5 with adapter VCC absent: no back-power, auto ROM entry, erase, flash, reset, runtime UART,
   watchdog reconnect, manual fallback, and interrupted-flash cleanup.
3. Force each U5 clear source separately: PGOOD, WDO, OS_LOCK_OK, MCU_CLEAR_N, SW3. Verify no source
   is masked by a high source and nFAULT remains diagnostic only.
4. Verify U6 power-up delay, low-voltage-only reset, comparator trip, tach-supply PG trip, and fast
   discharge on PGOOD loss.
5. Calibrate the 200 RPM trip using the RV1 procedure above, record raw reset near 180 RPM, verify
   Hall/FG plausibility, and run the V2-versioned TACH matrix. The analog architecture and target
   speeds remain unchanged; the current V1 `TACH-01` procedure is not sufficient for V2 evidence.
6. Verify MCF communication, address recovery, wake, watchdog, ALARM, nFAULT, SOX, FG, DIR, stop,
   digital speed command, and concurrent TMP1075 reads before energizing the installed motor. Capture
   concurrent traffic and prove that a complete MCF recovery sweep appears only on SDA/SCL, U12
   traffic appears only on TEMP_SDA/TEMP_SCL, and either bus remains functional when the other is
   held low during an engineering-board fault-injection test.
7. With the board powered, motor stopped, and temperatures equilibrated for at least 10 minutes,
   compare U12 with a calibrated reference probe adjacent to its package; require agreement within
   2 C. Repeat at powered closed-housing steady operation, verify the reported value rises
   monotonically when the chamber is warmed, and verify sensor polling does not disturb MCF
   transactions. Record the local offset if stable; do not hide excess or variable error with a
   firmware correction.
8. Repeat applicable no-load, loaded, insertion, cutoff, coast, stall, fault, thermal, EMI, and
   closed-housing tests for the new layout. The V2 thermal gate is the established eight-hour run at
   170 RPM in the final closed housing. Throughout that run, the U2-area board temperature, measured
   with a separate probe at U2 rather than inferred from U12, must remain at or below 75 C. Record
   both U2 and U12 traces and all other measured data in the test matrix.

## Evidence and adversarial review

The baseline uses the released V1 KiCad board/schematic, as-built BOM, electrical and controls docs,
probe map, commissioning records, and full relevant Claude/Codex sessions. Key sessions include
Codex `01a03ffa-6163-7fb2-8f87-11949bf26006` and Claude
`310fdd88-ad25-4a57-8272-e9943a4aee4d`, `7f56a23a-8227-4397-9974-bb92d85e20f7`,
`d7bd150a-a9e5-4d5f-bbad-29e9b183f6c2`, and `f5c91add-c948-48c7-93d9-badf70e1b2fc`.

A request to add a safety subsystem is not actionable without a demonstrated V1 failure mode or
violated existing invariant. Incorrect implementation, lost end-to-end behavior, component stress,
unroutable constraints, service hazards, sourcing errors, and incomplete validation remain in scope.

| Round | Lenses | Useful findings and disposition |
|---:|---|---|
| 1 | Electrical end-to-end; commissioning/firmware; BOM/ratsnest/history | Applied: 75 C WROOM thermal ceiling; explicit dual-line host control and cleanup; GPIO10 firmware/doc delta; ALARM and watchdog test points; U3.11 ratsnest endpoint; shared U4/U9 open-drain node explanation; V2-only probe-map and canonical-BOM gates; corrected D1 MPN. Rejected: preserving V1 TP numbers, treating copper NT1 as a populated part, restoring C32, and replacing Espressif's verified cross-coupled anti-reset circuit with grounded emitters. |
| 2 | Pin/datasheet; manufacturing/layout; completeness/contract | Applied: corrected U5 clear-diode polarity; corrected TPS3435 timeout to fixed 1.6 s; selected DTR-capable `UMFT231XA-01` and exact cable map; added a scoped 0.30 mm/1.0 mm U1 phase escape; added 0.30 mm PTH clearance and J5 mating/bend envelope; clarified the front-side SMD plus named THT assembly rule. |
| 3 | Electrical convergence; service/manufacturing convergence; history/intent convergence | Two lenses found no actionable defect. Applied the service lens findings: exact FT231X `0403:6015` discovery/selection requirement and a gate to version or replace every V1 J7/SH-U09C2/operator artifact before V2 service. A fresh round is required because this round produced useful feedback. |
| 4 | Electrical convergence; service/manufacturing convergence; history/intent convergence | Electrical lens found no useful feedback. The spec now requires parameterizing the V1-hardcoded probe verifier for explicit V2 board/map paths and explicitly V1-versioning the field-guide source/README so it cannot regenerate a wrong J7 sheet. A fresh round is required. |
| 5 | Electrical/history convergence; service and generated-artifact convergence | Electrical/history lenses found no useful feedback. Applied one service finding: the main integration-binder and PCB rebuild-booklet generators are now included in the V1-version/V2-replacement gate because they can regenerate F1, C34, J7, and GPIO14 instructions. A fresh round is required. |
| 6 | Electrical/tool boundary; service/manufacturing; history/tooling | Clarified probe parameterization as a future V2 implementation gate. Expanded V1-versioning to every field-guide source/reference, including stale C34 soldering media. Added an exact `jlc_fab.py pcb-01-v2` requirement with V2-specific population rules and outputs. A fresh round is required. |
| 7 | Electrical/spec convergence; service/manufacturing convergence; history/tool-boundary convergence | No useful feedback from any lens. The spec is converged for schematic capture and layout. |
| 8 | Sensor electrical/ratsnest; firmware/telemetry end to end; thermal/layout/manufacturing | Electrical and physical lenses found no useful defect. Applied firmware findings: require a single shared-bus owner with a standard TMP1075 transaction path, isolate sensor errors from MCF recovery/fault accounting, and define optional JSON/CSV telemetry plus tests. Also corrected the initial comparison to power U12 while holding the motor stopped. A fresh round is required. |
| 9 | Electrical/protocol convergence; firmware/evidence convergence; sourcing/layout/doc convergence | Electrical lens found no useful defect. Applied cross-document findings: version the dedicated-MCF transport rule for V1 and define V2 shared ownership; add canonical V2 temperature and U2 thermal matrix rows; mark stale J4/85 C operator material as V1; and make U8 unconditionally hand-assembled from in-hand stock. Raised the first-read gate from 30 ms to 35 ms to cover worst-case conversion timing and required boundary tests. A fresh round is required. |
| 10 | Hardware/firmware convergence; commissioning end to end; operator-doc convergence | Applied operator-doc findings: `housing.md`, `DRV-05`, and `motor-contingency.md` now label 85 C as V1-only, point V2 to its independent U2-area 75 C limit, and state that U12 cannot substitute for the U2 probe. Hardware, bus, timing, and ratsnest lenses otherwise found no useful defect. A fresh round is required. |
| 11 | Electrical/spec convergence; telemetry/matrix convergence; documentation convergence | Electrical lens found no useful defect. Corrected the matrix's pre-35 ms wording: the field remains present but unavailable as JSON `null` and empty CSV. Bound V2's U2-area 75 C gate to the established eight-hour 170 RPM final-housing run. A fresh round is required. |
| 12 | Electrical/bus convergence; firmware/commissioning convergence; sourcing/doc convergence | Applied one bus-architecture finding: the implemented broad MCF recovery sweep would send MCF control/CRC bytes to a shared U12 at `0x48`, while excluding that valid MCF address would weaken recovery. U12 now uses a dedicated GPIO6/GPIO11 I2C bus with R19/R20 pull-ups and TP30/TP31; the MCF bus and complete recovery behavior remain unchanged. A fresh round is required. |
| 13 | Dedicated-bus electrical/firmware convergence; sourcing/ref-reuse convergence; validation convergence | Applied one wording finding: the delete list now explicitly deletes R21 and only R20's V1 USB function/value, while retaining and reassigning the R20 designator as V2's TEMP_SCL pull-up. The dedicated bus, ratsnest, firmware, and validation lenses otherwise found no useful defect. A fresh round is required. |
| 14 | Electrical/spec convergence; firmware/commissioning convergence; tooling/ref-reuse convergence | Two lenses found no useful defect. Added one capture gate: the concurrent V2 Konnect project rule must cover TP1-TP31 rather than the pre-sensor TP1-TP29 set, including edge accessibility for TEMP_SDA and TEMP_SCL. A fresh round is required. |
| 15 | Electrical/spec convergence; firmware/commissioning convergence; Konnect/tooling convergence | Hardware and firmware lenses found no useful defect. Updated the committed V2 Konnect project rule itself from TP1-TP29 to TP1-TP31, explicitly naming TEMP_SDA and TEMP_SCL, so the documented accessibility gate is enforced. A fresh round is required. |
| 16 | Electrical/firmware convergence; commissioning/tooling convergence; fabrication-rule convergence | Two lenses found no useful defect. Resolved a pre-existing via-rule contradiction: 0.20 mm filled/capped thermal vias are now an explicit exception limited to U1/U4 exposed pads, while every ordinary via retains the 0.30 mm minimum. Konnect's project-wide minimum permits the exception and its design rule preserves the ordinary limit. A fresh round is required. |
| 17 | Electrical/commissioning convergence; fabrication-rule enforcement convergence | Two lenses found no useful defect. The remaining lens showed Konnect's scalar 0.20 mm minimum could not enforce the intended EP-only exception. Removed the exception: all vias now use at least 0.30 mm drill, and U1 uses the proven V1 twelve-via 0.30 mm POFV pattern. A fresh round is required. |
| 18 | Electrical/spec convergence; firmware/commissioning convergence; fabrication/tooling convergence | No useful feedback from any lens. The chamber-sensor revision, dedicated bus, complete ratsnest, firmware and telemetry contract, V1/V2 documentation boundary, validation evidence, and Konnect rules are converged for schematic capture and layout. |
| 19 | Bulk-cap mechanical spacing; option-bank deletion; overspeed-calibration procedure | C1/C2 geometry and C36-C40 deletion lenses found no defect. Applied one commissioning finding: define bridge-disabled TP15 observation of raw comparator trip/reset and low-voltage power-cycle/re-arm between RV1 trim trials. A fresh round is required. |
| 20 | Mechanical/electrical convergence; calibration/commissioning convergence; V1 evidence convergence | C1/C2 spacing, C36-C40 deletion, and the RV1 circuit were consistent. Applied one documentation finding: the canonical V1 `TACH-01` row lacks TP15 raw-reset evidence and U6 re-arm between trials, so the spec now makes that row V1-only and defines its required V2 replacement. A fresh round is required. |
