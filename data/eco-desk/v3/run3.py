#!/usr/bin/env python3
"""Sweep roster3 over the desk's 11 embarks x 20 seeds x 4 seasons; print the scorecard against the user's targets
(7 Oct: per layer and season ~8-10 interacting non-vermin + a few vermin, 10-12 in all; casts change each season).
usage: run3.py [label] [cfg overrides as k=v ...]"""
import collections, statistics as st, sys
from dataclasses import replace
from roster3 import Cfg3, build_year, components, R2
from species2 import tier

SEEDS = range(1, 21)


def main():
    cfg = Cfg3()
    for kv in sys.argv[2:]:
        k, v = kv.split('=')
        if k in ('savage', 'align'):
            cfg = replace(cfg, base=replace(cfg.base, **{k: v == '1' if k == 'savage' else v}))
            continue
        cfg = replace(cfg, **{k: type(getattr(cfg, k))(v) if not isinstance(getattr(cfg, k), bool) else v == '1'})
    agg = collections.defaultdict(list)
    excl = collections.defaultdict(collections.Counter)
    unf = collections.defaultdict(collections.Counter)
    seeds = collections.defaultdict(collections.Counter)
    for ek in R2.EMBARKS:
        for sd in SEEDS:
            yr = build_year(ek, sd, cfg)
            for layer in ('land', 'water', 'cavern', 'deep'):
                prev = None
                for s in ('SPRING', 'SUMMER', 'AUTUMN', 'WINTER'):
                    c, P = yr[s][layer]
                    if not P.species:
                        continue
                    a = agg[layer]
                    nv, v = len(c.members), len(c.vermin)
                    preds = [m for m in c.members if tier(P.species[m]) >= 2]
                    fed = [m for m in preds if any((m, j) in P.edges for j in c.all)]
                    hunted = [m for m in c.members if tier(P.species[m]) == 1 and any((p, m) in P.edges for p in c.members)]
                    prey = [m for m in c.members if tier(P.species[m]) == 1]
                    a.append(dict(nv=nv, v=v, tot=nv + v, parts=components(c), preds=len(preds), fed=len(fed), prey=len(prey),
                                  hunted=len(hunted), edges=len(c.edges), giant_seed=P.species[c.seed].giant if c.seed else False,
                                  carry=(len(set(c.all) & prev) / max(1, len(c.all))) if prev is not None else None,
                                  ok=nv >= {'land': 8, 'water': 6, 'cavern': 8, 'deep': 1}[layer]))
                    prev = set(c.all)
                    for i, why in c.excluded.items():
                        excl[layer][(i, why)] += 1
                    for n, why in c.unfilled.items():
                        unf[layer][(n, why.split(': ', 1)[1] if ': ' in why else why)] += 1
                    seeds[layer][','.join(c.seed_why)] += 1
    print('# roster3 %s' % sys.argv[1] if len(sys.argv) > 1 else '# roster3')
    print('| layer | casts | non-vermin mean (min-max) | vermin | total | casts >= target | one web | predators with prey in cast | prey with a predator in cast | edges | carried from last season | giant seeds |')
    print('|---|---|---|---|---|---|---|---|---|---|---|---|')
    for layer, a in agg.items():
        f = lambda k: st.mean(x[k] for x in a)
        cr = [x['carry'] for x in a if x['carry'] is not None]
        print('| %s | %d | %.1f (%d-%d) | %.1f | %.1f | %.0f%% | %.0f%% | %.0f%% | %.0f%% | %.1f | %.0f%% | %.0f%% |' % (
            layer, len(a), f('nv'), min(x['nv'] for x in a), max(x['nv'] for x in a), f('v'), f('tot'), 100 * f('ok'),
            100 * st.mean(x['parts'] == 1 for x in a), 100 * sum(x['fed'] for x in a) / max(1, sum(x['preds'] for x in a)),
            100 * sum(x['hunted'] for x in a) / max(1, sum(x['prey'] for x in a)), f('edges'), 100 * st.mean(cr) if cr else 0,
            100 * f('giant_seed')))
    for layer in agg:
        print('\n## %s: unfilled slots (count of casts)' % layer)
        for (n, why), k in unf[layer].most_common(8):
            print('- %s: %s (%d)' % (n, why, k))
        print('seeds by reason:', dict(seeds[layer].most_common()))
        print('never castable (species: reason, casts):', ', '.join('%s: %s %d' % (i, w, k) for (i, w), k in excl[layer].most_common(14)))


if __name__ == '__main__':
    main()
