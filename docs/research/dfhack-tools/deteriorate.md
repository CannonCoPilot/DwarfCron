# deteriorate (DFHack 53.16-r2)

Sources read: `scripts/deteriorate.lua` (392 lines), `scripts/docs/deteriorate.rst`, `scripts/test/deteriorate.lua`,
`scripts/internal/control-panel/registry.lua`, `library/modules/Items.cpp` (Items::remove), and `library/LuaTools.cpp`
(dfhack.timeout). Paths are relative to `/Users/nathanielcannon/Claude/GitRepos/dfhack-53.16-r2`.
Web doc: https://docs.dfhack.org/en/stable/docs/tools/deteriorate.html. The stable site is built from 53.16-r2 and its
text matches the local rst. The script is identical in `dfhack-latest`. The only entry for 53.16-r2 in the scripts
changelog is "`gui/control-panel`: fixed incorrect description of deteriorate commands" (scripts/changelog.txt:61).

## What it does

An enableable fort tool (`--@enable`, `--@module`). Items in chosen categories gain wear (`x`, `X`, `XX`) and are then
deleted. It exists to clear clutter that hurts FPS.

| Form | Source | Effect |
|---|---|---|
| `enable` / `disable deteriorate` | :288-294, :241-261 | starts or stops the per-category timers |
| `deteriorate` / `deteriorate status` | :342-343, `status` :315-328 | |
| `deteriorate enable\|disable <cats>` | :344-367 | |
| `deteriorate frequency <days> <cats>` | :368-380 | **undocumented alias `freq`**. Fractions are allowed. The value must be > 0 |
| `deteriorate now <cats>` | :381-387 | immediate deletion. **It works while the tool is disabled** (there is no enabled check) |
| `-h`, `--help`, `help` | :332-340 | |

Categories (:13-24): `clothes`, `food`, `corpses`, `usable-parts`, `unusable-parts`, plus the aliases `parts` and
`all`. The defaults are `corpses` and `unusable-parts` on, with frequency 1 day each (:26-40).

Control-panel entries (registry.lua:129-134): `enable deteriorate`, plus the optional run commands
`deteriorate enable all`, `deteriorate frequency 0.15 all` ("less than a month") and `deteriorate frequency 3 all`
("about a year").

## How it works

### Items in scope (vectors of `df.global.world.items.other`)

| category | vectors | filter |
|---|---|---|
| clothes | GLOVES, ARMOR, SHOES, PANTS, HELM (:55-63) | `subtype.armorlevel == 0 and flags.on_ground and wear > 0` (:92-96) |
| food | FISH, FISH_RAW, EGG, CHEESE, PLANT, PLANT_GROWTH, FOOD, MEAT, LIQUID_MISC (:65-77) | everything, except that LIQUID_MISC must be `*:MILK` (:98-104). **There is no location check** |
| corpses | CORPSE, **REMAINS** (:79-84) | not `flags.in_building` (:108-114) |
| usable-parts / unusable-parts | CORPSEPIECE (:86-90) | not in a building. "Usable" means one of the `corpse_flags` plant, silk, leather, bone, shell, wood, soap, tooth, horn, pearl, skull, hair_wool, yarn, and not `dead_dwarf` or `unbutchered` (:116-148) |

### Wear model

- Default (:156-163): each cycle `wear_timer += 1`. When it passes 24, wear goes up by 1 and the timer resets. The item
  is deleted when `wear > 3`. That makes **100 cycles from fresh to gone**: about 100 days at frequency 1, 15 days at
  0.15, and 300 days at 3.
- Clothes (:151-154): `wear_timer = ceil(wear_timer * (wear + 0.5))`, which speeds up DF's own wear counter. The item
  is deleted at `wear > 2` (XX).
- Deletion goes through `dfhack.items.remove(item)` (:174-177), which removes any job on the item, detaches it, and sets
  `forbid`, `hidden`, `removed` and `garbage_collect` (Items.cpp:1044-1063). Items already flagged `garbage_collect` are
  skipped. **Each deletion prints a console line**: `deteriorate: <item> crumbles away to dust`.

### Timers and persistence

- One `dfhack.timeout(n, 'ticks', ...)` chain per category (`event_loop` :208-224). The interval is
  `max(1, floor(1200 * frequency))` ticks. Tick timers are cancelled on map or world unload (LuaTools.cpp:2039-2041) and
  rebuilt from `SC_MAP_LOADED` (:263-279). They advance only while the game runs.
- `last_cycle_tick` is a normalized tick (`ReadCurrentTick + 403200 * year`, :202-204). It is saved with the rest of the
  state through `dfhack.persistent.saveSiteData('deteriorate', state)` (:48-50), per fort. A reload therefore resumes
  the cycle phase.
- `dfhack.timeout_active(id, nil)` cancels a category (:233-239).

## Side effects, gotchas

- **Permanent**: deleted items are gone, and the wear and `wear_timer` values it adds stay in the save even after you
  disable the tool.
- **`food` has no location filter.** Stockpiled, barrelled and carried food all rot, including **every EGG, fertile
  nest-box clutches among them**, and every PLANT. The docs say "all food". The practical result is that a `food`
  setting can stop egg-laying breeding and empty the larder.
- `corpses` includes REMAINS (vermin remains) and the corpses of your own dwarves that are not entombed. The tool does
  not check for active butchering or hauling jobs; `Items::remove` deletes such jobs.
- "Entombed" is approximated by `flags.in_building` (a TODO at :106-107). A corpse in any building counts as entombed.
- Cost: each cycle scans whole item vectors for each enabled category. At `0.15 all` that is 5 categories every 180
  ticks. On item-heavy forts this is noticeable, and the console spam grows with each deletion.
- The test file `scripts/test/deteriorate.lua` is **stale**. It drives an old CLI (`start`, `stop`, `-t`, `--types`,
  `--freq`, for example :61, :88-111, :123-126) that the current script rejects with `unrecognized command`.

## Relevance to seasonal-wildlife and aquarium

- **It can delete experiment evidence.** Predation and vermin readouts that count corpses, CORPSEPIECEs or vermin
  REMAINS (the ECO kills, and "fort pets eat placed vermin") lose items once the tool's cycles add up. In our short
  cells (3,000 ticks) the default frequency of 1 day deletes nothing new: deletion needs 100 cycles of 1,200 ticks. The
  control-panel option "0.15 all" runs a cycle every 180 ticks and finishes a fresh corpse in about 18,000 ticks, and
  wear carries over between cells on the same save. Check `deteriorate status` on rig forts, or read the `deteriorate`
  site-data key, before trusting corpse counts across long sessions.
- **The `food` category removes FISH_RAW and FISH.** That includes fish caught from water we stock, and every EGG.
  Neither matters to population lists in `world.populations.all`, but it affects any "catch" or egg-based measurement.
- **Reusable**: its timer pattern is solid. A persisted `last_cycle_tick` plus `dfhack.timeout` re-armed in
  `SC_MAP_LOADED` and cancelled with `timeout_active(id, nil)` (:206-239, :263-279) resumes the cycle phase across a
  reload without drift. That is the same shape our daily job needs, and it is an alternative to repeat-util where
  phase matters.
- No interaction with the aquarium plugin. The tool deals only with items, never with tiles or liquids.
