"""R3 fits on harm.json.  y1 = hunters killed by the placed prey species (binomial of hunters placed);
y2 = prey->hunter attack events (UNIT_ATTACK = new wound or killing blow by the prey's race on the hunter's race), Poisson/quasi.
Run: python3 harm.py && python3 fit.py > fit.out"""
import json, sys, collections, numpy as np
sys.path.insert(0, "/Users/nathanielcannon/Claude/Projects/DwarfCron/data/eco-review/part1/A-mechanics-analysis")
from glm import fit, report, lrt
from scipy import stats
R = json.load(open("harm.json"))
l2 = np.log2

def clean(x): return x["written"] and not x["mod"] and x["mh"] and x["mp"] and x["nh"] > 0 and x["np"] > 0

def show(title, rows):
    print(f"\n### {title}")
    g = collections.OrderedDict()
    for x in rows:
        k = (x["hunter"], x["prey"])
        a = g.setdefault(k, dict(cr=0, nh=0, dead=0, back=0, att=0, pk=0, np=0, mh=x["mh"], mp=x["mp"], ben=x["prey_benign"]))
        a["cr"] += 1; a["nh"] += x["nh"]; a["dead"] += x["h_killed_by_prey"]; a["back"] += x["att_back"]; a["att"] += x["att"]; a["pk"] += x["prey_killed"]; a["np"] += x["np"]
    for (h, p), a in sorted(g.items(), key=lambda kv: (kv[0][0], kv[1]["mp"])):
        print(f"{h:26s} {p:20s} mp={a['mp']:>8} mp/mh={a['mp']/a['mh']:7.2f} benign={int(a['ben'])} cr={a['cr']:3d} hunters={a['nh']:4d} "
              f"killed_by_prey={a['dead']:3d} ({a['dead']/a['nh']:.2f}) back/hunter={a['back']/a['nh']:6.2f} back/att={a['back']/max(a['att'],1):.2f} prey_killed={a['pk']}/{a['np']}")

def binfit(name, rows, terms):
    y = np.array([x["h_killed_by_prey"] for x in rows]); m = np.array([x["nh"] for x in rows])
    X = np.column_stack([np.ones(len(rows))] + [np.array([t[1](x) for x in rows], float) for t in terms])
    r1 = fit(X, y, "binom", m=m); print(report(name, r1, ["const"] + [t[0] for t in terms]))
    for j, t in enumerate(terms):
        X0 = np.delete(X, j + 1, axis=1); r0 = fit(X0, y, "binom", m=m); d, k, p = lrt(r0, r1)
        print(f"   LRT drop {t[0]}: chi2={d:.2f} df={k} p={p:.4f}")
    return r1

def poisfit(name, rows, terms, yk="att_back"):
    y = np.array([x[yk] for x in rows], float)
    off = np.log(np.array([max(x["ticks"] or 3000, 1) for x in rows], float) / 3000)
    X = np.column_stack([np.ones(len(rows))] + [np.array([t[1](x) for x in rows], float) for t in terms])
    r1 = fit(X, y, "pois", off=off); print(report(name + " (quasi-Poisson SEs, offset log ticks/3000)", r1, ["const"] + [t[0] for t in terms], quasi=True))
    return r1

LMP = ("log2 prey mass", lambda x: l2(x["mp"])); LRATIO = ("log2 prey/hunter mass", lambda x: l2(x["mp"] / x["mh"]))
LNH = ("log2 n hunters", lambda x: l2(x["nh"])); LNP = ("log2 n prey", lambda x: l2(x["np"]))
LPACK = ("log2 packmass/preymass", lambda x: l2(x["nh"] * x["mh"] / x["mp"]))
BEN = ("prey BENIGN", lambda x: float(x["prey_benign"]))

C = [x for x in R if clean(x)]
print(f"clean pair-records (written, no temperament arm): {len(C)}; hunters {sum(x['nh'] for x in C)}; killed by prey {sum(x['h_killed_by_prey'] for x in C)}")
show("All clean pairs, per hunter x prey (summed over cell-reps)", C)
show("Temperament arms (RAGE / BENIGN off / CRAZED etc.), for contrast", [x for x in R if x["mod"] and x["mh"] and x["mp"]])

print("\n## A. Pooled, all clean pairs (binomial, hunters killed by prey / hunters placed)")
binfit("A1 prey mass", C, [LMP])
binfit("A2 prey/hunter mass", C, [LRATIO])
binfit("A3 prey/hunter mass + n hunters + n prey + BENIGN", C, [LRATIO, LNH, LNP, BEN])
binfit("A4 pack-mass/prey-mass ratio + BENIGN", C, [LPACK, BEN])

W = [x for x in C if x["hunter"] == "WOLF" and x["prey"] in ("DEER", "ELK", "MOOSE", "WATER_BUFFALO", "ELEPHANT")]
print(f"\n## B. Wolves on the deer..elephant ladder (CAL x2, PK, SW1/SW2/SW1R/SW2R, TV/TV2/T1/FVA/L2 controls, P1): {len(W)} records, "
      f"{sum(x['nh'] for x in W)} wolves, {sum(x['h_killed_by_prey'] for x in W)} killed by prey")
binfit("B1 prey mass", W, [LMP])
binfit("B2 prey mass + n wolves", W, [LMP, LNH])
binfit("B3 pack-mass/prey-mass ratio", W, [LPACK])
for blk in ("CAL", "CALa1", "PK"):
    pass
CP = [x for x in W if x["block"] in ("CAL", "PK")]
binfit("B4 CAL+PK only: prey mass + n wolves", CP, [LMP, LNH])
NE = [x for x in W if x["prey"] != "ELEPHANT"]
print(f"   without elephant: {len(NE)} records, {sum(x['nh'] for x in NE)} wolves, {sum(x['h_killed_by_prey'] for x in NE)} killed")
binfit("B5 wolves, deer..buffalo only (no elephant): prey mass + n wolves", NE, [LMP, LNH])

print("\n## C. Injury proxy: prey->hunter wounding strikes (UNIT_ATTACK prey>hunter)")
poisfit("C1 all clean: prey/hunter mass + n hunters + n prey + BENIGN", C, [LRATIO, LNH, LNP, BEN])
poisfit("C2 wolves ladder: prey mass + n wolves", W, [LMP, LNH])
poisfit("C3 wolves ladder: hunter->prey strikes (fight length) ~ prey mass + n wolves", W, [LMP, LNH], yk="att")
# wounds received per hunter death, and per strike made
for k in ("DEER", "ELK", "MOOSE", "WATER_BUFFALO", "ELEPHANT"):
    s = [x for x in W if x["prey"] == k]
    a = sum(x["att"] for x in s); b = sum(x["att_back"] for x in s); d = sum(x["h_killed_by_prey"] for x in s); n = sum(x["nh"] for x in s)
    print(f"   {k:14s} wolves {n:4d} strikes made {a:5d} strikes taken {b:4d} taken/made {b/max(a,1):.3f} killed {d:3d} ({d/n:.3f})")

print("\n## D. Cell position (shared load), wolves ladder: deaths vs position within rep")
pos = [(x["pos"], x["h_killed_by_prey"] / x["nh"], x["prey"]) for x in W if x["block"] in ("CAL", "PK")]
rho, p = stats.spearmanr([a for a, _, _ in pos], [b for _, b, _ in pos]); print(f"   CAL+PK: Spearman(pos, death share) rho={rho:.2f} p={p:.3f} (prey order = mass order, so not separable)")
for blk in ("SW1", "SW2", "SW1R", "SW2R"):
    s = [x for x in W if x["block"] == blk and x["prey"] == "ELEPHANT"]
    print(f"   {blk}: wolves killed by elephants per cell position", sorted((x["pos"], x["h_killed_by_prey"]) for x in s))

print("\n## E. Robustness")
BENR = [x for x in C if x["prey_benign"]]
binfit("E1 BENIGN prey only: prey/hunter mass + n hunters", BENR, [LRATIO, LNH])
NOEL = [x for x in BENR if x["prey"] != "ELEPHANT"]
print(f"   BENIGN prey, no elephant: {len(NOEL)} records, {sum(x['nh'] for x in NOEL)} hunters, {sum(x['h_killed_by_prey'] for x in NOEL)} killed")
binfit("E2 BENIGN prey, elephant removed: prey/hunter mass + n hunters", NOEL, [LRATIO, LNH])
SURF = [x for x in NOEL if not x["block"].startswith(("HC", "REACHC"))]
print(f"   ...and surface only: {len(SURF)} records, {sum(x['nh'] for x in SURF)} hunters, {sum(x['h_killed_by_prey'] for x in SURF)} killed")
binfit("E3 BENIGN surface prey, no elephant: prey/hunter mass + n hunters", SURF, [LRATIO, LNH])
poisfit("E4 BENIGN prey: wounding strikes taken ~ prey/hunter mass + n hunters + n prey", BENR, [LRATIO, LNH, LNP])
poisfit("E5 BENIGN prey, no elephant: wounding strikes taken ~ prey/hunter mass + n hunters + n prey", NOEL, [LRATIO, LNH, LNP])
NB = [x for x in C if not x["prey_benign"]]
print(f"   non-BENIGN prey (capybara, crundle, reacher): {sum(x['nh'] for x in NB)} hunters, {sum(x['h_killed_by_prey'] for x in NB)} killed by prey;"
      f" BENIGN prey: {sum(x['nh'] for x in BENR)} hunters, {sum(x['h_killed_by_prey'] for x in BENR)} killed")

print("\n## F. SW1/SW2/SW1R/SW2R: one wolf pack (5) meets DEER x6, WATER_BUFFALO x6, ELEPHANT x4 in the SAME cell (no position confound between prey)")
for p in ("DEER", "WATER_BUFFALO", "ELEPHANT"):
    s = [x for x in R if x["block"].startswith("SW") and x["prey"] == p]
    print(f"   {p:14s} cell-reps {len(s)} wolf-exposures {sum(x['nh'] for x in s)} strikes made {sum(x['att'] for x in s):5d} taken {sum(x['att_back'] for x in s):4d}"
          f" wolves killed by it {sum(x['h_killed_by_prey'] for x in s):3d}  prey killed {sum(x['prey_killed'] for x in s)}/{sum(x['np'] for x in s)}")
s = [x for x in R if x["block"].startswith("SW") and x["prey"] == "ELEPHANT"]
k = [x["h_killed_by_prey"] for x in s]; print(f"   wolves killed by elephants per run: mean {np.mean(k):.2f}, runs with >=1 loss {sum(1 for v in k if v)}/{len(k)}")
print("\n## G. Hyena vs giant hyena on elephants (relative mass)")
for h in ("HYENA", "GIANT_HYENA"):
    s = [x for x in C if x["hunter"] == h and x["prey"] == "ELEPHANT"]
    print(f"   {h:12s} mp/mh {5000000/s[0]['mh']:.1f} hunters {sum(x['nh'] for x in s)} killed {sum(x['h_killed_by_prey'] for x in s)} strikes taken {sum(x['att_back'] for x in s)} elephants killed {sum(x['prey_killed'] for x in s)}/{sum(x['np'] for x in s)}")

print("\n## H. Wolves: killed by prey / wolves placed (strikes taken), by block family and prey")
fam = lambda b: "SW*" if b.startswith("SW") else ("CAL" if b == "CAL" else ("PK" if b == "PK" else "TV/TV2/T1/FVA/L2/P1"))
tab = collections.defaultdict(lambda: [0, 0, 0, 0])
for x in W:
    a = tab[(fam(x["block"]), x["prey"])]; a[0] += x["h_killed_by_prey"]; a[1] += x["nh"]; a[2] += x["att_back"]; a[3] += 1
for k in sorted(tab, key=lambda k: (k[0], {"DEER":1,"ELK":2,"MOOSE":3,"WATER_BUFFALO":4,"ELEPHANT":5}[k[1]])):
    a = tab[k]; print(f"   {k[0]:22s} {k[1]:14s} {a[0]:3d}/{a[1]:4d}  taken {a[2]:4d}  cell-reps {a[3]}")
