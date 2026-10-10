"""castsim.pools: the population entries of an embark -- a real fort's, from a sw-state-check dump the run kit saved
(every world.populations.all entry within one region tile of the embark: race, layer key, quantity, type), or a synthetic
embark stocked the way DF's worldgen stocks a region (see synthetic())."""
from __future__ import annotations

import json
import random
from pathlib import Path


def depths_of(eng, tok):
    c = eng.R.creature(tok)
    d = c['depth']
    if not d or d[1] <= 0: return 'cavern', set()
    lo, hi = d
    cav = {x - 1 for x in range(lo, min(hi, 3) + 1)}
    return ('cavern', cav) if cav else ('deep', set())


def from_dump(eng, path):
    st = json.loads(Path(path).read_text())
    pops = []
    # the dump takes every entry within one world tile of the embark; the engine reads a surface entry only on the region
    # tiles its map blocks name (getEmbarkRegions' block set), and its cave entries on the wider ring. The tool's own
    # snapshot (captureDefault, at first enable) is keyed by exactly the land-layer entries the engine read, so it scopes
    # them; cave entries need no scoping; water-feature entries cannot be scoped from the dump (named in the report)
    snap = set((st.get('snapshot') or {}).keys())
    for idx, tok, key, qty, ext, typ in st['pops']:
        if snap and ':' not in key and key not in snap: continue
        if ':' in key and key.startswith('water:'): layer, deps = 'water', set()
        elif key.startswith('cave:'):
            layer, deps = depths_of(eng, tok) if tok in eng.R.src else ('cavern', set())
        else: layer, deps = 'land', set()
        pops.append({'race': tok, 'layer': layer, 'type': typ, 'quantity': qty, 'depths': deps, 'index': idx})
    return pops, st


def synthetic(eng, spec, seed=1):
    """DF worldgen, approximated: for each region biome of the embark, every natural creature whose BIOME admits it is a
    candidate (SAVAGE ones only on a savage region; GOOD/EVIL only on a region of their alignment; never a megabeast,
    night creature, unliving or civilised race); DF stocks a candidate with odds that follow its FREQUENCY (50 = the
    default, an even chance; 100 = always), as many entries as the region tiles it lives on, at its POPULATION_NUMBER.
    Land biomes stock land entries; lakes, rivers and pools stock water (feature) entries; an ocean coast stocks its sea
    life on land-layer entries, as DF does (STATE addendum 20); caverns stock SUBTERRANEAN species by raw depth."""
    rng = random.Random(seed)
    pops, idx = [], 0
    for tok in sorted(eng.R.src):
        c = eng.R.creature(tok)
        if 'DOES_NOT_EXIST' in c['flags'] or 'EQUIPMENT_WAGON' in c['flags']: continue
        info = eng.classify(tok)
        if info['eco'] != 'natural' or info['civ'] or info['mega'] or info['night']: continue
        if info['savage'] and not spec.get('savage'): continue
        if info['ap'] and not spec.get('savage'): continue
        b = c['biomes']
        p = min(1.0, max(0.05, c['freq'] / 100.0))
        def add(layer, n=1, deps=()):
            nonlocal idx
            for _ in range(n):
                q = rng.randint(15, 60) if not info['gameVermin'] else rng.randint(200, 3000)
                typ = 'Animal' if not info['gameVermin'] else ('ColonyInsect' if 'VERMIN_SOIL_COLONY' in c['flags'] else 'Vermin')
                pops.append({'race': tok, 'layer': layer, 'type': typ, 'quantity': q, 'depths': set(deps), 'index': idx}); idx += 1
        land_hit = [x for x in spec['land'] if x in b]
        if land_hit and rng.random() < p: add('land', len(land_hit))
        for w in spec.get('water', []):
            if w in b and rng.random() < p:
                add('land' if w.startswith('OCEAN') else 'water')
        if spec.get('caverns') and any(x.startswith('SUBTERRANEAN') for x in b) and rng.random() < p:
            layer, deps = depths_of(eng, tok)
            if layer == 'cavern' and deps: add('cavern', 1, deps)
    return pops
