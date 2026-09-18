#!/usr/bin/env python3
"""E18 tally: nudge threshold vs kill latency.
Per arm/rep: tick of the first armed-predator arrival (cougar/dingo/wolf), tick of the first armed kill
(a non-predator's death whose own combat reports name a cougar/dingo/wolf as the attacker), the latency
between them, total nudges from the last ecology status line, and the nudge threshold in force.
Usage: e18-tally.py [run_dir]   (default: newest data/experiments/E18/*)
"""
import csv, glob, os, re, sys
from collections import Counter, defaultdict
ARMED = ("cougar", "dingo", "wolf"); PRED = {"COUGAR", "DINGO", "WOLF"}
run_dir = sys.argv[1] if len(sys.argv) > 1 else sorted(glob.glob("data/experiments/E18/*"))[-1]
VERB = r"(attacks|bites|scratches|charges at|kicks|strikes|punches|bashes|pushes|shoots|stabs|slashes|gores|collides with)"
subj = re.compile(r"^The ([a-z][a-z ]*?) " + VERB + r" the ")
combat = defaultdict(list)
with open(os.path.join(run_dir, "combat.tsv")) as f:
    for r in csv.DictReader(f, delimiter="\t"): combat[(r["arm"], int(r["rep"]), r["unit"])].append(r["text"])
first_arr, first_kill, nudges, keys, seen = {}, {}, {}, [], set()
with open(os.path.join(run_dir, "events.tsv")) as f:
    for r in csv.DictReader(f, delimiter="\t"):
        k = (r["arm"], int(r["rep"])); t = int(r["tick"])
        if k not in keys: keys.append(k)
        if r["event"] == "arrival" and r["detail"].split()[0] in PRED: first_arr.setdefault(k, t)
        elif r["event"] == "death":
            sp = r["detail"].split()[0]
            if sp in PRED or (k, r["subject"]) in seen: continue
            seen.add((k, r["subject"]))
            c = Counter(m.group(1) for txt in combat.get((k[0], k[1], r["subject"]), []) for m in [subj.match(txt)] if m)
            killer = c.most_common(1)[0][0] if c else "-"
            if any(a in killer for a in ARMED) and k not in first_kill: first_kill[k] = (t, sp, killer)
        elif "ecology:" in r["detail"]:
            m = re.search(r"nudges (\d+)", r["detail"])
            if m: nudges[k] = int(m.group(1))
print(f"run {run_dir}")
print("arm\trep\tfirst_armed_arrival\tfirst_armed_kill\tlatency_ticks\tvictim<-killer\tnudges_total")
for k in keys:
    a = first_arr.get(k); kl = first_kill.get(k)
    lat = (kl[0] - a) if (a is not None and kl) else "-"
    print(f"{k[0]}\t{k[1]}\t{a if a is not None else '-'}\t{kl[0] if kl else '-'}\t{lat}\t{(kl[1]+'<-'+kl[2]) if kl else '-'}\t{nudges.get(k,'-')}")
