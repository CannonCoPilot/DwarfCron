# APEX boost: every species admitted (DF 53.16 vanilla + extinct, natural class)

Rule (user rule 2): IF (guild in {AL apex hunter land, AW water apex, ML ground mesocarnivore, RP raptor} OR CARNIVORE) AND (giant variant OR adult body size >= 1,000,000 cm3) THEN apex, with or without LARGE_PREDATOR, with or without BENIGN.

Readings (stated, not inferred from names):
- CARNIVORE is read as CARNIVORE or BONECARN. Wiki: BONECARN "implies CARNIVORE"; the raws never write both.
- ORCA, GIANT_ORCA and GIANT_CUTTLEFISH carry no diet token and are BENIGN. They enter only through the tool's curated predator override (SW:982). The literal rule would exclude ORCA, which the brief names as an intended case.
- Giant = census kind `giant` (APPLY_CREATURE_VARIATION:GIANT) or an id starting GIANT_. Mass = the tool's adult mass (cm3).
- Native apex = AL/AW (LARGE_PREDATOR) below the size/giant bar. They hold the apex slot without the boost.
- BENIGN apex must have BENIGN cleared by the tool before DF acts on a written relation (T1: BENIGN on WOLF + write = 0 attacks; BENIGN off DEER = it attacked). Sentient apex may not attack by default (roster2 `sentient_attack=False`).
- Every giant and every animal person is SAVAGE in the raws (wiki: SAVAGE creatures "only show up in savage biomes"). So the boosted giants exist only on savage embarks. 99 of 100 extinct species are also SAVAGE; CRETACEOUS_CARNOTAURUS is not.

## Counts

| group | boosted | of which BENIGN | of which sentient | curious beast |
|---|---|---|---|---|
| vanilla giants | 63 | 15 | 0 | 8 |
| vanilla natural (non-giant) | 5 | 2 | 0 | 0 |
| vanilla animal people | 1 | 1 | 1 | 0 |
| extinct | 10 | 1 | 0 | 0 |
| extinct animal people | 10 | 1 | 10 | 0 |
| **total** | **89** | **20** | **11** | **8** |

Boosted by guild: ML 34, AL 22, AW 14, RP 10, MW 9. Native apex (not boosted): 90 (38 sentient, 0 BENIGN).

## BENIGN apex: the tool must clear BENIGN to arm them (20)

CRETACEOUS_ARCHELON_MAN (MW, 2.68M), CRETACEOUS_ARCHELON (MW, 2.68M), SPERM_WHALE_MAN (MW, 25.00M), GIANT_WOLVERINE (ML, 0.34M), BADGER, GIANT (ML, 0.31M), GIANT_OTTER (ML, 0.27M), GIANT_FOX (ML, 0.24M), GIANT_MONGOOSE (ML, 0.22M), GIANT_POND_TURTLE (ML, 0.20M), GIANT_STOAT (ML, 0.20M), GIANT_SPERM_WHALE (MW, 200.00M), GIANT_ORCA (MW, 40.00M), GIANT_EAGLE (RP, 0.23M), GIANT_SNOWY_OWL (RP, 0.21M), GIANT_OSPREY (RP, 0.21M), GIANT PEREGRINE FALCON (RP, 0.21M), GIANT_BARN_OWL (RP, 0.20M), GIANT_KESTREL (RP, 0.20M), SPERM_WHALE (MW, 25.00M), ORCA (MW, 5.00M)

## Sentient apex: excluded as attackers by default (11 boosted + 38 native)

Boosted: CRETACEOUS_TYRANNOSAURUS_MAN, JURASSIC_TORVOSAURUS_MAN, JURASSIC_ALLOSAURUS_MAN, CRETACEOUS_CARNOTAURUS_MAN, CENOZOIC_MEGALODON_MAN, CRETACEOUS_MOSASAURUS_MAN, CRETACEOUS_SPINOSAURUS_AEGYPTIACUS_MAN, CRETACEOUS_SPINOSAURUS_MIRABILIS_MAN, DEVONIAN_DUNKLEOSTEUS_MAN, CRETACEOUS_ARCHELON_MAN, SPERM_WHALE_MAN

Native: JURASSIC_AFROVENATOR_MAN, CENOZOIC_ANDREWSARCHUS_MAN, JURASSIC_CERATOSAURUS_MAN, PERMIAN_ANTEOSAURUS_MAN, CRETACEOUS_UTAHRAPTOR_MAN, CENOZOIC_MEGALANIA_MAN, JURASSIC_DILOPHOSAURUS_MAN, CENOZOIC_SMILODON_MAN, CENOZOIC_KELENKEN_MAN, CRETACEOUS_DEINONYCHUS_MAN, CENOZOIC_THYLACINE_MAN, CRETACEOUS_VELOCIRAPTOR_MAN, JURASSIC_ICHTHYOSAURUS_MAN, JURASSIC_PLESIOSAURUS_MAN, PERMIAN_HELICOPRION_MAN, SILURIAN_JAEKELOPTERUS_MAN, PERMIAN_DIMETRODON_MAN, DEVONIAN_TIKTAALIK_MAN, BEAR_POLAR_MAN, TIGER_MAN, BEAR_GRIZZLY_MAN, LION_MAN, BEAR_BLACK_MAN, ANACONDA_MAN, JAGUAR_MAN, COUGAR_MAN, HYENA_MAN, LEOPARD_MAN, CHEETAH_MAN, WOLF_MAN, DINGO_MAN, CROCODILE_SALTWATER_MAN, ALLIGATOR_MAN, TROGLODYTE, RODENT MAN, REPTILE_MAN, SERPENT_MAN, AMPHIBIAN_MAN

## Full list: boosted apex (89)

| id | admitted by | source / kind | guild | adult cm3 | layer | flags |
|---|---|---|---|---|---|---|
| CRETACEOUS_TYRANNOSAURUS_MAN | guild AL+BONECARN+size 6.2M | extinct / animal_person | AL | 6,250,000 | land | **sentient** |
| JURASSIC_TORVOSAURUS_MAN | guild AL+BONECARN+size 2.2M | extinct / animal_person | AL | 2,177,000 | land | **sentient** |
| JURASSIC_ALLOSAURUS_MAN | guild AL+BONECARN+size 2.0M | extinct / animal_person | AL | 2,000,000 | land | **sentient** |
| CRETACEOUS_CARNOTAURUS_MAN | guild AL+BONECARN+size 1.7M | extinct / animal_person | AL | 1,700,000 | land | **sentient** |
| CENOZOIC_MEGALODON_MAN | guild AW+CARNIVORE+size 23.3M | extinct / animal_person | AW | 23,269,000 | ocean | **sentient** |
| CRETACEOUS_MOSASAURUS_MAN | guild AW+CARNIVORE+size 12.5M | extinct / animal_person | AW | 12,500,000 | ocean | **sentient** |
| CRETACEOUS_SPINOSAURUS_AEGYPTIACUS_MAN | guild AW+BONECARN+size 7.4M | extinct / animal_person | AW | 7,400,000 | land + water | **sentient** |
| CRETACEOUS_SPINOSAURUS_MIRABILIS_MAN | guild AW+BONECARN+size 7.4M | extinct / animal_person | AW | 7,400,000 | land + water | **sentient** |
| DEVONIAN_DUNKLEOSTEUS_MAN | guild AW+CARNIVORE+size 2.5M | extinct / animal_person | AW | 2,500,000 | ocean | **sentient** |
| CRETACEOUS_ARCHELON_MAN | CARNIVORE+size 2.7M | extinct / animal_person | MW | 2,676,000 | ocean | **BENIGN**, **sentient**, not LP |
| CRETACEOUS_TYRANNOSAURUS | guild AL+BONECARN+size 6.2M | extinct / plain | AL | 6,250,000 | land |  |
| JURASSIC_TORVOSAURUS | guild AL+BONECARN+size 2.2M | extinct / plain | AL | 2,177,000 | land |  |
| JURASSIC_ALLOSAURUS | guild AL+BONECARN+size 2.0M | extinct / plain | AL | 2,000,000 | land |  |
| CRETACEOUS_CARNOTAURUS | guild AL+BONECARN+size 1.7M | extinct / plain | AL | 1,700,000 | land |  |
| CENOZOIC_MEGALODON | guild AW+CARNIVORE+size 23.3M | extinct / plain | AW | 23,269,000 | ocean |  |
| CRETACEOUS_MOSASAURUS | guild AW+CARNIVORE+size 12.5M | extinct / plain | AW | 12,500,000 | ocean |  |
| CRETACEOUS_SPINOSAURUS_AEGYPTIACUS | guild AW+BONECARN+size 7.4M | extinct / plain | AW | 7,400,000 | land + water |  |
| CRETACEOUS_SPINOSAURUS_MIRABILIS | guild AW+BONECARN+size 7.4M | extinct / plain | AW | 7,400,000 | land + water |  |
| DEVONIAN_DUNKLEOSTEUS | guild AW+CARNIVORE+size 2.5M | extinct / plain | AW | 2,500,000 | ocean |  |
| CRETACEOUS_ARCHELON | CARNIVORE+size 2.7M | extinct / plain | MW | 2,676,000 | ocean | **BENIGN**, not LP |
| SPERM_WHALE_MAN | CARNIVORE+size 25.0M | vanilla / animal_person | MW | 25,000,000 | ocean | **BENIGN**, **sentient**, not LP |
| GIANT_BEAR_POLAR | guild AL+BONECARN+giant | vanilla / giant | AL | 3,268,000 | land | curious beast |
| GIANT_TIGER | guild AL+CARNIVORE+giant | vanilla / giant | AL | 1,894,500 | land |  |
| GIANT_BEAR_GRIZZLY | guild AL+giant | vanilla / giant | AL | 1,700,000 | land | curious beast |
| GIANT_LION | guild AL+CARNIVORE+giant | vanilla / giant | AL | 1,700,000 | land |  |
| GIANT_BEAR_BLACK | guild AL+giant | vanilla / giant | AL | 1,084,800 | land | curious beast |
| GIANT_ANACONDA | guild AL+CARNIVORE+giant | vanilla / giant | AL | 933,000 | land |  |
| GIANT_JAGUAR | guild AL+CARNIVORE+giant | vanilla / giant | AL | 745,500 | land |  |
| GIANT_COUGAR | guild AL+CARNIVORE+giant | vanilla / giant | AL | 633,600 | land |  |
| GIANT_HYENA | guild AL+BONECARN+giant | vanilla / giant | AL | 633,600 | land |  |
| GIANT_LEOPARD | guild AL+CARNIVORE+giant | vanilla / giant | AL | 560,000 | land |  |
| GIANT_CHEETAH | guild AL+CARNIVORE+giant | vanilla / giant | AL | 560,000 | land |  |
| GIANT_WOLF | guild AL+BONECARN+giant | vanilla / giant | AL | 486,800 | land |  |
| GIANT_DINGO | guild AL+BONECARN+giant | vanilla / giant | AL | 341,800 | land |  |
| GIANT_CROCODILE_SALTWATER | guild AW+CARNIVORE+giant | vanilla / giant | AW | 6,440,000 | land + water |  |
| GIANT_ALLIGATOR | guild AW+CARNIVORE+giant | vanilla / giant | AW | 3,268,000 | land + water |  |
| GIANT_JUMPING_SPIDER | guild ML+CARNIVORE+giant | vanilla / giant | ML | 2,000,070 | land | not LP |
| GIANT_BROWN_RECLUSE_SPIDER | guild ML+CARNIVORE+giant | vanilla / giant | ML | 2,000,070 | land | not LP |
| GIANT_PYTHON | guild ML+CARNIVORE+giant | vanilla / giant | ML | 1,700,000 | land | not LP |
| GIANT_MONITOR_LIZARD | guild ML+CARNIVORE+giant | vanilla / giant | ML | 933,000 | land | not LP |
| GIANT_BARK_SCORPION | guild ML+CARNIVORE+giant | vanilla / giant | ML | 666,730 | land | not LP |
| GIANT_SNAPPING_TURTLE | guild ML+CARNIVORE+giant | vanilla / giant | ML | 414,000 | land + water | not LP |
| GIANT_OCELOT | guild ML+CARNIVORE+giant | vanilla / giant | ML | 377,750 | land | not LP |
| GIANT_LYNX | guild ML+CARNIVORE+giant | vanilla / giant | ML | 377,750 | land | not LP |
| GIANT_WOLVERINE | guild ML+BONECARN+giant | vanilla / giant | ML | 341,800 | land | **BENIGN**, not LP |
| BADGER, GIANT | guild ML+BONECARN+giant | vanilla / giant | ML | 306,000 | land | **BENIGN**, not LP, id has space/comma |
| GIANT_COYOTE | guild ML+BONECARN+giant | vanilla / giant | ML | 306,000 | land | not LP |
| GIANT_JACKAL | guild ML+BONECARN+giant | vanilla / giant | ML | 306,000 | land | not LP |
| HONEY BADGER, GIANT | guild ML+BONECARN+giant | vanilla / giant | ML | 298,900 | land | curious beast, not LP, id has space/comma |
| GIANT_OTTER | guild ML+BONECARN+giant | vanilla / giant | ML | 270,500 | land + water | **BENIGN**, not LP |
| GIANT_BUSHMASTER | guild ML+CARNIVORE+giant | vanilla / giant | ML | 259,840 | land | not LP |
| GIANT_BOBCAT | guild ML+CARNIVORE+giant | vanilla / giant | ML | 256,320 | land | not LP |
| GIANT_RATTLESNAKE | guild ML+CARNIVORE+giant | vanilla / giant | ML | 249,270 | land | not LP |
| GIANT_FOX | guild ML+BONECARN+giant | vanilla / giant | ML | 242,160 | land | **BENIGN**, not LP |
| GIANT_COATI | guild ML+CARNIVORE+giant | vanilla / giant | ML | 242,160 | land | curious beast, not LP |
| GIANT_KING_COBRA | guild ML+CARNIVORE+giant | vanilla / giant | ML | 242,160 | land | not LP |
| GIANT_BLACK_MAMBA | guild ML+CARNIVORE+giant | vanilla / giant | ML | 235,100 | land | not LP |
| GIANT_IGUANA | guild ML+CARNIVORE+giant | vanilla / giant | ML | 228,040 | land | not LP |
| GIANT_MONGOOSE | guild ML+BONECARN+giant | vanilla / giant | ML | 221,040 | land | **BENIGN**, not LP |
| GIANT_GILA_MONSTER | guild ML+CARNIVORE+giant | vanilla / giant | ML | 214,020 | land + water | not LP |
| GIANT_KINGSNAKE | guild ML+CARNIVORE+giant | vanilla / giant | ML | 210,510 | land | not LP |
| GIANT_SKINK | guild ML+CARNIVORE+giant | vanilla / giant | ML | 203,500 | land | not LP |
| GIANT_POND_TURTLE | guild ML+CARNIVORE+giant | vanilla / giant | ML | 203,500 | land + water | **BENIGN**, not LP |
| GIANT_COPPERHEAD_SNAKE | guild ML+CARNIVORE+giant | vanilla / giant | ML | 203,500 | land | not LP |
| GIANT_STOAT | guild ML+BONECARN+giant | vanilla / giant | ML | 202,450 | land | **BENIGN**, not LP |
| GIANT_LIZARD | guild ML+CARNIVORE+giant | vanilla / giant | ML | 201,400 | land | not LP |
| GIANT_CHAMELEON | guild ML+CARNIVORE+giant | vanilla / giant | ML | 201,040 | land | not LP |
| GIANT_ADDER | guild ML+CARNIVORE+giant | vanilla / giant | ML | 201,040 | land | not LP |
| GIANT_ANOLE | guild ML+CARNIVORE+giant | vanilla / giant | ML | 200,620 | land | not LP |
| GIANT_LEOPARD_GECKO | guild ML+CARNIVORE+giant | vanilla / giant | ML | 200,350 | land | not LP |
| GIANT_SPERM_WHALE | CARNIVORE+giant | vanilla / giant | MW | 200,000,000 | ocean | **BENIGN**, not LP |
| GIANT_ORCA | tool override+giant | vanilla / giant | MW | 40,000,000 | ocean | **BENIGN**, not LP |
| GIANT_OCTOPUS | CARNIVORE+giant | vanilla / giant | MW | 235,100 | ocean | not LP |
| GIANT_CUTTLEFISH | tool override+giant | vanilla / giant | MW | 207,010 | ocean | not LP |
| GIANT_VULTURE | guild RP+BONECARN+giant | vanilla / giant | RP | 263,430 | flying | curious beast, not LP |
| GIANT_EAGLE | guild RP+BONECARN+giant | vanilla / giant | RP | 228,040 | flying | **BENIGN**, not LP |
| GIANT_SNOWY_OWL | guild RP+BONECARN+giant | vanilla / giant | RP | 214,020 | flying | **BENIGN**, not LP |
| GIANT_OSPREY | guild RP+BONECARN+giant | vanilla / giant | RP | 214,020 | flying | **BENIGN**, not LP |
| GIANT_GREAT_HORNED_OWL | guild RP+BONECARN+giant | vanilla / giant | RP | 214,020 | flying | not LP |
| GIANT_BUZZARD | guild RP+BONECARN+giant | vanilla / giant | RP | 209,800 | flying | curious beast, not LP |
| GIANT PEREGRINE FALCON | guild RP+BONECARN+giant | vanilla / giant | RP | 207,700 | flying | **BENIGN**, not LP, id has space/comma |
| GIANT_KEA | guild RP+BONECARN+giant | vanilla / giant | RP | 207,010 | flying | curious beast, not LP |
| GIANT_BARN_OWL | guild RP+BONECARN+giant | vanilla / giant | RP | 203,500 | flying | **BENIGN**, not LP |
| GIANT_KESTREL | guild RP+BONECARN+giant | vanilla / giant | RP | 201,750 | flying | **BENIGN**, not LP |
| JABBERER | guild AL+BONECARN+size 4.5M | vanilla / plain | AL | 4,500,000 | cavern 2-3 |  |
| SEA_SERPENT | guild AW+BONECARN+size 9.0M | vanilla / plain | AW | 9,000,000 | ocean |  |
| SHARK_GREAT_WHITE | guild AW+size 2.0M | vanilla / plain | AW | 2,000,000 | ocean |  |
| SPERM_WHALE | CARNIVORE+size 25.0M | vanilla / plain | MW | 25,000,000 | ocean | **BENIGN**, not LP |
| ORCA | tool override+size 5.0M | vanilla / plain | MW | 5,000,000 | ocean | **BENIGN**, not LP |

## Native apex (LARGE_PREDATOR land/water, below the bar) (90)

| id | source / kind | guild | adult cm3 | layer | flags |
|---|---|---|---|---|---|
| JURASSIC_AFROVENATOR_MAN | extinct / animal_person | AL | 950,000 | land | **sentient** |
| CENOZOIC_ANDREWSARCHUS_MAN | extinct / animal_person | AL | 850,000 | land | **sentient** |
| JURASSIC_CERATOSAURUS_MAN | extinct / animal_person | AL | 750,000 | land | **sentient** |
| PERMIAN_ANTEOSAURUS_MAN | extinct / animal_person | AL | 600,000 | land | **sentient** |
| CRETACEOUS_UTAHRAPTOR_MAN | extinct / animal_person | AL | 500,000 | land | **sentient** |
| CENOZOIC_MEGALANIA_MAN | extinct / animal_person | AL | 450,000 | land | **sentient** |
| JURASSIC_DILOPHOSAURUS_MAN | extinct / animal_person | AL | 400,000 | land | **sentient** |
| CENOZOIC_SMILODON_MAN | extinct / animal_person | AL | 328,000 | land | **sentient** |
| CENOZOIC_KELENKEN_MAN | extinct / animal_person | AL | 100,000 | land | **sentient** |
| CRETACEOUS_DEINONYCHUS_MAN | extinct / animal_person | AL | 100,000 | land | **sentient** |
| CENOZOIC_THYLACINE_MAN | extinct / animal_person | AL | 19,000 | land | **sentient** |
| CRETACEOUS_VELOCIRAPTOR_MAN | extinct / animal_person | AL | 17,000 | land | **sentient** |
| JURASSIC_ICHTHYOSAURUS_MAN | extinct / animal_person | AW | 650,000 | ocean | **sentient** |
| JURASSIC_PLESIOSAURUS_MAN | extinct / animal_person | AW | 450,000 | ocean | **sentient** |
| PERMIAN_HELICOPRION_MAN | extinct / animal_person | AW | 339,000 | ocean | **sentient** |
| SILURIAN_JAEKELOPTERUS_MAN | extinct / animal_person | AW | 200,000 | fresh water | **sentient** |
| PERMIAN_DIMETRODON_MAN | extinct / animal_person | AW | 139,000 | land + water | **sentient** |
| DEVONIAN_TIKTAALIK_MAN | extinct / animal_person | AW | 47,000 | land + water | **sentient** |
| JURASSIC_AFROVENATOR | extinct / plain | AL | 950,000 | land |  |
| CENOZOIC_ANDREWSARCHUS | extinct / plain | AL | 850,000 | land |  |
| JURASSIC_CERATOSAURUS | extinct / plain | AL | 750,000 | land |  |
| PERMIAN_ANTEOSAURUS | extinct / plain | AL | 600,000 | land |  |
| CRETACEOUS_UTAHRAPTOR | extinct / plain | AL | 500,000 | land |  |
| CENOZOIC_MEGALANIA | extinct / plain | AL | 450,000 | land |  |
| JURASSIC_DILOPHOSAURUS | extinct / plain | AL | 400,000 | land |  |
| CENOZOIC_SMILODON | extinct / plain | AL | 328,000 | land |  |
| CENOZOIC_KELENKEN | extinct / plain | AL | 100,000 | land |  |
| CRETACEOUS_DEINONYCHUS | extinct / plain | AL | 100,000 | land |  |
| CENOZOIC_THYLACINE | extinct / plain | AL | 19,000 | land |  |
| CRETACEOUS_VELOCIRAPTOR | extinct / plain | AL | 17,000 | land |  |
| JURASSIC_ICHTHYOSAURUS | extinct / plain | AW | 650,000 | ocean |  |
| JURASSIC_PLESIOSAURUS | extinct / plain | AW | 450,000 | ocean |  |
| PERMIAN_HELICOPRION | extinct / plain | AW | 339,000 | ocean |  |
| SILURIAN_JAEKELOPTERUS | extinct / plain | AW | 200,000 | fresh water |  |
| PERMIAN_DIMETRODON | extinct / plain | AW | 139,000 | land + water |  |
| DEVONIAN_TIKTAALIK | extinct / plain | AW | 47,000 | land + water |  |
| BEAR_POLAR_MAN | vanilla / animal_person | AL | 400,000 | land | **sentient**, curious beast |
| TIGER_MAN | vanilla / animal_person | AL | 225,000 | land | **sentient** |
| BEAR_GRIZZLY_MAN | vanilla / animal_person | AL | 200,000 | land | **sentient**, curious beast |
| LION_MAN | vanilla / animal_person | AL | 200,000 | land | **sentient** |
| BEAR_BLACK_MAN | vanilla / animal_person | AL | 120,000 | land | **sentient**, curious beast |
| ANACONDA_MAN | vanilla / animal_person | AL | 100,000 | land | **sentient** |
| JAGUAR_MAN | vanilla / animal_person | AL | 75,000 | land | **sentient** |
| COUGAR_MAN | vanilla / animal_person | AL | 60,000 | land | **sentient** |
| HYENA_MAN | vanilla / animal_person | AL | 60,000 | land | **sentient** |
| LEOPARD_MAN | vanilla / animal_person | AL | 50,000 | land | **sentient** |
| CHEETAH_MAN | vanilla / animal_person | AL | 50,000 | land | **sentient** |
| WOLF_MAN | vanilla / animal_person | AL | 40,000 | land | **sentient** |
| DINGO_MAN | vanilla / animal_person | AL | 20,000 | land | **sentient** |
| CROCODILE_SALTWATER_MAN | vanilla / animal_person | AW | 800,000 | land + water | **sentient** |
| ALLIGATOR_MAN | vanilla / animal_person | AW | 400,000 | land + water | **sentient** |
| VORACIOUS_CAVE_CRAWLER | vanilla / plain | AL | 900,000 | cavern 2-3 |  |
| BEAR_POLAR | vanilla / plain | AL | 400,000 | land | curious beast |
| TIGER | vanilla / plain | AL | 225,000 | land |  |
| BEAR_GRIZZLY | vanilla / plain | AL | 200,000 | land | curious beast |
| LION | vanilla / plain | AL | 200,000 | land |  |
| BLIND_CAVE_BEAR | vanilla / plain | AL | 200,000 | cavern 1-2 |  |
| SPIDER_CAVE_GIANT | vanilla / plain | AL | 200,000 | cavern 2-3 |  |
| BEAR_BLACK | vanilla / plain | AL | 120,000 | land | curious beast |
| ANACONDA | vanilla / plain | AL | 100,000 | land |  |
| MOLEMARIAN | vanilla / plain | AL | 90,000 | cavern 2-3 |  |
| JAGUAR | vanilla / plain | AL | 75,000 | land |  |
| COUGAR | vanilla / plain | AL | 60,000 | land |  |
| TROGLODYTE | vanilla / plain | AL | 60,000 | cavern 1-2 | **sentient** |
| HYENA | vanilla / plain | AL | 60,000 | land |  |
| LEOPARD | vanilla / plain | AL | 50,000 | land |  |
| CHEETAH | vanilla / plain | AL | 50,000 | land |  |
| HELMET_SNAKE | vanilla / plain | AL | 50,000 | cavern 1-2 |  |
| WOLF | vanilla / plain | AL | 40,000 | land |  |
| RODENT MAN | vanilla / plain | AL | 40,000 | cavern 1-3 | **sentient**, id has space/comma |
| DINGO | vanilla / plain | AL | 20,000 | land |  |
| IMP_FIRE | vanilla / plain | AL | 6,000 | magma |  |
| CROCODILE_SALTWATER | vanilla / plain | AW | 800,000 | land + water |  |
| CROCODILE_CAVE | vanilla / plain | AW | 600,000 | cavern 1-2 |  |
| SHARK_TIGER | vanilla / plain | AW | 500,000 | ocean |  |
| SHARK_HAMMERHEAD | vanilla / plain | AW | 500,000 | ocean |  |
| ALLIGATOR | vanilla / plain | AW | 400,000 | land + water |  |
| SHARK_BLUE | vanilla / plain | AW | 300,000 | ocean |  |
| TOAD_GIANT_CAVE | vanilla / plain | AW | 200,000 | cavern 1-2 |  |
| OLM_GIANT | vanilla / plain | AW | 200,000 | cavern 1-2 |  |
| SHARK_BULL | vanilla / plain | AW | 150,000 | ocean |  |
| SHARK_MAKO_SHORTFIN | vanilla / plain | AW | 80,000 | ocean |  |
| SHARK_MAKO_LONGFIN | vanilla / plain | AW | 80,000 | ocean |  |
| SHARK_FRILL | vanilla / plain | AW | 60,000 | ocean |  |
| REPTILE_MAN | vanilla / plain | AW | 50,000 | cavern 1-3 | **sentient** |
| SERPENT_MAN | vanilla / plain | AW | 50,000 | cavern 1-3 | **sentient** |
| POND_GRABBER | vanilla / plain | AW | 30,000 | cavern 1-2 |  |
| FISH_LAMPREY_SEA | vanilla / plain | AW | 20,000 | ocean |  |
| AMPHIBIAN_MAN | vanilla / plain | AW | 20,000 | cavern 1-3 | **sentient** |
| SHARK_REEF_BLACKTIP | vanilla / plain | AW | 15,000 | ocean |  |

## Not admitted, for the record

- Adult >= 1M cm3 but no predator guild and no diet token (40, stay prey): CENOZOIC_DEINOTHERIUM, CENOZOIC_GLYPTODON, CENOZOIC_MAMMOTH_PYGMY, CENOZOIC_MAMMOTH_WOOLLY, CENOZOIC_MEGACEROPS, CENOZOIC_MEGATHERIUM, CENOZOIC_PARACERATHERIUM, CENOZOIC_PLATYBELODON, CENOZOIC_RHINOCEROS_WOOLLY, CRETACEOUS_AMARGASAURUS, CRETACEOUS_ANKYLOSAURUS, CRETACEOUS_IGUANODON, CRETACEOUS_KOSMOCERATOPS, CRETACEOUS_NODOSAURUS, CRETACEOUS_NOTHRONYCHUS, CRETACEOUS_PARASAUROLOPHUS, CRETACEOUS_SUZHOUSAURUS, CRETACEOUS_THERIZINOSAURUS, CRETACEOUS_TRICERATOPS, CRETACEOUS_TSINTAOSAURUS, DRALTHA, ELEPHANT, ELEPHANT_SEAL, FISH_RAY_MANTA, FISH_STURGEON, FISH_SUNFISH_OCEAN, GIRAFFE, HIPPO, JURASSIC_BRACHIOSAURUS, JURASSIC_BRONTOSAURUS, JURASSIC_DIPLODOCUS, JURASSIC_KENTROSAURUS, JURASSIC_STEGOSAURUS, NARWHAL, RHINOCEROS, RUTHERER, SHARK_BASKING, SHARK_WHALE, WALRUS, WATER_BUFFALO.
- Carnivores between 300k and 1M cm3, not LP, not giant (2, stay meso): CENOZOIC_TITANOBOA 933k, CENOZOIC_TITANOBOA_MAN 933k.
