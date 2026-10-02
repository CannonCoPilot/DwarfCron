# Part 2 desk answers: R1, R2, R3, R6, R22, R24, R28, R40

W2:Urist desk research, 1 Oct 2026.
- **No rig was used.** DF is the user's running game.
- **Nothing committed, nothing edited.** No code or report source was touched.
- **Only files added:** this file, plus the analysis code and outputs it cites:
  - `data/eco-review/part2/R3-analysis/` (`harm.py`, `fit.py`, `harm.json`, `harm.tsv`, `fit.out`);
  - `data/eco-review/part2/R28-analysis/` (`ud.py`, `ud.json`);
  - `data/eco-review/part2/R24-analysis/` (`aplost.py`).

**Labels.**
- **MEASURED**: our rig data, with the replicate count.
- **DOCUMENTED**: DF wiki, DFHack or df-structures source, vanilla raws, or tool code, cited file:line.
- **INFERRED**: our reasoning, untested.

**Path prefixes.**
- `SWP/` = `Projects/seasonal-wildlife/` (checked out on v7.0, head 99c1ec8).
- `DC/` = `Projects/DwarfCron/`.
- `dfhack-latest/` and `dfhack-53.16-r2/` = `~/Claude/GitRepos/…`.
- Raws = `…/Steam/steamapps/common/Dwarf Fortress/data/vanilla/`, read with Python.

## Headline answers

- **R1. All four terms are real code paths.** They differ mainly in `flags2.roaming_wilderness_population_source`:
  - **DF brought**: the flag is set. The unit enters at a map, wet or cavern edge.
  - **Tool placed** (`PLACE.one`): the flag is cleared at birth. Stock is debited and the enemy-status row is reset to NONE.
  - **Rig placed** (`cx-eco spawn`): the flag is cleared. The reference may be borrowed, nothing is debited, the countdown is 200k, and the row is reset to **STRANGER (0)**. That last one is a rig bug worth a one-line fix.
  - **Released**: only the two flag bits are cleared.
  - All four are DFHack-wild. Only DF-brought, unreleased units are DF-wild aimers.
- **R2. "The fort's side" is every slotted unit whose roaming flag is clear:** citizens, livestock and pets, caravan and visitor animals, and placed or released wildlife.
  - DF writes PREDATOR_OR_PREY from these units toward each new arrival.
  - The arrival writes BENIGN_ANIMAL or DANGEROUS_ANIMAL back.
  - "Non-wild" therefore means *roaming flag clear on the aimer*. MEASURED correlation, mechanism INFERRED.
- **R3. Partly.**
  - Predator deaths and wounds are flat across deer to buffalo (OR 1.07 per doubling [0.68, 1.68]).
  - They jump only at elephant-scale size gaps (28% of wolves, 0% of giant hyenas) and with non-BENIGN or raging prey of any size (capybara 5/5 wolves; raging deer 19/72).
  - "Fights get longer" is not supported (×1.00).
  - Wounds were never logged directly; the attack rows are wound events.
  - Experiment PMH1 is designed below.
- **R6. The driver is citizens in a cavern z-band** (pressure 0.02 gain per citizen, 0.01 decay per 300 t, threshold 1.0).
  - The trigger is the next roster-admitted, DF-drawn cavern group, which gets the agitated flag.
  - It ends on its duration (10 d), on wipe-out, or on switch-off, followed by a 30 d cooldown.
  - **The player gets no DF announcement.** There are only ledger lines and the pressure readouts.
  - The gap halving is driven by the maximum pressure across all caverns, so it is not layer-specific.
- **R22. DF has only `flow_size` 0-7 per tile; "column depth" is computed by us, two different ways.**
  - "Depth" and "deep" carry five meanings across the tool and the report.
  - 19 places are listed below, including the same cavern printed as "depth 0", `cavern0:` and "Cavern 1".
- **R24. The two mods restore attacks to the extinct animal people only.**
  - The ecology gaps are in the plain extinct animals: apex FREQUENCY 50 (against 2-5), no GRAZER on 17 dinosaurs, and misfiled Titanoboa, Dimetrodon, Tiktaalik and Eoraptor.
  - Recommendation: a tool override table plus the mods as an option.
- **R28. Raw depth = `layer_depth` + 1** (1-3 caverns, 4 magma sea, 5 underworld).
  - **37 species can live in cavern 1.** Only RAT_LARGE and MOLE_DOG_NAKED are confined to it.
  - MAGMA_CRAB is 3:5 with a lava-only biome, and lives in the magma sea on CTRL.
  - The tool layers by `cave_id`, never by the raw, so DF waves are not misplaced. But the `place` verb would put a deep entry on the surface, and placed lava species land on dry floor.
- **R40. `pack_sneak` is a mass-share threshold (0.25) that gives group hunters a soul SNEAK skill of 10.**
  - SNEAK was only ever tested at 0 against 10, on the unit, never across 0-20 and never as the caste NATURAL_SKILL.
  - The threshold sweep (0 / 0.25 / 1.0) showed no effect.

---

## R1 — "DF brought", "the tool placed", "the rig placed", "it was released"

**Short answer.** All four terms name real code paths, and none is just a figure of speech. Three of them create or admit a unit:
- **DF brought**: DF's own wave draw.
- **the tool placed**: seasonal-wildlife's `PLACE.one`.
- **the rig placed**: DwarfCron's `cx-eco spawn`.

The fourth, **released**, changes a unit DF brought. It clears two flag bits and nothing else.

All four end with a unit that DFHack calls wildlife, because all four carry a population reference. What separates them is mainly `flags2.roaming_wilderness_population_source` (set only on a DF-brought unit not yet released), plus where the unit enters, its leave countdown, how its enemy-status row starts, and which stock is debited.

### Definitions, grounded in code

- **DF brought (a DF wave).**
  - What it is: DF draws a group from a regional, cavern or lake/ocean `world_population` entry and walks it in.
  - Where it enters (MEASURED):
    - land waves at the map edge, from `plotinfo.map_edge` surface tiles (`SWP/STATE.md:783-791`, E14);
    - aquatic waves through wet edge tiles, not through that table (`STATE.md:775, 791`);
    - cavern waves at the cavern band's edge (`STATE.md:3169, 3218`).
  - A new unit is listed `inactive` at the edge for one sample before it is on the map (MEASURED, `STATE.md:651`).
  - Fields on the unit:
    - `unit.animal.population`, the six-field `world_population_ref` (DOCUMENTED: `dfhack-latest/library/xml/df.unit.xml:2692`, `df.regionpop.xml:36-60`);
    - `animal.leave_countdown` ("once 0, it heads for the edge and leaves", `df.unit.xml:2694-2695`);
    - `flags2.roaming_wilderness_population_source` set. DFHack names the bit `ROMAING_WILDERPOP` (`df.unit.xml:1405`). MEASURED: the tool's gate test `gatedLayer` relies on it (`SWP/scripts/seasonal-wildlife.lua:3511-3519`), and the RELS probe classes such units as `wild` (`DC/data/eco-desk/v2/research/lua/rel_sample.lua:16`).
    - The twin bit `..._not_a_map_feature` (`df.unit.xml:1406`) was never read on its own. Its state on a DF unit is UNKNOWN.
  - The entry's stock is debited per unit at the draw (MEASURED, E15, `STATE.md:645-650`).
  - DF gives the unit an enemy-status slot lazily: 0 natives were slotted at load, and 42 were slotted at +100 t (MEASURED, RELP, `findings.md:242`).
  - While any unit of a source keeps the flag, DF sends no new wave from that layer (MEASURED, G1/G2, `seasonal-wildlife.lua:3401-3406`; gate open at ≤1 flagged unit, `:3592-3596`).
- **The tool placed** (`PLACE.one`, `seasonal-wildlife.lua:3948-3970`). This covers every tool path: `place` / `PLACE.fromEntry` `:3994-4024`, Driver B water draws `:4941`, sponges `:5514`, and the rig's `cx-load wild`, which calls the tool's `place` (`DC/chronicler/dfhack/scripts/cx-load.lua:154-168`).
  - `dfhack.units.create(race, caste)` makes the unit, with a random caste.
  - The six-field reference is copied from the pool entry `pent`. For sponges, `pent` is a lent entry: the region's sponge entry, else any managed ocean species' entry (`:5491-5505`).
  - `leave_countdown` is set: 25,000 by default; `cfg.water.countdown` × 0.8-1.2 for Driver B; "years out" for sponges.
  - **Both roaming flags are cleared** (`:3959-3960`).
  - Then: `pos`/`idle_area` are set, the unit is inserted in `units.active`, the occupancy bit is set, and `flags1.inactive=false`.
  - `PLACE.enemySlot` takes the first free slot and resets its row and column to **NONE (−1)** (`:3976-3990`, the SLOTV fix).
  - The entry's stock is debited by 1 per unit (`:4021`, `:4942`).
  - Placement is anywhere on a free tile: land on walkable ground, water at flow ≥4, cavern inside its band (`:4000-4016`). It is not at the map edge.
  - No histfig, civ or tame writes. All DOCUMENTED (code).
- **The rig placed** (`cx-eco spawn`, `DC/chronicler/dfhack/scripts/cx-eco.lua:337-403`). This happens only in experiments, never in a player's game.
  - The same `create` call and the same placement writes as the tool, with four differences:
    1. **The reference.** It is the *first* Animal entry anywhere in the world with that race, with no region or layer filter. With none, it is the first surface Animal entry of **any species** ("borrowed", `:343-354`). No stock is debited.
    2. **Countdown.** 200,000 by default (`:340`).
    3. **The enemy-status row.** It is reset to **0 = STRANGER** (`:394`), not NONE. SLOTV showed DF's empty cell is NONE (−1), and the tool's own comment says STRANGER "predators fight (E11c)" (`seasonal-wildlife.lua:3985`).
    4. **Position.** Units go at a chosen spot within a radius, with caste filtered by sex (`:355-369`).
  - Both roaming flags are cleared (`:382-383`).
  - `cx-load clearwild` vanishes units via `vanish_countdown=1` (`cx-load.lua:107-112`). That is removal, not placement.
- **It was released** (`releaseGroup`, `seasonal-wildlife.lua:3568-3579`).
  - The tool's gate takes a DF-brought group and clears `roaming_wilderness_population_source` and `..._not_a_map_feature` on every member. It then marks the group `resident=true` and `detached_at` in the tool's own saved data.
  - Callers:
    - `detachOldest` (`:3581-3590`) when the layer has room under its group cap;
    - `V7.drainGate`, i.e. `gate_drain`, which keeps releasing the next-oldest gated group until ≤1 flagged unit remains (`:3592-3614`);
    - coupling (`:3664`);
    - send-off (`:5971`).
  - Nothing else changes: population reference, countdown, slot, position and stock all stay as they were.
  - DF still refunds the entry when the unit leaves, flag or no flag (MEASURED, E4-E9bc, `STATE.md:3415-3420`).
  - The rig's `cx-probe release` does the same flag clear (A-mechanics §2.1).

### Fields per origin

| field | DF brought (wave, not yet released) | released (DF-brought, gate opened) | tool placed | rig placed (`cx-eco spawn`) |
|---|---|---|---|---|
| `animal.population` (6 fields) | the drawn entry | unchanged | copied from a managed pool entry (sponges may get a lent ocean entry) | first world entry of the race, else a borrowed other-species surface entry |
| `isWildlife` (DFHack, `Units.cpp:601-607`) | true | true | true | true |
| `flags2.roaming_wilderness_population_source` | **set** | cleared | cleared at birth | cleared at birth |
| `..._not_a_map_feature` | unknown (never read) | cleared | cleared | cleared |
| entry point | map edge / wet edge / cavern edge | (already on map) | any free tile on its layer | chosen spot ± radius |
| `leave_countdown` | DF's value (not logged) | unchanged | 25,000; water ×0.8-1.2 of cfg; sponge years | 200,000 |
| enemy-status slot | DF, lazy | unchanged | allocated at once; row/col = NONE (−1) | allocated at once; row/col = **STRANGER (0)** |
| stock debit | DF, per unit (E15) | none (refund on departure, E4) | tool, per unit | **none** |
| holds DF's layer gate shut | yes, while ≥2 flagged | no | no | no |
| tracked as a tool group | yes (`discoverGroups`, `:3539-3562`) | yes, `resident` | Driver B water groups yes (`:4946`); `place` no | no |

### Which ones DF treats as wild for aiming

- **As aimers.** Only units with the roaming flag set count as wild to DF, and on the surface they almost never aim: 5 of 370 PREDATOR_OR_PREY entries in RELS.
  - Released, tool-placed and rig-placed units all have the flag cleared, and DF aims them like citizens and livestock at later arrivals:
    - RELS `other>wild` 57;
    - RELS3 released ravens to skunks 2 and to kestrels 8;
    - RELS2 forced release `other>other` 1,551 vs RELS2b 29 wild>wild.
  - Status: MEASURED, 2 reps per block (`DC/data/eco-desk/findings.md:258-267, 299-308, 404-409`).
- **As targets.** Released units are still aimed at (RELS2). So the target-side test looks like "has a population reference", the `isWildlife` sense (INFERRED from MEASURED rows).
- **Caverns are the exception.** Flagged cavern units aim at each other: RELS 38, RELS2b 9/7, RELS3 66 (MEASURED).
- **Caveats.**
  - The flag-as-DF's-test is correlational. No run set the flag back on a placed unit: WILD1, proposed in A-mechanics §2, does that.
  - Tool-placed units' aiming is INFERRED from the rig-placed and released rows. No relation probe ran on `PLACE.one` units specifically.
  - The rig's STRANGER initialisation (`cx-eco.lua:394`) means every rig-placed unit started with STRANGER toward every slotted unit until DF overwrote it. This applies to every CAL/STL/LONE/REACH/GPK hunter.
  - That is one more way rig-placed units differ from tool-placed ones. Its effect on attacks is UNTESTED, and it is a one-line rig fix (write −1).
- **Recommended vocabulary** (consistent with A-mechanics §2):
  - **arrival** (DF brought, flag set);
  - **resident** (released);
  - **tool-placed**;
  - **rig-placed**;
  - **DF-wild** (flag set) vs **DFHack-wild** (`isWildlife`).

---

## R2 — "the fort's side" and the mechanic behind it

**Definition (as used in the report, `DC/data/eco-report/eco-report-doc-rev326.md:742-753`).**
- "The fort's side" means the units that DF itself sets up against each new surface wild arrival. These are:
  - citizens (`isCitizen`);
  - livestock and pets (`isTame`);
  - by the same mechanism, any non-citizen, non-tame unit whose roaming flag is clear: placed, released, caravan and visitor animals. That is the probe's `other` class; RELS logged LLAMA and CAMEL_1_HUMP as `other` aimers (A-mechanics §2.1).
- So mechanically "the fort's side" is **"every slotted unit that is not a not-yet-released DF wave unit"**. It is not an allegiance.

**The mechanic.**
- The structure (DOCUMENTED, `dfhack-latest/library/xml/df.unit_reaction.xml:2-51`): `world.enemy_status_cache` (bay12 `unit_reaction_handlerst`) holds
  - `slot_used[500]`,
  - a 500×500 `rel_map` of `unit_reaction_type`,
  - `next_slot`.
- Each unit points at its row via `unit.enemy.enemy_status_slot` (`df.unit.xml:3099`, bay12 `reaction_column`).
- The values in use include NONE (−1), STRANGER, WE_ARE_SAME_RACE_WILDERNESS_ANIMALS, PREDATOR_OR_PREY, BENIGN_ANIMAL, DANGEROUS_ANIMAL and SAME_CULTURE.
- What DF writes (MEASURED, CTRL, tool off, `rel_map` sampled every 3,000 t; RELS 14 cell-reps, RELS2b 4, RELS3 4):
  1. **Slots.** DF allocates them lazily. At +100 t only SAME_RACE, SAME_CULTURE and STRANGER exist (RELP, `findings.md:242-245`). Unused cells read NONE (SLOTV, `findings.md:267-269`).
  2. **Fort side toward the arrival: PREDATOR_OR_PREY**, in the fort unit's row toward the arrival.
     - Citizens 159, tame 107, `other` 57 entries (RELS).
     - Coverage: 81 of 138 citizens seen wrote one (59%), and 76 of 85 surface arrivals seen received one (89%) (A-mechanics §11).
     - First seen at a median of 35-85 tiles; entries are cleared again within a few samples (`findings.md:262-263`).
  3. **The arrival toward the fort side: BENIGN_ANIMAL** if the species is BENIGN (662 entries), **else DANGEROUS_ANIMAL** (15). RELS2b: the cougar wrote DANGEROUS toward dwarves (5, 6) (`findings.md:404-409`).
  4. **Surface wild toward surface wild**: almost never (5 of 370; RELS2b one cougar>owl/kestrel pair). **Cavern wild ↔ cavern wild**: yes (38; olm↔crundle 9/7).
  5. **No attacks followed.** RELS had 0 attack and 0 death rows in 14 cell-reps (A-mechanics §11). A PREDATOR_OR_PREY cell is a disposition, not a hunt.
     - Placed hunters did act on DF's own entries over 30k-t cells: STL2 norel LION killed 8 natives; the `findings.md:240-245` RELP note.
- **What "non-wild" means mechanically.**
  - On the aimer's side: `flags2.roaming_wilderness_population_source` is **clear**.
    - The decisive contrast: RELS2 cleared the flag on every arrival and got 1,551 `other>other` entries; RELS2b, same steering without the clear, got 29 wild>wild.
    - Species tokens were irrelevant: a lion as-is, BENIGN, no LP or AMBUSH all received entries (`findings.md:263-264`).
    - Status: MEASURED correlation (4 blocks × 2 reps); mechanism INFERRED.
  - On the target's side: the target needs a population reference (released units are still targets), not the flag.
  - DFHack's `isWildlife` ignores the flag entirely (`dfhack-53.16-r2/library/modules/Units.cpp:601-607` reads `population_idx >= 0` and not fort-controlled/merchant/forest). DFHack-wild and DF-aim-wild therefore disagree exactly on released and placed units.
  - Underground there is a second, unknown rule: flagged cavern natives aim at each other, and HC1-HC4 show it is species-dependent.

**Gaps.**
- The DF writer function is not reverse-engineered. Everything above is observed `rel_map` content.
- No probe logged `isWildlife`, `population_idx`, `civ_id` or `flags4.agitated` beside the class.
- WILD1 (A-mechanics §2, re-sized to n=5 per R12, on region8 per R11) would turn the flag reading from correlation into a test: set the flag back on placed deer.

---

## R3 — "prey mass correlates with increased predator death and injury": confirm or invalidate

**Verdict: PARTLY. Prey mass on its own does not drive harm; two thresholds do.**
1. **Mass alone does not.** Across deer → elk → moose → buffalo (all BENIGN prey, 3.5× to 25× wolf mass), wolf deaths do not rise with prey mass: OR 1.07 per doubling [0.68, 1.68], 11 of 831 wolves. **MEASURED.**
2. **Harm comes from prey that can fight back**, which happens in two ways:
   - **Prey vastly larger than the hunter.**
     - Elephants killed 28% of wolves (125× wolf mass) and 17% of hyenas (83×).
     - They killed 0 of 20 giant hyenas (8×).
   - **Prey that is not BENIGN, whatever its size.**
     - Capybaras (45 kg, about wolf-sized) killed 5 of 5 wolves.
     - Deer made raging or non-BENIGN killed 19 of 72 wolves.
3. **"Fights get longer with prey mass" is not supported** when all the wolf data are pooled: hunter wound events on prey ×1.00 per doubling [0.76, 1.32]. Part 1's PK-only figure (×1.63) does not hold in general.

All analysis code and output are in `DC/data/eco-review/part2/R3-analysis/`:
- `harm.py` parses the TSVs into `harm.json` and `harm.tsv`.
- `fit.py` reuses Part 1's `glm.py` and writes `fit.out`.

### R3.1 What the rig logged: deaths, yes; injuries only as wound events
- **Deaths: one row per incident** (`DC/chronicler/dfhack/scripts/cx-eco.lua:488-497`; DOCUMENTED). Each row carries:
  - victim and killer
  - cause
  - `victim_spawned` and `killer_spawned`
  - dt
- **Never logged: wound state, health samples or HP.**
  - `cx-eco.lua` and `eco-run.py` never read `body.wounds`, `blood_count` or pain.
  - The only `blood_count` write is the one that drains placed corpses (`cx-eco.lua:413`).
- **The `attacks` rows are, however, an injury proxy.** The handler counts eventful `onUnitAttack` by attacker race > defender race and ignores the wound argument (`cx-eco.lua:450-455`). DFHack fires UNIT_ATTACK only in two cases:
  - a strike leaves a fresh wound (`age <= 1`) by that attacker on the defender (`DC/repos/dfhack/library/modules/EventManager.cpp:1124-1131, 1187-1212`);
  - the strike kills (`:1214-1236`).

  The docs agree: "NOT called if blocked, dodged, deflected, or parried" (`DC/repos/dfhack/docs/dev/Lua API.rst:7354-7357`).
- **What `PREY>HUNTER n` therefore counts:** wounding blows the prey's race landed on the hunter's race.
  - This corrects Part 1's reading of attack rows as "strikes / fight length" (A-mechanics §3.3).
  - Caveats: the count is keyed by race (a native of the same race is pooled in), it undercounts because of the `already_done` pair key, and it carries no severity.

### R3.2 Data and method
**Records.** `harm.py` turns 38 TSVs into 787 records, one per (cell-rep, hunter species, prey species). Sources:
- P1, W1L, W1O, T1, L2 (`ECO/20260929-235553/`)
- CAL (both attempts), PK, WB
- GPK, GPKR, GPKW
- FSH2, FVA, REACH ×4
- STL, STL2, LONE, LONE10
- TV, TV2, HC1-3, HCP, HO, HR (`ECO2-*`), HC4 ×4
- SW1, SW2, SW1R, SW2R

**Fields per record:**
- hunters placed
- hunters killed by the placed prey species
- prey→hunter wound events and hunter→prey wound events
- prey killed
- adult masses, from `DC/data/bestiary/creatures.json`

**Attribution.** Of 144 hunter deaths, 134 were by the placed prey. The other 10 were by dwarves, natives, or suffocation.

**Fits:**
- deaths: binomial
- wound events: quasi-Poisson with a log-ticks offset

**"Clean" set:** the relation was written (or the tool was on, in SW) and there was no temperament arm. That gives 667 records and 2,079 hunters.

### R3.3 Results (MEASURED; 1-2 reps per block, 4 for SW1+SW1R and SW2+SW2R)

**Wolves on the BENIGN mass ladder.** Each cell is hunters killed by the prey / wolves placed, with wound events taken in brackets.

| prey (mass, × wolf) | CAL (30k t, adjacent; 2 attempts) | PK (3k t, adjacent, 2 reps) | SW* (30k t, herds 45-60 tiles off, 4+4 reps) | TV/TV2/T1/FVA/L2 controls | total killed (share) | wounds taken / strikes made |
|---|---|---|---|---|---|---|
| DEER 140k (3.5×) | 0/45 (1) | 0/32 (3) | 0/200 (3) | 4/162 (36) | 4/439 (0.9%) | 0.02 |
| ELK 300k (7.5×) | — | 2/32 (27) | — | — | 2/32 (6%) | 0.08 |
| MOOSE 525k (13×) | 0/45 (2) | 2/32 (36) | — | — | 2/77 (3%) | 0.03 |
| WATER_BUFFALO 1M (25×) | 1/45 (10) | 0/32 (3) | 2/200 (25) | 0/6 | 3/283 (1%) | 0.02 |
| ELEPHANT 5M (125×) | 13/45 (106) | — | 56/200 (329) | — | 69/245 (28%) | 0.21 |

**Binomial fits** (hunters killed by prey; odds ratio per doubling):

| set | term | OR [95% CI] | p (LRT) |
|---|---|---|---|
| all clean pairs (667) | log2 prey/hunter mass, adjusted for hunter n, prey n, BENIGN | 1.64 [1.46, 1.84] | <0.001 |
| | prey BENIGN | 0.01 [0.00, 0.02] | <0.001 |
| BENIGN prey without the elephant (602 records, 24 deaths) | log2 prey/hunter mass | **0.92 [0.82, 1.04]** | 0.21 |
| ...surface only (15 deaths) | log2 prey/hunter mass | 1.16 [0.93, 1.44] | 0.16 |
| wolves, deer to buffalo (167 records, 831 wolves, 11 deaths) | log2 prey mass (+ n wolves) | **1.07 [0.68, 1.68]** | 0.78 |
| wolves including the elephant (216 records) | log2 prey mass | 2.46 [2.01, 3.01] | <0.001 |

**Wound events** (quasi-Poisson, rate ratio per doubling):
- **Wounds taken by wolves vs prey mass, elephant included:** 1.63 [0.99, 2.69], p 0.054.
- **BENIGN prey without the elephant:** 0.75 [0.62, 0.92]. Bigger BENIGN prey were engaged less, especially by lone cats (INFERRED).
- **Hunter wound events on prey vs prey mass (wolves):** 1.00 [0.76, 1.32].

**Contrasts that isolate the cause:**
- **SW1, SW2, SW1R and SW2R carry no position confound between prey.**
  - Setup: every cell holds the same 5 wolves with DEER ×6, BUFFALO ×6 and ELEPHANT ×4 at once (`DC/scripts/eco-run.py:809-814`), run in both cell orders.
  - Wolves killed out of 200 exposures each: elephant 56, buffalo 2, deer 0.
  - Wounds taken per strike made: elephant 0.22, buffalo 0.06, deer 0.07.
  - 33 of 40 runs lost at least one wolf to an elephant.
  - Elephant kills by cell position (1 to 5) were flat in both orders: 1.4, 0.9, 1.4, 1.4, 2.0.
- **Relative size, same prey.**
  - Elephants killed 5/30 hyenas (60k, 83×) in CAL.
  - Elephants killed 0/20 GIANT_HYENA (634k, 8×) in GPK, and 4/4 elephants died.
  - GIANT_CROCODILE ×4 against HIPPO (0.23×): 0/16 crocodiles lost, 8/8 hippos killed.
- **Temperament, same or smaller mass.**
  - In the raws, CAPYBARA has no `[BENIGN]`. DEER (`creature_large_temperate.txt`) and ELEPHANT (`creature_large_tropical.txt`) carry it. DOCUMENTED, Python scan.
  - WOLF ×5 against CAPYBARA 45k (1.1×): 5/5 wolves killed; 132 wounds taken against 20 given (W1L, 1 rep; `DC/data/eco-desk/findings.md:81-85`).
  - LION against CAPYBARA: 1/5 lions lost, 125 wounds taken.
  - BAT_GIANT against CRUNDLE (non-BENIGN): 1/4 bats lost.
  - Deer under RAGE, BENIGN off or CRAZED (T1, TV, TV2): **19/72 wolves killed**, against 4/439 for normal deer. The PRONE_TO_RAGE dose-response is at `findings.md:107-110`.
  - Pooled: non-BENIGN prey killed 7/40 hunters (18%). BENIGN prey killed 98/2,039 (4.8%), and 69 of those 98 were elephant kills.
- **Caverns.** TROLL ×5 against GORLAK (BENIGN, 0.2×): 8/10 trolls killed (HC1).
  - Cavern fights are hostile brawls, not predation (`findings.md:113-119`).
  - They are kept out of the surface reading.

**Confounds:**
- **Cell order.** CAL and PK run prey in mass order within one load per rep. Wolf deaths against cell position: Spearman ρ 0.29, p 0.017, which cannot be separated from mass in those blocks.
- **SW exposure.** SW's within-cell contrast is the clean evidence, but DF chooses the targets: wolves spent 55-93% of their strikes on the elephant (`findings.md:542-551`).
- **Start distance.** Hunters started on top of the prey in CAL, PK, TV and W1L.
- **One species dominates.** 68 of 105 clean deaths came from the elephant.
- **Speed.** The elephant is also the slowest prey (sprint 488), so mass and speed cannot be separated for it.

### R3.4 Reading
- **MEASURED.** Predator deaths and wounds are flat over a 7× prey-mass range (deer to buffalo).
  - They jump at the elephant (125×), but only when the hunter is small relative to it; not at the giant hyena's 8×.
  - Non-BENIGN or enraged prey kill hunters at elephant rates while being wolf-sized.
- **INFERRED.** In DF combat, harm is a threshold, not a correlation. It depends on:
  - whether the prey is willing to fight (BENIGN, rage);
  - the prey's size advantage per blow.
- **For the tool** (recommendation only, INFERRED):
  - The 0.05 pack-mass floor (`SWP/scripts/seasonal-wildlife.lua:4210-4217`) already screens wolf-vs-elephant pairings: 5 wolves on an elephant give a share of 0.04.
  - A harm screen should key on two things: prey/hunter mass of about 50-100× or more, **and** non-BENIGN prey (the capybara case).
- **Never measured:**
  - severity of injury, or how it builds up in survivors;
  - prey mass at fixed prey speed;
  - any hunter other than wolves on a mass ladder.

### R3.5 Proposed experiment PMH1: prey-mass ladder at fixed speed, deaths and wounds (n = 5 per arm)

**Setup:**
- **World.** Save region8, world Snospdastrasp "The Last Planets" (R11). Survey a land spot at block start and record it.
- **Load and order.**
  - One fresh load per rep, 5 reps (R12).
  - Arms in a cyclic Latin order: rep *k* starts at arm *k*.
  - About 60k t per load, which stays under the session-length FPS loss (memory fps-load-facts).
  - `cx-load sustain` once per cell.
- **Wipe before every cell (R15).** Vanish every non-citizen unit on the map: wild, cavern, livestock and visitors (`vanish_countdown`, as `cx-eco clear` does, `cx-eco.lua:503-507`).
  - Receipt: a non-citizen unit count of 0 at +10 t, before any placement.
- **Hunter:** WOLF ×5 (40k, sprint 149) in every arm.

**Arms.** All prey are BENIGN and sprint 137-157 except arm 5:

| arm | prey | mass | sprint | role |
|---|---|---|---|---|
| 1 | HARE | 3.5k | 146 | ladder |
| 2 | DEER | 140k | 137 | ladder |
| 3 | GIRAFFE | 1M | 146 | ladder |
| 4 | RHINOCEROS | 3M | 157 | ladder |
| 5 | ELEPHANT | 5M | 488 | known-harm reference (slow) |
| 6 | DEER, `BENIGN` off | 140k | 137 | temperament control at fixed mass |

That is 6 arms × 5 reps = 30 runs.

**Running each cell:**
- **Geometry.** Wolves start 25 tiles from the herd centre. `cx-eco rel WOLF <prey>` at t0.
- **Duration.** 10,000 t per cell. Two reasons:
  - The median hunter death across all logged deaths came at 10.5k t, mostly SW at 45-60 tiles.
  - Adjacent CAL deaths came near 3k t.
- **Receipts:**
  - placed counts
  - relation pairs > 0
  - wolf-to-nearest-prey distance ≥ 20 at t0
  - at least 1 `wound` row in a smoke cell
  - BENIGN-off readback in arm 6

**Logger changes** (desk work, before the rig is free):
1. Make the watch handler `function(att, def, wound)`. When `wound >= 0`, emit `eco wound victim attacker wound_id parts severed artery broken guts nerve`. These come from the wound part flags (`df.unit.xml:1924-1960, 2081, 2092`).
2. Every 1,000 t, and at the end, emit per placed wolf:
   - `#u.body.wounds`
   - `u.body.blood_count / blood_max` (`df.unit.xml:2834-2835`)
   - `counters.pain`, `stunned`, `unconscious` and `winded` (`:2876-2897`)
   - body-part status counts: missing, bone, muscle and nerve (`:1853-1880`)

   Healed wounds drop out of `body.wounds`, so both the events and the samples are needed.

**Analysis:**
- Binomial: wolves killed ~ log2 prey mass over arms 1-4 (100 wolves), with rep as a block.
- Arm 6 against arm 2.
- Negative binomial: wounds received per wolf.
- Severity score: share of wolves with an artery, fracture or severed part, or blood < 50%.

**Power** (INFERRED):
- Deaths alone separate only the elephant arm: about 3-4/25 against 0/25.
- The 100-wolf mass trend and the wound counts carry the test. In SW, wounds per strike were 0.02 for deer against 0.21 for elephants, about ×10.

**Prediction if R3.4 holds:** arms 1-4 flat; arms 5 and 6 high.

---

## R6 — what drives and ends the current v7.0 irruption, and what it tells the player

All of this is DOCUMENTED (code, `SWP/scripts/seasonal-wildlife.lua` on branch v7.0) unless marked otherwise.

- **Switch and defaults.** Opt-in: `irruption = { enabled=false, threshold=1.0, gain=0.02, decay=0.01, duration_days=10, cooldown_days=30 }` (`:471`; config parse `:555-560`).
- **The drive: cavern pressure from your dwarves.** On every groups tick (`GROUPS_CADENCE = 300` ticks, `:3391`), `IRRUPT.tick` (`:6080-6118`) counts living citizens whose z lies in each cavern band (`IRRUPT.citizensInBands`, `:6040-6051`, bands from `CAVE`) and sets `p = p·(1−decay) + gain·citizens` per cavern depth 0-2.
  - At the defaults the steady state is 2× the citizen count.
  - MEASURED (T9b, `STATE.md:3733-3756`, 2 reps per arm): 3 citizens crossed 1.0 on **day 19**, reaching 3.9-4.1 by mid-season. The control stayed at 0.000.
  - The formula predicts about day 4.5 at 3 continuous citizens (INFERRED arithmetic). The gap suggests the citizens were not in the band at every tick, which fits their thirst deaths. The value is unverified.
  - DF's invasion machinery is never touched (`:6034`, "Never touches plotinfo.invasions"). This is consistent with the user's ruling R4/R23 and with E23b/c/d drawing zero invaders (`STATE.md:3826-3845`).
- **The early effect.** From half the threshold the cavern gate's gap is halved (`IRRUPT.gapDays`, `:6073-6079`).
  - The code takes the **maximum pressure over all three caverns** and halves the gap for every cavern (`:6211`, `:6228`). So it is not layer-specific (relevant to R5).
  - MEASURED: never observed. The gate sat at its group cap all season (T9b, `STATE.md:3747-3750`).
- **The trigger.** Once pressure ≥ threshold, the **next DF-drawn cavern group from that depth** that `discoverGroups` lists as fresh is armed (`:6104-6117`), provided the cavern roster admits it (`cfg.allow[key] ~= false`).
  - Arming sets `flags4.agitated_wilderness_creature` on every member. The flag is re-applied on every groups tick because it decays (E29).
  - The cavern's pressure is then reset to 0.
  - Which groups can be armed:
    - It must be a DF-brought, flagged group: `gatedLayer` requires the roaming flag (`:3513`). A tool-placed cavern group can never be armed.
    - Any species qualifies, tribal or not. T9b armed troglodytes, a giant earthworm, a cave crocodile, a giant olm and a giant cave swallow (MEASURED).
    - Only one armed group exists at a time.
- **The end.** `IRRUPT.disarm` (`:6064-6071`) clears the flag in any of these cases:
  - `duration_days` has passed ("duration over");
  - no armed member is alive on the map ("none left on the map");
  - irruptions are switched off;
  - rotation is disabled (`:7050`) or everything is switched off (`:7109`).
  - After a disarm, a `cooldown_days` cooldown blocks the next arming (`:6069`, `:6094`).
  - MEASURED: T9 (pinned pressure) armed 4 groups per rep and stood 3 down at "duration over" (`STATE.md:3660-3672`). T9b armed 3 per rep, each standing down after its 20 days.
- **What the player is told.**
  - **No DF announcement at any stage.** The tool's `announce()` (`:3363-3365`) is used only for "roster applied" (`:3378`).
  - All irruption messages are ledger lines of kind `irruption` (`LEDGER.add`, `:710-723`), shown in the Ledger tab:
    - "armed TOKEN xN from cavern D at pressure P for N days (k flagged); the roster admitted it" (`:6111`);
    - "TOKEN xN arrived at pressure P but the roster blocks it: not armed" (`:6115`);
    - "TOKEN xN stood down (reason; k flag(s) cleared)" (`:6067`).
  - Passive readouts:
    - the `irruption` verb's status line, "irruptions: on threshold … pressure cavern 1 x cavern 2 y … armed: TOKEN xN from cavern D, n day(s) left … cooldown n day(s)" (`:6120-6128`, verb `:7785-7801`);
    - the Live tab's line (`gui/seasonal-wildlife.lua:1001`);
    - the Layers tab rows "irruptions" and "cavern pressure x / y / z" and "AGITATED: TOKEN xN" per cavern (`gui/...:1227-1244`).
  - **Coming**: only the pressure number rising. **Happened**: the "armed" ledger line. **Ended**: the "stood down" line.
  - Nothing reaches DF's announcement log, and nothing warns at the half-threshold gap change.
- **Not in v7.0, for the irruption builder (R5/R10):**
  - no layer-specific gap;
  - no cap lift for animal-people groups;
  - no per-token assignment (CRAZED/RAGE/THIEF ~10%);
  - no "one individual with all tags";
  - no exclusion of tribal cavern dwellers from agitation;
  - no in-game end condition beyond duration, wipe-out or cooldown.

---

## R22 — "depth": column water depth vs tile water level (and two more meanings)

**Headline.**
- DF stores only a per-tile water level, `flow_size`: a 3-bit field holding 0-7.
- DF has no "column depth" field. Column depth exists only where our code counts stacked tiles at level 4/7 or more, and the rig and the tool count them differently.
- "Depth" carries four meanings across the tool and the report:
  - tile level n/7;
  - column depth in levels;
  - z-distance below the surface;
  - cavern layer (`layer_depth` 0-4; raw `UNDERGROUND_DEPTH` 1-5).
- "Deep" adds a fifth: the tool's 'deep' layer, meaning the magma sea and the underworld.

### R22.1 What DF stores (DOCUMENTED)

| concept | where | values | source |
|---|---|---|---|
| Tile water level ("depth" on the wiki) | `tile_designation.flow_size` (bay12 `LIQUID_AMOUNT`, 3 bits) | 0-7 | `GitRepos/df-structures/df.d_basics.xml:10999` |
| Liquid kind | `tile_designation.liquid_type` → `tile_liquid` {Water, Magma} | 1 bit | `df.d_basics.xml:11011, 11036-11039` |
| Other water bits | `water_table` (aquifer), `flow_forbid`, `liquid_static`, `water_stagnant`, `water_salt`; block `has_aquifer`/`check_aquifer`, `sink_level` | flags | `df.d_basics.xml:11013, 11018-11023`; `df.block.xml:12-15, 388` |
| Column water depth | **no field.** df-structures has only ground and river elevation (`df.block.xml:408`; `df.region_midmap.xml:117, 211, 226`) | computed only | DOCUMENTED by absence |
| Cavern layer | `world_underground_region.layer_depth`; DFHack `layer_type`: Surface −1, Cavern1 0, Cavern2 1, Cavern3 2, MagmaSea 3, Underworld 4 | 0-4 | `df.dfhack.xml:638-645`, `df.world.xml:768`, `df.feature.xml:152-153` |
| Raw cavern depth | `UNDERGROUND_DEPTH:min:max` (see R28) | 0-5 | raws, MEASURED with Python |

**What the DF wiki says** (DOCUMENTED; dwarffortresswiki.org Water and Swimmer, fetched 1 Oct):
- "Water has 7 depth levels per tile ... 7 filling the tile completely."
- On stacking: "A lake three Z-levels deep, with each level having 7/7 depth, can be thought of as having 21 levels of depth." This is exactly the user's distinction.
- Thresholds:
  - 3/7 or lower: "will cause suffocation in aquatic creatures".
  - 4/7 and up: dwarves will not path through it, and it trains swimming.
  - 7/7: an unskilled swimmer drowns.
- The tool's tile test `flow_size >= 4` is the wiki's aquatic-safe line.

### R22.2 How our code measures column depth (code)

| counter | rule | caveat |
|---|---|---|
| Rig `cx-eco depth` (`DC/chronicler/dfhack/scripts/cx-eco.lua:86-102, 236-246`) | From the top water tile, counts the **contiguous** run at flow ≥4 (not magma); every tile read | A partial top tile (1-3/7) is not counted: this measures "stacked tiles at 4/7 or more" |
| Tool `ENGINE.deepColumns` (`SWP/scripts/seasonal-wildlife.lua:4866-4890` on `ENGINE.waterTiles` `:4785-4805`) | Counts **distinct z-levels** with outside ocean water at flow ≥4 inside `PLACE.surfaceBand` (surface −12 … +1, `:3883, 3893-3896`), sampling every 2nd x and y | Not contiguous, and a ¼ sample: "0 of 5,374 OCEAN2 columns" and the rig's "36,650 BOATS columns" are not comparable denominators (INFERRED from code) |

MEASURED (DEPTH, 1 rep, `DC/data/experiments/ECO/20260929-235553/DEPTH.tsv:1`): on BOATS, columns of 1/2/3/4 levels number 14,846 / 9,759 / 8,564 / 3,481. There are none of 5 or more.

### R22.3 Every ambiguous use

**Terms used in the "proposed" column:**
- **tile level n/7** (`flow_size`);
- **column depth (levels)**: stacked tiles at ≥4/7;
- **z below surface**;
- **cavern layer 1-3**, 1-based for display;
- **magma/underworld layer**.

| # | file:line | text | actual meaning | problem | proposed |
|---|---|---|---|---|---|
| 1 | `seasonal-wildlife.lua:3803` (CAVE.survey) | `if d.flow_size >= 4` water, else `r.open` | tile level | A 1-3/7 water tile counts as open floor (matters for R28/R44 cavern placement) | "tile level ≥4/7" |
| 2 | `:3867-3869, 3928-3929, 4383` ("WATER tile ... depth 4 or more"), `:4392` | water test `flow_size >= 4` | tile level | "depth 4" reads as column depth | "water level ≥4/7" |
| 3 | `:4014`, `:4641` (player-facing) | "no free water tile at depth 4 or more" | tile level | A player reads it as 4 z-levels deep | "no free water tile at level 4/7 or more" |
| 4 | `:5474` "deep (flow 4+)"; `:6837` "a deep-water tile (flow 4+)" | `V7.seaAt`, `SCAV.wet` | tile level | "deep" means tile level here but column ≥3 in `deepColumns` | "full tile (≥4/7)"; keep "deep" for columns |
| 5 | `:5550` "a busy or shallow tile" | sponge seeding | tile level <4/7 | "shallow" elsewhere means 1-2 levels (content.html:42) | "a low-water tile (<4/7)" |
| 6 | `:87-88`, `:456` `deep_levels=3`, `:4866-4890, 5088-5091, 5357-5371`, `:7921` "deep water: N/M ocean column(s) at or past 3 levels" | `deepColumns` | column depth | Non-contiguous, ¼ sample | "column depth ≥3 levels"; rename `deep_levels` → `column_levels` |
| 7 | `:111`, `:4895` "fortress oceans are 1-4 levels deep"; `:4899` "on a shallow map" | pelagic weight | column depth | right sense, unlabelled | "column depth 1-4 levels" |
| 8 | `:4501` "2. DEPTH: water at flow 4 or more within `NEAR` levels of the land-entry surface"; `:4507` "OCEAN dormant on depth, CTRL dormant on depth" | `WET.survey` | **z below surface** combined with tile level | "dormant on depth" means the water is too far down (OCEAN: 39 levels), not too shallow | "z-distance to water" |
| 9 | `:878-890, 902, 2788-2793, 3509-3517, 3776-3779` ("cave 8 depth 0 … magma sea (depth 3)") | `caveDepth` = `layer_depth` | cavern layer, 0-based | Shares the word with water; 0-based while the raws are 1-based | "cavern layer", shown 1-based |
| 10 | `:3848` `'depth %d (cave %d)'`, `:4008` "cavern depth %d", `:4730`, `:6249` key `cavern%d:`, `:7669-7708` `place … cavern [depth]` (0-based) **vs** `:6111, 6124-6125` "from cavern %d" (d+1) and `gui/seasonal-wildlife.lua:1236-1246` "Cavern %d" (d+1) | cavern index | cavern layer | **The same cavern prints as "depth 0", `cavern0:` and "Cavern 1"** | 1-based everywhere the player sees it |
| 11 | `:356` LAYERS 'deep'; `:7075` "Layer: deep"; `gui/...:203, 214, 261, 1257-1281`; `seasonal-wildlife-web.lua:230-239`; `:7321, 7587` "deep %d" | 'deep' layer | magma sea + underworld | Printed beside "deep water" (`:7921`) in the same `build` output | "magma/underworld layer" |
| 12 | `:751, 782` `UNDO.depth`, "fifty deep"; `:423` `deepcopy`; `gui/...:137-140` | ring size, recursion | not water | grep noise only | leave |
| 13 | `DC/scripts/eco-report/content.html:42` "Fortress water is shallow … no column 3 levels deep"; `:71` "1–2 levels deep"; `:72` "91% one level deep"; `:344` "Depth by fort" | DEPTH and v7.0 survey | column depth | "shallow" invites the wiki's ≤3/7 (suffocation) reading | "Fortress oceans are 1-2 levels (column depth)" |
| 14 | `content.html:345` "Big fish don't suffer in shallow water"; doc rev326 `:265` | S8O | column depth | "suffer" invites the tile-level (suffocation) reading | "in 1-2-level columns" |
| 15 | `content.html:340`, doc `:266` "Depth can't sort species, since the raws carry no depth token"; doc `:17` | water habitat | column depth | `UNDERGROUND_DEPTH` **is** a raw depth token (cavern), and doc `:323` uses it | "the raws carry no water-depth token" |
| 16 | `content.html:269` "0 of 5,374 OCEAN2 columns 3 or more levels deep"; doc `:773, 834, 882` | deepColumns | column depth | ¼-sample denominator, not comparable with DEPTH | "sampled columns" |
| 17 | `content.html:270` "A deep layer delivered demons"; doc `:334, 775` | 'deep' layer | magma/underworld | sits next to the deep-water item at `:269` | "The magma/underworld layer delivered demons" |
| 18 | `content.html:291` "DF's natives (4–5 per depth)"; doc `:241, 542, 832` "each cavern depth"; doc `:571, 585` | cavern | cavern layer | same word as water depth | "per cavern layer" |
| 19 | doc `:323` "UNDERGROUND_DEPTH (… at depths 1 / 2 / 3)" | raw scale | raw cavern depth, 1-based | the tool's `caveDepth` for the same caverns is 0/1/2 | state the offset: raw 1 = `layer_depth` 0 |

("doc" = `DC/data/eco-report/eco-report-doc-rev326.md`.)

**Fix (desk work, no rig).**
- Terms:
  - "column depth (levels)" for stacked tiles at ≥4/7;
  - "water level n/7" for `flow_size`;
  - "cavern layer 1-3" and "magma/underworld layer" underground, never "depth" or "deep" there.
- Code:
  - rename `water.deep_levels` and the 'deep' layer label;
  - make `deepColumns` contiguous and full-resolution, or say that it samples;
  - print caverns 1-based in `CAVE.describe`, the `cavernN:` keys and `place`.
- Labels:
  - DOCUMENTED: df-structures lines, the wiki quotes, the `layer_type` enum.
  - MEASURED: DEPTH histogram (1 rep).
  - INFERRED: the ¼-sample comparability.

---

## R24 — EXTINCT creatures: what the two workshop mods add, what tags the vanilla extinct creatures lack, and how the tool should handle them

**Headline.**
- **Neither mod touches ecology tags.** Both restore natural attacks (bite, gore, scratch, tail) to the 100 extinct *animal people*. 3755752944 also gives the Mosasaurus man a head, mouth and teeth.
  - In the 53.16 raws on the rig, 96 of the 100 extinct animal people already re-apply every natural weapon of their root animal. The other 4 still lose one.
- **The gaps that matter to the tool are in the 100 plain extinct *animals*:**
  - All 16 extinct land LARGE_PREDATORs carry FREQUENCY 50. Vanilla real-animal land apexes carry 2-5.
  - 17 large herbivorous dinosaurs (and Glyptodon) lack STANDARD_GRAZER.
  - A few predators are misfiled.
- **Recommendation: both, scoped.** The tool's own handling is the default:
  - a curated role/guild override;
  - an apex FREQUENCY write through cfg.odds;
  - a few BENIGN/LARGE_PREDATOR writes through `V7.flag`.

  Players may add the attack mods as an option. Never write GRAZER or BIOME at run time.

### R24.1 What the two mods add (DOCUMENTED)

Source: the Steam Web API `GetPublishedFileDetails` and the page HTML, fetched 1 Oct. WebFetch returned HTTP 429.

| id | title | posted / updated | size | what it changes |
|---|---|---|---|---|
| 3753912171 | "Extinct Intelligent Creature Attacks" | 28 Jun 2026 | 138.7 KB | "Adds bite, gore, scratch, and other such attacks to vanilla extinct intelligent creatures" |
| 3755752944 | "Eugene's Dino Bite: Extinct Animal-People Combat Fix" | 1 Jul / 11 Jul 2026 | 1.96 MB | "Restores missing natural combat attacks to all 100 extinct animal-people … (v53.15+)", e.g. Carnotaurus, Ankylosaurus, Spinosaurus, Anomalocaris men: claws/talons, tail slaps, beak bites, horn/tusk gores, pincer snaps. Also the "Mosasaurus Maw Patch (v53.15.1)", which appends a head, mouth and teeth to the legless Mosasaurus humanoids. "Safe to enable on new world generation." |

- **No ecology tokens.** Neither description mentions BIOME, FREQUENCY, CLUSTER_NUMBER, POPULATION_NUMBER, BENIGN, LARGE_PREDATOR or a diet token.
- **Mod files not inspected.** They are not installed (the rig's `mods/` holds 243 other folders), and the API gives no `file_url`. So "attacks only" is INFERRED from the descriptions.

### R24.2 The mechanism the mods patch (DOCUMENTED raws; MEASURED by a static Python parse)

**How the ANIMAL_PERSON variation works.** It is defined in `vanilla_creatures/objects/c_variation_default.txt:14`:
- It strips `CLUSTER_NUMBER` and `ATTACK` (`:49-50`).
- It adds `SAVAGE` (`:184`) and `CHANGE_FREQUENCY_PERC:10` (`:187`).
- It has a `_LEGLESS` twin (`:205`).

Each animal person then re-adds its attacks by hand.

**Comparison: root animal's attack body-part categories vs its animal person's** (feet ignored; the rig is on 53.16, the mods target 53.15; script `DC/data/eco-review/part2/R24-analysis/aplost.py`):
- **Extinct: 4 of 100 lose a root weapon.**
  - CAMBRIAN_ANOMALOCARIS_MAN loses its pincer.
  - CENOZOIC_ENTELODON_MAN loses its head bite and hooves.
  - DEVONIAN_DUNKLEOSTEUS_MAN loses its tail.
  - PERMIAN_HELICOPRION_MAN loses its tail.
- **Vanilla (non-extinct): 11 of 177 lose one.** Examples: DEER_MAN and MOOSE MAN lose their horns and hooves.

**Why it matters little to the tool.** v7.0 never reads ATTACK, and animal people are already savage-only and down-weighted (R13/R26).

### R24.3 Tags the plain extinct animals lack (MEASURED)

Source: `DC/data/bestiary/creatures.json`, built by `DC/scripts/bestiary/build_bestiary.py:479-481` from `vanilla_creatures_extinct/objects/*.txt`. The 200 extinct entries are 100 animals in 10 period files plus 100 animal people.

| token (share carrying it) | vanilla wild, natural (227) | extinct (100) | reading |
|---|---|---|---|
| BIOME, POPULATION_NUMBER, PREFSTRING | 100% | 100% | no gap |
| SAVAGE | 7% | 99% (only CRETACEOUS_CARNOTAURUS lacks it) | by design: extinct = savage biomes |
| explicit FREQUENCY | 34% | 9% (91 at the default 50) | see gap 1 |
| CLUSTER_NUMBER | 72% | 38% | mostly solitary predators and vermin; 23 of 25 large land herbivores have it |
| LARGE_ROAMING | 100% | 83% | the 17 without it are all vermin (Hallucigenia, Meganeura, Archaeopteryx…): correct |
| BENIGN / LARGE_PREDATOR / CARNIVORE | 61 / 18 / 15% | 59 / 28 / 35% | same pattern |
| UNDERGROUND_DEPTH | 14% | 0% | no cavern extinct species (consistent with R28) |

**Gap 1: apex FREQUENCY.**
- All 16 extinct land LARGE_PREDATORs sit at 50: T. rex, Allosaurus, Smilodon, Utahraptor, Velociraptor, Deinonychus, Megalania, Kelenken, Andrewsarchus, Thylacine, Afrovenator, Carnotaurus, Ceratosaurus, Dilophosaurus, Torvosaurus, Anteosaurus.
  - Spot-checked: `CRETACEOUS_TYRANNOSAURUS` carries LARGE_PREDATOR and no FREQUENCY token.
- Vanilla real-animal apexes: grizzly and polar bear 2; tiger, lion, wolf, cougar, jaguar, leopard, cheetah, hyena, dingo and black bear 5.
- DF draws in proportion to FREQUENCY (wiki "Extinction"), so on a savage map an extinct apex is drawn about 10-25× as often as a lion. INFERRED from that rule.

**Gap 2: no STANDARD_GRAZER on 17 large herbivorous dinosaurs and Glyptodon.**
- The species: Triceratops, Kosmoceratops, Iguanodon, Parasaurolophus, Tsintaosaurus, Ankylosaurus, Nodosaurus, Stegosaurus, Kentrosaurus, Brachiosaurus, Brontosaurus, Diplodocus, Amargasaurus, Therizinosaurus, Suzhousaurus, Nothronychus, Glyptodon.
- Spot-checked:
  - ELEPHANT and CENOZOIC_MAMMOTH_WOOLLY carry STANDARD_GRAZER.
  - JURASSIC_STEGOSAURUS does not.
- The tool's GZ guild needs caste GRAZER (`seasonal-wildlife.lua:1385`), so these files land in land prey (PL).

**Gap 3: misfiled predators** (raws MEASURED; the ecological judgement is INFERRED):
- CENOZOIC_TITANOBOA (933 kg) has FREQUENCY:30, CARNIVORE and no LP, so it files as a mesocarnivore. The 100 kg ANACONDA is LP and files as apex.
- PERMIAN_DIMETRODON is AMPHIBIOUS with a river biome, so it files as a water apex.
- DEVONIAN_TIKTAALIK is 47 kg and LP, so it files as a water apex.
- TRIASSIC_EORAPTOR is BENIGN with no diet token, so it files as prey.

### R24.4 How v7.0 handles extinct creatures today (DOCUMENTED, code)

- **No extinct-specific code.** No REAL_WORLD_EXTINCT or period class appears. Every `extinct` hit is the regional-entry flag `pop.flags.extinct` (e.g. `:2395`, `:3622`). No extinct id is in `MODEL.ROLE` (`:1198-1204`).
- **Presence is decided by worldgen.**
  - `buildPool` (`:1746`) uses only the embark's regional populations. Whether those include extinct species depends on the world setting "Real world extinct creatures" plus SAVAGE (wiki World_generation).
  - The install's `region2-world_gen_param.txt` reads `[REAL_WORLD_EXTINCT:UNTAMED_WILDS]`.
  - **Region8's value is unread** and needs the rig or its saved world_gen_param.
- **Classification uses generic tokens:**
  - role = CARNIVORE/BONECARN/LARGE_PREDATOR/AMBUSHPREDATOR (`:1204, 1342-1347`);
  - guild = `MODEL.guild` (`:1375-1385`);
  - armed = not wholly BENIGN (`:1298`);
  - group = the midpoint of cluster_number (`:1287`).

  So every gap in R24.3 flows straight into roster slots and arming.
- **Classification is cached once per world** (`CACHE.class`, `:1273, 1314`). A runtime raw write must land before the first `classify` call, or the cache must be cleared.
- **The levers already exist:**
  - `V7.flag`, with undo via `V7.rec` (`:6421-6435`);
  - `CURIOUS.apply`, which already clears BENIGN on curated predators (`:6389-6397`);
  - `cr.frequency` writes (`:2979`, `:2996-3013`, builder `:5050-5058, 5177`);
  - `cr.cluster_number` writes (`:3677-3678`).

### R24.5 Proposal: both, scoped (INFERRED design)

**(a) The tool is the default path.** It needs no new world, and it covers the plain animals, which the mods never touch.

| group (representatives) | change | via | why |
|---|---|---|---|
| 16 extinct land apexes (T. rex, Allosaurus, Smilodon, raptors…) | effective FREQUENCY 5 (T. rex / Smilodon 2-5, like grizzly/tiger) for DF's own draw; on a built roster the builder's ladder already overrides | `cr.frequency` via cfg.odds (snapshot + restore), only while the tool is enabled | 50 vs 2-5 (gap 1) |
| 17 grazing dinosaurs + Glyptodon | guild GZ **in the tool's model only** (a curated `MODEL.GUILD_OVERRIDE` beside `MODEL.ROLE`); do **not** write GRAZER | model table | a GRAZER raw write could make tamed or pastured dinosaurs need pasture and starve (INFERRED risk); the guild only steers slots |
| CENOZOIC_TITANOBOA | LARGE_PREDATOR on; role apex | `V7.flag` + model | 933 kg constrictor vs LP anaconda |
| PERMIAN_DIMETRODON | habitat override land, guild AL | `cfg.habitat_override` (`:1191-1192`) | AMPHIBIOUS puts a land apex in water slots |
| DEVONIAN_TIKTAALIK | guild MW (meso); raw untouched | model table | a 47 kg "water apex" |
| TRIASSIC_EORAPTOR | role predator (ML); clear BENIGN while ecology runs | `MODEL.ROLE` + the `CURIOUS.apply` path | a small carnivore filed as prey |
| theropod packs (Deinonychus, Velociraptor, Utahraptor, cluster 3-5) | none | — | already pack-sized and LP |
| BIOME / SAVAGE / POPULATION_NUMBER | **no runtime write** | — | worldgen-time only: a write cannot add a species to a region's populations (`:1746`) |
| 4 animal people missing a weapon | leave to the mods | — | the tool never reads ATTACK |

**(b) The mods are optional.**
- A USAGE note: "for fights with extinct animal people, players may add workshop 3755752944 (all 100, plus the Mosasaurus head fix); 3753912171 is an earlier, smaller equivalent: use one of the two."
- Both need a new world, which conflicts with R11 (region8). That is a second reason the tool path is the default.
- The tool's `animalRoot` scan already reads `data/installed_mods` and `mods` (`:1241`), so modded raws are picked up (code only).

**Verification when experiments resume** (n=5, region8):
1. Read region8's REAL_WORLD_EXTINCT and whether any extinct regional entries exist on the embark. If there are none, every row above is inert there, and the test needs a savage-extinct embark.
2. Then compare FREQUENCY 5 against 50 on one extinct apex, with arrival share over a short season as the readout.

---

## R28 — UNDERGROUND_DEPTH: how depth maps to layers, every species by depth, and what the tool does with it

**Headline.**
- Layer 1 is not "only RAT_LARGE and MOLE_DOG_NAKED". Those two are the only species confined to layer 1 (depth 1:1). The raws make **37 species eligible for layer 1**: 29 non-vermin and non-lava, 7 vermin, and IMP_FIRE in magma. Figure 15a is unsorted and draws each bar at its maximum, which hides this.
- MAGMA_CRAB is `UNDERGROUND_DEPTH:3:5` with `BIOME:SUBTERRANEAN_LAVA` (`creature_next_underground.txt:451-452`), so it is eligible for cavern 3, the magma sea and the underworld. On CTRL it was measured in the magma sea (cave 34, z21), not the underworld.
- The v7.0 tool never reads UNDERGROUND_DEPTH. It takes depth from each population entry's `cave_id`, then `world_underground_region.layer_depth`: 0-2 is `cavern`, 3-4 is `deep`. DF's own waves cannot be put on the wrong layer this way. Two gaps exist, both INFERRED from code:
  - The `place` verb sends a `deep` entry, such as a magma crab, to the **surface**.
  - A cavern entry of a lava species is placed on a dry floor.

### R28.1 How depth maps to layers (DOCUMENTED)

- **The raw token.** `UNDERGROUND_DEPTH:min:max` (wiki, Creature_token, `UNDERGROUND_DEPTH` row: https://dwarffortresswiki.org/index.php/Creature_token):
  - "Numbers can be from 0 to 5."
  - "0 is actually 'above ground' and can be used if the creature is to appear both above and below ground."
  - "Values from 1-3 are the respective cavern levels, 4 is the magma sea and 5 is the HFS."
  - "Demons use only 5:5."
  - Flying 5:5 creatures join the initial HFS wave; without FLIER they "only spawn from the map edges".
  - Civilizations export only depth-1 underground plants and animals.
- **The DF structures.** `world_underground_region` (`GitRepos/df-structures/df.region.xml:427-429`) has three fields:
  - `layer_depth` (original name `depth_level`), commented "0-2 caves, 3 magma sea, 4 hell".
  - `layer_depth_p1a`/`_p1b` (original names `pop_min_depth`/`pop_max_depth`), commented "+1".
  - `creature_raw.underground_layer_min/max` (original `min_depth`/`max_depth`, `df.creature.xml:1537-1538`) holds the raw numbers.
  - So **raw depth = layer_depth + 1**: cavern 1 ↔ layer_depth 0, magma sea ↔ 3, underworld ↔ 4. DOCUMENTED.
- **Matching.** A region's population draws species whose `[min, max]` contains its pop depth and whose BIOME is the matching SUBTERRANEAN_* type: CHASM is land, WATER is cavern pools and lakes, LAVA is magma (Cavern page: "Chasm, water, and lava mean land, water (pool), and magma (pipes) respectively").
  - The wiki's per-level table (https://dwarffortresswiki.org/index.php/Cavern, ==Wildlife==, "Level 1-4") agrees with this rule species for species. Examples: "Large rat" and "Naked mole dog" are Level 1 only; "Fire imp" is Levels 1-4; "Magma crab" is Levels 3-4.
  - The rule itself is INFERRED from the field names plus that agreement.
- **Alignment does not gate caverns.** "alignment plays no role ... Good creatures like the gorlak, evil creatures like the troll ... can be found in any cavern" (Cavern, ==Wildlife==).
- **Arrival.** Cavern units arrive through each layer's open map edges (Cavern intro). MEASURED: zeroing cavern entries does not stop cavern waves (T7, STATE addendum 51; `seasonal-wildlife.lua:2875-2884`).

### R28.2 Is layer 1 really only RAT_LARGE and MOLE_DOG_NAKED?

**No.** Source: a Python parse of the 53.16 vanilla raws with the eco-desk resolver (`data/eco-desk/census.py`, so COPY_TAGS_FROM and variations are applied). The script is `DC/data/eco-review/part2/R28-analysis/ud.py`, with its output in `ud.json`.

- **What the parse found.** 67 creatures carry UNDERGROUND_DEPTH: all vanilla, and **none of the 200 extinct creatures**. The span counts match figure 15a exactly: 1:2 25, 2:3 14, 3:3 11, 1:3 9, 1:1 2, 3:4 2, 0:4 1, 2:2 1, 2:4 1, 3:5 1. MEASURED.
- **What "only depth 1" means.** Only RAT_LARGE and MOLE_DOG_NAKED have **max = 1**, so they are the only species confined to layer 1.
- **Eligibility per layer** (min ≤ d ≤ max):

| layer | eligible species | of which non-vermin, non-lava | vermin | lava-only biome (lives only where magma is) |
|---|---|---|---|---|
| cavern 1 (d1) | 37 | 29 | 7 | IMP_FIRE |
| cavern 2 (d2) | 51 | 41 | 9 | IMP_FIRE, SNAKE_FIRE |
| cavern 3 (d3) | 39 | 32 | 3 | IMP_FIRE, SNAKE_FIRE, ELEMENTMAN_FIRE, ELEMENTMAN_MAGMA, MAGMA_CRAB |
| magma sea (d4) | 5 | 0 | 1 | the same five |
| underworld (d5) | 1 (+ generated DEMON_*, 5:5) | 0 | 0 | MAGMA_CRAB |

- **Layer-1 non-vermin species (29):**
  - MOLE_DOG_NAKED, RAT_LARGE
  - BAT_GIANT, BAT_MAN, BIRD_SWALLOW_CAVE_GIANT, BLIND_CAVE_BEAR, CAVE_FISH_MAN, CAVE_SWALLOW_MAN, CROCODILE_CAVE, DRALTHA, DRUNIAN, GIANT_EARTHWORM, HELMET_SNAKE, MOLE_GIANT, OLM_GIANT, OLM_MAN, POND_GRABBER, RAT_GIANT, TOAD_GIANT_CAVE, TROGLODYTE
  - AMPHIBIAN_MAN, ANT_MAN, ELK_BIRD, GORLAK, GREMLIN, REPTILE_MAN, `RODENT MAN` (the vanilla id contains a space, `creature_subterranean.txt:2677`), SERPENT_MAN, TROLL
- **Why the figure misleads.** It plots `form='range'` with `y='depth_max'`, and its rows come out in resolver dict order (`scripts/eco-report/raws_report.py:469-473`; `data/eco-report/raws.json` rows begin FLOATING_GUTS, DRUNIAN, CREEPING_EYE...). A reader scanning for bars at 1 sees only the two 1:1 species.
- **Fix to the figure.** Sort the rows on `(depth_min, depth_max, id)`: `rows15a.sort(key=lambda x: (x['depth_min'], x['depth_max'], x['id']))` before `fig(id='15a', ...)`. Draw the bar from min to max, and retitle it "37 species can live in cavern 1, 51 in cavern 2, 39 in cavern 3; 2 live only in cavern 1". This is a desk recommendation: the report source has not been edited.

### R28.3 Why MAGMA_CRAB is depth 5

- **The raw.** `[BIOME:SUBTERRANEAN_LAVA][UNDERGROUND_DEPTH:3:5][FREQUENCY:100]` plus `[FIREIMMUNE][MAGMA_VISION][IF_EXISTS_SET_HEATDAM_POINT:13000]` (`vanilla_creatures/objects/creature_next_underground.txt:442-502`). DOCUMENTED.
- **What the 5 means.** Max 5 only makes the underworld a legal region. In a cavern layer or the HFS it still needs magma (LAVA biome).
- **Where it actually lives.**
  - The wiki lists it at Levels 3-4 and on the Magma sea page (https://dwarffortresswiki.org/index.php/Magma_sea, ==Wildlife==).
  - MEASURED on CTRL (1 fort): magma crabs in **cave 34 = magma sea**, z21. The underworld, cave 43, held DEMON_10/13 at z5-8 (STATE.md:1928-1932).
  - The DF-read raw field agrees: `underground_layer 3..5` (STATE.md:1998).
- **Why the figure shows "layer 5".** The figure draws each species at its maximum. Bay 12's reason for 5 rather than 4 is not documented; INFERRED, it lets crabs live in the HFS magma.

### R28.4 Fiery and magma creatures: can the tool misplace them?

There are six fiery species: IMP_FIRE 0:4, SNAKE_FIRE 2:4 (vermin), ELEMENTMAN_FIRE 3:4, ELEMENTMAN_MAGMA 3:4 and MAGMA_CRAB 3:5. All are LAVA-only and FIREIMMUNE. CAVE_DRAGON 3:3 is a CHASM species with FIREIMMUNE_SUPER, so it is correctly a cavern-3 creature.

- **The engine maps layers by the entry's region, never by the raw** (code, DOCUMENTED):
  - `layerOf(pop)` (`seasonal-wildlife.lua:900-905`) and `WILD.layerOf(u)` (`:2790-2795`) return `cavern` iff `CACHE.caveDepth(cave_id) <= 2`, else `deep`. `caveDepth` reads `world_data.underground_regions[cave_id].layer_depth` (`:891-899`).
  - `gatedLayer` (`:3511-3518`) tracks only depth 0-2; the magma sea and the underworld are "never tracked".
  - `ecoRealm` (`:4034-4039`) returns nil for `deep`, so no relation is written there.
  - `CAVE.survey` drops the magma-sea band and numbers bands 0-2 (`:3765-3779`).
  - IRRUPT works on `DEPTHS = {0,1,2}` only (`:6038`).
  - grep finds no `UNDERGROUND_DEPTH`, `underground_layer` or `SUBTERRANEAN_LAVA` anywhere in v7.0. So a DF-drawn wave is never re-layered, and depth-4/5 units are never managed. That matches R60 for demons: `layers.deep` steers only the frequency of natural deep species (`:887-890`, `:3006-3012`).
- **Gap 1: the `place` verb puts a deep entry on the surface** (INFERRED from code, not run).
  - The `place` verb (`:7694-7716`) picks the largest-quantity Animal entry of the token. With no layer argument, or with `deep`, a magma crab's or fire man's entry is `deep`.
  - `PLACE.fromEntry` (`:4003-4011`) only builds a band for `layer == 'cavern'`. Otherwise it uses the surface water band or `PLACE.tiles(false, …, nil)`, whose default band is the whole map with `subterranean = false` (`:3903`), so the unit lands on the surface.
  - Fix: refuse `deep` in `PLACE.fromEntry`, or place it only on a magma-adjacent tile of its own band.
  - No automatic job reaches this path. STOCK.run filters `layerOf(pop) == 'cavern'` (`:4700-4732`), and ENGINE draws only water feature entries.
- **Gap 2: a lava species in a cavern entry lands on dry floor** (INFERRED from code and the wiki).
  - DF itself puts fire imps in caverns 1-3 and fire men, magma men and crabs in cavern 3 (wiki table). Those entries are `cavern`, depth ≤ 2.
  - `PLACE.fromEntry` places them on any free walkable floor in the band, and the ground search "never picks magma" (`:266`, `:4379`).
  - A placed IMP_FIRE or MAGMA_CRAB therefore starts away from magma pools. The wiki warns that crab spit "may hit some cave moss and set it alight, causing a cavern-wide fire" (Magma_crab page).
  - Fix: for creatures whose only biome is SUBTERRANEAN_LAVA, pick a tile adjacent to magma (`flow_size > 0 and liquid_type`) in the band, or skip them.
- **Gap 3: the deep lever's FREQUENCY write is shared.** FREQUENCY is per raw and shared across layers (comment `:3000-3005`). So `layers.deep` odds or holds on IMP_FIRE or SNAKE_FIRE also change their cavern-layer waves. DOCUMENTED by code; the size of the effect is not measured.
- **The builder (offline, `data/eco-desk/v2/guilds/roster2.py:172-186`) is clean.** Cavern layers require CHASM or WATER and `lo <= L <= hi` (`cav_mode='range'`), and LAVA species go to `deep`. So the roster never seats a fiery species on cavern 1-3. DOCUMENTED (code).

### R28.5 Could the tool raise layer-1 diversity?

- **Limits today.**
  - The tool places only from population entries the region already holds (`PLACE.fromEntry` needs `pent`, banded by `pent.population.cave_id`).
  - Its cavern lever is FREQUENCY, because DF's cavern spawning reads no entry the tool can reach (STATE addendum 51).
  - So it can tilt odds toward eligible species DF already populated in cavern 1. It cannot add a species DF did not give the region.
- **Option (INFERRED feasible; untested underground).** Place a layer-1-eligible species with a **borrowed population ref** of that layer, as `cx-eco spawn` already does on the surface (`chronicler/dfhack/scripts/cx-eco.lua:343-351`). Gate it on these conditions:
  - `craw.underground_layer_min <= 1 <= underground_layer_max`;
  - a CHASM or WATER biome;
  - not LAVA-only.
- **The pool.** Eligible non-civ animals: BLIND_CAVE_BEAR, CROCODILE_CAVE, DRALTHA, DRUNIAN, ELK_BIRD, GIANT_EARTHWORM, HELMET_SNAKE, MOLE_GIANT, OLM_GIANT, POND_GRABBER, RAT_GIANT, TOAD_GIANT_CAVE, BAT_GIANT, BIRD_SWALLOW_CAVE_GIANT, plus TROGLODYTE, GREMLIN, MOLE_DOG_NAKED and RAT_LARGE.
- **Costs.** A departure refunds the borrowed entry. Before relying on this, check that it does not collide with R44's 5-group cavern cap.

### R28.6 Every vanilla species with UNDERGROUND_DEPTH, sorted by min, then max, then id (MEASURED from raws, 67)

Biome: CH = SUBTERRANEAN_CHASM, WA = SUBTERRANEAN_WATER, LAVA = SUBTERRANEAN_LAVA, NF = NOT_FREEZING. FREQ "(50)" is the raw default. LP = LARGE_PREDATOR; HEROES = LOCAL_POPS_PRODUCE_HEROES. c1-c3 = cavern layers.

| depth | species | where (raw) | biome | FREQ | tags |
|---|---|---|---|---|---|
| 0:4 | IMP_FIRE | surface, c1, c2, c3, magma sea | LAVA | 20 | FIREIMMUNE, LP |
| 1:1 | MOLE_DOG_NAKED | c1 | CH | 100 |  |
| 1:1 | RAT_LARGE | c1 | CH | 100 |  |
| 1:2 | BAT | c1, c2 | NF/CH | 100 | FLIER, vermin |
| 1:2 | BAT_GIANT | c1, c2 | CH | (50) | LP, FLIER |
| 1:2 | BAT_MAN | c1, c2 | NF/CH | 100 | FLIER, HEROES |
| 1:2 | BIRD_SWALLOW_CAVE | c1, c2 | CH | 100 | FLIER, vermin |
| 1:2 | BIRD_SWALLOW_CAVE_GIANT | c1, c2 | CH | (50) | FLIER |
| 1:2 | BLIND_CAVE_BEAR | c1, c2 | CH | 10 | LP |
| 1:2 | CAP_HOPPER | c1, c2 | WA | 100 | AMPHIB, vermin |
| 1:2 | CAVE_FISH_MAN | c1, c2 | WA | (50) | AMPHIB, HEROES |
| 1:2 | CAVE_SWALLOW_MAN | c1, c2 | CH | 100 | FLIER, HEROES |
| 1:2 | CROCODILE_CAVE | c1, c2 | WA | (50) | LP, AMPHIB |
| 1:2 | DRALTHA | c1, c2 | CH | (50) |  |
| 1:2 | DRUNIAN | c1, c2 | CH | 10 |  |
| 1:2 | FISH_CAVE | c1, c2 | WA | (50) | AQUATIC, vermin |
| 1:2 | GIANT_EARTHWORM | c1, c2 | CH | 20 |  |
| 1:2 | HELMET_SNAKE | c1, c2 | CH | 30 | LP |
| 1:2 | LOBSTER_CAVE | c1, c2 | WA | (50) | AQUATIC, vermin |
| 1:2 | MOLE_GIANT | c1, c2 | CH | 100 |  |
| 1:2 | OLM | c1, c2 | WA | 100 | AMPHIB, vermin |
| 1:2 | OLM_GIANT | c1, c2 | WA | (50) | LP, AMPHIB |
| 1:2 | OLM_MAN | c1, c2 | WA | 100 | AMPHIB, HEROES |
| 1:2 | POND_GRABBER | c1, c2 | WA | (50) | LP, AQUATIC |
| 1:2 | RAT_GIANT | c1, c2 | CH | 100 |  |
| 1:2 | SPIDER_CAVE | c1, c2 | CH/WA | (50) | vermin |
| 1:2 | TOAD_GIANT_CAVE | c1, c2 | WA | (50) | LP, AMPHIB |
| 1:2 | TROGLODYTE | c1, c2 | CH | 100 | LP |
| 1:3 | AMPHIBIAN_MAN | c1, c2, c3 | WA | 100 | LP, AMPHIB |
| 1:3 | ANT_MAN | c1, c2, c3 | CH | 100 | LP, FLIER |
| 1:3 | ELK_BIRD | c1, c2, c3 | CH | (50) |  |
| 1:3 | GORLAK | c1, c2, c3 | CH | 25 | GOOD, HEROES |
| 1:3 | GREMLIN | c1, c2, c3 | CH | (50) |  |
| 1:3 | REPTILE_MAN | c1, c2, c3 | WA | 100 | LP, AMPHIB |
| 1:3 | RODENT MAN | c1, c2, c3 | CH | 100 | LP |
| 1:3 | SERPENT_MAN | c1, c2, c3 | WA | 100 | LP, AMPHIB |
| 1:3 | TROLL | c1, c2, c3 | CH | (50) | LP, EVIL |
| 2:2 | MANERA | c2 | CH | 10 | EVIL |
| 2:3 | BLIND_CAVE_OGRE | c2, c3 | CH | 50 | LP, EVIL |
| 2:3 | BUGBAT | c2, c3 | CH | (50) | FLIER |
| 2:3 | CAVE_FLOATER | c2, c3 | CH | 10 | FLIER |
| 2:3 | CRUNDLE | c2, c3 | CH/WA | 100 |  |
| 2:3 | FLOATING_GUTS | c2, c3 | CH | 10 |  |
| 2:3 | GREEN_DEVOURER | c2, c3 | CH | 10 |  |
| 2:3 | JABBERER | c2, c3 | CH | (50) | LP |
| 2:3 | MAGGOT_PURRING | c2, c3 | CH | (50) | vermin |
| 2:3 | MOLEMARIAN | c2, c3 | CH | 20 | LP |
| 2:3 | PLUMP_HELMET_MAN | c2, c3 | WA | 20 | HEROES |
| 2:3 | REACHER | c2, c3 | CH | (50) | EVIL |
| 2:3 | RUTHERER | c2, c3 | CH | (50) |  |
| 2:3 | SPIDER_CAVE_GIANT | c2, c3 | CH | 20 | LP |
| 2:3 | VORACIOUS_CAVE_CRAWLER | c2, c3 | CH | (50) | LP |
| 2:4 | SNAKE_FIRE | c2, c3, magma sea | LAVA | 100 | FIREIMMUNE, vermin |
| 3:3 | BLOOD_MAN | c3 | CH | 1 | LP, EVIL, NOT_LIVING |
| 3:3 | CAVE_BLOB | c3 | CH/WA | 10 |  |
| 3:3 | CAVE_DRAGON | c3 | CH | 5 | FIREIMMUNE_SUPER, LP, EVIL |
| 3:3 | CREEPING_EYE | c3 | CH | 5 | EVIL |
| 3:3 | CREEPY_CRAWLER | c3 | CH | 10 | EVIL, vermin |
| 3:3 | ELEMENTMAN_AMETHYST | c3 | CH | 1 | LP, NOT_LIVING |
| 3:3 | ELEMENTMAN_GABBRO | c3 | CH | 1 | LP, NOT_LIVING |
| 3:3 | ELEMENTMAN_IRON | c3 | CH | 1 | LP, NOT_LIVING |
| 3:3 | ELEMENTMAN_MUD | c3 | WA | 1 | LP, NOT_LIVING |
| 3:3 | FLESH_BALL | c3 | WA | 10 |  |
| 3:3 | HUNGRY_HEAD | c3 | CH | (50) | LP, FLIER |
| 3:4 | ELEMENTMAN_FIRE | c3, magma sea | LAVA | 1 | FIREIMMUNE, LP, NOT_LIVING |
| 3:4 | ELEMENTMAN_MAGMA | c3, magma sea | LAVA | 1 | FIREIMMUNE, LP, NOT_LIVING |
| 3:5 | MAGMA_CRAB | c3, magma sea, underworld | LAVA | 100 | FIREIMMUNE |

---

## R40 — what `pack_sneak` is, and whether SNEAK was tested across 0-20

**What it is (DOCUMENTED, code, v7.0).**
- `cfg.v7.pack_sneak`, default **0.25** (`SWP/scripts/seasonal-wildlife.lua:500`), is read in the ecology relation write (`:4179`).
- For each candidate predator → prey pair that `MODEL.reaches` allows, the write computes `share = (alive members of the predator's tracked group, or 1 if ungrouped) × predator mass / prey mass` (`:4183-4189`, `:4212-4214`). Then:
  - if `share < pack_floor` (0.05), no relation is written;
  - **else, if `pack_sneak > 0` and `share ≥ pack_sneak`, `V7.unitSkills(a, {'SNEAK'}, 10, 'pack')` gives that hunter unit SNEAK rating 10 in `status.current_soul.skills`** (`:4217`; `unitSkills` `:6462-6494`).
- It is a per-unit soul skill, not a raw `NATURAL_SKILL`. It is written once per unit per session (cache key `id:pack`), recorded, and undone on restore.
- **What it does in practice (INFERRED from code).**
  - The level is fixed at 10. The threshold only decides *who* gets it.
  - At 0.25 almost every armed hunter qualifies against almost every prey: a lone cougar against a deer has share 0.43.
  - Solitary hunters already get SNEAK 10 from the `solo` package (`:6408-6419`, `V7.soloUnits` `:6497-6504`). So `pack_sneak` adds SNEAK only to group hunters.
  - DFHack's `getSpeed` shows SNEAK acting only while `flags1.hidden_in_ambush` is set (`Units.cpp:1632-1636`). The wiki says the skill matters only while the unit is sneaking toward prey (Ambusher page; A-mechanics §13).
  - No placed hunter was ever caught hidden (0 of 426 snapshots, A-mechanics §13). So by the documentation the write is probably inert.
- **Measured effect.** SW2/SW2R swept the *threshold*, 0 / 0.25 / 1.0, with the level fixed at 10, over 4 reps on CTRL. Placed prey killed: sneak0 4 vs ctl 3 vs sneak100 0. There was no measurable effect, and the result was confounded by cell position (`findings.md:544-551`; `STATE.md:4083-4087`). The night's recommendation was "pack_sneak 0 and retire the per-unit SNEAK write" (`STATE.md:4131`). It is not yet applied: v7.0 still defaults to 0.25.

**Was NATURAL_SKILL:SNEAK tested across its range? No.**
- Every SNEAK arm ever run wrote **rating 10 on the unit's soul**: STL `sneak`/`nslow`, STL2 `sneak`/`all`, LONE/LONE10 `pkg`, and SW2 via the tool. The code is `utils.insert_or_update(..., {id=df.job_skill.SNEAK, rating=10})` (`DC/scripts/eco-run.py:348-350, 376-382, 397-412`; tool `:4217`).
- The only contrast was 0 vs 10. No arm used any other level.
- No arm wrote the **caste raw** `NATURAL_SKILL`. The tool's caste write (`V7.naturalSkill`, `:6436-6450`) is "unverified on the rig" (`:6416-6418`; `STATE.md:3917-3918, 3929`), and the validator checks AMBUSHPREDATOR only.
- Results at 10 (A-mechanics §12, MEASURED):
  - STL+STL2 sneak vs ctl: RR 1.75 [0.44, 8.2]. All of it came from lion kills, and the lion's own control killed as often.
  - LONE/LONE10 full package: ×2.1 [1.2, 3.9], confounded with cell order. SNEAK cannot be separated from the six other skills, AMBUSHPREDATOR and `stealth_slows` 0.

**Scale (DOCUMENTED).**
- Skill ratings run Dabbling 0 … Accomplished 10 … Grand Master 14, and "Legendary" is **15 and up**. 20 is Legendary+5 (DF wiki, Skill page).
- DFHack's sneak speed term caps at `min(20, SNEAK)` (`Units.cpp:1632-1636`). So 20 is the useful ceiling for stealth movement, and the user's "legendary = 20" is right as a ceiling.
- Our 10 is "Accomplished", mid-range.
- Vanilla raws (Python scan of `data/vanilla/vanilla_creatures/objects/creature_*.txt`, this review): **GREMLIN is the only creature with NATURAL_SKILL:SNEAK (3)**.
  - CLIMBING:15 is common (110 creatures).
  - Combat natural skills appear only on megabeasts: DRAGON, HYDRA, ROC, MINOTAUR at 6-14.

**The honest answer.**
- `pack_sneak` is a mass-share threshold that hands rating-10 SNEAK to group hunters.
- It was tested only as a threshold (0 / 0.25 / 1.0, no effect, confounded), and SNEAK only at 0 vs 10 on the unit.
- The 0-20 range, the caste-raw route, and whether a wild unit ever enters the hidden state for the skill to act on were all never tested.
- Per R8 and R58, keep the solo package. A post-alpha **SNK-L** arm set would settle it:
  - region8, n=5 reps per arm, fresh load per rep, all animals wiped (R15);
  - one JAGUAR or SHARK_TIGER as hunter, SNEAK at 0 / 5 / 10 / 15 / 20 written as the caste NATURAL_SKILL *before* placement (receipt: the caste vector read back) and on the unit;
  - a forced hidden start (`flags1.hidden_in_ambush=true` at placement);
  - prey at 30 tiles;
  - readout: the hidden flag every 10 t, prey detection (`enemy.detection_info.last_spotted_unid`) and first-strike tick;
  - 15,000 t per rep.
