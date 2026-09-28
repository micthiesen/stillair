# State

Last updated: **2026-09-27** (V2 Home pairing and final bench validation complete).

## Now

- **PCB-01 V2 is ready to connect for interim use.** The normal provisional firmware and saved
  loaded MCF image are installed and verified. Final bench state is Off, no fault, zero drive
  output. Native USB, flashing, console access, and EEPROM apply/readback passed with the motor
  disconnected. Scope, exact image hash, and evidence are in the
  [bench receipt](../testing/pcb-01-v2-bench-2026-09-27.md).
- **Apple Home pairing succeeded and survived a board-only reset.** Michael confirmed the add
  and exercised Home controls after the reset. Both Home fabrics remain stored. UniFi multicast
  enhancement on SyNet-2G is the retained workaround for the observed incoming group-traffic
  failure; the normal group-key interval is restored. Network validation continued past the
  AP's one-hour interval and passed fresh ARP/NDP after the reset. The internal AP/C6 cause
  remains unproven. See [controls.md](controls.md#matter-implementation-notes-2026-07-27-from-building-it) and the
  [complete validation receipt](../testing/pcb-01-v2-bench-2026-09-27.md).
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

Michael will connect/install V2 using the saved provisional configuration and existing Home
pairing. Bench flashing and the requested final checks are complete; installation is the
remaining part of his selected plan. Keep UniFi multicast enhancement enabled. Follow his
explicit scope: no additional intermediate motor tests; final loaded tuning remains deferred
until requested or a problem is reported. See the
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

- V2 group-traffic workaround, Home pairing/control, restart persistence, final stopped state,
  and qualification limits: [bench receipt](../testing/pcb-01-v2-bench-2026-09-27.md) and
  [test matrix](../testing/test-matrix.csv).
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
