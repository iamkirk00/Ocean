"""Previews: painted front (with tile seams + numbers), paint-by-number guide, walk-by parallax GIF."""
import math, sys, pickle
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon
import scene as S

TILE_SCALE, TILE_ORIGIN = 100, (-90, -90)
WALLC = (232, 227, 219)
FONT = "DejaVuSans-Bold.ttf"

def shade(f, L=np.array([-.35, .7, .62])):
    L = L/np.linalg.norm(L)
    k = .62 + .5*max(float(f["n"] @ L), 0)
    return tuple((np.clip(S.RGB[f["color"]]*k, 0, 1)*255).astype(int))

def front(facets, tiles, path, px=0.6, numbers=True, paint_numbers=False, lit=True):
    """Orthographic front view. px = pixels per mm."""
    pad = 40
    Wp, Hp = int(S.W*px) + 2*pad, int(S.H*px) + 2*pad
    img = Image.new("RGB", (Wp, Hp), WALLC); d = ImageDraw.Draw(img)
    tf = lambda x, y: (pad + x*px, pad + (S.H - y)*px)
    for f in facets:
        col = shade(f) if lit else tuple((S.RGB[f["color"]]*255).astype(int))
        d.polygon([tf(*p) for p in f["pts"]], fill=col, outline=col if not paint_numbers else (40, 40, 40))
    fnt = ImageFont.truetype(FONT, max(9, int(26*px)))
    for t in tiles:
        ring = np.asarray(t["poly"].exterior.coords)
        d.line([tf(*p) for p in ring], fill=WALLC, width=max(2, int(4*px)))
        if numbers:
            c = t["poly"].representative_point()
            d.text(tf(c.x, c.y), str(t["num"]), font=fnt, fill=(255, 255, 255), anchor="mm",
                   stroke_width=2, stroke_fill=(0, 0, 0))
    if paint_numbers:
        f2 = ImageFont.truetype("DejaVuSans.ttf", max(8, int(9*px)))
        for f in facets:
            p = Polygon(f["pts"])
            if p.area*px*px < 260: continue
            c = p.centroid
            d.text(tf(c.x, c.y), str(f["color"]), font=f2, fill=(20, 20, 20) if f["color"] >= 5 and f["color"] != 8 else (235, 235, 235), anchor="mm")
    img.save(path)
    return img

def perspective(facets, path, eye, size=(1000, 680), fov=46, L=np.array([-.35, .7, .62]), tiles=None):
    """Render the relief from a real eye position in the room (wall plane z=0, room z>0)."""
    eye = np.asarray(eye, float)
    target = np.array([S.W/2, S.H/2, 0.0])
    f = target - eye; f /= np.linalg.norm(f)
    r = np.cross(f, [0, 1, 0]); r /= np.linalg.norm(r); u = np.cross(r, f)
    foc = size[0]/2/math.tan(math.radians(fov/2))
    Ln = L/np.linalg.norm(L)
    tris, cols = [], []
    for fa in facets:
        P = np.c_[fa["pts"], fa["z"]]
        k = .62 + .5*max(float(fa["n"] @ Ln), 0)
        tris.append(P); cols.append(np.clip(S.RGB[fa["color"]]*k, 0, 1))
    tris = np.array(tris); cols = np.array(cols)
    # cheap side walls of the relief: extrude steep edges so height reads in the GIF
    rel = tris - eye
    zc = rel @ f
    order = np.argsort(-zc.mean(1))
    S2 = 2
    img = Image.new("RGB", (size[0]*S2, size[1]*S2), WALLC); d = ImageDraw.Draw(img)
    for i in order:
        p = rel[i]
        sx = size[0]/2 + foc*(p @ r)/(p @ f); sy = size[1]/2 - foc*(p @ u)/(p @ f)
        c = tuple((cols[i]*255).astype(int))
        d.polygon([(a*S2, b*S2) for a, b in zip(sx, sy)], fill=c, outline=c)
    if tiles is not None:
        for t in tiles:
            ring = np.asarray(t["poly"].exterior.coords)
            P = np.c_[ring, np.full(len(ring), S.BASE + .7)] - eye
            sx = size[0]/2 + foc*(P @ r)/(P @ f); sy = size[1]/2 - foc*(P @ u)/(P @ f)
            d.line([(a*S2, b*S2) for a, b in zip(sx, sy)], fill=WALLC, width=2)
    img = img.resize(size, Image.LANCZOS)
    img.save(path) if path else None
    return img

if __name__ == "__main__":
    facets, h, P, T, z = S.build_facets()
    tiles = S.cairo_tiles(TILE_SCALE, TILE_ORIGIN)
    pickle.dump(dict(facets=facets, h=h), open(".scene.pkl", "wb"))
    print("facets", len(facets), "tiles", len(tiles), "max relief", round(float(h.max()), 1))
    front(facets, tiles, "wall_painted.png", px=0.6, numbers=True)
    front(facets, tiles, "wall_clean.png", px=0.6, numbers=False)
    # walk-by parallax: eye at 1.6 m height, 2.2 m from the wall, walking left -> right
    frames = []
    for k, xs in enumerate(np.linspace(-900, S.W + 900, 14)):
        frames.append(perspective(facets, None, (xs, 1250, 2300), tiles=tiles))
    frames += frames[::-1][1:-1]
    frames[0].save("walk_by.gif", save_all=True, append_images=frames[1:], duration=110, loop=0)
    frames[0].save("walk_left.png"); frames[7].save("walk_mid.png")
