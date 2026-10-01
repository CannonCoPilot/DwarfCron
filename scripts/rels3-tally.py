"""RELS3 tally: are groups the TOOL releases (seasonal-wildlife enable + groups on) treated as non-wild the same way
DF's own gate treats them? tool_on has ecology OFF so only the release/gate mechanism is isolated; tool_off is the
untouched control. Same reader shape as rels-tally.py. Usage: rels3-tally.py <run>"""
import sys, re, collections, pathlib, statistics
run = pathlib.Path(sys.argv[1])
new = collections.defaultdict(collections.Counter); series = collections.defaultdict(list); dist = collections.defaultdict(list)
pairs = collections.defaultdict(collections.Counter)
for t in sorted(run.glob("RELS3*.tsv")):
    for line in open(t):
        f = line.rstrip("\n").split("\t")
        if len(f) < 5: continue
        cell, rep, kind, kv = f[1], f[2], f[3], dict(re.findall(r"(\w+)=(\S+)", f[4]))
        k = (cell, rep)
        if kind == "rel" and "ur" in kv:
            a, b, ur = kv["a"].split(":"), kv["b"].split(":"), kv["ur"]
            new[k][ur] += 1; dist[k].append(int(kv["d"]))
            if ur == "PREDATOR_OR_PREY": pairs[k][f"{a[0]}({a[1]})>{b[0]}({b[1]})"] += 1
        elif kind == "relsum": series[k].append(int(kv["entries"]))
print("cell rep: new rels by type | P_O_P pairs | relsum series (live entries per 3k) | median first-seen d")
for k in sorted(new, key=lambda k: (k[0], k[1])):
    print(f"== {k[0]:8s} r{k[1]}: new {dict(new[k])}  series {series[k]}  median d {statistics.median(dist[k]) if dist[k] else '-'}")
    print(f"   P_O_P pairs: {dict(pairs[k].most_common(8))}")
# tool_on vs tool_off side by side, since this is the entire point of the block
arms = sorted({c for c, _ in new})
print("\narm comparison (mean P_O_P new-pair count per rep):")
for a in arms:
    vals = [sum(pairs[k].values()) for k in pairs if k[0] == a]
    print(f"  {a:10s} {vals}  mean {statistics.mean(vals) if vals else '-'}")
