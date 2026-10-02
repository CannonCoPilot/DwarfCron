#!/usr/bin/env python3
"""Alpha Four section 7: run every check of 'What this page cannot check' in sequence (experiments/ALPHA4-SECTION7.md).

seasonal-wildlife v7.1 on DFHack 53.16-r2, fort RinghatchetsReady in world region9 (SEC7_FORT overrides). The rig must
be free: every stage loads, steps and quits DF. One RPC at a time, so the stages never overlap.

Stages, in order (item = the section 7 row it answers; see the doc's table):
  DEPLOY    host   copy chronicler/dfhack/scripts/*.lua (cx-sec7.lua is new) and the v7.1 tool (cmp-checked)
  FACTS     1 load what the fort offers -> data/alpha4-sec7/facts.json: cavern civ races, water bodies, savagery,
                   extinct rows, ticks to the season, the load's wall time and t/s. The blocks read it, so it runs first.
                   The same load runs the probes: SURV (10), AP1 desk + R28P (9), the extinct precondition (11),
                   the breathing scan (15)
  R2        1+1    item 15: dfhack-r2 REPORT section 4 on this fort (versions, a setting through save + reload,
                   occupancy after placement and a nudge, breathing, plugin states, the cx harness verbs)
  VALIDATE  1      items 14, 15: validate-full on the fort (every phase; phase_v71 last; gui.* and web.* claims)
  PANEL     1      item 14: the Panel on a real screen: every section, one step and its read-back, default back,
                   width at the frame edge, stderr.log; the Panel's refresh time with an irruption running
  WEBLOAD   10     item 14: the page open (polled as the page polls) against no page, n = 5 fresh loads per arm
  S7_*      eco    items 1-13: eco-run blocks (alpha4_sec7_blocks.py), n = 5 per arm, fresh load per arm
                   (tier CORE by default; --tier full adds the stream notes' other rig tests; ocean needs SEC7_OCEAN_FORT)

Usage: alpha4-sec7.py [--only STAGE|ITEM|BLOCK,...] [--tier core|full|ocean|all] [--reps 5] [--dry-run] [--plan]
       alpha4-sec7.py --list
  --only 6          every stage of item 6;  --only FACTS,S7_SKL  those two;  --skip VALIDATE  all but that
  --dry-run         nothing touches DF: eco-run and validate-full run their own dry runs, the runner's own stages walk
                    with empty replies, and every Lua chunk this runner and the blocks send goes through luac53 -p
  --plan            the wall-time estimate per stage and in total (load time and t/s from facts.json when measured)
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
FORT = os.environ.get("SEC7_FORT", "RinghatchetsReady")
TOOL = Path(os.environ.get("SW_TOOL", str(Path.home() / "Claude/Projects/sw-wt/deploy")))
LUAC = Path(os.environ.get("LUAC53", str(Path.home() / "Claude/Projects/sw-wt/.tools/luac53")))
FACTS = ROOT / "data/alpha4-sec7/facts.json"
WEB_PORT = 8642
DEF_LOAD_S, DEF_TPS = 180.0, 200.0      # unmeasured guesses for an 8x8 fort with open caverns; FACTS measures both

ITEMS = {
    1: "Skill writes act on new arrivals and do not rust",
    2: "Packs, stoops and fishing change kills",
    3: "The clock holds groups near the cap",
    4: "The cavern gate holds five; natives trimmed walk off",
    5: "A lost leader makes the group scatter",
    6: "Tokens act (irruption M1-M9, main experiment, T-*)",
    7: "Scavenging takes days, swimmers eat from the water",
    8: "Vermin eaters eat what they walk to",
    9: "The apex scheduler meets its presence target; the ladder meets 20% carnivores",
    10: "Pull, mix and guard shape the water",
    11: "Extinct corrections change arrivals",
    12: "Water auto-on and spill reach 3-5 groups",
    13: "Cost of every v7.1 change",
    14: "Panel and page round trips on a real screen",
    15: "Anything at all on DFHack 53.16-r2",
}
# S7_NAT answers five rows at once (one natural-arrivals block); the others belong to one row each
BLOCK_ITEMS = {"S7_NAT": (3, 4, 9, 10, 12), "S7_NATLEV": (3, 4, 9, 10, 12)}


# --------------------------------------------------------------------------------------------- eco-run as a lib --
def load_ecorun():
    spec = importlib.util.spec_from_file_location("ecorun_sec7", SCRIPTS / "eco-run.py")
    er = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(er)
    return er


ER = load_ecorun()
import alpha4_sec7_blocks as SB  # noqa: E402  (eco-run registered it already; this is the same module)

LUA_SENT: list[str] = []     # every Lua chunk this runner sends itself (checked by luac53 under --dry-run)
LOG = None


def say(m):
    line = f"{time.strftime('%H:%M:%S')} {m}"
    print(line, flush=True)
    if LOG:
        LOG.write(line + "\n"); LOG.flush()


def sh(*a, timeout=900, check=False):
    try:
        return ER.sh(*a, timeout=timeout, check=check)
    except Exception as e:   # one bad call never stops the stage: it is written down and judged
        say(f"   !! cx-lifecycle {' '.join(map(str, a))[:120]}: {e!r}"[:400])
        return ""


def lua(code, timeout=120):
    LUA_SENT.append(code)
    return sh("lua", code, timeout=timeout)


def nap(sec):
    """time.sleep, skipped in a dry run (nothing is drawing)."""
    if not ER.DRY:
        time.sleep(sec)


def eco_rows(text):
    return [l for l in text.splitlines() if l.startswith("eco ")]


def kv(line):
    return dict(t.split("=", 1) for t in line.split()[2:] if "=" in t)


def sec7(*a, timeout=300):
    """A cx-sec7 verb over `cmd` (CX_RPC_TIMEOUT 180 from eco-run's ENV): its eco rows."""
    return eco_rows(sh("cmd", "cx-sec7", *a, timeout=timeout))


def tool(*words, timeout=180):
    return sec7("toolall", *words, timeout=timeout)


def fresh_load():
    t0 = time.monotonic()
    if ER.DRY:
        ER.DRY.append(f"fresh_load {FORT}")
    else:
        ER.fresh_load(FORT, say)
    return time.monotonic() - t0


class Out:
    """The rows of one stage, written as TSV: stage, rep, arm, kind, key=value..."""
    def __init__(self, run, name):
        self.f = open(run / f"{name}.tsv", "a")
        self.name = name

    def put(self, rows, rep="-", arm="-"):
        for l in rows:
            p = l.split()
            self.f.write("\t".join([self.name, str(rep), arm, p[1] if len(p) > 1 else "?", " ".join(p[2:])]) + "\n")
        self.f.flush()

    def verdict(self, check, ok, got):
        self.f.write("\t".join([self.name, "-", "-", "VERDICT", f"check={check} ok={ok} got={str(got)[:300]}"]) + "\n")
        self.f.flush()
        say(f"   [{'PASS' if ok is True else 'FAIL' if ok is False else ok}] {check}: {str(got)[:160]}")


# ------------------------------------------------------------------------------------------------------ stages --
def st_deploy(run, a):
    say("== DEPLOY: chronicler scripts (cx-sec7.lua) and the v7.1 tool")
    sh("deploy", timeout=120)
    out = sh("deploy-tool", str(TOOL / "scripts"), timeout=300)
    say("   " + (out.strip().splitlines() or ["(dry)"])[-1][:200])


def derive(rows):
    d = {}
    f = next((kv(l) for l in rows if l.startswith("eco facts ")), {})
    bodies = {kv(l).get("body"): int(kv(l).get("tiles", 0) or 0) for l in rows if l.startswith("eco factbody ")}
    cav = [kv(l) for l in rows if l.startswith("eco factcav ")]
    ext = next((kv(l) for l in rows if l.startswith("eco factext ")), {})
    d["to_season"] = int(f.get("to_season", 33600) or 33600)
    d["savagery"] = int(f.get("savagery", -1) or -1)
    d["calm"] = 0 <= d["savagery"] < 66
    d["has_lake"], d["has_river"], d["has_ocean"] = bodies.get("lake", 0) > 0, bodies.get("river", 0) > 0, bodies.get("ocean", 0) > 0
    d["bodies"] = [b for b, n in bodies.items() if n > 0]
    civ = [c for c in cav if int(c.get("civ", 0) or 0) > 0]
    pred = [c for c in cav if int(c.get("pred", 0) or 0) > 0]
    ap = [c for c in cav if c.get("ap", "-") not in ("-", "")]
    d["has_civ"] = bool(civ)
    d["civ_cavern"] = int(civ[0]["cavern"]) if civ else (int(pred[0]["cavern"]) if pred else 1)
    d["pred_cavern"] = int(pred[0]["cavern"]) if pred else 1
    d["has_ap"] = bool(ap)
    d["ap_cavern"] = int(ap[0]["cavern"]) if ap else 0
    d["ap_token"] = ap[0]["ap"].split(",")[0] if ap else ""
    d["has_cavern_natives"] = any(int(c.get("wild_units", 0) or 0) > 0 for c in cav)
    d["extinct_in_embark"] = int(ext.get("in_embark", 0) or 0)
    d["extinct_apex"] = int(ext.get("apex", 0) or 0)
    d["r2"] = f.get("r2") == "true"
    d["rwe"] = f.get("rwe_param", "na")
    return d, f


def st_facts(run, a):
    say(f"== FACTS on {FORT} (and the one-load probes: SURV, AP1, R28P, extinct, breathing)")
    o = Out(run, "facts")
    load_s = fresh_load()
    rows = sec7("facts")
    o.put(rows)
    t0 = sec7("perf", "f0"); sh("step", 3000, timeout=900); t1 = sec7("perf", "f1")
    o.put(t0 + t1)
    tps = next((float(kv(l).get("tps", -1)) for l in t1 if l.startswith("eco perf ")), -1.0)
    d, f = derive(rows)
    d["load_s"], d["tps"] = round(load_s, 1), tps
    # --- probes on the same load
    p = Out(run, "probes")
    surv = tool("water", "depth") + tool("water", "depth", "full") + eco_rows(sh("cmd", "cx-eco", "depth", "sec7", timeout=300))
    surv += eco_rows(lua("local sw=reqscript('seasonal-wildlife'); local t=dfhack.getTickCount(); local ok,wt=pcall(sw.ENGINE.waterTiles,true);"
                         " local ms=dfhack.getTickCount()-t; print(('eco surv ok=%d ms=%d stopped=%s ncols=%s zreached=%s')"
                         ":format(ok and 1 or 0, ms, tostring(ok and wt.stopped), tostring(ok and wt.ncols), tostring(ok and wt.zReached)))"))
    p.put(surv, arm="SURV")
    s = next((kv(l) for l in surv if l.startswith("eco surv ")), {})
    p.verdict("SURV scan finishes inside its 1,000 ms budget", s.get("stopped") == "false", s)
    ap1 = sec7("ap1", "10", timeout=600)
    p.put(ap1, arm="AP1")
    r = {kv(l).get("ap_pick"): kv(l) for l in ap1 if l.startswith("eco ap1 ")}
    lo, hi = r.get("0.100", r.get("0.1", {})), r.get("1", {})
    p.verdict("AP1: animal people seated less at ap_pick 0.1 than at 1 (R13)",
              float(lo.get("ap_share", 9)) <= float(hi.get("ap_share", -1)) if lo and hi else "NO-DATA", {"0.1": lo, "1": hi})
    r28 = tool("place", "MAGMA_CRAB", "1") + tool("place", "MAGMA_CRAB", "1", "cavern") + tool("roster", "depth")
    p.put(r28, arm="R28P")
    txt = " ".join(kv(l).get("text", "") for l in r28 if l.startswith("eco toolline "))
    p.verdict("R28P: a magma crab is refused on the surface and in a cavern (R28/R60 named)", bool(re.search(r"R28|R60|deep", txt)), txt[:200])
    ext = tool("extinct", "status") + tool("extinct", "list")
    p.put(ext, arm="EXTINCT")
    p.verdict("extinct precondition (R24.4): the world's REAL_WORLD_EXTINCT setting and in-embark rows",
              "INFO", {"rwe_param": f.get("rwe_param"), "rwe_loader": f.get("rwe_loader"), "in_embark": d["extinct_in_embark"],
                       "apex": d["extinct_apex"]})
    br = sec7("breath", "load")
    p.put(br, arm="R2")
    sh("title", timeout=300)
    FACTS.parent.mkdir(parents=True, exist_ok=True)
    if not ER.DRY:
        FACTS.write_text(json.dumps({"fort": FORT, "read": time.strftime("%Y-%m-%d %H:%M"), "facts": f, "derived": d}, indent=1))
    say(f"   facts: {json.dumps(d)[:400]}")
    say(f"   load {load_s:.0f} s, {tps:.0f} t/s; written to {FACTS}" + (" (dry: not written)" if ER.DRY else ""))


def st_r2(run, a):
    say("== R2: dfhack-r2 REPORT section 4 on this fort")
    o = Out(run, "r2")
    sh("save-delete", "S7_R2_TMP", timeout=300)   # a leftover from an interrupted run: DF refuses a taken name
    fresh_load()
    v = eco_rows(lua("local d,c,r='?','?','?'; pcall(function() d=dfhack.getDFHackVersion() end);"
                     " pcall(function() c=dfhack.getDFVersion() end); pcall(function() r=dfhack.getDFHackRelease() end);"
                     " print(('eco ver dfhack=%s df=%s release=%s'):format(d,c,r))"))
    o.put(v)
    ver = kv(v[0]) if v else {}
    o.verdict("1 version: DFHack 53.16-r2", "53.16-r2" in (ver.get("dfhack", "") + ver.get("release", "")), ver)
    # 2 a setting through save and reload (saveSiteData / getSiteData across the changed GetCurrentSiteId)
    o.put(tool("hunters", "stoop", "chance", "61"))
    sh("save", "S7_R2_TMP", timeout=900); sh("title", timeout=300); sh("load", "S7_R2_TMP", timeout=1200)
    c = eco_rows(sh("cmd", "cx-eco", "cfg", "hunters.stoop.chance", timeout=120))
    o.put(c)
    o.verdict("2 a setting survives save and reload", any(kv(l).get("value") == "61" for l in c), c)
    # 3 occupancy after placement and a nudge (r2's teleport bookkeeping)
    sp = eco_rows(sh("cmd", "cx-eco", "spot", "land", timeout=300))
    s = kv(sp[-1]) if sp else {"x": "100", "y": "100", "z": "50"}
    o.put(eco_rows(sh("cmd", "cx-eco", "spawn", "DEER", "10", s["x"], s["y"], s["z"], "3", timeout=300)))
    o.put(eco_rows(sh("cmd", "cx-eco", "spawn", "WOLF", "4", str(int(s["x"]) + 45), s["y"], s["z"], "3", timeout=300)))
    o.put(sec7("cfgset", "ecology.nudge", "true", "ecology.far_tiles", "20"))
    o.put(tool("enable")); o.put(tool("groups", "ecology", "now"))
    sh("step", 200, timeout=600)
    occ = sec7("occ", "after_nudge")
    o.put(occ)
    oc = kv(occ[0]) if occ else {}
    o.verdict("3 no ghost-occupied tile and no doubly-occupied tile", oc.get("ghost") == "0" and oc.get("double") == "0", oc)
    # 4 breathing over units.all, after a water draw (the timestream trap)
    o.put(tool("water", "now")); sh("step", 20, timeout=300)
    br = sec7("breath", "after_water")
    o.put(br)
    b = kv(br[0]) if br else {}
    o.verdict("4 no dead or inactive unit reads not-FINE (else timestream never skips here)",
              b.get("nf_dead") == "0" and b.get("nf_inactive") == "0", b)
    # 6 plugins that r2 brought back must not be on by themselves
    pl = sh("cmd", "enable", timeout=120)
    on = [l.strip() for l in pl.splitlines() if re.search(r"(smooth-movement|stockflow).*(on|enabled)", l, re.I)]
    o.verdict("5 smooth-movement and stockflow are not enabled", not on, on or "off")
    # 7 the cx harness on r2: sustain, makeown, tp, rel, gather
    h = eco_rows(lua("dfhack.run_command('cx-load','sustain'); print('eco sustain ok=1')"))
    h += eco_rows(sh("cmd", "cx-load", "citizens", "1", timeout=300))
    h += eco_rows(sh("cmd", "cx-eco", "tp", "DEER", str(int(s["x"]) + 5), s["y"], s["z"], timeout=120))
    h += eco_rows(sh("cmd", "cx-probe", "gather", timeout=120))
    o.put(h)
    tp = next((kv(l) for l in h if l.startswith("eco tp ")), {})
    o.verdict("7 cx harness: sustain, citizens (makeown), tp", int(tp.get("units", 0) or 0) > 0, h[:4])
    sh("title", timeout=300)
    sh("save-delete", "S7_R2_TMP", timeout=300)


def st_validate(run, a):
    say(f"== VALIDATE: validate-full on {FORT} (every phase, phase_v71 last)")
    cmd = [sys.executable, str(SCRIPTS / "validate-full.py"), "--fort", FORT] + (["--dry-run"] if a.dry_run else [])
    env = dict(os.environ, SW_TOOL=str(TOOL))
    say("   $ " + " ".join(cmd))
    p = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, timeout=6 * 3600)
    (run / "validate.log").write_text(p.stdout + p.stderr)
    tail = [l for l in (p.stdout + p.stderr).splitlines() if l.strip()][-4:]
    for l in tail:
        say("   " + l[:200])


# The Panel: the window on the real screen (a DFHack screen cannot render headless). Per section: screen, one step
# (Right) on the selected row, the read-back line, the config path that changed, then `d` (default back).
PANEL_SECTIONS = 13
CFG_FLAT = ("local sw=reqscript('seasonal-wildlife'); local c=sw.loadConfig(); local out={};"
            " local function walk(t,p,d) if d>6 then return end; for k,v in pairs(t) do local q=p..(p~='' and '.' or '')..tostring(k);"
            " if type(v)=='table' then walk(v,q,d+1) elseif type(v)~='function' then out[#out+1]=q..'='..tostring(v) end end end;"
            " walk(c,'',0); table.sort(out); for _,l in ipairs(out) do print('cfgline '..l) end")


def cfg_flat():
    return {l[8:].split("=", 1)[0]: l[8:].split("=", 1)[1] for l in lua(CFG_FLAT).splitlines() if l.startswith("cfgline ") and "=" in l}


def st_panel(run, a):
    say("== PANEL: the window's Panel on the real screen")
    o = Out(run, "panel")
    shots = run / "panel"; shots.mkdir(exist_ok=True)
    fresh_load()
    o.put(tool("enable"))
    sh("cmd", "gui/seasonal-wildlife", timeout=120); nap(2.5)
    sh("ui", "click", "Panel", timeout=60); nap(1.5)
    rect = {}
    try:
        rect = json.loads(lua("local json=require('json'); local gw=reqscript('gui/seasonal-wildlife'); local w=gw.view and gw.view.subviews and gw.view.subviews[1];"
                              " print(json.encode(w and w.frame_rect and {x1=w.frame_rect.x1,x2=w.frame_rect.x2,y1=w.frame_rect.y1,y2=w.frame_rect.y2} or {}))").strip() or "{}")
    except ValueError:
        pass
    seen, steps, edge = [], 0, 0
    for i in range(PANEL_SECTIONS):
        before = cfg_flat()
        txt = sh("screen", timeout=120); (shots / f"s{i:02d}-a.txt").write_text(txt)
        m = re.search(r"^\s*\d+\|\s*([^\n]*?):\s+\d+ control", txt, re.M)
        name = m.group(1).strip() if m else f"section{i}"
        sh("key", "CURSOR_RIGHT", timeout=60); nap(1.2)
        after = cfg_flat()
        txt2 = sh("screen", timeout=120); (shots / f"s{i:02d}-b.txt").write_text(txt2)
        changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k)
                         and not k.startswith(("why.", "default_snapshot.", "ledger")))
        rb = [l for l in txt2.splitlines() if re.search(r"read back|refused", l)]
        sh("key", "CUSTOM_D", timeout=60); nap(1.0)
        back = cfg_flat()
        restored = all(back.get(k) == before.get(k) for k in changed)
        # width: a non-space glyph in the frame's last column is a clipped row (screen-check trap 2)
        x2 = rect.get("x2")
        clip = 0
        if x2:
            for l in txt2.splitlines():
                mm = re.match(r"^\s*(\d+)\|(.*)$", l)
                if mm and rect.get("y1", 0) <= int(mm.group(1)) <= rect.get("y2", 999):
                    body = mm.group(2)
                    if len(body) > x2 - 1 and body[x2 - 1] not in " |+-=#│║":
                        clip += 1
        edge += clip
        steps += 1 if changed else 0
        seen.append(name)
        o.put([f"eco panelsec n={i} name={name.replace(' ', '_')} changed={','.join(changed)[:200] or '-'} readback={len(rb)} "
               f"restored={int(restored)} clipped={clip}"])
        sh("key", "CUSTOM_S", timeout=60); nap(1.2)
    o.verdict("13 sections reached by S", len(set(seen)) >= PANEL_SECTIONS, seen)
    o.verdict("each section: a step changes the config and shows a read-back; d puts it back", f"{steps}/{PANEL_SECTIONS}", steps)
    o.verdict("no row clipped at the frame's edge", edge == 0, edge)
    # the Panel's refresh with an irruption running (ui.md: time it)
    o.put(sec7("cfgset", "irruption.enabled", "true", "irruption.need_breach", "false", "irruption.pause.start", "false",
               "irruption.zoom", "false", "irruption.popup", "false"))
    o.put(tool("irruption", "now", str(SB.facts().get("civ_cavern") or 1)))
    rt = eco_rows(lua("local gw=reqscript('gui/seasonal-wildlife'); local w=gw.view and gw.view.subviews and gw.view.subviews[1];"
                      " local f=w and (w.refreshPanel or w.refresh); local n,ms=0,0; if f then local t=dfhack.getTickCount();"
                      " for i=1,10 do if pcall(f,w) then n=n+1 end end; ms=(dfhack.getTickCount()-t)/10 end;"
                      " local sw=reqscript('seasonal-wildlife'); print(('eco panelrefresh calls=%d ms=%.1f groups=%d'):format(n, ms, #sw.loadGroups().groups))"))
    o.put(rt)
    o.verdict("Panel refresh time with an irruption running (no target in ui.md; recorded)", "INFO", rt)
    log = sh("logs", timeout=60)
    errs = [l for l in log.splitlines() if re.search(r"seasonal-wildlife.*(error|traceback)", l, re.I)]
    o.verdict("stderr.log has no seasonal-wildlife error after the walk", not errs, errs[:3])
    sh("key", "LEAVESCREEN", timeout=60)
    sh("title", timeout=300)


def _poll(tok, stop, counts):
    """What the open page does: /state.json every 2 s, /status.json every 5 s."""
    n = 0
    while not stop.is_set():
        for path in (["/state.json"] + (["/status.json"] if n % 5 == 0 else [])):
            p = subprocess.run(["curl", "-s", "-m", "10", "-o", "/dev/null", "-w", "%{http_code}",
                                f"http://127.0.0.1:{WEB_PORT}{path}?t={tok}"], capture_output=True, text=True)
            counts[p.stdout.strip() or "0"] = counts.get(p.stdout.strip() or "0", 0) + 1
        n += 2
        stop.wait(2.0)


def st_webload(run, a):
    say(f"== WEBLOAD: the page open vs no page, n = {a.reps} per arm, a fresh DF per rep")
    o = Out(run, "webload")
    arms = ["page_on", "page_off"]
    for rep in range(1, a.reps + 1):
        for arm in ER.ecolib.arm_order(arms, rep, "counterbalance"):
            fresh_load()
            o.put(tool("enable"), rep, arm)
            out = sh("cmd", "seasonal-wildlife-web", "start", str(WEB_PORT), timeout=60)
            m = re.search(r"\?t=([0-9a-f]+)", out or "")
            tok = m.group(1) if m else ""
            stop, counts = threading.Event(), {}
            th = None
            if arm == "page_on" and tok and not ER.DRY:
                th = threading.Thread(target=_poll, args=(tok, stop, counts), daemon=True); th.start()
            o.put(sec7("perf", "t0"), rep, arm)
            sh("step", 3000, timeout=900)
            o.put(sec7("perf", "t3000"), rep, arm)
            nap(30)   # paused: the page polls on; the frame rate is DF's draw cost alone
            st = eco_rows(lua("local W=_G.SW_WEB; local s=W and W.stats or {}; local e=df.global.enabler;"
                              " print(('eco webstats requests=%s snap_ms=%s snap_worst=%s status_ms=%s status_worst=%s fps=%s gfps=%s')"
                              ":format(tostring(s.requests), tostring(s.snap_ms), tostring(s.snap_worst), tostring(s.status_ms),"
                              " tostring(s.status_worst), tostring(e.calculated_fps), tostring(e.calculated_gfps)))"))
            stop.set()
            if th:
                th.join(timeout=15)
            o.put(st + [f"eco poll codes={json.dumps(counts).replace(' ', '')}"], rep, arm)
            sh("cmd", "seasonal-wildlife-web", "stop", timeout=60)
            sh("title", timeout=300)
    say("   tally: t/s (perf t3000 tps) and snap/status ms per arm; the claim is web.v71.perf (snap < 50 ms after the first)")


def st_block(run, a, name):
    b = ER.BLOCKS[name]
    req = b.get("sec7_requires")
    d = SB.facts()
    if req and not d.get(req):
        say(f"== {name}: NOT-TESTABLE-HERE on {b['fort']}: needs {req} (facts.json says no)")
        (run / "skipped.tsv").open("a").write(f"{name}\t{req}\n")
        return
    cmd = [sys.executable, str(SCRIPTS / "eco-run.py"), name, "--run", str(run / "eco"), "--reps", str(a.reps)]
    if a.dry_run:
        cmd.append("--dry-run")
    say(f"== {name} (item {', '.join(map(str, BLOCK_ITEMS.get(name, (b.get('sec7_item'),))))}; tier {b.get('sec7_tier')}): $ " + " ".join(cmd[1:]))
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=48 * 3600)
    (run / "eco").mkdir(exist_ok=True)
    (run / "eco" / f"{name}.runner.log").write_text(p.stdout + p.stderr)
    for l in [l for l in p.stdout.splitlines() if "MANIP-FAIL" in l or "FAILED" in l or "ABORTED" in l or "done" in l][-5:]:
        say("   " + l[:200])
    if p.returncode:
        say(f"   !! eco-run exited {p.returncode}: {(p.stderr or '').strip()[-300:]}")


# ------------------------------------------------------------------------------------------------ the registry --
def tiers(t):
    return {"core": ("CORE",), "full": ("CORE", "FULL"), "ocean": ("OCEAN",), "all": ("CORE", "FULL", "OCEAN")}[t]


def stages(a):
    S = [dict(name="DEPLOY", items=(), fn=st_deploy, est=lambda m: 0.5),
         dict(name="FACTS", items=(9, 10, 11, 15), fn=st_facts, est=lambda m: (m["load_s"] + 3000 / m["tps"]) / 60 + 4),
         dict(name="R2", items=(15,), fn=st_r2, est=lambda m: 2 * m["load_s"] / 60 + 4),
         dict(name="VALIDATE", items=(14, 15), fn=st_validate, est=lambda m: 25.0),
         dict(name="PANEL", items=(14,), fn=st_panel, est=lambda m: m["load_s"] / 60 + 6),
         dict(name="WEBLOAD", items=(14,), fn=st_webload,
              est=lambda m: 2 * a.reps * ((m["load_s"] + 3000 / m["tps"]) / 60 + 1.0))]
    want = tiers(a.tier)
    blocks = sorted((n for n, b in ER.BLOCKS.items() if n.startswith("S7_") and b.get("sec7_tier") in want),
                    key=lambda n: (ER.BLOCKS[n].get("sec7_item", 99), n))
    for n in blocks:
        b = ER.BLOCKS[n]
        S.append(dict(name=n, items=BLOCK_ITEMS.get(n, (b.get("sec7_item"),)), fn=(lambda run, a, n=n: st_block(run, a, n)),
                      est=(lambda m, b=b: ER.ecolib.estimate(b, a.reps, "arm", tps=m["tps"], load_s=m["load_s"],
                                                             wipe=b.get("wipe", True))["minutes"]), block=n))
    return S


def selected(S, a):
    if not a.only:
        pick = S
    else:
        keys = {k.strip() for k in a.only.split(",") if k.strip()}
        pick = [s for s in S if s["name"] in keys or any(str(i) in keys for i in s["items"])]
    skip = {k.strip() for k in (a.skip or "").split(",") if k.strip()}
    return [s for s in pick if s["name"] not in skip]


def measured():
    m = {"load_s": DEF_LOAD_S, "tps": DEF_TPS, "measured": False}
    try:
        d = json.loads(FACTS.read_text()).get("derived", {})
        if d.get("load_s", 0) > 0 and d.get("tps", 0) > 0:
            m.update(load_s=float(d["load_s"]), tps=float(d["tps"]), measured=True)
    except (OSError, ValueError):
        pass
    return m


def plan(S, a):
    m = measured()
    d = SB.facts()
    tot = 0.0
    print(f"{'stage':<12} {'tier':<5} {'items':<14} {'minutes':>8}  note")
    for s in S:
        b = ER.BLOCKS.get(s.get("block", ""), {})
        req = b.get("sec7_requires")
        skip = bool(req and not d.get(req))
        mins = 0.0 if skip else s["est"](m)
        tot += mins
        print(f"{s['name']:<12} {b.get('sec7_tier', '-'):<5} {','.join(map(str, s['items'])) or '-':<14} {mins:>8.1f}  "
              f"{'skipped: needs ' + req if skip else ''}")
    print(f"total about {tot / 60:.1f} h at {m['tps']:.0f} t/s and {m['load_s']:.0f} s per load "
          f"({'measured by FACTS' if m['measured'] else 'unmeasured guesses: run FACTS first'}); n = {a.reps} per arm")
    return tot


def luac_check(chunks):
    bad = 0
    with tempfile.TemporaryDirectory() as td:
        for i, c in enumerate(chunks):
            f = Path(td) / f"c{i}.lua"
            f.write_text(c)
            p = subprocess.run([str(LUAC), "-p", str(f)], capture_output=True, text=True)
            if p.returncode:
                bad += 1
                say(f"   luac53: {p.stderr.strip()[:200]}  <- {c[:120]}")
    return bad


def block_chunks():
    """Every lua: step of every S7_ block, with eco-run's placeholders filled as eco-run fills them."""
    out = []
    for n, b in ER.BLOCKS.items():
        if not n.startswith("S7_"):
            continue
        for c in b["cells"].values():
            for st in list(c.get("steps", [])) + list(c.get("post", [])):
                if st.startswith("lua:"):
                    s = re.sub(r"\{ids:(\w+)\}", "1,2", st[4:])
                    s = re.sub(r"\{(F?[XYZ])([+-]\d+)?\}", "10", s)
                    out.append(s)
    return out


def main():
    global LOG
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--only")
    ap.add_argument("--skip")
    ap.add_argument("--tier", choices=["core", "full", "ocean", "all"], default="core")
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    S = selected(stages(a), a)
    if a.list:
        for s in S:
            b = ER.BLOCKS.get(s.get("block", ""), {})
            print(f"{s['name']:<12} items {','.join(map(str, s['items'])) or '-':<12} {b.get('sec7_tier', '')}"
                  f"{'  needs ' + b['sec7_requires'] if b.get('sec7_requires') else ''}")
        return 0
    if a.plan:
        plan(S, a)
        return 0
    stamp = time.strftime("%Y%m%d-%H%M%S")
    run = Path(tempfile.mkdtemp(prefix="alpha4-sec7-dry-")) if a.dry_run else ROOT / "data/alpha4-sec7" / stamp
    run.mkdir(parents=True, exist_ok=True)
    LOG = open(run / "log.txt", "a")
    if a.dry_run:
        ER.DRY.append("dry-run")
    say(f"alpha4-sec7: {len(S)} stage(s) on {FORT}, tier {a.tier}, n = {a.reps}{', DRY RUN' if a.dry_run else ''} -> {run}")
    t0 = time.monotonic()
    for s in S:
        ts = time.monotonic()
        try:
            s["fn"](run, a)
        except Exception as e:   # a stage that raises is written down; the next stage still runs
            say(f"   !! {s['name']} raised {e!r}"[:400])
        say(f"   {s['name']}: {(time.monotonic() - ts) / 60:.1f} min")
    if a.dry_run:
        chunks = block_chunks() + LUA_SENT
        bad = luac_check(chunks)
        say(f"dry run: {len(chunks)} Lua chunks through luac53 ({bad} failed); {len(ER.DRY) - 1} runner rig calls recorded")
        (run / "dry-calls.txt").write_text("\n".join(map(str, ER.DRY[1:])) + "\n")
        bad += subprocess.run([str(LUAC), "-p", str(ROOT / "chronicler/dfhack/scripts/cx-sec7.lua")]).returncode
        say(f"=== alpha4-sec7 dry run {'clean' if not bad else 'FOUND ' + str(bad) + ' PROBLEM(S)'} ({(time.monotonic() - t0):.0f} s)")
        return 1 if bad else 0
    say(f"=== alpha4-sec7 done in {(time.monotonic() - t0) / 3600:.1f} h -> {run}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
