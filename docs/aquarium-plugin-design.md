# Aquarium plugin: design for stage 1 (depth compositing)

Status: draft, 3 Oct 2026. It is written while stage 0 (the toolchain, plus a hook that only counts frames) is
still being built. Each claim is marked [V] if read in DFHack r2 source or on the rig, or [I] if inferred and
still needs a rig probe.

## Why a plugin

- DF composites only the first water level below the camera. Seen from above, the sea is the `RIVER_BED:1:1`
  sheet drawn into the main background (one texpos slot, `texture_indices3[6525]`). Under it, lower0 holds the
  water and its fog. lower1 to lower7 are empty: no bed and nothing deeper (render-internals section 9) [V].
- The Lua route had to work per cell, every frame, which put the ocean fort at 16-24 FPS. The user chose a C++
  plugin (3 Oct).

## Mechanism: the smooth-movement model

- Hook `renderer_2d_base::update_all`. The world is already drawn when it runs, and DF's own `update_all` then
  draws the UI on top (`smooth-movement.cpp:846-850`) [V].
- Inside the hook, redraw single cells with `renderer->update_viewport_tile(vp, x, y)`. Any buffer value can be
  swapped in for the call with `scoped_value_restorest` and restored afterwards, so DF's own buffers are never left
  changed (`:216-240, :314-328`) [V].
- Draw order is lower_viewport[7] → … → [0] → main (`:700-712, :767`). Each viewport's `screentexpos_interface`
  holds one level of z-fog (MULTILEVEL_AIR). Redrawing a stack level by level therefore deepens the fog by one step
  per level, which is the effect DF itself gives [V for the plugin, I for DF].
- Buffer index: `x * dim_y + y`, column-major (`:316`) [V]. Main cell (x,y) is map tile
  (window_x + x, window_y + y, window_z).
- Every `screentexpos_*` buffer has an `_old` twin. DF probably redraws only the cells that changed [I]. The plan
  below never depends on that, because every stack it draws starts from an opaque bottom tile. So redrawing a
  stack every frame cannot pile up translucent layers.
- `++gps->force_full_display_count` forces a full repaint. Call it whenever a toggle changes what the plugin
  draws (`:910-925`) [V].

## Stage 1: bed, water levels and fog

For each main cell over water, the plugin draws its own stack. It has to do this whenever the view level holds
water, or the cell is open space with water within D levels below. D = min(8,
`number_of_lower_elevations_shown`).

1. Column plan (cached per view; rebuilt when window_x/y/z or the dims change, and otherwise every N ticks):
   - Walk down from the view z. Record `top` (first water level) and `bed` (first level whose tile is not open
     water: floor, ramp or wall), up to D levels down. Also record the bed tile: floor, ramp with direction, or
     wall.
   - Read only map blocks (`Maps::getTileBlock`, designation `flow_size` and `liquid_type`, tiletype shape). This
     is cheap in C++.
2. Draw, per planned cell, from the bottom up:
   - **Bottom** (opaque): the bed sprite in a scratch slot. Sand floor for standing water (`FLOOR_SAND`; user
     choice, 3 Oct), mud for rivers, the ramp sprite for ramps (the user wants submerged slopes visible), and a
     dark fill for walls or a missing bed. Draw it through `lower_viewport[min(bed,7)]` with every other layer
     zeroed.
   - **Each water level** k = bed-1 … 1: zero lower_viewport[k]'s buffers at that index, then set:
     - `liquid_flag` = the water value DF wrote for that level. Copy the encoding from lower0, where DF already
       draws the top water level; never invent it.
     - `screentexpos` = the texpos of the creature there, if any (stage 2);
     - `interface` = the MULTILEVEL_AIR fog texpos.
     Then call `update_viewport_tile`.
   - **lower0 and main**: redraw with DF's own values. The `RIVER_BED` sheet in the main background is made
     transparent by repointing slot 6525 once while the plugin is enabled (restore on disable/unload).
     Repointing costs nothing per frame and was proven on the rig.
3. Turning it off restores slot 6525 and calls `force_full_display_count`.

Cost model to measure on the rig: `update_viewport_tile` calls per frame = Σ over the planned cells of
(depth + 1). That is about 6,000 at a 120×68 zoom on a 4-deep sea. Map reads happen only when the plan is
rebuilt. Budget: under 2 ms per frame at that zoom. If a call costs too much, draw the bottom and one
mid-level only.

## Stage 2: creatures under water, and a veil

- Units carry their own sprite: `unit->texpos[3][2]` with `texpos_currently_in_use` (`df.unit.xml:3128-3130`) [V
  field; which index is the body sprite is still to be probed].
- Candidate list: active units in the view rectangle whose tile has water. It is rebuilt with the column plan,
  so the per-frame cost is O(units in view).
- **Deeper creatures**: write the unit's texpos into `screentexpos` of the scratch lower viewport at its level,
  before the fog above it is drawn. Each level of water above it then tints it.
- **Creatures at the view level**: DF draws them over their own water. Write a translucent veil tile into the
  main `screentexpos_top_shadow`, at that cell only and only where the layer is 0, then redraw that cell. This is
  the glass-floor idea run the other way round (user, 3 Oct: "a translucent or hazy tint that overlays creature
  tiles who are underwater").

## Stage 3: the user's other v2 and v3 items (kept from the Lua work)

- Wave crests, from DF's OceanWave/SeaFoam flows. Read on a tick change only, cached, and drawn per frame as
  O(flows).
- Mist on the dry beach: DF's own FLOW_WATER_MIST tiles.
- Lake-only shimmer.
- River streaks that follow `perm_flow_dir`. The direction table comes from the Lua v2 work.

## Rig probes before stage 1 code is trusted

1. The cost of one `update_viewport_tile` call (time 1,000 calls in the hook).
2. Are all 8 lower viewports allocated, with the same dims as main, even when `flag.active` is 0? Use the same
   `viewport_readable` test as smooth-movement. If they are not, draw through lower0 for every level.
3. What `liquid_flag` value does lower0 hold at a 7/7 water cell? Copy it at runtime.
4. Which `unit->texpos[i][j]` is the body sprite? Compare it with the main `screentexpos` at a visible unit.
5. Scroll test. Hold WASD over the sea, with no pop-in allowed, because the plan is keyed by the view.
