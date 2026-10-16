"""castsim.cavern_weird: the cavern weirdness score against cavern diversity (user 15 Oct 2026: "cavern diversity may be
significantly reduced by the weirdness rating that we are using to place them semi-weighted into cavern layers").

Per cavern species (every raw creature the full-pool filters let into a cavern layer, vermin included): the hand score
(design.WEIRD = the engine's ROSTER.FP.WEIRD), the pick multiplier it gives in caverns 1-3, DF's raw depth range, the cast
slots it can fill, guild, habitat, size, group size, FREQUENCY and the raw tags that matter for a cast. Per cavern x slot:
how many species compete, and the effective number of species (1 / sum of squared pick shares) with the score and
without it, from the base pick weight (pack x3, giant x0.2, animal person x0.1; reuse and food-web links left out,
since they change cast by cast). Rig evidence: how many season casts held the species in each cavern, and how many
units of it arrived in the caverns, over the full-year forts in ecology.CELLS.
Usage: python3 cavern_weird.py   (writes data/castsim/cavern_weird.json)"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import crowd  # noqa: E402
import ecology  # noqa: E402
from design import Design, WEIRD, weird_weight  # noqa: E402

OUT = HERE.parent.parent / 'data' / 'castsim' / 'cavern_weird.json'
CAVES = (1, 2, 3)
SLOTS = ('apex', 'meso', 'ground prey', 'flier', 'swimmer', 'sentient')
# raw tags worth seeing beside a cavern cast slot
TAGS = ('LARGE_PREDATOR', 'CARNIVORE', 'BONECARN', 'BENIGN', 'AMBUSHPREDATOR', 'FLIER', 'AMPHIBIOUS', 'AQUATIC',
        'CAN_LEARN', 'CAN_SPEAK', 'INTELLIGENT', 'TRAPAVOID', 'WEBBER', 'NO_EAT', 'NO_DRINK', 'NOT_LIVING', 'NOPAIN',
        'NOFEAR', 'EXTRAVISION', 'FIREIMMUNE', 'MAGMA_SAFE', 'PET_EXOTIC', 'EVIL', 'SAVAGE', 'FANCIFUL', 'MUNDANE',
        'VERMIN_SOIL_COLONY', 'VERMIN_GROUNDER', 'VERMIN_FISH', 'VERMIN_EATER', 'UBIQUITOUS')
SPEC = {'land': [], 'water': {}, 'caverns': list(CAVES), 'extinct': 'WILDERNESS'}


def base_weight(D, e):
    """the cast pick weight without reuse and without the weirdness tilt"""
    return D.weight({'e': dict(e, weird=None)}, {}, 'ground')


def eff(ws):
    t = sum(ws)
    return round(1 / sum((w / t) ** 2 for w in ws), 1) if t else 0


def rig_evidence(known):
    """{token: {'casts': {cavern: n}, 'units': {cavern: n}, 'forts': n}} over the full-year forts, and the fort-years read"""
    ev = collections.defaultdict(lambda: {'casts': collections.Counter(), 'units': collections.Counter(), 'forts': set()})
    read = 0
    for _eng, r, a, name, _b, _rg in ecology.CELLS:
        cell = ecology.ROOT / r / a / 'rep1'
        if not (cell / 'events.tsv').exists():
            continue
        read += 1
        for (L, _s), v in ecology.casts(cell, known).items():
            if L.startswith('cavern'):
                for t in v['cast'] + v['vermin']:
                    ev[t]['casts'][int(L[-1])] += 1
        bands = crowd.cavern_bands(cell)
        for line in (cell / 'events.tsv').read_text(encoding='cp437').splitlines()[1:]:
            x = line.split('\t')
            if len(x) < 10 or x[1] != 'ARRIVE' or x[5] not in ecology.WILD or x[9] != 'cavern' or x[3] in crowd.PLACED:
                continue
            k = crowd.depth_of(bands, int(x[8])) if bands and x[8].lstrip('-').isdigit() else 0
            ev[x[3]]['units'][k] += 1
            ev[x[3]]['forts'].add(f'{r}/{a}')
    return ev, read


def main():
    D = Design()
    pool, _f, _r = D.pool(SPEC)
    fbs = D.fort_biomes(SPEC)
    rows, by_slot = [], {(k, s): [] for k in CAVES for s in SLOTS}
    for tok, e in sorted(pool.items()):
        layers, _notes = D.layers_of(e, SPEC, fbs)
        caves = [int(L[-1]) for L in layers if L.startswith('cavern')]
        if not caves:
            continue
        c = D.R.creature(tok)
        verm = bool(e['gameVermin'])
        slots = [] if verm else D.slots_for(e, 'cavern1', None)
        w0 = base_weight(D, e)
        sc = WEIRD.get(tok)
        mult = {k: (round(weird_weight(k, sc), 3) if sc is not None else 1.0) for k in CAVES}
        row = {'t': tok, 'wd': sc, 'mult': mult, 'caves': caves, 'dep': list(c['depth']) if c.get('depth') else None,
               'v': verm, 'vc': D.E.vclass(e) if verm else '', 'slots': slots, 'g': e['guild'], 'h': e['habitat'],
               'm': e['mass'], 'cl': list(e.get('cmin') and (e['cmin'], e['cmax']) or ()), 'fq': c.get('freq'),
               'pet': e['pet'], 'w0': round(w0, 3), 'sent': bool(e['sentient']), 'ap': bool(e['ap']),
               'tags': [t for t in TAGS if t in c['flags']], 'file': c.get('file', '')}
        rows.append(row)
        if not verm:
            for k in caves:
                for s in slots:
                    by_slot[(k, s)].append(row)
    # pick shares per cavern x slot, with the score and flat
    summary = []
    for (k, s), lst in by_slot.items():
        if not lst:
            summary.append({'cave': k, 'slot': s, 'n': 0}); continue
        wt = [r['w0'] * r['mult'][k] for r in lst]
        wf = [r['w0'] for r in lst]
        tt, tf = sum(wt), sum(wf)
        for r, a, b in zip(lst, wt, wf):
            r.setdefault('share', {})[f'{k}|{s}'] = [round(100 * a / tt, 1), round(100 * b / tf, 1)]
        top = max(zip(lst, wt), key=lambda z: z[1])
        topf = max(zip(lst, wf), key=lambda z: z[1])
        low = sum(1 for r in lst if r['mult'][k] <= 0.15)
        summary.append({'cave': k, 'slot': s, 'n': len(lst), 'eff': eff(wt), 'eff_flat': eff(wf),
                        'top': top[0]['t'], 'top_share': round(100 * top[1] / tt, 1),
                        'top_flat': topf[0]['t'], 'top_flat_share': round(100 * topf[1] / tf, 1), 'suppressed': low,
                        'unscored': sum(1 for r in lst if r['wd'] is None)})
    ev, read = rig_evidence(set(D.R.src))
    for r in rows:
        x = ev.get(r['t'])
        r['rig'] = {'casts': {k: x['casts'][k] for k in CAVES}, 'units': {k: x['units'][k] for k in CAVES},
                    'forts': len(x['forts'])} if x else {'casts': {k: 0 for k in CAVES}, 'units': {k: 0 for k in CAVES}, 'forts': 0}
    scored_absent = sorted(t for t in WEIRD if t not in {r['t'] for r in rows})
    OUT.write_text(json.dumps({'rows': rows, 'summary': summary, 'fort_years': read, 'scored_not_in_pool': scored_absent}, indent=1))
    print('wrote', OUT, len(rows), 'species;', sum(1 for r in rows if not r['v']), 'non-vermin;', read, 'fort-years')
    for x in summary:
        if x['n']:
            print(f"  cavern {x['cave']} {x['slot']:12} n {x['n']:2}  eff {x['eff']:5} (flat {x['eff_flat']:5})  "
                  f"top {x['top']} {x['top_share']}% (flat {x['top_flat']} {x['top_flat_share']}%)  "
                  f"suppressed {x['suppressed']}  unscored {x['unscored']}")
    print('scored but not in the cavern pool:', scored_absent)
    print('unscored non-vermin:', [r['t'] for r in rows if r['wd'] is None and not r['v']])


if __name__ == '__main__':
    main()
