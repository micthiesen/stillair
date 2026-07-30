# State

Fast-moving work state and chosen next step. This records the work, not machine state or
uncommitted changes. Durable findings live in the linked docs.

Last updated: **2026-07-30** (mid-routing checkpoint: PCB-01 power + USB + ESP routed,
buck loop and tach analog remain.)

## Now

- **PCB-01 routing is ~60% done** (Michael lays copper, Claude sequences — working well
  as label-level step-by-step). Done: L2 ground planes (AGND + PGND island meeting only
  at NT1), antenna keepout, motor phases (B.Cu diagonals into J2 after the U↔W pin swap),
  the whole MCF west-side cluster, input stage (J1 → fuse → reverse-PMOS → planes), L3
  split into `vm24-plane`/`3v3-plane` with via-storm distribution, the 3.3 V regulator,
  USB (connector fan-out + FS diff pair + ESD), ESP power/grounds. Rationale for every
  non-obvious call → [electrical.md](electrical.md) "Routing notes".
- **Remaining to route**: MCF buck loop (pins 3/5 → L1/C16 — the hardest corridor, B.Cu
  dives, in progress), digital signal fan-out (ESP ↔ MCF ↔ watchdog: SDA/SCL, SPEED, DIR,
  FG, EN/BOOT, PGOOD, EXT_WD, heartbeat), tach + safety analog block (Hall → LM2907 →
  comparator → latch, the most placement-sensitive), +12 V tach LDO, leftover connectors/
  TPs, then B.Cu AGND fill + L3 leftover ground fill + final stitch, full DRC, and the
  scripted silkscreen cleanup (Claude, KiCad closed). 283 ratsnest items at checkpoint.
- **DRC discipline held**: all error classes at baseline waiver families; via-diameter
  and stacked-via slips caught and fixed same-chunk. `kicad-cli pcb drc` on a saved file
  is the fast loop (no UI round-trip).
- **Layout-lock amendments** (routing-driven, all recorded): J2 phase order U↔W, C15 and
  C12 rotated 180°, net classes actually persisted to `.kicad_pro` (the setup script had
  silently never run).
- **Mechanical/ordering unchanged**: motor still in transit; SP-100 waits on measurements.

## Next

**Finish routing PCB-01** — buck loop, then digital fan-out, then tach analog (guide
chunk-by-chunk in pad-label vocabulary; Michael threads, walkaround negotiates). Then
fills + final DRC + silk sweep. After that: fab-output pass (gerbers/pos/BOM via the /pcb
skill manufacture path).

## Candidates Not Chosen

- **Motor-arrival release sprint**: measurement checklist → SP-100 → MC-100/RH-100 CNC
  batch. Becomes Next the day the GL100 box arrives.
- **Fab-output pass** — immediately after routing completes.
- **TEMP_SENSE firmware implementation** — parked with `TODO(temp-sense)` in
  `app/src/matter.rs`.
- **Blade materials + first prints**; **mount mockup** — carried, fully parallel.

## Learned Recently

- **Routing decisions + ground/plane architecture** → [electrical.md](electrical.md)
  "Routing notes (2026-07, in progress)".
- **J2 phase pinout change** → SCH-07 connector table in electrical.md.
- **Waiver counts drift with rotations/net-class changes** — re-triage at session end
  (task open); J7's Tag-Connect keepout self-flag excluded in-UI as benign.
- **Step-by-step routing workflow** (small chunks, pad-number + net-name vocabulary,
  screenshots at checkpoints, headless DRC between steps) — candidate for the /pcb skill
  once routing completes and the pattern is proven end-to-end.
