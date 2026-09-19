#!/usr/bin/env python3
"""E23 tally: can an agitated wave bring a species the roster has closed?

v6.1's other safety question. Both arms pin outdoor_irritation at 100,000 with wild_sens 1 on a
savage biome, so every wildlife group DF sends is agitated by construction; one arm closes the land
roster to its three largest entries, the control runs the tool off. The fork is whether the pool
gates agitation or agitation bypasses the pool.

The discriminator is per SPECIES, not per count: an agitated arrival of a CLOSED species is the
finding, and one closed species arriving agitated is enough to say the roster does not hold under
agitation. So arrivals are split into on-roster (an entry the arm left open) and off-roster.
Usage: e23-tally.py [run_dir]"""
import csv, glob, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tallylib import drop_incomplete
from collections import defaultdict, Counter

run_dir = sys.argv[1] if len(sys.argv) > 1 else sorted(glob.glob("data/experiments/E23/*"))[-1]
KEPT = re.compile(r"e23: roster closed - (\d+) assigned, (\d+) land entries closed, (\d+) left open, kept (.+?)(?:'|$)")
SAMPLE = re.compile(r"e23: land=(\d+) agitated=(\d+) citizens=(\d+) irritation=(\d+) mix=(.*?) day=(\d+)")
SAV = re.compile(r"e23: savagery=(-?\d+) irritation=(\d+) min=(\d+) sens=(\d+) -> surface agitation chance=(\d+)%")

kept = {}; sav = {}; samples = defaultdict(list); arrivals = defaultdict(Counter)
for r in csv.DictReader(open(f"{run_dir}/events.tsv"), delimiter="\t"):
    k = (r["arm"], int(r["rep"]))
    if r["event"] == "arrival":
        m = re.search(r"layer=(\w+)", r["detail"])
        if m and m.group(1) == "surface":
            arrivals[k][r["detail"].split()[0]] += 1
    elif r["event"] == "manipulation":
        m = KEPT.search(r["detail"])
        if m:
            kept[k] = set(re.findall(r"([A-Z][A-Z0-9_]+)\(", m.group(4))) or set(
                t.split("(")[0] for t in m.group(4).split("+"))
        m = SAV.search(r["detail"])
        if m:
            sav[k] = (int(m.group(1)), int(m.group(5)))
        m = SAMPLE.search(r["detail"])
        if m:
            mix = {}
            if m.group(5) != "none":
                for part in m.group(5).split(","):
                    bits = part.strip().rsplit(" x", 1)
                    if len(bits) == 2 and bits[1].isdigit():
                        mix[bits[0].strip()] = int(bits[1])
            samples[k].append((int(m.group(1)), int(m.group(2)), int(m.group(3)), mix))
drop_incomplete(run_dir, samples, arrivals, kept, sav)

print(f"run {run_dir}")
for k in sorted(samples):
    s = samples[k]
    open_set = kept.get(k)
    ag_species = Counter()
    for _, _, _, mix in s:
        for t, n in mix.items():
            ag_species[t] = max(ag_species[t], n)
    land = [x[0] for x in s]; ag = [x[1] for x in s]; cz = [x[2] for x in s]
    sv, ch = sav.get(k, ("?", "?"))
    share = [a / l for a, l in zip(ag, land) if l] or [0]
    print(f"\n=== {k[0]} rep {k[1]}  savagery={sv} chance={ch}%  "
          f"land mean {sum(land)/len(land):.1f}, agitated {sum(share)/len(share):.0%} of them, "
          f"citizens {cz[0]}->{cz[-1]}")
    if open_set is not None:
        print(f"    roster left OPEN: {', '.join(sorted(open_set))}")
    arr = arrivals[k]
    if open_set:
        on = {t: n for t, n in arr.items() if t in open_set}
        off = {t: n for t, n in arr.items() if t not in open_set}
        print(f"    surface arrivals: {sum(arr.values())} total — "
              f"ON-roster {sum(on.values())} ({', '.join(f'{t} x{n}' for t, n in sorted(on.items())) or 'none'})")
        print(f"                      OFF-roster {sum(off.values())} "
              f"({', '.join(f'{t} x{n}' for t, n in sorted(off.items(), key=lambda x: -x[1])[:8]) or 'none'})")
        verdict = ("the pool GATES agitation — nothing closed arrived" if not off else
                   f"agitation BYPASSES the pool — {len(off)} closed species arrived")
        print(f"    >>> {verdict}")
    else:
        print(f"    surface arrivals: {sum(arr.values())} — "
              f"{', '.join(f'{t} x{n}' for t, n in sorted(arr.items(), key=lambda x: -x[1])[:8])}")
    if ag_species:
        print(f"    agitated species seen on the map: "
              f"{', '.join(f'{t} x{n}' for t, n in sorted(ag_species.items(), key=lambda x: -x[1]))}")
print("\nKILL: agitated arrivals confined to open entries, 2 of 2, lets v6.1 ship irruptions on the roster the")
print("      player already sets; any closed species arriving agitated means the module needs its own filter")
