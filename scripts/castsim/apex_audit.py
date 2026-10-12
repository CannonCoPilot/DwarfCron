#!/usr/bin/env python3
"""castsim.apex_audit: biome x apex. For every DF surface biome on a calm-to-wild, neutral region (no savage species, no
GOOD/EVIL, extinct species absent as under UNTAMED_WILDS), which species can hold the apex slot of each layer in each
season under the design's rule (design.py apex_tier): true apexes and local ones. -> data/castsim/apex_audit.json"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from design import Design  # noqa: E402
from raws import LAND, OCEANS  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'data/castsim/apex_audit.json'
SEASONS = ['Spring', 'Summer', 'Autumn', 'Winter']
LAKES = ['LAKE_TEMPERATE_FRESHWATER', 'LAKE_TROPICAL_FRESHWATER']
TEMP_WET = ['SWAMP_TEMPERATE_FRESHWATER', 'SWAMP_TEMPERATE_SALTWATER', 'MARSH_TEMPERATE_FRESHWATER', 'MARSH_TEMPERATE_SALTWATER']
# Proposed hand-wiring for the biomes with fewer than two true apexes (12 Oct, for the user's review). 'promote': a species
# that already lives there becomes a true apex there; 'wire': an existing apex species is treated as living in the biome
# (the tool's pool, not a raw edit). Real-life basis in the reason.
PROPOSALS = [
    ('WOLF', 'wire', 'ground', ['GRASSLAND_TEMPERATE', 'SAVANNA_TEMPERATE', 'MOUNTAIN'] + TEMP_WET,
     'gray wolves held the prairies and steppes, mountains and coastal marshes (red wolf) until hunted out'),
    ('BEAR_GRIZZLY', 'wire', 'ground', ['GRASSLAND_TEMPERATE', 'SAVANNA_TEMPERATE', 'MOUNTAIN'],
     'the plains grizzly ranged the Great Plains; grizzlies are the apex of high mountain meadows'),
    ('COUGAR', 'wire', 'ground', ['MOUNTAIN', 'SWAMP_TEMPERATE_FRESHWATER', 'SWAMP_TEMPERATE_SALTWATER'],
     'the mountain lion by name; the Florida panther lives in swamps'),
    ('BEAR_BLACK', 'wire', 'ground', TEMP_WET, 'black bears are common in temperate swamps and marsh edges (Great Dismal Swamp)'),
    ('COYOTE', 'promote', 'ground', ['GRASSLAND_TEMPERATE', 'SAVANNA_TEMPERATE', 'MOUNTAIN'] + TEMP_WET,
     'the apex of today\'s prairies and marshes where wolves are gone; a pack hunter of deer'),
    ('WOLF', 'wire', 'ground', ['GLACIER'], 'arctic wolves hunt the ice margins of Greenland and Ellesmere'),
    ('BIRD_OWL_SNOWY', 'wire', 'flying', ['GLACIER'], 'snowy owls hunt over the ice edge'),
    ('LYNX', 'promote', 'ground', ['FOREST_TAIGA'], 'the boreal apex in winter, when the bears hibernate'),
    ('ALLIGATOR', 'wire', 'fresh', ['LAKE_TEMPERATE_FRESHWATER'], 'the apex of southern US lakes'),
    ('FISH_GAR_LONGNOSE', 'promote', 'fresh', ['LAKE_TEMPERATE_FRESHWATER'], 'a top fish predator of warm temperate lakes'),
    ('CROCODILE_SALTWATER', 'wire', 'fresh', ['LAKE_TROPICAL_FRESHWATER'], 'stands in for the Nile and mugger crocodiles, apexes of tropical lakes'),
    ('FISH_TIGERFISH', 'promote', 'fresh', ['LAKE_TROPICAL_FRESHWATER'], 'the goliath tigerfish tops African lakes and rivers'),
]


def spec_for(b):
    base = {'sav': 50, 'evil': 50, 'src': 'audit'}
    if b in OCEANS: return {'land': [], 'water': {'ocean': [dict(base, biome=b)]}, 'caverns': [], 'extinct': 'UNTAMED_WILDS'}, ['ocean']
    if b in LAKES: return {'land': [], 'water': {'lake': [dict(base, biome=b)]}, 'caverns': [], 'extinct': 'UNTAMED_WILDS'}, ['fresh']
    return {'land': [dict(base, biome=b)], 'water': {}, 'caverns': [], 'extinct': 'UNTAMED_WILDS'}, ['ground', 'flying']


def main():
    D = Design()
    rows = []
    for b in LAND + OCEANS + LAKES:
        spec, layers = spec_for(b)
        pool, _, _ = D.pool(spec)
        fbs = D.fort_biomes(spec)
        for L in layers:
            members = []
            for tok, e in pool.items():
                ls, _ = D.layers_of(e, spec, fbs)
                if L in ls and not e['gameVermin'] and not e.get('plant'): members.append(e)
            per = []
            for s in range(4):
                ins = [e for e in members if not e['noSeason'][s]]
                true = sorted((e['token'] for e in ins if D.apex_tier(e, L) == 'apex'))
                local = sorted((e['token'] for e in ins if D.apex_tier(e, L) == 'local'))
                per.append({'true': true, 'local': local})
            preds = sorted(((e['mass'], e['token']) for e in members if D.predator(e) and not D.apex_tier(e, L) and not e['sentient']), reverse=True)
            # the same count with the proposals applied (wired species added to the biome, promoted ones made true apexes)
            props = [p for p in PROPOSALS if p[2] == L and b in p[3]]
            after = []
            for s in range(4):
                t = set(per[s]['true'])
                for tok, kind, _, _, _ in props:
                    e = D.E.classify(tok)
                    if e['noSeason'][s]: continue
                    if kind == 'wire' or tok in per[s]['local'] or any(x['token'] == tok for x in members if not x['noSeason'][s]): t.add(tok)
                after.append(len(t))
            rows.append({'biome': b, 'layer': L, 'n': len(members), 'seasons': per, 'proposals': [p[0] + ' (' + p[1] + ')' for p in props],
                         'min_after': min(after),
                         'min_true': min(len(p['true']) for p in per), 'min_any': min(len(p['true']) + len(p['local']) for p in per),
                         'top_preds': [(t, m) for m, t in preds[:6]]})
    OUT.write_text(json.dumps({'rows': rows, 'proposals': [{'t': t, 'kind': k, 'layer': L, 'biomes': bs, 'why': w} for t, k, L, bs, w in PROPOSALS]}, indent=1))
    for r in rows:
        allt = sorted({t for p in r['seasons'] for t in p['true']}); alll = sorted({t for p in r['seasons'] for t in p['local']})
        flag = 'LOW' if r['min_true'] < 2 else ''
        if flag: print('    after proposals: min true per season', r['min_after'], r['proposals'])
        print(f"{flag:3} {r['biome']:34} {r['layer']:6} n={r['n']:3} true(min/season)={r['min_true']} any={r['min_any']} | {', '.join(allt)} | local: {', '.join(alll)} | top preds: {', '.join(t for t, m in r['top_preds'][:4])}")


if __name__ == '__main__':
    main()
