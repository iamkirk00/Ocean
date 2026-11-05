"""True-3D low-poly blue whale emerging from a wall (or a room corner) + hex splash tiles.

World coords (mm): Y up. Single wall: wall plane z=0, room is z>0.
Corner: walls z=0 (x>0) and x=0 (z>0), room is x>0 & z>0.
"""
import math
import numpy as np
import trimesh
from scipy.spatial import Delaunay
from shapely.geometry import Polygon, Point, MultiPolygon
from shapely.ops import unary_union

PAL = {  # paint-by-number palette (model colours; print is white)
    1: ("Deep navy",  "#16244a"),
    2: ("Ocean blue", "#2f6fb8"),
    3: ("Sky blue",   "#93c9ec"),
    4: ("White",      "#f3f7fb"),
    5: ("Magenta",    "#e0407e"),
    6: ("Orange",     "#f39a2b"),
}

HEX_F = 180.0                      # flat-to-flat; corner-to-corner 208 mm fits a 220 bed
HEX_R = HEX_F / math.sqrt(3)
TILE_BASE = 3.0
SHELL_T = 1.8                      # whale shell wall thickness (4 perimeters @ 0.45)

# ------------------------------------------------------------------ spine helpers
def catmull(P, n):
    P = np.asarray(P, float)
    P = np.vstack([2*P[0]-P[1], P, 2*P[-1]-P[-2]])
    out = []
    for i in range(1, len(P)-2):
        p0, p1, p2, p3 = P[i-1], P[i], P[i+1], P[i+2]
        for t in np.linspace(0, 1, n, endpoint=False):
            out.append(0.5*((2*p1) + (-p0+p2)*t + (2*p0-5*p1+4*p2-p3)*t*t + (-p0+3*p1-3*p2+p3)*t**3))
    out.append(P[-2])
    return np.array(out)

def resample(C, s):
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(C, axis=0), axis=1))]
    d /= d[-1]
    return np.stack([np.interp(s, d, C[:, k]) for k in range(3)], 1)

# ------------------------------------------------------------------ body profile
S_TAB  = [0, .012, .035, .07, .13, .22, .32, .45, .62, .80, 1.0]
W_TAB  = [0,  42,  66,  84,  98, 108, 114, 110,  98,  80, 56]   # half-width (lateral)
HD_TAB = [0,  10,  18,  26,  38,  56,  70,  78,  74,  64, 46]   # dorsal half-height
HV_TAB = [0,  26,  50,  70,  90, 104, 106,  98,  86,  70, 50]   # ventral half-height (throat sag)

def build_whale(ctrl, roll_tab, scale=1.0, inset=0.0, seed=1, detail=True):
    """Loft a whale along ctrl points (snout first). Returns trimesh with face 'paint' ids."""
    rng = np.random.default_rng(seed)
    C = catmull(ctrl, 30)
    n_st = 26
    s = np.concatenate([[0], [.006, .02, .045], np.linspace(.075, 1, n_st-4)])
    P = resample(C, s)
    T = np.gradient(P, axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True)

    # theta samples: dorsal..lateral coarse, ventral band dense (throat pleats)
    th_side = np.r_[np.linspace(0, 1.45, 4), 1.62, 1.80, 1.95, 2.15]                                   # 0 = dorsal ridge
    th_vent = np.linspace(2.15, np.pi, 12)[1:]                          # dense to belly mid
    half = np.r_[th_side, th_vent]
    TH = np.r_[half, 2*np.pi - half[::-1][1:-1]]
    nth = len(TH)
    vent_idx = np.where(np.abs(np.pi - np.where(TH > np.pi, 2*np.pi - TH, TH)) < (np.pi - 2.15) + 1e-6)[0]
    mouth_th = 1.95

    verts = np.zeros((n_st, nth, 3))
    paint_v = np.zeros((n_st, nth), int)
    for i, (si, Pi, Ti) in enumerate(zip(s, P, T)):
        roll = np.interp(si, *roll_tab)
        up0 = np.array([0, 1.0, 0]) - Ti*Ti[1]; up0 /= np.linalg.norm(up0)
        lat0 = np.cross(Ti, up0)
        up = math.cos(roll)*up0 + math.sin(roll)*lat0
        lat = np.cross(Ti, up)
        w = np.interp(si, S_TAB, W_TAB)*scale - inset
        hd = np.interp(si, S_TAB, HD_TAB)*scale - inset
        hv = np.interp(si, S_TAB, HV_TAB)*scale - inset
        w, hd, hv = max(w, .3), max(hd, .3), max(hv, .3)
        for k, th in enumerate(TH):
            c, sn = math.cos(th), math.sin(th)
            # flatter top on the head (blue whale's broad U-shaped rostrum)
            flat = np.interp(si, [0, .25, .45], [1.0, .55, .15])
            cy = np.sign(c)*abs(c)**(1 - .45*flat) if c > 0 else c
            x = w*sn; y = (hd if c > 0 else hv)*cy
            r = 1.0
            thm = th if th <= np.pi else 2*np.pi - th
            if detail:
                # throat pleats: alternate ridge/groove in the ventral band, snout -> navel
                if k in vent_idx and .015 < si < .50:
                    fade = np.interp(si, [.015, .05, .38, .50], [0, 1, 1, 0])
                    j = np.where(vent_idx == k)[0][0]
                    if j % 2 == 1:
                        r -= (5.5*scale/ max(math.hypot(x, y), 1)) * fade * 4.0
                # mouth line groove along the side of the head
                if abs(thm - mouth_th) < .2 and .01 < si < .23:
                    r -= 0.11*np.interp(si, [.01, .04, .2, .23], [0, 1, 1, 0])
                if thm < .35 and .09 < si < .2:
                    r += 0.10*math.sin(np.pi*(si-.09)/.11)
                if not (k in vent_idx and si < .5):
                    r *= 1 + rng.uniform(-.045, .045) * (si > .02)
            verts[i, k] = Pi + up*y*r + lat*x*r
            # paint ids
            if abs(thm - mouth_th) < .2 and .01 < si < .21:
                paint_v[i, k] = 1
            elif .17 < si < .25 and abs(thm - 1.62) < .25:
                paint_v[i, k] = 1          # eye
            elif k in vent_idx and si < .5:
                j = np.where(vent_idx == k)[0][0]
                paint_v[i, k] = 3 if j % 2 == 1 else 4
            elif thm > 2.0:
                paint_v[i, k] = 3
            elif thm > 1.45:
                paint_v[i, k] = 2 if rng.random() < .6 else 3
            else:
                paint_v[i, k] = 2 if rng.random() < .88 else 1
    V = verts.reshape(-1, 3)
    F, FP = [], []
    idx = lambda i, k: i*nth + (k % nth)
    for i in range(n_st-1):
        for k in range(nth):
            a, b, c2, d = idx(i, k), idx(i, k+1), idx(i+1, k+1), idx(i+1, k)
            F += [[a, d, c2], [a, c2, b]]
            pv = paint_v[i, k] if i > 0 else paint_v[i+1, k]
            FP += [pv, pv]
    # caps
    tip = len(V); V = np.vstack([V, P[0] - T[0]*1.0])
    for k in range(nth):
        F.append([tip, idx(0, k), idx(0, k+1)]); FP.append(2)
    tail = len(V); V = np.vstack([V, P[-1]])
    for k in range(nth):
        F.append([tail, idx(n_st-1, k+1), idx(n_st-1, k)]); FP.append(2)
    m = trimesh.Trimesh(V, np.array(F), process=False)
    m.metadata["paint"] = np.array(FP)
    if m.volume < 0:
        m.invert()
    # mouth line + eye paint
    ctr = m.triangles_center
    return m, dict(P=P, T=T, s=s)

def build_flipper(root, direction, length, width, thick, seed=2):
    d = np.asarray(direction, float); d /= np.linalg.norm(d)
    side = np.cross(d, [0, 1, 0]); side /= np.linalg.norm(side) + 1e-9
    flat = np.cross(side, d)
    st = np.linspace(0, 1, 8)
    wv = np.interp(st, [0, .2, .6, .9, 1], [.8, 1, .7, .3, .05])*width
    tv = np.interp(st, [0, .3, 1], [1, .8, .3])*thick
    ring = [(1, 0), (.5, .7), (-.5, .7), (-1, 0), (-.5, -.7), (.5, -.7)]
    V = []
    for t, w, th in zip(st, wv, tv):
        c = np.asarray(root) + d*length*t - flat*30*t*t
        for a, b in ring:
            V.append(c + side*a*w + flat*b*th)
    V = np.array(V); n = len(ring); F = []
    for i in range(len(st)-1):
        for k in range(n):
            a, b = i*n+k, i*n+(k+1) % n
            F += [[a, b, b+n], [a, b+n, a+n]]
    for k in range(1, n-1):
        F.append([0, k+1, k]); F.append([(len(st)-1)*n, (len(st)-1)*n+k, (len(st)-1)*n+k+1])
    m = trimesh.Trimesh(V, F, process=True)
    trimesh.repair.fix_normals(m)
    m.metadata["paint"] = np.full(len(m.faces), 3)
    return m

# ------------------------------------------------------------------ walls / tiles
class Wall:
    """A wall plane with 2D coords (u along wall, v = world Y) and outward normal."""
    def __init__(self, origin, u_dir, normal, u_range):
        self.o = np.asarray(origin, float); self.u = np.asarray(u_dir, float)
        self.n = np.asarray(normal, float); self.v = np.array([0, 1.0, 0]); self.u_range = u_range
    def to3d(self, uv, h=0.0):
        uv = np.atleast_2d(uv); h = np.broadcast_to(h, (len(uv),))
        return self.o + np.outer(uv[:, 0], self.u) + np.outer(uv[:, 1], self.v) + np.outer(h, self.n)

def section_poly(mesh, wall, unfold_sign=1.0):
    sec = mesh.section(plane_origin=wall.o + wall.n*TILE_BASE, plane_normal=wall.n)
    if sec is None:
        return Polygon()
    polys = []
    for path in sec.discrete:
        uv = np.c_[(path - wall.o) @ wall.u, (path - wall.o) @ wall.v]
        if len(uv) > 3:
            p = Polygon(uv).buffer(0)
            polys.append(p)
    return unary_union(polys)

def hex_poly(cx, cy, R=HEX_R):
    return Polygon([(cx + R*math.cos(math.radians(30+60*i)), cy + R*math.sin(math.radians(30+60*i)))
                    for i in range(6)])

def splash_height_fn(foot, seed=4, reach=270, peak=90):
    """Height field (unfolded wall coords) for the splash crown around the whale footprint."""
    rng = np.random.default_rng(seed)
    c = np.array(foot.centroid.coords[0])
    n = 30
    angs = np.sort(rng.uniform(-np.pi, np.pi, n))
    lens = rng.uniform(.45, 1.0, n)*reach
    wids = rng.uniform(.07, .14, n)
    accents = rng.random(n)
    edge = foot.exterior if foot.geom_type == "Polygon" else unary_union(foot).convex_hull.exterior
    def h(u, v):
        p = Point(u, v)
        if foot.contains(p):
            return 0.0, 4
        d = foot.distance(p)
        a = math.atan2(v-c[1], u-c[0])
        crown = (peak*.75)*math.exp(-(d/34)**2)
        best, col = crown, (4 if crown > 12 else 3)
        for A, L, W, acc in zip(angs, lens, wids, accents):
            da = math.atan2(math.sin(a-A), math.cos(a-A))
            t = d / L
            if t >= 1: continue
            wid = W*(1-t)*1.0
            if abs(da) < wid:
                hh = peak*(1-t)**1.2*(1-abs(da)/wid)*(0.6+0.4*(L/reach))
                if hh > best:
                    best = hh
                    col = 4 if t < .55 else (5 if acc > .85 else 6 if acc > .72 else 3)
        ripple = 1.2 + 1.0*math.cos(d/30)*math.exp(-d/400)
        if best < ripple + .5:
            return ripple, 1 if rng.random() < .85 else 2
        return best, col
    return h

def make_tile(poly_uv, wall, hfn, u_shift=0.0, spacing=22.0, seed=0):
    """Solid low-poly tile: flat back on wall, faceted top = base + splash height."""
    rng = np.random.default_rng(seed)
    pts = []
    ring = poly_uv.exterior
    L = ring.length
    for d in np.linspace(0, L, max(int(L/spacing), 12), endpoint=False):
        p = ring.interpolate(d); pts.append((p.x, p.y))
    nb = len(pts)
    minx, miny, maxx, maxy = poly_uv.bounds
    inner = poly_uv.buffer(-spacing*.3)
    for y in np.arange(miny, maxy, spacing*.85):
        for x in np.arange(minx, maxx, spacing):
            q = (x + rng.uniform(-.4, .4)*spacing, y + rng.uniform(-.4, .4)*spacing)
            if inner.contains(Point(q)): pts.append(q)
    pts = np.array(pts)
    tri = Delaunay(pts)
    hh, cols = zip(*[hfn(p[0]+u_shift, p[1]) for p in pts])
    hh = np.array(hh) + TILE_BASE
    top = []
    for s_ in tri.simplices:
        if poly_uv.buffer(.01).contains(Point(pts[s_].mean(0))):
            top.append(s_)
    top = np.array(top)
    n = len(pts)
    Vt = wall.to3d(pts, hh); Vb = wall.to3d(pts, 0.0)
    V = np.vstack([Vt, Vb])
    F = [list(t) for t in top] + [[t[0]+n, t[2]+n, t[1]+n] for t in top]
    for i in range(nb):
        j = (i+1) % nb
        F += [[i, i+n, j+n], [i, j+n, j]]
    m = trimesh.Trimesh(V, np.array(F), process=False)
    if m.volume < 0: m.invert()
    pid = [max(set([cols[t[0]], cols[t[1]], cols[t[2]]]), key=[cols[t[0]], cols[t[1]], cols[t[2]]].count) for t in top]
    m.metadata["paint"] = np.array(pid + [1]*(len(F)-len(top)))
    return m

# ------------------------------------------------------------------ scenes
def _clip_room(mesh, planes):
    for o, n in planes:
        mesh = mesh.slice_plane(o, n, cap=True)
    return mesh

def scene_single():
    # snout first. Emerges from the wall heading out (+z), turns to swim along +x past you.
    ctrl = [(780, 1450, 300), (580, 1446, 328), (380, 1422, 300), (200, 1384, 222),
            (70, 1344, 104), (0, 1322, -60), (-50, 1300, -330)]
    roll = ([0, .2, .5, .8, 1], [.42, .38, .25, .06, 0])               # bank: belly toward viewer
    return _scene(ctrl, roll, walls=[Wall((0, 0, 0), (1, 0, 0), (0, 0, 1), (-1e4, 1e4))],
                  name="single")

def scene_corner():
    # bursts out of the corner seam on the diagonal, then curves to swim past along wall A
    ctrl = [(800, 1440, 250), (600, 1436, 292), (400, 1410, 282), (230, 1372, 222),
            (100, 1340, 120), (0, 1320, 0), (-170, 1300, -170)]
    roll = ([0, .2, .5, .8, 1], [.42, .38, .22, .04, 0])
    walls = [Wall((0, 0, 0), (1, 0, 0), (0, 0, 1), (0, 1e4)),        # wall A (z=0), u = x
             Wall((0, 0, 0), (0, 0, 1), (1, 0, 0), (0, 1e4))]        # wall B (x=0), u = z
    return _scene(ctrl, roll, walls, name="corner")

def _scene(ctrl, roll, walls, name):
    body, sp = build_whale(ctrl, roll)
    # pectoral flippers at s≈0.3: swept back/down/out
    i = np.searchsorted(sp["s"], .30)
    P, T = sp["P"][i], sp["T"][i]
    lat = np.cross(T, [0, 1, 0]); lat /= np.linalg.norm(lat)
    fins = []
    for sgn in (+1, -1):
        root = P + lat*sgn*78 - np.array([0, 70, 0])
        dirv = T*.55 + lat*sgn*.55 + np.array([0, -.6, 0])
        fins.append(build_flipper(root, dirv, 200, 30, 10))
    parts = [body] + fins
    # clip to the room
    planes = [(w.o, w.n) for w in walls]
    clipped = []
    for p in parts:
        paint = p.metadata["paint"]
        q = p.copy(); q.metadata["paint"] = paint
        for o, n in planes:
            if name == "single" or True:
                q2 = q.slice_plane(o + n*TILE_BASE, n, cap=True)
                # carry paint ids by nearest original face centre
                if len(q2.faces):
                    from scipy.spatial import cKDTree
                    kd = cKDTree(q.triangles_center)
                    _, j = kd.query(q2.triangles_center)
                    q2.metadata["paint"] = q.metadata["paint"][j]
                q = q2
        if len(q.faces): clipped.append(q)
    # footprints on each wall -> unfolded coords (wall B mirrored to negative u)
    feet = []
    for wi, w in enumerate(walls):
        fp = section_poly(unary_union_mesh(parts), w)
        if fp.is_empty: continue
        if len(walls) == 2:
            fp = fp.intersection(Polygon([(0, -1e4), (1e4, -1e4), (1e4, 1e4), (0, 1e4)]))
            if wi == 1:
                from shapely.affinity import scale as sscale
                fp = sscale(fp, -1, 1, origin=(0, 0))
        feet.append(fp)
    foot = unary_union(feet).buffer(2)
    if foot.geom_type == "MultiPolygon":
        foot = max(foot.geoms, key=lambda g: g.area)
    hfn = splash_height_fn(foot)
    # hex grid on unfolded plane; corner line at u = 0
    zone = foot.buffer(250)
    tiles = []
    dy = 1.5*HEX_R
    c0 = np.array(foot.centroid.coords[0])
    for r in range(-6, 7):
        cy = c0[1] + r*dy
        off = 0 if r % 2 == 0 else HEX_F/2
        for c in range(-6, 7):
            cx = (0 if len(walls) == 2 else c0[0]) + off + c*HEX_F
            hp = hex_poly(cx, cy)
            if hp.intersection(zone).area / hp.area < .45: continue
            tiles.append((r, c, hp))
    rows = sorted({t[0] for t in tiles}); cmin = min(t[1] for t in tiles)
    out_tiles = []
    for r, c, hp in tiles:
        label = f"{chr(65+rows.index(r))}{c-cmin+1}"
        if len(walls) == 1:
            out_tiles.append(dict(label=label, wall=0, uv=hp,
                                  mesh=make_tile(hp, walls[0], hfn, seed=hash(label) % 999)))
        else:
            for wi, half in ((0, Polygon([(0, -1e4), (1e4, -1e4), (1e4, 1e4), (0, 1e4)])),
                             (1, Polygon([(0, -1e4), (-1e4, -1e4), (-1e4, 1e4), (0, 1e4)]))):
                part = hp.intersection(half)
                if part.is_empty or part.area < 0.04*hp.area: continue
                if part.geom_type != "Polygon": continue
                lab = label + ("" if part.area > .97*hp.area else ("a" if wi == 0 else "b"))
                from shapely.affinity import scale as sscale
                local = part if wi == 0 else sscale(part, -1, 1, origin=(0, 0))
                sh = (lambda wi_: (lambda u, v: hfn(u if wi_ == 0 else -u, v)))(wi)
                out_tiles.append(dict(label=lab, wall=wi, uv=part,
                                      mesh=make_tile(local, walls[wi], sh, seed=hash(lab) % 999)))
    return dict(name=name, whale=clipped, walls=walls, tiles=out_tiles, foot=foot, ctrl=ctrl, roll=roll)

def unary_union_mesh(parts):
    return trimesh.util.concatenate(parts)
