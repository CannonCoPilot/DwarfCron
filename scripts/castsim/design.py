"""castsim.design: the cast pipeline as the user specified it on 9 Oct 2026 (evening), simulated on DF's raws.

The rules this module follows (the user's words, condensed):
  * The pool is NOT the region's population list. Every creature in the raws is a candidate; the top-level filters are
    wild-and-natural, BIOME (the fort's land biomes, its water bodies, its caverns), SAVAGE (giants, animal people and
    SAVAGE-tagged species only where the biome is savage), GOOD/EVIL (only where the biome is good / evil), and DF's
    worldgen rule for real-world-extinct species (REAL_WORLD_EXTINCT).
  * Seven layers: land-ground, land-flying, ocean, freshwater, cavern 1, cavern 2, cavern 3; x 4 seasons = 28 lists, and
    a season cast is drawn from each list.
  * land-ground never takes an amphibious creature. land-flying: apex 1, 2 meso-or-prey fliers, 2-3 flying vermin, the
    food web assigned after the draw. Ocean: saltwater aquatic + amphibious + shore + niche fliers; apex 1, meso 1-2,
    fish 3, pelagic 1, shore 1-2, waterbird 1-2, vermin 2-3. Freshwater by subtype (not compounding): lake (or lake +
    river) like ocean without pelagic; river/brook without a lake: meso 1, fish 2, shore 1, waterbird 1, vermin 2; murky
    pools only: a mini roster of small aquatic/amphibious creatures, meso 1, fish 2, vermin 2. Shore creatures and
    fliers can take small aquatic creatures and vermin (they are not placed in the water).
  * Each cavern: apex 1, meso 1, ground prey 1, flier 1, amphibious-or-aquatic 1, sentient 1, vermin 2; cavern 1 the
    least weird on average, cavern 3 the most.

Kept from the engine as built (v7.4-onebuilder 834f92e): classify / guild / the extinct corrections (engine.py); the apex
"mix" (largest flagged predator in season keeps apex); the high-value seed (war, top 10% pet value, top 10% size; no
sentient seed); pick weights (pack x3, x0.1 per appearance on the year's other casts, giants x0.2); one candidate per
species per cast. Everything this module had to decide that the user did not specify is in JUDGEMENT (the report lists it).
"""
from __future__ import annotations

import math
import random

from engine import Engine, REACH, R0, CAST_DEF

SAVAGE_AT, EVIL_AT, GOOD_AT = 66, 66, 32          # DF: savagery 66+ = savage; evil 66+ = evil, 0-32 = good
SALT_WET = {'MARSH_TEMPERATE_SALTWATER', 'MARSH_TROPICAL_SALTWATER', 'SWAMP_TEMPERATE_SALTWATER', 'SWAMP_TROPICAL_SALTWATER',
            'SWAMP_MANGROVE'}
POOL_CAP = 20000                                   # "small" for the murky-pool mini roster, cm3 (judgement)
SUBTER = ('SUBTERRANEAN_WATER', 'SUBTERRANEAN_CHASM')
EXTINCT_RULE = {
    'NONE': 'absent from the world',
    'ISOLATED': 'only in isolated savage regions (small savage islands and patches)',
    'UNTAMED_WILDS': 'only in savage regions',
    'WILDERNESS': 'in any wild region',
    'DOMESTICATED': 'in any wild region (and kept by civilisations)',
}

LAYERS = ['ground', 'flying', 'ocean', 'fresh', 'cavern1', 'cavern2', 'cavern3']
LAYER_NAME = {'ground': 'land-ground', 'flying': 'land-flying', 'ocean': 'ocean (saltwater)', 'fresh': 'freshwater',
              'cavern1': 'cavern 1', 'cavern2': 'cavern 2', 'cavern3': 'cavern 3'}
# slot -> (min, max) per cast; the count is drawn per cast inside the range
SLOTS = {
    'ground': {'apex': (1, 1), 'meso': (2, 2), 'grazer': (2, 2), 'ground prey': (2, 2), '_vermin': (3, 3)},
    'flying': {'apex': (1, 1), 'flier': (2, 2), '_vermin': (2, 3)},
    'ocean': {'apex': (1, 1), 'meso': (1, 2), 'fish': (3, 3), 'pelagic': (1, 1), 'shore': (1, 2), 'waterbird': (1, 2), '_vermin': (2, 3)},
    'fresh:lake': {'apex': (1, 1), 'meso': (1, 2), 'fish': (3, 3), 'shore': (1, 2), 'waterbird': (1, 2), '_vermin': (2, 3)},
    'fresh:river': {'meso': (1, 1), 'fish': (2, 2), 'shore': (1, 1), 'waterbird': (1, 1), '_vermin': (2, 2)},
    'fresh:pool': {'meso': (1, 1), 'fish': (2, 2), '_vermin': (2, 2)},
    'cavern': {'apex': (1, 1), 'meso': (1, 1), 'ground prey': (1, 1), 'flier': (1, 1), 'swimmer': (1, 1), 'sentient': (1, 1), '_vermin': (2, 2)},
}
SLOT_LABEL = {'swimmer': 'amphib or aquatic', 'flier': 'flier'}

# a first-cut weirdness score for the cavern species (0 = a real animal's cave form, 1 = wholly alien); the user's call.
# Low: cave forms of real animals. Middle: cave animal people, humanoids, odd-but-animal. High: bodiless, eyeballs, blobs.
WEIRD = {
    'BAT_GIANT': .10, 'RAT_GIANT': .10, 'RAT_LARGE': .05, 'MOLE_GIANT': .10, 'MOLE_DOG_NAKED': .10, 'BLIND_CAVE_BEAR': .15,
    'CROCODILE_CAVE': .15, 'OLM_GIANT': .15, 'TOAD_GIANT_CAVE': .15, 'BIRD_SWALLOW_CAVE_GIANT': .15, 'GIANT_EARTHWORM': .20,
    'SPIDER_CAVE_GIANT': .25, 'HELMET_SNAKE': .35, 'POND_GRABBER': .40, 'ELK_BIRD': .40, 'DRALTHA': .45,
    'TROGLODYTE': .30, 'RODENT MAN': .35, 'OLM_MAN': .35, 'CAVE_FISH_MAN': .35, 'BAT_MAN': .35, 'CAVE_SWALLOW_MAN': .35,
    'AMPHIBIAN_MAN': .40, 'REPTILE_MAN': .40, 'SERPENT_MAN': .40, 'ANT_MAN': .45, 'TROLL': .50, 'BLIND_CAVE_OGRE': .50,
    'GREMLIN': .55, 'DRUNIAN': .55, 'GORLAK': .60, 'MANERA': .60, 'PLUMP_HELMET_MAN': .65, 'CRUNDLE': .60, 'BUGBAT': .60,
    'MOLEMARIAN': .65, 'RUTHERER': .65, 'MAGMA_CRAB': .60, 'CAVE_DRAGON': .70, 'JABBERER': .70, 'REACHER': .75,
    'VORACIOUS_CAVE_CRAWLER': .75, 'CAVE_FLOATER': .80, 'GREEN_DEVOURER': .80, 'CAVE_BLOB': .90, 'FLOATING_GUTS': .90,
    'FLESH_BALL': .90, 'CREEPING_EYE': .95, 'HUNGRY_HEAD': .95,
    # cavern vermin
    'FISH_CAVE': .10, 'LOBSTER_CAVE': .15, 'OLM': .10, 'BIRD_SWALLOW_CAVE': .10, 'SPIDER_CAVE': .15, 'CAP_HOPPER': .55,
    'CREEPY_CRAWLER': .60, 'MAGGOT_PURRING': .70, 'SNAKE_FIRE': .70,
}


def weird_weight(k, s):
    """the cavern pick multiplier for weirdness s in cavern k (1 favours the plain, 2 the middle, 3 the strange)"""
    if k == 1: return (1 - s) ** 2 + 0.05
    if k == 2: return max(0.05, 1 - abs(s - 0.5) * 1.8)
    return s ** 2 + 0.05


JUDGEMENT = [
    ('land-ground slots', 'not specified: kept the v7.4 land cast without its raptor, bird and sentient slots (apex 1, meso 2, grazer 2, ground prey 2, vermin 3).'),
    ('ranges', '"1-2" and "2-3": each cast draws its count inside the range, so cast sizes vary from season to season.'),
    ('apex rule', 'kept as built (the mix): the largest flagged predator in season keeps the apex slot; the others can take meso. With full pools this makes the apex the same species in every season it is in season (see the diversity table).'),
    ('river-only apex', 'no apex slot (your list has none); flagged predators there can take the meso slot.'),
    ('fill fallback', 'a slot with room and no candidate linked to the cast is filled anyway from its eligible species ("no link"), so no slot stays empty while candidates exist; the food web is computed after the draw on every layer, as you asked for land-flying.'),
    ('amphibians', 'an amphibious (water-breathing, not aquatic) creature never enters land-ground; if its BIOME names a fort land biome it can enter the freshwater layer (its shore slot), and on a saltwater marsh, swamp or mangrove the ocean layer.'),
    ('shore and fliers', 'a shore creature or a waterbird eats an aquatic creature no larger than itself (or 20,000 cm3), and aquatic vermin.'),
    ('murky pools', '"small" = adult size up to 20,000 cm3 for the pool mini roster; DF\'s pool fish and amphibians are vermin (lungfish, pond turtle, toad), so the pool\'s fish slot draws fish-class and amphibious vermin too (a species drawn as fish is not also drawn as vermin).'),
    ('cavern sentients', 'a sentient cavern species (troll, blind cave ogre, gorlak, animal people, troglodyte) fills only the sentient slot.'),
    ('weirdness', 'a first-cut 0-1 score per cavern species (table in the step-through); cavern 1 picks weight (1-w)^2, cavern 2 the middle, cavern 3 w^2. DF\'s own raw depth range still decides which caverns a species can live in.'),
    ('region biomes', 'a real fort\'s biomes are the 3x3 world tiles around it (DF draws a block\'s wildlife from all nine region neighbours); each biome takes the savagery and evil of the nearest tile that has it.'),
    ('alignment', 'GOOD species only where the biome is good (evil 0-32), EVIL only where evil (66+); cavern species are exempt (v7: alignment only limits taming).'),
    ('cavern savagery', 'caverns ignore surface savagery: DF stocks savage cave species (giant cave spider) on calm forts.'),
    ('extinct rule', 'DF\'s raws tag every real-world-extinct species SAVAGE; the world\'s REAL_WORLD_EXTINCT setting is read in place of that tag (UNTAMED_WILDS and ISOLATED: savage regions only; WILDERNESS and DOMESTICATED: any wild region). Extinct animal people stay savage-only, as all animal people.'),
    ('extinct setting', 'region19\'s REAL_WORLD_EXTINCT cannot be read without DF (world.raws.param_real_world_extinct); the real forts assume UNTAMED_WILDS, the install\'s default preset value.'),
    ('wild', 'a creature is wild when it has a BIOME and either LARGE_ROAMING or a vermin tag (DF\'s own test for region populations).'),
]


BROAD = {'ALL_MAIN', 'ANY_LAND', 'ANY_TEMPERATE', 'ANY_TROPICAL', 'NOT_FREEZING'}
WATER_WORDS = ('OCEAN', 'LAKE', 'RIVER', 'POOL')


def explicit_water(raw_tokens, water_biomes):
    """the fort water biomes a creature's raws name on purpose (not through ALL_MAIN, ANY_TROPICAL and the like)"""
    from raws import AGG
    out = set()
    for t in raw_tokens:
        if t in BROAD: continue
        for b in AGG.get(t, [t]):
            if b in water_biomes and b.startswith(WATER_WORDS): out.add(b)
    return out


class Design:
    def __init__(self, raws=None):
        self.E = Engine(raws, align={'good': True, 'evil': True})   # alignment is gated per biome below
        self.R = self.E.R

    # ------------------------------------------------------------------ the fort's biome set
    @staticmethod
    def fort_biomes(spec):
        """{biome: {'sav', 'evil', 'kind'}} for the fort: land biomes, water bodies, caverns"""
        out = {}
        for b in spec['land']: out[b['biome']] = {'sav': b['sav'], 'evil': b['evil'], 'kind': 'land'}
        for k in ('ocean', 'lake', 'river', 'pool'):
            for w in spec['water'].get(k) or ():
                out[w['biome']] = {'sav': w['sav'], 'evil': w['evil'], 'kind': k}
        if spec.get('caverns'):
            for b in SUBTER: out[b] = {'sav': 0, 'evil': 50, 'kind': 'cavern'}
        return out

    @staticmethod
    def fresh_subtype(spec):
        w = spec['water']
        if w.get('lake'): return 'lake'
        if w.get('river'): return 'river'
        if w.get('pool'): return 'pool'
        return None

    # ------------------------------------------------------------------ step 1: the top-level filters
    def gate(self, info, b, fb, spec):
        """can this species live in fort biome b? (None = yes, else the reason)"""
        if b in SUBTER: return None
        # a real-world-extinct species (not its animal person) follows the world's REAL_WORLD_EXTINCT rule in place of
        # its raw SAVAGE tag: DF's raws tag them all SAVAGE, the worldgen setting says savage-only or any wild region
        if info['extinct'] and not info['ap']:
            rule = spec.get('extinct', 'UNTAMED_WILDS')
            if rule == 'NONE': return 'extinct: absent from this world'
            if rule in ('UNTAMED_WILDS', 'ISOLATED') and fb['sav'] < SAVAGE_AT: return f'extinct ({rule}): biome not savage'
            if rule == 'ISOLATED' and not spec.get('isolated'): return 'extinct (ISOLATED): region not isolated'
        elif info['savage'] and fb['sav'] < SAVAGE_AT:
            return 'SAVAGE (giant / animal person / tagged): biome not savage'
        if info['good'] and fb['evil'] > GOOD_AT: return 'GOOD: biome not good'
        if info['evil'] and fb['evil'] < EVIL_AT: return 'EVIL: biome not evil'
        return None

    def pool(self, spec):
        """every creature in the raws through the top-level filters; returns (pool {token: entry}, funnel, rejected rows)"""
        fbs = self.fort_biomes(spec)
        funnel = {'all creatures': 0, 'wild': 0, 'natural (not locked)': 0, 'BIOME matches the fort': 0, 'passes savage / alignment / extinct': 0}
        rejected, pool = [], {}
        for tok in sorted(self.R.src):
            c = self.R.creature(tok)
            funnel['all creatures'] += 1
            f = c['flags']
            if 'DOES_NOT_EXIST' in f or 'EQUIPMENT_WAGON' in f or not c['biomes']: continue
            info = self.E.classify(tok)
            if not ('LARGE_ROAMING' in f or info['gameVermin']): continue
            funnel['wild'] += 1
            if info['eco'] != 'natural' or info['mega'] or info['night']: continue
            funnel['natural (not locked)'] += 1
            hit = [b for b in c['biomes'] if b in fbs]
            if not hit: continue
            funnel['BIOME matches the fort'] += 1
            ok, why = [], []
            for b in hit:
                r = self.gate(info, b, fbs[b], spec)
                (why if r else ok).append(r or b)
            if not ok:
                rejected.append({'token': tok, 'why': sorted(set(why))[0], 'biomes': hit}); continue
            funnel['passes savage / alignment / extinct'] += 1
            e = dict(info)
            e.update(key=tok, matched=sorted(ok), weird=WEIRD.get(tok))
            pool[tok] = e
        return pool, funnel, rejected

    # ------------------------------------------------------------------ step 2: the seven layers
    def layers_of(self, e, spec, fbs):
        """the layers a pool species belongs to, and the notes on layers it was kept out of"""
        m = set(e['matched'])
        land = [b for b in m if fbs[b]['kind'] == 'land']
        hab, verm = e['habitat'], e['gameVermin']
        out, notes = [], []
        vc = self.E.vclass(e) if verm else None
        if land:
            if verm:
                if vc in ('VB', 'VI'): out.append('flying')
                elif vc != 'VF': out.append('ground')
            elif hab == 'land': out.append('ground')
            elif hab in ('flier', 'waterbird'): out.append('flying')
            elif hab == 'semiaquatic': notes.append(('ground', 'amphibious: never on land-ground'))
        # a water layer takes aquatic and amphibious species on any biome match; land animals, fliers and insects only
        # where their raws name the water body itself (ALL_MAIN or ANY_TROPICAL would put rats and beetles in every pool)
        wet = hab in ('aquatic', 'semiaquatic')
        named = explicit_water(self.R.creature(e['token'])['biome_tokens'], {b for b in m if fbs[b]['kind'] not in ('land', 'cavern')})
        seas = {w['biome'] for w in spec['water'].get('ocean') or ()}
        if seas:
            if (m & seas and (wet or m & seas & named)) or (not verm and hab in ('semiaquatic', 'waterbird') and set(land) & SALT_WET):
                out.append('ocean')
            elif m & seas: notes.append(('ocean', 'its raws name no sea (a broad biome group only)'))
        sub = self.fresh_subtype(spec)
        if sub:
            fw = {w['biome'] for k in ('lake', 'river', 'pool') for w in spec['water'].get(k) or ()}
            hit = m & fw
            via = bool(hit and (wet or hit & named)) or (not verm and hab == 'semiaquatic' and land and not set(land) <= SALT_WET)
            if hit and not via: notes.append(('fresh', 'its raws name no lake, river or pool (a broad biome group only)'))
            if via:
                if sub == 'pool' and not verm and e['mass'] > POOL_CAP: notes.append(('fresh', f'too large for the murky-pool roster ({e["mass"]:,} cm3)'))
                elif sub == 'pool' and not verm and hab in ('flier', 'waterbird', 'land'): notes.append(('fresh', 'not aquatic or amphibious (murky-pool roster)'))
                else: out.append('fresh')
        if m & set(SUBTER):
            lo, hi = e['depthLo'], e['depthHi']
            for k in spec.get('caverns') or ():
                if (not lo or not hi) or lo <= k <= hi: out.append(f'cavern{k}')
                else: notes.append((f'cavern{k}', f'raw depth {lo}-{hi}'))
        return out, notes

    # ------------------------------------------------------------------ slot eligibility
    def flagged(self, e, layer):
        if e['civ'] or e['gameVermin']: return False
        if layer == 'flying': return self.E.fly_apex(dict(e, layer='land'))
        kind = R0['aquatic_apex'].get(e['token'])
        if layer in ('ocean', 'fresh'):
            if kind in ('apex', 'pelagic'): return True
            return e['habitat'] in ('aquatic', 'semiaquatic') and (e['guild'] in ('AL', 'AW') or self.E.boosted(e))
        return e['guild'] in ('AL', 'AW') or self.E.boosted(e)

    @staticmethod
    def predator(e):
        return e['guild'] in ('ML', 'MW', 'RP', 'AL', 'AW') or e['role'] == 'predator'

    def slots_for(self, e, layer, sub):
        """the cast slots a (non-vermin) candidate can fill on this layer"""
        hab, pred, g = e['habitat'], self.predator(e), e['guild']
        if layer.startswith('cavern'):
            if e['sentient']: return ['sentient']
            s = []
            if self.flagged(e, layer): s.append('apex')
            if pred: s.append('meso')
            if hab == 'land' and not pred: s.append('ground prey')
            if hab in ('flier', 'waterbird'): s.append('flier')
            if hab in ('aquatic', 'semiaquatic'): s.append('swimmer')
            return s
        if layer == 'ground':
            s = []
            if self.flagged(e, layer): s.append('apex')
            if pred: s.append('meso')
            elif g == 'GZ': s.append('grazer')
            else: s.append('ground prey')
            return s
        if layer == 'flying':
            return (['apex'] if self.flagged(e, layer) else []) + ['flier']
        # water layers
        s = []
        flyer = hab in ('flier', 'waterbird')
        if flyer: return ['waterbird'] if not (layer == 'fresh' and sub == 'pool') else []
        wet = hab in ('aquatic', 'semiaquatic')
        if sub == 'pool':
            if pred: s.append('meso')
            elif wet: s.append('fish')
            return s
        if self.flagged(e, layer) and not (layer == 'fresh' and sub == 'river'): s.append('apex')
        if pred and (wet or hab == 'land'): s.append('meso')
        if hab == 'aquatic' and not pred:
            s.append('pelagic' if (g == 'PE' and layer == 'ocean') else 'fish')
        if hab in ('semiaquatic', 'land'): s.append('shore')
        return [x for x in s if x in SLOTS[self.slot_key(layer, sub)]]

    @staticmethod
    def slot_key(layer, sub):
        if layer == 'fresh': return 'fresh:' + sub
        if layer.startswith('cavern'): return 'cavern'
        return layer

    # ------------------------------------------------------------------ the food web, after the draw
    TIER = {'apex': 3, 'meso': 2, 'sentient': 2, 'grazer': 1, 'ground prey': 1, 'pelagic': 1}

    def tier(self, c):
        if c['vermin']: return 0
        t = self.TIER.get(c['slot'])
        if t is not None: return t
        return 2 if self.predator(c['e']) else 1     # flier, waterbird, shore, fish, swimmer

    def diet_code(self, c):
        s, e = c['slot'], c['e']
        if s == 'apex': return 'APX'
        if s in ('meso', 'sentient'): return 'MW' if e['habitat'] == 'aquatic' else 'ML'
        if s in ('flier', 'waterbird'): return 'RP' if self.predator(e) else 'LB'
        return e['guild']

    def eats(self, a, b):
        if a['vermin']: return False
        ea, eb = a['e'], b['e']
        shore_like = a['slot'] in ('shore', 'waterbird') or (a['slot'] in ('flier', 'swimmer') and ea['habitat'] in ('semiaquatic', 'waterbird'))
        if b['vermin']:
            d, _ = self.E.vdiet(ea, self.diet_code(a), 'cavern' if a['layer'].startswith('cavern') else 'land')
            if shore_like and self.predator(ea): d = set(d) | {'VF'}
            return b['vclass'] in d
        if self.tier(a) <= self.tier(b): return False
        if shore_like and eb['habitat'] == 'aquatic':
            return eb['mass'] <= max(ea['mass'], POOL_CAP)
        if not REACH.get(ea['habitat'], REACH['land']).get(eb['habitat'], False): return False
        return True

    # ------------------------------------------------------------------ one season cast
    def weight(self, c, used, layer):
        e, w = c['e'], 1.0
        if self.predator(e) and not e['benign'] and e['cmax'] > 1: w *= CAST_DEF['pack']
        w *= CAST_DEF['reuse'] ** used.get(e['token'], 0)
        if e['giant']: w *= CAST_DEF['giant']
        if e['ap'] and not e['civ']: w *= R0['ap_pick']
        if layer.startswith('cavern') and e.get('weird') is not None: w *= weird_weight(int(layer[-1]), e['weird'])
        return w

    def high_value(self, cands):
        k = math.ceil(len(cands) * CAST_DEF['hv_top']) if cands else 0
        why = {}
        def note(c, w): why[c['e']['token']] = (why.get(c['e']['token'], '') + ', ' + w).lstrip(', ')
        for c in cands:
            if c['e']['war']: note(c, 'war')
        for fld, label in (('pet', 'pet'), ('mass', 'size')):
            lst = sorted([c for c in cands if c['e'][fld] > 0], key=lambda c: (-c['e'][fld], c['e']['token']))
            for c in lst[:k]: note(c, f'{label} {c["e"][fld]:,}')
        return why

    def cast(self, lst, layer, sub, season, used, rng):
        key = self.slot_key(layer, sub)
        table = SLOTS[key]
        want = {s: rng.randint(lo, hi) for s, (lo, hi) in table.items() if s != '_vermin'}
        vwant = rng.randint(*table['_vermin'])
        cands = [c for c in lst if not c['vermin']]
        verm = [c for c in lst if c['vermin']]
        tr = {'want': dict(want), 'vermin_want': vwant, 'log': []}
        members, have, taken = [], {s: 0 for s in want}, set()
        def put(c, slot, how, frm=None):
            c = dict(c, slot=slot); members.append(c); have[slot] += 1; taken.add(c['e']['token'])
            tr['log'].append({'species': c['e']['token'], 'slot': slot, 'how': how, 'from': frm})
            return c
        def pick(pool):
            ws = [self.weight(c, used, layer) for c in pool]
            tot = sum(ws)
            if tot <= 0: return None
            r = rng.random() * tot
            for c, w in zip(pool, ws):
                r -= w
                if r <= 0: return c
            return pool[-1]
        # apex: the mix (largest flagged in season), else the largest non-sentient predator is promoted
        rank = sorted([c for c in cands if 'apex' in c['slots']], key=lambda c: (-c['e']['mass'], c['e']['token']))
        tr['apex_rank'] = [(c['e']['token'], c['e']['mass']) for c in rank]
        tr['apex_rule'] = None
        if 'apex' in want:
            if rank:
                put(rank[0], 'apex', 'apex: largest flagged predator'); tr['apex_rule'] = 'largest flagged predator'
            else:
                pr = sorted([c for c in cands if 'meso' in c['slots'] and not c['e']['sentient']], key=lambda c: (-c['e']['mass'], c['e']['token']))
                if pr:
                    put(pr[0], 'apex', 'apex: largest predator (none flagged)'); tr['apex_rule'] = 'largest predator promoted (none flagged)'
                    tr['apex_rank'] = [(c['e']['token'], c['e']['mass']) for c in pr[:6]]
        def room(c): return [s for s in c['slots'] if s in want and have[s] < want[s] and s != 'apex']
        # seed: high value, not sentient, with room
        free = [c for c in cands if c['e']['token'] not in taken and room(c)]
        hv = self.high_value(free)
        tr['hv'] = hv
        seeds = [c for c in free if c['e']['token'] in hv and not c['e']['sentient'] and not c['e']['ap']]
        direct = layer == 'flying'            # land-flying: draw the slots, the web comes after (user)
        if not direct and seeds:
            s = pick(seeds)
            if s:
                slot = max(room(s), key=lambda x: (want[x] - have[x]) / want[x])
                put(s, slot, 'seed (' + hv[s['e']['token']] + ')')
        # growth along the food web into the emptiest slot; a slot nothing links to is filled anyway
        guard = 0
        while guard < 200:
            guard += 1
            open_ = [s for s in want if have[s] < want[s]]
            if not open_: break
            free = [c for c in cands if c['e']['token'] not in taken and room(c)]
            if not free: break
            linked = []
            if not direct:
                order = rng.sample(members, len(members))   # as the engine: growth starts from a random cast member
                for c in free:
                    for m in order:
                        if self.eats(dict(c, slot=room(c)[0], layer=layer), dict(m, layer=layer)) or self.eats(dict(m, layer=layer), dict(c, slot=room(c)[0], layer=layer)):
                            linked.append((c, m)); break
            if linked:
                best = max((want[s] - have[s]) / want[s] for c, _ in linked for s in room(c))
                top = [(c, m) for c, m in linked if any((want[s] - have[s]) / want[s] == best for s in room(c))]
                c = pick([c for c, _ in top])
                frm = next(m for cc, m in top if cc is c)
                slot = next(s for s in room(c) if (want[s] - have[s]) / want[s] == best)
                rel = 'its prey' if self.eats(dict(frm, layer=layer), dict(c, slot=slot, layer=layer)) else 'its predator'
                put(c, slot, f'linked ({rel} of {frm["e"]["token"]})', frm['e']['token'])
            else:
                s = max(open_, key=lambda x: (want[x] - have[x]) / want[x])
                el = [c for c in free if s in room(c)]
                if not el:
                    want[s] = have[s]; continue
                c = pick(el)
                put(c, s, 'drawn (slot fill)' if direct else 'no link: filled anyway')
        unfilled = {}
        for s, (lo, hi) in table.items():
            if s == '_vermin': continue
            if have.get(s, 0) < tr['want'][s]:
                n = sum(1 for c in cands if s in c['slots'])
                unfilled[s] = f'{have.get(s, 0)} of {tr["want"][s]}: ' + ('none in season' if n == 0 else 'all candidates used in other slots')
        # vermin: what the members eat, one per class first, then any
        ms = [dict(m, layer=layer) for m in members]
        eaten = {}
        for v in verm:
            n = sum(1 for m in ms if self.eats(m, v))
            eaten[v['e']['token']] = n
        order = sorted([v for v in verm if v['e']['token'] not in taken], key=lambda v: (-eaten[v['e']['token']], rng.random()))
        vsel, seen = [], set()
        for v in order:
            if len(vsel) >= vwant: break
            if eaten[v['e']['token']] and v['vclass'] not in seen: seen.add(v['vclass']); vsel.append(v)
        for v in order:
            if len(vsel) >= vwant: break
            if v not in vsel: vsel.append(v)
        # the web, after the draw
        allm = ms + [dict(v, slot='vermin', layer=layer) for v in vsel]
        edges = [(a['e']['token'], b['e']['token']) for a in allm for b in allm if a is not b and self.eats(a, b)]
        linked_set = {x for ed in edges for x in ed}
        for m in members: used[m['e']['token']] = used.get(m['e']['token'], 0) + 1
        ws = [m['e']['weird'] for m in members if m['e'].get('weird') is not None]
        tr.update(members=[(m['e']['token'], m['slot']) for m in members],
                  vermin=[(v['e']['token'], v['vclass'], eaten[v['e']['token']]) for v in vsel],
                  vermin_eligible=len(verm), unfilled=unfilled, edges=edges,
                  isolated=sorted(m['e']['token'] for m in members if m['e']['token'] not in linked_set),
                  weird=round(sum(ws) / len(ws), 2) if ws else None)
        return tr

    # ------------------------------------------------------------------ the whole embark
    def run(self, spec, year=250, site=1):
        pool, funnel, rejected = self.pool(spec)
        fbs = self.fort_biomes(spec)
        sub = self.fresh_subtype(spec)
        layer_sets, notes = {L: [] for L in LAYERS}, []
        for tok, e in pool.items():
            ls, ns = self.layers_of(e, spec, fbs)
            e['layers'] = ls
            for L in ls: layer_sets[L].append(tok)
            for L, why in ns: notes.append({'token': tok, 'layer': L, 'why': why})
        active = [L for L in LAYERS if layer_sets[L] and (L != 'ocean' or spec['water'].get('ocean'))
                  and (L != 'fresh' or sub) and (not L.startswith('cavern') or int(L[-1]) in (spec.get('caverns') or ()))]
        lists, casts, used = {}, {}, {}
        for L in active:
            for s in range(4):
                lst = []
                for tok in sorted(layer_sets[L]):
                    e = pool[tok]
                    if e['noSeason'][s]: continue
                    if e['gameVermin']:
                        vc = self.E.vclass(e)
                        lst.append({'e': e, 'vermin': True, 'vclass': vc, 'slots': ['vermin']})
                        # murky pools: DF's pool fish and amphibians are vermin, so the fish slot draws them too
                        if L == 'fresh' and sub == 'pool' and (vc == 'VF' or e['habitat'] == 'semiaquatic'):
                            lst.append({'e': e, 'vermin': False, 'slots': ['fish'], 'vermin_fish': True})
                    else:
                        sl = self.slots_for(e, L, sub)
                        if sl: lst.append({'e': e, 'vermin': False, 'slots': sl})
                lists[(L, s)] = lst
                seed = (site * 7919 + year * 104729 + s * 131 + LAYERS.index(L) * 17) % 2147483647
                casts[(L, s)] = self.cast(lst, L, sub, s, used, random.Random(seed))
        return {'pool': pool, 'funnel': funnel, 'rejected': rejected, 'notes': notes, 'layers': layer_sets, 'active': active,
                'sub': sub, 'lists': lists, 'casts': casts, 'fbs': fbs}
