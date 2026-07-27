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
assembly. Tether path requirement: ≥4.5 kN. All capacities below are design strengths in
**cracked concrete at f'c 2500 psi** — the correct conservative assumption for a suspended
slab soffit.

- **Primary anchors (selected candidate): Hilti KB-TZ2 3/8 in stainless, hef 2 in**
  (hnom 2-1/2 in, ~70 mm hole). Design tension 8.6 kN; with the ~0.92 group factor at
  130 mm spacing (below scr = 152 mm), **~7.9 kN vs 1.09 kN demand ≈ 7× margin** (shear
  ~40×; still ~5× with the 0.75 seismic factor). Min slab 102 mm. Install torque 41 N·m.
  Use heavy flat washers over the plate's 11 × 20 mm slots. No sustained-load or overhead
  penalty applies to wedge anchors (that 0.55 factor is adhesive-bond-specific).
- **Tether anchor: KB-TZ2 3/8 in at hef 2-1/2 in** (9.7 kN, 2.2× over 4.5 kN; needs
  ≥127 mm slab) or hef 2 in (8.6 kN, 1.9×) if thickness is marginal. Keep ≥190 mm from the
  primaries to avoid group interaction. Terminate in a forged shoulder eyebolt or rated eye
  nut (never a bent-wire eye); proof-test in place per the existing test plan.
- **Rejected alternatives**: KH-EZ/HUS-EZ screw anchors (ESR permits loosening max one turn
  — not actually removable/reinstallable, and shallow-embedment cracked pullout is too weak
  for the tether); HIT-HY 200 adhesive (approved overhead, but overhead *sustained* tension
  triggers continuous special inspection, certified installers, the 0.55 sustained-bond
  factor, and piston-plug injection — massive procedural overkill for a 60 N sustained
  load; fallback only if scanning forces unusual geometry).

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
4. **Thickness vs anchor**: ≥102 mm for hef 2 in; ≥127 mm for hef 2-1/2 in.
5. **Existing bolts**: identify but do not trust or reuse — type/embedment/condition are
   unknowable. Install new anchors offset from abandoned holes (rule of thumb ≥ one
   embedment depth, or fill old holes with high-strength repair mortar first; judgment rule,
   confirm in PROFIS or with an engineer).
6. **Rebar hit (non-PT)**: relocate the hole rather than cut. A PT tendon strike is the
   non-negotiable hazard — never drill an unscanned PT-suspect slab.
7. Keep the cracked-concrete assumption for final selection.
8. **Installation QA**: hammer-drill per the MPII, clean holes, torque-wrench to 41 N·m,
   then the planned proof loads.

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
