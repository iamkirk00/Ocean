"""v2 tiles: material estimate + test kit (eye / mouth / pleats tiles and a frame corner)."""
import sys, os, json, pickle
import numpy as np
from shapely.geometry import Point
import scene2 as S2
import tiles as T

def load():
    sc = pickle.load(open(".scene2.pkl", "rb"))
    return sc["facets"], S2.cairo_tiles(100, sc["origin"])

def grams(M, infill=.10):
    tm = T.to_tm(M); vol = M.volume()
    # slicer-like: 4 top + 2 bottom layers (~1.2 mm over the footprint), 2 walls, low infill
    foot = tm.area_faces[tm.face_normals[:, 2] < -.9].sum()
    skins = foot*1.2
    walls = tm.area_faces[np.abs(tm.face_normals[:, 2]) < .3].sum()*0.84
    return (skins + walls + max(vol - skins - walls, 0)*infill)/1000*1.24

if __name__ == "__main__":
    facets, tiles = load()
    mode = sys.argv[1] if len(sys.argv) > 1 else "stats"
    if mode == "stats":
        tot = 0; rows = []
        for t in tiles:
            M = T.build_tile(t, facets); g = grams(M); tot += g; rows.append((t["num"], round(g)))
        print(json.dumps(dict(tiles=len(tiles), total_grams=round(tot), heaviest=sorted(rows, key=lambda r: -r[1])[:4])))
    else:
        os.makedirs("stl_v2_test_kit", exist_ok=True)
        eye = S2.MAIN.pt(.205, .006)
        mouth = S2.MAIN.pt(.09, S2.throat_top(.09))
        pleat = S2.MAIN.pt(.30, -.05)
        picks = {}
        for name, p in (("eye", eye), ("mouth", mouth), ("pleats", pleat), ("frame-corner", (S2.W - 20, S2.H - 20))):
            t = min(tiles, key=lambda t: t["poly"].distance(Point(p)) + (0 if t["poly"].contains(Point(p)) else 1e6))
            picks[t["num"]] = (t, name)
        for num, (t, name) in sorted(picks.items()):
            M = T.build_tile(t, facets)
            T.to_tm(M).export(f"stl_v2_test_kit/tile_{num:03d}_{name}.stl")
            print(num, name, round(grams(M)), "g")
