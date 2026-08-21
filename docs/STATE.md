# State

Fast-moving work state and chosen next step. Durable findings live in the linked design,
commissioning, BOM, and test documents.

Last updated: **2026-08-20** (ceiling assembly complete; installed checks and loaded commissioning next.)

## Now

- **The ceiling assembly is physically complete by owner report.** MP-100, ST-100, SP-100,
  MC-100, GL100, tether, RH-100, all three blades, BR-100/PCB-02, the Hall magnet and balance
  slugs, PCB-01, and the KD-100/castellated-nut/cotter catcher stack are installed. The permanent
  feed was verified at stable 24 V with correct polarity. Installation details and remaining
  evidence are in [install.md](install.md).
- **The stationary fastener stacks are recorded.** GL100-to-MC-100 uses four M4 × 12 screws,
  blue removable threadlocker, and an approximately 1.5 N·m hand target. MC-100-to-ST-100 uses
  three M6 × 20 A4-80 screws, genuine Nord-Lock pairs, no threadlocker, and a 5 N·m target.
  The exact blade-nut resolution after the A4 all-metal galling event still needs one owner
  sentence in [blade-v2.md](blade-v2.md) and [the BOM](../bom/bom.csv).
- **Installed power, Hall, and motor harnesses are connected but not released for loaded power.**
  Final evidence still needed: independent cable strain relief, installed continuity/polarity,
  1.5–4.0 mm Hall gap, at least 2 mm catcher and stationary clearances, connector seating, and
  unobstructed 360° hand rotation with no rubbing.
- **The unloaded motor, electronics, harnesses, and safety behavior are qualified.** The retained
  25 kHz `mcf_config::UNLOADED_IMAGE` completed both-direction operation through 170 RPM and a
  ten-minute 170 RPM endurance run. It remains the immutable A/B baseline; loaded tuning gets a
  separate candidate. Evidence is in
  [unloaded-tuning-2026-08-20.md](../testing/unloaded-tuning-2026-08-20.md).
- **The evidence path for loaded work is ready.** Existing Hall/FG, MCF telemetry, camera/audio,
  wall-power, and IR capture support safe loaded tuning. The optional OWON USB scope can add
  waveform evidence if available, but it is not a prerequisite.

## Next

Record the final blade fastener configuration, then perform the complete electrically dead
installed inspection from [install.md](install.md): measure Hall/catcher clearances, support every
cable independently of its connector, verify continuity and polarity, and hand-rotate the rotor
through 360° with no contact.

Once those checks pass, begin ceiling-mounted loaded commissioning at the lowest useful speed,
then run loaded MPET and bounded tuning through [integration.md](integration.md). Preserve the
unloaded image as the A/B baseline and do not write EEPROM until the loaded golden image is
reviewed.

## Candidates Not Chosen

- **Loaded tuning before installed inspection:** rejected. The completed mechanical stack still
  needs measured gaps, continuity, strain relief, and full hand-rotation evidence before power.
- **Loaded tuning on an improvised bench rig:** not chosen; the ceiling installation provides the
  final support, rotor load, cable lengths, ceiling interaction, and room acoustics.
- **EEPROM commit of the unloaded image:** rejected. Only the reviewed loaded golden image may
  populate persistent `IMAGE`.
- **USB oscilloscope as a blocker:** rejected. It is optional additional evidence.
- **Reopening accepted plate, anchor, tether, or catcher proof work:** rejected unless Michael
  explicitly requests it; the installed inspection checks condition and clearance, not proof basis.

## Learned Recently

- Ceiling hardware, wiring state, fastener targets, and installed check sequence:
  [install.md](install.md) and [parts.md](parts.md).
- Blade-joint geometry and the A4 all-metal prevailing-nut galling failure:
  [blade-v2.md](blade-v2.md) and [bom.csv](../bom/bom.csv).
- Retained unloaded tuning, acoustic interpretation, and endurance evidence:
  [unloaded-tuning-2026-08-20.md](../testing/unloaded-tuning-2026-08-20.md).
- Measurement authority and optional scope capture contract: [observability.md](observability.md).
