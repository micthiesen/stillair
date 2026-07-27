# State

Fast-moving work state and chosen next step. This records the work, not machine state or
uncommitted changes. Durable findings live in the linked docs.

Last updated: **2026-07-26** (control plane locked to Matter/rs-matter; BOM sourcing
verified and completed).

## Now

- **The repo is the canonical source.** All content from the ChatGPT design site (revision 3,
  GL100) lives in `docs/`, `bom/`, and `testing/`; temporary links to the site's diagrams
  remain in mechanical/parts/electrical docs until OnShape reproduces them.
- **Control plane is locked: Matter over Wi-Fi via rs-matter + rs-matter-embassy**, used from
  Apple Home, replacing the HAP/HomeKit plan. Its ESP examples pin exactly our firmware
  stack; integration details in [controls.md](controls.md) > "Home integration". Open product
  question: whether Apple Home renders `AirflowDirection` (fallback: a second On/Off
  "reverse" endpoint).
- **First orders are in.** Wall-box power chain, supply, connectors, cable (DigiKey) and the
  GL100 (RobotShop). BOM now carries LCSC numbers + lifecycle notes; boards will come from
  JLCPCB (PCBA vs hand-population TBD). LM2907M is active but thin-stocked — buy spares with
  the V1 order; exact MCF8316DULVRGFR isn't LCSC-stocked (consign or evaluate the plain D
  variant).
- **Firmware scaffold compiles and CI guards it** (fmt/clippy -D warnings/release build). No
  business logic; contract in [controls.md](controls.md).
- **Nothing is fabricated.** Motor-dependent metal gates on measuring the purchased GL100;
  the V1 PCB gates on KiCad capture. A donut-shaped horizontal V2 board is a documented open
  option ([electrical.md](electrical.md) > PCB-01).

## Next

**Capture the V1 controller schematic in KiCad** (`pcb/`), following
[electrical.md](electrical.md) block by block (SCH-01 through SCH-07). It gates the V1 board
order, which gates motor tuning and every V1-to-V2 test. Not hardware-gated. While capturing,
prefer LCSC-stocked footprints (see `bom/bom.csv` Notes) so the JLCPCB-assembly option stays
open.

## Candidates Not Chosen

- **rs-matter devkit spike.** Build rs-matter-embassy's `light_wifi_persistent` example on a
  bare ESP32-C6 devkit, commission into Apple Home (accept the uncertified-accessory prompt),
  then swap in a Fan endpoint (0x002B) with a hand-written FanControl handler to answer the
  AirflowDirection UI question. Needs a C6 devkit in hand; runs fully in parallel with KiCad.
- **Motor release checks (measure faces, thread depths, bores; import STEP).** Hardware-gated:
  do it as soon as the GL100 arrives; unblocks motor-dependent metal in CAD.
- **OnShape modeling of motor-independent parts (MP-100 plate, ST-100 standoffs, blades).**
  Startable now but off the critical path.
- **Order PCB semiconductors.** Fold into the V1 board order after KiCad capture freezes
  footprints (decides consign-vs-catalog for the MCF variant too).

## Learned Recently

- **rs-matter is the only maintained pure-Rust Matter path and fits our exact stack** →
  [controls.md](controls.md) > "Home integration" (versions, commissioning, OTA caveat,
  fallbacks).
- **BOM lifecycles/sourcing verified 2026-07** → `bom/bom.csv` Notes column + `bom/README.md`
  (LM2907 thin stock, MMSZ5242B dual-source, MCF variant catalog gap, JST mating PNs).
- **Donut-V2 geometry is viable (ID Ø30–40 × OD ≤Ø130 inside the standoffs, carrier-boss
  mounting) at the cost of re-running layout-sensitive V1 tests** →
  [electrical.md](electrical.md) > PCB-01.
