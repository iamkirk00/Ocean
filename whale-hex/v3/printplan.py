"""Hollow the whale into a printable shell, split everything to fit the K1C, estimate PLA.

usage: python3 printplan.py [single|corner] [--stl]
"""
import sys, json, math
import numpy as np
import trimesh
import manifold3d as mf
import whale3d as W

BED = np.array([210.0, 210.0, 240.0])      # K1C 220x220x250 minus margin
PLA = 1.24                                 # g/cm^3

def to_mf(m):
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices, np.float32),
                               tri_verts=np.asarray(m.faces, np.uint32)))
def to_tm(M):
    g = M.to_mesh()
    return trimesh.Trimesh(np.asarray(g.vert_properties)[:, :3], np.asarray(g.tri_verts), process=True)

def room_box(walls):
    big = mf.Manifold.cube([8000, 8000, 8000], center=True)
    for w in walls:
        n = w.n
        # keep half-space in front of each wall surface (tiles occupy 0..TILE_BASE)
        big = big.trim_by_plane(list(-n * -1.0), float(np.dot(n, w.o + n*W.TILE_BASE)))
    return big

def fits(m):
    ext = np.sort(trimesh.bounds.oriented_bounds(m)[1])
    return np.all(ext <= np.sort(BED)), ext

def split_to_fit(M, depth=0):
    tm = to_tm(M)
    ok, ext = fits(tm)
    if ok or depth > 6:
        return [M]
    T, ext = trimesh.bounds.oriented_bounds(tm)
    axis = np.linalg.inv(T)[:3, int(np.argmax(ext))]
    c = tm.bounds.mean(0) if True else tm.centroid
    off = float(np.dot(axis, tm.centroid))
    a = M.trim_by_plane(list(axis), off)
    b = M.trim_by_plane(list(-axis), -off)
    out = []
    for p in (a, b):
        for comp in p.decompose():
            if comp.volume() > 50:
                out += split_to_fit(comp, depth+1)
    return out

def tile_grams(m):
    # slicer-like estimate: 2 walls, 4 top / 3 bottom layers @0.2, 10% gyroid
    top = m.area_faces[m.face_normals @ np.array([0, 0, 1]) > -2].sum()  # all faces (shell)
    shell_mm3 = m.area * 0.8
    infill = max(m.volume - shell_mm3, 0) * 0.10
    return (shell_mm3 + infill) / 1000 * PLA

def main(name, write):
    sc = W.scene_single() if name == "single" else W.scene_corner()
    # rebuild unclipped parts for booleans
    ctrl, roll = sc["ctrl"], sc["roll"]
    outer, sp = W.build_whale(ctrl, roll)
    inner, _ = W.build_whale(ctrl, roll, inset=W.SHELL_T)
    fins = []
    i = np.searchsorted(sp["s"], .30); P, T = sp["P"][i], sp["T"][i]
    lat = np.cross(T, [0, 1, 0]); lat /= np.linalg.norm(lat)
    for sgn in (+1, -1):
        root = P + lat*sgn*78 - np.array([0, 70, 0])
        fins.append(W.build_flipper(root, T*.55 + lat*sgn*.55 + np.array([0, -.6, 0]), 200, 30, 10))
    room = room_box(sc["walls"])
    body = to_mf(outer)
    for f in fins: body = body + to_mf(f)
    shell = (body - to_mf(inner)) ^ room
    shell_tm = to_tm(shell)
    pieces = split_to_fit(shell)
    whale_g = shell.volume()/1000*PLA
    tiles_g = sum(tile_grams(t["mesh"]) for t in sc["tiles"])
    tall = max(t["mesh"].extents.max() for t in sc["tiles"])
    res = dict(version=name, whale_pieces=len(pieces), whale_grams=round(whale_g),
               tiles=len(sc["tiles"]), tiles_grams=round(tiles_g), total_grams=round(whale_g+tiles_g),
               whale_reach_mm=round(float(shell_tm.bounds[1][2])),
               whale_bbox_mm=[round(v) for v in shell_tm.extents])
    if write:
        import os
        d = f"stl_{name}"; os.makedirs(d, exist_ok=True)
        for k, p in enumerate(pieces):
            to_tm(p).export(f"{d}/whale_W{k+1:02d}.stl")
        for t in sc["tiles"]:
            t["mesh"].export(f"{d}/tile_{t['label']}.stl")
    print(json.dumps(res))
    return res

if __name__ == "__main__":
    main(sys.argv[1], "--stl" in sys.argv)
