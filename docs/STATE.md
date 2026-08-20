# State

Fast-moving work state and chosen next step. This records the work, not machine state or
uncommitted changes. Durable findings live in the linked docs.

Last updated: **2026-08-19** (first no-motor power and firmware bring-up.)

## Now

- **All fabricated parts are received**: both JLCPCB runs (PCB-01
  **W2026073105230212**, 2 assembled + 3 bare; PCB-02 **W2026073108244536**, 5 bare)
  and all JLCCNC parts, including MP-100, four ST-100s, and batch
  **W2026080301372216** (SP-100 / MC-100 / RH-100). Owner accepted the delivered parts
  as received on 2026-08-14; no separate incoming-inspection pass is planned. SP-100 is
  **SUS304**; RH-100 used the **±0.05 tier** for the measured-bore pilot fit.
- **Arrived 2026-08-01**: GL100 motor, the full Accu fastener set, Titen HD anchors,
  DigiKey 374750597 (salesorder 100668200). Measured: axial 34.2–34.3 (nominal stands,
  stack derived), KD-100 t = 3.38 → SP-100 cross-hole Z136.6, bore Ø29.99–30.00 →
  pilot Ø29.85. All caliper-clearable fabrication gates closed (parts.md).
- **Design deltas this weekend** (all in parts.md): MR-100 caps deleted — epoxy is the
  retention; Hall sensor line moved to the standoff bisector ("150°", relational def
  controls); RH-100 blade stations owner-customized (released STEP is interface truth;
  blade root is owner-managed); BR-100 will be owner hand-fabbed, not designed in repo.
- **Consolidated DigiKey reorder received 2026-08-14**: **100888768**, 27 warehouse lines,
  CAD $200.98 after tax. It replaces cancelled orders **100616913** and **100723632**.
  Final quantities and four same-footprint substitutions are in `bom/README.md` and
  `bom.csv`; owner accepted the received order as complete.
- **BP-100 blade manufacturing and blade-root qualification are complete** (owner,
  2026-08-14). MEC-01/02/02B passed. Assembled rotor balance/runout remains open under
  MEC-05.
- **Build-critical procurement is closed.** Two loose `DMP6023LE-13` spares and optional
  SparkFun `15362` scope headers are not active work. M2 hardware and crimpers remain owner
  stock; BR-100 remains owner-fabricated and untracked. Do not reopen procurement,
  incoming inspection, or CubeMars correspondence unless Michael explicitly asks.
- **MP-100 ceiling installation is complete** (owner-reported 2026-08-17), with all three
  ST-100 standoffs and SP-100 spindle installed. `INS-01` is accepted as passed against the
  documented stack. The tether and central catcher tests are also owner-reported passes
  (`INS-02`, `MEC-04`). Michael owns all remaining installation work; do not plan, suggest,
  audit, or prompt for ceiling installation, tether, or catcher work.
- **PCB-01 and PCB-02 hand-population is complete** (owner-reported 2026-08-19). PCB-01 has
  C1, C2, C34, J1, J2, U8, and the F1 link fitted; the C36-C40 timing-calibration bank and
  C6 spare bulk-cap site remain intentionally DNP. PCB-02 has U1, C1, and J1 fitted. Both
  boards passed the practical unpowered continuity and no-hard-short checks in binder sheets
  1A and 1B. The first power harness is complete and polarity-checked. The motor-phase
  harness convention is J2 pin 3/U red, pin 2/V green, pin 1/W yellow; at the motor end,
  viewed with the motor centre above its connector, motor pins 1-2-3 are red-green-yellow
  from left to right. Preserve that order and correct final rotation sense in software if
  needed. The completed motor harness has continuity through all phase pairs and no phase
  continuity to the motor housing; its PCB-01 end remains disconnected pending release of
  powered motor work.
- **PCB-01 first no-motor power passed at 18.0 V** (2026-08-19): steady 0.043 A / 0.78 W
  with firmware, Wi-Fi, and BLE running; no sag or abnormal heating. Measured from TP4 AGND:
  TP8 DVDD 1.547 V, TP7 AVDD 3.281 V, TP18 SDA 3.269 V, TP19 SCL 3.159 V, and TP12 DRVOFF
  3.104 V. ESP32-C6 identification and flashing passed over J6. A wake-assisted probe then
  identified the MCF8316D at 0x01 and read its configuration successfully, proving the bus and
  soldering. Repeated 100 kHz packets later wedged I2C because they omitted TI's required
  100 us inter-byte spacing. Hardware-controller workarounds at 5 kHz and 2.5 kHz still
  produced intermittent NACKs in real-board soaks. Firmware now uses a dedicated GPIO0/1
  software bus with normal-speed bits, an explicit 110 us SCL-low hold after each byte, and
  bounded support for the MCF's clock stretching. A 30-second soak through concurrent
  Wi-Fi/BLE/Matter startup plus a separate 60-second sustained poll stayed in `idle_off`;
  both fault registers read zero and the full configuration check completed (`unverified`
  is expected until motor tuning creates the golden image). The numbered board-smoke script
  subsequently passed unchanged: `idle_off`, zero command/duty, clean MCF fault registers,
  readable VM telemetry, and a successful configuration read.
- **The Hall board and harness passed end-to-end** (2026-08-19). Final physical colors are
  PCB-01 J3 left-to-right red/blue/green when viewed component-side with C1/C2 upper-left;
  PCB-02 top-to-bottom green/blue/red when viewed component-side with J1 at the top. This is
  electrically 1-to-1, 2-to-2, 3-to-3; the differing visual order comes from the mirrored
  board frames. HALL_TACH measured 3.251 V released and 0.04 V active, switching at about
  10 mm with the intended rotor magnet. Live firmware telemetry registered every manual
  approach/release cycle.
- **The no-motor permission command path passed** (2026-08-19). With J2 physically
  disconnected, a 35 RPM command drove TP12 DRVOFF from 3.1 V to 0 V as U5 armed. The MCF
  immediately reported the expected open-phase `StartFailed`; firmware revoked permission
  and TP12 returned to 3.1 V. This proves arm plus firmware fault revocation, but is not a
  substitute for PCB-03's separate forced independent-source checks.
- **The first connected-motor command exposed the missing configuration gate** (2026-08-19).
  The restrained unloaded motor moved only a few degrees and stopped; telemetry decoded
  controller status `0x81000000` as `MPET_BEMF_FAULT`. Factory-zero R/L/Ke and speed PI
  fields make any nonzero target enter implicit MPET, so this was not a normal startup and
  showed no short or sustained drive. Firmware now blocks all start-capable commands while
  `unverified`. `config stage` loads a reviewed 0.5 A GL100 first-spin image into volatile
  shadow, verifies it, and reports `provisional` without committing EEPROM. The next hardware
  step is to flash this build, stage once at 19.4 V (above the staged 18 V undervoltage
  threshold), and retry the observed 35 RPM smoke.
- **The first staged retry exposed a start-timeout mismatch** (2026-08-19). The MCF reported
  no gate-driver or controller fault and made only its alignment movement before the firmware
  stopped it at 15 s. At 1.5 RPM/s the command had not yet reached the 35 RPM released
  minimum, which takes about 23 s. `START_TIMEOUT_MS` is now 45 s and compile-time-checked to
  exceed the minimum-speed ramp time; the next step is the same restrained 35 RPM retry.
- **The corrected retry isolated the next blocker to MCF PWM capture** (2026-08-19). During
  a 25 s diagnostic, ESP telemetry ramped to the correct 19.4% duty and J8.6 measured a
  matching 0.63 V average at the MCF SPEED pin, but MCF `ALGO_STATUS.DUTY_CMD`, applied
  voltage, and bus current all stayed zero. PIN_CONFIG, PERI_CONFIG1, and ALGO_DEBUG1 read
  back correctly. The next diagnostic moves the carrier from the 200 Hz low band to 1 kHz in
  the normal 325 Hz–100 kHz band without changing requested speed or motor PWM frequency.
- **The 1 kHz retry produced the same result**, closing the PWM-input branch (2026-08-19).
  J8.6 again followed the requested ramp, while the MCF reported zero decoded duty, idle
  algorithm state, zero applied voltage, and zero bus current with no fault. The supervised
  provisional path now sends that same ramp through TI's volatile I²C speed override while
  holding the physical SPEED pin at zero. This isolates motor/startup tuning from the failed
  pin decoder without bypassing the permission latch, 0.5 A limit, or stop/fault handling.
- **The first I²C-controlled start reached the drive and exposed an un-deglitched hardware
  current trip** (2026-08-19). At roughly 3% command the MCF latched
  `HW_LOCK_LIMIT` (`CONTROLLER_FAULT_STATUS = 0x80040000`) before visible movement; the
  supply display did not catch the brief event. The seed had left `HW_LOCK_ILIMIT_DEG = 0`
  (no deglitch). It is now 2 µs, TI's normal tuning value, while the 2 A hardware threshold,
  0.5 A commanded startup current, and latched Hi-Z response remain unchanged.
- **The unloaded motor now aligns and rotates smoothly in open loop** (2026-08-19). With the
  2 µs current deglitch and a 500 mV auto-handoff floor, it aligned about 10°, accelerated
  smoothly through roughly 3, 6, and 15 RPM, then twitched at closed-loop handoff and latched
  abnormal BEMF (`0x80500000`). Peak supply current was only 0.114 A. The next seed raises
  the automatic floor to 1 V, which extended the smooth-ish open-loop run but produced the
  same handoff jump and fault at 0.115 A peak. The next seed uses deterministic manual handoff
  at 27 RPM; it reached 26.6 RPM, then produced the same jump and fault at only 0.119 A peak.
  The next seed keeps the manual threshold and widens TI's enabled abnormal-BEMF tolerance
  from 40% to 70% to accommodate the unmeasured KV-to-phase Ke convention.
- **The streamlined printable integration binder is ready** at
  `output/pdf/stillair-integration-field-guides.pdf`, with editable source in
  `docs/field-guides/`. It covers only the active electronics, mechanical integration,
  firmware, balance, workshop proof-speed, representative-start, and thermal tracks.
- **Curated short SMD technique videos** for one-pad tacking, tack-and-drag, and bridge
  cleanup are indexed in
  [`docs/field-guides/soldering-videos.md`](field-guides/soldering-videos.md). Use them with
  the project-specific component maps on binder sheets 1A and 1B.
- **The final test-location flow is settled**: no-motor and restrained bare-motor work on
  the desk; unpowered balance/runout; first powered full-rotor work on a secured 216 RPM
  external-drive setup in a cleared area; then loaded MPET, tuning, starts, normal speeds,
  shutdowns, and thermal testing on the installed ceiling plate. Workshop proof uses PCB-02
  Hall telemetry or the drive readout, continuous observation, and a reachable cutoff. GL100
  phases stay disconnected from PCB-01; the expected analog latch does not stop the external
  drive, and no safety bypass is used. Do not assume a vibration sensor, optical tachometer,
  remote interlock, or second operator. Use normal safety firmware plus the host CLI over
  long USB J6 whenever PCB-01 drives the motor.
- **Commissioning software is ready for the corrected first-spin retry**: the normal firmware now has a
  fault-aware `Mpet` service state and bounded `mpet run`, confirmed EEPROM commits with
  the required 750 ms wait and self-clear poll, nine-clock I2C recovery, `wait speed`, and six
  numbered scripts under `firmware/scripts/`, plus a volatile-only provisional configuration
  gate that prevents factory defaults from running. The host and target builds are covered by
  tests; real startup results, loaded tuning, and the resulting golden image remain
  hardware-gated.

## Next

Work from [integration.md](integration.md). Electronics is the main dependency spine; PCB-01
assembly, harnesses, first power, rails, USB, sustained MCF communication, and the end-to-end
Hall path have passed at 18 V. Next complete the remaining board-only safety checks before
connecting motor phases, then proceed through motor integration, balance, controller tuning,
essential hardware safety checks, workshop proof speed, representative starts, and the
thermal run.

## Candidates Not Chosen

- **EB-100 PCB-bracket CAD** — wait until PCB-01's omitted connectors are populated so the
  bracket and cable bends are designed around physical geometry; pairs naturally with the
  owner's BR-100 hand-fab.
- **Rotor balance/runout** — blade manufacturing and qualification passed; MEC-05 remains
  before any powered rotor run.

## Future Only On Explicit Request

Do not suggest, schedule, or use these as blockers unless Michael explicitly asks to resume
one: ENC-100 cosmetic housing, TEMP_SENSE firmware, intentional-imbalance testing,
exhaustive start matrices, exhaustive acoustic testing, network/Matter resilience testing,
and exhaustive fault permutations. Installation, tether, and catcher work are owner-managed
and must not be surfaced as project tasks.

## Learned Recently

- **Canada distributor terms + placed consolidated order** (DigiKey CAD is DDP; USD is
  CPT; 100888768 has 27 immediate lines after trimming contingency spares, four
  substitutions, two pins) → bom/README.md, bom.csv.
- **GL100 measurements + gate closures** (axial stack, washer → Z136.6, bore → pilot
  Ø29.85; face/bore ownership confirmed) → parts.md "GL100 release checks" +
  "Fabrication gates".
- **Owner verification philosophy** (measure only what feeds non-adjustable machined
  features or safety assumptions; adapt at install otherwise) → CLAUDE.md.
- **Drawing pass as model audit + frame-ambiguity gotcha** (caught M5-default
  counterbores and stale Ø6.1 pockets; angles mirror across sketch frames — define
  clockings relationally) → CLAUDE.md OnShape section.
- **MR-100 deletion + epoxy retention rationale**; **SUS304 substitution margin math**;
  **±0.05-tier reasoning for the pilot** → parts.md.
- **Order log + arrivals** (100668200 = 374750597; W2026080301372216 contents) →
  bom/README.md, bom.csv.
- **All remaining arrivals + BP-100 manufacturing completion** → STATE.md, bom/README.md,
  bom.csv, parts.md, blade-v2.md.
- **Integration dependency map + energy-sized work menu; ceiling approval/template and
  tether-spacing conflict** → integration.md, install.md.
- **Printable field-guide review** surfaced and recorded the loaded-rotor MPET requirement,
  unverified golden-image gate, proof-procedure and tether holds, SUS304 SP-100 truth,
  M3 cable-clamp taps, 10 nF C31 delay capacitor, and 30-second tach settling requirement
  → field-guide binder plus integration.md, parts.md, electrical.md, install.md, and the
  test matrix.
- **Scope simplification** (owner, 2026-08-17): MP-100 installation, tether proof, and
  catcher proof accepted complete; remaining installation is owner-managed. Cosmetic
  housing, TEMP_SENSE, imbalance, and exhaustive test variants are future-only and must not
  be prompted → integration.md, install.md, decisions.md, test matrix, field-guide binder.
