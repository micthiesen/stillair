# State

Fast-moving work state and chosen next step. This records the work, not machine state or
uncommitted changes. Durable findings live in the linked docs.

Last updated: **2026-07-26** (repo bootstrapped; design site imported and deprecated).

## Now

- **The repo is now the canonical source.** All content from the ChatGPT design site
  (revision 3, GL100) is consolidated into `docs/`, `bom/`, and `testing/`; the site is no
  longer referenced.
- **First orders are in.** The wall-box power chain, GST60A24-P1J supply, Micro-Fit connector
  set, Belden cable (DigiKey), and the GL100 KV10 motor (RobotShop) are ordered; see
  [../bom/bom.csv](../bom/bom.csv). All PCB semiconductors and JST/USB connectors wait for
  the V1 board run.
- **Firmware scaffold compiles.** `firmware/` is a stubbed ESP32-C6 supervisor on the current
  esp-hal 1.1 stack (stable Rust, esp-rtos/Embassy, esp-radio in the tree but unused). No
  business logic yet; the contract is [controls.md](controls.md).
- **Nothing is fabricated.** Motor-dependent metal is gated on measuring the purchased GL100
  ([parts.md](parts.md) > "Fabrication gates"); the V1 PCB is gated on KiCad capture.

## Next

**Capture the V1 controller schematic in KiCad** (`pcb/`), following
[electrical.md](electrical.md) block by block (SCH-01 through SCH-07). It gates the V1 board
order, which gates motor tuning and every V1-to-V2 test; nothing else on the critical path can
start before parts arrive. Not hardware-gated.

## Candidates Not Chosen

- **Motor release checks (measure faces, thread depths, bores; import STEP).** Hardware-gated:
  do it as soon as the GL100 arrives; it then unblocks motor-dependent metal in CAD.
- **OnShape modeling of motor-independent parts (MP-100 plate, ST-100 standoffs, blades).**
  Startable now but off the critical path; blades and plate don't gate the V1 bring-up.
- **Firmware HomeKit/Wi-Fi spike.** Useful de-risk of the HAP stack on a bare devkit, but the
  V1 board gates everything the supervisor actually controls.
- **Order PCB semiconductors.** Fold into the V1 board order after KiCad capture freezes
  footprints.

## Learned Recently

- (none yet; this file starts with the bootstrap)
