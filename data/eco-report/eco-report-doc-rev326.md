# ECO: how DF wildlife really behaves, and what it means for seasonal-wildlife

Oct 1, 2026 · @Nathaniel Cannon

## Summary

In DF 53.16, wild animals hunt only when a predator relation is written, and only a non-BENIGN animal acts on it. Everything else about predation follows from that rule. Over 300 cells and 10 spawn-time runs, with one or two replicates, tested it and the questions below on the rig on 29–30 Sep 2026. The one refinement: DF itself relates every unit that isn't flagged wild (dwarves, livestock, placed animals, and groups the tool releases) to each new wild arrival, so placed hunters attacked native wildlife the test never related them to (RELS).

- **No relation, no hunting.** 0 attacks in 48 predator pairs over 3,000 ticks. With the relation written, every large predator attacked. A coyote, which is not a LARGE\_PREDATOR, also killed deer. DF does write them itself, but on the surface only from non-wild units toward wild arrivals (RELS).
- **BENIGN is the switch, not LARGE\_PREDATOR.** A wolf made BENIGN never attacked. Deer made non-BENIGN killed 2 wolves, and capybaras killed 5 of 5 wolves.
- **Amphibious predators cross the shoreline; aquatic ones never leave the water.** Alligators and saltwater crocodiles killed land prey from the water. Sharks and lampreys made 0 attacks on land prey.
- **Nothing in DF eats remains,** but the tool can do it itself: walking scavengers to corpses with a full path and deleting the corpses works and survives a save and reload.
- **Leaders hold groups together and protect prey.** A led herd spread 2–4 tiles against 52 without a leader, and took 1 attack from wolves against 88.
- **FREQUENCY is a proportional lever.** Wave shares came out 61 / 24 / 13% for FREQUENCY 100 / 50 / 25. NO\_SPRING set at run time stops a species; UBIQUITOUS set at run time does nothing.
- **An emptied population entry stops a species; a replacement takes over within \~2,000 ticks.** Watch the entry's quantity: DF never sets the extinct flag.
- **Curious beasts leave.** Placed bears, raccoons and polar bears left within 3,000 ticks, unless their CURIOUS\_BEAST flags were turned off.
- **Fortress-map water is shallow.** OCEAN2's ocean is 1–2 levels deep and LAKE is 91% one level, so column depth cannot separate deep-ocean species from shallow ones.
- **Animal-vs-animal combat alerts can be filtered safely.** Fights that involve dwarves keep their alert.
- **Group size drives kills, not prey size.** Seven wolves and ten hyenas killed elephants; lone wolves did nothing even to deer. Over 30,000 ticks, bigger and slower prey died more often (CAL, PK).
- **Lone hunters need dense prey.** Spread out, they rarely meet any: 2 of 16 unchanged runs made a kill (STL, STL2). Among 48 prey, the skill package lifted a cougar's kills from 14 to 29 over 10 seasons each (LONE10, p = 0.025), mostly on native animals.
- **Sharks take swimming waterbirds**, 5 of 6 ducks in both replicates, but only in the water (WB).
- **BENIGN predators need it cleared.** An orca with BENIGN made 0 attacks on seals; cleared, it killed 4 of 8 (HO).
- **DF never pairs surface wild with surface wild.** It aims citizens, livestock and placed units at each new arrival; every surface hunt between wild animals needs the tool's write (RELS, RELS2b).
- **Savage giant packs take megafauna.** Ten giant hyenas killed both elephants in every run, and four giant saltwater crocodiles killed both hippos (GPK).
- **A leader holds flocks and schools too.** Led flocks and schools held to 5–30 tiles, against 100–150 without a leader; led orca pods were half as wide (COH).
- **One fixed value moves the map: the predator ladder.** At ×0.5 predators fall to about 2% of land animals. Cadence, nudge, pack-mass floor, sneak bonus and the ×3 pack bonus showed no effect once cell order was controlled (SW1–SW7).
- **The apex FREQUENCY doesn't bring apexes.** 0–3 apex arrivals per season at any setting. Apexes have to be placed or stocked (S8, SW4).
- **DF never draws a SAVAGE species onto a calm map,** even with its population entry added (INV2). Add invasive has to place them.
- **The tool's scavenging pass clears carcasses on land and in water** within about 2,400 ticks when the tool is on (SCV2b).
- **Flags don't start cavern invasions.** Two seasons with the caverns discovered and irritation pinned raised none, even with animal people present (E23e). A halved cavern gate brings no extra traffic (T9c).

v6.9 (released 30 Sep) fixed the ecology write: it now checks reach, arms any non-BENIGN carnivore. Builder v2.2 has been run offline, and tool v7.0 is built on a branch but not yet deployed; in v7.0 the tool's own season deal overrides NO\_\<season>. The next steps are in the tracker at the end.

## How the suite ran

Each cell placed two groups of wild animals side by side, stepped the game 3,000 ticks (CAL and STL 30,000; LONE one season, 100,800), read who attacked and killed whom, and cleared the map for the next cell. Blocks of cells ran in one load of a test fort that was never saved.

- **Placement.** Species were placed regardless of biome: the question was how two groups behave once together, not whether DF would bring them. Usually 6 predators and 10 prey, 10 tiles apart, at least 30 tiles from any dwarf. Boundary tests put both groups on the same shore, one in the water and one on land.
- **A kill** is a Death incident whose killer and victim were both placed. **An attack** is one DFHack UNIT\_ATTACK event. Native animals and cavern fights are excluded.
- **Arms.** Most pairs ran twice: DF on its own, and with the predator relation written, the way the tool's ecology job writes it.
- **Forts.** CTRL (land), LAKE (freshwater), OCEAN2 (ocean shelf), BOATS (caverns), RIVER4 (river) and the fresh test embarks FPS2E1–E6 (1×1 to 6×6).
- **Spawn-time questions** used the existing experiment driver: CTRL with the tool disarmed, every land species at FREQUENCY 1 except those under test, the surface gate released every 1,500 ticks, and DF's own waves counted.
- **Desk work** covered the wiki's definition of every token (never inferred from the name), a census of the 967 vanilla creatures (363 of them wildlife), an audit of the tool's classification, and a simulation of the proposed roster rules over 68,000 generated webs.

The early blocks ran each cell once, so a single cell there is suggestive, not proven; from TV2 on, cells ran 2 replicates (LONE 5). The pattern across the 40-cell matrices is what carries the conclusions.

## Predation: what DF carries out

DF hunts only on a predator relation, written by the tool or, over longer runs, by DF itself (RELP), and any attacker that is not BENIGN carries it out. The LARGE\_PREDATOR tag does not decide it.

&#91;embedded content: ECO P1, CTRL fort, 29–30 Sep 2026 · 6 predators vs 10 prey placed 10 tiles apart, 3,000 ticks, 1 replicate per cell\]

- **DF alone never hunted.** 0 attacks in the 40 predator × prey pairs, and 0 in 8 predator × predator pairs, wolf packs side by side included.
- **LARGE\_PREDATOR is not needed once the relation is written.** The coyote made 343 attacks on deer. Flipping LARGE\_PREDATOR on a coyote, or off a wolf, changed nothing without the relation.
- **BENIGN blocks it.** The fox made 0 attacks in every cell. A wolf made BENIGN made 0 attacks, against 64 for the control.
- **Prey that is not BENIGN fights back.** Water buffalo killed a lion. Deer made non-BENIGN killed 2 of 6 wolves, and capybaras killed all 5 wolves on the lake shore.
- **AT\_PEACE\_WITH\_WILDLIFE does not stop a written relation:** 328 attacks, 2 kills.
- **CRAZED and OPPOSED\_TO\_LIFE aim wildlife at the fort.** CRAZED deer ignored the rabbits beside them, crossed 30 tiles and killed 3 dwarves.
- **Kills are few for the attacks made:** 0–3 of 10 prey per cell, even at 300 attacks. Most fights end in flight.

This corrects an earlier note that only LARGE\_PREDATOR animals act on the relation. Badgers never acted in that test because they are BENIGN.

## Across the land/water boundary, and the tool's sorting

Amphibious predators hunt across the shoreline in both directions. Aquatic predators take prey only in the water, and land predators never enter it. Up to v6.8 the tool's ecology write got this wrong both ways.

| Predator (where) | Prey (where) | Fort | Killed of 8 | Attacks (predator / prey) |
| --- | --- | --- | --- | --- |
| ALLIGATOR (water) | DEER (land) | LAKE | 5 | 103 / 9 |
| ALLIGATOR (water) | CAPYBARA (land) | LAKE | 5 | 57 / 21 |
| CROCODILE\_SALTWATER (water) | WATER\_BUFFALO (land) | LAKE | 4 | 338 / 27 |
| ALLIGATOR (land) | DEER (land) | LAKE | 2 | 41 / 10 |
| ALLIGATOR (water) | FISH\_PIKE (water) | LAKE | 0 | 7 / 0 |
| FISH\_LAMPREY\_SEA (water) | DEER (land) | LAKE | 0 | 0 / 0 |
| WOLF (land) | FISH\_PIKE (water) | LAKE | 0 | 0 / 0 |
| WOLF (land) | CAPYBARA (water) | LAKE | 0; all 5 wolves died | 20 / 132 |
| LION (land) | CAPYBARA (land) | LAKE | 3; 1 lion died | 77 / 125 |
| SHARK\_BLUE (water) | HARP\_SEAL (water) | OCEAN2 | 4 | 106 / 2 |
| SHARK\_BLUE (water) | HARP\_SEAL (land) | OCEAN2 | 1 | 53 / 0 |
| SHARK\_GREAT\_WHITE (water) | LEOPARD\_SEAL (water) | OCEAN2 | 1 | 25 / 0 |
| SHARK\_TIGER (water) | FISH\_MILKFISH (water) | OCEAN2 | 5; 1 shark died | 24 / 2 |
| SHARK\_BLUE (water) | DEER (land) | OCEAN2 | 0 | 0 / 0 |
| BEAR\_POLAR (land) | BIRD\_PENGUIN (water) | OCEAN2 | 0 | 0 / 0 |

Relation written in every row; without it, every one of these pairs made 0 attacks. Seals fled onto land from the sharks: only 1 of 7 surviving leopard seals was still in the water.

What the tool does with this, from the desk audit of its code against the raws:

- **Before v6.9, water-layer units were left out of the ecology entirely,** so the alligator and crocodile predation above never happened under the tool. Its own notes also disagree on whether lake species are water-layer or surface.
- **Before v6.9, ocean species drawn from surface entries counted as land.** The write paired the 12 ocean large predators against every land animal, and shark × deer does nothing.
- **Before v6.9, the write ignored the tool's own `eats()` rules.** Only 42% of the 2,599 pairs it would write between co-occurring natural species pass them: 46% fail habitat reach, 198 fail on size.
- **Habitat itself is classified correctly.** No species whose raws say water is filed as land.

## Every layer: caverns, cavern pools, river, ocean, lake

The surface rules hold on every water body. Underground, some species fight with no relation written and others do not, so the tool keeps writing cavern relations. Each cell: 5 predators and 8 prey, 3,000 ticks, 1 replicate, counted among the placed animals only.

| Layer (fort) | Pair | DF alone | Relation written |
| --- | --- | --- | --- |
| Cavern 1 (BOATS) | troll × gorlak | 143 / 141 attacks, 0 kills | 4 trolls and 5 gorlaks dead |
| Cavern 1 | troll × elk bird | 1 kill | 4 kills |
| Cavern 1 | giant cave toad × elk bird | 0 | 2 kills |
| Cavern 2 | troglodyte × elk bird | 101 attacks, 2 kills | 1 kill |
| Cavern 2 | voracious cave crawler × crundle | 8 of 8 killed | 7 of 8 |
| Cavern 3 | jabberer × reacher | 0 | 7 of 8 killed |
| Cavern 3 | blind cave ogre × rutherer | 0 | 3 killed |
| Cavern pool | cave crocodile (pool) × elk bird (land) | 1 kill | 5 of 8 |
| Cavern pool | giant olm (pool) × crundle | 0 | 8 of 8 |
| Cavern pool | pond grabber (stays wet) × gorlak | 0 | 1 attack |
| River (RIVER4) | bull shark × pike | 0 | 8 of 8 killed |
| River | sea lamprey × pike | 0 | 590 attacks, 0 kills |
| River | alligator (water) × deer | 0 | 1 kill |
| River | wolf with water-breathing and swimming × pike | 0 | 2 attacks, 0 kills |
| Ocean (OCEAN2) | orca × harp seal | 0 | 0; BENIGN cleared: 4 of 8 killed |

- **Native cavern fighting depends on the species or the spot.** Trolls, gorlaks (BENIGN and CAN\_SPEAK), troglodytes and cave crawlers fought unprompted. Jabberers, blind cave ogres and cave toads did not. No single token separates the two sets. BENIGN on a troll did not stop it (85 attacks), unlike the BENIGN wolf on the surface (0).
- **Cavern pools follow the surface water rules.** Amphibious predators take land prey from the pool; aquatic ones never leave the water. So the tool's reach rules apply underground unchanged.
- **BENIGN blocks even a curated apex.** The orca is BENIGN in the raws and ignored written seals until the flag was cleared. The apex boost has to clear BENIGN, as on land.
- **The sea lamprey attacks but does not kill** in 3,000 ticks. It should not count as a lake or river apex.
- **Land predators don't fish, even with water-breathing.** Wolves already swim in the raws. Given water-breathing they made 2 attacks on pike here and 1 per replicate in FISH, with no kill; swimming alone made none (REACH).
- **Leaders hold groups together on every layer.** A led group's spread fell from 33–47 tiles to 2–9 for gorlaks, troglodytes, pike, milkfish and carp. Only on land did cohesion protect prey: tiger sharks killed 5, 10 and 1 milkfish (no leader, lowest id, largest male).
- **Remains are never touched underground or in water either.** No corpse was held or moved beside trolls, giant rats or a pool crocodile. The cavern walk-and-eat failed because the straight path hit rock (0 of 5 trolls arrived), so v6.9's scavenging job gives a path only along a clear line.
- **Vermin cells were empty on every layer** (0–2 vermin near the spot). The rerun at the densest spots was empty too: on the surface those are bumblebee and termite colonies (14,000–19,000 each), which nothing hunts, and caverns hold at most 2 vermin near any spot. Vermin predation is still untested, so rule C stays bookkeeping. VRM now places loose vermin itself and tests DF's GOBBLE\_VERMIN tokens (research/vermin.md).

## Token census: what the raws hold

The two creature folders define 967 creatures in 45 files, and the census covered every one of them. Of the tokens asked about, 16 appear in no creature definition. Six of those still exist in DF, written by world generators or granted by syndromes.

| Token | Where it exists, if not in a creature's raws |
| --- | --- |
| CRAZED | written into every werebeast by the procedural creature generator |
| SENSE\_CREATURE\_CLASS | written into night trolls by the generator |
| BLOODSUCKER | granted by the vampire curse (a syndrome's CE\_ADD\_TAG) |
| OPPOSED\_TO\_LIFE | granted by undead syndromes (necromancy, animation, evil clouds) |
| NATURAL\_ANIMAL | DF's flag name for \[NATURAL\], used in syndrome conditions |
| CANNOT\_CLIMB | only an announcement type |
| GRAZER, MATUTINAL, VIEWRANGE | nowhere (GRAZER occurs only inside STANDARD\_GRAZER; VIEWRANGE defaults to 20) |
| GOBBLE\_VERMIN\_CREATURE, LAYS\_UNUSUAL\_EGGS, NO\_SUMMER, VERMINHUNTER, HAUL\_REFUSE, bare CURIOUSBEAST, MISCHIEVIOUS | nowhere (the raws spell MISCHIEVOUS, once) |

&#91;embedded content: data/eco-desk/v2/tokens (DwarfCron) · DF 53.16 vanilla raws, 363 wildlife species, resolved per creature\]

- **Aquatic core.** AQUATIC, IMMOBILE\_LAND, NO\_DRINK and UNDERSWIM travel together on 77 species. 75 of them are also CANNOT\_JUMP, and none is diurnal.
- **Vermin body.** Every vermin token sits inside SMALL\_REMAINS, and VERMIN\_FISH sits inside FISHITEM.
- **Cavern.** LOW\_LIGHT\_VISION sits inside UNDERGROUND\_DEPTH. ODOR\_LEVEL, SMELL\_TRIGGER, EXTRAVISION and NOBREATHE mark elemental men, the blood man and fire creatures.
- **Grazers.** 25 of 32 STANDARD\_GRAZER species carry VISION\_ARC 50:310, the only VISION\_ARC value in the raws.
- **Thieves.** 11 of 12 LOOSE\_CLUSTERS species are CURIOUSBEAST\_\* thieves, so that token marks thieves more than a spacing style.
- **Foragers, spiders, beasts of burden.** GOBBLE\_VERMIN\_CLASS and ROOT\_AROUND are the same 7 species. WEBBER and WEBIMMUNE are the 4 spiders. PACK\_ANIMAL and WAGON\_PULLER are horse, water buffalo, yak and muskox.
- **LARGE\_PREDATOR belongs to no block.** Its best overlap is J = 0.26, it never co-occurs with BENIGN, and 26 of the 60 wild predators carry neither CARNIVORE nor BONECARN.
- **Activity.** Every creature carries exactly one activity pattern.

**Values** (the full distributions are in the data files):

- **FREQUENCY.** 174 of 363 wild species set it. Low explicit values mark predators and big prey: the median for LARGE\_PREDATOR is 5. An explicit 100 marks vermin and birds.
- **POPULATION\_NUMBER.** Set on every wild species: 15:30 for most animals, 250:500 for vermin, 2:3 to 10:20 for land predators.
- **CLUSTER\_NUMBER.** Land predators are mostly 1:1, grazers 3:7, shore animals 5:10, vermin swarms 100:200.
- **PRONE\_TO\_RAGE** is on 4 species, none of them predators. **SMELL\_TRIGGER** is always 10000. **GRASSTRAMPLE** is 0 on every BENIGN species that declares it.
- **VIEWRANGE** is never set, so every creature sees 20 tiles. The token effects below test what changing the values does.

## Token effects

Of the \~95 tokens asked about, three flags and one value change wildlife behaviour measurably within 3,000 ticks: BENIGN, CRAZED, OPPOSED\_TO\_LIFE, and PRONE\_TO\_RAGE at 25 or more. The CURIOUS\_BEAST flags decide whether an animal stays. Two spawn flags change what DF draws: NO\_\<season> works when set at run time, UBIQUITOUS does not.

| Token flipped (species) | Setting | Result | Control |
| --- | --- | --- | --- |
| BENIGN on (WOLF, relation written) | behaviour | 0 attacks | 64 attacks, 1 kill |
| BENIGN off (DEER, with written WOLF) | behaviour | deer 46 attacks, 2 wolves killed | deer 3 attacks |
| CRAZED on (DEER beside RABBIT) | behaviour | deer went to the fort, killed 3 dwarves, all died | — |
| OPPOSED\_TO\_LIFE on (DEER beside RABBIT) | behaviour | 16 attacks on dwarves, 4 of 6 deer killed | — |
| FLEEQUICK on (DEER, written WOLF) | behaviour | 2 attacks on deer; TV2: 3 and 158, not repeated | 64 attacks |
| AT\_PEACE\_WITH\_WILDLIFE on (WOLF, written) | behaviour | 328 attacks, 2 kills: no protection | 64 attacks, 1 kill |
| LARGE\_PREDATOR on COYOTE / off WOLF (no relation) | behaviour | 0 attacks either way | 0 attacks |
| PRONE\_TO\_RAGE = 1 / 25 / 50 / 100 (DEER, written WOLF) | behaviour | deer attacks 0 / 17 / 81 / 98; at 100, 4 of 6 wolves killed | — |
| AMBUSHPREDATOR on, NATURAL\_ANIMAL off (WOLF) | behaviour | 0 attacks | 0 attacks |
| MEANDERER off (DEER) / LOOSE\_CLUSTERS on (KANGAROO) | movement | spread 63 vs 44 / 43 vs 36 tiles; TV2: MEANDERER off 72 and 65 vs 39 and 42 (repeated), LOOSE\_CLUSTERS no effect | — |
| CURIOUS\_BEAST\* off (BEAR\_GRIZZLY) | presence | 0 of 6 left the map | 6 of 6 left |
| NO\_SPRING on (KANGAROO, FREQUENCY 100, spring) | spawn | 0 of 19 waves | 61% of waves |
| UBIQUITOUS on (a FREQUENCY-5 species, others 25) | spawn | 0 of 13 and 0 of 23 waves | — |

&#91;embedded content: ECO TV2, CTRL, tool off, 30 Sep 2026 · 6 WOLF written against 10 DEER, 2 replicates · data/eco-desk/findings.md (TV2)\]

Second replicates (TV2, one shared spot): MEANDERER off repeated (deer scattered over 72 and 65 tiles against 39 and 42). FLEEQUICK did not (3 and 158 attacks), and LOOSE\_CLUSTERS made no difference (37–39 against 41–42 tiles). A giant fox, BENIGN in its raws, attacked deer only with BENIGN cleared (2 and 10 attacks, 1 kill).

The desk triage (T0) placed each token by what the wiki documents for fortress-mode wildlife:

- **39 affect behaviour** (hunting, fleeing, movement, detection, fort-directed aggression). **10 affect the spawn pick.** **14 have no documented wildlife effect** (CAN\_SPEAK, PETVALUE, TRAINABLE\_\*, MOUNT, WAGON\_PULLER and the like), and 7 are unclear.
- **16 of the tokens asked about appear in no creature definition, not 9, and 6 of those still exist in play.** The census above lists each and where it comes from (generators, syndromes). Set at run time, two of the six act: the CRAZED and OPPOSED\_TO\_LIFE rows in the table.
- **Values act too, and PRONE\_TO\_RAGE works by dose.** Deer set to 25, 50 and 100 made 17, 81 and 98 attacks on written wolves; at 100 they killed 4 of 6 and lost none. At 1 (the badger's raw value) nothing happened. The two-replicate rerun at one shared spot (TV2) repeated it: at 100 the deer made 98 and 94 attacks and killed 4 of 6 wolves both times. VIEWRANGE also held: deer that see 40 tiles drew 3 and 0 attacks, against 168 and 7 at 5 tiles. A narrow VISION\_ARC did not repeat (5 and 147 attacks). How often each value occurs, and with what, is in the census above. STANDARD\_GRAZER, PRONE\_TO\_RAGE, VIEWRANGE and VISION\_ARC live in the caste's misc fields; AMPHIBIOUS, AQUATIC, SWIMS\_INNATE and CURIOUSBEAST\_\* compile to differently named flags.
- **The activity tokens** (DIURNAL, NOCTURNAL, CREPUSCULAR, ALL\_ACTIVE) are documented for Adventurer mode only.
- **Raw NO\_\<season> flag or the tool: which wins depends on who brings the animal.** DF's own pick honours the flag even when it is set at run time: NO\_SPRING stopped 19 of 19 spring kangaroo waves (T2). Land and cavern arrivals are DF's draws. So a NO\_WINTER bear dealt Winter never comes, and the roster shows a season that stays empty. The tool's own water draws and `call` did not check the flag, so there the tool won. Up to v6.8 the tool never read the flag: 22 NO\_WINTER wild species (both bears, the rabbit) could be dealt Winter. v6.9 moved a forbidden season to the next allowed one. At your ruling v7.0 reverses that: the tool clears NO\_\<season> on the species it manages, so its own deal wins, and restores the flags when switched off. ECO2-W settled it with the natural flag: in Winter a groundhog at FREQUENCY 100 with stock 500 took 0 of 42 and 0 of 44 waves while it kept NO\_WINTER, and 21 of 32 and 19 of 25 with the flag cleared. The raw flag wins unless it is cleared, as v7.0 now does.

## Scavenging

No creature in DF eats or moves remains, but the tool can do it itself: walk the scavenger to the corpse with a full path, then delete the corpse. Both steps worked, and the result survived a save and reload.

1. **Nothing scavenges on its own.** Six fresh kangaroo corpses, with 6 of a candidate beside them for 4,000 ticks: vulture, hyena, black bear, raccoon, wolf, and deer as control. None was moved or held. The wiki documents no corpse-eating in any mode.
2. **A labor does not help.** Setting HAUL\_REFUSE on wild wolves gave them no job.
3. **A destination alone does not move a wild unit.** Setting only the path's destination, with or without a goal, moved no hyena.
4. **A full path does.** Given a tile-by-tile path, 3 of 6 hyenas stood within 3 tiles of the corpses 300 ticks later, from 20 tiles away. Deleting the corpses within 2 tiles of them removed 6 of 6.
5. **The deletion is safe.** Teleport, eat, save, reload: the corpses stayed gone, the fort loaded, and the hyenas were alive.

Who should scavenge is a policy choice, since no raw token marks scavengers. The pinned rule ("BONECARN, or CARNIVORE and not small") misses the vulture, buzzard, jackal and hyena. The desk proposal is 23 candidates: BONECARN, plus the CURIOUSBEAST\_EATER food thieves, plus species whose descriptions say carrion or scavenging (vulture, buzzard, black bear, longfin mako). Only 4 of them are LARGE\_PREDATOR, so scavenging has to be the tool's own walk-and-delete, never a DF relation.

## Groups: leaders, curious beasts, groups at once

A leader keeps a group together, and a led herd was barely attacked. Which member leads made no consistent difference; v7.0 makes the largest adult male the leader. On 5×5 and 6×6 maps a groups-at-once limit of √(embark) + 1 adds about one group; on smaller maps DF never had more groups on the map than the old limit of 3, so raising it changed nothing.

| Group, 3,000 ticks | No leader | Lowest id leads (the tool's rule) | Largest male leads |
| --- | --- | --- | --- |
| 10 DEER, spread in tiles | 52.5 | 1.7 | 3.6 |
| 8 WOLF, spread in tiles | 45.6 | 10.0 | 3.4 |
| 10 DEER + 6 written WOLF: attacks on deer | 88 | 1 | 1 |
| same: deer killed | 1 | 0 | 0 |

A largest-male rule is cheap to write, and it holds a group together as well as the lowest-id rule does. v7.0 now implements it: the largest adult male leads, and a living leader keeps the role. Whether size helps a group in a fight was not tested.

&#91;embedded content: ECO L1 (CTRL), HC1 and HC2 (BOATS caverns), HR (RIVER4), HO (OCEAN2), HL (LAKE) · 29–30 Sep 2026 · data/eco-desk/findings.md\]

**Curious beasts come to steal, then leave.** The CURIOUS\_BEAST tokens do send the animal to the fort's items, as you expected. On BOATS a placed raccoon walked about 35 tiles to the wagon pile (306 items) and took a rope. Its leave countdown then dropped from 199,600 to 0, and it walked off the map edge with the rope, out of the world. That is DF's thief visit: arrive, take, go.

Placed alone on CTRL, 6 of 6 grizzlies, 6 of 6 black bears and 6 of 6 raccoons were gone within 3,000 ticks. Polar bears left the shore mid-hunt. Resetting the leave countdown every 300 ticks did not hold them (4 of 4 raccoons left). Clearing the CURIOUS\_BEAST, \_EATER and \_GUZZLER flags did (0 of 6 grizzlies and 0 of 4 raccoons left).

**'As residents' means animals meant to stay on the map for their season**, whether the tool placed them or DF drew them. Both kinds steal and leave while the flags are on. v6.9 adds `curious TOKEN resident|thief`: *resident* clears the flags species-wide while the tool runs and restores them when it stops; *thief* keeps DF's visit.

**Groups at once versus embark size (ECO2-G).** Fresh 7-dwarf embarks from 1×1 to 6×6, the tool on with the preset, 40,000 ticks, 2 replicates per arm. A group is one species from one population among the live wild animals, counted every 1,500 ticks.

&#91;embedded content: ECO2-G, fresh 7-dwarf embarks FPS2E1–E6, tool on with the preset, 40,000 ticks, 2 replicates · data/eco-desk/findings.md\]

| Embark | Land limit: default / √ + 1 | Surface groups at once, default | Surface groups at once, √ + 1 | Surface waves, default / √ + 1 | Ticks/s, default / √ + 1 |
| --- | --- | --- | --- | --- | --- |
| 1×1 | 3 / 2 | 1.98 | 1.77 | 3.0 / 4.0 | 507 / 530 |
| 2×2 | 3 / 3 | 1.98 | 2.09 | 4.5 / 4.0 | 466 / 613 |
| 3×3 | 3 / 4 | 1.76 | 1.94 | 3.5 / 3.5 | 365 / 369 |
| 4×4 | 3 / 5 | 2.71 | 2.60 | 3.5 / 3.0 | 422 / 409 |
| 5×5 | 3 / 6 | 2.16 | **3.28** | 4.0 / 5.5 | 271 / 289 |
| 6×6 | 3 / 7 | 2.69 | **3.46** | 3.0 / 5.0 | 223 / 261 |

The limit binds on big maps. At 5×5 and 6×6 every √ + 1 replicate (3.16–3.81) held more groups than every default replicate (1.77–2.85). Up to 4×4 the two are within noise, and there was no speed cost anywhere. The cavern limit did not bind: cavern groups ran about 5–9 whatever it was set to, because residents and ungated sources count too.

**Who brings the groups.** On land and in the caverns, DF draws every group; the tool only opens or closes the gate (the limit, stock, FREQUENCY, seasons). The tool draws water groups itself (Driver B), and places animals only on a command (`place`). So a higher limit fills only when DF has groups to send. With 2 replicates (ECO2-G) it added about one group at 5×5 and 6×6 and nothing below, at no speed cost.

v6.9 makes √(embark) + 1 the default for land groups at once. On a 1×1 that means 2 rather than 3 (1.77 against 1.98 groups, within noise); `limits land groups N` sets a fixed number instead. v7.0 goes further: land, each water body and each cavern depth get their own limit of floor(√tiles) + 1, counted separately.

## Spawn levers: FREQUENCY, seasons, exhaustion

FREQUENCY sets a species' share of DF's land waves in proportion, NO\_\<season> flags work when the tool sets them, and an emptied population entry stops a species at once.

&#91;embedded content: ECO-F1, CTRL, tool disarmed, surface gate released every 1,500 ticks, 1 replicate · 30 Sep 2026\]

- **FREQUENCY is a balancing lever you can compute with.** Four species at 100, 50, 25 and 12 took shares of 61, 24, 13 and 0%, against 53, 27, 13 and 6% predicted. Emu's expected 2 waves did not come, within the noise of 38 waves. Fliers, caverns and the deep draw from separate pools and were not affected.
- **FREQUENCY works the same way in the caverns, one layer at a time (ECO2-FC).** Each cavern layer draws from its own pool, and the 143 waves split evenly across the three. In cavern 3, blind cave ogres, blood men and cave blobs at FREQUENCY 50, 25 and 12 took 21, 10 and 7 waves: 55, 26 and 18% of the named, against 57, 29 and 14% predicted. In cavern 1 the giant cave swallow at 100 took 42 of 49. The layer is picked first, then the species by FREQUENCY, so the tool's cavern balance can be set per layer.
- **NO\_\<season> set at run time is honoured.** A kangaroo at FREQUENCY 100 with NO\_SPRING took 0 of 19 spring waves, where without the flag it took 61%. The tool can gate seasons with DF's own flags rather than only with stock and FREQUENCY.
- **UBIQUITOUS set at run time is ignored at the pick.** Flagged species at FREQUENCY 5 took 0 of 13 and 0 of 23 waves. The wiki's role for it is worldgen territory.
- **An emptied entry stops the species; its replacement takes over within about 2,000 ticks.** A kangaroo entry of 3 went to 0 when its one wave arrived, and no kangaroo came after, although DF left the extinct flag false. A hook watching the entry then raised wombats, whose first wave came 2,090 ticks later. They took 27 of the next 29 waves. POPULATION\_NUMBER exhaustion should be detected from the entry's quantity, not from the extinct flag.

## Oceans: deep versus shallow

Fortress-map water is 1 to 4 levels deep, and deep columns exist on some maps but not others. So "deep ocean" can key on the map, not the species: draw open-water species rarely unless the map has columns 3 or more levels deep.

| Fort | Water columns | 1 level | 2 levels | 3 levels | 4 levels |
| --- | --- | --- | --- | --- | --- |
| LAKE (freshwater lake) | 31,047 | 91% | 5% | 4% | 0% |
| OCEAN2 (ocean shelf) | 21,328 | 43% | 57% | 0% | 0% |
| BOATS (ocean + salt river) | 36,650 | 41% | 27% | 23% | 9% |

- **Big fish do not suffer in shallow water.** Two whale sharks (20M cm³) and three blue sharks placed in OCEAN2's 1–2-level water were alive, wet and moving 3,000 ticks later.
- **The raws hold no depth token.** UNDERSWIM is on 79 of 83 aquatic creatures. The usable signals are AMPHIBIOUS in an ocean biome (shore dwellers: seals, walrus, crabs), body size (seven ocean species over 1M cm³) and descriptions ("open ocean" only for the swordfish).
- **A rule the tool could apply:** an 'open water' class of ANY\_OCEAN or non-AMPHIBIOUS ocean species over \~1M cm³, drawn at a low weight unless the map has 3+-level columns. Coastal species stay at full weight. A map like OCEAN2 would then carry sharks and seals but rarely whales.

## Combat alerts and the fight log

Animal-vs-animal combat alerts can be dropped safely, and a per-species fight log is cheap. DF's own announcement settings cannot do the first: they switch per report type (43 COMBAT\_\* types), not per who is fighting.

- **The filter** runs every tick and drops each COMBAT alert in which no unit is a citizen, one of the fort's civilisation, or fort-controlled. A COMBAT alert lists its units (`report_unid`), which is what makes this possible.
- **Wild fight, filter off:** 1 alert. **Filter on:** 0 alerts, 3 dropped.
- **Wolves set on dwarves, filter on:** the alert stayed.
- **Save and reload with the filter running:** the fort loaded and play went on. The per-unit combat reports remain in each animal's own log; only the alert button goes.
- **The fight log** takes attacks from DFHack's UNIT\_ATTACK event and deaths from the incident list (killer, victim, cause). It gave every count in this report. Grouped by species pair and time, it is the data for an interaction plot. It is blind to fights in caverns nobody has opened, because DF writes no reports there; deaths still show in the incidents.

## Geography and tag set-groups

The raws hold no geography, so realms must be tool data. Tags do partition wildlife into about 15 guilds the tool can map behaviours onto, each defined by documented tokens alone. Four axes carry the split: aggression, water habit, flight and layer. Activity time only shatters the guilds into one-species cells and has no documented fortress effect.

| Guild | Rule (tokens) | Wildlife | Examples | What the tool would drive from it |
| --- | --- | --- | --- | --- |
| Apex hunter, land | LARGE\_PREDATOR, not AQUATIC/AMPHIBIOUS | 13 | wolf, cougar, lion, grizzly | Armed; pack cohesion if cluster > 1; rare |
| Water apex | LARGE\_PREDATOR and (AQUATIC or AMPHIBIOUS) | 13 | sharks, alligator, saltwater crocodile | Armed, water-reach prey only (needs the realm fix) |
| Ground mesocarnivore | CARNIVORE or BONECARN, not LP, not FLIER | 28 | fox, badger, coyote, bobcat, jackal | **Armable only when not BENIGN** (coyote, jackal, bobcat, lynx); the rest vermin hunting |
| Raptor | FLIER and BONECARN | 11 | eagle, peregrine, owls, kestrel | Vermin hunting; never armed (BENIGN) |
| Thief / scavenger | CURIOUSBEAST\_EATER, \_ITEM or \_GUZZLER | 19 | black bear, raccoon, vulture, mandrill | Scavenging walk-and-delete; leaves the map unless the flags are cleared |
| Grazer herd | STANDARD\_GRAZER | 31 | deer, horse, reindeer, water buffalo | Base prey; herd with a leader |
| Other land prey | BENIGN, not grazer, carnivore, flier or swimmer | 47 | boar, kangaroo, ostrich, elephant | Prey; LOOSE\_CLUSTERS for spacing |
| Shore / semiaquatic | AMPHIBIOUS, or all-water biomes and not AQUATIC | 35 | seals, hippo, capybara, beaver | Shore placement; prey to land and water apex; herd, not school |
| Pelagic | AQUATIC ocean species ≥ 1M cm³ or BEACH\_FREQUENCY | 10 | whale shark, sperm whale, orca, manta | Deep-water class: rare without 3+-level columns |
| Coastal / reef fish | AQUATIC ocean species < 1M cm³ | 29 | nurse shark, stingray, cod, milkfish | Ocean water layer; school |
| Freshwater fish | AQUATIC, lake/river/pool, not ocean | 4 | pike, carp, gar, tigerfish | Lake/river placement; school |
| Waterbird | FLIER, water biome, not BONECARN | 6 | duck, goose, swan, loon | Flock; water-apex prey |
| Land bird | FLIER, no water biome, not BONECARN | 4 | raven, stork, grey parrot | Flock; prey |
| Vermin | any VERMIN\_\* flag | 104 | toad, sparrow, salmon, fly | Stock only (not units): the tool's seven families |
| Cavern fauna | subterranean biomes only | 39 | crundle, cave crocodile, giant rat | By cavern depth; 24 of 55 are LP |

Only the sponge is left unassigned. Overlaps are small and meaningful: the bears are apex and thieves, and the vulture, buzzard and kea are raptors and thieves.

**Realms (real-world knowledge, not the raws).** A realm table assigns the 308 surface species to 13 realms: Nearctic 75, Palearctic 48, Africa 35, Indomalaya 33, Neotropics 27, Australasia 17, Arctic 13, New Zealand 4, Madagascar 3, Antarctic 4, oceanic 55, cosmopolitan 44, DF-invented 24.

- **Gaps are real.** Australasia's only land large predator is the dingo, which does reach temperate grassland. New Zealand, Madagascar and the Antarctic have no armable predator, and Africa has none outside the tropics.
- **Arctic ≠ Antarctic cannot come from DF.** All four 'Antarctic' species (the penguins, leopard and elephant seals) are OCEAN\_ARCTIC in the raws, beside the polar bear. Keeping them apart has to be a tool rule.
- **Across biomes:** a realm roster would filter the region pool and bring absent members in with Add invasive. But Add invasive will not place a species in a biome its raws do not list, so a realm roster outside the realm's home climate needs a new placement path.

## The imposed roster and food-web rules

The rules are sound in intent. As written, they never finish filling their slots, and they demote the classic pack hunters to vermin-eaters. Nine small changes fix that. A prototype built the webs over the raws census: 68,000 of them, for 7 embark types × 7 layers × 4 seasons × 20 seeds, under 34 rule variants.

### Rule by rule

| Rule | Sound? | What goes wrong as written | Fix |
| --- | --- | --- | --- |
| A. Only GIANT and PREDATOR eat non-giant predators | Yes | Either reading gives nearly the same webs (4 of 2,000 differ). Mutual predation appears in 36% of surface and 75% of cavern webs | A predator eats another only if it is at least twice its size |
| B. Small predators eat vermin only | Matches DF, but mis-sized | The tool's size bands (small < 150k cm³) make wolf, dingo, hyena, cougar and cheetah 'small', so B bans them from deer. Their vermin links are ones DF never carries out | Size predators by the predator/prey mass ratio (`eats()`), not fixed bands; B applies to BENIGN small carnivores |
| C. Split bird vermin from flying insects; birds eat insects | Feasible as bookkeeping only | Vermin are not units, so no DF relation can hold this. Without a floor and ceiling, insects hit 0 and stay there | A tool stock transfer each pass (insect abundance down in proportion to bird abundance), with a floor and a ceiling |
| D. Only large (tag AND size) and GIANT predators attack sentients and animal people | Right for fort safety | Tag AND size is nearly empty: only the jabberer qualifies in caverns, so troglodytes and animal-person prey go uneaten in 95% of cav1 webs | By the LARGE\_PREDATOR tag alone, applied as an exclusion in the relation write |
| E. Medium and large predators eat small to medium prey | Mis-stated. Your call: no strict size classes; prey weighted by the eats() mass ratio, none barred | Large prey is eaten by nobody: the 'giant or large prey' slot is filled, then isolated (13% of flying webs are a single stranded species) | Large predators eat medium to large prey |
| F. Pack predators +1 size class | Yes, and it carries the web | Without it, isolated animals rise from 6% to 24% of webs. 'Pack' by cluster size alone includes grazer herds | Pack = not BENIGN, carnivore, cluster > 1; clamp at the top class |
| G. Cavern layers by 'bizarreness' | Feasible, partly native | A bizarre score from raw facts correlates 0.49 with DF's own UNDERGROUND\_DEPTH (means 3.3 / 5.1 / 8.7 at depths 1 / 2 / 3). Cut by score alone, cav2 keeps 5 candidates | Use UNDERGROUND\_DEPTH as the ceiling and the score as a preference: 25 / 32 / 21 candidates |

### The algorithm, steps 0–8

1. **Step 4 never terminates on its own.** No web ever reached its caps, strict or lenient, because the caps span classes that a layer cannot hold (land has no flying-vermin slots). Every web stopped only because nothing more could be added. Required: per-layer caps and a stop when a full pass adds nothing.
2. **'High value' means giants.** Every giant has PETVALUE 500, so the seed was a giant in 75% of land webs and 100% of flying ones. Step 3 then excludes high-value animals, so giants appear only as the seed or its first partner. Required: giants are not 'high value', and the seed must have at least one relation available in its pool.
3. **Animal people crowd the pool.** They are 37–44% of every surface pool, and 30% of predator slots went to sentient species (a grizzly-bear man eating a cougar). Required: sentients never eat.
4. **Only 43% of surface predator links are ones DF can act on,** and 26% in the flying layer. The rest target vermin or have a BENIGN predator (eagles, owls, fox, badger). Required: no BENIGN species in a predator slot; vermin links become stock changes.
5. **Step 6 cannot repair what A–F exclude.** It connected none of 102 isolated animals: none had any allowed relation anywhere in its pool. The rules need a priority order: fort safety (D) > physical reach (land/water) > size (E, F) > connectivity (6).
6. **Webs change completely with the seed** (overlap about 0.17 on land). That is variety, but a fort's web should be fixed by the embark seed so that it survives a reload.
7. **Seasonal breaks are rare and vermin-only** (20% of flying webs lose their insect prey in winter). Required anyway: a predator's seasons must lie within the union of its prey's seasons.
8. **The deep layer is always the same two species,** fire imp and magma crab: a roster rule cannot add variety that is not in the raws.

### Contradictions actually hit

- The single cap table against layers that cannot hold some classes.
- Rule E against the giant/large-prey slot.
- Rule D (tag AND size) against connecting every node in the caverns.
- Rule B against DF: all of B's links are on vermin, which no unit can act on.
- Sentients as prey only, against the pack check in cav1: every pack predator there is sentient, so the check passes 0% of the time.

### With the fixes

The nine fixes: per-layer caps and the stop guard; a seed with at least one relation; the `eats()` ratio instead of bands (pairs with prey 3× the predator's size fall from 5,756 to 601); D by tag; no BENIGN predators; sentients never eat; predator on predator only at 2× size; picks weighted by DF FREQUENCY, with giants not 'high value'; vermin links as stock changes.

Applying fixes 1 and 3–8 (with band adjustments) brought surface isolation down to 2%. The pack/herd check passed 71–75% (91% on land), links DF can act on rose to 77%, and mutual predation fell to 0%.

*Three of these rules were later reversed at your rulings: animal people hunt, armed BENIGN predators are cleared rather than left out, and picks are uniform rather than weighted by FREQUENCY.*

### Guild-first rebuild (v2)

Built guild-first, every roster closes. Over 54,560 builds (11 embark types × every layer × 4 seasons × 20 seeds × 11 configurations), no roster had an isolated or split animal (v2.0; v2.1 split cavern rosters, v2.2 restored 0%), mutual predation, or a humanoid-rule break. Guilds decide which species may meet; size, preference and pack bonuses only weight what the guilds allow.

| Measure (surface) | v1 with fixes | v2 guild-first |
| --- | --- | --- |
| Rosters with an isolated or split animal | 2% | 0% |
| Giants / animal people on a calm map | 75% of land seeds / 20% of nodes | 0% / 0% |
| Edges DF or the tool carries out | 77% (unit edges only) | 90% (79% of unit edges) |
| Pack-and-herd check | 75% | 45%, or 62% with a ×3 group-hunter bonus |
| Seasonal breaks before the guard | 20% (flying) | 4% |
| Roster overlap between seeds, land | 0.17 | 0.32 |
| Unit pairs with prey ≥ 3× the eater | 8,190 | 1,808 |

- **The SAVAGE gate does most of the work.** Every giant, every animal person and 99 of 100 extinct species carry SAVAGE in the raws, so a calm map keeps them out. On a savage map giants are 23% of nodes, sentients 9% and extinct species 12%.
- **The apex boost admits 89 species:** 63 giants, 10 extinct, 11 animal people, and the great white shark, sea serpent, orca, sperm whale and jabberer. 20 are BENIGN and need it cleared; the 11 sentients now hunt by their root guild (v2.1). The orca gets in only through the tool's curated predator override.
- **Weak layers.** In v2.0, flying had no measured raptor hunt and 20% of its edges had a BENIGN raptor; v2.1 clears BENIGN on armed raptors, and REACH measured raptor kills. The temperate lake has no apex half the time (v2.2 fills it with fishing land predators, whose fishing FISH did not confirm). Cavern pools on levels 1–2 hold only 4 amphibious predators; level 3 has nothing linkable. The magma sea is always fire imp and magma crab.
- **Pelagic species** appeared in 57–73% of ocean rosters in v2.0, because a pelagic needs an apex big enough to take it. v2.1's pelagic apex slot makes it 100%.
- **Realms.** There are 75 guild gaps across the 96 realm × biome cells, and same-realm extinct species close only 5. Australasia's missing large apex could be CENOZOIC\_MEGALANIA beside the thylacine; both are SAVAGE, and alone in the apex slot the megalania pushes out the dingo pack (31% → 15%) unless there is a second apex slot. SAVAGE is not a proxy for Australasia (6% of SAVAGE species): it marks a giants-plus-dinosaurs 'lost world'. GOOD and EVIL species are now managed on matching regions, and cavern ones everywhere (v7.0; full list below). Of the period realms, only the Mesozoic hangs together.

Four decisions for you, each with my recommendation:

- [x] **×3 pick bonus for group hunters?** It raises land pack-and-herd from 62% to 81% at no cost seen. Decided (30 Sep): yes, as a ×3 multiplier on a uniform base pick (see the FREQUENCY note below).
- [x] **Savage maps: boosted giant mesocarnivores take 57% of land apex slots.** Giant skinks, lizards and stoats carry FREQUENCY 25 against 5 for real large predators. Decided: cap boosted mesocarnivores so they are picked no more often than real large predators; keep the boost.
- [x] **Extinct species on calm maps?** CRETACEOUS\_CARNOTAURUS, the one non-SAVAGE extinct species (FREQUENCY 50), takes 25% of calm apex slots. Decided: DF's worldgen setting governs extinct species; the tool assumes 'Isolated' (savage islands and small savage biomes), so extinct species enter only savage embarks, and there as gap fills.
- [x] **Who may attack animal people?** As written, the humanoid rule mostly admits giant raptors and giant lizards. Decided: land and water apex guilds only (extended 30 Sep: a flying apex takes flying animal people; animal people and cavern civ races also hunt; civ races are prey of cavern apexes), including giants boosted into apex from those guilds (giant wolf, giant lion, giant crocodile); boosted mesocarnivores and raptors stay out.

Files: `data/eco-desk/v2/guilds/` (design.md for the rules and slot tables, results.md, apex.md, realms.md).

### The 5× size gate, drawn

Superseded by CAL: the 5× gate is gone, and v2.1 and v7.0 use a 5% pack-mass floor instead. The gate let a group of n hunters take prey up to 5 × one hunter's mass × n^0.75, so the pack needed grows as (prey/predator ÷ 5)^4/3. The builder counts each species' usual group, the midpoint of DF's group-size range. It is a gate on which relations get written, not a prediction of who wins: DF's own combat decides that.

&#91;embedded content: DF 53.16 raws via data/eco-desk/v2/guilds/species2.tsv (adult size, cm³ ≈ g) · rule R9: prey ≤ 5 × hunter mass × n^0.75\]

The boundary falls where real packs hunt. Wolves reach moose (4 of a group of 5) but not water buffalo (9); lion prides of 2 take giraffe but not rhinoceros (5); hyena clans of 10 take buffalo (5). The gate would have barred every elephant hunt (74 wolves, 43 hyenas or 9 lions); CAL then saw 7 wolves and 10 hyenas kill elephants. One lion or one tiger passes against a water buffalo (5× and 4.4×), and ECO P1 already saw a buffalo kill a lion, so the solitary end may be too generous. PK and CAL then measured it, and the gate was dropped.

**Pack-size sweep on the rig (ECO3 PK).** Written wolves against 4 prey at one spot, 3,000 ticks, 2 replicates; prey killed, summed over both:

&#91;embedded content: ECO3 PK, CTRL, tool off, 30 Sep 2026 · n wolves against 4 prey at one spot, 2 replicates summed · data/experiments/ECO/ECO3-20260930-133945\]

| Wolves | Deer (gate: 1) | Elk (2) | Moose (4) | Water buffalo (9) |
| --- | --- | --- | --- | --- |
| 1 | 0 | 0 | 0 | 0 |
| 3 | 0 | 0 (2 wolves killed) | 0 | 0 |
| 5 | 1 | 0 | 0 | 0 |
| 7 | 1 | 2 | 1 (2 wolves killed) | 2 |

DF's combat turns on pack size, not prey size. A lone wolf barely engages even a deer (0–1 attacks), and kills come at 5–7 wolves on every prey up to water buffalo, which the gate forbids (7 wolves killed one in both replicates). Kill rates stay low, at most 2 of 4 prey per 3,000 ticks. CAL then settled it: no upper gate, and a 5% pack-mass floor with a sneak bonus for packs at 25% or more.

**Sharks take swimming waterbirds (ECO3 WB).** Tiger sharks written against birds placed in the sea killed 5 of 6 ducks in both replicates, and 2 and 3 of 6 penguins; with no relation written, 0 attacks. The reach table's untested cell is a yes, in water.

**Longer calibration (ECO CAL): kills follow group size, not prey mass.** 6 prey against written predators at one spot, 30,000 ticks (about 25 days), citizens watered and fed before each cell, 2 replicates. Prey killed per replicate:

&#91;embedded content: ECO CAL, CTRL, tool off, sustain per cell, 30 Sep 2026 · data/experiments/ECO/CAL-20260930-142550 (and -135309 rep 1 wolf cells)\]

| Hunters | Deer (3.5×) | Moose (13×) | Water buffalo (25×) | Elephant (125×) |
| --- | --- | --- | --- | --- |
| 3 wolves | 0, 0 | 0, 1 | 2, 0 | 0, 0 |
| 5 wolves | 0, 0 | 0, 1 | 1, 0 | 0, 0 |
| 7 wolves | 1, 0 | 2, 0 | 3, 1 | 2, 1 |
| 5 hyenas | — | — | 0, 0 | 1, 1 |
| 10 hyenas | — | — | 0, 1 | 5, 3 |

- **Solitary hunters are nearly inert:** 1 kill in 12 cells (cougar against deer, elk and moose; lion against giraffe and water buffalo; tiger against water buffalo). The lion took one buffalo.
- **Bigger prey died more often, not less.** Across the wolf cells: deer 1, moose 4, water buffalo 7, elephants 3. Ten hyenas killed 8 elephants over the two replicates. Deer escape by running.
- **Predation thins, it never wipes out:** at most 5 of 6 prey in 25 days. The best rate was 1.3 kills per 10,000 ticks (10 hyenas on elephants); 7 wolves ran 0.2–0.7. Elephants killed 5 wolves and 5 hyenas.

**What changes in the builder:**

1. **No mass-ratio gate.** DF's combat gives it no basis. Prey choice keeps only the soft size preference (your 'no strict size rules'), which makes a wolf pack on an elephant rare rather than forbidden.
2. **Group size is the lever.** Pack hunters' edges are the ones DF carries out. Solitary hunters' edges are still written, since a lone cougar should hunt, and they hunt when prey is dense (LONE: about 3 kills a season); v7.0 gives them the solitary package.
3. **The FREQUENCY ladder, sized to keep predators visible.** On the ECO2-G embarks the surface drew 3–5.5 waves per 40,000 ticks, about 8–14 per season. At the first proposal (apex 1 against prey 8) an apex group would arrive about once in four seasons, too rare to see predation at all. Kill rates are low enough that prey can afford a larger predator share: even a 10-hyena clan takes about 13 prey a season, against 30–40 prey arriving. The first revised ladder (apex 3, mesocarnivores 3, prey 4–6) gave 31% predators on land in v2.1. v2.2 raises prey and scales each roster so its commonest member sits at DF's cap of 100: predators make up 16% of land arrivals, 10% ocean, 10% lake, 12% river, 19% flying and 15–16% in the caverns, with about one apex wave a season (chart in the third round below). Within a guild each value is still scaled by body size to the power −0.75 (Damuth's law), clamped to 0.25–4×.
4. **Checked on the rig before it ships:** a season with the ladder written, counting waves by tier against the prediction, and kills against arrivals. The exhaustion watcher backs up any prey species that runs out.

### Solitary hunters: speed, stealth and skills (STL, STL2)

Lone hunters kill rarely, with or without skills. Across STL and STL2 (64 runs of 30,000 ticks), hunters given skills or AMBUSHPREDATOR killed in 10 of 48 runs and unchanged hunters in 2 of 16, a difference well within chance. No hunter was ever hidden (0 of 426 samples). The one steady signal is narrow: a cougar with combat skills attacked deer 131 and 145 times and killed one in each replicate, where an unchanged cougar barely engaged.

&#91;embedded content: ECO STL and STL2, CTRL, tool off, 30 Sep 2026 · 4 hunter–prey pairs × 2 replicates per block · scripts/stl-tally.py\]

**Why deer escape: speed.** DF gives speed as ticks per 100 tiles, so lower is faster. Wolf kills in CAL rose as the prey got slower (10 hyenas also killed 8 elephants and 1 buffalo):

| Species | Role | Speed (lower = faster) | Killed by wolves in CAL |
| --- | --- | --- | --- |
| Lion | solitary hunter | 109 | — |
| Elk | prey | 122 | — |
| Deer | prey | 137 | 1 |
| Wolf | pack hunter | 149 | — |
| Moose | prey | 157 | 4 |
| Tiger | solitary hunter | 157 | — |
| Water buffalo | prey | 183 | 7 |
| Cougar | solitary hunter | 195 | — |
| Elephant | prey | 488 | 3 |

The lion is faster than every prey here and still made 1 kill in 4 CAL cells. A solitary hunter's problem is engaging at all, not catching up.

**STL** put one cougar or one lion against 6 deer (fast) or 6 water buffalo (slow), with the relation written: 30,000 ticks, 2 replicates, every cell watered and fed first. Each row covers 8 cell-replicates:

| Arm | What changed on the hunter | Its attacks on the prey | Prey killed | Hunters lost | Hidden samples |
| --- | --- | --- | --- | --- | --- |
| ctl | nothing | 17 | 0 | 0 | 0 |
| sneak | Sneak skill 10 (what NATURAL\_SKILL:SNEAK:10 gives a new unit) | 112 | 3 | 0 | 0 |
| nslow | sneak, and sneaking costs no speed (stealth\_slows 0) | 21 | 1 | 1 | 0 |
| ambush | AMBUSHPREDATOR on | 29 | 1 | 0 | 0 |

- **All 5 kills were the lion's:** deer 3, water buffalo 2. The cougar, slower than both prey, killed nothing in any arm.
- **STL alone looked like an effect, but the numbers were small.** Kills came in 4 of 24 treated cell-replicates against 0 of 8 controls, and in CAL the unchanged lone hunters made 1 kill in 12 cells. STL2, below, doubled the comparison and the gap closed.
- **Wild animals don't sneak.** Hunters are never flagged hidden, with or without the skill or AMBUSHPREDATOR, so stealth\_slows and ambush are not the lever. Whatever the skill does, it works in the fight.

**A side finding: hunters attack animals they were never related to.** The relation is written only between the placed hunter and its placed prey, and the tool is off on CTRL (checked: enabled 0, no jobs). Even so, over 30,000 ticks:

- in CAL, wolves and hyenas made 745 attacks on the fort's own wildlife and killed 53 (30 badgers, 6 emus, 6 kangaroos, 4 wombats and others);
- in STL, AMBUSHPREDATOR hunters made 103 such attacks and killed 5; the controls made none.

In STL2 a lion with no relation written at all killed 8 badgers (104 attacks against their 4), and a cougar attacked a native wolf, a porcupine and a kakapo. So DF writes relations itself. A probe on CTRL (RELP, 1 run) read DF's relation table: no native had an entry at load, but within 3,000 ticks of placing a lion, DF had written PREDATOR\_OR\_PREY between the lion and a wild kestrel, and between dwarves, livestock and that kestrel, with nothing written by us. P1's rule still holds as stated: hunting needs a PREDATOR\_OR\_PREY entry. But DF adds such entries on its own over time, and the tool's writes come on top of them. How fast and between whom is a new tracker item.

**STL2** used the same 4 pairs and 2 replicates, with the skills written at rating 10 on the placed hunter. Rows pool both blocks where an arm ran in both:

| Arm | Runs | Its attacks on the prey | Prey killed | Runs with a kill |
| --- | --- | --- | --- | --- |
| ctl (STL + STL2) | 16 | 70 | 4 | 2 |
| norel: no relation written | 8 | 0 | 0 | 0 |
| sneak (STL + STL2) | 16 | 197 | 7 | 4 |
| fight: Fighter, Biter, Striker, Wrestler, Dodger | 8 | 315 | 3 | 3 |
| all: sneak, fight, Observer, AMBUSHPREDATOR | 8 | 18 | 1 | 1 |

- **STL's clean control was luck.** In STL2 the unchanged lion killed 3 deer and then 1.
- **Combat skills raise engagement, not kills.** The fight arm made the most attacks, but its kill rate matches the others. Stacking sneak, Observer and AMBUSHPREDATOR on top erased even the attacks.
- **Without a relation a hunter ignores its placed prey entirely** (0 attacks in 8 runs), so the written relation is still what aims it.

The data alone don't settle it (pooled p = 0.35). You chose to build it: v7.0 gives every armed solitary hunter the package, and LONE tested it at high prey density (below). What actually decides a lone hunter's kills is whether it meets prey at all, and one lion or cougar on a large map rarely does, with or without skills.

Data: `data/experiments/ECO/STL-20260930-155456` and `STL2-*`, tallied by `scripts/stl-tally.py`.

### v2.1: your answers worked through (30 Sep)

The builder was rerun on the same 11 embarks with your rulings: uniform picks ×3 for pack hunters, the FREQUENCY ladder applied last, no 5× mass cap, and the changes below. Every pelagic species now has a predator, and every BENIGN attacker the roster arms is cleared, so DF can act on every unit edge except the 19% whose reach is untested. Three things got worse, listed after the table.

| Your point | What the rerun shows | v2.1 change |
| --- | --- | --- |
| Animal people (TIGER\_MAN etc.) as predators | v2 wrote 0 edges from them. v2.1 writes 6,551 unit edges on savage maps, with animal people attacking in 78% of rosters. Calm maps are unchanged: every animal person is SAVAGE | Allowed, using their root species' guild. Civ races (amphibian, reptile, serpent, rodent and ant men, troglodytes, gremlins, plump helmet men) stay out |
| Clear BENIGN on the 20 boosted apexes | All 20 are cleared, including the orca and sperm whale, the giant fox, badger, otter, stoat, wolverine and mongoose, the six giant raptors, and Archelon | Done |
| Does the orca get in, with BENIGN cleared? | It is in every calm ocean pool. It was on 13% of ocean rosters in v2 and is on 61% in v2.1, always with BENIGN cleared (with the flag on it made 0 attacks; cleared, it killed 4 of 8 seals) | Orca is the most common pelagic apex |
| The unit edges DF doesn't carry out | 19% of surface unit edges (3,039 of 16,401) had a BENIGN attacker. Raptors made 1,880 of them (eagle 569, osprey 484, peregrine 374, owls, kestrel) and mesocarnivores 1,159 (badger 430, river otter 278, sea otter, fox, wolverine, stoat, mongoose) | BENIGN is cleared on every predator the roster arms, which takes those edges to 0%. What's left is 19% untested reach: flier on flier (3,007 edges, the whole flying layer), shark on waterbird in water (459; WB says yes) and aquatic on shore animal in water (292; HO says yes) |
| Pelagic apexes: giant squid, giant orca, giant sperm whale, giant octopus, great white | Pelagic prey appeared on 65% of calm ocean rosters and 80% of savage ones. v2.1 has 100%, and every pelagic has a predator. Calm apexes picked: orca 196, sperm whale 65, great white 59. Savage adds giant orca 89, sea serpent 24, giant sperm whale 23 | The ocean gets a second apex slot, for a pelagic apex. The giant octopus (235 kg) and GIGANTIC SQUID (201 kg) are too small to be apexes, so both are water mesopredators. The squid has no diet token, so it is armed through the curated override and addressed by index, since its id has a space; it went from 0 edges to 732 |
| Giant pack hunters and elephants | Giants that hunt in groups: hyena 5–15 (a pack of 10 is 6.3 t), dingo 3–12, coyote 2–10, jackal 1–5, lion 1–3, and the giant alligator and saltwater crocodile 1–3. The giant wolf is solitary in the raws. On savage maps, elephants get edges from giant dingoes, lions and hyenas, rhinoceros from all four, hippos from the giant crocodilians | No special rule: the pack-mass floor below decides it |
| Does a species with no predator drop out? | Yes. The link guard drops a big herbivore that nothing in its pool can take: 8 calm pool cells in v2 (rhinoceros, hippo) and 255 savage (sauropods, Paraceratherium, giant rhinoceros). v2.1 cuts that to 4 and 179, and to 14 savage at a 5% floor. No predator is dropped for being too big | Dropped species are reported by name (next row) |
| "A pass adds nothing" | It happened silently in v2 | Every slot left below its minimum is reported with its cause. When a pass adds nothing, the builder seeds a new predator-prey pair before giving up |
| GOOD, EVIL, FANCIFUL | See below | Three small fixes, none built yet |

**What got worse (all three fixed in v2.2, third round below):**

- **Every cavern roster splits into two webs.** Cavern raptors, bats and floaters had only one link to the rest of the web, and it ran through sentient prey. Under your apex-only rule for sentient targets they lost that link. The pair fallback brings them back, but as a separate web. It needs a rule for what cavern fliers may eat, which also needs a flier-on-land-prey reach test.
- **Predators make up more of the arrivals:** land 14% → 31%, ocean 6% → 14%. This is the ladder, not the roster. It is what the season test and the threshold sweep (tracker) have to judge.
- **Insect men and bird men never make a flying roster** (646 pool cells), because no apex guild flies. That follows from the apex-only rule, so it's for you to decide whether it's acceptable.

**The pack-mass floor is your call.** Without the 5× cap, nothing stops a river otter being written against a hippo (240 such edges). A floor on the hunters' total mass as a share of the prey's fixes that, and the builder now takes it as a setting:

| Floor | What it allows |
| --- | --- |
| 0% | Anything: river otters get 240 edges onto elephants and hippos, honey badgers 74, jackals 69 |
| 5% | Every kill measured so far, including 7 wolves on an elephant (5.6% of its mass) |
| 20% (proposed 30 Sep) | Only real-world hunts. Forbids the elephant kills CAL measured; elephants fall from 34 to 3 of 160 calm rosters |
| 30% | Also drops cougar on elk and tiger on buffalo |

Decided (30 Sep): 5% for an edge, plus a sneak bonus for packs at 25% or more. It forbids only what DF has never been seen to do, and a giant elephant still makes a roster (1 of 160 at 5%, none at 20%, because a giant-hyena pack is 16% of its mass).

**GOOD, EVIL and FANCIFUL: the tool mostly stays out of the way, with one leak.** DF places GOOD creatures (8: unicorn, satyr, mountain gnome, merperson, gorlak, fairy, pixie, fluffy wambler) and EVIL ones (24: ogre, harpy, nightwing, ice wolf, troll, reacher, demon rat and others) on matching regions by its own rule, outside the normal pick. The tool classes all of them, plus FANCIFUL, as `mythic`, which is locked, so the roster, holds, FREQUENCY writes and the cavern ceiling never touch their entries (seasonal-wildlife.lua:412, :986–989, :1299). v7.0 goes further at your ruling: aligned surface GOOD/EVIL wildlife and every cavern GOOD/EVIL species are managed. Three fixes:

1. **Leak.** The Vermin tab lists locked families (`VERMIN.rows`, :2145, has no lock filter). Pressing D seasons fairies, pixies, demon rats, knuckle worms, phantom spiders, blood gnats and the creepy crawler, and then `applyLive` zeroes them out of season. The fix is to filter locked entries there and clear any saved allow on a locked key at load.
2. **Cavern GOOD/EVIL species are ordinary cavern wildlife.** Trolls, reachers, blind cave ogres and gorlaks appear under any surface alignment, but they are locked, so the cavern roster can't hold or season them. The fix is to class a GOOD/EVIL species whose only biomes are subterranean as natural.
3. **FANCIFUL is not a placement token.** It marks "a thing of legend" for art, yet it locks the yeti and the sasquatch, which are ordinary SAVAGE surface predators. The fix is to drop FANCIFUL from the mythic test; megabeasts are already caught separately.

Files: `data/eco-desk/v2/guilds/results21.md`, `tables21.md`, `design.md` (rules marked v2.1); runs in `runs/v21*.jsonl`, with the v2 runs kept in `runs/v2-orig/`.

### Third round (30 Sep evening): your notes worked through

Every note is answered below. Builder v2.2 (offline) and tool v7.0 (committed on a local branch, not deployed) take your design principle: where the tool manages an ecological space, it overrides vanilla DF instead of running alongside it. The rig work you asked for runs in sequence: LONE, then the reach tests, then vermin (VRM), then DF's own relation writes (RELS).

| Your note | Answer | What changed |
| --- | --- | --- |
| Downside of turning CURIOUS\_BEAST off? | The flags drive DF's thief visits: raccoons and bears walk in, steal food, drink or items, then leave. Off, they stop raiding and stop leaving, so they stay as residents and the tool's limits must manage their exits. The tool already offers both (`curious TOKEN resident\|thief`) | No change |
| Scavengers on remains anywhere outside stockpiles? | Yes. Walking a scavenger to remains and deleting them works and survives a reload (S2) | v7.0: scavengers target remains anywhere on the map, skipping stockpiles, buildings, inventories and remains already in a job (opt-in) |
| Do sharks take swimming seals? Crocodiles swimming otters, or a capybara up on land? | Sharks: yes, in the water (W1O: 4 of 8 seals placed in water). Seals on the shore are safe unless they enter the water (1 of 8 killed in W1O). Alligators took 5 of 8 deer and crocodiles 4 of 8 water buffalo from the water (W1L); REACH has since confirmed swimming and inland kills (below) | REACH tests: crocodile on swimming beavers (the otter's id has a space, so the test verbs can't name it), crocodile on capybaras 15 tiles inland, shark on seals in water and on shore |
| Swim flags do make a land predator fish | Only partly. Wolves already swim in the raws; with water-breathing added they touched pike (2 attacks in HR, 1 per replicate in FISH) but never killed one, and swimming alone made no attack | v2.2 and v7.0: fishing land predators (grizzly, black and polar bear, tiger, jaguar) get edges to fish. FISH found wolves don't fish even with water-breathing, so I recommend this feature off by default |
| Vermin predation is a huge hole | Agreed: high priority. DF's raws carry one gobble link: `GOBBLE_VERMIN_CLASS:EDIBLE_GROUND_BUG` on 15 creatures (ducks, geese, peafowl, hedgehogs, pangolins, chickens), matching large roaches, beetles, thrips and ants. No vanilla creature uses `GOBBLE_VERMIN_CREATURE`, but the caste fields exist and can be written | VRM places loose vermin on the map (DFHack's own colony code shows how) and tests native, written and absent gobblers. v2.2 uses the gobble tokens as its vermin edges: 92% need the tool to write `GOBBLE_VERMIN_CREATURE` |
| Seasons: defer to NO\_\<season> or overwrite? | Overwrite. DF brings land and cavern animals itself, drawing waves from the region's population entries; the tool only gates them (limits, stock, FREQUENCY). Up to v6.9, when the tool dealt a species a season its raws forbid (a NO\_WINTER bear dealt Winter), v6.9 moved it to the next allowed season, because DF would never send it then | v7.0: raw season flags only seed the first deal. The tool clears NO\_\<season> on managed species, so its own deal wins (ECO2-W showed a cleared flag lets the species arrive), and restores the flags when switched off |
| "On smaller maps DF's own supply runs out first" | Up to 4×4 embarks, DF never had more groups on the map than the old limit of 3, so raising it added nothing. On 5×5 and 6×6, DF sent more and the limit was what held them back | No change |
| Leader = largest male | Implement | v7.0: the largest adult male leads, else the largest adult, else lowest id; a living leader keeps the role |
| Groups at once by layer, every layer independent | Before: land used √tiles + 1, but water had one shared count of 2 across ocean, lake, river and pools, and the caverns one shared count of 2 across all depths | v7.0: land, each water body and each cavern depth get their own count of floor(√tiles) + 1 (3 on a 2×2), with their own clocks. Only the water layer's animal ceiling stays shared |
| Give solo predators SNEAK, no sneak slowdown and AMBUSHPREDATOR; "statistically significant as a meta-analysis" | Built as you decided. Pooling every lone-hunter run so far, though, it isn't: skilled or AMBUSHPREDATOR hunters killed in 10 of 48 runs, unchanged ones in 3 of 28 (Fisher's exact test, p = 0.35). LONE, which removes the encounter problem, is the real test | v7.0: every armed solitary predator gets natural skills at 10 (Sneak, Fighter, Biter, Striker, Wrestler, Dodger, Observer), stealth\_slows 0 on every gait and AMBUSHPREDATOR, on its castes and on units already present; restored on off |
| Is the off-target hunting due to AMBUSHPREDATOR? | Not alone. STL2's lion with no relation and no AMBUSHPREDATOR killed 8 badgers, and CAL's wolves killed 53 natives without it. DF writes PREDATOR\_OR\_PREY entries itself (RELP) | RELS logs DF's writes over a season and isolates candidate triggers |
| Downside of a low pack-mass floor; vegetation check for big herbivores | 5% against 20% adds 2,616 edges (9%), 416 of them on prey of a tonne or more, with odd pairs such as peregrine on albatross and jaguar on hippo. In CAL, hunts below 5% made 0 kills and lost 4 hunters; at 5–20% they made 15 kills and lost 6, so 5% cuts exactly the band where DF only loses hunters | v2.2: a herbivore no predator can take stays on the roster if the map's vegetation supports its size (index ≥ 20 + 15·log10(mass / 100 kg)). Calm elephants 3 → 10 of 160 rosters, water buffalo 40 → 80 of 80. The tool needs a vegetation survey at load for this |
| GOOD, EVIL, FANCIFUL: why not in the ecosystem? | They were locked as "mythic" under decision D8 (26 Sep, mythic and legendary unmanaged). DF placed them, the tool never touched them | v7.0: the three fixes, plus surface GOOD/EVIL wildlife is managed when the embark's region alignment matches (read from the region map; evilness < 33 good, ≥ 66 evil). Cavern GOOD/EVIL species are always managed. The full list is below |
| Bats eat flying vermin, cavern raptors eat bats; scan for singletons | Right. In v2.1 cavern fliers had lost their only link | v2.2: bugbats and floaters eat cave bats and ground vermin; giant bats, hungry heads and giant cave swallows eat bats, bugbats, floaters and cavern land prey. Split webs 100% → 0%. The full scan leaves only the 5 cavern civ races (troglodyte, rodent, amphibian, reptile and serpent men): apex-tier, so nothing may eat them, and barred from attacking. Your call: config `v22_civ` lets them hunt, which clears it |
| Predators at 31% of land arrivals: can FREQUENCY fix it? | Yes | v2.2 ladder, scaled so each roster's commonest member is at DF's cap of 100: predators land 16%, ocean 10%, lake 10%, river 12%, flying 19%, caverns 15–16%; apex about one wave a season. Savage land runs 23% (two apex slots) |
| An apex flying guild; insect and bird men on flying rosters | Yes to both | v2.2: raptors of 2 kg or more that aren't scavengers (eagle, great horned and snowy owls, osprey) fill a flying apex on 100% of calm flying rosters. Savage maps add giant raptors and three pterosaurs. Flying animal people get a prey slot like land ones: 0 → 880 of 880 savage flying rosters |
| Pack floor 5% for an edge, sneak bonus at 25% | Built in both | v7.0 uses the group actually present; at 25% the pack gets unit SNEAK 10. In v2.2, 87–100% of edges clear 25%, so the bonus marks nearly every pack hunt; the 5–25% stretch hunts are the rest |
| Cavern raptors and bats on cavern land prey | Yes | REACH tests giant bats on bugbats and crundles, and BENIGN-cleared giant cave swallows on bugbats |
| A lone hunter's limit is meeting prey: scale the map up | Agreed, that was the design gap | LONE: one cougar among 48 prey of 8 species, one season or until it dies, 5 replicates, unchanged against the full package |
| DF writes relations itself: explore | It's a new facet of vanilla predation | RELS: DF's relation table every 3,000 ticks, a natives-only season plus a lion as is, BENIGN, LARGE\_PREDATOR off and AMBUSHPREDATOR on, a deer, and badgers |

&#91;embedded content: data/eco-desk/v2/guilds/results22.md §0 (main = v2, v21, v22) · calm embarks; cavern pools and the magma sea are left out: one apex over vermin, structural\]

The v2.1 ladder roughly doubled predators on every layer. v2.2 scales each roster so its commonest member sits at DF's cap of 100, which brings land to 16% and the lake from 57% to 10%. Flying stays at 19% because a flying roster holds an apex and 1–2 raptors against at most 4 bird species; going lower needs a smaller raptor slot, not FREQUENCY.

Tool v7.0 is commit `49fde90` on the seasonal-wildlife branch `v7.0`. `luac` is clean and luacheck shows no new warnings. Every change has a switch under `cfg.v7` and a `seasonal-wildlife v7` verb. It goes onto the rig once the queued experiments finish, with 17 new validator checks. Builder v2.2 files are in `data/eco-desk/v2/guilds` (`results22.md`, `ge22.md`, `design.md` rules marked v2.2).

### GOOD, EVIL and FANCIFUL creatures

The raws hold 8 GOOD and 24 EVIL creatures; all but the goblin have biomes, so DF places them on matching regions. FANCIFUL is an art token, but it also locked two ordinary SAVAGE predators, the yeti and the sasquatch. In v2.2 and v7.0 each appears on a matching region, and the cavern ones everywhere. Mountain gnomes, dark gnomes and stranglers never appeared, only because no test embark has their biome.

| Creature | Tag | Guild | Mass (kg) | Group | Sentient | Where it appears in v2.2 |
| --- | --- | --- | --- | --- | --- | --- |
| Unicorn | GOOD | grazer | 600 | 3–7 |  | good forests and shrubland (104 of 560 land rosters) |
| Satyr | GOOD | land prey | 60 | 3–5 | yes | good forests (160 of 160) |
| Mountain gnome | GOOD | land prey | 15 | 5–10 | yes | mountains (no test embark) |
| Merperson | GOOD | coastal fish | 70 | 3–6 | yes | good oceans (320 of 320) |
| Gorlak | GOOD | land prey | 50 | 1 | yes | every cavern depth |
| Fairy, pixie | GOOD | flying vermin | <0.1 | 1; 100–200 |  | good flying rosters |
| Fluffy wambler | GOOD | ground vermin | 2 | 1 |  | good land |
| Ogre | EVIL | land apex | 6,000 | 1–3 | yes | evil grassland, savanna and shrubland (402 of 560) |
| Foul blendec | EVIL | land apex | 60 | 3–5 | yes | evil forests (158 of 160) |
| Blizzard man | EVIL | land apex | 300 | 1 | yes | evil glacier and tundra (160 of 160) |
| Ice wolf | EVIL | land apex | 50 | 3–7 |  | evil glacier and tundra |
| Beak dog | EVIL | land apex | 150 | 3–7 |  | evil marshes |
| Strangler | EVIL | land apex | 40 | 1–3 |  | tropical moist forest (no test embark) |
| Grimeling | EVIL | water apex | 70 | 1 |  | evil swamps |
| Sea monster | EVIL | water apex | 8,000 | 1 |  | evil oceans (48 of 320) |
| Harpy | EVIL | raptor | 60 | 2–3 | yes | evil grassland and shrubland skies (640 of 640) |
| Nightwing | EVIL | raptor | 120 | 1 | yes | evil deserts (80 of 80) |
| Dark gnome | EVIL | land prey | 15 | 5–10 | yes | mountains (no test embark) |
| Troll | EVIL | cavern apex | 250 | 1 | yes | every cavern depth |
| Blind cave ogre | EVIL | cavern apex | 7,000 | 1–3 | yes | caverns 2–3 |
| Cave dragon | EVIL | cavern apex | 15,000 | 1 |  | cavern 3 |
| Blood man | EVIL | cavern apex | 70 | 2–5 |  | cavern 3 |
| Reacher | EVIL | cavern mesopredator | 70 | 1 |  | caverns 2–3 |
| Manera | EVIL | cavern prey | 60 | 1 | yes | cavern 2 |
| Creeping eye | EVIL | cavern prey | 20 | 10–20 |  | cavern 3 |
| Creepy crawler | EVIL | cavern vermin | 1 | 1 |  | cavern 3 |
| Demon rat, knuckle worm, phantom spider | EVIL | ground vermin | 0.3–1 | 1 |  | evil land |
| Blood gnat | EVIL | flying insect vermin | <0.1 | 100–200 |  | evil pools |
| Yeti | FANCIFUL | land apex | 300 | 1 |  | savage mountains, glacier and tundra |
| Sasquatch | FANCIFUL | land apex | 300 | 1 |  | savage temperate forest and taiga |

The goblin is EVIL but has no biome; it is a civilization race, not wildlife.

### A lone hunter among 48 prey (LONE)

With prey all around it, a lone cougar does hunt. Unchanged, it killed 14 animals in 5 seasons, about 3 a season; with the full package, 22, about 4.4. Encounter was the limit in the earlier tests, as you said. The package leads on every measure, but at 5 replicates the gap is not yet separable from chance.

Setup: CTRL with the tool off; one cougar among 6 each of rabbit, hare, groundhog, mountain goat, kangaroo, deer, elk and water buffalo (spread over 20 tiles); relations written to all 8; one season (100,800 ticks), 5 replicates per arm. The cougar survived every run, alive in all 21 samples, so no run was cut short.

&#91;embedded content: ECO LONE, CTRL, tool off, 30 Sep 2026 · 100,800 ticks per run, 5 runs per arm · data/experiments/ECO/LONE-\*, scripts/lone-tally.py\]

| Arm | Kills of the 48 placed prey (per run) | Native animals killed | Attacks on placed prey | All attacks |
| --- | --- | --- | --- | --- |
| Unchanged | 5 (2, 0, 1, 0, 2) | 9 | 139 | 390 |
| Package: Sneak, Fighter, Biter, Striker, Wrestler, Dodger, Observer at 10, no sneak slowdown, AMBUSHPREDATOR | 11 (1, 2, 6, 0, 2) | 11 | 290 | 472 |

- **Significance (permutation test, one-sided):** placed-prey kills p = 0.25, all kills p = 0.13, attacks on placed prey p = 0.20. Each run varies a lot (0 to 6 kills), so the 5 replicates per arm you asked for are too few for a firm answer. Ten per arm would likely settle it.
- **What it hunts:** mostly small prey. Kills were groundhogs (8), mountain goats (5), a kangaroo, a rabbit and one elk (300 kg, a package run). It never killed a deer or a water buffalo, though the package cougar attacked buffalo 41 times in one run.
- **Natives drew over half its kills (20 of 36) and half its attacks:** badgers, wombats, skunks, emus. DF wrote those relations itself (RELP), so a placed hunter also preys on the fort's own wildlife.
- **For the tool:** a solitary hunter is only active if prey is dense near it. The package is built in v7.0 as you decided; the season test will show its effect at real densities.

Data: `data/experiments/ECO/LONE-*`, tallied by `scripts/lone-tally.py`.

**LONE10 (10 runs per arm, 30 Sep night) settles it: the package lifts kills.** The same cougar among 48 prey, one season per run. Kills 29 against 14, attacks 1,393 against 664; per run the package's kills were 7, 2, 3, 3, 4, 12, 8, 0, 7, 3 against the control's 2, 1, 5, 0, 2, 2, 0, 0, 4, 5 (one-sided permutation test p = 0.025; at 5 runs per arm it was p = 0.13). Most of the lift is on native wildlife the cougar met on its own (20 against 7); on the 48 placed prey the two arms were close (9 against 7). The control cougar died once; the package cougar never did. Data: `data/experiments/ECO/LONE10-*`.

### Reach tests (REACH)

Every reach you asked about works except two: an eagle never took a rabbit, and wolves never caught pike, with swim flags or without. Crocodiles answer your question fully: they take swimming prey and go up on land for prey 15 tiles from the water.

&#91;embedded content: ECO REACHW (OCEAN2 shore), REACHF (CTRL), REACHC (BOATS cavern 1), FISH (RIVER4) · 30 Sep 2026 · 3 predators against 6 prey (wolves 5 against 8 pike), 3,000 ticks (water cells 5,000), 2 replicates\]

- **Crocodiles leave the water to hunt.** In the inland cell, 1 to 3 of the 3 crocodiles stood on dry tiles in every 1,000-tick sample, and the capybaras fought back (49 attacks on the crocodiles) without killing one.
- **Sharks hunt only in the water.** Seals on the shore were safe in both replicates; in the water the two replicates split 0 and 4 kills.
- **Fliers take fliers.** The kea flock, the BENIGN-cleared eagle and the owl all killed birds, so the flying layer's web is real. The eagle never engaged a rabbit, so raptor-on-land-prey edges should stay rare.
- **Cavern fliers take cavern prey,** as v2.2 now writes. A giant bat was lost in two cells.
- **Swim flags do not make a wolf fish.** Swimming alone made 0 attacks, and swimming with water-breathing 1 attack per replicate, against 0 unchanged. HR's earlier 2 attacks were the same: contact, not hunting. The fishing land predators in v7.0 and v2.2 rest on this, so I recommend switching that feature off by default until a bear or tiger test says otherwise.

### Vermin predation (VRM)

DF's gobbling is real and class-specific, and a written token carries it to a predator that lacks it (VRM2, below). The first run (VRM) pointed that way but was flawed, as the last bullets say. Placed vermin persist: with no consumer near, all 40 roaches and 20 grasshoppers are still on the map 6,000 ticks later.

- **Native gobblers took roaches only.** Ducks removed 5 roaches in each replicate and hedgehogs 8 and 6, but neither touched a grasshopper. The roach is an `EDIBLE_GROUND_BUG` and the grasshopper isn't, which is exactly what their `GOBBLE_VERMIN_CLASS:EDIBLE_GROUND_BUG` says.
- **Cats cleared vermin fast:** 68 and 71 roaches, plus 45 and 41 grasshoppers, with 29 roaches gone in the first 500 ticks.
- **The run was flawed.** Placed vermin aren't removed with the test's units, so they piled up from cell to cell (40 roaches in the first cell, 225 by the last). The only control also ran first. For the later cells (badgers with the gobble tokens written, and cats), elapsed time is mixed in with the consumer's effect. In the written-token badger cells, grasshoppers fell as fast as roaches, so the write can't yet be credited.
- **The written tokens did land:** both castes took the class or the creature, and both were restored afterwards.

&#91;embedded content: ECO VRM2, CTRL, tool off, 30 Sep 2026 · one fresh load per arm, 40 roaches + 20 grasshoppers placed, 4 consumers, 6,000 ticks, 2 replicates · data/experiments/ECO/VRM2-20260930-202822, scripts/vrm-tally.py\]

**VRM2 reran it cleanly:** each arm got its own fresh load of CTRL, so every arm started from the same 40 roaches and 20 grasshoppers at the same session age. Two replicates per arm, 6,000 ticks each.

- **The written token works.** Badgers with `GOBBLE_VERMIN_CLASS:EDIBLE_GROUND_BUG` written in took 7 and 10 roaches and no grasshoppers, the same pattern as the native gobblers (ducks 4 and 4, hedgehogs 4 and 3). Naming the roach directly (`GOBBLE_VERMIN_CREATURE`) did the same in the replicate the cats left alone: 6 roaches and no grasshoppers. Badgers with no token took nothing selectively.
- **Cats take everything:** 38 and 39 roaches and 20 and 19 grasshoppers, nearly all of both within 6,000 ticks.
- **CTRL's own two pet cats are the background eater.** Three of the 14 replicates lost both kinds of vermin with no consumer that eats both: control rep 1, plain badger rep 2, and named-roach badger rep 2. VRM3b, a control that listed every unit within 6 tiles of a placed vermin every 250 ticks, caught it: the fort's cats (units 117 and 118) reached the spot at t2,250, and while they stayed (distance 0–1 at every sample) grasshoppers fell from 18 to 5 and roaches from 40 to 28. A wild badger and a dwarf passed once each. Across VRM3b's 6 replicates, vermin fell in exactly the 2 the cats visited (from t2,250 and t2,500) and in none of the 4 they didn't. So a selective arm is read only where the grasshoppers held; where both fell, it was the cats.
- **The tokens are restored afterwards.** Both castes took the written class or creature, and the restore put them back.

What it means for the tool: writing a gobble token turns an ordinary predator into a vermin eater of exactly the class named, so the builder's `GOBBLE_VERMIN` edges can be written onto BENIGN predators as vermin-only edges, as planned.

Data: `data/experiments/ECO/VRM2-20260930-202822`, `VRM3-*`, `VRM3b-*`, tallied by `scripts/vrm-tally.py`.

### Domestic animals as prey (DOM, v7.0)

Your request: the fort's livestock and pets become prey of land apex hunters (AL), ground mesocarnivores (ML) and any cavern predator, on every layer, behind a switch. It's built as `v7 domestic` (off by default, because it costs the player animals). Each ecology pass is the trigger: a fort animal with no such predator on the map has nothing written, and is related to each one that arrives at the next pass.

&#91;embedded content: ECO DOM2, CTRL, tool on, ecology on, livestock-as-prey off, 30 Sep 2026 · 3 WOLF moved onto the nearest fort animal, an ecology pass every 1,500 ticks, 12,000 ticks, 2 replicates · data/experiments/ECO/DOM2-\*\]

- **The switch is the whole difference.** Off: no relation written and no wolf touched a fort animal, both replicates. On: the wolves were related to all 11 fort animals and attacked them (37 and 88 attacks); they killed a cavy in each replicate and a chicken, and went for the pig and the dogs.
- **The dogs fight back.** The fort's dogs made 29 and 38 attacks on the wolves and killed one wolf in each replicate.
- **A gap the first run found:** dogs, cats, pigs and chickens have no BIOME in the raws, so the tool classed them 'unclassified' and its forgotten-beast safety filter (`fb_safe`) kept them out of every pairing. The first run reached only 5 of the 11 animals (yaks, horses, reindeer, turkeys, cavies). The fix lets a tame animal of the fort's own through and nothing else (`6c79f32`). The same gap had also kept these four out of the older 'Livestock as prey' switch.

Data: `data/experiments/ECO/DOM-*` and `DOM2-*`; findings `data/eco-desk/findings.md` (DOM).

### DF's own relation writes (RELS)

DF marks each new wild arrival as prey for every unit that isn't wild: dwarves, livestock, and any animal placed by a script. That is why placed hunters attacked the fort's own animals in CAL, STL and LONE: they were treated like fort animals. Between surface wildlife DF writes almost nothing, so on the surface "no relation, no hunting" holds for DF's own arrivals.

&#91;embedded content: ECO RELS, CTRL, tool off, 30 Sep 2026 · 7 cells × 2 replicates, relation table read every 3,000 ticks · data/experiments/ECO/RELS-\*, scripts/rels-tally.py\]

- **Tokens don't matter.** A placed lion as it is, with BENIGN, without LARGE\_PREDATOR and with AMBUSHPREDATOR all got the same entries, and so did a placed deer and placed badgers. What decides it is whether the unit carries DF's wild flag.
- **The arrival answers with BENIGN\_ANIMAL** (662 entries), or DANGEROUS\_ANIMAL when it is the bigger animal (15, an owl toward the lion). DF writes them at sight range (median 35–85 tiles) and clears them again within a few thousand ticks.
- **The surface exception:** 5 entries, 3 of them between one wild great horned owl (a carnivore) and a wombat and a skunk.
- **Caverns are different:** cavern wildlife writes entries toward each other (giant cave toad and troglodyte, cave crocodile and elk bird, reacher and gorlak), which is why cavern species fight without a written relation.
- **What it means for the tool.** When the tool releases a DF wave into a tracked group, it clears the same wild flag (seasonal-wildlife.lua:3197), and its own placements do too (:3559). DF then treats those groups like fort animals and aims them at every later wild arrival. The v7.0 sweep clears those entries when the roster doesn't pair the species. Its filter still sees released groups, because DFHack's wildlife test reads the population reference, not the wild flag. Its refought counter will show how often DF writes them back.

Data: `data/experiments/ECO/RELS-*`, tallied by `scripts/rels-tally.py`.

### A mechanistic version for a new embark

*Superseded in part by your 30 Sep rulings: picks are now uniform (×3 for packs), BENIGN is cleared on every armed predator, animal people and cavern civ races hunt, the tool's own season deal replaces DF's NO\_\<season> flags, and the v2.2 ladder sets FREQUENCY. The v2.1, v2.2 and third-round sections below carry the current rules.*

1. **Pool** per layer: the region's population entries, split by the guilds above, with UNDERGROUND\_DEPTH plus the bizarre score for caverns and the realm filter if one is chosen.
2. **Slots** per layer, sized by guild: land 1 apex, 1–2 armable mesocarnivores, 1 thief, 2 grazers, 2 other prey; water and cavern tables of their own. The embark seed fixes the order.
3. **Grow** from a seed that has at least one relation. Fill the emptiest guild first with the candidate the `eats()` rule links to the web, weighted by FREQUENCY. Stop when a pass adds nothing.
4. **Edges** = every `eats()` pair within reach (land, water, amphibious both ways), minus BENIGN attackers, minus sentient targets unless the predator is LARGE\_PREDATOR. The relation write carries exactly these edges, no others.
5. **Seasons** from DF's own NO\_\<season> flags plus the tool's deal, each predator within its prey's seasons.
6. **Balance** with FREQUENCY, which is proportional: apex 1×, mesocarnivores 3×, grazers and prey 6–8×. Groups get a leader, since a led herd was barely attacked. Vermin get stock, and insect/bird bookkeeping has floors and ceilings.
7. **Invariants checked on every build:** no isolated non-vermin node, at least one pack predator and one herd prey where the pool has them, no edge DF cannot act on, and every species inside its raw seasons.
8. **Replacement:** when an entry's quantity reaches 0, promote the nearest same-guild candidate. N1 showed it takes over within about 2,000 ticks.

## Overnight blocks, 30 Sep – 1 Oct

The overnight blocks closed every open item in the tracker except the final validation. Five of them needed a rerun after the first pass tested nothing or was confounded: SW3, SCV2 and S8C tested nothing, and SW1 and SW2 were confounded by cell order. This table lists the single-question blocks; the sections below cover relations, scavenging, the seasons, the sweep and the forts. Savage giant packs kill elephants, rhinoceros and hippos. A leader holds flocks and schools together. Lake species take a written relation. FLEEQUICK, VISION\_ARC and the fishers switch did nothing measurable. Every block ran 2 replicates except LAKEP (one run).

| Block | Item | Fort | Question | Answer |
| --- | --- | --- | --- | --- |
| VRM4 | 31 | CTRL | Does DF honour a vermin class the tool writes at runtime? | Yes. Badgers given GOBBLE\_VERMIN\_CLASS:SWV\_TEST ate 4 and 6 of 20 grasshoppers carrying that class; the control ate 0 and 0 |
| LAKEP | 12 | LAKE | Are lake species writable? | Yes. Lake units are feature entries the tool puts in the surface realm; 21 of 21 written alligator–carp pairs still held at every read to 3,000 ticks |
| HC4 | 14 | BOATS | Do cavern species fight with no relation because of the species or the spot? | Mostly the species: 5 of 8 pairs behaved the same at a second spot (trolls × gorlaks and troglodytes × elk birds fight at both; jabberers, ogres and giant olms never). Three moved with the spot. Keep the cavern write |
| GPK, GPKW, GPKR | 10 | CTRL, OCEAN2, RIVER4 | Do savage giant packs take megafauna? | Yes. 10 giant hyenas killed both elephants in both runs; 10 giant dingoes 1 of 2 rhinoceros per run; 4 giant saltwater crocodiles both hippos in all 4 runs. No hunter lost |
| FSH2 | 33 | RIVER4 | Do bears and tigers with swimming written catch river fish? | No. 0 attacks on 8 pike in all 6 runs; two grizzlies left the map. Fishers now default off in v7.0 |
| FVA | 24 | CTRL | Do FLEEQUICK and VISION\_ARC change a wolf pack's success? | No reliable effect. Replicate 2 was quiet in every arm, the control too (3 attacks each). Parked |
| INV, INV2 | 17 | CTRL | Does DF keep sending a SAVAGE species added on a calm map? | No. INV's yeti was refused on biome, so INV2 used CENOZOIC\_SMILODON: its entry was added both runs, yet DF drew none in a full season (0 at all 21 samples, 2 runs). Add invasive must place SAVAGE species on calm land itself |
| COH, COHO, COHR | 20 | CTRL, OCEAN2, RIVER4 | Does a leader hold flocks, schools and pods? | Yes, below |
| SCV, SCVW, SCVC | 19 | CTRL, LAKE, BOATS | Who scavenges after a kill? | Wolves only, below |
| RELS2, RELS2b, RELS3 | 27 | CTRL | How does DF write relations for new arrivals? | DF aims the fort at each arrival but never pairs surface wild with surface wild; table below |

Data: `data/experiments/ECO/<block>-*`; one paragraph per block in `data/eco-desk/findings.md`.

### Cohesion with a leader (item 20)

&#91;embedded content: ECO COH (CTRL), COHO (OCEAN2), COHR (RIVER4), 1 Oct 2026 · the \`lead\` verb names the largest male, 15,000 ticks, 2 replicates · data/experiments/ECO/COH-\*\]

A leader works in water and in the air as it does for herds and packs on land, so item 20 is closed. The orca pod is the exception: led, it is about half as wide but still loose, because open ocean gives it room. The duck flock in replicate 2 loosened late, to 48–62 tiles after tick 9,000.

### Scavenging (item 19)

With the tool on, v7.0's scavenging pass clears carcasses on land and in water within about 2,400 ticks. DF's own behaviour and the rig's walk-and-eat verbs cleared them only for wolves on land. What the night didn't measure is which species did the eating.

| Block | Where | What ate | Result |
| --- | --- | --- | --- |
| SCV | CTRL, 6 kangaroo carcasses | The rig's walk and eat verbs | Wolves ate 6 and 2. Jackals and vultures never got near: 0 |
| SCVW | LAKE, 6 carp carcasses in water | The same verbs | 0. Alligators can't be walked; wolves on the bank couldn't reach the water |
| SCVC | BOATS cavern 1, 6 elk birds | DF alone, trolls present | 7 corpses before and after 3,000 ticks: DF removes none |
| SCV2b | CTRL, 6 kangaroo carcasses | The tool's pass, with 5 wolves, jackals or vultures placed | 0 or 1 left in all 6 cells |
| SCV2Wb | RIVER4, 6 carp carcasses in the river | The tool's pass, with 5 pond grabbers in the water or 5 wolves on the bank | 0 left in all 4 cells |

- **The first SCV2 run tested nothing.** The pass does nothing unless the tool itself is on, and CTRL's tool is off; its status line still said "on". The reruns switch the tool on and print the pass's own counters each time.
- **Which species ate is not recorded.** The pass saw 6 to 21 scavengers each time. That includes CTRL's native ravens, which the tool lists as scavengers. The per-species count sits in the tool's ledger, which these cells didn't capture.
- **The teleport fallbacks never fired.** Carcasses were gone before the 600-tick wait ran out, so the fliers' landing and the wanderers' last step weren't exercised.
- **Almost no vanilla swimmer counts as a scavenger.** The tool counts a creature as a scavenger only if it eats bone or curious-beast food, or is on a short named list. In vanilla that leaves only pond grabbers, sea serpents and sea monsters among swimmers; alligators and sharks don't qualify. Whether carnivorous swimmers should count is your call.
- **A small status bug.** When no remains are left, the pass stops updating its last-pass counters, so the status line repeats the last pass that had any.

Data: `data/experiments/ECO/SCV-*` and `SCV2b-*`; one paragraph per block in `findings.md`.

### Relations for arrivals: who DF aims at whom (item 27)

On the surface, DF never pairs a wild predator with wild prey on its own; the tool's ecology write is the only source of that pairing. Every other entry DF writes runs between the fort's side and the arrival, or among cavern natives. Each row reads "the writer's row holds this toward the target". The off-target hunts in earlier placed-unit blocks (CAL, STL, LONE) come from row 3.

| # | Writer | Target | Relation | How often | Evidence |
| --- | --- | --- | --- | --- | --- |
| 1 | Citizen dwarves | Each new surface wild arrival | PREDATOR\_OR\_PREY | Every arrival, within about 3,000 ticks | RELS 159 entries; RELS2b dwarves toward the cougar (2) and kestrels (7–18) |
| 2 | Livestock and pets | Each new arrival | PREDATOR\_OR\_PREY | Most arrivals | RELS 107; RELS2b horse, yak and reindeer toward emus, ravens and kestrels |
| 3 | Units a script placed or the tool released (roaming flag cleared, so non-wild to DF) | Later wild arrivals | PREDATOR\_OR\_PREY | Often | RELS 57; RELS3 released ravens toward skunks (2) and kestrels (8) |
| 4 | The arrival | Fort units | BENIGN\_ANIMAL if the species is BENIGN, else DANGEROUS\_ANIMAL | Every arrival | RELS 662 and 15; RELS2b cougar toward dwarves DANGEROUS\_ANIMAL (5, 6) |
| 5 | Surface wild | Surface wild | PREDATOR\_OR\_PREY | Almost never | RELS 5; RELS2b a wild cougar with an owl and a kestrel, one entry each, in one replicate |
| 6 | Cavern wild | Cavern wild | PREDATOR\_OR\_PREY | Yes, both ways | RELS 38; RELS2b giant olm and crundle (9, 7) |

RELS2 forced each arrival's release, which clears the roaming flag, so every arrival became non-wild and DF aimed them at one another (kangaroo toward raven 56, wolf toward badger 36). That is row 3 applied to everything, an artefact of the release rather than DF's default. RELS2b dropped the forced release: the cougar arrived wild in both replicates and behaved as rows 1, 4 and 5 say.

Data: `data/experiments/ECO/RELS2-*`, `RELS2b-*`, `RELS3-*`, tallied by `scripts/rels2-tally.py` and `rels3-tally.py`.

### A season on v7.0 with the roster builder (items 8, 15, 16, 18)

The builder fills every slot it has candidates for and reports the gaps. On the surface, predators made 5–42% of arriving units; the v2.2 ladder aims at 14–18%. Giant jackal packs carried the overshoot on BOATS: wave counts stayed modest, but each pack is large. CTRL undershoots because its supply is mostly ravens. The apex slot barely shows up in a season: 0–3 apex animals arrived per run. Each run is 100,800 ticks (one season), 2 replicates, tool on.

| Run | Fort | Builder | Surface units / waves | Predators, % of surface units | Apex units | Deaths per surface arrival |
| --- | --- | --- | --- | --- | --- | --- |
| S8C | CTRL | off (control) | 45 / 7, 34 / 10 | 4%, 0% | 0, 0 | 0.87, 0.59 |
| S8B | BOATS | on | 76 / 19, 122 / 18 | 42%, 14% | 0, 3 (cheetah) | 1.28, 0.24 |
| S8O | OCEAN2 | on | 49 / 12, 41 / 12 | 18%, 39% | 2, 1 (anaconda) | 0.76, 0.61 |
| S8Cb | CTRL | on | 37 / 11, 37 / 13 | 5%, 5% | 0, 0 (cougar) | 0.51, 0.62 |

On CTRL the builder barely moves the surface: ravens make up most arrivals with or without it, so its predators stay at 5%. The apex never arrived on CTRL (4 runs), and on the other forts 0–3 a season. With SW4's apex in 1 run of 6 at any multiplier, the apex FREQUENCY doesn't visibly steer apexes (item 15). The recommendation: drop the apex step from the ladder and steer apexes by placement and stock instead.

- **The builder picks at random each run.** On BOATS, replicate 2 seated giraffe men and elephant men as grazers and drew 72 giraffe men. Animal people fill guild slots like their root animals, as you ruled.
- **Gaps are reported, not hidden.** BOATS has no water apex and no freshwater fish to pick, so those slots stay empty and the build output says so. Stingray and milkfish were dropped as isolated: no linked predator.
- **Plump helmet men swamp the caverns.** On BOATS, 54 and 180 arrived, about 15 per wave, in the cavern shore-prey slot. That slot needs a group-size cap.
- **No pelagic species on shallow oceans (item 18).** The survey at load found 0 of 5,374 ocean columns 3 or more levels deep on OCEAN2, so the pelagic slot stays closed and nothing can strand.
- **Placed orcas do strand (item 16).** In COHO's unled pods, 3 of 12 orcas died of drowning within 15,000 ticks; led pods lost none. An orca breathes only water, so drowning means it was out of water. Its raws carry BEACH\_FREQUENCY:10.
- **A deep layer delivers demons.** On CTRL, 15 and 16 demon units in 4–5 groups arrived on the deep layer in the builder-off control. The tool leaves demons unmanaged (D8).

Data: `data/experiments/S8C`, `S8B` and `S8O`, tallied by `scripts/s8-tally.py`. Sponges show up in the runner's arrival lists on OCEAN2 and BOATS and are ignored.

### Threshold sweep: which fixed values matter (item 11)

One lever moved the map: halving the predator ladder cut predators to about 2% of land animals. Of the group limits, the cavern cap trims only the tool's own share, and the water cap rarely binds. None of the other values changed kills or fights in a way that held up once the cell order was reversed. Each block ran 2 replicates; from SW3 on, the second replicate ran its arms in reverse order.

| Block | Value | Levels (current in bold) | Result | Change to the tool |
| --- | --- | --- | --- | --- |
| SW1, SW1R | Ecology cadence; nudge | 500, **1,500**, 6,000 ticks; off, **40 / 3,000 / r6**, tight | No effect, confirmed in reversed order. Over 4 replicates, placed prey killed per arm: 0–3. Wolf attacks on the herds: 145–243, with no pattern. The busy-ness gap followed cell position | Recommend a 3,000-tick cadence (half the passes) and the nudge off by default (no visible teleports) |
| SW2, SW2R | Pack-mass floor; sneak bonus | 0, **0.05**, 0.20; 0, **0.25**, 1.0 | No effect in either order. Placed prey killed over 4 replicates: 0–4 per arm, with 0 at sneak 1.0. The 20% floor's shift off the elephant didn't repeat | Recommend pack\_sneak 0 and retiring the per-unit SNEAK write; keep the floor at 0.05 (the arena can't isolate it) |
| SW3, SW3B | Land groups at once | 1, 3, **auto** | Counting land groups only (SW3B): auto 4.7 and 3.6 present, cap 3 at 3.6 and 2.6, cap 1 at 1.4 and 2.4, below auto in both orders. No fights in any cell | Keep auto |
| SW4 | Ladder, predator multiplier | ×0.5, **×1**, ×2 | Predators 1.8% and 1.9% at ×0.5, 10.6–14.0% at ×1. ×2 gave 20.1% and 6.9% depending on order. Apex present in 1 run of 6 | Keep ×1; it already overshoots the target on presence |
| SW5 | Cavern groups at once | 1, 2, **auto** | 14–16 cavern groups at caps 1 and 2 against 24–27 at auto, the same in both orders. DF's own 4–5 groups per cavern stay | Relabel it a soft target on the Layers tab; keep auto |
| SW6 | Water groups at once | 1, 2, **auto** | BOATS gets only 2–5 water groups. Cap 2 matched auto; cap 1 held in one replicate of two | Optional default 2; thin evidence |
| SW7 | ×3 pack bonus (builder) | 1, **3**, 5 | Only 8 of about 28 wanted species exist on CTRL. Land groups and fights were the same at every level | Remove the ×3 weight, as design rule R11 already leans |

What the night taught the method. The first sweep cells shared one fort load per replicate and always ran in the same order. Natives that arrived during the replicate filled the later cells: in SW1's last two arms, the placed wolves made only 12–58% of the attacks, against about 90% in the control. Three fixes now apply:

- every busy-ness flag requires both replicates on the same side of the control;
- the arena blocks also print a placed-animals-only readout;
- the runner alternates cell order between replicates.

Data: `data/experiments/ECO/SW-*`, `SW4-*`, `SW-rig2-*`, tallied by `scripts/sweep-tally.py`; the reruns land in `SWR-*`.

### Good and evil forts, cavern invasions, the cavern gate (items 6 and 25)

- **Good and evil forts (item 6).** On region6 I embarked GOODF on a good tundra tile and EVILF on an evil shrubland tile. On each, the map's own alignment counts as natural and the tool manages it. GOODF manages fluffy wamblers, pixies and fairies; EVILF manages harpies, ogres, blood gnats, knuckle worms and demon rats. The opposite alignment becomes mythic and stays locked, and so do all ten night creatures. On EVILF, a blind cave ogre and two gorlaks appeared with no pool entry, because the cavern layer is off by default on a fresh embark. With it switched on, both are natural and unlocked, as v7.0 intends.
- **Cavern invasions (E23e).** BOATS's caverns hold 334 animal-person and civ-race populations. Two seasons with the caverns marked discovered, irritation pinned at 300,000 and three dwarves on the cavern floor raised no invasion: 0 invaders at every sample in all four runs. Flags alone don't trigger one; the trigger needs real excavation, wealth or population.
- **The halved cavern gate (T9c).** Under pressure, the gap to the next cavern wave shortened from 8–20 days to 3–9. But waves then sat overdue for up to 42 days, and cavern animals were no more numerous: 18–20 present against 21–25 in the control. The gate isn't what limits cavern traffic.

### Validation of v7.0 (item 32)

The full validator passes v7.0: 214 PASS, 0 FAIL, 0 DEAD, 30 not testable on the forts it loads, 13 backlog. The first run failed 4 claims, all written before v7.0 and contradicted by v7.0's intended changes:

- the largest male now leads;
- per-water-body and per-cavern limits word the output differently;
- the tool's seasons override NO\_\<season>.

Those claims are now v7.0-aware, and the v7.0 claims that test the new behaviour directly pass. The 2 doc-drift notes are release steps: the USAGE.md header version and the Docket's version line.

## Recommended changes to seasonal-wildlife

The first five fix the ecology the tool writes today. The rest add the levers this suite showed work.

| # | Change | Evidence | Effort | v6.9 (released 30 Sep; validate-full 192 PASS, 0 FAIL) / v7.0 (built on a branch, not deployed) |
| --- | --- | --- | --- | --- |
| 1 | Filter the relation write through `eats()` (habitat reach, size, class) | 58% of written pairs fail the tool's own rules; shark × deer and wolf × pike made 0 attacks | Small: call `eats()` in `ecoWrite` | In: the write keeps only pairs the predator can reach |
| 2 | Arm every non-BENIGN carnivore, not only LARGE\_PREDATOR; never arm BENIGN | The coyote killed deer; fox, badger and a BENIGN wolf never attacked | Small: change `ecoArmed` | v6.9: in. v7.0 reverses 'never arm BENIGN': it clears BENIGN on every predator the roster arms (your ruling) |
| 3 | Bring water-layer units into the ecology, with realm from habitat (land / water / amphibious both) | Alligators and crocodiles killed 4–5 of 8 land prey from the water; sharks took seals in the water | Medium: `ecoRealm` + placement | In: water units in the surface realm, amphibious both ways |
| 4 | Read BENIGN on prey: warn, or cap group sizes, where non-BENIGN prey outguns the predator | Capybaras killed 5 of 5 wolves; buffalo killed a lion | Small: a pairing check | v7.0: a 5% pack-mass floor on the group present, and a sneak bonus at 25% |
| 5 | Respect the raw NO\_\<season> flags when dealing seasons, and use them as a season gate | 22 NO\_WINTER species can be dealt Winter; NO\_SPRING set at run time stopped 100% of spring waves | Small | v6.9: the deal and the water draw respect the flag. Reversed in v7.0: the tool's deal wins, and NO\_\<season> is cleared on managed species |
| 6 | Scavenging as walk-and-delete for a 23-species set (BONECARN, food thieves, carrion eaters) | Nothing in DF eats remains; a full path moved hyenas in 300 ticks; the deletion survived a reload | Medium: a job with a path builder and a reach check | In, opt-in: a path only along a clear line (the blind cavern path failed in HC1); v7.0: remains anywhere outside stockpiles |
| 7 | Hold curious beasts: clear CURIOUS\_BEAST\* while the tool keeps them as residents, restore on off | 18 of 18 placed bears and raccoons left within 3,000 ticks; 0 of 6 with the flags off | Small, species-wide | In: curious TOKEN resident\|thief |
| 8 | Combat alert filter (animal vs animal only), as a setting | Drops wild-only alerts, keeps fights with dwarves, safe across a save and reload | Small: done as a prototype | In: on by default, Panel switch, alerts on\|off |
| 9 | Exhaustion watcher and niche replacement by guild | A 0 entry stopped the species though the extinct flag stayed false; the replacement took over in about 2,000 ticks | Small | In: same guild first, season given back at the boundary |
| 10 | Groups at once = √(embark tiles) + 1 | ECO2-G: +1 group at 5×5 and 6×6 in every replicate, no change up to 4×4, no speed cost | Trivial | In: the land default (v6.9); v7.0 gives every water body and cavern depth its own √ + 1 limit |
| 11 | FREQUENCY as the balancing dial, including the roster's weights | Shares proportional within a few points | Already the odds lever; extend to the roster | Superseded: picks are uniform (×3 for packs), and the v2.2 ladder sets FREQUENCY last |
| 12 | Deep-water class: open-ocean species rare unless the map has 3+-level columns | OCEAN2 has none, BOATS has 33% | Small: one map survey at load | In part: pelagic draw weight inverse to size, floor 0.1; no depth survey yet |
| 13 | Leader = largest male (optional; same cohesion as lowest id) | Both hold a herd within 2–4 tiles; a led herd was barely attacked | Trivial | v7.0: the largest adult male leads |
| 14 | Build the default roster and food web by guilds, with the nine rule fixes | Guild-first v2.1: 0% isolated on the surface, every unit edge armed (81% measured reach, 19% untested), 0 mutual predation | Large: a new builder | Builder v2.2 run offline (civ races hunt and are prey); its port into v7.0 is next |
| 15 | Realm table as optional tool data (Arctic and Antarctic kept apart by the table) | The raws hold no geography | Medium: data, plus a placement path outside home biomes | Open |
| 16 | Solitary-hunter package: natural skills 10, no sneak slowdown, AMBUSHPREDATOR | LONE: 22 kills against 14 in 5 seasons each (p = 0.13); STL and STL2 pooled p = 0.35 | Small | v7.0, your decision |
| 17 | Manage GOOD/EVIL wildlife on matching regions; fix the Vermin-tab leak, cavern GOOD/EVIL and FANCIFUL locks | Code audit: 8 GOOD and 24 EVIL species were locked as mythic | Medium | v7.0; needs a good and an evil fort test |
| 18 | Cavern civ races hunt and are prey of cavern apexes; never write a relation that involves a forgotten beast or megabeast | Builder: 20 singletons to 0. Audit found two paths that could touch beast entries | Small | v7.0, both paths fixed |
| 19 | Sweep: clear DF's own PREDATOR\_OR\_PREY entries between managed wildlife the roster doesn't pair | RELP: DF writes these itself; natives were half of LONE's kills | Medium | v7.0, with a count of pairs DF writes back |
| 20 | Fishing land predators (bears, tiger, jaguar) get edges to fish | FISH: wolves made 0 kills on pike in every arm | Small | v7.0, on; I recommend off |
| 21 | Slot set-up and departed-slot clears write 0 (STRANGER), not empty | E11c: predators fight units they read as STRANGER | Small | Fixed in v7.0 (3c26941): SLOTV showed DF's empty value is NONE (-1); both paths now write it |

Not recommended: CRAZED or OPPOSED\_TO\_LIFE as predation levers (they send wildlife at the fort), and UBIQUITOUS at run time (it does nothing at the pick).

## Open questions and next experiments

Every item below is done; v7.0 validates at 214 PASS, 0 FAIL. What remains are your decisions on what the night found. None of them is applied to the tool yet:

1. **Defaults the sweep supports:**
   - Ecology cadence 3,000 ticks instead of 1,500.
   - The nudge off by default.
   - Sneak bonus 0, and retire the per-unit SNEAK write.
   - Remove the builder's ×3 pack bonus.
   - Drop the apex step from the FREQUENCY ladder; steer apexes by placement and stock.
   - Relabel the cavern groups limit as a soft target.
2. **Carnivorous swimmers as scavengers.** Only pond grabbers, sea serpents and sea monsters qualify in vanilla today. Should alligators, crocodiles and sharks count?
3. **A group-size cap for animal people in caverns.** Plump helmet men arrived about 15 per wave on BOATS.
4. **Add invasive for SAVAGE species on calm maps.** DF never draws them, so the tool would have to place them.
5. **Pushing.** Nothing from tonight is pushed: DwarfCron `Dev` and seasonal-wildlife `v7.0` are local only.

| # | Item | What's missing | Next step | When |
| --- | --- | --- | --- | --- |
| 1 | Pack-mass floor | Its value. 5% allows every kill measured so far; 20% forbids the elephant kills CAL saw | Decided 30 Sep: 5% for an edge, sneak bonus at 25%; built in v7.0 | Done |
| 2 | Cavern fliers split off into their own web | What cavern raptors, bats and floaters may eat once sentients are off their menu | Done in v2.2 (bats eat vermin, cavern raptors eat bats and land prey). REACH: giant bats killed 5 of 12 crundles | Done |
| 3 | Insect men and bird men never make a flying roster | The apex-only rule leaves them no allowed attacker (646 pool cells) | Done in v2.2: a flying apex takes flying animal people (880 of 880 savage flying rosters) | Done |
| 4 | Skills for solitary hunters (STL2) | Answered: no. Pooled over STL and STL2, skilled hunters killed in 10 of 48 runs and unchanged ones in 2 of 16 | Done. A lone hunter's limit is meeting prey at all | Done |
| 5 | Port the roster builder into the tool (v7.0) | ROSTER.build, the unfilled-slot report and pair fallback, the ladder, BENIGN clears, the pelagic slot, index addressing for the 36 ids with a space or comma | Done in v7.0 (0d030b2): ROSTER.build, slots, ladder, the unfilled-slot report and `roster build`. It ran on CTRL, BOATS and OCEAN2 tonight (S8) | Done |
| 6 | GOOD/EVIL/FANCIFUL fixes | The Vermin-tab leak, cavern GOOD/EVIL classed as natural, FANCIFUL dropped from the mythic test | Done on GOODF and EVILF (region6): a map's own alignment is natural and managed; the opposite alignment and night creatures are locked. Cavern evil species class as natural once the cavern layer is on | Done |
| 7 | NATURAL\_SKILL written by the tool | Built in v7.0 at your decision. LONE leans its way (22 against 14 kills, p = 0.13); 10 runs per arm would settle it | Write the skill on each solitary hunter's castes at arming; restore when the tool is off | Done |
| 8 | A season with v7.0 on CTRL and BOATS | Arrivals by tier against the ladder, kills against arrivals, and whether 31% predator arrivals on land is too many | Done: surface predators 5% (CTRL), 14–42% (BOATS), 18–39% (OCEAN2) against the 14–18% target; the overshoot is pack size, the undershoot CTRL's raven-heavy supply | Done |
| 9 | Raptor block | The whole flying layer: flier-on-flier reach (3,007 edges), BENIGN-cleared raptors, giant raptors | Ran (REACH): kea killed 5 of 12 parrots, the BENIGN-cleared eagle 2 of 12 ravens and no rabbits | Done |
| 10 | Giant pack block (savage) | Whether giant hyenas and dingoes take elephants and rhinoceros, and giant crocodilians hippos | Done (GPK): giant hyenas killed both elephants in both runs, giant dingoes 1 of 2 rhinoceros per run, giant saltwater crocodiles both hippos in all 4 runs | Done |
| 11 | Threshold sweep: the ecology's sweet spot | Every hard-coded value (ladder steps, ×3 pack bonus, pack-mass floor, size preference, groups at once) tuned against how busy the map is | Done (SW1–SW7 plus reruns): only the ladder multiplier moves the map (×0.5 cuts predators to 2%). Cadence, nudge, floor, sneak and pack bonus show no effect; the cavern cap is a soft target. Recommended defaults are in the sweep table | Done |
| 12 | Are lake species writable? | Whether lake species are feature entries (no realm) or surface ones | Done (LAKEP): lake units sit in the surface realm; 21 of 21 written pairs held to 3,000 ticks | Done |
| 13 | Vermin predation | Never observed: dense spots are bumblebee and termite colonies nothing hunts | VRM2 (a fresh fort per arm): native gobblers and badgers with a written token took roaches only; cats took everything. The background eater was CTRL's own two cats (VRM3b) | Done |
| 14 | Cavern species that fight with no relation | Species or spot? | Done (HC4): mostly the species, 5 of 8 pairs behaved the same at a second spot; keep the cavern write | Done |
| 15 | Does the apex FREQUENCY matter? | DF may draw large predators from their own pool | Done: no. Apex arrivals 0 in all 4 CTRL runs, 0–3 elsewhere, and 1 run of 6 in SW4 at any multiplier. Steer apexes by placement and stock | Done |
| 16 | Placed orcas and sperm whales stranding | BEACH\_FREQUENCY on placed units | Done: placed orcas strand when unled (3 of 12 drowned in 15,000 ticks, none with a leader). The builder never draws pelagics on a shallow ocean | Done |
| 17 | Add invasive with a SAVAGE species on a calm map | Whether DF keeps sending it | Done (INV2): with the smilodon's entry present, DF drew none onto calm CTRL in a season. The tool must place SAVAGE invasives itself on calm maps | Done |
| 18 | Deep-water survey at load | Pelagic weight still ignores map depth | Done in v7.0: the build reports deep columns at load (OCEAN2: 0 of 5,374 at 3+ levels, so the pelagic slot stays shut) | Done |
| 19 | Scavenging extensions | A pack after a kill, jackals, fliers, corpses in water, cavern miasma first | Done: with the tool on, v7.0's pass clears land and water carcasses in about 2,400 ticks. Not yet measured: which species ate. For you: should carnivorous swimmers count as scavengers? | Done |
| 20 | School, flock and pod cohesion with a leader | Only herds and packs on land were tested | Done (COH): a leader holds flocks and schools to 5–30 tiles; a led orca pod is half as wide | Done |
| 21 | Realm table (recommendation 15) | No implementation planned | Built in v7.0 (e8cbda7) as optional data behind the `realms` switch, off by default; `realm` sets the embark's realm. Not rig-tested | Done |
| 22 | Leader = largest male (recommendation 13) | Implemented in v7.0 at your ruling | Park | Done |
| 23 | Prey that outguns its predator (recommendation 4) | A pairing warning | Done in v7.0 (89662c5): the builder warns when prey outguns its predator by 2× or more. Tonight's builds printed it, for example "CHEETAH pack vs GIANT\_JACKAL herd 18.4x" | Done |
| 24 | FLEEQUICK and VISION\_ARC | Their two replicates disagreed; the tool doesn't use them | Done (FVA): no reliable effect over 2 more replicates; parked | Done |
| 25 | Wilderpop §8 and rig speed | T9c cavern gate under pressure, T8g, E42c pairs, E23e animal people in caverns; FPS1 (why the rig runs slower than your game) | Done: T9c (the halved gate buys no traffic), E23e (no cavern invasion from flags, even with animal people present), E42c answered by X4, FPS1 and T8g earlier | Done |
| 26 | Your question "where is the optimal…" | Answered: thresholds for every decision | Item 11 | Done |
| 27 | DF writes predator relations itself | How often, and between whom: RELP saw PREDATOR\_OR\_PREY entries between a placed lion, livestock and a wild kestrel within 3,000 ticks, and STL2's unrelated lion killed 8 badgers | Done (RELS, RELS2b, RELS3): DF aims citizens, livestock and placed units at each arrival; surface wild never pairs with surface wild. v7.0's sweep clears the pairs the roster doesn't make | Done |
| 28 | Cavern civ races hunt and are prey | They were the last 20 singletons | Done in v2.2 and v7.0, with forgotten beasts and megabeasts never written | Done |
| 29 | Slot clears write STRANGER (0), not empty | What DF itself leaves in a fresh slot | SLOTV: every unused slot and every unrelated pair reads NONE (-1); STRANGER is never DF's default. Both paths fixed in v7.0 (3c26941) | Done |
| 30 | Vegetation survey at load | v2.2's vegetation link for big herbivores needs a measure of the map's grass, shrubs and trees | Done in v7.0 (df0aa83): each build reports a vegetation index. Tonight's builds read 52 on BOATS and 47 on OCEAN2, and kept hippos and platypus by the vegetation link | Done |
| 31 | GOBBLE\_VERMIN writes in the tool | Whether a written gobble class or creature makes a consumer eat vermin | Done: VRM4 shows DF honours a class the tool writes at runtime (4 and 6 eaten against 0 and 0); vermin classes and gobble writes are in v7.0 | Done |
| 32 | Deploy and validate v7.0 | 23 new validator checks (alignment, groups per layer, seasons, solo package, pack floor, sweep, civ and beast safety) | Done: validate-full on v7.0 (1e65e03), 214 PASS, 0 FAIL, after 4 pre-v7.0 claims were made v7.0-aware. Release steps left: USAGE.md header, Docket, merge and push | Done |
| 33 | Fishing land predators | FISH: wolves never caught pike, even with water-breathing | Done (FSH2): 0 attacks in 6 runs; fishers now default off in v7.0 (3ca528c) | Done |
| 34 | Does the solitary package lift kills? | LONE leans its way but 5 runs per arm can't separate it (p = 0.13) | Done: LONE10, kills 29 against 14 (p = 0.025); the lift is mostly on natives | Done |

## Data, code and sources

Everything is in the DwarfCron repository, commit f7949f3 on branch Dev.

| What | Where |
| --- | --- |
| Design | `experiments/ECO-design.md` |
| In-game instrument | `chronicler/dfhack/scripts/cx-eco.lua` |
| Block runner and analysis | `scripts/eco-run.py`, `scripts/eco-analyze.py` |
| Cell data (P1 P2 T1 S S2 B L1 L2 A1 W1L W1O O OS DEPTH DEPTHL) | `data/experiments/ECO/20260929-235553/` |
| Spawn-time runs | `data/experiments/ECO-F1`, `ECO-T2`, `ECO-N1`, `ECO-G1` (manifests in `experiments/`) |
| Wiki token table, raws census, tool audit, token triage, guilds, realms, scavenger sets | `data/eco-desk/` |
| Roster-rule prototype and its results | `data/eco-desk/roster/` (`results.md` first) |
| Later blocks (ECO2, TV2, ECO3 PK and WB, CAL, STL, STL2, RELP, LONE, REACH, VRM, RELS, SLOTV) and their logs | data/experiments/ECO/\<block>-\<date>/, data/logs/ |
| Every block's findings in one file | data/eco-desk/findings.md |
| Tallies for the lone-hunter blocks | scripts/stl-tally.py, scripts/lone-tally.py |
| Roster builder v2, v2.1, v2.2: rules, results, GOOD/EVIL table, civ races | data/eco-desk/v2/guilds/ (design.md, results.md, results21.md, results22.md, ge22.md, civ22.out) |
| Research: vermin and gobbling, DF's own relation writes | data/eco-desk/v2/research/ (vermin.md, relations.md, lua/) |
| Tool v7.0 (not deployed) | seasonal-wildlife, branch v7.0: 49fde90, 355801f, 093629c |

Token definitions come from the wiki's [Creature token](https://dwarffortresswiki.org/index.php/Creature_token) page and the pages it links, read as raw wikitext. Tool behaviour comes from seasonal-wildlife v6.8.0 source; the rig ran v6.7.0. DF 53.16, DFHack 53.16-r1.1.
