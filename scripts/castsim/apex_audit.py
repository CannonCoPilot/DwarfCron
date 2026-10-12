#!/usr/bin/env python3
"""castsim.apex_audit: an exhaustive biome x region x apex audit, built programmatically from the raws (user 12 Oct).

For every DF surface biome (27 land biomes, 3 oceans, temperate and tropical lakes; rivers serve as source biomes for the
freshwater apexes) under each of six region types -- not savage or savage, x good, neutral or evil -- it runs the
design's own filters (design.py: wild, natural, BIOME, SAVAGE, GOOD/EVIL, REAL_WORLD_EXTINCT as UNTAMED_WILDS) and layer
split, and counts per season the species that can hold the layer's apex: true apexes and local ones. A biome-layer is
short when some season has fewer than two true apexes.

Candidates for a short biome-layer are generated from the whole creature list, not picked by hand:
  * promote -- every resident predator of the biome-layer (same region type) that cannot hold the apex today, scored by
    its group size against the largest resident's;
  * wire -- every species that is a true apex of the same layer in some other biome (same region type) and does not live
    in this one, scored by fauna overlap: the share of this biome-layer's residents that also live in the candidate's own
    biomes; only within the same climate band (tropical / temperate / cold; biomes without one match any).
The automatic proposal takes the resident local apexes first (lynx, coyote, wolverine...), then wired apexes with overlap
>= 0.5, best first, then other resident predators by size, then the remaining wires, until every season has two true apexes. Real-life plausibility is the reviewer's call; the scores say
how well each candidate fits DF's own fauna. -> data/castsim/apex_audit.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from design import Design  # noqa: E402
from raws import LAND, OCEANS  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'data/castsim/apex_audit.json'
LAKES = ['LAKE_TEMPERATE_FRESHWATER', 'LAKE_TROPICAL_FRESHWATER']
RIVERS = ['RIVER_TEMPERATE_FRESHWATER', 'RIVER_TROPICAL_FRESHWATER']      # source biomes for freshwater wires only
CONDITIONS = [(sav, al) for sav in ('wild', 'savage') for al in ('good', 'neutral', 'evil')]
SAV = {'wild': 50, 'savage': 80}
EVIL = {'good': 20, 'neutral': 50, 'evil': 80}
WIRE_MIN = 0.5


def band(b):
    if 'TROPICAL' in b or b == 'SWAMP_MANGROVE': return 'tropical'
    if b in ('TUNDRA', 'GLACIER', 'OCEAN_ARCTIC'): return 'cold'
    if 'TEMPERATE' in b: return 'temperate'
    if b == 'FOREST_TAIGA': return 'boreal'
    return None                                   # mountain, deserts: any band


def bands_match(a, b):
    if a is None or b is None: return True
    near = {('boreal', 'cold'), ('cold', 'boreal'), ('boreal', 'temperate'), ('temperate', 'boreal')}
    return a == b or (a, b) in near


def spec_for(b, sav, al):
    base = {'sav': SAV[sav], 'evil': EVIL[al], 'src': 'audit'}
    if b in OCEANS: return {'land': [], 'water': {'ocean': [dict(base, biome=b)]}, 'caverns': [], 'extinct': 'UNTAMED_WILDS'}, ['ocean']
    if b in LAKES: return {'land': [], 'water': {'lake': [dict(base, biome=b)]}, 'caverns': [], 'extinct': 'UNTAMED_WILDS'}, ['fresh']
    if b in RIVERS: return {'land': [], 'water': {'river': [dict(base, biome=b)]}, 'caverns': [], 'extinct': 'UNTAMED_WILDS'}, ['fresh']
    return {'land': [dict(base, biome=b)], 'water': {}, 'caverns': [], 'extinct': 'UNTAMED_WILDS'}, ['ground', 'flying']


def gsize(D, e):
    pack = D.predator(e) and not e['benign'] and e['cmax'] > 1
    return e['mass'] * ((e['cmin'] + e['cmax']) / 2 if pack else 1)


def main():
    D = Design()
    # residents[(cond, layer, biome)] = {token: entry}
    res = {}
    for cond in CONDITIONS:
        for b in LAND + OCEANS + LAKES + RIVERS:
            spec, layers = spec_for(b, *cond)
            pool, _, _ = D.pool(spec)
            fbs = D.fort_biomes(spec)
            for L in layers:
                res[(cond, L, b)] = {t: e for t, e in pool.items()
                                     if L in D.layers_of(e, spec, fbs)[0] and not e['gameVermin'] and not e.get('plant')}
    rows = []
    for cond in CONDITIONS:
        for (c2, L, b), mem in sorted(res.items()):
            if c2 != cond or b in RIVERS: continue
            tier = {t: D.apex_tier(e, L) for t, e in mem.items()}
            per = [{'true': sorted(t for t, e in mem.items() if tier[t] == 'apex' and not e['noSeason'][s]),
                    'local': sorted(t for t, e in mem.items() if tier[t] == 'local' and not e['noSeason'][s])} for s in range(4)]
            min_true = min(len(p['true']) for p in per)
            row = {'biome': b, 'layer': L, 'sav': cond[0], 'align': cond[1], 'n': len(mem), 'seasons': per, 'min_true': min_true,
                   'promote': [], 'wire': [], 'proposal': [], 'min_after': min_true}
            if min_true < 2:
                # promote: every resident predator that cannot hold the apex
                big = max((gsize(D, e) for e in mem.values()), default=1) or 1
                for t, e in mem.items():
                    if tier[t] == 'apex' or not D.predator(e) or e['sentient']: continue
                    row['promote'].append({'t': t, 'score': round(gsize(D, e) / big, 4), 'g': round(gsize(D, e)), 'local': tier[t] == 'local',
                                           'seasons': [s for s in range(4) if not e['noSeason'][s]]})
                row['promote'].sort(key=lambda x: (not x['local'], -x['score']))   # the local apexes first
                # wire: every true apex of this layer in another biome (same region type), scored by fauna overlap
                cands = {}
                for (c3, L3, b3), m3 in res.items():
                    if c3 != cond or L3 != L or b3 == b or not bands_match(band(b), band(b3)): continue
                    for t, e in m3.items():
                        if t in mem or D.apex_tier(e, L) != 'apex': continue
                        cands.setdefault(t, (e, set()))[1].add(b3)
                for t, (e, homes) in cands.items():
                    union = set()
                    for b3 in homes: union |= set(res[(cond, L, b3)])
                    ov = len(set(mem) & union) / len(mem) if mem else 0.0
                    row['wire'].append({'t': t, 'score': round(ov, 3), 'g': round(gsize(D, e)), 'homes': sorted(homes),
                                        'seasons': [s for s in range(4) if not e['noSeason'][s]]})
                row['wire'].sort(key=lambda x: (-x['score'], -x['g'], x['t']))
                # the automatic proposal
                have = [set(p['true']) for p in per]
                order = ([('promote', p) for p in row['promote'] if p['local']] + [('wire', w) for w in row['wire'] if w['score'] >= WIRE_MIN]
                         + [('promote', p) for p in row['promote'] if not p['local']]
                         + [('wire', w) for w in row['wire'] if w['score'] < WIRE_MIN])
                for kind, c in order:
                    if min(len(h) for h in have) >= 2: break
                    if not any(len(have[s]) < 2 for s in c['seasons']): continue
                    for s in c['seasons']: have[s].add(c['t'])
                    row['proposal'].append({'t': c['t'], 'kind': kind, 'score': c['score']})
                row['min_after'] = min(len(h) for h in have)
            rows.append(row)
    roll = []   # every species that is a true apex of a layer somewhere, per region type, with its biomes
    for cond in CONDITIONS:
        for L in ('ground', 'flying', 'ocean', 'fresh'):
            by = {}
            for (c2, L2, b), mem in res.items():
                if c2 != cond or L2 != L: continue
                for t, e in mem.items():
                    if D.apex_tier(e, L) == 'apex': by.setdefault(t, set()).add(b)
            for t, bs in sorted(by.items()):
                e = D.E.classify(t)
                roll.append({'sav': cond[0], 'align': cond[1], 'layer': L, 't': t, 'n': len(bs), 'biomes': sorted(bs),
                             'kind': 'giant' if e['giant'] else ('animal person' if e['ap'] else ('extinct' if e['extinct'] else
                                     ('GOOD' if e['good'] else ('EVIL' if e['evil'] else 'ordinary'))))})
    OUT.write_text(json.dumps({'conditions': CONDITIONS, 'wire_min': WIRE_MIN, 'rows': rows, 'roll': roll}, separators=(',', ':')))
    import collections
    for cond in CONDITIONS:
        c = collections.Counter((r['layer'], r['kind']) for r in roll if (r['sav'], r['align']) == cond)
        print(cond, dict(c))
    print('wild neutral ground apexes:', [(r['t'], r['n']) for r in roll if (r['sav'], r['align'], r['layer']) == ('wild', 'neutral', 'ground')])
    short = [r for r in rows if r['min_true'] < 2]
    print(len(rows), 'biome-layer-region rows;', len(short), 'short;', sum(1 for r in short if r['min_after'] < 2), 'still short after the proposal')
    for r in short:
        print(f"{r['sav']:6} {r['align']:7} {r['biome']:30} {r['layer']:6} true={r['min_true']} -> {r['min_after']} | "
              + ', '.join(f"{p['t']}({p['kind'][0]} {p['score']})" for p in r['proposal'])
              + f" | {len(r['promote'])} promote, {len(r['wire'])} wire candidates")


if __name__ == '__main__':
    main()
