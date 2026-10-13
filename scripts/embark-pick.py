#!/usr/bin/env python3
"""Shortlist embark sites by region type from `cx-lifecycle.sh survey` TSVs (seasonal-wildlife test forts, 12 Oct 2026).

A candidate is a land tile with an ocean or lake tile beside it (the 4x4 is placed across that seam so the water is on the
map: memory embark-site-traps), neither carrying a site. Its biome set is the 3x3 neighbourhood of both tiles, which is
what DF draws a fort's wildlife from (memory df-region-draw-tiles). Each candidate is scored, per region type, by the
share of its land tiles of that type; it must cover 2+ land biomes.

Alignment: the world region's good/evil flags (survey columns rgood/revil, added 12 Oct) when the survey has them -- that
is what DF and the tool place GOOD/EVIL wildlife by. Older surveys only have tile evilness, used as a proxy (<= 32 good,
>= 66 evil) and marked 'unverified'. Savage: tile savagery >= 66.

usage: embark-pick.py NAME=survey.tsv [NAME=survey.tsv ...] [--top N] [--only CATEGORY]
"""
import argparse
import collections
import csv

SAVAGE_AT, EVIL_AT, GOOD_AT = 66, 66, 32


def load(f):
    T = {}
    for r in csv.DictReader(open(f), delimiter='\t'):
        T[(int(r['x']), int(r['y']))] = {k: (int(v) if v.lstrip('-').isdigit() else v) for k, v in r.items()}
    return T


def kind(r):
    b = r['biome']
    return 'ocean' if b.startswith('OCEAN') else ('lake' if b.startswith('LAKE') or r['lake'] else 'land')


def align(r):
    if 'rgood' in r:
        return 'good' if r['rgood'] else ('evil' if r['revil'] else 'neutral')
    return 'good' if r['evil'] <= GOOD_AT else ('evil' if r['evil'] >= EVIL_AT else 'neutral')


def cat(r):
    return align(r), ('savage' if r['sav'] >= SAVAGE_AT else 'calm')


def candidates(T, world):
    out = []
    verified = any('rgood' in t for t in T.values())
    for (x, y), t in T.items():
        if kind(t) != 'land' or t['site']:
            continue
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            w = T.get((x + dx, y + dy))
            if not w or kind(w) == 'land' or w['site']:
                continue
            nb = {}
            for cx, cy in ((x, y), (x + dx, y + dy)):
                for ix in (-1, 0, 1):
                    for iy in (-1, 0, 1):
                        n = T.get((cx + ix, cy + iy))
                        if n:
                            nb[(cx + ix, cy + iy)] = n
            land = [n for n in nb.values() if kind(n) == 'land']
            if not land:
                continue
            out.append(dict(world=world, x=x, y=y, wx=x + dx, wy=y + dy, water=kind(w), wbiome=w['biome'],
                            biomes=sorted({n['biome'] for n in land}), cats=collections.Counter(cat(n) for n in land),
                            nsav=sum(1 for n in land if n['sav'] >= SAVAGE_AT), nland=len(land), own=t, verified=verified))
    return out


def share(c, pred):
    return sum(v for k, v in c['cats'].items() if pred(k)) / sum(c['cats'].values())


GOALS = {
    'good': lambda c: share(c, lambda k: k == ('good', 'calm')),
    'evil': lambda c: share(c, lambda k: k == ('evil', 'calm')),
    'untamed-wilds': lambda c: share(c, lambda k: k == ('neutral', 'savage')),
    'joyous-wilds': lambda c: share(c, lambda k: k == ('good', 'savage')),
    'terrifying': lambda c: share(c, lambda k: k == ('evil', 'savage')),
    'small-savage': lambda c: (1.0 if 1 <= c['nsav'] <= 2 and c['nland'] >= 6 else 0.0) * share(c, lambda k: k[1] == 'calm'),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('surveys', nargs='+')
    ap.add_argument('--top', type=int, default=3)
    ap.add_argument('--only')
    a = ap.parse_args()
    allc = []
    for s in a.surveys:
        name, _, f = s.partition('=')
        allc += candidates(load(f), name)
    for g, fn in GOALS.items():
        if a.only and g != a.only:
            continue
        rows = sorted((c for c in allc if len(c['biomes']) >= 2), key=lambda c: (-fn(c), -len(c['biomes']), c['water'] != 'lake'))
        print(f'## {g}')
        for c in rows[:a.top]:
            t = c['own']
            cs = ' '.join(f'{p[0]}/{p[1]}:{n}' for p, n in sorted(c['cats'].items()))
            print(f"  {fn(c):.2f}  {c['world']} {c['x']},{c['y']} {t['biome']} sav{t['sav']} ev{t['evil']} -> {c['water']} {c['wx']},{c['wy']} "
                  f"{c['wbiome']} | {len(c['biomes'])} land biomes: {', '.join(c['biomes'])} | {cs}"
                  + ('' if c['verified'] else ' | alignment unverified (tile evilness)'))


if __name__ == '__main__':
    main()
