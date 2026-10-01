#!/usr/bin/env python3
"""roster2: guild-first roster + food-web builder for seasonal-wildlife (files only; DF 53.16 vanilla + extinct raws).

build(embark, layer, season, seed, cfg) is a pure function of its arguments plus the static species table (species2.py).
Precedence (design.md section 1): layer pool -> guild slot table -> diet matrix by guild -> apex boost -> humanoid rule
-> DF reach -> soft size preference -> FREQUENCY-weighted pick -> guards (link, stop, season, BENIGN, curious beast).
"""
import math, random, hashlib, copy
from dataclasses import dataclass, replace
from collections import Counter, defaultdict
from species2 import load, is_water, is_wetland, is_sub, SEASONS, boosted, tier, PRED_GUILDS, SCAV, ECO as _ECO
import csv as _csv

SP = load()

# ------------------------------------------------------------------ v2.1 species adjustments (user rulings 30 Sep 2026)
PEL_APEX = {'SHARK_GREAT_WHITE', 'ORCA', 'SPERM_WHALE', 'GIANT_ORCA', 'GIANT_SPERM_WHALE', 'SEA_SERPENT'}   # pelagic apex sub-slot
MW_NOT_APEX = {'GIANT_OCTOPUS': 235_100, 'GIGANTIC SQUID': 201_400}    # too small for a pelagic apex: water mesopredators
def _sp21():
    S = copy.deepcopy(SP)
    for sid in MW_NOT_APEX:          # the squid has no diet token: it is armed through the tool's curated predator override
        z = S[sid]; z.guild = 'MW'; z.apex = False; z.apex_why = 'v2.1: water meso (%d cm3)' % z.mass
    return S
SP21 = _sp21()

# ------------------------------------------------------------------ v2.2 species (user rulings 30 Sep 2026, evening)
FLY_APEX_MIN = 2000           # flying apex: a non-scavenger raptor of at least 2 kg (calm: eagle, owls, osprey; savage adds giants, pterosaurs)
FISHERS = {'BEAR_GRIZZLY', 'BEAR_BLACK', 'TIGER', 'JAGUAR'}   # land apexes that fish; the tool writes swim flags on them
def _gobble():
    """DF's own vermin-eating tokens from the census: consumer -> set of GOBBLE_VERMIN_CLASS; vermin -> creature classes."""
    G, C = {}, {}
    for r in _csv.DictReader(open(_ECO / 'tokens-by-creature.tsv'), delimiter='\t'):
        if r['GOBBLE_VERMIN_CLASS'] not in ('', '0'): G[r['id']] = set(r['GOBBLE_VERMIN_CLASS'].replace('some:', '').split('|'))
        C[r['id']] = set(x for x in r['creature_classes'].split(',') if x)
    return G, C
GOBBLE, CCLASS = _gobble()
def _sp22():
    """natural class + GOOD/EVIL species (tool class mythic/unliving) + the FANCIFUL-only wildlife (yeti, sasquatch)."""
    S = load(include_classes=('natural', 'mythic', 'unliving'))
    S = {k: v for k, v in S.items() if v.eco == 'natural' or v.good or v.evil or (v.fanciful and v.lr)}
    for sid in MW_NOT_APEX:
        if sid in S: z = S[sid]; z.guild = 'MW'; z.apex = False; z.apex_why = 'v2.1: water meso (%d cm3)' % z.mass
    for z in S.values():
        z.fisher = z.id in FISHERS
        z.monster = (z.good or z.evil or z.fanciful) and not z.vermin      # GOOD/EVIL wildlife: attacks by its guild even if it speaks
        # v2.2 civ (user 30 Sep: "let them hunt and also be prey of cavern apexes"): the sentient, non-animal-person cavern races
        z.civ = (z.sentient and z.kind != 'animal_person' and not z.monster and not z.vermin
                 and any(is_sub(x) for x in z.biomes))
        if z.guild == 'RP' and not z.vermin and not z.sentient and not z.apex and z.mass >= FLY_APEX_MIN and z.id not in SCAV \
                and not any(is_sub(x) for x in z.biomes):                  # cave raptors stay mesopredators (they eat bats)
            z.apex = True; z.apex_why = 'v2.2 flying apex (%d g)' % z.mass
    return S
SP22 = _sp22()
def species(cfg): return SP22 if cfg.v22 else SP21 if cfg.v21 else SP
def species_for(label): return SP22 if label.startswith('v22') else SP21 if label.startswith('v21') else SP

# ------------------------------------------------------------------ embarks (v1's 7 + 4 water/deep extras)
EMBARKS = {
    'TEMP_GRASS_FOREST': ({'GRASSLAND_TEMPERATE', 'FOREST_TEMPERATE_BROADLEAF', 'FOREST_TEMPERATE_CONIFER'}, 1),
    'TROP_SAVANNA_SHRUB': ({'SAVANNA_TROPICAL', 'SHRUBLAND_TROPICAL'}, 1),
    'TAIGA_TUNDRA': ({'FOREST_TAIGA', 'TUNDRA'}, 1),
    'DESERT': ({'DESERT_SAND', 'DESERT_ROCK', 'DESERT_BADLAND'}, 1),
    'TROP_WETLAND': ({'SWAMP_TROPICAL_FRESHWATER', 'MARSH_TROPICAL_FRESHWATER', 'POOL_TROPICAL_FRESHWATER'}, 1),
    'LAKE_RIVER': ({'GRASSLAND_TEMPERATE', 'FOREST_TEMPERATE_BROADLEAF', 'LAKE_TEMPERATE_FRESHWATER', 'RIVER_TEMPERATE_FRESHWATER'}, 3),
    'OCEAN_SHORE': ({'GRASSLAND_TEMPERATE', 'SHRUBLAND_TEMPERATE', 'OCEAN_TEMPERATE'}, 2),
    # extras (water coverage; deep = deepest water column in z-levels, measured: ocean 1-2, lake up to 3)
    'TROP_OCEAN_SALTRIVER': ({'SHRUBLAND_TROPICAL', 'OCEAN_TROPICAL', 'RIVER_TROPICAL_SALTWATER'}, 2),   # like BOATS
    'ARCTIC_COAST': ({'TUNDRA', 'GLACIER', 'OCEAN_ARCTIC'}, 2),
    'TROP_LAKE': ({'SAVANNA_TROPICAL', 'LAKE_TROPICAL_FRESHWATER', 'RIVER_TROPICAL_FRESHWATER'}, 3),  # like LAKE
    'OCEAN_SHORE_DEEP': ({'GRASSLAND_TEMPERATE', 'SHRUBLAND_TEMPERATE', 'OCEAN_TEMPERATE'}, 4),      # deep-column variant
}
V1_EMBARKS = list(EMBARKS)[:7]
SURFACE = ['land', 'flying', 'ocean', 'lake', 'river']
UNDER = ['cav1', 'cav2', 'cav3', 'cavw1', 'cavw2', 'cavw3', 'deep']
LAYERS = SURFACE + UNDER
WATER_LAYERS = {'ocean', 'lake', 'river', 'cavw1', 'cavw2', 'cavw3'}

# ------------------------------------------------------------------ slot tables: slot -> (min, max); order = precedence
SLOTS = {
    'land':   [('APX', 1, 1), ('GZ', 1, 2), ('PL', 1, 2), ('ML', 1, 2), ('SH', 0, 1), ('TH', 0, 1), ('SN', 0, 1), ('VG', 1, 3), ('VC', 0, 1)],
    'flying': [('APX', 0, 1), ('RP', 1, 2), ('LB', 1, 2), ('WB', 0, 2), ('TH', 0, 1), ('SN', 0, 1), ('VB', 1, 1), ('VI', 1, 2)],
    'ocean':  [('APX', 1, 1), ('FC', 1, 3), ('SH', 1, 2), ('MW', 0, 1), ('PE', 0, 1), ('WB', 0, 1), ('SN', 0, 1), ('VF', 1, 3)],
    'lake':   [('APX', 0, 1), ('FF', 1, 2), ('SH', 1, 2), ('MW', 0, 1), ('WB', 0, 1), ('SN', 0, 1), ('VF', 1, 3)],
    'river':  [('APX', 0, 1), ('FF', 1, 2), ('SH', 1, 2), ('MW', 0, 1), ('WB', 0, 1), ('SN', 0, 1), ('VF', 1, 3)],
    'cav':    [('APX', 1, 1), ('PL', 1, 3), ('ML', 0, 1), ('RP', 0, 1), ('LB', 0, 1), ('SH', 0, 1), ('TH', 0, 1), ('SN', 0, 1), ('VG', 0, 2), ('VB', 0, 1)],
    'cavw':   [('APX', 1, 1), ('FF', 0, 2), ('SH', 0, 2), ('MW', 0, 1), ('SN', 0, 1), ('VF', 1, 3)],
    'deep':   [('APX', 0, 1), ('PL', 0, 2), ('ML', 0, 1)],
}
SLOTS22 = dict(SLOTS, cav=SLOTS['cav'] + [('VI', 0, 2)])     # v2.2: cavern flying insects (none in vanilla pools; kept for mods)
def _with_snp(t): return [x for k in t for x in ([k, ('SNP', 0, 1)] if k[0] == 'SN' else [k])]
SLOTS22 = {k: _with_snp(v) for k, v in SLOTS22.items()}   # v2.2: a prey-guild animal person gets its own slot (insect/bird men)
def slot_table(layer, cfg, deep_cols):
    t = (SLOTS22 if cfg.v22 else SLOTS)['cav' if layer.startswith('cav') and not layer.startswith('cavw') else 'cavw' if layer.startswith('cavw') else layer]
    out = []
    for k, lo, hi in t:
        if k == 'APX' and layer == 'land' and cfg.savage: hi = 2                     # wiki: 2 LP groups on savage maps
        if k == 'PE' and deep_cols >= cfg.deep_levels: lo, hi = 1, 2                 # deep map: pelagic slot opens
        out.append((k, lo, hi))
        if k == 'APX' and layer == 'ocean' and cfg.pelagic_apex: out.append(('APE', 1, 1))   # v2.1: one pelagic apex
    return out

# ------------------------------------------------------------------ frequency ladder (the FREQUENCY the tool writes per guild)
LADDER = {'APX': 4, 'ML': 12, 'RP': 12, 'MW': 12, 'GZ': 50, 'PL': 40, 'SH': 30, 'LB': 40, 'WB': 30, 'FC': 50, 'FF': 50,
          'PE': None, 'SN': 5, 'TH': 10}
# v2.1 ladder (user ruling 30 Sep): the FREQUENCY the tool writes as a finalizing step, per layer family; x10 for resolution
# (shares are unchanged by the factor), then x (mass / slot geometric mean)^-0.75 clamped 0.25-4 within a slot.
LADDER21 = {
    'land':   {'APX': 3, 'ML': 3, 'GZ': 6, 'PL': 5, 'SH': 4, 'AL': 3, 'AW': 2},
    'flying': {'APX': 2, 'RP': 2, 'LB': 6, 'WB': 6},
    'water':  {'APX': 2, 'APE': 2, 'AW': 2, 'MW': 3, 'ML': 3, 'FC': 8, 'FF': 8, 'PE': 2, 'SH': 4, 'WB': 6},
    'cav':    {'APX': 3, 'ML': 3, 'GZ': 6, 'PL': 5, 'SH': 4, 'RP': 2, 'LB': 6, 'WB': 6, 'AL': 3, 'AW': 2},
}
LADDER22 = {   # v2.2: searched so predators are ~14-18% of land arrivals and ~8-10% of ocean ones (results22.md section 2)
    'land':   {'APX': 4, 'AL': 4, 'AW': 4, 'ML': 2, 'GZ': 10.5, 'PL': 8.75, 'SH': 7},          # prey x1.75 of v2.1
    'flying': {'APX': 2, 'RP': 2, 'LB': 30, 'WB': 30},                                      # prey x5: still ~19%
    'water':  {'APX': 3, 'APE': 3, 'AW': 3, 'MW': 2, 'ML': 2, 'FC': 12, 'FF': 12, 'PE': 2, 'SH': 6, 'WB': 9},   # prey x1.5
    'cav':    {'APX': 3, 'AL': 3, 'AW': 3, 'ML': 2, 'RP': 2, 'GZ': 12, 'PL': 10, 'SH': 8, 'LB': 12, 'WB': 12},  # prey x2
}
def ladder_family(layer):
    if layer in ('ocean', 'lake', 'river') or layer.startswith('cavw'): return 'water'
    if layer.startswith('cav') or layer == 'deep': return 'cav'
    return layer
def pelagic_freq(mass, deep_cols, cfg):
    f = max(cfg.pe_floor, min(50, round(100 * 2e5 / mass)))
    return min(100, f * cfg.deep_boost) if deep_cols >= cfg.deep_levels else f

@dataclass(frozen=True)
class Cfg:
    savage: bool = False          # embark region is savage: SAVAGE-tagged species (all giants, all animal people, 99/100 extinct) allowed
    savage_filter: bool = True    # False = v1 behaviour: SAVAGE species everywhere (for comparison only)
    extinct: bool = True          # extinct species allowed where their SAVAGE tag allows
    sentient_attack: bool = False # sentients (animal people, civ races) may be attackers
    humanoid_rule: bool = True    # sentient targets only for LARGE_PREDATOR or (giant and CARNIVORE/BONECARN)
    size_pref: bool = True        # soft size preference (lognormal on prey / effective predator mass)
    sigma: float = 1.0            # ln sd of the preference
    floor: float = 0.02           # preference never below this (no hard size cut)
    r_max: float = 5.0            # physical bound: prey heavier than 5x the effective (group) hunting mass is not a hunt
    r_min: float = 1e-4           # physical bound: a unit 10,000x lighter is not a unit hunt (use a vermin stock link)
    weight: str = 'frequency'     # 'frequency' (DF FREQUENCY) | 'uniform'
    cav_mode: str = 'range'       # 'range' = UNDERGROUND_DEPTH min..max hard; 'ceiling' = dmin..3 (allowed deeper than max)
    biz_pref: bool = True         # bizarre-score preference in caverns
    deep_levels: int = 3          # water columns of this many z-levels open the pelagic slot and boost its frequency
    deep_boost: int = 3
    pe_floor: int = 2
    allow: frozenset = None       # optional whitelist of species ids (realm / DF-feature mapping experiments)
    realm: tuple = None           # optional realm filter (COS always; OCE on water layers; CAVE underground)
    pack_pref: float = 1.0        # contrived (secondary) rule: pick-weight multiplier for pack predators / herd prey
    label: str = 'main'
    # v2.1 switches (all off = v2 main)
    v21: bool = False             # species adjustments (GIANT_OCTOPUS, GIGANTIC SQUID -> MW, not apex)
    ap_attack: bool = False       # animal people may attack, by their own trophic guild (civ races stay out)
    humanoid_guilds: tuple = None # sentient targets only for attackers in these guilds (ruling: AL, AW incl. boosted giants)
    pack_pred_only: bool = False  # x pack_pref only for group HUNTERS (tier >= 2), not herds
    clear_benign_preds: bool = False  # clear BENIGN on every predator-guild member the roster arms
    pelagic_apex: bool = False    # ocean: one coastal apex + one pelagic apex (APE)
    ladder21: bool = False        # FREQUENCY written = LADDER21 x within-slot mass scaling
    mass_floor: float = 0.0       # v2.1 pack-mass floor: hunting group's total mass >= this x prey mass (0 = off; CAL)
    # v2.2 switches (user rulings 30 Sep evening)
    v22: bool = False             # v2.2 species (GOOD/EVIL, fishers, flying apex) and diet (cavern fliers, gobble, fishers)
    align: str = ''               # '' calm-aligned region | 'good' | 'evil': GOOD / EVIL species admitted on matching regions
    sneak_ratio: float = 0.25     # edges whose group mass >= this x prey mass carry the sneak bonus (tool gives the pack SNEAK)
    veg: bool = False             # vegetation link: a herbivore with no predator is kept when the embark's vegetation supports it
    civ_attack: bool = False      # cavern civ races (troglodytes, amphibian/reptile/serpent/rodent/ant men...) attack by guild
    civ_prey: bool = False        # v2.2 civ: cavern civ races rank as meso (tier 2) for edges, so cavern apexes (tier 3) may eat them
    monster_slot: bool = False    # v2.2 civ: a sentient GOOD/EVIL apex (troll, blind cave ogre, ogre...) takes the apex slot, not SN,
                                  # so it can share a roster with the civ races it hunts

PREF_RATIO = {'AL': 0.8, 'AW': 0.5, 'ML': 0.3, 'MW': 0.2, 'RP': 0.3}   # preferred prey / effective predator mass

# ------------------------------------------------------------------ pools
def _land_biomes(s): return {b for b in s.biomes if not is_water(b) and not is_sub(b)}
def in_layer(s, bset, layer, cfg):
    if layer.startswith('cav') or layer == 'deep':
        if layer == 'deep':
            return 'SUBTERRANEAN_LAVA' in s.biomes or (s.depth[1] >= 4 and s.depth[0] <= 4 and s.depth[1] > 0)
        L = int(layer[-1])
        lo, hi = s.depth
        if hi == 0: return False
        ok = lo <= L <= hi if cfg.cav_mode == 'range' else lo <= L
        if not ok: return False
        if layer.startswith('cavw'):
            if 'SUBTERRANEAN_WATER' not in s.biomes: return False
            return (s.vermin and s.vclass == 'VF') or (not s.vermin and s.lr and (s.aquatic or s.amphib or s.guild == 'SH'))
        if not s.biomes & {'SUBTERRANEAN_CHASM', 'SUBTERRANEAN_WATER'}: return False
        if s.vermin: return s.vclass in ('VG', 'VB', 'VI', 'VC')
        return s.lr and not s.aquatic
    hit = s.biomes & bset
    if not hit: return False
    if layer == 'flying':
        if cfg is not None and cfg.v22 and s.vermin and s.vclass == 'VC': return False   # v2.2: hives sit on land (VC slot)
        return s.flier and (s.lr or s.vermin)
    if layer == 'land':
        if s.flier: return False
        if s.vermin: return s.vclass in ('VG', 'VC') and bool(_land_biomes(s) & bset)
        return s.lr and not s.aquatic and bool({b for b in hit if not is_water(b)})
    key = {'ocean': 'OCEAN', 'lake': 'LAKE', 'river': 'RIVER'}[layer]
    wh = {b for b in hit if b.startswith(key)}
    if cfg is not None and cfg.v22 and getattr(s, 'fisher', False) and any(b.startswith(key) for b in bset) \
            and _land_biomes(s) & bset:
        return True                                           # v2.2: a land apex that fishes joins the water web on its shore
    if not wh: return False
    if s.vermin: return s.vclass == 'VF'
    if not s.lr: return False
    if s.flier: return s.guild == 'WB'
    return s.aquatic or s.amphib or s.guild == 'SH' or (s.guild == 'ML' and s.amphib)

_POOL = {}
def pool(ekey, layer, season, cfg):
    k = (ekey, layer, season, cfg.savage, cfg.savage_filter, cfg.extinct, cfg.cav_mode, cfg.allow, cfg.realm, cfg.v21, cfg.v22, cfg.align)
    if k not in _POOL:
        bset = EMBARKS[ekey][0] if ekey in EMBARKS else set()
        out = []
        for s in species(cfg).values():
            if not in_layer(s, bset, layer, cfg): continue
            if season not in s.seasons: continue
            if s.source == 'extinct' and not cfg.extinct: continue
            if cfg.savage_filter and s.savage and not cfg.savage and not (layer.startswith('cav') or layer == 'deep'):
                continue       # wiki: SAVAGE "will only show up in savage biomes"; "no effect on cavern creatures"
            if s.good or s.evil:
                if not cfg.v22: continue
                under = layer.startswith('cav') or layer == 'deep'      # audit: GOOD/EVIL tags only limit taming underground
                if not under and not ((s.good and cfg.align == 'good') or (s.evil and cfg.align == 'evil')): continue
            if cfg.allow is not None and s.id not in cfg.allow: continue
            if cfg.realm is not None:
                ok = set(cfg.realm) | {'COS', 'CAVE'} | ({'OCE'} if layer in WATER_LAYERS else set())
                if not set(s.realms) & ok: continue
            out.append(s)
        _POOL[k] = sorted(out, key=lambda z: z.id)
    return _POOL[k]

# ------------------------------------------------------------------ slot key and diet matrix
def slot_of(s, layer, cfg=None):
    if s.vermin: return s.vclass
    if s.sentient and not (cfg is not None and cfg.monster_slot and getattr(s, 'monster', False) and s.apex):
        return 'SNP' if (cfg is not None and cfg.v22 and tier(s) == 1) else 'SN'
    if cfg is not None and cfg.pelagic_apex and layer == 'ocean' and s.id in PEL_APEX: return 'APE'
    if s.apex: return 'APX'
    g = s.guild
    if layer in WATER_LAYERS and g == 'ML': return 'MW'         # amphibious mesocarnivores (otters, snapping turtles) in water
    return g

DIET = {   # eater guild -> prey guilds (same layer). Intraguild predation only downward in tier (see tier()).
    'AL': {'GZ', 'PL', 'SH', 'ML', 'SN'},
    'AW': {'FC', 'FF', 'PE', 'SH', 'MW', 'WB', 'GZ', 'PL', 'ML', 'SN', 'VF'},   # VF: vermin fish as a stock link (cave water has no unit fish)
    'ML': {'PL', 'GZ', 'SH', 'SN', 'VG', 'VC', 'VF'},
    'MW': {'FC', 'FF', 'SH', 'PE', 'MW', 'SN', 'VF'},
    'RP': {'LB', 'WB', 'RP', 'SN', 'VB', 'VI'},
}
VERMIN_DIET = {'VB': {'VI'}}
CAVE_LB_DIET = {'VB', 'VI', 'VG'}       # v2.2: cavern bats / floaters eat flying (and ground) vermin: never left as singletons
CAVE_RP_EXTRA = {'PL', 'GZ', 'SH'}      # v2.2 (user: yes): cavern raptors also take cavern land prey (reach to be tested)
def is_cave(layer): return bool(layer) and (layer.startswith('cav') and not layer.startswith('cavw') or layer == 'deep')
def diet_of(p, layer, cfg):
    d = DIET.get(p.guild)
    if not (cfg is not None and cfg.v22): return d
    d = set(d or ())
    if p.guild == 'RP' and is_cave(layer): d |= CAVE_RP_EXTRA
    if p.guild == 'LB' and is_cave(layer): d |= CAVE_LB_DIET
    if getattr(p, 'fisher', False) and layer in WATER_LAYERS: d |= {'FF', 'FC', 'SH', 'WB'}   # fish, and shore animals/birds at the edge
    if p.id in GOBBLE: d |= {'VG', 'VC'}              # DF's own GOBBLE_VERMIN_CLASS eaters (fowl, hedgehog, pangolin)
    return d or None
def gobble_native(p, x):
    """True when DF's raws already make p eat vermin x (GOBBLE_VERMIN_CLASS matches x's creature class)."""
    return bool(GOBBLE.get(p.id, set()) & CCLASS.get(x.id, set()))

def cleared(p, cfg):
    """BENIGN is cleared by the tool: boosted apex always (T1); v2.1 every predator-guild member it arms."""
    return p.benign and (boosted(p) or (cfg is not None and cfg.clear_benign_preds and p.guild in PRED_GUILDS))
def eff_benign(p, cfg=None): return p.benign and not cleared(p, cfg)

def eff_mass(p, cfg=None):
    g = p.cmid if (p.cmax > 1 and not (eff_benign(p, cfg) if cfg is not None and cfg.v21 else p.benign)) else 1
    return p.mass * g ** 0.75

def attack_ok_on_sentient(p, cfg=None, x=None):
    if cfg is not None and cfg.v22 and p.apex and p.guild == 'RP' and x is not None and x.flier: return True   # v2.2 flying apex
    if cfg is not None and cfg.humanoid_guilds: return p.guild in cfg.humanoid_guilds
    return p.lp or (p.giant and (p.carn or p.bonecarn))

def reach(p, x):
    """DF reach (W1L/W1O): 'ok' measured pattern, 'untested', or None = impossible (no edge)."""
    if x.vermin or p.vermin: return 'stock'
    if getattr(p, 'fisher', False) and x.aquatic: return 'untested'   # v2.2: swim flags written by the tool (HR wolf: 2 attacks)
    if p.aquatic:
        if x.aquatic or x.amphib: return 'ok'
        if x.guild in ('SH', 'WB'): return 'untested'          # penguins / waterbirds in water
        return None                                           # aquatic never leaves water (lamprey x deer: 0)
    if p.flier:
        return 'untested'                                     # no raptor attacked anything on the rig yet (all BENIGN or untested)
    if x.aquatic: return 'ok' if p.amphib else None           # land predators never enter water (wolf x pike: 0)
    if x.flier: return 'untested'
    return 'ok'

def etier(s, cfg):
    """Tier for edge direction. v2.2 civ: a cavern civ race ranks as meso (2), not apex, so it hunts prey below it and
    is hunted by the cavern apexes above it; strict downward edges keep mutual predation and apex-on-apex at 0."""
    t = tier(s)
    return 2 if (cfg is not None and cfg.civ_prey and getattr(s, 'civ', False) and t > 2) else t

def edge(p, x, cfg, layer=None):
    """(allowed, pref_weight, kind) where kind in {'unit', 'stock'}; None if not an edge."""
    if p.id == x.id: return None
    if etier(p, cfg) <= etier(x, cfg): return None              # strict downward: no mutual, no apex-on-apex
    if p.vermin:
        return (1.0, 'stock') if x.vermin and x.vclass in VERMIN_DIET.get(p.vclass, ()) else None
    g = p.guild
    xs = 'SN' if x.sentient else ('MW' if (x.guild == 'ML' and x.amphib and x.aquatic) else x.guild)
    diet = diet_of(p, layer, cfg)
    if diet is None: return None
    if boosted(p): diet = diet | {g}                           # boosted apex eats its own home guild (giant fox > fox)
    if x.vermin and cfg.v22 and p.id in GOBBLE and not gobble_native(p, x) and g not in DIET: return None   # gobblers: their class only
    if xs not in diet: return None
    if x.sentient and cfg.humanoid_rule and not attack_ok_on_sentient(p, cfg, x): return None
    if p.sentient and not (cfg.sentient_attack or (cfg.ap_attack and p.kind == 'animal_person')
                           or (cfg.v22 and getattr(p, 'monster', False)) or (cfg.civ_attack and getattr(p, 'civ', False))):
        return None
    if x.vermin: return (1.0, 'stock')
    if reach(p, x) is None: return None
    if cfg.mass_floor:
        grp = p.cmid if (p.cmax > 1 and not eff_benign(p, cfg)) else 1
        if p.mass * grp < cfg.mass_floor * x.mass: return None
    r = x.mass / eff_mass(p, cfg)
    if r > cfg.r_max or r < cfg.r_min: return None
    if not cfg.size_pref: return (1.0, 'unit')
    rs = PREF_RATIO.get(g, 0.5)
    w = cfg.floor + (1 - cfg.floor) * math.exp(-(math.log(r / rs)) ** 2 / (2 * cfg.sigma ** 2))
    return (w, 'unit')

def actable(p, x, cfg=None):
    """'df' = DF carries it out (measured), 'df?' = written but untested reach, 'stock' = tool stock transfer,
    'no' = written edge DF will not act on (a BENIGN attacker the tool leaves BENIGN)."""
    if p.vermin or x.vermin: return 'stock'
    if p.benign and not cleared(p, cfg): return 'no'
    rc = reach(p, x)
    return 'df' if rc == 'ok' else 'df?'

# ------------------------------------------------------------------ build
_REL = {}
def relations(ekey, layer, season, cfg):
    """All allowed edges over one pool: {(p, x): (w, kind)} and the neighbour sets; cached per pool and config."""
    k = (ekey, layer, season, cfg)
    if k not in _REL:
        P = pool(ekey, layer, season, cfg)
        E = {}
        for p in P:
            if p.vermin and p.vclass not in VERMIN_DIET: continue
            if not p.vermin and diet_of(p, layer, cfg) is None: continue
            for x in P:
                e = edge(p, x, cfg, layer)
                if e: E[(p.id, x.id)] = e
        nb = defaultdict(set)
        for (a, b) in E: nb[a].add(b); nb[b].add(a)
        _REL[k] = (E, nb)
    return _REL[k]

def _rng(*parts): return random.Random(int(hashlib.sha256('|'.join(map(str, parts)).encode()).hexdigest()[:16], 16))
BIZ_TARGET = {1: 2, 2: 4, 3: 7}

def freq21(roster, slot, layer, deep_cols, cfg):
    """v2.1: LADDER21 base by slot (a sentient or TH member uses its trophic slot) x within-slot mass scaling."""
    lad = (LADDER22 if cfg.v22 else LADDER21)[ladder_family(layer)]
    def key(s):
        k = slot[s.id]
        if k in ('SN', 'TH', 'SNP'): k = 'APX' if s.apex else s.guild
        return k
    groups = defaultdict(list)
    for s in roster:
        if not s.vermin: groups[key(s)].append(s)
    out = {}
    for k, mem in groups.items():
        base = lad.get(k, 5)
        if k == 'PE' and deep_cols >= cfg.deep_levels: base *= cfg.deep_boost
        gm = math.exp(sum(math.log(max(1, m.mass)) for m in mem) / len(mem))
        for m in mem:
            sc = min(4.0, max(0.25, (max(1, m.mass) / gm) ** -0.75))
            out[m.id] = 10 * base * sc if cfg.v22 else min(100, max(1, round(10 * base * sc)))
    if cfg.v22 and out:     # v2.2: DF caps FREQUENCY at 100; scale the roster so its commonest member is 100 (ratios kept)
        top = max(out.values()); k = 100 / top if top > 100 else 1
        out = {sid: max(1, round(v * k)) for sid, v in out.items()}
    return out

def freq_of(s, slot, deep_cols, cfg):
    if s.deep and not s.apex and slot in ('PE', 'FC', 'MW'): return pelagic_freq(s.mass, deep_cols, cfg)
    return LADDER.get(slot) or 10

# v2.2 vegetation link. DF exposes per map: the region tiles' vegetation index (world_data.region_map[x][y].vegetation, 0-100),
# grass per tile (block_square_event_grassst amounts), and shrubs/trees (world.plants). Here the index is approximated per biome
# (EXTERNAL knowledge of DF's biome rules: deserts < 10, grassland/savanna/shrubland 10-65, forests and wetlands 66+); the tool
# would read the embark's own tiles instead (in-tool survey: mean vegetation of the embark region tiles + grass-tile share).
VEG_BIOME = {'MOUNTAIN': 10, 'GLACIER': 0, 'TUNDRA': 15, 'FOREST_TAIGA': 70}
def veg_index(b):
    if b in VEG_BIOME: return VEG_BIOME[b]
    if b.startswith(('SWAMP', 'MARSH')): return 75
    if b.startswith('FOREST'): return 85
    if b.startswith('GRASSLAND'): return 50
    if b.startswith('SAVANNA'): return 45
    if b.startswith('SHRUBLAND'): return 30
    if b.startswith('DESERT'): return 5
    if b.startswith('SUBTERRANEAN'): return 40     # cavern floor fungus (moss, tower caps): assumed mid
    return 0
def veg_need(mass): return max(10.0, min(90.0, 20 + 15 * math.log10(max(1, mass) / 1e5)))   # 100 kg 20, 1 t 35, 5 t 45, 40 t 59
def herbivore(s): return not s.vermin and tier(s) == 1 and s.guild in ('GZ', 'PL', 'SH') and not s.diet_pred
VEG_W = 0.05      # weight of the vegetation link: below any animal edge, so a hunted herbivore is always preferred
def veg_supports(ekey, layer, s):
    if layer == 'land':
        bs = EMBARKS[ekey][0] if ekey in EMBARKS else set()
        cand = [veg_index(b) for b in (s.biomes & bs) if not is_water(b)]
    elif is_cave(layer): cand = [veg_index('SUBTERRANEAN_CHASM')]
    elif layer in ('lake', 'river', 'ocean'):            # a shore grazer (hippo, capybara) feeds on the embark's land
        bs = EMBARKS[ekey][0] if ekey in EMBARKS else set()
        cand = [veg_index(b) for b in bs if not is_water(b)]
    else: return False
    return bool(cand) and max(cand) >= veg_need(s.mass)

def build(ekey, layer, season, seed, cfg=Cfg()):
    rng = _rng(ekey, layer, season, seed, cfg.label)
    P = pool(ekey, layer, season, cfg)
    deep_cols = EMBARKS[ekey][1] if ekey in EMBARKS else 0
    table = slot_table(layer, cfg, deep_cols)
    tmax = {k: hi for k, lo, hi in table}; tmin = {k: lo for k, lo, hi in table}
    slot = {s.id: slot_of(s, layer, cfg) for s in P}
    E, nb = relations(ekey, layer, season, cfg)
    veg_ok = {s.id for s in P if cfg.veg and herbivore(s) and veg_supports(ekey, layer, s)}
    L = int(layer[-1]) if layer[-1].isdigit() else 0
    def pick_w(s):
        w = max(1, s.freq) if cfg.weight == 'frequency' else 1
        if s.deep and not s.apex and not cfg.v21: w = pelagic_freq(s.mass, deep_cols, cfg)
        if cfg.pack_pref != 1.0 and not s.vermin and s.cmax > 1 and not (eff_benign(s, cfg) if cfg.v21 else s.benign) \
                and (not cfg.pack_pred_only or tier(s) >= 2):
            w *= cfg.pack_pref
        if cfg.biz_pref and L and s.bizarre >= 0:
            w *= math.exp(-((s.bizarre - BIZ_TARGET[L]) / 3.0) ** 2) + 0.05
        return w
    roster, ids, count = [], set(), Counter()
    def fill_count(k):
        if k == 'TH': return sum(1 for s in roster if (s.cb or s.scav))
        return count[k]
    def add(s, k):
        roster.append(s); ids.add(s.id); count[k] += 1
    def link_w(s):
        return sum(E[(s.id, r.id)][0] if (s.id, r.id) in E else E[(r.id, s.id)][0] for r in roster if r.id in nb[s.id]) \
            + (VEG_W if s.id in veg_ok else 0)
    res = dict(embark=ekey, layer=layer, season=season, seed=seed, cfg=cfg.label, pool_n=len(P), deep_cols=deep_cols,
               pool_slots=dict(Counter(slot.values())), slots={k: [lo, hi] for k, lo, hi in table})
    # seed: first slot in precedence with a linked candidate (seed with >= 1 relation)
    seed_sp = None
    for k, lo, hi in table:
        c = [s for s in P if (slot[s.id] == k or (k == 'TH' and (s.cb or s.scav))) and (nb[s.id] or s.id in veg_ok)]
        if c:
            seed_sp = rng.choices(c, weights=[pick_w(s) for s in c])[0]
            add(seed_sp, slot[seed_sp.id]); break
    res['seed_sp'] = seed_sp.id if seed_sp else None
    # fill: passes over the slot table in precedence order; a pick must link to the roster; guard = no progress
    passes = 0
    while seed_sp is not None and passes < 30:
        passes += 1; progress = False
        for want_min in (True, False):
            for k, lo, hi in table:
                cur = fill_count(k)
                if cur >= (lo if want_min else hi): continue
                if k == 'TH':
                    c = [s for s in P if s.id not in ids and (s.cb or s.scav) and count[slot[s.id]] < tmax.get(slot[s.id], 0)]
                else:
                    c = [s for s in P if s.id not in ids and slot[s.id] == k]
                c = [(s, link_w(s)) for s in c]
                c = [(s, w) for s, w in c if w > 0]
                if not c: continue
                s = rng.choices([z for z, _ in c], weights=[pick_w(z) * w for z, w in c])[0]
                add(s, slot[s.id]); progress = True
        if not progress and cfg.v21:
            # v2.1 fallback for the no-progress stop: a slot whose candidates link only to species not yet on the roster
            # (a closed sub-web, e.g. cave raptors + bats + floaters) is seeded as a predator-prey PAIR, then passes resume.
            for k, lo, hi in table:
                if fill_count(k) >= hi or k == 'TH': continue
                c = [z for z in P if z.id not in ids and slot[z.id] == k]
                pairs = [(z, y) for z in c for y in P if y.id in nb[z.id] and y.id not in ids and y.id != z.id
                         and slot[y.id] in tmax and count[slot[y.id]] < tmax[slot[y.id]]]
                if not pairs: continue
                z, y = rng.choice(pairs)
                add(z, k); add(y, slot[y.id]); res.setdefault('pair_fill', []).append([z.id, y.id]); progress = True
                break
        if all(fill_count(k) >= hi for k, lo, hi in table) or not progress: break
    res['passes'] = passes
    if cfg.v21:     # v2.1: every slot left below its maximum is reported with its reason (user: no silent stops)
        un = {}
        for k, lo, hi in table:
            if fill_count(k) >= hi: continue
            cand = [z for z in P if z.id not in ids and (slot[z.id] == k or (k == 'TH' and (z.cb or z.scav)))]
            if not cand: why = 'pool has no candidate' if not any(slot[z.id] == k for z in P) else 'pool exhausted'
            elif not any(nb[z.id] for z in cand): why = 'candidates have no edge in the pool'
            elif not any(nb[z.id] & ids for z in cand): why = 'candidates link only to non-roster species'
            else: why = 'other'
            un[k] = [fill_count(k), lo, hi, why, len(cand)]
        res['unfilled'] = un
    res['terminated'] = 'max' if all(fill_count(k) >= hi for k, lo, hi in table) else 'no_progress'
    # all allowed edges among the roster (step 5 equivalent)
    RE = {(a, b): E[(a, b)] for (a, b) in E if a in ids and b in ids}
    touched = {a for e in RE for a in e} | (veg_ok & ids)
    iso = [s.id for s in roster if s.id not in touched]
    # isolation repair: swap an isolated member for a same-slot candidate that links, else drop it
    repaired, dropped = [], []
    for sid in iso:
        s = next(z for z in roster if z.id == sid); k = slot[sid]
        roster.remove(s); ids.discard(sid); count[k] -= 1
        c = [(z, link_w(z)) for z in P if z.id not in ids and z.id != sid and slot[z.id] == k]
        c = [(z, w) for z, w in c if w > 0]
        if c:
            z = rng.choices([a for a, _ in c], weights=[pick_w(a) * w for a, w in c])[0]
            add(z, k); repaired.append((sid, z.id))
        else:
            dropped.append(sid)
    RE = {(a, b): E[(a, b)] for (a, b) in E if a in ids and b in ids}
    touched = {a for e in RE for a in e} | (veg_ok & ids)
    res['isolated_pre'] = iso; res['repaired'] = repaired; res['dropped'] = dropped
    res['isolated'] = [s.id for s in roster if s.id not in touched] if len(roster) > 1 else [s.id for s in roster]
    res['roster'] = [s.id for s in roster]
    res['slot'] = {s.id: slot[s.id] for s in roster}
    S = species(cfg)
    res['edges'] = sorted([a, b, round(w, 3), kind, actable(S[a], S[b], cfg)] for (a, b), (w, kind) in RE.items())
    if cfg.v22:
        res['veg'] = sorted(veg_ok & ids)                                          # herbivores the vegetation supports
        animal = {a for e in RE for a in e}
        res['veg_only'] = sorted((veg_ok & ids) - animal)                          # kept by the vegetation link alone
        sn = []
        for a, b, w, k, act in res['edges']:
            if k != 'unit': continue
            p, x = S[a], S[b]
            grp = p.cmid if (p.cmax > 1 and not eff_benign(p, cfg)) else 1
            if p.mass * grp >= cfg.sneak_ratio * x.mass: sn.append([a, b])
        res['sneak'] = sn                                                          # the tool gives these hunters unit SNEAK
        res['vlinks'] = [[a, b, ('native' if gobble_native(S[a], S[b]) else 'write') if not S[a].vermin else 'tool']
                         for a, b, w, k, act in res['edges'] if k == 'stock']
    # frequency ladder the tool writes, and the arrival share it implies (F1: shares proportional to FREQUENCY)
    fq = (freq21(roster, slot, layer, deep_cols, cfg) if cfg.ladder21 else
          {s.id: freq_of(s, slot[s.id], deep_cols, cfg) for s in roster if not s.vermin})
    tot = sum(fq.values()) or 1
    res['freq'] = fq; res['share'] = {k: round(v / tot, 3) for k, v in fq.items()}
    # guards / tool actions
    res['stop'] = sorted(s.id for s in P if s.id not in ids)                      # entry quantity 0 (N1: stops a species)
    res['benign_clear'] = [s.id for s in roster if boosted(s) and s.benign]        # T1: BENIGN off lets it act
    if cfg.clear_benign_preds:                                                     # v2.1: + every armed BENIGN predator
        att = {a for a, *_ in res['edges']}
        res['benign_clear'] = [s.id for s in roster if cleared(s, cfg) and s.id in att]
    res['arm'] = sorted({a for a, b, w, k, act in res['edges'] if act in ('df', 'df?')})
    res['cb_resident'] = [s.id for s in roster if s.cb]                            # B: tool-placed curious beasts leave in 3,000 t
    # seasonal breaks: a predator present in another season whose roster prey are all absent then -> NO_<season> write
    br = []
    for p in roster:
        prey = [S[b] for a, b, w, k, act in res['edges'] if a == p.id]
        if not prey: continue
        for s2 in SEASONS:
            if s2 == season or s2 not in p.seasons: continue
            if not any(s2 in x.seasons for x in prey): br.append((p.id, s2))
    res['season_break'] = br
    return res

def components(res, veg=False):
    adj = defaultdict(set)
    for a, b, *_ in res['edges']: adj[a].add(b); adj[b].add(a)
    if veg and res.get('veg'):                     # every vegetation-supported herbivore eats the same plants: one node
        for v in res['veg']: adj[v].add('~VEG'); adj['~VEG'].add(v)
    seen, n = set(), 0
    for s in res['roster']:
        if s in seen: continue
        n += 1; st = [s]
        while st:
            v = st.pop()
            if v in seen: continue
            seen.add(v); st.extend(adj[v] - seen)
    return n

if __name__ == '__main__':
    import sys, pprint
    a = sys.argv[1:] + ['TEMP_GRASS_FOREST', 'land', 'SPRING', '1'][len(sys.argv) - 1:]
    r = build(a[0], a[1], a[2], int(a[3]))
    r.pop('stop')
    pprint.pprint(r, width=160)
