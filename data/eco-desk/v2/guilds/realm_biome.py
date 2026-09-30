#!/usr/bin/env python3
"""Realms x DF biomes: itemised correspondence, per-cell rosters by guild (incl. extinct), gaps, proposed fills, and
DF-world-feature realm mappings (SAVAGE, GOOD/EVIL, FANCIFUL, REAL_WORLD_EXTINCT periods). Writes realms.md, realm_biome.tsv.
Realm membership is EXTERNAL knowledge (realms2.py); nothing geographic is read from the raws.
"""
import csv
from pathlib import Path
from collections import Counter, defaultdict
from dataclasses import replace
from species2 import load, B, boosted, is_water, is_wetland
from realms2 import REALMS, REALM_NAME
import roster2
from roster2 import build, Cfg, EMBARKS, SEASONS

HERE = Path(__file__).resolve().parent
S = load()                                             # natural class (what the tool manages)
ALL = load(include_classes=('natural', 'mythic', 'unliving', 'mega', 'generated', 'unclassified'))

# ------------------------------------------------------------------ biome-token groups used in the tables
GROUPS = [
    ('polar land', ['TUNDRA', 'GLACIER']), ('taiga', ['FOREST_TAIGA']),
    ('temperate forest', ['FOREST_TEMPERATE_CONIFER', 'FOREST_TEMPERATE_BROADLEAF']),
    ('temperate grass/savanna/shrub', ['GRASSLAND_TEMPERATE', 'SAVANNA_TEMPERATE', 'SHRUBLAND_TEMPERATE']),
    ('temperate wetland', ['SWAMP_TEMPERATE_FRESHWATER', 'SWAMP_TEMPERATE_SALTWATER', 'MARSH_TEMPERATE_FRESHWATER', 'MARSH_TEMPERATE_SALTWATER']),
    ('tropical forest', ['FOREST_TROPICAL_CONIFER', 'FOREST_TROPICAL_DRY_BROADLEAF', 'FOREST_TROPICAL_MOIST_BROADLEAF']),
    ('tropical grass/savanna/shrub', ['GRASSLAND_TROPICAL', 'SAVANNA_TROPICAL', 'SHRUBLAND_TROPICAL']),
    ('tropical wetland', ['SWAMP_TROPICAL_FRESHWATER', 'SWAMP_TROPICAL_SALTWATER', 'SWAMP_MANGROVE', 'MARSH_TROPICAL_FRESHWATER', 'MARSH_TROPICAL_SALTWATER']),
    ('desert', ['DESERT_BADLAND', 'DESERT_ROCK', 'DESERT_SAND']), ('mountain', ['MOUNTAIN']),
    ('ocean arctic', ['OCEAN_ARCTIC']), ('ocean temperate', ['OCEAN_TEMPERATE']), ('ocean tropical', ['OCEAN_TROPICAL']),
    ('lake/river temperate fresh', ['LAKE_TEMPERATE_FRESHWATER', 'RIVER_TEMPERATE_FRESHWATER']),
    ('lake/river temperate brackish/salt', ['LAKE_TEMPERATE_BRACKISHWATER', 'LAKE_TEMPERATE_SALTWATER', 'RIVER_TEMPERATE_BRACKISHWATER', 'RIVER_TEMPERATE_SALTWATER']),
    ('lake/river tropical fresh', ['LAKE_TROPICAL_FRESHWATER', 'RIVER_TROPICAL_FRESHWATER']),
    ('lake/river tropical brackish/salt', ['LAKE_TROPICAL_BRACKISHWATER', 'LAKE_TROPICAL_SALTWATER', 'RIVER_TROPICAL_BRACKISHWATER', 'RIVER_TROPICAL_SALTWATER']),
    ('pools (vermin only)', [b for b in B if b.startswith('POOL')]),
    ('subterranean', ['SUBTERRANEAN_CHASM', 'SUBTERRANEAN_WATER', 'SUBTERRANEAN_LAVA']),
]
GROUP_OF = {b: g for g, bs in GROUPS for b in bs}
assert set(GROUP_OF) == set(B), set(B) - set(GROUP_OF)
def kind_of(g):
    if g.startswith('ocean'): return 'ocean'
    if g.startswith('lake'): return 'fresh'
    if g.startswith('pools'): return 'pool'
    if g == 'subterranean': return 'sub'
    return 'land'

# ------------------------------------------------------------------ realm <-> DF biome correspondence (EXTERNAL; climates present)
Y = 'native'
RB = {  # realm -> set of groups whose climate exists in that realm today
 'AUS': {'temperate forest', 'temperate grass/savanna/shrub', 'temperate wetland', 'tropical forest', 'tropical grass/savanna/shrub',
         'tropical wetland', 'desert', 'mountain', 'ocean temperate', 'ocean tropical', 'lake/river temperate fresh',
         'lake/river temperate brackish/salt', 'lake/river tropical fresh', 'lake/river tropical brackish/salt'},
 'NZ': {'temperate forest', 'temperate grass/savanna/shrub', 'temperate wetland', 'mountain', 'polar land', 'ocean temperate',
        'lake/river temperate fresh'},
 'AFR': {'temperate grass/savanna/shrub', 'temperate forest', 'tropical forest', 'tropical grass/savanna/shrub', 'tropical wetland',
         'desert', 'mountain', 'ocean temperate', 'ocean tropical', 'lake/river tropical fresh', 'lake/river tropical brackish/salt'},
 'MAD': {'tropical forest', 'tropical grass/savanna/shrub', 'tropical wetland', 'mountain', 'ocean tropical', 'lake/river tropical fresh'},
 'NEO': {'temperate forest', 'temperate grass/savanna/shrub', 'temperate wetland', 'tropical forest', 'tropical grass/savanna/shrub',
         'tropical wetland', 'desert', 'mountain', 'polar land', 'ocean temperate', 'ocean tropical', 'lake/river temperate fresh',
         'lake/river tropical fresh', 'lake/river tropical brackish/salt'},
 'NEA': {'polar land', 'taiga', 'temperate forest', 'temperate grass/savanna/shrub', 'temperate wetland', 'tropical wetland', 'desert',
         'mountain', 'ocean arctic', 'ocean temperate', 'ocean tropical', 'lake/river temperate fresh', 'lake/river temperate brackish/salt'},
 'PAL': {'polar land', 'taiga', 'temperate forest', 'temperate grass/savanna/shrub', 'temperate wetland', 'desert', 'mountain',
         'ocean arctic', 'ocean temperate', 'lake/river temperate fresh', 'lake/river temperate brackish/salt'},
 'IND': {'tropical forest', 'tropical grass/savanna/shrub', 'tropical wetland', 'temperate forest', 'mountain', 'polar land', 'desert',
         'ocean tropical', 'lake/river tropical fresh', 'lake/river tropical brackish/salt'},
 'ARC': {'polar land', 'taiga', 'mountain', 'ocean arctic', 'lake/river temperate fresh'},
 'ANT': {'polar land', 'ocean arctic'},
 'OCE': {'ocean arctic', 'ocean temperate', 'ocean tropical'},
}
TABLE_REALMS = ['AUS', 'NZ', 'AFR', 'MAD', 'NEO', 'NEA', 'PAL', 'IND', 'ARC', 'ANT', 'OCE']
GROUP_NAMES = [g for g, _ in GROUPS if g not in ('pools (vermin only)', 'subterranean')]

# ------------------------------------------------------------------ guild codes for coverage
def code(s):
    if s.vermin: return 'v'
    if s.apex: return 'A'
    return {'ML': 'M', 'MW': 'M', 'RP': 'R', 'GZ': 'G', 'PL': 'P', 'LB': 'P', 'SH': 'S', 'FC': 'W', 'FF': 'W', 'PE': 'W', 'WB': 'B'}[s.guild]
REQUIRED = {'land': ['A', 'M', 'G|P', 'R'], 'ocean': ['A', 'W', 'S'], 'fresh': ['W|v', 'S'], 'pool': [], 'sub': []}
ORDER = 'AMRGPSWBT'

def members(realm, group, sets=('plain',), src=('vanilla',), pool=S):
    bs = set(dict(GROUPS)[group])
    out = []
    for s in pool.values():
        if s.source not in src or s.kind not in sets: continue
        if not (s.biomes & bs): continue
        ok = {realm, 'COS'} | ({'OCE'} if kind_of(group) == 'ocean' else set())   # Q9: COS always; OCE on ocean
        if not set(s.realms) & ok: continue
        out.append(s)
    return out

def cover(ms):
    c = Counter(code(s) for s in ms)
    c['T'] = sum(1 for s in ms if (s.cb or s.scav) and not s.vermin)
    return c

def cov_str(c):
    parts = ['%s%d' % (k, c[k]) for k in ORDER if c.get(k)]
    if c.get('v'): parts.append('v%d' % c['v'])
    return ' '.join(parts) if parts else '—'

def gaps(c, kind):
    out = []
    for req in REQUIRED[kind]:
        if not any(c.get(k) for k in req.split('|')): out.append(req.replace('|v', ''))
    return out

def fills(realm, group, gap, kind):
    """Candidate fills for one missing guild code, in order of preference."""
    bs = set(dict(GROUPS)[group])
    def ok(s): return not s.vermin and s.kind == 'plain' and (code(s) in gap.split('|') or (gap == 'W' and s.vclass == 'VF'))
    out = []
    # 1 same realm, extinct, raws list this biome (DF places it natively on a SAVAGE embark)
    x = [s for s in S.values() if ok(s) and s.source == 'extinct' and realm in s.realms and s.biomes & bs]
    if x: out.append('extinct same realm, biome listed: ' + ', '.join(sorted(s.id for s in x)[:6]))
    # 2 same realm, vanilla, other biome (cross-biome import: untested in DF, Q9)
    x = [s for s in S.values() if ok(s) and s.source == 'vanilla' and realm in s.realms and kind_of(GROUP_OF[next(iter(s.biomes))]) == kind]
    if x: out.append('same realm, other biome (cross-biome import): ' + ', '.join(sorted(s.id for s in x)[:6]))
    x = [s for s in S.values() if ok(s) and s.source == 'extinct' and realm in s.realms and not (s.biomes & bs)]
    if x: out.append('extinct same realm, other biome: ' + ', '.join(sorted(s.id for s in x)[:6]))
    # 3 cosmopolitan with the biome
    x = [s for s in S.values() if ok(s) and ('COS' in s.realms or (kind == 'ocean' and 'OCE' in s.realms)) and s.biomes & bs and s.source == 'vanilla']
    if x: out.append('COS/OCE with biome: ' + ', '.join(sorted(s.id for s in x)[:6]))
    # 4 analog from another realm that lists the biome (DF-native placement)
    x = [s for s in S.values() if ok(s) and s.source == 'vanilla' and s.biomes & bs and realm not in s.realms]
    if x: out.append('other-realm analog, biome listed: ' + ', '.join(sorted(s.id for s in x)[:5]) + ('…' if len(x) > 5 else ''))
    return out or ['none in DF (natural class)']

P = []
P.append('# Realms x DF biomes: correspondence, rosters by guild, gaps, fills, and DF-feature realm mappings\n')
P.append('Realm membership is **external real-world knowledge** (realms2.py: Q9 table for vanilla, fossil locality for extinct, '
         'root animal for giants and animal people). DF places a species on any landmass whose BIOME it lists, around a random '
         'per-species epicenter (wiki FREQUENCY); it has no realms. The extinct creatures\' period class "currently has no effect on how '
         'or where they appear" (wiki, Extinction). Scope below: the tool\'s natural class (894 creatures incl. giants, animal people, '
         'extinct). Guild codes: **A** apex (LARGE_PREDATOR land/water, plus the apex boost), **M** meso (ML/MW), **R** raptor, '
         '**G** grazer, **P** other land prey / land bird, **S** shore / semiaquatic, **W** fish (coastal, pelagic, fresh), **B** waterbird, '
         '**T** thief/scavenger tag (CURIOUSBEAST_* or Q2 text), **v** vermin (stock only).\n')

# ---- 1. correspondence
P.append('## 1. Realm <-> DF biome itemization\n')
P.append('Every DF biome token, its table group, whether each realm has that climate today (external), and how many natural '
         'non-vermin DF species of that realm list the token (vanilla / +extinct). "·" = the realm does not have that biome; '
         '"0" = the realm has it but DF gives it no species.\n')
head = ['DF biome token', 'group'] + TABLE_REALMS
rows = []
for b in B:
    g = GROUP_OF[b]
    row = [b, g]
    for R in TABLE_REALMS:
        v = sum(1 for s in S.values() if not s.vermin and s.kind == 'plain' and s.source == 'vanilla' and b in s.biomes and R in s.realms)
        e = sum(1 for s in S.values() if not s.vermin and s.kind == 'plain' and s.source == 'extinct' and b in s.biomes and R in s.realms)
        native = g in RB.get(R, set())
        row.append(('%d' % v + ('+%d' % e if e else '')) if native else ('·' if not (v or e) else '(%d%s)' % (v, '+%d' % e if e else '')))
    rows.append(row)
P.append('| ' + ' | '.join(head) + ' |'); P.append('|' + '---|' * len(head))
for r in rows: P.append('| ' + ' | '.join(r) + ' |')
P.append('\n"(n)" = DF has species of that realm on a biome the realm does not have today (DF places by biome only; e.g. a Nearctic '
         'species whose BIOME list is a broad ANY_ token).\n')

# ---- 2. per realm x group rosters (vanilla natural, then + extinct, then + giants)
P.append('## 2. Guild coverage per realm x biome group\n')
P.append('Each cell: vanilla natural non-giant (DF-native, non-savage) coverage; then `+ext` = what same-realm extinct species that list '
         'the biome add; then `+gi` = what giants of this realm\'s own animals add (giants of COS roots, e.g. giant insects and raptors, exist in every realm on a savage embark and are not counted) (giants, animal people and extinct are all SAVAGE: savage embarks only). '
         'Gaps (bold) = a required guild missing where the realm has that climate. Required: land = A, M, G or P, R; ocean = A, W, S; '
         'fresh water = W (unit or vermin fish), S. COS species count in every realm and OCE species in every ocean cell (Q9).\n')
head = ['realm'] + GROUP_NAMES
P.append('| ' + ' | '.join(head) + ' |'); P.append('|' + '---|' * len(head))
TSV = []
gap_list = []
for R in TABLE_REALMS:
    row = [R]
    for g in GROUP_NAMES:
        kind = kind_of(g)
        v = members(R, g)
        e = members(R, g, src=('extinct',))
        gi = [s for s in members(R, g, sets=('giant',)) if R in s.realms]   # giants of this realm's own animals (COS giants: note)
        cv, ce = cover(v), cover(v + e)
        native = g in RB.get(R, set())
        if not native and not v and not e:
            row.append('·'); continue
        gp = gaps(cv, kind) if native else []
        gpe = gaps(ce, kind) if native else []
        cell = cov_str(cv)
        add = Counter(ce) - Counter(cv)
        if add: cell += ' +ext ' + cov_str(add)
        addg = cover(v + e + gi) - ce
        if addg: cell += ' +gi ' + cov_str(addg)
        if gp: cell += ' **gap ' + ','.join(gp) + ('→%s' % (','.join(gpe) if gpe else 'filled by ext') if gp != gpe else '') + '**'
        if not native: cell = '(' + cell + ')'
        row.append(cell)
        TSV.append([R, g, int(native), cov_str(cv), cov_str(ce), ','.join(gp), ','.join(gpe),
                    ' '.join(sorted(s.id for s in v if not s.vermin)), ' '.join(sorted(s.id for s in e if not s.vermin)),
                    ' '.join(sorted(s.id for s in gi))])
        for x in gp: gap_list.append((R, g, x, kind, x not in gpe))
    P.append('| ' + ' | '.join(row) + ' |')
with open(HERE / 'realm_biome.tsv', 'w') as f:
    w = csv.writer(f, delimiter='\t')
    w.writerow(['realm', 'group', 'realm_has_climate', 'coverage_vanilla', 'coverage_with_extinct', 'gaps_vanilla', 'gaps_with_extinct',
                'vanilla_members', 'extinct_members', 'giant_members'])
    w.writerows(TSV)
P.append('\nFull member lists per cell: `realm_biome.tsv`.\n')

# ---- 3. gaps and fills
P.append('## 3. Gaps and proposed fills\n')
P.append('Fill order: (1) same-realm extinct species whose raws list the biome (DF-native on a savage embark; no cross-biome write); '
         '(2) same-realm vanilla species from another biome (cross-biome import: the tool must write a population the raws do not '
         'admit; **untested**, Q9); (3) same-realm extinct from another biome; (4) cosmopolitan species with the biome; (5) an analog '
         'from another realm that lists the biome (DF-native, breaks the realm).\n')
P.append('| realm | biome group | missing | extinct closes it | fills (in order) |'); P.append('|---|---|---|---|---|')
for R, g, x, kind, closed in gap_list:
    P.append('| %s | %s | %s | %s | %s |' % (R, g, x, 'yes' if closed else 'no', ' ; '.join(fills(R, g, x, kind))))
n_gap = len(gap_list); n_closed = sum(1 for t in gap_list if t[4])
P.append('\n%d gaps over %d realm x biome cells where the realm has the climate; same-realm extinct species close %d of them.\n'
         % (n_gap, sum(1 for t in TSV if t[2]), n_closed))

# ---- 4. Australasia
P.append('## 4. Australasia: the large-land-predator gap\n')
aus_land = [s for s in S.values() if 'AUS' in s.realms and not s.vermin and s.kind == 'plain' and code(s) in 'AM' and not s.aquatic]
P.append('Vanilla AUS land predators (natural, non-giant): ' + ', '.join('%s (%s, %dk, %s%s)' % (s.id, s.guild, s.mass // 1000, 'LP' if s.lp else 'not LP', ', apex' if s.apex else '')
                                                            for s in sorted(aus_land, key=lambda z: -z.mass) if s.source == 'vanilla') + '.\n')
P.append('Extinct AUS predators: ' + ', '.join('%s (%s, %dk, %s; BIOME %s; SAVAGE=%d)' % (s.id, s.guild, s.mass // 1000, 'LP' if s.lp else 'not LP', s.biome_tokens, s.savage)
                                             for s in aus_land if s.source == 'extinct') + '.\n')
big_other = sorted([s for s in S.values() if s.source == 'extinct' and s.kind == 'plain' and code(s) == 'A' and not s.aquatic], key=lambda z: -z.mass)
P.append('Other extinct land apex that DF could place in AUS-climate biomes (breaks the realm): ' +
         ', '.join('%s %.2fM [%s]' % (s.id, s.mass / 1e6, '/'.join(s.realms)) for s in big_other) + '.\n')
P.append('Reading: DINGO (20k, pack 3:12) is the only vanilla Australasian LP on land besides the saltwater crocodile (wetland/river). '
         'The extinct set supplies two genuinely Australian predators: CENOZOIC_THYLACINE (19k, LP, BONECARN; temperate forest/shrub/grass) '
         'and CENOZOIC_MEGALANIA (450k, LP, CARNIVORE; tropical dry forest, temperate shrub/grass). MEGALANIA is the large apex the realm '
         'lacks; with a pack-adjusted size preference it takes KANGAROO/EMU/WOMBAT/DIPROTODON-sized prey. Both are SAVAGE, so DF itself '
         'places them only in savage regions; a calm AUS embark would need the tool to add them (Add invasive admits them wherever their '
         'BIOME matches, SW:2541). Neither is boosted (450k < 1M, not giant): MEGALANIA is a native apex by LARGE_PREDATOR.\n')

# ---- 5. DF-feature realm mappings
P.append('## 5. Realms from DF world features instead of geography\n')
P.append('DF has three creature-side world features: SAVAGE ("only in savage biomes"), GOOD ("only in good biomes"), EVIL ("only in evil '
         'biomes"); SAVAGE cannot combine with GOOD/EVIL on a creature, but a region can be savage AND good ("joyous wilds") or savage AND '
         'evil ("terrifying"). FANCIFUL marks mythical creatures (worldgen/civ flavour; no spawn rule on the wiki). REAL_WORLD_EXTINCT and '
         'the period classes (CAMBRIAN ... CENOZOIC) are labels with no placement effect (wiki). Untagged species appear in every region, '
         'so a savage region = untagged + SAVAGE-tagged.\n')
def mset(pred, pool=ALL): return {k for k, s in pool.items() if pred(s)}
MAP = {
    'M0 calm/neutral (no SAVAGE/GOOD/EVIL tag)': mset(lambda s: not s.savage and not s.good and not s.evil),
    'M1 SAVAGE-tagged only (what a savage region adds)': mset(lambda s: s.savage),
    'M2 savage region (M0 + M1)': mset(lambda s: not s.good and not s.evil),
    'M3 savage x GOOD (joyous wilds: M2 + GOOD)': mset(lambda s: not s.evil),
    'M4 savage x EVIL (terrifying: M2 + EVIL)': mset(lambda s: not s.good),
    'M5 FANCIFUL': mset(lambda s: s.fanciful),
    'M6a Paleozoic (CAMBRIAN..PERMIAN)': mset(lambda s: s.period in ('CAMBRIAN', 'ORDOVICIAN', 'SILURIAN', 'DEVONIAN', 'CARBONIFEROUS', 'PERMIAN')),
    'M6b Mesozoic (TRIASSIC..CRETACEOUS)': mset(lambda s: s.period in ('TRIASSIC', 'JURASSIC', 'CRETACEOUS')),
    'M6c Cenozoic': mset(lambda s: s.period == 'CENOZOIC'),
    'M7 SAVAGE natural non-sentient (M1 minus animal people/civ races)': mset(lambda s: s.savage and not s.sentient and s.eco == 'natural'),
}
P.append('### 5a. What each mapping admits (all classes; the tool manages only the natural class)\n')
P.append('| mapping | total | natural class | giants | animal people / sentient | extinct | mythic/other class | AUS-rooted share | largest single realm (share) |')
P.append('|---|---|---|---|---|---|---|---|---|')
for name, ids in MAP.items():
    X = [ALL[i] for i in ids]
    nat = [s for s in X if s.eco == 'natural']
    rc = Counter(r for s in nat if not s.vermin for r in s.realms)
    tot_r = sum(1 for s in nat if not s.vermin) or 1
    top = rc.most_common(1)[0] if rc else ('-', 0)
    P.append('| %s | %d | %d | %d | %d | %d | %d | %s | %s %d%% |' % (
        name, len(X), len(nat), sum(s.giant for s in X), sum(s.sentient for s in X), sum(s.source == 'extinct' for s in X),
        sum(s.eco != 'natural' for s in X), '%d%%' % round(100 * sum(1 for s in nat if not s.vermin and 'AUS' in s.realms) / tot_r),
        top[0], round(100 * top[1] / tot_r)))
P.append('')
m1_plain = sorted(k for k in MAP['M1 SAVAGE-tagged only (what a savage region adds)'] if ALL[k].kind == 'plain' and ALL[k].source == 'vanilla')
P.append('M1 non-giant, non-person vanilla members: ' + ', '.join(m1_plain) + '. Every other M1 member is a giant, an animal person or extinct.\n')
P.append('GOOD: ' + ', '.join(sorted(k for k, s in ALL.items() if s.good)) + ' (classes: ' +
         ', '.join('%s %d' % kv for kv in Counter(s.eco for s in ALL.values() if s.good).items()) + '). EVIL: ' +
         ', '.join(sorted(k for k, s in ALL.items() if s.evil)) + ' (classes: ' + ', '.join('%s %d' % kv for kv in Counter(s.eco for s in ALL.values() if s.evil).items()) + '). '
         'FANCIFUL: ' + ', '.join(sorted(k for k, s in ALL.items() if s.fanciful)) + ' (natural: %d).\n' % sum(1 for s in ALL.values() if s.fanciful and s.eco == 'natural'))

# 5b: coverage by biome group of the natural part of each mapping
P.append('### 5b. Guild coverage per biome group (natural class of each mapping; non-vermin)\n')
maps_b = ['M0 calm/neutral (no SAVAGE/GOOD/EVIL tag)', 'M1 SAVAGE-tagged only (what a savage region adds)', 'M7 SAVAGE natural non-sentient (M1 minus animal people/civ races)',
          'M6a Paleozoic (CAMBRIAN..PERMIAN)', 'M6b Mesozoic (TRIASSIC..CRETACEOUS)', 'M6c Cenozoic']
P.append('| mapping | ' + ' | '.join(GROUP_NAMES) + ' |'); P.append('|---|' + '---|' * len(GROUP_NAMES))
for name in maps_b:
    ids = MAP[name]
    row = [name.split(' ')[0]]
    for g in GROUP_NAMES:
        bs = set(dict(GROUPS)[g])
        ms = [S[i] for i in ids if i in S and S[i].biomes & bs]
        c = cover(ms)
        gp = gaps(c, kind_of(g))
        row.append(cov_str(c) + (' **gap ' + ','.join(gp) + '**' if gp else ''))
    P.append('| ' + ' | '.join(row) + ' |')
P.append('')

# 5c: build rosters under each natural mapping (land/flying/ocean over the v1 embarks) and score coherence
P.append('### 5c. Rosters built under each mapping (roster2, v1 embarks, land + flying + ocean, 4 seasons x 10 seeds)\n')
P.append('Coherence = the web closes (apex present, no isolated node, pack AND herd on DF-actable edges) and is not dominated by '
         'sentients or giants. `savage=True` so SAVAGE species are admissible; the mapping is then the whitelist.\n')
def score(allow, realm=None):
    cfg = replace(Cfg(), savage=True, allow=frozenset(allow) if allow is not None else None, realm=realm, label='map')
    R = []
    for e in roster2.V1_EMBARKS:
        for l in ('land', 'flying', 'ocean'):
            for s in SEASONS:
                for sd in range(1, 11):
                    r = build(e, l, s, sd, cfg)
                    if r['roster']: R.append(r)
    if not R: return None
    n = len(R)
    def f(pred): return '%d%%' % round(100 * sum(1 for r in R if pred(r)) / n)
    def act(r): return {(a, b) for a, b, w, k, ac in r['edges'] if ac in ('df', 'df?')}
    def packherd(r):
        A = act(r); ids = r['roster']; SP = roster2.SP
        p = any(not SP[x].vermin and SP[x].cmax > 1 and any(a == x for a, b in A) for x in ids if r['slot'][x] in ('APX', 'ML', 'MW', 'RP'))
        h = any(SP[x].cmax > 1 and any(b == x for a, b in A) for x in ids if r['slot'][x] in ('GZ', 'PL', 'SH', 'FC', 'FF', 'PE', 'LB', 'WB'))
        return p and h
    nodes = sum(len(r['roster']) for r in R)
    SP = roster2.SP
    Ld = [r for r in R if r['layer'] == 'land']
    land_apex = '%d%% of %d' % (round(100 * sum(1 for r in Ld if any(r['slot'][x] == 'APX' for x in r['roster'])) / len(Ld)), len(Ld)) if Ld else '-'
    return [n, '%.1f' % (nodes / n), f(lambda r: any(r['slot'][x] == 'APX' for x in r['roster'])), land_apex, f(lambda r: r['isolated']),
            f(packherd), '%d%%' % round(100 * sum(1 for r in R for x in r['roster'] if SP[x].sentient) / nodes),
            '%d%%' % round(100 * sum(1 for r in R for x in r['roster'] if SP[x].giant) / nodes),
            '%d%%' % round(100 * sum(1 for r in R for x in r['roster'] if SP[x].source == 'extinct') / nodes)]
P.append('| mapping | non-empty rosters | mean size | apex present (all layers) | land rosters with apex | isolated | pack AND herd (actable) | sentient share | giant share | extinct share |')
P.append('|---|---|---|---|---|---|---|---|---|---|')
nat = lambda ids: {i for i in ids if i in roster2.SP}
for name in maps_b + ['M2 savage region (M0 + M1)']:
    sc = score(nat(MAP[name]))
    P.append('| %s | %s |' % (name, ' | '.join(map(str, sc)) if sc else 'no roster'))
calm = {k for k, s in roster2.SP.items() if not s.savage}
ext = {k for k, s in roster2.SP.items() if s.source == 'extinct' and not s.sentient}
for R in ('AUS', 'NZ', 'AFR', 'MAD', 'NEO', 'NEA', 'PAL', 'IND', 'ARC', 'ANT'):
    for lab, allow in (('calm embark (DF-native, no SAVAGE species)', calm),
                       ('calm + same-realm extinct added by the tool (the fills)', calm | ext),
                       ('savage embark (+ own giants, animal people, extinct)', None)):
        sc = score(allow, realm=(R,))
        P.append('| realm %s, %s | %s |' % (R, lab, ' | '.join(map(str, sc)) if sc else 'no roster'))
P.append('')
(HERE / 'realms.md').write_text('\n'.join(P) + '\n')
print('gaps', n_gap, 'closed by extinct', n_closed)
