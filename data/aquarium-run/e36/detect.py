"""Flag map cells darker than all 8 neighbours by a near-uniform multiply (the 'square' glitch).
usage: detect.py TILEPX img... ; prints per image the flagged cells (cx, cy, ratio rgb)."""
import sys
import numpy as np
from PIL import Image
t = int(sys.argv[1])
tot = 0
for f in sys.argv[2:]:
    a = np.asarray(Image.open(f).convert('RGB')).astype(float)
    H, W = a.shape[0] // t, a.shape[1] // t
    m = a[:H * t, :W * t].reshape(H, t, W, t, 3).mean(axis=(1, 3))
    hits = []
    for y in range(4, H - 2):          # skip the top bar rows
        for x in range(1, W - 7):      # skip the right panel
            nb = np.array([m[y + dy, x + dx] for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx])
            med = np.median(nb, axis=0)
            if med[1] < 50 or (np.abs(nb - med).max(axis=1) <= 12).sum() < 5:   # dark UI / mixed surroundings
                continue
            if y > H - 8 and (x < 30 or 42 < x < 78):   # notification box, toolbar
                continue
            r = m[y, x] / np.maximum(med, 1)
            if r[1] < 0.8 and r[2] < 0.85 and r[0] < 0.9:
                hits.append((x, y, tuple(np.round(r, 2))))
    tot += len(hits)
    print(f.split("/")[-1], len(hits), hits)
print('TOTAL', tot)
