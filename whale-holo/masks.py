"""Whale / flipper / lower-fin masks for the reference painting (1024 px), snapped to the black
outline with GrabCut inside a narrow band. Outputs private/masks.npz."""
import cv2, numpy as np
from scipy import ndimage

BODY = [(128,688),(160,736),(256,772),(400,777),(470,758),(540,726),(600,688),(650,652),(690,615),(705,540),
        (740,440),(752,400),(770,300),(790,220),(800,160),(805,110),(790,60),(760,95),(690,115),(560,140),
        (450,190),(330,270),(240,370),(185,460),(145,570),(125,650)]
FLIP = [(650,470),(700,455),(760,500),(840,580),(920,680),(975,750),(978,790),(940,800),(870,760),(790,690),(720,610),(670,560)]
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
    np.savez("private/masks.npz", **masks)
    ov = img.copy()
    for name, c in (("body", (0, 255, 0)), ("flip", (0, 0, 255)), ("fin", (255, 0, 0))):
        cs, _ = cv2.findContours(masks[name].astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        cv2.drawContours(ov, cs, -1, c, 2)
    cv2.imwrite("private/belly_check.png", cv2.resize(ov[560:960, 100:760], None, fx=1.5, fy=1.5))
    cv2.imwrite("private/mask_check.png", cv2.resize(ov, (640, 640)))
