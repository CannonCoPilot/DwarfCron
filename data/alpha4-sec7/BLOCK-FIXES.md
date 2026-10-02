# Alpha Four section 7: block fixes after the first rig run

W2:Urist, 2 Oct 2026. This was desk work only: the section-7 run (`data/logs/sec7-core3.log`, run dir `data/alpha4-sec7/20261002-024942/`) owned the rig throughout.

- **Tool under test:** seasonal-wildlife 9e5aabe.
- **Fort:** RinghatchetsReady.
- **Commits:** `0b71fe4`, `f4dd75f` (the CFG fix, S7_IRRM below), on DwarfCron Dev, not pushed. It touches `scripts/alpha4_sec7_blocks.py`, `chronicler/dfhack/scripts/cx-sec7.lua` and `experiments/ALPHA4-SECTION7.md`.
- **Verified:**
  - `eco-run.py <all 19 blocks below> --dry-run --reps 1`: every block walked.
  - `alpha4-sec7.py --dry-run --reps 1 --only <the same 19>`: 1,971 Lua chunks through luac53, 0 failed. The verdict was "dry run clean".

## Two things to know before rerunning

1. **The rig still has the old cx-sec7.lua.**
   - eco-run never deploys. The probe on the rig is the one the run's DEPLOY copied at 02:49 (HEAD `a48bbd6`).
   - The fixes to S7_SKL, S7_NAT and S7_TRIM use new probe features. These are the `far<X>x<Y>` spot, the comma-list `rustpush`/`nofloor` with their `*sum` rows, `hold.held_open`, `nat.cav_max`, and `trim.dismissed`.
   - Those three blocks need DEPLOY before they rerun.
   - Every edit to a block that has not run yet uses only verbs and fields the HEAD probe already has. The running sequence imports the blocks file fresh for each block, so it picks those edits up safely.
2. **The run's DEPLOY did not deploy the tool.**
   - The log shows `ERROR: not a directory: /Users/nathanielcannon/Claude/Projects/sw-wt/sec7/scripts`. The 9e5aabe worktree was at `/Users/nathanielcannon/Claude/Projects/seasonal-wildlife/sw-wt/sec7` then; it has since moved to `/Users/nathanielcannon/Claude/Projects/sw-wt/sec7` (verified: 9e5aabe), so the path the run used is now correct.
   - The tool on the rig (copied 01:57) is byte-identical to 9e5aabe, so tonight's data is from the right build.
   - A rerun's DEPLOY must set `SW_TOOL=/Users/nathanielcannon/Claude/Projects/sw-wt/sec7`. Without it the runner's default `sw-wt/deploy` (e16eef2, a different build) is copied over 9e5aabe.

## Aborted blocks

| block | cause (from the runner log and TSV receipts) | fix |
|---|---|---|
| **S7_SKL** | **The subjects killed each other.** Cougars were placed 6 tiles from the wolves. 24 of the 25 attack rows involving a subject were COUGAR↔WOLF (one was OTTER_MAN→WOLF). By t2000, 1-5 of the 6 wolves were gone in most cells. In rep 5 nopkg every wolf was gone, so `rustpush.units>0` read the last row, WOLF, as 0, and the block aborted after 13 good cells.<br><br>**A second writer contaminated two arms.** The pack-share sneak bonus (`hunters.skills.pack_bonus` 10, separate from `v7.solo` and `hunters.pack`; each species was the other's prey) gave every **nopkg** subject SNEAK 10 with floor 10 by t2000, so nopkg was never a no-write arm. In pkg_nofloor rep 4 it re-wrote floor 10 after `nofloor`, which spoiled that positive-control cell.<br><br>The positive control otherwise worked: in reps 1-3, floor 0 made SNEAK rust 15→14 and 10→9. | The wolves are placed at `cx-sec7 at far{X}x{Y}`. That is the nearest dry, open land spot 80-160 tiles from the cougars and 30 tiles clear of citizens, and it is new in cx-sec7's `resolve`.<br><br>`hunters skills pack_bonus 0` runs in every arm, and the check reads it back as 0.<br><br>`rustpush`/`nofloor` take `COUGAR,WOLF` in one call. They print per-token rows (units, alive, placed, lost) and a `rustpushsum`/`nofloorsum` row.<br><br>The cell check is `rustpushsum.tokens_hit>=1` in the pkg arms and `rustpushsum.alive>=1` in nopkg. With every writer off, nopkg subjects hold no SNEAK entry, so there is nothing to push. A species that is wholly lost is a censored rep with its losses on record, not an abort. |
| **S7_NAT** | **A stale v7.1 expectation.** Since 9e5aabe (`groups cavern mix`, on by default, `V7.GRP.holdLevel`/`holdFor`), the gate holds an in-season species at max(2, weight // 10) and only out-of-season species at 1. The check `hold[t3000].held_not_1==0` therefore aborted a correct gate (held_not_1=1). | **Probe:** the `hold` receipt now compares each gate-held raw with its own hold level. The base is the snapshot original (or the raw) raised to any `cfg.odds` for the token, run through `GRP.holdLevel`. It prints `held_open` (above the level: the gate did not reach that raw), `held_mix`, `held_at1`, `held_mismatch` (against `holdFor` now: after a season change this can differ with no rewrite, so it is reported, not judged), `mix`, and the old `held_not_1`.<br><br>**Block:** the check is `hold[t].held_open==0`. The def arm also checks `groups.cavern_hold_mix==true`, the gate as shipped, and the readback adds that path. The doc's row 4 is updated. |
| **S7_TRIM** | **The check fired before the pass it waited for**, with an unproven precondition. The trim acts only on groups in the tool's record. Cavern natives become groups at adoption, every 1,200 t. The trim is paced by `g.trim_next` (one day = 1,200 t), which the save carries from its own play, plus the 300-t groups pass. So the first trim can come about 1,500 t after enable, and `trim[t1200]` read 0.<br><br>**The receipt was also lossy.** It read only `g.trim_undo`, which drops a unit as soon as it is gone. | **Block:** set `groups natives cavern on`, `trim_days 1` and `mark pre`, then run `groups natives now` at t0. A precondition check, `nat[t0].cav_max>1`, proves a cavern is over cap 1. The run is 4,800 t, sampled every 300 t, with `nat` every 1,200 t. The check is `trim[t2400].dismissed>0`.<br><br>**Probe:** `trim` now keeps the ids of `trimmed` group records and counts the ledger's `dismiss` "over its cap" lines since mark `pre` (`dismissed`, `dismissed_units`). `nat` prints `cav_max`. `mark pre` resets the trim record. |
| **S7_IRRM** | **A harness bug, not a tool bug and not the block's verb.** The block writes the irruption config with `CFG` → `cx-sec7 cfgset`, which coerced values with `(raw == 'true' and true) or (raw == 'false' and false) or tonumber(raw) or raw` (`chronicler/dfhack/scripts/cx-sec7.lua:920` at a48bbd6). For 'false' the and/or falls through to `raw`, so the STRING 'false' was saved. The tool's sanitizer keeps a boolean key only when the saved value is a boolean (`seasonal-wildlife.lua:9320` at 9e5aabe, `type(dv) == 'boolean' and type(sv) == 'boolean'`) and otherwise keeps the default, which is correct. So every false written through cfgset reverted to its default: the receipt shows `irruption.agitate` true and `need_breach` true while `size_cap` 6 and `enabled` true were written. | **Block:** `CFG` now writes the config with an inline `lua:` chunk (proper true/false/number coercion, prints `eco cfgset written=N`), so it works on any deployed probe and the running sequence picks it up from the next block on. **Probe:** `cfgset` fixed the same way, for after DEPLOY. **Who else used CFG with a false:** S7_NAT v70 (never ran: def aborted first), S7_IRRP2 (started 05:03:58 with the old file, before the fix: arm A's `enabled==false` check fails, and arms B/C lost every `false` silently -- tokens off, pause/zoom/popup off -- so its data is invalid whatever it reports), and S7_IRRR35, S7_IRRTSEQ, S7_F1, S7_PERF1, S7_PERF4 (not started at the fix: they get the inline write). Nothing already completed used CFG. |

## Review of the blocks not yet run (fixed where needed)

| block | finding | change |
|---|---|---|
| S7_IRRTSEQ | If a route left its event active, the next route's `irruption now` would answer "already irrupting". Its `irr alive>0` check would then pass on the old event's subjects, and the residue would be blamed on the wrong route. Every route reviewed does end its event: groups off and disable run `IRRUPT.restoreAll`. This is a guard. | Each event starts with `irruption end <cav>`, which is a no-op when nothing is active. Each route's own `resid` row is taken before it, so a route that leaves an event active still shows it (`active_events`). |
| S7_SCV3W | The POND_GRABBER spawn at `<X+10>` with radius 2 asked for deep water 10 tiles from a spot that only guarantees 30 of its 49 nearest tiles are wet. That spawn would place 0, the automatic spawn check would fail, and the block would abort. | The spawn is at the water spot itself, `<X> <Y>`, with radius 3. |
| S7_PERF4 | `cx-load citizens 60` ran as one `lua:` step. cx-rpc `--lua` has a 15 s deadline, and 60 makeown citizens risk outlasting it (the 6x6 trap in memory fort-load-levers). The cell would then FAIL. | Six `lua:` steps of `citizens 10`. The `cit.n>=60` check is unchanged. |
| S7_EXR1 | `benign.found==1` never proved the dial. | fix_on also checks `benign.castes_benign==0`. `V7.EXTINCT.apply` runs at enable on every world raw carrying the REAL_WORLD_EXTINCT class (this world: rwe=1). Its roles step writes `TAGS.TRIASSIC_EORAPTOR.benign=false` on every caste. fix_off stays the control, with no check. If this assumption is wrong, the block aborts in its first fix_on cell, about 2 min. |
| S7_PAN1 | No change. DEER is not in the embark pool, so the spawn takes a world entry. Panic and cohesion work by raw class (`V7.natural` → `raceEco`), not by pool. `adopt` leads at once (COHT's adopt reply names the leader), so `leader_male==1` at t300 is sound. | none |
| S7_IRRM, S7_IRRP2 | Their timing is sound (but both lost every `false` they wrote: see S7_IRRM above). `IRRUPT.start` places the first wave at once (`IRRUPT.hold`, "the first wave now"), so `alive>0` after 20 t is sound. P2's 0.1-day warning at pinned pressure (`p >= threshold`) starts the event well before its t1200 check. | none |
| S7_IRRR35 | No change; noted for the analysis. `gsize[t1200].groups>0` is also met by adopted native PLUMP_HELMET_MAN groups, so in the quiet arm it does not prove that `call` drew a wave. The tally must count only groups that arrived after t0. | none |
| S7_VF4 | No change; a risk. `vermin[t0].total>0` needs the river's own fish vermin within 12 tiles of `river:shore`. If there are none, the block aborts in its first cell (cheap). The fallback would be cx-eco `vspot`. | none |
| S7_SCV3, S7_VF1, S7_GRD1, S7_EXU1, S7_F1, S7_PERF1, S7_PERF2 | No change. Every config path the blocks read or write exists in 9e5aabe's defaults (checked mechanically over every registered block). Every verb exists. F1's auto-on runs in `enableSched`, so the check right after ENABLE is sound. A 20-call PERF1 bench is about 1 s at the 51 ms per round measured on an earlier fort. Scavengers are chosen by raw flags, not by pool. | none |

## Seen in data that has already run (not edited)

- **S7_COHT** (it was running during this work):
  - `lake:water` resolved to 186,222,55. The tool's `adopt` called the school `water:river`, because `V7.GRP.bodyAt` puts that lake spot by the river. So the "lake substitute" ran in water the tool calls river.
  - In led rep 1, the leader was `gone` (off the map) by t900, with `lost=died`, and the school then panicked.
  - S7_FSH4, S7_GRD1 and S7_SCV3W use the same lake spot.
- **S7_SKL** in this run (reps 1-4, and rep 5 pkg) used the old design: subjects 6 tiles apart and the bonus on. **Do not pool it with the rerun.**

## Rerun commands

Run these after the current sequence ends and the rig is free. They need the rig, so they are not run here.

```sh
cd ~/Claude/Projects/DwarfCron
export SW_TOOL=/Users/nathanielcannon/Claude/Projects/sw-wt/sec7                       # 9e5aabe (moved here)
git -C "$SW_TOOL" log --oneline -1                                                     # expect 9e5aabe
.venv/bin/python scripts/alpha4-sec7.py --only DEPLOY,S7_SKL,S7_NAT,S7_TRIM,S7_IRRM,S7_IRRP2 > data/logs/sec7-rerun1.log 2>&1
#   DEPLOY copies cx-sec7.lua at 0b71fe4 (needed: far spot, rustpushsum, held_open, cav_max, trim dismissed) and the tool
#   S7_SKL 3 arms x 5, S7_NAT 2 x 5, S7_TRIM 1 x 5, S7_IRRM 7 x 5, S7_IRRP2 3 x 5 -> a new data/alpha4-sec7/<stamp>/eco/
#   S7_IRRP2 is on the list even if it finishes in core3: it ran with the false-dropping CFG
```

- **Faster check first (optional):** `--reps 1` on the same line. That takes about 10 min for SKL, about 25 min for NAT (50,055 t per arm at 145 t/s, plus samples and loads) and about 3 min for TRIM.
- **Only S7_NAT's check changed.** Its cells are the same, so NAT can wait until last if rig time is short.
- **Blocks still running in the current sequence** (S7_PAN1 onward) carry the pending-block edits above. They need no rerun unless they abort.
