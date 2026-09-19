#!/usr/bin/env python3
"""E32 tally: can a mid-predator be made to hunt without becoming a general predator?
The user's question from the 17th. T4 established the constraint — a BENIGN predator never acts
on a written relation, the drive is the LARGE_PREDATOR caste flag — so this arm flips that flag
on the badger's castes, which also makes the tool's ecology switch arm it.

The fork is not "does the badger hunt" but WHAT IT ATTACKS. So the report is the badger's victim
list by species, taken from the attacker side of the combat text, plus anything that would rule
a plain flag-flip out as a shippable mid-predator class: attacks on the fort's own animals, on
citizens, or on creatures well above its own weight.
Usage: e32-tally.py [run_dir]"""
import os
import csv, glob, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tallylib import drop_incomplete
from collections import Counter, defaultdict
run_dir = sys.argv[1] if len(sys.argv) > 1 else sorted(glob.glob("data/experiments/E32b/2*"))[-1]
SAMPLE = re.compile(r"e32b?: land=(\d+) badgers=(\d+) armed_castes=(\d+) citizens=(\d+) day=(\d+)")
VERB = r"(attacks|bites|scratches|charges at|kicks|strikes|punches|bashes|pushes|shoots|stabs|slashes|gores|collides with|latches on)"
# "The badger bites the groundhog in the head!"  -> attacker 'badger', victim 'groundhog'
PAIR = re.compile(r"^The ([a-z][a-z ]*?) " + VERB + r" the ([a-z][a-z ]*?)[ ,!.]", re.I)
FORT = re.compile(r"\bstray\b|\bwar \b|\btame\b", re.I)
# ⚠️ DFHack attaches a combat report to EVERY participant, so the same report id appears on the
# attacker's row and the victim's. Counting rows double-counts exactly the events that involve
# two tracked units — which is every attack this experiment is about. Dedupe on (arm, rep, report).
CITIZEN = re.compile(r"\bdwarf\b|\bUrist\b", re.I)

badgers = defaultdict(list); armed = {}; land = defaultdict(list)
for r in csv.DictReader(open(f"{run_dir}/events.tsv"), delimiter="\t"):
    if r["event"] != "manipulation": continue
    m = SAMPLE.search(r["detail"])
    if m:
        k = (r["arm"], int(r["rep"]))
        land[k].append(int(m.group(1))); badgers[k].append(int(m.group(2))); armed[k] = int(m.group(3))

victims = defaultdict(Counter)      # key -> Counter(victim species) where badger is attacker
as_victim = defaultdict(Counter)    # key -> Counter(attacker) where badger is the victim
reports = defaultdict(int)
p = os.path.join(run_dir, "combat.tsv")
if os.path.exists(p):
    seen_reports = set()
    for r in csv.DictReader(open(p), delimiter="\t"):
        k = (r["arm"], int(r["rep"]))
        rid = (k, r["report"])
        if rid in seen_reports:
            continue
        seen_reports.add(rid)
        reports[k] += 1
        m = PAIR.match(r["text"])
        if not m: continue
        attacker, victim = m.group(1).strip().lower(), m.group(3).strip().lower()
        if "badger" in attacker and "badger" not in victim:
            victims[k][victim] += 1
        elif "badger" in victim and "badger" not in attacker:
            as_victim[k][attacker] += 1

drop_incomplete(run_dir, badgers, land, armed, victims, as_victim, reports)
print(f"run {run_dir}")
print("arm\trep\tarmed castes\tbadgers min/max\tland mean\tcombat reports\tbadger ATTACKS (n)\tbadger attacked BY")
for k in sorted(badgers):
    b = badgers[k]; l = land[k]
    v = victims[k]; av = as_victim[k]
    print(f"{k[0]}\t{k[1]}\t{armed.get(k,'-')}\t{min(b)}/{max(b)}\t{sum(l)/len(l):.1f}\t{reports.get(k,0)}"
          f"\t{sum(v.values())}\t{sum(av.values())}")
    if v: print("   badger attacked: " + ", ".join(f"{s} x{n}" for s, n in v.most_common()))
    if av: print("   badger was attacked by: " + ", ".join(f"{s} x{n}" for s, n in av.most_common()))
    fort_hits = sum(n for s, n in v.items() if FORT.search(s))
    cit_hits = sum(n for s, n in v.items() if CITIZEN.search(s))
    if fort_hits or cit_hits:
        print(f"   ** OUT OF CLASS: {fort_hits} attack(s) on the fort's own animals, {cit_hits} on citizens")

arm_v = defaultdict(Counter); arm_reps = defaultdict(int)
for k in badgers:
    arm_v[k[0]] += victims[k]; arm_reps[k[0]] += 1
print("\narm\treps\tbadger attacks\tdistinct victim species\tvictims")
for a in sorted(arm_v):
    v = arm_v[a]
    print(f"{a}\t{arm_reps[a]}\t{sum(v.values())}\t{len(v)}\t{', '.join(f'{s} x{n}' for s, n in v.most_common(8)) or 'none'}")
print("\nKILL: the armed badger takes small prey and vermin and nothing else, 2 of 2, ships a mid-predator class;")
print("a badger taking anything it meets means the class needs a SIZE FILTER on the relation targets, not just the flag")
