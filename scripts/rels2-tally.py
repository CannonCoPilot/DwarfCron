"""RELS2 tally: genuine DF-drawn arrivals (FREQUENCY steered toward one subject, tool off, cx-probe forces the
release) -- same reader shape as rels-tally.py, for the cougar/deer/elk cells. Usage: rels2-tally.py <run>"""
import sys, re, collections, pathlib, statistics
run = pathlib.Path(sys.argv[1])
new = collections.defaultdict(collections.Counter); series = collections.defaultdict(list); dist = collections.defaultdict(list)
pairs = collections.defaultdict(collections.Counter); subj = collections.defaultdict(collections.Counter)
freq = collections.defaultdict(list); rel_cnt = collections.defaultdict(int)
SUBJ = {"cougar": "COUGAR", "deer": "DEER", "elk": "ELK"}
for t in sorted(run.glob("RELS2*.tsv")):
    for line in open(t):
        f = line.rstrip("\n").split("\t")
        if len(f) < 5: continue
        cell, rep, kind, kv = f[1], f[2], f[3], dict(re.findall(r"(\w+)=(\S+)", f[4]))
        k = (cell, rep)
        if kind == "rel" and "ur" in kv:
            a, b, ur = kv["a"].split(":"), kv["b"].split(":"), kv["ur"]
            new[k][ur] += 1; dist[k].append(int(kv["d"]))
            if ur == "PREDATOR_OR_PREY": pairs[k][f"{a[0]}({a[1]})>{b[0]}({b[1]})"] += 1
            s = SUBJ.get(cell)
            if s and (a[0] == s or b[0] == s): subj[k][f"{a[0]}>{b[0]} {ur}"] += 1
        elif kind == "relsum": series[k].append(int(kv["entries"]))
        elif kind == "freq": freq[k].append(f"named={kv.get('named')} others={kv.get('others')}")
        elif kind == "release": rel_cnt[k] += 1
print("cell rep: freq write | releases forced | new rels by type | P_O_P subject pairs | relsum series | median first-seen d")
for k in sorted(new, key=lambda k: (k[0], k[1])):
    print(f"== {k[0]:8s} r{k[1]}: {freq[k][0] if freq[k] else '-'}  releases {rel_cnt[k]}  new {dict(new[k])}")
    print(f"   subject pairs: {dict(subj[k].most_common(8))}")
    print(f"   P_O_P pairs: {dict(pairs[k].most_common(8))}  series {series[k]}  median d {statistics.median(dist[k]) if dist[k] else '-'}")
