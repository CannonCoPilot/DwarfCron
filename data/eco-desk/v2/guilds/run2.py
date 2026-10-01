#!/usr/bin/env python3
"""Sweep roster2.build over embarks x layers x 4 seasons x 20 seeds per config; write runs/<cfg>.jsonl and tables2.md.
usage: run2.py            (all configs)
"""
import json, itertools, statistics as st
from dataclasses import replace
from collections import Counter, defaultdict
from pathlib import Path
from roster2 import *            # noqa
from roster2 import components
from species2 import tier

OUT = Path(__file__).resolve().parent
(OUT / 'runs').mkdir(exist_ok=True)
SEEDS = range(1, 21)
M = Cfg()
CONFIGS = {
    'main': M,                                                                 # neutral (non-savage) embarks
    'savage': replace(M, savage=True, label='savage'),                         # giants, animal people, extinct allowed
    'savage_noextinct': replace(M, savage=True, extinct=False, label='savage_noextinct'),
    'v1like': replace(M, savage_filter=False, extinct=False, label='v1like'),  # SAVAGE species everywhere, no extinct (v1 universe)
    'nosizepref': replace(M, size_pref=False, label='nosizepref'),
    'uniform': replace(M, weight='uniform', label='uniform'),
    'cav_ceiling': replace(M, cav_mode='ceiling', label='cav_ceiling'),
    'nobiz': replace(M, biz_pref=False, label='nobiz'),
    'sentient_attack': replace(M, savage=True, sentient_attack=True, label='sentient_attack'),
    'no_humanoid_rule': replace(M, savage=True, humanoid_rule=False, label='no_humanoid_rule'),
    'pack_pref3': replace(M, pack_pref=3.0, label='pack_pref3'),
}
# v2.1 (user rulings 30 Sep 2026 + CAL): uniform pick x3 group hunters, no hard 5x cap, ladder finalize, animal-person
# attackers, sentient targets for AL/AW only, BENIGN cleared on armed predators, pelagic apex sub-slot.
V21 = replace(M, v21=True, weight='uniform', pack_pref=3.0, pack_pred_only=True, r_max=float('inf'), ladder21=True,
              ap_attack=True, humanoid_guilds=('AL', 'AW'), clear_benign_preds=True, pelagic_apex=True, mass_floor=0.2,
              label='v21')
CONFIGS.update({
    'v21': V21,
    'v21_savage': replace(V21, savage=True, label='v21_savage'),
    'v21_keepbenign': replace(V21, clear_benign_preds=False, label='v21_keepbenign'),   # the BENIGN fix isolated
    'main_clearbenign': replace(M, clear_benign_preds=True, label='main_clearbenign'),  # the BENIGN fix alone on v2 main
    'v21_nofloor': replace(V21, mass_floor=0.0, label='v21_nofloor'),          # no size bound at all (CAL reading taken literally)
    'v21_floor05': replace(V21, mass_floor=0.05, label='v21_floor05'),         # the lowest measured kill: 7 wolves on elephants, 5.6%
    'v21_floor30': replace(V21, mass_floor=0.3, label='v21_floor30'),
    'v21_savage_floor05': replace(V21, savage=True, mass_floor=0.05, label='v21_savage_floor05'),
})

# v2.2 (user rulings 30 Sep evening): pack-mass floor 5% (+ sneak bonus at 25%), cavern fliers fed (bats on vermin, cave
# raptors on bats and cave land prey), flying apex + flying animal people, fishers, GOBBLE-based vermin links, vegetation
# link for predator-less herbivores, GOOD/EVIL species on matching regions, ladder22.
V22 = replace(V21, v22=True, mass_floor=0.05, veg=True, ladder21=True, label='v22')
CONFIGS.update({
    'v22': V22,
    'v22_savage': replace(V22, savage=True, label='v22_savage'),
    'v22_good': replace(V22, align='good', label='v22_good'),
    'v22_evil': replace(V22, align='evil', label='v22_evil'),
    'v22_evil_savage': replace(V22, align='evil', savage=True, label='v22_evil_savage'),
    'v22_floor20': replace(V22, mass_floor=0.2, label='v22_floor20'),
    'v22_noveg': replace(V22, veg=False, label='v22_noveg'),
    'v22_civ': replace(V22, civ_attack=True, label='v22_civ'),          # cavern civ races as attackers (not a ruling yet)
})

def jobs():
    for e in EMBARKS:
        for l in SURFACE:
            for s in SEASONS:
                for sd in SEEDS: yield e, l, s, sd
    for l in UNDER:
        for s in SEASONS:
            for sd in SEEDS: yield 'UNDER', l, s, sd

def run(label):
    cfg = CONFIGS[label]
    rows = []
    for e, l, s, sd in jobs():
        r = build(e, l, s, sd, cfg)
        r['components'] = components(r)
        if cfg.v22: r['components_veg'] = components(r, veg=True)
        rows.append(r)
    with open(OUT / 'runs' / (label + '.jsonl'), 'w') as f:
        for r in rows:
            rr = dict(r); rr['stop_n'] = len(rr.pop('stop')); f.write(json.dumps(rr) + '\n')
    return rows

# ------------------------------------------------------------------ metrics
def pct(a, b): return '%d%%' % round(100 * a / b) if b else '-'
def mean(x): x = list(x); return st.mean(x) if x else float('nan')
def f1(x): return '%.1f' % x if x == x else '-'
def md(head, rows):
    out = ['| ' + ' | '.join(map(str, head)) + ' |', '|' + '---|' * len(head)]
    out += ['| ' + ' | '.join(map(str, r)) + ' |' for r in rows]
    return '\n'.join(out)

def derive(r):
    SP = species_for(r['cfg'])
    E = r['edges']; ids = r['roster']
    d = {}
    d['n'] = len(ids); d['e'] = len(E)
    d['df'] = sum(1 for e in E if e[4] == 'df'); d['dfq'] = sum(1 for e in E if e[4] == 'df?')
    d['stock'] = sum(1 for e in E if e[4] == 'stock'); d['no'] = sum(1 for e in E if e[4] == 'no')
    d['unit'] = sum(1 for e in E if e[3] == 'unit')
    pairs = {(a, b) for a, b, *_ in E}
    d['mutual'] = any((b, a) in pairs for a, b in pairs)
    act = {(a, b) for a, b, w, k, ac in E if ac in ('df', 'df?')}
    packp = [p for p in ids if not SP[p].vermin and tier(SP[p]) >= 2 and SP[p].cmax > 1 and any(a == p for a, b in act)]
    herd = [x for x in ids if not SP[x].vermin and tier(SP[x]) == 1 and SP[x].cmax > 1 and any(b == x for a, b in act)]
    d['pack'] = bool(packp); d['herd'] = bool(herd); d['packherd'] = bool(packp) and bool(herd)
    # v1 step-8 definition: any pack predator (cluster max > 1) with any prey edge, and any herd prey with any eater
    v1p = any(not SP[p].vermin and tier(SP[p]) >= 2 and SP[p].cmax > 1 and any(a == p for a, b in pairs) for p in ids)
    v1h = any(not SP[x].vermin and tier(SP[x]) == 1 and SP[x].cmax > 1 and any(b == x for a, b in pairs) for x in ids)
    d['step8v1'] = v1p and v1h
    d['apex'] = any(r['slot'][s] == 'APX' for s in ids)
    d['apex_df'] = any(r['slot'][a] == 'APX' for a, b in act)
    d['sentient_n'] = sum(1 for s in ids if SP[s].sentient)
    d['giant_n'] = sum(1 for s in ids if SP[s].giant)
    d['extinct_n'] = sum(1 for s in ids if SP[s].source == 'extinct')
    d['sent_uneaten'] = [s for s in ids if SP[s].sentient and not any(b == s for a, b, *_ in E)]
    d['pred_share'] = sum(v for k, v in r['share'].items() if tier(SP[k]) >= 2)
    return d

def layer_rows(R, embarks=None):
    SP = species_for(R[0]['cfg']) if R else species_for('main')
    rows = []
    for L in LAYERS:
        X = [r for r in R if r['layer'] == L and (embarks is None or r['embark'] in embarks or r['embark'] == 'UNDER')]
        if not X: continue
        N = [r for r in X if r['roster']]
        D = [derive(r) for r in N]
        alle = sum(d['e'] for d in D) or 1
        allu = sum(d['unit'] for d in D) or 1
        rows.append([L, len(X), len(X) - len(N), f1(mean(d['n'] for d in D)), f1(mean(d['e'] for d in D)),
                     pct(sum(1 for r in N if r['isolated_pre']), len(N)), pct(sum(1 for r in N if r['isolated'] or r['components'] > 1), len(N)),
                     pct(sum(d['df'] for d in D), alle), pct(sum(d['dfq'] for d in D), alle), pct(sum(d['stock'] for d in D), alle),
                     pct(sum(d['no'] for d in D), alle), pct(sum(d['df'] + d['dfq'] for d in D), allu),
                     pct(sum(1 for d in D if d['apex']), len(N)), pct(sum(1 for d in D if d['pack']), len(N)),
                     pct(sum(1 for d in D if d['herd']), len(N)), pct(sum(1 for d in D if d['packherd']), len(N)),
                     pct(sum(1 for d in D if d['step8v1']), len(N)),
                     pct(sum(1 for d in D if d['mutual']), len(N)), pct(sum(1 for r in N if r['season_break']), len(N)),
                     f1(mean(len(r['season_break']) for r in N)), pct(sum(1 for d in D if d['sent_uneaten']), len(N)),
                     '%.2f' % mean(d['pred_share'] for d in D) if D else '-',
                     pct(sum(1 for r in N if any(r['slot'][s] == 'APX' and SP[s].cb for s in r['roster'])), len(N)),
                     f1(mean(len(r['benign_clear']) for r in N)), f1(mean(r['stop_n'] if 'stop_n' in r else len(r['stop']) for r in N)),
                     f1(mean(len(r['arm']) for r in N))])
    head = ['layer', 'rosters', 'empty', 'mean size', 'mean edges', 'isolated before repair', 'isolated / split after',
            'edges DF-actable (measured reach)', 'edges written, reach untested', 'edges = vermin stock', 'edges DF will not act (BENIGN)',
            'unit edges actable (incl. untested)', 'apex present', 'pack hunts', 'herd hunted', 'pack AND herd', 'v1 step 8 (any edge)', 'mutual predation',
            'seasonal break (pre-guard)', 'NO_<season> writes / roster', 'sentient uneaten', 'predator share of arrivals',
            'apex is a curious beast', 'BENIGN clears / roster', 'stop list (qty 0) / roster', 'armed attackers / roster']
    return md(head, rows)

def slotfill_rows(R, embarks=None):
    SP = species_for(R[0]['cfg']) if R else species_for('main')
    SL = ['APX', 'ML', 'MW', 'RP', 'GZ', 'PL', 'SH', 'FC', 'FF', 'PE', 'LB', 'WB', 'TH', 'SN', 'VG', 'VC', 'VF', 'VB', 'VI']
    rows = []
    for L in LAYERS:
        N = [r for r in R if r['layer'] == L and r['roster'] and (embarks is None or r['embark'] in embarks or r['embark'] == 'UNDER')]
        if not N: continue
        row = [L]
        for k in SL:
            has_slot = [r for r in N if k in r['slots']]
            if not has_slot: row.append(''); continue
            if k == 'TH':
                got = sum(1 for r in has_slot if any(SP[s].cb or SP[s].scav for s in r['roster']))
                avail = sum(1 for r in has_slot if True)
            else:
                got = sum(1 for r in has_slot if any(r['slot'][s] == k for s in r['roster']))
                avail = sum(1 for r in has_slot if r['pool_slots'].get(k, 0) > 0)
            mn = mean(sum(1 for s in r['roster'] if r['slot'][s] == k) for r in has_slot) if k != 'TH' else float('nan')
            row.append('%s/%s%s' % (pct(got, len(has_slot)), pct(avail, len(has_slot)), (' (%.1f)' % mn) if mn == mn else ''))
        rows.append(row)
    return md(['layer'] + SL, rows)

def sensitivity(R):
    g = defaultdict(list)
    for r in R: g[(r['embark'], r['layer'], r['season'])].append(frozenset(r['roster']))
    out = defaultdict(list)
    for (e, l, s), sets in g.items():
        sets = [x for x in sets if x]
        if len(sets) < 2: continue
        jac = [len(a & c) / len(a | c) for a, c in itertools.combinations(sets, 2)]
        out[l].append((mean(jac), len(set(sets)), len(set().union(*sets))))
    return md(['layer', 'cells', 'mean pairwise Jaccard (20 seeds)', 'distinct rosters / 20', 'species ever used'],
              [[L, len(out[L]), '%.2f' % mean(x[0] for x in out[L]), f1(mean(x[1] for x in out[L])), f1(mean(x[2] for x in out[L]))]
               for L in LAYERS if out.get(L)])

def absurd(cfg):
    U = [s for s in SP.values() if s.source == 'vanilla']
    n = 0
    for p in U:
        if p.vermin: continue
        for x in U:
            if not x.vermin and x.mass >= 3 * p.mass:
                e = edge(p, x, cfg)
                if e and e[1] == 'unit': n += 1
    return n

def summary_row(label, R, embarks, layers):
    N = [r for r in R if r['roster'] and r['layer'] in layers and (r['embark'] in embarks or r['embark'] == 'UNDER')]
    D = [derive(r) for r in N]
    alle = sum(d['e'] for d in D) or 1
    return [label, len(N), f1(mean(d['n'] for d in D)), pct(sum(1 for r in N if r['isolated'] or r['components'] > 1), len(N)),
            pct(sum(1 for d in D if d['step8v1']), len(N)), pct(sum(1 for d in D if d['packherd']), len(N)), pct(sum(d['df'] for d in D), alle),
            pct(sum(d['df'] + d['dfq'] for d in D), alle), pct(sum(d['df'] + d['dfq'] + d['stock'] for d in D), alle),
            pct(sum(1 for d in D if d['mutual']), len(N)),
            pct(sum(d['sentient_n'] for d in D), sum(d['n'] for d in D)), pct(sum(d['giant_n'] for d in D), sum(d['n'] for d in D)),
            pct(sum(d['extinct_n'] for d in D), sum(d['n'] for d in D)),
            pct(sum(1 for r in N if r['season_break']), len(N))]

if __name__ == '__main__':
    import sys
    labels = sys.argv[1:] or list(CONFIGS)
    ALL = {}
    for lb in labels:
        ALL[lb] = run(lb); print(lb, len(ALL[lb]))
    P = []
    SURF = set(SURFACE); UND = set(UNDER)
    P.append('# roster2 sweep tables (generated by run2.py; do not edit)\n')
    P.append('Jobs per config: %d embarks x %d surface layers x 4 seasons x 20 seeds + %d underground layers x 4 x 20 = %d builds.\n'
             % (len(EMBARKS), len(SURFACE), len(UNDER), len(ALL[labels[0]])))
    P.append('## Config comparison (v1 embarks only: %s)\n' % ', '.join(V1_EMBARKS))
    head = ['config', 'rosters', 'mean size', 'isolated / split', 'v1 step 8 (pack + herd, any edge)', 'pack AND herd on actable edges', 'edges DF-actable (measured)', '+ untested reach',
            '+ vermin stock (tool-actable)', 'mutual predation', 'sentient share of nodes', 'giant share', 'extinct share', 'seasonal break pre-guard']
    for part, lays in (('surface', SURF), ('caverns + deep', UND)):
        P.append('### ' + part + '\n')
        P.append(md(head, [summary_row(lb, ALL[lb], set(V1_EMBARKS), lays) for lb in labels]) + '\n')
    P.append('Allowed unit pairs with prey >= 3x eater mass over the vanilla universe (v1 metric): ' +
             ', '.join('%s %d' % (lb, absurd(CONFIGS[lb])) for lb in labels if lb in ('main', 'nosizepref', 'v1like')) + '\n')
    for lb in labels:
        P.append('## %s: per layer (all %d embarks)\n' % (lb, len(EMBARKS)))
        P.append(layer_rows(ALL[lb]) + '\n')
        P.append('### %s: slot fill per guild (rosters with >=1 of the guild / pools with a candidate; (mean count))\n' % lb)
        P.append(slotfill_rows(ALL[lb]) + '\n')
        if lb in ('main', 'savage'):
            P.append('### %s: seed sensitivity\n' % lb)
            P.append(sensitivity(ALL[lb]) + '\n')
    name = ('tables22.md' if any(lb.startswith('v22') for lb in labels) else
            'tables21.md' if any(lb.startswith('v21') or lb.endswith('clearbenign') for lb in labels) else 'tables2.md')
    (OUT / name).write_text('\n'.join(P))
