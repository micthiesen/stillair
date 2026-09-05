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

Michael drives OnShape; give one exact UI step at a time and wait for its result. Prefer projected
geometry, constraints, and face-relative end conditions over typed coordinates.

- Put deterministic table/math geometry in one `cad/*.fs` FeatureScript per item; keep work needing
  visual judgment manual. Append FS station arrays rather than reordering them, quote map keys that
  collide with variables, and verify every `pbcopy` with `pbpaste`.
- Guided lofts use splines through exact section points, eased off flat faces. Prefer one guided
  loft through all stations; split lofts crease at the seam. See `cad/bp100_sections.fs`.
- Put provisional or motor-gated dimensions in Variable Studio. Vendor STEP files are reference
  only: do not boolean against them or mate to faces a re-import can replace.
- Run the matching `cad/*_check.py` before modeling and after number changes. Extend it when a new
  class of geometric claim escapes validation.
- Define angular clocking relationally and verify it visually. Release through a drawing with auto
  hole callouts; DWG NO and filename suffice when TITLE cannot be edited.
- Match verification effort to consequence. Trust a physically confirmed vendor revision. Measure
  dimensions feeding non-adjustable machining or safety assumptions; adapt cheap assembly details
  such as screw length during installation.

## Probing PCB-01 with Michael

Before asking Michael to locate or probe any PCB-01 test point, connector, or signal, read
[`docs/probing.md`](docs/probing.md) and generate the exact request with
`pcb/tools/probe_guide.py <TP-or-J> [--mode dc|resistance|scope]`. The retained map supplies the
component-side orientation, nearby labelled landmarks, correct ground domain, instrument setup,
expected result, stop conditions, and literal report format. Never give only a designator or rely on
remembered connector orientation.

Present the generated request in concise, natural bench language. By default include only the
relative location, exact clip points, whether a temporary pigtail is worthwhile, expected result,
and literal report template. Keep coordinates, circuit rationale, and the full safety inventory in
the guide unless one changes the immediate action.

Give one hookup at a time. Leads are connected, inspected, moved, and removed with all relevant
power off; apply power only after Michael confirms the hookup is stable. Prefer test points over
connector pins. For repeated, installed, tiny-pad, or automated measurements, follow the guide's
temporary-pigtail criteria instead of repeatedly landing handheld probes. Never ground a scope to a
motor phase. After any board-layout change, run `pcb/tools/probe_guide.py --verify-board` and inspect
a fresh component-side render before using the map.

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
target/debug/stillair --port /dev/cu.usbmodem2101 mpet run --for 120
target/debug/stillair --sim script scripts/04-loaded-speed-ladder.txt
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
- `pcb/` — KiCad projects for the 78 × 58 mm V1 and 88 × 64 mm V2 controller boards:
  `pcb/pcb-01/` (V1) and `pcb/pcb-01-v2/` (V2),
  driven through Konnect, project scripts, and KiCad itself. Read `/pcb` before touching any
  `.kicad_*` file; it defines the safe channel for each file and operation.
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
