"""VRM tally: per cell-rep, placed ROACH_LARGE (edible ground bug) and GRASSHOPPER (control) counts on the map from t0 to
the end, the consumers' hunger readings, and the gobble write. Removal = map count falls. Usage: vrm-tally.py <run>"""
import sys, re, collections, pathlib
run = pathlib.Path(sys.argv[1])
M = collections.defaultdict(lambda: collections.defaultdict(list)); G = {}; HU = collections.defaultdict(list)
lines = [l for t in sorted(run.glob("VRM*.tsv")) for l in open(t)]
for line in lines:
    f = line.rstrip("\n").split("\t")
    if len(f) < 5: continue
    cell, rep, kind, kv = f[1], f[2], f[3], dict(re.findall(r"(\w+)=(\S+)", f[4]))
    k = (cell, rep)
    if kind == "vcount": M[k][kv["race"]].append(int(kv["map"]))
    elif kind == "gobble" and "kind" in kv: G[k] = f"{kv['kind']}={kv.get('value')} castes={kv.get('castes')}"
    elif kind == "hunger": HU[k].append(f[4][:60])
print("cell rep: roach map t0->end (removed) | grasshopper t0->end | gobble write")
for k in sorted(M, key=lambda k: (k[0], k[1])):
    r, g = M[k].get("ROACH_LARGE", [0]), M[k].get("GRASSHOPPER", [0])
    print(f"{k[0]:12s} r{k[1]}: roach {r[0]}->{r[-1]} ({r[0]-r[-1]}) | grasshopper {g[0]}->{g[-1]} ({g[0]-g[-1]}) | {G.get(k, '-')}")
    if HU[k]: print("    hunger first/last:", HU[k][0], "|", HU[k][-1])
# per arm, both reps: mean removed (VRM2: every arm from the same fresh 40 roaches + 20 grasshoppers)
A = collections.defaultdict(lambda: [[], []])
for (cell, rep), m in M.items():
    r, g = m.get("ROACH_LARGE", [0]), m.get("GRASSHOPPER", [0])
    A[cell][0].append(r[0] - r[-1]); A[cell][1].append(g[0] - g[-1])
print("\narm: roach removed per rep | grasshopper removed per rep")
for cell in sorted(A): print(f"{cell:12s} roach {A[cell][0]} | grasshopper {A[cell][1]}")
