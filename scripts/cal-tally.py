#!/usr/bin/env python3
"""ECO CAL tally: kill rates over 30,000 ticks by predator, group size and prey.
Reads <run>/CAL.tsv (eco-run output). Counts only kills whose killer and victim were both placed by the cell.
Per cell (mean of reps): prey killed of 6, predators lost, first-kill tick, kills per 10,000 ticks, and the
prey-to-hunter mass ratio. Usage: cal-tally.py <run dir> [--json out.json]"""
import json, re, sys, statistics as st
from collections import defaultdict
D = sys.argv[1]
MASS = {"WOLF": 40000, "HYENA": 60000, "COUGAR": 60000, "LION": 200000, "TIGER": 225000, "DEER": 140000, "ELK": 300000,
        "MOOSE": 525000, "WATER_BUFFALO": 1000000, "ELEPHANT": 5000000, "GIRAFFE": 1000000}
def kv(s): return dict(re.findall(r"(\w+)=(\S+)", s))
cells = defaultdict(lambda: defaultdict(lambda: {"kills": [], "lost": 0, "ticks": 30000}))
for line in open(f"{D}/CAL.tsv"):
    p = line.rstrip("\n").split("\t")
    if len(p) < 5: continue
    _, cell, rep, kind, rest = p[:5]
    c = cells[cell][rep]
    if kind == "death":
        d = kv(rest)
        if d.get("victim_spawned") == "1" and d.get("killer_spawned") == "1":
            pred = cell.split("_")[0].rstrip("0123456789").upper()
            if d.get("killer") == pred: c["kills"].append(int(d.get("dt", -1)))
            else: c["lost"] += 1
    elif kind == "alerts":
        c["ticks"] = int(kv(rest).get("ticks", 30000)) or 30000
out = []
print(f"{'cell':26s} reps  ratio  n | killed/6  lost  first-kill(t)  kills/10k t")
for cell, reps in cells.items():
    m = re.match(r"([a-z]+)(\d+)_(.+)", cell); pred, n, prey = m.group(1).upper(), int(m.group(2)), m.group(3)
    ratio = MASS[prey] / MASS[pred]
    k = [len(r["kills"]) for r in reps.values()]; lost = [r["lost"] for r in reps.values()]
    firsts = [min(r["kills"]) for r in reps.values() if r["kills"]]
    rate = [10000 * len(r["kills"]) / r["ticks"] for r in reps.values()]
    rec = {"cell": cell, "pred": pred, "n": n, "prey": prey, "ratio": round(ratio, 2), "reps": len(reps), "killed": k, "lost": lost,
           "first": firsts, "rate10k": round(st.mean(rate), 2)}
    out.append(rec)
    print(f"{cell:26s} {len(reps):4d} {ratio:6.1f} {n:2d} | {'/'.join(map(str, k)):8s} {'/'.join(map(str, lost)):5s} "
          f"{('/'.join(str(f) for f in firsts) or '-'):14s} {rec['rate10k']:.2f}")
if "--json" in sys.argv: json.dump(out, open(sys.argv[sys.argv.index("--json") + 1], "w"), indent=1)
