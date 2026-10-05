# plant (DFHack 53.16-r2)

Sources read: `plugins/plant.cpp` (726 lines), `plugins/lua/plant.lua` (124 lines), `docs/plugins/plant.rst`,
`test/plugins/plant.lua`, the struct XML (`df.veg.xml` plant / veg_handlerst, `df.block.xml:417` column plants,
`df.matgloss.xml` plant_raw_flags), and `Maps::getPlantAtTile` (`library/modules/Maps.cpp:1219`). Web doc:
https://docs.dfhack.org/en/stable/docs/tools/plant.html. All paths are relative to
`/Users/nathanielcannon/Claude/GitRepos/dfhack-53.16-r2`.

## What it does

`plant <mode> …` lists, creates, ages or removes shrubs and saplings. Grass goes through `regrass`. It is a C++ command
with Lua argument parsing. It has no hooks, timers, enable state or Lua API.

| Mode | Syntax | Notes |
|---|---|---|
| `list` | `plant list` | Prints `world.raws.plants.bushes` (shrubs) and `.trees` (saplings) as `index: id` (`:537-548`). |
| `create` | `plant create <id> [pos] [-c] [-a age]` | One plant at `pos`, or at the keyboard cursor. `id` is a raw id (case- and accent-insensitive) or a numeric index into `plants.all` (`plant.lua:10-27`). Grass raws are refused (`:617-621`). |
| `grow` | `plant grow [pos [pos]] [-a] [-f\|-e ids] [-z] [-n]` | Default target is the whole map, default age 3 years. |
| `remove` | `plant remove [pos [pos]] [-s] [-p] [-d] [-f\|-e ids] [-z] [-n]` | With no `-s`/`-p`, removes only **invalid** plants (Bug 12868). |

### Options

Options are parsed in `plant.lua:70-87`.

| Option | Applies to | Effect |
|---|---|---|
| `-c/--force` | create only | Ignore and clear `no_grow`, and skip the WET/DRY check. Using it with any other mode is an error (`:549-553`). |
| `-a/--age <n\|tree\|1x1\|2x2\|3x3>` | create, grow | Years, capped at 1250. Stored as `40320*n - 1` (`plant.lua:54-68`). `grow_counter` is in **10-tick units**: 403,200 ticks/yr ÷ 10. With remove it is an error. |
| `-f/--filter`, `-e/--exclude` | grow, remove | Comma list of ids. Only one filter may be defined. For remove it requires `-s` or `-p`. |
| `-z/--zlevel` | grow, remove | Whole z-levels. |
| `-n/--dry-run` | grow, remove | Count only. With create it is an error. |
| `-s/--shrubs`, `-p/--saplings`, `-d/--dead` | remove | `-d` requires `-s` or `-p`. |
| **`-t/--trees`** | (remove) | **Undocumented.** It is parsed, but then fails with "--trees not implemented!" (`:571-575`). |

Doc and code differences:

- **`--dryrun` does not exist.** The web docs and the r2 `.rst` (`plant.rst:162`) list the remove option as `--dryrun`.
  The parser has only `dry-run`, so `plant remove --dryrun` fails as an unknown option. Use `-n` or `--dry-run`.
- `-t/--trees` is missing from the docs.
- Otherwise the web docs and the r2 `.rst` are identical.

## How `create` works (df_createplant, `:124-252`)

### Preconditions, checked in order

1. The block column must exist. The tile's **shape must be FLOOR**.
2. `occupancy.building == None`, and `no_grow` must be unset unless `-c` is given.
3. **Liquid:** it refuses `flow_size > 3` water or any magma ("Too much liquid!") (`:153-159`).
4. **Material** must be SOIL, GRASS_LIGHT, GRASS_DARK or ASHES. Rough STONE, LAVA_STONE or MINERAL is accepted only
   with a MUD spatter. Smooth or track stone is refused (`:161-188`).
   - RIVER, POOL, BROOK_BED and FROZEN_LIQUID beds all fall to the `default:` case: "Wrong tile material".
5. **WET/DRY:** `tile_watery` scans a 5×5 area **one z below** the tile, corners excluded, for POOL or RIVER material or
   BROOK_BED shape (`:96-122`).
   - A watery tile needs a raw with `WET`. A dry tile needs `DRY`, unless `-c` is given.
   - **There is no biome check.** Raw biome flags, GOOD/EVIL/SAVAGE and underground status are not consulted.

### What it allocates and writes

```cpp
auto plant = df::allocate<df::plant>();
plant->type = TREE ? (watery ? WET_TREE : DRY_TREE) : (watery ? WET_PLANT : DRY_PLANT);
plant->hitpoints = TREE ? 400000 : 100000;
plant->material = plant_idx;  plant->pos = pos;
plant->grow_counter = age<0 ? 0 : age;  plant->update_order = rand() % 10;
world->plants.all.push_back(plant);
col->plants.push_back(plant);        // col = getBlockColumn((x/48)*3, (y/48)*3): the top-left column of the 48x48 mid-level tile
world->plants.{tree_dry|tree_wet|shrub_dry|shrub_wet}.push_back(plant);
*tt = Sapling | Shrub;               // the tiletype is replaced outright
occ->bits.no_grow = false;
```

Things it leaves alone:

- `tree_info` stays null, which makes the plant a sapling or shrub.
- `site_id`, `srb_id`, `damage_flags` and `contaminants` keep their allocator defaults.
- No `world.populations` Tree or Bush entry is debited or created.
- No block flags are set.
- Existing grass events stay under the shrub, which matches vanilla.

## grow (`:296-357`)

- **Saplings.** Sets `grow_counter = age`, clears the `dead` damage flag, and turns a `SaplingDead` tiletype back into
  `Sapling`. The default age is `120*28*12*3 - 1`, one tick-unit short of 3 years: "let the game handle the actual
  growing-up" (`:75`). The sapling becomes a tree only on DF's next growth update, not immediately.
- **Trees.** `grow_counter` is raised only if the age is above 3 years.
- **Cuboid test.** `plant_in_cuboid` walks `tree_info` body and roots, so trees whose canopy alone falls in the cuboid
  count (`:254-294`).

## remove (`:425-523`)

- Walks `world.plants.all` backwards.
- Trees with `tree_info` are always skipped (TODO).
- For each target:
  - `uncat_plant` erases it from the type vector and the column vector.
  - `set_tt` rewrites the tile to a grass floor if any grass event has amount > 0, **else a SoilFloor**.
  - It is erased from `plants.all` and then `delete`d.

Gotchas:

- **Soil replaces stone.** A shrub that was created on muddy *stone* turns back into **soil** on removal: the material
  changes.
- **Dangling pointers.** There is no cleanup of jobs or references that may point at the deleted plant.

## Side effects, performance, failure modes

- **Persistence.** Everything is saved map state.
- **Cost.** `grow` and `remove` are O(plants) map-wide. `remove` uses `vector::erase` per plant, which is fine at normal
  counts.
- **Cursor required.** `create` without a position needs an active keyboard cursor. Otherwise: "Invalid pos for
  create!" A headless rig must pass coordinates.
- **Validation gaps.** `create` does not check whether a plant already occupies the tile. A FLOOR shape test excludes
  live shrub and sapling tiles, but not an orphan `plants.all` entry on a floor tile, which is the Bug 12868 case.

## Relevance to the aquarium (seaweed/seagrass on river and sea beds)

### What a real underwater plant would need, judged against this code

1. **A raw.** Vanilla has none. Our own `aquarium.cpp:2964` comment says "vanilla has no seaweed". The raw would need:
   - `WET`
   - the right `BIOME_OCEAN_*`, `BIOME_LAKE_*` or `BIOME_RIVER_*` flags (`df.matgloss.xml:154-183`) if DF itself is to
     seed it
   - a `shrub_drown_level` (`plant_raw.shrub_drown_level`, int8, `df.matgloss.xml:370`) above our bed depths (beds sit
     at 7/7). Otherwise DF would drown it. The drowning is inferred from the field name and the regrass comment "usually
     4"; it is not verified.
2. **A placement path that bypasses `plant create`.** `create` refuses `flow_size > 3` and RIVER/POOL bed materials, so
   it **cannot be used on any of our beds**. We would have to repeat its writes ourselves: allocate a `df::plant` as
   WET_PLANT, push it into `plants.all`, `shrub_wet` and the column vector at `(x/48)*3, (y/48)*3`, and set the tiletype
   to `Shrub`.
3. **Accept that the tiletype is lost.** `*tt = tiletype::Shrub` replaces the bed tile. On a river that erases the
   RIVER-material tile. Our water-body classification reads that tile ("tile evidence, not region biome"), and DF's own
   river behaviour depends on it too. The aquarium's `bed_family` would also stop seeing sand or mud there.

**Conclusion:** keep seaweed and seagrass **render-only**. That is the current design: a sprite in DF's plant slot
(`background_two`), hashed by world position, at `aquarium.cpp:512-519`. A real plant would cost real map state and
break our tile evidence, for visuals we already have.

### Conflict to guard against

- `classify` assigns `out.plant` on any bed whose shape is not EMPTY, RAMP_TOP or RAMP (`aquarium.cpp:497-519`).
- A real **Shrub or Sapling** tile on a sea or river bed would get our seaweed sprite in the same plant slot, hiding DF's
  real plant. Examples: a shallow-bank shrub at depth 3 or less, a user's `plant create -c` result, or a modded aquatic
  plant.
- **Fix (cheap):** skip the sprite when the bed tile's shape is SHRUB or SAPLING, or its material is PLANT or TREE. A
  heavier alternative is to skip when `Maps::getPlantAtTile` returns non-null.

### Reuse for seasonal-wildlife

- `dfhack.maps.getPlantAtTile(x,y,z)` (Lua API over `Maps.cpp:1219`) is the right test for "is this tile a plant or tree
  body".
- Our `groundTile` (seasonal-wildlife.lua:4372-4382) accepts only FLOOR and RAMP shapes, so it already excludes SHRUB and
  SAPLING tiles as well as TREE-material tiles. That is conservative: DF units walk over shrubs, so accepting the SHRUB
  shape would enlarge the placeable set in brushy biomes.
- The WET/DRY rule here (POOL, RIVER or BROOK_BED within the 5×5 area one z below) is DF's own "near water" test for
  vegetation. It is a ready-made, vanilla-consistent proximity test if we ever need a "riparian tile" notion for
  shoreline prey.
