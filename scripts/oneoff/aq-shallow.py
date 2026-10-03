#!/usr/bin/env python3
"""Aquarium diagnosis (2 Oct): does the bed show through SHALLOW water (a water tile that has its own floor), and is
the dark seen through deep water DF's lower-level fog? Reuses aquarium-run.py's rig helpers. For each preset: write it
(in game), reload AQUA_LAKE, find water tiles whose own cell has a floor (depth 1 column) and deep ones (open below),
centre on a shallow one beside dry land, capture. Prints per-tile pixel means; shots in data/aquarium-run/<run>-shallow/.
Usage: python3 scripts/oneoff/aq-shallow.py [preset ...]   (default: vanilla clear)
"""
import importlib.util, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("aqr", ROOT / "scripts/aquarium-run.py")
A = importlib.util.module_from_spec(spec); spec.loader.exec_module(A)

class Args: tool_src = str(Path.home() / "Claude/Projects/sw-wt/rc"); view = None; dry_run = False
A.ARGS = Args(); A.MODE = "live"; A.STAGE = "shallow"
A.OUT = A.OUT.with_name(A.RUN + "-shallow"); A.SHOTS = A.OUT / "shots"; A.SHOTS.mkdir(parents=True, exist_ok=True)
A.LOG = open(A.OUT / "log.txt", "w")

FIND = """
local M = df.global.world.map
local W, H, Z = M.x_count, M.y_count, M.z_count
local function water(x, y, z)
  local d = dfhack.maps.getTileFlags(x, y, z); if not d then return 0 end
  if d.liquid_type then return 0 end   -- magma
  return d.flow_size
end
local function shape(x, y, z)
  local tt = dfhack.maps.getTileType(x, y, z); if not tt then return nil end
  return df.tiletype_shape[df.tiletype.attrs[tt].shape]
end
local shallow, deep = {}, {}
for z = 56, 50, -1 do
  for x = 40, 300, 3 do for y = 140, 340, 3 do
    local f = water(x, y, z)
    if f >= 4 and water(x, y, z + 1) == 0 and dfhack.maps.getTileFlags(x, y, z).outside then
      local sh = shape(x, y, z)
      local dry = 0
      for _, o in ipairs({ {2,0}, {-2,0}, {0,2}, {0,-2}, {1,1}, {-1,-1} }) do
        if water(x + o[1], y + o[2], z) == 0 and shape(x + o[1], y + o[2], z) == 'FLOOR' then dry = dry + 1 end
      end
      if sh == 'FLOOR' and #shallow < 40 then shallow[#shallow + 1] = { x, y, z, f, dry } end
      if sh == 'EMPTY' and #deep < 10 then deep[#deep + 1] = { x, y, z, f } end
    end
  end end
  if #shallow >= 40 then break end
end
return { shallow = shallow, deep = deep, lower = df.global.d_init.display.number_of_lower_elevations_shown }
"""

def main():
    presets = sys.argv[1:] or ["vanilla", "clear"]
    res = {}
    for p in presets:
        A.load_fort("AQUA_LAKE", f"(shallow probe, preset {p})")
        ok, out = A.set_preset(p)
        A.log(f"preset {p}: ok {ok}")
        A.load_fort("AQUA_LAKE", f"(reload so DF reads the {p} pages)")
        F, raw = A.lua("find-shallow", FIND, timeout=240)
        if not F:
            A.log(f"finder failed: {raw[-400:]}"); print(raw[-400:]); return 1
        A.log(f"shallow {len(F['shallow'])} deep {len(F['deep'])} lower {F['lower']}: first {F['shallow'][:3]}")
        if not F["shallow"]:
            print("no shallow water tile with its own floor found"); return 1
        sx, sy, sz = F["shallow"][0][:3]
        G = A.centre(sx, sy, sz)
        png = A.shot(f"{p}-shallow", G)
        tiles = {"shallow": [t[:3] for t in F["shallow"][:12] if t[2] == sz], "deep": [t[:3] for t in F["deep"] if t[2] == sz]}
        from PIL import Image
        img = Image.open(png).convert("RGB")
        stat = {k: A.stats(img, G, [tuple(c[:2]) for c in v]) if v else None for k, v in tiles.items()}
        res[p] = {"centre": [sx, sy, sz], "tiles": tiles, "stats": stat, "shot": str(png)}
        A.log(f"{p}: {json.dumps(stat)[:600]}")
    (A.OUT / "result.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str)[:3000]); print("OUT", A.OUT)

if __name__ == "__main__":
    sys.exit(main())
