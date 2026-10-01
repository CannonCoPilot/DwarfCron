"""RELS tally: DF's own relation writes per cell. For each cell-rep: new entries by reaction and by (a class > b class),
the subject's (placed unit's) entries, live-entry counts over time, median first-seen distance. Usage: rels-tally.py <run>"""
import sys, re, collections, pathlib, statistics
run = pathlib.Path(sys.argv[1])
SUBJ = {"lion": "LION", "lion_benign": "LION", "lion_nolp": "LION", "lion_ambush": "LION", "deer": "DEER", "badger": "BADGER"}
new = collections.defaultdict(collections.Counter); series = collections.defaultdict(list); dist = collections.defaultdict(list)
subj = collections.defaultdict(collections.Counter); pairs = collections.defaultdict(collections.Counter)
att = collections.defaultdict(collections.Counter)
for line in open(run / "RELS.tsv"):
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
    elif kind == "attacks": att[k][kv.get("pair", "?")] += int(kv.get("n", 0))
for k in sorted(new, key=lambda k: (k[0], k[1])):
    print(f"== {k[0]} r{k[1]}: new {dict(new[k])}  live entries per 3k: {series[k]}  median d {statistics.median(dist[k]) if dist[k] else '-'}")
    print("   P_O_P pairs:", dict(pairs[k].most_common(8)))
    if subj[k]: print("   subject:", dict(subj[k].most_common(8)))
    if att[k]: print("   attacks:", dict(att[k].most_common(6)))
