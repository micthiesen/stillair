# State

Fast-moving work state and chosen next step. This records the work, not machine state or
uncommitted changes. Durable findings live in the linked docs.

Last updated: **2026-07-27** (firmware program A–D complete and proven on silicon; Matter
paired with Apple Home; Next moved to the V1 schematic, which now gates everything else).

## Now

- **The firmware is done and runs on real hardware.** `firmware/` is three crates:
  `stillair-core` (`no_std`, zero esp-\* deps, sans-I/O, **171 host tests**), `firmware/cli`
  (the tuning harness, driving a board or an in-process simulator), and `firmware/app` (the
  C6 binary). The supervisor state machine, the MCF8316D I²C wire format, the tuning console,
  the boot-time configuration gate, and the Matter control plane are all implemented, reviewed,
  and flashed. CI runs fmt + clippy + tests on core, fmt + clippy + release build on app.
- **Matter works end to end against Apple Home.** It renders a continuous 0–100% speed slider,
  on/off, and a reverse button — `AirflowDirection` is surfaced, so the second On/Off endpoint
  held as a fallback is dropped. A slider at 61% arrived at the supervisor as a 116.8 RPM
  target, matching the documented linear map onto [35, 170] exactly, so the whole
  Matter → mapping → supervisor path is verified on silicon (CTL-12).
- **The fan pairs but will not spin, correctly.** With no MCF8316D on the bus the stored
  configuration check fails and `SafeBoot` refuses to reach `IdleOff`; commands from Home are
  accepted and held as intent. That is the safety gate working, and it is also why everything
  left in firmware is gated on real hardware.
- **MP-100 is ordered — the first custom part committed to metal.** JLCCNC, SUS304, qty 1,
  ~$130; rev A STEP + PDF in [`cad/`](../cad/). **On arrival: check flatness with a straightedge
  before drilling the ceiling** — JLC holds no form tolerances.
- **Mount work can start** ([build.md](build.md) > "Mount build-first plan"): mockup first, then
  ST-100/SP-100/KD-100/BL-100/LS-100 are fully spec'd and motor-independent. GL100 + parts en
  route; CubeMars bearing email sent 2026-07-27 (Gate 01 awaiting reply). Anchors are Simpson
  Titen HD with the full ESR-2713 basis in [install.md](install.md).

## Next

**Capture the V1 controller schematic in KiCad** (`pcb/`). Every remaining firmware unknown —
register values, the golden image, sensorless startup tuning, the analog trip calibration — is
gated on having an MCF8316D to talk to, so the board is now the single thing standing between
here and a fan that turns. Follow [electrical.md](electrical.md) SCH-01–SCH-07 **as amended by
the review** (delayed `/PRE` RC + Schmitt, corrected reverse-polarity FET orientation, LM2907
fixes, GPIO7/15 routes, GPIO8/9 pull-ups, 22 µF module bulk, NTC/VBUS circuits); order config
and footprint sourcing in `pcb/README.md`. Not hardware-gated.

Then, once a real MCF8316D exists: **capture the golden image.** The gate is built and holds;
`stillair --port … config capture` prints the table, and until it is filled in every telemetry
frame and CSV row honestly reports `config: unverified`.

## Candidates Not Chosen

- **Mount mockup + first metal** (MDF/printed plate-standoff-carrier mockup; order plate/rod/
  17-4PH stock; fab ST-100/SP-100/KD-100). Owner-driven and fully parallel with the PCB — worth
  running alongside rather than instead of it.
- **Blade adapter filament qualification** — startable as soon as PPA-CF is ordered; the longest
  non-motor-gated path, so it wants starting early even though it is not the critical path.
- **Motor release checks** when the GL100 arrives (pilot-register rotating-surface confirmation,
  axial-length tolerance measurement). Hardware-gated on delivery.
- **Non-concurrent Matter commissioning** (`run` instead of `run_coex`) — a lever held in
  reserve for the coexistence scan flakiness, not a task. Costs a larger `BUMP_SIZE` and
  reportedly breaks Alexa; unused until something needs it.

## Learned Recently

- **Stored-configuration verification** — the golden-image design, the four-valued verdict, and
  why the image is whole registers rather than named bit fields →
  [controls.md](controls.md) > "Stored-configuration verification"; rows CTL-08/09/10.
- **Matter implementation and build** — the cluster mapping, why nothing is cached in the
  handler, the measured memory numbers, the `[patch.crates-io]` cost, `esp-alloc`'s mandatory
  `compat` feature, and why `mbedtls` cannot build here →
  [controls.md](controls.md) > "Matter implementation notes" / "Building the Matter firmware",
  and [CLAUDE.md](../CLAUDE.md) > "Firmware conventions".
- **Apple Home commissions onto whatever SSID the phone is on**, with no picker, and reports
  every failure as "Pairing Failed" — a 5 GHz SSID fails as `NoAccessPointFound` and only the
  device's serial log says so → [controls.md](controls.md) > "Home integration"; the capture
  procedure is in [CLAUDE.md](../CLAUDE.md) > "Driving the fan".
- **Running on real silicon finds what a simulator cannot.** The first flash exposed a log flood
  that evicted telemetry frames from the bounded output queue during exactly the fault they were
  meant to record; status logging is now transition-only (comment in `app/src/main.rs`). The
  bare dev board also cannot leave `SafeBoot` — GPIO22 PGOOD floats low and floating-means-bad
  is the correct fail-safe reading; jumpering is in [CLAUDE.md](../CLAUDE.md).
- **Review keeps finding one shape of defect: a claim that cannot come back from reality.** A
  Matter-private attribute cache no fault could clear, a `config dump` that printed one register
  of twenty-four and exited zero, a write budgeted 500 ms that takes 750 ms. All fixed; the
  reasoning is in code comments at each site.
- **The full-design review's fixes are in** → [electrical.md](electrical.md) (U6 power-up preset
  race, reversed FET, LM2907 timing cap, GPIO15/7 routes, two-tier trip claim),
  [controls.md](controls.md), [parts.md](parts.md), [build.md](build.md). Its lesson:
  **the dossier's failure mode is wiring/config detail, not architecture** — worth carrying into
  the schematic capture that is now next. Review fixes need the same adversarial verification as
  the original design; two defective fixes were caught before capture.
- **A 1 pulse/rev tach cannot guarantee tight overspeed overshoot** against fast ramps; the
  supply-power bound is the real backstop → [electrical.md](electrical.md), 270 RPM basis.
