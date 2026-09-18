#!/usr/bin/env python3
"""E21 tally: cavern layers rotated with the surface. Per rep: surface and cavern arrivals per 10,000 ticks against the
cavern wild units present (from the 'e21 layers' lines); out-of-season cavern arrivals against the roster's cavern keys.
Usage: e21-tally.py [run_dir]"""
import csv, glob, re, sys
from collections import defaultdict
run_dir = sys.argv[1] if len(sys.argv) > 1 else sorted(glob.glob("data/experiments/E21/*"))[-1]
YEAR, SEASON = 403200, 100800
roster = defaultdict(dict)
for r in csv.DictReader(open(f"{run_dir}/roster.tsv"), delimiter="\t"):
    roster[int(r["rep"])][r["token"]] = set(int(x) for x in r["seasons"].split(",") if x != "")
surf = defaultdict(lambda: defaultdict(int)); cav = defaultdict(lambda: defaultdict(int)); present = defaultdict(dict); oos = defaultdict(list)
for r in csv.DictReader(open(f"{run_dir}/events.tsv"), delimiter="\t"):
    rep = int(r["rep"]); t = int(r["tick"]); b = t // 10000
    m = re.search(r"ref6=(-?\d+),(-?\d+),(-?\d+),(-?\d+),(-?\d+)", r["detail"])
    if r["event"] == "arrival" and m:
        sp = r["detail"].split()[0]; s = (int(r["abs_tick"]) % YEAR) // SEASON
        if int(m.group(5)) >= 0:
            cav[rep][b] += 1
            ks = [k for k in roster[rep] if k.startswith("cavern") and k.endswith(":" + sp)]
            if ks and s not in roster[rep][ks[0]]: oos[rep].append((t, sp, s))
        elif int(m.group(4)) < 0: surf[rep][b] += 1
    mm = re.search(r"e21 layers: (.*?) \|", r["detail"])
    if mm:
        c = sum(int(x) for x in re.findall(r"cavern\d*=(\d+)", mm.group(1)))
        present[rep][b] = max(present[rep].get(b, 0), c)
print(f"run {run_dir}")
for rep in sorted(set(surf) | set(cav)):
    print(f"rep {rep}: out-of-season cavern arrivals {len(oos[rep])} {oos[rep][:5]}")
    print("  bucket(10k)\tsurface_arrivals\tcavern_arrivals\tcavern_wild_present(max)")
    for b in sorted(set(surf[rep]) | set(cav[rep]) | set(present[rep])):
        print(f"  {b*10000}\t{surf[rep].get(b,0)}\t{cav[rep].get(b,0)}\t{present[rep].get(b,'-')}")
    withc = [surf[rep].get(b,0) for b in present[rep] if present[rep][b] > 0]; without = [surf[rep].get(b,0) for b in present[rep] if present[rep][b] == 0]
    f = lambda v: f"{sum(v)/len(v):.1f} over {len(v)} buckets" if v else "-"
    print(f"  surface arrivals per 10k: with cavern wild present {f(withc)}; with none {f(without)}")
