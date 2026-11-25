"""Whale painting -> 3D 'hologram' relief, paint-by-number, whole-hexagon tiles.

Uses the photo-relief pipeline (paint regions, raised outlines, tile builder). The source art and
everything derived from it stay in ./private/ (git-ignored).
usage: python3 holo.py [art_size_mm]
"""
import sys, os, json, math
import numpy as np, cv2
from scipy import ndimage
from shapely.geometry import Polygon, Point
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "photo-relief"))
import photo_relief as P
import make_tiles as MT

ART = float(sys.argv[1]) if len(sys.argv) > 1 else 610.0     # art square, mm (24")
PAD = 110.0                                                  # white margin so whole hexes fit
P.MMPX = 0.5; P.N_COLOURS = 20; P.MIN_REGION_MM2 = 20.0
P.PANEL_W = P.PANEL_H = ART + 2*PAD
HEX_F = 180.0; HEX_R = HEX_F/math.sqrt(3)                    # pointy-top, 208 mm tall: fits a 220 bed
BASE = 3.0
EYE, SNOUT, TAIL, FLIP_ROOT, FLIP_TIP = (568, 424), (140, 690), (790, 80), (690, 480), (965, 775)

def prepare():
    art = cv2.imread("private/art.jpg")[:, :, ::-1]
    n = int(ART/P.MMPX); pad = int(PAD/P.MMPX)
    a = cv2.resize(art, (n, n), interpolation=cv2.INTER_AREA)
    edge = np.vstack([a[:4].reshape(-1, 3), a[-4:].reshape(-1, 3), a[:, :4].reshape(-1, 3), a[:, -4:].reshape(-1, 3)])
    bgc = np.median(edge[edge.mean(1) > 200], axis=0).astype(np.uint8)       # the painting's own white
    canvas = np.empty((n + 2*pad, n + 2*pad, 3), np.uint8); canvas[:] = bgc; canvas[pad:pad+n, pad:pad+n] = a
    M = np.load("private/masks.npz")
    def up(m):
        mm = cv2.resize(m.astype(np.uint8), (n, n), interpolation=cv2.INTER_NEAREST)
        out = np.zeros(canvas.shape[:2], bool); out[pad:pad+n, pad:pad+n] = mm > 0; return out
    masks = {k: up(M[k]) for k in M.files}
    s = n/1024.0
    tr = lambda p: (pad + p[0]*s, pad + p[1]*s)                  # art px -> canvas px
    return canvas, masks, tr

def heightfield(rgb, masks, tr):
    Hp, Wp = rgb.shape[:2]
    yy, xx = np.mgrid[0:Hp, 0:Wp]
    gray = cv2.cvtColor(np.ascontiguousarray(rgb), cv2.COLOR_RGB2GRAY)
    hsv = cv2.cvtColor(np.ascontiguousarray(rgb), cv2.COLOR_RGB2HSV)
    body, flip, fin = masks["body"], masks["flip"], masks["fin"]
    whale = body | flip | fin
    # nearness along the body: tail (0) -> snout (1): the head comes out of the wall toward you
    t0, t1 = np.array(tr(TAIL)), np.array(tr(SNOUT)); ax = t1 - t0
    t = np.clip(((xx - t0[0])*ax[0] + (yy - t0[1])*ax[1])/(ax @ ax), 0, 1)
    rb = 0.13*ART
    h_body = P.dome(body, rb)*(7 + 23*t**0.85)
    # pleats, eye, shading lines from the painting itself: dark strokes become grooves
    h_body += np.where(body, 2.6*P.highpass(gray, 6/P.MMPX)*np.clip(t*1.6, .3, 1), 0)
    # flipper: in front of the body, highest at the root, tapering toward the tip
    r0, r1 = np.array(tr(FLIP_ROOT)), np.array(tr(FLIP_TIP)); fa = r1 - r0
    tf = np.clip(((xx - r0[0])*fa[0] + (yy - r0[1])*fa[1])/(fa @ fa), 0, 1)
    h_flip = 13 + 9*P.dome(flip, 22)*(1 - .4*tf) - 7*tf + 1.5*P.highpass(gray, 5/P.MMPX)
    # lower fin: behind the body
    h_fin = 4 + 6*P.dome(fin, 18)
    # paint splashes and drips: anything not white and not whale becomes raised paint
    white = (hsv[:, :, 1] < 40) & (hsv[:, :, 2] > 195)
    splash = ~white & ~whale
    splash = ndimage.binary_opening(splash, iterations=1)
    h_splash = np.where(splash, 0.9 + 1.6*P.dome(splash, 4.5), 0)
    h = h_splash
    h = np.where(fin, np.maximum(h, h_fin), h)
    h = np.where(body, np.maximum(h_body, 0.9), h)
    h = np.where(flip, np.maximum(h, h_flip), h)
    h = ndimage.gaussian_filter(h, 0.8)
    return BASE + np.clip(h, 0, None), whale, splash, white

def hex_grid(rgb, white, origin):
    Hp, Wp = rgb.shape[:2]; Wmm, Hmm = Wp*P.MMPX, Hp*P.MMPX
    art = ~white
    tiles = []
    dy = 1.5*HEX_R
    for r in range(-1, int(Hmm/dy) + 2):
        for c in range(-1, int(Wmm/HEX_F) + 2):
            cx = origin[0] + c*HEX_F + (HEX_F/2 if r % 2 else 0); cy = origin[1] + r*dy
            hp = Polygon([(cx + HEX_R*math.cos(math.radians(30 + 60*i)), cy + HEX_R*math.sin(math.radians(30 + 60*i))) for i in range(6)])
            x0, y0, x1, y1 = hp.bounds
            if x0 < 0 or y0 < 0 or x1 > Wmm or y1 > Hmm: continue
            # fraction of the hex covered by art (sampled)
            cs, rs = slice(int(x0/P.MMPX), int(x1/P.MMPX)), slice(int((Hmm - y1)/P.MMPX), int((Hmm - y0)/P.MMPX))
            inside = hp.intersection(Polygon([(PAD, PAD), (PAD + ART, PAD), (PAD + ART, PAD + ART), (PAD, PAD + ART)])).area/hp.area
            if inside < 0.8 or art[rs, cs].mean() < 0.30: continue
            tiles.append(dict(poly=hp, cx=cx, cy=cy))
    tiles.sort(key=lambda t: (round(t["cy"]/dy), t["cx"]))
    for k, t in enumerate(tiles): t["num"] = k + 1
    return tiles

def best_origin(rgb, white, keypts):
    best = None
    for ox in np.arange(0, HEX_F, 12):
        for oy in np.arange(0, 1.5*HEX_R*2, 12):
            ts = hex_grid(rgb, white, (ox, oy))
            if not ts: continue
            d = min(min(t["poly"].boundary.distance(Point(p)) for t in ts) for p in keypts)
            sc = (-min(d, 35), len(ts))
            if best is None or sc < best[0]: best = (sc, (ox, oy))
    return best[1]

if __name__ == "__main__":
    rgb, masks, tr = prepare()
    lbl, cols = P.paint_regions(rgb)
    h, whale, splash, white = heightfield(rgb, masks, tr)
    h = h + P.OUTLINE_H*P.outlines(lbl)
    Hp = rgb.shape[0]; Hmm = Hp*P.MMPX
    to_mm = lambda p: (tr(p)[0]*P.MMPX, Hmm - tr(p)[1]*P.MMPX)
    origin = best_origin(rgb, white, [to_mm(EYE), to_mm(SNOUT)])
    tiles = hex_grid(rgb, white, origin)
    np.save("private/height.npy", h.astype(np.float32)); np.save("private/labels.npy", lbl.astype(np.int16))
    np.save("private/colours.npy", cols); cv2.imwrite("private/canvas.png", rgb[:, :, ::-1])
    json.dump(dict(art_mm=ART, origin=[float(o) for o in origin],
                   tiles=[dict(num=t["num"], poly=list(t["poly"].exterior.coords)) for t in tiles]), open("private/tiles.json", "w"))
    print(json.dumps(dict(art_mm=ART, tiles=len(tiles), max_relief=round(float(h.max()), 1),
                          regions=len(P.label_positions(lbl)))))
