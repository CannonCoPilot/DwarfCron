# roster2 (guild-first) results, with a comparison to v1

**Run**
- Files only; the game was not touched. Code: `roster2.py`, `species2.py`, `realms2.py`, `run2.py`. Rules: `design.md`.
- Sweep size: 11 embark types (v1's 7, plus a tropical ocean with a salt river, an arctic coast, a tropical lake, and a deep-column
  ocean) × 5 surface layers × 4 seasons × 20 seeds, plus 7 underground layers × 4 × 20. That is 4,960 builds per config,
  11 configs, about 10 s in total.
- v1 comparisons use v1's 7 embarks only.
- Full tables: `tables2.md`. Concrete rosters: `examples2.md`. The apex list: `apex.md` / `apex.tsv`. Realms: `realms.md` /
  `realm_biome.tsv`. The species table: `species2.tsv`.

## 1. Headline results

1. **The SAVAGE gate (R0) removes v1's two worst distortions.**
   - Every giant, every animal person and 99 of 100 extinct species are SAVAGE in the raws. On a calm embark they are out.
   - Main surface rosters hold 0% giants and 0% sentients, against v1's 75% giant seeds and 20% animal-person nodes.
   - On a savage embark: giants 23%, sentients 9% (capped by the one SN slot), extinct 12%.
2. **Every roster closes.**
   - Isolated or split rosters: 0% in every layer and config. v1 was 6% (baseline) or 2% (FIX3).
   - Picks must link, so no member was ever isolated and the swap/drop repair never fired (0 of 54,560 builds).
   - Fills end in at most 3 passes: at slot maximum, or on the no-progress guard where the pool runs out. v1 never reached its
     caps.
3. **Mutual predation and apex-on-apex are 0 by construction.** The tier rule does it with no size threshold (0 of 36,026 main
   edges). Humanoid-rule violations: 0.
4. **What DF can carry out** (main, v1 embarks, surface):

   | edge class | share of all edges |
   |---|---|
   | measured reach | 31% |
   | written, reach untested (fliers, penguins, waterbirds) | 6% |
   | vermin stock transfers the tool performs | 53% |
   | BENIGN attacker (DF never acts) | 10% |

   - Tool-actable in total: 90%. Unit edges alone are 79% actable.
   - Caverns: 100% of unit edges are actable.
   - Flying is the weak layer. There are no measured raptor hunts, and 20% of its edges have a BENIGN raptor as attacker.
5. **Packs and herds**, v1 step-8 definition (any pack predator with prey, any herd with an eater):

   | layer | main | pack_pref3 |
   |---|---|---|
   | land | 62% | 81% |
   | river | 87% | 94% |
   | cav2 / cav3 | 89% / 100% | 92% / 100% |
   | cav1 | 0% | 0% |
   | ocean | 27% | 27% |
   | flying | 24% | 41% |

   - Surface overall: 45% (v1 FIX3 75%).
   - v1's high step-8 was carried by animal-person and giant packs, which are now SAVAGE-gated. With sentient attackers on,
     surface step-8 is 94%.
   - DF's own FREQUENCY favours solitary predators, so pure FREQUENCY picks give fewer packs. The secondary rule `pack_pref=3`
     (pick weight ×3 for non-BENIGN group species) raises surface step-8 to 62% and land to 81%, at no cost elsewhere.
   - cav1 has no non-sentient pack hunter; ocean apexes are solitary sharks (ORCA 3:9 is the exception).
6. **The APEX boost admits 89 species:**
   - 63 giants, 5 vanilla (SHARK_GREAT_WHITE, SEA_SERPENT, ORCA, SPERM_WHALE, JABBERER), 10 extinct, 11 animal people.
   - 20 are BENIGN and need BENIGN cleared. 11 are sentient and are held back as attackers.
   - Consequence on savage embarks: 57% of land apex slots go to **boosted giant mesocarnivores**, which carry FREQUENCY 25
     against 5 for real LPs: GIANT_SKINK, GIANT_LIZARD, GIANT_STOAT, GIANT_JUMPING_SPIDER, GIANT_RATTLESNAKE.
   - Flying apex on savage embarks is 100% giant raptors.
   - This is a decision (section 6).
7. **One non-SAVAGE extinct species dominates calm-map apex picks.**
   - CRETACEOUS_CARNOTAURUS is the only non-SAVAGE extinct species, and it carries FREQUENCY 50. It takes 25% of calm land
     apex slots (DINGO 14%, WOLF 14%).
   - If the world contains extinct creatures, DF would favour it the same way. Drop extinct on calm maps unless it is wanted.
8. **Seasons**
   - Pre-guard seasonal breaks: 4% of surface rosters (land 7%, flying 8%), against v1 flying 20%.
   - The guard costs 0.04 NO_<season> writes per roster.
   - Caverns carry no season flags.
9. **Seed sensitivity is lower than v1.** Mean pairwise Jaccard over 20 seeds:

   | layer | v2 | v1 |
   |---|---|---|
   | land | 0.32 | 0.17 |
   | flying | 0.33 | 0.16 |
   | ocean | 0.29 | 0.27 (water) |
   | cav1 / cav2 | 0.44 / 0.47 | 0.34-0.41 |
   | deep | 1.00 | 1.00 |

   - v2 lake 0.48, river 0.70, cav3 0.56, cavern water 0.57-0.65.
   - Slot tables fix the composition by guild, and FREQUENCY picks favour the common members.
10. **Size**
    - Allowed unit pairs with prey ≥ 3× the eater's raw mass, over the vanilla universe: 1,808. v1: baseline 5,756, FIX3 8,190,
      FIX3_ratio 601.
    - The remainder are group hunts inside the 5× effective-mass bound: wolf pack on moose, dingo pack on ibex.
    - In rosters the median unit prey/predator mass is 0.50, p90 4.0, and 15% of unit edges are ≥ 3×, all by group hunters.
    - Removing the soft preference (`nosizepref`) changes the web-level metrics by ≤ 2 points. It chooses which prey is picked,
      not whether webs close.
11. **Water and cavern layers stand as separate ecosystems.** They are thin, and several slots cannot be filled from DF's pools.

## 2. v1 vs v2 (v1 embarks)

| metric | v1 baseline | v1 FIX3 | v1 FIX3_ratio | **v2 main** | v2 pack_pref3 | v2 savage |
|---|---|---|---|---|---|---|
| surface mean size | 7-9 | 9.4 | 9.3 | 9.1 | 9.1 | 11.3 |
| surface isolated / split | 6% | 2% | 2% | **0%** | 0% | 0% |
| surface step 8 (v1 definition) | 78% | 75% | 71% | 45% | 62% | 47% |
| surface pack AND herd on actable edges | - | - | - | 34% | 55% | 31% |
| surface edges DF-actable (v1 definition: non-BENIGN unit attacker, unit target) | 43% | 77% | 74% | 37% | 39% | 48% |
| surface edges tool-actable (+ vermin stock) | - | - | - | **90%** | 92% | 97% |
| surface mutual predation | 0% | 0% | 0% | 0% | 0% | 0% |
| sentient share of nodes / of predators | 20% / 30% | - / 0% | - / 0% | 0% / 0% | 0% / 0% | 9% / 0% |
| giant seeds or giant share | 75% of land seeds | - | - | 0% | 0% | 23% of nodes |
| caverns+deep isolated / step 8 | 0-16% / 82-100% | 0% / 75% | 25% / 50% | 0% / 54% | 0% / 58% | 0% / 51% |
| caverns+deep edges DF-actable (measured reach) | 45-100% | 87% | 83% | 69% (77% incl. untested) | 66% | 68% |
| caps / termination | never reached (guard) | guard | guard | slot max or no-progress | same | same |
| seasonal breaks | flying 20% | - | - | 4% pre-guard, 0 after | 3% | 4% |
| allowed unit pairs ≥ 3× (universe) | 5,756 | 8,190 | 601 | 1,808 | 1,808 | 1,808 |

Reading the DF-actable drop:
- v2 counts every vermin link as an edge; they are 53% of surface edges.
- v2 keeps BENIGN mesocarnivores (fox, badger, the raptors) as web members. They are vermin-stock eaters and prey, and never armed.
- v1 FIX3 had removed BENIGN predators from predator slots.
- On unit edges alone, v2 is 79% actable (surface) and 100% (caverns).

## 3. Per layer (main config; all 11 embarks)

| layer | non-empty rosters | size | apex present | DF-actable (measured) / + untested / + stock | BENIGN (no) | pack AND herd | v1 step 8 | predator share of arrivals | stop list per roster |
|---|---|---|---|---|---|---|---|---|---|
| land | 880 | 10.6 | 100% | 52% / 52% / 95% | 5% | 49% | 62% | 0.14 | 29 |
| flying | 880 | 6.6 | 0% | 0% / 11% / 80% | 20% | 24% | 24% | 0.36 | 17 |
| ocean | 320 | 11.5 | 100% | 53% / 58% / 97% | 2% | 11% | 27% | 0.06 | 34 |
| lake | 160 | 7.0 | 50% | 25% / 43% / 96% | 4% | 0% | 19% | 0.54 | 10 |
| river | 240 | 8.3 | 100% | 38% / 41% / 92% | 8% | 79% | 87% | 0.13 | 6 |
| cav1 | 80 | 5.3 | 100% | 92% / 97% / 100% | 0% | 0% | 0% | 0.08 | 23 |
| cav2 | 80 | 9.1 | 100% | 71% / 84% / 100% | 0% | 89% | 89% | 0.15 | 28 |
| cav3 | 80 | 8.1 | 100% | 89% / 100% / 100% | 0% | 100% | 100% | 0.12 | 13 |
| cavw1 | 80 | 5.0 | 100% | 25% / 25% / 100% | 0% | 12% | 12% | 0.44 | 8 |
| cavw2 | 80 | 5.0 | 100% | 19% / 25% / 100% | 0% | 22% | 22% | 0.44 | 9 |
| cavw3 | 0 of 80 | - | - | - | - | - | - | - | - |
| deep | 80 | 2.0 | 100% | 100% | 0% | 100% | 100% | 0.09 | 0 |

**Slot fill** (rosters with ≥ 1 of the guild / pools that had a candidate; full table in `tables2.md`):
- **land:** APX, ML, GZ, PL 100/100; TH 48/100; SH 0/0; VG 91/91.
- **flying:** RP 100/100; LB 71/73; WB 60/64; APX 0/0 (no boosted flier on a calm map: giant raptors are SAVAGE).
- **ocean:** APX, FC, SH, MW 100/100; WB 72/100.
- **ocean PE:** 65/100 overall (57-73% by embark). On the deep-column embark the pelagic count doubles (1.27 per roster against
  0.57-0.74), but presence stays 63%: a pelagic needs an apex big enough to take it (R9, ≤ 5× effective mass).
- **lake:** APX 50/50, since the temperate lake has no LP in DF (FISH_LAMPREY_SEA is lake apex only where it lists the lake);
  FF 50/100.
- **river:** FF 67/67.
- **cav1:** ML 0/0; RP 14/100; VG 0/100 (no meso eats cavern vermin).
- **cav2 / cav3:** APX, ML, PL full; RP 69/100 and 55/100.
- **cavw1-2:** APX + SN + VF only (no unit fish). cavw3 never has a linkable roster: FLESH_BALL has no predator there.

**Tool writes per roster** (main, surface, v1 embarks): 1.4 armed attackers, 0.01 BENIGN clears (savage 0.38), 24.5 stop-list
entries (savage 98.5), 0.04 NO_<season>.

## 4. Example rosters (`examples2.md` has the edges, tags, ladder f and shares)

| layer | roster |
|---|---|
| land, TEMP, summer | DINGO (APX); ELK, RED PANDA (GZ); WILD_BOAR, BIRD_KAKAPO (PL); BADGER, KINGSNAKE (ML); 3 VG + TERMITE (stock). DF has no realms: this is a DF-faithful mix |
| land, TAIGA, winter | BEAR_POLAR (APX); DEER, MOOSE; WILD_BOAR, RACCOON; FOX, WOLVERINE (BENIGN meso: vermin eaters and prey) |
| flying, TEMP | BIRD_EAGLE, BIRD_OWL_BARN (BENIGN raptors: `-x>` on birds, stock on vermin); BIRD_RAVEN, BIRD_STORK_WHITE; magpie → thrips, mosquito |
| ocean, arctic, winter | ORCA (boosted, BENIGN cleared) → WALRUS, HARP_SEAL, NARWHAL (PE), halibut, tuna; OCTOPUS (MW) → cuttlefish, herring (stock) |
| ocean, deep column | SHARK_GREAT_WHITE (APX) with two PE slots: FISH_STURGEON, FISH_SUNFISH_OCEAN (inverse-size f 39 / 60 with the ×3 deep boost) |
| river, tropical salt | CROCODILE_SALTWATER → HIPPO, PLATYPUS, RIVER OTTER; otter (MW, BENIGN) → vermin fish (stock) |
| lake, temperate | FISH_LAMPREY_SEA → carp, gar, SNAPPING TURTLE; beaver, mink, goose as reach-untested targets |
| cav2 | OLM_GIANT (APX) → DRUNIAN, RAT_GIANT, MOLE_GIANT, PLUMP_HELMET_MAN (sentient; LP may take it); CRUNDLE (ML); BAT_GIANT (RP) → CAVE_FLOATER |
| cav3 | MOLEMARIAN (APX), CRUNDLE, HUNGRY_HEAD over GREEN_DEVOURER, FLOATING_GUTS, CAVE_BLOB, FLESH_BALL |
| cavw1 | OLM_GIANT → OLM_MAN (sentient) + cave fish, lobster, cap hopper (stock) |
| deep | IMP_FIRE → MAGMA_CRAB (always) |
| land, savage TEMP | GIANT_COATI + GIANT_COPPERHEAD_SNAKE (two boosted apex) over CENOZOIC_MIOHIPPUS, IBEX, KOALA; CENOZOIC_MIOHIPPUS_MAN (SN) |
| ocean, savage | JURASSIC_ICHTHYOSAURUS over giant crabs, ammonite man, skate; TRIASSIC_PSEPHODERMA (MW) |

## 5. Realms (`realms.md`)

**Coverage**
- 96 realm × biome cells have the realm's climate. They show 75 gaps in a required guild (land: apex, meso, grazer/prey,
  raptor; ocean: apex, fish, shore; fresh water: fish, shore).
- Cosmopolitan species count in every realm, and oceanic species in every ocean.
- Same-realm extinct species whose raws list the biome close only 5 gaps: AFR temperate grassland (PERMIAN_ANTEOSAURUS); NEA
  desert (Utahraptor, Allosaurus, Dilophosaurus...); PAL desert apex and meso; NEO desert prey.
- Most gaps need a cross-biome import, which is untested in DF (Q9), or an analog from another realm.

**Australasia**
- DINGO (20k) and CROCODILE_SALTWATER are its only LP.
- The extinct set supplies CENOZOIC_MEGALANIA (450k, LP) and CENOZOIC_THYLACINE (19k, LP). Both are Australian and list
  temperate grass/shrub, and MEGALANIA also tropical dry forest. MEGALANIA is the large apex the realm lacks.
- Both are SAVAGE, so on a calm map the tool would have to add them.
- A trade-off: adding them to the calm AUS roster halves pack AND herd (31% → 15%), because a solitary apex displaces the
  dingo pack in the single APX slot. A second APX slot for the fill would avoid that.

**DF-feature realms**
- **SAVAGE-only (M1):** 570 creatures. 178 are giants, 285 sentient and 199 extinct; the only non-giant, non-person vanilla members
  are FOXSQUIRREL, MOGHOPPER, LIZARD_RHINO_TWO_LEGGED, FLY_ACORN, SPIDER_CAVE_GIANT, SEA_SERPENT, YETI and SASQUATCH.
  - Only 6% have an Australasian root, the same share as the calm set.
  - "Australasian = SAVAGE" is therefore not a geographic proxy. It is a "lost world / giant-and-dinosaur" realm.
  - Built as a roster whitelist it closes (100% apex, 0% isolated), but it is 48% giants and 33% extinct, and pack AND herd is
    21% (calm set 50%).
- **SAVAGE × GOOD, SAVAGE × EVIL, FANCIFUL:** these add only mythic/unliving-class creatures (GOOD 8, EVIL 23, FANCIFUL 16).
  No natural species carries them, so they change nothing the tool manages.
- **Period realms** (Paleozoic 50, Mesozoic 110, Cenozoic 40; half animal people):
  - Mesozoic is the only coherent one: land apex in temperate forest, grass and desert; pack AND herd 28%.
  - Cenozoic has megafauna prey and 5 land apex (Smilodon, Thylacine, Andrewsarchus, Kelenken, Megalania), but its only meso is
    Titanoboa and it has no raptor.
  - Paleozoic is aquatic, with gaps everywhere on land.

## 6. Decisions this puts to the user

1. **Pack preference.** Adopt `pack_pref=3` as the secondary rule? It gives land step-8 81% (from 62%) and surface 62%, and costs
   nothing measurable.
2. **The boost's FREQUENCY.** On savage maps, cap a boosted mesocarnivore's pick weight at the native-LP level (f 5)? Otherwise giant
   skinks, lizards and stoats take 57% of apex slots. Alternatively, keep the boost for AL/AW/RP only and leave giant ML as meso.
3. **Extinct on calm maps.** Off by default? CARNOTAURUS alone takes 25% of calm apex slots. Use extinct only as realm fills,
   e.g. MEGALANIA/THYLACINE for AUS, with a second APX slot so the fill does not displace a pack.
4. **Humanoid rule.** On savage maps it admits giant raptors and giant lizards as the main attackers of animal people. Keep it,
   or restrict sentient targets to AL/AW attackers (a guild rule, not a size bar)?
5. **Water and cavern-water webs** cannot be written until ecoWrite gives water-layer units a realm (W2). That fix comes before
   any water block on the rig.

## Files (all in this directory)

| file | contents |
|---|---|
| design.md | The rule set in precedence order, slot tables, apex rule, humanoid rule, water/cavern specifics, frequency ladder, rig test matrix |
| results.md | This file |
| species2.py → species2.tsv | Species table: guilds, apex, deep class, realms, flags (894 natural-class creatures) |
| realms2.py | Realm table: Q9 plus extinct fossil localities (external knowledge) |
| roster2.py | The builder: `build(embark, layer, season, seed, cfg)` |
| run2.py → tables2.md, runs/*.jsonl | Sweep over 11 configs, 4,960 builds each |
| examples2.py → examples2.md | 24 example rosters |
| apex.py → apex.md, apex.tsv | Every apex, boosted and native, with its flags |
| realm_biome.py → realms.md, realm_biome.tsv | Realm × biome itemisation, coverage, gaps, fills, DF-feature mappings, roster scores |
