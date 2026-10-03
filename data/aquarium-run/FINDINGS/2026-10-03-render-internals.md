# Aquarium render internals: desk research, 3 Oct 2026

Scope: DF 53.16 (Steam, graphics) + DFHack 53.16-r2. Sources only, no game access.
Inputs: the r2 source tree (`/Users/nathanielcannon/Claude/GitRepos/dfhack-53.16-r2`, abbreviated `R2/`), the DF install
(`$DF_DIR`, vanilla raws and images, `Dwarf Fortress.exe` strings), the Steam workshop content dir
(`.../steamapps/workshop/content/975370/`, 235 items), and the rig findings in `2026-10-02-transparency.md` (F1-F21).

Labels: **[V]** = verified in source, raws, images or exe bytes (with a citation). **[I]** = inferred, because DF's renderer is closed
source. **[R]** = has to be measured on the rig; the matching probe is in section 6.

---------------------------------------------------------------------------------------------------------------------

## 0. Summary

1. **Where the lower-level water sprite comes from.** DFHack names no per-token texpos table. DF keeps its map
   texpos tables in about 51,000 unnamed int32s inside `gps`: `texture_indices1..11` [V]. A tile page's texpos
   vector maps each tile through `idx = y*page_dim_x + x` [V]. F7 showed that two different texpos reach the
   screen: the main viewport uses the mod's re-bound UNDERWATER tiles and the lower viewports use the vanilla ones.
   So DF most likely resolves the two paths through different slots [I]. The fix with the lowest risk and no
   per-frame cost is to scan `gps.texture_indices*` once for the vanilla LIQUIDS texpos values, then overwrite those
   slots with the mod's texpos once per world load (probes P2 and P5). The fallback is to swap pointers in
   `enabler.textures.raws` and then flush the tile cache (`gps.do_clean_tile_cache`) [V fields]. That has
   ownership and double-free hazards (section 1.4).
2. **Layer order.** The layers composite in struct order [V], which the smooth-movement plugin's redraw groups
   confirm [V]: background, background_two, liquid, spatter, building_one, item, vehicle, vermin, creatures,
   building_two, projectile, high_flow, top_shadow, signpost, up-creatures, designation, interface. Water (the
   liquid flag) sits in the base group, so creatures always draw on top of their own water. Viewports draw
   lower_viewport[7] first, up to [0], then main. Each viewport's `screentexpos_interface` layer holds the shading
   for the levels beneath it (the z-fog) [V as the plugin's model of DF, I for DF itself]. A translucent tile written
   only at underwater creatures' cells into `screentexpos_top_shadow` or `screentexpos_designation` of the
   **main** viewport costs O(visible creatures). It covers the creature, including creatures one or more levels down,
   because main draws after every lower viewport.
3. **River motion.** Vanilla FLOWS art is non-directional and nearly invisible [V, image analysis]: every direction
   row is identical, there are only 8 distinct frames, and each frame is about 115 sparkle pixels at alpha 64 or
   less. RIVER_BED's 16 "frames" differ by about 0.3/255 per channel [V]. The Flowing Water mod (3419529410) changes
   **only the art**: same tokens, same 16-frame layout, a new `flowing1.png` with directional streaks [V]. So the
   claimed animation depends on DF already cycling frames 1..16 [I]. "No river animation" (F10) is therefore
   unproven at the texpos level: vanilla frames are too similar to show up in a pixel diff. Probe P7 samples the
   texpos per frame.
4. **No raws token exists for ocean waves or foam** [V]. The exe has only the 11 `FLOW_*` tokens, and the
   OceanWave and SeaFoam flow types (`df.flow.xml:15-16`) have no graphics token. Mist does have a token
   (`FLOW_WATER_MIST`, 4 frames) [V].
5. **Cheapest design** (section 5). Raws bake plus a one-time slot repoint cost nothing per frame and replace the
   per-frame "lift" (the current FPS killer). Fog is DF's own. Creature tint, wave crests and shoreline slopes cost
   O(creatures), O(wave flows) and O(ramp cells), and are re-planned only when the view moves. Flow animation costs
   nothing per frame if DF cycles FLOWS frames. If it does not, rotating the FLOWS slot values costs O(1) per
   animation step. Each piece has a probe in section 6.

---------------------------------------------------------------------------------------------------------------------

## 1. Q1: where DF gets the texpos for liquid, per path

### 1.1 What the structures show [V]

- `graphic_viewportst` (`R2/library/xml/df.g_src.graphics.xml:355-421`) holds per-cell *texpos* layers plus four
  *flag* layers: `screentexpos_floor_flag` (u64), `screentexpos_liquid_flag` (u32), `screentexpos_ramp_flag` (u64) and
  `screentexpos_shadow_flag` (u32). **Liquid is not stored as a texpos.** It is a flag word that the renderer
  turns into a texpos at draw time. The layout comes from DFHack's own decoder (`R2/scripts/devel/inspect-screen.lua:196-204`):

  | bits | field | F2's 0x3c decodes to |
  |---|---|---|
  | 0-1 | `center_animation` | 0 |
  | 2-4 | `center_level` (1-7, the UNDERWATER_n index) | 7 |
  | 5-8 | `center_type` | 1 (water) |
  | 9-12, 13-16, 17-20, 21-24 | n, s, w, e `edge_type` (UNDERWATER_EDGE_* overlays) | 0 |

- Because liquid is a flag, the texpos the renderer draws for UNDERWATER_n must come from a lookup table. The only
  candidates DFHack exposes are:
  - `gps.texture_indices1..11`: static int32 arrays of 136, 11346, 20192, 4508, 60, 128, 458, 8340, 101, 276 and
    6845 entries (`df.g_src.graphics.xml:815-838`). They are opaque padding for graphicst's unnamed `texpos_*`
    fields, interleaved with named vectors (`texpos_custom_symbol`, `texpos_boulder`, `texpos_item_*`,
    `texpos_site_map`, `texpos_map_drawn`).
  - `gps.black_background_texpos[1]` (`:814`).
  - The `graphical_interface` and `classic_interface` sets (`interface_setst`), which hold only UI art.
  - `init.font.*_texpos` (`df.g_src.init.xml:3-15`), fonts only.
- Token → tile: `df.global.texture` (`texture_handlerst`, global `df.game_v.xml:253`) has `page[]` of `tile_pagest`
  {token, filename, page_dim_x/y, `texpos[]`, `texpos_gs[]`, loaded} (`df.g_src.texture_handler.xml:20-37`).
  `Screen::findGraphicsTile` indexes `texpos[y*page_dim_x + x]` and returns the **first loaded page** with that token
  (`R2/library/modules/Screen.cpp:538-559`).
- Surfaces: `df.global.enabler.textures.raws` is a vector of `SDL_Surface*` indexed by texpos
  (`df.g_src.enabler.xml:23-28`). The SDL_Textures that are actually drawn are cached per
  (texpos, fg/bg colour, flag) in `renderer_2d_base.tile_cache` (`df.g_src.renderer_2d.xml:2-15`,
  `texture_fullid` at `df.g_src.enabler.xml:48-57`). `gps.do_clean_tile_cache` ("true by main, false by graphics",
  `df.g_src.graphics.xml:806`) is the flush handshake.

### 1.2 Why lower viewports draw the vanilla sprite

From F7: the mod re-binds UNDERWATER_1..7 to its own page, SW_AQ_LIQUIDS (raws in the mod's `graphics_sw_aquarium.txt`),
and the main viewport obeys. Lower viewports still draw the vanilla LIQUIDS (0,0) art, and a same-token
`TILE_PAGE:LIQUIDS` override changed nothing. This fits two facts:

- (a) DF fills **two** slot groups for liquid: a view-level one, which follows the last binding, and a
  lower-level one, which is filled from the page or the first binding.
- (b) Duplicate page tokens resolve first-wins. `findGraphicsTile` itself is first-wins [V], and DF's loader
  probably is too [I].

Either way, the vanilla texpos value must sit in some slot that the lower-level path reads [I]. **Probe P2** finds it.
List every `texture_indicesK[i]` whose value equals a vanilla LIQUIDS texpos, and every one that equals a
SW_AQ_LIQUIDS texpos. Expect runs of 7 (UNDERWATER_7..1) and 7 more for `_LABEL`. If the vanilla run and the mod run
sit at different offsets, the two-path explanation is confirmed. Then overwrite the vanilla run once with the
values you want. **P5** does this and can undo it.

### 1.3 Candidate fields, ranked

| # | Target | Fixes | Per-frame cost | Risk |
|---|---|---|---|---|
| 1 | `gps.texture_indicesK[i]` slots holding the vanilla UNDERWATER_n (and `_LABEL`) texpos | the lower-level water sprite | 0 (one write per world load) | Low. These are plain ints; restore on unload. DF may reprint only when something changes, so bump `gps.force_full_display_count`. |
| 2 | The slot(s) holding fill **2566** (the background under submerged FLOOR cells, shared with SoilWall per F2) | the bed under all water | 0 | Only works if the under-water fill has its **own** slot. If the same slot feeds walls, repointing it re-skins every soil wall. P2 lists all hits and P5 tests each one alone. |
| 3 | `gps.texture_indicesK[i]` slots for the FLOWS / RIVER / BROOK frames | river animation (section 3) | O(1) per animation step | Low |
| 4 | `enabler.textures.raws[vanilla_texpos]` pointer | any path that uses that texpos | 0 | **High**, see 1.4 |
| 5 | `texture.page[LIQUIDS].texpos[]` entries | nothing at run time, probably | 0 | DF copies texpos into its slots when graphics load [I], so later edits are dead. Use only to read values. |

The main viewport's liquid (UNDERWATER_n) reads the same kind of slot as row 1 but in the view-level group. The raws
re-bind already reaches it. F16/F17 verified the bake there.

### 1.4 Hazards of the surface-pointer route [V facts, I consequences]

The DFHack docs say "the game periodically deletes textures that are in the vector"
(`R2/docs/dev/Lua API.rst:3385-3387`). DFHack also frees its own surfaces by handle on reset, not by slot
(`R2/library/modules/Textures.cpp:303-309`).

- Aliasing slot A to slot B's surface means both get freed: a double free, and DF crashes.
- Exchanging a DF-owned surface with a DFHack-owned tile hits the same problem through DFHack's reset.
- Only **exchanging two DF-owned surfaces** (two raws-loaded pages) is ownership-safe. Even that gives the main
  viewport's slot the other art.
- Mod tile pages are per-world, so their texpos can change on every world load. Redo the swap on every world load,
  and undo it on `SC_WORLD_UNLOADED`.

Use row 1 (the slot repoint). Keep row 4 as a last resort.

---------------------------------------------------------------------------------------------------------------------

## 2. Q2: layer order, drawing over creatures, glass floors and fog

### 2.1 Composite order inside one viewport

The order follows the struct (`df.g_src.graphics.xml:366-390`) [V]. The smooth-movement plugin's suppression
groups match it: base, then item, then vehicle, then vermin + creatures ("main"), then upper, then designation,
then interface (`R2/plugins/smooth-movement/smooth-movement.cpp:288-312, 394-418`;
`visual_animation.h:23-36`) [V].

| # | layer | notes |
|---|---|---|
| 1 | `screentexpos_background` | Floor or ramp sprite, or fill 2566 under submerged floors (F2). **0 means transparent: DF shows the next lower viewport.** |
| 2 | `screentexpos_floor_flag` | Edging bits (s/w/e/n edging, special_texture) |
| 3 | `screentexpos_background_two` | Boulders and plants. Also river art (F20, 34190/34196) and ramp/shore art (34850..34854) on cells over water one level down. |
| 4 | `screentexpos_liquid_flag` | **Water draws here, under everything that follows.** |
| 5 | `screentexpos_spatter_flag`, `screentexpos_spatter` | |
| 6 | `screentexpos_ramp_flag` | Ramp type, walls, open_air, arrows |
| 7 | `screentexpos_shadow_flag` | |
| 8 | `screentexpos_building_one` | |
| 9 | `screentexpos_item` | |
| 10 | `screentexpos_vehicle` | |
| 11 | `screentexpos_vermin` | |
| 12 | `screentexpos_left_creature`, `screentexpos` (centre), `screentexpos_right_creature` | |
| 13 | `screentexpos_building_two` | **Everything from here down draws above creatures.** |
| 14 | `screentexpos_projectile` | |
| 15 | `screentexpos_high_flow` | DF's flows: mist, smoke [I by name] |
| 16 | `screentexpos_top_shadow` | |
| 17 | `screentexpos_signpost` | |
| 18 | `screentexpos_upleft_creature`, `screentexpos_up_creature`, `screentexpos_upright_creature` | Tops of tall sprites |
| 19 | `screentexpos_designation` | |
| 20 | `screentexpos_interface` | Cursor; DFHack's map `paintTile` writes here by default (`Screen.cpp:119-122`). **In viewports with levels beneath, this is the z-fog** (2.3). |

### 2.2 Making creatures look inside the water (O(creatures))

- **At the view level:** the water (layer 4) is always under the creature (layer 12), so DF never draws a creature
  inside water. Writing a translucent "water veil" tile into layer 16 `screentexpos_top_shadow` (or 19
  `screentexpos_designation`) of the **main** viewport, at the creature's cell only, covers the creature's body.
  - Layer 16 does not cover the tops of tall sprites (layer 18). Use 19 for those, or also write the cell above.
  - Write only where the layer is 0, so DF's own shadows and designations survive.
- **For creatures on lower levels seen from above:** F7 showed that writes into `lower_viewport[k]` never reach the
  screen. Main draws after all lower viewports [V, 2.3], though. So the same veil written into the main cell at
  (x,y) covers the creature at z-1, z-2 and so on, under DF's fog. Write it into `screentexpos_top_shadow`, or into
  `screentexpos_interface` only if you append to the fog (the interface layer holds the fog there).
- **Cost:** for each visible underwater creature, read 3-4 values and write 1-2. Keep a candidate list of units in
  view and in water, refreshed every ~50 ticks, so the per-frame work stays O(U). It never walks the cells.
  - This is the same technique as transparent glass floors, applied the other way round: glass is a translucent
    tile drawn in a layer *above* the lower content.

### 2.3 Glass floors, MULTILEVEL_AIR fog and the "shows a lower level" signal

- **Draw order across viewports:** lower_viewport[7] → … → [0] → main. This is the smooth-movement plugin's model
  ("matching DF's lower-to-main draw order", `smooth-movement.cpp:767`). It builds its list in that order (`:703-712`)
  and the composite looks right on the rig's DF [V for the plugin, I for DF].
  - "The interface layer is the shading for levels below the camera" (`:321`).
  - "A viewport shades everything drawn beneath it, so this covers every staged tile. … would not deepen with
    distance" (`:772-774`).
  - So each viewport that sits over deeper content puts the fog tile in its own `screentexpos_interface`, and the
    fog **accumulates once per level**. That is DF's per-level z-fog.
- **The fog tile is MULTILEVEL_AIR** [V]. It is `[TILE_GRAPHICS:MULTILEVEL_OVERLAY:3:3:MULTILEVEL_AIR]`
  (vanilla `graphics_tiles.txt:719`), a uniform RGBA (89,146,172, alpha 96) tile in `multilevel_overlay.png` (my
  pixel check). Ramp-shaped variants are `MULTILEVEL_RAMP_WITH_WALL_*` / `MULTILEVEL_RAMP_OTHER` (`:720-766`).
  - The White Z Fog (2899098612) and Black Shadows and ZFog (2899669539) mods re-bind exactly these tokens to their
    own pages (their `graphics_tiles_*_zfog.txt`) [V].
  - Grey Z-fog 2899337501 is **not installed** in this workshop dir. White and Black are.
- **Glass floors:** vanilla `glass_floor.png` is already translucent (alpha 144-255, my check), bound by
  `[TILE_GRAPHICS:FLOOR_GLASS:1:0:GLASS_CLEAR_FLOOR]` (`graphics_tiles.txt:53-55`). The Transparent Glass Floors mod
  (2978122014) only swaps in lower-alpha art for the same three tokens (`graphics_transparent_floors.txt`) [V].
  - So DF draws the lower viewport under a glass-floor cell and composites the glass sprite in main
    `screentexpos_background` over it [I].
  - DF's "see-through" test therefore covers glass floors as well as open space, ramp tops and EMPTY-shape water
    (F2: deep EMPTY lake cells already show lower levels through fog).
- **A per-cell "shows lower level" flag:** `graphic_viewportst` has **no explicit depth field** [V].
  - The effective signal is `background == 0`. DFHack's own `Gui::getDepthAt` walks `gps.viewport[depth]` and
    returns the first depth whose `screentexpos_background[i] ~= 0` (`R2/library/modules/Gui.cpp:3026-3038`) [V].
    This is also why the "lift" works: writing a bed into main background makes depth 0.
  - Upstream, the print parameter block `df.global.world.viewport` (type `map_viewport`, original name
    `print_map_rectangle_paramst`, `df.world.xml:713`) carries `under_limit_start`, `under_limit[]`,
    `under_limit_dx` and `under_limit_dy` (`df.graphics_mainview.xml:13-16`) [V fields]. These are probably the
    per-column limit for how far down to draw [I, semantics unverified; P3 prints them].
  - `d_init.display.number_of_lower_elevations_shown` (`df.d_init.xml:67`) caps the depth, which tops out at 8
    lower viewports (`df.g_src.graphics.xml:728`).

---------------------------------------------------------------------------------------------------------------------

## 3. Q3: river motion

- **Tokens** [V, vanilla `graphics_fluids.txt`]:
  - Format: `[TILE_GRAPHICS:<page>:<x>:<y>:<TOKEN>:<set>:<frame>]`.
  - RIVER_TO_* and BROOK_TO_* (8 directions each) map to the **same cells** of FLOWS / FLOWS2 / FLOWS3 / FLOWS4
    (sets 1-4) × frames 1-16. Row y = NW, NE, SE, SW, N, S, W, E.
  - RIVER_BED_* (16 frames, set 1, page RIVER) and BROOK_BED_* (sets 1-4, pages BROOK..BROOK4) are the river and
    brook body art.
  - The exe holds exactly these strings as a token table (byte offset ≈24.636 M: `RIVER_TO_NW` …
    `BROOK_BED_SW`) [V].
- **Vanilla art** [V, my pixel analysis of `$DF_DIR/data/vanilla/vanilla_environment/graphics/images`]:
  - `flows.png`: all 8 direction rows are byte-identical, and flows2..4 are byte-identical to flows. Each row has 8
    distinct frames (period 8), each about 115 pixels of pale cyan (160,208,213) at alpha 64 or less. These are
    non-directional sparkles.
  - `river.png`: fully opaque (alpha 255). RIVER_BED row 0 has 9 distinct frames out of 16, and frames 0 and 1
    differ by a total |Δ| of 1130 over 4096 channel values (about 0.3 per channel).
  - So vanilla motion, if DF cycles at all, is close to invisible. **F10's pixel-diff result ("0 map pixels
    changed") cannot tell "not animated" from "animated with near-identical frames".** Measure the texpos per
    frame instead (P7).
- **Which cells and layers** [I + F20]:
  - River art appears in `screentexpos_background_two` of the **open cell over the river** (F20: 34190/34196 on
    cells over water one level down). That is the river seen from above.
  - At the river's own z the cell is the liquid flag (0x3c), with `center_animation` = 0.
  - FLOWS frames are probably drawn in the same over-river cell (bg2 or `high_flow`) or chosen through the liquid
    flag's 2-bit `center_animation` [I].
  - Candidate clocks are `map_renderer.cur_tick_count` (GetTickCount) and `map_renderer.tick_phase`
    (cur_year_tick % 10080) (`df.graphics_mainview.xml:43-44`).
  - P7 samples bg2, high_flow and liquid_flag per frame at a river cell, at z and at z+1. P8 makes a histogram of
    `center_animation` over the screen. P9 forces `center_animation` to 1..3 to see whether flow frames appear.
- **What Flowing Water (3419529410, installed) changes** [V]:
  - It adds 4 tile pages, FLOWINGWATER..FLOWINGWATER4, all pointing at **one** image (`flowing1.png`, 512×256)
    (`tile_page_flowing_water.txt`).
  - It re-binds BROOK_TO_* / RIVER_TO_* sets 1-4 × frames 1-16 to them (`graphics_flowing_fluids.txt`, 1040 lines).
    The token set is unchanged.
  - The art has 16 distinct frames per row, alpha about 11-19. The frame-to-frame best match is a displacement of
    8 px or more, roughly along the row's direction: W → −x, E → +x, S → +y, N → −y, diagonals mostly matching.
    Those are the streaks moving downstream.
  - Since it ships nothing but art, its "animates water" claim only holds if DF cycles frames 1..16 itself [I].
  - The aquarium mod already does the same re-bind with `sw_aq_flows1..4.png`.
- **What a mod needs:**
  - Per direction row, 16 frames whose streak pattern is rolled (wrap-around) by about 2-4 px × frame along the
    direction, so the loop is seamless.
  - The same art on all four sets, both RIVER_TO and BROOK_TO, and alpha low enough not to hide the bed.
  - That is all raws can do. If P7 shows DF holds the frame fixed, two script fallbacks remain:
    - (i) Rotate the FLOWS slot values that P2 finds. Per animation step, write 16 frames × 8 dirs × 4 sets = 512
      int32s at most, or 32 if DF reads only frame 1. That is O(1) in cells, and no cache flush is needed because
      only texpos numbers change.
    - (ii) Write the frame texpos into a layer per river cell: O(visible river cells) per frame, using a plan that is
      rebuilt only when the view moves.

---------------------------------------------------------------------------------------------------------------------

## 4. Q4: ramps and slopes under water

- **What DF knows per cell** [V]: `screentexpos_ramp_flag` (u64) = `type` (8 bits), `wall_n/w/e/s/nw/ne/sw/se`,
  `n/s/w/e_is_dark_corner`, `n/s/w/e_is_open_air`, `show_up_arrow`, `show_down_arrow` and `color_index`
  (`inspect-screen.lua:215-236`).
- **Ramp art** [V tokens, I placement]:
  - The ramp body is the material's `*_RAMP_WITH_WALL_*` tile, drawn in `screentexpos_background`.
  - `RAMP_OVERLAY` tiles (`graphics_tiles.txt:179-225`) give shading and walls, keyed by the ramp flag.
  - Seen from above (the ramp top at z+1), DF uses the ramp-shaped fog `MULTILEVEL_RAMP_*` in the interface layer.
  - F20's bg2 34850..34854 on ramp tops over water are probably RAMP_OVERLAY or MULTILEVEL_RAMP tiles; P1's reverse
    lookup will tell.
- **Why slopes vanish under water:** the liquid draws at layer 4, over the background. The baked UNDERWATER tile is
  opaque (F16), and DF may also put fill 2566 instead of the ramp in background for submerged ramps [R: P3 on a
  submerged ramp cell].
- **Keeping slopes visible at the lowest cost:** submerged ramp cells are a thin shoreline set (R cells).
  - Plan them when the view moves. Write the ramp sprite (the vanilla `*_RAMP_*` texpos for the tile's material and
    shape) into `background`, set `liquid_flag = 0`, and put an **unbaked** translucent water tile into
    `background_two`, which draws after background and before creatures.
  - This costs O(R) per frame, or O(R) only on change if P4 shows DF does not rewrite unchanged cells.
  - Keep the ramp flag so DF still draws the overlay shading.
  - For the view from above, the same R cells' tops already get DF's MULTILEVEL_RAMP fog. Leave bg2 cleared as in
    F20.

---------------------------------------------------------------------------------------------------------------------

## 5. Q5: cheapest architecture

Cost basis: about 0.32 µs per Lua userdata access on the rig (F12). A typical view is 60×34 = 2,040 cells; wide zoom
reaches 6,000 or more (F12: 6,000 lifted cells = 8.4 ms). Today's per-frame O(all visible cells) loops (lift, bed
painter, background_two clear, crest/shimmer) are what take 250 FPS down to 16-24.

| Piece | Mechanism | Per-frame cost | One-time / event cost | Depends on |
|---|---|---|---|---|
| (a) Surface plus sand bed, view level | Raws bake (exists, F16-17) | 0 | – | done |
| (a) Same, seen from above | **Repoint the lower-path UNDERWATER slots** to the mod texpos (P2, P5) | 0 | Scan of about 51k int32 ≈ 16-30 ms per world load | P2 finds a distinct vanilla run |
| (a) Mud for rivers | Option 1: accept sand (0). Option 2: keep the river override but limited to visible river cells with a view-move plan | 0 / ≈0.1-0.3 ms (300-800 cells × 1 write) | plan on view move | user taste |
| (a) Visible slopes | Shoreline plan of R submerged ramp cells (section 4) | ≈0.02-0.25 ms (R = 20-200 × ≈4 accesses), or 0 between view moves if P4 shows persistence | plan on view move | P3 on a ramp, P4 |
| (b) Lower levels through water, per-level fog | DF native: lower viewports plus `screentexpos_interface` MULTILEVEL_AIR per level | 0 | – | the lower-path water must be translucent; see the trade-off below |
| (c) Creature tint | Veil tile into main `screentexpos_top_shadow` (or `designation`) at underwater units' cells, view z and up to 8 levels below | O(U): about 4 accesses × U, so 100 units ≈ 0.13 ms | refresh the candidate list every ≈50 ticks: O(all active units) amortized | – |
| (d) Mist | Option 1: DF's own `Mist` flows via `dfhack.maps.spawnFlow` at the dry ocean edge, which DF draws and animates (FLOW_WATER_MIST, 4 frames). Option 2: tiles in `high_flow` at the edge cells | 0 / O(edge) | O(spawns) on a timer | Option 1 changes gameplay: waterfall mist affects moods [I] |
| (d) Waves | No token exists (section 0, item 4). Read `block.flows` of visible blocks for OceanWave/SeaFoam **on tick change only**, cache (cell index, crest texpos), write per frame | O(F), with F the wave flows in view (≈100-300) ≈ 0.03-0.1 ms | O(visible blocks) per tick | F11: waves live on the open level above the sea |
| (e) Flow animation | Raws re-bind (exists). If DF does not cycle frames, rotate the FLOWS slot values | 0, or ≤512 writes per animation step (≈0.16 ms, not per cell) | – | P7, P2 |
| Bonus: standing-water shimmer | Rotate the UNDERWATER_7 slot among 2-4 baked caustic variants | about 1-7 writes per step | – | P2 |

**Design trade-off for (b):**

- **Bake everywhere (current).** If the lower-path slots point at the baked tile, every water level in a column draws
  as sand-and-water. From above you see z-1's "sand", not the true bottom, so depth comes only from DF's fog.
- **True depth.** The lower path points at an **unbaked** translucent tile, the main path stays baked, and the
  bottom fill 2566 is repointed to sand.
  - Only possible if P2 finds separate slots for (i) the lower-path liquid and (ii) the under-water fill, separate
    from SoilWall's fill.
  - Then columns stack translucent water plus fog down to a sand bottom, still at zero per-frame cost.
  - If 2566 is shared with walls, the bottom stays dark fill. You would then need per-cell bed writes on FLOOR-shape
    water cells in the main view only, at O(bed cells).

**Native fallback:** a small C++ plugin can do the per-cell layer work, including in **lower** viewports. It would
hook `renderer_2d_base::update_all` and re-composite cells with `renderer->update_viewport_tile(vp,x,y)` under scoped
value swaps, exactly as smooth-movement does (`smooth-movement.cpp:288-312, 846-850, 940-944`). C++ access is
roughly 10-30× cheaper per cell than Lua. The cost is a Windows build of an r2 plugin. Keep it in reserve in case
the slot routes fail.

---------------------------------------------------------------------------------------------------------------------

## 6. Rig probes

All probes are read-only unless stated. Each is pcall-wrapped and prints its results. Run them with the map visible
(`lua -f probe.lua`, or paste into `:lua`). Coordinates come from the mouse cell; the index formula follows
`inspect-screen.lua:282-283`. Run P1 first: P3 and P7 reuse its reverse table `_G.AQP.rev`.

### P1: texpos inventory and reverse lookup (≈30-100 ms, once)

```lua
local ok, err = pcall(function()
  local T = df.global.texture
  _G.AQP = _G.AQP or {}
  local rev, n = {}, 0
  for pi, p in ipairs(T.page) do
    if p.loaded then
      local w = p.page_dim_x
      for i, tp in ipairs(p.texpos) do
        if rev[tp] == nil then rev[tp] = ('%s[%d](%d,%d)'):format(p.token, pi, i % w, i // w) end
        n = n + 1
      end
    end
  end
  _G.AQP.rev = rev
  print('pages', #T.page, 'texpos entries', n, 'raws', #df.global.enabler.textures.raws,
        'init_texture_size', df.global.enabler.textures.init_texture_size)
  for pi, p in ipairs(T.page) do
    local t = p.token
    if t == 'LIQUIDS' or t:find('AQ') or t == 'MULTILEVEL_OVERLAY' or t == 'FLOOR_GLASS'
       or t:find('^FLOWS') or t:find('^FLOWINGWATER') or t == 'RIVER' or t == 'EVENT_FLOWS' or t == 'RAMP_OVERLAY' then
      print(('page[%d] %-18s loaded=%s dim=%dx%d n=%d first=%s file=%s'):format(pi, t, tostring(p.loaded),
        p.page_dim_x, p.page_dim_y, #p.texpos, (#p.texpos > 0) and tostring(p.texpos[0]) or '-', tostring(p.filename)))
    end
  end
  for _, v in ipairs{2566, 15561, 15577, 15657, 34190, 34196, 34850, 34851, 34852, 34853, 34854} do
    print('texpos', v, '=', rev[v] or '(on no page: DF-internal or DFHack tile)')
  end
end)
if not ok then print('P1 FAIL: ' .. tostring(err)) end
```

Look for: **two** pages with token `LIQUIDS` (vanilla plus the failed override), the SW_AQ_LIQUIDS texpos, and
which pages 2566, 34190 and 34850 come from.

### P2: slot scan of gps.texture_indices* (≈16-30 ms, once)

```lua
local ok, err = pcall(function()
  local g, T = df.global.gps, df.global.texture
  local want = {}
  local toks = {LIQUIDS=1, SW_AQ_LIQUIDS=1, FLOWS=1, FLOWS2=1, FLOWS3=1, FLOWS4=1, SW_AQ_FLOWS1=1,
                RIVER=1, BROOK=1, MULTILEVEL_OVERLAY=1, EVENT_FLOWS=1, FLOOR_SAND=1}
  for pi, p in ipairs(T.page) do
    if p.loaded and toks[p.token] then
      local w = p.page_dim_x
      for i, tp in ipairs(p.texpos) do want[tp] = ('%s[%d](%d,%d)'):format(p.token, pi, i % w, i // w) end
    end
  end
  want[2566] = want[2566] or 'FILL_2566'
  local sizes = {136, 11346, 20192, 4508, 60, 128, 458, 8340, 101, 276, 6845}
  local hits, t0 = 0, os.clock()
  for k, n in ipairs(sizes) do
    local arr = g['texture_indices' .. k]
    for i = 0, n - 1 do
      local v = arr[i]
      if want[v] then
        hits = hits + 1
        if hits <= 500 then print(('texture_indices%d[%d] = %d  %s'):format(k, i, v, want[v])) end
      end
    end
  end
  print(('hits=%d scan=%.1f ms black_background_texpos=%d'):format(hits, (os.clock() - t0) * 1000,
        g.black_background_texpos[0]))
end)
if not ok then print('P2 FAIL: ' .. tostring(err)) end
```

Read the result:

- Two runs of 7 consecutive UNDERWATER values, one vanilla and one SW_AQ, means two paths, and P5 targets the
  vanilla run.
- Count the FILL_2566 hits. One hit means it is shared with walls. Several hits mean P5 can test each one.
- FLOWS runs of 16 mean the slot rotation in section 3 is possible.
- If nothing matches, DF keeps these tables elsewhere. Fall back to P6 (surface swap), or the C++ plugin.

### P3: full cell dump at the mouse, main plus 8 lower viewports

```lua
local ok, err = pcall(function()
  local g = df.global.gps
  local pos = dfhack.gui.getMousePos()
  if not pos then print('P3: no map cell under mouse') return end
  local mv = g.main_viewport
  local x, y = pos.x - df.global.window_x, pos.y - df.global.window_y
  local idx = x * mv.dim_y + y
  local rev = (_G.AQP or {}).rev or {}
  local L = {'screentexpos_background', 'screentexpos_background_two', 'screentexpos_building_one',
             'screentexpos_item', 'screentexpos', 'screentexpos_building_two', 'screentexpos_high_flow',
             'screentexpos_top_shadow', 'screentexpos_signpost', 'screentexpos_up_creature',
             'screentexpos_designation', 'screentexpos_interface'}
  local function liq(v) return ('anim=%d lvl=%d type=%d edge n%d s%d w%d e%d'):format(v & 3, (v >> 2) & 7,
    (v >> 5) & 15, (v >> 9) & 15, (v >> 13) & 15, (v >> 17) & 15, (v >> 21) & 15) end
  local function get(vp, f) local o, v = pcall(function() return vp[f][idx] end) return o and v or nil end
  local function dump(tag, vp)
    if not vp then print(tag, 'nil') return end
    if not vp.flag.active then print(tag, 'inactive') return end
    local out = {}
    for _, f in ipairs(L) do
      local v = get(vp, f)
      local nm = (f == 'screentexpos') and 'creature' or (f:gsub('screentexpos_', ''))
      if v and v ~= 0 then out[#out + 1] = ('%s=%d%s'):format(nm, v,
        rev[v] and ('<' .. rev[v] .. '>') or '') end
    end
    local lf, rf, ff = get(vp, 'screentexpos_liquid_flag'), get(vp, 'screentexpos_ramp_flag'),
                       get(vp, 'screentexpos_floor_flag')
    if lf and lf ~= 0 then out[#out + 1] = 'liq[' .. liq(lf) .. ']' end
    if rf and rf ~= 0 then out[#out + 1] = ('ramp=0x%x type=%d'):format(rf, rf & 255) end
    if ff and ff ~= 0 then out[#out + 1] = ('floorflag=0x%x'):format(ff) end
    print(tag, #out > 0 and table.concat(out, ' ') or '(all zero)')
  end
  print(('cell map=(%d,%d,%d) vp=(%d,%d) idx=%d dims=%dx%d'):format(pos.x, pos.y, pos.z, x, y, idx, mv.dim_x, mv.dim_y))
  dump('main  ', mv)
  for k = 0, 7 do dump('lower' .. k, g.lower_viewport[k]) end
  local wv = df.global.world.viewport
  print('world.viewport under_limit start/dx/dy', wv.under_limit_start, wv.under_limit_dx, wv.under_limit_dy)
  if x >= 0 and y >= 0 and x < wv.under_limit_dx and y < wv.under_limit_dy then
    local o, v = pcall(function() return wv.under_limit[x * wv.under_limit_dy + y] end)
    print('under_limit[cell] (layout guessed x*dy+y)', o and v or 'unreadable')
  end
  print('z_levels_to_show', df.global.d_init.display.number_of_lower_elevations_shown)
end)
if not ok then print('P3 FAIL: ' .. tostring(err)) end
```

Run P3 on six kinds of cell:

1. Sea from the land level (z112): which lower viewport holds the liquid, and its `interface`, which should be
   MULTILEVEL_AIR.
2. Open air over the river (F20 squares).
3. A submerged ramp.
4. A glass floor, if one exists.
5. A swimming fish at the view level.
6. A fish one level down.

### P4: does DF rewrite unchanged viewport cells every frame? (writes one cell once)

```lua
local ok, err = pcall(function()
  local mv = df.global.gps.main_viewport
  local pos = dfhack.gui.getMousePos(); if not pos then print('P4: no cell') return end
  local idx = (pos.x - df.global.window_x) * mv.dim_y + (pos.y - df.global.window_y)
  local marker = dfhack.screen.findGraphicsTile('FLOOR_SAND', 0, 0)
  local orig = mv.screentexpos_background[idx]
  mv.screentexpos_background[idx] = marker
  local seen, n = {}, 0
  local function step()
    n = n + 1
    local v = mv.screentexpos_background[idx]
    seen[#seen + 1] = (v == marker) and 'M' or tostring(v)
    if n < 60 then dfhack.timeout(1, 'frames', step)
    else print('P4 orig', orig, 'marker', marker, 'per-frame:', table.concat(seen, ' ')) end
  end
  dfhack.timeout(1, 'frames', step)
end)
if not ok then print('P4 FAIL: ' .. tostring(err)) end
```

Run it paused and unpaused. If the value stays all `M` until the view moves, every per-cell piece in section 5
becomes O(changed cells).

### P5: repoint one slot, and undo it (WRITE)

```lua
-- Edit ARR/IDX from P2's output. NEW defaults to the mod's UNDERWATER_7. Set RESTORE=true to undo.
local ARR, IDX, NEW, RESTORE = 'texture_indices3', 0, nil, false
local ok, err = pcall(function()
  local g = df.global.gps
  _G.AQ_SLOT = _G.AQ_SLOT or {}
  local key = ARR .. ':' .. IDX
  if RESTORE then
    local old = _G.AQ_SLOT[key]
    if old then g[ARR][IDX] = old; _G.AQ_SLOT[key] = nil; print('P5 restored', key, old) else print('P5 nothing saved', key) end
  else
    NEW = NEW or dfhack.screen.findGraphicsTile('SW_AQ_LIQUIDS', 0, 0)
    if _G.AQ_SLOT[key] == nil then _G.AQ_SLOT[key] = g[ARR][IDX] end
    g[ARR][IDX] = NEW
    print('P5 set', key, 'from', _G.AQ_SLOT[key], 'to', NEW)
  end
  if g.force_full_display_count < 2 then g.force_full_display_count = 2 end
end)
if not ok then print('P5 FAIL: ' .. tostring(err)) end
```

Pass: from z112 the sea draws with the mod tile, and the main viewport and walls are unchanged. Restore before
saving or quitting until this is proven.

### P6: surface-pointer exchange (WRITE, last resort; read section 1.4 first)

```lua
-- Exchanges raws[A] <-> raws[B]. Both must be DF-loaded raws tiles; never a DFHack loadTileset/createTile handle.
-- Run again to swap back. Swap back before unloading the world.
local A, B = nil, nil
local ok, err = pcall(function()
  local T, tex = df.global.texture, df.global.enabler.textures
  if not A then for _, p in ipairs(T.page) do if p.token == 'LIQUIDS' and p.loaded then A = p.texpos[0]; break end end end
  B = B or dfhack.screen.findGraphicsTile('SW_AQ_LIQUIDS', 0, 0)
  print('A', A, 'B', B, 'raws', #tex.raws, 'init_texture_size', tex.init_texture_size)
  local pa, pb = tex.raws[A], tex.raws[B]
  print('before', tostring(pa), tostring(pb))
  tex.raws[A], tex.raws[B] = pb, pa
  print('after ', tostring(tex.raws[A]), tostring(tex.raws[B]))
  df.global.gps.do_clean_tile_cache = true
  df.global.gps.force_full_display_count = 2
  _G.AQ_SWAPPED = not _G.AQ_SWAPPED
  print('P6 swapped state', _G.AQ_SWAPPED)
end)
if not ok then print('P6 FAIL: ' .. tostring(err)) end
```

[R] Assigning a generic `pointer` vector element from Lua is unverified. If it raises an error, this route is C++
only.

### P7: river and flow frame sampler, 120 frames at the mouse cell (z and z+1)

```lua
local ok, err = pcall(function()
  local g = df.global.gps
  local mv, lv = g.main_viewport, g.lower_viewport[0]
  local pos = dfhack.gui.getMousePos(); if not pos then print('P7: no cell') return end
  local idx = (pos.x - df.global.window_x) * mv.dim_y + (pos.y - df.global.window_y)
  local F = {'screentexpos_background', 'screentexpos_background_two', 'screentexpos_high_flow',
             'screentexpos_liquid_flag', 'screentexpos_interface'}
  local rev = (_G.AQP or {}).rev or {}
  local hist, n, ph0 = {}, 0, df.global.map_renderer.tick_phase
  local function rec(tag, vp)
    if not vp or not vp.flag.active then return end
    for _, f in ipairs(F) do
      local o, v = pcall(function() return vp[f][idx] end)
      if o then local k = tag .. '.' .. f; hist[k] = hist[k] or {}; hist[k][v] = (hist[k][v] or 0) + 1 end
    end
  end
  local function step()
    n = n + 1; rec('main', mv); rec('low0', lv)
    if n < 120 then dfhack.timeout(1, 'frames', step) return end
    for k, t in pairs(hist) do
      local s = {}
      for v, c in pairs(t) do s[#s + 1] = ('%d%s x%d'):format(v, rev[v] and ('<' .. rev[v] .. '>') or '', c) end
      print(k, table.concat(s, ' | '))
    end
    print('tick_phase', ph0, '->', df.global.map_renderer.tick_phase, 'cur_tick_count', df.global.map_renderer.cur_tick_count)
  end
  dfhack.timeout(1, 'frames', step)
end)
if not ok then print('P7 FAIL: ' .. tostring(err)) end
```

Do one vanilla run and one with Flowing Water or the aquarium flows enabled. If the FLOWS or RIVER texpos varies
over the 120 frames, DF cycles frames and raws are enough. If one value repeats, the frame is fixed and the slot
rotation is the way.

### P8: liquid-flag histogram over the screen (diagnostic, O(cells) once)

```lua
local ok, err = pcall(function()
  local g = df.global.gps
  local function hist(vp, tag)
    if not vp or not vp.flag.active then return end
    local lf, n = vp.screentexpos_liquid_flag, vp.dim_x * vp.dim_y
    local anim, typ, edge = {}, {}, 0
    for i = 0, n - 1 do
      local v = lf[i]
      if v ~= 0 then
        anim[v & 3] = (anim[v & 3] or 0) + 1
        typ[(v >> 5) & 15] = (typ[(v >> 5) & 15] or 0) + 1
        if (v >> 9) ~= 0 then edge = edge + 1 end
      end
    end
    local a, t = {}, {}
    for k, c in pairs(anim) do a[#a + 1] = k .. ':' .. c end
    for k, c in pairs(typ) do t[#t + 1] = k .. ':' .. c end
    print(tag, 'anim{' .. table.concat(a, ' ') .. '}', 'type{' .. table.concat(t, ' ') .. '}', 'edged', edge)
  end
  hist(g.main_viewport, 'main')
  for k = 0, 7 do hist(g.lower_viewport[k], 'low' .. k) end
end)
if not ok then print('P8 FAIL: ' .. tostring(err)) end
```

### P9: force `center_animation` on a 9×9 patch for 240 frames (WRITE, self-clearing)

```lua
local ok, err = pcall(function()
  local mv = df.global.gps.main_viewport
  local pos = dfhack.gui.getMousePos(); if not pos then print('P9: no cell') return end
  local cx, cy, n = pos.x - df.global.window_x, pos.y - df.global.window_y, 0
  local function step()
    n = n + 1
    local a = (n // 8) % 4
    for dx = -4, 4 do for dy = -4, 4 do
      local x, y = cx + dx, cy + dy
      if x >= 0 and y >= 0 and x < mv.dim_x and y < mv.dim_y then
        local i = x * mv.dim_y + y
        local v = mv.screentexpos_liquid_flag[i]
        if v ~= 0 then mv.screentexpos_liquid_flag[i] = (v & ~3) | a end
      end
    end end
    if n < 240 then dfhack.timeout(1, 'frames', step) else print('P9 done') end
  end
  dfhack.timeout(1, 'frames', step)
end)
if not ok then print('P9 FAIL: ' .. tostring(err)) end
```

If a frames timeout writes too early (DF reprints before compositing), repeat the inner loop from the AquariumView
`onRenderFrame`, where background writes are known to reach the composite (F3).

### P10: cost of the creature-tint candidate scan

```lua
local ok, err = pcall(function()
  local t0 = os.clock()
  local wx, wy, wz = df.global.window_x, df.global.window_y, df.global.window_z
  local mv = df.global.gps.main_viewport
  local inview, wet = 0, 0
  for _, u in ipairs(df.global.world.units.active) do
    local p = u.pos
    local x, y = p.x - wx, p.y - wy
    if x >= 0 and y >= 0 and x < mv.dim_x and y < mv.dim_y and p.z <= wz and p.z >= wz - 8 then
      inview = inview + 1
      local f = dfhack.maps.getTileFlags(p)
      if f and f.flow_size > 0 and f.liquid_type == df.tile_liquid.Water then wet = wet + 1 end
    end
  end
  print(('P10 active=%d in-view=%d underwater=%d scan=%.2f ms'):format(#df.global.world.units.active, inview, wet,
        (os.clock() - t0) * 1000))
end)
if not ok then print('P10 FAIL: ' .. tostring(err)) end
```

The scan should run every ≈50 ticks. The per-frame veil write then touches only the `wet` list: top_shadow at
(x,y), only where it is 0.

---------------------------------------------------------------------------------------------------------------------

## 7. Verification checklist, in order

1. Run P1 and P2. Do lower-path and main-path UNDERWATER runs exist in separate slots? Does fill 2566 have its
   own slot?
2. P5 on the vanilla UNDERWATER run. Does the sea look right from z112 with **no lift** running? If so, delete the
   lift. That is the largest FPS win.
3. Run P3 on the six cells listed under P3: fog = MULTILEVEL_AIR in which viewport's interface layer, and what
   submerged ramp cells hold.
4. P4: is a one-time write persistent? This decides between O(changed) and O(planned) per frame.
5. P7, P8 and P9: does DF cycle FLOWS or RIVER frames, and on what?
6. Prototype the creature veil (P10 plus a top_shadow write in onRenderFrame), then measure ms per frame and the
   FPS on the user's ocean fort against the current 16-24.

## 8. Source index

- DFHack r2 structures: `library/xml/df.g_src.graphics.xml` (graphic_map_portst 248-344, graphic_viewportst 355-421,
  graphic/gps 724-840), `df.g_src.texture_handler.xml`, `df.g_src.enabler.xml` (enabler_textures 23-28,
  texture_fullid 42-57, renderer vmethods 98-128), `df.g_src.renderer_2d.xml`, `df.graphics_mainview.xml`,
  `df.d_init.xml:67`, `df.flow.xml:2-18`, `df.world.xml:713`, `df.game_v.xml:250-255`.
- DFHack r2 code: `plugins/smooth-movement/smooth-movement.cpp` (layer groups, viewport order, interface fog,
  update_all hook), `plugins/smooth-movement/visual_animation.h:23-36`, `library/modules/Screen.cpp:119-139, 256-283, 538-559`,
  `library/modules/Gui.cpp:3026-3038`, `library/modules/Textures.cpp:95-116, 303-309`,
  `scripts/devel/inspect-screen.lua:146-238, 282-310`, `docs/dev/Lua API.rst:3379-3437`.
- DF install: `data/vanilla/vanilla_environment/graphics/graphics_fluids.txt` (LIQUIDS 5-48, FLOWS*/BROOK*/RIVER* frames),
  `graphics_flows.txt` (10 FLOW_* tokens), `graphics_tiles.txt:53-55, 179-225, 719-766`, `tile_page_environment.txt`,
  `images/{flows,flows2-4,river,brook,liquids,multilevel_overlay,glass_floor}.png` (pixel stats computed with PIL),
  `Dwarf Fortress.exe` (token string tables near byte offset 24.59-24.64 M).
- Workshop (installed): Flowing Water 3419529410, Transparent Glass Floors 2978122014, White Z Fog 2899098612,
  Black Shadows and ZFog 2899669539. **Grey Z-fog 2899337501 is not installed.**

## 9. Rig results, 3 Oct 13:30 (AQS_OCEAN on region11, aquarium overlay OFF, view z123 one level above the sea)

- P1/P2: gps.texture_indices3 holds the token-bound tiles: [20143..20149] = SW_AQ_LIQUIDS col 0 (the mod's
  UNDERWATER_1..7, i.e. the re-bind lands in the table), [20151..20157] = LIQUIDS col 1 = **UNDERMAGMA** (not a
  lower-level water path; a test repoint briefly drew magma as water, reverted). Vanilla UNDERWATER (LIQUIDS col 0,
  texpos 167850..167856) is in NO table: nothing draws it any more.
- P3 at a sea cell seen from above: MAIN background = 164942 = RIVER page (0,0) = `RIVER_BED:1:1` (an opaque teal
  sheet); lower0 = liquid flag (lvl 7, water) + interface = MULTILEVEL_AIR fog; lower1..7 all zero (DF composites
  only the first water level below; nothing deeper, no bed).
  -> **the opaque teal "sea from above" is RIVER_BED frame 1 painted into the main background**, not a water sprite.
- texture_indices3[6525] is the only slot holding 164942. Repointing it once to a transparent tile (zero per-frame
  cost) removed the sheet: the view then shows lower0's water + fog, flat (no bed, no lower creatures) -- restored.
- Consequence: from above, the only thing DF can show is the top water level. Seeing the bed and creatures 2+ levels
  down needs either (a) per-frame work proportional to the cells we draw, or (b) a C++ plugin hooking the renderer.
