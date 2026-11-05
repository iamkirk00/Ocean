"""Blue whale bursting OUT of the wall: a low-poly height-field relief cut into hex tiles.

Units: mm. x right, y DOWN (image coords), z = height off the wall (toward the room).
The same height field feeds the preview renders and the STL export, so the print
matches the picture.
"""
import math
import numpy as np
from scipy.spatial import Delaunay
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union

HEX_F = 100.0                    # hex size, flat-to-flat (mm)
HEX_R = HEX_F / math.sqrt(3)
BASE = 3.0                       # flat back plate thickness under every tile (mm)

FIL = {"navy": "#16244a", "ocean": "#2f6fb8", "sky": "#93c9ec", "white": "#f3f7fb"}

PORTAL = np.array([545.0, 395.0])   # where the body disappears into the wall

# ---------------------------------------------------------------- whale body (view space)
# Chain of ellipsoid blobs, snout -> into the wall. Each: centre xy, z0 (centre height),
# rx (along body), ry (across), rz (depth), body-axis angle. Foreshortened: near = big.
AX = math.atan2(-1.0, 1.15)         # body axis points up-right, back into the wall
BLOBS = [
    # cx,  cy,  z0,  rx,  ry,  rz   (head first)
    (300, 625,  30, 150, 128,  52),   # broad flat U-shaped head, closest to the room
    (352, 660,  18, 125, 100,  46),   # lower jaw + throat pleats (ventral bulge)
    (420, 545,  20, 150, 135,  50),   # chest
    (500, 455,   2, 140, 118,  44),   # mid body
    (570, 380, -24, 120,  95,  38),   # disappearing into the wall
]

def _blob_h(x, y, b):
    cx, cy, z0, rx, ry, rz = b
    dx, dy = x - cx, y - cy
    c, s = math.cos(AX), math.sin(AX)
    u = (dx*c + dy*s) / rx
    v = (-dx*s + dy*c) / ry
    q = 1 - u*u - v*v
    return np.where(q > 0, z0 + rz*np.sqrt(np.clip(q, 0, 1)), -1e3)

def smax(a, b, k=10.0):
    h = np.clip(0.5 + 0.5*(a - b)/k, 0, 1)
    return a*h + b*(1-h) + k*h*(1-h)

def whale_h(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    h = _blob_h(x, y, BLOBS[0])
    for b in BLOBS[1:]:
        h = smax(h, _blob_h(x, y, b), 14.0)
    return h

# ---- flippers: long thin blue-whale pectoral fins, flat ellipsoids
def _fin_h(x, y, root, tip, width, zr, zt, thick):
    x = np.asarray(x, float); y = np.asarray(y, float)
    root, tip = np.asarray(root, float), np.asarray(tip, float)
    d = tip - root; L = np.linalg.norm(d); d /= L
    n = np.array([-d[1], d[0]])
    px, py = x - root[0], y - root[1]
    t = (px*d[0] + py*d[1]) / L
    w = width * np.clip(np.interp(t, [-.05, 0, .25, .7, 1], [0, .8, 1, .55, 0]), 0, 1) + 1e-6
    off = (px*n[0] + py*n[1]) - 10*np.sin(np.pi*np.clip(t, 0, 1))      # gentle sweep
    q = 1 - (off/w)**2
    ok = (t > -.05) & (t < 1) & (q > 0)
    return np.where(ok, zr + (zt - zr)*np.clip(t, 0, 1) + thick*np.sqrt(np.clip(q, 0, 1)), -1e3)

FIN_NEAR = dict(root=(470, 650), tip=(655, 815), width=32, zr=56, zt=36, thick=8)
FIN_FAR = dict(root=(300, 520), tip=(175, 455), width=22, zr=18, zt=8, thick=5)

def fins_h(x, y):
    return np.maximum(_fin_h(x, y, **FIN_NEAR), _fin_h(x, y, **FIN_FAR))

# ---------------------------------------------------------------- splash crown + wall ripples
RNG = np.random.default_rng(3)
N_SPIKES = 34
SPK_ANG = np.sort(RNG.uniform(0, 2*np.pi, N_SPIKES))
SPK_LEN = RNG.uniform(90, 260, N_SPIKES)
SPK_W = RNG.uniform(.10, .20, N_SPIKES)

def splash_h(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    dx, dy = x - PORTAL[0], y - PORTAL[1]
    r = np.hypot(dx, dy); a = np.arctan2(dy, dx)
    R0 = 165.0
    # crown wall right around the hole
    crown = 20*np.exp(-((r - R0)/28)**2)
    # radial spikes flung outward
    spikes = np.zeros_like(r)
    for ang, L, w in zip(SPK_ANG, SPK_LEN, SPK_W):
        da = np.angle(np.exp(1j*(a - ang)))
        t = (r - R0) / L
        width = w * (1 - np.clip(t, 0, 1))
        on = (t > -0.2) & (t < 1) & (np.abs(da) < width)
        prof = 30*(1 - np.clip(t, 0, 1))**1.1 * (1 - np.abs(da)/np.maximum(width, 1e-6))
        spikes = np.maximum(spikes, np.where(on, prof, 0))
    return np.maximum(crown, spikes)

def wall_h(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    r = np.hypot(x - PORTAL[0], y - PORTAL[1])
    return 1.2 + 1.0*np.cos(r / 38.0) * np.exp(-r/600)       # faint concentric ripples

# droplets: little raised gems flung out past the crown
DROPS = []
for _ in range(30):
    a = RNG.uniform(0, 2*np.pi); r = RNG.uniform(260, 470)
    DROPS.append((PORTAL[0] + r*math.cos(a)*1.1, PORTAL[1] + r*math.sin(a), RNG.uniform(6, 11)))

def drops_h(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    h = np.full_like(x, -1e3)
    for cx, cy, s in DROPS:
        d = np.maximum(np.abs(x-cx), np.abs(y-cy)*1.25) + 0.6*np.minimum(np.abs(x-cx), np.abs(y-cy))
        h = np.maximum(h, np.where(d < s, 7.0*(1 - d/s) + 3, -1e3))
    return h

# ---------------------------------------------------------------- combined field
LAYERS = ["wall", "splash", "drops", "whale", "fin"]

def field(x, y):
    """Return (height, layer index) of the visible surface at x, y."""
    sp = splash_h(x, y)
    hs = np.stack([wall_h(x, y), np.where(sp > 0.8, sp + 1.2, -1e3), drops_h(x, y), whale_h(x, y), fins_h(x, y)])
    return hs.max(0), hs.argmax(0), hs

# ---------------------------------------------------------------- incised details on the whale
def details():
    """Polylines carved ~1.5 mm into the whale (mouth line, throat pleats, eye)."""
    lines = []
    # mouth line: from snout tip along the lower-right side of the head, up to the eye
    lines.append((np.array([(212, 690), (250, 707), (300, 712), (352, 700), (398, 676), (430, 646)]), 3.2))
    # throat pleats below the mouth line, running back along the body
    for k in range(5):
        o = 14 + 13*k
        lines.append((np.array([(250 + 6*k, 710 + o*.9), (310, 724 + o), (372, 716 + o*.85),
                                (430, 690 + o*.7), (478, 652 + o*.55)]), 2.0))
    eye = (446, 632)
    return lines, eye

# ---------------------------------------------------------------- hexes
def hex_poly(cx, cy, inset=0.0):
    R = HEX_R - inset/math.cos(math.pi/6)
    return Polygon([(cx + R*math.cos(math.radians(30 + 60*i)),
                     cy + R*math.sin(math.radians(30 + 60*i))) for i in range(6)])

def build_hexes():
    # footprint of the art = wherever anything rises meaningfully off the wall
    xs, ys = np.meshgrid(np.arange(0, 1000, 8.0), np.arange(0, 1000, 8.0))
    h, lay, _ = field(xs.ravel(), ys.ravel())
    hot = (lay >= 1) & (h > 3)
    pts = np.c_[xs.ravel()[hot], ys.ravel()[hot]]
    art = unary_union([Point(p).buffer(6) for p in pts[::2]])
    halo = art.buffer(30)
    dy = 1.5*HEX_R
    hexes = []
    for r in range(13):
        cy = -20 + r*dy
        off = 0 if r % 2 == 0 else HEX_F/2
        for c in range(12):
            cx = -20 + off + c*HEX_F
            hp = hex_poly(cx, cy)
            if hp.intersection(halo).area / hp.area > 0.28:
                hexes.append(dict(row=r, col=c, cx=cx, cy=cy, poly=hp))
    rows = sorted({h["row"] for h in hexes})
    cmin = min(h["col"] for h in hexes)
    for h in hexes:
        h["label"] = f"{chr(65 + rows.index(h['row']))}{h['col'] - cmin + 1}"
    return hexes

# ---------------------------------------------------------------- low-poly mesh
def lowpoly(region):
    """Jittered points over the region, denser on the whale, Delaunay -> facets."""
    rng = np.random.default_rng(42)
    minx, miny, maxx, maxy = region.bounds
    pts = []
    for sp, sel in [(34.0, None), (24.0, "whale")]:
        for yy in np.arange(miny, maxy + sp, sp*0.866):
            for xx in np.arange(minx, maxx + sp, sp):
                pts.append((xx + rng.uniform(-.4, .4)*sp, yy + rng.uniform(-.4, .4)*sp, sel))
    P = []
    for x, y, sel in pts:
        if sel == "whale":
            _, lay, _ = field(np.array([x]), np.array([y]))
            if lay[0] < 3: continue
        P.append((x, y))
    # crisp silhouettes: sample along whale + fin outlines (contour of layer change)
    xs, ys = np.meshgrid(np.arange(minx, maxx, 4.0), np.arange(miny, maxy, 4.0))
    _, lay, _ = field(xs.ravel(), ys.ravel())
    lay = lay.reshape(xs.shape)
    edge = (lay >= 3) & ((np.roll(lay, 1, 0) < 3) | (np.roll(lay, 1, 1) < 3) |
                         (np.roll(lay, -1, 0) < 3) | (np.roll(lay, -1, 1) < 3))
    E = np.c_[xs[edge], ys[edge]]
    if len(E):
        E = E[rng.permutation(len(E))]
        keep = []
        for e in E:
            if all(np.hypot(*(e - k)) > 15 for k in keep[-80:]):
                keep.append(e)
        P += [tuple(k) for k in keep]
    P = np.array(P)
    tri = Delaunay(P)
    z, lay, _ = field(P[:, 0], P[:, 1])
    return P, tri.simplices, z, lay

def facet_color(c, zc, lay, normal, rng):
    x, y = c
    L = LAYERS[lay]
    r = rng.random()
    if L == "wall":
        d = np.hypot(x - PORTAL[0], y - PORTAL[1])
        return "ocean" if r < max(0.05, 0.55 - d/600) else "navy"
    if L in ("splash", "drops"):
        return "white" if (zc > 12 or L == "drops") and r < .8 else "sky"
    if L == "fin":
        return "white" if normal[0] + normal[1] > 0.35 else "sky"
    # whale: back (facing up-left) ocean blue, flank mixed, belly/throat pale
    vent = normal[0]*0.7 + normal[1]*0.7
    if vent > 0.30 or (lay == 3 and _throat(x, y)):
        return "sky" if r < .8 else "white"
    if vent > 0.05:
        return "ocean" if r < .55 else "sky"
    return "ocean"

def _throat(x, y):
    return y > 690 - 0.25*(x - 250) and x < 480


def build():
    hexes = build_hexes()
    region = unary_union([h["poly"] for h in hexes]).buffer(4)
    P, T, z, lay = lowpoly(region)
    rng = np.random.default_rng(9)
    facets = []
    for s in T:
        p3 = np.c_[P[s], z[s]]
        n = np.cross(p3[1]-p3[0], p3[2]-p3[0]); n /= np.linalg.norm(n) + 1e-9
        if n[2] < 0: n = -n
        c = P[s].mean(0)
        _, lc, _ = field(np.array([c[0]]), np.array([c[1]]))
        facets.append(dict(pts=P[s], z=z[s], n=n, layer=int(lc[0]),
                           color=facet_color(c, z[s].mean(), int(lc[0]), n, rng)))
    lines, eye = details()
    whale_area = unary_union([Polygon(f["pts"]) for f in facets if f["layer"] == 3]).buffer(-4)
    return dict(hexes=hexes, facets=facets, whale_area=whale_area, lines=lines, eye=eye, P=P, T=T, z=z)
