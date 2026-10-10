#!/usr/bin/env python3
"""castsim.run: the pool -> roster -> cast pipeline on five embarks, every step recorded, for the report.

    python3 scripts/castsim/run.py            -> data/castsim/castsim.json (and a console summary)

Three real forts (the population dumps X3 on v7.4 saved, V73_LAKE2 / V73_OCEAN2 / V73_BROOK on region19) and two
synthetic embarks stocked by castsim.pools.synthetic (DF's worldgen, approximated from the raws).
"""
from __future__ import annotations

import collections
import glob
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from engine import Engine, SEASONS, CAST  # noqa: E402
from pools import from_dump, synthetic  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / 'data/season-run/X3v74'
OUT = ROOT / 'data/castsim/castsim.json'

EXAMPLES = [
    {'id': 'lake', 'name': 'Lake fort (V73_LAKE2)', 'kind': 'real', 'dump': 'L', 'ctx': {}},
    {'id': 'ocean', 'name': 'Ocean-shore fort (V73_OCEAN2)', 'kind': 'real', 'dump': 'O', 'ctx': {'ocean': True}},
    {'id': 'brook', 'name': 'Brook fort (V73_BROOK)', 'kind': 'real', 'dump': 'B', 'ctx': {}},
    {'id': 'taiga', 'name': 'Taiga and tundra on an arctic coast, with a river (synthetic)', 'kind': 'synthetic',
     'spec': {'land': ['FOREST_TAIGA', 'TUNDRA'], 'water': ['RIVER_TEMPERATE_FRESHWATER', 'OCEAN_ARCTIC'], 'caverns': True, 'savage': False},
     'ctx': {'ocean': True}, 'seed': 7},
    {'id': 'savage', 'name': 'Savage temperate broadleaf forest and grassland, with a lake (synthetic)', 'kind': 'synthetic',
     'spec': {'land': ['FOREST_TEMPERATE_BROADLEAF', 'GRASSLAND_TEMPERATE'], 'water': ['LAKE_TEMPERATE_FRESHWATER'], 'caverns': True, 'savage': True},
     'ctx': {}, 'seed': 11},
]


def biome_profile(eng, pool):
    """the land biomes the embark's land species share (a real dump names no biome; read it from who lives there)"""
    c = collections.Counter()
    n = 0
    for e in pool.values():
        if e['layer'] == 'land' and e['category'] != 'vermin' and not e['locked']:
            n += 1
            for b in e['biomes']:
                if not b.startswith(('OCEAN', 'LAKE', 'RIVER', 'POOL', 'SUBTERRANEAN')): c[b] += 1
    return [(b, k) for b, k in c.most_common(6)], n


def species_row(e):
    s = ''.join(x for i, x in enumerate(('Sp', 'Su', 'Au', 'Wi')) if not e['noSeason'][i])
    return {'key': e['key'], 'token': e['token'], 'layer': e['layer'], 'cat': e['category'], 'guild': e['guild'], 'habitat': e['habitat'],
            'role': e['role'], 'mass': e['mass'], 'lp': e['largePred'], 'benign': e['benign'], 'giant': e['giant'], 'ap': e['ap'],
            'civ': e['civ'], 'sentient': e['sentient'], 'savage': e['savage'], 'eco': e['eco'], 'locked': e['locked'],
            'ecoWhy': e['ecoWhy'], 'extinct': e['extinct'], 'fixes': e['fixes'], 'pet': e['pet'], 'war': e['war'], 'freq': e['freq'],
            'cluster': [e['cmin'], e['cmax']], 'depth': [e['depthLo'], e['depthHi']] if e['depthLo'] else None,
            'depths': sorted(d + 1 for d in e['depths']), 'seasons': s if len(s) < 8 else 'all', 'entries': e['entries'],
            'mega': e['mega'], 'night': e['night'], 'root': e['root']}


def run_one(eng, ex):
    if ex['kind'] == 'real':
        f = sorted(glob.glob(str(RUNS / ex['dump'] / 'rep1/states/*.json')))[0]
        pops, st = from_dump(eng, f)
        source = f'{Path(f).relative_to(ROOT)} (tool snapshot: {len(st.get("snapshot") or {})} land keys)'
    else:
        pops = synthetic(eng, ex['spec'], ex['seed'])
        source = 'synthetic: ' + ', '.join(ex['spec']['land'] + ex['spec']['water']) + (', caverns' if ex['spec'].get('caverns') else '') + (', savage' if ex['spec'].get('savage') else '')
    raw = collections.Counter((p['layer'], p['type']) for p in pops)
    pool, flog = eng.build_pool(pops)
    traces, roster = eng.cast_year(pool)
    roster['ladder'] = eng.ladder(pool, {k: v for k, v in _codes(traces, pool).items()}, ex.get('ctx'))
    parts = {}
    for part in ('land', 'flying', 'water', 'cavern'):
        inn, out = [], {}
        for e in pool.values():
            ok, why = eng.in_part(e, part)
            if ok: inn.append(e['token'])
            elif e['category'] != 'vermin' and (e['layer'] == ('cavern' if part == 'cavern' else ('water' if part == 'water' else 'land'))):
                out[e['token']] = why
        parts[part] = {'in': sorted(inn), 'out': out}
    bio, nland = biome_profile(eng, pool)
    return {'id': ex['id'], 'name': ex['name'], 'kind': ex['kind'], 'source': source, 'ctx': ex.get('ctx', {}),
            'entries': {f'{a}|{b}': n for (a, b), n in sorted(raw.items())}, 'n_entries': len(pops), 'filter': flog,
            'pool': [species_row(e) for e in sorted(pool.values(), key=lambda x: (x['layer'], x['category'] == 'vermin', x['key']))],
            'biomes': bio, 'n_land': nland, 'parts': parts,
            'casts': {f'{L}|{SEASONS[s]}': _jsonable(tr) for (L, s), tr in sorted(traces.items())},
            'roster': {'cast': {k: [SEASONS[s] for s in v] for k, v in roster['cast'].items()}, 'resting': sorted(roster['resting']),
                       'ladder': roster['ladder']}}


def _codes(traces, pool):
    out = {}
    for (L, s), tr in traces.items():
        for tok, slot, code in tr.get('members', []):
            key = next((k for k, e in pool.items() if e['token'] == tok and _layer_ok(e, L)), None)
            if key and key not in out:
                part = 'flying' if (L == 'land' and pool[key]['habitat'] in ('flier', 'waterbird')) else L
                out[key] = (L, part, code)
    return out


def _layer_ok(e, L):
    if L == 'cavern': return e['layer'] == 'cavern'
    if L == 'water': return e['layer'] == 'water' or (e['layer'] == 'land' and e['habitat'] in ('aquatic', 'semiaquatic'))
    return e['layer'] == 'land'


def _jsonable(x):
    if isinstance(x, dict): return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)): return [_jsonable(v) for v in x]
    if isinstance(x, set): return sorted(_jsonable(v) for v in x)
    return x


def main():
    out = []
    for ex in EXAMPLES:
        eng = Engine(align={'good': False, 'evil': False})
        r = run_one(eng, ex)
        out.append(r)
        print(f"== {r['name']}: {r['n_entries']} entries, pool {len(r['pool'])} keys; biomes {r['biomes'][:3]}")
        for k, tr in r['casts'].items():
            print(f"   {k:16} seed {tr.get('seed')!s:24} apex {tr['apex_rank']['apex']!s:22} members {len(tr['members'])} vermin {len(tr['vermin'])} unfilled {list(tr['unfilled'])}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1, default=str))
    print('wrote', OUT, OUT.stat().st_size)


if __name__ == '__main__':
    main()
