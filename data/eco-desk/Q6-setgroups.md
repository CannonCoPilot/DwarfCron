# Q6: tags as pre-built set-groups for the tool (desk)

**Scope**
- Wildlife is n=363 (the census): 248 LARGE_ROAMING (LR), 114 vermin, 1 neither (SPONGE).
- The tool's class split is 326 natural, 25 mythic, 12 unliving.

**Rules**
- A token's effect is claimed only from `wiki-tokens.md`.
- Where the wiki documents no fortress effect, the token is used as a **label**, not as a behaviour.
- Script: `eco/w/q6.py`; output in `q6-out.txt`.

## 1. Clean partitions (disjoint across the 363 wildlife species)

| partition | cells (wildlife count) | documented effect of the split |
|---|---|---|
| Population | LR 248 / vermin 114 (by family: GROUNDER 60, FISH 29, SOIL 9, EATER 7, ROTTER 5, SOIL_COLONY 4) / neither 1 | LR is the spawn tag; vermin are not units (the tool manages only their stock). |
| Aggression | LARGE_PREDATOR 60 / BENIGN 163 / unmarked 140 (none of the 114 vermin is LP) | LP attacks smaller creatures and is limited to one LP group per map. BENIGN flees. Unmarked has no documented default. |
| Diet | CARNIVORE 46 / BONECARN 41 / STANDARD_GRAZER 32 / none 244 | CARNIVORE: meat only. BONECARN: "does not work". STANDARD_GRAZER: hunger (documented for tame animals). |
| Water habit | AQUATIC 83 / AMPHIBIOUS 28 / SWIMS_INNATE only 190 / SWIMS_LEARNED 17 / none 45 | Breathing (AQUATIC, AMPHIBIOUS). SWIMS_* affects movement only; "fortress AI never paths into water". |
| Activity | ALL_ACTIVE 183 / DIURNAL 122 / NOCTURNAL 52 / CREPUSCULAR 21 (overlaps N/D) / VESPERTINE 1 | Adventure-mode timing only; no fortress effect is documented. |
| Flight | FLIER 60 / not 303 | Movement. |
| Layer | surface 308 / cavern-only 55 | Spawn layer. |

## 2. Products

Over the 248 LR species, aggression × diet × water (AQ / AMPH / air) × flight fills **27 of 72 cells**:

| aggression | diet | water | flier | n | examples |
|---|---|---|---|---|---|
| BEN | none | air | – | 49 | penguins, kiwi, ostrich, boar, monkeys |
| BEN | GRZ | air | – | 30 | horse, deer, reindeer, water buffalo, cavy |
| BEN | none | AQ | – | 30 | non-LP sharks, big ocean fish |
| LP | BONE | air | – | 16 | WOLF, DINGO, HYENA, BEAR_POLAR (+ trolls, ogres) |
| unm | none | air | – | 15 | RACCOON, MACAQUE, MANDRILL |
| unm | CARN | air | – | 15 | snakes, BOBCAT, LYNX, OCELOT, lizards |
| LP | none | air | – | 12 | BEAR_GRIZZLY, BEAR_BLACK (+ cave LPs) |
| BEN | none | air | FL | 11 | raven, stork, loon, grey parrot |
| LP | none | AQ | – | 10 | FISH_LAMPREY_SEA, 9 sharks |
| LP | CARN | air | – | 10 | COUGAR, LION, LEOPARD, JAGUAR, TIGER, CHEETAH, ANACONDA |
| BEN | BONE | air | FL | 7 | eagle, owls, falcon, kestrel, osprey |
| BEN | none | AMPH | – | 6 | walrus, hippo, platypus, seals |
| BEN | BONE | air | – | 5 | FOX, BADGER, WOLVERINE, MONGOOSE, STOAT |
| LP | CARN | AMPH | – | 5 | ALLIGATOR, CROCODILE_SALTWATER (+ cave crocodile, cave toad, olm) |
| unm | BONE | air | FL | 4 | KEA, GREAT_HORNED_OWL, BUZZARD, VULTURE |
| unm | BONE | air | – | 4 | COYOTE, JACKAL, HONEY BADGER (+ REACHER) |
| (11 more cells of 1-3) | | | | 17 | CAPYBARA, OCTOPUS, SPERM_WHALE, sea/river otter, crabs, PANDA… |

Adding factors fragments the cells:

| product (all 363) | non-empty cells | singleton cells | cells with ≥5 species |
|---|---|---|---|
| population × aggression × diet × water × flier × layer | 55 | 17 | 22 |
| + activity | 92 | 40 | 20 |

Activity adds 37 cells, 23 of them singletons, and has no documented fortress effect. It is a label, not a set-group axis.

**Useful axes:**
- **aggression**: DF acts on it (T4, E32b).
- **water habit**: breathing decides the survivable layer.
- **diet**: a label only; CARNIVORE and BONECARN do not change DF behaviour in fort mode (per the wiki).
- **flight**.
- **layer**.

## 3. Proposed guild scheme

Counts are over the 363 wildlife species; the first number is all classes, the one in brackets is natural only. Examples are natural species.

Behaviours:
- **arm** = the relation write.
- **cohesion** = the tool's follow label.
- **Rarity** comes from FREQUENCY in the raws: 153 LR species are at 50, 36 at 5, 20 at 10, 13 at 100, 10 at 1.

| guild | boolean expression | n (natural) | 5 examples | tool behaviour it would drive |
|---|---|---|---|---|
| G1 apex hunter (land) | LARGE_PREDATOR ∧ ¬AQUATIC ∧ ¬AMPHIBIOUS ∧ surface | 21 (13) | BEAR_GRIZZLY, BEAR_BLACK, COUGAR, WOLF, LION | Land layer. The **only arm set**. Cohesion `pack` if cluster >1, else solitary. DF documents 1 LP group per map, so cap concurrent G1 groups at 1 (2 when savage). Rare (FREQUENCY 2-5 in vanilla). |
| G2 water apex | LARGE_PREDATOR ∧ (AQUATIC ∨ AMPHIBIOUS) ∧ surface | 15 (13) | FISH_LAMPREY_SEA, SHARK_GREAT_WHITE, SHARK_BLUE, ALLIGATOR, CROCODILE_SALTWATER | Placed in water. Arm **only** against G8/G10/G11/G12 targets (REACH). School cohesion. Needs the realm fix (W2). |
| G3 ground mesocarnivore | (CARNIVORE ∨ BONECARN) ∧ ¬LARGE_PREDATOR ∧ ¬FLIER ∧ ¬AQUATIC ∧ LR | 29 (28) | FOX, BADGER, COYOTE, BOBCAT, JACKAL | Land layer. **Not armable** (BENIGN or unmarked; T4); arming needs an LP flip (E32b, T1). A target of G1. HUNTS_VERMIN write (X5: no effect). Solitary/pair cohesion, not `herd`. |
| G4 raptor | FLIER ∧ BONECARN | 11 (11) | BIRD_EAGLE, BIRD_FALCON_PEREGRINE, BIRD_OWL_BARN, BIRD_OSPREY, BIRD_KESTREL | Flock label. DIVE_HUNTS_VERMIN write (the tool already does this, SW:4588). Never armed (7 are BENIGN). |
| G5 thief / scavenger | CURIOUSBEAST_EATER ∨ _ITEM ∨ _GUZZLER | 21 (19) | BEAR_BLACK, RACCOON, BIRD_VULTURE, MANDRILL, HONEY BADGER | The scavenging category (S1/S2 subjects; see Q2). These visit the fort, per the wiki's documented theft. Membership of DF's CURIOUS_BEAST wave pool is undocumented. |
| G6 grazer herd | STANDARD_GRAZER | 32 (31) | DEER, HORSE, REINDEER, WATER_BUFFALO, GAZELLE | Land layer. Prey-eligible. `herd` cohesion; 30 of 32 are MEANDERER. The base prey of each land season. |
| G7 other land prey | LR ∧ BENIGN ∧ ¬STANDARD_GRAZER ∧ ¬(CARNIVORE∨BONECARN) ∧ ¬FLIER ∧ ¬AQUATIC ∧ ¬AMPHIBIOUS | 49 (47) | WILD_BOAR, KANGAROO, BIRD_OSTRICH, CHIMPANZEE, ELEPHANT | Prey-eligible. Cohesion `herd`; `loose` where LOOSE_CLUSTERS (the only documented spacing token). |
| G8 shore / semiaquatic | AMPHIBIOUS ∨ (all BIOME water ∧ ¬AQUATIC ∧ ¬FLIER) | 37 (35) | HARP_SEAL, WALRUS, HIPPO, CAPYBARA, BEAVER | Shore placement (the W1 boundary). Prey of G1 and G2 (REACH allows both). Follow as herd on land, not `school`. |
| G9 pelagic / deep ocean | AQUATIC ∧ LR ∧ ocean BIOME ∧ (BODY_SIZE ≥ 1,000,000 ∨ BEACH_FREQUENCY) | 11 (10) | SHARK_WHALE, SHARK_BASKING, SPERM_WHALE, ORCA, FISH_RAY_MANTA | The deep class for Q8: drawn only where the map has deep columns (O1). BEACH_FREQUENCY is the documented stranding risk. |
| G10 coastal / reef fish | AQUATIC ∧ LR ∧ ocean BIOME ∧ size < 1M ∧ ¬BEACH_FREQUENCY | 29 (29) | SHARK_NURSE, FISH_STINGRAY, FISH_COD, FISH_GROUPER_GIANT, FISH_MILKFISH | Ocean water layer, school. Prey of G2. |
| G11 large freshwater fish | AQUATIC ∧ LR ∧ (LAKE ∨ RIVER ∨ POOL) ∧ ¬ocean | 4 (4) | FISH_PIKE, FISH_CARP, FISH_GAR_LONGNOSE, FISH_TIGERFISH | Lake/river placement (feature layer). School. |
| G12 waterbird | FLIER ∧ water BIOME ∧ LR ∧ ¬BONECARN | 6 (6) | BIRD_DUCK, BIRD_GOOSE, BIRD_SWAN, BIRD_LOON, BIRD_ALBATROSS | Waterbird habitat, flock. Prey of G2 (REACH). |
| G13 land bird (non-raptor) | FLIER ∧ LR ∧ ¬BONECARN ∧ no water BIOME | 9 (4 surface natural) | BIRD_RAVEN, BIRD_STORK_WHITE, BIRD_PARROT_GREY, BIRD_HORNBILL | Flock, prey-eligible. The other 5 members are 4 cavern fliers and NIGHTWING (unliving). |
| G14 vermin (existing families) | any VERMIN_* creature flag | 114 (104) | TOAD, SPARROW, FISH_SALMON, FLY, ANT | Not units, so stock lever only. The tool's families (SW:1883): fish / flies / colony / soil / mammals / fliers / crawlers. |
| G15 cavern fauna | every BIOME is SUBTERRANEAN_* (UNDERGROUND_DEPTH set) | 55 (39) | CRUNDLE, DRUNIAN, CROCODILE_CAVE, RAT_GIANT, BAT_GIANT | Cavern layer by depth. DF waves them (E40). Arm cavern LPs within their depth realm (24 of 55 are LP). |
| overlay: hibernator | NO_WINTER (plus NO_SPRING / NO_AUTUMN) | 22 (+1, +2) | RABBIT, BEAR_GRIZZLY, BEAR_BLACK, GROUNDHOG, BADGER | **Season mask**: never deal the absent season (documented "does not appear"). T2 tests whether DF honours it. |
| overlay: fights back | PRONE_TO_RAGE > 0 | 4 | BADGER, HONEY BADGER, WOLVERINE, BLACK_MAMBA | "Flip out at visible non-friendly creatures" (documented). Useful as a prey trait. T1 measures it. |
| overlay: common | UBIQUITOUS | 9 (all vermin insects) | FLY, ANT, BEETLE, MOSQUITO, TICK | Rarity: always passes the spawn roll (documented). |

### Overlaps

69 species sit in more than one guild. The main overlaps:

| overlap | n | species |
|---|---|---|
| G2 ∧ G10 | 9 | small ocean LPs: lamprey, 8 sharks |
| G2 ∧ G9 | 3 | SHARK_GREAT_WHITE, SEA_SERPENT, SEA_MONSTER |
| G2 ∧ G8 | 3 | ALLIGATOR, CROCODILE_SALTWATER, GRIMELING |
| G1 ∧ G5 | 3 | BEAR_GRIZZLY, BEAR_BLACK, BEAR_POLAR (armed and thieves) |
| G4 ∧ G5 | 3 | BIRD_KEA, BIRD_BUZZARD, BIRD_VULTURE |
| G3 ∧ G8 | 5 | GILA_MONSTER, the otters, the snapping turtles |
| G7 ∧ G8 | 5 | penguins, BEAVER, MINK |
| G3 ∧ G5 | 2 | HONEY BADGER, COATI |
| G14/G15 with others | 33 | amphibious vermin (TOAD, AXOLOTL, LEECH), cavern vermin, cavern amphibians and cavern prey |

Precedence proposal:
- **Layer:** G15 > G14 > water guilds (G2, G8-G12) > land guilds.
- **Arming:** G1/G2 come first.
- G5 and the overlays are **tags added on top**, not exclusive guilds.

### Unassigned (1)

SPONGE: IMMOBILE, unliving class. Keep it out of placement and cohesion (documented "cannot move").

## 4. What the scheme changes versus the tool today

| behaviour | today (SW) | with guilds |
|---|---|---|
| Arm | every `largePred` in realm land/cavern, any class (SW:3236) | G1 against G6/G7/G8/G3/G13 targets; G2 against the water guilds; G15 LPs within depth. Never locked classes. |
| Predator role for coupling and pair guarantee | any CARNIVORE/BONECARN/LP/AMBUSH (103 non-vermin) | G1/G2 (armable), with G3/G4 as "co-present, not hunting" (T4) |
| Cohesion | water→school, FLIER→flock, LP→pack, else herd (SW:4225) | G8 → herd, not school. G3 → solitary/pair. LOOSE_CLUSTERS → loose (12 species). Cluster 1:1 → solitary. |
| Seasons | climate lean only (SW:1459) | + the NO_* mask |
| Deep water | none | G9 draws only on deep maps (O1/O2) |
| Scavenging | PLAN.md:195-220 (BONECARN or CARNIVORE and not small) | G5 ∪ {BIRD_CROW, BIRD_RAVEN, JACKAL} by description (Q2). BONECARN alone is not documented to eat. |

### Validation hooks

The rig blocks that test each guild boundary:

| rig block | what it validates |
|---|---|
| P1 | G1 vs G3 (WOLF vs COYOTE vs FOX) |
| T1 | the LP flip on COYOTE (the G3→G1 promotion), and BENIGN |
| W1 | G2 vs G8 and G1 vs G8 across the shore |
| S1 | G5 vs BONECARN |
| L1 | cohesion labels |
| T2 | the hibernator overlay |
