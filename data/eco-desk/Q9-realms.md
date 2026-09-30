# Q9: a curated realm table as candidate tool data (desk)

> **The realm assignments below are EXTERNAL real-world knowledge (native ranges), not DF data.** The DF raws carry no
> geography: no continent, realm or range token exists (census e). DF places a species on any landmass whose biome
> it lists, around a random per-species epicenter (wiki, FREQUENCY). The table is proposed tool data, to be edited by users.
> Data file: `eco/w/realms.py` (`REALM[token] = [realms]`); tables from `eco/w/q9.py`.

## What DF has

**Polar**
- No Antarctic exists. OCEAN_ARCTIC is DF's only cold ocean.
- BIRD_PENGUIN, BIRD_PENGUIN_EMPEROR, LEOPARD_SEAL and ELEPHANT_SEAL (real Antarctic or southern species) are all OCEAN_ARCTIC.
- They share that biome with WALRUS, HARP_SEAL, NARWHAL and BIRD_PUFFIN.
- BEAR_POLAR is GLACIER+TUNDRA, next to them.
- So in DF, penguins and polar bears co-occur. Only a table can separate an Arctic from an "Antarctic".

**The tool's existing geography hook**
- `MARSUPIAL_TOKENS` (SW:821) is a curated clade set. Many of its names do not exist in vanilla: WALLABY, QUOKKA, THYLACINE, TASMANIAN_DEVIL…
- `fillCategory` ranks marsupials first on a "marsupial embark" (SW:1687).
- A clade is not a realm. OPOSSUM is in the set but is Nearctic/Neotropical. The dingo (a placental) is Australasian and not in it.

**Add invasive (`addNewSpecies`, SW:2515)**
- It inserts a population only into embark regions **whose biome the raws already admit**. Other regions are skipped with `:biome` (SW:2539-2574).
- It writes `feature_idx = -1`, so every added species is a surface entry.

## Realm membership (surface wildlife, n=308; cavern-only 55 = no real-world realm)

Multi-realm natives are listed in each realm. 244 species have one realm, 54 have two, 10 have three.

Counts per realm:

| realm | total | non-vermin | vermin |
|---|---|---|---|
| Australasia (AUS) | 17 | 13 | 4 |
| New Zealand (NZ) | 4 | 4 | 0 |
| Africa (AFR) | 35 | 29 | 6 |
| Madagascar (MAD) | 3 | 2 | 1 |
| Neotropics (NEO) | 27 | 20 | 7 |
| Nearctic (NEA) | 75 | 48 | 27 |
| Palearctic (PAL) | 48 | 36 | 12 |
| Indomalaya (IND) | 33 | 31 | 2 |
| Arctic (ARC) | 13 | 12 | 1 |
| Antarctic / southern (ANT) | 4 | 4 | 0 |
| Oceanic / pelagic (OCE) | 55 | 36 | 19 |
| Cosmopolitan (COS) | 44 | 10 | 34 |
| Fantasy / DF-invented (FANT) | 24 | 14 | 10 |

Non-vermin members:

| realm | non-vermin members |
|---|---|
| AUS | KANGAROO, KOALA, WOMBAT, ECHIDNA, PLATYPUS, DINGO, BIRD_EMU, BIRD_CASSOWARY, BIRD_PENGUIN_LITTLE, CROCODILE_SALTWATER, MONITOR_LIZARD, PYTHON, SHARK_WOBBEGONG_SPOTTED |
| NZ | BIRD_KIWI, BIRD_KAKAPO, BIRD_KEA, BIRD_PENGUIN_LITTLE |
| AFR | LION, LEOPARD, CHEETAH, HYENA, JACKAL, HONEY BADGER, MONGOOSE, BLACK_MAMBA, PYTHON, MONITOR_LIZARD, ELEPHANT, RHINOCEROS, HIPPO, GIRAFFE, WARTHOG, IMPALA, GAZELLE, AARDVARK, PANGOLIN, CAMEL_1_HUMP, CHIMPANZEE, BONOBO, GORILLA, MANDRILL, BIRD_OSTRICH, BIRD_PARROT_GREY, BIRD_HORNBILL, BIRD_STORK_WHITE, FISH_TIGERFISH |
| MAD | AYE-AYE, GIANT TORTOISE (with NEO: Galápagos / Aldabra) |
| NEO | JAGUAR, COUGAR, OCELOT, ANACONDA, BUSHMASTER, RATTLESNAKE, COATI, CAPYBARA, TAPIR, SLOTH, ARMADILLO, OPOSSUM, CAVY, CHINCHILLA, CAPUCHIN, SPIDER_MONKEY, IGUANA, GIANT TORTOISE, BIRD_BUZZARD (turkey vulture), BIRD_OWL_GREAT_HORNED |
| NEA | WOLF, COUGAR, BEAR_GRIZZLY, BEAR_BLACK, COYOTE, BOBCAT, LYNX, FOX, BADGER, WOLVERINE, WEASEL, STOAT, MINK, RIVER OTTER, SEA OTTER, RACCOON, SKUNK, OPOSSUM, PORCUPINE, BEAVER, GROUNDHOG, MARMOT_HOARY, ARMADILLO, DEER, ELK, MOOSE, REINDEER, GOAT_MOUNTAIN, ALLIGATOR, SNAPPING TURTLE, ALLIGATOR SNAPPING TURTLE, GILA_MONSTER, DESERT TORTOISE, RATTLESNAKE, COPPERHEAD_SNAKE, KINGSNAKE, BIRD_TURKEY, BIRD_GOOSE, BIRD_LOON, BIRD_RAVEN, BIRD_BUZZARD, BIRD_OWL_GREAT_HORNED, FISH_PIKE, FISH_GAR_LONGNOSE, FISH_STURGEON, FISH_LAMPREY_SEA, HORSESHOE_CRAB, ELEPHANT_SEAL |
| PAL | WOLF, TIGER, LYNX, FOX, BADGER, WOLVERINE, WEASEL, STOAT, MINK, RIVER OTTER, SEA OTTER, BEAVER, JACKAL, WILD_BOAR, DEER, ELK, MOOSE, REINDEER, IBEX, YAK, HORSE, CAMEL_1_HUMP, CAMEL_2_HUMP, GAZELLE, RABBIT, PANDA, MACAQUE_RHESUS, ADDER, BIRD_GOOSE, BIRD_LOON, BIRD_RAVEN, BIRD_STORK_WHITE, FISH_CARP, FISH_PIKE, FISH_STURGEON, FISH_LAMPREY_SEA |
| IND | TIGER, LEOPARD, CROCODILE_SALTWATER, KING_COBRA, PYTHON, MONITOR_LIZARD, HONEY BADGER, MONGOOSE, JACKAL, BEAR_SLOTH, RED PANDA, ELEPHANT, RHINOCEROS, WATER_BUFFALO, WILD_BOAR, PANGOLIN, ORANGUTAN, the 9 gibbons, GRAY_LANGUR, MACAQUE_RHESUS, BIRD_PEAFOWL_BLUE, BIRD_HORNBILL, HORSESHOE_CRAB |
| ARC | BEAR_POLAR, WOLF, WOLVERINE, STOAT, MUSKOX, REINDEER, WALRUS, HARP_SEAL, NARWHAL, BIRD_OWL_SNOWY, BIRD_PUFFIN, BIRD_RAVEN |
| ANT | BIRD_PENGUIN, BIRD_PENGUIN_EMPEROR, LEOPARD_SEAL, ELEPHANT_SEAL (with NEA). All are OCEAN_ARCTIC in DF. There is no Antarctic land fauna. |
| OCE | the 17 sharks except the wobbegong (9 LP), 19 big ocean fish / rays, ORCA, SPERM_WHALE, OCTOPUS, BIRD_ALBATROSS, SPONGE |
| COS | BIRD_EAGLE, BIRD_FALCON_PEREGRINE, BIRD_KESTREL, BIRD_OSPREY, BIRD_OWL_BARN, BIRD_VULTURE (DF text is generic), BIRD_DUCK, BIRD_SWAN, CRAB, HARE |
| FANT | OGRE, UNICORN, YETI, SASQUATCH, BLIZZARD_MAN, WOLF_ICE, BEAK_DOG, GRIMELING, STRANGLER, NIGHTWING, SEA_SERPENT, SEA_MONSTER, GNOME_MOUNTAIN, GNOME_DARK |

Vermin:
- **COS:** 34 vermin (insects, worm, rat, bat, toad, generic small birds, lizard/skink, mussel/oyster).
- **Realm-specific:** NEA 27 (e.g. bluejay, cardinal, grackle, the three bullheads, the chipmunk and squirrels); OCE 19 (reef and schooling fish, squid, nautilus); PAL 12; NEO 7; AFR 6; AUS 4 (cockatiel, lorikeet, green tree frog, lungfish).
- **FANT:** 10 (rat demon, fluffy wambler, acorn fly and others).

**Unassignable or judgement calls**
- The generic DF names (DEER, FOX, BADGER, BIRD_EAGLE, SPARROW, BIRD_CROW) were given the realms their DF description best fits, or COS when the name is a whole genus or family.
- BIRD_VULTURE ("featherless red head … tropical deserts") and BIRD_BUZZARD ("red-faced black bird … temperate lands") both read like the turkey vulture. BUZZARD was set NEA/NEO and VULTURE COS.
- FISH_LUNGFISH is AFR/AUS/NEO; GREEN_TREE_FROG is NEA/AUS.

## Per realm × DF biome group

Scope: natural, non-vermin, surface. Codes: **A**n = LARGE_PREDATOR species (the tool's only armable set), **p**n = other predators by diet (never armed), **y**n = prey; — = none. A species counts in each biome group its BIOME tokens reach.

| realm | polar land | taiga | temperate forest | temperate grass/sav/shrub | temperate wetland | tropical forest | tropical grass/sav/shrub | tropical wetland | desert | mountain | ocean | fresh/brackish |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AUS | — | A1 | A1y4 | **A1y4** | A1 | A1p2y1 | A1p1 | A2 | A1y2 | y1 | y2 | A1y1 |
| NZ | — | — | p1y2 | p1y2 | — | — | — | — | — | p1 | y1 | — |
| AFR | — | — | — | y1 | y1 | A1p4y8 | A4p5y12 | A1p2y2 | A1p1y2 | — | — | y2 |
| MAD | — | — | — | — | — | y1 | y1 | — | — | — | — | — |
| NEO | p1 | p1 | A1p3y1 | A1p3y1 | p2y1 | A2p6y5 | A2p3y3 | A2p3y2 | A1p3 | p1y1 | — | — |
| NEA | A1p3y5 | A3p7y7 | A4p8y9 | A2p6y8 | A1p5y4 | A1p3y2 | A1p2y2 | A1p3y1 | p7y4 | p5y2 | A1p1y3 | A2p3y7 |
| PAL | A1p1y4 | A1p5y5 | A1p3y6 | A1p2y9 | p1y5 | A1y2 | A1p1y5 | A1y3 | y5 | p1y1 | A1p1y1 | A1p1y7 |
| IND | — | — | y3 | y3 | y1 | A2p4y17 | A2p4y5 | A3p1y2 | A1p1y1 | — | y1 | A1 |
| ARC | A2p2y3 | A1p2y2 | A1y1 | A1y2 | y1 | — | — | — | y1 | p1 | y4 | — |
| ANT | — | — | — | — | — | — | — | — | — | — | y4 | — |
| OCE | — | — | — | — | — | — | — | — | — | — | A9p3y23 | y2 |
| all DF (natural) | A2p6y6 | A4p8y7 | A5p14y19 | A3p12y23 | A2p11y9 | A5p15y30 | A8p13y19 | A7p11y8 | A3p12y11 | p8y5 | A11p5y36 | A3p4y15 |

Adding COS to a realm adds only non-armable predators (the 6 raptors) and a few prey (duck, swan, hare, crab). It fills no **A** gap. For example, AUS+COS on polar land = p2, and NZ+COS stays p-only everywhere.

The LP in each non-empty **A** cell:
- **AUS:** DINGO everywhere except polar and mountain (its only BIOME is NOT_FREEZING = biomes 3-26, which includes taiga and desert); CROCODILE_SALTWATER in tropical wetland and fresh water.
- **AFR:** LION, LEOPARD, CHEETAH and HYENA, tropical grass only; LEOPARD in forest, wetland and desert. **No temperate LP.**
- **NEO:** COUGAR (temperate and tropical), JAGUAR, ANACONDA.
- **NEA:** WOLF, BEAR_GRIZZLY, BEAR_BLACK, COUGAR, ALLIGATOR, FISH_LAMPREY_SEA.
- **PAL:** WOLF (polar and temperate), TIGER (tropical), FISH_LAMPREY_SEA.
- **IND:** TIGER, LEOPARD, CROCODILE_SALTWATER.
- **ARC:** BEAR_POLAR, WOLF.
- **OCE:** 9 sharks.

**Answers**
- **Is there an Australasian predator for a temperate grassland?** Yes, but only one: DINGO (LP, BONECARN, pack 3:12). Its prey there are KANGAROO, BIRD_EMU, WOMBAT and ECHIDNA.
- **Hard gaps**, where a realm-filtered roster has no armable predator:
  - AUS on polar land and mountain;
  - NZ everywhere (true to life: no native land-mammal predator);
  - MAD everywhere;
  - ANT everywhere (4 benign ocean species, no predator);
  - AFR in every temperate, polar or mountain biome;
  - IND temperate;
  - NEO polar, taiga and temperate wetland;
  - PAL and NEA in desert and mountain.
- **Thin prey:** AFR temperate (1 prey), MAD (2 species in total), NZ (3 prey).

## How the tool could apply it

1. **Data**
   - A `realm` table (token → realms), shipped for vanilla, like `MARSUPIAL_TOKENS` but for geography. Add a per-embark setting `realm = AUS | … | off`.
   - COS is always allowed. OCE is allowed on the ocean layer. FANT follows the class switches the tool already has (mythic, locked).
2. **Roster filter**
   - On a realm embark, set `allow=false` for every managed species outside `realm ∪ COS` (∪ OCE for ocean entries). This uses the existing inactive state, which holds stock at 0 (land, water, vermin) or frequency 1 (caverns) (SW:1437).
   - X1 already showed that the roster gates arrivals.
3. **Fill check per biome group**
   - After filtering, run the pair guarantee (SW:1543) per season. Where a biome group present on the embark has no armed predator (the gaps above), the tool can:
     - (a) accept a prey-only season and say so;
     - (b) import a same-realm species by Add invasive. Only works where its raws list that biome (SW:2541), e.g. DINGO into any non-freezing AUS biome;
     - (c) **cross-biome import**, e.g. DINGO onto a tundra embark. Today Add invasive refuses it (`:biome`). It needs either a force path that writes the population whatever the biome, or a species-wide BIOME flag write in memory (global to the species, so it must be restored at unload).
   - Whether DF keeps waving a species into a biome its raws do not list is **untested**. That is a T2-style manifest check.
4. **Antarctic vs Arctic**
   - A realm filter `ANT` on an OCEAN_ARCTIC or GLACIER embark keeps only the 4 southern species (all BENIGN, ocean).
   - It removes BEAR_POLAR, WALRUS, NARWHAL and the other Arctic species. That is the only way to split the two poles in DF.
   - Nothing in ANT can be armed, so an Antarctic season has no predation unless OCE sharks are allowed. SHARK_BLUE and SHARK_FRILL are ANY_OCEAN, so they already reach OCEAN_ARCTIC.
5. **Ocean**
   - OCE species need the W2 realm fix (a water realm) before any realm-based pairing makes sense. Today they pair with land animals.

## Gaps and risks

- **The external table is a judgement.** About 30 generic DF names are ambiguous (DEER, FOX, EAGLE, SWAN…). Ship it editable.
- **Cross-biome imports are untested.** A realm-faithful roster for any realm outside its home climate needs them: an AUS fort on tundra, an AFR fort in a temperate forest.
- **FREQUENCY is low for many LPs.** DINGO, WOLF, LION and TIGER are at 5, so a realm roster with a single LP will see it rarely (X3: FREQUENCY steers the pick). The tool's odds lever may be needed to keep one apex per season.
- **NZ and MAD are too small to fill a year.** They need COS padding or an explicit "sparse fauna" mode.
