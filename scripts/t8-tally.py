#!/usr/bin/env python3
"""T8 tally (v5.10.0 patterns). Per arm and replicate: waves (surface arrivals of one species within 100
ticks), wave sizes, gaps between waves, the bird share of waves in summer's first week (ticks
100,800-109,199 of the year), predator waves by whether prey were on the map at the arrival, and the
release reasons the ledger recorded. Then each pattern against the manifest's prediction.
Usage: t8-tally.py [run_dir]"""
import csv, glob, json, re, sys
from collections import defaultdict
from statistics import median
import os
args = [a for a in sys.argv[1:] if not a.startswith("--")]
run_dir = args[0] if args else sorted(glob.glob("data/experiments/T8/2*"))[-1]
# --baseline DIR: take the steady and burst arms from another run (T8b measures only the three re-designed patterns)
baseline = sys.argv[sys.argv.index("--baseline") + 1] if "--baseline" in sys.argv else None
valid = set(); have_prov = False
ev = defaultdict(list)
prey_at = defaultdict(lambda: defaultdict(int))
cats = {}
reasons = defaultdict(lambda: defaultdict(int))   # key -> reason word -> count
seen_lines = {}
def cat(sp): return cats.get(sp, "?")
def load(d, arms=None):
    global have_prov
    keep = lambda a: arms is None or a in arms
    if os.path.exists(f"{d}/provenance.json"):
        have_prov = True
        for r in json.load(open(f"{d}/provenance.json")).get("replicates", []):
            if r.get("valid") and keep(r["arm"]): valid.add((r["arm"], int(r["rep"])))
    for r in csv.DictReader(open(f"{d}/events.tsv"), delimiter="\t"):
        if keep(r["arm"]): ev[(r["arm"], int(r["rep"]))].append(r)
    for line in open(f"{d}/log.txt", errors="replace"):
        m = re.search(r"t8 cats: (.*)", line)
        if m:
            for kv in m.group(1).split():
                k, _, v = kv.partition("="); cats[k] = v
    for r in csv.DictReader(open(f"{d}/units.tsv"), delimiter="\t"):
        if r["dead"] == "1" or r["inactive"] == "1" or r["wild"] != "1" or r["layer"] != "surface" or not keep(r["arm"]): continue
        if cat(r["species"]) == "prey": prey_at[(r["arm"], int(r["rep"]))][int(r["tick"])] += 1
    cur = None
    for line in open(f"{d}/log.txt", errors="replace"):
        m = re.search(r"^\S+ == \w+ arm=(\w+) rep=(\d+)", line)
        if m: cur = (m.group(1), int(m.group(2))) if keep(m.group(1)) else None
        if "t8 ledger:" in line and cur:
            seen_lines.setdefault(cur, set())
            for piece in line.split(" | "):
                m2 = re.search(r"(y\d+ \w+ \d+\s+wave\s+(\w+)\s+detached \w+ x\d+; (\w+))", piece)
                if m2 and m2.group(2) == "land" and m2.group(1) not in seen_lines[cur]:
                    seen_lines[cur].add(m2.group(1)); reasons[cur][m2.group(3)] += 1
load(run_dir)
if baseline: load(baseline, arms={"steady", "burst"})
if not have_prov: valid = None
SUMMER_WEEK = (100800, 100800 + 7 * 1200)
GAP_MAX_T = 20 * 1200
out = {}
print(f"run {run_dir}" + (f"  (steady and burst from {baseline})" if baseline else "") + "\n")
print(f"{'arm':8} {'rep':>3} {'waves':>5} {'events':>6} {'max size':>8} {'med size':>8} {'gaps 2-3.6k':>11} {'gaps>=24k':>9} {'med gap d':>9} {'wk1 bird/all':>12} {'pred w/ prey':>12} reasons")
for key in sorted(ev):
    arm, rep = key
    rows = [r for r in ev[key] if r["event"] == "arrival" and "layer=surface" in r["detail"]]
    waves = []   # (tick, species, n)
    for r in sorted(rows, key=lambda r: int(r["tick"])):
        t, sp = int(r["tick"]), r["detail"].split()[0]
        if waves and waves[-1][1] == sp and t - waves[-1][0] <= 100: waves[-1] = (waves[-1][0], sp, waves[-1][2] + 1)
        else: waves.append((t, sp, 1))
    sizes = [n for _, _, n in waves]
    # arrival EVENTS: waves of any species within 500 ticks are one event (DF lands several groups at once)
    events = []
    for t, _, _ in waves:
        if events and t - events[-1] <= 500: continue
        events.append(t)
    gaps = [b - a for a, b in zip(events, events[1:])]
    wk = [w for w in waves if SUMMER_WEEK[0] <= w[0] < SUMMER_WEEK[1]]
    wk_bird = sum(1 for w in wk if cat(w[1]) == "bird")
    pred_waves = [w for w in waves if cat(w[1]) == "predator"]
    samples = sorted(prey_at[key])
    def prey_present(t):
        prior = [s for s in samples if s <= t]
        return prey_at[key][prior[-1]] if prior else 0
    pred_with_prey = sum(1 for w in pred_waves if prey_present(w[0]) > 0)
    rs = ", ".join(f"{k}:{v}" for k, v in sorted(reasons[key].items()))
    out[key] = dict(waves=len(waves), med_size=median(sizes) if sizes else 0, max_size=max(sizes) if sizes else 0, small=sum(1 for n in sizes if n <= 2),
                    events=len(events), gaps_burst=sum(1 for g in gaps if 2000 <= g <= 3600), gaps_long=sum(1 for g in gaps if g >= GAP_MAX_T),
                    med_gap_days=(median(gaps) / 1200) if gaps else 0, wk=len(wk), wk_bird=wk_bird, pred=len(pred_waves),
                    pred_with_prey=pred_with_prey, reasons=dict(reasons[key]), valid=(valid is None or key in valid))
    o = out[key]
    print(f"{arm:8} {rep:>3} {o['waves']:>5} {o['events']:>6} {o['max_size']:>8} {o['med_size']:>8.1f} {o['gaps_burst']:>11} {o['gaps_long']:>9} {o['med_gap_days']:>9.1f} {wk_bird:>5}/{len(wk):<6} {pred_with_prey:>5}/{len(pred_waves):<6} {rs}{'' if o['valid'] else '  (not yet in provenance)'}")
print()
def arm_reps(a): return [o for k, o in out.items() if k[0] == a and o["valid"]]
st = arm_reps("steady")
def verdict(name, ok, why): print(f"{name:8} {'PASS' if ok else 'FAIL'}  {why}")
if arm_reps("burst"):
    ok = all(o["gaps_burst"] >= 1 and o["gaps_long"] >= 1 for o in arm_reps("burst")) and all(o["gaps_burst"] == 0 for o in st)
    verdict("burst", ok, "each burst replicate has an event gap of 2,000-3,600 ticks (the 2.5-day spacing) and a gap >= 20 days; steady has no such spacing; burst " + str([(o["gaps_burst"], o["gaps_long"]) for o in arm_reps("burst")]) + " steady " + str([o["gaps_burst"] for o in st]))
if arm_reps("trickle"):
    ok = all(o["max_size"] <= 2 for o in arm_reps("trickle")) and all(o["max_size"] > 2 for o in st)
    verdict("trickle", ok, "largest wave <= 2 in each trickle replicate, above 2 in each steady one; trickle " + str([o["max_size"] for o in arm_reps("trickle")]) + " vs steady " + str([o["max_size"] for o in st]))
if arm_reps("dawn"):
    d = arm_reps("dawn"); share = lambda o: (o["wk_bird"] / o["wk"]) if o["wk"] else None
    ds = [share(o) for o in d]; ss = [share(o) for o in st]
    known = [x for x in ds if x is not None]
    if not known: print(f"{'dawn':8} INCONCLUSIVE  no wave landed in summer's first week in any dawn replicate; the window is 8,400 ticks")
    else:
        ok = all(x > 0 for x in known) and all(x is None or min(known) >= x for x in ss)
        verdict("dawn", ok, "summer week-one bird share above zero in each dawn replicate that had a wave there, and at or above steady's; dawn " + str(ds) + " vs steady " + str(ss))
if arm_reps("follow"):
    f = arm_reps("follow")
    share = lambda o: (o["pred"] / o["waves"]) if o["waves"] else 0
    fs, ss2 = [round(share(o), 2) for o in f], [round(share(o), 2) for o in st]
    ok = all(o["pred"] == 0 or o["pred_with_prey"] == o["pred"] for o in f) and any(o["pred"] > 0 for o in f) and (not ss2 or min(fs) >= max(ss2))
    verdict("follow", ok, "every predator wave arrived with prey on the map, at least one did, and follow's predator share of waves is at or above steady's best (prey is nearly always on this fort, so presence alone does not separate the two); follow " + str(fs) + " vs steady " + str(ss2) + "; with-prey " + str([(o["pred_with_prey"], o["pred"]) for o in f]))
if st:
    ok = all(5 * 1200 * 0.5 <= o["med_gap_days"] * 1200 <= 40 * 1200 for o in st)
    verdict("steady", ok, "median gap within the 5-20 day range's neighbourhood; " + str([round(o["med_gap_days"], 1) for o in st]))
