# bandscan.py IMG... [--T 48 --oy 4 --y0 100 --y1 1015 --x0 10 --x1 1640]
# A torn/half-drawn tile row shows as a step INSIDE the tiles (not at a tile edge) at the same height right along the row.
# Per tile: the biggest |mean(above split) - mean(below split)| over splits 6..T-6. A row is banded when more than half
# its tiles (80%) step (>12 grey levels) at the same split (+-1).
import sys, numpy as np, argparse
from PIL import Image
ap = argparse.ArgumentParser(); ap.add_argument('imgs', nargs='+')
for k, v in dict(T=48, oy=4, y0=100, y1=1015, x0=10, x1=1640, m=6).items(): ap.add_argument('--' + k, type=int, default=v)
o = ap.parse_args(); T = o.T
tx0, tx1 = o.x0 // T + 1, o.x1 // T
ty0 = -(-(o.y0 - o.oy) // T); ty1 = (o.y1 - o.oy) // T
tot = 0; hitf = 0
for f in o.imgs:
    a = np.asarray(Image.open(f).convert('L'), dtype=np.float32)
    ty1f = min(ty1, (a.shape[0] - o.oy) // T)
    blk = a[o.oy + ty0 * T:o.oy + ty1f * T, tx0 * T:tx1 * T]
    nr, nc = blk.shape[0] // T, blk.shape[1] // T
    prof = blk.reshape(nr, T, nc, T).mean(axis=3)              # (row, y in tile, col)
    c = np.cumsum(prof, axis=1); tot_ = c[:, -1:, :]
    s = np.arange(o.m, T - o.m + 1)
    above = c[:, s - 1, :] / s[None, :, None]; below = (tot_ - c[:, s - 1, :]) / (T - s)[None, :, None]
    d = np.abs(above - below); best = d.max(axis=1); arg = s[d.argmax(axis=1)]
    rows = []
    for r in range(nr):
        strong = arg[r][best[r] > 12]
        if len(strong):
            vals, cnt = np.unique(strong, return_counts=True); v = vals[cnt.argmax()]
            n = int(((strong >= v - 1) & (strong <= v + 1)).sum())
            if n >= 0.8 * nc: rows.append((ty0 + r, int(v), n, nc))
    tot += len(rows); hitf += bool(rows)
    if rows: print(f'{f.split("/")[-1]}: banded tile rows (row, split, tiles, of) {rows}')
print(f'bandscan: {tot} banded rows in {hitf} of {len(o.imgs)} images')
