# Aquarium plugin: experiment log (from 3 Oct 2026, evening)

One entry per experiment: what was tried, what it looked like, what went wrong and why, and what fixed it.
Baseline: plugin 115dbfc (underlay + creatures), see `2026-10-03-plugin-depth.md`.
Rig: DF 53.16, DFHack 53.16-r2, CrossOver, fort AQS_OCEAN (region11) unless stated. GFPS is the plugin's
render-interval meter. Screenshots are in `data/aquarium-run/plugin/`.

## User play test of 115dbfc (3 Oct, evening): reported issues

| # | Report | First hypothesis |
|---|---|---|
| U1 | WASD is blippy: the sand bed flashes into place before the water overlay | plan keyed to `window_x/y/z`, but DF's buffers are reprinted later, so for a frame the swaps hit cells DF had not reprinted |
| U2 | z-change (Shift+>/<) pops the whole water layer out and in | same as U1, plus a whole plan rebuild + 3-15 ms compose at the new z |
| U3 | toggling the water-depth numbers leaves a ghost of the numbers stuck | numbers baked into the composed underlay (the lower viewports' `show_liquid_numbers` flag was on when composed); the recompose key ignores the flag |
| U4 | mist nice; no waves or surface motion | the plugin draws no waves yet (the Lua crests are off) |
| U5 | creatures skip layers: a shark at -2 shows from 0 but not from -1 | from -1 the view cell holds water; DF prints nothing below a water cell, and the plugin only drew k >= 2 |
| U6 | no slope sprite anywhere in the ocean | to check: ramp beds may never be classed as ramps |
| U7 | the previous (Lua) shading and slopes looked better | DF's water + fog tile per level is too dense and teal; the Lua tinted the bed by depth |
| U8 | approved: full sprites for the vermin-class fish in the aquarium mod | |
| U9 | unpaused, sea creatures do not move | to check |
| U10 | spawn pelagics and larger non-vermin sea animals | |
| U11 | some cavern tunnels render as sand (near the minimap's mystery squares) | bed-at-view-level rule paints sand over any floor holding water (cavern damp/puddles) |
| U12 | cavern fungiwood branch tiles keep the old water-coloured background | branch shapes are not treated as see-through, so the sheet stays under them |
| U13 | cavern slopes are the single pyramid nub | the bed ramp uses RAMP_OTHER, not a directional ramp |

## Entries

### E1-E2. WASD flash and z-change pop: plan keyed to the wrong clock (U1, U2)
- **Cause.** The plan (which screen cells look into water) was built on the core thread from `window_x/y/z`. Those
  change the moment a key is pressed. DF reprints the viewport buffers later, so the hook spent a frame or more with
  a plan for the new view and buffers for the old one. On a stale frame it skipped the underlay (DF's sheet showed:
  pop-out); on the frame it swapped, it zeroed the sheet at cells whose buffers still held the old view (the sand bed
  flashing through before DF's water arrived). A z change is the worst case: every cell changes, and the core thread
  rebuilt the plan only on its next update.
- **Probe.** `world->viewport` (`map_viewport`, DF's print parameters) carries `corner`, the map position the buffers
  were printed for. At rest corner == window; after a key press the window moves first.
- **Fix (v3).** The plan is built on the render thread, synchronously, whenever `world->viewport.corner` (or dims or
  shown depth) differs from the plan's. Cost on the rig: 0.07-0.08 ms per build at 80×45; compose 1.2 ms. Every
  frame's underlay, swaps and creature cells now refer to the same printed view. Creature marks carry map positions,
  converted with the plan's corner at draw time. Rechecked once a second for floods and digging (swapped in only when
  the cells differ).
- **Risk noted.** Map blocks are read on the render thread. DF does the same when printing; the plugin stops at map
  unload. Watch crashlogs.

### E3. Liquid-depth digits stuck in place (U3)
- **Cause.** Composing went through the lower viewports with DF's water value. A viewport whose
  `flag.show_liquid_numbers` was set drew the digit into the composed texture, and the recompose key ignored the flag,
  so the digits stayed after the toggle.
- **Fix (v3).** `compose_tile` clears `show_liquid_numbers` for its call (deeper levels never show digits). Tint
  shading draws no liquid at all. DF's own levels keep DF's digits.

### E4. Creatures skip layers: a shark at -2 shows from 0 but not from -1 (U5)
- **Cause.** The plugin drew levels from 2 down, assuming DF prints level 1 (lower0) itself. That holds only when the
  view cell is open: per column, DF prints down to the first water level and stops. From -1 the view cell is water,
  so DF printed nothing below it, and level 1 (where the shark was) belonged to nobody.
- **Fix (v3).** Per column, `fp` = 1 when the view cell holds water, else the first water level + 1. The plugin draws
  levels fp..bed (bed, tint, creatures). The viewport holding DF's sheet is level top-1, not always main.
  The underlay goes in before DF's first (deepest) viewport of the frame, not "lower0 or main".

### E5. No slope sprite anywhere in the ocean (U6)
- **Cause.** The column walk took the first water tile whose shape was not EMPTY as the bed. Over a submerged ramp the
  tile above is RAMP_TOP, and it holds water too. Every slope was classed as a floor one level too high: plan stats
  showed floor=1539 ramp=0.
- **Fix.** Watery RAMP_TOP continues down like open space. Same view: floor=1168 ramp=371.
- **Direction.** All DF ramp pages share one 47-tile layout named by the walls around the ramp (`RAMP_WITH_WALL_N_S_E`
  …, diagonals only where neither neighbouring side is a wall; `RAMP_OTHER` with no walls). The table is generated
  from the raws (`src/ramp_table.inc`). The wall mask comes from the 8 neighbours at the ramp's level. Shot e5/e6:
  slopes now show as shaded wedges under the water at every z.

### E6. Bed sprite by water body; view-level beds (U7, U11, U13)
- **View-level bed.** At z121 (bed at the view level), DF draws its dark fill (texpos 2566, the same as a wall top)
  under 7/7 water: probe at map 49,120,121, StonePebbles3 + fill. 115dbfc painted sand on every such cell. That is
  the cavern "tunnels rendered as sand": any floor holding water became sand.
- **Fix.** The fill texpos is learned from a wall cell at the view level, and only cells where DF drew exactly the fill
  get the bed sprite. A floor DF draws itself is left alone.
- **Families.** Surface standing or salt water: yellow sand floor + SAND_YELLOW_RAMPS (the user's choice). River and
  brook tiletypes: mud (the mod's SW_AQ_BEDS 0,0 when loaded, else DIRT_FLOOR_5B) + SOIL_RAMPS. Subterranean: true
  material (STONE_FLOOR_1 + STONE_RAMPS, or dirt + SOIL_RAMPS). Caverns no longer get sand or the RAMP_OTHER nub.
  Not yet seen in a cavern on the rig.
- **Shading.** `shade tint` (default): the bed, then one translucent fill for the water above it, alpha
  1-(1-a)^n with a = 60/255, colour #1e6478. It replaces DF's water tile + MULTILEVEL_AIR fog per level
  (`shade df`), which buried the bed at 4 deep. Shot e6: the bed and its slopes read through 1-4 levels, darker with
  depth; view-level shallows show bright sand.
- **Branches (U12).** BRANCH, TWIG and TRUNK_BRANCH count as see-through at the top of the column. Their
  `background_two` (the branch art) is kept; only the sheet in `background` goes. Not yet seen in a cavern on the rig.

### E7. Sea creatures never move when unpaused (U9); pelagic test stock (U10)
- **Measurement.** 245 units in water, unpaused for about 1,000 ticks: 0 of 240 spawned swimmers moved; the 5 natural
  magma crabs did.
- **Cause.** The test spawner (`scripts/oneoff/aq-spawn.lua`) skipped two of the six documented placement writes:
  the population reference and the flags2 roaming clears.
- **Controlled test.** Hake got the flags2 clears only, cod got the clears plus a population reference borrowed from a
  natural magma crab, herring were left untouched as the control. After about 1,000 ticks: cod 30/30 moved, hake
  0/30, herring 0/30. **A placed wild animal without a population reference never gets wander behaviour.** The
  product's `place` verb writes the reference, so this was the test props only.
- **Fix.** The spawner borrows a reference from any wild unit on the map and refuses without one. It also clears the
  flags2 bits and takes an optional map `box`. The 210 existing swimmers were fixed in place.
- **U10.** 56 non-vermin pelagics and large animals (13 species: bluefin tuna, swordfish, marlin, ocean sunfish,
  narwhal, basking shark, whale shark, hammerhead, tiger shark, shortfin mako, great barracuda, opah, stingray)
  placed in view at z119-122, saved as fort AQS_PELAGIC. Shot e7: every one is drawn from every z, with the plugin's
  per-depth tint on the deeper ones; DF's own sprites are correct for all of them.

### E8. Milky water: DF's z-fog over the tinted bed
- **Look.** With the bed + tint underlay, the view from above (z123) read pale and milky (e7 top row, e8 col 2).
- **Cause.** DF draws its MULTILEVEL_AIR fog (RGBA 89,146,172, a=96) in the interface layer of the deepest viewport
  it prints for a column (lower0 over the sea), on top of the plugin's levels: a light-blue haze over the tint.
- **Experiment (e8 grid):** vanilla | DF fog on | DF fog off | fog off + tint #145a6e a=90. Fog off gives a deeper
  teal-green with the bed's slopes intact. The darker tint stays closest to the vanilla ocean colour while keeping
  the depth cues.
- **Decision.** `fog off` by default (the fog is swapped out of that viewport's interface layer at planned columns
  with a bed below DF's level), tint #145a6e, alpha 80/level. `aquarium-plugin fog on` and `tint RRGGBB A` keep both
  tunable.

### E9. The vermin-fish placeholder fixed in the mod (U8, approved)
- `graphics/graphics_sw_aquarium_creatures.txt`, generated from the player's vanilla creature graphics. Every creature
  with a VERMIN tile and no DEFAULT (or LAYER_SET DEFAULT, or caste DEFAULT) gets
  `[CREATURE_GRAPHICS:T][DEFAULT:<its VERMIN page:x:y>:AS_IS]`. That is 114 creatures on vanilla 53.16.
- **Glitch 1.** The first build wrote `[DEFAULT:CREATURES_SMALL:0:92]`. After a reload,
  `creature_raw.graphics.creature_texture_texpos[0][DEFAULT]` was still 0: no error in errorlog.txt, the line was
  silently dropped. It was not file discovery: the same blocks appended to the mod's existing graphics file also
  stayed 0. **Cause:** a creature DEFAULT needs the colour mode as a fifth field (vanilla:
  `[DEFAULT:CREATURES_AQUATIC:0:3:AS_IS]`). With `:AS_IS` the reload gives hake 103003, salmon 102839, herring
  102991, squid 102799, none of them the placeholder (68053).
- DF merges CREATURE_GRAPHICS blocks by token across mods (vanilla already splits one creature across the small and
  portrait files), so the mod adds only the DEFAULT line.
- Python and Lua generators both write it (twin rule); `test_generator.py` checks them on a synthetic creature tree:
  0 failures. Installed into region11's world copy and reloaded as AQS_PELAGIC (shot e9).
- The plugin's placeholder swap stays as a fallback for worlds made without the updated mod.

### E10. Measuring pop-in frame by frame (verifies E1-E2)
- **Screen video doesn't work.** `screencapture -v` records the desktop, but DF lives on another Space; the window
  can't be targeted. `CGWindowListCreateImage` is gone in macOS 26 (ScreenCaptureKit only), and stills
  (~150 ms each) are too slow to catch a one-frame pop.
- **In-plugin probe.** `aquarium-plugin popprobe Y N` arms N frames. Right after DF draws main, `SDL_RenderReadPixels`
  reads one pixel row of the frame and records the share of DF's own water look (sea sheet from above (0,80,92), or
  dark water at its own level (20,64,74)), plus whether the underlay was placed. `popdump` lists the samples.
- **Detector validated.** Depth off at z123: 1000 permille sheet. Depth on: 0.
- **Result (v3, 8a508d5+).** 575 frames covering 8 z transitions and 5 pans pressed as real DF keys
  (CURSOR_*_Z, CURSOR_*_FAST): vanilla share 0-30 permille (max 3%: shore pixels), 0 frames without the underlay.
  Compose max 2.5 ms, plan 0.09 ms, worst frame gap 16.9 ms at 100 GFPS (cap).

### E11. Waves (U4)
- **What DF has.** In view at z123: 188-382 OceanWave flows, a few SeaFoam, and hundreds of Steam flows at z123/124.
  DF draws Steam and Mist through FLOW_* tokens: the mist the user liked is DF's own. No token exists for OceanWave
  or SeaFoam, so DF draws nothing for them. `flow_info.dest` holds garbage (e.g. 18384,5026,0), so it gives no
  direction.
- **Attempt 1: crests at the wave cells, facing the coast** (sum of directions to land within 4 tiles). Shot e11
  pair: crests appeared on grass and stone.
- **Probe.** Every OceanWave in view sits on dry beach (163 pebbles, 209 floor, a few shrubs, boulders and saplings),
  with no water at its level or below. In this fort DF's "ocean wave" is the wash on the sand, not a crest at sea.
  (The 2 Oct note "waves live on the open level above the sea" (F11) is wrong for this fort.)
- **Attempt 2: surf + wash.** Surf: a crest on each water cell next to a washed beach cell, facing it (strongest
  wave kept per water cell). Wash: foam lace on the beach cell's seaward edge, reaching up the sand and back over 4
  frames. SeaFoam (or a wave over water): speckles. Built on the core thread from the visible blocks' `flows` (the
  vectors are only walked there); drawn after DF's main viewport, before the UI, at the view level only. O(waves)
  copies per frame.
- **Glitch: "( ( (".** A curved, end-faded arc per cell read as a row of brackets. Crests are now near-straight and the
  full cell wide (curvature 0.008, sigma 1.8 px, foam trail 6 px, light break-up), and neighbours share a phase per
  3×3 block, so the surf reads as a line rolling in (e11d pair). Diagonal cells still show a quarter-arc.
- **Cost.** Unpaused at 80×45 with about 290 marks: GFPS 49-51 with waves on, 52-56 off (noisy; the simulation
  dominates). A per-draw `SDL_SetTextureAlphaMod` was replaced by 3 baked alpha tiers (density →
  tier): 3×3×9×4 = 324 sprites of 32×32, made once.
- **Open.** Diagonal crest shape. Waves are drawn only at the view level; from the water level they are above the
  camera and not shown.

### E12. River fort: sand that reads as dry ground; bed families verified
- **AQS_RIVER water by tiletype material at z127:** POOL floor/ramp 145/679 (murky pools: standing water, so sand),
  RIVER floor/ramp 186/245 (river, so mud).
- **Glitch.** At the water level (z127) the pools' sand and sand ramps read as almost dry tan ground (e12 grid, bottom
  right): the user's original "ocean surface looks like tan dry ground". The plugin tinted only the levels below
  DF's own. DF's top water tile is the mod's translucent one (about 35%), and a bed at the view level got no tint at
  all.
- **Fix.** The tint counts every water level from the top one down, DF's included: n = k - top + 1. A view-level bed
  (where DF drew its fill) is now composed into the underlay with its tint, and main's fill is swapped to
  transparent instead of to the sand sprite. Shot e12b: pools read as tinted water with sand slopes; the river reads
  dark over its mud bed, ramp banks visible, fish visible from z128 and z127.
- **Mud.** The mod's SW_AQ_BEDS page is not loaded in a world built with `--bake off` (nothing binds it), so mud
  falls back to DIRT_FLOOR_5B.

### E13. Caverns: unexplored caverns leaked; branches; stone slopes (U11-U13)
- **Glitch.** AQS_RIVER's cavern lake (z74-75) is undiscovered: vanilla shows it all dark. The plugin drew water, beds
  and dark maze-like floors there (e13 grid, right). It ignored `designation.hidden`. This also explains the user's
  cavern "mystery squares" and "tunnels as sand": hidden cavern water got beds.
- **Fix.** A hidden tile anywhere in the column ends it: `cells=0` over the undiscovered lake (e13b).
- **Revealed** (`reveal`, test fort only, not saved; e13c): vanilla paints an opaque bright-blue sheet over cavern
  water. The plugin shows translucent water over STONE_FLOOR_1 with STONE_RAMPS slopes (60 ramp beds in view). Fungiwood
  crowns (BRANCH/TWIG over the lake, about 450 cells) keep their art with water visible beneath them (U12).
- **Open.** At the cavern water level (z75), stone floor + tint reads darker than vanilla's blue. STONE_FLOOR_1's
  regular dot speckle shows as a dot grid over large lakes. Candidates: a lighter cave-floor sprite, a per-family
  tint.

### E14. The shore glow (user: "the soft glow along the shore is gone")
- **Rim gradient (first try, alpha 70).** On each planned cell, a light (214,240,236) gradient one sixth of a tile wide
  on every side whose neighbour is not planned water. Composed once per view into a second target texture and copied
  once per frame after DF's main viewport, under the waves. Too subtle at 70 (e14 grid).
- **DF's own edge art at partial alpha** (`glow df A`: RIVER_BED_N/S/E/W/corner variants and bevels, on shore cells
  only, at 150 and 220). Those tiles are mostly opaque teal, so the shore gets a dark frame, not a glow (e14b 2×2).
  Kept as an option, off.
- **The real source of vanilla's rounded shore.** DF draws the land's edging (grass, stone) curling over the water
  cell from the water cell's `floor_flag` edge bits. In 115dbfc those bits were cleared to kill dark corner squares,
  but the squares were the RIVER_BED_SE bevels in `background_two` (fixed separately, E-dark-squares of the depth
  log). Clearing `floor_flag` only squared off the shore.
- **Fix.** `floor_flag` is kept (E14c: rounded grass edges over translucent water, no dark squares), and the rim
  defaults to alpha 110.

### E15. Lake fort: pale shallows, a dark region, and three wrong theories
AQS_LAKE: lake surface at z102, 3,600 planned cells in the test view, 2,591 of them with the bed at the view level
(SoilFloor under 7/7 water, soil walls below).
- **Glitch A: pale shallows from above (z103).** Where the bed sat at DF's own first water level (top = bed = 1),
  the underlay drew the bed unshaded (the old "only below DF's level" rule) and DF's light water tile left it milky.
  **Fix:** in tint mode the tint always applies (n = bed - top + 1).
- **Glitch B: a large region at z102 stayed exactly vanilla-dark.** Things tried, in order:
  1. *Compose raced DF's reprint.* The compose drew view-level beds only where it saw DF's fill at compose time.
     Changed to always compose. No change.
  2. *Transparent background over nothing.* A view cell holding water has no lower viewport printed, so making main's
     fill transparent shows blank, not the underlay. True, and fixed: DF draws the bed itself (swap fill → bed
     sprite), and the bed's one-level tint moved to the surface layer, copied after main (which also veils
     creatures swimming at the view level). Still dark.
  3. *Is the swap reaching DF at all?* Counters showed 2,591 view-level beds and 2,591 swapped. A debug switch
     blanked their liquid flag: z101 cells went dry (the swap reaches DF there), z102 unchanged. *Does DF diff
     against `_old`?* No: after DF draws with the swapped sand, `screentexpos_background_old` still holds 2566.
  4. **Actual cause: fill learning.** After a redeploy, `tex_fill` was relearned from "the first wall cell in view",
     and at z102 that wall drew its own sprite, not the generic fill. The status line then read "DF fill under 0,
     swapped 0": nothing matched, nothing was swapped. (The earlier "2591 swapped" reading came from a fill learned
     in the previous fort.) **Fix:** the fill is the commonest main background among view-level bed cells (DF puts
     it under every submerged floor), accepted at a 40% share of 8 or more cells.
- **Result (e15f).** z102 and z101 both show sand under tinted water in the shallows (olive), teal over the deeper
  slopes, and fish visible. Debug switches were removed afterwards; the view-level bed counters stay in `status`.

### E16. Regression on the ocean (AQS_PELAGIC), plugin e798a36
- **Look (e16 grid).** z123: translucent water over sand slopes, pelagics at every depth, surf line along the beach,
  soft rim, no dark corner squares now that `floor_flag` is kept. z122/z121: sand beds in the shallows, fish and
  sharks from every z. Surf alpha tiers lowered to 0.35/0.5/0.68 (at 0.5-0.95 the crests read loud).
- **Cost (paused, 80×45, all features on).** GFPS 100.0 (the frame cap) with depth on against 80.3-80.9 off. Compose
  max 1.75 ms per view change, plan 0.11 ms.
- **Pop probe.** 343 frames, 6 z transitions + pans: 0 frames with DF's own water look, 0 without the underlay.

## Status of the user's reports (U1-U13), plugin e798a36 + tool fe72c29

| # | Report | Status | Entry |
|---|---|---|---|
| U1 | WASD sand flash | fixed: plan keyed to `world->viewport.corner`; probe shows 0 bad frames | E1, E10, E16 |
| U2 | z-change pop | fixed: same, plus synchronous plan + compose (≤ 2.5 ms) | E1, E10, E16 |
| U3 | depth digits stuck | fixed: never composed | E3 |
| U4 | no waves / surface motion | surf crests + beach wash from DF's OceanWave flows; foam; mist is DF's own | E11 |
| U5 | creatures skip layers | fixed: per-column first plugin level `fp` | E4 |
| U6 | no slope sprite | fixed: watery RAMP_TOP; directional ramps from wall masks | E5 |
| U7 | old shading looked better | tint model (bed + depth tint over every level), DF fog off, grass edging kept | E6, E8, E12, E14 |
| U8 | fish sprites in the mod | done: 114 creatures, Python and Lua generators, test 0 failures | E9 |
| U9 | sea creatures do not move | test spawner defect (no population reference); fixed | E7 |
| U10 | pelagics for testing | 56 placed, 13 species, all drawn correctly | E7 |
| U11 | cavern tunnels as sand | fixed: hidden tiles skipped; fill replaced only where DF drew fill | E6, E13 |
| U12 | fungiwood branch backgrounds | fixed: branch shapes see-through, branch art kept | E6, E13 |
| U13 | cavern slope nub | fixed: true-material directional ramps (STONE_RAMPS) | E5, E6, E13 |

**Still open:** the diagonal surf crest shape; the cavern water-level look is darker than vanilla (stone floor + tint);
mud needs the beds page in `--bake off` worlds; lake shimmer and river flow-direction streaks (v3) are not built in
the plugin yet; the tool's Lua per-cell aquarium overlay re-enables itself on load and should stand down when the
plugin is on.
