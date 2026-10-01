"""COH/COHO/COHR tally: group cohesion via the `lead` verb substitution (largest-male vs none -- see report for why
this stands in for a dedicated tool-side cohesion toggle). leader_dist.lua gives mean/max member distance to the
chosen leader each sample; group_spread.lua gives the group's own bounding-box width/depth. Compares the
"largest-male" and "none" arms of the same token pair-wise. Usage: coh-tally.py <run> [COH COHO COHR ...]"""
import sys, re, collections, pathlib, statistics
run = pathlib.Path(sys.argv[1])
blocks = sys.argv[2:] or ["COH", "COHO", "COHR"]
ld = collections.defaultdict(list); sp = collections.defaultdict(list)
for bname in blocks:
    for t in sorted(run.glob(f"{bname}*.tsv")):
        for line in open(t):
            f = line.rstrip("\n").split("\t")
            if len(f) < 5: continue
            cell, rep, kind, kv = f[1], f[2], f[3], dict(re.findall(r"(\w+)=(\S+)", f[4]))
            k = (cell, rep)
            if kind == "leaderdist": ld[k].append((kv.get("tag"), float(kv.get("mean", -1)), float(kv.get("max", -1)), int(kv.get("leader", -1))))
            elif kind == "spread": sp[k].append((kv.get("tag"), int(kv.get("n", 0)), int(kv.get("width", 0)), int(kv.get("depth", 0))))
print("cell rep: mean member-to-leader distance (time series) | bounding-box spread (time series)")
for k in sorted(ld, key=lambda k: (k[0], k[1])):
    means = [m for _, m, _, _ in ld[k] if m >= 0]
    widths = [w for _, n, w, d in sp[k]]
    depths = [d for _, n, w, d in sp[k]]
    print(f"== {k[0]:26s} r{k[1]}: mean dist series {['%.1f' % m for m in means]}")
    print(f"   width series {widths}  depth series {depths}")
# pair "<group>_largest-male" against "<group>_none" for the same token, both reps. leader_dist.lua always reports
# mean=-1 for the "none" arm (no leader is ever chosen, by design -- that IS the "cohesion off" reading), so the
# real largest-male-vs-none signal is the bounding-box spread, not member-to-leader distance.
dist_pairs = collections.defaultdict(lambda: {"largest-male": [], "none": []})
spread_pairs = collections.defaultdict(lambda: {"largest-male": [], "none": []})
for (cell, rep), rows in ld.items():
    for suffix in ("largest-male", "none"):
        if cell.endswith("_" + suffix):
            base = cell[: -len(suffix) - 1]
            means = [m for _, m, _, _ in rows if m >= 0]
            if means: dist_pairs[base][suffix].append(statistics.mean(means))
for (cell, rep), rows in sp.items():
    for suffix in ("largest-male", "none"):
        if cell.endswith("_" + suffix):
            base = cell[: -len(suffix) - 1]
            widths = [w for _, n, w, d in rows]
            if widths: spread_pairs[base][suffix].append(statistics.mean(widths))
print("\ntoken: mean(mean member-to-leader distance) largest-male vs none, per rep (none is always -1 by design)")
for base in sorted(dist_pairs):
    lm, no = dist_pairs[base]["largest-male"], dist_pairs[base]["none"]
    print(f"  {base:20s} largest-male {['%.1f' % x for x in lm]}  none {['%.1f' % x for x in no]}")
print("\ntoken: mean(bounding-box width) largest-male vs none, per rep -- this is the real cohesion signal")
for base in sorted(spread_pairs):
    lm, no = spread_pairs[base]["largest-male"], spread_pairs[base]["none"]
    print(f"  {base:20s} largest-male {['%.1f' % x for x in lm]}  none {['%.1f' % x for x in no]}")
