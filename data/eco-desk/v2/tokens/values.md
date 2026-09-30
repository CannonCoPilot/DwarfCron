# Token values in DF 53.16 vanilla creature raws

Source: `token_census.py` → `values.tsv` (every number below is in that file) and `values-by-creature.tsv` (one row per creature, for audit).

## How to read this

**Populations**
- **all** = the 967 creatures defined in `vanilla_creatures/objects` + `vanilla_creatures_extinct/objects`.
- **wild** = the 363 species that pass census.py `is_wild`: they have a BIOME, they are vanilla (not extinct), they are not a giant or animal person, and they are not a civ race, megabeast, demon or night creature.

**How values are taken.** Values come after resolution (COPY_TAGS_FROM, APPLY_CREATURE_VARIATION, the caste walk), using census.py's resolver unchanged.
- For creature-level range tokens (FREQUENCY, POPULATION_NUMBER, CLUSTER_NUMBER, UNDERGROUND_DEPTH, TRIGGERABLE_GROUP), the last occurrence wins.
- For caste tokens, the value is taken per caste. No creature has a caste-varying value for any valued token: `n_caste_varying` = 0 on every row.
- For multi-valued tokens (BIOME, GAIT, SPECIFIC_FOOD, GOBBLE_*), each distinct value counts once per creature.

**Groupings in values.tsv**
- **behaviour**: LARGE_PREDATOR / BENIGN / neither. No creature carries both, in either population.
- **flier**: FLIER or not.
- **vermin**: any VERMIN_GROUNDER/ROTTER/SOIL/SOIL_COLONY/FISH/EATER, or none.
- **guild** (wild only).
- **kind** (animal person / giant / vanilla / extinct).

**Guild** is the primary Q6 guild (`../../Q6-setgroups.md`), reimplemented. It is exclusive, with precedence G15 cavern > G14 vermin > water guilds > land guilds. Because of that, guild sizes are smaller than Q6's overlapping counts. "Water BIOME" means any BIOME token that contains OCEAN, LAKE, RIVER or POOL.

**Defaults** are taken only from `../../wiki-tokens.md`, as cited there:

| token | default |
|---|---|
| FREQUENCY | 50 |
| CLUSTER_NUMBER | 1:1 |
| POPULATION_NUMBER | 1:1 |
| ODOR_LEVEL | 50 |
| GRASSTRAMPLE | 5 |
| VIEWRANGE | 20 |
| VISION_ARC | 60:120 |

`median_with_default` / `mean_with_default` fill in that default for the creatures that lack the token. wiki-tokens.md gives no default for PRONE_TO_RAGE, PETVALUE, SMELL_TRIGGER (it only says that 10000 means "cannot smell"), LOW_LIGHT_VISION, UNDERGROUND_DEPTH, TRIGGERABLE_GROUP or BEACH_FREQUENCY, so none is assumed for them.

## Summary per token (wild = 363; all = 967)

### FREQUENCY
- **Who sets it:** 174 wild set it explicitly. The other 189 get the default of 50.
- **Explicit values (wild):** 100 (84 species), 5 (36), 10 (22), 1 (10), 30 (6), 20 (6), 50 (4), 2 (2), 25 (3), 40 (1).
- **LARGE_PREDATOR (wild):** 39 of 60 are explicit. Median 5, mean 12.3. Values: 16 at 5 and 10 at 1. FREQUENCY:1 = SHARK_FRILL, BLOOD_MAN, the 6 ELEMENTMAN_*, YETI and SASQUATCH. Only 1 LP is at 100.
- **BENIGN (wild):** 48 of 163 are explicit (28 at 100, 13 at 5, 6 at 10). The other 115 take the default of 50.
- **neither:** 87 of 140 are explicit, 55 of them at 100.
- **FLIER:** 36 of 60 are explicit, and 34 of those are 100.
- **Vermin:** 74 of 114 are explicit, and 70 of those are 100.
- **Guilds:**
  - G1 land apex: all 21 explicit, median 5.
  - G7 land prey: 18 of 38 explicit, all at 5 or 10.
  - G6 grazers: 2 of 29 explicit. The rest are at the default of 50.
- **Reading:** an explicit low FREQUENCY marks predators and big prey. An explicit 100 marks vermin and birds.

### POPULATION_NUMBER
- **Who sets it:** every wild species (363 of 363), and 937 of 967 overall.
- **Common values (wild):** 15:30 (134), 250:500 (113), 10:20 (31), 20:50 (21).
- **Vermin:** 105 of 114 are 250:500, and 5 are 2500:5000.
- **LARGE_PREDATOR:** median min:max is 10:20. Range 1:1 to 100:200.
- **BENIGN:** median 15:30.
- **Guilds:**
  - G1 land apex: 2:3 (7), 10:20 (7), 5:10 (6).
  - G6 grazers: 27 of 29 are 15:30.

### CLUSTER_NUMBER
- **Who sets it:** 198 of 363 wild. The rest take the default of 1:1.
- **Common values (wild):** 1:1 (64), 5:10 (36), 3:7 (22), 1:4 (11), 1:3 (10), 100:200 (9 vermin swarms).
- **By guild (explicit only):**

| guild | explicit | typical value |
|---|---|---|
| G1 land apex | 21/21 | 13 at 1:1; 3:7 ×3, 1:3 ×3 |
| G3 mesocarnivore | 21/22 | 18 at 1:1 |
| G6 grazer | 29/29 | 3:7 ×12, 1:4 ×6, 1:1 ×6, 5:10 ×4 |
| G7 land prey | 35/38 | 1:1 ×13, 5:10 ×8, 2:2 ×8 |
| G8 shore | 15/19 | 5:10 ×6 |
| G4 raptor | 3/10 | 5:10 |
| G12 waterbird | 6/6 | 1:4 … 5:10 |
| G15 cavern | 27/55 | median 2:5 |
| G14 vermin | 19/105 | 9 at 100:200 (the fliers/swarms) |
| G2 water apex | 3/15 | 1:1 or 1:3 |
| G9 pelagic | 3/8 | (small numbers) |
| G10 coastal fish | 5/20 | (small numbers) |

- **LARGE_PREDATOR:** 34 of 60 wild are explicit. Median 1:2; the largest is 5:15.
- **BENIGN:** median 2.5:7 (median of the mins : median of the maxes).

### BEACH_FREQUENCY
- **Carriers:** 7 creatures overall, all at 10: ORCA, SPERM_WHALE, JELLYFISH_SEA_NETTLE, plus the ORCA and SPERM_WHALE man/giant versions.
- **Wild:** 3.
- **No default is documented.**

### PETVALUE
- **Who sets it:** 288 of 363 wild.
- **Common values (wild):** 10 (57), 50 (49), 500 (35), 200 (31).
- **By behaviour:**

| group | median | range |
|---|---|---|
| LARGE_PREDATOR | 500 | 50–10000 |
| BENIGN | 50 | — |
| neither | 30 | — |
| vermin | 10 | — |

- **By guild:**

| guild | PETVALUE |
|---|---|
| G9 pelagic | median 625 |
| G2 water apex | median 500 |
| G4 raptor | 25 |
| G12 waterbird | 10 |

- **Reading:** PETVALUE tracks size and danger. It has no default.

### PRONE_TO_RAGE
- **Carriers (wild):** exactly 4, all G3 mesocarnivores:

| species | value | behaviour flag |
|---|---|---|
| BADGER | 1 | BENIGN |
| WOLVERINE | 10 | BENIGN |
| HONEY BADGER | 10 | neither |
| BLACK_MAMBA | 1 | neither |

- **All creatures:** 12 = those 4 plus their man and giant versions, with the same values.
- **LARGE_PREDATOR:** none carries it.
- **Values:** only 1 and 10 occur.

### ODOR_LEVEL
- **Carriers:** 14 overall, 12 wild.
- **LARGE_PREDATOR:** 10 of the 12 wild carriers are LARGE_PREDATOR, and 10 of the 12 are G15 cavern: the cavern "men" (ELEMENTMAN_*, BLOOD_MAN, BLIZZARD_MAN), GRIMELING, IMP_FIRE and SNAKE_FIRE.
- **Values:**
  - 0 (6 carriers): the stone, metal and gem elementals, BLIZZARD_MAN and PLUMP_HELMET_MAN.
  - 50 (3 carriers).
  - 90 (2 carriers): IMP_FIRE and ELEMENTMAN_MUD.
  - 5 (1 carrier): GRIMELING.
- **Everyone else** has the default of 50.

### SMELL_TRIGGER
- **Wild:** 9 species carry it, all at 10000 ("cannot smell"). All 9 are G15 cavern and also carry ODOR_LEVEL.
- **Other values:** they occur only on civ races: DWARF 90, HUMAN 90, GOBLIN 50, KOBOLD 25, ELF 10, GREMLIN 10.
- **No default is documented.**

### VIEWRANGE
- **Present on 0 creatures.** No file anywhere under `data/` contains it.
- **Default:** 20 (wiki-tokens.md) applies to every creature.

### VISION_ARC
- **Carriers:** 125 overall, 42 wild.
- **Value:** only one value occurs anywhere: **50:310**. That is a narrow binocular arc and a wide total arc, the opposite of the 60:120 default.
- **Who has it (wild):**
  - 25 of the 32 STANDARD_GRAZER species.
  - 8 G7 land prey.
  - 7 vermin.
  - 2 waterbirds.
- **By behaviour:** 37 BENIGN and 5 neither. **No LARGE_PREDATOR** carries it, and only 2 FLIERs do.
- **Everyone else:** the default of 60:120.

### GRASSTRAMPLE
- **Carriers:** 106 wild, 279 overall.
- **Value 0 (93 of 106 wild):** every BENIGN carrier is 0, as is every G6/G7 carrier.
- **Nonzero (13 wild):**
  - 20: ALLIGATOR, CROCODILE_SALTWATER, IGUANA, MONITOR_LIZARD, TROLL, OGRE, and cavern animals.
  - 50: CAVE_DRAGON.
  - 10: SPIDER_CAVE_GIANT.
- **LARGE_PREDATOR:** 31 wild carry it (20 at 0, 11 nonzero).
- **Everyone else:** the default of 5. So, by the raws, the 257 wild species without the token trample *more* than the BENIGN species that declare 0.

### GRAZER
- **Present on 0 creatures, in no file.** The raws use STANDARD_GRAZER instead (107 overall, 32 wild).
- **STANDARD_GRAZER never takes a value.**

### LOW_LIGHT_VISION
- **Carriers:** 42 overall, 28 wild.
- **Value:** every one is 10000, except GOBLIN at 100.
- **Where (wild):** 27 of the 28 are G15 cavern.

### UNDERGROUND_DEPTH
- **Carriers:** 67 overall, 56 wild. The 55 G15 species all carry it, plus 1 vermin.
- **Values (wild):** 1:2 (21), 2:3 (14), 3:3 (11), then a tail up to 3:5.
- **LARGE_PREDATOR sits deeper:** median min 2, median max 3. BENIGN: median 1:2.

### TRIGGERABLE_GROUP
- **Carriers:** 5 creatures, all vermin:
  - 5:50: RAT, RAT_DEMON, ROACH_LARGE, WAMBLER_FLUFFY.
  - 50:100: BAT.

### GAIT
- **Carriers:** 959 of 967 creatures, 360 of 363 wild. Almost all of these come from the STANDARD_*_GAITS variations (the CV_NEW_TAG:GAIT lines in c_variation_default.txt), not from GAIT written in a creature.
- **Gait types (wild):** SWIM 311, WALK 282, CRAWL 282, CLIMB 132, FLY 60.
- **FLY gait and FLIER (wild):** the FLY gait matches FLIER one-to-one, 60 = 60.
- **FLY gait and FLIER (all):** 8 animal people keep FLIER but have no FLY gait: CARBONIFEROUS_MEGANEURA_MAN, CRETACEOUS_QUETZALCOATLUS_MAN, CRETACEOUS_SINOPTERUS_MAN, JURASSIC_ARCHAEOPTERYX_MAN, JURASSIC_PTERODACTYLUS_MAN, JURASSIC_JEHOLOPTERUS_MAN, JURASSIC_RHAMPHORHYNCHUS_MAN and TRIASSIC_SHAROVIPTERYX_MAN. The ANIMAL_PERSON variation replaces their gaits but does not remove FLIER.

### SPECIFIC_FOOD
- **Carriers:** 6 creatures (2 wild: the pandas, plus their man and giant versions).
- **Value:** each carries 3 entries: `PLANT:BAMBOO, ARROW`, `PLANT:BAMBOO, GOLDEN` and `PLANT:BAMBOO, HEDGE` (the plant ids really contain ", ").

### GOBBLE_VERMIN_CLASS / GOBBLE_VERMIN_CREATURE
- **GOBBLE_VERMIN_CLASS:** 15 carriers overall, 7 wild. The value is always EDIBLE_GROUND_BUG. Every carrier is BENIGN.
- **GOBBLE_VERMIN_CREATURE:** 0 carriers, in no file.

### SENSE_CREATURE_CLASS
- **In the creature raws:** 0.
- **In the procedural generator:** the night-troll generator writes `[SENSE_CREATURE_CLASS:GENERAL_POISON:15:4:0:1]`. See string-census.tsv.

### SMALL_REMAINS
- **Carriers:** 131 overall, 115 wild.
- **Value:** it never takes one; it is always the bare `[SMALL_REMAINS]`.

### BIOME
- **Tokens used:** 76 distinct BIOME tokens overall, 75 on wild species.
- **Biomes per wild species:** 184 species have 1 biome, 87 have 2 and 26 have 3; the most is 11.
- **Full count (all / wild):**

  SHRUBLAND_TEMPERATE 150/29; SAVANNA_TEMPERATE 117/24; GRASSLAND_TEMPERATE 105/26; ANY_TEMPERATE_FOREST 104/38; SHRUBLAND_TROPICAL 91/26; ANY_DESERT 85/29; FOREST_TEMPERATE_BROADLEAF 83/7; SAVANNA_TROPICAL 78/25; NOT_FREEZING 70/28; ANY_TROPICAL_FOREST 65/23; OCEAN_TEMPERATE 65/39; GRASSLAND_TROPICAL 59/20; FOREST_TROPICAL_MOIST_BROADLEAF 57/25; OCEAN_TROPICAL 55/31; FOREST_TAIGA 52/19; DESERT_BADLAND 52/2; MARSH_TEMPERATE_FRESHWATER 51/8; TUNDRA 47/17; SUBTERRANEAN_CHASM 46/40; ANY_OCEAN 44/17; MOUNTAIN 41/16; RIVER_TEMPERATE_FRESHWATER 40/16; LAKE_TEMPERATE_FRESHWATER 37/15; OCEAN_ARCTIC 36/22; ANY_GRASSLAND 33/11; FOREST_TROPICAL_DRY_BROADLEAF 27/5; ANY_SHRUBLAND 27/9; ANY_SAVANNA 27/9; ANY_LAKE 26/6; RIVER_TEMPERATE_BRACKISHWATER 26/12; ANY_WETLAND 25/9; MARSH_TROPICAL_FRESHWATER 25/6; SWAMP_MANGROVE 23/9; LAKE_TEMPERATE_BRACKISHWATER 22/10; SWAMP_TEMPERATE_FRESHWATER 22/4; RIVER_TROPICAL_FRESHWATER 21/11; SUBTERRANEAN_WATER 19/14; ANY_FOREST 18/6; LAKE_TROPICAL_FRESHWATER 18/10; SWAMP_TROPICAL_FRESHWATER 18/6; RIVER_TROPICAL_BRACKISHWATER 17/7; MARSH_TROPICAL_SALTWATER 16/5; DESERT_ROCK 16/2; FOREST_TEMPERATE_CONIFER 15/3; MARSH_TEMPERATE_SALTWATER 15/6; POOL_TROPICAL_SALTWATER 15/1; RIVER_TROPICAL_SALTWATER 14/6; ANY_RIVER 13/5; ANY_TEMPERATE_WETLAND 12/4; ANY_POOL 11/11; ANY_TROPICAL 11/4; FOREST_TROPICAL_CONIFER 11/3; SWAMP_TROPICAL_SALTWATER 11/5; ANY_TEMPERATE_LAKE 10/4; LAKE_TROPICAL_BRACKISHWATER 10/6; LAKE_TROPICAL_SALTWATER 10/6; DESERT_SAND 10/2; POOL_TEMPERATE_SALTWATER 10/0; ANY_LAND 9/2; ANY_TROPICAL_WETLAND 7/3; RIVER_TEMPERATE_SALTWATER 7/7; POOL_TEMPERATE_FRESHWATER 7/3; GLACIER 6/4; POOL_TEMPERATE_BRACKISHWATER 6/2; ANY_TEMPERATE_RIVER 6/2; ANY_TEMPERATE 5/2; LAKE_TEMPERATE_SALTWATER 5/3; SUBTERRANEAN_LAVA 5/5; ANY_TEMPERATE_MARSH 4/2; ANY_TEMPERATE_SWAMP 4/2; SWAMP_TEMPERATE_SALTWATER 4/2; ANY_TROPICAL_SWAMP 3/1; ALL_MAIN 2/2; TAIGA 1/1; POOL_TROPICAL_FRESHWATER 1/1; POOL_TROPICAL_BRACKISHWATER 1/1.

- **Oddity:** `TAIGA` (1 creature) sits beside `FOREST_TAIGA` (52). That 1 is worth checking against the Biome token page.
