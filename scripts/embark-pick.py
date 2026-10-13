#!/usr/bin/env python3
"""Shortlist embark sites by region type from `cx-lifecycle.sh survey` TSVs (seasonal-wildlife test forts, 12 Oct 2026).

A candidate is a 2x2 block of region tiles: the 4x4 embark square placed over the block's shared corner covers all four
(cx-lifecycle.sh embark ... off-x=14 off-y=14 from the top-left tile). The fort's biomes are its embark tiles (user 12 Oct:
"a fortress has part or all of its map in a savage biome if the embark tiles include some or all savage biome tiles"), so
the block needs an ocean or lake tile (the water on the map), 2+ land biomes, and no site. Each candidate is scored, per
region type, by the share of its land tiles of that type; small savage = some land tiles savage, some calm.

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
    for (x, y) in T:
        block = [T.get((x + dx, y + dy)) for dx in (0, 1) for dy in (0, 1)]
        if any(b is None or b['site'] for b in block):
            continue
        land = [b for b in block if kind(b) == 'land']
        water = [b for b in block if kind(b) != 'land']
        if not water or len(land) < 2:
            continue
        out.append(dict(world=world, x=x, y=y, water=kind(water[0]), wbiome=water[0]['biome'],
                        biomes=sorted({n['biome'] for n in land}), cats=collections.Counter(cat(n) for n in land),
                        nsav=sum(1 for n in land if n['sav'] >= SAVAGE_AT), nland=len(land), own=land[0], verified=verified,
                        contrast=max(n['sav'] for n in land) >= 80 and all(n['sav'] <= 50 for n in land if n['sav'] < SAVAGE_AT),
                        tiles=' '.join(f"{b['biome'][:12]}({b['sav']}/{b['evil']})" for b in block)))
    return out


def share(c, pred):
    return sum(v for k, v in c['cats'].items() if pred(k)) / sum(c['cats'].values())


GOALS = {
    'good': lambda c: share(c, lambda k: k == ('good', 'calm')),
    'evil': lambda c: share(c, lambda k: k == ('evil', 'calm')),
    'untamed-wilds': lambda c: share(c, lambda k: k == ('neutral', 'savage')),
    'joyous-wilds': lambda c: share(c, lambda k: k == ('good', 'savage')),
    'terrifying': lambda c: share(c, lambda k: k == ('evil', 'savage')),
    # one clearly savage land tile among clearly calm ones: savage 80+, calm 50 or less (a tile at 65-66 tests nothing)
    'small-savage': lambda c: (1.0 if c['nsav'] == 1 else 0.6 if 0 < c['nsav'] < c['nland'] else 0.0)
                              * (1.0 if c['contrast'] else 0.3),
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
            print(f"  {fn(c):.2f}  {c['world']} block {c['x']},{c['y']} (+1,+1; embark off 14,14) {c['water']} | {len(c['biomes'])} land biomes: "
                  f"{', '.join(c['biomes'])} | {cs} | tiles sav/evil: {c['tiles']}"
                  + ('' if c['verified'] else ' | alignment unverified (tile evilness)'))


if __name__ == '__main__':
    main()
