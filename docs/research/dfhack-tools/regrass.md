# regrass (DFHack 53.16-r2)

Sources read: `plugins/regrass.cpp` (524 lines), `plugins/lua/regrass.lua` (76 lines), `docs/plugins/regrass.rst`,
`test/plugins/regrass.lua`, and the struct XML (`df.matgloss.xml` plant_raw_flags, `df.d_basics.xml` biome_type
attributes). Web doc: https://docs.dfhack.org/en/stable/docs/tools/regrass.html. All paths are relative to
`/Users/nathanielcannon/Claude/GitRepos/dfhack-53.16-r2`.

## What it does

`regrass [<pos> [<pos>]] [options]` refills or creates surface grass and cavern moss. It is a C++ command with Lua
argument parsing. It has no hooks, no timers, no enable state and no exported Lua API.

### Targeting (`df_regrass`, `:433-524`)

- **No positions:** every block in `world->map.map_blocks` (`regrass_map`, `:417-423`).
- **One position:** that tile. With `-b`, the whole 16×16 block containing it.
- **Two positions:** the cuboid between them.
- **`-z`:** whole z-levels: between the two positions' z, at the first position's z, or at the viewport z.
  - `-b` and `-z` together are an error.
  - `-b` with two positions is an error.

### Options

Options are parsed in `regrass.lua:29-74`.

| Option | Effect in code |
|---|---|
| `-l/--list` | `forced_plant = -2`. Prints `index: id` for `world.raws.plants.grasses` and exits. |
| `-m/--max` | Sets **every** grass event on the tile to 100, ignoring biome (`:237-240`). |
| `-n/--new` | Allocates a `block_square_event_grassst` for each biome-compatible grass missing from the block (`:259-288`). |
| `-f/--force` | Clears `occupancy.no_grow` (`:252-253`) and, where nothing compatible exists, forces a grass. With no `-p`, the type is **one random grass for the whole run** (`regrass.lua:53-60`). |
| `-p/--plant <id>` | Chooses the forced grass by name (case- and accent-insensitive) or by index. **Without `-f` it is a hard error**: `qerror('Use of --plant without --force!')` (`regrass.lua:48-49`). The docs imply this but do not state it as an error. |
| `-a/--ashes` | Allows ASHES floors. |
| `-d/--buildings` | Allows tiles whose building occupancy is up to `Passable`. |
| `-u/--mud` | Allows rough stone, lava stone, mineral or feature stone **with a MUD material_spatter amount > 0**. |
| `-b/--block`, `-z/--zlevel` | Targeting, as above. |

The web docs and the r2 `.rst` have the same substance. Both warn that whole-map runs can freeze the game for minutes
with debug logging on. Per-tile reasons are logged with `debugfilter set Debug|Trace regrass log`.

## How it works: structures

**Grass is not a plant object.** It is a per-block `block_square_event_grassst` with a `plant_index` (the grass raw) and
`amount[16][16]` (0-100), stored in `map_block.block_events`. A tile counts as grassy when some grass event has
`amount > 0` and the tiletype is a GRASS_LIGHT/GRASS_DARK floor, ramp or stair.

### `valid_tile` (`:68-168`), checked in this order

1. If the tile material is already GRASS_LIGHT, GRASS_DARK or PLANT (a shrub or sapling standing on grass), the tile is
   valid.
2. A tree trunk tile is valid only at the tree's base z (`Maps::getPlantAtTile(p)->pos.z == p.z`).
3. **Liquid: invalid when `flow_size > 3` for water, or `> 0` for magma**. The comment reads
   "df::plant_raw::shrub_drown_level is usually 4" (`:97-101`).
4. The shape must be FLOOR, RAMP or a STAIR.
5. The building occupancy must be ≤ None, or ≤ Passable with `-d`.
6. `no_grow` makes the tile invalid unless `-f` is given.
7. SOIL is valid, except FURROWED (roads) and WET (beach) specials.
8. ASHES is valid with `-a`.
9. With `-u`, muddy rough stone is valid.

### `grasses_for_tile` (`:170-218`): which grasses are compatible

- **Subterranean tiles** (`designation.subterranean`): every grass raw with `BIOME_SUBTERRANEAN_WATER`.
- **Surface tiles**:
  - `Maps::getBlockTileBiomeRgn` gives the tile's own region, through `region_offset`.
  - `ENUM_ATTR(biome_type, plant_raw_flag, getBiomeType(x,y))` maps the region to its required biome flag.
  - The grass then has to pass the GOOD/EVIL/SAVAGE gates: `evilness < 33` is good, `> 65` is evil, and `savagery > 65`
    is savage.

### `regrass_events` (`:220-343`)

1. Refill the first event with a non-zero amount to 100 (or all events with `-m`).
2. Add new events (`-n`).
3. Otherwise pick a **random** compatible event and set it to 100.
4. If nothing is left and `-f` is given, reuse or allocate the forced grass event.

### `regrass_tile` (`:345-384`)

If the tiletype is not already grass, plant or tree, it is rewritten:

- **FLOOR** becomes `findRandomVariant(GrassLightFloor1 | GrassDarkFloor1)`, a coin flip.
- **RAMP and STAIR** become `findTileType(shape, GRASS_LIGHT|DARK, …)`.

`block->tiletype` is the only tiletype written. No block flags (designated, update) are set, and **no
`world.populations` Grass entry is touched**.

## Side effects, persistence, performance, gotchas

- **Persistence.** Tiletypes and grass events are saved map state, so the change is permanent.
- **Map-wide cost.** The default run visits every tile of every block (`world->map.map_blocks`) and, per tile, scans the
  block's events. That is O(tiles × events) in a single call.
- **Muddy stone loses its material.** `-u` turns muddy stone into a GRASS_LIGHT or GRASS_DARK floor, so the stone tiletype is
  gone.
- **Non-standard combinations.** `-m` sets every event on the tile to 100 with no biome check, so a tile can carry
  several grasses at once (not normal DF). `-f` with a random raw can place a cavern moss on the surface.
- **Unused return value.** If the Lua parser returns -1 (no grass raws loaded), the return value is ignored and the run
  fails later with "Plant raw not found for --force: -1".
- **No grass under water.** A tile with water depth 4 or more is always skipped. A beach WET soil tile is skipped even
  when dry.

## Relevance to our work

- **seasonal-wildlife (grazers).** Herbivore survival in test forts depends on grass amounts. On a long rig block where
  grazers deplete a CTRL or region9 pasture, `regrass -m` is a controlled reset of the forage variable.
  - It is a deliberate **intervention**, and it changes tiletypes. Record it in the manifest, and apply it to every arm
    equally or not at all.
  - It never touches `populations.all` Grass entries, so it does not affect our population ledger.
- **aquarium (seagrass).** This confirms that **DF grass cannot exist under water of depth 4 or more**. regrass refuses
  those tiles, consistent with `shrub_drown_level` being about 4. Making "real" seagrass on our river and sea beds
  (normally 7/7) with grass events is therefore not a vanilla-consistent option.
  - The grass event amount and tile conversion would also overwrite the bed's tiletype, which the aquarium reads for bed
    family and water-body evidence.
  - Our render-only seagrass sprite (`aquarium.cpp:512-519`) is the right design.
  - For shallow banks (depth 1-3) where DF grass *can* live, the aquarium should leave existing GRASS tiletypes alone
    rather than drawing a sprite over them.
- **Lesson.** `ENUM_ATTR(biome_type, plant_raw_flag, …)` is the vanilla mapping from region biome to plant flag. It
  includes `BIOME_LAKE_*`, `BIOME_RIVER_*` and `BIOME_OCEAN_*` plant flags (`df.matgloss.xml:154-183`). If we ever ship
  aquatic plant raws, this is the gate DF would use to make them native to sea, lake or river tiles.
