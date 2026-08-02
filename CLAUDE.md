# Stillair

Custom 44-inch direct-drive ceiling fan: planning docs, BOM, commissioning tests, firmware,
and (eventually) CAD outputs and the KiCad PCB. The full 3D model lives in OnShape; everything
else lives here. This repo is the canonical source; the old ChatGPT design site is dead.

> This is a living document. Update it when you learn new preferences, patterns, or project
> conventions. Don't ask — just update it if something is missing or outdated.

**Session state: the fast-moving "what we're working on / what's next" lives in
[docs/STATE.md](docs/STATE.md) — read that first.** End work sessions with `/wrap`; decide an
open next step with `/next`.

## Building in OnShape together

Michael drives OnShape; Claude designs and instructs. Learned working style (from the BP-100
blade build, 2026-07):

- **One step at a time.** When Michael executes the clicks, give a single step with exact
  dialog values, then stop and wait for the result before the next. Never dump a 12-step
  sequence to execute blind — steps get invalidated by what the model actually does.
- **Natural OnShape referencing over typed coordinates.** Prefer projected geometry (U),
  midpoint/coincident snaps, dims to existing edges, and "up to next/face" end conditions.
  Typed coordinate tables are the fallback, not the default, and are error-prone across
  sketch-plane orientations.
- **Lean FeatureScript for geometry generation.** Custom FeatureScripts are the preferred way
  to get computed geometry (section curves, tables of sketches, parametric cuts) into the
  model: one FS file per item with multiple features in it, not many fragments — kept in
  `cad/*.fs`, edited here, `pbcopy`'d for pasting into a Feature Studio, committed like code.
  The line: **deterministic geometry from tables/math → FS; anything needing visual judgment
  or geometry feedback → manual features** (lofts blending into curved faces, fillets that
  may fail and need radius negotiation, up-to-next extrudes, anything you'd tune by eye).
- **FS gotchas that bit us**: sketch ids derive from array position, so append new stations
  at the array *end* and edit values in place — reordering breaks downstream feature
  references. Bare map keys collide with in-scope variable names (`{ r : r }` fails; quote
  them). `pbpaste`-verify after every `pbcopy`.
- **Lofts between dissimilar profiles want FS-generated guide curves.** A loft from a flat
  face to a spline section twists, and manual loft connections don't fix it; guide splines
  through *exact* section interpolation points do (smoothstep easing off flat faces so they
  leave tangent; dense samples wherever the shape changes fast, or the fit spline
  overshoots corners). And one guided loft through all stations beats two lofts meeting at
  a station — the seam always creases the silhouette. See the root/span guide features in
  `cad/bp100_sections.fs` (2026-07-28, BP-100 v3).
- **Provisional dimensions live in a Variable Studio, vendor models are reference-only.**
  Any number parts.md marks provisional or motor-gated (pilot OD, GL100 axial length, wire
  window clocking, Hall gap …) becomes a named variable (`#pilotOD`), so a bench measurement
  is a one-line edit that regenerates the stack. Imported vendor STEPs (GL100) are visual/
  interface reference — never boolean against them or hang mates on faces that a re-import
  would replace.
- **Cross-check computed geometry with a host-side script** (`cad/*_check.py` pattern) before
  Michael models it; rerun when the numbers change. The camber-line-vs-chord-line rod miss
  was caught by a question, not the script — extend the script when a new class of claim
  appears.
- **Verification effort follows cost asymmetry, not checklists** (Michael, 2026-08-01, GL100
  arrival). Once a vendor part's revision is physically confirmed, trust its STEP/datasheet
  for positions and interfaces. Don't pre-measure anything whose failure mode is cheap to
  adapt at assembly (thread depths, screw lengths — a bottoming screw is felt at hand-torque
  and fixed with a washer). Reserve bench measurement for dimensions that feed a
  **non-adjustable machined feature or a safety assumption** (KD-100 thickness → SP-100
  cross-hole; pilot bore ID → RH-100 pilot OD). When 99% sure, prefer adapting at install
  over 3× verification work — never generate measurement busywork.

## Quick reference

`firmware/` is three crates on purpose. `stillair-core` holds the whole behavioral contract as
sans-I/O logic with no esp-\* dependencies, so it builds and tests on the host; `firmware/cli`
is the host-side tuning harness; `firmware/app` is the ESP32-C6 binary and is its own
workspace with its own target.

```bash
cd firmware            # host workspace: core + cli
cargo test             # the tests that can actually fail for a behavioral reason
cargo fmt && cargo clippy --all-targets

cd firmware/app        # the C6 binary: target/runner from app/.cargo/config.toml
cargo build
cargo run              # flash + monitor via espflash (needs the board)
```

## Driving the fan (the tuning harness)

`firmware/cli` builds `stillair`, which speaks the console protocol to either a board
(`--port`) or an in-process simulator (`--sim`). Everything it prints is machine-readable and
it exits non-zero on failure, so a commissioning step is a shell command with an exit code.

```bash
cd firmware && cargo build
target/debug/stillair --sim script my-sequence.txt   # a sequence in ONE session
target/debug/stillair --port /dev/cu.usbmodem2101 wait running --for 30
target/debug/stillair --sim stream 10 --for 120 > sweep.csv
target/debug/stillair --port /dev/cu.usbmodem2101 config capture   # golden image, paste-ready
```

**Flashing the C6 dev board**: `espflash flash --port /dev/cu.usbmodem2101 --non-interactive
firmware/app/target/riscv32imac-unknown-none-elf/debug/stillair`, then drive it with
`--port`. The bare dev board **cannot leave `SafeBoot`**: GPIO22 (3.3 V PGOOD) floats low with
nothing attached, and floating-means-bad is the correct fail-safe reading, so no internal
pull-up is fitted. Jumper GPIO22 to 3V3 (and GPIO21 to 3V3 for nFAULT-idle-high, GPIO14 to GND
for ALARM-idle-low) to exercise the state machine on bare silicon. Even then `Starting` faults
with `NoRotation` after 15 s, because nothing generates FG edges — the simulator is still the
place to exercise behaviour, and the board is the place to exercise I/O.

**To debug Wi-Fi/Matter, capture the raw serial log** — the CLI only surfaces `@`-prefixed
protocol lines, and everything interesting during commissioning is a plain log line:

```bash
nohup sh -c 'cat /dev/cu.usbmodem2101 > /tmp/pair.log' &   # only one reader at a time
```

Kill the capture before running `espflash` or the CLI; they contend for the port. Apple Home
reports every commissioning failure as "Pairing Failed" regardless of cause, so this log is the
only place the real reason appears.

**Use `script` for anything multi-step.** Each CLI invocation opens a fresh link, and against
`--sim` a fresh link is a fresh simulator that has forgotten everything — so a two-command
sequence run as two invocations silently tests nothing.

**The simulator validates the harness, never the motor.** It runs the real `Supervisor`
against a toy rotor with simulated time, so protocol/CLI/CSV/pass-fail logic are all
exercised without hardware. It says nothing about sensorless startup, acoustics, or whether
any register value is correct.

**After firmware changes run `cargo fmt && cargo clippy --all-targets && cargo test` in
`firmware/`, and `cargo fmt && cargo clippy --all-targets && cargo build` in `firmware/app/`.**
New behavior belongs in `stillair-core` with a test; `app/` should stay thin enough that
nothing in it needs one.

## Always commit and push

Personal project: commit and push directly to `main` whenever something is finished, bundling
any other pending changes (docs/BOM/state) into the same push. No draft PRs, no asking first.
This overrides the global draft-PR workflow.

## Repo map

- `docs/` — the design dossier: [overview](docs/overview.md), [decisions](docs/decisions.md)
  (locked baseline + release gates), [mechanical](docs/mechanical.md),
  [parts](docs/parts.md) (dimensioned CAD handoff), [electrical](docs/electrical.md) (PCB
  handoff), [controls](docs/controls.md) (firmware contract), [build](docs/build.md), and
  [STATE.md](docs/STATE.md).
- `bom/` — `bom.csv` with design + purchase status per line; conventions in `bom/README.md`.
- `testing/` — `test-matrix.csv`, the pass/fail commissioning matrix with sign-off fields.
- `cad/` — fabrication outputs (DXF/STEP/print files) exported from OnShape when parts near
  release. The OnShape model itself is not in the repo.
- `pcb/` — KiCad project for the 78 × 58 mm V1/V2 controller board: `pcb/pcb-01/` (PCB-01),
  driven through the Konnect MCP server. See the `/pcb` skill before touching any `.kicad_*`
  file — those are never edited as text.
- `firmware/` — Rust `no_std` supervisor firmware: `core/` (host-testable contract) and
  `app/` (ESP32-C6 binary).

## Design invariants

Keep these properties when changing anything; they come from the safety architecture in
[docs/electrical.md](docs/electrical.md) and [docs/controls.md](docs/controls.md):

- Firmware **never** drives DRVOFF directly and **never** commutates phases; it can revoke
  drive permission but cannot force it on after a fault.
- The analog overspeed chain (Hall → LM2907 → TLV1701 → U6 lock) works without any firmware
  or MCF participation; only a low-voltage power cycle resets it.
- Power restoration always lands in off; direction changes only from verified stopped.
- Speed limits are layered: 170 RPM user max < 180 RPM MCF stored limit < 200 RPM analog trip.
- Numbers in `docs/` marked provisional (MCF register seeds, pilot diameter, anchor selection)
  are commissioning guesses that measured data replaces; when a measured value lands, update
  the doc and the test matrix together.

## Firmware conventions

- Bare-metal esp-hal 1.1 stack (no esp-idf): `esp-rtos` + Embassy, `esp-radio` for Wi-Fi,
  `esp-println`/`log` for logging (`ESP_LOG` env), `esp-backtrace` panics. Pure Rust is the
  point — never pull in esp-idf or other large C SDKs.
- Control plane is **Matter over Wi-Fi via rs-matter + rs-matter-embassy** (git dep). The
  `[patch.crates-io]` table in `app/Cargo.toml` pins **every** esp-\* crate to one esp-hal git
  rev, mirrored from rs-matter-embassy's own esp example — they share generated metadata, so
  it is all-or-nothing, and updating means taking a newer rev from that example rather than
  bumping one entry. `rustcrypto` (the default), never `mbedtls`: mbedtls drives CMake at a
  riscv32 C cross-compiler and does not build on macOS at all. Details and the Apple Home
  mapping: docs/controls.md > "Home integration" and "Matter implementation notes".
- **Stable** Rust, target `riscv32imac-unknown-none-elf` (ESP32-C6 only — the
  ESP32-C6-MINI-1-H4 in the BOM; never other chips). Toolchain pinned in
  `firmware/rust-toolchain.toml`.
- Runner is `espflash flash --monitor` via `firmware/.cargo/config.toml`. No secrets are
  committed; when Wi-Fi credentials become real, add them via `[env]` in an uncommitted
  overlay and document the mechanism here.
- Strong types (enums per state, no boolean flags), no debug leftovers, small focused
  modules. Format with plain `cargo fmt`; lint with `cargo clippy`.
- **Behavior goes in `stillair-core`, wiring goes in `app/`.** The core is sans-I/O: it takes
  an injected `Millis` plus sampled `Inputs` and returns `Action`s, so every contract clause
  is unit-testable without a board (including the 10 s holds). It must never gain an esp-\*
  dependency — that independence is also what keeps it clear of the `[patch.crates-io]` churn
  rs-matter-embassy will bring. Integer math only in the core: RV32IMAC has no FPU, so speeds
  are milli-RPM `u32`, not `f32`.
- When updating deps, the esp-* crates version-bump in lockstep (esp-hal / esp-rtos /
  esp-radio / esp-println / esp-backtrace / esp-alloc / esp-bootloader-esp-idf); check the
  MIGRATING docs in the esp-rs/esp-hal repo for breaking changes. Heads-up: esp-radio has a
  1.0.0 beta out; expect an API break when adopting it.
- CI (`.github/workflows/ci.yml`) has two jobs: `core` (fmt, clippy, **tests**) and `app`
  (fmt, clippy, release build). Clippy warnings fail the build there even though they're soft
  locally.

## Project knowledge lives in the repo, not personal memory

Do not use personal/auto memory for this project. All durable knowledge — design decisions,
measured data, gotchas, preferences — belongs in the repo where every future session sees it:
the right `docs/*.md`, `bom/bom.csv`, `testing/test-matrix.csv`, this file, or a skill under
`.claude/skills/`. When you learn something worth keeping, augment the appropriate home
instead of writing a memory. STATE.md holds pointers and decisions, never the content.

## Sibling projects

When unsure about tooling or conventions, check sibling projects under `../`
(`omni-notify` for AI-tooling conventions, `esp32` for the previous-generation firmware
patterns, `unseamless-coop` for the session-continuity system). Shared AI tooling syncs via
`/sync` (`.claude/skills/sync/sync-map.json` lists peers).

## On-demand procedures live in skills

- **/pcb** — KiCad + Konnect: capture, board setup, validation, and the agent/human split.
- **/next** — decide the next step: candidates, gating analysis, recorded in STATE.md.
- **/wrap** — conclude a session: sweep learnings into their homes, rewrite STATE.md, commit,
  push.
- **/sync** — reconcile shared AI tooling with peer projects.
