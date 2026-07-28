FeatureScript 1560;
import(path : "onshape/std/geometry.fs", version : "1560.0");

// BP-100 blade sections (see docs/blade-v2.md).
// Drapes a NACA 6407 section onto each selected chord line: scaled to the line's
// length, LE at the ceiling-ward (higher-Z) endpoint, camber side toward +Z.
// Assumes the chord lines live on vertical planes (station planes offset along X),
// which is how the blade Part Studio is built.

const M = 0.06;  // max camber
const P = 0.40;  // camber position
const T = 0.07;  // thickness
const N = 30;    // points per surface

annotation { "Feature Type Name" : "BP-100 airfoil sections" }
export const bp100Sections = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
        annotation { "Name" : "Chord lines", "Filter" : EntityType.EDGE && SketchObject.YES, "MaxNumberOfPicks" : 12 }
        definition.chords is Query;
        annotation { "Name" : "TE thickness" }
        isLength(definition.teGap, { (millimeter) : [0, 0.6, 3] } as LengthBoundSpec);
    }
    {
        const edges = evaluateQuery(context, definition.chords);
        var i = 0;
        for (var e in edges)
        {
            const plane = evOwnerSketchPlane(context, { "entity" : e });
            const lines = evEdgeTangentLines(context, { "edge" : e, "parameters" : [0, 1] });
            const p0 = lines[0].origin;
            const p1 = lines[1].origin;
            // LE is the ceiling-ward endpoint at every station of this blade
            var le = p0;
            var te = p1;
            if (p1[2] > p0[2])
            {
                le = p1;
                te = p0;
            }
            const c = norm(te - le);
            const u = normalize(te - le);           // chordwise, LE -> TE
            var v = vector(0, 0, 1) - dot(vector(0, 0, 1), u) * u;
            v = normalize(v);                       // toward ceiling, perpendicular to chord
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
                        + 0.5 * gapRel * x;         // linear opening to the TE gap
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
            {
                const world = le + (p[0] * c) * u + (p[1] * c) * v;
                sketchPts = append(sketchPts, worldToPlane(plane, world));
            }

            var sk = newSketchOnPlane(context, id + ("station" ~ toString(i)), { "sketchPlane" : plane });
            skFitSpline(sk, "foil", { "points" : sketchPts });
            skLineSegment(sk, "te", { "start" : sketchPts[size(sketchPts) - 1], "end" : sketchPts[0] });
            skSolve(sk);
            i += 1;
        }
    });
