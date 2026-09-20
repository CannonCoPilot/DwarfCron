#!/usr/bin/env python3
"""E41f — aquatic predator vs aquatic prey in ONE cavern's water: does a written relation make a cave
crocodile hunt giant cave toads that share its water?
E41b showed the relation does not pull a crocodile out of its water for floor prey. This puts both in
cave 13's water (depth 1) with `place ... cavern 1` (v5.9.5) -- one CROCODILE_CAVE, three
TOAD_GIANT_CAVE -- and writes PREDATOR_OR_PREY between the crocodile and each toad directly, because
the toad is a LARGE_PREDATOR in the raws and the tool's classifier would never pair it as prey. Tool
disabled in both arms, so this measures the mechanism the tool would use:
  none -- placed, no relation written
  rel  -- placed, relation written at t0
Two replicates per arm, 6,000 ticks. Reads: toads dead (and the crocodile), incident records naming
victim and criminal, crocodile-to-nearest-toad distance per sample. Subject receipt: all four placed,
in water, same depth, all with an enemy-status slot; else VACUOUS. One RPC at a time. Never saves.
"""
import json, re, subprocess, sys, datetime as dt
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
CX = str(ROOT / "scripts/cx-lifecycle.sh")
RUN = ROOT / "data/experiments/E41f" / dt.datetime.now().strftime("%Y%m%d-%H%M%S"); RUN.mkdir(parents=True)
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
    out = sh("cmd", "seasonal-wildlife", "place", tok, str(n), "cavern", "1"); m = re.search(r"at ids ([\d,]+)", out)
    return [int(x) for x in m.group(1).split(",")] if m else [], (out.strip().splitlines() or [out])[0][:120]
def state(pred, prey):
    return luaj("local ur=df.global.world.world_data.underground_regions; local function rec(id) local u=df.unit.find(id); if not u then return {gone=true} end; "
                "local d=dfhack.maps.getTileFlags(u.pos); return {dead=dfhack.units.isDead(u), x=u.pos.x, y=u.pos.y, z=u.pos.z, water=(d.flow_size>=4 and not d.liquid_type), sub=d.subterranean, "
                "slot=u.enemy.enemy_status_slot, depth=ur[u.animal.population.cave_id] and ur[u.animal.population.cave_id].layer_depth or -1} end; "
                f"local p=rec({pred}); local prey={{}}; local best=999; for _,id in ipairs({{{','.join(map(str, prey))}}}) do local r=rec(id); prey[#prey+1]=r; "
                "if not r.gone and not r.dead and not p.gone and not p.dead then local d=math.max(math.abs(r.x-p.x), math.abs(r.y-p.y)); if d<best then best=d end end end; "
                "print(json.encode({pred=p, prey=prey, nearest=best, tick=df.global.cur_year*403200+df.global.cur_year_tick}))")
rows = []
for rep in (1, 2):
    for arm in ("none", "rel"):
        log(f"== rep {rep} arm {arm}: restore + load CTRL")
        sh("save-restore", "CTRL.preverify"); out = sh("load", "CTRL"); log("  " + out.strip().splitlines()[-1][:100])
        sh("cmd", "seasonal-wildlife", "disable")
        pred, r1 = place("CROCODILE_CAVE", 1); prey, r2 = place("TOAD_GIANT_CAVE", 3)
        log(f"  {r1}\n  {r2}")
        if len(pred) != 1 or len(prey) != 3:
            log("  VACUOUS: the subject was not placed"); rows.append({"rep": rep, "arm": arm, "vacuous": True}); continue
        s0 = state(pred[0], prey)
        allw = s0["pred"]["water"] and all(p["water"] for p in s0["prey"])
        depths = {s0["pred"]["depth"]} | {p["depth"] for p in s0["prey"]}
        slots = [s0["pred"]["slot"]] + [p["slot"] for p in s0["prey"]]
        log(f"  placed: crocodile z{s0['pred']['z']} water={s0['pred']['water']}; toads water={[p['water'] for p in s0['prey']]} depths {sorted(depths)} slots {slots}; nearest {s0['nearest']} tiles")
        if not allw or len(depths) != 1 or any(x < 0 for x in slots):
            log("  VACUOUS: not all in one cavern's water with slots"); rows.append({"rep": rep, "arm": arm, "vacuous": True}); continue
        written = 0
        if arm == "rel":
            w = luaj(f"local c=df.global.world.enemy_status_cache; local v=df.unit_reaction_type.PREDATOR_OR_PREY; local a=df.unit.find({pred[0]}); local sa=a.enemy.enemy_status_slot; local n=0; "
                     f"for _,id in ipairs({{{','.join(map(str, prey))}}}) do local b=df.unit.find(id); local sb=b.enemy.enemy_status_slot; c.rel_map[sa][sb].ur=v; c.rel_map[sb][sa].ur=v; n=n+1 end; print(json.encode({{written=n}}))")
            written = w.get("written", 0); log(f"  relation written for {written} pair(s)")
        t0 = s0["tick"]; samples = []
        for k in range(BUDGET // SAMPLE):
            sh("step", str(SAMPLE), "400", timeout=500); st = state(pred[0], prey)
            dead = sum(1 for p in st["prey"] if p.get("dead") or p.get("gone"))
            samples.append({"at": st["tick"] - t0, "dead": dead, "nearest": st["nearest"], "pred_dead": st["pred"].get("dead"), "pred_z": st["pred"].get("z"), "pred_water": st["pred"].get("water")})
            log(f"  +{st['tick'] - t0}: toads dead {dead}/3, crocodile dead={st['pred'].get('dead')} at z{st['pred'].get('z')} water={st['pred'].get('water')}, nearest living toad {st['nearest']} tiles")
        att = luaj("local ids={" + ",".join(map(str, prey + pred)) + "}; local set={}; for _,i in ipairs(ids) do set[i]=true end; local who={}; "
                   "for _,inc in ipairs(df.global.world.incidents.all) do if set[inc.victim] then local k=inc.criminal; local ku=k>=0 and df.unit.find(k); "
                   "who[#who+1]=('victim #%d by %s#%d'):format(inc.victim, ku and df.creature_raw.find(ku.race).creature_id or '?', k) end end; print(json.encode({incidents=who}))")
        log(f"  incidents: {att.get('incidents')}")
        rows.append({"rep": rep, "arm": arm, "vacuous": False, "pred": pred[0], "prey": prey, "written": written, "samples": samples, "incidents": att.get("incidents")})
        (RUN / "rows.json").write_text(json.dumps(rows, indent=1))
log("== TALLY")
for r in rows:
    if r.get("vacuous"): log(f"  rep {r['rep']} {r['arm']}: VACUOUS"); continue
    last = r["samples"][-1]
    log(f"  rep {r['rep']} {r['arm']:4s}: written {r['written']}  toads dead at end {last['dead']}/3  by sample {[s['dead'] for s in r['samples']]}  crocodile dead={last['pred_dead']}  incidents {r['incidents']}")
log(f"== DONE {RUN}")
