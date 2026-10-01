"""LONE tally: per cell-rep, the hunter's attacks and kills by prey species, natives it killed, and when it died.
Usage: lone-tally.py <run dir>"""
import sys, re, collections, pathlib
run = pathlib.Path(sys.argv[1]); P = "COUGAR"
R = collections.defaultdict(lambda: dict(att=collections.Counter(), kill=collections.Counter(), nat=collections.Counter(),
                                         died=None, alive=[], lost_to=None))
for line in open(run / "LONE.tsv"):
    f = line.rstrip("\n").split("\t")
    if len(f) < 5: continue
    cell, rep, kind, kv = f[1], f[2], f[3], dict(re.findall(r"(\w+)=(\S+)", f[4]))
    r = R[(cell, rep)]
    if kind == "attacks" and kv.get("pair", "").startswith(P + ">"): r["att"][kv["pair"].split(">")[1]] += int(kv["n"])
    elif kind == "death":
        if kv.get("killer") == P and kv.get("killer_spawned") == "1":
            (r["kill"] if kv.get("victim_spawned") == "1" else r["nat"])[kv["victim"]] += 1
        elif kv.get("victim") == P and kv.get("victim_spawned") == "1":
            r["died"] = int(kv.get("dt", -1)); r["lost_to"] = f"{kv.get('killer')}/{kv.get('cause')}"
    elif kind == "alive": r["alive"].append(int(kv.get(P, 0)))
arms = collections.defaultdict(lambda: [0, 0, 0, 0, 0])
for (cell, rep) in sorted(R, key=lambda k: (k[0], int(k[1]))):
    r = R[(cell, rep)]; a, k, n = sum(r["att"].values()), sum(r["kill"].values()), sum(r["nat"].values())
    print(f"{cell} r{rep}: attacks {a} kills {k} {dict(r['kill'])} natives {n} died {'t'+str(r['died'])+' '+r['lost_to'] if r['died'] is not None else 'no'}")
    print(f"    attacks by prey {dict(r['att'])}")
    s = arms[cell.split('_')[-1]]; s[0] += 1; s[1] += a; s[2] += k; s[3] += n; s[4] += 1 if r["died"] is not None else 0
print("\narm\truns\tattacks\tkills\tnative kills\thunter died")
for k, v in arms.items(): print(f"{k}\t{v[0]}\t{v[1]}\t{v[2]}\t{v[3]}\t{v[4]}")
