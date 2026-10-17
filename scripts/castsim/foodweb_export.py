"""castsim.foodweb_export: every wild creature in DF 53.16's raws, with what the v7.6 cast builder reads, for the Food Web
Explorer page (foodweb_page.py) and its in-page cast simulator (foodweb_sim.js).

The creature fields are the desk's (design.Design, engine.Engine: the engine's classify mirrored) after the same edits
Design.pool makes (placed plants, colony insects, the filter feeder); the gates, layers, slots, food-web test and cast build
are ported to foodweb_sim.js, which follows the engine (sw-wt/plugin ROSTER.FP, v7.6.1) where the engine has moved past the
desk: CAVE.ASSIGN (the user's cavern picks), the cavern food-web guarantee, the brook roster, hvSet's pet value for giants
(the root's) and its tie-break. Usage: python3 foodweb_export.py  (writes data/castsim/foodweb/creatures.json)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import design as DS  # noqa: E402
import engine as EN  # noqa: E402
from design import Design, explicit_water, fresh_raw  # noqa: E402
from design_run import wiring  # noqa: E402
from raws import LAND, OCEANS, LAKES, RIVERS, POOLS  # noqa: E402

ROOT = HERE.parent.parent
OUT = ROOT / 'data/castsim/foodweb/creatures.json'
SW = Path.home() / 'Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua'
THIEF_TAGS = ('CURIOUSBEAST_EATER', 'CURIOUSBEAST_GUZZLER', 'CURIOUSBEAST_ITEM', 'MISCHIEVOUS', 'LOCKPICKER', 'TRAPAVOID')
BROOK_MAX_MASS = 25000      # engine V7.WB.BROOK_MAX_MASS
WATER_ALL = OCEANS + LAKES + RIVERS + POOLS


LEG_WORDS = ('LEG', 'FOOT', 'FEET', 'TOE', 'QUADRUPED', 'HUMANOID', 'INSECT', 'SPIDER', 'CLAW', 'PINCER', 'HOOF', 'STANCE', '2PARTBODY_LEGS', 'BIRD')


def swv_class(c):
    """VERMIN.swvClass (engine): the tool's own vermin class, from flags and creature classes"""
    a, f, cc = c['any'], c['flags'], c['cclass']
    if 'EDIBLE_GROUND_BUG' in cc: return 'SWV_GROUND_BUG'
    if 'VERMIN_FISH' in f: return 'SWV_SMALL_FISH'
    if a('AQUATIC') or a('IMMOBILE_LAND'): return 'SWV_SMALL_FISH'
    if a('VERMIN_MICRO') or 'VERMIN_ROTTER' in f: return 'SWV_FLYING_INSECT'
    if 'VERMIN_SOIL_COLONY' in f: return 'SWV_COLONY'
    if 'VERMIN_SOIL' in f: return 'SWV_SOIL'
    if 'MAMMAL' in cc: return 'SWV_BAT' if a('FLIER') else 'SWV_SMALL_MAMMAL'
    if a('FLIER') and a('LAYS_EGGS'): return 'SWV_SMALL_BIRD'
    if a('FLIER'): return 'SWV_FLYING_INSECT'
    if a('AMPHIBIOUS'): return 'SWV_HERP'
    if not a('NOBONES'): return 'SWV_HERP'
    if 'VERMIN_GROUNDER' in f: return 'SWV_GROUND_BUG'
    return 'SWV_OTHER'


def cave_assign():
    """CAVE.ASSIGN as the engine has it (the user's 56 picks, 16 Oct), read from the Lua source"""
    src = SW.read_text()
    a = src.index('CAVE.ASSIGN = {')
    b = src.index('\n}', a)
    out = {}
    for m in re.finditer(r"(?:\['([^']+)'\]|([A-Z_]+))\s*=\s*\{([\d,\s]*)\}", src[a:b]):
        out[m.group(1) or m.group(2)] = [int(x) for x in m.group(3).replace(' ', '').split(',') if x]
    return out


def name_of(D, tok):
    toks = D.R.src[tok]['toks']
    nm = next((t for t in toks if t[0] == 'NAME'), None)
    return nm[1].lower() if nm and len(nm) > 1 else tok.lower().replace('_', ' ')


def main():
    D = Design(wiring=wiring())
    E, R = D.E, D.R
    wired = {t for v in D.wiring.values() for t, _ in v} | set(DS.EVIL_APEX)
    rows, funnel = [], {'all creatures': 0, 'wild': 0, 'natural': 0}
    for tok in sorted(R.src):
        c = R.creature(tok)
        funnel['all creatures'] += 1
        f = c['flags']
        if 'DOES_NOT_EXIST' in f or 'EQUIPMENT_WAGON' in f:
            continue
        info = E.classify(tok)
        plant = tok in DS.PLACED_PLANTS
        if plant:
            info = dict(info, eco='natural', locked=False)
        if 'VERMIN_SOIL_COLONY' in f and not info['gameVermin']:
            info = dict(info, gameVermin=True, category='vermin', guild='V')
        wild = bool(c['biomes']) and ('LARGE_ROAMING' in f or info['gameVermin'] or plant)
        if tok in DS.FILTER_FEEDERS and info['eco'] == 'unliving' and info['ecoWhy'] == ['NO_EAT+NO_DRINK']:
            info = dict(info, eco='natural', locked=False)
        natural = info['eco'] == 'natural' and not info['mega'] and not info['night']
        if wild: funnel['wild'] += 1
        if wild and natural: funnel['natural'] += 1
        if not (wild and natural) and tok not in wired:
            continue
        e = info
        root = c.get('root') if e['giant'] else None
        pet = R.creature(root)['pet'] if root and root in R.src else e['pet']   # ROSTER.hvInfo: a giant reads its root's value
        thief = [t for t in THIEF_TAGS if c['any'](t)]
        # vanilla 'this eats that': the raws' only creature-to-creature diet tokens (17 Oct survey of every creature token)
        gvc = sorted({t[1] for t in R.src[tok]['toks'] if t[0] == 'GOBBLE_VERMIN_CLASS' and len(t) > 1})
        gvt = sorted({t[1] for t in R.src[tok]['toks'] if t[0] == 'GOBBLE_VERMIN_CREATURE' and len(t) > 1})
        dhv = any(t[0] in ('DIVE_HUNTS_VERMIN', 'HUNTS_VERMIN') for t in R.src[tok]['toks'])
        body = [x for t in R.src[tok]['toks'] if t[0] == 'BODY' for x in t[1:]]
        legless = bool(body) and not any(w in x for x in body for w in LEG_WORDS)   # engine VERMIN.legless: no STANCE part
        swv = swv_class(c) if e['gameVermin'] else None
        bodies = sorted(e['bodies'])
        rows.append({
            't': tok, 'nm': name_of(D, tok), 'g': e['guild'], 'h': e['habitat'], 'ro': e['role'], 'v': bool(e['gameVermin']),
            'vc': E.vclass(e) if e['gameVermin'] else None, 'm': e['mass'], 'c0': e['cmin'], 'c1': e['cmax'],
            'bn': bool(e['benign']), 'gi': bool(e['giant']), 'ap': bool(e['ap']), 'apv': bool(e['apVermin']), 'civ': bool(e['civ']),
            'se': bool(e['sentient']), 'lp': bool(e['largePred']), 'war': bool(e['war']), 'pet': pet or 0, 'pet0': e['pet'] or 0,
            'sav': bool(e['savage']), 'gd': bool(e['good']), 'ev': bool(e['evil']), 'ex': bool(e['extinct']),
            'ns': [bool(e['noSeason'][s]) for s in range(4)], 'd': [e['depthLo'], e['depthHi']] if e['depthLo'] else None,
            'rt': e['root'], 'gob': bool(e['gobble']), 'fq': e['freq'], 'wd': DS.WEIRD.get(tok),
            'b': sorted(c['biomes']), 'wn': sorted(explicit_water(c['biome_tokens'], set(WATER_ALL))),
            'fr': fresh_raw(c['biomes']), 'fa': bool(E.fly_apex(dict(e, layer='land'))), 'bo': bool(E.boosted(e)),
            'pl': plant, 'nat': bool(wild and natural), 'th': thief,
            'cc': sorted(c['cclass']), 'gvc': gvc, 'gvt': gvt, 'dhv': dhv, 'swv': swv, 'carn': bool(e['carnivore']), 'grz': bool(c['any']('GRAZER') or c['any']('STANDARD_GRAZER')), 'lg': legless, 'amb': bool(c['any']('AMBUSHPREDATOR')), 'wb': bodies,
        })
    W = {f'{sav}|{al}|{L}|{b}': [[t, k] for t, k in v] for (sav, al, L, b), v in D.wiring.items()}
    meta = {
        'land': LAND, 'oceans': OCEANS, 'lakes': LAKES, 'rivers': RIVERS, 'pools': POOLS,
        'slots': DS.SLOTS, 'tier': D.TIER, 'reach': EN.REACH, 'vdiet': {k: sorted(v) for k, v in EN.VDIET.items()},
        'never_prey': sorted(EN.T['NEVER_PREY']), 'aquatic_apex': EN.R0['aquatic_apex'],
        'real_apex': {k: [v[0], v[1]] for k, v in DS.REAL_APEX.items()},
        'extra_biomes': {k: sorted(v) for k, v in DS.EXTRA_BIOMES.items()},
        'evil_extra_biomes': {k: sorted(v) for k, v in DS.EVIL_EXTRA_BIOMES.items()},
        'biome_limit': {k: sorted(v) for k, v in DS.BIOME_LIMIT.items()},
        'giant_bugs': sorted(DS.GIANT_BUGS), 'evil_apex': DS.EVIL_APEX,
        'evil_apex_biomes': {k: sorted(v) for k, v in DS.EVIL_APEX_BIOMES.items()},
        'salt_wet': sorted(DS.SALT_WET), 'fly_not_raptor': ['BIRD_ALBATROSS', 'BIRD_LOON', 'BIRD_PUFFIN', 'BIRD_STORK_WHITE'], 'wiring': W, 'cave_assign': cave_assign(),
        'params': {'pack': EN.CAST_DEF['pack'], 'giant': EN.CAST_DEF['giant'], 'hv_top': EN.CAST_DEF['hv_top'],
                   'reuse': DS.REUSE, 'ap_pick': EN.R0['ap_pick'], 'apex_pack': DS.APEX_PACK},
        'pool_cap': DS.POOL_CAP, 'brook_max_mass': BROOK_MAX_MASS,
        'savage_at': DS.SAVAGE_AT, 'evil_at': DS.EVIL_AT, 'good_at': DS.GOOD_AT,
        'funnel': funnel, 'source': 'DF 53.16 vanilla raws via castsim.raws; engine sw-wt/plugin v7.6.1',
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({'meta': meta, 'creatures': rows}, separators=(',', ':')))
    print('wrote', OUT, OUT.stat().st_size, 'creatures', len(rows), funnel, 'assign', len(meta['cave_assign']))


if __name__ == '__main__':
    main()
