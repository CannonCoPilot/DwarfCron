## Where the tool size bands put the classic predators (whole natural species set, ignoring layer/biome)

| species | cm3 | tool band | LP | BENIGN | cluster max | class (baseline) | may eat units / vermin / sentients (baseline) | eats DEER? (baseline) | class (FIX3) | units / vermin / sentients (FIX3) | eats DEER? (FIX3) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| WOLF | 40000 | small | LP |  | 7 | small_pred | 158 / 104 / 0 | yes | medium_pred | 502 / 0 / 192 | yes |
| COYOTE | 15000 | small |  |  | 10 | small_pred | 139 / 104 / 0 | yes | small_pred | 245 / 104 / 0 | yes |
| FOX | 6000 | small |  | BENIGN | 1 | small_pred | 0 / 104 / 0 | no | small_prey | 0 / 0 / 0 | no |
| DINGO | 20000 | small | LP |  | 12 | small_pred | 158 / 104 / 0 | yes | medium_pred | 496 / 0 / 192 | yes |
| HYENA | 60000 | small | LP |  | 15 | small_pred | 158 / 104 / 0 | yes | medium_pred | 506 / 0 / 192 | yes |
| COUGAR | 60000 | small | LP |  | 1 | small_pred | 0 / 104 / 0 | no | medium_pred | 444 / 0 / 183 | yes |
| LION | 200000 | medium | LP |  | 3 | medium_pred | 334 / 0 / 0 | yes | large_pred | 520 / 0 / 192 | yes |
| TIGER | 225000 | medium | LP |  | 1 | medium_pred | 280 / 0 / 0 | yes | large_pred | 520 / 0 / 192 | yes |
| LEOPARD | 50000 | small | LP |  | 1 | small_pred | 0 / 104 / 0 | no | medium_pred | 442 / 0 / 183 | yes |
| JAGUAR | 75000 | small | LP |  | 1 | small_pred | 0 / 104 / 0 | no | medium_pred | 444 / 0 / 183 | yes |
| CHEETAH | 50000 | small | LP |  | 1 | small_pred | 0 / 104 / 0 | no | medium_pred | 442 / 0 / 183 | yes |
| BEAR_BLACK | 120000 | small | LP |  | 1 | small_pred | 0 / 104 / 0 | no | medium_pred | 451 / 0 / 183 | yes |
| BEAR_GRIZZLY | 200000 | medium | LP |  | 1 | medium_pred | 280 / 0 / 0 | yes | large_pred | 520 / 0 / 192 | yes |
| BEAR_POLAR | 400000 | medium | LP |  | 1 | medium_pred | 280 / 0 / 0 | yes | large_pred | 530 / 0 / 192 | yes |
| CROCODILE_SALTWATER | 800000 | medium | LP |  | 3 | medium_pred | 334 / 0 / 0 | yes | large_pred | 534 / 0 / 192 | yes |
| ALLIGATOR | 400000 | medium | LP |  | 3 | medium_pred | 334 / 0 / 0 | yes | large_pred | 530 / 0 / 192 | yes |
| ANACONDA | 100000 | small | LP |  | 1 | small_pred | 0 / 104 / 0 | no | medium_pred | 448 / 0 / 183 | yes |
| SHARK_GREAT_WHITE | 2000000 | large | LP |  | 1 | large_pred | 464 / 0 / 183 | yes | large_pred | 539 / 0 / 192 | yes |
| SHARK_BLUE | 300000 | medium | LP |  | 1 | medium_pred | 280 / 0 / 0 | yes | large_pred | 522 / 0 / 192 | yes |
| ORCA | 5000000 | large |  | BENIGN | 9 | large_pred | 295 / 0 / 0 | yes | giant_large_prey | 0 / 0 / 0 | no |
| BIRD_EAGLE | 4000 | small |  | BENIGN | 1 | small_pred | 0 / 104 / 0 | no | small_prey | 0 / 0 / 0 | no |
| BIRD_OWL_GREAT_HORNED | 2000 | small |  |  | 1 | small_pred | 0 / 104 / 0 | no | small_pred | 118 / 104 / 0 | yes |
| BLIND_CAVE_BEAR | 200000 | medium | LP |  | 1 | medium_pred | 280 / 0 / 0 | yes | large_pred | 520 / 0 / 192 | yes |
| CROCODILE_CAVE | 600000 | medium | LP |  | 1 | medium_pred | 280 / 0 / 0 | yes | large_pred | 532 / 0 / 192 | yes |
| JABBERER | 4500000 | large | LP |  | 1 | large_pred | 464 / 0 / 183 | yes | large_pred | 540 / 0 / 192 | yes |
| GIANT_WOLF | 486800 | medium | LP |  | 1 | giant_pred | 464 / 0 / 183 | yes | giant_pred | 531 / 0 / 192 | yes |

## Natural non-giant, non-sentient predators by tool band x LP x BENIGN

| band | LP | BENIGN | n |
|---|---|---|---|
| large | False | True | 2 |
| large | True | False | 3 |
| medium | False | False | 1 |
| medium | False | True | 1 |
| medium | True | False | 17 |
| small | False | False | 25 |
| small | False | True | 13 |
| small | True | False | 19 |

Rule D eaters, baseline (LP and >=1M cm3, plus giant predators): non-giant = GIANT_ALLIGATOR, GIANT_BEAR_BLACK, GIANT_BEAR_GRIZZLY, GIANT_BEAR_POLAR, GIANT_CROCODILE_SALTWATER, GIANT_LION, GIANT_TIGER, JABBERER, SEA_SERPENT, SHARK_GREAT_WHITE

Large-band (>=1M) natural predators, any tag: JABBERER, ORCA, SEA_SERPENT, SHARK_GREAT_WHITE, SPERM_WHALE

Allowed unit pairs with prey >=3x eater mass, by config: baseline 5756, cls_lp+1 10264, FIX 18304, FIX_ratio 2059, FIX3 8190, FIX3_ratio 601

## Allowed (baseline) unit pairs where the prey is >=3x the eater: 5756 pairs; examples (ratio, eater, prey)


Non-giant, non-AP examples only: BIRD_KEA>DEER (140x), BIRD_KEA>REINDEER (130x), BIRD_KEA>PANDA (130x), LION>SPERM_WHALE (125x), LION>SHARK_WHALE (100x), BIRD_KEA>WARTHOG (100x), BIRD_KEA>MONITOR_LIZARD (100x), BIRD_KEA>FISH_SKATE_COMMON (100x), BIRD_KEA>ELK_BIRD (100x), BIRD_KEA>BEAR_SLOTH (100x), BIRD_BUZZARD>DEER (100x), BIRD_BUZZARD>REINDEER (93x), BIRD_BUZZARD>PANDA (93x), BIRD_KEA>KANGAROO (90x), BIRD_KEA>BIRD_OSTRICH (90x)

## Non-vermin pool make-up (spring)

| embark | layer | non-vermin pool | animal people | giants | high-value | giants among high-value |
|---|---|---|---|---|---|---|
| TEMP_GRASS_FOREST | land | 149 | 37% | 36% | 44% | 82% |
| TEMP_GRASS_FOREST | flying | 66 | 44% | 42% | 42% | 100% |
| TROP_SAVANNA_SHRUB | land | 116 | 37% | 35% | 57% | 62% |
| TROP_SAVANNA_SHRUB | flying | 41 | 44% | 41% | 41% | 100% |
| TAIGA_TUNDRA | land | 87 | 38% | 36% | 52% | 69% |
| TAIGA_TUNDRA | flying | 36 | 44% | 42% | 42% | 100% |
| DESERT | land | 84 | 39% | 38% | 48% | 80% |
| DESERT | flying | 44 | 43% | 41% | 41% | 100% |
| TROP_WETLAND | land | 66 | 39% | 36% | 59% | 62% |
| TROP_WETLAND | flying | 40 | 42% | 40% | 40% | 100% |
| LAKE_RIVER | land | 149 | 37% | 36% | 44% | 82% |
| LAKE_RIVER | flying | 81 | 42% | 41% | 41% | 100% |
| OCEAN_SHORE | land | 105 | 37% | 35% | 39% | 90% |
| OCEAN_SHORE | flying | 68 | 43% | 41% | 41% | 100% |

## Sentient pool entries with no allowed eater anywhere in their pool (spring; per embark x layer)

| config | sentient entries | no eater | share | examples |
|---|---|---|---|---|
| baseline | 490 | 8 | 2% | AMPHIBIAN_MAN, BAT_MAN, CAVE_SWALLOW_MAN, GREMLIN, OLM_MAN, REPTILE_MAN, RODENT MAN, TROGLODYTE |
| D_tag | 490 | 0 | 0% |  |
| FIX | 490 | 17 | 3% | BARN_OWL_MAN, BAT_MAN, BUTTERFLY_MONARCH_MAN, EAGLE_MAN, FIREFLY_MAN, FLY_MAN, KESTREL_MAN, MANTIS_MAN |
| FIX3 | 490 | 17 | 3% | BARN_OWL_MAN, BAT_MAN, BUTTERFLY_MONARCH_MAN, EAGLE_MAN, FIREFLY_MAN, FLY_MAN, KESTREL_MAN, MANTIS_MAN |
| FIX3_ratio | 490 | 18 | 4% | BARN_OWL_MAN, BAT_MAN, BUTTERFLY_MONARCH_MAN, EAGLE_MAN, FIREFLY_MAN, FLY_MAN, KESTREL_MAN, MANTIS_MAN |

- TEMP_GRASS_FOREST flying: 21 predators, non-BENIGN: BIRD_BUZZARD, BIRD_KEA, BIRD_OWL_GREAT_HORNED, BUZZARD_MAN, GIANT_BUZZARD, GIANT_GREAT_HORNED_OWL, GIANT_KEA, GREAT_HORNED_OWL_MAN, KEA_MAN
- TROP_SAVANNA_SHRUB flying: 18 predators, non-BENIGN: BIRD_OWL_GREAT_HORNED, BIRD_VULTURE, GIANT_GREAT_HORNED_OWL, GIANT_VULTURE, GREAT_HORNED_OWL_MAN, VULTURE_MAN
- TAIGA_TUNDRA flying: 12 predators, non-BENIGN: BIRD_OWL_GREAT_HORNED, GIANT_GREAT_HORNED_OWL, GREAT_HORNED_OWL_MAN
- DESERT flying: 18 predators, non-BENIGN: BIRD_BUZZARD, BIRD_OWL_GREAT_HORNED, BIRD_VULTURE, BUZZARD_MAN, GIANT_BUZZARD, GIANT_GREAT_HORNED_OWL, GIANT_VULTURE, GREAT_HORNED_OWL_MAN, VULTURE_MAN
- TROP_WETLAND flying: 15 predators, non-BENIGN: none
- LAKE_RIVER flying: 24 predators, non-BENIGN: BIRD_BUZZARD, BIRD_KEA, BIRD_OWL_GREAT_HORNED, BUZZARD_MAN, GIANT_BUZZARD, GIANT_GREAT_HORNED_OWL, GIANT_KEA, GREAT_HORNED_OWL_MAN, KEA_MAN
- OCEAN_SHORE flying: 24 predators, non-BENIGN: BIRD_BUZZARD, BIRD_KEA, BIRD_OWL_GREAT_HORNED, BUZZARD_MAN, GIANT_BUZZARD, GIANT_GREAT_HORNED_OWL, GIANT_KEA, GREAT_HORNED_OWL_MAN, KEA_MAN

## Cavern candidates: DF depth vs depth+ceiling (natural, spring)

| layer | DF depth range | after score ceiling | removed by the ceiling (score) |
|---|---|---|---|
| cav1 | 34 | 25 | ANT_MAN(4), CAVE_FISH_MAN(5), FISH_CAVE(4), GIANT_EARTHWORM(6), HELMET_SNAKE(5), LOBSTER_CAVE(7), POND_GRABBER(6), SERPENT_MAN(5), SPIDER_CAVE(9) |
| cav2 | 43 | 32 | CAVE_FISH_MAN(5), CAVE_FLOATER(8), FLOATING_GUTS(10), GIANT_EARTHWORM(6), HELMET_SNAKE(5), LOBSTER_CAVE(7), POND_GRABBER(6), SERPENT_MAN(5), SPIDER_CAVE(9), SPIDER_CAVE_GIANT(9), VORACIOUS_CAVE_CRAWLER(5) |
| cav3 | 21 | 21 | - |

- cav1 pool (baseline): AMPHIBIAN_MAN[small_pred,3], BAT[v_flybird,0], BAT_GIANT[medium_pred,2], BAT_MAN[small_prey,2], BIRD_SWALLOW_CAVE[v_flybird,1], BIRD_SWALLOW_CAVE_GIANT[medium_pred,3], BLIND_CAVE_BEAR[medium_pred,3], CAP_HOPPER[v_ground_fish,3], CAVE_SWALLOW_MAN[small_prey,3], CROCODILE_CAVE[medium_pred,3], DRALTHA[giant_large_prey,3], DRUNIAN[small_prey,2], ELK_BIRD[small_prey,3], GREMLIN[small_pred,3], MOLE_DOG_NAKED[small_prey,3], MOLE_GIANT[medium_prey,2], OLM[v_ground_fish,1], OLM_GIANT[medium_pred,3], OLM_MAN[small_prey,3], RAT_GIANT[medium_prey,2], RAT_LARGE[small_prey,2], REPTILE_MAN[small_pred,3], RODENT MAN[small_pred,2], TOAD_GIANT_CAVE[medium_pred,3], TROGLODYTE[small_pred,2]
- cav2 pool (baseline): AMPHIBIAN_MAN[small_pred,3], ANT_MAN[small_prey,4], BAT[v_flybird,0], BAT_GIANT[medium_pred,2], BAT_MAN[small_prey,2], BIRD_SWALLOW_CAVE[v_flybird,1], BIRD_SWALLOW_CAVE_GIANT[medium_pred,3], BLIND_CAVE_BEAR[medium_pred,3], BUGBAT[small_prey,3], CAP_HOPPER[v_ground_fish,3], CAVE_SWALLOW_MAN[small_prey,3], CROCODILE_CAVE[medium_pred,3], CRUNDLE[small_pred,3], DRALTHA[giant_large_prey,3], DRUNIAN[small_prey,2], ELK_BIRD[small_prey,3], FISH_CAVE[v_ground_fish,4], GREEN_DEVOURER[small_prey,4], GREMLIN[small_pred,3], JABBERER[large_pred,4], MOLEMARIAN[small_pred,3], MOLE_GIANT[medium_prey,2], OLM[v_ground_fish,1], OLM_GIANT[medium_pred,3], OLM_MAN[small_prey,3], PLUMP_HELMET_MAN[small_prey,4], RAT_GIANT[medium_prey,2], REPTILE_MAN[small_pred,3], RODENT MAN[small_pred,2], RUTHERER[giant_large_prey,3], TOAD_GIANT_CAVE[medium_pred,3], TROGLODYTE[small_pred,2]
- cav3 pool (baseline): AMPHIBIAN_MAN[small_pred,3], ANT_MAN[small_prey,4], BUGBAT[small_prey,3], CAVE_BLOB[small_prey,11], CAVE_FLOATER[small_prey,8], CRUNDLE[small_pred,3], ELK_BIRD[small_prey,3], FLESH_BALL[small_prey,10], FLOATING_GUTS[small_prey,10], GREEN_DEVOURER[small_prey,4], GREMLIN[small_pred,3], HUNGRY_HEAD[small_pred,5], JABBERER[large_pred,4], MOLEMARIAN[small_pred,3], PLUMP_HELMET_MAN[small_prey,4], REPTILE_MAN[small_pred,3], RODENT MAN[small_pred,2], RUTHERER[giant_large_prey,3], SERPENT_MAN[small_pred,5], SPIDER_CAVE_GIANT[medium_pred,9], VORACIOUS_CAVE_CRAWLER[medium_pred,5]
- deep pool (baseline): IMP_FIRE[small_pred,6], MAGMA_CRAB[small_prey,8]
