# Validator v7.1: the claims, what each checks, which fort

W2:Urist, 1 October 2026. Branch `v71-claims`, a worktree of DwarfCron `Dev`. Built at the desk with no rig: DF was the user's running game, so nothing here has run on DF yet.

**Offline checks run:**
- `python -m py_compile scripts/validate-full.py`;
- `validate-full.py --list`;
- `validate-full.py --dry-run`: every phase, against the v7.1 tip of seasonal-wildlife (`d7cc6f9`). It sends every Lua chunk through `luac53 -p`, checks every engine name against the checkout, and checks every console verb against the dispatcher. The result was clean: 910 stub calls, 339 Lua chunks, 0 syntax failures, 0 unknown engine names, 0 unknown verbs, 0 raises; each of the 149 v7.1 claims recorded exactly once;
- `pytest tests/harness`: 20 harness cases plus 4 new validator cases.

**Sources:**
- the stream notes `docs/v7.1/*.md` in seasonal-wildlife at the `v7.1` tip: roster, groups, ecology, scav, vermin, extinct, water, irruption, fixes, web and perf. Each note lists the claims it needs and the wording it changes;
- the user's rulings, `data/eco-review/part2/USER-REVIEW-PART2.md`: R7, R11, R12, R29, R32, R37, R38, R44, R45 and R62 are quoted below;
- `experiments/HARNESS-v71.md`, for the `phase_v71` stub, the region8 world and the b1 forts.

## 1. How to run it

```sh
scripts/validate-full.py --list v7.1/                    # the v7.1 claim register (id, surface, claimed-as, sub-phase, claim)
SW_TOOL=<v7.1 checkout> scripts/validate-full.py --dry-run --only v71    # offline: luac53, engine names, verbs
scripts/cx-lifecycle.sh deploy-tool <v7.1 checkout>/scripts            # five scripts, each cmp-checked
scripts/validate-full.py                                 # a full run; phase_v71 runs last, after w0
scripts/validate-full.py --only v71 --fort OCEAN2 --v71 water,fixes    # the fort-dependent claims, per fort
```

- **Detecting v7.1.** v7.1 keeps the v7.0.0 changelog header; the lead bumps it at release. The validator therefore cannot tell v7.1 by version alone. `V71` is true when either:
  - the deployed version line reads 7.1 or later; or
  - the deployed engine defines `V7.GRP`, which is new in v7.1.
- **Order.**
  - In a full run, `phase_v71` runs after `phase_w0`. v7.1 places units (apex groups, irruption waves, `place` clusters), and w0's tab timings must not carry them.
  - Inside `phase_v71`, the sub-phases run in this order: deploy, fixes, ecology, groups, water, roster, extinct, vermin, scav, irruption, perf, web.
  - Each sub-phase runs between `cfg_push` and `cfg_pop`. Those snapshot and restore three things: the config, the groups record and the enabled state. If the tool was disabled at the start, `disable` restores the raws.
- **Choosing sub-phases.** `--v71 a,b` runs only the named ones.
- **When a sub-phase raises:** every claim it had not yet recorded is marked FAIL with the exception. A claim the sub-phase never recorded is marked NOT-TESTABLE-HERE.
- **`--only v71`** records every v7.1 claim, so a run on a single fort is complete.

## 2. Conventions every v7.1 claim follows

- **`luap`.** Every probe runs under `pcall`. A Lua error does not come back over RPC: DFHack writes it to stderr.log and the call times out (cx-lifecycle.sh:865). With `luap`, a broken probe reports `{_err}` instead of hanging for 45 s, and its claims are recorded FAIL with the message.
- **Manipulation check (H2 for the validator).** A claim that turns a dial reads the dial back before it judges the effect. It reads the persisted config with `cfgv`, or reads the value inside the probe. If the dial did not take, the claim is FAIL with the note `MANIPFAIL`, and the effect is never read. This guards against a vacuous PASS (memory: manifest-subject-receipt).
- **Fort conditions.** `v71_facts` reads what the loaded fort offers:
  - water bodies, and the deepest ocean column;
  - caverns reached;
  - map size;
  - whether the DFHack build is r2.

  A claim whose condition is missing is NOT-TESTABLE-HERE, and its note names the fort that supplies the condition (section 5).
- **Evidence.** The judged fields go into the record as JSON, together with the probe's reply.

## 3. Existing claims v7.1 changes (updated, not new)

| claim | what changed in v7.1 | the check now |
|---|---|---|
| `cli.status`, `cli.quota`, `gui.tab.live` | the limits line is `limits [map-size formula per layer]:` or `limits [single fixed cap N on every layer]:` (R7) | accepts the bracketed mode |
| `mech.v69.autogroups` | `limits land groups N` sets the single fixed cap N on **every** layer; `groups auto` restores the formula | `land N (map size)`, then `land 4 (fixed)` + `water 4 (fixed)` + `single fixed cap 4`; ends on `limits formula` |
| `mech.water.target`, `mech.quota.land`, `mech.quota.water`, `mech.limits` | water reads `per water body`; groups read `N (fixed)`; caverns read `N (fixed, R44)` | new regexes; restores to `limits formula`, water ceiling 0 (R45), cavern ceiling 0 |
| `mech.ecology.cadence` | default 3,000 (R37) | the cadence is read back (3000) and writes still rise across 3,200 t |
| `mech.ecology.nudge` | off by default (R38) | text only (it was NOT-TESTABLE already) |
| `cli.scavenge` | `scavenging: on` only with the tool enabled too; `now` says `nothing ran: the tool is disabled` (scav §14) | reads the tool state first; expects the matching wording |
| `mech.v70.leader_male` | R32: no adult male means no leader (`grp.unled`), with no fallback to the largest adult | expects the male or nobody |
| `mech.v70.groups_auto_all` / `_water_body` / `_cavern_depth` | `layer_groups` is retired (forced on); caverns hold the fixed cap of 5 (R44) | land = water = `water:ocean` = the formula; cavern = `cavern:1` = `cavern_cap`; one status line with `per water body`, `per cavern` and `(fixed, R44)` |
| `mech.v70.solo_raws` | solitary means `MODEL.cohesionOf == 'solitary'`, through `V7.H.profileOf` (ecology notes) | picks by profile; skips a species already AMBUSHPREDATOR on every caste |
| `mech.v70.fishers_flags` | the default list is the bears, who already swim; RACCOON, TIGER and JAGUAR are off | puts a non-swimming land carnivore on the list for this probe only |
| `mech.v70.pack_sneak` | the unit tag is `:pack:<level>` | matches both forms |
| `cli.v70.v7` | RACCOON is off by default | turns it back off at the end |
| `mech.irruption.arm` | IRRUPT v2 replaced arming | text points at `mech.v71.irr.*` |
| `cli.water` | `target` and `cadence` are retired; layer and spill line added | text only |
| `bl.grouping`, `bl.balance` | shipped in v7.1 (R62) | resolved from `mech.v71.cohesion` and `mech.v71.water.mix` (`SHIPPED_BACKLOG`) |
| `mech.v71.apex.hook` (proposed in the groups notes) | the hook is gone (fixes §5) | not written; `mech.v71.apex.onecaller` instead |

Unchanged and still right on v7.1, checked against the code:
- `cli.irruption`: the status line still opens `irruptions: on  threshold ... cavern 1`;
- `cli.quota.cavern` and `cli.errors`: they still give the retirement notes and usage;
- `mech.v70.scav_mapwide`: `capped at radius` appears only when off;
- `cli.groups.status`;
- `cli.cavern.stock`: still retired.

## 4. Deploy

v7.1 ships a fifth script. `seasonal-wildlife-controls.lua` is the control registry, and `seasonal-wildlife-web.lua` reqscripts it when it loads, so a tree without it serves no page.

**`cx-lifecycle.sh deploy-tool`**:
- still copies the whole tree;
- now also `cmp`-checks each of the tool's scripts in place: engine, `gui/`, web server, web page, and the controls module whenever the web server requires it;
- fails loudly on a missing or different file.

Tested offline against a temporary DF directory: the full tree passes, and a tree that lost `controls.lua` fails.

**Two claims check the deploy on every run:**
- `deploy.v71.files` (host side): the five files are byte-identical to the checkout under test;
- `deploy.v71.loads` (in game): the registry loads with its 12 sections, and so does the web server.

## 5. The v7.1 claims, by stream

There are 149 claims: 140 for v7.1, the seven v7.0 ids the stub reserved, and 2 for deploy. Each sub-phase is `v71_<stream>` in `scripts/validate-full.py`.
The fort column names the condition a claim needs. Where a fort is named, region8 per R11 comes first; the older fort in brackets is the interim stand-in until `b1-forts.py` has embarked the region8 1x1s.

### deploy (this doc, section 4): 2 claims

| claim | what it checks (how) | fort / condition |
|---|---|---|
| `deploy.v71.files` | see section 4 | any fort |
| `deploy.v71.loads` | see section 4 | any fort |

### fixes (docs/v7.1/fixes.md section 5): 11 claims

| claim | what it checks (how) | fort / condition |
|---|---|---|
| `mech.v71.fix.cohesion_override` | `hunters cohesion WOLF herd` / `COUGAR solitary` (read back); cohesionLabel, V7.GRP.cohere on a live WOLF group if one stands (labels and follow distances) and a memberless cougar group; `auto` restores pack | any fort; the live follow distance needs a WOLF group (region8 savage/forest) |
| `mech.v71.fix.swimscav_cache` | SCAV.kind(SHARK_NURSE) before and right after `hunters swimscav SHARK_NURSE off` (read back), no reload | any fort |
| `mech.v71.fix.forager_no_crash` | five wild units marked waiting in CACHE.scav7, VERMIN.forager on each and a forced VERMIN.forageRun under pcall | any fort with wild units on the map |
| `mech.v71.fix.edges_after_build` | `roster build land`, `vermin edges edges` (source read back), VERMIN.edges() label, V7.apply on a copy: an SWV class in a consumer caste's gobble_vermin_class | any fort whose land build seats a vermin consumer |
| `mech.v71.fix.apex_pelagic` | `roster build water`, `roster apex now water`; every new placed water group: pelagic only in the ocean, led or unled; none pelagic without an ocean | a water fort: OCEAN2 / region8 SHORE (pelagic), LAKE (lake-only half) |
| `mech.v71.fix.water_auto` | V7.WAT.autoLayer on a never-set config copy against the map's wet edge and water tiles (ledger line), and on a player-set copy | any fort (CTRL judges the dry half; a region8 water fort the wet half) |
| `mech.v71.fix.water_migrate` | V7.watSanitize on four saved shapes (pure) | any fort |
| `mech.v71.fix.spill` | spill.min raised to 10 in a copy (read back) then V7.WAT.spillCheck: borrowed keys hold the season with stock > 0 and are saved; spillRoll after the stamp moves gives them back; `water spill off` empties the saved borrowed set | a water fort with an active water roster: region8 LAKE (until then LAKE) |
| `mech.v71.fix.ids` | V7.CLI.resolve on HONEY BADGER's underscore, #index and water:#index forms; `odds` for both forms prints the same | any fort |
| `mech.v71.fix.world_switch` | records NOT-TESTABLE-HERE with the shared caches' sizes | a second world loaded in one DF session (two region8 saves) |
| `mech.v71.fix.cavern_max` | `limits cavern ceiling 3` (read back): cavern_max == cavern_cap | any fort |

### ecology (ecology.md): 11 claims

| claim | what it checks (how) | fort / condition |
|---|---|---|
| `mech.v71.cadence_default` | defaultConfig() cadence 3000 / nudge false; V7.sanitizeHunters on pre-v7.1 copies (1500 -> 3000, nudge -> off, 2000 kept, a v7.1 config untouched) | any fort |
| `mech.v71.fish_bears_default` | defaultConfig().v7: fishers on, every true fisher_list token contains BEAR | any fort |
| `mech.v71.skill_profile` | V7.apply on an enabled config copy; min caste SNEAK (V7.H.casteSkill) of a solitary and a pack species before / after / after V7.restore() | a fort with both a solitary and a pack hunter in the embark: region8 B1-R8-*-SAVAGE (one alone: NOT-TESTABLE-HERE) |
| `mech.v71.skill_units` | places one packaged hunter (`place TOKEN 1`) before the raws; its soul's SNEAK rating, natural floor and nominal level before / after / after restore | a fort with a stocked land hunter (region8 savage); CTRL often has none |
| `mech.v71.packs_inferred` | V7.H.packSizes on fake WOLF and COUGAR hunters (no unit touched): two wolves 5 tiles apart in no group are a pack of 2; two cougars, two wolves 30 tiles apart, and pack off give none | any fort (vanilla raws) |
| `mech.v71.readback` | V7.H.readback() after the apply: casteOk == castes on every row | any fort with an armed predator in the embark |
| `mech.v71.raptor_armed` | BENIGN caste count of BIRD_EAGLE (else the first RP species) before / after V7.apply / after restore; ecoArmed(entry) | a fort with a raptor in the embark (region8 forest/mountain) |
| `mech.v71.raptor_cap` | V7.H.raptorTooBig with the eagle's model mass against DEER and RABBIT masses (pure) | any fort |
| `mech.v71.cohesion` | MODEL.cohesionOf for COUGAR/WOLF/FISH_PIKE/BIRD_RAVEN against their raw cluster; `hunters cohesion WOLF herd` (dial read back) then `auto` | any fort |
| `mech.v71.swimscav` | MODEL.swimScavenger on six tokens with swim_scav on and on a copy with it off (pure) | any fort |
| `mech.v71.bankpair` | V7.H.bankPair from surveyed water tiles; flow of G and W by getTileFlags, same z, adjacent | a fort with a river or lake: region8 RIVER/LAKE (until then RIVER4, LAKE) |
| `mech.v70.solo_skill` | a second `place` of the solitary species while the caste write holds; the new unit's soul SNEAK >= profile | a stocked solitary land hunter: region8 savage |

### groups (groups.md; R7, R31, R32, R35, R44, R45): 24 claims

| claim | what it checks (how) | fort / condition |
|---|---|---|
| `mech.v71.limits.formula` | groupsFor land, water:ocean/lake/river = QUOTA.autoGroups(); every cavern = groups.cavern_cap; default mode formula, cap 5 (in-memory config) | any fort |
| `mech.v71.limits.fixed` | `limits fixed 2` (manip: limits.mode/fixed read back), groupsFor land/ocean/pool 2, cavern 2, QUOTA.status says 'single fixed cap 2'; `limits formula` back to the sqrt rule | any fort |
| `mech.v71.layer_groups.retired` | a raw config with v7.layer_groups=false through the tool's own loader (site data written, read, put back) loads true; `v7 layer_groups off` prints 'retired' and the value stays true | any fort |
| `mech.v71.migrate` | a v7.0 raw config through the loader: land auto=false/4 -> mode fixed 4, water ceiling 12 -> 0, seasons_own true, cavern cap/max 5; an auto land with ceiling 30 -> formula, 30 kept | any fort |
| `mech.v71.clock.state` | V7.GRP.releaseGap on a synthetic record (fixed cap 5): last = now, target in [cap-band, cap], due = last + gap | any fort |
| `mech.v71.clock.forward` | dueTick with 2 groups < with 3; adaptive off -> nil | any fort |
| `mech.v71.clock.pause` | dueTick nil at the cap; layerRows' land row (fixed cap 1, one record) says 'paused at the cap' | any fort |
| `mech.v71.cavern.count` | adoptNatives on a copy of the groups record: native cavern records at depth 0-2, the cavern row shows '(N native)' | cavern natives on the map (region8 fort with cavern entries) |
| `mech.v71.cavern.hold` | cavernHold with hold off (none) then any (cavern at cap): held species at frequency 1, none 0/deep/shared; released -> every frequency back; CACHE.capHeld empty | cavern entries on the region tiles |
| `mech.v71.cavern.trim` | cap 1 + a dummy record: trimOne sends the oldest native group off (countdowns <= 10, g.trim_undo), PATTERN.sizeRestore (disable path) puts them back | cavern natives on the map |
| `mech.v71.cavern.deep` | no deep unit in any record; no deep species in capHeld/apcap; adopt refuses a deep unit (R60 reason) | any fort; the adopt half needs magma-sea life (MAGMA) |
| `mech.v71.water.cap` | water:ocean/lake/river/pool = autoGroups; default ceiling 0; `water` quotes 'N group(s) at once per water body' = autoGroups (manip: limits formula) | any fort |
| `mech.v71.lead.male` | V7.leaderOf on live groups (and citizens as stand-ins): the largest adult male; an all-female set -> nil, unled 'no adult male' | any fort with citizens |
| `mech.v71.lead.lost` | synthetic record over 2+ live herd/pack animals with a leader that left (and a dead unit's id for 'died'): leader_lost, panic, nobody following, ledger 'panic for'; panic expired -> 'panic is over', still unled | 2+ wild herd/pack animals on the map |
| `mech.v71.panic.walk` | the same panic: members within panic_tiles have goal SeekStation and a path; moves > 0 | as above |
| `mech.v71.lead.water` | `water layer on`, `water now`: the drawn group's leader stands in water, members follow at follow_school/pod (or unled 'no wet adult male') | water: region8 SHORE/LAKE/RIVER; until then LAKE/RIVER4/OCEAN2/BOATS |
| `mech.v71.lead.place` | `place TOKEN 6` (ORCA on an ocean fort, else the best-stocked land herd): one record, spread <= 12 tiles, led by an adult male or unled 'no adult male' | any fort with a stocked herd entry |
| `mech.v71.lead.seeded` | ENGINE.count skips a synthetic seeded record; live: adoptNatives' seeded schools are seeded=true and uncounted | live half: a water fort with DF-seeded schools |
| `mech.v71.lead.sponge` | cohesionLabel(SPONGE) and of an IMMOBILE race = solitary; no led record of either | any fort |
| `mech.v71.adopt` | `groups adopt` 2-3 live wild units of one species: one record holding exactly them (adopted=true), each id once, led or unled by R32; a citizen refused | 2+ wild animals of one species |
| `mech.v71.apcap` | V7.GRP.apCap (in-memory config enabled, apcap 5): a *_MAN cavern species capped; IRRUPT.activeOn stubbed true -> raw range back; capped again; PATTERN.sizeRestore restores | a cavern animal-people species with cluster > 5 (plump helmet men) |
| `mech.v71.restore` | cavern hold + apcap, then PANEL.restoreAll (all off) and `disable`: every frequency and cluster range back, capHeld/apcap empty | cavern entries |
| `mech.v71.apex.onecaller` | ROSTER.apex.tick nil, ROSTER.placeTick a function; static: no apex.tick call in the engine's code, tick() pcalls ROSTER.placeTick | any fort (static half needs $SW_TOOL) |
| `mech.v70.gate_drain` | three live land units as flagged one-animal gated records: V7.drainGate releases the two oldest, stops at one flagged; flags put back; default on; two call sites | 3 wild land animals on the map |

### water (water.md; R14, R22, R45, R62): 13 claims

| claim | what it checks (how) | fort / condition |
|---|---|---|
| `mech.v71.water.survey.levels` | `ENGINE.waterTiles(true)` + `deepColumns(cfg,true)`: ocean histogram has columns at 3-4, `n > 0`, `zReached` below the top ocean level, not stopped; `water depth` prints the ocean row | BOATS (deep ocean columns); region8 SHORE if its `water depth` shows 3+ |
| `mech.v71.water.survey.ocean2` | the same survey: ocean histogram only 1 and 2, max 2 | OCEAN2 only (the claim is its measured ocean) |
| `mech.v71.water.survey.contig` | `water budget 1900` (read back), `water depth full`, then stride-2 vs stride-1 histograms: every bucket of 25+ columns x4 within 10% | any water fort (LAKE, RIVER4, OCEAN2) |
| `mech.v71.water.column_levels` | `V7.watSanitize` on `{deep_levels=2}` -> 2, `{deep_levels=2,column_levels=4}` -> 4, default 3; `water levels 2` (read back) -> `deepColumns().need == 2` | any fort |
| `mech.v71.water.landaq` | `water aquatic on/off` (each read back); ocean candidates hold keys without `water:` when on, none when off, no token twice | ocean: OCEAN2 / region8 SHORE |
| `mech.v71.water.mix` | `water mix on` (read back), `water now BODY`, `water mix BODY`; candidates' weights sum > 0; the census's most-present species shows `balance < 1` | any water fort |
| `mech.v71.water.apexlimit` | `water mix apex 1` (read back); `V7.WAT.mix` on a curated apex + an aquatic prey with a synthetic census holding 1 then 0 apex groups: apex 0 then > 0, prey > 0; lamprey level C, off the apex list | any fort |
| `mech.v71.water.pull` | pull/lift/seek read back on; a small ocean prey drawn (`ENGINE.draw` only=prey); roster predators and the curated apexes weighed against the census: `pull >= pull.min`; a lifted pelagic's base == FREQUENCY | ocean: OCEAN2 / region8 SHORE |
| `mech.v71.water.seed` | after the prey draw, a roster predator of it drawn: `grp.pulled == 'prey'`, ledger 'seeded by its prey', members wet, within seek_radius+6 of a prey unit, column depth >= deepest sampled near the prey - 1 | ocean with an in-season roster predator of the prey |
| `mech.v71.water.guard.recheck` | guard/recheck read back on; `water` says 'via getBreathingState'; an aquatic fish drawn, teleported to dry ground, guard pass x2 (20 t apart): back on water, ledger `strand ... moved` | water fort on DFHack r2 |
| `mech.v71.water.retry` | `V7.waterTick` on a cloned groups record with `cfg.allow = {}` (manip: every body says nothing drawable): each body's next draw <= retry_days x 1200 | any water fort |
| `mech.v71.water.fisher` | candidates of every body hold no BEAR_*; the three vanilla bears are `fisher` on the apex list | any water fort |
| `mech.v71.water.nodeep` | no `cavern:`/`deep:` key among candidates; every census position inside the surface band | any water fort |

### roster (roster.md; R13, R25, R26, R34, R36, R41, R43, R49, R50, R59, R61): 15 claims

| claim | what it checks (how) | fort / condition |
|---|---|---|
| `mech.v70.builder` | `roster build land` (console): slot lines, an UNFILLED line with a reason for each slot under its minimum, the ladder, the vegetation survey line; the water build's deep survey rides on mech.v71.water.pelagic's probe | any fort (CTRL) |
| `mech.v70.outgun` | `roster outgun land` run inside the game: the survey line, every factor >= v7 outgun, CACHE.ver unmoved (read-only); an in-memory build with outgun_cap on writes a group size for each outgunned prey | any fort; the cap half needs an outgunned pair in the land pool |
| `mech.v70.realms` | V7.REALMS has 300+ entries; V7.realmOk with realms on: own realm in, another out, an unlisted token in; realms off: all in | any fort |
| `mech.v71.ladder.units` | the same `roster build land` reply: ladder-info carn_units within 0.03 of carn, every ladder value >= 1, no apex FREQUENCY above apex_raw_cap (apex_odds 0) | any fort |
| `mech.v71.apex.place` | after the build: the apex keys' stock read; `roster apex now land`; stock debited by the group size and a placed tag='apex' record in g.groups | a land apex in the embark pool with stock: a region8 savage fort; interim a savage fort |
| `mech.v71.apex.cap` | ROSTER.apex.decide (cap 1, target 25, not forced) on a scratch state key with the placed group on the map: why == 'cap 1 reached' | as apex.place |
| `mech.v71.flying` | in-memory `ROSTER.build(c, 'flying')`: RP have <= 1, APX members none of vulture/buzzard/kea/raven, APX filled | a surface raptor >= 2,000 cm3 in the pool (region8 forest/lake fort); NOT-TESTABLE when APX is empty |
| `mech.v71.water.pelagic` | in-memory water build: APE and PE seated or UNFILLED 'no candidate in pool'; MODEL.entry(FISH_LAMPREY_SEA) slots MW | ocean: region8 SHORE; interim OCEAN2/BOATS (the lamprey half runs anywhere) |
| `mech.v71.civ` | V7.isCivRaw on ANT_MAN, BAT_MAN, WOLF_MAN; every pool entry a civ boolean | any fort |
| `mech.v71.apmass` | classify(DAMSELFLY_MAN): mass >= 30,000, guild RP | any fort |
| `mech.v71.freqfloor` | V7.restore, list in-embark AP at raw FREQUENCY 0, V7.apply (enabled in memory): each >= floor; V7.restore: 0 | an embark with a bear/cat/dog man (19 in vanilla at 0) |
| `mech.v71.place.deep` | race count, `place MAGMA_CRAB 1 deep`, race count: a refusal naming R28/R60, no new unit | a stocked MAGMA_CRAB entry (MAGMA fort, or any region8 fort with a magma sea entry) |
| `mech.v71.invasive` | ROSTER.savage false; addNewSpecies(CENOZOIC_SMILODON) saved; smilodon units +>= 1; `roster apex` lists 'invasive CENOZOIC_SMILODON' | calm map whose biome the smilodon allows: CTRL / region8 CALM |
| `mech.v71.realm.table` | `realm table`: head missing_from_raws=0, entries == realm-entry lines >= 300 | any fort (vanilla raws) |
| `mech.v71.gobble` | `roster gobble land` after the build: >= 1 kind=write; each native edge's class in the consumer's classify().gobble and the vermin's cclass | any fort with allowed vermin |

### extinct (extinct.md; R24): 12 claims

| claim | what it checks (how) | fort / condition |
|---|---|---|
| `mech.v71.extinct.class` | count of raws with REAL_WORLD_EXTINCT == 200; every TAGS token in the raws has it; `extinct list` has no 'no REAL_WORLD_EXTINCT class' row | any fort (vanilla raws) |
| `mech.v71.extinct.freq` | snapshot of every TAGS raw before / after V7.apply (enabled in memory) / after V7.restore: T. rex 2, Quetzalcoatlus 5, Titanoboa 3, Mosasaurus 50; restored 50/100/30/50 | any fort |
| `mech.v71.extinct.grazer` | same snapshot: TRICERATOPS GRAZER all castes, misc.grazer 150, HAS_ANY_GRAZER, guild GZ; restored; MOA unchanged | any fort |
| `mech.v71.extinct.roles` | same snapshot + classify: EORAPTOR, TIKTAALIK, TITANOBOA flags and guilds; DIMETRODON land/AL and ROSTER.inPart(land) | any fort |
| `mech.v71.extinct.model_off` | `extinct off` (manip: extinct.fix false), classify TRICERATOPS PL and EORAPTOR prey, raws vanilla; `extinct on` after | any fort |
| `mech.v71.extinct.restore` | every TAGS raw field equal before the write and after V7.restore (manip: the apply changed >= 1 field) | any fort |
| `mech.v71.extinct.cavsnap` | T. rex held by hand (CAVERN.write 1; manip: raw 1), apply: snapshot 2 raw 1; both restore orders end at 50 | any fort |
| `mech.v71.extinct.standdown` | T. rex FREQUENCY 7 by hand (manip), apply: stays 7, rowLine 'stood down ... raw 7'; restore: 7; put back | any fort |
| `mech.v71.extinct.realm` | realmSync with realms off/on/off: rows added == TAGS realm rows absent from the base table (>= 80), T. rex NEA on, gone off; a user json entry survives | any fort; the json half only where dfhack-config/seasonal-wildlife-realms.json exists |
| `mech.v71.extinct.units` | wild/tame units of corrected extinct species: flags into the unit cache on apply, back on restore; tame untouched | wild extinct fauna on the map: a region8 fort with them (none known on the older forts) |
| `mech.v71.extinct.mods` | `extinct mods`: 'attack mods active: 0' and the five AP_LOST names | the vanilla rig |
| `mech.v71.extinct.ladder` | apply, then up to four in-memory land builds until an extinct apex is seated: ladder_info.apex reads 'raw <min(corrected, cap)>' | an extinct land apex in the embark pool (region8 fort) |

### vermin (vermin.md; R20, R21, R27, R51): 10 claims

| claim | what it checks (how) | fort / condition |
|---|---|---|
| `mech.v70.gobble` | V7.restore, apply (enabled in memory): CACHE.gobble tagged > 0 and consumers > 0; every member's castes carry its SWV class; gobbleStatus 'vermin gobble: on' | any fort with allowed vermin |
| `mech.v71.vrm.swv_split` | VERMIN.allClasses: SWV_COLONY and SWV_BAT filled (bats fly), no VERMIN_SOIL_COLONY raw in SWV_SOIL; `vermin classes` lists both | any fort (world raws) |
| `mech.v71.vrm.edges_src` | `vermin edges` names the source and table; apply under source edges, then rules: each in-embark consumer's caste-0 SWV gobble classes == VERMIN.gobbleWants | any fort |
| `mech.v71.vrm.class_off` | `vermin class SWV_HERP off` (manip), apply: 0 SWV_HERP strings; `on` (manip), apply: > 0 | a herp among the map's vermin for the 'on' half (region8 LAKE/RIVER; interim LAKE) |
| `mech.v71.vrm.restore` | apply: SWV strings > 0 (manip); V7.restore: 0 in every caste's creature_class and gobble vectors | any fort |
| `mech.v71.vrm.vector` | VERMIN.index: a source, objs = loose + colonies, loose amount == an independent count leaving colonies out; `vermin census` has no 'NO VERMIN VECTOR' | vermin on the map (any fort outside deep winter) |
| `mech.v71.vrm.forage_run` | `vermin forage now`: 'N eater(s) drawn now', 'last pass' with a source; every pending forager wild/untamed/natural/not deep with u.path.dest on its line | any fort; the per-forager half needs wild vermin eaters near vermin |
| `mech.v71.vrm.forage_off` | `vermin forage off` (manip): pending 0, PANEL.jobs foraging off, not scheduled, released walks cleared; `on` after | any fort |
| `mech.v71.vrm.cfg` | a bad vermin_eat block saved to site data and read by loadConfig (the original put back in the same probe): numbers and source at defaults, SWV_HERP false kept, the rest on | any fort |
| `mech.v71.vrm.perf` | tool and foraging on (manip), FUSE.stats for the forage job reset, 3,000 ticks: worst < 50 ms | region8 per the notes; runs on any fort |

### scav (scav.md; R16, R17, R18, R30, R42): 12 claims

| claim | what it checks (how) | fort / condition |
|---|---|---|
| `mech.v71.scav_status_fresh` | `scavenge on` (read back), `scavenge now`, then `scavenge`: last pass age <= 50 t and it ran | any fort (tool enabled by the sub-phase) |
| `mech.v71.scav_shared_state` | CACHE.scav7 after the pass; fallbacks in the console status equal a reqscript copy's SCAV.status | any fort |
| `mech.v71.scav_swimmer` | SCAV.is on six tokens, then `scavenge swimmers off` (read back): every swim-kind one false | any fort |
| `mech.v71.scav_keys` | `scavenge set hop_tiles 99` refused, `6` saved (read back), listed by `scavenge keys`, kept with CACHE.cfg dropped | any fort |
| `mech.v71.scav_discovery` | SCAV.newRemains on a DEER: default delay >= discover_min_h; every delay key 0 (incl. discover_min_h): found at once | any fort; the live corpse half is rig test SCV |
| `mech.v71.scav_attribution` | SCAV.stats().pairs and the eco ledger's 'eaten --' lines | a fort where a remains was finished (rig test SCV, region8 savage) |
| `mech.v71.scav_fbsafe` | SCAV.naturalRemains on a demon/FB/titan/megabeast race and on DEER; no non-natural unit among the pass's walkers | any generated world |
| `mech.v71.scav_off_cancels` | repeat-util isScheduled for scavenge and curious after enable (read back), then after disable | any fort |
| `cli.curious_reform` | `curious reform off/on/now`, `loot keep/drop`, `set stay_min 25000` (read back) and `50` (refused) | any fort |
| `mech.v71.curious_reform` | places a stocked curious thief, zeroes its countdown, one CURIOUS.pass: record, bits clear, countdown in range, ledger; after `disable` bits as before and countdown 0 | a fort with a stocked curious beast (raccoon): region8 temperate forest, or BOATS |
| `mech.v71.panel_curious` | PANEL.SWITCHES has curiousreform; PANEL.allOff on a copy turns it off (saved Panel record put back) | any fort |
| `mech.v70.scav_ext` | v7.scav_ext default; SCAV.mover on four tokens; SCAV.suits/inReach on wet and dry remains; the fallbacks counter in the status | any fort; the live landings are rig test SCV/SCVW |

### irruption (irruption.md; R4, R5, R6, R10, R35, R60): 15 claims

| claim | what it checks (how) | fort / condition |
|---|---|---|
| `mech.v71.irr.cfg` | IRRUPT.defaults rev 2 with every key of section 6; IRRUPT.sanitize on a v7.0 table and on bad values | any fort |
| `mech.v71.irr.migrate` | IRRUPT.migrate on a synthetic v7.0 record: armed stood down (flag cleared), cooldowns spread | any fort |
| `mech.v71.irr.trigger` | pin the chosen cavern at the threshold, IRRUPT.tick -> warning (ledger 'something stirs'), warn_until passed, tick -> active with wave 1 ('IRRUPTS'), others idle; fallback none on a no-civ cavern -> idle + retry | a cavern band with a civ race or predator entry (manip: irruption on, need_breach off, size 2/4/6 read back) |
| `mech.v71.irr.layer` | synthetic state, cavern 1 active: activeOn and gapDays per cavern | any fort |
| `mech.v71.irr.wave` | wave 1 size = clamp(clusterMax x 2, 4, 6) bounded by stock; one marked record, led; stock debited by n | as trigger |
| `mech.v71.irr.tokens` | per-token unit counts vs pct, one champion, every write read back on the unit | a cavern with a civ race (BOATS/OCEAN2; region8) |
| `mech.v71.irr.caste` | caste snapshot of every candidate race before/after; casteHeld nil | as trigger |
| `mech.v71.irr.agitate` | ev.agit members all non-civ, non-fort, natural, this cavern; <= cap; no new agitation outside the list | as trigger; full effect needs other animals in that cavern |
| `mech.v71.irr.end` | `irruption end N` and a forced event run past its duration: 0 residual writes, countdowns per end_mode leave, cooldown, pressure 0, marks cleared; cooldown -> idle | as trigger |
| `mech.v71.irr.off` | an event under each of `irruption off`, `disable`, `groups off`, PANEL.restoreAll: 0 residual, no active phase; while off a pinned cavern places nothing | as trigger |
| `mech.v71.irr.fbsafe` | candidates natural at their own depth; agitable false for non-natural units; placed units in a cavern | any fort; placed half as trigger |
| `mech.v71.irr.msg` | IRRUPT.say stubbed in the probe's copy: warn/start/wave/finish/ready/lapse each called; all msg off -> say false; pause.start pauses (state put back) | as trigger |
| `mech.v71.irr.status` | `irruption status` rows and the one-liner in `status` | any fort |
| `mech.v71.irr.r35` | during event 1 apCap leaves the cavern's *_MAN species at its raw range; after the end it is capped; cap off restores | a *_MAN species in the irrupting cavern |
| `gui.irr.rows` | static: the window names the IRRUPT v2 keys | NOT-TESTABLE-HERE until the UI wave lands |

### perf (perf.md; R48, R55): 15 claims

| claim | what it checks (how) | fort / condition |
|---|---|---|
| `perf.p0.kb` | `perf reset`, `enable` (read back), 3,200 t: groups job kb >= 0, worst tick >= its worst pass | any fort |
| `perf.p0.verb` | `perf` prints the switch line, the job table and the counters (or 'not in this build') | any fort |
| `perf.p1.memo` | raceEco == ecoOf for every race on the map; CACHE.ecoClass filled; V7.natural the same with `perf legacy class on` (read back) | any fort |
| `perf.p2.groups` | loadGroups twice the same table; the saved compact record round-trips #groups with no `stuck` key (persist_transient off, read back) | any fort |
| `perf.p2.undo` | UNDO.push/pop on the held CACHE.undo ring: depth +1, label back | any fort |
| `perf.p3.overlay` | overlayData twice the same table; markers == groups with a live member | any fort |
| `perf.p4.census` | countByLayer inside a fake pass == the units.active loop; discoverGroups ids equal with `perf legacy census on` (read back) | any fort |
| `perf.p5.phases` | every Panel job that is on is scheduled at once after `enable`; shared ticks 0 or deferrals > 0 over 3,200 t | any fort |
| `perf.p6.live` | per layer, the managed-index biomass sum == the full population walk (headless form of the Live tab) | any fort |
| `perf.p7.ro` | groupsTick on cfgRO: CACHE.cfg identity/ver unchanged when no writer is due; CAVERN.apply twice: the second saves nothing (saveSiteData counted) | any fort |
| `perf.p8.pool` | V7.PERF.pool twice the same, hits +1; rebuilt after saveConfig | any fort |
| `perf.p9.native` | CAVE/WET survey counts identical with `perf legacy survey on` (read back); on r2 grass share within 3 and PLACE.tiles' first level equal | any fort; the native half needs DFHack r2 |
| `perf.p10.slice` | after `enable` + 3,200 t: sliceLog.warm n >= 1 no error, four surveys cached; `perf build land` + 200 t: sliceLog.build no error | any fort |
| `perf.p11.events` | `perf census` says 'the wild-id set'; every live wild unit is in the set; arrivals during the run counted | any fort (arrivals: a fort with surface waves) |
| `perf.p12.scav` | edible natural remains counted equal with `perf legacy scav on/off`; webCensus.wild == countByLayer | a fort with corpses on the map |

### web (web.md; R54): 8 claims

| claim | what it checks (how) | fort / condition |
|---|---|---|
| `web.v71.controls` | GET /controls.json: 200, >= 12 sections, >= 300 controls, every available non-{T} row has `value` | any fort |
| `web.v71.set` | POST /set hunters.stoop.chance 61 -> 200, value 61, config 61 (read back), ledger count +1; 101 -> 400 'at most 100'; unknown id -> 400 | any fort |
| `web.v71.set_panel` | POST /set switch.nudge on -> 200 via 'Panel: Nudge', ecology.nudge true (read back), undo depth +1; off -> false | any fort |
| `web.v71.status` | GET /status.json: 200, every section without `error`, groupmap.layers[0].key == 'land' | any fort |
| `web.v71.cluster` | /state.json species vs the raws' cluster_number: gmin < gmax, gmax == [0] for every two-number species | any fort |
| `web.v71.guard` | /act roster_build arg=everything 400; /set GET 405; bad token 403 (set, controls.json); /cmd groups adopt 400 | any fort |
| `web.v71.perf` | two snapshot builds 2.3 s apart after the first: snap_ms < 50 each (`_G.SW_WEB.stats`) | any fort |
| `web.v71.stop` | `seasonal-wildlife-web stop`, then GET / gets no answer | any fort |

## 6. Which fort each claim needs (R11, region8)

**Most claims run on any loaded fort, CTRL included.** They are pure engine probes over:
- defaults, migrations and sanitisers;
- classification and the model;
- verbs with their read-back;
- raw writes and their restores;
- the web endpoints.

**The rest need a condition on the map.** `v71_facts` reads each condition at the start of `phase_v71`. A claim whose condition is missing is recorded NOT-TESTABLE-HERE, and its note names the fort. The 1x1 forts come from `b1-forts.py embark --only NEED`, on region8 "The Last Planets" (HARNESS-v71 section 5). Until they exist, the older fort in brackets stands in.

| condition | region8 fort (R11) | until then | claims that need it |
|---|---|---|---|
| ocean, shallow (max column 2) | B1-R8-*-SHORE whose `water depth` shows max 2 | OCEAN2 | `water.survey.ocean2`, `water.landaq`, `water.pull`, `water.seed`, `fix.apex_pelagic` (ocean half), `roster water.pelagic` |
| ocean, deep columns (3+) | B1-R8-*-SHORE whose `water depth` shows 3+ | BOATS | `water.survey.levels` |
| any surface water | SHORE / LAKE / RIVER | LAKE, RIVER4 | `water.survey.contig`, `water.mix`, `water.retry`, `water.fisher`, `water.nodeep`, `fix.spill`, `fix.water_auto` (wet half), `bankpair`, `lead.water`, `lead.seeded` (live half) |
| water and DFHack r2 | any wet region8 fort on r2 | LAKE on r2 | `water.guard.recheck`; the native half of `perf.p9.native` |
| a dry map | an interior 1x1 with no water in `facts` | CTRL | `fix.water_auto` (dry half) |
| populated caverns, reached | a region8 fort after a breach (dig-now and an aquifer seal; memory fort-load-levers) | BOATS or OCEAN2 (cavern civ races seen there) | `cavern.count`, `cavern.trim`, `apcap`, `irr.r35`, `irr.tokens` (civ wave) |
| stocked hunters and raptors in the embark | B1-R8-*-SAVAGE, forest or mountain | none reliable | `skill_profile`, `skill_units`, `solo_skill`, `raptor_armed`, `apex.place`, `apex.cap`, `flying` (only when CTRL lacks them) |
| a stocked curious thief (raccoon, monkey) | a region8 forest fort | BOATS | `mech.v71.curious_reform` |
| extinct animals in the embark | a region8 fort whose embark lists one (the extinct status line counts them) | none | `extinct.units`, `extinct.ladder` |
| a calm map (savagery under 33) | B1-R8-*-CALM | CTRL | `mech.v71.invasive` |
| a second world in the same DF session | load region8, go to the title, load another world | — | `fix.world_switch`: only its one-world half is judged |

**Running the whole programme.** When the region8 forts exist, it takes one full run and one `--only v71` run per fort:

```sh
scripts/validate-full.py --fort B1-R8-<CODE>-<rx>_<ry>-CALM                  # the full run (region8 CALM; CTRL until then)
for f in SHORE LAKE RIVER SAVAGE; do
  scripts/validate-full.py --fort B1-R8-<...>-$f --only v71 --v71 fixes,ecology,groups,water,roster,irruption,scav
done
```

Each per-fort run records every v7.1 claim. A claim takes the verdict from the fort that supplies its condition.

## 7. NOT-TESTABLE-HERE

### By design on CTRL

CTRL is dry, calm, and its caverns are never opened. On CTRL these claims stay NOT-TESTABLE-HERE (each names its fort in section 6):
- **water:** every claim except `water.column_levels` and `water.apexlimit` (both run on any fort);
- **cavern natives:** `cavern.count`, `cavern.trim`; also `apcap` and `irr.r35` unless a `*_MAN` cavern species is stocked;
- **irruption:** `irr.tokens` needs a civ race in a cavern;
- **ecology and scav, needing animals on the map:**
  - `skill_profile`, `skill_units`, `solo_skill` and `raptor_armed` need a hunter or raptor in the embark;
  - `curious_reform` needs a thief;
  - `bankpair` needs water;
- **extinct:** `extinct.units`, `extinct.ladder`;
- **roster:**
  - `water.pelagic` needs an ocean;
  - `place.deep` needs a stocked magma crab (the MAGMA fort);
  - `freqfloor` needs a bear, cat or dog man on the embark.

### On any fort, in one session

- **`mech.v71.fix.world_switch`** needs a second world loaded in the same DF process. Only this session's half is judged (the shared caches exist and are filled).
- **`mech.v71.scav_attribution`** needs a carcass eaten to the end. That is rig test SCV in scav.md section 15; an advance of a few thousand ticks rarely finishes one.
- **`mech.v71.irr.end`, the "repelled" end reason**, needs the fort to kill the wave's units. The other end reasons are judged; this one is left to a rig test.
- **`gui.irr.rows`** waits for the UI wave. The GUI still has the v7.0 irruption rows (next section).
- **`perf.p5.phases`, the 6,000-tick watch for two heavy jobs on one tick:** only the scheduling half is judged headless.
- **`perf.p6.live`:** the Live tab's biomass rows are read through the engine functions the tab calls, not off the screen.

## 8. Where the v7.1 code and its notes disagree (likely FAIL on the rig)

The builders found these while checking every probe against the code. Each claim is written to the notes' intent; where a note's recipe cannot work, the check says so in its record.

1. **`mech.v71.scav_discovery`.** The recipe in scav.md (every `discover_*_h` and `scent_ticks` at 0) leaves `discover_min_h` at 2 h, which is 100 t, so a remains is never found in its first pass. The check also zeroes `discover_min_h`. As the notes word it, the claim would fail.
2. **`mech.v71.water.retry`.** `next_water_body` is set to max(release gap, `retry_days` × 1,200). When the adaptive clock's gap is longer than a day, the back-off exceeds the notes' "≤ `retry_days` × 1,200". The check reads both terms and judges the max.
3. **The GUI still runs v7.0 irruption logic.**
   - It disarms through `g.armed`.
   - The Layers text says "the next arriving cavern group … is armed", while IRRUPT v2 places its own waves.
   - This is for the UI wave. `gui.irr.rows` records it.
4. **`ROSTER.placeTick` has two callers**, `tick()` and the `roster apex now` verb. `mech.v71.apex.onecaller` requires that the *job* path is `tick()` alone and that the `ROSTER.apex.tick` hook is gone.
5. **`roster apex now` is forced**, so it ignores the cap. `mech.v71.apex.cap` therefore calls `ROSTER.apex.decide` unforced.
6. **With the tool disabled, `roster build land` shows an extinct apex at the capped 5**, not "raw 2". `mech.v71.extinct.ladder` turns the corrections on before building.
7. **VRM-EDGES-SRC.** Once a roster build has run, the edge table is per species (fixes section 1, item 2), so the vermin notes' "an ML consumer carries SWV_SMALL_FISH and SWV_COLONY" no longer holds as worded. The check compares each consumer's classes with `VERMIN.gobbleWants`.
8. **`CACHE.realmOverrideDone` is shared between script copies.** A copy may never load the user's realms json. This is noted in `mech.v71.extinct.realm`.
9. **`mech.v71.skill_profile`.** A pack species gets SNEAK 5 *and* combat 10, and is packaged whenever `hunters.pack_on` is set, not only under `v7.solo`. The check follows the code.
10. **`perf.p10.slice`.** `ROSTER.build` picks at random, so a sliced `perf build` cannot be compared with `roster build` roster for roster. Only the slice finishing without error, and its log, are judged.

## 9. Offline checks, and what the dry run catches

`validate-full.py --dry-run` is new. It runs `main()` against a stub rig: every probe answers `{}`, every verb answers `""`, and `subprocess.run` and `time.sleep` are stubbed. Every phase's Python therefore runs end to end. It then checks four things:
- **Syntax:** every distinct Lua chunk goes through `luac53 -p` (DFHack's own 5.3.6).
- **Engine names:** every name a chunk reads is checked against the checkout in `$SW_TOOL`.
  - Only `_ENV` exports are reachable as `sw.X`, so an unexported table is caught (memory screen-check-traps: unexported table).
  - A call must name a defined function.
  - Aliases such as `local V7=sw.V7` and `local G=sw.GRP` (`V7.GRP`) are resolved.
  - A field read off a known table is listed but not failed.
- **Verbs:** every console verb is checked against the dispatcher.
- **Raises:** any phase that raised is reported.

Exit 1 on any finding.

**On the v7.1 tip** (`d7cc6f9`), all phases:
- 910 stub calls;
- 339 Lua chunks, 0 syntax failures;
- 0 unknown names;
- 0 unknown verbs;
- 0 raises.

**Under `--only v71`:** every one of the 149 v7.1 claims is recorded exactly once.

**`tests/harness/test_validate_full.py`** checks four things:
- claim ids are unique and every surface is known;
- every v7.1 row maps to an existing `v71_<stream>`;
- every shipped backlog item resolves to a claim that exists;
- the dry run is clean. This last test is skipped without a v7.1 checkout; set `SW_TOOL`.

With the harness tests, `pytest tests/harness` gives 24 passed.

**What the dry run cannot catch:**
- a wrong return shape;
- a field that is nil at run time;
- a wrong expected value.

Only the rig settles those. Some builders also fed crafted answers to their sub-phases to reach the deeper branches; that is not a substitute.

## 10. Rig tests this needs, later

All on region8 forts (R11), on DFHack r2, after `revalidate-dfhack-r2`:

1. **Deploy and smoke.** Run `cx-lifecycle.sh deploy-tool <v7.1>/scripts`; all five scripts must show `ok`. Then `validate-full.py --only v71 --v71 deploy,fixes` on the CALM fort (CTRL until then).
2. **The full run** on the CALM fort. Read these first:
   - the updated claims of section 3, for any wording this desk work missed;
   - `bl.grouping` and `bl.balance`, resolved by their claims.
3. **One `--only v71` run per fort** in section 6: SHORE (deep and shallow), LAKE, RIVER, SAVAGE, and a breached-cavern fort.
4. **Any FAIL among the section 8 items:** decide whether the code or the note is right before changing the claim.

The validator is a functional check, one pass per claim, so R12's n = 5 applies to the experiments, not here.

## 11. Open risks

- **Nothing here has run on DF.** The dry run proves syntax, names, verbs and Python flow. It does not prove values.
  - Expect a first rig run to turn up wording mismatches, as v6.2.1's first run did (`luaj` parsing; run 143815).
  - Read every FAIL's `got` before believing it.
- **cfg_push/cfg_pop restore the config, the groups record and the enabled state. They do not remove units.** The apex, irruption, `place` and water draws leave units on the map until teardown restores the save.
  - `phase_v71` runs after `phase_w0` for that reason.
  - A later phase added after v71 would see those units.
- **An area that turns the tool on and off re-applies and restores the raws.** If a restore were incomplete, a later area would read changed raws. `mech.v70.restore_all` and `mech.v71.restore` exist to catch exactly that.
- **`V71` is detected by a feature.** If the lead renames `V7.GRP` before release, detection falls back to the version line, which the release bump sets anyway.
- **Region savagery comes from `active_site[0]`'s region tile.** That is the embark's tile, but a 1x1 can draw from neighbours (memory df-region-draw-tiles). Near a cut, the `calm` condition can be wrong.
- **`gui.irr.rows` and any Panel/web claim for the UI wave** stay NOT-TESTABLE-HERE until that wave lands.

## 12. Changelog fragment (DwarfCron, validator wave 2)

```
validator v7.1 (1 Oct 2026, W2:Urist)
- validate-full phase_v71: 149 claims, one sub-phase per v7.1 stream (deploy, fixes, ecology, groups, water, roster,
  extinct, vermin, scav, irruption, perf, web) plus the seven v7.0 ids the stub reserved (builder, gobble, scav_ext,
  outgun, realms, gate_drain, solo_skill); manipulation checks (MANIPFAIL) on every dial; fort conditions name the
  region8 fort (R11); --v71 picks sub-phases; runs after w0.
- existing claims follow v7.1: limits '[mode]' and the fixed cap on every layer (R7), the cavern cap (R44), cadence
  3000 and nudge off (R37/R38), scavenge tool-off wording, leader R32, solo by cohesionOf, fishers on a non-swimmer,
  the groups trio without layer_groups; bl.grouping and bl.balance shipped (R62).
- V71 detected by feature (V7.GRP), as v7.1 keeps the v7.0.0 header until release.
- --list and --dry-run (luac53, engine names against $SW_TOOL, verbs against the dispatcher); luap (pcall'd probes).
- cx-lifecycle deploy-tool cmp-checks the five seasonal-wildlife scripts (seasonal-wildlife-controls.lua is new).
- tests/harness/test_validate_full.py.
```

## 13. Merge hazards

- **`scripts/validate-full.py`:**
  - the CLAIMS rows edited in section 3, and the v7.1 block at the end of CLAIMS;
  - `phase_cli`, `phase_mechanics` (limits/water and the cadence), `phase_v69` (autogroups, scavenge) and `phase_v70` (leader, groups trio, raws probe, pack tag, `v7`);
  - the plumbing after `centre_on`, `SHIPPED_BACKLOG`, and the whole v7.1 section that replaced the stub;
  - `dry_report`, `main`, and the header (usage, `DRY`, `V71`).
- **`scripts/cx-lifecycle.sh`:** `cmd_deploy_tool` and the header comment.
- **New:** `tests/harness/test_validate_full.py`, and this document.
- **No edits in seasonal-wildlife.** The read worktree `sw-wt/claims-read` was removed when done.
