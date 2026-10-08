# Rig harness inventory (DwarfCron, read 8 Oct 2026)

What runs and analyses experiments on the Dwarf Fortress rig (DF 53.16 Steam + DFHack 53.16-r2 under CrossOver, RPC on
127.0.0.1:5555). Read from the code only; nothing was run against the game. Paths are relative to
`/Users/nathanielcannon/Claude/Projects/DwarfCron` unless they start with `~`.

## 0. Rig state found while reading (8 Oct, afternoon)

- **DF is running** (pid 78677; the save dir holds a `current` folder), so the rig was in use. Nothing here touched it.
- **The engine on the rig is the shadow copy, not the package.** `Dwarf Fortress/dfhack-config/scripts/` holds all seven
  tool files (written 8 Oct 11:47). Its `seasonal-wildlife.lua` is byte-identical to sw-wt/plugin HEAD 8185d85. The
  package copy in `DFHack/hack/scripts/` is from 7 Oct 09:49, and its engine differs (1,124,466 vs 1,170,019 bytes). The
  dll in `DFHack/hack/plugins/seasonal-wildlife.plug.dll` is from 8 Oct 15:04. DFHack finds dfhack-config/scripts first,
  so the v7.3 runs used hot-swapped scripts with a newer dll. This is the shadowing trap of memory `v72-package`. A test of
  "the package as shipped" must first remove the dfhack-config copies (with DF stopped).
- `dfhack-config/seasonal-wildlife.json` reads `{"autostart": true}`.
- **No `.preverify` backup exists for any v7.3 or test-item-1 fort.** `df-snapshots/saves/` holds 25 backups, newest
  AQUA_SHORE16 / AQUA_LAKE / region9 / RinghatchetsReady. `cx-experiment.py` and `eco-run.py` restore from these, so
  they cannot run on V73_* / T1END_* forts until someone takes `save-backup <fort> preverify`.

## 1. Rig control: `scripts/cx-lifecycle.sh` (1,115 lines; config `scripts/cx-config.sh`)

Every verb is one shell call. In-game steps go through `chronicler-ui` / `cx-embark` / `cx-probe` / `cx-load` / `cx-eco`
(Lua in `chronicler/dfhack/scripts/`, installed by `deploy`). Dispatch: `cx-lifecycle.sh:1072-1114`. With no verb or an
unknown one it prints the header (`:2-46`).

| Verb | What it does | Where | Notes |
|---|---|---|---|
| `start` | Sets the user's AUTOSAVE to NONE, launches DF via cxstart with `DFHACK_PORT`, `WINEESYNC=0`, console off, then waits for RPC and the title and clears the Welcome panel | `:146` | Port 5555, falls back to 5100 (`cx-config.sh:50-51`). RPC is up about 10 s after launch |
| `stop` / `restart` | RPC `die`, then `wineserver -k`, then TERM, then KILL; restores the user's AUTOSAVE line | `:189` | The TERM fallback is for a 2-day-old DF that ignored both (28 Sep) |
| `status`, `health` | Process, port, RPC handshake, a Lua exec | `:222`, `:236` | |
| `load <folder>` | Clicks through Continue, the world row and the fort row. Scrolls the world and save lists by `scroll_position_*`. Refuses a folder name that is a prefix of another. Tries the last world row when two worlds share a name | `:878` | Times out at `CX_LOAD_TIMEOUT` = 180 s |
| `state` / `pause` / `unpause` | One line: screen, focus, map, paused, year, tick, modal | `:755-757` | |
| `step <ticks> [secs=120]` | Drains popups, unpauses, polls the tick every 0.25 s, then pauses and confirms it. Handles the year wrap, empty reads, stalls (drains popups, backs out of menus) | `:805` | Warns on a short step. **Pass a larger `secs` for long steps** |
| `fps [cap] [gfps]` | Reads or sets `enabler.fps/gfps` | `:783` | Refuses fps < 10 (0 freezes DF for good) |
| `save [name]` | With a name: a manual save to a NEW folder via Options. Without one: DFHack `quicksave`, which writes **DF's `autosave N` slot** | `:946` | Use only named saves for test forts |
| `title` | Quit without saving, back to the title | `:986` | |
| `popups` | Empties `world.status.popups`, which halts the simulation silently | `:770` | |
| `save-backup <region> [tag]` / `save-restore <region.tag>` / `saves` | Copies one save folder to or from `df-snapshots/saves/`. A restore touches every file so the save sorts newest in DF's list | `:324`, `:335`, `:356` | Restore needs DF at the title, not in a fort |
| `save-delete <folder>` | | `:1010` | Refused while a map is loaded |
| `snapshot` / `restore` / `snapshots` | Copies the whole 5.4 GB bottle | `:1047-1068` | DF must be stopped |
| `genworld <title> <seed> [preset=7] [end-year=5]` | Unattended worldgen; prints the folder | `:472` | Preset 7 (33x33) takes about 15 s |
| `survey [world] [filter]`, `rivers [world]` | Region-tile tables from the site screen | `:666`, `:657` | Default world `CX_TEST_WORLD` = region9 |
| `embark <world> <rx> <ry> <name> [ox oy]` / `embark1 <rx> <ry> <name> [ox=7 oy=7]` | In-script placement (no pointer), Play now, map load, position check, named save | `:690`, `:749` | **Set `CX_EMBARK_SIZE=N` explicitly.** `CX_EMBARK_STOP=1` stops in placement mode |
| `facts [save]` | The fort's site record, tiles, edges, features, population per layer, clock | `:677` | |
| `deploy` | Flat copy of `chronicler/dfhack/scripts/*.lua` into dfhack-config/scripts | `:260` | |
| `deploy-tool <dir>` | Copies a tool tree into **dfhack-config/scripts** and cmp-checks the tool's 5-7 files | `:278` | **Shadows the v7.2 package in hack/scripts; not for package tests** |
| `lua <code>` / `cmd <args>` / `probe <args>` | Raw Lua / a DFHack command / `cx-probe`. `cmd` prints any traceback that lands in stderr.log | `:1023`, `:1028` | `CX_RPC_TIMEOUT`, default 15 s |
| `key`, `type`, `wait`, `screen`, `ui` | Drive DF by on-screen text | `:1017-1020`, `:363` | |
| `logs [n]`, `port`, `bottles`, `autosave [status\|off\|restore]` | | `:1040-1042`, `:1113` | |

## 2. Experiment runners

### 2.1 `scripts/cx-experiment.py`: manifest-driven wilderpop replicates (808 lines)

- **Usage:**
  - `cx-experiment.py run experiments/X.json [--reps N] [--arm a,b] [--budget T] [--order counterbalance|interleave|blocked] [--manifest-reps]`
  - `cx-experiment.py report data/experiments/<id>/<run-id>`
  - Header `:1-38`, argparse `:795-802`.
- **Input:** a manifest JSON in `experiments/`. The library holds E1-E42b, ECO-*, ECO2-*, FPS1-FPS3b and E25/E26 per-fort
  variants: about 90 files. Its keys:
  - required: `id`, `fort`, `backup`;
  - optional: `fps` (default 1000), `gfps` (default 10), `sample_every` (default 200), `tick_budget` (default 20,000);
  - `arms[]` with `pre`, `on_arrival`, `after_on_arrival`, `every`, `stop_when`, `tool_must_be`, `tool_may_vary`, `wipe`, `fort`/`backup`, `stopwatch`, `roster`.
  - A manipulation is either `probe:<args>` or raw Lua (`:238`).
- **One replicate** (`run_replicate`, `:292`):
  1. Go to the title, `save-restore <backup>`, and sha256 the tree against the backup.
  2. `load`, `popups`, `fps`.
  3. Baseline: `cx-probe clock/units/pops/pops all`.
  4. R15 wipe if the arm places animals (`wants_wipe`, `:251`; `cx-eco wipecheck` must read 0).
  5. `pre` manipulations, then assert `tool_must_be`.
  6. Step-and-sample until the budget runs out, checking liveness at every step: the tick advanced, no popups, a sane
     unit count, the tool state unchanged.
  7. Quit without saving, then re-hash the save folder.
  - The budget counts from after the t0 manipulations, in case they moved the clock (`:404-412`).
- **Defaults:**
  - 5 reps per arm (R12, `:575-580`).
  - Counterbalanced order: odd reps run the arms in written order, even reps reverse it (`arm_order`, `:259`).
  - A failed replicate is recorded and the run goes on; DF is restarted if needed (`:612-620`).
- **Output** in `data/experiments/<id>/<run-id>/`: `manifest.json`, `provenance.json` (DF/DFHack versions, the commits
  of DwarfCron and of `SW_REPO`, default `~/Claude/Projects/seasonal-wildlife`, which is the v7.0 checkout: set `SW_REPO`),
  `rows.tsv`, `units.tsv`, `pops.tsv`, `events.tsv`, `log.txt`, and then the report.
- **Runtime:** loads, not ticks, set the wall time. The restore and load take about 40 s to 2.5 min; a restart per
  replicate would add about 40 s (`cx-lifecycle.sh:342`). Read `wall_s` and `ticks_per_s` in each `done:` line.
- **Pre-flight:** `scripts/manifest-lint.py experiments/*.json` runs `luac -p` on every Lua chunk and refuses any
  `frequency = 0` write (addendum 54: zeroing the last underground vermin-rotter freezes DF).

### 2.2 `scripts/eco-run.py`: ECO behaviour blocks (1,473 lines; library `scripts/ecolib.py`)

- **Usage:**
  - `eco-run.py BLOCK[,..] [--reps 5] [--only cells] [--load arm|rep] [--order counterbalance|rotate|fixed] [--no-wipe] [--manip abort|skip] [--isolate roam|none] [--placement tool|legacy] [--tick-scale F] [--dry-run]`
  - `eco-run.py list`
  - `eco-run.py plan BLOCK --tick-scale F`: a wall-time estimate with no rig.
  - Header `:1-31`.
- **Model:** a block is one fort plus cells. A cell is a list of `cx-eco` verbs (spawn, rel, flag, lead, adopt, watch,
  read, clear) plus `step:N`, `lua:`, `read:TAG` and `check:KIND[k=v].KEY OP VALUE`.
  - v7.1 defaults: a fresh load per arm, 5 reps, counterbalanced order, a wipe before placement, a manipulation check
    that aborts the block, and placement the way the tool's PLACE.one does it.
  - Full description: `experiments/HARNESS-v71.md` §1-3.
- **Output:** `data/experiments/ECO/<run>/<BLOCK>.tsv`, one row per `eco ...` line.
- **Readers:**
  - `scripts/eco-v71-tally.py`: manipulation receipts first, then attacks by origin, bouts, hidden and groups3;
  - `scripts/eco-analyze.py`: kills, attacks and groups per cell;
  - `scripts/eco-report/build.py`: the ECO page, with the `figcheck.py` gate.
- **Runtime** (HARNESS-v71.md §7, `:343`):
  - a fresh load per arm costs about 2.5 min per cell;
  - a 3,000-tick cell steps in about 7 s at 450 t/s;
  - P1 (80 cells x 5 reps) is about 20 h at tick-scale 0.5.

### 2.3 `experiments/HARNESS-v71.md` (377 lines)

This is the v7.1 harness spec (1 Oct). It covers:
- the defaults table (§1);
- usage (§2);
- the fixes H1-H7 (§3): fresh load per arm, manipulation checks, adopt-by-id, the roam flag, groups3, bouts/hidden, figcheck;
- R15 wipe semantics;
- `cx-eco spawn` aligned with the tool's PLACE.one;
- the R11 1x1 fort programme via `scripts/b1-forts.py`: `survey` and `embark` run on the rig, about 1 min and about
  4 min per fort; `pick` runs at the desk (§5);
- open risks (§7).

Its region8 test-world text is superseded by region9 (`cx-config.sh:41`) and, for v7.3 work, by region19 forts.

### 2.4 v7.3 season-run tooling: `data/t1-season/`

The pipeline behind test item 1 (7 Oct) and the v7.3 season-cast runs (8 Oct). It has no single driver. The
per-fort recipe, read from the files each run left behind, is:
1. load the fort;
2. `sw-t1-recorder start sw-t1/<NAME> 100 [pops]`;
3. dump `seasonal-wildlife cast status` to `casts-start.txt` (and the water bodies when relevant);
4. `run-season.sh <NAME>`;
5. dump the casts, the ledger and `ecology pairs tsv` at the end;
6. `sw-t1-recorder stop`;
7. copy `Dwarf Fortress/sw-t1/<NAME>/` into `data/t1-season/<NAME>/`;
8. run the checkers below.

| Tool | Usage | Inputs | Outputs | Runtime |
|---|---|---|---|---|
| `run-season.sh` (26 lines) | `run-season.sh NAME` (fort already loaded) | Live rig on port 5555 | `NAME/run.log` | Steps to 2,000 ticks past the next season change in 10k chunks (`:9`, `:16`). Runs `cx-load sustain` after every chunk (`:23`). **No mid-run save** (`:24`). Exits 3 on an empty RPC tick read (a hang), 2 on a failed step. A 2x2 fort does 10k ticks in 27-35 s fresh, about 60 s in a longer session; spring to autumn (about 160k ticks) takes 12-15 min. A 6x6 does 10k in about 85 s; a 16x16 in about 255 s (one season about 1 h) |
| `sw-t1-recorder.lua` (254 lines; deployed in dfhack-config/scripts) | `sw-t1-recorder start DIR [EVERY=100] [POPS]` / `stop` / `status` (`:3-7`) | Runs **in game** on a repeat timer, with no RPC polling | `DIR/events.tsv` (ARRIVE/LEAVE/RETURN/DIE/TAME/KIND with cause and killer), `positions.tsv` (every 1,000 ticks), `reports.tsv`, `samples.tsv` (wild, in groups, pets, dead, fps), `pops.tsv` (with POPS), `ledger.tsv` (the tool's ledger, live, so the 300-entry cap does not bite) (`:9-19`) | Citizens are not recorded |
| `v73_check.py` (162 lines) | `v73_check.py DIR [PREV_DIR...]` | Recorder TSVs, `casts-start.txt`, `ledger.txt`/`ledger.tsv`, `pairs.tsv`, and the DF raws (for token names with spaces) | Console: each managed-layer arrival set against its season's cast (in the cast, or a leak and why), groups sent off at the season change, relation pairs by who set them | Seconds |
| `v73_part.py` (177 lines) | `v73_part.py > v73.part.html` | The run list `RUNS` (`:9`) | The report's v7.3 section, built from `v73_check.summarize` and `f0_compare.cavern` | |
| `f0_compare.py` (49 lines) | `f0_compare.py A_DIR B_DIR ...` (pairs: arm A restfreq 1, arm B restfreq 0) | As above, plus `run.log` | Cavern arrivals per season, ledger groups in or off the cast, the gate's sendoffs, fps, and step seconds per 10k (a freeze shows as a stalled step) | |
| `analyze.py` | `analyze.py DIR [--underworld-z N]` | The TSVs and `ledger.txt` | `DIR/summary.md` (`fill_removed` names `?` departures) | |
| `report_data.py` | `report_data.py DIR > DIR/report.json` | The TSVs, ledger, roster | Demographics, interactions, timings | |
| `build_report.py` (+ `figures.py`, `report_template.html`) | `build_report.py OUT.html` | Each fort's `report.json` (`FORTS`, `:8`) | Test-item-1 report page (published as artifact 6sPcvuJAWB6FbRtkei78Cs) | |
| `headlines.py`, `roster_classes.py` | `headlines.py DIR..`, `roster_classes.py DIR..` | | Headline numbers; roster species classed vermin/predator/prey from the raws | |
| `sw-roster-dump.lua`, `sw-native-probe.lua` | Deployed scripts, one-shot reads | | Roster TSV; where each water native came from | The roster-dump header cites a `cx-lifecycle lua-file` verb that does not exist; use `cmd sw-roster-dump` |

Run directories (each holds `NOTE.txt` with what it is): V73_WATERFALL, V73_WINTER, V73_WREN, V73_BROOK, V73_LAKE2,
V73_LAKE3, V73_OCEAN2, V73_OCEAN2_AU (lost to thirst), V73_OCEAN3, V73_LAKE_F0 and V73_OCEAN_F0 (arm B of the cavern
rest test), plus T1_* / FALLS_2. All are n = 1 per arm (`24820a1`: "n=1 per arm so pending").

### 2.5 `scripts/aquarium-run.py`: aquarium rig test driver (1,597 lines)

- **Usage** (header `:7-21`):
  - `aquarium-run.py [--only setup,t1,..] [--skip ..] [--embark-shore] [--deploy] [--presets vanilla,aquarium,clear] [--t2-presets ..] [--t3-presets vanilla,aquarium,shallows] [--frames 6 --gap 0.25] [--perf-reps 5 --perf-secs 10] [--dry-run]`
  - The fix loop: `--view lake|river|brook|mist|surf|ocean|fish [--fort F] [--paused]`.
- **Stages:** setup, shore, t1-t11 (`:52`).
  - setup: deploy identity, `aquarium status`, and the mod plus its installed copy;
  - t1: per-preset transparency against a vanilla arm, with dry control cells;
  - mist: Mist/Steam drawn and animating;
  - t2: fish below the surface;
  - t3: ocean darkness;
  - t4: waves over 6,000 ticks;
  - t5: surf;
  - t6-t11: lens, legend, veil, perf (stopwatch), fuse, verbs/web round trip, uninstall guard.
  - Forts: AQUA_LAKE, AQUA_SHORE16, RinghatchetsReady (`:53`). Each is restored from `.preverify` and never saved.
  - Thresholds: `TRANS_MIN`, `CONTROL_MAX`, … (`:56`).
- **Output** in `data/aquarium-run/<stamp>/`: `results.json`, `report.md`, `log.txt`, `receipts/`, `shots/` (PNG, boxes, GIF, contact sheet).
  Exit 0 when no row fails, 1 when one fails, 2 when the run could not start.
- **Stale defaults:**
  - `--tool-src` defaults to `~/Claude/Projects/sw-wt/rc` (`:1534`);
  - `--deploy` uses `deploy-tool`, which shadows the package (`:630`);
  - it reads the mod at `installed_mods/seasonal_wildlife_aquarium (1)`;
  - it is still framed on the v7.1 Lua aquarium. Re-point it before using it on the v7.2 plugin renderer.
- **Related:**
  - `scripts/cx-record.sh SECONDS [NAME] [--fps N --crop X,Y,W,H --gif]` records the DF window (ScreenCaptureKit plus ffmpeg) to mp4, GIF or frames;
  - `scripts/oneoff/aq-*.py` are probes.

### 2.6 Validator: `scripts/validate-full.py` (7,704 lines) and `experiments/VALIDATOR-v71.md` (478 lines)

- **Usage** (`:22-27`, argparse `:7566-7572`):
  - `validate-full.py [--fort CTRL] [--skip-lake] [--skip-gui] [--only w0|model|mech|v65|v66|v68|v69|v70|v71|gui] [--v71 deploy,fixes,ecology,groups,water,roster,extinct,vermin,scav,irruption,perf,web] [--preset]`
  - `--list [TEXT]` prints the claim register (411 claims); `--dry-run` checks offline: luac53, engine names, verbs.
- **Verdicts:** PASS / FAIL / DEAD / UNWIRED / DOC-DRIFT / NOT-TESTABLE-HERE / BACKLOG (`:4-15`).
  - Evidence per claim: the console receipt, a Lua probe of the game state, and a PNG plus text grid for anything visible.
  - Restores the fort and leaves it byte-identical.
- **Output:** `data/validation/full/<stamp>/` (`results.json`, `claims.json`, `shots/`, `screens/`, `ground/`, `rig.json`).
  `scripts/validate-report.py [run_dir] [-o out.html]` builds the self-contained page.
- **Runtime:**
  - the last full v7.1 run on DFHack r2 (`data/logs/validate-v71-r2b.log`) took 8 min, 00:17:51 to 00:25:50 (PASS 357, NOT-TESTABLE-HERE 47, BACKLOG 4);
  - the v6.x run of 30 Sep took about 6 min.
- **Version gating reads `dfhack-config/scripts/seasonal-wildlife.lua` only** (`deployed_version`, `:55`; `DEPLOYED`, `:68`).
  - On a clean package install (engine in hack/scripts) it reads version (0,0,0) and every v6.5+ phase is gated off.
  - `SW_TOOL` defaults to `~/Claude/Projects/seasonal-wildlife`, the v7.0 checkout (`:38`). Point it at sw-wt/plugin.
  - There are no v7.2/v7.3 claims yet. The v7.1 claims rest on `V7.GRP` detection.
- **Older and related:**
  - `scripts/validate-tool.py` (CLI, GUI and MECHANICS phases; superseded);
  - `scripts/web-live.py` (v7.1 companion: every route, security, registry round trip);
  - `scripts/web2-live.py` (about 15 min: polls the page cadence and drives headless Chrome);
  - `scripts/alpha4-run.py` (the 109-step Alpha Four walkthrough, one function per step, on RinghatchetsReady);
  - `scripts/alpha4-sec7.py` (Alpha 4 §7 checks);
  - `scripts/oneoff/chain-*.sh` (unattended chains, e.g. `chain-rc.sh`: deploy, validate on two forts, sec7).

### 2.7 Other experiment tooling

| Tool | Purpose |
|---|---|
| `scripts/b1-forts.py survey\|pick\|embark\|status [--dry-run]` | The R11 1x1-per-biome programme |
| `scripts/fps4-run.py`, `fps5-run.py`, `fps6-run.py` (+ `fps*-analyze.py`, `procstat.py`) | Speed experiments; stopwatch rates; DF/wineserver rusage |
| `scripts/*-tally.py`, `tallylib.py` | Per-experiment tallies; `drop_incomplete` keeps only replicates with a `done:` line |
| `data/sponge-test/run5.sh` | Resumable pattern: start, load, step 20k chunks, **save each chunk**, stop at the first event |
| `scripts/cx-rpc.py --version / --lua / --cmd` | The RPC client every tool uses |

In-game helpers (`chronicler/dfhack/scripts/`):
- `cx-probe` (clock, units, pops, tool, provenance, release, setq, countdown, kill, rel, edge, relrow, lever, spawn, gather, spawn2);
- `cx-load` (line, wild, clearwild, constwild, wipe, hold, **sustain**, citizens, work, breach, world, guests);
- `cx-eco` (spot, spawn, rel, watch, read, clear, flag, lead, wipe, wipecheck, groups3, adopt, cfg, skill, relcount, ecostate);
- `cx-embark` (worldgen, survey, place, size, site);
- `chronicler-ui` (state, screen, find, click, key, type, saves).

## 3. Saved test forts (save dir, 8 Oct; 78 folders)

| Save | World | What it is | Backup |
|---|---|---|---|
| V73_LAKE2 | region19 Smaksmo Oxdu | 2x2 at 10,42 off 7,7 on the lake's own cell (lake 1,062 tiles, two river runs, a pool); spring embark save | none |
| V73_LAKE | region19 | First lake try on the seam (10,41): **no water**. Do not use | none |
| V73_OCEAN2 | region19 | 2x2 at 63,46 off 8,6: one ocean column, one shrubland; salt ocean 6,191 tiles, up to 4 deep; **salt only, needs sustain** | none |
| V73_OCEAN | region19 | Seam try: only freshwater pools. Do not use | none |
| V73_BROOK | region19 | Fresh 2x2 at 21,22, marsh and brook; casts built at enable | none |
| T1_OCEAN_RIVER / T1END_OCEAN_RIVER | region19 | 16x16 at 54,45 +0,8; shrubland, major river, temperate ocean; spring embark / summer-day-2 end | none |
| T1_LAKE_RIVER / T1END_LAKE_RIVER | region19 | 16x16 at 14,12 +8,12; lake, marsh, major river | none |
| T1_BROOK / T1END_BROOK | region19 | 16x16 at 51,22; conifer forest with a brook | none |
| T1_FALLS / T1END_FALLS | region19 | 16x16 at 38,36; a river dropping 11 levels in steps, **no real waterfall** | none |
| FALLS_2 / T1END_WATERFALL | Whitepaged (Volalmorul), the user's world | The user's 6x6 tropical embark with a real waterfall into a gorge; T1END = summer day 2 | none |
| BROOK, FALLS, LAKE_RIVER, OCEAN_RIVER | region18/19 | 6 Oct pre-test-item-1 forts | none |
| region19 | Smaksmo Oxdu | World folder (shares its name with region18; `load` handles that) | none |
| AQUA_LAKE ("Shortsling"), AQUA_SHORE16 ("Learnedchanneled") | region10 "Camade Mare" | Aquarium forts: lake, river and pool / ocean | `.preverify` |
| AQUA_BROOK, AQUA_FALLS | region10 | Aquarium brook / falls forts (5 Oct) | none |
| AQS_OCEAN, AQS_RIVER, AQS_LAKE, AQS_PELAGIC | region11 | Aquarium plugin forts, 3 Oct (`data/aquarium-run/FINDINGS/2026-10-03-plugin-log.md:5`); AQS_RIVER has an undiscovered cavern lake | none |
| AQ2_LAKE, AQ2_SEA, AQ2_MOUTH, AQ2_TROP6 | region11/12 | 3 Oct aquarium forts. `AQ2_LAKE` is a prefix of nothing now, but `load` refuses prefix names | none |
| RinghatchetsReady / region9 | region9 "Camade Mare" | The 1 Oct standard test fort: 8x8, multi-biome, lake and river, caverns dug and revealed, depot. Validator and Alpha 4 fort | `.preverify` |
| CTRL, LAKE, OCEAN, OCEAN2, RIVER3, RIVER4, MAGMA, SPLIT, GOODF, EVILF, BOATS | region4/6 era | Wilderpop and ECO forts (CTRL: inland, dry, caverns never opened) | `.preverify` |
| FPS2E1-6, FPS6X5a | | FPS experiment forts | `.preverify` |
| region8, region1-7, region12-17 | | Worlds; region8 superseded | some |
| autosave 2, autosave 3, kideturdin_0510, talontowers_26moonstone, boatsbowed_* | **user's** | The user's own games. Never touch them | |

The autosave-1 slot the rig wrote on 7 Oct is parked at `df-snapshots/parked/autosave1-rig-quicksave-T1_OCEAN_RIVER-20261007`.

## 4. Rig traps that constrain experiment design (memory)

### Design rules (user rulings)

| Rule | Source | Consequence for a run |
|---|---|---|
| **n = 5 replicates per arm, short reps** (R12, 1 Oct). Supersedes "2 per arm" | `two-reps-per-arm` | Shorten reps rather than cut reps. Both harnesses default to 5. The v7.3 season runs are n = 1, so they are PENDING |
| **Inconclusive means PENDING, then move on.** No mid-round rig fix or redesign. Exception: aquarium visuals are fixed until they work | `inconclusive-mark-pending` | Label thin rows "pending (inconclusive: reason)"; re-run only on request |
| **Prove the subject is present before comparing arms.** A failed receipt is a trigger failure, not a negative result | `manifest-subject-receipt` | Force the precondition in `pre`, print it, and sample the subject's own count every pass. E21, E32 and E29 were vacuous without it |

### Rig mechanics

| Trap | Source | Consequence |
|---|---|---|
| DF hangs every ~40-60k ticks of fps-1000 stepping (since 5 Oct): low CPU, RPC never returns, no crash log | `rig-fast-step-hang` | Run long jobs in chunks with a timeout per chunk. Save each chunk to a NEW folder (`save NAME`, never quicksave). A silent stderr.log for more than 4 min means a hang; `stop` recovers it in about 60 s. run-season.sh does not save mid-run, so a hang loses the run |
| `quicksave` writes DF's `autosave 1`; a semiannual autosave can write a test fort into the user's Continue list (crashed DF 5 Oct) | `rig-fast-step-hang`, `embark-site-traps` | `start` sets AUTOSAVE NONE and `stop` restores it (`cx-lifecycle.sh:61-80`). After rig work, `ls -lt save/` and park every folder the session wrote |
| Never move, rename or delete save folders while DF runs | `save-dir-while-running` | Stop DF first. Two worlds can share a display name |
| Pass `CX_EMBARK_SIZE` explicitly, or DF reuses the last embark size. 16x16 embarks time out the position read (about 5 min busy) | `rig-fast-step-hang`, `embark-site-traps` | Use 2x2 (or 1x1) for per-layer tests: 16x16 runs at about 40 t/s against about 300 t/s for 2x2 |
| A seam fort misses the water: a water tile's edge cells take the neighbour's biome | `embark-site-traps` | Place on midmap cells of biome 5. Confirm with `seasonal-wildlife water bodies` after about 1,500 ticks |
| Rig embarks carry no drink; salt-only or dry forts die of thirst about 115k ticks in, and DF withers the fort | `embark-site-traps`, `fort-load-levers`, `ctrl-fort-facts` | `cx-load sustain` every chunk or cell on any run over about 100k ticks. Cells after a wither record nothing and still look valid |
| The region `site` flag misses small sites; an elevation drop is not a waterfall | `embark-site-traps` | Check the square against every site footprint. Confirm water features by inspection |
| **Process age dominates speed**: 300k ticks in one DF costs about 28%, and only a restart recovers it. A 2-day-old DF is about 3x slower | `fps-load-facts`, `fort-load-levers` | Restart DF before any timing, and compare t/s only within one session. A `step` carries about 5 s of overhead, so time with the stopwatch. +500 wild animals costs 38%; the tool on vs off is about +2% (noise) |
| Identical loads differ by 10-16% in fps | `experiment-readout-traps` 6 | Pair on/off inside one load with a sham arm. Discard the first sample after each switch |
| Never poll the user's game (port 5000) with map-wide Lua | `no-polling-user-game` | Run time series on the rig (5555) or in-plugin/in-game (the sw-t1-recorder pattern) |

### Readout traps (`experiment-readout-traps`, 34 items; the ones that shape designs)

| # | Trap | Check |
|---|---|---|
| 1 | events.tsv grows while a replicate runs | Tally only replicates with a `done:` line |
| 11 | Arrivals are listed at the sample tick | Define a wave by consecutive ids, one species, one ref6 |
| 12 | The first draw races the pre's writes | List first-sample waves; never score them |
| 13 | A replicate with no arrival is censored | Report `>window` |
| 16 | Stock traces net debit, refund and regrowth | Test a debit with a direct draw |
| 17 | A t0 clock jump spends the budget | Fixed in cx-experiment; check `ticks_per_s` |
| 20 | Cells sharing a load pile natives into later cells | Fresh load per arm; reversed order; score placed-only pairs |
| 21, 22 | A verb's "on" can be a no-op; a dial can miss its subject | Print the job's own counters and the dial's internal state; abort if unchanged |
| 24 | A Lua step error reads as empty | Abort on any traceback |
| 25 | A self-healing pass hides the bug its check targets | Check with repair off; prove the check fails on a reintroduced bug |
| 29-31 | Removals logged as race `?`; `\S+` cuts names with spaces; the ledger pads days 1-9 with two spaces | Covered in analyze.py and v73_check.py |
| 33 | The tool's ledger keeps only 300 entries; a season writes about 900 | Record the ledger live (recorder `ledger.tsv`) |
| 34 | ARRIVE kind is `wild` until the tool adopts the unit | Attribute tool vs DF from the ledger or `animal.population` |

Other trap groups:
- **Pets eat placed vermin** (18): put an off-target kind beside the target.
- **Vacuous probe paths** (14): a pcall'd bad path reads as an empty world. Run every sample line once by hand.
- **CTRL facts:** no animal people, so no cavern invasion is possible. The cavern gate saturates at 2 groups. Teleported
  citizens die at about 60 days.

## 5. What this means for efficient new runs

1. **Use 2x2 region19 forts.** They run about 300 t/s fresh, and a season takes 5-6 min. Take `save-backup <fort> preverify`
   for V73_LAKE2, V73_OCEAN2 and V73_BROOK first: none exists, and both harnesses need one.
2. **Restart DF per arm or per fort** (process age), with a fresh load per arm (H1). Loads (about 0.5-2.5 min) cost more
   than short reps.
3. **Record in game** (sw-t1-recorder plus a live ledger), not by RPC polling, and check with `v73_check.py`. Pair arms
   with `f0_compare.py`-style scripts. Five reps per arm makes 5x the 12-15 min season runs, so keep reps to one season
   or less.
4. **Chunk steps at 10k with timeouts, run `cx-load sustain` each chunk, save a named copy every ~20k** if the run is
   long (the hang trap), and park new save folders afterwards.
5. **Decide the install under test.** Either the package (remove the dfhack-config shadow copies, DF stopped) or
   hot-swapped scripts. Record which one in the provenance; cx-experiment's `SW_REPO` and the validator's `SW_TOOL`
   default to the stale v7.0 checkout.
