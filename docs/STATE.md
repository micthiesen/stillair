# State

Last updated: **2026-09-30** (owner project status and procurement reconciliation, America/Vancouver).

## Now

- **Final tuning remains, then the aesthetic housing.** Michael's September 30 owner status
  supersedes interim installation as the primary pending step. Housing includes the integrated
  Hall sensor holder and sound dampening cover; the Hall harness is built and done. See
  [build.md](build.md), [housing.md](housing.md), and [harness context](electrical.md).
- **Retained V2 bench evidence:** the normal provisional firmware and saved
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
- **Reviewed orders are received except Mouser 40452969 and DigiKey 101388939.**
  V2 boards/loose parts and PCB-03 boards/stencil/display are owner-confirmed received.
  Optional e-ink is dropped; retain its design and received hardware. Entire DigiKey order
  cancellation and removal of all six Mouser spacers were requested by sent emails, with
  vendor confirmation pending. See [procurement reconciliation](../bom/README.md#owner-reconciliation-2026-09-30)
  and [PCB-03 decision](pcb-03.md#owner-decision-and-procurement-2026-09-30).
- **New boards use the validated tscircuit-to-KiCad workflow.** Existing released boards remain
  KiCad-authoritative. The PCB-03 fixture is an initial handoff with declared downstream cleanup
  and routing work, not a fabrication-ready replacement. See [pcb-workflow.md](pcb-workflow.md).

## Next

Final tuning, followed by the aesthetic housing with integrated Hall sensor holder and
sound dampening cover, is Michael's remaining-work sequence as of September 30. See
[build.md](build.md) and [housing.md](housing.md). The existing bench qualification limits
and historical evidence remain; no new test or commissioning result was recorded here.
Keep UniFi multicast enhancement enabled.

The V1 offer-rejection reply is drafted separately; await Michael's send confirmation
or a further JLCPCB response before recording a change in the complaint's status.

## Candidates Not Chosen

- **Repeat the impedance clarification:** answered by revised calculations and CAM metadata;
  revisit only if the relevant geometry, copper, or stack changes.
- **Repeat the POFV request:** Chian explicitly confirmed all three requested process details.
- **Return V1 for repair:** V1 is superseded and Michael does not want to return it.
- **Repeat interim installation as the primary next step:** superseded by the September 30
  remaining-work status.
- **Optional e-ink addition or further display purchases:** dropped by Michael; design and
  received boards/display retained, DigiKey cancellation awaiting vendor confirmation.

## Learned Recently

- September 30 owner project/receipt confirmations and sent vendor requests: [procurement](../bom/README.md#owner-reconciliation-2026-09-30).

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
