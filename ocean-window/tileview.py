import sys, math, numpy as np, trimesh
from PIL import Image, ImageDraw, ImageFont
def view(path, eye_dir, size=520, light=(-.4, .6, .7)):
    m = trimesh.load(path)
    c = m.bounds.mean(0); R = np.linalg.norm(m.extents)*0.9
    e = np.asarray(eye_dir, float); e /= np.linalg.norm(e); cam = c + e*R*2.2
    f = c - cam; f /= np.linalg.norm(f)
    up = np.array([0, 1.0, 0]) if abs(f[1]) < .9 else np.array([0, 0, 1.0])
    r = np.cross(f, up); r /= np.linalg.norm(r); u = np.cross(r, f)
    L = np.asarray(light, float); L /= np.linalg.norm(L)
    tri = m.triangles; n = m.face_normals
    vis = np.einsum("ij,ij->i", n, cam - tri.mean(1)) > 0
    tri, n = tri[vis], n[vis]
    k = .35 + .65*np.clip(n @ L, 0, 1)
    rel = tri - cam; z = rel @ f
    foc = size*1.6
    S2 = 2; img = Image.new("RGB", (size*S2, size*S2), (240, 238, 234)); d = ImageDraw.Draw(img)
    for i in np.argsort(-z.mean(1)):
        p = rel[i]; sx = size/2 + foc*(p @ r)/(p @ f); sy = size/2 - foc*(p @ u)/(p @ f)
        g = int(235*k[i]); d.polygon([(a*S2, b*S2) for a, b in zip(sx, sy)], fill=(g, g, g - 4))
    return img.resize((size, size), Image.LANCZOS)
if __name__ == "__main__":
    out = Image.new("RGB", (520*3, 560), (240, 238, 234)); d = ImageDraw.Draw(out)
    fnt = ImageFont.truetype("DejaVuSans-Bold.ttf", 20)
    for k, (p, e, lab) in enumerate([("stl_test_kit/tile_064.stl", (.35, -.55, 1), "tile 64: front (raised whale)"),
                                     ("stl_test_kit/tile_064_HOLLOW_whale_test.stl", (.35, -.55, 1), "tile 64: HOLLOW whale test"),
                                     ("stl_test_kit/tile_064.stl", (.2, .3, -1), "tile 64: back (number + UP)")]):
        out.paste(view(p, e), (k*520, 40)); d.text((k*520 + 20, 10), lab, font=fnt, fill=(30, 30, 40))
    out.save("test_tile_views.png")
