# State

Last updated: **2026-09-27** (V2 assembled, bench-flashed, loaded settings saved).

## Now

- **One PCB-01 V2 is assembled and bench-flashed.** Native USB, the runtime console, MCF
  communication, and persistent configuration apply/readback succeeded with the motor disconnected.
  The board holds the existing loaded image and reports `idle_off`, no fault, `config=verified`.
  See the [bench receipt](../testing/pcb-01-v2-bench-2026-09-27.md) for exact evidence and limits.
- **Apple Home pairing failed after Wi-Fi joined.** Attestation and NOC installation succeeded,
  but the final commissioning request did not arrive before timeout. Serial and Bonjour captures
  are collecting a requested retry; exact cause remains unresolved. See the
  [pairing follow-up](../testing/pcb-01-v2-bench-2026-09-27.md#apple-home-pairing-follow-up).
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

Diagnose the operational-network pairing timeout on the new V2, then Michael installs it with the
saved loaded configuration. Follow his explicit scope: no additional intermediate motor tests;
respond to reported problems and resume final tuning when requested. See the
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

- V2 bench evidence, persistent image, and untested scope:
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
