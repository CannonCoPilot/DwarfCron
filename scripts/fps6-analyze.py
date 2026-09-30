#!/usr/bin/env python3
"""FPS6 analysis (design: experiments/FPS6-design.md, Analysis 1-4). Usage: fps6-analyze.py <FPS6 run dir>

The world is the unit of replication: each session's play readings are averaged first, then the world's sessions.
  1. log(ms/tick) = a + b*log(world area) + c*log(1 + history years); b and c are elasticities.
  2. The same with the world-scale counts from `cx-load world` (live historical figures, armies, events) in place of
     the design factors, one at a time: which count carries the effect, if any.
  3. Once-per-load costs -- load time, footprint at load, save size, generation time -- on the design factors.
  4. The season curve per world: log(t/s) on ticks played (slope = % speed lost per 100k ticks), then the slopes on
     the design factors: does a bigger or older world make the process age faster?
The fort differs per world (the site rule picks a different tile), so 1 is repeated with the fort's own load (citizens,
wild units, items) as covariates.
"""
import csv, importlib.util, statistics, sys
from collections import defaultdict
from pathlib import Path
from typing import Any
import numpy as np

_spec: Any = importlib.util.spec_from_file_location("fps5a", Path(__file__).with_name("fps5-analyze.py"))
fps5 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(fps5)
f, ols = fps5.f, fps5.ols
SIZES = ("SMALLER", "SMALL", "MEDIUM", "LARGE")

def tsv(d, name):
    p = Path(d) / name
    return list(csv.DictReader(open(p), delimiter="\t")) if p.exists() else []

def mean(xs):
    xs = [x for x in xs if x == x]
    return statistics.mean(xs) if xs else float("nan")

def fit(label, per, keys, names):
    """OLS of log(y) on the named predictors over worlds; skipped when there are not enough worlds to fit."""
    rows = [(v["y"], [v[k] for k in keys]) for v in per.values() if all(v[k] == v[k] for k in keys) and v["y"] == v["y"] and v["y"] > 0]
    print(f"\n  {label}")
    if len(rows) < len(keys) + 2:
        print(f"    skipped: {len(rows)} world(s), need {len(keys) + 2}")
        return
    flat = [n for i, n in enumerate(names) if len({x[i] for _, x in rows}) < 2] + (["the outcome"] if len({y for y, _ in rows}) < 2 else [])
    if flat:
        print(f"    skipped: {', '.join(flat)} the same in every world")
        return
    ols([[1] + x for _, x in rows], [np.log(y) for y, _ in rows], ["a"] + names)

def main(d):
    worlds = {w["world"]: w for w in tsv(d, "worlds.tsv") if w["status"] == "ok"}
    loads, rows = tsv(d, "loads.tsv"), [r for r in tsv(d, "rows.tsv") if r.get("tps")]
    print(f"== FPS6 {d}: {len(worlds)} world(s) ok, {len(loads)} load(s), {len(rows)} reading(s)")

    sess = defaultdict(list)
    for r in rows:
        sess[(r["world"], r["rep"])].append(r)
    W = {}
    for key, w in worlds.items():
        ss = [g for (k, _), g in sess.items() if k == key]
        play = [[r for r in g if r["phase"] == "play"] for g in ss]
        ld = [l for l in loads if l["world"] == key]
        v: dict[str, Any] = dict(w=w, n_sess=sum(1 for p in play if p), area=np.log(f(w, "world_dim") ** 2), hist=np.log(1 + f(w, "years")))
        v["ms"] = mean([mean([1000 / f(r, "tps") for r in p]) for p in play if p])
        v["ms0"] = mean([1000 / f(r, "tps") for g in ss for r in g if r["phase"] == "P0_fresh_original"])
        for k in ("citizens", "wild", "items"):
            v[k] = mean([mean([f(r, k) for r in p]) for p in play if p])
        v["items_k"] = np.log(v["items"] / 1000) if v["items"] > 0 else float("nan")
        for k in ("hf_alive", "hf", "armies", "events", "entities", "sites", "near_civ", "load_wall_s", "df_footprint_mb", "save_mb"):
            v[k] = mean([f(l, k) for l in ld])
        for k in ("hf_alive", "armies", "events", "entities", "sites"):
            v["log_" + k] = np.log(1 + v[k])
        slopes = []
        for p in play:
            p = sorted(p, key=lambda r: f(r, "ticks_played"))
            if len(p) >= 3:
                slopes.append((np.exp(np.polyfit([f(r, "ticks_played") / 1e5 for r in p], [np.log(f(r, "tps")) for r in p], 1)[0]) - 1) * 100)
        v["slope"] = mean(slopes); v["slopes"] = slopes
        W[key] = v

    print("\n-- per world (play = mean ms/tick over the season's readings, sessions averaged; P0 = fresh at load)")
    print(f"  {'world':<6} {'size':<8} {'dim':>4} {'years':>5} {'lvl':>3} {'water':<6} {'sess':>4} {'t/s play':>8} {'t/s P0':>7} "
          f"{'%/100k':>13} {'hf alive':>8} {'armies':>6} {'events':>7} {'load s':>6} {'MB fp':>6} {'save':>5} {'gen s':>5} {'crash':>5} "
          f"{'cit':>4} {'wild':>4} {'items':>6}")
    order = sorted(W, key=lambda k: (SIZES.index(W[k]["w"]["size_name"]), int(W[k]["w"]["years"]), k))
    for k in order:
        v, w = W[k], W[k]["w"]
        print(f"  {k:<6} {w['size_name']:<8} {w['world_dim']:>4} {w['years']:>5} {w['rule_level']:>3} {w['water']:<6} {v['n_sess']:>4} "
              f"{1000 / v['ms']:>8.0f} {1000 / v['ms0']:>7.0f} {'/'.join(f'{s:+.0f}' for s in v['slopes']) or '-':>13} "
              f"{v['hf_alive']:>8.0f} {v['armies']:>6.0f} {v['events']:>7.0f} {v['load_wall_s']:>6.0f} {v['df_footprint_mb']:>6.0f} "
              f"{v['save_mb']:>5.0f} {f(w, 'gen_wall_s'):>5.0f} {w.get('gen_crashes') or 0:>5} {v['citizens']:>4.0f} {v['wild']:>4.0f} {v['items']:>6.0f}")

    print("\n-- cell means, t/s over the season (worlds in the cell)")
    cells = defaultdict(list)
    for v in W.values():
        cells[(v["w"]["size_name"], int(v["w"]["years"]))].append(1000 / v["ms"])
    yrs = sorted({y for _, y in cells})
    print(f"  {'':<8} " + " ".join(f"{str(y) + ' y':>16}" for y in yrs))
    for s in SIZES:
        if any(k[0] == s for k in cells):
            print(f"  {s:<8} " + " ".join(f"{mean(cells[(s, y)]):>7.0f} {'(' + ', '.join(f'{x:.0f}' for x in cells[(s, y)]) + ')':<8}"
                                          if cells.get((s, y)) else f"{'-':>16}" for y in yrs))

    print("\n== 1. ms/tick on world area and history length (elasticities)")
    for k in W: W[k]["y"] = W[k]["ms"]
    fit("log(ms/tick) = a + b log(area) + c log(1+years)", W, ["area", "hist"], ["b log(area tiles)", "c log(1+years)"])
    fit("the same, fresh at load (P0) instead of the season", {k: dict(v, y=v["ms0"]) for k, v in W.items()}, ["area", "hist"],
        ["b log(area tiles)", "c log(1+years)"])
    fit("the same with the fort's own load (the site differs per world)", W, ["area", "hist", "citizens", "wild", "items_k"],
        ["b log(area tiles)", "c log(1+years)", "per citizen", "per wild unit", "log(items/1000)"])

    print("\n== 2. ms/tick on the world's scale, one count at a time (log(1+count))")
    for k in ("hf_alive", "armies", "events", "entities", "sites"):
        fit(f"log(ms/tick) on log(1+{k})", W, ["log_" + k], [f"log(1+{k})"])
    fit("log(ms/tick) on log(1+hf_alive) and log(area): the figures beyond the map's size", W, ["log_hf_alive", "area"],
        ["log(1+hf_alive)", "log(area tiles)"])

    print("\n== 3. once-per-load costs on the design factors")
    for k, lbl in (("load_wall_s", "load time (s)"), ("df_footprint_mb", "footprint at load (MB)"), ("save_mb", "save size (MB)")):
        fit(f"log({lbl})", {w: dict(v, y=v[k]) for w, v in W.items()}, ["area", "hist"], ["log(area tiles)", "log(1+years)"])
    fit("log(generation time, s)", {w: dict(v, y=f(v["w"], "gen_wall_s")) for w, v in W.items()}, ["area", "hist"],
        ["log(area tiles)", "log(1+years)"])

    print("\n== 4. the season curve: % t/s per 100k ticks, per world, on the design factors (linear, not logged)")
    rs = [(v["slope"], [1, v["area"], v["hist"]]) for v in W.values() if v["slope"] == v["slope"]]
    if len(rs) >= 4:
        ols([x for _, x in rs], [s for s, _ in rs], ["a (% per 100k t)", "per log(area)", "per log(1+years)"])
    else:
        print(f"  skipped: {len(rs)} world(s) with a season curve")
    crashes = sum(int(w.get("gen_crashes") or 0) for w in worlds.values())
    print(f"\n-- generation crashes: {crashes} across {len(worlds)} world(s)"
          + "".join(f"; {k} {w['gen_crashes']}" for k, w in worlds.items() if (w.get("gen_crashes") or "0") != "0"))

if __name__ == "__main__":
    main(sys.argv[1])
