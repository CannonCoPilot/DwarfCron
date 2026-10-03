#!/usr/bin/env python3
"""aquarium-run.py -- the Seasonal Wildlife Aquarium rig test driver (sw-wt/rc docs/v7.1/aquarium.md section 9, T1-T11).

The user's goal: the water and mist animations and the water transparency fundamentally working. Failed tests are never
skipped: they get fixed. So every test writes its receipts (each cx-lifecycle call and its exact reply, in order), its
screenshots (bursts of frames for anything that moves, with an animated GIF and a contact sheet) and, where pixels can
decide it, an automated pixel check with its numbers and an annotated copy of the frame showing the cells it measured.

    scripts/aquarium-run.py                          SETUP + T1..T11 (AQUA_SHORE must exist for T3/T4/T5/T8)
    scripts/aquarium-run.py --embark-shore           also embark AQUA_SHORE on region10 first (stage `shore`)
    scripts/aquarium-run.py --only setup,t1,mist     a selection (stages below; `mist` = T1's arms, mist captures only)
    scripts/aquarium-run.py --skip t8,t10
    scripts/aquarium-run.py --view lake|river|brook|mist|surf|ocean|fish [--fort AQUA_LAKE] [--frames 8]
                                                     the fix loop: centre the view on the target (on the map that is
                                                     loaded, or after loading --fort) and capture a burst + GIF
    scripts/aquarium-run.py --dry-run                no rig: fake replies + synthetic frames prove the plumbing;
                                                     SETUP's file checks still read the real disk (read only)
Options: --tool-src DIR (the rc worktree, default ~/Claude/Projects/sw-wt/rc), --deploy (cx-lifecycle deploy-tool
<tool-src>/scripts + tests/rig/sw-aquarium-watch.lua; default: check only), --presets vanilla,aquarium,clear (T1 arms),
--t2-presets aquarium,clear, --t3-presets vanilla,aquarium,shallows, --frames N --gap S (bursts; default 6 x 0.25 s),
--fish TOKEN (T2: placed if no creature is already below the surface), --no-spawn (mist: never spawn a test flow),
--restart-escalate (T1: if the aquarium arm shows no change after a title reload, restart DF and capture again),
--perf-reps N (T8, default 5), --perf-secs S (default 10).

Stages (in order): setup, shore, t1, t2, t3, t4, t5, t6, t7, t8, t9, t10, t11. Forts: AQUA_LAKE (region10, the mod),
AQUA_SHORE (region10, ocean), RinghatchetsReady (no mod). Every fort is restored from <fort>.preverify and loaded fresh
whenever a stage needs it; the run never saves a fort it tests (only the shore stage saves AQUA_SHORE, once, then backs
it up as AQUA_SHORE.preverify). One RPC at a time; fps is never touched.

What each check decides (thresholds are first-run guesses, recorded in every row so the lead can re-judge them):
  setup.*       deploy byte-identity; `aquarium status` graphics mode and lower elevations; the mod folder AND the
                installed copy DF actually loads (data/installed_mods/seasonal_wildlife_aquarium (1)): 10 files, PNG
                sizes = the raws' PAGE_DIM_PIXELS, page alphas = the stamp's preset, raws = the rc tree's committed raws
  t1.*          per preset arm (install, title, restore, load): status names the preset the world loaded; lake and
                river water cells differ from the vanilla arm by >= TRANS_MIN while dry control cells differ by <=
                CONTROL_MAX (same view, same tick); edge energy and luminance per arm; river streak frames change
  mist.*        a Mist/Steam flow found (or spawned: dfhack.maps.spawnFlow, Mist and Steam side by side) and drawn
                (after-before diff in its cells), animating (frame diffs > control), restyled (aquarium v vanilla colour),
                and the overlay's foam on mist cells
  t2.*          fish below the surface: lens on v off differs in the fish cells (lens draws), probe lists them; the open
                question "does DF draw them through translucent water" scored as the fish cells' contrast to their
                water neighbours with the lens off (INFO, per preset)
  t3.*          ocean surface per preset: dark fraction (fog or black), change v vanilla
  t4.*          sw-aquarium-watch over 6,000 ticks: wave makers, fronts, OceanWave/SeaFoam flows
  t5.*          surf/front burst with waves on v off: frame change in the surf cells (overlay animates) > control
  t6-t11        lens + legend + probe on RinghatchetsReady; veil on v off; perf arms (stopwatch); fuse trip + rearm;
                verbs and web registry round trip, restore/install actions; the uninstall guard
Output: data/aquarium-run/<stamp>/ results.json, report.md, log.txt, receipts/<stage>.txt, shots/ (PNG frames, *-boxes.png
annotated, *.gif, *-sheet.png). Exit 0 when no row FAILs, 1 when one does, 2 when the run could not start.
"""
import argparse, http.client, json, math, os, re, shutil, subprocess, sys, time
from datetime import datetime
from pathlib import Path

try:
    from PIL import Image, ImageDraw
    import numpy as np
except ImportError:   # pragma: no cover
    sys.exit("aquarium-run needs Pillow and numpy (python3 -m pip install pillow numpy)")

ROOT = Path(__file__).resolve().parent.parent
CX = str(ROOT / "scripts" / "cx-lifecycle.sh")
RUN = datetime.now().strftime("%Y%m%d-%H%M%S")
LUAC = Path.home() / "Claude/Projects/sw-wt/.tools/luac53"
STAGES = ["setup", "shore", "t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8", "t9", "t10", "t11"]
FORT = {"lake": "AQUA_LAKE", "ocean": "AQUA_SHORE", "plain": "RinghatchetsReady"}
MOD_ID = "seasonal_wildlife_aquarium"
SHORE = {"world": "region10", "rx": 205, "ry": 170, "ox": 5, "oy": 13, "size": 6}
TRANS_MIN, CONTROL_MAX, ANIM_MIN, MIST_MIN, LENS_MIN = 6.0, 3.0, 1.5, 4.0, 6.0
WPORT = 8643


def cx_paths():
    """DF_DIR / DF_USER_DIR / backups as cx-config.sh says (read, never written)."""
    p = subprocess.run(["bash", "-c", f'source "{ROOT}/scripts/cx-config.sh"; echo "$DF_DIR"; echo "$DF_USER_DIR"; echo "$CX_SNAPSHOT_DIR"'],
                       capture_output=True, text=True)
    a = (p.stdout.strip().split("\n") + ["", "", ""])[:3]
    return Path(a[0]), Path(a[1]), Path(a[2] or str(Path.home() / "Library/Application Support/CrossOver/df-snapshots")) / "saves"


REAL_DF, REAL_USER, BACKUPS = cx_paths()
DF_DIR, USER_DIR = REAL_DF, REAL_USER
MODE = "live"
OUT = ROOT / "data" / "aquarium-run" / RUN
SHOTS = OUT / "shots"
LOG = None
RESULTS = []
STAGE = "setup"
ARGS = None
FAKE = None


# ------------------------------------------------------------------------------------------------ logging, rows, receipts
def log(m):
    line = f"{datetime.now().strftime('%H:%M:%S')} {m}"
    print(line, flush=True)
    if LOG:
        LOG.write(line + "\n"); LOG.flush()


def receipt(text):
    d = OUT / "receipts"; d.mkdir(parents=True, exist_ok=True)
    with open(d / f"{STAGE}.txt", "a") as f:
        f.write(text.rstrip("\n") + "\n")


def rec(rid, verdict, ev, data=None, shots=None):
    row = {"id": rid, "stage": STAGE, "verdict": verdict, "evidence": str(ev), "receipts": f"receipts/{STAGE}.txt"}
    if data is not None: row["data"] = data
    if shots: row["shots"] = [str(Path(s).relative_to(OUT)) if str(s).startswith(str(OUT)) else str(s) for s in shots if s]
    RESULTS.append(row)
    log(f"  [{verdict}] {rid}: {str(ev)[:260]}")
    return verdict == "PASS"


def cx(*a, timeout=180):
    """One cx-lifecycle call (one RPC at a time); every call and its full reply goes into the stage's receipts."""
    args = [str(x) for x in a]
    t0 = time.time()
    if MODE == "live":
        try:
            p = subprocess.run([CX, *args], capture_output=True, text=True, timeout=timeout, cwd=ROOT,
                               env=dict(os.environ, CX_RPC_TIMEOUT="45"))
            rc, out, err = p.returncode, (p.stdout or "").replace("\r", ""), (p.stderr or "").replace("\r", "")
        except subprocess.TimeoutExpired:
            rc, out, err = 124, "", f"timed out after {timeout}s"
    else:
        rc, out, err = FAKE.reply(args)
    shown = " ".join(x if re.fullmatch(r"[\w.,:/=@+-]+", x) else repr(x[:400] + ("..." if len(x) > 400 else "")) for x in args)
    receipt(f"$ cx-lifecycle.sh {shown}\n{out}{('[stderr] ' + err) if err.strip() else ''}[rc={rc} {time.time() - t0:.1f}s]\n")
    return rc, out, err


def sw(*words, timeout=120):
    return cx("cmd", "seasonal-wildlife", *words, timeout=timeout)


def aq(*words, timeout=120):
    rc, out, err = sw("aquarium", *words, timeout=timeout)
    return out + err


def lua(tag, code, timeout=90):
    """Run a Lua snippet that prints one 'AQJ <json>' line (or 'AQERR <msg>'); returns (obj or None, raw text).
    Every snippet is pcall-wrapped: a Lua error must never read as an empty answer (readout trap 24)."""
    wrapped = (f"-- AQ:{tag}\nlocal json = require('json')\nlocal ok, r = pcall(function()\n{code}\nend)\n"
               "if ok then print('AQJ ' .. json.encode(r, { pretty = false })) else print('AQERR ' .. tostring(r)) end")
    rc, out, err = cx("lua", wrapped, timeout=timeout)
    m = re.search(r"^AQJ (.*)", out, re.M | re.S)   # json.encode is pretty by default: take everything after the marker
    if m:
        try:
            return json.loads(m.group(1).strip()), out
        except ValueError:
            pass
    return None, (out + err).strip() or f"rc={rc}, no reply"


def state():
    rc, out, err = cx("state", timeout=60)
    return dict(re.findall(r"(\w+)=(\S+)", out))


def wait_state(key, want, secs):
    t = time.time() + secs
    while time.time() < t:
        if state().get(key) == want: return True
        time.sleep(2 if MODE == "live" else 0)
    return False


def nap(s):
    if MODE == "live": time.sleep(s)


# ------------------------------------------------------------------------------------------------ the fort
CUR = {"fort": None}


def load_fort(fort, why=""):
    """title (unsaved) -> save-restore <fort>.preverify -> load -> popups -> pause. Returns True on a loaded map."""
    log(f"== load {fort} from {fort}.preverify {why}")
    if not (BACKUPS / f"{fort}.preverify").is_dir() and MODE == "live":
        rec(f"{STAGE}.fort.{fort}", "FAIL", f"no backup {BACKUPS / (fort + '.preverify')}: back the fort up before testing on it")
        return False
    st = state()
    if st.get("map") == "true":
        cx("title", timeout=240)
    cx("save-restore", f"{fort}.preverify", timeout=400)
    rc, out, err = cx("load", fort, timeout=420)
    st = state()
    if st.get("map") != "true":
        rec(f"{STAGE}.fort.{fort}", "FAIL", f"{fort} did not load: {(out + err).strip()[-300:]} | state {st}")
        CUR["fort"] = None
        return False
    cx("popups"); cx("pause")
    CUR["fort"] = fort
    return True


def ensure_fort(fort, fresh=False, why=""):
    if CUR["fort"] == fort and not fresh and state().get("map") == "true":
        return True
    return load_fort(fort, why)


# ------------------------------------------------------------------------------------------------ the mod on disk
def mod_dir():
    return USER_DIR / "mods" / MOD_ID


def installed_copies(user=None):
    root = (user or USER_DIR) / "data" / "installed_mods"
    out = []
    if root.is_dir():
        for d in sorted(root.iterdir()):
            if d.name.startswith(MOD_ID + " (") and (d / "info.txt").is_file() and f"[ID:{MOD_ID}]" in (d / "info.txt").read_text("latin-1"):
                out.append(d)
    return out


def stamp(d):
    p = Path(d) / "sw_aquarium_stamp.txt"
    if not p.is_file(): return {}
    return dict(l.split("=", 1) for l in p.read_text().splitlines() if "=" in l)


GFX_FILES = ["info.txt", "sw_aquarium_stamp.txt", "graphics/tile_page_sw_aquarium.txt", "graphics/graphics_sw_aquarium.txt",
             "graphics/images/sw_aq_liquids.png", "graphics/images/sw_aq_mist.png"] + [f"graphics/images/sw_aq_flows{v}.png" for v in range(1, 5)]


def check_mod_folder(d, tool, label):
    """The aq.pages claim on one folder: files, PNG size = raws, alpha = stamp, raws = the rc tree's committed raws."""
    d = Path(d)
    probs, facts = [], {}
    miss = [f for f in GFX_FILES if not (d / f).is_file()]
    if miss: probs.append(f"missing {miss}")
    st = stamp(d); facts["stamp"] = st
    committed = Path(tool) / "mods" / MOD_ID
    for f in ["info.txt", "graphics/tile_page_sw_aquarium.txt", "graphics/graphics_sw_aquarium.txt"]:
        if (d / f).is_file() and (committed / f).is_file() and (d / f).read_bytes() != (committed / f).read_bytes():
            probs.append(f"{f} differs from the rc tree's committed raws (stale install)")
            if f == "info.txt":
                nm = re.search(r"\[NAME:([^\]]*)\]", (d / f).read_text("latin-1"))
                if nm and ":" in nm.group(1): probs.append(f"NAME has a colon ('{nm.group(1)}': DF reads only up to it)")
    tp = d / "graphics/tile_page_sw_aquarium.txt"
    if tp.is_file():
        for pid, fn, w, h in re.findall(r"\[TILE_PAGE:(\w+)\]\s*\[FILE:images/([^\]]+)\]\s*\[TILE_DIM:32:32\]\s*\[PAGE_DIM_PIXELS:(\d+):(\d+)\]", tp.read_text()):
            p = d / "graphics/images" / fn
            if p.is_file():
                sz = Image.open(p).size
                if sz != (int(w), int(h)): probs.append(f"{fn} is {sz}, raws say {w}x{h}")
    liq = d / "graphics/images/sw_aq_liquids.png"
    if liq.is_file() and st.get("alpha"):
        a = np.array(Image.open(liq).convert("RGBA"))[:, :, 3]
        want = [int(x) for x in st["alpha"].split(",")]
        got = [int(np.median(a[r * 32:(r + 1) * 32, 0:32][a[r * 32:(r + 1) * 32, 0:32] > 0])) if (a[r * 32:(r + 1) * 32, 0:32] > 0).any() else 0 for r in range(7)]
        facts["water_alpha"] = got
        if got != want: probs.append(f"water alpha {got} != stamp {want}")
    mi = d / "graphics/images/sw_aq_mist.png"
    if mi.is_file():
        a = np.array(Image.open(mi).convert("RGBA"))[:, :, 3]
        facts["mist_alpha_max"] = int(a.max()); facts["mist_frame_px"] = [int((a[r * 32:(r + 1) * 32] > 0).sum()) for r in range(4)]
    return probs, facts


def set_preset(p):
    """The arm's preset into the mod AND the installed copy the world loads. In game when a map is loaded (the product
    path), else with the desk generator. Verified on disk: the installed copy's stamp must name the preset."""
    tool = Path(ARGS.tool_src)
    if state().get("map") == "true":
        out = aq("install", p, timeout=180)
        how = "in game"
    else:
        cmd = [sys.executable, str(tool / "tools/aquarium/make_aquarium_mod.py"), "--df", str(REAL_DF), "--out", str(mod_dir()), "--preset", p]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        out = r.stdout + r.stderr
        receipt(f"$ {' '.join(cmd)}\n{out}[rc={r.returncode}]\n")
        how = "desk generator"
    copies = installed_copies()
    got = {str(c.name): stamp(c).get("preset") for c in copies}
    if copies and any(v != p for v in got.values()):
        # the deployed aquarium.lua predates the installed-copy refresh (sw-wt rc 100f325): say so, then refresh at the desk
        rec(f"{STAGE}.preset.{p}.reaches_world", "FAIL",
            f"after `install {p}` ({how}) the installed copy the world loads still says {got}: the deployed "
            f"seasonal-wildlife-aquarium.lua does not refresh data/installed_mods (needs rc 100f325+); refreshing at the desk so the test can go on",
            data={"reply": out[-600:]})
        cmd = [sys.executable, str(tool / "tools/aquarium/make_aquarium_mod.py"), "--df", str(REAL_DF), "--out", str(mod_dir()), "--preset", p]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        receipt(f"$ {' '.join(cmd)}\n{r.stdout}{r.stderr}[rc={r.returncode}]\n")
        got = {str(c.name): stamp(c).get("preset") for c in installed_copies()}
    ok = stamp(mod_dir()).get("preset") == p and all(v == p for v in got.values())
    log(f"  preset {p} ({how}): mods/ {stamp(mod_dir()).get('preset')}, installed copies {got}")
    return ok, out


# ------------------------------------------------------------------------------------------------ view, targets, cells
GEOM_LUA = """
local g = df.global.gps; local mv = g.main_viewport
local lower = -1
pcall(function() lower = df.global.d_init.display.number_of_lower_elevations_shown end)
return { wx = df.global.window_x, wy = df.global.window_y, wz = df.global.window_z, dim_x = mv.dim_x, dim_y = mv.dim_y,
  spx = g.screen_pixel_x, spy = g.screen_pixel_y, zoom = g.viewport_zoom_factor, gm = dfhack.screen.inGraphicsMode(),
  lower = lower, paused = df.global.pause_state, tick = df.global.cur_year_tick,
  mx = df.global.world.map.x_count, my = df.global.world.map.y_count, mz = df.global.world.map.z_count }
"""


def geom():
    g, raw = lua("geom", GEOM_LUA)
    return g


def centre(x, y, z):
    g, raw = lua("centre", f"""
dfhack.gui.revealInDwarfmodeMap({x}, {y}, {z}, true)
df.global.window_z = {z}
local mv = df.global.gps.main_viewport
return {{ wx = df.global.window_x, wy = df.global.window_y, wz = df.global.window_z, dim_x = mv.dim_x, dim_y = mv.dim_y }}
""")
    nap(0.8)
    G = geom() or {}
    G["target"] = [x, y, z]
    log(f"  view centred on {x},{y},{z}: window {G.get('wx')},{G.get('wy')},{G.get('wz')} dim {G.get('dim_x')}x{G.get('dim_y')} px {G.get('spx')}x{G.get('spy')}")
    return G


FIND_LUA = """
local S, DL = %(stride)d, dfhack.getTickCount() + %(ms)d
local M = df.global.world.map
local W, H, Z = M.x_count, M.y_count, M.z_count
local OPEN = df.tiletype_shape_basic.Open
local function basic(tt) local a = df.tiletype.attrs[tt]; return df.tiletype_shape.attrs[a.shape].basic_shape, a.shape end
local cols, n, stopped = {}, 0, nil
for x = S // 2, W - 1, S do
  if dfhack.getTickCount() > DL then stopped = 'deadline'; break end
  local prev = Z - 1
  for y = S // 2, H - 1, S do
    local z = math.min(Z - 1, prev + 12)
    local tt = dfhack.maps.getTileType(x, y, z)
    while z < Z - 1 and tt and basic(tt) ~= OPEN do z = z + 1; tt = dfhack.maps.getTileType(x, y, z) end
    local top
    while z >= 0 do
      tt = dfhack.maps.getTileType(x, y, z)
      local d = dfhack.maps.getTileFlags(x, y, z)
      if not tt or not d then break end
      local b, shape = basic(tt)
      if d.flow_size > 0 then top = { z = z, magma = d.liquid_type, hidden = d.hidden, salt = d.water_salt, outside = d.outside, size = d.flow_size } break end
      if b ~= OPEN then
        if shape == df.tiletype_shape.BROOK_TOP then top = { z = z, brook = true, hidden = d.hidden, outside = d.outside } end
        break
      end
      z = z - 1
    end
    if top then
      prev = top.z
      if not top.hidden and not top.magma then
        local depth, zz = 0, top.z
        while zz >= 0 and depth < 12 do local d = dfhack.maps.getTileFlags(x, y, zz); if not d or d.flow_size == 0 then break end; depth = depth + 1; zz = zz - 1 end
        local flow = 0
        local zf = top.brook and top.z - 1 or top.z
        pcall(function() local blk = dfhack.maps.getTileBlock(x, y, zf); flow = blk.liquid_flow[x %% 16][y %% 16].perm_flow_dir end)
        if n < 4000 then n = n + 1; cols[n] = { x, y, top.z, depth, top.salt and 1 or 0, flow, top.brook and 1 or 0, top.size or 0 }
        else stopped = 'cap 4000 columns' end
      end
    elseif z >= 0 then prev = z end
  end
end
local flows, fc = {}, {}
for _, blk in ipairs(M.map_blocks) do
  for _, fl in ipairs(blk.flows) do
    if fl.density > 0 then
      local k = df.flow_type[fl.type] or tostring(fl.type)
      fc[k] = (fc[k] or 0) + 1
      if (k == 'Mist' or k == 'Steam' or k == 'OceanWave' or k == 'SeaFoam') and #flows < 400 then
        local d = dfhack.maps.getTileFlags(fl.pos.x, fl.pos.y, fl.pos.z)
        flows[#flows + 1] = { k, fl.pos.x, fl.pos.y, fl.pos.z, fl.density, d and d.hidden and 1 or 0 }
      end
    end
  end
end
local ev = df.global.world.event
local coast, fronts = {}, {}
for _, m in ipairs(ev.ocean_wave_makers) do
  pcall(function() for i = 0, #m.coastline.x - 1 do if #coast < 600 then coast[#coast + 1] = { m.coastline.x[i], m.coastline.y[i], m.pos.z } end end end)
end
for _, w in ipairs(ev.ocean_waves) do fronts[#fronts + 1] = { w.cur.x, w.cur.y, w.z, w.vis_duration } end
return { W = W, H = H, Z = Z, stride = S, cols = cols, stopped = stopped, flows = flows, flow_counts = fc, coast = coast,
         fronts = fronts, makers = #ev.ocean_wave_makers }
"""


def find_targets(stride=4):
    t0 = time.time()
    F, raw = lua("find", FIND_LUA % {"stride": stride, "ms": 9000}, timeout=120)
    if not F:
        log(f"  target finder failed: {raw[-300:]}")
        return {"error": raw[-400:]}
    cols = F.get("cols") or []
    by = {(c[0], c[1]): c for c in cols}
    S = F.get("stride", stride)

    def interior(c):   # stride-grid neighbours that are water with the same surface z
        return sum(1 for dx in (-S, 0, S) for dy in (-S, 0, S) if (dx or dy) and by.get((c[0] + dx, c[1] + dy), [0, 0, -1])[2] == c[2])
    T = {"lake": None, "river": None, "brook": None, "ocean": None, "mist": None, "surf": None, "counts": F.get("flow_counts"),
         "makers": F.get("makers"), "fronts": F.get("fronts")[:20] if F.get("fronts") else [], "stopped": F.get("stopped"),
         "columns": len(cols), "secs": round(time.time() - t0, 1)}
    lakes = [c for c in cols if not c[4] and not c[5] and not c[6] and c[3] >= 2]
    if lakes: T["lake"] = max(lakes, key=lambda c: (min(interior(c), 6), c[3]))[:4]
    rivers = [c for c in cols if c[5] and not c[6]]
    if rivers: T["river"] = max(rivers, key=lambda c: (interior(c), c[3]))[:4]
    brooks = [c for c in cols if c[6]]
    if brooks: T["brook"] = max(brooks, key=interior)[:4]
    oceans = [c for c in cols if c[4] and c[3] >= 2]
    if oceans: T["ocean"] = max(oceans, key=lambda c: (min(interior(c), 6), c[3]))[:4]
    mists = [f for f in (F.get("flows") or []) if f[0] in ("Mist", "Steam") and not f[5]]
    if mists:   # the densest visible cluster
        best = max(mists, key=lambda f: sum(g[4] for g in mists if abs(g[1] - f[1]) <= 3 and abs(g[2] - f[2]) <= 3 and g[3] == f[3]))
        T["mist"] = [best[1], best[2], best[3], best[0]]
    if F.get("fronts"):
        f = F["fronts"][0]; T["surf"] = [f[0], f[1], f[2], "front"]
    elif F.get("coast"):
        zs = {}
        for c in F["coast"]: zs[c[2]] = zs.get(c[2], 0) + 1
        z = max(zs, key=zs.get)
        pts = [c for c in F["coast"] if c[2] == z]
        p = pts[len(pts) // 2]; T["surf"] = [p[0], p[1], z, "coast"]
    T["flows"] = [f for f in (F.get("flows") or [])][:60]
    log(f"  targets ({T['columns']} columns, {T['secs']} s{', STOPPED ' + str(T['stopped']) if T['stopped'] else ''}): "
        f"lake {T['lake']} river {T['river']} brook {T['brook']} ocean {T['ocean']} mist {T['mist']} surf {T['surf']}; flows {T['counts']}; makers {T['makers']}")
    return T


CELLS_LUA = """
local x0, y0, z, R = %(x)d, %(y)d, %(z)d, %(r)d
local OPEN = df.tiletype_shape_basic.Open
local rows = {}
for y = y0 - R, y0 + R do
  local row = {}
  for x = x0 - R, x0 + R do
    local tt = dfhack.maps.getTileType(x, y, z)
    local d = dfhack.maps.getTileFlags(x, y, z)
    local c = '?'
    if tt and d then
      if d.hidden then c = 'h'
      elseif d.flow_size > 0 then c = d.liquid_type and 'm' or tostring(d.flow_size)
      else
        local b = df.tiletype_shape.attrs[df.tiletype.attrs[tt].shape].basic_shape
        if b == OPEN then
          local d2 = dfhack.maps.getTileFlags(x, y, z - 1)
          c = (d2 and d2.flow_size > 0) and 'b' or 'o'
        elseif b == df.tiletype_shape_basic.Wall then c = 'x'
        else c = 'l' end
      end
    end
    row[#row + 1] = c
  end
  rows[#rows + 1] = table.concat(row)
end
return { x0 = x0 - R, y0 = y0 - R, z = z, rows = rows }
"""


def cells_around(x, y, z, r=8):
    C, raw = lua("cells", CELLS_LUA % {"x": x, "y": y, "z": z, "r": r})
    return C or {"x0": x - r, "y0": y - r, "z": z, "rows": [], "error": raw[-200:]}


def pick_cells(C, x, y, kinds, n=9, rmax=4, away=None):
    """Up to n cells of a class near (x,y), nearest first. kinds: a set of class chars. away: cells to keep >= 2 cells
    from (a control must never touch what it controls for: a mist blob or a lens mark can spill into a neighbour)."""
    out = []
    for j, row in enumerate(C.get("rows") or []):
        for i, c in enumerate(row):
            cx_, cy_ = C["x0"] + i, C["y0"] + j
            d = max(abs(cx_ - x), abs(cy_ - y))
            if away and any(max(abs(cx_ - a), abs(cy_ - b)) < 2 for a, b in away): continue
            if c in kinds and d <= rmax: out.append((d, cx_, cy_))
    out.sort()
    return [(a, b) for _, a, b in out[:n]]


WATER = set("1234567")


# ------------------------------------------------------------------------------------------------ screenshots and pixels
_WIN = {"id": None}


def winid():
    if _WIN["id"]: return _WIN["id"]
    p = subprocess.run(["swift", str(ROOT / "scripts/cx-winid.swift")], capture_output=True, text=True, timeout=60)
    for line in p.stdout.splitlines():
        if "onscreen=true" in line and "|Dwarf Fortress|" in line:
            _WIN["id"] = line.split("|")[0]; break
    return _WIN["id"]


def shot(name, G=None):
    SHOTS.mkdir(parents=True, exist_ok=True)
    png = SHOTS / f"{name}.png"
    if MODE == "live":
        wid = winid()
        if not wid:
            log("  no DF window id (cx-winid.swift): no screenshot"); return None
        subprocess.run(["screencapture", "-l", wid, "-x", "-o", str(png)], timeout=30)
    else:
        FAKE.render(G).save(png)
    return png if png.exists() else None


def burst(name, n, gap, G=None):
    frames = []
    for i in range(n):
        p = shot(f"{name}-f{i + 1}", G)
        if p: frames.append(p)
        if MODE != "live": FAKE.t += gap
        nap(gap)
    if frames:
        ims = [Image.open(p).convert("RGB") for p in frames]
        w = 960; h = int(ims[0].height * w / ims[0].width)
        small = [im.resize((w, h)) for im in ims]
        small[0].save(SHOTS / f"{name}.gif", save_all=True, append_images=small[1:], duration=int(gap * 1000) or 250, loop=0)
        cols = min(3, len(small)); rows = math.ceil(len(small) / cols)
        sheet = Image.new("RGB", (cols * w // 2, rows * h // 2), (0, 0, 0))
        for k, im in enumerate(small):
            sheet.paste(im.resize((w // 2, h // 2)), ((k % cols) * w // 2, (k // cols) * h // 2))
        sheet.save(SHOTS / f"{name}-sheet.png")
    return frames


def cell_box(G, img, x, y, inset=0.22):
    """Pixel box of map cell (x,y) in a window capture: map = whole client area (screen_pixel_x x screen_pixel_y),
    dim_x x dim_y cells from window_x/window_y; the capture may be scaled (Retina) and carries the title bar on top."""
    W, H = img.size
    spx, spy = G.get("spx") or W, G.get("spy") or H
    sc = W / spx
    top = max(0, H - spy * sc)
    cw, ch = spx / max(1, G["dim_x"]) * sc, spy / max(1, G["dim_y"]) * sc
    x0, y0 = (x - G["wx"]) * cw, top + (y - G["wy"]) * ch
    return (int(x0 + cw * inset), int(y0 + ch * inset), int(x0 + cw * (1 - inset)), int(y0 + ch * (1 - inset)))


def region(img, G, cells):
    a = np.asarray(img.convert("RGB"), dtype=np.float32)
    parts = []
    for (x, y) in cells:
        x0, y0, x1, y1 = cell_box(G, img, x, y)
        if x1 > x0 and y1 > y0 and x0 >= 0 and y0 >= 0 and x1 <= a.shape[1] and y1 <= a.shape[0]:
            parts.append(a[y0:y1, x0:x1].reshape(-1, 3))
    return np.concatenate(parts) if parts else None


def stats(img, G, cells):
    r = region(img, G, cells)
    if r is None: return None
    L = r @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    a = np.asarray(img.convert("L"), dtype=np.float32)
    edge = []
    for (x, y) in cells:
        x0, y0, x1, y1 = cell_box(G, img, x, y)
        if x1 - x0 > 2 and y1 - y0 > 2 and x0 >= 0 and y0 >= 0 and x1 <= a.shape[1] and y1 <= a.shape[0]:
            b = a[y0:y1, x0:x1]
            edge.append(float(np.abs(np.diff(b, axis=0)).mean() + np.abs(np.diff(b, axis=1)).mean()))
    return {"n": len(cells), "L": round(float(L.mean()), 2), "Lsd": round(float(L.std()), 2), "rgb": [round(float(v), 1) for v in r.mean(0)],
            "edge": round(float(np.mean(edge)), 2) if edge else None, "dark": round(float((L < 25).mean()), 3)}


def diff(img_a, img_b, G, cells):
    a, b = region(img_a, G, cells), region(img_b, G, cells)
    if a is None or b is None or a.shape != b.shape: return None
    return round(float(np.abs(a - b).mean()), 2)


def annotate(img_path, G, groups, name):
    """Copy of the frame with the measured cells boxed (red target, yellow control, cyan other) for the lead's eye."""
    try:
        im = Image.open(img_path).convert("RGB"); d = ImageDraw.Draw(im)
        colours = {"target": (255, 40, 40), "control": (255, 220, 0), "other": (0, 220, 255)}
        for kind, cells in groups.items():
            for (x, y) in cells or []:
                d.rectangle(cell_box(G, im, x, y, inset=0.05), outline=colours.get(kind, (255, 255, 255)), width=2)
        p = SHOTS / f"{name}-boxes.png"; im.save(p); return p
    except Exception as e:   # never let a drawing aid fail a test
        log(f"  annotate {name}: {e}"); return None


def frame_changes(frames, G, cells):
    ims = [Image.open(p) for p in frames]
    ds = [diff(a, b, G, cells) for a, b in zip(ims, ims[1:])]
    ds = [x for x in ds if x is not None]
    return round(float(np.mean(ds)), 2) if ds else None


# ------------------------------------------------------------------------------------------------ status parsing
def status():
    return aq("status")


def status_facts(txt):
    f = {}
    m = re.search(r"graphics mode (\w+)", txt); f["graphics"] = m and m.group(1)
    m = re.search(r"DF shows (-?\d+|\?) lower level", txt); f["lower"] = m and m.group(1)
    f["active"] = "ACTIVE in this world" in txt
    m = re.search(r"this world loaded (.+?): preset (\w+)", txt); f["world_preset"] = m and m.group(2); f["world_copy"] = m and m.group(1)
    m = re.search(r"mod: installed at .*?, preset (\w+)", txt); f["mods_preset"] = m and m.group(1)
    f["stopped"] = re.findall(r"^\s+(\w+)\s+STOPPED: (.*)$", txt, re.M)
    f["paint_avgs"] = [float(x) for x in re.findall(r"paint avg ([\d.]+) ms", txt)]
    f["auto_no_ocean"] = "auto: no ocean on this map" in txt
    return f


def errorlog_mark():
    p = REAL_DF / "errorlog.txt"
    return p.stat().st_size if p.exists() and MODE == "live" else 0


def errorlog_since(mark):
    p = REAL_DF / "errorlog.txt"
    if MODE != "live" or not p.exists(): return []
    with open(p, "rb") as f:
        f.seek(mark); t = f.read().decode("latin-1", "replace")
    return [l for l in t.splitlines() if re.search(r"sw_aq|SW_AQ|aquarium|TILE_PAGE|graphics|UNDERWATER|FLOW_|RIVER_TO|BROOK_TO|tile page", l, re.I)]


# ------------------------------------------------------------------------------------------------ stages
def st_setup():
    tool = Path(ARGS.tool_src)
    dest = DF_DIR / "dfhack-config/scripts"
    if ARGS.deploy:
        rc, out, err = cx("deploy-tool", tool / "scripts", timeout=180)
        if MODE == "live": shutil.copy2(tool / "tests/rig/sw-aquarium-watch.lua", dest / "sw-aquarium-watch.lua")
        rec("setup.deploy_tool", "PASS" if rc == 0 else "FAIL", (out + err).strip()[-400:])
    bad = [f for f in ("scripts/seasonal-wildlife-aquarium.lua", "scripts/seasonal-wildlife-aquarium-gfx.lua", "scripts/seasonal-wildlife.lua",
                       "tests/rig/sw-aquarium-watch.lua") if LUAC.exists() and subprocess.run([str(LUAC), "-p", str(tool / f)], capture_output=True).returncode]
    rec("setup.luac53", "FAIL" if bad else "PASS", f"luac53 -p: {'failed ' + ', '.join(bad) if bad else 'OK'} ({tool})")
    pairs = [("scripts/seasonal-wildlife-aquarium.lua", "seasonal-wildlife-aquarium.lua"), ("scripts/seasonal-wildlife-aquarium-gfx.lua", "seasonal-wildlife-aquarium-gfx.lua"),
             ("tests/rig/sw-aquarium-watch.lua", "sw-aquarium-watch.lua")]
    side = [("scripts/seasonal-wildlife.lua", "seasonal-wildlife.lua"), ("scripts/seasonal-wildlife-controls.lua", "seasonal-wildlife-controls.lua")]
    rows = {}
    for a, b in pairs + side:
        s, d = tool / a, dest / b
        rows[b] = "identical" if d.is_file() and s.read_bytes() == d.read_bytes() else ("ABSENT" if not d.is_file() else "DIFFERS")
    need = all(rows[b] == "identical" for _, b in pairs)
    head = subprocess.run(["git", "-C", str(tool), "log", "--oneline", "-1"], capture_output=True, text=True).stdout.strip()
    rec("setup.deploy", "PASS" if need else "FAIL",
        f"in {dest}: " + ", ".join(f"{k} {v}" for k, v in rows.items()) + f" (tool {head}); fix: cx-lifecycle.sh deploy-tool {tool}/scripts and copy tests/rig/sw-aquarium-watch.lua",
        data=rows)
    # the mod on disk (read only): the folder new worlds take, and the installed copy region10 actually loads
    probs, facts = check_mod_folder(REAL_USER / "mods" / MOD_ID, tool, "mods")
    rec("setup.mod_folder", "PASS" if not probs else "FAIL",
        f"{REAL_USER / 'mods' / MOD_ID}: " + ("10 files, PNG sizes = raws, water alpha = stamp " + str(facts.get("stamp", {}).get("preset")) if not probs else "; ".join(probs)),
        data=facts)
    copies = installed_copies(REAL_USER)
    if not copies:
        rec("setup.installed_copy", "FAIL", f"no data/installed_mods/{MOD_ID} (N) under {REAL_USER}: no world made with the mod has been loaded/created")
    for c in copies:
        probs, facts = check_mod_folder(c, tool, "installed")
        same = all((c / f).is_file() and (REAL_USER / "mods" / MOD_ID / f).is_file() and (c / f).read_bytes() == (REAL_USER / "mods" / MOD_ID / f).read_bytes() for f in GFX_FILES)
        if not same: probs.append("differs from mods/ (a preset written to mods/ has not reached the copy worlds load)")
        rec("setup.installed_copy", "PASS" if not probs else "FAIL", f"{c} (what region10 loads): " + ("matches mods/ and its stamp" if not probs else "; ".join(probs)), data=facts)
    if ARGS.view: return
    # in game: the status receipt on the aquarium fort
    if not ensure_fort(FORT["lake"], why="(setup: status)"): return
    cx("cmd", "overlay", "list", "seasonal-wildlife-aquarium")
    st = status(); f = status_facts(st)
    rec("setup.status", "PASS" if "aquarium:" in st and "mod:" in st else "FAIL", st.strip()[:600], data=f)
    rec("setup.graphics", "PASS" if f["graphics"] == "yes" else "FAIL", f"graphics mode {f['graphics']} (the overlays and the mod need graphics mode)")
    lv = f["lower"]
    rec("setup.lower_elevations", "PASS" if lv not in (None, "?", "0", "-1") else "FAIL",
        f"DF shows {lv} lower level(s) (Settings -> lower elevations shown); 0 makes T2's question moot and deep water opaque")


def embark_shore():
    """Embark AQUA_SHORE on region10 at 205,170 (6x6, offset 5,13), opening the world by FOLDER: region9 and region10 share
    the name 'Camade Mare', so cx-lifecycle's own embark refuses; the row is chosen by its place among same-name rows in
    DF's own list and the opened world is proven by its mod list before anything is clicked on the map."""
    name = FORT["ocean"]
    if MODE == "live" and (REAL_USER / "save" / name).exists():
        ok = (BACKUPS / f"{name}.preverify").is_dir()
        rec("shore.exists", "PASS" if ok else "FAIL", f"save {name} already exists; backup {name}.preverify {'present' if ok else 'MISSING: cx-lifecycle.sh save-backup ' + name + ' preverify'}")
        return ok
    st = state()
    if st.get("map") == "true": cx("title", timeout=240); st = state()
    if st.get("screen") != "viewscreen_titlest":
        rec("shore.title", "FAIL", f"DF is not at the title screen: {st}"); return False
    rc, out, err = cx("cmd", "cx-embark", "worlds", timeout=60)
    rows = [l.split("\t") for l in out.splitlines() if "\t" in l]
    wname = next((r[1].strip() for r in rows if r[0] == SHORE["world"]), None)
    if not wname:
        rec("shore.world", "FAIL", f"DF lists no world folder {SHORE['world']}: {rows}"); return False
    same = [r[0] for r in rows if r[1].strip() == wname]
    k = same.index(SHORE["world"])
    if 0 < k < len(same) - 1:
        rec("shore.world", "FAIL", f"{SHORE['world']} is row {k + 1} of {len(same)} named '{wname}' ({same}): neither first nor last; move a world out (DF stopped)"); return False
    cx("ui", "click", "Start new game in existing world", timeout=60)
    cx("wait", f"World: {wname}", "20", timeout=60)
    cx("ui", "clicklast" if (k == len(same) - 1 and len(same) > 1) else "click", f"World: {wname}", timeout=60)
    if not wait_state("screen", "viewscreen_choose_game_typest", 120):
        rec("shore.open", "FAIL", f"the world did not load to the game-type screen: {state()}"); return False
    W, raw = lua("worldid", """
local mods = {}
for _, m in ipairs(require('script-manager').get_active_mods()) do mods[#mods + 1] = m.id end
local dir = '?'
pcall(function() dir = df.global.world.cur_savegame.save_dir end)
return { mods = mods, sites = #df.global.world.world_data.sites, save_dir = dir }
""")
    okw = bool(W) and MOD_ID in (W.get("mods") or [])
    rec("shore.world_is_region10", "PASS" if okw else "FAIL",
        f"opened row {k + 1}/{len(same)} '{wname}': mods include {MOD_ID}: {okw}; sites {W and W.get('sites')} (region10 1527, region9 1577); save_dir {W and W.get('save_dir')}",
        data=W)
    if not okw:
        for _ in range(4):
            cx("key", "LEAVESCREEN"); nap(1)
            if state().get("screen") == "viewscreen_titlest": break
        return False
    cx("ui", "click", "Fortress", timeout=60)
    if not wait_state("screen", "viewscreen_choose_start_sitest", 90):
        rec("shore.site_screen", "FAIL", f"no site screen: {state()}"); return False
    cx("ui", "click", "Okay")
    cx("cmd", "cx-embark", "center", SHORE["rx"], SHORE["ry"])
    nap(1)
    rd = ""
    for _ in range(3):
        cx("ui", "click", "Okay"); cx("ui", "clicklast", "Embark"); nap(1)
        rd = cx("cmd", "cx-embark", "read")[1]
        if "choosing=true" in rd: break
    if "choosing=true" not in rd:
        rec("shore.placement", "FAIL", f"Embark did not enter placement mode: {rd.strip()}"); return False
    cx("cmd", "cx-embark", "size", SHORE["size"]); nap(1)
    tx, ty = SHORE["rx"] * 16 + SHORE["ox"], SHORE["ry"] * 16 + SHORE["oy"]
    rd = cx("cmd", "cx-embark", "place", tx, ty)[1]
    if not rd.strip().startswith("placed"):
        rec("shore.place", "FAIL", f"place failed: {rd.strip()} ({state()})"); return False
    nap(1)
    if state().get("screen") != "viewscreen_setupdwarfgamest":
        rd = cx("cmd", "cx-embark", "read")[1]
        if f"mm_min={tx},{ty}" in rd and "confirm=true" in rd:
            cx("ui", "click", "Confirm")
        else:
            rec("shore.place", "FAIL", f"the embark click did not take (want {tx},{ty}): {rd.strip()}"); return False
    if not wait_state("screen", "viewscreen_setupdwarfgamest", 40):
        rec("shore.prepare", "FAIL", f"no preparation screen: {state()}"); return False
    cx("wait", "Play now!", "30", timeout=60); cx("ui", "click", "Play now!")
    if not wait_state("map", "true", 300):
        rec("shore.map", "FAIL", f"map never loaded: {state()}"); return False
    nap(2); cx("ui", "click", "Okay"); cx("pause")
    rd = cx("cmd", "cx-embark", "site")[1]
    if f"mm_min={tx},{ty} " not in rd + " ":
        rec("shore.site", "FAIL", f"the fort is not where it was placed (want {tx},{ty}): {rd.strip()}"); return False
    rc, out, err = cx("save", name, timeout=200)
    cx("title", timeout=240)
    rc2, out2, err2 = cx("save-backup", name, "preverify", timeout=300)
    ok = rc == 0 and rc2 == 0
    rec("shore.embark", "PASS" if ok else "FAIL", f"region10 tile {SHORE['rx']},{SHORE['ry']} {SHORE['size']}x{SHORE['size']} at {tx},{ty}: {rd.strip()}; save: {(out + err).strip()[-160:]}; backup: {(out2 + err2).strip()[-160:]}")
    return ok


def st_shore():
    if not ARGS.embark_shore:
        ok = MODE != "live" or (BACKUPS / f"{FORT['ocean']}.preverify").is_dir()
        rec("shore.present", "PASS" if ok else "FAIL", f"{FORT['ocean']}.preverify {'present' if ok else 'absent: run with --embark-shore (T3/T4/T5/T8 need it)'}")
        return
    embark_shore()


def capture_target(tag, kind, T, G0=None, frames=1, unpause=False, extra=None):
    """Centre on target T=[x,y,z,...], classify the cells around it, capture (one frame or a burst), annotate.
    Returns a dict with geometry, cells, frames and stats -- the receipt of what was looked at."""
    x, y, z = T[0], T[1], T[2]
    G = centre(x, y, z)
    if "wx" not in G or not G.get("dim_x"):
        p = shot(tag, None) if MODE == "live" else None
        return {"tag": tag, "target": T, "geom": G, "water": [], "control": [], "frames": [str(p)] if p else [], "error": "no view geometry (centre/geom Lua failed: see receipts)"}
    C = cells_around(x, y, z, 12)
    water = pick_cells(C, x, y, WATER | set("b"), n=9, rmax=3) or [(x, y)]
    if kind in ("mist", "surf"):
        water = [(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
    if extra: water = extra
    control = pick_cells(C, x, y, set("lx"), n=9, rmax=12, away=water)
    if unpause: cx("unpause")
    fr = burst(tag, frames, ARGS.gap, G) if frames > 1 else [shot(tag, G)]
    if unpause: cx("pause")
    fr = [f for f in fr if f]
    res = {"tag": tag, "target": T, "geom": G, "cells": C.get("rows"), "water": water, "control": control, "frames": [str(f) for f in fr]}
    if fr:
        im = Image.open(fr[0])
        res["stats_target"] = stats(im, G, water); res["stats_control"] = stats(im, G, control) if control else None
        if len(fr) > 1:
            res["anim_target"] = frame_changes(fr, G, water); res["anim_control"] = frame_changes(fr, G, control) if control else None
        res["boxes"] = str(annotate(fr[0], G, {"target": water, "control": control}, tag))
    return res


def spawn_mist(T):
    """Spawn a Mist (MIST_WATERFALL) and a Steam (MIST_WATER) flow side by side at the target's level, to see which
    flow types DF draws with its water-mist sprite. Returns {Mist:[x,y,z], Steam:[x,y,z]} for the cells that took one."""
    x, y, z = T[0], T[1], T[2]
    S, raw = lua("spawn", f"""
local out = {{}}
for k, dx in pairs({{ Mist = -2, Steam = 2 }}) do
  local pos = xyz2pos({x} + dx, {y}, {z})
  local fl = dfhack.maps.spawnFlow(pos, df.flow_type[k], 6, -1, 100)
  out[k] = fl and {{ pos.x, pos.y, pos.z }} or false
end
return out
""")
    return S or {}, raw


def t1_arms(only_mist=False):
    """T1 (+ the mist rows): per preset arm, set the preset into the mod and the copy the world loads, reload AQUA_LAKE,
    status, then capture the lake and river (and brook) views and the mist, with every overlay off so only DF draws."""
    presets = [p.strip() for p in ARGS.presets.split(",") if p.strip()]
    if "vanilla" not in presets: presets = ["vanilla"] + presets
    arms, targets = {}, None
    mark = errorlog_mark()
    for p in presets:
        log(f"== T1 arm {p}")
        set_preset(p)
        if not load_fort(FORT["lake"], f"(T1 arm {p})"): return
        st = status(); f = status_facts(st)
        rec(f"t1.{p}.world_preset", "PASS" if f["world_preset"] == p or (MODE == "live" and f["world_preset"] is None and stamp_copy_is(p)) else "FAIL",
            f"status after reload: world loaded {f['world_copy']} preset {f['world_preset']} (want {p}); mods/ {f['mods_preset']}; active {f['active']}", data=f)
        aq("off")
        targets = targets or find_targets()
        arm = {"status": f}
        for kind in (["lake", "river", "brook"] if not only_mist else []):
            T = targets.get(kind)
            if not T: continue
            arm[kind] = capture_target(f"t1-{p}-{kind}", kind, T, frames=(ARGS.frames if kind in ("river", "brook") else 1), unpause=kind in ("river", "brook"))
        arm["mist"] = mist_capture(p, targets)
        if p == "aquarium" and arm["mist"].get("frames"):
            aq("on"); aq("foam", "on"); aq("waves", "on")
            M = arm["mist"]; T = M["target"]
            arm["mist_overlay"] = capture_target(f"t1-{p}-mist-overlay", "mist", T, frames=ARGS.frames, unpause=True)
            aq("waves", "auto")
        arms[p] = arm
    lines = errorlog_since(mark)
    rec("t1.errorlog", "PASS" if not lines else "FAIL", f"{len(lines)} new errorlog.txt line(s) about graphics/tile pages/the mod: {lines[:8]}", data=lines[:40])
    t1_verdicts(arms, targets or {}, only_mist)
    if ARGS.restart_escalate and not only_mist and "aquarium" in arms:
        d = (arms["aquarium"].get("lake") or {}).get("vs_vanilla")
        if d is not None and d < TRANS_MIN:
            log("== T1 escalation: no change after a title reload; restarting DF and capturing the aquarium arm again")
            cx("stop", timeout=180); cx("start", timeout=400)
            if load_fort(FORT["lake"], "(T1 escalation)"):
                aq("off")
                again = capture_target("t1-aquarium-lake-restart", "lake", targets["lake"])
                van = Image.open(arms["vanilla"]["lake"]["frames"][0]); G = again["geom"]
                dd = diff(van, Image.open(again["frames"][0]), G, again["water"]) if again.get("frames") else None
                rec("t1.reload_needs_restart", "INFO", f"after a DF restart the lake differs from vanilla by {dd} (title reload: {d}); "
                    f"{'DF re-reads tile pages only on restart' if dd and dd >= TRANS_MIN else 'still no change: the pages are not reaching the renderer'}",
                    shots=again["frames"])
    set_preset("aquarium")   # leave the rig on the default look


def stamp_copy_is(p):
    return all(stamp(c).get("preset") == p for c in installed_copies()) if installed_copies() else False


def mist_capture(p, targets):
    T = targets.get("mist")
    res = {"target": T, "source": "natural" if T else None}
    if T:
        cap = capture_target(f"t1-{p}-mist", "mist", T, frames=ARGS.frames, unpause=True)
        res.update(cap)
        return res
    if ARGS.no_spawn:
        res["source"] = "none"; return res
    base = targets.get("river") or targets.get("lake") or targets.get("brook") or targets.get("ocean")
    if not base:
        res["source"] = "none (no water target to spawn over)"; return res
    G = centre(base[0], base[1], base[2])
    before = shot(f"t1-{p}-mist-before", G)
    S, raw = spawn_mist(base)
    if MODE != "live": FAKE.spawned = S
    res["source"] = "spawned"; res["spawn"] = S; res["spawn_raw"] = raw[-200:]
    cells = {k: [(v[0] + dx, v[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)] for k, v in S.items() if v}
    nap(0.3)
    after = shot(f"t1-{p}-mist-after", G)
    cx("unpause")
    fr = burst(f"t1-{p}-mist", ARGS.frames, ARGS.gap, G)
    cx("pause")
    C = cells_around(base[0], base[1], base[2], 12)
    control = pick_cells(C, base[0], base[1], set("lx"), n=9, rmax=12, away=sum(cells.values(), []))
    res.update({"geom": G, "target": [base[0], base[1], base[2], "spawned"], "frames": [str(f) for f in fr], "before": str(before), "after": str(after),
                "control": control, "cells_by_type": cells, "water": sum(cells.values(), [])})
    if before and after:
        ib, ia = Image.open(before), Image.open(after)
        res["drawn"] = {k: diff(ib, ia, G, c) for k, c in cells.items()}
        res["drawn_control"] = diff(ib, ia, G, control) if control else None
    if fr:
        res["anim_target"] = frame_changes(fr, G, res["water"]); res["anim_control"] = frame_changes(fr, G, control) if control else None
        res["stats_target"] = stats(Image.open(fr[0]), G, res["water"])
        res["boxes"] = str(annotate(fr[0], G, {"target": res["water"], "control": control}, f"t1-{p}-mist"))
    return res


def t1_verdicts(arms, targets, only_mist):
    van = arms.get("vanilla") or {}
    data = {p: {k: {kk: v.get(kk) for kk in ("target", "stats_target", "stats_control", "anim_target", "anim_control", "drawn", "drawn_control", "source", "boxes")}
                for k, v in a.items() if isinstance(v, dict) and k != "status"} for p, a in arms.items()}
    (OUT / "t1-metrics.json").write_text(json.dumps(data, indent=1, default=str))
    for kind in ([] if only_mist else ["lake", "river", "brook"]):
        if not targets.get(kind):
            rec(f"t1.{kind}", "FAIL" if kind == "lake" else "NOT-TESTABLE",
                f"no visible {kind} water found on {FORT['lake']} by the finder ({targets.get('columns')} columns sampled; stopped {targets.get('stopped')})")
            continue
        V = van.get(kind)
        for p, a in arms.items():
            if p == "vanilla" or kind not in a: continue
            A = a[kind]
            if not (V and V.get("frames") and A.get("frames")):
                rec(f"t1.{kind}.{p}", "FAIL", "no capture (see log)"); continue
            G = A["geom"]
            iv, ia = Image.open(V["frames"][0]), Image.open(A["frames"][0])
            dw, dc = diff(iv, ia, G, A["water"]), (diff(iv, ia, G, A["control"]) if A["control"] else None)
            A["vs_vanilla"] = dw
            same_view = V["geom"].get("wx") == G.get("wx") and V["geom"].get("wy") == G.get("wy") and V["geom"].get("wz") == G.get("wz")
            ok = dw is not None and dw >= TRANS_MIN and (dc is None or dc <= CONTROL_MAX) and same_view
            sv, sa = V.get("stats_target") or {}, A.get("stats_target") or {}
            rec(f"t1.{kind}.{p}", "PASS" if ok else "FAIL",
                f"{kind} at {A['target'][:3]}: water cells differ from vanilla by {dw} (need >= {TRANS_MIN}), dry control by {dc} (need <= {CONTROL_MAX}, "
                f"{len(A['control'])} cells), same view {same_view}; luminance {sv.get('L')} -> {sa.get('L')}, edge detail {sv.get('edge')} -> {sa.get('edge')}, "
                f"dark {sv.get('dark')} -> {sa.get('dark')}", data={"vanilla": sv, p: sa, "diff_water": dw, "diff_control": dc}, shots=[V.get("boxes"), A.get("boxes")])
        A = (arms.get("aquarium") or {}).get(kind)
        if kind in ("river", "brook") and A and A.get("frames"):
            at, ac = A.get("anim_target"), A.get("anim_control")
            ok = at is not None and at >= ANIM_MIN and (ac is None or at >= 2 * ac)
            rec(f"t1.{kind}.streaks_animate", "PASS" if ok else "FAIL",
                f"{len(A['frames'])} frames {ARGS.gap}s apart (unpaused, overlays off): mean frame change in the {kind} cells {at} (need >= {ANIM_MIN} and >= 2x control {ac})",
                shots=[str(SHOTS / f"t1-aquarium-{kind}.gif"), A.get("boxes")])
    # mist
    M = (arms.get("aquarium") or arms.get(next(iter(arms), "")) or {}).get("mist") or {}
    src = M.get("source")
    rec("mist.source", "PASS" if src == "natural" else ("INFO" if src == "spawned" else "FAIL"),
        f"Mist/Steam flows on the map: {targets.get('counts')}; source {src} at {M.get('target')}" +
        ("" if src == "natural" else "; no waterfall mist on AQUA_LAKE: test flows spawned (dfhack.maps.spawnFlow) so the sprite can be judged" if src == "spawned" else
         "; none found and none spawned (--no-spawn)"), data={"flows": targets.get("flows")})
    if src == "spawned":
        for k in ("Mist", "Steam"):
            d = (M.get("drawn") or {}).get(k)
            if d is None:
                rec(f"mist.drawn.{k}", "FAIL", f"spawnFlow({k}) returned nothing: {M.get('spawn_raw')}"); continue
            ok = d >= MIST_MIN and (M.get("drawn_control") is None or M["drawn_control"] <= CONTROL_MAX)
            rec(f"mist.drawn.{k}", ("PASS" if ok else "FAIL") if k == "Mist" else ("INFO"),
                f"{k} ({'MIST_WATERFALL' if k == 'Mist' else 'MIST_WATER'}) cells before/after the spawn differ by {d} (need >= {MIST_MIN}); control {M.get('drawn_control')}"
                + ("" if k == "Mist" else " -- whether DF draws MIST_WATER with FLOW_WATER_MIST (answers the preflight's coverage question)"),
                shots=[M.get("before"), M.get("after"), M.get("boxes")])
    if M.get("frames"):
        at, ac = M.get("anim_target"), M.get("anim_control")
        ok = at is not None and at >= ANIM_MIN and (ac is None or at >= 2 * ac)
        rec("mist.animates", "PASS" if ok else "FAIL",
            f"{len(M['frames'])} frames (unpaused, overlays off): mean frame change in the mist cells {at} (need >= {ANIM_MIN} and >= 2x control {ac})",
            shots=[str(SHOTS / "t1-aquarium-mist.gif"), M.get("boxes")])
        V = (arms.get("vanilla") or {}).get("mist") or {}
        if V.get("frames") and "aquarium" in arms:
            sv, sa = V.get("stats_target") or {}, M.get("stats_target") or {}
            d = (np.array(sa.get("rgb") or [0, 0, 0]) - np.array(sv.get("rgb") or [0, 0, 0])).tolist()
            rec("mist.restyle", "INFO", f"mist cells mean RGB vanilla {sv.get('rgb')} -> aquarium {sa.get('rgb')} (delta {[round(x, 1) for x in d]}; the restyle is alpha x0.75 + 15% cool tint)")
        O = (arms.get("aquarium") or {}).get("mist_overlay")
        if O and O.get("frames"):
            G = O["geom"]
            dov = diff(Image.open(M["frames"][0]), Image.open(O["frames"][0]), G, O["water"]) if M.get("frames") else None
            rec("mist.overlay_foam", "PASS" if dov is not None and dov >= MIST_MIN and (O.get("anim_target") or 0) >= ANIM_MIN else "FAIL",
                f"overlay on (foam on): mist cells differ from the overlay-off burst by {dov} (need >= {MIST_MIN}; includes the mist's own drift) and change "
                f"{O.get('anim_target')} frame to frame (control {O.get('anim_control')})",
                shots=[str(SHOTS / "t1-aquarium-mist-overlay.gif")])


FISH_LUA = """
local best, list = nil, {}
for _, u in ipairs(df.global.world.units.active) do
  if not dfhack.units.isDead(u) then
    local x, y, z = dfhack.units.getPosition(u)
    local d = x and dfhack.maps.getTileFlags(x, y, z)
    if d and d.flow_size > 0 and not d.liquid_type then
      local top = z
      while true do
        local d2 = dfhack.maps.getTileFlags(x, y, top + 1)
        if not d2 or d2.flow_size == 0 then break end
        top = top + 1
      end
      local dt = dfhack.maps.getTileFlags(x, y, top)
      if top > z and dt and not dt.hidden then
        list[#list + 1] = { x, y, z, top, df.global.world.raws.creatures.all[u.race].creature_id, u.id }
      end
    end
  end
end
for _, a in ipairs(list) do
  local n = 0
  for _, b in ipairs(list) do if math.abs(a[1] - b[1]) <= 4 and math.abs(a[2] - b[2]) <= 4 and a[4] == b[4] then n = n + 1 end end
  if not best or n > best.n then best = { n = n, x = a[1], y = a[2], z = a[4] } end
end
return { best = best, n = #list, fish = list }
"""


def find_fish():
    F, raw = lua("fish", FISH_LUA)
    return F or {"best": None, "n": 0, "fish": [], "error": raw[-200:]}


def fish_view(tag):
    F = find_fish()
    if not F.get("best") and ARGS.fish:
        sw("place", ARGS.fish, "6", "water", timeout=120); F = find_fish()
    if not F.get("best"):
        sw("water", "now", timeout=180); cx("step", "100", "60", timeout=120); F = find_fish()
    return F


def t2():
    presets = [p.strip() for p in ARGS.t2_presets.split(",") if p.strip()]
    for p in presets:
        log(f"== T2 arm {p}")
        set_preset(p)
        if not load_fort(FORT["lake"], f"(T2 {p})"): return
        aq("on")
        F = fish_view(p)
        b = F.get("best")
        if not b:
            rec(f"t2.{p}.fish", "FAIL", f"no creature below the surface of visible water on {FORT['lake']} ({F.get('error', '')}); pass --fish TOKEN (a stocked water entry) and re-run")
            continue
        fish = [(f[0], f[1]) for f in F["fish"] if f[3] == b["z"] and abs(f[0] - b["x"]) <= 6 and abs(f[1] - b["y"]) <= 6]
        rec(f"t2.{p}.fish", "PASS", f"{F['n']} creatures below a visible water surface; view over {b['n']} at {b['x']},{b['y']} z {b['z']}",
            data={"fish": F["fish"][:30]})
        aq("lens", "off"); nap(0.6)
        off = capture_target(f"t2-{p}-lens-off", "lake", [b["x"], b["y"], b["z"]], extra=fish)
        aq("lens", "on"); nap(1.2)
        on = capture_target(f"t2-{p}-lens-on", "lake", [b["x"], b["y"], b["z"]], extra=fish)
        pr = aq("probe")
        m = re.search(r"(\d+) creatures below in view, (\d+) cells marked", pr)
        rec(f"t2.{p}.probe", "PASS" if m and int(m.group(1)) > 0 else "FAIL", pr.strip()[:500])
        if off.get("frames") and on.get("frames"):
            G = on["geom"]
            io_, in_ = Image.open(off["frames"][0]), Image.open(on["frames"][0])
            dl, dc = diff(io_, in_, G, fish), (diff(io_, in_, G, on["control"]) if on["control"] else None)
            rec(f"t2.{p}.lens_draws", "PASS" if dl is not None and dl >= LENS_MIN and (dc is None or dc <= CONTROL_MAX) else "FAIL",
                f"lens on v off: fish cells differ by {dl} (need >= {LENS_MIN}), dry control by {dc}", shots=[off.get("boxes"), on.get("boxes")])
            # the open question: with the lens off, do the fish cells stand out from water cells at the same level?
            C = cells_around(b["x"], b["y"], b["z"], 8)
            nb = pick_cells(C, b["x"], b["y"], WATER, n=20, rmax=8, away=fish)
            sf, sn = stats(io_, G, fish), stats(io_, G, nb)
            score = None
            if sf and sn and sn.get("Lsd"):
                score = round(abs(sf["L"] - sn["L"]) / max(1.0, sn["Lsd"]), 2)
            rec(f"t2.{p}.df_shows_below", "INFO",
                f"lens off: fish cells L {sf and sf['L']} edge {sf and sf['edge']} v water neighbours L {sn and sn['L']} edge {sn and sn['edge']} (sd {sn and sn['Lsd']}): "
                f"contrast {score} sd ({'DF appears to draw them through the water' if score and score >= 1.0 else 'no sign DF draws them: the lens carries the view'})",
                data={"fish": sf, "neighbours": sn}, shots=[off.get("boxes")])
    set_preset("aquarium")


def t3():
    presets = [p.strip() for p in ARGS.t3_presets.split(",") if p.strip()]
    caps = {}
    for p in presets:
        log(f"== T3 arm {p}")
        set_preset(p)
        if not load_fort(FORT["ocean"], f"(T3 {p})"): return
        aq("off")
        if "_T" not in caps: caps["_T"] = find_targets()
        T = caps["_T"].get("ocean")
        if not T:
            rec("t3.ocean", "FAIL", f"no visible salt water 2+ deep on {FORT['ocean']}"); return
        caps[p] = capture_target(f"t3-{p}-ocean", "ocean", T)
        s = caps[p].get("stats_target") or {}
        rec(f"t3.{p}.view", "INFO", f"ocean at {T[:3]} (column depth {T[3]}): L {s.get('L')}, dark fraction {s.get('dark')}, edge {s.get('edge')}", shots=[caps[p].get("boxes")])
    A, V = caps.get("aquarium"), caps.get("vanilla")
    if A and A.get("stats_target"):
        dark = A["stats_target"]["dark"]
        rec("t3.deep_ocean", "PASS" if dark < 0.5 else "FAIL",
            f"aquarium preset: {round(dark * 100)}% of the sea cells near-black (L < 25): {'fog / floor: keep aquarium' if dark < 0.5 else 'BLACK: make shallows the ocean default'}")
        if V and V.get("frames") and A.get("frames"):
            d = diff(Image.open(V["frames"][0]), Image.open(A["frames"][0]), A["geom"], A["water"])
            rec("t3.transparency", "PASS" if d is not None and d >= TRANS_MIN else "FAIL", f"sea cells aquarium v vanilla differ by {d} (need >= {TRANS_MIN})")
    set_preset("aquarium")


def t4():
    if not ensure_fort(FORT["ocean"], fresh=True, why="(T4)"): return
    watch = REAL_DF / "sw-aquarium-watch.txt"
    m0 = watch.stat().st_mtime if watch.exists() else 0
    cx("cmd", "sw-aquarium-watch", "6000", "100", timeout=60)
    cx("step", "6300", "600", timeout=700)
    if MODE == "live" and (not watch.exists() or watch.stat().st_mtime <= m0):
        cx("cmd", "sw-aquarium-watch", "stop", timeout=60)
    txt = (watch.read_text() if watch.exists() else "") if MODE == "live" else FAKE.watch_text()
    (OUT / "sw-aquarium-watch.txt").write_text(txt)
    receipt("--- sw-aquarium-watch.txt ---\n" + txt[:4000])
    mk = re.search(r"wave makers (\d+)", txt); fr = re.search(r"wave fronts: in (\d+) samples, at most (\d+)", txt)
    fl = re.search(r"OceanWave\+SeaFoam flows: in (\d+) samples, at most (\d+)", txt)
    makers = int(mk.group(1)) if mk else None
    rec("t4.makers", "PASS" if makers and makers > 0 else "FAIL", f"wave makers on {FORT['ocean']}: {makers} (0 = no ocean on the map: the ocean tests have no subject)")
    rec("t4.fronts", "PASS" if fr and int(fr.group(1)) > 0 else "INFO",
        f"wave fronts in {fr and fr.group(1)} samples (at most {fr and fr.group(2)} at once); OceanWave/SeaFoam flows in {fl and fl.group(1)} samples (at most {fl and fl.group(2)}). "
        "None = DF does not spawn waves in graphics mode here: the surf (coastline points) carries the effect", data={"text": txt[:2000]})


def t5():
    if not ensure_fort(FORT["ocean"], why="(T5)"): return
    T = find_targets()
    if not T.get("surf"):
        rec("t5.surf", "FAIL", f"no wave front and no coastline point on {FORT['ocean']} (makers {T.get('makers')})"); return
    aq("on"); aq("waves", "on"); aq("surf", "on"); aq("foam", "on"); nap(0.6)
    on = capture_target("t5-waves-on", "surf", T["surf"], frames=max(8, ARGS.frames), unpause=True)
    aq("waves", "off"); nap(0.6)
    off = capture_target("t5-waves-off", "surf", T["surf"], frames=max(8, ARGS.frames), unpause=True)
    aq("waves", "auto")
    a1, a0 = on.get("anim_target"), off.get("anim_target")
    ok = a1 is not None and a1 >= ANIM_MIN and (a0 is None or a1 >= 1.5 * a0)
    rec("t5.waves_drawn", "PASS" if ok else "FAIL",
        f"surf/front cells at {T['surf']}: frame change with waves on {a1} v off {a0} (need >= {ANIM_MIN} and >= 1.5x off); control {on.get('anim_control')}",
        shots=[str(SHOTS / "t5-waves-on.gif"), on.get("boxes"), str(SHOTS / "t5-waves-off.gif")])
    st = status()
    rec("t5.status", "PASS" if "auto: ocean" in st or "on (" in st else "FAIL", st.strip()[:400])
    # auto on the lake map: no ocean, nothing drawn
    if ensure_fort(FORT["lake"], why="(T5 lake auto)"):
        st = status()
        rec("t5.lake_auto_off", "PASS" if status_facts(st)["auto_no_ocean"] else "FAIL", f"{FORT['lake']}: {st.strip()[:300]}")


def t6():
    if not ensure_fort(FORT["plain"], fresh=True, why="(T6)"): return
    aq("on"); aq("lens", "on"); aq("legend", "on")
    F = find_fish()
    b = F.get("best")
    if not b:
        rec("t6.fish", "FAIL", f"no creature below a visible water surface on {FORT['plain']}"); return
    fish = [(f[0], f[1]) for f in F["fish"] if f[3] == b["z"] and abs(f[0] - b["x"]) <= 6 and abs(f[1] - b["y"]) <= 6]
    nap(1.2)
    on = capture_target("t6-lens-on", "lake", [b["x"], b["y"], b["z"]], extra=fish)
    pr = aq("probe")
    m = re.search(r"(\d+) creatures below in view, (\d+) cells marked", pr)
    rows = [l for l in pr.splitlines() if re.match(r"\s{2}\S.*x\d+", l)]
    rec("t6.probe", "PASS" if m and int(m.group(1)) > 0 and rows else "FAIL", pr.strip()[:600])
    rc, scr, err = cx("screen", timeout=120)
    (OUT / "t6-screen.txt").write_text(scr)
    rec("t6.legend", "PASS" if "Below z" in scr else "FAIL", f"the legend panel {'is' if 'Below z' in scr else 'is NOT'} on screen ('Below z' in the screen text; t6-screen.txt)")
    aq("lens", "off"); nap(0.8)
    off = capture_target("t6-lens-off", "lake", [b["x"], b["y"], b["z"]], extra=fish)
    if on.get("frames") and off.get("frames"):
        G = on["geom"]
        dl = diff(Image.open(off["frames"][0]), Image.open(on["frames"][0]), G, fish)
        dc = diff(Image.open(off["frames"][0]), Image.open(on["frames"][0]), G, on["control"]) if on["control"] else None
        rec("t6.lens_marks", "PASS" if dl is not None and dl >= LENS_MIN and (dc is None or dc <= CONTROL_MAX) else "FAIL",
            f"fish cells lens on v off differ by {dl} (need >= {LENS_MIN}); dry land control {dc} (need <= {CONTROL_MAX}: no marks on dry land)",
            shots=[on.get("boxes"), off.get("boxes")])
    aq("lens", "on")


def t7():
    if not ensure_fort(FORT["plain"], why="(T7)"): return
    T = find_targets().get("lake")
    if not T:
        rec("t7.lake", "FAIL", f"no visible lake water on {FORT['plain']}"); return
    aq("on"); aq("lens", "off"); aq("waves", "off"); aq("veil", "off"); nap(0.6)
    off = capture_target("t7-veil-off", "lake", T)
    aq("veil", "on"); nap(1.5)
    on = capture_target("t7-veil-on", "lake", T)
    st = status(); f = status_facts(st)
    aq("veil", "off"); aq("lens", "on"); aq("waves", "auto")
    if off.get("frames") and on.get("frames"):
        G = on["geom"]
        dw = diff(Image.open(off["frames"][0]), Image.open(on["frames"][0]), G, on["water"])
        dc = diff(Image.open(off["frames"][0]), Image.open(on["frames"][0]), G, on["control"]) if on["control"] else None
        rec("t7.veil_draws", "PASS" if dw is not None and dw >= TRANS_MIN and (dc is None or dc <= CONTROL_MAX) else "FAIL",
            f"veil on v off: lake cells differ by {dw} (need >= {TRANS_MIN}), dry control {dc}; look at t7-veil-on-boxes.png for the shore edges",
            shots=[off.get("boxes"), on.get("boxes")])
    rec("t7.veil_running", "FAIL" if any(k == "veil" for k, _ in f["stopped"]) else "PASS", f"status stopped layers {f['stopped']}; paint avgs {f['paint_avgs']}")


def ticks_now():
    g = geom() or {}
    return g.get("tick")


def t8():
    if not ensure_fort(FORT["ocean"], fresh=True, why="(T8)"): return
    T = find_targets()
    tgt = T.get("ocean") or T.get("surf")
    if tgt: centre(tgt[0], tgt[1], tgt[2])
    arms = {"off": [("off",)], "on": [("on",), ("lens", "on"), ("waves", "on"), ("veil", "off")], "veil": [("on",), ("veil", "on")]}
    rates = {k: [] for k in arms}
    order = list(arms)
    for r in range(ARGS.perf_reps):
        for k in order[r % 3:] + order[:r % 3]:
            for w in arms[k]: aq(*w)
            t0 = ticks_now(); cx("unpause"); w0 = time.time()
            nap(ARGS.perf_secs)
            cx("pause"); w1 = time.time(); t1 = ticks_now()
            if MODE != "live": t0, t1, w1 = 0, int(ARGS.perf_secs * {"off": 100, "on": 99.6, "veil": 92}[k]), w0 + ARGS.perf_secs
            if t0 is not None and t1 is not None:
                dt = (t1 - t0) % 403200
                rates[k].append(round(dt / max(0.1, w1 - w0), 2))
    st = status(); f = status_facts(st)
    aq("veil", "off"); aq("waves", "auto")
    mean = {k: round(float(np.mean(v)), 2) if v else None for k, v in rates.items()}
    se = {k: round(float(np.std(v) / math.sqrt(len(v))), 2) if len(v) > 1 else None for k, v in rates.items()}
    cost = round(100 * (1 - mean["on"] / mean["off"]), 2) if mean["on"] and mean["off"] else None
    noise = round(100 * 2 * math.hypot(se["on"] or 0, se["off"] or 0) / mean["off"], 2) if mean["off"] else None
    rec("t8.cost_lens_waves", "PASS" if cost is not None and cost <= max(1.0, noise or 0) else "FAIL",
        f"ticks/s by stopwatch ({ARGS.perf_reps} reps x {ARGS.perf_secs}s, interleaved): off {mean['off']} (se {se['off']}), on {mean['on']} (se {se['on']}): "
        f"cost {cost}% (need <= 1% or within 2 se = {noise}%)", data={"rates": rates})
    rec("t8.cost_veil", "INFO", f"veil arm {mean['veil']} ticks/s (se {se['veil']}) = {round(100 * (1 - mean['veil'] / mean['off']), 2) if mean['veil'] and mean['off'] else None}% below off")
    pa = f["paint_avgs"]
    rec("t8.paint", "PASS" if pa and max(pa) < 1.0 and not f["stopped"] else "FAIL", f"status paint avg ms per layer {pa} (need < 1 ms), stopped {f['stopped']}")


def t9():
    if not ensure_fort(FORT["lake"], why="(T9)"): return
    T = find_targets().get("lake")
    if T: centre(T[0], T[1], T[2])
    logf = REAL_DF / "stderr.log"
    m0 = logf.stat().st_size if (MODE == "live" and logf.exists()) else 0
    for w in (("on",), ("lens", "on"), ("waves", "on"), ("veil", "on"), ("marks", "3000"), ("hz", "10"), ("budget", "1"), ("trip", "5")): aq(*w)
    cx("unpause"); nap(8); cx("pause")
    st = status(); f = status_facts(st)
    new = ""
    if MODE == "live" and logf.exists():
        with open(logf, "rb") as fh: fh.seek(m0); new = fh.read().decode("latin-1", "replace")
    lines = [l for l in new.splitlines() if "aquarium" in l.lower()]
    if f["stopped"]:
        rec("t9.fuse_trips", "PASS" if 1 <= len(lines) <= 3 or MODE != "live" else "FAIL",
            f"stopped {f['stopped']}; console lines about it {len(lines)} (need one per tripped layer): {lines[:4]}")
    else:
        rec("t9.fuse_trips", "NOT-TESTABLE" if f["paint_avgs"] and max(f["paint_avgs"]) < 1.0 else "FAIL",
            f"no layer stopped with budget 1 ms / trip 5; paint avgs {f['paint_avgs']} ms (under 1 ms the fuse cannot be provoked on this view)")
    aq("rearm"); nap(1)
    st2 = status()
    rec("t9.rearm", "PASS" if not status_facts(st2)["stopped"] else "FAIL", f"after rearm: stopped {status_facts(st2)['stopped']}")
    for w in (("budget", "2"), ("trip", "30"), ("marks", "400"), ("hz", "4"), ("veil", "off"), ("waves", "auto")): aq(*w)


def http_get(path, timeout=20):
    try:
        c = http.client.HTTPConnection("127.0.0.1", WPORT, timeout=timeout)
        c.request("GET", path, headers={"Host": f"127.0.0.1:{WPORT}"})
        r = c.getresponse(); b = r.read(); c.close()
        return r.status, b
    except Exception as e:
        return 0, str(e).encode()


def t10():
    if not ensure_fort(FORT["lake"], why="(T10)"): return
    trips = [(("depth", "6"), r"depth 6"), (("color", "kind"), r"colour kind"), (("lens", "off"), r"lens\s+off"), (("schools", "off"), r"schools off"),
             (("rows", "5"), r"\(5 rows\)"), (("waves", "off"), r"waves\s+off"), (("budget", "3"), r"budget 3 ms")]
    bad = []
    for w, rx in trips:
        aq(*w)
        if not re.search(rx, status()): bad.append(" ".join(w))
    for w in (("depth", "4"), ("color", "level"), ("lens", "on"), ("schools", "on"), ("rows", "8"), ("waves", "auto"), ("budget", "2")): aq(*w)
    rec("t10.verbs", "PASS" if not bad else "FAIL", f"{len(trips)} console set/read-back round trips through `aquarium status`; failed: {bad}")
    if MODE == "live":
        cx("cmd", "seasonal-wildlife-web", "stop", timeout=60)
        rc, out, err = cx("cmd", "seasonal-wildlife-web", "start", str(WPORT), timeout=90)
        m = re.search(r"\?t=([0-9a-f]+)", out); tok = m.group(1) if m else ""
        code, b = http_get(f"/controls.json?t={tok}")
        n = 0
        try:
            j = json.loads(b); secs = j.get("sections") or j.get("controls") or j
            txt = json.dumps(secs); n = len(re.findall(r'"aquarium\.[a-z_]+"', txt))
        except Exception:
            pass
        code2, b2 = http_get(f"/set?id=aquarium.depth&v=5&t={tok}")
        st = status()
        rec("t10.registry", "PASS" if code == 200 and n >= 17 and "depth 5" in st else "FAIL",
            f"/controls.json {code}: {n} aquarium ids (need 17); /set aquarium.depth=5 -> {code2}, status depth 5: {'depth 5' in st}")
        aq("depth", "4"); cx("cmd", "seasonal-wildlife-web", "stop", timeout=60)
    else:
        rec("t10.registry", "NOT-TESTABLE", "dry run: the web registry round trip needs the live server")
    cx("cmd", "gui/seasonal-wildlife", timeout=60); nap(1.5)
    p = shot("t10-panel", geom())
    rc, scr, err = cx("screen", timeout=120)
    (OUT / "t10-screen.txt").write_text(scr)
    cx("key", "LEAVESCREEN")
    rec("t10.panel", "INFO", f"the Panel opened; 'Aquarium' {'is' if 'Aquarium' in scr else 'is not'} in the screen text (the section may be on another page: look at t10-panel.png)", shots=[p])
    aq("restore", timeout=180)
    v = {c.name: stamp(c).get("preset") for c in installed_copies()}
    ok1 = stamp(mod_dir()).get("preset") == "vanilla" and all(x == "vanilla" for x in v.values())
    set_preset("aquarium")
    v2 = {c.name: stamp(c).get("preset") for c in installed_copies()}
    rec("t10.actions", "PASS" if ok1 and stamp(mod_dir()).get("preset") == "aquarium" else "FAIL",
        f"restore -> mods/ + installed copies vanilla: {ok1} ({v}); install aquarium -> {stamp(mod_dir()).get('preset')} {v2}")


def t11():
    if not ensure_fort(FORT["lake"], why="(T11)"): return
    out = aq("uninstall")
    kept = (mod_dir() / "info.txt").is_file() or MODE != "live"
    rec("t11.uninstall_guard", "PASS" if "this world uses the Aquarium mod" in out and kept else "FAIL", f"{out.strip()[:300]}; mod folder kept {kept}")


def restore_cfg():
    """The aquarium config back to its defaults (the tool keeps it per fort, and the fort is quit unsaved, but the engine's
    shared cache can outlive a load in one DF process)."""
    for w in (("on",), ("lens", "on"), ("legend", "on"), ("schools", "on"), ("waves", "auto"), ("surf", "on"), ("foam", "on"), ("veil", "off"),
              ("depth", "4"), ("color", "level"), ("rows", "8"), ("budget", "2"), ("trip", "30"), ("marks", "400"), ("hz", "4")):
        aq(*w)


def view_mode():
    """--view: centre on a named target on the loaded map (or --fort, restored and loaded) and capture a burst."""
    if ARGS.fort and not load_fort(ARGS.fort, "(--view)"): return 2
    if state().get("map") != "true":
        rec("view.map", "FAIL", "no map loaded (pass --fort NAME)"); return 2
    kind = ARGS.view
    if kind == "fish":
        F = find_fish(); b = F.get("best")
        T = [b["x"], b["y"], b["z"]] if b else None
    else:
        TT = find_targets(); T = TT.get(kind)
        base = TT.get("river") or TT.get("lake") or TT.get("brook") or TT.get("ocean")
        if kind == "mist" and not T and base and not ARGS.no_spawn:   # no waterfall mist here: spawn a Mist + Steam pair
            S, raw = spawn_mist(base)
            if MODE != "live": FAKE.spawned = S
            T = S.get("Mist") or S.get("Steam") or None
            log(f"  no natural mist: spawned {S} ({raw[-120:]})")
    if not T:
        rec(f"view.{kind}", "FAIL", f"no {kind} target on this map"); return 1
    st = status()
    cap = capture_target(f"view-{kind}", kind, T, frames=ARGS.frames, unpause=not ARGS.paused)
    (OUT / "view.json").write_text(json.dumps(cap, indent=1, default=str))
    rec(f"view.{kind}", "PASS" if cap.get("frames") else "FAIL",
        f"{kind} at {T}: view {cap['geom'].get('wx')},{cap['geom'].get('wy')},{cap['geom'].get('wz')}; {len(cap.get('frames') or [])} frames; "
        f"frame change target {cap.get('anim_target')} control {cap.get('anim_control')}; stats {cap.get('stats_target')}; {status_facts(st)}",
        shots=[str(SHOTS / f"view-{kind}.gif"), cap.get("boxes")])
    return 0


# ------------------------------------------------------------------------------------------------ dry-run fake rig
class Fake:
    """A stand-in for the rig: plausible cx-lifecycle replies and synthetic frames drawn from a toy map, so every path of
    the driver (receipts, centring, cells, pixel checks, GIFs, rows) runs without DF. Its numbers prove plumbing only."""
    def __init__(self, out):
        self.t, self.map, self.fort, self.paused = 0.0, False, None, True
        self.disk, self.loaded = "aquarium", "aquarium"
        self.cfg = {"enabled": True, "lens": True, "waves": "auto", "veil": False, "foam": True, "surf": True, "depth": 4, "color": "level",
                    "schools": True, "rows": 8, "budget": 2}
        self.win = (0, 0, 150); self.spawned = {}; self.out = out; self.screen = None
        self.dim = (60, 34)


    def kind(self, x, y, z):   # the toy map: lake disk, a river row, an ocean south (AQUA_SHORE), land elsewhere
        if (x - 192) ** 2 + (y - 192) ** 2 <= 18 ** 2: return "lake"
        if 118 <= y <= 121 and 90 <= x <= 300: return "river"
        if self.fort == FORT["ocean"] and y >= 250: return "ocean"
        if self.fort == FORT["ocean"] and y == 249: return "coast"
        return "land"

    def reply(self, a):
        v = a[0]
        if v == "state":
            scr = self.screen or ('viewscreen_dwarfmodest' if self.map else 'viewscreen_titlest')
            return 0, (f"screen={scr} focus=dwarfmode/Default world={str(self.map).lower()} "
                       f"map={str(self.map).lower()} paused={str(self.paused).lower()} titlemode=MAIN_MENU year=100 tick=1000\n"), ""
        if v == "title": self.map = False; self.screen = None; return 0, "", "[cx-lifecycle] back at the title screen\n"
        if v == "load":
            cp = installed_copies()
            self.map, self.fort, self.spawned, self.screen = True, a[1], {}, None
            self.loaded = "vanilla" if a[1] == FORT["plain"] else (stamp(cp[0]).get("preset") if cp else self.disk)
            return 0, "", "[cx-lifecycle] loaded after 30s\n"
        if v == "ui" and len(a) > 2 and a[1] in ("click", "clicklast"):
            t = a[2]
            if t.startswith("World:"): self.screen = "viewscreen_choose_game_typest"
            elif t == "Fortress": self.screen = "viewscreen_choose_start_sitest"
            elif t == "Confirm": self.screen = "viewscreen_setupdwarfgamest"
            elif t == "Play now!": self.map, self.fort, self.screen = True, FORT["ocean"], None
            return 0, f"clicked {t}\n", ""
        if v == "key" and a[1:] == ["LEAVESCREEN"]: self.screen = None; return 0, "", ""
        if v in ("pause", "unpause"): self.paused = v == "pause"; return 0, f"{v}d\n", ""
        if v == "cmd" and a[1] == "seasonal-wildlife" and len(a) > 2 and a[2] == "aquarium":
            return 0, self.aq(a[3:]), ""
        if v == "cmd" and a[1] == "seasonal-wildlife-web":
            return 0, "web server on 127.0.0.1:8643 http://127.0.0.1:8643/?t=0123abcd\n", ""
        if v == "cmd" and a[1] == "sw-aquarium-watch":
            return 0, "sw-aquarium-watch: sampling every 100 ticks for 6000 ticks; unpause. 3 wave makers on this map.\n", ""
        if v == "cmd" and a[1] == "cx-embark":
            w = a[2]
            if w == "worlds": return 0, "region9\tCamade Mare\nregion10\tCamade Mare\n", ""
            if w == "read": return 0, f"mm_min=3285,2733 mm_max=3290,2738 region=205,170 choosing=true zoomed=true zoom_cent=3288,2728 confirm=false\n", ""
            if w == "place": self.screen = "viewscreen_setupdwarfgamest"; return 0, f"placed {a[3]},{a[4]}..x warn=0,0..0,0\n", ""
            if w == "site": return 0, f"site mm_min={SHORE['rx'] * 16 + SHORE['ox']},{SHORE['ry'] * 16 + SHORE['oy']} mm_max=0,0\n", ""
            return 0, "ok\n", ""
        if v == "lua": return 0, self.lua(a[1]), ""
        if v == "screen": return 0, "Below z: 6 swimmers in 2 species, 1 schools, to -2\n Aquarium\n", ""
        return 0, f"(fake) {' '.join(a)[:80]}\n", ""

    def aq(self, w):
        w = list(w) or ["status"]
        if w[0] == "status":
            st = {"preset": stamp(mod_dir()).get("preset", self.disk)}
            return ("aquarium: on; lens on (depth 4, level colours), legend on, waves auto, veil off; mod preset aquarium\n"
                    f"aquarium: {'on' if self.cfg['enabled'] else 'OFF'}; graphics mode yes; DF shows 1 lower level(s) (Settings: lower elevations shown)\n"
                    f"  lens   {'on' if self.cfg['lens'] else 'off'}  depth {self.cfg['depth']}, fade 0.70, colour {self.cfg['color']}, schools {'on' if self.cfg['schools'] else 'off'}, legend on ({self.cfg['rows']} rows)\n"
                    "         frames 120, paint avg 0.21 ms, worst 1 ms; scans 30, last 1 ms (worst 2), 12 marks; ok\n"
                    f"  waves  {self.cfg['waves'] if self.cfg['waves'] == 'off' else 'on'}  {'auto: ocean (3 wave makers)' if self.fort == FORT['ocean'] else 'auto: no ocean on this map'}; surf on, foam on\n"
                    f"  veil   {'on' if self.cfg['veil'] else 'off'}  (experimental run-time translucency)\n"
                    f"  budget {self.cfg['budget']} ms a frame, fuse after 30 frames over, 400 marks at most, 4 scans a second\n"
                    f"  mod: installed at /fake/mods/{MOD_ID}, preset {st['preset']} (alpha x), by lua (in game); ACTIVE in this world\n"
                    f"  this world loaded /fake/data/installed_mods/{MOD_ID} (1): preset {self.loaded} (alpha x)\n")
        if w[0] in ("install", "restore"):
            p = "vanilla" if w[0] == "restore" else (w[1] if len(w) > 1 else "aquarium")
            self.disk = p
            for d in [mod_dir()] + installed_copies():
                d.mkdir(parents=True, exist_ok=True)
                (d / "sw_aquarium_stamp.txt").write_text(f"mod={MOD_ID}\npreset={p}\n")
            return f"Aquarium mod written: /fake/mods/{MOD_ID}\n  preset {p} ..., 10 files in 2.1 s\n  refreshed the copy worlds made with the mod load: /fake/data/installed_mods/{MOD_ID} (1) (10 files)\n"
        if w[0] == "uninstall": return "this world uses the Aquarium mod: removing it would stop the world loading. Use `aquarium restore`...\n"
        if w[0] == "probe":
            return ("waves: 3 wave makers (120 coastline points), 0 wave fronts []; flows on the map (900 blocks): OceanWave 0, SeaFoam 0, waterfall Mist 0\n"
                    "lens at z 150, depth 4: 6 creatures below in view, 6 cells marked, 1 school brackets\n  tigerfish                x6   -1..-2   school led             native\n")
        if w[0] in ("on", "off"): self.cfg["enabled"] = w[0] == "on"; return f"aquarium overlays: {w[0] == 'on'}\n"
        if w[0] == "rearm": return "re-armed 0 stopped aquarium layer(s)\n"
        if len(w) > 1:
            k = {"rows": "rows"}.get(w[0], w[0])
            val = w[1]
            self.cfg[k] = (val == "on") if val in ("on", "off") and k not in ("waves",) else (int(val) if val.isdigit() else val)
            return f"aquarium {w[0]}: {val}\n"
        return "usage\n"

    def lua(self, code):
        tag = re.search(r"-- AQ:(\w+)", code).group(1)
        if tag in ("geom", "centre"):
            if tag == "centre":
                m = re.search(r"revealInDwarfmodeMap\((-?\d+), (-?\d+), (-?\d+)", code)
                x, y, z = int(m.group(1)), int(m.group(2)), int(m.group(3))
                self.win = (x - self.dim[0] // 2, y - self.dim[1] // 2, z)
            r = {"wx": self.win[0], "wy": self.win[1], "wz": self.win[2], "dim_x": self.dim[0], "dim_y": self.dim[1], "spx": 1920, "spy": 1088,
                 "zoom": 64, "gm": True, "lower": 1, "paused": self.paused, "tick": 1000, "mx": 384, "my": 384, "mz": 200}
        elif tag == "find":
            cols = []
            for x in range(2, 384, 4):
                for y in range(2, 384, 4):
                    k = self.kind(x, y, 150)
                    if k == "lake": cols.append([x, y, 150, 3, 0, 0, 0, 7])
                    elif k == "river": cols.append([x, y, 150, 1, 0, 2, 0, 4])
                    elif k == "ocean": cols.append([x, y, 150, 5, 1, 0, 0, 7])
            r = {"W": 384, "H": 384, "Z": 200, "stride": 4, "cols": cols, "flows": [], "flow_counts": {"Miasma": 2}, "fronts": [],
                 "coast": [[x, 249, 150] for x in range(60, 330, 3)] if self.fort == FORT["ocean"] else [], "makers": 3 if self.fort == FORT["ocean"] else 0}
        elif tag == "cells":
            m = re.search(r"local x0, y0, z, R = (\d+), (\d+), (\d+), (\d+)", code)
            x0, y0, z, R = (int(m.group(i)) for i in range(1, 5))
            ch = {"lake": "7", "river": "4", "ocean": "7", "coast": "l", "land": "l"}
            r = {"x0": x0 - R, "y0": y0 - R, "z": z, "rows": ["".join(ch[self.kind(x, y, z)] for x in range(x0 - R, x0 + R + 1)) for y in range(y0 - R, y0 + R + 1)]}
        elif tag == "spawn":
            m = re.search(r"xyz2pos\((\d+) \+ dx, (\d+), (\d+)\)", code)
            x, y, z = int(m.group(1)), int(m.group(2)), int(m.group(3))
            r = {"Mist": [x - 2, y, z], "Steam": [x + 2, y, z]}
        elif tag == "fish":
            r = {"best": {"n": 6, "x": 190, "y": 190, "z": 150}, "n": 6, "fish": [[188 + i, 190, 148 + (i % 2), 150, "FISH_TIGERFISH", 100 + i] for i in range(6)]}
        elif tag == "worldid":
            r = {"mods": ["vanilla_text", MOD_ID], "sites": 1527, "save_dir": "region10"}
        else:
            r = {}
        return "AQJ " + json.dumps(r) + "\n"

    def watch_text(self):
        return ("sw-aquarium-watch: 61 samples every 100 ticks; graphics mode true; wave makers 3\n  wave fronts: in 12 samples, at most 2 at once, 5 front-samples with spawn_flows set\n"
                "  OceanWave+SeaFoam flows: in 9 samples, at most 14 at once\n")

    def render(self, G):
        """A toy DF frame: 32 px cells under a 28 px title bar; water = blue over a striped bed at the preset's alpha."""
        alpha = {"vanilla": 255, "subtle": 205, "aquarium": 140, "clear": 95, "shallows": 255}.get(self.loaded, 140)
        if self.fort == FORT["plain"] and self.cfg.get("veil") and self.cfg.get("enabled"): alpha = 140
        W, H = 1920, 1088 + 28
        im = Image.new("RGB", (W, H), (60, 60, 60)); d = ImageDraw.Draw(im)
        wx, wy, wz = self.win
        f = int(self.t / 0.25)
        fish = {(188 + i, 190) for i in range(6)}
        for j in range(self.dim[1]):
            for i in range(self.dim[0]):
                x, y = wx + i, wy + j
                k = self.kind(x, y, wz)
                x0, y0 = i * 32, 28 + j * 32
                if k in ("land", "coast"):
                    c = (90 + (x * 7 + y * 3) % 20, 120 + (x * 5) % 15, 60)
                    d.rectangle([x0, y0, x0 + 31, y0 + 31], fill=c)
                    continue
                bed = (150, 130, 90) if (x + y) % 3 else (110, 95, 70)
                a = alpha / 255.0 if k != "river" else min(1.0, alpha / 255.0 * 0.9)
                if k == "ocean" and self.loaded == "shallows": a = 1.0
                water = (30, 80, 150)
                c = tuple(int(bed[n] * (1 - a) + water[n] * a) for n in range(3))
                d.rectangle([x0, y0, x0 + 31, y0 + 31], fill=c)
                if k == "river":
                    s = (f * 6 + x * 5) % 32
                    d.line([x0 + s, y0 + 4, x0 + s, y0 + 28], fill=(int(c[0] + 25), int(c[1] + 25), int(c[2] + 25)), width=2)
                if (x, y) in fish:
                    if alpha < 200: d.ellipse([x0 + 8, y0 + 12, x0 + 24, y0 + 20], fill=tuple(int(v * 0.7) for v in c))
                    if self.cfg.get("enabled") and self.cfg.get("lens"): d.ellipse([x0 + 6, y0 + 10, x0 + 26, y0 + 22], fill=(40, 200, 190))
                if self.cfg.get("enabled") and self.cfg.get("waves") != "off" and self.fort == FORT["ocean"] and y == 250:
                    s = (f * 5 + x * 3) % 32
                    d.line([x0, y0 + s, x0 + 31, y0 + s], fill=(235, 245, 255), width=3)
        for k_, v in (self.spawned or {}).items():
            if v and k_ == "Mist":
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        x0, y0 = (v[0] + dx - wx) * 32, 28 + (v[1] + dy - wy) * 32
                        r = 8 + (f * 3 + dx * 5) % 10
                        d.ellipse([x0 + 16 - r, y0 + 16 - r, x0 + 16 + r, y0 + 16 + r], fill=(225, 235, 245))
                        if self.cfg.get("enabled") and self.cfg.get("foam"):   # the overlay's foam specks on mist cells
                            for q in range(10):
                                sx, sy = x0 + (f * 7 + q * 9) % 30, y0 + (f * 5 + q * 13) % 30
                                d.rectangle([sx, sy, sx + 4, sy + 4], fill=(40, 40, 60))
        return im


# ------------------------------------------------------------------------------------------------ main
def finish(code):
    fails = [r for r in RESULTS if r["verdict"] == "FAIL"]
    counts = {v: sum(1 for r in RESULTS if r["verdict"] == v) for v in ("PASS", "FAIL", "NOT-TESTABLE", "INFO")}
    json.dump({"run": RUN, "mode": MODE, "args": vars(ARGS), "thresholds": {"TRANS_MIN": TRANS_MIN, "CONTROL_MAX": CONTROL_MAX, "ANIM_MIN": ANIM_MIN,
               "MIST_MIN": MIST_MIN, "LENS_MIN": LENS_MIN}, "counts": counts, "rows": RESULTS}, open(OUT / "results.json", "w"), indent=1, default=str)
    with open(OUT / "report.md", "w") as f:
        f.write(f"# Aquarium rig run {RUN} ({MODE})\n\n{counts}\n\nTool: {ARGS.tool_src}. Receipts per stage in `receipts/`, frames in `shots/` "
                f"(`*-boxes.png`: red = measured target cells, yellow = dry control cells; `*.gif`, `*-sheet.png` = bursts).\n\n"
                "| row | verdict | evidence | shots |\n|---|---|---|---|\n")
        for r in RESULTS:
            sh_ = ", ".join(f"[{Path(s).name}]({s})" for s in (r.get("shots") or []) if s and s != "None")
            f.write(f"| {r['id']} | {r['verdict']} | {r['evidence'].replace('|', '/')[:600]} | {sh_} |\n")
        if fails:
            f.write("\n## FAILs first\n\n" + "\n".join(f"- **{r['id']}**: {r['evidence'][:400]} (receipts: {r['receipts']})" for r in fails) + "\n")
    log(f"== {counts}; {OUT}")
    return code if code else (1 if fails else 0)


def main():
    global MODE, OUT, SHOTS, LOG, ARGS, FAKE, STAGE, DF_DIR, USER_DIR
    ap = argparse.ArgumentParser(description="Aquarium rig test driver (docs/v7.1/aquarium.md section 9)")
    ap.add_argument("--tool-src", default=str(Path.home() / "Claude/Projects/sw-wt/rc"))
    ap.add_argument("--only"); ap.add_argument("--skip")
    ap.add_argument("--deploy", action="store_true"); ap.add_argument("--embark-shore", action="store_true")
    ap.add_argument("--presets", default="vanilla,aquarium,clear"); ap.add_argument("--t2-presets", default="aquarium,clear")
    ap.add_argument("--t3-presets", default="vanilla,aquarium,shallows")
    ap.add_argument("--frames", type=int, default=6); ap.add_argument("--gap", type=float, default=0.25)
    ap.add_argument("--fish"); ap.add_argument("--no-spawn", action="store_true"); ap.add_argument("--restart-escalate", action="store_true")
    ap.add_argument("--perf-reps", type=int, default=5); ap.add_argument("--perf-secs", type=float, default=10)
    ap.add_argument("--view", choices=["lake", "river", "brook", "mist", "surf", "ocean", "fish"]); ap.add_argument("--fort")
    ap.add_argument("--paused", action="store_true", help="--view: capture without unpausing")
    ap.add_argument("--dry-run", action="store_true")
    ARGS = ap.parse_args()
    if ARGS.dry_run:
        MODE = "dry"; OUT = OUT.with_name(RUN + ("-view" if ARGS.view else "") + "-dry")
        # dry runs never write the rig: the mutable mod folders are scratch copies of the real ones
        USER_DIR = OUT / "fake_user"; DF_DIR = OUT / "fake_df"
        for src, dst in [(REAL_USER / "mods" / MOD_ID, USER_DIR / "mods" / MOD_ID)] + [(c, USER_DIR / "data/installed_mods" / c.name) for c in installed_copies(REAL_USER)]:
            if src.is_dir(): shutil.copytree(src, dst)
        (DF_DIR / "dfhack-config/scripts").mkdir(parents=True, exist_ok=True)
        for f in ("seasonal-wildlife-aquarium.lua", "seasonal-wildlife-aquarium-gfx.lua", "seasonal-wildlife.lua", "seasonal-wildlife-controls.lua", "sw-aquarium-watch.lua"):
            if (REAL_DF / "dfhack-config/scripts" / f).is_file(): shutil.copy2(REAL_DF / "dfhack-config/scripts" / f, DF_DIR / "dfhack-config/scripts" / f)
    elif ARGS.view:
        OUT = OUT.with_name(RUN + "-view")
    SHOTS = OUT / "shots"
    OUT.mkdir(parents=True, exist_ok=True); SHOTS.mkdir(exist_ok=True)
    LOG = open(OUT / "log.txt", "w")
    FAKE = Fake(OUT) if MODE == "dry" else None
    head = subprocess.run(["git", "-C", ARGS.tool_src, "log", "--oneline", "-1"], capture_output=True, text=True).stdout.strip()
    log(f"aquarium-run {RUN}: mode {MODE}, tool {ARGS.tool_src} ({head}), DF {REAL_DF}")
    if ARGS.view:
        STAGE = "view"
        return finish(view_mode())
    stages = [s.strip() for s in ARGS.only.split(",")] if ARGS.only else list(STAGES)
    only_mist = "mist" in stages and "t1" not in stages
    if only_mist: stages = [s if s != "mist" else "t1" for s in stages]
    if ARGS.skip: stages = [s for s in stages if s not in [x.strip() for x in ARGS.skip.split(",")]]
    unknown = [s for s in stages if s not in STAGES]
    if unknown:
        print(f"unknown stage(s) {unknown}; stages: {', '.join(STAGES)} (+ mist)"); return 2
    if MODE == "live":
        st = state()
        if not st:
            STAGE = "setup"; rec("session.rig", "FAIL", "cx-lifecycle state answered nothing: is DF running (cx-lifecycle.sh start)?")
            return finish(2)
        log(f"rig state: {st}")
    fn = {"setup": st_setup, "shore": st_shore, "t1": lambda: t1_arms(only_mist), "t2": t2, "t3": t3, "t4": t4, "t5": t5, "t6": t6, "t7": t7,
          "t8": t8, "t9": t9, "t10": t10, "t11": t11}
    for s in [x for x in STAGES if x in stages]:
        STAGE = s
        log(f"=== stage {s}")
        try:
            fn[s]()
        except Exception as e:   # a driver bug must fail its stage loudly, not end the run
            import traceback
            rec(f"{s}.driver_error", "FAIL", f"{type(e).__name__}: {e}", data=traceback.format_exc()[-1500:])
    STAGE = "end"
    if state().get("map") == "true":
        restore_cfg(); cx("pause")
        if MODE == "live": cx("title", timeout=240)
    return finish(0)


if __name__ == "__main__":
    sys.exit(main())
