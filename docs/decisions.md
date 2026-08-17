# Decision register

What is fixed, and what still needs evidence. The system architecture is selected; the
remaining items are physical qualification gates, not unresolved aesthetic or product choices.

## Locked baseline

The design to take into CAD. All items below are **selected**.

| Area | Decision | Note |
|---|---|---|
| Mounting | Compact metal plate, two primary anchors, separate tether anchor | MP-100 installation and tether proof accepted complete by owner report 2026-08-17. Remaining installation is owner-managed and not an active project gate. |
| Structure | Metal ceiling structure and hub; blades bolt directly to the hub (adapters deleted 2026-07-28, BP-100 v3) | A non-contact central capture path retains the rotor after motor-bearing retention failure. |
| Rotor | 44-inch maximum, three printed BP-100 v3 cambered-airfoil blades with CF-rod spars, baked-in twist, and integrated bolt-on roots | Replaced the symmetric-birch/12°-adapter rotor 2026-07-27, root integrated 2026-07-28 ([blade-v2.md](blade-v2.md)); forward flow optimized, reverse degraded-but-functional by accepted trade. Birch BL-100 is the fallback. 42 inches remains the diameter fallback if wall-effect testing or handling makes 44 undesirable. |
| Drive | CubeMars GL100 KV10 with TI MCF8316D sensorless FOC | The low-KV motor is naturally matched to slow direct drive. A custom four-layer V1 board replaces the evaluation module. |
| Power | Mean Well GST60A24-P1J, 24 V / 60 W, 3 A source fuse | Only low voltage crosses the ceiling; a physical switch opens the positive conductor. |
| Control | ESP32-C6, local Matter over Wi-Fi (rs-matter, pure Rust), continuous speed and reverse, used from Apple Home | Replaces the original HomeKit/HAP plan (no maintained no_std HAP exists). Network loss preserves operation; ESP failure disables the bridge; power restoration remains off. |
| Duty | 35–170 RPM target range, 180 RPM driver limit, 200 RPM analog trip | Release the actual minimum after representative startup testing. The analog path is an independent runaway backstop, not precision regulation. |
| Appearance | Minimal light wood or white blades with consistent stainless hardware | No light; the white printed surface conduit is outside the fan design. |

## Why GL100 (vs GL80)

The KV10 winding is naturally matched to slow direct drive: it trades 383 g and 11.9 mm of
axial depth for a 2.9× higher torque constant than the GL80, reaching the target speed range
with far less phase current (less copper heating, easier low-speed operating point).

| Attribute | GL100 KV10 | GL80 KV30 | Advantage |
|---|---|---|---|
| Speed matching | KV10 · 223 RPM no-load at 24 V | KV30 · 450 RPM rated at 24 V | GL100 |
| Torque constant | 1.030 N·m/A | 0.356 N·m/A | GL100 |
| Est. current at 0.7–0.8 N·m load | 0.68–0.78 A + losses | 1.97–2.25 A + losses | GL100 |
| Mass | 698 g | 315 g | GL80 |
| Envelope | Ø106.8 × 34.2 mm | Ø87 × 22.3 mm | GL80 |

GL100 ratings: 3.0 N·m rated at 130 RPM, 7.7 N·m peak, 223 RPM no-load, 20 pole pairs,
Ø30 through-bore, 698 g, rotor inertia 2310 g·cm², IP45, −20 to 50 °C. Calculated operating
point: 0.68–0.78 A torque current and 12.5–14.2 W mechanical at 170 RPM; roughly 18–25 W
total input estimated (core/bearing losses unpublished). Do not confuse capability with
requirement: the controller caps current at 1.5 A and disables flux weakening, so peak motor
torque is not available in the installed fan.

## Active release gates

Three active gates remain. A failed gate has a named fallback; it must not be converted into
an undocumented assumption.

1. **Sensorless control** — the GL100 and representative final rotor pass representative
   starts, stable-speed operation, overnight thermal, reversal, and essential shutdown tests
   on PCB V1.
2. **Permanent PCB** — V1 proves protection, connectors, power conversion, watchdog, analog
   overspeed, bus-voltage behavior, thermals, RF, and the exact MCF settings before V2 release.
3. **Rotor qualification** — blades, root joints, hub, central capture, and catcher are
   accepted complete; balance/runout and guarded proof speed remain active.

Anchor selection and mounting sequence remain recorded in [install.md](install.md) as
reference. Michael owns installation and any local approval decisions; agents must not
surface them as work unless explicitly asked.

## Accepted deviations

Constraints that cannot all be optimized.

- **Wall clearance: 5.5 inches per side at 44-inch diameter.** Well below common 18-inch
  guidance. The room cannot fit a useful fan that meets the guidance, so 44 inches is a
  deliberate experimental maximum and 42 inches remains the fallback.
- **Ceiling gap: ~4.7 inches to the nearest blade surface (hugger regime; changed
  2026-07-27/28, was 8.0–8.2).** Open cabinet doors reach within ~160 mm of the ceiling and
  collided with the original blade plane — a hard constraint, so the rotor was raised
  ~99 mm (ST-100 138 → 62; adapter deleted, the v3 blade root bolts flush to the hub). At
  ~0.106 D the gap chokes the inflow annulus (~0.42 m² vs the 0.98 m² disk): expect roughly
  **15–25% less CFM at fixed RPM** and a corresponding CFM/W efficiency loss. Accepted
  because delivered airflow is recoverable with the 3× RPM headroom (60 → ~72 RPM restores
  flow at ~20 W total, tip speed still ~4 m/s) and a fan that strikes doors is worth 0% of
  its airflow. Secondary effect: the v3 proplet droops downward instead of raking up, so
  the tip stays out of the intake throat.
- **Certification: a custom assembly is not certified by using a certified power brick.**
  Component approvals reduce risk but do not create an accepted mark for the complete
  appliance. Michael owns any local approval decision; it is outside active project work.

## Deliverable boundaries

The docs define dimensioned mechanical views, part interfaces, materials, loads, exact
standard components, a circuit-level PCB handoff, placement zones, controller behavior,
sources, and acceptance tests. Michael creates the final OnShape models, captures and reviews
the KiCad schematic/layout in `pcb/`, and implements firmware in `firmware/`. Installation,
tether, catcher, slab verification, and local approval are owner-managed and outside the
active project plan.
