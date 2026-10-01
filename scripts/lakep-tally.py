"""LAKEP tally: lake-layer wild unit survey either side of a written ALLIGATOR x FISH_CARP relation (lake_wild.lua),
and whether the write survives in enemy_status_cache.rel_map over 3,000 t (lake_persist.lua). One run (--reps 1), no
arm comparison -- this block reports a single replicate's own before/after. Usage: lakep-tally.py <run>"""
import sys, re, collections, pathlib
run = pathlib.Path(sys.argv[1])
wild = collections.defaultdict(lambda: collections.defaultdict(int)); persist = collections.defaultdict(list)
for t in sorted(run.glob("LAKEP*.tsv")):
    for line in open(t):
        f = line.rstrip("\n").split("\t")
        if len(f) < 5: continue
        cell, rep, kind, kv = f[1], f[2], f[3], dict(re.findall(r"(\w+)=(\S+)", f[4]))
        k = (cell, rep)
        if kind == "lakewild": wild[(k, kv.get("tag"))][kv.get("realm", "?")] += 1
        elif kind == "lakewildsum": wild[(k, kv.get("tag"))]["__n"] = int(kv.get("n", 0))
        elif kind == "lakerel": persist[k].append((kv.get("tag"), kv.get("alive_a"), kv.get("alive_b"), kv.get("held"), kv.get("total")))
print("cell rep: lake-wild unit realm counts pre vs t3000 | held/total PREDATOR_OR_PREY pairs over time")
for k in sorted(persist, key=lambda k: (k[0], k[1])):
    for tag in ("pre", "t3000"):
        d = wild.get((k, tag), {})
        n = d.get("__n", sum(v for kk, v in d.items() if kk != "__n"))
        by_realm = {kk: vv for kk, vv in d.items() if kk != "__n"}
        print(f"== {k[0]:14s} r{k[1]} {tag}: n={n} by_realm={by_realm}")
    print(f"   persist (tag, alive_a, alive_b, held, total): {persist[k]}")
