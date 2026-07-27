# Stillair

Custom 44-inch direct-drive ceiling fan: planning docs, BOM, commissioning tests, firmware,
and (eventually) CAD outputs and the KiCad PCB. The full 3D model lives in OnShape; everything
else lives here. This repo is the canonical source; the old ChatGPT design site is dead.

> This is a living document. Update it when you learn new preferences, patterns, or project
> conventions. Don't ask — just update it if something is missing or outdated.

**Session state: the fast-moving "what we're working on / what's next" lives in
[docs/STATE.md](docs/STATE.md) — read that first.** End work sessions with `/wrap`; decide an
open next step with `/next`.

## Quick reference

```bash
cd firmware
cargo build            # target/runner come from .cargo/config.toml
cargo run              # flash + monitor via espflash (needs the board)
```

**Always run `cargo fmt && cargo clippy && cargo build` (in `firmware/`) after firmware
changes.** There are no tests yet; add them when logic appears.

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
- `pcb/` — KiCad project for the 78 × 58 mm V1/V2 controller board (not started).
- `firmware/` — Rust `no_std` ESP32-C6 supervisor firmware.

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
  `esp-println`/`log` for logging (`ESP_LOG` env), `esp-backtrace` panics.
- **Stable** Rust, target `riscv32imac-unknown-none-elf` (ESP32-C6 only — the
  ESP32-C6-MINI-1-H4 in the BOM; never other chips). Toolchain pinned in
  `firmware/rust-toolchain.toml`.
- Runner is `espflash flash --monitor` via `firmware/.cargo/config.toml`. No secrets are
  committed; when Wi-Fi credentials become real, add them via `[env]` in an uncommitted
  overlay and document the mechanism here.
- Strong types (enums per state, no boolean flags), no debug leftovers, small focused
  modules. Format with plain `cargo fmt`; lint with `cargo clippy`.
- When updating deps, the esp-* crates version-bump in lockstep (esp-hal / esp-rtos /
  esp-radio / esp-println / esp-backtrace / esp-alloc / esp-bootloader-esp-idf); check the
  MIGRATING docs in the esp-rs/esp-hal repo for breaking changes.

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

- **/next** — decide the next step: candidates, gating analysis, recorded in STATE.md.
- **/wrap** — conclude a session: sweep learnings into their homes, rewrite STATE.md, commit,
  push.
- **/sync** — reconcile shared AI tooling with peer projects.
