"""Crop the vanilla sprites the user named on 5 Oct for the water checklist page.

Usage: python3 crop_checklist.py <DF data/vanilla dir>
Writes checklist/<name>.png: each named 32 px tile (or strip of tiles), scaled 2x, nearest neighbour.
Coordinates are DF's own (column, row from 0); the page labels them the way the user counted (from 1).
"""
import os, sys
from PIL import Image

V = sys.argv[1]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'checklist')
os.makedirs(OUT, exist_ok=True)
SHEETS = {
    'standard': 'vanilla_plants_graphics/graphics/images/plant_standard.png',
    'crops': 'vanilla_plants_graphics/graphics/images/plant_crops.png',
    'grass_other': 'vanilla_plants_graphics/graphics/images/grass_other.png',
    'cavern_grass': 'vanilla_plants_graphics/graphics/images/cavern_grass.png',
    'boulders': 'vanilla_items_graphics/graphics/images/boulders.png',
    'nature': 'vanilla_items_graphics/graphics/images/item_nature.png',
    'driftwood': 'vanilla_environment/graphics/images/driftwood.png',
}
img = {k: Image.open(os.path.join(V, p)).convert('RGBA') for k, p in SHEETS.items()}

def strip(name, sheet, cells):
    """cells: list of (col, row) tiles laid left to right with a 4 px gap."""
    w = len(cells) * 36 - 4
    out = Image.new('RGBA', (w, 32), (0, 0, 0, 0))
    for i, (c, r) in enumerate(cells):
        out.paste(img[sheet].crop((c * 32, r * 32, c * 32 + 32, r * 32 + 32)), (i * 36, 0))
    out.resize((w * 2, 64), Image.NEAREST).save(os.path.join(OUT, name + '.png'))

strip('reed-rope', 'standard', [(0, 14)])                      # the reed seen in Shortsling (E37 river plant)
strip('grass-longland', 'standard', [(0, 10)])                 # E37's other river plant
strip('crops-r11', 'crops', [(0, 10), (0, 11)])                 # user's "column 1 row 11": sorghum (row 11 from 1) / rice (row 11 from 0)
strip('papyrus-sedge', 'crops', [(0, 33), (6, 33), (7, 33)])   # DF's actual papyrus sedge: shrub, crop, sprout
strip('pool-r1c8', 'crops', [(7, 0)])                           # user's "first row 8th column" for pool beds
strip('coral-candidates', 'crops', [(0, 16), (0, 17), (0, 18), (0, 19), (3, 17), (5, 19)])  # pink/red: amaranths, red spinach
strip('grass-other-r2', 'grass_other', [(c, 1) for c in range(4)])
strip('cavern-last3', 'cavern_grass', [(c, r) for r in range(3) for c in (17, 18, 19)])
strip('cavern-last3-r2', 'cavern_grass', [(17, 1), (18, 1), (19, 1)])
strip('boulders', 'boulders', [(0, 1), (0, 3), (0, 4), (0, 6), (0, 7), (1, 12), (0, 13), (1, 13)])
strip('branch', 'nature', [(0, 0)])
dw = img['driftwood']
strip('driftwood', 'driftwood', [(c, r) for r in range(dw.height // 32) for c in range(dw.width // 32)][:6])
print(sorted(os.listdir(OUT)))
