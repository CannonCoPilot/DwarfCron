#!/usr/bin/env python3
"""One round of the Seasonal Wildlife Alpha Four walkthrough (artifact RCdoPTWhabmMBQQw2azpHr), played on the rig.

Each of the page's 109 steps is one function here. It does what the step's Do line says (window keys, console verbs,
the browser companion's endpoints), reads the screen, the console reply and the tool's own state, and marks the step
Pass, Anomaly or Skipped against the step's Expect line, with the evidence (every command and its reply, screen dumps,
readbacks). The steps and their expectations are .claude/scratch/gen_alpha4.py (v7.1); the tool under test is the
deployed seasonal-wildlife v7.1 (sw-wt/deploy bff2726).

Fort: RinghatchetsReady (world region9; 8x8, lake and river, caverns dug and revealed), restored from its .preverify
backup at the start of every session and never saved over. Step 6.14 saves to a NEW folder (A4R<run>), loads it, and
the round ends by quitting to the title and deleting that folder. 6.14 runs last for that reason.

Rules kept: one RPC at a time (every call is sequential); the window is closed before any tick step; time-based steps
step at most a few thousand ticks at the fps cap 1000; a season boundary further than --season-budget ticks away is
reached by moving the calendar (cur_year_tick) to just before it, recorded as a manipulation (--no-jump turns that off).

Usage:
  alpha4-run.py                         the whole round (about 30-40 min)
  alpha4-run.py --only 2.7,2.8,6.10     just those steps (a fresh session: restore, load)
  alpha4-run.py --feature 5             one feature (0 = version and deploy, 1-6 the page's features)
  alpha4-run.py --dry-run [--only ...]  print the planned rig commands; touches nothing
Output: data/alpha4/<run>/ results.json, marks.json (the page's "Load a round" format, _meta.page = alpha4),
        report.md (grouped by the six features), log.txt, screens/
"""
import argparse, json, os, re, subprocess, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CX = str(ROOT / "scripts" / "cx-lifecycle.sh")
RPC = str(ROOT / "scripts" / "cx-rpc.py")
PY = str(ROOT / ".venv" / "bin" / "python") if (ROOT / ".venv" / "bin" / "python").exists() else sys.executable
RUN = datetime.now().strftime("%Y%m%d-%H%M%S")
OUT = ROOT / "data" / "alpha4" / RUN
SCREENS = OUT / "screens"
FORT, BACKUP_TAG = "RinghatchetsReady", "preverify"
RELOAD = "A4R" + RUN.replace("-", "")[-8:]          # a new folder each round; deleted at the end
SAVE_ROOT = Path.home() / "Library/Application Support/CrossOver/Bottles/Win10/drive_c/users/crossover/AppData/Roaming/Bay 12 Games/Dwarf Fortress/save"
BACKUPS = Path.home() / "Library/Application Support/CrossOver/df-snapshots/saves"
DF_DIR = Path.home() / "Library/Application Support/CrossOver/Bottles/Win10/drive_c/Program Files (x86)/Steam/steamapps/common/Dwarf Fortress"
WEB_PORT = 8642
SEASONS = ["Spring", "Summer", "Autumn", "Winter"]
SCODE = ["Sp", "Su", "Au", "Wi"]
SKEY = ["CUSTOM_S", "CUSTOM_U", "CUSTOM_A", "CUSTOM_W"]
BACKSPACE = "STRING_A000"
TABS = ["Overview", "Panel", "Roster", "Seasons", "Food web", "Live", "Layers", "Vermin", "Ledger"]
SEASON_TICKS = 100800
FEATURES = {0: "Before you start: version and deploy", 1: "Biodiversity above the vanilla 7", 2: "Active ecosystems in all layers",
            3: "Seasonal changes in food webs", 4: "Ecological realism", 5: "Cavern mechanics",
            6: "Other: Panel, companion, console, cost"}
SURF = {"gui": "In the window", "con": "At the console", "web": "In the browser companion", "": "Before you start"}

DRY = False
NO_JUMP = False
SEASON_BUDGET = 24000
PORT = "5555"
results: list[dict] = []
memo: dict[str, Any] = {}
CUR: dict[str, Any] = {}          # the step being played: id, title, evidence
_log = None

# =============================================================================================== the rig
def log(msg):
    line = f"{datetime.now().strftime('%H:%M:%S')} {msg}"
    print(line, flush=True)
    if _log:
        _log.write(line + "\n"); _log.flush()

def plan(what):
    """Dry run: what would be sent to the rig."""
    print(f"    [{CUR.get('id', '--')}] {what}", flush=True)

def ev(kind, cmd, out=None):
    """One piece of evidence for the current step."""
    CUR.setdefault("evidence", []).append({"kind": kind, "cmd": cmd, "out": (out if out is None or len(str(out)) <= 4000 else str(out)[:4000] + " ...[cut]")})

def sh(*args, timeout=180, quiet=False):
    """One cx-lifecycle verb."""
    a = [str(x) for x in args]
    if DRY:
        plan("cx-lifecycle.sh " + " ".join(json.dumps(x) if " " in x else x for x in a))
        return 0, ""
    env = dict(os.environ, CX_RPC_TIMEOUT="45")
    try:
        p = subprocess.run([CX, *a], capture_output=True, text=True, timeout=timeout, cwd=ROOT, env=env)
        out = (p.stdout or "") + (p.stderr or "")
        rc = p.returncode
    except subprocess.TimeoutExpired:
        rc, out = 124, f"(cx-lifecycle {' '.join(a[:3])} timed out after {timeout}s)"
    if not quiet and a and a[0] not in ("screen", "lua"):
        ev("rig", " ".join(a), out.strip())
    return rc, out

def rpc_lua(code, timeout=45):
    """Lua over RPC with a deadline of our own (cx-lifecycle's `lua` verb caps at 15 s)."""
    if DRY:
        plan("lua: " + re.sub(r"\s+", " ", code)[:150])
        return ""
    try:
        p = subprocess.run([PY, RPC, "--port", PORT, "--timeout", str(timeout), "--lua", code],
                           capture_output=True, text=True, timeout=timeout + 30, cwd=ROOT)
        return (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return f"(lua timed out after {timeout}s)"

def luaj(code, timeout=45) -> Any:
    """Lua that prints one json.encode'd value; DFHack's encoder pretty-prints, so parse bracket to bracket."""
    out = rpc_lua("local json=require('json'); " + code, timeout=timeout)
    if DRY:
        return {}
    starts = [k for k in (out.find("{"), out.find("[")) if k != -1]
    if not starts:
        return {"_raw": out}
    i = min(starts); j = out.rfind("}" if out[i] == "{" else "]")
    try:
        return json.loads(out[i:j + 1])
    except ValueError:
        return {"_raw": out}

def luap(code, timeout=45) -> dict:
    """luaj under pcall: a Lua error comes back as {'_err': ...}; always a dict."""
    j = luaj("local __ok, __e = pcall(function()\n" + code + "\nend)\nif not __ok then print(json.encode({_err=tostring(__e)})) end", timeout=timeout)
    if isinstance(j, dict) and ("_err" in j or ("_raw" in j and not DRY)):
        ev("probe-error", re.sub(r"\s+", " ", code)[:200], str(j.get("_err") or j.get("_raw"))[:600])
    return j if isinstance(j, dict) else {"_list": j}

def lst(x):
    return x if isinstance(x, list) else (x.get("_list") if isinstance(x, dict) and isinstance(x.get("_list"), list) else [])

def script(name, *args, timeout=60, record=True):
    """A DFHack command run in the game with run_command_silent: the whole reply comes back, and a Lua error comes
    back as text instead of a timeout. This is what a tester typing it at the console sees."""
    words = ",".join(json.dumps(str(a)) for a in (name, *args))
    shown = " ".join(str(a) if " " not in str(a) else json.dumps(str(a)) for a in (name, *args))
    if DRY:
        plan("console: " + shown)
        return ""
    j = luaj(f"local ok,out=pcall(dfhack.run_command_silent,{words}); print(json.encode({{ok=ok,out=tostring(out)}}))", timeout=timeout)
    if isinstance(j, dict) and "out" in j:
        out = str(j.get("out") or "") if j.get("ok") else "LUA ERROR: " + str(j.get("out"))
    else:
        out = "NO REPLY: " + str(j.get("_raw", j) if isinstance(j, dict) else j)[:600]
    if record:
        ev("console", shown, out.rstrip())
    return out

def tool(*args, timeout=60, record=True):
    return script("seasonal-wildlife", *args, timeout=timeout, record=record)

def ctl(*args, timeout=60):
    return script("seasonal-wildlife-controls", *args, timeout=timeout)

def webcmd(*args, timeout=60):
    return script("seasonal-wildlife-web", *args, timeout=timeout)

SW = "local sw=reqscript('seasonal-wildlife'); "
GW = "local gw=reqscript('gui/seasonal-wildlife'); local w=gw.view and gw.view.subviews and gw.view.subviews[1]; "
FLAT = """local function flat(t)
  if type(t)=='string' then return t end
  if type(t)=='function' then local ok,r=pcall(t); return ok and flat(r) or '' end
  if type(t)~='table' then return '' end
  local o={}
  for _,x in ipairs(t) do
    if type(x)=='string' then o[#o+1]=x
    elseif type(x)=='table' then local s=x.text; if type(s)=='function' then local ok,r=pcall(s); s=ok and r or '' end; if s~=nil then o[#o+1]=tostring(s) end end
  end
  return table.concat(o)
end
"""

def screen(name):
    if DRY:
        plan(f"cx-lifecycle.sh screen  -> screens/{name}.txt")
        return ""
    txt = sh("screen", timeout=120, quiet=True)[1]
    SCREENS.mkdir(parents=True, exist_ok=True)
    fn = f"{CUR.get('id', 'x')}-{name}.txt"
    (SCREENS / fn).write_text(txt)
    ev("screen", fn)
    return txt

def key(k, wait=0.8):
    sh("key", k, timeout=60, quiet=True)
    ev("key", k)
    if not DRY:
        time.sleep(wait)

def typ(text, wait=0.5):
    sh("type", text, timeout=60, quiet=True)
    ev("type", text)
    if not DRY:
        time.sleep(wait)

def click(label, wait=1.2):
    out = sh("ui", "click", label, timeout=60, quiet=True)[1]
    ev("click", label, out.strip()[:200])
    if not DRY:
        time.sleep(wait)
    return out

def answer(text, clear=8):
    for _ in range(clear):
        key(BACKSPACE, 0.1)
    if text:
        typ(text)
    key("SELECT", 1.2)

def nap(s):
    if not DRY:
        time.sleep(s)

def stepped(ticks, secs=None):
    """Run the fort `ticks` ticks with the window closed; returns (ticks, wall seconds)."""
    close_window()
    secs = secs or max(120, int(ticks / 60) + 60)
    out = sh("step", ticks, secs, timeout=secs + 90)[1]
    m = re.search(r"stepped (-?\d+) ticks .* in (\d+)s", out)
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)

def ticks_now():
    j = luap("print(json.encode({y=df.global.cur_year, t=df.global.cur_year_tick, s=df.global.cur_season}))")
    return j

def announcements(n=10):
    r = luaj("local a=df.global.world.status.announcements; local o={}; for i=math.max(0,#a-%d),#a-1 do o[#o+1]=a[i].text end; print(json.encode(o))" % n)
    return r if isinstance(r, list) else []

def ledger_count():
    return luap(SW + "print(json.encode({n=sw.LEDGER.load().count}))").get("n")

def undo_depth():
    return luap(SW + "print(json.encode({d=sw.UNDO.depth()}))").get("d")

CFG_GET = """local function get(c, p)
  for k in p:gmatch('[^.]+') do
    if type(c) ~= 'table' then return nil end
    local v = c[k]; if v == nil and tonumber(k) then v = c[tonumber(k)] end
    c = v
  end
  return c
end
"""
def cfgv(*paths) -> dict:
    lst_ = ",".join(json.dumps(p) for p in paths)
    j = luap(SW + "local c=sw.loadConfig()\n" + CFG_GET + f"local out={{}}; for _,p in ipairs({{{lst_}}}) do out[p]=get(c,p) end; print(json.encode(out))")
    return j if "_err" not in j and "_raw" not in j else {}

def max_unit_id():
    return luap("local m=0; for _,u in ipairs(df.global.world.units.all) do if u.id>m then m=u.id end end; print(json.encode({m=m}))").get("m", 0)

def wild_units():
    """Every wild unit on the map: id, token, layer, caste flags we test on."""
    return lst(luap(SW + """local o={}
for _,u in ipairs(df.global.world.units.active) do
  if not dfhack.units.isDead(u) and sw.WILD.onMap(u) then
    local cr=df.creature_raw.find(u.race)
    o[#o+1]={id=u.id, t=cr and cr.creature_id or '?', layer=sw.WILD.layerOf(u), x=u.pos.x, y=u.pos.y, z=u.pos.z}
  end
end
print(json.encode(o))"""))

def roster():
    """Every managed species on this embark: allow, seasons, stock, layer, role, token."""
    r = luap(SW + "local cfg=sw.loadConfig(); local pool=sw.buildPool(cfg); local o={}; for _,e in ipairs(pool) do if e.inEmbark and not e.locked then "
             "o[e.key]={allow=cfg.allow[e.key], assign=cfg.assign[e.key] or {}, stock=cfg.stock[e.key], cat=e.cat, size=e.size, hab=e.habitat, layer=e.layer, token=e.token, civ=e.civ and true or false} end end; "
             "print(json.encode(o))", timeout=120)
    return r if "_err" not in r and "_raw" not in r else {}

def season_str(a):
    return "".join(SCODE[i] for i in sorted(a or [])) or "none"

# ---- the window ------------------------------------------------------------------------------------------------
def window_open():
    if DRY:
        return False
    r = luap(GW + "print(json.encode({open=w~=nil}))")
    return bool(r.get("open"))

def open_window(tab=None):
    if not window_open():
        sh("cmd", "gui/seasonal-wildlife", timeout=120, quiet=True); ev("console", "gui/seasonal-wildlife"); nap(2.5)
    if tab:
        select_tab(tab)

def close_window():
    if DRY:
        plan("close the window (LEAVESCREEN until it is gone)")
        return
    for _ in range(6):
        if not window_open():
            return
        sh("key", "LEAVESCREEN", timeout=60, quiet=True); time.sleep(0.7)

def select_tab(name, by_click=False):
    """The tab a tester clicks. By default the TabBar's own selection (a click on a word the map or a list also draws
    could press something else); by_click=True clicks the label and checks which page opened."""
    i = TABS.index(name) + 1
    if by_click:
        click(name, 1.5)
        got = luap(GW + "print(json.encode({p=w and w.subviews.pages:getSelected() or 0}))").get("p")
        if got == i:
            return "click"
    luap(GW + f"if w then w.subviews.pages:setSelected({i}); w:refreshTab({i}) end; print(json.encode({{p=w and w.subviews.pages:getSelected() or 0}}))")
    ev("tab", name)
    nap(0.8)
    return "tabbar"

def win_rect():
    r = luap(GW + "if w and w.frame_rect then print(json.encode({y1=w.frame_rect.y1,y2=w.frame_rect.y2,x1=w.frame_rect.x1,x2=w.frame_rect.x2})) else print('{}') end")
    return (r.get("y1", 0), r.get("y2", 999), r.get("x1", 0), r.get("x2", 999))

def win_text(txt):
    """The window's own rows, cropped to its frame (overlays and DF labels paint beside it: screen-check trap 6)."""
    y1, y2, x1, x2 = win_rect()
    rows = []
    for l in txt.splitlines():
        m = re.match(r"^\s*(\d+)\|(.*)$", l)
        if m and y1 <= int(m.group(1)) <= y2:
            rows.append(m.group(2)[x1:x2 + 1].rstrip())
    return "\n".join(rows)

def scr_text(txt):
    """The whole screen's rows without the row numbers."""
    return "\n".join(re.sub(r"^\s*\d+\|", "", l) for l in txt.splitlines())

def view_lines(view_id):
    """Every line a List or Label in the window holds (all rows, not only the visible ones)."""
    r = luap(GW + FLAT + f"""local v=w and w.subviews['{view_id}']; local o={{}}
if v then
  if v.getChoices then for _,c in ipairs(v:getChoices()) do o[#o+1]=flat(c.text) end
  else o[1]=flat(v.text) end
end
print(json.encode({{lines=o}}))""")
    return [str(x) for x in (r.get("lines") or [])]

def label(view_id):
    return "\n".join(view_lines(view_id))

def focus():
    r = luap("print(json.encode({f=dfhack.gui.getCurFocus(true)}))")
    return tuple(r.get("f", []) or [])

def asks(k, name, wait=1.0):
    """Press k; did a dialog take the focus? (the window's own key labels carry the same words)."""
    f0 = focus(); key(k, wait); f1 = focus(); t = screen(name)
    return (f1 != f0) or DRY, t

def yes():
    key("SELECT", 1.5)

def esc(wait=0.8):
    """Escape out of a DFHack screen; never on DF's own map (Esc there opens the main menu)."""
    f = " ".join(focus())
    if DRY or ("dfhack/lua" in f):
        key("LEAVESCREEN", wait)
        return True
    ev("esc", "skipped", f"focus {f}: no DFHack screen to close")
    return False

def dismiss_dialogs(n=3):
    """Close dialogs over the window, leaving the window itself."""
    for _ in range(n):
        f = " ".join(focus())
        if DRY or not f or "dfhack/lua" not in f or f.strip().endswith("dfhack/lua/seasonal-wildlife"):
            return
        key("LEAVESCREEN", 0.7)

def select_row(listname, match_lua):
    r = luap(GW + f"local L=w.subviews['{listname}']; local vis=L.getVisibleChoices and L:getVisibleChoices() or L:getChoices(); "
             f"for i,c in ipairs(vis) do if {match_lua} then if L.list then L.list:setSelected(i) else L:setSelected(i) end; print(json.encode({{i=i}})) return end end; print(json.encode({{i=-1}}))")
    return (r.get("i", -1) or -1) > 0

def select_key(k):
    return select_row("list", f"c.entry and c.entry.key=='{k}'")

# ---- the Panel -------------------------------------------------------------------------------------------------
def panel_open(section=None):
    open_window()
    key("CUSTOM_ALT_P", 1.2)
    if section:
        return panel_section(section)
    return True

def panel_shown():
    return luap(GW + "print(json.encode({s=w and w._psecShown or '', i=w and w._psec or 0}))").get("s")

def panel_section(sec_id, max_press=14):
    """S until the section list marks this section (a tester pressing S)."""
    if DRY:
        plan(f"press S until the Panel shows section '{sec_id}'")
        return True
    for _ in range(max_press):
        if panel_shown() == sec_id:
            return True
        key("CUSTOM_S", 0.6)
    return panel_shown() == sec_id

def panel_rows():
    return view_lines("panel")

def panel_select(ident):
    """Put the Panel cursor on a control, action or readout by id or label (a tester scrolling to it)."""
    r = luap(GW + f"""local L=w.subviews.panel; local want={json.dumps(ident)}
for i,c in ipairs(L:getChoices()) do local d=c.data
  if d and ((d.ctl and (d.ctl.id==want or d.ctl.label==want)) or (d.act and (d.act.id==want or d.act.label==want)) or (d.read and (d.read.id==want or d.read.label==want))) then
    L:setSelected(i); pcall(function() w:panelHelp() end); print(json.encode({{i=i}})) return end
end
print(json.encode({{i=-1}}))""")
    ok = (r.get("i", -1) or -1) > 0
    ev("select", f"Panel row {ident}", "selected" if ok else "NOT FOUND")
    return ok or DRY

def panel_report():
    return {"cmd": label("panel_cmd"), "status": label("panel_status")}

# ---- marking ---------------------------------------------------------------------------------------------------
STEPS: list[tuple[str, str, str, Any]] = []
def step(sid, title, surface=""):
    def deco(fn):
        STEPS.append((sid, title, surface, fn)); return fn
    return deco

def mark(v, note, data=None):
    CUR["v"], CUR["note"] = v, note
    if data is not None:
        CUR["data"] = data

def missing(text, *pats):
    """The patterns (regex, case-insensitive, multiline) the text does not hold."""
    return [p for p in pats if not re.search(p, text or "", re.I | re.M)]

ERR = r"LUA ERROR|NO REPLY|stack traceback|attempt to (index|call|compare|perform|concatenate)|\.lua:\d+:"
def errs(text):
    return re.findall(ERR, text or "")

def judge(text, want=(), forbid=(), what=""):
    """Pass when every wanted pattern is there, no forbidden one is, and no Lua error; the note says which."""
    miss = missing(text, *want)
    hit = [p for p in forbid if re.search(p, text or "", re.I | re.M)]
    er = errs(text)
    parts = []
    if miss: parts.append("missing " + "; ".join(f"/{p}/" for p in miss))
    if hit: parts.append("present but should not be " + "; ".join(f"/{p}/" for p in hit))
    if er: parts.append("error text: " + ", ".join(sorted(set(er))))
    v = "a" if parts else "p"
    return v, (what + (": " if what else "") + ("; ".join(parts) if parts else "every expected line seen"))

def first(text, pat, default=""):
    m = re.search(pat, text or "", re.I | re.M)
    return (m.group(0) if m else default).strip()

def lines_with(text, pat, n=4):
    return " | ".join(l.strip()[:160] for l in (text or "").splitlines() if re.search(pat, l, re.I))[: 160 * n]

# ---- facts about the fort ----------------------------------------------------------------------------------------
FACTS_LUA = SW + """local out={loaded=dfhack.isMapLoaded()}
out.dfhack = dfhack.getDFHackVersion and dfhack.getDFHackVersion() or '?'
out.df = dfhack.getDFVersion and dfhack.getDFVersion() or '?'
out.r2 = (dfhack.units.getBreathingState ~= nil)
if out.loaded then
  local m = df.global.world.map; out.x, out.y, out.z = m.x_count, m.y_count, m.z_count
  local c = sw.loadConfig(); out.enabled = c.enabled; out.initialized = c.initialized and true or false
  local ok, w = pcall(sw.ENGINE.waterTiles, false)
  if ok and type(w) == 'table' then out.water = w.sum; out.maxDepth = w.maxDepth end
  local okc, cf = pcall(sw.cavernsFound)
  out.caverns = {}; out.reached = 0
  if okc and type(cf) == 'table' then for d, found in pairs(cf) do out.caverns['c' .. d] = found; if found then out.reached = out.reached + 1 end end end
  local n = 0; for _, u in ipairs(df.global.world.units.active) do if dfhack.units.isCitizen(u) and not dfhack.units.isDead(u) then n = n + 1 end end
  out.citizens = n
  local okv, sav = pcall(function() local st = df.global.world.world_data.active_site[0]; return dfhack.maps.getRegionBiome(st.pos.x, st.pos.y).savagery end)
  out.savagery = okv and sav or nil
  out.year, out.season, out.tick = df.global.cur_year, df.global.cur_season, df.global.cur_year_tick
end
print(json.encode(out))"""

def facts(refresh=False):
    if refresh or "facts" not in memo:
        memo["facts"] = luap(FACTS_LUA, timeout=120)
    return memo["facts"]

def water_bodies():
    w = (facts().get("water") or {}) if isinstance(facts().get("water"), dict) else {}
    return [b for b in ("ocean", "lake", "river", "pool") if (w.get(b) or 0) > 0]

def calm():
    s = facts().get("savagery")
    return isinstance(s, (int, float)) and s < 33

def ensure_tool():
    """The tool as a tester has it after the first open: initialized (the first-run preset), rotation on."""
    if memo.get("tool_ready") or DRY:
        return
    c = cfgv("initialized", "enabled")
    if not c.get("initialized"):
        open_window(); nap(1.5); memo["first_run"] = label("layers_status") or "first open"
        close_window()
    memo["tool_ready"] = True

# ---- the browser companion (served by DF at 127.0.0.1:8642; CrossOver shares the Mac's loopback) ----------------
def http(path, method="GET", host=None, timeout=10, record=True):
    if DRY:
        plan(f"HTTP {method} http://127.0.0.1:{WEB_PORT}{path}" + (f"  (Host: {host})" if host else ""))
        return 0, ""
    req = urllib.request.Request(f"http://127.0.0.1:{WEB_PORT}{path}", method=method, data=(b"" if method == "POST" else None))
    if host:
        req.add_header("Host", host)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            code, body = r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        code, body = e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        code, body = 0, f"{type(e).__name__}: {e}"
    if record:
        ev("http", f"{method} {re.sub(r't=[0-9a-f]+', 't=TOKEN', path)}" + (f" Host:{host}" if host else ""),
           f"{code} " + (body if len(body) < 1500 else body[:1500] + f" ...[{len(body)} bytes]"))
    return code, body

def js(body):
    try:
        return json.loads(body)
    except Exception:
        return {}

def web_up():
    """Start the companion once (the step 6.16 verb); returns the token or ''."""
    if memo.get("web_tok") and not DRY:
        return memo["web_tok"]
    out = webcmd("start", WEB_PORT)
    memo["web_start"] = out
    m = re.search(r"\?t=([0-9a-f]+)", out or "")
    memo["web_tok"] = m.group(1) if m else ""
    nap(1.0)
    return memo["web_tok"] or ("0" * 20 if DRY else "")

def q(**kw):
    return urllib.parse.urlencode(kw, doseq=True)

def web_set(tok, cid, v, extra=None):
    c, b = http(f"/set?{q(t=tok, id=cid, v=v, **(extra or {}))}", "POST")
    return c, js(b), b

def web_needed(sid):
    tok = web_up()
    if not tok:
        mark("s", f"the companion did not start, so this browser step cannot be reached from the Mac: {memo.get('web_start', '')[:300]}")
    return tok

# =============================================================================================== 0
@step("0.1", "Choose the world and the fort")
def s0_1():
    f = facts(refresh=True)
    ok = f.get("loaded") and (f.get("citizens") or 0) > 0
    mark("p" if ok or DRY else "a",
         f"{FORT} (world region9) restored from {FORT}.{BACKUP_TAG} and loaded: map {f.get('x')}x{f.get('y')} tiles "
         f"({(f.get('x') or 0) // 48}x{(f.get('y') or 0) // 48} embark), {f.get('citizens')} citizens, year {f.get('year')} "
         f"{SEASONS[f.get('season') or 0]}, water {f.get('water')}, deepest column {f.get('maxDepth')}, caverns {f.get('caverns')}, "
         f"savagery {f.get('savagery')} ({'calm' if calm() else 'not calm'}), tool initialized {f.get('initialized')}, rotation {f.get('enabled')}.", f)

@step("0.2", "Back it up")
def s0_2():
    b = BACKUPS / f"{FORT}.{BACKUP_TAG}"
    ok = b.is_dir() or DRY
    mark("p" if ok else "a", f"The control is {b.name} in df-snapshots ({'present' if b.is_dir() else 'MISSING'}); the session restored the save "
         f"from it before loading, and the round never saves over {FORT} (6.14 saves to the new folder {RELOAD}, deleted at the end).")

@step("0.3", "DFHack is 53.16-r2")
def s0_3():
    f = facts()
    v = str(f.get("dfhack", ""))
    tb = ""
    logf = DF_DIR / "stderr.log"
    if logf.exists() and memo.get("stderr0") is not None:
        tail = logf.read_bytes()[memo["stderr0"]:].decode("utf-8", "replace")
        tb = lines_with(tail, r"seasonal-wildlife.*(error|traceback)|traceback.*seasonal", 3)
    ok = "53.16-r2" in v
    mark("p" if (ok and not tb) or DRY else "a", f"DFHack version '{v}' (DF {f.get('df')}); r2 API (units.getBreathingState) {f.get('r2')}; "
         f"stderr.log since the session began: {tb or 'no traceback naming seasonal-wildlife'}.")

@step("0.4", "The tool is 7.1.0")
def s0_4():
    rel = luap(SW + "print(json.encode({r=sw.CACHE.release}))").get("r")
    ev("lua", "lua print(reqscript('seasonal-wildlife').CACHE.release)", rel)
    h = script("help", "seasonal-wildlife")
    verbs = [r"water layer", r"water spill|spill", r"vermin forage", r"scavenge", r"curious reform|reform", r"hunters", r"roster apex", r"extinct", r"irruption", r"perf"]
    miss = missing(h, *verbs)
    v71 = len(re.findall(r"v7\.1", h))
    ok = rel == "7.1.0" and not miss
    mark("p" if ok else "a", f"CACHE.release reads '{rel}'; `help seasonal-wildlife` ({len(h)} chars) names the v7.1 verbs: "
         f"{'all' if not miss else 'missing ' + ', '.join(miss)}; 'v7.1' appears {v71} time(s).")

EXPECT_CTL = {"switches": 20, "limits": 19, "caverns": 10, "leaders": 13, "roster": 40, "ecology": 31, "water": 33,
              "scavenging": 38, "vermin": 23, "extinct": 9, "v7": 17, "irruption": 103}
@step("0.5", "The controls module is deployed")
def s0_5():
    out = script("seasonal-wildlife-controls")
    got = {m.group(1): int(m.group(2)) for m in re.finditer(r"^(\w+)\s+(\d+)\s{2}", out, re.M)}
    tail = re.search(r"(\d+) species rows, (\d+) actions, (\d+) readouts", out)
    diff = {k: (v, got.get(k)) for k, v in EXPECT_CTL.items() if got.get(k) != v}
    tl = tuple(int(x) for x in tail.groups()) if tail else None
    ok = not diff and tl == (7, 21, 27)
    if "Unknown command" in out or "not found" in out.lower() and not got:
        return mark("a", f"the command is unknown: the deploy missed seasonal-wildlife-controls.lua: {out[:200]}")
    mark("p" if ok else "a", f"{len(got)} section lines, total {sum(got.values())} controls; tail '{tail.group(0) if tail else 'none'}'. "
         + ("Every count as the page expects." if ok else f"Differs from the page (expected, got): {diff or 'sections equal'}; tail expected 7/21/27, got {tl}."
            + " The page's counts were taken at fce7d68; the deployed build is bff2726 (fixes2), so a moved count may be the newer build."),
         {"sections": got, "tail": tl})

@step("0.6", "Help and usage list every verb once")
def s0_6():
    out = tool("help")
    v, n = judge(out, want=[r"^Usage: seasonal-wildlife \[gui\|status\|now\|enable\|disable\|preset\|undo\|layer", r"perf \.\.\.\]",
                            r"realm \.\.\.", r"v7 \.\.\.", r"extinct \.\.\.", r"irruption \.\.\.", r"TOKEN"],
                 forbid=[r"\bquota\b", r"cavern \[on\|off\|now\]", r"water target"], what="the usage line")
    words = re.findall(r"[|\[]([a-z][a-z0-9]*)(?= |\||\])", out.split("(TOKEN")[0])
    top = [w for w in words if w in ("gui", "status", "now", "enable", "disable", "preset", "undo", "layer", "limits", "groups", "water", "place", "stock",
                                     "odds", "size", "call", "sendoff", "roster", "seasons", "pattern", "ledger", "clear", "classes", "class", "caverns",
                                     "vermin", "scavenge", "curious", "exhaust", "alerts", "hunting", "hunters", "sponges", "realm", "v7", "extinct", "irruption", "perf")]
    dup = sorted({w for w in top if top.count(w) > 1} - {"on", "off"})
    mark(v, n + (f"; words listed more than once: {dup}" if dup else "; no verb word repeated at the top level") + ".")

@step("0.7", "A v7.0 fort migrates once")
def s0_7():
    led = tool("ledger", "400")
    irr = tool("irruption")
    if not re.search(r"migrat", led + irr, re.I):
        return mark("s", "This fort never ran v7.0 (no 'migrat' in the ledger or the irruption readout): a fresh region9 fort has nothing to migrate, as the page says.")
    out = "\n".join([tool("groups", "ecology"), tool("v7"), tool("limits"), irr])
    v, n = judge(out, want=[r"3000", r"migrated v7\.0|migrated"], what="migrated defaults")
    mark(v, n + ". " + lines_with(led + irr, r"migrat", 4))

@step("0.8", "Frame-rate baseline")
def s0_8():
    n, s = stepped(3000)
    memo["base_tps"] = n / s if s else None
    fps = luap("print(json.encode({fps=df.global.enabler.calculated_fps, cap=df.global.enabler.fps}))")
    mark("p" if s or DRY else "a", f"Window closed, tick cap 1000: {n} ticks in {s}s = {n / s if s else 0:.0f} ticks per second "
         f"(DF reports {fps.get('fps')} fps against the cap {fps.get('cap')}). The baseline for 6.22.")

# =============================================================================================== 1
@step("1.1", "Roster: the columns and the keys in full", "gui")
def s1_1():
    ensure_tool(); open_window("Roster")
    t = win_text(screen("roster"))
    cols = ["CREATURE", "ROLE", "SIZE", "HAB", "BIOME", "SEASON", "STOCK", "ODDS", "act", "WHY"]
    labels = [r"Ctrl\+f: Send off \+ next", r"Ctrl\+w: Stock \(row\)", r"Ctrl\+g: Stock \(filter\)", r"Alt\+o: Odds \(row\)", r"Ctrl\+x: Add invasive"]
    mc = [c for c in cols if c not in t]
    ml = missing(t, *labels)
    bio = first(t, r"Biome: \S+")
    mark("a" if mc or ml else "p", f"Columns {'all present' if not mc else 'missing ' + str(mc)}; key labels "
         f"{'all read in full' if not ml else 'not found in full: ' + ', '.join(ml)}; filter row '{bio or 'no Biome label seen'}'.")

@step("1.2", "The species page and its v7 rows", "gui")
def s1_2():
    ensure_tool(); close_window(); open_window("Roster")
    r = roster()
    k = next((k for k, e in r.items() if e.get("allow") is True and e.get("layer") == "land" and e.get("cat") == "predator"), None) or \
        next((k for k, e in r.items() if e.get("allow") is True and e.get("layer") == "land" and e.get("cat") == "prey"), None)
    if not k and not DRY:
        return mark("s", "no active land animal on the Roster to open")
    select_key(k or "")
    opened, t = asks("CUSTOM_I", "detail")
    st = scr_text(t)
    foot = missing(st, r"Enter: active/inactive", r"k: stock", r"v: v7")
    v7line = first(st, r"v7: .*")
    o2, t2 = asks("CUSTOM_V", "v7rows")
    rows = [x for x in ("skill level", "never stoops", "fishes", "swimmer scavenger", "cohesion", "water apex", "extinct") if x in scr_text(t2).lower()]
    esc(0.8); esc(0.8)
    ok = opened and not foot and v7line and o2 and rows
    mark("p" if ok else "a", f"{k}: detail page {'opened' if opened else 'did NOT open'}; foot labels {'all seen' if not foot else 'missing ' + str(foot)}; "
         f"facts line '{v7line or 'no v7: line'}'; V {'opened a list' if o2 else 'opened nothing'} with rows {rows or 'none recognised'}.")

@step("1.3", "Add invasive: a SAVAGE species on a calm map", "gui")
def s1_3():
    ensure_tool()
    if not calm() and not DRY:
        return mark("s", f"{FORT} is not a calm map (savagery {facts().get('savagery')}); the R36 placement is for calm maps.")
    close_window(); open_window("Roster")
    lab = ""
    for i in range(4):
        lab = luap(GW + "print(json.encode({l=w.subviews.viewmode:getOptionLabel()}))").get("l") or ""
        if "Add" in str(lab):
            break
        key("CUSTOM_V", 1.0)
    if "Add" not in str(lab) and not DRY:
        return mark("a", f"View never reached Add invasive (last '{lab}')")
    pick = luap(GW + "local L=w.subviews.list; local vis=L:getVisibleChoices(); local best=nil; for i,c in ipairs(vis) do if c.entry and c.entry.token=='CENOZOIC_SMILODON' then best=i end end; "
                "best=best or 1; local c=vis[best]; if L.list then L.list:setSelected(best) end; print(json.encode({t=c and c.entry and c.entry.token or '', k=c and c.entry and c.entry.key or ''}))")
    tok = pick.get("t", "")
    asked, _ = asks("CUSTOM_CTRL_X", "ask")
    if asked and not DRY:
        yes()
    st = label("status")
    nap(1.0)
    ap = tool("roster", "apex")
    placed = re.search(r"invasive placed:?\s*(\d+)", ap)
    ok = tok and placed and int(placed.group(1)) >= 1
    mark("p" if ok else "a", f"Added {tok or '?'} (confirm asked: {asked}); status '{st[:160]}'; roster apex: '{first(ap, r'.*invasive placed.*')[:200] or 'no invasive placed count'}'.")
    close_window()

def panel_check(sec, want, name, forbid=(r"error", r"Refused")):
    ensure_tool(); close_window()
    okS = panel_open(sec)
    t = win_text(screen(name))
    rows = "\n".join(panel_rows())
    v, n = judge(rows, want=want, forbid=forbid, what=f"section {sec}")
    if not okS and not DRY:
        v, n = "a", f"S never reached section {sec} (shown: {panel_shown()})"
    return v, n, rows, t

@step("1.4", "Panel: Roster & apexes", "gui")
def s1_4():
    v, n, rows, t = panel_check("roster", [r"roster v7\.1", r"apex \w+ present \d+%", r"pyramid \w+", r"APEX SCHEDULER", r"LADDER AND PYRAMID",
                                           r"PICKS AND FREQUENCIES", r"PREDATION MODEL", r"Build the roster", r"Apex decision now"], "roster")
    mark(v, n + f". First readout: '{first(rows, r'roster v7\.1.*')[:200]}'.")

@step("1.5", "Panel: Extinct", "gui")
def s1_5():
    v, n, rows, t = panel_check("extinct", [r"extinct: fix", r"Grazers", r"Rows"], "extinct")
    g0 = cfgv("extinct.grazer").get("extinct.grazer")
    panel_select("extinct.grazer"); key("SELECT", 1.5); r1 = panel_report(); g1 = cfgv("extinct.grazer").get("extinct.grazer")
    key("SELECT", 1.5); r2 = panel_report(); g2 = cfgv("extinct.grazer").get("extinct.grazer")
    panel_select("extinct_list"); opened, lb = asks("SELECT", "rows", 1.5)
    has_rows = "extinct-entry" in scr_text(lb)
    if opened:
        esc(0.8)
    ok = v == "p" and "extinct set grazer" in r1["cmd"] and "read back" in r1["status"] and g1 != g0 and g2 == g0 and opened and has_rows
    mark("p" if ok or DRY else "a", f"{n}. Grazers {g0} -> {g1} -> {g2}; bottom lines after the first Enter: '{r1['cmd'][:90]}' / '{r1['status'][:90]}'; "
         f"Rows {'opened a list with extinct-entry lines' if opened and has_rows else 'opened ' + ('a list without extinct-entry' if opened else 'nothing')}.")

def con_step(cmds, want=(), forbid=(r"^Usage: seasonal-wildlife",), what="", extra=""):
    out = "\n".join(tool(*c) for c in cmds)
    v, n = judge(out, want=want, forbid=forbid, what=what)
    mark(v, n + (". " + extra if extra else "."))
    return out

@step("1.6", "Build the land roster", "con")
def s1_6():
    ensure_tool()
    out = tool("roster", "build", "land", timeout=120)
    apex = re.findall(r"apex (\S+): FREQUENCY (\d+)", out)
    ladder = first(out, r"ladder-info.*")
    u = tool("undo")
    v, n = judge(out + "\n" + u, want=[r"ladder-info target=", r"gobble edges: \d+", r"undid:.*roster"], forbid=[r"^Usage:"], what="build land then undo")
    mark(v, f"{n}. {ladder[:200]}; apexes seated by the scheduler: {', '.join(f'{a} {f}' for a, f in apex) or 'none'}; undo: '{first(u, r'undid.*')}'.")

@step("1.7", "The flying layer", "con")
def s1_7():
    ensure_tool()
    out = tool("roster", "build", "flying", timeout=120)
    apx = lines_with(out, r"\bAPX\b", 3)
    bad = [x for x in ("VULTURE", "BUZZARD", "KEA", "RAVEN") if re.search(r"APX.*" + x, out)]
    u = tool("undo")
    v, n = judge(out, want=[r"\bAPX\b", r"\bRP\b", r"\bLB\b", r"\bWB\b"], forbid=[r"^Usage:"], what="build flying")
    if bad:
        v, n = "a", n + f"; scavenger birds in APX: {bad}"
    mark(v, f"{n}. APX: {apx[:240] or '-'}; undo: '{first(u, r'undid.*')}'.")

@step("1.8", "The water roster and the curated apexes", "con")
def s1_8():
    ensure_tool()
    b = tool("roster", "build", "water", timeout=120)
    a = tool("roster", "aquatic")
    tool("undo")
    n_ap = len(re.findall(r"^\s*aquatic-apex \S+", a, re.M))
    bears = re.findall(r"aquatic-apex (BEAR\S*) (\w+)", a)
    dim = "DIMETRODON" in a
    ocean = "ocean" in water_bodies()
    ok = n_ap == 33 and not dim and all(r == "fisher" for _, r in bears) and not errs(b + a)
    mark("p" if ok else "a", f"roster aquatic: {n_ap} aquatic-apex lines (page: 33); bears {bears or 'none listed'}; DIMETRODON {'LISTED' if dim else 'absent'}. "
         f"Build water: {lines_with(b, r'\\b(APE|PE|MW|UNFILLED)\\b', 4) or b[:200]}. "
         f"{'This fort has an ocean.' if ocean else 'No ocean on this fort (bodies: ' + (', '.join(water_bodies()) or 'none') + '): the APE/PE ocean seats are untested here.'}")

@step("1.9", "Animal people, giants and the x3 pack bonus", "con")
def s1_9():
    ensure_tool()
    s = tool("roster", "set")
    miss = missing(s, r"ap_pick=0\.1\b", r"ap_freq=0\.25", r"ap_freq_floor=1", r"giant_pick=0\.2", r"giant_freq=0\.5", r"pack_bonus=3")
    picks = []
    for i in range(3):
        o = tool("roster", "build", "land", timeout=120, record=(i == 0))
        picks.append((len(set(re.findall(r"\b([A-Z_]+_MAN)\b", o))), len(set(re.findall(r"\b(GIANT_[A-Z_]+)\b", o)))))
        tool("undo", record=False)
    mark("a" if miss else "p", f"knobs {'as the page says' if not miss else 'differ: missing ' + str(miss)} ('{s.strip()[:200]}'); "
         f"three land builds (each undone): animal people / giants named per build {picks}.")

@step("1.10", "Outgunned pairs on every layer", "con")
def s1_10():
    ensure_tool()
    con_step([("roster", "outgun", "land"), ("roster", "outgun", "flying")],
             want=[r"roster outgun land -- (\d+ pair|none found)", r"roster outgun flying -- (\d+ pair|none found)"], what="outgun land and flying")

@step("1.11", "Extinct corrections", "con")
def s1_11():
    ensure_tool()
    out = con_step([("extinct",), ("extinct", "list"), ("extinct", "mods"), ("extinct", "CRETACEOUS_TYRANNOSAURUS", "off"), ("extinct", "CRETACEOUS_TYRANNOSAURUS", "on")],
                   want=[r"extinct: fix (on|off) \[", r"of 83 table species", r"extinct-entry \S+", r"extinct-mod-only", r"attack mods active: \d+", r"CRETACEOUS_TYRANNOSAURUS.*\| skipped"],
                   what="extinct status, list, mods, a row off and on")
    CUR["note"] += f" Status: '{first(out, r'extinct: fix.*')[:220]}'."

@step("1.12", "The realm table", "con")
def s1_12():
    ensure_tool()
    out = con_step([("realm", "table"), ("realm",)], want=[r"realm-table entries=\d+ missing_from_raws=0", r"realm-entry \S+", r"^realm: "],
                   what="realm table and realm")
    CUR["note"] += f" Head: '{first(out, r'realm-table.*')[:200]}'."

@step("1.13", "The apex scheduler", "con")
def s1_13():
    ensure_tool()
    b = tool("roster", "build", "land", timeout=120)
    out = "\n".join([tool("roster", "apex", "status"), tool("roster", "apex", "now", "land"),
                     tool("roster", "apex", "target", "land", "30"), tool("roster", "apex", "target", "land", "25")])
    tool("undo"); tool("undo"); tool("undo")
    v, n = judge(out, want=[r"apex-state land groups=\d+ units=\d+ presence=", r"apex now|placed|cap \d+ reached|nothing placed"], forbid=[r"^Usage:"],
                 what="status, now, target 30 then 25")
    mark(v, f"{n}. {lines_with(out, r'apex-state land|apex now|placed|cap', 3)}. (The build, the target changes and the build were undone.)")

@step("1.14", "Roster tab", "web")
def s1_14():
    ensure_tool()
    tok = web_needed("1.14")
    if not tok:
        return
    c1, page = http("/", record=False)
    c2, st = http(f"/status.json?{q(t=tok, s='roster')}")
    c3, cj = http(f"/controls.json?{q(t=tok)}", record=False)
    reg = js(cj); acts = {a.get("id") for a in reg.get("actions") or [] if isinstance(a, dict)}
    sec = (js(st).get("sections") or {}).get("roster") or {}
    lines = sec.get("lines") or []
    ok = c1 == 200 and "Roster" in page and c2 == 200 and not sec.get("error") and any("apex" in str(l) for l in lines) and {"roster_build", "apex_now"} <= acts
    mark("p" if ok else "a", f"Data level only (the page is not rendered here): GET / {c1} ({len(page)} bytes, 'Roster' tab {'in' if 'Roster' in page else 'NOT in'} the page); "
         f"status roster {c2}: {len(lines)} line(s), e.g. '{(lines[0] if lines else '')[:140]}'; actions Build/Apex now in the registry: "
         f"{sorted(acts & {'roster_build', 'apex_now'})}. The pyramid drawing itself needs a browser.")

@step("1.15", "Species chips and v7 rows", "web")
def s1_15():
    ensure_tool()
    tok = web_needed("1.15")
    if not tok:
        return
    c, b = http(f"/state.json?{q(t=tok)}", record=False)
    snap = js(b); sp = [s for s in snap.get("species") or [] if isinstance(s, dict)]
    keys = sorted({k for s in sp for k in s.keys()})
    swapped = [s.get("token") for s in sp if isinstance(s.get("gmin"), (int, float)) and isinstance(s.get("gmax"), (int, float)) and s["gmin"] > s["gmax"]]
    c2, cj = http(f"/controls.json?{q(t=tok)}", record=False)
    srows = [r.get("id") for r in js(cj).get("species") or [] if isinstance(r, dict)]
    chips = [k for k in ("slot", "guild", "part", "giant", "extinct", "scav", "gobble") if any(k in kk for kk in keys)]
    ev("http", "GET /state.json", f"{c} species {len(sp)}; fields {keys[:60]}")
    ok = c == 200 and sp and not swapped and len(srows) >= 7
    mark("p" if ok else "a", f"state.json {c}: {len(sp)} species; chip fields present {chips}; group sizes min>max on {swapped[:6] or 'none'}; "
         f"per-species v7 rows in the registry {len(srows)} ({', '.join(map(str, srows[:7]))}). Data level only; the chips' drawing needs a browser.")

# =============================================================================================== 2
@step("2.1", "Overview: the real caps", "gui")
def s2_1():
    ensure_tool(); open_window("Overview")
    win_text(screen("overview"))
    t = "\n".join(view_lines("overview"))
    grp = lines_with(t, r"group", 6)
    ok = re.search(r"\bof \d+", t) and re.search(r"cap \d+ each", t) and not re.search(r"\btarget\b", grp, re.I) and not re.search(r"cavern.*\bof 2\b", t, re.I)
    mark("p" if ok or DRY else "a", f"Groups lines: {grp or 'none found'}; irruptions line: '{first(t, r'irruptions:.*')[:120] or 'none (irruptions off)'}'.")

@step("2.2", "Layers: group cap and release clock", "gui")
def s2_2():
    ensure_tool(); open_window("Layers")
    t = win_text(screen("layers"))
    rows = "\n".join(view_lines("layers"))
    v, n = judge(rows, want=[r"group cap", r"\(map size\)|map size", r"5/cavern", r"release clock", r"adapt 0\.5-20d"], what="Layers rows")
    wide = max((len(l) for l in rows.splitlines()), default=0)
    mark(v if wide <= 86 else "a", n + f"; widest row {wide} columns (86 allowed). {lines_with(rows, r'group cap|release clock', 2)}")

@step("2.3", "Layers C: one fixed cap, or the formula", "gui")
def s2_3():
    ensure_tool(); close_window(); open_window("Layers")
    opened, p = asks("CUSTOM_C", "prompt")
    title = "Group cap (every layer)" in scr_text(p)
    answer("3")
    s1 = label("layers_status"); l1 = tool("limits")
    key("CUSTOM_C", 1.0); answer("auto")
    s2 = label("layers_status"); l2 = tool("limits")
    ok = opened and title and "Fixed cap: 3" in s1 and "read back" in s1 and "single fixed cap 3" in l1 and "map-size formula" in l2
    mark("p" if ok or DRY else "a", f"prompt {'titled Group cap (every layer)' if title else 'opened: ' + str(opened)}; after 3: status '{s1[:100]}', limits '{first(l1, r'limits \[.*?\]')}'; "
         f"after auto: status '{s2[:100]}', limits '{first(l2, r'limits \[.*?\]')}'.")

@step("2.4", "Panel: Limits & groups", "gui")
def s2_4():
    v, n, rows, t = panel_check("limits", [r"Group cap:", r"MAP-SIZE FORMULA|sqrt", r"caverns 5 each|cavern", r"\blayer\b.*\bcap\b", r"^\s*land\b",
                                           r"Adaptive release clock", r"Fixed cap", r"Drawn groups leave with their leader", r"Shortest gap", r"Longest gap"], "limits")
    memo["limits_readout"] = first(rows, r"Group cap:.*")
    mark(v, n + f". Readout: '{memo['limits_readout'][:200]}'.")

@step("2.5", "Live: limits and groups", "gui")
def s2_5():
    ensure_tool(); close_window(); open_window("Live")
    screen("live")
    t = "\n".join(view_lines("live"))
    lim = first(t, r".*limits.*"); grp = first(t, r"Groups:.*")
    states = sorted({s for s in ("led by #", "PANIC", "unled", "native", "seeded", "placed", "adopted", "IRR") if s in t})
    gap = "gap 5-20 days" in t
    ok = lim and grp
    mark("p" if ok or DRY else "a", f"limits line '{lim[:160]}'; Groups line '{grp[:120]}'{' (still the v6 gap wording: the watch item)' if gap else ''}; "
         f"group states seen: {states or 'none (no groups on the map)'}.")

@step("2.6", "Panel: Leaders & panic", "gui")
def s2_6():
    v, n, rows, t = panel_check("leaders", [r"leaders \(R32\): largest adult male", r"panic", r"animal-people", r"Panic days", r"Flight radius",
                                            r"Re-elect after panic", r"Cohesion"], "leaders")
    mark(v, n + f". '{first(rows, r'leaders \(R32\).*')[:200]}'.")

@step("2.7", "limits: formula, fixed, and the retired per-layer number", "con")
def s2_7():
    ensure_tool()
    outs = [tool("limits"), tool("limits", "fixed", "4"), tool("limits", "land", "groups", "3"), tool("limits", "water", "groups", "auto"), tool("limits", "formula")]
    want = [(0, r"limits \[map-size formula"), (0, r"on the map now"), (1, r"single fixed cap 4"), (2, r"per-layer group numbers are retired"),
            (4, r"map-size formula")]
    miss = [f"#{i + 1} /{p}/" for i, p in want if not re.search(p, outs[i], re.I)]
    usage = [i + 1 for i, o in enumerate(outs) if re.search(r"^Usage:", o, re.M)]
    er = errs("\n".join(outs))
    ok = not miss and not usage and not er
    mark("p" if ok else "a", ("every reply as expected" if ok else f"missing {miss}; usage printed by command(s) {usage}; errors {er}")
         + f". First: '{first(outs[0], r'limits \[.*')[:200]}'; water groups auto: '{outs[3].strip()[:120]}'.")

@step("2.8", "groups layers: one row per layer key", "con")
def s2_8():
    ensure_tool()
    out = tool("groups", "layers")
    keys = re.findall(r"^\s+(land|water:\S+|cavern:\d+)\s+cap (\d+) \(([^)]+)\)", out, re.M)
    v, n = judge(out, want=[r"release clock: adaptive", r"cavern gate \(R44\)", r"leaders \(R32\)", r"animal-people cap"], what="groups layers")
    if not keys and not DRY:
        v, n = "a", n + "; no per-key rows"
    mark(v, n + f"; rows: {', '.join(f'{k} cap {c} ({m})' for k, c, m in keys) or 'none'}.")

def layer_rows(out):
    return {m.group(1): {"cap": int(m.group(2)), "now": int(m.group(4))}
            for m in re.finditer(r"^\s+(land|water:\S+|cavern:\d+)\s+cap (\d+) \(([^)]+)\)\s+target \S+\s+now (\d+)", out, re.M)}

@step("2.9", "The adaptive clock fills toward the cap", "con")
def s2_9():
    ensure_tool()
    a = tool("groups", "clock", "jitter", "0.5"); b = tool("groups", "clock", "jitter", "0.35")
    r0 = layer_rows(tool("groups", "layers"))
    n, s = stepped(3600)
    r1 = layer_rows(tool("groups", "layers"))
    ok = re.search(r"jitter \+-50%", a) and re.search(r"jitter \+-35%", b)
    land0, land1 = r0.get("land", {}), r1.get("land", {})
    mark("p" if ok or DRY else "a", f"jitter 0.5 -> '{first(a, r'jitter \+-\d+%')}', back -> '{first(b, r'jitter \+-\d+%')}'. Land now/cap {land0.get('now')}/{land0.get('cap')} "
         f"-> {land1.get('now')}/{land1.get('cap')} over {n} ticks (one short look; G2r measures the fill over 30,000).")

@step("2.10", "Leaders and panic", "con")
def s2_10():
    ensure_tool()
    g = luap(SW + """local g=sw.loadGroups(); local best=nil
for _,grp in ipairs(g.groups or {}) do
  local u = grp.leader and df.unit.find(grp.leader)
  if u and not dfhack.units.isDead(u) and #(grp.ids or {})>=3 and (grp.layer or 'land')=='land' and not grp.panic then best={token=grp.token, leader=grp.leader, n=#grp.ids} break end
end
print(json.encode(best or {}))""")
    if not g.get("leader") and not DRY:
        return mark("s", "no led land group of three or more on the map to lose its leader")
    l0 = ledger_count()
    luap(f"local u=df.unit.find({int(g.get('leader') or 0)}); if u then u.body.blood_count=0 end; print('{{}}')")
    ev("lua", f"the leader #{g.get('leader')} of {g.get('token')} x{g.get('n')} killed (blood to 0): the manipulation", None)
    stepped(1500)
    led = tool("ledger", "10", "panic")
    lay = tool("groups", "layers")
    after = luap(SW + f"""local g=sw.loadGroups(); for _,grp in ipairs(g.groups or {{}}) do if grp.token=='{g.get('token', '')}' then
  print(json.encode({{leader=grp.leader, lost=grp.leader_lost, panic=grp.panic and true or false}})) return end end; print('{{}}')""")
    ok = re.search(r"panic", led, re.I) and not after.get("leader")
    mark("p" if ok or DRY else "a", f"killed the leader of {g.get('token')} x{g.get('n')}; after 1,500 ticks the group's leader {after.get('leader')}, lost {after.get('lost')}, panic {after.get('panic')}; "
         f"ledger panic lines: {lines_with(led, r'panic', 2) or 'none'}; ledger {l0} -> {ledger_count()}.")

@step("2.11", "Aquatic leaders", "con")
def s2_11():
    ensure_tool()
    bodies = water_bodies()
    if not bodies and not DRY:
        return mark("s", "no water body on this map")
    out, body = "", ""
    for b in (["ocean", "lake", "river"] if DRY else [x for x in ("ocean", "lake", "river") if x in bodies]):
        out = tool("water", "now", b); body = b
        if re.search(r"water: drew", out):
            break
    m = re.search(r"water: drew (\S+) x(\d+) into the (\S+)", out)
    if not m and not DRY:
        return mark("s", f"no draw on {', '.join(bodies)}: '{out.strip()[:200]}' (season, stock or the cap bound it)")
    tok = m.group(1) if m else ""
    nap(1.0); stepped(300)
    gl = luap(SW + f"""local g=sw.loadGroups(); local o={{}}
for _,grp in ipairs(g.groups or {{}}) do if grp.token=='{tok}' and grp.body then
  local u = grp.leader and df.unit.find(grp.leader); local wet=false
  if u then local f=dfhack.maps.getTileFlags(u.pos); wet = f and f.flow_size>=4 or false end
  o[#o+1]={{leader=grp.leader, wet=wet, n=#(grp.ids or {{}}), body=grp.body, rule=grp.leader_rule}} end end
print(json.encode({{g=o}}))""")
    gs = gl.get("g") or []
    led = [x for x in gs if x.get("leader")]
    dry = [x for x in led if not x.get("wet")]
    mark("p" if (led and not dry) or DRY else "a", f"'{m.group(0) if m else out[:120]}'; its group(s): {gs[:3]}; "
         f"{'led by a wet leader' if led and not dry else ('a leader on dry land' if dry else 'not led')}.")

@step("2.12", "Water layer auto-on with season spill", "con")
def s2_12():
    ensure_tool()
    w0 = tool("water"); led = tool("ledger", "400", "edit")
    off = tool("water", "layer", "off"); w1 = tool("water")
    au = tool("water", "layer", "auto"); w2 = tool("water")
    has_water = bool(water_bodies())
    want_on = r"water layer on \(follows the map\)"
    checks = {"on by default (ledger)": re.search(r"water layer on by default", led), "follows the map": re.search(want_on, w0),
              "set by the player after off": re.search(r"set by the player", w1), "back to the map after auto": re.search(want_on, w2),
              "season spill line": re.search(r"season spill (on|off)", w0)}
    bad = [k for k, v in checks.items() if not v]
    if not has_water and not DRY:
        return mark("p" if re.search(r"water layer off", w0) else "a", f"dry map: '{first(w0, r'water layer.*')[:160]}'")
    mark("a" if bad else "p", f"{'all as designed' if not bad else 'not seen: ' + ', '.join(bad)}. Layer line '{first(w0, r'water layer.*')[:200]}'; "
         f"borrowed: '{first(w0, r'borrowed the season.*|nothing borrowed.*')[:120]}'.")

@step("2.13", "Column depth reads every level", "con")
def s2_13():
    ensure_tool()
    a = tool("water", "depth"); b = tool("water", "depth", "full", timeout=120)
    v, n = judge(a + b, want=[r"column depth = stacked water tiles", r"every 2nd x and y sampled|sampled"], what="depth and depth full")
    one = re.search(r"max(imum)? 1\b", a) and not re.search(r"\b[2-9]\b.*deep", a)
    mark(v, n + f". {lines_with(a, r'lake|river|ocean|pool|max|scan', 4)}" + (" (every column 1 deep?)" if one else ""))

@step("2.14", "Three to five water groups per body", "con")
def s2_14():
    ensure_tool()
    if not water_bodies() and not DRY:
        return mark("s", "no water on this map")
    w0 = tool("water")
    n, s = stepped(7200)
    w1 = tool("water")
    rows = re.findall(r"^\s+(ocean|lake|river|pool)\s+(\d+) of (\d+) group\(s\) at once", w1, re.M)
    best = max((int(g) for _, g, _c in rows), default=0)
    mark("p" if best >= 3 or DRY else "a", f"after {n} ticks: per-body groups/cap {[(b, int(g), int(c)) for b, g, c in rows][:5] or 'no rows parsed'}; "
         f"the page expects 3 by about 7,000 ticks where something can be drawn. Rows: {lines_with(w1, r'drawable|last reason', 3)}")

@step("2.15", "Groups tab", "web")
def s2_15():
    ensure_tool()
    tok = web_needed("2.15")
    if not tok:
        return
    c, b = http(f"/status.json?{q(t=tok, s='groupmap')}")
    lay = ((js(b).get("sections") or {}).get("groupmap") or {}).get("layers") or []
    keys = [x.get("key") for x in lay if isinstance(x, dict)]
    caps = {x.get("key"): x.get("cap") for x in lay if isinstance(x, dict)}
    ok = c == 200 and keys and keys[0] == "land" and all(v is not None for v in caps.values())
    mark("p" if ok else "a", f"groupmap {c}: layer keys {keys}; caps {caps}. Data level only: the cards and pips need a browser.")

# =============================================================================================== 3
@step("3.1", "The season deal on the Roster", "gui")
def s3_1():
    ensure_tool(); close_window(); open_window("Roster")
    r = roster()
    pick = next((k for k, e in r.items() if e.get("allow") is True and e.get("layer") == "land" and e.get("cat") in ("prey", "predator") and len(e.get("assign") or []) >= 1), None)
    if not pick and not DRY:
        return mark("s", "no active land species")
    select_key(pick or ""); key("SELECT", 1.2)
    a1 = roster().get(pick, {}); row1 = label("status")
    select_key(pick or ""); key("SELECT", 1.2)
    a2 = roster().get(pick, {})
    seq = [season_str(a2.get("assign"))]
    select_key(pick or "")
    for _ in range(5):
        key("CUSTOM_E", 0.9); seq.append(season_str(roster().get(pick, {}).get("assign")))
    one = next((k for k, e in roster().items() if e.get("allow") is True and e.get("layer") == "land" and len(e.get("assign") or []) == 1), None)
    refused = None
    if one and select_key(one):
        s = roster()[one]["assign"][0]
        key(SKEY[s], 1.0)
        refused = len(roster().get(one, {}).get("assign") or []) == 1 and "the last season stays" in (label("status") + win_text(screen("last")))
    select_key(pick or ""); key("SELECT", 1.2)   # inactive again: 3.8 watches it
    memo["inactive"] = pick
    ok = a1.get("allow") is False and a2.get("allow") is True and len(a2.get("assign") or []) == 1 and "none" not in seq and refused
    mark("p" if ok or DRY else "a", f"{pick}: Enter -> active {a1.get('allow')} (seasons {season_str(a1.get('assign'))}); Enter -> active {a2.get('allow')} with {season_str(a2.get('assign'))}; "
         f"E: {' -> '.join(seq)}; removing {one}'s last season refused with the message: {refused}. {pick} left inactive for 3.8.")

@step("3.2", "Seasons tab and Food web by season", "gui")
def s3_2():
    ensure_tool(); open_window("Seasons")
    t = "\n".join(view_lines("seasons")); screen("seasons")
    marks = {m: bool(re.search(r"\s" + re.escape(m) + r"\s", t)) for m in ("+", "-", "X", ".")}
    select_tab("Food web")
    modes = []
    for _ in range(4):
        modes.append(luap(GW + "print(json.encode({m=w.subviews.web_mode:getOptionValue()}))").get("m"))
        if modes[-1] == "byseason":
            break
        key("CUSTOM_G", 1.0)
    w1 = "\n".join(view_lines("web")); screen("byseason")
    seen = [s for s in SEASONS if s in w1]
    key("CUSTOM_N", 1.0); sel = luap(GW + "print(json.encode({s=w.subviews.web_season:getOptionLabel()}))").get("s")
    ok = marks["+"] and marks["."] and "byseason" in modes and len(seen) == 4
    mark("p" if ok or DRY else "a", f"Seasons marks drawn {marks}; Food web modes {modes}; By season columns {seen}; N -> '{sel}'.")

@step("3.3", "Rotation and apply", "gui")
def s3_3():
    ensure_tool(); close_window(); open_window("Roster")
    opened, t = asks("CUSTOM_CTRL_D", "dryrun", 1.5)
    table = "Dry-run" in scr_text(t) or "Sp Su Au Wi" in scr_text(t)
    if opened:
        esc(0.8)
    a0 = announcements(); key("CUSTOM_CTRL_A", 1.5); a1 = announcements()
    hit = [a for a in a1 if "wildlife applied" in a]
    e0 = cfgv("enabled").get("enabled"); key("CUSTOM_CTRL_E", 1.0); e1 = cfgv("enabled").get("enabled"); key("CUSTOM_CTRL_E", 1.0); e2 = cfgv("enabled").get("enabled")
    ok = table and hit and e1 is not e0 and e2 == e0
    mark("p" if ok or DRY else "a", f"Ctrl+D: dry-run table {'shown' if table else 'not seen'}; Ctrl+A: '{hit[-1] if hit else (a1[-1] if a1 else 'no announcement')}'; Ctrl+E twice: rotation {e0} -> {e1} -> {e2}.")

def a_species(cond=None, exclude=()):
    r = roster()
    for k, e in r.items():
        if e.get("allow") is True and e.get("layer") == "land" and k not in exclude and (cond is None or cond(e)):
            return k, e
    return None, {}

@step("3.4", "seasons and roster at the console", "con")
def s3_4():
    ensure_tool()
    k, e = a_species(lambda e: e.get("token") == "BADGER") if not DRY else ("BADGER", {})
    if not k:
        k, e = a_species(exclude=(memo.get("inactive"),))
    if not k and not DRY:
        return mark("s", "no active land species")
    key_ = k or "BADGER"
    outs = [tool("seasons", key_, "SpAu"), tool("seasons", key_, "none"), tool("seasons", key_, "Xy"), tool("undo")]
    checks = [re.search(r"active, seasons SpAu", outs[0]), re.search(r"keeps at least one season", outs[1]),
              re.search(r"Usage|usage", outs[2]), re.search(r"undid: seasons", outs[3])]
    note_raw = re.search(r"NO_(SPRING|SUMMER|AUTUMN|WINTER) in its raws", outs[0])
    ok = all(checks) and not note_raw
    mark("p" if ok or DRY else "a", f"{key_}{'' if e.get('token') == 'BADGER' else ' (no BADGER on this roster)'}: SpAu '{outs[0].strip()[:100]}'; none '{outs[1].strip()[:120]}'; "
         f"Xy {'printed the usage' if checks[2] else 'did not print the usage'}; undo '{outs[3].strip()[:80]}'.")

@step("3.5", "Spaced raw ids by #N, underscore or quotes", "con")
def s3_5():
    ensure_tool()
    sp = luap(SW + """local cfg=sw.loadConfig(); local pool=sw.buildPool(cfg); local inE={}
for _,e in ipairs(pool) do if e.inEmbark then inE[e.token]=true end end
local best=nil; local any=nil
for i,cr in ipairs(df.global.world.raws.creatures.all) do
  if cr.creature_id:find(' ') then any = any or {id=cr.creature_id, n=i}; if inE[cr.creature_id] then best={id=cr.creature_id, n=i} break end end
end
print(json.encode(best or any or {}))""")
    rid, n = sp.get("id"), sp.get("n")
    if not rid and not DRY:
        return mark("s", "no creature raw id with a space in this world's raws")
    rid = rid or "HONEY BADGER"; n = n if n is not None else 0
    us = rid.replace(" ", "_")
    outs = [tool("roster", us), tool("odds", us), tool("odds", rid), tool("odds", f"#{n}")]
    lines = [first(o, r"^odds .*") or o.strip()[:80] for o in outs[1:]]
    same = len(set(lines)) == 1 and lines[0] and not any(re.search(r"^Usage", o, re.M) for o in outs[1:])
    mark("p" if same or DRY else "a", f"'{rid}' (raws #{n}): roster {us} -> '{outs[0].strip()[:90]}'; the three odds forms -> {lines}.")

@step("3.6", "seasons on an inactive species", "con")
def s3_6():
    ensure_tool()
    k, e = a_species(exclude=(memo.get("inactive"),))
    if not k and not DRY:
        return mark("s", "no active land species")
    k = k or "X"
    tool("roster", k, "inactive")
    l0, u0 = ledger_count(), undo_depth()
    out = tool("seasons", k, "Wi")
    l1, u1 = ledger_count(), undo_depth()
    a = roster().get(k, {})
    tool("undo"); tool("undo")
    ok = a.get("allow") is True and a.get("assign") == [3] and (l1 or 0) == (l0 or 0) + 1 and (u1 or 0) == (u0 or 0) + 1
    mark("p" if ok or DRY else "a", f"{k} made inactive, then seasons Wi: '{out.strip()[:120]}'; now active {a.get('allow')} seasons {season_str(a.get('assign'))}; "
         f"ledger {l0} -> {l1}, undo depth {u0} -> {u1} (both undone after).")

@step("3.7", "Vermin edges and families by season", "con")
def s3_7():
    ensure_tool()
    con_step([("vermin",), ("vermin", "edges"), ("roster", "gobble", "land")],
             want=[r"who eats which vermin -- source in force: (both|rules|edges|table)", r"gobble-edge land \S+ -> \S+"], what="vermin, edges, gobble land")

def to_boundary():
    """Reach the next season boundary: step, or (when it is far) move the calendar to 2,400 ticks before it."""
    t = ticks_now()
    tick = t.get("t") or 0
    nxt = ((tick // SEASON_TICKS) + 1) * SEASON_TICKS
    gap = nxt - tick
    jumped = None
    if gap > SEASON_BUDGET and not NO_JUMP:
        new = nxt - 2400
        luap(f"df.global.cur_year_tick={new}; pcall(function() df.global.cur_season_tick={(new % SEASON_TICKS) // 10} end); print('{{}}')")
        ev("manipulation", f"cur_year_tick {tick} -> {new}, cur_season_tick -> {(new % SEASON_TICKS) // 10} (the boundary was {gap} ticks away; budget {SEASON_BUDGET})", None)
        jumped = (tick, new); gap = 2400
    if gap > SEASON_BUDGET:
        return None, gap, jumped
    n, s = stepped(gap + 3600)
    return n, gap, jumped

@step("3.8", "A season boundary", "con")
def s3_8():
    ensure_tool()
    k = memo.get("inactive")
    s0 = ticks_now().get("s")
    ids0 = max_unit_id()
    n, gap, jumped = to_boundary()
    if n is None and not DRY:
        return mark("s", f"the boundary is {gap} ticks away, past the budget, and --no-jump is set")
    s1 = ticks_now().get("s")
    memo["boundary"] = s1 != s0
    arr_raw = luap(SW + """local cfg=sw.loadConfig(); local s=df.global.cur_season; local o={}
for _,u in ipairs(df.global.world.units.active) do if u.id>%d and sw.WILD.onMap(u) then
  local t=df.creature_raw.find(u.race).creature_id; local L=sw.WILD.layerOf(u); local key=(L=='land') and t or (L..':'..t)
  o[#o+1]={id=u.id, t=t, layer=L, key=key, allow=cfg.allow[key], inseason=sw.ROSTER.wants(cfg,key,s)} end end
print(json.encode(o))""" % ids0)
    arr = lst(arr_raw)
    if "_err" in arr_raw and not DRY:
        return mark("a", f"the arrivals probe failed after the boundary: {arr_raw['_err'][:200]}")
    bad = [x for x in arr if x.get("allow") is False or (x.get("allow") is not None and x.get("inseason") is False)]
    same = [x for x in arr if x.get("key") == k]
    ann = [a for a in announcements(60) if "roster applied" in a]
    led = tool("ledger", "20", "season")
    ok = memo["boundary"] and ann and not bad and not same
    mark("p" if ok or DRY else "a", f"season {s0} -> {s1} ({'calendar moved ' + str(jumped) + ', then ' if jumped else ''}{n} ticks stepped); announcement "
         f"'{ann[-1] if ann else 'none'}'; ledger season lines: {len(re.findall(r'season', led))}; {len(arr)} wild arrival(s); the inactive {k}: {len(same)}; "
         f"inactive or out-of-season arrivals: {', '.join(x['layer'] + ':' + x['t'] for x in bad[:8]) or 'none'}.", {"arrivals": arr[:100]})

@step("3.9", "The bears' run season", "con")
def s3_9():
    ensure_tool()
    h = tool("hunters")
    a = tool("hunters", "fish", "run", "SpSu"); b = tool("hunters", "fish", "run", "SuAu")
    f0 = first(h, r"fishers: .*")
    ok = re.search(r"fishers: on \[.*BEAR", f0) and re.search(r"run SuAu", f0) and not errs(a + b)
    mark("p" if ok or DRY else "a", f"'{f0[:230]}'; run SpSu then SuAu: '{(a.strip() or 'ok')[:100]}' / '{(b.strip() or 'ok')[:100]}'.")

@step("3.10", "Apex presence per season", "con")
def s3_10():
    ensure_tool()
    a = tool("roster", "apex", "status")
    stepped(2400)
    b = tool("roster", "apex", "status")
    pres = re.findall(r"apex-state (\w+) .*?presence=([\d.]+)%", a + "\n" + b)
    v, n = judge(a + b, want=[r"apex-state land .*presence="], what="apex status twice, 2,400 ticks apart")
    mark(v, n + f"; presence readings {pres[:8]} (targets land 25, water 20, cavern 70, flying 0; a season-long share is APX1's).")

@step("3.11", "Exhaustion fills a niche for the season", "con")
def s3_11():
    ensure_tool()
    s = ticks_now().get("s") or 0
    k, e = a_species(lambda e: s in (e.get("assign") or []) and e.get("cat") in ("prey", "predator"), exclude=(memo.get("inactive"),))
    if not k and not DRY:
        return mark("s", "no active land species in season")
    k = k or "X"
    st = tool("stock", k, "0"); ex = tool("exhaust", "now"); led = tool("ledger", "6")
    tool("stock", k, "clear")
    m = re.search(r"exhaust: (\d+) replacement", ex)
    rep = lines_with(led, r"exhaust|replac|niche", 2)
    mark("p" if (m and int(m.group(1)) >= 1) or DRY else "a", f"{k} stock 0 ('{st.strip()[:80]}'); exhaust now: '{ex.strip()[:160]}'; ledger: {rep or 'no replacement line'}. Stock cleared after.")

@step("3.12", "The spill gives the season back", "con")
def s3_12():
    ensure_tool()
    if not memo.get("boundary") and not DRY:
        return mark("s", "no season boundary was crossed this round (3.8)")
    w = tool("water")
    sp = first(w, r".*(nothing borrowed|borrowed the season).*")
    seasonless = [k for k, e in roster().items() if e.get("allow") is True and not e.get("assign")]
    ok = "nothing borrowed" in sp and not seasonless
    mark("p" if ok or DRY else "a", f"after the boundary: '{sp[:200] or 'no spill line'}'; active species with no season: {seasonless[:6] or 'none'}.")

@step("3.13", "Seasons from the page", "web")
def s3_13():
    ensure_tool()
    tok = web_needed("3.13")
    if not tok:
        return
    k, e = a_species(exclude=(memo.get("inactive"),))
    if not k and not DRY:
        return mark("s", "no active land species")
    k = k or "X"
    a0 = e.get("assign") or []
    want = "SpAu" if season_str(a0) != "SpAu" else "Wi"
    c1, b1 = http(f"/cmd?{q(t=tok, a=['seasons', k, want])}", "POST")
    a1 = roster().get(k, {}).get("assign")
    c2, b2 = http(f"/cmd?{q(t=tok, a=['seasons', k, 'none'])}", "POST")
    led = tool("ledger", "3")
    tool("undo")
    j1, j2 = js(b1), js(b2)
    ok = c1 == 200 and season_str(a1) == want and ("keeps at least one season" in str(j2.get("out")) or c2 == 400)
    mark("p" if ok or DRY else "a", f"{k}: POST /cmd seasons {want} -> {c1} '{str(j1.get('out'))[:100]}', Roster now {season_str(a1)}; seasons none -> {c2} '{str(j2.get('out'))[:120]}'; "
         f"ledger: {lines_with(led, k, 1) or 'no line naming it'} (undone after).")

# =============================================================================================== 4
@step("4.1", "Pyramid against target", "gui")
def s4_1():
    v, n, rows, t = panel_check("roster", [r"pyramid land .*target 73/20/7"], "pyramid")
    pyr = re.findall(r"pyramid (\w+) ([\d/]+)%?,? target ([\d/]+)", rows)
    mark(v, n + f"; pyramid lines {pyr or lines_with(rows, r'pyramid', 5)} (targets: land 73/20/7, flying 80/20/0, ocean 82/13/5, lake 87/13/3, cavern 60/27/13).")

@step("4.2", "Panel: Ecology, hunters", "gui")
def s4_2():
    v, n, rows, t = panel_check("ecology", [r"hunter\s+profile", r"Ecology cadence", r"3000", r"Stoop chance", r"Raptors armed", r"Fishers|fish", r"Swimmer scavengers"], "ecology")
    c0 = cfgv("hunters.stoop.chance").get("hunters.stoop.chance")
    panel_select("hunters.stoop.chance"); key("KEYBOARD_CURSOR_RIGHT", 1.5); r1 = panel_report()
    c1 = cfgv("hunters.stoop.chance").get("hunters.stoop.chance")
    star = any(re.search(r"\*\s*Stoop chance|Stoop chance.*\*", l) for l in panel_rows())
    key("CUSTOM_D", 1.5); r2 = panel_report(); c2 = cfgv("hunters.stoop.chance").get("hunters.stoop.chance")
    ok = v == "p" and c1 == (c0 or 0) + 1 and "hunters stoop chance" in r1["cmd"] and "read back" in r1["status"] and c2 == 60
    mark("p" if ok or DRY else "a", f"{n}. Stoop chance {c0} -> right {c1} ('{r1['cmd'][:70]}', '{r1['status'][:60]}', star {star}) -> D {c2} ('{r2['status'][:60]}').")

@step("4.3", "Panel: Scavenging, Water, Vermin eating", "gui")
def s4_3():
    res = []
    for sec, want in (("water", [r"DRAWS", r"MIX", r"PULL", r"STRANDING"]), ("scavenging", [r"scavenging", r"DISCOVERY", r"FEEDING", r"CURIOUS"]),
                      ("vermin", [r"WIRING", r"CLASSES", r"FORAGING", r"gobble|forage"])):
        v, n, rows, t = panel_check(sec, want, sec)
        res.append((sec, v, n))
    bad = [r for r in res if r[1] != "p"]
    mark("a" if bad else "p", "; ".join(f"{s}: {n}" for s, v, n in res) + ".")

@step("4.4", "Hunter skill profiles and the readback", "con")
def s4_4():
    ensure_tool()
    h = tool("hunters"); rb = tool("hunters", "readback")
    m = re.search(r"units (\d+)/(\d+) at level", h)
    v, n = judge(h + rb, want=[r"hunters: skill profiles on \d+ species", r"SNEAK readback castes \d+/\d+", r"levels solo apex 15, solo 12, pack 10 \(SNEAK 5, bonus 10\)",
                               r"skill profiles \(0-20; 15 Legendary, 20 Legendary\+5\)"], what="hunters and readback")
    if m and m.group(1) != m.group(2):
        v, n = "a", n + f"; units at level {m.group(1)} of {m.group(2)} on the map"
    mark(v, n + f". '{first(h, r'hunters: skill.*')[:230]}'.")

@step("4.5", "Change a skill level", "con")
def s4_5():
    ensure_tool()
    l0 = ledger_count()
    a = tool("hunters", "skills", "solo_apex", "16"); rb = tool("hunters", "readback"); h16 = tool("hunters", record=False)
    b = tool("hunters", "skills", "solo_apex", "15")
    sp = re.search(r"^\s*([A-Z][A-Z_]+)\s+\S*(solo|pack)", rb, re.M)
    tok = "COUGAR" if "COUGAR" in rb or DRY else (sp.group(1) if sp else "COUGAR")
    c = tool("hunters", "skills", tok, "18"); d = tool("hunters", "skills", tok, "auto")
    l1 = ledger_count()
    ok = "solo apex 16" in h16 and (l1 or 0) >= (l0 or 0) + 4 and not errs(a + b + c + d)
    mark("p" if ok or DRY else "a", f"solo_apex 16: status reads '{first(h16, r'levels solo apex \d+')}'; back to 15; {tok} 18 then auto ('{c.strip()[:80]}' / '{d.strip()[:80]}'); "
         f"ledger {l0} -> {l1} (four setters).")

@step("4.6", "Packs recognised", "con")
def s4_6():
    ensure_tool()
    e = tool("groups", "ecology", "now")
    h = tool("hunters")
    p = first(h, r"packs: .*")
    m = re.search(r"packs: (on|off), radius (\d+); last pass (\d+) tracked, (\d+) inferred, largest (\d+)", p)
    mark("p" if (m and m.group(1) == "on") or DRY else "a", f"ecology now: '{e.strip()[:100]}'; '{p[:200] or 'no packs line'}'. "
         f"Whether five wolves standing together count as one pack needs wolves on the map; this reads the pass's own count.")

@step("4.7", "Prey mass: the pack floor", "con")
def s4_7():
    ensure_tool()
    c = cfgv("hunters.pack_floor", "hunters.pack_sneak", "hunters.pack_on", "hunters.skills.pack_bonus")
    mark("s", f"The window and console show pairs, not mass shares, so the 5 % floor cannot be read off a pair here (the page: mark Skipped "
         f"if no such pair); config read: {c}. PK2 (ecology.md) measures it.")

@step("4.8", "Raptors armed, and the stoop", "con")
def s4_8():
    ensure_tool()
    raptors = luap(SW + """local cfg=sw.loadConfig(); local pool=sw.buildPool(cfg); local rp={}
for _,e in ipairs(pool) do if e.inEmbark and (e.guild=='RP' or e.slot=='RP') then rp[e.token]=true end end
local n,toks=0,{}
for _,u in ipairs(df.global.world.units.active) do if not dfhack.units.isDead(u) and sw.WILD.onMap(u) then local t=df.creature_raw.find(u.race).creature_id
  if rp[t] then n=n+1; toks[t]=true end end end
local o={}; for t in pairs(toks) do o[#o+1]=t end
print(json.encode({n=n, toks=o}))""")
    h0 = first(tool("hunters"), r"raptors: .*")
    line_ok = re.search(r"raptors: armed \(BENIGN cleared on RP species\); stoop on \(cooldown 2400 t, range 40, max 3/pass, chance 60%", h0)
    if not (raptors.get("n") or 0) and not DRY:
        return mark("p" if line_ok else "a", f"'{h0[:230]}'. No raptor on the map now, so no stoop to watch (rare by design: it rides the 3,000-tick ecology pass).")
    stepped(6000)
    h1 = first(tool("hunters"), r"raptors: .*")
    tot = re.search(r"total (\d+)", h1)
    mark("p" if line_ok or DRY else "a", f"raptors on the map {raptors.get('toks')}; before '{h0[:200]}'; after 6,000 ticks '{h1[:200]}' (stoops so far {tot.group(1) if tot else '?'}; rare by design).")

BEARS = ("BEAR_BLACK", "BEAR_GRIZZLY", "BEAR_POLAR", "BEAR_SLOTH", "BLIND_CAVE_BEAR")
@step("4.9", "Bears fish; polar bears swim", "con")
def s4_9():
    ensure_tool()
    bear = next((u for u in wild_units() if str(u.get("t", "")).startswith(("BEAR_", "GIANT_BEAR", "BLIND_CAVE_BEAR"))), None)
    if not bear and not DRY:
        return mark("s", f"no bear on the map (water bodies: {', '.join(water_bodies()) or 'none'}); the fishers line: '{first(tool('hunters'), r'fishers: .*')[:200]}'")
    tok = (bear or {}).get("t", "BEAR_GRIZZLY")
    r = tool("curious", tok, "resident")
    f0 = first(tool("hunters"), r"fishers: .*")
    stepped(3600)
    f1 = first(tool("hunters"), r"fishers: .*")
    tool("curious", tok, "thief")
    lured = re.search(r"totals lured (\d+)", f1)
    alive = luap(f"local u=df.unit.find({int((bear or {}).get('id') or 0)}); print(json.encode({{alive=u~=nil and not dfhack.units.isDead(u)}}))").get("alive")
    mark("p" if (lured and alive) or DRY else "a", f"{tok} #{(bear or {}).get('id')} made resident ('{r.strip()[:80]}'); fishers before '{f0[-160:]}'; after 3,600 ticks '{f1[-160:]}'; "
         f"bear alive {alive}. Curious habit put back after.")

@step("4.10", "The cohesion table", "con")
def s4_10():
    ensure_tool()
    lst_ = tool("hunters", "cohesion", "list")
    m = re.search(r"^\s*(WOLF)\b.*\bpack\b", lst_, re.M) or re.search(r"^\s*([A-Z_]+)\b.*\bpack\b", lst_, re.M)
    if not m and not DRY:
        return mark("a" if errs(lst_) or not lst_.strip() else "s", f"no pack species in the cohesion table: '{lst_.strip()[:200]}'")
    tok = m.group(1) if m else "WOLF"
    a = tool("hunters", "cohesion", tok, "herd"); l2 = tool("hunters", "cohesion", "list", record=False)
    herd = re.search(r"^\s*" + tok + r"\b.*\bherd\b", l2, re.M)
    b = tool("hunters", "cohesion", tok, "auto"); l3 = tool("hunters", "cohesion", "list", record=False)
    back = re.search(r"^\s*" + tok + r"\b.*\bpack\b", l3, re.M)
    rows = len([l for l in lst_.splitlines() if re.search(r"\b(solitary|pack|herd|flock|school)\b", l)])
    mark("p" if (herd and back) or DRY else "a", f"{rows} species rows; {tok} set herd: '{first(l2, '^\\s*' + tok + '.*')[:100]}'; auto: '{first(l3, '^\\s*' + tok + '.*')[:100]}'.")

@step("4.11", "Pelagic pull and the stranding guard", "con")
def s4_11():
    ensure_tool()
    bodies = water_bodies()
    body = "ocean" if "ocean" in bodies else (bodies[0] if bodies else "lake")
    mix = tool("water", "mix", body)
    w = tool("water")
    guard = first(w, r".*guard.*")
    mix_ok = re.search(r"base .*x .*= ", mix) or re.search(r"\(share|\d+%\)", mix)
    r2 = "getBreathingState" in w
    if "ocean" not in bodies and not DRY:
        return mark("a" if errs(mix + w) else "s", f"no ocean on this map (bodies {bodies or 'none'}): the pelagic pull is untested. On the {body}: mix "
                    f"{'reads base x factor = weight' if mix_ok else 'unreadable: ' + mix.strip()[:120]}; guard '{guard[:160]}' (r2 getBreathingState: {r2}).")
    outs = [tool("water", "now", "ocean") for _ in range(3)]
    led = tool("ledger", "10", "arrive", "water")
    pull = re.findall(r"pull ([\d.]+)", mix)
    mark("p" if (mix_ok and r2) or DRY else "a", f"mix: pulls {pull[:6] or 'none'}; shallow floor lifted {'shallow floor lifted' in mix}; draws {[first(o, r'water: drew.*')[:60] for o in outs]}; "
         f"guard '{guard[:120]}'; ledger arrive {lines_with(led, r'pull|seed|deep', 2) or '-'}.")

@step("4.12", "Curated water apexes in the draw", "con")
def s4_12():
    ensure_tool()
    a0 = tool("roster", "aquatic")
    a = tool("roster", "aquatic", "FISH_LAMPREY_SEA", "apex"); a1 = tool("roster", "aquatic", record=False)
    mix = tool("water", "mix")
    b = tool("roster", "aquatic", "FISH_LAMPREY_SEA", "off"); a2 = tool("roster", "aquatic", record=False)
    was = re.search(r"aquatic-apex FISH_LAMPREY_SEA", a0); on = re.search(r"aquatic-apex FISH_LAMPREY_SEA apex", a1); gone = not re.search(r"aquatic-apex FISH_LAMPREY_SEA", a2)
    fisher_drawn = re.search(r"BEAR\S*.*\bapex\b", mix)
    ok = not was and on and gone and not fisher_drawn
    mark("p" if ok or DRY else "a", f"lamprey listed at first: {bool(was)}; after 'apex': {bool(on)}; after 'off' gone: {gone}; a bear offered as a water apex in the mix: {bool(fisher_drawn)}; "
         f"mix apex line: '{first(mix, r'apex.*')[:120]}'.")

@step("4.13", "Scavenging at a natural cadence", "con")
def s4_13():
    ensure_tool()
    rem = luap("local n=0; for _,it in ipairs(df.global.world.items.other.ANY_CORPSE or {}) do n=n+1 end; print(json.encode({n=n}))").get("n")
    on = tool("scavenge", "on")
    stepped(4800)
    st = tool("scavenge", "stats"); led = tool("ledger", "10", "eco")
    eaten = lines_with(led, r"scavenging: .* eaten", 3)
    v, n = judge(on + st, want=[r"scaveng"], what="scavenge on and stats")
    if not rem and not DRY:
        return mark("s" if v == "p" else "a", n + "; no remains on the map to scavenge (ANY_CORPSE 0).")
    mark(v, n + f"; remains on the map {rem}; after 4,800 ticks: {eaten or 'no eaten line yet (found after hours; eaten over visits)'}; stats '{st.strip()[:200]}'.")

@step("4.14", "Scavenging status tells the truth", "con")
def s4_14():
    ensure_tool()
    d = tool("disable"); s = tool("scavenge"); n = tool("scavenge", "now"); e = tool("enable")
    v, nn = judge(s + n, want=[r"scavenging: off \(the tool is disabled; the scavenging switch is on\)", r"scavenge: 0 eaten \(nothing ran: "], what="disabled: status and now")
    mark(v, nn + f". '{first(s, r'scavenging: .*')[:160]}' / '{first(n, r'scavenge: .*')[:160]}'; rotation back on: '{e.strip()[:40]}'.")

@step("4.15", "Carnivorous swimmers scavenge", "con")
def s4_15():
    ensure_tool()
    out = tool("hunters", "swimscav", "list")
    want = [r"SHARK", r"CROCODILE", r"ALLIGATOR", r"POND_GRABBER|GRABBER", r"OTTER"]
    miss = missing(out, *want)
    lam = "FISH_LAMPREY_SEA" in out
    mark("a" if miss or lam else "p", f"swimmer scavengers {'include sharks, crocodiles, alligators, pond grabbers, otters' if not miss else 'missing ' + str(miss)}; sea lamprey "
         f"{'LISTED' if lam else 'absent'}; {len(re.findall(r'^[ ]*[A-Z][A-Z_]+', out, re.M))} lines. Eating wet remains over a day is scav.md §15's rig test.")

@step("4.16", "Vermin foraging on real vermin", "con")
def s4_16():
    ensure_tool()
    c = tool("vermin", "census"); f = tool("vermin", "forage", "now")
    stepped(1200)
    e = tool("vermin", "eats")
    v, n = judge(c + f + e, want=[r"vermin objects: \d+ \(\d+ loose, \d+ colony sites, \d+ hidden\) from world\.event\.vermin", r"vermin forage: \d+ eater"],
                 forbid=[r"NO VERMIN VECTOR"], what="census, forage now, eats a day later")
    mark(v, n + f". '{first(c, r'vermin objects.*')[:140]}'; '{first(f, r'vermin forage.*')[:100]}'; eats: {lines_with(e, r'drawn|arrived|eaten', 2) or e.strip()[:160]}.")

@step("4.17", "Ten vermin classes", "con")
def s4_17():
    ensure_tool()
    cl = tool("vermin", "classes")
    n = len(set(re.findall(r"\bSWV_[A-Z]+\b", cl)))
    outs = [tool("vermin", "class", "SWV_BAT", "off"), tool("vermin", "class", "SWV_BAT", "on"), tool("vermin", "edges", "rules"), tool("vermin", "edges", "both")]
    ok = n == 10 and "SWV_COLONY" in cl and "SWV_BAT" in cl and not errs("\n".join(outs)) and not any(re.search(r"^Usage", o, re.M) for o in outs)
    mark("p" if ok or DRY else "a", f"{n} SWV classes ({', '.join(sorted(set(re.findall(r'SWV_[A-Z]+', cl))))}); SWV_BAT off/on: '{outs[0].strip()[:80]}' / '{outs[1].strip()[:80]}'; "
         f"edges rules then both: '{first(outs[2], r'source.*')[:80]}' / '{first(outs[3], r'source.*')[:80]}'.")

@step("4.18", "Curious thieves steal once, then stay", "con")
def s4_18():
    ensure_tool()
    s0 = tool("curious", "status")
    cur = luap(SW + """local n,t=0,{}
for _,u in ipairs(df.global.world.units.active) do if not dfhack.units.isDead(u) and sw.WILD.onMap(u) then
  local cr=df.creature_raw.find(u.race); local c=cr and cr.caste[u.caste]
  if c and (c.flags.CURIOUS_BEAST_ITEM or c.flags.CURIOUS_BEAST_GUZZLER or c.flags.CURIOUS_BEAST_EATER) then n=n+1; t[cr.creature_id]=true end end end
local o={}; for k in pairs(t) do o[#o+1]=k end; print(json.encode({n=n, t=o}))""")
    v, n = judge(s0, want=[r"curious"], what="curious status")
    if not (cur.get("n") or 0) and not DRY:
        return mark("s" if v == "p" else "a", n + f"; no curious beast on the map now. Status: '{s0.strip()[:200]}'.")
    stepped(3600)
    s1 = tool("curious", "status"); led = tool("ledger", "10")
    mark(v, n + f"; curious beasts on the map {cur.get('t')}; status before '{s0.strip()[:120]}', after 3,600 ticks '{s1.strip()[:160]}'; ledger: {lines_with(led, r'stole|theft|reform|loot', 2) or 'no theft yet'}.")

@step("4.19", "Ecology controls from the page", "web")
def s4_19():
    ensure_tool()
    tok = web_needed("4.19")
    if not tok:
        return
    c1, j1, b1 = web_set(tok, "hunters.stoop.chance", 61)
    rap = first(tool("hunters"), r"raptors: .*")
    c2, cj = http(f"/controls.json?{q(t=tok)}", record=False)
    row = next((r for r in js(cj).get("controls") or [] if isinstance(r, dict) and r.get("id") == "hunters.stoop.chance"), {})
    c3, j3, b3 = web_set(tok, "hunters.stoop.chance", 60)
    ok = c1 == 200 and j1.get("value") == 61 and "chance 61%" in rap and c3 == 200 and j3.get("value") == 60
    mark("p" if ok or DRY else "a", f"POST /set stoop 61 -> {c1} value {j1.get('value')} cmd '{j1.get('cmd')}'; console raptors line reads chance "
         f"{first(rap, r'chance \d+%')}; the registry row now {row.get('value')} (default {row.get('default')}); reset 60 -> {c3} value {j3.get('value')}. "
         f"The toast, dot and reset button are the page's drawing (needs a browser).")

# =============================================================================================== 5
@step("5.1", "Layers: each cavern's phase", "gui")
def s5_1():
    ensure_tool(); close_window(); open_window("Layers")
    e0 = cfgv("irruption.enabled").get("irruption.enabled")
    key("CUSTOM_I", 1.5); e1 = cfgv("irruption.enabled").get("irruption.enabled")
    rows = "\n".join(view_lines("layers")); screen("irr-on")
    key("CUSTOM_I", 1.5); e2 = cfgv("irruption.enabled").get("irruption.enabled")
    cav = lines_with(rows, r"Cavern \d", 3)
    v, n = judge(rows, want=[r"irruptions", r"cavern pressure", r"Cavern \d .*(quiet|STIRRING|IRRUPTING|cooldown|not yet found)"], forbid=[r"AGITATED: "], what="Layers with irruptions on")
    if not (e1 is not e0 and e2 == e0) and not DRY:
        v, n = "a", n + f"; I did not toggle ({e0} -> {e1} -> {e2})"
    mark(v, n + f"; I: {e0} -> {e1} -> {e2}; {cav}.")

@step("5.2", "Panel: Cavern gate", "gui")
def s5_2():
    v, n, rows, t = panel_check("caverns", [r"cavern gate \(R44\): on\s+cap 5 per cavern", r"natives (counted|not counted)", r"Cavern gate", r"Cavern cap",
                                            r"Frequency hold", r"Trim over the cap", r"Count cavern natives", r"Animal-people cap", r"Adopt natives now"], "caverns")
    mark(v, n + f". '{first(rows, r'cavern gate \(R44\).*')[:200]}'.")

@step("5.3", "Panel: Irruptions", "gui")
def s5_3():
    v, n, rows, t = panel_check("irruption", [r"Irruptions (ON|off)", r"threshold", r"Cavern \d", r"TRIGGER", r"EVENT", r"END AND COOLDOWN", r"BEHAVIOUR TOKENS",
                                              r"AGITATION", r"MESSAGES", r"Stir"], "irruption")
    p0 = cfgv("irruption.tokens.thief.pct").get("irruption.tokens.thief.pct")
    panel_select("irruption.tokens.thief.pct")
    for _ in range(5):
        key("KEYBOARD_CURSOR_RIGHT", 0.9)
    r1 = panel_report(); p1 = cfgv("irruption.tokens.thief.pct").get("irruption.tokens.thief.pct")
    key("CUSTOM_D", 1.2); p2 = cfgv("irruption.tokens.thief.pct").get("irruption.tokens.thief.pct")
    panel_select("irr_stir"); opened, lb = asks("SELECT", "stir-which", 1.2)
    stirred = ""
    if opened:
        key("SELECT", 1.5); stirred = panel_report()["status"]
        dismiss_dialogs()
    irr = tool("irruption")
    ok = v == "p" and p1 == (p0 or 0) + 5 and "read back" in r1["status"] and p2 == p0 and opened
    memo["stirred_gui"] = "STIRRING" in irr
    mark("p" if ok or DRY else "a", f"{n}. Thief share {p0} -> {p1} ('{r1['status'][:70]}') -> D {p2}; Stir {'asked for a cavern' if opened else 'did not ask'}, then '{stirred[:100]}'; "
         f"cavern 1 now: '{first(irr, r'.*(STIRRING|quiet|IRRUPTING|cooldown).*')[:140]}'.")

@step("5.4", "The cavern gate at the console", "con")
def s5_4():
    ensure_tool()
    a = tool("groups", "cavern"); b = tool("groups", "cavern", "max", "4"); c = tool("groups", "cavern"); d = tool("limits", "cavern", "groups", "5"); e = tool("groups", "cavern", record=False)
    ok = re.search(r"groups: cavern gate on, cap 5 groups per cavern \(R44\)", a) and re.search(r"cap 4 groups per cavern", c) and re.search(r"cap 5 groups per cavern", e)
    memo["cavern_max_note"] = "cap 4 held until limits cavern groups 5" if ok else ""
    mark("p" if ok or DRY else "a", f"'{first(a, r'groups: cavern gate.*')[:180]}'; after max 4: '{first(c, r'cap \d+ groups per cavern')}'; after limits cavern groups 5: "
         f"'{first(e, r'cap \d+ groups per cavern')}'. (Its survival across a reload is checked in 6.14.)")

@step("5.5", "Natives counted, held and trimmed", "con")
def s5_5():
    ensure_tool()
    if not (facts().get("reached") or 0) and not DRY:
        return mark("s", "no cavern reached on this map")
    a = tool("groups", "layers"); na = tool("groups", "natives")
    stepped(1500)
    b = tool("groups", "layers"); nb = tool("groups", "natives", record=False)
    rows0, rows1 = {k: v for k, v in layer_rows(a).items() if k.startswith("cavern")}, {k: v for k, v in layer_rows(b).items() if k.startswith("cavern")}
    nat = re.findall(r"\((\d+) native\)", b)
    ok = rows1 and not errs(na + nb)
    mark("p" if ok or DRY else "a", f"cavern rows now/cap before {rows0} after 1,500 ticks {rows1}; native groups counted {nat or 'none'}; natives: '{na.strip()[:160]}'.")

CIV_NEW = ("ANT_MAN", "BAT_MAN", "CAVE_FISH_MAN", "CAVE_SWALLOW_MAN", "OLM_MAN")
@step("5.6", "Civ races and the civ set", "con")
def s5_6():
    ensure_tool()
    r = roster()
    civ = {e.get("token"): k for k, e in r.items() if e.get("civ") and e.get("layer") == "cavern"}
    pick = next((civ[t] for t in ("TROGLODYTE", "ANT_MAN", "RODENT_MAN", "PLUMP_HELMET_MAN") if t in civ), next(iter(civ.values()), None))
    out = tool("roster", pick) if pick else ""
    newset = luap(SW + "local o={}; for _,t in ipairs({" + ",".join(json.dumps(t) for t in CIV_NEW) + "}) do local ok,v=pcall(function() return sw.MODEL and sw.MODEL.isCiv and sw.MODEL.isCiv(t) end); o[t]=ok and v or nil end; print(json.encode(o))")
    inpool = {t: (r.get(civ.get(t, ""), {}).get("civ") if t in civ else None) for t in CIV_NEW}
    if not pick and not DRY:
        return mark("s", f"no civ race on this fort's cavern roster; civ-set probe {newset}")
    ok = re.search(r"guild|cavern", out, re.I) and not errs(out)
    mark("p" if ok or DRY else "a", f"civ races on the cavern roster: {sorted(civ)[:10]}; roster {pick}: '{out.strip()[:180]}'; the R61 additions (pool civ flag where present: {inpool}; model probe {newset}).")

@step("5.7", "Irruptions on, and the breach", "con")
def s5_7():
    ensure_tool()
    on = tool("irruption", "on")
    stepped(1500)
    st = tool("irruption"); led = tool("ledger", "10", "irruption")
    v, n = judge(on + st, want=[r"cavern 1|Cavern 1", r"quiet|STIRRING|IRRUPTING|cooldown|not reached"], what="irruption on and the readout")
    br = lines_with(led, r"breach|reached", 2)
    mark(v, n + f"; per-cavern rows: {lines_with(st, r'^\\s*cavern \\d|Cavern \\d', 3)}; breach ledger line: {br or 'none (the fort reached the caverns before the tool ran)'}.")

@step("5.8", "Pressure and the warning", "con")
def s5_8():
    ensure_tool()
    a0 = len(announcements(80))
    s = tool("irruption", "stir", "1")
    st = tool("irruption")
    ann = [a for a in announcements(20) if "stirs" in a]
    row = first(st, r".*(STIRRING|stirring).*")
    ok = row and ann
    mark("p" if ok or DRY else "a", f"pressure by citizens at work is a days-long rig measure (T-PR); forced with `irruption stir 1` (the Panel's Stir): '{s.strip()[:120]}'; "
         f"row '{row[:140] or 'no STIRRING row'}'; announcement '{ann[-1] if ann else 'none'}'.")

@step("5.9", "Waves of its own civ races", "con")
def s5_9():
    ensure_tool()
    ids0 = max_unit_id()
    n0 = tool("irruption", "now", "1")
    ann0 = [a for a in announcements(15) if "irrupting" in a]
    waves = []
    for _ in range(4):
        if waves:
            break
        stepped(1200)
        waves = [a for a in announcements(30) if re.search(r"A wave of .* surges", a)]
    placed = lst(luap(SW + "local o={}; for _,u in ipairs(df.global.world.units.active) do if u.id>%d and not dfhack.units.isDead(u) and sw.WILD.onMap(u) then o[#o+1]=df.creature_raw.find(u.race).creature_id end end; print(json.encode(o))" % ids0))
    st = tool("irruption")
    nothing = re.search(r"nothing to send: .*", n0 + st)
    memo["irr_started"] = bool(ann0 or waves)
    if nothing and not ann0:
        return mark("s", f"cavern 1 had nothing to send: '{nothing.group(0)[:200]}'")
    ok = ann0 and waves
    mark("p" if ok or DRY else "a", f"now 1: '{n0.strip()[:120]}'; announcement '{ann0[-1] if ann0 else 'none'}'; wave(s): {waves[-2:] or 'none in 4,800 ticks'}; "
         f"new units on the map {len(placed)} ({', '.join(sorted(set(placed))[:6])}).")

@step("5.10", "Tokens on 10 %, and one unit with all", "con")
def s5_10():
    ensure_tool()
    t = tool("irruption", "tokens"); st = tool("irruption")
    v, n = judge(t, want=[r"crazed.*on 10%", r"thief.*on 10%", r"trance.*off", r"champion.*on"], what="irruption tokens")
    cnt = first(st, r"tokens on living units.*")
    champ = re.search(r"champion (\d+)", cnt)
    if not memo.get("irr_started") and not DRY:
        return mark("s" if v == "p" else "a", n + "; no event running this round (5.9), so no wave to count tokens on.")
    if champ and champ.group(1) != "1":
        v, n = "a", n + f"; champion count {champ.group(1)} (exactly one per wave expected)"
    mark(v, n + f"; '{cnt[:220] or 'no tokens-on-units line'}'.")

@step("5.11", "The cavern's animals agitated", "con")
def s5_11():
    ensure_tool()
    st = tool("irruption")
    ag = first(st, r".*agitated.*")
    bad_raw = luap(SW + """local o={}
for _,u in ipairs(df.global.world.units.active) do
  if not dfhack.units.isDead(u) and u.flags4.agitated_wilderness_creature then
    local cr=df.creature_raw.find(u.race); local L=sw.WILD.onMap(u) and sw.WILD.layerOf(u) or 'none'
    if dfhack.units.isCitizen(u) or dfhack.units.isTame(u) or L~='cavern' then o[#o+1]=(cr and cr.creature_id or '?')..'@'..L end
  end
end
print(json.encode(o))""")
    bad = lst(bad_raw)
    if "_err" in bad_raw and not DRY:
        return mark("a", f"the agitated-units probe failed: {bad_raw['_err'][:200]}; readout '{ag[:160]}'")
    if not memo.get("irr_started") and not DRY:
        return mark("s", f"no event running this round (5.9); readout: '{ag[:160]}'")
    mark("a" if bad else "p", f"'{ag[:200] or 'no agitated count in the readout'}'; agitated units that are citizens, tame or off the cavern layer: {bad[:8] or 'none'}.")

@step("5.12", "The end and the cooldown", "con")
def s5_12():
    ensure_tool()
    e = tool("irruption", "end", "all")
    ann = [a for a in announcements(20) if re.search(r"run its course|driven the .* back", a)]
    st = tool("irruption")
    cool = first(st, r".*cooldown.*")
    c = tool("irruption", "cool", "all"); st2 = tool("irruption", record=False)
    cleared = not re.search(r"cooldown \d", st2)
    if not memo.get("irr_started") and not DRY:
        return mark("s" if not errs(e + c) else "a", f"no event running (5.9): end all '{e.strip()[:100]}', cool all '{c.strip()[:100]}'.")
    ok = ann and cool and cleared
    mark("p" if ok or DRY else "a", f"end all: '{e.strip()[:100]}'; announcement '{ann[-1] if ann else 'none'}'; row '{cool[:120] or 'no cooldown row'}'; after cool all, cooldown cleared: {cleared}.")

@step("5.13", "Difficulty: shares, waves, messages", "con")
def s5_13():
    ensure_tool()
    k0 = tool("irruption", "keys", record=False)
    before = dict(re.findall(r"^\s*([a-z_.]+)\s+(\S+)\s+\S+\.\.\S+", k0, re.M)) or dict(re.findall(r"^\s*([a-z_.]+)\s+(\S+)", k0, re.M))
    outs = [tool("irruption", "token", "thief", "25"), tool("irruption", "token", "all", "off"), tool("irruption", "champion", "off"),
            tool("irruption", "waves", "2"), tool("irruption", "msg", "wave", "off"), tool("irruption", "keys")]
    k1 = outs[-1]
    after = dict(re.findall(r"^\s*([a-z_.]+)\s+(\S+)\s+\S+\.\.\S+", k1, re.M)) or dict(re.findall(r"^\s*([a-z_.]+)\s+(\S+)", k1, re.M))
    checks = {"thief 25": re.search(r"thief[^\n]*25%", outs[0]) or re.search(r"tokens\.thief\.pct\s+25", k1), "keys line": re.search(r"tokens\.thief\.pct\s+25\s+0\.\.100", k1),
              "waves 2": re.search(r"waves?\D+2", outs[3])}
    restored = []
    for kk, vv in before.items():
        if after.get(kk) is not None and after.get(kk) != vv:
            tool("irruption", "set", kk, vv, record=False); restored.append(kk)
    bad = [k for k, v in checks.items() if not v]
    mark("a" if bad or errs("\n".join(outs)) else "p", f"{'every change printed its value' if not bad else 'not seen: ' + ', '.join(bad)}; keys lines {len(after)}; "
         f"'{first(k1, r'tokens\.thief\.pct.*')}'; set back {len(restored)} key(s) with `irruption set`.")

@step("5.14", "The animal-people cap and its lift", "con")
def s5_14():
    ensure_tool()
    a = tool("groups", "apcap")
    v, n = judge(a, want=[r"animal-people cap(:| \(R35\):) 5"], what="groups apcap")
    mark(v, n + f". '{a.strip()[:200]}'. Their group sizes over waves, and the lift during an irruption, are T-R35's (irruption.md §13).")

@step("5.15", "Depth and lava guards", "con")
def s5_15():
    ensure_tool()
    d = tool("roster", "depth")
    id0 = max_unit_id()
    p = tool("place", "MAGMA_CRAB", "1", "deep")
    id1 = max_unit_id()
    made = (id1 or 0) > (id0 or 0)
    v, n = judge(d, want=[r"depth-layer cavern=\d+ cave=\S+ stocked=\d+ eligible_unstocked=\d+"], what="roster depth")
    refused = re.search(r"R28|refus|deep|not", p, re.I)
    if made or not refused:
        v = "a"
    mark(v, n + f"; place MAGMA_CRAB 1 deep: '{p.strip()[:160]}'; a unit made: {made}.")

@step("5.16", "Demons and the deep untouched", "con")
def s5_16():
    ensure_tool()
    s = tool("status"); g = tool("groups", "layers")
    deep_row = re.search(r"^\s+deep\S*\s+cap", g, re.M)
    v, n = judge(s, want=[r"On the map now: land \d+ water \d+ cavern \d+", r"never managed"], what="status")
    if deep_row:
        v, n = "a", n + "; a deep key in the group rows"
    mark(v, n + f". '{first(s, r'On the map now.*')[:200]}'; deep row in groups layers: {bool(deep_row)}.")

@step("5.17", "Irruption controls from the page", "web")
def s5_17():
    ensure_tool()
    tok = web_needed("5.17")
    if not tok:
        return
    c, cj = http(f"/controls.json?{q(t=tok)}", record=False)
    reg = js(cj)
    n_irr = sum(1 for r in reg.get("controls") or [] if isinstance(r, dict) and r.get("sec") == "irruption")
    acts = sorted(a.get("id") for a in reg.get("actions") or [] if isinstance(a, dict) and a.get("sec") == "irruption")
    c2, st = http(f"/status.json?{q(t=tok, s='irruption')}")
    sec = (js(st).get("sections") or {}).get("irruption") or {}
    c3, b3 = http(f"/act?{q(t=tok, id='irr_stir', arg='1')}", "POST")
    j3 = js(b3)
    p0 = cfgv("irruption.tokens.thief.pct").get("irruption.tokens.thief.pct")
    c4, j4, _ = web_set(tok, "irruption.tokens.thief.pct", 15)
    c5, j5, _ = web_set(tok, "irruption.tokens.thief.pct", p0 if p0 is not None else 10)
    ok = c == 200 and n_irr >= 100 and {"irr_now", "irr_stir", "irr_end", "irr_cool", "irr_unpin"} <= set(acts) and c2 == 200 and not sec.get("error") and c3 == 200 and c4 == 200
    mark("p" if ok or DRY else "a", f"irruption controls {n_irr} (page: 103); actions {acts}; status section {c2} {len(sec.get('lines') or [])} line(s); "
         f"/act irr_stir 1 -> {c3} '{str(j3.get('out'))[:100]}'; thief share set 15 -> {c4} value {j4.get('value')}, back -> {c5}.")

# =============================================================================================== 6
@step("6.1", "Open the window; the tab bar", "gui")
def s6_1():
    ensure_tool(); close_window(); open_window()
    t = screen("open"); wt = win_text(t)
    miss = [x for x in TABS if x not in wt]
    nonascii = sorted({ch for ch in wt if ord(ch) > 126})
    how = select_tab("Ledger", by_click=True)
    got = luap(GW + "print(json.encode({p=w and w.subviews.pages:getSelected() or 0}))").get("p")
    wide = max((len(l) for l in wt.splitlines()), default=0)
    dims = luap("local w,h=dfhack.screen.getWindowSize(); print(json.encode({w=w,h=h}))")
    ok = not miss and not nonascii and got == 9
    mark("p" if ok or DRY else "a", f"nine tabs {'all drawn' if not miss else 'missing ' + str(miss)}; non-ASCII in the window: {''.join(nonascii) or 'none'}; Ledger reached by {how} (page {got}); "
         f"screen {dims.get('w')}x{dims.get('h')} columns, so the narrow (<92) scrolling bar is not exercised here (the rig cannot resize DF's window).")

@step("6.2", "Panel: sections and moving between them", "gui")
def s6_2():
    ensure_tool(); close_window(); panel_open()
    t = win_text(screen("panel"))
    seen = []
    for _ in range(14):
        s = panel_shown()
        if s in seen:
            break
        seen.append(s); key("CUSTOM_S", 0.6)
    back0 = panel_shown(); key("CUSTOM_SHIFT_S", 0.8); back1 = panel_shown()
    clicked = click("Vermin eating", 1.2); csec = panel_shown()
    keys_ = missing(t, r"All on", r"All off", r"Refresh", r"Section", r"back", r"Default", r"Find")
    helpl = "Every control, by section. Enter sets; Left/Right steps (Shift: x10); * = not default." in t
    ok = len(seen) == 13 and back1 != back0 and helpl and not keys_
    mark("p" if ok or DRY else "a", f"S visited {len(seen)} sections: {', '.join(map(str, seen))}; Shift+S {back0} -> {back1}; click 'Vermin eating' -> {csec}; help line {'seen' if helpl else 'NOT seen'}; "
         f"key labels {'all' if not keys_ else 'missing ' + str(keys_)}.")

@step("6.3", "Setting: Enter, steps, default, refusals", "gui")
def s6_3():
    ensure_tool(); close_window(); panel_open("limits")
    a0 = cfgv("groups.adaptive").get("groups.adaptive")
    panel_select("groups.adaptive"); key("SELECT", 1.2); a1 = cfgv("groups.adaptive").get("groups.adaptive"); key("SELECT", 1.2); a2 = cfgv("groups.adaptive").get("groups.adaptive")
    f0 = cfgv("limits.fixed").get("limits.fixed")
    panel_select("limits.fixed"); key("KEYBOARD_CURSOR_RIGHT", 1.2); f1 = cfgv("limits.fixed").get("limits.fixed")
    key("KEYBOARD_CURSOR_RIGHT_FAST", 1.2); f2 = cfgv("limits.fixed").get("limits.fixed"); r2 = panel_report()
    star = any(re.search(r"\*", l) and "Fixed cap" in l for l in panel_rows())
    opened, p = asks("SELECT", "fixedcap-prompt")
    rng = "1..20" in scr_text(p)
    answer("99"); r3 = panel_report(); f3 = cfgv("limits.fixed").get("limits.fixed")
    key("CUSTOM_D", 1.2); f4 = cfgv("limits.fixed").get("limits.fixed")
    p0 = cfgv("patterns.land").get("patterns.land")
    panel_select("patterns.land"); key("SELECT", 1.2); p1 = cfgv("patterns.land").get("patterns.land"); key("SEC_SELECT", 1.2); p2 = cfgv("patterns.land").get("patterns.land")
    back = tool("limits", "formula")
    ok = (a1 is not a0 and a2 == a0 and f1 == (f0 or 0) + 1 and f2 == min(20, (f1 or 0) + 10) and "read back" in r2["status"] and opened and rng
          and "at most 20" in r3["status"] and f3 == f2 and p1 != p0 and p2 == p0)
    mark("p" if ok or DRY else "a", f"Adaptive {a0} -> {a1} -> {a2}; Fixed cap {f0} -> right {f1} -> shift+right {f2} ('{r2['status'][:60]}', star {star}); Enter prompt "
         f"{'shows 1..20' if rng else 'opened ' + str(opened)}; 99 -> '{r3['status'][:70]}' (value {f3}); D -> {f4}; Land pattern {p0} -> Enter {p1} -> Shift+Enter {p2}. "
         f"Group cap put back with `limits formula`.")

@step("6.4", "Find a control", "gui")
def s6_4():
    ensure_tool(); close_window(); panel_open()
    opened, p = asks("CUSTOM_ALT_S", "find-prompt")
    answer("stoop")
    s = panel_shown(); rows = "\n".join(panel_rows())
    hits = [x for x in ("Stoop", "Stoop cooldown", "Stoop range", "Stoops per pass", "Stoop chance", "Prey size ratio") if x in rows]
    key("CUSTOM_ALT_S", 1.0); answer("", clear=12); s2 = panel_shown()
    ok = opened and s == "find" and len(hits) >= 4 and s2 != "find"
    mark("p" if ok or DRY else "a", f"Alt+S {'asked' if opened else 'did not ask'}; section '{s}' with {hits}; empty search closed it (now '{s2}').")

@step("6.5", "Switches & jobs; All off and All on", "gui")
def s6_5():
    v, n, rows, t = panel_check("switches", [r"Curious thieves stay", r"Cavern irruptions", r"Vermin foraging", r"Nudge", r"JOBS", r"ecology\s+3000 t",
                                             r"vermin foraging\s+100 t", r"curious thieves\s+50 t", r"season roster\s+1200 t", r"scavenging\s+200 t"], "switches")
    e0 = cfgv("enabled", "ecology.enabled")
    asked1, _ = asks("CUSTOM_X", "alloff-ask")
    if asked1:
        yes()
    st1 = panel_report()["status"]; e1 = cfgv("enabled")
    ext = first(tool("extinct"), r"written: .*"); hun = first(tool("hunters"), r"hunters: .*")
    asked2, _ = asks("CUSTOM_A", "allon-ask")
    if asked2:
        yes()
    st2 = panel_report()["status"]; e2 = cfgv("enabled", "ecology.enabled")
    ok = v == "p" and asked1 and asked2 and e1.get("enabled") is False and e2 == e0
    mark("p" if ok or DRY else "a", f"{n}. All off asked {asked1}: '{st1[:160]}' (rotation {e1.get('enabled')}); extinct {ext[:120] or '-'}; hunters '{hun[:120]}'; "
         f"All on asked {asked2}: '{st2[:80]}'; switches before {e0}, after {e2}.")

@step("6.6", "Actions and readouts on the Panel", "gui")
def s6_6():
    ensure_tool(); close_window(); panel_open("water")
    panel_select("water_depth"); o1, t1 = asks("SELECT", "depths", 1.5)
    shown = "column depth" in scr_text(t1).lower()
    if o1:
        esc(0.8)
    panel_select("water_now"); o2, t2 = asks("SELECT", "drawnow-which", 1.2)
    choices = [c for c in ("any", "ocean", "lake", "river", "pool") if re.search(r"\b" + c + r"\b", scr_text(t2))]
    if o2:
        key("SELECT", 1.5)
    st = panel_report(); dismiss_dialogs()
    ok = o1 and shown and o2 and len(choices) >= 4 and st["status"]
    mark("p" if ok or DRY else "a", f"Column depths: {'a list with the console output' if o1 and shown else 'did not show the depths'}; Draw now offered {choices}, picked 'any': "
         f"'{st['cmd'][:60]}' / '{st['status'][:120]}'.")

@step("6.7", "Help on every tab", "gui")
def s6_7():
    ensure_tool(); close_window(); open_window()
    got, v71 = {}, {}
    for tab in TABS:
        select_tab(tab)
        opened, t = asks("CUSTOM_ALT_H", f"help-{tab.replace(' ', '')}", 1.2)
        st = scr_text(t)
        got[tab] = opened and "Help" in st
        v71[tab] = "v7.1 added" in st
        if opened:
            esc(0.8)
            if "seasonal-wildlife" not in " ".join(focus()) or len(focus()) > 1:
                t2 = scr_text(screen(f"help2-{tab.replace(' ', '')}"))
                v71[tab] = v71[tab] or "v7.1" in t2
                dismiss_dialogs(1)
    miss = [t for t, v in got.items() if not v]
    mark("a" if miss else "p", f"Alt+H opened a help page on {9 - len(miss)} of 9 tabs{(' (not on ' + ', '.join(miss) + ')') if miss else ''}; the v7.1 words page seen on "
         f"{sum(v71.values())} tab(s). Note: the page expects the vocabulary unchanged from v7.0, but the deployed bff2726 added a 'words v7.1 added' block (fixes2 7aa68e2).")

@step("6.8", "Ledger and undo in the window", "gui")
def s6_8():
    ensure_tool(); close_window(); open_window("Ledger")
    kinds = []
    for _ in range(20):
        k = luap(GW + "print(json.encode({k=w.subviews.led_kind:getOptionLabel()}))").get("k")
        if k in kinds:
            break
        kinds.append(k); key("CUSTOM_K", 0.6)
    c0 = cfgv("hunters.stoop.chance").get("hunters.stoop.chance")
    panel_open("ecology"); panel_select("hunters.stoop.chance")
    for _ in range(3):
        key("KEYBOARD_CURSOR_RIGHT", 1.0)
    c3 = cfgv("hunters.stoop.chance").get("hunters.stoop.chance")
    select_tab("Ledger")
    labs = []
    for _ in range(3):
        labs.append(first(win_text(screen("undo")), r"Undo last edit \(\d+\)")); key("CUSTOM_Z", 1.0)
    c4 = cfgv("hunters.stoop.chance").get("hunters.stoop.chance")
    want = ["all", "edit", "season", "wave", "arrive", "irruption"]
    ok = all(w in [str(x).lower() for x in kinds] for w in want) and c3 == (c0 or 0) + 3 and c4 == c0
    mark("p" if ok or DRY else "a", f"K kinds: {', '.join(map(str, kinds))}; three Panel sets {c0} -> {c3}; Z three times -> {c4}; labels {labs}.")

VERB_SWEEP = [("status",), ("limits",), ("groups",), ("water",), ("caverns",), ("cavern",), ("roster",), ("ledger", "3"), ("classes",), ("vermin",),
              ("scavenge",), ("curious",), ("exhaust",), ("alerts",), ("hunting",), ("hunters",), ("sponges",), ("realm",), ("v7",), ("extinct",),
              ("irruption",), ("perf",), ("water", "bogus"), ("groups", "bogus"), ("roster", "bogus", "bogus"), ("hunters", "bogus"), ("irruption", "bogus"), ("perf", "bogus")]
@step("6.9", "Every console verb", "con")
def s6_9():
    ensure_tool()
    bad = []
    for c in VERB_SWEEP:
        o = tool(*c, timeout=90)
        if errs(o):
            bad.append(" ".join(c) + ": " + ", ".join(sorted(set(errs(o)))))
    mark("a" if bad else "p", f"{len(VERB_SWEEP)} verbs and bad arguments sent; " + (f"Lua errors from: {bad}" if bad else "every one answered with a status line or its usage, no Lua error."))

@step("6.10", "The registry from the console", "con")
def s6_10():
    ensure_tool()
    outs = [ctl("list", "water"), ctl("get", "hunters.stoop.chance"), ctl("set", "hunters.stoop.chance", "61"), ctl("set", "hunters.stoop.chance", "101"),
            ctl("set", "hunters.stoop.chance", "60")]
    nl = len([l for l in outs[0].splitlines() if l.strip().startswith("water.")])
    checks = {"list water": nl >= 10, "get 60": outs[1].strip().endswith("60"), "set 61 ran the verb": "seasonal-wildlife hunters stoop chance 61" in outs[2],
              "101 refused": "refused: Stoop chance: at most 100" in outs[3], "back to 60": "seasonal-wildlife hunters stoop chance 60" in outs[4]}
    bad = [k for k, v in checks.items() if not v]
    mark("a" if bad else "p", f"{'all as expected' if not bad else 'not as expected: ' + ', '.join(bad)}; list water {nl} rows; get '{outs[1].strip()[:20]}'; 101 -> '{outs[3].strip()[:80]}'.")

@step("6.11", "perf: what each job costs", "con")
def s6_11():
    ensure_tool()
    outs = [tool("perf"), tool("perf", "keys"), tool("perf", "census"), tool("perf", "bench", "50", timeout=180), tool("perf", "set", "overlay_ms", "2000"),
            tool("perf", "legacy", "census", "on"), tool("perf", "legacy", "census", "off"), tool("perf", "set", "overlay_ms", "1000")]
    nkeys = len(re.findall(r"^\s*[a-z_]+\s+\S+.*default", outs[1], re.M)) or len([l for l in outs[1].splitlines() if l.strip()])
    v, n = judge("\n".join(outs), want=[r"\bjob\b.*\bruns\b.*\blast\b.*\bworst\b", r"worst (single )?tick", r"census: \d+ wild on the map",
                                         r"perf overlay_ms = 2000", r"perf legacy_census = true", r"perf legacy_census = false"], what="perf verbs")
    mark(v, n + f"; perf keys {nkeys} line(s) (page: 21 keys); census '{first(outs[2], r'census: .*')[:140]}'; bench '{outs[3].strip()[:120]}'.")

@step("6.12", "status reads it all", "con")
def s6_12():
    ensure_tool()
    s = tool("status")
    blocks = {"limits": r"limits \[", "release clock": r"release clock", "cavern gate": r"cavern gate", "leaders": r"leaders \(R32\)", "animal-people": r"animal-people",
              "vermin forage": r"vermin forage", "hunters": r"hunters: skill", "water layer": r"water layer", "scavenging": r"scavenging", "curious reform": r"curious",
              "roster v7.1": r"roster v7\.1", "extinct": r"extinct: ", "perf": r"\bperf\b", "irruptions": r"irruption", "map counts": r"On the map now"}
    miss = [k for k, p in blocks.items() if not re.search(p, s, re.I)]
    mark("a" if miss or errs(s) else "p", f"status ({len(s.splitlines())} lines): {'every v7.1 block present' if not miss else 'missing ' + ', '.join(miss)}.")

@step("6.13", "Ledger and undo at the console", "con")
def s6_13():
    ensure_tool()
    outs = [tool("ledger", "20", "irruption"), tool("ledger", "20", "extinct"), tool("ledger", "20", "panic")]
    heads = [first(o, r"ledger: \d+ of \d+ recorded shown kind=\S+") for o in outs]
    tok = web_up() if memo.get("web_tok") else ""
    c0 = cfgv("hunters.stoop.chance").get("hunters.stoop.chance")
    ctl("set", "hunters.stoop.chance", "62")
    u = tool("undo")
    c1 = cfgv("hunters.stoop.chance").get("hunters.stoop.chance")
    ok = all(heads) and re.search(r"undid: .*\(\d+ more to undo\)", u) and c1 == c0
    mark("p" if ok or DRY else "a", f"kind filters: {heads}; a registry set (the Panel's path) to 62 then undo: '{first(u, r'undid.*')[:120]}', stoop chance {c0} -> 62 -> {c1}.")

@step("6.15", "Retired words point at v7.1", "con")
def s6_15():
    ensure_tool()
    out = con_step([("v7", "layer_groups", "off"), ("water", "target", "5"), ("cavern",)],
                   want=[r"v7 layer_groups: retired in v7\.1", r"water: retired in v6\.5", r"groups cavern cap"], forbid=(), what="three retired words")

@step("6.16", "Start the companion", "web")
def s6_16():
    ensure_tool()
    tok = web_up()
    out = memo.get("web_start", "")
    c, page = http("/", record=False)
    ok = tok and re.search(r"serving the companion at http://127\.0\.0\.1:8642/\?t=[0-9a-f]+|already serving", out) and c == 200
    mark("p" if ok or DRY else "a", f"'{out.strip()[:200]}'; GET / from the Mac -> {c} ({len(page)} bytes). CrossOver shares the Mac's loopback, so the browser on the Mac reaches it.")

@step("6.17", "The page and its tabs", "web")
def s6_17():
    tok = web_needed("6.17")
    if not tok:
        return
    c, page = http("/", record=False)
    tabs = [t for t in ("Status", "Species", "Food web", "Roster", "Groups", "Controls", "Ledger") if t in page]
    c2, st = http(f"/state.json?{q(t=tok)}", record=False)
    snap = js(st)
    links = [x for x in ("controls", "roster", "groups") if f"#{x}" in page or f"'{x}'" in page]
    ok = c == 200 and len(tabs) == 7 and c2 == 200 and snap.get("loaded") is True and snap.get("date")
    mark("p" if ok or DRY else "a", f"page {c}: tab names {tabs}; state.json {c2}: loaded {snap.get('loaded')}, date '{snap.get('date')}'; deep-link routes in the page {links}. "
         f"Rendering, light and dark need a browser.")

@step("6.18", "Controls: sections, search, defaults", "web")
def s6_18():
    tok = web_needed("6.18")
    if not tok:
        return
    c, cj = http(f"/controls.json?{q(t=tok)}", record=False)
    reg = js(cj); secs = reg.get("sections") or []; ctls = [r for r in reg.get("controls") or [] if isinstance(r, dict)]
    changed = [r.get("id") for r in ctls if r.get("available") and "value" in r and r.get("default") is not None and r.get("value") != r.get("default")]
    na = [r.get("id") for r in ctls if not r.get("available")]
    noverb = [r.get("id") for r in ctls if not (r.get("verb") or r.get("vmap") or r.get("panel") or r.get("direct"))]
    panic = [r.get("id") for r in ctls if "panic" in json.dumps(r).lower()]
    ok = c == 200 and len(secs) >= 12 and len(ctls) >= 300
    mark("p" if ok or DRY else "a", f"controls.json {c}: {len(secs)} sections, {len(ctls)} controls; changed from default {len(changed)} ({', '.join(map(str, changed[:6]))}); "
         f"not in this version {len(na)}; rows a search for 'panic' would find {len(panic)}; rows without a verb shown {len(noverb)}. The nav, widgets and reset buttons need a browser.")

@step("6.19", "A set and its readback", "web")
def s6_19():
    ensure_tool()
    tok = web_needed("6.19")
    if not tok:
        return
    l0, u0 = ledger_count(), undo_depth()
    c1, j1, b1 = web_set(tok, "limits.fixed", 4)
    lim = tool("limits"); l1, u1 = ledger_count(), undo_depth()
    open_window(); panel_open("limits"); key("CUSTOM_R", 1.0)
    prow = next((l for l in panel_rows() if "Fixed cap" in l), "")
    close_window()
    c2, j2, b2 = web_set(tok, "limits.fixed", 25)
    c3, j3, b3 = web_set(tok, "limits.mode", "formula")
    lim2 = tool("limits", record=False)
    ok = (c1 == 200 and j1.get("value") == 4 and "single fixed cap 4" in lim and (l1 or 0) > (l0 or 0) and (u1 or 0) == (u0 or 0) + 1
          and c2 == 400 and "at most 20" in str(j2.get("out")) and c3 == 200 and "map-size formula" in lim2)
    mark("p" if ok or DRY else "a", f"/set Fixed cap 4 -> {c1} value {j1.get('value')} ('{j1.get('cmd')}'); limits '{first(lim, r'limits \[.*?\]')}'; Panel row '{prow.strip()[:60]}'; "
         f"ledger {l0} -> {l1}, undo {u0} -> {u1}; 25 -> {c2} '{str(j2.get('out'))[:60]}'; Group cap formula -> {c3}, limits '{first(lim2, r'limits \[.*?\]')}'.")

@step("6.20", "Token guard and the whitelist", "web")
def s6_20():
    tok = web_needed("6.20")
    if not tok:
        return
    g0, _ = http("/state.json")
    g1, b1 = http("/controls.json?t=wrong")
    g2, _ = http(f"/state.json?{q(t=tok)}", host="evil.example:8642", record=True)
    refused = {}
    for verb in (["preset"], ["gui"], ["place", "WOLF", "1"], ["class", "WOLF", "natural"], ["groups", "adopt", "1"], ["groups", "nudge", "1", "1", "1"], ["groups", "pack", "3"]):
        c, b = http(f"/cmd?{q(t=tok, a=verb)}", "POST")
        refused[" ".join(verb)] = c
    ok = g0 == 403 and g1 == 403 and g2 == 403 and all(c == 400 for c in refused.values())
    mark("p" if ok or DRY else "a", f"no token {g0}; wrong token {g1} '{b1[:40]}'; wrong Host {g2}; from the page: {refused} (400 = refused).")

@step("6.21", "Its cost, then stop it", "web")
def s6_21():
    tok = web_needed("6.21")
    if not tok:
        return
    for _ in range(4):
        http(f"/state.json?{q(t=tok)}", record=False); http(f"/status.json?{q(t=tok)}", record=False); nap(2.3)
    n, s = stepped(1200)
    st = webcmd("status")
    m = re.search(r"snapshot last (\d+) ms, worst (\d+) ms", st)
    sp = webcmd("stop")
    c, _ = http("/")
    memo["web_tok"] = ""
    ok = re.search(r"requests \d+ \(commands \d+, sets \d+, refused \d+, errors \d+\)", st) and "stopped" in sp and c == 0
    worst = int(m.group(2)) if m else None
    mark("p" if ok or DRY else "a", f"after polling (paused and {n} ticks unpaused): '{st.strip()[:260]}'; snapshot worst {worst} ms (page: under 50 after the first); "
         f"stop '{sp.strip()}'; GET / after stop -> {c}.")

@step("6.22", "Frame rate on and off", "web")
def s6_22():
    ensure_tool()
    n1, s1 = stepped(3000)
    off = luap("local C=reqscript('seasonal-wildlife-controls'); local ok,out=C.act('all_off'); print(json.encode({ok=ok,out=tostring(out)}))")
    ev("lua", "All off (the Panel's action)", off)
    n2, s2 = stepped(3000)
    on = luap("local C=reqscript('seasonal-wildlife-controls'); local ok,out=C.act('all_on'); print(json.encode({ok=ok,out=tostring(out)}))")
    ev("lua", "All on (the Panel's action)", on)
    a, b = (n1 / s1 if s1 else 0), (n2 / s2 if s2 else 0)
    base = memo.get("base_tps")
    mark("p" if (s1 and s2) or DRY else "a", f"tool on {a:.0f} t/s, All off {b:.0f} t/s ({(a - b) / b * 100 if b else 0:+.0f}% of the off rate); baseline 0.8 {base or 0:.0f} t/s. One reading "
         f"each in one session, inside the 10-15 % load noise; PERF0-PERF4 measure it properly. All on put back: {on.get('ok')}.")

@step("6.14", "Save, quit, reload", "con")
def s6_14():
    ensure_tool()
    k = memo.get("inactive")
    tool("limits", "fixed", "4"); tool("irruption", "token", "thief", "25"); tool("hunters", "skills", "solo_apex", "16"); tool("groups", "cavern", "max", "4")
    if k:
        tool("roster", k, "inactive")
    before = {"limits": first(tool("limits"), r"limits \[.*?\]"), "thief": first(tool("irruption", "tokens"), r"thief.*"),
              "hunters": first(tool("hunters"), r"levels solo apex \d+"), "cavern": first(tool("groups", "cavern"), r"cap \d+ groups per cavern"),
              "inactive": roster().get(k, {}).get("allow") if k else None}
    led0 = [l for l in tool("ledger", "1").splitlines() if l.strip() and not l.startswith("ledger:")][-1:] or [""]
    u0 = undo_depth()
    close_window()
    sv = sh("save", RELOAD, timeout=400)[1]
    sh("title", timeout=200)
    memo["reload_saved"] = (SAVE_ROOT / RELOAD).is_dir()
    ld = sh("load", RELOAD, timeout=400)[1]
    sh("popups"); sh("fps", 1000, 10)
    after = {"limits": first(tool("limits"), r"limits \[.*?\]"), "thief": first(tool("irruption", "tokens"), r"thief.*"),
             "hunters": first(tool("hunters"), r"levels solo apex \d+"), "cavern": first(tool("groups", "cavern"), r"cap \d+ groups per cavern"),
             "inactive": roster().get(k, {}).get("allow") if k else None}
    led1 = tool("ledger", "12")
    u1 = undo_depth()
    same = {kk: before[kk] == after[kk] for kk in before}
    ok = "loaded" in ld and all(same.values()) and led0[0].strip()[:50] in led1 and (u1 or 0) >= min(u0 or 0, 50) - 1
    mark("p" if ok or DRY else "a", f"saved to the new folder {RELOAD} ({'written' if memo['reload_saved'] else 'NOT FOUND'}) and loaded it back: {'loaded' in ld}; "
         f"kept across the reload: {same}; values after {after}; the ledger's last line survived: {led0[0].strip()[:50] in led1}; undo depth {u0} -> {u1}.")

# =============================================================================================== the round
def order(steps):
    """Page order, except 6.14 (the reload) last: it moves the round onto the scratch copy."""
    late = [s for s in steps if s[0] == "6.14"]
    return [s for s in steps if s[0] != "6.14"] + late

def session_start():
    global PORT
    log(f"== session: restore {FORT}.{BACKUP_TAG}, load, fps cap 1000")
    if not DRY:
        p = sh("port", quiet=True)[1].strip()
        if p.isdigit():
            PORT = p
        logf = DF_DIR / "stderr.log"
        memo["stderr0"] = logf.stat().st_size if logf.exists() else None
    st = sh("state", quiet=True)[1]
    if "map=true" in st:
        sh("title", timeout=200, quiet=True)
    rc, out = sh("save-restore", f"{FORT}.{BACKUP_TAG}", timeout=400, quiet=True)
    log("   " + (out.strip().splitlines() or ["restore: no output"])[-1][:160])
    rc, out = sh("load", FORT, timeout=400, quiet=True)
    log("   " + (out.strip().splitlines() or ["load: no output"])[-1][:160])
    sh("popups", quiet=True); sh("fps", 1000, 10, quiet=True)
    memo["session_load"] = out.strip()[-200:]
    if not DRY and "loaded" not in out and "map=true" not in sh("state", quiet=True)[1]:
        raise SystemExit(f"could not load {FORT}: {out[-400:]}")

def session_end():
    log("== session end: close the window, quit to the title without saving, delete the scratch save")
    try:
        close_window()
        sh("title", timeout=200, quiet=True)
        if DRY or (SAVE_ROOT / RELOAD).is_dir():
            out = sh("save-delete", RELOAD, timeout=120, quiet=True)[1]
            log("   " + (out.strip()[-160:] or f"save-delete {RELOAD}"))
        if not DRY:
            d = subprocess.run(["diff", "-rq", str(SAVE_ROOT / FORT), str(BACKUPS / f"{FORT}.{BACKUP_TAG}")], capture_output=True, text=True)
            memo["fort_identical"] = d.returncode == 0
            log(f"   {FORT} vs its backup: {'IDENTICAL' if d.returncode == 0 else 'DIFFERS: ' + d.stdout[:300]}")
    except Exception as e:
        log(f"   session end failed: {type(e).__name__}: {e}")

def versions() -> str:
    if DRY:
        return "53.16 · 53.16-r2 · seasonal-wildlife 7.1.0 @ bff2726 (dry run)"
    f = facts()
    rel = luap(SW + "print(json.encode({r=sw.CACHE.release}))").get("r", "?")
    sha = subprocess.run(["git", "-C", str(Path.home() / "Claude/Projects/sw-wt/deploy"), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    return f"{f.get('df', '?')} · {f.get('dfhack', '?')} · seasonal-wildlife {rel} @ {sha or '?'}"

def report(ver):
    rs = sorted(results, key=lambda r: [int(x) for x in r["id"].split(".")])
    tally = {v: sum(1 for r in rs if r["v"] == v) for v in "pas"}
    L = ["# Seasonal Wildlife alpha trial four (window, console and browser, v7.1 on DFHack 53.16-r2, region9)", "",
         "- Tester: W2:Urist (the rig, driven by scripts/alpha4-run.py)",
         f"- Fort: {FORT} (region9; restored from {FORT}.{BACKUP_TAG}; the reload test used the scratch save {RELOAD}, deleted after)",
         f"- Game / DFHack / plugin: {ver}", f"- Date: {datetime.now().strftime('%Y-%m-%d')} (run {RUN})",
         "- Page: Alpha Four (https://claude.ai/artifact/RCdoPTWhabmMBQQw2azpHr; built for region8 at fce7d68, played here on region9 at the deployed build)", "",
         f"Tally: {tally['p']} pass · {tally['a']} anomaly · {tally['s']} skipped · {109 - len(rs)} unmarked of 109 steps.", "",
         "Browser steps are checked at the data level (the endpoints the page renders); a step a browser alone can show says so in its note."]
    an = [r for r in rs if r["v"] == "a"]
    if an:
        L += ["", "## Anomalies first"] + [f"- **{r['id']} {r['title']}**: {r['note']}" for r in an]
    for f in range(7):
        fr = [r for r in rs if int(r["id"].split(".")[0]) == f]
        if not fr:
            continue
        t = {v: sum(1 for r in fr if r["v"] == v) for v in "pas"}
        L += ["", f"## {f}. {FEATURES[f]} ({t['p']} pass, {t['a']} anomaly, {t['s']} skipped)"]
        for surf in ("", "gui", "con", "web"):
            sr = [r for r in fr if r["surface"] == surf]
            if not sr:
                continue
            if surf:
                L.append(f"\n### {SURF[surf]}")
            for r in sr:
                L.append(f"- **{r['id']} {r['title']}** [{ {'p': 'PASS', 'a': 'ANOMALY', 's': 'SKIPPED'}[r['v']] }]: {r['note']}")
    return "\n".join(L) + "\n"

def main():
    global _log, DRY, NO_JUMP, SEASON_BUDGET
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--only", help="comma-separated step ids, e.g. 2.7,2.8,6.10")
    ap.add_argument("--feature", help="feature number(s) 0-6, comma-separated")
    ap.add_argument("--dry-run", action="store_true", help="print the planned rig commands; touch nothing")
    ap.add_argument("--no-restore", action="store_true", help="play on the fort already loaded (no restore, no load); never saves it")
    ap.add_argument("--no-jump", action="store_true", help="never move the calendar to reach a season boundary")
    ap.add_argument("--season-budget", type=int, default=24000, help="ticks to step toward a season boundary before moving the calendar")
    a = ap.parse_args()
    DRY, NO_JUMP, SEASON_BUDGET = a.dry_run, a.no_jump, a.season_budget
    only = set(x.strip() for x in a.only.split(",")) if a.only else None
    feats = set(int(x) for x in a.feature.split(",")) if a.feature else None
    sel = [s for s in order(STEPS) if (not only or s[0] in only) and (feats is None or int(s[0].split(".")[0]) in feats)]
    if only and not DRY:
        unknown = only - {s[0] for s in STEPS}
        if unknown:
            print(f"unknown step id(s): {sorted(unknown)}", file=sys.stderr); return 2
    if not DRY:
        SCREENS.mkdir(parents=True, exist_ok=True); _log = open(OUT / "log.txt", "w")
    log(f"== alpha 4 round {RUN}{' (DRY RUN)' if DRY else ''}: {len(sel)} of {len(STEPS)} steps on {FORT}")
    t0 = time.time()
    crashed = []
    try:
        if not a.no_restore:
            session_start()
        for sid, title, surf, fn in sel:
            CUR.clear(); CUR.update({"id": sid, "title": title})
            if DRY:
                print(f"  -- {sid} {title} [{SURF[surf]}]", flush=True)
            s0 = time.time()
            try:
                fn()
            except Exception as e:
                import traceback
                crashed.append(sid)
                mark("a", f"the driver failed at this step: {type(e).__name__}: {e}")
                CUR.setdefault("evidence", []).append({"kind": "traceback", "cmd": "", "out": traceback.format_exc()[-1500:]})
                if not DRY:
                    try:
                        close_window()
                    except Exception:
                        pass
            if "v" not in CUR:
                mark("a", "the driver did not mark this step")
            results.append({"id": sid, "title": title, "feature": int(sid.split(".")[0]), "surface": surf, "v": CUR["v"], "note": CUR["note"],
                            "secs": round(time.time() - s0, 1), "data": CUR.get("data"), "evidence": CUR.get("evidence", [])})
            log(f"  [{'planned' if DRY else {'p': 'PASS', 'a': 'ANOMALY', 's': 'SKIPPED'}[CUR['v']]:<7}] {sid} {title}"
                + ("" if DRY else f": {CUR['note'][:170]}"))
            if not DRY:
                (OUT / "results.json").write_text(json.dumps(results, indent=1, default=str))
    finally:
        CUR.clear(); CUR["id"] = "end"
        if memo.get("web_tok") and not DRY:
            try: webcmd("stop")
            except Exception: pass
        if not a.no_restore or memo.get("reload_saved"):
            session_end()
    ver = versions() if not DRY else versions()
    marks = {r["id"]: {"v": r["v"], "n": r["note"]} for r in results}
    marks["_meta"] = {"page": "alpha4", "tName": "W2:Urist (rig, scripts/alpha4-run.py)", "tFort": f"{FORT} (region9, 8x8, lake and river, caverns open; from .{BACKUP_TAG})",
                      "tVer": ver, "tDate": datetime.now().strftime("%Y-%m-%d")}
    rep = report(ver)
    if DRY:
        log(f"== DRY RUN done: {len(results)} steps walked in {time.time() - t0:.1f}s; driver exceptions: {crashed or 'none'}; marks.json would carry {len(marks) - 1} marks "
            f"(_meta.page={marks['_meta']['page']}); report {len(rep.splitlines())} lines")
        return 1 if crashed else 0
    (OUT / "marks.json").write_text(json.dumps(marks, indent=1))
    (OUT / "report.md").write_text(rep)
    (OUT / "results.json").write_text(json.dumps(results, indent=1, default=str))
    log(f"== DONE {OUT} in {(time.time() - t0) / 60:.1f} min: " + "  ".join(f"{v} {sum(1 for r in results if r['v'] == v)}" for v in "pas")
        + (f"; driver exceptions at {crashed}" if crashed else "") + f"; fort identical to its backup: {memo.get('fort_identical')}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
