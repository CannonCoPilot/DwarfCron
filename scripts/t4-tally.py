#!/usr/bin/env python3
"""T4 gate tally: wild prey deaths per arm/rep from events.tsv, plus the tool's ecology status lines.

PASS = prey deaths (any species except the predators) > 0 in every ecology_on rep and 0 in every ecology_off rep.
Usage: t4-tally.py [run_dir]   (default: newest data/experiments/T4/*)
"""
import csv, glob, os, re, sys
from collections import defaultdict

PREDATORS = {"COUGAR", "DINGO", "WOLF"}   # LARGE_PREDATOR castes; a badger is a target since 67a7487
run_dir = sys.argv[1] if len(sys.argv) > 1 else sorted(glob.glob("data/experiments/T4/*"))[-1]
deaths = defaultdict(lambda: defaultdict(int))     # (arm,rep) -> species -> n
status = defaultdict(list)                         # (arm,rep) -> [ecology status strings]
keys = []
with open(os.path.join(run_dir, "events.tsv")) as f:
    for r in csv.DictReader(f, delimiter="\t"):
        k = (r["arm"], int(r["rep"]))
        if k not in keys: keys.append(k)
        if r["event"] == "death":
            deaths[k][r["detail"].split()[0]] += 1
        elif r["subject"].startswith("local ok,out=pcall(dfhack.run_command_silent") and "ecology:" in r["detail"]:
            m = re.search(r"ecology: (\w+)\s+last write day (\d+): (\d+) predator\(s\) x (\d+) target\(s\), (\d+) pair\(s\) written, (\d+) without a slot, (\d+) nudged, (\d+) slot\(s\) cleared; total writes (\d+), nudges (\d+)", r["detail"])
            if m: status[k].append(m.groups())

print(f"run {run_dir}")
print("arm\trep\tprey_deaths\tpred_deaths\tby_species\tlast_ecology_status")
ok = True; seen = defaultdict(int)
for k in keys:
    d = deaths[k]
    prey = sum(n for s, n in d.items() if s not in PREDATORS)
    pred = sum(n for s, n in d.items() if s in PREDATORS)
    st = status[k][-1] if status[k] else None
    stx = (f"eco={st[0]} preds={st[2]} targets={st[3]} pairs={st[4]} slotless={st[5]} nudged={st[6]} cleared={st[7]} writes={st[8]} nudges_total={st[9]}") if st else "-"
    print(f"{k[0]}\t{k[1]}\t{prey}\t{pred}\t{dict(sorted(d.items()))}\t{stx}")
    seen[k[0]] += 1
    if k[0].endswith("on") and prey == 0: ok = False
    if k[0].endswith("off") and prey > 0: ok = False
print(f"reps seen: {dict(seen)}")
complete = len(seen) == 2 and all(v >= 3 for v in seen.values())
print("VERDICT:", "INCOMPLETE" if not complete else ("PASS" if ok else "FAIL"))
