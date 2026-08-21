# State

Fast-moving work state and chosen next step. Durable findings live in the linked design,
commissioning, BOM, and test documents.

Last updated: **2026-08-20** (unloaded campaign wrapped; ceiling integration selected next.)

## Now

- **The permanent ceiling interface is complete.** MP-100, all three ST-100 standoffs, and
  SP-100 are installed. The primary anchors, tether, and catcher are owner-accepted complete
  and must not be reopened. Michael explicitly resumed project help for mounting the remaining
  fan assembly, electronics, and cables from below; the active sequence is in
  [install.md](install.md).
- **The ceiling 24 V feed is ready for integration.** Michael verified a stable 24 V at the
  ceiling plate with correct polarity on 2026-08-20. Keep it de-energized while assembling the
  stationary stack, rotor, electronics, and cable strain relief.
- **GL100 is mounted to MC-100.** The four M4 × 12 screws fit without bottoming and were
  installed on 2026-08-20 with blue removable threadlocker, using an approximately 1.5 N·m
  hand-torque target. The complete carrier/motor assembly was then mounted overhead with three
  M6 × 20 A4-80 screws, genuine glued Nord-Lock pairs, no threadlocker, and the selected 5 N·m
  target. The tether connection and rotor installation are next.
- **The rotor and installed electronics are physically in place.** Michael resolved the blade
  fastener installation and reports all blades installed; the exact resolution still needs to
  be recorded before loaded release because the A4 three-punch galling failure remains real.
  BR-100/PCB-02, the Hall magnet, both balance slugs, and PCB-01 are mounted, with 24 V, Hall,
  and motor harnesses connected. The central KD-100/castellated-nut/cotter stack is next. Keep
  power disconnected until catcher clearance, cable support, continuity, and hand rotation pass.
- **PCB-01, PCB-02, harnesses, firmware, and the restrained unloaded motor are qualified.**
  Board bring-up, Hall polarity and physical switching, MCF transport, permission/fault revoke,
  startup/handoff, 35–170 RPM in both directions, repeated stops, and normal coast-down passed.
- **The best unloaded configuration is permanently retained.** The exact table is
  `mcf_config::UNLOADED_IMAGE`; `PROVISIONAL_IMAGE` currently aliases it for volatile staging,
  while persistent `IMAGE` remains empty. Loaded tuning must add a separate candidate rather
  than edit or delete the unloaded baseline. Full evidence and rejected candidates are in
  [unloaded-tuning-2026-08-20.md](../testing/unloaded-tuning-2026-08-20.md).
- **The unloaded top-speed result is objective and repeatable.** The selected 25 kHz image
  completed ten minutes at 170 RPM with zero fault, stall, or reversal; mean wall draw was
  2.8077 W. The cyclical electrical whine was materially suppressed, while the faint steady
  winding/bearing-like sound remains the unloaded mechanical baseline.
- **The autonomous evidence harness is ready to extend to the loaded rotor.**
  `firmware/scripts/08-flash-and-unloaded-profile.sh` synchronizes serial telemetry, Hall/FG,
  Kasa power, IR motion, and room audio with fail-closed coverage checks. The qualified unloaded
  scripts remain retained rather than being repurposed for loaded work.
- **Optional waveform capture has a defined path.** An OWON VDS1022I USB-isolated PC scope is
  being purchased and may arrive in time for loaded tuning, but it is not a prerequisite. J8
  pin authority, common-ground limitations, safe hookups, and recorder requirements live in
  [observability.md](observability.md).

## Next

Install the finished motor/carrier, rotor, Hall board, controller, final harnesses, and a
strain-relieved long USB data connection on the existing ceiling plate, working unpowered and
one physical step at a time through [install.md](install.md) and
[integration.md](integration.md).

This is the chosen loaded-test location because it provides the final support, rotor load,
cable lengths, ceiling interaction, and room acoustics. After unpowered clearance and continuity
checks, the next-next step is loaded MPET and tuning with the retained unloaded image available
as the A/B baseline; use the USB scope too if it has arrived and passed the qualification in
[observability.md](observability.md).

## Candidates Not Chosen

- **Loaded tuning on an improvised bench rig:** not chosen; there is insufficient useful space,
  and the installed ceiling assembly is both better supported and more representative.
- **EEPROM commit of the unloaded image:** rejected. Only the reviewed loaded golden image may
  populate persistent `IMAGE` and be committed.
- **USB oscilloscope as a blocker:** rejected. It can improve current/bus/commutation evidence if
  available, but Hall/FG, camera/audio, MCF telemetry, and wall power already support a safe start.
- **More current to cure the old 170 RPM result at 19.4 V:** rejected by diagnostics; reduced
  bus-voltage authority, not current authority, caused that bench limit.

## Future Only On Explicit Request

Do not suggest, schedule, or use these as blockers unless Michael explicitly asks to resume one:
ENC-100 cosmetic housing, TEMP_SENSE firmware, intentional-imbalance testing, exhaustive start
matrices, exhaustive acoustic testing, network/Matter resilience testing, exhaustive fault
permutations, tether rework, catcher rework, or PCB-bracket CAD.

## Learned Recently

- Unloaded tuning values, acoustic interpretation, endurance evidence, and candidate history:
  [unloaded-tuning-2026-08-20.md](../testing/unloaded-tuning-2026-08-20.md).
- Ceiling integration order and the now-active USB service path: [install.md](install.md).
- Measurement authority and optional scope capture contract: [observability.md](observability.md).
- Motor rejection criteria and least-disruption alternatives: [motor-contingency.md](motor-contingency.md).
