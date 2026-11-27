"""Cut the photo relief into numbered Cairo-pentagon tiles (STL) + a tile map / paint guide overlay.
Reads/writes ./private/ only."""
import sys, os, json, math
import numpy as np
import trimesh, manifold3d as mf, fast_simplification
from shapely.geometry import Polygon, Point, box
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
import photo_relief as P

GAP, ENGRAVE, PLA = 0.2, 0.8, 1.24
CAIRO_C = (-2 + math.sqrt(28))/6

def cairo(scale, origin, W, H):
    c = CAIRO_C; out, seen = [], set()
    for i in range(-3, int(W/(2*scale)) + 3):
        for j in range(-3, int(H/(2*scale)) + 3):
            cx, cy = 2*i, 2*j
            vs = ([[(cx - c, cy), (cx + c, cy), (cx + 1, cy + s), (cx, cy + s*(2 - c)), (cx - 1, cy + s)] for s in (1, -1)]
                  if (i + j) % 2 == 0 else
                  [[(cx, cy - c), (cx, cy + c), (cx + s, cy + 1), (cx + s*(2 - c), cy), (cx + s, cy - 1)] for s in (1, -1)])
            for v in vs:
                p = Polygon([(origin[0] + x*scale, origin[1] + y*scale) for x, y in v])
                k = tuple(np.round(p.centroid.coords[0], 1))
                if k in seen: continue
                seen.add(k); q = p.intersection(box(0, 0, W, H))
                if q.is_empty or q.area < .04*p.area: continue
                out.append(dict(full=p, poly=q))
    out.sort(key=lambda t: (round(t["poly"].centroid.y/scale), t["poly"].centroid.x))
    for k, t in enumerate(out): t["num"] = k + 1
    return out

def keypoints(L, W, H):
    """Eyes, nose tip, mouth/tongue in panel mm (y up): seams should stay away from these."""
    pts = []
    for idx in (468, 473, 1, 13, 17):
        x, y = L[idx, 0]*W, (1 - L[idx, 1])*H
        pts.append((x, y))
    x, y = L[17, 0]*W, (1 - L[17, 1])*H - 0.05*H     # tongue
    pts.append((x, y))
    return pts

def best_tiling(W, H, L, scale=100):
    kp = keypoints(L, W, H); best = None
    for ox in np.arange(-190, 1, 8):
        for oy in np.arange(-190, 1, 8):
            t = cairo(scale, (ox, oy), W, H); full = t[0]["full"].area
            sl = sum(x["poly"].area/full < .3 for x in t)
            edges = [x["poly"].boundary for x in t]
            dmin = min(min(e.distance(Point(p)) for e in edges) for p in kp)
            score = (sl, -min(dmin, 30), len(t))
            if best is None or score < best[0]: best = (score, (ox, oy))
    return best[1], best[0]

def heightfield_solid(h, x0, y0, x1, y1):
    """Watertight block: faceted top from the heightfield over [x0,x1]x[y0,y1] (mm), flat bottom at z=0."""
    Hp, Wp = h.shape; s = P.MMPX
    c0, c1 = max(int(x0/s) - 1, 0), min(int(x1/s) + 2, Wp - 1)
    r1, r0 = min(Hp - 1 - int(y0/s) + 1, Hp - 1), max(Hp - 1 - int(y1/s) - 2, 0)
    sub = h[r0:r1 + 1, c0:c1 + 1]
    ny, nx = sub.shape
    X = (np.arange(nx) + c0)*s; Y = (Hp - 1 - (np.arange(ny) + r0))*s
    gx, gy = np.meshgrid(X, Y)
    top = np.c_[gx.ravel(), gy.ravel(), sub.ravel()]
    bot = np.c_[gx.ravel(), gy.ravel(), np.zeros(gx.size)]
    V = np.vstack([top, bot]); N = nx*ny
    idx = np.arange(N).reshape(ny, nx)
    a, b, c, d = idx[:-1, :-1].ravel(), idx[:-1, 1:].ravel(), idx[1:, 1:].ravel(), idx[1:, :-1].ravel()
    F = [np.c_[a, d, b], np.c_[b, d, c], np.c_[a + N, b + N, d + N], np.c_[b + N, c + N, d + N]]
    ring = np.r_[idx[0, :], idx[1:, -1], idx[-1, -2::-1], idx[-2:0:-1, 0]]
    for i in range(len(ring)):
        p, q = ring[i], ring[(i + 1) % len(ring)]
        F.append(np.array([[p, p + N, q], [q, p + N, q + N]]))
    m = trimesh.Trimesh(V, np.vstack(F), process=False)
    trimesh.repair.fix_normals(m)
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32)))

def text_solid(txt, size, center, depth):
    tp = TextPath((0, 0), txt, size=size, prop=FontProperties(family="DejaVu Sans", weight="bold"))
    cs = mf.CrossSection([np.asarray(p).tolist() for p in tp.to_polygons() if len(p) > 2], mf.FillRule.EvenOdd)
    b = cs.bounds(); cs = cs.translate([-(b[0] + b[2])/2, -(b[1] + b[3])/2]).mirror([1, 0])
    return mf.Manifold.extrude(cs, depth + .5).translate([center[0], center[1], -.5])

def arrow_solid(center, s, depth):
    pts = [(0, s), (-.55*s, .15*s), (-.2*s, .15*s), (-.2*s, -.8*s), (.2*s, -.8*s), (.2*s, .15*s), (.55*s, .15*s)]
    return mf.Manifold.extrude(mf.CrossSection([[(center[0] + x, center[1] + y) for x, y in pts]]), depth + .5).translate([0, 0, -.5])

def strip_pocket(cx, cy, w, h, depth, r=1.5):
    """Shallow rounded-rectangle recess in the tile back (z=0 face) for a mounting strip."""
    cs = mf.CrossSection.square([w - 2*r, h - 2*r], center=True).offset(r, mf.JoinType.Round)
    return mf.Manifold.extrude(cs, depth + .5).translate([cx, cy, -.5])

def build(t, h, pockets=()):
    poly = t["poly"].buffer(-GAP, join_style=2)
    x0, y0, x1, y1 = poly.bounds
    block = heightfield_solid(h, x0, y0, x1, y1)
    from shapely.geometry.polygon import orient
    ring = np.asarray(orient(poly, 1).exterior.coords)[:-1]           # counter-clockwise outline
    prism = mf.Manifold.extrude(mf.CrossSection([ring]), 200).translate([0, 0, -1])
    solid = block ^ prism
    c = poly.representative_point()
    solid = solid - text_solid(str(t["num"]), 26, (c.x, c.y - 8), ENGRAVE) - arrow_solid((c.x, c.y + 26), 12, ENGRAVE)
    for dx, dy, w, hh, depth in pockets:                       # offsets from the tile centre (mm)
        solid = solid - strip_pocket(c.x + dx, c.y + dy, w, hh, depth)
    g = solid.to_mesh()
    V, F = np.asarray(g.vert_properties)[:, :3], np.asarray(g.tri_verts)
    V2, F2 = fast_simplification.simplify(V.astype(np.float32), F.astype(np.int32), target_reduction=0.75)
    tm = trimesh.Trimesh(V2, F2, process=True)
    tm.apply_translation([-c.x, -c.y, 0])
    return tm, solid

def grams(M, tm, infill=.10):
    vol = M.volume(); foot = tm.area_faces[tm.face_normals[:, 2] < -.9].sum()
    walls = tm.area_faces[np.abs(tm.face_normals[:, 2]) < .3].sum()*0.84
    return (foot*1.2 + walls + max(vol - foot*1.2 - walls, 0)*infill)/1000*PLA

if __name__ == "__main__":
    h = np.load("private/height.npy").astype(np.float64)
    L = np.load("private/landmarks.npy")
    W, H = P.PANEL_W, P.PANEL_H
    origin, score = best_tiling(W, H, L)
    tiles = cairo(100, origin, W, H)
    os.makedirs("private/stl", exist_ok=True)
    tot = 0; info = []
    for t in tiles:
        tm, M = build(t, h)
        g = grams(M, tm); tot += g
        tm.export(f"private/stl/tile_{t['num']:02d}.stl")
        Mc = mf.Manifold(mf.Mesh(vert_properties=np.asarray(tm.vertices, np.float32), tri_verts=np.asarray(tm.faces, np.uint32)))
        info.append(dict(num=t["num"], grams=round(g), faces=len(tm.faces),
                         ok=str(Mc.status()) == "Error.NoError" and Mc.volume() > 1000))
    json.dump(dict(origin=[float(o) for o in origin], tiles=[dict(num=t["num"], poly=list(t["poly"].exterior.coords)) for t in tiles]),
              open("private/tiles.json", "w"))
    print(json.dumps(dict(origin=[float(o) for o in origin], seam_clearance_mm=-score[1], tiles=len(tiles),
                          total_grams=round(tot), all_valid=all(i["ok"] for i in info),
                          bad=[i["num"] for i in info if not i["ok"]])))
