"""Photo -> paint-by-number relief panel.

Smooth relief (not low-poly): face depth from MediaPipe face landmarks, gentle domes for hair /
clothes / background from a multiclass segmentation, fine texture from the photo itself, and a thin
raised outline around every paint region (like a printed paint-by-number canvas).

Inputs and outputs live in ./private/ (git-ignored): family photos never go into the repo.
usage: python3 photo_relief.py private/photo.jpg
"""
import sys, json, math
import numpy as np
import cv2
from scipy import ndimage
from scipy.interpolate import griddata

PANEL_W, PANEL_H = 381.0, 508.0     # 15" x 20"
MMPX = 0.5                          # heightfield resolution (mm per pixel)
BASE = 3.0
N_COLOURS = 16
MIN_REGION_MM2 = 35.0               # anything smaller is merged into a neighbour (too small to paint)
OUTLINE_H, OUTLINE_W = 0.5, 1.0     # raised paint lines

# segmentation classes (selfie_multiclass_256x256)
BG, HAIR, BODY, FACE, CLOTHES, OTHER = range(6)

def load(path):
    img = cv2.imread(path)[:, :, ::-1]
    Wp, Hp = int(PANEL_W/MMPX), int(PANEL_H/MMPX)
    return img, cv2.resize(img, (Wp, Hp), interpolation=cv2.INTER_AREA)

# ------------------------------------------------------------------ paint regions
def paint_regions(rgb):
    sm = cv2.pyrMeanShiftFiltering(np.ascontiguousarray(rgb[:, :, ::-1]), 10, 22)[:, :, ::-1]
    sm = cv2.bilateralFilter(np.ascontiguousarray(sm), 9, 30, 9)
    lab = cv2.cvtColor(np.ascontiguousarray(sm[:, :, ::-1]), cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float32)
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, .5)
    _, lab_lbl, centres = cv2.kmeans(lab, N_COLOURS, None, crit, 4, cv2.KMEANS_PP_CENTERS)
    lbl = lab_lbl.reshape(rgb.shape[:2])
    # smooth region boundaries: majority vote in a small neighbourhood
    onehot = np.stack([ndimage.gaussian_filter((lbl == k).astype(np.float32), 2.2) for k in range(N_COLOURS)])
    lbl = onehot.argmax(0)
    lbl = merge_small(lbl, int(MIN_REGION_MM2/MMPX**2))
    # order colours dark -> light so numbers feel natural on the guide
    cols = cv2.cvtColor(centres.reshape(1, -1, 3).astype(np.uint8), cv2.COLOR_LAB2RGB).reshape(-1, 3)
    order = np.argsort(centres[:, 0])
    remap = np.zeros(N_COLOURS, int); remap[order] = np.arange(N_COLOURS)
    lbl = remap[lbl]; cols = cols[order]
    # mean photo colour of each paint (truer than the k-means centre after smoothing)
    for k in range(N_COLOURS):
        if (lbl == k).any(): cols[k] = rgb[lbl == k].mean(0)
    return lbl, cols

def merge_small(lbl, min_px, rounds=6):
    for _ in range(rounds):
        changed = 0
        for k in np.unique(lbl):
            n, cc, stats, _ = cv2.connectedComponentsWithStats((lbl == k).astype(np.uint8), connectivity=4)
            for c in range(1, n):
                if stats[c, cv2.CC_STAT_AREA] >= min_px: continue
                x, y, w, h = stats[c, :4]
                x0, y0, x1, y1 = max(x-2, 0), max(y-2, 0), min(x+w+2, lbl.shape[1]), min(y+h+2, lbl.shape[0])
                sub = cc[y0:y1, x0:x1] == c
                ring = ndimage.binary_dilation(sub) & ~sub
                nb = lbl[y0:y1, x0:x1][ring]
                nb = nb[nb != k]
                if len(nb):
                    lbl[y0:y1, x0:x1][sub] = np.bincount(nb).argmax(); changed += 1
        if not changed: break
    return lbl

def outlines(lbl):
    b = np.zeros(lbl.shape, bool)
    b[:, 1:] |= lbl[:, 1:] != lbl[:, :-1]
    b[1:, :] |= lbl[1:, :] != lbl[:-1, :]
    r = max(1, int(round(OUTLINE_W/MMPX/2)))
    return ndimage.binary_dilation(b, iterations=r - 1) if r > 1 else b

# ------------------------------------------------------------------ relief
def dome(mask, radius_mm):
    d = ndimage.distance_transform_edt(mask)*MMPX
    t = np.clip(d/radius_mm, 0, 1)
    return np.sqrt(1 - (1 - t)**2)

def highpass(gray, sigma_px):
    g = gray.astype(np.float32)/255
    return g - ndimage.gaussian_filter(g, sigma_px)

def relief(rgb, seg, L, lbl):
    Hp, Wp = rgb.shape[:2]
    gray = cv2.cvtColor(np.ascontiguousarray(rgb), cv2.COLOR_RGB2GRAY)
    seg = cv2.resize(seg, (Wp, Hp), interpolation=cv2.INTER_NEAREST)
    yy, xx = np.mgrid[0:Hp, 0:Wp]
    # --- face from landmarks: closest point (nose) highest
    pts = np.c_[L[:, 0]*Wp, L[:, 1]*Hp]
    z = -L[:, 2]
    zf = griddata(pts, z, (xx, yy), method="linear")
    zn = griddata(pts, z, (xx, yy), method="nearest")
    hull = ~np.isnan(zf)
    zf = np.where(hull, zf, zn)
    zr = (zf - z.min())/(z.max() - z.min())
    face_h = 6.0 + 10.0*zr
    # fade the face surface off beyond the landmark hull (forehead top, cheeks) so it blends into hair
    dh = ndimage.distance_transform_edt(~hull)*MMPX
    face_h = face_h - np.clip(dh/40, 0, 1)*4
    # shading detail (eyelids, nostrils, smile lines): darker = slightly deeper
    face_h += 1.4*highpass(gray, 10)
    # --- tongue: pink/red blob just below the lower lip gets pushed toward the viewer
    hsv = cv2.cvtColor(np.ascontiguousarray(rgb), cv2.COLOR_RGB2HSV)
    lip = pts[17]
    near = ((xx - lip[0])/(0.16*Wp))**2 + ((yy - lip[1] - 0.05*Hp)/(0.11*Hp))**2 < 1
    redish = ((hsv[:, :, 0] < 12) | (hsv[:, :, 0] > 165)) & (hsv[:, :, 1] > 60) & (hsv[:, :, 2] > 90)
    tongue = ndimage.binary_opening(near & redish, iterations=3)
    if tongue.any():
        lab_, n_ = ndimage.label(tongue); sizes = ndimage.sum(tongue, lab_, range(1, n_ + 1))
        tongue = lab_ == (np.argmax(sizes) + 1)
        tongue = ndimage.binary_closing(tongue, iterations=6)
    # --- one continuous form: a soft hill over the whole person, face shape blended on top
    person = seg != BG
    body = 1.0 + 7.0*dome(person, 140)                                # head + shoulders swell
    head = np.isin(seg, [FACE, HAIR, BODY])
    body += 3.0*dome(head, 90)                                         # the head sits forward
    wf = ndimage.gaussian_filter(hull.astype(np.float32), 18)          # feathered face weight
    zr_s = ndimage.gaussian_filter(np.where(hull, zr, 0), 10)/np.maximum(ndimage.gaussian_filter(hull.astype(float), 10), 1e-3)
    zr_s = np.where(hull, zr_s, zr)
    face_rel = 14.0*np.clip(zr_s, 0, 1)**1.3                            # landmark depth: nose highest
    h = body + wf*face_rel
    # eyeballs: gentle domes from the iris landmarks (468-477), sized to each eye's width
    for iris, (c0, c1) in ((468, (33, 133)), (473, (362, 263))):
        ctr = pts[iris]; r = 0.36*np.linalg.norm(pts[c0] - pts[c1])
        de = np.hypot(xx - ctr[0], yy - ctr[1])/r
        h += 1.6*(0.5 + 0.5*np.cos(np.pi*np.clip(de, 0, 1)))
    # surface texture from the photo (kept small: it is for the hand, the paint does the rest)
    hp_fine, hp_mid = highpass(gray, 4), highpass(gray, 10)
    h += np.where(seg == HAIR, 2.2*highpass(gray, 6), 0)              # curls
    h += np.where(seg == FACE, 1.2*hp_mid, 0)                          # eyelids, nostrils, smile lines
    h += np.where(np.isin(seg, [CLOTHES, OTHER]), .5*hp_fine, 0)       # knit
    h += np.where(seg == BG, .7*highpass(gray, 3), 0)                  # grass
    if tongue.any():
        h = h + 5.5*dome(tongue, 12)
    # name badge: flat raised plate (very dark, low-saturation, large blob on the clothes)
    dark = (gray < 45) & (hsv[:, :, 1] < 80) & np.isin(seg, [CLOTHES, OTHER])
    lab_, n_ = ndimage.label(ndimage.binary_closing(dark, iterations=4))
    if n_:
        sizes = ndimage.sum(dark, lab_, range(1, n_ + 1))
        k = np.argmax(sizes) + 1
        if sizes[k - 1] > 2000:
            badge = ndimage.binary_fill_holes(lab_ == k)
            h = np.where(badge, np.percentile(h[badge], 60) + 1.2, h)
    h = ndimage.gaussian_filter(h, 1.0)
    h = BASE + np.clip(h, 0, None)
    h = h + OUTLINE_H*outlines(lbl)
    return h, dict(tongue=tongue, seg=seg)

# ------------------------------------------------------------------ previews
def shade(h, light=(-.45, -.6, .66)):
    gy, gx = np.gradient(h, MMPX)
    n = np.dstack([-gx, -gy, np.ones_like(h)]); n /= np.linalg.norm(n, axis=2, keepdims=True)
    L = np.array([light[0], light[1], light[2]]); L /= np.linalg.norm(L)
    # image rows go down: a lamp above-left = (-x, -row)
    return np.clip(.38 + .75*(n @ L), 0, 1.25)

def label_positions(lbl, min_px=400):
    out = []
    for k in np.unique(lbl):
        n, cc = cv2.connectedComponents((lbl == k).astype(np.uint8), connectivity=4)
        for c in range(1, n):
            m = cc == c
            if m.sum() < min_px: continue
            d = cv2.distanceTransform(m.astype(np.uint8), cv2.DIST_L2, 3)
            y, x = np.unravel_index(d.argmax(), d.shape)
            out.append((x, y, int(k) + 1, float(d.max())))
    return out

if __name__ == "__main__":
    from PIL import Image, ImageDraw, ImageFont
    src = sys.argv[1] if len(sys.argv) > 1 else "private/photo.jpg"
    full, rgb = load(src)
    seg = np.load("private/segmask.npy")[:, :, 0].astype(np.uint8)
    L = np.load("private/landmarks.npy")
    lbl, cols = paint_regions(rgb)
    h, extra = relief(rgb, seg, L, lbl)
    np.save("private/height.npy", h.astype(np.float32)); np.save("private/labels.npy", lbl.astype(np.int16))
    np.save("private/colours.npy", cols)
    out = lbl.shape[::-1]
    sh = shade(h)[:, :, None]
    painted = np.clip(cols[lbl]/255*sh, 0, 1)
    white = np.clip(np.array([.93, .92, .90])*sh, 0, 1)
    Image.fromarray((painted*255).astype(np.uint8)).save("private/preview_painted.png")
    Image.fromarray((white*255).astype(np.uint8)).save("private/preview_white.png")
    # paint guide: outlines + numbers + legend
    guide = np.full(lbl.shape + (3,), 255, np.uint8)
    guide[outlines(lbl)] = (90, 90, 90)
    g = Image.fromarray(guide).resize((out[0]*2, out[1]*2), Image.NEAREST); d = ImageDraw.Draw(g)
    fnt = ImageFont.truetype("DejaVuSans.ttf", 15)
    pos = label_positions(lbl)
    for x, y, num, r in pos:
        d.text((x*2, y*2), str(num), font=fnt, fill=(30, 30, 30), anchor="mm")
    legend = Image.new("RGB", (g.width, 230), "white"); dl = ImageDraw.Draw(legend)
    f2 = ImageFont.truetype("DejaVuSans-Bold.ttf", 20)
    for k in range(N_COLOURS):
        cx, cy = 20 + (k % 6)*250, 20 + (k//6)*68
        dl.rectangle([cx, cy, cx + 50, cy + 50], fill=tuple(int(v) for v in cols[k]), outline=(60, 60, 60))
        dl.text((cx + 62, cy + 14), f"{k+1}  #{''.join(f'{int(v):02x}' for v in cols[k])}", font=f2, fill=(20, 20, 20))
    sheet = Image.new("RGB", (g.width, g.height + legend.height), "white"); sheet.paste(g, (0, 0)); sheet.paste(legend, (0, g.height))
    sheet.save("private/paint_guide.png")
    print(json.dumps(dict(px=out, max_relief_mm=round(float(h.max()), 1), regions=len(pos),
                          tongue_px=int(extra["tongue"].sum()))))
