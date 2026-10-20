"""castsim.engine: the seasonal-wildlife tool's pool -> roster -> season-cast pipeline, step by step, as the engine runs it.

Every rule below names the engine function it follows (scripts/seasonal-wildlife.lua, branch v7.4-onebuilder cd08293).
The engine's own constant tables (cast slots, ladder, tiers, reach, vermin diets, curated roles and water apexes, the
roster defaults, the 83 extinct corrections) are read from engine_tables.json, which `lua tests/web/harness.lua . tables`
prints from the engine itself, so the simulation follows the code rather than a copy of it.

Differences from the live engine, all named in the report:
  * the random draws (seed pick, growth, vermin shuffle) use Python's generator seeded with the engine's own formula,
    not DFHack's, so a simulated cast is one possible cast, not the rig's;
  * a fort's cave entries are not split by cavern depth in the population dump, so a cavern species' depths are its raw
    UNDERGROUND_DEPTH range within the three caverns;
  * ROSTER.context's deep-column test (ocean water 3+ levels deep) is given per example.
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path

from raws import Raws

T = json.loads((Path(__file__).parent / 'engine_tables.json').read_text())
R0 = T['roster']
CAST, CAST_DEF, TIER, LEVEL, VDIET, REACH = T['CAST'], T['CAST_DEF'], T['TIER'], T['LEVEL'], T['VDIET'], T['REACH']
TIER.setdefault('FAPX', 3)
ROLE, PREDG, FLY_SCAV, EXT = T['ROLE'], T['PREDG'], T['FLY_SCAV'], T['EXTINCT']
LARGE = T['MODEL_LARGE']
# per-token habitat and guild, ahead of the raws' reading (engine MODEL.HABITAT_OVERRIDE, MODEL.GUILD_OVERRIDE); design.py fills them
HABITAT_OVERRIDE, GUILD_OVERRIDE = {}, {}
SEASONS = ['Spring', 'Summer', 'Autumn', 'Winter']
TPY = 403200
WATER_PREFIX = ('OCEAN', 'POOL', 'LAKE', 'RIVER', 'SUBTERRANEAN_WATER')
INNUMERABLE = 10000001
POP_TYPES = {'Animal', 'Vermin', 'VerminInnumerable', 'ColonyInsect'}


def is_water(nm): return nm.startswith(WATER_PREFIX)


class Engine:
    def __init__(self, raws: Raws | None = None, align=None, classes=('natural',)):
        self.R = raws or Raws()
        self.align = align or {'good': False, 'evil': False}
        self.classes = set(classes)
        self._class = {}
        self._roots = {}
        for tok, b in self.R.src.items():   # MODEL.rootOf: COPY_TAGS_FROM + APPLY_CREATURE_VARIATION:ANIMAL_PERSON
            frm = next((t[1] for t in b['toks'] if t[0] == 'COPY_TAGS_FROM'), None)
            if frm and any(t[0] == 'APPLY_CREATURE_VARIATION' and t[1].startswith('ANIMAL_PERSON') for t in b['toks']):
                self._roots[tok] = frm

    # ---------------------------------------------------------------- classify (sw:1815) and its readers
    def eco_class(self, c):
        """V7.ecologyClassRaw (sw:1609) + V7.alignedNatural (v7 aligned / cave_aligned / fanciful, all on)"""
        why = []
        for f in ('MEGABEAST', 'SEMIMEGABEAST', 'TITAN'):
            if c['any'](f): why.append(f)
        if why: return 'mega', why
        for f in ('NIGHT_CREATURE_HUNTER', 'NIGHT_CREATURE_BOGEYMAN', 'NIGHT_CREATURE_ANY', 'NIGHT_CREATURE_EXPERIMENTER'):
            if c['any'](f): why.append(f)
        if why: return 'night', why
        if c['any']('NOT_LIVING'): why.append('NOT_LIVING')
        if c['any']('NO_EAT') and c['any']('NO_DRINK') and not c['any']('GRAZER') and not c['any']('CARNIVORE'): why.append('NO_EAT+NO_DRINK')
        if why: return 'unliving', why
        f = c['flags']
        for k in ('FANCIFUL', 'GOOD', 'EVIL'):
            if k in f: why.append(k)
        if why:
            good, evil = 'GOOD' in f, 'EVIL' in f
            if not good and not evil:
                return ('natural', ['FANCIFUL is art, not placement (v7)']) if why == ['FANCIFUL'] else ('mythic', why)
            if not c['biomes']: return 'mythic', why
            if all(b.startswith('SUBTERRANEAN') for b in c['biomes']): return 'natural', ['a cavern species: alignment only limits taming (v7)']
            if (good and self.align['good']) or (evil and self.align['evil']): return 'natural', ['aligned wildlife on a region of its alignment (v7)']
            return 'mythic', why
        if self.R.adult_size(c['token']) <= 0: why.append('no body size')
        if not c['biomes']: why.append('no BIOME flags')
        if why: return 'unclassified', why
        return 'natural', ['biome flags + body size']

    def classify(self, tok):
        if tok in self._class: return self._class[tok]
        c = self.R.creature(tok)
        f = c['flags']
        vermin = bool(f & {'VERMIN_GROUNDER', 'VERMIN_ROTTER', 'VERMIN_SOIL', 'VERMIN_FISH', 'VERMIN_EATER', 'SMALL_RACE'})
        role = ROLE.get(tok) or ('predator' if any(c['any'](x) for x in ('CARNIVORE', 'BONECARN', 'LARGE_PREDATOR', 'AMBUSHPREDATOR')) else 'prey')
        water = any(is_water(b) for b in c['biomes']); land = any(not is_water(b) for b in c['biomes'])
        flier = c['any']('FLIER')
        if tok in HABITAT_OVERRIDE: hab = HABITAT_OVERRIDE[tok]
        elif c['any']('IMMOBILE_LAND') or c['any']('CANNOT_BREATHE_AIR'): hab = 'aquatic'      # MODEL.habitat (sw:1917)
        elif flier: hab = 'waterbird' if water else 'flier'
        elif c['any']('CAN_BREATHE_WATER') or (water and not land): hab = 'semiaquatic'
        else: hab = 'land'
        bodies = set()
        for b in c['biomes']:                                                                        # MODEL.waters (sw:1936)
            if b.startswith('OCEAN'): bodies.add('ocean')
            elif b == 'SUBTERRANEAN_WATER': bodies.add('cavern')
            else:
                p = b.split('_')
                if p[0] in ('LAKE', 'RIVER', 'POOL'): bodies.add(p[0].lower())
        cl = c['cluster'] or (1, 1)
        eco, ecowhy = self.eco_class(c)
        d = c['depth']
        out = dict(token=tok, category='vermin' if vermin else role, role=role, habitat=hab, aquatic=hab in ('aquatic', 'semiaquatic'),
                   bodies=bodies, flier=flier, gameVermin=vermin, mass=self.R.adult_size(tok), group=max(1, (cl[0] + cl[1]) // 2),
                   cmin=min(cl), cmax=max(cl), largePred=c['any']('LARGE_PREDATOR'), carnivore=c['any']('CARNIVORE'),
                   benign=c['every']('BENIGN') and ROLE.get(tok) != 'predator',
                   noSeason={s: c['every'](n) for s, n in enumerate(('NO_SPRING', 'NO_SUMMER', 'NO_AUTUMN', 'NO_WINTER'))},
                   giant=('GIANT' in c['variations']) or tok.startswith('GIANT_'),
                   sentient=c['any']('CAN_SPEAK') or c['any']('CAN_LEARN'), good='GOOD' in f, evil='EVIL' in f, savage='SAVAGE' in f,
                   monster=('GOOD' in f) or ('EVIL' in f), depthLo=d[0] if d and d[1] > 0 else None, depthHi=d[1] if d and d[1] > 0 else None,
                   fireOnly=bool(c['biomes']) and all(b == 'SUBTERRANEAN_LAVA' for b in c['biomes']),
                   gobble=sorted(g for g in c['gobble'] if not g.startswith('SWV_')), cclass=c['cclass'],
                   mega=c['any']('MEGABEAST') or c['any']('SEMIMEGABEAST') or c['any']('TITAN'),
                   night=any(c['any'](x) for x in ('NIGHT_CREATURE_HUNTER', 'NIGHT_CREATURE_BOGEYMAN', 'NIGHT_CREATURE_ANY', 'NIGHT_CREATURE_EXPERIMENTER')),
                   eco=eco, ecoWhy=ecowhy, pet=c['pet'], war=c['any']('TRAINABLE_WAR'), freq=c['freq'], biomes=c['biomes'],
                   extinct=c['extinct'], ap=False, apVermin=False, root=None, fixes=[])
        root = None if vermin else self._roots.get(tok)
        if root and root in self.R.src:                                                               # the root mirror (sw:1879)
            r = self.classify(root)
            for k in ('category', 'role', 'habitat', 'bodies', 'aquatic', 'flier', 'largePred', 'carnivore'): out[k] = r[k]
            if out['mass'] == r['mass']: out['mass'] = (r['mass'] + 70000) // 2
            out.update(root=root, ap=True, sentient=True)
            if r['gameVermin']: out.update(apVermin=True, role='predator', category='predator')
        out['guild'] = self.guild(c, out)                                                             # MODEL.guild (sw:1962)
        self.extinct_fix(tok, out)                                                                    # V7.EXTINCT.model (sw:14403)
        out['civ'] = self.is_civ(c, out)                                                              # V7.isCivRaw (sw:2282)
        out['locked'] = out['eco'] not in self.classes
        self._class[tok] = out
        return out

    def guild(self, c, o):
        if o['gameVermin']: return 'V'
        if o['apVermin']: return 'RP' if o['flier'] else ('MW' if o['habitat'] == 'aquatic' else 'ML')
        if c['token'] in GUILD_OVERRIDE: return GUILD_OVERRIDE[c['token']]
        aquatic = o['habitat'] == 'aquatic'
        amphib = (not aquatic) and c['any']('CAN_BREATHE_WATER')
        lp, flier = o['largePred'], o['flier']
        diet = c['any']('CARNIVORE') or c['any']('BONECARN') or ROLE.get(c['token']) == 'predator'
        if lp and not flier and (aquatic or amphib): return 'AW'
        if flier and (diet or lp): return 'RP'
        if lp: return 'AL'
        if diet: return 'MW' if aquatic else 'ML'
        if c['any']('GRAZER'): return 'GZ'
        water = any(is_water(b) for b in c['biomes']); land = any(not is_water(b) for b in c['biomes'])
        if flier: return 'WB' if water else 'LB'
        if aquatic: return ('PE' if o['mass'] >= 1000000 else 'FC') if 'ocean' in o['bodies'] else 'FF'
        if amphib or (water and not land): return 'SH'
        return 'PL'

    def extinct_fix(self, tok, o):
        t, own = EXT.get(tok), True
        if not t and o['ap'] and o['root']: t, own = EXT.get(o['root']), False
        if not t: return
        if own:
            for k, fld in (('lp', 'largePred'), ('carn', 'carnivore'), ('benign', 'benign')):
                if k in t: o[fld] = t[k]; o['fixes'].append(f'{fld}={t[k]}')
            if t.get('habitat'):
                o['habitat'] = t['habitat']; o['aquatic'] = t['habitat'] in ('aquatic', 'semiaquatic'); o['fixes'].append('habitat=' + t['habitat'])
            if (o['largePred'] or o['carnivore']) and o['role'] != 'predator':
                o['role'] = 'predator'
                if not o['gameVermin']: o['category'] = 'predator'
        if t.get('guild'): o['guild'] = t['guild']; o['fixes'].append('guild=' + t['guild'])
        if t.get('grazer') and o['guild'] == 'PL': o['guild'] = 'GZ'; o['fixes'].append('guild=GZ (grazer)')
        if own and t.get('cluster'):
            o['cmin'], o['cmax'] = t['cluster'][0], t['cluster'][1]; o['group'] = max(1, (o['cmin'] + o['cmax']) // 2)

    def is_civ(self, c, o):
        if not o['sentient']: return False
        if o['good'] or o['evil']: return False
        if o['root']:
            if not self.classify(o['root'])['gameVermin']: return False
        return any(b.startswith('SUBTERRANEAN') for b in c['biomes'])

    # ---------------------------------------------------------------- buildPool (sw:2351)
    def build_pool(self, pops):
        """pops: [{'race': TOKEN, 'layer': land|water|cavern|deep, 'type': ..., 'quantity': n, 'depths': {d}}] -- the managed
        population entries of the embark (managedPop, sw:1448). Returns the pool entries by key and the filter log."""
        log = {'not_creature_type': [], 'innumerable': [], 'deep': []}
        pool = {}
        for p in pops:
            if p['type'] not in POP_TYPES: log['not_creature_type'].append(p['race']); continue
            if p['quantity'] >= INNUMERABLE: log['innumerable'].append(p['race']); continue
            if p['race'] not in self.R.src: continue
            L = p['layer']
            if L == 'deep': log['deep'].append(p['race']); continue   # R60: the deep layer is never managed
            key = p['race'] if L == 'land' else f'{L}:{p["race"]}'
            info = self.classify(p['race'])
            e = pool.get(key)
            if not e:
                e = dict(info); e.update(key=key, layer=L, inEmbark=True, depths=set(), quantity=0, entries=0)
                pool[key] = e
            e['entries'] += 1
            e['quantity'] = max(e['quantity'], p['quantity'])
            if L == 'cavern': e['depths'] |= set(p.get('depths') or ())
        for k in log: log[k] = sorted(set(log[k]))
        return pool, log

    # ---------------------------------------------------------------- partitions and slots
    def in_part(self, e, part):
        """ROSTER.inPart (sw:7899); returns (bool, reason)"""
        if not e['inEmbark']: return False, 'not stocked on this embark'
        if e['locked']: return False, f'locked class ({e["eco"]}: {", ".join(e["ecoWhy"])})'
        if e['category'] == 'vermin': return False, 'vermin (the vermin slots take them)'
        if e['mega'] or e['night']: return False, 'megabeast or night creature'
        if part == 'cavern':
            if e['layer'] != 'cavern': return False, 'not a cavern entry'
            if e['fireOnly']: return False, 'lava-only (R28)'
            if e['depths']:
                ok = [d for d in e['depths'] if self.depth_ok(e, d)]
                return (True, '') if ok else (False, 'outside its raw depth range')
            return True, ''
        if e['layer'] == 'water': return (part == 'water'), ('a water entry' if part != 'water' else '')
        if e['layer'] != 'land': return False, 'not a land entry'
        fly = e['habitat'] in ('flier', 'waterbird')
        kind = R0['aquatic_apex'].get(e['token'])
        to_water = e['habitat'] == 'aquatic' or (kind is not None and kind != 'fisher' and e['habitat'] == 'semiaquatic')
        if part == 'water': return to_water, '' if to_water else 'a land animal'
        if part == 'flying': return fly, '' if fly else 'does not fly'
        ok = part == 'land' and not fly and not to_water
        return ok, '' if ok else ('flies (flying partition)' if fly else 'swims (water partition)')

    @staticmethod
    def depth_ok(e, d):
        lo, hi = e['depthLo'], e['depthHi']
        if not lo or not hi: return True
        return lo <= d + 1 <= hi

    def boosted(self, e):
        if e['guild'] not in PREDG: return False
        if e['mass'] >= LARGE: return True
        return bool(e['giant'] and R0['giant_boost'])

    def fly_apex(self, e):
        if e['guild'] != 'RP' or e['sentient'] or e['layer'] == 'cavern': return False
        if e['token'] in FLY_SCAV: return False
        return e['mass'] >= R0['fly_apex_min'] or self.boosted(e)

    def slot_of(self, e, part):
        """ROSTER.slotOf (sw:7849)"""
        g = e['guild']
        if e['civ']:   # civ_prey on
            return ('MW' if e['habitat'] == 'aquatic' else 'ML') if g in ('AL', 'AW') else g
        if part == 'water':
            kind = R0['aquatic_apex'].get(e['token'])
            if kind == 'pelagic': return 'APE'
            if kind in ('apex', 'fisher'): return 'APX'
            if g in ('AW', 'AL', 'ML'): return 'MW'
            return g
        if part == 'flying': return 'APX' if self.fly_apex(e) else g
        if g in ('AL', 'AW') or self.boosted(e): return 'APX'
        return g

    def tier(self, e, part): return TIER.get(self.slot_of(e, part), 1)

    def family(self, tok):
        """VERMIN.family (sw:3306)"""
        c = self.R.creature(tok)
        if 'VERMIN_FISH' in c['flags'] or c['any']('IMMOBILE_LAND') or c['any']('CANNOT_BREATHE_AIR'): return 'fish'
        if c['any']('VERMIN_MICRO') or 'VERMIN_ROTTER' in c['flags']: return 'flies'
        if 'VERMIN_SOIL_COLONY' in c['flags']: return 'colony'
        if 'VERMIN_SOIL' in c['flags']: return 'soil'
        if 'MAMMAL' in c['cclass']: return 'mammals'
        if c['any']('FLIER'): return 'fliers'
        return 'crawlers'

    def vclass(self, e):
        """ROSTER.vclass (sw:8145)"""
        c = self.R.creature(e['token'])
        fam = self.family(e['token'])
        if fam == 'fish': return 'VF'
        if fam == 'colony': return 'VC'
        if fam == 'fliers' or (fam == 'mammals' and e['flier']):
            bird = c['any']('FLIER') and c['any']('LAYS_EGGS') and 'MAMMAL' not in c['cclass']
            return 'VB' if (bird or 'MAMMAL' in c['cclass']) else 'VI'
        if fam == 'flies': return 'VI'
        return 'VG'

    def vdiet(self, e, code, part):
        base = VDIET.get(code)
        if code == 'APX' and e['habitat'] not in ('aquatic', 'semiaquatic'): base = None
        d = set((base or {}).keys())
        if part == 'cavern' and code == 'LB': d |= {'VB', 'VI', 'VG'}
        if e['apVermin']: d |= {'VG', 'VI', 'VF'}
        only = False
        if e['gobble']: only = not d; d |= {'VG', 'VC'}
        return d, only

    def reaches(self, a, b):
        """MODEL.reaches (sw:2589)"""
        if a['mega'] or a['night'] or b['mega'] or b['night']: return False
        if b['token'] in T['NEVER_PREY']: return False
        if a['eco'] != b['eco']: return False
        if (a['layer'] == 'cavern') != (b['layer'] == 'cavern'): return False
        if not REACH.get(a['habitat'], REACH['land']).get(b['habitat'], False): return False
        if a['aquatic'] and b['aquatic'] and a['bodies'] and b['bodies'] and not (a['bodies'] & b['bodies']): return False
        return True

    # ---------------------------------------------------------------- the season cast (ROSTER.castPool .. castGrow)
    def cast_slot(self, e, part, layer):
        code = self.slot_of(e, part)
        if layer == 'land' and part == 'flying' and code == 'APX': code = 'FAPX'
        for s in CAST[layer]['slots']:
            if code in s['codes']: return s['name'], code
        return None, code

    def vermin_ok(self, e, layer):
        if e['category'] != 'vermin' or not e['inEmbark'] or e['locked']: return False
        if layer == 'cavern': return e['layer'] == 'cavern'
        if e['layer'] in ('cavern', 'deep'): return False
        if layer == 'water': return e['layer'] == 'water' or (e['layer'] == 'land' and self.vclass(e) == 'VF')
        return e['layer'] == 'land' and self.vclass(e) != 'VF'

    def cast_pool(self, pool, layer, season, trace):
        """ROSTER.castPool (sw:8596) with the per-step reasons kept for the report"""
        L = CAST[layer]
        cands, by_key = [], {}
        out_part, out_season = {}, []
        # v7.4 (sw 834f92e): one candidate per species, the layer's own entry first (as vermin)
        toks, same_species = set(), []
        for own in (True, False):
            for part in L['parts']:
                for e in sorted(pool.values(), key=lambda x: x['key']):
                    if (e['layer'] == layer) != own or e['key'] in by_key: continue
                    ok, why = self.in_part(e, part)
                    if not ok:
                        if why and part == L['parts'][-1] and e['key'] not in by_key and e['category'] != 'vermin':
                            out_part.setdefault(e['key'], why)
                        continue
                    out_part.pop(e['key'], None)
                    if e['noSeason'][season]:
                        if e['token'] not in out_season: out_season.append(e['token'])
                        continue
                    if e['token'] in toks:
                        same_species.append(e['key']); continue
                    slot, code = self.cast_slot(e, part, layer)
                    c = dict(e=e, part=part, slot=slot, code=code, vermin=False)
                    cands.append(c); by_key[e['key']] = c; toks.add(e['token'])
        vermin_out = []
        for own in (True, False):
            for e in sorted(pool.values(), key=lambda x: x['key']):
                if (e['layer'] == layer) != own or e['key'] in by_key or e['token'] in toks: continue
                if not self.vermin_ok(e, layer): continue
                if e['noSeason'][season]: vermin_out.append(e['token']); continue
                c = dict(e=e, part=L['parts'][0], vermin=True, vclass=self.vclass(e), slot=None, code='V')
                cands.append(c); by_key[e['key']] = c; toks.add(e['token'])
        cands.sort(key=lambda c: c['e']['key'])
        trace.update(not_in_layer={k: v for k, v in out_part.items() if pool[k]['layer'] in ((layer,) if layer != 'land' else ('land',))},
                     out_of_season=sorted(out_season), vermin_out_of_season=sorted(vermin_out),
                     same_species=sorted(same_species))
        return cands, by_key

    def rank_apex(self, cands, layer):
        """ROSTER.castRankApex (v7.4 'the mix')"""
        L = CAST[layer]
        def slot_for(code):
            for s in L['slots']:
                if code in s['codes']: return s['name']
        flagged = [c for c in cands if not c['vermin'] and c['code'] in ('APX', 'APE')]
        big = lambda c: (-c['e']['mass'], c['e']['key'])
        if flagged:
            flagged.sort(key=big)
            demoted = []
            for c in flagged[1:]:
                meso = 'MW' if (layer == 'water' or c['e']['habitat'] in ('aquatic', 'semiaquatic')) else 'ML'
                if not slot_for(meso): meso = 'ML' if meso == 'MW' else 'MW'
                c['code'], c['slot'], c['ranked'] = meso, slot_for(meso), 'meso by size'
                demoted.append(c)
            flagged[0]['ranked'] = 'apex by size'
            return {'apex': flagged[0]['e']['token'], 'rule': 'largest flagged predator',
                    'ranked': [(c['e']['token'], c['e']['mass'], 'apex' if i == 0 else 'meso') for i, c in enumerate(flagged)]}
        pr = [c for c in cands if not c['vermin'] and c['code'] in ('ML', 'MW') and not (c['e']['civ'] or c['e']['ap'] or c['e']['sentient'])]
        if not pr: return {'apex': None, 'rule': 'no flagged predator and no mesopredator in season', 'ranked': []}
        pr.sort(key=big)
        pr[0]['code'], pr[0]['slot'], pr[0]['ranked'] = 'APX', slot_for('APX'), 'apex: largest predator (none flagged)'
        return {'apex': pr[0]['e']['token'], 'rule': 'largest mesopredator (none flagged)', 'ranked': [(c['e']['token'], c['e']['mass'], 'apex' if i == 0 else 'meso') for i, c in enumerate(pr)]}

    def eats(self, a, b):
        """ROSTER.castEats (sw:8624), the ranked codes' tiers"""
        if a['vermin']: return False
        if b['vermin']:
            d, _ = self.vdiet(a['e'], a['code'], a['part'])
            return b['vclass'] in d
        if TIER.get(a['code'], 1) <= TIER.get(b['code'], 1): return False
        if not self.reaches(a['e'], b['e']): return False
        da, db = a['e']['depths'], b['e']['depths']
        if da and db: return bool(da & db)
        return True

    def high_value(self, cands):
        """ROSTER.hvSet (v7.4): war-trainable, or top ceil(n/10) by pet value (a giant reads its root's), or by size"""
        k = math.ceil(len(cands) * CAST_DEF['hv_top'])
        rows = []
        for c in cands:
            e = c['e']
            pet = e['pet']
            if e['giant']:
                root = self.R.creature(e['token'])['root']
                if root and root in self.R.src: pet = self.R.creature(root)['pet']
            rows.append((c, pet, e['war'], e['mass']))
        why = {}
        def note(c, w): why[c['e']['key']] = (why.get(c['e']['key'], '') + ', ' + w).lstrip(', ')
        for c, pet, war, m in rows:
            if war: note(c, 'war-trainable')
        for idx, label in ((1, 'pet'), (3, 'size')):
            other = 3 if idx == 1 else 1
            lst = sorted([r for r in rows if r[idx] > 0], key=lambda r: (-r[idx], -r[other], r[0]['e']['key']))
            for r in lst[:k]: note(r[0], f'{label} {r[idx]:,}')
        return why, k, rows

    def grow(self, pool, layer, season, used, rng):
        """ROSTER.castGrow (sw:8659): returns the cast and a full trace"""
        tr = {'layer': layer, 'season': SEASONS[season]}
        cands, by_key = self.cast_pool(pool, layer, season, tr)
        tr['candidates'] = [(c['e']['token'], c['code'], c['slot'], 'vermin ' + c['vclass'] if c['vermin'] else c['e']['guild']) for c in cands]
        tr['apex_rank'] = self.rank_apex(cands, layer)
        eats, nb = {}, {}
        for a in cands:
            for b in cands:
                if a is not b and self.eats(a, b):
                    eats.setdefault(a['e']['key'], set()).add(b['e']['key'])
                    nb.setdefault(a['e']['key'], set()).add(b['e']['key']); nb.setdefault(b['e']['key'], set()).add(a['e']['key'])
        tr['web_edges'] = sum(len(v) for v in eats.values())
        excl = {}
        for c in cands:
            if not c['vermin'] and not c['slot']: excl[c['e']['key']] = f'no cast slot for its code {c["code"]}'
        changed = True
        while changed:
            changed = False
            for c in cands:
                k = c['e']['key']
                if k in excl: continue
                if not any(j not in excl for j in nb.get(k, ())):
                    excl[k] = 'linked only to species that cannot be cast' if nb.get(k) else 'no prey and no predator in the pool'
                    changed = True
        tr['excluded'] = {by_key[k]['e']['token']: v for k, v in excl.items() if not by_key[k]['vermin']}
        sn_on = R0['sn_slots']
        want = {s['name']: (0 if s['name'] == 'sentient' and not sn_on else s['want']) for s in CAST[layer]['slots']}
        have = {n: 0 for n in want}
        slots = {n: [] for n in want}
        def weight(c):
            e, w = c['e'], 1.0
            if TIER.get(c['code'], 1) >= 2 and not e['benign'] and e['cmax'] > 1: w *= CAST_DEF['pack']
            w *= CAST_DEF['reuse'] ** used.get(e['key'], 0)
            if e['giant']: w *= CAST_DEF['giant']
            if e['ap'] and not e['civ']: w *= R0['ap_pick']
            return w
        def pick(lst):
            tot = sum(weight(c) for c in lst)
            if tot <= 0: return None
            roll = rng.random() * tot
            for c in lst:
                roll -= weight(c)
                if roll <= 0: return c
            return lst[-1]
        allc = [c for c in cands if not c['vermin']]
        anyc = [c for c in allc if c['e']['key'] not in excl]
        hv, k, rows = self.high_value(allc)
        tr['high_value'] = {'k': k, 'n': len(allc), 'flagged': {by_key[key]['e']['token']: w for key, w in hv.items()},
                            'pet_rank': [(r[0]['e']['token'], r[1]) for r in sorted(rows, key=lambda r: -r[1])[:max(k, 3)]],
                            'size_rank': [(r[0]['e']['token'], r[3]) for r in sorted(rows, key=lambda r: -r[3])[:max(k, 3)]],
                            # every non-vermin candidate, for the report's sortable table: token, pet, war, size, why not a seed
                            'all': [(r[0]['e']['token'], r[1], bool(r[2]), r[3],
                                     'never castable' if r[0]['e']['key'] in excl else
                                     'sentient' if (r[0]['e']['ap'] or r[0]['e']['civ'] or r[0]['e']['sentient']) else '') for r in rows]}
        plain = [c for c in anyc if not (c['e']['ap'] or c['e']['civ'] or c['e']['sentient'])]
        seeds = [c for c in plain if c['e']['key'] in hv]
        tr['seed_pool'] = [(c['e']['token'], round(weight(c), 4)) for c in seeds]
        tr['seed_blocked'] = sorted(by_key[key]['e']['token'] for key in hv if key in excl or by_key[key]['e']['ap'] or by_key[key]['e']['civ'] or by_key[key]['e']['sentient'])
        seed = pick(seeds) or pick(plain)
        members, in_cast, log = [], set(), []
        def add(c, frm=None):
            members.append(c); in_cast.add(c['e']['key'])
            have[c['slot']] += 1; slots[c['slot']].append(c['e']['token'])
            if frm: log.append((frm['e']['token'], c['e']['token'], c['slot'], 'its prey' if c['e']['key'] in eats.get(frm['e']['key'], ()) else 'its predator'))
        if not seed:
            tr.update(seed=None, members=[], slots=slots, log=[], vermin=[], unfilled={n: 'empty pool' for n in want}); return tr, []
        tr['seed'] = seed['e']['token']; tr['seed_why'] = hv.get(seed['e']['key'], 'no high-value species can be cast: any linked one')
        add(seed)
        tried, guard = set(), 0
        while guard < 400:
            guard += 1
            room = {n for n, w in want.items() if have[n] < w}
            if not room: break
            open_ = [c for c in members if c['e']['key'] not in tried]
            if not open_: break
            m = open_[rng.randrange(len(open_))]
            cs = [by_key[j] for j in sorted(nb.get(m['e']['key'], ())) if not by_key[j]['vermin'] and j not in in_cast and j not in excl
                  and by_key[j]['slot'] in room]
            if not cs: tried.add(m['e']['key']); continue
            best = max((want[c['slot']] - have[c['slot']]) / want[c['slot']] for c in cs)
            top = sorted([c for c in cs if (want[c['slot']] - have[c['slot']]) / want[c['slot']] == best], key=lambda c: c['e']['key'])
            c = pick(top)
            if c: add(c, m)
            else: tried.add(m['e']['key'])
        unfilled = {}
        for n, w in want.items():
            if have[n] < w:
                avail = sum(1 for c in allc if c['slot'] == n and c['e']['key'] not in excl)
                unfilled[n] = f'{have[n]} of {w}: ' + ('none in season in the pool' if avail == 0 else f'no link to the cast from the {avail} in the pool')
        eaten = {}
        for c in members:
            for j in eats.get(c['e']['key'], ()):
                if by_key[j]['vermin']: eaten[j] = eaten.get(j, 0) + 1
        vl = sorted(eaten)
        rng.shuffle(vl)
        vermin, seen = [], set()
        for j in vl:
            if len(vermin) >= CAST[layer]['vermin']: break
            if by_key[j]['vclass'] not in seen: seen.add(by_key[j]['vclass']); vermin.append(j)
        for j in sorted(vl, key=lambda j: (-eaten[j], j)):
            if len(vermin) >= CAST[layer]['vermin']: break
            if j not in vermin: vermin.append(j)
        all_in = in_cast | set(vermin)
        edges = sorted((by_key[a]['e']['token'], by_key[b]['e']['token']) for a, t in eats.items() if a in all_in for b in t if b in all_in)
        tr.update(members=[(c['e']['token'], c['slot'], c['code']) for c in members], slots=slots, log=log,
                  vermin=[(by_key[j]['e']['token'], by_key[j]['vclass'], eaten[j]) for j in vermin], unfilled=unfilled, edges=edges,
                  eligible_vermin=len(eaten))
        return tr, [c for c in members] + [by_key[j] for j in vermin]

    def cast_year(self, pool, site=1, year=250, salt=0, layers=('land', 'water', 'cavern')):
        """ROSTER.castYear (sw:8820): every layer, every season; the roster written; the ladder (castLadder)"""
        used, traces, seasons_of, codes = {}, {}, {}, {}
        for layer in layers:
            for s in range(4):
                seed = (site * 7919 + year * 104729 + s * 131 + len(layer) * 17 + salt) % 2147483647
                tr, cast = self.grow(pool, layer, s, used, random.Random(seed))
                traces[(layer, s)] = tr
                for c in cast:
                    seasons_of.setdefault(c['e']['key'], []).append(s)
                    if not c['vermin']: codes.setdefault(c['e']['key'], (layer, c['part'], c['code']))
                for c in cast:
                    if not c['vermin']: used[c['e']['key']] = used.get(c['e']['key'], 0) + 1
        roster = {'cast': {}, 'resting': []}
        for e in pool.values():
            if e['key'] in seasons_of: roster['cast'][e['key']] = sorted(set(seasons_of[e['key']]))
            elif e['inEmbark'] and not e['mega'] and not e['night']: roster['resting'].append(e['key'])
        roster['ladder'] = self.ladder(pool, codes)
        return traces, roster

    def ladder(self, pool, codes, ctx=None):
        """ROSTER.castLadder + ROSTER.ladder (sw:8044): FREQUENCY per member by partition (units, pyramid, biomass guard)"""
        ctx = ctx or {}
        out = {}
        by_part = {}
        for key, (layer, part, code) in codes.items():
            by_part.setdefault(part, []).append((pool[key], 'APX' if code == 'FAPX' else code))
        for part, members in by_part.items():
            fam = T['LADDER22'].get(part, T['LADDER22']['land'])
            pk = ('ocean' if ctx.get('ocean') else 'lake') if part == 'water' else part
            tgt = R0['pyramid'].get(pk, R0['pyramid']['land'])
            by_slot, apex = {}, []
            for e, code in members:
                if LEVEL.get(code) == 'A': apex.append(e)
                else: by_slot.setdefault(code, []).append(e)
            q, lv, ent, sq = {}, {}, {}, {'H': 0.0, 'C': 0.0}
            for code, lst in by_slot.items():
                geo = math.exp(sum(math.log(max(1, e['mass'])) for e in lst) / len(lst))
                for e in lst:
                    b = fam.get(e['guild'] if code in ('SN', 'SNP') else code, fam.get(code, 5))
                    if part == 'water' and code == 'PE' and ctx.get('deep'): b *= 3
                    scale = max(0.25, min(4, (max(1, e['mass']) / geo) ** -0.75))
                    L = LEVEL.get(code, 'H')
                    mult = R0['ap_freq'] if (e['ap'] and not e['civ']) else (R0['giant_freq'] if e['giant'] else 1)
                    q[e['key']], lv[e['key']], ent[e['key']] = b * scale * mult, L, e
                    sq[L] += b * scale * mult
            uH, uC = tgt.get('H', 73), tgt.get('C', 20)
            if sq['C'] == 0: uH, uC = 1, 0
            elif sq['H'] == 0: uH, uC = 0, 1
            else: s_ = uH + uC; uH, uC = uH / s_, uC / s_
            mH = sum(v / sq['H'] * ent[k]['mass'] for k, v in q.items() if lv[k] == 'H') if sq['H'] else 0
            mC = sum(v / sq['C'] * ent[k]['mass'] for k, v in q.items() if lv[k] == 'C') if sq['C'] else 0
            binding, guard = 'pyramid target', R0['biomass_guard']
            if guard > 0 and part in ('land', 'cavern') and uH > 0 and uC > 0 and mH > 0 and mC > 0 and uC * mC > guard * uH * mH:
                r = guard * mH / mC; uC = r / (1 + r); uH = 1 - uC; binding = 'biomass guard'
            w = {}
            for k, v in q.items():
                e, L = ent[k], lv[k]
                x = (uH if L == 'H' else uC) * v / sq[L]
                gm = max(1, (e['cmin'] + e['cmax']) / 2) if e['cmax'] >= 1 else max(1, e['group'])
                w[k] = x / gm if R0['units'] else x
            mx = max(w.values()) if w else 1
            lad = {k: max(1, int(100 * x / mx + 0.5)) for k, x in w.items()}
            apex_odds = {}
            for e in apex:
                raw = e['freq']
                t = EXT.get(e['token'])
                if t and t.get('freq') and e['extinct'] and raw == t['freq'][0]:
                    raw = min(t['freq'][1], R0['apex_raw_cap']) if R0['apex_raw_cap'] > 0 else t['freq'][1]
                cap = R0['apex_raw_cap']
                apex_odds[e['token']] = min(raw, cap) if cap > 0 and raw > cap else raw
            out[part] = {'target': pk, 'herb_share': round(uH, 3), 'carn_share': round(uC, 3), 'binding': binding,
                         'odds': {ent[k]['token']: v for k, v in sorted(lad.items(), key=lambda kv: -kv[1])}, 'apex_odds': apex_odds}
        return out
