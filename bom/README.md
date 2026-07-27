# BOM

[`bom.csv`](bom.csv) is the canonical parts list with purchase tracking. Columns:

- **Design status** — the release state of the selection itself (selected, gated, V1-only).
  Gates reference [../docs/decisions.md](../docs/decisions.md) and
  [../docs/parts.md](../docs/parts.md).
- **Purchase status** — `Ordered (<vendor>)` / `Not ordered` / blocked notes. Update this
  column as orders go out and parts arrive (e.g. `Received`).
- **Order ref** — vendor order code (DigiKey part number, RobotShop product code).

Notes:

- Exact passive footprints and every fastener become orderable only after KiCad capture and
  CAD freeze their packages and lengths; they are intentionally not listed line-by-line yet.
- Custom mechanics (MP-100 through ENC-100) are fabricated per
  [../docs/parts.md](../docs/parts.md) and only after the motor and slab gates clear.
- Verify availability and price at order time.

Ordered so far (2026-07): the wall-box power chain, cable, Micro-Fit connector set, the
GST60A24-P1J supply (all DigiKey), and the GL100 KV10 motor (RobotShop). All PCB
semiconductors and JST/USB connectors are still to be ordered with the V1 board run.
