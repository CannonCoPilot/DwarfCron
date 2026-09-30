# Natural groupings of wildlife tokens (DF 53.16 vanilla raws)

Wildlife = vanilla (not extinct) creatures with a BIOME, excluding animal people, giants, civ races (CAN_SPEAK+CAN_LEARN), megabeasts/semi-megabeasts/titans/night creatures/demons/forgotten beasts. n=363; surface (any non-SUBTERRANEAN biome) n=308; underground-only n=55. Tokens are counted if present on any caste.

## Clean partitions (verified disjoint in wildlife)

- **LARGE_ROAMING vs VERMIN_***: disjoint. Every wildlife creature is exactly one of LARGE_ROAMING (248) or a vermin type (114), except 1 with neither.
- **LARGE_PREDATOR vs BENIGN**: disjoint (60 vs 163; 140 carry neither). AMBUSHPREDATOR (1, giant cave spider) sits inside LARGE_PREDATOR.
- **LARGE_PREDATOR vs vermin**: disjoint (no vermin is a LARGE_PREDATOR); no LARGE_PREDATOR is a STANDARD_GRAZER.
- **CARNIVORE vs BONECARN**: disjoint in every vanilla creature (BONECARN implies carnivory in DF, and the raws never write both). Neither overlaps STANDARD_GRAZER.
- **ALL_ACTIVE vs DIURNAL/NOCTURNAL/CREPUSCULAR**: disjoint. DIURNAL and NOCTURNAL never co-occur; CREPUSCULAR pairs with NOCTURNAL (15) or DIURNAL (1). MATUTINAL is absent from vanilla; VESPERTINE only on FIREFLY.
- **AQUATIC vs AMPHIBIOUS**: disjoint. AQUATIC almost always comes with IMMOBILE_LAND (80/83), NO_DRINK (82/83) and UNDERSWIM (79/83). SWIMS_LEARNED is disjoint from SWIMS_INNATE (apes, gnomes).
- **PET vs PET_EXOTIC**: disjoint.
- **Seasonal absence**: only NO_WINTER is common (22 wildlife: small mammals, insects, bears); NO_SUMMER is absent; NO_AUTUMN on 2, NO_SPRING on 1.

### Population type x role (wildlife) (n=363)

| | BENIGN | unmarked | LARGE_PREDATOR | total |
|---|---|---|---|---|
| LARGE_ROAMING | 141 | 47 | 60 | 248 |
| VERMIN(GROUNDER) | 16 | 44 | 0 | 60 |
| VERMIN(FISH) | 1 | 28 | 0 | 29 |
| VERMIN(SOIL) | 3 | 6 | 0 | 9 |
| VERMIN(EATER) | 1 | 6 | 0 | 7 |
| VERMIN(ROTTER) | 0 | 5 | 0 | 5 |
| VERMIN(SOIL_COLONY) | 0 | 4 | 0 | 4 |
| neither | 1 | 0 | 0 | 1 |

### Water habit x role (wildlife) (n=363)

| | BENIGN | unmarked | LARGE_PREDATOR | total |
|---|---|---|---|---|
| SWIMS_INNATE only | 101 | 57 | 32 | 190 |
| AQUATIC | 32 | 38 | 13 | 83 |
| no swim | 6 | 33 | 6 | 45 |
| AMPHIBIOUS | 10 | 12 | 6 | 28 |
| SWIMS_LEARNED | 14 | 0 | 3 | 17 |

### Diet token x role (wildlife) (n=363)

| | BENIGN | unmarked | LARGE_PREDATOR | total |
|---|---|---|---|---|
| unmarked | 117 | 101 | 26 | 244 |
| CARNIVORE | 2 | 29 | 15 | 46 |
| BONECARN | 14 | 8 | 19 | 41 |
| STANDARD_GRAZER | 30 | 2 | 0 | 32 |

### Activity x role (wildlife) (n=363)

| | BENIGN | unmarked | LARGE_PREDATOR | total |
|---|---|---|---|---|
| ALL_ACTIVE | 56 | 83 | 44 | 183 |
| DIURNAL | 79 | 34 | 8 | 121 |
| NOCTURNAL | 16 | 15 | 6 | 37 |
| NOCTURNAL+CREPUSCULAR | 10 | 3 | 2 | 15 |
| CREPUSCULAR | 1 | 4 | 0 | 5 |
| DIURNAL+CREPUSCULAR | 1 | 0 | 0 | 1 |
| VESPERTINE | 0 | 1 | 0 | 1 |

### Adult body size band x role (LARGE_ROAMING wildlife only) (n=248)

| | BENIGN | LARGE_PREDATOR | unmarked | total |
|---|---|---|---|---|
| 1k-30k | 60 | 5 | 30 | 95 |
| 30k-150k | 30 | 26 | 13 | 69 |
| 150k-1M | 23 | 22 | 2 | 47 |
| >=1M | 17 | 7 | 0 | 24 |
| <1k | 11 | 0 | 2 | 13 |

### Water habit x size band (LARGE_ROAMING wildlife) (n=248)

| | 1k-30k | 30k-150k | 150k-1M | >=1M | <1k | total |
|---|---|---|---|---|---|---|
| SWIMS_INNATE only | 67 | 39 | 25 | 9 | 13 | 153 |
| AQUATIC | 9 | 14 | 11 | 11 | 0 | 45 |
| AMPHIBIOUS | 5 | 5 | 7 | 3 | 0 | 20 |
| SWIMS_LEARNED | 10 | 6 | 1 | 0 | 0 | 17 |
| no swim | 4 | 5 | 3 | 1 | 0 | 13 |

### Climate family of BIOME tokens x role (surface wildlife) (n=308)

| | BENIGN | unmarked | LARGE_PREDATOR | total |
|---|---|---|---|---|
| tropical | 47 | 21 | 10 | 78 |
| broad(ANY_*/NOT_FREEZING/ALL_MAIN) | 18 | 37 | 5 | 60 |
| temperate | 27 | 31 | 0 | 58 |
| cold+temperate | 11 | 8 | 5 | 24 |
| temperate+tropical | 10 | 5 | 9 | 24 |
| cold | 12 | 1 | 3 | 16 |
| desert+tropical | 1 | 4 | 2 | 7 |
| desert | 3 | 2 | 1 | 6 |
| mountain | 6 | 0 | 0 | 6 |
| desert+temperate | 3 | 1 | 0 | 4 |
| cold+temperate+tropical | 2 | 1 | 0 | 3 |
| broad(ANY_*/NOT_FREEZING/ALL_MAIN)+desert | 2 | 1 | 0 | 3 |
| cold+desert+temperate | 2 | 0 | 0 | 2 |
| mountain+temperate | 1 | 1 | 0 | 2 |
| broad(ANY_*/NOT_FREEZING/ALL_MAIN)+desert+temperate+tropical | 2 | 0 | 0 | 2 |
| broad(ANY_*/NOT_FREEZING/ALL_MAIN)+temperate+tropical | 2 | 0 | 0 | 2 |
| cold+mountain | 1 | 0 | 1 | 2 |
| broad(ANY_*/NOT_FREEZING/ALL_MAIN)+cold+desert+mountain+temperate+tropical | 1 | 0 | 0 | 1 |
| broad(ANY_*/NOT_FREEZING/ALL_MAIN)+cold+desert+mountain+tropical | 0 | 1 | 0 | 1 |
| broad(ANY_*/NOT_FREEZING/ALL_MAIN)+cold+desert+mountain | 1 | 0 | 0 | 1 |
| desert+temperate+tropical | 0 | 1 | 0 | 1 |
| broad(ANY_*/NOT_FREEZING/ALL_MAIN)+underground | 0 | 1 | 0 | 1 |
| cold+desert+mountain+temperate | 0 | 1 | 0 | 1 |
| desert+mountain+temperate | 0 | 1 | 0 | 1 |
| broad(ANY_*/NOT_FREEZING/ALL_MAIN)+desert+mountain+temperate+tropical | 0 | 1 | 0 | 1 |
| broad(ANY_*/NOT_FREEZING/ALL_MAIN)+cold | 1 | 0 | 0 | 1 |
