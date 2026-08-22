# Home automation (provisional)

> **Status:** behavior draft only. The automation host, sensors, and final thresholds are TBD.
> Automatic starts are not released by this document. They remain gated on final loaded startup,
> acoustic, and endurance qualification.

Defines how Stillair should participate in household automation without turning a quiet,
low-power appliance into something that cycles whenever presence detection flickers. The first
useful automation is delayed shutdown after a real absence. Manual control remains primary.

## Goals

- Preserve long, comfortable occupied runs instead of optimizing away a few watt-hours.
- Turn the fan off when the home is genuinely empty for an extended period.
- Never surprise an occupant with an automatic start or direction change.
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
| Comfort | Forward 20% | 73 RPM | Default warm-weather occupied setting |
| Boost | Forward 50% | 109 RPM | Short initial cool-down, then return to Comfort |
| Off | Off | 0 RPM commanded | Normal absence and winter default |
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
4. Arrival cancels a pending away timer but does **not** start the fan.
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

## Vacation behavior

Vacation shutdown is deliberate, not inferred solely from geofencing:

1. Manually command the fan Off and confirm stopped.
2. Optionally switch the Kasa-controlled supply off for the trip. Power removal is additional
   isolation, not the everyday stopping method.
3. Restoring power must leave Stillair Off, as required by the firmware contract.
4. Returning home does not automatically start it.

The delayed-away automation remains a useful backstop, but it is not the vacation checklist's only
action.

## Release B: occupied comfort automation

Consider only after final startup refinement and long-duration loaded qualification. Provisional
behavior, if released:

- Required inputs: reliable household occupancy and a room-temperature sensor at occupied height.
- If occupied and temperature remains at or above **25.0 °C for 10 minutes**, set Forward Comfort
  (20%).
- If temperature remains at or below **23.5 °C for 20 minutes**, command Off.
- Do not start from an unknown occupancy or temperature state.
- Do not restart after a fault, failed command, device reboot, or power restoration. A person must
  inspect the state and issue the next command.
- Rate-limit automated starts to at most one per 30 minutes. Longer minimum-on/off times may be
  selected after observing the room.
- A manual percentage change suspends temperature automation for a provisional **4 hours** or until
  the next confirmed all-away transition. If the platform cannot distinguish manual from automated
  writes reliably, do not release automatic starts.

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
| Temperature unavailable | Suppress temperature automation |
| Matter controller or Wi-Fi unavailable | Do not assume the fan stopped; notify once |
| Fan reports a fault | Do not clear or restart automatically |
| Power restored | Leave Off; no arrival or temperature rule may immediately restart it |
| Manual physical or Kasa cutoff is Off | Treat as an intentional override |
| Repeated trigger or state flapping | Coalesce into one pending action; never cycle the fan |

The firmware intentionally continues its last local speed through network loss. An automation
engine therefore cannot claim an away shutdown succeeded until the device confirms Off.

## Acceptance checks

Before enabling Release A:

- A simulated absence shorter than 2 hours leaves a running fan unchanged.
- Two hours continuously away commands Off once and confirms the reported state.
- Presence flapping cancels or restarts the timer without cycling the fan.
- Returning home leaves the fan Off.
- An unreachable fan produces one notification and no retry storm or power cycle.
- Disabling automation cancels pending actions and leaves manual control untouched.

Before enabling Release B, additionally verify:

- Startup and loaded endurance gates are complete.
- Temperature hysteresis prevents cycling near either threshold.
- Manual speed changes suppress automation for the chosen override interval.
- Missing sensor data, reboot, network recovery, and fault recovery never cause an automatic start.
- Boost cancellation and return-to-Comfort behavior work from Apple Home and any alternate control
  surface in use.

## Decisions still open

- Apple Home alone versus a local automation engine.
- Presence source and the exact definition of household occupancy.
- Room and optional ceiling temperature sensors.
- Final away delay, temperature thresholds, override duration, and Boost duration.
- Whether automatic starts provide enough value to release at all.
- Whether reverse produces useful winter destratification in this room.
