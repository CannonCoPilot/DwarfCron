# v7.1 validation r2: triage of run 20261001-224525 (28 FAIL)

Rig: DF v0.53.16 / DFHack 53.16-r2. Tool: sw-wt/val, branch v7.1-val (from bff2726). Validator: dc-wt/val, branch v71-val.
Every run used `SW_TOOL=/Users/nathanielcannon/Claude/Projects/sw-wt/val`.

## Result

| Run | Fort | PASS | FAIL | DEAD | NOT-TESTABLE | BACKLOG |
|---|---|---|---|---|---|---|
| 20261001-224525 (before) | CTRL, full | 315 | 28 | 0 | 60 | 4 (+1 DOC-DRIFT) |
| **20261002-001751** (`data/logs/validate-v71-r2b.log`) | CTRL, full | **357** | **0** | **0** | 47 | 4 |
| **20261002-002611** (`data/logs/validate-v71-r2b-ringhatchets.log`) | RinghatchetsReady, `--only v71 --preset` | **135** | **0** | **0** | 16 | - |

- `rig.json` now records `DFHack 53.16-r2`. Run 224525 recorded `?`.
- Every NOT-TESTABLE-HERE row names a fort or the world condition that would test it.
- On RinghatchetsReady, 8 claims that are NOT-TESTABLE on CTRL pass: bankpair, lead.water, lead.seeded, water.guard.recheck, apex.place, apex.cap, fix.apex_pelagic and curious_reform.
- Both saves are byte-identical to their `.preverify` backups after the runs.
- DF is left at the title screen, with the tool deployed from the val tree.

## The 28 failures

Tool commits are in sw-wt/val and validator commits in dc-wt/val. These are the short hashes; the validator's last tweak (the fisher note) is in the report commit.

| Claim | Cause | Fix | Commit |
|---|---|---|---|
| deploy.v71.files, mech.v71.apex.onecaller | Setup. With no SW_TOOL, the static half read the v7.0 checkout. | Rerun with SW_TOOL: PASS. | - |
| doc.docket (the one DOC-DRIFT) | Setup: the same v7.0 checkout. | PASS with SW_TOOL (Docket r17 says v7.1.0). | - |
| cli.water.now | The claim is out of date. The v7.1 water layer turns itself on wherever there is water (fixes.md §4, R45), so CTRL's 226-tile pool is live and `water now` draws. | The claim now accepts a prompt live answer as well as a dormant one. | 92c3ba2 |
| mech.model.audit | The fixture is out of date: R25/R57 (animal-person own mass) and R24 (extinct fix). | Fixture regenerated. All 288 changed rows are explained: 286 animal people, plus Dimetrodon (land) and Eoraptor (predator). | 92c3ba2 |
| mech.animalperson | The claim is out of date. Since R25/R57, mass and band are the person's own (JAGUAR_MAN 72,500 = (75,000+70,000)/2). | The check now requires the same role and habitat, its own mass, and a band that matches that mass. Eats differences are reported, not judged. | 92c3ba2 |
| mech.v69.armed | The claim is out of date. R47 arms raptors whatever their raws say. | The R47 exception is added. | 92c3ba2 |
| mech.v69.guild | 87.4% agreement. All 113 differences come from rulings: 58 R25 vermin-root people and 54 R24 extinct species, plus NARWHAL MAN. | Species moved by a ruling are set aside. Agreement is 99.8%. | 92c3ba2 |
| mech.v70.civ_hunt | The probe was wrong. BAT_MAN (the only civ race on CTRL) is a predator by R25, so it is armed either way. | The probe uses an armed-guild civ race and reads its copy as prey. | 92c3ba2 |
| mech.v71.skill_profile, mech.v71.raptor_armed | The probe was wrong. 'before' was read after the tool had already applied. The restore path was correct (post = vanilla). | The probe restores first, then reads. | 92c3ba2 |
| mech.v70.realms, mech.v71.realm.table, bl.realm | The expectation was wrong. The table really holds 250 entries (168 curated + 82 extinct merged); "300+" was a guess. | The floor is now derived from the checkout (250). | 92c3ba2 |
| mech.v71.scav_fbsafe | Probe bug: `CASTE_MEGABEAST` is not a creature_raw flag. The engine uses `HAS_ANY_MEGABEAST` / `hasCasteFlag`, so it has no runtime bug. | The probe uses HAS_ANY_MEGABEAST. | 92c3ba2 |
| mech.v71.fix.swimscav_cache, mech.v71.water.guard.recheck | "no JSON": DFHack encodes an empty Lua table as `[]`, and `cr and false or nil` dropped the `false`. | `luap` reads `[]` as `{}` and the probes keep `false`. On RinghatchetsReady this then exposed a tool bug (see the table below). | 92c3ba2, 6a64072, 1eaf544 |
| gui.tab.live, gui.k.liveR | Real tool bug, not a closed window. The window was up; the dump the claim shows is cut at 900 characters. The Groups header sat below Herds & packs, whose rows wrapped ("cluster ?"), so it was pushed under the fold. | The Groups header and per-layer rows now lead the tab. Each row fits on one line, using the raw cluster range. | 03fc38c |
| gui.tab.layers, v6.patterns, v6.caverns, v6.ecology.tab | The claim is out of date. v7.1 renamed "groups at once" to "group cap" (R7, e64f323). | The check accepts "group cap". | 92c3ba2 |
| gui.k.layI | The claim is out of date. The pressures are now space-separated (e64f323). | The regex accepts both forms. | 92c3ba2 |
| web.v71.controls | Real tool bug: `o.value = ok and v or nil` dropped every off switch (20 rows). | Fixed: `if ok then o.value = v end`. | 03fc38c |
| mech.v71.extinct.grazer | The expectation was wrong. Every caste does get GRAZER; the restore puts back vanilla misc.grazer -1, and the check wanted 0. | The restore is judged against the before row. | 92c3ba2 |
| mech.v71.fix.spill | A stale borrow: the season had been removed from `assign` by a roster edit while the record stayed. Also, CTRL's otter was drawn down to 0. | Tool: spillCheck forgets stale borrows. Probe: a forced give-back first. NOT-TESTABLE on CTRL, PASS on RinghatchetsReady. | 03fc38c, 92c3ba2 |
| mech.v71.cavern.hold | Real tool bug: the gate's release freed species the roster held at 1 (out of season), returning them to their own frequency and dropping the snapshot. | The gate releases only the holds it made (`CACHE.capOwn`). | 03fc38c |
| mech.v71.bankpair | CTRL has only a pool, and a pool's banks are a level above its water. | The claim now needs a river or lake: NOT-TESTABLE on CTRL. RinghatchetsReady then showed a tool bug (see the table below). | 92c3ba2 |

## Bugs found while testing RinghatchetsReady and in the full rerun

| Claim | Cause | Fix | Commit |
|---|---|---|---|
| bankpair | Real tool bug: none of 10,593 river and lake tiles has a dry tile at its own level, so bankPair never found a pair and bears never fished. | bankPair now also finds the ramp bank: the floor one level up, over the wall a flooded ramp leans on. | 21d692d |
| lead.water | Real tool bug: `dfhack.units.create` leaves owner_type at PET_MASTER (0). Cohesion only leads NONE or PACK_LEADER units, so no drawn or placed group was ever led. | New units are set to NONE; older ones are treated as free. | 21d692d |
| water.guard.recheck | Real tool bug: r2's getBreathingState read FINE for a pike on dry land two passes running, so the guard never moved it. | A dry tile counts as stranded for an aquatic unit. | e16eef2 |
| ladder.units | Real tool bug: R26's animal-person and giant multipliers were applied after the level split, so carn_units fell to 0.066 against a target of 0.215 in half the builds. | The multipliers now act inside the level: 6 of 6 builds land within 0.03. | 21d692d |
| panic.walk | The probe picked units on walk group 0 (an unrevealed cavern). | The probe takes walkable units. Tool: a blocked flight takes the nearest open heading. | d067cce, 21d692d |
| v6.5–v6.9 claims reading NOT-TESTABLE with `{none: true}` | The LAKE reload drops the tool's site data, so the fort came back with no roster. | The preset is re-applied after phase_model, and the v7 raw probe restores before reading. | 92c3ba2, d9a4d1b |
| cavern.trim (`--only`), mech.v70.leader_male | `[]` JSON and `grp={}` with no race. | luap fix; wetGroup accepts a record with no race. | 92c3ba2, 03fc38c |
| water.mix (r2b-1) | A body with one candidate has balance 1 by construction. | The check weighs the body with the most candidates and judges its most-present candidate; one candidate makes it NOT-TESTABLE. | 6a64072 |

## Coordinator items

- **Versions:** the DF version string contains spaces, so `\S+` never matched. Fixed in d067cce.
- **Steps:** `step()` now runs in chunks of at most 3,000 ticks (d067cce).
- **NOT-TESTABLE notes:** they now name region9 instead of region8, following the user's 1 Oct ruling in cx-config. `FORT_HINT` covers the claims that had no note (54d9184, d9a4d1b).
- **New flag:** `--preset` applies the biome preset after load in `--only` runs (6a64072).

Tool checks: luac53 passes on all four scripts, and luacheck stays at 33 warnings (the baseline).
