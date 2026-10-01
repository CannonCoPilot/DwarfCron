# ECO review Part 1: answers, findings and plan (1 Oct 2026)

The user's Part 1 review is in `USER-REVIEW-PART1.md`. The evidence behind every line here is in the four desk reports:
- `A-mechanics.md`, items 1, 2, 3, 5, 11, 12, 13 and 14, plus the analysis scripts in `A-mechanics-analysis/`;
- `B-dials-groups-forts.md`, items 6, 10 and 16;
- `C-irruption-aquatic.md`, items 7, 8 and 9;
- `D-frequency-figures.md`, items 4, 15, 17, 18 and 19, plus the patches tested in `fig-diag/`.

**The report is not revised.** Revisions are held until the user's Part 2. No rig was used, because DF was running as the user's game.

## 0. What this pass changes in our understanding

1. **Every ECO arena block ran its cells in one load, in the same order each rep.** That covers CAL, PK, STL, STL2, LONE, LONE10 and SW1–SW7.
   - Natives and the tool's group records carry from cell to cell. SW1R showed this confound can produce an apparent effect.
   - None of those blocks' effects is clean until it is re-run with a fresh load per arm and the order reversed.
2. **The sweep's "no effect" verdicts are vacuous for three dials:**
   - **The placed wolf pack was never a tracked group.** `cx-eco spawn` clears the roaming flag, and the tool only adopts flagged units. So `swdiscover n=0` in all 40 cells, and `wolf_groups=0` in 782 of 800 samples.
   - **Pack floor and sneak therefore weighed one wolf, and no SW2 arm ever wrote SNEAK.** One wolf is 22% of a deer, below the 25% bar.
   - **The nudge fired 0 times in all 8 control reps.**
   - **There was no manipulation check.** We scored outcomes without first proving the dial changed the internal state.
3. **Placed and released units are fort-side to DF.** DF aims them at new arrivals itself, so any outcome scored on placed hunters mixes the tool's writes with DF's own.
4. **Figures:** eight specs list the value first, so their marks never draw. That is why 18, 19 and 11 look empty, and why five figures the user didn't name are empty too. Figure 17 drew a tick reference on the wave-count axis. All fixes are tested in `fig-diag/` and held.

## 1. Answers to the review (short form; full evidence in A–D)

| # | Question | Answer | Confidence |
|---|---|---|---|
| 1 | What does LARGE_PREDATOR do? | **Documented (wiki):** a drive to attack smaller creatures, at most one LP group per map, worldgen region placement, and its own wave pool. **Measured:** it doesn't start hunting (0 attacks without a written relation, P1/T1), and a relation isn't needed for it to act (a coyote without LP made 343 attacks). BENIGN is the switch. LP's only measured effect is that a BENIGN badger given LP gets drawn into fights with the fort's dogs (E32b, 2 reps). Whether LP has its own pool is open; X3 (p = 0.014) says LPs share the pick with prey on CTRL, so test LPP1 decides. DFHack never reads the token. | documented + 2-rep measured |
| 2 | Natives vs wild | Two independent axes. **Origin** is DF-drawn ("native") vs tool- or harness-placed vs released. **Wild** has two meanings: DFHack `isWildlife` (has a regional population reference) and DF's own aiming test (carries the roaming wave flag). The two "wild"s disagree exactly on placed and released units. Origin is a partition of units on the map. "Wild" excludes citizens, pets, livestock, caravan animals, invaders and visitors. Megabeasts, forgotten beasts, night creatures and vermin sit outside both. Full table: A §2. Test WILD1 checks the flag directly. | code + measured |
| 3 | Is it pack mass / prey mass? | **No.** Within wolves the mass ratio explains nothing (OR 0.96 per doubling), while pack size does (OR 3.8 per doubling, CI 1.0–13.8). Prey mass doesn't lower kills; it lengthens fights. It affects **pairing** only through the tool's own rules (the 5% floor and roster `eats()`). The best predictor of a kill is whether the prey can outrun the hunter (STL OR 0.20; LONE ×1.85 per +100 speed units). | measured, order-confounded |
| 4 | Apex FREQUENCY | FREQUENCY is a relative weight: each species gets about f / Σf of the picks (wiki + F1, X3, ECO2-FC). The ladder gave apexes 6–8% of land weight, which predicts about 4.8 apex waves over the six S8 runs; they got 6 (0, 0, 0, 3, 2, 1). So the step did what it was set to; the target was too low and set in waves. Test **FQ1** sweeps f = 1, 2, 5, 10, 25, 50, 75, 100. For the trophic pyramid, target **units** with a biomass check (§3). | wiki + measured |
| 5 | Curious beasts' tick counter | It's reachable (`unit.animal.leave_countdown`), but it isn't why they leave. DF zeroes it on theft and zeroed it again within 300 t of our reset (CB, 1 rep). They leave because they stole. The only measured hold is clearing the CURIOUS_BEAST caste flags. Probe **CBX** tests holding the steal goal or flag per unit. | 1-rep measured |
| 6 | Do the dials move the map? | Mechanisms of all 22 dials are in B §6.1. The verdict is unsupported: three manipulations never reached the subject (§0.2), outcomes were scored on units DF aims itself, cells shared a load, and two reps can only see roughly 5–6× effects. **Yes**, to all three of the user's questions: we used the wrong metrics, uncontrolled lurking variables, and designs that were too loose. The dials with large measured effects sat outside the sweep: FREQUENCY, cluster size, leader, BENIGN, hold, and relation writes on newcomers. | measured re-read |
| 7 | Irruption vs invasion | **Invasion** is DF's own army raid, disabled in the user's game. **Irruption** (an ecological term) is a sudden surge of a population beyond its normal range, driven by pressure or scarcity. Today the module only flags the next group DF sends as agitated when cavern pressure crosses a threshold. The redesign is in §4. | code + measured |
| 8 | Pelagic predators and shallow water | OCEAN2 is 1–2 levels deep. Pelagic predators stayed away because the single water-apex slot went to the saltwater crocodile, the "pelagic" slot is for **prey** and is optional, and large ocean species are drawn at 0.1× on shallow maps. **Probable bug:** the deep-water survey stops after the top water level, so it would also miss BOATS's 12,045 deep columns (rig read needed). Fix in §5. | code + measured |
| 9 | All aquatic groups led | The stranded orcas were the harness's **unled control** (COHO), not something the tool placed. The tool's own leader lever has never been measured in water. Real gaps: `place` makes no group and scatters animals; DF's embark-seeded water life is never led; nothing checks the leader is in water. Fix in §5. | code + measured |
| 10 | 1×1 forts per biome | Region6 (seed 424242) already has OCEAN, LAKE, RIVER, SAVAGE, GOOD and EVIL tiles: 23 region biomes. But GOOD and EVIL are both savage there, so a seed search is needed to separate alignment from savagery. A 1×1 has auto groups at once = 2, shorter walk-offs, ~465–550 t/s, and no room for the SW1 arena. Estimate: about 1.75 h desk + 6–7 h rig, after r2. | survey on disk |
| 11 | "DF aims every non-wild unit" | The axes are swapped in the spec, so it draws nothing. Its title overclaims "every": the median arrival is marked by one writer. It also never says that no attacks followed. Replace it with a holder-class × target-class grid of written relations, with an "attacks followed?" mark. | data re-tally |
| 12 | SNEAK alone best? | Not supported: kill ratio 1.75 (CI 0.44–8.2), all lion kills, and STL could only detect effects of ×5 or more. **The user's ruling stands:** apply SNEAK (§6). The one CI-clear gain is the full solitary package in LONE (×2.1, CI 1.2–3.9). | measured; user ruling |
| 13 | "Wild animals never sneak" | It overstates the data. 426 single-tick snapshots of `flags1.hidden_in_ambush` only cap hidden time at about 0.7%, which would still allow one short hidden approach per engagement. Half that test read a marauder flag. Experiments **SNK1** (sample hidden every 10 t around attacks), **SNK2** (prey flee-onset distance vs hunter Sneak skill) and **SNK3** (r2 `devel/datamine` snap/diff on a hunter during its approach) settle it. | measured, weak |
| 14 | Do combat skills raise engagement? | Strikes rose about ×8.7 (CI 2–37), but the share of runs with any attack didn't change. 276 of 315 strikes came from two cougar × deer runs. Define an engagement as a bout of attacks with gaps under 100 t, counted per hunter-day. **ENG1** needs about 8 runs per arm to see ×3 (see decision Q4). | measured, weak |
| 15 | Token heatmap figure | Full page width, outlined clusters at the 0.5 cut, and a new caption that explains the grouping and sort order. Built and rendered; held. | patch ready |
| 16 | Groups held below √(tiles)+1 | **Little's law, not the cap:** L = λW. The tool releases about one group per 15,000 t (the 5–20-day gap), and a group stays 22,500–59,000 t, so L ≈ 2–3. T8g implies W ≈ 34,500 t, which matches. The cap binds only below λW; bigger maps have longer walk-offs, so it bound only on 5×5 and 6×6. Coverage: land on CTRL only, caverns on BOATS, water on BOATS's ocean and river; lake, pool, deep and layer_groups A/B were never run. The three tallies define "group" three ways, none checked against DF's population entries. The re-run is §2 test G2. | measured + inferred |
| 17 | Kangaroo y-axis | The tick-2,400 reference line was drawn on the wave-count axis. Fixed; held. | patch ready |
| 18 | Leader figure empty | Value-first spec. Fixed; held. | patch ready |
| 19 | v2.2 ladder figure empty | Value-first spec, plus two lines both labelled "land". Fixed (one target band); held. | patch ready |

## 2. Fix the instrument before any new rig data (harness, v7.1-independent)

| Fix | Why | Size |
|---|---|---|
| H1. Default a **fresh load per arm**, with the order reversed in rep 2, for every multi-cell block | Cell-order and record carry-over (§0.1) | eco-run.py flag default; S |
| H2. **Manipulation check** first in every block: print the dial's internal state (tracked group n, written skills, nudge count, pairs written) and stop the block if it didn't change | §0.2: three vacuous dials | per-block receipt; S–M |
| H3. Placed packs must be **adopted as one tracked group**: either keep the roaming flag and register the group in the tool, or add a `groups adopt <ids>` verb | SW2's floor and sneak never saw a pack | M (verb + harness) |
| H4. Score outcomes on **DF-drawn subjects**, or on placed units with DF's aiming isolated (sweep its writes, or a no-tool control arm per cell) | §0.3 | design; M |
| H5. **One group definition** across tallies (unit.animal.population + arrival cluster + the tool's record), checked three ways against DF's population entries | Item 16 audit (B §16.3) | M |
| H6. Engagement and bout metrics from timestamped attacks; hidden-flag sampling every 10 t near attacks | Items 13–14 | S |
| H7. Fix the figure spec checker so a value-first spec fails the build | §0.4 | S |

## 3. FREQUENCY and the trophic pyramid (item 4)

**Target units, not waves.** Each species' weight is divided by its mean group size, (CLUSTER min + max) / 2. That matches observed group sizes on the rig (troglodyte 7.51 vs 7.5, wolf 4.79 vs 5).

**Pyramid targets**, as shares of units per season (D §2.3), with a biomass guard that keeps land and caverns upright and lets the ocean invert:

| Layer | Herbivores | Carnivores | Apex | Apex present on the map |
|---|---|---|---|---|
| Land | 70–76% | 18–23% | 5–8% | 20–30% of the season (1–2 visits); never more than 1 group (2 on savage maps) |
| Flying | 80% birds | 20% raptors | 0 (calm), ≤ 5% (savage) | Its own problem: CTRL's fliers are ravens whatever the roster says |
| Ocean | 80–85% | 10–15% | 3–5% | 15–25% on deep maps |
| Lake / river | 85–90% | 10–15% | 0–5% | Optional |
| Caverns, per depth | 55–65% | 25–30% | 10–15% | Most of the time; the ladder's job is to **raise prey** |

A literal 10% step leaves an apex on the map about 3% of the time, which is what the game does today. Proposed steps per level: ¼ on land, ⅕ in water, ⅓ in caverns.

**FQ1:** cougar at f = 1, 2, 5, 10, 25, 50, 75, 100 against four prey at f 25 each, on CTRL, 2 reps, counterbalanced, with subject receipts. Tool off and tool on, plus a season check: about 3.6 h, or 2.4 h trimmed. **LPP1** (does LP have its own pool?) shares FQ1's loads.

## 4. Irruption v2 (item 7): purpose, design, experiments

**Purpose.** An ecological surge, not a raid. Cavern civilisation races spill out of their range in larger numbers than rotation, driven by pressure in the caverns (dwarves, digging, fort activity), scarcity or season. They behave restlessly: they wander toward the fort, steal, rage, sneak and linger. It must be noticeable and survivable on a 7-dwarf fort, and every write is undone.

**Numbers.** The tool **places** the wave from the cavern's own population entry (`PLACE.fromEntry` in the cavern band). That debits the entry and refunds it on departure, so it uses no invasion machinery. Optionally the `cluster_number` write enlarges the next draw. Default: 3 waves of 2× cluster max, 2 days apart.

**Behaviour levers**, mapped to what the user asked for (C §7.4–7.5):
- **Rage:** per-unit CRAZED via `uwss_add_caste_flag`, which acted in E11c when re-applied. It is capped at ≤ 20% of a wave. The agitated flag is kept only as an opt-in "fury" tier.
- **Stealing:** CURIOUS_BEAST_ITEM, written on the caste just **before** the tool places the wave, so it reaches exactly the new units, then restored. A per-unit cache write is the alternative if probe M4 passes.
- **Wandering:** waypoints toward the fort's cavern access every 300–1,500 t, with no leader so the group spreads.
- **Meandering:** MEANDERER added; its effect on speaking races is doubtful (M3).
- **Sneaking:** write `hidden_in_ambush`, plus SNEAK/AMBUSH skills (M7).
- **Lingering:** a longer `leave_countdown`.
- **Never:** runtime-created syndromes (save risk) or the marauder/invader flags (that is the invasion machinery).

**Programme (C §7.6):**
- **Desk D1–D3:** syndromes with CE_ADD_TAG in vanilla; cavern civ-race entries per fort; how to address RODENT_MAN.
- **Phase 1, probes M1–M9:** does each write stick, does it act, does a caste write reach existing units, theft, mischief, hidden, waypoints, facets. 2 reps each, on BOATS. CTRL's caverns have no civ races.
- **Phase 2, three arms × 2 reps**, fresh load per arm, order reversed in rep 2, 30 days each, on BOATS with a breach and 3 citizens sustained:
  - A, normal rotation;
  - B, irruption without tokens;
  - C, irruption with tokens.
  - **Metrics:** distance, area covered, approach to citizens and the breach, thefts, attacks by and on the subject, rage episodes, hidden time, stay length, fort survival.
  - **Safety criterion:** the fort survives in C, 2 of 2.
- **Phase 3:** rebalance wave size, spacing, tier fractions and pressure gains on the Phase 2 numbers.

**Module sketch (C §7.7):** IRRUPT v2 behind a switch, off by default. It has ecological triggers, tiers (restless / thieving / fury), an event log, and restore on end, unload and disable. It adds console verbs, Panel rows and validator claims. Release: v7.2, after Phase 2.

## 5. Water (items 8 and 9)

- **Survey bug (check first):** confirm on the rig that the deep-water survey stops after the top water level (BOATS should read 12,045 columns 3+ deep), and fix it.
- **Pelagic rebalance:**
  - a separate **pelagic-apex** slot in the builder;
  - **prey presence raises the predator's draw weight** for that water body;
  - Driver B places the predator in the deepest water nearest the prey;
  - a stranding guard: water tile only, a wet path to the prey, and a `getBreathingState` check one tick after placement on r2.
  - Test: 2 arms × 2 reps, on OCEAN2 and BOATS.
- **Leaders for every grouping aquatic group:**
  - assign a leader when a group is drawn or placed, including `place`, which should create a group;
  - require a wet leader;
  - re-elect immediately when the leader dies or starts to leave;
  - adopt DF's embark-seeded schools.
  - Five validator claims, plus a test of the tool's own lever in water: COH-W, 2 reps.

## 6. Rulings and defaults from this review

- **SNEAK (user ruling, item 12):** apply it.
  - Keep SNEAK in the solo package (already on).
  - Keep `pack_sneak` at 0.25: reject open item `dflt-pack-sneak-0`.
  - Because the threshold is reached only by a real tracked pack (H3), also make SNEAK apply to every LP or AMBUSHPREDATOR hunter the ecology pairs, whatever its share.
  - Measure with SNK2, but don't gate the default on it.
- **Apex step:** keep it and re-target it to the §3 pyramid. Reject open item `dflt-drop-apex-step`.
- **Engagement counts as success (item 14):** if ENG1 shows more bouts without more kills, record it as a behavioural success.
- **Test forts (item 10):** 1×1 embarks, one per biome, are the standard for new experiments. A seed search is needed so GOOD and EVIL are not both savage.

## 7. Order of work (after the user's Part 2 and the DFHack r2 re-validation)

1. **Desk, no rig:** the harness fixes H1–H7; the irruption desk items D1–D3; a seed search for calm GOOD and calm EVIL tiles.
2. **Rig: r2 re-validation** (REPORT §4) and the deep-water survey read.
3. **Rig: build the 1×1 biome forts** (about 6–7 h).
4. **Rig, with manipulation checks:** FQ1 + LPP1, G2 (groups per layer, three-source), SNK1–3, ENG1, CBX, WILD1, COH-W.
5. **v7.1 build:**
   - unit-based ladder with the pyramid targets;
   - aquatic leaders;
   - pelagic slot and survey fix;
   - SNEAK rulings;
   - `groups adopt`;
   - the performance pass P0–P7.
6. **Irruption Phase 1 → Phase 2 → Phase 3**, then IRRUPT v2 in v7.2.
7. **Report revisions**, held until Part 2: the figure patches in `fig-diag/` and every answer above.

## 8. Questions for the user

- Q1. Pyramid targets: accept the §3 table (apex present 20–30% of the season on land)?
- Q2. Irruption tiers: allow the agitated "fury" tier at all (opt-in, ≤ 20% of a wave), or stop at CRAZED?
- Q3. Seed search for calm GOOD and calm EVIL forts: OK to generate new worlds?
- Q4. Replicates: two per arm can only detect effects of about ×5. ENG1 and SNK2 need about 8 runs per arm to see ×3. Keep two reps (pace) and report effects as "detectable only if large", or allow more reps for these two?
