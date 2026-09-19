#!/usr/bin/env python3
"""E40 — does DF's one-group-per-source gate hold underground?
Surface (E1/G1-G2): while any unit of the current wave still carries
flags2.roaming_wilderness_population_source, no new wave comes from that source; clear the flag
and the next wave lists within ~450-1,500 ticks. This asks the same of a CAVERN source, with the
tool DISABLED, on CTRL's preverify save. Two arms x two replicates (the user's pace rule):
  hold   -- touch nothing; count new cavern wild units over the budget
  detach -- clear the roaming flags on every gated cavern unit at t0; count the same
Subject receipt first: a replicate with no gated cavern unit at baseline is VACUOUS and is not an
arm. Arrivals are attributed by NEW unit id, cave depth 0-2 only. One RPC at a time. Never saves.
"""
import json, re, subprocess, sys, time, datetime as dt
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
CX = str(ROOT / "scripts/cx-lifecycle.sh")
RUN = ROOT / "data/experiments/E40" / dt.datetime.now().strftime("%Y%m%d-%H%M%S")
RUN.mkdir(parents=True)
LOG = open(RUN / "log.txt", "a")
BUDGET, SAMPLE = int(sys.argv[1]) if len(sys.argv) > 1 else 8000, 2000
def log(msg):
    line = f"{dt.datetime.now():%H:%M:%S} {msg}"; print(line, flush=True); LOG.write(line + "\n"); LOG.flush()
def sh(*a, timeout=300):
    p = subprocess.run([CX, *a], capture_output=True, text=True, timeout=timeout, cwd=ROOT); return (p.stdout or "") + (p.stderr or "")
def luaj(code, timeout=120):
    out = sh("lua", "local json=require('json'); " + code, timeout=timeout)
    i = out.find("{"); j = out.rfind("}")
    return json.loads(out[i:j+1]) if i != -1 else {"_raw": out}
CENSUS = ("local ur=df.global.world.world_data.underground_regions; local maxid=0; for _,u in ipairs(df.global.world.units.all) do if u.id>maxid then maxid=u.id end end; "
          "local gated,units={}, {}; for _,u in ipairs(df.global.world.units.active) do local r=u.animal.population; "
          "if dfhack.units.isWildlife(u) and not dfhack.units.isDead(u) and not u.flags1.inactive and r.cave_id~=-1 and r.feature_idx==-1 then "
          "local d=ur[r.cave_id] and ur[r.cave_id].layer_depth or -1; if d>=0 and d<=2 then local cr=df.creature_raw.find(u.race); "
          "units[#units+1]={id=u.id, token=cr and cr.creature_id or '?', depth=d, z=u.pos.z, gated=u.flags2.roaming_wilderness_population_source and true or false}; "
          "if u.flags2.roaming_wilderness_population_source then gated[#gated+1]=u.id end end end end; "
          "print(json.encode({maxid=maxid, tick=df.global.cur_year*403200+df.global.cur_year_tick, gated=gated, units=units}))")
def census(): return luaj(CENSUS)
rows = []
for rep in (1, 2):
    for arm in ("hold", "detach"):
        log(f"== rep {rep} arm {arm}: restore + load CTRL")
        sh("save-restore", "CTRL.preverify"); out = sh("load", "CTRL"); log("  " + out.strip().splitlines()[-1][:120])
        out = sh("cmd", "seasonal-wildlife", "disable"); log("  tool: " + out.strip()[:60])
        base = census(); gated = base.get("gated", [])
        log(f"  baseline: {len(base.get('units', []))} cavern wild units, {len(gated)} gated: {[ (u['token'], u['depth']) for u in base.get('units', []) if u['gated'] ]}")
        if not gated:
            log("  VACUOUS: no gated cavern unit at baseline — this replicate is not an arm"); rows.append({"rep": rep, "arm": arm, "vacuous": True}); continue
        if arm == "detach":
            out = luaj("local n=0; for _,id in ipairs({" + ",".join(map(str, gated)) + "}) do local u=df.unit.find(id); if u then u.flags2.roaming_wilderness_population_source=false; u.flags2.roaming_wilderness_population_source_not_a_map_feature=false; n=n+1 end end; print(json.encode({cleared=n}))")
            log(f"  detach: cleared the gate flag on {out.get('cleared')} unit(s)")
        maxid, t0 = base["maxid"], base["tick"]; seen = {}
        for k in range(BUDGET // SAMPLE):
            sh("step", str(SAMPLE), "400", timeout=500)
            c = census()
            new = [u for u in c.get("units", []) if u["id"] > maxid and u["id"] not in seen]
            for u in new: seen[u["id"]] = u; u["at"] = c["tick"] - t0
            log(f"  +{c['tick'] - t0} ticks: {len(seen)} new cavern arrival(s) so far" + (f" — new: {[(u['token'], u['depth']) for u in new]}" if new else ""))
        rows.append({"rep": rep, "arm": arm, "vacuous": False, "gated_at_t0": len(gated), "arrivals": list(seen.values()), "ticks": c["tick"] - t0})
        (RUN / "rows.json").write_text(json.dumps(rows, indent=1))
log("== TALLY")
for r in rows:
    if r.get("vacuous"): log(f"  rep {r['rep']} {r['arm']}: VACUOUS"); continue
    by = {}
    for u in r["arrivals"]: by[u["token"]] = by.get(u["token"], 0) + 1
    log(f"  rep {r['rep']} {r['arm']:6s}: {len(r['arrivals'])} new cavern unit(s) in {r['ticks']} ticks  {by}  first at {min([u['at'] for u in r['arrivals']], default='-')}")
(RUN / "rows.json").write_text(json.dumps(rows, indent=1))
log(f"== DONE {RUN}")
