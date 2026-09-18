#!/usr/bin/env python3
"""E20 tally: aquatic rotation for a year. Per rep: water-layer arrivals (ref6 feature index >= 0) by species and
season against the roster's 'water:TOKEN' seasons -> out-of-season count; the fate of water units on the map when
their species goes out of season at a boundary (death, departure, or still there), with the delay in ticks.
Usage: e20-tally.py [run_dir]"""
import csv, glob, re, sys
from collections import defaultdict
run_dir = sys.argv[1] if len(sys.argv) > 1 else sorted(glob.glob("data/experiments/E20/*"))[-1]
YEAR, SEASON = 403200, 100800
roster = defaultdict(dict)   # rep -> key -> set(seasons)
for r in csv.DictReader(open(f"{run_dir}/roster.tsv"), delimiter="\t"):
    roster[int(r["rep"])][r["token"]] = set(int(x) for x in r["seasons"].split(",") if x != "")
arr = defaultdict(list); deaths = defaultdict(dict)
for r in csv.DictReader(open(f"{run_dir}/events.tsv"), delimiter="\t"):
    rep = int(r["rep"]); m = re.search(r"ref6=(-?\d+),(-?\d+),(-?\d+),(-?\d+)", r["detail"])
    water = m and int(m.group(4)) >= 0
    if r["event"] == "arrival" and water: arr[rep].append((int(r["abs_tick"]), r["detail"].split()[0], r["subject"]))
    if r["event"] == "death" and water: deaths[rep][r["subject"]] = int(r["abs_tick"])
seen = defaultdict(lambda: defaultdict(list))   # rep -> id -> [(abs_tick, species, inactive)]
for r in csv.DictReader(open(f"{run_dir}/units.tsv"), delimiter="\t"):
    m = re.match(r"(-?\d+),(-?\d+),(-?\d+),(-?\d+)", r["ref6"])
    if not (m and int(m.group(4)) >= 0) or r["wild"] != "1": continue
    seen[int(r["rep"])][r["id"]].append((int(r["abs_tick"]), r["species"], r["inactive"] == "1", r["dead"] == "1"))
print(f"run {run_dir}")
for rep in sorted(set(roster) | set(arr)):
    keys = roster[rep]; oos = []; by = defaultdict(int)
    for t, sp, uid in arr[rep]:
        s = (t % YEAR) // SEASON; by[(sp, s)] += 1
        k = "water:" + sp
        if k in keys and s not in keys[k]: oos.append((t, sp, s))
    print(f"rep {rep}: water arrivals {len(arr[rep])} across {len(set(sp for _,sp,_ in arr[rep]))} species; OUT-OF-SEASON {len(oos)} {oos[:6]}")
    print("  arrivals by species/season:", dict(sorted(by.items())))
    print("  water roster:", {k: sorted(v) for k, v in sorted(keys.items()) if k.startswith('water:')})
    # fate at boundaries
    fates = defaultdict(int); delays = []
    for uid, track in seen[rep].items():
        track.sort(); sp = track[0][1]; k = "water:" + sp
        if k not in keys: continue
        first = track[0][0]
        # first boundary after arrival where the species is out of season
        b = (first // SEASON + 1) * SEASON
        while b < first + YEAR and ((b % YEAR) // SEASON) in keys[k]: b += SEASON
        if b >= track[-1][0] + 5000 and not any(x[2] or x[3] for x in track): continue   # never went out of season while watched
        last_alive = max((x[0] for x in track if not x[2] and not x[3]), default=first)
        if uid in deaths[rep] and deaths[rep][uid] >= b: fates["died"] += 1; delays.append(deaths[rep][uid] - b)
        elif any(x[2] for x in track if x[0] >= b): fates["departed"] += 1; delays.append(next(x[0] for x in track if x[0] >= b and x[2]) - b)
        elif last_alive >= b: fates["still there at last sample"] += 1
        else: fates["gone before boundary"] += 1
    print(f"  fate of water units past their species' out-of-season boundary: {dict(fates)}; delays (ticks after the boundary): {sorted(delays)[:10]}")
