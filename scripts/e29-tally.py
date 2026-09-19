#!/usr/bin/env python3
"""E29 tally: is flags4.agitated_wilderness_creature alone enough to turn wildlife on a fort?

v6.1's safety question, and the detection here has been wrong twice, so it is worth stating what
the evidence actually is.

  * `cx-probe combat` collects EVERY WILD UNIT'S log and nothing else — a dwarf is not wild, so a
    row with species == DWARF cannot exist. Testing for one reports a clean fort while it is being
    eaten.
  * DF does not write "dwarf" in these reports either. It names a citizen by PROFESSION: "The
    miner strikes the agitated cougar in the right rear paw with her (iron pick)". So the text of
    the ANIMAL's own report is where citizen involvement appears, and it appears as a job title.
  * A report is attached to every participant, so rows are deduped on (arm, rep, report).

The headline evidence is therefore the CITIZEN COUNT, which is sampled directly and cannot be
argued with; citizen-involving combat reports corroborate it.
Usage: e29-tally.py [run_dir]"""
import csv, glob, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tallylib import drop_incomplete
from collections import defaultdict

run_dir = sys.argv[1] if len(sys.argv) > 1 else sorted(glob.glob("data/experiments/E29/*"))[-1]
SAMPLE = re.compile(r"e29: wild_land=(\d+) agitated=(\d+) within15_of_dwarves=(\d+) citizens=(\d+) day=(\d+)")
REFLAG = re.compile(r"e29: re-flagged (\d+) wild land units")

PROFESSIONS = (r"miner|woodcutter|carpenter|mason|blacksmith|metalsmith|weaponsmith|armorsmith|jeweler|"
               r"gem cutter|gem setter|craftsdwarf|bone carver|stone crafter|wood crafter|metal crafter|"
               r"farmer|planter|herbalist|brewer|cook|fisherdwarf|fish cleaner|hunter|trapper|tanner|weaver|"
               r"clothier|leatherworker|engraver|architect|mechanic|animal caretaker|animal trainer|butcher|"
               r"milker|cheese maker|thresher|wood burner|potash maker|lye maker|soap maker|glassmaker|"
               r"wax worker|bookkeeper|manager|broker|expedition leader|militia commander|militia captain|"
               r"axedwarf|speardwarf|macedwarf|hammerdwarf|swordsdwarf|crossbowdwarf|marksdwarf|pikedwarf|"
               r"recruit|peasant|child|dwarf")
CITIZEN = re.compile(r"\bthe (" + PROFESSIONS + r")\b", re.I)
# a citizen is the only thing in these logs carrying gear; animals never wield or wear anything
GEAR = re.compile(r"\((?:[a-z ]*)(?:pick|axe|sword|spear|mace|hammer|crossbow|bolt|shield|helm|mail|"
                  r"greaves|gauntlet|boot|dress|cloak|robe|trousers|shoe|sock|mitten|cap)[a-z ]*\)", re.I)

agit = defaultdict(list); near = defaultdict(list); cz = defaultdict(list); land = defaultdict(list)
reflag = defaultdict(list)
for r in csv.DictReader(open(f"{run_dir}/events.tsv"), delimiter="\t"):
    if r["event"] != "manipulation":
        continue
    k = (r["arm"], int(r["rep"]))
    m = SAMPLE.search(r["detail"])
    if m:
        land[k].append(int(m.group(1))); agit[k].append(int(m.group(2)))
        near[k].append(int(m.group(3))); cz[k].append(int(m.group(4)))
    m = REFLAG.search(r["detail"])
    if m:
        reflag[k].append(int(m.group(1)))

cit_combat = defaultdict(int); any_combat = defaultdict(int); gear_combat = defaultdict(int)
p = os.path.join(run_dir, "combat.tsv")
if os.path.exists(p):
    seen, cited = set(), set()
    for r in csv.DictReader(open(p), delimiter="\t"):
        k = (r["arm"], int(r["rep"])); rid = (k, r["report"])
        is_cit = bool(CITIZEN.search(r["text"])); is_gear = bool(GEAR.search(r["text"]))
        if rid not in seen:
            seen.add(rid); any_combat[k] += 1
        if (is_cit or is_gear) and rid not in cited:
            cited.add(rid); cit_combat[k] += 1
            if is_gear: gear_combat[k] += 1
drop_incomplete(run_dir, agit, near, cz, land, reflag, cit_combat, any_combat)

print(f"run {run_dir}")
print("arm\trep\tre-flagged/pass\tagitated vs land\twithin15 mean/max\tCITIZENS\tcombat\tCITIZEN combat")
for k in sorted(agit):
    a, n, c, l = agit[k], near[k], cz[k], land[k]
    rf = reflag.get(k) or [0]
    # the honest decay measure: agitated against the wild land count at the same sample
    ratio = [x / y for x, y in zip(a, l) if y] or [0]
    lost = c[0] - min(c)
    print(f"{k[0]}\t{k[1]}\t{sum(rf)/len(rf):.1f}\t{sum(ratio)/len(ratio):.0%} of land units"
          f"\t{sum(n)/len(n):.1f}/{max(n)}\t{c[0]}->{c[-1]} (lost {lost})\t{any_combat.get(k,0)}\t{cit_combat.get(k,0)}")

print("\narm\treps\tcitizens lost\tcitizen-combat reports\tof which the citizen was armed/clothed")
per = defaultdict(lambda: [0, 0, 0, 0])
for k in agit:
    per[k[0]][0] += 1
    per[k[0]][1] += cz[k][0] - min(cz[k])
    per[k[0]][2] += cit_combat.get(k, 0)
    per[k[0]][3] += gear_combat.get(k, 0)
for a, (reps, lost, cc, gc) in sorted(per.items()):
    print(f"{a}\t{reps}\t{lost}\t{cc}\t{gc}")
print("\nKILL: citizen-involving combat in the agitated arm and none in the control, 2 of 2, makes the flag v6.1's lever")
print("NOTE: citizens lost is the ground truth — combat.tsv holds only WILD units' logs, so a citizen")
print("      appears there only as the animal's description of them ('the miner'), never as a DWARF row.")
