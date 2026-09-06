# Stillair overview

A quiet, low-profile 44-inch direct-drive ceiling fan for gentle overnight air mixing, with
local-only Apple Home control (Matter over Wi-Fi) and a minimal wood-and-white ceiling
presence. This repo is the
canonical source for the whole project: planning docs, BOM, firmware, CAD drawings,
authoritative tscircuit PCB source, and downstream KiCad boards. The full 3D model lives in
OnShape; everything else lives here.

## Key numbers

| Parameter | Value |
|---|---|
| Maximum rotor diameter | 44 in (1117.6 mm); 42 in fallback |
| Power bus | 24 V low-voltage, certified external supply |
| Target operating range | 35–170 RPM (minimum released only after qualification) |
| MCF driver speed limit | 180 RPM |
| Independent analog trip | 200 RPM nominal |
| Total ceiling drop | ≤10 in (254 mm absolute envelope) |
| Wall clearance | 5.5 in per side at 44 in diameter |
| Ceiling-to-blade gap | 8.0–8.2 in to nearest blade surface |
| Blades | Three symmetric 9 mm birch, 12° nominal pitch |
| Room | 55 in wide, 96 in ceiling, mattress top at 22 in; Vancouver, BC concrete condo |

## Architecture

Direct drive, low voltage, simple structure:

- **Motor**: CubeMars GL100 KV10 low-cogging gimbal motor (24 V, 20 pole pairs). Its KV10
  winding reaches the target speed with low phase current, giving the controller an easy
  low-speed operating point.
- **Drive**: TI MCF8316D sensorless FOC driver with integrated FETs, on a custom 78 × 58 mm
  four-layer controller PCB. The V1 board doubles as the development board (no TI evaluation
  module needed). V2 is only a contingency or optional later redesign; it may be smaller and does
  not inherit the V1 outline automatically. See [pcb-01-v2.md](pcb-01-v2.md).
- **Supervisor**: ESP32-C6-MINI-1-H4 running Matter over Wi-Fi (rs-matter, pure Rust), used
  from Apple Home. It configures the MCF over I²C and commands speed/direction; it never
  switches motor phases.
- **Power**: Mean Well GST60A24-P1J 24 V / 60 W certified supply, wall-side 3 A fuse and
  physical cutoff. Only low voltage crosses the ceiling.
- **Safety**: independent one-pulse Hall speed sensor → LM2907 → TLV1701 analog 200 RPM trip,
  hardware watchdog, and a permission latch that firmware can clear but not force. Mechanical
  backstops: a non-contact central rotor catcher and a separate rated whole-assembly tether.
- **Structure**: compact stainless ceiling plate, three aluminum standoffs, aluminum motor
  carrier and rotor hub, printed BP-100 blades, and a two-motion printed
  [housing](housing.md) with separate stationary and rotating sections.

## Design gates (dependency order)

1. **Motor system** (selected): GL100 KV10, MCF8316D FOC, 24 V / 60 W supply.
2. **Rotor geometry** (baseline set): 44 in, three birch blades, 12° nominal, 35–170 RPM target.
3. **Custom mechanics** (ready for CAD): dimensioned plan, elevation, section, hole, and
   tolerance views in [parts.md](parts.md).
4. **Build release** (qualification): V1 PCB, motor tuning, overspeed trip, bearings, and
   rotor proof. See [build.md](build.md).

## Scope

The design dossier (now these docs) defines the fan: dimensioned mechanical views, part
interfaces, materials, loads, exact standard components, a circuit-level PCB handoff,
placement zones, controller behavior, sources, and acceptance tests. What gets created from
it:

- Final 3D models in **OnShape** (not in this repo).
- Tscircuit schematic, board specification, and placement source in [`pcb/`](../pcb/), with KiCad
  owning downstream routing and production-only features.
- Firmware in [`firmware/`](../firmware/) (Rust, `no_std`, ESP32-C6).
- CNC/laser files for fabricated parts in [`cad/`](../cad/).

Slab verification and the local installation-approval path are site-specific execution work.

## Document map

- [decisions.md](decisions.md) — decision register: locked baseline, release gates, accepted deviations
- [mechanical.md](mechanical.md) — envelope, vertical stack, rotor geometry, retention
- [parts.md](parts.md) — dimensioned per-part specifications (the CAD handoff)
- [electrical.md](electrical.md) — PCB V1/V2 circuit and layout handoff
- [pcb-workflow.md](pcb-workflow.md): tscircuit source authority, KiCad handoff, and ECO rules
- [controls.md](controls.md) — motor-control contract and required state behavior
- [home-automation.md](home-automation.md) — provisional presence, comfort, and vacation behavior
- [observability.md](observability.md) — measurement authority, J8/scope hookups, synchronized evidence
- [probing.md](probing.md) — PCB-01 orientation, human test-point locations, connector pin views, and probe workflow
- [pcb-01-v2.md](pcb-01-v2.md) — conditional experience-based simplification and serviceability brief
- [motor-contingency.md](motor-contingency.md) — motor rejection criteria and least-disruption fallback paths
- [build.md](build.md) — build sequence, procurement gates, commissioning
- [integration.md](integration.md) — dependency spine, parallel tracks, and energy-sized next work
- [install.md](install.md) — anchors, slab verification, Vancouver approval path
- [../bom/bom.csv](../bom/bom.csv) — BOM with purchase tracking
- [../testing/test-matrix.csv](../testing/test-matrix.csv) — commissioning matrix with sign-off fields
