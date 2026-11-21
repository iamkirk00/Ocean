"""Per-tile printable solids: faceted relief top, colour-step lines, engraved number + UP arrow on the back.

usage: python3 tiles.py stats             -> material / time estimate for the whole wall
       python3 tiles.py kit               -> test kit STLs (whale-head tiles + hollow-whale variants)
       python3 tiles.py all               -> every tile
"""
import sys, os, json, math, pickle
import numpy as np
import trimesh
import manifold3d as mf
from shapely.geometry import Polygon
from shapely.affinity import scale as sscale, translate as stranslate
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
import scene as S
from render import TILE_SCALE, TILE_ORIGIN

GAP = 0.2                 # trimmed off every tile edge so neighbours fit
STEP = 0.35               # height step between different paint colours (tactile paint lines)
ENGRAVE = 0.8
PLA = 1.24

def plane_z(f, xy):
    A = np.c_[f["pts"], np.ones(3)]
    a, b, c = np.linalg.solve(A, f["z"])
    return a*xy[:, 0] + b*xy[:, 1] + c

def prism(poly, f, extra, hollow=None):
    xy = np.asarray(poly.exterior.coords)[:-1]
    zt = plane_z(f, xy) + extra
    if hollow is not None:
        zt = hollow(xy, zt, f)
    V = np.vstack([np.c_[xy, np.zeros(len(xy))], np.c_[xy, zt]])
    hull = trimesh.convex.convex_hull(V)
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(hull.vertices, np.float32),
                               tri_verts=np.asarray(hull.faces, np.uint32)))

def text_solid(txt, size, center, depth):
    tp = TextPath((0, 0), txt, size=size, prop=FontProperties(family="DejaVu Sans", weight="bold"))
    polys = []
    for poly in tp.to_polygons():
        if len(poly) > 2: polys.append(np.asarray(poly))
    cs = mf.CrossSection([p.tolist() for p in polys], mf.FillRule.EvenOdd)
    bb = cs.bounds()
    cs = cs.translate([-(bb[0] + bb[2])/2, -(bb[1] + bb[3])/2])
    cs = cs.mirror([1, 0])                        # read correctly when looking at the back
    return mf.Manifold.extrude(cs, depth + 0.5).translate([center[0], center[1], -0.5])

def arrow_solid(center, size, depth):
    s = size
    pts = [(0, s), (-.55*s, .15*s), (-.2*s, .15*s), (-.2*s, -.8*s), (.2*s, -.8*s), (.2*s, .15*s), (.55*s, .15*s)]
    cs = mf.CrossSection([[(center[0] + x, center[1] + y) for x, y in pts]])
    return mf.Manifold.extrude(cs, depth + .5).translate([0, 0, -.5])

def build_tile(t, facets, hollow=False):
    poly = t["poly"].buffer(-GAP, join_style=2)
    hfun = None
    if hollow:
        # hollow-whale variant: whale relief is carved INTO a thick tile (hollow-face illusion)
        top = S.BASE + 32.0
        def hfun(xy, zt, f):
            if f["layer"] == 2:
                return top - (zt - S.BASE)            # invert the relief
            return np.full(len(xy), top)
    parts = []
    minx, miny, maxx, maxy = poly.bounds
    for f in facets:
        fx, fy = f["pts"][:, 0], f["pts"][:, 1]
        if fx.max() < minx or fx.min() > maxx or fy.max() < miny or fy.min() > maxy: continue
        q = Polygon(f["pts"]).intersection(poly)
        if q.is_empty or q.area < 0.05 or q.geom_type != "Polygon": continue
        extra = STEP*(f["color"] % 4)
        parts.append(prism(q, f, extra, hfun))
    solid = mf.Manifold.batch_boolean(parts, mf.OpType.Add)
    # engrave number + UP arrow on the back (z=0 face)
    c = poly.representative_point()
    num = text_solid(str(t["num"]), 30, (c.x, c.y - 8), ENGRAVE)
    arr = arrow_solid((c.x, c.y + 30), 14, ENGRAVE)
    solid = solid - num - arr
    # move to a local frame with the tile centred at the origin
    solid = solid.translate([-c.x, -c.y, 0])
    return solid

def to_tm(M):
    g = M.to_mesh()
    return trimesh.Trimesh(np.asarray(g.vert_properties)[:, :3], np.asarray(g.tri_verts), process=False)

def grams(M):
    tm = to_tm(M)
    shell = tm.area*0.42*2/2 + 0                       # ~2 perimeters / skins over the surface
    vol = M.volume()
    est = min(vol, tm.area*0.8 + max(vol - tm.area*0.8, 0)*0.12)
    return est/1000*PLA

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "stats"
    sc = pickle.load(open(".scene.pkl", "rb"))
    facets = sc["facets"]
    tiles = S.cairo_tiles(TILE_SCALE, TILE_ORIGIN)
    if mode == "stats":
        tot = 0; rows = []
        for t in tiles:
            M = build_tile(t, facets); g = grams(M); tot += g
            rows.append((t["num"], round(g, 1), round(to_tm(M).bounds[1][2], 1)))
        print(json.dumps(dict(tiles=len(tiles), total_grams=round(tot), avg_grams=round(tot/len(tiles), 1),
                              heaviest=sorted(rows, key=lambda r: -r[1])[:5])))
    else:
        out = "stl_test_kit" if mode == "kit" else "stl_all"
        os.makedirs(out, exist_ok=True)
        # whale-head tiles: those that contain the eye and the snout
        eye = S.MAIN.eye()
        from shapely.geometry import Point
        if mode == "kit":
            pick = [t for t in tiles if t["poly"].distance(Point(eye)) < 120 or t["poly"].contains(Point(S.MAIN.s))]
        else:
            pick = tiles
        for t in pick:
            to_tm(build_tile(t, facets)).export(f"{out}/tile_{t['num']:03d}.stl")
        if mode == "kit":
            for t in [x for x in pick if x["poly"].contains(Point(eye))]:
                to_tm(build_tile(t, facets, hollow=True)).export(f"{out}/tile_{t['num']:03d}_HOLLOW_whale_test.stl")
        print(out, sorted(os.listdir(out)))
