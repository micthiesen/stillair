# State

Fast-moving work state and chosen next step. Durable findings live in the linked design,
commissioning, BOM, and test documents.

Last updated: **2026-08-29** (PCB-01 V2 KiCad capture and placement completed and board-review converged.)

## Now

- **PCB-01 V2 is captured, placed, and ready for manual trace routing.** The 88 x 64 mm KiCad board
  contains the exact 78-net/395-endpoint ratsnest, 162 top-side footprints, four-layer stackup,
  19 zones and rule areas, final placement, keepouts, fiducials, silkscreen, 3D models, probe map,
  assembly split, and guarded JLCPCB export. ERC is clean; the pre-route DRC has only 315 expected
  unconnected items and two expected isolated In2 3V3-fill warnings. Six sequential implemented-board
  review rounds converged with no useful electrical, DFM, visual, mechanical, or routing feedback.
  The board handoff and routing checklist are in [pcb-01-v2/README.md](../pcb/pcb-01-v2/README.md).

- **The installed fan retains its provisional 50--170 RPM loaded release.** The complete ceiling
  assembly, persistent golden MCF image, Apple Home control, cold-power recovery, nine 50 RPM
  starts, ten-minute low-speed hold, and overnight 50 RPM owner run passed. Higher settings still
  have a repeatable electrical tone and occasional chirp, and startup remains subjectively rough.
  Evidence and remaining release work are in
  [loaded-tuning-2026-08-21.md](../testing/loaded-tuning-2026-08-21.md) and
  [test-matrix.csv](../testing/test-matrix.csv).
- **The final loaded-tuning contract is saved but not active.** When Michael explicitly asks to
  start final tuning, use the objective verbatim from
  [final-loaded-tuning-goal.md](../testing/final-loaded-tuning-goal.md), adapting execution details
  only to verified hardware and tools. Tune the exposed assembly first; the decided motor and
  upper-housing damping follow as passive treatment with the fixed close microphone retained.
- **The replacement PCB-01 passed hand-population continuity and initial 18 V checks, but native
  USB remains unavailable.** C34/U8 checks passed; input settled near 0.023 A, TP5 was 3.328 V,
  TP25 was 2.480 V, and ESP_EN was about 3.3 V. Known cables, forced ROM boot, host restart, and J6
  reflow produced no enumeration. AVDD, DVDD, UART operation, MCF communication, and an unloaded
  start remain open in `PCB-01B` of [test-matrix.csv](../testing/test-matrix.csv).
- **The replacement service harness is fully specified and printed.** J7 pins 2--6 get five
  lettered leads; TX/RX/AGND reach the SH-U09C2 adapter, BOOT branches to a normally-open manual
  switch and removable RTS connection, and EN gets a normally-open reset switch. J7.1 and adapter
  VCC remain isolated. The black-and-white one-page build sheet and manual fallback are in
  [pcb-01-j7-usb-uart.pdf](../output/pdf/pcb-01-j7-usb-uart.pdf); printer job
  `Brother_HL_L2370DW_series-7` completed.
- **The software is ready for physical J7 qualification.** The application now defaults to the
  UART0 line protocol on GPIO16/17; an exclusive `usb-console` feature retains native USB. The
  synchronized runner auto-detects the exact FTDI, drives active-low RTS across a verified Kasa
  cold start, flashes without a reset-line handoff, watchdog-resets into the application, and
  releases RTS plus powers off on helper failure. The host firmware gates, both app builds, 50
  script tests, and loaded-profile dry runs pass. Hardware polarity, back-powering, ROM sync,
  flash/reset, runtime CLI, and cleanup behavior are deliberately unverified. See
  [controls.md](controls.md#commissioning-interface-and-build-policy).
- **The synchronized tuning observers remain prepared.** Kasa, Ubiquiti camera, fixed 24-bit/96
  kHz microphone, and VDS1022I static preflight passed. Installed scope leads remain J8.9 SOX
  black, TP20 FG yellow, and TP26 AGND blue, with OWON fixed as CH1 SOX / CH2 FG. Dynamic
  qualification waits for replacement-controller communication.

## Next

Route PCB-01 V2 in the order and widths in the interactive checklist linked from
[pcb-01-v2/README.md](../pcb/pcb-01-v2/README.md). Preserve the encoded keepouts and named local
escape areas, refill all zones, and finish with zero unconnected items and zero DRC violations.
Then run `python3 pcb/tools/jlc_fab.py pcb-01-v2`, inspect the generated Gerbers, drill map, BOM,
CPL, POFV notes, and assembly locator, and place the JLCPCB order using the tracked fabrication
notes. The export command now refuses to create orderable Gerbers until the final DRC gate passes.

## Candidates Not Chosen

- **Qualify the switched J7 harness first:** still useful for the installed V1 replacement board,
  but it does not advance the now-ready V2 manufacturing package.
- **Adopt manual-only BOOT now:** held as the immediate fallback. The removable D-to-RTS connection
  costs no board rework and deserves one controlled qualification first.
- **Return the board overhead and start loaded tuning:** blocked on UART communication, remaining
  rails, MCF access, and brief unloaded operation of the replacement controller.
- **Install damping or housing now:** deferred until the exposed controller tune is frozen, so
  passive treatment does not obscure source-level diagnosis.

## Learned Recently

- Ready-to-route PCB-01 V2 KiCad project, routing vocabulary, guarded JLCPCB exporter, probe map,
  assembly package, and implemented-board review record:
  [pcb-01-v2/README.md](../pcb/pcb-01-v2/README.md) and [pcb-01-v2.md](pcb-01-v2.md).
- Complete PCB-01 V2 schematic/layout handoff, exact BOM and ratsnest, evidence-based simplifications,
  digital chamber-temperature telemetry, implementation gates, and review record:
  [pcb-01-v2.md](pcb-01-v2.md).
- Switched J7 construction, monochrome wire patterns, automated RTS connection, and manual
  fallback: [pcb-01-j7-usb-uart.pdf](../output/pdf/pcb-01-j7-usb-uart.pdf) and
  [build.md](build.md#replacement-pcb-01-service-path-2026-08-28).
- UART0/USB build policy, fail-closed RTS/Kasa sequence, and physical qualification gate:
  [controls.md](controls.md#commissioning-interface-and-build-policy) and
  [firmware/scripts/README.md](../firmware/scripts/README.md).
- Replacement-board continuity, initial rail evidence, and remaining checks: `PCB-01B` in
  [test-matrix.csv](../testing/test-matrix.csv).
- Exact future goal, autonomy boundaries, evidence standard, and completion condition:
  [final-loaded-tuning-goal.md](../testing/final-loaded-tuning-goal.md).
- Board-relative probing and fixed tuning lead map: [probing.md](probing.md) and
  `pcb/pcb-01/probe-map.json`.
