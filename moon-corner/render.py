"""Render the moon corners as seen from inside a room (looking up into a ceiling corner)."""
import pickle, math, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import moon as M

H = 2440.0                                     # 8 ft ceiling
WALL = np.array([233, 228, 220]) / 255
TONES = {0: np.array([118, 118, 122])/255,     # maria  (paint guide: dark grey)
         1: np.array([196, 194, 190])/255,     # highlands (light grey)
         2: np.array([238, 238, 236])/255}     # rays / young crater (near white)
LIP = np.array([170, 170, 170])/255

def world(p):                                   # moon octant -> room (y up, ceiling at H)
    return np.c_[p[:, 0], H - p[:, 1], p[:, 2]]

def render(mult, cam, target, path, size=(1100, 900), fov=42, light=(0.75, -0.35, 0.55), paint=True):
    V, F = pickle.load(open(f".moon_{mult}x.pkl", "rb"))
    R = M.EDGE*mult; c = M.center_offset(R); C = -c*np.ones(3)
    tri_m = V[F]
    ctr = tri_m.mean(1)
    n_dir = (ctr - C); n_dir /= np.linalg.norm(n_dir, axis=1, keepdims=True)
    fn = np.cross(tri_m[:, 1] - tri_m[:, 0], tri_m[:, 2] - tri_m[:, 0])
    fn /= np.linalg.norm(fn, axis=1, keepdims=True) + 1e-12
    on_surface = np.einsum("ij,ij->i", fn, n_dir) > 0.05       # outer skin faces outward
    tone = M.MOON.paint(n_dir)
    tris = np.stack([world(t) for t in tri_m.reshape(-1, 3)]).reshape(-1, 3, 3) if False else \
        np.stack([tri_m[:, :, 0], H - tri_m[:, :, 1], tri_m[:, :, 2]], -1)
    nrm = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-12
    cam = np.asarray(cam, float)
    # orient normals outward from the moon centre (mirror flipped winding)
    Cw = np.array([C[0], H - C[1], C[2]])
    flip = np.einsum("ij,ij->i", nrm, tris.mean(1) - Cw) < 0
    nrm[flip] *= -1
    vis = (np.einsum("ij,ij->i", nrm, cam - tris.mean(1)) > 0) & on_surface
    tris, nrm, tone = tris[vis], nrm[vis], tone[vis]
    L = np.asarray(light, float); L /= np.linalg.norm(L)
    k = 0.30 + 0.85*np.clip(nrm @ L, 0, None) + 0.10*np.clip(nrm @ np.array([0, -1, 0]), 0, None)
    base = np.stack([TONES[t] if paint else TONES[1] for t in tone])
    cols = np.clip(base*k[:, None], 0, 1)
    f = np.asarray(target, float) - cam; f /= np.linalg.norm(f)
    r = np.cross(f, [0, 1, 0]); r /= np.linalg.norm(r); u = np.cross(r, f)
    focal = size[0]/2/math.tan(math.radians(fov/2))
    S = 2
    img = Image.new("RGB", (size[0]*S, size[1]*S), (255, 255, 255))
    d = ImageDraw.Draw(img)
    def proj(P):
        rel = P - cam; z = rel @ f
        return np.c_[size[0]/2 + focal*(rel @ r)/z, size[1]/2 - focal*(rel @ u)/z]*S
    # room: ceiling + two walls, lightly shaded
    g = np.linspace(0, 3000, 61)
    planes = ((lambda a, b: (a, H, b), 1.00), (lambda a, b: (a, H - b, 0), 0.90), (lambda a, b: (0, H - b, a), 0.80))
    for fnc, shade in planes:
        colr = tuple((WALL*shade*255).astype(int))
        for i in range(60):
            for j in range(60):
                q = np.array([fnc(g[i], g[j]), fnc(g[i+1], g[j]), fnc(g[i+1], g[j+1]), fnc(g[i], g[j+1])], float)
                if ((q - cam) @ f).min() < 20: continue
                d.polygon([tuple(p) for p in proj(q)], fill=colr, outline=colr)
    rel = tris.mean(1) - cam
    order = np.argsort(-(rel @ f))
    for i in order:
        p = proj(tris[i]); cc = tuple((cols[i]*255).astype(int))
        d.polygon([tuple(x) for x in p], fill=cc, outline=cc)
    img.resize(size, Image.LANCZOS).save(path)

if __name__ == "__main__":
    stats = {s["version"]: s for s in json.load(open("stats.json"))}
    cam_room = (1500, 1650, 1500)                 # standing in the room, looking up at the corner
    for m in (1, 2, 4):
        render(m, cam_room, (0, H - 40, 0), f"view_{m}x.png", fov=34)
        render(m, cam_room, (0, H - 40, 0), f"view_{m}x_white.png", fov=34, paint=False)
    render(1, (520, H - 760, 520), (60, H - 60, 60), "closeup_1x.png", fov=60, size=(1100, 900))
    render(4, (520, H - 760, 520), (60, H - 60, 60), "closeup_4x.png", fov=60, size=(1100, 900))
    # comparison sheet
    f1 = ImageFont.truetype("DejaVuSans-Bold.ttf", 30); f2 = ImageFont.truetype("DejaVuSans.ttf", 21)
    sheet = Image.new("RGB", (3*720, 680), (246, 244, 240)); dr = ImageDraw.Draw(sheet)
    dr.text((24, 20), "Ceiling-corner moon: 1 ft along each edge, three moon sizes", font=f1, fill=(30, 30, 40))
    dr.text((24, 64), "View from standing in the room, looking up into the corner. Same moon surface at every size; bigger moon = flatter, zoomed-in patch.",
            font=f2, fill=(70, 70, 70))
    for i, m in enumerate((1, 2, 4)):
        a = Image.open(f"view_{m}x_white.png").crop((280, 170, 820, 710)).resize((360, 360))
        b = Image.open(f"view_{m}x.png").crop((280, 170, 820, 710)).resize((360, 360))
        sheet.paste(a, (i*720, 260)); sheet.paste(b, (i*720 + 360, 260))
        dr.text((i*720 + 12, 230), "as printed (white)", font=f2, fill=(90, 90, 90))
        dr.text((i*720 + 372, 230), "painted", font=f2, fill=(90, 90, 90))
        s = stats[f"{m}x"]
        dr.text((i*720 + 24, 110), f"{m}x moon  ·  radius {s['moon_radius_mm']/304.8:.0f} ft", font=f1, fill=(30, 30, 40))
        dr.text((i*720 + 24, 155), f"{s['depth_from_corner_mm']} mm deep at the centre · {s['pieces']} pieces · ~{s['grams']} g",
                font=f2, fill=(70, 70, 70))
        dr.text((i*720 + 24, 187), ["exactly 1/8 of a moon", "flatter: a zoomed-in patch", "flattest: big craters, gentle dome"][i],
                font=f2, fill=(70, 70, 70))
    dr.text((24, 638), "Print: hollow 3 mm shell with a 16 mm flat lip on the walls and ceiling for mounting. All three together ~1.45 kg PLA.",
            font=f2, fill=(70, 70, 70))
    sheet.save("moon_corner_options.png")
