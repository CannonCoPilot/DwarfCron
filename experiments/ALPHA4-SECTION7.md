# Alpha Four section 7: a check for every row of "What this page cannot check"

W2:Urist, 1 October 2026. Desk work: nothing here has run on DF. The rig was busy with the lead's validate-full run.

**Under test:**
- seasonal-wildlife v7.1 at `bff2726` (`sw-wt/deploy`), on DFHack 53.16-r2;
- fort **RinghatchetsReady** in world **region9** (memory test-world-region9): 8x8, several biomes, a lake and a river, caverns dug and revealed, a trade depot.

**Source of the list:** `.claude/scratch/gen_alpha4.py`, the `CANNOT` table (phase 7). It has 15 rows.

**Harness:** v7.1 defaults (HARNESS-v71.md):
- n = 5 reps per arm;
- a fresh load per arm (restore `.preverify`, restart DF, load);
- counterbalanced order;
- every animal wiped before a cell places anything;
- manipulation checks that abort the block;
- placed units keep DF's roaming flag.

## 1. What was built

| file | what |
|---|---|
| `chronicler/dfhack/scripts/cx-sec7.lua` (new) | In-game probe verbs that read what the walkthrough cannot see: facts, spots by water body and cavern, skills and the rust floor, the tool group of a placed set (leader, panic, spread), natural-arrival samples per layer/cavern/body, the trim, irruption subjects with every write read back, residual writes, scavenging, water and breathing, occupancy, perf/stopwatch, ledger counts, config writes, AP1 builds. Every verb prints `eco <kind> k=v` and runs under `pcall`, so an error prints `eco error` instead of timing the RPC out. |
| `scripts/alpha4_sec7_blocks.py` (new) | 38 eco-run blocks named `S7_*`: 26 CORE, 9 FULL, 3 OCEAN. They read `data/alpha4-sec7/facts.json`. |
| `scripts/eco-run.py` (+3 lines at the end) | Registers the `S7_*` blocks. No existing block changes. |
| `scripts/alpha4-sec7.py` (new) | The runner, with `--only STAGE\|ITEM\|BLOCK`, `--skip`, `--tier`, `--reps`, `--dry-run`, `--plan` and `--list`. |

**Offline checks:**
- `luac53 -p` on cx-sec7.lua.
- `py_compile` on all three Python files.
- `alpha4-sec7.py --dry-run --tier all` (with `SEC7_OCEAN_FORT` set, so the OCEAN blocks register): 44 stages walked, eco-run's own dry run for each block, and validate-full `--dry-run` clean. All 2,066 Lua chunks the blocks and the runner send passed `luac53 -p`, with 0 failures.
- `pytest tests/harness`: 24 passed.

**The dry run cannot catch** a field that is nil at run time or a wrong expected value. The first rig run settles those.

## 2. How to run

```sh
scripts/cx-lifecycle.sh status                         # the rig must be free; DF is never shared with another run
scripts/alpha4-sec7.py --only DEPLOY,FACTS             # 8 min: deploys cx-sec7.lua + the v7.1 tool, reads the fort, measures load s and t/s
scripts/alpha4-sec7.py --plan                          # the estimate again, now with the measured load time and t/s
scripts/alpha4-sec7.py                                 # everything in CORE, in the order below (about 25 h)
scripts/alpha4-sec7.py --only 6                        # one row (here: irruption tokens)
scripts/alpha4-sec7.py --tier full --skip VALIDATE     # the stream notes' other rig tests too
SEC7_OCEAN_FORT=<region9 shore 1x1> scripts/alpha4-sec7.py --tier ocean   # after b1-forts.py embark --only shore
```

**Where the output goes:** `data/alpha4-sec7/<run>/` gets `log.txt`, one TSV per stage (rows `stage rep arm kind k=v`, with VERDICT rows) and `eco/<block>.tsv` (eco-run's own format: manipulation receipts first). The eco tallies (`eco-v71-tally.py`) read the eco TSVs.

**FACTS runs first.** The blocks take the cavern with a civ race, the ticks to the next season and the fort's conditions from it. A block whose condition is false on this fort (for example `has_ap`, an animal-people cavern entry) is skipped, and logged as NOT-TESTABLE-HERE with the reason.

## 3. Total rig time

The estimate uses 180 s per fresh load and 200 t/s. Neither has been measured on an 8x8 fort with open caverns. FACTS measures both, and `--plan` then re-estimates.

| tier | blocks + stages | time |
|---|---|---|
| **CORE**: every row answered at its shortest | 6 stages + 26 blocks | **about 25 h** (plus 41 min if the fort has animal people in a cavern, S7_IRRR35; plus 87 min if it has an extinct land apex, S7_EXF1) |
| FULL: adds the notes' other tests | +9 blocks | about 41 h in all |
| OCEAN: needs a region9 shore 1x1 | +3 blocks | about 3 h, plus the embark |

**What the time goes on (CORE blocks):**
- about 13 h of loads: 52 cells x 5 reps = 260 fresh loads at 3 min each, plus about 15 for the stages;
- about 8 h of RPC calls: 11,400 verbs at eco-run's planning figure of 2.5 s each (the sampling steps);
- about 2.4 h of ticks: 1.73 M ticks at 200 t/s.

**The levers left, if that is too long:**
- **Sample less often.** Halving the samples in S7_IRRM, S7_IRRP2, S7_FSH3 and S7_NAT saves about 2 h. Each cx-sec7 read is one RPC, and most take well under the 2.5 s the plan assumes, so the measured figure may be lower anyway.
- **`eco-run --load rep`** would cut the loads to about 3 h. It is not used, because the tool's config and records persist in site data, so cells sharing a load would not be independent (H1).

## 4. Item → check → command → time

The time is CORE at n = 5, using the estimate in section 3.

| # | row | check (what it reads) | command | time |
|---|---|---|---|---|
| 1 | Skill writes act on new arrivals and do not rust | **S7_SKL**:<br>• pre units (placed before the write) and post units (placed after it, read before any ecology pass);<br>• per unit: rating, nominal, floor (`natural_skill_lvl`), rust counters;<br>• caste NATURAL_SKILL and `V7.H.readback`;<br>• rust shortcut, with a no-floor positive control.<br>Arms: pkg, nopkg, pkg_nofloor. | `--only 1` | 81 min |
| 2 | Packs, stoops and fishing change kills | **S7_PK2**: pack on/off; `packs` (inferred, largest), relcount to buffalo, attacks.<br>**S7_STP1**: stoop on/off; eagles and rabbits, ledger eco, eagle x deer relcount = 0.<br>**S7_FSH3**: fishers on/off at the river; bear-pike adjacency every 300 t, attacks.<br>**S7_FSH4**: polar bears at the lake; swim, breathing, adjacency. | `--only 2` | 188 min |
| 3 | The clock holds groups near the cap | **S7_NAT** def vs v70, natives as subject:<br>• land groups vs `QUOTA.groupsFor` every 3,000 t, 36,000+ t;<br>• groups3 (H5) every 6,000 t.<br>Target: def mean in [cap-1.5, cap].<br>WAT5: water groups per body, mean ≥ 3. | `--only 3` | 91 min (shared) |
| 4 | The cavern gate holds five; natives trimmed walk off | S7_NAT:<br>• groups per cavern (tool record and natives by entry);<br>• manipulation check at every sample: held species read FREQUENCY 1.<br>Target: mean ≤ 5.5, max ≤ 6.<br>**S7_TRIM**: cap 1, the trimmed ids on the map vs gone every 300 t. | `--only 4` | 91 (shared) + 26 min |
| 5 | A lost leader makes the group scatter | **S7_PAN1**: panic on/off; 1 male + 5 female deer adopted; leader is the male (check); harness kills him; spread at +100/+300/+1,200/+2,400; ledger panic.<br>**S7_COHT** (lake substitute): pike school led vs cohesion off; spread, dry swimmers. | `--only 5` | 102 min |
| 6 | Tokens act | **S7_IRRM**: M1-M8; one token at 100% vs all off; the cavern from FACTS.<br>**S7_IRRP2**: A rotation / B no tokens / C R10 package; pinned pressure, 5-day event, civ units every 600 t.<br>**S7_IRRTSEQ**: T-END, T-OFF and T-SAVE routes in sequence, residual scan after each.<br>**S7_IRRR35**: animal-people wave size. | `--only 6` | 322 min (+41) |
| 7 | Scavenging takes days, swimmers eat from the water | **S7_SCV3**: natural vs sweep; 6 kangaroo carcasses, jackal/vulture/hyena 12 tiles off; SCAV stats and remains kg every 600 t over 7,200 t.<br>**S7_SCV3W**: pond grabbers in the lake, swimmers on/off; dry-tile receipt. | `--only 7` | 125 min |
| 8 | Vermin eaters eat what they walk to | **S7_VF1**: forage on/off; badger x4, grasshopper x20 at 15 tiles (pets wiped too); vermin count every 500 t, `vermin eats`.<br>**S7_VF4**: duck at the river bank against the river's own fish vermin. | `--only 8` | 95 min |
| 9 | Apex presence target; ladder 20% carnivores | S7_NAT:<br>• apex presence (the scheduler's own seen/total, and live apex groups);<br>• H/C/A unit shares on land.<br>FACTS: AP1 desk (10 builds each at ap_pick 0.1 and 1) and R28P (magma crab refused on the surface and in a cavern).<br>**S7_INV3**: smilodon added on a calm map. | `--only 9` | 91 (shared) + 24 min + FACTS |
| 10 | Pull, mix and guard shape the water | FACTS SURV: `water depth`, `water depth full` and `cx-eco depth`, scan ms and stopped.<br>S7_NAT: MIX1 species shares per body (def mix on, v70 off).<br>**S7_GRD1**: 3 pike adopted, teleported ashore, guard on/off; alive/wet every 200 t.<br>PELA: OCEAN. | `--only 10` | 48 min + shared |
| 11 | Extinct corrections change arrivals | FACTS: the world's `real_world_extinct` setting and the in-embark extinct rows (the R24.4 precondition).<br>**S7_EXR1**: fix on/off; eoraptor x5 by hares; BENIGN readback, attacks.<br>**S7_EXU1**: placed before vs after enable.<br>**S7_EXF1**: only with an extinct apex in the embark. | `--only 11` | 89 min (+87) |
| 12 | Water auto-on and spill reach 3-5 groups | **S7_F1**: layer off and unset vs `water layer off`; the layer after enable, water groups within a day.<br>F2: S7_NAT's water groups per body with spill on (def) vs off (v70), and the season ledger (the cell runs past the next season change when that is within 60,000 t). | `--only 12` | 44 min + shared |
| 13 | Cost of every v7.1 change | **S7_PERF1**: PERF0 bench, then 12,000 t; new paths vs all ten `legacy_*` + stagger off; FUSE per job, worst tick, stopwatch t/s.<br>**S7_PERF2**: overlay new / legacy / off.<br>**S7_PERF4**: +60 citizens, events on/off.<br>PERF3: OCEAN. | `--only 13` | 168 min |
| 14 | Panel and page round trips on a real screen | **VALIDATE**: every gui.* and web.* claim on this fort.<br>**PANEL**: all 13 sections; per section one step (Right), the config path that changed, the read-back line, `d` back to default, clipped rows at the frame edge; Panel refresh time with an irruption running; stderr.log.<br>**WEBLOAD**: page polled as it polls (state 2 s, status 5 s) vs no page; t/s, snap/status ms, fps; n = 5. | `--only 14` | 52 min + VALIDATE |
| 15 | Anything at all on DFHack 53.16-r2 | **R2**: REPORT section 4 on this fort (version; a setting through save and reload; occupancy after placement and a nudge; breathing over units.all after a water draw; smooth-movement/stockflow off; sustain, makeown, tp, gather).<br>**VALIDATE**: validate-full on the fort, every phase. | `--only 15` | 42 min |

## 5. Per row: what must be observed, why the page cannot, and what the check does

**1. Skills (SKL1, SKL2).**
- **What must be observed:**
  - after the write, a unit that arrives later carries the profile's SNEAK from its caste;
  - a unit already on the map carries it on its soul;
  - neither rusts below the floor.
- **Why the page cannot see it:** skills live in caste raws and unit souls, and rust takes about 30,000 ticks of disuse. The window shows neither.
- **The check:**
  - Pre units are placed before `enable` and the forced ecology pass. Post units are placed after, and read at once, before any pass, so a post unit at level got it from the caste alone.
  - `cx-sec7 skills` prints rating, nominal, floor and the rust counters per unit, plus the caste levels and the tool's readback rows.
- **Shortcut:** instead of 30,000 ticks of disuse, `rustpush` adds 200,000 to the skill's unused/rust/demotion counters and reads at +1,200 and +6,000.
  - This assumes DF rusts on those counters at its next skill pass.
  - The `pkg_nofloor` arm (floor zeroed first) is the positive control. If SNEAK does not drop there either, the shortcut did not engage DF's rust, and the floor result is vacuous.
  - FULL `S7_SKL30K` runs the real 30,000 ticks.
- **Also a shortcut:** a "new arrival" is a `units.create` placement (cx-eco spawn), not a DF-drawn wave. Whether DF's own wave creation reads NATURAL_SKILL the same way is the open half.

**2. Kills (PK2, STP1, FSH3, FSH4).**
- **What must be observed:** attack and kill counts against the lever.
- **Why the page cannot see it:** the window has no attack log.
- **The checks:** each lever's arm pair; cx-eco `watch`/`read` for attacks with origins; a manipulation check on each arm:
  - PK2: recognition `largest>=5` and the floor relation written;
  - STP1: stoop dial and cadence read back;
  - FSH3: fishers read back;
  - FSH4: `fish_breathe off` and polar on.
- **Shortcuts:**
  - STP1 runs 6,000 t with the ecology cadence at 1,000 (6 stoop opportunities against 5 in the notes' 15,000 t at 3,000). This changes the pass spacing, not the stoop rule.
  - FSH3 sets the run to all seasons, so the fishing run does not depend on the save's date.
  - FSH4 uses the lake's pike in place of seals. A fresh lake has no seals; the ocean version is OCEAN.

**3, 4, 9, 10, 12. Natural arrivals (G2r, WAT5, CAVG, APX1, LAD1, MIX1, F2).**
- **What must be observed:** counts and shares over tens of thousands of ticks.
- **Why the page cannot see them:** the page shows one moment.
- **The check: one block, S7_NAT.** It runs `preset`, a roster build for each layer and `enable`, then samples every 3,000 t:
  - groups per layer against the cap;
  - groups per cavern, from the tool's record and from the natives by entry;
  - water groups per body;
  - the hold check;
  - apex presence;
  - H/C/A unit shares;
  - extinct arrivals;
  - water species per body.
- **The two arms:** `def` judges the absolute targets. `v70` turns every lever back at once:
  - the adaptive clock and the cavern gate;
  - land aquatic, retry 5, mix, pull and spill;
  - apex scheduler, ladder units and extinct fix.
- **Shortcuts:**
  - **One contrast for all the levers.** An interaction (for example, apex groups counting against the land clock) is not separated. FULL `S7_NATLEV` has one arm per lever (5.9 h).
  - **APX1 sees one month** (36,000 t), not a season, so a presence share has wider error and the season-start placement is not seen.
  - **F2 does not run two seasons.** It reads the borrowed seasons given back at the next season change: the cell runs to `to_season + 3,000` when that is under 60,000 t. FACTS reads the save's tick, which is the same on every fresh load. When the change is further away, F2's give-back is not seen in CORE.
- **S7_TRIM** forces the trim (cap 1) and tracks the trimmed ids for 3,600 t: did DF walk them off? This is the groups.md open risk "trim countdown 10".

**5. Leader loss (PAN1, COHT).**
- **What must be observed:** spread over time after the leader dies.
- **The check:**
  - The leader is checked to be the adult male (R32).
  - The kill is exterminate's blood drain, so a corpse remains and the record reads "died".
  - `cx-sec7 grp` gives maximum and mean distance from the centroid, the mean pairwise distance, who follows, and `panic`/`lost`.
- **COHT substitute:** the fort has no ocean, so COHT uses a lake pike school (led vs cohesion off) in place of `place ORCA 6`. The orca version is OCEAN `S7_COHTO`.

**6. Tokens (M1-M9, the main experiment, T-PR, T-END, T-OFF, T-SAVE, T-R35).**
- **What must be observed:** unit internals:
  - curse masks (`uwss_add_caste_flag`);
  - the per-unit caste cache (`enemy.caste_flags`);
  - path goals, hidden flags, the soldier mood;
  - distances to citizens and to the access.
- **The check:** `cx-sec7 irr` reads every subject's written fields back, against the event record (`IRRUPT.state(g).layers.cD.ev.units`). `native` reads a non-subject of the same race (M3). `resid` scans every unit for leftover writes.
- **The M arms (agitation off; pauses and zoom off so the rig keeps stepping):**

| arm | probes | what it does |
|---|---|---|
| crazed | M1, M2 | reassert off, a read every 100 t, then save and reload |
| thief (+meander) | M3, M4 | natives read before, at +100 and at +3,000 |
| goalonly | M6 | a harness steal-goal write, no token |
| mischief | M5 | the token alone |
| sneak | M7 | the token alone |
| wander | M8 | the token alone |
| none | — | the control |

- **What the M arms leave out:**
  - **M9 is not built**, as the notes say. It runs only if M2 or M7 fail.
  - **M5 has no lever or door built** next to the cavern; it reads the goal and mood only.
  - **M4's fort item count is not read**; it reads items carried and goal.
- **P2 shortcut:** the "3 citizens working in the band" are left out; the pressure is pinned instead. Approach is measured to the access point and to the nearest citizen anywhere. Sampling is every 600 t, not 300.
- **T routes shortcut:** CORE runs all eight routes in one load, in sequence, with a residual scan after each. A route's residue is attributed because the scan before it read 0. The cost: later routes start on a fort that already held an event. FULL `S7_IRRT` gives each route its own load (2.8 h).
- **T-END:** "repelled" uses a harness kill, not a squad.
- **T-PR** (FULL): threshold 0.3, which gives the order of the sources, not their real days.
- **T-R35** runs only if FACTS finds an animal-people species in a cavern.

**7. Scavenging (scav.md section 15).**
- **What must be observed:** kg eaten per species over days, and swimmers feeding from water.
- **The check:** SCAV's own per-species counters and the remains registry, every 600 t over the full 7,200 t (6 days). This is not shortened: "takes days" is the claim.
- **The water arm:** pond grabbers, the only vanilla aquatic scavenger (SCV2Wb's note), feed on carp corpses in the lake. The control is swimmers off. The dry-tile and breathing counts are the "never beach" receipt.

**8. Vermin (vermin.md).**
- **What must be observed:** vermin are not units; their amounts near the placed eaters show the eating.
- **The check:** the VRM harness Lua (`vermin_create`, `vermin_count`) and the tool's `vermin eats`. The fort's pets are wiped too (trap: cats ate placed vermin).
- **Not in CORE:**
  - VF2 (one arm per class), VF3, VF5-VF8 are left out; at 2 arms x 5 reps each, the class suite alone is about 8 h.
  - The duck stands in for a heron, which may not exist in vanilla.

**11. Extinct.**
- **The precondition comes first.** FACTS reads `world.worldgen.worldgen_parms.real_world_extinct` (df-structures r2) and the in-embark rows.
- **EXR1 and EXU1 place their subjects**, so they run whatever the setting.
- **EXF1 (DF-drawn arrivals) runs only with an extinct land apex in the embark.** It has a shortcut: DF's surface gate is released every 1,500 t (SW4's lever), so more waves fall in 30,000 t. This changes the wave timing, not DF's pick.

**13. Cost.**
- Every cell is a fresh DF process (fps-load-facts: session length dominates). t/s comes from a stopwatch inside the game (game ticks over `getTickCount` between two reads), so step overhead is included.
- **Shortcuts:**
  - **PERF1 runs 12,000 t, not 33,600.** The per-1,000-tick costs are rates. 12,000 t holds 4 ecology passes and 40 groups passes.
  - **PERF4 uses `cx-load citizens 60`.**
  - **PERF3 is OCEAN**, because sponges need an ocean, and `layer_groups` is retired in v7.1, so arm B is sponges alone.

**14. A real screen.**
- **Why headless cannot do it:** DFHack screens render only on the real window.
- **VALIDATE runs validate-full on this fort.** Its gui.* and web.* claims run on the real window.
- **PANEL walks the v7.1 Panel's 13 sections**, with the keys taken from the live screen in the lead's run 20261001-224525 (`s`: section, `d`: default). Per section:
  - one Right step;
  - the flattened config is compared before and after, and must show a path that changed;
  - the read-back line;
  - `d` must put it back;
  - a glyph in the frame's last column counts as a clipped row (screen-check trap 2).
- **WEBLOAD** polls the server from the host exactly as the page does.

**15. r2.**
- **R2** is REPORT section 4's checklist, step by step, on this fort.
- **VALIDATE** is the full run.

## 6. Still uncheckable, and why

- **The narrow-screen check** (ui.md: the tab bar scrolls at about 90 columns). The rig has no lever that resizes DF's window. CrossOver's window would need an AppleScript resize with accessibility rights, which nobody has tried. This is a manual step.
- **A DF-drawn wave inheriting caste skills** (SKL1's strict form). DF's wave timing cannot be forced to land inside the cell. Placement through `units.create` stands in.
- **M5 with a lever and a door, and M4's fort item count.** Nothing builds a reachable lever or door, or counts the fort's items, headlessly. Goal and mood are read instead.
- **T-END "repelled by a squad".** A squad cannot be ordered headlessly. A harness kill stands in.
- **F2 over two whole seasons, and APX1 over a season.** These are cut to the next season change and one month. The full length is about 56 h per arm pair at n = 5.
- **OCEAN rows (PELA, PEL1, COHT with orcas, PERF3, the ocean half of FSH4).** RinghatchetsReady has no ocean. They need a region9 shore 1x1 (`b1-forts.py embark --only shore`, then `SEC7_OCEAN_FORT=`) or the user's say on whether region9 has an ocean at all.
- **EXM1** (the Steam attack mods). It needs a new world with the mod, which conflicts with region9 (R11). It is off the programme, as extinct.md says.

## 7. Found while building

- **`cx-lifecycle step N` stops at 120 s whatever N is.** eco-run passes no seconds, so a long step silently ends early: 36,000 t at 200 t/s would stop at 24,000. Every S7 block steps in chunks of 3,000 t or less. Existing blocks with 5,040-t steps are fine at CTRL's 450 t/s. On an 8x8 fort below 42 t/s they would truncate.
- **The `lua` RPC has a fixed 15 s deadline.** `cmd_lua` ignores `CX_RPC_TIMEOUT`, so slow probes go through `cmd cx-sec7`.
- **The lead's validate-full run 20261001-224525 wrote `rig.json` as `{"df": "?", "dfhack": "?", "release": "?"}`.** The version read returned nothing, so that run's record does not show it ran on r2. R2 step 1 reads the versions on its own.
