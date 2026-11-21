import sys, pickle, numpy as np
import scene2 as S
import render as R
R.S.RGB.update(S.RGB)                     # frame colours for the shared renderer
R.S.W, R.S.H, R.S.BASE = S.W, S.H, S.BASE
if __name__ == "__main__":
    facets, h = S.build_facets()
    best = None
    for ox in np.arange(-190, 1, 10):
        for oy in np.arange(-190, 1, 10):
            t = S.cairo_tiles(100, (ox, oy)); full = t[0]["full"].area
            sc = (sum(x["poly"].area/full < .3 for x in t), len(t))
            if best is None or sc < best[0]: best = (sc, ox, oy)
    tiles = S.cairo_tiles(100, (best[1], best[2]))
    pickle.dump(dict(facets=facets, h=h, origin=(best[1], best[2])), open(".scene2.pkl", "wb"))
    print("facets", len(facets), "tiles", len(tiles), "origin", best[1:], "max z", round(float(h.max()), 1))
    R.front(facets, tiles, "v2_wall_painted.png", px=0.9, numbers=True)
    R.front(facets, tiles, "v2_wall_clean.png", px=0.9, numbers=False)
    frames = []
    for xs in np.linspace(-700, S.W + 700, 14):
        frames.append(R.perspective(facets, None, (xs, 520, 1500), size=(1000, 680), fov=50, tiles=None))
    frames += frames[::-1][1:-1]
    frames[0].save("v2_walk_by.gif", save_all=True, append_images=frames[1:], duration=110, loop=0)
    frames[3].save("v2_walk_left.png")
    # close-up of the throat pleats from an oblique angle (standing near, looking along the wall)
    R.perspective(facets, "v2_closeup.png", (1350, 180, 420), size=(1000, 680), fov=55)
