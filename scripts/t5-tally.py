#!/usr/bin/env python3
"""T5 tally (v5.7 gate). Per rep: leader markers seen; hold tick and kangaroo count through the hold; dismiss tick and
the tick the last held kangaroo left; kangaroo pool entry at start, during the hold, and at the end; stuck units
(same tile 5 consecutive samples); first dingo/cougar/wolf pack's mean spread (E28 method).
Usage: t5-tally.py [run_dir]"""
import csv, glob, re, sys
from collections import defaultdict
run_dir = sys.argv[1] if len(sys.argv) > 1 else sorted(glob.glob("data/experiments/T5/*"))[-1]
ev = defaultdict(list)
for r in csv.DictReader(open(f"{run_dir}/events.tsv"), delimiter="\t"): ev[int(r["rep"])].append(r)
pos = defaultdict(lambda: defaultdict(dict))   # rep -> tick -> id -> (species, x, y, z, wild)
for r in csv.DictReader(open(f"{run_dir}/units.tsv"), delimiter="\t"):
    if r["dead"] == "1" or r["inactive"] == "1": continue
    pos[int(r["rep"])][int(r["tick"])][r["id"]] = (r["species"], int(r["x"]), int(r["y"]), int(r["z"]), r["wild"], r["layer"])
print(f"run {run_dir}")
for rep in sorted(ev):
    rows = ev[rep]; led = set(); hold = dism = None; pool = []
    for r in rows:
        d = r["detail"]; t = int(r["tick"])
        for m in re.finditer(r"([A-Z_]+) x(\d+) \w+ \(day \d+\) (\w+) led by #(\d+)", d): led.add((m.group(1), m.group(3)))
        if "t5: held KANGAROO" in d and hold is None: hold = t
        if "t5: dismissed KANGAROO" in d and dism is None: dism = t
        for m in re.finditer(r"t5 pool: KANGAROO idx (\d+) quantity (\d+)", d): pool.append((t, int(m.group(2))))
    ticks = sorted(pos[rep])
    kang = {t: sum(1 for v in pos[rep][t].values() if v[0] == "KANGAROO" and v[4] == "1") for t in ticks}
    during = [kang[t] for t in ticks if hold and dism and hold <= t <= dism]
    gone_at = next((t for t in ticks if dism and t > dism and kang[t] == 0), None)
    stuck = set(); run = defaultdict(lambda: (None, 0))
    for t in ticks:
        for uid, v in pos[rep][t].items():
            if v[4] != "1" or v[5] != "surface" or v[0].startswith("BIRD_"): continue   # fliers perch in trees for days
            last, n = run[uid]; run[uid] = (v[1:4], n + 1 if v[1:4] == last else 1)
            if run[uid][1] >= 5: stuck.add((uid, v[0]))
    # first armed pack spread: the first single species with 4+ wild members at once, followed by id
    pack = None; psp = None; dists = []
    for t in ticks:
        for sp in ("DINGO", "COUGAR", "WOLF"):
            armed = {u: v for u, v in pos[rep][t].items() if v[0] == sp and v[4] == "1"}
            if pack is None and len(armed) >= 4: pack, psp = set(armed), sp
        if pack:
            u = {i: v for i, v in pos[rep][t].items() if i in pack and v[4] == "1"}
            if len(u) >= 2:
                cx = sum(v[1] for v in u.values()) / len(u); cy = sum(v[2] for v in u.values()) / len(u)
                dists.append(sum(max(abs(v[1] - cx), abs(v[2] - cy)) for v in u.values()) / len(u))
    p0 = pool[0][1] if pool else None; pmid = [q for t, q in pool if hold and dism and hold <= t <= dism]; pend = pool[-1][1] if pool else None
    spread = f"{psp} {sum(dists)/len(dists):.2f} over {len(dists)} samples" if dists else "no armed pack of 4+"
    print(f"rep {rep}: led={sorted(led)}")
    print(f"  hold at {hold}, kangaroos during hold min/max {min(during) if during else '-'}/{max(during) if during else '-'}, dismiss at {dism}, all gone at {gone_at}")
    print(f"  kangaroo pool: start {p0}, during hold {sorted(set(pmid))}, end {pend}")
    print(f"  stuck units: {sorted(stuck)}; armed pack spread {spread}")
