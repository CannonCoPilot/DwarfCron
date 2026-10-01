# A — Mechanics: review Part 1, items 1, 2, 3, 5, 11, 12, 13, 14

Desk research for W2:Urist, 1 Oct 2026. No rig was used (DF belonged to the user), nothing was committed, and the report sources (`scripts/eco-report`, `data/eco-report`) were not edited.

**Labels.**
- **MEASURED**: our rig data, with the replicate count.
- **DOCUMENTED**: the DF wiki, the DFHack docs or source, or df-structures, quoted with file:line.
- **INFERRED**: our reasoning, untested.

**Re-analysis code.** `data/eco-review/part1/A-mechanics-analysis/` holds the code and its outputs:
- `hunt.py`: TSV → per cell-rep records
- `glm.py`: binomial/Poisson IRLS
- `item3.py`, `lone.py`, `speed.py`, `stl.py`, `lone2.py`, `power.py`
- outputs: `*.out`, `recs.json`

Rerun with `python3 hunt.py recs.json && python3 item3.py`, and so on. Raw data: `data/experiments/ECO/<BLOCK>-*/`.

**Design caveat that runs through items 3, 12 and 14 (MEASURED from the run logs).**
- CAL, PK, STL, STL2, LONE and LONE10 each ran their cells in one CTRL load per rep, in a fixed order that is the same in every rep:
  - ctl is always first in STL/STL2;
  - pkg is always second in LONE/LONE10;
  - CAL and PK prey run in mass order.
- This is the cell-position trap that SW1/SW1R exposed (findings.md:530-540). No effect in these blocks is free of it.

## Headline answers
1. **LARGE_PREDATOR.**
   - DOCUMENTED: an attack-smaller drive, a one-group-per-map cap, a worldgen region list, and a separate wave pool.
   - MEASURED: it neither starts hunting nor is needed to act on a written relation; BENIGN is the switch. Its only measured effect: a BENIGN badger given LP gets drawn into fights with the fort's dogs (E32b, 2 reps).
   - Separate pool: still open. F1 (1 rep) leans against the wiki. LPP1 settles it.
2. **Natives vs wild.**
   - "Native" means "not placed in this cell" in the tallies, but the prose uses it in three more senses.
   - "Wild" means either "roaming flag set" (DF's aiming test) or "has a population reference" (DFHack `isWildlife`, which the tool uses). The two disagree exactly on placed and released units.
   - The categories are not one partition. Section 2 has the origin × wild table, and WILD1 tests whether the flag is DF's test.
3. **Pack size, not pack-mass/prey-mass, predicts kills.**
   - Within wolves: pack size OR 3.8 per doubling [1.0, 13.8]; ratio OR 0.96; ratio constraint rejected, p 0.019.
   - Prey mass does not lower kills. It enters pairing only through the tool's 5% floor and `eats()`, and it lengthens fights.
   - Prey **speed relative to the hunter** predicts kills: STL OR 0.20 [0.06, 0.71]; LONE ×1.85 per +100 speed units, with mass flat.
4. **Curious beasts.**
   - The counter (`animal.leave_countdown`) is reachable and lengthens a normal animal's stay.
   - A curious beast leaves because it stole. DF re-zeroed the counter within 300 t after CB's reset.
   - Only a species-wide flag clear is measured to keep them. CBX (pin every 10 t, station reset, strip loot) answers "can we extend".
5. **Figure "DF aims every non-wild unit".**
   - Its spec has x and y swapped (`x: n, y: writer`), the only bar figure that does, so it likely renders empty.
   - Its title overclaims: entries came from 59% of citizens, toward 89% of arrivals.
   - It never says that no attack followed.
   - Replacement: a holder × target grid with the RELS2 counterfactual panel.
6. **SNEAK alone best?** Not supported: RR 1.75 [0.44, 8.2], all of it lion kills. The STL design detects only ×5 or larger. The only CI-clear gain is the full package in LONE/LONE10, ×2.1 [1.2, 3.9], confounded with cell order.
7. **"Wild animals never sneak."**
   - 0 of 426 single-tick snapshots, 5,000 t apart, bounds hidden time at ≤0.7%.
   - Half the test read a marauder flag.
   - By the wiki, SNEAK acts only while hidden. SNK0-SNK4 test it with a 1-tick trace and a forced hide.
8. **Engagement.**
   - The data show more *strikes* (×8.7) with combat skills, not more engaged runs (5/8 vs 11/16).
   - The fix: define bouts from timestamped attacks (gap < 100 t) and report bouts per hunter-day.
   - ENG1 needs ~8 runs per arm to see ×3.

## Contents
1. LARGE_PREDATOR
2. Natives vs wild
3. Pack size, pack mass, prey mass, ratio, speed
5. Curious beasts
11. The "DF aims every non-wild unit" figure
12. SNEAK alone best?
13. "Wild animals never sneak"
14. Engagement metric and a powered design

---

## 1. LARGE_PREDATOR

Labels: **MEASURED** (block, replicates), **DOCUMENTED** (quoted source), **INFERRED** (reasoning from code or data, not tested).
Paths: `DC` = /Users/nathanielcannon/Claude/Projects/DwarfCron, `SWP` = /Users/nathanielcannon/Claude/Projects/seasonal-wildlife,
`DFH` = /Users/nathanielcannon/Claude/GitRepos/dfhack-53.16-r2. Wiki = raw wikitext of dwarffortresswiki.org `Creature_token`
fetched 1 Oct 2026 (the same text the desk summarised on 29 Sep in `DC/data/eco-desk/wiki-tokens.md:57`).

### 1.1 Every documented use

| # | Use | Source (DOCUMENTED, quoted) | Fortress-mode wildlife relevance |
|---|---|---|---|
| D1 | Aggression rule | Creature_token, LARGE_PREDATOR: "Will attack other creatures that are smaller than it." | Claimed behaviour; see 1.2, our data do not show it |
| D2 | Tamed LPs | same entry: "Tamed large predators will still attack wildlife." … "When tamed, large predators tend to be much more aggressive to enemies than non-large predators, making them a good choice for an animal army." Animal_trainer page: "Animals with the LARGE_PREDATOR token are somewhat more aggressive than animals lacking this token, and are more likely to attack hostiles, while animals with a BENIGN token will simply run away from any hostiles" | Fort animals only; untested by us |
| D3 | Map cap | same entry: "In fortress mode, only one group of 'large predators' (possibly two groups on 'savage' maps) will appear on any given map." Surroundings page: "It is also possible that two groups of animals happen outside on a savage biome, instead of one." | Wave cap; untested directly (1.3) |
| D4 | Region list (worldgen) | same entry: "A single biome supports 7 large predator species, picking randomly and rolling a d100 under its FREQUENCY to add it until all 7 slots are filled." FREQUENCY entry: "There are five lists - VERMIN_GROUNDER, VERMIN_SOIL, VERMIN_SOIL_COLONY, LARGE_ROAMING, and LARGE_PREDATOR … The game will attempt to place seven creatures in each list for each sub-region." | Fixed at worldgen; a runtime flag flip cannot add a species to the list (INFERRED) |
| D5 | Wave pool | FREQUENCY entry: "These waves include LARGE_ROAMING, LARGE_ROAMING combined with FLIER, LARGE_PREDATOR, and CURIOUS_BEAST - so a lion does not compete for selection with a gazelle." | The open item lp-separate-pool (1.3) |
| D6 | Adventure mode | "large predators will try to ambush and attack you (and your party will attack them back)" | None for fortress |
| D7 | Worldgen / flavour | "They may go on rampages in worldgen, and adventurers may receive quests to kill them … they can be mentioned in the intro paragraph … 'ere the wolves get hungry.'" | None at run time |
| D8 | Opposite of BENIGN | BENIGN entry: "Can be thought of as the counterpoint of the LARGE_PREDATOR tag." | Interaction, 1.2 |
| D9 | Overridden | NIGHT_CREATURE entry: "Prevents creature behavior enabled by LARGE_PREDATOR." | Night creatures are not managed wildlife |
| D10 | Pack animals | PACK_ANIMAL entry: "Creatures with this tag but without BENIGN, and/or with LARGE_PREDATOR leads to hauled items being dropped." | Caravans only |
| D11 | Internal flag | `DFH/library/xml/df.creature.xml:821` caste flag `LARGE_PREDATOR`; `:1420` creature flag `HAS_ANY_LARGE_PREDATOR` (comment "[LARGE_PREDATOR]") — a per-creature summary DF keeps beside HAS_ANY_BENIGN, HAS_ANY_CURIOUS_BEAST | INFERRED: the summary flag (not the caste flag) is what list-building code would read; a runtime caste flip leaves it stale |

What the docs do **not** say (checked): the Hunting/Ambusher page ("Hunting" redirects to `Ambusher`) never mentions LARGE_PREDATOR; hunters
"hunt wild animals" of any kind ("This can result in your marmot hunter suddenly having an unpleasant chitchat with an elephant"). The
taming check in DFHack reads PET / PET_EXOTIC only (`DFH/library/modules/Units.cpp:427-435`, `isTamable`). DFHack's danger tests do not
read it: `isDanger` (`Units.cpp:661-674`) = crazed, invader, OPPOSED_TO_LIFE, agitated, uninvited visitor, or great danger / night creature;
`isGreatDanger` (`:676-680`) = demon, titan, megabeast, forgotten beast. Nothing in DFHack's library, plugins or scripts reads
LARGE_PREDATOR (grep of `DFH` returns only the two XML lines above), and the DFHack docs mirror has no hit. There is no "beast" status
tied to it. The wiki's creature table column "hostile" is editorial and does not track the token (Coyote, not LP, "hostile=No";
Badger, BENIGN, "hostile=Yes"; Cougar LP "Yes": `Creature` page lines 155, 201, 203).

Sibling tokens, as documented (Creature_token): BENIGN "non-aggressive by default, and will never automatically be engaged by companions or
soldiers, running away from any creatures that are not friendly to it, and will only defend itself if it becomes enraged"; CARNIVORE
"Creature *only* eats meat" (diet, plus worldgen devouring); AMBUSHPREDATOR "start out hidden and remain near its original location until its
prey draws near"; PRONE_TO_RAGE "percentage chance to flip out at visible non-friendly creatures. Enraged creatures attack anything regardless
of timidity". In vanilla: LP 60 creatures / 161 castes, BENIGN 163, neither 140, LP ∩ BENIGN = ∅, the only AMBUSHPREDATOR (giant cave
spider) is inside LP, no vermin is LP (`DC/data/eco-desk/groupings.md:8-9`, `token-counts.tsv:43`).

### 1.2 What our experiments measured

| Claim | Evidence | Label |
|---|---|---|
| LP gives no hunting drive within 3,000 t without a written relation, even on smaller prey | P1 DF-only arm: 0 attacks in all 40 cells, incl. 6 LP species x RABBIT (1,200 cm3) (`eco-analyze.py` on `DC/data/experiments/ECO/20260929-235553/P1.tsv`, matrix reproduced 1 Oct); T1: LP flipped ON coyote and OFF wolf, no write: 0 attacks either way (`findings.md:11`) | MEASURED, 1 rep each |
| LP is not needed to act on a written relation | P1 written: COYOTE (BONECARN, no LP, no BENIGN) 343 attacks on deer, 2 rabbits + 1 deer killed; every LP also attacked (WOLF 273 on deer, HYENA 306 on buffalo) (`findings.md:5-7, 608-610`) | MEASURED, 1 rep |
| D1's size rule does not bind on a written relation | P1 written: WOLF (40,000) 93 attacks on WATER_BUFFALO (1,000,000); CHEETAH (50,000) 140 on KANGAROO (90,000); GRIZZLY 234 on buffalo (same P1 matrix) | MEASURED, 1 rep |
| BENIGN beats LP on a written relation | T1: BENIGN set on WOLF (LP + BENIGN) + write: 0 attacks vs control 64 (`findings.md:12`); HO: ORCA (BENIGN) 0 attacks, BENIGN cleared 45 (`findings.md:151`); TV2 GIANT_FOX 0/0 vs BENIGN off 2/10 (`findings.md:190`) | MEASURED, 1-2 reps |
| LP on a BENIGN badger makes it fight the fort's dogs, not prey | E32b: LARGE_PREDATOR set on BADGER castes, BENIGN left on (`DC/experiments/E32b.json`, code `c.flags.LARGE_PREDATOR=true`); 11 badger attacks, all on stray dogs, dogs 40 on the badgers; control 0 and 0 with 6 badgers on map (`SWP/STATE.md:2746-2776`) | MEASURED, 2 reps per arm |
| …which fits BENIGN's "never automatically engaged by companions" being lifted by LP | the dogs attacked LP-badgers and ignored BENIGN-only ones (same rows) | INFERRED |
| LP does not change DF's own PREDATOR_OR_PREY aiming | RELS: placed LION as is / BENIGN / LP off / AMBUSH all aimed at natives (lion_nolp LION>BIRD_RAVEN 1 and 1; lion_benign LION>GROUNDHOG 4; lion LION>BADGER 3) (`scripts/rels-tally.py` on RELS, re-run 1 Oct) | MEASURED, 2 reps |
| The reverse row toward a hunter follows the arrival's BENIGN, not the hunter's LP | RELS2: BENIGN species > cougar BENIGN_ANIMAL, non-BENIGN > cougar DANGEROUS_ANIMAL (`findings.md:303-304`) | MEASURED, 2 reps |
| LP does not separate cavern fighters | HC1-HC4: TROLL (LP), TROGLODYTE (LP) and GORLAK (BENIGN) fight unprompted; JABBERER (LP), TOAD_GIANT_CAVE (LP), BLIND_CAVE_OGRE do not (`findings.md:129-133, 323-330`); BENIGN on TROLL does not pacify it (`:116`) | MEASURED, 1 + 2 reps |
| LP does not change arrival or season assignment | E32b: badgers arrived in both arms; E32 control: same 2,3 season assignment (`SWP/STATE.md:2484-2491, 2765-2766`) | MEASURED, 2 reps (arrival is noisy) |
| "Proximity alone" among a crowd of LPs kills no prey | E11c no-lever arm: ~50 cougars/dingoes/wolves gathered by prey, 0 prey died, but 4,718 predator-on-predator reports (`SWP/STATE.md:957-970`) | MEASURED, 3 reps |
| AMBUSHPREDATOR (an LP companion token) does nothing measurable on wolves/lions | T1, TV2 0/0; STL ambush arm; hidden flags 0 of 426 samples (`findings.md:19, 191, 225-226, 238`) | MEASURED, 1-2 reps |

So, MEASURED: on the fortress map LARGE_PREDATOR is neither necessary nor sufficient for hunting. The switch for *acting on a relation* is
BENIGN; the source of *the relation* is the tool's write or DF's own aiming (which ignores LP). LP's one measured behavioural effect is E32b:
a BENIGN animal given LP becomes engageable by, and fights, the fort's dogs.

**What LP still does inside our tool (code, v7.0 `SWP/scripts/seasonal-wildlife.lua`):** marks a species a predator in `MODEL.DIET`
(`:1204`); multiplies pack "take" by k = 1.5 in the pairing rule (`:1899, :1915`); defines guilds AL/AW/RP (`:1365-1379`); labels a group
'pack' for cohesion (`:5862`). It no longer arms anything: `ecoArmed` arms every non-BENIGN predator (`:4044-4055`, "the switch is BENIGN,
not LARGE_PREDATOR"). The k = 1.5 has no DF basis (D1-D11 say nothing about kill power; PK/CAL showed pack size, not tag, drives kills).

### 1.3 Is LARGE_PREDATOR drawn from its own wave pool? (open item lp-separate-pool, `DC/data/eco-report/open-items.json`)

DOCUMENTED yes (D5). Our data, re-read 1 Oct:

- **F1** (`DC/data/experiments/ECO-F1/20260930-003517`, 1 rep, 60k t, surface force-released every 1,500 t): KANGAROO f100, PORCUPINE f50,
  WOMBAT f25, the 11 other CTRL land species at f1 — including the three LPs (COUGAR, DINGO, WOLF; entries 2, 13, 12 throughout, so
  available) and the fliers (raven, kestrel, owl, kakapo). Surface waves: 0 LP of 38 non-flier waves; fliers at f1 still came 13 times
  (`waves.tsv`; owl 7, raven 3, kestrel 3). The f1 LPs behaved like the f1 land prey (groundhog 0, skunk 0, badger 1), not like the f1
  fliers. A shared pool predicts 3/182 x 38 = 0.6 LP waves (P(0) ≈ 0.53); a separate pool running as often as the flier pool predicts
  several. **Leans shared**, 1 rep, under forced release.
- **E11c / E16** looked decisive (124 of 142 and 82 of 84 surface waves were LP at f5 while prey sat at f50), **but it is an artefact**:
  the manipulation that opened the predators set every other land entry to quantity 0 and extinct (`E11c/20260917-130751/log.txt`,
  "opened 18 entries at 30 (COUGAR DINGO WOLF); closed 159"), and after the first LP wave not one prey wave came (0 of 124). What it does
  show: with only LP entries open, LP waves came at the ordinary wave cadence (~1 per 1,450 t vs F1's ~1 per 1,580 t), and ~50 LPs stood
  on the map at once — the D3 one-group cap does not survive the forced release (INFERRED: DF enforces it through the same roaming-flag gate).
- **RELS2b** kangaroo cells: a cougar "arrived" at f1 in both reps, but it is unit #181 carried over from the preceding cougar cell of the
  same load (present at t1500) — not evidence (readout trap 1).
- **SW4** (findings.md:469-475): the AL multiplier x0.5/x1/x2 left apex presence at 0 in 5 of 6 runs. Uninformative: a separate pool with
  all LPs scaled together predicts no change (shares within the pool unchanged); a shared pool predicts a change too small to see at 0-2 units.
- **S8C/S8Cb/S8B/S8O**: apex 0 in 4 CTRL runs, 0-3 elsewhere at f 13-27 (findings.md:526) — rarity, not mechanism.

Net: the only clean datum (F1) favours LP competing with land prey under FREQUENCY, against the wiki. It is one replicate under forced
release, so the item stays open. It matters for the ladder (if shared, the apex FREQUENCY step works through the same d100 as prey and
SW4/S8's null means "rare"; if separate, the step is inert because the multiplier scales the whole pool).

### Answer in two sentences
In DF 53.16 fortress mode, LARGE_PREDATOR is documented as an attack-smaller-creatures drive, a one-group-per-map wave cap, a worldgen
region list and a separate wave pool, but our runs show it neither starts hunting (0 attacks without a relation, P1/T1) nor is needed to act
on one (coyote 343 attacks); BENIGN is the switch, and LP's only measured effect is that a BENIGN animal given LP gets drawn into fights
with the fort's dogs (E32b, 2 reps). Whether LP waves come from their own pool is still open: the one clean datum (F1, 1 rep) has f1 LPs
crushed by f100 kangaroos like f1 prey, while f1 fliers kept arriving, which contradicts the wiki's separate pool.

### Evidence
P1/T1 (`DC/data/experiments/ECO/20260929-235553/P1.tsv`, `T1.tsv`; `findings.md:3-19, 608-610`), HO/TV2 (`findings.md:151, 190`), E32b
(`SWP/STATE.md:2746-2790`, `DC/experiments/E32b.json`), RELS/RELS2 (`rels-tally.py`; `findings.md:258-267, 299-305`), HC1-HC4
(`findings.md:113-133, 323-332`), F1 waves (`DC/data/experiments/ECO-F1/20260930-003517/waves.tsv`, `pops.tsv`, `log.txt` manipulation
line), E11c/E16 waves and manipulation (`DC/data/experiments/E11c/20260917-130751/`, `E16/20260917-164801/`), wiki Creature_token
(LARGE_PREDATOR, BENIGN, NIGHT_CREATURE, PACK_ANIMAL, FREQUENCY entries), Animal_trainer, Ambusher, Surroundings pages; DFHack
`Units.cpp:427-435, 661-680`, `df.creature.xml:821, 1420`; tool `seasonal-wildlife.lua:1204, 1365-1379, 1899-1915, 4040-4055, 5862`.

### Gaps
- Wave pool (D5): one usable replicate (F1), under forced release, which also defeats the D3 cap.
- D3 cap ("one LP group"; two on savage) never measured under DF's own gate; savage maps never tested.
- D1 "attacks smaller creatures": never observed without a relation in 3,000 t; over 30k t placed hunters attacked natives, but RELS shows
  that is DF aiming non-wild units, and the LP-off lion's *attacks* were not logged in RELS (`nowatch`), so LP's effect on long-window
  attacks is unmeasured.
- D2 (tamed LPs, war animals) untested; outside the wildlife scope.
- Whether a runtime caste flip changes wave typing (HAS_ANY_LARGE_PREDATOR is a separate creature flag that E32b did not touch).
- k_large = 1.5 in the tool's pairing rule has no measured basis.
- P1/T1 are 1 rep, 3,000 t cells; the "no drive without relation" result is a short-window result (RELP).

### Proposed experiment or change
**LPP1 — is LP a separate wave pool?** CTRL, tool disarmed, DF's own gate (no forced release, so D3 also shows), 100,800 t, fresh load per
arm, 2 reps per arm, rep 2 in reverse order. Pre: stock COUGAR/DINGO/WOLF and KANGAROO entries to 30 (receipt: entries and FREQUENCY
printed after the pre; LP entries > 0 at every sample), every other CTRL land species f1.
- Arm A: KANGAROO f100, all three LPs f1. Arm B: KANGAROO f100, all three LPs f100.
- Readouts from `waves.tsv` (cx-probe): non-flier surface waves per species; max concurrent flagged LP groups per sample.
- Predictions. Shared pool: LP share of non-flier waves ~2% (A) vs ~75% (B), and kangaroo waves fall about 4x in B. Separate pool: LP
  wave count about the same in A and B (within-pool shares are unchanged when all LPs move together), kangaroo waves unchanged. The two
  readouts move in opposite directions, so 2 reps per arm is enough unless waves are fewer than ~8 per run (then report as underpowered).
- Cap: concurrent flagged LP groups ≤ 1 at every sample (calm CTRL) would confirm D3; > 1 would refute it.
- Optional third arm only if the user wants the savage case: the same as B on a savage fort (≤ 2 LP groups predicted).

**Changes to the tool (for the user to decide, not applied):** drop k_large (or justify it by a pack-size measurement, item 3); keep LP only
as a guild/cohesion label; state on the page "BENIGN decides who acts; LP decides nothing we could measure except the dogs' engagement".

---

## 2. Natives vs wild

### 2.1 How DF and DFHack classify a unit (code)

`Units::isWildlife` (`DFH/library/modules/Units.cpp:601-607`):
```
return unit->animal.population.population_idx >= 0 && !isMerchant(unit) && !isForest(unit) && !isFortControlled(unit);
```
`isFortControlled` (`:173-193`): false if berserk, crazed, OPPOSED_TO_LIFE, undead or ghostly; false if any of flags1 invader_origin,
active_invader, diplomat, forest, merchant, marauder (`exclude_flags1`, `:121-128`); **true if flags1.tame**; false if flags2 visitor,
visitor_uninvited, resident, underworld (`exclude_flags2`, `:129-134`) or agitated; else `isOwnCiv` (civ_id == the fort's civ).
So DFHack's "wild" = *has a regional population reference* (`world_population_ref.population_idx`, `df.regionpop.xml:45`) and is not
tame, own-civ, merchant or forest. It does **not** read the roaming flag.

`flags2.roaming_wilderness_population_source` ("ROMAING_WILDERPOP") and `…_not_a_map_feature` (`df.unit.xml:1405-1406`) mark a unit of a
DF wave. The tool's own code documents that DF admits one wave per source while any unit carries the flag (`SWP/scripts/seasonal-wildlife.lua:3401-3406`),
and every placement path clears it: harness `cx-eco spawn` (`DC/chronicler/dfhack/scripts/cx-eco.lua:378-383`: copies the six-field
population ref from the species' entry **or a borrowed one** (`:343-351`), sets leave_countdown, clears both flags, allocates an enemy-status
slot `:390-396`), the tool's placement (`seasonal-wildlife.lua:3950-3960`), the tool's `releaseGroup` (`:3568-3577`), and `cx-probe release`.

**DF's own 'wild' test for its PREDATOR_OR_PREY writes (MEASURED, inferred mechanism).** The RELS probe classes each slotted unit as
`cit` (isCitizen), else `wild` if the roaming flag is set, else `tame` (isTame), else `other` (`DC/data/eco-desk/v2/research/lua/rel_sample.lua:16`;
RELP used the same test without `tame`, `DC/scripts/eco-run.py:553-554`). Class-to-class counts of DF's new entries, re-tallied 1 Oct:

| run (2 reps unless noted) | P_O_P aimer > target | count |
|---|---|---|
| RELS (natives, placed subjects; CTRL) | cit > wild 159; tame > wild 107; other > wild 57; wild > wild 47 (38 cavern-cavern, 5 surface, 4 mixed) | 370 |
| RELS2 (every arrival force-released) | other > other 1,551; tame > other 73; cit > other 67; wild > wild 4 | |
| RELS2b (same steering, no release) | tame > wild 49; cit > wild 39; wild > wild 29 (cavern olm/crundle/crawler pairs; surface cougar>owl/kestrel 4) | |
| RELS3 (tool releases, ecology off) | wild > wild 66 (cavern); tame > wild 44; other > wild 36; cit > wild 34; other > other 5 | |

Reading: a unit with the roaming flag **cleared** (placed, tool-released, force-released, and also caravan animals — RELS logged
`LLAMA(other)>BIRD_EMU` and `CAMEL_1_HUMP(other)>PORCUPINE`) aims PREDATOR_OR_PREY at units that carry a population reference, exactly as
citizens and livestock do; a flagged surface arrival almost never aims (5 of 370). The cleanest contrast is RELS2 vs RELS2b: the same
steered arrivals, forced release vs not: 1,551 other>other entries vs 29 wild>wild. So the field that makes a placed or released unit
non-wild **to DF's aiming** is, by every observation, `flags2.roaming_wilderness_population_source` (with its `_not_a_map_feature` twin,
always cleared together, so not separable). Mechanism INFERRED; correlation MEASURED (4 blocks, 2 reps each). Two caveats: (a) the
target side is not the flag — released 'other' units are aimed at (RELS2), so the target test looks like "has a population reference"
(= DFHack isWildlife); (b) the cavern breaks the rule — flagged cavern natives aim at each other (38/29/66 entries), so DF has a second
condition underground (unknown; HC1-HC4 show it is species-dependent).

Hence two different "wild"s that disagree on placed and released units: **DFHack-wild (isWildlife)** says placed/released are wild (and
the v7.0 sweep uses that, `seasonal-wildlife.lua:2776, 4084, 4256`), **DF-aim-wild (flag set)** says they are not.

### 2.2 How the study uses "native" and "wild" — three senses each

| Term | Where | Exact meaning |
|---|---|---|
| native (tallies) | `eco-analyze.py:5-6`, `lone-tally.py:14` (`victim_spawned == "1"` → placed, else native) | any unit **not spawned by the harness in this cell**: DF arrivals, residents, citizens, livestock, and a previous cell's leftovers in a shared load |
| native (prose, surface) | doc rev 326 lines 39, 615 ("the fort's own wildlife"), LONE/STL "native kills" | DF-drawn wildlife, as opposed to placed |
| native (caverns) | content.html:26 "In the caverns it pairs natives freely" | cavern-resident wildlife units that carry the roaming flag (probe class `wild`, both sides), e.g. OLM_GIANT<>CRUNDLE, TOAD_GIANT_CAVE>TROGLODYTE |
| native (raws) | doc 638 "native gobblers" | species whose vanilla raws carry the token, vs a token written at run time |
| wild (probe) | rel_sample.lua:16 | roaming flag set (a DF wave unit not yet released) |
| wild (DFHack, tool) | Units.cpp:601; cx-eco `read` 'wild' column (`cx-eco.lua:181`) | has a population ref and not tame/own-civ/merchant/forest |
| wild (prose) | content.html:26 "surface wild animals", "new arrivals" | DF arrivals (= probe sense) |

Are they mutually exclusive? **"native" vs "placed"** (tally sense) are exclusive and exhaustive within a cell by construction, but "native"
is not a kind of animal — it includes citizens and livestock. **"native" vs "wild"** are not opposites: a native can be wild (flagged
arrival), non-wild (citizen, livestock, a tool-released resident) or cavern; a placed unit is non-wild to DF's aiming yet wild to DFHack.
**Probe classes cit / wild / tame / other** are exclusive (evaluated in that order) and exhaustive over *slotted live units only*; units
without an enemy-status slot (lazy allocation, RELP `findings.md:242`) and vermin (not units) are outside them. `other` is a catch-all:
placed, released, caravan and visitor animals, invaders, merchants.

### 2.3 Origin x DF-wild table (every creature class placed)

Columns: **W1** population ref + roaming flag set (DFHack wild, DF-aim wild: aimed at, rarely aims on the surface) · **W2** population ref,
flag cleared, not tame (DFHack wild, DF-aim non-wild: aims and is aimed at) · **N** no population ref, or tame/own-civ/merchant/forest
(DFHack non-wild; aims at W1/W2) · **X** not a unit.

| Origin ↓ / class → | W1 | W2 | N | X | Label |
|---|---|---|---|---|---|
| DF-drawn surface wave, before release (land, flier) | yes | | | | MEASURED (RELS class `wild`) |
| DF-drawn surface wave released by the tool's gate / `cx-probe release` | | yes ("resident") | | | MEASURED (RELS2, RELS3) |
| DF-drawn cavern wave / cavern resident (incl. animal people PLUMP_HELMET_MAN, BLOOD_MAN… listed as cavern populations, E23e `findings.md:511`) | yes (aims at other cavern W1: the exception) | if the tool released it (RELS3 `ELK_BIRD(other)>TROGLODYTE`) | | | MEASURED; animal people's flag state INFERRED |
| Water-feature units (lake/ocean, feature_idx ≥ 0, LAKEP `findings.md:318-321`) | population ref yes; flag state not read | | | | INFERRED; tool ignores them in gatedLayer (`seasonal-wildlife.lua:3513`) |
| Harness-placed (`cx-eco spawn`), own or **borrowed** ref | | yes | | | MEASURED (RELS `other`); borrowed ref points at another species' entry (code) |
| Tool-placed (v7.0 placement) | | yes | | | code `:3950-3960`; aiming INFERRED same as harness |
| Agitated wildlife (flags4.agitated) | yes if a wave | | | | INFERRED; DFHack isDanger true (`:668`) |
| Wild animal caught in a cage, untamed | | likely (ref kept, not tame) | | | INFERRED |
| Wild animal tamed by the fort | | | yes (tame → fort-controlled) | | code `:186-189` |
| Tamed animal that reverted ("caged animal will eventually revert to its wild state", Animal_trainer) | | ? | ? | | unknown |
| Born on the map to wild parents | ? | ? | | | unknown (ref inheritance unread) |
| Citizens (dwarves) | | | yes | | code; RELS `cit` |
| Fort livestock and pets (incl. calves) | | | yes (tame) | | code; RELS `tame` |
| Merchants and their pack animals (caravan llama, camel) | | | yes (merchant / no ref) | | code; RELS logs them as `other` aimers, INFERRED no ref |
| Diplomats, visitors and their mounts | | | yes | | code `:124, :130-131` |
| Invaders and their beasts; marauding thieves | | | yes | | code `:121-127` |
| Megabeasts, titans, forgotten beasts, semi-megabeasts | | | yes (historical figures, INFERRED no ref) | | tool excludes them (`V7.natural` in ecoIsTarget, `seasonal-wildlife.lua:4082`) |
| Night creatures (werebeasts, bogeymen) | | | likely | | INFERRED; NIGHT_CREATURE also cancels LP (D9) |
| Demons / underworld spawn (DEMON_* on CTRL's deep layer, `findings.md:434`) | possibly (underworld populations) | | flags2.underworld → not fort-controlled | | unknown; tool never tracks depth > 2 (`seasonal-wildlife.lua:3516-3517`) |
| Vermin (incl. colonies, VRM blocks) | | | | yes — `df.vermin`, outside isWildlife and the relation table | code |

### Answer in two sentences
In the study "native" means "not placed by the harness in this cell" (tallies), but the prose also uses it for DF-drawn wildlife, for cavern
residents and for raw-native tokens, while "wild" means either "carries DF's roaming wave flag" (the RELS probe, DF's aiming) or "has a
regional population reference" (DFHack `isWildlife`, the tool) — and the two "wild"s disagree exactly on placed and released units, which
DFHack calls wild but DF treats as fort-side aimers. The categories are therefore not one partition: placed vs native is exclusive and
exhaustive per cell but cuts across wild/non-wild, the probe's cit/wild/tame/other is exhaustive only over slotted live units, and vermin,
slotless units and some edge classes (born-on-map, reverted tame, demons) sit outside or are unknown.

### Evidence
`DFH/library/modules/Units.cpp:121-134, 173-193, 572-607, 614-620, 661-680`; `DFH/library/xml/df.unit.xml:1327-1355, 1405-1406, 2691-2697`;
`df.regionpop.xml:36-60`; probe `DC/data/eco-desk/v2/research/lua/rel_sample.lua:16`, `DC/scripts/eco-run.py:553-554`; tallies
`eco-analyze.py:5-6`, `lone-tally.py:12-16`; placement `cx-eco.lua:343-396`, `seasonal-wildlife.lua:3401-3406, 3568-3577, 3745-3760,
3950-3960`; RELS/RELS2/RELS2b/RELS3 TSVs re-tallied 1 Oct (class matrix above; `findings.md:258-267, 299-308, 404-409`); report wording
`DC/scripts/eco-report/content.html:26`, `DC/data/eco-report/eco-report-doc-rev326.md:9, 39, 615, 638, 742, 748`.

### Gaps
- The flag-as-DF's-wild-test is correlational: every placed or released unit also differs in arrival path, leave_countdown and slot
  history; no run set the flag back on a placed unit.
- Why cavern flagged units aim at each other (a second rule underground) is unknown.
- Flag state of lake/ocean feature units, cavern animal people, born-on-map young, reverted tame animals, caged wild animals and demons
  was never read.
- The probe never logged `isWildlife`, `population_idx`, `civ_id` or `flags4.agitated` beside its class, so DFHack-wild and DF-aim-wild
  cannot be cross-tabbed from existing rows.

### Proposed experiment or change
**Vocabulary change for the page (no rig):** replace "native" with **arrival** (DF-drawn, flag set), **resident** (DF-drawn, flag cleared
by the tool's gate), **placed** (created by harness or tool), **cavern resident**, **fort side** (citizens, livestock, pets), **visitor
side** (caravans, visitors, invaders); say "DF-wild" for flag set and "DFHack-wild" for `isWildlife`; and "raw token" instead of "native
gobblers". The sentence "In the caverns it pairs natives freely" becomes "In the caverns DF pairs cavern residents with one another."

**WILD1 — is the roaming flag DF's wild test?** CTRL, tool off, 15,000 t, fresh load per arm, 2 reps per arm (counterbalanced), 6 DEER
placed at the spot, one flagged DF arrival present at t0 (receipt: its id, flag true, slot ≥ 0; a replicate without one is vacuous).
Arm A: placed deer with the flag cleared (today). Arm B: placed deer with `roaming_wilderness_population_source` (and `_not_a_map_feature`)
set true after placement. Every 1,500 t log the RELS class, `isWildlife`, `population_idx`, `civ_id` for each slotted unit and new
P_O_P entries. Prediction if the flag is the test: A shows DEER(other)>arrival entries (RELS: 8 in 30k t; use a longer window if 15k t
yields < 3), B shows none, and cit/tame>DEER entries appear in both (target side = population ref). Note B closes DF's surface gate
(`seasonal-wildlife.lua:3401-3406`), so no new arrivals: compare against the t0 arrival only. A third arm in a cavern (flagged cavern
units already aim) is worth adding only if A/B separate. Add `isWildlife` and `population_idx` to `rel_sample.lua`'s `desc()` for all future
relation probes.

---

## 3. "Pack size decides kills, not prey size": pack mass, prey mass, ratio, speed

Labels: MEASURED (rig data with replicate count), DOCUMENTED (wiki, DFHack docs or source), INFERRED (our reasoning, untested).
Re-analysis code and full output: `DwarfCron/data/eco-review/part1/A-mechanics-analysis/`.
- `hunt.py` parses the raw TSVs into one record per cell-rep (`recs.json`).
- `glm.py` is a numpy IRLS fit for binomial/Poisson GLMs with Wald CIs and likelihood-ratio tests.
- `item3.py`, `lone.py` and `speed.py` fit the models. Their outputs are `item3.out`, `lone.out` and `speed.out`.

Scoring is placed-only throughout. A kill is a Death row whose killer is the placed hunter species (killer_spawned=1) and whose victim is a placed prey (victim_spawned=1). Attacks are the `pair=HUNTER>PREY` UNIT_ATTACK counts. The parsed totals reproduce findings.md:196-221 cell for cell.

Masses are adult BODY_SIZE from the vanilla raws, read with Python. Speeds are the 4th argument of `STANDARD_QUADRUPED/WALKING_GAITS`, the sprint delay; a lower number is faster. Masses and speeds:

| species | role | mass | speed |
|---|---|---|---|
| wolf | hunter | 40k | 149 |
| hyena | hunter | 60k | 183 |
| cougar | hunter | 60k | 195 |
| lion | hunter | 200k | 109 |
| tiger | hunter | 225k | 157 |
| rabbit | prey | 0.5k | 204 |
| groundhog | prey | 3k | 548 |
| hare | prey | 3.5k | 146 |
| mountain goat | prey | 50k | 439 |
| kangaroo | prey | 90k | 183 |
| deer | prey | 140k | 137 |
| elk | prey | 300k | 122 |
| moose | prey | 525k | 157 |
| water buffalo | prey | 1M | 183 |
| giraffe | prey | 1M | 146 |
| elephant | prey | 5M | 488 |

### 3.1 The data and what each block can answer

| block | design | cell-reps | kills | what it can separate |
|---|---|---|---|---|
| CAL (`CAL-20260930-142550`) | wolves 3/5/7 × deer/moose/buffalo/elephant; hyenas 5/10 × buffalo/elephant; 5 solitary cells. 6 prey, relation written, 30,000 t | 44 (2 reps) | 27 of 264 prey | Pack size against prey mass, within wolves. Hyenas met only big prey, so species and prey mass are confounded for them |
| CAL attempt 1 (`CAL-20260930-135309`) | rep 1 wolf cells (findings.md:222) | 11 valid (wolf7_ELEPHANT stopped at 13,325 t) | 4 | Sensitivity check: a third wolf rep |
| PK (`ECO3-20260930-133945/PK.tsv`) | wolves 1/3/5/7 × deer/elk/moose/buffalo; 4 prey, 3,000 t | 32 (2 reps) | 7 of 128 | Pack size against prey mass over a short window |
| STL+STL2 | one cougar or lion × deer or buffalo, 30,000 t | 64 (non-norel) | 17 | Prey speed relative to the hunter |
| LONE+LONE10 | one cougar among 8 prey species × 6, 100,800 t | 30 runs | 59 | Prey mass against prey speed, which are decoupled across these 8 species |

**Design confounds (MEASURED from the logs).**
- **Cell order follows prey mass.** Every CAL and PK rep is one CTRL load, and the cells run in a fixed order: prey deer → moose → buffalo → elephant, pack size ascending within each prey (`CAL-*/log.txt`; block defs `scripts/eco-run.py:319-340`). Prey mass therefore rises with cell position and session time. This is the trap SW1/SW1R exposed (findings.md:530-540).
  - Position against kills shows no trend (Spearman ρ −0.20 and +0.08 per rep, p 0.38 and 0.72; `item3.out`).
  - The position confound cannot be removed from these data.
- **Hunters start on top of their prey.** Prey are placed at radius 4 and hunters at radius 5 around the same spot (`eco-run.py:333`, `:363`). So "kills" largely measure the first encounter:
  - CAL: 14 of 27 kills fell in the first 3,000 t (median 2,978 t).
  - STL/STL2: 8 of 17 fell in the first 1,000 t.
  - LONE: 16 of 59 fell in the first 1,000 t.

### 3.2 Kills: pack size, pack mass, prey mass, the ratio, prey speed (binomial GLM, kills of the prey placed)

Effects are per doubling (log2) unless stated. All rows are MEASURED, 2 reps.

| data | term | odds ratio [95% CI] | p (LRT) |
|---|---|---|---|
| CAL wolves only (24 cell-reps, 15 kills) | pack size (log2 n) | **3.79 [1.04, 13.8]** | 0.027 |
| | prey mass | 1.13 [0.85, 1.51] | 0.39 |
| | pack-mass / prey-mass ratio | 0.96 [0.73, 1.27] | 0.79 |
| | prey speed (+100) | 0.96 [0.65, 1.41] | 0.84 |
| | n + prey mass: prey mass | 1.14 [0.85, 1.53] | 0.39 |
| | ratio constraint (b_pack = −b_prey) | rejected | 0.019 |
| CAL wolves + attempt-1 rep (35, 19 kills) | n | 3.50 [1.15, 10.7] | 0.017 |
| | prey mass | 1.13 [0.88, 1.47] | 0.34 |
| | ratio | 0.96 [0.75, 1.23] | 0.75 |
| CAL wolves + hyenas (32, 26 kills) | n + prey mass: n | 4.26 [1.77, 10.2] | 0.001 |
| | n + prey mass: prey mass | **1.33 [1.01, 1.73]** (bigger prey died *more*) | 0.032 |
| | ratio | 0.86 [0.68, 1.09] | 0.22 |
| PK (32, 7 kills, 3,000 t) | n | 73.6 [1.2, 4,500]; 0 kills below n=5, 6 of 7 at n=7 | <0.001 |
| | prey mass | 0.94 [0.45, 1.95] | 0.87 |
| | ratio | 1.88 [1.00, 3.54] | 0.032, much weaker than n alone (AIC 25.6 vs 15.8) |

How to read these:
- **Within one hunter species, pack size carries all the signal.** The pack-mass/prey-mass ratio carries none. Wolves killed elephants (ratio 0.056) at 3 of 12 and deer (ratio 2.0) at 1 of 12 in the 7-wolf cells.
- **The "bigger prey died more" result needs the hyena cells.** Hyenas met only buffalo and elephant (10 hyenas × elephant 8/12). That is hunter species confounded with prey, so findings.md:219 ("bigger prey died MORE") is true of the pooled table but **not** within wolves.
- Correction already logged at findings.md:602-603: the CAL "speed" ordering was not monotonic for wolves.

**Prey speed relative to the hunter.** This is the variable the user did not list, and it is the one that predicts kills across solitary hunters.

| data | prey faster than the hunter | prey slower than the hunter | effect |
|---|---|---|---|
| CAL all | 1 / 72 killed | 26 / 192 | with log2 n in the model: OR 0.17 [0.02, 1.30], p 0.09 |
| STL+STL2 (64 cell-reps) | 3 / 192 | 14 / 192 | **OR 0.20 [0.06, 0.71], p 0.013**; prey mass adds nothing (OR 0.72 per doubling [0.49, 1.05]) |
| LONE+LONE10 (30 runs × 8 prey species) | 12 / 900 (hare, kangaroo, deer, elk, buffalo) | 47 / 540 (rabbit, groundhog, goat) | about 6.5× |

LONE+LONE10 Poisson model on the 8 prey species:
- Speed: kills ×**1.85 [1.44, 2.36] per +100 speed units**, p < 0.001.
- Mass, with speed in the model: ×0.99 [0.86, 1.14] per doubling, p 0.90.
- Spearman ρ, kills against slowness: 0.92, p 0.001.
- Groundhog (3 kg, speed 548): 27 of 180 killed. Goat (50 kg, 439): 16 of 180. Deer: 0 of 180. Elk: 1 of 180. Buffalo: 2 of 180.

Sources: `speed.out`, `lone.out`.

- PK at 3,000 t shows no speed effect (OR 1.41 [0.27, 7.3]). Its kills are the 7-wolf melee at the spawn spot.
- Caveats:
  - n = 8 prey species, and speed is a species trait. Groundhog and goat differ from deer in other ways too.
  - The gait number ignores agility, terrain and exhaustion.
  - Rabbit is slow (204) but small, and was rarely attacked (10 attacks in 30 runs). Size may matter for being noticed.
  - Status: MEASURED, INFERRED as cause.

### 3.3 Pairing, attacks and kills are three different decisions

**1. Pairing.** The tool decides this (code, DOCUMENTED by source).
- **Roster building** uses `eats()` (`seasonal-wildlife.lua:1940-1952`):
  - take = M_pred × G^0.75 × k, with k = 1.5 if LARGE_PREDATOR or AMBUSHPREDATOR (`:1914-1917`, PRED constants `:1912`).
  - need = M_prey × 0.6 (solo) or 0.9 (herd) (`:1918-1920`). A pair is allowed when take ≥ need.
  - `preference()` (`:1967-1973`) ranks prey with a log-normal around 0.4× the predator's mass.
  - Prey mass therefore decides which species share a web.
- **The live relation write**, `ecoWrite` (`:4155-4250`), stopped using `eats()` in v6.9 (comment `:1953-1956`: 58% of written pairs failed eats). It writes `PREDATOR_OR_PREY` when:
  - `MODEL.reaches` passes (realm, habitat, shared water; no size test), and
  - v7.0 `pack_floor` is on, and share = (alive members of the hunter's tracked group) × hunter mass / prey mass ≥ 0.05 (`:4210-4217`).
  - At share ≥ `pack_sneak` 0.25 it also writes SNEAK 10 on the hunter.
  - The floor applies only to **wild** targets (`rb ~= true`). A non-wild target (livestock, or a placed or released unit) bypasses it (`:4196-4210`).
  - So prey mass enters pairing through one threshold, set from a single CAL cell (7 wolves × elephant, share 0.056; comment `:4175-4176`).

**2. Attacks.** DF decides this. The tool's write only makes a pair *eligible*.
- MEASURED: no relation, no attack within 3,000 t on the surface (P1 0/40, 1 rep).
- DF also writes its own `PREDATOR_OR_PREY` over longer windows: fort side → each new arrival, placed/released units → arrivals, cavern wild ↔ wild (RELS/RELS2/RELS2b, 2 reps; findings.md:258-267, 404-409).
- Which eligible target a unit attacks: SW2/SW2R moved the floor 0 / 0.05 / 0.20, and the wolves' share of attacks on the elephant did not follow it (93/55%, 78/81%, 38/68%; findings.md:545-551).
  - So within an eligible set, DF's target choice is not the tool's.
  - INFERRED: proximity and vision dominate. VIEWRANGE on the prey changed attack counts in TV2 (findings.md:186).
- Prey mass and attacks:
  - CAL wolves: per doubling of prey mass ×1.21 [0.90, 1.62], p 0.22 (quasi-Poisson, dispersion ~80).
  - PK: ×1.63 [1.12, 2.37], p 0.011, adjusted for n.
  - An attack count is one strike per row. Big prey that fight back and survive generate long fights, so attack counts measure fight length, not how often a hunter decides to attack.
  - Engagement as a binary (any attack in the cell) rises with n in PK (OR 3.6 [1.5, 8.8] per doubling) and not with prey mass (1.45 [0.70, 3.0]).

**3. Kills.** These come from DF combat and pursuit. They rise with pack size and do not fall with prey mass (wolves). They fall sharply when the prey outruns the hunter (STL, LONE).

**The floor in CAL's own data.**
- Cells below 0.05 (wolf3 and wolf5 × elephant): 0 of 24 prey killed. Those cells had 352 attacks and lost 4 wolves.
- Cells at or above 0.05: 26 of 168 (Fisher p 0.050).
- Between 0.05 and 0.25: 17 of 72 (24%). At 0.25 or above: 9 of 96 (9%). Kill rate does *not* rise with the share.
- The floor's only support is the elephant (which fights back). It is a screen against futile, costly fights, not a ratio law. SW2/SW2R found no measurable effect of 0 / 0.05 / 0.20 on placed-prey kills over 4 reps (findings.md:549).

### Answer in two sentences

No: kill success does not follow pack mass divided by prey mass. Within wolves the ratio explains nothing (OR 0.96 per doubling, CI 0.73-1.27) and the constraint is rejected (p 0.019). Pack size explains most of it (OR 3.8 per doubling of n, CI 1.0-13.8). Prey mass does not lower kills: it decides pairing only through the tool's own 5% floor and roster `eats()`, and it lengthens fights (more attack rows). What predicts kills besides group size is whether the prey can outrun the hunter: OR 0.20 (0.06-0.71) when it can (STL); kills ×1.85 per +100 speed units with mass flat (LONE, 8 species). All of this is MEASURED at 2 reps, confounded with cell order, and underpowered for anything but large effects.

### Evidence

- Raw rows:
  - `data/experiments/ECO/CAL-20260930-142550/CAL.tsv` and `CAL-20260930-135309/CAL.tsv` (attempt 1)
  - `ECO3-20260930-133945/PK.tsv`
  - `STL-20260930-155456/STL.tsv` and `STL2-20260930-164417/STL2.tsv`
  - `LONE-20260930-184842/LONE.tsv` and `LONE10-20260930-212000/LONE.tsv`
- Parsed and fitted in `data/eco-review/part1/A-mechanics-analysis/{hunt,item3,lone,speed}.py` → `*.out`.
- Totals match findings.md:196-221, 224-239, 246-251, 582-593.
- Tool code: `Projects/seasonal-wildlife/scripts/seasonal-wildlife.lua:1912-1973` (eats, preference), `:4155-4250` (ecoWrite, floor, sneak bonus).
- DF's own targeting: RELS/RELS2/RELS2b (findings.md:258-267, 299-308, 404-409); SW2/SW2R prey choice (findings.md:388-396, 542-551).
- Cell order: `CAL-*/log.txt`, `ECO3-*/log.txt`; block defs `scripts/eco-run.py:319-340`.

### Gaps

- **Power.**
  - 27 kills in CAL, 7 in PK. The CI on the wolf pack-size effect runs from 1.04 to 13.8.
  - A prey-mass effect smaller than about ±50% per doubling cannot be excluded.
- **Prey mass and speed are collinear in CAL** (deer < moose < buffalo < elephant on both). Only LONE separates them, and it has one hunter species and 8 prey species.
- **No cell crosses prey mass with speed at fixed pack size.** For example, a fast heavy prey (elk 300k, 122) against a slow light one (goat 50k, 439) against the same pack.
- **Cell order is perfectly confounded with prey identity** in CAL and PK (one load per rep).
- **Kills are dominated by the placement encounter** (half in the first 3,000 t). Natural approach is not measured.
- **Hunter species is confounded with prey set** (hyenas only on big prey; cougar only on fast prey in CAL).
- **Attack counts are strike counts**, overdispersed 60-200×. They are not a decision measure.

### Proposed experiment or change

**PMS1: pack × prey mass × prey speed, counterbalanced.**
- Fort and pack: CTRL, written relation, WOLF packs of 3 and 7.
- Prey: four species chosen to cross mass and speed:
  - light-fast: HARE 3.5k, 146
  - light-slow: GOAT_MOUNTAIN 50k, 439
  - heavy-fast: ELK 300k, 122
  - heavy-slow: WATER_BUFFALO 1M, 183, or ELEPHANT 5M, 488
- 8 cells, 6 prey each.
- Hunters placed **40 tiles** from the prey, so the readout includes approach.
- Fresh load per cell, or ABBA order (rep 2 reversed). 2 reps per cell = 16 runs. 15,000 t (half of CAL; most kills come early).
- Receipts: placed counts, relation rows > 0 at +100 t, hunter-to-prey distance at t0.
- Readout:
  - kills (binomial GLM: n + log2 mass + speed)
  - first-attack tick and engagement bouts (from the item 14 logger)
  - hunters lost

**Power.** Pooling cells by factor gives 8 runs per level. That detects a ×4 kill odds on one factor (STL-like base rates). For the user's two-rep rule, the contrasts are designed as main effects, not as cell-by-cell comparisons.

**Tool.**
- Keep the 0.05 floor as a *harm screen* (elephant-type prey that kill packs). Do not raise it.
- Consider a speed screen for solitary hunters, which matches the data better than mass: write a relation only where the prey's sprint delay is ≥ 0.9 × the hunter's. This would stop deer/elk pairs for cougars, which produced 0 kills in 36 + 180 + 180 prey (CAL, LONE10, LONE).
- Recommendation only. The user holds the decision.

---

## 5. Curious beasts

User's question: "Curious beasts come to steal, then leave." Can we reach that tick counter, and can we just raise it?

### What we measured

| block | fort, set-up | arms | result | reps |
|---|---|---|---|---|
| B (P-day, run 20260929-235553/B.tsv) | CTRL, 6 placed at the land spot 126,96,104 (~30 tiles from the fort spot), 3,000 t | BEAR_GRIZZLY, BEAR_BLACK, RACCOON as placed; grizzly with CURIOUS_BEAST, _EATER, _GUZZLER caste flags off | as placed: gone 6/6, 6/6, 6/6. Flags off: 0/6 gone, alive, spread 47.6. "Gone" = `df.unit.find` nil (removed from the world), not inactive or offmap (B.tsv rows 3, 10, 14, 18) | 1 |
| BOATS trace (ECO2, interactive; findings.md:101-103; no raw file kept) | BOATS, 1 placed RACCOON | none | path goal WildernessCuriousStealTarget, walked ~35 tiles to the wagon pile (306 items), took 1 item (a rope). leave_countdown went 199,600 -> 0, goal SeekStation, walked off the edge with the rope, removed from the world. seasonal-wildlife.lua:6348-6350 adds "gone within 1,500 ticks". Grizzlies on BOATS wandered (MarauderMill) for 2,400 t and stole nothing | 1 unit |
| CB (ECO2-20260930-103132/CB.tsv) | CTRL, 4 RACCOON placed 12 tiles from the fort spot, 10 x 300 t | default; reset; flags_off | default 4/4 removed. reset 4/4 removed. flags_off 4/4 alive, wandering (goal MarauderMill, leave ~195,670, items=0, `wild=true`, forest=false) | 1 |

**What "reset" actually wrote.** This is the code in `scripts/eco-run.py:294-302`. After each of the ten 300-tick steps, the harness ran this for every spawned RACCOON whose `animal.leave_countdown == 0`:

`u.animal.leave_countdown = 200000; u.path.goal = None; u.path.path.{x,y,z}:resize(0)`

It did not write anything else. The station (`unit.idle_area`, `idle_area_type`), the hauled loot, the job and every flag were left as they were. The reset was also conditional: a unit with a non-zero countdown was skipped.

**What happened under reset** (CB.tsv rows 12-21). The counts of units reset at each 300-tick check were 4, 4, 3, 2, 1, 1, 1, 0, 0, 0.
- All four raccoons already had countdown 0 by the first check. So each one stole, and DF zeroed its countdown, within 300 ticks of being placed 12 tiles from the fort.
- At the next check (600 t), all four read 0 again. The harness had set 200,000 only 300 ticks earlier, and the countdown falls 1 per tick (STATE.md:637-639). It could not have run down. DF wrote 0 again: either it re-zeroes the countdown while the unit carries loot or heads for the edge, or the unit stole a second time.
- The count then falls as units are removed. The last one was reset at ~2,100 t and was gone by ~2,400 t.

So "countdown reset does not keep them" is MEASURED at 3,000 t (1 rep, 4 units). Whether it delayed departure is NOT known. The default arm logged only the end state (no per-unit departure time), so the two arms cannot be compared on stay length.

**Timing oddity.** The flags_off raccoons read `leave` ≈ 195,670 at the end. That is 4,330 ticks below the 200,000 set at spawn (cx-eco.lua:340, 381), while the cell's steps add up to 3,010 t. The cell ran ~1,300 t longer than its step count, or DF debited the countdown faster. That needs a clock receipt in any rerun (see memory experiment-readout-traps, t0 clock jump).

### What governs the stay

**The counter.** `unit.animal.leave_countdown` (df.unit.xml:2694-2695, comment "once 0, it heads for the edge and leaves"). It is readable and writable, and the tool already writes it:
- `holdGroup`, seasonal-wildlife.lua:5937-5944
- `dismissGroup`, :5946-5951
- spawn, cx-eco.lua:381; tool placement, seasonal-wildlife.lua:3958

For ordinary wildlife it really is the clock:
- MEASURED (E9a, STATE.md:637-640, n=46 arrivals): set per unit at arrival to 19,913-29,918 t and falls 1 per tick.
- MEASURED (E4/E9b, STATE.md:663-665, 3/3): zeroed units left within 1,700-3,000 t; units raised to 55,000 outstayed their siblings.

So for a non-curious animal, yes: the counter can be reached, and raising it lengthens the stay.

**Curious beasts are different.** The countdown is not what ends their visit; the theft does.
- DOCUMENTED, wiki Creature_token CURIOUSBEAST_EATER: "Allows a creature to steal and eat edible items from a site." It grabs a food item, runs to the map edge and vanishes there. The wiki's CURIOUSBEAST_ITEM entry: it "cannot drop hauled items until it enters combat". All three CURIOUSBEAST_* entries: tame or trained instances stop. The Steals_food page: thieves "grab a single stack (or container) and carry it towards the edge of the map."
- MEASURED (BOATS trace): the theft is followed at once by countdown 0 and path goal SeekStation.
- INFERRED: SeekStation means "walk to my station", so the departure intent lives in the station fields: `idle_area` and `idle_area_type` (df.unit.xml:2625-2633), whose enum `unit_station_type` (df.d_basics.xml:3897-3940) includes WildernessCuriousWander, WildernessCuriousStealTarget, WildernessRoamer and HeadForEdge. CB's reset cleared the path and goal but never the station. DF simply re-pathed to the edge, and either re-zeroed the countdown or the unit had already decided to leave. Neither `where` (cx-eco.lua:170-183) nor any CB row reads `idle_area_type`, so which station value they held is unknown.

**The arrival side.**
- DOCUMENTED (wiki FREQUENCY entry): fortress spawning has "separate wave pools: large roamers, flying large roamers, large predators, and curious beasts".
- MEASURED in DF's event queue (STATE.md:2714, E23c logs): DF queues a `WildlifeCurious` timed event.
- So natural curious beasts come in a wave type of their own. Our placed raccoons skipped that path: they have a borrowed population ref and the roaming flag cleared (cx-eco.lua:376-383). Even so, they behaved as thieves.

**Flags.**
- `caste_raw_flags` holds CURIOUS_BEAST, CURIOUS_BEAST_ITEM, CURIOUS_BEAST_GUZZLER and CURIOUS_BEAST_EATER (df.creature.xml:804-812), plus a creature-level `HAS_ANY_CURIOUS_BEAST` (:1421).
- MEASURED (B and CB, 1 rep each, 6/6 and 4/4): clearing the caste flags is enough. They are species-wide.
- There is no per-unit "has stolen" or "curious" flag in unit flags1-4 (df.unit.xml:1320-1480). The nearest are flags1.forest ("units no longer linked to merchant/diplomacy, they just try to leave mostly", :1330-1331), which read false on the CB units, and flags1.check_active_heist (meaning not established).

**Per-unit override.**
- DOCUMENTED (df-structures): a syndrome's CE_REMOVE_TAG can strip only the bits in `cie_add_tag_mask1` (df.material.xml:459-492). That list holds MISCHIEVOUS but no CURIOUS_BEAST* bit. Per-unit curse/syndrome removal (`unit.curse.rem_tags1`, df.unit.xml:2042-2043) therefore cannot turn the habit off for one animal.
- The only per-unit lever the wiki names is taming. That sets flags1.tame, which makes `isFortControlled` true (Units.cpp:187-188) and `isWildlife` false (Units.cpp:601-606). The animal would stop being wildlife to the tool's sweep and become a fort animal: a different outcome from "a wild resident".

**Current tool behaviour.** v6.9's `curious TOKEN resident` clears the four caste flags species-wide while the tool runs and restores them on off, disable or unload (seasonal-wildlife.lua:6346-6406). That is the measured remedy. It also strips the habit from any tamed animals of that species.

### Answer in two sentences
The counter can be reached (`unit.animal.leave_countdown`) and raising it does lengthen a normal animal's stay. A curious beast leaves because it stole, not because its counter ran out: DF zeroes the counter on theft and zeroed it again within 300 ticks after we reset it (CB, 1 rep), so the only measured way to keep them is clearing the CURIOUS_BEAST caste flags species-wide, which keeps 4/4 to 6/6. Pinning every few ticks, resetting the station, or taking away the loot are untested and could still work.

### Evidence
- MEASURED: B.tsv (1 rep): 6/6 gone for each curious species; grizzly with flags off 0/6 gone.
- MEASURED: CB.tsv rows 1-36 (1 rep, 4 units/arm): default 4/4 gone, reset 4/4 gone (resets 4,4,3,2,1,1,1,0,0,0), flags_off 4/4 stay.
- MEASURED: the reset code, eco-run.py:294-302.
- MEASURED: BOATS trace, findings.md:101-103 (1 unit, interactive, no raw file).
- MEASURED: countdown as the clock for ordinary wildlife, STATE.md:637-640 (n=46) and :663-665 (3/3).
- DOCUMENTED: df.unit.xml:2694-2696 (leave/vanish countdown), :2625-2633 (station), :1330-1331 (forest).
- DOCUMENTED: df.d_basics.xml:3897-3940 (station types), :3943-3952 (path goals); df.creature.xml:804-812, 1421; df.material.xml:459-492 (removable tags have no CURIOUS bit).
- DOCUMENTED: wiki Creature_token CURIOUSBEAST_EATER/_ITEM/_GUZZLER and FREQUENCY (separate curious-beast wave pool); wiki Steals_food.
- DOCUMENTED (code): Units.cpp:601-606 (isWildlife), 187-188 (tame means fort-controlled).

### Gaps
- No departure times in CB default or B, so we cannot tell whether reset delayed departure.
- The reset ran every 300 t and only on units at 0, never every tick or unconditionally.
- Station (`idle_area_type`, `idle_area`), inventory contents and job were never read before or after theft.
- Whether DF re-zeroes the countdown every tick, or a second theft re-zeroes it, is unknown.
- All subjects were placed units (borrowed ref, roaming flag cleared, countdown 200,000, ~10x natural). A natural WildlifeCurious arrival has never been traced.
- Whether bears in B stole anything is unknown (no item or inventory readout).
- One rep everywhere: B, CB and the trace all predate the two-reps rule.
- The cell clock ran ~1,300 t past its step count (flags_off leave 195,670).

### Proposed experiment or change
**CBX: can we extend a curious beast's stay?**

Set-up:
- CTRL, tool off.
- **Fresh fort load per arm.** CB's cells shared a load, so an earlier cell's thefts change the pile.
- 4 RACCOON placed 12 tiles from the fort spot, as in CB.
- 6,000 t per arm.
- 2 reps per arm, rep 2 runs the arms in reverse order.

Arms (5; pins run in-game via `repeat -time 10 -timeUnits ticks`, not by harness steps):
1. **ctl:** as placed.
2. **pin10:** every 10 t set `leave_countdown = 200000` unconditionally.
3. **pin10_station:** pin10, plus set `path.goal = None`, clear the path, `idle_area = pos` and `idle_area_type = WildernessRoamer` (or MarauderMill, the flags_off arm's wandering state).
4. **pin10_station_strip:** as arm 3, plus whenever `#u.inventory > 0`, move each hauled item to the ground at the unit's tile (`dfhack.items.moveToGround`). Receipt: item id and name.
5. **flags_off:** positive control; known to stay 4/4.

(Optional sixth arm, flagged as a different outcome: `tame` = flags1.tame + training_level SemiWild. The wiki says taming stops the habit, but the unit stops being wildlife to the tool.)

Receipts, read every 100 t, per raccoon:
- the full `where` line, extended with `idle_area_type`, `idle_area`, `#inventory` and item ids, `leave_countdown` read before the pin, and `df.global.cur_year_tick`;
- the pin job's counter (pins done, and how many found 0, which measures how often DF re-zeroes);
- the fort's item count in the wagon pile at start and end (thefts);
- the DFHack version string;
- the cell's t0 and final tick (the clock check).

A rep where fewer than 4 raccoons placed, or no theft happened in ctl, is vacuous.

Readout:
- per-unit time on map (survival curve), censored at 6,000;
- thefts per arm;
- countdown re-zero events per pinned unit.

Decision rule:
- An arm "extends the stay" if all 8 of its units (2 reps) outlast every ctl unit's departure.
- If pin10_station keeps them, the tool can offer a per-group "resident" that keeps the species' flags (thieves stay thieves elsewhere).
- If only flags_off works, keep v6.9's species-wide clear.

Follow-up if CBX succeeds: a natural-arrival arm on a fort whose pool holds a curious species (BOATS or a bear fort), with the pin applied to DF's own WildlifeCurious arrival.

---

## 11. The "DF aims every non-wild unit" figure

### What the figure is
experiments.json `figures[49]`, id `rels-who-writes` (experiments.json:21355-21361), block RELS, section "relations" ("Who DF aims at whom", content.html:115-140).
- Title: "DF aims every non-wild unit at each new wild arrival (323 of 370 entries); surface wildlife almost never at each other (5)"
- Subtitle: "PREDATOR_OR_PREY entries DF wrote itself, by writer and target class"
- Spec: form `bar`, `x: "n"`, `y: "writer"`, unit "entries", highlight "Placed animals (not flagged wild)"

Rows (writer → target, n):

| writer | target | n |
|---|---|---|
| Dwarves | surface wild arrival | 159 |
| Livestock and pets | surface wild arrival | 107 |
| Placed animals (not flagged wild) | surface wild arrival | 57 |
| Cavern wildlife | cavern wildlife | 38 |
| Surface wildlife | surface wildlife | 5 |
| Cavern and surface wildlife | each other | 4 |

Notes field: the figure was meant to explain why the hunters placed in CAL, STL and LONE killed unrelated natives. Released and placed units lose the roaming flag, so DF treats them as non-wild and aims them at later arrivals.

I re-tallied the counts from RELS-20260930-195031/RELS.tsv: 14 cell-reps, 370 PREDATOR_OR_PREY entries, no duplicates.
- Writer class "cit": 159. "tame": 107. "other": 57. Wild > wild: 47, split 38 / 5 / 4 by species.
- The classes come from `data/eco-desk/v2/research/lua/rel_sample.lua:16`: `cit` if isCitizen, else `wild` if `flags2.roaming_wilderness_population_source`, else `tame` if isTame, else `other`.

### Why it confuses

1. **It probably does not render.** INFERRED from code; I did not check it visually. The page template draws a bar as `x` = category and `y` = value (template.html:168-187: `cats = uniq(rows, x)`, `Plot.barX(rows, {x: y, y: x})`, highlight tests `r[x] === hi`).
   - This spec gives `x: "n"`, `y: "writer"`. It is the only bar figure of the six with the axes swapped (my check over every `form: bar` in experiments.json).
   - So the category axis shows the numbers 159, 107, 57, 38, 5, 4, and the value axis ("writer (entries)") tries to plot strings on a linear scale. Bars and labels come out empty or NaN, and the highlight never matches.
   - The user may be looking at an empty or garbled chart.

2. **The title claims more than the data shows.** The data are entry counts, not units or arrivals.
   - **"Every non-wild unit" is not supported.** Of the citizens that appear in any entry, 81 of 138 per cell-rep wrote a PREDATOR_OR_PREY entry (59%; e.g. lion_nolp rep 2: 4 of 13, deer rep 1: 1 of 14).
   - **"Each new wild arrival" is close but not exact.** 76 of 85 surface wild units seen per cell-rep (89%) got at least one entry from the fort side or a placed unit.
   - **No cavern wild unit got one** (0 of 39).

3. **"Non-wild" is undefined, and it clashes with the page's other "wild".**
   - The figure's "wild" is DF's roaming-population flag (`flags2.roaming_wilderness_population_source`).
   - The page's other wild is DFHack `isWildlife`, which reads `population_idx` (Units.cpp:601-606). That is what CB's `where` prints, and placed raccoons print `wild=true`.
   - So a placed animal is "wild" by one test and "not flagged wild" by the other.
   - "Placed animals" is really the catch-all `other` class: not a citizen, not tame, not roaming. It includes 4 entries from a LLAMA that no script placed. The species writing as `other` were BADGER 25, LION 18, DEER 8 and LLAMA 4.

4. **"Aims" reads as attacks, but none followed.** The entries are reaction values in `enemy_status_cache.rel_map`.
   - RELS.tsv has no `attacks` and no `death` rows in any of its 14 cell-reps; the run log reads "attacks 0, deaths 0" for every cell.
   - The same `read` verb logged native attacks in STL, so it does record them.
   - So the figure shows 370 "aimings" and 0 attacks.

5. **Bars mix two questions and hide the target.**
   - Rows 1-3 ask who DF points at arrivals. Rows 4-6 ask whether wild animals pair with each other.
   - The target class is in the data, but no axis or colour shows it.
   - The arrivals' own reactions toward the fort (BENIGN_ANIMAL 662 and DANGEROUS_ANIMAL 15 in RELS), which complete the picture, are left out.

6. **Raw counts carry exposure, not tendency.**
   - Dwarves lead because there are many of them: up to 14 per cell after `sustain`.
   - Cells differ in length: `nat` is 100,800 t and the subject cells 30,000 t.
   - Cells share a load in a fixed order (experiment-readout-traps).
   - None of the counts is per unit or per tick.

### Answer in two sentences
The figure was meant to show that DF writes PREDATOR_OR_PREY entries from the fort's side, and from script-placed units with the roaming flag cleared, toward new surface arrivals, but almost never between two surface wild animals. That is why placed hunters in CAL, STL and LONE attacked natives. It confuses because its axes are swapped in the spec (so it likely renders empty), its title claims "every unit, each arrival" from raw entry counts (59% of citizens, 89% of surface arrivals), "non-wild" clashes with the isWildlife sense used elsewhere, and it never says that no attack followed.

### Evidence
- MEASURED: RELS.tsv (14 cell-reps: 7 cells x 2 reps). My re-tally of class pairs by reaction:
  - cit>wild PREDATOR_OR_PREY 159; tame>wild 107; other>wild 57; wild>wild 47
  - wild>cit BENIGN_ANIMAL 514, DANGEROUS_ANIMAL 14; wild>tame BENIGN_ANIMAL 58; wild>other BENIGN_ANIMAL 43
  - 0 attack and 0 death rows
- MEASURED: RELS2b (4 cell-reps): cit>wild 39, tame>wild 49, wild>wild 29, other 0.
- MEASURED: RELS3 (4 cell-reps): other>wild 36, other>other 5.
- MEASURED: RELS2 forced release (6 cell-reps): other>other PREDATOR_OR_PREY 1,551, wild>wild 4. Once the flag is cleared on every arrival, DF pairs arrivals with each other: the flag decides.
- DOCUMENTED (code): rel_sample.lua:16 (class rule); Units.cpp:601-606 (isWildlife); template.html:168-187 (bar encoding); experiments.json:21355-21361 (spec).

### Gaps
- Not checked visually on the live page (no browser was used, and report sources were not edited).
- The probe lists only units that hold an enemy-status slot and appear in some entry. A unit with no slot or no entry is invisible, so the coverage percentages above have a "units seen" denominator, not a census.
- The cavern/surface split of wild units is by species name (my list), not by layer.
- No census of units present per sample, so we cannot compute entries per possible pair or per 10k ticks.

### Proposed experiment or change
**Replace the bar with a directed "who holds what toward whom" grid. Two small panels, one encoding.**
- **Rows:** the unit holding the entry. Five classes, defined in the caption: Citizens; Livestock & pets (tame); Placed or released (roaming flag cleared); Surface wild (roaming flag set); Cavern wild.
- **Columns:** the target, in the same five classes.
- **Cell:** % of target units that received at least one PREDATOR_OR_PREY entry from that row class, with the raw count small beneath. Show 0 cells explicitly. Grey the diagonal blocks that cannot occur.
- **Colour:** sequential, one hue.
- **Panel A:** RELS + RELS2b pooled (natural arrivals; 18 cell-reps, 2+ reps per arm).
- **Panel B:** RELS2, forced release: every arrival moved into "Placed or released", which lights up that row and column. This is the counterfactual that proves the flag is what matters.
- **Strip beside the grid:** attacks that followed in RELS = 0, and the arrival's own row (BENIGN_ANIMAL / DANGEROUS_ANIMAL toward fort classes) as a second small grid or a footnote.

**Title:** "DF points the fort, and anything a script places, at new surface arrivals, not wild at wild"

**Caption draft:** "Each cell: share of the column's units that DF itself gave a PREDATOR_OR_PREY entry from at least one unit of the row's class, read from enemy_status_cache every 3,000 ticks (count beneath). 'Wild' means DF's roaming-population flag is set. A unit a script places or the tool releases has that flag cleared and falls in the 'Placed or released' row, although DFHack's isWildlife still calls it wild. An entry is a disposition, not an attack: no attack followed in RELS's 14 runs. On the surface, entries run from the fort's side toward arrivals (citizens toward 89% of arrivals seen) and almost never between two wild animals (5 entries); in the caverns, natives pair with each other. Panel B: when every arrival's flag is cleared by a forced release, DF pairs the arrivals with one another (1,551 entries), so the flag, not the species tokens, decides. Data: RELS, RELS2b, RELS2 (CTRL, tool off; 2 reps per cell)."

**Data change before plotting:**
- Add `layer` (surface, cavern or water, from `animal.population` feature/cave fields) and the isWildlife value to `rel_sample.lua`'s `desc()`.
- Log a per-sample census of units by class, so cells can be normalised.
- Rename the `other` class to "placed / released / unowned" and break out merchants' and visitors' animals.

**Spec fix if the bar is kept:** swap to `x: "writer"`, `y: "n"` (the template's convention). Change the title to "Who DF itself sets up against new arrivals (entries, not attacks)", and add a `series: target` colour.

---

## 12. "No skill or ambush arm beat the unchanged lone hunter": is SNEAK alone best?

Re-analysis: `data/eco-review/part1/A-mechanics-analysis/stl.py` (→ `stl.out`), `lone2.py` (→ `lone2.out`), `power.py` (→ `power.out`). Scoring is placed-only, as in item 3.

### 12.1 What the arms were

The definitions are in `scripts/eco-run.py:342-417`.

| arm | block | what was written | when |
|---|---|---|---|
| ctl | STL, STL2 | relation only | — |
| sneak | STL, STL2 | unit skill SNEAK rating 10 | after spawn |
| nslow | STL | SNEAK 10 + every gait's `stealth_slows` = 0 (species-wide) | before spawn |
| ambush | STL | caste flag AMBUSHPREDATOR on | before spawn |
| fight | STL2 | MELEE_COMBAT, BITE, GRASP_STRIKE, WRESTLING, DODGING 10 | after spawn |
| all | STL2 | sneak + fight + SITUATIONAL_AWARENESS 10 + AMBUSHPREDATOR | — |
| norel | STL2 | nothing, and no relation written | — |
| pkg | LONE, LONE10 | = all + `stealth_slows` 0 | — |

**Design facts (MEASURED from the logs).**
- **Fixed arm order, one load per rep.** Each rep is one CTRL load, and the arms run in the same fixed order in both reps: STL ctl → sneak → nslow → ambush; STL2 ctl → norel → sneak → fight → all.
  - ctl is always first. pkg always runs second, 100,800 t after ctl, in LONE and LONE10 (`*/log.txt`).
  - This is the cell-position trap of SW1/SW1R (findings.md:530-540), and it is unremoved here.
- **The hunter starts within ~5 tiles of 6 prey.** Most kills come early: 8 of 17 STL/STL2 kills fell before 1,000 t.

### 12.2 Per arm, STL and STL2 pooled (16 runs for ctl and sneak, 8 for the others; 30,000 t each)

| arm | runs | kills (per run, exact 95%) | runs with a kill | engaged runs (≥1 attack on prey) | hunter→prey attacks (mean; median) |
|---|---|---|---|---|---|
| ctl | 16 | 4 (0.25; 0.07-0.64) | 2 | 11 | 70 (4.4; 1) |
| **sneak** | 16 | **7** (0.44; 0.18-0.90) | 4 | 9 | 197 (12.3; 1) |
| nslow | 8 | 1 (0.12; 0-0.70) | 1 | 4 | 21 (2.6; 0) |
| ambush | 8 | 1 (0.12; 0-0.70) | 1 | 3 | 29 (3.6; 0) |
| fight | 8 | 3 (0.38; 0.08-1.10) | 3 | 5 | **315** (39.4; 9) |
| all | 8 | 1 (0.12; 0-0.70) | 1 | 2 | 18 (2.2; 0) |
| norel | 8 | 0 | 0 | **0** | 0 |

**Against ctl.**

| arm | kill rate ratio [exact 95% CI] | p | other tests |
|---|---|---|---|
| sneak | **1.75 [0.44, 8.15]** | 0.55 | runs-with-kill Fisher p 0.65; mean attacks +7.9, one-sided permutation p 0.057 |
| fight | 1.50 [0.22, 8.9] | 0.69 | attacks +35/run, p 0.030 |
| nslow | 0.50 [0.01, 5.1] | — | — |
| ambush | 0.50 [0.01, 5.1] | — | — |
| all | 0.50 [0.01, 5.1] | — | engaged runs 2/8 vs 11/16, p 0.08 |
| norel | — | — | engaged 0/8 vs 11/16, **p 0.002** |

A Poisson GLM with cell-type (hunter × prey) and block fixed effects gives:
- kills: sneak RR 1.75 [0.51, 5.98], fight 1.03 [0.22, 4.8]
- attacks (quasi-Poisson): fight ×8.7 [2.0, 37], sneak ×2.8 [0.7, 11.4]

**Where the sneak kills came from (MEASURED).**
- All 7 sneak kills were by the LION: lion × deer 4, lion × buffalo 3.
- The lion × deer control also killed 4 in STL2 (3 + 1).
- The cougar never killed in ctl or sneak. Its 3 kills came in fight (2, on deer) and all (1, on buffalo).
- Lion over all arms: 14 kills in 32 runs. Cougar: 3 in 32.
- The lion (speed 109) outruns both prey; the cougar (195) outruns neither (item 3).

**LONE / LONE10 (one cougar, 8 prey species × 6, 100,800 t).**
- pkg against ctl on placed prey, LONE10 (10 runs/arm): 29 vs 14 kills, RR 2.07 [1.06, 4.24], one-sided permutation p 0.070.
- LONE + LONE10 pooled (15 runs/arm): **40 vs 19**, RR 2.11 [1.19, 3.85], permutation p 0.032. Bootstrap difference +1.4 kills/run [+0.13, +2.73]. Attacks 1,385 vs 641 (p 0.046). Engaged runs 13/15 vs 12/15.
- pkg is *all* + `stealth_slows` 0. It ran second in every rep, so the effect is confounded with session position (natives accumulating, season change).

### 12.3 Is "SNEAK alone best" supported?

**Not supported. Not refuted either.**
- SNEAK has the highest point estimate among the single-lever arms (kills 7 vs 4 in 16 runs each). But:
  - the CI runs from 0.44× to 8×;
  - every sneak kill is a lion, which killed as often in its own control;
  - in STL2 alone, sneak equalled ctl (4 vs 4 kills; 85 vs 53 attacks).
- The only pooled kill gain with a CI above 1 is the *full* package in LONE/LONE10 (RR 2.1). That package includes SNEAK, combat skills, Observer, AMBUSHPREDATOR and no stealth slow-down, so no single lever can be credited.
- The same package as STL2 *all*, minus `stealth_slows` 0, produced 1 kill in 8 runs. The prey density differs: 6 prey of one species against 48 prey of 8 species.
- **Mechanism (DOCUMENTED, item 13).** SNEAK acts only while the unit is in ambush mode, and no placed hunter was ever caught hidden. A SNEAK effect on kills would therefore be undocumented. SW2/SW2R tested the tool's own SNEAK write (pack_sneak 0 / 0.25 / 1.0) and found no effect on kills over 4 reps (findings.md:549-551).

### 12.4 Power: how large an effect could we see?

Simulated, one-sided α 0.05, 80% power. Overdispersion was estimated from the ctl runs: STL kills NB k ≈ 0.2-0.6, LONE10 k ≈ 3. Source: `power.out`.

| design | baseline | runs per arm | minimum detectable rate ratio |
|---|---|---|---|
| STL kills (30k t, 6 prey) | 0.25/run | 2 / 8 / 16 / 32 / 64 | >20 / ~8-10 / ~5 / ~4 / ~2.5 |
| STL attacks | 4.4/run, k 0.3 | 8 / 16 / 32 / 64 | >20 / 8 / 4 / 2.5 |
| runs-with-a-kill | 2/16 | 16 / 32 / 64 | detects 12.5% → 75% / 50% / 37.5% |
| LONE kills (100.8k t, 48 prey) | 1.4/run | 2 / 8 / 16 / 32 | 5-6 / ~3 / 2-2.5 / 1.75 |

- The STL designs could detect only a ×5 effect even pooled to 16 runs per arm. At the user's 2 reps per arm, only ×20.
- The observed SNEAK ratio (×1.75) would need roughly 100+ STL runs per arm.
- The LONE design is about 6× more efficient per run (dense prey, a full season). It is the one to use.

### Answer in two sentences

The data do not support "SNEAK alone was best". Its kill ratio against the unchanged hunter is 1.75 (CI 0.44-8.2, p 0.55, 16 runs per arm), all of it lion kills that the lion's control matched. The STL design can only see effects of ×5 or more, so the honest verdict is "no detectable effect". The only CI-clear gain is the full solitary package in the dense-prey LONE design (×2.1, CI 1.2-3.9), which is confounded with cell order. If the user wants SNEAK applied anyway, it costs nothing measurable (SW2/SW2R), but should be labelled unproven.

### Evidence

- Raw rows: `data/experiments/ECO/STL-20260930-155456/STL.tsv`, `STL2-20260930-164417/STL2.tsv`, `LONE-20260930-184842/LONE.tsv`, `LONE10-20260930-212000/LONE.tsv`.
- Arm definitions: `scripts/eco-run.py:342-417`. Logs: cell order.
- Tallies: `A-mechanics-analysis/stl.out`, `lone2.out`, `power.out`.
- Matches findings.md:224-241, 246-251, 582-593.
- SW2/SW2R: findings.md:388-396, 542-551.

### Gaps

- Arm order is fixed (ctl first, pkg second), with no counterbalancing and no fresh load per arm.
- No timestamps on attacks, so engagement onset and approach are unmeasurable (item 14).
- The lion and cougar differ in speed relative to the prey, which swamps the arms. Speed is the stronger factor (item 3).
- The STL `ambush` and `all` arms flipped AMBUSHPREDATOR after spawn, which by the wiki only acts at spawn (item 13). So "ambush" was not tested.
- The skills-write rows show `units=2` or more. The write also hit cleared hunters still in `units.active` (findings.md:240). This is harmless but unverified per arm: no read-back of the rating on the live hunter.

### Proposed experiment or change

**SNK-L ("SNEAK in the dense design").**
- Uses the LONE layout: one COUGAR, or one LION as a positive hunter, among 8 prey species × 6, 100,800 t.
- Arms: ctl, sneak-only (SNEAK 10 read back at +10 t), fight-only, pkg.
- Fresh CTRL load per run, with arm order rotated by a Latin square.
- 2 reps per arm per hunter. Data: 16 runs.
- Analyse jointly with LONE/LONE10 (adding a position covariate for the old runs).
- At 2 reps the minimum detectable ratio is ~5. To reach ×2, budget 16 runs per arm. A LONE run takes ~5 min wall, so 64 runs is ~5.5 h.
- Readouts: placed kills, engagements (item 14 metric), first-attack tick, hidden trace (item 13 SNK1).

**Tool.** Keep pack_sneak at 0 by default (SW2R recommendation). Apply SNEAK for solitary hunters only as a labelled, user-chosen default until SNK-L reports.

---

## 13. "Wild animals never sneak"

Labels: MEASURED (rig data, with replicate count), DOCUMENTED (DF wiki, DFHack docs or df-structures/DFHack source), INFERRED (our reasoning, untested).
Scope: this section covers the code and documentation side. The STL/STL2/LONE10 counts are re-analysed under items 12 and 14.

### What the STL sampler read

- **Code.** `_STL_SAMPLE` at `DwarfCron/scripts/eco-run.py:345-347` walks `df.global.world.units.active`. For each live unit whose `creature_id` matches the hunter token, it adds 1 to `n`, and adds 1 to `hidden` if `u.flags1.hidden_in_ambush or u.flags1.hidden_ambusher`. It prints `eco hidden token=P n=.. hidden=..`. `stl()` (`eco-run.py:357-368`) and `stl2()` (`:383-393`) both run `["step:5000", _STL_SAMPLE]` six times (`for _ in range(6)`). That gives **one single-tick snapshot every 5,000 ticks**, at t = 5k, 10k, … 30k after placement. Nothing was sampled before the first 5,000 ticks. `scripts/stl-tally.py:17` adds up `n` and `hidden`.
- **Sample counts (MEASURED).** STL has 192 `hidden` rows (16 cells × 2 reps × 6). In 186 of them `n=1`; in 6, `n=0` (the hunter was dead or gone). STL2 has 240 rows (20 cells × 2 reps × 6), all with `n=1`. Total: **426 hunter-snapshots with hidden = 0**, out of about 72 cell-reps × 30,000 t ≈ 2.16 M hunter-ticks. The snapshots cover 0.02 % of hunter time.
- **LONE / LONE10 had no hidden sampler.** `lone()` (`eco-run.py:399-412`) samples only `_ALIVE`, and `grep hidden LONE10-*/LONE.tsv` finds nothing. The "never sneaks" claim therefore rests on STL + STL2 alone.
- **One of the two flags is not a hiding flag (DOCUMENTED).** `hidden_ambusher` is DFHack's name for bay12 `MARAUDER_ACTIVE`, commented "Active marauder/invader moving inward?" (`dfhack-53.16-r2/library/xml/df.unit.xml:1349`). The real hiding bit is `flags1.hidden_in_ambush`, bay12 `AMBUSH` (`df.unit.xml:1345`). The OR was harmless, but only the first flag measures stealth.
- **Was `hidden_in_ambush` the right flag? Yes (DOCUMENTED).** DFHack treats it as *the* sneak marker:
  - `reveal-hidden-units` "exposes all units on the map who are currently sneaking or waiting in ambush" by clearing exactly `unit.flags1.hidden_in_ambush` (`dfhack-53.16-r2/scripts/reveal-hidden-units.lua:8-20`).
  - `Units::isHidden` returns true in fortress mode when `hidden_in_ambush && !isFortControlled` (`library/modules/Units.cpp:282`).
  - The Lua API docs say `isHidden` is "hidden to the player, accounting for sneaking" (docs mirror, `docs/dev/Lua API.html`, text line ~1871).
- **What the sampler can miss (INFERRED, quantified).** With 0 hits in 426 roughly independent snapshots, the 95 % upper bound on the share of time a hunter spends hidden is 1 − 0.05^(1/426) = **0.70 %**. That is about 210 ticks per 30,000-tick cell. How long a sneak is depends on how far it covers:
  - DFHack's reverse-engineered `getSpeed` adds `2000 − 100·min(20, SNEAK)` to the move delay while hidden (`Units.cpp:1632-1636`). That is roughly +10 ticks per tile at SNEAK 10, and +20 ticks per tile unskilled.
  - So a 10-tile hidden approach lasts about 100–300 ticks.

  How likely the sampler was to see nothing, by hidden time per cell:

  | hidden ticks per cell | share of time | expected hits in 426 | P(all 0) |
  |---|---|---|---|
  | 30 | 0.1 % | 0.4 | 0.65 |
  | 100 | 0.33 % | 1.4 | 0.24 |
  | 300 | 1 % | 4.3 | 0.014 |
  | 500 | 1.7 % | 7.2 | 0.0007 |

  The data rule out hunters that stay hidden for long stretches, or that make several long approaches per cell. They do **not** rule out one short hidden approach per engagement. Engagements were rare: STL ctl had 17 attacks in 8 cell-reps (findings.md:225). So "wild AI never sneaks" (findings.md:226) is stronger than the data support. Better wording: "no hunter was caught hidden in 426 single-tick snapshots; any sneaking lasts under ~200 ticks per 30k-tick cell".
- **Placed hunters may never enter the hiding state at all (INFERRED).** The STL hunters were placed headless with `dfhack.units.create` plus field writes (memory headless-unit-placement). AMBUSHPREDATOR is documented as making a creature "**start out** hidden" (wiki Creature_token). That is a spawn-time state. Flipping the caste flag on an already-placed unit (the STL `ambush` arm, `eco-run.py:360`; STL2 `all`, `:386`) has no documented route to set `hidden_in_ambush` afterwards. The `ambush` arms therefore never tested the documented effect.

### Fields that mark sneaking

All paths are in `/Users/nathanielcannon/Claude/GitRepos/dfhack-53.16-r2/library/` (DOCUMENTED structure; behaviour notes INFERRED unless cited).

| field | file:line | what it is | use for item 13 |
|---|---|---|---|
| `unit.flags1.hidden_in_ambush` (bay12 `AMBUSH`) | xml/df.unit.xml:1345 | The sneak/hidden state. Cleared by `reveal-hidden-units`. Read by `isHidden` and by the `getSpeed` penalty | Primary marker. Sample at 1–10 t |
| `unit.flags1.hidden_ambusher` (bay12 `MARAUDER_ACTIVE`) | xml/df.unit.xml:1349 | Misnamed: "Active marauder/invader moving inward?" | Drop from the sampler, or log it separately |
| `unit.flags3.just_sprung_ambush` | xml/df.unit.xml:1431 (flags3 block starts at 1409) | Set when an ambush is sprung. How long it lasts is unknown | Trace of a sneak that just ended. Sample it with the hidden flag; it may outlast the hidden state |
| `unit.flags1.hidden_in_ambush` in speed | modules/Units.cpp:1632-1636 | `speed += 2000 - 100*min(20, SNEAK)` while hidden and not MISCHIEVOUS | SNEAK changes speed **only while hidden**. When not hidden the skill does nothing here |
| `gait_info.stealth_slows` | xml/df.creature.xml:483 | Per-gait % slow while sneaking. Vanilla defaults 50/20/10 (raws body default) | The STL `nslow` / LONE `pkg` lever. Inert if the unit never sneaks |
| `job_skill.SNEAK` = "Ambush"/"Ambusher" | xml/df.skill_enum.xml:360-364 (profession HUNTER, labor HUNT) | The skill STL wrote | — |
| `job_skill.SITUATIONAL_AWARENESS` = "Observation"/"Observer" | xml/df.skill_enum.xml:540-543 | The detection skill (prey side) | Raise it on the **prey** to test detection |
| `job_type.Hunt` (skill SNEAK) | xml/df.job.xml:241-245 | Dwarf hunting job | Positive control (dwarf hunter) |
| `unit.enemy.detection_info.last_spotted_unid[200]`, `last_spotted_unid_num` | xml/df.unit.xml:2523-2526 (used at :3071) | Units this unit has spotted ("Seen own side, enemy side, not involved") | **Detection receipt.** Did the prey spot the hunter, and when? |
| `unit.enemy.attack_awareness` (`unit_id[10]`, `flag[10]`: ATTACKING_PART_KNOWN, STRIKE_TIME_KNOWN …) | xml/df.unit.xml:2508-2521 (used at :3069) | Whether the defender saw a given attack coming | Surprise-attack marker: a hidden hunter's strike should show "unknown" flags |
| `unit.status.misc_traits` id `RecentlyFledConflict` (bay12 `HAVE_RECENTLY_FLED_CONFLICT`, auto-decrement) | xml/df.d_basics.xml:2106; vector at df.unit.xml:2957 | Set when the unit flees a conflict | **Flee-onset marker for the prey** |
| misc_traits `HuntCheckDelay`, `ForcedToFight`, `FleeingInteractionRestricted` | xml/df.d_basics.xml:2099, 2105, 2134 | Hunting cadence; cornered prey; fleeing state | Secondary markers |
| `action_type` FLEE_CONFLICT, FLEE_CONFLICT_IN_TERROR, FLEE_FROM_UNIT, HUNT | xml/df.d_basics.xml:1809-1909 | AI action enum, held in `actionst.action` (df.unit.xml:1218-1219) | Found only under squads/activities (df.squad.xml:58), not on a wild unit. Use misc_traits instead |
| `unit.path.goal` (`unit_path_goal`: MarauderMill, WildernessRoamer, FleeTerrain, StartHunt …) | df.unit.xml:2640; enum xml/df.d_basics.xml:3943+ | Current path goal | A hunter's goal during approach. No sneak or stalk goal exists for wild units |
| `unit.actions[]` type Move/Attack; `unit_move_move_flag.charge` | df.unit.xml:1167, 236-238 | Per-tick actions; the Move flag `charge` | Charge onset = the end of the approach |
| `unit.opponent.unit_id/unit_pos/timer` | df.unit.xml:2699-2704 | Last target ("FleeFromOpponent panic") | Prey's last threat; check the timer around flee onset |
| global `debug_showambush` | xml/df.game_v.xml:342 | "Makes hidden ambushers visible on-screen and in the units list" | Leave false. `isHidden` returns false when it is set (Units.cpp:270) |
| alert `BEAST_AMBUSH`, `AMBUSH_AMBUSHER_NATURE` | xml/df.g_src.basics.xml:325, 222 | Announcement types | DF announces a beast ambush. Watch the reports |

There is no `ambush_counter` and no unit job or path goal named sneak or stalk for wild units. The `Hunt` job and the `HUNT` action exist for fort hunters. Wild units carry no job.

### How DF sneaking works (documented)

- **The skill acts on approach, not in the fight.** Wiki, Ambusher / Hunter page (dwarffortresswiki.org/index.php/Ambusher):
  - "The ambusher skill is what determines how well a unit can sneak without being caught."
  - "As an ambusher gets closer to their prey, there is a greater and greater chance they will be spotted by the animal … Higher skill allows dwarves to get closer before being spotted."
  - "Once close enough, the ambusher skill is no longer relevant … From there, the ambusher skill has no effect, and only combat skills are used."
  - "An unskilled hunter will crawl in ambush mode, making the hunter unable to reach fast animals like badgers."

  This contradicts the ECO reading "the skill acts in the fight, not by hiding" (findings.md:227). By the documentation, SNEAK can matter only while the unit is in ambush mode, which is `hidden_in_ambush`. Any SNEAK effect without the flag would be undocumented.
- **Detection is decided by the observer.** "A sneaking character can remain undetected by others so long as they remain out of the other creatures' scope of perception … [range] varies by sensory organs and observer skill." "Until the character is detected, no level of conflict is generated between the character and an enemy or timid creature." (Ambusher page.) Observer page: the skill "increases the chance to spot a stealth unit … the higher the skill the greater the range" (marked as needing verification); "Detections at a range of 20 tiles have been reported."
- **Which creatures sneak, per the wiki:**
  - AMBUSHPREDATOR: "Makes the creature start out hidden and remain near its original location until its prey draws near" (Creature_token). The only vanilla user is SPIDER_CAVE_GIANT (`data/eco-desk/token-counts.tsv`; T0-triage.tsv).
  - MISCHIEVOUS: "spawns stealthed … stays hidden until a citizen spots it" (GREMLIN). GREMLIN is also the only vanilla creature with NATURAL_SKILL:SNEAK (raws scan, this review).
  - LARGE_PREDATOR: "In adventurer mode, large predators will try to ambush and attack you."
  - Trained hunting animals "can sneak alongside their masters"; war beasts "cannot sneak". In the df-structures caption: "Hunting animals can move stealthfully during hunts" (xml/df.d_interface.xml:3760).
  - STEALTH_SLOWS (gait): "Slows movement by the specified percentage when the creature is sneaking." Every vanilla gait carries it (body default 50/20/10).
- **What the documentation implies (INFERRED).** The engine can sneak with any creature. A wild animal sneaks only through a spawn-time state (AMBUSHPREDATOR, MISCHIEVOUS) or through hunting training under a hunter dwarf. No page describes a wild fortress-mode animal entering ambush mode on its own to stalk prey. "Wild animals never sneak" is therefore the documented default, and our 0/426 agrees with it. The STL attack differences, if real, must come from something else: a SNEAK effect outside the flag (undocumented), or noise. STL2 ctl 53 attacks / 4 kills vs sneak 85 / 4 (stl-tally) points to noise.
- **Ambushes in fortress mode** (wiki Ambush page) are humanoid squads, werebeasts, and cavern animal-person swarms. "Hidden ambushers do not display combat reports … their combat actions may be included in other units' combat reports." So a hidden attacker can still fire UNIT_ATTACK events, but our attack counter (eventful, `cx-eco.lua:449-455`) records **no tick**, so it cannot tie an attack to a hidden state.

### Experiments

All designs: 2 reps per arm; rep 2 runs the arms in reverse order; fresh CTRL load per arm; placed-only scoring. Each run needs a manifest receipt in the pre and in every pass: the subject is on the map, the forced state is read back, `dfhack --version` shows r2. A failed receipt makes the replicate vacuous, not zero. Re-validate on r2 first (open item revalidate-dfhack-r2).

**Instrument changes (desk, before any run).**
1. A `cx-eco trace` verb. A `repeat-util` job every **1 tick** for the subject hunter and its prey keeps a 600-tick ring buffer of:
   - tick, pos, distance to the nearest prey
   - hunter `flags1.hidden_in_ambush`, `flags3.just_sprung_ambush`, `path.goal`, `actions[0].type`, Move `charge`
   - prey `misc_traits` RecentlyFledConflict/ForcedToFight, `detection_info.last_spotted_unid_num` and whether the hunter's id is in it, and `attack_awareness` for the hunter's id

   `eventful.onUnitAttack` records each attack with its tick and, on a pair's **first** attack, dumps the 300 ticks before it. This fixes the missing timestamps.
2. Drop `hidden_ambusher` from the hidden test; log it as `marauder_active`.

| id | question | design | readout | power note |
|---|---|---|---|---|
| **SNK0 sampler positive control** | Does the trace see sneaking at all on this rig? | CTRL. Arm A: one citizen with the HUNT labor, a crossbow and bolts; 6 DEER placed 40 tiles off, 6,000 t. Arm B: BOATS cavern, a DF-drawn (not placed) SPIDER_CAVE_GIANT, if present in the cavern pool (receipt: the unit exists). 2 reps each | Ticks with `hidden_in_ambush`=1 for the hunter dwarf during approach; whether the spider starts hidden | One positive per arm validates the instrument. If the dwarf never shows hidden, the flag is not the sneak marker on 53.16 and every 0/426 claim falls |
| **SNK1 does a wild hunter ever hide?** | Do placed and DF-drawn wild hunters enter ambush mode before an attack? | CTRL, 1 LION + 6 WATER_BUFFALO r5 written (the STL pair with most kills), 6,000 t. Arms: ctl vs SNEAK 10. Add one native-only arm: a DF-drawn COUGAR (FREQUENCY steered as RELS2b), traced from arrival | Per first attack: hidden ticks in the 300 t before it; `just_sprung_ambush` seen | Every first attack is a full-trace observation, so there is no 0.02 % duty cycle. Expect 2–10 first attacks per arm. One hidden episode refutes "never" |
| **SNK2 forced hide** | If a wild hunter is hidden, does SNEAK change how close it gets and how often it kills? | As SNK1. At t0 write `flags1.hidden_in_ambush=true` on the hunter. Arms: hidden + SNEAK 0, hidden + SNEAK 10, hidden + SNEAK 20, not hidden (ctl) | Tick the flag clears and the hunter–prey distance then; prey flee onset (RecentlyFledConflict set; prey `last_spotted` gains the hunter); first-attack tick; kills | Tests the documented mechanism directly. Prediction (DOCUMENTED): detection distance falls as SNEAK rises; speed penalty +2000/+1000/+0 (Units.cpp:1634). If DF clears the flag at once on wild units, that is itself the answer: the AI cannot sneak |
| **SNK3 prey detection dose** | Does the prey's Observer skill change flee-onset distance? | SNK2's hidden + SNEAK 10 arm × prey SITUATIONAL_AWARENESS 0 vs 20 | Flee-onset distance (median over prey) | A 2-arm contrast at 2 reps × 6 prey gives about 12 onset distances per arm. A Mann–Whitney test detects a shift of ~1 SD (power ~0.8) |
| **SNK4 datamine diff** | Which fields change on a hunter between wander, approach and attack? | After SNK1/2 show an approach: `devel/datamine snap h df.unit.find(ID).flags1` (likewise `.flags3`, `.status.misc_traits`, `.enemy.detection_info`, `.path`, `.counters`) at approach start, then `devel/datamine diff h` at first attack. Also `devel/datamine watch -n hid -i 1 df.unit.find(ID).flags1.hidden_in_ambush`. Hunter and nearest prey both | Changed paths | Tool documented in `dfhack-53.16-r2/scripts/docs/devel/datamine.rst` (watch/snap/diff/find; `-i` = frames). Limits: MAX_DEPTH 5, 200 elements, 20,000 leaves, 200 output lines (`scripts/devel/datamine.lua:42-45`). Snap sub-structures, not the whole unit. `watch` prints to the DFHack console, not to the RPC caller, so the rig must read the console log. Watches are cleared on world unload |

Flee-onset distance is defined as the hunter–prey distance at the first tick when the prey's `RecentlyFledConflict` misc trait appears, or else when its path goal leaves the herd for FleeTerrain. INFERRED: which marker DF actually sets for animal flight must be confirmed in SNK4 before SNK3 is scored.

### Answer in two sentences

DFHack and the wiki both treat `flags1.hidden_in_ambush` as the sneak state. Across 426 single-tick snapshots, no STL/STL2 hunter carried it. That puts a 95 % ceiling of ~0.7 % on hidden time (~210 ticks per 30k cell). It does not exclude one short hidden approach per engagement, and the `hidden_ambusher` half of the test was a marauder flag, not a hiding flag. By the documentation, wild animals sneak only by spawn-time state (AMBUSHPREDATOR = giant cave spider, MISCHIEVOUS = gremlin) or as trained hunting animals, and SNEAK acts only on approach, "no effect" once in combat. So "the skill acts in the fight" is unsupported, and any STL sneak-arm lift is most likely noise. A traced, forced-hide experiment (SNK1/SNK2) settles it.

### Evidence

- Sampler: `DwarfCron/scripts/eco-run.py:342-368` (STL), `:371-393` (STL2), `:399-412` (LONE, no hidden sampling); `scripts/stl-tally.py:17`. Rows: `data/experiments/ECO/STL-20260930-155456/STL.tsv` (192 hidden rows, 186 with n=1), `STL2-20260930-164417/STL2.tsv` (240, all n=1), hidden=0 throughout (MEASURED, 2 reps per cell).
- Fields: `library/xml/df.unit.xml:1345, 1349, 1431, 2508-2526, 2640, 2699-2704, 2957`; `xml/df.d_basics.xml:1809-1909, 2099-2134, 3943+`; `xml/df.creature.xml:483, 848`; `xml/df.skill_enum.xml:360-364, 540-543`; `xml/df.job.xml:241-245`; `xml/df.game_v.xml:342`; `xml/df.d_interface.xml:3760`.
- DFHack code and docs: `library/modules/Units.cpp:267-293` (isHidden), `:1632-1636` (sneak speed penalty); `scripts/reveal-hidden-units.lua`; `scripts/docs/devel/datamine.rst`; `scripts/devel/datamine.lua:42-45, 139-175`; docs mirror `docs/tools/reveal-hidden-units.html` ("Reveal sneaking units").
- Wiki (fetched 1 Oct 2026): Ambusher/Hunter, Observer, Ambush, and Creature_token (AMBUSHPREDATOR, MISCHIEVOUS, LARGE_PREDATOR, STEALTH_SLOWS), quoted above.
- Raws: AMBUSHPREDATOR only on SPIDER_CAVE_GIANT (`data/eco-desk/token-counts.tsv`); NATURAL_SKILL:SNEAK only on GREMLIN; STEALTH_SLOWS defaults 50/20/10 (vanilla raws scan, Python, this review).
- The tool writes SNEAK 10 for packs at a share of 0.25 or more (`seasonal-wildlife/scripts/seasonal-wildlife.lua:4167-4208`) and the solitary package including AMBUSHPREDATOR (`:6402-6510`). Both rely on a mechanism that, by the documentation, needs ambush mode.

### Gaps

- No positive control: we never showed that the sampler sees a sneaking unit on this rig (dwarf hunter, giant cave spider).
- Sampling duty cycle was 0.02 %, with no samples in the first 5,000 t and no attack timestamps. Hidden state cannot be tied to attacks.
- Unknown whether DF ever sets `hidden_in_ambush` on a wild unit after spawn, and whether it clears a forced one at once.
- Unknown which field marks animal flight (RecentlyFledConflict vs path goal FleeTerrain vs actions). Needs SNK4.
- The `ambush` arms flipped a spawn-time flag on already-placed units, so they could not test AMBUSHPREDATOR's documented effect.
- `detection_info` and `attack_awareness` are documented as structures only. What they mean for wild-vs-wild detection is INFERRED.

### Proposed experiment or change

1. Desk, now: correct the claim on the page, when revisions resume. Replace "wild animals never sneak; the skill acts in the fight" with: "No placed hunter was caught hidden in 426 snapshots (≤ ~0.7 % of the time). By the wiki, wild animals sneak only when spawned as ambushers (giant cave spider) or as hunting animals, and SNEAK acts only while sneaking."
2. Instrument: add `cx-eco trace` (1-tick ring buffer, first-attack dump, timestamped attacks). Split `hidden_ambusher` out of the hidden test.
3. Run order: SNK0 (positive control) → SNK1 (does a wild hunter hide?) → SNK2 (forced hide × SNEAK 0/10/20) → SNK3 (prey Observer 0/20) → SNK4 (datamine diff). Each arm 2 reps, counterbalanced, CTRL, 6,000 t.
4. Tool, pending SNK2: if forced hiding plus SNEAK raises kills, give the tool a "stalk" write (set `hidden_in_ambush` on armed solitary hunters on arrival) instead of the inert SNEAK and stealth_slows writes. If not, retire SNEAK, stealth_slows and AMBUSHPREDATOR from the solo package and pack_sneak (consistent with SW2/SW2R, findings.md:542-551).

---

## 14. "Combat skills raise engagement": what the data can say, a metric, and a powered design

### 14.1 What was measured, and what "engagement" meant on the page

The rig logs, per cell, the **total** count of UNIT_ATTACK events for each attacker>defender race pair. The read is at the end of the cell (`attacks` rows). It also logs Death incidents with a tick (`dt`).
- There is **no timestamp on any attack** (item 13: the eventful counter records none, `cx-eco.lua:449-455`).
- There is no position trace.

So the page's "engagement" could only mean the attack count. An attack count is the number of strikes. One long fight with a buffalo can produce 100+ rows.

STL2 fight arm against ctl (MEASURED, 8 vs 16 runs pooled with STL ctl; `stl.out`):

| readout | fight | ctl | test |
|---|---|---|---|
| hunter→prey attacks | 315 (mean 39.4/run) | 70 (4.4/run) | permutation p 0.030; GLM with cell-type fixed effects ×8.7 [2.0, 37] |
| runs with ≥1 attack (a crude "engaged" binary) | 5 of 8 (62%) | 11 of 16 (69%) | Fisher p 1.0; logistic OR 0.75 [0.10, 5.4] |
| kills | 3 | 4 | RR 1.50 [0.22, 8.9] |

- 276 of the 315 fight attacks came from two runs, cougar × deer (131 and 145, 1 kill each).
- The skill arm did not make the hunter engage in more runs. It made the fights that happened **longer or more intense**.
- The cougar, which cannot outrun deer, killed deer only in the fight arm (1 + 1). The ctl and sneak cougar had 0 kills on deer in 8 runs.
- INFERRED: combat skill helps once contact happens, and contact is set by speed and placement.

LONE/LONE10 pkg against ctl (includes the same combat skills; 15 runs/arm): attacks 1,385 vs 641 (p 0.046), engaged runs 13 vs 12, kills 40 vs 19. The pattern is the same: more strikes and more kills, the same share of runs engaged. It is confounded by cell order (item 12).

**Verdict on the claim.** "Combat skills raise engagement" is MEASURED only as "combat skills raise attack strikes", and only in 2 runs that dominate the total. Engagement in the sense the user means (more encounters started) shows no difference in the one binary we have.

### 14.2 An engagement metric (definition)

Define these per hunter unit h and prey unit p, from timestamped attack events. All need the new logger in 14.3.

- **Attack event:** an `eventful.onUnitAttack(attacker, defender, wound)` callback with attacker = h and defender = a placed prey, stamped with the absolute tick.
- **Engagement (bout):** a maximal run of attack events from h on one prey p in which consecutive events are less than **G = 100 ticks** apart. A new bout starts after a gap of 100 t or more, or on a different prey.
  - G = 100 t is about 2 DF hours (1,200 t per day).
  - G is chosen from the gap distribution once the logger runs: take the trough of a bimodal log-gap histogram.
  - A sensitivity check at G = 50 and 300 is reported alongside.
- **Engagement rate:** bouts per hunter per 1,200 t (per hunter-day), over the time the hunter is alive and on the map. This is an exposure offset in a Poisson/NB model: offset log(alive hunter-days).
- **Contact (approach) event**, a lower-level complement:
  - the first tick at which h is within 2 tiles of some p while the relation row reads PREDATOR_OR_PREY;
  - it needs the 10-tick position trace.
  - Contacts per hunter-day separate "meets prey" from "attacks on meeting". The ratio bouts / contacts is **attack propensity**.
- **Outcome of a bout:** kill (the prey's Death incident within 300 t of the bout's last event, killer = h), prey escaped (alive and > 10 tiles away 300 t later), or hunter lost.
- **First-attack latency:** ticks from placement, or from arrival for DF-drawn hunters, to h's first bout.

On the page, report engagement rate, attack propensity and kill-per-bout separately. "More engagements without more kills" is then a measurable success, as the user asks.

### 14.3 Logger change (desk, before the rig is free)

- `cx-eco watch2`: a `require('plugins.eventful')` `onUnitAttack` handler. For each event it appends a TSV row:
  - `attack tick=<cur_year_tick + year*403200> a=<id> d=<id> a_tok d_tok a_spawned d_spawned dist=<chebyshev>`
- A `repeat-util` job every 10 t logs, for the subject hunters, `pos` and the nearest related prey's id and distance. This gives contacts. With few hunters the cost is small (memory: fail-fast mandate; keep a deadline).
- A tally `scripts/engage-tally.py` builds bouts, contacts and outcomes from these rows, with G as a parameter.
- Receipt in the pre: one forced test attack is logged with a tick (spawn two hostile units adjacent, check one `attack` row) before the arms run. Otherwise the replicate is vacuous.

### 14.4 A powered experiment (ENG1)

**Question.** Do combat skills (and SNEAK) raise the engagement rate, attack propensity or kill per bout of a solitary hunter, at natural density?

**Design.**
- CTRL, the LONE layout:
  - 8 prey species × 6 at r20
  - one hunter at the centre
  - relation written to all
  - 50,400 t (half a season: half the LONE kills came after 3,459 t, so 50k covers most)
- Hunter: COUGAR (slow, the hard case) and LION (fast), as a blocking factor.
- Arms: ctl; fight (MELEE_COMBAT, BITE, GRASP_STRIKE, WRESTLING, DODGING 10); sneak (SNEAK 10). Each skill is read back on the live hunter at +10 t as the receipt.
- **Fresh load per run.** Arm order per rep follows a Latin square (ctl-fight-sneak, fight-sneak-ctl, sneak-ctl-fight). This removes the position confound of every earlier block.
- Hunter death censors exposure: the offset uses alive time.

**Power** (`power.py`, NB with k = 1, baseline 3 bouts per run):

| runs per arm | minimum detectable rate ratio (80% power) |
|---|---|
| 2 | ~8 |
| 4 | ~4 |
| 8 | ~3 |
| 16 | ~2 |

- Bouts are many per run where kills are few, so the engagement rate is much better powered than kills (STL kills needed ~16 runs/arm for ×5).
- **Recommended:** 8 runs per arm per hunter = 48 runs × ~2.5 min wall at 50k t ≈ 2 h. This detects ×3 on engagement. For the user's pace rule, run 2 reps first: a pilot to fix G, the baseline rate and the overdispersion. Then size the rest from the pilot's k.
- **Analysis:** NB GLM, bouts ~ arm + hunter + offset(log alive-days); the same for contacts. Binomial for kill-per-bout, with bouts nested in runs (a GEE or a run random effect). Report RRs with 95% CIs.

### Answer in two sentences

Our data cannot separate "more engagements" from "longer fights". Combat skills multiplied attack strikes (×8.7, CI 2-37) but did not change the share of runs with any attack (5/8 against 11/16), and 276 of the 315 strikes came from two cougar × deer runs. With timestamped attacks we can define an engagement as a bout of attacks separated by gaps under 100 t and report bouts per hunter-day. That makes a powered test feasible at about 8 runs per arm for a ×3 effect, and success then means "more bouts" even without more kills.

### Evidence

- Raw rows: `STL2-20260930-164417/STL2.tsv`, `STL-20260930-155456/STL.tsv`, `LONE*-*/LONE.tsv`.
- Tallies: `A-mechanics-analysis/stl.out` (per-arm table, GLM), `lone2.out`, `power.out` (the engagement-rate power row).
- Attack logger without ticks: `chronicler/dfhack/scripts/cx-eco.lua:449-455` (item 13).
- findings.md:235-239 ("skills raise engagement (fight) at most").

### Gaps

- No attack timestamps or positions in any ECO block, so bouts, contacts and latency cannot be computed retroactively.
- The STL2 fight arm has 8 runs, and two of them carry 88% of its strikes.
- The 100 t bout gap G is an assumption until a pilot shows the gap distribution.
- Combat skill effects may differ by prey that fight back (buffalo, elephant); this needs a prey block.

### Proposed experiment or change

1. Build `watch2` + the 10-t position trace + `engage-tally.py` (desk).
2. ENG1 pilot (2 reps/arm/hunter, 12 runs), then ENG1 proper (8/arm/hunter).
3. On the page, when revisions resume: rename "engagement" to "attack strikes" for the existing STL/LONE numbers. Report the engaged-run binary beside them.
