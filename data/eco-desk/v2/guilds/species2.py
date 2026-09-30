#!/usr/bin/env python3
"""v2 species table: raw-derived facts, guilds, apex boost, layers, realms (files only; DF 53.16 vanilla + extinct raws).

Inputs (all read-only):
  ../../tokens-by-creature.tsv   census.py output, 967 creatures, inheritance resolved (token value 'all' / 'some:..' / 0)
  ../../../fixtures/species-model.tsv  the tool's own MODEL.audit (eco class, role, habitat, mass)
  ../../roster/bizarre.tsv       v1 BIZARRE score (caverns)
  realms2.py                     realm table (EXTERNAL real-world knowledge; DF raws carry no geography)
Writes species2.tsv (one row per creature in the universe) when run as a script.

Token effects come from ../../wiki-tokens.md and ../../findings.md, never from token names.
"""
import csv, re
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
ECO = HERE.parent.parent                      # data/eco-desk
FIXT = ECO.parent / 'fixtures' / 'species-model.tsv'

# ------------------------------------------------------------------ DF biome expansion (biome_type order; same as v1)
B = ['MOUNTAIN','GLACIER','TUNDRA','SWAMP_TEMPERATE_FRESHWATER','SWAMP_TEMPERATE_SALTWATER','MARSH_TEMPERATE_FRESHWATER',
     'MARSH_TEMPERATE_SALTWATER','SWAMP_TROPICAL_FRESHWATER','SWAMP_TROPICAL_SALTWATER','SWAMP_MANGROVE','MARSH_TROPICAL_FRESHWATER',
     'MARSH_TROPICAL_SALTWATER','FOREST_TAIGA','FOREST_TEMPERATE_CONIFER','FOREST_TEMPERATE_BROADLEAF','FOREST_TROPICAL_CONIFER',
     'FOREST_TROPICAL_DRY_BROADLEAF','FOREST_TROPICAL_MOIST_BROADLEAF','GRASSLAND_TEMPERATE','SAVANNA_TEMPERATE','SHRUBLAND_TEMPERATE',
     'GRASSLAND_TROPICAL','SAVANNA_TROPICAL','SHRUBLAND_TROPICAL','DESERT_BADLAND','DESERT_ROCK','DESERT_SAND','OCEAN_TROPICAL',
     'OCEAN_TEMPERATE','OCEAN_ARCTIC','POOL_TEMPERATE_FRESHWATER','POOL_TEMPERATE_BRACKISHWATER','POOL_TEMPERATE_SALTWATER',
     'POOL_TROPICAL_FRESHWATER','POOL_TROPICAL_BRACKISHWATER','POOL_TROPICAL_SALTWATER','LAKE_TEMPERATE_FRESHWATER',
     'LAKE_TEMPERATE_BRACKISHWATER','LAKE_TEMPERATE_SALTWATER','LAKE_TROPICAL_FRESHWATER','LAKE_TROPICAL_BRACKISHWATER',
     'LAKE_TROPICAL_SALTWATER','RIVER_TEMPERATE_FRESHWATER','RIVER_TEMPERATE_BRACKISHWATER','RIVER_TEMPERATE_SALTWATER',
     'RIVER_TROPICAL_FRESHWATER','RIVER_TROPICAL_BRACKISHWATER','RIVER_TROPICAL_SALTWATER','SUBTERRANEAN_WATER',
     'SUBTERRANEAN_CHASM','SUBTERRANEAN_LAVA']
def _r(a, b): return B[a:b + 1]
SETS = {'ALL_MAIN': _r(0, 29) + _r(36, 41), 'ANY_LAND': _r(0, 26), 'ANY_OCEAN': _r(27, 29), 'ANY_LAKE': _r(36, 41),
        'ANY_TEMPERATE_LAKE': _r(36, 38), 'ANY_TROPICAL_LAKE': _r(39, 41), 'ANY_RIVER': _r(42, 47), 'ANY_TEMPERATE_RIVER': _r(42, 44),
        'ANY_TROPICAL_RIVER': _r(45, 47), 'ANY_POOL': _r(30, 35), 'NOT_FREEZING': _r(3, 26),
        'ANY_TEMPERATE': _r(3, 6) + _r(13, 14) + _r(18, 20), 'ANY_TROPICAL': _r(7, 11) + _r(15, 17) + _r(21, 23),
        'ANY_FOREST': _r(12, 17), 'ANY_SHRUBLAND': [B[20], B[23]], 'ANY_GRASSLAND': [B[18], B[21]], 'ANY_SAVANNA': [B[19], B[22]],
        'ANY_TEMPERATE_FOREST': _r(13, 14), 'ANY_TROPICAL_FOREST': _r(15, 17), 'ANY_TEMPERATE_BROADLEAF': _r(3, 6) + [B[14]] + _r(18, 20),
        'ANY_TROPICAL_BROADLEAF': _r(7, 11) + _r(16, 17) + _r(21, 23), 'ANY_WETLAND': _r(3, 11), 'ANY_TEMPERATE_WETLAND': _r(3, 6),
        'ANY_TROPICAL_WETLAND': _r(7, 11), 'ANY_TROPICAL_MARSH': _r(10, 11), 'ANY_TEMPERATE_MARSH': _r(5, 6),
        'ANY_TROPICAL_SWAMP': _r(7, 9), 'ANY_TEMPERATE_SWAMP': _r(3, 4), 'ANY_DESERT': _r(24, 26), 'TAIGA': ['FOREST_TAIGA'],
        'MOUNTAINS': ['MOUNTAIN']}
def expand(biomes):
    out = set()
    for b in biomes.split(','):
        if b: out |= set(SETS.get(b, [b]))
    return frozenset(out)
def is_water(b): return b.startswith(('OCEAN', 'POOL', 'LAKE', 'RIVER'))
def is_wetland(b): return b.startswith(('SWAMP', 'MARSH'))
def is_sub(b): return b.startswith('SUBTERRANEAN')
SEASONS = ['SPRING', 'SUMMER', 'AUTUMN', 'WINTER']

# DF biome-token groups (every token DF uses, grouped the way the realm tables report them)
BIOME_GROUP = {}
for b in B:
    if b in ('TUNDRA', 'GLACIER'): g = 'polar land'
    elif b == 'FOREST_TAIGA': g = 'taiga'
    elif b in ('FOREST_TEMPERATE_CONIFER', 'FOREST_TEMPERATE_BROADLEAF'): g = 'temperate forest'
    elif b.startswith('FOREST_TROPICAL'): g = 'tropical forest'
    elif b in ('GRASSLAND_TEMPERATE', 'SAVANNA_TEMPERATE', 'SHRUBLAND_TEMPERATE'): g = 'temperate grass/savanna/shrub'
    elif b in ('GRASSLAND_TROPICAL', 'SAVANNA_TROPICAL', 'SHRUBLAND_TROPICAL'): g = 'tropical grass/savanna/shrub'
    elif b.startswith('DESERT'): g = 'desert'
    elif is_wetland(b) and 'TEMPERATE' in b: g = 'temperate wetland'
    elif is_wetland(b): g = 'tropical wetland'
    elif b == 'MOUNTAIN': g = 'mountain'
    elif b == 'OCEAN_ARCTIC': g = 'ocean arctic'
    elif b.startswith('OCEAN'): g = 'ocean ' + b.split('_')[1].lower()
    elif b.startswith(('LAKE', 'RIVER')): g = ('lake ' if b.startswith('LAKE') else 'river ') + b.split('_')[1].lower() + ' ' + b.split('_')[2].lower().replace('water', '')
    elif b.startswith('POOL'): g = 'pool (vermin only)'
    else: g = 'subterranean ' + b.split('_')[1].lower()
    BIOME_GROUP[b] = g

# ------------------------------------------------------------------ helpers over census values
def has(r, t): return r.get(t) not in (0, '0', None, '')
def allc(r, t): return r.get(t) == 'all' or (has(r, t) and not str(r.get(t)).startswith('some:'))
def num(x, d=0):
    try: return int(str(x).split('|')[0].split('=')[-1])
    except Exception: return d

# Q2 recommended scavenger set (DESCRIPTION text or CURIOUSBEAST_EATER; labels only, S2: scavenging = tool walk + delete)
SCAV = {'BIRD_VULTURE', 'BIRD_BUZZARD', 'BIRD_KEA', 'BIRD_RAVEN', 'JACKAL', 'BEAR_BLACK', 'BEAR_GRIZZLY', 'BEAR_POLAR', 'BEAR_SLOTH',
        'RACCOON', 'COATI', 'HONEY BADGER', 'MANDRILL', 'MACAQUE_RHESUS', 'GRAY_LANGUR', 'CAPUCHIN', 'SHARK_MAKO_LONGFIN', 'FLESH_BALL',
        'DRUNIAN', 'RAT_GIANT', 'RAT_LARGE', 'MOLE_GIANT', 'MOLE_DOG_NAKED'}
ROLE_OVERRIDE_PRED = {'ORCA', 'GIANT_ORCA', 'GIANT_CUTTLEFISH'}      # the tool's curated overrides (SW:982)

# BIZARRE score (v1 bizarre.py); v1 tertile cut q1<=3, q2<=4 (bizarre-summary.txt)
BIZ = {}
for i, line in enumerate(open(ECO / 'roster' / 'bizarre.tsv')):
    p = line.rstrip('\n').split('\t')
    if i == 0: hdr = p; continue
    d = dict(zip(hdr, p)); BIZ[d['id']] = int(d['score'])
def biz_band(s): return 1 if s <= 3 else 2 if s <= 4 else 3

# FANCIFUL (creature-level token, not in the census columns): scanned from the raws when available
FANCIFUL = set()
_RAW = Path.home() / 'Library/Application Support/CrossOver/Bottles/Win10/drive_c/Program Files (x86)/Steam/steamapps/common/Dwarf Fortress/data/vanilla'
try:
    for f in list((_RAW / 'vanilla_creatures' / 'objects').glob('creature_*.txt')):
        cur = None
        for m in re.finditer(r'\[([^\[\]]+)\]', f.read_text(encoding='latin-1', errors='replace')):
            t = m.group(1).split(':')
            if t[0] == 'CREATURE': cur = t[1]
            elif t[0] == 'FANCIFUL' and cur: FANCIFUL.add(cur)
except Exception:
    pass

# ------------------------------------------------------------------ species record
@dataclass
class Sp:
    id: str; source: str; kind: str; root: str; eco: str; role_tool: str; habitat_tool: str
    vermin: bool; lr: bool; flier: bool; aquatic: bool; amphib: bool
    lp: bool; benign: bool; benign_some: bool; carn: bool; bonecarn: bool; grazer: bool; meander: bool
    cb: bool; scav: bool; prone_rage: bool
    mass: int; cmin: int; cmax: int; loose: bool; freq: int; freq_raw: str
    biomes: frozenset; biome_tokens: str; depth: tuple; seasons: frozenset
    sentient: bool; giant: bool; savage: bool; good: bool; evil: bool; fanciful: bool; period: str; beach: bool
    vclass: str = ''; bizarre: int = -1
    guild: str = ''; apex: bool = False; apex_why: str = ''; deep: bool = False; realms: tuple = ()
    @property
    def diet_pred(self): return self.carn or self.bonecarn or self.id in ROLE_OVERRIDE_PRED
    @property
    def cmid(self): return max(1, (self.cmin + self.cmax) // 2)
    @property
    def ocean(self): return any(b.startswith('OCEAN') for b in self.biomes)
    @property
    def fresh(self): return any(b.startswith(('LAKE', 'RIVER')) for b in self.biomes)
    @property
    def cavern(self): return bool(self.biomes & {'SUBTERRANEAN_CHASM', 'SUBTERRANEAN_WATER'})
    @property
    def surface(self): return any(not is_sub(b) for b in self.biomes)

PERIODS = ['CAMBRIAN', 'ORDOVICIAN', 'SILURIAN', 'DEVONIAN', 'CARBONIFEROUS', 'PERMIAN', 'TRIASSIC', 'JURASSIC', 'CRETACEOUS', 'CENOZOIC']
ERA = {'CAMBRIAN': 'Paleozoic', 'ORDOVICIAN': 'Paleozoic', 'SILURIAN': 'Paleozoic', 'DEVONIAN': 'Paleozoic', 'CARBONIFEROUS': 'Paleozoic',
       'PERMIAN': 'Paleozoic', 'TRIASSIC': 'Mesozoic', 'JURASSIC': 'Mesozoic', 'CRETACEOUS': 'Mesozoic', 'CENOZOIC': 'Cenozoic'}

def _vclass(r, flier, aquatic, classes):
    if has(r, 'VERMIN_SOIL_COLONY'): return 'VC'
    if flier:
        if r['id'].startswith(('BIRD_', 'SPARROW')) or r['id'] == 'BAT' or 'MAMMAL' in classes: return 'VB'
        return 'VI'
    if has(r, 'VERMIN_FISH') or aquatic: return 'VF'
    if has(r, 'AMPHIBIOUS') and not any(not is_water(b) and not is_sub(b) for b in expand(r['biomes'])): return 'VF'
    return 'VG'

def load(include_classes=('natural',)):
    fx = {r['token']: r for r in csv.DictReader(open(FIXT), delimiter='\t')}
    out = {}
    for r in csv.DictReader(open(ECO / 'tokens-by-creature.tsv'), delimiter='\t'):
        f = fx.get(r['id'])
        if not r['biomes'] or not f: continue
        if f['eco'] not in include_classes: continue
        if has(r, 'IMMOBILE') and r['IMMOBILE'] == 'all': continue
        classes = r['creature_classes'].split(',')
        cl = r['cluster_number']
        cmin, cmax = (int(cl.split(':')[0]), int(cl.split(':')[1])) if cl else (1, 1)
        dep = tuple(int(x) for x in str(r['UNDERGROUND_DEPTH']).split(':')) if has(r, 'UNDERGROUND_DEPTH') else (0, 0)
        flier, aquatic = has(r, 'FLIER'), has(r, 'AQUATIC')
        vermin = r['is_vermin'] == '1'
        period = next((c for c in classes if c in PERIODS), '')
        s = Sp(id=r['id'], source=r['source'], kind=r['kind'] or 'plain', root=r['copy_from'] or r['id'], eco=f['eco'],
               role_tool=f['role'], habitat_tool=f['habitat'], vermin=vermin, lr=has(r, 'LARGE_ROAMING'), flier=flier,
               aquatic=aquatic, amphib=has(r, 'AMPHIBIOUS'), lp=has(r, 'LARGE_PREDATOR'), benign=allc(r, 'BENIGN'),
               benign_some=has(r, 'BENIGN') and not allc(r, 'BENIGN'), carn=has(r, 'CARNIVORE'), bonecarn=has(r, 'BONECARN'),
               grazer=has(r, 'STANDARD_GRAZER') or has(r, 'GRAZER'), meander=has(r, 'MEANDERER'),
               cb=has(r, 'CURIOUSBEAST_EATER') or has(r, 'CURIOUSBEAST_ITEM') or has(r, 'CURIOUSBEAST_GUZZLER'),
               scav=r['id'] in SCAV, prone_rage=has(r, 'PRONE_TO_RAGE'),
               mass=int(f['mass'] or r['adult_body_size'] or 1), cmin=cmin, cmax=cmax, loose=has(r, 'LOOSE_CLUSTERS'),
               freq=num(r['frequency_eff'], 50), freq_raw=r['frequency'] or '(50)', biomes=expand(r['biomes']),
               biome_tokens=r['biomes'], depth=dep, seasons=frozenset(x for x in SEASONS if not has(r, 'NO_' + x)),
               sentient=r['kind'] == 'animal_person' or has(r, 'CAN_SPEAK') or has(r, 'CAN_LEARN'),
               giant=r['kind'] == 'giant' or r['id'].startswith('GIANT_'), savage=r['SAVAGE'] == '1', good=r['GOOD'] == '1',
               evil=r['EVIL'] == '1', fanciful=r['id'] in FANCIFUL, period=period, beach=has(r, 'BEACH_FREQUENCY'))
        s.bizarre = BIZ.get(s.id, -1)
        if vermin: s.vclass = _vclass(r, flier, aquatic, classes)
        out[s.id] = s
    for s in out.values():
        s.guild = guild_of(s)
        s.apex, s.apex_why = apex_of(s)
        s.deep = s.aquatic and s.ocean and (s.mass >= 1_000_000 or s.beach) and not s.vermin
    try:
        from realms2 import realm_of
        for s in out.values(): s.realms = realm_of(s, out)
    except ImportError:
        pass
    return out

# ------------------------------------------------------------------ guilds (Q6 scheme, extended; precedence = order of tests)
GUILDS = {
    'AL': 'apex hunter, land (G1): LARGE_PREDATOR, not AQUATIC/AMPHIBIOUS/FLIER',
    'AW': 'water apex (G2): LARGE_PREDATOR and (AQUATIC or AMPHIBIOUS)',
    'RP': 'raptor (G4): FLIER and (BONECARN or CARNIVORE or LARGE_PREDATOR)',
    'ML': 'ground mesocarnivore (G3): CARNIVORE/BONECARN, not LP, not FLIER, not AQUATIC',
    'MW': 'water mesopredator (new): AQUATIC, CARNIVORE/BONECARN or tool override, not LP',
    'GZ': 'grazer herd (G6): STANDARD_GRAZER',
    'SH': 'shore / semiaquatic prey (G8): AMPHIBIOUS, or all-water BIOME and not AQUATIC/FLIER',
    'PE': 'pelagic prey (G9): AQUATIC ocean, adult >= 1,000,000 cm3 or BEACH_FREQUENCY',
    'FC': 'coastal / reef fish (G10): AQUATIC ocean, smaller',
    'FF': 'freshwater / cave-water fish (G11): AQUATIC, lake/river/subterranean water, no ocean',
    'WB': 'waterbird (G12): FLIER with an ocean/lake/river/pool BIOME, not carnivore',
    'LB': 'land bird (G13): FLIER, not carnivore, no water BIOME',
    'PL': 'other land prey (G7): everything else that walks',
    'VG': 'vermin: ground', 'VF': 'vermin: fish / aquatic', 'VC': 'vermin: soil colony',
    'VB': 'vermin: flying bird / bat', 'VI': 'vermin: flying insect',
}
PRED_GUILDS = {'AL', 'AW', 'RP', 'ML', 'MW'}
APEX_GUILDS = {'AL', 'AW'}
def guild_of(s):
    if s.vermin: return s.vclass
    water_only = s.biomes and all(is_water(b) or b == 'SUBTERRANEAN_WATER' for b in s.biomes)
    if s.lp and not s.flier and (s.aquatic or s.amphib): return 'AW'
    if s.flier and (s.diet_pred or s.lp): return 'RP'
    if s.lp: return 'AL'
    if s.diet_pred and s.aquatic: return 'MW'
    if s.diet_pred: return 'ML'
    if s.grazer: return 'GZ'
    if s.flier: return 'WB' if any(is_water(b) for b in s.biomes) else 'LB'
    if s.aquatic:
        if s.ocean: return 'PE' if (s.mass >= 1_000_000 or s.beach) else 'FC'
        return 'FF'
    if s.amphib or water_only: return 'SH'
    return 'PL'

# ------------------------------------------------------------------ APEX boost (user rule 2)
BOOST_GUILDS = {'AL', 'AW', 'ML', 'RP'}          # apex hunter land, water apex, ground mesocarnivore, raptor
def apex_of(s):
    """IF (guild in {AL, AW, ML, RP} OR CARNIVORE) AND (giant OR adult >= 1,000,000 cm3) THEN apex.
    CARNIVORE is read as CARNIVORE or BONECARN (wiki: BONECARN 'implies CARNIVORE') or the tool's curated predator override
    (ORCA, GIANT_ORCA, GIANT_CUTTLEFISH: BENIGN, no diet token). Native apex = AL/AW without the boost."""
    if s.vermin: return False, ''
    diet = s.carn or s.bonecarn
    g_ok = s.guild in BOOST_GUILDS
    big = s.giant or s.mass >= 1_000_000
    why = []
    if g_ok: why.append('guild ' + s.guild)
    if diet: why.append('CARNIVORE' if s.carn else 'BONECARN')
    if not diet and s.id in ROLE_OVERRIDE_PRED: why.append('tool override')
    if big: why.append('giant' if s.giant else 'size %.1fM' % (s.mass / 1e6))
    if (g_ok or diet or s.id in ROLE_OVERRIDE_PRED) and big: return True, '+'.join(why)
    if s.guild in APEX_GUILDS: return True, 'native ' + s.guild
    return False, ''

def boosted(s): return s.apex and not s.apex_why.startswith('native')

def tier(s):
    """Trophic rank used for antisymmetric edges: apex 3 > meso/raptor 2 > prey 1 > bird vermin 0.5 > other vermin 0."""
    if s.vermin: return 0.5 if s.vclass == 'VB' else 0
    if s.apex: return 3
    if s.guild in PRED_GUILDS: return 2
    return 1

COLS = ['id', 'source', 'kind', 'root', 'guild', 'apex', 'apex_why', 'deep', 'vermin', 'lr', 'mass', 'cluster', 'loose', 'freq',
        'freq_raw', 'lp', 'benign', 'carn', 'bonecarn', 'grazer', 'flier', 'aquatic', 'amphib', 'sentient', 'giant', 'savage',
        'good', 'evil', 'fanciful', 'period', 'cb', 'scav', 'seasons', 'depth', 'bizarre', 'realms', 'biome_tokens']
def row(s):
    d = {c: getattr(s, c, '') for c in COLS}
    d['cluster'] = '%d:%d' % (s.cmin, s.cmax); d['seasons'] = ','.join(x[:2] for x in SEASONS if x in s.seasons)
    d['depth'] = '%d:%d' % s.depth; d['realms'] = ','.join(s.realms)
    return {k: (int(v) if isinstance(v, bool) else v) for k, v in d.items()}

if __name__ == '__main__':
    S = load()
    with open(HERE / 'species2.tsv', 'w') as f:
        w = csv.DictWriter(f, COLS, delimiter='\t'); w.writeheader()
        for s in sorted(S.values(), key=lambda z: z.id): w.writerow(row(s))
    from collections import Counter
    print(len(S), 'species (natural class, with BIOME, not IMMOBILE)')
    print(Counter((s.source, s.kind) for s in S.values()))
    print(Counter(s.guild for s in S.values()))
