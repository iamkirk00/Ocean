"""STL export + paint guide for the hologram whale (private/)."""
import sys, os, json, numpy as np
sys.path.insert(0, "../photo-relief")
import photo_relief as P, make_tiles as MT
import manifold3d as mf
from shapely.geometry import Polygon
from PIL import Image, ImageDraw, ImageFont
P.MMPX = 0.5
h = np.load("private/height.npy").astype(np.float64); lbl = np.load("private/labels.npy"); cols = np.load("private/colours.npy")
tl = json.load(open("private/tiles.json"))
os.makedirs("private/stl", exist_ok=True)
tot, info = 0, []
for t in tl["tiles"]:
    tt = dict(num=t["num"], poly=Polygon(t["poly"]))
    tm, M = MT.build(tt, h)
    g = MT.grams(M, tm); tot += g
    tm.export(f"private/stl/hex_{t['num']:02d}.stl")
    Mc = mf.Manifold(mf.Mesh(vert_properties=np.asarray(tm.vertices, np.float32), tri_verts=np.asarray(tm.faces, np.uint32)))
    info.append((t["num"], round(g), round(float(tm.extents[2]), 1), str(Mc.status()) == "Error.NoError" and Mc.volume() > 1000))
print(json.dumps(dict(tiles=len(info), total_grams=round(tot), all_valid=all(i[3] for i in info),
                      tallest_mm=max(i[2] for i in info), per_tile=[i[:3] for i in info])))
# paint guide: outlines + region numbers + tile seams + legend
Hp, Wp = lbl.shape; Hmm = Hp*P.MMPX
g = np.full(lbl.shape + (3,), 255, np.uint8); g[P.outlines(lbl)] = (95, 95, 95)
im = Image.fromarray(g); d = ImageDraw.Draw(im); f = ImageFont.truetype("DejaVuSans.ttf", 12)
for x, y, num, r in P.label_positions(lbl, min_px=300):
    d.text((x, y), str(num), font=f, fill=(25, 25, 25), anchor="mm")
fb = ImageFont.truetype("DejaVuSans-Bold.ttf", 40)
for t in tl["tiles"]:
    pts = [(x/P.MMPX, (Hmm - y)/P.MMPX) for x, y in t["poly"]]
    d.line(pts, fill=(220, 50, 50), width=4)
    c = Polygon(t["poly"]).centroid; d.text((c.x/P.MMPX, (Hmm - c.y)/P.MMPX - 60), f"#{t['num']}", font=fb, fill=(220, 50, 50), anchor="mm")
legend = Image.new("RGB", (im.width, 330), "white"); dl = ImageDraw.Draw(legend); f2 = ImageFont.truetype("DejaVuSans-Bold.ttf", 22)
for k in range(len(cols)):
    cx, cy = 20 + (k % 5)*int(im.width/5), 20 + (k//5)*75
    dl.rectangle([cx, cy, cx + 55, cy + 55], fill=tuple(int(v) for v in cols[k]), outline=(60, 60, 60))
    dl.text((cx + 68, cy + 15), f"{k+1}  #{''.join(f'{int(v):02x}' for v in cols[k])}", font=f2, fill=(20, 20, 20))
sheet = Image.new("RGB", (im.width, im.height + legend.height), "white"); sheet.paste(im, (0, 0)); sheet.paste(legend, (0, im.height))
sheet.save("private/paint_guide.png")
