#!/usr/bin/env python3
"""v2.2 item analysis over runs/<cfg>.jsonl. Prints the numbers in results22.md (python3 analyze22.py > analyze22.out)."""
import json, math, itertools
from collections import Counter, defaultdict
from roster2 import SP, SP21, SP22, species_for, SURFACE, UNDER, LAYERS, EMBARKS, LADDER21, ladder_family, pool, relations, \
    herbivore, veg_supports, is_cave
from run2 import CONFIGS
from species2 import tier
def load(lb): return [json.loads(l) for l in open('runs/%s.jsonl' % lb)]
LBS = ('main', 'v21', 'v21_savage', 'v22', 'v22_savage', 'v22_good', 'v22_evil', 'v22_evil_savage', 'v22_floor20', 'v22_noveg',
       'v21_floor05', 'v22_civ')
R = {lb: load(lb) for lb in LBS}
def pct(a, b): return '%d%%' % round(100 * a / b) if b else '-'
V22S = ('v22', 'v22_savage', 'v22_good', 'v22_evil', 'v22_evil_savage')

print('== 1. split webs / singletons (rosters with >1 component; components_veg joins herbivores through the plants)')
for lb in ('v21', 'v21_savage') + V22S:
    for part, lays in (('surface', SURFACE), ('caverns', [l for l in UNDER if l.startswith('cav') and not l.startswith('cavw')]),
                       ('cave water', ['cavw1', 'cavw2', 'cavw3']), ('deep', ['deep'])):
        X = [r for r in R[lb] if r['layer'] in lays and r['roster']]
        sp = sum(1 for r in X if r['components'] > 1)
        spv = sum(1 for r in X if r.get('components_veg', r['components']) > 1)
        print('%-16s %-10s rosters %5d split %5s  split (veg joined) %5s' % (lb, part, len(X), pct(sp, len(X)), pct(spv, len(X))))
# which species sit outside the largest component, by guild (v22 family)
def minor(r):
    adj = defaultdict(set)
    for a, b, *_ in r['edges']: adj[a].add(b); adj[b].add(a)
    for v in r.get('veg', []): adj[v].add('~VEG'); adj['~VEG'].add(v)
    comps, seen = [], set()
    for s in r['roster']:
        if s in seen: continue
        c, st = set(), [s]
        while st:
            v = st.pop()
            if v in seen: continue
            seen.add(v); c.add(v); st.extend(adj[v] - seen)
        comps.append(c - {'~VEG'})
    comps.sort(key=len, reverse=True)
    return [x for c in comps[1:] for x in c]
for lb in V22S:
    S = species_for(lb)
    m = Counter(); ml = Counter()
    for r in R[lb]:
        for x in minor(r): m[(r['layer'], S[x].guild, x)] += 1; ml[r['layer']] += 1
    print(lb, 'species outside the main web (layer, guild, id): count', m.most_common(14))
# never placeable: pool members with no edge and no vegetation link, per config (unique pool cells)
print('== 1b. never placeable (no allowed edge in the pool and no vegetation link)')
for lb in ('v21',) + V22S:
    cfg = CONFIGS[lb]; S = species_for(lb)
    seen, never, why = set(), Counter(), {}
    for r in R[lb]:
        k = (r['embark'], r['layer'], r['season'])
        if k in seen: continue
        seen.add(k)
        P = pool(r['embark'], r['layer'], r['season'], cfg); E, nb = relations(r['embark'], r['layer'], r['season'], cfg)
        for s in P:
            if nb[s.id]: continue
            if cfg.veg and herbivore(s) and veg_supports(r['embark'], r['layer'], s): continue
            never[(r['layer'], s.guild, s.id)] += 1
            if s.vermin: why[s.id] = 'vermin with no consumer in the pool'
            elif s.sentient and not getattr(s, 'monster', False): why[s.id] = 'sentient: no allowed attacker; not an attacker'
            elif tier(s) >= 2: why[s.id] = 'predator with no prey in reach'
            elif herbivore(s): why[s.id] = 'herbivore: no predator, vegetation too thin for its mass'
            else: why[s.id] = 'prey with no predator in reach'
    tot = sum(never.values())
    byg = Counter()
    for (l, g, sid), n in never.items(): byg[why[sid]] += n
    print(lb, 'pool cells', len(seen), 'unplaceable species-cells', tot, dict(byg))
    print('   top', [(k, n, why[k[2]]) for k, n in never.most_common(12)])

print('== 2. predator share of arrivals by layer and the apex share (ladder as run = LADDER21 x within-slot mass)')
def shares(r, S, lad):
    fam = ladder_family(r['layer']); L = lad[fam]
    groups = defaultdict(list)
    for sid in r['roster']:
        s = S[sid]
        if s.vermin: continue
        k = r['slot'][sid]
        if k in ('SN', 'TH', 'SNP'): k = 'APX' if s.apex else s.guild
        groups[k].append(s)
    f = {}
    for k, mem in groups.items():
        base = L.get(k, 5)
        if k == 'PE' and r['deep_cols'] >= 3: base *= 3
        gm = math.exp(sum(math.log(max(1, m.mass)) for m in mem) / len(mem))
        for m in mem: f[m.id] = (k, 10 * base * min(4.0, max(0.25, (max(1, m.mass) / gm) ** -0.75)))
    tot = sum(v for k, v in f.values()) or 1
    pred = sum(v for sid, (k, v) in f.items() if tier(S[sid]) >= 2) / tot
    apx = sum(v for sid, (k, v) in f.items() if k in ('APX', 'APE')) / tot
    return pred, apx
def table(lb, lad):
    S = species_for(lb); out = {}
    for L in LAYERS:
        X = [r for r in R[lb] if r['layer'] == L and r['roster']]
        if not X: continue
        s = [shares(r, S, lad) for r in X]
        out[L] = (sum(a for a, b in s) / len(s), sum(b for a, b in s) / len(s))
    return out
base = table('v22', LADDER21)
print('v22 at the v2.1 ladder:', {k: '%.2f / apex %.2f' % v for k, v in base.items()})
# search: prey bases raised, predator bases held; one multiplier per family on the prey guilds
PREY = {'land': ('GZ', 'PL', 'SH'), 'flying': ('LB', 'WB'), 'water': ('FC', 'FF', 'SH', 'WB'), 'cav': ('GZ', 'PL', 'SH', 'LB', 'WB')}
best = {}
for fam, lays in (('land', ['land']), ('flying', ['flying']), ('water', ['ocean', 'lake', 'river']), ('cav', ['cav1', 'cav2', 'cav3'])):
    res = []
    for k in (1, 1.5, 2, 2.5, 3, 3.5, 4, 5):
        for apx in (2, 3, 4):
            lad = {f: dict(v) for f, v in LADDER21.items()}
            for g in PREY[fam]: lad[fam][g] = LADDER21[fam].get(g, 5) * k
            for g in ('APX', 'APE', 'AL', 'AW'):
                if g in lad[fam]: lad[fam][g] = apx
            for g in ('ML', 'MW', 'RP'):
                if g in lad[fam]: lad[fam][g] = 2 if fam != 'flying' else lad[fam][g]
            t = table('v22', lad)
            res.append((k, apx, {L: t[L] for L in lays if L in t}))
    best[fam] = res
    for k, apx, t in res:
        print('  %-6s prey x%.1f apex %d meso 2: %s' % (fam, k, apx, {L: '%.2f/%.2f' % v for L, v in t.items()}))

print('== 2b. as built: predator share / apex share of the FREQUENCY the tool writes (v21 vs v22 ladder)')
for lb in ('v21', 'v22', 'v22_savage'):
    S = species_for(lb); out = {}
    for L in LAYERS:
        X = [r for r in R[lb] if r['layer'] == L and r['roster']]
        if not X: continue
        pr = [sum(v for k, v in r['share'].items() if tier(S[k]) >= 2) for r in X]
        ap = [sum(v for k, v in r['share'].items() if r['slot'].get(k) in ('APX', 'APE')) for r in X]
        out[L] = '%.2f/%.2f' % (sum(pr) / len(pr), sum(ap) / len(ap))
    print(lb, out)

print('== 1c. never placeable in ANY layer of the embark-season (the true singletons), v22 family')
for lb in V22S + ('v22_civ',):
    cfg = CONFIGS[lb]; S = species_for(lb)
    pools = defaultdict(set); ok = defaultdict(set)
    seen = set()
    for r in R[lb]:
        k = (r['embark'], r['layer'], r['season'])
        if k in seen: continue
        seen.add(k)
        P = pool(r['embark'], r['layer'], r['season'], cfg); E, nb = relations(r['embark'], r['layer'], r['season'], cfg)
        key = (r['embark'], r['season'])
        for z in P:
            pools[key].add(z.id)
            if nb[z.id] or (cfg.veg and herbivore(z) and veg_supports(r['embark'], r['layer'], z)): ok[key].add(z.id)
    bad = Counter()
    for key in pools:
        for sid in pools[key] - ok[key]: bad[sid] += 1
    print(lb, 'species-cells never placeable in any layer', sum(bad.values()), [(k, S[k].guild, n) for k, n in bad.most_common(16)])

print('== 3. flying apex and flying animal people')
for lb in ('v21', 'v22', 'v21_savage', 'v22_savage'):
    S = species_for(lb); X = [r for r in R[lb] if r['layer'] == 'flying' and r['roster']]
    apx = Counter(s for r in X for s in r['roster'] if r['slot'][s] == 'APX')
    sn = [s for r in X for s in r['roster'] if S[s].sentient]
    sne = sum(1 for r in X for e in r['edges'] if S[e[1]].sentient and e[3] == 'unit')
    print(lb, 'flying rosters', len(X), 'apex present', pct(sum(1 for r in X if any(r['slot'][s] == 'APX' for s in r['roster'])), len(X)),
          'apex picks', apx.most_common(8), '| sentient fliers on rosters', len(sn), Counter(sn).most_common(6), 'unit edges onto them', sne)

for lb in ('v21_savage', 'v22_savage'):
    S = species_for(lb)
    for L in ('land', 'flying'):
        X = [r for r in R[lb] if r['layer'] == L and r['roster']]
        pr = Counter(s for r in X for s in r['roster'] if S[s].sentient and tier(S[s]) == 1)
        print('  %s %s: prey-guild animal people on %d of %d rosters; eaten by unit edges in %d' % (lb, L,
              sum(1 for r in X if any(S[s].sentient and tier(S[s]) == 1 for s in r['roster'])), len(X),
              sum(1 for r in X if any(S[e[1]].sentient and tier(S[e[1]]) == 1 and e[3] == 'unit' for e in r['edges']))), pr.most_common(5))
print('== 4. sneak-bonus edges (group mass >= 25% of prey) per layer, v22 and v22_savage')
for lb in ('v22', 'v22_savage'):
    out = {}
    for L in LAYERS:
        X = [r for r in R[lb] if r['layer'] == L and r['roster']]
        u = sum(1 for r in X for e in r['edges'] if e[3] == 'unit')
        sn = sum(len(r.get('sneak', [])) for r in X)
        if u: out[L] = '%d/%d (%s)' % (sn, u, pct(sn, u))
    print(lb, out)

print('== 5. vegetation link and the floor')
BIG = ['ELEPHANT', 'RHINOCEROS', 'HIPPO', 'GIRAFFE', 'WATER_BUFFALO', 'MOOSE', 'GIANT_ELEPHANT', 'MOOSE, GIANT', 'GIANT_RHINOCEROS',
       'PARACERATHERIUM', 'JURASSIC_BRACHIOSAURUS', 'UNICORN']
for lb in ('v21', 'v22_noveg', 'v22', 'v22_floor20', 'v21_savage', 'v22_savage', 'v22_good'):
    cfg = CONFIGS[lb]; out = {}
    for sid in BIG:
        inp = onr = vo = 0
        for r in R[lb]:
            if not r['roster'] or r['embark'] == 'UNDER' or r['layer'] != 'land': continue
            P = {s.id for s in pool(r['embark'], 'land', r['season'], cfg)}
            if sid not in P: continue
            inp += 1; onr += sid in r['roster']; vo += sid in r.get('veg_only', [])
        if inp: out[sid] = '%d/%d%s' % (onr, inp, (' veg-only %d' % vo) if vo else '')
    print(lb, out)
for lb in ('v22', 'v22_savage'):
    X = [r for r in R[lb] if r['layer'] in ('land', 'cav1', 'cav2', 'cav3') and r['roster']]
    print(lb, 'rosters with a vegetation-only herbivore', pct(sum(1 for r in X if r.get('veg_only')), len(X)),
          Counter(s for r in X for s in r.get('veg_only', [])).most_common(10))
# floor downsides: v22 (5%) vs v22_floor20 (20%): unit edges by prey/hunter-group mass ratio band, top added pairs
def ratio_band(p, x, cfg):
    grp = p.cmid if p.cmax > 1 else 1
    r = p.mass * grp / x.mass
    return '<5%' if r < .05 else '5-20%' if r < .2 else '20-50%' if r < .5 else '>=50%'
for lb in ('v22', 'v22_floor20', 'v22_savage'):
    S = species_for(lb); cfg = CONFIGS[lb]
    U = [(e[0], e[1]) for r in R[lb] for e in r['edges'] if e[3] == 'unit']
    b = Counter(ratio_band(S[a], S[x], cfg) for a, x in U)
    print(lb, 'unit edges', len(U), 'by group/prey mass', dict(b))
    if lb != 'v22_floor20':
        low = Counter((a, x) for a, x in U if ratio_band(S[a], S[x], cfg) == '5-20%')
        print('   5-20% pairs (absent at a 20% floor):', low.most_common(16))
        sizes = Counter('%s' % ('>=1 t' if S[x].mass >= 1e6 else '100 kg-1 t' if S[x].mass >= 1e5 else '<100 kg') for a, x in U
                        if ratio_band(S[a], S[x], cfg) == '5-20%')
        print('   their prey sizes', dict(sizes))

print('== 6. GOOD / EVIL species: pools and rosters')
S = SP22
GE = sorted([s for s in S.values() if s.good or s.evil or (s.fanciful and s.eco != 'natural')], key=lambda z: (not z.good, z.id))
for s in GE:
    cells = Counter(); onr = Counter()
    for lb in ('v22_good', 'v22_evil', 'v22_evil_savage', 'v22_savage'):
        cfg = CONFIGS[lb]
        for r in R[lb]:
            if not r['roster']: continue
            if s.id in {z.id for z in pool(r['embark'], r['layer'], r['season'], cfg)}:
                cells[(lb, r['layer'])] += 1; onr[(lb, r['layer'])] += s.id in r['roster']
    where = '; '.join('%s %s %d/%d' % (lb.replace('v22_', ''), L, onr[(lb, L)], n) for (lb, L), n in sorted(cells.items()))
    print('GE|%s|%s|%s|%d|%d:%d|%s|%s|%s|%s|%s' % (s.id, 'GOOD' if s.good else 'EVIL' if s.evil else 'FANCIFUL', s.guild + (' apex' if s.apex else ''),
          s.mass, s.cmin, s.cmax, s.biome_tokens[:70], 'yes' if s.sentient else '', 'yes' if s.savage else '', s.vclass if s.vermin else '',
          where or 'never in a pool on these embarks'))

print('== 7. fishers')
for lb in ('v21', 'v22'):
    S = species_for(lb)
    for L in ('lake', 'river', 'ocean'):
        X = [r for r in R[lb] if r['layer'] == L and r['roster']]
        ap = sum(1 for r in X if any(r['slot'][s] in ('APX', 'APE') for s in r['roster']))
        fi = Counter(s for r in X for s in r['roster'] if getattr(S[s], 'fisher', False))
        fe = sum(1 for r in X for e in r['edges'] if getattr(S[e[0]], 'fisher', False) and S[e[1]].aquatic)
        print(lb, L, 'rosters', len(X), 'apex present', pct(ap, len(X)), 'fishers on roster', dict(fi), 'fisher -> fish edges', fe)

print('== 8. vermin links: native GOBBLE, tool-written GOBBLE_VERMIN_CREATURE, vermin-on-vermin bookkeeping')
for lb in V22S:
    X = [r for r in R[lb] if r['roster']]
    c = Counter(v[2] for r in X for v in r.get('vlinks', []))
    tot = sum(c.values())
    w = [len({(a, b) for a, b, k in r.get('vlinks', []) if k == 'write'}) for r in X]
    print(lb, 'vermin links', tot, {k: '%d (%s)' % (n, pct(n, tot)) for k, n in c.items()},
          'writes per roster %.1f' % (sum(w) / len(w)))
    nat = Counter((a, b) for r in X for a, b, k in r.get('vlinks', []) if k == 'native')
    print('   native pairs', nat.most_common(8))
