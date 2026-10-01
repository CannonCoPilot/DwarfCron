"""Build a prototype 'translucent_water' graphics mod from the vanilla liquids.png.
Overrides UNDERWATER_1..7 (+ _LABEL) via a new tile page; magma left untouched."""
import sys
from PIL import Image
src, out = sys.argv[1], sys.argv[2]
# alpha per depth row (row 0 = depth 7 ... row 6 = depth 1); vanilla is 255,255,255,255,230,204,179
ALPHA = [150, 140, 130, 120, 110, 100, 90]
im = Image.open(src).convert('RGBA')
px = im.load()
for col in (0, 2):                      # col 0 = UNDERWATER_n, col 2 = UNDERWATER_n_LABEL
    for row in range(7):
        for y in range(row*32, row*32+32):
            for x in range(col*32, col*32+32):
                r, g, b, a = px[x, y]
                if a == 0: continue
                if col == 2 and min(r, g, b) > 200:   # keep depth digits opaque
                    continue
                px[x, y] = (r, g, b, ALPHA[row])
im.save(out)
print('wrote', out)
