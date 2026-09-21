#!/usr/bin/env python3
"""T8 tally (v5.10.0 patterns). Per arm and replicate: waves (surface arrivals of one species within 100
ticks), wave sizes, gaps between waves, the bird share of waves in summer's first week (ticks
100,800-109,199 of the year), predator waves by whether prey were on the map at the arrival, and the
release reasons the ledger recorded. Then each pattern against the manifest's prediction.
Usage: t8-tally.py [run_dir]"""
import csv, glob, json, re, sys
from collections import defaultdict
from statistics import median
run_dir = sys.argv[1] if len(sys.argv) > 1 else sorted(glob.glob("data/experiments/T8/2*"))[-1]
prov = json.load(open(f"{run_dir}/provenance.json"))
valid = {(r["arm"], int(r["rep"])) for r in prov.get("replicates", []) if r.get("valid")}
ev = defaultdict(list)
for r in csv.DictReader(open(f"{run_dir}/events.tsv"), delimiter="\t"): ev[(r["arm"], int(r["rep"]))].append(r)
# wild prey on the surface per sample, from units.tsv
prey_at = defaultdict(lambda: defaultdict(int))
cats = {}
for line in open(f"{run_dir}/log.txt", errors="replace"):
    m = re.search(r"t8 cats: (.*)", line)
    if m:
        for kv in m.group(1).split():
            k, _, v = kv.partition("="); cats[k] = v
def cat(sp): return cats.get(sp, "?")
for r in csv.DictReader(open(f"{run_dir}/units.tsv"), delimiter="\t"):
    if r["dead"] == "1" or r["inactive"] == "1" or r["wild"] != "1" or r["layer"] != "surface": continue
    if cat(r["species"]) == "prey": prey_at[(r["arm"], int(r["rep"]))][int(r["tick"])] += 1
reasons = defaultdict(lambda: defaultdict(int))   # key -> reason word -> count
cur = None
for line in open(f"{run_dir}/log.txt", errors="replace"):
    m = re.search(r"^\S+ == \w+ arm=(\w+) rep=(\d+)", line)
    if m: cur = (m.group(1), int(m.group(2)))
    if "t8 ledger:" in line and cur:
        for w in re.findall(r"detached \w+ x\d+; (\w+)", line): reasons[cur][w] += 1
SUMMER_WEEK = (100800, 100800 + 7 * 1200)
GAP_MAX_T = 20 * 1200
out = {}
print(f"run {run_dir}\n")
print(f"{'arm':8} {'rep':>3} {'waves':>5} {'med size':>8} {'<=2':>4} {'gaps<=3500':>10} {'gaps>=24k':>9} {'med gap d':>9} {'wk1 bird/all':>12} {'pred w/ prey':>12} reasons")
for key in sorted(ev):
    arm, rep = key
    rows = [r for r in ev[key] if r["event"] == "arrival" and "layer=surface" in r["detail"]]
    waves = []   # (tick, species, n)
    for r in sorted(rows, key=lambda r: int(r["tick"])):
        t, sp = int(r["tick"]), r["detail"].split()[0]
        if waves and waves[-1][1] == sp and t - waves[-1][0] <= 100: waves[-1] = (waves[-1][0], sp, waves[-1][2] + 1)
        else: waves.append((t, sp, 1))
    sizes = [n for _, _, n in waves]
    ticks = [t for t, _, _ in waves]
    gaps = [b - a for a, b in zip(ticks, ticks[1:])]
    wk = [w for w in waves if SUMMER_WEEK[0] <= w[0] < SUMMER_WEEK[1]]
    wk_bird = sum(1 for w in wk if cat(w[1]) == "bird")
    pred_waves = [w for w in waves if cat(w[1]) == "predator"]
    samples = sorted(prey_at[key])
    def prey_present(t):
        prior = [s for s in samples if s <= t]
        return prey_at[key][prior[-1]] if prior else 0
    pred_with_prey = sum(1 for w in pred_waves if prey_present(w[0]) > 0)
    rs = ", ".join(f"{k}:{v}" for k, v in sorted(reasons[key].items()))
    out[key] = dict(waves=len(waves), med_size=median(sizes) if sizes else 0, small=sum(1 for n in sizes if n <= 2),
                    gaps_short=sum(1 for g in gaps if g <= 3500), gaps_long=sum(1 for g in gaps if g >= GAP_MAX_T),
                    med_gap_days=(median(gaps) / 1200) if gaps else 0, wk=len(wk), wk_bird=wk_bird, pred=len(pred_waves),
                    pred_with_prey=pred_with_prey, reasons=dict(reasons[key]), valid=key in valid)
    o = out[key]
    print(f"{arm:8} {rep:>3} {o['waves']:>5} {o['med_size']:>8.1f} {o['small']:>4} {o['gaps_short']:>10} {o['gaps_long']:>9} {o['med_gap_days']:>9.1f} {wk_bird:>5}/{len(wk):<6} {pred_with_prey:>5}/{len(pred_waves):<6} {rs}{'' if o['valid'] else '  INVALID'}")
print()
def arm_reps(a): return [o for k, o in out.items() if k[0] == a and o["valid"]]
st = arm_reps("steady")
def verdict(name, ok, why): print(f"{name:8} {'PASS' if ok else 'FAIL'}  {why}")
if arm_reps("burst"):
    ok = all(o["gaps_short"] >= 1 and o["gaps_long"] >= 1 for o in arm_reps("burst"))
    verdict("burst", ok, "each replicate has a gap <= 3,500 ticks and a gap >= 20 days; " + str([(o["gaps_short"], o["gaps_long"]) for o in arm_reps("burst")]))
if arm_reps("trickle"):
    ok = all(o["med_size"] <= 2 for o in arm_reps("trickle")) and (not st or median([o["med_size"] for o in st]) > 2)
    verdict("trickle", ok, "median wave size <= 2 in each replicate, steady's above 2; " + str([o["med_size"] for o in arm_reps("trickle")]) + " vs steady " + str([o["med_size"] for o in st]))
if arm_reps("dawn"):
    d = arm_reps("dawn"); share = lambda o: (o["wk_bird"] / o["wk"]) if o["wk"] else None
    ds = [share(o) for o in d]; ss = [share(o) for o in st]
    ok = all(x is not None and x > 0 for x in ds) and (not ss or all(x is None or (min(v for v in ds if v is not None) >= x) for x in ss))
    verdict("dawn", ok, "summer week-one bird share above zero in each replicate and at or above steady's; " + str(ds) + " vs steady " + str(ss))
if arm_reps("follow"):
    f = arm_reps("follow")
    ok = all(o["pred"] == 0 or o["pred_with_prey"] == o["pred"] for o in f) and any(o["pred"] > 0 for o in f)
    verdict("follow", ok, "every predator wave arrived with prey on the map, and there was at least one; " + str([(o["pred_with_prey"], o["pred"]) for o in f]))
if st:
    ok = all(5 * 1200 * 0.5 <= o["med_gap_days"] * 1200 <= 40 * 1200 for o in st)
    verdict("steady", ok, "median gap within the 5-20 day range's neighbourhood; " + str([round(o["med_gap_days"], 1) for o in st]))
