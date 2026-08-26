# Housing specification

Functional specification for the final cosmetic housing. Michael owns its aesthetic design,
surface language, proportions, seams, colors, and detailed CAD. This document fixes only the
interfaces needed for acoustics, cooling, sensing, service, retention, and moving clearances.

## Architecture

The housing is two mechanically separate assemblies with no contact across their running gap:

1. **Stationary upper enclosure:** spans from the MP-100 ceiling plate to the MC-100 stationary
   motor-carrier region. It encloses PCB-01, the standoffs, wiring, and the stationary motor mount.
   It provides the final stationary Hall-sensor mount.
2. **Rotating lower cover:** securely fixed to the RH-100/rotor assembly and rotating with the
   hub and GL100 outer rotor. It covers the rotor hub and the main rotating motor shell while
   preserving access and clearance for the catcher, nut, cotter, and spindle end.

The rotating hub continues to carry the tach magnet. The Hall sensor remains stationary so the
magnet crosses it once per revolution. Housing geometry may integrate both features, but may not
turn the sensor and magnet into one rigidly rotating assembly.

The aesthetic transition between the two sections may visually read as one form. The physical
interface remains an open, non-contact running gap sized from the realized runout and stack
tolerances.

## Acoustic intent

- The final acoustic configuration includes the owner-selected 2 mm butyl/film automotive damping
  panels on the motor and inside the stationary upper housing. Install them after the exposed
  controller tune is frozen; they are a passive improvement, not part of finding that tune.
- Attenuate airborne motor and controller tones after electrical tuning is complete.
- Keep the stationary and rotating covers stiff enough that neither becomes an obvious resonant
  sounding board.
- Avoid a direct acoustic sightline through any optional opening where the form permits a hidden
  or baffled path instead.
- Do not add ventilation openings preemptively. Ordinary seams, service gaps, and the cable entry
  are acceptable, but acoustic closure is the starting configuration.
- Keep the independently supported close microphone fixed outside the future housing envelope from
  the exposed finalist through the damped final-assembly capture. Compare at identical speed, load,
  microphone position, and gain. Michael's direct listening from bed is the user-facing judgment;
  no separate bed-position microphone recording is required.

## Thermal design

The primary motor heat path is conductive rather than ventilation-dependent:

`GL100 stator -> stationary motor face -> MC-100 -> three aluminum ST-100 standoffs -> MP-100 -> ceiling`

The large aluminum carrier and three solid Ø16 mm standoffs already provide the intended
thermal bridge. MP-100 spreads that heat and couples it into the ceiling/slab while its exposed
underside exchanges heat with the stationary enclosure air. No additional rods, internal
radiators, heat pipes, or mandatory free-vent area are part of the baseline.

PCB-01 heat reaches the structure through internal convection and radiation plus its bracket and
mounting interfaces. Keep reasonable free air volume around the board and do not pack the upper
cavity with thermal or acoustic insulation.

Thermal adequacy is decided with the complete final housing installed during `DRV-05`: eight hours
at 170 RPM, motor below 70 C and PCB below 85 C. If that test fails, respond in this order:

1. Confirm sensor placement and eliminate a mechanical rub or tuning loss.
2. Improve stationary conduction into MC-100 or MP-100.
3. Add the minimum concealed high/low baffled vent area demonstrated necessary by a repeated test.

Do not vent the rotating cover unless measurement identifies a separate rotating-volume thermal
problem.

## Temperature observation

The GL100 has no documented built-in temperature output. PCB-01 provides J4 `TEMP_SENSE`, a 10 kOhm
pull-up divider to GPIO6 for the purchased Vishay `NTCALUG01T103G501` ring-lug NTC. Mount the NTC on
a stationary GL100 surface or the immediately adjacent MC-100 motor-mount region, with the final
location recorded so later tests remain comparable. It may not attach to the rotating shell.

The NTC input is electrically complete but firmware acquisition remains `TODO(temp-sense)`, so it
does not currently appear in console telemetry. Until that is implemented, read the NTC with an
external meter/logger or use an independent attached temperature logger for `DRV-05`.

PCB-01 has no dedicated numeric board-temperature sensor. The MCF8316D reports internal
overtemperature warning/shutdown states, and firmware treats either as a stop, but those threshold
bits are protection rather than a qualification thermometer. Attach an independent thermocouple or
temperature probe at the MCF/board thermal region for the 85 C PCB measurement.

## Mechanical and service interfaces

- Preserve at least 8.0 mm housing-to-rotating-hub axial clearance where the stationary housing
  passes above the hub, and at least 2.0 mm from other stationary brackets to rotating parts except
  for the qualified Hall gap.
- Derive the stationary-to-rotating cosmetic gap from measured runout and the final printed-part
  tolerances, not nominal CAD alone.
- Preserve the catcher disk, castellated nut, cotter, spindle-end, blade, Hall, cable, and hand-turn
  inspection clearances.
- Secure the rotating cover positively to the rotating assembly and include it in the final balance,
  runout, hand-rotation, and full-speed observation.
- Retain service access to PCB-01, connectors, cutoff/programming paths, and the fixed cable entry
  without loading the housing with cable strain.
- Keep the ESP32-C6 antenna behind nonmetallic housing with at least 15 mm spatial clearance from
  metal.
- Printed material, attachment, and any secondary retention are selected with the final CAD. The
  functional result must remain secure through the released 170 RPM range and after repeated
  service removal.
