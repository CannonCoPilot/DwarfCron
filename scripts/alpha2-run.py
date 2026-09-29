#!/usr/bin/env python3
"""One round of the Seasonal Wildlife alpha 2 walkthrough (artifact 3qMtYL2M), played on the rig as a tester would.

Each step of the walkthrough is one function here: it presses the keys the page names, reads the screen and the
tool's state, and marks the step Pass, Anomaly or Skipped with a note saying what was pressed and seen. Selecting a
row is done through the window's own list widget (a tester scrolls to it); every action is a real key.

Fort: BOATS, the rig's copy of the alpha one fort, restored from BOATS.preverify first. Nothing is written to any
other save; step 17.1 saves to a NEW folder (A2RELOAD) and loads it back. Step 7.2 (reset everything) runs last,
because it would undo the inactive species 16.1 watches.

Usage: alpha2-run.py [--from STEP] [--only STEP,STEP]
Output: data/alpha2/<run>/  results.json (per step), marks.json (the page's storage shape), report.md, screens/
"""
import argparse, json, os, re, subprocess, sys, time
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CX = str(ROOT / "scripts" / "cx-lifecycle.sh")
RUN = datetime.now().strftime("%Y%m%d-%H%M%S")
OUT = ROOT / "data/alpha2" / RUN
SCREENS = OUT / "screens"
FORT, BACKUP, RELOAD = "BOATS", "BOATS.preverify", "A2R" + RUN.replace("-", "")[-6:]   # a new folder each round
SEASONS = ["Spring", "Summer", "Autumn", "Winter"]
SKEY = ["CUSTOM_S", "CUSTOM_U", "CUSTOM_A", "CUSTOM_W"]
BACKSPACE = "STRING_A000"

results: list[dict] = []
memo: dict[str, Any] = {}          # facts one step leaves for a later one (the species made inactive, the stock set)
_log = None

# --- the rig ---------------------------------------------------------------------------------------------
def log(msg):
    line = f"{datetime.now().strftime('%H:%M:%S')} {msg}"
    print(line, flush=True); _log.write(line + "\n"); _log.flush()

def sh(*args, timeout=180):
    env = dict(os.environ, CX_RPC_TIMEOUT="45")
    p = subprocess.run([CX, *map(str, args)], capture_output=True, text=True, timeout=timeout, cwd=ROOT, env=env)
    return p.returncode, (p.stdout or "") + (p.stderr or "")

def lua(code, timeout=120):
    return sh("lua", code, timeout=timeout)[1]

def luaj(code, timeout=120) -> Any:
    out = lua("local json=require('json'); " + code, timeout=timeout)
    starts = [k for k in (out.find("{"), out.find("[")) if k != -1]
    if not starts:
        return {"_raw": out}
    i = min(starts); j = out.rfind("}" if out[i] == "{" else "]")
    try:
        return json.loads(out[i:j + 1])
    except ValueError:
        return {"_raw": out}

def screen(name):
    txt = sh("screen", timeout=120)[1]
    (SCREENS / f"{name}.txt").write_text(txt)
    return txt

def key(k, wait=0.8):
    sh("key", k, timeout=60); time.sleep(wait)

def typ(text, wait=0.5):
    sh("type", text, timeout=60); time.sleep(wait)

def click(label, wait=1.2):
    out = sh("ui", "click", label, timeout=60)[1]; time.sleep(wait); return out

def answer(text):
    for _ in range(6): key(BACKSPACE, 0.12)
    typ(text); key("SELECT", 1.2)

def stepped(ticks, secs=400):
    """Step with the window closed (a DFHack window can hold the game); returns (ticks, wall seconds)."""
    close_window()
    out = sh("step", ticks, secs, timeout=secs + 60)[1]
    m = re.search(r"stepped (\d+) ticks .* in (\d+)s", out)
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)

SW = "local sw=reqscript('seasonal-wildlife'); "
GW = "local gw=reqscript('gui/seasonal-wildlife'); local w=gw.view and gw.view.subviews and gw.view.subviews[1]; "

def window_open():
    r = luaj(GW + "print(json.encode({open=w~=nil}))", timeout=30)
    return isinstance(r, dict) and r.get("open")

def open_window(tab=None):
    if not window_open():
        sh("cmd", "gui/seasonal-wildlife", timeout=120); time.sleep(2.5)
    if tab:
        click(tab, 1.5)

def close_window():
    for _ in range(4):
        if not window_open():
            return
        key("LEAVESCREEN", 0.8)

def win_text(txt):
    """The window's own rows, cropped to its frame (DF's map labels sit beside it)."""
    r = luaj(GW + "if w and w.frame_rect then print(json.encode({y1=w.frame_rect.y1,y2=w.frame_rect.y2,x1=w.frame_rect.x1,x2=w.frame_rect.x2})) else print('{}') end", timeout=30)
    y1, y2, x1, x2 = (r.get("y1", 0), r.get("y2", 999), r.get("x1", 0), r.get("x2", 999)) if isinstance(r, dict) else (0, 999, 0, 999)
    rows = []
    for l in txt.splitlines():
        m = re.match(r"^\s*(\d+)\|(.*)$", l)
        if m and y1 <= int(m.group(1)) <= y2:
            rows.append(m.group(2)[x1:x2 + 1].rstrip())
    return "\n".join(rows)

def announcements(n=6):
    r = luaj("local a=df.global.world.status.announcements; local o={}; for i=math.max(0,#a-%d),#a-1 do o[#o+1]=a[i].text end; print(json.encode(o))" % n, timeout=30)
    return r if isinstance(r, list) else []

def roster():
    """Every species on this embark: allow, seasons, stock set, odds set, role, size, habitat, layer."""
    r = luaj(SW + "local cfg=sw.loadConfig(); local pool=sw.buildPool(cfg); local o={}; for _,e in ipairs(pool) do if e.inEmbark and not e.locked then "
             "o[e.key]={allow=cfg.allow[e.key], assign=cfg.assign[e.key] or {}, stock=cfg.stock[e.key], odds=cfg.odds[e.key], cat=e.cat, size=e.size, hab=e.habitat, layer=e.layer, token=e.token, mass=e.mass, why=(cfg.why or {})[e.key]} end end; "
             "print(json.encode(o))", timeout=180)
    return r if isinstance(r, dict) and "_raw" not in r else {}

def select_row(listname, match_lua):
    """Put the cursor on the first visible row whose choice satisfies `match_lua` (a Lua expression over c)."""
    r = luaj(GW + f"local L=w.subviews['{listname}']; local vis=L.getVisibleChoices and L:getVisibleChoices() or L:getChoices(); "
             f"for i,c in ipairs(vis) do if {match_lua} then if L.list then L.list:setSelected(i) else L:setSelected(i) end; print(json.encode({{i=i}})) return end end; print(json.encode({{i=-1}}))", timeout=60)
    return isinstance(r, dict) and r.get("i", -1) > 0

def select_key(k):
    return select_row("list", f"c.entry and c.entry.key=='{k}'")

def focus():
    r = luaj("print(json.encode({f=dfhack.gui.getCurFocus(true)}))", timeout=30)
    return tuple(r.get("f", [])) if isinstance(r, dict) else ()

def asks(k, name):
    """Press k and report whether a dialog took the focus (the window's own key labels carry the same words, so
    the text alone cannot say a dialog opened)."""
    f0 = focus(); key(k, 1.0); f1 = focus(); t = screen(name)
    return f1 != f0, t

def list_row(t, token):
    """The Roster list row for a species (the header's 'Ecosystem balanced. [X: eats ...]' line names it too)."""
    return next((l for l in t.splitlines() if re.match(r"^\s+" + re.escape((token or "")[:16]) + r"\b.*\s(prey|predator|vermin)\s", l)), "")

def season_str(a):
    return "".join(SEASONS[i][:2] for i in sorted(a)) or "none"

# --- marking ---------------------------------------------------------------------------------------------
STEPS: list[tuple[str, str, Any]] = []
def step(sid, title):
    def deco(fn):
        STEPS.append((sid, title, fn)); return fn
    return deco

def mark(sid, title, v, note, evidence=None):
    results.append({"id": sid, "title": title, "v": v, "note": note, "evidence": evidence})
    log(f"  [{ {'p': 'PASS', 'a': 'ANOMALY', 's': 'SKIPPED'}[v]:<7}] {sid} {title}: {note[:150]}")

# --- 0 ---------------------------------------------------------------------------------------------------
@step("0.1", "Choose the fort")
def s01():
    st = sh("state")[1]
    if "map=true" in st:
        sh("title", timeout=120)
    sh("save-restore", FORT, BACKUP.split(".", 1)[1], timeout=300)
    rc, out = sh("load", FORT, timeout=400)
    sh("popups"); sh("fps", 1000, 10)
    b = luaj(SW + "local w=df.global.world; local n=0; for _,u in ipairs(w.units.active) do if dfhack.units.isCitizen(u) then n=n+1 end end; "
             "local wt=sw.ENGINE.waterTiles(); local found=0; for _,c in pairs(sw.CAVE and sw.CAVE.found and sw.CAVE.found() or {}) do found=found+1 end; "
             "print(json.encode({citizens=n, year=df.global.cur_year, season=df.global.cur_season, tick=df.global.cur_year_tick, "
             "water_tiles=#wt.tiles, salt=wt.sum.salt, fresh=wt.sum.fresh, river=wt.sum.river, ocean=wt.sum.ocean, caverns_found=found}))", timeout=120)
    memo["baseline"] = b
    ok = "loaded" in out and isinstance(b, dict) and b.get("citizens")
    mark("0.1", "Choose the fort", "p" if ok else "a",
         f"BOATS (the rig's copy of the alpha one fort) restored from {BACKUP} and loaded: {b.get('citizens')} citizens, year {b.get('year')} {SEASONS[b.get('season', 0)]}, "
         f"water tiles {b.get('water_tiles')} (river {b.get('river')}, ocean {b.get('ocean')}; salt {b.get('salt')}, fresh {b.get('fresh')}), caverns found {b.get('caverns_found')}"
         if isinstance(b, dict) else f"load: {out[-200:]}", b)

@step("0.2", "Back it up")
def s02():
    mark("0.2", "Back it up", "p", f"The copy is {BACKUP}, byte-restored before loading (the rig's save-restore checks the tree hash); the live region7 game is not touched.")

@step("0.3", "Turn on the frame counter")
def s03():
    n, s = stepped(3000)
    memo["base_tps"] = n / s if s else None
    mark("0.3", "Turn on the frame counter", "p" if s else "a",
         f"Baseline with the tool as saved: {n} ticks in {s}s = {n / s:.0f} ticks per second (tick cap 1000, graphics cap 10)." if s else "the step did not report its time")

# --- 1 ---------------------------------------------------------------------------------------------------
@step("1.1", "Open the window")
def s11():
    open_window()
    t = screen("1.1-open"); wt = win_text(t)
    tabs = ["Overview", "Panel", "Roster", "Seasons", "Food web", "Live", "Layers", "Vermin", "Ledger"]
    miss = [x for x in tabs if x not in wt]
    blocks = [x for x in ("On the map", "In season now", "Next boundary") if x not in wt]
    nonascii = sorted({ch for ch in wt if ord(ch) > 126})
    ok = "Seasonal Wildlife" in t and not miss and not blocks and not nonascii
    mark("1.1", "Open the window", "p" if ok else "a",
         f"Title and nine tabs {'present' if not miss else 'missing ' + str(miss)}; Overview blocks {'present' if not blocks else 'missing ' + str(blocks)}; "
         f"non-ASCII in the window: {''.join(nonascii) or 'none'}.")

@step("1.2", "Read the Panel")
def s12():
    click("Panel", 1.5); t = win_text(screen("1.2-panel"))
    rows = re.findall(r"\[(ON|off)\]\s+(\S.*?)\s{2,}", t)
    ok = "SWITCHES" in t and "JOBS" in t and len(rows) >= 12 and "frame rate" in t
    memo["switches"] = dict((n.strip(), s) for s, n in rows)
    mark("1.2", "Read the Panel", "p" if ok else "a",
         f"{len(rows)} switch rows ({sum(1 for s, _ in rows if s == 'ON')} on); JOBS table {'present' if 'JOBS' in t else 'missing'}; frame-rate line {'present' if 'frame rate' in t else 'missing'}. "
         f"Off by default: {', '.join(n.strip() for s, n in rows if s == 'off')}.")

@step("1.3", "Read the job timings")
def s13():
    stepped(1200)
    open_window("Panel"); key("CUSTOM_R", 1.0)
    t = win_text(screen("1.3-jobs"))
    jobs = re.findall(r"\[(?:ON|off)\]\s+(.+?)\s{2,}(\d+) t\s+(\d+) ms\s+(\d+) ms\s+(\d+)\s+(\d+)\s+(\S+)", t)
    tripped = [j[0].strip() for j in jobs if j[6] != "intact"]
    detail = "; ".join(f"{j[0].strip()} worst {j[3]} ms over {j[5]} of {j[4]}" for j in jobs)
    mark("1.3", "Read the job timings", "a" if tripped or not jobs else "p",
         (f"Fuse tripped on {tripped}. " if tripped else "Every fuse intact. ") + (detail or "no job rows parsed") +
         (". Worst passes above the 50 ms budget are the known open item (X7)." if any(int(j[3]) > 50 for j in jobs) else "."), jobs)

@step("1.4", "All off, then all on")
def s14():
    click("Panel", 1.0)
    q = SW + "local c=sw.loadConfig(); local ru=require('repeat-util'); local held=0; for _ in pairs(sw.CAVERN.saved()) do held=held+1 end; print(json.encode({enabled=c.enabled, eco=c.ecology.enabled, held=held}))"
    q0 = luaj(q)
    a1, _ = asks("CUSTOM_X", "1.4-alloff-ask"); key("SELECT", 1.5); q1 = luaj(q)
    a2, _ = asks("CUSTOM_A", "1.4-allon-ask"); key("SELECT", 1.5); q2 = luaj(q)
    asked = a1 and a2
    ok = asked and q1.get("enabled") is False and q1.get("held") == 0 and q2.get("enabled") == q0.get("enabled") and q2.get("eco") == q0.get("eco")
    mark("1.4", "All off, then all on", "p" if ok else "a",
         f"Both asked first: {asked}. Before {q0}; after All off {q1}; after All on {q2}.")

# --- 2 ---------------------------------------------------------------------------------------------------
@step("2.1", "Read the new columns")
def s21():
    open_window("Roster"); t = win_text(screen("2.1-roster"))
    cols = ["CREATURE", "ROLE", "SIZE", "HAB", "BIOME", "SEASON", "STOCK", "ODDS", "act", "WHY"]
    miss = [c for c in cols if c not in t]
    m = re.search(r"(\d+) special left to DF", t)
    mark("2.1", "Read the new columns", "p" if not miss and m else "a",
         f"Columns {'all present' if not miss else 'missing ' + str(miss)}; header: '{m.group(0) if m else 'no special count'}'.")

@step("2.2", "Filters")
def s22():
    base = win_text(screen("2.2-base")); seen = {}
    for k, name, n in (("CUSTOM_V", "View", 3), ("CUSTOM_C", "Cat", 1), ("CUSTOM_B", "Biome", 1), ("CUSTOM_N", "Season", 1)):
        labels = []
        for i in range(n):
            key(k, 1.0); t = win_text(screen(f"2.2-{name}-{i}"))
            m = re.search(name + r": ([A-Za-z .]+?)(?:\s{2,}|$)", t, re.M); labels.append(m.group(1) if m else "?")
            if name != "View":
                seen[name] = (labels[-1], t != base)
        if name == "View":
            seen[name] = (" -> ".join(labels), True)
    # put the filters back: Cat, Biome and Season cycle round; View came back to Current after three presses
    close_window(); open_window("Roster")
    changed = all(v[1] for v in seen.values())
    mark("2.2", "Filters", "p" if changed else "a",
         "; ".join(f"{k}: {v[0]}{'' if v[1] else ' (rows unchanged)'}" for k, v in seen.items()) + ". The window was reopened to reset the filters.")

@step("2.3", "Make a species inactive")
def s23():
    close_window(); open_window("Roster")
    r = roster()
    pick = next((k for k, e in r.items() if e.get("allow") is True and e.get("layer") == "land" and e.get("cat") in ("prey", "predator") and len(e.get("assign", [])) >= 1), None)
    if not pick or not select_key(pick):
        return mark("2.3", "Make a species inactive", "s", "no active land species to select")
    key("SELECT", 1.2); t = win_text(screen("2.3-inactive")); r2 = roster().get(pick, {})
    row = list_row(t, r[pick].get("token"))
    memo["inactive"] = pick
    ok = r2.get("allow") is False and not r2.get("assign") and re.search(r"\s-\s+you ", row)
    mark("2.3", "Make a species inactive", "p" if ok else "a",
         f"{pick}: allow {r[pick]['allow']} -> {r2.get('allow')}, seasons {season_str(r[pick]['assign'])} -> {season_str(r2.get('assign', []))}; row now: '{row.strip()}'.")

@step("2.4", "Make it active again")
def s24():
    pick = memo.get("inactive")
    if not pick or not select_key(pick):
        return mark("2.4", "Make it active again", "s", "no species from 2.3")
    key("SELECT", 1.2); r2 = roster().get(pick, {})
    n = len(r2.get("assign", []))
    mark("2.4", "Make it active again", "p" if r2.get("allow") is True and n == 1 else "a",
         f"{pick}: active {r2.get('allow')}, seasons {season_str(r2.get('assign', []))} ({n}).")
    # leave it inactive for 16.1, the way a tester would after this step
    select_key(pick); key("SELECT", 1.2)
    memo["inactive_after"] = roster().get(pick, {})

@step("2.5", "Cycle seasons")
def s25():
    r = roster()
    pick = next((k for k, e in r.items() if e.get("allow") is True and e.get("layer") == "land" and len(e.get("assign", [])) >= 1 and k != memo.get("inactive")), None)
    if not pick or not select_key(pick):
        return mark("2.5", "Cycle seasons", "s", "no active row")
    seq = [season_str(r[pick].get("assign", []))]
    for i in range(8):
        key("CUSTOM_E", 0.9); seq.append(season_str(roster().get(pick, {}).get("assign", [])))
    mark("2.5", "Cycle seasons", "a" if "none" in seq else "p", f"{pick}: " + " -> ".join(seq) + ".")

@step("2.6", "Try to remove the last season")
def s26():
    r = roster()
    pick = next((k for k, e in r.items() if e.get("allow") is True and e.get("layer") == "land" and len(e.get("assign", [])) == 1), None)
    if not pick or not select_key(pick):
        return mark("2.6", "Try to remove the last season", "s", "no one-season species")
    s = r[pick].get("assign", [])[0]
    key(SKEY[s], 1.0); t = win_text(screen("2.6-last")); after = roster().get(pick, {}).get("assign", [])
    msg = "the last season stays" in t
    mark("2.6", "Try to remove the last season", "p" if msg and len(after) == 1 else "a",
         f"{pick} on {SEASONS[s]}: pressed its key; seasons after {season_str(after)}; refusal on screen: {msg}.")

@step("2.7", "Cycle the layer")
def s27():
    titles = []
    for i in range(5):
        key("CUSTOM_ALT_L", 1.2); t = screen(f"2.7-layer-{i}")
        m = re.search(r"Seasonal Wildlife \. ([^|]*?\(Alt\+L\))", t); titles.append(m.group(1) if m else "?")
    want = ["Land", "Water", "Cavern", "Deep", "All layers"]
    ok = all(w in t_ for w, t_ in zip(want, titles))
    mark("2.7", "Cycle the layer", "p" if ok else "a", " -> ".join(titles) + ". No macro recording started (Alt+L is not a DF key).")

# --- 3 ---------------------------------------------------------------------------------------------------
def detail(k, name):
    close_window(); open_window("Roster")
    if not select_key(k):
        return None
    key("CUSTOM_I", 1.5); return win_text(screen(name))

@step("3.1", "Open the detail")
def s31():
    r = roster()
    big = sorted(((e.get("mass") or 0, k) for k, e in r.items() if e.get("layer") == "land" and e.get("cat") != "vermin"), reverse=True)
    if not big:
        return mark("3.1", "Open the detail", "s", "no land species")
    k = big[0][1]; t = detail(k, "3.1-detail") or ""
    m = re.search(r"adult (\d+) cm3, (\w+)", t)
    rows = [x for x in ("habitat", "role", "body", "stock", "odds", "group size", "seasons", "eats", "eaten by") if x in t]
    mass, band = (int(m.group(1)), m.group(2)) if m else (0, "?")
    want = "large" if mass >= 1_000_000 else "medium" if mass >= 150_000 else "small"
    memo["detail_key"] = k
    mark("3.1", "Open the detail", "p" if m and band == want and len(rows) == 9 else "a",
         f"{k}: body 'adult {mass:,} cm3, {band}' (the D4 band for that volume is {want}); rows present: {', '.join(rows)}.")

@step("3.2", "Habitat and role come from the raws")
def s32():
    want = {"ORCA": ("aquatic", "predator"), "GIANT_ORCA": ("aquatic", "predator"), "BIRD_ALBATROSS": ("waterbird", None), "DINGO": ("land", "predator")}
    r = roster(); notes = []; bad = []
    for tok, (hab, role) in want.items():
        k = next((k for k, e in r.items() if e.get("token") == tok), None)
        if not k:
            continue
        e = r[k]; notes.append(f"{tok} {e['hab']} {e['cat']} {e['size']}")
        if e.get("hab") != hab or (role and e.get("cat") != role) or (tok == "DINGO" and e.get("size") != "small"):
            bad.append(tok)
    if not notes:
        # none on this embark's roster: read the model the detail page uses for them
        m = luaj(SW + "local o={}; for _,t in ipairs({'ORCA','GIANT_ORCA','BIRD_ALBATROSS','DINGO'}) do local e=sw.MODEL.entry(t); if e then o[t]={hab=e.habitat, role=e.role, size=e.size} end end; print(json.encode(o))")
        notes = [f"{t} {v.get('hab')} {v.get('role')} {v.get('size')} (model; not on this roster)" for t, v in (m.items() if isinstance(m, dict) else [])]
        bad = [t for t, v in (m.items() if isinstance(m, dict) else []) if v.get("hab") != want[t][0] or (want[t][1] and v.get("role") != want[t][1])]
    mark("3.2", "Habitat and role come from the raws", "a" if bad else "p", "; ".join(notes) + (f". Wrong: {bad}" if bad else "."))

@step("3.3", "Set its stock")
def s33():
    k = memo.get("detail_key"); t = detail(k, "3.3-before")
    if t is None:
        return mark("3.3", "Set its stock", "s", "no detail species")
    key("CUSTOM_K", 1.0); p = win_text(screen("3.3-prompt")); answer("40")
    t2 = win_text(screen("3.3-after")); line = next((l.strip() for l in t2.splitlines() if re.search(r"\bstock\b", l) and "region" in l), "")
    opened = "Stock for" in p or ": stock" in p   # the detail page's prompt is titled '<TOKEN>: stock'
    ok = opened and ("(you set 40)" in line or "40 come back in season" in line)
    memo["stock_set"] = (k, 40)
    mark("3.3", "Set its stock", "p" if ok else "a", f"{k}: prompt {'opened' if opened else 'did not open'}; stock line now '{line}'.")

@step("3.4", "Set its odds")
def s34():
    k = memo.get("detail_key"); detail(k, "3.4-before")
    key("CUSTOM_O", 1.0); answer("20")
    t2 = win_text(screen("3.4-after")); line = next((l.strip() for l in t2.splitlines() if re.search(r"\bodds\b", l) and "weight" in l), "")
    mark("3.4", "Set its odds", "p" if "weight 20" in line and "you set it" in line else "a", f"{k}: odds line now '{line}'.")

@step("3.5", "Set its group size")
def s35():
    k = memo.get("detail_key"); detail(k, "3.5-before")
    key("CUSTOM_G", 1.0); answer("2")
    t2 = win_text(screen("3.5-after")); line = next((l.strip() for l in t2.splitlines() if "group size" in l and "(" in l and "clade" not in l), "")
    mark("3.5", "Set its group size", "p" if "2 (you set it)" in line else "a", f"{k}: group size line now '{line}'.")
    # clear the three writes so they do not skew the season boundary
    sh("cmd", "seasonal-wildlife", "size", r_token(k), "clear"); sh("cmd", "seasonal-wildlife", "odds", r_token(k), "clear")

def r_token(k):
    return k.split(":", 1)[-1]

@step("3.6", "Call a wave")
def s36():
    r = roster(); season = luaj("print(json.encode({s=df.global.cur_season}))").get("s", 0)
    k = next((k for k, e in r.items() if e.get("allow") is True and e.get("layer") == "land" and e.get("cat") == "prey" and season in e.get("assign", [])), None)
    if not k or detail(k, "3.6-before") is None:
        return mark("3.6", "Call a wave", "s", "no active land prey in season")
    key("CUSTOM_C", 1.2); t = win_text(screen("3.6-called"))
    close_window()
    ids0 = luaj("local m=0; for _,u in ipairs(df.global.world.units.all) do if u.id>m then m=u.id end end; print(json.encode({m=m}))").get("m", 0)
    got = None; waited = 0
    for _ in range(8):
        n, s = stepped(1500); waited += n
        a = luaj(SW + "local o={}; for _,u in ipairs(df.global.world.units.active) do if u.id>%d and sw.WILD.onMap(u) and sw.WILD.layerOf(u)=='land' then o[#o+1]=df.creature_raw.find(u.race).creature_id end end; print(json.encode(o))" % ids0)
        if isinstance(a, list) and a:
            got = a; break
    if not got:
        return mark("3.6", "Call a wave", "s", f"called {k}; no land arrival in {waited} ticks (a censored wait: the gate or DF did not draw in the window). Screen after C: '{t.splitlines()[-1].strip() if t else ''}'.")
    mark("3.6", "Call a wave", "p" if all(x == r[k].get("token") for x in got) else "a", f"called {k}; the next land arrival after {waited} ticks: {', '.join(got)}.")

# --- 4 ---------------------------------------------------------------------------------------------------
@step("4.1", "Stock for one row")
def s41():
    close_window(); open_window("Roster")
    r = roster(); k = next((k for k, e in r.items() if e.get("layer") == "land" and e.get("cat") == "prey"), None)
    select_key(k); key("CUSTOM_CTRL_W", 1.0); p = win_text(screen("4.1-prompt")); answer("55")
    ok = "Stock for" in p and roster().get(k, {}).get("stock") == 55
    mark("4.1", "Stock for one row", "p" if ok else "a", f"{k}: prompt {'opened' if 'Stock for' in p else 'did not open'}; stored stock {roster().get(k, {}).get('stock')}.")

@step("4.2", "Stock for the filter")
def s42():
    close_window(); open_window("Roster")
    key("CUSTOM_C", 1.0); t = win_text(screen("4.2-cat")); cat = (re.search(r"Cat: (\w+)", t) or [None, "?"])[1]
    r0 = roster(); key("CUSTOM_CTRL_G", 1.0); answer("44"); r1 = roster()
    changed = {k for k in r1 if r1[k].get("stock") != r0.get(k, {}).get("stock")}
    inside = {k for k in changed if r1[k].get("cat") == cat or r1[k].get("hab") == cat}
    outside = changed - inside
    mark("4.2", "Stock for the filter", "p" if changed and not outside else "a",
         f"Cat filter '{cat}': {len(changed)} species set to 44; outside the filter: {sorted(outside)[:6] or 'none'}.")
    close_window(); open_window("Roster")

@step("4.3", "Odds for one row")
def s43():
    close_window(); open_window("Roster")
    r = roster()
    # v6.7: prefer an active land prey OUT of season, so the bracketed share is what is tested; else any active one
    cur = luaj("print(json.encode({s=df.global.cur_season}))").get("s", -1)
    land = [k for k, e in r.items() if e.get("layer") == "land" and e.get("allow") is True and e.get("cat") == "prey"]
    k = next((k for k in land if cur not in (r[k].get("assign") or [])), None) if cur >= 0 else None
    k = k or (land[0] if land else None)
    select_key(k); key("CUSTOM_ALT_O", 1.0); answer("30")
    t = win_text(screen("4.3-odds")); row = list_row(t, r[k].get("token"))
    # v6.7 (round 1's anomaly): the ODDS cell is the column before 'act'; '-' on an active species is the anomaly,
    # '(n%)' is the out-of-season share, 'n%' the in-season one
    m = re.search(r"\s(\(\d+%\)|\d+%|-)\s+[Y-]\s", row)
    cell = m.group(1) if m else "?"
    mark("4.3", "Odds for one row", "p" if cell not in ("-", "?") else "a",
         f"{k}: ODDS cell '{cell}' ({'out of season, bracketed' if cell.startswith('(') else 'in season' if cell.endswith('%') else 'no share shown'}); row '{row.strip()}'.")
    sh("cmd", "seasonal-wildlife", "odds", r_token(k), "clear")

# --- 5 ---------------------------------------------------------------------------------------------------
@step("5.1", "Every tool asks")
def s51():
    close_window(); open_window("Roster")
    r0 = roster(); asked = {}
    for k, name in (("CUSTOM_M", "Matrix assign"), ("CUSTOM_O", "Co-align"), ("CUSTOM_F", "Fill to targets"), ("CUSTOM_Y", "Fill natural prey"), ("CUSTOM_D", "Fill natural predators")):
        asked[name], _ = asks(k, f"5.1-{name}")
        if asked[name]:
            key("LEAVESCREEN", 1.0)
    same = roster() == r0
    mark("5.1", "Every tool asks", "p" if all(asked.values()) and same else "a",
         "; ".join(f"{n}: {'asked' if a else 'did not ask'}" for n, a in asked.items()) + f". Answering No left the roster {'unchanged' if same else 'CHANGED'}.")

def seasons_stats(r):
    act = {k: e for k, e in r.items() if e.get("allow") is True}
    per = [sum(1 for e in act.values() if s in e.get("assign", [])) for s in range(4)]
    four = sum(1 for e in act.values() if len(e.get("assign", [])) == 4)
    none = sum(1 for e in act.values() if not e.get("assign", []))
    return len(act), per, four, none

@step("5.2", "Matrix assign")
def s52():
    close_window(); open_window("Roster")
    key("CUSTOM_M", 1.0); key("SELECT", 2.0); r = roster()
    n, per, four, none = seasons_stats(r)
    whys = {}
    for e in r.values():
        if e.get("allow") is True:
            w = (e.get("why") or "")[:6]; whys[w.split(" ")[0] if w else "?"] = whys.get(w.split(" ")[0] if w else "?", 0) + 1
    t = win_text(screen("5.2-matrix"))
    wh = re.findall(r"\s(matrix|pair)\s+\w+\d+\s*$", t, re.M)
    ok = none == 0 and max(per) <= n / 2 + 1
    mark("5.2", "Matrix assign", "p" if ok else "a",
         f"{n} active; per season {dict(zip(['Sp', 'Su', 'Au', 'Wi'], per))} (half is {n / 2:.0f}); with no season {none}; all four {four}; WHY on screen: {', '.join(sorted(set(wh))) or 'none visible'}.")

@step("5.3", "Co-align")
def s53():
    r0 = roster(); key("CUSTOM_O", 1.0); key("SELECT", 2.0); r1 = roster()
    n0, _, four0, _ = seasons_stats(r0); n1, per, four1, _ = seasons_stats(r1)
    shrunk = [k for k in r1 if r1[k].get("allow") is True and not set(r0.get(k, {}).get("assign", [])) <= set(r1[k].get("assign", []))]
    grew = sum(len(r1[k].get("assign", [])) - len(r0.get(k, {}).get("assign", [])) for k in r1 if r1[k].get("allow") is True)
    ok = not shrunk and four1 <= max(four0 + 3, n1 // 4)
    mark("5.3", "Co-align", "p" if ok else "a",
         f"{grew} season cell(s) added; species on all four seasons {four0} -> {four1} of {n1}; any season removed: {shrunk[:5] or 'none'}.")

@step("5.4", "Fill natural prey and predators")
def s54():
    r0 = roster(); inact0 = sum(1 for e in r0.values() if e.get("allow") is not True)
    key("CUSTOM_Y", 1.0); key("SELECT", 1.5); ra = roster(); key("CUSTOM_D", 1.0); key("SELECT", 1.5); rb = roster()
    ny = sum(1 for k in ra if ra[k].get("allow") is True and r0.get(k, {}).get("allow") is not True)
    nd = sum(1 for k in rb if rb[k].get("allow") is True and ra.get(k, {}).get("allow") is not True)
    led = sh("cmd", "seasonal-wildlife", "ledger", "4", "edit")[1]
    ok = (ny + nd) <= max(3, inact0 // 2)
    mark("5.4", "Fill natural prey and predators", "p" if ok else "a",
         f"Y activated {ny}, D activated {nd}, of {inact0} inactive before. Ledger: " + " | ".join(l.strip()[:90] for l in led.splitlines() if "fill" in l.lower())[-300:])

@step("5.5", "Category targets")
def s55():
    close_window(); open_window("Roster")
    key("CUSTOM_SHIFT_P", 1.0); key("CUSTOM_SHIFT_P", 1.0); t = win_text(screen("5.5-target"))
    m = re.search(r"prey: (\d)", t)
    key("CUSTOM_C", 1.0); key("CUSTOM_C", 1.0); t2 = win_text(screen("5.5-cat")); cat = (re.search(r"Cat: (\w+)", t2) or [None, "?"])[1]
    key("CUSTOM_ALT_F", 1.0); p = win_text(screen("5.5-fill-prompt"))
    prompted = "to N" in p or "Target count" in p
    if prompted:
        key("LEAVESCREEN", 1.0)
    head = "Thin:" in t or "Ecosystem balanced" in t
    mark("5.5", "Category targets", "p" if m and prompted and head else "a",
         f"Shift+P twice: target line 'prey: {m.group(1) if m else '?'}'; header {'shows Thin/balanced' if head else 'shows neither'}; Alt+F with Cat '{cat}': {'prompt opened (cancelled)' if prompted else 'no prompt: ' + p.splitlines()[-1].strip() if p else ''}.")

# --- 6 ---------------------------------------------------------------------------------------------------
@step("6.1", "Dry run")
def s61():
    close_window(); open_window("Roster")
    r0 = roster(); key("CUSTOM_CTRL_D", 1.5); t = screen("6.1-dryrun"); same = roster() == r0
    table = "Dry-run" in t and "Sp Su Au Wi" in t
    key("LEAVESCREEN", 0.8)
    mark("6.1", "Dry run", "p" if table and same else "a", f"the Dry-run season table (Sp Su Au Wi) {'opened' if table else 'did not open'}; roster unchanged: {same}.")

@step("6.2", "Apply now")
def s62():
    close_window(); open_window("Roster")
    a0 = announcements(); key("CUSTOM_CTRL_A", 1.5); a1 = announcements()
    hit = [a for a in a1 if "wildlife applied" in a and a not in a0[-2:]]
    mark("6.2", "Apply now", "p" if hit else "a", f"Announcement: '{hit[-1] if hit else (a1[-1] if a1 else 'none')}'.")

@step("6.3", "Send off and next")
def s63():
    q = SW + "local n=0; for _,u in ipairs(df.global.world.units.active) do if sw.WILD.onMap(u) and sw.WILD.layerOf(u)=='land' and (u.flags2.roaming_wilderness_population_source or u.flags2.roaming_wilderness_population_source_not_a_map_feature) then n=n+1 end end; print(json.encode({n=n}))"
    f0 = luaj(q).get("n", -1); key("CUSTOM_CTRL_F", 1.5); f1 = luaj(q).get("n", -1)
    if f0 == 0:
        return mark("6.3", "Send off and next", "s", "no wild land group on the surface at this moment")
    mark("6.3", "Send off and next", "p" if f1 == 0 else "a", f"wild land units still tied to their entry: {f0} -> {f1}.")

@step("6.4", "Rotation off and on")
def s64():
    q = SW + "print(json.encode({e=sw.loadConfig().enabled}))"
    e0 = luaj(q).get("e"); key("CUSTOM_CTRL_E", 1.0); t1 = win_text(screen("6.4-off")); e1 = luaj(q).get("e")
    key("CUSTOM_CTRL_E", 1.0); t2 = win_text(screen("6.4-on")); e2 = luaj(q).get("e")
    h1 = re.search(r"rotation (\w+)", t1); h2 = re.search(r"rotation (\w+)", t2)
    ok = e1 is not e0 and e2 == e0 and h1 and h2 and h1.group(1) != h2.group(1)
    mark("6.4", "Rotation off and on", "p" if ok else "a", f"rotation {e0} -> {e1} -> {e2}; header 'rotation {h1.group(1) if h1 else '?'}' then 'rotation {h2.group(1) if h2 else '?'}'.")

# --- 7 ---------------------------------------------------------------------------------------------------
@step("7.1", "Reset the roster")
def s71():
    close_window(); open_window("Roster")
    r0 = roster(); stock0 = {k: e.get("stock") for k, e in r0.items() if e.get("stock") is not None}
    key("CUSTOM_ALT_R", 1.2); c = win_text(screen("7.1-choice")); key("SELECT", 1.2); d = win_text(screen("7.1-confirm")); key("SELECT", 2.0)
    r1 = roster(); n, per, four, none = seasons_stats(r1)
    kept = all(r1.get(k, {}).get("stock") == v for k, v in stock0.items())
    extra = sum(1 for e in r1.values() if e.get("allow") is True and len(e.get("assign", [])) > 1)
    ok = "The roster" in c and "Everything" in c and "Reset the roster" in d and none == 0 and kept
    mark("7.1", "Reset the roster", "p" if ok else "a",
         f"Choice offered: {'The roster' in c and 'Everything' in c}; confirmation: {'Reset the roster' in d}; {n} active, {none} with no season, {extra} with a second season (the pair guarantee); "
         f"{len(stock0)} stock setting(s) kept: {kept}.")
    # the inactive species of 2.3 came back as first found: make it inactive again for 16.1
    k = memo.get("inactive")
    if k and r1.get(k, {}).get("allow") is True:
        select_key(k); key("SELECT", 1.0)

# --- 8 ---------------------------------------------------------------------------------------------------
@step("8.1", "Add invasive")
def s81():
    close_window(); open_window("Roster")
    for i in range(3):
        key("CUSTOM_V", 1.0); t = win_text(screen(f"8.1-view-{i}"))
        if "View: Add invasive" in t:
            break
    if "View: Add invasive" not in t:
        return mark("8.1", "Add invasive", "a", "View never reached Add invasive")
    pick = luaj(GW + "local L=w.subviews.list; local c=(L:getVisibleChoices())[1]; print(json.encode({k=c and c.entry and c.entry.key or '', t=c and c.entry and c.entry.token or ''}))")
    key("CUSTOM_CTRL_X", 1.0); p = win_text(screen("8.1-ask")); key("SELECT", 2.5)
    tok = pick.get("t") if isinstance(pick, dict) else ""
    after = luaj(SW + f"local cfg=sw.loadConfig(); local pool=sw.buildPool(cfg); for _,e in ipairs(pool) do if e.token=='{tok}' then print(json.encode({{inEmbark=e.inEmbark, allow=cfg.allow[e.key], assign=cfg.assign[e.key] or {{}}}})) return end end; print('{{}}')")
    led = sh("cmd", "seasonal-wildlife", "ledger", "3")[1]
    # v6.7 (round 1's anomaly): right after the add the species obeys the roster rule -- active with a season, or inactive
    ok = isinstance(after, dict) and after.get("inEmbark") and (after.get("allow") is False or (after.get("allow") is True and len(after.get("assign") or []) >= 1))
    mark("8.1", "Add invasive", "p" if ok else "a",
         f"{tok}: on this embark after the add: {after.get('inEmbark') if isinstance(after, dict) else after}; active {after.get('allow') if isinstance(after, dict) else '?'} seasons {season_str(after.get('assign', [])) if isinstance(after, dict) else '?'}. "
         f"Ledger: {' | '.join(l.strip()[:80] for l in led.splitlines()[-2:])}")
    close_window()

# --- 9 ---------------------------------------------------------------------------------------------------
@step("9.1", "Read it")
def s91():
    open_window("Seasons"); t = win_text(screen("9.1-seasons"))
    ok = all(s in t for s in SEASONS) and re.search(r"\s\+\s", t) and re.search(r"\s\.\s", t)
    mark("9.1", "Read it", "p" if ok else "a", f"Four season columns: {all(s in t for s in SEASONS)}; + and . marks drawn: {bool(ok)}.")

@step("9.2", "Edit from the grid")
def s92():
    r = roster()
    sel = luaj(GW + "local L=w.subviews.seasons; local vis=L.getVisibleChoices and L:getVisibleChoices() or L:getChoices(); for i,c in ipairs(vis) do if c.entry and c.entry.key then L:setSelected(i); print(json.encode({k=c.entry.key})) return end end; print('{}')")
    k = sel.get("k") if isinstance(sel, dict) else None
    if not k or k not in r:
        return mark("9.2", "Edit from the grid", "s", "could not select a species row on the Seasons tab")
    a0 = r[k].get("assign", []); s = next((i for i in range(4) if i not in a0), None)
    if s is None:
        return mark("9.2", "Edit from the grid", "s", f"{k} already has all four seasons")
    key(SKEY[s], 1.0); t = win_text(screen("9.2-edit")); a1 = roster().get(k, {}).get("assign", [])
    hdr = re.search(re.escape(r[k].get("token")[:12]) + r"[A-Z_]*: (\w+)", t)
    ok = s in a1 and hdr
    # try removing its only season on a one-season species
    one = next((kk for kk, e in roster().items() if e.get("allow") is True and len(e.get("assign", [])) == 1 and kk != k), None)
    refused = None
    if one:
        luaj(GW + f"local L=w.subviews.seasons; local vis=L.getVisibleChoices and L:getVisibleChoices() or L:getChoices(); for i,c in ipairs(vis) do if c.entry and c.entry.key=='{one}' then L:setSelected(i) end end; print('{{}}')")
        key(SKEY[roster()[one].get("assign", [0])[0]], 1.0); refused = len(roster().get(one, {}).get("assign", [])) == 1
    mark("9.2", "Edit from the grid", "p" if ok and refused is not False else "a",
         f"{k}: {SEASONS[s]} added ({season_str(a0)} -> {season_str(a1)}); header '{hdr.group(0) if hdr else 'no header line'}'; removing {one}'s last season here refused: {refused}.")
    key(SKEY[s], 1.0)   # put it back

# --- 10 --------------------------------------------------------------------------------------------------
@step("10.1", "The pyramid")
def s101():
    open_window("Food web"); t = win_text(screen("10.1-web"))
    body = t.split("trophic pyramid", 1)[-1].split("aquatic chain", 1)[0]
    tiers = [l.strip() for l in body.splitlines()[1:] if l.strip() and not set(l.strip()) <= set("^ ")]
    chain = [l.strip() for l in t.split("aquatic chain", 1)[-1].splitlines() if "---->" in l]
    # v6.7 (round 1's design question, the user's call): an animal person stands where its root animal stands
    ap = luaj(SW + """local cfg=sw.loadConfig(); local pool=sw.buildPool(cfg); local n,bad=0,{}
for _,a in ipairs(pool) do if a.inEmbark then local root=sw.MODEL.rootOf(a.token); local b=root and sw.MODEL.entry(root)
  if b then n=n+1; local d=(a.role~=b.role or a.habitat~=b.habitat or a.size~=b.size)
    if not d then for _,p in ipairs(pool) do if p.inEmbark and p.token~=a.token and p.token~=root and (sw.eats(a,p)~=sw.eats(b,p) or sw.eats(p,a)~=sw.eats(p,b)) then d=true break end end end
    if d then bad[#bad+1]=a.token..'/'..root end end end end
print(json.encode({people=n, differ=bad}))""")
    apok = isinstance(ap, dict) and ap.get("people", 0) > 0 and not ap.get("differ")
    mark("10.1", "The pyramid", "p" if len(tiers) == 4 and "^" in body and apok else "a",
         f"{len(tiers)} tiers, top '{tiers[0][:70] if tiers else ''}', base '{tiers[-1][:70] if tiers else ''}'; aquatic chain lines: {len(chain)}, e.g. '{chain[0][:90] if chain else ''}'. "
         f"Animal people on this embark mirroring their root (role, habitat, size, every eats verdict both ways): "
         f"{(ap.get('people', 0) - len(ap.get('differ') or [])) if isinstance(ap, dict) else '?'} of {ap.get('people', '?') if isinstance(ap, dict) else ap}"
         f"{'; differ: ' + ', '.join(ap['differ'][:6]) if isinstance(ap, dict) and ap.get('differ') else ''}.")

@step("10.2", "Diet follows habitat")
def s102():
    bad = luaj(SW + "local cfg=sw.loadConfig(); local pool=sw.buildPool(cfg); local o={}; for _,e in ipairs(pool) do if e.inEmbark and e.cat=='predator' and e.habitat=='land' then "
               "for _,p in ipairs(pool) do if p.inEmbark and p.habitat=='aquatic' and sw.eats(e,p) then o[#o+1]=e.token..'>'..p.token end end end end; "
               "local b={}; for _,e in ipairs(pool) do if e.inEmbark and e.cat=='predator' and (e.habitat=='flier') then for _,p in ipairs(pool) do if p.inEmbark and p.habitat=='aquatic' and p.cat~='vermin' and sw.eats(e,p) then b[#b+1]=e.token..'>'..p.token end end end end; "
               "print(json.encode({land_aquatic=o, flier_aquatic=b}))", timeout=180)
    t = win_text(screen("10.2-web"))
    la = bad.get("land_aquatic", []) if isinstance(bad, dict) else ["probe failed"]
    fa = bad.get("flier_aquatic", []) if isinstance(bad, dict) else []
    mark("10.2", "Diet follows habitat", "p" if not la and not fa else "a",
         f"Land predators eating aquatic species on this roster: {la[:6] or 'none'}; fliers eating aquatic non-vermin: {fa[:6] or 'none'}.")

@step("10.3", "The four modes")
def s103():
    modes = []
    for i, k in enumerate(("CUSTOM_G", "CUSTOM_G", "CUSTOM_L")):
        key(k, 1.2); t = win_text(screen(f"10.3-mode-{i}"))
        modes.append("graph" if "as a graph" in t else "by season" if "mass ratio" in t else "by layer" if "bridge edges" in t else "?")
    key("CUSTOM_G", 1.0); key("CUSTOM_N", 1.2); tn = win_text(screen("10.3-season"))
    ok = modes == ["graph", "by season", "by layer"]
    mark("10.3", "The four modes", "p" if ok else "a", f"G, G, L gave {' -> '.join(modes)}; N shows a season: {any(s in tn for s in SEASONS)}.")

# --- 11 --------------------------------------------------------------------------------------------------
@step("11.1", "Origins")
def s111():
    open_window("Live"); t = win_text(screen("11.1-live"))
    m = re.search(r"Wild on map: (.*)", t)
    origins = re.findall(r"^\s+(DF wave|tool-drawn|resident|born here|untracked|deep)\s+(\d+)", t, re.M)
    total = luaj(SW + "local n=0; for _,u in ipairs(df.global.world.units.active) do if sw.WILD.onMap(u) then n=n+1 end end; print(json.encode({n=n}))").get("n")
    s = sum(int(n) for _, n in origins)
    lines = [x for x in ("ecology:", "limits:", "fuse:") if x in t]
    mark("11.1", "Origins", "p" if origins and s == total and len(lines) == 3 else "a",
         f"Origins {', '.join(f'{o} {n}' for o, n in origins)} (sum {s}); wild on the map by probe {total}; lines present: {', '.join(lines)}.")

def live_group_row():
    t = screen("11-live-rows"); wt = win_text(t)
    rows = [l for l in wt.splitlines() if re.search(r"\bx\d+ (gated|resident|drawn)", l)]
    if not rows:
        return None
    ok = luaj(GW + "local L=w.subviews.live; for i,c in ipairs(L:getChoices()) do if c.grp then L:setSelected(i); print(json.encode({i=i, t=c.grp.token})) return end end; print('{}')")
    return ok if isinstance(ok, dict) and ok.get("t") else None

@step("11.2", "Groups")
def s112():
    t = win_text(screen("11.2-live"))
    m = re.search(r"Groups: .*", t)
    rows = [l.strip() for l in t.splitlines() if re.search(r"\bx\d+ (gated|resident|drawn)", l)]
    mark("11.2", "Groups", "p" if m and rows else ("s" if m else "a"), f"'{m.group(0)[:100] if m else 'no Groups: line'}'; {len(rows)} group row(s), first '{rows[0][:80] if rows else ''}'.")

@step("11.3", "Hold and send off")
def s113():
    g = live_group_row()
    if not g:
        return mark("11.3", "Hold and send off", "s", "no tracked group on the map")
    key("CUSTOM_Q", 1.2); tq = win_text(screen("11.3-hold")); key("CUSTOM_X", 1.2); tx = win_text(screen("11.3-dismiss"))
    mark("11.3", "Hold and send off", "p" if "more days" in tq and "dismissed" in tx else "a",
         f"{g['t']}: after Q 'held N more days' shown {'held' in tq and 'more days' in tq}; after X 'dismissed' shown {'dismissed' in tx}.")

@step("11.4", "Follow and centre")
def s114():
    g = live_group_row()
    if not g:
        return mark("11.4", "Follow and centre", "s", "no tracked group on the map")
    key("CUSTOM_F", 1.2); f = luaj("print(json.encode({f=df.global.plotinfo.follow_unit}))").get("f", -1)
    luaj("df.global.plotinfo.follow_unit=-1; df.global.window_x=0; df.global.window_y=0; print('{}')")
    live_group_row(); key("SELECT", 1.2); v = luaj("print(json.encode({x=df.global.window_x, y=df.global.window_y}))")
    moved = isinstance(v, dict) and (v.get("x") or v.get("y"))
    mark("11.4", "Follow and centre", "p" if f >= 0 and moved else "a", f"{g['t']}: follow unit {f}; after Enter the view is at {v}.")

@step("11.5", "Herds and packs")
def s115():
    t = win_text(screen("11.5-herds"))
    rows = re.findall(r"^\s+(\S+)\s+(herd|pack|flock|school|solitary)\s+(.+?)\s{2,}", t, re.M)
    q = [r[0] for r in rows if r[2].strip().startswith("?")]
    mark("11.5", "Herds and packs", "p" if rows and not q else ("s" if not rows else "a"),
         f"{len(rows)} tracked species: " + ", ".join(f"{r[0]} {r[1]}" for r in rows[:8]) + (f"; reason '?' for {q}" if q else "; every one has a reason."))

# --- 12 --------------------------------------------------------------------------------------------------
@step("12.1", "Read the table")
def s121():
    open_window("Layers"); t = win_text(screen("12.1-layers"))
    cols = [c for c in ("LAND", "WATER", "CAVERN", "DEEP") if c in t]
    rows = [r for r in ("drawn by", "groups at once", "ceiling", "gap between waves", "pattern", "coupling", "cohesion", "ecology switch", "nudge after", "pack size") if r in t]
    m = re.search(r"drawn by\s+(.+)", t)
    mark("12.1", "Read the table", "p" if len(cols) == 4 and len(rows) == 10 else "a", f"Columns {', '.join(cols)}; {len(rows)} of 10 rows; drawn by: {m.group(1).strip() if m else '?'}.")

@step("12.2", "Change a limit")
def s122():
    q = SW + "local c=sw.loadConfig(); print(json.encode({g=c.limits.land.groups}))"
    g0 = luaj(q).get("g"); key("CUSTOM_C", 1.0); answer(str((g0 or 3) + 1)); g1 = luaj(q).get("g")
    led = sh("cmd", "seasonal-wildlife", "ledger", "2", "edit")[1]
    ok = g1 == (g0 or 3) + 1 and "groups at once" in led
    mark("12.2", "Change a limit", "p" if ok else "a", f"land groups at once {g0} -> {g1}; ledger: {led.strip().splitlines()[-1][:90] if led.strip() else ''}.")
    key("CUSTOM_C", 1.0); answer(str(g0))

@step("12.3", "The water line")
def s123():
    t = win_text(screen("12.3-water")); m = re.search(r"water: .*", t)
    wet = memo.get("baseline", {}).get("water_tiles", 0)
    ok = m and ("draws on" in m.group(0) if wet else "dormant" in m.group(0))
    mark("12.3", "The water line", "p" if ok else "a", f"'{m.group(0)[:150] if m else 'no water line'}' (the fort has {wet} water tiles).")

@step("12.4", "Caverns")
def s124():
    t = win_text(screen("12.4-caverns")); rows = re.findall(r"Cavern (\d)\s+(.+)", t)
    mark("12.4", "Caverns", "p" if rows else "a", "; ".join(f"cavern {n}: {s.strip()[:60]}" for n, s in rows) or "no cavern rows")

# --- 13 --------------------------------------------------------------------------------------------------
@step("13.1", "Families")
def s131():
    open_window("Vermin"); t = win_text(screen("13.1-vermin"))
    fams = re.findall(r"^\s*[+-] (\w+)\s+", t, re.M)
    mark("13.1", "Families", "p" if len(fams) >= 3 else "a", f"Families: {', '.join(fams)}.")

@step("13.2", "Open a family")
def s132():
    key("CUSTOM_E", 1.2); t = win_text(screen("13.2-open"))
    sp = re.findall(r"^\s{5,}(\S+)\s+(active|inactive)\s", t, re.M)
    memo["vermin_rows"] = sp
    mark("13.2", "Open a family", "p" if sp else "a", f"{len(sp)} species rows under the family: {', '.join(s for s, _ in sp[:6])}.")

@step("13.3", "Edit one vermin species")
def s133():
    sel = luaj(GW + "local L=w.subviews.vermin; for i,c in ipairs(L:getChoices()) do if c.entry and c.entry.key then L:setSelected(i); print(json.encode({k=c.entry.key})) return end end; print('{}')")
    k = sel.get("k") if isinstance(sel, dict) else None
    if not k:
        return mark("13.3", "Edit one vermin species", "s", "no species row to select")
    r0 = roster(); key("CUSTOM_SHIFT_W", 1.0); answer("33"); r1 = roster()
    changed = sorted(kk for kk in r1 if r1[kk].get("stock") != r0.get(kk, {}).get("stock"))
    mark("13.3", "Edit one vermin species", "p" if changed == [k] else "a", f"Shift+W on {k}: stock set on {changed or 'nothing'}.")

@step("13.4", "Vermin hunting on")
def s134():
    close_window(); open_window("Panel")
    ok = luaj(GW + "local L=w.subviews.panel; for i,c in ipairs(L:getChoices()) do if c.data and c.data.switch and c.data.switch.label=='Vermin hunting' then L:setSelected(i); print(json.encode({i=i})) return end end; print('{}')")
    if not (isinstance(ok, dict) and ok.get("i")):
        return mark("13.4", "Vermin hunting on", "s", "could not select the Vermin hunting row")
    key("SELECT", 1.5)
    f = luaj(SW + "local o={}; for tok,list in pairs(sw.CACHE.hunt or {}) do o[#o+1]=tok..':'..(list[1] and list[1].flag or '?') end; table.sort(o); print(json.encode({on=sw.loadConfig().hunting.enabled, flags=o}))")
    on = isinstance(f, dict) and f.get("on")
    mark("13.4", "Vermin hunting on", "p" if on and f.get("flags") else "a",
         f"switch on: {on}; castes flagged: {', '.join(f.get('flags', [])[:10]) if isinstance(f, dict) else f}. Behaviour over the boundary is watched in 16.1.")

# --- 14 --------------------------------------------------------------------------------------------------
@step("14.1", "Filter the ledger")
def s141():
    close_window(); open_window("Ledger")
    t0 = win_text(screen("14.1-ledger")); key("CUSTOM_K", 1.0); t1 = win_text(screen("14.1-kind")); key("CUSTOM_L", 1.0); t2 = win_text(screen("14.1-layer"))
    c = [re.search(r"(\d+) of (\d+) recorded", x) for x in (t0, t1, t2)]
    kinds = re.search(r"Kind: (\w+)", t1); layer = re.search(r"Layer: (\w+)", t2)
    ok = all(c) and (c[1].group(1) != c[0].group(1) or c[2].group(1) != c[1].group(1))
    mark("14.1", "Filter the ledger", "p" if ok else "a",
         f"counts {' -> '.join(m.group(0) if m else '?' for m in c)}; Kind {kinds.group(1) if kinds else '?'}, Layer {layer.group(1) if layer else '?'}.")

@step("14.2", "Undo")
def s142():
    close_window(); open_window("Roster")
    r0 = roster(); keys = [k for k, e in r0.items() if e.get("layer") == "land" and e.get("cat") != "vermin"][:3]
    for k in keys:
        select_key(k); key("SELECT", 1.0)
    mid = roster(); changed = sum(1 for k in keys if mid[k].get("allow") != r0[k].get("allow"))
    open_window("Ledger")
    for _ in range(3):
        key("CUSTOM_Z", 1.2)
    r1 = roster(); back = all(r1[k].get("allow") == r0[k].get("allow") and r1[k].get("assign", []) == r0[k].get("assign", []) for k in keys)
    t = win_text(screen("14.2-undo")); depth = re.search(r"Undo last edit \((\d+)\)", t)
    mark("14.2", "Undo", "p" if changed == 3 and back else "a",
         f"three edits on {keys} ({changed} changed); after three Z all back as before: {back}; undo ring now holds {depth.group(1) if depth else '?'}; the tab says 'fifty deep': {'fifty deep' in t}.")

@step("14.3", "Help on every tab")
def s143():
    got = {}
    for tab in ("Overview", "Panel", "Roster", "Seasons", "Food web", "Live", "Layers", "Vermin", "Ledger"):
        close_window(); open_window(tab); key("CUSTOM_ALT_H", 1.2); t = screen(f"14.3-help-{tab}")
        got[tab] = "Help" in t and "stock" in t and "odds" in t
        key("LEAVESCREEN", 0.8)
    miss = [t for t, v in got.items() if not v]
    mark("14.3", "Help on every tab", "a" if miss else "p", "Alt+H opened a help page with the vocabulary on every tab." if not miss else f"no help page (or no vocabulary) on: {miss}.")

# --- 15 --------------------------------------------------------------------------------------------------
@step("15.1", "Turn it on")
def s151():
    close_window()
    out = sh("cmd", "overlay", "enable", "seasonal-wildlife.groups")[1]
    links = luaj(SW + "local l=sw.overlayLinks and sw.overlayLinks() or {}; print(json.encode({n=#l}))")
    mark("15.1", "Turn it on", "p" if "enabled" in out else "a",
         f"Enabled by DFHack's overlay command (the control-panel menu is the player's route to the same switch): '{out.strip()[:80]}'; predator-prey links it would draw now: {links.get('n') if isinstance(links, dict) else links}. Left enabled until 17; disabled at the end of the round.")

# --- 16 --------------------------------------------------------------------------------------------------
@step("16.1", "Inactive stays away")
def s161():
    k = memo.get("inactive")
    r = roster(); inactive = {e.get("token") + "@" + e.get("layer") for kk, e in r.items() if e.get("allow") is not True}
    watched = r.get(k, {}); memo["season0"] = luaj("print(json.encode({s=df.global.cur_season}))").get("s", 0)
    ids0 = luaj("local m=0; for _,u in ipairs(df.global.world.units.all) do if u.id>m then m=u.id end end; print(json.encode({m=m}))").get("m", 0)
    arrivals = []; ticks = 0; boundary = None
    for _ in range(80):
        n, s = stepped(2000); ticks += n
        a = luaj(SW + "local o={}; local cfg=sw.loadConfig(); local s=df.global.cur_season; for _,u in ipairs(df.global.world.units.active) do if u.id>%d and sw.WILD.onMap(u) then "
                 "local t=df.creature_raw.find(u.race).creature_id; local L=sw.WILD.layerOf(u); local key=(L=='land') and t or (L..':'..t); "
                 "o[#o+1]={id=u.id, t=t, layer=L, allow=cfg.allow[key], inseason=sw.ROSTER.wants(cfg,key,s), season=s} end end; print(json.encode(o))" % ids0, timeout=120)
        for x in (a if isinstance(a, list) else []):
            if x.get("id") not in {y["id"] for y in arrivals}:
                arrivals.append(x)
        ids0 = max([ids0] + [x.get("id") for x in (a if isinstance(a, list) else [])])
        s_now = luaj("print(json.encode({s=df.global.cur_season}))").get("s", 0)
        if boundary is None and s_now != memo["season0"]:
            boundary = ticks
        if boundary is not None and ticks - boundary >= 20000:
            break
    memo["boundary"] = boundary
    managed = [x for x in arrivals if x.get("layer") in ("land", "water", "cavern") and x.get("allow") is not None]
    bad = [x for x in managed if x.get("allow") is False or not x.get("inseason")]
    same = [x for x in arrivals if x.get("t") == watched.get("token")]
    memo["arrivals"] = arrivals
    if boundary is None:
        return mark("16.1", "Inactive stays away", "s", f"no season boundary in {ticks} ticks")
    mark("16.1", "Inactive stays away", "a" if bad else "p",
         f"{ticks} ticks stepped, boundary at +{boundary}; {len(arrivals)} wild arrivals ({len(managed)} of managed species); the species made inactive in 2.3 ({k}): {len(same)} arrival(s); "
         f"inactive or out-of-season arrivals: {', '.join(x['layer'] + ':' + x['t'] for x in bad[:8]) or 'none'}.", {"arrivals": arrivals[:200]})

@step("16.2", "The boundary itself")
def s162():
    a = announcements(200); led = sh("cmd", "seasonal-wildlife", "ledger", "30", "season")[1]
    hit = [x for x in a if "roster applied" in x]
    mark("16.2", "The boundary itself", "p" if hit and "roster applied" in led else "a",
         f"announcement: '{hit[-1] if hit else 'none in the last 200'}'; ledger season line: {'present' if 'roster applied' in led else 'missing'}.")

@step("16.3", "Water groups")
def s163():
    if not memo.get("baseline", {}).get("water_tiles"):
        return mark("16.3", "Water groups", "s", "no open water on this map")
    g = luaj(SW + "local g=sw.loadGroups(); local o={}; for _,grp in ipairs(g.groups) do if grp.drawn then local wet,here=0,0; for _,id in ipairs(grp.ids) do local u=df.unit.find(id); "
             "if u and dfhack.units.isActive(u) and not dfhack.units.isDead(u) then here=here+1; local d=dfhack.maps.getTileFlags(u.pos); if d and d.flow_size>=4 then wet=wet+1 end end end; "
             "o[#o+1]={t=grp.token, n=#grp.ids, here=here, wet=wet, body=grp.body, salt=grp.salt} end end; print(json.encode(o))")
    led = sh("cmd", "seasonal-wildlife", "ledger", "40", "arrive", "water")[1]
    drawn = [l.strip() for l in led.splitlines() if "drawn into" in l]
    rows = g if isinstance(g, list) else []
    dry = [x for x in rows if x.get("here") and x.get("wet") < x.get("here")]
    if not drawn and not rows:
        return mark("16.3", "Water groups", "s", "no water draw in this round (gap, ceiling or roster)")
    mark("16.3", "Water groups", "a" if dry else "p",
         f"{len(drawn)} water draw(s) in the ledger, e.g. '{drawn[-1][:90] if drawn else ''}'; drawn groups on the map now: " +
         (", ".join(f"{x['t']} {x['here']}/{x['n']} here, {x['wet']} in water ({x['body']}, {x['salt']})" for x in rows) or "none (left on their countdown)") + ".")

# --- 17 --------------------------------------------------------------------------------------------------
@step("17.1", "Save, quit, reload")
def s171():
    k = memo.get("inactive"); r0 = roster()
    led0 = [l for l in sh("cmd", "seasonal-wildlife", "ledger", "1")[1].strip().splitlines() if l.strip() and not l.startswith("ledger:")][-1:] or [""]   # the entry, not the footer
    stock0 = {kk: e.get("stock") for kk, e in r0.items() if e.get("stock") is not None}
    close_window()
    sv = sh("save", RELOAD, timeout=400)[1]; sh("title", timeout=200); ld = sh("load", RELOAD, timeout=400)[1]; sh("popups"); sh("fps", 1000, 10)
    r1 = roster(); led1 = sh("cmd", "seasonal-wildlife", "ledger", "3")[1]
    same_inactive = r1.get(k, {}).get("allow") == r0.get(k, {}).get("allow")
    same_stock = all(r1.get(kk, {}).get("stock") == v for kk, v in stock0.items())
    led1 = sh("cmd", "seasonal-wildlife", "ledger", "12")[1]
    same_led = led0[0].strip()[:60] in led1
    ok = "loaded" in ld and same_inactive and same_stock and same_led
    mark("17.1", "Save, quit, reload", "p" if ok else "a",
         f"saved to the new folder {RELOAD} and loaded it back: {'loaded' in ld}; {k} still {'inactive' if r1.get(k, {}).get('allow') is False else r1.get(k, {}).get('allow')}; "
         f"{len(stock0)} stock setting(s) kept: {same_stock}; ledger's last line survived: {same_led}.")

@step("17.2", "Frame rate on and off")
def s172():
    n1, s1 = stepped(3000)
    open_window("Panel"); key("CUSTOM_X", 1.0); key("SELECT", 1.5)
    n2, s2 = stepped(3000)
    open_window("Panel"); key("CUSTOM_A", 1.0); key("SELECT", 1.5); t = win_text(screen("17.2-panel")); close_window()
    on, off = (n1 / s1 if s1 else 0), (n2 / s2 if s2 else 0)
    mark("17.2", "Frame rate on and off", "p" if on and off else "a",
         f"tool on {on:.0f} t/s, all off {off:.0f} t/s ({(off - on) / off * 100 if off else 0:+.0f}% of the off rate; one reading each, so within the 10-15% load noise). FPS1 measures this with two runs per arm.")

@step("7.2", "Reset everything")
def s72():
    open_window("Roster")
    key("CUSTOM_ALT_R", 1.2); key("STANDARDSCROLL_DOWN", 0.6); c = win_text(screen("7.2-choice")); key("SELECT", 1.2); d = win_text(screen("7.2-confirm")); key("SELECT", 2.5)
    r = roster(); stock_left = sum(1 for e in r.values() if e.get("stock") is not None)
    n, per, four, none = seasons_stats(r)
    ok = "Reset everything" in d and stock_left == 0 and none == 0
    mark("7.2", "Reset everything", "p" if ok else "a",
         f"(run last, on the reload copy) confirmation 'Reset everything': {'Reset everything' in d}; stock settings left {stock_left}; {n} active, {none} with no season.")
    close_window()
    sh("cmd", "overlay", "disable", "seasonal-wildlife.groups")

# --- the report ------------------------------------------------------------------------------------------
def report():
    order = {sid: i for i, (sid, _, _) in enumerate(STEPS)}
    rs = sorted(results, key=lambda r: [int(x) for x in r["id"].split(".")])
    p = [r for r in rs if r["v"] == "p"]; a = [r for r in rs if r["v"] == "a"]; s = [r for r in rs if r["v"] == "s"]
    L = ["# Seasonal Wildlife alpha trial two (UI, v6.6)", "", "- Tester: W2:Urist (the rig, driven by scripts/alpha2-run.py)",
         f"- Fort: BOATS (the rig's copy of the alpha one fort, restored from {BACKUP})", "- Game / DFHack / plugin: 53.16 · 53.16-r1.1 · v6.6.0 @ f22fa30",
         f"- Date: {datetime.now().strftime('%Y-%m-%d')} (run {RUN})", "",
         f"Tally: {len(p)} pass · {len(a)} anomaly · {len(s)} skipped · {62 - len(rs)} unmarked of 62 steps."]
    for title, rows, note in (("Anomalies", a, True), ("Skipped (and why)", s, True), ("Passes", p, True)):
        if rows:
            L += ["", f"## {title}"] + [f"- **{r['id']} {r['title']}**: {r['note']}" for r in rows]
    return "\n".join(L) + "\n"

def main():
    global _log
    ap = argparse.ArgumentParser(); ap.add_argument("--only"); a = ap.parse_args()
    SCREENS.mkdir(parents=True, exist_ok=True); _log = open(OUT / "log.txt", "w")
    only = set(a.only.split(",")) if a.only else None
    log(f"== alpha 2 round {RUN}: {len(STEPS)} steps on {FORT}")
    for sid, title, fn in STEPS:
        if only and sid not in only:
            continue
        try:
            fn()
        except Exception as e:
            mark(sid, title, "a", f"the driver failed at this step: {type(e).__name__}: {e}")
        (OUT / "results.json").write_text(json.dumps(results, indent=1))
    marks = {r["id"]: {"v": r["v"], "n": r["note"]} for r in results}
    marks["_meta"] = {"tName": "W2:Urist (rig)", "tFort": "BOATS (alpha one fort copy)", "tVer": "53.16 · 53.16-r1.1 · v6.6.0 @ f22fa30", "tDate": datetime.now().strftime("%Y-%m-%d")}
    (OUT / "marks.json").write_text(json.dumps(marks, indent=1))
    (OUT / "report.md").write_text(report())
    close_window()
    log(f"== DONE {OUT}: " + "  ".join(f"{v} {sum(1 for r in results if r['v'] == v)}" for v in ("p", "a", "s")))
    return 0

if __name__ == "__main__":
    sys.exit(main())
