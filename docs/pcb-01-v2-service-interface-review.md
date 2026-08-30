# PCB-01 V2 service-interface review handoff

Status: **closed and superseded 2026-08-30**

Decision: PCB-01 V2 uses native USB-C only. J5, Q4, R55-R57, the FTDI adapter path, and all
RTS/DTR/UART nets were removed from the schematic and PCB. J4 connects the ESP32-C6 native USB
Serial/JTAG peripheral through series damping and dedicated data/CC ESD protection; board power is
required, and BOOT/RESET provide manual ROM recovery. The analysis below is retained only as the
record of why the FTDI design was rejected.

Date: 2026-08-29

## Question for the reviewing session

Confirm or revise the PCB-01 V2 J5 UART service design so the exact external adapter can remain
connected while PCB-01 is powered or unpowered, cannot back-power the 3V3 rail, enters the ESP32-C6
ROM loader automatically through standard `esptool` RTS/DTR sequencing, resets into the application,
and supports the 115200-baud runtime console. Do not rely only on a post-fabrication bring-up gate.
Resolve the electrical mechanism before routing or ordering the board.

The current DSD TECH SH-U09C2 is not the V2 adapter. The frozen V2 spec intentionally selects FTDI
`UMFT231XA-01`, which exposes both RTS# and DTR#. The question is whether the current board-side
interface is electrically safe when that USB-powered module is connected to an unpowered target.

## Current V2 design

Authority: [`pcb-01-v2.md`](pcb-01-v2.md), especially "External interfaces", "Automatic
programming", "ESP service", "Firmware feasibility contract", and "Engineering-board bring-up".

- J5 is keyed JST PH 1x5: pin 1 AGND, pin 2 board `UART_TX`, pin 3 board `UART_RX_CONN`, pin 4
  `RTS_N`, pin 5 `DTR_N`. It intentionally carries no power.
- Adapter wiring is UMFT231XA GND to J5.1, RXD to J5.2, TXD to J5.3, RTS# to J5.4, and DTR# to
  J5.5. FTDI V3OUT, VCCIO, VCC, and VBUS remain unconnected to the target.
- The UMFT231XA remains in its default USB-powered, 3.3 V VCCIO configuration.
- R57 is 470 ohm between adapter TXD and ESP32-C6 RXD0.
- Q4 `BC847BDW1T1G` plus R55/R56 10 k implements Espressif's cross-coupled auto-download circuit.
  Manual RESET and BOOT buttons remain.
- The exported KiCad netlist matches the specified endpoints. Relevant nets are:
  - `UART_TX`: U2.25 to J5.2
  - `UART_RX_CONN`: J5.3 to R57.1; `UART_RX`: R57.2 to U2.24
  - `RTS_N`: J5.4, Q4.4, R56.1; R56.2 to Q4.2
  - `DTR_N`: J5.5, Q4.1, R55.1; R55.2 to Q4.5
  - Q4.6 pulls `ESP_BOOT`; Q4.3 pulls `ESP_EN`
- Q4's implemented pin mapping agrees with onsemi SOT-363 Style 1 and the Espressif truth table.

## Issue found

The automatic BOOT/RESET topology is correct, but the current specification does not establish its
"no back-power" requirement by construction.

FTDI documents that the UMFT231XA ships with JP1 shorted, connecting its internal 3.3 V regulator to
VCCIO. TXD, RTS#, and DTR# are therefore powered outputs whenever the adapter is active on USB. V2
connects those live outputs to a board whose 3V3 rail may be off:

- TXD reaches ESP32-C6 RXD0 through only 470 ohm. This limits injection current but is not isolation.
- RTS# and DTR# reach the Q4 base/emitter network through the two 10 k resistors and transistor
  junctions. The cross-coupled circuit prevents continuous reset when both controls are asserted;
  it is not specified as powered-off isolation.
- The V2 validation gate says to prove no back-power on an engineering board, but fabrication would
  already have occurred. The earlier paragraph requires pre-order qualification on a development
  module, yet no retained result currently proves the exact UMFT231XA plus Q4 plus unpowered-target
  condition.

Do not change UMFT231XA JP1 so PCB-01 supplies only VCCIO without reviewing FTDI's power guidance.
FTDI explicitly says powering VCCIO from a different source than USB-powered VCC leaves the chip in
an unknown state and recommends powering the whole device from one source. A target-powered VCCIO
connection is therefore not an automatic fix.

## Triggering V1 evidence

The V1 result does not prove the V2 circuit will fail, because V1 connected RTS directly to BOOT and
did not have DTR or Q4. It does prove that leaving adapter VCC disconnected is insufficient evidence
of no back-powering.

On 2026-08-29, with PCB-01B's 18 V input off and only the SH-U09C2 connected:

- TP5/3V3 measured 1.3 V while adapter VCC was visibly disconnected.
- Disconnecting RTS reduced TP5 to 0.37 V. After the buttons discharged the residual voltage, TP5
  stayed at 0 V for 30 seconds.
- Isolated adapter RTS measured 3.3 V released and the host could assert it low.
- With RTS asserted low, TP5 stayed at 0 V. At 18.0 V board input, current settled at 0.022 A.
- Two ROM-entry sequences produced no response: cold power with RTS asserted, and RTS asserted plus
  manual RESET.
- `espflash board-info` failed twice with `Failed to connect to the device`.
- `esptool` reported `Failed to connect to ESP32-C6: No serial data received`.
- A raw 115200-baud capture received no bytes during another reset with BOOT held low.
- BOOT measured 0 V during the failed sequence. EN was not measured because the owner ended probing.

This cannot distinguish a PCB-01B ESP/reset/UART failure from a harness signal-path fault. Treat the
board as unavailable, but do not infer a specific V1 root cause.

## Required independent review

1. Re-derive Q4's truth table from the current Espressif ESP32-C6 DevKitC schematic and the onsemi
   transistor pinout. Check the KiCad symbol, footprint, netlist, and placed pad mapping, not only
   the Markdown connectivity table.
2. Quantify or bench-measure every powered-adapter to unpowered-target path for the exact
   UMFT231XA-01 in its default configuration. Test all four RTS#/DTR# states, idle TXD, USB plug and
   unplug, port open and close, host sleep, interrupted flash, and repeated runtime reopen.
3. Decide whether the current 470 ohm plus Q4 network meets a literal no-back-power criterion. State
   a voltage and current acceptance limit before testing.
4. If isolation is needed, prefer target-side logic or switching with a manufacturer-specified
   partial-power-down/Ioff behavior on every connected signal. One candidate to evaluate is a
   target-powered quad buffer such as `SN74LV125A`, which TI explicitly specifies for Ioff partial
   power-down operation and 5.5 V tolerant inputs. Verify output-enable behavior during the 3V3
   ramp, signal direction per channel, control-line truth table, package/pinout, exact MPN/LCSC
   availability, and whether pull-ups are needed. Do not substitute `SN74LVC125A` without checking
   the exact current datasheet because similarly named variants differ in Ioff claims.
5. Preserve standard `esptool` semantics: RTS controls EN, DTR controls GPIO9/BOOT, both are active
   low, and both asserted together must release EN and BOOT. Preserve manual RESET/BOOT fallback.
6. Physically qualify the exact adapter, cable, buffer or transistor network, and ESP32-C6-WROOM-1
   development target before PCB fabrication. Save measured powered and unpowered rail voltages,
   successful ROM identity, erase, flash, watchdog reset, runtime `stillair` traffic, and cleanup.
7. If the design changes, update `docs/pcb-01-v2.md`, the exact component schedule and connectivity,
   KiCad through Konnect, placement, capture parity counts, probe map, firmware port discovery and
   control-line handling, bring-up gates, fabrication outputs, `docs/STATE.md`, and this handoff.

## Primary references

- [FTDI UMFT231XA product page](https://ftdichip.com/products/umft231xa-01/)
- [FTDI UMFT231XA datasheet](https://ftdichip.com/wp-content/uploads/2020/07/DS_UMFT231XA.pdf)
- [FTDI FT231X datasheet](https://www.ftdichip.com/wp-content/uploads/2025/06/DS_FT231X.pdf)
- [FTDI input/output pin states](https://ftdichip.com/wp-content/uploads/2020/07/AN_184-FTDI-Device-Input-Output-Pin-States.pdf)
- [FTDI mixed-power guidance](https://www.ftdichip.com/Support/Knowledgebase/canftdidevicesbepoweredin.htm)
- [Espressif ESP32-C6 boot-mode selection](https://docs.espressif.com/projects/esptool/en/latest/esp32c6/advanced-topics/boot-mode-selection.html)
- [Espressif ESP32-C6 DevKitC schematic](https://docs.espressif.com/projects/esp-dev-kits/en/latest/_static/esp32-c6-devkitc-1/schematics/esp32-c6-devkitc-1-schematics.pdf)
- [onsemi BC847BDW1T1G datasheet](https://www.onsemi.com/download/data-sheet/pdf/bc846bdw1t1-d.pdf)
- [TI SN74LV125A product page](https://www.ti.com/product/SN74LV125A)
