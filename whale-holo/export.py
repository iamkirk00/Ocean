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
# paint guide: engraved numbers (black, as on the print) + guide-only numbers for the smallest areas (blue)
import cv2
placed = json.load(open("private/numbers.json"))
Hp, Wp = lbl.shape; Hmm = Hp*P.MMPX
g = np.full(lbl.shape + (3,), 255, np.uint8); g[P.outlines(lbl)] = (95, 95, 95)
on = np.zeros(lbl.shape, bool); tmask = Image.new("L", (Wp, Hp), 0)
for t in tl["tiles"]: ImageDraw.Draw(tmask).polygon([(x/P.MMPX, (Hmm - y)/P.MMPX) for x, y in t["poly"]], fill=1)
on = np.array(tmask) > 0
g[~on] = (238, 236, 232)
im = Image.fromarray(g); d = ImageDraw.Draw(im)
has = np.zeros(lbl.shape, bool)
for p in placed:
    f = ImageFont.truetype("DejaVuSans-Bold.ttf", max(9, int(p["mm"]/P.MMPX*.9)))
    d.text((p["x"], p["y"]), str(p["colour"]), font=f, fill=(20, 20, 20), anchor="mm")
    k = p["colour"] - 1
    n, cc = cv2.connectedComponents(((lbl == k) & on).astype(np.uint8), connectivity=4)
    if lbl[p["y"], p["x"]] == k and cc[p["y"], p["x"]]: has |= cc == cc[p["y"], p["x"]]
fs = ImageFont.truetype("DejaVuSans-Bold.ttf", 10)
for k in np.unique(lbl):
    n, cc, st, cen = cv2.connectedComponentsWithStats(((lbl == k) & on & ~has).astype(np.uint8), connectivity=4)
    for c in range(1, n):
        if st[c, 4] < 30: continue
        m = (cc == c).astype(np.uint8); dt = cv2.distanceTransform(m, cv2.DIST_L2, 3)
        y, x = np.unravel_index(dt.argmax(), dt.shape)
        d.text((x, y), str(int(k) + 1), font=fs, fill=(30, 90, 220), anchor="mm")
fb = ImageFont.truetype("DejaVuSans-Bold.ttf", 44)
for t in tl["tiles"]:
    pts = [(x/P.MMPX, (Hmm - y)/P.MMPX) for x, y in t["poly"]]
    d.line(pts, fill=(220, 50, 50), width=4)
def legend(width):
    L = Image.new("RGB", (width, 420), "white"); dl = ImageDraw.Draw(L); f2 = ImageFont.truetype("DejaVuSans-Bold.ttf", 22)
    for k in range(len(cols)):
        cx, cy = 20 + (k % 4)*int(width/4), 20 + (k//4)*70
        dl.rectangle([cx, cy, cx + 52, cy + 52], fill=tuple(int(v) for v in cols[k]), outline=(60, 60, 60))
        dl.text((cx + 64, cy + 14), f"{k+1}  #{''.join(f'{int(v):02x}' for v in cols[k])}", font=f2, fill=(20, 20, 20))
    dl.text((20, 380), "Black numbers are engraved on the tile. Blue numbers are guide-only (area too small to engrave).",
            font=ImageFont.truetype("DejaVuSans.ttf", 20), fill=(60, 60, 60))
    return L
ys, xs = np.nonzero(on); full = im.crop((xs.min() - 20, ys.min() - 20, xs.max() + 20, ys.max() + 20))
for t in tl["tiles"]:
    c = Polygon(t["poly"]).centroid
    ImageDraw.Draw(im).text((c.x/P.MMPX, (Hmm - c.y)/P.MMPX), f"#{t['num']}", font=fb, fill=(220, 50, 50), anchor="mm")
full = im.crop((xs.min() - 20, ys.min() - 20, xs.max() + 20, ys.max() + 20))
L = legend(full.width); sheet = Image.new("RGB", (full.width, full.height + L.height), "white")
sheet.paste(full, (0, 0)); sheet.paste(L, (0, full.height)); sheet.save("private/paint_guide.png")
# one sheet per tile, enlarged, so the painter works tile by tile
os.makedirs("private/guides", exist_ok=True)
for t in tl["tiles"]:
    poly = Polygon(t["poly"]); x0, y0, x1, y1 = poly.bounds
    box = (int(x0/P.MMPX) - 10, int((Hmm - y1)/P.MMPX) - 10, int(x1/P.MMPX) + 10, int((Hmm - y0)/P.MMPX) + 10)
    tile = Image.fromarray(g).crop(box)                                    # without the big tile labels
    tile_im = im.crop(box).resize((tile.width*2, tile.height*2), Image.LANCZOS)
    L = legend(tile_im.width); s2 = Image.new("RGB", (tile_im.width, tile_im.height + L.height + 50), "white")
    ImageDraw.Draw(s2).text((20, 10), f"Tile #{t['num']}  (UP arrow on the back points up)", font=ImageFont.truetype("DejaVuSans-Bold.ttf", 28), fill=(20, 20, 20))
    s2.paste(tile_im, (0, 50)); s2.paste(L, (0, 50 + tile_im.height)); s2.save(f"private/guides/tile_{t['num']:02d}.png")
