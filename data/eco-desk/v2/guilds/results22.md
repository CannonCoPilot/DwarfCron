# Roster builder v2.2: results (30 Sep 2026, user rulings of the evening)

Files only: `roster2.py` (v2.2 switches, all off = v2.1 / v2), `run2.py` (configs `v22*`), `analyze22.py` -> `analyze22.out`,
`tables22.md` (full per-layer and slot-fill tables), `ge22.md` (GOOD/EVIL table, also below), `cmp22.out` (table 0).
`runs/v22*.jsonl` are gitignored like the rest of `runs/`. main, savage, v21 and v21_savage reran byte-identical.

**v2.2 = v2.1 plus:** pack-mass floor 5% (was 20%) with a sneak-bonus flag at 25%; cavern bats/floaters eat flying and
ground vermin and cavern raptors also take cavern land prey; a flying apex (surface raptors >= 2 kg, not scavengers; giants
and pterosaurs on savage maps), with flying sentients as its prey; a prey-sentient slot (SNP 0-1) beside SN on every layer;
fishers (grizzly, black bear, tiger, jaguar) join the lake/river/ocean webs; GOBBLE-based vermin links; a vegetation link for
predator-less herbivores; GOOD/EVIL species on matching regions (and always underground); colony vermin out of the flying pool;
ladder22 with FREQUENCY scaled to DF's cap of 100.

## 0. Per layer, main / v21 / v22 (calm embarks, 11 embarks x 4 seasons x 20 seeds)

| layer | rosters (main / v21 / v22) | mean size | split webs | unit edges DF can act on (measured / +untested) | apex present | predator share of arrivals | apex share |
|---|---|---|---|---|---|---|---|
| land | 880 / 880 / 880 | 10.6 / 10.6 / 10.6 | 0% / 0% / 0% | 91% / 91% / 100% / 100% / 100% / 100% | 100% / 100% / 100% | 0.14 / 0.31 / 0.16 | 0.02 / 0.09 / 0.07 |
| flying | 880 / 880 / 880 | 6.6 / 6.6 / 7.5 | 0% / 0% / 0% | 0% / 34% / 0% / 100% / 0% / 100% | 0% / 0% / 100% | 0.36 / 0.37 / 0.19 | 0.00 / 0.00 / 0.06 |
| ocean | 320 / 320 / 320 | 11.5 / 13.2 / 13.2 | 0% / 0% / 0% | 87% / 96% / 90% / 100% / 89% / 100% | 100% / 100% / 100% | 0.06 / 0.14 / 0.10 | 0.02 / 0.08 / 0.07 |
| lake | 160 / 160 / 160 | 7.0 / 7.0 / 9.5 | 0% / 0% / 0% | 53% / 91% / 62% / 100% / 54% / 100% | 50% / 50% / 100% | 0.54 / 0.57 / 0.10 | 0.01 / 0.03 / 0.06 |
| river | 240 / 240 / 240 | 8.3 / 8.3 / 8.3 | 0% / 0% / 0% | 79% / 84% / 98% / 100% / 93% / 100% | 100% / 100% / 100% | 0.13 / 0.21 / 0.12 | 0.03 / 0.08 / 0.07 |
| cav1 | 80 / 80 / 80 | 5.3 / 7.0 / 8.1 | 0% / 100% / 0% | 95% / 100% / 90% / 100% / 72% / 100% | 100% / 100% / 100% | 0.08 / 0.24 / 0.15 | 0.03 / 0.12 / 0.06 |
| cav2 | 80 / 80 / 80 | 9.1 / 10.0 / 11.0 | 0% / 100% / 0% | 84% / 100% / 88% / 100% / 76% / 100% | 100% / 100% / 100% | 0.15 / 0.25 / 0.16 | 0.02 / 0.09 / 0.06 |
| cav3 | 80 / 80 / 80 | 8.1 / 9.0 / 11.0 | 0% / 100% / 0% | 89% / 100% / 91% / 100% / 77% / 100% | 100% / 100% / 100% | 0.12 / 0.21 / 0.16 | 0.02 / 0.07 / 0.09 |
| cavw1 | 80 / 80 / 80 | 5.0 / 5.0 / 5.0 | 0% / 0% / 0% | 100% / 100% / 100% / 100% / 100% / 100% | 100% / 100% / 100% | 0.44 / 0.33 / 0.33 | 0.44 / 0.33 / 0.33 |
| cavw2 | 80 / 80 / 80 | 5.0 / 5.0 / 5.0 | 0% / 0% / 0% | 78% / 100% / 61% / 100% / 66% / 100% | 100% / 100% / 100% | 0.44 / 0.33 / 0.33 | 0.44 / 0.33 / 0.33 |
| cavw3 | 0 / 0 / 0 | - / - / - | - / - / - | 0% / 0% / 0% / 0% / 0% / 0% | - / - / - | - / - / - | - / - / - |
| deep | 80 / 80 / 80 | 2.0 / 2.0 / 2.0 | 0% / 0% / 0% | 100% / 100% / 100% / 100% / 100% / 100% | 100% / 100% / 100% | 0.09 / 0.38 / 0.23 | 0.09 / 0.38 / 0.23 |

"Split webs" counts a roster whose animal web has more than one part after joining the herbivores the vegetation supports
through one plant node. v21's 100% cavern split is gone. The flying layer's measured reach stays 0% until the raptor block runs.

## 1. Singletons and split webs (full creature set, all configs: calm, savage, good, evil, evil+savage)

- **Cavern webs rejoined: 100% split (v21) -> 0% (v22)** in every config. Bugbats and floaters eat cave vermin (VB/VG; no
  cavern flying insect exists in vanilla), BAT_GIANT / HUNGRY_HEAD / giant cave swallow eat bats, bugbats, floaters and cave land
  prey. Cave raptors stay mesopredators (the flying-apex rule is surface-only).
- **Surface:** 0% split on calm and good/evil maps. On savage maps 7% have a prey-guild animal person with no allowed attacker
  that the vegetation link keeps (e.g. GRAY_LANGUR_MAN); joined through the plants, 0%.
- **Never placeable in any layer of the embark-season (the true singletons): 20 species-cells, all five cavern civ races**
  (TROGLODYTE, RODENT MAN, AMPHIBIAN_MAN, REPTILE_MAN, SERPENT_MAN). They are apex-tier (nothing may eat them: no apex-on-apex)
  and sentient non-animal-people (kept out of attacker roles in v2.1). **Irreducible under the current rules; your call.**
  With `civ_attack` (config `v22_civ`, not a ruling) they hunt by guild and the count is 0.
- Pool-level leftovers in v22 (placeable in another layer, so not singletons): GIANT_FLY / GIANT_MOSQUITO in savage lake pools
  (eaten in the flying layer). Fixed on the way: ANT / BUMBLEBEE / HONEY_BEE colonies were in the flying pool with no consumer
  (120 cells) -> moved to the land VC slot; lake ducks, carp, milkfish, stingray, tigerfish with no predator (temperate lake had
  no apex half the time) -> fishers take them; HIPPO in lake pools -> vegetation link (shore grazing) or fishers.
- Never in a pool on these 11 embarks (not a rule problem): GNOME_MOUNTAIN, GNOME_DARK (MOUNTAIN), STRANGLER
  (FOREST_TROPICAL_MOIST_BROADLEAF).

## 2. FREQUENCY ladder (predator share of arrivals)

v2.1's ladder put predators at 31% of land arrivals. Ladder22 (`roster2.LADDER22`, the FREQUENCY the tool writes, then scaled
per roster so the commonest member is 100: DF's cap compressed raised prey values otherwise):

| family | apex | meso / raptor | prey | result, calm (predator share / apex share) |
|---|---|---|---|---|
| land | 4 | 2 | grazer 10.5, other land prey 8.75, shore 7 (x1.75 of v2.1) | land 0.16 / 0.07 |
| flying | 2 | 2 | land birds 30, waterbirds 30 (x5) | flying 0.19 / 0.06 |
| water | 3 (coastal and pelagic apex) | 2 | fish 12, shore 6, waterbirds 9 (x1.5); pelagic 2 | ocean 0.10 / 0.07, lake 0.10, river 0.12 |
| caverns | 3 | 2 | grazer 12, land prey 10, shore 8, birds 12 (x2) | cav1-3 0.15-0.16 / 0.06-0.09 |

- An apex share of 0.06-0.07 at 8-14 surface waves a season (ECO2-G) is about one apex wave a season (0.5-1.0).
- Flying stays at 19% even at prey x5: a flying roster holds an apex and 1-2 raptors against 1-4 birds. Lower needs a slot change
  (RP 1-1).
- Savage maps run higher (land 0.23 / apex 0.11, ocean 0.13): two apex slots (wiki: 2 LP groups) plus animal-person hunters.
- Structural, not ladder: cavern pools 0.33 (one apex over vermin fish), magma sea 0.23 (fire imp over magma crab).
- Full search grid in analyze22.out section 2.

## 3. Flying apex and flying animal people

- Flying apex present on 100% of calm flying rosters (v21: 0%): BIRD_EAGLE 325, BIRD_OWL_GREAT_HORNED 285, BIRD_OSPREY 215,
  BIRD_OWL_SNOWY 55 of 880. BENIGN cleared (eagle, osprey, snowy owl are BENIGN). Savage adds the giant raptors, Quetzalcoatlus,
  Sinopterus and Rhamphorhynchus. The vulture is excluded (scavenger set).
- Insect men and bird men: on **0 of 880** savage flying rosters in v21, **880 of 880** in v22 (RAVEN_MAN, ALBATROSS_MAN,
  PARAKEET_MAN, BAT_MAN, WREN_MAN...), eaten by a unit edge on all 880. Same principle as land: on 866 of 880 savage land rosters
  (v21: 148). Rule: the flying apex may take a flying sentient (land: AL/AW apexes, unchanged); a prey-guild animal person takes
  the new SNP slot, an attacker one the SN slot; animal people attack by their root guild.

## 4. Pack-mass floor 5%, sneak bonus at 25%

Sneak-bonus edges (hunting group mass >= 25% of the prey's), v22 calm: land 87%, flying 89%, ocean 90%, lake 92%, river 96%,
caverns 97-100%. Savage land 87%. So the flag marks almost every edge; the 13% without it are the stretch hunts (5-25%):
small packs or lone hunters on large prey. The tool would give SNEAK to the hunters on flagged edges.

## 5. Vegetation link, and what a 5% floor costs

**Rule:** a herbivore (grazer / other land prey / shore animal, not a carnivore, prey tier) with no predator in its pool is still
linked, to one plant node, when the embark's vegetation index for its own biomes is at least `20 + 15 x log10(mass / 100 kg)`
(100 kg 20, 1 t 35, 5 t 45, 40 t 59). Its link weight (0.05) sits below any animal edge, so a hunted herbivore is always
preferred. Index per biome is approximated here (forest 85, wetland 75, taiga 70, grassland 50, savanna 45, shrubland 30,
tundra 15, mountain 10, desert 5, cavern 40; EXTERNAL knowledge of DF's biome rules). **In-tool survey needed:** the mean
`vegetation` of the embark's region tiles (`world_data.region_map[x][y].vegetation`, 0-100) and the grass-tile share of the
surface (`block_square_event_grassst` amounts), read once at load.

Big herbivores on calm land rosters (on roster / pool cells): ELEPHANT v21 3/160 -> v22 10/160; RHINOCEROS 8 -> 20/240
(3 by vegetation alone); WATER_BUFFALO 40 -> 80/80; GIRAFFE 69 -> 79/240. Most of the gain is the 5% floor; the vegetation
link adds the few with no predator at all (rhinoceros 3, savage MOOSE, GIANT_ELK, Platybelodon). GIANT_ELEPHANT (40 t) and
JURASSIC_BRACHIOSAURUS stay at 0 of 160 / 400: both HAVE edges (giant dingo, hyena, lion; T. rex, allosaurus), but every edge
carries the size preference's floor weight, so the uniform pick almost never takes them. They are possible, not forbidden.

**Downsides of 5% vs 20%** (v22 vs v22_floor20, calm unit edges): 28,632 vs 26,176 edges; the extra 2,616 (9%) have a hunting
group of 5-20% of the prey's mass. 416 of them are on prey of a tonne or more (JAGUAR x HIPPO 113, MONITOR_LIZARD x GIRAFFE 53),
549 on 100 kg - 1 t (RATTLESNAKE / BOBCAT / HONEY BADGER x WILD_BOAR, JACKAL x GIANT TORTOISE), 1,651 under 100 kg (mostly
small raptors on big birds: PEREGRINE x ALBATROSS 179, BARN OWL x WHITE STORK 128, KESTREL x STORK 108). On savage maps 4,059
(10%), 1,439 on prey of a tonne or more. CAL measured what DF does in each band (30,000 ticks, 2 reps):

| hunters' mass / prey's | cell-reps | prey killed | hunters lost |
|---|---|---|---|
| < 5% (3-5 wolves on elephants) | 4 | 0 | 4 |
| 5-20% | 10 | 15 | 6 |
| 20-50% | 20 | 8 | 0 |
| >= 50% | 10 | 4 | 1 |

So the 5-20% band is where DF's kills AND losses concentrate (1.5 kills and 0.6 hunters lost per cell-rep): a 5% floor admits
productive but costly hunts and many odd-looking pairs (snakes and bobcats on boar, small falcons on albatross); below 5% DF
only loses hunters, which the floor removes. Unintended consequences to watch in the season test: predator attrition, and
written relations a player may read as absurd (a kestrel on a stork).

## 6. GOOD / EVIL (and the FANCIFUL-only yeti and sasquatch)

8 GOOD and 23 EVIL species with BIOMEs load from the raws (GOBLIN, the 24th EVIL, has none). Admitted on matching regions
(`align` good / evil), and underground always (the audit: alignment only limits taming there). Sentient GOOD/EVIL wildlife
(ogres, trolls, blendecs, blizzard men, harpies, nightwings) hunt by guild (a 'monster' overlay), unlike civ races.

| token | tag | guild | mass (cm3) | group | BIOMEs | sentient | SAVAGE | vermin | on v22 rosters (config layer: rosters with it / pool cells) |
|---|---|---|---|---|---|---|---|---|---|
| FAIRY | GOOD | VB | 100 | 1:1 | ALL_MAIN |  |  | VB | good flying 155/880 |
| GNOME_MOUNTAIN | GOOD | PL | 15000 | 5:10 | MOUNTAIN | yes |  |  | never in a pool on these embarks |
| GORLAK | GOOD | PL | 50000 | 1:1 | SUBTERRANEAN_CHASM | yes |  |  | evil cav1 65/80; evil cav2 24/80; evil cav3 33/80; evil_savage cav1 70/80; evil_savage cav2 19/80; evil_savage cav3 27/80; good cav1 65/80; good cav2 21/80; good cav3 26/80; savage cav1 68/80; savage cav2 31/80; savage cav3 30/80 |
| MERPERSON | GOOD | FC | 70000 | 3:6 | ANY_OCEAN | yes |  |  | good ocean 320/320 |
| PIXIE | GOOD | VB | 10 | 100:200 | ALL_MAIN |  |  | VB | good flying 155/880 |
| SATYR | GOOD | PL | 60000 | 3:5 | FOREST_TEMPERATE_BROADLEAF,FOREST_TROPICAL_CONIFER,FOREST_TROPICAL_DRY | yes |  |  | good land 160/160 |
| UNICORN | GOOD | GZ | 600000 | 3:7 | FOREST_TAIGA,ANY_TEMPERATE_FOREST,ANY_TROPICAL_FOREST,SHRUBLAND_TEMPER |  |  |  | good land 104/560 |
| WAMBLER_FLUFFY | GOOD | VG | 2000 | 1:1 | ANY_LAND |  |  | VG | good land 274/880 |
| BEAK_DOG | EVIL | AL apex | 150000 | 3:7 | MARSH_TEMPERATE_FRESHWATER,MARSH_TEMPERATE_SALTWATER,MARSH_TROPICAL_FR |  |  |  | evil land 12/80; evil_savage land 15/80 |
| BLENDEC_FOUL | EVIL | AL apex | 60000 | 3:5 | FOREST_TEMPERATE_BROADLEAF,FOREST_TROPICAL_CONIFER,FOREST_TROPICAL_DRY | yes |  |  | evil land 158/160; evil_savage land 2/160 |
| BLIND_CAVE_OGRE | EVIL | AL apex | 7000000 | 1:3 | SUBTERRANEAN_CHASM | yes |  |  | evil cav2 15/80; evil cav3 36/80; evil_savage cav2 21/80; evil_savage cav3 40/80; good cav2 17/80; good cav3 45/80; savage cav2 16/80; savage cav3 40/80 |
| BLIZZARD_MAN | EVIL | AL apex | 300000 | 1:1 | GLACIER,TUNDRA | yes |  |  | evil land 160/160; evil_savage land 1/160 |
| BLOOD_MAN | EVIL | AL apex | 70000 | 2:5 | SUBTERRANEAN_CHASM |  |  |  | evil cav3 41/80; evil_savage cav3 40/80; good cav3 38/80; savage cav3 44/80 |
| CAVE_DRAGON | EVIL | AL apex | 15000000 | 1:1 | SUBTERRANEAN_CHASM |  |  |  | evil cav3 10/80; evil_savage cav3 5/80; good cav3 9/80; savage cav3 7/80 |
| CREEPING_EYE | EVIL | PL | 20000 | 10:20 | SUBTERRANEAN_CHASM |  |  |  | evil cav3 73/80; evil_savage cav3 77/80; good cav3 70/80; savage cav3 72/80 |
| CREEPY_CRAWLER | EVIL | VG | 1000 | 1:1 | SUBTERRANEAN_CHASM |  |  | VG | evil cav3 80/80; evil_savage cav3 80/80; good cav3 80/80; savage cav3 80/80 |
| GNAT_BLOOD | EVIL | VI | 10 | 100:200 | ANY_POOL |  |  | VI | evil flying 23/80; evil_savage flying 12/80 |
| GNOME_DARK | EVIL | PL | 15000 | 5:10 | MOUNTAIN | yes |  |  | never in a pool on these embarks |
| GRIMELING | EVIL | AW apex | 70000 | 1:1 | SWAMP_TEMPERATE_FRESHWATER,SWAMP_TEMPERATE_SALTWATER,SWAMP_TROPICAL_FR |  |  |  | evil land 3/80; evil_savage land 6/80 |
| HARPY | EVIL | RP | 60000 | 2:3 | SHRUBLAND_TEMPERATE,SAVANNA_TEMPERATE,GRASSLAND_TEMPERATE,SHRUBLAND_TR | yes |  |  | evil flying 640/640; evil_savage flying 89/640 |
| MANERA | EVIL | PL | 60000 | 1:1 | SUBTERRANEAN_CHASM | yes |  |  | evil cav2 20/80; evil_savage cav2 27/80; good cav2 22/80; savage cav2 21/80 |
| NIGHTWING | EVIL | RP | 120000 | 1:1 | ANY_DESERT | yes |  |  | evil flying 80/80; evil_savage flying 6/80 |
| OGRE | EVIL | AL apex | 6000000 | 1:3 | SHRUBLAND_TEMPERATE,SAVANNA_TEMPERATE,GRASSLAND_TEMPERATE,SHRUBLAND_TR | yes |  |  | evil land 402/560; evil_savage land 4/560 |
| RAT_DEMON | EVIL | VG | 300 | 1:1 | NOT_FREEZING |  |  | VG | evil land 159/800; evil_savage land 149/800 |
| REACHER | EVIL | ML | 70000 | 1:1 | SUBTERRANEAN_CHASM |  |  |  | evil cav2 32/80; evil cav3 22/80; evil_savage cav2 31/80; evil_savage cav3 18/80; good cav2 28/80; good cav3 19/80; savage cav2 30/80; savage cav3 27/80 |
| SASQUATCH | FANCIFUL | AL apex | 300000 | 1:1 | ANY_TEMPERATE_FOREST,FOREST_TAIGA |  | yes |  | evil_savage land 13/240; savage land 13/240 |
| SEA_MONSTER | EVIL | AW apex | 8000000 | 1:1 | ANY_OCEAN |  |  |  | evil ocean 48/320; evil_savage ocean 35/320 |
| SPIDER_PHANTOM | EVIL | VG | 500 | 1:1 | ANY_TEMPERATE_FOREST,ANY_TROPICAL_FOREST |  |  | VG | evil land 28/160; evil_savage land 27/160 |
| STRANGLER | EVIL | AL apex | 40000 | 1:3 | FOREST_TROPICAL_MOIST_BROADLEAF |  |  |  | never in a pool on these embarks |
| TROLL | EVIL | AL apex | 250000 | 1:1 | SUBTERRANEAN_CHASM | yes |  |  | evil cav1 73/80; evil cav2 62/80; evil cav3 40/80; evil_savage cav1 73/80; evil_savage cav2 54/80; evil_savage cav3 35/80; good cav1 72/80; good cav2 59/80; good cav3 31/80; savage cav1 76/80; savage cav2 59/80; savage cav3 36/80 |
| WOLF_ICE | EVIL | AL apex | 50000 | 3:7 | GLACIER,TUNDRA |  |  |  | evil land 43/160; evil_savage land 54/160 |
| WORM_KNUCKLE | EVIL | VG | 1000 | 1:1 | NOT_FREEZING |  |  | VG | evil land 169/800; evil_savage land 140/800 |
| YETI | FANCIFUL | AL apex | 300000 | 1:1 | MOUNTAIN,GLACIER,TUNDRA |  | yes |  | evil_savage land 14/160; savage land 28/160 |

## 7. Fishers

BEAR_GRIZZLY, BEAR_BLACK, TIGER, JAGUAR (apexes; the raccoon is prey-tier and cannot take fish under the tier rule; the polar bear
hunts seals already) join the lake/river/ocean webs where their land biome meets the water, with edges to fish, shore animals and
waterbirds; reach is `untested` (the tool writes swim flags; HR: a swimming, water-breathing wolf attacked pike twice, 0 kills).
**Lake apex present: 50% (v21) -> 100% (v22)**: jaguar 80, black bear 20, grizzly 19 of 160 lake rosters; river 72 fishers
on 240; 363 fisher -> fish edges in all.

## 8. Vermin links from DF's GOBBLE tokens

The raws carry GOBBLE_VERMIN_CLASS on 15 creatures, all EDIBLE_GROUND_BUG (fowl, kiwi, hedgehog, pangolin and their giant/man
versions); 4 vermin carry the class (THRIPS, ROACH_LARGE, BEETLE, ANT); no creature carries GOBBLE_VERMIN_CREATURE. v22 gives the
gobblers stock edges to exactly those vermin (they gain vermin links they lacked) and labels every vermin link:

| config | vermin links | native (DF already does it) | write (tool writes GOBBLE_VERMIN_CREATURE on the consumer) | vermin on vermin (tool bookkeeping) | writes per roster |
|---|---|---|---|---|---|
| v22 | 20,698 | 40 (0.2%) | 19,058 (92%) | 1,600 (8%) | 6.4 |
| v22_savage | 29,929 | 19 | 28,310 (95%) | 1,600 (5%) | 9.6 |

Native pairs: PANGOLIN, BIRD_KIWI, BIRD_TURKEY x BEETLE. So DF's own tokens cover almost nothing: the vermin web depends on the
tool writing GOBBLE_VERMIN_CREATURE (about 6-10 consumer -> vermin writes per roster), which the vermin block must show DF acts on.
