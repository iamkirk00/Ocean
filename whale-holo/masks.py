"""Whale / flipper / lower-fin masks for the reference painting (1024 px), snapped to the black
outline with GrabCut inside a narrow band. Outputs private/masks.npz."""
import cv2, numpy as np
from scipy import ndimage

BODY = [(128,688),(160,736),(256,772),(400,777),(470,758),(540,726),(600,688),(650,652),(690,615),(705,540),
        (740,440),(752,400),(770,300),(790,220),(800,160),(805,110),(790,60),(760,95),(690,115),(560,140),
        (450,190),(330,270),(240,370),(185,460),(145,570),(125,650)]
FLIP = [(650,470),(700,455),(760,500),(840,580),(920,680),(975,750),(978,790),(940,800),(870,760),(790,690),(720,610),(670,560)]
# bottom of the lowest throat ridge: everything below it is the painting's shadow, not whale
RIDGE_BOTTOM = [(140,719),(167,725),(233,739),(300,744),(367,736),(433,717),(500,693),(567,664),(633,633),(687,608),(700,593)]
# the nose's dark rounded underside is whale (not shadow): follow the painted outline around the chin
NOSE_UNDERSIDE = [(126,690),(126,705),(133,722),(148,745),(170,764),(200,777),(240,784),(282,779),(320,765),(352,750),(375,738),(300,735),(140,715)]
FIN = [(320,768),(328,832),(344,888),(384,920),(413,912),(419,848),(424,784)]

def poly_mask(shape, p):
    m = np.zeros(shape, np.uint8); cv2.fillPoly(m, [np.array(p).reshape(-1, 1, 2)], 1); return m

def snap(img, p, band, clip_px):
    pm = poly_mask(img.shape[:2], p); k = np.ones((3, 3), np.uint8)
    gc = np.full(img.shape[:2], cv2.GC_BGD, np.uint8)
    gc[cv2.dilate(pm, k, iterations=band) > 0] = cv2.GC_PR_BGD
    gc[pm > 0] = cv2.GC_PR_FGD
    gc[cv2.erode(pm, k, iterations=band) > 0] = cv2.GC_FGD
    cv2.grabCut(img, gc, None, np.zeros((1, 65)), np.zeros((1, 65)), 5, cv2.GC_INIT_WITH_MASK)
    m = ((gc == cv2.GC_FGD) | (gc == cv2.GC_PR_FGD)).astype(np.uint8)
    m &= cv2.dilate(pm, k, iterations=clip_px)          # never wander far from the traced outline
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    return ndimage.binary_fill_holes(lab == (1 + np.argmax(st[1:, cv2.CC_STAT_AREA])))

if __name__ == "__main__":
    img = cv2.imread("private/art.jpg")
    masks = dict(body=snap(img, BODY, 8, 3), flip=snap(img, FLIP, 12, 8), fin=snap(img, FIN, 10, 6))
    # one smooth lower outline: around the chin, then along the bottom of the throat ridges
    from scipy.interpolate import UnivariateSpline
    chin = [p for p in NOSE_UNDERSIDE if p[0] < 300 and p[1] > 718]
    pts = np.array(sorted(chin + [p for p in RIDGE_BOTTOM if p[0] >= 330], key=lambda p: p[0]), float)
    spl = UnivariateSpline(pts[:, 0], pts[:, 1], s=len(pts)*6.0)
    xs = np.arange(img.shape[1]); yy = np.arange(img.shape[0])[:, None]
    x_lo, x_hi = pts[0, 0], pts[-1, 0]
    inside = (xs >= x_lo) & (xs <= x_hi)
    curve = np.where(inside, spl(np.clip(xs, x_lo, x_hi)), 0) + 2
    body = masks["body"].copy()
    # fill down to the curve under the head (the chin), then cut everything below it
    top = np.array([np.nonzero(body[:, x])[0].min() if body[:, x].any() else 10**6 for x in xs])
    fill = (yy >= top[None, :]) & (yy <= curve[None, :]) & inside[None, :]
    body = (body | fill) & ~((yy > curve[None, :]) & inside[None, :])
    body = cv2.morphologyEx(body.astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (17, 17))) > 0
    body = cv2.GaussianBlur(body.astype(np.float32), (0, 0), 2.5) > 0.5      # soften any remaining kink
    # the nose tip is convex: fill the small corner where the old snout edge meets the new curve
    wy0, wy1, wx0, wx1 = 640, 790, 100, 230
    win = body[wy0:wy1, wx0:wx1].astype(np.uint8)
    cs, _ = cv2.findContours(win, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if cs:
        hull = cv2.convexHull(np.vstack(cs)); fillw = np.zeros_like(win); cv2.fillPoly(fillw, [hull], 1)
        body[wy0:wy1, wx0:wx1] |= fillw.astype(bool)
    body = cv2.GaussianBlur(body.astype(np.float32), (0, 0), 2.0) > 0.5
    masks["body"] = ndimage.binary_fill_holes(body)
    np.save("private/lower_outline.npy", np.c_[xs[inside], curve[inside]])
    np.savez("private/masks.npz", **masks)
    ov = img.copy()
    for name, c in (("body", (0, 255, 0)), ("flip", (0, 0, 255)), ("fin", (255, 0, 0))):
        cs, _ = cv2.findContours(masks[name].astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        cv2.drawContours(ov, cs, -1, c, 2)
    cv2.imwrite("private/belly_check.png", cv2.resize(ov[560:960, 100:760], None, fx=1.5, fy=1.5))
    cv2.imwrite("private/mask_check.png", cv2.resize(ov, (640, 640)))
