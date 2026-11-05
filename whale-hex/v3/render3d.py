"""Tiny painter's-algorithm renderer (flat shaded) for previews."""
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import whale3d as W

WALLC = np.array([232, 226, 216]) / 255

def look(cam, target, up=(0, 1, 0)):
    f = np.asarray(target, float) - cam; f /= np.linalg.norm(f)
    r = np.cross(f, up); r /= np.linalg.norm(r)
    u = np.cross(r, f)
    return r, u, f

def render(scene, cam, target, path, size=(1400, 1050), fov=50, paint=True, labels=False, light=(-.4, .8, .6)):
    cam = np.asarray(cam, float)
    r, u, f = look(cam, target)
    L = np.asarray(light, float); L /= np.linalg.norm(L)
    focal = size[0]/2/np.tan(np.radians(fov/2))
    tris, cols = [], []
    walls_t, walls_c = [], []
    def add_mesh(m, ids, base=None):
        for tri, n, pid in zip(m.triangles, m.face_normals, ids):
            if np.dot(n, tri.mean(0) - cam) > 0:      # back-face cull
                continue
            c = np.array(Image.new("RGB", (1, 1), W.PAL[pid][1]).getpixel((0, 0)))/255 if base is None else base
            k = .42 + .65*max(np.dot(n, L), 0)
            tris.append(tri); cols.append(np.clip(c*k, 0, 1))
    # walls (big quads, subdivided for sorting)
    for w in scene["walls"]:
        lo, hi = w.u_range
        lo, hi = max(lo, -1400), min(hi, 1800)
        us = np.linspace(lo, hi, 13); vs = np.linspace(400, 2500, 10)
        for a in range(len(us)-1):
            for b in range(len(vs)-1):
                q = w.to3d(np.array([(us[a], vs[b]), (us[a+1], vs[b]), (us[a+1], vs[b+1]), (us[a], vs[b+1])]))
                for t in ([0, 1, 2], [0, 2, 3]):
                    walls_t.append(q[t]); walls_c.append(WALLC*(0.93 if w.n[0] > .5 else 1.0))
    for t in scene["tiles"]:
        add_mesh(t["mesh"], t["mesh"].metadata["paint"])
    for m in scene["whale"]:
        add_mesh(m, m.metadata["paint"])
    nw = len(walls_t)
    tris = np.array(walls_t + tris); cols = np.array(walls_c + cols)
    rel = tris - cam
    z = rel @ f; x = rel @ r; y = rel @ u
    ok = (z > 10).all(1)
    tris2 = np.stack([x, y, z], -1)[ok]; cols = cols[ok]
    depth = tris2[:, :, 2].mean(1)
    isw = np.arange(len(ok))[ok] < nw
    depth = np.where(isw, 1e9 + depth, depth)          # walls always behind
    order = np.argsort(-depth)
    S = 2
    img = Image.new("RGB", (size[0]*S, size[1]*S), tuple((WALLC*255).astype(int)))
    d = ImageDraw.Draw(img)
    for i in order:
        p = tris2[i]
        sx = size[0]/2 + focal*p[:, 0]/p[:, 2]; sy = size[1]/2 - focal*p[:, 1]/p[:, 2]
        c = tuple((cols[i]*255).astype(int))
        d.polygon([(a*S, b*S) for a, b in zip(sx, sy)], fill=c, outline=c)
    if labels:
        try: font = ImageFont.truetype("DejaVuSans-Bold.ttf", 26*S//2)
        except Exception: font = ImageFont.load_default()
        for t in scene["tiles"]:
            c3 = t["mesh"].bounds.mean(0)
            rel = c3 - cam
            zz = rel @ f
            sx = size[0]/2 + focal*(rel @ r)/zz; sy = size[1]/2 - focal*(rel @ u)/zz
            d.text((sx*S, sy*S), t["label"], fill=(20, 20, 20), font=font, anchor="mm",
                   stroke_width=3, stroke_fill=(255, 255, 255))
    img = img.resize(size, Image.LANCZOS)
    img.save(path)
