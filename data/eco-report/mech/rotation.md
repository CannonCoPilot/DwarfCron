# Seasonal rotation and arrival control: how the code does it

Source: `/Users/nathanielcannon/Claude/Projects/sw-wt/plugin`, branch `v7.2-plugin`, HEAD `8185d85` (clean). Read from the code only. Nothing was run against the game.

Line references use these short forms:

| Short | File |
|---|---|
| `sw:N` | `scripts/seasonal-wildlife.lua` (the engine, 18,778 lines) |
| `ctl:N` | `scripts/seasonal-wildlife-controls.lua` (the control registry) |
| `gui:N` | `scripts/gui/seasonal-wildlife.lua` |
| `cpp:N` | `plugin/src/seasonal-wildlife.cpp` |
| `plua:N` | `plugin/lua/seasonal-wildlife.lua` |

Where a doc disagrees with the code, the code wins, and the disagreement is listed in section 10.

---

## 0. The model in one page

**Two drivers.** Every layer gets its animals through one of two drivers.

- **Driver A: DF draws.** This covers land, sea life listed on land entries, and caverns 1-3. DF sends a "wave" from a population **source** whenever no flagged animal of that source is on the map. A source is a region tile x feature x cave x population entry; see `srcKey` at sw:4307 and the gate notes at sw:4167-4187 and sw:12567-12575. The tool steers these draws three ways:
  - **Who comes:**
    - on the surface, by the regional entry's `quantity` and `flags.extinct` (applyLive sw:3027, holdOutOfSeason sw:3072);
    - in the caverns, by the creature raw's `frequency` (CAVERN.apply sw:3698). Entry quantity gates nothing underground (sw:3548-3557, sw:3614-3621).
  - **When:** by holding DF's own gate shut. A wave's animals keep the `roaming_wilderness_population_source` flag, and the tool clears that flag (a "release") only on its own clock (releaseGroup sw:4411, detachOldest sw:4424).
  - **How many at once:** by a per-layer group cap (QUOTA.groupsFor sw:3526). In the caverns there is also a frequency hold and a trim (V7.GRP.cavernPass sw:12591).
- **Driver B: the tool draws.** This covers water bodies (ocean, lake, river or brook, pool), because DF never waves a feature entry in play (sw:4583-4586). The tool picks a species (ENGINE.candidates sw:5972, V7.WAT.mix sw:6394). It creates the animals with `dfhack.units.create` (PLACE.one sw:4821), debits the entry one per animal (sw:6125), and tracks them as a group under a per-body-type cap and clock (V7.waterTick sw:9280).

**The roster is the season.** Every managed key has an explicit `cfg.allow[key]` (true = active, false = inactive) and, when active, `cfg.assign[key]` = a list of seasons 0-3. `ROSTER.wants(cfg, key, season)` is the single test every pass uses: allow == true and the season is in assign (sw:2726). Keys:
- land species are keyed `TOKEN`;
- other layers are keyed `water:TOKEN`, `cavern:TOKEN` or `deep:TOKEN` (keyFor sw:1411).

The layer comes from the entry: `cave_id` gives cavern (depth 0-2) or deep (3+), `feature_idx` gives water, anything else is land (layerOf sw:1403).

**v7.3 season casts.** When `cfg.cast.enabled` and `cfg.casts` exist (ROSTER.castOn sw:8305), the roster is generated once a year:
- For each layer (land, water, cavern) and each season, a "cast" is grown from a high-value seed through its prey and predators into fixed guild slots (ROSTER.castGrow sw:8451, slots sw:8282-8297).
- A species in some season's cast is active with exactly those seasons.
- Every other species the cast layer manages "rests" (allow = false, no seasons).
- Locked species that would rest go into `cfg.casts.rest` (ROSTER.castYear sw:8589-8631; ROSTER.managedKey sw:2723).

---

## 1. The job schedule

### 1.1 Registration

All recurring jobs are DFHack `repeat-util` repeats (sw:518). Each is wrapped by `FUSE.job` (sw:4233) and started through `V7.PERF.every` (sw:16466).
- `V7.PERF.every` starts each repeat behind a one-shot `dfhack.timeout(phase, 'ticks')`, registered in repeat-util's own table so `repeatUtil.cancel(name)` also cancels the pending start (sw:16460-16479). With `perf.stagger` off, or no map loaded, it calls `scheduleEvery` directly.
- Phases are fixed offsets from the enable tick: `V7.PERF.PHASE = { groups = 31, daily = 77, ecology = 150, scav = 37, alerts = 5, curious = 23, forage = 61 }` (sw:16465).
- Jobs are scheduled from `enableSched` (sw:15926-15949) and `scheduleGroups` (sw:13330-13335). Both run on `enable rotation`, on `PANEL.fortOn` (`enable`/`on`), and at every map load of an enabled fort (PANEL.onMapLoad sw:16214).

What does not use repeat-util:
- **The season timer** (`V7.ST`, v7.3): a bare `dfhack.timeout` armed by the daily job (sw:4124-4128). It is not FUSE-timed.
- **The split-off water pass**: a bare `dfhack.timeout(3)` (V7.PASS.waterLater sw:13164-13174), run under the groups job's FUSE name.
- **Sliced load-time surveys**: per-tick `dfhack.timeout(1,'ticks')` coroutine steps (V7.PERF.slice sw:16790-16811). While paused they use per-frame steps (V7.PERF.drivePaused sw:16846-16862). The sliced work is the caverns, the wet edge, the water tiles, vegetation and the water-body registry scan (V7.PERF.warm sw:16863-16873).
- **FUSE defers**: a 1-tick `dfhack.timeout` re-run when another heavy job already used this tick, at most 3 times (FUSE.DEFER sw:4232, sw:4237-4247).
- **eventful**: used only to feed the census's wild-unit id set (`onUnitNewActive`, V7.PERF.eventsOn sw:16568-16583). It schedules no rotation work.
- **The C++ plugin**: schedules no rotation work. It only:
  - calls the Lua module at `SC_CORE_INITIALIZED` (autostart, cpp:7481-7490);
  - sets `bridge_pending` at `SC_MAP_LOADED` when the plugin is enabled (cpp:7491-7492), and calls `on_map_loaded` on the next frame (cpp:7430-7436 → plua:91-94 → `map_loaded` sw:16280);
  - turns the renderer on or off (`plugin_enable` cpp:7410-7422 → `turn_on`/`turn_off` sw:16219/16257).
  - `wscan` (cpp:6938-6981) is the native water-body scan the registry can use (V7.WB.native). It is a classifier, not a scheduler.
- **The engine's own state hook**: `dfhack.onStateChange[MODULE]` (sw:17098-17115).
  - On `SC_MAP_LOADED` and `SC_WORLD_UNLOADED` it runs `CACHE.drop`.
  - On world unload it also restores every raw write (each in its own `pcall`), cancels every job and sets `lastSeason = nil`.
  - On map load it runs `PANEL.onMapLoad`.

### 1.2 Job table

| Job (repeat name) | Cadence | Phase | Function | What it does for rotation and arrivals | Lines |
|---|---|---|---|---|---|
| `seasonal-wildlife` (daily) | 1 game day (`'days'` unit; per the code comment it runs at the enable hour, e.g. 1,068 t into each day, sw:4088-4089) | +77 | `tick` | See below. | sw:4133-4153, sw:15941 |
| `seasonal-wildlife/groups` | 300 t (`GROUPS_CADENCE`) | +31 | `groupsJob` → `groupsTick` | Runs only when `cfg.enabled and cfg.groups.enabled`. Steps listed in section 1.3. | sw:4157-4163, sw:13188-13305, sw:13331 |
| (groups, water step) | each groups pass, +3 t | — | `V7.PASS.water` → `ENGINE.tick` | Inside a scheduled pass the Driver B step runs as its own pass 3 ticks later. It tries one water body per pass (`V7.PASS.WATER_BODIES = 1`). | sw:13163-13187, sw:13259-13263 |
| `seasonal-wildlife/ecology` | `ecology.cadence` = 3,000 t | +150 | `ecologyJob` | Relation writes and the sweep (out of scope here). Reads the cast's edge set (ROSTER.castEdgeSet sw:8673). | sw:9570-9578, sw:13333 |
| `seasonal-wildlife/scavenge` | `scavenge.cadence` 200 t | +37 | `SCAV.run` | Not rotation. | sw:15375-15378 |
| `seasonal-wildlife/alerts` | 10 t | +5 | `ALERTS.run` | Not rotation. | sw:14722, sw:14760 |
| `seasonal-wildlife/curious` | `curious.cadence` 50 t | +23 | `CURIOUS.pass` | Not rotation. | sw:13669-13672 |
| `seasonal-wildlife/forage` | 100 t step | +61 | `VERMIN.forageRun` | Parked by default (`V7.parkNudges` sw:1071-1081). | sw:15834-15838 |
| `seasonal-wildlife/water`, `seasonal-wildlife/cavern` | — | — | — | Retired names. They are only cancelled, never run (sw:13347-13351). | |
| season timer (`CACHE.boundaryTimer`) | one shot at the boundary tick | — | `V7.ST.now` | Applies the season change at its own tick. If DF has not turned `cur_season` yet, it retries every 10 t, at most 12 times. | sw:4111-4128 |

What the daily job does, in order:
1. A season change if `cur_season ~= lastSeason` (V7.ST.turn). Otherwise `holdOutOfSeason`, then `CAVERN.apply`.
2. `V7.ST.arm` (sets the season timer).
3. `V7.WB.daily`: rescans the water-body registry at a new season, a newly found cavern or a settings change.
4. `ROSTER.placeTick`: the apex scheduler, at most once a game day.

**Budgets and fuses** (FUSE sw:4202):
- Every job pass is timed. Over `JOB_MS` (250 ms) it prints a warning. Over `TRIP_MS` (2,000 ms), or on any Lua error, `FUSE.trip` cancels the repeat outright, logs a `fuse` ledger line and keeps the trip in site data until `enable` re-arms (sw:4208-4216, sw:4273-4277).
- `BUDGET_MS` (50) only counts passes "over".
- Heavy scans take a `SCAN_MS` (1,500) deadline.
- Each pass shares one unit census (`CACHE.census`), opened and closed by FUSE.job (sw:4251-4256).
- Each job's parts are timed into the same stats by `FUSE.lap` (sw:4287).

**Coincidence.** With the default cadences the phases never land on the same tick (checked by modular arithmetic: groups ≡31 mod 300, daily ≡77 mod 1200, ecology ≡150 mod 3000, scav ≡37 mod 200, curious ≡23 mod 50, alerts ≡5 mod 10, forage ≡61 mod 100, the water pass ≡34 mod 300). If two jobs do meet (after a player cadence change or a defer), the later heavy one waits a tick (sw:4229-4247). The season timer can fire on any tick, and nothing staggers it.

### 1.3 Order inside one groups pass (`groupsTick`, sw:13188-13305)

1. `holdOutOfSeason` (every 300 t since v6.3, sw:13190-13194)
2. Waits if the load-time survey is still slicing (returns early, at most `WAIT_PASSES` = 20 passes, sw:13202-13206, sw:16834-16841)
3. A private config copy if a job-path config writer has work (`V7.PERF.writersDue` sw:16490-16510)
4. **v7.3 season-change fallback**: if `lastSeason ~= nil` and `cur_season ~= lastSeason`, it cancels the timer and runs `V7.ST.turn` (in a pcall), then re-reads the config (sw:13210-13218)
5. `ROSTER.exhaustCheck` (sw:13219)
6. `V7.WAT.spillCheck` (once a game day; returns at once under casts, sw:7362)
7. `reconcileGroups` drops members that have gone; a finished group's stay feeds the clock's W (sw:4370-4386, V7.GRP.observe sw:12371)
8. `PATTERN.trickleApply`, `V7.GRP.apCap`, `PATTERN.sizeApply`, `PATTERN.dawnStanding`
9. `discoverGroups`: new flagged waves become gated groups and get an `arrive` ledger line (sw:4388-4407, sw:13229-13230)
10. `V7.GRP.adoptNatives` (every 1,200 t, sw:12800)
11. **`V7.GRP.castTurnover`** (once per season stamp, sw:12778)
12. `applyCohesion` (leaders and panic) and `stuckSweep`
13. Coupling or pattern-table end/start (coupling is parked)
14. The Driver B water step (deferred +3 t inside a scheduled pass), then sponges
15. **The land release** (sw:13268-13288)
16. **`V7.GRP.cavernPass`**: cavern release, hold and trim (sw:13291-13296)
17. `IRRUPT.tick` (sw:13300)
18. `saveGroups`

---

## 2. The season deal

### 2.1 Who gets which season

- **Without casts** (the preset, matrix or manual roster), seasons come from `ROSTER.deal` (sw:2665-2673). Species are sorted by climate lean within their group (realm|habitat|role, sw:2638-2640) and dealt one season each by quarter (`ROSTER.quarterOf` sw:2647, order Winter, Autumn, Spring, Summer = `ROSTER.ORDER {3,2,0,1}` sw:2631).
- `ROSTER.normalize` (sw:2699-2714) makes the roster whole: every in-embark, unlocked species gets an explicit allow; an active one with no season gets one by `ROSTER.defaultSeason` (sw:2675); an inactive one is cleared of seasons. It runs at every `enableSched`, so at every load (sw:15933).
- **With casts**, `ROSTER.castYear` (sw:8589) writes allow and assign for every pool entry a cast layer manages (`ROSTER.castManages` sw:8576-8586). Casts are reseeded per site, year, season and layer:
  - seed = `(site*7919 + year*104729 + s*131 + #layer*17 + salt) % 2^31-1` (sw:8602);
  - a species in last winter's cast is weighted `carry` 0.25 (sw:8475), so the casts turn over year to year.

### 2.2 DF's NO_SPRING / NO_SUMMER / NO_AUTUMN / NO_WINTER versus `seasons_own`

- DF honours `NO_<season>` at its own pick (ECO T2, cited at sw:2650-2653). `classify` records them per creature as `noSeason[0..3]` (sw:1822-1823). Classification is memoized per world in `CACHE.class` (sw:1796).
- `v7.seasons_own` defaults to on (sw:840), and `V7.grpSanitize` forces it on at migration (sw:728). With it on:
  - `ROSTER.fitSeason` returns the dealt season unchanged (sw:2657-2663);
  - `V7.apply` clears every `NO_<season>` caste flag on every in-embark, unlocked species in the pool, recorded through `V7.rec` (sw:13833-13835);
  - the flags come back on disable, All off and world unload (`V7.restore` sw:13741, sw:15966, sw:16051, sw:17102);
  - Driver B ignores `noSeason` too (sw:5995-5999).
- With it off, the deal moves a forbidden season to the next allowed one (sw:2661) and Driver B skips the species in that season.
- **Casts honour the raws whatever `seasons_own` says.** `ROSTER.castPool` drops a species with `noSeason[season]` (sw:8393, sw:8406), and `ROSTER.castReplaceOk` refuses one as a stand-in (sw:8650). The flags are read from the memoized classification, so this holds only if `CACHE.class` was built before `V7.apply` cleared them (section 9, item P10).

### 2.3 What a season change does (`V7.ST.turn`, sw:4093-4109)

Called once per change by whichever comes first: the timer (`V7.ST.now`), the groups-pass fallback, or the daily job.

1. `lastSeason = s` (first, before any work).
2. Copy-on-write of the shared config (sw:4095).
3. `ROSTER.exhaustRoll`: borrowed seasons given back, exhausted marks forgotten (sw:3106-3120).
4. `V7.WAT.spillRoll`: water spill borrows given back (sw:7342-7358).
5. If casts are on and `casts.year ~= cur_year`: `ROSTER.castYear` grows this year's casts and saves (sw:4098-4101). In practice this happens at Winter → Spring, or at the first apply after a load into a later year.
6. **`applyLive(cfg, s)`** (sw:3027-3063):
   - For every managed entry on an enabled layer:
     - **In season** (`ROSTER.wants`):
       - a player stock (`cfg.stock[key]`) is written exactly, spread over the entries (RESERVE.set sw:3015), unless the key is exhausted;
       - an entry at quantity ≤ 0 is refilled from the reserve `res[i]`, else the worldgen snapshot `default_snapshot[key]`, else `qtyFor` = `in_season_qty × weight / 50` = 100 by default (sw:2453, sw:3042-3048);
       - an entry above 0 is left as DF keeps it;
       - the reserve slot is then cleared and `extinct = (quantity <= 0)` (sw:3049-3050).
     - **Out of season, inactive or resting**: the quantity is saved into the reserve and the entry is set to `quantity = 0, extinct = true`, "both barriers" (sw:3053-3054).
   - It sets **`CACHE.appliedStamp = year*4 + season`** when `season == cur_season` (sw:3061).
7. A DF announcement "`<Season> wildlife roster applied.`" (sw:4103) and a `season` ledger line "`<Season> roster applied: land 9+3 (seed …), …`" (sw:4104).
8. `PATTERN.trickleApply` (sw:4105).
9. `CAVERN.apply(cfg, s)`: cavern and deep FREQUENCY for the new season (sw:4107, section 3.4).

Nothing in the turn dismisses groups or rescans water. The turnover runs in the next groups pass (`castTurnover`), and the registry rescan in the next daily pass (`V7.WB.daily` sw:6851-6864).

### 2.4 The v7.3 season timer (commit 34a3a4b)

- `V7.ST.arm` is called by every daily pass. When the boundary is ≤ 1,500 t away (`V7.ST.TICKS` = 403,200/4 = 100,800), it arms a one-shot timeout for the boundary tick (sw:4124-4128). The daily cadence is 1,200 t, so the last day before a change always arms it.
- `V7.ST.now` (sw:4111-4123):
  - It returns if the tool is off or `lastSeason == nil` (no apply yet since the load).
  - If DF has not turned `cur_season` yet, it re-arms every 10 t, up to 12 tries (120 t).
  - Otherwise it runs `pcall(V7.ST.turn)`. An error becomes a `fuse` ledger line.
- **Fallback**: the groups pass (sw:13210-13218), then the daily job.
- `V7.ST.cancel` runs in `enableSched` (sw:15938), `disableSched` (sw:15951) and the groups fallback.
- `CACHE.drop` forgets the timer id (sw:17092), because tick timeouts die with the map.

### 2.5 `CACHE.appliedStamp` and the exhaustion race (commit 6e1ffb2)

- `ROSTER.exhaustCheck` returns at once unless `CACHE.appliedStamp == year*4 + cur_season` (sw:3128).
- Before the fix, the groups pass could reach a boundary before the daily apply. It found the new season's species still at 0 from their rest, called them exhausted, and swapped 17 of 22 autumn cast species for stand-ins (the comment at sw:3124-3127).
- The stamp is set only by `applyLive` (sw:3061) and dropped with the map (sw:17091). So after a load no exhaustion check runs until the first daily pass (+77 t) has applied the season.

---

## 3. Holding and resting: keeping out-of-cast species away

### 3.1 Surface (land and water entries): quantity, extinct flag, reserve

| Mechanism | Where | What |
|---|---|---|
| Season apply | applyLive sw:3027 | Out of season: `res[i] = quantity`, then `quantity = 0`, `extinct = true`. In season: refill only entries at 0. |
| Hold | holdOutOfSeason sw:3072-3090 | Every managed entry with quantity > 0 that the roster does not want this season is pinned back to 0 and extinct, and the amount is **added** to its reserve. Runs every groups pass (sw:13194) and every daily pass (sw:4141). |
| Why the hold re-runs | sw:3065-3071, sw:13190-13192 | DF refunds a departing animal to the entry it came from, whether or not it still has its flag (E15, v5.3, sw:4181-4187). A refund to an out-of-season entry would let DF draw a fresh out-of-season wave. |
| Reserve store | RESERVE sw:2974-3012 | Site-data key `seasonal-wildlife/reserve`, keyed by **position in `world.populations.all`** (`tostring(r.i)`). `RESERVE.of` reports live and held stock. |
| Player stock | `cfg.stock[key]`, RESERVE.set sw:3015 | Written exactly at the apply. A stock of 0 is "a choice, not exhaustion" (sw:3098-3099, sw:3132). |

**How stock comes back in season.** At the next `applyLive` with the species in season, each entry at quantity ≤ 0 takes back its remembered reserve (or the snapshot, or 100) and its extinct flag is cleared. DF then debits one per arriving animal and breeds the entry up (sw:3069-3070). Driver B debits one per placed animal (sw:6125). A stand-in or spill restocks the same way (sw:3173-3183, sw:7404-7413).

### 3.2 Caverns (and deep): raw FREQUENCY

- `CAVERN.apply` (sw:3698-3760) runs at every season change and every daily pass. It builds a `want` per raw token from every key on the cavern layer (when `layers.cavern` is on), the deep layer (`layers.deep`), or any key with player odds.
  - **Open** (wanted this season by any key of the token): the player's odds, or the raw restored from the snapshot (floored by the R61 animal-people floor, sw:3742).
  - **Held** (a cavern or deep key not wanted, or passed over by a `call`): `CAVERN.SUPPRESSED = 1` (sw:3630).
  - Under casts, held species take **`CAVERN.restLevel`** instead (sw:3753): `cfg.cast.cavern_rest_freq` (default 1; `cast restfreq 0|1` sw:18351-18357).
- **restfreq 0 vermin guard** (09ab266, sw:3683-3697): FREQUENCY 0 is allowed only when the raw is not vermin by `classify` and carries none of VERMIN_FISH, VERMIN_SOIL_COLONY, VERMIN_ROTTER, VERMIN_GROUNDER, VERMIN_SOIL, nor the caste flag VERMIN_MICRO. Otherwise it stays at 1. The reason is in the comments: CREEPY_CRAWLER at 0 froze DF (sw:3623-3629); FREQUENCY 1 "still leaks ~15%" (sw:3681).
- **Locked species a cast rests** (`casts.rest`: BLOOD_MAN, ELEMENTMAN_MUD…) are held too, though they have no allow entry (sw:3716-3723).
- **Land keys are never held by raw** (sw:3678): "A land key out of season is held by its stock, not by its raw."
- **Snapshot**: every value written is first kept in `seasonal-wildlife/cavern` site data (CAVERN.write sw:3647-3654; CAVERN.saved/save sw:3640-3644). It is put back by `CAVERN.restoreAll` (sw:3659-3668) on disable, All off and unload. An orphan sweep restores holds no layer or gate owns any more (V7.GRP.orphans sw:12708-12722).

### 3.3 The hold is re-asserted in the groups job

- **Every 300 t**: `holdOutOfSeason` (sw:13194).
- **Daily**: `holdOutOfSeason` and `CAVERN.apply` (sw:4141-4142).
- The cavern gate's own frequency hold changes whenever its at-cap set changes (`V7.GRP.cavernHold` sw:12723-12768, keyed by `CACHE.capSig`).
- **Not every 300 t**: `CAVERN.apply`. A cavern raw changed by something else stays changed until the next daily pass. Examples: a stand-in promoted in a cavern, or a gate hold written over a resting species (section 9, P7).

---

## 4. Exhaustion and stand-ins

`ROSTER.exhaustCheck` (sw:3121-3193) runs every groups pass, after the apply stamp check.

1. `exhaustRoll` (same stamp: no-op).
2. For every key wanted this season (and not stock 0, not already done), sum the entries' live quantity. Every key at 0 is **exhausted**: `x.done[key] = true`.
3. For each exhausted non-vermin key, it picks a **stand-in**:
   - **Without casts**: the same `ROSTER.group` (realm|habitat|role). The score is the log-mass distance, plus 100 when the guild differs.
   - **With casts**: `ROSTER.castReplaceOk` (sw:8635-8662). The stand-in must fill the same cast slot on the same layer and eat, or be eaten by, a member of this season's cast. A **resting** species may be chosen (`cfg.allow == false` is accepted under casts, sw:3155).
   - In both cases the stand-in must:
     - not be in season already;
     - not be done or promoted;
     - have live + reserve + snapshot stock > 0;
     - without `seasons_own`, not be forbidden that season by the raws.
4. The stand-in gets the season added to its assign and `allow = true`. Its entries are restocked from reserve, snapshot or qtyFor, and extinct is cleared. It is recorded in `x.promoted[key] = { season, for_key, resting }` with an `edit` ledger line (sw:3167-3185).
5. While `x.done` holds a key, `applyLive` does not refill it (`ROSTER.exhaustHolds` sw:3101-3104, sw:3041-3042).

**Retirement** (`ROSTER.exhaustRoll` sw:3106-3120, at the season change or at the first check of a new stamp):
- The borrowed season is removed from each stand-in's assign, but never when that would leave an active species seasonless.
- A stand-in that was resting goes back to rest (`allow = false`, assign nil, sw:3114).
- `done` and `promoted` are cleared.
- The stand-in's entries are then zeroed by the turn's `applyLive`, because it is no longer in season.
- Its groups already on the map:
  - **Under casts**, the next `castTurnover` dismisses them (no longer wanted).
  - **Without casts** they stay until their own leave countdowns run out.

**Caverns**: a cavern stand-in's stock is opened at once, but its FREQUENCY stays held until the next daily `CAVERN.apply`, up to one game day later (exhaustCheck does not call CAVERN.apply).

---

## 5. Turnover at a season change, and natives

### 5.1 `V7.GRP.castTurnover` (sw:12778-12799), casts only

- Once per `year*4 + season` stamp, kept in `CACHE.castTurnStamp`. Only `cast rebuild` clears it (sw:18365).
- It walks every tracked group that is not already dismissed and not an irruption wave. It computes the key from the group's layer:
  - `keyFor(layer, token)` first;
  - **fix 8817eb4** (sw:12788-12791): if that key is not managed but the plain land key is, it uses the land key. Ocean life and river fish have no feature index, so the pool files them under their land key even when Driver B drew them into water groups.
- A group whose key is managed and not wanted this season is **dismissed** (`dismissGroup`), with one ledger line listing the species.

### 5.2 How send-off works mechanically

| Path | Writes | Teleport? | Lines |
|---|---|---|---|
| `dismissGroup` (turnover, `groups dismiss`) | every live member `animal.leave_countdown = 0`; follower links cleared; `grp.dismissed = true`; roaming flags **left as they are** | no | sw:10594-10601 |
| `ENGINE.sendOff` (`sendoff land|cavern`, a `call`, the window's Ctrl+F) | discover first, then for every **gated** group of the layer: `dismissGroup` + `releaseGroup` (both roaming flags cleared); resets that layer's release clock to now | no | sw:10613-10630 |
| `V7.GRP.trimOne` (cavern over cap) | each natural member's `leave_countdown = 10` (the old value kept in `g.trim_undo` and put back on disable, All off and unload if the unit is still there); `trimmed`, `dismissed`, and `trim_gated` for a DF wave | no | sw:12636-12673, sw:13055-13067 |
| `holdGroup` | raises countdowns | no | sw:10584-10593 |

The animals walk off on DF's own leave path. Nothing teleports, kills or deletes them. A dismissed group stays in `g.groups`, and in every count, until `reconcileGroups` sees its members gone (sw:4361-4386). For a group in an enclosed lake or pool, no code checks that a path off the map exists.

### 5.3 Discovery of DF waves vs adoption of natives

- **Discovery** (`discoverGroups` sw:4388-4407, `gatedLayer` sw:4351-4359) counts any active, living, non-invader unit carrying `flags2.roaming_wilderness_population_source` with **`feature_idx == -1`**. A unit with no cave is land; a cave of depth 0-2 is cavern. Units are grouped by race|source into one **gated** group (`resident = false`).
- **Adoption** (`V7.GRP.adoptNatives` sw:12800-12854, every `ADOPT_EVERY` = 1,200 t; `CACHE.grpAdoptAt`) takes any natural wild unit that no record holds and that carries no roaming flag:
  - a young one whose mother is tracked joins her group;
  - otherwise it is grouped by layer|race|source as a **native** (land or cavern; counted) or a **seeded** water school (led, never counted).
- **Defaults outside casts**: `natives_cavern = true`, `natives_land = false`, `seeded_water = true` (sw:802).
- **Under casts** (v7.3, sw:12809-12822):
  - every land native is adopted, whatever `natives_land` says;
  - every water unit is adopted;
  - a unit **flagged** in a water feature (DF's embark fish) is adopted too; otherwise discovery and adoption both skip it.
  - Adopted natives of resting species are then dismissed by the same pass's `castTurnover`. Adoption runs before turnover in the pass.

**Natives at load.** At map load:
1. The first groups pass (+31 t) holds stock and, if the load-time survey has finished, adopts and turns over.
2. No exhaustion runs and the season apply has not happened (lastSeason nil) until the daily pass at +77 t. That pass makes a full `V7.ST.turn`, with the announcement, at every load.

---

## 6. Group caps and the gate

### 6.1 Caps (`QUOTA.groupsFor` sw:3526-3537)

| Layer key | Cap | Default |
|---|---|---|
| `land` | `limits.mode == 'formula'`: `floor(sqrt(embark tiles)) + 1`, where embark tiles = `(map.x_count//48) * (map.y_count//48)` (`QUOTA.autoGroups` sw:3508-3513); `'fixed'`: `limits.fixed` | formula, so 2 on a 1x1, 5 on a 4x4, 9 on an 8x8 |
| `water:<ocean\|lake\|river\|pool>` | the same formula or fixed value, **per body type**, not per individual body (V7.GRP.lk sw:12320-12325; waterTick counts `grp.body == body` sw:9294) | as land |
| `cavern:<0\|1\|2>` | `groups.cavern_cap`, universal; under fixed mode `min(cavern_cap, fixed)` | 5 |
| deep | no key, no cap (R60) | — |

Animal **ceilings** (`limits.<layer>.ceiling`, default 0 = none) are separate:
- land: no release at or over the ceiling (sw:13272-13273);
- water: no draw at or over it (sw:9306-9307);
- cavern: every cavern species held at 1 by `CAVERN.apply` while over (sw:3726-3734).

`QUOTA.cavernThrottle` (sw:3574-3609) has **no caller** and `QUOTA.cavern` returns 0 (sw:3558), so it is dead code.

### 6.2 The release clock (R31, `V7.GRP.ctl/gapFor/dueTick/releaseGap` sw:12344-12421)

Each layer key keeps its own controller. Its state lives in `g.ctl[lk]` in the groups record.
- **W**, the mean stay, is an exponential mean (`w_alpha` 0.2) of finished groups' stays. Priors: land 34,500, water 27,000, cavern 30,000. Natives, seeded, trimmed and irruption groups do not feed it (sw:12372).
- **L\*** is redrawn uniformly in `[cap - target_band, cap]` (band 1) at every release, with a jitter `1 ± gap_jitter` (0.35).
- **gap** = `W / L* × f × jitter`, where:
  - `d = L* - n` (n = groups there now);
  - `f = 1/(1 + catchup×d)` when d > 0, else `1 + catchup×|d|`;
  - the result is clamped to `[gap_floor_days, gap_max_days]` = [0.5, 20] days.
- Each pass recomputes the due tick from the last release with the current n. The layer's timer only ever moves **earlier**. At n ≥ cap the clock returns nil, which pauses it.
- `adaptive` off, or the `burst` pattern, uses `PATTERN.nextGap`: 5-20 jitter days (`gap_min_days`, `gap_max_days`), or burst gaps (sw:10236-10254).

**Land release** (sw:13268-13288). All of these must hold:
- no coupling or pattern table restored this pass;
- `nLand < cap`, where `nLand` = `ENGINE.count(g,'land')`, every land group except seeded (sw:6147-6151), so natives, placed apex groups and dismissed groups that have not left all count;
- now ≥ `g.next_wave_tick`;
- under the land ceiling.

Then `detachOldest` releases the oldest gated land group (sw:4424-4434), and its source can draw again.

**gate_drain** (`v7.gate_drain`, on): `V7.drainGate` (sw:4445-4464) then releases the next-oldest gated groups of the layer until at most one flagged animal remains. It releases at most `room = cap - n - 1` extras (sw:13282).

### 6.3 The cavern gate (R44, `V7.GRP.cavernPass` sw:12591-12635)

Per depth d, with `cap = cavern_cap` (5):
- **Count**: every cavern group of depth d except running irruption waves: DF waves (gated and released), natives, placed and adopted groups, **and dismissed or trimmed groups not yet gone** (sw:12595-12601).
- **Release**: if a gated group exists and n < cap and the depth's clock is due, `detachOldest(g,'cavern',d)`. The gap is multiplied by 0.5 while irruption pressure for that cavern is high (`IRRUPT.gapDays` sw:10938-10953, sw:12607, sw:12615), then gate_drain runs.
- **Trim** (`cavern_trim`, on; `trim_days` 1): if n > cap, at most one group per depth per day (`V7.GRP.trimOne` sw:12636-12673):
  - the oldest native first, else the oldest resident;
  - with `cavern_trim_gated` (on, ruled 2 Oct) and no resident left, the oldest **gated DF wave**. Its source then reopens (sw:12649-12652).
- **Hold** (`V7.GRP.cavernHold` sw:12723-12768): while any cavern a species lives in is at cap (`cavern_hold = 'any'`), every **natural** species with an Animal entry in a cavern and none on the surface or below the caverns (`V7.GRP.species` sw:12529-12559; `cavern_hold_shared` off) is held:
  - at `V7.GRP.holdLevel` = `max(2, weight // 10)`, never above its weight (`cavern_hold_mix` on, sw:12683-12688);
  - at 1 if the roster itself holds it (`V7.GRP.holdFor` sw:12691-12700).
  - It releases only the holds it made itself (`CACHE.capOwn`) and then re-runs `CAVERN.apply` so the roster's own holds stand (sw:12738-12762).
- **The cavern gate at 5**: the hard part is release withholding. It only stops a source that currently has a **flagged** (gated) group on the map (comment sw:12571-12573, sw:12580).

### 6.4 Water caps and the tool's own draws (`V7.waterTick` sw:9280-9345)

For each body type the registry holds:
1. n = water groups of that type that are not seeded; cap = `QUOTA.groupsFor('water:<type>')`.
2. The adaptive due tick, but never inside an empty-draw back-off (`g.water_retry`, sw:9297-9301).
3. A scheduled pass tries at most one body (`V7.PASS.WATER_BODIES`).
4. `ENGINE.draw` (sw:6081-6103):
   - **candidates**: active, in season, stocked managed entries on the water layer, or AQUATIC land entries when `water.land_aquatic` is on (sw:5972-6014);
   - a body type the species may enter (`V7.WB.fitting` sw:6942-6956; brooks take adult mass ≤ 10,000 cm³ only, sw:6918-6941);
   - weighted by `ENGINE.weight` × `V7.WAT.mix`;
   - up to 3 species tried (`V7.WAT.RETRIES`).
5. `ENGINE.drawOne` (sw:6104-6146):
   - group size from `cfg.group_size` or the raw cluster;
   - capped by stock and ceiling room;
   - the entry tile from `V7.WAT.entry` (sw:7151): an edge column for oceans and rivers, else edge, then nearest the centroid; the column tile is the **first full (7/7) tile from the bottom up** (`V7.WAT.colTile` sw:7043-7054; runs encode `zz = bottom*1024 + top`, sw:6542-6548);
   - the group fills outward through breathable tiles of the same body (sw:7092-7120);
   - each unit is placed by `PLACE.one` (create, copy the six-field population reference, leave countdown `water.countdown` 25,000 ± 20%, clear the roaming flags, set position, insert into `units.active`, occupancy bit, enemy slot; sw:4821-4846);
   - the entry is debited by 1 per unit;
   - the group record has `drawn = true`, `resident = true` (never gated);
   - it is led in the same pass (sw:9332).
6. After a draw the next one waits on the adaptive gap. After an empty draw it waits exactly `water.retry_days` (1).

Cavern pools are never drawn by Driver B: `V7.GRP.BODIES` is ocean, lake, river and pool only (sw:695).

### 6.5 Season spill (thin water bodies; `V7.WAT.spillCheck` sw:7359-7423)

- Once a game day.
- For each body type with fewer than `water.spill.min` (3) drawable in-season candidates, active **out-of-season** water species (nearest dealt season first) borrow the current season. Their entries are restocked from reserve, snapshot or qtyFor.
- The borrow is recorded in `water.spill_state.borrowed`, given back at the change (`spillRoll` in `V7.ST.turn`), on disable (sw:15972) and on `water spill off`.
- **Under casts the spill is off** (`return 0`, sw:7362): "the water cast is the season's water roster."

### 6.6 Irruption and the gate

Irruption (opt-in; `irruption.enabled` defaults to false, sw:10754, but `enable`/`PANEL.fortOn` turns every non-parked Panel switch on, including irruption, sw:16102):
- halves the cavern's release gap while pressure is ≥ `gap_share × threshold` or the layer is in warning or active (sw:10938-10953, sw:12607);
- its waves are tool-placed, outside the cavern cap and never trimmed or turned over while the event runs (sw:12597, sw:12639, sw:12785);
- lifts the animal-people cluster cap on that cavern (sw:13001-13003).
- When the event ends, `grp.irruption` is cleared (sw:11796). The survivors then count against the cap and can be trimmed.

---

## 7. Persistence, load, disable

### 7.1 Per-save site data

| Key | Holds | Lines |
|---|---|---|
| `seasonal-wildlife/config` | the whole config (rebuilt key by key by `loadConfigRaw`) | sw:521, sw:894-1060 |
| `seasonal-wildlife/groups` | `g.groups` (every tracked group), `next_wave_tick`, `next_cavern_depth`, `next_water_body`, `water_retry`, `ctl` (each layer's W, L\*, last release), `trim_undo`, `rapex`, `exclusion` (a coupling or pattern snapshot), irruption state; compact JSON via `V7.PERF.persist` | sw:4188, sw:4315-4345, sw:16360-16369 |
| `seasonal-wildlife/reserve` | out-of-season stock by population index | sw:2983-2988 |
| `seasonal-wildlife/cavern` | original FREQUENCY of every raw the tool holds | sw:3630-3644 |
| `seasonal-wildlife/quota` | the dead cavernThrottle's snapshot | sw:3561-3568 |
| `/ledger` (300 entries), `/undo` (50 deep), `/fuse`, `/panel` (All-off switch memory), `/caverns`, `/wetedge` | as named | sw:1156, sw:1219, sw:4202, sw:15997, sw:4621, sw:5543 |

Config fields that matter here: `enabled`, `layers`, `allow`, `assign`, `weight`, `stock`, `odds`, `default_snapshot`, `exhaust {enabled, stamp, done, promoted}`, `water.spill_state`, `limits`, `groups.*`, `patterns`, `v7.*`, and **`cast` / `casts`**.

**b0895b9.** Until this commit, `saveConfig` wrote `cast` and `casts` but `loadConfigRaw` never read them back. After any save and load a fort ran with no casts and the cast switch off, and `full_enable_roster` and `migrated_v71` were lost the same way (comment sw:8306-8309). `V7.castSanitize` (sw:8315-8347), called last in `loadConfigRaw` (sw:1058), now reads back:
- `cast` (only the `CAST_DEF` keys plus `cavern_rest_freq`);
- `casts.year`, `casts.built`, the per-layer per-season records (members, vermin, seed and the rest copied as written), and `casts.rest`;
- `full_enable_roster` and `migrated_v71`.

`cfg.cast` is not in `defaultConfig`; `ROSTER.castCfg` creates it on demand with `enabled = true` (sw:8298-8304).

**Raw writes are memory only.** This covers NO_<season> clears, FREQUENCY, cluster sizes (trickle, group size, animal-people cap), hunting flags and the rest. DF re-reads raws on load. **Population quantities, extinct flags and units' leave countdowns are saved in the world.**

### 7.2 Map load

1. `CACHE.drop` (sw:17078-17097) clears:
   - cfg, ledger, pops index, reserve cache, cavern snapshot cache, groups cache (PERF.drop), census, surveys, water-body registry;
   - `appliedStamp`, `boundaryTimer`, `waterLater`;
   - per world only: class memos, race indices, cave depths.
2. `PANEL.onMapLoad` (sw:16214): if `cfg.enabled`, `enableSched` (sw:15926-15949) runs:
   - `V7.WAT.autoLayer` (water layer on if the map has water and the player never set it, sw:7311-7326);
   - `buildPool`, `ROSTER.normalize`, `CACHE.managedPops()`;
   - `HUNT.apply`, `CURIOUS.apply`, `V7.apply` (NO_<season> cleared again, etc.);
   - `saveConfig`, `lastSeason = nil`, `V7.ST.cancel`, `FUSE.reset`;
   - `V7.PERF.warm` (sliced surveys and the registry scan);
   - every job scheduled.
   - It also runs `IRRUPT.MASK.onLoad`.
3. The plugin's bridge (when the renderer is enabled) calls `map_loaded` on the next frame (sw:16280-16291):
   - a fort with **no config at all** gets `PANEL.fortOn` (everything on; casts grown when `cast.enabled`; sw:16086-16124);
   - otherwise it runs `onMapLoad` only if the engine's own handler missed the load.
4. In the first ticks:
   - **+31**: groups pass (hold; wait for the survey, or adopt and turn over);
   - **+77**: the daily pass makes the full season turn (applyLive, CAVERN.apply, appliedStamp). With casts, `castYear` runs if the save's `casts.year` is older than the current year.

### 7.3 Disable, All off, unload

- **`disable` / `disableSched`** (sw:15950-15978):
  - cancels the timer;
  - restores cavern FREQUENCY (`CAVERN.restoreAll`), trickle, group size (which reaches `V7.GRP.restoreAll`: animal-people cap, gate holds, trim countdowns, sw:13036-13070), hunting, curious, scavenging walks, every V7 raw write and forager walks;
  - gives back spill borrows;
  - sets `enabled = false`;
  - cancels every job;
  - restores irruption writes.
- **`off` / `disable seasonal-wildlife`**: `turn_off` → `disableSched`, plus the aquarium flag and autostart off (sw:16257-16279).
- **All off**: `PANEL.allOff` remembers the switches, runs `PANEL.restoreAll` (also ends a standing coupling or pattern table, sw:16042-16060), and sets every non-layer switch off. The GUI then calls `disableSched` (gui:2641); the registry calls `reschedule` (ctl:913-914).
- **World unload**: each restore in its own pcall, every job cancelled, `lastSeason = nil` (sw:17099-17109).
- **What none of these put back**: population **quantities and extinct flags**, and `exhaust` / `spill` assignment edits (spill is given back on disable; exhaust borrows are not). Every out-of-season, inactive or resting entry stays at `quantity = 0, extinct = true` in the world after disable, with its stock remembered only in the tool's `reserve` site data. Only `resetToDefault` (a Roster "reset everything") writes quantities back from the worldgen snapshot (sw:3928-3940).

---

## 8. Defaults and config keys (from `defaultConfig` sw:735-868 and the sanitizers)

### 8.1 Rotation and holding

| Key | Default | Meaning | Control / verb |
|---|---|---|---|
| `enabled` | false (a new fort: `enable` sets true) | seasonal rotation (jobs run) | Panel `rotation` (sw:15999); `enable rotation` / `disable` (ctl:79) |
| `layers.land/water/cavern/deep` | true / false / false / false (`enable` turns all four on, sw:16102) | which layers are managed | Panel `land`, `water`, `cavern`, `deep`; `layer X on|off` |
| `water.layer_auto` / `layer_set` | true / false | water layer on where the map has water | `water layer auto|on|off` (ctl:251) |
| `in_season_qty` | 100 | refill amount (× weight/50) when no reserve or snapshot exists | — |
| `weight[key]` | 50 | abundance multiplier for qtyFor | — |
| `stock[key]` | absent | exact stock written in season | `stock KEY N` |
| `odds[key]` | absent | FREQUENCY written while open | `odds KEY N` |
| `v7.seasons_own` | true | tool's deal overrides NO_<season> | `v7 seasons_own` (ctl:437) |
| `cast.enabled` | true when first created (`CAST_DEF`) | season casts are the roster | `cast on|off` (console only) |
| `cast.cavern_rest_freq` | 1 (absent → 1) | FREQUENCY for resting cavern species | `cast restfreq 0|1` (console only) |
| `cast.carry / giant / pack / hv_petvalue / hv_mass / salt` | 0.25 / 0.2 / 3 / 200 / 1,000,000 / 0 | cast growth weights, high-value seed test, reseed salt | `cast rebuild [SALT]` |
| `exhaust.enabled` | true | exhaustion and stand-ins | Panel `exhaust`; `exhaust on|off|now` |
| `water.spill.enabled` / `min` | true / 3 | season spill (off under casts) | `water spill`, `water spill min` (ctl:254-255) |
| `parked` | true | nudges parked: ecology nudge, coupling, forage, stoop, fishers, panic forced off (sw:1065-1081) | config only |

### 8.2 Caps, clock and gate

| Key | Default | Control |
|---|---|---|
| `limits.mode` / `limits.fixed` | 'formula' / 3 | ctl:90-92 |
| `limits.land/water/cavern.ceiling` | 0 / 0 / 0 | ctl:93-95 |
| `groups.enabled` | true | Panel `groups` |
| `groups.adaptive` | true | ctl:102 |
| `groups.target_band`, `catchup`, `gap_jitter`, `gap_floor_days`, `gap_max_days`, `w_alpha` | 1, 1.0, 0.35, 0.5, 20, 0.2 | ctl:103-108 |
| `groups.gap_min_days` | 5 (non-adaptive only) | — |
| `groups.w_prior_land/water/cavern` | 34,500 / 27,000 / 30,000 | ctl:109-111 |
| `groups.sync_countdown` | true | ctl:112 |
| `v7.gate_drain` | true | ctl:445 |
| `groups.cavern` | true | ctl:120 |
| `groups.cavern_cap` | 5 | ctl:121 |
| `groups.cavern_hold` | 'any' | ctl:122 |
| `groups.cavern_hold_mix` | true | ctl:123 |
| `groups.cavern_hold_shared` | false | ctl:124 |
| `groups.cavern_trim` / `cavern_trim_days` / `cavern_trim_gated` | true / 1 / true | ctl:125-127 |
| `groups.natives_cavern` / `natives_land` / `seeded_water` | true / false / true | ctl:128-130 |
| `groups.apcap` | 5 | ctl:131 |
| `patterns.land/water/cavern` | 'steady' | ctl:98-100 |
| `water.enabled` | true | ctl:247 |
| `water.countdown` | 25,000 | `water countdown N` |
| `water.retry_days` | 1 | ctl:258 |
| `water.land_aquatic` | true | `water aquatic on|off` |
| `water.mix` | `{enabled=true, balance=1.0, balance_cap=4, feed=0.5, pyramid=0.5, apex_max=1, cap=20}` | ctl:263-268 |
| `water.pull` | `{enabled=true, k=1.0, min=1.5, cap=4, lift_floor=true}` | `water pull` |
| `water.bodies` | `{min_tiles=9, pool_max=64, scan_ms=4}` | `water bodies` |
| `water.brook_max_mass` | 10,000 (absent → `V7.WB.BROOK_MAX_MASS`) | — |
| `cavern.countdown` | 25,000 (placements) | — |
| `roster.apex` | `{enabled=true, presence={land=25, flying=0, water=20, cavern=70}, cap_calm=1, cap_savage=2, residence=21500}` | ctl section `roster` |

Hard-coded constants:
- `GROUPS_CADENCE` 300, `ADOPT_EVERY` 1,200, `TRIM_COUNTDOWN` 10, `HOLD_DIV` 10, `CAVERN.SUPPRESSED` 1;
- `V7.ST` retry: 10 t × 12; arm window 1,500 t;
- `V7.PASS.GAP` 3, `WATER_BODIES` 1;
- FUSE: 250 / 2,000 / 1,500 / 50 ms, DEFER 3.

**Controls not exposed in the registry or Panel**: `cast.*` (console only), `water.countdown`, `cavern.countdown`, `groups.gap_min_days`, `in_season_qty`, `parked`.

---

## 9. Known gaps, races and suspicious logic

Ordered roughly by impact. "Field" marks a field report this explains.

**P1. Field: land overshoot (9.65 vs 9).** Nothing ever reduces the land count. There is no land trim; only caverns trim (`cavernPass` sw:12591; the land block sw:13268-13288 only withholds releases). The status line says so: "paused, N over the cap (placed, DF waves)" (sw:13114). Sources of overshoot, all counted by `ENGINE.count` (sw:6147):
- (a) DF draws per border source. Any source whose flagged group died or walked off draws again with no release, and an 8x8 embark has many land sources.
- (b) Under casts, **every land native is adopted and counted** whatever `natives_land` says (sw:12822). The `natives_land` default of false exists precisely because it is not counted.
- (c) The apex scheduler places land, water and cavern apex groups against its own cap (`cap_calm` 1 / `cap_savage` 2, sw:8861), not the layer cap, and they count (`resident`, `placed`, sw:8829-8834).
- (d) A release at n = cap-1 lets the released source draw again, so the count reaches the cap. Any spontaneous source then overshoots it.
- (e) Dismissed (turnover) groups count until they physically leave.

**P2. Field: the cavern gate cannot hold DF's waves (23-31 groups in cavern 2 vs cap 5).**
- (a) Release withholding stops only a source that currently has a flagged group on the map (sw:12571-12580). A cavern spans many region-tile sources.
- (b) The hold is a weight, not a gate. Every in-season natural cavern-only species drops to `weight // 10` (minimum 2). Per the code's own comments, FREQUENCY is "a comparative weight on a shared budget" (sw:12675-12682). Scaling every species by the same factor keeps their ratios, so it thins arrivals only to the extent that DF's wave rate depends on absolute frequency. The code has no test of that.
- (c) Species that also live on the surface, in surface water or in the deep are **never held** (`cavern_hold_shared` off, `s.deep`; sw:12728). While the gate holds, their share of the cavern draw rises about 10x.
- (d) Under casts, resting species sit at `restfreq` 1 while in-cast species are cut to /10. The gate cuts the cast's advantage over resting species from about 50:1 to about 5:1, so it **amplifies cast leaks** while a cavern is at cap.
- (e) The trim removes at most one group per cavern per day (`cavern_trim_days` 1), at countdown 10. `trim_gated` empties a gated wave's source, which **reopens it** (acknowledged at sw:12651-12652).
- (f) Natives are counted (sw:12577), so the cap can already be exceeded at load.

**P3. The trim sends off the season's own cast after a turnover (a bug).** `cavernPass` counts dismissed groups in n (sw:12595-12601). `trimOne` treats only `grp.trimmed` as pending, and picks only `not grp.dismissed` residents (sw:12640-12656). After `castTurnover` dismisses off-cast cavern groups, n stays over the cap until they have walked out. So the trim sends off the oldest **in-cast** native or resident group (or an in-cast gated wave) once a day until then. Likely fix: count `grp.dismissed` as pending in `trimOne`.

**P4. Field: cavern lead time (a species arriving about 28 t after a change).** Three parts of the code explain this; the code cannot prevent the first.
- (a) The change lands at the boundary tick, plus up to 10-120 t of retry while DF has not turned `cur_season` (sw:4117-4119).
- (b) DF can deliver a wave whose species it picked before the FREQUENCY change.
- (c) **`castTurnover` runs once per season stamp** (sw:12781). An off-cast group that arrives after the pass that made the turnover, whether a DF wave picked before the change or a FREQUENCY-1 leak (about 15%, sw:3681), is never sent off that season. It also occupies a cavern cap slot.
- **Suggestion**: make the turnover a standing rule (any off-cast tracked group, any pass), not a one-shot.

**P5. Field: minks drowning loop (water balance x20).**
- (a) **Every swimmer enters at the deepest full-water tile.** `V7.WAT.colTile` walks a column from the bottom up and returns the first 7/7 tile (sw:7043-7054; runs store `bottom*1024 + top`, sw:6548). No check asks whether the species breathes water.
  - `MODEL.habitat` calls a species "semiaquatic" if it breathes water **or** if all its raw biomes are water (sw:1901-1902).
  - So an air-breathing semiaquatic with a lake or river feature entry is a Driver B candidate (sw:5978) and is placed on the bed of the deepest column.
- (b) When those animals die, the census sees an empty predator level, because it counts living units only (`WILD.onMap`; sw:6313). `V7.WAT.mix` then boosts the same species: balance up to `balance_cap` 4 (sw:6417), pyramid `((13+1)/(0+1))^0.5 ≈ 3.7` for a missing C level (sw:6425-6427), pull up to 4 with prey present (sw:6432). The product is clamped to `mix.cap` = **20** (sw:6438).
- (c) No record of deaths, drowning or failed survival feeds back. `retry_days` applies only to empty draws (sw:9322-9325).
- **Suggestion**: place air-breathers at the top tile of a column, or on the shore.

**P6. The reserve is thrown away when a refund beats the apply (a bug).** In `applyLive`'s in-season branch, `res[id] = nil` runs unconditionally (sw:3049). The reserve is restored only when `quantity <= 0`. If DF refunds a departing animal to an out-of-season entry in the up to 300 t between the last hold and the change that brings the species back in season, the entry is > 0. The stored reserve (possibly thousands, e.g. "cavies 5,191", sw:2977-2978) is then discarded and the entry keeps only the refund. The same pattern is in `exhaustCheck` (sw:3175-3181) and `spillCheck` (sw:7406-7411).
- **Suggestion**: add the reserve to the live quantity instead of discarding it.

**P7. A cavern raw changed between daily passes is not re-asserted.** `CAVERN.apply` runs at the turn and daily only (sw:4107, sw:4142). Two cases:
- A cavern **stand-in** (exhaustion) stays held up to a day.
- With `restfreq 0`, when the gate newly holds a resting natural species it writes `holdFor` = 1 over the 0 (sw:12695-12696, sw:12755), until the next daily pass.

**P8. A season turn that errors in the daily job kills rotation for the season.** `tick` calls `V7.ST.turn` without a pcall (sw:4139); `V7.ST.now` and the groups fallback do pcall it. An error trips the daily job's fuse, which cancels it: no daily holds, no `CAVERN.apply`, no timer, no registry rescan, no apex scheduler. Meanwhile `lastSeason` was already set as the turn's first statement (sw:4094), so the groups-pass fallback will not retry. `appliedStamp` was never set either, so exhaustion is off all season.

**P9. Disable leaves the world held.** No disable, off, All off or unload path restores population quantities or extinct flags (section 7.3). Every out-of-season, inactive or resting entry stays at 0 and extinct in the saved world after `disable` or `off`; the stock is only in the tool's `reserve` record. Raws reload clean; entries do not.

**P10. The cast season filter depends on classification timing.**
- `castPool` and `castReplaceOk` read `e.noSeason` from the memoized `classify`. With `seasons_own`, `V7.apply` clears the NO_<season> caste flags in the raws.
- Any path that empties `CACHE.class` while those writes stand makes the next `buildPool` reclassify with the flags already cleared: undo (`UNDO.after` sw:15985, then `enableSched` builds the pool before `V7.apply` restores, sw:15932), `extinct` toggles (sw:14381), the `v7` verb (sw:18683), and `roster set ap_vermin_mass` (sw:9267).
- After that, `noSeason` reads all false for the rest of the world session. Later `castYear` or `cast rebuild` calls cast species into seasons their raws forbid, and the filter is silently gone.

**P11. `CACHE.castTurnStamp` is never dropped** (absent from `CACHE.drop` sw:17078-17097). The comment promises "once after load" (sw:12775-12776). But loading a save, or another fort, in the same DFHack session and the same game year and season skips the turnover entirely, and off-cast natives adopted at load stay all season. `CACHE.grpAdoptAt` and `CACHE.watSpillAt` are not dropped either (milder).

**P12. Turnover-dismissed groups bias the clock.** `V7.GRP.observe` skips trimmed groups but not dismissed ones (sw:12372). Every season change feeds truncated stays into W, which pulls W down and shortens release gaps.

**P13. A pattern table that spans a season change can starve the new season.** The `follow` pattern, a coupling or a call snapshots every land entry and restores it later (`PATTERN.openOnly` sw:10272-10299, `endCoupling` sw:10535-10558). If the restore comes after the season's `applyLive`, newly in-season species go back to the snapshot's 0. Nothing refills them until the next change (`holdOutOfSeason` only zeroes), and `exhaustCheck` then calls them exhausted and promotes stand-ins. In the other direction the restore re-opens out-of-season entries until the next hold (≤ 300 t). The default `steady` pattern with coupling parked avoids this.

**P14. The reserve is keyed by vector position** (`tostring(r.i)`, sw:3038, sw:3081) with no race recorded. If `world.populations.all` is reordered or grows mid-vector (Add invasive writes the region master and needs a reload, sw:505-506), a remembered stock can be handed to another species' entry. `applyLive` checks the current row's race, but not that the reserve belongs to it. The coupling snapshot `g.exclusion.snapshot` has the same problem.

**P15. `enable` turns on the deep layer, contradicting R60.** `PANEL.fortOn` sets every Panel switch, including `deep` (sw:16011, sw:16102). This has three effects:
- `ROSTER.normalize` in `enableSched` (not cast-aware; only `fortOn` checks `castOn`, sw:16109 vs sw:15933) gives deep species one default season each, outside the casts;
- `holdOutOfSeason` and `CAVERN.apply` then rotate magma-sea species;
- under casts, `CAVERN.restLevel` applies to held deep species too (sw:3753), so `restfreq 0` can zero a deep raw.

The R60 comments ("the deep is never touched", sw:12319, sw:12590, sw:4898-4900) hold only for groups and placement.

**P16. Water caps and the mix are per body type, not per body.** Two lakes share `water:lake`'s count, cap, clock and census (sw:9294, sw:6318-6331). Cavern pools get no tool draws at all (sw:695).

**P17. Send-off relies on DF's leave path.** No teleport or removal. A dismissed school in an enclosed lake or pool has no edge to walk to; nothing in the code checks that it ever leaves, and it counts against the body's cap until it does.

**P18. Outside casts, flagged fish in a water feature are never tracked.** `gatedLayer` drops `feature_idx ~= -1` (sw:4354), and `adoptNatives` takes flagged units only under casts (sw:12815). With casts off these units "fell between the two" (sw:12809-12811): never counted and never led.

**P19. Exhaustion borrows are not given back on disable** (only spill is, sw:15972). A borrowed season stays in `assign` until the next season stamp. Low impact because `exhaustRoll` catches it later.

**P20. Small code-comment errors.**
- `CAVERN.restLevel`'s comment says the pool's vermin test "reads only GROUNDER, ROTTER and SOIL" (sw:3690-3691). `classify` also reads VERMIN_FISH, VERMIN_EATER and SMALL_RACE (sw:1801-1802).
- `exhaustCheck`'s comment still says the apply is "in the daily tick" (sw:3125). Since 34a3a4b it is usually the timer.

---

## 10. Where the docs disagree with the code

| Doc | Says | Code |
|---|---|---|
| HANDOFF.md:120 | `CACHE.release` **'7.1.0'** | `'7.2.0'` (sw:615); not bumped for the v7.3 work |
| HANDOFF.md:80 | Driver B "re-checks breathing one tick later" | The stranding guard is removed (sw:9482-9483) |
| HANDOFF.md:103-104 | the groups pass includes "the guard" | Removed. HANDOFF also lists only the daily job for season changes; v7.3 adds the timer and the groups-pass fallback (sw:4086-4132, sw:13210-13218) |
| HANDOFF.md:83 | 194 top-level locals | 196 top-level `local` lines now |
| docs/v7.1/groups.md:18 | "a failed draw backs off to gap_min_days" | `water.retry_days` (1 day) exactly (sw:9312-9325); water.md:35 has it right |
| docs/v7.1/groups.md:84-86 | trim sends off "the oldest resident group (natives first)" | Also the oldest **gated DF wave** when no resident is left (`cavern_trim_gated`, default on, sw:12649-12655, sw:801); groups.md never mentions `trim_gated` |
| PLAN.md:362 | groups at once "land 3, cavern 2" | land formula, cavern 5 (sw:3526-3537, sw:801) |
| Script header changelog (sw:158-497) | newest entry v7.1.0 | No v7.3 entry, although the usage text lists `cast` (sw:77-78) and v7.3 code is throughout |
| water-bodies.md:33 | the entry chooser takes "7/7 bottom first" | Matches the code. The doc gives no rule for air-breathers (P5) |
| Controls help ctl:95 | the cavern ceiling "holds new cavern arrivals" | True through `CAVERN.apply` (sw:3726-3734). `QUOTA.cavernThrottle` is dead code |

---

## 11. One season change, tick by tick (casts on, default settings)

T = the boundary tick (`cur_year_tick % 100,800 == 0`). Times are game ticks.

| When | Who | What |
|---|---|---|
| T - ≤1,500 | daily job | `V7.ST.arm`: a one-shot timeout for T (sw:4124-4128). The usual daily `holdOutOfSeason` and `CAVERN.apply` for the old season. |
| T - 300 … T | groups passes | Old-season holds every 300 t. Exhaustion and stand-ins for the old season. |
| T (+0…120) | timer → `V7.ST.now` | Retries every 10 t until DF's `cur_season` flips (≤ 12 tries). Then `V7.ST.turn`: `lastSeason = s`; `exhaustRoll` (stand-ins lose the season, resting ones rest again); `spillRoll`; **Winter→Spring: `castYear`** (new casts, saved); **`applyLive`** (old season's species and stand-ins zeroed into the reserve and set extinct; new cast refilled from reserve, snapshot or 100; `appliedStamp` set); announcement and `season` ledger line; trickle; **`CAVERN.apply`** (new cast open; resting held at `restfreq`; the gate's /10 holds stand). If the timer did not run, the next groups pass or daily pass makes the same turn. |
| T … T+28 (example) | DF | A wave picked before the change can still arrive (P4). |
| first groups pass after T (≤ 300 t; offset +31 mod 300) | groups job | `holdOutOfSeason` (new season); fallback turn if needed; **`exhaustCheck`** (now allowed: appliedStamp matches) promotes stand-ins for any new-cast key with 0 stock; reconcile; `discoverGroups` (`arrive` lines); `adoptNatives` (if 1,200 t have passed); **`castTurnover`** (every tracked off-cast group, natives included, gets countdown 0 and leaves on DF's path, still counted until gone); cohesion; land release (usually paused: dismissed groups still count); water step +3 t (one body); **`cavernPass`** (count includes dismissed groups, so it is over cap, the hold engages, and trim may hit in-cast groups, P3); irruption; save. |
| next daily pass (≤ 1,200 t after T) | daily job | `holdOutOfSeason` + `CAVERN.apply`; **`V7.WB.daily`**: the stamp changed, so a sliced water-body rescan starts (the old registry stays in use until the swap); `ROSTER.placeTick` (apex presence counters reset for the season, sw:8851). |
| T + days | groups passes | Dismissed groups leave and their stays feed W (P12); caps free up; the adaptive clock releases the new cast's waves (land and cavern) and Driver B draws new water groups. Arrivals of off-cast species after the turnover pass stay all season (P4). |
| every 3,000 t | ecology job | Relation writes follow the current cast's edges (`ROSTER.castEdgeSet`). |
