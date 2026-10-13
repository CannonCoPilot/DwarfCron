"""castsim.apex_share: each species' share of the land-ground apex draw, averaged over every land biome and season of one
region type -- the rules of 12 Oct against those of 13 Oct (dingo narrowed, biome additions, apex pack x1.5; user 13 Oct)."""
from __future__ import annotations

import collections
import contextlib

import design
from apex_audit import LAND, spec_for


@contextlib.contextmanager
def rules_of_12_oct():
    keep = (design.EXTRA_BIOMES, design.EVIL_EXTRA_BIOMES, design.BIOME_LIMIT, design.GIANT_BUGS, design.APEX_PACK)
    design.EXTRA_BIOMES, design.EVIL_EXTRA_BIOMES, design.BIOME_LIMIT, design.GIANT_BUGS = {}, {}, {}, set()
    design.APEX_PACK = design.CAST_DEF['pack']
    try: yield
    finally: design.EXTRA_BIOMES, design.EVIL_EXTRA_BIOMES, design.BIOME_LIMIT, design.GIANT_BUGS, design.APEX_PACK = keep


def shares(sav='wild', al='neutral'):
    """{token: share of the first ground apex draw}, each land biome and season weighted equally; and the biomes with no
    true or local apex"""
    D = design.Design()
    tot, n, none = collections.Counter(), 0, []
    for b in LAND:
        spec, _ = spec_for(b, sav, al)
        r = D.run(spec)
        for s in range(4):
            c = r['casts'].get(('ground', s))
            if not c: continue
            n += 1
            rank = c.get('apex_rank') or []
            if not rank or c.get('apex_rule', '').startswith('largest'): none.append((b, s)); continue
            for tok, _m, _g, share, _tier, _st in rank: tot[tok] += share
    return {t: v / n for t, v in tot.items()} if n else {}, sorted({b for b, _ in none})


def compare():
    with rules_of_12_oct():
        before, nb = shares()
    after, na = shares()
    return before, after, nb, na


if __name__ == '__main__':
    b, a, nb, na = compare()
    for t in sorted(set(b) | set(a), key=lambda t: -a.get(t, 0)):
        if max(b.get(t, 0), a.get(t, 0)) >= 0.01: print(f'{t:24} {b.get(t, 0):6.1%} -> {a.get(t, 0):6.1%}')
    print('no apex before:', nb); print('no apex after:', na)
