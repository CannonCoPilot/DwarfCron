# Triage: validate-full 20261002-020031 (RinghatchetsReady, first full run)

Run: v7.1-a4fix `9e5aabe`, validator DwarfCron `b42cc20`, fort RinghatchetsReady (region9, 8x8, 5 biomes, lake+river,
3 caverns, ~120 units). Result 356 PASS, 7 FAIL, 41 NT. Desk-only triage: no rig contact (the section-7 run owns it).

Fix commits:
- tool `v7.1-a4fix`: `dcd169b` (Layers status order), `72b5c25` (ecology pass per-pair cost)
- validator DwarfCron `Dev`: `ca4d53c` (the five probe fixes, `--only mech|v66`)

| # | claim | class | short cause | fix |
|---|---|---|---|---|
| 1 | mech.place | VALIDATOR (fort context) | hard-coded CTRL species | ca4d53c |
| 2 | gui.k.layR | TOOL BUG (display) + VALIDATOR (report) | status row clipped before "rotation on" | dcd169b + ca4d53c |
| 3 | v6.presets | same as 2 | the window was open; the check printed DF's top bar | dcd169b + ca4d53c |
| 4 | mech.model.audit | VALIDATOR (fort context) | the fixture is one world's reading; worldgen creatures differ per world | ca4d53c |
| 5 | mech.hunt | VALIDATOR (fort context) | GIANT PEREGRINE FALCON has the flag in its own raws; the tool rightly leaves it set | ca4d53c |
| 6 | w0.timing.jobs | VALIDATOR (wrong path) + TOOL (real ecology cost) | probe ran off the job's path; the ecology pass really is near or over budget on this fort | ca4d53c + 72b5c25 |
| 7 | mech.v71.cavern.hold | VALIDATOR | the live gate already held species; its release was read as "not back" | ca4d53c |

No tool regression in the model (4), hunting (5) or the cavern gate (7).

## 1. mech.place: VALIDATOR (fort context)

`validate-full.py` (b42cc20) :2463-2466 placed `KANGAROO`, then `GROUNDHOG`. Those are CTRL's species, and
RinghatchetsReady stocks neither: `place: no stocked GROUNDHOG entry on the land layer`. The tool's refusal is correct
(seasonal-wildlife.lua :15739 `place` looks for a stocked Animal entry of that token).
Fix (`ca4d53c`, :2522): the probe now picks from this fort's own `pools()`. It takes a land Animal entry with qty >= 3,
trying KANGAROO and GROUNDHOG first, then the fullest entry. With no such entry the verdict is NOT-TESTABLE, not FAIL.

## 2 and 3. gui.k.layR and v6.presets: TOOL BUG (display) and VALIDATOR (report)

Both claims read the same screen, `screens/C17f-layers-preset.txt`. The window **was** open (rows 3-60 hold the Layers
tab), so #3's "DF's fort screen" is wrong. `v6.presets` printed `tr[:300]`, which is DF's own top bar (rows 0-1).
Row 60, the status line, reads:

    Preset rock desert, temperate freshwater lake, temperate grassland, temperate savanna, temperate shrubland: 161 active, one season each;

The status label is one line high (`gui/seasonal-wildlife.lua:568`, `h=1`). The five-biome preset name filled it, so
"rotation on" and the layer note were cut off at the window's edge. The check needs `"Preset" and "rotation on"`, so it
failed. The ledger side passed: build lines went 50 -> 55 and the last line names the preset. On CTRL (one biome) the
line fit.

- Tool (`dcd169b`, gui :1518 and the first-run line :619): the outcome now comes first and the biome names last:
  `Preset re-applied: N active, one season each; rotation on; <layers>. Biomes: <names>.` This is a real defect for any
  multi-biome fort: the player could not see the outcome.
- Validator (`ca4d53c`, :3134): it reads the status row itself (`srow`) and reports it with re-applied and rotation-on
  flags. `v6.presets` prints that row, not the top bar.

## 4. mech.model.audit: VALIDATOR (fort context); no model regression found

`data/fixtures/species-model.tsv` holds 1054 rows from CTRL's world: 963 non-generated (vanilla) and 91 eco `generated`
(DEMON_n, FORGOTTEN_BEAST_n, NIGHT_CREATURE_n, TITAN_1, `HF103 DIVINE_n`). Each world makes its own generated creatures
under the same token names with different bodies, so a row-for-row compare on region9 is world noise.

The 84 "changed or missing" rows are fixture rows with no identical live row (`gone`). What the evidence shows:
- All 40 rows the result shows (the first 40 of `gone`, sorted) are generated. They run DEMON_10 .. FORGOTTEN_BEAST_7.
  So no vanilla token that sorts before FORGOTTEN_BEAST_8 (A..F, about 40% of the raws) changed.
- The counts fit zero vanilla diffs: 2036 live = 963 vanilla + 1073 generated, and 84 = 91 - 7 (7 CTRL generated rows
  happen to match region9 rows; DEMON_1, DEMON_2, FB_17, FB_20 and FB_21 are visible examples). Also 1066 = 1073 - 7.
- The same counts also fit k changed vanilla rows if k more generated rows matched by chance (`m_after = 2 + k`). That
  is possible only for rows that sort after FORGOTTEN_BEAST_7, where 46 fixture generated rows lie and 44 `gone` rows
  are unseen. The run's results show only the first 40 diffs and the live reading was not saved, so this cannot be
  settled at the desk.

**Verdict:** the evidence points to no vanilla change (no real model regression), but it is not proven for tokens
G..Z. The re-run decides. The audit's columns come from raws only (`MODEL.audit`, seasonal-wildlife.lua :2168), and
phase_model reads clean raws after the LAKE reload, so no world-specific reading of a vanilla raw is expected.

Fix (`ca4d53c`, phase_model :1034-1090): the audit compares token by token, only on tokens that are non-generated in
the reading they come from. A vanilla token that changed, is missing, or is new is a FAIL, printed with both rows.
Generated tokens are counted and listed apart, never judged. The live reading is written to `model-audit-live.tsv` in
the run folder, so any diff can be read in full.

## 5. mech.hunt: VALIDATOR (fort context); no tool bug

`left: 2` is the two castes (male and female) of **GIANT PEREGRINE FALCON**. In vanilla `creature_birds.txt` it has
`[COPY_TAGS_FROM:BIRD_FALCON_PEREGRINE]` with `[APPLY_CREATURE_VARIATION:GIANT]`, and that variation does not remove
`DIVE_HUNTS_VERMIN`. So the giant falcon carries the flag natively, and it is on this fort's roster (Food web screens
C16*). Python over the raws found only two other native carriers: BIRD_FALCON_PEREGRINE (DIVE) and CAT (HUNTS).
PEREGRINE FALCON MAN removes the tag with `CV_REMOVE_TAG`.

The tool behaves as documented. `HUNT.apply` (:11527) writes and records only castes that do not already carry the flag,
and `HUNT.restore` (:11512) clears only what it recorded. Here wrote = restored = 85. The probe (b42cc20 :1990) counted
every flagged caste after `off` and exempted only the token `BIRD_FALCON_PEREGRINE`.

Fix (`ca4d53c`, :2013): before the write, the probe snapshots castes that already carry the flag and that are not in
`CACHE.hunt`. `left` then counts only castes the tool could have written. `left_castes` and `native` are reported.

## 6. w0.timing.jobs: VALIDATOR (wrong path) and TOOL (real ecology cost)

**Validator.** TIMING_LUA (b42cc20 :2081-2100) ran `groupsTick(cfg, g)` and `ecologyRun(cfg, g)` with
`cfg = sw.loadConfig()`, a deep copy. The scheduled job (`groupsJob`/`ecologyJob`) passes `V7.PERF.cfgRO()` (=
`CACHE.cfg`) inside `FUSE.job` (:4003). That wrapper opens one unit census per pass and batches the ledger. The copy
breaks three things:
- `V7.PERF.pool` (P8) memoizes only for `CACHE.cfg`, so every job caller rebuilt the pool. That is
  exhaustCheck, startCoupling, PATTERN.openOnly and trickleApply; the same run timed `buildPool` at 18 ms.
- `V7.PERF.raceEco` (P1) memoizes only for `CACHE.cfg`, so `ecoOf` ran per unit.
- No census was open, so every census reader walked the units again.

The 87 ms groups figure is mostly this artefact. The real job on this fort (alpha 4 round 003228 `perf` table, 138
passes) ran a **26.5 ms mean** groups pass. Its worst pass was 283 ms (`groups:engine` 264, a water draw placing units),
and 14 passes were over budget. The section-7 webload rows show 23-31 ms means, worst 71-72 ms (engine 52-71).

**Tool.** The ecology pass really is near or over budget here: **45.6 ms mean, worst 92, 6 of 16 passes over, 9 MB
of heap per pass** (003228). Profiled from the code: `ecoWrite`'s predator x target loop (b42cc20 :4848-4905) cost
O(P x T) userdata reads per pair:
- `b.id` four times, `b.race` twice (civ_prey and reach), and `b.enemy.enemy_status_slot` twice. Each `.enemy` is a
  fresh userdata.
- `MODEL.reaches`, `raptorTooBig` and `fishers` were re-evaluated per pair.
- `V7.unitSkills(a, {'SNEAK'}, ...)` built a new table and a key string on every pair over the sneak share, though it
  is idempotent per unit.

`V7.sweep` (:4952) read each unit's `.enemy` slot and `rm[sb]` per pair. With 30 predators x 150 targets that is about
4,500 pairs, and about 10 us a pair matches the 45 ms. Map size enters only through unit counts: P x T in the write,
M^2 in the sweep (which is capped at `ECO.SWEEP_MS` 20).

Fix (`72b5c25`, ecoWrite :4797 and V7.sweep :4952). Same pairs, verdicts and counters:
- Each target's id, realm, species entry, domestic flag and slot are read once a pass.
- A slot the pass assigns is written back. This includes a predator that is also a civ_prey target, mapped by
  `T.at[id]`.
- A non-wild target's size is read once, only when a raptor asks.
- The species verdict (reach, raptor mass, fishers) is memoized per predator-species x target-species for the pass.
- The sneak bonus is tried once per predator.
- The sweep precomputes slot, id and each rel_map row once a pass.

Checks: `luac53 -p` passes; luacheck shows 2 fewer warnings than HEAD and no new ones; no new top-level local.
Nothing was measured on the rig.

Validator fix (`ca4d53c`, TIMING_LUA :2066 `J()`, verdict :2175): each job is timed the way FUSE.job runs it (`cfgRO`,
census open, ledger batched and flushed, ecology plus `soloUnits` plus `saveGroups`). The claim also fails when
`FUSE.stats` shows a session **mean** of 50 ms or more for groups or ecology. The worst pass is reported, not judged:
water draws and irruption waves place units, and `JOB_MS` 250 warns on those.

On the budget: the rulings (USER-REVIEW-PART2 R48/R55) approve the perf work but set no embark-size scaling, and the
50 ms is W7's (alpha 1). Per the fail-fast mandate, the budget stays and the fix is to be fast.
Open, not fixed here:
- `groups:engine` worst 71-283 ms (Driver B's water draw placing a school). This is over the 50 ms budget but under
  JOB_MS 250, except for the single 283 ms pass.
- `groups:save` costs 18 ms on every pass (003228 `last`). saveGroups JSON-encodes the whole record each pass; next
  look at what in `g` grows on an 8x8 fort.

## 7. mech.v71.cavern.hold: VALIDATOR; the gate is correct

The probe (b42cc20 :4351-4386) read `pre[t] = cr.frequency` while the **live gate already held 17 species**
(`prior: 17`). For a species the gate owned (`CACHE.capOwn`, a snapshot it wrote itself), `pre` was the held level
`max(2, w//10)`, not the species' weight. The probe then runs:

1. `cavernHold(off)` releases every hold the gate owns and puts the raw back to its snapshot (V7.GRP.cavernHold :10983;
   own and snap give `cr.frequency = snap[t]`).
2. `cavernHold(any)` holds 19 species at the mix level. `bad` is empty, so every level is right.
3. `cavernHold({})` releases them again, back to the weight.

The final check compares against `pre`, the held level, so a species whose held level differs from its weight reads as
"not back". That is the 3 in `diff` (HUNGRY_HEAD, SPIDER_CAVE_GIANT, REACHER). The other prior-held species are the
roster's own holds (out of season, with a roster snapshot), and the check excludes those. The probe was edited for the
mix in b42cc20. Before the mix every hold was at 1, and CTRL's gate never held any species at probe time, so this did
not show there.

Fix (`ca4d53c`, :4421 and :4453): the probe first releases the live gate's holds. It records `prior`, `priorOwn` and
`released` (`token:held->snapshot`). It then takes its baseline after that release and compares against the baseline
snapshot. On the re-run, `released` should list those three species going from their mix level to their weight, and
`diff` should be empty. A non-empty `diff` after that would be a real gate bug. The next groups pass re-holds the live
gate's species.

## Re-run (after the section-7 run; deploy v7.1-a4fix `72b5c25` to the rig first)

`--only` takes one phase per call, not claim ids: `w0 model mech v65 v66 v68 v69 v70 v71 gui`. `ca4d53c` added `mech`
and `v66`, because mech.place and mech.hunt were reachable only in a full run. `--v71 AREA` picks the v7.1 sub-phase.

```
cd ~/Claude/Projects/DwarfCron
SW_TOOL=~/Claude/Projects/sw-wt/a4fix python3 scripts/validate-full.py --fort RinghatchetsReady --only mech --preset      # 1 mech.place
SW_TOOL=~/Claude/Projects/sw-wt/a4fix python3 scripts/validate-full.py --fort RinghatchetsReady --only gui                # 2 gui.k.layR, 3 v6.presets
SW_TOOL=~/Claude/Projects/sw-wt/a4fix python3 scripts/validate-full.py --fort RinghatchetsReady --only model              # 4 mech.model.audit
SW_TOOL=~/Claude/Projects/sw-wt/a4fix python3 scripts/validate-full.py --fort RinghatchetsReady --only v66 --preset       # 5 mech.hunt
SW_TOOL=~/Claude/Projects/sw-wt/a4fix python3 scripts/validate-full.py --fort RinghatchetsReady --only w0 --preset        # 6 w0.timing.jobs
SW_TOOL=~/Claude/Projects/sw-wt/a4fix python3 scripts/validate-full.py --fort RinghatchetsReady --only v71 --v71 groups   # 7 mech.v71.cavern.hold
```

Notes:
- `--only w0` runs right after the load, so `FUSE.stats` holds few passes. For the session-mean half of #6, read a
  full run (or the next alpha round's `perf` table). The ecology figure to compare is 45.6 ms mean, 9 MB a pass
  (003228).
- For #4, read `model-audit-live.tsv` if any vanilla diff appears.
- A full run (`--fort RinghatchetsReady`, no `--only`) covers all seven in one go (this run took 10 minutes).
- All re-run calls passed `--dry-run` against a4fix: luac53 0 failed, 0 unknown engine names, 0 raised.
