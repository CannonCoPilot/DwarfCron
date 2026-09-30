"""STL/STL2 tally: per cell and rep, the hunter's attacks on prey, prey killed by the placed hunter, hunter lost, and
hidden samples. Only deaths with victim_spawned=1 count (the log's 'deaths' includes cavern fights on the map).
Usage: stl-tally.py <run dir> [block]"""
import sys, re, collections, pathlib
run = pathlib.Path(sys.argv[1]); blk = sys.argv[2] if len(sys.argv) > 2 else run.name.split("-")[0]
T = collections.defaultdict(lambda: dict(att=0, kill=0, lost=0, hid=0, samp=0))
for line in open(run / f"{blk}.tsv"):
    f = line.rstrip("\n").split("\t")
    if len(f) < 5: continue
    cell, rep, kind, kv = f[1], f[2], f[3], dict(re.findall(r"(\w+)=(\S+)", f[4]))
    pred, prey = cell.split("_")[0].upper(), "_".join(cell.split("_")[1:-1])
    r = T[(cell, rep)]
    if kind == "attacks" and kv.get("pair") == f"{pred}>{prey}": r["att"] += int(kv["n"])
    elif kind == "death" and kv.get("victim_spawned") == "1":
        if kv.get("victim") == prey and kv.get("killer") == pred: r["kill"] += 1
        elif kv.get("victim") == pred: r["lost"] += 1
    elif kind == "hidden": r["samp"] += int(kv["n"]); r["hid"] += int(kv["hidden"])
cells = sorted({c for c, _ in T}, key=lambda c: (c.split("_")[0], c.split("_")[1], c.split("_")[-1]))
print("cell\trep1 att/kill/lost\trep2 att/kill/lost\thidden/samples")
arms = collections.defaultdict(lambda: [0, 0, 0, 0])
for c in cells:
    a = [T.get((c, r)) for r in ("1", "2")]
    s = "\t".join(f"{x['att']}/{x['kill']}/{x['lost']}" if x else "-" for x in a)
    print(f"{c}\t{s}\t{sum(x['hid'] for x in a if x)}/{sum(x['samp'] for x in a if x)}")
    arm = c.split("_")[-1]
    for x in a:
        if x: arms[arm][0] += x["att"]; arms[arm][1] += x["kill"]; arms[arm][2] += x["lost"]; arms[arm][3] += 1
print("\narm\tcell-reps\thunter attacks\tprey killed\thunters lost")
for k, v in arms.items(): print(f"{k}\t{v[3]}\t{v[0]}\t{v[1]}\t{v[2]}")
