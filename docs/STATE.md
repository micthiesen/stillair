# State

Fast-moving work state and chosen next step. This records the work, not machine state or
uncommitted changes. Durable findings live in the linked docs.

Last updated: **2026-07-28** (ordering-campaign session: COTS substitution pass, then every
currently-orderable line ordered — Accu fasteners, DigiKey LCSC-gap electronics, brass rod,
and the ST-100 standoffs as the second custom part committed to metal.)

## Now

- **The firmware is done and runs on real hardware.** `firmware/` is three crates:
  `stillair-core` (`no_std`, zero esp-\* deps, sans-I/O, **171 host tests**), `firmware/cli`
  (the tuning harness), and `firmware/app` (the C6 binary). Supervisor, MCF8316D wire
  format, tuning console, configuration gate, and the Matter control plane are implemented
  and **verified end to end against Apple Home** (CTL-12). Everything left is gated on a
  real MCF8316D.
- **The full assembly model exists in OnShape and moves** — variable-driven, one Part
  Studio, revolute-mate animation. The model frame is rotated 180° about Z vs the docs
  ([mechanical.md](mechanical.md) > Coordinate system). Owner remainder: resize the RH-100
  tach pockets to Ø6.45 × 3.35 for the imperial magnets ([parts.md](parts.md)).
- **Everything orderable is ordered (2026-07-28)**: the complete mechanical fastener set
  incl. KD-100 DIN 440 washers and Nord-Locks (Accu, $219.45 CAD), the LCSC-gap
  electronics order 374750597 (DigiKey, ~$63 USD), CW-100 brass rod (Amazon), and
  **ST-100 rev A — JLCCNC, qty 4, 6061 clear anodized, $101.79** (files in `cad/`,
  pre-order check + fabrication callouts in [parts.md](parts.md)). Tach magnets, P-clips,
  and bench hardware are owner stock; every remaining electronics purchase rides the V1
  board run via LCSC ([bom/README.md](../bom/README.md)).
- **Custom metal is now measurement-gated, not design-gated.** SP-100 needs exactly two
  numbers, both in transit: measured KD-100 washer thickness (cotter Z = t + 133.2;
  washers due ~Thu) and measured GL100 axial body length (capture-gap stack). MC-100 and
  RH-100 wait on the physical motor (pilot bore, face ownership, wire-exit clocking, M4
  thread depths) plus Gate 01 (CubeMars bearing reply; worst case adds an external thrust
  bearing reshaping both). BR-100 is undesigned. ([parts.md](parts.md) fabrication gates,
  [build.md](build.md).)
- **On-arrival checks queued**: KD-100 washers (magnet test, flatness, measure t before
  drilling SP-100), M5 prevailing nuts (caliper AF ≤8.1, height ≤5.0), ST-100 (62.0 ±0.1,
  square on ends, chase taps with an M6 screw), MP-100 (straightedge flatness before
  ceiling drilling). All recorded in [bom.csv](../bom/bom.csv) notes.

## Next

**Capture the V1 controller schematic in KiCad** (`pcb/`) — carried forward; it is the
critical path to a fan that turns, and every remaining firmware unknown is gated on a real
MCF8316D. Follow [electrical.md](electrical.md) SCH-01–SCH-07 as amended; order config and
footprint sourcing in `pcb/README.md`. Capture-time notes from this session's sourcing:
use the **3296Y** footprint (not W — different footprint, substituted for stock), confirm
the Sunlord SWPA4018S470MT LCSC C-number + Isat ≥ ~0.5 A, and re-verify TPSM365R6V3RDNR
stock. Once a real MCF8316D exists: `stillair --port … config capture`.

Small model remainders, do opportunistically (tracked, not blocking): tach-pocket resize
(above), re-export `cad/BP-100.step` (committed STEP is v2 geometry), unmodeled hub screws
if wanted for visuals, and the step-9 clearance extras (BR-100 bracket at r76, MR-100 caps,
EB-100 + horizontal PCB envelope).

## Candidates Not Chosen

- **Motor-arrival release sprint**: when the GL100 lands, run the measurement checklist and
  release SP-100 → MC-100/RH-100; consider quoting all three now and batching them into one
  CNC order to share shipping. Becomes Next the day the box arrives.
- **Blade materials + first prints**: Ø3 CF rods (cut 374) and an LW-PLA spool are still
  unordered (blades were out of scope this session); segA material call is the owner's
  strength program. Print 4 sets, select 3.
- **Mount mockup** (MDF/printed disk + rod standoffs at the 62 mm stack) — still open,
  fully parallel with the PCB.
- **Non-concurrent Matter commissioning** (`run` vs `run_coex`) — a held lever, not a task.

## Learned Recently

- **ST-100 pre-order check** (JLC blind-tap drill math, screw-bottoming margins, which
  callouts are advisory-only, qty-with-spare rationale) → [parts.md](parts.md) ST-100.
- **OnShape turned-part + drawing how-to** (countersink-as-thread-chamfer, mid-plane
  mirror for the second tap, Datum/Geometric-tolerance tool behavior) →
  [`cad/README.md`](../cad/README.md).
- **KD-100 is purchased, not fabbed**: Accu DIN 440 Ø44 × Ø13.5 × 4.0; SP-100 stack
  re-derived around the 4 mm washer with a measure-first rule → [parts.md](parts.md),
  [mechanical.md](mechanical.md).
- **Sourcing traps and substitutions** (3296Y footprint swap, Sunlord-for-Coilcraft,
  Marketplace separate-shipping trap, 3-punch vs DIN 980V nut geometry, SPH-002T
  packaging) → [bom.csv](../bom/bom.csv) Design-status/Notes fields.
- **Scope rules**: common bench hardware is out of BOM scope; the DigiKey cart is
  LCSC-gap-only → [bom/README.md](../bom/README.md).
