# gui/biomes (DFHack 53.16-r2)

- Docs: https://docs.dfhack.org/en/stable/docs/tools/gui/biomes.html (read 5 Oct 2026)
- r2 doc: `scripts/docs/gui/biomes.rst`. It matches the web page: the summary, the DF bug 8781 sky-biome caveat with its two cases (a muddied cast-obsidian sky farm, and an evil inherited sky biome killing or zombifying fliers), and bare usage. No difference found.
- Source: `scripts/gui/biomes.lua` (371 lines, pure Lua, no plugin). Added at `scripts/changelog.txt:877`.
- Tags: fort, inspection, map.

## What it does and its options

The command is `gui/biomes`, with no arguments; the source never reads `...`. It opens a ZScreen (`focus_path='BiomeVisualizer'`, `pass_movement_keys=true`, `:312-316`). In graphics mode the screen draws a letter or texture on every map tile in the viewport, one letter per biome region. In ASCII mode the letters blink at 500 ms (`:326`).

The resizable legend window sits under the minimap (`:106-119`). For each region it lists `"<letter>: <Surroundings> <biome caption>"`. Hovering a list row or a map tile shows that region's details:

- type
- savagery and evilness
- elevation, rainfall, drainage, vegetation, temperature and volcanism
- the `lake` / `brook` flags

The details code is at `:240-274`. Selecting a row highlights its tiles in cyan. It refuses to run with no map loaded (`:362-364`). Running it again raises the existing window (`:371`).

## How it works (file:line)

- **The per-tile lookup** (`gatherBiomeInfo`, `:39-95`) takes one z-level at a time over every (x, y) of the map:
  - `dfhack.maps.getTileBiomeRgn(x,y,z)` returns a world region tile (`rgnX`, `rgnY`), or nil when there is no block (`LuaTools.cpp:207`, `PushPosXY` of an invalid coord).
  - The result is cached per region in `regionBiomeMap[rx][ry]`: `{ biomeTypeId = dfhack.maps.getBiomeType(rx,ry), biome = dfhack.maps.getRegionBiome(rx,ry) }`.
  - Each tile stores the 1-based index of its `region_map_entry` in `biomesMap[z][y][x]`.
  - **The list is keyed by region_map_entry identity, not by biome type** (`:79-87`). Two neighbouring region tiles of the same type become two letters.
- **The C++ underneath** (`library/modules/Maps.cpp`):
  - `getBlockTileBiomeRgn` (`:982-997`) reads `designation[x][y].bits.biome` (0-8), then `block->region_offset[that]` (0-8), then `getBiomeRgnPos(block->region_pos, off)`.
  - `getBiomeRgnPos` (`:969-979`) adds `biome_offsets[off]`, ordered NW, N, NE, W, here, E, SW, S, SE (`:963-967`; enum `BiomeOffset`, `Maps.h:120-131`), then clamps to the world.
  - `getRegionBiome` (`:459-470`) returns `&world_data->region_map[x][y]`, or NULL when out of range.
  - `getBiomeType` (`Maps.h:429`, which calls `getBiomeTypeWithRef`, `Maps.cpp:1300+`) reverse-engineers DF's biome classification. It derives tropicality from temperature and latitude, honouring `flip_latitude`. **It throws** (`CHECK_NULL_POINTER`) on an invalid region.
- **Naming** (`GetBiomeName`, `:121-136`, "based on probe.cpp"): savagery and evilness are each bucketed as <33, 33-65 and >65 into a 3×3 grid (Serene, Mirthful, Joyous Wilds / Calm, Wilderness, Untamed Wilds / Sinister, Haunted, Terrifying), followed by `df.biome_type.attrs[id].caption`.
- **Order:** z = 0 is gathered at script load (`:97-99`) so the deep biomes take the first letters. Other z-levels are gathered lazily the first time `window_z` lands on them (`:330-334`). Drawing uses `guidm.renderMapOverlay` over the whole viewport every frame (`:355`).
- **Textures:** three tilesets are loaded from `hack/data/art/` on every run (`:12-25`), with fallbacks to `X` and `a` when there is no texpos.

## Side effects, performance, gotchas

- **Read-only.** It changes no game state and persists nothing, and the caches live only for this run.
- **The first frame on each new z is slow.** A z-level costs one Lua call to `getTileBiomeRgn` per tile. On an 8×8 embark that is 147,456 calls, plus a linear `find` over `biomeList` per tile (`:82`). Expect a visible hitch on first view of each level. **Never run it on the user's game as a probe.** Our block-level `region_offset` decode is the cheap equivalent.
- **The cache never refreshes.** It is per-session per-z, which is fine because biomes do not change.
- **More than 26 regions breaks the labels.** `string.char('a' + #biomeList)` (`:84, :351`) produces `{`, `|` and so on after `z`, and `TILE_STARTING_SYMBOL + (N-1)` (`:347`) runs past the small-letters tileset. This is possible on a large multi-biome embark with the sky biomes of bug 8781.
- **Region coordinates are never shown.** The legend has no rx:ry, so you cannot match a letter to a `world.populations` entry without reading `regionBiomeMap` yourself.
- **The sky-biome caveat is real data, not a display glitch.** Different z-levels of one column can resolve to different region tiles (DF bug 8781). Our own v5.8.4 note says the same: on CTRL 2,160 of 16,704 blocks name 28:19, mixed within a column.

## Relevance to our work

- **It answers a different question from our census, and it would under-report wildlife sources.**
  - gui/biomes shows, for each **tile**, the region its own `designation.biome` index names. That determines the tile's weather, plants and savagery.
  - seasonal-wildlife (`getEmbarkRegions`, `seasonal-wildlife.lua:819-867`) collects, for each **block**, all nine `region_offset[0..8]` entries. That is the set DF draws wildlife from (df-region-draw-tiles: X1's cavies came from 50:62, a tile named only by `region_offset` entries other than the first tile's).
  - So **gui/biomes is a valid view of "what biome is this tile" and an invalid view of "which populations can arrive here".** Do not use its letters as the managed set.
- **Same decode, so our arithmetic is cross-checked.** Our `(off % 3) - 1, (off // 3) - 1` with a clamp (`seasonal-wildlife.lua:849-855`; `aquarium.cpp:3345-3351` `lake_biome`) equals `getBiomeRgnPos`'s table. `Maps.cpp:443-457` `addRegionBiomeOffset` uses a *different*, keypad-ordered 1-9 convention, flipped vertically. Its own comment warns it is "upside down compared to (fort) map block region offsets". **Never feed `region_offset` values to `addRegionBiomeOffset`.**
- **The (-1,-1) "Bug 13" shift** recorded in seasonal-wildlife (`:806-815`) is what this tool would display too. It comes from DF's per-block `region_offset` data, not from a DFHack decoding error, since both paths compute the same thing.
- **Reusable pieces:**
  - The savagery/evilness → surroundings naming (`:121-136`) suits the seasonal-wildlife GUI and report labels.
  - Its tooltip field list (`region_map_entry` savagery, evilness, rainfall, drainage, vegetation, temperature, volcanism, `flags.is_lake`/`is_brook`) is a ready schema for a per-region panel.
  - **Wrap `getBiomeType` in `pcall`** as we already do: it throws, and gui/biomes does not guard it.
- **Aquarium:** `lake_biome` uses the per-tile index, as gui/biomes does, which is right for "is this water a lake". The water-body memory is "tile evidence, not region biome". gui/biomes is a handy manual check when a body is misclassified: hover the tile and read `lake`/`brook`.
