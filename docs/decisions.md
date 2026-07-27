# Decision register

What is fixed, and what still needs evidence. The system architecture is selected; the
remaining items are physical qualification gates, not unresolved aesthetic or product choices.

## Locked baseline

The design to take into CAD. All items below are **selected**.

| Area | Decision | Note |
|---|---|---|
| Mounting | Compact metal plate, two primary anchors, separate tether anchor | Exact anchors remain conditional on the verified slab and load calculation. |
| Structure | Metal ceiling structure and hub; qualified printed blade adapters | A non-contact central capture path retains the rotor after motor-bearing retention failure. |
| Rotor | 44-inch maximum, three symmetric birch blades, 12° nominal pitch | 42 inches is the fallback if wall-effect testing or handling makes 44 undesirable. |
| Drive | CubeMars GL100 KV10 with TI MCF8316D sensorless FOC | The low-KV motor is naturally matched to slow direct drive. A custom four-layer V1 board replaces the evaluation module. |
| Power | Mean Well GST60A24-P1J, 24 V / 60 W, 3 A source fuse | Only low voltage crosses the ceiling; a physical switch opens the positive conductor. |
| Control | ESP32-C6, local HomeKit over Wi-Fi, continuous speed and reverse | Network loss preserves operation; ESP failure disables the bridge; power restoration remains off. |
| Duty | 35–170 RPM target range, 180 RPM driver limit, 200 RPM analog trip | Release the actual minimum only after repeatable startup and acoustic qualification. The analog path is an independent runaway backstop, not precision regulation. |
| Appearance | Minimal light wood or white blades with consistent stainless hardware | No light; the white printed surface conduit is outside the fan design. |

## Release gates (before permanent installation)

Six explicit gates. A failed gate has a named fallback; it must not be converted into an
undocumented assumption.

1. **Motor bearings** — CubeMars confirms the vertical axial-load basis, or the motor is
   redesigned around an independently rated bearing path.
2. **Sensorless control** — the GL100 and representative final rotor pass starts, low-speed
   acoustics, overnight thermal, reversal, and fault tests on PCB V1.
3. **Permanent PCB** — V1 proves protection, connectors, power conversion, watchdog, analog
   overspeed, bus-voltage behavior, thermals, RF, and the exact MCF settings before V2 release.
4. **Concrete interface** — the slab, existing hole, hidden services, anchor geometry,
   installation torque, and separate tether anchor are physically verified.
5. **Rotor qualification** — blades, adapters, hub, central capture, balance, proof load,
   proof speed, controlled imbalance behavior, and dynamic catcher/tether tests are signed off.
6. **Installation approval** — any required permit, accepted certification mark, or field
   evaluation for a permanent custom appliance is resolved locally. *(Open gate.)*

## Accepted deviations

Constraints that cannot all be optimized.

- **Wall clearance: 5.5 inches per side at 44-inch diameter.** Well below common 18-inch
  guidance. The room cannot fit a useful fan that meets the guidance, so 44 inches is a
  deliberate experimental maximum and 42 inches remains the fallback.
- **Ceiling gap: 8.0–8.2 inches to the nearest blade surface.** The full 0.2-diameter
  heuristic would exceed the desired total drop once blade pitch is included. The selected gap
  spends nearly all of the permitted 10-inch envelope on airflow.
- **Certification: a custom assembly is not certified by using a certified power brick.**
  Component approvals reduce risk but do not create an accepted mark for the complete
  appliance. Confirm the local permanent-installation path before ceiling release (gate 6).

## Deliverable boundaries

The docs define dimensioned mechanical views, part interfaces, materials, loads, exact
standard components, a circuit-level PCB handoff, placement zones, controller behavior,
sources, and acceptance tests. Michael creates the final OnShape models, captures and reviews
the KiCad schematic/layout in `pcb/`, and implements firmware in `firmware/`. Slab
verification and local installation approval remain site-specific execution work.
