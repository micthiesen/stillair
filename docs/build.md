# Build release

Order, assemble, prove, install. A gated sequence built around an instrumented custom V1
board. No TI evaluation module is required. Final loaded work happens on the installed plate,
beginning at the lowest useful speed with continuous observation and a reachable cutoff.

## Build sequence (five gated phases)

1. **Build and bring up PCB V1** — buy the GL100 and order the roomy 78 × 58 mm V1 board.
   Verify rails and DRVOFF first, then measure the motor and tune sensorless startup through
   I²C using the board's test points.
2. **Freeze CAD and PCB V2** — use measured V1 results to freeze the blade, hub,
   capture spindle, carrier, plate, housing, protection, thermal design, and golden MCF
   register set. Keep the PCB outline unchanged.
3. **Fabricate and inspect** — make the metal and printed parts, inspect every critical
   interface, destructively test a blade root-joint sample, proof the three installed blade
   roots, and prepare four matched blades.
4. **Assemble and inspect unpowered** — install the final mechanics, verify retention and hand
   clearance, and check balance and runout before applying motor power.
5. **Ceiling integration and commissioning** — Michael has explicitly resumed project
   assistance for mounting the remaining assembly and routing 24 V, motor, Hall, and long-USB
   service connections on the installed plate. Loaded MPET, tuning, representative starts,
   normal-range speed and shutdown checks, and thermal verification then run in that final
   support/load/acoustic environment.

### Replacement PCB-01 service path (2026-08-28)

The replacement board passed hand-populated C34/U8 continuity and initial 18 V rail checks, but
its native USB never enumerated after known cables, forced ROM boot, host restart, and J6 pin
reflow. UART0 on J7 is the recovery path through a DSD TECH SH-U09C2 FT232RNL USB-UART adapter.
Solder one light lead to each J7 pin 2--6 and leave J7.1/board-3V3 isolated. A/B/C connect TX,
RX, and AGND to adapter RXD, TXD, and GND. D/BOOT branches to adapter RTS and to a normally-open
momentary switch whose other terminal returns to C/AGND. E/EN uses the same switch-to-C pattern
for manual reset. Disconnect D from RTS before using the BOOT switch; never ground an actively
driven RTS output. Check every intended connection and adjacent-pad isolation before power.

The application now defaults to the J7 UART0 console, while a `usb-console` build feature retains
the original native-USB transport. The synchronized runner can assert active-low RTS, cold-cycle
the Kasa supply, release BOOT, flash with `--before no-reset`, and watchdog-reset into the UART
application. This sequence is host-tested but not yet physically qualified; see
[controls.md](controls.md#commissioning-interface-and-build-policy).
The printable direct end-to-end pad map is
[`pcb-01-j7-usb-uart.pdf`](../output/pdf/pcb-01-j7-usb-uart.pdf).

## Mount build-first plan (2026-07 review; supports incremental in-person building)

- **Mock first, cheap**: an MDF or 3D-printed Ø210 disk + three printed/threaded-rod
  Ø16 × 62 standoffs + a blank Ø180 disk, to feel the (now much shallower) drop in the room
  before any stainless is cut.
- **Received + owner-accepted 2026-08-14**: MP-100, ST-100 (qty 4),
  SP-100, MC-100, RH-100, PCB-01 (2 assembled + 3 bare), and PCB-02 (5 bare).
- **Ordered finished**: MP-100 (JLCCNC 2026-07-27), ST-100 (JLCCNC 2026-07-28, qty 4,
  clear anodized), KD-100 (became a purchased DIN 440 washer — Accu 2026-07-28). BP-100
  blade manufacturing and blade-root qualification passed 2026-08-14; assembled rotor
  balance/runout is checked unpowered during final ceiling integration.
- **SP-100 measure-first gates closed before fabrication**: measured KD-100 thickness set
  the cotter-hole Z; measured GL100 axial length set the capture stack. The finished part
  arrived with the rest of the JLCCNC batch on 2026-08-14. See parts.md > SP-100.
- **MP-100 is released** (2026-07-27): both paper decisions landed — ENC tab clocking at
  45/105/165/225/285/345° and a 15° rim cable entry replacing the deleted mid-plate slot.
  See parts.md "ENC-100 tab clocking" and "Cable entry". Never was motor-gated.
- **MC-100/RH-100 partial strategy**: their motor-independent features (ODs, standoff
  holes, center clearances, tether holes, blade-root stations, tach pockets) can be machined
  early, leaving the motor-pattern operations (Ø60/Ø50 PCD clocking, wire window, pilot OD)
  as final ops after the GL100 is measured.

## Procurement gates

- **Buy first**: CubeMars GL100 KV10, GST60A24 supply, and the fully populated 78 × 58 mm
  PCB V1. The TI evaluation board is intentionally skipped.
- **After V1 pass**: controller V2. Same outline and holes; remove only development features
  proven unnecessary after startup, thermal, and essential safety testing.
- **After CAD review**: custom mechanics. Fabricate plate, carrier, hub, capture hardware,
  blades, and housing only after motor faces, fastener depths, and the slab
  interface are resolved.

Purchase state is tracked in [../bom/bom.csv](../bom/bom.csv).

## Commissioning

Pass or fail, not "seems fine." The full matrix with method, acceptance limit, and sign-off
fields is [../testing/test-matrix.csv](../testing/test-matrix.csv); these limits are the
minimum release basis and can be tightened after measured data exists. Highlights:

| Test | Acceptance limit |
|---|---|
| Representative starts (20/direction at the intended minimum at 24.0 V; 5/direction at 23.3 and 24.7 V) | No retry, reverse kick, stall, click, or hunting |
| Speed range (steady at 30/40/55/70/120/170 RPM) | Stable speed and acceptable current waveform; each low speed released only if all starts pass |
| Hard limit (max command + command-path fault) | Motor controller never exceeds 180 RPM |
| Rotor proof (secured external drive, 216 RPM × 2 min/direction, continuously observed) | No abnormal motion, sound, damage, loosening, deformation, balance shift, or contact |
| Bus voltage (≥100 MHz probe at MCF pins during coast/cutoff/stall/reversal) | Peak ≤35 V, no 28 V OVP trip; otherwise redesign suppression |
| Analog overspeed | Reset near 180 RPM; trip near 200 RPM, never above 220 RPM across voltage and temperature |
| Essential fault behavior | Hardware fault or watchdog disables the bridge; power returns off; reversal only after stop |
