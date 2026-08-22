# Home automation (provisional)

> **Status:** behavior draft only. The automation host, sensors, and final thresholds are TBD.
> Automatic starts are desired but not yet released by this document. They remain gated on final
> loaded startup, acoustic, and endurance qualification.

Defines how Stillair should participate in household automation without turning a quiet,
low-power appliance into something that cycles whenever presence detection flickers. The first
useful first automation is delayed shutdown after a real absence. Once the automatic-start gate
passes, the intended steady state is a 1% baseline whenever the home is occupied, with higher
speeds selected only when useful. Manual control remains primary.

## Goals

- Preserve long, comfortable occupied runs instead of optimizing away a few watt-hours.
- Turn the fan off when the home is genuinely empty for an extended period.
- Release automatic arrival starts only after explicit enablement and qualification; never
  automate a direction change.
- Keep presence, temperature, and automation failures from causing rapid cycling.
- Use only the normal Matter control path. Automation never bypasses firmware limits, fault
  handling, stopped-direction checks, or the physical cutoff.
- Keep daily operation local. Cloud availability must not be required to stop or control the fan.

## Platform boundary

Apple Home is preferred if it can express the chosen delays, hysteresis, household occupancy, and
manual-override behavior reliably. A local automation engine such as Home Assistant is acceptable
if Apple Home cannot. Platform selection must not change the behavior in this document.

The fan exposes ordinary Matter On/Off, continuous percentage, and airflow direction. Daily
automation commands those attributes only. Kasa or the physical low-voltage cutoff is a separate
power boundary, not a substitute for normal Off.

## Provisional operating presets

The current 1--100% slider maps linearly across the released 50--170 RPM range.

| Preset | Command | Approx. speed | Intended use |
|---|---:|---:|---|
| Sleep | Forward 1% | 50 RPM | Nearly inaudible overnight mixing |
| Comfort | Forward 20% | 73 RPM | Warm-weather occupied boost |
| Boost | Forward 50% | 109 RPM | Short initial cool-down, then return to Comfort |
| Off | Off | 0 RPM commanded | Confirmed absence, vacation, or manual override |
| Winter mix | Reverse, speed TBD | TBD | Manual experiment only; not an automatic preset yet |

These are named intentions, not firmware constants. Changing the released minimum changes their
physical RPM and requires this table to be revisited.

## Release A: delayed away shutdown

This is the recommended first automation and may be adopted before automatic starts.

1. Define `home occupied` as at least one household member reliably present. A missing or stale
   presence source is **unknown**, not away.
2. When all household members have been continuously away for **2 hours**, issue one Matter Off
   command.
3. Confirm that the fan reports Off. If it is unreachable or does not confirm, notify once; do not
   repeatedly command, power-cycle, or attempt to clear a fault.
4. Before the automatic-start gate passes, arrival cancels a pending away timer but does **not**
   start the fan.
5. An absence shorter than 2 hours changes nothing. Errands therefore leave a low-speed run alone.

The two-hour delay is provisional. Its purpose is to debounce both short errands and unreliable
presence transitions, not to save a meaningful amount of energy: the released floor measured
about 1.7 W.

## Manual control and overrides

- A person may set any released forward speed or turn the fan off at any time.
- Release A never overwrites a manual speed while the home remains occupied.
- Provide a visible `Fan automation enabled` toggle if the chosen platform supports a helper or
  virtual switch. Disabling it cancels pending actions.
- Scenes should set direction and percentage explicitly rather than relying on an old retained
  target. Off may retain the last setting for manual resume, but an automation should state its
  intent completely.
- Do not create an automation that reacts to every On, Off, percentage, or presence event by
  writing another value back. Feedback loops must be impossible by construction.
- After automatic arrival starts are released, a manual Off while occupied suppresses all
  automatic starts and temperature changes until the next genuine all-away then arrival cycle, or
  until the person explicitly re-enables automatic operation.

## Vacation behavior

Vacation shutdown is deliberate, not inferred solely from geofencing:

1. Enable a visible Vacation mode (or disable fan automation), then cancel pending automation.
2. Manually command the fan Off and confirm stopped.
3. Optionally switch the Kasa-controlled supply off for the trip. Power removal is additional
   isolation, not the everyday stopping method.
4. Restoring power must leave Stillair Off, as required by the firmware contract.
5. The arrival that ends a vacation does not automatically start the fan. After disabling Vacation
   mode, start it manually; later ordinary away then arrival cycles may use Release B.

The delayed-away automation remains a useful backstop, but it is not the vacation checklist's only
action.

## Release B: occupied baseline

Consider only after final startup refinement and long-duration loaded qualification. Once released,
the automation should make low-speed circulation the occupied default:

- Required input: reliable household occupancy.
- After the home changes from confirmed all-away to continuously occupied for a provisional **10
  minutes**, set Forward Sleep (1%).
- Do not start from an unknown occupancy state. A stale presence source must not look like an
  arrival.
- Do not restart after a fault, failed command, device reboot, or power restoration. A person must
  inspect the state and issue the next command.
- Rate-limit automated starts to at most one per 30 minutes. Longer minimum-on/off times may be
  selected after observing the room.
- A manual percentage change becomes the occupied setting and is not pulled back to Sleep merely
  because the arrival rule exists. A manual Off applies the override above.
- Power restoration while somebody is already home is not an arrival and must leave the fan Off.
  The next start is manual or follows a later genuine away then arrival transition.

## Release C: adaptive comfort boost

Consider after Release B has proven that arrival detection and manual overrides are reliable.
Provisional behavior:

- Required inputs: reliable household occupancy and a room-temperature sensor at occupied height.
- If occupied and temperature remains at or above **25.0 °C for 10 minutes**, set Forward Comfort
  (20%).
- If temperature remains at or below **23.5 °C for 20 minutes**, return to Forward Sleep (1%), not
  Off.
- Do not act from an unknown occupancy or temperature state.
- A manual percentage change suspends temperature adaptation for a provisional **4 hours** or until
  the next confirmed all-away transition. If the platform cannot distinguish manual from automated
  writes reliably, keep Release B but do not release adaptive boosting.

The fan should complement AC rather than follow compressor state. A person may choose a warmer AC
setpoint once comfort is proven, but this specification does not automatically alter HVAC settings.

## Boost scene

Boost is a manual convenience, not a thermostat response:

1. Set forward 50% for a provisional 15 minutes.
2. Return to forward 20% if the home is still occupied and automation remains enabled.
3. If the user changes speed or turns the fan off during Boost, cancel the scheduled return.

The 3 RPM/s firmware ramp already makes the transition gradual. The scene must not emulate a ramp
with a burst of percentage writes.

## Winter and reverse

Reverse is retained as an experiment for destratification without direct downflow. Do not automate
it from season or outdoor temperature alone. The cambered blades, close ceiling gap, and close wall
clearance all make reverse less predictable than forward.

A future winter rule requires evidence from two indoor sensors: one near occupied height and one
near the ceiling. Only consider automatic reverse if a repeatable temperature difference shows
useful stratification and a manual speed trial improves it without objectionable noise or draft.
Direction changes must always use the firmware's normal stop, verified-still, and restart path.

## Failure behavior

| Condition | Automation response |
|---|---|
| Presence unknown or stale | Hold; never infer permission to start |
| Temperature unavailable | Hold the occupied baseline or manual setting; suppress adaptive boost |
| Matter controller or Wi-Fi unavailable | Do not assume the fan stopped; notify once |
| Fan reports a fault | Do not clear or restart automatically |
| Power restored | Leave Off; restoration is not an arrival and may not immediately restart it |
| Manual physical or Kasa cutoff is Off | Treat as an intentional override |
| Repeated trigger or state flapping | Coalesce into one pending action; never cycle the fan |

The firmware intentionally continues its last local speed through network loss. An automation
engine therefore cannot claim an away shutdown succeeded until the device confirms Off.

## Acceptance checks

Before enabling Release A:

- A simulated absence shorter than 2 hours leaves a running fan unchanged.
- Two hours continuously away commands Off once and confirms the reported state.
- Presence flapping cancels or restarts the timer without cycling the fan.
- Before Release B, returning home leaves the fan Off.
- An unreachable fan produces one notification and no retry storm or power cycle.
- Disabling automation cancels pending actions and leaves manual control untouched.

Before enabling Release B, additionally verify:

- Startup and loaded endurance gates are complete.
- A real arrival starts Forward Sleep once after the debounce, while presence flapping does not.
- Manual speed changes remain in force and manual Off suppresses further occupied automation.
- Missing presence data, reboot, network recovery, power restoration, and fault recovery never
  cause an automatic start.

Before enabling Release C, additionally verify:

- Temperature hysteresis prevents cycling near either threshold.
- Cooling returns Comfort to Sleep rather than Off.
- Manual speed changes suppress adaptation for the chosen override interval.
- Boost cancellation and return-to-Comfort behavior work from Apple Home and any alternate control
  surface in use.

## Decisions still open

- Apple Home alone versus a local automation engine.
- Presence source and the exact definition of household occupancy.
- Room and optional ceiling temperature sensors.
- Final away and arrival delays, temperature thresholds, override duration, and Boost duration.
- The exact qualification evidence required before enabling automatic arrival starts.
- Whether reverse produces useful winter destratification in this room.
