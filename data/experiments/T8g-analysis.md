# T8g: do the layers compete for arrivals? A desk read of the T8-series data

Desk work only: no rig run. Script: `scripts/t8g-analyze.py` (pure Python, standard library). Run it with
`.venv/bin/python scripts/t8g-analyze.py` (about 4 s, seeded permutations). All numbers below are its output.

## Question

The T8f memory note says: "the surface cadence can stop while deep and cavern draws go on — layer competition is the candidate".
So the question is this. When more than one layer can draw (surface, cavern 1-3, magma sea, underworld), does a draw on one
layer take an arrival away from another, through one global gate or cap? Or does each layer draw on its own?

## Answer

**Each layer draws on its own. Nothing in 26 replicates shows layer competition.**

The surface stalls that prompted T8g come from the tool, not from DF:

- DF's surface gate is open only while **at most one flagged surface unit** is on the map (E1).
- A gated group of **one animal** therefore never holds that gate shut, so DF draws a second group behind it.
- The tool's release detaches the **oldest** gated group, which is often that singleton.
- The newer group stays flagged, and the surface waits for the tool's next release, 5-20 days later.

This mechanism explains T8d's ten-day wait and T8f clear rep 1's wait of more than 14.7 days. It explains all 36 slow releases.

## Data

| run | arms x reps | tool | notes |
|---|---|---|---|
| T8 20260921-131819 | steady, burst, trickle, dawn, follow x 2 | v5.10.0 | pattern study |
| T8b 20260921-150212 | trickle, dawn, follow x 2 | v5.10.2 | |
| T8c 20260921-155444 | dawn x 2 | v5.10.4 | |
| T8d 20260921-161410 | dawn x 2 | v5.10.6 | one ten-day wait |
| T8e 20260921-213219 | dawn x 2 | v6.1.2 | |
| T8f 20260921-233953 | held, clear x 2 | v6.1.2 | the 14.7-day wait |

The design is the same in every run:
- Fort: CTRL from `CTRL.preverify`.
- Window: about 100,800 ticks, from Spring day 14 to Summer day 14.
- Sampling: every 1,000 ticks.
- Tool settings: groups on, max 4 land groups, cavern_max 2, ecology on.
- All 26 replicates are valid, and the save was untouched in all of them.

**Every replicate had every layer open.** `pops.tsv` shows every cavern and deep entry above zero in every replicate.

**How a source is identified.** Each unit's population `cave_id` gives its source:
- -1 is the surface.
- 8, 13 and 25 are caverns 1, 2 and 3. This was checked by the z of every arrival (36-62, 29-33, 24-31) and by the tool's own
  `cavern0/1/2` group labels.
- 34 is the magma sea.
- 43 and 44 are the underworld.

The harness's `layer` column does not separate the three caverns.

**Definitions.**
- A **wave** is the arrivals of one species from one source that are listed at one sample.
- A **flagged** unit carries `flags2.roaming_wilderness_population_source` (`units.tsv` `flag_src`). These are the units DF
  counts against a source's gate.

**Readout traps honoured** (see memory, experiment-readout-traps):
- Arrivals are dated only to the sample interval.
- The first sample, about 1,100 ticks after load, carries DF's post-load fill: median 3 surface, 5 cavern and 1 deep waves. It
  is reported separately and left out of every rate and every test.
- T8e and T8f logged an extra snapshot 2-26 ticks after the start. It is not treated as a sample.
- A layer with no later arrival is reported as censored, not as zero.

## Per-layer table

All values are medians across the 26 replicates, with [min-max]. The first sample is excluded.

| layer | waves / 10k t | units / 10k t | first wave after the first sample, days | groups at once, mean | groups at once, max | DF-flagged units, mean |
|---|---|---|---|---|---|---|
| surface | 0.75 [0.50-1.20] | 2.44 [0.79-3.99] | 16.9 [0.9-27.7] | 2.59 [1.90-3.24] | 4 [3-5] | 4.5 [2.2-7.3] |
| cavern 1 | 0.60 [0.40-0.80] | 1.74 [0.50-3.08] | 23.5 [0.9-28.1] | 1.77 [1.31-2.56] | 3 [2-4] | 5.5 [2.0-8.3] |
| cavern 2 | 0.60 [0.30-1.00] | 2.05 [1.00-4.29] | 20.7 [0.9-59.6] | 1.99 [1.11-2.65] | 3 [2-6] | 6.1 [2.8-11.2] |
| cavern 3 | 0.50 [0.20-1.00] | 1.70 [0.30-3.87] | 19.4 [0.85-35.1] | 2.18 [1.42-4.30] | 4 [2-7] | 7.2 [3.0-11.9] |
| magma sea | 0.00 [0-0.30] | 0.00 [0-0.50] | 83.6 (23 of 26 censored) | 1.00 | 1 [1-3] | 4.7 |
| underworld | 0.40 [0.30-0.80] | 1.05 [0.80-1.39] | 23.5 [17.1-31.1] | 1.36 [1.01-1.88] | 2 [2-4] | 3.6 |
| caverns 1-3 | 1.64 [1.19-2.29] | 5.54 [2.99-8.27] | 0.9 [0.85-23.5] | 6.12 [4.96-7.55] | 8 [6-11] | 17.8 [12.5-24.6] |
| all layers | | | | | 14 [12-16] | |

- The surface rate is held down by the tool's land gate: gaps of 5-20 days by pattern.
- The cavern rates are DF's own. The tool released a cavern group about twice per run.
- No layer approaches a common ceiling. The all-layer maximum varies from 12 to 16 groups between replicates, and the caverns
  held up to 43 flagged units.

## Tests and results

### 1. Each source has its own gate

The test counts the flagged units of the **same** source that are left at each wave's own sample, leaving out the units first
listed there. DF's rule (E1) predicts at most one.

| source | waves | at most 1 flagged left |
|---|---|---|
| surface | 198 | 91% |
| cavern 1 | 147 | 83% |
| cavern 2 | 165 | 72% |
| cavern 3 | 131 | 64% |
| underworld | 114 | 82% |

The surface follows its own one-unit rule. Most cavern waves do too, but with more exceptions.

When a source's own gate was seen open at the start of an interval, that source drew within that same interval every time:

| source | own gate open at the interval start | drew in that interval |
|---|---|---|
| surface | 13 | 13 of 13 |
| cavern 1 | 11 | 11 of 11 |
| cavern 2 | 15 | 15 of 15 |
| cavern 3 | 8 | 8 of 8 |
| underworld | 8 | 8 of 8 |

When the surface gate was closed at an interval's start, a surface wave arrived in 0.068 of intervals. Those are gates that opened
inside the interval.

In 26 replicates, **an open surface gate never once went a full sample without a surface draw.** Competition needs exactly that
event: an open gate whose draw went elsewhere. It did not happen.

### 2. A surface draw does not change the other layers' hazard

In the same interval:

| other layer | interval with a surface wave | interval without one |
|---|---|---|
| any cavern wave | 0.152 | 0.158 |
| any deep wave | 0.035 | 0.050 |

### 3. Waves in the same interval, against a circular-shift null

The null shifts each replicate's own series, 2,000 shifts, seed 8.

| pair | observed | null median | P(null <= obs) | P(null >= obs) |
|---|---|---|---|---|
| surface x cavern | 26 | 26.0 | 0.53 | 0.56 |
| surface x deep | 6 | 8.0 | 0.28 | 0.84 |
| cavern 1 x cavern 2 | 19 | 9.0 | 1.00 | **0.003** |
| cavern 1 x cavern 3 | 13 | 7.0 | 0.97 | 0.057 |
| cavern 2 x cavern 3 | 22 | 8.0 | 1.00 | **<0.001** |
| caverns x deep | 30 | 18.0 | 1.00 | **0.004** |

- **Surface against the underground:** what independence predicts.
- **Underground against underground:** the layers draw **together** more often than chance. That is a shared clock or a shared
  trigger, the opposite of competition.

### 4. Across replicates

Spearman correlation of waves per 10k ticks, n = 26:

| pair | rho | p |
|---|---|---|
| surface vs caverns | -0.24 | 0.24 |
| surface vs deep | -0.02 | 0.92 |
| caverns vs deep | +0.06 | 0.77 |
| cavern pairs | -0.03 to +0.08 | ≥ 0.68 |

- **Within cells** (rep 1 minus rep 2, which removes the arm and the tool version; 13 cells): surface vs caverns r = -0.01, with
  5 opposite signs and 8 the same.
- **Variance ratio.** Var(total) / Σ Var(layer) = 0.84. The 95% band under independence is 0.55-1.53, p = 0.27, so independent.
  A shared budget would push the ratio well below 1.

### 5. Long surface waits are closed surface gates

- 165 surface waits lasted more than 2 days.
- In 155 of them, **two or more flagged surface units stood at every sample.**
- Of the 2,160 samples inside those waits, only 10 showed the gate open. Each of those was followed by a surface draw in the next
  interval.
- Other-layer waves inside the waits: 449 intervals, against 447.5 expected at each replicate's own rate. The underground did not
  draw more while the surface waited.

### 6. Slow releases, and why they are slow

- 154 tool land releases were read from the ledger.
- The median release-to-wave time was 0.90 days (IQR 0.65-1.23).
- 36 releases were slow (more than 2 days plus a sample, or no wave at all).
- In **all 36**, two or more flagged surface units stood at every sample from a day after the release onward.
- The release had detached a **one-animal** group in 27 of the 36 slow releases, against 37 of the 118 prompt ones (Fisher
  two-sided p = 5e-6).

The named cases:
- **T8f clear rep 1.** On Summer day 1 the tool detached `WOMBAT x1`. `BIRD_RAVEN x3` (#223-225) had arrived on Spring day 81
  behind the gated singleton and stayed gated and flagged for the last 14.7 days.
- **T8d dawn rep 2, the ten days.** On Summer day 1 the tool detached `BIRD_OWL_GREAT_HORNED x1`, and three or more flagged units
  stood for the next 10.0 days.

## What the data can and cannot answer

**It can answer:**
- Whether an open layer takes arrivals from another while all layers are open: it does not, at a resolution of 1,000 ticks.
- Why the surface stalled: a closed surface gate behind a one-animal gated group.
- That no common ceiling on groups or units binds up to the totals seen: 16 groups, and 43 flagged cavern units.

**It cannot answer:**
- **"A layer alone vs with others open."** No T8 replicate closed a layer. This is the controlled contrast the question asks
  for, and it does not exist on disk. Section 1's open-gate hazards (13 of 13 regardless of the other layers) and section 5's
  independence are the observational substitute.
- **Competition finer than one sample.** For example, DF serving one source per check and the next a few hundred ticks later.
  This is invisible at 1,000-tick sampling. It would cost at most a few hundred ticks per draw, which is below anything a player
  sees.
- **Why the underground layers co-occur.** The cause could be a shared DF clock for underground draws, cavern deaths clustering
  (the cavern fights of HC1/HC2), or a harness listing effect.
- **Why the cavern one-unit rule is weaker.** It holds for 64-83% of cavern waves. The cavern source may be finer than a cave,
  or the rule may differ underground.
- **Water.** CTRL has no water layer.
- **Other forts and worlds.** All the data come from one fort (CTRL), one world, and one 100,800-tick window per replicate,
  spring into summer.
- **Ceilings above the range seen.** A global ceiling higher than the totals observed cannot be ruled out.

## Consequences

1. **Drop layer competition as an explanation** in the memory note and the Wilderpop report §8. The T8f line should read:
   "a release that detaches a one-animal gated group leaves a newer group flagged; the surface waits for the next release".
2. **Tool fix, seasonal-wildlife v7.0 `detachOldest`, line about 3277.** The surface release still picks the oldest gated
   group. To actually open DF's gate, the release should do one of the following:
   - detach gated land groups until at most one flagged surface unit remains; or
   - skip, or merge into the next group, a gated group whose flagged count is at most 1, since it was never holding the gate.
   The pattern promise "release, then the wave (usually)" then becomes "release, then the wave".
3. **The roster and limits can treat each layer as its own budget.** Cavern and surface groups at once do not trade off, so
   `limits` per layer, and v7's `layer_groups` per cavern, need no cross-layer coupling.
4. **Optional decisive test, only if wanted (T8h).**
   - Fort and window: CTRL, 30,000 ticks, the surface released every 1,500 ticks as in F1.
   - Arms: caverns as is, vs every cavern species at frequency 1 (CAVERN.SUPPRESSED).
   - Readout: surface waves per 10k ticks.
   - Two replicates per arm, about 25 minutes in all.
   - Independence predicts equal rates.
