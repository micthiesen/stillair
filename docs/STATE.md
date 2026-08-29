# State

Fast-moving work state and chosen next step. Durable findings live in the linked design,
commissioning, BOM, and test documents.

Last updated: **2026-08-28** (replacement PCB-01 qualified through initial rails; J7/UART recovery selected.)

## Now

- **The installed fan retains its provisional 50--170 RPM loaded release.** The complete ceiling
  assembly, persistent golden MCF image, Apple Home control, cold-power recovery, nine 50 RPM
  starts, ten-minute low-speed hold, and overnight 50 RPM owner run passed. Higher settings still
  have a repeatable electrical tone and occasional chirp, and startup remains subjectively rough.
  Evidence and remaining release work are in
  [loaded-tuning-2026-08-21.md](../testing/loaded-tuning-2026-08-21.md) and
  [test-matrix.csv](../testing/test-matrix.csv).
- **The final loaded-tuning contract is saved but not active.** When Michael explicitly asks to
  start final tuning, use the objective verbatim from
  [final-loaded-tuning-goal.md](../testing/final-loaded-tuning-goal.md), adapting only execution
  details to the verified hardware and tools then available. The exposed assembly is tuned first;
  the already-decided motor and upper-housing damping follow as passive treatment, with the fixed
  close microphone retained and no formal bed-position recording.
- **The replacement PCB-01 passed hand-population continuity and initial power checks but native
  USB is unavailable.** C34/U8 checks passed; at 18 V with a 0.25 A limit, input current settled
  near 0.023 A, TP5 was 3.328 V, TP25 was 2.480 V, and ESP_EN was about 3.3 V. Known cables,
  connector orientations, forced ROM boot, host restart, and J6 reflow produced no macOS
  enumeration. R20/R21 remain about 21 Ohm with no data-line short. Full results and the open AVDD,
  DVDD, UART-console, and MCF-communication checks are in `PCB-01B` of
  [test-matrix.csv](../testing/test-matrix.csv).
- **J7/UART0 is the selected replacement-board service path.** A DSD TECH SH-U09C2 FT232RNL
  adapter is ordered. Fast domestic TC2030 cables were unavailable, so the selected fallback is a
  light prewired JST-SH pigtail soldered once to J7 pins 2--6, with J7.1/board-3V3 isolated and the
  harness checked and strain-relieved before power. J7 can already reach the ROM UART downloader,
  but the application runtime protocol is currently USB Serial/JTAG only and must be bound to
  UART0 before the tuning CLI can use it. See [build.md](build.md#replacement-pcb-01-service-path-2026-08-28)
  and [controls.md](controls.md#commissioning-interface-and-build-policy).
- **The synchronized tuning harness is prepared but not yet dynamically qualified on this board.**
  Kasa, Ubiquiti camera, fixed 24-bit/96 kHz microphone, VDS1022I capture, and the retained scope
  hookup passed static preflight. Installed lead colors are J8.9 SOX black, TP20 FG yellow, and
  TP26 AGND blue; OWON remains CH1 SOX and CH2 FG without rewiring. The fail-closed baseline and
  candidate runners are ready, but SOX/FG/camera timing and live MCF readback wait for controller
  communication.
- **The failed PCB-01 remains quarantined, and JLCPCB is reviewing the replacement board's U2.**
  The failed board's MCF internal rails measured about 5 Ohm and 3 Ohm to AGND and must not be
  powered. The replacement-board quality complaint for SMT job `SMT026073063521-12177845A` was
  submitted on 2026-08-28 with photos/video and requests a replacement PCBA; status was
  `Submitted` / `Processing` with no case number.

## Next

Add a UART0 transport for the existing application line protocol and output writer while preserving
the current USB path, then run the host/app verification gates. This is startable before the ordered
adapter arrives and is the software prerequisite for using J7 as the installed commissioning link.

When the adapter and pigtail are in hand, map the pigtail by continuity rather than color, attach
only J7 pins 2--6 with power removed, verify every intended connection and adjacent-pad isolation,
add strain relief, and test ROM flashing plus the runtime CLI. Then complete replacement-board AVDD,
DVDD, MCF communication, active provisional firmware, and brief unloaded-start qualification beside
the fan. Do not reinstall the board or start final tuning until these checks pass.

## Candidates Not Chosen

- **Wait for JLCPCB before continuing:** deferred. A replacement may be useful, but the UART path is
  independently recoverable and advances the critical path now.
- **Return the board overhead and begin loaded tuning:** blocked. Runtime communication, remaining
  rails, MCF access, and unloaded operation are not yet proved on the replacement controller.
- **Buy an imported TC2030 cable or fabricate a generic-pogo jig:** rejected for this recovery.
  Available TC2030 listings miss the required schedule, while generic pogo products do not match
  J7's 2x3 1.27 mm geometry and add more fixture work than the one-time pigtail.
- **Install damping or housing now:** deferred until the exposed controller tune is frozen, so
  passive treatment does not obscure source-level diagnosis.

## Learned Recently

- Replacement-board recovery interface, current USB-only runtime limitation, and pigtail rules:
  [build.md](build.md#replacement-pcb-01-service-path-2026-08-28) and
  [controls.md](controls.md#commissioning-interface-and-build-policy).
- Replacement-board continuity, initial rail evidence, and remaining checks: `PCB-01B` in
  [test-matrix.csv](../testing/test-matrix.csv).
- Exact future goal, autonomy boundaries, evidence standard, and completion condition:
  [final-loaded-tuning-goal.md](../testing/final-loaded-tuning-goal.md).
- Board-relative probing and fixed tuning lead map: [probing.md](probing.md) and
  `pcb/pcb-01/probe-map.json`.
- Loaded commissioning baseline and candidate sequence:
  [loaded-tuning-2026-08-21.md](../testing/loaded-tuning-2026-08-21.md).
