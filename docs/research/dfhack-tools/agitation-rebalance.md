# agitation-rebalance (DFHack 53.16-r2)

Sources read: `scripts/agitation-rebalance.lua` (790 lines), `scripts/docs/agitation-rebalance.rst`, its callee
`scripts/exterminate.lua`, `library/modules/EventManager.cpp`, `library/LuaTools.cpp` (timeouts), and df-structures in
`library/xml/`. All paths are relative to `/Users/nathanielcannon/Claude/GitRepos/dfhack-53.16-r2`.
Web doc: https://docs.dfhack.org/en/stable/docs/tools/agitation-rebalance.html. The "stable" site is currently built
from 53.16-r2. A word-level diff against the local rst shows the same text, with only markup differences. The script
is byte-identical in `dfhack-latest` (1 Oct 2026).

## What it does

It is an enableable fort-mode mod (`--@enable = true`, `--@module = true`). It changes irritation-driven attacks from a
continuous flood into a single attack in response to what the player did:

- **surface**: when an agitated wild unit arrives, the fort's surface irritation counter is lowered to the
  difficulty minimum, so the next wave rolls at 0%.
- **cavern**: cavern invasions (`FeatureAttack` timed events) are rolled once again against irritation gained since the
  last invasion. Events that fail the roll are deleted.
- **cap-invaders**: live cavern invaders across all layers are culled down to `cavern_dweller_max_attackers` by
  disintegration.
- **monitor**: an overlay showing surface and cavern threat as None, Low, Med or High.
- **auto-preset**: when the mod is enabled, it maps a vanilla "Enemies" difficulty to one of the mod's presets.

### Commands and options

| Command | Source | Notes |
|---|---|---|
| `enable agitation-rebalance` / `disable ...` | :774-777 | `do_enable` / `do_disable` |
| `agitation-rebalance` or `... status` | :782-784, `print_status` :725-756 | prints features, four difficulty values, agitated and visible-invader counts, and obfuscated chances |
| `agitation-rebalance preset <casual\|lenient\|strict\|insane>` | :778-779, `do_preset` :326-333 | works while disabled. It writes `plotinfo.main.custom_difficulty` |
| `agitation-rebalance enable\|disable <feature>` | :780-781, `enable_feature` :758-769 | see the hyphen bug below |
| any other word | :785-787 | prints help |
| *(not in docs)* `:lua reqscript('agitation-rebalance').monitor_debug=true` | :517-519 | debug overlay: exact percentages per layer, forgotten-beast (FB) chances, raw irritation values, invader count and cap, and stats counters |

**Gap between the docs and the code: the documented feature names `auto-preset` and `cap-invaders` do not work.**
`enable_feature` indexes `state.features[which]` with the argument unchanged (:763), but the keys are `auto_preset` and
`cap_invaders` (:66-69). As a result, `agitation-rebalance disable auto-preset` raises `feature not found`. You have to
type `auto_preset` or `cap_invaders`. The underscore names are the ones `status` prints. `surface`, `cavern` and
`monitor` work as documented.

### Preset values written (source :14-39)

| preset | wild_irritate_min | wild_sens | wild_irritate_decay | cavern_dweller_max_attackers |
|---|---|---|---|---|
| casual | 100000 | 100000 | 100000 | 0 |
| lenient | 10000 | 10000 | 5000 | 20 |
| strict | 2500 | 500 | 1000 | 50 |
| insane | 600 | 200 | 200 | 100 |

Auto-preset compares these four fields exactly against the vanilla "Enemies" presets (:41-60): Off means
2000/10000/500/0, Normal means 2000/10000/500/50, and Hard means 0/10000/100/75. If they match, it loads casual, lenient
or strict (:347-361). It runs at every `do_enable` (:369), which includes every map load while the mod is enabled
(:390-392).

## How it works

### DF fields read and written

| Field | r2 definition | Use |
|---|---|---|
| `df.global.plotinfo.outdoor_irritation` | df.plotinfo.xml:846 | surface counter. **Written**, clamped to `wild_irritate_min` (:115-116) |
| `plotinfo.main.custom_difficulty.{wild_irritate_min, wild_sens, wild_irritate_decay, cavern_dweller_max_attackers, forgotten_*}` | df.plotinfo.xml:751-768 | read for chances. **Written** by presets |
| `world.features.map_features[]` → `feature_init_subterranean_from_layerst`, `.start_depth` (layer_type), `.feature.irritation_level` | df.feature.xml:90,152,239. The xml comment reads "divide by 10k for attack chance, max 100k" | cavern counters. **Written** on each new invasion (:160-170) |
| `plotinfo.tasks.wealth.total` | | input to the FB chance |
| `unit.flags4.agitated_wilderness_creature` (through `dfhack.units.isAgitated`, Units.cpp:609-612) | | detects a surface attack |
| `unit.invasion_id` → `df.invasion_info.find()` → `origin_master_army_controller_id == -1` | df.unit.xml:2667, df.plotinfo.xml:343 | definition of "cavern invader" (:181-187): an invasion with no army controller, not caged, not tame |
| `unit.animal.vanish_countdown` | df.unit.xml:2696 | `> 0` means the unit is already being exterminated (:176-179) |
| `df.global.timed_events[]` with `type == FeatureAttack`, `.entity` | | **erased and deleted** when they fail the roll (:309-319) |
| `df.global.cur_year`, `cur_season`, `cur_season_tick` | | season scheduling |

Note on field names: in r2, and still in `dfhack-latest`, the unit field is `unit.invasion_id` (df.unit.xml:2667). The
name `invasion` (with `original-name='invasion_id'`) belongs to **`unit_parley`** (df.unit.xml:1709), not to `unit`.

### Hooks and timers

- **eventful `UNIT_NEW_ACTIVE`, frequency 5 ticks** (:367-368): `check_new_unit` (:243-264). EventManager diffs
  `world.units.active` against its previous set and fires once per newly active unit id
  (EventManager.cpp:732-754). The first 6 ticks after enabling are ignored so that existing units do not count (:246, :365).
- **Season loop**: `seasons_cleaning` (:339-345) runs `cull_invaders()` and `throttle_invasions()`, then
  `dfhack.timeout(TICKS_PER_SEASON - cur_season_tick + 1, 'ticks', ...)`. Tick timers are cancelled on
  `SC_MAP_UNLOADED`/`SC_WORLD_UNLOADED` (LuaTools.cpp:2039-2041) and rebuilt on `SC_MAP_LOADED` (:378-393).
- **Persistence**: `dfhack.persistent.saveSiteData('agitation-rebalance', state)` (:105-107). State includes `enabled`,
  `features`, `caverns.{last_invasion_id,last_year_roll,last_season_roll,baseline,player_visible_baseline}`, and `stats`.
  It is stored per fort, in site data.
- **Overlay** `agitation-rebalance.monitor`: `IrritationOverlay` on `dwarfmode/Default`, updated at most once every 5 s
  (:399-406). The update recounts invaders, which is a full pass over `units.active` (:705-707).

### Chance models, as the DFHack authors encoded vanilla

- Surface: `0` if `outdoor_irritation <= wild_irritate_min` **or savagery <= 65**. Otherwise
  `min(100, (irr - min)*100 // wild_sens)` (:422-427). Savagery is read from the region biome of **map tile (0,0)**
  only, at about ground level (:408-419).
- Cavern, natural rate: per layer `min(1, irritation_level/10000)`. Layers roll top-down, so layer 2's chance is
  `(1-c1)*c2` (:273-284).
- Forgotten beast: `min(33, (wealth//forgotten_wealth_div + irritation - forgotten_irritate_min)*33 // forgotten_sens)`
  (:430-439).
- The mod's cavern roll: `irritation = sum(all layers) - baseline`, against `irr_max = (wild_irritate_min + wild_sens)//2`.
  This value is scaled by the natural chance until a first invasion has happened (:286-296).

### Removing excess invaders

`exterminate.killUnit(unit, DISINTEGRATE)` sets `unit.animal.vanish_countdown = 1` and removes every inventory item
(exterminate.lua:49-52, 97-102, 113-115). DF then removes the unit in a puff of smoke with no corpse. The cull runs from
the end of `units.active` backwards, so animal-people invaders tend to survive over their war animals (:189-206).

## Side effects, persistence, gotchas

- **Permanent changes to the save**: preset values in `custom_difficulty` (fort), `outdoor_irritation` (fort), and
  **cavern `irritation_level`, which is world-level and survives into later forts in the region**. `on_cavern_attack`
  clamps every cavern layer to `min(current, 100000 - cavern_sens, normalized)` (:160-169). The docs say "we don't want
  to adjust the irritation counters directly", but the counters are lowered (capped) all the same. Deleted
  `FeatureAttack` timed events are gone for good.
- **Bug: the cavern roll happens about once per year, not once per season.** The guard at :300-303 is
  `last_year_roll == cur_year and last_season_roll >= cur_season or last_year_roll >= cur_year`. Lua parses this as
  `(A and B) or C`, and `C` is true for the rest of any year in which a roll has happened. Later-season
  `FeatureAttack` events in the same year pass unthrottled.
- **Unit mismatch in the season timer**: `TICKS_PER_SEASON` is 100800 game ticks (:335-337), but `cur_season_tick`
  counts 0-10080 in units of 10 ticks. autofarm.cpp:92-94 uses 10080 as the season length. Unless the mod is enabled at
  a season start, the next run lands partway into the following season, not at its boundary.
- **Bug: the cavern feature is gated on `cap_invaders`**: `check_new_unit` returns early unless
  `state.features.cap_invaders` is set (:253). With `cap_invaders` off, `on_cavern_attack`, which sets the baseline,
  never runs. With `cavern` off and `cap_invaders` on, the irritation clamp still runs.
- **Any** newly active unit with `agitated_wilderness_creature` counts as a "surface attack", whatever its z-level or
  layer (:249-251). A cavern unit flagged agitated also resets the surface counter.
- Enabling twice within a season starts a second `seasons_cleaning` chain. Disabling does not cancel the timer; the
  chain stops only on its next tick because `state.enabled` is false (:340).
- Performance: one pass over `units.active` for each new cavern invader (`get_num_cavern_invaders`, :218-231), plus the
  eventful poll every 5 ticks, plus the overlay every 5 s. This is light.
- With `cap_invaders` and max 0 (casual), every cavern invasion is erased in advance (`over_cap` at :307-308), and any
  invader that still enters is disintegrated. The rst caveat about "billowing smoke near the edge of the map" refers to
  this.
- `qerror('needs a loaded fortress map to work')` unless the game is in fort mode with a map loaded (:719-721).

## Relevance to seasonal-wildlife and aquarium

- **Our arrivals feed its rolls.** In savage biomes, every new surface wildlife group rolls for agitation against
  `outdoor_irritation` (rst :79-90). The seasonal-wildlife scheduler detaches gated groups so that DF sends the next wave
  (seasonal-wildlife.lua:3398-3420). More waves mean more agitation rolls. With agitation-rebalance enabled, the first
  agitated arrival resets the counter, which limits the damage. Without it, our faster cadence speeds up vanilla
  retaliation. The status page could show the surface number using the same formula (:422-427): read
  `plotinfo.outdoor_irritation` and `custom_difficulty` directly, with no need to enable the mod.
- **Conflict with our irruption.** IRRUPT arms a cavern group by setting `flags4.agitated_wilderness_creature`
  (seasonal-wildlife.lua:6027-6060). If the flag is set before eventful's 5-tick poll first sees the unit as active, this
  mod counts it as a *surface* attack and writes `plotinfo.outdoor_irritation` (:249-251). Arming after arrival, which is
  how our groups tick works, avoids this. Keep it that way, or test with the mod enabled.
- **cap-invaders will not cull our animals** unless they carry an `invasion_id` whose invasion has no army controller
  (:181-187). Never give placed or irrupting units an invasion record. That also keeps them out of the ecology rulings'
  "irruption is not an invasion" boundary.
- **Field names**: our `WILD.invader` probes both `invasion_id` and `invasion`, on the belief that a later tree renamed
  the unit field (seasonal-wildlife.lua:2755-2772). That belief is wrong for r2 and for latest: the rename is on
  `unit_parley`. The probe is harmless, but its comment can be corrected. `unit.invasion_id` is what this mod uses, and
  it works in r2.
- **Reusable techniques**: (1) the eventful `UNIT_NEW_ACTIVE` hook (:367-368) is a cheap, C++-side arrival detector. It
  could replace any Lua polling for "a new group arrived", in line with the no-polling rule for the user's game. (2)
  Erasing `df.global.timed_events` entries of type `FeatureAttack` (:309-319) is a proven way to suppress vanilla cavern
  invasions, if we want ecology-only caverns in tests. (3) `exterminate.killUnit(u, DISINTEGRATE)` removes a unit with no
  corpse.
- **Multi-biome gotcha**: the monitor's savagery check samples only map tile (0,0) (:411-418). On region9, which is a
  multi-biome 8x8 embark, the surface threat it displays may be wrong for the savage part of the map.
- **Rig hygiene**: if the control panel autostarts this mod on a test fort, our cavern experiments lose invasions and
  cavern irritation is clamped world-wide. Check `agitation-rebalance status` (or the site-data key) before attributing
  a change in cavern behaviour to our tool.
- Aquarium plugin: no interaction.
