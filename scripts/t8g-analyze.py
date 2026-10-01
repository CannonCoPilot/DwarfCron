#!/usr/bin/env python3
"""T8g -- the layer-competition read of the T8-series data on disk (no rig).

Question: when more than one layer (surface, cavern 1-3, magma sea, underworld) can draw, does a draw on
one layer take arrivals from another (one global gate or cap), or does each layer draw independently?

Reads every run dir under data/experiments/T8*/ (T8, T8b..T8f: 26 replicates, all on CTRL, all with every
layer open). Pure Python, standard library only. Usage:
    .venv/bin/python scripts/t8g-analyze.py [--perm N] [--seed S]
Prints the tables that data/experiments/T8g-analysis.md quotes.

Sources. A unit's source is its population's cave: -1 = surface, 8/13/25 = caverns 1/2/3 on CTRL (cave ids
read off the T7 addendum and the z of every arrival: 36-62, 29-33, 24-31), 34 = the magma sea, 43/44 = the
underworld. The harness's own `layer` column says cavern/deep but cannot tell the three caverns apart.

Readout traps honoured (memory: experiment-readout-traps):
  * arrivals are listed at the SAMPLE tick (every 1,000 ticks here), so an arrival is dated to an interval;
  * the first sample's arrivals race the pre's write and include DF's post-load fill: they are reported
    separately and left out of every rate and every test;
  * a replicate with no arrival in a layer is censored at its last tick, not missing.
"""
import csv, glob, json, os, random, re, sys
from collections import defaultdict, Counter
from statistics import median, mean

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PERM = int(sys.argv[sys.argv.index("--perm") + 1]) if "--perm" in sys.argv else 2000
SEED = int(sys.argv[sys.argv.index("--seed") + 1]) if "--seed" in sys.argv else 8
DAY = 1200
CAVE = {-1: "surface", 8: "cavern1", 13: "cavern2", 25: "cavern3", 34: "magma", 43: "underworld", 44: "underworld"}
LAYERS = ["surface", "cavern1", "cavern2", "cavern3", "magma", "underworld"]
GROUPS = {"cavern": ["cavern1", "cavern2", "cavern3"], "deep": ["magma", "underworld"]}
SEASON = {"Spring": 0, "Summer": 1, "Autumn": 2, "Winter": 3}


def src_of(ref6):
    cave = int(ref6.split(",")[3])
    return CAVE.get(cave, f"cave{cave}")


def kv(detail):
    out = {"species": detail.split(" ")[0]}
    for tok in detail.split(" ")[1:]:
        k, _, v = tok.partition("=")
        out[k] = v
    return out


# ---------------------------------------------------------------- load
reps = []   # one dict per replicate
for run in sorted(glob.glob(os.path.join(ROOT, "data/experiments/T8*/2*"))):
    exp = os.path.basename(os.path.dirname(run))
    prov = json.load(open(os.path.join(run, "provenance.json")))
    valid = {(r["arm"], int(r["rep"])): r for r in prov["replicates"]}
    ev = defaultdict(list)
    for r in csv.DictReader(open(os.path.join(run, "events.tsv")), delimiter="\t"):
        ev[(r["arm"], int(r["rep"]))].append(r)
    snaps = defaultdict(lambda: defaultdict(list))   # rep -> tick -> [unit rows]
    for r in csv.DictReader(open(os.path.join(run, "units.tsv")), delimiter="\t"):
        if r["wild"] != "1" or r["dead"] == "1" or r["inactive"] == "1":
            continue
        snaps[(r["arm"], int(r["rep"]))][int(r["tick"])].append(r)
    # open surface entries on the two draw tiles per sample (zero quantity or extinct stops a draw)
    openpop = defaultdict(lambda: defaultdict(set))
    for r in csv.DictReader(open(os.path.join(run, "pops.tsv")), delimiter="\t"):
        if r["layer"] != "surface" or r["type"] != "Animal":
            continue
        tile = ",".join(r["ref6"].split(",")[:2])
        if tile not in ("29,20", "28,19"):
            continue
        if int(r["quantity"]) > 0 and r["extinct"] == "0":
            openpop[(r["arm"], int(r["rep"]))][int(r["tick"])].add(r["species"])
    # the tool's land ledger: release days ('detached' / 'the gate opens'), deduplicated
    releases = defaultdict(lambda: defaultdict(set)); cur = None
    for line in open(os.path.join(run, "log.txt"), errors="replace"):
        m = re.search(r"== \w+ arm=(\w+) rep=(\d+)", line)
        if m:
            cur = (m.group(1), int(m.group(2))); continue
        if cur and "t8 ledger:" in line:
            for piece in line.split(" | "):
                m2 = re.search(r"y\d+ (\w+) (\d+)\s+wave\s+land\s+(.*)", piece)
                if m2 and ("detached" in m2.group(3) or "the gate opens" in m2.group(3)):
                    yt = (SEASON[m2.group(1)] * 84 + int(m2.group(2)) - 1) * DAY
                    m3 = re.search(r"detached (\w+) x(\d+)", m2.group(3))
                    releases[cur][yt].add(f"{m3.group(1)} x{m3.group(2)}" if m3 else "gate opens")
    for key in sorted(ev):
        if not valid.get(key, {}).get("valid"):
            continue
        rows = ev[key]
        start = min(int(r["tick"]) for r in rows)
        ticks = sorted(snaps[key])
        rep = {"exp": exp, "arm": key[0], "rep": key[1], "cell": f"{exp}/{key[0]}", "start": start,
               "ticks": ticks, "end": max(int(r["tick"]) for r in rows), "snaps": snaps[key],
               "openpop": openpop[key], "releases": sorted((yt, " + ".join(sorted(w))) for yt, w in releases[key].items()), "unit_group": {},
               "waves": [], "tps": valid[key].get("ticks_per_s"), "wall": valid[key].get("wall_s")}
        # waves: arrivals of one species from one source listed at one sample = one group
        w = defaultdict(list)
        for r in rows:
            if r["event"] == "arrival":
                d = kv(r["detail"])
                w[(int(r["tick"]), src_of(d["ref6"]), d["species"])].append(int(r["subject"]))
            elif r["event"] == "present_at_start":
                d = kv(r["detail"])
                rep["unit_group"][int(r["subject"])] = ("start", src_of(d["ref6"]), d["species"], d["ref6"])
        for (t, s, sp), ids in sorted(w.items()):
            rep["waves"].append({"tick": t, "src": s, "species": sp, "n": len(ids)})
            for i in ids:
                rep["unit_group"][i] = (t, s, sp)
        # the first real sample: T8e/T8f also logged a snapshot 2-26 ticks after the start, which is not one
        rep["first_sample"] = next((t for t in ticks if t >= start + 500), start)
        reps.append(rep)

print(f"T8g: {len(reps)} valid replicates in {len(set(r['cell'] for r in reps))} cells "
      f"({', '.join(sorted(set(r['exp'] for r in reps)))})\n")

# sanity: every layer open in every replicate (no 'alone' arm exists)
# ---------------------------------------------------------------- 1. rates per layer
def lay(s, which):
    return s == which or s in GROUPS.get(which, [])

COLS = LAYERS + ["cavern", "deep"]
print("== 1. Waves (groups) and units per 10k ticks, first sample excluded; first-sample burst shown apart")
print(f"{'cell':16}{'rep':>4}{'span':>8} " + "".join(f"{c:>13}" for c in COLS) + f"{'1st-sample waves s/c/d':>25}")
rate_w = defaultdict(list); rate_u = defaultdict(list); first = defaultdict(list); fsb = defaultdict(list)
for r in reps:
    span = r["end"] - r["first_sample"]
    cells = []
    for c in COLS:
        ws = [w for w in r["waves"] if w["tick"] > r["first_sample"] and lay(w["src"], c)]
        nw = len(ws); nu = sum(w["n"] for w in ws)
        rate_w[c].append(nw / span * 1e4); rate_u[c].append(nu / span * 1e4)
        cells.append(f"{nw / span * 1e4:5.2f}/{nu / span * 1e4:5.1f}")
        ft = [w["tick"] for w in ws]
        first[c].append(((min(ft) - r["first_sample"]) / DAY, False) if ft else ((r["end"] - r["first_sample"]) / DAY, True))
    b = [sum(1 for w in r["waves"] if w["tick"] <= r["first_sample"] and lay(w["src"], c)) for c in ("surface", "cavern", "deep")]
    for c, n in zip(("surface", "cavern", "deep"), b):
        fsb[c].append(n)
    print(f"{r['cell']:16}{r['rep']:>4}{span:>8} " + "".join(f"{x:>13}" for x in cells) + f"{'/'.join(map(str, b)):>25}")
print("(each cell: waves/10k / units/10k)\n")

def q(v):
    v = sorted(v)
    return f"{median(v):6.2f} [{v[0]:.2f}-{v[-1]:.2f}]"

print(f"{'layer':12}{'waves/10k med [min-max]':>26}{'units/10k med [min-max]':>26}{'first wave after 1st sample, days med [min-max] (censored)':>60}")
for c in COLS:
    f = first[c]; cen = sum(1 for _, x in f if x)
    fv = sorted(d for d, _ in f)
    print(f"{c:12}{q(rate_w[c]):>26}{q(rate_u[c]):>26}{f'{median(fv):6.2f} [{fv[0]:.2f}-{fv[-1]:.2f}] ({cen} censored)':>60}")
print(f"first-sample burst (waves): surface {q(fsb['surface'])}  cavern {q(fsb['cavern'])}  deep {q(fsb['deep'])}\n")


# ---------------------------------------------------------------- 2. groups at once, flagged units per source
print("== 2. Groups present at once (sample snapshots after the first), per layer: median of per-rep means, and of per-rep maxima")
gstats = defaultdict(lambda: {"mean": [], "max": []}); fstats = defaultdict(lambda: {"mean": [], "max": []})
tot_groups_max = []; per_snapshot = {}
for r in reps:
    g_series = defaultdict(list); f_series = defaultdict(list); tot = []
    snap = per_snapshot[id(r)] = {}
    for t in r["ticks"]:
        if t < r["first_sample"]:
            continue
        gs = defaultdict(set); fl = Counter(); old = Counter()
        for u in r["snaps"][t]:
            s = src_of(u["ref6"])
            gid = r["unit_group"].get(int(u["id"]), ("?", s, u["species"]))
            gs[s].add(gid)
            if u["flag_src"] == "1":
                fl[s] += 1
                if gid[0] != t:          # not first listed at this very sample
                    old[s] += 1
        snap[t] = {"gs": gs, "fl": fl, "old": old}
        if t == r["first_sample"]:
            continue
        for c in COLS:
            g_series[c].append(sum(len(gs[s]) for s in gs if lay(s, c)))
            f_series[c].append(sum(fl[s] for s in fl if lay(s, c)))
        tot.append(sum(len(v) for v in gs.values()))
    for c in COLS:
        gstats[c]["mean"].append(mean(g_series[c])); gstats[c]["max"].append(max(g_series[c]))
        fstats[c]["mean"].append(mean(f_series[c])); fstats[c]["max"].append(max(f_series[c]))
    tot_groups_max.append(max(tot))
print(f"{'layer':12}{'groups mean':>22}{'groups max':>22}{'DF-flagged units mean':>26}{'flagged max':>22}")
for c in COLS:
    print(f"{c:12}{q(gstats[c]['mean']):>22}{q(gstats[c]['max']):>22}{q(fstats[c]['mean']):>26}{q(fstats[c]['max']):>22}")
print(f"all layers, groups at once (max per rep): {q(tot_groups_max)}\n")

# ---------------------------------------------------------------- 3. the per-source gate rule
print("== 3. The per-source gate: flagged units of the SAME source around each wave (surface rule, E1: a draw needs <=1)")
print("        'before' = at the previous sample; 'left' = at the wave's own sample, not counting units first listed there")
pre = defaultdict(Counter); left = defaultdict(Counter)
for r in reps:
    snap = per_snapshot[id(r)]
    ts = sorted(snap)
    for w in r["waves"]:
        if w["tick"] <= r["first_sample"] or w["tick"] not in snap:
            continue
        prev = [t for t in ts if t < w["tick"]][-1]
        pre[w["src"]][min(snap[prev]["fl"][w["src"]], 6)] += 1
        left[w["src"]][min(snap[w["tick"]]["old"][w["src"]], 6)] += 1
GATE = {}
for c in LAYERS:
    n = sum(pre[c].values())
    if not n:
        continue
    b1 = sum(v for k, v in pre[c].items() if k <= 1); l1 = sum(v for k, v in left[c].items() if k <= 1)
    GATE[c] = (n, b1, l1)
    print(f"  {c:11} waves {n:4}  <=1 before {b1:4} ({b1 / n * 100:4.0f}%)  <=1 left {l1:4} ({l1 / n * 100:4.0f}%)   left-dist {dict(sorted(left[c].items()))} (6 = 6+)")
print("  (a source whose gate opened inside the interval reads >1 before and <=1 left; 'left' is the test of the rule)\n")

# ---------------------------------------------------------------- 4. competition tests
# interval k = (t_{k-1}, t_k]; state at t_{k-1}; outcome = waves listed at t_k
def intervals(r):
    snap = per_snapshot[id(r)]
    ts = sorted(snap)
    wt = defaultdict(Counter)
    for w in r["waves"]:
        wt[w["tick"]][w["src"]] += 1
    return [{"a": a, "b": b, "s0": snap[a], "s1": snap[b], "w": wt.get(b, Counter())} for a, b in zip(ts, ts[1:])]

IV = {id(r): intervals(r) for r in reps}
allrows = [x for r in reps for x in IV[id(r)]]
cav_w = lambda x: sum(x["w"][s] for s in GROUPS["cavern"])
deep_w = lambda x: sum(x["w"][s] for s in GROUPS["deep"])
other_w = lambda x: cav_w(x) + deep_w(x)
def hz(rows, f):
    n = len(rows); k = sum(1 for x in rows if f(x))
    return f"{k:4}/{n:<5} = {k / n if n else 0:5.3f}"
surf = lambda x: x["w"]["surface"] > 0

print("== 4a. The surface gate seen OPEN: <=1 flagged surface unit at an interval's start. Did DF draw a surface wave")
print("        in that interval, and did it matter what the other layers were doing?")
openrows = [x for x in allrows if x["s0"]["fl"]["surface"] <= 1]
print(f"  surface gate open at start                 {hz(openrows, surf)}")
print(f"     ... and >=1 cavern/deep wave that interval {hz([x for x in openrows if other_w(x) > 0], surf)}")
print(f"     ... and no cavern/deep wave                {hz([x for x in openrows if other_w(x) == 0], surf)}")
print(f"  surface gate closed at start (>1)          {hz([x for x in allrows if x['s0']['fl']['surface'] > 1], surf)}")
# the same read per cavern source: its own gate open at start -> its own wave?
for c in LAYERS[1:]:
    o = [x for x in allrows if x["s0"]["fl"][c] <= 1]
    cl = [x for x in allrows if x["s0"]["fl"][c] > 1]
    f = lambda x, c=c: x["w"][c] > 0
    so = [x for x in o if x["s0"]["fl"]["surface"] <= 1 or x["w"]["surface"] > 0]
    print(f"  {c:11} own gate open {hz(o, f)}   closed {hz(cl, f)}   open AND surface open/drawing {hz(so, f)}")
print()

print("== 4b. Does a surface draw change the other layers' hazard in the same interval?")
for name, f in [("cavern (any)", lambda x: cav_w(x) > 0), ("deep (any)", lambda x: deep_w(x) > 0)]:
    print(f"  {name:13} with a surface wave {hz([x for x in allrows if surf(x)], f)}   without {hz([x for x in allrows if not surf(x)], f)}")
print()

print(f"== 4c. Co-occurrence in one interval vs a within-replicate circular-shift null ({PERM} shifts, seed {SEED})")
rng = random.Random(SEED)
def cooc(pairs):
    obs = sum(sum(1 for s, o in zip(S, O) if s and o) for S, O in pairs)
    exp_ = sum(sum(S) * sum(O) / len(S) for S, O in pairs)
    null = []
    for _ in range(PERM):
        tot = 0
        for S, O in pairs:
            k = rng.randrange(1, len(O)) if len(O) > 1 else 0
            Oc = O[k:] + O[:k]
            tot += sum(1 for s, o in zip(S, Oc) if s and o)
        null.append(tot)
    lo = sum(1 for v in null if v <= obs) / PERM; hi = sum(1 for v in null if v >= obs) / PERM
    return obs, exp_, median(null), lo, hi
COOC = {}
for name, fA, fB in [("surface x cavern(any)", surf, lambda x: cav_w(x) > 0),
                     ("surface x deep(any)", surf, lambda x: deep_w(x) > 0),
                     ("cavern1 x cavern2", lambda x: x["w"]["cavern1"] > 0, lambda x: x["w"]["cavern2"] > 0),
                     ("cavern1 x cavern3", lambda x: x["w"]["cavern1"] > 0, lambda x: x["w"]["cavern3"] > 0),
                     ("cavern2 x cavern3", lambda x: x["w"]["cavern2"] > 0, lambda x: x["w"]["cavern3"] > 0),
                     ("cavern(any) x deep", lambda x: cav_w(x) > 0, lambda x: deep_w(x) > 0)]:
    pairs = [([fA(x) for x in IV[id(r)]], [fB(x) for x in IV[id(r)]]) for r in reps]
    COOC[name] = cooc(pairs)
    obs, e, nm, lo, hi = COOC[name]
    print(f"  {name:22} both in one interval: observed {obs:3}  independence {e:5.1f}  shift-null median {nm:5.1f}  "
          f"P(null<=obs) {lo:.3f}  P(null>=obs) {hi:.3f}")
print("  (competition for one draw predicts observed BELOW the null; a shared clock or a shared trigger predicts ABOVE)\n")

print("== 4d. Across replicates: does a busy layer leave less for the others? (waves/10k, first sample excluded)")
def ranks(v):
    o = sorted(range(len(v)), key=lambda i: v[i]); rk = [0.0] * len(v); i = 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]:
            j += 1
        for k in range(i, j + 1):
            rk[o[k]] = (i + j) / 2 + 1
        i = j + 1
    return rk
def pearson(a, b):
    ma, mb = mean(a), mean(b)
    sa = sum((x - ma) ** 2 for x in a) ** .5; sb = sum((y - mb) ** 2 for y in b) ** .5
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (sa * sb) if sa and sb else float("nan")
def spearman(a, b):
    return pearson(ranks(a), ranks(b))
def perm_p(a, b, f, n=PERM):
    obs = f(a, b); bb = list(b); c = 0
    for _ in range(n):
        rng.shuffle(bb)
        if abs(f(a, bb)) >= abs(obs):
            c += 1
    return obs, c / n
for a, b in [("surface", "cavern"), ("surface", "deep"), ("cavern", "deep"), ("cavern1", "cavern2"), ("cavern1", "cavern3"), ("cavern2", "cavern3")]:
    rho, p = perm_p(rate_w[a], rate_w[b], spearman)
    print(f"  {a:8} vs {b:8} Spearman rho {rho:+.2f}  (two-sided permutation p {p:.3f}, n={len(reps)})")
cells = defaultdict(dict)
for i, r in enumerate(reps):
    cells[r["cell"]][r["rep"]] = i
dd = [(c[1], c[2]) for c in cells.values() if 1 in c and 2 in c]
for a, b in [("surface", "cavern"), ("surface", "deep"), ("cavern", "deep")]:
    da = [rate_w[a][i] - rate_w[a][j] for i, j in dd]; db = [rate_w[b][i] - rate_w[b][j] for i, j in dd]
    opp = sum(1 for x, y in zip(da, db) if x * y < 0); same = sum(1 for x, y in zip(da, db) if x * y > 0)
    print(f"  within-cell rep1-rep2 ({len(dd)} cells, removes arm and tool version): {a} vs {b}: Pearson {pearson(da, db):+.2f}; "
          f"opposite signs {opp}, same {same}")
var = lambda v: sum((x - mean(v)) ** 2 for x in v) / (len(v) - 1)
parts = ["surface", "cavern1", "cavern2", "cavern3", "deep"]
tot = [sum(rate_w[c][i] for c in parts) for i in range(len(reps))]
VR = var(tot) / sum(var(rate_w[c]) for c in parts)
vr_null = []
cols = [list(rate_w[c]) for c in parts]
for _ in range(PERM):
    for col in cols:
        rng.shuffle(col)
    t_ = [sum(col[i] for col in cols) for i in range(len(reps))]
    vr_null.append(var(t_) / sum(var(col) for col in cols))
vr_null.sort()
print(f"  variance ratio Var(total waves)/sum Var(layer waves) = {VR:.2f}; independence null (columns shuffled) 95% band "
      f"{vr_null[int(.025 * PERM)]:.2f}-{vr_null[int(.975 * PERM)]:.2f}; P(null<=obs) {sum(1 for v in vr_null if v <= VR) / PERM:.3f}")
print("  (1 = independent; <1 = layers trade off; >1 = they move together)\n")

print("== 4e. Every surface wait over 2 days (between consecutive surface waves, first sample excluded): was DF's")
print("        surface gate open during it, and did the other layers draw more than their usual rate inside it?")
waits = []
for r in reps:
    snap = per_snapshot[id(r)]; ts = sorted(snap)
    rate_o = sum(1 for x in IV[id(r)] if other_w(x) > 0) / len(IV[id(r)])
    st = [r["first_sample"]] + sorted(set(w["tick"] for w in r["waves"] if w["src"] == "surface" and w["tick"] > r["first_sample"]))
    ends = st[1:] + [None]
    for a, b in zip(st, ends):
        hi = b if b else r["end"]
        if hi - a <= 2 * DAY:
            continue
        inside = [t for t in ts if a < t < hi] if b else [t for t in ts if a < t <= hi]
        if not inside:
            continue
        mins = min(snap[t]["fl"]["surface"] for t in inside)
        open_n = sum(1 for t in inside if snap[t]["fl"]["surface"] <= 1)
        iv = [x for x in IV[id(r)] if a < x["b"] <= hi]
        ow = sum(1 for x in iv if other_w(x) > 0)
        waits.append({"cell": r["cell"], "rep": r["rep"], "a": a, "days": (hi - a) / DAY, "cens": b is None, "min": mins,
                      "open_n": open_n, "n": len(inside), "ow": ow, "ow_exp": rate_o * len(iv)})
closed_w = [w for w in waits if w["min"] > 1]
print(f"  waits > 2 days: {len(waits)}  (censored at replicate end: {sum(w['cens'] for w in waits)})")
print(f"  DF surface gate >1 flagged at EVERY sample inside the wait: {len(closed_w)} of {len(waits)}")
print(f"  samples inside waits with the gate open: {sum(w['open_n'] for w in waits)} of {sum(w['n'] for w in waits)}")
print(f"  other-layer wave intervals inside waits: {sum(w['ow'] for w in waits)} vs {sum(w['ow_exp'] for w in waits):.1f} at each rep's own rate")
print(f"  longest waits:")
for w in sorted(waits, key=lambda w: -w["days"])[:10]:
    print(f"    {w['cell']:15} rep {w['rep']}  from day {w['a'] / DAY:5.1f}  {'>' if w['cens'] else ' '}{w['days']:5.1f} d  surface flagged min {w['min']:2}  "
          f"open samples {w['open_n']}/{w['n']}  other-layer wave intervals {w['ow']} (exp {w['ow_exp']:.1f})")
print()

print("== 4f. Each tool land release (ledger day; 'detached' or 'the gate opens'), the next surface wave, and the")
print("        DF surface gate over the wait")
lat = []
for r in reps:
    snap = per_snapshot[id(r)]; ts = sorted(snap)
    sw_t = sorted(w["tick"] for w in r["waves"] if w["src"] == "surface" and w["tick"] > r["first_sample"])
    for rel, what in r["releases"]:
        if rel <= r["first_sample"] or rel >= r["end"]:
            continue
        nxt = [t for t in sw_t if t > rel]
        t1 = nxt[0] if nxt else None
        hi = t1 if t1 else r["end"]
        inside = [t for t in ts if rel + DAY <= t < hi]       # samples surely after the release day
        mn = min((snap[t]["fl"]["surface"] for t in inside), default=None)
        lat.append({"cell": r["cell"], "rep": r["rep"], "rel": rel, "what": what, "lat": hi - rel, "cens": t1 is None, "min": mn,
                    "ow": sum(1 for w in r["waves"] if rel < w["tick"] < hi and w["src"] != "surface")})
lv = sorted(x["lat"] / DAY for x in lat if not x["cens"])
slow = [x for x in lat if x["cens"] or x["lat"] > 2 * DAY + 1000]
print(f"  releases {len(lat)}; release-to-wave days median {median(lv):.2f}, quartiles {lv[len(lv) // 4]:.2f}-{lv[3 * len(lv) // 4]:.2f}, "
      f"max {lv[-1]:.1f}; censored {sum(x['cens'] for x in lat)}")
fast = [x for x in lat if x not in slow]
def is_single(x):
    d = [p for p in x["what"].split(" + ") if p != "gate opens"]
    return bool(d) and all(p.endswith(" x1") for p in d)
single = lambda xs: sum(1 for x in xs if is_single(x))
def fisher(a, b, c, d):   # two-sided, 2x2 [[a,b],[c,d]]
    from math import comb
    n = a + b + c + d; r1 = a + b; c1 = a + c
    pr = lambda k: comb(r1, k) * comb(n - r1, c1 - k) / comb(n, c1)
    p0 = pr(a)
    return sum(pr(k) for k in range(max(0, c1 - (n - r1)), min(r1, c1) + 1) if pr(k) <= p0 * (1 + 1e-9))
a_, c_ = single(slow), single(fast)
print(f"  the release detached only a ONE-animal group: slow {a_} of {len(slow)}; prompt {c_} of {len(fast)}; "
      f"Fisher two-sided p {fisher(a_, len(slow) - a_, c_, len(fast) - c_):.2g}")
print(f"  slow (> 2 days + a sample) or none: {len(slow)}; of these, DF surface gate >1 flagged at every sample a day or more after the release: "
      f"{sum(1 for x in slow if x['min'] is not None and x['min'] > 1)}")
for x in sorted(slow, key=lambda x: -x["lat"]):
    print(f"    {x['cell']:15} rep {x['rep']}  release day {x['rel'] / DAY:5.1f} ({x['what']:18})  wait {'>' if x['cens'] else ' '}{x['lat'] / DAY:5.1f} d  "
          f"min surface flagged after {x['min']}  other-layer waves in the wait {x['ow']}")
print()

print("== 5. Rig pace (for planning): ticks/s and wall s per ~100,800-tick replicate (sample every 1,000)")
print(f"  ticks/s {q([r['tps'] for r in reps])}   wall s {q([r['wall'] for r in reps])}")
