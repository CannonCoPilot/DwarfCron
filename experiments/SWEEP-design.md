# SWEEP: tuning seasonal-wildlife v7.0's fixed values against how busy the map is (tracker item 11)

**Status (1 Oct 2026 review):** SW1–SW7 ran on the night of 30 Sep – 1 Oct, with reruns SW1R, SW2R (reversed cell order) and SW3B
(SW3 counted the wrong groups), all on DFHack 53.16-r1.1 against v7.0 (deployed, unmerged). Desk D1 ran (`experiments/SWEEP-D1.md`).
SW8 has not run: it waits on the user's decisions about the defaults. Results and verdicts are in section 5; the new designs the
results call for are in section 6. The rig moved to DFHack 53.16-r2 on 1 Oct, so SW8 and anything new run only after the r2
re-validation (open item revalidate-dfhack-r2). The original design text (sections 0–4) is kept as written on 30 Sep.

**What it does:** tunes each hard-coded value of seasonal-wildlife v7.0 against one measure of how busy the map is. Each value
gets 3 levels, always including the current one. The rule is **two replicates per arm**, with as few arms as possible.

**Sources:**
- `data/eco-desk/findings.md` (ECO results; block IDs in [brackets])
- `data/eco-desk/v2/guilds/design.md` (the builder)
- `scripts/eco-run.py`, `scripts/cx-experiment.py`, the `experiments/*.json` manifests
- the tool at `~/Claude/Projects/seasonal-wildlife/scripts/seasonal-wildlife.lua` (v7.0.0 WIP, f986b50)
- `data/experiments/T8g-analysis.md`

---

## 0. Where each value lives, and how a run sets it without a code change

Several of the listed values are **not in the tool**. They live in the desk roster builder (`roster2.py`). The tool reaches
them only through the roster and through per-species `odds` (the raw FREQUENCY).

| value | current | lives in | set it with |
|---|---|---|---|
| FREQUENCY ladder steps | `LADDER22` (see note) | builder `roster2.py` | builder output → per species `seasonal-wildlife odds TOKEN N` (cfg `odds`, ≥ 1). No tool code change. The builder needs a predator-multiplier knob (desk, trivial) |
| x3 pack bonus | `pack_pref=3.0`, `pack_pred_only` | builder only (pick weight) | desk config. A roster reaches the fort via `roster` / `seasons` verbs (cfg `allow`, `assign`) |
| pack-mass floor | 5% | tool `cfg.v7.pack_floor`, builder `mass_floor` | `seasonal-wildlife v7 pack_floor 0.2` (0..10; 0 = off) |
| sneak bonus | 25% | tool `cfg.v7.pack_sneak`, builder `sneak_ratio` | `seasonal-wildlife v7 pack_sneak 0` (0 = off) |
| size preference (builder) | σ 1.0, floor 0.02, r* per guild | builder `Cfg.sigma` / `floor` | desk config |
| size preference (tool) | `PRED.ideal` 0.4, `PRED.sigma` 1.2 | tool local table, exported as `sw.PRED` | **no cfg key, no CLI.** See note 2 |
| groups at once, land | auto = floor(√(embark tiles)) + 1 (CTRL 4x4 → 5) | `cfg.limits.land.{groups,auto}` | `limits land groups N` (turns auto off); `limits land groups auto` |
| groups at once, cavern / water | auto per cavern or water body with `v7.layer_groups` | `cfg.limits.cavern` / `.water` | `limits cavern groups N`, `limits water groups N`; `v7 layer_groups on/off` |
| ecology cadence | 1,500 t | `cfg.ecology.cadence` | **no CLI verb.** In the pre, write the cfg, then `groups ecology on` (that reschedules the job). Receipt: `status`'s job table prints the cadence |
| nudge thresholds | far_tiles 40, far_ticks 3,000, radius 6 | `cfg.ecology.{far_tiles,far_ticks,radius}` | `groups nudge <far_tiles> <far_ticks> <radius>` (radius ≥ 2) |
| nudge switch | on | `cfg.ecology.nudge` | pre-Lua cfg write (the window has a toggle; no verb) |
| land gate gap | 5-20 days | `cfg.groups.gap_min_days` / `gap_max_days` | pre-Lua cfg write |

**Hard-coded with no lever:**
- `GROUPS_CADENCE` = 300 t (the scheduler)
- `SCAV.CADENCE` = 200
- `ENGINE.RADIUS` = 6

**Note 1, the ladder numbers.** The task quotes apex 3 / meso 3 / grazer 6 / other prey 5 / shore 4 and so on. That is
**LADDER21** (v2.1). The builder's current config `v22` writes **LADDER22**:
- land: apex 4, meso 2, grazer 10.5, prey 8.75, shore 7
- flying: birds 30
- water: fish 12

v2.2 retuned it so predators make about 16% of land arrivals. The sweep therefore treats the ladder as one dial, **the
predator multiplier** on the predator steps with the prey steps fixed. It is applied to whichever ladder is adopted.

**Note 2, the tool's size preference.** `preference()` only orders the lists from `matchPrey` (`pairGuarantee`, UI). The
relation write uses `MODEL.reaches` and the pack floor. So at runtime the tool's size preference should not change how busy the
map is.

Patching `sw.PRED` from a pre-step is risky. The scheduled job may run a separate script copy (memory:
dfhack-script-copies), so the patch needs a receipt from inside the job. If the value is ever swept on the rig, add a cfg key
first (a one-line change).

**Do this before any natural-arrival run (from T8g).**
- `detachOldest` (seasonal-wildlife.lua ~3277) releases the *oldest* gated land group. When that group is a single animal,
  it was never holding DF's gate (at most one flagged unit). DF had already drawn a second group behind it, and that group stays
  flagged.
- In T8, 36 of 154 releases stalled for 2-20 days this way, and 27 of the 36 had detached a one-animal group.
- Fix the release (detach until at most one flagged surface unit remains) before SW3 and SW8. If it is not fixed, log it as a
  confound: it adds 5-20-day holes to the arrival rate W in about one release in four.

---

## 1. The busy-ness measure

Everything below comes from what the rig already logs:
- cx-experiment's `units.tsv` (every wild unit, every sample: layer, `ref6`, `flag_src`, dead, inactive) and `events.tsv`
  (arrivals, departures, deaths)
- `cx-eco watch` / `read` (eventful UNIT_ATTACK counts per attacker>defender race, and Death incidents with killer, victim
  and cause), called from a manifest's `every`
- the tool's `groups` status line (pairs written, nudges, slotted) and the ledger

### Components

Each component is computed per replicate, per layer L (surface; caverns 1-3; each water body on BOATS), and per window. A
window is the run, or its part inside one season: year tick ÷ 100,800. The first sample is always dropped (DF's post-load
fill; T8g).

| | component | definition | source |
|---|---|---|---|
| G | groups present | Mean, over samples, of the distinct wild groups alive on L. A group is the arrivals of one species from one source that are first listed at one sample. Units present at the start are grouped by species and population. This is the same key as `t8g-analyze.py` | `units.tsv`, `events.tsv` |
| W | arrivals | Arrival waves per 10k ticks on L | `events.tsv` |
| A | fights | **Attack-intervals** per 10k ticks: the number of (attacker race > defender race, sample interval) cells with at least one wild-on-wild attack. Counting intervals, not attacks, stops one long fight from dominating (HR: one lamprey made 590 attacks). Layer = the attacker's | `cx-eco read` attacks, differenced per read |
| K | kills | Deaths of wild units whose killer is a wild unit, per 10k ticks | `cx-eco read` death incidents |

### The index

B = (G/G₀ · (W+½)/(W₀+½) · (A+2)/(A₀+2) · (K+½)/(K₀+½))^¼

- B is a geometric mean of ratios to the **control arm of the same run**, which is the current value.
- The pseudo-counts are about half the smallest non-zero rate seen (T8g; CAL; DOM2), so a zero cannot sink the index.
- B = 1 means as busy as today. B is reported per layer and per season window, and always next to its four components.
- **Absolute companion, for the user:** wildlife events per in-game day = (waves + kills + attack-intervals) per 1,200 ticks.
  A target band can then be set in player terms once the baseline is known.

### Guards

A level that breaks a guard is out, however busy it is.

1. **Fort harm.** Deaths of citizens or fort animals caused by wild units, and wild-on-citizen attack-intervals, must not
   exceed the control's.
2. **Speed.** The stopwatch rate (manifest key `stopwatch`) must be at least 90% of the control's in the same run (memory:
   fps-load-facts; +200 wild units cost 12%). Arms are interleaved so DF process age does not bias them: rep 1 in order, rep 2
   reversed, and DF restarted before each run.
3. **Persistence.** No roster prey species may have its entry at 0 for more than half the window (N1). Report hunters lost to
   prey.
4. **Visibility.** Report nudges per season. A nudge is a teleport the player can see.

### Decision rule (two replicates)

- A level **differs** from the control only if both of its replicates fall outside the control's two-replicate range on B
  (the 2-of-2 rule of T8 and DOM2). With n = 2, only differences of about 1.5x or more will show.
- The **sweet spot** is the level that differs in the wanted direction and passes every guard.
- **Otherwise keep the current value.** No value changes without a measured reason.

### How to compute

One tally script reads a run directory:
- It reuses `t8g-analyze.py`'s loader for G and W (group key, first-sample cut, source by cave id).
- It parses the `eco ... attacks` and `eco ... death` lines that the manifest's `every` prints, for A and K.
- It splits windows at year tick 100,800.

It does not exist yet. It is about 150 lines, mostly reuse.

---

## 2. The sweep, value by value

### Shared conditions

- Tool v7.0 `preset`, `enable`, groups on, ecology on, `v7.domestic` off, livestock safe.
- `cx-load sustain` in the pre.
- fps 1000.
- Sampling: every 1,500 t. The `every` block runs `cx-eco read`, `groups` and `ledger 6 wave` every 3,000 t. T8f's polls at
  every 1,000 t doubled step wall time, 670 s against 315 s.

### Wall-time model

Per replicate: ticks ÷ rate + overhead.

| fort | rate | overhead per replicate |
|---|---|---|
| CTRL | 250 t/s (T8 median 243; range 118-321) | 2.5 min (T8 1.3 min, T8f 3 min) |
| BOATS | 206 t/s (FPS3b stopwatch) | 3 min |

So one replicate costs:
- CTRL: 30k t ≈ 4.5 min; 50.4k t ≈ 6 min; 60k t ≈ 6.5 min; 100.8k t ≈ 9.2 min.
- BOATS: 50.4k t ≈ 7 min; 100.8k t ≈ 11.2 min.

Add about 2 min per run for a DF restart. At the rig's slow end (150 t/s) every step time is about 1.7x.

### Window lengths, and why shorter than a season is safe

| window | used for | why it is enough |
|---|---|---|
| **30,000 t** | levers that act on encounters (cadence, nudge, floor, sneak) | The arena places the subjects, so arrivals do not drive the readout. DOM2 saw 37-88 attacks in 12k t; CAL's 7-wolf cells killed within 30k |
| **50,400 t (half a season)** | groups at once | The land gate cycles every 5-20 days (6-24k t), so 50k gives 2-8 cycles. ECO2-G resolved groups in 40k |
| **60,000 t** | the ladder | The F1 design (surface released every 1,500 t) gave 38 non-bird waves in 60k, about 76 per arm over two replicates. That puts about ±0.05 on a 20% predator share |
| **100,800 t (a full season)** | the confirmation run | Kills and persistence need it: a lone hunter makes about 3 kills a season (LONE) |

### The arena

SW1 and SW2 use one standard community on CTRL, so that encounter levers are never vacuous:

- **Placement.** `cx-eco spawn`:
  - 5 WOLF at the land spot.
  - 6 DEER, 6 WATER_BUFFALO and 4 ELEPHANT, each herd 45-60 tiles from the pack. That is beyond far_tiles 40, so the nudge is
    in play.
- **Adoption.** The pre then calls `sw.discoverGroups` (exported) so that the tool tracks the pack as one group. The pack floor
  reads the *tracked* group's mass; a stray unit is treated as hunting alone.
- **Mass bands.** The prey are chosen so that each pack-mass band holds one pair. With approximate cm³ figures (CAL: 7 wolves
  are 5.6% of an elephant):

  | prey | 5 wolves as a share of the prey's mass | band |
  |---|---|---|
  | deer | above 25% | sneak |
  | buffalo | about 20% | between the floors |
  | elephant | about 4% | below 5% |

  Desk receipt D2 (section 3) must confirm the bands with the tool's own masses before the run.
- **Subject receipt, per replicate** (memory: manifest-subject-receipt). Taken by 3,000 t:
  - `groups` lists `WOLF x5` as one group.
  - The ecology line shows pairs written above 0.
  - In the control, at least one nudge.

  A replicate that fails this is vacuous, and is reported as vacuous, not as a zero.

### Per value

| # | value | levels (current in **bold**) | fort | window | arms × reps | readout beyond B |
|---|---|---|---|---|---|---|
| a | ecology cadence | 500, **1,500**, 6,000 | CTRL arena | 30k | in SW1 | time from placement or arrival to the first written pair (ledger); relation rows alive per read |
| b | nudge | off, **40 t / 3,000 t / r6**, tight 20 / 1,500 / r6 | CTRL arena | 30k | in SW1 | nudges; pack-to-herd distance per sample; fort harm (a nudge can land a pack near the fort) |
| c | pack-mass floor | 0, **0.05**, 0.20 | CTRL arena | 30k | in SW2 | pairs written per band; hunters lost; kills per band |
| d | sneak bonus | 0 (off), **0.25**, 1.0 | CTRL arena | 30k | in SW2 | units given SNEAK. The prior is no lift (STL / STL2: skilled 10 of 48 runs with a kill vs 2 of 16 unchanged) |
| e | groups at once, land | 1, 3, **auto = 5** | CTRL natural arrivals | 50.4k | SW3: 3 × 2 | stalls (T8g method). ECO2-G found 3 ≈ 5 on a 4x4 (2.71 vs 2.60), so 8 is skipped as supply-limited and the informative end is the low one |
| f | ladder, predator multiplier | ×0.5, **×1**, ×2 | CTRL, F1 design (tool disarmed, roster FREQUENCY written by the pre, surface released every 1,500 t) | 60k | SW4: 3 × 2 | predator share of waves against f/Σf (F1). **The apex share against APX f** settles whether LARGE_PREDATOR is a separate DF pool (design.md §5, §8 open) |
| g | groups at once, cavern | 1, 2, **auto** (per cavern, `layer_groups`) | BOATS natural | 50.4k | SW5: 3 × 2 | cavern groups per cavern. Prior: the limit does not bind (ECO2-G; T8g: about 6 cavern groups at limit 2) |
| h | groups at once, water | 1, 2, **auto** (per body) | BOATS natural | 50.4k | SW6: 3 × 2 | Receipt: water-layer units present in the control (memory: three vacuous runs) |
| i | x3 pack bonus | 1, 2, **3**, 5 | desk D1 | — | 0 rig | pack/herd share, isolation, DF-actable edges over the 7 embarks × seeds. Goes to the rig (SW7) only if CTRL's roster changes |
| j | size preference (builder) | σ 0.5, **1.0**, off | desk D1 | — | 0 rig | v2 already found `nosizepref` within 2 points except seasonal breaks (4% → 2%). Rig only if the roster changes |
| k | size preference (tool `PRED`) | — | desk D3 | — | 0 rig | Show that it orders lists only. Make it a cfg key before any rig use |

SW1 and SW2 each share one control arm, which saves a duplicate control per value. Their arms:

- **SW1:** `ctl`, `cad500`, `cad6000`, `nudge_off`, `nudge_tight`
- **SW2:** `ctl`, `floor0`, `floor20`, `sneak0`, `sneak100`

---

## 3. Order and time budget (cheapest informative first)

**Desk first (no rig, about 1 h):**

- **D1.** Builder sweeps over the 7 embarks × 20 seeds:
  - pack bonus (i), size preference (j), and the ladder multiplier's predicted predator share (f).
  - Output: which levels change the **CTRL** and **BOATS** rosters at all.
  - Rule: a lever that changes no roster on these forts is decided at the desk and is not run.
- **D2.** Receipts:
  - The tool's masses for the arena pairs, confirming that the floor and sneak bands each hold a pair.
  - From T8's `units.tsv` (positions every 1,000 t, already on disk): how often each nudge level would have fired on CTRL's
    natural predators. If the off and tight levels would fire the same, drop the nudge arms.
- **D3.** Show where `PRED` is read (k).

**Rig:**

| order | run | arms (2 reps each) | fort, window | wall time |
|---|---|---|---|---|
| 1 | **SW1 ARENA-A**: cadence and nudge | ctl (1,500; 40/3,000/r6), cad500, cad6000, nudge_off, nudge_tight (20/1,500/r6) | CTRL arena, 30,000 t | 10 × 4.5 = 45 min + a 10k-t arena smoke (5 min) + restart ≈ **52 min** |
| 2 | **SW2 ARENA-B**: pack floor and sneak | ctl (0.05; 0.25), floor0, floor20, sneak0, sneak100 | CTRL arena, 30,000 t | 45 min + restart ≈ **47 min** |
| 3 | **SW3 GROUPS-LAND** | g1, g3, auto (5) | CTRL natural, 50,400 t | 6 × 6 = 36 + 2 ≈ **38 min** |
| 4 | SW4 LADDER | ×0.5, ×1, ×2 | CTRL F1 design, 60,000 t | 6 × 6.5 + 2 ≈ 41 min |
| 5 | SW5 GROUPS-CAVERN | c1, c2, auto | BOATS, 50,400 t | 6 × 7 + 2 ≈ 44 min |
| 6 | SW6 GROUPS-WATER | w1, w2, auto | BOATS, 50,400 t | 6 × 7 + 2 ≈ 44 min |
| 7 | SW7 BUILDER (only if D1 changes the CTRL roster) | pack bonus 1 / 3 / 5 rosters applied | CTRL natural, 50,400 t | ≈ 38 min |
| 8 | **SW8 CONFIRM** | all chosen values vs all current values | CTRL and BOATS, 100,800 t | CTRL 4 × 9.2 + BOATS 4 × 11.2 + 2 restarts ≈ 86 min |

**Why this order:**
- **SW1 and SW2 come first.** Cadence, nudge, floor and sneak are the runtime levers with **no prior rig data**. They act
  directly on A and K, the busiest components. They need no roster change, and they cost the least per arm (30k t).
- **SW3 is next.** It is the cheapest natural-arrival run, and its auto arm sets the natural-arrival baseline for B and its
  noise.
- **SW4, SW5 and SW6 follow.** Each has a strong prior (F1, ECO2-FC, ECO2-G), so it is more confirmation than discovery.
- **SW8 checks that the chosen values do not interact.**

**Total rig time:** about **5.9 h** without SW7 (354 min), about **6.5 h** with it (392 min). At the rig's slow end (150 t/s)
it could reach about 8.5 h.

**Stop rules:**
- If SW1's smoke run fails the subject receipt, fix the arena before any arena arm runs.
- If SW1 and SW2 show no lever differing on B, run SW8 only on the levers that did differ, or skip it.

---

## 4. What changes in the tool, by outcome

| value | outcome → change |
|---|---|
| ecology cadence | **500 beats 1,500 on A or K in 2 of 2, speed guard holds** → default 750-1,000. **6,000 ≈ 1,500** → default 3,000 (half the passes and fuse time; rows are re-written often enough). **6,000 < 1,500** → keep 1,500 (DF sheds rows; E16/E17) |
| nudge | **off ≈ current** → default nudge off (no visible teleports; RELS shows DF brings the fight anyway). **tight > current, fort harm unchanged** → defaults 20 / 1,500. **current > off** → keep |
| pack-mass floor | **floor 0 adds only hunter losses** (as CAL: below 5% only hunters died) → keep 0.05. **0.20 ≈ 0.05 in kills with fewer losses** → raise to 0.10-0.20 and the builder's `mass_floor` with it. **0 adds kills** → lower to 0.02 |
| sneak bonus | **0 ≈ 0.25 ≈ 1.0** (STL predicts this) → default `pack_sneak 0` and retire the per-unit SNEAK write: fewer unit writes, and one less thing to explain. **A level raises kills 2 of 2** → keep it at that level |
| groups at once, land | **1 < 3 ≈ 5** → keep auto (free on 4x4; binds on 5x5-6x6 per ECO2-G). **5 fails speed or fort harm** → cap auto at 4. **1 ≈ 5** → the limit is not the lever on CTRL; keep auto and leave the big-map case to ECO2-G |
| ladder | **Predator share follows the multiplier** (F1) → set the multiplier that puts B in the user's band, and write it into LADDER22. **Apex share flat across APX f** → APX f is moot (LP is its own DF pool): drop the APX step and steer apex presence by placement and stock (design.md §8) |
| groups at once, cavern | **The caverns ignore the limit** (expected) → document the cavern limit as DF's own and hide it from the Layers tab, or relabel it a soft target. **1 < auto** → keep auto per cavern |
| groups at once, water | **1 < 2 ≈ auto** → keep auto per body. **2 ≈ auto** → default 2 (less placement) |
| x3 pack bonus / size preference | **No CTRL or BOATS roster change at the desk** → remove the contrived weight (simpler builder; design.md R11 already demotes it). **Change** → SW7 decides by B |
| tool `PRED` | Make it a cfg key or delete it from the runtime path. It is used only to order lists |

Each change is checked in SW8 before it ships, and SW8's B, per season, is the number reported to the user as "how busy the
map is now".

---

## 5. What ran and what it found (1 Oct 2026 review)

Sources: `data/eco-desk/findings.md` (SW1–SW7, SW1R, SW2R, SW3B entries), `scripts/sweep-tally.py`, run dirs
`data/experiments/ECO/SW-20261001-003336` (SW1, SW2, SW3), `SW4-20261001-030441`, `SW-rig2-20261001-033105` (SW5, SW6, SW7),
`SWR-20261001-063950` (SW1R, SW2R, SW3B). Figures: ECO page section 12.

| run | ran | verdict | per section 4 | open |
|---|---|---|---|---|
| SW1 + SW1R cadence, nudge | 2 + 2 reps, fixed then reversed order | No level of cadence (500 / 1,500 / 6,000) or nudge (off / current / tight) changed placed-prey kills (0–1 a run; pooled over 4 reps 1, 2, 0, 3, 1). SW1's B flags were cell position, not the lever (placed wolves' share of attacks 76–94% in a load's first cell, 2–30% in its last) | 6,000 ≈ 1,500 → cadence 3,000; off ≈ current → nudge off | Proposed, not applied (decisions dflt-ecology-cadence-3000, dflt-nudge-off) |
| SW2 + SW2R floor, sneak | 2 + 2 reps | Placed prey killed over 4 reps: ctl 3, floor0 1, floor20 3, sneak0 4, sneak100 0. The 0.20 floor's shift off the elephant (SW2 rep 1) did not repeat | sneak 0 ≈ 0.25 ≈ 1.0 → pack_sneak 0, retire the SNEAK write; floor stays 0.05 (no evidence either way) | Decision dflt-pack-sneak-0 |
| SW3 land groups | 2 reps, counterbalanced | **Uninformative**: the status line counted every tracked group (mostly cavern) | – | Rerun as SW3B |
| SW3B land groups | 2 reps, counterbalanced | Land groups 1.4 / 2.4 at cap 1, 3.6 / 2.6 at cap 3, 4.7 / 3.6 at auto; caps not hard (max 4 at cap 1); 0 attacks in every cell | 1 < 3 ≤ auto → keep auto | – |
| SW4 ladder multiplier | 2 reps, counterbalanced, 60,000 t | Predators 1.8% / 1.9% of land units at ×0.5, 14.0% / 10.6% at ×1; ×2 gave 20.1% (last cell) and 6.9% (first cell). Apex present in 1 run of 6 | Share follows ×0.5 but not reliably ×2; apex share flat → drop the APX step | Decision ladder-drop-apx-step; lp-separate-pool |
| SW5 cavern groups | 2 reps, counterbalanced, BOATS | Cavern groups 24.0 / 27.3 at auto vs 13.8–16.0 at caps 1–2; DF's natives (4–5 per depth) stay. Attacks per 10,000 t do not simply follow groups (c1 rep 1 379 > auto) | Caverns partly ignore the limit → keep auto, relabel a soft target | Decision cavern-limit-soft-target |
| SW6 water groups | 2 reps, counterbalanced, BOATS | Water groups 4.8 / 2.1 auto, 1.0 / 2.1 w1, 3.1 / 2.3 w2; BOATS's supply is 2–5 groups, so the cap rarely binds | 2 ≈ auto → optional default 2 (thin) | Decision water-groups-default-2 |
| SW7 pack bonus | 2 reps, counterbalanced | Land groups 3.1 / 1.6, 2.2 / 2.2, 3.3 / 2.8 at ×1 / ×3 / ×5; 0 attacks; only 7–8 of 27–29 wanted species exist in CTRL's pool (weak test) | No measurable effect → remove the ×3 | Decision builder-drop-x3-pack-bonus |
| SW8 confirm | **not run** | – | – | Blocked on the decisions (sw8-confirm) |

**Departures from the design, and what they mean for the verdicts.**
- **The B index was not used for verdicts.** Cell position confounded B in SW1/SW2 (memory experiment-readout-traps 20); the verdicts
  rest on placed-only readouts (attacks on the placed herds, placed prey killed, wolves lost) and on the group and share counts.
  The guards (fort harm, speed, persistence, visibility) were not tallied per arm. **Untested:** whether any lever changes speed or
  fort harm.
- **Counterbalancing came late.** SW1 and SW2 ran in a fixed order; SW1R/SW2R reversed it. SW3–SW7 were flagged `counterbalance`
  (eco-run.py: even reps reversed). Reversal balances position over two reps but does not remove the pile-up of natives.
- **The arena cannot isolate the tool's write.** The placed wolves are non-wild to DF, which aims them at targets itself (RELS
  row 3), so a lever that only changes the tool's written pairs (floor, sneak) can be masked. The no-effect verdicts for SW1/SW2 hold
  for "a placed 5-wolf pack against herds 45–60 tiles away", not for natural arrivals. **Untested:** the same levers on DF-drawn
  predators.
- **Power.** Kills were 0–4 per arm over 4 reps, so only a large effect could show. "No effect" means "none large enough to see".
- **The detachOldest stall (section 0, from T8g) is fixed in v7.0** as `gate_drain` (V7.drainGate, seasonal-wildlife.lua ~3593,
  default on): after a release it keeps releasing the next-oldest gated group until at most one flagged animal remains. SW3B ran on
  v7.0, so the fix was in place unless a cell switched it off; no SW3B receipt prints gate_drain, and the validator has no
  gate_drain claim (open item validator-v70-coverage). **Unchecked per cell.**
- **D2 and D3 (desk receipts) were not written up.** The arena's mass bands were not confirmed with the tool's own masses before
  SW2 (SW2's own note: five wolves sit at ~5% of an elephant). D3 (`PRED` is read only to order lists) stands as written in note 2.

## 6. Next sweep designs (1 Oct 2026 review)

Same rules as section 2: two replicates per arm, the current value as control, counterbalanced order (rep 2 reversed) and a
**fresh fort load per arm** for arena blocks so natives cannot pile into later cells; a subject receipt per replicate (memory
manifest-subject-receipt); placed-only scoring wherever anything is placed. Run on DFHack 53.16-r2 only after the r2 re-validation.

**SW8 CONFIRM (revised).** After the user rules on the defaults (cadence 3,000; nudge off; pack_sneak 0; ×3 bonus removed; APX
step dropped; cavern limit soft):
- Arms: all chosen values vs all current values. CTRL and BOATS, natural arrivals (no arena), 100,800 t, 2 reps each, arm order
  reversed in rep 2, DF restarted before each run.
- Receipt per replicate: a `v7` print of every switched value from inside the scheduled job (memory dfhack-script-copies), the
  ecology job's last-run counters (pairs written, nudges, cadence) every 3,000 t, and land/cavern/water group counts in the status line.
- Readout: the four B components per layer and season window and B itself, now that no shared-load cells are involved; the four
  guards (fort harm, stopwatch speed ≥ 90% of control, persistence, nudges per season); predator share of surface units.
- This is the first test of cadence, nudge and sneak on DF-drawn predators. Wall time ≈ 86 min (section 3).

**SW9 TOOL-ONLY WRITE (optional, only if a floor or sneak decision needs evidence).** Isolate the tool's written pair from DF's
own aiming: the predators are DF arrivals, not placed units.
- CTRL, FREQUENCY steered so a wolf pack arrives (F1 design), herds placed as prey; arms: pack_floor 0.05 vs 0.20, the prey herd
  of mass chosen so the pair falls between the floors.
- Receipt: the arriving pack is wild (roaming flag true) and tracked as one group; the tool's ecology line shows the pair written
  (0.05) or refused (0.20).
- Readout: DF's own rel rows toward the herd (RELS method) and attacks on the herd per arm.

**SW10 ladder22 (after the port; open item builder-port-vs-v22).** The SW4 design re-run on the ported v2.2 ladder: ×1 v2.1 vs ×1
v2.2 on CTRL and BOATS, 60,000 t, 2 reps each, predator share of units and of waves against the 14–18% target. ECO-design.md S8L
is the full-season version.
