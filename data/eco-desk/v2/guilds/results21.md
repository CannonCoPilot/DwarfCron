# Roster builder v2.1: results (30 Sep 2026)

Files only, no rig. Code: `roster2.py` (v2.1 switches on `Cfg`, all off = v2 main), `run2.py` (configs `v21*`), `analyze21.py`
(item numbers, output in `analyze21.out`). Sweep: 11 embarks x 5 surface layers x 4 seasons x 20 seeds + 7 underground layers
= 4,960 builds per config. Tables: `tables21.md`. v2 outputs are unchanged: `runs/main.jsonl` and `runs/savage.jsonl` are
byte-identical to the backup in `runs/v2-orig/` (with the v2 code, tables and design).

## What v2.1 changes (config `v21`; `v21_savage` = the same on a savage embark)

| # | change | source |
|---|---|---|
| 1 | Uniform pick; x3 only for non-BENIGN group HUNTERS (tier >= 2), not herds | user ruling 30 Sep |
| 2 | FREQUENCY written = ladder x (mass / slot geometric mean)^-0.75, clamped 0.25-4, written x10 (land apex 3, meso 3, grazer 6, prey 5, shore 4; raptor 2, birds 6; water apex 2, water meso 3, fish 8, pelagic 2; caverns same tiers) | user ruling |
| 3 | No hard 5x upper size gate. In its place a **pack-mass floor**: the hunting group's total mass (mass x mid cluster size, non-BENIGN) >= 20% of prey mass. Variants 0%, 5%, 30% run | CAL; floor value pending the user |
| 4 | Animal people attack with their own trophic guild; civ races (AMPHIBIAN_MAN, REPTILE_MAN, SERPENT_MAN, RODENT MAN, TROGLODYTE, ANT_MAN, GREMLIN, PLUMP_HELMET_MAN) stay out | user 30 Sep: "let them be predators" |
| 5 | Sentient targets only for attackers in AL/AW (incl. giants boosted from those guilds) | user ruling |
| 6 | BENIGN cleared on every predator-guild member the roster arms (not only boosted apex) | user 30 Sep: "clear it" |
| 7 | Ocean: coastal APX 1-1 + pelagic apex APE 1-1 from SHARK_GREAT_WHITE, ORCA, SPERM_WHALE (+ GIANT_ORCA, GIANT_SPERM_WHALE, SEA_SERPENT on savage) | user 30 Sep |
| 8 | GIANT_OCTOPUS (235,100 cm3) and GIGANTIC SQUID (201,400 cm3) are water mesopredators (MW), not apex. The squid has no diet token: armed through the curated override. Its id has a space: the tool must address it by creature index | size |
| 9 | Unfilled-slot report: every slot below max carries its reason; the no-progress stop falls back to seeding a predator-prey PAIR | user: no silent stops |

## Per layer, main vs v21 (all 11 embarks)

DF = edges DF carries out on measured reach; ? = written, reach untested; stock = vermin transfers; no = BENIGN attacker left
BENIGN; unit act = unit edges actable incl. untested; P&H = pack AND herd on actable edges; pred = predator share of arrivals.

| layer | size main / v21 | DF | ? | stock | no | unit act | P&H | pred | split |
|---|---|---|---|---|---|---|---|---|---|
| land | 10.6 / 10.6 | 52 / 61% | 0 / 0% | 43 / 39% | 5 / 0% | 91 / 100% | 49 / 92% | 0.14 / 0.31 | 0 / 0% |
| flying | 6.6 / 6.6 | 0 / 0% | 11 / 32% | 69 / 68% | 20 / 0% | 34 / 100% | 24 / 41% | 0.36 / 0.37 | 0 / 0% |
| ocean | 11.5 / 13.2 | 53 / 58% | 5 / 6% | 39 / 36% | 2 / 0% | 96 / 100% | 11 / 80% | 0.06 / 0.14 | 0 / 0% |
| lake | 7.0 / 7.0 | 25 / 29% | 18 / 18% | 53 / 53% | 4 / 0% | 91 / 100% | 0 / 34% | 0.54 / 0.57 | 0 / 0% |
| river | 8.3 / 8.3 | 38 / 48% | 3 / 1% | 51 / 51% | 8 / 0% | 84 / 100% | 79 / 98% | 0.13 / 0.21 | 0 / 0% |
| cav1 | 5.3 / 7.0 | 92 / 72% | 5 / 8% | 3 / 20% | 0 / 0% | 100 / 100% | 0 / 0% | 0.08 / 0.24 | 0 / 100% |
| cav2 | 9.1 / 10.0 | 71 / 72% | 13 / 10% | 16 / 18% | 0 / 0% | 100 / 100% | 89 / 100% | 0.15 / 0.25 | 0 / 100% |
| cav3 | 8.1 / 9.0 | 89 / 91% | 11 / 9% | 0 / 0% | 0 / 0% | 100 / 100% | 100 / 100% | 0.12 / 0.21 | 0 / 100% |
| cavw1 | 5.0 / 5.0 | 25 / 25% | 0 / 0% | 75 / 75% | 0 / 0% | 100 / 100% | 12 / 25% | 0.44 / 0.33 | 0 / 0% |
| cavw2 | 5.0 / 5.0 | 19 / 15% | 6 / 10% | 75 / 75% | 0 / 0% | 100 / 100% | 22 / 40% | 0.44 / 0.33 | 0 / 0% |
| deep | 2.0 / 2.0 | 100 / 100% | 0 | 0 | 0 | 100 / 100% | 100 / 100% | 0.09 / 0.38 | 0 / 0% |

- Surface summary (v1 embarks): pack AND herd 34% -> 71% (v21_savage 94%); tool-actable edges 90% -> 100%; mutual predation 0.
- **Caverns split (100%)** is new and deliberate: the humanoid ruling (item 5) removed the only link from the cave-flier sub-web
  (BAT_GIANT, giant cave swallow, HUNGRY_HEAD, bats, bugbats, floaters) to the land web, which ran through sentient prey
  (BAT_MAN, CAVE_SWALLOW_MAN). v2 main kept the fliers only through those edges; plain v21 dropped them silently (RP/LB/VB 0 in
  cav1-3). The pair fallback now seeds them as their own sub-web in all 240 cavern rosters, and `unfilled` records it.
- The pelagic-apex slot and the ladder raise predator share of arrivals: land 0.14 -> 0.31, ocean 0.06 -> 0.14. At the ladder's
  intended ~9% apex waves this is the first number the season-on-the-rig test must check.

## Item answers

**2. Animal people as predators.** 284 animal people exist; 112 fall in predator guilds (all SAVAGE, 29 BENIGN). On
`v21_savage` they write 12,655 attacker edges (6,551 unit edges, the rest vermin stock) and appear as attackers in 78% of
rosters; `savage` (v2) wrote 0. Top: HONEY BADGER MAN, JURASSIC_ICHTHYOSAURUS_MAN, EAGLE_MAN, PEREGRINE FALCON MAN, BEAR_POLAR_MAN.
Civ-race attacker edges: 0. Calm maps are unchanged (every animal person is SAVAGE). The 11 boosted sentient apex:
SPERM_WHALE_MAN, CENOZOIC_MEGALODON_MAN, CRETACEOUS_ARCHELON_MAN, CRETACEOUS_MOSASAURUS_MAN, CRETACEOUS_CARNOTAURUS_MAN,
CRETACEOUS_SPINOSAURUS_AEGYPTIACUS_MAN, CRETACEOUS_TYRANNOSAURUS_MAN, CRETACEOUS_SPINOSAURUS_MIRABILIS_MAN,
DEVONIAN_DUNKLEOSTEUS_MAN, JURASSIC_TORVOSAURUS_MAN, JURASSIC_ALLOSAURUS_MAN. Sentient-target edges now come only from AL
(805) and AW (438); v2 also had ML 1,095 and RP 1,021. Side effect: insect-men and bird-men (FLY_MAN, MANTIS_MAN, WREN_MAN
...) have no allowed attacker on the flying layer (no AL/AW there), so they never make a roster (646 pool cells).

**3. BENIGN clears; ORCA.** The builder clears BENIGN on all 20 boosted BENIGN apex: BADGER, GIANT; CRETACEOUS_ARCHELON;
CRETACEOUS_ARCHELON_MAN; GIANT PEREGRINE FALCON; GIANT_BARN_OWL; GIANT_EAGLE; GIANT_FOX; GIANT_KESTREL; GIANT_MONGOOSE;
GIANT_ORCA; GIANT_OSPREY; GIANT_OTTER; GIANT_POND_TURTLE; GIANT_SNOWY_OWL; GIANT_SPERM_WHALE; GIANT_STOAT; GIANT_WOLVERINE;
ORCA; SPERM_WHALE; SPERM_WHALE_MAN. ORCA is in the pool of every calm ocean roster (all 4 ocean embarks, all seasons). v2 main
put it on 41 of 320 (13%); v21 puts it on 196 of 320 (61%), as the pelagic apex. BENIGN is cleared on every one.

**4. The unit edges DF would not act on.** In main, 19% of surface unit edges (3,039 of 16,401) had a BENIGN attacker left
BENIGN: RP 1,880 (BIRD_EAGLE 569, BIRD_OSPREY 484, BIRD_FALCON_PEREGRINE 374, BIRD_OWL_BARN 190, BIRD_KESTREL 143,
BIRD_OWL_SNOWY 120) and ML 1,159 (BADGER 430, RIVER OTTER 278, SEA OTTER 120, FOX 108, WOLVERINE 108, STOAT 64, MONGOOSE
51). A further 10% have untested reach. Clearing BENIGN on armed predators alone (`main_clearbenign`) takes BENIGN edges to 0%
and unit edges to 79% measured reach + 21% untested. The fix is measured: T1 GIANT_FOX with BENIGN off attacked deer (2 / 10
attacks, 1 kill). Still untested in v21 (19% of surface unit edges), which the rig must test:
- flier -> flier, 3,007 edges, all on the flying layer (no raptor hunt has run);
- aquatic -> waterbird in water, 459, and aquatic -> shore animal in water, 292 (ocean 488, lake 240, river 23).

**5. Pelagic apex.** Ocean PE presence: main 65% (58-74% by embark), savage 80%; v21 **100%** on every embark, and every PE is
eaten. APE picks on calm maps: ORCA 196, SHARK_GREAT_WHITE 59, SPERM_WHALE 65. On savage maps: ORCA 107, GIANT_ORCA 89,
SHARK_GREAT_WHITE 40, SPERM_WHALE 37, SEA_SERPENT 24, GIANT_SPERM_WHALE 23. The coastal APX is now sharks and lamprey
(SHARK_BLUE, FISH_LAMPREY_SEA, SHARK_FRILL, makos). GIANT_OCTOPUS moved APX -> MW (on 101 savage ocean rosters, 824 edges);
GIGANTIC SQUID moved FC (0 edges) -> MW (89 rosters, 732 edges).

**6. Large prey and the link guard.** Yes: the link guard drops a large herbivore that no predator in the pool may take. In
main, RHINOCEROS and HIPPO were unlinkable in 4 pool cells each (one embark x 4 seasons). On savage maps, 255 cells
(JURASSIC_BRACHIOSAURUS, BRONTOSAURUS, CENOZOIC_PARACERATHERIUM, GIANT_RHINOCEROS, and giant insects on the flying layer).
Roster share of prey >= 1,000,000 cm3 when in the pool, and unlinkable cells:

| config | roster share | unlinkable cells |
|---|---|---|
| main | 33% | 8 |
| v21 (20% floor) | 34% | 4 (HIPPO) |
| v21 5% floor | 37% | 4 |
| v21 no floor | 42% | 0 |
| savage | 5% | 255 |
| v21_savage | 6% | 179 |
| v21_savage 5% floor | 8% | 14 |

Per species on calm maps (on roster / in pool), main -> v21: ELEPHANT 34/160 -> 3/160; RHINOCEROS 56 -> 8/240; HIPPO 160 ->
160/240; GIRAFFE 81 -> 69/240; WATER_BUFFALO 47 -> 40/80; MOOSE 19 -> 30/240. The elephant drop is the 20% floor: no calm
group reaches 1,000,000 cm3 (10 hyenas = 600,000), and main's elephant eater was CRETACEOUS_CARNOTAURUS alone (147 edges onto
big prey) through R9's 5x effective mass. CAL measured 7 wolves (5.6% of an elephant's mass) and 10 hyenas (12%) killing
elephants, so **a 20% floor forbids kills DF makes**; 5% matches the lowest measured kill. With no floor at all, solitary small
hunters get edges onto big prey (RIVER OTTER 240, HONEY BADGER 74, JACKAL 69, RATTLESNAKE 66 edges onto elephant, hippo and kin),
which CAL says are inert.
**Predators with no allowable prey:** none is dropped for being too large. The tier rule lets any apex eat everything below it
and R9 keeps only a lower bound. The only predator-guild species that can never link in v21 are the 6 civ races in cavern
pools (96 cells), by the ruling. In `savage` v2, 734 cells of animal-person predators (DINGO_MAN, WOLF_MAN, COUGAR_MAN,
dinosaur men) could never link. v21 fixes this: they are attackers now.

**7. Giant packs.** In raws, the giants that hunt in groups are GIANT_HYENA 5:15 (633,600 cm3 each; a mid pack of 10 = 6.3M),
GIANT_DINGO 3:12 (341,800; 7 = 2.4M), GIANT_COYOTE 2:10 (306,000; 6 = 1.8M), GIANT_JACKAL 1:5 (306,000; 3 = 0.9M), GIANT_LION
1:3 (1,700,000; 2 = 3.4M) and the crocodilians GIANT_ALLIGATOR / GIANT_CROCODILE_SALTWATER 1:3. BADGER, GIANT 4:12 and
GIANT_ORCA 3:9 are BENIGN (cleared in v21). GIANT_WOLF is 1:1. Edges on `v21_savage` (20% floor), summed over builds:

| prey | edges by attacker |
|---|---|
| ELEPHANT | GIANT_DINGO 5, GIANT_LION 4, GIANT_HYENA 3 |
| RHINOCEROS | GIANT_HYENA 10, GIANT_LION 10, GIANT_DINGO 8, GIANT_JACKAL 4 |
| GIANT_RHINOCEROS | GIANT_HYENA 2 |
| HIPPO | GIANT_CROCODILE_SALTWATER 30, GIANT_ALLIGATOR 10 |

GIANT_ELEPHANT (40,000,000 cm3) makes 0 of 160 rosters at the 20% floor: no giant group reaches 8M (a giant hyena pack is 16%).
At 5% it makes 1 (eaten by GIANT_DINGO). By CAL's pattern (7 wolves and 10 hyenas killed elephants), a giant-hyena pack on an
elephant is very likely real. That is untested: it is the first giant arm to run.

## Open (for the user)

- **Pack-mass floor:** 5% (the lowest measured kill) or 20% (the earlier proposal)? The data favour 5%: 20% forbids kills CAL
  saw and removes elephants from calm rosters.
- **Humanoid ruling side effects:** cave fliers form their own sub-web (split 100% in caverns), and flying-layer animal people
  are never on a roster. Allow RP to take flier sentients, or accept both?
- Predator share of arrivals rose (land 0.31): check it against a season on the rig before shipping the ladder.
