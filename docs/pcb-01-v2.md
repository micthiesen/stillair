# PCB-01 V2 contingency brief

Status: **not planned work**. If the current PCB-01 recovers, it is the finished one-off
controller and no V2 is required. Revisit this brief only if the board proves unrecoverable and
JLCPCB does not replace it, or if Michael later chooses to redesign it for fun.

This is an experience-based brief from the 2026-08-29 recovery discussion, not a completed design
review. Do not carry V1 parts or layout forward automatically. Start from the final working
as-built controller and its commissioning evidence.

## Direction

Make a smaller, simpler, easier-to-service one-off controller. Preserve the proven safety and
motor-control architecture, but remove options, duplicate interfaces, and components whose purpose
has been tested away. Bench and installed access matter more than minimum possible board area.

## Service and probing

- Prefer one clearly labelled row of large plated through-holes along an accessible board edge for
  important test and service signals. A probe clip or temporary soldered lead must fit without
  landing on a tiny pad.
- Route a signal to its nearest edge instead when forcing everything into one row would create a
  genuine routing tangle.
- Candidate signals from V1 commissioning are 3V3, AGND, AVDD, DVDD, FG, SOX, UART TX, and UART RX.
  Finalize the list from actual use before layout.
- Put readable signal names and orientation on the silkscreen. Preserve physical clearance for
  clips and hand soldering.
- Delete J8. Replace any signal it uniquely provided with the accessible edge points above.

## Programming and recovery

- Delete native USB-C, VBUS sensing, and USB-only support circuitry if the J7 UART path proves it
  can flash firmware and carry the complete runtime tuning console.
- Replace the tiny programming footprint with an accessible, keyed edge connector or large
  through-hole interface for TX, RX, GND, BOOT, and EN. Do not put board 3V3 on the service cable.
- Add automatic BOOT/RESET control using proper RTS and DTR circuitry.
- Retain normally-open physical BOOT and RESET controls as a manual fallback.
- Prefer an ESP module/package whose joints can be visually inspected and reworked, if a compatible
  choice exists without compromising the required radio layout.

## Simplification and assembly

- Delete the unused alternate capacitor footprints.
- Delete the small local fuse footprint that V1 bridges; source protection now lives at the power
  brick.
- Select a C34 that JLCPCB can assemble. C34 was the only remaining hand-installed capacitor that
  proved unnecessarily fiddly; the other intentional hand soldering is acceptable.
- Review every remaining component against the final commissioning record. Classify it as
  required, proven redundant, unused option, or service friction. Remove only items supported by
  that evidence.
- Shrink the board after the deletions, without sacrificing connector access, probe clearance,
  useful silkscreen, or comfortable hand soldering.

## Keep

- The independent overspeed chain, permission latch, watchdog, fault handling, and other released
  safety protections.
- MCF telemetry and the diagnostic signals that commissioning actually used.
- Recovery access independent of the primary runtime interface.
- Test access in general. V1's test points and J7 are what kept an apparent USB failure from making
  the controller immediately unrecoverable.

## Before any V2 schematic work

1. Finish V1 recovery and final tuning so the evidence set is complete.
2. Audit the as-built BOM using the four classifications above.
3. Freeze the exact edge-access signal list and connector arrangement.
4. Source the JLCPCB-assemblable C34 and any inspectable ESP alternative.
5. Recalculate the board outline only after the retained circuit is known.

V2 is not a productionization exercise and does not need to preserve the V1 outline or mounting
holes unless the eventual physical installation makes that useful.
