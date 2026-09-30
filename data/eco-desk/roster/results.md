# Roster / food-web rules A-G + steps 0-8: what they do (desk prototype, DF 53.16 vanilla raws)

**Run**
- 7 embark biome sets × 3 surface layers × 4 seasons × 20 seeds, plus 4 underground layers × 4 seasons × 20 seeds.
  That is 2,000 rosters per config, **34 configs, 68,000 rosters**. It takes about 30 s in total.
- The game was not touched. The inputs are raws plus today's measured facts (findings.md).
- Interpretation choices are in `rules.md`. Full tables are in `tables.md`, rule-level facts in `extras.md`, and concrete
  rosters in `examples.md`.

**How to read "baseline"**
- Baseline = the rules as written, with the tool's size bands (small < 150k, medium < 1M, large ≥ 1M cm3).
- The baseline readings are: A = LARGE_PREDATOR tag, D = LP tag AND band large, F = cluster max > 1, caverns = DF depth +
  BIZARRE ceiling, uniform random picks, animal people included.

## 1. Headline results

1. **Step 4 never terminates on its own.**
   - Strict caps were reached in **0 of 57,120** non-empty rosters, across all 34 configs. The lenient reading ("1-3",
     "0-1") was also reached in 0.
   - Every roster ended on the no-progress guard. The guard is not optional.
   - Why:
     - The caps are global but the classes are layer-bound. The land layer has no flying-vermin classes, and the flying
       layer has no medium predators or medium prey.
     - Under the tool's bands no land species is a "large predator" at all.
     - In the baseline, 79% of land rosters also stopped with a class still unfilled while the pool held candidates.
       Those candidates had no allowed relation to anything in the roster, or were high-value and so barred from step 3.
   - There is no runaway: caps bound a roster at 14. Observed maximums were 10 species and 15 edges (baseline).
2. **The tool's size bands turn the classic predators into "small predators", and rule B then makes them vermin-eaters.**
   - wolf 40k, dingo, hyena, cougar, leopard, jaguar, cheetah, black bear 120k and anaconda are all band *small*.
   - Solitary ones (cougar, leopard, jaguar, cheetah, black bear, anaconda) may eat **only vermin** (0 unit prey).
   - Pack ones (wolf, dingo, hyena, coyote) reach "small" prey only through rule F. "Small" includes the 140k deer.
   - Lion, tiger, grizzly, polar bear and crocodile are *medium*.
   - Only 5 natural predators are *large*: JABBERER, ORCA, SEA_SERPENT, SHARK_GREAT_WHITE, SPERM_WHALE.
   - The land layer's large_pred slot is empty in 100% of rosters (the pool never has one).
   - Example (examples.md): a temperate roster where COUGAR eats BEETLE, SLUG, LIZARD, TERMITE, and the top predator is
     BEAR_GRIZZLY_MAN.
3. **Bands are also too coarse in the other direction.**
   - **5,756** allowed unit pairs have prey ≥ 3× the eater's mass. Examples: BIRD_KEA > DEER (140×), BIRD_BUZZARD >
     DEER (100×), LION > SPERM_WHALE.
   - The cause is pack +1 on a "small" band that spans 1k to 150k.
   - Pair counts by config: A(ii) adds predator-on-predator pairs such as BADGER > BEAR_BLACK; the band fixes (FIX)
     raise the count to 18,304; the tool's own mass-ratio test (`size=ratio`) cuts it to 601–2,059.
4. **Only 43% of baseline predator edges are ones DF will act on** (surface; flying 26%). The rest:
   - edges onto vermin: 43% of land edges, 47% of flying edges. Vermin are not units, so no unit fights them.
   - edges whose eater is BENIGN (eagles, falcons, owls, fox, badger, otters, orca). P1 and T1 measured 0 attacks for
     these.
   - With DF-actable edges only, step 8 drops from 78% to 60% on the surface.
   - Every raptor of the TROP_WETLAND flying pool is BENIGN, so that layer has no actable predator at all.
5. **High value = giants.**
   - All 178 giants carry PETVALUE 500, so every giant is HV. Giants are 62–100% of the HV species in each pool.
   - The seed is a giant in **75% of land rosters and 100% of flying rosters**.
   - Step 3 excludes HV species, so giants enter a roster only as the seed or at step 2. The giant_pred slot is filled in
     79% of land rosters, but only because the seed was a giant or its step-2 partner.
   - The seed takes ≥ 50% of the edges in 26% of land, 44% of water, 86% of cav3 and 100% of deep rosters.
6. **Animal people are a third of every surface pool (37–44%) and act as predators.**
   - Animal people are 20% of all surface roster nodes. Sentients fill 30% of predator nodes (baseline surface) and 35%
     in caverns (civ races).
   - Examples: BEAR_GRIZZLY_MAN eats COUGAR; RODENT MAN and TROGLODYTE hunt cave rats.
   - With `sentient_pred=False` that share is 0.
7. **Rule D starves sentients where no large LP exists.**
   - Baseline D (LP and ≥ 1M) admits only JABBERER, SEA_SERPENT, SHARK_GREAT_WHITE and 7 giant LPs.
   - An uneaten sentient appears in **95% of cav1, 54% of cav2 and 36% of cav3 rosters**, and 13% of land rosters.
   - AMPHIBIAN_MAN, REPTILE_MAN, RODENT MAN, TROGLODYTE, GREMLIN, BAT_MAN, OLM_MAN and CAVE_SWALLOW_MAN have no
     allowed eater in their pool at all.
   - D = LP tag alone brings this to 0 structurally (12% of cavern rosters still end with one uneaten).
8. **E "medium to small" leaves large prey without any eater unless a pack exists.**
   - 13% of flying rosters and 5–16% of cavern rosters are **singletons**. The HV seed is a ≥ 1M species nothing may
     eat: GIANT_THRIPS, GIANT_FLY or GIANT_MOSQUITO (2,000,000 cm3, larger than every giant raptor), or DRALTHA 2.5M /
     RUTHERER 3M in the caverns.
   - Step 2 finds an empty list, and step 6 finds `no_relation_in_pool` for every one.
   - **Step 6 connected 0 of 102 isolated nodes.** An isolated node after step 5 has, by construction, no allowed
     relation in the roster, and here none in the pool either.
9. **Step 5 does not blow up density.**
   - Edges grow ×1.1–1.3 over the step 2–4 tree (max ×2.2) in the baseline, and ×1.5–2.2 under the fixes (max ×2.6).
   - The caps keep rosters at 1–12 species.
10. **Rule A barely matters in practice.**
    - A(i) and A(ii) differ on 387 pool pairs, but change only 4 of 2,000 rosters. Predators are one per class, so
      predator-on-predator candidates rarely arise.
    - D(size) gave the same numbers as D(tag AND size): the only band-large non-LP predators are ORCA and SPERM_WHALE
      (both BENIGN).
11. **Rule F is load-bearing** (it is the only thing that lets small predators eat units).
    - F = none raises surface isolation from 6% to 24% and drops cavern step 8 from 91% to 3%.
    - F = LP-and-cluster puts isolation at 14%.
12. **Seasonal breaks are rare and vermin-only.**
    - 20% of flying rosters have a bird vermin whose only prey (moth, butterfly, firefly, dragonfly) is NO_WINTER.
    - 0% on land or water: NO_WINTER is on only 22 wildlife species, and every multi-prey predator keeps one prey in
      winter.
    - Caverns have no season flags.
13. **Rosters are very seed-sensitive.**
    - Mean pairwise Jaccard across 20 seeds: 0.17 land, 0.16 flying, 0.27 water, 0.34–0.41 cav1/cav2.
    - 17–20 distinct rosters per 20 seeds.
    - Deep is 1.00: IMP_FIRE + MAGMA_CRAB every time, the only 2 natural magma-sea species.

## 2. Baseline per layer (rules as written)

| layer | rosters | mean size | isolated after 6 | step 8 | step 8 (DF-actable) | edges DF-actable | edges onto vermin | uneaten sentient | caps filled where pool allowed |
|---|---|---|---|---|---|---|---|---|---|
| land | 560 | 9.4 | 0% | 86% | 74% | 53% | 43% | 13% | 21% |
| flying | 560 | 7.0 | 13% | 67% | 43% | 26% | 47% | 0% | 80% |
| water | 240 (+320 empty) | 6.3 | 0% | 81% | 68% | 53% | 29% | 11% | 12% |
| cav1 | 80 | 6.5 | 5% | 95% | 95% | 49% | 48% | 95% | 0% |
| cav2 | 80 | 7.0 | 16% | 82% | 82% | 45% | 50% | 54% | 0% |
| cav3 | 80 | 3.2 | 12% | 86% | 86% | 100% | 0% | 36% | 0% |
| deep | 80 | 2.0 | 0% | 100% | 100% | 100% | 0% | 0% | 100% |

**Cap fill, baseline** (roster got ≥ 1 / pool had any): this measures how often each slot can be filled at all.

| layer | giant pred | large pred | medium pred | small pred | giant/large prey | medium prey | small prey | ground/fish v | colony v | bird v | insect v |
|---|---|---|---|---|---|---|---|---|---|---|---|
| land | 79/100 | 0/0 | 24/64 | 100/100 | 59/100 | 79/100 | 98/100 | 100/100 | 100/100 | 0/0 | 0/0 |
| flying | 87/100 | 0/0 | 0/0 | 87/100 | 93/100 | 0/0 | 87/100 | 0/0 | 87/100 | 87/100 | 87/100 |
| water | 47/100 | 15/33 | 73/100 | 67/67 | 42/100 | 11/33 | 97/100 | 67/100 | 0/0 | 0/0 | 0/0 |
| cav1 | 0/0 | 0/0 | 89/100 | 95/100 | 5/100 | 38/100 | 95/100 | 95/100 | 0/0 | 95/100 | 0/0 |
| cav2 | 0/0 | 8/100 | 59/100 | 84/100 | 16/100 | 28/100 | 84/100 | 84/100 | 0/0 | 84/100 | 0/0 |
| cav3 | 0/0 | 9/100 | 36/100 | 88/100 | 12/100 | 0/0 | 88/100 | 0/0 | 0/0 | 0/0 | 0/0 |
| deep | 0/0 | 0/0 | 0/0 | 100/100 | 0/0 | 0/0 | 100/100 | 0/0 | 0/0 | 0/0 | 0/0 |

**Refusal reasons, baseline** (all ordered pairs with a predator first, in all rosters):

| outcome | share of pairs |
|---|---|
| allowed | 55% |
| E | 23% |
| D | 8% |
| B | 8% |
| giant predator uneatable | 5% |
| A | 1% |

Step 7 frequencies put 12–23% of the weight on predators (surface) and 20–47% underground.

## 3. Failure modes, with rosters (examples.md has the edges)

| mode | where / how often (baseline) | example |
|---|---|---|
| Never terminates without the guard | 100% of non-empty rosters | every roster |
| Classic LP as vermin-eater (bands + B) | cougar/leopard/jaguar/cheetah/black bear: 0 unit prey | TEMP land summer s5: COUGAR > BEETLE, SLUG, LIZARD, TERMITE |
| Absurd size pairs (band + pack) | 5,756 allowed unit pairs ≥ 3× | BIRD_KEA > DEER, BIRD_BUZZARD > DEER |
| Singleton roster (HV seed with no relation) | flying 13%, cav1 5%, cav2 16%, cav3 12% | TAIGA flying: [GIANT_THRIPS]; cav1: [DRALTHA]; cav2: [RUTHERER] |
| Giant-seeded webs | seeds are giants: land 75%, flying 100% | GIANT_SQUIRREL_RED, GIANT_TICK, GIANT_WREN, GIANT_CROW as seeds |
| Sentient uneaten (D) | cav1 95%, cav2 54%, land 13% | cav1: RODENT MAN, TROGLODYTE, AMPHIBIAN_MAN uneaten |
| Sentient as top predator | 30% of predator nodes are sentient | BEAR_GRIZZLY_MAN > COUGAR, ELK; RODENT MAN > DRUNIAN, RAT_LARGE |
| Rule-C bird vermin with nothing to eat | cav1 95%, cav2 84% (caverns have no flying insects) | BIRD_SWALLOW_CAVE, BAT in every cav1/2 roster |
| Web DF cannot act on | flying: 74% of edges non-actable | TEMP flying s1: GIANT_KESTREL*, BIRD_EAGLE* are the only predators, both BENIGN |
| Degenerate deep layer | 100% identical | [MAGMA_CRAB, IMP_FIRE] (IMP_FIRE > MAGMA_CRAB exists only through pack +1) |
| Empty water layer | 4 of 7 embark sets have no water biome | TEMP, SAVANNA, TAIGA, DESERT |
| Step 8 fails in a connected web | land 14% | TEMP land s1: BEAR_GRIZZLY and RATTLESNAKE are both solitary |

## 4. Contradictory or mutually exclusive requirements actually hit

1. **Caps × layers.** One cap table for all layers cannot be met.
   - Land can never hold the two flying-vermin slots, flying never holds medium predators or prey, and the cav3 and deep
     pools have no vermin slots.
   - The strict step-4 stop condition is unreachable in 100% of rosters. Caps must be per layer, or "maximum where the
     pool allows".
2. **HV seed × step 3's non-HV rule.**
   - Giants are all HV, so the giant slots fill only from steps 1-2.
   - With hv_fallback, giants per roster rise from 1.4 to 1.9 and uneaten sentients fall from 7% to 0% (surface).
3. **E ("medium to small") × the giant/large-prey slot.**
   - The slot is filled by species that only a pack large/giant predator may eat.
   - Result: singletons (§3), and 5–16% of cavern rosters with uneaten big prey.
   - E_large removes them: surface isolation 0%, cavern step 8 98%.
4. **D (tag AND size) × caverns.** Of all cavern predators only JABBERER (cav2-3) qualifies. Sentient civ races are
   common in every cavern layer, so D and "every node connected" (step 6) are mutually exclusive in 54–95% of cav1/cav2
   rosters.
5. **B × DF.**
   - Rule B's small-predator edges all target vermin, which DF cannot execute. Rule C's edges are vermin-to-vermin.
   - With B as written, small predators contribute **no DF-actable edges at all**. Step 8 counted on DF-actable edges
     loses 12–26 points on the surface.
6. **Sentients prey-only (a fix) × step 8 in cav1.**
   - The only pack predators in cav1 are sentient civ races (RODENT MAN, TROGLODYTE, AMPHIBIAN_MAN, cluster 10).
   - The non-sentient cav1 predators are all LP of band medium, and cmax 1.
   - With `sentient_pred=False`, step 8 is impossible in cav1 (0%).
7. **A (predators may eat predators) × the class upgrade.**
   - Once LP moves up a class (`lp+1`) and D admits LP, two LPs in adjacent slots eat each other.
   - That gives mutual predation in 36% of surface and 75% of cavern rosters, e.g. COUGAR_MAN ↔ BEAR_GRIZZLY_MAN and
     TROGLODYTE ↔ CROCODILE_CAVE.
   - The tool's own peer rule (eat a predator only if ≥ 2× its mass) removes all of it.
8. **Size bands × realism.** Relaxing the band windows to fix connectivity (FIX: 18,304 absurd pairs) and tightening
   them to fix absurdity (FIX_ratio: isolation 25% underground, and deep becomes a singleton because IMP_FIRE 6k cannot
   take MAGMA_CRAB 30k) pull against each other.

## 5. Minimal rule changes and the re-run numbers

One factor at a time from baseline (surface / caverns+deep). The full table is in tables.md, "Config comparison".

| change | fixes | surface isolated | step 8 | DF-actable edges | cavern uneaten sentient | side effect |
|---|---|---|---|---|---|---|
| baseline | — | 6% | 78% | 43% | 46% | — |
| `seed_linked`: seed must have ≥ 1 relation in the pool | singletons | **0%** | 80% | 41% | 52% | none |
| `E_large`: large/giant eat up to large | big prey uneaten | 0% | 78% (caverns 98%) | 40% | 46% | — |
| `D_tag`: any LP may eat sentients | D starvation | 6% | 79% | 46% | **12%** | more LP-eats-sentient pairs |
| `cls_lp+1`: LP moves up one class | LP-as-vermin-eater | 6% | 81% | 51% | 49% | 10,264 absurd pairs (bands) |
| `benign_filter`: BENIGN never gets a predator slot | un-actable webs | 10% | 80% | **58%** | 47% | flying loses most predators |
| `weight_freq`: DF FREQUENCY weights | AP flood | 6% | 74% | 43% | 47% | APs per roster 1.6 → 1.0 |
| `hv_nogiant` | giant-seeded webs | 2% | 78% | 45% | 46% | giants still enter at step 3 |
| `sentient_prey_only` | sentients as predators | 6% | 64% | 41% | 0% | step 8 falls (cav 52%) |
| `peer` (the tool's rule) | mutual predation | 6% | 77% | 43% | 46% | none in the baseline |

**Combined sets** (all include seed_linked, lp+1, E_large, B+small, D_tag, frequency weights, giants not HV, hv_fallback,
benign_filter):

| config | layers | mean size | isolated | step 8 | step 8 (DF-actable) | DF-actable edges | mutual predation | sentient share of predators | absurd pairs (≥ 3×) |
|---|---|---|---|---|---|---|---|---|---|
| FIX | surface | 9.2 | 2% | 82% | 82% | 79% | 36% | 36% | 18,304 |
| FIX | caverns+deep | 7.2 | 0% | 100% | 100% | 85% | 75% | 50% | |
| **FIX3** (= FIX + sentient prey-only + peer) | surface | 9.4 | 2% | 75% | 75% | 77% | 0% | 0% | 8,190 |
| **FIX3** | caverns+deep | 6.0 | 0% | 75% | 75% | 87% | 0% | 0% | |
| **FIX3_ratio** (bands → the tool's mass test) | surface | 9.3 | 2% | 71% | 71% | 74% | 0% | 0% | **601** |
| **FIX3_ratio** | caverns+deep | 5.1 | 25% | 50% | 50% | 83% | 0% | 0% | |

**FIX3 per layer**:
- land: 11.6 species, step 8 91%, 80% actable. Caps are filled wherever the pool allows in 100% of rosters, so the guard
  is then equivalent to "caps reached".
- flying: step 8 62%, 60% actable. TROP_WETLAND has no non-BENIGN flier, so its 80 flying rosters are 32 singletons plus 48 bird-vermin/insect-vermin
  pairs.
- water: step 8 67%, 88% actable.
- cav1: step 8 0% (contradiction 6).
- cav2 and cav3: step 8 100%.

**Removing one element of FIX** (tables.md):
- B+small removed (`FIX_keepB`, measured on FIX): cavern "predator without prey" 0% → 11%.
- D back to tag AND size (`FIX_keepD`, measured on FIX): cavern uneaten sentients 0% → 59%.
- benign_filter removed (`FIX_keepBenign`, measured on FIX): DF-actable edges 79% → 61%.
- `FIX_keepE` (E back to "medium to small") changes little once `seed_linked` is on. Surface isolation stays at 2%: the
  singletons it caused came through the seed.

**Recommended minimal set** (in order of payoff):
1. Keep the no-progress guard, and define caps as per-layer maxima ("filled wherever the pool allows").
2. `seed_linked`.
3. Classify by LP (`lp+1`), or better, replace the B/E/F band windows with the tool's existing mass test (`size=ratio`,
   with pack group^0.75). It removes 90% of the absurd pairs. Its cost: some big prey and the deep layer have no eater,
   which is realistic. Accept those as "apex prey" rather than forcing step 6.
4. D = LP tag.
5. Predator slots only for non-BENIGN species. Alternatively, keep BENIGN predators as decorative and have the tool flip
   BENIGN off at arm time (T1: the BENIGN flag blocks acting; E32b: an LP flip made a BENIGN badger attack).
6. Sentients never eat, with a pack exception for the cavern civ races if step 8 must hold in cav1.
7. The tool's peer rule for predator-on-predator edges.
8. DF FREQUENCY-weighted picks, and giants not counted as "high value".
9. Treat every vermin edge (rules B and C) as a **stock** effect the tool applies. Vermin are df.vermin objects the tool
   already manages; they are not DF relations.

**Not fixable by rules on the DF side** (from W2 and findings):
- The tool's ecoWrite excludes water-layer units (realm nil). The water-layer webs here (88% "actable" by BENIGN/unit
  criteria) are therefore unwritable today until the realm fix lands.
- DF itself spawns one LARGE_PREDATOR group per map (wiki). FIX3 land rosters hold 1.6 non-giant LPs on average, so
  any second LP must be placed by the tool.

## 6. Caverns: the BIZARRE score (bizarre.tsv, bizarre-summary.txt)

**The score and DF's own depth**
- 67 subterranean creatures are scored; 48 are natural and in chasm/water.
- The score rises with DF's own depth:

  | UNDERGROUND_DEPTH min | mean score | n |
  |---|---|---|
  | 1 | 3.3 | 34 |
  | 2 | 5.1 | 11 |
  | 3 | 8.7 | 3 |

- Spearman ρ with depth min is 0.49 (0.62 over all 62 classes). **DF's depth already encodes most of the weirdness.**
- Band 1 (score ≤ 3) holds 25 of the 34 depth-1 species.

**Candidates per cavern layer** (natural):

| rule | cav1 | cav2 | cav3 |
|---|---|---|---|
| DF depth only | 34 | 43 | 21 |
| score tertile only | 29 | **5 (degenerate)** | 14 |
| depth + ceiling (used) | 25 | 32 | 21 |

**What the ceiling removes**
- From cav1: SPIDER_CAVE (9), LOBSTER_CAVE (7), GIANT_EARTHWORM (6), POND_GRABBER (6), HELMET_SNAKE (5),
  SERPENT_MAN (5), CAVE_FISH_MAN (5), ANT_MAN (4), FISH_CAVE (4).
- From cav2: additionally FLOATING_GUTS (10), CAVE_FLOATER (8), SPIDER_CAVE_GIANT (9), VORACIOUS_CAVE_CRAWLER (5).

**Effect on the rosters**
- The pure-score cut is too blunt: many species tie at 3.
- The ceiling cut changes cavern step 8 from 77% (depth only) to 91%, and uneaten sentients from 23% to 46%.
- cav3 is small (21 candidates, 3.2-species rosters) because DF puts few natural species at depth 3.
- The scoring is transparent (10 components, weights in bizarre-cut.json). The score's value is as a tie-break inside
  DF's depth ranges, not as a replacement for them.

## Files

All in `roster/`:

| file | contents |
|---|---|
| rules.md | Every interpretation. |
| roster.py | The model and build(). |
| run.py | Configs and the sweep; writes runs/*.jsonl, 34 × 2,000 rosters. |
| analyze.py | Writes tables.md. |
| extras.py | Writes extras.md: classic-predator placement, absurd pairs, pool make-up, D structure, cavern cut. |
| examples.py | Writes examples.md. |
| feat.py | Writes features.json. |
| bizarre.py | Writes bizarre.tsv, bizarre-cut.json, bizarre-summary.txt. |
