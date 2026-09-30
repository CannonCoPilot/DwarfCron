#!/usr/bin/env python3
"""Tables from runs/<label>.jsonl -> tables.md (+ examples.md). usage: analyze.py [label ...]"""
import sys, json, itertools
from pathlib import Path
from collections import Counter, defaultdict
from roster import *   # noqa
from run import CONFIGS

LAYERS = ['land', 'flying', 'water', 'cav1', 'cav2', 'cav3', 'deep']

def load(label): return [json.loads(l) for l in open(HERE / 'runs' / (label + '.jsonl'))]
def pct(n, d): return '-' if not d else '%d%%' % round(100 * n / d)
def mean(xs): xs = list(xs); return sum(xs) / len(xs) if xs else float('nan')
def f1(x): return '-' if x != x else '%.1f' % x

def md(head, rows):
    o = ['| ' + ' | '.join(head) + ' |', '|' + '---|' * len(head)]
    o += ['| ' + ' | '.join(str(c) for c in r) + ' |' for r in rows]
    return '\n'.join(o)

def nonempty(R): return [r for r in R if r['roster']]

# ---------------------------------------------------------------- per-roster derived metrics
def derive(r, cfg):
    E = [tuple(e) for e in r['edges_final']]
    ids = r['roster']; cls = r['classes']
    outd = Counter(e[0] for e in E); ind = Counter(e[1] for e in E)
    eaters = [i for i in ids if is_eater(SPECIES[i], cfg)]
    preyish = [i for i in ids if not is_eater(SPECIES[i], cfg)]
    d = {}
    d['pred_no_prey'] = [i for i in eaters if outd[i] == 0 and not SPECIES[i].vermin]
    d['vbird_no_insect'] = [i for i in eaters if outd[i] == 0 and SPECIES[i].vermin]
    unitE = [e for e in E if not SPECIES[e[0]].vermin and not SPECIES[e[1]].vermin]
    feasE = [e for e in unitE if not SPECIES[e[0]].benign]
    def s8(EE):
        pk = any(e[0] == p for p in ids for e in EE if cls[p] in PRED_CLASSES and SPECIES[p].cmax > 1)
        hd = any(e[1] == x for x in ids for e in EE if cls[x] in PREY_CLASSES and SPECIES[x].cmax > 1)
        return pk and hd
    d['step8_unit'] = s8(unitE); d['step8_feas'] = s8(feasE)
    d['vermin_edges'] = sum(1 for e in E if SPECIES[e[1]].vermin)
    d['contested'] = sum(1 for e in feasE if not SPECIES[e[1]].benign)
    d['feas'] = len(feasE)
    Es = set(E)
    d['recip'] = sum(1 for (a, b) in Es if (b, a) in Es) // 2
    preds = [i for i in ids if cls[i] in PRED_CLASSES]
    d['ap_pred_share'] = (sum(1 for i in preds if SPECIES[i].sentient), len(preds))
    w = r['freq']; tot = sum(w.values())
    d['pred_weight_share'] = sum(v for k, v in w.items() if cls[k] in PRED_CLASSES) / tot if tot else 0
    d['prey_no_pred'] = [i for i in preyish if ind[i] == 0]
    deg = Counter(); [deg.update(e) for e in E]
    sd = r.get('seed_sp')
    d['seed_share'] = (deg[sd] / len(E)) if E and sd else 0.0
    d['seed_maxdeg'] = bool(E) and sd is not None and deg[sd] == max(deg.values())
    # seasonal breaks (surface): predator present in another season whose roster prey are all absent then
    br = []
    if r['layer'] in SURFACE_LAYERS:
        for p in eaters:
            prey = [x for (a, x) in E if a == p]
            if not prey: continue
            for s2 in SPECIES[p].seasons:
                if s2 == r['season']: continue
                if not any(s2 in SPECIES[x].seasons for x in prey): br.append((p, s2)); break
    d['season_break'] = br
    # contradictions
    d['B_starve'] = []   # small prey uneaten while a roster small predator would eat it if rule B were lifted
    liftB = replace(cfg, B_small_extra=1)
    for x in ids:
        if cls[x] == 'small_prey' and ind[x] == 0:
            if any(cls[p] == 'small_pred' and eats(SPECIES[p], SPECIES[x], liftB) for p in ids): d['B_starve'].append(x)
    d['sentient_uneaten'] = [x for x in ids if SPECIES[x].sentient and ind[x] == 0]
    d['bigprey_uneaten'] = [x for x in ids if cls[x] == 'giant_large_prey' and ind[x] == 0]
    return d

def rule_blocks(R, cfg):
    """Reasons eats() refuses among all ordered roster pairs whose first member is a predator (non-vermin)."""
    c = Counter()
    for r in R:
        for p, x in itertools.permutations(r['roster'], 2):
            sp = SPECIES[p]
            if sp.vermin or r['classes'][p] not in PRED_CLASSES: continue
            ok, why = eats(sp, SPECIES[x], cfg, why=True)
            c[why] += 1
    return c

def sensitivity(R):
    g = defaultdict(list)
    for r in R: g[(r['bkey'], r['layer'], r['season'])].append(frozenset(r['roster']))
    out = defaultdict(list)
    for (b, l, s), sets in g.items():
        sets = [x for x in sets if x]
        if len(sets) < 2: continue
        jac = [len(a & c) / len(a | c) for a, c in itertools.combinations(sets, 2)]
        out[l].append((mean(jac), len(set(sets)), len(set().union(*sets))))
    return out

def layer_table(R, cfg):
    rows = []
    for L in LAYERS:
        X = [r for r in R if r['layer'] == L]
        N = nonempty(X)
        if not X: continue
        der = [derive(r, cfg) for r in N]
        term = Counter(r['terminated'] for r in X)
        et = mean(r['edges_tree'] for r in N); ea = mean(r['edges_all'] for r in N)
        iso = sum(1 for r in N if r['isolated_pre6'])
        if not N: continue
        s6 = Counter(v for r in N for v in r['step6'].values())
        unit = sum(r['edges_unit'] for r in N); fe = sum(r['edges_df_feasible'] for r in N); alle = sum(r['edges_all'] for r in N)
        rows.append([L, len(X), len(X) - len(N), f1(mean(len(r['roster']) for r in N)),
                     '%d/%d/%d' % (min(len(r['roster']) for r in N), round(mean(len(r['roster']) for r in N)), max(len(r['roster']) for r in N)) if N else '-',
                     pct(term['caps_strict'], len(X)), pct(term['caps_lenient'], len(X)), pct(term['no_progress'], len(X)),
                     f1(et), f1(ea), f1(ea / et if et else float('nan')),
                     pct(iso, len(N)), '%d/%d/%d/%d' % (s6['bridged_within_caps'], s6['bridge_needs_cap_break'], s6['impossible_under_A-F'] + s6['no_main_component'], s6['no_relation_in_pool']),
                     pct(sum(1 for r in N if r['components'] > 1), len(N)),
                     pct(sum(1 for r in N if r['step8']), len(N)), pct(sum(1 for r in N if r['step8_pack']), len(N)), pct(sum(1 for r in N if r['step8_herd']), len(N)),
                     pct(sum(1 for d in der if d['seed_share'] >= 0.5), len(N)), pct(sum(1 for d in der if d['seed_maxdeg']), len(N)),
                     pct(sum(1 for d in der if d['pred_no_prey']), len(N)), pct(sum(1 for d in der if d['prey_no_pred']), len(N)),
                     pct(sum(1 for d in der if d['season_break']), len(N)) if L in SURFACE_LAYERS else 'n/a',
                     pct(fe, alle), pct(unit, alle), pct(sum(d['vermin_edges'] for d in der), alle),
                     pct(sum(d['contested'] for d in der), sum(d['feas'] for d in der)),
                     pct(sum(1 for r in N if all(v == 0 for v in r['unfilled_pool_has'].values())), len(N)),
                     pct(sum(1 for d in der if d['step8_unit']), len(N)), pct(sum(1 for d in der if d['step8_feas']), len(N)),
                     pct(sum(1 for d in der if d['vbird_no_insect']), len(N)),
                     f1(max(r['edges_all'] / r['edges_tree'] for r in N if r['edges_tree']) if any(r['edges_tree'] for r in N) else float('nan')),
                     '%.2f' % mean(d['pred_weight_share'] for d in der)])
    head = ['layer', 'rosters', 'empty', 'mean size', 'size min/mean/max', 'term: caps strict', 'caps lenient', 'no-progress guard',
            'edges steps2-4', 'edges step5', 'x', 'isolated pre-6', 'step6 bridged/needs cap/impossible/no rel', 'components>1 after 6',
            'step8 pass', 'pack ok', 'herd ok', 'seed >=50% edges', 'seed = max degree', 'has pred w/o prey', 'has prey w/o pred',
            'seasonal break', 'edges DF can act on', 'edges unit-unit', 'edges onto vermin', 'DF-actable edges with fight-back prey',
            'caps filled wherever pool allowed', 'step8 pass (unit edges)', 'step8 pass (DF-actable edges)', 'vermin bird w/o insect',
            'max edge x', 'predator share of step-7 weight']
    return md(head, rows)

def capfill_table(R, cfg):
    rows = []
    for L in LAYERS:
        X = nonempty([r for r in R if r['layer'] == L])
        if not X: continue
        row = [L]
        for k in CLASSES:
            avail = sum(1 for r in X if r['pool_by_class'].get(k, 0) > 0)
            filled = sum(1 for r in X if any(c == k for c in r['classes'].values()))
            full = sum(1 for r in X if sum(1 for c in r['classes'].values() if c == k) >= CAPS[k])
            row.append('%s / %s' % (pct(filled, len(X)), pct(avail, len(X))) if avail else '0 / 0')
        rows.append(row)
    return md(['layer'] + ['%s (cap %d)' % (k, CAPS[k]) for k in CLASSES], rows)

def pool_table(cfg):
    rows = []
    for b in list(EMBARKS) + ['UNDER']:
        for L in (SURFACE_LAYERS if b != 'UNDER' else UNDER_LAYERS):
            P = pool(b, L, 'SPRING', cfg); W = pool(b, L, 'WINTER', cfg)
            c = Counter(tclass(s, cfg) for s in P)
            rows.append([b, L, len(P), len(W), sum(1 for s in P if s.kind == 'giant'), sum(1 for s in P if s.kind == 'animal_person'),
                         sum(1 for s in P if s.hv and not s.vermin)] + [c.get(k, 0) for k in CLASSES])
    return md(['embark', 'layer', 'pool spring', 'winter', 'giants', 'animal people', 'HV non-vermin'] + CLASSES, rows)

def compare_table(labels):
    rows = []
    for lb in labels:
        cfg = CONFIGS[lb]; R = load(lb)
        for grp, Ls in (('surface', SURFACE_LAYERS), ('caverns+deep', UNDER_LAYERS)):
            X = [r for r in R if r['layer'] in Ls]; N = nonempty(X)
            der = [derive(r, cfg) for r in N]
            alle = sum(r['edges_all'] for r in N)
            rows.append([lb, grp, f1(mean(len(r['roster']) for r in N)), pct(sum(1 for r in X if r['terminated'] == 'no_progress'), len(X)),
                         f1(mean(r['edges_all'] for r in N) / max(1e-9, mean(r['edges_tree'] for r in N))),
                         pct(sum(1 for r in N if r['isolated_pre6']), len(N)),
                         pct(sum(1 for r in N if r['isolated_final']), len(N)),
                         pct(sum(1 for r in N if r['step8']), len(N)),
                         pct(sum(1 for d in der if d['pred_no_prey']), len(N)), pct(sum(1 for d in der if d['prey_no_pred']), len(N)),
                         pct(sum(1 for d in der if d['B_starve']), len(N)), pct(sum(1 for d in der if d['sentient_uneaten']), len(N)),
                         pct(sum(1 for d in der if d['bigprey_uneaten']), len(N)),
                         pct(sum(r['edges_df_feasible'] for r in N), alle),
                         pct(sum(1 for d in der if d['step8_feas']), len(N)),
                         pct(sum(1 for d in der if d['recip']), len(N)),
                         pct(sum(d['ap_pred_share'][0] for d in der), sum(d['ap_pred_share'][1] for d in der)),
                         f1(mean(sum(1 for i in r['roster'] if SPECIES[i].kind == 'animal_person') for r in N)),
                         f1(mean(sum(1 for i in r['roster'] if SPECIES[i].kind == 'giant') for r in N))])
    return md(['config', 'layers', 'mean size', 'no-progress guard', 'edge x (step5/steps2-4)', 'isolated pre-6', 'isolated after 6',
               'step8 pass', 'pred w/o prey', 'prey w/o pred', 'B-starve', 'sentient uneaten', 'big prey uneaten', 'edges DF can act on', 'step8 on DF-actable edges', 'rosters with mutual predation', 'sentient share of predator nodes',
               'AP per roster', 'giants per roster'], rows)

def main(labels):
    out = []
    P = out.append
    B = CONFIGS['baseline']; R = load('baseline')
    P('# Roster prototype tables (generated by analyze.py)\n')
    P('## Pools (baseline class scheme; spring unless noted)\n'); P(pool_table(B)); P('')
    P('## Cap fill, baseline: filled at least once / pool had the class at all (per non-empty roster)\n'); P(capfill_table(R, B)); P('')
    P('## Per-layer outcomes, baseline\n'); P(layer_table(R, B)); P('')
    rb = rule_blocks(nonempty(R), B)
    P('## Why eats() refuses (baseline; ordered roster pairs whose first member is a predator)\n')
    P(md(['reason', 'pairs', 'share'], [[k, v, pct(v, sum(rb.values()))] for k, v in rb.most_common()])); P('')
    se = sensitivity(R)
    P('## Seed sensitivity, baseline (per embark x layer x season, 20 seeds)\n')
    P(md(['layer', 'cells', 'mean pairwise Jaccard', 'distinct rosters / 20 (mean)', 'species ever used (mean)'],
         [[L, len(se[L]), '%.2f' % mean(x[0] for x in se[L]), f1(mean(x[1] for x in se[L])), f1(mean(x[2] for x in se[L]))] for L in LAYERS if se.get(L)]))
    P('')
    # seed kind / step 2
    P('## Step 1-2, baseline\n')
    rows = []
    for L in LAYERS:
        X = nonempty([r for r in R if r['layer'] == L])
        if not X: continue
        sk = Counter(r['seed_kind'] for r in X); sc = Counter(r['seed_class'] for r in X)
        rows.append([L, pct(sk['hv'], len(X)), pct(sk['no_hv_fallback'] + sk['vermin_only'], len(X)), pct(sum(1 for r in X if not r['step2_ok']), len(X)),
                     pct(sum(1 for r in X if SPECIES[r['seed_sp']].kind == 'giant'), len(X)),
                     ', '.join('%s %d' % (k, v) for k, v in sc.most_common(4))])
    P(md(['layer', 'HV seed', 'no HV in pool', 'step 2 empty list', 'seed is a giant', 'seed classes (top 4)'], rows)); P('')
    P('## Config comparison (one factor at a time from baseline, then the fix sets)\n'); P(compare_table(labels)); P('')
    for lb in ('FIX3', 'FIX3_ratio'):
        if lb in labels:
            P('## Per-layer outcomes, %s\n' % lb); P(layer_table(load(lb), CONFIGS[lb])); P('')
            P('## Cap fill, %s\n' % lb); P(capfill_table(load(lb), CONFIGS[lb])); P('')
            rb = rule_blocks(nonempty(load(lb)), CONFIGS[lb])
            P('## Why eats() refuses, %s\n' % lb)
            P(md(['reason', 'pairs', 'share'], [[k, v, pct(v, sum(rb.values()))] for k, v in rb.most_common()])); P('')
    (HERE / 'tables.md').write_text('\n'.join(out) + '\n')
    print('\n'.join(out))

if __name__ == '__main__':
    main(sys.argv[1:] or list(CONFIGS))
