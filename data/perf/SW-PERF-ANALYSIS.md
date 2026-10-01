# seasonal-wildlife: performance architecture, memory, and what "parallel" can mean on DFHack

W2:Urist, 1 October 2026. Code and source review only. The rig was not started, no harness command was run, nothing
was edited or committed. Subject: `seasonal-wildlife` branch `v7.0` @ `1e65e03` (engine `scripts/seasonal-wildlife.lua`
8,125 lines; window `scripts/gui/seasonal-wildlife.lua`; web server `scripts/seasonal-wildlife-web.lua`). Platform source:
`GitRepos/dfhack-53.16-r2` @ `02e77acf1` (the build installed on the rig per `DwarfCron/data/dfhack-r2/REPORT.md`).
Line numbers are `engine:N`, `gui:N`, `web:N` for the three scripts, and DFHack paths are relative to the r2 tree.

---

## 0. Bottom line

1. **The scheduled jobs are not where the frame rate goes.** From the measured passes, the groups, ecology and daily
   jobs average about **1% of wall time** at 200 ticks/s (§2.2). That agrees with FPS2b, where the tool on vs off was
   within noise (+2%). Splitting that work across threads or ticks cannot buy back more than about 1%.
2. **What players feel is the spikes, plus three paths outside the jobs:**
   - groups passes of 67–149 ms and ecology passes of 58–71 ms, against a 50 ms budget;
   - the jobs share ticks: ecology always runs on the same tick as a groups pass, and all three coincide every 6,000 ticks;
   - **the map overlay** does a JSON decode and an O(M²) relation scan **on every render frame** (unmeasured, and possibly the largest single cost when it is on);
   - **the web snapshot**, every 2 s while the page is open;
   - **GUI edits**, which re-encode the undo ring (estimated at about 50 ms on the host at the full depth of 50, more on the rig).
3. **Where the cost comes from:** the Lua-to-DF wrapper allocates a new userdata on every struct-field step
   (`library/LuaWrapper.cpp:175-191`). Hot loops also repeat classification work that never changes within a world (for
   example, `ecologyClass` is uncached and runs for every unit, twice per ecology pass). The fixes are mostly caching and
   allocation discipline, not concurrency.
4. **The biggest frame-rate lever the tool controls is the number of units it keeps on the map.** DF charges about 0.07%
   per placed wild animal (fps-load-facts). With v7, sponge ribbons can add up to 8×16 = 128 units, and `layer_groups`
   allows sqrt(embark)+1 groups per layer, per water body and per cavern. That is a DF cost, not a Lua cost, and it
   needs its own experiment (PERF3).
5. **On "parallel processing", honestly:**
   - DFHack Lua is one shared `lua_State` on DF's simulation thread, under the core lock.
   - Coroutines give time-slicing, not parallelism.
   - A C++ worker thread is possible in principle, but it costs a per-release, per-OS binary. The real win there is native code, which needs no thread.
   - An external process is possible through the web socket, but no per-tick work is pure enough to move.
   - **The useful forms on this platform are:**
     - work avoided: caches, one census per pass, memoized classification;
     - work moved into native code: `forEachTile`, eventful's C++ unit diff;
     - work staggered and sliced: job phases, resumable surveys.

---

## 1. Platform constraints (verified in DFHack 53.16-r2 source)

| Constraint | Verdict | Where confirmed |
|---|---|---|
| Lua runs on DF's simulation thread under the core lock | Yes. Tick and frame timers run inside `Core::doUpdate` → `Core::onUpdate` → `Lua::Core::onUpdate` → `run_timers`. The simulation thread "pretend[s] … [it] has suspended the core" for the whole update. Every millisecond a job spends is a millisecond the simulation does not advance. | `library/Core.cpp:1632-1650`, `:1666-1682`; `library/LuaTools.cpp:2051-2088` |
| One Lua state for everything | Yes. `Core::State` is a single `lua_State*`. Every DFHack script, the overlay framework and the window share one heap and one GC. | `library/include/Core.h:364` |
| No OS threads for Lua | Correct. No DFHack Lua API spawns a thread. Lua code reaches DF memory only through the core lock: "Suspending is necessary for accessing a consistent state of DF memory… Every thread is allowed only one suspend per DF frame." | `docs/dev/Lua API.rst:688-698` |
| DF memory only with the core suspended | Yes. `CoreSuspender` / `CoreSuspenderBase` wrap `Core::CoreSuspendMutex` (a recursive timed mutex). The persistence getters and setters take it explicitly. | `library/include/Core.h:354, 378-400, 461`; `library/LuaApi.cpp:308, 323` |
| Coroutines | Available and cooperative on the same thread. `luaL_openlibs` opens `coroutine`. DFHack adds `dfhack.saferesume`, and `gui.script` already resumes coroutines from `dfhack.timeout` callbacks: a ready time-slicing primitive. | `library/LuaTools.cpp:1797`; `docs/dev/Lua API.rst:642-660`; `library/lua/gui/script.lua:29-60` |
| Scheduling | `dfhack.timeout(n, 'frames'|'ticks'|'days'|'months'|'years')`. A day is 1,200 ticks. Tick timers key on `world->frame_counter`. Everything except frames is cancelled at world unload. `repeat-util.scheduleEvery` runs the callback **immediately**, then re-arms at `frame_counter + delta`, so it does not drift. | `library/LuaTools.cpp:1940-1985`; `docs/dev/Lua API.rst:3806-3816`; `library/lua/repeat-util.lua:36-49` |
| Lua version and GC | **Lua 5.3.6.** **Incremental GC only**: `lua.h` defines `LUA_GCSTOP` … `LUA_GCISRUNNING` but no `LUA_GCGEN`/`LUA_GCINC`. Defaults are pause 200%, stepmul 200. DFHack never calls `lua_gc`, and nothing in `library/` or `plugins/` calls `collectgarbage`. | `depends/lua/include/lua.h:19-21, 301-309`; `depends/lua/src/lstate.c:31-36` |
| Timing | `dfhack.getTickCount()` is `GetTickCount()` on Windows (our CrossOver build) and `gettimeofday` elsewhere, in milliseconds. `os.clock` is the C `clock()`. **Native per-repeat accounting already exists:** `repeat-util` calls `dfhack.internal.recordRepeatRuntime` after every repeat; `dfhack.internal.getPerfCounters()` returns `update_lua_per_repeat`, `overlay_per_widget`, `total_overlay_ms` and the rest; `script-manager.print_timers()` prints them; `dfhack.internal.resetPerfCounters()` starts a window. DFHack's own target is ≤10% CPU with every tool on. | `library/LuaApi.cpp:1381, 1409, 3997-4000, 4714-4741`; `library/Process.cpp:660-668`; `docs/Core.rst:439-470` |
| C++ plugin worker thread | Possible. `std::thread` is used by `RemoteServer` and by `rendermax`'s light renderer, which copies map data under its own mutexes and lights on `hardware_concurrency()` workers. A worker must never touch DF memory or the Lua state. It may only compute on data copied out under the core lock, with results applied on a later locked update. | `library/RemoteServer.cpp:252, 479`; `plugins/rendermax/renderer_light.cpp:108`; `plugins/rendermax/renderer_light.hpp:106-128, 245-277` |
| `dfhack.maps.forEachTile` (r2, documented as experimental) | One C++ call scans a tile cuboid block-major, clamped to the map, skipping unallocated blocks. **Filter** (all optional, every one must hold): tiletype set; material/shape/shape_basic/special/variant sets (inclusion only, so "not TREE" means listing every other material); `designation` and `occupancy` as named bit-fields compiled to a single `(whole & mask) == bits` test (**exact values only**, so `flow_size>=4` takes four calls or a Lua filter); an optional Lua `filter` function run last. **Actions:** `set_tiletype` (or a map), designation/occupancy set/clear, `construct` (buffered, merged sorted), and a Lua `callback(x,y,z,block,lx,ly,tiletype)` that may return `false` to abort. **Returns counts only**: `scanned, matched, changed, constructed, aborted`. No stride and no deadline. Each Lua filter or callback call pushes 7 arguments, including a fresh block userdata. | `library/include/modules/Maps.h:457-561`; `library/modules/Maps.cpp:1798-1925`; `library/LuaApi.cpp:2880-3125`; `docs/dev/Lua API.rst:2611-2690` |
| `getTileBlockCoord` / `getBlockOrigin` / `getTileBlockOffset` | Inline shifts (`pos.x>>4`, `<<4`). Convenience only, with no performance meaning. | `library/include/modules/Maps.h:358-362`; `library/LuaApi.cpp:2721-2731` |
| **Cost model for DF access from Lua** | **Every struct, compound or container step allocates a new full userdata** (`push_object_ref` → `lua_newuserdata` + `setmetatable`), with no per-pointer cache. `cache.rel_map[sa][sb].ur` makes 3 allocations, `blk.designation[lx][ly].outside` makes 3, and `u.animal.population.cave_id` makes 2. Primitive leaves (ints, bools) allocate nothing. This is the dominant garbage source in every hot loop below. | `library/LuaWrapper.cpp:175-191, 209-246` |
| Persistence | `dfhack.persistent.getSiteData`/`saveSiteData` = pure-Lua JSON (Jeffrey Friedl's `JSON.lua`). It encodes **pretty** with a tab indent by default, aligns keys, and **always sorts object keys**. `saveSiteDataString` and `getSiteDataString` are exported for a caller that wants compact JSON. | `library/lua/dfhack.lua:793-820`; `library/lua/json.lua:7-17`; `library/lua/json/internal.lua:1443, 1629-1636`; `library/LuaApi.cpp:382-383` |
| Event hooks | `eventful.onUnitNewActive`/`onUnitDeath`, gated by `enableEvent(type, freq)`. The smallest frequency registered by any tool wins. The new-active check is a C++ `unordered_set` diff over `units.active` (`EventManager.cpp:732-752`). Units already present at load are seeded without events (`:379-382`). | `plugins/eventful.cpp:98-99, 278-297`; `docs/dev/Lua API.rst:7382-7390` |
| Overlay | Widgets run inside DF's viewscreen `render` interpose (every frame) and are charged to `total_overlay_ms` / `overlay_per_widget`. `overlay_onupdate` is throttled by `overlay_onupdate_max_freq_seconds` (default 5). | `plugins/overlay.cpp:57-73, 106-108, 234`; `plugins/lua/overlay.lua:444-464, 611-618` |

Two consequences shape everything below:
- **Garbage is shared.** The tool's garbage is collected in incremental steps charged to whatever Lua allocates next: another tool, the overlay or the window. Part of the tool's GC cost is therefore invisible to `FUSE`.
- **Clock granularity.** `GetTickCount` under Wine: the X1 job stats cluster at 0/16–17/33/49–50/66–67 ms (with some 35/36/41), so per-pass "0 ms" means "under one clock step". Sums from the native perf counters average this out; single-pass readings do not.

---

## 2. Map of periodic jobs and heavy paths

### 2.1 Every periodic or recurring path, ranked by expected cost

Notation: U = `units.active`; W = wild units on the map; M = wild units holding an enemy slot; P/T = predators and targets in the ecology pass; R = managed population rows (`CACHE.managedPops`, a few hundred); N = all of `populations.all` (7,606 on the trial fort); C = creature raws (about 1,054 vanilla); K = water candidate keys; Tw = cached water tiles (≤3,000); S = scavengers (≤40); Rm = remains items.

| # | Path | Cadence | What it iterates | Complexity | Measured | File:line |
|---|---|---|---|---|---|---|
| 1 | **Map overlay** `GroupsOverlay:onRenderFrame` (opt-in, `default_enabled=false`) | **every render frame** (about 50/s) | `groupsStatus()` → `loadGroups()` **JSON decode** + a string per group; member `df.unit.find`; `ecoLivePairUnits(60)`: walk U with `WILD.onMap`, then pairs of M reading `rel_map` both ways (6 userdata per pair), plus a table per related pair | O(U + M²) per frame, plus decode | **unmeasured** | engine:7179-7217 → 6241, 3496, 4341-4361 |
| 2 | **groups job** `groupsJob` → `groupsTick` | 300 ticks | `loadConfig` deep copy (669); `loadGroups` decode (3496); `holdOutOfSeason` O(R) (2443); `ROSTER.exhaustCheck` O(R), plus **`buildPool`** (O(N + C)) when a stock runs dry (2491-2530); `reconcileGroups` id finds (3529); `PATTERN.trickleApply/sizeApply/dawnStanding` (dawn → `openOnly` → `buildPool` + O(N), 5692); `discoverGroups` O(U) (3546); `applyCohesion` + `cohesionLabel` raw scan per group (5906, 5857); `stuckSweep` (6004); coupling start on a prey arrival: `buildPool` + O(N) + O(C) (3630); `ENGINE.tick` → `V7.waterTick`: per due body a `WILD.countByLayer` O(U) and `ENGINE.draw` → `ENGINE.candidates` **O(K×Tw)** (5422, 4839); `V7.spongeTick` daily (5529); land gate `countByLayer` O(U); cavern gates; `IRRUPT.tick` O(U) if on; **`saveGroups` encode** (3505) | typical O(U + R), spikes O(N + C + K×Tw) | X7/X1: runs 655, **worst 67 (v6.3), 149 ms (v6.4)**, 5–10 passes over 50 ms; typical "last" 0–17 ms; validator (1 Oct) 0 ms | engine:3393, 6129-6239, 6258 |
| 3 | **ecology job** `ecologyJob` → `ecologyRun` | 1,500 ticks (`cfg.ecology.cadence`) | `loadConfig`; `loadGroups` decode; `ecoClearDeparted` (U walk with fb_safe, plus 2×500 cell writes × 3 userdata per departed slot) (4110); predset cached by `CACHE.ver`; U walk through `ecoIsPredator`/`ecoIsTarget`, **each calling `V7.natural` → `ecoOf` → uncached `ecologyClass`** (about 10 caste-flag scans and a `why` table) (4074-4090, 1665, 1163, 1073); `ecoWrite` **P×T pair evaluation with no budget** (`ecoToken` = `creature_raw.find` per pair, `MODEL.reaches`), writes budgeted at 30 ms (4155-4245); `V7.sweep` U walk (`managedWild` → `ecoOf` again), then O(M²) ≤ 20 ms (4264-4313); `ecoNudge` O(P×T) (4425); `V7.soloUnits` O(U) (6485); `saveGroups` encode | O(U·c_class + P×T + M²) | **worst 58–71 ms** (X1 runs 138–139, 2–5 over budget); typical 0–18; validator 5 ms | engine:5604-5612, 4450-4485 |
| 4 | **web snapshot** (only while `seasonal-wildlife-web` serves) | poll every 5 frames (non-blocking accept); snapshot at most every 2 s; `poolAndPairs` rebuilt every 30 s or on a config change | `loadConfig` copy; `buildPool` (25–50 ms) plus an O(n²) `eats` pair table every 30 s (web:72-101); stock over R; `loadGroups` decode; U walk with `WILD.origin`; per pool species row: 3 × `hasCasteFlag` (caste walks), `whyFor`, `ODDS.weight`, gfx; `json.encode` of the whole snapshot | O(U + pool) per 2 s, plus O(pool²) per 30 s | self-reported `snap_ms` only (not in any run log) | web:35-36, 214-336, 422-442 |
| 5 | **daily roster** `tick` | 1 day = 1,200 ticks | `loadConfig`; at a season flip `applyLive` O(R) + `RESERVE.save` (2399); `holdOutOfSeason` O(R); `CAVERN.apply`: O(`cfg.allow` keys) + `countByLayer` O(U) + **`CAVERN.save` JSON every day, unconditionally** (3006-3071) | O(R + U) | validator 11 ms | engine:3369-3386, 7025 |
| 6 | **scavenging** (opt-in) `SCAV.run` | 200 ticks | U walk; every corpse item → `SCAV.edible` (`buildings.findAtTile`, `pcall` closures) (6811); for each scavenger × each remain: **`SCAV.wet` (a `getTileFlags` + pos table per pair)** (6839, 6929); `SCAV.line` with `getWalkableGroup` per tile, map-wide since `scav_mapwide` | O(U + Rm + S×Rm + S×dist) | unmeasured | engine:6862-6990 |
| 7 | **quiet alerts** (opt-in) `ALERTS.run` | **10 ticks** | `announcement_alert` (usually empty); the `FUSE.job` wrapper (`pcall`, stats, `LEDGER.flush`, `absTick`) is paid 120×/day | O(alerts) | unmeasured, presumably near 0 | engine:6754-6777 |
| 8 | **Live tab refresh** (on demand: tab open, R, any Live action) | user | `groupsStatus` decode; 2 U walks; **biomass: a walk of all N `populations.all` with `managedPop` per enabled layer (up to 4×N ≈ 30,000 calls)** instead of the R-row index | O(4N + 2U) | **78–101 ms** (X7: 84; validator 1 Oct: 78; budget 100) | gui:995-1105 (loop at gui:1079) |
| 9 | **window open / rebuild** | user | `buildPool` + `loadConfig` | O(N + C) | open 183 ms; `buildPool` 25 ms (validator), about 50 ms (STATE 95) | gui:563-572 |
| 10 | **every window edit** `Win:save` | user | `UNDO.push`: **decode the whole undo ring, append a deep-copied snapshot, re-encode it pretty** (760-770), then `saveConfig` (encode) and `loadConfig` (deep copy) | O(ring × cfg) | unmeasured on the rig; host benchmark in §2.3 | gui:558-562; engine:751-787 |
| 11 | Once per map, cached | first use after load | `getEmbarkRegions` (all blocks × 9 offsets) 44–100 ms (823); `CAVE.survey` 43 ms (3780); `WET.survey` (4515); `ENGINE.waterTiles` ≤1,000 ms deadline (4785); `ENGINE.deepColumns`; `V7.vegSurvey` ≤1,000 ms deadline (4978); `CACHE.managedPops` O(N) (2341); `ALERTS.humanoids` O(C) | O(map tiles) | as given | — |
| 12 | Once per world | first classification | `MODEL.rootOf`: `listdir_recursive` over `data/vanilla`, `installed_mods` and `mods`, reading every `creature*.txt` line by line (1238-1263); `classify`/`climate`/`rawBiomes` per raw (cached) | file I/O | unmeasured | — |
| 13 | Verbs | user | `place` (`PLACE.tiles` + one unit) 223–309 ms; `now` 25 ms; `status` 88 ms; `roster build` = `buildPool` + slots | — | STATE addendum 72 (STATE.md:3066-3069) | engine:3898-3946, 5177 |
| — | Retired jobs (`WATER.JOB`, `STOCK.JOB`) | cancelled at schedule (6275-6276) | — | — | X1: water 54–67 ms worst; **cavern placement 329–366 ms** (the reason it was retired) | — |

### 2.2 What the measurements add up to

- **Mean cost of the jobs at 200 t/s** (BOATS ran 206 t/s fresh), using the X1 typical "last" readings:
  - groups: about 8 ms × 0.67 passes/s ≈ 5 ms/s;
  - ecology: about 10 ms × 0.13/s ≈ 1.3 ms/s;
  - daily: 11 ms × 0.17/s ≈ 1.8 ms/s.
  - **Total ≈ 8 ms per second of play, about 0.8%.**
  - This is consistent with FPS2b's "tool on vs off +2% (noise)", and well inside DFHack's 10% guideline.
  - The older E38 (v5.8, STATE addendum 70) found 10–12%, before W7 cut per-entry allocation (engine:916-921 records about 1.5 s of garbage per pass on the 54 MB heap).
- **The spikes are the user-visible part.** A 149 ms pass is about 30 ticks' worth of time at 200 t/s, a visible hitch.
- **Stacking.** `enableSched` schedules the daily job, then (via `scheduleGroups`) groups and ecology, all on one `frame_counter` (engine:7025, 6258-6260). `repeat-util` fires each immediately and re-arms at fixed deltas. So:
  - **ecology (1,500) always lands on a groups tick (300)**;
  - groups and daily coincide every 1,200 ticks;
  - scavenging (200) meets groups every 600;
  - all of them meet every 6,000 ticks.
  - The worst single tick is therefore the **sum** (groups 149 + ecology 71 = 220 ms is possible). `FUSE` times jobs, not ticks, so it cannot see this.

### 2.3 Host benchmark of DFHack's JSON on the tool's real site data

Measured off-rig, with the r2 `json/internal.lua` on host Lua 5.5 (arm64 native, so faster than DF's x86 Lua 5.3 under
Rosetta and Wine). The data is the tool's own records from the rig's latest autosave
(`…/save/autosave 3/dfhack-entity-288.dat`, 1 Oct 05:35). `undo50` is that ring filled to its v6.5 cap of 50. The
benchmark script is in this session's scratchpad (not kept). It measures **relative cost only**; the rig multiplier is
unknown, and W7's note of 65 ms per config decode on the trial fort suggests ×10 or more.

| record | bytes (pretty) | decode | encode pretty | encode compact | allocation, decode+encode |
|---|---|---|---|---|---|
| groups | 11,944 | 1.18 ms | 0.78 ms | 0.66 ms | 60 KB |
| config | 21,082 | 2.46 ms | 0.98 ms | 0.88 ms | 72 KB |
| ledger | 31,268 | 3.23 ms | 1.60 ms | 1.37 ms | 100 KB |
| undo (10 deep today) | 66,337 | 6.82 ms | 3.08 ms | 2.81 ms | 320 KB |
| undo at 50 | 374,911 | **34.3 ms** | **15.8 ms** | 13.7 ms | **2.1 MB** |

What this shows:
- **The groups record (decoded 5–7 times per second while the overlay is on, otherwise twice per groups pass) is small but
  not free.** About 2 ms of host time per decode/encode round trip, and 60 KB of garbage each time.
- **The undo ring is the outlier.** Every window edit pays one full decode and one full encode, about 50 ms on the host
  at depth 50, and that is before the deep copy, `saveConfig` and `loadConfig`. The live saves show the ring at 10
  snapshots (6.6 KB each). It will reach 50 as users edit.
- **Compact encoding saves only about 10–15% of encode CPU.** It saves more in size: groups 11.9 KB pretty becomes
  8.8 KB compact; undo 66 KB becomes 52 KB. The real win is not decoding at all.
- **Save footprint today:** undo 66 KB, ledger 31 KB, config 21 KB, groups 11–12 KB, reserve 5 KB, about 136 KB of
  the tool's site data in the save. That rises toward about 450 KB as the undo ring fills.

---

## 3. Memory

### 3.1 Allocation hot spots (per tick, pass or unit)

1. **DF wrapper userdata on every struct step** (`LuaWrapper.cpp:175-191`). The worst offenders:
   - `rel_map[a][b].ur` in `ecoWrite` (engine:4233), `V7.sweep` (4291-4293), `ecoClearDeparted` (4134: **3,000 allocations per departed slot**), `ecoLivePairs`/`ecoLivePairUnits` (4331, 4354);
   - `u.animal.population` read **before** the cheap flag test in `gatedLayer` (3512), on every active unit every groups pass;
   - `des[lx][ly]` in every survey (3800, 3920, 4801, 5003);
   - `pop.population` twice per entry in `managedPop`/`layerOf` (900-929).
2. **Uncached classification inside unit loops.** `ecologyClass(craw)` (1073) runs up to 10 `hasCasteFlag` scans (each walks the castes) and builds a `why` table. It is reached through `ecoOf` (1163) from:
   - `V7.natural` (1665), for every active unit in `ecoIsTarget` (4080, which reaches `V7.natural` before the citizen test) and for every wild unit in `ecoIsPredator`;
   - `V7.managedWild` (4254) in the sweep.
   
   That is about 2–3 `ecoOf` calls per unit per ecology pass. `cohesionLabel` (5857) rescans castes for every group every 300 ticks, and so does `hasCasteFlag(craw,'FLIER')` in `stuckSweep` (6009).
3. **Closures per call.**
   - `WILD.invader` creates a `pcall(function() … end)` closure on every call (2772), and it sits under `WILD.onMap` (2775), which every unit walk uses.
   - `V7.natural` (1675-1679) and `V7.leaderOf` (5893) do the same.
4. **`loadConfig()` deep-copies the whole config** (669-675: about 2–3k table entries, roughly the 21 KB record) on every groups, ecology and daily pass and every web snapshot. `ALERTS.run` and `SCAV.run` already read `CACHE.cfg` directly (6755, 6863).
5. **Groups record decode and encode** (3496, 3505) on every groups pass, every ecology pass (5607-5611), every web snapshot (web:228), **every overlay frame** (7181 via 6241) and every Live refresh (gui:999).
6. **Per-pass scratch tables:**
   - `ecoWrite`'s `allow` (2 entries per allowed pair, 4219), `realm`, `dom`, `packN`;
   - `stuckSweep` makes a new `{x,y,z,since}` record and a `tostring(id)` for every moved unit (6011-6016);
   - `discoverGroups` formats `srcKey` twice per gated unit (3552-3553);
   - `ENGINE.candidates` builds a tile array per candidate from all Tw tiles (4859);
   - `liveMembers` sorts a fresh array per group (5865).
7. **`buildPool`** (1746-1805) builds hundreds to over a thousand entry tables of about 45 fields each, plus `biomes` and `affinity` subtables, on every call. It has about 25 call sites. Only `ecoPredatorSet` (4057) and the web server (web:72) memoize it.
8. **Overlay:** a string per group and a 3-table record per related pair, **per frame**.
9. **`SCAV`:** `SCAV.wet` makes a position table and a flags userdata per (scavenger, remain) pair; `SCAV.line` makes one per path tile.

### 3.2 Caches and their lifetimes

All shared caches live in `_G.__seasonal_wildlife_cache` (engine:439-445), keyed by release `7.0.0`, per [[dfhack-script-copies]].

| Cache | Key / invalidation | Lifetime | Bound |
|---|---|---|---|
| `CACHE.cfg`, `CACHE.ver` | `saveConfig` bumps `ver` | dropped on map load/unload (7140) | one config |
| `CACHE.region`, `CACHE.regionNum` | site id + map size; `regionNum` is weak-keyed | map / process | tiny |
| `CACHE.class`, `climate`, `rawBiomes`, `animalRoot`, `rawByToken`, `spongeRace` | per raw | world (dropped on world unload, 7144) | C |
| `CACHE.depth` | cave_id | **never dropped by `CACHE.drop`.** Re-created only when a copy re-runs its main chunk (891) | small; **stale across a world switch without a script reload (correctness)** |
| `CACHE.pops` (managed index) | `#populations.all` + regionSet | map | R |
| `CACHE.predset`, `ecoByTok` | `CACHE.ver` | map | pool |
| `CACHE.ecoDone` | slot pair → unit pair; cleared every 8th pass (`ECO.REFRESH`) and on load | map | ≤ P×T (≤ 250k slots in theory) |
| `CACHE.ecoAllow` | rebuilt every ecology pass | pass | 2 × allowed pairs |
| `CACHE.sweepSeen/At/Pass/Log` | pruned after `ECO.REFIGHT` passes | process (not dropped on load) | cleared pairs |
| `CACHE.ledger` | write-through; `LEDGER.CAP` 300 | map | 300 lines (~31 KB) |
| `CACHE.reserve`, `cavsnap`, `cave`, `wet`, `wtiles`, `deepCols`, `veg`, `align`, `call` | — | map | small; `wtiles` ≤ 3,000 tiles |
| `CACHE.fuseStats` | job and lap names | process | about 20 names |
| `CACHE.trickle`, `gsize`, `hunt`, `curious`, `gobble`, `humanoid`, `scav` | per species | world, or **never** (`scav` keyed by token, not dropped) | C |
| `CACHE.v7raw` (undo closures) and `CACHE.v7units` (`'id:tag'` keys) | append on every unit skill write or visit (6421, 6453-6457) | until `V7.restore`/unload | **grows with every solitary or pack hunter that arrives in a session** (closures plus strings; slow but unbounded within a session) |
| `_G.SW_WEB` (`W.poolCache`, `W.snapText`) | `CACHE.ver` + 30 s; 2 s TTL | process | one pool and one snapshot string |

Per-copy state **outside** CACHE (each script copy has its own):
- `raceCache` (2316): `CACHE.drop` resets only the copy whose `onStateChange` handler is registered, so **other copies keep race indices from the previous world (correctness)**;
- `flagKnown` (973);
- `SCAV.wait` and `SCAV.fallbacks` (6802): **`wait` never drops units that left the map**;
- `WILD.field`, `ENGINE.stagnant`, `lastSeason` (3367).

Persisted records and their bounds:
- ledger: 300 entries;
- **undo: 50 snapshots, about 375 KB pretty at the alpha fort's snapshot size**;
- groups: bounded by tracked units (`stuck`, `ecology.slots` and `far_since` are pruned per pass, 6021, 4135-4136);
- config: grows with `why` strings, one per key;
- reserve: per entry index.

Every one of them is re-serialized into the save at each DF save.

### 3.3 GC behaviour and recommendation

- The tool never calls `collectgarbage` (none of the three scripts do), and DFHack never tunes the GC. So it is Lua 5.3
  incremental with pause 200: a cycle starts when the heap doubles. On the 54 MB heap of engine:921 that is around
  108 MB. Each allocation pays GC debt at stepmul 200.
- The tool's garbage is mostly paid inside its own passes (allocation debt), with the rest landing on the next Lua
  allocator: overlay, window or other tools.
- **Do not** call `collectgarbage('collect')`. A full cycle on a 50–100 MB shared heap is a stall of tens to hundreds of
  milliseconds, and it collects every tool's garbage.
- **Do not** change `setpause`/`setstepmul`. They are global to all of DFHack's Lua.
- **Do** measure allocation per pass. `collectgarbage('count')` before and after inside `FUSE.job` (engine:3451) gives
  a net figure (a lower bound when a step runs mid-pass). An exact figure can be taken in a probe that brackets one pass
  with `collectgarbage('stop')`/`'restart'`.
- **Optional, after the allocation cuts:** a `'frames'` timer that runs `collectgarbage('step', k)` only while
  `df.global.pause_state` is set. That pays the shared GC debt during paused time, which DFHack's perf doc counts as
  free for game speed (`docs/Core.rst:455-460`). Small benefit, low risk, and it affects everyone's garbage. Treat it as
  an experiment, not a default.

---

## 4. "Parallel processing" options, assessed for this platform

| Option | What it can do here | Benefit | Cost and risk | Verdict |
|---|---|---|---|---|
| **(a) Time-slicing with coroutines** (`FUSE.slice`: resume under a per-tick ms budget, re-arm with `dfhack.timeout(1,'ticks')`, total deadline still trips) | Load-time surveys (`CAVE.survey`, `ENGINE.waterTiles`, `V7.vegSurvey`, `getEmbarkRegions`); `buildPool` when a job needs it (exhaust, dawn, coupling); the population sweep in `startCoupling`/`openOnly`; `ROSTER.build`. Ecology already slices by hand (`ECO.BUDGET_MS` deferral, 4162; `CACHE.sweepAt` resume, 4281). | Cuts the **worst tick**, not the mean: a 150 ms chunk becomes 5 × 30 ms. | **Never hold a DF userdata across a yield.** A unit can be freed between ticks, which risks a crash, not just stale data. Hold ids and indices and re-resolve with `df.unit.find` and `populations.all[i]` (append-only, so indices stay stable). The world can unload mid-coroutine: abort on `SC_WORLD_UNLOADED`. Results can be one or more ticks stale. It fits the fuse design as `FUSE.job` per slice plus a total-wall deadline plus a slice-count cap. | **Yes, narrowly**, for load-time surveys and any work left over after the caching fixes. Not for the 300-tick groups pass, whose typical cost is already small. **v7.2.** |
| **(b) Native bulk calls** (`dfhack.maps.forEachTile`, r2) | Replaces the Lua tile loops in `V7.vegSurvey` (4978-5020: **two count-only calls, no Lua per tile**), `WET.survey` (4515-4560) and `CAVE.survey` (3780-3825: four 1-tile-thick edge boxes in place of 256 tiles per edge block), `ENGINE.waterTiles` (4785-4828: `designation{outside=true,liquid_type=false,flow_size=k}` for k=4..7, callback per water tile), and `PLACE.tiles` (3898-3946: a count-only call per z to find the first level with room, then gather). **Not** `getEmbarkRegions` (already per block, 846-856) or the ring searches (`groundTile`/`waterTile` rings at 4397-4423, `SCAV.fallbackMove`, `V7.floorAt`), which need nearest-first order. | Load time and verb latency (for example `place` at 223–309 ms). **Not steady-state FPS**: these are cached per map. | Feature-detect (`if dfhack.maps.forEachTile`) and `pcall`, falling back to the current loop. Exact-match filters only. Callbacks still allocate a block userdata per call, so keep callbacks to matched tiles. Full detail in `DwarfCron/data/dfhack-r2/REPORT.md` §3.1. | **Yes.** **v7.2** (the edge-only Lua rewrite of `WET`/`CAVE` gets most of the gain on r1.1 too). |
| **(c) External process** (host Python, the web socket or RPC) | Pure, deterministic functions of raws + config + embark: roster build, ladder, species model, food-web pairing. `roster2.py` already is one ("a pure function of its arguments plus the static species table", roster2.py:3-5). | **None at runtime.** These run on demand (verb or window) and are already cached per world (`CACHE.class`). The per-tick work reads and writes live DF memory (`rel_map`, unit flags, population quantities) and must stay in-game. | A Python dependency on players' machines, an IPC protocol, and two implementations drifting apart. | **No for runtime.** Keep `roster2.py` as a design oracle and a parity test: diff its output against `ROSTER.build` on the same embark. |
| **(d) C++ plugin with a worker thread** | Copy unit records (id, race, pos, slot, flags) and the pair rules under the lock in `plugin_onupdate`; evaluate pairs and nearest targets on a worker; apply the `rel_map` writes on a later locked update. The `rendermax` pattern. | The pair evaluation is a few thousand checks: microseconds in C++ **on one thread**. The gain is native code, not concurrency. | A binary per DFHack release (ABI) and per OS; a separate distribution channel from the scripts; races and staleness; a cross-compile toolchain for a Windows DLL from macOS. | **Not worth it.** If native help is wanted, upstream a generic single-threaded bulk API to DFHack instead (the `forEachTile` route): for example a units filter returning id arrays, or a bulk `rel_map` read/write. |
| **(e) Precompute at world or map load instead of per pass** | Memoize `ecologyClass` per raw, and per-race unit facts (natural?, token, cohesion label, flier, water) keyed by `CACHE.ver`. Bucket water tiles by (body, salinity). Memoize `buildPool` by `CACHE.ver` + regionSet + `#populations.all` + layers. Persist the `MODEL.rootOf` map (raw-file scan, 1238-1263) to `dfhack-config` keyed by DF version + mod list. Cache static web species fields per world. | The largest steady-state saving available (proposals P1, P5, P8). | Invalidation discipline: raws per world, config per `ver`. A shared memoized pool must be treated as **read-only** (audit callers that mutate entries, for example `ENGINE.candidates` sets `e.habitat` on a `MODEL.entry` result, 4857). | **Yes.** v7.1 for the memos, v7.2 for the pool. |
| **(f) Event-driven instead of rescans** | `eventful.onUnitNewActive` (a native C++ diff) feeds the arrivals that `discoverGroups` scans for, and keeps a set of wild ids so the census walks only W, not U. `onUnitDeath` prunes. | Cuts the U walks (about 4 userdata per unit per walk) to W walks. The ecology write already remembers pairs (`ecoDone`); new pairs could be evaluated only as new × existing between refreshes. | No "left the map" event (keep the id-find reconcile, which is cheap). Units present at load are not reported (`EventManager.cpp:379-382`), so seed with one scan. Another tool can force a smaller global frequency. The handler is keyed by name, so register one shared handler with state in CACHE. Population quantities have no event (the hold stays polling, which is cheap on the R index). | **Yes, after the census (P4).** **v7.2.** |

---

## 5. Ranked proposals

How the savings were estimated:
- **Allocation counts** come from the code paths above, priced at roughly 0.5–1 µs per wrapper push on the rig. The r2 report puts these crossings at "roughly microseconds each".
- **Measured job times** are the X1/X7 FUSE stats and the validator of 1 Oct.
- **JSON costs** are the host benchmark in §2.3. The rig multiplier is unknown.

All of these are estimates to be confirmed by the experiments listed with each proposal.

| Rank | Change | Expected saving | Risk | How to measure (2 reps per arm) | Release |
|---|---|---|---|---|---|
| **P0** | **Instrument first:** (1) `FUSE.job` records KB allocated per pass (`collectgarbage('count')` delta) beside ms; (2) a per-tick total (sum of all job ms on one `frame_counter`, worst kept); (3) a `perf` verb printing `dfhack.internal.getPerfCounters()` rows for the tool's repeat names and the `seasonal-wildlife.groups` overlay. | None. It makes every other row measurable without quantization. | Negligible (one `count` call per pass). | Part of every experiment below. | v7.1 |
| **P1** | **Memoize classification for unit loops:** `ecologyClass` per raw in CACHE (world lifetime), and a per-race record `{token, eco, natural, cohesion, flier, water}` keyed by `CACHE.ver`. Unit-specific branches stay per unit: unclassified-but-domestic and undead (1673-1679). `ecoToken`, `V7.natural`, `V7.managedWild`, `cohesionLabel` and `stuckSweep`'s flier test all read the memo. Also precompute each target's token and entry once per pass in `ecoWrite` (the `realm[]` pattern at 4169-4172). | **Ecology:** about 2–3 `ecoOf` per unit × about 40–60 wrapper allocations each, removed. For 300 units that is roughly 35–55k allocations, an estimated 20–50 ms of the 58–71 ms worst pass. Typical pass to under one clock step. **Groups:** `cohesionLabel` per group per pass. | Low. These are pure functions of raws + config. Invalidate on `ver` and world unload. | **PERF0 bench:** one RPC per rep on BOATS, `ecologyRun(cfg,g)` ×10 timed and KB counted, v7.0 vs patched (2 fresh DF processes each). **PERF1:** a season on BOATS, v7.0 vs v7.1, perf-counter ms per 1,000 ticks for `seasonal-wildlife/ecology`, plus FUSE worst and over. | v7.1 |
| **P2** | **Keep the groups state in the shared CACHE** (as W7 did for config, ledger and reserve). `loadGroups` returns `CACHE.groups`, and `saveGroups` writes through **compact** (`dfhack.persistent.saveSiteDataString(KEY, json.encode(g,{pretty=false}))`) and only when the pass changed something. Move `stuck` and `ecology.far_since` (positions and timers) out of the persisted record. **Same treatment for the undo ring:** hold it in CACHE, push in memory, persist compact, and consider persisting only the newest 10 while keeping 50 in memory. | Removes a decode from every groups and ecology pass, every web snapshot, every Live refresh and **every overlay frame**: about 1.2 ms host (×rig factor) and 60 KB garbage each time. Undo push at depth 50: about 50 ms host → about 3–5 ms (in-memory append + compact encode), roughly 10× on the rig. Smaller saves. | Medium. Every reader and writer must go through the one table: the window's hold and dismiss (gui:1141, 1146) already use `saveGroups`. Drop it with the map (`CACHE.drop`). Durability is unchanged because writes still go through on each pass. | PERF0 bench: `loadGroups()` ×20, `saveGroups(g)` ×20, `UNDO.push` at depth 50 ×5, before and after. PERF1 (as P1) for the groups-pass ms and KB. | v7.1 |
| **P3** | **Overlay renders from a cache:** compute the marker and link list in `overlay_onupdate` with `overlay_onupdate_max_freq_seconds = 1`, from `CACHE.groups` (P2) and a pair list refreshed by the ecology pass (`ecoLivePairUnits` already exists; store its result in CACHE when ecology runs). `onRenderFrame` only paints. | Today, per frame: a decode, plus an O(M²) scan with 6 wrapper allocations per pair. Rough figures: M=30 is about 2.6k allocations per frame, M=100 about 30k (an estimated 15–30 ms per frame, which would cap the frame rate on its own). After: about 0. | Low. Links can be up to 1 s or one ecology pass old. | **PERF2:** BOATS, 10,000 ticks, arm A overlay off and arm B overlay on, first on v7.0 and then on v7.1. Read `overlay_per_widget['seasonal-wildlife.groups']` ms/s and stopwatch t/s. | v7.1 |
| **P4** | **One unit census per pass, plus the water draw by buckets.** Census: a single walk of `units.active` per groups pass gives counts by layer, gated units and wild units. `discoverGroups`, `WILD.countByLayer` (up to 6 calls a pass, including once per due water body at 5432), `CAVERN.apply` and `IRRUPT` all read it. `gatedLayer` tests `flags2` before reading `u.animal.population` (3512). `WILD.invader` reads the probed field directly with no closure (2772). Water: `ENGINE.waterTiles` also returns buckets by `(body, salt)`; `ENGINE.candidates` takes the union of fitting buckets instead of filtering all Tw tiles per candidate (4859). | Census: up to 5 of 6 U walks per groups pass (about 4 allocations per unit per walk), an estimated 2–8 ms per pass at U≈300–600. Water: from K×Tw (10–30 × 3,000 = 30–90k `ENGINE.fits` calls plus K arrays) to O(K): **most of the 50–67 ms water-draw pass**. | Low. The bucket semantics must match `ENGINE.fits` exactly (brackish accepts both salinities). | PERF0 bench: `ENGINE.candidates(cfg)` ×20 on OCEAN or LAKE, and `groupsTick` ×10 with a body due. PERF1 for the groups worst. | v7.1 |
| **P5** | **Stagger the job phases:** start each repeat behind a one-shot `dfhack.timeout(offset,'ticks')` (for example groups +0, daily +75, ecology +150, scavenging +37) so no two heavy jobs share a tick. Keep the timeout id to cancel on disable; tick timeouts die with the world anyway. | Mean unchanged. Worst single tick drops from **sum to max**: ecology no longer lands on a groups tick, and the 6,000-tick all-jobs coincidence goes away (up to about 70 ms off the worst tick, from today's numbers). | Very low. Jobs only read the clock, so phase does not matter. | P0's per-tick worst, over PERF1's season, v7.0 vs v7.1. | v7.1 |
| **P6** | **Live tab biomass on the managed index:** replace the `populations.all` walk per layer (gui:1079-1089) with `CACHE.managedPops()` rows filtered by `r.layer`, and pool lookups by `r.key`. | Live refresh 78–101 ms → an estimated under 15 ms (removes about 30k `managedPop` calls). | Very low. | The validator's `w0.timing.tabs` (`refreshLive`), 2 runs before and after. | v7.1 |
| **P7** | **Jobs read `CACHE.cfg` read-only.** A `loadConfigRO()` returns the shared table. Only writers (`exhaustRoll`/`exhaustCheck` → `saveConfig`; verbs; window) take `loadConfig()`'s deep copy. Stop `CAVERN.apply` saving its snapshot when nothing changed (3063). | Removes a deep copy of about 2–3k entries from every groups, ecology, daily and web pass. Smaller in ms (validator `loadConfig` reads 0 ms), larger in garbage. | Low–medium. A job that mutates its config must copy first: audit `ROSTER.exhaustCheck` (2491-2530), which mutates `x.done` and `x.promoted`. | P0's KB/pass in PERF1. | v7.1 |
| **P8** | **Memoize `buildPool`** by (`CACHE.ver`, regionSet, `#populations.all`, enabled layers), returned read-only. Callers that need to edit get a shallow copy. Job callers: `exhaustCheck` promotion (2506), `PATTERN.openOnly` for dawn and call (5694), `trickleApply` (5745), `startCoupling` (3631). Window and web callers too. | Removes the 25–50 ms pool build from the groups-pass spikes (coupling, dawn, exhaustion: the probable source of the 149 ms worst). Window open 183 ms → about 130 ms on a warm cache. | Medium. Callers that mutate entries must be found and fixed. | PERF0 bench of `startCoupling`-like and `openOnly` paths; PERF1 groups worst. | v7.2 |
| **P9** | **Surveys via `forEachTile`** with feature detection and the Lua fallback: `vegSurvey` (count-only), `WET`/`CAVE` (edge boxes), `waterTiles` (flow 4..7 plus callback), `PLACE.tiles` (count per z, then gather). Also an edge-only Lua rewrite for r1.1. | Load time (the first pass after load) and `place` latency (223–309 ms → an estimated under 50 ms). No steady-state FPS change. | Low with the fallback. `forEachTile` is marked experimental. | PERF0 bench: each survey with `force`, ×3, r2 path vs Lua path (toggle by nil-ing the API in the probe). | v7.2 |
| **P10** | **Coroutine slicing (`FUSE.slice`)** for whatever is still heavy after P1–P8: load-time surveys, `ROSTER.build`. Ids only across yields. | Worst tick only. | Medium (staleness, unload mid-slice). | P0 per-tick worst. | v7.2 |
| **P11** | **eventful arrivals** (`onUnitNewActive`) plus a maintained wild-id set, so the census walks W, not U. Seed at load. | U walk → W walk. Gain depends on how many citizens and livestock there are relative to wild animals. | Medium (shared event frequency, missed events at load). | PERF1 with a busy fort (FPS3 +60 citizens). | v7.2 |
| **P12** | **Web snapshot:** cache static species fields (name, diet flags, ASCII, gfx) per world; build only the dynamic fields every 2 s; reuse the census; read P2's `CACHE.groups`. **Scavenging:** compute `SCAV.wet` once per remain, cache the `SCAV.edible` verdict per item id (re-checked every N passes), move `SCAV.wait` into CACHE and prune departed ids. | Web: an estimated 50–80% of `snap_ms` (unmeasured, so P0 first). Scavenging: from S×Rm tile lookups to Rm. | Low. | Web: `seasonal-wildlife-web status` reports `snap_ms`/`snap_worst`; 2 reps of a 5-minute page-open window. Scavenging: perf-counter ms for `seasonal-wildlife/scavenge`. | v7.2 |
| **P13** | **Unit count, the DF-side lever (measure before changing anything):** sponges (up to 128 immobile units) and `layer_groups` (sqrt+1 groups per layer, per water body and per cavern). | If DF charges sponges like other wild animals (about 0.07% each), 128 sponges cost about 9%: ten times all the tool's jobs together. Immobile units may cost less. | It is a design question, not a code risk. | **PERF3 (FPS7):** OCEAN fort, fresh DF per rep, 30,000 ticks, stopwatch t/s. Arm A is v7 defaults; arm B has `sponges off` and `layer_groups off`. Split the two only if A ≠ B. | v7.1 measure → v7.2 act |

**Not proposed:**
- Retuning the Lua GC globally.
- A full `collectgarbage` anywhere.
- A threaded C++ plugin.
- Moving any per-tick work to an external process.
- Slicing the 300-tick groups pass before the caching fixes have landed.

### Correctness notes found on the way (not performance; for the lead)

- `CACHE.depth` (891) is not cleared by `CACHE.drop` (7140), so a world switch in one DFHack session without a script
  reload keeps cave depths from the previous world.
- `raceCache` (2316) is per copy, and `CACHE.drop`'s `raceCache = {}` resets only the copy that owns the
  `onStateChange` handler. Other copies keep the old world's race indices. This is the [[dfhack-script-copies]] trap.
  It belongs in CACHE.
- `CACHE.scav` is never dropped (6804). It is keyed by token, so it is harmless unless the raws differ between worlds.
- `SCAV.wait` (6802) is per copy and never prunes departed units.
- r2's `dfhack.units.teleport` walks all of `units.active` on every call (`REPORT.md` r2 §2). The ring searches call
  `teleport` per candidate until one succeeds (4404, 4418, 6855); `groundTile` pre-checks occupancy, so
  it is usually one call, but each call is now O(U).

---

## 6. Shared experiment design

One design covers every timing claim. Pace follows [[two-reps-per-arm]], and every trap is from [[fps-load-facts]] and
[[experiment-readout-traps]].

- **PERF0, the bench probe (no time passes).** One RPC per replicate on a **fresh DF process** (process age costs up
  to 28%). Load BOATS (the alpha fort) or OCEAN for water. Call each target function N times in one Lua chunk and
  report ms per call (`dfhack.getTickCount` over N, to beat the clock granularity) and KB per call (GC stopped around
  the call). Arms: v7.0 vs the patched build, deployed as two script names so both run in the same process (for
  example `seasonal-wildlife` and a copy `sw71`), with the order reversed between replicates. Two replicates. Minutes
  of rig time.
- **PERF1, a season of play.** BOATS, 33,600 ticks (one month), or a full season if time allows, unpaused.
  `dfhack.internal.resetPerfCounters()` at t0. Read at the end:
  - `update_lua_per_repeat` for each tool repeat (ms per 1,000 ticks);
  - `FUSE.stats` (runs, worst, over);
  - P0's KB per pass and worst per-tick total;
  - stopwatch t/s (secondary; it is noisy for effects under 5%).
  
  Arms: v7.0 vs v7.1. Two replicates each, each on a fresh process. **Subject receipt** (per
  [[manifest-subject-receipt]]): every job's `runs > 0`, ecology wrote at least one pair, and at least one groups pass
  had a water body due. Otherwise the arm is vacuous.
- **PERF2, the overlay.** As PERF1 but 10,000 ticks with the overlay enabled (receipt: `overlay_per_widget` holds the
  widget name with ms > 0), v7.0 vs v7.1, plus one overlay-off arm on v7.0 as the floor.
- **PERF3 (FPS7), unit count.** As in §5 P13. The stopwatch rate is primary here, because the effect is in DF, not Lua.

Release fit:
- **v7.1:** P0–P7 (local, low-risk changes; one PERF0 + PERF1 + PERF2 cycle validates them together), plus measuring P13.
- **v7.2:** P8–P13 (structural changes and new APIs: the shared pool, `forEachTile` with fallback, coroutine slicing,
  eventful, web and scavenging rework, and any unit-count decision PERF3 supports).
