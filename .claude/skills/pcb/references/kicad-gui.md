# KiCad GUI automation on this Mac

Read this reference when downstream KiCad work needs project launch, Board Setup, ECO application,
or window cleanup. It records the reliable automation path after a tscircuit handoff. It does not
authorize direct edits to protected KiCad files.

## Open the project without stray editors

1. Close existing KiCad editor windows. Resolve any save prompt instead of force-quitting.
2. Open the target `.kicad_pro`, never a `.kicad_sch` or `.kicad_pcb` directly.
3. In the project manager, open Schematic Editor or PCB Editor from **Tools** or its large button.
4. Minimize the project-manager window immediately after the editor opens. This leaves the yabai
   tile to the working editor.
5. Close any generic or `untitled` editor window that opened outside the project.
6. Audit the result:

   ```bash
   python3 pcb/tools/kicad_window_state.py pcb/pcb-01-v2/pcb-01-v2.kicad_pro
   ```

The audit is read-only and exits nonzero for a visible project manager or a stand-alone editor.
It reports success when KiCad is fully closed, which is also a valid starting state.

## Automation method

Use the normal computer-control tool when it can click the visible UI. If it repeatedly returns
`remoteConnection`, stop retrying that route. On this Mac, the reliable fallback is to run
`/usr/bin/osascript` or `/opt/homebrew/bin/cliclick` through the Codex app's Node REPL using
`node:child_process`. This makes macOS attribute Accessibility and Automation access to Codex,
whose permissions are already approved. Running `osascript` from a terminal attributes the request
to that terminal and can open a new TCC prompt.

Prefer Accessibility controls over coordinates:

- raise a window with its `AXRaise` action;
- invoke named menu items and buttons through `System Events`;
- save with Command-S;
- inspect `entire contents` and use role, value, and position to disambiguate controls.

wxWidgets layer trees and list controls may not appear in Accessibility. For those only, query the
window frame with `yabai`, capture it with `screencapture -x`, inspect the crop, then click the
resolved screen coordinate with `cliclick`. Re-query the dialog after each state change. Do not
reuse coordinates across a moved or resized window.

If macOS presents a permission alert, inspect the actual alert and approve only the access needed
for the current KiCad operation. Do not dismiss or guess through an unseen prompt.

## Initial handoff setup

The tscircuit handoff tool creates the initial project, schematic/netlist, outline, holes, and
placement in a staging directory. Validate and adopt that seed once. Do not manually recreate those
source-owned domains in KiCad.

Use KiCad's Board Setup and Schematic Setup dialogs only for items declared in
`design/kicad-augment.json`, such as project metadata, stackup/copper weights, impedance settings,
net classes, custom rules, and fabrication constraints unsupported by the exporter. Do not use
Konnect's `add_layer`, `set_design_rules`, `create_netclass`, or `assign_net_to_class` on KiCad 10.
Do not edit `.kicad_pro` directly.

After routes exist, use the handoff ECO plan rather than Update PCB from Schematic as a blind full
sync. Snapshot route, via, zone, graphic, rule, and UUID state before applying an ECO, then prove
unrelated KiCad-owned state is preserved.

Board Setup fields can share a vertical coordinate. When UI automation must target a field, match
both x and y position or another unique Accessibility property. A y-only match can update a second
field such as maximum error deviation.

## Verify after setup or ECO

- Save both editors.
- Run ERC and headless DRC. For an initial unrouted seed, unconnected findings are expected; parse,
  outline, courtyard, or footprint errors are not.
- Reopen Board Setup and confirm the visible values, especially layer count, stackup thickness,
  copper weights, minimums, and default net class.
- Run source-to-KiCad parity and verify all applied augmentation items.
- Run the window audit and leave the project manager minimized.
