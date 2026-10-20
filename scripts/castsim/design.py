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

from engine import Engine, REACH, R0, CAST_DEF, ROLE, HABITAT_OVERRIDE, GUILD_OVERRIDE

SAVAGE_AT, EVIL_AT, GOOD_AT = 66, 66, 32          # DF: savagery 66+ = savage; evil 66+ = evil, 0-32 = good
SALT_WET = {'MARSH_TEMPERATE_SALTWATER', 'MARSH_TROPICAL_SALTWATER', 'SWAMP_TEMPERATE_SALTWATER', 'SWAMP_TROPICAL_SALTWATER',
            'SWAMP_MANGROVE'}
POOL_CAP = 20000                                   # "small" for the murky-pool mini roster, cm3 (engine V7.WB.POOL_MAX_MASS)
SUBTER = ('SUBTERRANEAN_WATER', 'SUBTERRANEAN_CHASM')
EXTINCT_RULE = {
    'NONE': 'absent from the world',
    'ISOLATED': 'only in isolated regions: world regions of 5 tiles or less, savage or not (measured on region16, 13 Oct)',
    'UNTAMED_WILDS': 'only in savage regions',
    'WILDERNESS': 'in any wild region',
    'DOMESTICATED': 'in any wild region (and kept by civilisations)',
}

LAYERS = ['ground', 'flying', 'ocean', 'fresh', 'cavern1', 'cavern2', 'cavern3']
LAYER_NAME = {'ground': 'land-ground', 'flying': 'land-flying', 'ocean': 'ocean (saltwater)', 'fresh': 'freshwater',
              'cavern1': 'cavern 1', 'cavern2': 'cavern 2', 'cavern3': 'cavern 3'}
# slot -> (min, max) per cast; the count is drawn per cast inside the range
SLOTS = {
    'ground': {'apex': (1, 1), 'meso': (2, 2), 'grazer': (2, 2), 'ground prey': (2, 2), 'sentient': (1, 1), '_vermin': (3, 3)},
    'flying': {'apex': (1, 1), 'flier': (2, 2), 'sentient': (1, 1), '_vermin': (2, 3)},
    'ocean': {'apex': (1, 1), 'meso': (1, 2), 'fish': (3, 3), 'pelagic': (1, 1), 'shore': (1, 2), 'waterbird': (1, 2), 'sentient': (1, 1), '_vermin': (2, 3)},
    'fresh:lake': {'apex': (1, 1), 'meso': (1, 2), 'fish': (3, 3), 'shore': (1, 2), 'waterbird': (1, 2), 'sentient': (1, 1), '_vermin': (2, 3)},
    'fresh:river': {'meso': (1, 1), 'fish': (2, 2), 'shore': (1, 1), 'waterbird': (1, 1), 'sentient': (1, 1), '_vermin': (2, 2)},
    'fresh:pool': {'meso': (1, 1), 'fish': (2, 2), 'sentient': (1, 1), '_vermin': (2, 2)},
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


# Real-life apex predators that DF does not tag LARGE_PREDATOR (several not even CARNIVORE, so the tool reads them as
# prey). 'apex': joins the apex draw like a flagged predator. 'local': apex only where no true apex is in season on the
# layer (the top predator of a small or depleted community). Proposed 10 Oct; the user's call.
# user 17 Oct: a species read as another for every feeding link and the slots that steer them (engine ROSTER.FP.LINK_AS)
LINK_AS = {'GIGANTIC SQUID': 'GIANT_OCTOPUS', 'GIANT_LEOPARD_SEAL': 'LEOPARD_SEAL'}
# user 17 Oct: every apex of the layer takes this species (engine ROSTER.FP.FORCED_PREY)
FORCED_PREY = {'LEOPARD_SEAL': 'ocean'}
# user 19 Oct: on the surface only a land-flying predator or apex eats the bat (engine ROSTER.FP.FLIER_ONLY_PREY)
FLIER_ONLY_PREY = {'BAT'}
# user 19 Oct: the osprey and eagle eat every ocean and freshwater fish prey and ground snake, never an apex (engine
# MODEL.forcedDiet). The desk has no body plan, so it models the fish only: no cast holds them with a ground snake.
_FISH_LAND_VERMIN = [('OCEAN', 'SWV_SMALL_FISH'), ('FRESH', 'SWV_SMALL_FISH'), ('GROUND', 'SWV_SMALL_MAMMAL'), ('GROUND', 'SWV_HERP')]
FORCED_DIET = {   # user 19 Oct, and the great horned owl: land mammal and herp vermin, and the hare
    'BIRD_OSPREY': {'fish': True, 'noPelagic': True, 'snake': True, 'vermin': _FISH_LAND_VERMIN},   # 20 Oct: no pelagic fish
    'BIRD_EAGLE': {'fish': True, 'noPelagic': True, 'snake': True, 'vermin': _FISH_LAND_VERMIN},
    'BIRD_OWL_GREAT_HORNED': {'prey': ['HARE'], 'vermin': [('GROUND', 'SWV_SMALL_MAMMAL'), ('GROUND', 'SWV_HERP')]},
    # user 19 Oct: the peregrine takes ground snakes and never the raven, duck or rabbit
    'BIRD_FALCON_PEREGRINE': {'snake': True, 'never': ['BIRD_RAVEN', 'BIRD_DUCK', 'RABBIT'], 'vermin': []},
    # user 19 Oct: the grizzly and black bear take every ocean vermin and freshwater small fish; the polar bear every
    # non-vermin on the ocean layer (no cast holds a bear with ocean creatures, so the desk's casts do not change)
    'BEAR_GRIZZLY': {'vermin': [('OCEAN',), ('FRESH', 'SWV_SMALL_FISH')]},
    'BEAR_BLACK': {'vermin': [('OCEAN',), ('FRESH', 'SWV_SMALL_FISH')]},
    'BEAR_POLAR': {'ocean': True, 'vermin': []},
    # user 19 Oct: the alligator takes nothing that flies, no insect vermin, and every swimming (ocean or freshwater) vermin.
    # The desk's ladder has no vermin types; the alligator's ladder vermin are small fish only, so only noFliers matters here.
    'ALLIGATOR': {'noFliers': True, 'noTypes': ['SWV_FLYING_INSECT', 'SWV_GROUND_BUG', 'SWV_COLONY'], 'swimVermin': True,
                  'vermin': [('OCEAN',), ('FRESH',)]},
    # user 20 Oct (engine ROSTER.FP.FORCED_DIET)
    'CROCODILE_CAVE': {'prey': ['RUTHERER', 'DRALTHA'], 'vermin': []},
    'BLIND_CAVE_BEAR': {'prey': ['RUTHERER', 'DRALTHA'], 'vermin': []},
    'BAT_GIANT': {'prey': ['RUTHERER', 'DRALTHA'], 'vermin': []},
    'HIPPO': {'fish': True, 'vermin': [('OCEAN', 'SWV_SMALL_FISH'), ('FRESH', 'SWV_SMALL_FISH')]},
    'GIANT_HIPPO': {'fish': True, 'vermin': [('OCEAN', 'SWV_SMALL_FISH'), ('FRESH', 'SWV_SMALL_FISH')]},
    'BEAVER': {'fish': True, 'vermin': [('OCEAN', 'SWV_SMALL_FISH'), ('FRESH', 'SWV_SMALL_FISH')]},
    'GIANT_ALLIGATOR': {'prey': ['GIANT_HIPPO'], 'vermin': []},
    'HARPY': {'sentients': ['ground', 'flying'], 'overApex': True, 'vermin': []},
    'GRIMELING': {'sentients': ['ocean', 'fresh'], 'overApex': True, 'vermin': []},
    'CRETACEOUS_UTAHRAPTOR': {'bigPrey': 1000000, 'vermin': []},
    # user 20 Oct (later): the pterosaurs take every flying vermin and the freshwater flying insects
    'CRETACEOUS_SINOPTERUS': {'vermin': [('FLYING',), ('FRESH', 'SWV_FLYING_INSECT')]},
    'JURASSIC_RHAMPHORHYNCHUS': {'vermin': [('FLYING',), ('FRESH', 'SWV_FLYING_INSECT')]},
    'CRETACEOUS_QUETZALCOATLUS': {'vermin': [('FLYING',), ('FRESH', 'SWV_FLYING_INSECT')]},
}
# user 20 Oct: the extinct apexes eat any non-apex sentient by habitat class (engine MODEL.habEats)
HAB_CLASS = {'land': 'ground', 'flier': 'flier', 'waterbird': 'flier', 'semiaquatic': 'shore', 'aquatic': 'water'}
HAB_EATS = {'ground': {'ground'}, 'flier': {'ground', 'flier'}, 'shore': {'ground', 'water'}, 'water': {'shore', 'water'}}
REAL_APEX = {
    'PYTHON': ('ground', 'apex', 'large constrictors take deer and pigs; Burmese pythons are the apex of the Everglades today'),
    'MONITOR_LIZARD': ('ground', 'apex', 'the Komodo dragon is the apex predator of its islands'),
    'LYNX': ('ground', 'local', 'the Eurasian lynx tops forests that have no wolves or bears'),
    'COYOTE': ('ground', 'local', 'the apex where wolves are gone; hunts in packs'),
    'WOLVERINE': ('ground', 'local', 'tops tundra and taiga communities; drives wolves off kills'),
    'BIRD_FALCON_PEREGRINE': ('flying', 'apex', 'the apex aerial hunter of other birds (under the 2,000 cm3 raptor floor)'),
    # user 17 Oct: "take away apex from leopard seal" (every ocean apex takes it: FORCED_PREY) and give the giant leopard seal apex
    'GIANT_LEOPARD_SEAL': ('ocean', 'apex', 'user 17 Oct: apex/meso/shore, with the leopard seal\'s links (LINK_AS)'),
    'FISH_GROUPER_GIANT': ('ocean', 'local', 'top reef predator where sharks are few (DF: read as fish prey)'),
    'FISH_BARRACUDA_GREAT': ('ocean', 'local', 'a reef top predator (DF: read as fish prey)'),
    'FISH_PIKE': ('fresh', 'apex', 'the top predator of northern lakes and rivers (DF: read as fish prey)'),
    'FISH_GAR_LONGNOSE': ('fresh', 'local', 'top predator of warm rivers without crocodilians (DF: read as fish prey)'),
    'ALLIGATOR SNAPPING TURTLE': ('fresh', 'local', 'the ambush apex of southern rivers'),
    # user 13 Oct: two more freshwater apexes
    'FISH_TIGERFISH': ('fresh', 'apex', 'the goliath tigerfish tops African rivers and lakes'),
    'ANACONDA': ('fresh', 'apex', 'the apex of Amazon rivers and lakes (reaches tropical lakes and rivers through EXTRA_BIOMES)'),
}
# Real-life hunters DF does not tag CARNIVORE (or BONECARN), so the tool reads them as prey (user 12 Oct: apply). Upper-level
# predators only: mid-level fish (cod, carp, bluefish, skate) stay in the fish slot, penguins stay shore birds. In the
# engine this is MODEL.ROLE = 'predator' entries.
REAL_CARNIVORE = {
    'FISH_PIKE': 'freshwater ambush predator of fish, frogs, ducklings', 'FISH_GAR_LONGNOSE': 'freshwater fish hunter',
    'FISH_TIGERFISH': 'pack-hunting freshwater predator', 'FISH_BARRACUDA_GREAT': 'reef predator of fish',
    'FISH_GROUPER_GIANT': 'reef predator: fish, rays, small sharks, turtles', 'FISH_CONGER_EEL': 'nocturnal fish and octopus hunter',
    'FISH_MARLIN': 'pelagic hunter of tuna and squid', 'FISH_SWORDFISH': 'pelagic hunter of fish and squid',
    'FISH_TUNA_BLUEFIN': 'pelagic hunter of fish and squid', 'FISH_HALIBUT': 'large benthic fish hunter',
    'FISH_COELACANTH': 'deep-water fish hunter', 'FISH_OPAH': 'hunter of squid and small fish',
    'SHARK_ANGEL': 'ambush shark', 'SHARK_NURSE': 'benthic shark: fish, crustaceans, squid', 'SHARK_REEF_WHITETIP': 'reef shark',
    'SHARK_SPINY_DOGFISH': 'pack-hunting small shark', 'SHARK_WOBBEGONG_SPOTTED': 'ambush shark',
    'LEOPARD_SEAL': 'hunts penguins and other seals', 'ELEPHANT_SEAL': 'hunts squid and fish', 'HARP_SEAL': 'hunts fish and crustaceans',
    'WALRUS': 'eats clams; takes seals at times', 'MINK': 'semiaquatic hunter of fish, frogs, rodents', 'WEASEL': 'hunter of rodents and birds',
    # user 13 Oct: giant bugs eat whatever they can catch (the raws give these no CARNIVORE)
    'GIANT_MANTIS': 'ambush hunter', 'GIANT_DRAGONFLY': 'the top aerial insect predator', 'GIANT_TICK': 'blood-feeder, carries disease',
    'GIANT_MOSQUITO': 'blood-feeder, carries disease', 'GIANT_ROACH': 'eats anything it can catch',
}
REUSE = 0.01          # x per cast the species is already on this year (user 12 Oct; was CAST_DEF reuse 0.1)
# sponges are placed like plants on the bed (user 30 Sep, 12 Oct): they pass the wild and natural filters and the biome
# gates, enter the water layers they live in, and take no cast slot; the sponge man is a natural filter-feeder creature
PLACED_PLANTS = {'SPONGE', 'GIANT_SPONGE'}
# Evil apexes for the layers an evil region had none on (user 12 Oct): the harpy (EVIL, LARGE_PREDATOR raptor; kept out of
# the flying apex only by its sentience) on land-flying, the grimeling (EVIL, LARGE_PREDATOR semiaquatic hunter of marshes
# and swamps; DF tags it NO_EAT+NO_DRINK, so it is let through the natural filter like the sponge man) on freshwater.
# Wired into every land biome / freshwater body of an evil region.
EVIL_APEX = {'HARPY': 'flying', 'GRIMELING': 'fresh', 'NIGHTWING': 'flying'}
# user 13 Oct: the nightwing (EVIL, LARGE_PREDATOR desert flier; DF tags it NO_EAT+NO_DRINK and sentient) is the evil desert
# flier, wired only into an evil region's deserts (the harpy covers its grass, savanna, shrub and marsh)
EVIL_APEX_BIOMES = {'NIGHTWING': {'DESERT_BADLAND', 'DESERT_ROCK', 'DESERT_SAND'}}
def _bx(*names):
    """biome names, ANY_* groups expanded"""
    from raws import AGG
    return {b for n in names for b in AGG.get(n, [n])}


# Tool-side biome additions (user 13 Oct): the species is treated as living in these biomes as well as its raws' own. Apex
# predators stuck in tropical-only subtypes (DF rarely makes tropical land) moved into the realistic ecotypes beside them,
# MOUNTAIN given its first true apex, and the temperate wetlands kept an apex once the dingo is narrowed. The gates
# (savage, alignment, extinct) still apply per biome. In the engine: ROSTER.EXTRA_BIOMES, read by buildPool.
EXTRA_BIOMES = {
    'LION': _bx('GRASSLAND_TEMPERATE', 'SAVANNA_TEMPERATE', 'SHRUBLAND_TEMPERATE', 'DESERT_BADLAND', 'DESERT_SAND'),
    'TIGER': _bx('GRASSLAND_TROPICAL', 'SAVANNA_TROPICAL', 'FOREST_TAIGA', 'ANY_TEMPERATE_FOREST', 'GRASSLAND_TEMPERATE'),
    'HYENA': _bx('ANY_DESERT', 'SAVANNA_TEMPERATE'),
    'CHEETAH': _bx('DESERT_SAND', 'DESERT_ROCK', 'SAVANNA_TEMPERATE'),
    'PYTHON': _bx('ANY_TROPICAL_SWAMP', 'ANY_TROPICAL_MARSH', 'FOREST_TROPICAL_DRY_BROADLEAF', 'GRASSLAND_TROPICAL', 'SAVANNA_TROPICAL'),
    'MONITOR_LIZARD': _bx('ANY_DESERT', 'SWAMP_MANGROVE', 'MARSH_TROPICAL_FRESHWATER'),
    'COUGAR': _bx('MOUNTAIN', 'DESERT_BADLAND', 'DESERT_ROCK', 'GRASSLAND_TEMPERATE', 'SWAMP_TEMPERATE_FRESHWATER'),
    'LEOPARD': _bx('MOUNTAIN'),
    'JAGUAR': _bx('ANY_TEMPERATE_WETLAND'),
    'BEAR_BLACK': _bx('ANY_TEMPERATE_WETLAND'),
    'WOLF': _bx('ANY_TEMPERATE_WETLAND'),
    'ANACONDA': _bx('LAKE_TROPICAL_FRESHWATER', 'RIVER_TROPICAL_FRESHWATER'),
    # user 20 Oct: the grimeling to any marsh, any swamp, any lake or any river (its raws name every marsh and swamp already)
    'GRIMELING': _bx('ANY_LAKE', 'ANY_RIVER'),
    # user 17 Oct: the giant dragonfly and giant mosquito hunt over lakes and rivers; the mosquito is freshwater vermin
    'GIANT_DRAGONFLY': _bx('LAKE_TEMPERATE_FRESHWATER', 'LAKE_TROPICAL_FRESHWATER', 'RIVER_TEMPERATE_FRESHWATER', 'RIVER_TROPICAL_FRESHWATER'), 'GIANT_MOSQUITO': _bx('LAKE_TEMPERATE_FRESHWATER', 'LAKE_TROPICAL_FRESHWATER', 'RIVER_TEMPERATE_FRESHWATER', 'RIVER_TROPICAL_FRESHWATER'), 'MOSQUITO': _bx('LAKE_TEMPERATE_FRESHWATER', 'LAKE_TROPICAL_FRESHWATER', 'RIVER_TEMPERATE_FRESHWATER', 'RIVER_TROPICAL_FRESHWATER'),
}
# ... and on evil biomes only: the evil roster widened beyond its narrow raw ranges (user 13 Oct)
EVIL_EXTRA_BIOMES = {
    'BEAK_DOG': _bx('ANY_WETLAND'),
    'STRANGLER': _bx('ANY_TROPICAL_FOREST', 'ANY_TEMPERATE_FOREST'),
    'BLENDEC_FOUL': _bx('ANY_FOREST'),
    'OGRE': _bx('MOUNTAIN', 'ANY_DESERT'),
}
# the dingo's raws say NOT_FREEZING (23 of 27 land biomes), so it took half the ground apex draws: kept to arid, open and dry
# country (user 13 Oct)
BIOME_LIMIT = {
    'DINGO': _bx('ANY_DESERT', 'ANY_GRASSLAND', 'ANY_SAVANNA', 'ANY_SHRUBLAND', 'FOREST_TROPICAL_DRY_BROADLEAF', 'FOREST_TEMPERATE_BROADLEAF'),
}
# Giant bug apexes (user 13 Oct): the giant bug-likes that hunt (the three giant arachnids, and five the raws left without
# CARNIVORE, made predators in REAL_CARNIVORE) live in ANY savage or evil land biome of the fort, a calm evil one included
# (past their giant SAVAGE tag), and are true apexes there; a flier is eligible on land-ground as well as land-flying.
GIANT_BUGS = {'GIANT_JUMPING_SPIDER', 'GIANT_BARK_SCORPION', 'GIANT_BROWN_RECLUSE_SPIDER', 'GIANT_MANTIS', 'GIANT_DRAGONFLY',
              'GIANT_TICK', 'GIANT_MOSQUITO', 'GIANT_ROACH'}
# user 17 Oct ("Changing Vermin the Tool Feeds"; engine ROSTER.FP.HABITAT / WATER_BUG_APEX / VERMIN_FRESH): the giant mantis and
# giant roach are fliers, not waterbirds; no giant bug flier is on land-ground; the giant dragonfly and giant mosquito are
# freshwater apexes and waterbirds (lake: apex + waterbird; river: waterbird); the mosquito is freshwater vermin only
HABITAT = {'GIANT_MANTIS': 'flier', 'GIANT_ROACH': 'flier',
           # user 20 Oct: the gila monster is a desert land animal (its raws' AMPHIBIOUS read semiaquatic); the giant follows
           'GILA_MONSTER': 'land', 'GIANT_GILA_MONSTER': 'land'}
# user 20 Oct: white stork and kea land-bird prey; puffin, loon and albatross waterbird prey (engine MODEL.ROLE 'prey' and
# MODEL.GUILD_OVERRIDE; the four were REAL_CARNIVORE from 12 Oct, the kea's BONECARN reads raptor)
PREY_BIRDS = {'BIRD_STORK_WHITE': 'LB', 'BIRD_KEA': 'LB', 'BIRD_PUFFIN': 'WB', 'BIRD_LOON': 'WB', 'BIRD_ALBATROSS': 'WB'}
# seabirds and the stork are never flying apexes (engine ROSTER.FLY_NOT_RAPTOR)
FLY_NOT_RAPTOR = {'BIRD_ALBATROSS', 'BIRD_LOON', 'BIRD_PUFFIN', 'BIRD_STORK_WHITE'}
WATER_BUG_APEX = {'GIANT_DRAGONFLY', 'GIANT_MOSQUITO'}
VERMIN_FRESH = {'MOSQUITO'}
VERMIN_GROUND = {'ROACH_LARGE'}
VERMIN_INSECT = {'FAIRY'}   # user 19 Oct: the fairy is a flying insect (engine VERMIN.SWV_OVERRIDE; cast class VI)   # user 17 Oct: the large roach is ground vermin (engine ROSTER.FP.VERMIN_GROUND; class VG)
APEX_PACK = 1.5       # the apex draw's pack bonus (user 13 Oct; was the cast-wide x3): group size already counts the pack
APEX_FLOOR = 0.0      # no size floor: the square-root weight already favours the large (a 10% floor cut lions beside ogres)
# filter feeders DF marks NO_EAT+NO_DRINK: kept natural (user 10 Oct); an immobile sponge is placed like a plant on the
# bed (user 30 Sep) and takes no cast slot
FILTER_FEEDERS = {'SPONGE_MAN'}


def weird_weight(k, s):
    """the cavern pick multiplier for weirdness s in cavern k (1 favours the plain, 2 the middle, 3 the strange)"""
    if k == 1: return (1 - s) ** 2 + 0.05
    if k == 2: return max(0.05, 1 - abs(s - 0.5) * 1.8)
    return s ** 2 + 0.05


JUDGEMENT = [
    ('land-ground slots', 'not specified: kept the v7.4 land cast without its raptor, bird and sentient slots (apex 1, meso 2, grazer 2, ground prey 2, vermin 3).'),
    ('ranges', '"1-2" and "2-3": each cast draws its count inside the range, so cast sizes vary from season to season.'),
    ('apex rule', 'rebuilt 10 Oct: the apex is a weighted draw among the eligible predators in season, not the largest. Eligible: LARGE_PREDATOR species, giants of any predator, animal people whose root is eligible, the curated water apexes, raptors of 2,000 cm3 and up, and the real-life apexes DF does not flag (table on the page). Weight: the square root of group size (adult size x the pack\'s mean size) against the largest, x1.5 for pack hunters (13 Oct; x3 before: the pack was counted twice, in group size and again as the bonus), x0.01 per cast the species is already on this year, x0.2 giants, x0.1 animal people. No size floor (a 10% floor cut lions and hyenas beside a pair of ogres, and the great white beside an orca pod). The rest can still take meso. Water layers: only the curated water apexes (and their giants and animal people) are eligible, as in the engine; DF\'s other LARGE_PREDATOR water species (sea lamprey, frill shark, blacktip) take meso.'),
    ('hand-wiring', 'the audit\'s automatic proposal is approved and applied (12 Oct): per biome and region type, promoted residents and wired apexes are true apexes; a wired species is treated as living in the biome. Evil regions also get the harpy on land-flying and the grimeling on freshwater (the grimeling let through the natural filter as a hand-wired apex).'),
    ('local apexes', 'a "local" real-life apex (lynx, coyote, wolverine, gar, grouper...) holds the apex only when no true apex is in season; with none of either, the largest non-sentient predator is promoted (the old fallback, still your open question).'),
    ('sponges', 'the sponge and the giant sponge are placed like plants on the bed (30 Sep, 12 Oct): they pass the filters, enter the water layers they live in, and take no cast slot; the sponge man passes as a natural filter-feeder creature and can be cast.'),
    ('CARNIVORE fix', 'real-life hunters DF does not tag CARNIVORE are read as predators (table on the page): upper-level fish and small sharks, seals, walrus, mink, weasel, fish-eating seabirds and the white stork. Mid-level fish (cod, carp, bluefish, skate) and penguins are left as they were.'),
    ('reuse', 'x0.01^N at cast inclusion, N = the number of casts already built that hold the species (any layer, any season). The 28 casts are built at once at embark (or first enable, or a redraw) in a random order, seeded by site and year, so no season gets the first pick of the species eligible all year (a Spring-first order gave Spring the unpenalised pick; measured on the page).'),
    ('biome additions', 'tool-side (13 Oct): apex predators DF keeps in tropical subtypes, which worldgen rarely makes, also live in the realistic ecotypes beside them (lion, tiger, hyena, cheetah, python, monitor lizard, cougar; leopard to mountains, jaguar, black bear and wolf to temperate wetlands; table on the page). The dingo is kept to arid, open and dry country. On evil regions the evil roster is widened (beak dog to every wetland, strangler and blendec foul to forests, ogre to mountains and deserts) and the nightwing is the evil desert flier. The gates still apply per biome.'),
    ('giant bug apexes', 'giant bugs eat what they can catch (13 Oct): the mantis, dragonfly, tick, mosquito and roach are read as predators, and they and the three giant arachnids are true apexes in any savage or evil land biome, a calm evil one included; the fliers can take the land-ground apex as well as land-flying. The x0.2 giant weight still applies.'),
    ('new water apexes', 'the tigerfish (tropical lakes and rivers) and the anaconda (wired into tropical lakes and rivers) are freshwater apexes (13 Oct).'),
    ('river-only apex', 'no apex slot (your list has none); flagged predators there can take the meso slot.'),
    ('fill fallback', 'a slot with room and no candidate linked to the cast is filled anyway from its eligible species ("no link"), so no slot stays empty while candidates exist; the food web is computed after the draw on every layer, as you asked for land-flying.'),
    ('amphibians', 'an amphibious (water-breathing, not aquatic) creature never enters land-ground; if its BIOME names a fort land biome it can enter the freshwater layer (its shore slot), and on a saltwater marsh, swamp or mangrove the ocean layer.'),
    ('shore and fliers', 'a shore creature or a waterbird eats an aquatic creature no larger than itself (or 20,000 cm3), and aquatic vermin.'),
    ('murky pools', 'plan B (user 13 Oct: a murky pool is a subset of lake and river, keeping small creatures and vermin): aquatic or amphibious species of adult size up to 20,000 cm3 whose raws reach lake, river or pool water, plus vermin; a small lake or river species fits a pool body in the engine\'s draw too. DF\'s pool fish and amphibians are vermin (lungfish, pond turtle, toad), so the pool\'s fish slot draws fish-class and amphibious vermin too (a species drawn as fish is not also drawn as vermin). The engine also admits small lake/river species DF stocked in water near the fort; this desk sim builds from raws only, so it shows the raws path.'),
    ('cavern sentients', 'a sentient cavern species (troll, blind cave ogre, gorlak, animal people, troglodyte) fills only the sentient slot.'),
    ('weirdness', 'a first-cut 0-1 score per cavern species (table in the step-through); cavern 1 picks weight (1-w)^2, cavern 2 the middle, cavern 3 w^2. DF\'s own raw depth range still decides which caverns a species can live in.'),
    ('region biomes', 'a real fort\'s biomes are the 3x3 world tiles around it (DF draws a block\'s wildlife from all nine region neighbours); each biome takes the savagery and evil of the nearest tile that has it.'),
    ('alignment', 'GOOD species only where the biome is good (evil 0-32), EVIL only where evil (66+); cavern species are exempt (v7: alignment only limits taming).'),
    ('cavern savagery', 'caverns ignore surface savagery: DF stocks savage cave species (giant cave spider) on calm forts.'),
    ('extinct rule', 'DF\'s raws tag every real-world-extinct species SAVAGE; the world\'s REAL_WORLD_EXTINCT setting is read in place of that tag (UNTAMED_WILDS: savage regions only; ISOLATED: small world regions of 5 tiles or less, savage or not, as DF stocks them on region16; WILDERNESS and DOMESTICATED: any wild region). Extinct animal people stay savage-only, as all animal people.'),
    ('extinct setting', 'region19\'s REAL_WORLD_EXTINCT cannot be read without DF (world.raws.param_real_world_extinct); the real forts assume UNTAMED_WILDS, the install\'s default preset value.'),
    ('wild', 'a creature is wild when it has a BIOME and either LARGE_ROAMING or a vermin tag, colony insects (VERMIN_SOIL_COLONY: ants, bees, termites) included (DF\'s own test for region populations).'),
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


def raw_bodies(biomes):
    """the water body types a creature's raws reach (the engine's MODEL.waters): ocean, cavern, lake, river, pool"""
    out = set()
    for b in biomes:
        if b.startswith('OCEAN'): out.add('ocean')
        elif b == 'SUBTERRANEAN_WATER': out.add('cavern')
        else:
            parts = b.split('_')
            if len(parts) == 3 and parts[0] in ('LAKE', 'RIVER', 'POOL') and parts[2] in ('FRESHWATER', 'BRACKISHWATER', 'SALTWATER'):
                out.add(parts[0].lower())
    return out


def fresh_raw(biomes):
    """v7.5 plan B (engine ROSTER.FP.freshRaw, 13 Oct): the raws reach fresh water -- a lake, river or pool -- or name no water
    body at all (read as any water, the engine's V7.WB.typesFor)"""
    w = raw_bodies(biomes)
    return not w or bool(w & {'lake', 'river', 'pool'})


class Design:
    def __init__(self, raws=None, wiring=None, order='random'):
        """wiring: {(savagery, alignment, layer, biome): [(token, 'promote'|'wire'), ...]} -- the approved apex hand-wiring"""
        self.wiring = wiring or {}
        self.order = order        # 'random' (user 12 Oct) or 'season' (Spring first, for the bias comparison)
        self.ground_fly = {}      # token -> {hunter, ground, flying} on the current embark (apex_bar)
        self.apex_any = {}        # token -> the layers it is an apex of on the current embark (never prey)
        self.cur_pool = {}        # the current embark's pool (LINK_AS models)
        self.promoted = set()     # (layer, token): true apexes by hand-wiring on the current embark
        for tok in REAL_CARNIVORE: ROLE.setdefault(tok, 'predator')   # the CARNIVORE classifier fix (before any classify)
        for tok, g in PREY_BIRDS.items(): ROLE[tok] = 'prey'; GUILD_OVERRIDE[tok] = g
        HABITAT_OVERRIDE.update(HABITAT)
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
    def region_type(fb):
        return ('savage' if fb['sav'] >= SAVAGE_AT else 'wild',
                'evil' if fb['evil'] >= EVIL_AT else ('good' if fb['evil'] <= GOOD_AT else 'neutral'))

    def wires_for(self, fbs):
        """the hand-wiring that applies on this embark: [(layer, token, kind, biome)]"""
        out = []
        for b, fb in fbs.items():
            if fb['kind'] == 'cavern': continue
            sav, al = self.region_type(fb)
            layers = ['ground', 'flying'] if fb['kind'] == 'land' else (['ocean'] if fb['kind'] == 'ocean' else ['fresh'])
            for L in layers:
                for t, kind in self.wiring.get((sav, al, L, b), ()): out.append((L, t, kind, b))
                if al == 'evil':
                    for t, el in EVIL_APEX.items():
                        if el == L and b in EVIL_APEX_BIOMES.get(t, (b,)): out.append((L, t, 'wire', b))
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
        if info['token'] in GIANT_BUGS and (fb['kind'] == 'land' or (info['token'] in WATER_BUG_APEX and fb['kind'] in ('lake', 'river'))) \
                and (fb['sav'] >= SAVAGE_AT or fb['evil'] >= EVIL_AT):
            return None   # a giant bug apex lives in any savage or evil land biome (user 13 Oct)
        # a real-world-extinct species (not its animal person) follows the world's REAL_WORLD_EXTINCT rule in place of
        # its raw SAVAGE tag: DF's raws tag them all SAVAGE, the worldgen setting says savage-only or any wild region
        if info['extinct'] and not info['ap']:
            rule = spec.get('extinct', 'UNTAMED_WILDS')
            if rule == 'NONE': return 'extinct: absent from this world'
            if rule == 'UNTAMED_WILDS' and fb['sav'] < SAVAGE_AT: return 'extinct (UNTAMED_WILDS): biome not savage'
            # 13 Oct: DF stocks them in small world regions (5 tiles or less), savage or not; this was 'never' before
            if rule == 'ISOLATED' and not fb.get('iso'): return 'extinct (ISOLATED): no small (isolated) region for this biome'
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
            if tok in HABITAT: info = dict(info, habitat=HABITAT[tok])
            if tok in PLACED_PLANTS:
                info = dict(info, eco='natural', ecoWhy=['placed like a plant on the bed (user 30 Sep, 12 Oct)'], locked=False, plant=True)
            if 'VERMIN_SOIL_COLONY' in f and not info['gameVermin']:   # colony insects: DF stocks them as ColonyInsect populations
                info = dict(info, gameVermin=True, category='vermin', guild='V')
            if not ('LARGE_ROAMING' in f or info['gameVermin'] or info.get('plant')): continue
            funnel['wild'] += 1
            if (tok in FILTER_FEEDERS and info['eco'] == 'unliving' and info['ecoWhy'] == ['NO_EAT+NO_DRINK']):
                info = dict(info, eco='natural', ecoWhy=['filter feeder (kept, user 10 Oct)'], locked=False)
            if info['eco'] != 'natural' or info['mega'] or info['night']: continue
            funnel['natural (not locked)'] += 1
            hit = sorted(b for b in self.biomes_of(tok, c, fbs) if b in fbs)
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
            added = sorted(set(ok) - set(c['biomes']))
            if added: e['extra'] = added      # biomes the tool-side tables gave it (not its raws')
            pool[tok] = e
        # the approved hand-wiring: a wired species is treated as living in the biome; wired and promoted species are true
        # apexes of the layer on this embark
        self.promoted = set()
        for L, t, kind, b in self.wires_for(fbs):
            self.promoted.add((L, t))
            if kind != 'wire': continue
            if t in pool:
                if b not in pool[t]['matched']: pool[t]['matched'] = sorted(set(pool[t]['matched']) | {b}); pool[t].setdefault('wired', []).append(b)
                continue
            info = self.E.classify(t)
            if info['eco'] != 'natural':
                info = dict(info, eco='natural', ecoWhy=['hand-wired apex (user 12 Oct)'], locked=False)
            e = dict(info); e.update(key=t, matched=[b], weird=WEIRD.get(t), wired=[b])
            pool[t] = e
        return pool, funnel, rejected

    def biomes_of(self, tok, c, fbs):
        """the biomes a species lives in: its raws' (narrowed by BIOME_LIMIT), the tool-side additions, the evil-only additions
        on an evil biome, and for a giant bug apex every savage or evil land biome of the fort (user 13 Oct)"""
        bs = set(c['biomes'])
        if tok in BIOME_LIMIT: bs &= BIOME_LIMIT[tok]
        bs |= EXTRA_BIOMES.get(tok, set())
        for b in EVIL_EXTRA_BIOMES.get(tok, ()):
            if b in fbs and fbs[b]['evil'] >= EVIL_AT: bs.add(b)
        if tok in GIANT_BUGS:
            bs |= {b for b, fb in fbs.items() if fb['kind'] == 'land' and (fb['sav'] >= SAVAGE_AT or fb['evil'] >= EVIL_AT)}
        return bs

    # ------------------------------------------------------------------ step 2: the seven layers
    def layers_of(self, e, spec, fbs):
        """the layers a pool species belongs to, and the notes on layers it was kept out of"""
        m = set(e['matched'])
        land = [b for b in m if fbs[b]['kind'] == 'land']
        hab, verm = e['habitat'], e['gameVermin']
        out, notes = [], []
        vc = ('VG' if e['token'] in VERMIN_GROUND else 'VI' if e['token'] in VERMIN_INSECT else self.E.vclass(e)) if verm else None
        if land and not (verm and e['token'] in VERMIN_FRESH):
            if verm:
                if vc in ('VB', 'VI'): out.append('flying')
                elif vc != 'VF': out.append('ground')
            elif hab == 'land': out.append('ground')
            elif hab in ('flier', 'waterbird'):
                out.append('flying')   # user 17 Oct: no giant bug flier on land-ground (was: hunts on the ground too, 13 Oct)
            elif hab == 'semiaquatic': notes.append(('ground', 'amphibious: never on land-ground'))
        # a water layer takes aquatic and amphibious species on any biome match; land animals, fliers and insects only
        # where their raws name the water body itself (ALL_MAIN or ANY_TROPICAL would put rats and beetles in every pool)
        wet = hab in ('aquatic', 'semiaquatic')
        named = explicit_water(self.R.creature(e['token'])['biome_tokens'], {b for b in m if fbs[b]['kind'] not in ('land', 'cavern')})
        named |= EXTRA_BIOMES.get(e['token'], set()) & {b for b in m if fbs[b]['kind'] not in ('land', 'cavern')}   # a tool-side addition is named on purpose (engine FP.layersOf: EXTRA_BIOMES, raws or not)
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
                # v7.5 plan B (13 Oct): a murky pool takes only a species whose raws reach lake, river or pool water
                elif sub == 'pool' and not verm and not fresh_raw(self.R.creature(e['token'])['biomes']):
                    notes.append(('fresh', 'no lake, river or pool in its raws (murky-pool roster)'))
                else: out.append('fresh')
        if m & set(SUBTER):
            lo, hi = e['depthLo'], e['depthHi']
            for k in spec.get('caverns') or ():
                if (not lo or not hi) or lo <= k <= hi: out.append(f'cavern{k}')
                else: notes.append((f'cavern{k}', f'raw depth {lo}-{hi}'))
        return out, notes

    # ------------------------------------------------------------------ slot eligibility
    def apex_tier(self, e, layer):
        """'apex', 'local' or None: can this species hold the apex slot on this layer?"""
        if e['civ'] or e['gameVermin']: return None
        if (layer, e['token']) in self.promoted: return 'apex'
        if e['token'] in GIANT_BUGS and layer in ('ground', 'flying'): return 'apex'
        if e['token'] in WATER_BUG_APEX and layer == 'fresh': return 'apex'
        if self.flagged(e, layer): return 'apex'
        for tok in (e['token'], e.get('root')):
            r = REAL_APEX.get(tok)
            if r and r[0] == layer: return r[1]
        if e['giant']:   # a giant of a real-life apex
            r = REAL_APEX.get(e['token'][6:])
            if r and r[0] == layer: return 'apex'
        return None

    def flagged(self, e, layer):
        if e['civ'] or e['gameVermin']: return False
        if layer == 'flying':
            if e['ap'] and e['largePred'] and e['habitat'] in ('flier', 'waterbird'): return True   # an animal person of a flagged flier
            if e['token'] in REAL_CARNIVORE or e['token'] in FLY_NOT_RAPTOR: return False   # seabirds and the stork are not raptors
            return self.E.fly_apex(dict(e, layer='land'))
        if layer in ('ocean', 'fresh'):
            # as the engine (slotOf): only the curated water apexes hold a water apex slot -- a giant or an animal person
            # of one too; DF's other LARGE_PREDATOR water species (sea lamprey, frill shark, blacktip) take meso (R49)
            for tok in (e['token'], e.get('root'), e['token'][6:] if e['giant'] else None):
                if tok and R0['aquatic_apex'].get(tok) in ('apex', 'pelagic'): return True
            return False
        return e['guild'] in ('AL', 'AW') or self.E.boosted(e)

    @staticmethod
    def predator(e):
        return e['guild'] in ('ML', 'MW', 'RP', 'AL', 'AW') or e['role'] == 'predator'

    def link(self, e):
        """the entry a link test reads e as (LINK_AS, when the model is in this embark's pool), else e"""
        m = LINK_AS.get(e['token'])
        return self.cur_pool.get(m, e) if m else e

    def slots_for(self, e, layer, sub):
        """the cast slots a (non-vermin) candidate can fill on this layer"""
        le = self.link(e)
        hab, pred, g = le['habitat'], self.predator(le), le['guild']
        if layer.startswith('cavern'):
            if e['sentient']: return ['sentient']
            s = []
            if self.apex_tier(e, layer): s.append('apex')
            if pred: s.append('meso')
            if hab == 'land' and not pred: s.append('ground prey')
            if hab in ('flier', 'waterbird'): s.append('flier')
            if hab in ('aquatic', 'semiaquatic'): s.append('swimmer')
            return s
        # user 17 Oct: a sentient fills the surface layers' sentient slot only (engine FP.slotsFor); a curated evil apex keeps its seat
        if e['sentient']:
            if EVIL_APEX.get(e['token']) == layer and self.apex_tier(e, layer): return ['apex', 'sentient']
            return ['sentient']
        if layer == 'ground':
            s = []
            if self.apex_tier(e, layer): s.append('apex')
            if pred: s.append('meso')
            elif g == 'GZ': s.append('grazer')
            else: s.append('ground prey')
            return s
        if layer == 'flying':
            return (['apex'] if self.apex_tier(e, layer) else []) + ['flier']
        # water layers
        s = []
        flyer = hab in ('flier', 'waterbird')
        if flyer:
            if layer == 'fresh' and sub == 'pool': return []
            if e['token'] in WATER_BUG_APEX and layer == 'fresh' and sub != 'river' and self.apex_tier(e, layer): return ['apex', 'waterbird']
            return ['waterbird']
        wet = hab in ('aquatic', 'semiaquatic')
        if sub == 'pool':
            if pred: s.append('meso')
            elif wet: s.append('fish')
            return s
        if e.get('plant'): return ['placed plant']   # sponges: placed on the bed, no cast slot
        if self.apex_tier(e, layer) and not (layer == 'fresh' and sub == 'river'): s.append('apex')
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
        if eb['token'] in FLIER_ONLY_PREY:   # user 19 Oct: the bat, on the surface, to flying predators and apexes only
            g = self.ground_fly.get(ea['token'])
            if g and not g['flyHunter']: return False
        if not b['vermin'] and self.forced_diet(ea, eb): return True   # the user's own diets (engine MODEL.forcedDiet)
        if b['vermin'] and eb['gameVermin']:   # user 20 Oct: no flying-only vermin for a non-flier
            ls = eb.get('layers', ())
            if 'flying' in ls and not any(L in ls for L in ('ground', 'ocean', 'fresh')):
                g = self.ground_fly.get(ea['token'], {})
                if not (g.get('flier') or ea['habitat'] in ('flier', 'waterbird') or 'flying' in ea.get('layers', ())): return False
        if self.apex_bar(ea, eb): return False   # user 17 Oct: the link bars on the real species
        if FORCED_PREY.get(eb['token']) in self.apex_any.get(ea['token'], ()): return True   # the leopard seal to every ocean apex
        ea, eb = self.link(ea), self.link(eb)    # LINK_AS
        if ea['guild'] == 'GZ': return False   # user 17 Oct: no grazer eats anything
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
    @staticmethod
    def used_key(token, slot):
        """user 17 Oct: a sentient seat is exempt from the repeat penalty of the species' other seats (engine FP.usedKey)"""
        return 'SN|' + token if slot == 'sentient' else token

    def weight(self, c, used, layer, pack=None, apex_draw=False):
        e, w = c['e'], 1.0
        if self.predator(e) and not e['benign'] and e['cmax'] > 1: w *= CAST_DEF['pack'] if pack is None else pack
        # only once drawn: `used` counts casts already built this year; a sentient's sentient seats apart (user 17 Oct)
        w *= REUSE ** used.get(self.used_key(e['token'], 'sentient' if e['sentient'] and not apex_draw else None), 0)
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

    def cast(self, lst, layer, sub, season, used, rng, drawn=None):
        key = self.slot_key(layer, sub)
        table = SLOTS[key]
        want = {s: rng.randint(lo, hi) for s, (lo, hi) in table.items() if s != '_vermin'}
        vwant = rng.randint(*table['_vermin'])
        cands = [c for c in lst if not c['vermin'] and 'placed plant' not in c['slots']]
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
        # apex (rebuilt 10 Oct): a weighted draw among the eligible in season -- true apexes first, local ones only when
        # there is none; group size (adult size x the pack's mean size) sets a floor and a square-root weight
        tr['apex_rank'], tr['apex_rule'] = [], None
        if 'apex' in want:
            elig = [c for c in cands if 'apex' in c['slots']]
            tier = 'apex' if any(c['tier'] == 'apex' for c in elig) else ('local' if elig else None)
            elig = [c for c in elig if c['tier'] == tier]
            if elig:
                def gsize(c):
                    e = c['e']
                    pack = self.predator(e) and not e['benign'] and e['cmax'] > 1
                    return e['mass'] * ((e['cmin'] + e['cmax']) / 2 if pack else 1)
                mx = max(gsize(c) for c in elig)
                rows = []
                for c in sorted(elig, key=lambda c: (-gsize(c), c['e']['token'])):
                    g = gsize(c)
                    ok = g >= APEX_FLOOR * mx
                    w = (g / mx) ** 0.5 * self.weight(c, used, layer, pack=APEX_PACK, apex_draw=True) if ok else 0.0
                    rows.append((c, g, w, ok))
                tot = sum(w for _, _, w, _ in rows)
                r, chosen = rng.random() * tot, None
                for c, g, w, ok in rows:
                    if not ok: continue
                    r -= w
                    if r <= 0: chosen = c; break
                chosen = chosen or next(c for c, _, _, ok in rows if ok)
                tr['apex_rank'] = [(c['e']['token'], c['e']['mass'], round(g), round(w / tot, 3) if tot else 0, c['tier'],
                                    'apex' if c is chosen else ('below the size floor' if not ok else 'eligible: can take meso'))
                                   for c, g, w, ok in rows]
                tr['apex_rule'] = ('weighted draw among the true apexes in season' if tier == 'apex'
                                   else 'weighted draw among the local apexes (no true apex in season)')
                put(chosen, 'apex', f'apex: drawn ({tier}, chance {round(dict((x["e"]["token"], w) for x, _, w, _ in rows)[chosen["e"]["token"]] / tot * 100)}%)')
            else:
                pr = sorted([c for c in cands if 'meso' in c['slots'] and not c['e']['sentient']], key=lambda c: (-c['e']['mass'], c['e']['token']))
                if pr:
                    put(pr[0], 'apex', 'apex: largest predator (none eligible)'); tr['apex_rule'] = 'largest predator promoted (no eligible apex in season)'
                    tr['apex_rank'] = [(c['e']['token'], c['e']['mass'], c['e']['mass'], 0, 'none', 'apex' if i == 0 else 'promotion order') for i, c in enumerate(pr[:6])]
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
        for m in members:
            if drawn is not None: drawn.add(m['e']['token'])
            else: k = self.used_key(m['e']['token'], m['slot']); used[k] = used.get(k, 0) + 1
        ws = [m['e']['weird'] for m in members if m['e'].get('weird') is not None]
        tr.update(members=[(m['e']['token'], m['slot']) for m in members],
                  placed=[c['e']['token'] for c in lst if 'placed plant' in c['slots']],
                  vermin=[(v['e']['token'], v['vclass'], eaten[v['e']['token']]) for v in vsel],
                  vermin_eligible=len(verm), unfilled=unfilled, edges=edges,
                  isolated=sorted(m['e']['token'] for m in members if m['e']['token'] not in linked_set),
                  weird=round(sum(ws) / len(ws), 2) if ws else None)
        return tr

    # ------------------------------------------------------------------ the whole embark
    def forced_diet(self, ea, eb):
        """the user's own diets (engine MODEL.forcedDiet): sentients past the apex rule (harpy, grimeling), then never an apex:
        the extinct apexes' sentients by habitat class, named prey, ground prey of a ton or more, fish prey (no pelagic for
        the eagle and osprey), the polar bear's ocean creatures"""
        d, t = FORCED_DIET.get(ea['token']), eb['token']
        ls = eb.get('layers', ())
        sent = eb['sentient'] and not eb['civ'] and not eb['gameVermin']
        if d and d.get('sentients') and sent and any(L in ls for L in d['sentients']): return True
        if t in self.apex_any: return False
        if sent and ea['extinct'] and ea['token'] in self.apex_any:
            if HAB_CLASS.get(eb['habitat'], 'ground') in HAB_EATS.get(HAB_CLASS.get(self.link(ea)['habitat'], 'ground'), ()): return True
        if not d: return False
        if t in d.get('prey', ()): return True
        if d.get('bigPrey') and 'ground' in ls and eb['mass'] >= d['bigPrey'] and not eb['gameVermin'] and not self.predator(self.link(eb)): return True
        g = self.ground_fly.get(t, {})
        if d.get('fish') and g.get('fish') and not (d.get('noPelagic') and self.link(eb)['guild'] == 'PE'): return True
        return bool(d.get('ocean') and not eb['gameVermin'] and 'ocean' in ls)

    def apex_bar(self, ea, eb):
        """user 17 Oct, the link bars (engine MODEL.apexBar): no apex is prey; no land-ground apex or predator takes anything on
        land-flying (a flying hunter on the ground is kept); no ocean or freshwater apex or predator links either way with a
        land-ground or land-flying creature unless either can take a shore seat."""
        if eb['token'] in self.apex_any: return True
        if eb['token'] in FORCED_DIET.get(ea['token'], {}).get('never', ()): return True   # user 19 Oct: a bird's 'never' list
        if FORCED_DIET.get(ea['token'], {}).get('noFliers') and ((not eb['gameVermin'] and eb['habitat'] == 'flier') or (eb['gameVermin'] and 'flying' in eb.get('layers', ()))):
            return True   # user 19 Oct: the alligator takes nothing that flies (20 Oct: waterbirds yes)
        a, b = self.ground_fly.get(ea['token']), self.ground_fly.get(eb['token'])
        if not a or not b: return False
        if a['hunter'] and b['flying'] and not (a['flying'] and b['ground']): return True
        gfb = (b['ground'] or b['flying']) and not (b['verm'] and b['wet'])   # a vermin also in water is water vermin here
        if ((a['water'] and gfb) or (b['water'] and (a['ground'] or a['flying']))) and not (a['shore'] or b['shore']): return True
        if a['oshore'] and b['ground']: return True    # user 19 Oct: no ocean-shore predator takes a land-ground creature
        if b['oshore'] and a['gapex']: return True     # ... and no land-ground apex takes it
        return False

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
        # the bars' table, as the engine's VERMIN.apexMark: ground hunters, water hunters, shore seats, layers
        self.cur_pool = pool
        self.ground_fly = {}
        for tok, e in pool.items():
            ls = e['layers']
            if not any(L in ls for L in ('ground', 'flying', 'ocean', 'fresh')): continue
            v, le = e['gameVermin'], self.link(e)
            wet = [L for L in ('ocean', 'fresh') if L in ls]
            self.ground_fly[tok] = {
                'hunter': (not v) and 'ground' in ls and bool(self.apex_tier(e, 'ground') or self.predator(le)),
                'water': (not v) and bool(wet) and bool(any(self.apex_tier(e, L) for L in wet) or self.predator(le)),
                'shore': (not v) and any('shore' in self.slots_for(e, L, sub) for L in wet),
                'ground': 'ground' in ls, 'flying': 'flying' in ls, 'verm': v, 'wet': bool(wet),
                # user 19 Oct: an ocean-shore predator; a land-ground apex
                'oshore': (not v) and 'ocean' in ls and 'shore' in self.slots_for(e, 'ocean', sub) and bool(self.predator(le) or self.apex_tier(e, 'ocean')),
                'gapex': (not v) and 'ground' in ls and bool(self.apex_tier(e, 'ground')),
                'fish': (not v) and bool(wet) and le['habitat'] == 'aquatic' and not self.predator(le),
                'flyHunter': (not v) and 'flying' in ls and bool(self.apex_tier(e, 'flying') or self.predator(le)),
                'flier': (not v) and (le['habitat'] in ('flier', 'waterbird') or 'flying' in ls)}
        self.apex_any = {}
        for tok, e in pool.items():
            if e['gameVermin']: continue
            ls = {L for L in e['layers'] if self.apex_tier(e, L)}
            if ls: self.apex_any[tok] = ls
        active = [L for L in LAYERS if layer_sets[L] and (L != 'ocean' or spec['water'].get('ocean'))
                  and (L != 'fresh' or sub) and (not L.startswith('cavern') or int(L[-1]) in (spec.get('caverns') or ()))]
        # all 28 casts at once, in a random order (seeded by site and year; user 12 Oct): a fixed Spring-first order handed
        # the early seasons the first, unpenalised pick of every species eligible all year. The x0.01 repeat weight counts
        # the casts already built that hold the species (any layer, any season).
        lists = {}
        for s in range(4):
            for L in active:
                lst = []
                for tok in sorted(layer_sets[L]):
                    e = pool[tok]
                    if e['noSeason'][s]: continue
                    if e['gameVermin']:
                        vc = 'VG' if tok in VERMIN_GROUND else 'VI' if tok in VERMIN_INSECT else self.E.vclass(e)
                        lst.append({'e': e, 'vermin': True, 'vclass': vc, 'slots': ['vermin']})
                        # murky pools: DF's pool fish and amphibians are vermin, so the fish slot draws them too
                        if L == 'fresh' and sub == 'pool' and (vc == 'VF' or e['habitat'] == 'semiaquatic'):
                            lst.append({'e': e, 'vermin': False, 'slots': ['fish'], 'vermin_fish': True, 'tier': None})
                    else:
                        sl = self.slots_for(e, L, sub)
                        if sl: lst.append({'e': e, 'vermin': False, 'slots': sl, 'tier': self.apex_tier(e, L) if 'apex' in sl else None})
                lists[(L, s)] = lst
        order = [(L, s) for s in range(4) for L in active]
        if self.order == 'random':
            random.Random((site * 7919 + year * 104729 + 7) % 2147483647).shuffle(order)
        casts, used = {}, {}
        for n, (L, s) in enumerate(order):
            seed = (site * 7919 + year * 104729 + s * 131 + LAYERS.index(L) * 17) % 2147483647
            casts[(L, s)] = self.cast(lists[(L, s)], L, sub, s, used, random.Random(seed))
            casts[(L, s)]['built'] = n + 1
        return {'pool': pool, 'funnel': funnel, 'rejected': rejected, 'notes': notes, 'layers': layer_sets, 'active': active,
                'sub': sub, 'lists': lists, 'casts': casts, 'fbs': fbs}
