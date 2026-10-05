# force (DFHack 53.16-r2)

- Docs: https://docs.dfhack.org/en/stable/docs/tools/force.html (read 5 Oct 2026)
- r2 doc: `scripts/docs/force.rst`. Its content matches the stable web page: usage, civ IDs, the `:lua` civ lister, five examples, five event types, and "Wildlife may take up to 100 ticks". No difference found.
- Source: `scripts/force.lua` (58 lines). The `Wildlife` path is `scripts/fix/wildlife.lua:100-116`. `modtools/force` was merged into it (`scripts/changelog.txt:533`). `Wildlife` was added at `changelog.txt:509`.
- Tags: fort, armok, gameplay.

## Commands and options

```
force <event> [<civ>]
force Wildlife [all]
```

Documented events are Caravan, Migrants, Diplomat, Megabeast and Wildlife. The `<civ>` argument applies to Caravan and Diplomat and defaults to the player civ.

**Accepted but not in the docs (from source):**

- **Any `df.timed_event_type` name, case-insensitive** (`force.lua:28-35`). The enum (`df.plotinfo.xml:213-226`) also gives:
  - `WildlifeCurious` (bay12 `CURIOUS_BEAST`)
  - `WildlifeMischievous` (`MISCHIEVOUS`)
  - `WildlifeFlier` (`SWARM`)
  - `NightCreature` (`ATTACK_WEREBEAST`)
  - `TributeCaravan`
  - `EvaluateAttackAndSendImmediateArmy`
  - `NONE` (value -1, which still passes the `if not df.timed_event_type[...]` check because -1 is truthy in Lua)

  Only `FeatureAttack` (bay12 `ATTACK_FEATURE`, a cavern/feature invasion) is refused (`:36-38`). For every type except Caravan, Diplomat and Migrants, `entity` is nil.
- **`<civ>` forms** (`findCiv`, `:3-10`): the literal `player`, a numeric `historical_entity` id, or an `entity_raw.code` (case-insensitive; the first matching entity wins).
- **Bad-civ message bug:** `:44-45` prints `tostring(civ)` *after* `civ` was set to nil, so you get "unable to find civilization: nil".
- `force help` (any first arg containing "help") prints help. With no args it raises `qerror('missing event type')`.

## How it works

**Native events: one append to the timed-event queue** (`:51-58`):

```lua
df.global.timed_events:insert('#', { new=true, type=df.timed_event_type[eventType],
    season=df.global.cur_season, season_ticks=df.global.cur_season_tick,
    entity=civ, feature_ind=-1 })
```

- `df.global.timed_events` (bay12 `plot_event`, `df.game_v.xml:18-19`) is a vector of `timed_event` (`plot_eventst`, `df.plotinfo.xml:228-237`). Its fields are `type`, `season`, `season_ticks` (commented "1 tick = 10 frames"), `entity`, `feature_ind`, `layer_id`, `feature_ax`, `feature_ay`.
- The event is stamped with *now*, so DF processes it on its next check ("most events next tick").
- **Whether the event has any visible effect is DF's decision.** DFHack does not validate it.

**`Wildlife` is synthetic: it creates no event.** `force.lua:22-25` calls `fix/wildlife.free_all_wildlife(args[2]=='all')`. For every unit in `world.units.active` that is not dead, is active, is `isWildlife` (`population_idx >= 0`, not merchant, not forest, not fort-controlled, `Units.cpp:601-607`) **and** has `flags2.roaming_wilderness_population_source` set, and that is not hidden unless `all` was given (`fix/wildlife.lua:108-116`), it calls `detach_unit` (`:66-70`). That function:

1. clears `flags2.roaming_wilderness_population_source` and `..._not_a_map_feature`;
2. **refunds one** to the matching `world.populations.all` entry. The match is on region_x/y, feature_idx, cave_id, site_id and population_idx. The new value is `quantity = min(quantity+1, quantity_max)`, and entries at 10000001 or above (innumerable) are skipped (`:47-63`).

"Hidden" is `Units::isHidden`. That is ambush state or, for wild units, `!Maps::isTileVisible(pos)` (`Units.cpp:267-293, 141-143`). It is about tile visibility, not cavern discovery.

## Side effects, persistence, gotchas

- **The queue entry persists.** The event goes into a saved global vector, so an event DF has not consumed survives a save.
- **Wildlife writes are permanent.** The flag clear and the population refund are unit and world data, so they persist too.
- **Rate limits come from DF.** The doc says "DF may choose to ignore events that are triggered too frequently" and allows one caravan per civ.
- **Our measurements (seasonal-wildlife `STATE.md` addendum 37, E22, 17 Sep 2026, CTRL, 53.16-r1.1):**
  - `force Caravan MOUNTAIN` brought merchants in about 1,700 ticks. They come inland only if a trade depot exists.
  - **`force Migrants` and `force Megabeast` were accepted (rc 0), but nothing arrived in 36,000 ticks.** So rc 0 means "queued", not "happened".
- **Lines 28-32 iterate the enum type with `ipairs`.** The match only canonicalises case. An unmatched name falls through to the uppercased string, which fails the lookup and raises `qerror`.
- **No mode check.** Running `force` with no fort loaded fails on `df.global.plotinfo` or the enum access with a Lua error rather than a clean message.

## Relevance to our work

- **The test harness already uses the Wildlife path:** `validate-full.py:2468-2496` (mech.force), Ctrl+F and `W` in the GUI. The source confirms the harness note: it is a flag-clear release, not a spawn. With nothing flagged it is a no-op, and any wave that follows comes from DF's own timer. Keep scoring "nothing to free" as NOT-TESTABLE.
- **Conflict: the refund can undo our holds.** `detach_unit` adds 1 to the unit's population entry. seasonal-wildlife holds inactive entries at `quantity = 0` and `flags.extinct = true` (`seasonal-wildlife.lua:2426, 2454, 2918`). After `force Wildlife` such an entry reads 1. `extinct` still blocks the draw (E8: either barrier stops a draw), but any audit that reads "held = quantity 0" will see a false FAIL.
  - The refund also double-counts animals that are still on the map. Our scheduler (`seasonal-wildlife.lua:3402-3420`) deliberately detaches *without* refunding, because DF refunds on departure.
  - **Rule: in tests, run our own `sendoff`/detach rather than `force Wildlife`**, or re-apply holds afterwards.
- **`force Wildlife` without `all` is not a "surface only" switch.** It frees every *visible* flagged unit. If the map was revealed (`reveal`/`gui/reveal` with restore off), cavern wildlife counts as visible and is freed too. Pass `all` deliberately, or assert visibility, so cells are comparable.
- **The event list for the harness:**
  - **Usable:** Caravan (with a depot), Diplomat.
  - **Measured dead on 53.16:** Migrants, Megabeast. For citizens use create+makeown (fort-load-levers).
  - **Untested and worth one probe each:** `WildlifeCurious`, `WildlifeMischievous` and `WildlifeFlier`. These are DF's native wildlife-behaviour plot events and bear directly on seasonal-wildlife (thieving/curious beasts, flier swarms). `NightCreature` is also untested.
  - **Not reachable through `force`:**
    - Cavern invasions. `FeatureAttack` is refused, and it needs `feature_ind`/`layer_id`/`feature_ax/ay` that force does not set. Our `e23b-probe-breach.sh:56-59` already reads such queued events. To test, insert a fully populated `timed_event` ourselves.
    - Sieges. There is no siege type. `EvaluateAttackAndSendImmediateArmy` goes in with `entity=nil`, so treat it as unknown and risky.
  - **Never** `force NONE`: it queues a type -1 event.
- **A pattern to copy.** One `timed_events:insert('#', {...})` is the whole mechanism. A rig verb can stamp a future `season_ticks` to schedule an event at a known tick, instead of firing it "now".
