#!/usr/bin/env python3
"""ECO2-G tally: groups at once by embark size, default limit vs sqrt(embark)+1.
Per replicate and sample (after the first): wild groups = distinct (species, population ref6) among live, active wild
units, per layer (surface, cavern); wild units per layer. Waves per layer from waves.tsv; t/s from the done: lines.
Usage: eco-g-tally.py <run dir>"""
import csv, json, re, sys, statistics as st
from collections import defaultdict
D = sys.argv[1]
samples = defaultdict(lambda: defaultdict(lambda: {"g": defaultdict(set), "u": defaultdict(int)}))
for r in csv.DictReader(open(f"{D}/units.tsv"), delimiter="\t"):
    if r["wild"] != "1" or r["dead"] != "0" or r["inactive"] != "0": continue
    s = samples[(r["arm"], r["rep"])][int(r["abs_tick"])]
    s["g"][r["layer"]].add((r["species"], r["ref6"])); s["u"][r["layer"]] += 1
waves = defaultdict(lambda: defaultdict(int))
import os
if os.path.exists(f"{D}/waves.tsv"):   # written when the run completes
    for r in csv.DictReader(open(f"{D}/waves.tsv"), delimiter="\t"):
        waves[(r["arm"], r["rep"])][r["layer"]] += 1
tps = {}
for m in re.finditer(r'done: (\{.*\})', open(f"{D}/log.txt").read()):
    j = json.loads(m.group(1)); tps[(j["arm"], str(j["rep"]))] = j.get("ticks_per_s")
rows = []
for key, ss in sorted(samples.items()):
    ticks = sorted(ss)[1:]
    if not ticks: continue
    rec = {"arm": key[0], "rep": key[1]}
    for L in ("surface", "cavern"):
        g = [len(ss[t]["g"][L]) for t in ticks]; u = [ss[t]["u"][L] for t in ticks]
        rec[f"{L}_g_mean"], rec[f"{L}_g_max"], rec[f"{L}_u_mean"] = st.mean(g), max(g), st.mean(u)
        rec[f"{L}_waves"] = waves[key][L]
    rec["tps"] = tps.get(key)
    rows.append(rec)
by = defaultdict(list)
for r in rows: by[r["arm"]].append(r)
def order(a): n = int(a.split("x")[0]); return (n, a.endswith("root1"))
print(f"{'arm':14s} reps | surface groups mean (max) units waves | cavern groups mean (max) units waves | t/s")
out = []
for a in sorted(by, key=order):
    rs = by[a]; m = lambda k: st.mean(x[k] for x in rs if x[k] is not None)
    line = {"arm": a, "reps": len(rs), **{k: m(k) for k in rs[0] if k not in ("arm", "rep")}}
    out.append(line)
    print(f"{a:14s} {len(rs):4d} | {line['surface_g_mean']:5.2f} ({max(x['surface_g_max'] for x in rs)}) {line['surface_u_mean']:6.1f} {line['surface_waves']:5.1f}"
          f" | {line['cavern_g_mean']:5.2f} ({max(x['cavern_g_max'] for x in rs)}) {line['cavern_u_mean']:6.1f} {line['cavern_waves']:5.1f} | {line['tps'] or 0:6.0f}")
json.dump({"per_rep": rows, "per_arm": out}, open(f"{D}/g-tally.json", "w"), indent=1)
