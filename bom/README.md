# BOM

[`bom.csv`](bom.csv) is the canonical parts list with purchase tracking. Columns:

- **Design status** — the release state of the selection itself (selected, gated, V1-only).
  Gates reference [../docs/decisions.md](../docs/decisions.md) and
  [../docs/parts.md](../docs/parts.md).
- **Purchase status** — `Ordered (<vendor>)` / `Not ordered` / blocked notes. Update this
  column as orders go out and parts arrive (e.g. `Received`).
- **Order ref** — vendor order code (DigiKey part number, RobotShop product code).

- **Notes** — sourcing detail: LCSC part numbers (for the JLCPCB path), stock caveats,
  alternates. Stock counts are snapshots (dated) — re-verify before ordering.

Notes:

- Exact passive footprints and every fastener become orderable only after KiCad capture and
  CAD freeze their packages and lengths; they are intentionally not listed line-by-line yet.
- Custom mechanics (MP-100 through ENC-100) are fabricated per
  [../docs/parts.md](../docs/parts.md) and only after the motor and slab gates clear.
- Verify availability and price at order time.
- **JLCPCB path**: boards come from JLCPCB; PCBA vs hand-population is TBD. As of 2026-07
  every IC except the exact `MCF8316DULVRGFR` variant is in the LCSC catalog, but all as
  Extended parts (per-part feeder fee), and LM2907M / TPS3435 stock is thin. The MCF either
  gets consigned or swapped to the plain `MCF8316DVRGFR` after an equivalence check.
- Tools (crimpers etc.), wall-box enclosure hardware, and test equipment are deliberately out
  of scope for this BOM.

Ordered so far (2026-07): the wall-box power chain, cable, Micro-Fit connector set, the
GST60A24-P1J supply (all DigiKey), and the GL100 KV10 motor (RobotShop). All PCB
semiconductors and JST/USB connectors are still to be ordered with the V1 board run.
