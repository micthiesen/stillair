# PCB

KiCad projects for the 78 × 58 mm V1 and 88 × 64 mm V2 controller boards (schematic
capture, layout, fab outputs). The complete circuit-level handoff (outline, schematic blocks,
starting values, pinouts, placement zones, layer plan, test points) is
[../docs/electrical.md](../docs/electrical.md), and the V1-to-V2 gate list is at the bottom
of that doc.

## Projects

- `pcb-01/` — the controller board (**PCB-01**). Captured, routed, and ordered from JLCPCB
  2026-07-30 (order W2026073105230212).
- `pcb-01-v2/` — the fresh **PCB-01 V2** controller project. It is intentionally not cloned from
  V1. Capture, placement, routing, silkscreen, and the submission package are complete; its exact
  authority is [`docs/pcb-01-v2.md`](../docs/pcb-01-v2.md) and its order procedure is
  [`pcb-01-v2/fab/ORDERING.md`](pcb-01-v2/fab/ORDERING.md).
- `pcb-02/` — the 24 × 8 mm DRV5033 Hall daughterboard (**PCB-02**). Created 2026-07-30:
  schematic captured (ERC clean), 2-layer board set up (outline, M2 hole pair as the BR-100
  datum, JLCPCB rules). Ships as its own small order — PCB-01 already went out separately.

## Tooling

KiCad 10 plus the [Konnect](https://github.com/mixelpixx/Konnect) MCP server, wired up in
`.mcp.json` (Claude Code) and `.codex/config.toml` (Codex), both project-scoped. The operating manual — who
drives what, session startup, and the quirks — is the **`/pcb` skill** at
[`.claude/skills/pcb/SKILL.md`](../.claude/skills/pcb/SKILL.md). Board constraints and the
safety-critical routing rules are committed as Konnect project config in
`pcb-01/.konnect/project.json`, so the agent reads them without being told.

Fabrication is planned through JLCPCB; JLCPCB assembly vs hand-population is TBD (prefer
footprints/parts in the LCSC catalog where it doesn't compromise the design, so the PCBA
option stays open). The Hall daughterboard (18 × 8 mm, DRV5033) is a second tiny board that
should ride in the same order/panel. A possible V2 reshape to a horizontal donut board is
noted in the handoff doc.

## Human probing map

PCB-01 test-point and connector locations are retained in `pcb-01/probe-map.json`; the human
workflow, ground-domain rules, and temporary-wire policy are in [`docs/probing.md`](../docs/probing.md).
Use `pcb/tools/probe_guide.py TP7`, `pcb/tools/probe_guide.py J8`, or
`pcb/tools/probe_guide.py TP2 --mode resistance` to print a complete one-step instruction. Run
`pcb/tools/probe_guide.py --verify-board` after any layout revision so the retained map cannot silently
drift from the board.

## JLCPCB order config

The bullets below are the historical V1 research record. They do not control PCB-01 V2. V2 uses
the impedance-controlled JLC041621-7628 build, exact POFV attachments, and assembly split in
[`pcb-01-v2/fab/ORDERING.md`](pcb-01-v2/fab/ORDERING.md).

- Standard 4-layer 1.6 mm with the order-form copper dropdown set to **2 oz outer / 1 oz
  inner** (the V1 order did not use a canned JLC04161H stackup; sanity-check the resulting
  dielectric build in the quote tool). ENIG and the Ø3.2 NPTH holes are unrestricted.
- **2 oz raises min trace/space to 0.15–0.16 mm** — check routing under the ESP module
  fits. The common fallback for a ~2 A board is 1 oz outer with ≥1.5–2 mm pours, avoiding
  the 2 oz penalty entirely; decide at capture.
- MCF exposed-pad thermal vias: request **POFV (copper-filled/capped vias)**, drills
  0.25–0.35 mm — a paid special process at 4 layers; budget it.
- Ballpark: ~$80–150 for qty 5 bare boards with the above; 2 oz doesn't block PCBA.

## Footprint/symbol sourcing (researched 2026-07)

Clean pulls from KiCad official libs: ESP32-C6-MINI-1 (needs KiCad ≥8.0.9), GCT USB4105
(note: **top-mount** — confirm against the housing), TC2030-NL, JST PH and SH/SRSS
connectors, Coilcraft LPS4018, Panasonic EEU-FR (parametric CP_Radial), SMC TVS, SOIC-14,
SOT-23 variants.

Needs Ultra Librarian download + datasheet verification: **MCF8316D** (rectangular-body
VQFN-40 RGF — KiCad's stock VQFN-40 is the wrong shape), **TPSM365R6** (RDN QFN-FCMOD).
Hybrid cases: TPS7A1601A (KiCad footprint, UL symbol; check EP copper vs TI's land),
SN74LVC1G74 DCT/SM8 (KiCad's generic SSOP-8 pad span is wider than TI's spec — use TI/UL's).
All TI discrete symbols come from SnapEDA/UL (pinouts are part-specific). Molex: the ordered
headers are the **right-angle** variants (43045-0200, 43650-0300) — use the horizontal
footprints, not vertical.
