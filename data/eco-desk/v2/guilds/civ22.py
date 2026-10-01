#!/usr/bin/env python3
"""v2.2 civ ruling check: singletons, civ edges per cavern depth, mutual predation, apex-on-apex (python3 civ22.py > civ22.out)."""
import json
from collections import Counter, defaultdict
from roster2 import species_for, pool, relations, herbivore, veg_supports, etier
from run2 import CONFIGS
from species2 import tier
LBS = ('v22', 'v22_savage', 'v22_good', 'v22_evil', 'v22_evil_savage', 'v22_civ', 'v22_nociv')
S = species_for('v22')
print('civ races:', sorted(k for k, s in S.items() if getattr(s, 'civ', False)))
for lb in LBS:
    cfg = CONFIGS[lb]
    R = [json.loads(l) for l in open('runs/%s.jsonl' % lb)]
    pools, ok, seen = defaultdict(set), defaultdict(set), set()
    for r in R:
        k = (r['embark'], r['layer'], r['season'])
        if k in seen: continue
        seen.add(k)
        P = pool(*k, cfg); E, nb = relations(*k, cfg); key = (r['embark'], r['season'])
        for z in P:
            pools[key].add(z.id)
            if nb[z.id] or (cfg.veg and herbivore(z) and veg_supports(r['embark'], r['layer'], z)): ok[key].add(z.id)
    single = Counter(sid for key in pools for sid in pools[key] - ok[key])
    civ_out, civ_in, mutual, aoa, civ_on_roster = Counter(), Counter(), 0, 0, Counter()
    by_attacker, civciv = Counter(), Counter()
    for r in R:
        L = r['layer']; es = {(a, b) for a, b, *_ in r['edges']}
        mutual += sum(1 for a, b in es if (b, a) in es)
        for a, b, w, kind, act in r['edges']:
            if kind != 'unit': continue
            if tier(S[a]) == 3 and tier(S[b]) == 3 and not getattr(S[b], 'civ', False): aoa += 1
            if getattr(S[a], 'civ', False): civ_out[L] += 1
            if getattr(S[b], 'civ', False):
                if getattr(S[a], 'civ', False): civciv[L] += 1
                elif tier(S[a]) == 3: civ_in[L] += 1; by_attacker[a] += 1
        civ_on_roster[L] += sum(1 for s in r['roster'] if getattr(S[s], 'civ', False))
    lays = sorted(set(civ_out) | set(civ_in) | set(civ_on_roster))
    print('%-16s singletons %3d %s | mutual %d | apex-on-apex (non-civ) %d' % (lb, sum(single.values()), single.most_common(6), mutual, aoa))
    for L in lays:
        if not (civ_on_roster[L] or civ_out[L] or civ_in[L]): continue
        print('    %-6s civ on rosters %4d  civ->x unit edges %5d  cavern apex->civ unit edges %5d  civ->civ %4d' % (L, civ_on_roster[L], civ_out[L], civ_in[L], civciv[L]))
    if lb == 'v22':
        print('    non-civ apex attackers of civ races:', by_attacker.most_common(14))
        for k in ('TROLL', 'BLIND_CAVE_OGRE', 'CAVE_DRAGON', 'BLOOD_MAN'):
            print('      %s edges onto civ: %d' % (k, by_attacker[k]))
