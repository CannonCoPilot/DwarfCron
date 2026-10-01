# DFHack 53.16-r2: what changed, what it does to our code, what to use

W2:Urist, 1 October 2026. This was a code-only review. The rig was not started, and nothing was committed in any repo.

- **Installed build:** `DFHack/hack/dfhack.dll` reports `53.16-r2-0-g02e77acf`.
  - The plugins `export-world-map`, `smooth-movement` and `stockflow` are present, and so are the scripts `devel/datamine` and `gui/export-world-map`.
  - `hack/init/onMapLoad.default.init` now ends with `lua require('quickfix').repair_site_id()`.
- **Source trees:**
  - `dfhack-53.16-r2` is at tag `53.16-r2`, commit `02e77acf1`. The core diff covers 214 files, +18,262/−4,416.
  - The `library/xml` submodule moved from `1dd01aad` to `63efa5f4` (47 commits).
  - The `scripts` submodule moved from `7549711a` to `5d5fb16b` (98 commits).
  - `dfhack-latest`, which is develop 2 commits past r2, only touches the git-describe build files. Nothing functional differs from r2.
- **Our deployed copies survived the upgrade:**
  - `Dwarf Fortress/dfhack-config/scripts/` still holds seasonal-wildlife (engine, gui, web), the cx-* probes and the chronicler scripts.
  - The deployed `seasonal-wildlife.lua` is byte-identical to `seasonal-wildlife@v7.0`.
  - The control-panel init files are empty, so nothing new is auto-enabled.

---

## 0. Bottom line

| Question | Verdict |
|---|---|
| Does r2 break anything in seasonal-wildlife v7.0? | **No.** Every API, global and structure field we touch is unchanged or changed in a way that matches how we use it (section 2). |
| Do we have to change anything? | **No.** One existing bug is worth fixing: `chronicler-bridge.lua:1784` reads `df.global.current_weather[2][2]`. That is the same lookup r2 fixed as broken in `World::ReadCurrentWeather`. Use `dfhack.maps.getCurrentWeather()` instead. |
| Behaviour changes that reach us | (a) `dfhack.units.teleport` now updates tile occupancy correctly, and each call scans every active unit. (b) `timestream` refuses to skip time while any unit has breathing trouble (drowning, beached aquatics, choking). (c) `stderr.log` is unbuffered on Windows. (d) `exportlegends` writes three extra files. |
| Is `modtools/create-unit` usable again? | **No.** The script is unchanged since 2025-02-09. Line 164 still reads `df.global.world.arena_spawn`, r2's df-structures has no such field (0 hits), and the docs still tag it `unavailable`. `dfhack.units.create` plus the six writes stays the only route. |
| Most useful new features | `dfhack.maps.forEachTile` (native scan of a block of tiles) for the vegetation, water, map-edge and placement scans. `dfhack.units.getBreathingState` as a check after aquatic placement or wading. The population exports from `exportlegends` and `export-world-map` for Chronicler and the eco desk. |

---

## 1. What r2 changed, read from the code

### 1.1 Lua API (`library/LuaApi.cpp`, `docs/dev/Lua API.rst`)

**`dfhack.maps.forEachTile(bounds[, filter[, actions]])`**
- New in r2. Registered at `LuaApi.cpp:3145`; the C++ is at `Maps.cpp:1834`.
- It scans a box of tiles in one native call.
  - **Bounds:** `{x1,y1,z1,x2,y2,z2}`, two positions, or six integers. The box is clamped to the loaded map, and unallocated blocks are skipped.
  - **Filter:** `tiletype(s)`, `material`, `shape`, `shape_basic`, `special` and `variant`, each one value or a list. `designation` and `occupancy` take tables of field name to an **exact** value. `filter` is a Lua predicate run last.
  - **Actions:** `set_tiletype` (one value, or a from-to map), designation and occupancy writes, `construct` (buffered, then merged into `world.event.constructions` in one sorted pass), and `callback(x,y,z,block,lx,ly,tt)`. Returning exactly `false` from the callback stops the scan.
  - **Returns:** `{scanned, matched, changed, constructed, aborted}`.
- It walks block by block. The docs mark it **experimental: "may change in future releases"**.

**Block coordinate helpers**
- `dfhack.maps.getTileBlockCoord`, `getBlockOrigin` and `getTileBlockOffset` are new (`LuaApi.cpp:3129–3131`).
- They are shift-and-mask helpers (`>>4`, `<<4`, `&15`). z is passed through unchanged.

**Weather**
- `dfhack.maps.getCurrentWeather([pos])` is new (`LuaApi.cpp:3136`, C++ at `Maps.cpp:999`).
  - It indexes `current_weather[biome_x − map.region_x/16 + 1][…]`, using the biome region of the given tile.
  - With no argument it uses the centre of the map.
- `dfhack.world.ReadCurrentWeather()` used to read `current_weather[2][2]` (r1.1 `World.cpp:156`).
  - In r2 (`World.cpp:158`) it calls `Maps::getCurrentWeather()` and returns a `df::weather_type`.
  - The docs call it deprecated, but it is still wrapped without a warning, so nothing is printed.

**Breathing**
- `dfhack.units.breathes(u)` is new (`LuaApi.cpp:2213`, `Units.cpp:559`).
  - It is true unless the unit's active caste has `NOBREATHE`. Curses can change it.
- `dfhack.units.getBreathingState(u)` is new (`LuaApi.cpp:2286`, `Units.cpp:2389`).
  - It returns a **number**: 0 = CANT, 1 = TROUBLE, 2 = FINE. No enum is exported to Lua.
  - FINE if the unit does not breathe.
  - CANT if `flags1.drowning` is set, or if the unit is losing a choke hold.
  - Otherwise it follows `flags2.breathing_problem` and `breathing_good`.

**`dfhack.units.isCitizen(u[,insane])` and `isResident(u[,insane])`**
- Moved from r1.1 `Units.cpp:143` and `:155` to r2 `:146` and `:161`.
- Both now reject dead units first.
- **Only the `include_insane=true` path changes.** In r1.1 the default path already excluded the dead, because `isSane` begins with `isDead(unit) ||` (r1.1 `Units.cpp:229`).

**`dfhack.units.teleport(u,pos)`** (r1.1 `Units.cpp:766`, r2 `:778`)
1. The source tile now comes from `getPosition(unit)`, so caged units are handled correctly.
2. Wagons (`EQUIPMENT_WAGON`) get their full 3×3 footprint.
3. The old tile's `unit` or `unit_grounded` bit is cleared **only if no other unit of the same kind (standing or prone) remains there**. r1.1 always cleared it, which could leave an occupied tile looking free.
4. To do that, it walks all of `world.units.active` on **every call**, building a set of occupied tiles.

**Other unit and persistence functions**
- `dfhack.units.setPathGoal(u,pos,goal)` (r1.1 `:977`, r2 `:1033`) only gains a NULL check.
  - The body is unchanged: if the goal changed, it sets dest and goal and clears `path.path`, and it copies that to a standard mount.
- `dfhack.units.create` and `isWildlife` (r1.1 `:997`/`:589`, r2 `:1054`/`:601`) have byte-identical bodies.
- `dfhack.persistent.getSiteData` and `saveSiteData` still call `World::GetCurrentSiteId()` (`Persistence.cpp:330`).
  - That function (`World.cpp:217`) now falls back to `plotinfo.main.fortress_site->id` when `site_id < 0`.
  - This fixes reclaimed forts before their first save.
  - `quickfix.repair_site_id()` also runs on every map load and writes `plotinfo.site_id` from `fortress_site`.

**`ipairs(df.<enum>.attrs)`**
- In r1.1 this loop never ended (DFHack issue #1860).
- `LuaWrapper.cpp` now gives attrs tables an `__ipairs` for plain and complex enums, so the loop stops where `ipairs(df.<enum>)` stops.
- Indexing past the end still returns the default entry.
- The attrs table is now frozen with `leave_metatable=true`.

**Smaller additions**
- **Deprecation warnings:** new wrapper macros (`WRAPM_D`, `WRAP_D`, `WRAPN_D`) and `LuaWrapper::notify_deprecated` print a warning once per script and line. No function uses them yet.
- **Pens:** foreground and background colours outside the colour table are now clamped to grey and black. This is the `COLOR_RESET` fix.
- **Coordinate types:** `df.coord` and `df.coord2d` are now generated from C++ templates (`CoordTemplate.h`).
  - Lua still sees `df.coord`; the tests in `test/structures/*` are unchanged.
  - `isValid` and `clear` are registered as object methods.
  - The C++ constructors switched from `uint16_t` to `int16_t`.
- **Struct identity:** struct types that are structurally equivalent are now treated as compatible (`DataDefs.cpp is_equivalent`). This only affects plugin and core type sharing; we never see it.

**C++-only additions, with no Lua binding in r2:**
- `Maps::describeSurroundings(savagery, evilness)` at `Maps.cpp:1583`. It returns one of 9 names, Serene through Terrifying, using the bands `<33`, `33..65` and `>65`.
- `Maps::getSiteTypeName(site)`.
- `Maps::addRegionBiomeOffset`, which uses the region_details keypad 1..9 convention.
- `Maps::getBiomeRgnPos`, now exported and range-checked, with unchanged behaviour.
- `MapCache::propagateVerticalFlags`.
- `MiscUtils::print_range`.

The only user of the first three is the `export-world-map` plugin.

### 1.2 Structures (`library/xml`, 1dd01aad → 63efa5f4, 40 files)

The xml changelog lists only two items: support for overriding code generation, and `graphic_viewport_spatter_flag`. The diff itself contains more.

- **Removed types:**
  - The `save_version` enum (about 100 items) and the `cmv_version` enum (`df.dfhack.xml`).
  - Every `read_file(… loadversion)` argument became `int32_t` (about 20 files).
  - `df.global.version`, `min_load_version` and `movie_version` are now plain `int32_t` (`df.game_v.xml`).
  - `world.original_save_version` is now `int32_t` (`df.world.xml:686`).
- **Removed field:**
  - `unit_action.data.raw_data`, the 24×int32 union arm (`df.unit.xml` r1.1:1176).
  - The `None` item of `unit_action_type` lost its `tag='raw_data'` attribute (`df.d_basics.xml`).
- **Moved and renamed:**
  - The placeholder `viewport_spatter_flag` bitfield was removed from `df.descriptor.xml`.
  - A real `viewport_spatter_flag` bitfield was added in `df.g_src.graphics.xml`, with shape, material, colour, fire frame and accepts_spatter fields, plus a `viewport_spatter_flag_fire` enum.
  - `screentexpos_spatter_flag` is now typed as that bitfield instead of `uint32_t`.
- **Added:**
  - A `circumstance_flag` bitfield and a `circumstancest` struct (`df.personality.xml`).
  - Extra `coord2d` includes on `block_square_event_mineralst` and `block_burrow` (`df.block.xml`).
- **Annotation only:** `df.item.xml` changes about 90 lines, all notes on `item_type` generic-item attributes.
  - One attribute value changed from `BOX` to `BAG` for `ANY_GOOD_FOOD`, and its `original-name` changed from `good` to `food`.
  - The items of `ANY_EDIBLE_VERMIN` were listed.
  - None of this changes memory layout.
- **Fields we use, all untouched.** Line numbers shift only because of the edits above.

| Field | r1.1 | r2 |
|---|---|---|
| `unit.animal.leave_countdown` (`df.unit.xml`) | 2695 | 2694 |
| `vanish_countdown` | 2697 | 2696 |
| `unit.enemy.enemy_status_slot` | 3100 | 3099 |
| `flags2.breathing_problem` | 1405 | 1404 |
| `flags2.roaming_wilderness_population_source` | 1406 | 1405 |
| `unit.path.goal` | 2641 | 2640 |
| `unit.invasion` (original name `invasion_id`) | 1710 | 1709 |
| `enemy_status_cache.rel_map` (`df.unit_reaction.xml`) | 47 | 47 |
| `world.populations` (`df.world.xml`) | 521 | 521 |
| `plotinfo.follow_unit` (`df.plotinfo.xml`) | 1094 | 1094 |
| `creature_raw.frequency` (`df.creature.xml`) | 1506 | 1506 |
| `creature_raw.cluster_number` (`df.creature.xml`) | 1508 | 1508 |
| `enabler.calculated_fps` / `fps` (`df.g_src.enabler.xml`) | 151 / 159 | 151 / 159 |
| `current_weather`, a 5×5 grid of `weather_type` (`df.game_v.xml`) | 54 | 48 |

### 1.3 Plugins and scripts

**New or reinstated plugins** (`plugins/CMakeLists.txt`):
- **`export-world-map`:** a plugin, plus `scripts/gui/export-world-map.lua` and four helper scripts in `internal/export-world-map/`.
  - It **only runs on the embark-selection screen**, and it needs region tiles that DF generates as you scroll the embark map. The gui version does the scrolling itself.
  - The plugin writes `regions.csv` (biome info, using `describeSurroundings`), `sites.csv` (using `getSiteTypeName`), `rivers.csv` and an elevation raster.
  - The gui adds roads (GeoJSON), geology layers, and per-region `creature_pops.csv`, `vermin_pops.csv` and `plant_pops.csv`. Their columns are `region_id;population_type;raw_id;pop_count_min;pop_count_max`.
- **`smooth-movement`:** rendering only. It needs the SDL 2D renderer and is **off unless enabled**.
- **`stockflow`:** reinstated. The control panel lists it as an automation entry, but it is not enabled by default.
- **`labormanager` is no longer its own DLL.**
  - Its source (`labormanager.cpp`, −2,145 lines) was deleted and the logic folded into `autolabor` as a "modern" engine.
  - `autolabor mode legacy|modern|monitor` switches engines, and the mode is saved with the fort.
  - `labormanager` is now a second command of the `autolabor` plugin.
  - Legacy mode turns DF's work-detail system off.

**New scripts:**
- **`devel/datamine`:**
  - `watch <expr>` polls every N frames and prints changes.
  - `snap` and `diff` record every field reachable from an expression and diff them later.
  - `find <expr> <substr>` searches fields by name or value.
- `devel/infinite-sky-probe`.
- `devel/jobwatch`.
- `fix/stuck-written-materials`.
- `prioritize this`, which absorbs `do-job-now`; the old name still forwards.

**Changed tools we touch or could touch:**
- **`timestream`:**
  - **A new check, `breathing_difficulties()` at `timestream.cpp:400`, makes the time-skip step (`clamp_timeskip`, `:406` and `:413`) return 0 while any unit in `world.units.all` is not FINE.**
  - It no longer fast-forwards the `winded` and `suffocation` counters.
  - `unconscious` is floored at 2.
  - `set fps` now passes the parsed number (`timestream.lua:18`).
- **`dig-now`:**
  - Its flag propagation moved into `MapCache::propagateVerticalFlags`.
  - A **solid** tile now also clears the light and outside flags on the column below it.
  - It is called only from the **Channel and Ramp** branches (`dig-now.cpp:467`, `:510`). Stairs and default digs do not propagate.
- **`exportlegends`** (legends mode) now always writes three files besides `legends_plus.xml` (`exportlegends.lua:1290–1306`):
  - `<save>-<date>-world_sites_and_pops.txt`: civilisation, site, and outdoor and underground animal population totals.
  - `-world_history.txt`.
  - `-world_map.csv`: per world tile, biome, alignment, savagery, elevation, volcanism, and river, road and lake flags.
- **Smaller fixes:**
  - `liquids`, `tiletypes`, `aquifer`, `3dveins`, `autodump`, `burrow`, `probe`, `sort`, `stocks`, `strangemood` and `suspendmanager`.
  - `overlay`: hotkeys no longer steal keys while DF has a text field open. It adds `is_native_text_entry_active()` to `plugins/lua/overlay.lua`, with no API change.
  - `widgets.Slider` and `RangeSlider`, `quickfort` and `gui/quickfort`.
  - `full-heal --all-citizens` was adapted because `isCitizen` now excludes the dead.

**Core changes:**
- **Plugin exceptions** (`PluginManager.cpp`): a C++ exception in a plugin command now prints `Exception in …` and returns `CR_FAILURE`. Before, it crashed DF.
- **stderr** (`Core.cpp`): on Windows stderr is set unbuffered, so **`stderr.log` is written as it happens**.
- **Console** (`Console-windows.cpp`): `dfhack-run` no longer takes over the terminal that launched it.
- **Selection getters** (`Gui.cpp`): `getSelected{Unit,Job,Item,…}` return nil, instead of re-entering Lua, when called from the render thread while a DFHack Lua screen has focus. This is the hotkey-hang fix.

### 1.4 The `unavailable` tag list

Counted by searching `docs/` and `scripts/docs/` for `:tags: … unavailable` at each tag.

| Group | r1.1 | r2 | No longer unavailable |
|---|---|---|---|
| Plugins | 24 | 22 | `labormanager`, `stockflow` |
| Scripts | 81 | 80 | `questport` (fixed for current DF) |

Still unavailable in r2:
- **Plugins:** autogems, building-hacks, channel-safely, digFlood, diggingInvaders, dwarfmonitor, embark-assistant, fixveins, follow, generated-creature-renamer, jobutils, manipulator, map-render, mode, power-meter, rendermax, siege-engine, steam-engine, stocks (the legacy page), title-folder, workflow, zone.
- **Scripts that matter to us:** `modtools/create-unit`, `spawnunit`, `modtools/transform-unit`, `modtools/spawn-flow`, `devel/inject-raws`, `devel/unit-path`, `do-job-now` (superseded by `prioritize`), `load-save`, and every `modtools/*trigger` script.

### 1.5 Removals (confirmed)

- The core changelog's "Removed" section is **empty**. `docs/about/Removed.rst` only gained a sentence pointing autohauler users at `labormanager`.
- `scripts` removed two `confirm` prompts, `squad-disband` and `hotkey-reset` (`internal/confirm/specs.lua`, −59 lines), because DF now asks for both itself.
- Structures lost `save_version`, `cmv_version` and `unit_action.data.raw_data` (see 1.2).
- The `stockpiles` tag was renamed `stockpile`. This only affects the filter in gui/launcher.
- The separate `labormanager` DLL is gone; the command lives on inside `autolabor`.

### 1.6 Timestream summary

1. `set fps` passes the parsed number.
2. Time skips are suspended while **any** unit in `units.all` has `getBreathingState() ~= FINE`.
3. Skips no longer count down the winded and suffocation counters.
4. `unconscious` is floored at 2 rather than 1.

`units.all` includes off-map and inactive units. I could not tell from the code whether a dead or offloaded unit keeps `flags1.drowning` or `flags2.breathing_problem` set. If one does, timestream stops skipping for the rest of the session. A rig check is in section 4, step 4.

---

## 2. Impact on our code

Legend:
- **=** unchanged: the r1.1 and r2 code is byte-identical, or the change cannot reach our call.
- **Δ** behaviour changed.
- **!** a bug of ours that already existed and that r2 exposes.

### 2.1 seasonal-wildlife (v7.0)

**Changed in r2**

- **`dfhack.units.teleport`** — **Δ**
  - Where: `seasonal-wildlife.lua:4404` (ecoPlaceNear), `:4418` (regroundNear), `:6855` (SCAV.fallbackMove); also `cx-eco.lua:300`.
  - r2 code: r1.1 `Units.cpp:766` → r2 `:778`.
  - **Correctness, in our favour.** `groundTile` and `waterTile` (`:4368`/`:4384`) test `occupancy.unit`. r1.1 could clear that bit on a tile another unit still stood on, so a later nudge or placement could stack a second unit there.
  - **Cost.** One scan of all active units per successful call. Each of our call sites stops at the first success, so this is about one call per moved unit, roughly 0.1 ms at 1,000 active units. It only shows in FPS work if nudge or scavenging moves hundreds of units in one pass.
- **`dfhack.persistent.getSiteData` / `saveSiteData`** (16 + 15 calls, `:534, :677, :700` … `:7124`) — **Δ, fix only**
  - Reclaimed forts used to fail until their first save; they now work, and the map-load hook also repairs `plotinfo.site_id`.
  - Our cache key at `:824` uses `plotinfo.site_id`. On a reclaimed fort that is now the real id instead of −1.

**Unchanged, with notes**

- **`PLACE.one`** (`:3948–3969`): `dfhack.units.create` plus six writes, including setting `occupancy.unit = true` by hand.
  - `Units::create` is byte-identical.
  - The fields we write (`world.units.active`, `animal.population.*`, `leave_countdown`, the `flags2.roaming_*` flags, `idle_area`) have the same layout.
- **SCAV path writes** (`:6890–6901`, `walkTo`): we fill `u.path.path` x/y/z by hand, assign `u.path.dest` and set `u.path.goal = SeekStation`.
  - We never call `setPathGoal`, so its NULL fix does not apply.
  - Do not switch to it: `setPathGoal` clears `path.path`, which would throw away our hand-built line unless it were called first.
- **`isCitizen(u)` with one argument** (`:4083, :6044, :6766, :6819`, alongside `isOwnCiv` and `isFortControlled`).
  - The default path already excluded the dead in r1.1.
  - We never pass `true`; there are 0 hits in either repo.
- **`V7.alignment`** (`:1104–1117`): good if evilness < 33, evil if ≥ 66.
  - Unchanged, and now **confirmed**: the new `Maps::describeSurroundings` (`Maps.cpp:1583`) uses exactly `<33` and `>65` for the evilness bands.
- **`WILD.invader`** (`:2755–2773`) tries the field name `invasion_id`, then `invasion`.
  - The field is `unit.invasion` (original name `invasion_id`) in **both** r1.1 (`df.unit.xml:1710`) and r2 (`:1709`).
  - The comment at `:2756` saying r1.1 calls it `invasion_id` is wrong, but harmless, because the code tries both names.
- **Biome-region lookups** (`:806–868, :4545, :4808`): `getTileBiomeRgn`, `getRegionBiome`, `getBiomeType`, and our decoding of block `region_offset`.
  - The body of `getBlockTileBiomeRgn` is identical; only `getBiomeRgnPos` gained a range check.
  - Our `off % 3 − 1, off // 3 − 1` decoding matches DFHack's own offset table.
  - Bug 13 (the (−1,−1) shift) is therefore not addressed by r2.
- **Enum attrs** (`:3860, :3907, :3931, :4375, :4994, :5031`): we index `df.tiletype.attrs`, `df.tiletype_shape.attrs` and `df.plant_type.attrs` and never loop over them.
  - There is no `ipairs` or `pairs` over any `.attrs` in either repo, so the loop fix affects nothing.
  - **Portability note:** any new code that loops `ipairs(df.X.attrs)` will hang on r1.1.

**Unchanged, no notes**

- `isWildlife`, `isDead`, `isActive`, `isTame`, `isAnimal`, `isUndead`, `isAdult`, `isFortControlled`, `isOwnCiv`, `getPosition` (many call sites, e.g. `:2776, :4084, :4170, :4256, :4432`).
- `unit.animal.leave_countdown` / `vanish_countdown` (`:3958, :5942, :5950`).
- `world.populations.all`, `pop.population.*`, `pop.quantity` (`:1783, :4568` and others; `cx-load.lua:89/:148`, `cx-eco.lua:346`, `cx-embark.lua:273`, `cx-probe.lua:157/:220`).
- `creature_raw.frequency` read and write (`:2977–2990`) and `cluster_number[0/1]` (`:1287`).
- `world.enemy_status_cache.rel_map[a][b].ur`, `slot_used`, `unit.enemy.enemy_status_slot` (`:3983, :4112–4354`; `cx-eco.lua:255/:394/:442`; `cx-probe.lua:246–314`).
- `plotinfo.follow_unit` (`gui/seasonal-wildlife.lua:1136`).
- `df.global.enabler.calculated_fps` / `.fps`, read only (`:7133–7136`; `cx-load.lua:46`; `cx-probe.lua:117`).
- `overlay` enable/disable/get_state, `repeat-util`, `json`, `gui.widgets` (we use no sliders) — gui `:1741, :1792`; engine `:343, :7171`. The overlay change only suppresses hotkeys during native text entry.
- `dfhack.gui.revealInDwarfmodeMap`, `showAnnouncement`, `screen.paintString`, `translation.translateName`, `filesystem.*`, `random.new`.
- `plugins.luasocket` (`seasonal-wildlife-web.lua:457`); not in the diff.
- `dfhack.run_command_silent('overlay', …)` (gui `:1792`).

### 2.2 DwarfCron: Chronicler bridge, cx-* probes, harness

**Needs a fix**

- **`df.global.current_weather[2][2]`** at `chronicler/dfhack/scripts/chronicler-bridge.lua:1784` — **!**
  - This is the same lookup r2 calls broken and replaced in `World::ReadCurrentWeather` (r1.1 `World.cpp:156` → r2 `:158` → `Maps.cpp:999`).
  - The correct index is `biome_x − map.region_x/16 + 1`, so `[2][2]` is usually a neighbouring region's weather.
  - Fix: `state.weather_type = dfhack.maps.getCurrentWeather()`, keeping `[2][2]` as the fallback when that function is nil (r1.1).

**Changed in r2**

- **`timestream set fps N`** (`chronicler/dfhack/controller.py:347, :557, :568`) — **Δ**
  - The number-parsing fix is harmless for integers.
  - Time skips now pause while any unit has breathing trouble, so speed modes 2–4 can quietly run at normal speed on forts with beached or drowning creatures (see 1.6).
- **`exportlegends all`** (`chronicler-export.lua:51`) — **Δ, additive**
  - Each export now writes three more files and runs a little longer.
  - The bridge builds the expected filenames itself (`:56` onward), so it ignores the extra files rather than mis-parsing them.
- **`enable`/`disable autolabor`, `enable autochop`/`autofarm`, `workorder`, `orders import`** (the old `girderpriced-*.lua` fort scripts) — **Δ**
  - `autolabor` is now the legacy engine of a three-mode plugin, and the mode is saved per fort.
  - `enable autolabor` still means legacy.
- **Readers of `stderr.log`** — **Δ, positive**
  - This covers `cx-lifecycle.sh logs` and the Lua errors that never come back over RPC (`cx-lifecycle.sh:852`).
  - Windows now writes stderr unbuffered, so lines appear when they happen rather than in flushed bursts.
  - This affects the "a FAIL burst at one timestamp is the reader" readout trap: bursts no longer come from buffering. Re-baseline any reader that relied on burst timing.

**Unchanged**

- **`isResident(u)`, `isCitizen(u)` and `getCitizens()` with default arguments** (`chronicler-bridge.lua:478–479, :636, :1736`; `controller.py:237, :392–428`), for the same reason as in 2.1. The census in `controller.py:405–419` already filters with `isAlive`.
- **`modtools/create-unit`** (`cx-probe.lua:363`, the `spawn` command, guarded at `:330–337`): still broken, so the guard stays correct.
- **`dfhack.units.create` plus writes** (`cx-load.lua:190`, `cx-eco.lua:376`).
- **`reqscript('makeown')`** (`cx-load.lua:186`): `makeown.lua` is not in the scripts diff.
- **`dig-now x,y,zbot x,y,ztop --clean` on a stair column** (`cx-load.lua:341`).
  - We designate DownStair, UpDownStair and UpStair (`:334–336`).
  - r2's new flag propagation runs only in the Channel and Ramp branches, so the breach shaft is unaffected.
- **`stockpiles import library/all -s <id>`** (`cx-load.lua:253`): the Lua diff is GUI only.
- **Parsing of `keybinding list` output** (`scripts/validate-full.py:1605`): no keybinding change.
- **`fix/wildlife`, and `overlay enable` / `overlay list` on `seasonal-wildlife.groups`** (`validate-full.py:1847, :2100–2101, :2197, :2729, :2790`; `alpha2-run.py:842, :942`).
- **`die`, `quicksave`, the RPC `RunCommand`/`RunLua` calls and `--version`** (`cx-lifecycle.sh:158`, `:771` onward; `cx-rpc.py:74`): the remote server is unchanged. The version string is now `53.16-r2`.

**Cosmetic**

- Hard-coded "53.16-r1.1" labels in `validate-report.py:224`, `alpha2-run.py:950, :973`, `eco-report/appendix.py:66`, and the comment at `cx-probe.lua:330`. Update them once r2 is validated.

**Searched for and found in neither repo:**
- APIs and fields: `setPathGoal`, `ReadCurrentWeather`, `save_version`, `df.global.version`, `raw_data`, `spatter_flag`, `ipairs`/`pairs` over `df.*.attrs`, and `isCitizen`/`isResident` with `true` as the second argument.
- Tools and scripts: `region-pops`, `spawnunit`, `labormanager`, `stockflow`, `do-job-now`, `confirm`, `gui/launcher`.

---

## 3. Opportunities

Every r2 call must be **feature-detected**, for example `if dfhack.maps.forEachTile then … else <current Lua loop> end`, with the call wrapped in `pcall`. There are two reasons:
- Players still on r1.1 run the same `seasonal-wildlife.lua`.
- `forEachTile` is documented as experimental.

This matches the fail-fast mandate: one native call, with the existing loop as the fallback.

### 3.1 `dfhack.maps.forEachTile`: where it pays and why

**Why it is faster.** Today each tile costs:
- a Lua userdata lookup for `des[lx][ly]`;
- a bitfield read through the wrapper for each of `flow_size`, `liquid_type` and `outside`;
- further lookups for `tiletype.attrs[tt]` and `tiletype_shape.attrs[shape]`.

That is several crossings between C and Lua per tile, roughly microseconds each. `forEachTile` does the whole filter in C++, at tens of nanoseconds per tile. It only calls into Lua for a `filter` or `callback`, once per tile that passes the native filter.

**Gotchas:**
- **Exact values only.** `designation` filters test exact values. `flow_size >= 4` has to be written either as four calls (`flow_size=4`, 5, 6, 7) with the counts summed, or as a native pre-filter `{liquid_type=false}` plus a Lua `filter`.
- **No "walkable" or "not tree" keys.** Build the `shape` list once (shapes where `df.tiletype_shape.attrs[s].walkable`) and the `material` list once (every `tiletype_material` except `TREE`). Iterate the enum, not its attrs (see 2.1).
- **No stride argument.**
- **No deadline inside a native call.** It is one call, so keep the box bounded. With a `callback`, return `false` once `FUSE.over(deadline)` is true.

**Per function in seasonal-wildlife.lua, in order of payoff:**

1. **`V7.vegSurvey`** (`:4980–5020`, floor and grass counts) — **the largest win**
   - Today: every second tile of every block in the surface band; Lua checks `outside`, tree material and walkability, then the four GRASS materials.
   - With r2: **two count-only native calls, with no Lua per tile**.
     - `floor = forEachTile(band, {designation={outside=true}, shape=WALKABLE, material=NON_TREE}).matched`
     - `grass` = the same call with the four GRASS materials.
   - Gain: the full band costs about as much as one current z-level. The sampling error from striding disappears, and `grassShare` (a ratio) needs no cap.
2. **`WET.survey`** (`:4515–4560`, wet tiles at the map edge)
   - Today: for each edge block on every z in the band, it walks **all 256 tiles** to find the 32 or fewer that lie on the edge. About 94% of the work is discarded.
   - With r2: four 1-tile-thick boxes per band (x=0, x=W−1, y=0, y=H−1).
     - Filter `{designation={liquid_type=false}}` plus a Lua `filter` that keeps `flow_size>=4`.
     - A callback that tallies `d.biome` per block, as now.
   - Gain: about 16× fewer tiles visited, and the remaining test is native. Rewriting the Lua loop to walk only each block's edge row or column gets most of that 16× even without r2.
3. **`CAVE.survey`** (`:3780–3825`, cavern bands at the edge)
   - Today: the same edge pattern, over all z.
   - With r2: the same four edge boxes over all z.
     - Filter `{designation={subterranean=true, outside=false}}`.
     - A callback that reads `block.global_feature` plus flow and liquid type to tally open, water and magma tiles.
   - Gain: as for WET.survey, over more levels. This is the scan that most often runs into its FUSE budget.
4. **`ENGINE.waterTiles`** (`:4785–4828`, classifies surface water, capped at 3,000 tiles)
   - Today: every second tile on each z in the band; Lua checks `outside`, flow and magma.
   - With r2, per z level:
     - A native filter `{designation={outside=true, liquid_type=false, flow_size=k}}` for k = 4..7.
     - A callback that records `{x,y,z,body,salt}` and returns `false` at `TILE_CAP`.
     - To keep the current every-second-tile density, skip odd x or y in the callback.
   - Gain: dry tiles, which are most tiles, are rejected natively; Lua only runs on water tiles. `ENGINE.deepColumns` (`:4870`) is built from waterTiles and speeds up with it.
5. **`PLACE.tiles`** (`:3898–3946`, land or water candidates, top-down to the first level with room)
   - Today: a Lua walk of every third tile on each z.
   - With r2, per z level from the top down:
     - **Find the level:** a **count-only** native call to find the first level with `matched > 0`.
       - For land: `{designation=WORLD_BITS, occupancy={unit=false}, material=NON_TREE, shape=WALKABLE}`.
       - For water: `flow_size` 4..7 and `liquid_type=false`.
     - **Gather on that level only:** a callback that keeps every-third-tile positions and stops at 200.
   - Gain: empty levels (sky, solid rock) cost one native call instead of a Lua walk. This scan runs behind every `place` and every water draw.
6. **Ring searches** through `groundTile`/`waterTile`, used by `ecoPlaceNear` (`:4397`), `regroundNear` (`:4412`, up to 13 z × (2r+1)²) and `SCAV.fallbackMove` (`:6849`)
   - Today: one `getTileBlock` plus array reads per candidate tile.
   - Only `regroundNear` is worth converting:
     - One box from (x−r, y−r, z−12) to (x+r, y+r, z).
     - Filter `{shape={FLOOR,RAMP}, material=NON_TREE, occupancy={unit=false}}`, plus a Lua filter that drops magma.
     - A callback that keeps the best (dz, ring).
   - The others usually stop at radius 2.
   - Gain: moderate, and only in the worst case (a unit stuck in a canopy). Low priority.
7. **Not worth converting:**
   - `V7.seaAt` / `V7.floorAt` (`:5475–5491`), `SCAV.wet` (`:6839`) and `PLACE.tile` (`:3855`) touch 1–7 tiles each; call overhead would dominate.
   - `getEmbarkRegions` (`:827–868`) already works per block, with 9 byte reads of `region_offset` each.

`getTileBlockCoord`, `getBlockOrigin` and `getTileBlockOffset` only make the `xyz2pos(bx*16, by*16, z)` and `x % 16` idioms easier to read, and each is an extra C call. Do not use them in hot loops.

### 3.2 `getBreathingState` and `breathes` for aquatic safety

`breathes(u)` only means "does not have NOBREATHE". It does **not** mean "aquatic", so it cannot replace `MODEL.isWater(cr)`. Where it does help:

- **A check after placement.** One tick after `PLACE.one` (water layer), `V7.ribbon`, `ecoPlaceNear`, or `SCAV.fallbackMove(…, water=true)`, read `getBreathingState(u)`.
  - 0 (CANT) means the unit was beached or put in the wrong medium. Count it, then re-place or retire it.
  - This fits the manifest-subject-receipt rule.
- **v7 fishers (`fishers` / `fish_breathe`).** These give land species `CAN_SWIM_INNATE`, and optionally `CAN_BREATHE_WATER`.
  - A periodic count of fishers in TROUBLE or CANT shows directly whether `fish_breathe=false` drowns them.
  - Today that can only be inferred from deaths.
- **Scavengers wading from a bank (scav_ext).** Use the same check before choosing the water fallback.
- **Explaining timestream.** Any CANT or TROUBLE unit now stops timestream skipping. Showing that count in `status` would explain a "timestream is not skipping" report.

### 3.3 Surroundings and realm

`describeSurroundings` has **no Lua binding**. It is still useful as DFHack's reverse-engineered statement of DF's 3×3 bands: `<33`, `33..65` and `>65` on both axes. Our `V7.alignment` matches it on evilness (2.1). If we want a savagery axis (Calm / Wilderness / Untamed Wilds), copy the same bands rather than inventing new ones.

### 3.4 World-scale exports for Chronicler and the eco desk

- **`exportlegends` (legends mode) is the easiest win.**
  - `-world_sites_and_pops.txt` gives world-wide outdoor and underground animal population totals.
  - `-world_map.csv` gives savagery, alignment, biome and water flags **per world tile**.
  - Chronicler already runs `exportlegends all`; it only needs to read the two new files.
- **`gui/export-world-map` / `export-world-map` (embark-selection screen only).**
  - They produce per-region `creature_pops.csv`, `vermin_pops.csv` and `plant_pops.csv` with min and max counts, plus `regions.csv` (biome and surroundings per region tile) and `sites.csv`.
  - That is a direct census, at worldgen time, of the wild populations the roster builder models.
  - In the df-worldgen flow, run it at the embark-selection step, before embarking test forts. The gui scrolls the embark map itself. It would replace hand surveys of `world.populations` across candidate sites.
  - Note that `export-pops.lua` reads `world_data.regions[].population`, the region pools, not the per-tile `world.populations.all`.

### 3.5 `devel/datamine` for reverse engineering

- `snap <name> <expr>` and then `diff <name>`, taken before and after an action (a wave arrival, an `enemy_status_cache` write), gives exactly the "which fields changed" view our probes build by hand.
- `watch -n x <expr>` replaces one-off polling probes for single values such as `unit.animal.leave_countdown` or the `slot_used` count.
- Watches print to the DFHack console, not over RPC. On the rig, read them from `stderr.log`, which is now unbuffered, or keep using the RPC probes.

### 3.6 Other

- If Chronicler's speed modes matter, show the CANT/TROUBLE count from 3.2 in the bridge state.
- `stderr.log` is now real-time, so `cx-lifecycle.sh logs` can show a Lua error right after the RPC call instead of after a flush.

---

## 4. Rig re-validation checklist, riskiest first

Run these when the rig is next free. Each step is cheap; stop at the first failure.

1. **Version and load (minutes).**
   - `cx-rpc.py --version` should report `53.16-r2`, and `cx-probe rig` should show `dfhack_version` as `53.16-r2`.
   - Load CTRL. In `stderr.log`, `quickfix` should appear only on reclaimed forts, with no Lua errors from our scripts at load. DFHack's script manager loads every module script on world load (`gui/seasonal-wildlife.lua:32`), so a load error would show up here.
   - Run `luac -p` on the three seasonal-wildlife scripts and the cx-*.lua scripts. The Lua version did not change in r2, so this is a formality.
2. **Saved settings round-trip.** Run `seasonal-wildlife status`, change one setting, save, reload and read it back. This exercises `saveSiteData`/`getSiteData` through the changed `GetCurrentSiteId`.
3. **Placement and teleport occupancy (the highest behavioural risk).**
   - In validate-full, run:
     - `phase_mechanics`: `mech.place`, `mech.ecology.nudge`, `cli.place`.
     - `phase_v70`: `mech.v70.slotv`, `scav_mapwide`, the scav_ext fallback, fishers.
     - `phase_lake`: water placement.
   - Then add one probe: after `place` and a forced `groups ecology now` nudge, scan the placement band for tiles marked occupied with no standing unit, and for tiles with two standing units.
   - On r2 both counts should be zero. Any non-zero count is a new readout trap.
4. **The breathing check.** With aquatic placements and fishers on, call `getBreathingState` across `world.units.all`, including dead and inactive units, and count those not FINE. If dead or inactive units show up, timestream will never skip on that fort. Record the result as a CTRL fort fact.
5. **FPS baseline.**
   - Re-time CTRL with the stopwatch method from fps-load-facts: a fresh process, the same tick window, ecology on. The teleport scan and the unbuffered stderr are the two r2 costs on our path.
   - Confirm `smooth-movement` and `stockflow` are not enabled (`enable` with no arguments lists the state of every plugin).
6. **The rest of validate-full.**
   - `phase_w0`: the `keybinding list` parse.
   - `phase_gui`: overlay enable and list. Also try window keys while a native text field is open; that code path is new.
   - `phase_cli` and `phase_static`.
   - `phase_model` and `phase_v65`–`v69`: no change expected.
7. **cx harness.**
   - `cx-load sustain`, makeown and the breach. `dig-now` on stairs should leave the outside and light flags along the shaft identical to before.
   - `stockpiles import`.
   - `cx-eco tp`, `cx-probe rel` and `cx-probe gather`.
   - The `cx-embark` populations line.
   - One `chronicler-export`, to confirm the three new exportlegends files appear and the ingest ignores them.
8. **Cleanup.**
   - Fix `chronicler-bridge.lua:1784` to use `getCurrentWeather`.
   - Update the "53.16-r1.1" labels in `validate-report.py:224`, `alpha2-run.py` and `eco-report/appendix.py`, and the df-rig skill description, which still says "DFHack 53.16-r1.1".
   - Correct the `invasion_id` comment at `seasonal-wildlife.lua:2756`.

---

## 5. Docs mirror inventory

- **wget has finished.**
  - `wget.log` line 6756 reads `=== wget exit 8`, after `Downloaded: 560 files, 9.0M`.
  - Exit 8 comes from **one** 404, for `docs/tools/Settingqualityandmaterialfilters`. That is an upstream doc bug: a malformed link at `docs/plugins/buildingplan.rst:30` meant to point to its own section heading at line 155. It is not a missing page.
- **Version confirmed:**
  - `index.html` is titled "DFHack 53.16-r2 documentation".
  - The offline single-page build, `htmlzip/dfhack-stable/index.html` (4.4 MB, built 29 Sep at 11:30), has the same title. The `53.16-r2` tag was committed on 29 Sep at 12:10 −0500.
  - Both contain the new r2 API: `forEachTile` and `getBreathingState` appear in `docs/dev/Lua API.html`.
- **Mirror tree:** `dfhack-docs-stable/docs.dfhack.org/en/stable/` holds 558 files, 519 of them HTML.

| Section | HTML pages |
|---|---|
| root: index, search, LICENSE, 29 tag indexes | 32 |
| `docs/`: Core, Installing, Introduction, NEWS, NEWS-dev, Quickstart, Tags, Tools | 8 |
| `docs/about` | 4 |
| `docs/api`: index, Maps | 2 |
| `docs/dev` | 13 |
| `docs/dev/compile` | 4 |
| `docs/guides` | 5 |
| `docs/tools`, top level | 275 |
| `docs/tools/devel` | 47 |
| `docs/tools/fix` | 29 |
| `docs/tools/gui` | 69 |
| `docs/tools/modtools` | 30 |
| `library/xml`: SYNTAX | 1 |

- **Completeness against the repo at the r2 tag. No pages are missing.**
  - All 429 tool docs are present: `docs/plugins/*.rst` plus `scripts/docs/**/*.rst`.
  - The mirror also has the 21 built-in command pages from `docs/builtins/` (alias, cls, die, enable, keybinding, kill-lua and so on).
  - Every other page under `docs/` is present (about, api, dev, dev/compile, guides), including `docs/dev/Lua API.html`.
  - All the pages new in r2 are present: `export-world-map`, `smooth-movement`, `stockflow`, `devel/datamine`, `devel/infinite-sky-probe`, `devel/jobwatch`, `fix/stuck-written-materials`, `gui/export-world-map`.
- `unavailable-tag-index.html` in the mirror is the page to check for what is still disabled (see 1.4).
