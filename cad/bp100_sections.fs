FeatureScript 1560;
import(path : "onshape/std/geometry.fs", version : "1560.0");

// BP-100 v3 blade sections (see docs/blade-v2.md).
// v3: the blade root is an integrated flat mounting rectangle (r52-96, modeled
// manually in the Part Studio) that bolts straight to RH-100 — no adapter.
// Feature 1 generates the 8 NACA 6407 airfoil station sketches from the
// built-in table; feature 2 cuts the spar channel; feature 3 generates four
// 3D guide curves for the manual transition loft from the rectangle's outboard
// end face (r96) to the first station (r120) — an unguided loft between the
// 4-cornered face and the spline section twists (found 2026-07-28).
// Frame: X radial outboard, Y toward the LE, Z up toward the ceiling.
// The pitch/rod plane depth is a dialog input — drive it with the Variable
// Studio expression (#hubBottom + 6 mm) so stack changes regenerate the blade.
// Give ALL features the same Pitch plane depth / Pitch offset / TE thickness
// values, or the guides will miss the section curves.

// radius, chord, twist (deg), anchor y-shift, z-raise — all mm.
// zr is now NEGATIVE outboard: the proplet flips DOWNWARD in v3 — with the
// hugger ceiling gap the old tip-up rake sat exactly in the intake throat at
// the rotor perimeter; drooping it moves the tip vortex away from the ceiling
// and opens the throat (2026-07-27).
const STATIONS = [
    { r : 120,   c : 81,  tw : 16.7, ys : 0,   zr : 0 },
    { r : 180,   c : 100, tw : 15.0, ys : 0,   zr : 0 },
    { r : 250,   c : 118, tw : 13.0, ys : 0,   zr : 0 },
    { r : 330,   c : 112, tw : 11.5, ys : 0,   zr : 0 },
    { r : 420,   c : 94,  tw : 10.0, ys : 0,   zr : 0 },
    { r : 500,   c : 76,  tw : 9.0,  ys : 0,   zr : -3 },
    { r : 556,   c : 40,  tw : 8.5,  ys : -6,  zr : -6 },
    { r : 557.5, c : 18,  tw : 8.5,  ys : -7,  zr : -6.4 }
];
// Root-corner closure lofts stay rejected (tangent off a growing chord bulges
// outward — 2026-07-27); in v3 the root simply IS the rectangle, so there is
// nothing to close.

// Root rectangle geometry (must match the manual Part Studio sketch)
const RECT_R_END = 96;    // outboard end face radius, mm
const RECT_HALF_W = 25;   // half width, mm (y +/- 25)
const RECT_HALF_T = 6;    // half thickness, mm (12 thick about the pitch plane)

const M = 0.06;  // max camber
const P = 0.40;  // camber position
const T = 0.07;  // thickness
const N = 30;    // points per surface

// camber-line height at 30% chord: sections anchor to the spar by this point,
// NOT the chord line — the cambered section's material sits above its chord
// line, so a rod on the chord line would run outside the blade entirely
const YC30 = M / P ^ 2 * (2 * P * 0.3 - 0.3 ^ 2);

const PITCH_BOUNDS = { (millimeter) : [50, 124.2, 400] } as LengthBoundSpec;

// In-plane section points (h toward LE, v toward ceiling, with units) for one
// station map {r, c, tw, ys, zr}, given the dialog pitch offset and TE gap.
// Point order: TE-upper -> LE -> TE-lower; the sketch spline interpolates
// these exact points, which is what lets the guide feature land on the curve.
function sectionPlanePts(s is map, pitchOffset, teGap) returns array
{
    const c = s.c * millimeter;
    const tw = s.tw * degree + pitchOffset;
    const anchor = vector(s.ys, s.zr) * millimeter;
    const u = vector(-cos(tw), -sin(tw));    // chordwise, LE -> TE
    const v = vector(-sin(tw), cos(tw));     // thickness-wise, toward ceiling
    const le = anchor + 0.3 * c * vector(cos(tw), sin(tw)) - (YC30 * c) * v;
    const gapRel = teGap / c;

    var upper = [];
    var lower = [];
    for (var j = 0; j < N; j += 1)
    {
        const x = 0.5 * (1 - cos(PI * j / (N - 1) * radian));
        var yc;
        var dyc;
        if (x < P)
        {
            yc = M / P ^ 2 * (2 * P * x - x * x);
            dyc = 2 * M / P ^ 2 * (P - x);
        }
        else
        {
            yc = M / (1 - P) ^ 2 * ((1 - 2 * P) + 2 * P * x - x * x);
            dyc = 2 * M / (1 - P) ^ 2 * (P - x);
        }
        const yt = T / 0.2 * (0.2969 * sqrt(x) - 0.1260 * x - 0.3516 * x ^ 2
                    + 0.2843 * x ^ 3 - 0.1036 * x ^ 4)
                + 0.5 * gapRel * x;          // linear opening to the TE gap
        const th = atan(dyc);
        upper = append(upper, vector(x - yt * sin(th), yc + yt * cos(th)));
        lower = append(lower, vector(x + yt * sin(th), yc - yt * cos(th)));
    }

    // one open run TE-upper -> LE -> TE-lower (the sketch adds the TE closer)
    var pts2d = [];
    for (var j = N - 1; j >= 0; j -= 1)
        pts2d = append(pts2d, upper[j]);
    for (var j = 1; j < N; j += 1)
        pts2d = append(pts2d, lower[j]);

    var planePts = [];
    for (var p in pts2d)
        planePts = append(planePts, le + (p[0] * c) * u + (p[1] * c) * v);
    return planePts;
}

annotation { "Feature Type Name" : "BP-100 airfoil sections" }
export const bp100Sections = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
        annotation { "Name" : "Pitch plane depth" }
        isLength(definition.pitchZ, PITCH_BOUNDS);
        annotation { "Name" : "Pitch offset" }
        isAngle(definition.pitchOffset, { (degree) : [-6, 0, 6] } as AngleBoundSpec);
        annotation { "Name" : "TE thickness" }
        isLength(definition.teGap, { (millimeter) : [0, 0.6, 3] } as LengthBoundSpec);
    }
    {
        var i = 0;
        for (var s in STATIONS)
        {
            const sketchPts = sectionPlanePts(s, definition.pitchOffset, definition.teGap);
            const pl = plane(vector(s.r * millimeter, 0 * millimeter, -definition.pitchZ),
                             vector(1, 0, 0), vector(0, 1, 0));
            var sk = newSketchOnPlane(context, id + ("station" ~ toString(i)), { "sketchPlane" : pl });
            skFitSpline(sk, "foil", { "points" : sketchPts });
            skLineSegment(sk, "te", { "start" : sketchPts[size(sketchPts) - 1], "end" : sketchPts[0] });
            skSolve(sk);
            i += 1;
        }
    });

// Cuts the Ø3.4 spar-rod channel along the pitch axis. Insert AFTER the lofts
// (rectangle + transition + main + tip). v3 span r56-430: starts inside the
// root rectangle (4 mm cap to its r52 inner arc) and ends where the DOWNWARD
// proplet run-in drops the loft off the straight rod line (wall dies ~r460;
// see cad/bp100_envelope_check.py). Rod cut length 374 from 400 mm stock.
annotation { "Feature Type Name" : "BP-100 spar channel" }
export const bp100SparChannel = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
        annotation { "Name" : "Blade part", "Filter" : EntityType.BODY && BodyType.SOLID, "MaxNumberOfPicks" : 1 }
        definition.blade is Query;
        annotation { "Name" : "Pitch plane depth" }
        isLength(definition.pitchZ, PITCH_BOUNDS);
        annotation { "Name" : "Channel diameter" }
        isLength(definition.channelD, { (millimeter) : [2, 3.4, 6] } as LengthBoundSpec);
        annotation { "Name" : "Start radius" }
        isLength(definition.rStart, { (millimeter) : [40, 56, 400] } as LengthBoundSpec);
        annotation { "Name" : "End radius" }
        isLength(definition.rEnd, { (millimeter) : [200, 430, 500] } as LengthBoundSpec);
    }
    {
        fCylinder(context, id + "rod", {
                    "bottomCenter" : vector(definition.rStart, 0 * millimeter, -definition.pitchZ),
                    "topCenter" : vector(definition.rEnd, 0 * millimeter, -definition.pitchZ),
                    "radius" : definition.channelD / 2
                });
        opBoolean(context, id + "cut", {
                    "tools" : qCreatedBy(id + "rod", EntityType.BODY),
                    "targets" : definition.blade,
                    "operationType" : BooleanOperationType.SUBTRACTION
                });
    });

// Four 3D guide curves for the transition loft: rectangle end-face corners ->
// exact interpolation points of the r120 section spline. Smoothstep easing in
// (y, z) leaves the slab tangent (parallel to X) and arrives flat at the
// section, so the loft cannot twist. Use them as Guides in a loft whose
// profiles are the rectangle end face and the r120 section (or the main
// loft's r120 end face). Same dialog values as the sections feature, or the
// guide ends will miss the drawn curve.
annotation { "Feature Type Name" : "BP-100 root guides" }
export const bp100RootGuides = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
        annotation { "Name" : "Pitch plane depth" }
        isLength(definition.pitchZ, PITCH_BOUNDS);
        annotation { "Name" : "Pitch offset" }
        isAngle(definition.pitchOffset, { (degree) : [-6, 0, 6] } as AngleBoundSpec);
        annotation { "Name" : "TE thickness" }
        isLength(definition.teGap, { (millimeter) : [0, 0.6, 3] } as LengthBoundSpec);
    }
    {
        const planePts = sectionPlanePts(STATIONS[0], definition.pitchOffset, definition.teGap);
        const r0 = STATIONS[0].r * millimeter;
        const rFace = RECT_R_END * millimeter;

        // corner (y, z-offset from pitch plane) -> section point index.
        // Front (+y / LE-side) corners aim just aft of the LE on each surface;
        // aft corners aim at the TE spline ends.
        const pairs = [
            { corner : vector( RECT_HALF_W,  RECT_HALF_T) * millimeter, idx : N - 3 },     // LE upper
            { corner : vector( RECT_HALF_W, -RECT_HALF_T) * millimeter, idx : N + 1 },     // LE lower
            { corner : vector(-RECT_HALF_W,  RECT_HALF_T) * millimeter, idx : 0 },         // TE upper
            { corner : vector(-RECT_HALF_W, -RECT_HALF_T) * millimeter, idx : 2 * N - 2 }  // TE lower
        ];

        var g = 0;
        for (var pr in pairs)
        {
            const target = planePts[pr.idx];
            var pts = [];
            const K = 9;
            for (var k = 0; k <= K; k += 1)
            {
                const s = k / K;
                const h = 3 * s ^ 2 - 2 * s ^ 3;   // smoothstep: flat at both ends
                const yz = pr.corner + h * (target - pr.corner);
                pts = append(pts, vector(rFace + s * (r0 - rFace), yz[0], -definition.pitchZ + yz[1]));
            }
            opFitSpline(context, id + ("guide" ~ toString(g)), { "points" : pts });
            g += 1;
        }
    });

// Five 3D guide curves spanning the WHOLE main loft, r120 -> r556: LE, both
// TE ends, and mid-chord upper/lower. Each passes exactly through the section
// points at every loft profile radius, with extra samples through the r420-556
// taper so the silhouette follows the table instead of overshooting. Having
// one guided loft removes the r500 seam entirely — two lofts meeting there
// always left a planform crease (found 2026-07-28). The r557.5 end station is
// moderated (c18, ys-7, zr-6.4 vs the original c14/ys-10/zr-8 hook) so the
// guides can turn it; dense samples at 556/557/557.5 pin the rounding.
// Recipe: ONE main loft = all station sketches r120..r557.5 with these
// Guides, then full-round fillet the r557.5 end face.
// Same dialog values as the sections feature.
annotation { "Feature Type Name" : "BP-100 span guides" }
export const bp100SpanGuides = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
        annotation { "Name" : "Pitch plane depth" }
        isLength(definition.pitchZ, PITCH_BOUNDS);
        annotation { "Name" : "Pitch offset" }
        isAngle(definition.pitchOffset, { (degree) : [-6, 0, 6] } as AngleBoundSpec);
        annotation { "Name" : "TE thickness" }
        isLength(definition.teGap, { (millimeter) : [0, 0.6, 3] } as LengthBoundSpec);
    }
    {
        // Must include every main-loft profile radius exactly (guides have to
        // intersect the profiles); intermediate values are linear station
        // interpolation for shape control through the taper.
        const RS = [120, 180, 250, 330, 420, 460, 500, 515, 530, 545, 556, 557, 557.5];
        // TE upper, mid upper, LE, mid lower, TE lower
        const guideIdx = [0, 18, N - 1, 40, 2 * N - 2];

        var ptsByR = [];
        for (var r in RS)
        {
            // bracketing stations for piecewise-linear interpolation
            var i0 = 0;
            for (var j = 0; j < size(STATIONS) - 1; j += 1)
            {
                if (STATIONS[j].r <= r)
                    i0 = j;
            }
            const s0 = STATIONS[i0];
            const s1 = STATIONS[min(i0 + 1, size(STATIONS) - 1)];
            const f = s1.r == s0.r ? 0 : (r - s0.r) / (s1.r - s0.r);
            const st = { "r" : r,
                       "c" : s0.c + f * (s1.c - s0.c),
                       "tw" : s0.tw + f * (s1.tw - s0.tw),
                       "ys" : s0.ys + f * (s1.ys - s0.ys),
                       "zr" : s0.zr + f * (s1.zr - s0.zr) };
            ptsByR = append(ptsByR, { "r" : r, "pts" : sectionPlanePts(st, definition.pitchOffset, definition.teGap) });
        }

        var g = 0;
        for (var idx in guideIdx)
        {
            var pts = [];
            for (var e in ptsByR)
            {
                const p = e.pts[idx];
                pts = append(pts, vector(e.r * millimeter, p[0], -definition.pitchZ + p[1]));
            }
            opFitSpline(context, id + ("spanguide" ~ toString(g)), { "points" : pts });
            g += 1;
        }
    });
