# PCB-03 display bridge

PCB-03 is an optional, fully hand-assembled bridge between PCB-01 V2's dedicated temperature
I2C bus and a small SPI e-paper display. It is not part of the fan safety architecture. Its
ordinary absence, reset, cable failure, or firmware failure must not affect motor control, fault
handling, temperature acquisition, USB recovery, or the analog overspeed chain. A device that
physically holds the shared I2C lines low is the documented exception for temperature acquisition.

## Selected architecture

- Host connection: PCB-01 V2 `TP5 3V3`, `TP4 AGND`, `TP30 TEMP_SDA`, and `TP31 TEMP_SCL`.
- J1: JST `S4B-PH-K-S`, side-entry PH 2.0 mm header. Pin 1 `AGND`, pin 2 `3V3`, pin 3
  `TEMP_SDA`, pin 4 `TEMP_SCL`.
- U1: NXP `SC18IS606PWJ`, active TSSOP-16 I2C-to-SPI bridge at 7-bit address `0x28`.
- U2: TI `PCA9536DR`, active SOIC-8 four-bit I2C GPIO expander at fixed 7-bit address `0x41`.
- Display connection: J2 JST `S8B-PH-K-S`, side-entry PH 2.0 mm header. It uses a purpose-built
  straight-through PHR-8-to-PHR-8 cable to the Waveshare 1.54-inch black/white 200 x 200 SPI
  e-paper module. The module's included PH-to-loose-socket lead is not used.
- Existing V2 device: TMP1075 remains at `0x48`. No address conflicts exist.
- Board: 50 x 30 mm, two layers, 1 oz copper, 1.6 mm FR-4, all components on the top side,
  with two 2.2 mm NPTH M2 mounting holes on the vertical centerline.

The bridge avoids a second programmable controller. ESP firmware writes e-paper command and image
data through U1 and controls the display's sideband pins through U2.

## Schematic contract

### J1 host interface

| Pin | Net | Source on PCB-01 V2 |
|---:|---|---|
| 1 | `AGND` | TP4 |
| 2 | `3V3` | TP5 |
| 3 | `TEMP_SDA` | TP30 |
| 4 | `TEMP_SCL` | TP31 |

PCB-01 V2 already supplies 4.7 kOhm pull-ups on TEMP_SDA and TEMP_SCL. PCB-03 must not duplicate
them. The host pigtail is soldered to V2's plated test holes with power removed and terminates in a
PHR-4 housing. J1 is keyed. Wire `TP4` to J1.1, `TP5` to J1.2, `TP30` to J1.3, and `TP31` to
J1.4; the order in which the test points are listed elsewhere is not the connector pin order.

### U1 SC18IS606PWJ

| Pin | Signal | Connection |
|---:|---|---|
| 1 | SDA | `TEMP_SDA` |
| 2 | SCL | `TEMP_SCL` |
| 3 | active-low INT | R1 10 kOhm pull-up to `3V3`; otherwise unused |
| 4 | active-low RESET | `BRIDGE_RESET_N`, R2 10 kOhm pull-up to `3V3` |
| 5, 6, 7 | A2, A1, A0 | `AGND`, selecting `0x28` |
| 8 | CS2/GPIO2 | no connect |
| 9 | CS0/GPIO0 | `EPD_CS_N` |
| 10 | MOSI | `EPD_DIN` |
| 11 | SPICLK | `EPD_CLK` |
| 12 | VDD | `3V3`, bypassed by C1 100 nF |
| 13 | VSS | `AGND` |
| 14 | CITO / MISO | R3 10 kOhm pull-down to `AGND`; the selected display is write-only |
| 15 | VREFP | `3V3` |
| 16 | CS1/GPIO1 | no connect |

U1 operates at up to 400 kHz I2C and 1.875 MHz SPI with a 1024-byte buffer. Configure SPI mode 0,
MSB first, at no more than 1.875 MHz. V2 initially runs this bus at 100 kHz. Each SPI transfer is an
I2C write beginning with function ID `0x01` for CS0; that function byte is not sent to the display.
A 200 x 200 monochrome frame is 5,000 bytes and requires four 1024-byte payload chunks plus one
904-byte chunk. After each I2C STOP, U1 performs the SPI transfer and may NACK while busy; firmware
must wait briefly, poll address `0x28` for ACK, impose a bounded timeout, and support normal clock
stretching. `BRIDGE_INT_N` is not routed back to the ESP.

### U2 PCA9536DR

| Pin | Signal | Connection and boot state |
|---:|---|---|
| 1 | IO0 | `EPD_DC`; input with weak pull-up after power-on, then push-pull output |
| 2 | IO1 | `EPD_RESET_N`; input with weak pull-up after power-on, then push-pull output |
| 3 | IO2 | `EPD_BUSY`; input |
| 4 | VSS | `AGND` |
| 5 | IO3 | `BRIDGE_RESET_N`; input with weak pull-up after power-on, then push-pull output |
| 6 | SCL | `TEMP_SCL` |
| 7 | SDA | `TEMP_SDA` |
| 8 | VDD | `3V3`, bypassed by C2 100 nF |

U2's power-on input state and the external U1 reset pull-up leave both reset lines released while
the ESP boots. This is intentional: U1 must be reachable before firmware can control its reset.
EPD chip select remains inactive, so the released display cannot interpret traffic during boot.
Firmware must first write output register `0x01 = 0x00`, then configuration register
`0x03 = 0x04`, leaving only IO2 as an input. It then performs explicit bridge and display reset
sequences before the first SPI transfer.

### J2 display interface

| Pin | Net | Waveshare signal |
|---:|---|---|
| 1 | `3V3` | VCC |
| 2 | `AGND` | GND |
| 3 | `EPD_DIN` | DIN / MOSI |
| 4 | `EPD_CLK` | CLK / SCK |
| 5 | `EPD_CS_N` | CS, active low |
| 6 | `EPD_DC` | DC |
| 7 | `EPD_RESET_N` | RST, active low |
| 8 | `EPD_BUSY` | BUSY, active high on the selected monochrome V2 module |

C3 is 4.7 uF from `3V3` to `AGND` at J2. The Waveshare module contains its own panel power circuit.
The selected black/white module refreshes in about 2 seconds and specifies 26.4 mW typical refresh
power. PCB-03's two ICs add at most a few milliamps, leaving ample margin inside V2's approximately
209 mA worst-case 3.3 V headroom.

## Mechanical and placement contract

- Board origin is local `(0, 0)` at the northwest corner; KiCad absolute origin is `(50, 50)` mm.
- Outline is 50 x 30 mm.
- H1 and H2 are 2.2 mm NPTH at local `(25,4.5)` and `(25,26.5)` mm. The centerline pair avoids
  both side-entry connector courtyards and leaves room for cable strain relief at either edge.
- J1 is centered on the west edge and its mating face points west.
- J2 is centered on the east edge and its mating face points east.
- Put U1 near J2 so `EPD_CLK`, `EPD_DIN`, and `EPD_CS_N` are short and direct.
- Put U2 between U1 and J2 so the four sideband nets remain short and easy to inspect.
- Put C1 and C2 immediately at their IC supply pins. Put C3 at J2 pins 1 and 2.
- Keep all reference text visible after assembly. Print the complete J1 and J2 pin order on the
  back silkscreen and label both cable destinations on the front.
- The installed bracket or enclosure must retain both cable bundles with a short service loop.
  Neither connector's through-hole solder joints are the cable strain relief.
- This is a hand-routed board. Placement ends with a clean ratsnest; no traces or zones are added
  before Michael routes it.

## Hand assembly and sourcing

All SMD parts are deliberately hand-solderable: U1 is 0.65 mm-pitch TSSOP, U2 is 1.27 mm-pitch
SOIC, and passives are 0603. J1 and J2 are through-hole. The PH family matches PCB-01/PCB-02 and
uses the standard `SPH-002T-P0.5S` contacts already in stock. New PHR-4 and two PHR-8 housings are
inexpensive; the headers and bridge ICs are board-specific purchases. The display harness uses
eight 24-30 AWG conductors and 16 stock contacts. It does not use the low-insertion-force contact.

PCB-03 is ordered as bare boards only. There is no JLCPCB assembly BOM or CPL. Generate Gerbers,
drill files, a human-readable BOM, and front/back assembly drawings when routing is complete.

## Firmware contract

- Probe `0x28` and `0x41` after the required TMP1075 transaction path is healthy. Missing optional
  display hardware is not a boot fault and must not delay or suppress supervision.
- Initialize U2 output latches before enabling outputs. Reset U1 and the display explicitly before
  each display initialization.
- Treat `EPD_BUSY = 1` as busy. Do not reuse the active-low driver for Waveshare's three-color
  Module (B). With J2 unplugged, U2's weak input pull-up also reads busy. A persistent BUSY-high
  timeout therefore means display absent or disabled, never a boot or supervision fault.
- Keep all display work outside the supervisor timing path. Use bounded I2C transactions and yield
  between image chunks.
- One thread-mode owner must serialize TMP1075, SC18IS606, and PCA9536 access on GPIO6/GPIO11.
  Wrap every transaction in a software timeout. A stuck SDA or SCL line makes both temperature and
  the optional display unavailable for that boot; bus clear may be attempted once, but U2 cannot
  reset U1 while the shared bus itself is wedged. Motor supervision and both overspeed layers remain
  independent and continue operating.
- Use one static `[u8; 5000]` framebuffer in BSS. Do not allocate it on a task stack or from the
  Matter bump allocator.
- Refresh only on a meaningful state change or a conservative periodic interval. Never make display
  completion a prerequisite for a control action.
- A display-bus error disables display updates for that boot after a bounded recovery attempt. It
  must not alter the existing MCF bus, TEMP sensor result, drive permission, or fault state.
- The initial page should show commanded RPM, measured FG RPM, chamber temperature, direction,
  supervisor state, and the highest-priority active fault. Exact typography is firmware work, not
  a PCB release gate.

## Release gates

The schematic is ERC-clean. The placed, unrouted board has zero DRC violations and 33 expected
unconnected items. Connector mating faces point outward, all component courtyards are clear, and
the complete connector pin orders are printed on the back silkscreen.

Before fabrication release, using the exact display that will be installed:

1. Freeze the label part number and hardware revision for the plain monochrome Waveshare 1.54-inch
   V2 module, currently identified by Waveshare as HINK-E0154A05 / WFC0000CZ07, and prove it operates
   from `3V3` for both power and logic. Do not substitute Module (B) or Module (G).
2. Bench-wire the actual display to an SC18IS606 and prove that command `0x24` followed by four
   1024-byte chunks and one 904-byte chunk produces a correct image despite CS toggling between
   chunks. Failure changes the architecture to direct ESP SPI or a local controller.
3. Run a slow-ramp and brownout recovery check on PCA9536 and confirm the documented initialization
   sequence always regains control of both reset lines.

Michael may route the present reviewed placement. Do not order boards until the three bench gates
above pass. Routing completion then requires zero unrouted items, a reviewed headless DRC result,
filled-ground verification, final renders, and bare-board fabrication outputs.
