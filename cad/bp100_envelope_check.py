"""BP-100 v3 (integrated root, no adapter) geometry cross-check.

v3 changes vs v2: first station moves r110 -> r120 (rectangle root r52-96 +
transition loft r96-120); proplet flips downward (zr negative, away from the
ceiling now that the gap is hugger-class); pitch/rod plane = hub underside
+ 6 (rectangle mid-thickness), project Z 124.2 at #standoffLen 62.
"""

import bisect
import math

M, P, T = 0.06, 0.40, 0.07
YC30 = M / P**2 * (2 * P * 0.30 - 0.30**2)  # camber-line height at x/c = 0.30

PITCH_Z = 124.2  # project Z of the rod/pitch plane (hub underside 118.2 + 6)
HUB_UNDER = 118.2
RECT_T = 12.0
RECT_TOP = HUB_UNDER  # rectangle top face flush on hub underside
RECT_BOT = HUB_UNDER + RECT_T

stations = [  # r, chord, twist deg, y-shift, z-raise (+ = toward ceiling)
    (120, 81, 16.7, 0, 0),
    (180, 100, 15.0, 0, 0),
    (250, 118, 13.0, 0, 0),
    (330, 112, 11.5, 0, 0),
    (420, 94, 10.0, 0, 0),
    (500, 76, 9.0, 0, -3),
    (556, 40, 8.5, -6, -6),
    (557.5, 18, 8.5, -7, -6.4),
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


def interp_station(r):
    rs = [s[0] for s in stations]
    i = bisect.bisect_right(rs, r) - 1
    i = max(0, min(i, len(stations) - 2))
    r0, c0, t0, y0, z0 = stations[i]
    r1, c1, t1, y1, z1 = stations[i + 1]
    f = 0 if r1 == r0 else (r - r0) / (r1 - r0)
    return (
        c0 + f * (c1 - c0),
        t0 + f * (t1 - t0),
        y0 + f * (y1 - y0),
        z0 + f * (z1 - z0),
    )


print(f"camber offset yc(0.30) = {YC30:.5f} c")
print(f"pitch/rod plane project Z = {PITCH_Z}\n")

print("station extents (v = up toward ceiling, project Z = PITCH_Z - v):")
worst_up, worst_dn = -1e9, 1e9
for r, c, tw, ys, zr in stations:
    pts = section_pts(c, tw, ys, zr)
    vmax = max(p[1] for p in pts)
    vmin = min(p[1] for p in pts)
    worst_up = max(worst_up, vmax)
    worst_dn = min(worst_dn, vmin)
    print(
        f"  r{r:6.1f}: up {vmax:6.1f} / dn {vmin:6.1f}  ->  Z {PITCH_Z - vmax:6.1f} / {PITCH_Z - vmin:6.1f}"
    )
print(f"  blade highest Z {PITCH_Z - worst_up:.1f} (ceiling gap {PITCH_Z - worst_up:.1f} mm)")
print(f"  blade lowest  Z {PITCH_Z - worst_dn:.1f} (doors need <= ~160)")

print("\nrod fit (nearest surface to spar axis; wall = d - 1.7):")
for r, c, tw, ys, zr in stations[:6]:
    pts = section_pts(c, tw, ys, zr)
    d = min(math.hypot(px, pv) for px, pv in pts)
    print(f"  r{r:6.1f}: nearest surface {d:5.2f} mm -> wall {d - 1.7:5.2f} mm")

print("\ninterpolated wall along candidate rod span (droop now kills the *upper* wall):")
for r in (420, 430, 440, 450, 460, 470):
    c, tw, ys, zr = interp_station(r)
    pts = section_pts(c, tw, ys, zr)
    d = min(math.hypot(px, pv) for px, pv in pts)
    print(f"  r{r}: wall {d - 1.7:5.2f} mm (raise {zr:.2f})")

print("\nrectangle root (r52-96 x y+/-25, t12):")
corner = math.hypot(96, 25)
print(f"  outer corner radius {corner:.1f} vs hub OD r100 -> {'inside' if corner < 100 else 'POKES OUT'}")
chan_top = RECT_T / 2 - 1.7
chan_bot = RECT_T / 2 + 1.7
print(f"  rod channel band {chan_top:.1f}-{chan_bot:.1f} from top face")
print(f"  nut pocket (5.0 deep from underside) floor at {RECT_T - 5.0:.1f} from top; at y+/-15, channel at y0 -> no overlap")
print(f"  balance pocket top face 2.0 deep -> web to channel top {chan_top - 2.0:.1f} mm")
print(f"  rectangle bottom Z {RECT_BOT}; nut bottom Z 141.7; spindle end Z 144.0 (all above blade lowest)")

print("\ntransition r96 -> r120 (lateral flare of TE):")
c, tw, ys, zr = stations[0][1], stations[0][2], stations[0][3], stations[0][4]
pts = section_pts(c, tw, ys, zr)
hmin = min(ph for ph, pv in pts)
hmax = max(ph for ph, pv in pts)
print(f"  r120 section spans h {hmin:.1f} .. {hmax:.1f} vs rectangle y +/-25")
print(f"  TE flare {abs(hmin) - 25:.1f} mm over 24 mm radial ({math.degrees(math.atan((abs(hmin) - 25) / 24)):.0f} deg off-radial)")
