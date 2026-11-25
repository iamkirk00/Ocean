"""Previews (private/): white print under a side lamp, painted, hex map, paint guide."""
import sys, os, json, numpy as np
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon
from shapely.ops import unary_union
sys.path.insert(0, "../photo-relief"); import photo_relief as P
P.MMPX = 0.5
h = np.load("private/height.npy"); lbl = np.load("private/labels.npy"); cols = np.load("private/colours.npy")
tl = json.load(open("private/tiles.json")); Hp, Wp = h.shape; Hmm = Hp*P.MMPX
px = lambda x, y: (x/P.MMPX, (Hmm - y)/P.MMPX)
polys = [Polygon(t["poly"]) for t in tl["tiles"]]
# mask: only what is on a tile is printed
from PIL import Image as I
m = I.new("L", (Wp, Hp), 0); dm = ImageDraw.Draw(m)
for p in polys: dm.polygon([px(*c) for c in p.exterior.coords], fill=255)
on = np.array(m) > 0
WALL = np.array([.92, .90, .87])
def compose(rgb):
    out = np.where(on[:, :, None], rgb, WALL)
    im = Image.fromarray((np.clip(out, 0, 1)*255).astype(np.uint8)); d = ImageDraw.Draw(im)
    for p in polys: d.line([px(*c) for c in p.exterior.coords], fill=(235, 232, 226), width=5)
    return im
sh = P.shade(h)[:, :, None]; shr = P.shade(h, light=(-.85, -.3, .42))[:, :, None]
painted = compose(cols[lbl]/255*sh)
white = compose(np.array([.95, .94, .92])*shr)
mapim = painted.copy(); d = ImageDraw.Draw(mapim); f = ImageFont.truetype("DejaVuSans-Bold.ttf", 46)
for t, p in zip(tl["tiles"], polys):
    c = p.centroid; d.text(px(c.x, c.y), str(t["num"]), font=f, fill="white", anchor="mm", stroke_width=4, stroke_fill="black")
b = unary_union(polys).bounds; crop = (int(b[0]/P.MMPX) - 30, int((Hmm - b[3])/P.MMPX) - 30, int(b[2]/P.MMPX) + 30, int((Hmm - b[1])/P.MMPX) + 30)
for im, name in ((painted, "painted"), (white, "white"), (mapim, "map")):
    im.crop(crop).save(f"private/{name}.png")
a, b2 = Image.open("private/white.png"), Image.open("private/painted.png")
s = Image.new("RGB", (a.width*2 + 30, a.height), (255, 255, 255)); s.paste(a, (0, 0)); s.paste(b2, (a.width + 30, 0))
s.resize((s.width*2//5, s.height*2//5)).save("private/compare_small.png"); s.save("private/compare.png")
