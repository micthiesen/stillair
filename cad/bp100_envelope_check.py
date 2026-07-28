"""Re-check BP-100 envelope with sections anchored by the camber point at 30% chord."""

import math

M, P, T = 0.06, 0.40, 0.07
YC30 = M / P**2 * (2 * P * 0.30 - 0.30**2)  # camber-line height at x/c = 0.30

stations = [  # r, chord, twist deg, y-shift, z-raise
    (110, 78, 17.0, 0, 0),
    (180, 100, 15.0, 0, 0),
    (250, 118, 13.0, 0, 0),
    (330, 112, 11.5, 0, 0),
    (420, 94, 10.0, 0, 0),
    (500, 76, 9.0, 0, 3),
    (556, 40, 8.5, -6, 6),
    (557.5, 14, 8.5, -10, 8),
]


def camber(x):
    if x < P:
        yc = M / P**2 * (2 * P * x - x * x)
        dyc = 2 * M / P**2 * (P - x)
    else:
        yc = M / (1 - P) ** 2 * ((1 - 2 * P) + 2 * P * x - x * x)
        dyc = 2 * M / (1 - P) ** 2 * (P - x)
    return yc, dyc


def thickness(x):
    return (
        T / 0.2
        * (0.2969 * math.sqrt(x) - 0.1260 * x - 0.3516 * x**2 + 0.2843 * x**3 - 0.1036 * x**4)
    )


def section_pts(c, tw, ys, zr):
    """Draped section points in plane coords (h toward LE, v toward ceiling)."""
    th = math.radians(tw)
    u = (-math.cos(th), -math.sin(th))
    v = (-math.sin(th), math.cos(th))
    le = (
        ys + 0.3 * c * math.cos(th) - YC30 * c * v[0],
        zr + 0.3 * c * math.sin(th) - YC30 * c * v[1],
    )
    pts = []
    n = 40
    for i in range(n):
        x = 0.5 * (1 - math.cos(math.pi * i / (n - 1)))
        yc, dyc = camber(x)
        yt = thickness(x)
        a = math.atan(dyc)
        for sgn in (1, -1):
            px = x - sgn * yt * math.sin(a)
            py = yc + sgn * yt * math.cos(a)
            pts.append(
                (le[0] + px * c * u[0] + py * c * v[0], le[1] + px * c * u[1] + py * c * v[1])
            )
    return pts


print(f"camber offset yc(0.30) = {YC30:.5f} c\n")
print("station extents (v = up toward ceiling, project Z = 223.5 - v):")
for r, c, tw, ys, zr in stations:
    pts = section_pts(c, tw, ys, zr)
    vmax = max(p[1] for p in pts)
    vmin = min(p[1] for p in pts)
    print(
        f"  r{r:6.1f}: up {vmax:6.1f} / dn {vmin:6.1f}  ->  Z {223.5 - vmax:6.1f} / {223.5 - vmin:6.1f}"
    )

# rod wall check: channel Ø3.4 centered at origin of each station's plane coords
print("\nrod fit (distance from origin to nearest surface point must exceed 1.7 + wall):")
for r, c, tw, ys, zr in stations[:6]:
    pts = section_pts(c, tw, ys, zr)
    # min distance from origin to the section outline (sampled)
    d = min(math.hypot(px, pv) for px, pv in pts)
    print(f"  r{r:6.1f}: nearest surface {d:5.2f} mm from spar axis -> wall {d - 1.7:5.2f} mm")

# raise interpolation kills the lower wall outboard; find where wall hits 1.0 mm
print("\ninterpolated wall along candidate rod span (linear station interp):")
import bisect

rs = [s[0] for s in stations]
for r in (420, 430, 440, 450, 460, 470):
    i = bisect.bisect_right(rs, r) - 1
    r0, c0, t0, y0, z0 = stations[i]
    r1, c1, t1, y1, z1 = stations[min(i + 1, len(stations) - 1)]
    f = 0 if r1 == r0 else (r - r0) / (r1 - r0)
    c = c0 + f * (c1 - c0)
    tw = t0 + f * (t1 - t0)
    ys = y0 + f * (y1 - y0)
    zr = z0 + f * (z1 - z0)
    pts = section_pts(c, tw, ys, zr)
    d = min(math.hypot(px, pv) for px, pv in pts)
    print(f"  r{r}: wall {d - 1.7:5.2f} mm (raise {zr:.2f})")

# pad region: lowest surface point with horizontal coord in the pad footprint
print("\npad-region lower surface (h in [-40, +18]), stations r110/r180 + r192 interp:")
for r, c, tw, ys, zr in [stations[0], stations[1]]:
    pts = section_pts(c, tw, ys, zr)
    vmin = min(pv for ph, pv in pts if -40 <= ph <= 18)
    vall = min(pv for ph, pv in pts)
    print(f"  r{r}: min v in footprint {vmin:6.1f} (full-section min {vall:6.1f}) -> Z {223.5 - vmin:.1f}")
