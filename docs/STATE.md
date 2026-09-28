# State

Last updated: **2026-09-27** (V2 ready; AP fault resolved; automated Matter verified).

## Now

- **One PCB-01 V2 is assembled and bench-flashed.** Native USB, the runtime console, MCF
  communication, and persistent configuration apply/readback succeeded with the motor disconnected.
  The board holds the existing loaded image and reports `idle_off`, no fault, `config=verified`.
  See the [bench receipt](../testing/pcb-01-v2-bench-2026-09-27.md) for exact evidence and limits.
- **The pairing network blocker is resolved.** The U7 Pro was failing to deliver inbound
  broadcast/multicast traffic on SyNet-2G, affecting V2 and other clients. One AP restart restored
  delivery without changing its settings. Automated Matter commissioning then completed over
  IPv6, and a normal-release reboot restored its fabric/network and passed fresh secure reads.
  The test fabric and Wi-Fi seed were removed; the final release advertises `Stillair`, identifies
  as `PCB-01 V2`, and is back at `idle_off`, no fault, `config=verified`. Apple Home itself has not
  been retried since the fix because Michael was away. The confirmed RSSI initialization guard
  remains; experimental sequential mode and credential-seeded images are not installed.
  See the [complete receipt and evidence](../testing/pcb-01-v2-bench-2026-09-27.md).
  Michael chose interim use with no additional intermediate motor tests; final tuning stays deferred.
- **V1's USB complaint remains unresolved.** JLCPCB refused credit against an existing order
  and proposed a USD 30 future coupon or free expedite service for one order. Michael asked for
  both current orders to be expedited; Paul declined that request. Michael now wants to reject
  the offer and state that the experience will affect future purchasing decisions.
  The [reply history and rejection draft](jlcpcb-v1-credit-request.md) are retained. The rejection
  is unsent; no coupon or expedite service is confirmed. Complaint evidence is in
  [bom/README.md](../bom/README.md).
- **PCB-03 boards and stencil have shipped; parts and display remain pending.** Shipping and the
  accepted paste-layer addition are in [PCB-03 ORDERING.md](../pcb/pcb-03/fab/ORDERING.md).
  DigiKey 101388939 includes the backordered SC18IS606PWJ; AliExpress display order is
  8213753300045333. Retain the first-article gates in [pcb-03.md](pcb-03.md).
- **New boards use the validated tscircuit-to-KiCad workflow.** Existing released boards remain
  KiCad-authoritative. The PCB-03 fixture is an initial handoff with declared downstream cleanup
  and routing work, not a fabrication-ready replacement. See [pcb-workflow.md](pcb-workflow.md).

## Next

Michael retries adding **Stillair** in Apple Home with **3497-0112-332**, then installs it with
its saved loaded configuration. The shared network failure is fixed and automated commissioning
passed; the remaining confirmation requires his Home app. If its commissioning window has expired,
reopen it with an ESP reset over USB. Follow his explicit scope: no additional intermediate motor
tests; respond to reported problems and resume final tuning when requested. See the
[bench receipt](../testing/pcb-01-v2-bench-2026-09-27.md).

The V1 offer-rejection reply is drafted separately; await Michael's send confirmation
or a further JLCPCB response before recording a change in the complaint's status.

## Candidates Not Chosen

- **Repeat the impedance clarification:** answered by revised calculations and CAM metadata;
  revisit only if the relevant geometry, copper, or stack changes.
- **Repeat the POFV request:** Chian explicitly confirmed all three requested process details.
- **Return V1 for repair:** V1 is superseded and Michael does not want to return it.
- **Additional intermediate motor testing or final tuning now:** deferred by Michael; the selected
  scope is bench flash/configuration followed by installation for interim use.

## Learned Recently

- V2 AP diagnosis, successful Matter commissioning, final release, and untested scope:
  [bench receipt](../testing/pcb-01-v2-bench-2026-09-27.md).
- V2 map selection: [probing.md](probing.md). Rustup PATH and native USB reset behavior:
  [controls.md](controls.md#commissioning-interface-and-build-policy).
- V1 complaint evidence and supplier offers: [bom/README.md](../bom/README.md).
- Credit refusal, one-order expedite limit, additional order reference, and rejection draft:
  [correspondence](jlcpcb-v1-credit-request.md).
- V2 production and qualification checklist: [PCB-01 V2 ORDERING.md](../pcb/pcb-01-v2/fab/ORDERING.md).
- Shared native transactions, guarded schematic fields, preparation audits, and lifecycle helpers:
  [PCB tools](../pcb/tools/README.md); project adoption limits in [pcb-workflow.md](pcb-workflow.md).
- CAM and placement evidence: [production review](../pcb/pcb-01-v2/fab/production-review/README.md)
  and [placement review](../pcb/pcb-01-v2/fab/placement-review/README.md).
- Orders, backorders, and inventory: [bom.csv](../bom/bom.csv) and [bom/README.md](../bom/README.md).
