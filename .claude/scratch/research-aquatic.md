# Aquatic & amphibious wildlife spawning in DF 53.16 / DFHack 53.16-r1.1

Research memo. Local sources only:

- Wiki clone: `/Users/nathanielcannon/Claude/Projects/DwarfCron/data/wiki/` (489 pages; **A–G only** — there is no `Fishing.md`, `Water.md`, `Wildlife.md`, `Surroundings.md`, `River.md`, `Ocean.md`, `Pool.md`. Every wiki citation below is to a page that actually exists in the clone.)
  - Caveat: the markdown conversion **stripped the token-name column** out of `Creature_token.md`'s tables (they were wiki template links). Token identity is recovered from alphabetical position plus description text; where I do that I mark it **[inferred from table position]**.
- Raws: `…/Dwarf Fortress/data/vanilla/vanilla_creatures/objects/creature_*.txt` (CRLF, cp437).
- DFHack: `/Users/nathanielcannon/Claude/GitRepos/dfhack-latest/`
- df-structures: `/Users/nathanielcannon/Claude/GitRepos/df-structures/` (HEAD `3bfa5aa`, 2026-09-07; content identical to `dfhack-latest/library/xml/`).

Measured facts from our rig are taken as given and referenced as **[measured]**.

---

## 0. The one-paragraph model

DF keeps three *separate* population pools, all reachable through `world.populations.all` (`local_population`, `df.wilderpop.xml:9`), distinguished by the `world_population_ref` in `local_population.population`:

| pool | discriminator | backing store |
|---|---|---|
| **region / surface** | `feature_idx == -1` **and** `cave_id == -1` | `world_region.population` (`df.region.xml:344`) |
| **local map feature** (rivers, brooks, pits, caves) | `feature_idx >= 0` | `feature.population` (`df.feature.xml:88`) |
| **cavern / magma layer** | `cave_id >= 0` | `world_underground_region.feature_init.feature.population` |

The resolution rule is spelled out as a code-helper in `df-structures/df.regionpop.xml:45-61`:

```lisp
(reg (or (when (/= $info.feature_idx -1)               ; -> feature_map[..].feature_init[..][feature_idx].feature
           ...)
         (awhen $info.cave_id.ref-target               ; -> underground region's feature
           $it.feature_init.feature)
         (find-instance $world_region                  ; -> region_map[x][y].region_id
                        $wdata.region_map[x][y].region_id)))
$reg.population[$]
```

Surface wildlife arrives in **waves** drawn from the region pool for the world tiles touching the embark (`plotinfo.border`, §5). That is exactly consistent with **[measured]**: only `feature_idx == -1 && cave_id == -1` entries produced surface arrivals, and cavern (`cave_id >= 0`) waves fire regardless of revelation.

---

## 1. How carp / otters / sharks / whales actually appear on a fortress map

### 1a. The wave mechanic — this is the whole answer for creature-units

`scripts/docs/fix/wildlife.rst:16-24` is the clearest statement of the mechanic anywhere in the local corpus:

> "Dwarf Fortress manages wildlife in 'waves'. A small group of creatures of a species that has population associated with a local region enters the map, wanders around for a while (or aggressively attacks you if it is an agitated group), and then leaves the map. Any members of the group that successfully leave the map will get added back to the regional population. … A new wave cannot enter until the previous group has been destroyed or has left the map, so wildlife activity effectively completely halts. This is DF :bug:`12921`."

Confirmed in code: `scripts/fix/wildlife.lua:47-63` (`refund_population`) walks `df.global.world.populations.all`, matches on the full six-tuple `region_x, region_y, feature_idx, cave_id, site_id, population_idx`, and does `population.quantity = math.min(population.quantity + count, population.quantity_max)`. So **a wave decrements `local_population.quantity`, and leaving the map refunds it.** `quantity >= 10000001` is the "uncounted / infinite" sentinel (`fix/wildlife.lua:51`; `world_population.count_min`/`count_max` init-value `10000001`, `df.regionpop.xml:22-23`).

The per-wave selection algorithm is described on the wiki under FREQUENCY, `Creature_token.md:536` **[inferred from table position: this is the FREQUENCY entry]**:

> "In Fortress Mode, the game will try and spawn large wildlife (creatures with [LARGE_ROAMING] or [LARGE_PREDATOR]) in fairly regular waves. These waves include […] so a lion does not compete for selection with a gazelle. When the game decides it needs to spawn in a fresh wave of e.g. [x] creatures, it will select one of the creatures available to it from the lists for that sub-region at random, with all creatures weighted equally. Once it has selected a creature, it then effectively rolls a d100 against the relevant creature's [FREQUENCY]. …"

And the per-sub-region list construction, `Creature_token.md:534`:

> "Each sub-region in the world will attempt to fill lists of wildlife. There are five lists […] The game will attempt to place seven creatures in each list for each sub-region."

`Creature_token.md:771` (LARGE_PREDATOR entry): "A single biome supports 7 large predator species, picking randomly and rolling a d100 under its [FREQUENCY] to add it until all 7 slots are filled." And `Creature_token.md:770`: "In fortress mode, only one group of 'large predators' (possibly two groups on 'savage' maps) will appear on any given map."

### 1b. Why river creatures never arrive but ocean/lake ones should

**The key wiki line is `Creature_token.md:779`**, inside the LARGE_ROAMING entry **[inferred from table position — the entry beginning "This is the core requisite tag allowing the creature to spawn as a wild animal in the appropriate biomes"]**:

> "**Large roamers are not able to spawn in Pool biomes as they do not connect to the edge of the map and are too small, Lake biomes are a suitable alternative.**"

That is the wiki's own statement of the edge-connectivity requirement. It names Pools, but the same structural fact distinguishes rivers from lakes/oceans in our data:

- A **river or brook on the local map is a map feature** — `feature_type::outdoor_river` (`df.feature.xml:48`), class `feature_outdoor_riverst` (`df.feature.xml:110`), which inherits `feature`'s own `population` vector (`df.feature.xml:88`). Hence river populations carry `feature_idx >= 0`. **[measured]**: those entries produced zero arrivals in 8 × 20,000-tick replicates.
- An **ocean or lake is a region biome**, not a feature. `Maps::getBiomeTypeWithRef` (`library/modules/Maps.cpp:1297-1370`) derives `LAKE_*` from `region->flags.is_set(region_map_entry_flags::is_lake)` and `OCEAN_*` from `region->elevation < 100`. **`RIVER_*` and `POOL_*` are never returned by that function at all** (grep for `RIVER_|POOL_` in `Maps.cpp` returns nothing). Ocean/lake fish therefore live in `world_region.population` with `feature_idx == -1` — **[measured]** exactly what we saw.

**Conclusion (partly inferred):** the surface wave machinery draws from the *region* pool only, so the ordinary surface path can deliver ocean fish, sharks, whales and rays on an ocean embark, and lake fish on a lake embark, but **cannot** deliver river carp/otter/hippo/alligator/platypus, because those live on the river *feature*'s pool. **This is not directly proven** — **[measured]** only closed the negative half (rivers never fire); the ocean/lake aquatic surface entries were never tested with the water open. That is experiment E1.

Corroborating in-game text for edge-of-water arrival exists for the cavern case, `Cave_crocodile.md:3`:

> "The largest creatures inhabiting the first cavern level, **they'll spawn individually out of the edges of the water** and seek for dwarves to attack…"

### 1c. Vermin fish (fishing) vs creature units — completely separate systems

These are different `world_population_type` values (`df.regionpop.xml:2-12`):

```
Animal (ROAMING) | Vermin (VERMIN) | VerminInnumerable (SOIL) | ColonyInsect (SOIL_COLONY) | Tree | Grass | Bush
```

- **Fishing catches only `VERMIN_FISH` creatures.** Repeated verbatim across the clone: `Cod.md:5` "your fisherdwarves can only catch vermin fish… Capturing them with a fishery will not work, as that too is restricted to vermin"; `Bluefish.md:3`, `Bluefin_tuna.md:3`, `Coelacanth.md:3`, `Conger_eel.md:3` "As non-vermin fish, X can't be fished by fisherdwarves, but can be caught with the use of a drowning chamber"; same line on `Blue_shark.md:3`, `Bull_shark.md:3`, `Angelshark.md:3`, `Common_skate.md:3`, `Blacktip_reef_shark.md:3`, `Basking_shark.md:5`. `Cage.md:120`: "Aquariums cannot be used to store large fish (they will drown), though vermin fish work just fine."
- Live-fish trapping is a *fishery* job against a fishing zone: `Animal_trap.md:9` "to catch vermin in water, order the task 'Capture a live fish' from a fishery. A fisherdwarf will then take a trap and capture an **aquatic vermin** from a fishing zone."
- There is a per-feature fishing prohibition list in plotinfo: `no_fishing_feature_x/_y/_idx/_layer` (`df.plotinfo.xml:1009-1012`, bay12 `fishing_prohibition_*`). Worth dumping on an ocean/lake fort.
- In the raws, vermin fish carry `VERMIN_FISH` + `FISHITEM` (e.g. `POND_TURTLE`, `creature_riverlakepool_new.txt:1034`) or `VERMIN_GROUNDER` + `FISHITEM` (`FISH_LUNGFISH`, `creature_small_riverlake.txt:5`; `OLM`, `creature_subterranean.txt:1385`). `SHARK_GREAT_WHITE`, `FISH_CARP`, `ORCA` etc. have **no** vermin flag — they are `Animal`-type populations and spawn as real units.
- Vermin are also excluded from the arena/sandbox spawn list: `scripts/gui/sandbox.lua:381-383` filters out `cre.flags.VERMIN_GROUNDER`, `VERMIN_SOIL`, `DOES_NOT_EXIST`, `EQUIPMENT_WAGON`.

Seasonal vermin-fish migration is a real mechanic: `Creature_token.md:325` (CLUSTER_NUMBER entry) — "**Vermin fish with this token in combination with temperate ocean and river biome tokens will perform seasonal migrations.**"

### 1d. Do carp attack?

No, not any more. `Carp.md:5`: "Carp are nearly as heavy as dwarves but are entirely benign, and **due to being aquatic, they will never attack civilians out of their own volition.** … Undead carp, however, are a different story." Raws agree: `FISH_CARP` has `[BENIGN]` and no `LARGE_PREDATOR` (`creature_large_riverlake.txt:236`).

---

## 2. Token semantics, and 15 creatures with their tokens

### Token meanings (wiki `Creature_token.md`, token names **[inferred from table position]**)

| Token | Line | Description (verbatim) |
|---|---|---|
| `AQUATIC` | `Creature_token.md:77` | "Enables the creature to breathe in water, but causes it to air-drown on dry land." |
| `AMPHIBIOUS` | `Creature_token.md:36` | "Allows a creature to breathe both in and out of water (unlike [AQUATIC]) - does not prevent drowning in magma." |
| `IMMOBILE_LAND` | `Creature_token.md:723` | "The creature is immobile while on land. **Only works on [AQUATIC] creatures which can't breathe on land.**" |
| `UNDERSWIM` | `Creature_token.md:1555` | "The creature is displayed as blue when in 7/7 water. Used on fish and amphibious creatures which swim under the water." (purely cosmetic) |
| `SWIMS_INNATE` | `Creature_token.md:1456` | "The creature naturally knows how to swim perfectly and does not use the swimmer skill… **However, Fortress mode AI never paths into water anyway, so it's less useful there.**" |
| `SWIMS_LEARNED` | `Creature_token.md:1459` | "The creature swims only as well as their present swimming skill allows them to." |
| `IMMOBILE` | `Creature_token.md:719` | "The creature cannot move. Found on sponges. Will also stop a creature from breeding in fortress mode." |
| `BEACH_FREQUENCY` | `Creature_token.md:121` | "Creature may be subject to beaching, becoming stranded on shores, where they will eventually air-drown. … Presumably requires the creature to be [AQUATIC]. Used by orcas, sperm whales and sea nettle jellyfish." |
| `LARGE_PREDATOR` | `Creature_token.md:770` | see §1a / §4 |
| `AMBUSHPREDATOR` | `Creature_token.md:33` | "Makes the creature start out hidden and remain near its original location until its prey draws near." |
| `BENIGN` | `Creature_token.md:124` | "non-aggressive by default, and will never automatically be engaged by companions or soldiers, running away from any creatures that are not friendly to it, and will only defend itself if it becomes enraged." |
| `PRONE_TO_RAGE` | `Creature_token.md:1225` | "Creature has a percentage chance to flip out at visible non-friendly creatures. Enraged creatures attack anything regardless of timidity and get a strength bonus." |
| `CARNIVORE` | `Creature_token.md:246` | "Creature *only* eats meat." |
| `BONECARN` | `Creature_token.md:192` | "Creature eats bones. Implies [CARNIVORE]. **Currently does not work due to a bug.**" |
| `UNDERGROUND_DEPTH` | `Creature_token.md:1552` | "0 is actually 'above ground'… 1-3 are the respective cavern levels, 4 is the magma sea and 5 is the HFS… **without [x] they will only spawn from the map edges.**" |

**Important negative:** none of `AQUATIC`, `AMPHIBIOUS`, `IMMOBILE_LAND`, `UNDERSWIM`, `SWIMS_INNATE` is documented as affecting *spawn eligibility*. Spawn eligibility is `LARGE_ROAMING`/`LARGE_PREDATOR` + `BIOME:` + `FREQUENCY` (`Creature_token.md:534-536, 770-779`). The swim tokens govern **breathing** and **land mobility** only. The one pathing note is `SWIMS_INNATE`'s "Fortress mode AI never paths into water anyway."

### The 15 creatures, exact raws

Extracted by script over all `creature_*.txt`. Biome and flag lists are verbatim token text.

Gotcha for our tool: vanilla has **no `[CREATURE:OTTER]`** — the raws use `RIVER OTTER` and `SEA OTTER`, and **creature IDs can contain spaces** (also `SNAPPING TURTLE`, `ALLIGATOR SNAPPING TURTLE`). A naive `[A-Z_]+` regex silently drops them.

| # | creature (raw ID) | file:line | BIOME tokens | water / behaviour tokens | pop / cluster |
|---|---|---|---|---|---|
| 1 | `RIVER OTTER` | `creature_riverlakepool_new.txt:10` | `ANY_POOL`, `ANY_LAKE`, **`ANY_RIVER`** | `AMPHIBIOUS`, `SWIMS_INNATE`, `BENIGN`, `BONECARN`, `NATURAL` | 10:20 / 1:4 |
| 2 | `SEA OTTER` | `creature_riverlakepool_new.txt:107` | `OCEAN_TEMPERATE` | `AMPHIBIOUS`, `SWIMS_INNATE`, `BENIGN`, `BONECARN` | 10:20 / 5:10 |
| 3 | `GIANT_OTTER` | `creature_riverlakepool_new.txt:230` | *(inherited)* `COPY_TAGS_FROM:RIVER OTTER` → pools/lakes/rivers | inherits `AMPHIBIOUS`, `SWIMS_INNATE`; `MOUNT_EXOTIC`, `PETVALUE:500` | 10:20 / 1:4 |
| 4 | `FISH_CARP` | `creature_large_riverlake.txt:236` | `RIVER_TEMPERATE_FRESHWATER`, `RIVER_TROPICAL_FRESHWATER`, `LAKE_TEMPERATE_FRESHWATER`, `LAKE_TROPICAL_FRESHWATER` | **`AQUATIC`, `UNDERSWIM`, `IMMOBILE_LAND`**, `SWIMS_INNATE`, `BENIGN`, `MEANDERER` | 15:30 / 5:10 |
| 5 | `FISH_STURGEON` | `creature_large_ocean.txt:1767` | `OCEAN_ARCTIC`, `OCEAN_TEMPERATE`, `RIVER_TEMPERATE_{FRESH,BRACKISH,SALT}WATER` | `AQUATIC`, `UNDERSWIM`, `IMMOBILE_LAND`, `SWIMS_INNATE`, `BENIGN` | 15:30 / — |
| 6 | `FISH_PIKE` | `creature_large_riverlake.txt:408` | `RIVER_TEMPERATE_{FRESH,BRACKISH}`, `LAKE_TEMPERATE_{FRESH,BRACKISH}` | `AQUATIC`, `UNDERSWIM`, `IMMOBILE_LAND`, `SWIMS_INNATE`, `BENIGN`, `MEANDERER` | 15:30 / — |
| 7 | `FISH_STINGRAY` | `creature_large_ocean.txt:1607` | `OCEAN_TROPICAL`, `RIVER_TROPICAL_{F,B,S}`, `LAKE_TROPICAL_{F,B,S}` | `AQUATIC`, `UNDERSWIM`, `IMMOBILE_LAND`, `SWIMS_INNATE`, `BENIGN`, `MEANDERER` | 15:30 / — |
| 8 | `SHARK_GREAT_WHITE` | `creature_large_ocean.txt:218` | `OCEAN_TEMPERATE`, `OCEAN_TROPICAL` | `AQUATIC`, `UNDERSWIM`, `IMMOBILE_LAND`, **`LARGE_PREDATOR`**, `SWIMS_INNATE` | 15:30 / — |
| 9 | `SHARK_BULL` | `creature_large_ocean.txt:996` | `OCEAN_TROPICAL` | `AQUATIC`, `UNDERSWIM`, `IMMOBILE_LAND`, `LARGE_PREDATOR`, `SWIMS_INNATE` | 15:30 / — |
| 10 | `ORCA` | `creature_ocean_new.txt:572` | **`ANY_OCEAN`** | `AQUATIC`, `UNDERSWIM`, `IMMOBILE_LAND`, `BEACH_FREQUENCY:10`, `BENIGN`, `SWIMS_INNATE` | 15:30 / 3:9 |
| 11 | `SPERM_WHALE` | `creature_ocean_new.txt:896` | `ANY_OCEAN` | `AQUATIC`, `UNDERSWIM`, `IMMOBILE_LAND`, `BEACH_FREQUENCY:10`, `CARNIVORE`, `BENIGN`, `MEANDERER`, `SWIMS_INNATE` | 15:30 / **1:1** |
| 12 | `ALLIGATOR` | `creature_large_temperate.txt:1373` | `SWAMP_{TEMP,TROP}_FRESHWATER`, `MARSH_{TEMP,TROP}_FRESHWATER`, `RIVER_{TEMP,TROP}_{FRESH,BRACKISH}WATER` | **`AMPHIBIOUS`** (no `AQUATIC`), `LARGE_PREDATOR`, `CARNIVORE`, `MEANDERER`, `SWIMS_INNATE`, `MOUNT_EXOTIC` | 5:10 / 1:3 |
| 13 | `CROCODILE_SALTWATER` | `creature_large_tropical.txt:2963` | `SWAMP_TROPICAL_{FRESH,SALT}`, `MARSH_TROPICAL_{FRESH,SALT}`, `SWAMP_MANGROVE`, `RIVER_TROPICAL_{S,B,F}` | `AMPHIBIOUS`, `LARGE_PREDATOR`, `CARNIVORE`, `MEANDERER`, `FREQUENCY:5`, `SWIMS_INNATE` | 5:10 / 1:3 |
| 13b | `CROCODILE_CAVE` | `creature_subterranean.txt:5` | **`SUBTERRANEAN_WATER`** | `AMPHIBIOUS`, `LARGE_PREDATOR`, `CARNIVORE`, `UNDERGROUND_DEPTH:1:2`, `SWIMS_INNATE` | 10:20 / — |
| 14 | `HIPPO` | `creature_large_riverlake.txt:5` | `RIVER_TROPICAL_{S,B,F}`, `LAKE_TROPICAL_{S,B,F}` | `AMPHIBIOUS`, `BENIGN`, `MEANDERER`, `SWIMS_INNATE` | 15:30 / 3:7 |
| 15 | `PLATYPUS` | `creature_large_riverlake.txt:504` | **`ANY_RIVER`** | `AMPHIBIOUS`, `UNDERSWIM`, `BENIGN`, `FREQUENCY:10`, `SWIMS_INNATE` | 15:30 / 1:1 |
| 16 | `BEAVER` | `creature_riverlakepool_new.txt:499` | `ANY_TEMPERATE_LAKE`, `ANY_TEMPERATE_RIVER` | **no `AQUATIC`, no `AMPHIBIOUS`**; `SWIMS_INNATE`, `BENIGN`, `MEANDERER` | 15:30 / 3:10 |
| 17 | `SNAPPING TURTLE` | `creature_riverlakepool_new.txt:262` | `RIVER_TEMPERATE_{F,B}`, `LAKE_TEMPERATE_{F,B}`, `POOL_TEMPERATE_{F,B}` | `AMPHIBIOUS`, `CARNIVORE`, `SWIMS_INNATE` | 25:50 / — |
| 18 | `ALLIGATOR SNAPPING TURTLE` | `creature_riverlakepool_new.txt:353` | same as #17 | `AMPHIBIOUS`, `CARNIVORE`, `SWIMS_INNATE` | 25:50 / — |
| — | `POND_TURTLE` *(vermin contrast)* | `creature_riverlakepool_new.txt:1034` | `ANY_POOL` | **`VERMIN_FISH`, `FISHITEM`**, `AMPHIBIOUS`, `CARNIVORE`, `BENIGN` | 250:500 / — |

**Observations**

- `AQUATIC` + `UNDERSWIM` + `IMMOBILE_LAND` travel as a fixed triple on every true fish/shark/whale. Any creature carrying it is helpless and drowning the instant it is on land — decisive for any "place a shark" tool.
- Only two of the listed creatures use the **`BIOME:ANY_RIVER`** set token: `RIVER OTTER` and `PLATYPUS`. Everything else spells out `RIVER_<climate>_<salinity>` explicitly. Across all raws there are 40 `BIOME:ANY_{RIVER,LAKE,POOL,OCEAN}` lines total.
- `BEAVER` has **neither** `AQUATIC` nor `AMPHIBIOUS` — a lake/river creature that is a plain land animal with `SWIMS_INNATE`. Matches `Beaver.md:3` ("benign meanderers").
- Biome IDs: 42-47 are the six `RIVER_*`, 30-35 the six `POOL_*` (`Biome_token.md:30-47`); sets at `Biome_token.md:135-141`: `ANY_RIVER` = 42-47, `ANY_POOL` = 30-35, `ANY_OCEAN` = 27-29, `ANY_LAKE` = 36-41. Crucially `Biome_token.md:118`: the "all biomes" set is "0-29, 36-41 — **All biomes excluding pools, rivers, and underground features**". DF's own biome-set vocabulary treats rivers and pools as second-class, exactly as the feature/region split predicts.

---

## 3. DFHack: creating or placing a wild unit directly

### 3a. `modtools/create-unit` (and `spawnunit`, its thin wrapper)

`scripts/spawnunit.lua` is a 49-line argument shim that calls `dfhack.run_script('modtools/create-unit', …)` (`spawnunit.lua:49`). Note its doc is `:tags: unavailable` (`scripts/docs/spawnunit.rst:6`).

**How it actually creates the unit** — it drives the vanilla *arena* spawn path, `scripts/modtools/create-unit.lua:155-305`:

```lua
local arenaSpawn = df.global.world.arena_spawn
arenaSpawn.type = 0; arenaSpawn.filter = ""; arenaSpawn.interaction = -1
arenaSpawn.tame = df.world.T_arena_spawn.T_tame.NotTame
arenaSpawn.race:insert(0, race_id)                           -- :227
arenaSpawn.caste:insert(0, caste_id)                         -- :229
arenaSpawn.creature_cnt:insert('#', 0)
local dwarfmodeScreen = df.viewscreen_dwarfmodest:new()      -- :234
df.global.plotinfo.main.mode = df.ui_sidebar_mode.LookAround
df.global.gametype = df.game_type.DWARF_ARENA                -- :240
df.global.cursor.x/.y/.z = pos.x/pos.y/pos.z                 -- :244-246  (cursor IS the spawn point)
gui.simulateInput(dwarfmodeScreen, 'D_LOOK_ARENA_CREATURE')  -- :292  open arena spawn menu
gui.simulateInput(dfhack.gui.getCurViewscreen(), 'SELECT')   -- :294  create the creature
local unit = df.unit.find(df.global.unit_next_id-1)          -- :301
```

Comment at `:243`: "move cursor to location instead of moving unit later, corrects issue of missing mapdata when moving the created unit." **This matters for aquatic placement: do not teleport a fish after creation; set the cursor to the water tile first.**

**Location filtering** — `isValidSpawnLocation(pos, locationType)` (`create-unit.lua:387-405`) only understands `'Open'` (tile `basic_shape == Open`) and `'Walkable'` (`tileShapeAttrs.walkable`). A flooded floor tile *is* walkable, so `-locationType Walkable` will accept water, but there is **no** water-aware mode. `'Any'` (`:277`) skips validation entirely and is the right choice for an `AQUATIC` unit in 7/7 water.

**`wildUnit(unit)` — `create-unit.lua:914-933`, the exact field writes:**

```lua
function wildUnit(unit)
  local casteFlags = unit.enemy.caste_flags
  if not(casteFlags.CAN_SPEAK or casteFlags.CAN_LEARN) then
    if dfhack.isSiteLoaded() then
      local site = dfhack.world.getCurrentSite()
      unit.animal.population.region_x = site.pos.x
      unit.animal.population.region_y = site.pos.y
    end
    unit.animal.population.unk_28 = -1
    unit.animal.population.population_idx = -1  -- Eventually want to make a real population
    unit.animal.population.layer_depth = -1     -- Eventually this should be a parameter
    unit.animal.leave_countdown = 99999         -- Eventually this should be a parameter
    unit.flags2.roaming_wilderness_population_source = true
    unit.flags2.roaming_wilderness_population_source_not_a_map_feature = true
  end
end
```

Two defects worth knowing:

1. **`unk_28` is stale.** Current `world_population_ref` has no `unk_28`; the fields at that region are `feature_idx` (int16, `df.regionpop.xml:39`) and `cave_id` (int32, `:41`). Depending on how the Lua binding resolves it, that line either errors or writes the wrong field. **Our tool should write `feature_idx = -1`, `cave_id = -1`, `site_id`, `population_idx` explicitly.**
2. **`population_idx = -1` means the unit is not wildlife as far as DFHack is concerned.** `Units::isWildlife` (`library/modules/Units.cpp:596-602`):

```cpp
bool Units::isWildlife(df::unit *unit) {
    return unit->animal.population.population_idx >= 0
        && !isMerchant(unit) && !isForest(unit) && !isFortControlled(unit);
}
```

So a `create-unit --wild` fish is skipped by `fix/wildlife`, by the notify overlay (`scripts/internal/notify/notifications.lua:138`), and by `spectate`'s wildlife filter (`plugins/spectate.cpp:455`). It also can never refund a population slot, because `refund_population` matches on `population_idx` (`fix/wildlife.lua:57`). **To make a genuinely integrated wild unit you must point `population_idx` at a real index into `world_region.population` (or the feature/cave equivalent) and decrement that `local_population.quantity` yourself.**

`domesticateUnit` (`create-unit.lua:895-912`) is the inverse: `population_id = -1`, zeroes all of `animal.population`, sets `flags1.tame` and `training_level = Domesticated`.

Timers: `unit.animal.leave_countdown` — "once 0, it heads for the edge and leaves"; `unit.animal.vanish_countdown` — "once 0, it vanishes in a puff of smoke" (`df.unit.xml:2696-2698`). `setVanishCountdown` at `create-unit.lua:974`.

### 3b. `gui/sandbox`

`gui/sandbox` does **not** create units itself. It configures `df.global.world.arena` / `game.main_interface.arena_unit` (`sandbox.lua:363-425`, `init_arena`) and then fires the vanilla interface action `ARENA_CREATE_CREATURE` (`sandbox.lua:133`), letting the player click a tile. Afterwards `finalize_units` (`sandbox.lua:76-91`) walks `first_created_unit_id … df.global.unit_next_id-1` and applies a disposition:

```lua
local function finalize_animal(unit, disposition)          -- sandbox.lua:48-60
    if disposition == DISPOSITIONS.HOSTILE or disposition == DISPOSITIONS.HOSTILE_UNDEAD then
        unit.flags4.agitated_wilderness_creature = true
    elseif disposition == DISPOSITIONS.WILD then
        unit.flags2.roaming_wilderness_population_source = true
        unit.flags2.roaming_wilderness_population_source_not_a_map_feature = true
        unit.animal.leave_countdown = 20000
    elseif disposition == DISPOSITIONS.FRIENDLY then   -- noop
    elseif disposition == DISPOSITIONS.FORT then makeown.make_own(unit) end
end
```

Sentients take a different branch (`sandbox.lua:33-46`): `flags1.active_invader` + `marauder` for hostile; `flags2.visitor` + `flags3.guest` + `leave_countdown = 20000` for wild.

`finalize_animal` **never touches `animal.population`**, so sandbox units are also `isWildlife() == false`.

### 3c. `force Wildlife` — the closest thing to "make a wave happen now"

`scripts/force.lua:1,22-23` → `reqscript('fix/wildlife').free_all_wildlife(all)`. It does not spawn anything; it *unblocks* the queue by detaching every currently-stuck wildlife unit:

```lua
local function detach_unit(unit)                           -- fix/wildlife.lua:66-70
    unit.flags2.roaming_wilderness_population_source = false
    unit.flags2.roaming_wilderness_population_source_not_a_map_feature = false
    refund_population{race=unit.race, pop=unit.animal.population, known=true, count=1}
end
```

`scripts/docs/force.rst:43-48, 62-63`: "``force Wildlife`` — Allow additional wildlife to enter the map. Only affects areas that you can see… ``force Wildlife all`` — even in areas you haven't explored yet. … **The ``Wildlife`` event may take up to 100 ticks to take effect.**" The 100-tick figure suggests the wave scheduler runs on roughly a 100-tick cadence — useful for sizing experiment polling.

### 3d. Relevant exported API

`dfhack.units.isWildlife` (`LuaApi.cpp:2217`, `Units.h:165`), plus `isAgitated`, `isDanger`, `isAnimal`, `isHidden`, `isActive`, `isKilled`, `getRaceReadableNameById` — all in `library/modules/Units.cpp`.

---

## 4. Wild predators vs wild prey

### The governing rule, stated on the wiki

`Faction.md:200` (footnote 5 of the hostility matrix) — the most direct statement in the clone:

> "**[LARGE_PREDATOR]s will attack anything significantly smaller than themselves. In most other cases, wildlife will flee from non-[BENIGN] wildlife. Two [BENIGN] wild animals will ignore each other.**"

Supporting:

- `Creature_token.md:770` (LARGE_PREDATOR): "Will attack other creatures that are smaller than it. **Tamed large predators will still attack wildlife.**"
- `Creature_token.md:33` (AMBUSHPREDATOR): "Makes the creature start out hidden and remain near its original location until its prey draws near."
- `Creature_token.md:124` (BENIGN): "non-aggressive by default, and will never automatically be engaged by companions or soldiers, running away from any creatures that are not friendly to it, **and will only defend itself if it becomes enraged**."
- `Creature_token.md:1225` (PRONE_TO_RAGE): "percentage chance to flip out at visible non-friendly creatures. Enraged creatures attack anything regardless of timidity…" — cf. `Badger.md:21` ("badger storms"), `Giant_badger.md:3`.
- `Entity_token.md:266` / `DF2014_Entity_token.md:254` (AT_PEACE_WITH_WILDLIFE **[inferred]**): "Will not attack wildlife, and will not be attacked by them, even if you have them in your party." Cats have the creature-level analogue — `Cat.md:13`: "Thanks to their [token], cats will not perturb natural creatures."
- `BONECARN` is **non-functional**: `Creature_token.md:192` "Implies [CARNIVORE]. **Currently does not work due to a bug.**" Relevant because `RIVER OTTER`, `SEA OTTER` and `WOLF` all carry it.

**For our aquatic case:** sharks are `LARGE_PREDATOR`; carp/pike/sturgeon/stingray are `BENIGN`. `Faction.md:200` predicts sharks *should* attack fish in the same water. Alligator / saltwater croc / cave croc are `AMPHIBIOUS` + `LARGE_PREDATOR` + `CARNIVORE`. Note `Creature_token.md:770`: "only one group of 'large predators' (possibly two groups on 'savage' maps) will appear on any given map" — so on a natural ocean fort, at most one shark group at a time.

### The "agitated" system — the other source of hostile wildlife

Wiki, `Creature.md:68`:

> "Disruption of the environment in a savage biome, such as woodcutting or **fishing**, may cause the appearance of 'agitated' or 'irritated' animals. Agitated animals will directly seek out and attack dwarves, instead of their normal behavior. Agitation rate and threshold can be adjusted in the difficulty settings."

`Embark.md:87`: the enemies "Off" preset "prevents sieges, megabeast attacks, werebeast attacks, and agitated wildlife."

Code:

- Flag: `unit.flags4.agitated_wilderness_creature` (`df.unit.xml:1472`, bay12 `AGITATED_WILDERNESS_CREATURE`; the `unit_flags4` bitfield begins at `df.unit.xml:1456`).
- `Units::isAgitated` (`Units.cpp:604-607`) is exactly that flag; `Units::isDanger` (`Units.cpp:656-669`) includes `isAgitated(unit)`; `Units::isFortControlled` (`Units.cpp:168-186`) returns false for agitated units.
- Surface irritation counter: `df.global.plotinfo.outdoor_irritation` vs `custom_difficulty.wild_irritate_min` (`scripts/agitation-rebalance.lua:112-118`).
- Cavern irritation is **per feature**: `feature.irritation_level`, "divide by 10k for attack chance, max 100k" (`df.feature.xml:90`), plus `irritation_attacks` "maxes at 10?" (`:91`). `agitation-rebalance.lua:121-129, 268-272` read `map_feature.feature.irritation_level` on each `feature_init_subterranean_from_layerst`; `get_cavern_attack_independent_natural_chance` = `min(1, irritation/10000)` (`:268-270`).
- `Units::isAnimal` (`Units.cpp:567-578`) keys partly on `flags2.roaming_wilderness_population_source`.

### Structures for hostility bookkeeping

`unit.enemy.caste_flags` is a *cached copy* of the caste raw flags, consulted throughout `Units.cpp` (e.g. `:570`, `:634`); `unit.uwss_add_caste_flag` / `uwss_remove_caste_flag` are the curse/were overlays (`Units.cpp:114-115`). `isOpposedToLife` folds into both `isFortControlled` and `isDanger`.

---

## 5. `world_data.region_map[x][y]`, ocean/lake biomes, and the water map edge

### There is no stored biome field

`region_map_entry` (`df.region.xml:278-313`) stores `elevation`, `rainfall`, `vegetation`, `temperature`, `evilness`, `drainage`, `volcanism`, `savagery`, `salinity`, `snowfall`, a `df-flagarray flags`, plus `region_id` (→ `world_region`), `landmass_id`, `geo_index`. **There is no `biome_type` member.** `world_data.region_map` is a pointer-to-pointer array (`df.region.xml:802-803`).

Biome is *computed*: `Maps::getBiomeTypeWithRef(region_x, region_y, region_ref_y)`, `library/modules/Maps.cpp:1297+`, header comment "Based on reverse-engineering of FUN_140bfe460 (v50.11 win64 Steam)":

```cpp
if (region->flags.is_set(df::region_map_entry_flags::is_lake)) {
    if      (region->salinity > 65) return tropical? LAKE_TROPICAL_SALTWATER    : LAKE_TEMPERATE_SALTWATER;
    else if (region->salinity < 33) return tropical? LAKE_TROPICAL_FRESHWATER   : LAKE_TEMPERATE_FRESHWATER;
    else                            return tropical? LAKE_TROPICAL_BRACKISHWATER: LAKE_TEMPERATE_BRACKISHWATER;
}
if (region->elevation > 149) return MOUNTAIN;
if (region->elevation < 100) {                          // <-- OCEAN test
    if (potential_tropical)            return OCEAN_TROPICAL;
    else if (region->temperature < -4) return OCEAN_ARCTIC;
    else                               return OCEAN_TEMPERATE;
}
```

(`Maps.cpp:1342-1364`; tropicality from `world_data.flip_latitude` / `world_height` / `region->temperature`, `:1305-1340`.) `elevation` comment at `df.region.xml:284`: "0-99=Ocean, 150+=Mountains, 100-149: all other biomes."

**`RIVER_*` and `POOL_*` are never produced by this function.** Rivers appear only as `region_map_entry_flags::has_river`, `river_up/down/left/right`, `is_brook`, `orig_river_source` (`df.region.xml:207-224`). That is the structural reason river fauna live on a feature, not a region.

Per-tile biome on the loaded map goes through `Maps::getBlockTileBiomeRgn` (`Maps.cpp:979-993`): `designation.bits.biome` (0-8) → `block->region_offset[idx]` → `getBiomeRgnPos(block->region_pos, idx)` with the 3×3 `biome_offsets` table (`Maps.cpp:960-964`). **[measured]** "the site's tiles and neighbouring block-biome tiles" is exactly this 3×3 neighbourhood.

### Map-edge entry points

`df.plotinfo.xml:983-1006` is the decisive structure:

```xml
<static-array name='border' count='4' comment='region coords for map edge tiles, for choosing wilderpops'>
    <static-array count='768' type-name='coord2d'/>
</static-array>
<compound type-name='coord_path' name='wilderpop_enter'/>
<compound name='map_edge'>
    <static-array name='layer_x' original-name='connected_enter_x' count='5'><stl-vector type-name='int16_t'/></static-array>
    <stl-vector type-name='int16_t' name='surface_x' original-name='connected_enter_x_5'/>
    <static-array name='layer_y' original-name='connected_enter_y' count='5'>…</static-array>
    <stl-vector type-name='int16_t' name='surface_y' original-name='connected_enter_y_5'/>
    <static-array name='layer_z' original-name='connected_enter_z' count='5'>…</static-array>
    <stl-vector type-name='int16_t' name='surface_z' original-name='connected_enter_z_5'/>
</compound>
```

So: **`plotinfo.border[0..3]` are the four edges' world-tile coords, used specifically "for choosing wilderpops"**; `plotinfo.map_edge.surface_x/y/z` is the precomputed list of *connected* surface entry tiles; `layer_x/y/z[0..4]` is the same per underground layer (Cavern 1-3, magma sea, underworld); `plotinfo.wilderpop_enter` is a `coord_path` of chosen entry positions. And `world_population_ref.layer_depth` carries the comment (`df.regionpop.xml:63`): "gets overwritten when creatures arrives on map, so it knows **which edge it should go to when it leaves**."

**Whether `surface_x/y/z` includes submerged water tiles on a coastal embark is the single most important unknown.** The wiki hint is `Creature_token.md:779` — pools are excluded *because* "they do not connect to the edge of the map" — which strongly implies the edge-connectivity test is done on *water* connectivity for water creatures, and that an ocean or lake that touches the edge passes. Also `Bridge.md:117`: "Walls cannot be built along map edges above ground, but raising bridges can. Because these bridges can be raised to act as walls, **they can be used to control where wildlife, enemies, and caravans spawn on the map edges**" — i.e. the entry-tile list is recomputed from map connectivity and is player-manipulable. **[inferred, untested]**

---

## Experiments this suggests

Run with the `df-rig` / `df-worldgen` skills. Baseline: two forts, **OCEAN** (needs `region.elevation < 100` on at least one embark tile) and **LAKE** (needs `region_map_entry_flags::is_lake`). Back up every save first.

### E1 — Does an ocean/lake surface wave ever arrive? (the untested half of our measurement)

The direct sequel to **[measured]**. On the OCEAN fort, leave the water fully open, wall off nothing, log arrivals for 8 × 20,000 ticks.

```lua
-- census the draw pool, split by pool class
local rows = {}
for i,p in ipairs(df.global.world.populations.all) do
  local r = p.population
  local cls = (r.feature_idx >= 0 and 'FEATURE') or (r.cave_id >= 0 and 'CAVE') or 'REGION'
  local name = p.race >= 0 and df.global.world.raws.creatures.all[p.race].creature_id or '?'
  table.insert(rows, ('%3d %-7s %-28s qty=%d/%d rx=%d ry=%d fi=%d cave=%d site=%d pidx=%d'):format(
    i, cls, name, p.quantity, p.quantity_max,
    r.region_x, r.region_y, r.feature_idx, r.cave_id, r.site_id, r.population_idx))
end
print(table.concat(rows,'\n'))
```

Poll for new units roughly every 100 ticks (the `force Wildlife` latency, `scripts/docs/force.rst:62-63`):

```lua
for _,u in ipairs(df.global.world.units.active) do
  if u.flags2.roaming_wilderness_population_source then
    print(df.global.world.raws.creatures.all[u.race].creature_id,
          u.animal.population.feature_idx, u.animal.population.cave_id,
          u.animal.population.population_idx, u.animal.leave_countdown,
          dfhack.units.isWildlife(u), dfhack.units.isAgitated(u))
  end
end
```

**Predicted:** sharks/whales/ocean fish arrive with `feature_idx == -1, cave_id == -1, population_idx >= 0`, and the matching `world.populations.all[i].quantity` decrements by the cluster size. If nothing arrives, the real blocker is not the pool class but **edge-connectivity of water**, which flips the whole model.

### E2 — Dump the surface entry-tile list and check for water

Run on both forts immediately after load. **This is the decisive test for question 5.**

```lua
local pi = df.global.plotinfo
print('#surface entries', #pi.map_edge.surface_x)
for i=0,#pi.map_edge.surface_x-1 do
  local x,y,z = pi.map_edge.surface_x[i], pi.map_edge.surface_y[i], pi.map_edge.surface_z[i]
  local b = dfhack.maps.getTileBlock(x,y,z)
  local tt = b and b.tiletype[x%16][y%16]
  local d  = b and b.designation[x%16][y%16]
  print(i,x,y,z, tt and df.tiletype[tt], d and d.flow_size, d and d.liquid_type)
end
for layer=0,4 do print('layer',layer,'#entries',#pi.map_edge.layer_x[layer]) end
print('wilderpop_enter len', #pi.wilderpop_enter.x)
for e=0,3 do print('border edge',e,'first coord', pi.border[e][0].x, pi.border[e][0].y) end
```

If `flow_size == 7` tiles appear in `surface_x/y/z` on the ocean fort, water creatures have a real edge to swim in from. Diff against an inland fort to see whether the list is water-inclusive at all.

### E3 — Make a river population behave like a region population

Probes whether the `feature_idx >= 0` exclusion **[measured]** is causal. On a river fort, take a river `local_population` (carp/otter) and rewrite its ref to the region form, then watch for arrivals.

```lua
for _,p in ipairs(df.global.world.populations.all) do
  local r = p.population
  if r.feature_idx >= 0 then
    -- record originals FIRST
    r.feature_idx = -1
    r.cave_id = -1
    -- population_idx must now index world_region.population of region_map[r.region_x][r.region_y].region_id
  end
end
```

Caveat: `population_idx` is pool-relative (`df.regionpop.xml:45-61`), so this is only meaningful if you also repoint `population_idx` at a valid `world_region.population` slot for the *same species*; otherwise the entry is corrupt. Safer variant: **append** a new region-class `local_population` for carp (E4) instead of mutating the river one.

### E4 — Synthesise a region population entry for a species not naturally present

The "put sharks on a lake" experiment. Two layers.

1. Add a `world_population` to the region's own vector so a valid `population_idx` exists:

```lua
local wd  = df.global.world.world_data
local pos = dfhack.world.getCurrentSite().pos
local reg = df.world_region.find(wd.region_map[pos.x][pos.y].region_id)
local wp  = df.world_population:new()
wp.type = df.world_population_type.Animal
wp.race = RACE_IDX                  -- e.g. SHARK_GREAT_WHITE
wp.count_min, wp.count_max = 30, 30
reg.population:insert('#', wp)
local pidx = #reg.population - 1
```

2. Add the matching `local_population` to the draw pool:

```lua
local lp = df.local_population:new()
lp.type = df.world_population_type.Animal
lp.race = wp.race
lp.quantity, lp.quantity_max = 30, 30
lp.population.region_x, lp.population.region_y = pos.x, pos.y
lp.population.feature_idx    = -1
lp.population.cave_id        = -1
lp.population.site_id        = dfhack.world.getCurrentSite().id
lp.population.population_idx = pidx
lp.population.layer_depth    = -1
df.global.world.populations.all:insert('#', lp)
```

Then `force Wildlife` and wait ≥ 100 ticks. **This is the cleanest test of whether the wave selector reads `world.populations.all` live or a cached per-site list built at embark.** If it reads the live vector, this is the whole mechanism for our tool and no unit-placement hackery is needed.

### E5 — Direct placement of an `AQUATIC` unit in 7/7 water

Test that `create-unit` can place a shark without instantly killing it. Use `-locationType Any` so `isValidSpawnLocation` (`create-unit.lua:387-405`) is bypassed — it has no water-aware mode.

```
modtools/create-unit -race SHARK_GREAT_WHITE -caste MALE -location [ X Y Z ] -locationType Any -duration 0
```

Then repair the population linkage that `wildUnit` gets wrong (`create-unit.lua:914-933`):

```lua
local u = df.unit.find(df.global.unit_next_id-1)
local r = u.animal.population
r.region_x, r.region_y = pos.x, pos.y
r.feature_idx = -1          -- NOT unk_28 (stale field name at create-unit.lua:925)
r.cave_id     = -1
r.site_id     = dfhack.world.getCurrentSite().id
r.population_idx = pidx     -- from E4; >= 0 is REQUIRED for Units::isWildlife (Units.cpp:596)
r.layer_depth = -1
u.animal.leave_countdown = 20000
u.flags2.roaming_wilderness_population_source = true
u.flags2.roaming_wilderness_population_source_not_a_map_feature = false  -- it IS a region pop
print(dfhack.units.isWildlife(u))   -- expect true, unlike stock create-unit
```

Measure: (a) survival past 1,000 ticks in water; (b) death on a dry floor tile (`AQUATIC` + `IMMOBILE_LAND` predicts yes); (c) when `leave_countdown` reaches 0, does it path to a water map edge or get stuck and feed `fix/wildlife`.

### E6 — Predator/prey in water

On the OCEAN fort, place one `SHARK_GREAT_WHITE` (`LARGE_PREDATOR`) and ten `FISH_CARP` / `FISH_BLUEFISH` (`BENIGN`) in the same connected body of water via E5. Watch combat reports and `unit.opponent.unit_id` / relationships. Tests `Faction.md:200` in the aquatic case. Repeat with `CROCODILE_CAVE` in a cavern lake, and with the shark flagged `flags4.agitated_wilderness_creature = true` to see whether agitation changes target selection from dwarves-only to anything.

### E7 — Fishing prohibition and vermin pools

On both forts dump `plotinfo.no_fishing_feature_x/_y/_idx/_layer` (`df.plotinfo.xml:1009-1012`) before and after heavy fishing, alongside `plotinfo.outdoor_irritation`. Cross-checks `Creature.md:68`'s claim that **fishing** raises agitation, and tells us whether vermin-fish depletion is tracked on the feature or the region.

### E8 — Verify the wave-refund accounting

Snapshot every `world.populations.all[i].quantity` (E1 script), let one natural wave arrive and leave, snapshot again. Confirms `refund_population`'s model (`fix/wildlife.lua:47-63`) and gives the exact ledger our tool must respect if we want to inject units without breaking vanilla waves.

---

## Open questions

1. **Does `plotinfo.map_edge.surface_x/y/z` contain submerged tiles?** Not resolvable from source; E2 settles it. Everything about "a shark arrives naturally on an ocean fort" depends on the answer.
2. **Is the wave draw pool read live from `world.populations.all`, or cached at embark?** `world.area_grasses.world_tiles` is explicitly commented "grasses in world tiles around embark. Populated at embark" (`df.world.xml:667-668`), which proves DF *does* build embark-time caches of this shape. If a wildlife equivalent exists, E4 fails and we would have to find and patch that cache instead. I found no such structure in df-structures, but absence of evidence is weak here.
3. **What are the "five lists" of `Creature_token.md:534`?** The token names were stripped by the markdown conversion. **[speculation]** likely `LARGE_PREDATOR`, `LARGE_ROAMING`, a small/vermin list, and two more. Whether aquatic species occupy their own list — which would explain a shark group and a wolf group coexisting — is unknown. Needs the original wiki page (out of scope: no web).
4. **Is `population_idx >= 0` sufficient for DF itself** (not merely for `Units::isWildlife`) to treat a unit as part of a wave — i.e. to block the next wave and to refund on leave? `fix/wildlife`'s existence proves DF has a "previous group still here" gate, but the exact predicate DF uses is in no local source.
5. **Where do `POOL_*` biomes come from at all?** They are absent from `Maps::getBiomeTypeWithRef` and there is no pool `feature_type` (`df.feature.xml:47-57`), yet `POOL_TEMPERATE_FRESHWATER` etc. exist as `biome_type` values and creatures use them (`SNAPPING TURTLE`, `POND_TURTLE`). Unresolved.
6. **Does `create-unit.lua:904/925`'s `unk_28` write throw or silently corrupt** against current structures? One-line test on the rig. If it throws, `--wild` is currently broken outright in 53.16-r1.1 — worth reporting upstream.
7. **`BEACH_FREQUENCY:10` on `ORCA` / `SPERM_WHALE`** (`creature_ocean_new.txt:572, 896`) is a second, independent way aquatic megafauna reach a coastal map — they beach and air-drown (`Creature_token.md:121`). Not investigated; could be an easier lever than wave injection for "a whale appeared on my beach".
8. **Fresh vs salt on the LAKE fort.** `Maps.cpp:1344-1350` branches on `region->salinity` (> 65 salt, < 33 fresh, else brackish). Our lake fort's salinity decides whether the pool holds `FISH_CARP` / `FISH_PIKE` (freshwater) or nothing useful. Check before committing to the embark.
