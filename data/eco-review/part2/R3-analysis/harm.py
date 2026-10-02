"""R3: does prey mass go with predator death and injury?  Parse every ECO TSV that has placed hunters and placed prey into
one record per (cell-rep, hunter species, prey species): hunters placed, hunters dead (any cause), hunters killed by the prey
species, prey->hunter attack events (= DFHack UNIT_ATTACK events: a strike that left a fresh wound, or a killing blow;
EventManager.cpp:1133-1240), hunter->prey attack events, prey killed.  Output: harm.json + harm.tsv.
Masses: adult_size from data/bestiary/creatures.json (vanilla raws)."""
import re, json, glob, os, collections, sys
E = "/Users/nathanielcannon/Claude/Projects/DwarfCron/data/experiments/ECO/"
B = {c['id']: c for c in json.load(open("/Users/nathanielcannon/Claude/Projects/DwarfCron/data/bestiary/creatures.json"))}
FILES = """20260929-235553/P1.tsv 20260929-235553/W1L.tsv 20260929-235553/W1O.tsv 20260929-235553/T1.tsv 20260929-235553/L2.tsv
CAL-20260930-135309/CAL.tsv CAL-20260930-142550/CAL.tsv ECO3-20260930-133945/PK.tsv ECO3-20260930-133945/WB.tsv
GPK-20260930-234231/GPK.tsv GPK-20260930-234231/GPKR.tsv GPK-20260930-234231/GPKW.tsv FSH2-20260930-235459/FSH2.tsv
FVA-20260930-235715/FVA.tsv REACH-20260930-193803/FISH.tsv REACH-20260930-193803/REACHC.tsv REACH-20260930-193803/REACHF.tsv
REACH-20260930-193803/REACHW.tsv STL-20260930-155456/STL.tsv STL2-20260930-164417/STL2.tsv LONE-20260930-184842/LONE.tsv
LONE10-20260930-212000/LONE.tsv ECO2-20260930-103132/TV.tsv ECO2-20260930-103132/TV2.tsv ECO2-20260930-103132/HC1.tsv
ECO2-20260930-103132/HC2.tsv ECO2-20260930-103132/HC3.tsv ECO2-20260930-103132/HCP.tsv ECO2-20260930-103132/HO.tsv
ECO2-20260930-103132/HR.tsv HC4-20260930-233321/HC4_1.tsv HC4-20260930-233321/HC4_2.tsv HC4-20260930-233321/HC4_3.tsv
HC4-20260930-233321/HC4_P.tsv SW-20261001-003336/SW1.tsv SW-20261001-003336/SW2.tsv SWR-20261001-063950/SW1R.tsv
SWR-20261001-063950/SW2R.tsv""".split()
# cells whose arm changes the temperament of prey or hunter (excluded from the clean mass fits, reported apart)
MOD = re.compile(r"rage|RAGE|BENIGN_off|benignoff|CRAZED|OPPOSED|BENIGN_on|PEACE|NATURAL_off|CURIOUS", re.I)
SKIP = re.compile(r"^(lead_|corpses_|walkeat_|vermin_|v_|viewrange\d+_MILKFISH)")

def kv(s): return dict(re.findall(r"(\w+)=(\S+)", s))
def stem(c): return re.sub(r"(:f|:ff)?(:df|:w|_df|_w)$", "", c)
def carn(t):
    c = B.get(t) or {}
    return bool(c.get('large_predator') or c.get('carnivore')) and not c.get('benign')

def parse(path):
    R = collections.OrderedDict()
    for line in open(E + path):
        f = line.rstrip("\n").split("\t")
        if len(f) < 5: continue
        blk, cell, rep, kind, rest = f[0], f[1], f[2], f[3], f[4]
        r = R.setdefault((cell, rep), dict(block=blk, file=path, cell=cell, rep=rep, spawn=collections.Counter(), rel=[],
                                           att=collections.Counter(), deaths=[], ticks=None, order=len(R)))
        d = kv(rest)
        if kind == "spawn": r["spawn"][d["token"]] += int(d["placed"])
        elif kind == "rel": r["rel"].append((d["a"], d["b"]))
        elif kind == "attacks": r["att"][d["pair"]] += int(d["n"])
        elif kind == "death": r["deaths"].append(d)
        elif kind == "alerts": r["ticks"] = int(d.get("ticks", 0))
    return R

def pairs_for(r, stemrel):
    if SKIP.match(r["cell"]): return []
    toks = [t for t in r["spawn"] if r["spawn"][t] > 0]
    if r["rel"]:
        return sorted({(a, b) for a, b in r["rel"] if a != b and a in toks and b in toks})
    if stem(r["cell"]) in stemrel: return [p for p in stemrel[stem(r["cell"])] if p[0] in toks and p[1] in toks]
    m = re.match(r"([A-Z_]+)(\(\w+\))?x([A-Z_]+)", r["cell"])
    if m and m.group(1) in toks and m.group(3) in toks: return [(m.group(1), m.group(3))]
    m = re.match(r"([a-z]+)\d*_([A-Z_]+?)(_[a-z]+)?$", r["cell"])  # CAL/PK/STL style
    if m and m.group(1).upper() in toks and m.group(2) in toks: return [(m.group(1).upper(), m.group(2))]
    hs = [t for t in toks if carn(t)]; ps = [t for t in toks if not carn(t)]
    if len(hs) == 1 and ps: return [(hs[0], p) for p in ps]
    return []

recs = []
for path in FILES:
    R = parse(path)
    stemrel = collections.defaultdict(set)
    for r in R.values():
        for a, b in r["rel"]:
            if a != b: stemrel[stem(r["cell"])].add((a, b))
    # order of the cell within its rep (cell position in the shared load)
    pos = collections.defaultdict(int)
    for (cell, rep), r in R.items():
        pos[rep] += 1; r["pos"] = pos[rep]
    for (cell, rep), r in R.items():
        P = pairs_for(r, stemrel)
        preys = sorted({b for _, b in P})
        for h, p in P:
            dd = r["deaths"]
            hdead = [d for d in dd if d.get("victim") == h and d.get("victim_spawned") == "1"]
            x = dict(block=r["block"], file=path, cell=cell, rep=rep, pos=r["pos"], hunter=h, prey=p, nprey_species=len(preys),
                     nh=r["spawn"][h], np=r["spawn"][p], mh=B.get(h, {}).get("adult_size"), mp=B.get(p, {}).get("adult_size"),
                     prey_benign=bool(B.get(p, {}).get("benign")), written=bool(r["rel"]) or r["block"].startswith("SW"), mod=bool(MOD.search(cell)),
                     ticks=r["ticks"],
                     h_dead=len(hdead),
                     h_killed_by_prey=sum(1 for d in hdead if d.get("killer") == p and d.get("killer_spawned") == "1"),
                     h_killed_by_prey_any=sum(1 for d in hdead if d.get("killer") == p),
                     h_killed_other=sum(1 for d in hdead if d.get("killer") != p),
                     h_death_causes=collections.Counter((d.get("killer"), d.get("cause")) for d in hdead),
                     att_back=r["att"].get(f"{p}>{h}", 0), att=r["att"].get(f"{h}>{p}", 0),
                     prey_killed=sum(1 for d in dd if d.get("victim") == p and d.get("victim_spawned") == "1" and d.get("killer") == h))
            # in multi-prey cells, deaths of the hunter by 'other' are shared: count them once (on the first pair)
            if len(preys) > 1:  # multi-prey cell: attribute deaths to the prey that killed; the rest go to a cell-level 'other'
                x["h_dead"] = sum(1 for d in hdead if d.get("killer") == p)
                x["h_dead_other_cell"] = sum(1 for d in hdead if d.get("killer") not in preys) if p == preys[0] else 0
                x["h_killed_other"] = 0
            x["h_death_causes"] = {f"{k}|{c}": n for (k, c), n in x["h_death_causes"].items()}
            recs.append(x)
json.dump(recs, open(os.path.join(os.path.dirname(__file__), "harm.json"), "w"), indent=0)
cols = "block cell rep pos hunter prey nprey_species nh np mh mp prey_benign written mod ticks h_dead h_killed_by_prey h_killed_by_prey_any att_back att prey_killed".split()
with open(os.path.join(os.path.dirname(__file__), "harm.tsv"), "w") as fo:
    fo.write("\t".join(cols) + "\n")
    for x in recs: fo.write("\t".join(str(x[c]) for c in cols) + "\n")
print(len(recs), "pair records;", sum(x["h_dead"] for x in recs), "hunter deaths;", sum(x["h_killed_by_prey"] for x in recs), "by the placed prey")
