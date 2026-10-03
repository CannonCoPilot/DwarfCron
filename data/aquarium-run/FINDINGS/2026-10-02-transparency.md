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
10. No river animation in DF 53.16 fortress mode, vanilla included: river cells with perm_flow_dir ~= 0 (RinghatchetsReady
    12,175,55; AQUA_LAKE ~40,000 tiles) carry liquid_flag 0x3c; unpaused 6-frame bursts change 0 map pixels in both worlds.
    Water motion (flow streaks, shimmer) must be drawn by the tool (v7.1-waves phase 2).

## 23:20-23:50 (AQUA_SHORE16; rc 8648530 -> eddaf21 -> 4ab50cc/077b433 -> 924d2b6)
11. DF keeps every wave front and OceanWave flow on the OPEN level above the sea (probe: 622 fronts all at z112; sea
    water at z111). Waves 'water cells only' classed them as land -> nothing drawn at either level. Fixed eddaf21 (sea =
    water at z, or open over water 1-2 down; fronts read from z-1..z+1): next run painted 217-400 cells, crests merged.
12. Bed lift paint 2.37 ms avg (821 cells x ~9 viewport accesses) fused at the 2 ms budget; 6000 lifted cells at a wide
    view = 8.4 ms. ~0.32 us per userdata access on the rig (~9x desk Lua). Fixed bf8d79a: per-scan plan, 2 writes/cell,
    sentinels, swimmers only near units; fail-soft degrade steps before the fuse.
13. PIXEL ORDER: DFHack r2 Textures::createTile builds an SDL_PIXELFORMAT_RGBA32 surface from the uint32 vector (R at
    the lowest address) -> on the little-endian host a pixel is 0xAABBGGRR. The aquarium packed 0xRRGGBBAA everywhere,
    so every run-time sprite had its channels scrambled: pale crests/shimmer/surf at alpha 40-70 drew as OPAQUE CYAN
    (shot 20261002-233123-look/shots/clear-433-606-z111-on.png), and the bed's colours were wrong since d900381 (the
    'grey stone'). Desk previews decode the same wrong order, so they looked right. Fixed 924d2b6: makeTile byte-swaps
    at the DF boundary; harness/preview stubs now model DF's order.

## 3 Oct 00:00-09:20 (v1 per the user's priorities; rc 24ceca2/5f7404c)
14. USER PRIORITIES (2 Oct late): v1 = see-through water (sand bed ocean, mud fresh) + creatures below the view tinted per
    level; v2 = subtle ocean crests from DF's waves + DF mist on the dry ocean edge; v3 = flow streaks / shimmer (now OFF).
15. Script bed v1 on the rig (40x23 view): ocean z111/z112 see-through over sand, paint 0.05 ms, no fuse
    (20261003-001452-look). But single opaque cells remain at the beach level, and on AQUA_LAKE's river bank (z56) a
    diagonal checker of unlifted cells; the user sees water 'clip in and out' when scrolling (stale per-view plan).
16. RAWS BAKE TEST (20261003-091205-bake): DF's sand_floor tile composited UNDER each of the mod's UNDERWATER tiles
    (opaque) -> at the water level the sea shows sand through water with NO script at all. From one level up DF still
    draws the vanilla opaque teal (raws never reach lower viewports). USER CHOSE: bake sand into all standing water
    (ocean/lake/pool/cavern share UNDERWATER_1..7); rivers/brooks mud via RIVER_BED_*/BROOK_BED_*. Script shrinks to
    the from-above lift (liquid flag + creatures + fog), rebuilt in the frame the view moves.
