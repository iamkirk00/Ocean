"""Ceiling-corner moon: the part of a cratered moon that pokes out of a room corner.

Geometry (mm): corner at origin, the two walls + ceiling are the planes x=0, y=0, z=0,
the room is the octant x,y,z >= 0. The moon sphere is centred on the corner diagonal at
-c(1,1,1) (behind the corner) and sized so it meets each corner edge exactly EDGE mm
from the corner. R = EDGE gives exactly 1/8 of a moon; bigger R = flatter, zoomed-in cap.

usage: python3 moon.py            -> previews + stats for 1x, 2x, 4x
       python3 moon.py --stl      -> also writes printable STL pieces per version
"""
import sys, json, math, os
import numpy as np
import trimesh
import manifold3d as mf
from scipy.spatial import Delaunay, cKDTree

EDGE = 304.8                      # 1 ft along each corner edge
SHELL = 3.0                       # shell thickness (radial)
FLANGE_W, FLANGE_T = 16.0, 2.4    # mounting lip lying flat on walls/ceiling
BED = np.array([210.0, 210.0, 240.0])   # Creality K1C 220x220x250 minus margin
PLA = 1.24
D = np.ones(3) / math.sqrt(3)     # corner diagonal, pointing into the room
E1 = np.array([1, -1, 0]) / math.sqrt(2)
E2 = np.cross(D, E1)

def center_offset(R):
    # |(EDGE,0,0) + c(1,1,1)| = R  ->  3c^2 + 2*EDGE*c + EDGE^2 - R^2 = 0
    return (-2*EDGE + math.sqrt(4*EDGE**2 - 12*(EDGE**2 - R**2))) / 6

# ------------------------------------------------------------------ moon surface (unit sphere)
class Moon:
    """Procedural moon relief in *angular* units, shared by all scales, so the 2x/4x
    versions are genuinely zoomed-in views of the same moon."""
    def __init__(self, seed=1969):
        rng = np.random.default_rng(seed)
        # craters within 62 deg of the corner diagonal (covers every version)
        cap = math.radians(62)
        area_deg2 = 2*math.pi*(1 - math.cos(cap)) * (180/math.pi)**2
        dmin, dmax = 0.28, 26.0                       # crater diameters, degrees of arc
        n = int(0.075 * area_deg2 / dmin**2)          # N(>D) ~ D^-2 (near-saturated, like the highlands)
        u = rng.random(n)
        Dd = dmin / np.sqrt(1 - u*(1 - (dmin/dmax)**2))
        dirs = self._random_cap(rng, n, cap)
        self.c_dir, self.c_D = dirs, np.radians(Dd)
        self.c_fresh = rng.random(n)                  # 1 = crisp young crater, 0 = worn
        # a few big impact basins -> maria (smooth dark low plains)
        self.m_dir = self._random_cap(rng, 4, math.radians(55))
        self.m_r = np.radians(rng.uniform(14, 26, 4))
        # one young rayed crater (like Tycho)
        self.ray_dir = self._random_cap(rng, 1, math.radians(18))[0]
        self.ray_D = math.radians(4.2)
        self.ray_ang = rng.uniform(0, 2*np.pi, 14)
        self.ray_len = np.radians(rng.uniform(10, 30, 14))
        self.tree = cKDTree(self.c_dir)

    @staticmethod
    def _random_cap(rng, n, cap):
        z = rng.uniform(math.cos(cap), 1, n); phi = rng.uniform(0, 2*np.pi, n)
        s = np.sqrt(1 - z*z)
        loc = np.c_[s*np.cos(phi), s*np.sin(phi), z]
        return loc[:, 0:1]*E1 + loc[:, 1:2]*E2 + loc[:, 2:3]*D

    def mare(self, n):
        m = np.zeros(len(n))
        for d, r in zip(self.m_dir, self.m_r):
            ang = np.arccos(np.clip(n @ d, -1, 1))
            m = np.maximum(m, 1/(1 + np.exp((ang - r)/math.radians(1.6))))
        return m

    def height(self, n, R):
        """Radial relief in mm for unit directions n on a moon of radius R (mm)."""
        h = np.zeros(len(n))
        mare = self.mare(n)
        h -= 2.2 * mare * min(1.0, R/305)                    # maria sit low
        order = np.argsort(-self.c_D)
        for i in order:
            Dm = self.c_D[i] * R                              # diameter in mm on this moon
            if Dm < 3.0:                                      # too small to print at this scale
                continue
            rr = self.c_D[i] * 2.2
            idx = self.tree.query_ball_point(self.c_dir[i], rr) if False else None
            ang = np.arccos(np.clip(n @ self.c_dir[i], -1, 1))
            sel = ang < rr
            if not sel.any():
                continue
            x = ang[sel] / (self.c_D[i]/2)                   # 1 at rim
            fresh = 0.45 + 0.55*self.c_fresh[i]
            depth = min(0.2*Dm, 1.2 + 0.07*Dm, 9.0) * fresh   # simple -> complex crater flattening
            rim = 0.22*depth
            inner = -depth*(1 - x**2) + rim
            if Dm > 45:                                       # central peak + flat floor
                inner = np.maximum(inner, -depth*0.75 + rim) + 0.5*depth*np.exp(-(x/0.18)**2)
            outer = rim * np.clip(x, 1, None)**-3.2
            prof = np.where(x < 1, inner, outer)
            # craters on maria are partly flooded / softer
            prof *= 1 - 0.35*mare[sel]
            # newer craters overprint older ones: blend toward the crater shape inside the rim
            w = np.clip(1.3 - x, 0, 1)
            h[sel] = h[sel]*(1 - w*0.85) + prof + (h[sel]*w*0.0)
        # fine regolith texture
        h += 0.25*np.sin(n @ np.array([31, 7, 19.0])*R/30) * np.sin(n @ np.array([-11, 29, 5.0])*R/30)
        return h

    def paint(self, n):
        """Paint-guide tone: 0 maria (dark grey), 1 highlands (light grey), 2 rays/fresh (white)."""
        tone = np.where(self.mare(n) > 0.5, 0, 1)
        # rays
        rel = n - np.outer(n @ self.ray_dir, self.ray_dir)
        a1 = np.cross(self.ray_dir, [0, 0, 1.0]); a1 /= np.linalg.norm(a1); a2 = np.cross(self.ray_dir, a1)
        phi = np.arctan2(rel @ a2, rel @ a1)
        ang = np.arccos(np.clip(n @ self.ray_dir, -1, 1))
        for A, L in zip(self.ray_ang, self.ray_len):
            dphi = np.abs(np.angle(np.exp(1j*(phi - A))))
            on = (dphi < 0.018*(1 - ang/L)) & (ang < L) & (ang > self.ray_D*0.6)
            tone = np.where(on, 2, tone)
        tone = np.where(ang < self.ray_D*0.62, 2, tone)                               # bright young crater
        return tone

MOON = Moon()

# ------------------------------------------------------------------ mesh building
def disc_points(rho_max, step):
    pts = []
    for j, y in enumerate(np.arange(-rho_max, rho_max + step, step*0.866)):
        off = step/2 if j % 2 else 0
        for x in np.arange(-rho_max + off, rho_max + step, step):
            if x*x + y*y < (rho_max - step*0.3)**2:
                pts.append((x, y))
    ring = int(2*math.pi*rho_max/step)
    for t in np.linspace(0, 2*np.pi, ring, endpoint=False):
        pts.append((rho_max*math.cos(t), rho_max*math.sin(t)))
    return np.array(pts), ring

def surface_solid(R, c, radial_offset, rho_max, step, back=-60.0, relief=True):
    """Closed solid: moon surface (radius R+offset, with relief) extruded back along -D."""
    C = -c*np.ones(3)
    P2, ring = disc_points(rho_max, step)
    tri = Delaunay(P2).simplices
    rho2 = (P2**2).sum(1)
    s = np.sqrt(np.clip(R**2 - rho2, 0, None))
    base = C + P2[:, :1]*E1 + P2[:, 1:2]*E2 + s[:, None]*D
    n = (base - C) / R
    h = MOON.height(n, R) if relief else np.zeros(len(n))
    top = C + n*(R + radial_offset + h)[:, None]
    # back face: push each point straight back along -D to the plane d.p = back
    bot = top - ((top @ D) - back)[:, None]*D
    N = len(top)
    V = np.vstack([top, bot])
    F = [t for t in tri] + [t[::-1] + N for t in tri]
    bidx = np.arange(N - ring, N)                    # boundary ring (last points, in order)
    for k in range(ring):
        a, b = bidx[k], bidx[(k+1) % ring]
        F += [[a, b, b+N], [a, b+N, a+N]]
    m = trimesh.Trimesh(V, np.array(F), process=True)
    trimesh.repair.fix_normals(m)
    return m, n, h

def to_mf(m):
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices, np.float32),
                               tri_verts=np.asarray(m.faces, np.uint32)))
def to_tm(M):
    g = M.to_mesh()
    return trimesh.Trimesh(np.asarray(g.vert_properties)[:, :3], np.asarray(g.tri_verts), process=False)

def octant(extra=0.0):
    return mf.Manifold.cube([2000, 2000, 2000]).translate([extra, extra, extra])

def build(mult, step=None):
    R = EDGE*mult
    c = center_offset(R)
    rho_max = EDGE*math.sqrt(2/3) + 25
    step = step or 1.8
    outer, n, h = surface_solid(R, c, 0.0, rho_max, step)
    inner, _, _ = surface_solid(R, c, -SHELL, rho_max, step)
    lip, _, _ = surface_solid(R, c, -SHELL - FLANGE_W, rho_max, step*3, relief=False)
    O, I, L = to_mf(outer), to_mf(inner), to_mf(lip)
    room = octant()
    shell = (O - I) ^ room
    # flanges: thin slabs on each of the 3 planes, between the shell and an inset sphere
    slab = (mf.Manifold.cube([FLANGE_T, 2000, 2000]) + mf.Manifold.cube([2000, FLANGE_T, 2000])
            + mf.Manifold.cube([2000, 2000, FLANGE_T]))
    flange = ((O - L) ^ slab) ^ room
    part = shell + flange
    return dict(mult=mult, R=R, c=c, solid=part, outer=outer,
                bulge=R - c*math.sqrt(3), flat=EDGE/math.sqrt(3))

# ------------------------------------------------------------------ splitting for the K1C
def fits(m):
    ext = np.sort(trimesh.bounds.oriented_bounds(m)[1])
    return bool(np.all(ext <= np.sort(BED)))

def split(M, depth=0):
    tm = to_tm(M)
    if fits(tm) or depth > 6:
        return [M]
    # cut with planes through the corner diagonal first (keeps pieces wedge-shaped)
    T, ext = trimesh.bounds.oriented_bounds(tm)
    ax = np.linalg.inv(T)[:3, int(np.argmax(ext))]
    off = float(ax @ tm.centroid)
    out = []
    for p in (M.trim_by_plane(list(ax), off), M.trim_by_plane(list(-ax), -off)):
        for comp in p.decompose():
            if comp.volume() > 20:
                out += split(comp, depth + 1)
    return out

def wedge_split(M, k):
    """Split into k wedges around the corner diagonal (symmetric, tidy seams)."""
    pieces = []
    for i in range(k):
        a0, a1 = 2*np.pi*i/k, 2*np.pi*(i+1)/k
        n0 = -(-math.sin(a0)*E1 + math.cos(a0)*E2)   # keep side angle > a0
        n1 = (-math.sin(a1)*E1 + math.cos(a1)*E2)    # keep side angle < a1
        p = M.trim_by_plane(list(-n0), 0.0).trim_by_plane(list(-n1), 0.0)
        pieces.append(p)
    return pieces

if __name__ == "__main__":
    write = "--stl" in sys.argv
    stats = []
    for mult in (1, 2, 4):
        b = build(mult)
        solid = b["solid"]
        pieces = []
        for w in wedge_split(solid, 3):
            pieces += split(w)
        grams = solid.volume()/1000*PLA
        st = dict(version=f"{mult}x", moon_radius_mm=round(b["R"]), center_behind_corner_mm=round(b["c"]*math.sqrt(3)),
                  depth_from_corner_mm=round(b["bulge"]), bulge_past_flat_mm=round(b["bulge"] - b["flat"]),
                  pieces=len(pieces), grams=round(grams))
        stats.append(st); print(json.dumps(st))
        tm = to_tm(solid); tm.export(f"moon_{mult}x_preview.ply") if False else None
        np.save(f".mesh_{mult}x.npy", np.array([0]))
        if write:
            os.makedirs(f"stl_{mult}x", exist_ok=True)
            for k, p in enumerate(pieces):
                to_tm(p).export(f"stl_{mult}x/moon_{mult}x_part{k+1}.stl")
        trimesh.exchange.export.export_mesh(tm, f".moon_{mult}x.glb") if False else None
        import pickle; pickle.dump((tm.vertices, tm.faces), open(f".moon_{mult}x.pkl", "wb"))
    json.dump(stats, open("stats.json", "w"), indent=1)
