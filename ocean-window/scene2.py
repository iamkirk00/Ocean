"""v2: a smaller 'sunken window' into the ocean. A raised frame is the wall/glass plane; the whale
passes just behind it, too big to fit the opening, close enough to see its throat pleats.

Wall coords (mm): x 0..W, y 0..H (up), z = height off the wall.
"""
import math
import numpy as np
from scipy import ndimage
from scipy.spatial import Delaunay
from shapely.geometry import Polygon, box
import scene as S1                                 # reuse whale shape, tiling, helpers

W, H = 1219.2, 762.0           # 48" x 30" overall, frame included
PX = 2.0
GW, GH = int(W/PX)+1, int(H/PX)+1
BASE = 3.0                     # open water
FRAME_W = 45.0                 # frame width (flat top + inner bevel)
FRAME_TOP = 22.0               # the frame = the wall/glass plane: highest thing on the piece
BEVEL = 28.0                   # inner bevel (the 'reveal' you look past into the water)
WHALE_NEAR = 19.0              # whale's nearest point: just behind the glass

PALETTE = dict(S1.PALETTE)
PALETTE[11] = ("Frame (your wall colour)", "#e9e4dc")
PALETTE[12] = ("Reveal shadow",            "#9a948a")
RGB = {k: np.array([int(v[1][i:i+2], 16) for i in (1, 3, 5)])/255 for k, v in PALETTE.items()}

INNER = (FRAME_W, FRAME_W, W - FRAME_W, H - FRAME_W)

# ------------------------------------------------------------------ whale: big and close
class BigWhale(S1.Whale):
    pass
# body length 2.3 m: only head + front of the body fit; it exits behind the left frame edge
MAIN = BigWhale(snout=(1050, 395), length=2300, angle_deg=-6, wave=.010, near=1.0, far=.86,
                relief=(WHALE_NEAR - BASE, 9), far_tone=0)
FAR = S1.Whale(snout=(470, 610), length=300, angle_deg=4, near=1.0, far=.92, relief=(3.5, 2.5), far_tone=1)

YY, XX = np.mgrid[0:GH, 0:GW]
GX, GY = XX*PX, H - YY*PX

def mask_of(polys, lw=0):
    from PIL import Image, ImageDraw
    img = Image.new("L", (GW, GH), 0); d = ImageDraw.Draw(img)
    for p in polys:
        q = [(x/PX, (H - y)/PX) for x, y in p]
        if lw: d.line(q, fill=255, width=max(1, int(lw/PX)), joint="curve")
        else: d.polygon(q, fill=255)
    return np.array(img) > 0

def whale_coords(wh):
    """Per-pixel body coordinates: u along the body, off = signed offset / L (dorsal +)."""
    ax = np.array([math.cos(wh.a), math.sin(wh.a)]); nx = np.array([-ax[1], ax[0]])
    dx, dy = GX - wh.s[0], GY - wh.s[1]
    u = np.clip(-(dx*ax[0] + dy*ax[1])/wh.L, 0, 1.2)
    cy = wh.wave*wh.L*np.sin(np.pi*(u - .15)/0.9)*u
    off = ((dx*nx[0] + dy*nx[1]) - cy)/(wh.L*wh.scale(u))
    return u, off

def mouth_off(u):
    return -.006 - .012*np.sin(np.pi*np.clip(u, 0, .21)/.21) + .02*np.clip((u - .16)/.03, 0, 1)

N_PLEATS = 11
def throat_top(u):
    u = np.asarray(u, float)
    m = -.006 - .012*np.sin(np.pi*np.clip(u, 0, .21)/.21)
    return np.where(u < .17, m, np.interp(u, [.17, .24, .5], [-.006 - .012*np.sin(np.pi*.17/.21), -.024, -.030]))

def pleat_v(u, off):
    m = throat_top(u); b = np.interp(u, S1.U, S1.BOT)
    return (m - off)/np.maximum(m - b, 1e-6)       # 0 at the mouth line, 1 at the belly edge

def whale_height(wh, big=True):
    body = mask_of([wh.body()]); fl = mask_of([wh.flukes()]); dor = mask_of([wh.dorsal()])
    flip = mask_of([wh.flipper()])
    silh = body | fl | dor
    u, off = whale_coords(wh)
    hs = np.interp(u, [0, .5, 1], [wh.relief[0], wh.relief[0]*.85, wh.relief[1]])
    d = ndimage.distance_transform_edt(silh)*PX
    rad = 0.07*wh.L
    t = np.clip(d/rad, 0, 1)
    h = np.where(silh, np.sqrt(1 - (1 - t)**2)*hs, 0)
    if big:
        # throat pleats: rounded ridges between the mouth line and the belly, chin -> navel
        v = pleat_v(u, off)
        zone = silh & (v > 0.04) & (v < 1.02) & (u > .015) & (u < .50)
        fade = np.clip((u - .015)/.03, 0, 1)*np.clip((.50 - u)/.08, 0, 1)*np.clip(v/0.08, 0, 1)
        ridge = 0.5 + 0.5*np.cos(2*np.pi*N_PLEATS*v)
        h = np.where(zone, h - 2.6*(1 - ridge)*fade, h)
        # mouth line: a crisp groove, and the lip above it slightly proud
        dm = np.abs(off - throat_top(u))*wh.L*wh.scale(u)
        lip = silh & (u < .185) & (dm < 6)
        h = np.where(lip, h - 3.0*np.clip(1 - dm/6, 0, 1), h)
        # eye + brow
        e = wh.pt(.205, .006)
        de = np.hypot(GX - e[0], GY - e[1])
        h = h + np.where(de < 16, 2.0*np.sqrt(np.clip(1 - (de/16)**2, 0, 1)), 0)
        # splash-guard ridge in front of the blowhole (top of the head)
        dg = np.hypot((u - .13)/.03, (off - .05)/.01)
        h = h + np.where(silh & (dg < 1), 1.8*(1 - dg), 0)
    # flipper rides proud of the body
    hf = np.where(flip, np.maximum(h, 0) + 2.5 + 4*np.clip(ndimage.distance_transform_edt(flip)*PX/14, 0, 1), 0)
    h = np.where(flip, np.maximum(h, hf), h)
    return np.where(silh | flip, np.maximum(h, .8), 0), silh | flip, flip, u, off

def frame_height():
    x0, y0, x1, y1 = INNER
    d_in = np.minimum.reduce([GX - x0, GY - y0, x1 - GX, y1 - GY])   # >0 inside the opening
    h = np.full(GX.shape, np.nan)
    ring = d_in < 0
    # inner bevel: from the glass line (d=0) up to the flat frame top over BEVEL mm
    t = np.clip(-d_in/BEVEL, 0, 1)
    h = np.where(ring, BASE + 2 + (FRAME_TOP - BASE - 2)*np.sqrt(t), h)
    side = np.where(GY - y0 == np.minimum.reduce([GX - x0, GY - y0, x1 - GX, y1 - GY]), 0,       # bottom
            np.where(y1 - GY == np.minimum.reduce([GX - x0, GY - y0, x1 - GX, y1 - GY]), 2,      # top
            np.where(GX - x0 == np.minimum.reduce([GX - x0, GY - y0, x1 - GX, y1 - GY]), 1, 3)))  # left / right
    return h, ring, side, d_in

def build_heightfield():
    hm, mm, flip_m, um, offm = whale_height(MAIN, True)
    hf, mf_, _, _, _ = whale_height(FAR, False)
    water = BASE + .6 + .35*np.sin(GX/260 - GY/180) + .5*np.sin(GX/90 + 2*np.sin(GY/130))*np.clip((GY/H - .8)/.2, 0, 1)
    fm = mask_of(S1.fish_school(n=18, centre=(860, 170), spread=(200, 70)))
    h = np.where(fm, BASE + 1.4, water)
    h = np.where(mf_, BASE + .8 + hf, h)
    h = np.where(mm, BASE + hm, h)
    layer = np.where(mm, 2, np.where(mf_, 1, np.where(fm, 3, 0)))
    fh, ring, side, d_in = frame_height()
    h_scene = h.copy()
    # the frame occludes everything: inside the ring the frame wins
    h = np.where(ring, fh, h)
    return h, layer, dict(mm=mm, flip=flip_m, u=um, off=offm, side=side, d_in=d_in, h_scene=h_scene)

# ------------------------------------------------------------------ paint
def ray_strength(x, y):
    sun = np.array([300.0, 1500.0])
    a = np.arctan2(x - sun[0], sun[1] - y)
    k = (np.sin(a*19 + 1.3) + .6*np.sin(a*37 - .4) + .4*np.sin(a*61))/2.0
    return np.clip(k, 0, 1)*np.clip((y - 40)/(H - 40), 0, 1)**.8

_R = np.random.default_rng(5)
def water_tone(x, y):
    yn = (y - FRAME_W)/(H - 2*FRAME_W)
    t = np.interp(yn, [0, .3, .55, .8, 1], [1.4, 2.4, 3.2, 4.2, 5.2]) + 1.3*ray_strength(x, y)
    # shadow band cast by the top of the frame onto the water just inside the opening
    t -= 1.2*np.clip(1 - (H - FRAME_W - y)/70, 0, 1)
    lo = math.floor(t); t = lo + (1 if _R.random() < t - lo else 0)
    return int(np.clip(t, 1, 7))

def facet_colour(c, layer, n, F):
    x, y = c
    i, j = int(np.clip((H - y)/PX, 0, GH - 1)), int(np.clip(x/PX, 0, GW - 1))
    if layer == 4:
        side = F["side"][i, j]; d_in = F["d_in"][i, j]
        if d_in < -BEVEL: return 11                         # flat frame top = wall colour
        return 12 if side in (2, 1) else 11                 # top/left reveal in shadow
    if layer == 0: return water_tone(x, y)
    if layer == 3: return 4
    light = n @ np.array([-.25, .75, .62])/np.linalg.norm([-.25, .75, .62])
    if layer == 1: return int(np.clip(water_tone(x, y) - 1, 1, 7))
    if F["flip"][i, j]: return 10 if light > .6 else 9
    u, off = F["u"][i, j], F["off"][i, j]
    e = MAIN.pt(.205, .006)
    de = math.hypot(x - e[0], y - e[1])
    if de < 8: return 1                                     # eye
    if de < 17: return 8                                    # eye surround
    if u < .5 and off < throat_top(u) - .002:               # throat: pale ridges, darker grooves
        band = int(math.floor(pleat_v(u, off)*2*N_PLEATS))   # each slope between crest and groove
        return 10 if band % 2 == 1 else 9                     # upper slope catches light, lower in shade
    mott = math.sin(x/37 + 1.7*math.sin(y/53)) + math.sin(y/29 - x/71) + .8*math.sin((x + y)/23)
    if light < .5: return 8
    if mott > 1.3: return 8 if light < .8 else 9            # blue-whale mottling
    if mott < -1.5 and light > .7: return 10
    return 9 if light < .86 else 10

# ------------------------------------------------------------------ low-poly sampling
def sample_points(F, rng):
    pts = []
    x0, y0, x1, y1 = INNER
    for y in np.arange(y0, y1, 40*.866):
        for x in np.arange(x0, x1, 40):
            q = (x + rng.uniform(-.38, .38)*40, y + rng.uniform(-.38, .38)*34)
            if x0 + 4 < q[0] < x1 - 4 and y0 + 4 < q[1] < y1 - 4: pts.append(q)
    # frame: corners of the outer edge, the glass line, the bevel top line (clean straight facets)
    for t in np.linspace(0, 1, 40): pts += [(x0 + t*(x1 - x0), y0), (x0 + t*(x1 - x0), y1)]
    for t in np.linspace(0, 1, 26): pts += [(x0, y0 + t*(y1 - y0)), (x1, y0 + t*(y1 - y0))]
    # whale: interior lattice
    mm = F["mm"]
    for y in np.arange(y0, y1, 26*.866):
        for x in np.arange(x0, x1, 26):
            q = (x + rng.uniform(-.3, .3)*26, y + rng.uniform(-.3, .3)*22)
            i, j = int((H - q[1])/PX), int(q[0]/PX)
            if mm[i, j] and (F["u"][i, j] > .52 or F["off"][i, j] > throat_top(F["u"][i, j]) + .004):
                pts.append(q)
    # whale outline + mouth line + eye
    for wh, sp in ((MAIN, 12), (FAR, 10)):
        for poly in (wh.body(), wh.flukes(), wh.dorsal(), wh.flipper()):
            P = Polygon(poly).buffer(0)
            if P.is_empty: continue
            ring = P.exterior; ring2 = P.buffer(3).exterior
            for dd in np.arange(0, ring.length, sp):
                p = ring.interpolate(dd); q = ring2.interpolate(dd/ring.length*ring2.length)
                for r in (p, q):
                    if x0 < r.x < x1 and y0 < r.y < y1: pts.append((r.x, r.y))
    for u in np.arange(0, .19, .008):
        for o in (.0025,):
            p = MAIN.pt(u, throat_top(u) + o)
            if x0 < p[0] < x1 and y0 < p[1] < y1: pts.append(tuple(p))
    e = MAIN.pt(.205, .006)
    for r in (7, 16):
        for a in np.linspace(0, 2*np.pi, 10, endpoint=False):
            pts.append((e[0] + r*math.cos(a), e[1] + r*math.sin(a)))
    pts.append(tuple(e))
    for fpoly in S1.fish_school(n=18, centre=(860, 170), spread=(200, 70)):
        pts += [tuple(p) for p in fpoly]
    P = np.array(pts)
    P[:, 0] = np.clip(P[:, 0], x0, x1); P[:, 1] = np.clip(P[:, 1], y0, y1)
    P = np.unique(np.round(P, 2), axis=0)
    from shapely import contains_xy
    TP = throat_polygon().buffer(4)
    return P[~contains_xy(TP, P[:, 0], P[:, 1])]

TU = np.arange(.03, .485, .024)
def throat_grid():
    """Structured (u, v) grid: rows along every crest and every groove, columns ~55 mm apart."""
    V = np.arange(0, 2*N_PLEATS + 1)/(2*N_PLEATS)
    G = np.zeros((len(V), len(TU), 2))
    for k, v in enumerate(V):
        m = throat_top(TU); b = np.interp(TU, S1.U, S1.BOT)
        G[k] = MAIN.pt(TU, m - v*(m - b)*0.985)
    return G

def throat_polygon():
    G = throat_grid()
    ring = np.vstack([G[0], G[1:, -1], G[-1, ::-1], G[::-1, 0][1:]])
    return Polygon(ring).buffer(0)

def frame_facets():
    """Crisp mitred frame: inner bevel (2 steps) + flat top, as explicit facets."""
    x0, y0, x1, y1 = INNER
    zb = BASE + .6
    rings = [(0.0, zb), (BEVEL*.45, BASE + 2 + (FRAME_TOP - BASE - 2)*math.sqrt(.45)),
             (BEVEL, FRAME_TOP), (FRAME_W, FRAME_TOP)]
    def rect(d):
        return np.array([(x0 - d, y0 - d), (x1 + d, y0 - d), (x1 + d, y1 + d), (x0 - d, y1 + d)])
    out = []
    for (da, za), (db, zb2) in zip(rings[:-1], rings[1:]):
        A, B = rect(da), rect(db)
        for k in range(4):            # sides: 0 bottom, 1 right, 2 top, 3 left
            a0, a1, b0, b1 = A[k], A[(k+1) % 4], B[k], B[(k+1) % 4]
            # split long sides into segments so tiles clip cleanly and facets stay low-poly
            nseg = 8 if k in (0, 2) else 5
            for t0, t1 in zip(np.linspace(0, 1, nseg+1)[:-1], np.linspace(0, 1, nseg+1)[1:]):
                pa0, pa1 = a0 + (a1 - a0)*t0, a0 + (a1 - a0)*t1
                # outer ring is longer: map by the same fraction (keeps mitred corners)
                pb0, pb1 = b0 + (b1 - b0)*t0, b0 + (b1 - b0)*t1
                side = {0: 0, 1: 3, 2: 2, 3: 1}[k]
                for tri, zz in (([pa0, pa1, pb1], [za, za, zb2]), ([pa0, pb1, pb0], [za, zb2, zb2])):
                    p3 = np.c_[np.array(tri), zz]
                    n = np.cross(p3[1] - p3[0], p3[2] - p3[0]); n /= np.linalg.norm(n) + 1e-12
                    if n[2] < 0: n = -n
                    col = 11 if (db > BEVEL + .1 or side in (0, 3)) else 12
                    out.append(dict(pts=np.array(tri), z=np.array(zz, float), n=n, layer=4, color=col))
    return out

def build_facets():
    import triangle as tr
    from shapely.geometry import Polygon as SP
    rng = np.random.default_rng(11)
    h, layer, F = build_heightfield()
    hz = F["h_scene"]
    P = sample_points(F, rng)
    G = throat_grid(); nv, nu = G.shape[:2]
    ring = np.vstack([G[0], G[1:, -1], G[-1, ::-1][1:], G[::-1, 0][1:-1]])
    nP = len(P)
    verts = np.vstack([P, ring])
    segs = [[nP + i, nP + (i + 1) % len(ring)] for i in range(len(ring))]
    hole = MAIN.pt(.25, (throat_top(.25) + np.interp(.25, S1.U, S1.BOT))/2)
    out = tr.triangulate(dict(vertices=verts, segments=np.array(segs), holes=np.array([hole])), "pc")
    V2, T2 = out["vertices"], out["triangles"]
    tris = [V2[t] for t in T2]
    # structured throat strips: each quad split along the ridge direction
    for k in range(nv - 1):
        for i in range(nu - 1):
            a, b, c, d = G[k, i], G[k, i + 1], G[k + 1, i + 1], G[k + 1, i]
            tris += [np.array([a, b, c]), np.array([a, c, d])]
    x0, y0, x1, y1 = INNER
    opening = SP([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
    def zf(p):
        j = np.clip(p[:, 0]/PX, 0, GW - 1); i = np.clip((H - p[:, 1])/PX, 0, GH - 1)
        return ndimage.map_coordinates(hz, [i, j], order=1, mode="nearest")
    facets = []
    for p in tris:
        z = zf(p)
        p3 = np.c_[p, z]
        n = np.cross(p3[1] - p3[0], p3[2] - p3[0]); nn = np.linalg.norm(n)
        if nn < 1e-9: continue
        n /= nn
        if n[2] < 0: n = -n
        c = p.mean(0)
        ii, jj = int(np.clip((H - c[1])/PX, 0, GH - 1)), int(np.clip(c[0]/PX, 0, GW - 1))
        lay = int(layer[ii, jj])
        col = facet_colour(c, lay, n, F)
        q = SP(p)
        if not q.within(opening):
            q = q.intersection(opening)
            if q.is_empty or q.geom_type != "Polygon" or q.area < .5: continue
            A = np.c_[p, np.ones(3)]; coef = np.linalg.solve(A, z)
            xy = np.asarray(q.exterior.coords)[:-1]
            for m in range(1, len(xy) - 1):
                tri = xy[[0, m, m + 1]]
                facets.append(dict(pts=tri, z=tri @ coef[:2] + coef[2], n=n, layer=lay, color=col))
            continue
        facets.append(dict(pts=p, z=z, n=n, layer=lay, color=col))
    return facets + frame_facets(), h

def cairo_tiles(scale=100, origin=(-90, -90)):
    S1.W, S1.H = W, H          # tiling code reads the wall size from scene v1
    return S1.cairo_tiles(scale, origin)
