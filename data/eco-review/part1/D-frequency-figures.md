# D: FREQUENCY, the trophic pyramid, and figures 11, 15, 17, 18, 19

Desk research for review Part 1, items 4, 11 (data only), 15, 17, 18 and 19. Written 1 Oct 2026 by W2:Urist's desk researcher.
I did not use the rig, made no commits, and left the report sources unedited. I tested every figure fix on a scratchpad copy:
`/private/tmp/claude-501/-Users-nathanielcannon-Claude-Projects-DwarfCron/6c601b1a-073b-42c6-a27d-44f793ddcd7d/scratchpad/fig-diag/`
(called SCRATCH below). It holds the copied sources, `patch_exp.py`, `harness.py`, `shot.sh`, the diffs and before/after
screenshots in `shots/`.

---

## 0. Headlines

1. **FREQUENCY works on apexes. The ladder simply asks for very few of them.** Each built ladder gives the apex 6–8% of the
   non-flier land weight. DF sends about 6–15 non-flier land waves a season, so the model expects about 0.4–1.2 apex waves per
   season. The S8 runs got 0, 0, 0, 3, 2 and 1 apex waves (AL guild). That is the expected count, not a failure (§1.3).
2. **On CTRL, large predators compete with prey in the same draw.** The wiki says otherwise. Re-tallying X3: with kangaroo at
   f100, LARGE_PREDATOR waves were 1 of 71 non-flier waves; with every species at f ≤ 4 they were 7 of 57 (Fisher one-sided
   p = 0.014). In T2, with everything at equal f, they were 4/24, 7/24 and 4/16. F1 and N1 (kangaroo f100) had 0 (§1.3b).
   This answers open item `lp-separate-pool` provisionally. The proposed dose test (§1.4) confirms or overturns it.
3. **Do not drop the apex step; re-target it.** Set the apex weight from a presence target: an apex on the map about a quarter
   of the time, which is 1–2 visits a season. Below that, apexes stay as rare as they are now (§2.4).
4. **Pyramid:** target the time-averaged **numbers** on the map (units present), with an upright-biomass guard on land and in
   the caverns. Water may invert. A literal 10% step would leave an apex on the map about 3% of the time, which is what players
   already see. Proposed steps are ¼ on land, ⅕ in water and ⅓ in the caverns (§2).
5. **Units, not waves (resolved):** the ladder should target units. Divide each species' weight by its expected group size,
   (CLUSTER_NUMBER min + max)/2. On the rig that predictor matches the observed mean group size: kangaroo 3.11 vs 3.0,
   troglodyte 7.51 vs 7.5, wolf 4.79 vs 5.0, crundle 16.7 vs 17.5. The apex level is the exception: it is set by visits (§3).
6. **Figures:** one renderer convention broke **eight** figures, including 18 and 19. Categorical forms read `x` as the
   category, and eight specs were written value-first, so every mark became NaN and the frame came out empty. Figure 17's
   reference line is a tick value (2,400) drawn on the y axis, which stretched the axis to 2,400. Figure 15 sat in a ~490-px
   gallery cell, so 75 columns of 4-px cells were overprinted with 10.5-px numbers. All are fixed and rendered headless (§4).

---

## 1. Item 4: what FREQUENCY does, and why the apex step "doesn't bring apexes"

### 1.1 What DF does with FREQUENCY (wiki, verified 1 Oct)

- **Range and default.** The argument is "number, max 100" and "Defaults to 50 if not specified". The wiki calls it "a
  comparative number": with three creatures at 10/25/50, the one at 50 "will appear approximately 58.8% of the time"
  ([Creature token](https://dwarffortresswiki.org/index.php/Creature_token),
  [DF2014:Creature token](https://dwarffortresswiki.org/index.php/DF2014:Creature_token)).
- **Two roles.**
  - **Worldgen territory.** Each creature gets an epicenter with a Manhattan radius of FREQUENCY/100 × the world size. The
    lion's f5 gives about 13 tiles on a 256 map.
  - **On-map pick.** DF picks a creature at random from the sub-region's list and "effectively rolls a d100 against the
    relevant creature's [FREQUENCY]"; on failure it picks again. Under that rule a species' share is fᵢ/Σf over the eligible
    list.
  - A runtime write cannot change territory, because worldgen is over. The tool only ever acts on the on-map pick. The builder
    seats only `e.inEmbark` species, so a seated species is already in the region's list.
- **Lists.** There are five lists: VERMIN_GROUNDER, VERMIN_SOIL, VERMIN_SOIL_COLONY, LARGE_ROAMING and LARGE_PREDATOR, with
  seven creatures per list per sub-region. The current wiki adds that waves are "split by type (roaming, roaming fliers,
  predators, curious beasts), so a lion does not compete for selection with a gazelle". It also says only one large-predator
  group appears per map, two on savage maps ([Creature token](https://dwarffortresswiki.org/index.php/Creature_token),
  LARGE_PREDATOR).
- **Related tokens.** UBIQUITOUS "acts as [FREQUENCY:100]" for the territory and pick logic. Our T2 run found it ignored at the
  fortress pick at run time (`data/eco-desk/findings.md:67-71`). CLUSTER_NUMBER defaults to 1:1. POPULATION_NUMBER is the total
  that can ever visit (deer 15:30) ([Creature](https://dwarffortresswiki.org/index.php/Creature)).

### 1.2 What our data says at the values tried

| run | setting | result | source |
|---|---|---|---|
| E34 | 7 cavern species at f **0** | 0 arrivals over two suppressed half-seasons; back when restored | seasonal-wildlife `STATE.md:2047` (addendum 53) |
| addendum 54 | CREEPY_CRAWLER at f 0 | **freezes DF**; f 1 is safe. Hence "never 0": `CAVERN.SUPPRESSED = 1` and `CAVERN.write` clamps to ≥ 1 | `STATE.md:2119`; `seasonal-wildlife.lua:2950-2957, 2974-2981` |
| E36 | cavern pair at 100:25 vs 4:1 | pair 20.5 → 0 waves, total −9%: a comparative weight on a shared budget | `STATE.md:2179-2232` |
| E21b | 5 common cavern species at 100 vs 1 | the five fell 85% but still came (f1 is a bias, not a gate); layer volume −44% | `STATE.md:2235-2290` |
| F1 | kangaroo/porcupine/wombat/emu/badger = 100/50/25/12/1 | 60.5 / 23.7 / 13.2 / 0 / 2.6% of non-bird waves vs f/Σf 53.5 / 26.7 / 13.4 / 6.4 / 0.5% | `findings.md:50-53` |
| X3 | kangaroo:porcupine 100:25 vs 4:1, all else f1 | pair took 80 / 70% vs 23 / 24% of surface waves | `STATE.md:3874`; `data/experiments/X3/20260926-212003/tally.txt` |
| ECO2-FC | cavern species 100 / 50 / 25 / 12 vs 1 | per depth, 55 / 26 / 18% vs predicted 57 / 29 / 14%. DF picks the cavern depth first (49 / 49 / 45 waves), then the species within it | `findings.md:160-166` |
| ECO2-W, T2 | NO_WINTER / NO_SPRING on an f100 species | 0 of 42 and 0 of 44; 0 of 19. The season flag beats any FREQUENCY | `findings.md:192-195, 67-69` |
| N1 | kangaroo f100, entry quantity 3 → 0 | no kangaroo after the entry hit 0. Quantity gates, FREQUENCY cannot override | figure `n1-exhaustion-replacement` |
| SW4 | land predator f ×0.5 / ×1 / ×2 (AL f 4-8) | predators present 1.8–1.9% / 10.6–14.0% / 6.9–20.1%; apex present in 1 of 6 runs | `findings.md:469-476` |
| S8B/S8O/S8Cb | built ladders (apex f 13–27) | apex waves 0, 0 (CTRL); 0, 3 (BOATS); 2, 1 (OCEAN2) | `scripts/s8-tally.py` on the three runs (§1.3) |

FREQUENCY steers composition in proportion to f/Σf: on the surface (F1, X3), per cavern depth (ECO2-FC), and underground
generally (E36). It does not set volume (E36/E21b). Season flags and stock gate it outright (ECO2-W, T2, N1).

### 1.3 Why "the apex FREQUENCY doesn't bring apexes"

I re-tallied the existing runs. No new rig time was used.

**(a) The built ladders ask for few apexes.** Here is each S8 land ladder's apex share of non-flier weight, from the
`s8 build land` receipts in each `log.txt`:

| run | apex (f) | apex / Σf of non-flier roster | non-flier land waves in the season | expected apex waves | observed AL waves |
|---|---|---|---|---|---|
| S8Cb CTRL r1 | COUGAR 14 | 7.5% | ~6 (11 surface − 3 raven − 2 kestrel) | ~0.45 | 0 |
| S8Cb CTRL r2 | COUGAR 14 | 7.4% | ~7 | ~0.5 | 0 |
| S8B BOATS r1 | CHEETAH 13 | 5.7% | ~16 | ~0.9 | 0 |
| S8B BOATS r2 | CHEETAH 27 | 7.8% | ~17 | ~1.3 | 3 |
| S8O OCEAN2 r1 | ANACONDA 27 | 7.6% | ~12 | ~0.9 | 2 |
| S8O OCEAN2 r2 | ANACONDA 15 | 6.2% | ~12 | ~0.7 | 1 |

The model expects about 4.8 apex waves summed over the six runs, and 6 were seen. Under a Poisson model, P(0) for a CTRL run is
about 0.6, so 0 and 0 there is unremarkable. The S8 surface tallies (waves per guild, e.g. "AL 3/3", "AL 2/2") come from
`python3 scripts/s8-tally.py data/experiments/{S8C/20261001-062036,S8B/20261001-020551,S8O/20261001-022543}`.

SW4 is the same story. It set al_f=4 on six AL species against GZ×6, PL×8 and LB×2 (`SW4.tsv` swladder `phase=set` rows).
At design.md §5's 50/40/40 values, AL is 24/748 = 3.2% of the weight, or about 1 apex wave in a 60,000 t run at ×1.

**(b) LARGE_PREDATOR competes with prey in the same pick on CTRL.** I counted LARGE_PREDATOR (species2.tsv `lp=1`) and
FLIER per wave from each run's `waves.tsv`:

| run | prey weights | LP waves / non-flier waves |
|---|---|---|
| X3 high r1, r2 | kangaroo 100, porcupine 25, rest 1 | 0/37, 1/34 |
| X3 low r1, r2 | kangaroo 4, porcupine 1, rest 1 | 4/29, 3/28 |
| T2 nospring_KANGAROO | kangaroo out of season, rest 1 | 4/24 (DINGO 2, COUGAR 2) |
| T2 ubiq_PORCUPINE / ubiq_WOMBAT | rest 25 | 7/24, 4/16 (COUGAR, WOLF, DINGO) |
| F1, N1 | kangaroo 100 | 0/38, 0/28 |

High vs low in X3 gives Fisher one-sided p = 0.014. If LPs had their own wave type with its own cadence, raising the kangaroo
could not suppress them. So on CTRL the data favour one weighted pick in which LPs take their f/Σf.

Fliers were also 7–9 waves in X3 high against 18–23 in low, which bears on open item `flier-pool-steering`. The
wiki's split-by-type sentence may describe the wave *categories* (and the one-LP-group cap) rather than separate weighted
lists. The dose test in §1.4 settles it either way.

**(c) Group size cuts the apex's unit share.** Apexes arrive alone: the rig's mean wave size is COUGAR 1.54 and the raw
CLUSTER_NUMBER for CHEETAH and ANACONDA is 1:1. Their prey arrive in groups of 2.5–8, and ravens in groups of 6. So the
apex's unit share is ⅓–⅕ of its wave share. That is why the S8 tallies show "apex 0–3 units".

**(d) Other things that bound apexes, none of which explains the S8 zeros:**

- The one-LP-group-per-map cap (two on savage maps) limits concurrency. It only binds once apex visits approach one per
  residence time, about 21,500 t (the median leave countdown at arrival is 21,401 t for LPs and 21,630 t for roamers, over
  658 and 1,764 waves).
- Stock (POPULATION_NUMBER). CTRL's COUGAR entries hold quantity 2 each across several region tiles (S8Cb `pops.tsv`), so the
  draw is not exhausted. Killing them does exhaust it (N1).
- Biome and season eligibility: COUGAR carries all four seasons.
- The cavern LP natives (jabberer, troll, troglodyte) are on the map throughout CTRL's season. COUGAR still arrived in T2 with
  them present, so they do not block a surface LP group.

**Conclusion.** "The apex FREQUENCY doesn't bring apexes" is a calibration result, not a mechanism failure. The ladder writes
apex ≈ 7% of weight by design (R13: v2.1 apex 3 vs grazer 6 and prey 5). In a layer that gets about 10 land waves a season,
that is under one apex visit. Open item `ladder-drop-apx-step` should be **rejected**; re-target the step as in §2.4. Open
item `lp-separate-pool` is answered provisionally: shared pick on CTRL.

### 1.4 The incremental FREQUENCY test (FQ1): design

**Question.** How does an apex's share of land waves, units and presence respond to its FREQUENCY over the full range 1–100,
against a fixed competitor set? Is it f/(f+M) (shared pick), flat (separate LP pool), or flat above some f (the one-group
cap)?

**Fort: CTRL** (`CTRL.preverify`, spring of year 2, tick 16,800; ~180 t/s).
- F1, X3, T2, N1 and S8Cb all ran here, so the competitors' behaviour is known.
- Its land pool holds three LPs (COUGAR, WOLF, DINGO) and the four competitors below, all seen arriving.
- It has no water layer to confound the result.

**Subject: COUGAR.** It is LARGE_PREDATOR, AL guild, CLUSTER 1:1 (rig mean 1.54), carries all four seasons, has raw f5,
arrived 2–3 times per T2 run, and has stock 2 per entry.

**Competitors.** KANGAROO, PORCUPINE, WOMBAT and BIRD_EMU at **f 25** each, so **M = 100**. All four are non-LP, carry all
four seasons and are in CTRL's pool. Every other land species, including WOLF and DINGO, gets entry quantity 0, which gates
them (N1). Fliers are left native and reported separately (they are CTRL's ravens).

**Arms.** f_apex ∈ {1, 2, 5, 10, 25, 50, 75, 100}. Never 0 (addendum 54's rule is kept even on the surface).

**Phases** (2 replicates per arm; each run restores the save, as in X3):

| phase | what varies | tool | ticks | runs | rig time |
|---|---|---|---|---|---|
| A: dose | 8 f levels | **off** (harness writes f and quantities; surface released every 1,500 t, as in F1/X3) | 60,000 | 16 | 16 × ~6.3 min (X3: 336 s run + ~40 s load) ≈ **1.7 h** |
| B: tool on | f 5 / 25 / 100 | **on** (land gate √+1, stop list, `cfg.odds.COUGAR = f`, CAVERN.apply rewriting daily), natural cadence | 100,800 (one season) | 6 | 6 × ~10 min ≈ **1.0 h** |
| C: season | f 50; season set at load (as ECO2-W) to Sp/Su/Au/Wi | off, released | 60,000 | 8 | ≈ **0.85 h** |

Total **≈ 3.6 h**. A paced variant drops to 6 levels (1, 5, 10, 25, 50, 100) in A and 2 seasons in C, for about 2.4 h.
Restart DF between phases, since 16 × 60k = 960k ticks and one process loses ~28% fps by 300k ticks (memory
`fps-load-facts.md`). Time runs with the stopwatch, not step wall time.

**Counterbalance.** Rep 1 runs ascending f, rep 2 descending. In phase B rep 2 is also reversed. Phase C rep 2 runs Wi→Sp.

**Outcomes.** Each run reports:
- **primary:** cougar waves / non-flier surface waves;
- cougar units / non-flier units;
- **presence:** the fraction of 1,500-t samples with ≥ 1 cougar on the map;
- time to first cougar wave;
- each competitor's share (to fit M_eff).

Phase B adds apex visits per natural season. Phase C reports everything per season.

**Subject receipt.** All of these are printed into the TSV:
- at t0, after the pre write: `cr.frequency` for COUGAR and the four competitors, and Σ quantity of COUGAR's entries (> 0);
- WOLF / DINGO / others at quantity 0;
- `NO_<season>` absent on COUGAR for the run's season;
- tool state (the `tool state ok` line);
- a re-read after the first sample, because first-sample draws race the pre's write (memory `experiment-readout-traps.md`).

Waves listed at the first sample are excluded. A run with no cougar wave is **censored data (0)**, not missing. At the end,
`cr.frequency` is re-read (phase B: it must equal the arm, proving CAVERN.apply held it).

**Predictions** (M = 100, about 32 non-flier waves per 60k released run):

| f | 1 | 2 | 5 | 10 | 25 | 50 | 75 | 100 |
|---|---|---|---|---|---|---|---|---|
| shared pick p = f/(f+100) | 1.0% | 2.0% | 4.8% | 9.1% | 20% | 33% | 43% | 50% |
| expected cougar waves per run | 0.3 | 0.6 | 1.5 | 2.9 | 6.4 | 10.7 | 13.7 | 16 |

- **Separate pool:** a flat count at every f ≥ 1, independent of M.
- **One-group cap binding:** cougar waves plateau near run length / residence (60,000/21,500 ≈ 3 per run unless the
  release removes it) while presence → ~100%.

**Analysis.** Fit a binomial GLM, waves_apex ~ Bin(n_nonflier, f/(f+M_eff)), by maximum likelihood over the 16 runs. Compare
it against the flat model (LR test) and the capped model.

**Decision rule:**
- M_eff within ×2 of 100 and a monotone curve → the ladder math in §2.4 holds for LPs.
- Flat → drop the LP weight and steer apexes by placement (open item `apex-placement-stock-test`).
- Plateau → the presence target is capped at one group, and apex f above the plateau is wasted.

**Optional (+0.6 h).** Repeat phase A at f 5 / 25 / 100 with WOLF (CLUSTER 3:7, rig mean 4.79) as the subject. It tests
whether unit share = wave share × g holds for a pack, which is the units-vs-waves rule in §3.

---

## 2. Item 4: the trophic pyramid as a target for the tool

### 2.1 Which pyramid is meaningful for DF waves

- **Energy.** DF has no energy flow: animals neither grow nor reproduce on the map, and predation is kills of visitors. The
  only measurable flux is kills per arrival (the S8 "per surface arrival 0.24–1.28"). It is a diagnostic, not a target.
- **Producers** are plants: grass, shrub and tree tiles. They are not units. The tool already reads them (V7.vegSurvey: e.g.
  "vegetation index 67 (region 50, grass 85%…)" in the S8Cb receipt). Level 1 therefore acts as a **gate**, not a share. It
  decides which herbivores may be seated (design R12.1, the vegetation link) and could scale herbivore group size. It cannot
  scale herbivore volume: FREQUENCY composes, it does not add volume (E36).
- **Numbers (units present, time-averaged)** is what a player sees. It is also what the tool controls best. By Little's law,
  units present per species = arrival rate × group size × residence. Residence is about equal across classes (median leave
  countdown ≈ 21,400–21,600 t for LP, roamer and flier), so **numbers ∝ wave share × group size**. Both terms are known in
  advance.
- **Biomass** = numbers × body mass. In real terrestrial vertebrate communities it is strongly bottom-heavy: about 90 kg of a
  carnivore per 10,000 kg of prey (Carbone & Gittleman 2002, *Science* 295:2273), and predator biomass scales as prey
  biomass^~0.75 (Hatton et al. 2015, *Science* 349:aac6284). Marine pyramids can invert, as the user notes.
- **Recommendation:** target **numbers**, with a **biomass guard** that keeps the biomass pyramid upright on land and in the
  caverns (B_apex ≤ B_meso ≤ ½ B_herb) and lets it invert in water.

### 2.2 Why not the literal 10% rule

DF surface traffic is small: 37–122 surface units and 11–19 waves a season (S8). A 10% step in numbers puts the apex at about
1% of units, or 0.4–1.2 apex units a season. That is today's game. The CTRL worked example (§2.4) gives, for each numbers
step r:

| step r (each level / the one below) | land units H / C / A | apex on the map | apex waves per season |
|---|---|---|---|
| 1/10 (literal) | 90 / 9 / 1% | ~3% of the time | 0.14 |
| **1/4 (proposed, land)** | 76 / 19 / 5% | ~16% | 0.84 |
| 1/3 | 69 / 23 / 8% | ~25% | 1.37 |

Treat the 10% rule as the *direction* (each level smaller by a fixed step) and choose the step for visibility. On CTRL a step
between ¼ and ⅓ gives the "apex about a quarter of the time" target. The biomass guard is what still respects ecology: in the
¼ example the apex holds 12% of biomass against the meso's 11%, right at the guard. At ⅓ the guard trips (18% vs 13%), so the
apex would be held at about 6–7% of units on CTRL.

### 2.3 Proposed targets per layer

Each layer gets its unit shares, an apex presence target, and a note on why.

**Land (non-flier), per season**
- Units: H 70–76%, C 18–23%, A 5–8%.
- Apex presence: an apex group on the map **20–30% of the season** (1–2 visits); never more than 1 group (DF cap; 2 on savage).
- Biomass guard: B_A ≤ B_C ≤ ½ B_H.

**Flying**
- Units: birds 80%, raptors 20%, apex 0 (calm) / ≤ 5% (savage).
- Apex presence: none on calm maps (no calm flying apex exists, design §2).
- Why: CTRL's fliers are ravens whatever the roster says (open `flier-pool-steering`). Treat this layer separately until that
  is tested.

**Ocean**
- Units: fish and shore prey 80–85%, meso 10–15%, apex 3–5%.
- Apex presence: 15–25% of the season on deep maps; pelagic apexes stay at the floor on shallow maps (ENGINE.weight).
- Biomass may invert (orca, sharks), as real oceans do. The tool draws water itself (`ENGINE.draw`, weight = FREQUENCY with
  pelagic scaling, `seasonal-wildlife.lua:4900-4910`), so these shares are exact, not DF-mediated.

**Lake / river**
- Units: prey 85–90%, meso 10–15%, apex 0–5%.
- Apex presence: optional (open item `lake-apex-gap`).
- Why: temperate lakes often have no apex candidate (fishers off after FSH2).

**Caverns, per depth**
- Units: H 55–65%, C 25–30%, A 10–15%.
- Apex presence: an apex on each depth most of the time is acceptable.
- Why: real caves have truncated, predator-light-at-the-top food chains, and DF's caverns are already predator-heavy.
  Predators were 53–92% of cavern units in S8, mostly natives and DF's off-roster "special class" (D8). So the ladder's job
  underground is to **raise prey**, not apexes. Compute per depth, because DF picks the depth first, then the species
  (ECO2-FC).

### 2.4 From roster to level shares, and the ladder math

**Guild → trophic level** (design.md R3):
- **H** (herbivore / non-carnivore prey): GZ, PL, SH, LB, WB, FC, FF, PE. An SNP animal person takes its root's level.
- **C** (carnivore / omnivore): ML, MW, RP.
- **A** (apex): AL and AW, including boosted giants (R4).
- Vermin (V*) are stock, not waves, so they are excluded.
- TH keeps its trophic level.
- DF has no omnivore flag. A non-CARNIVORE, non-LP species is H. That is the only diet information the raws give.

**Shares from a roster** (per layer; per cavern depth; per season, over in-season members only):
- wave share s_L = Σ_{i∈L} fᵢ / Σ_j fⱼ
- unit share u_L = Σ_{i∈L} fᵢ gᵢ / Σ_j fⱼ gⱼ, with gᵢ = (CLUSTER min + max)/2, or `cfg.group_size[key]` if set
- biomass share b_L = Σ fᵢ gᵢ mᵢ / Σ fⱼ gⱼ mⱼ
- apex visits per season V_A = s_A × W, where W is the layer's non-flier waves per season (land ~6–17 on the S8 forts; caverns
  ~20–43 over 3 depths)
- presence P_A = 1 − exp(−V_A × R / T), with R ≈ 21,500 t and T = 100,800 t per season

**Setting the ladder to hit a target (u_H, u_C, u_A):**
1. **Within each level,** split the level's share equally, or by (mass/geomean)^−0.75 normalized to mean 1 as now: qᵢ.
2. **Weight:** wᵢ = u_L(i) × qᵢ / (gᵢ × Σ_{j∈L} qⱼ). Dividing by gᵢ turns a unit target into a wave weight.
3. **Biomass guard:** if b_A > b_C or b_C > ½ b_H (land and caverns), lower u_A, then u_C, and redistribute to H.
4. **Apex presence:** compute V_A and P_A. If P_A falls below the layer target, raise u_A up to the guard. Report the binding
   constraint (presence, biomass or cap).
5. **Scale:** fᵢ = clamp(round(100 × wᵢ / max w), 1, 100), so the max is 100 (DF's cap) and the floor is 1 (never 0).
   Report any species the floor inflated: the max/min ratio must stay ≤ 100. A 15-strong plump-helmet-man herd against
   lone 1:1 species can hit it.
6. **Keep the mass constant:** hold total in-season f mass roughly constant across seasons. E21b's rule: removing 24% of a
   cavern layer's mass cost 44% of its volume.

**Worked example: CTRL roster from S8Cb rep 1** (GROUNDHOG, KANGAROO, PORCUPINE, BIRD_KAKAPO; BADGER; COUGAR):

| step | COUGAR f | BADGER f | prey f | apex waves | apex units | apex biomass | apex on map |
|---|---|---|---|---|---|---|---|
| 1/4 | 26 | 12 | 40 / 33 / 100 / 100 | 8.4% | 5.0% | 11.6% | 16% |
| 1/3 | 46 | 17 | same | 13.7% | 7.9% | 18.1% (guard trips) | 25% |
| today (v2.1 ladder) | 14 | 14 | 100 / 8 / 15 / 35 | 7.5% | ~3% | — | ~15% |

Compute with W = 10 non-flier waves a season. To read the "today" row against the table: today's ladder has an apex wave
share similar to the ¼ step's. It differs in that groundhogs swamp the prey level and the meso level gets 3.9% of waves but
18% of units (badger groups of 8).

**Code touchpoints** (for the eventual port; not edited):
- `ROSTER.LADDER` / the R13 block, `seasonal-wildlife.lua:5354-5417`. Replace the per-guild base values with the level
  targets, add the g-division and the guard.
- `ENGINE.groupSize` (`:4911`) already reads `cluster_number`, so gᵢ is available.
- `CAVERN.apply` (`:3006`) writes `cfg.odds` daily, so a per-season ladder is deliverable without new persistence.
- The collapse of cav1–3 into one cavern layer (documented gap, `:5052-5066`) must be undone for the ladder: shares are
  per depth.

---

## 3. "Should the ladder target units rather than waves?" (open item `ladder-units-vs-waves`): resolved, **units**

1. **The pyramid is about units.** Numbers and biomass are on-map quantities. Waves are a means. A ladder in wave shares is
   off by each species' group size, which spans 1 (cougar, kestrel) to about 17 (crundle) on the rig, with up to 15 per wave
   for plump helmet men in S8B.
2. **Pack size explains every reported overshoot.**
   - S8B rep 1: GIANT_JACKAL 27 units in 6 waves put predators at 42% of units.
   - PLUMP_HELMET_MAN: 54 and 180 cavern units from 7 and 12 waves.
   - CTRL's badger is ML at 3.9% of waves but 18% of units in the worked example.
3. **The correction is predictable.** By Little's law with equal residence, units ∝ f × g. I compared the rig's mean wave size
   against the raw CLUSTER_NUMBER midpoint (all `data/experiments/*/*/waves.tsv`, species with ≥ 90 waves): kangaroo 3.11 vs
   3.0, troglodyte 7.51 vs 7.5, elk bird 7.17 vs 7.5, crundle 16.7 vs 17.5, wolf 4.79 vs 5.0, dingo 6.70 vs 7.5, badger 7.05 vs
   8.0, raven 6.10 vs 6.0, groundhog 2.60 vs 2.5. The outliers are tool-placed or overridden groups (pangolin, tigerfish).
   So dividing f by (cmin + cmax)/2 hits unit shares without new rig work.
4. **The exception is the apex.** Its *presence* depends on visits, not units, so the apex level is set by the visit target
   (§2.4 step 4). Its unit share then follows (g ≈ 1). This is a hybrid: prey and meso by units, apex by visits, both
   reported.
5. **The group-size cap is a complement.** A cap via `cfg.group_size` (the `outgun_cap` mechanism, and open item
   `cavern-animal-person-group-cap`) trims the swamp at its source. Dividing by g keeps shares right whatever the cap is.
6. **Not yet measured:** whether residence really is equal when prey are killed. Prey that die leave early, so units of prey
   run below f × g. SW4 saw predators "linger" above f/Σf. The optional WOLF arm of FQ1 and any S8 rerun after the port test
   this.

---

## 4. Figures

The renderer is `scripts/eco-report/template.html` (Observable Plot 0.6.16). The convention for every categorical form (bar,
dot, dumbbell, box, strip, stackedBar, groupedBar, range) is **`spec.x` = category, `spec.y` = value**. For example, the dot
case draws `Plot.dot(rows, {x:y, y:x})` (`template.html:212-215`).

To verify, I rendered each figure headless with Chrome (`/Applications/Google Chrome.app`, `--headless=new`) through SCRATCH
`harness.py`, which uses the template's own renderer with d3/Plot fetched locally. I counted the marks drawn per figure
(`all-before.diag`, `all-after.diag`). Across all 99 figures, only the ten targeted ones changed their mark counts, and none
errors.

### 4.1 Figure 18: "A leader holds flocks and schools…" (`coh-flock-school-pod`)
- **Cause:** the spec has `x: "width"` (numeric) and `y: "group"` (text), the wrong way round. The renderer put the 16 widths
  on the category axis and tried to place the text "Duck flock x12" on a linear x scale. Every dot became NaN, so 0 circles
  were drawn and the y ticks read "5.2 | 30.3 | 139.7…".
- **Fix:** swap x and y (data). A renderer guard now also swaps any categorical spec whose x is all-numeric and y is text,
  with a console warning.
- **Second bug:** the replicate-mean tick pooled both arms (leader + none) into one meaningless mid-tick. It is now one tick
  per series, in that series' colour.
- **After:** 16 dots, four groups. Leader 5–49 tiles vs none 87–149 (`shots/after2.png`).

### 4.2 Figure 19: "On the desk, the v2.2 ladder…" (`builder-predator-share-desk`)
- **Cause:** same swap (`x: "predator_share"`, `y: "layer"`). The y axis listed 24 share values and the x axis ran
  0.140–0.180, set only by the two reference lines.
- **Fix:** swap. The two reference lines were both labelled "(land)" (14% and 18%). They become one labelled band edge,
  "land aim 14-18%", plus an unlabelled 18% line.
- **After:** 24 dots over 8 layers × 3 versions.

### 4.3 Five more figures empty for the same reason (not named in the review)
`hc4-species-or-spot` (dumbbell), `leader-spread` (dumbbell), `size-gate-model` (dot), `vrm2-gobble-tokens` (dot) and
`sw2-elephant-choice` (dumbbell) all drew 0 marks before and 10–28 after. `shots/suspects.png` is before, `shots/dots.png`
after. Check for the rest of Part 2:
- `size-gate-model`'s subtitle promises a "group size DF sends (bar)" that the spec does not draw.
- `vrm2`'s longest labels clip at the 280-px left-margin cap.

### 4.4 Figure 17: "When the kangaroo entry hit 0 no kangaroo came" (`n1-exhaustion-replacement`)
- **Cause:** `reference: [{value: 2400}]` is a **tick**: the kangaroo wave at t 2,400. The spec's own note says "reference is
  on the x axis". The renderer only draws x-axis rules for horizontal categorical forms. For `line` it drew `ruleY(2400)`,
  which forced the y domain to 0–2,400 and flattened the 0–25 wave counts onto the floor.
- **Fix:**
  - Renderer: a reference may carry `axis: "x"`, drawn as a vertical rule on line, scatter and histogram.
  - Data: set `axis: "x"`, `yLabel: "waves so far"` (this also removes the doubled "cumulative_waves (waves (cumulative))"),
    and `curve: "step-after"`, because a cumulative count is a step function and monotone-x showed fractional waves between
    samples.
- **After:** y axis 0–25. Wombat steps to 25, groundhog 1→2, kangaroo flat at 1 after the dashed t 2,400 line.
- **Remaining wart:** kangaroo (1) and groundhog (1) overlap until t 34,450, so the blue line hides under the green.
  Acceptable; dodge them if wanted.

### 4.5 Figure 11: "DF aims every non-wild unit…" (`rels-who-writes`): data diagnosis only
- **Render cause:** the same swap (`x: "n"`, `y: "writer"`). The bars were drawn full-width in grey, labelled with the
  counts 4…159 instead of the writers. The `highlight` compares `r[x]` (a number) with a writer string, so nothing could match.
- **Spec cause of "makes no sense":** the chart shows only `writer`. The `target` column, which carries the meaning
  ("→ surface wild arrival" vs "→ each other"), was in the rows but never drawn. "Cavern and surface wildlife" alone reads as
  nonsense.
- **Fix in scratch:**
  - Swap the axes.
  - Add an `entry` label per row: "Dwarves → new arrival", "Livestock, pets → new arrival", "Placed animals → new arrival",
    "Cavern → cavern wildlife", "Surface → surface wildlife", "Cavern ↔ surface wildlife".
  - Highlight placed animals.
  - The rendered bars are 159 / 107 / 57 / 38 / 5 / 4.

**Data check** against `data/experiments/ECO/RELS-20260930-195031/RELS.tsv`. I recounted the PREDATOR_OR_PREY `rel` rows by
the a:/b: class fields:
- The counts reproduce. citizen→wild 159, tame→wild 107, other→wild 57 and wild→wild 47 make 370; the figure's 38 + 5 + 4
  split of the 47 matches the `rels-tally.py` classes.
- **The title's "every" is not what the rows show.** The rows count *entries*, not the share of non-wild units that wrote.
  Per arrival targeted, the median number of distinct writers is **1** (62 of 112 targets had one writer; the maximum was
  20). The data support: "most relation entries DF writes are a non-wild unit marking a newly seen wild arrival (323 of 370);
  a typical arrival is marked by one unit, a few by up to 20".
- Exposure is pooled unevenly. The `nat` cell ran 100,800 t and the six subject cells 30,000 t each (89 of 370 entries come
  from `nat`).
- The "Placed animals (not flagged wild)" bar (57) is an artefact class (released groups lose the roaming flag; the spec's own
  note).

Item 11's other researcher should judge whether the figure belongs in the report at all.

### 4.6 Figure 15: "Wildlife tokens travel in a few tight blocks" (`token-cooccurrence`)

**Cause of the bad layout:**
- It was the 9th tokens figure, so `{{gallery:tokens}}` (`content.html:220`) placed it in a default gallery cell
  (`minmax(420px,1fr)`, about 490 px at full page width).
- 75 columns in about 490 − 200 px of margin gives cells 4 px wide. The renderer still printed a 10.5-px number in each of
  1,847 cells, and sized the height at 26 px per row (2,060 px), so cells were tall slivers.
- Dark mode had a second problem: the `blues` scheme starts near white, so the hundreds of low-Jaccard cells (0.05–0.2)
  showed as bright white squares on a dark panel.

**Order check:**
- Row and column order are identical: first appearance of token_a and of token_b in the rows both equal
  `cluster-order.json` `wild.order`, the UPGMA leaf order.
- `clusters.md`: distance 1 − Jaccard, average linkage, tokens on ≥ 3 of 363 wild species, 75 tokens.

**Fixes:**
- **Layout:**
  - Spec `layout: "full"` adds class `span`. CSS `.gallery > .fig.span{grid-column:1 / -1}` makes the card span the full
    gallery width; at a 1,800-px window that is ~1,500 px.
  - For a matrix of more than 24 columns (or `cellText:false`), cells are drawn **square**:
    side = (width − margins)/75 ≈ 16 px.
  - No cell numbers (the value is in the tooltip).
  - Ticks are 12 px with x labels rotated −90°.
  - A theme-aware ramp, `C.grid → C.s1` over a fixed 0–1 domain, works in light and dark.
- **Block outlines:** the 12 blocks of the 0.5 cut (`cluster-cuts.json` `wild["0.5"]`, every one contiguous in the order) are
  outlined and numbered. Each outline's tooltip gives its members and the all/any species counts.
- **Verified:**
  - `shots/heat-dark.png`, `shots/heat-light.png`;
  - in-page full width: `shots/tokens-after.png`, a scratch build of the whole page with the tokens section isolated;
  - 1,859 rects = 1,847 cells + 12 outlines.

**Proposed subtitle:** "Jaccard overlap of the 75 tokens carried by 3+ of the 363 wildlife species: species with both /
species with either. Same tokens, same order on both axes; blank = under 0.05; outlined = the 12 blocks that hold at mean
J >= 0.5".

**Proposed caption (new):**

> How to read it. The order is the leaf order of an average-linkage tree on 1 − Jaccard, so tokens that ride on the same
> species sit side by side and a dark square on the diagonal is a block of tokens that travel together. The numbered
> outlines are the blocks that survive a cut at 0.5: 1 rat-like vermin; 2 spiders; 3 thieves; 4 ground foragers; 5 beasts of
> burden; 6 grazers; 7 aquatic core; 8 vermin fish; 9 vermin body; 10 backbone (prevalence); 11 cavern senses; 12 cavern.
> Only adjacency carries meaning, and loosely: tokens side by side share a branch of the tree; a block's place along the
> diagonal is not a rank, and the tree could be flipped at any branch without changing it. Dark rows outside any block are
> prevalence, not meaning: the backbone (BIOME and POPULATION_NUMBER on 363 of 363, GAIT 360, NATURAL 331) overlaps
> everything common. From the top left the order runs: rare tokens and the vermin set, thieves, domestic and burden tokens,
> grazers, the aquatic core, the vermin body and fish, the backbone, fliers, activity and diet, the two cavern blocks, and
> LARGE_PREDATOR last, because no token travels with it (best partner UNDERGROUND_DEPTH, J 0.26; it never co-occurs with
> BENIGN). What it means for the tool: writing one token of a block without its partners builds a combination no vanilla
> species carries (AQUATIC without IMMOBILE_LAND and NO_DRINK, for example), while LARGE_PREDATOR can be written alone without
> breaking a pattern. Desk survey of the 53.16 raws (eco/T0-triage.tsv; data/eco-desk/v2/tokens/clusters.md,
> cluster-order.json, cluster-cuts.json).

Every number is from `data/eco-desk/v2/tokens/clusters.md`:
- the block table and its counts;
- the backbone prevalence;
- "LARGE_PREDATOR has no tight cluster. Its best partner is UNDERGROUND_DEPTH, at J = 0.26";
- coincidence 7, "LARGE_PREDATOR and BENIGN never co-occur";
- the aquatic core: "the only AQUATIC species without IMMOBILE_LAND are MOON_SNAIL, SPONGE and LOBSTER_CAVE".

---

## 5. Exact proposed patches (tested in SCRATCH; NOT applied to the report sources)

To apply after Part 2:
1. Apply the two diffs below.
2. Run `python3 SCRATCH/patch_exp.py data/eco-report/experiments.json`. It is idempotent and reads the token
   cluster files from the repo.
3. Run `python3 scripts/eco-report/build.py`.

### 5.1 `scripts/eco-report/build.py`

```diff
--- a/scripts/eco-report/build.py
+++ b/scripts/eco-report/build.py
@@ -39,7 +39,8 @@
 
 def fig_card(f):
     cap = " · ".join(x for x in [f.get("caption"), f.get("notes")] if x)
-    return (f'<figure class="fig" data-fig="{esc(f["id"])}" id="fig-{esc(f["id"])}">'
+    span = " span" if f.get("layout") == "full" else ""   # full: the card spans every column of its gallery
+    return (f'<figure class="fig{span}" data-fig="{esc(f["id"])}" id="fig-{esc(f["id"])}">'
             f'<div class="ft">{esc(f.get("title"))}</div>'
             + (f'<div class="fs">{esc(f.get("subtitle"))}</div>' if f.get("subtitle") else "")
             + '<div class="plot"></div>'
```

### 5.2 `scripts/eco-report/template.html`

```diff
--- a/scripts/eco-report/template.html
+++ b/scripts/eco-report/template.html
@@ -73,6 +73,7 @@
 .gallery{display:grid; grid-template-columns:repeat(auto-fill,minmax(420px,1fr)); gap:16px; align-items:start}
 .gallery.stack{grid-template-columns:minmax(0,1fr)}
 .gallery.wide{grid-template-columns:repeat(auto-fill,minmax(560px,1fr))}
+.gallery > .fig.span{grid-column:1 / -1}
 .subsec{display:grid; gap:14px; padding-top:6px}
 /* figures */
 .fig{margin:0; background:var(--panel); border:1px solid var(--rule); border-radius:6px; padding:14px 16px 12px; display:grid; gap:6px; min-width:0}
@@ -165,7 +166,12 @@
 
 function build(spec, width){
   const C = css(); const rows = (spec.rows || []).map(r => { const o = {}; for (const k in r) o[k] = num(r[k]); return o; });
-  const x = spec.x, y = spec.y, s = spec.series || null, fct = spec.facet || null, form = spec.form;
+  let x = spec.x, y = spec.y; const s = spec.series || null, fct = spec.facet || null, form = spec.form;
+  // Categorical forms read spec.x as the category and spec.y as the value. A spec written the other way round
+  // (numeric x, text y) used to plot text on a linear scale: every mark NaN, an empty frame. Swap it and say so.
+  if (['bar','dot','dumbbell','box','strip','stackedBar','groupedBar','range'].includes(form) && rows.length && x && y
+      && rows.every(r => typeof r[x] === 'number') && rows.some(r => typeof r[y] === 'string')){
+    console.warn('figure', spec.id, ': x/y swapped (x must be the category)'); [x, y] = [y, x]; }
   const color = colorScale(spec, rows, C);
   const hi = spec.highlight;
   const base = {width, style:{background:'transparent', color:C.ink2, fontFamily:C.ui, fontSize:'12px', overflow:'visible'},
@@ -211,7 +217,8 @@
       const hasRep = rows.some(r => r.rep != null);
       marks = [Plot.ruleY(cats, {stroke:C.grid}),
                Plot.dot(rows, {x:y, y:x, fill: s ? s : accent, r:5, stroke:C.panel, strokeWidth:1, title:T})];
-      if (hasRep) marks.push(Plot.tickX(rows, Plot.groupY({x:'mean'}, {x:y, y:x, stroke:C.ink, strokeWidth:2})));
+      // replicate mean: one tick per category AND series (one tick pooled over both arms meant nothing)
+      if (hasRep) marks.push(Plot.tickX(rows, Plot.groupY({x:'mean'}, s ? {x:y, y:x, z:s, stroke:s, strokeWidth:2} : {x:y, y:x, stroke:C.ink, strokeWidth:2})));
       opt = {marginLeft:lm, height:Math.max(110, 26 * cats.length + 54), x:{label:(spec.yLabel || y) + unit, grid:true, type: valueLog ? 'log':'linear'}, y:{label:null, domain:spec.categoryOrder || cats}};
       break; }
     case 'dumbbell': {
@@ -227,14 +234,35 @@
       const xs = uniq(rows, x), ys = uniq(rows, y === v ? (s || y) : y);
       const yk = y === v ? s : y;
       const vmax = d3.max(rows, d => +d[v] || 0) || 1;
-      marks = [Plot.cell(rows, {x:x, y:yk, fill:v, title:T, inset:1}), Plot.text(rows, {x:x, y:yk, text:d => d[v] == null ? '' : fmt(d[v]), fill:d => ((+d[v] || 0) / vmax > 0.5 ? '#ffffff' : '#17201C'), fontSize:10.5, fontWeight:500})];
-      opt = {marginLeft:Math.min(260, 18 + 7.4*longest(ys)), marginBottom: Math.min(150, 24 + 6.4*longest(xs)), height:Math.max(160, 26 * ys.length + 110),
-             x:{label:null, tickRotate: longest(xs) > 5 ? -40 : 0, domain:spec.xOrder || xs}, y:{label:null, domain:spec.yOrder || ys},
-             color:{type: spec.colorType || 'linear', scheme:'blues', legend:true, label:(spec.valueLabel || v) + (spec.unit && !(spec.valueLabel || v).includes(spec.unit) ? ` (${spec.unit})` : '')}};
-      return Plot.plot({...base, ...opt, marks});
+      const big = spec.cellText === false || xs.length > 24;
+      const xd = spec.xOrder || xs, yd = spec.yOrder || ys;
+      marks = [Plot.cell(rows, {x:x, y:yk, fill:v, title:T, inset: big ? 0.5 : 1})];
+      if (!big) marks.push(Plot.text(rows, {x:x, y:yk, text:d => d[v] == null ? '' : fmt(d[v]), fill:d => ((+d[v] || 0) / vmax > 0.5 ? '#ffffff' : '#17201C'), fontSize:10.5, fontWeight:500}));
+      const ml = Math.min(260, 18 + 7.4*longest(ys)), mb = big ? Math.min(200, 18 + 7.4*longest(xs)) : Math.min(150, 24 + 6.4*longest(xs));
+      const side = big ? Math.max(9, Math.floor((width - ml - 20) / xd.length)) : 26;    // square cells for a big matrix
+      opt = {marginLeft:ml, marginBottom:mb, marginRight: big ? 20 : 28,
+             width: big ? ml + side * xd.length + 20 : width,
+             height: big ? side * yd.length + mb + 16 : Math.max(160, 26 * ys.length + 110),
+             x:{label:null, tickRotate: big ? -90 : (longest(xs) > 5 ? -40 : 0), domain:xd}, y:{label:null, domain:yd},
+             color:{type: spec.colorType || 'linear', ...(big ? {domain:[0, 1], range:[C.grid, C.pal[0]]} : {scheme:'blues'}), legend:true, label:(spec.valueLabel || v) + (spec.unit && !(spec.valueLabel || v).includes(spec.unit) ? ` (${spec.unit})` : '')}};
+      const node = Plot.plot({...base, ...opt, marks});
+      if (big && spec.blocks){   // outline each block on the diagonal; a block is {from, to, label}, first and last token in the order
+        const sx = node.scale('x'), sy = node.scale('y');
+        const svg = node.tagName.toLowerCase() === 'svg' ? node : [...node.querySelectorAll('svg')].pop();
+        const g = d3.select(svg).append('g').attr('aria-label', 'blocks');
+        for (const bk of spec.blocks){
+          const i = xd.indexOf(bk.from), j = xd.indexOf(bk.to); if (i < 0 || j < 0) continue;
+          const x0 = sx.apply(xd[i]), x1 = sx.apply(xd[j]) + sx.bandwidth, y0 = sy.apply(yd[yd.indexOf(bk.from)]), y1 = sy.apply(yd[yd.indexOf(bk.to)]) + sy.bandwidth;
+          g.append('rect').attr('x', x0).attr('y', y0).attr('width', x1 - x0).attr('height', y1 - y0).attr('fill', 'none').attr('stroke', C.ink).attr('stroke-width', 1.6)
+           .append('title').text(bk.label);
+          if (bk.tag) g.append('text').attr('x', x1 + 3).attr('y', y0 - 3).attr('font-size', 11.5).attr('font-weight', 700).attr('fill', C.ink)
+             .attr('stroke', C.panel).attr('stroke-width', 3).attr('paint-order', 'stroke').text(bk.tag);
+        }
+      }
+      return node;
     }
     case 'line': {
-      marks = [Plot.line(rows, {x:x, y:y, stroke: s || accent, strokeWidth:2, curve:'monotone-x'}), Plot.dot(rows, {x:x, y:y, fill: s || accent, r:3, title:T})];
+      marks = [Plot.line(rows, {x:x, y:y, stroke: s || accent, strokeWidth:2, curve: spec.curve || 'monotone-x'}), Plot.dot(rows, {x:x, y:y, fill: s || accent, r:3, title:T})];
       opt = {height:280, x:{label:(spec.xLabel || x), grid:false}, y:{label:(spec.yLabel || y) + unit, grid:true, type: valueLog ? 'log':'linear'}};
       break; }
     case 'scatter': {
@@ -265,7 +293,8 @@
       break; }
     default: return null;
   }
-  refs.forEach((rf, ri) => { const vv = rf.value; const horizontal = ['bar','dot','dumbbell','box','strip','stackedBar','range'].includes(form) && (form !== 'bar' || cats.length > 5 || longest(cats) > 9);
+  refs.forEach((rf, ri) => { const vv = rf.value; const horizontal = rf.axis === 'x' && ['line','scatter','histogram'].includes(form) ? true :
+      ['bar','dot','dumbbell','box','strip','stackedBar','range'].includes(form) && (form !== 'bar' || cats.length > 5 || longest(cats) > 9);
     if (horizontal){ marks.push(Plot.ruleX([vv], {stroke:C.ink3, strokeDasharray:'4,3'}), Plot.text([vv], {x:d => d, frameAnchor:'top', dy:-2 + ri * 12, text:() => rf.label, fill:C.ink3, fontSize:10.5, textAnchor:'start', dx:4})); }
     else { marks.push(Plot.ruleY([vv], {stroke:C.ink3, strokeDasharray:'4,3'}), Plot.text([vv], {y:d => d, frameAnchor:'right', dy:-6, text:() => rf.label, fill:C.ink3, fontSize:10.5, textAnchor:'end'})); } });
   if (fct){ opt.fy = undefined; }
```

### 5.3 `data/eco-report/experiments.json`: field changes per figure (generated by SCRATCH `patch_exp.py`; long values truncated)

```diff
## hc4-species-or-spot
- x: "attacks_both"
+ x: "pair"
- y: "pair"
+ y: "attacks_both"
## token-cooccurrence
- blocks: null
+ blocks: [{"from": "GNAWER", "to": "VERMIN_EATER", "label": "1 rat-like vermin: GNAWER, VERMIN_EATER (all 4 / any 8 species, mean J 0.5)", "tag": "1"}, {"from": "WEBBER", "to": "WEBIMMUNE", "label": "2 spiders: WEBBER, WEBIMMUNE (all 4 / any 5 species, mean J 0.8)", "tag": "2"}, {"from": "CURIOUSBEAST_ITEM",... (1959 chars)
- caption: "Desk survey of the 53.16 raws (eco/T0-triage.tsv); rows from the report widget token-heatmap (23da11c7-e484)"
+ caption: "How to read it. The order is the leaf order of an average-linkage tree on 1 - Jaccard, so tokens that ride on the same species sit side by side and a dark square on the diagonal is a block of tokens that travel together. The numbered outlines are the blocks that survive a cut at 0.5: 1 rat-like ver... (1507 chars)
- cellText: null
+ cellText: false
- layout: null
+ layout: "full"
- notes: "Not a rig experiment: raws survey. Keep the widget's cluster order (order of token_a first appearance). Diagonal set to 1.0; species_with_a = prevalence bar."
+ notes: "Not a rig experiment. Hover a cell for the pair and the number of species carrying the row token; hover an outline for the block's members and counts."
- subtitle: "Jaccard overlap of the 75 tokens carried by 3+ of the 363 wildlife species, cluster order; overlaps under 0.05 omitted"
+ subtitle: "Jaccard overlap of the 75 tokens carried by 3+ of the 363 wildlife species: species with both / species with either. Same tokens, same order on both axes; blank = under 0.05; outlined = the 12 blocks that hold at mean J >= 0.5"
- unit: "Jaccard"
+ unit: null
- valueLabel: null
+ valueLabel: "Jaccard overlap"
- xOrder: null
+ xOrder: ["BEACH_FREQUENCY", "PRONE_TO_RAGE", "SAVAGE", "VERMIN_MICRO", "VERMIN_ROTTER", "GOOD", "VERMIN_HATEABLE", "TRIGGERABLE_GROUP", "GNAWER", "VERMIN_EATER", "VERMIN_BITE", "WEBBER", "WEBIMMUNE", "VERMIN_SOIL_COLONY", "UBIQUITOUS", "VERMIN_SOIL", "CURIOUSBEAST_GUZZLER", "CURIOUSBEAST_EATER", "CURIOUSBEA... (1115 chars)
- yOrder: null
+ yOrder: ["BEACH_FREQUENCY", "PRONE_TO_RAGE", "SAVAGE", "VERMIN_MICRO", "VERMIN_ROTTER", "GOOD", "VERMIN_HATEABLE", "TRIGGERABLE_GROUP", "GNAWER", "VERMIN_EATER", "VERMIN_BITE", "WEBBER", "WEBIMMUNE", "VERMIN_SOIL_COLONY", "UBIQUITOUS", "VERMIN_SOIL", "CURIOUSBEAST_GUZZLER", "CURIOUSBEAST_EATER", "CURIOUSBEA... (1115 chars)
## leader-spread
- x: "spread"
+ x: "group"
- y: "group"
+ y: "spread"
## coh-flock-school-pod
- x: "width"
+ x: "group"
- y: "group"
+ y: "width"
## n1-exhaustion-replacement
- curve: null
+ curve: "step-after"
- notes: "Extinct flag stayed FALSE: quantity 0 alone gates. First wombat wave +2,090 t after the kangaroo wave. reference is on the x axis."
+ notes: "Extinct flag stayed FALSE: quantity 0 alone gates. First wombat wave +2,090 t after the kangaroo wave."
- reference: [{"value": 2400, "label": "kangaroo wave of 3 (entry 3 -> 0); hook fires at next 1,500-t pass"}]
+ reference: [{"value": 2400, "axis": "x", "label": "kangaroo wave of 3 (entry 3 -> 0)"}]
- unit: "waves (cumulative)"
+ unit: null
- xLabel: null
+ xLabel: "ticks"
- yLabel: null
+ yLabel: "waves so far"
## builder-predator-share-desk
- reference: [{"value": 0.14, "label": "aim 14% (land)"}, {"value": 0.18, "label": "aim 18% (land)"}]
+ reference: [{"value": 0.14, "label": "land aim 14-18%"}, {"value": 0.18, "label": ""}]
- unit: "share of arrivals"
+ unit: null
- x: "predator_share"
+ x: "layer"
- y: "layer"
+ y: "predator_share"
- yLabel: null
+ yLabel: "predator share of arrivals"
## size-gate-model
- x: "hunters_needed"
+ x: "pair"
- y: "pair"
+ y: "hunters_needed"
## rels-who-writes
- highlight: "Placed animals (not flagged wild)"
+ highlight: "Placed animals → new arrival"
  rows: + field(s) ['entry'] on every row, e.g. {"entry": "Dwarves → new arrival"}
- x: "n"
+ x: "entry"
- y: "writer"
+ y: "n"
## vrm2-gobble-tokens
- x: "share"
+ x: "arm"
- y: "arm"
+ y: "share"
## sw2-elephant-choice
- x: "elephant_share"
+ x: "arm"
- y: "arm"
+ y: "elephant_share"
```

The full `patch_exp.py` (the source of truth for 5.3):

```python
"""Apply the figure-data fixes to experiments.json (scratch copy). Idempotent."""
import json, sys
from pathlib import Path
P = Path(sys.argv[1] if len(sys.argv) > 1 else "data/eco-report/experiments.json")
TOK = Path("/Users/nathanielcannon/Claude/Projects/DwarfCron/data/eco-desk/v2/tokens")
d = json.loads(P.read_text())
F = {f["id"]: f for f in d["figures"]}
# (a) eight specs written value-first: the renderer wants x = category, y = value
for fid in ["hc4-species-or-spot", "leader-spread", "coh-flock-school-pod", "builder-predator-share-desk",
            "size-gate-model", "rels-who-writes", "vrm2-gobble-tokens", "sw2-elephant-choice"]:
    f = F[fid]
    if all(isinstance(r.get(f["x"]), (int, float)) for r in f["rows"]):
        f["x"], f["y"] = f["y"], f["x"]
# (b) N1: the kangaroo reference is a tick (x), not a wave count (y)
f = F["n1-exhaustion-replacement"]
f["reference"] = [{"value": 2400, "axis": "x", "label": "kangaroo wave of 3 (entry 3 -> 0)"}]
f["yLabel"] = "waves so far"; f["xLabel"] = "ticks"; f["unit"] = None; f["curve"] = "step-after"
f["notes"] = f["notes"].replace(" reference is on the x axis.", "")
# (c) builder: one aim band, not two lines both labelled 'land'
f = F["builder-predator-share-desk"]
f["reference"] = [{"value": 0.14, "label": "land aim 14-18%"}, {"value": 0.18, "label": ""}]
f["yLabel"] = "predator share of arrivals"; f["unit"] = None
# (d) RELS: the bar label must carry the target class too (the chart showed writers only)
f = F["rels-who-writes"]
SHORT = {"Dwarves": "Dwarves → new arrival", "Livestock and pets": "Livestock, pets → new arrival",
         "Placed animals (not flagged wild)": "Placed animals → new arrival", "Cavern wildlife": "Cavern → cavern wildlife",
         "Surface wildlife": "Surface → surface wildlife", "Cavern and surface wildlife": "Cavern ↔ surface wildlife"}
for r in f["rows"]:
    r["entry"] = SHORT[r["writer"]]
f["x"] = "entry"; f["highlight"] = "Placed animals → new arrival"
# (e) token heatmap: full width, block outlines from the 0.5 cut, caption that explains the grouping and order
f = F["token-cooccurrence"]
order = json.loads((TOK / "cluster-order.json").read_text())["wild"]["order"]
cuts = json.loads((TOK / "cluster-cuts.json").read_text())["wild"]["0.5"]
names = {"CANNOT_JUMP": "aquatic core", "SMALL_REMAINS": "vermin body", "FISHITEM": "vermin fish", "PETVALUE": "backbone (prevalence)",
         "LOW_LIGHT_VISION": "cavern", "ODOR_LEVEL": "cavern senses", "STANDARD_GRAZER": "grazers", "GOBBLE_VERMIN_CLASS": "ground foragers",
         "WEBBER": "spiders", "CURIOUSBEAST_ITEM": "thieves", "PACK_ANIMAL": "beasts of burden", "GNAWER": "rat-like vermin"}
blocks = []
for c in cuts:
    idx = sorted(order.index(t) for t in c["tokens"])
    first = order[idx[0]]
    blocks.append({"from": first, "to": order[idx[-1]], "i": idx[0],
                   "label": f'{names.get(first, first)}: {", ".join(order[i] for i in idx)} (all {c["n_all"]} / any {c["n_any"]} species, mean J {c["mean_pair_jaccard"]})'})
blocks.sort(key=lambda b: b["i"])
for k, b in enumerate(blocks):
    b["tag"] = str(k + 1); b["label"] = f'{k+1} {b["label"]}'; del b["i"]
f["blocks"] = blocks
f["layout"] = "full"; f["cellText"] = False
f["xOrder"] = f["yOrder"] = order
f["subtitle"] = ("Jaccard overlap of the 75 tokens carried by 3+ of the 363 wildlife species: species with both / species with either. "
                 "Same tokens, same order on both axes; blank = under 0.05; outlined = the 12 blocks that hold at mean J >= 0.5")
key = "; ".join(f'{b["tag"]} {b["label"].split(":")[0][len(b["tag"])+1:]}' for b in blocks)
f["caption"] = (
    "How to read it. The order is the leaf order of an average-linkage tree on 1 - Jaccard, so tokens that ride on the same species sit side by side "
    "and a dark square on the diagonal is a block of tokens that travel together. The numbered outlines are the blocks that survive a cut at 0.5: "
    + key + ". Only adjacency carries meaning, and loosely: tokens side by side share a branch of the tree; a block's place along the diagonal is not a rank, and the tree could be flipped at any branch without changing it. "
    "Dark rows outside any block are prevalence, not meaning: the backbone (BIOME and POPULATION_NUMBER on 363 of 363, GAIT 360, NATURAL 331) "
    "overlaps everything common. From the top left the order runs: rare tokens and the vermin set, thieves, domestic and burden tokens, grazers, the aquatic core, "
    "the vermin body and fish, the backbone, fliers, activity and diet, the two cavern blocks, and LARGE_PREDATOR last, because no token "
    "travels with it (best partner UNDERGROUND_DEPTH, J 0.26; it never co-occurs with BENIGN). What it means for the tool: writing one token of a block "
    "without its partners builds a combination no vanilla species carries (AQUATIC without IMMOBILE_LAND and NO_DRINK, for example), while LARGE_PREDATOR "
    "can be written alone without breaking a pattern. Desk survey of the 53.16 raws (eco/T0-triage.tsv; data/eco-desk/v2/tokens/clusters.md, cluster-order.json, cluster-cuts.json).")
f["valueLabel"] = "Jaccard overlap"; f["unit"] = None
f["notes"] = "Not a rig experiment. Hover a cell for the pair and the number of species carrying the row token; hover an outline for the block's members and counts."
P.write_text(json.dumps(d, indent=1, ensure_ascii=False))
print("patched", P)
```

---

## 6. Sources

- Wiki: [Creature token](https://dwarffortresswiki.org/index.php/Creature_token) (FREQUENCY, LARGE_PREDATOR, UBIQUITOUS,
  CLUSTER_NUMBER, LARGE_ROAMING, BENIGN); [DF2014:Creature token](https://dwarffortresswiki.org/index.php/DF2014:Creature_token)
  (default 50, max 100, the 58.8% example, one LP group per map); [Creature](https://dwarffortresswiki.org/index.php/Creature)
  (POPULATION_NUMBER, "comparative number").
- Ecology: Carbone & Gittleman 2002, *Science* 295:2273, [PubMed](https://pubmed.ncbi.nlm.nih.gov/11910114/); Hatton et al.
  2015, *Science* 349:aac6284, doi:10.1126/science.aac6284.
- Tool: `Projects/seasonal-wildlife/scripts/seasonal-wildlife.lua` (v7.0, 99c1ec8): never-0 2940-2957, CAVERN.write 2974,
  CAVERN.apply 3006, ODDS.weight 3075, ENGINE.weight 4900, ENGINE.groupSize 4911, R13 ladder 5354-5379, ROSTER.LADDER 5413.
  `STATE.md` addenda 53-56 (2047-2290) and the X3 note (3874).
- Desk: `DwarfCron/data/eco-desk/findings.md` (F1 50-53, T2 67, ECO2-FC 160, ECO2-W 192, S8B 437, S8O 449, SW4 469, S8Cb 519);
  `data/eco-desk/v2/guilds/design.md` (R3, R12.7, R13, §§2, 3, 5, 8, 9), `species2.tsv`; `data/eco-desk/v2/tokens/clusters.md`,
  `cluster-order.json`, `cluster-cuts.json`; `data/eco-report/open-items.json` (ladder-drop-apx-step, lp-separate-pool,
  ladder-units-vs-waves, builder-port-vs-v22, cavern-animal-person-group-cap, flier-pool-steering, apex-placement-stock-test).
- Runs re-tallied: `data/experiments/X3/20260926-212003`, `ECO-F1`, `ECO-N1`, `ECO-T2` (waves.tsv);
  `S8C/20261001-062036`, `S8B/20261001-020551`, `S8O/20261001-022543` (log.txt, pops.tsv, `scripts/s8-tally.py`);
  `ECO/SW4-20261001-030441/SW4.tsv`; `ECO/RELS-20260930-195031/RELS.tsv`; all `data/experiments/*/*/waves.tsv` for group sizes
  and leave countdowns.
