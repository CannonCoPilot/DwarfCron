# shiftcheck.py FRAMEDIR [tile_px] [x0 x1 y0 y1]: consecutive frames during a vertical pan should be the previous
# frame slid by whole tiles; find the slide, then score each tile row of the overlap. A torn or half-drawn
# row scores high where its neighbours score low.
import sys, os, numpy as np
from PIL import Image
d = sys.argv[1]; T = int(sys.argv[2]) if len(sys.argv) > 2 else 48
x0, x1, y0, y1 = (int(v) for v in (sys.argv[3:7] if len(sys.argv) > 6 else (10, 1640, 120, 1015)))
fs = sorted(f for f in os.listdir(d) if f.endswith('.png'))
load = lambda f: np.asarray(Image.open(os.path.join(d, f)).convert('RGB'), dtype=np.float32)
prev = load(fs[0]); bad = 0; moved = 0
for i in range(1, len(fs)):
    cur = load(fs[i])
    best = None
    for k in range(0, 18):                     # camera down by k tiles => content moves up k*T px
        s = k * T
        a = prev[y0 + s:y1, x0:x1]; b = cur[y0:y1 - s, x0:x1]
        e = np.abs(a - b).mean()
        if best is None or e < best[1]: best = (k, e)
    k, e = best
    if k:
        moved += 1
        s = k * T; a = prev[y0 + s:y1, x0:x1]; b = cur[y0:y1 - s, x0:x1]
        diff = np.abs(a - b).mean(axis=(1, 2))           # per pixel row
        # per 8-px strip
        strips = diff[: len(diff) // 8 * 8].reshape(-1, 8).mean(axis=1)
        med = np.median(strips)
        hot = [(int(y0 + j * 8), round(float(v), 1)) for j, v in enumerate(strips) if v > max(4 * med, 12)]
        if hot:
            bad += 1
            print(f'{fs[i]} slide {k} tiles, mean err {e:.1f}, median strip {med:.1f}, hot strips (screen y, err): {hot[:10]}')
    prev = cur
print(f'{moved} moved frames, {bad} with a hot strip')
# --- still frames: the camera did not move, but a whole tile row changed (a glitch shown, then repaired)
oy = 4
prev = load(fs[0]); still_hits = 0
for i in range(1, len(fs)):
    cur = load(fs[i])
    e = np.abs(cur - prev)[y0:y1, x0:x1]
    if e.mean() > 0.3:
        moved_here = min(np.abs(prev[y0 + k * T:y1, x0:x1] - cur[y0:y1 - k * T, x0:x1]).mean() for k in range(1, 18)) < e.mean() * 0.5
        if not moved_here:
            rows = e.mean(axis=(1, 2))
            hot = []
            for t in range((y0 - oy) // T, (y1 - oy) // T + 1):
                a, b = max(oy + t * T, y0) - y0, min(oy + (t + 1) * T, y1) - y0
                if b > a and rows[a:b].mean() > 2.0: hot.append((t, round(float(rows[a:b].mean()), 1)))
            if hot:
                still_hits += 1
                print(f'{fs[i]} no camera move, tile rows changed (row, err): {hot[:10]}')
    prev = cur
print(f'{still_hits} still frames with a changed tile row')
