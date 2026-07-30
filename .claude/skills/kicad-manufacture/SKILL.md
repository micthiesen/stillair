---
name: kicad-manufacture
description: |
  Manufacturing and fabrication workflow for the Stillair KiCad boards. Triggers on: "send to fab",
  "order boards", "gerbers", "JLCPCB", "manufacturing", "export for production", "pick and place",
  "assembly files", "generate fabrication outputs", "BOM for fab", "production files", "fab house".
argument-hint: "[fab house or export task]"
---

# Fabrication Outputs (Stillair)

> **Rewritten 2026-07-30 after the PCB-01 order.** The original Konnect skill told you to use
> `export_manufacturing_package` and `validate_for_manufacturing`. **Do not.** Both are broken
> against this KiCad 10 project (verified on PCB-01): the "jlcpcb" BOM has no LCSC column and
> KiCad-native headers, the position file is in **inches** with `Ref/PosX/PosY` headers,
> `drill.drl` is emitted as a *directory*, and the validator read the routed 4-layer board as
> "2 layers, 0 nets, 0 tracks — READY". The full division of labor lives in the **/pcb** skill;
> this file is the fab-output procedure only.

## The procedure

```bash
python3 pcb/tools/jlc_fab.py     # from the repo root; KiCad closed (or board saved + zones refilled)
```

Writes into `pcb/pcb-01/fab/`:

- `pcb-01-gerbers.zip` — 4 copper layers + masks + paste + silk + Edge.Cuts + Excellon drill
  + map. Upload this on the JLCPCB quote page.
- `bom-jlcpcb.csv` — `Comment,Designator,Footprint,LCSC Part #`, grouped, assembly subset only.
- `cpl-jlcpcb.csv` — `Designator,Mid X,Mid Y,Layer,Rotation`, mm, assembly subset only.

The script filters DNP refs, bare-pad "components" (TP*, J7 Tag-Connect, NT1, JP1), and the
`HAND_SOLDER` set (bench-populated parts — the list and its rationale live in the script and in
docs/electrical.md > "Fabrication"). LCSC numbers for parts whose schematic LCSC field is empty
merge from `pcb/pcb-01/fab/lcsc-map.csv` (schematic field wins when present); substitution
rationale is in that file's Note column. For a new board, copy/parameterize the script and
start a fresh lcsc-map.

**Pre-flight gate**: headless DRC diffed against the baseline in
`pcb/pcb-01/placement/waivers.md` — NOT Konnect's validator. Save + refill zones (`B`) in
KiCad first if the board changed; see the /pcb skill's DRC quirks.

## Part sourcing lookups

`search_jlcpcb_parts` has no local DB (`download_jlcpcb_database` 404s in Konnect v0.2.1) and
JLCPCB/LCSC part pages are JS-rendered and WebFetch-opaque. Use
**https://jlcsearch.tscircuit.com** (plain JSON/HTML mirror of the JLCPCB catalog):
`/resistors/list.json?package=0402&resistance=4700` (raw ohms — "4.7k" silently mismatches),
`/capacitors/list.json?package=0603&capacitance=<farads>`, `/components/list?search=...`.
Fields: `lcsc`, `is_basic`, `is_preferred`, `stock`. **JLC's SMT-pool stock ≠ LCSC marketplace
stock** — the order page's part-matching dialog is the final authority, and deep-stock parts
can still come up short there (two did on the PCB-01 order).

## JLCPCB order-flow facts (verified on the 2026-07-30 PCB-01 order)

- **Copper weights**: the impedance/"Specify Stackup" pickers (JLC04161H-…) lock copper foils.
  Leave both off and set Outer/Inner Copper Weight directly (PCB-01: 2 oz outer / 1 oz inner —
  2 oz outer IS offered on 4-layer).
- **Min Via Hole option must match the drill file** (`grep '^T[0-9]*C' *.drl`). PCB-01 has
  0.2 mm drills → the 0.2 mm tier, not the 0.3 default.
- **Standard PCBA is forced** when any part is "Standard Only" (the ESP32-C6 module is).
  Standard: $25 setup, $1.50/unique-part feeder (basic and extended alike). Boards < 70 mm in
  a dimension get auto edge rails; take the depanel service.
- **THT hand-solder service** ($3.50 + ~$0.017/joint) is worth it for cheap genuine-JST
  headers; not for authenticity-sensitive parts (Panasonic FR electrolytics stay bench-side).
- **"Confirm Parts Placement"** costs cents — always tick it; it's the backstop for parts with
  no preview model (U1 on this order) and for KiCad-native CPL rotations, which JLC
  auto-corrects imperfectly (verify diode bands and pin-1 in the preview, from the board file
  if in doubt — not from memory).
- Saved order pages decode offline: selected options carry the `cur` CSS class.
- Shipping to Canada: DHL Express — clearance handled, tax link by email, ~2.5%/min-$17
  processing; "Global Standard Direct Line" caps declared value at $99; billing your own
  courier account makes you importer of record.

## What Konnect's manufacturing toolset is still OK for

Nothing on this project. `estimate_cost` is untested and JLCPCB's live quote page is the real
number anyway. Don't load the `manufacturing` toolset.
