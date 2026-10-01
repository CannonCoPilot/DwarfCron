#!/usr/bin/env python3
"""Chart-ready population statistics over DF 53.16 vanilla creature raws for seasonal-wildlife questions.
Reuses data/eco-desk/census.py (resolver) and data/eco-desk/v2/guilds/species2.py (guilds, mass, flags)."""
import json, math, sys, datetime, statistics
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path('/Users/nathanielcannon/Claude/Projects/DwarfCron')
sys.path.insert(0, str(ROOT / 'data/eco-desk'))
sys.path.insert(0, str(ROOT / 'data/eco-desk/v2/guilds'))
import census as C          # noqa
import species2 as S        # noqa

OUT = ROOT / 'data/eco-report/raws.json'

# ------------------------------------------------------------------ resolve every raw creature (vanilla + extinct)
paths = [(p, 'vanilla') for p in sorted((C.VAN / 'vanilla_creatures/objects').glob('*.txt'))]
paths += [(p, 'extinct') for p in sorted((C.VAN / 'vanilla_creatures_extinct/objects').glob('*.txt'))]
CR, VA, SRC = C.read_objects(paths)
cache, info = {}, {}
RAW = {}
for cid in CR:
    tags = C.resolve(cid, CR, VA, cache, info)
    castes, occ = C.caste_walk(tags)
    RAW[cid] = dict(tags=tags, names=set(occ), occ=occ, castes=castes)

def last(cid, tok):
    o = RAW[cid]['occ'].get(tok)
    return o[-1][1] if o else None
def vals(cid, tok):
    return [o[1] for o in RAW[cid]['occ'].get(tok, [])]
def iv(x, d=None):
    try: return int(x)
    except Exception: return d

# entity races (civ citizens)
ENT = set()
import re
for f in (C.VAN / 'vanilla_entities/objects').glob('*.txt'):
    for m in re.finditer(r'\[([^\[\]]+)\]', f.read_text(encoding='latin-1', errors='replace')):
        p = m.group(1).split(':')
        if p[0] == 'CREATURE' and len(p) > 1: ENT.add(p[1])

# ------------------------------------------------------------------ the wildlife set
SP = S.load(include_classes=('natural', 'mythic', 'unliving'))
ALLV = [c for c in CR if SRC[c][0] == 'vanilla']
ALLX = [c for c in CR if SRC[c][0] == 'extinct']
withbiome_v = [c for c in ALLV if vals(c, 'BIOME')]
mega = [c for c in withbiome_v if RAW[c]['names'] & {'MEGABEAST', 'SEMIMEGABEAST'}]
W = {k: s for k, s in SP.items() if s.source == 'vanilla' and k not in mega}
X = {k: s for k, s in SP.items() if s.source == 'extinct'}
excluded = sorted(set(withbiome_v) - set(W))
excl_why = {}
for c in excluded:
    n = RAW[c]['names']
    if n & {'MEGABEAST', 'SEMIMEGABEAST'}: excl_why[c] = 'MEGABEAST/SEMIMEGABEAST (worldgen-placed, arrives as an attack)'
    elif 'IMMOBILE' in n: excl_why[c] = 'IMMOBILE (sponges; species2 drops them)'
    else: excl_why[c] = 'other'

# ------------------------------------------------------------------ per-species derived facts
GUILD_ORDER = ['AL', 'AW', 'RP', 'ML', 'MW', 'GZ', 'SH', 'PE', 'FC', 'FF', 'WB', 'LB', 'PL', 'VG', 'VC', 'VI', 'VB', 'VF']
GUILD_NAME = {'AL': 'apex land', 'AW': 'water apex', 'RP': 'raptor', 'ML': 'ground mesocarnivore', 'MW': 'water mesopredator',
              'GZ': 'grazer', 'SH': 'shore/semiaquatic prey', 'PE': 'pelagic', 'FC': 'coastal fish', 'FF': 'freshwater fish',
              'WB': 'waterbird', 'LB': 'land bird', 'PL': 'other land prey', 'VG': 'vermin ground', 'VC': 'vermin soil colony',
              'VI': 'vermin flying insect', 'VB': 'vermin bird/bat', 'VF': 'vermin fish/aquatic'}
PRED = S.PRED_GUILDS

def role(s):
    if s.vermin: return 'vermin'
    return 'predator' if s.guild in PRED else 'prey'

def layer(s):
    if 'SUBTERRANEAN_LAVA' in s.biomes or (s.depth[0] >= 4): return 'magma-deep'
    if not s.surface: return 'cavern'
    if s.flier: return 'flying'
    water_only = all(S.is_water(b) or b == 'SUBTERRANEAN_WATER' for b in s.biomes)
    if s.aquatic or s.amphib or water_only: return 'water'
    return 'surface land'
LAYERS = ['surface land', 'flying', 'water', 'cavern', 'magma-deep']

def gaits(cid):
    out = {}
    for t in vals(cid, 'GAIT'):
        if len(t) > 3 and iv(t[3]) is not None:
            k = t[1]; v = iv(t[3])
            out[k] = min(out.get(k, 10 ** 9), v)
    return out

def mode_of(s, g):
    if s.flier and 'FLY' in g: return 'FLY'
    if s.aquatic and 'SWIM' in g: return 'SWIM'
    for k in ('WALK', 'CRAWL', 'CLIMB', 'SWIM', 'FLY'):
        if k in g: return k
    return None

def pair(t, a=1):
    if not t: return (None, None)
    return iv(t[a]), iv(t[a + 1]) if len(t) > a + 1 else iv(t[a])

def anyname(cid, *toks): return any(t in RAW[cid]['names'] for t in toks)

def swv(cid, s):
    n = RAW[cid]['names']; cls = {t[1] for t in vals(cid, 'CREATURE_CLASS') if len(t) > 1}
    if 'EDIBLE_GROUND_BUG' in cls: return 'ground bug'
    if 'VERMIN_FISH' in n: return 'fish'
    if 'AQUATIC' in n or 'IMMOBILE_LAND' in n: return 'fish'
    if 'VERMIN_MICRO' in n or 'VERMIN_ROTTER' in n: return 'flying insect'
    if 'VERMIN_SOIL_COLONY' in n or 'VERMIN_SOIL' in n: return 'soil'
    if 'MAMMAL' in cls: return 'small mammal'
    if 'FLIER' in n and 'LAYS_EGGS' in n: return 'small bird'
    if 'FLIER' in n: return 'flying insect'
    if 'AMPHIBIOUS' in n: return 'herp'
    if 'NOBONES' not in n: return 'herp'
    if 'VERMIN_GROUNDER' in n: return 'ground bug'
    return 'other'

def legless(cid):
    names = [t[2].upper() for t in vals(cid, 'GAIT') if len(t) > 2]
    if not names: return False
    return not any('WALK' in x or 'RUN' in x for x in names)

def humanoid(cid):
    cls = {t[1] for t in vals(cid, 'CREATURE_CLASS') if len(t) > 1}
    return cid in ENT or cid.endswith('MAN') or 'ANIMAL_PERSON' in cls

SCAV_TEXT = {'BIRD_VULTURE', 'BIRD_BUZZARD', 'BEAR_BLACK', 'JACKAL', 'HYENA', 'BIRD_RAVEN', 'FLESH_BALL'}

REC = {}
for pool, srcname in ((W, 'vanilla'), (X, 'extinct')):
    for k, s in pool.items():
        g = gaits(k); md = mode_of(s, g)
        pn = pair(last(k, 'POPULATION_NUMBER')); cn = pair(last(k, 'CLUSTER_NUMBER'))
        cl = [pair(t) for t in vals(k, 'CLUTCH_SIZE')]
        ch = [iv(t[1]) for t in vals(k, 'CHILD') if len(t) > 1]
        gt = [iv(t[1]) for t in vals(k, 'GRASSTRAMPLE') if len(t) > 1]
        bf = [iv(t[1]) for t in vals(k, 'BEACH_FREQUENCY') if len(t) > 1]
        REC[k] = dict(
            id=k, source=srcname, kind=s.kind, root=s.root, guild=s.guild, role=role(s), layer=layer(s),
            also_cavern=bool(s.surface and s.cavern), mass=s.mass, eco=s.eco, vermin=s.vermin,
            animal_person=s.kind == 'animal_person', giant=s.giant, sentient=s.sentient, civ_race=k in ENT,
            pop_min=pn[0], pop_max=pn[1], cl_min=cn[0], cl_max=cn[1], cl_declared=cn[0] is not None,
            freq=s.freq, freq_declared=not s.freq_raw.startswith('('),
            top_speed=(g[md] if md else None), speed_mode=md, gaits=g,
            clutch_min=min((c[0] for c in cl if c[0] is not None), default=None),
            clutch_max=max((c[1] for c in cl if c[1] is not None), default=None),
            lays_eggs=anyname(k, 'LAYS_EGGS'), child=min(ch) if ch else None,
            grasstrample=max(gt) if gt else None, std_grazer=anyname(k, 'STANDARD_GRAZER'), grazer_tok=anyname(k, 'GRAZER'),
            beach=max(bf) if bf else None, depth=list(s.depth) if s.depth != (0, 0) else None,
            scav=(k in SCAV_TEXT or anyname(k, 'BONECARN', 'CURIOUSBEAST_EATER')) and not humanoid(k),
            humanoid=humanoid(k), legless=legless(k), swv=swv(k, s) if s.vermin else None,
            classes=sorted({t[1] for t in vals(k, 'CREATURE_CLASS') if len(t) > 1}),
            biomes=sorted(s.biomes), seasons=sorted(s.seasons))

V = [r for r in REC.values() if r['source'] == 'vanilla']
XV = [r for r in REC.values() if r['source'] == 'extinct']
def sp(id_): return SP[id_]

# ------------------------------------------------------------------ figures
FIG = []
def fig(**kw):
    base = dict(id=None, title=None, subtitle='', caption='', form='bar', x=None, y=None, series=None, facet=None,
                unit=None, log=False, rows=[], notes='')
    base.update(kw); FIG.append(base); return base

def pct(a, b): return round(100.0 * a / b, 1) if b else 0.0
nV = len(V)
gcount = Counter(r['guild'] for r in V)

# 1. guild x layer x role
c1 = Counter((r['guild'], r['layer'], r['role']) for r in V)
rows1 = [dict(guild=g, guild_name=GUILD_NAME[g], layer=l, role=ro, count=n) for (g, l, ro), n in sorted(c1.items(), key=lambda kv: (GUILD_ORDER.index(kv[0][0]), LAYERS.index(kv[0][1])))]
role_ct = Counter(r['role'] for r in V); layer_ct = Counter(r['layer'] for r in V)
top_g = gcount.most_common(1)[0]
fig(id='1', title=f'{nV} wildlife species fall into 18 guilds; predators are {role_ct["predator"]} ({pct(role_ct["predator"], nV)}%), prey {role_ct["prey"]}, vermin {role_ct["vermin"]}',
    subtitle='Species count by guild, stacked by layer family; facet by role', form='stackedBar', x='guild', y='count', series='layer', facet='role',
    unit='species', rows=rows1,
    caption=f'Layer family per species (precedence magma-deep > cavern-only > flying > water > surface land). Totals by layer: ' + ', '.join(f'{l} {layer_ct[l]}' for l in LAYERS) + f'. Largest guild: {top_g[0]} ({top_g[1]}). {sum(r["also_cavern"] for r in V)} surface species also list a cavern biome (counted as surface).',
    notes='role = predator when guild in PRED_GUILDS {AL,AW,RP,ML,MW}; vermin guilds V*; else prey. Includes animal people and giants (filter with figure 12 flags in species list).')

# 2. body size strip by guild, with extinct facet
rows2 = [dict(id=r['id'], guild=r['guild'], source=r['source'], kind=r['kind'], mass=r['mass'],
              band=('small' if r['mass'] < 150000 else 'medium' if r['mass'] < 1000000 else 'large')) for r in REC.values()]
bands = Counter(x['band'] for x in rows2 if x['source'] == 'vanilla')
med = {g: statistics.median([r['mass'] for r in V if r['guild'] == g]) for g in GUILD_ORDER if gcount[g]}
mn2 = min((x for x in rows2 if x['source'] == 'vanilla'), key=lambda x: x['mass']); mx2 = max((x for x in rows2 if x['source'] == 'vanilla'), key=lambda x: x['mass'])
fig(id='2', title=f'Adult size spans {math.log10(mx2["mass"] / mn2["mass"]):.1f} orders of magnitude ({mn2["id"]} {mn2["mass"]:,} to {mx2["id"]} {mx2["mass"]:,} cm³): {bands["small"]} small, {bands["medium"]} medium, {bands["large"]} large species (tool bands <150k / <1M cm³)',
    subtitle='Adult BODY_SIZE (final, x CHANGE_BODY_SIZE_PERC) per species by guild, log scale; facet vanilla vs extinct', form='dot', x='guild', y='mass',
    series='kind', facet='source', unit='cm³', log=True, rows=rows2,
    caption='Median adult volume by guild (vanilla): ' + ', '.join(f'{g} {med[g]:,.0f}' for g in GUILD_ORDER if g in med) + '. Reference lines: 150,000 (small/medium) and 1,000,000 (medium/large), MODEL.SMALL / MODEL.LARGE in seasonal-wildlife.lua.',
    notes='mass = species2 mass (the tool fixture MODEL.audit adultSize in cm³, else census adult_body_size). Extinct facet = vanilla_creatures_extinct raws (the bestiary calls them modded extinct).',
    refLines=[dict(y=150000, label='small < 150k'), dict(y=1000000, label='large >= 1M')])

# 3. FREQUENCY
rows3 = [dict(id=r['id'], guild=r['guild'], kind=r['kind'], freq=r['freq'], declared=r['freq_declared']) for r in V]
at50 = sum(1 for r in V if r['freq'] == 50); und = sum(1 for r in V if not r['freq_declared'])
fdist = Counter(r['freq'] for r in V); ap0 = sum(1 for r in V if r['freq'] == 0)
fig(id='3', title=f'{pct(at50, nV)}% of wildlife ({at50}/{nV}) sits at FREQUENCY 50; {und} species never declare FREQUENCY',
    subtitle='Effective FREQUENCY (last FREQUENCY x CHANGE_FREQUENCY_PERC; default 50) per species, by guild', form='dot', x='guild', y='freq',
    series='kind', unit='FREQUENCY (0-100)', rows=rows3,
    caption='Value counts: ' + ', '.join(f'{k}:{v}' for k, v in sorted(fdist.items())) + f'. Animal people carry CHANGE_FREQUENCY_PERC:10 (5 or 10 for most) and giants a halving (25 for most); integer rounding leaves {ap0} animal people at FREQUENCY 0.',
    notes='Histogram view: bin rows by freq. declared=false means no FREQUENCY token (DF default 50).')

# 4. POPULATION_NUMBER / CLUSTER_NUMBER
rows4 = []
for r in V:
    rows4.append(dict(id=r['id'], guild=r['guild'], kind=r['kind'], measure='POPULATION_NUMBER', min=r['pop_min'], max=r['pop_max']))
    rows4.append(dict(id=r['id'], guild=r['guild'], kind=r['kind'], measure='CLUSTER_NUMBER', min=r['cl_min'] if r['cl_declared'] else 1,
                      max=r['cl_max'] if r['cl_declared'] else 1, declared=r['cl_declared']))
def rng(g, a, b):
    xs = [(r[a], r[b]) for r in V if r['guild'] == g and r[a] is not None]
    return (min(x[0] for x in xs), max(x[1] for x in xs)) if xs else (None, None)
grp_summary = {g: dict(pop=rng(g, 'pop_min', 'pop_max'), cl=rng(g, 'cl_min', 'cl_max')) for g in GUILD_ORDER}
solo = sum(1 for r in V if not r['vermin'] and (not r['cl_declared'] or r['cl_max'] == 1))
nonv = sum(1 for r in V if not r['vermin'])
biggest_cl = max((r for r in V if r['cl_max'] and not r['vermin']), key=lambda r: r['cl_max'])
fig(id='4', title=f'{solo} of {nonv} non-vermin species ({pct(solo, nonv)}%) arrive alone (CLUSTER_NUMBER 1:1 or absent); the largest non-vermin group is {biggest_cl["id"]} at {biggest_cl["cl_min"]}:{biggest_cl["cl_max"]}',
    subtitle='POPULATION_NUMBER and CLUSTER_NUMBER min-max per species, grouped by guild', form='range', x='guild', y='max', series='measure',
    unit='individuals', log=True, rows=rows4,
    caption='Guild envelopes (pop min-max / cluster min-max): ' + '; '.join(f'{g} {v["pop"][0]}-{v["pop"][1]} / {v["cl"][0]}-{v["cl"][1]}' for g, v in grp_summary.items() if v['pop'][0] is not None),
    notes='Absent CLUSTER_NUMBER plotted as 1:1 with declared=false. Vermin have POPULATION_NUMBER (stock) but no CLUSTER_NUMBER.')

# 5. seasons
SEAS = ['SPRING', 'SUMMER', 'AUTUMN', 'WINTER']
rows5 = []
for g in GUILD_ORDER:
    grp = [r for r in V if r['guild'] == g]
    if not grp: continue
    for x in SEAS:
        n = sum(1 for r in grp if x not in r['seasons'])
        rows5.append(dict(guild=g, token='NO_' + x, count=n, share=pct(n, len(grp)), n=len(grp)))
noc = Counter()
for r in V:
    for x in SEAS:
        if x not in r['seasons']: noc[x] += 1
allyear = sum(1 for r in V if len(r['seasons']) == 4)
hib = sorted(((pct(sum(1 for r in V if r['guild'] == g and 'WINTER' not in r['seasons']), gcount[g]), g) for g in GUILD_ORDER if gcount[g]), reverse=True)
fig(id='5', title=f'NO_WINTER is the only season gate in use: {noc["WINTER"]} species ({pct(noc["WINTER"], nV)}%) skip winter vs NO_SPRING {noc["SPRING"]}, NO_AUTUMN {noc["AUTUMN"]}, NO_SUMMER {noc["SUMMER"]}; {allyear} are present all year',
    subtitle='Species with each NO_<season> token, by guild (count and share of guild)', form='heatmap', x='token', y='guild', series=None,
    unit='% of guild', rows=rows5,
    caption=f'Totals: NO_SPRING {noc["SPRING"]}, NO_SUMMER {noc["SUMMER"]}, NO_AUTUMN {noc["AUTUMN"]}, NO_WINTER {noc["WINTER"]}. Guilds hibernating most (NO_WINTER share): ' + ', '.join(f'{g} {p}%' for p, g in hib[:6]) + '.',
    notes='Any caste carrying the token counts (species2 seasons).')

# 6. biome coverage
def bfam(b):
    if b.startswith('FOREST'): return 'forest'
    if b.startswith('GRASSLAND'): return 'grassland'
    if b.startswith('SAVANNA'): return 'savanna'
    if b.startswith('SHRUBLAND'): return 'shrubland'
    if b in ('TUNDRA', 'GLACIER'): return 'tundra/glacier'
    if b.startswith('DESERT'): return 'desert'
    if b.startswith(('SWAMP', 'MARSH')): return 'wetland'
    if b == 'MOUNTAIN': return 'mountain'
    if b.startswith('OCEAN'): return 'ocean'
    if b.startswith('LAKE'): return 'lake'
    if b.startswith('RIVER'): return 'river'
    if b.startswith('POOL'): return 'pool'
    return {'SUBTERRANEAN_CHASM': 'cavern land', 'SUBTERRANEAN_WATER': 'cavern water', 'SUBTERRANEAN_LAVA': 'magma'}[b]
def zone(b):
    if b in ('TUNDRA', 'GLACIER', 'FOREST_TAIGA', 'OCEAN_ARCTIC'): return 'polar/taiga'
    if 'TEMPERATE' in b: return 'temperate'
    if 'TROPICAL' in b or b == 'SWAMP_MANGROVE': return 'tropical'
    return 'unzoned (mountain/desert/subterranean)'
FAMS = ['forest', 'grassland', 'savanna', 'shrubland', 'tundra/glacier', 'desert', 'wetland', 'mountain', 'ocean', 'lake', 'river', 'pool', 'cavern land', 'cavern water', 'magma']
ZONES = ['temperate', 'tropical', 'polar/taiga', 'unzoned (mountain/desert/subterranean)']
rows6 = []
fc = Counter(); zc = Counter(); fcv = Counter()
for r in V:
    fs = {bfam(b) for b in r['biomes']}; zs = {zone(b) for b in r['biomes']}
    for f in fs:
        fc[f] += 1
        if r['vermin']: fcv[f] += 1
    for z in zs: zc[z] += 1
for f in FAMS: rows6.append(dict(dimension='biome family', category=f, count=fc[f], vermin=fcv[f], nonvermin=fc[f] - fcv[f]))
for z in ZONES: rows6.append(dict(dimension='temperature zone', category=z, count=zc[z]))
sav = sum(1 for r in V if sp(r['id']).savage); good = sum(1 for r in V if sp(r['id']).good); evil = sum(1 for r in V if sp(r['id']).evil)
for lab, n in (('SAVAGE', sav), ('GOOD', good), ('EVIL', evil), ('none (calm-only)', sum(1 for r in V if not (sp(r['id']).savage or sp(r['id']).good or sp(r['id']).evil)))):
    rows6.append(dict(dimension='alignment requirement', category=lab, count=n))
savk = Counter(r['kind'] for r in V if sp(r['id']).savage)
fig(id='6', title=f'Forest is the widest family ({fc["forest"]} species); {sav} species ({pct(sav, nV)}%) need a SAVAGE region, {good} GOOD and {evil} EVIL',
    subtitle='Species per biome family, per temperature zone, and alignment requirement (a species counts once per family/zone it lists)', form='groupedBar',
    x='category', y='count', series='dimension', facet='dimension', unit='species', rows=rows6,
    caption=f'SAVAGE species by kind: ' + ', '.join(f'{k} {v}' for k, v in savk.items()) + '. Zone: polar/taiga = TUNDRA, GLACIER, FOREST_TAIGA, OCEAN_ARCTIC; MOUNTAIN, DESERT_* and SUBTERRANEAN_* carry no zone.',
    notes='Biome lists expanded from ANY_* shortcuts (species2.expand). Pool biomes hold vermin only.')

# 7. habitat / locomotion
def hab(r):
    n = RAW[r['id']]['names']
    return dict(AQUATIC='AQUATIC' in n, AMPHIBIOUS='AMPHIBIOUS' in n, FLIER='FLIER' in n, IMMOBILE_LAND='IMMOBILE_LAND' in n,
                SWIMS_INNATE='SWIMS_INNATE' in n, SWIMS_LEARNED='SWIMS_LEARNED' in n,
                **{'land-only (no AQUATIC/AMPHIBIOUS/FLIER)': not (n & {'AQUATIC', 'AMPHIBIOUS', 'FLIER'})})
HTOK = ['land-only (no AQUATIC/AMPHIBIOUS/FLIER)', 'AQUATIC', 'AMPHIBIOUS', 'FLIER', 'IMMOBILE_LAND', 'SWIMS_INNATE', 'SWIMS_LEARNED']
rows7 = []; tot7 = Counter()
for g in GUILD_ORDER:
    grp = [r for r in V if r['guild'] == g]
    if not grp: continue
    hs = [hab(r) for r in grp]
    for t in HTOK:
        n = sum(h[t] for h in hs); tot7[t] += n
        rows7.append(dict(guild=g, token=t, count=n, share=pct(n, len(grp)), n=len(grp)))
fig(id='7', title=f'{tot7["SWIMS_INNATE"]} species ({pct(tot7["SWIMS_INNATE"], nV)}%) swim innately but only {tot7["AQUATIC"]} are AQUATIC and {tot7["AMPHIBIOUS"]} AMPHIBIOUS; {tot7["FLIER"]} fly',
    subtitle='Habitat and locomotion tokens by guild (count, share of guild)', form='heatmap', x='token', y='guild', unit='% of guild', rows=rows7,
    caption='Totals: ' + ', '.join(f'{t} {tot7[t]}' for t in HTOK) + '. IMMOBILE_LAND = fish-like (cannot move on land). SWIMS_INNATE says nothing about habitat (wolves and eagles carry it).',
    notes='Any caste.')

# 8. behaviour heatmap
BT = ['LARGE_PREDATOR', 'BENIGN', 'CARNIVORE', 'BONECARN', 'CURIOUSBEAST_EATER', 'CURIOUSBEAST_ITEM', 'CURIOUSBEAST_GUZZLER', 'AMBUSHPREDATOR',
      'FLEEQUICK', 'VISION_ARC', 'PRONE_TO_RAGE', 'MEANDERER', 'LOCAL_POPS_PRODUCE_HEROES', 'GOBBLE_VERMIN_CLASS', 'GOBBLE_VERMIN_CREATURE',
      'HUNTS_VERMIN', 'DIVE_HUNTS_VERMIN', 'PET', 'PET_EXOTIC', 'MOUNT', 'SEMIMEGABEAST', 'MEGABEAST', 'FANCIFUL', 'SAVAGE', 'GOOD', 'EVIL',
      'BEACH_FREQUENCY', 'UBIQUITOUS', 'LARGE_ROAMING', 'NOCTURNAL']
rows8 = []; tot8 = Counter()
for g in GUILD_ORDER:
    grp = [r for r in V if r['guild'] == g]
    if not grp: continue
    for t in BT:
        n = sum(1 for r in grp if t in RAW[r['id']]['names']); tot8[t] += n
        rows8.append(dict(guild=g, token=t, count=n, share=pct(n, len(grp)), n=len(grp)))
absent = [t for t in BT if tot8[t] == 0]
lp_ml = next(x for x in rows8 if x['guild'] == 'ML' and x['token'] == 'BENIGN')
pred_benign = sum(1 for r in V if r['role'] == 'predator' and 'BENIGN' in RAW[r['id']]['names'])
npred = role_ct['predator']
fig(id='8', title=f'{pred_benign} of {npred} predator-guild species ({pct(pred_benign, npred)}%) carry BENIGN; LARGE_PREDATOR is on {tot8["LARGE_PREDATOR"]} species',
    subtitle='Share of each guild carrying each behaviour token (any caste)', form='heatmap', x='token', y='guild', unit='% of guild', rows=rows8,
    caption='Totals across wildlife: ' + ', '.join(f'{t} {tot8[t]}' for t in BT) + '.' + (f' Absent from the wildlife set: {", ".join(absent)}.' if absent else ''),
    notes='LOCAL_POPS_PRODUCE_HEROES kept because present (animal people). MEGABEAST/SEMIMEGABEAST are 0 by the filter (those species are excluded). LARGE_ROAMING and NOCTURNAL added as context.')

# 9. scavengers
SC = [r for r in V if r['scav']]
def why_scav(r):
    w = []
    if r['id'] in SCAV_TEXT: w.append('listed')
    if 'BONECARN' in RAW[r['id']]['names']: w.append('BONECARN')
    if 'CURIOUSBEAST_EATER' in RAW[r['id']]['names']: w.append('CURIOUSBEAST_EATER')
    return '+'.join(w)
def loco(r):
    n = RAW[r['id']]['names']
    if 'AQUATIC' in n: return 'aquatic'
    if 'FLIER' in n: return 'flier'
    if 'AMPHIBIOUS' in n: return 'amphibious'
    return 'walker'
rows9 = [dict(id=r['id'], guild=r['guild'], kind=r['kind'], layer=r['layer'], locomotion=loco(r), why=why_scav(r), mass=r['mass']) for r in SC]
lc9 = Counter(x['locomotion'] for x in rows9)
aq9 = sorted(x['id'] for x in rows9 if x['locomotion'] == 'aquatic')
cand_excl = sorted(r['id'] for r in V if (r['id'] in SCAV_TEXT or anyname(r['id'], 'BONECARN', 'CURIOUSBEAST_EATER')) and r['humanoid'])
fig(id='9', title=f'{len(SC)} wildlife species pass SCAV.is; only {lc9["aquatic"]} are aquatic ({", ".join(aq9)})',
    subtitle='Species SCAV.is accepts (listed, BONECARN or CURIOUSBEAST_EATER; humanoids excluded), by locomotion and layer', form='stackedBar',
    x='locomotion', y='count', series='layer', unit='species', rows=rows9,
    caption='By locomotion: ' + ', '.join(f'{k} {v}' for k, v in lc9.most_common()) + f'. Excluded as humanoid (animal people, *MAN, entity races): {len(cand_excl)} species. Per-species rows; count rows to draw the bar.',
    notes='SCAV.is reads caste flag CURIOUS_BEAST_EATER (DFHack enum) = raw CURIOUSBEAST_EATER. Mythic SEA_MONSTER is in the wildlife set here (the species2 natural filter alone drops it).')

# 10. speed vs mass
rows10 = [dict(id=r['id'], guild=r['guild'], role=r['role'], kind=r['kind'], mass=r['mass'], speed=r['top_speed'], mode=r['speed_mode'])
          for r in V if r['top_speed'] and not r['vermin']]
def medsp(ro, mode=None):
    xs = [x['speed'] for x in rows10 if x['role'] == ro and (mode is None or x['mode'] == mode)]
    return statistics.median(xs) if xs else None
fastest = min((x for x in rows10 if x['mode'] == 'WALK'), key=lambda x: x['speed'])
nogait = sum(1 for r in V if not r['vermin'] and not r['top_speed'])
def medk(ro, kind, mode='WALK'):
    xs = [x['speed'] for x in rows10 if x['role'] == ro and x['kind'] == kind and x['mode'] == mode]
    return statistics.median(xs) if xs else None
ap293 = sum(1 for x in rows10 if x['kind'] == 'animal_person' and x['speed'] == 293)
nap10 = sum(1 for x in rows10 if x['kind'] == 'animal_person')
fig(id='10', title=f'Plain walking predators barely outrun plain walking prey (median top gait {medk("predator", "plain")} vs {medk("prey", "plain")} ticks/100 tiles); {ap293} of {nap10} animal people share the humanoid 293',

    subtitle='Fastest gait in the species\' main mode (fly for fliers, swim for aquatic, else walk) vs adult mass; lower = faster', form='scatter',
    x='mass', y='speed', series='role', facet='mode', unit='ticks per 100 tiles (GAIT max speed)', log=True, rows=rows10,
    caption=f'Reference: elk 122, deer 137, wolf 149, cougar 195, lion 109 (GAIT:WALK max speed). Median walk top gait, giants: predator {medk("predator", "giant")}, prey {medk("prey", "giant")}. Fastest walker {fastest["id"]} {fastest["speed"]}. {nogait} non-vermin species have no GAIT.',
    notes='GAIT field 3 (max speed) read from resolved raws; min across castes. log applies to mass (x).')

# 11. predator mass vs pack, prey envelope
rows11 = []
prey_pool = [r for r in V if not r['vermin']]
for r in V:
    if r['role'] != 'predator': continue
    s = sp(r['id'])
    n = s.cmid if (s.cmax > 1 and not s.benign) else 1
    eff = s.mass * n ** 0.75
    pmax, pmin = 5.0 * eff, 1e-4 * eff
    diet = S.DIET if hasattr(S, 'DIET') else None
    rows11.append(dict(id=r['id'], guild=r['guild'], kind=r['kind'], mass=s.mass, pack=n, cl_min=s.cmin, cl_max=s.cmax, benign=s.benign,
                       eff_mass=round(eff), prey_max=round(pmax), prey_min=round(pmin, 1)))
# count prey species in envelope by builder DIET guilds (ignores layer/realm/sentience)
sys.path.insert(0, str(ROOT / 'data/eco-desk/v2/guilds'))
try:
    import roster2 as R2
    DIET = R2.DIET
except Exception:
    DIET = {'AL': {'GZ', 'PL', 'SH', 'ML'}, 'AW': {'FC', 'FF', 'PE', 'SH', 'MW', 'WB', 'GZ', 'PL', 'ML'}, 'ML': {'PL', 'GZ', 'SH'},
            'MW': {'FC', 'FF', 'SH', 'PE', 'MW'}, 'RP': {'LB', 'WB', 'RP'}}
for x in rows11:
    d = DIET.get(x['guild'], set())
    x['prey_species_in_range'] = sum(1 for p in prey_pool if p['id'] != x['id'] and p['guild'] in d and not p['sentient']
                                     and x['prey_min'] <= p['mass'] <= x['prey_max'])
packs = sum(1 for x in rows11 if x['pack'] > 1)
zero_prey = sum(1 for x in rows11 if x['prey_species_in_range'] == 0)
fig(id='11', title=f'{packs} of {len(rows11)} predators hunt as packs in the builder; {zero_prey} have no prey species inside their 5x(mass x n^0.75) envelope',
    subtitle='Predator adult mass vs effective pack size n (CLUSTER_NUMBER midpoint, 1 if BENIGN or solitary), with the prey-mass envelope the v2 builder allows', form='scatter',
    x='mass', y='pack', series='guild', unit='cm³ / individuals', log=True, rows=rows11,
    caption='Builder rule (roster2.edge): prey mass / (M x n^0.75) must lie in [1e-4, 5]. prey_species_in_range counts non-sentient, non-vermin wildlife in the predator guild\'s DIET guilds whose mass falls in the envelope; layers, realms and tiers are ignored, so it is an upper bound. Zero-prey predators: ' + ', '.join(x['id'] for x in rows11 if x['prey_species_in_range'] == 0) + ' (animal people of vermin roots keep the root\'s tiny mass).',
    notes='Draw prey_min..prey_max as a vertical range per predator for the envelope view.')

# 12. animal people and giants
rows12 = []
for kind in ('animal_person', 'giant'):
    c12 = Counter()
    for r in V:
        if r['kind'] != kind: continue
        rg = W[r['root']].guild if r['root'] in W else (SP[r['root']].guild if r['root'] in SP else '?')
        c12[(rg, r['guild'])] += 1
    for (rg, og), n in sorted(c12.items()):
        rows12.append(dict(kind=kind, root_guild=rg, own_guild=og, count=n))
nap = sum(1 for r in V if r['kind'] == 'animal_person'); ngi = sum(1 for r in V if r['kind'] == 'giant')
shift_gi = sum(x['count'] for x in rows12 if x['kind'] == 'giant' and x['root_guild'] != x['own_guild'])
shift_ap = sum(x['count'] for x in rows12 if x['kind'] == 'animal_person' and x['root_guild'] != x['own_guild'])
apsav = sum(1 for r in V if r['kind'] == 'animal_person' and sp(r['id']).savage)
fig(id='12', title=f'{nap} animal people and {ngi} giants are {pct(nap + ngi, nV)}% of wildlife; {shift_gi} giants and {shift_ap} animal people change guild from their root',
    subtitle='Animal people and giants per root-animal guild (series = their own computed guild)', form='stackedBar', x='root_guild', y='count',
    series='own_guild', facet='kind', unit='species', rows=rows12,
    caption=f'{apsav} of {nap} animal people carry SAVAGE. Guild change mostly from size (giants cross the 1M cm³ pelagic line or gain LARGE_PREDATOR).',
    notes='root = COPY_TAGS_FROM source. "?" = root not in the wildlife set.')

# 13. vermin
VM = [r for r in V if r['vermin']]
c13 = Counter(r['swv'] for r in VM)
rows13 = [dict(panel='vermin by family (tool SWV class)', category=k, count=v) for k, v in c13.most_common()]
# native gobble tokens
gob_cls = Counter(); gob_cre = Counter(); gob_cons = defaultdict(list)
for r in V:
    for t in vals(r['id'], 'GOBBLE_VERMIN_CLASS'):
        if len(t) > 1: gob_cls[t[1]] += 1; gob_cons[t[1]].append(r['id'])
    for t in vals(r['id'], 'GOBBLE_VERMIN_CREATURE'):
        if len(t) > 1: gob_cre[t[1]] += 1
for cl, n in gob_cls.items():
    members = [r['id'] for r in V if cl in r['classes']]
    rows13.append(dict(panel='native GOBBLE_VERMIN_CLASS', category=cl, count=n, members=len(members), member_ids=members, consumer_ids=sorted(set(gob_cons[cl]))))
for cl, n in gob_cre.items():
    rows13.append(dict(panel='native GOBBLE_VERMIN_CREATURE', category=cl, count=n))
# tool rules (v7.0 VERMIN.GOBBLE_RULES) by SWV class
rule_ct = Counter()
for r in V:
    if r['vermin']: continue
    s = sp(r['id']); m = r['mass']; g = r['guild']; cls = set()
    if g in ('ML', 'PL', 'SH') and m < 10000 and (s.carn or not anyname(r['id'], 'GRAZER')): cls |= {'ground bug', 'soil'}
    if g in ('WB', 'FF', 'FC'): cls |= {'fish'}
    if g == 'RP': cls |= {'small bird', 'small mammal'}
    if g == 'LB': cls |= {'flying insect'}
    if g == 'ML' and r['legless']: cls |= {'small mammal', 'herp'}
    for c in cls: rule_ct[c] += 1
for k in ['ground bug', 'soil', 'flying insect', 'small bird', 'small mammal', 'herp', 'fish', 'other']:
    rows13.append(dict(panel='consumers wired by tool GOBBLE_RULES', category=k, count=rule_ct[k], members=c13.get(k, 0)))
for r in VM:
    rows13.append(dict(panel='vermin species', category=r['swv'], id=r['id'], guild=r['guild'], mass=r['mass']))
fig(id='13', title=f'{len(VM)} vermin species; DF wires only one gobble class natively (EDIBLE_GROUND_BUG: {gob_cls.get("EDIBLE_GROUND_BUG", 0)} consumers, {sum(1 for r in V if "EDIBLE_GROUND_BUG" in r["classes"])} prey species)',
    subtitle='Vermin per tool family (VERMIN.swvClass), native GOBBLE_VERMIN tokens, and consumers the tool\'s GOBBLE_RULES would wire per family', form='bar',
    x='category', y='count', facet='panel', unit='species', rows=rows13,
    caption='Families: ' + ', '.join(f'{k} {v}' for k, v in c13.most_common()) + '. Tool-rule consumers: ' + ', '.join(f'{k} {rule_ct[k]}' for k in rule_ct) + '.',
    notes='swvClass re-implemented from raws (CREATURE_CLASS, VERMIN_*, AQUATIC, IMMOBILE_LAND, FLIER+LAYS_EGGS, AMPHIBIOUS, NOBONES). Guild mass test uses species2 mass (cm³) against GOBBLE_MASS_SMALL 10000. legless = no gait named WALK/RUN.')

# 14. pelagic / deep water
rows14 = [dict(id=r['id'], guild=r['guild'], kind=r['kind'], mass=r['mass'], beach=r['beach'], deep=sp(r['id']).deep) for r in V if r['guild'] in ('PE', 'AW')]
beach = [x for x in rows14 if x['beach']]
beach_all = [(r['id'], r['beach']) for r in V if r['beach']]
fig(id='14', title=f'{sum(1 for x in rows14 if x["guild"] == "PE")} pelagic and {sum(1 for x in rows14 if x["guild"] == "AW")} water-apex species; BEACH_FREQUENCY on {len(beach_all)} ({", ".join(f"{a} {b}" for a, b in beach_all)})',
    subtitle='Adult mass of PE and AW species (log), BEACH_FREQUENCY marked', form='dot', x='guild', y='mass', series='kind', unit='cm³', log=True, rows=rows14,
    caption='PE = aquatic ocean prey >= 1,000,000 cm³ or BEACH_FREQUENCY; AW = LARGE_PREDATOR and AQUATIC/AMPHIBIOUS. deep = aquatic ocean non-vermin >= 1M cm³ or beaching (species2).',
    notes='BEACH_FREQUENCY values are in rows (beach).', refLines=[dict(y=1000000, label='pelagic line 1M cm³')])

# 15a underground depth
rows15a = [dict(id=r['id'], guild=r['guild'], kind=r['kind'], layer=r['layer'], depth_min=r['depth'][0], depth_max=r['depth'][1]) for r in V if r['depth']]
dc = Counter((x['depth_min'], x['depth_max']) for x in rows15a)
fig(id='15a', title=f'{len(rows15a)} species carry UNDERGROUND_DEPTH; the commonest span is {dc.most_common(1)[0][0][0]}:{dc.most_common(1)[0][0][1]} ({dc.most_common(1)[0][1]} species)',
    subtitle='UNDERGROUND_DEPTH min-max per species (1-3 caverns, 4 magma sea, 5 underworld)', form='range', x='id', y='depth_max', series='guild',
    unit='cavern layer', rows=rows15a, caption='Span counts: ' + ', '.join(f'{a}:{b} {n}' for (a, b), n in dc.most_common()) + '. Decides which cavern layer a species can be drawn for (builder cav_mode range).')

# 15b grazing
rows15b = [dict(id=r['id'], guild=r['guild'], std_grazer=r['std_grazer'], grasstrample=r['grasstrample'], mass=r['mass']) for r in V if r['std_grazer'] or r['grasstrample'] is not None]
nsg = sum(1 for r in V if r['std_grazer']); gtv = Counter(r['grasstrample'] for r in V if r['grasstrample'] is not None)
sg_g = Counter(r['guild'] for r in V if r['std_grazer'])
fig(id='15b', title=f'{nsg} species graze (STANDARD_GRAZER), {", ".join(f"{g} {n}" for g, n in sg_g.most_common())}; GRASSTRAMPLE is on {sum(gtv.values())}',
    subtitle='STANDARD_GRAZER carriers and GRASSTRAMPLE values by guild', form='dot', x='guild', y='grasstrample', series='std_grazer', unit='GRASSTRAMPLE',
    rows=rows15b, caption='GRASSTRAMPLE values: ' + ', '.join(f'{k}:{v}' for k, v in sorted(gtv.items())) + '. Grazers starve without grass; the tool\'s vegetation link reads this.',
    notes='Explicit GRAZER:n is absent from 53.16 vanilla raws; STANDARD_GRAZER derives it from size in-game.')

# 15c eggs
rows15c = [dict(id=r['id'], guild=r['guild'], clutch_min=r['clutch_min'], clutch_max=r['clutch_max'], mass=r['mass']) for r in V if r['lays_eggs']]
egg_g = Counter(r['guild'] for r in V if r['lays_eggs'])
fig(id='15c', title=f'{len(rows15c)} species ({pct(len(rows15c), nV)}%) lay eggs; clutches range {min(x["clutch_min"] for x in rows15c if x["clutch_min"])}-{max(x["clutch_max"] for x in rows15c if x["clutch_max"])}',
    subtitle='CLUTCH_SIZE min-max per egg layer, by guild', form='range', x='guild', y='clutch_max', unit='eggs', log=True, rows=rows15c,
    caption='Egg layers by guild: ' + ', '.join(f'{g} {n}' for g, n in egg_g.most_common()) + '.')

# 15d CHILD
rows15d = [dict(id=r['id'], guild=r['guild'], kind=r['kind'], child=r['child']) for r in V if r['child'] is not None]
nochild = sum(1 for r in V if r['child'] is None)
fig(id='15d', title=f'{len(rows15d)} species have a CHILD stage (median {statistics.median(x["child"] for x in rows15d)} years); {nochild} are born adult',
    subtitle='CHILD age (years to adulthood) by guild', form='dot', x='guild', y='child', series='kind', unit='years', rows=rows15d,
    caption='CHILD length sets how long arrivals stay small (and below the size bands) after births on the map.')

# ------------------------------------------------------------------ counts and species list
counts = dict(
    raw_creatures_vanilla=len(ALLV), raw_creatures_extinct=len(ALLX),
    vanilla_with_biome=len(withbiome_v), wildlife=nV,
    excluded_with_biome={c: excl_why[c] for c in excluded},
    by_kind=dict(Counter(r['kind'] for r in V)), by_eco_class=dict(Counter(r['eco'] for r in V)),
    vermin=sum(r['vermin'] for r in V), nonvermin=sum(not r['vermin'] for r in V),
    by_guild={g: gcount[g] for g in GUILD_ORDER}, by_role=dict(role_ct), by_layer={l: layer_ct[l] for l in LAYERS},
    animal_people=nap, giants=ngi, civ_race_flagged=sorted(r['id'] for r in V if r['civ_race']),
    sentient_nonAP=sorted(r['id'] for r in V if r['sentient'] and r['kind'] != 'animal_person'),
    extinct_species=len(XV), extinct_by_guild=dict(Counter(r['guild'] for r in XV)),
    plain_only=sum(1 for r in V if r['kind'] == 'plain'))

grav = sum(1 for r in V if 'GRAVITATE_BODY_SIZE' in RAW[r['id']]['names'])
tbs = {}
import csv as _csv
for _r in _csv.DictReader(open(ROOT / 'data/eco-desk/tokens-by-creature.tsv'), delimiter='\t'): tbs[_r['id']] = float(_r['adult_body_size'] or 0)
mis = [r['id'] for r in V if tbs.get(r['id']) and (r['mass'] / tbs[r['id']] > 2 or tbs[r['id']] / r['mass'] > 2)]
counts['caveats'] = dict(
    animal_person_gravitate=f"{grav} wildlife species (the animal people) carry GRAVITATE_BODY_SIZE:70000 from the ANIMAL_PERSON variation; species2/fixture mass for an animal person is its root's mass, so in-game sizes of small-root animal people (DAMSELFLY_MAN 10 cm3 here) are probably pulled toward 70,000 cm3. Figures 2, 10, 11, 12 use species2 mass as given.",
    mass_source_disagreement=f"{len(mis)} species where species2 mass (tool fixture, live game x10 scale) and census raw adult_body_size differ by more than 2x: tiny vermin roots floor at 10 cm3 vs raw 1-3, and their giants read 10x raw (GIANT_DAMSELFLY 2,000,070 vs 200,007), which moves them from medium to large; multi-caste ANT_MAN reads 20,000 raw (last caste) vs 10 fixture.",
    mass_disagreement_ids=mis)
species = [{k: r[k] for k in ('id', 'source', 'kind', 'root', 'guild', 'role', 'layer', 'mass', 'freq', 'pop_min', 'pop_max', 'cl_min', 'cl_max',
                              'top_speed', 'speed_mode', 'vermin', 'animal_person', 'giant', 'sentient', 'civ_race', 'scav', 'swv', 'eco')} for r in V]

doc = dict(
    generated=datetime.datetime.now().isoformat(timespec='seconds') + ' by raws_report.py (scratchpad); DF 53.16 vanilla raws, files only',
    filter=('Wildlife = every creature in data/vanilla/vanilla_creatures/objects with a BIOME token, classed natural/mythic/unliving by the tool fixture '
            '(fixtures/species-model.tsv MODEL.audit), resolved through COPY_TAGS_FROM / APPLY_CREATURE_VARIATION / caste walk (eco-desk/census.py), '
            'guilded by v2/guilds/species2.py. Excluded: MEGABEAST/SEMIMEGABEAST (8: worldgen-placed, arrive as attacks) and IMMOBILE sponges (SPONGE, GIANT_SPONGE; SPONGE_MAN is kept). '
            'Generated night creatures, forgotten beasts, titans and demons have no vanilla raw and are absent by construction. '
            'Animal people (kind=animal_person) and giants (kind=giant) are included and flagged; the 9 SUBTERRANEAN_ANIMAL_PEOPLES entity races '
            'have BIOME and spawn wild in caverns, so they are kept and flagged civ_race. Vermin are included as guilds V*. '
            'Extinct raws (vanilla_creatures_extinct, 200) appear only as a facet of figure 2 and in counts.'),
    counts=counts, guilds={g: S.GUILDS[g] for g in GUILD_ORDER}, figures=FIG, species=species)
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(doc, indent=1, default=lambda o: sorted(o) if isinstance(o, (set, frozenset)) else str(o)))
print('wrote', OUT, OUT.stat().st_size)
print(json.dumps(counts, indent=1, default=str)[:3000])
for f in FIG: print(f['id'], len(f['rows']), '|', f['title'])
