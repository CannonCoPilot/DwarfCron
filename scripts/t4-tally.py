#!/usr/bin/env python3
"""T4 gate tally: who killed what, per arm and rep.

A kill is attributed from the victim's own combat reports (combat.tsv rows carry the unit the
report belongs to): the most frequent attacking subject is the killer. Classes: armed = a
LARGE_PREDATOR caste (cougar, dingo, wolf); fort = the fort's dogs/dwarves; wild = any other
wild attacker (owl, raven, badger rage...); cavern = the victim lived in a cavern or water
layer (ref6 feature/cave index >= 0); none = no attack report at all (fall, drowning...).
PASS = at least one armed kill of a surface non-predator in every ecology_on rep; the
ecology_off reps are reported as the chance rate (T4 first run: one unwritten cougar killed
four badgers in one off rep, so zero is not the bar).
Usage: t4-tally.py [run_dir]   (default: newest data/experiments/T4/*)
"""
import csv, glob, os, re, sys
from collections import Counter, defaultdict

ARMED = {"cougar", "dingo", "wolf"}
PRED_TOKENS = {"COUGAR", "DINGO", "WOLF"}
run_dir = sys.argv[1] if len(sys.argv) > 1 else sorted(glob.glob("data/experiments/T4/*"))[-1]
VERB = r"(attacks|bites|scratches|charges at|kicks|strikes|punches|bashes|pushes|shoots|stabs|slashes|gores|collides with)"
subj_re = re.compile(r"^The ([a-z][a-z ]*?) " + VERB + r" the ")

combat = defaultdict(list)          # (arm, rep, unit) -> [text]
with open(os.path.join(run_dir, "combat.tsv")) as f:
    for r in csv.DictReader(f, delimiter="\t"):
        combat[(r["arm"], int(r["rep"]), r["unit"])].append(r["text"])

deaths = defaultdict(list)          # (arm, rep) -> [(species, killer, cls)]
status = defaultdict(list)
keys = []
seen_dead = set()
with open(os.path.join(run_dir, "events.tsv")) as f:
    for r in csv.DictReader(f, delimiter="\t"):
        k = (r["arm"], int(r["rep"]))
        if k not in keys: keys.append(k)
        if r["event"] == "death":
            uid = r["subject"]
            if (k, uid) in seen_dead: continue            # the harness can log a death twice
            seen_dead.add((k, uid))
            species = r["detail"].split()[0]
            m = re.search(r"ref6=(-?\d+),(-?\d+),(-?\d+),(-?\d+),(-?\d+)", r["detail"])
            cavern = m and (int(m.group(4)) >= 0 or int(m.group(5)) >= 0)
            subjects = Counter()
            for t in combat.get((k[0], k[1], uid), []):
                mm = subj_re.match(t)
                if mm: subjects[mm.group(1)] += 1
            killer = subjects.most_common(1)[0][0] if subjects else "-"
            if any(a in killer for a in ARMED): cls = "armed"
            elif "dog" in killer or "dwarf" in killer: cls = "fort"
            elif killer == "-": cls = "none"
            else: cls = "wild"
            if cavern: cls = "cavern"
            if species in PRED_TOKENS and cls == "armed": cls = "pred-v-pred"
            deaths[k].append((species, killer, cls))
        elif r["subject"].startswith("local ok,out=pcall(dfhack.run_command_silent") and "ecology:" in r["detail"]:
            mm = re.search(r"ecology: (\w+)\s+last write day (\d+): (\d+) predator\(s\) x (\d+) target\(s\), (\d+) pair\(s\) written", r["detail"])
            if mm: status[k].append(mm.groups())

print(f"run {run_dir}")
print("arm\trep\tarmed_kills\tfort\twild\tcavern\tnone\tkills (species<-killer)\tlast ecology status")
ok = True; seen = Counter()
for k in keys:
    d = deaths[k]; c = Counter(x[2] for x in d)
    st = status[k][-1] if status[k] else None
    stx = f"eco={st[0]} preds={st[2]} targets={st[3]} pairs={st[4]}" if st else "-"
    kills = ", ".join(f"{s}<-{kl}" for s, kl, _ in d) or "-"
    print(f"{k[0]}\t{k[1]}\t{c['armed']}\t{c['fort']}\t{c['wild']}\t{c['cavern']}\t{c['none']}\t{kills}\t{stx}")
    seen[k[0]] += 1
    if k[0].endswith("on") and c["armed"] == 0: ok = False
on_rate = sum(Counter(x[2] for x in deaths[k])["armed"] for k in keys if k[0].endswith("on"))
off_rate = sum(Counter(x[2] for x in deaths[k])["armed"] for k in keys if k[0].endswith("off"))
print(f"armed kills: on={on_rate} off={off_rate}; reps seen: {dict(seen)}")
complete = len(seen) == 2 and all(v >= 3 for v in seen.values())
print("VERDICT:", "INCOMPLETE" if not complete else ("PASS" if ok and on_rate > off_rate else "FAIL"))
