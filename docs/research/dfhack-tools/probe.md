# probe / bprobe / cprobe (DFHack 53.16-r2)

Sources read: `plugins/probe.cpp` (409 lines), `plugins/lua/probe.lua` (14 lines), `docs/plugins/probe.rst`,
`test/plugins/probe.lua`, and `docs/changelog.txt`. Web doc: https://docs.dfhack.org/en/stable/docs/tools/probe.html.
All paths are relative to `/Users/nathanielcannon/Claude/GitRepos/dfhack-53.16-r2`.

## What it does

The plugin registers three commands (`probe.cpp:398-408`). All three are read-only. The plugin has no `plugin_onupdate`,
no hooks, no state and no Lua API.

| Command | Options | Output |
|---|---|---|
| `probe [-c|--cursor x,y,z]` | `-c` parsed by `plugins.probe.parse_commandline` with `argparse.coords` (`probe.lua:5-12`) | Tile dump (below) |
| `bprobe` | none, and parameters are ignored | Selected building: id, name, type and subtype (with a custom workshop or furnace code), nest-box claim and item count, room count, "in construction" (`:313-396`) |
| `cprobe` | none | Selected unit: id, race, civ (decimal and hex), and **worn** items only, each with owned flag and armour flag (`:46-69`) |

Doc and code differences:

- The web docs and the r2 `.rst` agree.
- If `-c` gives an invalid coordinate, probe silently falls back to the keyboard cursor (`:118-123`).
- `cprobe` lists only `inv_item_role_type::Worn` items, not wielded or hauled ones.
- `bprobe` and `cprobe` act on the UI selection (`Gui::getSelectedBuilding/Unit`). Without a selection they return
  CR_FAILURE.
- r2 changelog: "`probe`: fix malformed output of local/global map feature names".

## What `probe` reads (probe.cpp:95-311)

It builds a `MapExtras::MapCache` (lazy, per block) and reads the target block's raw `map_block`:

- **Tiletypes.** It prints three tiletypes: current, `staticTiletypeAt` (the tile ignoring constructions) and
  `baseTiletypeAt` (the tile ignoring constructions and veins). Each is shown with the shape, material, special, variant
  and direction attributes (`describeTile`, `:71-93`).
- **Temperatures.** `temperature1/2`.
- **Biome.** `region_offset[des.biome]` → `world_data->region_map[bx][by]`. It prints the region id, savagery, evilness
  and a surroundings name (Serene … Terrifying) (`:154-177`).
  - It uses the tile's **own** `designation.biome` index, so it gives the region the tile actually draws from, not the
    embark centre.
- **Materials.** Geolayer index; layer, vein (with inclusion type), base and static materials.
- **Liquid.**
  - Liquid fields: `flow_size` with a magma/water label, `flow_forbid`, `water_salt` ("salty") and `water_stagnant`.
  - Designation flags: `pile`, `rained`, `smooth`, `dig`, `traffic`, `hidden`, `light`, `outside`, `subterranean`,
    `water_table`, `feature_local`/`feature_global` (with the feature index, type and origin address).
  - Block field: `fog_of_war`.
- **Occupancy.** `building` enum, `unit`, `unit_grounded`, `item`, `moss`, `dig_marked`/`dig_auto`, carve-track bits,
  `monster_lair` and `no_grow`.
- **Block events.** For each `block_square_event_grassst` with a non-zero amount on the tile, it prints one
  `amount of grass` line, **without the event's `plant_index`**, so you cannot tell which grass it is. For `world_construction` it prints the row bitmask.

What it does **not** print:

- the plant at the tile (no `getPlantAtTile`), vermin, items or units
- flow direction (`perm_flow_dir`) and the river path
- block flags (`map_block.flags`: designated, update_liquid, etc.)
- any world population data

## Side effects, performance, failure modes

- No writes. The MapCache is created and destroyed per call. Cost is microseconds.
- It needs a loaded map: "Map is not available!" otherwise (CR_FAILURE).
- With no `-c` and no keyboard cursor, it prints "No cursor; place cursor over tile to probe." A headless rig therefore
  **must pass `-c x,y,z`**.
- On an unallocated block (open sky above the map's blocks) it prints "No data." and returns CR_OK. A caller that only
  checks the return code will treat this as success.
- Output is human text through `color_ostream`. It is not structured, so a caller has to parse it.

## Relevance to our work

- **Reuse as an independent witness.** `dfhack.run_command_silent('probe', '-c', 'x,y,z')` returns the dump as a string
  in one RPC call. The rig harness can attach it to a FAIL report for any tile our code classified: placement refused,
  aquarium bed family, water body. This is the "receipt" pattern from the manifest-subject memory: a second, independent
  reader of the same tile.
  - Use it **one-shot only**. Never poll it on the user's game (memory: no polling the user game).
- **Water-body classification.** The aquarium classifies by tile evidence, not by region biome. probe prints the inputs
  we rely on: tiletype material (RIVER, POOL, SOIL…), `flow_size`, `water_salt`, `water_stagnant`, `subterranean`,
  `outside`, plus the **per-tile** biome region via `region_offset`. That last one matches our
  "DF draws from all 9 region_offset neighbours" finding. probe does not show river flow direction, so it cannot settle
  perm-flow questions.
- **Spawn and vermin questions.** probe gives the per-tile region id, savagery and evilness, and the `feature_local` index.
  Together these explain which `populations.all` entries (matched by `region_x`/`region_y` or `feature_idx`) can supply
  that tile.
- **cprobe** gives the unit id and race number quickly. For wildlife inspection, our own dump is richer: population
  back-ref, `leave_countdown`, flags2.
- **No conflicts.** It is read-only.
