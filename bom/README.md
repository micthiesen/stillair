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

- Exact passive footprints (and any PCB-side mounting hardware) become orderable only after
  KiCad capture freezes their packages; they are intentionally not listed line-by-line yet.
  The **mechanical** fastener set was frozen by the 2026-07-27/28 CAD work and is now listed
  line-by-line with sourcing (2026-07-28 holistic pass). M3 hardware for EB-100/ENC-100/BR-100
  waits on those bracket designs.
- Custom mechanics (MP-100 through ENC-100) are fabricated per
  [../docs/parts.md](../docs/parts.md) and only after the motor and slab gates clear.
- Verify availability and price at order time.
- **Purchasing split** (decided pre-repo, carried forward): DigiKey Canada for off-board
  hardware, cable, connectors, and bring-up spares; Mouser for DigiKey stock gaps (the
  TPSM365R6V3RDNR has been out of stock at DigiKey before); JLCPCB turnkey sourcing for
  board-mounted parts when using their assembly — JLCPCB's overseas-consignment fees are
  uneconomic for a prototype, so consignment is effectively off the table.
- **JLCPCB path**: boards come from JLCPCB; PCBA vs hand-population is still open, but the
  owner is comfortable hand-installing SMD (confirmed 2026-07-28), so hand-population and
  the hand-solder-just-the-MCF hybrid are both live options. The 2026-07-28 DigiKey cart
  (Web ID 374750597, salesorder 100668200 — the number on the packing slip; received
  2026-08-01) deliberately holds only **LCSC-gap parts**: thin/absent-at-LCSC ICs
  and spares, Coilcraft (never on LCSC), Panasonic FR bulk caps, genuine JST PH headers,
  the GCT USB-C, cable-side housings/contacts, and the Hall daughterboard parts. As of 2026-07
  every IC except the exact `MCF8316DULVRGFR` variant is in the LCSC catalog, but all as
  Extended parts (per-part feeder fee), and LM2907M / TPS3435 stock is thin. Since
  consignment is uneconomic, the MCF choice for a PCBA run is: swap to the plain
  `MCF8316DVRGFR` after an equivalence check, or hand-solder just that part on an otherwise
  assembled board.
- Tools (crimpers etc.), wall-box enclosure hardware, and test equipment are deliberately out
  of scope for this BOM.
- **Common electronics bench hardware is also out of scope** (owner decision 2026-07-28):
  PCB standoffs, M3 mounting screws for boards, jumper wire, heat-shrink and similar
  commodity stock the owner already keeps on hand. Only project-specific or
  uncommon-spec hardware gets a BOM line.

## 2026-08-09 DigiKey reorder decision

DigiKey orders **100616913** and **100723632** were cancelled. The former order ID was
never recorded in the repo, but its contents reconstruct cleanly from the still-pending
wall-box power chain, supply, cut cable, and first Micro-Fit quantities. Order 100723632
is fully reconstructed from its 24 recorded lines. `bom.csv` now reflects the cancelled
quantities instead of treating them as in hand or in flight.

Use **one DigiKey Canada order paid in CAD** for the combined available basket. DigiKey's
Canadian CAD checkout is DDP, with duty and customs paid by DigiKey, and delivery is free
above CAD $100. A USD checkout is CPT and leaves tax, duty, and brokerage due on delivery;
that currency choice, not FedEx itself, caused the separate carrier bill on order 129980940.
Exclude Marketplace lines because they use supplier shipping and may be CPT even in a CAD
cart. The combined warehouse basket is comfortably above CAD $100. A stock-price snapshot
on 2026-08-09 puts it around **CAD $140-155 before BC tax**, excluding the pins below;
the range remains provisional because order 100616913 did not preserve its Belden cut
length or Micro-Fit contact spare quantity. Confirm those two quantities in the cancelled
order before cart upload.

Mouser Canada is the runner-up: CAD orders can also be DDP and ship free above CAD $100,
but it does not offer the Belden 5300UE in project-sized cut lengths, and its exact E-Switch
was not immediately stocked in the comparison snapshot. Newark's small-quantity coverage
was worse (for example, the recovered 43650-0300 carried a 10-piece minimum from UK stock).
Splitting the basket loses the landed-price advantage without improving project readiness.

Pinned outside this order:

- `DMP6023LE-13` qty 2 loose spares: DigiKey stock zero; assembled boards already contain
  the required devices. Mouser had deep stock, so these are easy to revisit later.
- SparkFun `15362` qty 2: optional DNP scope headers, not normally stocked at DigiKey.
- The wall-box fuse holder: `0FHA0200Z` is officially an automotive Add-A-Circuit tap,
  not the covered standalone inline holder described by the BOM, and DigiKey stock is zero.
  `0FHA0200ZP` is the same tap in retail packaging with four fuses, not a design fix.

Two commodity stock gaps stay in the single DigiKey order via DigiKey-listed direct
substitutes: KEMET `C0603C104K5RACTU` for the depleted Samsung 100 nF decoupling strip,
and Taiyo Yuden `EMK107ABJ475KA-T` for the depleted Samsung 4.7 uF DNP-ladder cap. The
formerly backordered Molex `43650-0300` has recovered to deep stock and is no longer pinned.

Ordered so far: the GL100 KV10 motor (RobotShop), the MP-100 ceiling
plate (JLCCNC), and — 2026-07-28 — the complete mechanical fastener set including the
KD-100 catcher washers and Nord-Locks (Accu, $219.45 CAD), CW-100 brass rod (Amazon), and
the LCSC-gap electronics order 374750597 (DigiKey, ~$63 USD: insurance ICs and spares,
bulk caps, USB-C, cable-side JST housings/contacts, trimmers, dev cable), and the ST-100
standoffs (JLCCNC, qty 4, $101.79). The V1 board run went out 2026-07-30 as JLCPCB
W2026073105230212 (boards + all LCSC-path parts via PCBA) with PCB-02 following the same
day as W2026073108244536. DigiKey **100723632** ($62.33, 24 lines: PCB-02's C1/J1,
the C34 1206 C0G, board-#2 completion headers, the J4 NTC element, EB-100 M3 standoffs,
tach-chain 0.1% spares, the C2 DNP calibration ladder, and bench spares) was placed
2026-07-30 and cancelled before fulfillment; its available lines now join the consolidated
CAD reorder above.

Arrivals 2026-08-01: the GL100 motor (RobotShop), the complete Accu fastener order, the
ohcanadasupply.ca Titen HD anchors, and DigiKey 374750597 (salesorder 100668200 on the
packing slip). Still in transit: PCB-01 (DHL) and PCB-02 (Global Standard Direct Line).

The motor-gated CNC batch went out 2026-08-02 as JLCCNC **W2026080301372216** ($204.44
shipped): SP-100 $82.76 (SUS304 — JLCCNC stocks no 17-4PH; margin math in parts.md),
MC-100 $48.83 and RH-100 $42.08 (both 6061-T6, bead blast + natural matte anodize;
RH-100 on the ±0.05 tolerance tier so the measured-bore pilot fit is contractual, the
one paid tier in the batch that's functionally load-bearing).

DigiKey cart mechanics (learned building 100723632 via browser automation): the cart
page's Bulk Add box takes `qty, part-number` lines but **silently drops MPNs that have
multiple packaging variants** (cut tape / reel / Digi-Reel) — use packaging-specific
DigiKey numbers (the `-1-ND` / `...CT-ND` forms, findable on each product page) for
anything taped; single-listing MPNs (connectors, hardware) resolve fine as bare MPNs.
Verify the cart line MPNs after a bulk add rather than trusting the submit.
