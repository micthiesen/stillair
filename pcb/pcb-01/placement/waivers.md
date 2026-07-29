# Accepted DRC residuals — PCB-01 placement (2026-07-29)

> **LAYOUT LOCKED 2026-07-29** after the three-round board-truth review loop (18 + 5 + 2
> agent lenses; round 3 verdict GO, zero defects). Final DRC:
> clearance 10 (stock fine-pitch footprint internals), courtyards_overlap 15 (list below,
> all TP-ring or verified-body-clear margin pairs), silk classes pending post-routing
> cleanup, lib_footprint classes = our deliberate customizations. Placement changes after
> this point only with a re-run of the checks in pcb/tools/.

Reference list for reading `kicad-cli pcb drc` output. Every violation class below
was triaged item-by-item; anything not listed here appearing in a future DRC run
is NEW and needs a look. Rule of thumb from the J2 incident: courtyard classes may
be margin-only noise, but **anything touching copper, edge, or holes is never
cosmetic until proven so at pad level**.

## courtyards_overlap (16) — all verified body-clear via F.Fab outlines

Courtyards include ~0.25 mm grace margins; these pairs overlap margins only.

- **TP×TP / TP×part pairs** (TP7/8/10-20/24/27, C11, C12, C16, Q2, U7): a test
  point has no body, just a probe pad. All probe pads themselves are clear of
  neighbor bodies. No assembly impact.
- **RV1 × U8** (−0.23 courtyard): bodies 0.27 mm apart (RV1 top 89.10 vs U8
  bottom 88.83). Trimmer screw access is from the top — unaffected.
- **RV1 × R48** (−0.12 courtyard): bodies 0.33 mm apart.
- **J8 × U9** (−0.57 courtyard): bodies 1.18 mm apart; U9's pad-tip copper comes
  within 0.13 mm of J8's body edge. J8 is a DNP bench-scope header — when loaded,
  its plastic sits next to U9's pin-4/5 fillets. Accepted.
- **J8 × TP6** (−0.52 courtyard): TP6's probe pad is 0.48 mm clear of J8's body;
  probeable even with the header loaded.

## Board-edge overhangs — intentional (mating faces) or trivial

- **J1** (Micro-Fit RA input): mating face + ~3.1 mm of body off the LEFT edge;
  THT pins and peg on-board. Standard right-angle inlet placement.
- **J2** (Micro-Fit RA motor): face flush at the BOTTOM edge, courtyard grace
  0.55 mm past it. (Re-placed 2026-07-29 — was rotated 90° wrong with pin 3's
  pad off-board; see SKILL.md lesson.)
- **J6** (USB-C top-mount): courtyard extends 1.78 mm past the TOP edge — the
  plug-overmold zone of an edge-mount receptacle. Pads on-board (DRC-clean).
- **J8**: body pokes 0.24 mm past the RIGHT edge. Harmless (nothing there);
  moving it west would put its body over U9's pad tips, which is worse.
- `check_plan.py` `EDGE_WAIVER` encodes the per-side allowances (J1 left,
  J2 bottom).

## Other residual classes

- **clearance (14)**: pad-to-pad inside stock fine-pitch footprints
  (SOT-563 / SOT-23-8 geometry vs our 0.1 mm min_clearance rule). Fab-proven
  library parts; not layout defects.
- **silk_overlap / silk_over_copper (199 each) + silk_edge_clearance (6)**:
  reference-text noise from the placement pass; cosmetic sweep pending.
- **lib_footprint_mismatch (7) / lib_footprint_issues (4)**: our deliberately
  customized footprints (MCF8316D pads, ESP32 trimmed courtyard, TPSM comb-pad
  simplification) differing from library copies.
- **H4 × U2**: mounting hole inside the ESP32 antenna-keepout courtyard —
  documented tradeoff from the placement pass (check_plan.py waives it).
