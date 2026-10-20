"""Food-web structure of three directed networks (edge = eater -> eaten) per fort x layer x season.
L0 = tool's tier ladder through 16 Oct (v7.6.1), L1 = today's ladder (the cast builder now), NR = New Rules."""
import json, sys, math, collections
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components, shortest_path
SP = sys.argv[1]
G = json.load(open(SP + '/graph/graphs.json'))
LEVELS = ['vermin', 'prey', 'predator', 'apex']

def gini(x):
    x = np.sort(np.asarray(x, float))
    if x.sum() == 0: return 0.0
    n = len(x); return float((2 * np.arange(1, n + 1) - n - 1).dot(x) / (n * x.sum()))

def trophic_levels(n, E):
    """prey-averaged trophic level: TL_i = 1 + mean TL of i's prey; species that eat nothing are TL 1"""
    A = np.zeros((n, n))
    for a, b in E: A[a, b] = 1
    k = A.sum(1)
    Q = np.divide(A, k[:, None], out=np.zeros_like(A), where=k[:, None] > 0)
    M = np.eye(n) - Q
    try: tl = np.linalg.solve(M, np.ones(n)); ok = True
    except np.linalg.LinAlgError: tl = np.linalg.lstsq(M, np.ones(n), rcond=None)[0]; ok = False
    return tl, ok

def metrics(nodes, E):
    n = len(nodes); idx = {x['t']: i for i, x in enumerate(nodes)}
    e = [(idx[a], idx[b]) for a, b, *_ in E if a in idx and b in idx]
    L = len(e)
    outd = np.zeros(n, int); ind = np.zeros(n, int)
    for a, b in e: outd[a] += 1; ind[b] += 1
    cat = ['isolated' if o == 0 and i == 0 else 'top' if i == 0 else 'basal' if o == 0 else 'intermediate' for o, i in zip(outd, ind)]
    es = set(e); mutual = sum(1 for a, b in e if (b, a) in es) // 2
    if n:
        A = csr_matrix((np.ones(L), ([a for a, _ in e], [b for _, b in e])), shape=(n, n))
        ncomp, lab = connected_components(A, directed=True, connection='strong')
        sizes = collections.Counter(lab); cyc = [s for s in sizes.values() if s > 1]
        D = shortest_path(A, directed=True, unweighted=True)
    else: cyc, D = [], np.zeros((0, 0))
    tl, tlok = trophic_levels(n, e) if n else (np.zeros(0), True)
    lev = [x['level'] for x in nodes]
    apex = [i for i in range(n) if lev[i] == 'apex']; verm = [i for i in range(n) if lev[i] == 'vermin']
    # vermin with a chain of eaters up to an apex (apex =>* vermin)
    vreach = [v for v in verm if any(np.isfinite(D[a, v]) for a in apex)] if apex else []
    plen = [D[a, v] for v in verm for a in apex if np.isfinite(D[a, v])]
    # non-vermin animals sitting on some apex => ... => vermin chain
    spine = [i for i in range(n) if lev[i] in ('prey', 'predator') and any(np.isfinite(D[a, i]) for a in apex) and any(np.isfinite(D[i, v]) for v in verm)]
    # edges by seat level, and inverted edges (eater sits on a lower seat than the eaten)
    lvl = collections.Counter((lev[a], lev[b]) for a, b in e)
    inverted = sum(c for (x, y), c in lvl.items() if LEVELS.index(x) < LEVELS.index(y))
    same = sum(c for (x, y), c in lvl.items() if x == y)
    # mass ratio eater/eaten for animal prey
    mr = [math.log10(nodes[a]['m'] / nodes[b]['m']) for a, b in e if nodes[b]['level'] != 'vermin' and nodes[a]['m'] and nodes[b]['m']]
    heavier = sum(1 for x in mr if x < 0)
    # trophic level vs seat
    tl_by = {l: float(np.mean([tl[i] for i in range(n) if lev[i] == l])) for l in LEVELS if any(lev[i] == l for i in range(n))}
    anim = [i for i in range(n) if lev[i] != 'vermin']
    rho = None
    if len(anim) > 3:
        r1 = np.argsort(np.argsort([tl[i] for i in anim])); r2 = np.argsort(np.argsort([math.log10(max(1, nodes[i]['m'])) for i in anim]))
        rho = float(np.corrcoef(r1, r2)[0, 1])
    deg = outd + ind
    hubs = sorted(range(n), key=lambda i: -deg[i])[:5]
    return dict(S=n, L=L, C=L / n ** 2 if n else 0, LS=L / n if n else 0,
        cats=dict(collections.Counter(cat)), isolated=[nodes[i]['nm'] for i in range(n) if cat[i] == 'isolated'],
        apex_eaten=[nodes[i]['nm'] for i in apex if ind[i] > 0], apex_no_prey=[nodes[i]['nm'] for i in apex if outd[i] == 0],
        pred_no_prey=[nodes[i]['nm'] for i in range(n) if lev[i] == 'predator' and outd[i] == 0],
        mutual=mutual, cycles=len(cyc), cyc_max=max(cyc) if cyc else 0,
        gen_mean=float(outd[[i for i in range(n) if lev[i] != 'vermin']].mean()) if anim else 0, gini_deg=gini(deg),
        gen_cv=float(np.std(outd) / np.mean(outd)) if outd.mean() else 0, vul_cv=float(np.std(ind) / np.mean(ind)) if ind.mean() else 0,
        hubs=[(nodes[i]['nm'], nodes[i]['level'], int(outd[i]), int(ind[i])) for i in hubs],
        tl_ok=tlok, tl_by=tl_by, tl_max=float(tl.max()) if n else 0, rho_tl_mass=rho,
        vermin=len(verm), vermin_to_apex=len(vreach), path_mean=float(np.mean(plen)) if plen else None, spine=len(spine), animals_mid=sum(1 for i in range(n) if lev[i] in ('prey', 'predator')),
        lvl={f'{x}>{y}': c for (x, y), c in sorted(lvl.items())}, inverted=inverted, same_level=same,
        mr_median=float(np.median(mr)) if mr else None, mr_n=len(mr), prey_heavier=heavier,
        tl=dict((nodes[i]['t'], float(tl[i])) for i in range(n)), cat_of=dict((nodes[i]['t'], cat[i]) for i in range(n)))

R = {}
for fk, F in G.items():
    R[fk] = {}
    for L, seasons in F['layers'].items():
        R[fk][L] = []
        for row in seasons:
            nc, no = row['cur']['nodes'], row['old']['nodes']
            m = {'NR': metrics(nc, row['cur']['edges']['NR']), 'L1': metrics(nc, row['cur']['edges']['L1']), 'L0': metrics(no, row['old']['edges']['L0'])}
            # edge-level differences on shared nodes
            shared = {x['t'] for x in nc} & {x['t'] for x in no}
            NR = {(a, b) for a, b, *_ in row['cur']['edges']['NR']}; L1 = {(a, b) for a, b in row['cur']['edges']['L1']}
            L0 = {(a, b) for a, b in row['old']['edges']['L0'] if a in shared and b in shared}
            NRs = {(a, b) for a, b in NR if a in shared and b in shared}
            m['diff'] = dict(nr_only_vs_L1=len(NR - L1), l1_only_vs_NR=len(L1 - NR), both_L1=len(NR & L1),
                             nr_only_vs_L0=len(NRs - L0), l0_only_vs_NR=len(L0 - NRs), both_L0=len(NRs & L0),
                             nodes_cur=len(nc), nodes_old=len(no), nodes_shared=len(shared),
                             only_cur=sorted({x['nm'] for x in nc if x['t'] not in shared}), only_old=sorted({x['nm'] for x in no if x['t'] not in shared}))
            # rule attribution of NR edges
            m['nr_rules'] = dict(collections.Counter('+'.join(sorted(r)) for *_, r in row['cur']['edges']['NR']))
            R[fk][L].append(m)
json.dump(R, open(SP + '/graph/metrics.json', 'w'))
print('ok', sum(len(v) for f in R.values() for v in f.values()), 'graphs x 3 networks')
