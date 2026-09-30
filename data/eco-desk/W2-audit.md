# W2: the tool's classification checked against the raws (desk)

**Inputs**
- The tool's model: `data/fixtures/species-model.tsv`, which the tool's own `MODEL.audit` (SW:1131) writes. All 363 wildlife species join to it.
- The raws: `eco/census.json`, the vanilla 53.16 raws with inheritance resolved.
- Pair rules: re-implemented from `eats()` (SW:1374), `MODEL.REACH` (SW:1361) and `ecoArmed`/`ecoRealm`/`ecoWrite` (SW:3224/3236/3311). Scripts are in `eco/w/w2.py`; raw output is in `w2-out*.txt`.

**Notation**
- SW = `seasonal-wildlife.lua` v6.8.0. Wildlife = the census's 363 species (326 in the tool's `natural` class, 25 `mythic`, 12 `unliving`).
- A pair "can co-occur" when the two species share a base biome, or when one is an ocean species and the other has land biomes of the same climate. This is a desk proxy for "could be on one embark".

## (a) Habitat and layer

| check | count | species |
|---|---|---|
| Raws say water (AQUATIC, AMPHIBIOUS or all-water BIOME) but the tool says land/flier | **0** | — |
| Tool says water (aquatic/semiaquatic) with neither AQUATIC nor AMPHIBIOUS (all-water biome rule, SW:1100) | 9 | BIRD_PENGUIN, _LITTLE, _EMPEROR, BEAVER, MINK, LEECH; FLESH_BALL, PLUMP_HELMET_MAN, ELEMENTMAN_MUD |
| Tool says land but a biome is SUBTERRANEAN_WATER | 2 | CRUNDLE, CAVE_BLOB (cavern) |
| SWIMS_INNATE on tool-land non-vermin | 124 of 149 | the tool ignores it (comment SW:971; `e.swims` is stored at SW:1065 and never used). This is correct: the wiki says "fortress mode AI never paths into water anyway". |
| Legacy `isAquatic` (counts AQUATIC_UNDERSWIM, the display-only flag) | — | defined at SW:892 and never called; dead code |

From the raws' side, habitat is consistent: every AQUATIC species is `aquatic`, and every AMPHIBIOUS species is `semiaquatic`, or `waterbird` if it flies. The defects are in the **layer/realm** a unit is given, not in the habitat.

### Realm

Background:
- `ecoRealm(u)` (SW:3224) keys on the unit's population entry, through `WILD.layerOf` (SW:2035).
- An entry with a feature index is `water`, which returns nil and is excluded from ecology. Any other surface entry is `land`.
- Ocean life arrives from surface entries (PLAN.md:25, 87), so it gets realm `land`.

| group (wildlife) | n | what the ecology write does with it |
|---|---|---|
| Any OCEAN biome | 81 | Realm `land`. Split: 51 aquatic (26 prey, 25 vermin), 15 aquatic predators, 10 semiaquatic, 5 waterbird. |
| ↳ LARGE_PREDATOR, armed at realm `land` | **12** | FISH_LAMPREY_SEA, SHARK_GREAT_WHITE, _FRILL, _MAKO_SHORTFIN, _MAKO_LONGFIN, _TIGER, _BULL, _REEF_BLACKTIP, _BLUE, _HAMMERHEAD, SEA_SERPENT, SEA_MONSTER. Each is written PREDATOR_OR_PREY against **every** wild land unit, caravan animal and visitor mount in realm `land`. |
| ↳ not LP, not vermin: targets of every land LP | 42 | Seals, walrus, penguins, sea otter, orca, sperm whale, all non-LP sharks and big fish (e.g. BEAR_GRIZZLY×SHARK_BASKING, WOLF×FISH_COD are written). |
| Lake biomes only (no land or ocean biome) | 24 | **Ambiguous in the tool's own notes.** SW:734 says lake life carries a feature index (realm nil). PLAN.md:25 says lake life comes from surface entries (realm `land`). Examples: HIPPO, FISH_PIKE, BEAVER, RIVER OTTER, SNAPPING TURTLE, BIRD_LOON. This decides whether W1's WOLF×FISH_PIKE cell can be written at all. |
| River/pool biomes only | 8 | Feature entries, so realm nil and never in ecology: TOAD, PLATYPUS, POND_TURTLE, DAMSELFLY, DRAGONFLY, MOGHOPPER, FLY_ACORN, GNAT_BLOOD. |
| Species added by `addNewSpecies` | any | Always written with `feature_idx = -1` (SW:2566). An aquatic species added as invasive therefore becomes a surface/`land` entry, the same issue as ocean life. |

## (b) Role

The rules as the tool has them:
- `MODEL.role` (SW:1103) calls a species a predator if any caste has CARNIVORE, BONECARN, LARGE_PREDATOR or AMBUSHPREDATOR, with 4 curated overrides (SW:982).
- The relation write arms only `largePred` species (`ecoArmed`, SW:3236). T4 and capabilities.md explain why: DF's hunting drive fires only for LARGE_PREDATOR.

| check | count | species / note |
|---|---|---|
| Tool predators (non-vermin) | 103 | Another 11 vermin also read as predator (the spiders, scorpion, lizards, POND_TURTLE). They are not units. |
| Tool predator **and BENIGN** | **16** | FOX, BADGER, WOLVERINE, MONGOOSE, STOAT, RIVER OTTER, SEA OTTER, BIRD_EAGLE, _FALCON_PEREGRINE, _KESTREL, _OSPREY, _OWL_BARN, _OWL_SNOWY, BIRD_SWALLOW_CAVE_GIANT (all BONECARN); SPERM_WHALE (CARNIVORE); ORCA (curated). The wiki says BENIGN "runs away from any creatures that are not friendly". T4 measured it: a written relation is ignored. |
| Tool predator, **not LP**, so never armed | **43** | 16 BENIGN plus 27 unmarked: COYOTE, JACKAL, BOBCAT, LYNX, OCELOT, HONEY BADGER, COATI, the 9 snakes, GILA_MONSTER, IGUANA, MONITOR_LIZARD, the 2 snapping turtles, OCTOPUS, BIRD_KEA, _BUZZARD, _VULTURE, _OWL_GREAT_HORNED, CRUNDLE, REACHER. By habitat: 24 land, 10 flier, 5 semiaquatic, 3 aquatic, 1 waterbird. |
| LARGE_PREDATOR the tool calls prey or vermin | **0** | The DIET list includes LP, and no vanilla vermin is LP. |
| LP only on the water layer (so never armed) | 0 by raws | 0 if lake species are surface entries; see the lake row in (a). |
| LP in a non-natural class, armed anyway | **20** | `ecoArmed` does not test `e.locked`/`eco`, while `eats()` refuses across classes (SW:1377). Mythic: TROLL, OGRE, YETI, SASQUATCH, BLIZZARD_MAN, WOLF_ICE, BEAK_DOG, STRANGLER, BLIND_CAVE_OGRE, CAVE_DRAGON, SEA_MONSTER. Unliving: GRIMELING, NIGHTWING, BLOOD_MAN, and the 6 ELEMENTMAN_*. |
| LP with a water habitat, armed at realm `land` | 15 | The 12 ocean LPs above, plus ALLIGATOR and CROCODILE_SALTWATER (river + wetland) and GRIMELING. |
| Curated overrides | 2 wildlife | ORCA→predator: BENIGN, not LP, so never armed; the override only affects eats(), coupling and roster. SHARK_WHALE→prey: already prey (BENIGN, no diet token). |
| The 26 LPs whose role reason is "LARGE_PREDATOR" (no diet token) | 26 | Includes BEAR_GRIZZLY, BEAR_BLACK and the sharks. Correct as predators; they carry no CARNIVORE or BONECARN. |

## (c) Pair rules

Two different predicates are in play:

| predicate | used by | rule |
|---|---|---|
| `eats(e, p)` | coupling (`matchPredators` SW:1411), pair guarantee (SW:1567), co-align, water coupling (SW:3929) | same class; same cavern/non-cavern layer; predator; `REACH[pred habitat][prey habitat]`; if both are aquatic, a shared water body; no peer ≥0.5× mass; take ≥ need |
| `ecoWrite` | the relation write, which is the only thing DF acts on | predator = LP (realm land/cavern); target = **every** other wild unit in the same realm, plus non-fort animals. It calls none of `eats()`/REACH/size/class (SW:3311-3345). |

### What ecoWrite writes, judged by eats()

Species pairs among wildlife: 60 armed species (40 natural) × all targets in the same realm.

| scope | pairs written | eats() ok | refused by REACH | by size | by peer | by water body | by class |
|---|---|---|---|---|---|---|---|
| all wildlife, same realm | 6,504 | 2,219 | 1,627 | 398 | 99 | 170 | 1,991 |
| can co-occur | 3,450 | 1,104 | 1,204 | 200 | 61 | 48 | 833 |
| **can co-occur, natural × natural** | **2,599** | **1,091 (42%)** | **1,201 (46%)** | 198 | 61 | 48 | — |

Natural co-occurring pairs, by predator habitat and verdict:

| predator habitat | eats() ok | REACH | size | peer | water body |
|---|---|---|---|---|---|
| aquatic (11 ocean LPs + cavern) | 290 | **917** (all against land/flier targets: shark×deer, lamprey×eagle) | 91 | 27 | — |
| land (21) | 722 | **271** (land LP × ocean fish: BEAR_GRIZZLY×SHARK_BASKING, WOLF×FISH_COD) | 94 | 31 | — |
| semiaquatic (ALLIGATOR, CROCODILE_SALTWATER, cave) | 62 | 13 | 1 | — | 48 (river crocodilian × sea fish) |
| flier (cavern LPs) | 17 | — | 12 | 3 | — |

Most REACH-refused targets per predator: SHARK_FRILL, SHARK_BLUE and SEA_SERPENT 102 each; the other ocean sharks 61-93; FISH_LAMPREY_SEA 54; DINGO 28; COUGAR 27; LION and LEOPARD 21 each.

### What eats() allows that ecoWrite never writes

Natural, can co-occur: 2,211 eats()-ok pairs, of which **1,120 are never written**.
- **Unarmed predators:** 42 non-LP predators account for most of it. By habitat: land 624, flier 156, aquatic 117, semiaquatic 85, waterbird 22 (e.g. BOBCAT×RABBIT, FALCON×DUCK).
- **LP × LP:** 113 pairs are never written, because an LP is never a target (e.g. SHARK_GREAT_WHITE×SHARK_BLUE, ×FISH_LAMPREY_SEA).
- **Water layer:** 7 pairs.

### Cross land/water pairs that eats() allows (natural, co-occurring: 301)

- **REACH allows:**
  - flier/land predator × semiaquatic prey: e.g. BIRD_EAGLE×BIRD_PENGUIN, WOLF×CAPYBARA;
  - semiaquatic × land: ALLIGATOR×DEER;
  - aquatic × waterbird: SHARK_GREAT_WHITE×BIRD_DUCK, FISH_LAMPREY_SEA×BIRD_PUFFIN;
  - waterbird × aquatic.
- **REACH forbids:** land × aquatic and aquatic × land/flier.

### The W1 cells as the tool sees them

| pair | eats() | ecoWrite writes it | note |
|---|---|---|---|
| FISH_LAMPREY_SEA × DEER | REACH ✗ | **yes** | Aquatic LP, realm land. Also fails size: take 30k < need 126k. |
| SHARK_BLUE × HARP_SEAL | ok | yes | |
| SHARK_BLUE × DEER / SHARK_GREAT_WHITE × DEER | REACH ✗ | **yes** | The ocean-realm defect. |
| ALLIGATOR / CROCODILE_SALTWATER × DEER, × CAPYBARA | ok | yes | E41/41b: the crocodile is not pulled from water. |
| ALLIGATOR × FISH_PIKE | ok | yes, if pike is realm land (lake-entry question) | |
| WOLF × CAPYBARA, LION × CAPYBARA | ok | yes | |
| WOLF × SEA OTTER | peer ✗ (otter is a BONECARN predator ≥0.5× wolf) | yes | |
| WOLF × FISH_PIKE, LION × FISH_PIKE | REACH ✗ | yes, if pike is realm land | |
| BEAR_POLAR × HARP_SEAL; SHARK_BLUE × BIRD_PENGUIN | ok | yes | |
| WOLF × SHARK_BLUE | REACH ✗ | no (sharks are LP, never targets) | |

W1 is therefore also the test of whether DF acts on REACH-forbidden written pairs. A shark written against a deer on the shore should give no attacks. If one does occur, REACH is too strict.

## Other model findings

- **Cohesion label** (SW:4225):
  - 24 LR LPs with cluster 1:1 get `pack`, e.g. cougar, tiger, the bears. Harmless: a lone animal has no one to follow.
  - 28 semiaquatic land-walkers get `school` (follow distance 5): penguins, hippo, walrus, crocodilians, otters, beaver, capybara.
  - 24 non-LP carnivores get `herd` (follow distance 8): fox, coyote, bobcat, snakes.
  - LOOSE_CLUSTERS (12 wild) is never read.
- **Seasons:** NO_SPRING, NO_SUMMER, NO_AUTUMN and NO_WINTER are never read. The roster deals quarters by climate lean, coldest to Winter (ROSTER.quarterOf SW:1459). 22 wild species are NO_WINTER, including BEAR_GRIZZLY, BEAR_BLACK, RABBIT, BADGER and GROUNDHOG. A Winter deal for one of them is a slot DF will not fill (T2 tests this).
- **SEA_SERPENT is class `natural`** in the fixture. It is an ocean LP ("giant limbless dragon", 9M cm3), so it is armed at realm `land` and enters the natural food web.

## Suggested tool changes

These follow from the counts above.

1. **Filter the write by `eats()`**, or at least by REACH and class. That removes ~46% of natural written pairs (REACH) and all cross-class pairs, and makes the write agree with the coupling and the pair guarantee.
2. **Realm from habitat, not only from the entry.** Give aquatic/semiaquatic units from surface entries the realm `water:<body>`. Ocean LPs would then pair only with ocean or shore targets, and land LPs never with sea fish.
3. **Make `ecoArmed` require `not e.locked`**. That stops 20 mythic/unliving LPs from being armed.
4. **Settle the lake-entry question:** SW:734 vs PLAN.md:25.
5. **Mask NO_\* seasons in the roster deal**, or report the conflict.
6. **Decide on the 42 unarmable predators.** E32b showed that a runtime LP flip makes a BENIGN badger attack. Either use an LP flip as the arming lever (T1 tests it on COYOTE), or drop them from the predator role the coupling uses.
