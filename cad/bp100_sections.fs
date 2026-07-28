FeatureScript 1560;
import(path : "onshape/std/geometry.fs", version : "1560.0");

// BP-100 v3 blade sections (see docs/blade-v2.md).
// v3: the blade root is an integrated flat mounting rectangle (r52-96, modeled
// manually in the Part Studio) that bolts straight to RH-100 — no adapter.
// This feature generates the 8 NACA 6407 airfoil station sketches from the
// built-in table; a manual transition loft joins the rectangle's outboard end
// (r96) to the first station (r120).
// Frame: X radial outboard, Y toward the LE, Z up toward the ceiling.
// The pitch/rod plane depth is a dialog input — drive it with the Variable
// Studio expression (#hubBottom + 6 mm) so stack changes regenerate the blade.

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
    { r : 557.5, c : 14,  tw : 8.5,  ys : -10, zr : -8 }
];
// Root-corner closure lofts stay rejected (tangent off a growing chord bulges
// outward — 2026-07-27); in v3 the root simply IS the rectangle, so there is
// nothing to close.

const M = 0.06;  // max camber
const P = 0.40;  // camber position
const T = 0.07;  // thickness
const N = 30;    // points per surface

// camber-line height at 30% chord: sections anchor to the spar by this point,
// NOT the chord line — the cambered section's material sits above its chord
// line, so a rod on the chord line would run outside the blade entirely
const YC30 = M / P ^ 2 * (2 * P * 0.3 - 0.3 ^ 2);

const PITCH_BOUNDS = { (millimeter) : [50, 124.2, 400] } as LengthBoundSpec;

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
            const c = s.c * millimeter;
            const tw = s.tw * degree + definition.pitchOffset;
            const anchor = vector(s.ys, s.zr) * millimeter;
            const u = vector(-cos(tw), -sin(tw));    // chordwise, LE -> TE
            const v = vector(-sin(tw), cos(tw));     // thickness-wise, toward ceiling
            const le = anchor + 0.3 * c * vector(cos(tw), sin(tw)) - (YC30 * c) * v;
            const gapRel = definition.teGap / c;

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

            // one open run TE-upper -> LE -> TE-lower, then a line closing the blunt TE
            var pts2d = [];
            for (var j = N - 1; j >= 0; j -= 1)
                pts2d = append(pts2d, upper[j]);
            for (var j = 1; j < N; j += 1)
                pts2d = append(pts2d, lower[j]);

            var sketchPts = [];
            for (var p in pts2d)
                sketchPts = append(sketchPts, le + (p[0] * c) * u + (p[1] * c) * v);

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
// Set "Pitch plane depth" to the same expression as the sections feature.
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
