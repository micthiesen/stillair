# PCB-01 probing field guide

This is the canonical human workflow for locating and probing PCB-01. It supplements
[`observability.md`](observability.md), which defines measurement authority and scope safety.
The machine-readable location and pin data lives in
[`pcb/pcb-01/probe-map.json`](../pcb/pcb-01/probe-map.json). Print an exact hookup with:

```bash
pcb/tools/probe_guide.py map
pcb/tools/probe_guide.py TP7
pcb/tools/probe_guide.py TP2 --mode resistance
pcb/tools/probe_guide.py J8
pcb/tools/probe_guide.py --verify-board
```

`--verify-board` compares every retained test-point coordinate/net and every numeric connector pin
against the committed KiCad board through the existing read-only board parser. Run it after any PCB
layout change. Never update the map from memory.

## Physical orientation

Every instruction uses the **component-side view** with the board held as follows:

- C1 and C2, the upper two large radial capacitors, are at upper-left.
- J5 and J6 USB-C are on the top edge.
- J2, J4, and J3 are on the bottom edge.
- J1 is on the left edge.
- The ESP32-C6 module and J8 are on the right.

```text
PCB-01, component side, not to scale

  TOP: J5 / J6 USB-C
  +----------------------------------------------------------------+
  | H3   C1      C2      TP5  TP4       J5       TP26/28   J6   H4 |
  | TP1  J1/Q1       TP3                                           |
  |                   TP2       U3/TP9            ESP U2            |
  | D2   TP8/16   U1   TP12/7  TP20/17/18/19   TP22      TP23/21  |
  |                       TP11/24/27/10       U7/U9       TP6  J8  |
  | H1      C6/J2             J4                    J3          H2 |
  +----------------------------------------------------------------+
  BOTTOM: J2 / J4 / J3
```

If C1/C2 are not upper-left and J8 is not lower-right, stop. The board is not in the documented
frame and connector pin descriptions will be misleading.

## Standard probing exchange

The agent gives **one hookup at a time** in this exact order:

```text
PROBE:     <test point> - <net> - <measurement mode>
STATE:     <power off/on, USB state, discharge requirement, motor state>
ORIENT:    component side; C1/C2 upper-left; J8 lower-right
FIND:      <relative position using nearby labelled components>
REFERENCE: <black lead or scope ground point and ground domain>
TIP:       <red lead or probe-tip point>
INSTRUMENT:<DMM/scope, volts/ohms, AC/DC coupling, x1/x10, range>
EXPECTED:  <number or state-dependent behavior>
STOP:      <specific abort conditions>
REPORT:    <literal result template>
```

The user replies `connected` only after the unpowered hookup is stable and inspected. The agent may
then apply the named power state and acquire the reading. Power returns off before any lead moves.
Do not ask the user to hold a probe while simultaneously operating power, software, or the rotor.

Example:

```text
PROBE:      TP7 - MCF_AVDD - DC volts
STATE:      Connect with 24 V off, USB disconnected, and capacitors discharged.
ORIENT:     Component side; C1/C2 upper-left; J8 lower-right.
FIND:       Immediately upper-right of U1, below TP12, beside C14 and R4-R7.
REFERENCE:  Black lead to TP4 (AGND), the large top-edge ring above C11/U3.
TIP:        Red lead to TP7.
INSTRUMENT: DMM, DC volts, autorange or 5 V range.
EXPECTED:   About 3.3 V after controlled power-up.
STOP:       Current limit, heat, smell, smoke, spark, or unstable lead placement.
REPORT:     `TP7 MCF_AVDD: __ V, steady/rising/falling, TP4 reference`
```

## Ground and instrument rules

- **TP4 is the default AGND reference** for logic, analog, 3.3 V, 12 V tach, and MCF internal-rail
  measurements. TP26 and TP28 are additional AGND access near J6.
- **TP3 is the default PGND reference** for RAW24 and VM24. TP27 is a second PGND point near U1.
- AGND and PGND join only through the board's designed net tie. Do not casually bridge them with
  multiple instrument grounds.
- The OWON VDS1022I's two BNC grounds are common. Both channels must use the same ground domain.
- Use x1 for 0 to 3.3 V logic, SOX, AVDD, and DVDD when the chosen range does not clip.
- Use x10 for VM24 and RAW24. Confirm the scope's configured attenuation and at least 40 V range.
- Never connect a grounded scope lead to J2 U, V, or W. Phase measurements require a rated
  differential probe. USB isolation does not isolate the OWON channels from one another.
- Resistance, continuity, diode, and capacitance modes require all power removed, USB disconnected,
  and voltage checked below 1 V before switching the meter out of voltage mode.
- Connect and remove every lead with power off. The only exception is moving a purpose-built,
  finger-safe selector that the specific test procedure explicitly permits.

## When to attach a temporary wire

Attach an insulated pigtail instead of repeatedly hand-probing when any of these is true:

- the same point will be used for three or more power cycles or captures;
- the board will be installed overhead or enclosed;
- the pad is too small to clip securely, including bare J8 pads;
- a long automated capture needs hands-off strain relief;
- two probes, USB, and power would otherwise crowd the same area.

Use 30 AWG insulated Kynar or similarly light wire for low-voltage logic and DC rail sensing only;
never use a probe pigtail to carry supply or motor current. Keep it only as long as needed, normally
50 to 100 mm. Solder only with all sources removed and the
bulk capacitors discharged. Route the insulated portion flat to the board, add Kapton strain relief
away from the joint, inspect for bridges under magnification, and label both ends with the net name.
Remove the pigtail after the campaign unless it is deliberately promoted to a service lead.

Do **not** use a long pigtail for high-bandwidth VM24 switching/transient measurements. Its loop
inductance can create or hide ringing. Use a direct x10 probe with a spring ground at the intended
power-domain reference. Do not attach ordinary pigtails to motor phases, switch nodes, fine-pitch IC
pins, USB data pads, or an energized board.

For repeated J8 work, populate the selected 1.27 mm header or attach inspected pigtails once while
the board is on the bench. Repeatedly landing handheld hooks on the bare J8 pads is not an acceptable
installed workflow.

## Test-point location index

Coordinates are retained in the JSON map for verification. Human instructions use landmarks first.

| TP | Net | Human location |
|---|---|---|
| TP1 | RAW24 | Far left edge, left of R1/R2 and above D1 |
| TP2 | VM24 | Lower ring of TP3/TP2 pair, right of C2/F1 |
| TP3 | PGND | Upper ring of TP3/TP2 pair, right of C2/F1 |
| TP4 | AGND | Large top-edge ring above C11/U3, right of TP5 |
| TP5 | 3V3 | Large top-edge ring above C7, left of TP4 |
| TP6 | +12V_TACH | Lower-right tach area, left of J8 and above C27 |
| TP7 | MCF_AVDD | Upper-right of U1, below TP12, beside C14/R4-R7 |
| TP8 | MCF_DVDD | Upper ring of TP8/TP16 pair, left of U1 |
| TP9 | PGOOD | Above SW1, right of R3, below C9/C10 |
| TP10 | U5_CLR_OR | Bottom ring of TP11/TP24/TP27/TP10 column |
| TP11 | U5_Q | Top ring of TP11/TP24/TP27/TP10 column |
| TP12 | DRVOFF | Upper-right of U1, directly above TP7 |
| TP13 | WD_HEARTBEAT | Upper ring of TP13/TP14 pair below C20 |
| TP14 | WDO | Lower ring of TP13/TP14 pair above U6 |
| TP15 | WD_MR | Above R34, between U10 and U7 |
| TP16 | MCF_EXT_WD | Lower ring of TP8/TP16 pair, left of U1 |
| TP17 | NFAULT | Second ring of TP20/TP17/TP18/TP19 column |
| TP18 | SDA | Third ring of TP20/TP17/TP18/TP19 column |
| TP19 | SCL | Bottom ring of TP20/TP17/TP18/TP19 column |
| TP20 | FG | Top ring of TP20/TP17/TP18/TP19 column |
| TP21 | HALL_TACH | Unlabelled far-right ring beside R43/Q3, below TP23 |
| TP22 | VTACH | Middle-right, left of TP23, above C32/R49 |
| TP23 | VREF | Large far-right ring beside Q3, above TP21 |
| TP24 | OVERSPEED_N | Unlabelled second ring of TP11/TP24/TP27/TP10 column |
| TP25 | VBUS_SENSE | Below-right of J6, beside U12/R21/R58 |
| TP26 | AGND | Below-left of J6, above R55/R11 |
| TP27 | PGND | Unlabelled third ring of TP11/TP24/TP27/TP10 column |
| TP28 | AGND | Below TP26 and left of J6/U12 |

Three dense points lack usable silkscreen labels: TP21 is the lone ring beside R43/Q3; TP24 is the
second ring and TP27 is the third ring in the four-ring column immediately right of U1.

## Connector pin views

All diagrams use the component-side orientation above.

### J8 SCOPE, lower-right

Odd pins are inboard/left. Even pins are at the board edge/right.

```text
inboard                     board edge
1 VM24                  2 PGND
3 3V3                   4 +12V_TACH
5 DRVOFF                6 SPEED
7 FG                    8 NFAULT
9 SOX                  10 AGND
           top to bottom
```

### J7 PROGRAM, centre-right

```text
top:     2 UART_TX   4 ESP_EN    6 AGND
bottom:  1 3V3       3 UART_RX   5 ESP_BOOT
```

J7 pin 1 is board 3.3 V, not a power input. A programmer must not drive it while 24 V is present.

### Edge connectors

- **J1 POWER, left edge:** pin 1 RAW24_IN is left/outboard; pin 2 PGND is right/inboard.
- **J2 MOTOR, bottom edge:** left-to-right is pin 3 U, pin 2 V, pin 1 W.
- **J3 HALL, bottom edge:** left-to-right is pin 1 3V3, pin 2 HALL_TACH, pin 3 AGND.
- **J4 TEMP, bottom edge:** left-to-right is pin 1 TEMP_SENSE, pin 2 AGND.
- **J5 I2C, top edge:** board pads left-to-right are pin 4 SCL, pin 3 SDA, pin 2 3V3,
  pin 1 AGND. Prefer TP18/TP19/TP4.
- **J6 USB-C, top edge:** use a cable rather than hand-probing. VBUS does not power the board;
  TP25 exposes the divided VBUS_SENSE signal.
- **JP1 MODE/SYNC:** left-to-right is pin 1 AGND, pin 2 MODE_SYNC, pin 3 3V3.

## Updating this guide

The KiCad board remains the physical authority. After a layout revision:

1. Open the correct board in KiCad and confirm the component-side orientation.
2. Update `probe-map.json` from board truth, including relative human landmarks.
3. Run `pcb/tools/probe_guide.py --verify-board`.
4. Generate and inspect a fresh component-side render with `bash pcb/tools/render_board.sh`.
5. Update this document only after the map and render agree.

Do not edit `.kicad_pcb` or other KiCad object-graph files to maintain this guide.
