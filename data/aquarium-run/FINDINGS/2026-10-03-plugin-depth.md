# Aquarium C++ plugin: depth and creatures, rig results (3 Oct 2026)

Rig: DF 53.16, DFHack 53.16-r2, CrossOver. Fort AQS_OCEAN (region11), at 120×68 (the user's zoom). The Lua aquarium
overlay was OFF for every number here (after a restart it switched itself back on and spoiled the first A/B).
Plugin source: `Projects/sw-wt/aquarium-plugin`, commits 632ca97 (stage 1, per-cell redraw), a082795 (underlay),
115dbfc (creatures). Build and deploy: `docs/dfhack-plugin-build.md`. GFPS is the plugin's own render-interval meter
(the time between `update_all` calls). DF's `calculated_gfps` disagreed with it and is too noisy to use.

## Facts about DF's renderer (measured)

1. **DF repaints every world cell, every frame.** A stack drawn once with no redraw was gone in the next screenshot
   (s4-persist). `gps.force_full_display_count` stays at 13; it is not a one-shot counter.
2. **DF draws whole viewports with `renderer::update_full_viewport`**, once per frame each: lower_viewport[0] first,
   then main, at about 1.5 ms of CPU each at 120×68. Over the sea it never calls it for lower1..7.
3. **Redrawing cells one by one costs about 1.4 µs per `update_viewport_tile` call, and almost all of it is outside
   the hook** (SDL/GPU under CrossOver):

   | design | calls per frame | frame time | GFPS |
   |---|---|---|---|
   | vanilla | 0 | 23.5 ms | 42.5 |
   | per-cell stacks, every level | 22,785 | 59.4 ms | 16.8 |
   | per-cell stacks, bed + top only | 15,746 | 43.8 ms | 22.8 |
   | **underlay texture (shipped)** | 1 copy | 20.9 ms | **47.8** |

4. Over the sea seen from above, main holds the RIVER page column-0 art: RIVER_BED in `background` and the
   RIVER_BED_* edge variants (S, S_E, S_W …) in `background` / `background_two`, with edge bits in `floor_flag`.
   lower0 holds the water (liquid flag 0x3c) plus MULTILEVEL_AIR fog (texpos 22229). lower1..7 are empty.
5. **Units of vermin-class creatures get DF's placeholder sprite.** Salmon, herring, shad, hake and squid
   (VERMIN_FISH, with only a `VERMIN` tile in graphics_creatures_small.txt) are drawn as `DEFAULTS:0:0` (texpos
   125969), a teal blob, when they are spawned as units. That is the user's "salmon looks like a Gorlak". Cod,
   octopus and sharks have DEFAULT sprites and look right. Animals carry no `unit->texpos` (it is 0). DF picks
   their sprite from `creature_raw.graphics.creature_texture_texpos` plus a frame/facing offset (cod base 71331,
   drawn as 71493).

## The design that shipped (underlay)

- Core thread (`plugin_onupdate`): a column plan per view (first water level, bed level, bed shape) built from map
  blocks. It is rebuilt on a view change, and every 20 calls otherwise (swapped in only when it differs). The
  in-water creature list is rebuilt every call.
- Render thread, on the first `update_full_viewport` of lower0/main in a frame:
  1. When the view or plan changes, compose the deeper levels of every planned column into a screen-sized SDL target
     texture, with DF's own `update_viewport_tile` and the render target redirected. Each column gets the sand bed,
     then water + fog per level, down to lower1. This takes 3–15 ms per view.
  2. One blended copy of that texture.
  3. Creatures two or more levels down: their sprite, then the water + fog steps above them. This is O(creatures).
- During DF's main draw, at the planned cells: the background (the sheet), the `floor_flag` edge bits and the
  `background_two` bevels are swapped out (when the view cell is open space). A bed at the view level gets sand.
  The placeholder sprite is swapped for the creature's own vermin sprite in main and lower0. Every value is
  restored after the call.
- Switches: `aquarium-plugin depth on|off`, `levels all|bed`, `surface on|off` (default off: one more water layer
  on top made the sea opaque), `cell X Y` (dumps every viewport's layers), and the status line.

## What the user sees now (screenshots in data/aquarium-run/plugin/)

- Above the sea (z123): translucent teal in place of the flat sheet, a lighter sand band in the 1-level shallows,
  and fish one or more levels down visible (s7, s9 grid). The shore's dark corner squares are fixed (they were
  RIVER_BED_SE bevels in background_two).
- Underwater (z122/z121): the sand bed shows through translucent water, deeper patches read darker, and fish have
  their real sprites (s10 grid; left = vanilla, right = plugin).
- Performance: faster than vanilla, because main no longer draws the opaque sheet.

## Open

- A 4-deep column with `levels all` still hides most of the bed. Next to try: fog only on the middle levels, or a
  graded tint.
- The ramp bed uses the generic SAND_YELLOW_RAMPS RAMP_OTHER. Directional ramps (the user's slopes) are next.
- Shore glow lost: it was part of the RIVER_BED_* sheet art.
- Scroll: each view step recomposes (3–15 ms one-off). Holding WASD still needs a test for hitching.
- Root fix for the placeholder: add `DEFAULT` creature graphics for the vermin-class fish to the aquarium mod
  (reuse each fish's CREATURES_SMALL tile), so they look right without the plugin too.
- River and lake forts: not yet tested with the plugin.
