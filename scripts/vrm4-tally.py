"""VRM4 tally: a runtime CREATURE_CLASS (SWV_TEST) on GRASSHOPPER matched by GOBBLE_VERMIN_CLASS on BADGER (arm
"gobble" only; "ctl" has the class with no matching gobbler). vcount near/map series every 250 t (13 samples, offset
30 tiles from the spot to clear CTRL's own pet cats), nearsum of any unit standing by the vermin. Usage: vrm4-tally.py <run>"""
import sys, re, collections, pathlib
run = pathlib.Path(sys.argv[1])
M = collections.defaultdict(list); NEAR = collections.defaultdict(list); CLS = {}; GOB = {}
for t in sorted(run.glob("VRM4*.tsv")):
    for line in open(t):
        f = line.rstrip("\n").split("\t")
        if len(f) < 5: continue
        cell, rep, kind, kv = f[1], f[2], f[3], dict(re.findall(r"(\w+)=(\S+)", f[4]))
        k = (cell, rep)
        if kind == "vcount": M[k].append((kv.get("tag"), int(kv.get("near", 0)), int(kv.get("map", 0))))
        elif kind == "nearsum": NEAR[k].append(f"{kv.get('tag')}:units={kv.get('units')}")
        elif kind == "class": CLS[k] = f"value={kv.get('value')} castes={kv.get('castes')}"
        elif kind == "gobble" and "kind" in kv: GOB[k] = f"{kv['kind']}={kv.get('value')} castes={kv.get('castes')}"
print("cell rep: GRASSHOPPER near/map series (t0..t3000) | nearsum | class write | gobble write")
for k in sorted(M, key=lambda k: (k[0], k[1])):
    series = M[k]
    near0, nearN = (series[0][1], series[-1][1]) if series else (0, 0)
    map0, mapN = (series[0][2], series[-1][2]) if series else (0, 0)
    print(f"== {k[0]:8s} r{k[1]}: near {near0}->{nearN} (removed {near0 - nearN})  map {map0}->{mapN} (removed {map0 - mapN})")
    print(f"   series: {[(t, n, m) for t, n, m in series]}")
    print(f"   class: {CLS.get(k, '-')}  gobble: {GOB.get(k, '- (ctl arm: no gobbler written)')}")
# per-arm (ctl vs gobble), both reps: does GOBBLE_VERMIN_CLASS speed removal vs the class alone?
A = collections.defaultdict(list)
for k, series in M.items():
    if series: A[k[0]].append(series[0][1] - series[-1][1])
print("\narm: near-count removed per rep (higher = more consumed)")
for arm in sorted(A): print(f"  {arm:8s} {A[arm]}")
