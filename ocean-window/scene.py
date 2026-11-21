"""'Window into the ocean' wall: 6 ft x 4 ft, Cairo-pentagon tiles, low-poly paint-by-number relief.

Wall coords (mm): x 0..W left->right, y 0..H bottom->top, z = relief height off the wall.
"""
import math
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from scipy.spatial import Delaunay
from shapely.geometry import Polygon, box, Point

W, H = 1828.8, 1219.2           # 6 ft x 4 ft
PX = 2.0                        # heightfield grid, mm per pixel
BASE = 3.0                      # tile thickness under the open ocean
GW, GH = int(W/PX)+1, int(H/PX)+1

PALETTE = {                     # paint-by-number colours
    1: ("Abyss navy",      "#0b1a33"),
    2: ("Deep blue",       "#14325c"),
    3: ("Ocean blue",      "#1f5b91"),
    4: ("Teal blue",       "#2c87ab"),
    5: ("Aqua",            "#5cb7cf"),
    6: ("Light aqua",      "#a6dbe5"),
    7: ("Foam white",      "#eef8fa"),
    8: ("Whale slate",     "#2b3d55"),
    9: ("Whale blue-grey", "#5a7898"),
    10: ("Whale pale",     "#a9bdcf"),
}
RGB = {k: np.array([int(v[1][i:i+2], 16) for i in (1, 3, 5)])/255 for k, v in PALETTE.items()}

# ------------------------------------------------------------------ blue whale side view
# fractions of body length L along the body (u) and offsets from the centreline
U   = [0, .01, .04, .10, .20, .30, .40, .50, .60, .70, .78, .85, .90, .95, .97]
TOP = [.004, .016, .028, .042, .055, .062, .064, .060, .052, .042, .032, .020, .015, .013, .012]
BOT = [-.008, -.022, -.038, -.058, -.072, -.077, -.074, -.066, -.055, -.042, -.030, -.018, -.014, -.012, -.011]

class Whale:
    def __init__(self, snout, length, angle_deg=-4, wave=.018, near=1.0, far=.82, relief=(26, 12), far_tone=0):
        self.s = np.array(snout, float); self.L = length
        self.a = math.radians(angle_deg); self.wave = wave
        self.near, self.far = near, far           # perspective scale head vs tail
        self.relief = relief                      # relief height head vs tail (mm)
        self.far_tone = far_tone                  # 0 = full colour, >0 = fades into the water

    def scale(self, u):
        return self.near + (self.far - self.near)*np.asarray(u)

    def pt(self, u, off):
        """Wall point for body fraction u (0 snout -> 1 fluke tips) and offset (fraction of L)."""
        u = np.asarray(u, float); off = np.asarray(off, float)
        # swim direction: snout points right (+x); body extends to the left
        along = -u*self.L
        cy = self.wave*self.L*np.sin(np.pi*(u - .15)/0.9) * u        # gentle body wave
        sc = self.scale(u)
        x, y = along, cy + off*self.L*sc
        c, s = math.cos(self.a), math.sin(self.a)
        return np.stack([self.s[0] + x*c - y*s, self.s[1] + x*s + y*c], -1)

    def body(self):
        u = np.linspace(0, .97, 90)
        top = self.pt(u, np.interp(u, U, TOP)); bot = self.pt(u, np.interp(u, U, BOT))
        return np.vstack([top, bot[::-1]])

    def dorsal(self):
        return np.array([self.pt(.74, .045), self.pt(.80, .058), self.pt(.82, .030), self.pt(.77, .03)]).reshape(-1, 2)

    def flukes(self):
        # seen slightly from above: two swept lobes
        pts = [(.95, .010), (1.0, .045), (1.06, .085), (1.035, .040), (1.045, .0), (1.035, -.040),
               (1.06, -.075), (1.0, -.040), (.95, -.010)]
        return np.array([self.pt(u, o) for u, o in pts]).reshape(-1, 2)

    def flipper(self):
        pts = [(.245, -.045), (.30, -.050), (.37, -.095), (.45, -.145), (.43, -.140),
               (.34, -.090), (.26, -.068)]
        return np.array([self.pt(u, o) for u, o in pts]).reshape(-1, 2)

    def mouth(self):
        u = np.linspace(0.005, .19, 20)
        return self.pt(u, -.006 - .012*np.sin(np.pi*u/.21) + .02*np.clip((u-.16)/.03, 0, 1))

    def eye(self):
        return self.pt(.205, .006)[0] if np.ndim(self.pt(.205, .006)) > 1 else self.pt(.205, .006)

    def pleats(self, n=9):
        lines = []
        for k in range(n):
            f = (k + 1)/(n + 1)
            u = np.linspace(.03 + .01*k, .44 - .015*abs(k - n/2), 24)
            mouth_off = -.006 - .012*np.sin(np.pi*np.clip(u, 0, .21)/.21)
            bot = np.interp(u, U, BOT)
            lines.append(self.pt(u, mouth_off + (bot - mouth_off)*(.18 + .78*f)))
        return lines

# main whale: big, near, swimming right and slightly up; distant companion behind
MAIN = Whale(snout=(1560, 610), length=1250, angle_deg=-5, near=1.0, far=.80, relief=(30, 13))
FAR = Whale(snout=(560, 905), length=430, angle_deg=3, near=1.0, far=.9, relief=(6, 4.5), far_tone=1)

def fish_school(seed=8, n=26, centre=(1330, 250), spread=(230, 95)):
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        cx = centre[0] + rng.normal(0, spread[0]/2); cy = centre[1] + rng.normal(0, spread[1]/2)
        L = rng.uniform(26, 40); a = math.radians(rng.uniform(-12, 8))
        body = [(0, 0), (-.45, .22), (-.8, .05), (-1.0, .2), (-1.0, -.2), (-.8, -.05), (-.45, -.22)]
        out.append([(cx + L*(x*math.cos(a) - y*math.sin(a)), cy + L*(x*math.sin(a) + y*math.cos(a))) for x, y in body])
    return out
FISH = fish_school()

# ------------------------------------------------------------------ rasterise helpers
def mask_of(polys, lw=0):
    img = Image.new("L", (GW, GH), 0); d = ImageDraw.Draw(img)
    for p in polys:
        q = [(x/PX, (H - y)/PX) for x, y in p]
        if lw: d.line(q, fill=255, width=max(1, int(lw/PX)), joint="curve")
        else: d.polygon(q, fill=255)
    return np.array(img) > 0

def inflate(mask, radius):
    d = ndimage.distance_transform_edt(mask)*PX
    t = np.clip(d/radius, 0, 1)
    return np.sqrt(1 - (1 - t)**2)                 # quarter-round profile -> rounded body

# grid coordinates (row 0 = top of wall)
YY, XX = np.mgrid[0:GH, 0:GW]
GX, GY = XX*PX, H - YY*PX

def whale_fields(wh):
    body = mask_of([wh.body()]); fl = mask_of([wh.flukes()]); dor = mask_of([wh.dorsal()])
    flip = mask_of([wh.flipper()])
    silh = body | fl | dor
    # u coordinate per pixel (projection onto the body axis) for head->tail relief falloff
    ax = np.array([math.cos(wh.a), math.sin(wh.a)])
    u = np.clip(((wh.s[0] - GX)*ax[0] + (wh.s[1] - GY)*ax[1]) / wh.L, 0, 1.1)
    hscale = np.interp(u, [0, 1], wh.relief)
    rad = 0.075*wh.L*np.interp(u, [0, .4, 1], [1, 1, .5])
    h = np.where(silh, inflate(silh, rad.mean())*hscale, 0)
    # flipper sits proud of the body
    hf = inflate(flip, 18)*hscale*.35 + np.where(flip, h + 2.0, 0)
    h = np.where(flip, np.maximum(h, hf), h)
    # grooves: mouth line + throat pleats (V grooves), eye dome
    groove = np.zeros_like(h)
    if wh.L > 800:
        gm = mask_of([wh.mouth()], lw=5) & silh
        groove = np.maximum(groove, gm*2.2)
        for ln in wh.pleats():
            gp = mask_of([ln], lw=4) & silh & ~flip
            groove = np.maximum(groove, gp*1.6)
        e = wh.eye(); de = np.hypot(GX - e[0], GY - e[1])
        h = h + np.where(de < 9, 2.2*np.sqrt(np.clip(1 - (de/9)**2, 0, 1)), 0)
    h = np.where(silh | flip, np.maximum(h - groove, .8), 0)
    return h, silh | flip, flip, u

def build_heightfield():
    hm, mm, flip_m, um = whale_fields(MAIN)
    hf, mf_, flip_f, uf = whale_fields(FAR)
    # open water: gentle surface ripples near the top, faint long swells elsewhere
    yn = GY/H
    water = .6*np.sin(GX/95 + 2*np.sin(GY/140))*np.clip((yn - .82)/.18, 0, 1)
    water += .35*np.sin(GX/260 - GY/180)
    h = BASE + 0.6 + water
    fm = mask_of(FISH)
    h = np.where(fm, BASE + 1.6, h)                # distant fish: barely raised
    h = np.where(mf_, BASE + 1.0 + hf, h)          # distant whale: low relief
    h = np.where(mm, BASE + hm, h)                 # main whale on top
    layer = np.where(mm, 2, np.where(mf_, 1, np.where(fm, 3, 0)))
    return h, layer, dict(main=(mm, flip_m, um), far=(mf_, flip_f, uf))

# ------------------------------------------------------------------ god rays (paint only)
SUN = np.array([420.0, 1900.0])
def ray_strength(x, y):
    a = np.arctan2(x - SUN[0], SUN[1] - y)
    k = (np.sin(a*23 + 1.3) + .6*np.sin(a*41 - .4) + .4*np.sin(a*67))/2.0
    fade = np.clip((y - 60)/(H - 60), 0, 1)**0.8
    return np.clip(k, 0, 1)*fade

_TONE_RNG = np.random.default_rng(5)
def water_tone(x, y):
    yn = y/H
    base = np.interp(yn, [0, .15, .35, .55, .75, .90, 1.0], [1.0, 1.4, 2.3, 3.2, 4.1, 5.0, 5.7])
    t = base + 1.4*ray_strength(x, y)
    lo = math.floor(t); frac = t - lo
    t = lo + (1 if _TONE_RNG.random() < frac else 0)      # dithered low-poly gradient
    return int(np.clip(t, 1, 7))

# ------------------------------------------------------------------ low-poly facets
def sample_points(fields, rng):
    mm, flip_m, um = fields["main"]; mf_, flip_f, uf = fields["far"]
    pts = []
    # background: coarse jittered lattice, a little finer near the surface
    for y in np.arange(0, H + 1, 46*.866):
        sp = 46 if y < .8*H else 34
        for x in np.arange(0, W + 1, sp):
            q = (x + rng.uniform(-.38, .38)*sp, y + rng.uniform(-.38, .38)*sp*.866)
            if 8 < q[0] < W - 8 and 8 < q[1] < H - 8: pts.append(q)
    # whale interiors: finer
    def fill(mask, sp):
        ys, xs = np.nonzero(mask)
        if not len(xs): return
        x0, x1 = xs.min()*PX, xs.max()*PX; y0, y1 = H - ys.max()*PX, H - ys.min()*PX
        for y in np.arange(y0, y1, sp*.866):
            for x in np.arange(x0, x1, sp):
                q = (x + rng.uniform(-.35, .35)*sp, y + rng.uniform(-.35, .35)*sp)
                i, j = int((H - q[1])/PX), int(q[0]/PX)
                if 0 <= i < GH and 0 <= j < GW and mask[i, j]: pts.append(q)
    fill(mm, 24); fill(mf_, 20)
    for fpoly in FISH:
        pts.extend([tuple(p) for p in fpoly])
    # crisp outlines + features
    for wh, sp in ((MAIN, 11), (FAR, 10)):
        for poly in (wh.body(), wh.flukes(), wh.dorsal(), wh.flipper()):
            P = Polygon(poly).buffer(0)
            ring = P.exterior
            for d in np.arange(0, ring.length, sp):
                p = ring.interpolate(d); pts.append((p.x, p.y))
                # second ring just outside so the relief edge is steep and clean
                q = P.buffer(3.5).exterior.interpolate(d/ring.length*P.buffer(3.5).exterior.length)
                pts.append((q.x, q.y))
    for ln in MAIN.pleats() + [MAIN.mouth()]:
        L = np.r_[0, np.cumsum(np.linalg.norm(np.diff(ln, axis=0), axis=1))]
        for d in np.arange(0, L[-1], 26):
            p = np.array([np.interp(d, L, ln[:, 0]), np.interp(d, L, ln[:, 1])])
            t = ln[min(np.searchsorted(L, d), len(ln)-1)] - ln[max(np.searchsorted(L, d)-1, 0)]
            n = np.array([-t[1], t[0]]); n /= np.linalg.norm(n) + 1e-9
            pts += [tuple(p)]
    e = MAIN.eye()
    for a in np.linspace(0, 2*np.pi, 8, endpoint=False):
        pts.append((e[0] + 9*math.cos(a), e[1] + 9*math.sin(a)))
    pts.append(tuple(e))
    for x in np.linspace(0, W, 48): pts += [(x, 0), (x, H)]
    for y in np.linspace(0, H, 32): pts += [(0, y), (W, y)]
    P = np.array(pts)
    P[:, 0] = np.clip(P[:, 0], 0, W); P[:, 1] = np.clip(P[:, 1], 0, H)
    return np.unique(np.round(P, 2), axis=0)

def hf_at(h, P):
    j = np.clip(P[:, 0]/PX, 0, GW - 1); i = np.clip((H - P[:, 1])/PX, 0, GH - 1)
    return ndimage.map_coordinates(h, [i, j], order=1, mode="nearest")

def facet_colour(c, layer, n, fields):
    x, y = c
    if layer == 0:
        return water_tone(x, y)
    if layer == 3:                                  # fish: silvery against the deep water
        return 4
    light = n @ np.array([-.25, .75, .62])/np.linalg.norm([-.25, .75, .62])
    if layer == 1:                                  # distant whale: dissolves into the water
        bg = water_tone(x, y)
        return int(np.clip(bg - 1 - (light > .7), 1, 7))
    mm, flip_m, um = fields["main"]
    i, j = int((H - y)/PX), int(x/PX)
    u = um[min(i, GH-1), min(j, GW-1)]
    # belly / throat region: below the mouth-line band
    off = ((MAIN.s[0] - x)*-math.sin(MAIN.a) + (y - MAIN.s[1])*math.cos(MAIN.a))/MAIN.L
    if flip_m[min(i, GH-1), min(j, GW-1)]:
        return 10 if light > .55 else 9
    if off < -.035 and u < .55:
        return 10 if light > .45 else 9
    if light > .82: return 10
    if light > .55: return 9
    return 8

def build_facets():
    rng = np.random.default_rng(11)
    h, layer, fields = build_heightfield()
    P = sample_points(fields, rng)
    tri = Delaunay(P)
    z = hf_at(h, P)
    facets = []
    for s in tri.simplices:
        p = P[s]; c = p.mean(0)
        i, j = int(np.clip((H - c[1])/PX, 0, GH-1)), int(np.clip(c[0]/PX, 0, GW-1))
        lay = int(layer[i, j])
        p3 = np.c_[p, z[s]]
        n = np.cross(p3[1] - p3[0], p3[2] - p3[0]); n /= np.linalg.norm(n) + 1e-12
        if n[2] < 0: n = -n
        facets.append(dict(pts=p, z=z[s], n=n, layer=lay, color=facet_colour(c, lay, n, fields)))
    return facets, h, P, tri.simplices, z

# ------------------------------------------------------------------ Cairo pentagon tiling
CAIRO_C = (-2 + math.sqrt(28))/6            # equilateral Cairo pentagon (all 5 sides equal)

def cairo_tiles(scale, origin=(0, 0)):
    """Cairo tiling: short edges at lattice points (2i,2j), alternating orientation."""
    c = CAIRO_C
    tiles = []
    ni, nj = int(W/(2*scale)) + 3, int(H/(2*scale)) + 3
    for i in range(-2, ni):
        for j in range(-2, nj):
            cx, cy = 2*i, 2*j
            if (i + j) % 2 == 0:            # horizontal short edge -> pentagons above and below
                for sg in (1, -1):
                    v = [(cx - c, cy), (cx + c, cy), (cx + 1, cy + sg), (cx, cy + sg*(2 - c)), (cx - 1, cy + sg)]
                    tiles.append(v)
            else:                           # vertical short edge -> pentagons left and right
                for sg in (1, -1):
                    v = [(cx, cy - c), (cx, cy + c), (cx + sg, cy + 1), (cx + sg*(2 - c), cy), (cx + sg, cy - 1)]
                    tiles.append(v)
    out, seen = [], set()
    wall = box(0, 0, W, H)
    for v in tiles:
        P = Polygon([(origin[0] + x*scale, origin[1] + y*scale) for x, y in v]).buffer(0)
        key = tuple(np.round(np.array(P.centroid.coords[0]), 1))
        if key in seen: continue
        seen.add(key)
        Q = P.intersection(wall)
        if Q.is_empty or Q.area < 0.04*P.area: continue
        out.append(dict(full=P, poly=Q, partial=Q.area < .995*P.area))
    # install order: bottom row first, left -> right, working up (tiles rest on the row below)
    rowh = scale*1.0
    out.sort(key=lambda t: (round(t["poly"].centroid.y/rowh), t["poly"].centroid.x))
    for k, t in enumerate(out):
        t["num"] = k + 1
    return out
