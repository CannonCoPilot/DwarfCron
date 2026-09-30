# Test-species candidates from the DF 53.16 vanilla creature raws

Source: `census.py` over `data/vanilla/vanilla_creatures/objects/*.txt` + `vanilla_creatures_extinct` (967 creatures), with
COPY_TAGS_FROM, APPLY_CREATURE_VARIATION, inline CV_* and GO_TO_START/END/TAG resolved; token presence is "any caste" unless
it says `some:`. Size = adult BODY_SIZE (last value) x CHANGE_BODY_SIZE_PERC. `freq (50)` = no FREQUENCY token (DF default 50).
Only DF tokens are quoted below. Anything about real-world geography is labelled **external** (not from the raws).

Common abbreviations: LR = LARGE_ROAMING, LP = LARGE_PREDATOR, BEN = BENIGN, GRZ = STANDARD_GRAZER, AMPH = AMPHIBIOUS,
AQ = AQUATIC (always with IMMOBILE_LAND/NO_DRINK/UNDERSWIM for fish), US = UNDERSWIM, SWIM = SWIMS_INNATE, MEA = MEANDERER,
D/N/C/AA = DIURNAL/NOCTURNAL/CREPUSCULAR/ALL_ACTIVE.

**Design caveat that applies to every pair:** surface LARGE_PREDATORs are rare in the raws. Wolf, cougar, lion, tiger, cheetah,
hyena, crocodile and similar carry `FREQUENCY:5`, and bears carry `FREQUENCY:2`, while their prey carry 50. Sharks and alligators
are the exception at 50. If the predator has to arrive naturally, you will wait a long time, so plan to place it.

## (a) Predator / prey pairs (predator = LARGE_PREDATOR; prey = BENIGN, and they share at least one BIOME unless noted)

| # | Predator (size, freq, tokens) | Prey (size, tokens) | Shared biome(s) | Why |
|---|---|---|---|---|
| 1 | WOLF 40k, f5, pop 10:20 cl 3:7. LP BONECARN D MEA SWIM | DEER 140k. BEN GRZ D MEA SWIM | FOREST_TAIGA, ANY_TEMPERATE_FOREST | The classic temperate pair. The prey is larger than the predator, and the wolf comes in packs (cl 3:7). |
| 2 | WOLF (as above) | RABBIT 500. BEN GRZ D MEA NO_WINTER SWIM COMMON_DOMESTIC | SHRUBLAND_TEMPERATE | The same predator on 80x smaller prey. The rabbit is absent in winter. |
| 3 | CHEETAH 50k, f5, pop 5:10 cl 1:1. LP CARNIVORE D MEA SWIM TRAINABLE | GAZELLE 20k. BEN GRZ D MEA SWIM (cl 5:10) | SAVANNA_TROPICAL, GRASSLAND_TROPICAL | A small solitary predator on small herd prey. |
| 4 | LION 200k, f5, cl 1:3. Same tokens as cheetah plus MOUNT_EXOTIC | IMPALA 50k / WARTHOG 100k / GIRAFFE 1M (all BEN GRZ D MEA; giraffe has no SWIMS_INNATE) | SAVANNA_TROPICAL, GRASSLAND_TROPICAL | One predator against a size ladder of prey. Lion and cheetah share biomes and tokens, so they differ mainly in size. |
| 5 | BEAR_GRIZZLY 200k, f2, pop 2:3. LP D MEA NO_WINTER STANCE_CLIMBER CURIOUSBEAST_EATER/GUZZLER, no diet token | MOOSE 525k. BEN GRZ D MEA SWIM | FOREST_TAIGA, ANY_TEMPERATE_FOREST | Prey larger than the predator. The bear carries no CARNIVORE/BONECARN. |
| 6 | CROCODILE_SALTWATER 800k, f5. LP CARNIVORE AMPH AA CANNOT_JUMP | WATER_BUFFALO 1M (BEN GRZ D SWIM) or CAPYBARA 45k (AMPH GRZ D, not BENIGN) | tropical swamps and marshes (buffalo ANY_TROPICAL_WETLAND; capybara ANY_WETLAND) | **Water-to-land.** An amphibious ambusher against a land grazer, or against another amphibian. |
| 7 | ALLIGATOR 400k, freq (50). LP CARNIVORE AMPH AA | BIRD_DUCK 1k (BEN FLIER SWIM ROOT_AROUND GOBBLE_VERMIN_CLASS) or CAPYBARA | temperate and tropical freshwater swamps and marshes | A water predator that arrives at normal frequency, against a flier and swimmer. |
| 8 | BEAR_POLAR 400k, f2. LP BONECARN D MEA | HARP_SEAL 165k (AMPH BEN US D) / BIRD_PENGUIN 4k (BEN D MEA SWIM, **not** AMPH/AQ) / MUSKOX 285k, REINDEER 130k (land GRZ) | Bear GLACIER/TUNDRA. Seal and penguin OCEAN_ARCTIC (adjacent, not shared). Muskox and reindeer share TUNDRA. | **Land-to-water.** A land predator at the ice edge against amphibious prey, with land grazers as the control. |
| 9 | SHARK_BLUE 300k, freq (50), ANY_OCEAN. LP AQ US AA | HARP_SEAL / BIRD_PENGUIN / WALRUS 1.5M (AMPH BEN US) | OCEAN_ARCTIC | **Shark against swimmer.** The one LP shark that lives in arctic water, where the seals and penguins are. |
| 10 | SHARK_GREAT_WHITE 2M, freq (50). LP AQ US AA | SEA OTTER 30k (AMPH BEN BONECARN D) or FISH_TUNA_BLUEFIN 600k (AQ BEN, pop 25:50 cl 10:15) | OCEAN_TEMPERATE | A shark against an amphibious mammal, and against a fully aquatic fish. |
| 11 | SHARK_TIGER 500k (OCEAN_TROPICAL). LP AQ | FISH_MILKFISH 10k (AQ BEN MEA, cl 3:7) / FISH_STINGRAY 5k | OCEAN_TROPICAL | A tropical-water pair. The milkfish description says "easy prey for predators". |
| 12 | ANACONDA 100k, freq 50. LP CARNIVORE AA CANNOT_JUMP (not AMPH) | CAPYBARA 45k (AMPH GRZ) | ANY_TROPICAL_WETLAND | A predator that arrives at normal frequency, against a wetland grazer. |
| 13 | FISH_LAMPREY_SEA 20k. LP AQ (the only LARGE_PREDATOR river fish) | BEAVER 20k (BEN N MEA SWIM) / FISH_STURGEON 1.5M (AQ BEN) | RIVER/LAKE_TEMPERATE_* | A small water predator on a same-size mammal and on a huge fish. |
| 14 | TIGER 225k, f5. LP CARNIVORE N MEA | WILD_BOAR 80k (BEN D MEA, very wide biomes) | tropical forest and swamps | Nocturnal predator, diurnal prey. |
| 15 | HYENA 60k / DINGO 20k, f5. LP BONECARN N+C MEA, pack cl 5:15 / 3:12 | IMPALA (hyena); KANGAROO 90k (BEN GRZ N+C) or RABBIT (dingo; dingo is NOT_FREEZING, so it covers almost everywhere) | tropical savanna / temperate grassland | Pack scavenger-predators. Hyena and dingo have identical token sets and differ only in size. |

Things to know about the land predators:
- Many carnivores are **not** LARGE_PREDATOR. FOX, STOAT, MONGOOSE, BADGER, RIVER/SEA OTTER, the eagles, owls and falcons
  are BENIGN plus BONECARN. JACKAL, COYOTE, BOBCAT, LYNX, OCELOT and the snakes carry a diet token but neither BENIGN nor LP.
- In the raws, temperate-only surface wildlife has **zero** LARGE_PREDATORs. Every temperate LP also lists a cold or tropical biome.

## (b) Natural minimal pairs (same interest-token set except the one named; sizes and biomes listed)

"Exact" means identical across all ~100 interest tokens apart from BIOME, FREQUENCY, POP/CLUSTER, GAIT, PETVALUE and
VISION_ARC/GRASSTRAMPLE.

| Token that differs | Has it | Lacks it | Exact? | Notes |
|---|---|---|---|---|
| LARGE_PREDATOR | WOLF 40k | COYOTE 15k | exact | Both BONECARN D MEA, f5, pop 10:20. Shared biomes: TUNDRA, FOREST_TAIGA, ANY_TEMPERATE_FOREST, SHRUBLAND_TEMPERATE. **The best LP pair.** |
| LARGE_PREDATOR (+BENIGN) | SHARK_BLUE 300k / SHARK_GREAT_WHITE 2M | FISH_SWORDFISH 650k / FISH_TUNA_BLUEFIN 600k (BENIGN) | LP swapped for BENIGN | All AQ US AA, shared OCEAN_TEMPERATE/TROPICAL. SHARK_NURSE 150k is BENIGN plus MEANDERER instead of LP. |
| BENIGN | BIRD_CROW 500 | BIRD_BLUEJAY 100 | exact | Both vermin (VERMIN_GROUNDER) FLIER D. Shared: temperate grass, savanna and shrub. |
| MEANDERER | FISH_PIKE 35k | FISH_GAR_LONGNOSE 20k | exact | Identical biomes (4 temperate river/lake). |
| UNDERSWIM | WALRUS 1.5M (OCEAN_ARCTIC) | HIPPO 1.5M (tropical river/lake) | exact | Same size. Both AMPH BEN D MEA. |
| AMPHIBIOUS | SEA OTTER 30k (OCEAN_TEMPERATE) | FOX 6k (taiga/temperate forest) | exact | Both BEN BONECARN D. STOAT 350 and MONGOOSE 3k have the fox's exact token set, which gives a size ladder of 350 / 3k / 6k. |
| NO_WINTER | GROUNDHOG 3k (temperate grass/shrub/savanna) | DEER 140k (forest) / GAZELLE 20k / IMPALA 50k | exact | All BEN GRZ D MEA SWIM. |
| NO_AUTUMN (+NO_WINTER both) | MARMOT_HOARY 10k (MOUNTAIN) | GROUNDHOG 3k | exact | The only natural NO_AUTUMN mammal. |
| CREPUSCULAR | ARMADILLO 7.5k | AARDVARK 50k | exact | Both BEN N MEA. Shared: SAVANNA/GRASSLAND/SHRUBLAND_TROPICAL. |
| NOCTURNAL | ARMADILLO (N+C) | SKUNK 4k (C only) | exact | No shared biome. |
| SWIMS_INNATE (+MOUNT_EXOTIC) | WARTHOG 100k / IMPALA 50k | GIRAFFE 1M | 2 tokens | Same savanna. The giraffe is the only big grazer that cannot swim. |
| DIVE_HUNTS_VERMIN (+PET vs PET_EXOTIC) | BIRD_FALCON_PEREGRINE 600 | BIRD_OWL_BARN 500 | 2 tokens | Both BEN BONECARN FLIER AA. Share 8 biome tokens. |
| VERMIN_FISH | FISH_SALMON 200 | FISH_MOLLY_SAILFIN 200 | exact (in the behaviour vector) | Both vermin fish, VERMIN_GROUNDER. |
| CURIOUSBEAST_ITEM (+STANCE_CLIMBER) | BIRD_KEA 1k | BIRD_BUZZARD 1.4k | near | Both BONECARN CURIOUSBEAST_EATER LOOSE_CLUSTERS FLIER. |
| LOOSE_CLUSTERS | SPIDER_MONKEY 8.5k | AYE-AYE 2.5k | exact (behaviour vector) | Tropical forest. |
| size only | HARP_SEAL 165k / LEOPARD_SEAL 400k | (identical tokens) | exact | Both OCEAN_ARCTIC AMPH BEN US D. ELEPHANT_SEAL 3M adds MEANDERER. |
| size only | GAZELLE 20k / IMPALA 50k / DEER 140k | (identical tokens) | exact | BEN GRZ D MEA SWIM. The first two share savanna. |
| size only | LION 200k / CHEETAH 50k | (lion adds MOUNT_EXOTIC) | near | Identical biomes. |
| size only | DINGO 20k / HYENA 60k | (identical tokens) | exact | LP BONECARN N+C MEA. |

The full list of one-token pairs is regenerated by the minimal-pair snippet at the bottom of this file. The most frequent
single-token differences are MEANDERER (214 pairs), STANDARD_GRAZER (148), VERMIN_FISH (147), VERMIN_GROUNDER (63), BENIGN (59),
FLIER (54), NO_WINTER (39) and SWIMS_INNATE (25).

## (c) Scavenger and "eats odd things" signals

In the raws, CARNIVORE and BONECARN never appear together, and neither appears with STANDARD_GRAZER. There is **no carrion
token**. The scavenger reading comes from BONECARN, the CURIOUSBEAST_* thieves, and the descriptions.

- **CARNIVORE** (51 vanilla, not animal person or giant; 46 wildlife): the big cats (cougar, lion, leopard, jaguar, tiger,
  cheetah, lynx, bobcat, ocelot), crocodilians (alligator, saltwater crocodile, cave crocodile), snakes (adder, kingsnake,
  rattlesnake, copperhead, anaconda, king cobra, black mamba, bushmaster, python), lizards (gila monster, monitor lizard, iguana,
  skink, chameleon, anole, gecko, lizard), turtles (snapping, alligator snapping, pond), OCTOPUS, SPERM_WHALE, spiders and
  scorpion, COATI, CAT (domestic), and cave creatures (crundle, helmet snake, voracious cave crawler, giant cave toad, giant olm,
  giant cave spider).
- **BONECARN** (49 vanilla; 41 wildlife), "eats bones": WOLF, COYOTE, DINGO, HYENA, JACKAL, FOX, STOAT, BADGER,
  HONEY BADGER, WOLVERINE, MONGOOSE, RIVER OTTER, SEA OTTER, BEAR_POLAR, DOG, the raptors (eagle, falcon, kestrel, osprey, the
  three owls), **BIRD_VULTURE and BIRD_BUZZARD** (their descriptions say "carcasses" and "carrion"), BIRD_KEA, and many
  monsters (troll, ogre, yeti, sasquatch, sea serpent, sea monster, cave dragon, and others).
- **CURIOUSBEAST_EATER / _GUZZLER / _ITEM** (steal food / drink / items from the fort): bears (grizzly, black, polar, sloth:
  EATER plus GUZZLER), RACCOON (EATER plus ITEM), the monkeys (macaque, mandrill, capuchin, gray langur: EATER plus ITEM),
  COATI, BIRD_KEA, BIRD_VULTURE, BIRD_BUZZARD, HONEY BADGER (EATER), the gnomes (GUZZLER), and cave rats and moles.
  BEAR_BLACK's description says it "will also steal carcasses from other hunters", and SHARK_MAKO_LONGFIN's says it "scavenges".
- **VERMIN_EATER** (7; creature-level; vermin that eat food and stockpiles): RAT, HAMSTER, LIZARD, ROACH_LARGE,
  LIZARD_RHINO_TWO_LEGGED, RAT_DEMON, WAMBLER_FLUFFY. GNAWER is on 5 of them (rat, hamster, bat, rat demon, rhino lizard), and
  TRIGGERABLE_GROUP 5:50 is on rat, roach, rat demon and wambler (bat is 50:100).
- **VERMIN_ROTTER** (5; appear around rot): FLY, FLY_ACORN, GNAT_BLOOD, CREEPY_CRAWLER, WORM_KNUCKLE.
- **GOBBLE_VERMIN_CLASS** (always `EDIBLE_GROUND_BUG`; always paired with ROOT_AROUND): BIRD_DUCK, BIRD_GOOSE, BIRD_TURKEY,
  BIRD_PEAFOWL_BLUE, BIRD_KIWI, HEDGEHOG, PANGOLIN, and the domestic chicken and guineafowl. GOBBLE_VERMIN_CREATURE: 0.
- **HUNTS_VERMIN / RETURNS_VERMIN_KILLS_TO_OWNER / AT_PEACE_WITH_WILDLIFE**: CAT only. **DIVE_HUNTS_VERMIN**: BIRD_FALCON_PEREGRINE
  only.
- **SPECIFIC_FOOD**: PANDA and RED PANDA (bamboo).

## (d) Ocean creatures: what separates open water from the coast

The raws have **no depth or open-ocean token**. Ocean biomes are only OCEAN_TROPICAL, OCEAN_TEMPERATE, OCEAN_ARCTIC and
ANY_OCEAN. UNDERSWIM is on almost every AQUATIC creature (79/83), so it is not a depth marker. Wildlife that uses an ocean biome
number 81 (79 plus FAIRY and PIXIE through ALL_MAIN). By climate:

- **ANY_OCEAN** (all three climates): SHARK_BLUE, SHARK_FRILL (LP), ORCA, SPERM_WHALE, OCTOPUS, BIRD_ALBATROSS; the vermin
  CUTTLEFISH, NAUTILUS, SQUID and OYSTER; the AMPHIBIOUS CRAB and HORSESHOE_CRAB; SPONGE and MUSSEL (also freshwater); the
  SEA_SERPENT and SEA_MONSTER monsters.
- **OCEAN_ARCTIC only**: the 4 seals and walrus (AMPH), NARWHAL (AQ), BIRD_PUFFIN (FLIER), and the 3 penguins (SWIMS_INNATE only,
  not AQ or AMPH).
- **OCEAN_TEMPERATE + OCEAN_TROPICAL**: most LR sharks and big fish (great white, makos, hammerhead, angel, dogfish, wobbegong,
  skate, opah, bluefish, sunfish, swordfish, marlin).
- **OCEAN_TROPICAL only**: whale shark, tiger shark, bull shark, the two reef sharks, manta, coelacanth, giant grouper, great
  barracuda, and the vermin clownfish, glasseye and puffer.
- **Ocean plus fresh water** (anadromous in effect): lamprey (sea and brook), sturgeon, salmon, shad, steelhead, milkfish,
  stingray.

Raw signals usable for coast versus open water:
1. **AMPHIBIOUS in an ocean biome** marks shore-dwellers: seals, walrus, sea otter, crab, horseshoe crab.
2. **BEACH_FREQUENCY:10** is on only ORCA, SPERM_WHALE and JELLYFISH_SEA_NETTLE (the things that wash up on beaches).
3. **Vermin (VERMIN_FISH, pop 250:500 or larger) versus LARGE_ROAMING (pop 15:30).** In DF this is a population-model
   difference, not a depth one.
4. **Size.** Ocean LRs run from 1.5k to 25M. Over 1M: whale shark 20M, sperm whale 25M, basking shark 15M, orca 5M,
   elephant seal 3M, manta 2.3M, great white 2M.
5. **DESCRIPTION text only** (not a token):
   - Coastal or shallow: SHARK_FRILL, SHARK_SPINY_DOGFISH, SHARK_MAKO_LONGFIN, SHARK_HAMMERHEAD, SHARK_BULL, both reef
     sharks, SHARK_NURSE, FISH_COELACANTH, FISH_MILKFISH, FISH_STINGRAY ("near the beach"), CROCODILE_SALTWATER, HORSESHOE_CRAB,
     and the rays, sole, flounder, ratfish and sea nettle.
   - Reef: giant grouper, seahorse, glasseye, puffer.
   - Open ocean: only FISH_SWORDFISH says so.

## (e) Geographic grouping: what the raws support

- **No continent, hemisphere or realm tokens exist.** Biome tokens only encode climate and landform (TEMPERATE, TROPICAL, TUNDRA,
  GLACIER, TAIGA, DESERT_*, MOUNTAIN, OCEAN_ARCTIC, ...). A DF world generates its own continents, and any animal can appear on
  any landmass with a matching biome.
- **There is no Antarctic.** The penguins (BIRD_PENGUIN, _LITTLE, _EMPEROR) are OCEAN_ARCTIC, and their descriptions say
  "arctic shorelines" and "glacial ice". BEAR_POLAR is GLACIER+TUNDRA ("hunts the shores along tundra and glaciers"). In the
  raws, penguins and polar bears share a polar zone, so they co-occur and can be tested as a predator/prey pair (#8).
- **Marsupial evidence is nearly absent.** The only raw string is `PREFSTRING:pouches` on KANGAROO (and GIANT_KANGAROO /
  KANGAROO_MAN by inheritance). No body part, CREATURE_CLASS or description says "pouch" or "marsupial". KOALA, WOMBAT and
  OPOSSUM carry nothing marsupial. CREATURE_CLASS values are only GENERAL_POISON, MAMMAL, ANIMAL_PERSON, REAL_WORLD_EXTINCT, the 10 geologic periods,
  POISONOUS, EDIBLE_GROUND_BUG and two tracking-symbol classes. There is no REPTILE, BIRD, FISH or MARSUPIAL class; MAMMAL is the only taxon class.
- Raw evidence that *is* usable: climate lean from BIOME (cold / temperate / tropical / desert / mountain; see groupings.md) and
  description words ("temperate woodland", "tropical forests", "savanna", "jungle", "high mountains", "arctic shorelines",
  "tundra", "snowy wilds").
- **External, name-based sets** (real-world knowledge, not in the raws), in case you want a geographic factor:
  - Australia/NZ: KANGAROO, KOALA, WOMBAT, ECHIDNA, PLATYPUS (LAYS_EGGS; a monotreme in reality), DINGO, BIRD_EMU,
    BIRD_CASSOWARY, BIRD_LORIKEET, BIRD_COCKATIEL, SHARK_WOBBEGONG_SPOTTED; NZ: BIRD_KIWI, BIRD_KAKAPO, BIRD_KEA.
  - Africa: LION, CHEETAH, HYENA, JACKAL, GIRAFFE, RHINOCEROS, HIPPO, WARTHOG, IMPALA, GAZELLE, AARDVARK, MONGOOSE, the apes,
    MANDRILL, BLACK_MAMBA, BIRD_OSTRICH; Madagascar: AYE-AYE.
  - The Americas: COUGAR, JAGUAR, OCELOT, BOBCAT, COYOTE, RACCOON, SKUNK, OPOSSUM, COATI, ARMADILLO, SLOTH, TAPIR, CAPYBARA,
    CHINCHILLA, CAVY, LION_TAMARIN, CAPUCHIN, SPIDER_MONKEY, ALLIGATOR, RATTLESNAKE, COPPERHEAD_SNAKE, KINGSNAKE, GILA_MONSTER,
    ANACONDA, BIRD_BLUEJAY, BIRD_CARDINAL, BIRD_GRACKLE, BIRD_TURKEY, GROUNDHOG, BEAVER.
  - Asia: TIGER, PANDA, RED PANDA, ORANGUTAN, the gibbons, KING_COBRA, MACAQUE_RHESUS, GRAY_LANGUR, YAK, WATER_BUFFALO,
    CAMEL_2_HUMP, PYTHON.
  - Arctic: BEAR_POLAR, MUSKOX, REINDEER, WALRUS, NARWHAL, the seals, BIRD_OWL_SNOWY, BIRD_PUFFIN, plus the penguins as DF
    places them.
  In DF these sets are **not** geographically segregated. For example, KANGAROO (temperate grass/savanna/shrub, desert) and
  HORSE (temperate grass/savanna) can share a tile.

## Minimal-pair snippet

```
python3 - <<'EOF'   # run in this folder; prints single-token pairs among surface, non-evil/good/savage wildlife
import json,itertools; from census import INTEREST
d=json.load(open('census.json')); X={'BIOME','FREQUENCY','POPULATION_NUMBER','CLUSTER_NUMBER','PETVALUE','GAIT','VISION_ARC','GRASSTRAMPLE'}
W=[r for r in d if r['_wild'] and not r['EVIL'] and not r['GOOD'] and r['SAVAGE'] in (0,'0')]
v={r['id']:frozenset(t for t in INTEREST if t not in X and r[t] not in (0,'0')) for r in W}
for a,b in itertools.combinations(v,2):
    if len(v[a]^v[b])==1: print(a,b,set(v[a]^v[b]))
EOF
```
