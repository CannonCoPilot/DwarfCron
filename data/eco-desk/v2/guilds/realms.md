# Realms x DF biomes: correspondence, rosters by guild, gaps, fills, and DF-feature realm mappings

Realm membership is **external real-world knowledge** (realms2.py: Q9 table for vanilla, fossil locality for extinct, root animal for giants and animal people). DF places a species on any landmass whose BIOME it lists, around a random per-species epicenter (wiki FREQUENCY); it has no realms. The extinct creatures' period class "currently has no effect on how or where they appear" (wiki, Extinction). Scope below: the tool's natural class (894 creatures incl. giants, animal people, extinct). Guild codes: **A** apex (LARGE_PREDATOR land/water, plus the apex boost), **M** meso (ML/MW), **R** raptor, **G** grazer, **P** other land prey / land bird, **S** shore / semiaquatic, **W** fish (coastal, pelagic, fresh), **B** waterbird, **T** thief/scavenger tag (CURIOUSBEAST_* or Q2 text), **v** vermin (stock only).

## 1. Realm <-> DF biome itemization

Every DF biome token, its table group, whether each realm has that climate today (external), and how many natural non-vermin DF species of that realm list the token (vanilla / +extinct). "·" = the realm does not have that biome; "0" = the realm has it but DF gives it no species.

| DF biome token | group | AUS | NZ | AFR | MAD | NEO | NEA | PAL | IND | ARC | ANT | OCE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MOUNTAIN | mountain | 1 | 1 | 0 | 0 | 2 | 7 | 2 | 0 | 1 | · | · |
| GLACIER | polar land | · | 0 | · | · | 0 | 0 | 0 | 0 | 1 | 0 | · |
| TUNDRA | polar land | · | 0 | · | · | 1 | 9+1 | 6+2 | 0 | 7+2 | 0 | · |
| SWAMP_TEMPERATE_FRESHWATER | temperate wetland | 1 | 0 | (1) | · | 2 | 8+3 | 5+2 | (1) | (1) | · | · |
| SWAMP_TEMPERATE_SALTWATER | temperate wetland | 1 | 0 | (1) | · | 2 | 7 | 5 | (1) | (1) | · | · |
| MARSH_TEMPERATE_FRESHWATER | temperate wetland | 1 | 0 | (1+1) | · | 3 | 7+10 | 6+4 | (1) | (1) | · | · |
| MARSH_TEMPERATE_SALTWATER | temperate wetland | 1 | 0 | (1) | · | 3 | 6 | 6 | (1) | (1) | · | · |
| SWAMP_TROPICAL_FRESHWATER | tropical wetland | 2 | · | 5 | 0 | 4+1 | 4+1 | (4) | 6 | (0+1) | · | · |
| SWAMP_TROPICAL_SALTWATER | tropical wetland | 2 | · | 5 | 0 | 4 | 3 | (4) | 6 | · | · | · |
| SWAMP_MANGROVE | tropical wetland | 2 | · | 5 | 0 | 7 | 4 | (4) | 6 | · | · | · |
| MARSH_TROPICAL_FRESHWATER | tropical wetland | 2 | · | 3+2 | 0 | 4+1 | 3+1 | (3+1) | 5 | (0+1) | · | · |
| MARSH_TROPICAL_SALTWATER | tropical wetland | 2 | · | 3+2 | 0 | 4 | 2 | (3) | 5 | · | · | · |
| FOREST_TAIGA | taiga | (1) | · | · | · | (2) | 19 | 12 | (2) | 5 | · | · |
| FOREST_TEMPERATE_CONIFER | temperate forest | 4 | 3 | 0 | · | 5 | 20+1 | 10+3 | 3 | (2) | · | · |
| FOREST_TEMPERATE_BROADLEAF | temperate forest | 5+1 | 3+1 | 0 | · | 5+2 | 20+20 | 10+6 | 3 | (2) | · | · |
| FOREST_TROPICAL_CONIFER | tropical forest | 2 | · | 7 | 0 | 10 | (6) | (3) | 11 | · | · | · |
| FOREST_TROPICAL_DRY_BROADLEAF | tropical forest | 2+1 | · | 7+1 | 1+1 | 11 | (6) | (3+1) | 12 | · | · | · |
| FOREST_TROPICAL_MOIST_BROADLEAF | tropical forest | 4 | · | 13+1 | 1+1 | 13 | (6) | (3+4) | 23+1 | · | · | · |
| GRASSLAND_TEMPERATE | temperate grass/savanna/shrub | 3+2 | 1+1 | 1+2 | · | 4+4 | 12+6 | 11+5 | (3+2) | (2+2) | (0+1) | · |
| SAVANNA_TEMPERATE | temperate grass/savanna/shrub | 3 | 1 | 0+1 | · | 4+4 | 11+21 | 8+3 | (3) | (1) | · | · |
| SHRUBLAND_TEMPERATE | temperate grass/savanna/shrub | 5+2 | 3+1 | 0+2 | · | 4+8 | 14+18 | 8+5 | (3+2) | (2) | (0+1) | · |
| GRASSLAND_TROPICAL | tropical grass/savanna/shrub | 2 | · | 15+1 | 0 | 6 | (4) | (6+1) | 8+1 | · | · | · |
| SAVANNA_TROPICAL | tropical grass/savanna/shrub | 2 | · | 17+3 | 1 | 7 | (4) | (4+1) | 9+1 | · | · | · |
| SHRUBLAND_TROPICAL | tropical grass/savanna/shrub | 2 | · | 17+2 | 1 | 7+2 | (5) | (4+5) | 11 | · | · | · |
| DESERT_BADLAND | desert | 3 | · | 4+3 | · | 4+3 | 11+10 | 5+6 | 3+2 | (1) | (0+1) | · |
| DESERT_ROCK | desert | 3 | · | 4 | · | 4 | 11 | 5+4 | 3 | (1) | · | · |
| DESERT_SAND | desert | 3 | · | 4 | · | 4 | 11 | 5+2 | 3 | (1) | · | · |
| OCEAN_TROPICAL | ocean tropical | 1 | · | 0 | 0 | 0 | 1 | · | 1 | · | · | 28+9 |
| OCEAN_TEMPERATE | ocean temperate | 1 | 0 | 0 | · | 0 | 4 | 3 | (1) | · | · | 24+11 |
| OCEAN_ARCTIC | ocean arctic | (1) | (1) | · | · | · | 4 | 2 | (1) | 4 | 3 | 10+2 |
| POOL_TEMPERATE_FRESHWATER | pools (vermin only) | · | · | · | · | · | (3) | (1) | · | · | · | · |
| POOL_TEMPERATE_BRACKISHWATER | pools (vermin only) | · | · | · | · | · | (3) | (1) | · | · | · | · |
| POOL_TEMPERATE_SALTWATER | pools (vermin only) | · | · | · | · | · | (1) | (1) | · | · | · | (0+2) |
| POOL_TROPICAL_FRESHWATER | pools (vermin only) | · | · | · | · | · | (1) | (1) | · | · | · | · |
| POOL_TROPICAL_BRACKISHWATER | pools (vermin only) | · | · | · | · | · | (1) | (1) | · | · | · | · |
| POOL_TROPICAL_SALTWATER | pools (vermin only) | · | · | · | · | · | (1) | (1) | · | · | · | (0+2) |
| LAKE_TEMPERATE_FRESHWATER | lake/river temperate fresh | 0 | 0 | · | · | 0 | 10+2 | 8+4 | · | 0 | · | · |
| LAKE_TEMPERATE_BRACKISHWATER | lake/river temperate brackish/salt | 0 | · | · | · | · | 10 | 7+3 | · | · | · | · |
| LAKE_TEMPERATE_SALTWATER | lake/river temperate brackish/salt | 0 | · | · | · | · | 6 | 6 | · | · | · | · |
| LAKE_TROPICAL_FRESHWATER | lake/river tropical fresh | 0 | · | 2 | 0 | 0+1 | (1+1) | (2) | 0 | (0+1) | · | · |
| LAKE_TROPICAL_BRACKISHWATER | lake/river tropical brackish/salt | 0 | · | 1 | · | 0 | (1) | (1) | 0 | · | · | · |
| LAKE_TROPICAL_SALTWATER | lake/river tropical brackish/salt | 0 | · | 1 | · | 0 | (1) | (1) | 0 | · | · | · |
| RIVER_TEMPERATE_FRESHWATER | lake/river temperate fresh | 1 | 0 | · | · | 0 | 10+3 | 7+4 | · | 0 | · | · |
| RIVER_TEMPERATE_BRACKISHWATER | lake/river temperate brackish/salt | 1 | · | · | · | · | 10 | 6+3 | · | · | · | · |
| RIVER_TEMPERATE_SALTWATER | lake/river temperate brackish/salt | 1 | · | · | · | · | 5 | 5 | · | · | · | · |
| RIVER_TROPICAL_FRESHWATER | lake/river tropical fresh | 2 | · | 2 | 0 | 0+1 | (2+1) | (2) | 1 | (0+1) | · | · |
| RIVER_TROPICAL_BRACKISHWATER | lake/river tropical brackish/salt | 2 | · | 1+2 | · | 0 | (2) | (1) | 1 | · | · | · |
| RIVER_TROPICAL_SALTWATER | lake/river tropical brackish/salt | 2 | · | 1+2 | · | 0 | (1) | (1) | 1 | · | · | · |
| SUBTERRANEAN_WATER | subterranean | · | · | · | · | · | · | · | · | · | · | · |
| SUBTERRANEAN_CHASM | subterranean | · | · | · | · | · | · | · | · | · | · | · |
| SUBTERRANEAN_LAVA | subterranean | · | · | · | · | · | · | · | · | · | · | · |

"(n)" = DF has species of that realm on a biome the realm does not have today (DF places by biome only; e.g. a Nearctic species whose BIOME list is a broad ANY_ token).

## 2. Guild coverage per realm x biome group

Each cell: vanilla natural non-giant (DF-native, non-savage) coverage; then `+ext` = what same-realm extinct species that list the biome add; then `+gi` = what giants of this realm's own animals add (giants of COS roots, e.g. giant insects and raptors, exist in every realm on a savage embark and are not counted) (giants, animal people and extinct are all SAVAGE: savage embarks only). Gaps (bold) = a required guild missing where the realm has that climate. Required: land = A, M, G or P, R; ocean = A, W, S; fresh water = W (unit or vermin fish), S. COS species count in every realm and OCE species in every ocean cell (Q9).

| realm | polar land | taiga | temperate forest | temperate grass/savanna/shrub | temperate wetland | tropical forest | tropical grass/savanna/shrub | tropical wetland | desert | mountain | ocean arctic | ocean temperate | ocean tropical | lake/river temperate fresh | lake/river temperate brackish/salt | lake/river tropical fresh | lake/river tropical brackish/salt |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AUS | (R2 v1) | (A1 R2 v27 +gi A1) | A1 R3 G1 P3 v34 +ext A1 +gi A1 G1 P3 **gap M** | A1 R4 G3 P2 v32 +ext A2 +gi A1 G2 P3 **gap M** | A1 R5 B2 v30 +gi A1 S1 **gap M,G|P** | A1 M2 R3 P1 v33 +ext A1 +gi A3 P2 | A1 M1 R5 T1 v30 +gi A2 **gap G|P** | A2 R5 B1 v29 +gi A2 P1 **gap M,G|P** | A1 R4 G1 P1 T1 v31 +gi A1 G1 P2 **gap M** | R2 G1 v1 +gi G1 **gap A,M** | (A4 M1 R1 S2 W4 B1 v12 +ext A1 W1) | A8 M1 R1 S1 W15 B1 T1 v22 +ext A7 M1 W3 v3 | A11 M1 R1 S1 W18 B1 T1 v11 +ext A6 W3 v5 | R1 S1 B2 v14 +gi S2 | R1 S1 B2 v10 +gi S1 | A1 R1 S1 W2 B1 v7 +gi A1 S1 | A1 R1 S1 W2 B1 v5 +gi A1 S1 |
| NZ | R2 v1 **gap A,M,G|P** | (R2 v27) | R4 P2 T1 v34 +ext P1 +gi A1 P2 T1 **gap A,M** | R5 G1 P2 T1 v31 +ext P1 +gi A1 P2 T1 **gap A,M** | R5 B2 v29 **gap A,M,G|P** | (R3 v32) | (R5 T1 v30) | (R5 B1 v28) | (R4 T1 v30) | R3 T1 v1 +gi A1 T1 **gap A,M,G|P** | (A4 M1 R1 S2 W4 B1 v12 +ext A1 W1) | A8 M1 R1 S1 W14 B1 T1 v22 +ext A7 M1 W3 v3 | (A11 M1 R1 S1 W17 B1 T1 v11 +ext A6 W3 v5) | R1 B2 v13 **gap S** | (R1 B2 v10) | (R1 W2 B1 v6) | (R1 W2 B1 v4) |
| AFR | (R2 v1) | (R2 v27) | R3 v35 +gi P1 **gap A,M,G|P** | R4 G1 P1 v32 +ext A1 G1 P1 +gi P2 **gap A,M→M** | (R5 P1 B2 v29 +ext G1 +gi P1) | A1 M4 R3 G1 P7 T2 v34 +ext G1 P1 +gi A5 G1 P6 T2 | A4 M5 R5 G6 P6 T3 v31 +ext A1 G1 P1 +gi A9 G6 P5 T1 | A1 M2 R5 P2 B1 T1 v28 +ext A2 +gi A3 P1 T1 | A1 M1 R4 G1 P1 T2 v30 +ext A2 P1 +gi A2 G1 P1 T1 | R2 v1 **gap A,M,G|P** | (A4 M1 R1 S1 W4 B1 v12 +ext A1 W1) | A8 M1 R1 S1 W14 B1 T1 v22 +ext A7 M1 W3 v3 | A11 M1 R1 S1 W17 B1 T1 v11 +ext A6 W3 v5 | (R1 B2 v13) | (R1 B2 v10) | R1 S1 W3 B1 v7 +gi S1 | R1 S1 W2 B1 v5 +ext A2 +gi S1 |
| MAD | (R2 v1) | (R2 v27) | (R3 v34) | (R4 G1 v31) | (R5 B2 v29) | R3 P1 v32 +ext P1 +gi P1 **gap A,M** | R5 P1 T1 v30 +gi P1 **gap A,M** | R5 B1 v28 **gap A,M,G|P** | (R4 T1 v30) | R2 v1 **gap A,M,G|P** | (A4 M1 R1 S1 W4 B1 v12 +ext A1 W1) | (A8 M1 R1 S1 W14 B1 T1 v22 +ext A7 M1 W3 v3) | A11 M1 R1 S1 W17 B1 T1 v11 +ext A6 W3 v5 | (R1 B2 v13) | (R1 B2 v10) | R1 W2 B1 v6 **gap S** | (R1 W2 B1 v4) |
| NEO | R3 v1 +gi A1 **gap A,M,G|P** | (M1 R3 v27 +gi A2) | A1 M2 R4 P1 T1 v35 +ext A1 G1 +gi A4 P2 T1 | A1 M1 R6 G1 P1 T1 v31 +ext A3 M1 G1 P3 +gi A4 P1 T1 | M1 R6 G1 B2 T1 v29 +gi A2 G1 T1 **gap A** | A2 M5 R4 G1 P4 T2 v32 +gi A8 G1 P4 T2 | A2 M2 R6 G1 P2 T1 v30 +ext A1 M1 +gi A5 P2 | A2 M2 R6 G1 P1 B1 T1 v28 +ext M1 +gi A5 G1 P1 T1 | A1 M1 R6 T2 v30 +ext M1 P2 +gi A4 T1 **gap G|P→filled by ext** | R3 P1 v1 +gi A1 P1 **gap A,M** | (A4 M1 R1 S1 W4 B1 v12 +ext A1 W1) | A8 M1 R1 S1 W14 B1 T1 v22 +ext A7 M1 W3 v3 | A11 M1 R1 S1 W17 B1 T1 v11 +ext A6 W3 v5 | R1 B2 v13 **gap S** | (R1 B2 v10) | R1 W2 B1 v7 +ext M1 **gap S** | R1 W2 B1 v5 **gap S** |
| NEA | A1 M2 R3 G2 P3 T1 v1 +ext G1 +gi A4 G1 P3 | A3 M8 R3 G3 P4 T4 v27 +gi A12 G2 P4 T3 | A4 M7 R4 G2 P7 T4 v39 +ext A6 G3 P11 +gi A12 G2 P11 T3 | A2 M4 R6 G3 P6 T2 v34 +ext A9 R1 G6 P10 +gi A8 G2 P8 T1 | A1 M4 R6 P3 B3 T2 v31 +ext A1 M2 P7 v1 +gi A6 P3 S1 T1 | (A1 M2 R4 P2 v32 +gi A4 P2) | (A1 M1 R6 P2 T1 v30 +gi A3 P2) | A1 M2 R6 P1 B1 v28 +ext A1 +gi A4 P1 | M5 R6 P4 T3 v30 +ext A6 P4 +gi A7 P4 T1 **gap A→filled by ext** | M4 R3 G2 v1 +gi A5 G2 **gap A** | A5 M1 R1 S3 W5 B1 v12 +ext A1 W1 +gi S2 | A9 M2 R1 S2 W15 B1 T1 v22 +ext A7 M1 W3 v3 +gi S1 | A11 M1 R1 S2 W17 B1 T1 v11 +ext A6 W3 v5 +gi S1 | A2 M3 R1 S2 W3 B4 v14 +ext A1 M2 v1 +gi A3 S3 B1 | A2 M3 R1 S2 W3 B4 v10 +ext v1 +gi A3 S2 B1 | (A1 M1 R1 W2 B1 v6 +ext A1 +gi A2) | (A1 M1 R1 W2 B1 v4 +gi A2) |
| PAL | A1 M1 R2 G2 P2 T1 v1 +ext G2 +gi A2 G1 P2 | A1 M5 R2 G3 P3 T1 v27 +gi A6 G2 P3 | A1 M3 R3 G3 P3 T1 v34 +ext A1 M1 P4 v3 +gi A4 G3 P3 | A1 M2 R4 G5 P5 T2 v31 +ext A2 G5 P1 v2 +gi A3 G2 P5 T1 | M1 R5 P4 B3 T1 v29 +ext M1 G1 P3 v2 +gi A1 P4 **gap A** | (A1 R3 P2 v32 +ext R2 G1 P2 v3 +gi A1 P2) | (A1 M1 R5 G2 P3 T2 v30 +ext A1 M1 G1 P3 v2 +gi A2 G2 P3) | (A1 R5 P3 B1 v28 +ext P1 +gi A1 P3) | R4 G3 P2 T2 v30 +ext A3 M1 G1 P3 v2 +gi G3 P2 **gap A,M→filled by ext** | M1 R2 G1 v1 +gi A1 **gap A** | A5 M1 R1 S1 W5 B1 v12 +ext A1 W1 | A9 M2 R1 S1 W15 B1 T1 v22 +ext A7 M1 W3 v3 | (A11 M1 R1 S1 W17 B1 T1 v11 +ext A6 W3 v5) | A1 M1 R1 S2 W3 B4 v13 +ext A1 M1 W2 v3 +gi A1 S2 B1 | A1 M1 R1 S2 W2 B4 v10 +ext A1 W2 v1 +gi A1 S2 B1 | (M1 R1 W3 B1 v6 +gi A1) | (M1 R1 W2 B1 v4 +gi A1) |
| IND | R2 v1 **gap A,M,G|P** | (R2 P2 T1 v27 +gi P2 T1) | R3 G1 P2 T1 v34 +gi G1 P2 T1 **gap A,M** | (R4 G1 P3 T2 v31 +ext G1 P1 +gi P3 T2) | (R5 P1 B2 v29 +gi P1) | A2 M4 R3 G1 P16 T3 v33 +ext G1 +gi A6 G1 P6 T3 | A2 M4 R5 G2 P3 T4 v31 +ext G1 +gi A6 G2 P4 T2 | A3 M1 R5 G1 P1 B1 T1 v28 +gi A4 P1 T1 | A1 M1 R4 P1 T3 v30 +ext G1 P1 +gi A2 P1 T2 | R2 v1 **gap A,M,G|P** | (A4 M1 R1 S2 W4 B1 v12 +ext A1 W1 +gi S1) | (A8 M1 R1 S2 W14 B1 T1 v22 +ext A7 M1 W3 v3 +gi S1) | A11 M1 R1 S2 W17 B1 T1 v11 +ext A6 W3 v5 +gi S1 | (R1 B2 v13) | (R1 B2 v10) | A1 R1 W2 B1 v6 +gi A1 **gap S** | A1 R1 W2 B1 v4 +gi A1 **gap S** |
| ARC | A2 M1 R3 G2 P1 T2 v1 +ext G2 +gi A4 G1 P1 T1 | A1 M2 R2 G1 P1 T1 v27 +gi A3 P1 | (A1 R3 P1 T1 v34 +gi A1 P1) | (A1 R4 G2 P1 T1 v31 +ext G2 +gi A1 G1 P1) | (R5 P1 B2 T1 v29 +gi P1) | (R3 v32) | (R5 T1 v30) | (R5 B1 v28 +ext A1) | (R4 P1 T2 v30 +gi P1) | M1 R2 v1 +gi A1 **gap A,G|P** | A4 M1 R1 S3 W5 B2 v12 +ext A1 W1 +gi S2 W1 B1 | (A8 M1 R1 S1 W14 B1 T1 v22 +ext A7 M1 W3 v3) | (A11 M1 R1 S1 W17 B1 T1 v11 +ext A6 W3 v5) | R1 B2 v13 **gap S** | (R1 B2 v10) | (R1 W2 B1 v6 +ext A1) | (R1 W2 B1 v4) |
| ANT | R2 v1 **gap A,M,G|P** | (R2 v27) | (R3 v34) | (R4 G1 v31 +ext P1) | (R5 B2 v29) | (R3 v32) | (R5 T1 v30) | (R5 B1 v28) | (R4 T1 v30 +ext P1) | (R2 v1) | A4 M1 R1 S4 W4 B1 v12 +ext A1 W1 +gi S2 | (A8 M1 R1 S1 W14 B1 T1 v22 +ext A7 M1 W3 v3) | (A11 M1 R1 S1 W17 B1 T1 v11 +ext A6 W3 v5) | (R1 B2 v13) | (R1 B2 v10) | (R1 W2 B1 v6) | (R1 W2 B1 v4) |
| OCE | (R2 v1) | (R2 v27) | (R3 v34) | (R4 G1 v31) | (R5 B2 v29) | (R3 v32) | (R5 T1 v30) | (R5 B1 v28) | (R4 T1 v30) | (R2 v1) | A4 M1 R1 S1 W4 B1 v12 +ext A1 W1 +gi A4 W2 B1 | A8 M1 R1 S1 W14 B1 T1 v22 +ext A7 M1 W3 v3 +gi A4 W3 B1 | A11 M1 R1 S1 W17 B1 T1 v11 +ext A6 W3 v5 +gi A4 W2 B1 | (R1 B2 v13) | (R1 B2 v10 +ext v1) | (R1 W2 B1 v6) | (R1 W2 B1 v4) |

Full member lists per cell: `realm_biome.tsv`.

## 3. Gaps and proposed fills

Fill order: (1) same-realm extinct species whose raws list the biome (DF-native on a savage embark; no cross-biome write); (2) same-realm vanilla species from another biome (cross-biome import: the tool must write a population the raws do not admit; **untested**, Q9); (3) same-realm extinct from another biome; (4) cosmopolitan species with the biome; (5) an analog from another realm that lists the biome (DF-native, breaks the realm).

| realm | biome group | missing | extinct closes it | fills (in order) |
|---|---|---|---|---|
| AUS | temperate forest | M | no | same realm, other biome (cross-biome import): MONITOR_LIZARD, PYTHON ; other-realm analog, biome listed: ADDER, BADGER, BOBCAT, COATI, COPPERHEAD_SNAKE… |
| AUS | temperate grass/savanna/shrub | M | no | same realm, other biome (cross-biome import): MONITOR_LIZARD, PYTHON ; other-realm analog, biome listed: ADDER, BADGER, COYOTE, KINGSNAKE, RATTLESNAKE |
| AUS | temperate wetland | M | no | same realm, other biome (cross-biome import): MONITOR_LIZARD, PYTHON ; other-realm analog, biome listed: ADDER, BOBCAT, COPPERHEAD_SNAKE, COYOTE, RATTLESNAKE |
| AUS | temperate wetland | G|P | no | same realm, other biome (cross-biome import): BIRD_CASSOWARY, BIRD_EMU, ECHIDNA, KANGAROO, KOALA, WOMBAT ; other-realm analog, biome listed: BIRD_RAVEN, BIRD_STORK_WHITE, BIRD_TURKEY, CAPYBARA, WEASEL… |
| AUS | tropical grass/savanna/shrub | G|P | no | same realm, other biome (cross-biome import): BIRD_CASSOWARY, BIRD_EMU, ECHIDNA, KANGAROO, KOALA, WOMBAT ; other-realm analog, biome listed: AARDVARK, ARMADILLO, BIRD_OSTRICH, BIRD_STORK_WHITE, BONOBO… |
| AUS | tropical wetland | M | no | same realm, other biome (cross-biome import): MONITOR_LIZARD, PYTHON ; other-realm analog, biome listed: BLACK_MAMBA, BOBCAT, HONEY BADGER, OCELOT, RATTLESNAKE |
| AUS | tropical wetland | G|P | no | same realm, other biome (cross-biome import): BIRD_CASSOWARY, BIRD_EMU, ECHIDNA, KANGAROO, KOALA, WOMBAT ; other-realm analog, biome listed: BIRD_STORK_WHITE, CAPUCHIN, CAPYBARA, GORILLA, WATER_BUFFALO… |
| AUS | desert | M | no | same realm, other biome (cross-biome import): MONITOR_LIZARD, PYTHON ; other-realm analog, biome listed: BOBCAT, COYOTE, GILA_MONSTER, HONEY BADGER, KINGSNAKE… |
| AUS | mountain | A | no | same realm, other biome (cross-biome import): CROCODILE_SALTWATER, DINGO ; extinct same realm, other biome: CENOZOIC_MEGALANIA, CENOZOIC_THYLACINE |
| AUS | mountain | M | no | same realm, other biome (cross-biome import): MONITOR_LIZARD, PYTHON ; other-realm analog, biome listed: BOBCAT, COYOTE, KINGSNAKE, WOLVERINE |
| NZ | polar land | A | no | other-realm analog, biome listed: BEAR_POLAR, WOLF |
| NZ | polar land | M | no | other-realm analog, biome listed: COYOTE, STOAT |
| NZ | polar land | G|P | no | same realm, other biome (cross-biome import): BIRD_KAKAPO, BIRD_KIWI ; extinct same realm, other biome: CENOZOIC_MOA ; other-realm analog, biome listed: BIRD_RAVEN, ELK, MUSKOX, PORCUPINE, REINDEER… |
| NZ | temperate forest | A | no | other-realm analog, biome listed: BEAR_BLACK, BEAR_GRIZZLY, COUGAR, DINGO, WOLF |
| NZ | temperate forest | M | no | other-realm analog, biome listed: ADDER, BADGER, BOBCAT, COATI, COPPERHEAD_SNAKE… |
| NZ | temperate grass/savanna/shrub | A | no | other-realm analog, biome listed: COUGAR, DINGO, WOLF |
| NZ | temperate grass/savanna/shrub | M | no | other-realm analog, biome listed: ADDER, BADGER, COYOTE, KINGSNAKE, RATTLESNAKE |
| NZ | temperate wetland | A | no | other-realm analog, biome listed: ALLIGATOR, DINGO |
| NZ | temperate wetland | M | no | other-realm analog, biome listed: ADDER, BOBCAT, COPPERHEAD_SNAKE, COYOTE, RATTLESNAKE |
| NZ | temperate wetland | G|P | no | same realm, other biome (cross-biome import): BIRD_KAKAPO, BIRD_KIWI ; extinct same realm, other biome: CENOZOIC_MOA ; other-realm analog, biome listed: BIRD_RAVEN, BIRD_STORK_WHITE, BIRD_TURKEY, CAPYBARA, WEASEL… |
| NZ | mountain | A | no | none in DF (natural class) |
| NZ | mountain | M | no | other-realm analog, biome listed: BOBCAT, COYOTE, KINGSNAKE, WOLVERINE |
| NZ | mountain | G|P | no | same realm, other biome (cross-biome import): BIRD_KAKAPO, BIRD_KIWI ; extinct same realm, other biome: CENOZOIC_MOA ; other-realm analog, biome listed: CHINCHILLA, GOAT_MOUNTAIN, MARMOT_HOARY, WOMBAT, YAK |
| NZ | lake/river temperate fresh | S | no | other-realm analog, biome listed: BEAVER, MINK, PLATYPUS |
| AFR | temperate forest | A | no | same realm, other biome (cross-biome import): CHEETAH, HYENA, LEOPARD, LION ; extinct same realm, other biome: CRETACEOUS_SPINOSAURUS_AEGYPTIACUS, CRETACEOUS_SPINOSAURUS_MIRABILIS, JURASSIC_AFROVENATOR, PERMIAN_ANTEOSAURUS ; other-realm analog, biome listed: BEAR_BLACK, BEAR_GRIZZLY, COUGAR, DINGO, WOLF |
| AFR | temperate forest | M | no | same realm, other biome (cross-biome import): BLACK_MAMBA, HONEY BADGER, JACKAL, MONGOOSE, MONITOR_LIZARD, PYTHON ; other-realm analog, biome listed: ADDER, BADGER, BOBCAT, COATI, COPPERHEAD_SNAKE… |
| AFR | temperate forest | G|P | no | same realm, other biome (cross-biome import): AARDVARK, BIRD_HORNBILL, BIRD_OSTRICH, BIRD_PARROT_GREY, BIRD_STORK_WHITE, BONOBO ; extinct same realm, other biome: CENOZOIC_DEINOTHERIUM, CENOZOIC_PLATYBELODON, JURASSIC_KENTROSAURUS, PERMIAN_LYSTROSAURUS ; other-realm analog, biome listed: BIRD_EMU, BIRD_KAKAPO, BIRD_KIWI, BIRD_RAVEN, BIRD_TURKEY… |
| AFR | temperate grass/savanna/shrub | A | yes | extinct same realm, biome listed: PERMIAN_ANTEOSAURUS ; same realm, other biome (cross-biome import): CHEETAH, HYENA, LEOPARD, LION ; extinct same realm, other biome: CRETACEOUS_SPINOSAURUS_AEGYPTIACUS, CRETACEOUS_SPINOSAURUS_MIRABILIS, JURASSIC_AFROVENATOR ; other-realm analog, biome listed: COUGAR, DINGO, WOLF |
| AFR | temperate grass/savanna/shrub | M | no | same realm, other biome (cross-biome import): BLACK_MAMBA, HONEY BADGER, JACKAL, MONGOOSE, MONITOR_LIZARD, PYTHON ; other-realm analog, biome listed: ADDER, BADGER, COYOTE, KINGSNAKE, RATTLESNAKE |
| AFR | mountain | A | no | same realm, other biome (cross-biome import): CHEETAH, HYENA, LEOPARD, LION ; extinct same realm, other biome: CRETACEOUS_SPINOSAURUS_AEGYPTIACUS, CRETACEOUS_SPINOSAURUS_MIRABILIS, JURASSIC_AFROVENATOR, PERMIAN_ANTEOSAURUS |
| AFR | mountain | M | no | same realm, other biome (cross-biome import): BLACK_MAMBA, HONEY BADGER, JACKAL, MONGOOSE, MONITOR_LIZARD, PYTHON ; other-realm analog, biome listed: BOBCAT, COYOTE, KINGSNAKE, WOLVERINE |
| AFR | mountain | G|P | no | same realm, other biome (cross-biome import): AARDVARK, BIRD_HORNBILL, BIRD_OSTRICH, BIRD_PARROT_GREY, BIRD_STORK_WHITE, BONOBO ; extinct same realm, other biome: CENOZOIC_DEINOTHERIUM, CENOZOIC_PLATYBELODON, JURASSIC_KENTROSAURUS, PERMIAN_LYSTROSAURUS ; other-realm analog, biome listed: CHINCHILLA, GOAT_MOUNTAIN, MARMOT_HOARY, WOMBAT, YAK |
| MAD | tropical forest | A | no | other-realm analog, biome listed: COUGAR, DINGO, JAGUAR, LEOPARD, TIGER |
| MAD | tropical forest | M | no | other-realm analog, biome listed: BLACK_MAMBA, BOBCAT, BUSHMASTER, COATI, HONEY BADGER… |
| MAD | tropical grass/savanna/shrub | A | no | other-realm analog, biome listed: CHEETAH, COUGAR, DINGO, HYENA, JAGUAR… |
| MAD | tropical grass/savanna/shrub | M | no | other-realm analog, biome listed: BLACK_MAMBA, HONEY BADGER, JACKAL, MONGOOSE, MONITOR_LIZARD… |
| MAD | tropical wetland | A | no | other-realm analog, biome listed: ALLIGATOR, ANACONDA, CROCODILE_SALTWATER, DINGO, JAGUAR… |
| MAD | tropical wetland | M | no | other-realm analog, biome listed: BLACK_MAMBA, BOBCAT, HONEY BADGER, OCELOT, RATTLESNAKE |
| MAD | tropical wetland | G|P | no | same realm, other biome (cross-biome import): AYE-AYE, GIANT TORTOISE ; extinct same realm, other biome: CENOZOIC_DODO ; other-realm analog, biome listed: BIRD_STORK_WHITE, CAPUCHIN, CAPYBARA, GORILLA, WATER_BUFFALO… |
| MAD | mountain | A | no | none in DF (natural class) |
| MAD | mountain | M | no | other-realm analog, biome listed: BOBCAT, COYOTE, KINGSNAKE, WOLVERINE |
| MAD | mountain | G|P | no | same realm, other biome (cross-biome import): AYE-AYE, GIANT TORTOISE ; extinct same realm, other biome: CENOZOIC_DODO ; other-realm analog, biome listed: CHINCHILLA, GOAT_MOUNTAIN, MARMOT_HOARY, WOMBAT, YAK |
| MAD | lake/river tropical fresh | S | no | other-realm analog, biome listed: HIPPO, PLATYPUS |
| NEO | polar land | A | no | same realm, other biome (cross-biome import): ANACONDA, COUGAR, JAGUAR ; extinct same realm, other biome: CENOZOIC_KELENKEN, CENOZOIC_SMILODON, CRETACEOUS_CARNOTAURUS ; other-realm analog, biome listed: BEAR_POLAR, WOLF |
| NEO | polar land | M | no | same realm, other biome (cross-biome import): BUSHMASTER, COATI, IGUANA, OCELOT, RATTLESNAKE ; extinct same realm, other biome: CENOZOIC_TITANOBOA, CRETACEOUS_BUITRERAPTOR ; other-realm analog, biome listed: COYOTE, STOAT |
| NEO | polar land | G|P | no | same realm, other biome (cross-biome import): ARMADILLO, CAPUCHIN, CAPYBARA, CAVY, CHINCHILLA, GIANT TORTOISE ; extinct same realm, other biome: CENOZOIC_GLYPTODON, CENOZOIC_MEGATHERIUM, CRETACEOUS_AMARGASAURUS, TRIASSIC_EORAPTOR ; other-realm analog, biome listed: BIRD_RAVEN, ELK, MUSKOX, PORCUPINE, REINDEER… |
| NEO | temperate wetland | A | no | same realm, other biome (cross-biome import): ANACONDA, COUGAR, JAGUAR ; extinct same realm, other biome: CENOZOIC_KELENKEN, CENOZOIC_SMILODON, CRETACEOUS_CARNOTAURUS ; other-realm analog, biome listed: ALLIGATOR, DINGO |
| NEO | desert | G|P | yes | extinct same realm, biome listed: CRETACEOUS_AMARGASAURUS, TRIASSIC_EORAPTOR ; same realm, other biome (cross-biome import): ARMADILLO, CAPUCHIN, CAPYBARA, CAVY, CHINCHILLA, GIANT TORTOISE ; extinct same realm, other biome: CENOZOIC_GLYPTODON, CENOZOIC_MEGATHERIUM ; other-realm analog, biome listed: BIRD_OSTRICH, BIRD_RAVEN, CAMEL_1_HUMP, CAMEL_2_HUMP, DESERT TORTOISE… |
| NEO | mountain | A | no | same realm, other biome (cross-biome import): ANACONDA, COUGAR, JAGUAR ; extinct same realm, other biome: CENOZOIC_KELENKEN, CENOZOIC_SMILODON, CRETACEOUS_CARNOTAURUS |
| NEO | mountain | M | no | same realm, other biome (cross-biome import): BUSHMASTER, COATI, IGUANA, OCELOT, RATTLESNAKE ; extinct same realm, other biome: CENOZOIC_TITANOBOA, CRETACEOUS_BUITRERAPTOR ; other-realm analog, biome listed: BOBCAT, COYOTE, KINGSNAKE, WOLVERINE |
| NEO | lake/river temperate fresh | S | no | other-realm analog, biome listed: BEAVER, MINK, PLATYPUS |
| NEO | lake/river tropical fresh | S | no | other-realm analog, biome listed: HIPPO, PLATYPUS |
| NEO | lake/river tropical brackish/salt | S | no | other-realm analog, biome listed: HIPPO, PLATYPUS |
| NEA | desert | A | yes | extinct same realm, biome listed: CRETACEOUS_UTAHRAPTOR, JURASSIC_ALLOSAURUS, JURASSIC_CERATOSAURUS, JURASSIC_DILOPHOSAURUS, JURASSIC_TORVOSAURUS, PERMIAN_DIMETRODON ; same realm, other biome (cross-biome import): ALLIGATOR, BEAR_BLACK, BEAR_GRIZZLY, COUGAR, WOLF ; extinct same realm, other biome: CENOZOIC_SMILODON, CRETACEOUS_DEINONYCHUS, CRETACEOUS_TYRANNOSAURUS, DEVONIAN_TIKTAALIK ; other-realm analog, biome listed: DINGO, JAGUAR, LEOPARD |
| NEA | mountain | A | no | same realm, other biome (cross-biome import): ALLIGATOR, BEAR_BLACK, BEAR_GRIZZLY, COUGAR, WOLF ; extinct same realm, other biome: CENOZOIC_SMILODON, CRETACEOUS_DEINONYCHUS, CRETACEOUS_TYRANNOSAURUS, CRETACEOUS_UTAHRAPTOR, DEVONIAN_TIKTAALIK, JURASSIC_ALLOSAURUS |
| PAL | temperate wetland | A | no | same realm, other biome (cross-biome import): TIGER, WOLF ; extinct same realm, other biome: CENOZOIC_ANDREWSARCHUS, CRETACEOUS_VELOCIRAPTOR, JURASSIC_TORVOSAURUS, SILURIAN_JAEKELOPTERUS ; other-realm analog, biome listed: ALLIGATOR, DINGO |
| PAL | desert | A | yes | extinct same realm, biome listed: CENOZOIC_ANDREWSARCHUS, CRETACEOUS_VELOCIRAPTOR, JURASSIC_TORVOSAURUS ; same realm, other biome (cross-biome import): TIGER, WOLF ; extinct same realm, other biome: SILURIAN_JAEKELOPTERUS ; other-realm analog, biome listed: DINGO, JAGUAR, LEOPARD |
| PAL | desert | M | yes | extinct same realm, biome listed: CRETACEOUS_MONONYKUS ; same realm, other biome (cross-biome import): ADDER, BADGER, FOX, JACKAL, LYNX, STOAT ; extinct same realm, other biome: TRIASSIC_DREPANOSAURUS, TRIASSIC_GERROTHORAX ; other-realm analog, biome listed: BOBCAT, COYOTE, GILA_MONSTER, HONEY BADGER, KINGSNAKE… |
| PAL | mountain | A | no | same realm, other biome (cross-biome import): TIGER, WOLF ; extinct same realm, other biome: CENOZOIC_ANDREWSARCHUS, CRETACEOUS_VELOCIRAPTOR, JURASSIC_TORVOSAURUS, SILURIAN_JAEKELOPTERUS |
| IND | polar land | A | no | same realm, other biome (cross-biome import): CROCODILE_SALTWATER, LEOPARD, TIGER ; other-realm analog, biome listed: BEAR_POLAR, WOLF |
| IND | polar land | M | no | same realm, other biome (cross-biome import): HONEY BADGER, JACKAL, KING_COBRA, MONGOOSE, MONITOR_LIZARD, PYTHON ; other-realm analog, biome listed: COYOTE, STOAT |
| IND | polar land | G|P | no | same realm, other biome (cross-biome import): BEAR_SLOTH, BIRD_HORNBILL, BIRD_PEAFOWL_BLUE, ELEPHANT, GIBBON_BILOU, GIBBON_BLACK_CRESTED ; extinct same realm, other biome: CENOZOIC_DEINOTHERIUM, CENOZOIC_PARACERATHERIUM, PERMIAN_LYSTROSAURUS ; other-realm analog, biome listed: BIRD_RAVEN, ELK, MUSKOX, PORCUPINE, REINDEER… |
| IND | temperate forest | A | no | same realm, other biome (cross-biome import): CROCODILE_SALTWATER, LEOPARD, TIGER ; other-realm analog, biome listed: BEAR_BLACK, BEAR_GRIZZLY, COUGAR, DINGO, WOLF |
| IND | temperate forest | M | no | same realm, other biome (cross-biome import): HONEY BADGER, JACKAL, KING_COBRA, MONGOOSE, MONITOR_LIZARD, PYTHON ; other-realm analog, biome listed: ADDER, BADGER, BOBCAT, COATI, COPPERHEAD_SNAKE… |
| IND | mountain | A | no | same realm, other biome (cross-biome import): CROCODILE_SALTWATER, LEOPARD, TIGER |
| IND | mountain | M | no | same realm, other biome (cross-biome import): HONEY BADGER, JACKAL, KING_COBRA, MONGOOSE, MONITOR_LIZARD, PYTHON ; other-realm analog, biome listed: BOBCAT, COYOTE, KINGSNAKE, WOLVERINE |
| IND | mountain | G|P | no | same realm, other biome (cross-biome import): BEAR_SLOTH, BIRD_HORNBILL, BIRD_PEAFOWL_BLUE, ELEPHANT, GIBBON_BILOU, GIBBON_BLACK_CRESTED ; extinct same realm, other biome: CENOZOIC_DEINOTHERIUM, CENOZOIC_PARACERATHERIUM, PERMIAN_LYSTROSAURUS ; other-realm analog, biome listed: CHINCHILLA, GOAT_MOUNTAIN, MARMOT_HOARY, WOMBAT, YAK |
| IND | lake/river tropical fresh | S | no | other-realm analog, biome listed: HIPPO, PLATYPUS |
| IND | lake/river tropical brackish/salt | S | no | other-realm analog, biome listed: HIPPO, PLATYPUS |
| ARC | mountain | A | no | same realm, other biome (cross-biome import): BEAR_POLAR, WOLF ; extinct same realm, other biome: DEVONIAN_TIKTAALIK |
| ARC | mountain | G|P | no | same realm, other biome (cross-biome import): BIRD_RAVEN, MUSKOX, REINDEER ; extinct same realm, other biome: CENOZOIC_MAMMOTH_WOOLLY, CENOZOIC_RHINOCEROS_WOOLLY ; other-realm analog, biome listed: CHINCHILLA, GOAT_MOUNTAIN, MARMOT_HOARY, WOMBAT, YAK |
| ARC | lake/river temperate fresh | S | no | other-realm analog, biome listed: BEAVER, MINK, PLATYPUS |
| ANT | polar land | A | no | other-realm analog, biome listed: BEAR_POLAR, WOLF |
| ANT | polar land | M | no | other-realm analog, biome listed: COYOTE, STOAT |
| ANT | polar land | G|P | no | extinct same realm, other biome: PERMIAN_LYSTROSAURUS ; other-realm analog, biome listed: BIRD_RAVEN, ELK, MUSKOX, PORCUPINE, REINDEER… |

75 gaps over 96 realm x biome cells where the realm has the climate; same-realm extinct species close 5 of them.

## 4. Australasia: the large-land-predator gap

Vanilla AUS land predators (natural, non-giant): CROCODILE_SALTWATER (AW, 800k, LP, apex), PYTHON (ML, 200k, not LP), MONITOR_LIZARD (ML, 100k, not LP), DINGO (AL, 20k, LP, apex).

Extinct AUS predators: CENOZOIC_THYLACINE (AL, 19k, LP; BIOME FOREST_TEMPERATE_BROADLEAF,SHRUBLAND_TEMPERATE,GRASSLAND_TEMPERATE; SAVAGE=1), CENOZOIC_MEGALANIA (AL, 450k, LP; BIOME FOREST_TROPICAL_DRY_BROADLEAF,SHRUBLAND_TEMPERATE,GRASSLAND_TEMPERATE; SAVAGE=1).

Other extinct land apex that DF could place in AUS-climate biomes (breaks the realm): CRETACEOUS_SPINOSAURUS_AEGYPTIACUS 7.40M [AFR], CRETACEOUS_SPINOSAURUS_MIRABILIS 7.40M [AFR], CRETACEOUS_TYRANNOSAURUS 6.25M [NEA], JURASSIC_TORVOSAURUS 2.18M [NEA/PAL], JURASSIC_ALLOSAURUS 2.00M [NEA], CRETACEOUS_CARNOTAURUS 1.70M [NEO], JURASSIC_AFROVENATOR 0.95M [AFR], CENOZOIC_ANDREWSARCHUS 0.85M [PAL], JURASSIC_CERATOSAURUS 0.75M [NEA], PERMIAN_ANTEOSAURUS 0.60M [AFR], CRETACEOUS_UTAHRAPTOR 0.50M [NEA], CENOZOIC_MEGALANIA 0.45M [AUS], JURASSIC_DILOPHOSAURUS 0.40M [NEA], CENOZOIC_SMILODON 0.33M [NEO/NEA], PERMIAN_DIMETRODON 0.14M [NEA], CENOZOIC_KELENKEN 0.10M [NEO], CRETACEOUS_DEINONYCHUS 0.10M [NEA], DEVONIAN_TIKTAALIK 0.05M [NEA/ARC], CENOZOIC_THYLACINE 0.02M [AUS], CRETACEOUS_VELOCIRAPTOR 0.02M [PAL].

Reading: DINGO (20k, pack 3:12) is the only vanilla Australasian LP on land besides the saltwater crocodile (wetland/river). The extinct set supplies two genuinely Australian predators: CENOZOIC_THYLACINE (19k, LP, BONECARN; temperate forest/shrub/grass) and CENOZOIC_MEGALANIA (450k, LP, CARNIVORE; tropical dry forest, temperate shrub/grass). MEGALANIA is the large apex the realm lacks; with a pack-adjusted size preference it takes KANGAROO/EMU/WOMBAT/DIPROTODON-sized prey. Both are SAVAGE, so DF itself places them only in savage regions; a calm AUS embark would need the tool to add them (Add invasive admits them wherever their BIOME matches, SW:2541). Neither is boosted (450k < 1M, not giant): MEGALANIA is a native apex by LARGE_PREDATOR.

## 5. Realms from DF world features instead of geography

DF has three creature-side world features: SAVAGE ("only in savage biomes"), GOOD ("only in good biomes"), EVIL ("only in evil biomes"); SAVAGE cannot combine with GOOD/EVIL on a creature, but a region can be savage AND good ("joyous wilds") or savage AND evil ("terrifying"). FANCIFUL marks mythical creatures (worldgen/civ flavour; no spawn rule on the wiki). REAL_WORLD_EXTINCT and the period classes (CAMBRIAN ... CENOZOIC) are labels with no placement effect (wiki). Untagged species appear in every region, so a savage region = untagged + SAVAGE-tagged.

### 5a. What each mapping admits (all classes; the tool manages only the natural class)

| mapping | total | natural class | giants | animal people / sentient | extinct | mythic/other class | AUS-rooted share | largest single realm (share) |
|---|---|---|---|---|---|---|---|---|
| M0 calm/neutral (no SAVAGE/GOOD/EVIL tag) | 343 | 327 | 1 | 12 | 1 | 16 | 6% | NEA 21% |
| M1 SAVAGE-tagged only (what a savage region adds) | 570 | 567 | 178 | 285 | 199 | 3 | 6% | NEA 29% |
| M2 savage region (M0 + M1) | 913 | 894 | 179 | 297 | 200 | 19 | 6% | NEA 27% |
| M3 savage x GOOD (joyous wilds: M2 + GOOD) | 921 | 894 | 179 | 301 | 200 | 27 | 6% | NEA 27% |
| M4 savage x EVIL (terrifying: M2 + EVIL) | 936 | 894 | 179 | 306 | 200 | 42 | 6% | NEA 27% |
| M5 FANCIFUL | 16 | 0 | 0 | 8 | 0 | 16 | 0% | - 0% |
| M6a Paleozoic (CAMBRIAN..PERMIAN) | 50 | 50 | 0 | 25 | 50 | 0 | 0% | OCE 38% |
| M6b Mesozoic (TRIASSIC..CRETACEOUS) | 110 | 110 | 0 | 55 | 110 | 0 | 0% | NEA 39% |
| M6c Cenozoic | 40 | 40 | 0 | 20 | 40 | 0 | 10% | PAL 35% |
| M7 SAVAGE natural non-sentient (M1 minus animal people/civ races) | 283 | 283 | 178 | 0 | 99 | 0 | 6% | NEA 30% |

M1 non-giant, non-person vanilla members: FLY_ACORN, FOXSQUIRREL, LIZARD_RHINO_TWO_LEGGED, MOGHOPPER, SASQUATCH, SEA_SERPENT, SPIDER_CAVE_GIANT, YETI. Every other M1 member is a giant, an animal person or extinct.

GOOD: FAIRY, GNOME_MOUNTAIN, GORLAK, MERPERSON, PIXIE, SATYR, UNICORN, WAMBLER_FLUFFY (classes: mythic 8). EVIL: BEAK_DOG, BLENDEC_FOUL, BLIND_CAVE_OGRE, BLIZZARD_MAN, BLOOD_MAN, CAVE_DRAGON, CREEPING_EYE, CREEPY_CRAWLER, GNAT_BLOOD, GNOME_DARK, GRIMELING, HARPY, MANERA, NIGHTWING, OGRE, RAT_DEMON, REACHER, SEA_MONSTER, SPIDER_PHANTOM, STRANGLER, TROLL, WOLF_ICE, WORM_KNUCKLE (classes: mythic 20, unliving 3). FANCIFUL: BIRD_ROC, COLOSSUS_BRONZE, CYCLOPS, DRAGON, ETTIN, FAIRY, GIANT, HARPY, HYDRA, MERPERSON, MINOTAUR, NIGHTWING, PIXIE, SASQUATCH, SATYR, YETI (natural: 0).

### 5b. Guild coverage per biome group (natural class of each mapping; non-vermin)

| mapping | polar land | taiga | temperate forest | temperate grass/savanna/shrub | temperate wetland | tropical forest | tropical grass/savanna/shrub | tropical wetland | desert | mountain | ocean arctic | ocean temperate | ocean tropical | lake/river temperate fresh | lake/river temperate brackish/salt | lake/river tropical fresh | lake/river tropical brackish/salt |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| M0 | A2 M2 R4 G3 P3 T2 | A4 M8 R3 G3 P6 T5 v26 | A5 M9 R5 G5 P14 T7 v38 | A4 M5 R7 G9 P14 T5 v35 | A2 M5 R6 G1 P5 B3 T2 v30 | A5 M11 R4 G2 P28 T6 v34 | A9 M7 R6 G8 P11 T4 v30 | A7 M5 R6 G2 P5 B1 T2 v28 | A3 M6 R6 G4 P7 T5 v30 | M4 R4 G4 P1 T1 **gap A** | A5 M1 R1 S9 W6 B2 v12 | A9 M2 R1 S2 W16 B1 T1 v22 | A11 M1 R1 S2 W18 B1 T1 v11 | A2 M3 R1 S3 W4 B4 v14 | A2 M3 R1 S3 W3 B4 v10 | A2 M1 R1 S2 W4 B1 v7 | A2 M1 R1 S2 W2 B1 v5 |
| M1 | A10 M2 R4 G8 P6 T2 v1 | A21 M10 R3 G4 P45 B4 T8 v1 | A42 M16 R6 G18 P109 B5 T12 v5 | A50 M11 R10 G34 P107 B4 T8 v3 | A20 M15 R6 G4 P63 S2 B7 T2 v3 | A33 M17 R11 G6 P77 B4 T12 v4 | A39 M17 R7 G16 P61 B4 T6 v3 | A34 M10 R6 G2 P45 B4 T4 v1 | A44 M18 R6 G10 P68 B4 T8 v3 | A8 M4 R4 G6 P2 T2 v1 | A9 M1 R1 S14 W10 B4 | A21 M4 R1 S4 W16 B2 v3 | A19 M5 R1 S4 W13 B2 v5 | A10 M10 R1 S12 W5 B13 v3 | A8 M3 R1 S10 W6 B12 v2 | A9 M4 R1 S10 B8 **gap W** | A11 M2 R1 S10 B8 **gap W** |
| M7 | A8 G4 P3 T1 v1 **gap M,R** | A17 G2 P21 B2 T4 v1 **gap M,R** | A30 M1 G9 P53 B2 T6 v5 **gap R** | A32 M1 R1 G17 P52 B2 T4 v3 | A17 M3 G2 P30 S1 B3 T1 v3 **gap R** | A27 R2 G3 P37 B2 T6 v4 **gap M** | A28 M2 G8 P29 B2 T3 v3 **gap R** | A24 M1 G1 P21 B2 T2 v1 **gap R** | A31 M2 G5 P33 B2 T4 v3 **gap R** | A8 G3 P1 T1 v1 **gap M,R** | A7 S7 W4 B2 | A13 M1 S2 W6 B1 v3 | A12 S2 W5 B1 v5 | A7 M3 S6 W2 B6 v3 | A6 S5 W2 B6 v2 | A6 M1 S5 B4 **gap W** | A7 S5 B4 **gap W** |
| M6a | — **gap A,M,G|P,R** | — **gap A,M,G|P,R** | G2 P2 B1 v1 **gap A,M,R** | A4 G2 P2 **gap M,R** | M5 P2 B1 v2 **gap A,R** | — **gap A,M,G|P,R** | — **gap A,M,G|P,R** | A2 **gap M,G|P,R** | A4 P2 **gap M,R** | — **gap A,M,G|P,R** | — **gap A,W,S** | A4 W6 v2 **gap S** | A4 M4 W5 v5 **gap S** | A4 M5 W5 B1 v3 **gap S** | A2 W6 v2 **gap S** | A2 **gap W,S** | — **gap W,S** |
| M6b | — **gap A,M,G|P,R** | — **gap A,M,G|P,R** | A10 M3 R1 P26 v2 | A16 M3 R3 P26 v2 | A2 M2 P16 **gap R** | R7 P6 v3 **gap A,M** | A6 M5 R1 P8 v2 | A4 P2 **gap M,R** | A14 M6 P18 v2 **gap R** | — **gap A,M,G|P,R** | A2 W2 **gap S** | A8 M3 W2 v1 **gap S** | A6 W2 **gap S** | M2 **gap W,S** | — **gap W,S** | — **gap W,S** | A4 **gap W,S** |
| M6c | G4 **gap A,M,R** | — **gap A,M,G|P,R** | A4 G6 P2 **gap M,R** | A10 G18 P4 **gap M,R** | G2 **gap A,M,R** | A2 G2 P2 **gap M,R** | G2 **gap A,M,R** | M2 **gap A,G|P,R** | A2 G2 **gap M,R** | — **gap A,M,G|P,R** | — **gap A,W,S** | A2 **gap W,S** | A2 **gap W,S** | — **gap W,S** | — **gap W,S** | M2 **gap W,S** | — **gap W,S** |

### 5c. Rosters built under each mapping (roster2, v1 embarks, land + flying + ocean, 4 seasons x 10 seeds)

Coherence = the web closes (apex present, no isolated node, pack AND herd on DF-actable edges) and is not dominated by sentients or giants. `savage=True` so SAVAGE species are admissible; the mapping is then the whitelist.

| mapping | non-empty rosters | mean size | apex present (all layers) | land rosters with apex | isolated | pack AND herd (actable) | sentient share | giant share | extinct share |
|---|---|---|---|---|---|---|---|---|---|
| M0 calm/neutral (no SAVAGE/GOOD/EVIL tag) | 600 | 9.5 | 53% | 100% of 280 | 0% | 50% | 0% | 0% | 1% |
| M1 SAVAGE-tagged only (what a savage region adds) | 600 | 8.0 | 100% | 100% of 280 | 0% | 21% | 12% | 48% | 33% |
| M7 SAVAGE natural non-sentient (M1 minus animal people/civ races) | 600 | 7.1 | 100% | 100% of 280 | 0% | 21% | 0% | 55% | 37% |
| M6a Paleozoic (CAMBRIAN..PERMIAN) | 120 | 5.0 | 100% | 100% of 80 | 0% | 0% | 20% | 0% | 100% |
| M6b Mesozoic (TRIASSIC..CRETACEOUS) | 280 | 7.1 | 100% | 100% of 240 | 0% | 28% | 14% | 0% | 100% |
| M6c Cenozoic | 120 | 6.6 | 100% | 100% of 120 | 0% | 0% | 15% | 0% | 100% |
| M2 savage region (M0 + M1) | 600 | 11.6 | 100% | 100% of 280 | 0% | 33% | 9% | 24% | 10% |
| realm AUS, calm embark (DF-native, no SAVAGE species) | 520 | 5.5 | 46% | 100% of 200 | 0% | 31% | 0% | 0% | 0% |
| realm AUS, calm + same-realm extinct added by the tool (the fills) | 520 | 5.8 | 46% | 100% of 200 | 0% | 15% | 0% | 0% | 9% |
| realm AUS, savage embark (+ own giants, animal people, extinct) | 600 | 10.0 | 100% | 100% of 280 | 0% | 5% | 10% | 34% | 3% |
| realm NZ, calm embark (DF-native, no SAVAGE species) | 320 | 6.0 | 12% | - | 0% | 7% | 0% | 0% | 0% |
| realm NZ, calm + same-realm extinct added by the tool (the fills) | 320 | 6.1 | 12% | - | 0% | 6% | 0% | 0% | 4% |
| realm NZ, savage embark (+ own giants, animal people, extinct) | 600 | 9.8 | 100% | 100% of 280 | 0% | 10% | 10% | 37% | 3% |
| realm AFR, calm embark (DF-native, no SAVAGE species) | 440 | 7.1 | 36% | 100% of 120 | 0% | 7% | 0% | 0% | 0% |
| realm AFR, calm + same-realm extinct added by the tool (the fills) | 480 | 7.1 | 42% | 100% of 160 | 0% | 5% | 0% | 0% | 11% |
| realm AFR, savage embark (+ own giants, animal people, extinct) | 600 | 10.4 | 100% | 100% of 280 | 0% | 5% | 9% | 32% | 6% |
| realm MAD, calm embark (DF-native, no SAVAGE species) | 320 | 6.0 | 12% | - | 0% | 1% | 0% | 0% | 0% |
| realm MAD, calm + same-realm extinct added by the tool (the fills) | 320 | 6.0 | 12% | - | 0% | 1% | 0% | 0% | 4% |
| realm MAD, savage embark (+ own giants, animal people, extinct) | 600 | 9.8 | 100% | 100% of 280 | 0% | 4% | 10% | 37% | 1% |
| realm NEO, calm embark (DF-native, no SAVAGE species) | 600 | 7.0 | 47% | 86% of 280 | 0% | 2% | 0% | 0% | 2% |
| realm NEO, calm + same-realm extinct added by the tool (the fills) | 600 | 7.5 | 47% | 86% of 280 | 0% | 2% | 0% | 0% | 13% |
| realm NEO, savage embark (+ own giants, animal people, extinct) | 600 | 11.0 | 100% | 100% of 280 | 0% | 9% | 9% | 32% | 7% |
| realm NEA, calm embark (DF-native, no SAVAGE species) | 600 | 8.4 | 47% | 86% of 280 | 0% | 33% | 0% | 0% | 0% |
| realm NEA, calm + same-realm extinct added by the tool (the fills) | 600 | 8.6 | 53% | 100% of 280 | 0% | 26% | 0% | 0% | 15% |
| realm NEA, savage embark (+ own giants, animal people, extinct) | 600 | 10.9 | 100% | 100% of 280 | 0% | 24% | 9% | 27% | 8% |
| realm PAL, calm embark (DF-native, no SAVAGE species) | 560 | 8.0 | 50% | 100% of 240 | 0% | 39% | 0% | 0% | 0% |
| realm PAL, calm + same-realm extinct added by the tool (the fills) | 600 | 8.6 | 53% | 100% of 280 | 0% | 34% | 0% | 0% | 18% |
| realm PAL, savage embark (+ own giants, animal people, extinct) | 600 | 11.0 | 100% | 100% of 280 | 0% | 20% | 9% | 26% | 9% |
| realm IND, calm embark (DF-native, no SAVAGE species) | 440 | 6.8 | 36% | 100% of 120 | 0% | 8% | 0% | 0% | 0% |
| realm IND, calm + same-realm extinct added by the tool (the fills) | 440 | 6.9 | 36% | 100% of 120 | 0% | 8% | 0% | 0% | 4% |
| realm IND, savage embark (+ own giants, animal people, extinct) | 600 | 10.2 | 100% | 100% of 280 | 0% | 5% | 10% | 34% | 3% |
| realm ARC, calm embark (DF-native, no SAVAGE species) | 480 | 6.0 | 42% | 100% of 160 | 0% | 38% | 0% | 0% | 0% |
| realm ARC, calm + same-realm extinct added by the tool (the fills) | 480 | 6.0 | 42% | 100% of 160 | 0% | 38% | 0% | 0% | 2% |
| realm ARC, savage embark (+ own giants, animal people, extinct) | 600 | 10.0 | 100% | 100% of 280 | 0% | 8% | 10% | 33% | 3% |
| realm ANT, calm embark (DF-native, no SAVAGE species) | 320 | 6.0 | 12% | - | 0% | 1% | 0% | 0% | 0% |
| realm ANT, calm + same-realm extinct added by the tool (the fills) | 320 | 6.0 | 12% | - | 0% | 1% | 0% | 0% | 4% |
| realm ANT, savage embark (+ own giants, animal people, extinct) | 600 | 9.8 | 100% | 100% of 280 | 0% | 4% | 10% | 36% | 5% |

