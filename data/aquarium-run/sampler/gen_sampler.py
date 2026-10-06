"""Generate wave / foam / mist / shimmer sprite variants for the aquarium plugin's graphics sampler.

Each variant is a 32x32 sprite with 4 frames. For the sampler page we bake each into a 4x3-tile scene
(per frame) over DF's own tiles (sand floor, depth-4 water) and write a 4-frame horizontal strip PNG.
Outputs: out/<id>.png (scene strip, 128x96 per frame) and out/<id>-tile.png (raw 32px frame strip).
"""
import json, math, os, sys
import numpy as np
from PIL import Image

G = sys.argv[1]  # DF vanilla_environment/graphics dir
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
os.makedirs(OUT, exist_ok=True)
F = 4
yy, xx = np.mgrid[0:32, 0:32].astype(float)
cx, cy = xx - 15.5, yy - 15.5

def tile(path, col, row):
    im = Image.open(os.path.join(G, 'images', path)).convert('RGBA')
    return np.asarray(im.crop((col * 32, row * 32, col * 32 + 32, row * 32 + 32))).astype(float) / 255

SAND = tile('sand_floor.png', 0, 0)
WATER = tile('liquids.png', 0, 3)
MIST = [tile('event_flows.png', 2, r) for r in range(4)]

def h(a):
    a = np.asarray(a, dtype=np.uint64) & 0xffffffff
    a ^= a >> 16; a = (a * 0x7feb352d) & 0xffffffff; a ^= a >> 15; a = (a * 0x846ca68b) & 0xffffffff; a ^= a >> 16
    return a

def vnoise(x, y, grid, seed, period=None):
    u, v = x / grid, y / grid
    i, j = np.floor(u).astype(np.int64), np.floor(v).astype(np.int64)
    fu, fv = u - i, v - j
    su, sv = fu * fu * (3 - 2 * fu), fv * fv * (3 - 2 * fv)
    def lat(a, b):
        if period:
            n = int(period / grid); a, b = a % n, b % n
        return (h(a * 7919 + b * 104729 + seed * 1299709) % 1000) / 1000.0
    return (lat(i, j) * (1 - su) + lat(i + 1, j) * su) * (1 - sv) + (lat(i, j + 1) * (1 - su) + lat(i + 1, j + 1) * su) * sv

def ss(a, b, t):
    k = np.clip((t - a) / (b - a), 0, 1); return k * k * (3 - 2 * k)

def rgba(a, r=245, g=250, b=252):
    out = np.zeros((32, 32, 4)); out[..., 0], out[..., 1], out[..., 2] = r / 255, g / 255, b / 255
    out[..., 3] = np.clip(a, 0, 1); return out

# ---------------- crests (travel = east, so the crest line runs north-south) ----------------
def crest_plugin(f, wx, wy):  # what the plugin draws now: soft core, lace, shoulder, streaky wake
    bob = 1.2 * math.sin(2 * math.pi * f / 4); d = cx - (1 + bob)
    t = (cy + wy * 32) / 32
    lace = 0.4 + 0.6 * (0.6 * vnoise(t * 32, 0 * t + f * 1.6, 5.3, 5, 32) + 0.4 * vnoise(t * 32, 0 * t - f, 2, 13, 32))
    core = np.exp(-d * d / 8) * lace; ahead = np.where(d > 0, 0.2 * np.exp(-d * d / 24.5), 0)
    streak = 0.25 + 0.75 * vnoise(cy + wy * 32, 0 * cy, 2, 9, 32) ** 1.5
    wake = np.where(d < 0, 0.5 * np.exp(d / 7) * streak, 0)
    w = core / (core + wake + ahead + 1e-6)
    a = np.clip(core + ahead + wake, 0, 1) * 0.85
    o = rgba(a); o[..., 0] = (200 + 48 * w) / 255; o[..., 1] = (228 + 24 * w) / 255; o[..., 2] = (236 + 19 * w) / 255
    return o

def crest_whitecap(f, wx, wy):  # breaking crest: ragged white lip plus spray specks thrown forward
    gy = cy + wy * 32
    lip = 1.5 + 2.5 * (vnoise(gy, f * 3.0, 4, 21, 32) - 0.5)
    d = cx - lip
    body = ss(-4, 0, d) * (1 - ss(0, 1.2, d))
    foam = np.where(d < 0, np.exp(d / 3.5) * (vnoise(xx + f * 2, gy, 2.5, 4, 32) > 0.55), 0) * 0.7
    spray = ((h((xx.astype(int) + 7 * f) * 31 + (gy.astype(int)) * 97) % 100) < 6) & (d > 1) & (d < 6)
    return rgba(np.maximum(body, foam) + spray * 0.8)

def crest_swell(f, wx, wy):  # unbroken swell: two soft parallel bands (crest + trough shadow), no foam
    p = cx - (-3 + 6 * f / 4)
    light = np.exp(-p * p / 6); dark = np.exp(-(p + 5) ** 2 / 10)
    o = rgba(light * 0.55, 230, 245, 250)
    sh = rgba(dark * 0.35, 10, 50, 70)
    return over(o, sh)

def crest_pixel(f, wx, wy):  # DF-style hard pixels: a 2px white line with a 1px pale-blue shadow, stepped
    gy = (cy + wy * 32).astype(int)
    step = ((gy // 4 + f) % 3) - 1
    x0 = 16 + step
    a = np.zeros((32, 32)); a[(xx.astype(int) == x0) | (xx.astype(int) == x0 + 1)] = 0.95
    s = np.zeros((32, 32)); s[xx.astype(int) == x0 - 1] = 0.6
    return over(rgba(s, 150, 205, 220), rgba(a))

def crest_ascii(f, wx, wy):  # literal ASCII '~' glyphs riding the front: 3 per tile column, bob
    a = np.zeros((32, 32))
    for k, y0 in enumerate((5, 15, 25)):
        u = cy - (y0 - 15.5) - (1 if (f + k) % 2 else 0)
        cxv = cx
        curve = 2.0 * np.sin(2 * math.pi * (cy - (y0 - 15.5)) / 10)
        m = (np.abs(cy - (y0 - 15.5)) < 5)
        dist = np.abs(cxv - curve * 0) ; 
        # draw a sideways tilde: x = 1.6 sin(...) along y
        d2 = np.abs(cx - 1.6 * np.sin(2 * math.pi * u / 10))
        a = np.maximum(a, np.clip(1.2 - d2, 0, 1) * m)
    return rgba(a * 0.9)

# ---------------- landing foam (shore is south of the tile: landward = down) ----------------
def foam_wavelets(f, wx, wy):  # what the plugin draws now: two level '~'
    lay = [(-6, -5), (6, 5)] if (h(wx * 92821 + wy * 68917) & 1) == 0 else [(5, -6), (-6, 4.5)]
    surge = -1.5 * math.cos(2 * math.pi * f / 4); slide = math.sin(2 * math.pi * f / 4)
    a = np.zeros((32, 32)); half, amp, k = 6.0, 1.5, 2 * math.pi / 12
    for s0, s1 in lay:
        u = cx - s0 - slide
        taper = np.clip((half + 1 - np.abs(u)) / 2.5, 0, 1) * (np.abs(u) <= half + 1.5)
        curve = s1 + surge - amp * np.sin(k * u); sl = amp * k * np.cos(k * u)
        dist = np.abs(cy - curve) / np.sqrt(1 + sl * sl)
        a = np.maximum(a, np.clip(1 - (dist - 0.7), 0, 1) * taper)
    return rgba(a * 0.9)

def foam_swash(f, wx, wy):  # swash sheet running up the sand with a bright ragged lip
    lip = -6 + 14 * (0.5 - 0.5 * math.cos(2 * math.pi * f / 4))
    gx = cx + wx * 32
    edge = lip + 3 * (vnoise(gx, f * 2.0, 4, 3, 32) - 0.5)
    rim = np.exp(-(cy - edge) ** 2 / 3); behind = cy < edge
    lace = vnoise(gx, cy + f * 3, 5, 7, 32)
    a = np.where(cy > edge + 2.5, 0, np.minimum(1, 0.28 * behind + 0.45 * lace ** 2.2 * behind + rim * 0.85))
    w = np.clip(rim + lace ** 2.2 * behind, 0, 1)
    o = rgba(a); o[..., 0] = (150 + 100 * w) / 255; o[..., 1] = (205 + 45 * w) / 255; o[..., 2] = (215 + 35 * w) / 255
    return o

def foam_bubbles(f, wx, wy):  # clusters of round bubbles that pop and re-form
    a = np.zeros((32, 32))
    for k in range(9):
        r = h(wx * 131 + wy * 977 + k * 7919)
        bx, by = (r % 26) + 3 - 15.5, ((r >> 8) % 26) + 3 - 15.5
        life = ((r >> 16) + f) % 4
        rad = [1.2, 2.0, 2.6, 0][life]
        if rad == 0: continue
        d = np.sqrt((cx - bx) ** 2 + (cy - by) ** 2)
        ring = np.clip(1 - np.abs(d - rad) / 0.8, 0, 1)
        a = np.maximum(a, ring * (0.9 if life < 2 else 0.6))
    return rgba(a)

def foam_lace(f, wx, wy):  # world-anchored lace over a wet film (the 'wash on' foam)
    gx, gy = xx + wx * 32 + f * 2, yy + wy * 32 + f * 1.2
    n = 0.5 * vnoise(gx, gy, 8, 3, 512) + 0.35 * vnoise(gx, gy, 4, 11, 512) + 0.15 * vnoise(gx, gy, 2, 23, 512)
    a = ss(0.6, 0.7, n) * 0.7 + 0.12
    w = np.clip((a - 0.12) / 0.7, 0, 1)
    o = rgba(a * 0.8); o[..., 0] = (170 + 75 * w) / 255; o[..., 1] = (215 + 35 * w) / 255; o[..., 2] = (225 + 25 * w) / 255
    return o

def foam_line(f, wx, wy):  # a single continuous foam line along the water's edge that breathes
    reach = 8 + 3 * math.sin(2 * math.pi * f / 4)
    gx = cx + wx * 32
    edge = reach + 1.5 * (vnoise(gx, f * 1.0, 6, 31, 32) - 0.5) - 16
    d = cy - edge
    a = np.exp(-d * d / 2.2) * (0.6 + 0.4 * vnoise(gx, 0 * gx + f, 3, 41, 32))
    a += np.where(d < 0, 0.18 * np.exp(d / 4), 0)
    return rgba(a)

# ---------------- mist / spray ----------------
def mist_vanilla(f, wx, wy):  # DF's own FLOW_WATER_MIST frames, for reference
    return MIST[f].copy()

def mist_puffs(f, wx, wy):  # soft round puffs that drift landward and thin out
    a = np.zeros((32, 32))
    for k in range(3):
        r = h(wx * 53 + wy * 97 + k * 131)
        bx = ((r % 20) + 6 - 15.5); by = (((r >> 8) % 20) + 6 - 15.5) - 2.5 * f
        rad = 6 + 2 * f
        d2 = ((cx - bx) ** 2 + (cy - by) ** 2) / (rad * rad)
        a = np.maximum(a, np.exp(-d2 * 2.2) * (0.55 - 0.1 * f))
    a *= 0.75 + 0.25 * vnoise(xx + wx * 32, yy + wy * 32 - f * 3, 5, 61, 512)
    return rgba(a, 235, 242, 245)

def mist_dither(f, wx, wy):  # ASCII-faithful shade blocks: a 2x2 ordered dither at the frame's density
    lvl = [0.25, 0.5, 0.75, 0.5][f]
    bayer = np.array([[0, 2], [3, 1]]) / 4 + 0.125
    th = bayer[(yy.astype(int) // 2) % 2, (xx.astype(int) // 2) % 2]
    a = (th < lvl) * 0.55
    return rgba(a, 225, 232, 238)

def mist_wisps(f, wx, wy):  # thin streaks of wind-blown spray
    gx = xx + wx * 32 - f * 5; gy = yy + wy * 32
    n = vnoise(gx * 0.5, gy * 3, 4, 71, 512)
    a = ss(0.62, 0.8, n) * 0.6
    return rgba(a, 238, 244, 248)

# ---------------- surface shimmer skin (seen from above) ----------------
def shimmer_caustic(f, wx, wy):  # caustic web: bright where two noise ridges meet
    gx, gy = xx + wx * 32, yy + wy * 32
    n1 = vnoise(gx + f * 3, gy, 9, 81, 512); n2 = vnoise(gx, gy - f * 3, 7, 83, 512)
    r = 1 - np.abs(n1 - n2) * 6
    return rgba(np.clip(r, 0, 1) ** 3 * 0.35, 220, 245, 250)

def shimmer_glints(f, wx, wy):  # scattered sun glints that twinkle
    r = h((xx.astype(int) + wx * 32) * 73 + (yy.astype(int) + wy * 32) * 151 + f * 1013) % 1000
    a = (r < 6) * 0.9
    return rgba(a)

def shimmer_ripple(f, wx, wy):  # long low ripple lines drifting with the wind
    gx, gy = xx + wx * 32, yy + wy * 32
    p = np.sin((gy + 0.3 * gx + f * 2) * 2 * math.pi / 8 + 2 * vnoise(gx, gy, 12, 91, 512))
    return rgba(ss(0.85, 1.0, p) * 0.3, 210, 240, 248)

def over(a, b):  # b over a
    out = np.zeros_like(a)
    ab = b[..., 3:4]; aa = a[..., 3:4]
    oa = ab + aa * (1 - ab)
    out[..., :3] = np.where(oa > 0, (b[..., :3] * ab + a[..., :3] * aa * (1 - ab)) / np.maximum(oa, 1e-6), 0)
    out[..., 3:4] = oa
    return out

# scene layouts, 4 cols x 3 rows: S sand, W water; the sprite goes on cells marked with an uppercase in mask
SCENES = {
    'sea':   (['WWWW', 'WWWW', 'WWWW'], [(1, 0), (1, 1), (1, 2), (3, 0), (3, 1), (3, 2)]),
    'shore': (['WWWW', 'WWWW', 'SSSS'], [(0, 2), (1, 2), (2, 2), (3, 2)]),
    'mist':  (['WWWW', 'SSSS', 'SSSS'], [(0, 1), (1, 1), (2, 1), (3, 1), (1, 2), (2, 2)]),
    'skin':  (['WWWW', 'WWWW', 'WWWW'], [(c, r) for r in range(3) for c in range(4)]),
}

VARIANTS = [
    # id, group, scene, fn, title, note
    ('crest-plugin', 'crest', 'sea', crest_plugin, 'Soft crest (in the plugin now)', 'Gaussian core with broken lace, a faint shoulder ahead and a streaky wake. Bobs 1 px.'),
    ('crest-whitecap', 'crest', 'sea', crest_whitecap, 'Whitecap', 'Ragged breaking lip, foam behind it, spray specks thrown ahead.'),
    ('crest-swell', 'crest', 'sea', crest_swell, 'Unbroken swell', 'A pale crest band with a darker trough behind it; no foam. Reads as deep water.'),
    ('crest-pixel', 'crest', 'sea', crest_pixel, 'Hard pixel line', 'A 2 px white line with a 1 px blue shadow, stepped like DF\'s own pixel art.'),
    ('crest-ascii', 'crest', 'sea', crest_ascii, 'ASCII tildes', 'Three sideways \'~\' per tile riding the front, the literal ASCII look.'),
    ('foam-wavelets', 'foam', 'shore', foam_wavelets, 'Level \'~\' (in the plugin now)', 'Two white \'~\' per tile, bobbing and sliding. Placeholder.'),
    ('foam-swash', 'foam', 'shore', foam_swash, 'Swash sheet', 'Thin water sheet running up the sand with a bright ragged lip.'),
    ('foam-bubbles', 'foam', 'shore', foam_bubbles, 'Bubble clusters', 'Ring bubbles that grow, pop and re-form at random.'),
    ('foam-lace', 'foam', 'shore', foam_lace, 'Lace over a wet film', 'World-anchored lace, seamless across tiles (the old `wash on` foam).'),
    ('foam-line', 'foam', 'shore', foam_line, 'Breathing foam line', 'One continuous line along the edge that advances and retreats.'),
    ('mist-vanilla', 'mist', 'mist', mist_vanilla, 'DF\'s own mist (reference)', 'Vanilla FLOW_WATER_MIST, density frames 1-4, as DF draws spray today.'),
    ('mist-puffs', 'mist', 'mist', mist_puffs, 'Drifting puffs', 'Soft round puffs that drift inland, swell and thin out.'),
    ('mist-dither', 'mist', 'mist', mist_dither, 'Dithered shade', 'An ordered 2x2 dither at the density level, faithful to ASCII ░▒.'),
    ('mist-wisps', 'mist', 'mist', mist_wisps, 'Wind wisps', 'Thin streaks of blown spray moving with the wind.'),
    ('skin-caustic', 'skin', 'skin', shimmer_caustic, 'Caustic web', 'Bright where two drifting noise fields meet, like sunlight on shallows.'),
    ('skin-glints', 'skin', 'skin', shimmer_glints, 'Sun glints', 'Sparse single-pixel glints that twinkle frame to frame.'),
    ('skin-ripple', 'skin', 'skin', shimmer_ripple, 'Wind ripples', 'Long, low ripple lines drifting downwind.'),
]


# ---------------- falls: the lip (river running east into a drop at column 3) ----------------
UW = [tile('liquids.png', 0, 7 - d) for d in range(1, 8)]  # UW[d-1] = DF's UNDERWATER_d
FLOOR = tile('floors.png', 1, 7)  # DIRT_FLOOR_5; recoloured to the plugin's mud below
_l = (0.299 * FLOOR[..., 0] + 0.587 * FLOOR[..., 1] + 0.114 * FLOOR[..., 2]); _ml = _l.mean(); _t = _ml + (_l - _ml) * 0.45
MUD = np.dstack([np.clip(np.array(m) / 255 * _t / _ml, 0, 1) for m in (178, 136, 88)] + [np.ones((32, 32))])
LIP_DEPTH = [7, 5, 3]      # DF's depth on columns 0-2 as the water drains to the edge (measured 7..1)
LIP_SPEED = [0.35, 0.65, 1.0]

def lip_bg(f, c, r):
    if c == 3:  # the drop: open air over the falls, DF's mist on it
        o = np.zeros((32, 32, 4)); o[..., 0], o[..., 1], o[..., 2], o[..., 3] = 0.16, 0.2, 0.24, 1
        return over(o, MIST[(f + r) % 4])
    return over(MUD, UW[LIP_DEPTH[c] - 1])

def lip_even(c):  # one even sheet over the stepped depths: DF's full-depth water laid on the shallower columns
    e = UW[6].copy(); e[..., 3] *= [0.0, 0.75, 1.0][c]; return e

def lip_ref(f, wx, wy):  # what DF draws now
    return np.zeros((32, 32, 4))

def lip_glassy(f, wx, wy):  # an even glassy tongue: steps hidden, soft highlight bands sliding to the edge, faster near it
    sp = LIP_SPEED[wx]; gx = xx + wx * 32
    ph = (gx - f * 8 * sp * 2) / 14 * 2 * math.pi
    band = ss(0.75, 1.0, np.sin(ph + 0.6 * np.sin((yy + wy * 32) / 9))) * (0.18 + 0.2 * sp)
    return over(lip_even(wx), rgba(band, 215, 240, 250))

def lip_streaks(f, wx, wy):  # fast white dashes racing to the edge, longer and brighter near it
    sp = LIP_SPEED[wx]; a = np.zeros((32, 32))
    for k in range(7):
        r = int(h(k * 7919 + (wy * 4 + wx) * 131))
        y0 = (r % 30) + 1; ln = 4 + 8 * sp; x0 = ((r >> 8) % 32 + f * 8 * (1 + sp)) % 40 - 6
        m = (np.abs(yy - y0) < 0.6) & (xx >= x0) & (xx <= x0 + ln)
        a = np.maximum(a, m * (0.35 + 0.45 * sp) * np.clip((xx - x0) / ln, 0.2, 1))
    return over(lip_even(wx), rgba(a, 235, 248, 252))

def lip_chevron(f, wx, wy):  # standing V waves pointing downstream, shimmering in place
    sp = LIP_SPEED[wx]; gy = yy + wy * 32 - 48
    u = xx + wx * 32 - np.abs(gy) * 0.55
    p = np.sin(u / 7 * 2 * math.pi - f * math.pi / 2)
    a = ss(0.8, 1.0, p) * (0.2 + 0.35 * sp)
    return over(lip_even(wx), rgba(a, 220, 242, 250))

_flow = np.asarray(Image.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'online', 'flow-down.png')).convert('RGBA')).astype(float) / 255
def lip_oga(f, wx, wy):  # madmedicsoft 'simple water flow' (CC0), turned to run east, doubled to 32 px, every other frame
    fr = _flow[:, (2 * f) * 16:(2 * f + 1) * 16]
    fr = np.rot90(fr, 1)  # down -> east
    fr = fr.repeat(2, 0).repeat(2, 1)
    # keep only the strokes: the tile's light-blue body is dropped, its
    # brighter-than-median pixels become white strokes on the even sheet
    lum = 0.299 * fr[..., 0] + 0.587 * fr[..., 1] + 0.114 * fr[..., 2]
    a = ss(np.median(lum), np.median(lum) + 0.12, lum) * (0.35 + 0.45 * LIP_SPEED[wx])
    return over(lip_even(wx), rgba(a, 225, 245, 252))

# ---------------- falls: the froth (landing tile at column 1, row 1) ----------------
LAND = (1, 1)
def froth_k(wx, wy):  # strength by distance from the landing tile: 1, 0.55, 0.25
    d = max(abs(wx - LAND[0]), abs(wy - LAND[1])); return [1.0, 0.55, 0.25, 0.1][min(d, 3)]

def froth_bg(f, c, r):
    b = over(MUD, UW[6])
    if (c, r) == LAND:  # the falling column, as DF's mod mist page draws it
        o = np.zeros((32, 32, 4)); stripes = 0.5 + 0.5 * np.sin((xx * 1.7 + yy * 0.2 + f * 8) / 32 * 2 * math.pi * 3)
        o[..., 0], o[..., 1], o[..., 2] = 0.55 + 0.3 * stripes, 0.85, 0.92; o[..., 3] = 0.55 + 0.25 * stripes
        b = over(b, o)
    return b

def froth_ref(f, wx, wy):
    return np.zeros((32, 32, 4))

def froth_boil(f, wx, wy):  # churning white foam, dense at the landing, broken patches further out
    k = froth_k(wx, wy); gx, gy = xx + wx * 32, yy + wy * 32
    n = 0.6 * vnoise(gx + f * 3, gy - f * 2, 6, 17, 512) + 0.4 * vnoise(gx - f * 4, gy + f * 3, 3, 29, 512)
    a = ss(1.0 - 0.55 * k, 1.05 - 0.55 * k, n) * (0.55 + 0.4 * k)
    return rgba(a, 240, 248, 250)

def froth_bubbles(f, wx, wy):  # bubble rings welling up and popping, many at the landing, few at the edge
    k = froth_k(wx, wy); a = np.zeros((32, 32))
    for i in range(int(4 + 14 * k)):
        r = int(h(wx * 131 + wy * 977 + i * 7919))
        bx, by = (r % 28) + 2 - 15.5, ((r >> 8) % 28) + 2 - 15.5
        life = ((r >> 16) + f) % 4; rad = [1.0, 1.7, 2.3, 0][life]
        if rad == 0: continue
        d = np.sqrt((cx - bx) ** 2 + (cy - by) ** 2)
        a = np.maximum(a, np.clip(1 - np.abs(d - rad) / 0.7, 0, 1) * (0.85 if life < 2 else 0.5))
    return rgba(a * (0.5 + 0.5 * k))

def froth_rings(f, wx, wy):  # rings spreading out from the landing point and fading
    gx = xx + wx * 32 - (LAND[0] * 32 + 16); gy = yy + wy * 32 - (LAND[1] * 32 + 16)
    d = np.sqrt(gx * gx + gy * gy)
    a = np.zeros((32, 32))
    for j in range(3):
        rad = (f * 6 + j * 24) % 72 + 8
        a = np.maximum(a, np.clip(1 - np.abs(d - rad) / 1.6, 0, 1) * np.clip(1 - rad / 72, 0, 1) * 0.7)
    a = np.maximum(a, np.clip(1 - d / 14, 0, 1) * 0.6)  # the churned centre
    return rgba(a, 235, 246, 250)

def froth_spray(f, wx, wy):  # foam on the water and DF's mist over it, both fading with distance
    k = froth_k(wx, wy); gx, gy = xx + wx * 32, yy + wy * 32
    n = vnoise(gx + f * 2, gy + f * 2, 4, 47, 512)
    foam = rgba(ss(0.95 - 0.45 * k, 1.0 - 0.45 * k, n) * 0.75 * k ** 1.5, 240, 248, 250)
    m = MIST[(f + wx + wy) % 4].copy(); m[..., 3] *= 0.7 * k * k
    return over(foam, m)

SCENES['lip'] = (lip_bg, [(c, r) for r in range(3) for c in range(3)])
SCENES['froth'] = (froth_bg, [(c, r) for r in range(3) for c in range(4)])
VARIANTS += [
    ('lip-df', 'lip', 'lip', lip_ref, 'DF now (reference)', 'What DF draws today: depth 7, 5 and 3 toward the drop, so the water steps from dark to light.'),
    ('lip-glassy', 'lip', 'lip', lip_glassy, 'Glassy tongue', 'The steps evened out into one sheet; soft highlight bands slide to the edge, quicker near it.'),
    ('lip-streaks', 'lip', 'lip', lip_streaks, 'Racing streaks', 'Even sheet with thin white dashes racing to the edge, longer and brighter as it nears.'),
    ('lip-chevron', 'lip', 'lip', lip_chevron, 'Standing V waves', 'Even sheet with V-shaped standing waves pointing downstream, shimmering in place.'),
    ('lip-oga', 'lip', 'lip', lip_oga, 'Flow strokes (OGA, CC0)', 'madmedicsoft\'s simple water flow, turned to run toward the edge, over an even sheet.'),
    ('froth-df', 'froth', 'froth', froth_ref, 'DF now (reference)', 'Today: the falling column lands and the pool round it is plain water.'),
    ('froth-boil', 'froth', 'froth', froth_boil, 'Churning foam', 'White foam boiling at the landing, breaking into patches further out.'),
    ('froth-bubbles', 'froth', 'froth', froth_bubbles, 'Bubble boil', 'Bubble rings welling up and popping; many at the landing, few two tiles out.'),
    ('froth-rings', 'froth', 'froth', froth_rings, 'Spreading rings', 'A churned centre with rings running out from it and fading.'),
    ('froth-spray', 'froth', 'froth', froth_spray, 'Foam and mist', 'Patchy foam on the water with DF\'s own mist over it, both thinning with distance.'),
]

meta = []
for vid, grp, scene, fn, title, note in VARIANTS:
    layout, cells = SCENES[scene]
    frames, tiles = [], []
    for f in range(F):
        sc = np.zeros((96, 128, 4))
        for r in range(3):
            for c in range(4):
                if callable(layout):
                    sc[r * 32:(r + 1) * 32, c * 32:(c + 1) * 32] = layout(f, c, r)
                else:
                    sc[r * 32:(r + 1) * 32, c * 32:(c + 1) * 32] = SAND if layout[r][c] == 'S' else over(SAND, WATER)
        for (c, r) in cells:
            spr = fn(f, c, r)
            sc[r * 32:(r + 1) * 32, c * 32:(c + 1) * 32] = over(sc[r * 32:(r + 1) * 32, c * 32:(c + 1) * 32], spr)
        frames.append(sc); tiles.append(fn(f, 1, 1))
    strip = np.concatenate(frames, axis=1)
    Image.fromarray((np.clip(strip, 0, 1) * 255).astype(np.uint8)).save(os.path.join(OUT, vid + '.png'), optimize=True)
    Image.fromarray((np.clip(np.concatenate(tiles, axis=1), 0, 1) * 255).astype(np.uint8)).save(os.path.join(OUT, vid + '-tile.png'), optimize=True)
    meta.append({'id': vid, 'group': grp, 'title': title, 'note': note})
json.dump(meta, open(os.path.join(OUT, 'meta.json'), 'w'), indent=1)
print(len(meta), 'variants ->', OUT)
