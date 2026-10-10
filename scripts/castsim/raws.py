"""castsim.raws: DF 53.16's creature raws, compiled the way DF compiles them, as far as the seasonal-wildlife tool reads them.

DF reads data/vanilla/vanilla_creatures*/objects/creature_*.txt. A creature block is a token stream; a block that says
[COPY_TAGS_FROM:ROOT] starts from ROOT's compiled tokens, and [APPLY_CREATURE_VARIATION:V] applies the variation's
CV_REMOVE_TAG / CV_NEW_TAG / CV_ADD_TAG edits (c_variation_default.txt): a GIANT drops pet value and every vermin tag,
doubles its size and turns SAVAGE; an ANIMAL_PERSON drops pet value and the vermin tags and gains CAN_LEARN, CAN_SPEAK,
SAVAGE and GRAVITATE_BODY_SIZE:70000. Castes: tokens before any [CASTE] apply to every caste; [CASTE:X] / [SELECT_CASTE:X|ALL]
/ [SELECT_ADDITIONAL_CASTE:X] direct the rest. DF then derives a few flags the tool reads: GRAZER from STANDARD_GRAZER,
TRAINABLE_WAR and TRAINABLE_HUNTING from TRAINABLE, CANNOT_BREATHE_AIR and CAN_BREATHE_WATER from AQUATIC,
CAN_BREATHE_WATER from AMPHIBIOUS, and the BIOME_* set with DF's aggregate biome tokens expanded.

Approximations (named in the report): CV_CONVERT_TAG is not applied (it renames body/attack tokens the tool does not
read); the animal person's adult size is (root + 70,000) / 2, as the engine computes it (classify).
"""
from __future__ import annotations

import copy
import functools
import re
from pathlib import Path

DF = Path.home() / ('Library/Application Support/CrossOver/Bottles/Win10/drive_c/Program Files (x86)/Steam/steamapps/'
                    'common/Dwarf Fortress/data/vanilla')

# DF 53.16 biome_type names (df.biome_type)
LAND = ['MOUNTAIN', 'GLACIER', 'TUNDRA', 'SWAMP_TEMPERATE_FRESHWATER', 'SWAMP_TEMPERATE_SALTWATER', 'MARSH_TEMPERATE_FRESHWATER',
        'MARSH_TEMPERATE_SALTWATER', 'SWAMP_TROPICAL_FRESHWATER', 'SWAMP_TROPICAL_SALTWATER', 'SWAMP_MANGROVE',
        'MARSH_TROPICAL_FRESHWATER', 'MARSH_TROPICAL_SALTWATER', 'FOREST_TAIGA', 'FOREST_TEMPERATE_CONIFER',
        'FOREST_TEMPERATE_BROADLEAF', 'FOREST_TROPICAL_CONIFER', 'FOREST_TROPICAL_DRY_BROADLEAF', 'FOREST_TROPICAL_MOIST_BROADLEAF',
        'GRASSLAND_TEMPERATE', 'SAVANNA_TEMPERATE', 'SHRUBLAND_TEMPERATE', 'GRASSLAND_TROPICAL', 'SAVANNA_TROPICAL',
        'SHRUBLAND_TROPICAL', 'DESERT_BADLAND', 'DESERT_ROCK', 'DESERT_SAND']
OCEANS = ['OCEAN_TROPICAL', 'OCEAN_TEMPERATE', 'OCEAN_ARCTIC']
def _w(kind, zone): return [f'{kind}_{zone}_{s}' for s in ('FRESHWATER', 'BRACKISHWATER', 'SALTWATER')]
LAKES = _w('LAKE', 'TEMPERATE') + _w('LAKE', 'TROPICAL')
RIVERS = _w('RIVER', 'TEMPERATE') + _w('RIVER', 'TROPICAL')
POOLS = _w('POOL', 'TEMPERATE') + _w('POOL', 'TROPICAL')
SUBTER = ['SUBTERRANEAN_WATER', 'SUBTERRANEAN_CHASM', 'SUBTERRANEAN_LAVA']
WATER = OCEANS + LAKES + RIVERS + POOLS
ALL = LAND + WATER + SUBTER
FREEZING = {'GLACIER', 'TUNDRA', 'OCEAN_ARCTIC', 'MOUNTAIN', 'FOREST_TAIGA'}
TEMPERATE_LAND = [b for b in LAND if 'TEMPERATE' in b] + ['FOREST_TAIGA']
TROPICAL_LAND = [b for b in LAND if 'TROPICAL' in b or b == 'SWAMP_MANGROVE']
AGG = {
    'ALL_MAIN': LAND + WATER, 'ANY_LAND': LAND, 'ANY_OCEAN': OCEANS, 'ANY_LAKE': LAKES, 'ANY_RIVER': RIVERS, 'ANY_POOL': POOLS,
    'ANY_TEMPERATE_LAKE': _w('LAKE', 'TEMPERATE'), 'ANY_TROPICAL_LAKE': _w('LAKE', 'TROPICAL'),
    'ANY_TEMPERATE_RIVER': _w('RIVER', 'TEMPERATE'), 'ANY_TROPICAL_RIVER': _w('RIVER', 'TROPICAL'),
    'ANY_TEMPERATE_POOL': _w('POOL', 'TEMPERATE'), 'ANY_TROPICAL_POOL': _w('POOL', 'TROPICAL'),
    'NOT_FREEZING': [b for b in LAND + WATER if b not in FREEZING],
    'ANY_TEMPERATE': TEMPERATE_LAND + _w('LAKE', 'TEMPERATE') + _w('RIVER', 'TEMPERATE') + _w('POOL', 'TEMPERATE') + ['OCEAN_TEMPERATE'],
    'ANY_TROPICAL': TROPICAL_LAND + _w('LAKE', 'TROPICAL') + _w('RIVER', 'TROPICAL') + _w('POOL', 'TROPICAL') + ['OCEAN_TROPICAL'],
    'ANY_FOREST': [b for b in LAND if b.startswith('FOREST')], 'ANY_SHRUBLAND': [b for b in LAND if b.startswith('SHRUBLAND')],
    'ANY_GRASSLAND': [b for b in LAND if b.startswith('GRASSLAND')], 'ANY_SAVANNA': [b for b in LAND if b.startswith('SAVANNA')],
    'ANY_TEMPERATE_FOREST': ['FOREST_TEMPERATE_CONIFER', 'FOREST_TEMPERATE_BROADLEAF'],
    'ANY_TROPICAL_FOREST': ['FOREST_TROPICAL_CONIFER', 'FOREST_TROPICAL_DRY_BROADLEAF', 'FOREST_TROPICAL_MOIST_BROADLEAF'],
    'ANY_TEMPERATE_BROADLEAF': ['FOREST_TEMPERATE_BROADLEAF'],
    'ANY_TROPICAL_BROADLEAF': ['FOREST_TROPICAL_DRY_BROADLEAF', 'FOREST_TROPICAL_MOIST_BROADLEAF'],
    'ANY_WETLAND': [b for b in LAND if b.startswith(('SWAMP', 'MARSH'))],
    'ANY_TEMPERATE_WETLAND': [b for b in LAND if b.startswith(('SWAMP', 'MARSH')) and 'TEMPERATE' in b],
    'ANY_TROPICAL_WETLAND': [b for b in LAND if b.startswith(('SWAMP', 'MARSH')) and ('TROPICAL' in b or 'MANGROVE' in b)],
    'ANY_TEMPERATE_MARSH': ['MARSH_TEMPERATE_FRESHWATER', 'MARSH_TEMPERATE_SALTWATER'],
    'ANY_TROPICAL_MARSH': ['MARSH_TROPICAL_FRESHWATER', 'MARSH_TROPICAL_SALTWATER'],
    'ANY_TEMPERATE_SWAMP': ['SWAMP_TEMPERATE_FRESHWATER', 'SWAMP_TEMPERATE_SALTWATER'],
    'ANY_TROPICAL_SWAMP': ['SWAMP_TROPICAL_FRESHWATER', 'SWAMP_TROPICAL_SALTWATER', 'SWAMP_MANGROVE'],
    'ANY_DESERT': ['DESERT_BADLAND', 'DESERT_ROCK', 'DESERT_SAND'],
}
DERIVED = {'STANDARD_GRAZER': ['GRAZER'], 'TRAINABLE': ['TRAINABLE_WAR', 'TRAINABLE_HUNTING'],
           'AQUATIC': ['CANNOT_BREATHE_AIR', 'CAN_BREATHE_WATER'], 'AMPHIBIOUS': ['CAN_BREATHE_WATER']}
TOKEN = re.compile(r'\[([^\]]+)\]')


def _blocks(objdirs):
    out = {}
    for d in objdirs:
        for f in sorted(d.glob('creature_*.txt')):
            text = f.read_text(encoding='latin-1')
            for chunk in re.split(r'(?=\[CREATURE:)', text)[1:]:
                toks = [t.split(':') for t in TOKEN.findall(chunk)]
                out[toks[0][1]] = {'toks': toks[1:], 'file': f.name, 'extinct': 'extinct' in str(d)}
    return out


def _variations():
    text = (DF / 'vanilla_creatures/objects/c_variation_default.txt').read_text(encoding='latin-1')
    out = {}
    for chunk in re.split(r'(?=\[CREATURE_VARIATION:)', text)[1:]:
        toks = [t.split(':') for t in TOKEN.findall(chunk)]
        out[toks[0][1]] = toks[1:]
    return out


class Raws:
    def __init__(self):
        self.src = _blocks([DF / 'vanilla_creatures/objects', DF / 'vanilla_creatures_extinct/objects'])
        self.var = _variations()

    @functools.lru_cache(maxsize=None)
    def tokens(self, tok):
        """the compiled token list of a creature (COPY_TAGS_FROM and variations applied)"""
        b = self.src[tok]
        out, removes = [], []
        for t in b['toks']:
            if t[0] == 'COPY_TAGS_FROM':
                out = copy.deepcopy(self.tokens(t[1]))
            elif t[0] == 'APPLY_CREATURE_VARIATION':
                out = self._apply(out, self.var.get(t[1], []), removes); removes = []
            elif t[0] == 'CV_REMOVE_TAG':
                removes.append(t[1:])
            elif t[0] == 'APPLY_CURRENT_CREATURE_VARIATION':
                if removes: out = [x for x in out if not any(x[:len(r)] == r for r in removes)]; removes = []
            elif t[0] in ('GO_TO_END', 'GO_TO_START', 'GO_TO_TAG'):
                pass
            else:
                out.append(t)
        return out

    @staticmethod
    def _apply(base, var, extra_removes):
        removes = [v[1:] for v in var if v[0] == 'CV_REMOVE_TAG'] + extra_removes
        kept = [x for x in base if not any(x[:len(r)] == r for r in removes)]
        news = [v[1:] for v in var if v[0] in ('CV_NEW_TAG', 'CV_ADD_TAG')]
        return kept + news

    @functools.lru_cache(maxsize=None)
    def creature(self, tok):
        """the fields the tool reads: castes (flag sets, body size, pet value), creature flags and values"""
        toks = self.tokens(tok)
        castes, order, sel = {}, [], ['ALL']
        allc, cre = set(), set()
        biomes, gobble, cclass, btoks = set(), set(), set(), set()
        vals = {'FREQUENCY': 50, 'CLUSTER_NUMBER': None, 'UNDERGROUND_DEPTH': None, 'PETVALUE': {}, 'BODY_SIZE': {}, 'SIZE_PERC': 100,
                'FREQ_PERC': 100, 'GRAVITATE': None}
        def target():
            if sel == ['ALL']: return ['ALL']
            return sel
        for t in toks:
            k = t[0]
            if k == 'CASTE':
                castes.setdefault(t[1], set()); order.append(t[1]); sel = [t[1]]; continue
            if k == 'SELECT_CASTE':
                sel = ['ALL'] if t[1] == 'ALL' else [t[1]]; castes.setdefault(t[1], set()) if t[1] != 'ALL' else None; continue
            if k == 'SELECT_ADDITIONAL_CASTE':
                sel = (sel if sel != ['ALL'] else []) + [t[1]]; continue
            if k == 'BIOME':
                for b in AGG.get(t[1], [t[1]]): biomes.add(b)
                btoks.add(t[1])
            elif k == 'FREQUENCY': vals['FREQUENCY'] = int(t[1])
            elif k == 'CHANGE_FREQUENCY_PERC': vals['FREQ_PERC'] = int(t[1])
            elif k == 'CLUSTER_NUMBER': vals['CLUSTER_NUMBER'] = (int(t[1]), int(t[2]))
            elif k == 'UNDERGROUND_DEPTH': vals['UNDERGROUND_DEPTH'] = (int(t[1]), int(t[2]))
            elif k == 'GOBBLE_VERMIN_CLASS': gobble.add(t[1])
            elif k == 'CREATURE_CLASS': cclass.add(t[1])
            elif k == 'CHANGE_BODY_SIZE_PERC': vals['SIZE_PERC'] = int(t[1])
            elif k == 'GRAVITATE_BODY_SIZE': vals['GRAVITATE'] = int(t[1])
            for c in target():
                if k == 'PETVALUE': vals['PETVALUE'][c] = int(t[1])
                if k == 'BODY_SIZE' and len(t) >= 4: vals['BODY_SIZE'][c] = int(t[3])
            flags = [k] + DERIVED.get(k, [])
            cre.update(flags)
            for c in target():
                if c == 'ALL': allc.update(flags)
                else: castes.setdefault(c, set()).update(flags)
        if not castes: castes = {'DEFAULT': set()}
        cs = {c: (allc | f) for c, f in castes.items()}
        def anyc(fl): return any(fl in f for f in cs.values())
        def everyc(fl): return all(fl in f for f in cs.values())
        size = max([v for v in vals['BODY_SIZE'].values()] or [0])
        pet = max([v for v in vals['PETVALUE'].values()] or [0])
        return {'token': tok, 'castes': cs, 'flags': cre, 'any': anyc, 'every': everyc, 'biomes': biomes, 'gobble': gobble,
                'cclass': cclass, 'biome_tokens': btoks, 'freq': vals['FREQUENCY'] * vals['FREQ_PERC'] // 100, 'cluster': vals['CLUSTER_NUMBER'],
                'depth': vals['UNDERGROUND_DEPTH'], 'pet': pet, 'size_raw': size, 'size_perc': vals['SIZE_PERC'],
                'gravitate': vals['GRAVITATE'], 'extinct': self.src[tok]['extinct'], 'file': self.src[tok]['file'],
                'root': next((t[1] for t in self.src[tok]['toks'] if t[0] == 'COPY_TAGS_FROM'), None),
                'variations': [t[1] for t in self.src[tok]['toks'] if t[0] == 'APPLY_CREATURE_VARIATION']}

    def adult_size(self, tok):
        """adult body volume in cm3 as the engine reads it (adultSize: the largest caste's last BODY_SIZE x10 -- DF stores
        the raw's cm3 value / 10 -- with the size percentage DF applies)"""
        c = self.creature(tok)
        return c['size_raw'] * c['size_perc'] // 100
