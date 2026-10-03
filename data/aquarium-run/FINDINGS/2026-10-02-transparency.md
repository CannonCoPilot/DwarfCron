# Aquarium transparency: rig findings, 2 Oct 2026 22:15-22:45 (AQUA_LAKE, region10, mod loaded)

1. The mod loads and re-binds the water sprite: vanilla (0,71,88) -> aquarium (20,60,73) -> clear (29,55,67) in the same cells.
2. DF draws NO bed under a water cell. gps.main_viewport.screentexpos_background for a shallow river cell (RiverE, shape
   FLOOR, water 7/7) = 2566, the same texpos as a SoilWall cell (the generic dark fill); floor_flag 0, background_two 0,
   liquid_flag 0x3c. Translucent water therefore shows only that fill, underlay ~(49,44,52). Deep lake cells (shape EMPTY)
   show the same fill through DF's lower-level fog.
3. A per-frame write of a bed sprite into screentexpos_background under every water cell (in the aquarium view overlay's
   onRenderFrame) reaches the composite: with findGraphicsTile('FLOOR_SAND',0,0) the sandy bed shows through the clear
   preset with the fish on top (shots: data/aquarium-run/20261002-222358-shallow/shots/clear-shallow-bed-sand.png vs
   clear-shallow.png). DIRT_FLOOR (FLOORS 0,6) drew nearly black: greyscale sprite, needs the material colour.
4. Standing water is static in vanilla too: liquid_flag 0x3c unchanged over 79 unpaused ticks; whole-frame diffs change
   only the FPS counter. Animation = flowing-river/brook streaks (RIVER_TO_*/BROOK_TO_*), waterfall mist, ocean waves.
5. aquarium-run issues: target finder too slow for a 384x384x73 map (deadline stop: lake 'None'); the river target was a
   deep lake cell; AQUA_SHORE embark failed (placement mode not entered: zoomed=true); T2 needs --fish; legend not on
   screen; lens marks touch dry land (3.99 > 3.0).
Build: agent on branch v7.1-bed (bed painter layer). Probe: scripts/oneoff/aq-shallow.py.

## 23:15-23:40 (AQUA_SHORE16 sea; rc d900381 with the bed layer)
6. Bed layer at the water's own level (view z 111): works (821 cells, stone, deep tiers, paint 0.02 ms avg).
7. From the land level (view z 112) the sea is drawn by DF through gps.lower_viewport[0] with the VANILLA opaque water
   sprite ((0,77.2,90.2) = vanilla liquids.png UNDERWATER_7): the mod's re-bound tokens do not apply to lower viewports.
   Overriding TILE_PAGE:LIQUIDS in the mod (full-size copy, same id) changed nothing, even after a DF restart (reverted).
   Writes into lower_viewport[0].screentexpos_background never reach the screen (composited before overlays).
8. 'Lift' works: copying lower_viewport[0]'s liquid flag into the main viewport's liquid flag (main cell open space) and
   writing the bed into main background draws DF's own translucent water over the bed at the view level (776 cells;
   bed-*/z112-lift.png). Open-space backgrounds: 15561, shore variants 15577..15657 with floor_flag edge bits (keep them).
9. Waves overlay: every crest is ours (widget disabled -> none); DF draws nothing for waves/foam. Crests on dry land,
   fronts drawn as vertical columns of glyphs, `waves off` lagging: redesign under way (v7.1-waves).
