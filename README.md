# stillair

Custom 44-inch direct-drive ceiling fan for quiet overnight air mixing: CubeMars GL100 KV10
gimbal motor, TI MCF8316D sensorless FOC on a custom controller board, ESP32-C6 supervisor
with local-only Apple Home control via Matter (rs-matter), and an independent analog
overspeed backstop.

This repo is the canonical source for everything except the OnShape 3D model:

- [`docs/`](docs/overview.md) — the full design dossier (start at the overview; current work
  state in [docs/STATE.md](docs/STATE.md))
- [`bom/`](bom/README.md) — parts list with purchase tracking
- [`testing/`](testing/README.md) — commissioning matrix with sign-off fields
- [`firmware/`](firmware/) — Rust `no_std` ESP32-C6 supervisor (stub; contract in
  [docs/controls.md](docs/controls.md))
- [`pcb/`](pcb/README.md): authoritative tscircuit source for new boards plus downstream KiCad
  routing and production outputs (requirements in [docs/electrical.md](docs/electrical.md))
- [`cad/`](cad/README.md) — fabrication outputs (specs in [docs/parts.md](docs/parts.md))

Firmware: `cd firmware && cargo build` (stable Rust; flashing via `cargo run` uses espflash).
