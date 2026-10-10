#!/usr/bin/env python3
"""castsim.design_run: the 9 Oct-evening design (design.py) on six embarks -> data/castsim/design.json

Real forts (region19, X3 on v7.4): biomes from the world survey (data/t1-season/survey19.tsv: the fort's world tile and its
eight neighbours, each biome with the savagery and evil of the nearest tile that has it), water bodies from the tool's own
scan at load (water-bodies-start.txt; the brook fort's run kept none: its survey tile has a brook and no lake). DF's own
population list (the X3 state dump) is kept only to show which pool species DF had stocked. Three synthetic embarks
cover the cases the real forts do not: an arctic coast with a river, a savage lake, and murky pools only.
"""
from __future__ import annotations

import csv
import glob
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from design import Design, LAYERS, SLOTS, JUDGEMENT, EXTINCT_RULE, WEIRD, REAL_APEX  # noqa: E402
from engine import SEASONS  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'data/castsim/design.json'
SURVEY = ROOT / 'data/t1-season/survey19.tsv'
RUNS = ROOT / 'data/season-run/X3v74'
ORDER = [(0, 0), (0, -1), (1, 0), (0, 1), (-1, 0), (-1, -1), (1, -1), (1, 1), (-1, 1)]   # centre, orthogonal, diagonal
DIRS = {(0, 0): 'own tile', (0, -1): 'N', (1, 0): 'E', (0, 1): 'S', (-1, 0): 'W', (-1, -1): 'NW', (1, -1): 'NE', (1, 1): 'SE', (-1, 1): 'SW'}


def survey():
    return {(int(r['x']), int(r['y'])): r for r in csv.DictReader(SURVEY.open(), delimiter='\t')}


def real_spec(sv, x, y, water, R=None, st=None, kinds=(), **kw):
    """water: {kind: [biome, ...]} known from the map scan / survey; kinds: the freshwater kinds whose temperature zones
    are read from DF's stocked water species (infer_water)"""
    land, seen = [], set()
    for dx, dy in ORDER:
        r = sv.get((x + dx, y + dy))
        if not r: continue
        b = r['biome']
        if b in seen or b.startswith(('OCEAN', 'LAKE', 'RIVER', 'POOL')): continue
        seen.add(b); land.append({'biome': b, 'sav': int(r['sav']), 'evil': int(r['evil']), 'src': DIRS[(dx, dy)]})
    c = sv[(x, y)]
    src = {b: 'map scan / survey' for bs in water.values() for b in bs}
    if st is not None and kinds:
        inferred, unexplained = infer_water(R, st, kinds)
        for b, n in inferred:
            k = b.split('_')[0].lower()
            if b not in water.setdefault(k, []): water[k].append(b); src[b] = f"DF's stocked water species ({n})"
        kw['inferred_water'] = {'chosen': inferred, 'unexplained': unexplained}
    w = {}
    for k, bs in water.items():
        w[k] = []
        for b in bs:
            d = {'biome': b, 'sav': int(c['sav']), 'evil': int(c['evil']), 'src': src[b]}
            if k == 'ocean':   # the nearest ocean tile
                for dx, dy in ORDER:
                    r = sv.get((x + dx, y + dy))
                    if r and r['biome'] == b: d.update(sav=int(r['sav']), evil=int(r['evil']), src=DIRS[(dx, dy)] + ' (survey)'); break
            w[k].append(d)
    return dict(land=land, water=w, caverns=[1, 2, 3], extinct='UNTAMED_WILDS', **kw)


def infer_water(R, st, kinds):
    """a real fort's freshwater biomes, read from what DF stocked there: greedy cover of the stocked species whose raws
    name a lake, river or pool (water entries and land ones: DF lists pool insects and amphibians as land entries) by the
    LAKE/RIVER/POOL x TEMPERATE/TROPICAL freshwater biomes, keeping a biome only if it explains at least two species"""
    from raws import AGG
    from design import BROAD
    named = {}
    for t in st:
        if t not in R.src: continue
        out = set()
        for b in R.creature(t)['biome_tokens']:
            if b in BROAD: continue
            for x in AGG.get(b, [b]):
                if x.startswith(('LAKE', 'RIVER', 'POOL')): out.add(x)
        if out: named[t] = out
    toks = list(named)
    cands = [f'{k}_{z}_FRESHWATER' for k in kinds for z in ('TEMPERATE', 'TROPICAL')]
    left, chosen = set(toks), []
    while True:
        best = max(cands, key=lambda c: (sum(1 for t in left if c in named[t]), c))
        n = sum(1 for t in left if best in named[t])
        if n < 2: break
        chosen.append((best, n)); left -= {t for t in left if best in named[t]}; cands.remove(best)
    return chosen, sorted(left)


def stocked(dump):
    f = sorted(glob.glob(str(RUNS / dump / 'rep1/states/*.json')))[0]
    st = json.loads(Path(f).read_text())
    snap = set((st.get('snapshot') or {}).keys())
    out = {}
    for idx, tok, key, qty, ext, typ in st['pops']:
        if ':' not in key and snap and key not in snap and typ != 'ColonyInsect': continue
        layer = 'water' if key.startswith('water:') else ('cavern' if key.startswith('cave:') else 'land')
        out.setdefault(tok, set()).add(layer)
    return out, str(Path(f).relative_to(ROOT))


def examples(R):
    sv = survey()
    stL, stB = stocked('L')[0], stocked('B')[0]
    return [
        {'id': 'lake', 'name': 'Lake fort (V73_LAKE2, region19 10,42)', 'kind': 'real', 'dump': 'L',
         'water_scan': 'lake 1062 tiles, rivers 69 + 13, pool 67 (scan at load)',
         'spec': real_spec(sv, 10, 42, {'lake': ['LAKE_TROPICAL_FRESHWATER']}, R, stL, ('LAKE', 'RIVER', 'POOL'))},
        {'id': 'ocean', 'name': 'Ocean-shore fort (V73_OCEAN2, region19 63,46)', 'kind': 'real', 'dump': 'O',
         'water_scan': 'ocean 6191 tiles, salt, 4 deep (scan at load); no lake, river or pool',
         'spec': real_spec(sv, 63, 46, {'ocean': ['OCEAN_TEMPERATE']})},
        {'id': 'brook', 'name': 'Brook fort (V73_BROOK, region19 21,22)', 'kind': 'real', 'dump': 'B',
         'water_scan': 'a brook and river (survey; no lake); no map scan kept; DF stocked pool species too',
         'spec': real_spec(sv, 21, 22, {'river': ['RIVER_TEMPERATE_FRESHWATER']}, R, stB, ('RIVER', 'POOL'))},
        {'id': 'taiga', 'name': 'Taiga and tundra on an arctic coast, with a river (synthetic)', 'kind': 'synthetic',
         'water_scan': 'arctic ocean + a river, no lake (given)',
         'spec': {'land': [{'biome': 'FOREST_TAIGA', 'sav': 45, 'evil': 50, 'src': 'given'}, {'biome': 'TUNDRA', 'sav': 45, 'evil': 50, 'src': 'given'}],
                  'water': {'ocean': [{'biome': 'OCEAN_ARCTIC', 'sav': 45, 'evil': 50, 'src': 'given'}],
                            'river': [{'biome': 'RIVER_TEMPERATE_FRESHWATER', 'sav': 45, 'evil': 50, 'src': 'given'}]},
                  'caverns': [1, 2, 3], 'extinct': 'WILDERNESS'}},
        {'id': 'savage', 'name': 'Savage temperate broadleaf forest and grassland, with a lake (synthetic)', 'kind': 'synthetic',
         'water_scan': 'a lake, no river (given)',
         'spec': {'land': [{'biome': 'FOREST_TEMPERATE_BROADLEAF', 'sav': 80, 'evil': 50, 'src': 'given'}, {'biome': 'GRASSLAND_TEMPERATE', 'sav': 80, 'evil': 50, 'src': 'given'}],
                  'water': {'lake': [{'biome': 'LAKE_TEMPERATE_FRESHWATER', 'sav': 80, 'evil': 50, 'src': 'given'}]},
                  'caverns': [1, 2, 3], 'extinct': 'UNTAMED_WILDS'}},
        {'id': 'pools', 'name': 'Evil tropical savanna with murky pools only (synthetic)', 'kind': 'synthetic',
         'water_scan': 'murky pools only (given)',
         'spec': {'land': [{'biome': 'SAVANNA_TROPICAL', 'sav': 50, 'evil': 75, 'src': 'given'}, {'biome': 'GRASSLAND_TROPICAL', 'sav': 50, 'evil': 75, 'src': 'given'}],
                  'water': {'pool': [{'biome': 'POOL_TROPICAL_FRESHWATER', 'sav': 50, 'evil': 75, 'src': 'given'}]},
                  'caverns': [1, 2, 3], 'extinct': 'UNTAMED_WILDS'}},
    ]


def species_row(D, e, st):
    s = ''.join(x for i, x in enumerate(('Sp', 'Su', 'Au', 'Wi')) if not e['noSeason'][i])
    flags = [f for f, on in (('LARGE_PREDATOR', e['largePred']), ('BENIGN', e['benign']), ('giant', e['giant']), ('animal person', e['ap']),
                             ('civ race', e['civ']), ('sentient', e['sentient'] and not e['ap'] and not e['civ']), ('SAVAGE', e['savage']),
                             ('GOOD', e['good']), ('EVIL', e['evil']), ('extinct', e['extinct'])) if on]
    return {'t': e['token'], 'g': e['guild'], 'h': e['habitat'], 'r': e['role'], 'm': e['mass'], 'p': e['pet'], 'w': e['war'],
            'v': e['gameVermin'], 'vc': D.E.vclass(e) if e['gameVermin'] else '', 's': s if len(s) < 8 else 'all', 'f': flags,
            'wd': e.get('weird'), 'b': e['matched'], 'L': e['layers'], 'dep': [e['depthLo'], e['depthHi']] if e['depthLo'] else None,
            'st': sorted(st[e['token']]) if st is not None and e['token'] in st else ([] if st is not None else None)}


def main():
    D = Design()
    out = []
    for site, ex in enumerate(examples(D.R), 1):
        st, src = (stocked(ex['dump']) if ex['kind'] == 'real' else (None, None))
        r = D.run(ex['spec'], site=site)
        pool = r['pool']
        sp = {tok: species_row(D, e, st) for tok, e in pool.items()}
        lists = {f'{L}|{SEASONS[s]}': [{'t': c['e']['token'], 'sl': c['slots'], 'vc': c.get('vclass')} for c in lst] for (L, s), lst in r['lists'].items()}
        casts = {f'{L}|{SEASONS[s]}': tr for (L, s), tr in r['casts'].items()}
        df_only = sorted(t for t in (st or {}) if t not in pool)
        out.append({'id': ex['id'], 'name': ex['name'], 'kind': ex['kind'], 'spec': ex['spec'], 'water_scan': ex['water_scan'],
                    'sub': r['sub'], 'funnel': r['funnel'], 'rejected': r['rejected'], 'notes': r['notes'], 'active': r['active'],
                    'species': sp, 'lists': lists, 'casts': casts, 'dump': src,
                    'df_stocked': len(st) if st is not None else None, 'df_only': df_only})
        print(f"== {ex['name']}  sub={r['sub']}  funnel={list(r['funnel'].values())}  rejected={len(r['rejected'])}")
        for L in r['active']:
            sizes = [len(r['lists'][(L, s)]) for s in range(4)]
            uniq = sorted({m for s in range(4) for m, _ in r['casts'][(L, s)]['members']})
            dfn = sum(1 for t in r['layers'][L] if st and t in st) if st is not None else '-'
            apex = [next((m for m, sl in r['casts'][(L, s)]['members'] if sl == 'apex'), '-') for s in range(4)]
            wd = [r['casts'][(L, s)]['weird'] for s in range(4)] if L.startswith('cavern') else ''
            print(f"   {L:8} pool {len(r['layers'][L]):3} (DF stocked {dfn})  lists {sizes}  distinct cast {len(uniq):2}  apex {apex} {wd}")
    real = []
    for tok, (layer, tier, why) in REAL_APEX.items():
        c = D.R.creature(tok); i = D.E.classify(tok)
        real.append({'t': tok, 'layer': layer, 'tier': tier, 'why': why, 'm': i['mass'], 'carn': c['any']('CARNIVORE'), 'role': i['role'], 'g': i['guild']})
    meta = {'layers': LAYERS, 'slots': SLOTS, 'judgement': JUDGEMENT, 'extinct_rule': EXTINCT_RULE, 'weird': WEIRD, 'real_apex': real}
    OUT.write_text(json.dumps({'meta': meta, 'embarks': out}, default=lambda o: sorted(o) if isinstance(o, set) else str(o)))
    print('wrote', OUT, OUT.stat().st_size)


if __name__ == '__main__':
    main()
