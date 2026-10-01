# Harness v7.1: what changed, how to use it, defaults

W2:Urist, 1 October 2026. Branch `v71-harness`, a worktree of DwarfCron `Dev`. Built at the desk with no rig. DF was the user's running game, so nothing here has run on DF yet. Every piece was checked offline:
- `luac53` (DFHack's Lua 5.3.6) on every changed `.lua`, plus `luacheck` with no new warnings;
- `python -m py_compile` on every changed script;
- a `--dry-run` of all 91 eco-run blocks (32,384 canned rig calls, none failed);
- 20 pytest cases in `tests/harness/`.

Sources:
- the user's rulings: `data/eco-review/part2/USER-REVIEW-PART2.md` (R11, R12, R15, R23);
- Part 1 plan section 2, fixes H1–H7: `data/eco-review/part1/PLAN-PART1.md`;
- B section 10 and 16.3–16.5: `data/eco-review/part1/B-dials-groups-forts.md`;
- R1 "the rig placed": `data/eco-review/part2/ANSWERS.md`;
- open items `validator-backlog-stale`, `validator-cli-water-dup`, `validator-v70-coverage`, `cx-probe-invasion-exclusion` and `chronicler-weather-lookup`.

## 1. The new defaults in one table

| default | was | ruling | where | override |
|---|---|---|---|---|
| **5 replicates per arm** | 1 (eco-run), the manifest's own (cx-experiment) | R12 | `eco-run.py --reps 5`; `cx-experiment.py` sets every arm to 5 | `--reps N`; cx-experiment `--manifest-reps` or `"reps_locked": true` |
| **short reps** | — | R12 | `eco-run.py --tick-scale F` multiplies every `step:N` and cell length; `eco-run.py plan` prints wall time | `--tick-scale 1.0` |
| **fresh load per arm** | one load per rep, every cell in it | H1 | `eco-run.py --load arm`: restore `.preverify`, restart DF, load, for every cell (`fresh_load`, `eco-run.py:1161`) | `--load rep` |
| **counterbalanced order** | written order every rep | H1 | `--order counterbalance`: odd reps in written order, even reps reversed. `rotate` gives Latin rows (with 5 cells and 5 reps, every cell takes every position once) | `--order fixed` |
| **wipe every animal before a cell places anything** | natives and earlier cells' units stayed | R15 | `cx-eco wipe` + `wipecheck == 0` (`eco-run.py:1183`, `cx-eco.lua:876`); cx-experiment wipes before any arm whose `pre` places animals | `--no-wipe`; block `wipe=False` + `wipe_why`; manifest/arm `"wipe": false` |
| **manipulation check, abort on failure** | none | H2 | receipts checked as they print; explicit `check:` steps; first failure aborts the block | `--manip skip` (drop the cell only) |
| **placed packs adopted as one tool group** | `discoverGroups` (n = 0 in all 40 SW cells) | H3 | `cx-eco adopt TOKEN` → `seasonal-wildlife groups adopt <ids>` (v7.1 tool verb) | — |
| **placed units keep DF's roaming flag** | flag cleared | H4 | `--isolate roam` appends `roam` to every spawn | `--isolate none` |
| **placement like the tool's PLACE.one** | STRANGER row, first entry, no debit | ANSWERS R1 | spawn defaults `slot=none ref=site debit=1` | `--placement legacy` |
| **test world region8** | region4/6 forts | R11 | `CX_TEST_WORLD=region8` (`cx-config.sh`); `survey`/`rivers` default to it; `embark1`; `b1-forts.py` | `CX_TEST_WORLD=...` |

## 2. How to use it

```sh
scripts/eco-run.py list                                # blocks, with any wipe opt-out and its reason
scripts/eco-run.py plan SW1,SW2 --tick-scale 0.5       # wall-time estimate; no rig
scripts/eco-run.py SW2 --dry-run --reps 2              # walk every step with canned receipts; no rig call
scripts/eco-run.py SW2                                 # 5 reps, fresh load per arm, counterbalanced, wiped, checked
scripts/eco-run.py SW2 --load rep --order fixed --no-wipe --isolate none --placement legacy --reps 2   # the pre-v7.1 run
scripts/eco-v71-tally.py data/experiments/ECO/<run>    # receipts first, then attacks by origin, bouts, hidden, groups3
scripts/cx-experiment.py run experiments/E9a.json      # 5 reps per arm, counterbalanced interleave
scripts/b1-forts.py survey --dry-run                   # the R11 programme (section 5)
```

**Step forms in a cell:**
- `spawn ...` and every other cx-eco verb;
- `lua:CODE`, `step:N`, `read:TAG`, `save:`, `load:`;
- **new:** `check:KIND[k=v,...].KEY OP VALUE`, with OP one of `== != >= <= > <`.
  - The check is evaluated against the latest receipt of that kind which matches the filter, for example `check:cfg[path=v7.pack_sneak].value==1.0` or `check:skill.with>0`.
  - A missing receipt fails the check.
  - A malformed check fails before any rig time is spent.

## 3. What each fix does

### H1: a fresh load per arm, with the order reversed

- Under `--load arm`, `eco-run.py` gives each cell of each rep its own `save-restore FORT.preverify`, DF restart and load. Then it finds the spot and runs.
- Natives, the tool's group records (`g.groups` in site data) and placed vermin no longer carry from cell to cell. The SW1R cell-position confound is gone by construction.
- **Order:** `arm_order` in `scripts/ecolib.py`.
- **cx-experiment** already restored and loaded per replicate. Its new default order is interleaved: rep r runs every arm, reversed on even r (`arm_order`, `cx-experiment.py:259`).

### H2: the manipulation check (printed first; aborts the block)

At block start the log prints each cell's checks, both explicit and automatic. The automatic checks run on every receipt as it prints (`ecolib.AUTO`). A count of zero means the manipulation reached nothing:

| receipt | must show | why |
|---|---|---|
| `spawn` | `placed > 0` | manifest-subject-receipt: three runs went vacuous without it |
| `rel`, `relfort` | `pairs > 0` | a relation written to no pair |
| `lead` with how=`lowest` | `leader >= 0` | `largest-male` rightly names no leader when there is no male (R32), so it is not checked |
| `adopt` | `adopted == 1` | the pack is ONE tracked group (H3) |
| `sneak`, `skills` | `units > 0` | the skill write reached a unit |
| `sw7apply` | `applied > 0` | the roster push landed |
| `swreceipt` | `present > 0` | subject present on the layer |
| `wipecheck` | `remaining == 0` | R15 |

**Explicit read-backs** come from the tool's own state, not from an echo:
- `cx-eco cfg PATH...`: the persisted config value;
- `cx-eco skill TOKEN SKILL`: on-map units holding the skill, and the highest rating;
- `cx-eco relcount A B`: PREDATOR_OR_PREY cells still standing between live spawned A and B;
- `cx-eco ecostate`: groups by layer, ecology pairs and nudges.

**Explicit checks added to the existing blocks:**
- **SW1:** cadence 500 or 6000, `nudge == false`, `far_tiles == 20`.
- **SW2:**
  - `pack_floor` and `pack_sneak` as written;
  - after the first ecology pass, SNEAK must be written (`sneak100`) or absent (`sneak0`).
  - No SW2 arm ever wrote SNEAK before this (PLAN 0.2).
- **SW3, SW5, SW6:** the limits and `layer_groups`.
- **SW4:** the disarm, and the ladder reaching at least one AL species.
- **B1 baselines:** the tool enabled and `layer_groups` on.

**On a failed check:**
- The cell's receipts and a `MANIPFAIL` row go to the TSV.
- The block stops. Under `--manip skip`, only that cell is dropped.
- In every cell, the receipts (kinds in `ecolib.RECEIPTS`) are written before the outcome rows.

### H3: the placed pack adopted as one tracked group

- `sw_arena` (SW1/SW2) now ends with `adopt WOLF` and `ecostate`, in place of `sw.discoverGroups`.
- `cx-eco adopt TOKEN` (`cx-eco.lua:1001`) passes every live spawned TOKEN id to `seasonal-wildlife groups adopt <ids>`.
- The receipt is read from `sw.loadGroups()` and gives:
  - `groups`: how many tool groups hold those ids;
  - `members`;
  - `adopted=1` only when the ids form exactly one group;
  - `roam`: how many still carry DF's flag;
  - the first line of the tool's reply.
- On the v7.0 tool, which has no adopt verb, the receipt reads `adopted=0` and the block aborts. That is the correct outcome: without adoption, the SW arena results are vacuous.

**The roaming-flag behaviour:**
- **Before v7.1:** `cx-eco spawn` cleared both roaming bits. The tool's `discoverGroups` only adopts flagged units (`gatedLayer`), so a placed pack was never a group. DF also treats unflagged units as fort-side and aims them at newcomers (A §2; RELS `other>wild` 57).
- **v7.1 default (`--isolate roam`):** the flag is kept. DF treats the units as wild, so it does not aim them. They also count toward DF's surface gate, so no DF surface wave arrives while two or more of them stand on the map. That is a further isolation, and an expected one.
- **With the tool on**, two more things happen:
  - its `discoverGroups` would adopt flagged units by itself;
  - its gate drain (`v7.gate_drain`) may release the group, clearing the flags and marking it resident. From then on DF aims those units again.
- **Reading it:** `cx-eco watch` records each attack with both sides' origin at the moment of the attack (placed, drawn, released, or fort-side), so a tally can tell the two phases apart. `eco-v71-tally.py` prints attacks per origin class.

### H4: score on DF-drawn subjects, or isolate DF's aiming

- **Isolation:** `--isolate roam` (above).
- **Attribution:** every attack is logged with its tick, attacker and defender ids and tokens, and both origins:
  - `atk` rows;
  - `attacks_o` pair counts, for example `WOLF(placed)>DEER(placed)` or `WOLF(placed)>BADGER(drawn)`.
- The tally scores `placed>placed` (DF's aiming isolated) apart from anything involving a drawn, released or fort-side unit.
- **Not built:** an automatic no-tool control arm per cell. Removing the tool-enabling steps from a cell cannot be done safely in general. Where a block needs that control, write it as its own cell (SW1/SW2's `ctl` already are).

### H5: one group definition, checked three ways

`cx-eco groups3 base|TAG` (`cx-eco.lua:917`).

**The definition:** a group is the live, on-map animals that share three things:
- species;
- population entry (ref6);
- arrival sample: the first `groups3` call that saw them (units on the map at `base` share that sample).

This is B 16.3's three-source key. Two waves of one species from one entry at different samples stay two groups; that was T8g's merge failure.

**Cross-checks:**
- **(2) the tool's record:** which canonical groups each `g.groups` entry's live members fall in;
- **(3) DF's population entries:** quantity now against the reading at `base`. This is a net figure: debits, refunds and regrowth all move it (trap 16).

**Per group**, the verdict is one of:
- `match`;
- `untracked`: no tool group;
- `split`: more than one tool group;
- `notool`: the tool is not loaded.

**Per tool group:** `ok`, `merged` (it spans more than one canonical group), or `stale` (no live member).

**Per layer:** a `g3sum` row. Deep layers are excluded (R60), and so are fort-side and non-natural units.

**Where it runs:** SW3, SW5, SW6 and the B1 baselines log `groups3` at every sample.

### H6: bouts and hidden sampling

**`cx-eco watch [bout_gap=100] [wildpred]` samples hidden flags** (`hidden_in_ambush` / `hidden_ambusher`) every 10 t on:
- every placed unit;
- every unit that attacked in the last 300 t;
- with `wildpred`, every flagged wild CARNIVORE or LARGE_PREDATOR.

Each attack also carries the attacker's hidden samples from the 300 t before it (`hid`/`hn`).

**`read` adds:**
- `bout`: per attacker, the count of attack runs whose gaps are under `bout_gap`;
- `bouts`: per token, per hunter-day. Hunters are the placed units of that token at the watch; a hunter-day is 1,200 t;
- `hidden`: samples, hidden samples, and the share in the 100 t after the unit's own attacks.

The attack log is capped at 5,000 rows per cell, and an `atk_over` row counts the rest. `ecolib.bouts_from_rows` re-counts bouts offline from the `atk` rows.

### H7: the figure-spec check

- `scripts/eco-report/figcheck.py` runs from `build.py` on every placed figure.
- **Errors:**
  - `value-first`: a categorical form whose x is numeric in every row while its y holds text;
  - `no-rows`;
  - `missing-key`: the spec names a field no row has;
  - `zero-marks`.
- **Warning:** `ref-on-axis`, a reference value more than 10 times outside the value range.
- `build.py` refuses to write the page while an error stands (exit 2); `--allow-bad-figs` overrides.
- **On today's data** it names:
  - exactly the eight value-first specs of D section 4;
  - `raw-15a`, the R28 depth figure: `form: range` with no lo/hi fields, so no bars are drawn;
  - figure 17's tick reference, as a warning.
- The held `fig-diag` patches are **not** applied. The report waits for Part 2, so the page build fails until they are.

### R15: the wipe

**`cx-eco wipe [livestock] [close]`** (`cx-eco.lua:876`; `cx-load wipe` forwards to it):
- Every animal on the map is set to vanish on the next tick. That is exterminate's method: `vanish_countdown 1`, no corpse.
- **An animal** is a live on-map unit that is none of:
  - fort-side: citizen or resident, or livestock, pet or fort-controlled (livestock is taken only with the word `livestock`);
  - a guest: merchant, diplomat, visitor, invader, or another civ's member;
  - non-natural: megabeast, FB, titan, demon, night creature, undead, GENERATED (fb_safe);
  - on the deep layers (R60).
- **The receipt** counts what was marked by origin (drawn, placed, released, livestock) and what was kept by reason.
- **`close`** also closes the site's Animal entries, so no new natives arrive. This happens in memory only and is never saved.
- **`wipecheck`** prints `remaining` and `pending`.
- **eco-run** wipes, steps 5 t and checks. If an arrival slipped in, it wipes and checks once more. If anything is still left, that is a `MANIPFAIL`.

**Blocks whose subject is the natives opt out**, each with its reason:
- RELS, RELS2, RELS2b, RELS3, RELP, SLOTV, LAKEP;
- SW3, SW3B, SW4, SW5, SW6, SW7 (natural arrivals);
- the surveys DEPTH, DEPTHL and O;
- the B1 baselines.

**In cx-experiment:**
- An arm whose `pre` calls `cx-eco spawn`, `cx-load wild` or `cx-probe spawn`/`spawn2` is wiped first; a failed `wipecheck` invalidates the replicate.
- FPS2 and FPS2b opt out, because their wild load is added on top of the natives on purpose.

**Vermin** are not units and are not wiped. With fresh loads per arm, VRM's pile-up cannot recur.

### Rig placement aligned with the tool's PLACE.one (ANSWERS R1)

`cx-eco spawn` (`cx-eco.lua:470`) differed from the tool in four ways. Options now follow the 10 positionals:

| | pre-v7.1 rig | v7.1 default | option |
|---|---|---|---|
| enemy-status row and column of the new slot | **0 = STRANGER**, which predators fight (E11c). Every rig-placed hunter before today started with it | **−1 = NONE**, as DF's empty cell and the tool since v7.0 (SLOTV, addendum 96d) | `slot=none` / `slot=stranger` |
| population reference | the race's first Animal entry anywhere in the world, else a borrowed surface entry of another species | the race's entry on the site's region tiles (+1 ring), on the medium's layer first; then the first in the world; then borrowed | `ref=site` / `ref=first` |
| stock | never debited | 1 per unit from the referenced entry (floor 0), never from a borrowed one | `debit=1` / `debit=0` |
| leave countdown | 200,000 | **unchanged: 200,000**, so a subject stays for the whole cell. The tool's PLACE.one uses 25,000; pass it as the 10th positional to match | positional |
| roaming flag | cleared | cleared. eco-run's `--isolate roam` keeps it | `roam` |

`legacy` sets all three old behaviours at once (`slot=stranger ref=first debit=0`). `eco-run.py --placement legacy` appends it to every spawn, so an old block reproduces exactly. The receipt now prints `ref`, `slot`, `debited` and `countdown`.

## 4. Smaller fixes

**`chronicler-bridge.lua:1784`:** the fort's weather now comes from `dfhack.maps.getCurrentWeather()` (r2), falling back to `current_weather[2][2]` on r1.1, where no correct reader exists. `[2][2]` is the grid's centre, usually a neighbouring region (`dfhack-r2/REPORT.md` 2.2).

**`53.16-r1.1` labels, now read at runtime:**
- `validate-full.py`: `rig_versions()`, logged at setup, written to `rig.json`, and used in `doc.usage.version`.
- `validate-report.py`: the eyebrow takes the tool and rig versions from the run.
- `alpha2-run.py`: `versions()` gives DF, DFHack, the deployed tool version and its commit.
- The ECO report's prose and the bestiary keep "r1.1" where it describes runs that did happen on r1.1.

**The validator's backlog register** (`validator-backlog-stale`):
- Seven items are now `shipped vX`:
  - frequency, popnumber (v6.5);
  - concurrency, quiet (v6.9);
  - largestmale, deepwater, realm (v7.0).
- **How a full run records them** (`resolve_shipped_backlog`, `validate-full.py:2726`): from the claim that exercises each, as PASS, FAIL, or NOT-TESTABLE-HERE naming the claim. deepwater and realm point at TODO claims.
- Six stay BACKLOG: grouping, migrants, perch, r2r4, eats and balance.
- The stale "leader is lowest-id" note is removed.

**`cli.water` recorded twice:** the timed `water now` check is now its own claim, `cli.water.now`.

**`phase_v71` stub** (`--only v71`; it also runs in a full run on v7.1+). It lists the reserved ids from `validator-v70-coverage`:
- `mech.v70.builder`
- `mech.v70.gobble`
- `mech.v70.scav_ext`
- `mech.v70.outgun`
- `mech.v70.realms`
- `mech.v70.gate_drain`
- `mech.v70.solo_skill`

None is in CLAIMS until its check is written (validator wave 2). The list goes to `v71-todo.json` for each run.

**cx-probe invasions** (R23):
- DF's invasions are off in the game code, so E23f is not needed.
- The guard stays, as one `is_invader` test (`invasion_id >= 0` or the invader flags) that mirrors the tool's WILD.onMap.
- `units` gains an `invader` column (`wild=0` for an invader), and `wild_alive` and `release` skip invaders.

## 5. R11: the region8 test world and the 1x1 programme

**The world:**
- `region8` in the save directory: Snospdastrasp, "The Last Planets".
- It is now the harness's test world: `CX_TEST_WORLD`, `CX_TEST_WORLD_NAME` and the `R8` tag in `cx-config.sh`.
- `cx-lifecycle.sh survey` and `rivers` default to it.
- `cx-lifecycle.sh embark1 RX RY NAME [ox=7 oy=7]` embarks a 1x1 from it. Offset 7,7 is the centre of the region tile, so the 9 region_offset neighbours a block can draw from are as far from other biomes as a 1x1 allows (memory df-region-draw-tiles).

**region8 itself is never written:**
- Every embark saves under its own new name; a manual save is a copy.
- `b1-forts.py` backs up region8 once (`region8.pre-b1`) and hashes it after every embark. Any change stops the programme and asks the user.
- region8 is also the user's own game world, so the programme runs only when DF is not the user's game.

**No survey of region8 exists yet**, and its region data cannot be read from the save on disk. The survey is therefore a rig step:

1. **`b1-forts.py survey`** (rig, about 1 min): `survey region8` and `rivers region8` write `data/forts/region8-survey.tsv` and `region8-rivers.tsv`.
2. **`b1-forts.py pick`** (desk): writes `data/forts/region8-b1-picks.tsv`. It picks the needs in this order:
   - **shore:** a land tile with ocean neighbours, with the 1x1 on the side facing the water (offset 0 or 15);
   - **lake:** away from a major river;
   - **river:** a major river through interior land;
   - **savage:** savagery 66 or more, not mountain where possible;
   - **calm:** savagery under 33;
   - **good:** evilness under 33, not savage where possible;
   - **evil:** evilness 66 or more, not savage where possible;
   - then one interior tile per remaining land biome: no site, same8 = 8, mid savagery and evilness.
   - A need the world cannot meet is listed as MISSING, which calls for B 10.2's seed search. It is never invented.
   - Tested on region6's survey: 7 needs plus 18 land biomes, one tile each.
3. **`b1-forts.py embark [--only NEED,...]`** (rig, about 4 min per fort). For each pick it runs:
   - `embark1`;
   - `title`;
   - `facts NAME`, saved to `data/forts/b1/NAME.facts.txt`;
   - `save-backup NAME preverify`;
   - the region8 hash check;
   - then it adds a registry row to `data/forts/b1-forts.tsv`.

   **Names** follow `B1-R8-<CODE>-<rx>_<ry>[-NEED]`, for example `B1-R8-OCNT-03_17-SHORE` (B 10.5).
4. **eco-run** builds a `B1BASE_<save>` block from each registered fort:
   - tool on, `layer_groups` on, natural arrivals;
   - 50,400 t, sampled every 5,040 t;
   - `groups3` (H5) and `ecostate` at every sample;
   - 5 reps;
   - wipe off, because the natives are the subject.

   Run the six named needs first (B 10.6).

**Checks per fort, after the embark:** read `facts` for:
- water by body, and whether the shore and lake forts actually hold water (flags `verify-water` and `verify-river`);
- the 9-offset region union;
- the cavern depths present;
- alignment. The `world_region` good/evil flags that `V7.alignment` also reads are not in the survey.

## 6. Rig tests this needs, later

All of them run on **region8 forts, 5 reps per arm, short reps** (R11, R12), on DFHack r2, and only after `revalidate-dfhack-r2`.

1. **Smoke the new cx-eco verbs** on one B1 fort, 1 rep:
   - `wipe` then `wipecheck` reads 0, with the counts by origin plausible;
   - `spawn` shows `slot=-1` and the rel_map row reads −1 (`cx-probe relrow`);
   - `ref=site`, with the entry debited;
   - `roam` keeps the flag;
   - `adopt` gives `adopted=1` on the v7.1 tool;
   - the `watch` sampler: `hidden` rows appear and nothing stalls (10-t repeat-util);
   - `groups3 base` then `groups3 t1` gives the rows and `g3sum`;
   - `cfg`, `skill`, `relcount` and `ecostate`.
2. **`eco-run.py SW2 --reps 5 --tick-scale 0.5`:** the manipulation checks must pass (pack adopted, SNEAK written in sneak100); otherwise the block aborts as designed.
3. **The `--placement legacy` vs `tool` pair on P1's wolf × deer written cells:** does the STRANGER row change attack counts?
4. **The B1 programme:** `survey`, `pick`, `embark` the six named needs, then their baselines.
5. **validate-full on v7.1**, checked for:
   - `cli.water.now` recorded once;
   - the shipped backlog resolved;
   - `rig.json` reading r2.

## 7. Open risks

- **adopt depends on the tool.** If the v7.1 tool's `groups adopt` prints a different receipt, nothing breaks, because the harness reads `sw.loadGroups()` and not the reply. But if adoption groups by a key other than "these ids", `adopted` can read 0 for a correct adoption.
- **`--isolate roam` with the tool on:**
  - The tool's gate drain may release the placed group mid-cell; the attack origins show it (H3).
  - Flagged placed units also hold DF's surface gate shut, so no surface waves arrive during the cell.
  - Both are intended, but they are new conditions for every old block re-run under v7.1 defaults.
- **The wipe** relies on `vanish_countdown` removing the unit next tick, as `clear` and `clearwild` already do. A unit DF refuses to vanish would fail `wipecheck` and abort the block. That failure is loud, not silent.
- **`spawn` debit** lowers the site's stock for the placed species. Over a long cell DF draws that species less. With fresh loads per arm this does not carry between cells. Use `debit=0` where a block reads that species' natural arrivals.
- **Fresh load per arm costs about 2.5 min per cell** (restart and load), against about 7 s of stepping for a 3,000-t cell at 450 t/s: loads, not ticks, set the wall time of a short-cell block. P1 (80 cells × 5 reps) is about 20 h at tick scale 0.5 (`eco-run.py plan`), so trim arms before running it, or use `--load rep` for blocks whose cells are independent by design (the wipe still clears every cell).
- **`b1-forts.py`'s shoreline offset is a desk guess**, because DF's biome edges are ragged across mid-level tiles. The `facts` water check after the embark is what decides.

## 8. Changelog fragment (DwarfCron, harness v7.1)

```
harness v7.1 (1 Oct 2026, W2:Urist)
- eco-run: 5 reps per arm (R12), fresh load per arm with counterbalanced order (H1), every cell wiped of animals
  before placement (R15), manipulation checks that abort the block (H2), placed packs adopted by id (H3), placed
  units keep DF's roaming flag (H4), three-source group logging (H5), plan / --dry-run / --tick-scale.
- cx-eco: wipe, wipecheck, groups3, adopt, cfg, skill, relcount, ecostate; watch logs timestamped attacks with
  origins, bouts and hidden samples (H6); spawn places like the tool's PLACE.one (NONE row, own entry, debited),
  'legacy' reproduces the old rig.
- cx-experiment: 5 reps per arm, counterbalanced interleave, wipe before arms that place animals.
- R11: region8 is the test world; cx-lifecycle embark1; scripts/b1-forts.py (survey, pick, embark, status).
- eco-report: figcheck fails the build on value-first / zero-mark specs (H7).
- validator: shipped backlog resolved from its claims, cli.water.now, rig versions at runtime, phase_v71 stub.
- cx-probe: invaders kept out of wild counts (R23 guard). chronicler-bridge: getCurrentWeather (r2).
```

## 9. Merge hazards

- No edits in seasonal-wildlife, and none in its GUI or web files. There is no Panel/web surface, because the harness has none (rule 5 does not apply).
- **Shared spots in DwarfCron that another branch may also touch:**
  - `scripts/eco-run.py`: the header, `sh`/`eco`, `sw_arena`, sw1/sw2/sw3/sw4/sw5/sw6, the tail (the WIPE_OPT_OUT and B1 blocks), and `main`, which was rewritten whole;
  - `chronicler/dfhack/scripts/cx-eco.lua`: the header, `spawn`, `watch`, `read`, `clear`, and the new verbs before the final `else`;
  - `scripts/validate-full.py`: the backlog rows in CLAIMS, the `cli.water.now` claim, `rig_versions`, `phase_static`'s backlog loop, the new resolver and stub before `phase_teardown`, and `main`;
  - `scripts/cx-lifecycle.sh`: the header comment, `cmd_survey`/`cmd_rivers` defaults, `cmd_embark1`, and the dispatcher;
  - `scripts/cx-config.sh`: a new test-world block;
  - `experiments/FPS2.json` and `FPS2b.json`: `"wipe": false`.
- **New files:**
  - `scripts/ecolib.py`, `scripts/b1-forts.py`, `scripts/eco-v71-tally.py`;
  - `scripts/eco-report/figcheck.py`;
  - `tests/harness/*`;
  - this document.
