# State

Fast-moving work state and chosen next step. Durable findings live in the linked design,
commissioning, BOM, and test documents.

Last updated: **2026-08-30** (V2 redesigned around native USB-C and reconverged as a whole board.)

## Now

- **PCB-01 V2 is captured, holistically placed, and ready for manual trace routing.** The 88 x 64 mm
  KiCad board has native USB-C at J4, no FTDI/UART service circuit, 166 top-side footprints, the
  exact 78-net/411-endpoint ratsnest, four-layer stackup, 20 zones/rule areas, two local USB-ESD
  ground vias, keepouts, fiducials, silkscreen, 3D models, probe map, assembly split, and guarded
  JLCPCB export. ERC and schematic parity pass. Pre-route DRC has 328 expected unconnected items and
  one expected isolated In2 3V3-plane warning, with no other violation. Four native-USB board-review
  rounds converged with no further improvement. The repeated whole-board review is recorded in
  [pcb-01-v2.md](pcb-01-v2.md). The handoff and routing checklist are in
  [pcb-01-v2/README.md](../pcb/pcb-01-v2/README.md).

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
- **The replacement PCB-01 is unavailable after both native USB and J7 UART failed.** C34/U8 and
  initial 18 V checks passed, and the switched J7 adapter test drew the nominal 0.022 A. USB-only
  J7 testing exposed 1.3 V back-power through the signal harness. RTS polarity worked, but two ROM
  entry sequences, `espflash`, `esptool`, and a raw reset capture produced no UART response. The
  evidence cannot distinguish a board ESP/reset/UART fault from a harness signal fault; Michael
  ended probing and rejected the board. Details are in `PCB-01B` of
  [test-matrix.csv](../testing/test-matrix.csv) and the V2 review handoff linked above.
- **The replacement service harness is fully specified and printed.** J7 pins 2--6 get five
  lettered leads; TX/RX/AGND reach the SH-U09C2 adapter, BOOT branches to a normally-open manual
  switch and removable RTS connection, and EN gets a normally-open reset switch. J7.1 and adapter
  VCC remain isolated. The black-and-white one-page build sheet and manual fallback are in
  [pcb-01-j7-usb-uart.pdf](../output/pdf/pcb-01-j7-usb-uart.pdf); printer job
  `Brother_HL_L2370DW_series-7` completed.
- **V2 firmware and commissioning use native USB only.** ESP32-C6 GPIO12/13 carry D-/D+ through J4;
  GPIO16/17 are unconnected. Flashing uses the ROM USB Serial/JTAG interface, with BOOT plus RESET
  as the deterministic recovery sequence. The host and app firmware gates pass. The final assembled
  board still requires the normal first-article USB enumeration, ROM-download, flash, reboot, and
  runtime CLI checks. See
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

- **Retain FTDI as a V2 backup:** rejected. It creates powered-off back-power and adapter/harness
  uncertainty without improving the ESP32-C6 ROM recovery path. V2 uses native USB-C only.
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
- Closed V2 service-interface decision and retained V1 failure evidence:
  [pcb-01-v2-service-interface-review.md](pcb-01-v2-service-interface-review.md).
- Switched J7 construction, monochrome wire patterns, automated RTS connection, and manual
  fallback: [pcb-01-j7-usb-uart.pdf](../output/pdf/pcb-01-j7-usb-uart.pdf) and
  [build.md](build.md#replacement-pcb-01-service-path-2026-08-28).
- Native-USB build policy, ROM recovery sequence, and physical qualification gate:
  [controls.md](controls.md#commissioning-interface-and-build-policy) and
  [firmware/scripts/README.md](../firmware/scripts/README.md).
- Replacement-board continuity, initial rail evidence, and remaining checks: `PCB-01B` in
  [test-matrix.csv](../testing/test-matrix.csv).
- Exact future goal, autonomy boundaries, evidence standard, and completion condition:
  [final-loaded-tuning-goal.md](../testing/final-loaded-tuning-goal.md).
- Board-relative probing and fixed tuning lead map: [probing.md](probing.md) and
  `pcb/pcb-01/probe-map.json`.
