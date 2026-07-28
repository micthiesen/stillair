FeatureScript 1560;
import(path : "onshape/std/geometry.fs", version : "1560.0");

// BP-100 blade sections (see docs/blade-v2.md).
// Generates all 8 NACA 6407 station sketches from the built-in station table:
// scaled to chord, twisted LE-up about the 30%-chord point (which sits on the
// spar axis at y = ys, z = zr), on a computed plane at each radius.
// Frame: X radial outboard, Y toward the LE, Z up toward the ceiling.

// radius, chord, twist (deg), anchor y-shift, z-raise — all mm
const STATIONS = [
    { r : 110,   c : 78,  tw : 17.0, ys : 0,   zr : 0 },
    { r : 180,   c : 100, tw : 15.0, ys : 0,   zr : 0 },
    { r : 250,   c : 118, tw : 13.0, ys : 0,   zr : 0 },
    { r : 330,   c : 112, tw : 11.5, ys : 0,   zr : 0 },
    { r : 420,   c : 94,  tw : 10.0, ys : 0,   zr : 0 },
    { r : 500,   c : 76,  tw : 9.0,  ys : 0,   zr : 3 },
    { r : 556,   c : 40,  tw : 8.5,  ys : -6,  zr : 6 },
    { r : 557.5, c : 14,  tw : 8.5,  ys : -10, zr : 8 },
    // root closure: rounds the r110 end's plan-view corners via a second
    // small loft. Appended LAST so the earlier stations keep their sketch
    // ids (the main loft references them by id).
    { r : 105.5, c : 66,  tw : 17.0, ys : 0,   zr : 0 },
    { r : 101.5, c : 30,  tw : 17.0, ys : 0,   zr : 0 }
];

const Z_CENTER = -223.5; // blade pitch plane, mm below the ceiling (world origin)

const M = 0.06;  // max camber
const P = 0.40;  // camber position
const T = 0.07;  // thickness
const N = 30;    // points per surface

// camber-line height at 30% chord: sections anchor to the spar by this point,
// NOT the chord line — the cambered section's material sits above its chord
// line, so a rod on the chord line would run outside the blade entirely
const YC30 = M / P ^ 2 * (2 * P * 0.3 - 0.3 ^ 2);

annotation { "Feature Type Name" : "BP-100 airfoil sections" }
export const bp100Sections = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
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

            const pl = plane(vector(s.r, 0, Z_CENTER) * millimeter, vector(1, 0, 0), vector(0, 1, 0));
            var sk = newSketchOnPlane(context, id + ("station" ~ toString(i)), { "sketchPlane" : pl });
            skFitSpline(sk, "foil", { "points" : sketchPts });
            skLineSegment(sk, "te", { "start" : sketchPts[size(sketchPts) - 1], "end" : sketchPts[0] });
            skSolve(sk);
            i += 1;
        }
    });

// Cuts the Ø3.4 spar-rod channel along the pitch axis. Insert AFTER the loft
// (and tip fillet); the r112 start leaves a 2 mm cap inside the root, and the
// r430 end is where the proplet run-in starts lifting the loft off the straight
// rod line (see docs/blade-v2.md, "Spar and segmentation").
annotation { "Feature Type Name" : "BP-100 spar channel" }
export const bp100SparChannel = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
        annotation { "Name" : "Blade part", "Filter" : EntityType.BODY && BodyType.SOLID, "MaxNumberOfPicks" : 1 }
        definition.blade is Query;
        annotation { "Name" : "Channel diameter" }
        isLength(definition.channelD, { (millimeter) : [2, 3.4, 6] } as LengthBoundSpec);
        annotation { "Name" : "Start radius" }
        isLength(definition.rStart, { (millimeter) : [100, 112, 400] } as LengthBoundSpec);
        annotation { "Name" : "End radius" }
        isLength(definition.rEnd, { (millimeter) : [200, 430, 500] } as LengthBoundSpec);
    }
    {
        fCylinder(context, id + "rod", {
                    "bottomCenter" : vector(definition.rStart, 0 * millimeter, Z_CENTER * millimeter),
                    "topCenter" : vector(definition.rEnd, 0 * millimeter, Z_CENTER * millimeter),
                    "radius" : definition.channelD / 2
                });
        opBoolean(context, id + "cut", {
                    "tools" : qCreatedBy(id + "rod", EntityType.BODY),
                    "targets" : definition.blade,
                    "operationType" : BooleanOperationType.SUBTRACTION
                });
    });
