#!/usr/bin/env python3
"""E24 tally: is the abundance slider a volume control or only an eligibility gate?
in_season_qty 200 against 20 — a tenfold difference written into every managed land entry,
same species, same season. The discriminator is SURFACE arrivals, so arrivals are counted from
the events, not from the harness's total (which includes cavern waves the tool is not managing
in this design). Also reports the pool quantity the manipulation actually wrote, because an arm
that did not move the entries is vacuous rather than negative.
Usage: e24-tally.py [run_dir]"""
import os
import csv, glob, json, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tallylib import drop_incomplete
from collections import defaultdict
run_dir = sys.argv[1] if len(sys.argv) > 1 else sorted(glob.glob("data/experiments/E24/*"))[-1]
SAMPLE = re.compile(r"e24: land=(\d+) water=(\d+) cavern=(\d+) deep=(\d+) citizens=(\d+) land_pool_qty=(\d+) day=(\d+)")
SETUP = re.compile(r"e24: in_season_qty=(\d+) . (\d+) allowed, (\d+) assigned, (\d+) entries activated")

waves = defaultdict(lambda: defaultdict(int))      # key -> abs_tick -> n surface arrivals
arrivals = defaultdict(lambda: defaultdict(int))   # key -> layer -> n
species = defaultdict(lambda: defaultdict(int))    # key -> species -> n (surface only)
present = defaultdict(list)
poolq = defaultdict(list)
setup = {}
for r in csv.DictReader(open(f"{run_dir}/events.tsv"), delimiter="\t"):
    k = (r["arm"], int(r["rep"]))
    if r["event"] == "arrival":
        m = re.search(r"layer=(\w+)", r["detail"])
        layer = m.group(1) if m else "?"
        arrivals[k][layer] += 1
        if layer == "surface":
            species[k][r["detail"].split()[0]] += 1
            waves[k][int(r["abs_tick"])] += 1
    elif r["event"] == "manipulation":
        m = SAMPLE.search(r["detail"])
        if m:
            present[k].append(int(m.group(1))); poolq[k].append(int(m.group(6)))
        m = SETUP.search(r["detail"])
        if m:
            setup[k] = (int(m.group(1)), int(m.group(3)), int(m.group(4)))

drop_incomplete(run_dir, arrivals, species, present, poolq, setup, waves)
print(f"run {run_dir}")
print("arm\trep\tqty\topened\tland present mean\tpool qty\tsurf arr\tWAVES\tMEAN WAVE SIZE\tmax wave")
for k in sorted(arrivals):
    p = present.get(k) or [0]
    q = poolq.get(k) or [0]
    s = setup.get(k, ("-", "-", "-"))
    w = list(waves[k].values())
    mw = (sum(w) / len(w)) if w else 0.0
    print(f"{k[0]}\t{k[1]}\t{s[0]}\t{s[2]}\t{sum(p)/len(p):.1f}"
          f"\t{q[0]}->{q[-1]}\t{arrivals[k]['surface']}\t{len(w)}\t{mw:.2f}\t{max(w) if w else 0}")

print("\narm\treps\tSURFACE arrivals\tmean\tland present (mean)\ttop surface species")
by_arm = defaultdict(list); pres_arm = defaultdict(list); sp_arm = defaultdict(lambda: defaultdict(int))
for k in arrivals:
    by_arm[k[0]].append(arrivals[k]["surface"])
    pres_arm[k[0]].extend(present.get(k, []))
    for sp, n in species[k].items():
        sp_arm[k[0]][sp] += n
for a in sorted(by_arm):
    v = by_arm[a]; pr = pres_arm[a] or [0]
    top = sorted(sp_arm[a].items(), key=lambda x: -x[1])[:5]
    print(f"{a}\t{len(v)}\t{'+'.join(map(str, v))}\t{sum(v)/len(v):.1f}\t{sum(pr)/len(pr):.1f}"
          f"\t{', '.join(f'{s} x{n}' for s, n in top)}")
# the measure that is not bounded by the tool's scheduler
wv_arm = defaultdict(list)
for k, d in waves.items():
    wv_arm[k[0]].extend(d.values())
print("\narm\twaves\tmean wave size\tmax\twave-size distribution")
for a in sorted(wv_arm):
    w = wv_arm[a]
    dist = ", ".join(f"{n}x{w.count(n)}" for n in sorted(set(w)))
    print(f"{a}\t{len(w)}\t{sum(w)/len(w):.2f}\t{max(w)}\t{dist}")
if len(wv_arm) == 2:
    (a1, w1), (a2, w2) = sorted(wv_arm.items())
    m1, m2 = sum(w1)/len(w1), sum(w2)/len(w2)
    hi, lo = (m1, m2) if m1 >= m2 else (m2, m1)
    print(f"\nWAVE SIZE {a1} {m1:.2f} vs {a2} {m2:.2f} -> ratio {hi/lo if lo else float('inf'):.2f}"
          f" against a 10x difference in entry quantity")
    print("this is the discriminator: the scheduler caps wave COUNT in both arms, but DF sizes each wave")

arms = sorted(by_arm)
if len(arms) == 2:
    hi, lo = arms if sum(by_arm[arms[0]]) >= sum(by_arm[arms[1]]) else arms[::-1]
    a, b = sum(by_arm[hi]) / len(by_arm[hi]), sum(by_arm[lo]) / len(by_arm[lo])
    ratio = (a / b) if b else float("inf")
    print(f"\n{hi} / {lo} surface-arrival ratio = {ratio:.2f} against a 10x difference in entry quantity")
    print("a ratio near 10 makes abundance a VOLUME control; near 1 makes it an ELIGIBILITY gate only")
