# State

Fast-moving work state and chosen next step. This records the work, not machine state or
uncommitted changes. Durable findings live in the linked docs.

Last updated: **2026-07-30** (routing session 3 wrap: ALL point-to-point routing done —
digital fan-out, tach/safety analog block, J8 debug legs. Only fills/stitching + two J8
plane taps remain.)

## Now

- **PCB-01 routing: every functional net is routed.** This session closed the entire
  digital fan-out (I2C + J5, SPEED/DIR/BRAKE straps, FG/NFAULT/ALARM, buttons/J7/UART,
  PGOOD, watchdog web, DRVOFF, TEMP_SENSE) and the entire tach + safety analog block
  (LDO feed + +12V star, Hall front-end, LM2907, comparator/VREF, latch web), plus the
  thin J8 debug legs and the old RAW24 input-stage gap. Validated at the documented DRC
  baseline after each chunk. Whys → [electrical.md](electrical.md) "Routing notes".
- **Remaining on the board** (in order): (1) J8.1 VM24 + J8.2 PGND taps — via at the
  x 98 plane edge + eastward 0.25 run each; (2) **B.Cu AGND ground fill** + stitching
  (picks up the 87 AGND ratsnest items incl. R1/R8–R10/C16/J4.2/J5.1 stragglers) and the
  **3V3 stitch pass** (29 items: vias where L3 is the 3v3-plane, F.Cu feeds west of
  x 98); (3) J8.3 starved-thermal fix/waiver (task #14); (4) final DRC + waiver re-triage
  (task #13, counts have shuffled: courtyards, silk, the antenna-keepout footprint edit);
  (5) scripted silkscreen sweep (Claude, KiCad closed).
- **Board min via 0.4/0.2 is now really in Board Setup** (was documented but never
  entered — same failure class as the net-classes miss; new skill quirk).
- **End-of-session gotcha harvest** (all now /pcb quirks): unfill-all saved to disk reads
  as a 66-via dangling storm headlessly (`grep -c filled_polygon` → 0 is the tell);
  duplicate-numbered button pads need copper joins; accidental micro vias dodge the
  diameter check; buried duplicate stubs need box-select to delete.
- **Mechanical/ordering unchanged**: motor in transit; SP-100 waits on measurements.

## Next

**Finish PCB-01**: J8 plane taps → ground/3V3 fills + stitching → final DRC with waiver
re-triage (tasks #13, #14) → silk sweep. Then the fab-output pass (gerbers/pos/BOM via
the /pcb skill manufacture path). All small, well-scoped steps; the fills are the only
one with judgment in it (fill order, stitching density).

## Candidates Not Chosen

- **Motor-arrival release sprint**: measurement checklist → SP-100 → MC-100/RH-100 CNC
  batch. Becomes Next the day the GL100 box arrives.
- **PCB-02 Hall daughterboard capture** — small board, unblocks the fab order bundle;
  natural follow-on to the PCB-01 fab-output pass.
- **TEMP_SENSE firmware implementation** — parked with `TODO(temp-sense)` in
  `app/src/matter.rs`.
- **Blade materials + first prints**; **mount mockup** — carried, fully parallel.

## Learned Recently

- **Five new /pcb quirks** (unfill-storm, duplicate pads, micro vias, buried stubs,
  board-setup-didn't-land) → `.claude/skills/pcb/SKILL.md`.
- **All routing decisions** (L3-split 3V3 feeding rule, J8 conventions, analog block
  layout) → [electrical.md](electrical.md) "Routing notes (2026-07, in progress)".
- **Chunked pad-vocabulary routing scaled to ~30 chunks without a single misroute** —
  the loop (geometry dump → 3–6 legs with pad refs → Michael threads → headless DRC diff)
  is the proven method for the fills phase too.
