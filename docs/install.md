# Installation: anchors, slab verification, approvals

Site: 11-storey concrete condo in Vancouver, BC, built 2006. Ceiling slab possibly
post-tensioned (treat as PT until proven otherwise); existing bolts of unknown type in the
slab. This doc covers Gate 04 (concrete interface) and Gate 06 (installation approval) from
[decisions.md](decisions.md). Research basis: ICC-ES ESR-4266/ELC-4266 (CSA A23.3 Annex D
recognition), ESR-3027, ESR-4868, Hilti Tech Guide Ed. 22, City of Vancouver Electrical
By-law 5563 — researched 2026-07; uncertainty is marked inline.

## Anchor selection

Demand per primary anchor (two on 130 mm centers, from the design envelope of 1.25 kN
vertical / 0.30 kN lateral / 60 N·m overturning / 8 N·m torque): ~1.09 kN tension,
~0.21 kN shear. True sustained dead tension is only ~25–40 N per anchor for a 5–8 kg
assembly. Tether requirement: the calculated dynamic catch peak with ≥2× margin (order
1–2 kN for the ~4–5 kg retained mass over 15–20 mm slack — see parts.md; the earlier
"≥4.5 kN" was a dossier default, kept only as a free floor for the cable/fittings). All
capacities below are design strengths in **cracked concrete at f'c 2500 psi** — the correct
conservative assumption for a suspended slab soffit — from ICC-ES **ESR-2713** (Simpson
Titen HD), which recognizes all these diameters for seismic SDC A–F.

Selection revised 2026-07 after owner cost research: Hilti KB-TZ2 was technically fine
(~7× margin) but retail-absurd (pack pricing ~$2000); Simpson Titen HD screw anchors carry
equivalent code recognition at ~$1–3/anchor. The owner's proposed 1/4 × 1-7/8 in
(THDB25178H) was rejected on embedment arithmetic: through the 6 mm plate it reaches
1.639 in against a 1.625 in ESR minimum (0.36 mm margin), and any hard spacer puts it
below minimum — outside recognized capacity entirely.

- **Primary anchors (selected): 2× Simpson Titen HD 3/8 × 3 in (`THD37300H`)** — design
  tension 3.57 kN cracked (pullout-governed) vs 1.09 kN demand = **3.3× margin**; 70 mm
  drilled hole; min slab 102 mm; 130 mm centers clear the 76 mm minimum spacing; reaches
  full embedment through plate + 3 mm spacer with 3.7 mm to spare. Heavy flat washers over
  the 11 × 20 mm slots. Install per Simpson's instructions (drill per ESR, socket/impact
  drive — screw anchors have no set torque like wedge anchors). No sustained-load or
  overhead penalty applies (the ACI 0.55 factor is adhesive-bond-specific).
- **Tether anchor (default): Titen HD 3/8 × 4 in (`THD37400H`)** — 7.81 kN, covering both
  load bases unconditionally (1.74× over even the legacy 4.5 kN floor); 89 mm hole; min
  slab 127 mm. **Simplification path**: if the calculated/tested catch peak is ≤ ~1.7 kN
  (likely per first principles), a third `THD37300H` (3.57 kN, ≥2× margin) covers it and
  all three anchors become one part at one 70 mm hole depth. The shallowest
  technically-passing option (1/4 × 3 in, 67 mm hole, 5.51 kN) is deliberately not chosen:
  the single fall-arrest anchor is the wrong place for the catalog's smallest diameter to
  save 22 mm of hole depth. Keep ≥190 mm from the primaries; terminate in a forged
  shoulder eyebolt or rated eye nut (never a bent-wire eye); proof-test in place.
- **Service rule**: Titen HDs are torqued once and never fully removed (ESR-2713 §4.3
  permits a one-turn backout only; screw-formed concrete threads are a consumable
  interface). The design already services at the carrier-to-standoff M6 joint from below —
  the anchors and plate stay on the ceiling.
- **Scope caveats**: ESR-2713 formally excludes shock/impact loading, so the tether's
  arrest role technically outruns the paperwork — accepted on the static margins plus the
  mandated off-ceiling dynamic catch test. The ESR is a US (ACI 318-19) document;
  CSA A23.3 Annex D is methodologically near-identical, but a BC engineer should cite the
  Canadian evaluation reference if a stamped submission is ever needed.
- **Rejected alternatives**: HIT-HY 200 adhesive (overhead *sustained* tension triggers
  continuous special inspection, certified installers, the 0.55 sustained-bond factor, and
  piston-plug injection — overkill for a 60 N sustained load); Hilti KB-TZ2 wedge anchors
  remain a technically sound fallback if Titen HD availability changes (wedge studs also
  permit unlimited plate removal via the nuts, the one capability Titen HD lacks).
- **Purchasing**: ordered 2026-07 as singles from ohcanadasupply.ca (~$1.44/$1.53 each,
  3× THD37300H + 2× THD37400H including spares, ~$7.50 total — a fresh anchor per redrill,
  never reuse a driven one). Big-box Canada doesn't stock it online; amazon.ca sells
  50-packs (~$60) as the fallback source.

## Mounting sequence

Titen HDs are through-fixture fasteners — the plate and anchors go up together (the screw
head + washer clamps the plate; there is no set-stud-first step as with wedge anchors):

1. **Bench-assemble the plate unit**: SP-100 spindle into its recess (opens toward the
   ceiling — cannot be added later) and the three ST-100 standoffs torqued via their
   ceiling-face M6 flat-heads (also inaccessible later), plus hard spacers. ~3 kg unit.
2. After the scan clears the spots: mark via the plate or a template (the 11 × 20 slots
   absorb ±4–5 mm), drill **without the plate** using a 3/8 in carbide bit meeting ANSI
   B212.15 in a rotary hammer (SDS-plus; bit nominal matches the anchor — never substitute
   a 10 mm metric bit, the thread engagement assumes ANSI tolerance), depth-stopped at
   ~75 mm (primaries) / ~95–100 mm (tether), then brush/blow clean per Simpson's
   instructions. Tooling (2026-07): drill = the owner's **M12 Fuel hammer drill (3404)** in
   hammer mode with a **straight-shank** ANSI B212.15 carbide percussion bit — Makita
   B-68812 3/8 × 6 in (verify ANSI marking and ≥100 mm flute length on arrival; SDS bits do
   not fit a 3-jaw chuck). Expect slow going in tower slab: peck-drill to clear dust and
   cool the tip; if a hole barely progresses, rent an SDS-plus rotary hammer instead of
   forcing it. The M12 impact driver (no axial percussion — cannot drill) **drives** the
   anchors via a 9/16 in socket.
3. Offer up the plate unit; drive both primaries through washer + slot (socket/impact).
   **Length/stack budget**: the 3 in screws have 12.7 mm of fixture budget above the
   63.5 mm minimum embedment — plate 6 mm leaves ≤6.7 mm for washer + spacers combined.
   Use standard-thickness washers (~2.5 mm) and only as much spacer as the finish demands
   (≤~4 mm); if more shimming is needed, step up to a 3-1/2 in screw rather than thinning
   the embedment. Hardware (2026-07): Prime-Line 9080006 USS 3/8 × 1 in OD zinc washers —
   one under each head, one as the hard spacer per anchor (2.5 mm covers the ~1–2 mm
   ceiling texture plus any slightly-proud countersunk M6 heads on the plate's ceiling
   face); stack = 11 mm of the 12.7 mm budget. Drill ~75 mm for the primaries, ~95–100 mm for the 4 in tether ("too
   deep" costs nothing; too-shallow driving stalls the screw proud of the plate).
4. Stack from below: carrier (motor pre-bolted, wires through the window) onto the
   standoffs (M6 × 20 + wedge washers), hub + rotor onto the motor face, KD-100 +
   castellated nut + cotter onto the spindle, then electronics and housing. Service
   reverses this from below; anchors are never touched.

**Open item — tether termination**: a Titen HD ends in a plain hex head, so the wedge-era
"rated eye nut on the stud" plan no longer applies. Either clamp a **rated pad-eye/anchor
plate** under the THD37400H head, or substitute Simpson's **Titen HD rod-hanger (internally
threaded coupler) variant** and thread in a forged 3/8-16 shoulder eyebolt. Decide before
the tether hole is drilled; the tether path rating must include this fitting.

## Pre-drill verification checklist (Gate 04)

1. **Slab type is the gating unknown.** PT flat plates are common in 2000s Lower Mainland
   towers but not universal; treat this building as possibly PT until proven. The existing
   ceiling bolts prove nothing about slab type and do not license new drilling.
2. **Confirmation path, in order**: (a) structural drawings from the strata
   council/property manager; (b) City of Vancouver "property research / copies of permits"
   service for the structural set; (c) **GPR scan of the exact drill locations regardless**
   — as-builts drift and tendon drape makes local depth matter. Vancouver firms: Xradar,
   GPRS, etc.; single-visit cost plausibly a few hundred dollars (unverified).
3. **Scan deliverables**: slab thickness at the mount point; tendon/rebar positions with
   marked keep-outs; embedded electrical conduit (common in slab soffits); confirmation of
   solid slab.
4. **Thickness vs anchor**: ≥102 mm for the 3/8 × 3 in primaries; ≥127 mm for the
   3/8 × 4 in tether (drops to 102 mm if the simplification path applies). Drilled hole
   depths for tendon clearance: 70 mm (primaries), 89 mm (deep tether).
5. **Existing bolts**: identify but do not trust or reuse — type/embedment/condition are
   unknowable. Install new anchors offset from abandoned holes (rule of thumb ≥ one
   embedment depth, or fill old holes with high-strength repair mortar first; judgment rule,
   confirm in PROFIS or with an engineer).
6. **Rebar hit (non-PT)**: relocate the hole rather than cut. A PT tendon strike is the
   non-negotiable hazard — never drill an unscanned PT-suspect slab.
7. Keep the cracked-concrete assumption for final selection.
8. **Installation QA**: hammer-drill to the ESR hole spec, clean holes, drive per Simpson's
   installation instructions (socket/impact; no torque-set), never back out more than one
   turn, then the planned proof loads.

## Approvals (Gate 06)

Inside Vancouver city limits the electrical authority is the **City of Vancouver under its
own Electrical By-law 5563** (adopting CEC C22.1:24 with BC variations), not Technical
Safety BC.

Required (high confidence):

- **Strata written approval before drilling** — the slab is common property under the BC
  Strata Property Act; expect an alteration request + indemnity agreement, and possibly an
  engineer's letter/scan for a PT-suspect slab. Read the registered strata bylaws; this is
  the one unambiguous approval.
- **No building permit** (5–8 kg appliance, far below permit triggers) and **no electrical
  permit** (cord-and-plug into an existing receptacle is not "electrical work").

The one grey zone, and how to close it: whether the custom fan itself needs an approval
mark. Ontario's ESA explicitly exempts equipment fed from an approved Class 2 supply
(≤100 VA, ≤60 V DC) with carve-outs that don't include fans; BC/Vancouver practice is
reportedly similar but unverified in writing. **Close the gate with one email to the City's
electrical desk (electricalpermits@vancouver.ca)** describing the device. Two supporting
nuances:

- The GST60A24 is cULus-certified to UL/CSA 62368-1 as an LPS supply, inside Class 2 power
  limits, but not UL 1310 "Class 2"-**marked**. If the City reads "approved Class 2 supply"
  strictly, swapping to a Class 2-marked 24 V adapter is a trivial mitigation.
- Keep the 24 V run **surface-mounted** (the planned printed conduit). Concealing it in
  walls/ceiling cavities turns it into a CEC Section 16 power-limited *installation* with
  cable-type and permit questions.

Fallback if an approval is ever demanded: **CSA SPE-1000 field evaluation** (one-off custom
equipment labeling by CSA/Intertek/QPS; commonly cited in the low thousands of dollars,
unverified) — almost certainly unnecessary if the Class 2 relief applies.

Prudent, not required: a documentation package (design loads, proof-test results, PSU
certification) for the strata and any future sale. Insurance exposure is mostly folklore at
24 V DC, but the strata-deductible chargeback mechanism for owner-alteration losses is real.

Province dependence: the Class 2 exemption wording and the AHJ identity vary by province
(City of Vancouver in-city, TSBC elsewhere in BC, ESA in Ontario); the strata approval is BC
statute; the anchor engineering (ELC-4266 / CSA A23.3 Annex D) is Canada-wide.

## Sources

ESR-4266 / ELC-4266 / ESR-3027 / ESR-4868 (icc-es.org) · Hilti KB-TZ2 technical data · BC
Electrical Safety Regulation · ESA product-approval exceptions (esasafe.com) · Technical
Safety BC accepted certification marks · Intertek SPE-1000 · Vancouver Electrical By-law
5563 (bylaws.vancouver.ca/5563c.pdf) · Mean Well GST60A datasheet.
