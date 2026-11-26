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
    near_whale = ndimage.distance_transform_edt(~whale)*P.MMPX < 45
    shadow = near_whale & ~whale & (hsv[:, :, 2] < 95)          # dark paint hugging the whale = cast shadow
    shadow = ndimage.binary_closing(shadow, iterations=2)
    splash = ~white & ~whale & ~shadow
    splash = ndimage.binary_opening(splash, iterations=1)
    h_splash = np.where(splash, 0.9 + 1.6*P.dome(splash, 4.5), 0)
    h = np.where(shadow, 0.15, h_splash)                          # flat: the whale casts it, it isn't paint
    h = np.where(fin, np.maximum(h, h_fin), h)
    h = np.where(body, np.maximum(h_body, 0.9), h)
    h = np.where(flip, np.maximum(h, h_flip), h)
    h = ndimage.gaussian_filter(h, 0.8)
    return BASE + np.clip(h, 0, None), whale, splash, white

MIN_AREA_MM2, MIN_WIDTH_MM = 40.0, 2.5

OUT_AREA_MM2, OUT_WIDTH_MM = 90.0, 4.5      # splashes / background: tiny dots and hairline drips merge away

def paintable(lbl, whale=None, rounds=8):
    """Merge any paint area that is too small or too thin to paint into its best neighbour.
    Inside the whale we keep finer detail (thin white lines between the throat ridges)."""
    def limits(sub, y0, x0):
        inside = whale is not None and whale[y0:y0+sub.shape[0], x0:x0+sub.shape[1]][sub].mean() > .5
        a, w = (MIN_AREA_MM2, MIN_WIDTH_MM) if inside else (OUT_AREA_MM2, OUT_WIDTH_MM)
        return a/P.MMPX**2, w/2/P.MMPX
    for _ in range(rounds):
        changed = 0
        for k in np.unique(lbl):
            n, cc, st, _ = cv2.connectedComponentsWithStats((lbl == k).astype(np.uint8), connectivity=4)
            for c in range(1, n):
                x, y, w, hh, area = st[c]
                x0, y0, x1, y1 = max(x - 2, 0), max(y - 2, 0), min(x + w + 2, lbl.shape[1]), min(y + hh + 2, lbl.shape[0])
                sub = cc[y0:y1, x0:x1] == c
                min_px, min_r = limits(sub, y0, x0)
                if area >= min_px and cv2.distanceTransform(sub.astype(np.uint8), cv2.DIST_L2, 3).max() >= min_r:
                    continue
                ring = ndimage.binary_dilation(sub) & ~sub
                nb = lbl[y0:y1, x0:x1][ring]; nb = nb[nb != k]
                if len(nb): lbl[y0:y1, x0:x1][sub] = np.bincount(nb).argmax(); changed += 1
        if not changed: break
    return lbl

def region_stats(lbl):
    areas, widths = [], []
    for k in np.unique(lbl):
        n, cc, st, _ = cv2.connectedComponentsWithStats((lbl == k).astype(np.uint8), connectivity=4)
        for c in range(1, n):
            x, y, w, hh, a = st[c]
            sub = (cc[y:y+hh, x:x+w] == c).astype(np.uint8)
            areas.append(a*P.MMPX**2); widths.append(2*cv2.distanceTransform(np.pad(sub, 1), cv2.DIST_L2, 3).max()*P.MMPX)
    a, w = np.array(areas), np.array(widths)
    return dict(regions=len(a), smallest_mm2=round(float(a.min()), 1), narrowest_mm=round(float(w.min()), 1),
                median_mm2=round(float(np.median(a))), under_10mm_wide=int((w < 10).sum()))

ENGRAVE_D = 0.45
SIZES_MM = (8, 7, 6, 5.2, 4.5, 4.0)

def _glyph(txt, hmm, angle_deg):
    """Binary mask of a number, rotated, at heightfield resolution."""
    from PIL import Image, ImageDraw, ImageFont
    f = ImageFont.truetype("DejaVuSans-Bold.ttf", max(6, int(round(hmm/P.MMPX))))
    bb = f.getbbox(txt); w, h = bb[2] - bb[0] + 4, bb[3] - bb[1] + 4
    im = Image.new("L", (w, h), 0); ImageDraw.Draw(im).text((2 - bb[0], 2 - bb[1]), txt, font=f, fill=255)
    im = im.rotate(angle_deg, expand=True, resample=Image.NEAREST)
    return np.array(im) > 0

def _try_place(comp, txt):
    """Find a size/angle/position where the number fits fully inside the area (0.6 mm clearance)."""
    inner = cv2.erode(comp, np.ones((3, 3), np.uint8), iterations=max(1, int(round(.6/P.MMPX))))
    if not inner.any(): return None
    dt = cv2.distanceTransform(np.pad(comp, 1), cv2.DIST_L2, 3)[1:-1, 1:-1]
    ys, xs = np.nonzero(comp)
    ang = 0.0
    if len(xs) > 5:
        cov = np.cov(np.vstack([xs, ys])); ev, evec = np.linalg.eigh(cov)
        major = evec[:, np.argmax(ev)]
        ang = -np.degrees(np.arctan2(major[1], major[0]))
        if ang > 90: ang -= 180
        if ang < -90: ang += 180
    # candidate centres: the widest points of the area
    flat = np.argsort(dt.ravel())[::-1][:400:20]
    cands = [np.unravel_index(i, dt.shape) for i in flat]
    for hmm in SIZES_MM:
        for a in (0.0, ang) if abs(ang) > 12 else (0.0,):
            g = _glyph(txt, hmm, a); gh, gw = g.shape
            for cy, cx in cands:
                y0, x0 = cy - gh//2, cx - gw//2
                if y0 < 0 or x0 < 0 or y0 + gh > comp.shape[0] or x0 + gw > comp.shape[1]: continue
                if inner[y0:y0+gh, x0:x0+gw][g].all():
                    return y0, x0, g, hmm, a
    return None

def engrave_numbers(h, lbl, tiles, Hmm):
    """Engrave each paint area's colour number into its surface, separately on every tile.
    Numbers turn to run along long thin areas (throat stripes, drips) when that is what fits."""
    from PIL import Image, ImageDraw
    Hp, Wp = lbl.shape
    eng = np.zeros(lbl.shape, bool)
    placed, skipped = [], 0
    for t in tiles:
        tm = Image.new("L", (Wp, Hp), 0)
        ImageDraw.Draw(tm).polygon([(x/P.MMPX, (Hmm - y)/P.MMPX) for x, y in t["poly"].buffer(-3).exterior.coords], fill=1)
        tmask = np.array(tm) > 0
        ys_, xs_ = np.nonzero(tmask); x0, y0, x1, y1 = xs_.min(), ys_.min(), xs_.max(), ys_.max()
        sub_l, sub_t = lbl[y0:y1+1, x0:x1+1], tmask[y0:y1+1, x0:x1+1]
        for k in np.unique(sub_l[sub_t]):
            n, cc, st, _ = cv2.connectedComponentsWithStats(((sub_l == k) & sub_t).astype(np.uint8), connectivity=4)
            for c in range(1, n):
                bx, by, bw, bh, area = st[c]
                if area*P.MMPX**2 < MIN_AREA_MM2: continue
                comp = (cc[by:by+bh, bx:bx+bw] == c).astype(np.uint8)
                r = _try_place(comp, str(int(k) + 1))
                if r is None: skipped += 1; continue
                gy, gx, g, hmm, a = r
                Y, X = y0 + by + gy, x0 + bx + gx
                eng[Y:Y+g.shape[0], X:X+g.shape[1]] |= g
                placed.append(dict(tile=t["num"], colour=int(k) + 1, x=int(X + g.shape[1]//2), y=int(Y + g.shape[0]//2),
                                   mm=hmm, angle=round(float(a), 1)))
    return h - ENGRAVE_D*eng, eng, placed, skipped

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
    before = region_stats(lbl)
    lbl = paintable(lbl, masks["body"] | masks["flip"] | masks["fin"])
    after = region_stats(lbl)
    h, whale, splash, white = heightfield(rgb, masks, tr)
    h = h + P.OUTLINE_H*P.outlines(lbl)
    Hp = rgb.shape[0]; Hmm = Hp*P.MMPX
    to_mm = lambda p: (tr(p)[0]*P.MMPX, Hmm - tr(p)[1]*P.MMPX)
    origin = best_origin(rgb, white, [to_mm(EYE), to_mm(SNOUT)])
    tiles = hex_grid(rgb, white, origin)
    h, eng, placed, skipped = engrave_numbers(h, lbl, tiles, Hmm)
    json.dump(placed, open("private/numbers.json", "w"))
    np.save("private/height.npy", h.astype(np.float32)); np.save("private/labels.npy", lbl.astype(np.int16))
    np.save("private/colours.npy", cols); cv2.imwrite("private/canvas.png", rgb[:, :, ::-1])
    json.dump(dict(art_mm=ART, origin=[float(o) for o in origin],
                   tiles=[dict(num=t["num"], poly=list(t["poly"].exterior.coords)) for t in tiles]), open("private/tiles.json", "w"))
    print(json.dumps(dict(art_mm=ART, tiles=len(tiles), max_relief=round(float(h.max()), 1),
                          before=before, after=after, numbers_engraved=len(placed), guide_only=skipped)))
