"""NACA 6407 coordinates + per-station blade numbers for the BP-100 redesign."""

import math

M, P, T = 0.06, 0.40, 0.07  # camber, camber pos, thickness


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
        T
        / 0.2
        * (
            0.2969 * math.sqrt(x)
            - 0.1260 * x
            - 0.3516 * x**2
            + 0.2843 * x**3
            - 0.1036 * x**4  # closed trailing edge
        )
    )


# cosine spacing, 16 points per surface
n = 16
xs = [0.5 * (1 - math.cos(math.pi * i / (n - 1))) for i in range(n)]

upper, lower = [], []
for x in xs:
    yc, dyc = camber(x)
    yt = thickness(x)
    th = math.atan(dyc)
    upper.append((x - yt * math.sin(th), yc + yt * math.cos(th)))
    lower.append((x + yt * math.sin(th), yc - yt * math.cos(th)))

print("NACA 6407 normalized (x/c, y/c), TE->LE upper then LE->TE lower:")
pts = list(reversed(upper)) + lower[1:]
for x, y in pts:
    print(f"  {x:7.4f}, {y:8.4f}")

# per-station table
stations = [  # r, chord, twist deg
    (110, 78, 17.0),
    (180, 100, 15.0),
    (250, 118, 13.0),
    (330, 112, 11.5),
    (420, 94, 10.0),
    (500, 76, 9.0),
    (556, 40, 8.5),
]
print("\nstation table: r, c, twist, t_max mm, LE offset (+0.3c), TE offset (-0.7c),")
print("vertical extent about pitch axis (Z up +, mm), Z_upper/Z_lower abs (center Z223.5)")
for r, c, tw in stations:
    tmax = T * c
    le, te = 0.30 * c, -0.70 * c
    rad = math.radians(tw)
    # crude vertical extents: rotate section pts about 30% chord point
    zmin = zmax = 0.0
    for x, y in pts:
        dx = (x - 0.30) * c
        dy = y * c
        z = -dx * math.sin(rad) + dy * math.cos(rad)  # LE rotates up
        zmin, zmax = min(zmin, z), max(zmax, z)
    print(
        f"  r{r:5.0f}  c={c:5.1f}  tw={tw:4.1f}  t={tmax:4.1f}  LE=+{le:5.1f}  TE={te:6.1f}"
        f"  up {zmax:5.1f} / dn {zmin:6.1f}  ->  Z {223.5 - zmax:5.1f} / {223.5 - zmin:5.1f}"
    )

# rod channel wall check: 3.4 mm channel at 30% chord (near max thickness)
print("\nrod channel wall at Ø3.4, rod ends r470:")
for r, c, tw in stations:
    if r > 470:
        continue
    # thickness at x=0.30
    yt = thickness(0.30) * c
    wall = (2 * yt - 3.4) / 2
    print(f"  r{r:5.0f}: section depth {2*yt:4.1f} mm, wall {wall:4.2f} mm/side")

# tip speed / Re sanity
for rpm in (60, 170):
    v = 2 * math.pi * 0.5588 * rpm / 60
    re = v * 0.118 / 1.5e-5
    print(f"\n{rpm} RPM: tip speed {v:.1f} m/s, Re at max chord ~{re:,.0f}")
