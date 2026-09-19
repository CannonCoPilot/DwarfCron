#!/usr/bin/env python3
"""E41 — does the tool's ecology make a cavern predator hunt cavern prey?
Surface (E11c/E16/E17): writing PREDATOR_OR_PREY into enemy_status_cache.rel_map for a LARGE_PREDATOR
unit and a target makes the predator attack. This asks the same inside one cavern realm. On CTRL's
preverify save, place one CROCODILE_CAVE and four CRUNDLE -- both resolve to depth 1 (cave 13), the
crocodile in cavern water, the crundles on the cavern floor -- then 6,000 ticks:
  off -- tool disabled (no relation is written)
  eco -- tool enabled, cavern layer on, ecology on; `groups ecology now` right after placement
Two replicates per arm. Read: crundles dead among the four placed, the crocodile's distance to the
nearest living crundle, and the pairs the ecology reports. Subject receipt: all five placed, same
depth, else VACUOUS. One RPC at a time. Never saves.
"""
import json, re, subprocess, sys, datetime as dt
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
CX = str(ROOT / "scripts/cx-lifecycle.sh")
RUN = ROOT / "data/experiments/E41b" / dt.datetime.now().strftime("%Y%m%d-%H%M%S"); RUN.mkdir(parents=True)
LOG = open(RUN / "log.txt", "a")
BUDGET, SAMPLE = int(sys.argv[1]) if len(sys.argv) > 1 else 6000, 1500
def log(m):
    line = f"{dt.datetime.now():%H:%M:%S} {m}"; print(line, flush=True); LOG.write(line + "\n"); LOG.flush()
def sh(*a, timeout=300):
    p = subprocess.run([CX, *a], capture_output=True, text=True, timeout=timeout, cwd=ROOT); return (p.stdout or "") + (p.stderr or "")
def luaj(code, timeout=120):
    out = sh("lua", "local json=require('json'); " + code, timeout=timeout); i = out.find("{"); j = out.rfind("}")
    return json.loads(out[i:j+1]) if i != -1 else {"_raw": out}
def place(tok, n):
    out = sh("cmd", "seasonal-wildlife", "place", tok, str(n), "cavern"); m = re.search(r"at ids ([\d,]+)", out)
    return [int(x) for x in m.group(1).split(",")] if m else [], out.strip().splitlines()[0][:120] if out.strip() else out
def state(pred, prey):
    return luaj("local ur=df.global.world.world_data.underground_regions; local function rec(id) local u=df.unit.find(id); if not u then return {gone=true} end; "
                "return {dead=dfhack.units.isDead(u), x=u.pos.x, y=u.pos.y, z=u.pos.z, depth=ur[u.animal.population.cave_id] and ur[u.animal.population.cave_id].layer_depth or -1} end; "
                f"local p=rec({pred}); local prey={{}}; local best=999; for _,id in ipairs({{{','.join(map(str, prey))}}}) do local r=rec(id); prey[#prey+1]=r; "
                "if not r.gone and not r.dead and not p.gone then local d=math.max(math.abs(r.x-p.x), math.abs(r.y-p.y)); if d<best then best=d end end end; "
                "print(json.encode({pred=p, prey=prey, nearest=best, tick=df.global.cur_year*403200+df.global.cur_year_tick}))")
rows = []
for rep in (1, 2):
    for arm in ("off", "eco"):
        log(f"== rep {rep} arm {arm}: restore + load CTRL")
        sh("save-restore", "CTRL.preverify"); out = sh("load", "CTRL"); log("  " + out.strip().splitlines()[-1][:100])
        # E41b: BOTH arms run the tool enabled with the cavern layer on and the cavern gate OFF, so the
        # only difference is the ecology switch; E41's off arm had the whole tool off and its on arm
        # let the cavern gate bring other predators in (E40), which confounded the deaths.
        sh("cmd", "seasonal-wildlife", "disable")
        log("  " + sh("cmd", "seasonal-wildlife", "layer", "cavern", "on").strip()[:80])
        log("  " + sh("cmd", "seasonal-wildlife", "groups", "cavern", "off").strip()[:80])
        log("  " + sh("cmd", "seasonal-wildlife", "groups", "ecology", "on" if arm == "eco" else "off").strip()[:80])
        log("  " + sh("cmd", "seasonal-wildlife", "enable").strip()[:40])
        pred, r1 = place("CROCODILE_CAVE", 1); prey, r2 = place("CRUNDLE", 4)
        log(f"  {r1}\n  {r2}")
        if len(pred) != 1 or len(prey) != 4:
            log("  VACUOUS: the subject was not placed"); rows.append({"rep": rep, "arm": arm, "vacuous": True}); continue
        s0 = state(pred[0], prey)
        depths = {s0["pred"]["depth"]} | {p["depth"] for p in s0["prey"]}
        log(f"  placed: crocodile z{s0['pred']['z']} depth {s0['pred']['depth']}; crundles depths {sorted(depths)}; nearest {s0['nearest']} tiles")
        if len(depths) != 1:
            log("  VACUOUS: predator and prey are not in one realm"); rows.append({"rep": rep, "arm": arm, "vacuous": True}); continue
        pairs = None
        if arm == "eco":
            out = sh("cmd", "seasonal-wildlife", "groups", "ecology", "now"); log("  " + out.strip()[:200])
            m = re.search(r"(\d+) predator\(s\) x (\d+) target\(s\), (\d+) pair\(s\)", out); pairs = [int(x) for x in m.groups()] if m else None
        t0 = s0["tick"]; samples = []
        for k in range(BUDGET // SAMPLE):
            sh("step", str(SAMPLE), "400", timeout=500); st = state(pred[0], prey)
            dead = sum(1 for p in st["prey"] if p.get("dead") or p.get("gone"))
            samples.append({"at": st["tick"] - t0, "dead": dead, "nearest": st["nearest"], "pred_dead": st["pred"].get("dead"), "pred_z": st["pred"].get("z")})
            log(f"  +{st['tick'] - t0}: crundles dead/gone {dead}/4, crocodile at z{st['pred'].get('z')} nearest living crundle {st['nearest']} tiles")
        # attribution: DF's own combat reports naming the crocodile and a crundle; and the job's last write
        att = luaj("local n,hits=0,0; for _,r in ipairs(df.global.world.status.reports) do local t=r.text:lower(); if t:find('crocodile') and t:find('crundle') then hits=hits+1 end; n=n+1 end; print(json.encode({reports=n, croc_x_crundle=hits}))")
        eco_end = sh("cmd", "seasonal-wildlife", "groups", "ecology").strip()[:200]
        log(f"  reports naming crocodile+crundle: {att.get('croc_x_crundle')} of {att.get('reports')}; {eco_end}")
        rows.append({"rep": rep, "arm": arm, "vacuous": False, "pred": pred[0], "prey": prey, "pairs": pairs, "samples": samples, "reports": att, "eco_end": eco_end})
        (RUN / "rows.json").write_text(json.dumps(rows, indent=1))
        sh("cmd", "seasonal-wildlife", "disable")
log("== TALLY")
for r in rows:
    if r.get("vacuous"): log(f"  rep {r['rep']} {r['arm']}: VACUOUS"); continue
    last = r["samples"][-1]
    log(f"  rep {r['rep']} {r['arm']:3s}: crundles dead/gone at end {last['dead']}/4  by sample {[s['dead'] for s in r['samples']]}  combat reports croc+crundle {r.get('reports',{}).get('croc_x_crundle')}  | {r.get('eco_end','')[:110]}")
log(f"== DONE {RUN}")
