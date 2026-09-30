#!/usr/bin/env python3
"""Creature tiles for the companion's SAMPLE page, read from the local DF install (needs Pillow).

Usage: build_sprites.py <tokens.json> <out.json>
  tokens.json   a JSON list of creature tokens (build_mock.py --tokens writes it)
  out.json      {pages, font, palette, tiles: {TOKEN: {gfx, ascii}}} -- the same shape seasonal-wildlife-web
                serves live, except that the sample's sprite sheets are two small atlases cropped from DF's own
                sheets (an icon atlas and a default-image atlas), embedded as data URIs

Steam graphics: data/vanilla/*_graphics/graphics -- TILE_PAGE (file, tile size) and CREATURE_GRAPHICS blocks,
read for [DEFAULT:PAGE:x:y:...] or [DEFAULT:PAGE:LARGE_IMAGE:x1:y1:x2:y2:...] and [LIST_ICON:PAGE:x:y].
ASCII: [CREATURE_TILE:'c' | n] and [COLOR:fg:bg:bright] from data/vanilla/*/objects/creature_*.txt, drawn with
the install's own font (data/art/<FONT from prefs/init.txt>) and palette (data/init/colors.txt).

These are the user's own game assets: the output stays out of the repository (it is written wherever out.json
points, normally the session scratchpad) and the sample page that embeds it is for the user's own use.
"""
import base64, io, json, re, sys
from pathlib import Path
from PIL import Image

DF = Path.home() / "Library/Application Support/CrossOver/Bottles/Win10/drive_c/Program Files (x86)/Steam/steamapps/common/Dwarf Fortress"
VAN = DF / "data/vanilla"
COLORS = ["BLACK", "BLUE", "GREEN", "CYAN", "RED", "MAGENTA", "BROWN", "LGRAY", "DGRAY", "LBLUE", "LGREEN", "LCYAN", "LRED", "LMAGENTA", "YELLOW", "WHITE"]
TAG = re.compile(r"\[([^\]]+)\]")

def tile_pages():
    pages = {}
    for f in VAN.glob("*_graphics/graphics/tile_page_*.txt"):
        cur = None
        for t in TAG.findall(f.read_text(errors="replace")):
            p = t.split(":")
            if p[0] == "TILE_PAGE": cur = pages.setdefault(p[1], {"dir": f.parent})
            elif cur is not None and p[0] == "FILE": cur["file"] = p[1]
            elif cur is not None and p[0] == "TILE_DIM": cur["tw"], cur["th"] = int(p[1]), int(p[2])
    return pages

def creature_graphics():
    """TOKEN -> {'default': (page, x1, y1, x2, y2), 'icon': (page, x, y)} from the plain CREATURE_GRAPHICS blocks.
    The image is the first of: DEFAULT, VERMIN (vermin), the DEFAULT layer set's BODY layer (layered creatures), and
    ANIMATED (animal people, whose DEFAULT is a layer-set template)."""
    RANK = {"DEFAULT": 0, "VERMIN": 1, "BODY": 2, "ANIMATED": 3}
    def rect(p, i):   # p[i] is the page; LARGE_IMAGE:x1:y1:x2:y2 or x:y
        if len(p) > i + 5 and p[i + 1] == "LARGE_IMAGE": return (p[i], int(p[i + 2]), int(p[i + 3]), int(p[i + 4]), int(p[i + 5]))
        if len(p) > i + 2 and p[i + 1].isdigit() and p[i + 2].isdigit(): return (p[i], int(p[i + 1]), int(p[i + 2]), int(p[i + 1]), int(p[i + 2]))
        return None
    out = {}
    for f in VAN.glob("*_graphics/graphics/graphics_creatures*.txt"):
        if "statue" in f.name or "portrait" in f.name:
            continue
        cur, layerset = None, None
        for t in TAG.findall(f.read_text(errors="replace")):
            p = t.split(":")
            if p[0] in ("CREATURE_GRAPHICS", "CREATURE_CASTE_GRAPHICS"): cur, layerset = out.setdefault(p[1], {}), None; continue   # a caste block (lions) gives its first caste's image
            if p[0].endswith("CREATURE_GRAPHICS"): cur = None; continue
            if cur is None: continue
            if p[0] == "LAYER_SET": layerset = p[1]; continue
            kind = p[0] if p[0] in ("DEFAULT", "VERMIN", "ANIMATED") and layerset is None else ("BODY" if p[0] == "LAYER" and len(p) > 2 and p[1] == "BODY" and layerset == "DEFAULT" else None)
            if kind:
                r = rect(p, 2 if kind == "BODY" else 1)
                if r and RANK[kind] < cur.get("rank", 9): cur["default"], cur["rank"] = r, RANK[kind]
            elif p[0] == "LIST_ICON" and len(p) >= 4 and p[2].isdigit(): cur["icon"] = (p[1], int(p[2]), int(p[3]))
    return out

def creature_ascii():
    """TOKEN -> (tile code, fg, bg, bright), following COPY_TAGS_FROM for creatures that name no tile of their own."""
    raw, copy = {}, {}
    for f in VAN.glob("*/objects/creature_*.txt"):
        cur = None
        for t in TAG.findall(f.read_text(errors="replace")):
            p = t.split(":")
            if p[0] == "CREATURE": cur = raw.setdefault(p[1], {})
            elif cur is None: continue
            elif p[0] == "CREATURE_TILE" and "tile" not in cur:
                v = t.split(":", 1)[1]
                cur["tile"] = ord(v[1]) if v.startswith("'") and len(v) >= 3 else int(v) if v.isdigit() else None
            elif p[0] == "COLOR" and "color" not in cur and len(p) == 4: cur["color"] = tuple(int(x) for x in p[1:])
            elif p[0] == "COPY_TAGS_FROM": copy[id(cur)] = p[1]
            elif p[0] == "APPLY_CREATURE_VARIATION" and p[1].startswith("ANIMAL_PERSON"): cur.setdefault("person", True)
    out = {}
    for tok, r in raw.items():
        src = r
        for _ in range(3):   # a giant or a person without a tile of its own takes its source's
            if "tile" in src and "color" in src: break
            base = copy.get(id(src))
            if not base or base not in raw: break
            src = {**raw[base], **{k: v for k, v in src.items() if k in ("tile", "color")}}
        tile = src.get("tile") or ord(tok[0])
        fg, bg, br = src.get("color", (7, 0, 0))
        out[tok] = (tile, fg, bg, br)
    return out

def png_uri(im):
    b = io.BytesIO(); im.save(b, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()

def main(tok_path, out_path):
    tokens = json.load(open(tok_path))
    pages, gfx, asc = tile_pages(), creature_graphics(), creature_ascii()
    sheets = {}
    def sheet(name):
        if name not in sheets:
            pg = pages.get(name)
            sheets[name] = Image.open(pg["dir"] / pg["file"]).convert("RGBA") if pg and "file" in pg else None
        return sheets[name]
    # atlases: icons 32x32 in a 16-wide grid; default images in 3x2-tile cells (the largest LARGE_IMAGE here)
    have = [t for t in tokens if t in gfx and "default" in gfx[t] and sheet(gfx[t]["default"][0]) is not None]
    COLS, CW, CH = 16, 3, 2
    icons = Image.new("RGBA", (COLS * 32, ((len(have) + COLS - 1) // COLS) * 32 or 32), (0, 0, 0, 0))
    imgs = Image.new("RGBA", (COLS * CW * 32, ((len(have) + COLS - 1) // COLS) * CH * 32 or 64), (0, 0, 0, 0))
    tiles = {}
    for i, t in enumerate(have):
        g = gfx[t]; page, x1, y1, x2, y2 = g["default"]
        pg = pages[page]; tw, th = pg.get("tw", 32), pg.get("th", 32)
        w, h = min(CW, x2 - x1 + 1), min(CH, y2 - y1 + 1)
        crop = sheet(page).crop((x1 * tw, y1 * th, (x1 + w) * tw, (y1 + h) * th))
        if (tw, th) != (32, 32): crop = crop.resize((w * 32, h * 32), Image.Resampling.NEAREST)
        cx, cy = (i % COLS) * CW, (i // COLS) * CH
        imgs.paste(crop, (cx * 32, cy * 32))
        ic = g.get("icon")
        if ic and sheet(ic[0]) is not None:
            ipg = pages[ic[0]]; itw, ith = ipg.get("tw", 32), ipg.get("th", 32)
            icrop = sheet(ic[0]).crop((ic[1] * itw, ic[2] * ith, (ic[1] + 1) * itw, (ic[2] + 1) * ith)).resize((32, 32), Image.Resampling.NEAREST)
        else:
            icrop = crop.crop((0, 0, 32, 32)) if (w, h) == (1, 1) else crop.resize((32, 32 * h // w) if w >= h else (32 * w // h, 32), Image.Resampling.NEAREST)
            pad = Image.new("RGBA", (32, 32), (0, 0, 0, 0)); pad.paste(icrop, ((32 - icrop.width) // 2, (32 - icrop.height) // 2)); icrop = pad
        icons.paste(icrop, ((i % COLS) * 32, (i // COLS) * 32))
        tiles[t] = {"gfx": {"p": "img", "x": cx, "y": cy, "w": w, "h": h, "ip": "icon", "ix": i % COLS, "iy": i // COLS}}
    for t in tokens:
        a = asc.get(t)
        if a: tiles.setdefault(t, {})["ascii"] = {"ch": a[0], "fg": a[1], "bg": a[2], "br": a[3]}
    # the font and palette the install uses
    init = (DF / "prefs/init.txt").read_text(errors="replace") if (DF / "prefs/init.txt").exists() else ""
    m = re.search(r"\[FONT:([^\]]+)\]", init)
    font = Image.open(DF / "data/art" / (m.group(1) if m else "curses_640x300.png")).convert("RGBA")
    ctext = (DF / "data/init/colors.txt").read_text(errors="replace")
    pal = []
    for c in COLORS:
        rgb = [int(re.search(rf"\[{c}_{k}:(\d+)\]", ctext).group(1)) for k in "RGB"]
        pal.append("#%02x%02x%02x" % tuple(rgb))
    out = {"pages": {"img": {"url": png_uri(imgs), "w": imgs.width, "h": imgs.height, "tw": 32, "th": 32},
                     "icon": {"url": png_uri(icons), "w": icons.width, "h": icons.height, "tw": 32, "th": 32}},
           "font": {"url": png_uri(font), "gw": font.width // 16, "gh": font.height // 16}, "palette": pal, "tiles": tiles}
    json.dump(out, open(out_path, "w"))
    miss_g = [t for t in tokens if t not in have]; miss_a = [t for t in tokens if t not in asc]
    print(f"{len(tokens)} tokens: {len(have)} with Steam sprites, {len(tokens) - len(miss_a)} with ASCII tiles; "
          f"atlases {imgs.size} + {icons.size}; {len(json.dumps(out)) // 1024} KB")
    print("no sprite:", " ".join(miss_g[:40]) + (" ..." if len(miss_g) > 40 else ""))
    print("no ascii:", " ".join(miss_a[:20]))

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
