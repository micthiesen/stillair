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

## 2026-08-09 DigiKey consolidated order

DigiKey orders **100616913** and **100723632** were cancelled. Their cancellation invoices
(`130375795` and `130375791`) were checked line by line on 2026-08-09 and are the source of
truth for reconstructing the replacement basket. Order 100616913 contained 12 lines in
CAD/DDP; 100723632 contained 24 lines in USD/CPT. The four Micro-Fit connector families
appeared in both orders.

Use **one DigiKey Canada order paid in CAD** for the combined available basket. DigiKey's
Canadian CAD checkout is DDP, with duty and customs paid by DigiKey, and delivery is free
above CAD $100. A USD checkout is CPT and leaves tax, duty, and brokerage due on delivery;
that currency choice, not FedEx itself, caused the separate carrier bill on order 129980940.
Exclude Marketplace lines because they use supplier shipping and may be CPT even in a CAD
cart. The 30-line browser review cart **375208526**, named
`stillair-consolidated-reorder`, was checked line by line with no Marketplace, drop-ship,
or backordered offers. Before checkout, $46.37 of precautionary extras was removed: the
Panasonic bulk-cap, TLV1701 and SMD trimmer spare-only lines were dropped; power and motor
headers were reduced from 5 each to 2 each; S3B-PH-K-S from 2 to 1; NTCALUG from 2 to 1;
Keystone 24481 from 6 to 4; and C1206C104K3GACTU from 4 to 2. The useful connector
consumables, calibration parts and bench stock stayed.

The final 27-line basket was placed as DigiKey order **100888768** on 2026-08-09 and
received 2026-08-14 for
**CAD $179.45 before tax / $200.98 after BC GST+PST**, with free FedEx International
Priority. All lines were immediate-stock DigiKey warehouse items at checkout.

Mouser Canada is the runner-up: CAD orders can also be DDP and ship free above CAD $100,
but it does not offer the Belden 5300UE in project-sized cut lengths, and its exact E-Switch
was not immediately stocked in the comparison snapshot. Newark's small-quantity coverage
was worse (for example, the recovered 43650-0300 carried a 10-piece minimum from UK stock).
Splitting the basket loses the landed-price advantage without improving project readiness.

Pinned outside this order:

- `DMP6023LE-13` qty 2 loose spares: DigiKey stock zero; assembled boards already contain
  the required devices. Mouser had deep stock, so these are easy to revisit later.
- SparkFun `15362` qty 2: optional DNP scope headers, not normally stocked at DigiKey.

Four stock gaps stayed in the single DigiKey order through equivalent, same-footprint parts:

- KEMET `C0603C104K5RACTU` replaces Samsung `CL10B104KB8NNNC` (100 nF, 50 V, X7R, 0603).
- Vishay `PTN0603Y1002BST1` replaces Yageo `RT0603BRD0710KL` (10 kΩ, 0.1%, thin film,
  0603; power rating improves from 0.1 W to 0.15 W).
- KEMET `C0603C105K3RACTU` replaces Samsung `CL10B105KA8NNNC` (1 uF, 25 V, X7R, 0603).
- Taiyo Yuden `EMK107ABJ475KA-T` replaces Samsung `CL10A475KO8NNNC` (4.7 uF, 16 V,
  X5R, 0603).

The earlier fuse-holder mismatch was a reconstruction error. Invoice 130375795 confirms
that cancelled order 100616913 contained Littelfuse `FHAC0001ZXJ` / DigiKey `F3209-ND`, a
proper inline ATO holder, and it is in order 100888768. The formerly backordered Molex
`43650-0300` was also immediate-stock and is in that order.

Ordered so far: the GL100 KV10 motor (RobotShop), the MP-100 ceiling
plate (JLCCNC), and — 2026-07-28 — the complete mechanical fastener set including the
KD-100 catcher washers and Nord-Locks (Accu, $219.45 CAD), CW-100 brass rod (Amazon), and
the LCSC-gap electronics order 374750597 (DigiKey, ~$63 USD: insurance ICs and spares,
bulk caps, USB-C, cable-side JST housings/contacts, trimmers, dev cable), and the ST-100
standoffs (JLCCNC, qty 4, $101.79). The consolidated loose-parts basket was ordered from
DigiKey as **100888768** on 2026-08-09 ($200.98 CAD after tax). The V1 board run went out 2026-07-30 as JLCPCB
W2026073105230212 (boards + all LCSC-path parts via PCBA) with PCB-02 following the same
day as W2026073108244536. DigiKey **100723632** ($62.33, 24 lines: PCB-02's C1/J1,
the C34 1206 C0G, board-#2 completion headers, the J4 NTC element, EB-100 M3 standoffs,
tach-chain 0.1% spares, the C2 DNP calibration ladder, and bench spares) was placed
2026-07-30 and cancelled before fulfillment; its required and useful-stock lines were
reconciled into order 100888768 above.

Arrivals 2026-08-01: the GL100 motor (RobotShop), the complete Accu fastener order, the
ohcanadasupply.ca Titen HD anchors, and DigiKey 374750597 (salesorder 100668200 on the
packing slip). Arrivals 2026-08-14: DigiKey 100888768, PCB-01, PCB-02, all JLCCNC parts
(MP-100, four ST-100s, SP-100, MC-100, RH-100), and the completed owner-manufactured
BP-100 blade set. The owner accepted the delivered parts and order contents as received;
blade-root qualification MEC-01/02/02B passed by owner report. MEC-05 assembled rotor
balance/runout remains open.

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
