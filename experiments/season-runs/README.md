# Season runs: the run kit (ECO report X)

`scripts/season-run.py` is the one driver for every seasonal-wildlife season run on the CrossOver rig. The four specs
here are runs X0-X3 of the ECO report's plan (`data/eco-report/parts/plan.html`, section X).

| Spec | Run | Forts and arms | Needs |
|---|---|---|---|
| `X0.json` | Kit and backups: the forts load and the kit records what it claims | L, O, B, W; 1 cell each; 2,000 ticks | the backups (below) |
| `X1.json` | Switch round trip: on, one season, `off`, save, reload with the tool off, `on` | L, O; 1 cell each | fix batch A (F1, F3) |
| `X2.json` | Persistence: `cast off`, the turnover and the reserve across a reload | L; four scripted cases | fix batch A (F2, F6, F7) |
| `X3.json` | Season-boundary audit: spring to summer to autumn | L, O, B; 3 reps, counterbalanced | fix batch A |

Forts: L = V73_LAKE2, O = V73_OCEAN2, B = V73_BROOK, W = T1END_WATERFALL.

## How to run

```sh
# 0. once: back up the forts (DF stopped or at the title; refused for a fort DF has loaded)
scripts/season-run.py backup                      # V73_LAKE2 V73_OCEAN2 V73_BROOK T1END_WATERFALL -> .preverify

# 1. a run, then its analysis
scripts/season-run.py run experiments/season-runs/X0.json
scripts/season-run.py analyse data/season-run/X0
scripts/season-run.py run experiments/season-runs/X3.json      # ~7 h; best overnight
scripts/season-run.py analyse data/season-run/X3

# 2. afterwards, with DF stopped: move the run's chunk saves out of the save dir
scripts/season-run.py park data/season-run/X3

# a one-off run without a spec
scripts/season-run.py run --fort V73_LAKE2 --name F0_LAKE --arm restfreq0 --until season:2 \
    --pre 'seasonal-wildlife cast restfreq 0' --receipt 'seasonal-wildlife cast status ~ resting cavern species at frequency 0'

# offline: every rig call faked, answered from data/t1-season/V73_* (output in data/season-run/dryrun/)
scripts/season-run.py run experiments/season-runs/X3.json --dry-run [--dry-hang-at 12]
scripts/season-run.py analyse data/season-run/dryrun/X3
```

`run` refuses to start if a fort is loaded (another session may be using the rig; `--quit-loaded` quits it without
saving), if a fort has no `.preverify` backup, if the recorder is not deployed, or if the run name has been used
(its saves and recorder folders carry the name). Overrides: `--reps`, `--arm A,B` (a subset of a spec's arms),
`--until`, `--chunk`, `--pairs-every`, `--[no-]save-chunks`, `--[no-]sustain`, `--[no-]recorder`, `--[no-]ledger-live`,
`--[no-]restart-between-arms`, `--pre`, `--receipt`.

## One cell

A cell is one arm and one replicate. Arms run in the written order on odd replicates and reversed on even ones.

1. Restore the fort from `df-snapshots/saves/<FORT>.preverify` (`save-restore`), and check the restored tree against the backup by size and sha256. The run never touches the original folder.
2. Optionally restart DF (`restart_each_cell`). This puts the restored fort at the top of the Continue list and resets process age.
3. Load the fort by folder, then set fps 1000 and gfps 10. Read the ledger's baseline into `ledger-before.txt`.
4. Run the phases. The default cell is `pre`, `receipts`, `run`; a spec's own `phases` replace it.
5. At the end, whatever happened:
   - stop the recorder and copy its TSVs;
   - make the final ledger, pairs and casts dumps, and run the spec's `finally` items;
   - `title` (quit without saving), then hash the fort folder against the backup again;
   - write `cell.json`.

`run` phase:
- Start `sw-t1-recorder` into `sw-t1/SR_<run>_<arm>_r<k>_s<segment>` (it records in game; no RPC polling).
- Save a chunk before the first step, as a resume point that holds the manipulation.
- Then step until `until`:
  - Each step has its own deadline: `cx-lifecycle step N secs`, with secs = max(120, N/40) and a subprocess timeout 120 s longer.
  - Every `pairs_every` ticks: `ecology pairs tsv` goes to `pairs/<tick>.tsv`, `cast status` to `casts/<tick>.txt`, and the ledger is read.
  - Every `chunk` ticks: `cx-load sustain`, a ledger read, `perf` to `perf/<tick>.txt`, `states/<tick>.json` (with `state_every_chunk`), and a named save `SR_<run>_<arm>_r<k>_c<NNN>`.

`until`:
- `season:N[+K]`: K ticks (default 2,000) past the Nth season change.
- `ticks:N`: N ticks from the start of the phase.
- `before_change:N`: N ticks before the next season change.
- `tick:N`: an absolute tick.

On a hang (a step or call past its deadline, or two steps that barely move):
1. Record it in `cell.json`, `restart` DF and load the last chunk save.
2. Move the dumps from the abandoned stretch into `<series>/abandoned/`, and mark the ledger.
3. Run the receipts again (and the `pre` items with `pre_on_resume`).
4. Start a new recorder segment. The merged recorder tables keep each segment's rows only up to the tick the next segment resumed from.

After `max_hangs` (3) hangs, or a hang before the first save, the cell is HUNG.

### Spec keys

Top level, overridable per arm:
- `reps`, `until`, `chunk`, `pairs_every`, `save_chunks`, `sustain`, `recorder`, `recorder_every`, `ledger_live`, `perf`
- `state_every_chunk`, `restart_between_arms`, `restart_each_cell`, `fps`, `gfps`, `max_hangs`, `pre_on_resume`
- `live_count`, `check_files`, `backup_tag`

Item lists (the top-level list runs first, then the arm's): `pre`, `receipts`, `finally`.

An arm needs `name` and `fort`, and may add its own `phases`.

Items (pre, receipts, finally, and `cmd`/`lua`/`lua_file` phases):
- `"words ~ REGEX"` or `{"cmd": [...], "expect": RX, "expect_not": RX, "check": RX, "check_not": RX, "save_as": FILE, "name": ...}`.
- `{"lua": CODE}` or `{"lua_file": PATH, "args": [...]}` take the same keys.
- `expect` failures abort the cell (ABORTED). `check` failures are recorded in `cell.json` and the cell goes on.
- A traceback, `Could not find script` or `.lua:N:` in the output always fails the item (readout trap 24).

Phases (`{"do": ...}`):

| Phase | What it does |
|---|---|
| `pre` | runs the `pre` items |
| `receipts` | runs the receipts |
| `run` | the stepping loop above (keys as top-level overrides) |
| `cmd`, `lua`, `lua_file` | one item |
| `state` | `data/t1-season/sw-state-check.lua` to `states/<tag>.json`; `"all": true` covers every world entry |
| `audit` | `data/t1-season/sw-group-audit.lua` to `audits/<tag>.json` |
| `save` | a named save, `SR_..._<tag>` |
| `title` | quit without saving |
| `load_saved` | load a save made by `save` |
| `restart` | restart DF |
| `diff` | `{"a": tag, "b": tag, "what": [pops, raws, rel, snapshot], "expect_zero": [pops, raws, zeroed, extinct]}`; with no `a`, compares `b` with its worldgen snapshot |
| `diff_text` | `{"a": file, "b": file}` |
| `json_check` | `{"file", "key": "a.b", "op": "==", "value"}` |

## The in-game checks (sent as code through `cx-lifecycle lua`; nothing is deployed)

- `data/t1-season/sw-state-check.lua` prints one JSON line. Every read is inside one pcall, so an error prints
  `{"ok":false,...}` and aborts the cell. It loads no tool code: the tool's config, snapshot and reserve are read
  straight from its site data. The line holds:
  - every population entry within one world tile of the embark: index, token, config key, quantity, extinct flag;
  - the tool's worldgen snapshot and held reserve;
  - per race: FREQUENCY, CLUSTER_NUMBER, POPULATION_NUMBER, and the NO_season flags held by every caste;
  - PREDATOR_OR_PREY relation cells among active units, split into wild x wild, wild x other and other x other.
- `data/t1-season/sw-group-audit.lua` prints one JSON line: the tool's tracked groups against this season's cast,
  and `offcast`, the number of off-cast groups still on the map.

## Outputs

`data/season-run/<RUN>/run.json` holds:
- the spec, and the start and end times;
- the cells and their status;
- the save folders written;
- the provenance: the DwarfCron commit, and for each engine copy found (the dfhack-config shadow, which is the copy in use, and the hack/scripts package) its bytes, release string and the sw-wt/plugin commit whose blob matches it; whether the recorder deployed matches the repo; the autostart file before and after;
- DF/DFHack versions.

`<arm>/rep<k>/` holds:
- `run.log` (the run-season.sh step-line format, so f0_compare reads it);
- `receipts.txt`, `pre.txt`, `phase.txt`, `finally.txt`;
- `ledger.txt` (live; new lines counted from the footer's running total) and `ledger-before.txt`;
- the series `pairs/`, `casts/`, `perf/`, `states/`, `audits/`, `diffs/`;
- the merged recorder tables `events.tsv`, `positions.tsv`, `reports.tsv`, `samples.tsv`, `ledger.tsv`, with the raw segments in `recorder/`;
- `pairs.tsv`, `casts-start.txt`, `casts-end.txt` (v73_check's inputs);
- `v73_check.txt` and `cell.json`.

`cell.json`:
- `run` holds the status (OK, ABORTED, HUNG or FAILED, with the reason), receipts, checks, hangs, saves, segments, ticks, wall time and t/s.
- `analysis`, written by `analyse`, holds:
  - arrivals per layer and season, in cast or off it;
  - each off-cast arrival with its lead time after the season change (births apart);
  - ledger groups that came from neither the cast nor a stand-in;
  - in-cast send-offs (gate trims included), and off-cast send-offs with whether the species was off the map within 10 days (by species count in `positions.tsv`; the ledger names no unit ids);
  - stand-ins;
  - drownings within 2 days of arriving and of a tool draw, by species;
  - reserve conservation between consecutive state dumps (live plus held per key, allowing for arrivals);
  - the last `perf` table;
  - f0_compare's cavern table, median fps and s per 10k;
  - the X3 criteria and a verdict: PASS, FAIL, or PENDING when there are under 5 managed-layer arrivals (memory inconclusive-mark-pending).

`summary.md` and `summary.json` hold one row per cell and the totals per arm.

## Rig traps it guards against

| Trap (memory) | Guard |
|---|---|
| DF hangs every ~40-60k ticks at fps 1000 (rig-fast-step-hang) | a deadline per step and call; a named save every chunk plus one before the first step; restart, reload and resume |
| quicksave writes DF's `autosave N` slot (rig-fast-step-hang, embark-site-traps) | only named saves; `cx-lifecycle start` sets AUTOSAVE NONE |
| Never move saves while DF runs (save-dir-while-running) | `backup` refuses a fort DF has loaded, or an unidentified one; `park` refuses while DF runs; restores happen at the title |
| Run on a copy, never the original (harness) | restore from `.preverify`, hashed before and after each cell; quit without saving |
| `load` matches folder names by prefix | save names are `SR_<run>_<arm>_r<k>_c<NNN>`, letters and digits only and fixed width, checked prefix-free against the save dir |
| The Continue list is read once at DF start | `restart_each_cell` after the restore (X1-X3) puts the restored fort on top above the growing pile of chunk saves |
| The subject must be on the map (manifest-subject-receipt) | receipts after `pre`; any failure ABORTS the cell, and an aborted cell is a trigger failure, not a result |
| A Lua error read as empty (readout traps 14, 24) | tracebacks fail the item; the in-game checks print `ok:false` from a pcall; dumps with errors are counted and never written as data |
| A one-string `--cmd` never replies (trap 8) | command words are passed apart |
| The ledger keeps 300 entries (trap 33) | the ledger is read at every dump, and the recorder's own `ledger.tsv` captures every entry |
| ARRIVE kind is wild until adoption (trap 34) | sources come from the ledger (v73_check) |
| Rig embarks carry no drink (embark-site-traps) | `cx-load sustain` every chunk |
| Process age costs up to 28% (fps-load-facts) | `restart_between_arms` / `restart_each_cell` |
| Thin data (inconclusive-mark-pending) | verdict PENDING, never re-run mid-round |
| Cells sharing a load pile natives (trap 20) | a fresh restore and load per cell, with arm order reversed on even reps |
| `off` clears the global autostart (X1) | X1's `finally` runs `seasonal-wildlife on`; `run.json` warns if the autostart file changed |

## Known limits

- **X1 does not remove the tool's files.** "Reload with the tool absent" is approximated: `off` clears the autostart,
  so no tool code runs at the reload, and the state check reads site data without loading the tool. Removing the
  scripts would mean writing into the bottle with DF stopped, which the kit does not do.
- **X1's snapshot check:** `zeroed` and `extinct` must be 0. Other quantity differences against the worldgen snapshot
  are listed but not failed, because DF's own waves debit entries during the season.
- **X2's cases are drafts written against the fix descriptions (F2, F6, F7).** Confirm each case's trigger once batch A
  lands. For example, the refund case relies on `sendoff` making groups leave and refund before the change.
- **Send-off "left" is judged by species count.** A second group of the same species confounds it.
- **Disk use:** chunk saves run about 27 MB each on a 2x2 fort, and X3 writes about 80 of them. Park them after the run.
- **The season-test page is not rebuilt by `analyse`.** Run `data/t1-season/build_report.py` on the run's cells if it
  is wanted.
