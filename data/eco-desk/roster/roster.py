#!/usr/bin/env python3
"""Roster / food-web prototype for seasonal-wildlife (files only; DF 53.16 vanilla raws).

build(biome_set, layer, season, seed, cfg) is a pure function of its arguments (plus the static raw data).
Every interpretation choice is in rules.md; the knobs are the Cfg fields.
"""
import json, math, random, hashlib
from dataclasses import dataclass, field, replace
from pathlib import Path
from collections import defaultdict, Counter

HERE = Path(__file__).resolve().parent
ECO = HERE.parent
FIX = Path('/Users/nathanielcannon/Claude/Projects/DwarfCron/data/fixtures/species-model.tsv')

# ------------------------------------------------------------------ biome expansion (DF biome_type order, eco/w/lib.py)
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

EMBARKS = {   # realistic embark biome sets (surface)
    'TEMP_GRASS_FOREST': {'GRASSLAND_TEMPERATE', 'FOREST_TEMPERATE_BROADLEAF', 'FOREST_TEMPERATE_CONIFER'},
    'TROP_SAVANNA_SHRUB': {'SAVANNA_TROPICAL', 'SHRUBLAND_TROPICAL'},
    'TAIGA_TUNDRA': {'FOREST_TAIGA', 'TUNDRA'},
    'DESERT': {'DESERT_SAND', 'DESERT_ROCK', 'DESERT_BADLAND'},
    'TROP_WETLAND': {'SWAMP_TROPICAL_FRESHWATER', 'MARSH_TROPICAL_FRESHWATER', 'POOL_TROPICAL_FRESHWATER'},
    'LAKE_RIVER': {'GRASSLAND_TEMPERATE', 'FOREST_TEMPERATE_BROADLEAF', 'LAKE_TEMPERATE_FRESHWATER', 'RIVER_TEMPERATE_FRESHWATER'},
    'OCEAN_SHORE': {'GRASSLAND_TEMPERATE', 'SHRUBLAND_TEMPERATE', 'OCEAN_TEMPERATE'},
}
SURFACE_LAYERS = ['land', 'flying', 'water']
UNDER_LAYERS = ['cav1', 'cav2', 'cav3', 'deep']
SEASONS = ['SPRING', 'SUMMER', 'AUTUMN', 'WINTER']

# ------------------------------------------------------------------ classes
PRED_CLASSES = ['giant_pred', 'large_pred', 'medium_pred', 'small_pred']
PREY_CLASSES = ['giant_large_prey', 'medium_prey', 'small_prey']
VERMIN_CLASSES = ['v_ground_fish', 'v_colony', 'v_flybird', 'v_flyother']
CLASSES = PRED_CLASSES + PREY_CLASSES + VERMIN_CLASSES
CAPS = {'giant_pred': 1, 'large_pred': 1, 'medium_pred': 1, 'small_pred': 1, 'giant_large_prey': 1, 'medium_prey': 1,
        'small_prey': 2, 'v_ground_fish': 3, 'v_colony': 1, 'v_flybird': 1, 'v_flyother': 1}
CAP_MIN = dict(CAPS, v_ground_fish=1, v_colony=0)       # lenient reading of "1-3" and "0-1"
# step 7 frequency scale (user: ~1x,3x,4x,5x,6x,7x,8x,9x for 9 classes; 10 extrapolated for flying vermin, colony = 9)
FREQ = {'giant_pred': 1, 'large_pred': 3, 'giant_large_prey': 4, 'medium_pred': 5, 'medium_prey': 6, 'small_pred': 7,
        'small_prey': 8, 'v_ground_fish': 9, 'v_colony': 9, 'v_flybird': 10, 'v_flyother': 10}
SIZE_CAT = {'vermin': 0, 'small': 1, 'medium': 2, 'large': 3}

@dataclass(frozen=True)
class Cfg:
    cls: str = 'size'            # 'size' = tool bands only; 'tag+size' = LARGE_PREDATOR -> large_pred; 'lp+1' = LP moves up one band
    hv_mode: str = 'abs'         # 'abs' = absolute HV test; 'nogiant' = giants are not HV (all giants carry PETVALUE 500)
    A: str = 'lp'                # who counts as PREDATOR in rule A (eater and protected target): 'lp' | 'role'
    D: str = 'tag_and_size'      # large predator for rule D: 'tag_and_size' | 'tag' | 'size'
    F: str = 'cluster'           # pack: 'cluster' (cluster max>1) | 'lp_cluster' (LP and cluster max>1) | 'none'
    E_large_max: int = 2         # max prey size cat for large/giant preds (2 = "medium to small" as written)
    B_small_extra: int = 0       # extra size cats small preds may eat beyond vermin (0 = rule B as written)
    cav: str = 'depth+ceiling'   # cavern candidate rule: 'depth' | 'score' | 'depth+ceiling'
    weight: str = 'uniform'      # random picks: 'uniform' | 'frequency' (DF FREQUENCY)
    ap: bool = True              # include animal people / sentient LR wildlife
    hv_fallback: bool = False    # step 3: allow a high-value pick when no non-HV candidate exists
    size: str = 'band'           # 'band' = rules B/E/F size windows; 'ratio' = the tool's eats() mass test (take >= need) for unit prey
    seed_linked: bool = False    # fix: step 1 draws only species with >=1 relation in the pool
    sentient_pred: bool = True   # fix: sentients (animal people, civ races) are never predators
    peer: bool = False           # fix: a predator may eat another predator only if at least 2x its mass (the tool's peer rule)
    step6: str = 'bridge'        # 'bridge' = add a bridging species within caps | 'none'
    benign_filter: bool = False  # fix: predator slots only for non-BENIGN species (DF acts on the relation)
    label: str = 'baseline'

# ------------------------------------------------------------------ data
def _load():
    D = json.load(open(ECO / 'census.json'))
    F = json.load(open(HERE / 'features.json'))
    FX = {}
    for i, line in enumerate(open(FIX)):
        p = line.rstrip('\n').split('\t')
        if i == 0: hdr = p; continue
        FX[p[0]] = dict(zip(hdr, p))
    return D, F, FX

def has(r, t):
    v = r.get(t)
    return v not in (0, '0', None, '')
def allc(r, t): return r.get(t) == 'all' or (has(r, t) and not str(r.get(t)).startswith('some:'))

@dataclass
class Sp:
    id: str; kind: str; vermin: bool; role: str; band: str; mass: int; lp: bool; benign: bool; sentient: bool
    flier: bool; aquatic: bool; amphib: bool; lr: bool; biomes: frozenset; depth: tuple; seasons: frozenset
    cmax: int; cmid: int; freq: int; hv: bool; hv_why: str; vclass: str; bizarre: int = 0; eco: str = ''

def load_species():
    D, F, FX = _load()
    out = {}
    for r in D:
        fx = FX.get(r['id'])
        if r['source'] != 'vanilla' or not r['biomes'] or not fx or fx['eco'] != 'natural': continue
        f = F[r['id']]
        if f['IMMOBILE']: continue
        mass = int(fx['mass'] or r['adult_body_size'] or 0)
        cl = r['cluster_number']; cmax = int(cl.split(':')[1]) if cl else 1
        cmid = max(1, (int(cl.split(':')[0]) + cmax) // 2) if cl else 1
        dep = tuple(int(x) for x in str(r['UNDERGROUND_DEPTH']).split(':')) if has(r, 'UNDERGROUND_DEPTH') else (0, 0)
        seas = frozenset(s for s in SEASONS if not has(r, 'NO_' + s))
        sentient = r['kind'] == 'animal_person' or has(r, 'CAN_SPEAK') or has(r, 'CAN_LEARN')
        pv = int(str(r['PETVALUE']).split('|')[0].split('=')[-1]) if has(r, 'PETVALUE') else 0
        why = []
        if pv >= 200: why.append('PETVALUE%d' % pv)
        if has(r, 'TRAINABLE_WAR') or has(r, 'TRAINABLE'): why.append('war')
        if mass >= 1_000_000: why.append('parts:size')
        if set(f['valuable_mats']) & {'IVORY', 'PEARL', 'SILK'}: why.append('parts:' + '/'.join(sorted(set(f['valuable_mats']) & {'IVORY', 'PEARL', 'SILK'})))
        vermin = bool(r['is_vermin'])
        flier = has(r, 'FLIER')
        vclass = ''
        if vermin:
            if has(r, 'VERMIN_SOIL_COLONY'): vclass = 'v_colony'
            elif flier and (f['stance'] <= 2 or 'MAMMAL' in r['creature_classes']): vclass = 'v_flybird'
            elif flier: vclass = 'v_flyother'
            else: vclass = 'v_ground_fish'
        out[r['id']] = Sp(id=r['id'], kind=r['kind'], vermin=vermin, role=fx['role'], band=fx['band'], mass=mass,
                          lp=has(r, 'LARGE_PREDATOR'), benign=allc(r, 'BENIGN'), sentient=sentient, flier=flier,
                          aquatic=has(r, 'AQUATIC'), amphib=has(r, 'AMPHIBIOUS'), lr=has(r, 'LARGE_ROAMING'),
                          biomes=expand(r['biomes']), depth=dep, seasons=seas, cmax=cmax, cmid=cmid,
                          freq=int(r['frequency_eff'] or 50), hv=bool(why), hv_why=','.join(why), vclass=vclass, eco=fx['eco'])
    return out

SPECIES = load_species()
try:
    _BZ = {l.split('\t')[0]: int(l.split('\t')[-3]) for l in open(HERE / 'bizarre.tsv').read().splitlines()[1:]}
    for k, v in _BZ.items():
        if k in SPECIES: SPECIES[k].bizarre = v
    _CUT = json.load(open(HERE / 'bizarre-cut.json'))
except FileNotFoundError:
    _BZ, _CUT = {}, {'q1': 99, 'q2': 99}

# ------------------------------------------------------------------ classification
def tclass(s, cfg):
    if s.vermin: return s.vclass
    if s.role == 'predator':
        if (cfg.benign_filter and s.benign) or (not cfg.sentient_pred and s.sentient): return {'large': 'giant_large_prey', 'medium': 'medium_prey'}.get(s.band, 'small_prey') if s.kind != 'giant' else 'giant_large_prey'
        if s.kind == 'giant': return 'giant_pred'
        if s.band == 'large' or (cfg.cls == 'tag+size' and s.lp): return 'large_pred'
        if cfg.cls == 'lp+1' and s.lp: return {'small': 'medium_pred', 'medium': 'large_pred'}[s.band]
        return s.band + '_pred'
    if s.kind == 'giant' or s.band == 'large': return 'giant_large_prey'
    return s.band + '_prey'

def size_cat(s): return 0 if s.vermin else SIZE_CAT[s.band]

def is_pack(s, cfg):
    if cfg.F == 'none': return False
    if cfg.F == 'lp_cluster': return s.lp and s.cmax > 1
    return s.cmax > 1

def a_predator(s, cfg):
    """Rule A 'PREDATOR' status (used for both the privileged eater and the protected target)."""
    if s.vermin: return False
    return s.lp if cfg.A == 'lp' else s.role == 'predator'

def d_large(s, cfg):
    if s.vermin: return False
    big = s.band == 'large'
    return {'tag_and_size': s.lp and big, 'tag': s.lp, 'size': big and s.role == 'predator'}[cfg.D]

def eats(p, x, cfg, why=False):
    """Rules A-F. Returns bool (or (bool, reason) with why=True). Layer/season/co-presence handled by the caller."""
    def r(ok, msg): return (ok, msg) if why else ok
    if p.id == x.id: return r(False, 'self')
    cp, cx = tclass(p, cfg), tclass(x, cfg)
    # rule C: bird/mammal flying vermin eat flying-insect vermin; no other vermin eats
    if p.vermin:
        return r(cp == 'v_flybird' and cx == 'v_flyother', 'C')
    if cp not in PRED_CLASSES: return r(False, 'not a predator')
    giant = cp == 'giant_pred'
    # prey side protections
    if cx == 'giant_pred': return r(False, 'A:giant pred uneatable')
    if a_predator(x, cfg) and not (giant or a_predator(p, cfg)): return r(False, 'A')
    if x.sentient and not (giant or d_large(p, cfg)): return r(False, 'D')
    if cfg.peer and tclass(x, cfg) in PRED_CLASSES and p.mass < 2 * x.mass: return r(False, 'A(peer)')
    # size windows (B, E) with pack +1 (F)
    sx = size_cat(x)
    if cfg.size == 'ratio' and not x.vermin:
        if cp == 'small_pred' and cfg.B_small_extra == 0: return r(False, 'B')
        g = max(1, p.cmid) if is_pack(p, cfg) else 1
        take = p.mass * g ** 0.75 * (1.5 if p.lp else 1.0)
        need = x.mass * (0.9 if x.cmax > 1 else 0.6)
        return r(take >= need, 'ok' if take >= need else 'E(ratio)')
    if cp == 'small_pred': lo, hi = 0, 0 + cfg.B_small_extra          # B
    elif cp == 'medium_pred': lo, hi = 1, 2                             # E
    else: lo, hi = 1, cfg.E_large_max                                   # E (large and giant)
    if is_pack(p, cfg): hi += 1                                         # F
    if not (lo <= sx <= hi): return r(False, 'B' if cp == 'small_pred' else 'E')
    return r(True, 'ok')

def is_eater(s, cfg): return (not s.vermin and tclass(s, cfg) in PRED_CLASSES) or (s.vermin and s.vclass == 'v_flybird')

# ------------------------------------------------------------------ pools
def layer_of(s, bset, layer, cfg):
    """True if species s belongs to `layer` for embark biome set bset (surface) - caverns/deep ignore bset."""
    if layer in ('cav1', 'cav2', 'cav3'):
        if not (s.biomes & {'SUBTERRANEAN_CHASM', 'SUBTERRANEAN_WATER'}): return False
        L = int(layer[-1])
        in_depth = s.depth[0] <= L <= s.depth[1]
        if cfg.cav == 'depth': return in_depth
        sc = s.bizarre
        band = 1 if sc <= _CUT['q1'] else 2 if sc <= _CUT['q2'] else 3
        if cfg.cav == 'score': return band == L and s.depth[1] >= 1
        return in_depth and band <= L                                   # depth+ceiling
    if layer == 'deep':
        return 'SUBTERRANEAN_LAVA' in s.biomes or (s.depth[0] <= 4 <= s.depth[1] and s.depth[1] >= 1)
    hit = s.biomes & bset
    if not hit: return False
    land = {b for b in hit if not is_water(b)}
    water = {b for b in hit if is_water(b)}
    if s.vermin:
        if layer == 'flying': return s.flier
        if s.flier: return False
        if s.vclass == 'v_ground_fish' and (s.aquatic or s.id.startswith('FISH') or not land):
            return layer == 'water' and bool(water or s.amphib)
        return layer == 'land' and bool(land)
    if not s.lr: return False
    if layer == 'flying': return s.flier
    if s.flier: return False
    if layer == 'land': return bool(land) and not s.aquatic
    if layer == 'water':
        lr_water = {b for b in water if not b.startswith('POOL')}  # LARGE_ROAMING cannot spawn in pools (wiki)
        if s.aquatic: return bool(lr_water)
        if s.amphib: return bool(lr_water) or any(is_wetland(b) for b in land)
    return False

_POOL = {}
def pool(bkey, layer, season, cfg):
    k = (bkey, layer, season, cfg.cav, cfg.ap)
    if k not in _POOL:
        bset = EMBARKS.get(bkey, set())
        ps = [s for s in SPECIES.values() if layer_of(s, bset, layer, cfg) and season in s.seasons and (cfg.ap or not s.sentient)]
        _POOL[k] = sorted(ps, key=lambda s: s.id)
    return _POOL[k]

# ------------------------------------------------------------------ build
def _rng(*parts):
    h = hashlib.sha256('|'.join(map(str, parts)).encode()).hexdigest()
    return random.Random(int(h[:16], 16))

def _w(s, cfg): return max(1, s.freq) if cfg.weight == 'frequency' else 1

def _pick(rng, cands, cfg, anchor=None, bset=None):
    if not cands: return None
    if anchor is not None and bset:   # shared biome (within the embark) preferred
        sh = [c for c in cands if c.biomes & anchor.biomes & bset]
        if sh: cands = sh
    ws = []
    for c in cands:
        w = _w(c, cfg)
        if anchor is not None and not c.vermin and not anchor.vermin and c.mass and anchor.mass:
            # relative size: prey ~0.4x predator (lognormal, sd 1.5 in ln) - direction handled by caller via anchor role
            ratio = c.mass / anchor.mass if is_eater(anchor, cfg) else anchor.mass / c.mass
            w *= math.exp(-((math.log(ratio / 0.4)) ** 2) / (2 * 1.5 ** 2)) + 1e-6
        ws.append(w)
    return rng.choices(cands, weights=ws, k=1)[0]

_REL = {}
def relations(bkey, layer, season, cfg):
    """(pool, prey_of, eaters_of) - the full A-F relation over the pool, cached per pool and config."""
    k = (bkey, layer, season, cfg)
    if k not in _REL:
        P = pool(bkey, layer, season, cfg)
        prey_of = {p.id: frozenset(x.id for x in P if eats(p, x, cfg)) for p in P}
        eaters_of = defaultdict(set)
        for p, xs in prey_of.items():
            for x in xs: eaters_of[x].add(p)
        _REL[k] = (P, prey_of, {x.id: frozenset(eaters_of.get(x.id, ())) for x in P})
    return _REL[k]

def build(bkey, layer, season, seed, cfg=Cfg(), max_iter=50):
    rng = _rng(bkey, layer, season, seed, cfg.weight)
    P, prey_of, eaters_of = relations(bkey, layer, season, cfg)
    byid = {s.id: s for s in P}
    bset = EMBARKS.get(bkey, set()) if layer in SURFACE_LAYERS else None
    cls = {s.id: tclass(s, cfg) for s in P}
    count = Counter(); roster = []; ids = set(); tree = set(); log = []
    def room(s): return count[cls[s.id]] < CAPS[cls[s.id]]
    def add(s, how):
        roster.append(s); ids.add(s.id); count[cls[s.id]] += 1; log.append((s.id, how))
    res = {'bkey': bkey, 'layer': layer, 'season': season, 'seed': seed, 'cfg': cfg.label, 'pool_n': len(P),
           'pool_by_class': dict(Counter(cls.values()))}
    nonv = [s for s in P if not s.vermin]
    ishv = (lambda s: s.hv) if cfg.hv_mode == 'abs' else (lambda s: s.hv and s.kind != 'giant')
    hv = [s for s in nonv if ishv(s)]
    if cfg.seed_linked:
        nonv = [s for s in nonv if prey_of[s.id] or eaters_of[s.id]]
        hv = [s for s in hv if prey_of[s.id] or eaters_of[s.id]]
    res['hv_pool_n'] = len(hv)
    if hv: seed_sp = _pick(rng, hv, cfg); res['seed_kind'] = 'hv'
    elif nonv: seed_sp = _pick(rng, nonv, cfg); res['seed_kind'] = 'no_hv_fallback'
    elif P: seed_sp = _pick(rng, P, cfg); res['seed_kind'] = 'vermin_only'
    else:
        res.update(seed_kind='empty', roster=[], edges_tree=0, edges_all=0, edges_final=[], terminated='empty', classes={},
                   isolated_pre6=[], isolated_final=[], step6={}, components=0, step8=False, step8_pack=False, step8_herd=False,
                   edges_unit=0, edges_df_feasible=0, unfilled={k: CAPS[k] for k in CLASSES}, unfilled_pool_has={k: 0 for k in CLASSES},
                   step2_ok=False, iterations=0, freq={}, log=[], seed_sp=None, seed_class=None)
        return res
    add(seed_sp, 'seed')
    res['seed_sp'] = seed_sp.id; res['seed_class'] = cls[seed_sp.id]
    # step 2
    if is_eater(seed_sp, cfg):
        c = [byid[x] for x in prey_of[seed_sp.id] if x not in ids and room(byid[x])]
        pick = _pick(rng, sorted(c, key=lambda z: z.id), cfg, seed_sp, bset)
        if pick: add(pick, 'step2 prey of seed'); tree.add((seed_sp.id, pick.id))
    else:
        c = [byid[x] for x in eaters_of[seed_sp.id] if x not in ids and room(byid[x])]
        pick = _pick(rng, sorted(c, key=lambda z: z.id), cfg, seed_sp, bset)
        if pick: add(pick, 'step2 predator of seed'); tree.add((pick.id, seed_sp.id))
    res['step2_ok'] = pick is not None
    res['step2_list_n'] = len(c)
    # steps 3-4
    it = 0; terminated = None
    def caps_full(): return all(count[k] >= CAPS[k] for k in CLASSES)
    def caps_full_lenient(): return all(count[k] >= CAP_MIN[k] for k in CLASSES)
    while it < max_iter:
        it += 1; progress = False
        for a in list(roster):
            for direction in ('pred', 'prey'):
                src = eaters_of[a.id] if direction == 'pred' else prey_of[a.id]
                c = sorted((byid[x] for x in src if x not in ids and room(byid[x])), key=lambda z: z.id)
                c2 = [x for x in c if not ishv(x)]
                if not c2 and cfg.hv_fallback: c2 = c
                x = _pick(rng, c2, cfg, a, bset)
                if x:
                    add(x, 'step3 %s of %s' % (direction, a.id)); progress = True
                    tree.add((x.id, a.id) if direction == 'pred' else (a.id, x.id))
        if caps_full(): terminated = 'caps_strict'; break
        if not progress:
            terminated = 'caps_lenient' if caps_full_lenient() else 'no_progress'; break
    res['iterations'] = it; res['terminated'] = terminated
    unfilled = {k: CAPS[k] - count[k] for k in CLASSES if count[k] < CAPS[k]}
    res['unfilled'] = unfilled
    res['unfilled_pool_has'] = {k: sum(1 for s in P if cls[s.id] == k and s.id not in ids) for k in unfilled}
    # step 5
    def all_edges(): return {(p.id, x) for p in roster for x in prey_of[p.id] if x in ids}
    E = all_edges()
    res['edges_tree'] = len(tree); res['edges_all'] = len(E)
    touched = lambda E: {a for e in E for a in e}
    iso = [s.id for s in roster if s.id not in touched(E)]
    res['isolated_pre6'] = iso
    # step 6: bridge an isolated node to the main component with a pool species allowed by A-F
    res['step6'] = {}
    if cfg.step6 == 'bridge':
        for sid in iso:
            if sid in touched(E): res['step6'][sid] = 'connected_by_earlier_bridge'; continue
            comps = _components(roster, E)
            main = max(comps, key=len)
            link = prey_of[sid] | eaters_of[sid]
            if not link:
                res['step6'][sid] = 'no_relation_in_pool'; continue
            if len(main) <= 1:
                res['step6'][sid] = 'no_main_component'; continue
            best = None
            for b in sorted(link - ids):
                if (prey_of[b] | eaters_of[b]) & main:
                    if room(byid[b]): best = ('bridged_within_caps', byid[b]); break
                    best = best or ('bridge_needs_cap_break', byid[b])
            if best and best[0] == 'bridged_within_caps':
                add(best[1], 'step6 bridge for ' + sid); E = all_edges()
            res['step6'][sid] = best[0] if best else ('no_relation_in_pool' if not link else 'impossible_under_A-F')
    res['roster'] = [s.id for s in roster]; res['classes'] = {s.id: cls[s.id] for s in roster}
    res['log'] = log
    res['edges_final'] = sorted(E)
    res['components'] = len(_components(roster, E)); res['isolated_final'] = [s.id for s in roster if s.id not in touched(E)]
    res['freq'] = {s.id: FREQ[cls[s.id]] for s in roster}
    # step 8
    packp = [p for p in roster if not p.vermin and cls[p.id] in PRED_CLASSES and p.cmax > 1 and any(e[0] == p.id for e in E)]
    herd = [x for x in roster if not x.vermin and cls[x.id] in PREY_CLASSES and x.cmax > 1 and any(e[1] == x.id for e in E)]
    res['step8_pack'] = bool(packp); res['step8_herd'] = bool(herd); res['step8'] = bool(packp) and bool(herd)
    feas = [e for e in E if not SPECIES[e[0]].vermin and not SPECIES[e[0]].benign and not SPECIES[e[1]].vermin]
    res['edges_unit'] = sum(1 for e in E if not SPECIES[e[0]].vermin and not SPECIES[e[1]].vermin)
    res['edges_df_feasible'] = len(feas)
    return res

def _components(R, E):
    adj = defaultdict(set)
    for a, b in E: adj[a].add(b); adj[b].add(a)
    seen, comps = set(), []
    for s in R:
        if s.id in seen: continue
        st, c = [s.id], set()
        while st:
            v = st.pop()
            if v in c: continue
            c.add(v); st.extend(adj[v] - c)
        seen |= c; comps.append(c)
    return comps

if __name__ == '__main__':
    import sys, pprint
    a = sys.argv[1:] + ['TEMP_GRASS_FOREST', 'land', 'SPRING', '1'][len(sys.argv) - 1:]
    r = build(a[0], a[1], a[2], int(a[3]))
    pprint.pprint({k: v for k, v in r.items()}, width=160)
