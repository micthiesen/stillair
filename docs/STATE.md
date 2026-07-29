# State

Fast-moving work state and chosen next step. This records the work, not machine state or
uncommitted changes. Durable findings live in the linked docs.

Last updated: **2026-07-29** (PCB-01 session: schematic captured, board placed, aesthetic
pass, three-round board-truth review loop — 4 blockers found and fixed — layout locked,
firmware register guards landed.)

## Now

- **PCB-01 layout is LOCKED and ready to route.** Full schematic (SCH-01–07, ERC clean,
  170 parts), 4-layer board set up per spec, all placement done and aesthetically aligned,
  and a 25-lens agent review loop run to convergence (round 3: GO, zero defects). Final DRC
  residuals are all documented waivers →
  [pcb/pcb-01/placement/waivers.md](../pcb/pcb-01/placement/waivers.md). The review found
  and fixed 4 blockers the spec-derived capture could never catch — including a bug that
  was *in the spec itself* (HALL_TACH pulldown-vs-pullup self-contradiction) →
  [electrical.md](electrical.md) "Open items from the 2026-07 board-truth review".
- **Review-sourced fixes are on the board and in the spec**: R43 10k pull-up to 3V3 (the
  analog overspeed chain was structurally blind without it), NT1 net-tie (the only
  PGND↔AGND bridge — was layout-prose only), C36–C40 tach filter alternates marked DNP
  (else ~18.5 µF ⇒ ~12 s trip lag), J5 side-entry SM04B + U12 DRT-3 footprints (both were
  wrong parts/packages), C42/C43 safety-latch decoupling added, PGOOD pull-up re-sourced
  to U3 VCC per TI practice, proximity shuffle (C5 at U1's VM corner, C11/C32/C34 at
  their pins).
- **Firmware carries the review's guards** (`stillair-core`, 149 tests green):
  `mcf8316::fields` pins the two datasheet-verified bit layouts (CLOSED_LOOP4.MAX_SPEED,
  DEVICE_CONFIG2 EXT_WDT), `mcf_config` tests fail any future captured image that misses
  the four wiring-dependent registers or enables GPIO watchdog tickle with a window the
  2 Hz heartbeat can't satisfy (only 1000 ms qualifies). TEMP_SENSE remains wired-but-
  unread — `TODO(temp-sense)` at the ADC1/TRNG line in `app/src/matter.rs`.
- **Mechanical/ordering state unchanged from 2026-07-28**: everything orderable is
  ordered; SP-100 waits on two measurements in transit (KD-100 washer t, GL100 axial
  length); MC-100/RH-100 wait on the physical motor + Gate 01; on-arrival checks queued in
  [bom.csv](../bom/bom.csv) notes. Owner remainder: RH-100 tach-pocket resize to
  Ø6.45 × 3.35 ([parts.md](parts.md)).

## Next

**Route PCB-01** — Michael lays traces and pours, Claude guides (his explicit split).
Standing guidance from the lock handoff: ground pours meet **only at NT1**; USB routes
J6 → U12 → module with no stub; net classes drive widths (Power24/Phase 2.0 mm, Rail3V3
0.5, Tach12V 0.4); MCF switching-loop review vs TI's reference layout happens during
routing; silkscreen ref cleanup comes **after** routing (the 199 silk overlaps are the one
deliberately-deferred DRC class — Claude can script the sweep once vias are down). Review
context and waivers: [electrical.md](electrical.md) review section,
[waivers.md](../pcb/pcb-01/placement/waivers.md), the /pcb skill.

## Candidates Not Chosen

- **Motor-arrival release sprint**: when the GL100 lands, run the measurement checklist and
  release SP-100 → MC-100/RH-100; consider batching all three into one CNC order. Becomes
  Next the day the box arrives.
- **Fab-output pass after routing** (gerbers, pos, BOM export via the /pcb skill's
  manufacture path; MCF/TPSM footprints vs Ultra Librarian per `pcb/README.md`) — the step
  after routing, not chosen because routing isn't done.
- **TEMP_SENSE firmware implementation** (shared-ADC arrangement vs Matter TRNG) — parked
  with a code TODO; needs bench priorities, not board work.
- **Blade materials + first prints**; **mount mockup** — carried, fully parallel.
- **Non-concurrent Matter commissioning** (`run` vs `run_coex`) — a held lever, not a task.

## Learned Recently

- **The board-truth review loop** (agents review the board netlist against *intent* with
  the spec off-limits; fix → sweep spec → re-run until nits-only) → the /pcb skill,
  "board-truth review loop"; findings + accepted tradeoffs → [electrical.md](electrical.md).
- **Placement toolkit + gotchas** (exact courtyard model after the silk-bleed parser bug,
  per-side edge waivers, rot-blind checker, F8 round-trip flow, connector mating-face
  rules) → /pcb skill quirks, `pcb/tools/`.
- **Analog-trip calibration math** (LM2907 K ±10 % makes RV1 trim mandatory; ripple ≈
  hysteresis ⇒ ±10 RPM scatter; C2 bank is the remedy) → [electrical.md](electrical.md)
  SCH-06 calibration.
- **MCF register-image capture checklist** (SPEED_MODE, SPEED_RANGE_SEL, ALARM_PIN_EN,
  OTW_REP, EXT_WDT window, MAX_SPEED mapping) → [electrical.md](electrical.md) open items
  + enforced in `firmware/core/src/mcf_config.rs` tests.
- **J5/U12 were wrong variants since capture** (BOM said side-entry; TPD2EUSB30 only
  exists in DRT) → fixed everywhere; lesson folded into the /pcb skill's review-loop and
  footprint practices.
