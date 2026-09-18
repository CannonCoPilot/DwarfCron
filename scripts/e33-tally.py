#!/usr/bin/env python3
"""E33 tally: does a placement cadence hold the water layer?
Per arm/rep: the feature-layer wild count at each sample (min, mean, max, and the share of samples at or
above the target), how many animals were placed in total, the species mix at the end, citizen count, and
the pool debit for water entries across the run.
Usage: e33-tally.py [run_dir]"""
import csv, glob, re, sys
from collections import defaultdict
run_dir = sys.argv[1] if len(sys.argv) > 1 else sorted(glob.glob("data/experiments/E33/*"))[-1]
LINE = re.compile(r"e33 water: (\d+) on map \[([^\]]*)\] target (\S+) -> placed (\d+) \[([^\]]*)\](?: — ([^;]*?))? season (\d+) day (\d+)")
counts = defaultdict(list); post = defaultdict(list); placed = defaultdict(int); whys = defaultdict(set); last_mix = {}
for r in csv.DictReader(open(f"{run_dir}/events.tsv"), delimiter="\t"):
    m = LINE.search(r["detail"])
    if not m: continue
    k = (r["arm"], int(r["rep"]))
    counts[k].append(int(m.group(1))); post[k].append(int(m.group(1)) + int(m.group(4)))
    placed[k] += int(m.group(4)); last_mix[k] = m.group(2)
    if m.group(6): whys[k].add(m.group(6).strip())
# pool debit for water entries
debit = defaultdict(dict)
try:
    for r in csv.DictReader(open(f"{run_dir}/pops_all.tsv"), delimiter="\t"):
        if r["layer"] != "water": continue
        k = (r["arm"], int(r["rep"]))
        d = debit[k].setdefault(r["species"], [None, None])
        if r["phase"] == "start": d[0] = int(r["quantity"])
        else: d[1] = int(r["quantity"])
except (FileNotFoundError, KeyError): pass
print(f"run {run_dir}")
print("arm\trep\tsamples\tpre:min/mean/max\tpost:min/mean\tnever_empty\tplaced\tfinal mix")
for k in sorted(counts, key=lambda x: (x[0] != "placed", x[0], x[1])):
    c = counts[k]; q = post[k]
    print(f"{k[0]}\t{k[1]}\t{len(c)}\t{min(c)}/{sum(c)/len(c):.1f}/{max(c)}\t{min(q)}/{sum(q)/len(q):.1f}\t{min(c) > 0}\t{placed[k]}\t{last_mix[k][:60]}")
    if whys[k]: print(f"   placement was refused: {sorted(whys[k])}")
    if debit.get(k):
        moved = {s: (a, b) for s, (a, b) in debit[k].items() if a is not None and b is not None and a != b}
        if moved: print(f"   water entries that moved: {dict(sorted(moved.items()))}")
