"""castsim.rules: the New Rules tables, read from the one copy (sw-wt/plugin rules/new-rules.json; user 20 Oct, Q2).

The desk (design.py, engine.py) and the Food Web Explorer (foodweb_export.py -> creatures.json meta -> foodweb_sim.js) take
their rule tables from here; the engine's are generated from the same file (Phase B), and the plugin's tools/rules_check.py
holds the engine to it. Sets come back as Python sets, the vermin pairs of a diet as tuples, and every diet carries a vermin
list (empty when it has none), as the desk's tables always had. RULES_FILE=path reads another copy.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

RULES_FILE = Path(os.environ.get('RULES_FILE') or Path.home() / 'Claude/Projects/sw-wt/plugin/rules/new-rules.json')
DOC = json.loads(RULES_FILE.read_text())
RO, MO, VE = DOC['roster'], DOC['model'], DOC['vermin']
VERSION = DOC['version']

sets = lambda d: {k: set(v) for k, v in d.items()}   # noqa: E731

SLOTS = {k: {s: (lo, hi) for s, lo, hi in rows} for k, rows in RO['SLOTS'].items()}
SALT_WET = set(RO['SALT_WET'])
LINK_AS = dict(RO['LINK_AS'])
FORCED_PREY = dict(RO['FORCED_PREY'])
FLIER_ONLY_PREY = set(RO['FLIER_ONLY_PREY'])
FLIER_ONLY_TYPES = set(RO['FLIER_ONLY_TYPES'])
FORCED_DIET = {t: dict(d, vermin=[tuple(x) for x in d.get('vermin', [])]) for t, d in RO['FORCED_DIET'].items()}
REAL_APEX = {t: tuple(v) for t, v in RO['REAL_APEX'].items()}
EVIL_APEX = dict(RO['EVIL_APEX'])
EVIL_APEX_BIOMES = sets(RO['EVIL_APEX_BIOMES'])
WETLAND_GROUND = set(RO['WETLAND_GROUND'])
EXTRA_BIOMES = sets(RO['EXTRA_BIOMES'])
EVIL_EXTRA_BIOMES = sets(RO['EVIL_EXTRA_BIOMES'])
BIOME_LIMIT = sets(RO['BIOME_LIMIT'])
GIANT_BUGS = set(RO['GIANT_BUGS'])
WATER_BUG_APEX = set(RO['WATER_BUG_APEX'])
VERMIN_FRESH = set(RO['VERMIN_FRESH'])
VERMIN_GROUND = set(RO['VERMIN_GROUND'])
OFF_LAYERS = sets(RO.get('OFF_LAYERS', {}))
BONUS_PREDATOR = set(RO.get('BONUS_PREDATOR', []))
HUNTED_BY = dict(RO.get('HUNTED_BY', {}))
FLY_NOT_RAPTOR = set(RO['FLY_NOT_RAPTOR'])
PLACED_PLANTS = set(RO['PLACED_PLANTS'])
FILTER_FEEDERS = set(RO['FILTER_FEEDERS'])
APEX_PACK = RO['APEX_PACK']
WEIRD = dict(RO['WEIRD'])
CAVE_ASSIGN = {t: list(v) for t, v in RO['CAVE_ASSIGN'].items()}

ROLE = dict(MO['ROLE'])
ROLE_NOTE = dict(MO['ROLE_NOTE'])
HABITAT_OVERRIDE = dict(MO['HABITAT_OVERRIDE'])
GUILD_OVERRIDE = dict(MO['GUILD_OVERRIDE'])
HAB_CLASS = dict(MO['HAB_CLASS'])
HAB_EATS = sets(MO['HAB_EATS'])
NEVER_PREY = set(MO['NEVER_PREY'])

SWV_OVERRIDE = dict(VE['SWV_OVERRIDE'])
FRESH_EATERS = set(VE['FRESH_EATERS'])
GIANT_FLY_SKIP = set(VE['GIANT_FLY_SKIP'])
GOBBLE_RULES = VE['GOBBLE_RULES']
VCLASS = VE['VCLASS']
GOBBLE_EDGES = VE['GOBBLE_EDGES']


def meta():
    """the tables the explorer's simulator reads (creatures.json meta, beside the desk's own)"""
    return {
        'rules_version': VERSION, 'off_layers': {k: sorted(v) for k, v in OFF_LAYERS.items()},
        'bonus_predator': sorted(BONUS_PREDATOR), 'hunted_by': HUNTED_BY,
        'fresh_eaters': sorted(FRESH_EATERS), 'giant_fly_skip': sorted(GIANT_FLY_SKIP), 'gobble_rules': GOBBLE_RULES,
        'vclass': VCLASS, 'gobble_edges': GOBBLE_EDGES, 'hab_class': HAB_CLASS, 'hab_eats': {k: sorted(v) for k, v in HAB_EATS.items()},
    }
