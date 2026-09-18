#!/usr/bin/env python3
"""E28 tally: pack cohesion per arm and replicate from units.tsv.

For every sample, the wild dingoes on the map give a centroid and a mean Chebyshev distance to it.
Reported per arm/rep: samples with a pack (>= 4 dingoes), mean of the per-sample mean distance, its max,
the share of samples under 8 tiles, and stuck units (same tile for >= 5 consecutive samples, 5,000 ticks).
Usage: e28-tally.py [run_dir]   (default: newest data/experiments/E28/*)
"""
import csv, glob, sys
from collections import defaultdict
run_dir = sys.argv[1] if len(sys.argv) > 1 else sorted(glob.glob("data/experiments/E28/*"))[-1]
pos = defaultdict(lambda: defaultdict(dict))   # (arm,rep) -> tick -> id -> (x,y,z)
with open(f"{run_dir}/units.tsv") as f:
    for r in csv.DictReader(f, delimiter="\t"):
        if r["species"] != "DINGO" or r["wild"] != "1" or r["dead"] == "1" or r["inactive"] == "1": continue
        pos[(r["arm"], int(r["rep"]))][int(r["tick"])][r["id"]] = (int(r["x"]), int(r["y"]), int(r["z"]))
print(f"run {run_dir}")
print("arm\trep\tpack_samples\tmean_dist\tmax_dist\tshare_under_8\tstuck_units\tpack_size_range")
summary = defaultdict(list)
for key in sorted(pos, key=lambda k: (["control","station","leader","nudge"].index(k[0]) if k[0] in ["control","station","leader","nudge"] else 9, k[1])):
    ticks = sorted(pos[key]); dists = []; sizes = []
    for t in ticks:
        units = pos[key][t]
        if len(units) < 4: continue
        cx = sum(p[0] for p in units.values()) / len(units); cy = sum(p[1] for p in units.values()) / len(units)
        d = sum(max(abs(p[0]-cx), abs(p[1]-cy)) for p in units.values()) / len(units)
        dists.append(d); sizes.append(len(units))
    # stuck: same tile for 5 consecutive samples
    stuck = set(); run = defaultdict(lambda: (None, 0))
    for t in ticks:
        for uid, p in pos[key][t].items():
            last, n = run[uid]
            run[uid] = (p, n + 1 if p == last else 1)
            if run[uid][1] >= 5: stuck.add(uid)
    if dists:
        mean = sum(dists)/len(dists); mx = max(dists); under = sum(1 for d in dists if d < 8)/len(dists)
        print(f"{key[0]}\t{key[1]}\t{len(dists)}\t{mean:.2f}\t{mx:.1f}\t{under:.0%}\t{len(stuck)}\t{min(sizes)}-{max(sizes)}")
        summary[key[0]].append(mean)
    else:
        print(f"{key[0]}\t{key[1]}\t0\t-\t-\t-\t-\tno pack of 4+ seen")
print("arm means:", {a: round(sum(v)/len(v), 2) for a, v in summary.items()})
