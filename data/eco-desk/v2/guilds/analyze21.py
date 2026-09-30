#!/usr/bin/env python3
"""v2.1 item analysis over runs/<cfg>.jsonl (main, savage, v21, v21_savage, main_clearbenign). Prints the numbers in results21.md."""
import json
from collections import Counter, defaultdict
from roster2 import SP, SP21, species_for, SURFACE, EMBARKS
from run2 import CONFIGS
from roster2 import pool, relations
def load(lb): return [json.loads(l) for l in open('runs/%s.jsonl' % lb)]
R = {lb: load(lb) for lb in ('main', 'savage', 'v21', 'v21_savage', 'main_clearbenign')}
def pct(a, b): return '%d%%' % round(100 * a / b) if b else '-'

print('== 2. animal-person attackers')
for lb in ('savage', 'v21_savage'):
    S = species_for(lb); X = [r for r in R[lb] if r['roster']]
    ape = [e for r in X for e in r['edges'] if S[e[0]].kind == 'animal_person']
    ape_act = [e for e in ape if e[4] in ('df', 'df?')]
    ros = sum(1 for r in X if any(S[e[0]].kind == 'animal_person' for e in r['edges']))
    civ = [e for r in X for e in r['edges'] if S[e[0]].sentient and S[e[0]].kind != 'animal_person']
    sent_t = Counter(S[e[0]].guild for r in X for e in r['edges'] if S[e[1]].sentient and e[3] == 'unit')
    print(lb, 'AP attacker edges', len(ape), 'actable', len(ape_act), 'rosters with one', pct(ros, len(X)), 'civ-race attacker edges', len(civ),
          'sentient-target unit edges by attacker guild', dict(sent_t))
    print('   top AP attackers', Counter(e[0] for e in ape).most_common(8))

print('== 3. BENIGN clears, ORCA')
bb = sorted(s.id for s in SP.values() if s.apex and not s.apex_why.startswith('native') and s.benign)
print(len(bb), bb)
for lb in ('main', 'v21', 'savage', 'v21_savage'):
    O = [r for r in R[lb] if r['layer'] == 'ocean' and r['roster']]
    inpool = Counter(); onr = Counter(); clr = Counter()
    for r in O:
        cfg = CONFIGS[lb]
        P = {s.id for s in pool(r['embark'], 'ocean', r['season'], cfg)}
        for sid in ('ORCA', 'SPERM_WHALE', 'SHARK_GREAT_WHITE', 'GIANT_ORCA', 'GIANT_SPERM_WHALE', 'SEA_SERPENT'):
            if sid in P: inpool[sid] += 1
            if sid in r['roster']: onr[sid] += 1
            if sid in r['benign_clear']: clr[sid] += 1
    print(lb, 'ocean rosters', len(O), {k: '%d/%d pool, cleared %d' % (onr[k], inpool[k], clr[k]) for k in inpool})
    emb = Counter(r['embark'] for r in O if 'ORCA' in r['roster'])
    print('   ORCA on roster by embark', dict(emb))

print('== 4. surface unit edges not actable (main) and the BENIGN fix')
for lb in ('main', 'main_clearbenign', 'v21'):
    S = species_for(lb)
    X = [r for r in R[lb] if r['layer'] in SURFACE and r['roster']]
    U = [e for r in X for e in r['edges'] if e[3] == 'unit']
    no = [e for e in U if e[4] == 'no']; q = [e for e in U if e[4] == 'df?']; ok = [e for e in U if e[4] == 'df']
    print(lb, 'unit edges', len(U), 'df', pct(len(ok), len(U)), 'df?', pct(len(q), len(U)), 'no', pct(len(no), len(U)))
    if no:
        print('   BENIGN attackers by guild', dict(Counter(S[e[0]].guild for e in no)))
        print('   by species', Counter(e[0] for e in no).most_common(14))
    def pat(e):
        p, x = S[e[0]], S[e[1]]
        if p.flier: return 'flier attacker -> ' + ('flier' if x.flier else 'aquatic' if x.aquatic else 'land')
        if p.aquatic: return 'aquatic -> %s (shore/waterbird in water)' % x.guild
        if x.flier: return 'land/amphibious -> flier (%s)' % x.guild
        return 'other'
    print('   untested reach', dict(Counter(pat(e) for e in q)))
    print('   untested by layer', dict(Counter(r['layer'] for r in X for e in r['edges'] if e[3] == 'unit' and e[4] == 'df?')))

print('== 5. ocean pelagic')
for lb in ('main', 'v21', 'savage', 'v21_savage'):
    O = [r for r in R[lb] if r['layer'] == 'ocean' and r['roster']]
    pe = sum(1 for r in O if any(r['slot'][s] == 'PE' for s in r['roster']))
    pe_eaten = sum(1 for r in O if any(r['slot'][e[1]] == 'PE' for e in r['edges'] if e[3] == 'unit'))
    ape = Counter(s for r in O for s in r['roster'] if r['slot'][s] == 'APE')
    apx = Counter(s for r in O for s in r['roster'] if r['slot'][s] == 'APX')
    pp = sum(1 for r in O if r['pool_slots'].get('PE', 0) > 0)
    print(lb, 'ocean rosters', len(O), 'PE present', pct(pe, len(O)), 'PE eaten (unit edge)', pct(pe_eaten, len(O)), 'pools with PE', pct(pp, len(O)))
    print('   APE picks', dict(ape)); print('   APX picks', apx.most_common(6))
    by = defaultdict(lambda: [0, 0])
    for r in O:
        by[r['embark']][0] += 1; by[r['embark']][1] += any(r['slot'][s] == 'PE' for s in r['roster'])
    print('   PE by embark', {k: pct(v[1], v[0]) for k, v in by.items()})
for sid in ('GIANT_OCTOPUS', 'GIGANTIC SQUID'):
    print(sid, 'v2', SP[sid].guild, SP[sid].apex, 'v21', SP21[sid].guild, SP21[sid].apex, SP21[sid].mass)
    for lb in ('savage', 'v21_savage'):
        X = [r for r in R[lb] if sid in r['roster']]
        print('  ', lb, 'on', len(X), 'rosters, slot', Counter(r['slot'][sid] for r in X), 'attacker edges', sum(1 for r in X for e in r['edges'] if e[0] == sid))

print('== 6. large prey inclusion')
BIG = ['ELEPHANT', 'RHINOCEROS', 'HIPPO', 'GIRAFFE', 'WATER_BUFFALO', 'MOOSE', 'GIANT_ELEPHANT', 'MOOSE, GIANT', 'GIANT_ELEPHANT_SEAL', 'ELEPHANT_SEAL', 'WALRUS', 'SHARK_WHALE', 'SHARK_BASKING']
for lb in ('main', 'v21', 'savage', 'v21_savage'):
    cfg = CONFIGS[lb]; out = {}
    for sid in BIG:
        inp = onr = eaten = 0
        for r in R[lb]:
            if not r['roster']: continue
            P = {s.id for s in pool(r['embark'], r['layer'], r['season'], cfg)} if r['embark'] != 'UNDER' else set()
            if sid not in P: continue
            inp += 1; onr += sid in r['roster']
            eaten += any(e[1] == sid and e[3] == 'unit' for e in r['edges'])
        if inp: out[sid] = '%d/%d (%s), eaten %d' % (onr, inp, pct(onr, inp), eaten)
    print(lb, out)
# link guard drops: pool non-vermin species with no edge at all in the pool's relation set (never pickable)
for lb in ('main', 'v21', 'savage', 'v21_savage'):
    cfg = CONFIGS[lb]; S = species_for(lb)
    never = Counter(); cells = 0; npred = Counter(); nprey = Counter()
    seen = set()
    for r in R[lb]:
        k = (r['embark'], r['layer'], r['season'])
        if k in seen or r['embark'] == 'UNDER' and False: continue
        seen.add(k)
        P = pool(r['embark'], r['layer'], r['season'], cfg); E, nb = relations(r['embark'], r['layer'], r['season'], cfg)
        cells += 1
        for s in P:
            if s.vermin or nb[s.id]: continue
            if s.guild in ('AL', 'AW', 'ML', 'MW', 'RP') or s.apex: npred[s.id] += 1
            else: nprey[s.id] += 1
    print(lb, 'pool cells', cells, 'unlinkable predators', sum(npred.values()), npred.most_common(8))
    print('   unlinkable prey', sum(nprey.values()), nprey.most_common(10))

print('== 7. giant packs')
GP = ['GIANT_HYENA', 'GIANT_DINGO', 'GIANT_COYOTE', 'GIANT_JACKAL', 'GIANT_LION', 'GIANT_WOLF', 'GIANT_ALLIGATOR', 'GIANT_CROCODILE_SALTWATER', 'BADGER, GIANT', 'GIANT_ORCA']
for sid in GP: s = SP[sid]; print(sid, '%d:%d' % (s.cmin, s.cmax), s.mass, 'benign' if s.benign else '', s.guild)
TG = {'ELEPHANT', 'RHINOCEROS', 'GIANT_ELEPHANT', 'HIPPO', 'GIRAFFE'}
for lb in ('savage', 'v21_savage'):
    c = Counter((e[0], e[1]) for r in R[lb] for e in r['edges'] if e[1] in TG and e[3] == 'unit')
    ga = Counter(e[0] for r in R[lb] for e in r['edges'] if e[1] in TG and e[3] == 'unit')
    print(lb, 'edges onto big prey', sum(c.values()), 'by attacker', ga.most_common(14))
    print('   giant-pack edges', {k: v for k, v in c.items() if k[0] in GP})
