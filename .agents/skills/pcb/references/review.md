# PCB review gates

## Source review before handoff

- Requirements coverage and safety invariants.
- Datasheet-backed pin maps and intentional unused pins.
- Exact footprint identity, pad-number set, MPN, value, and supplier metadata.
- Net endpoint parity with the written electrical contract.
- Board dimensions, layer/fabrication spec, holes, keepouts, connector directions, and placement.
- Readable schematic and useful PCB placement renders.
- Complete downstream augmentation declaration.

## Handoff parity review

- Source manifest and staged KiCad seed agree in every tscircuit-owned domain.
- Coordinate and rotation transform is tested with asymmetric footprints and connectors.
- KiCad parses the project; ERC and pre-route DRC results are understood.
- No existing production board was overwritten.
- The accepted lock records source/tool fingerprints and stable identities.

## Routed KiCad review

- No source-owned drift from the accepted tscircuit manifest.
- Routes, vias, zones, stackup/rules, mask/paste, special processes, and silkscreen satisfy every
  augmentation item.
- ERC and DRC are clean except exact, documented, narrow waivers.
- Unconnected count is zero and filled zones are current.
- Front/back, copper, drill, and fabrication renders were inspected.
- BOM/CPL and fabrication package match the saved board and current order contract.

For safety-critical or production boards, use independent reviewers for electrical parity,
placement/mechanical constraints, handoff preservation, and fabrication readiness. Review findings
must be reproduced against the actual artifacts before changing the design.
