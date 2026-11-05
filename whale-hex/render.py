"""Front preview (raking light), assembly map, and an angled 3D view."""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from shapely.geometry import Polygon, LineString, Point
from shapely.ops import unary_union
import design as D

WALL = "#e8e2d8"
LIGHT = np.array([-0.5, -0.6, 0.62]); LIGHT /= np.linalg.norm(LIGHT)   # upper-left lamp

def lit(f, flat=False):
    rgb = np.array(matplotlib.colors.to_rgb(D.FIL[f["color"]]))
    if flat: return rgb
    k = 0.45 + 0.75*max(np.dot(f["n"], LIGHT), 0)
    return np.clip(rgb*k, 0, 1)

def add(ax, g, col, **kw):
    for p in getattr(g, "geoms", [g]):
        if p.geom_type == "Polygon" and p.area > .3:
            ax.add_patch(MPoly(np.asarray(p.exterior.coords), fc=col, ec=col, lw=.25, **kw))

def front(scene, path, labels=False, dpi=170):
    hexes = scene["hexes"]
    tiles = unary_union([h["poly"] for h in hexes])
    minx, miny, maxx, maxy = tiles.bounds; pad = 45
    fig = plt.figure(figsize=((maxx-minx+2*pad)/100, (maxy-miny+2*pad)/100), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off"); ax.set_aspect("equal")
    ax.set_xlim(minx-pad, maxx+pad); ax.set_ylim(maxy+pad, miny-pad); fig.patch.set_facecolor(WALL)
    add(ax, unary_union([D.hex_poly(h["cx"]+7, h["cy"]+9) for h in hexes]), "#cdc4b6")
    for f in scene["facets"]:
        g = Polygon(f["pts"]).intersection(tiles)
        if not g.is_empty: add(ax, g, lit(f, labels))
    body = scene["whale_area"]
    for pl, w in scene["lines"]:
        add(ax, LineString(pl).buffer(w/2).intersection(body).intersection(tiles), "#0e1833")
    add(ax, Point(scene["eye"]).buffer(7).intersection(tiles), "#0b1226")
    add(ax, Point(scene["eye"][0]-2, scene["eye"][1]-2).buffer(2), "#dfefff")
    for h in hexes:
        ax.plot(*np.asarray(h["poly"].exterior.coords).T, color=WALL, lw=2.4 if not labels else 1.2)
        if labels:
            ax.text(h["cx"], h["cy"], h["label"], ha="center", va="center", fontsize=10, fontweight="bold",
                    bbox=dict(boxstyle="round,pad=.25", fc="white", ec="none", alpha=.85))
    if labels:
        ax.text(minx, maxy+pad*.6, f"{len(hexes)} tiles · {D.HEX_F:.0f} mm flat-to-flat · overall "
                f"{maxx-minx:.0f} × {maxy-miny:.0f} mm · tallest point {max(f['z'].max() for f in scene['facets'])+D.BASE:.0f} mm",
                fontsize=10, color="#333", va="center")
    fig.savefig(path, dpi=dpi, facecolor=WALL); plt.close(fig)
    return maxx-minx, maxy-miny

def angled(scene, path, elev=28, azim=-115, dpi=150):
    hexes = scene["hexes"]
    tiles = unary_union([h["poly"] for h in hexes])
    polys, cols = [], []
    for f in scene["facets"]:
        g = Polygon(f["pts"]).intersection(tiles)
        if g.is_empty or g.geom_type != "Polygon" or g.area < 1: continue
        # z for clipped vertices via barycentric interpolation on the facet plane
        A = np.c_[f["pts"], np.ones(3)]; coef = np.linalg.lstsq(A, f["z"], rcond=None)[0]
        xy = np.asarray(g.exterior.coords)
        polys.append(np.c_[xy[:, 0], xy[:, 1], xy @ coef[:2] + coef[2] + D.BASE])
        cols.append(lit(f))
    # tile side walls (thin) for the base plate edge
    fig = plt.figure(figsize=(11, 9), dpi=dpi); fig.patch.set_facecolor(WALL)
    ax = fig.add_subplot(111, projection="3d"); ax.set_facecolor(WALL)
    pc = Poly3DCollection(polys, facecolors=cols, edgecolors=cols, linewidths=.2)
    ax.add_collection3d(pc)
    minx, miny, maxx, maxy = tiles.bounds
    ax.set_xlim(minx, maxx); ax.set_ylim(maxy, miny); ax.set_zlim(0, 140)
    ax.set_box_aspect((maxx-minx, maxy-miny, 140), zoom=1.35)
    ax.view_init(elev=elev, azim=azim); ax.axis("off")
    fig.savefig(path, dpi=dpi, facecolor=WALL, bbox_inches="tight"); plt.close(fig)

if __name__ == "__main__":
    s = D.build()
    print("tiles", len(s["hexes"]), "size", [round(v) for v in front(s, "preview_front.png")])
    front(s, "preview_map.png", labels=True, dpi=110)
    angled(s, "preview_angle.png")
