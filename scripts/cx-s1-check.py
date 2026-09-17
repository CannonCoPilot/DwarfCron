#!/usr/bin/env python3
"""S1 regression check: every arrival of an assigned species must fall in one of its
seasons; the unassigned control (COUGAR) must move only by DF's own spawn and return;
the scheduler must snap in-season entries at each boundary.

    cx-s1-check.py data/experiments/S1/<run-id>
"""
import csv, sys, collections
from pathlib import Path
TICKS_PER_YEAR, TICKS_PER_SEASON = 403_200, 100_800
SEASON = {0: "spring", 1: "summer", 2: "autumn", 3: "winter"}
d = Path(sys.argv[1])
def rd(f): return list(csv.DictReader(open(d / f), delimiter="\t"))
roster = {r["token"]: set(int(x) for x in r["seasons"].split(",")) for r in rd("roster.tsv")}
events = rd("events.tsv")
base = {e["rep"]: int(e["abs_tick"]) for e in events if e["event"] == "baseline"}
print(f"roster: {len(roster)} assigned tokens")
bad = []; seen_seasons = set(); arrivals = collections.Counter()
for e in events:
    if e["event"] != "arrival" or "layer=surface" not in e["detail"]:
        continue
    sp = e["detail"].split()[0]
    season = (int(e["abs_tick"]) % TICKS_PER_YEAR) // TICKS_PER_SEASON
    seen_seasons.add(season); arrivals[(sp, season)] += 1
    if sp in roster and season not in roster[sp]:
        bad.append((int(e["abs_tick"]) - base[e["rep"]], sp, SEASON[season], sorted(roster[sp]), e["detail"].split("ref6=")[1].split()[0]))
print(f"surface arrivals by season: " + ", ".join(f"{SEASON[s]} {sum(v for (sp, ss), v in arrivals.items() if ss == s)}" for s in sorted(seen_seasons)))
print(f"OUT-OF-SEASON arrivals of assigned species: {len(bad)}")
for b in bad:
    print(f"  +{b[0]} {b[1]} arrived in {b[2]}; assigned {b[3]}; ref6 {b[4]}")
unassigned = collections.Counter(sp for (sp, s) in arrivals.elements() if sp not in roster)
print(f"arrivals of unassigned species (allowed, the tool leaves them alone): {dict(unassigned)}")
pops = rd("pops.tsv")
trace = collections.defaultdict(list)
for r in pops:
    if r["species"] in ("COUGAR",) or (r["species"] in roster and r["layer"] == "surface"):
        trace[(r["species"], r["ref6"])].append((int(r["abs_tick"]), int(r["quantity"]), r["extinct"]))
for key in sorted(trace):
    if key[0] == "COUGAR":
        vals = sorted(set(q for _, q, _ in trace[key]))
        print(f"COUGAR control {key[1]}: quantities seen {vals} over {len(trace[key])} samples")
# boundaries: an assigned species' in-season quantity should jump at a season flip
flips = []
for key, series in trace.items():
    if key[0] == "COUGAR": continue
    series.sort()
    for (t0, q0, x0), (t1, q1, x1) in zip(series, series[1:]):
        if (t0 % TICKS_PER_YEAR) // TICKS_PER_SEASON != (t1 % TICKS_PER_YEAR) // TICKS_PER_SEASON and (q0 == 0) != (q1 == 0):
            flips.append((t1 - base["1"], key[0], q0, q1))
print(f"entries that switched between 0 and non-zero across a season boundary: {len(flips)} (first 12)")
for f in sorted(flips)[:12]:
    print(f"  +{f[0]} {f[1]} {f[2]} -> {f[3]}")
print("RESULT:", "PASS" if not bad else "FAIL")
