#!/usr/bin/env python3
"""T7b tally: does the frequency-based cavern ceiling bite AND release?
Per arm/rep the cavern-layer trace, how long the hold was on, and — the whole point —
every held->open transition with the cavern count that released it and what arrived after.
A ceiling that only ever engages is a one-way door and fails the gate.
Usage: t7b-tally.py [run_dir]"""
import os
import csv, glob, json, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tallylib import drop_incomplete
from collections import defaultdict
run_dir = sys.argv[1] if len(sys.argv) > 1 else sorted(glob.glob("data/experiments/T7b/*"))[-1]
LINE = re.compile(r"t7b: land=(\d+) water=(\d+) cavern=(\d+) deep=(\d+) citizens=(\d+) held=(\d+) day=(\d+)")
trace = defaultdict(list)
# the per-replicate totals the harness prints when a replicate ends; arrivals is the
# number that shows a brake on arrivals rather than a cull of what is already there.
done = {}
arm = rep = None
for line in open(f"{run_dir}/log.txt"):
    m = re.search(r"== T7b arm=(\S+) rep=(\d+)", line)
    if m:
        arm, rep = m.group(1), int(m.group(2))
    m = re.search(r"done: (\{.*\})", line)
    if m and arm is not None:
        d = json.loads(m.group(1))
        done[(d.get("arm", arm), d.get("rep", rep))] = d
for r in csv.DictReader(open(f"{run_dir}/events.tsv"), delimiter="\t"):
    m = LINE.search(r["detail"])
    if not m:
        continue
    land, water, cav, deep, cz, held, day = (int(x) for x in m.groups())
    trace[(r["arm"], int(r["rep"]))].append((day, cav, held, cz, land))
drop_incomplete(run_dir, trace, done)
print(f"run {run_dir}")
print("arm\trep\tn\tcavern min/mean/max\theld_frac\tbite\trelease\tarrivals\tdeaths\tverdict")
for k in sorted(trace):
    t = trace[k]
    cav = [x[1] for x in t]
    held = [x[2] for x in t]
    bites = releases = 0
    events = []
    for (d0, c0, h0, _, _), (d1, c1, h1, _, _) in zip(t, t[1:]):
        if h0 == 0 and h1 > 0:
            bites += 1; events.append(f"day {d1}: HELD at cavern {c1}")
        if h0 > 0 and h1 == 0:
            releases += 1; events.append(f"day {d1}: released at cavern {c1}")
    # did cavern life come back after a release?
    recovered = None
    for i, ((_, _, h0, _, _), (d1, c1, h1, _, _)) in enumerate(zip(t, t[1:]), start=1):
        if h0 > 0 and h1 == 0:
            after = [x[1] for x in t[i:]]
            if after:
                recovered = max(after) - c1
            break
    hf = sum(1 for h in held if h > 0) / len(held)
    verdict = ("one-way door" if bites and not releases else
               "never engaged" if not bites and not any(held) else
               "bit and released" if bites and releases else "held from the start")
    if verdict == "held from the start" and releases:
        verdict = "bit and released"
    d = done.get(k, {})
    arr = d.get("arrivals", "-"); dth = d.get("deaths", "-")
    print(f"{k[0]}\t{k[1]}\t{len(t)}\t{min(cav)}/{sum(cav)/len(cav):.1f}/{max(cav)}\t{hf:.2f}\t{bites}\t{releases}\t{arr}\t{dth}\t{verdict}")
    for e in events:
        print(f"   {e}")
    if recovered is not None:
        print(f"   cavern regained {recovered} after the first release")
# arm-level comparison: the ceiling arm must run measurably below the control
by_arm = defaultdict(list)
for k, t in trace.items():
    by_arm[k[0]].extend(x[1] for x in t)
arr_by_arm = defaultdict(list)
for (a, r), d in done.items():
    if "arrivals" in d:
        arr_by_arm[a].append(d["arrivals"])
print("\narm\tsamples\tcavern mean\tcavern max\treps\tarrivals (mean)")
for a, cs in sorted(by_arm.items()):
    ar = arr_by_arm.get(a, [])
    am = f"{'+'.join(str(x) for x in ar)} ({sum(ar)/len(ar):.1f})" if ar else "-"
    print(f"{a}\t{len(cs)}\t{sum(cs)/len(cs):.2f}\t{max(cs)}\t{len(ar)}\t{am}")
