# Build release

Order, assemble, prove, install. A gated sequence built around an instrumented custom V1
board. No TI evaluation module is required, and the first full-rotor spin never happens over
the bed.

## Build sequence (five gated phases)

1. **Build and bring up PCB V1** — buy the GL100 and order the roomy 78 × 58 mm V1 board.
   Verify rails and DRVOFF first, then measure the motor and tune sensorless startup through
   I²C using the board's test points.
2. **Freeze CAD and PCB V2** — use measured V1 results to freeze the blade, adapter, hub,
   capture spindle, carrier, plate, housing, protection, thermal design, and golden MCF
   register set. Keep the PCB outline unchanged.
3. **Fabricate and inspect** — make the metal and printed parts, inspect every critical
   interface, destructively test an adapter sample, proof the three installed adapters, and
   prepare four matched blades.
4. **Assemble and bench prove** — build on a level fixture, measure runout, balance the
   rotor, proof-speed it behind a barrier, verify central capture, then complete every
   control and fault test.
5. **Verify the slab and install** — resolve the permanent-installation approval path,
   identify and scan the slab, select the anchors, install the independent tether, then
   repeat limited-speed commissioning away from the bed.

## Procurement gates

- **Buy first**: CubeMars GL100 KV10, GST60A24 supply, and the fully populated 78 × 58 mm
  PCB V1. The TI evaluation board is intentionally skipped.
- **After V1 pass**: controller V2. Same outline and holes; remove only development features
  proven unnecessary after startup, acoustics, thermal, RF, and fault testing.
- **After CAD review**: custom mechanics. Fabricate plate, carrier, hub, capture hardware,
  adapters, blades, and housing only after motor faces, fastener depths, and the slab
  interface are resolved.

Purchase state is tracked in [../bom/bom.csv](../bom/bom.csv).

## Commissioning

Pass or fail, not "seems fine." The full matrix with method, acceptance limit, and sign-off
fields is [../testing/test-matrix.csv](../testing/test-matrix.csv); these limits are the
minimum release basis and can be tightened after measured data exists. Highlights:

| Test | Acceptance limit |
|---|---|
| Cold start (100 starts/direction at 30/35/40 RPM, 23.3/24.0/24.7 V) | No retry, reverse kick, stall, click, or objectionable tonal sequence |
| Sleep acoustics (motor-only + complete fan at 30/40/60/80/120/170 RPM, listened from bed) | No identifiable motor, controller, bearing, or structural tone at the released sleep speed |
| Speed range (steady at 30/40/55/70/120/170 RPM) | Stable speed and acceptable current waveform; each low speed released only if all starts pass |
| Hard limit (max command + command-path fault) | Motor controller never exceeds 180 RPM |
| Rotor proof (external drive, 216 RPM × 2 min/direction, behind barrier) | No damage, loosening, deformation, balance shift, or contact |
| Bus voltage (≥100 MHz probe at MCF pins during coast/cutoff/stall/reversal) | Peak ≤35 V, no 28 V OVP trip; otherwise redesign suppression |
| Analog overspeed | Reset near 180 RPM; trip near 200 RPM, never above 220 RPM across voltage and temperature |
| Fault behavior | Bridge disables on local fault; power returns off; network loss preserves last state; reversal only after stop |
