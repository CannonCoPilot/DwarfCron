# Token clusters in DF 53.16 vanilla creatures

Source: `token_census.py`. The dendrograms and orders are in `cluster-order.json`; the flat cuts, top pairs, never-together pairs and subset relations are in `cluster-cuts.json`; the full matrices are in `cooccur-matrix-{all,wild}.csv` and `jaccard-matrix-{all,wild}.csv`.

## Method

- **Presence:** a creature carries a token when the token is a tag name anywhere in its resolved tag list (census.py resolver, any caste).
- **Tokens clustered:** the tokens present on at least 3 creatures of the population. That is 75 tokens for the 363 wildlife species and 82 for all 967 creatures.
- **Clustering:** distance = 1 − Jaccard, with average linkage (UPGMA). It is implemented in the script (scipy is not installed). Ties are broken by index.
- **Matrix order:** rows and columns in the CSVs follow the cluster order, with the unclustered tokens (fewer than 3 carriers) appended at the end.

**Caveat.** Jaccard rewards prevalence. BIOME and POPULATION_NUMBER are on 363/363 wild species, GAIT on 360, NATURAL on 331, SWIMS_INNATE on 294, PETVALUE on 288, MUNDANE on 286 and LARGE_ROAMING on 248. These tokens form one large "backbone" cluster because they are nearly universal, not because they share a meaning. Read the backbone as the background.

## Clusters in the wildlife set (363 species)

Cut at a distance of 0.5 (mean pairwise Jaccard ≥ about 0.5), from cluster-cuts.json. "all / any" = the number of species carrying every token of the cluster / any token of it.

| cluster | all / any | mean J | what it is |
|---|---|---|---|
| CANNOT_JUMP, UNDERSWIM, NO_DRINK, AQUATIC, IMMOBILE_LAND | 75 / 152 | 0.73 | **Aquatic core.** 77 species carry the four of AQUATIC+IMMOBILE_LAND+NO_DRINK+UNDERSWIM, 75 of them also CANNOT_JUMP and 74 also ALL_ACTIVE. IMMOBILE_LAND ⊂ AQUATIC (80 of 83); the only AQUATIC species without IMMOBILE_LAND are MOON_SNAIL, SPONGE and LOBSTER_CAVE. 80 of the 83 AQUATIC species are ALL_ACTIVE, so at a cut of 0.7 ALL_ACTIVE joins this cluster. |
| SMALL_REMAINS, VERMIN_GROUNDER | 93 / 115 | 0.81 | **Vermin body.** VERMIN_GROUNDER ⊂ SMALL_REMAINS. So are VERMIN_NOTRAP (58), FISHITEM (39), VERMIN_FISH (29), VERMIN_HATEABLE (22), VERMIN_SOIL, VERMIN_BITE, VERMIN_EATER, VERMIN_MICRO, VERMIN_ROTTER, UBIQUITOUS, TRIGGERABLE_GROUP and GNAWER: every one of them sits inside SMALL_REMAINS. |
| FISHITEM, VERMIN_FISH | 29 / 39 | 0.74 | **Vermin fish.** VERMIN_FISH ⊂ FISHITEM ⊂ SMALL_REMAINS. |
| the backbone: PETVALUE, SWIMS_INNATE, MUNDANE, NATURAL, GAIT, POPULATION_NUMBER, BIOME, CLUSTER_NUMBER, LARGE_ROAMING | 128 / 363 | 0.73 | Prevalence cluster (see the caveat). At 0.7 it absorbs GRASSTRAMPLE, DIURNAL, FREQUENCY, PET_EXOTIC, BENIGN and MEANDERER. |
| LOW_LIGHT_VISION, UNDERGROUND_DEPTH | 28 / 56 | 0.50 | **Cavern.** LOW_LIGHT_VISION ⊂ UNDERGROUND_DEPTH. 27 of the 28 are G15. |
| ODOR_LEVEL, SMELL_TRIGGER (+ EXTRAVISION, NOBREATHE at 0.7) | 9 / 12 | 0.75 | **Cavern "sensory" block:** elemental men, BLOOD_MAN, fire imp and fire snake. SMELL_TRIGGER ⊂ ODOR_LEVEL, ⊂ EXTRAVISION, ⊂ UNDERGROUND_DEPTH and ⊂ ALL_ACTIVE. |
| STANDARD_GRAZER, VISION_ARC | 25 / 49 | 0.51 | **Grazers.** 25 of the 32 grazers carry VISION_ARC:50:310, the only VISION_ARC value in the raws. PACK_ANIMAL ⊂ STANDARD_GRAZER. |
| GOBBLE_VERMIN_CLASS, ROOT_AROUND | 7 / 7 | 1.00 | **Ground foragers:** BIRD_KIWI, BIRD_DUCK, BIRD_GOOSE, BIRD_PEAFOWL_BLUE, BIRD_TURKEY, HEDGEHOG and PANGOLIN. The two sets are identical, and all 7 are BENIGN. (In all creatures, PIG has ROOT_AROUND alone.) |
| WEBBER, WEBIMMUNE (+ VERMIN_BITE at 0.7) | 4 / 5 | 0.80 | **Spiders:** brown recluse, phantom, cave spider and giant cave spider. SNAKE_FIRE is WEBIMMUNE only. |
| CURIOUSBEAST_ITEM, LOOSE_CLUSTERS (+ CURIOUSBEAST_EATER at 0.7) | 7 / 13 | 0.54 | **Thieves.** CURIOUSBEAST_ITEM ⊂ CURIOUSBEAST_EATER (8 of 19). 7 of the 8 item thieves are LOOSE_CLUSTERS; COATI is the exception. 11 of the 12 LOOSE_CLUSTERS species carry some CURIOUSBEAST_* token; SPIDER_MONKEY is the exception. |
| PACK_ANIMAL, WAGON_PULLER | 4 / 8 | 0.50 | **Beasts of burden:** HORSE, WATER_BUFFALO, YAK and MUSKOX carry both. PACK_ANIMAL ⊂ BENIGN, ⊂ DIURNAL and ⊂ MEANDERER. |
| GNAWER, VERMIN_EATER (+ TRIGGERABLE_GROUP at 0.7) | 4 / 8 | 0.50 | **Rat-like vermin.** |

At a cut of 0.7 two more groups appear: **LAYS_EGGS + FLIER + STANCE_CLIMBER** (27 carry all three; 43 of the 60 fliers are STANCE_CLIMBER) and **VERMIN_MICRO + VERMIN_ROTTER**.

### Tokens that belong to no tight cluster

**LARGE_PREDATOR** has no tight cluster. Its best partner is UNDERGROUND_DEPTH, at J = 0.26 (24 of the 60 wild LPs are cavern). Next come LARGE_ROAMING (J 0.24; every wild LP is LARGE_ROAMING), BONECARN (19; J 0.23), GRASSTRAMPLE (31) and ALL_ACTIVE (44).
- **Guilds:** the 60 wild LPs are 24 G15 cavern, 21 G1 land and 15 G2 water.
- **Diet:** 26 of the 60 carry neither CARNIVORE nor BONECARN.
- **Activity:** 44 are ALL_ACTIVE, 8 DIURNAL, 6 NOCTURNAL, and 2 NOCTURNAL+CREPUSCULAR.

**BENIGN** sits in the backbone. Its best partners are PETVALUE (157 of 163), LARGE_ROAMING (141), MUNDANE and MEANDERER (93).

### Activity tokens

Every wild species (363 of 363), and every one of the 967 creatures, carries exactly one activity pattern:

| pattern | wild | all |
|---|---|---|
| ALL_ACTIVE | 183 | 445 |
| DIURNAL | 121 | 347 |
| NOCTURNAL | 37 | 108 |
| CREPUSCULAR + NOCTURNAL | 15 | 48 |
| CREPUSCULAR | 5 | 13 |
| CREPUSCULAR + DIURNAL | 1 | 3 |
| VESPERTINE | 1 | 3 |
| MATUTINAL | 0 | 0 |

- ALL_ACTIVE never co-occurs with DIURNAL, NOCTURNAL or VISION_ARC.
- **ALL_ACTIVE (wild):** vermin 55, cavern 53, and the water guilds (G10 17, G2 15, G9 8, G11 4).
- **DIURNAL (wild):** vermin 34, land prey 26, grazers 23, shore 12, waterbirds 6.
- **NOCTURNAL (wild):** spread thinly across the guilds.
- In the dendrogram DIURNAL joins the backbone next to BENIGN/MEANDERER, NOCTURNAL joins CREPUSCULAR (J 0.26), and ALL_ACTIVE joins the aquatic core.

## Clusters over all 967 creatures

These are the same structures, plus the animal-person and giant copies. At a cut of 0.5:

| cluster | all / any | J | note |
|---|---|---|---|
| CAN_LEARN + CAN_SPEAK | 300 / 311 | 0.97 | 285 of them are animal people |
| GOBBLE_VERMIN_CLASS + ROOT_AROUND | 15 / 16 | — | |
| WEBBER + WEBIMMUNE | 6 / 7 | — | |
| SMALL_REMAINS + VERMIN_GROUNDER | 106 / 132 | — | |
| FISHITEM + VERMIN_FISH | 32 / 42 | — | |
| PET_EXOTIC + PETVALUE | 449 / 591 | — | |
| IMMOBILE_LAND + UNDERSWIM + AQUATIC + NO_DRINK | 90 / 212 | — | |
| FLIER + STANCE_CLIMBER | 131 / 244 | — | |
| LOW_LIGHT_VISION + UNDERGROUND_DEPTH | 38 / 71 | — | |
| NOBREATHE + ODOR_LEVEL | 11 / 21 | — | |
| CURIOUSBEAST_ITEM + LOOSE_CLUSTERS | 19 / 37 | — | |
| STANDARD_GRAZER + VISION_ARC | 78 / 154 | — | |
| the backbone | — | — | SAVAGE, CLUSTER_NUMBER, LARGE_ROAMING, SWIMS_INNATE, NATURAL, GAIT, POPULATION_NUMBER, BIOME |

At 0.7:
- LARGE_PREDATOR + TRAINABLE form a pair (57 / 179, J 0.32).
- WAGON_PULLER + PACK_ANIMAL + TRAINABLE_WAR group together.
- COMMON_DOMESTIC + PET group together.

## Surprising coincidences and absences (wild unless stated)

1. **SAVAGE is a variation artefact.** It is on 571 of all creatures but on only 8 wild species (FOXSQUIRREL, MOGHOPPER, LIZARD_RHINO_TWO_LEGGED, FLY_ACORN, YETI, SASQUATCH, SEA_SERPENT, SPIDER_CAVE_GIANT). The other carriers are animal people (285), giants (179) and extinct creatures (99). In the all-creature set, SAVAGE lands in the backbone for that reason.
2. **VISION_ARC takes a single value, 50:310, on all 125 carriers.**
   - Wild carriers: mostly grazers and BENIGN prey. It is never on a LARGE_PREDATOR, and never on an ALL_ACTIVE species.
   - Everything else gets the default of 60:120, so by the raws the predators have the narrower field of view.
3. **GRASSTRAMPLE:0 is declared by every BENIGN carrier (57 of 57 wild).** Species without the token get the default of 5, so a declared grazer tramples less than an undeclared species. The nonzero values (20, and 50 for CAVE_DRAGON) belong to crocodilians, big lizards, ogres, trolls and cavern predators.
4. **LOOSE_CLUSTERS behaves as a thief marker.** 11 of its 12 wild carriers steal (CURIOUSBEAST_*), and 7 of the 8 item thieves carry it.
5. **GOBBLE_VERMIN_CLASS and ROOT_AROUND are the same 7 wild species.**
6. **PRONE_TO_RAGE (4 wild) is never on a LARGE_PREDATOR.** Two carriers are BENIGN (BADGER 1, WOLVERINE 10) and two are neither (HONEY BADGER 10, BLACK_MAMBA 1).
7. **LARGE_PREDATOR and BENIGN never co-occur**, in either population. Other pairs that are never together despite both tokens being common:
   - PET / PET_EXOTIC (50 / 172)
   - ALL_ACTIVE / DIURNAL / NOCTURNAL
   - LARGE_ROAMING / every VERMIN_* token and FISHITEM (SMALL_REMAINS overlaps LARGE_ROAMING on just 1 species)
   - MEANDERER / SMALL_REMAINS
   - GRASSTRAMPLE / AQUATIC and IMMOBILE_LAND
   - DIURNAL / AQUATIC, NO_DRINK and IMMOBILE_LAND. No aquatic species is diurnal: 80 of 83 are ALL_ACTIVE, 2 NOCTURNAL, 1 CREPUSCULAR.
   - NO_DRINK / STANCE_CLIMBER
   - LARGE_PREDATOR / SMALL_REMAINS
   - EVIL / MUNDANE
8. **Subset chains** (cluster-cuts.json `wild_subset`; the list excludes supersets present on ≥ 90% of the population):
   - SMELL_TRIGGER ⊂ ODOR_LEVEL ⊂ ALL_ACTIVE
   - IMMOBILE_LAND ⊂ AQUATIC; IMMOBILE_LAND ⊂ NO_DRINK
   - VERMIN_FISH ⊂ FISHITEM ⊂ SMALL_REMAINS
   - COMMON_DOMESTIC ⊂ PET; MOUNT ⊂ PET
   - PACK_ANIMAL ⊂ STANDARD_GRAZER
   - CURIOUSBEAST_ITEM ⊂ CURIOUSBEAST_EATER
   - UBIQUITOUS ⊂ VERMIN_NOTRAP
   - LOW_LIGHT_VISION ⊂ UNDERGROUND_DEPTH
   - LARGE_PREDATOR, BONECARN, MEANDERER, STANDARD_GRAZER, TRAINABLE and GRASSTRAMPLE ⊂ LARGE_ROAMING
9. **FLIER and the FLY gait match one-to-one for wild species (60 = 60).** Over all creatures, 8 flying extinct animal people keep FLIER without a FLY gait.
10. **CAN_LEARN is mostly EVIL on wild species.** 7 of the 10 wild CAN_LEARN species are EVIL: GNOME_DARK, BLIND_CAVE_OGRE, MANERA, TROLL, OGRE, BLIZZARD_MAN and NIGHTWING. This is the closest partner of EVIL (J 0.29).
11. **NO_WINTER (22 wild) has no cluster.** Its carriers are hibernators and insects: bears, groundhog, badger, bat, frogs, butterflies and others. Its best Jaccard is 0.14, so a season mask is independent of every other token.
