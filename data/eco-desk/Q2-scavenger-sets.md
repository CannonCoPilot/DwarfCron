# Q2: candidate scavenger sets (desk half)

**What the wiki documents** (`wiki-tokens.md`, answer 1):
- **No creature eats corpses or remains in any mode.**
- BONECARN "eats bones … currently does not work", per bug 11069 (the adventurer).
- CURIOUSBEAST_EATER steals *edible items* and leaves by the map edge. Whether a corpse is an "edible item" to it is **undocumented**; S1 tests it.
- VERMIN_ROTTER is "attracted to rot" with no consumption documented.
- CARNIVORE devouring happens in worldgen only.

So every set below is a **candidate label**. None has a documented corpse-eating effect in fortress mode.

Why LP status matters: only LARGE_PREDATOR animals act on a written predator relation (T4, capabilities.md). A scavenging behaviour built on the relation write (e.g. "treat a corpse-holder as prey") reaches only the LP members. The tool-driven path in S2 (path goal to the corpse, delete on arrival) does not depend on LP. Script: `eco/w/` (inline).

## Candidate definitions (wildlife, n=363)

| set | definition | n | LP / BENIGN / unmarked | natural n | documented effect |
|---|---|---|---|---|---|
| S-BONE | BONECARN | 41 | 19 / 14 / 8 | 29 | "eats bones", does not work (bug) |
| S-EAT | CURIOUSBEAST_EATER | 19 | 3 / 4 / 12 | 19 | steals food and leaves |
| S-CB | any CURIOUSBEAST_* (EATER, ITEM, GUZZLER) | 21 | 3 / 6 / 12 | 19 | steals food, items or drink |
| S-TXT | DESCRIPTION has carrion / carcass / scaveng / "dead " | 9 | 2 / 2 / 5 | 9 | none (flavour text) |
| S-GARB | DESCRIPTION has garbage / steal (not already in S-TXT): FLY, ROACH_LARGE, RACCOON, MANDRILL, RAT_DEMON | 5 | 0 / 0 / 5 | 4 | none |
| S-ROT | VERMIN_ROTTER | 5 | 0 / 0 / 5 (all vermin) | 2 | attracted to rot (vermin, not units) |
| S-PLAN | the PLAN.md web-page suggestion: (BONECARN ∨ CARNIVORE) ∧ not small (≥150k cm3) | 15 natural | mostly LP | 15 | — |

## Overlaps

| overlap | members |
|---|---|
| S-BONE ∩ S-EAT (5) | BEAR_POLAR (LP), BIRD_BUZZARD, BIRD_VULTURE, BIRD_KEA, HONEY BADGER |
| S-BONE ∩ S-TXT (3) | BIRD_BUZZARD, BIRD_VULTURE, JACKAL |
| S-EAT ∩ S-TXT (3) | BEAR_BLACK (LP; "steal carcasses from other hunters"), BIRD_BUZZARD, BIRD_VULTURE |
| all three (2) | **BIRD_BUZZARD, BIRD_VULTURE** |
| Union S-BONE ∪ S-CB ∪ S-TXT ∪ S-GARB ∪ S-ROT | 69 (51 natural) |

**S-PLAN misses every textual scavenger.** Its 15 natural members are ALLIGATOR, LION, TIGER, CROCODILE_SALTWATER, BEAR_POLAR, SPERM_WHALE, SEA_SERPENT, PYTHON, JABBERER and 6 cave species. It excludes VULTURE (9k), BUZZARD (1.4k), JACKAL (15k), HYENA (60k), WOLF (40k), BEAR_BLACK (120k) and RACCOON, because the tool's "small" band is < 150,000 cm3. BEAR_POLAR is the only member it shares with the scavenger evidence. Size is the wrong filter.

## Members (natural; tag codes: B = BONECARN, E = CB_EATER, I = CB_ITEM, G = CB_GUZZLER, D = carrion text, g = garbage/steal text)

| species | tags | aggression | tool habitat / band | adult cm3 | cluster | FREQUENCY | note |
|---|---|---|---|---|---|---|---|
| BIRD_VULTURE | B E D | unmarked | flier / small | 9,000 | 5:10 LOOSE | 50 | "scanning the ground for dead carcasses" |
| BIRD_BUZZARD | B E D | unmarked | flier / small | 1,400 | 5:10 LOOSE | 50 | "searches … for carrion" |
| BEAR_BLACK | E G D g | **LP** | land / small | 120,000 | 1:1 | 5 | "steal carcasses from other hunters"; S1 subject |
| BEAR_POLAR | B E G | **LP** | land / medium | 400,000 | 1:1 | 2 | |
| BEAR_GRIZZLY | E G | **LP** | land / medium | 200,000 | 1:1 | 2 | |
| BIRD_KEA | B E I | unmarked | flier / small | 1,000 | 5:10 LOOSE | 50 | |
| HONEY BADGER | B E | unmarked | land / small | 14,000 | 1:1 | 50 | PRONE_TO_RAGE |
| JACKAL | B D | unmarked | land / small | 15,000 | 1:5 | 5 | "packs when they find a body" |
| SHARK_MAKO_LONGFIN | D | **LP** | aquatic / small | 80,000 | – | 50 | "scavenges" (ocean) |
| BIRD_CROW (vermin) / BIRD_RAVEN | D | BENIGN | flier / small | 500 / 1,200 | – / 2:10 | 100 | "feeds on carrion"; the crow is vermin (not a unit) |
| FISH_BULLHEAD_YELLOW (vermin) | D | unmarked | aquatic | 200 | – | 50 | "scavenging in inland waters" |
| FLESH_BALL | D | unmarked | semiaquatic (cavern) | 70,000 | 2:5 | 10 | "absorbs dead matter" |
| RACCOON | E I g | unmarked | land / small | 7,000 | 1:3 LOOSE | 10 | S1 subject |
| MANDRILL | E I g | unmarked | land / small | 20,000 | 5:10 LOOSE | 10 | "stealing garbage" |
| MACAQUE_RHESUS, GRAY_LANGUR, CAPUCHIN | E I | unmarked | land / small | 3.5-15k | 5:10 LOOSE | 10 | thieves |
| COATI | E I (+CARNIVORE) | unmarked | land / small | 6,000 | 1:1 | 50 | |
| BEAR_SLOTH | E G | unmarked | land / small | 100,000 | 1:1 | 5 | |
| DRUNIAN, RAT_GIANT, RAT_LARGE, MOLE_GIANT, MOLE_DOG_NAKED | E (I/G) | unmarked or BENIGN | land (cavern) | 25-200k | – | 10-100 | cavern thieves ("raiding the supplies of cavern outposts") |
| WOLF, DINGO, HYENA | B | **LP** | land / small | 20-60k | 3:7 / 3:12 / 5:15 | 5 | bone-eaters by token; no scavenging text (HYENA's description is "pack predator") |
| COYOTE | B | unmarked | land / small | 15,000 | 2:10 | 5 | |
| FOX, BADGER, WOLVERINE, MONGOOSE, STOAT, RIVER/SEA OTTER | B | BENIGN | land/semi / small | 0.35-30k | – | 50 | |
| 7 raptors (EAGLE, FALCON, KESTREL, OSPREY, 3 owls) | B | BENIGN (the great horned owl is unmarked) | flier / small | 0.25-4k | – | 50 | |

## How LP status divides the sets

- **LP members of any candidate set (natural):** BEAR_BLACK, BEAR_GRIZZLY, BEAR_POLAR, WOLF, DINGO, HYENA, SHARK_MAKO_LONGFIN (plus cave LPs JABBERER, POND_GRABBER, IMP_FIRE, and SEA_SERPENT). Only these would respond to a relation-based "scavenge" lever.
- **The strongest textual scavengers are not LP:** VULTURE, BUZZARD, JACKAL, RAVEN and CROW. Neither are the thieves: RACCOON, the monkeys, KEA. For them, scavenging must be the tool's own walk-and-delete (S2) or DF's own CURIOUSBEAST theft (if S1 shows it covers corpses).
- **BENIGN members** (FOX, BADGER, the raptors, the otters) flee non-friendly creatures (wiki). A tool walk toward a corpse near a predator may be abandoned; S2 measures arrivals.

## Recommended candidate set (to score against S1/S2)

**SCAV = (S-EAT ∪ S-TXT) ∩ LR ∩ natural**, with BONECARN as a secondary tag. That is 23 species:
- BIRD_VULTURE, BIRD_BUZZARD, BIRD_KEA, BIRD_RAVEN, JACKAL;
- BEAR_BLACK, BEAR_GRIZZLY, BEAR_POLAR, BEAR_SLOTH;
- RACCOON, COATI, HONEY BADGER, MANDRILL, MACAQUE_RHESUS, GRAY_LANGUR, CAPUCHIN;
- SHARK_MAKO_LONGFIN, FLESH_BALL, and the cavern thieves DRUNIAN, RAT_GIANT, RAT_LARGE, MOLE_GIANT, MOLE_DOG_NAKED.

Rationale:
- Every member either has a documented item-taking behaviour (CURIOUSBEAST_EATER) or a DF description that says it scavenges.
- BONECARN alone (wolf, fox, raptors) has only a "does not work" effect, so it should rank a species lower, not qualify it.

Split for the tool:
- **walk-and-delete** (S2 route): non-LP members;
- **relation-assisted** (optional): LP members.

In the PLAN categories, `eats-remains` = SCAV. The vermin categories stay with the HUNT flags (X5: no measurable effect on wild animals).

**What S1 decides**
- If CURIOUSBEAST_EATER units carry corpses off unprompted, DF already provides "scavenging" for 19 species, and the tool only needs to bring them near corpses.
- If not, S2's tool-driven path is the only route, and LP status is irrelevant to it.
