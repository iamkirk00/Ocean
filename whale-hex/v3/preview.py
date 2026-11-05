import numpy as np, whale3d as W, render3d as R, time, sys
t0 = time.time()
for name, fn in (("single", W.scene_single), ("corner", W.scene_corner)):
    sc = fn()
    print(name, "tiles", len(sc["tiles"]), "whale parts", len(sc["whale"]),
          "max out", round(max(m.bounds[1][2] for m in sc["whale"])) if name == "single" else
          [round(max(m.bounds[1][0] for m in sc["whale"])), round(max(m.bounds[1][2] for m in sc["whale"]))],
          f"{time.time()-t0:.0f}s")
    if name == "single":
        R.render(sc, (1500, 1300, 1900), (330, 1300, 120), f"{name}_room.png")
        R.render(sc, (-700, 1450, 1800), (330, 1330, 150), f"{name}_approach.png")
    else:
        R.render(sc, (1900, 1350, 1900), (250, 1300, 200), f"{name}_room.png")
        R.render(sc, (2300, 1400, 700), (300, 1320, 200), f"{name}_approach.png")
