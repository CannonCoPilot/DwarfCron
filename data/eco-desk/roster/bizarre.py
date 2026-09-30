#!/usr/bin/env python3
"""BIZARRE score per subterranean creature (raw facts only) -> bizarre.tsv, bizarre-cut.json, bizarre-summary.txt."""
import json, sys
from pathlib import Path
from collections import Counter
HERE = Path(__file__).resolve().parent
D = json.load(open(HERE.parent / 'census.json'))
F = json.load(open(HERE / 'features.json'))
FX = {}
for i, line in enumerate(open('/Users/nathanielcannon/Claude/Projects/DwarfCron/data/fixtures/species-model.tsv')):
    p = line.rstrip('\n').split('\t')
    if i == 0: hdr = p; continue
    FX[p[0]] = dict(zip(hdr, p))
def has(r, t): return r.get(t) not in (0, '0', None, '')

ODD_FLAGS = ['NOBREATHE', 'NOT_LIVING', 'NO_EAT', 'NO_DRINK', 'NO_SLEEP', 'NOPAIN', 'NOEMOTION', 'NOTHOUGHT', 'NOFEAR', 'FIREIMMUNE']
COLS = ['not_MUNDANE', 'no_MAMMAL', 'odd_legs', 'no_head', 'multi_head', 'no_eyes', 'syndrome_or_extract', 'odd_flags', 'web', 'size_extreme']
WEIGHTS = {'not_MUNDANE': 2, 'no_MAMMAL': 1, 'odd_legs': 1, 'no_head': 2, 'multi_head': 2, 'no_eyes': 1,
           'syndrome_or_extract': 1, 'odd_flags': 1, 'web': 1, 'size_extreme': 1}

def components(r):
    f = F[r['id']]
    c = {}
    c['not_MUNDANE'] = int(not has(r, 'MUNDANE'))
    c['no_MAMMAL'] = int('MAMMAL' not in r['creature_classes'].split(','))
    c['odd_legs'] = int(f['stance'] not in (2, 4))
    c['no_head'] = int(f['heads'] == 0)
    c['multi_head'] = int(f['heads'] > 1)
    c['no_eyes'] = int(f['sight'] == 0)
    c['syndrome_or_extract'] = int(bool(f['SYNDROME'] or f['EXTRACT'] or f['SPECIALATTACK_INJECT_EXTRACT'] or f['ce']))
    c['odd_flags'] = min(3, sum(f[k] for k in ODD_FLAGS))       # each flag +1, capped at 3
    c['web'] = int(bool(f['WEBBER'] or f['THICKWEB']))
    c['size_extreme'] = int(r['adult_body_size'] >= 1_000_000)
    return c

def rank(xs):
    s = sorted(range(len(xs)), key=lambda i: xs[i]); rk = [0] * len(xs); i = 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and xs[s[j + 1]] == xs[s[i]]: j += 1
        for k in range(i, j + 1): rk[s[k]] = (i + j) / 2
        i = j + 1
    return rk
def spearman(a, b):
    ra, rb = rank(a), rank(b); n = len(a); ma = sum(ra) / n; mb = sum(rb) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb)); va = sum((x - ma) ** 2 for x in ra); vb = sum((y - mb) ** 2 for y in rb)
    return cov / (va * vb) ** 0.5

def main():
    sub = [r for r in D if r['source'] == 'vanilla' and r['biomes'] and any(b.startswith('SUBTERRANEAN') for b in r['biomes'].split(','))]
    rows = []
    for r in sub:
        c = components(r)
        score = sum(WEIGHTS[k] * v for k, v in c.items())
        dep = str(r['UNDERGROUND_DEPTH']) if has(r, 'UNDERGROUND_DEPTH') else '0:0'
        lo, hi = (int(x) for x in dep.split(':'))
        fx = FX.get(r['id'], {})
        rows.append(dict(id=r['id'], eco=fx.get('eco', '?'), kind=r['kind'] or '-', vermin=r['is_vermin'], biomes=r['biomes'],
                         size=r['adult_body_size'], role=fx.get('role', '?'), LP=int(has(r, 'LARGE_PREDATOR')), BENIGN=int(has(r, 'BENIGN')),
                         sentient=int(r['kind'] == 'animal_person' or has(r, 'CAN_SPEAK') or has(r, 'CAN_LEARN')),
                         body='+'.join(F[r['id']]['body_templates'][:3]), stance=F[r['id']]['stance'], heads=F[r['id']]['heads'],
                         **c, score=score, dmin=lo, dmax=hi))
    # cut: tertiles of the natural cavern (chasm/water) pool, i.e. the species the roster can draw
    cav = [x for x in rows if x['eco'] == 'natural' and ('SUBTERRANEAN_CHASM' in x['biomes'] or 'SUBTERRANEAN_WATER' in x['biomes'])]
    sc = sorted(x['score'] for x in cav)
    q1, q2 = sc[len(sc) // 3], sc[2 * len(sc) // 3]
    if q2 == q1: q2 = q1 + 1
    for x in rows:
        x['band'] = 1 if x['score'] <= q1 else 2 if x['score'] <= q2 else 3
    cols = ['id', 'eco', 'kind', 'vermin', 'role', 'LP', 'BENIGN', 'sentient', 'size', 'biomes', 'body', 'stance', 'heads'] + COLS + ['band', 'score', 'dmin', 'dmax']
    rows.sort(key=lambda x: (-x['score'], x['id']))
    with open(HERE / 'bizarre.tsv', 'w') as f:
        f.write('\t'.join(cols) + '\n')
        for x in rows: f.write('\t'.join(str(x[c]) for c in cols) + '\n')
    json.dump({'q1': q1, 'q2': q2, 'weights': WEIGHTS}, open(HERE / 'bizarre-cut.json', 'w'))
    # summary
    out = []
    P = lambda *a: out.append(' '.join(str(x) for x in a))
    P('subterranean creatures', len(rows), '; natural cavern (chasm/water) pool', len(cav), '; cut q1<=%d band1, <=%d band2, else band3' % (q1, q2))
    mid = [(x['dmin'] + x['dmax']) / 2 for x in cav]
    P('Spearman(score, depth min) = %.2f; (score, depth max) = %.2f; (score, depth mid) = %.2f  [natural cavern pool, n=%d]' % (
        spearman([x['score'] for x in cav], [x['dmin'] for x in cav]), spearman([x['score'] for x in cav], [x['dmax'] for x in cav]),
        spearman([x['score'] for x in cav], mid), len(cav)))
    allc = [x for x in rows if 'SUBTERRANEAN_CHASM' in x['biomes'] or 'SUBTERRANEAN_WATER' in x['biomes']]
    P('Spearman(score, depth min) all classes n=%d: %.2f' % (len(allc), spearman([x['score'] for x in allc], [x['dmin'] for x in allc])))
    P('mean score by depth min (natural cavern pool):', {d: round(sum(x['score'] for x in cav if x['dmin'] == d) / max(1, sum(1 for x in cav if x['dmin'] == d)), 2) for d in (1, 2, 3)},
      'n', dict(Counter(x['dmin'] for x in cav)))
    P('mean score by depth min (all classes):', {d: round(sum(x['score'] for x in allc if x['dmin'] == d) / max(1, sum(1 for x in allc if x['dmin'] == d)), 2) for d in (1, 2, 3)})
    P('\ncandidate counts per cavern layer (natural cavern pool; nonvermin/vermin):')
    for rule in ('depth', 'score', 'depth+ceiling'):
        cells = []
        for L in (1, 2, 3):
            if rule == 'depth': m = [x for x in cav if x['dmin'] <= L <= x['dmax']]
            elif rule == 'score': m = [x for x in cav if x['band'] == L]
            else: m = [x for x in cav if x['dmin'] <= L <= x['dmax'] and x['band'] <= L]
            cells.append('cav%d %d (%d/%d; LP %d)' % (L, len(m), sum(1 for x in m if not x['vermin']), sum(1 for x in m if x['vermin']), sum(x['LP'] for x in m)))
        P('  %-14s' % rule, ' | '.join(cells))
    P('\nband x depth-min cross tab (natural cavern pool):')
    for b in (1, 2, 3):
        P('  band', b, {d: sum(1 for x in cav if x['band'] == b and x['dmin'] == d) for d in (1, 2, 3)})
    (HERE / 'bizarre-summary.txt').write_text('\n'.join(out) + '\n')
    print('\n'.join(out))

if __name__ == '__main__':
    main()
