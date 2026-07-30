# State

Fast-moving work state and chosen next step. This records the work, not machine state or
uncommitted changes. Durable findings live in the linked docs.

Last updated: **2026-07-30** (routing session 2 wrap: power complete through the buck loop,
NT1 ground tie made real, USB + ESP done; digital fan-out and tach analog remain.)

## Now

- **PCB-01 routing: all power + USB + ESP done, validated at DRC baseline** (every
  violation class matches the documented waiver families; 276 ratsnest items remain, all
  planned). Done since capture: L2 AGND plane + PGND island (joined ONLY at NT1 — whose
  pad vias were nearly forgotten; see the new /pcb quirk), phases to J2 (U↔W pin swap),
  full MCF power cluster including the buck loop (C13/C15 column rearranged live to open
  via space — remote geometry analysis failed three times where the shove-router
  succeeded), input stage, L3 `vm24-plane`/`3v3-plane` split with via-storm distribution,
  3.3 V regulator, USB FS diff pair + ESD, ESP power/grounds. Board min via now 0.4/0.2.
  All whys → [electrical.md](electrical.md) "Routing notes (2026-07, in progress)".
- **Remaining to route** (in planned order): digital signal fan-out (ESP ↔ MCF ↔ watchdog:
  SDA/SCL, SPEED, DIR, FG, EN/BOOT, PGOOD, EXT_WD/TP16, heartbeat, TEMP_SENSE, J4/J5/J7),
  tach + safety analog block (Hall → LM2907 → RV1 → comparator → latch → DRVOFF; most
  placement-sensitive, +12 V LDO feed via R39 whose VM24 side is already stitched),
  stragglers (J8 DNP header thin traces), then B.Cu AGND ground fill + L3 leftover ground
  fill + stitching, final DRC to baseline, and the scripted silk cleanup (Claude, KiCad
  closed).
- **Workflow that's proven**: small chunks in pad-number + net-name vocabulary, Michael
  threads with walkaround, `kicad-cli pcb drc` on each save diffed against the waiver
  baseline, structural changes (cap rotations/rearrangements) sanctioned when corridors
  are provably dead. Deferred-AGND rule: west of U1, AGND is F.Cu-only (island below);
  R1/R8–R10/C16 AGND stragglers wait for the B.Cu fill.
- **Mechanical/ordering unchanged**: motor in transit; SP-100 waits on measurements.

## Next

**Finish routing PCB-01** — digital fan-out first (chunked like the power steps), then the
tach analog block, then fills + final DRC + waiver-count re-triage (open task) + silk
sweep. After that: fab-output pass (gerbers/pos/BOM via the /pcb skill manufacture path).

## Candidates Not Chosen

- **Motor-arrival release sprint**: measurement checklist → SP-100 → MC-100/RH-100 CNC
  batch. Becomes Next the day the GL100 box arrives.
- **Fab-output pass** — immediately after routing completes.
- **TEMP_SENSE firmware implementation** — parked with `TODO(temp-sense)` in
  `app/src/matter.rs`.
- **Blade materials + first prints**; **mount mockup** — carried, fully parallel.

## Learned Recently

- **NT1/net-tie vias, stale-fill DRC phantoms, zone-name reuse** → /pcb skill quirks
  (all three bit us this session).
- **Buck-loop resolution + all routing decisions** → [electrical.md](electrical.md)
  "Routing notes (2026-07, in progress)".
- **Remote mm-level geometry analysis has a floor**: three derived via placements failed
  where live shove-routing worked — hand corridor *topology* and constraints to the
  person at the screen, not coordinates, once gaps drop under ~1 mm.
