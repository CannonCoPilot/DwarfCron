# B — The tool's dials, concurrent groups, and the 1x1 biome forts (review items 6, 16, 10)

Desk work only, 1 Oct 2026. No rig calls were made, nothing was committed, and the report sources were not edited. Every
report revision is held until Part 2 arrives.

**Evidence labels.**
- **MEASURED**: replicated rig data. The run directory or findings entry is cited.
- **DOCUMENTED**: stated in the code, STATE.md, the DF wiki or DFHack's docs, but not measured here.
- **INFERRED**: my reading of code or data. It needs the check named beside it.

**Paths.**
- `sw.lua` = `seasonal-wildlife/scripts/seasonal-wildlife.lua` on branch v7.0 (99c1ec8).
- `findings` = `DwarfCron/data/eco-desk/findings.md`.
- `STATE` = `seasonal-wildlife/STATE.md`.
- Run directories sit under `DwarfCron/data/experiments/`.

---

## 0. Headline answers

1. **Item 6.** "Most dials don't move the map" is not supported, because for several dials the sweep never actually
   applied the manipulation. Re-reading the run data turned up three failures nobody had caught (section 6.2):
   - **The placed wolf pack was never tracked as a group** in any of the 40 arena cells.
     - The records show it: `swdiscover n=0` 40 of 40, and `wolf_groups=0` in 782 of 800 samples.
     - Cause: `cx-eco spawn` clears the roaming flag, and the tool only adopts flagged units.
     - So the pack-mass floor and the sneak bonus weighed **one wolf**, not five.
   - **No arm of SW2/SW2R ever wrote SNEAK.**
     - Measured against the raws, one wolf is 22% of a deer, 4% of a buffalo and 0.8% of an elephant, so nothing reached the
       25% sneak threshold.
     - The floor arms also collapsed: ctl (0.05) and floor20 (0.20) refuse exactly the same pairs.
   - **The nudge never fired at its current setting.**
     - Within-cell nudges were 0 in all 8 control replicates (SW1, SW1R, SW2, SW2R).
     - "Nudge off ≈ current" therefore compared two arms in which the nudge did nothing.

   Two further problems apply even where the manipulation did reach the subject:
   - The outcome was scored on placed units. DF treats these as non-wild and aims them at targets itself (RELS2), so the
     tool's dial was competing with DF's own targeting.
   - The cells of one load inherited each other's natives **and** each other's tool group records.

   Dials with strong measured effects were outside the sweep: FREQUENCY, cluster size, the leader, the BENIGN switch,
   rewriting relations on newcomers (E17), and hold / leave_countdown.

2. **Item 16.** Concurrent land groups are held near 2–3 by **Little's law**, not by the limit.
   - The tool releases at most one gated group per jittered gap. The gap is 5–20 days, mean 12.5 days = 15,000 ticks
     (`sw.lua:5629-5633`).
   - A group then stays for DF's leave countdown plus its walk off the map: 22,500–59,000 ticks (E9a).
   - So L = λW ≈ (1/16,000 t) × ~33,000 t ≈ 2.1, plus the one gated group in flight.
   - T8g measured surface 0.75 waves per 10k ticks and 2.59 groups at once. That implies W ≈ 34,500 ticks, which matches.

   The limit binds only when it sits below λW. On bigger maps the walk off takes longer, so W and L rise, and a limit of
   3 starts to bind. That is why √(embark)+1 helped only on 5x5 and 6x6 (INFERRED; section 16.2 gives the test).

   What has been run, per layer:
   - Land: CTRL's tile only (ECO2-G 1x1–6x6, G1, SW3B).
   - Caverns: BOATS only (SW5).
   - Water: BOATS ocean and river only (SW6).
   - Never run: lake, pool, deep, any other land biome, and layer_groups on against off.

   The three group tallies define a "group" three different ways (section 16.3). None of them is corroborated against
   DF's population entries.

3. **Item 10.** The six required forts can all be built in the existing world region6 (seed 424242) using its survey,
   which is already on disk:
   - OCEAN, LAKE, RIVER, SAVAGE, GOOD and EVIL tiles all exist there, and 23 distinct region biomes in all.
   - Caveat: GOOD (TUNDRA) and EVIL (SHRUBLAND_TEMPERATE) are both savage on this world. Only 22 land tiles are calm, so
     alignment and savagery are confounded.
   - A 1x1 sets groups at once to 2 (auto), shortens the walk off (smaller W), and makes the SW1 arena impossible (the map
     is 48 tiles wide).
   - It runs at about 465–550 ticks/s (ECO2-G).
   - The plan is about 1 h at the desk and 6–7 h on the rig, after the DFHack r2 re-validation (section 10.6).

---

## 6. Item 6: every dial, its mechanism and its evidence, then the sweep critiqued

### 6.1 Dial by dial

"First stage" means the internal state the dial changes. "Map" means whether rig evidence shows the change reaches
something on screen.

| dial (default) | mechanism in code | first-stage evidence | map evidence | verdict |
|---|---|---|---|---|
| **ecology cadence** (`ecology.cadence` 1,500; `sw.lua:476`) | `ecologyJob` scheduled every `cadence` ticks (`:6260`). Each pass: clears departed slots, writes **new** predator×target pairs within a 30 ms budget (`ECO.BUDGET_MS`, `:4154`), runs the sweep, then the nudge (`:4450-4501`). The pass memory `ecoDone` resets every 8th pass (`ECO.REFRESH`, `:4161`), so a pair DF wiped is rewritten only within 8 × cadence (48,000 t at cadence 6,000) | none recorded per arm. The SW status printed only cumulative pairs (`eco_pairs` = `last.pairs`), not latency | **MEASURED**, E17 (`STATE` add. 32): writing once vs rewriting every 1,500 t gave late prey killed **2 vs 21** and combat **70 vs 3,419**. Pairs DF never filled: 3 of 630. Shedding (about 1 unit in 9) is E16 | It moves the map **when prey arrive after the write or units shed rows**. The SW1 arena placed every animal at t0, so the cadence mechanism was mostly idle (INFERRED) |
| **nudge** (far_tiles 40 / far_ticks 3,000 / radius 6; `:476`) | `ecoNudge` (`:4425-4449`): a predator whose **nearest target** of any kind (natives and caravan animals included; `ecoIsTarget` `:4080-4096`) is beyond far_tiles for far_ticks is teleported to within `radius` of it | SW1/SW2 status: **0 nudges in every control cell** (section 6.2 C). Tight (20/1,500) fired 12–16 per cell | **MEASURED**, E18 (add. 40): the arrival time decides kill latency, not the threshold. 20 tiles teleported about 25× for no faster kill | Untested at the current setting. In the arena some target was always within 40 tiles (INFERRED) |
| **pack_floor** 0.05 (`v7`, `:497`) | `ecoWrite` (`:4179-4219`): share = (live members of the unit's **tracked** group, `packN`, `:4183-4188`) × predator mass ÷ prey mass. Below the floor, no pair is written (`g.ecology.small` counts it). A unit in no tracked group counts as 1 | SW2: pack never tracked, so the floor weighed one wolf (6.2 A/B) | **MEASURED**, CAL: 7 wolves = 5.6% of an elephant was the lowest share that killed. CAL kills deer 1, moose 4, buffalo 7, elephant 3 (wolves only; correction `findings:602`) | Not yet tested as designed |
| **pack_sneak** 0.25 (`:497`) | Same loop: share ≥ sneak gives SNEAK 10 to the hunter (`V7.unitSkills`, `:4217`, `:6453-6483`). It is written once per unit (`'pack'` tag) and never removed | Never written in any SW2 arm (6.2 B) | **MEASURED**, STL/STL2: skilled vs unchanged gave no clear lift (`findings:228`) | SW2's "no effect" is **vacuous**. The STL prior stands on its own |
| **x3 pack bonus** (builder only) | `ROSTER.pickWeight` (`:5142-5151`): weight ×3 if `packBonus` (`:5096-5099`), at **roster build** time only. No runtime effect | D1 desk: rosters change at every level, and pack-hunt presence moves 56.8% → 76.7% (`eco-run.py` SW7 comment) | SW7: no measurable effect, but only 7–8 of 27–29 wanted species exist in CTRL's pool (`findings:491`) | A composition dial. Its first stage is deterministic and measured at the desk. The rig test was weak by construction |
| **ladder / FREQUENCY** (`ROSTER.LADDER`, `:5413-5417`, R13 scaling `:5361-5383`, written to `cfg.odds` `:5395`) | `CAVERN.apply` writes `cr.frequency` = odds for every open species with odds, on any layer (`:3006-3049`). DF's pick reads it | **MEASURED**, F1: surface shares ∝ f (kangaroo f100 60.5% vs 53.5% predicted …). ECO2-FC: per cavern layer ∝ f. ENGINE water draw weight (`:4900-4910`) | **MEASURED**, SW4: ×0.5 cut predators to ~2% of land units in both orders; ×2 was not reliably above ×1. Apex present in 1 of 6 runs | It moves the map. The **apex** step is masked by DF's one-LP-group rule (**DOCUMENTED**, `STATE` add. 38; roster prototype `findings` "one LP group per map") |
| **groups at once** (land auto = ⌊√tiles⌋+1, `:2849-2854`; per layer `:2861-2866`) | The land gate releases the oldest gated group only if `nLand < cap` **and** the gap timer has run out (`:6179-6196`). Caverns per depth (`:6197-6222`), water per body (`:5422-5455`) | Receipts printed the limit in every cell (SW3B, SW5, SW6) | **MEASURED**: ECO2-G gave +1 group only on 5x5/6x6. SW3B: 1 < 3 ≤ auto. SW5: the cap trims the tool's cavern groups by ~40%. SW6: 2 ≈ auto | It moves the map at the low end (cap 1). Above λW it cannot (section 16) |
| **layer_groups** (on) | Per-cavern-depth and per-water-body counts and clocks (`:6197`, `:5422`), and the parent's auto | none | **never A/B tested**: SW5 and SW6 ran it on in every arm | Untested |
| **gate_drain** (on) | `V7.drainGate` (`:3598-3628`): after a release, keep detaching gated groups until ≤ 1 flagged unit remains | Ledger lines "also detached … (gate_drain)" exist (`:6189-6194`). **No SW3B receipt printed them** (SWEEP-design §5) | **MEASURED** at the desk only, T8g: 27 of 36 slow releases had freed a singleton (p = 5e-6) | Not measured on the rig. ECO2-G, G1 and T8 ran before it existed (INFERRED from dates) |
| **hold / leave_countdown** (verb) | `holdGroup` raises each member's countdown to ≥ days (`:5938-5946`). `dismissGroup` zeroes it (`:5948-5954`) | **MEASURED**, F11 (add. 11): zeroed units walked off in 1,700–3,000 t (3/3). Units raised to 55,000 left at +55,876…57,469 (3/3) | **MEASURED**, E19: a herd held a full season grazed, did not starve, did not breed. T5: held 40 days | A strong lever on W, and so on concurrent groups (section 16) |
| **cluster_number / group size** (`size`, trickle) | `PATTERN.sizeApply` writes the raw {n,n} (`:5762-5785`); trickle writes {2,1} (`:5738-5760`); the water draw uses `ENGINE.groupSize` (`:4911-4918`) | **MEASURED**, E12: {7,7} → 7 (3/3), {2,2} → 2 (3/3). E42b: one over, about 1 wave in 6 | T8b: trickle's largest waves 2–3 vs steady's 7–8 | It moves the map |
| **stock** | `RESERVE` (`:2365-2398`), `applyLive` (`:2399-2442`) | **MEASURED**, E15/F15: one debit per arrival (small entries); a refund on departure, none on death (E4) | **MEASURED**, E3: stock is **eligibility only**, the pick ignores abundance. N1: entry 0 means no more waves; replacement follows within ~2k t | A gate (0 vs > 0), not a weight |
| **odds** | `cfg.odds` → `cr.frequency` (`CAVERN.apply`); `ODDS.share` (`:3082-3093`) | as FREQUENCY | F1, ECO2-FC, SW4 | It moves the map |
| **seasons / rotation** | `applyLive` at each season flip (`tick`, `:3369-3389`); `holdOutOfSeason` daily and every 300 t (`:2443-2464`, `:6135`); `seasons_own` clears NO_<season> | **MEASURED**, S1: 0 out-of-season arrivals in a year (80 samples). T2: DF honours NO_<season> | X1: held species arrived from a missed region tile, fixed by the 9-offset union (memory df-region-draw-tiles) | It moves the map |
| **coupling** (off) | `startCoupling` (`:3630-3686`): release the prey, close every entry except its in-season predators' (≥ 10 stock), optionally size the packs (`groups.pack`), and restore on the predator's arrival or after 2 days | **MEASURED**, E10: predator wave 298–430 t after the release, 5/5 | **MEASURED**: E11, co-presence alone gave no kills. T4 with ecology on: armed kills 3 vs 0 | It moves the map (co-presence). Default off |
| **patterns** (steady) | `PATTERN` (`:5640-5856`): gap policy, table and size | **MEASURED**, T8–T8d (add. 89): burst gaps as designed; follow PASS 2/2; trickle sizes; dawn weak (1/1 plus 1 vacuous) | as first stage | It moves arrival timing and composition |
| **limits ceiling** | Land: the gate stays shut when `countByLayer().land ≥ ceiling` (`:6180-6181`). Water: the draw stops at the ceiling (`:5433`). Cavern: frequency held at 1 (`CAVERN.apply`) | **MEASURED**, T7b: a brake on arrivals with a long lag (44 days to fall from 28 to 9) | as first stage | A brake, not a cap |
| **scav** (opt-in; scav_mapwide, scav_ext on) | `SCAV.run` (`:6862`ff): scavengers walk to (or, with scav_ext, are teleported to) remains off stockpiles and eat them | **MEASURED**, SCV2b/SCV2Wb: 6 kangaroo and 6 carp carcasses cleared within ~2,400 t in every cell | as first stage | It moves the map. Which species ate was not logged |
| **sweep** (on) | `V7.sweep` (`:4264-4316`): DF-written PREDATOR_OR_PREY cells between managed wild animals that the web does not pair are set to NONE | Counters exist: `sweep_cleared`, `refought` | **no outcome test**. Validator `mech.v70.sweep` passed with **0 units walked** (STATE add. 98) | Unmeasured |
| **solo package** (on) | `V7.apply` (`:6493-6530`): caste AMBUSHPREDATOR, natural skills 10, stealth_slows 0; plus per-unit skills (`V7.soloUnits`, `:6485-6491`) | `nSolo`, `nNat` counts | **MEASURED**, LONE10 (10 seasons per arm): placed-prey kills 14 → 29 (p = 0.07), all kills 21 → 49 (p = 0.024). The hunter was a **placed** (non-wild) cougar | Moves the map for placed hunters. Untested on wild ones |
| **outgun** (2.0; cap off) | `ROSTER.outgunPairs` (`:5112-5129`): a warning and a ledger line; `outgun_cap` caps the prey group size (`:5342-5353`) | — | Its basis is **MEASURED**: capybara killed 5/5 wolves (W1L); buffalo killed a lion (P1) | By design no map effect unless `outgun_cap` is on |
| **cohesion / leader** (on) | `applyCohesion` (`:5906-5936`) | **MEASURED**, E28: spread 5.0 vs 9.9 tiles. COH: flock, school and pod 3–10× tighter | L2 (1 rep): a led herd was barely attacked (1 attack vs 88) | Moves the map strongly; not in the sweep |

### 6.2 What the run data show that the verdicts missed (MEASURED from the TSVs on disk)

Run directories:
- `ECO/SW-20261001-003336/{SW1,SW2}.tsv`
- `ECO/SWR-20261001-063950/{SW1R,SW2R,SW3B}.tsv`
- `ECO/SW-rig2-20261001-033105/{SW5,SW6}.tsv`

**A. The pack was never tracked.**
- The arena pre places the wolves with `cx-eco spawn`, which sets both roaming flags false (`cx-eco.lua:382-383`).
- It then calls `sw.discoverGroups` (`eco-run.py:814`). That function adopts only units whose roaming flag is set
  (`gatedLayer`, `sw.lua:3511-3518`).
- Result: `swdiscover n=0` in **40 of 40** arena cells, and `wolf_groups=0` in 782 of 800 samples. The 18 exceptions are
  SW1R samples, most likely a natural wolf arrival.
- The design's own subject receipt ("`groups` lists WOLF x5 as one group", SWEEP-design §2) failed in every cell, and the
  failure went unnoticed.
- Consequence: `packN` = 1 for every placed wolf (`sw.lua:4183-4188`).

**B. Measured against the raws, the floor and sneak arms were not the arms designed.**
- Body sizes from the vanilla raws, read with Python (trap 19): WOLF 40,000, DEER 182,000, WATER_BUFFALO 1,000,000,
  ELEPHANT 5,000,000. `adultSize` scales every species the same way (`sw.lua:951-959`).
- One wolf's share of each prey: deer 0.22, buffalo 0.04, elephant 0.008.

| arm (floor, sneak) | wolf→deer | wolf→buffalo | wolf→elephant | SNEAK written? |
|---|---|---|---|---|
| ctl (0.05, 0.25) | written | **refused** | **refused** | no (0.22 < 0.25) |
| floor0 (0, 0.25) | written | written | written | no |
| floor20 (0.20, 0.25) | written | refused | refused | no |
| sneak0 (0.05, 0) | written | refused | refused | off |
| sneak100 (0.05, 1.0) | written | refused | refused | no |

- ctl ≡ floor20 ≡ sneak0 ≡ sneak100 in the tool's state for every placed pair. Only floor0 differs.
- Yet the wolves attacked the elephant in 93% / 55% of their attacks on the placed herds in ctl (`findings:542`), a pair
  the tool had refused. That is DF's own aiming of non-wild units (RELS2).
- (INFERRED; check `g.ecology.small` and the rel_map for the placed pairs in a replay.)

**C. The nudge at its current setting fired 0 times in every control replicate.**
- Within-cell deltas of `eco_nudges_total`:

  | arm | SW1 | SW1R | SW2 | SW2R |
  |---|---|---|---|---|
  | ctl | 0, 0 | 0, 0 | 0, 0 | 0, 0 |
  | nudge_off | 0, 0 | 0, 0 | – | – |
  | nudge_tight | 16, 15 | 13, 12 | – | – |

- Every other current-nudge cell read 0, except cad500 SW1R rep 1 (+2), sneak0 SW2 rep 2 (+4) and SW2R sneak0 rep 2 (+2).
- The design's receipt "in the control, at least one nudge" failed.
- The status counter is **cumulative across a load's cells** (g.ecology persists in site data), so SW1R's later cells show
  12–15 inherited from nudge_tight. Read as is, it suggests nudges that never happened.
- "Off ≈ current" compares two inert arms. The only real nudge contrast in the data is tight vs off: placed prey killed,
  pooled over 4 reps, 1 vs 3 (`findings:530`).

**D. Cells inherited tool state, not just natives.**
- SW3B land groups at the cell's first sample, rep 1 in order g1 → g3 → auto: 2, 2, **5**. g3 ended at 6, and auto began
  at 5.
- Rep 2 (auto → g3 → g1): 3, 3, 1.
- SW6: w1 rep 2 held 2–3 water groups at cap 1, inherited from w2 rep 2.
- Group records persist in site data across cells. The post only disables the tool (`eco-run.py:863-865`).
- With W ≈ 30k ticks and 50.4k-tick cells, about half of each cell's first half is the previous arm's groups.
- Cell position also confounds **season**: 3 × 50,400 t = 1.5 seasons, so `applyLive` changes the roster in the middle
  of a run.

**E. The outcome was measured on units the dial does not govern.**
- Placed units carry no roaming flag, so DF treats them as "other" and aims them (RELS2/RELS3, `findings:299-308`).
- On wild surface pairs DF almost never writes the relation itself (RELS2b, `STATE` add. 98).
- The tool's write therefore matters on wild units, and the arena used only non-wild ones.

**F. Metric problems.**
- `sweep-tally.py` A = total attacks, not the designed attack-intervals (its own docstring).
- W = upward steps in the group count (`:84`). An interval where an arrival and a departure coincide reads as 0, and two
  arrivals read as 1.
- K = every death row (natives included).
- G = the tool's tracked groups (residents and stragglers included).
- Kills were 0–4 per arm over 4 reps: zero-inflated, so only about 4× effects can show.
- SW4 scored the predator share of **units present**, which weights by residence time (its own note: "predators
  linger"), instead of the share of **arrivals**.
- SW4 forced a release every 1,500 t. That makes every arrival non-wild (RELS2) and imposes about 20 times the natural
  arrival rate (E2: 16–25 waves per 24k t, against T8g's 0.75 per 10k).

**G. Power at two replicates.**
- Between-rep spread of wolf attacks in the same arm runs 3 vs 41 and 22 vs 70 (SW2R/SW1 ctl). That is a CV of about
  0.7, an SD of log ≈ 0.63.
- Two reps per arm give a standard error of the log difference ≈ 0.63, so a 2-of-2 separation needs about a **5–6×**
  effect.
- Kills (Poisson): a 2× ratio needs about 25 events in the control arm. A 1.5× ratio needs about 80. At 0–1 kills per
  run that is out of reach by replicates; it needs exposure.
- SW3B land groups: within-arm SD ≈ 0.7, so a difference of about 2 groups is detectable. The +1 that ECO2-G reports
  needed 4 reps per arm (5x5 and 6x6 pooled).

**Lurking variables.**

| variable | controlled? |
|---|---|
| cell order | late (SW1R/2R; counterbalancing from SW3 on) |
| carryover of natives and tool groups | **no** |
| season and roster flip | **no** |
| process age | DF restart per run, cells not |
| fort state (thirst) | sustain at mid-cell |
| natives present | **no**; placed-only scoring added after the fact |
| prey density and distance | fixed 45–60 tiles; natives nearer |
| one-LP-per-map | **no** |
| gate_drain state | no receipt |

### 6.3 Tighter designs, dial by dial

General rules, which apply to every row below:
1. **Run a first-stage manipulation check before scoring any outcome.** It is deterministic and needs no power. If the
   first stage does not move between arms, stop and report the arm as vacuous, not as "no effect".
2. **One fresh load per cell.** Use cx-experiment manifests, which restore the save every replicate (`eco-run.py`
   comment above SW4), instead of eco-run blocks that share a load.
3. **Restart DF per run.** Randomise arm order per replicate with a Latin square across reps. Start every cell from the
   same save tick, so the season is held constant. Record DF uptime as a covariate.
4. **Subjects must be wild to DF when the dial acts through the tool's relation write.** Either:
   - (a) steer FREQUENCY and let the natural gate bring them (RELS2b design, no forced release); or
   - (b) place them and then set `roaming_wilderness_population_source=true` plus a real population ref ("wild-placed").

   Option (b) is INFERRED and needs a pilot:
   - Verify with the RELS method that DF no longer writes PREDATOR_OR_PREY rows for them.
   - It also lets `discoverGroups` adopt the pack.
   - It holds the surface gate shut, so no natives pile in. Set the gap to 1,000 days so the tool does not release them.
5. **Score per exposure, not per cell.** For example, attacks per predator-prey-tick within r ≤ 10, and kills per prey
   exposure-day.
6. **Prefer frequent events** (attack-intervals, time to first attack) over rare ones (kills).

| dial | first-stage check (printed every pass, read from inside the job) | right outcome | design | power note |
|---|---|---|---|---|
| ecology cadence | time from each arrival (ledger `arrive`) to its first written pair; relation coverage = share of eligible (armed, reachable) pairs whose rel_map cell is PREDATOR_OR_PREY at each sample | kills and attacks on **late-arriving** prey (E17 design) | CTRL, wild-placed predators at t0; prey herds released into reach at +3k, +9k, +15k t. Arms 500 / 1,500 / 6,000 | coverage is a near-deterministic contrast; E17's 10× kill effect is detectable at 2 reps |
| nudge | nudges per pass; predator-to-nearest-target distance; time spent beyond far_tiles | encounter-time (pair-ticks within 5 tiles); first-attack latency | Separate the trigger from the response: place the only targets 60–80 tiles away on an **otherwise empty layer** (wild-placed, gate held). Arms off / 40 / 20 | first stage: current setting must log ≥ 1 nudge, or the cell is vacuous |
| pack_floor | `g.ecology.small` per pass; rel_map cell for each placed predator × herd | attacks/kills per herd, by mass band | wild-placed pack adopted (receipt `wolf_groups=1 members=5`); herds chosen from the tool's own masses: one above the floor, one between floors, one below. Arms 0 / 0.05 / 0.20 | pairs written is deterministic; the attack outcome needs about 3× |
| pack_sneak | SNEAK rating on each hunter's soul (read the skill, not the call's count; trap 15) | time from first approach (≤ 10 tiles) to first attack; kills per approach | pack mass chosen so share ≥ 0.25 for one herd; arms 0 / 0.25 | per approach: approaches are many, so better powered than kills |
| x3 pack bonus | built roster (slots, members) per seed: desk, deterministic | only if the roster differs: predator presence and kills under natural arrivals | desk D1 across the embarks; rig only on a fort whose pool holds the desk's species (BOATS, not CTRL) | — |
| ladder / FREQUENCY | `cr.frequency` per species after the pre and at every sample (CAVERN.apply rewrites daily) | **share of arrivals (waves) by guild** vs f/Σf; apex arrivals | natural gate with the drain, no forced release, 100k t; apex: also log "an LP group present" at each wave (the one-LP rule) | about 40 waves per arm resolves ±0.07 on a 20% share |
| groups at once | **blocked_by** per pass: cap / timer / no gated group / ceiling / DF gate shut (≥ 2 flagged) | L (instantaneous groups), λ, W | section 16.5 | blocked_by is deterministic |
| layer_groups | per-depth and per-body release clocks advancing (ledger) | groups per depth and body | on vs off, BOATS | — |
| gate_drain | count of drained releases; flagged surface units after each release | release-to-wave latency; stalls over 2 days | on vs off, CTRL, natural gate, 100k t | T8g prior: 36 of 154 slow without it |
| hold | countdown of each member | W, L | hold 0 vs 30 days on every arrival | W is near-deterministic |
| cluster size | written raw {n,n} | wave size | done (E12) | — |
| stock | entry quantity per sample | presence of the species' waves; time to exhaustion | done (E3, N1) | — |
| seasons | entry 0/1 by season | out-of-season arrivals | done (S1) | — |
| coupling | exclusion table opened/closed (ledger) | predator wave within 2 d of prey; co-presence-time | done (E10, T4) | — |
| patterns | per-pattern table and gap (ledger) | the pattern's own target (T8 metrics) | T8 series; repeat dawn with more weeks | — |
| ceiling | count per layer vs the ceiling | arrivals after the ceiling is crossed | done (T7b) | — |
| scav | `CACHE.scavLast` per pass, **written even when a pass finds nothing** (trap 21) | corpses cleared per day, and by which species | add the eater's token to the counters | — |
| sweep | `sweep_cleared`, `refought` per pass | off-web kills (a lion killing badgers, LONE natives) | on vs off with **wild** hunters; off-web prey present | validator must walk at least one unit |
| solo package | caste flags and skills on wild solitary hunters | kills per season | LONE10 again with **DF-drawn** cougars (FREQUENCY-steered) | LONE10's 10 seasons per arm were needed for p ≈ 0.02 |
| outgun_cap | `cfg.group_size` of the capped prey | predator losses, prey herd size | CAL-style with capybara or buffalo | — |

---

## 16. Item 16: what holds concurrent groups below √(embark)+1

### 16.1 Every mechanism, and the data that tells them apart

| # | mechanism | vanilla / tool | evidence | data that discriminates |
|---|---|---|---|---|
| 1 | **One surface gate**: DF draws a new surface wave only while ≤ 1 flagged surface unit is on the map, counted across all surface tiles. A gated group of 2 or more blocks every surface source | vanilla | **MEASURED**: E1 (add. 12; hold 2 → nothing in 12,000 t); T8g: 91% of 198 surface waves had ≤ 1 flagged unit left | flagged surface units per sample (units.tsv `flag_src`); whether a wave ever arrives with ≥ 2 flagged |
| 2 | **Per-source cavern gates** (each cave_id its own), weaker rule (64–83%) | vanilla | **MEASURED**: E40 (add. 77); T8g §1 | flagged units per cave_id at each wave |
| 3 | **The tool's release cadence**: one release per jittered gap of 5–20 days (`jitterDays` `:5629-5633`, `nextGap` `:5656-5675`). With the gate shut, λ ≤ 1/(gap + latency) | tool | **MEASURED**: DF's median wave gap is "twelve days" (T8c, add. 89), the tool's mean gap. T8g: release-to-wave median 0.90 days | ledger `wave` lines: release ticks and "gate reopens in X days"; λ against 1/E[gap] |
| 4 | **Residence time W**: per-unit countdown 19,913–29,918 t plus walk-off 367–9,789 t (ground), up to 31,138 t (ravens); stay 22,499–59,068 t | vanilla | **MEASURED**: E9a (add. 10), n = 46 | first-listed to last-listed per group, Kaplan-Meier for censored stays |
| 5 | **Little's law**: L = λW. With λ ≈ 1/16,000 t and W ≈ 33,000 t, L ≈ 2.1, plus the gated group | both | **INFERRED** from 3 and 4. Consistent with T8g: 0.75 waves per 10k and 2.59 at once → W ≈ 34,500 t | L_obs vs λ̂Ŵ per replicate; the arms of 16.5 change λ and W and leave the cap alone |
| 6 | **The cap counts residents and stragglers.** `ENGINE.count` (`:4958-4962`) counts every tracked group with ≥ 1 live member. A flock with one perching raven counts as a whole group (ravens perch for 5–20k t, add. 41) | tool | code; **MEASURED** perching | group size over time; the share of "groups" with 1 member left |
| 7 | **Singleton stall**: releasing a one-animal group leaves a newer group flagged, so the gate stays shut until the next gap. `gate_drain` fixes this in v7.0 | tool (pre-v7) | **MEASURED** at the desk, T8g: 27 of 36 slow releases (p = 5e-6). ECO2-G, G1 and T8 ran before the fix (INFERRED from dates) | releases followed by more than 2 days with ≥ 2 flagged; drained-release ledger lines |
| 8 | **No gated group to release**: `detachOldest` returns nil when DF has not sent one, so the timer is not reset and the gate waits on DF | tool / vanilla | code (`:6181-6182`) | blocked_by = no-gated, per pass |
| 9 | **Supply**: entries at 0 (out of season, inactive, exhausted; `applyLive`/`holdOutOfSeason`). Rotation leaves about a quarter of species in season (preset). N1: an exhausted entry never waves again | tool / vanilla | **MEASURED**: S1, N1 | in-season entries with stock > 0 at each sample (pops, keyed by idx; trap 2) |
| 10 | **One large-predator group per map at a time** | vanilla | **DOCUMENTED** (add. 38; roster prototype in findings) | concurrent LP groups never above 1 |
| 11 | **Wave latency** (DF's own timer once the gate opens): 266–433 t; an open gate always drew within the sample | vanilla | **MEASURED**: E1; T8g §4a (13 of 13) | not a limiter at ≥ 1,000-t resolution |
| 12 | **Layer separation**: no shared ceiling; layers draw independently (all-layer max 12–16 groups) | vanilla | **MEASURED**: T8g §2–4 | n/a; this rules a candidate out |
| 13 | **Departures and refunds**: a walk-off refunds, a death does not (E4), so predation drains stock | vanilla | **MEASURED**: E4, E15 | stock trace (trap 16: nets of debit and refund) |
| 14 | **Map edge and size**: the walk-off is longer on big maps, so W and L rise; the edge has fewer entry tiles on 1x1 | vanilla | **INFERRED** (E9a's walk-off range); ECO2-G implied W by size below | W by embark size at a fixed gap |
| 15 | **Water**: DF never waves rivers, lakes or pools (E20, E26). Water groups are the tool's draws, per body clock, gap 5–20 d, countdown 25,000 ± 20% (`:4936`, `:4944`), and the water ceiling 12 (`:462`, `:5434-5436`) | tool | **MEASURED**: E20; SW6: BOATS supply 2–5 groups | blocked_by per body; ceiling hits |
| 16 | **Cavern clocks**: per depth, gap 5–20 d, halved under irruption pressure (`IRRUPT.gapDays`, `:6073`); natives outside the tool's cap | tool / vanilla | **MEASURED**: SW5 (24–27 groups at auto vs 13.7–16 at caps 1–2); T9c | per-depth blocked_by; native vs tool groups |

Implied W from ECO2-G (L = mean surface groups, λ = surface waves in 40k t; crude, because L includes groups present at
the start). MEASURED inputs from `ECO2-G/20260930-111306/g-tally.json`:

| arm | L (reps) | waves (reps) | implied W, ticks |
|---|---|---|---|
| 1x1 limit 3 | 2.04, 1.91 | 3, 3 | 27k, 25k |
| 1x1 limit 2 | 1.79, 1.75 | 5, 3 | 14k, 23k |
| 4x4 limit 3 | 2.75, 2.68 | 4, 3 | 28k, 36k |
| 5x5 limit 6 | 3.40, 3.16 | 5, 6 | 27k, 21k |
| 6x6 limit 7 | 3.81, 3.12 | 5, 5 | 30k, 25k |
| 6x6 limit 3 | 2.85, 2.54 | 4, 2 | 29k, 51k |

The waves stay around 3–6 per 40k ticks at every limit. That is the release cadence. Raising the cap from 3 to 6–7 adds
waves (5x5: 4 → 5.5; 6x6: 3 → 5) only where 3 was being hit.

### 16.2 The test that tells "cap binds" from "cadence binds"

Two predictions:
- If the **cap** binds, `nLand ≥ cap` at most passes where the timer has run out and a gated group waits.
- If the **cadence** binds, `nLand < cap` and the timer is running.

The tool does not log why a release did not happen. Every pass can compute it from `sw.loadGroups()`, `sw.QUOTA.groupsFor`
and `sw.absTick()` (all exported). Report the share of passes in each blocked_by state. This is deterministic and needs no
replicates to read.

### 16.3 Group identification and counting: the code, tally by tally

**(a) The tool's record**, used by SW3, SW3B, SW5, SW6 and SW7 through `_SW_STATUS` (`eco-run.py:798-803`, `:938-947`).
- **Definition.**
  - `discoverGroups` (`sw.lua:3546-3566`): every 300 t, each **flagged**, untracked, live unit (`gatedLayer`
    `:3511-3518`: roaming flag set, `feature_idx == -1`, not an invader, cave depth ≤ 2) is keyed `race|srcKey`.
  - srcKey = region_x, region_y, feature_idx, cave_id, site_id, population_idx.
  - All fresh units sharing a key in that pass form one group.
  - Water groups are created only by `ENGINE.draw` (`:4941-4943`, `layer='water'`, `body`).
- **Merge.** Two draws of one species from one source within one 300-t pass become one group. This is rare, since a gate
  rarely admits two draws in 300 t. E42b saw two draws of one species from **different** ref6 at once; those stay two
  groups, which is correct.
- **Split.** One draw never splits. A unit whose flag is cleared before discovery is never tracked: `cx-probe release`,
  placement, or the forced-release designs (F1/SW4).
- **Lifetime.** `reconcileGroups` (`:3529-3544`) drops departed and dead members and drops the group only when **all** are
  gone. A group is counted from arrival to the last member's departure, stragglers included.
- **Placed units.** Never tracked on land (no flag). Tool-drawn water units are tracked as water groups. `cx-eco` units
  are never tracked (section 6.2 A).
- **Invaders.** Excluded through `WILD.invader` (`:2763-2774`), and that field is probed, not assumed. **Vermin** are not
  units.
- **Deep.** Never tracked (depth > 2).
- **Count.** Instantaneous: `ENGINE.count` at the sample, at most 300 t stale. Cumulative: only the ledger `arrive` lines.
  `sweep-tally` W counts upward steps (`:84`), which undercounts.
- **Persistence.** g.groups lives in site data, so it is inherited across cells of one load (section 6.2 D).

**(b) ECO2-G / G1 live scan.** There are two stages:
- **Online** (`experiments/ECO2-G.json` `every`):
  - Key `race:population_idx` among `isWildlife`, live, not inactive.
  - surface = `cave_id == -1 and feature_idx == -1`.
  - cavern = `cave_id ≠ -1`. **This includes the magma sea and the underworld.**
- **Offline** (`eco-g-tally.py:9-13`):
  - Key (species, ref6) among wild, alive, active rows of `units.tsv`.
  - Layer from `cx-probe layer_of` (`cx-probe.lua:88-96`: feature / cavern / deep / surface).
  - surface and cavern are tallied; deep and feature are left out.

Properties of (b):
- **Merge.** Successive waves of one species from one source that are present together (a resident plus a new gated
  wave) collapse into one group. This is common where one species dominates the supply (N1: wombats 25 of 26 waves; F1:
  kangaroo 60%). It undercounts L, and it does so most at high λ.
- **Split.** Only across ref6 (two tiles drawing the same species).
- **Placed units.** Counted: `cx-eco spawn` gives them a population ref (`cx-eco.lua:343-381`; it **borrows** another
  species' ref when the species has none).
- **Tool water draws.** Counted under whatever layer their population ref gives.
- **Invaders.** Not filtered by invasion_id (only `isWildlife`, documented as "surface or cavern wildlife").
- **Count.** Instantaneous only.

**(c) T8g** (`t8g-analyze.py:96-108`, `:153-182`).
- **Definition.** A wave = arrivals of one species from one source (cave id level) first listed at one sample. Units
  present at the start are grouped by (source, species, ref6).
- **Merge.** Two draws of one species in one sample interval (E42b; trap 11).
- **Split.** A draw whose units are first listed across two samples (a unit listed inactive at the edge for one sample;
  E9a).
- **Unknown units.** Units with no wave (born, placed) collapse into one '?' group per source and species.
- **Count.** Instantaneous groups per sample; cumulative waves per 10k.

**Corroboration across three sources** (never done so far). For each arrival, three things should agree:
1. The tool's new group, from the ledger `arrive TOKEN xN` and g.groups.
2. A run of consecutive unit ids of one species from one ref6 first listed at a sample (units.tsv).
3. A debit of N on that ref6's population entry. This is exact for entries under ~30 (E15/F15); raven-sized entries
   debit irregularly.

Mismatches to flag:
- A group with no debit: placement or misattribution.
- A debit with no group: an unflagged arrival, or a flag cleared before discovery.
- One debit and two groups: a split.
- Two debits and one group: a merge.

### 16.4 What was run, per layer, exactly

| run | fort(s) | land | water | caverns | deep | limit varied |
|---|---|---|---|---|---|---|
| ECO-G1 | FPS2E4 (4x4), FPS2E6 (6x6) at region4 29,20 SHRUBLAND_TEMPERATE | yes | none on map | not reported | no | land 3 vs 5, 3 vs 7; **1 rep** |
| ECO2-G (20260930-111306) | FPS2E1–E6 (1x1–6x6), same tile | yes | none on map | pooled 3 caverns (online scan also counted deep as cavern) | g-tally excludes it | land 3 vs √+1; cavern 2 in both arms (**not varied**) |
| SW3 (uninformative), SW3B | CTRL 4x4 (region4 29,20) | yes | none | recorded, not varied (v7 default auto per cavern) | no | land 1 / 3 / auto |
| SW5 | BOATS | – | – | depths 0, 1, 2 per cavern | receipt only | cavern 1 / 2 / auto per cavern |
| SW6 | BOATS | – | ocean and river only (lake 0, pool 0) | – | – | water 1 / 2 / auto per body |
| SW7 | CTRL | yes (not a limit test) | – | – | – | – |
| T8–T8f (observational) | CTRL | yes, cap 4 | none | per cave id, cap 2 | magma sea and underworld observed | no |

**Never run:**
- Land on any other biome (savage, good, evil, ocean-shore, lake, river forts).
- The lake and pool bodies.
- OCEAN2, LAKE and RIVER4 water.
- Caverns on CTRL with the limit varied.
- Deep (the tool cannot touch it).
- layer_groups on against off.
- Anything with gate_drain receipted.
- The 1x1–3x3 cavern limit.

### 16.5 The re-run: per layer, instantaneous and cumulative, three-source

**Forts and layers.**

| fort | layers |
|---|---|
| CTRL | land, caverns 1–3, deep observed |
| BOATS | land, ocean, river, caverns 1–3 |
| OCEAN2 | ocean |
| LAKE | lake (river present; report it) |
| RIVER4 | river |

There is no pool fort: survey for one. On the 1x1 programme, the same design runs per biome fort (section 10).

**Run discipline.**
- One fresh load per replicate (cx-experiment).
- DF restarted per run.
- Arm order a Latin square across reps.
- Start tick fixed (same season).
- `cx-load sustain` every sample.
- 60,000 t, sampled every 1,500 t.
- The first sample is listed, not scored. Scoring starts after a W/2 burn-in (15k t).

**Arms (2 reps each; four arms keep it to the user's pace).**

| arm | cap | gap (days) | prediction under Little's law |
|---|---|---|---|
| A control | auto | 5–20 | L ≈ λW ≈ 2–3 |
| B uncapped | 99 | 5–20 | L ≈ A (the cap does not bind) |
| C fast | 99 | 1–2 | L rises until DF's gate or supply binds (λ ×6) |
| D tight | 1 | 5–20 | L < A |
| (optional) E hold | auto | 5–20, plus hold 30 d on each arrival | W ↑ → L ↑ until the cap binds |

The gap is set through a pre-step cfg write of `groups.gap_min_days` / `gap_max_days`; there is no CLI verb (SWEEP §0).
For water and caverns, the same arms apply to the per-body and per-depth limits.

**Every sample prints:**
1. The tool's groups (id list, token, layer, body, depth, resident, arrived, member count) and the ledger `arrive` and
   `wave` lines.
2. `cx-probe units` (all wild units, flags, ref6, countdown, inactive), with the tool's layer and the harness's layer
   both written.
3. `cx-probe pops` for every managed entry, keyed by idx.
4. blocked_by per layer, body and depth, plus `next_wave_tick`, the flagged count per source, the cap, and drained
   releases.
5. A receipt from inside the job: limits, gap and gate_drain as the scheduled copy sees them (memory
   dfhack-script-copies).

**Outcomes per layer, body and depth.**
- G_inst = distinct groups with ≥ 1 live, active member, under all three definitions, side by side.
- G_eff = groups with ≥ 2 members or ≥ 50% of their arrival size.
- G_cum = distinct groups ever present.
- λ = new groups per 10k ticks.
- W = Kaplan-Meier stay per group.
- The L vs λW check.
- The blocked_by shares.
- Mismatches from the three-source reconciliation.

**Decision.**
- If B ≈ A, C ≫ A and blocked_by is mostly "timer", then the gap is the dial for "more groups at once". The default
  should change there (for example 3–8 days), not in the cap.
- If B > A, the cap binds; keep auto.

**Time.** Rates are per replicate: CTRL ~7 min at 60k t, BOATS ~8 min, the water forts ~6 min.

| fort | arms × reps | time |
|---|---|---|
| CTRL | 4 × 2 | ≈ 56 min |
| BOATS | 4 × 2 | ≈ 64 min |
| OCEAN2, LAKE, RIVER4 | 3 arms (A/B/C) × 2 | ≈ 36 min each |
| restarts | | ≈ 10 min |
| **total** | | **≈ 4.6 h** |

Run it on DFHack r2 only, after the re-validation (open item revalidate-dfhack-r2).

---

## 10. Item 10: the 1x1-per-biome test-fort programme

### 10.1 Listing a world's distinct biomes

- **Tool.** `cx-lifecycle.sh survey <world> [filter]` → `cx-embark survey` (`cx-embark.lua:120-170`).
- **What it prints.** One row per region tile: biome (`getBiomeType`), river, brook and major-river flags, lake,
  site, savagery, evilness, elevation, volcanism, `same8` (neighbours of the same biome), neighbouring river and ocean
  counts, and volcano.
- **Rivers.** `cx-embark rivers` (`:101-118`) prints each river tile's up, down, left and right flags.
- **region6 is already on disk.** `data/forts/region6-survey.tsv` covers seed 424242, SMALLER 33×33, 1,089 tiles.
  - **23 distinct biomes.**
  - Ocean: 139 tiles. Lake tiles: 5. Major-river tiles: 469.
  - Savage (≥ 66): 542. Good (evilness < 33): 40, all TUNDRA bar one. Evil (≥ 66): 74.
  - Calm (< 33): only 22, all MOUNTAIN.
  - (MEASURED from the TSV. Thresholds as the tool's `V7.alignment`, `sw.lua:1100-1104`.)
- **Biomes a region tile can carry but region6 lacks** (INFERRED from DF's `biome_type` enum; region tiles never take
  POOL_, RIVER_ or SUBTERRANEAN_ types):
  - DESERT_SAND
  - GRASSLAND_TROPICAL
  - FOREST_TROPICAL_DRY_BROADLEAF
  - SWAMP_MANGROVE
  - the temperate swamps and marshes
  - the brackish and saline lakes
  - a tropical saltwater swamp

  A second, larger world would be needed for full coverage (10.6 step 5).

### 10.2 Guaranteeing OCEAN, LAKE, RIVER, SAVAGE, GOOD and EVIL

region6 already holds all six. Candidate tiles from the survey (interior `same8 = 8` where possible, no site):

| need | tile | biome | notes |
|---|---|---|---|
| OCEAN | coast next to 1,11–2,13 (OCEAN_TEMPERATE, s8 = 8, sav 85–94), or 4,28 (OCEAN2's tile, offset 0,6) | OCEAN_* | a 1x1 wholly in ocean leaves the dwarves no land: place it on the shoreline so water and land share the 48×48 (INFERRED; check that the wagon lands) |
| LAKE | 12,27 / 12,28 (LAKE_TROPICAL_FRESHWATER, s8 = 2) | lake | lakes are 1–4 tiles here; the LAKE fort's river confound means the 1x1 must sit on lake water away from the inflow; check `ENGINE.waterTiles` body = lake, river = 0. Lakes are shallow (DEPTHL: 91% one level deep) |
| RIVER | 16,23 (RIVER4's tile, SHRUBLAND_TEMPERATE, s8 = 8, sav 42), 19,31, 16,26 | major river | use `cx-embark rivers` and place across the exit edge's midpoint (df-worldgen skill: offset 6,12 caught a southward exit). Prove the channel with a flood fill (`data/forts/water-proof`) |
| SAVAGE | 31,12 / 30,14 (MOUNTAIN, sav 89–92); for a non-mountain, FOREST_TEMPERATE_CONIFER sav ≥ 66 | — | most of region6 is savage; the contrast needs a **calm** fort, and only MOUNTAIN 31,26 (sav 29) qualifies |
| GOOD | 9,2 / 11,2 (TUNDRA, evil 2, **sav 79–87**); GOODF used 11,1 | — | good and savage confounded |
| EVIL | 10,5 / 8,5 (SHRUBLAND_TEMPERATE, evil 94–98, **sav 85**); EVILF used 7,5 | — | evil and savage confounded |

To break the confounds (a calm GOOD, a calm EVIL, a temperate lake, a tidal saltwater marsh), use a **seed search**.
Generate SMALLER worlds (~30 s each, plus a ~10 s survey) and accept the first seed with all of:
- an interior calm tile with evilness < 33;
- one with evilness ≥ 66;
- a lake of 2 or more tiles;
- an ocean coast.

Worldgen parameters could raise good, evil or savage region counts, but this rig has not verified which preset fields do
that. `cx-embark params` edits only seeds, title and end year (INFERRED; read `vs.worldgen_presets[0]` fields before
relying on them). Note that DF crashed in 2 of 4 generations of one pilot world (`fps6-run.py:127-128`): retry on a fresh
DF.

**Single-biome purity.** DF draws from every region tile that a block's `region_offset` names (memory
df-region-draw-tiles, X1).
- Use interior tiles and a centred 1x1: offset 7,7 inside the tile's 16×16.
- Record the 9-offset union (`getEmbarkRegions`) in each fort's facts.
- A fort whose union holds a second biome is labelled mixed.

### 10.3 What 1x1 changes against the current 3x3–6x6 forts

| aspect | 1x1 | evidence |
|---|---|---|
| groups at once (auto) | ⌊√1⌋+1 = **2** per layer, water body and cavern (`QUOTA.autoGroups`, `:2849-2854`) | ECO2-G 1x1: 1.77–1.79 groups at limit 2 vs 1.91–2.04 at 3 (MEASURED) |
| arrivals | 3–5 surface waves per 40k t, the same as bigger maps (the cadence binds) | ECO2-G (MEASURED) |
| units on the map | surface 2–9.5 (vs 6–18 on 4x4–6x6), so fewer encounters | ECO2-G g-tally (MEASURED) |
| walk-off, W | shorter (48 tiles to an edge), so a lower L | INFERRED; implied W 14–27k on 1x1 vs 21–51k on bigger maps (16.1) |
| map edge | 188 surface edge tiles vs 764 on 4x4 | geometry |
| caverns | present at CTRL's tile: about 3 cavern groups and 14–16 units on 1x1 | ECO2-G (MEASURED); must be checked per fort (CAVE.survey) |
| draw tiles | 1 to 9 region tiles: a narrow pool, so builder slots stay unfilled | memory df-region-draw-tiles |
| water | a 1x1 may hold little or no water; the PE slot needs a column 3+ levels deep (OCEAN2 had 0 of 5,374) | S8O (MEASURED) |
| thirst | 7 dwarves on a dry tile wither by about 190k t; on salt water too | memory fort-load-levers (MEASURED); use `cx-load sustain` everywhere |
| speed | 465–549 t/s vs 393–442 (4x4) and 220–264 (6x6) | ECO2-G (MEASURED) |
| arena geometry | 45–60-tile separations impossible; nudge far_tiles 40 is almost never exceeded (Chebyshev max 47) | geometry |

### 10.4 Which existing experiments transfer

- **Transfer as designed:**
  - natural-arrival counts (G, SW3B, and the 16.5 re-run) with auto = 2;
  - FREQUENCY share (F1, SW4) under the natural gate;
  - relation-write arenas at ≤ 10 tiles (P1, CAL, TV2, HC);
  - scavenging (SCV2b);
  - seasons (S1, N1);
  - water draws (S8O-style) where water exists;
  - alignment (Item 6 GOODF/EVILF).
- **Transfer with rescaled metrics:**
  - cohesion (COH). Unled spreads of 113–140 tiles cannot occur on a 48-tile map, so score spread as a share of the map
    width;
  - LONE10, where 48 placed prey crowd the map: halve them.
- **Do not transfer:**
  - the SW1 nudge arena and E18 nudge thresholds;
  - the FPS series (1x1 is atypical for load);
  - CTRL-specific facts (no animal people, the dry tile).
- **Need a survey first:** cavern invasion and irruption (E23, T9). They need animal-people populations in reach of each
  1x1 (memory ctrl-fort-facts).

### 10.5 Naming and archiving (the shared-world-name trap)

- **Worlds.** Keep one world per seed in the save directory. Same-seed worlds share a display name, and opening by name
  picks the first one listed (memory embark-hover-and-world-names).
  - Archive with `archive_world` (`fps6-run.py:110-119`) as `W<seed>-<preset>-<YYYYMMDD>`; DF reuses `regionN`.
  - After every embark, check `world_data.world_width` and `cur_year`.
  - region4 and region5 (CTRL, SPLIT) are both seed "text→0", the same world: move one out before generating there.
- **Forts.** `B1-<seedtag>-<BIOME>-<rx>_<ry>`, for example `B1-R6-OCNT-01_12`, `B1-R6-LAKE-12_27`. B1 means 1x1;
  seedtag R6 means region6/424242.
  - Biome codes are four letters: OCNT/OCNP/OCNA, LKTF, MNTN, GLAC, TNDR, SHTM, SHTR, FTCN, FTBL, FTMB, FTTC, TAIG, GRTM,
    SVTM, SVTR, DSBD, DSRK, MRTF, MRTS, SWTF.
  - Suffix `-SAV` / `-CALM` / `-GOOD` / `-EVIL` / `-RIV` where that is the reason for the fort.
- **Backups.** `<save>.preverify` for each.
- **Registry.** `data/forts/b1-forts.tsv`, one row per fort, holding:
  - save, world folder, seed, preset, rx, ry, offset;
  - biome, sav, evil, river, lake;
  - the 9-offset union of region tiles and its biomes;
  - water tiles by body, deep columns, cavern depths present;
  - population counts by layer, animal-people populations;
  - load t/s and the embark wall time;
  - the `cx-lifecycle facts` output saved beside it.

### 10.6 Order of work, with time estimates

| step | where | time |
|---|---|---|
| 0. DFHack r2 re-validation (open item; blocks every new run) | rig | per that item |
| 1. Pick the tiles from region6-survey.tsv (done in 10.2 for the six); write the registry skeleton and the 1x1 manifest template (16.5 design, auto = 2) | desk | 45 min |
| 2. Check that region6 is the only seed-424242 world; `cx-embark rivers`; check the shoreline and lake placements in the site screen's `read` | rig | 15 min |
| 3. Embark the six required 1x1 forts (`CX_EMBARK_SIZE=1`, `cx-lifecycle.sh:581-611`; ~90 s each plus facts and preverify, about 4 min each). Check each for water by body, the region union, caverns and alignment | rig | 30 min |
| 4. Embark the remaining 17 region6 biomes as 1x1 (at 4 min each) | rig | 70 min |
| 5. (optional) Seed search for calm GOOD and EVIL, a temperate lake and the missing biomes: SMALLER worlds about 40 s per seed for gen plus survey, 10–20 seeds, then embark about 8 forts | rig | 60–90 min |
| 6. Baseline per fort: tool on, preset, natural arrivals, 50,400 t, 2 reps, three-source group logging (16.5). About 500 t/s → ~100 s stepping plus ~3 min overhead → ~5 min per rep, 10 min per fort | rig | 23 forts ≈ 4 h (plus 8 ≈ 1.3 h) |
| 7. Tally: per-biome L, λ, W, groups by layer, species pool; feed the roster-builder slots | desk | 1 h |

**Total:** about 1.75 h at the desk and 6–7 h on the rig for region6 alone (8–9 h with the seed search).

Run the six required forts first (steps 2–3, then step 6 on those six, ≈ 1.5 h). They answer the user's named cases
before the full set is built.

---

## Appendix: open checks this desk pass could not close

- **Placed pairs in the arena** (6.2 B): replay one SW2 cell and print `g.ecology.small` and the rel_map cells for the
  placed wolf × buffalo and wolf × elephant pairs. This confirms that ctl refused them.
- **Wild-placed units** (6.3 rule 4): does setting the roaming flag on a `cx-eco spawn` unit stop DF aiming it, and does
  it hold the surface gate? This needs a pilot (RELS method).
- **Tool-drawn water units' population refs.** `ENGINE.candidates` takes only managed pops with layer 'water', that is
  feature-indexed entries (`:4839-4846`, `:2341-2356`, `:900-905`), yet F14 says ocean life has no feature index.
  - Dump the ref6 of a drawn ocean group on BOATS.
  - `WILD.layerOf` decides whether these units count against the water ceiling and in harness layer tallies.
  - SW6's t0 receipt read `water=5` in all 6 cells, while the tool's water groups ran 1–5. This is suggestive, not
    conclusive.
- **Newborn wild units**: do they carry the roaming flag? If they do, `discoverGroups` makes each one a new group.
  - E19 saw no births among held grazers.
  - RIVER4 had two carp born, both CHILD (STATE add. 35).
  - Check `flag_src` on any unit with `mother ≥ 0` in units.tsv.
