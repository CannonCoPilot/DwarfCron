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

### E17. Surf as a line along the shore; the Lua overlay stands down; a hung `status` (plugin 3007a6b)
- **Glitch: "( )" around headlands** (resume-check vs e17-surf-pair). Each water cell next to a washed beach cell
  got a crest facing that one beach cell. Around a one-tile grass point the cells west and east of it faced each
  other, so the crests bracketed it.
- **Fix 1: the shore normal.** A surf cell's direction is now the inverse-square-weighted sum of the directions to
  land within 3 tiles, binned to 8 ways. A crest is drawn only where its beach cell lies along that normal (dot ≥
  0.6), so a headland's flanks get none. The phase is shared along the line square to the normal, so a straight
  shore rolls in together. The wash uses the normal away from the sea.
- **Glitch: crests still bowed** (e17-surf-a-zoom). Diagonal crests at corners and the east face's crests read as
  ")" arcs. A waves-off shot proved they were the plugin's. An offline render of the sprite set
  (scratchpad crest_sprites.png) showed the 0.008·across² bow is plain at 32 px.
- **Fix 2:** straight crests (bow 0). Result (e17-straight-crop): straight strokes along the coast, no brackets.
  Diagonal coasts get short slanted strokes, not a joined line.
- **The Lua overlay re-enabled itself on load.** It now asks the plugin's own `isEnabled` (`dfhack.open_plugin`,
  once a second) and drops every Lua layer while the plugin runs. `aquarium status` says "STANDING DOWN" (tool rc
  bf4c93c, rig-verified).
- **`aquarium-plugin status` timed out over RPC** while the bare command replied. `status` was not a verb, and
  DFHack's wrong-usage path (printing the help) never replies over RPC. It is a verb now.

### E18. River mud without the mod; one-deep rivers milky; cavern water level (plugin 3007a6b + defaults)
- **Mud.** The plugin now makes its own river bed: DF's DIRT_FLOOR_5 (FLOORS 1,7), read from
  `enabler->textures.raws`, converted to RGBA32, and recoloured as the mod builder does (luminance contrast 45%,
  scaled into 178,136,88; no baked water). It is registered with `Textures::createTile`. Status shows
  `mud=… (DIRT_FLOOR_5 recoloured)` in AQS_RIVER, a `--bake off` world.
- **Glitch: the river from above (z128) was a pale milky blue** with no bed (e17-river-pair, right). The `cell` probe
  over the channel showed lower0 `iface=173256` = MULTILEVEL_OVERLAY 3,3, DF's z-fog. The plugin stripped the fog
  only where `bed > top`, but a one-deep river's bed is DF's first water level (`bed == top`).
- **Fix:** strip it where `bed >= top`. Result (e18-river-pair): clear dark teal, crisp fish.
- **Mud tint ladder** (e18-mud-ladder: 80 / 45 / 30). DF's own (mod) water tile gives most of the teal, so the
  tint changes little. 50 lets the mud's texture show and is now the mud default.
- **Cavern (AQS_RIVER, `reveal`, not saved; e18-cave-trio, e18-cave-tints).** The bed is now SMOOTH_FLOOR (FLOORS
  6,3), opaque grey stone. STONE_FLOOR_1 is a few pebbles on transparency, which drew a dot grid. Mean water colour
  at z76: vanilla (1,83,98); plugin #2a7896/64 (33,83,95); #00708e/88 (26,82,96). Brightness now matches vanilla.
  It stays greyer because the bed shows through, which vanilla's opaque sheet never allows. #00708e/88 is now the
  cavern default. `tint RRGGBB [alpha] [sand|mud|stone|soil|surface|cavern|all]` sets any family live.

### E19. Surface motion: lake shimmer and river streaks in the plugin (plugin d85075e, d39da3e)
- **Model.** Each planned column records its water body at the top water tile: cavern (subterranean), sea
  (`water_salt`), river (current set, or RIVER/BROOK material), else lake (lakes and pools). A river also records its
  current from `liquid_flow.perm_flow_dir`. The plan cuts the view into horizontal runs of one effect (at most 24
  cells). Six pattern textures are made once, tileable in x and y, at 32 px per cell: two caustic webs and four
  streak fields (E-W, N-S, NE-SW, NW-SE). Each frame, each run is one `SDL_RenderCopy` from a source rect at the run's
  world position plus an offset that slides with time. The pattern is world-anchored, so scrolling never makes it
  swim. Caustics: two webs drifting apart, crossfaded over 4.2 s. Streaks: the source slides against the current at
  28 px/s.
- **Glitch: rain** (e19-river-pair). DF's current varies per tile: the river's middle ran SW, its banks S. Mixed
  slashes read as rain. Smoothing to the mean current within 2 cells made them uniform but diagonal across a N-S
  channel (e19b), still rain.
- **Fix:** streaks run along the channel's local axis (the principal axis of the river cells within 3, used where the
  spread exceeds 0.3), signed by the current. Longer, sparser dashes (18-35 px, lanes 8 px apart). Result
  (e19c-river-crop): streaks run down the N-S reach and turn with the SW bend.
- **Motion measured** (pixels changed > 8 between two shots 0.3 s apart): river 3,218 and pool 1,664 with the
  effects on; 0 and 0 with them off.
- **Glitch: wallpaper** (e19-lake-pair, AQS_LAKE, 3,600 lake cells). Three low-frequency waves with an 8-cell period
  tiled visibly.
- **Fix:** a 16-cell period and five waves of 2-3 cell wavelength per web, lines sharper (power 6), alpha 45.
  Result (e19d-lake-pair): an irregular web with no visible repeat.
- **Cost.** 360 copies for the whole lake view: GFPS 100.0 (cap) on and off; viewport time +0.04 ms per frame.
  Textures 6 × 1280×544 ARGB (16.7 MB).
- `shimmer on|off|ALPHA`, `streaks on|off|ALPHA`; status line `bodies sea= lake= river= (with current) cavern=;
  motion … runs= drawn=`.

### E20. Starts by itself; a crash on map load; regression; the release package (plugin e0ff17a, package 74f23fb4)
- **Want.** `enable aquarium` alone drew nothing after a load: depth went off on unload and had to be turned on by
  hand. Now a remembered choice (`depth off` clears it) turns depth on when the plugin is enabled with a map loaded,
  and after every map load.
- **Crash (17:38, crashlog empty).** The first build started depth inside `SC_MAP_LOADED`. Starting it meant
  looking up tiles and deleting and remaking the mud texture while DF was still loading its own textures (both push
  onto `enabler->textures.raws`). The game hung on the load and wrote a crash log.
- **Fix.** The map-load start is deferred to the first `plugin_onupdate` after the load. The mud tile is made once
  per process and its texpos re-read through the handle each time. Verified: enable at the title, then AQS_PELAGIC →
  AQS_RIVER → AQS_PELAGIC. Depth came on by itself each time with no crash, and the mud texpos was re-resolved
  (167669, 167789, 167838).
- **Regression (AQS_PELAGIC).** Pop probe, 400 frames over 6 z transitions (z121-123) and 4 fast pans: 0 frames
  with DF's sheet, 0 without the underlay. Look (e20-ocean-pair): straight surf along the beach, translucent water
  over sand slopes, pelagics at every depth. Bodies: sea 798, so no shimmer runs on the sea.
- **Package.** `scripts/package.sh` refuses a dirty tree, rebuilds, checks that the dll names 53.16-r2, and zips
  `hack/plugins/aquarium.plug.dll` + README (requirements, install, persistence via `dfhack.init`, commands, cost,
  uninstall) + SHA256SUMS into `dist/aquarium-plugin-dfhack-53.16-r2-<commit>.zip`. The packaged dll is
  byte-identical to the one validated on the rig (cmp), and it is running there now.

### E21. User play test 4 Oct: crest strokes ugly; no light web on the sea (plugin 52b8488d)
- **Report** (user screenshot 2026-10-04 7.06 PM, own fort Kideturdim, sea surface z127): "the ocean wave sprites
  are ugly and not natural looking", and the pool's surface web "should also be present on the ocean water".
- **Web on the sea:** sea cells now get the shimmer runs too (1,907 sea cells in view, 111 runs).
- **Surf, try 1: foam band per land side** (e21-foam-zoom). A soft band from the land edge whose reach swells and
  ebbs (8 frames, 3.4 s), lace inside, phase stepping 0.11 cycle per tile along the coast. It read as frosted
  glass rectangles: a filled pale band with a hard outer edge, stepping between cells, and a gap at every outer
  corner of the land.
- **Try 2: bubbles + a broken lip + corner pieces** (e21b-foam-zoom). Quarter-round pieces where only the diagonal
  is land; phase step 0.035. It read as a white chalk dashed outline: the lip was too sharp and the coarse noise
  threshold cut it into dashes.
- **Try 3: soft continuous swash lip + a fainter outer swell half a cycle behind + sparse bubbles** (e21c-pair).
  Every term can be set live (`foam LIP BUBBLES WIDTH OUTER BREAK`; the sprites are rebaked on the render thread),
  so tuning needs no rebuild. Result: soft swell lines that follow the coast and round its corners. Defaults
  45 15 20 25 10 (between e21c's left and right). DF's OceanWave flows raise the foam to the stronger tier where
  they wash the beach. The white crest and wash strokes are no longer drawn; SeaFoam speckles stay.

### E22. The plugin crashed the user's game (3 Oct 19:10)
- **Evidence.** `backtrace_10_3.txt` (19:11): page fault reading 0x1e60 in `aquarium.plug+0x19a9d`, called from
  `+0x2550f` via dfhack, on dfhooks' update path (the core thread). Disassembling the shipped dll (74f23fb4,
  capstone): `mov edi, [rax + rcx*4]` with rax = 0 (`vp->screentexpos`, field +0x90) and rcx = 0x798 (index 1944 = cell
  57,6 in the user's 60×34 view). The code reads race/caste and inserts into `seen_sprite`: it is
  `build_creatures`, which learned swimmer sprites by reading DF's screen buffers from the core thread. A buffer was
  null mid-reallocation (the user zooms; the rig was always 80×45).
- **Fix.** The core thread no longer touches any screen buffer. Marks carry race/caste, and the render thread learns
  each sprite inside `swap_for_level`, while DF draws that viewport. `usable()` now requires every buffer the plugin
  touches, and `place_underlay` skips the frame if any lower viewport in reach is not usable.
- **Stress (the user's live game, paused).** 20 batched zoom-ins and 20 batched zoom-outs, then 15 zoom in/out pairs
  0.12 s apart: no crash, no new crash log, GFPS 98.8-99.9. (The user's sea held no swimmers, so this exercised the
  buffer guards, not the learning path; the old core-thread read is gone.)
- Older backtraces (`backtrace_10_1` 1 Oct, `backtrace.txt` 2 Oct) predate the plugin (Lua overlay / DF).
- **Install note (same day).** The user's own sessions never ran `enable aquarium` (empty `dfhack.init`), so no save
  showed the effects. `enable aquarium` was added to `dfhack-config/init/dfhack.init` (backup `.bak-20261003`).

### E23. Shimmer under the surface; no sea creatures (user 4 Oct, plugin and package 2702b7ca)
- **Report:** "The surface shimmer texture should not appear on water tiles below the surface z-layer. I also see no
  sea creatures."
- **Shimmer.** Runs and foam were cut for every planned column, including views from under water (view level holds
  water and so does the level above). Each column now records `surface`: its top water level has no water above it
  (for top = 0, z+1 is read). Runs, streaks and foam come only from surface columns. In the user's fort: z127 (the
  surface) 285 runs and 458 foam edges; z126 0 and 0 (e23-pair).
- **Creatures.** The user's fort: 0 sea-creature units (the 3 "in water" are fire imps in magma). 80 vermin in
  liquid, of which about 15 are sea fish (14 bat rays, 1 clownfish), the rest cavern and magma kinds. The
  seasonal-wildlife tool's water layer is OFF in that fort ("Layers: land"), so nothing stocks the sea. The plugin
  drew only units. It now also draws vermin in the water below DF's levels with their own vermin sprite
  (`creature_small_texpos`), excluded from sprite learning (else a unit's sprite at the vermin's cell would be
  learned for every vermin). After the swap: creatures_in_water 1-3, all drawn.
- Status counters `drawn=` for motion and foam keep the last non-empty value when nothing is drawn (cosmetic).

### E24. Surface skin one level too deep; river with no current; DF's waves (user 4 Oct 9.16 PM; plugin 04d3924e)
- **Skin.** From Elevation -1 (looking down at the sea) the skin is right; from Elevation -2 (the camera in the top
  water level) it also showed. E23's rule (no skin only when water lies above the view level) kept it. Now a column
  gets the skin only when the camera looks down onto its water (`top >= 1`). User's fort: z128 292 runs / 586 foam
  edges, z127 0 / 0 (e24-sea-pair).
- **River.** All 64 sampled river tiles at z127 have `perm_flow_dir` = inactive, so the plugin had no current and drew
  no streaks. The world river's path gives the direction: river 146 runs (28,29) → end (28,28), north into the sea.
  The plugin builds a downstream table per world tile from `world_data.rivers` when depth starts (`course_at`). After
  the swap: river 219 cells, all with a current; streaks run along the channel (e24-river-zoom).
- **DF's ocean waves.** About 230 OceanWave flows sit on the wet beach at z128 (SoilWetFloor / pebbles / driftwood),
  as on the rig (E11). Each is drawn as a foam wash running up the sand from the sea side. Its reach (swash frame) and
  strength come from the wave's density, so the washes move as DF moves its waves (137 drawn in view).

### E25. Creatures 2+ levels down in a light square (user 4 Oct 9.21 PM)
- **Cause.** Each creature below got `shade_above`, a tint rectangle over its whole tile. The bed around it had already
  been tinted for its own (deeper) depth, so the tile was tinted twice: a visible square.
- **Fix.** Creatures are drawn on their own screen-size layer (through the main viewport's tile path), each tinted by
  a MOD fill that multiplies only its own pixels (transparent pixels stay transparent), and the layer is copied once.
  At full strength a multiply left near-black silhouettes, so the tint is 0.55 of the bed's, toward the tint hue
  brightened (70 + 2×rgb) (e25-creatures-zoom: sponges and fish keep their shape, no squares).

### E26. The water-layer scan: bad and slow (user 4 Oct: "make a fast and good one")
- **Bad.** Both of the tool's scans (`ENGINE.waterTiles`, sampled; `V7.WB`, the registry) named water by the REGION
  BIOME of a run's top tile. The user's river (fresh, RIVER tiles) lies in an ocean region tile: registry body #2
  "ocean fresh 221 tiles", river 0. Meanwhile waterTiles called every fresh non-stagnant tile "river" (2,635 river
  tiles, mostly pools).
- **Good: DF's tile evidence.** A run is flowing (a river) if any of its tiles has a RIVER/BROOK bed, an active
  `perm_flow_dir`, or is falling water (open space with water below and at most 2 wet neighbours). Salt water is sea
  unless its biome is a lake; stagnant water is a pool; other standing water is a lake, or a pool under `pool_max`
  columns. Flowing water is typed river wherever it runs (it no longer needs to reach the map edge).
- **Fast.** The plugin exports `scan_water(bands)` (DFHACK_PLUGIN_LUA_COMMANDS): one C++ pass over the map blocks of
  the surface band and every discovered cavern, runs and classes in the tool's encodings, and the union-find. The
  registry (`V7.WB.build`) uses it when the plugin is loaded. The Lua scan remains the fallback, with the same
  evidence. User's fort, 144×144, 14 levels, 6,810 runs: native pass 2.7 ms (10 ms with the Lua records) against 80 ms
  for the Lua scan, with identical results: ocean 1, river 2 (212 + 13 tiles), pool 8. A 768×768 embark is about 28×
  the tiles: tens of ms native, where the Lua scan took seconds sliced over many ticks.
- **Live:** `water scan` in the user's fort: "#2 now a river (was ocean)".
- **Surface at any z / waterfalls.** The plugin plans per screen column: from the view level down to that column's
  first water, wherever it is, so a high river and a pool far below each get their own surface in the same view. A
  waterfall column (falling water) gets no skin (DF draws its mist), and in the registry it belongs to the river
  (flowing evidence), while the plunge pool's standing water is its own body.

### E27. "Fake wave action at water edges" (user 5 Oct, 7.36 AM; plugin a603818f)
- **Checked first:** the dll in the user's fort was byte-identical to the latest build (E24-E26 were live: scan_water
  present, river current 25/25). The look was the design, not a stale swap.
- **What drew at the edges:** (1) the shore rim (E14), a light gradient on every water cell beside land; (2) the E21
  foam on every sea edge, on the plugin's own 3.4 s clock (303 edges in view), only its strength raised beside DF's
  waves. Both read as wave action DF never simulated.
- **Step 1:** foam only on edges beside a DF wave, frame from its density: 145 of 303 edges. DF waves line most of
  this coast (323), so the outline stayed (e27-dfwaves).
- **Step 2:** rim off (`glow rim 0`): the outline on calm stretches went, and white bands stayed beside the waves
  (e27-rim-pair).
- **Fix:** only DF's own wave tiles are drawn: each OceanWave flow on the beach is a foam wash from the sea side, its
  reach and strength from its density, so it moves as DF moves the flow (85 in view). Water-edge foam (`surf on`) and
  the rim (`glow rim N`) are off by default, kept as options. DF's own sea mist still draws over the near-shore water
  (e27-wash-only).

### E28. "DF's waves aren't being drawn" (user 5 Oct)
- **Probe (user's view, paused).** 142 OceanWave flows (z128, densities mostly 20-70 of 100) and 145 Steam flows
  (z128-129). DF draws the Steam (DF's sea spray) with FLOW_WATER_MIST, here the aquarium mod's SW_AQ_MIST art: the
  light-blue squiggles. For OceanWave it draws nothing: the cell's high_flow and interface layers are empty, and the
  vanilla graphics have no wave token at all.
- **Why ours did not show:** the E27 washes went only on wave tiles touching the sea (84 of 142), as a thin edge lace
  from the sea side that read as faint arcs.
- **Try 1: a swash per tile** (a translucent sheet, foam lace, a ragged lip landward; e28b-trio): cracked glass,
  hard tile squares, and lips at different angles tile to tile.
- **Try 2: world-anchored foam** (two tileable laces at period fx_period, crossfaded and drifting; e28c-trio):
  seamless, but 16 px blobs at a low threshold read as snow camouflage.
- **Fix:** fine sparse foam (2-8 px cells, bubbles above 0.6) over a thin sea-blue wet film, strength 0.3 + 0.5 x
  density, on every OceanWave tile at the view level (142 of 142 drawn; e28d-pair). It churns in place and moves as DF
  moves its flows.

### E29. Finding DF's real wave-front process (user 5 Oct, ASCII screenshots 8.03-8.05 AM)
- **The user's point:** the Steam build runs a wave-front process that ASCII draws as moving white/grey/purple '~'
  over the water. Everything before this entry drew the wrong thing: E11-E28 used OceanWave FLOWS, which sit only on
  the beach.
- **Steps that ruled things out (user's fort, Elevation -1 = z128 over the sea at z127):**
  1. Flow sprite slots: `gps.texture_indices8[1564..1603]` hold the 10 vanilla flow tokens x 4 density frames
     (MIASMA, DUST, WATER_MIST = the mod's SW_AQ_MIST, LAVA_MIST, BOILING, VAPOR, DRAGONFIRE, FIRE, SMOKE, ITEM),
     followed by SHADOWS_WALL. No empty wave slot sits beside them, and vanilla has no wave token.
  2. Main-viewport layers at OceanWave, Steam and SeaFoam cells: all empty (high_flow 0).
  3. A dummy into the 40 flow slots (magenta X, `texture_indices8`, restored at once) proved nothing: the game was in
     ASCII mode then, so no graphics slot is read.
  4. Flows by z and medium over the whole map: OceanWave only on beach floors (z128), Steam on floors and in the air
     (z128-131); nothing in or over the water.
  5. ASCII glyphs read back with `dfhack.screen.readTile`: the white/grey shaded blocks (░▒▓█ by density, █ = 100)
     are STEAM flows, DF's sea spray, which graphics mode draws with the mod's mist art.
- **Found:** `df.event.xml` `event_handlerst.ocean_waves` = `event_ocean_wave_frontst` { dest (coord2d, the coast),
  cur (coord2d), z, active (set when it reaches the coast and starts spawning flows), move_timer, vis_duration
  (starts at 120, randomly decrements) }, made by `ocean_wave_makers` (3 here, 210 fronts, all z128). Proof: of
  about 800 water-below cells in view, exactly 42 drew '~' (126) instead of '≈' (247), and those were the 42 fronts
  in view; every other water cell was '≈'. ASCII draws a front by swapping the water glyph.
- **Plugin:** fronts read on the core thread (`world->event.ocean_waves`) are drawn on the open tile above the
  column's top water: a crest across the travel direction (cur → dest), strength from vis_duration.
  `fronts dummy` draws a magenta X control tile on every front, for a side-by-side check with ASCII '~'.
  The OceanWave-flow beach wash is off by default (`wash on`).
- **Also fixed:** in ASCII mode the plugin painted its water over the map (e29-dummy-small, right side); it now
  stands down when `Screen::inGraphicsMode()` is false (e29-ascii-after-small).
- **Pending:** the dummy confirmation in graphics mode. The user's game was in ASCII; dummy mode is armed in the
  live fort.

### E30. The wave cycle, confirmed with dummy tiles in graphics mode (user 5 Oct, 8.23-8.29 AM)
- **The user's ASCII sequence:** purple '~' (waves over deeper water) → white '~' (over depth-1 water at the coast) →
  on reaching land, mist (░ U+2591 / 176, ▒ U+2592 / 177).
- **Stage 1 = wave fronts** (`world.event.ocean_waves`). The user's graphics screenshot 8.28.45 with `fronts dummy`:
  magenta X lines exactly on the purple '~' lines (ASCII 8.23.23-8.24.08). Confirmed.
- **Stage 2 = OceanWave flows**, which a front spawns when it reaches the coast (`spawn_flows`, "set once the wave reaches
  the coast"). The first dummy pass skipped them (the beach wash was off), so the white stage was lost. The second
  pass draws a yellow X on every OceanWave flow at the view level (e30-dummies): 0 fronts left in the world at that
  moment (all landed) and yellow along the whole coast, where ASCII draws the white '~'. Earlier read-back agreed:
  white '~' glyphs sat on cells with OceanWave flows (E29 table: ch126/247 fg7 → flow).
- **Stage 3 = Steam flows** (the mist ░▒▓█ by density), drawn by DF itself with FLOW_WATER_MIST (the mod's SW_AQ_MIST).
- So the whole DF wave is: front (moves over the sea; vis_duration fades) → lands → OceanWave flows on the coastal
  tiles → Steam. Graphics mode has art only for stage 3. The plugin draws stage 1 (crests) and stage 2 (`wash`).

### E31. Art for the two wave stages graphics mode leaves blank (5 Oct, plugin a72462b)
- **Stage 1, fronts** (`world.event.ocean_waves`, ASCII purple '~'): a soft white crest square to the front's travel.
  It has a foam lace broken at two scales, a faint shoulder ahead and a streaky wake behind. Its 5 strength tiers
  follow `vis_duration` (120 → 0). One clock drives every front, so a row bobs as one crest.
  The lace is periodic along the line (32 px, or 32√2 on diagonals), so neighbouring fronts join.
  - First cut (e31-preview, pass 1): a 32 px sprite left a gap at every corner of a diagonal line, because the band
    crosses into the two side tiles there. Fix: a 48 px sprite overhangs each neighbour by 8 px and crossfades its
    ends into the next front's (the two ends sum to 1). The preview showed a seamless diagonal.
- **Stage 2, landed OceanWave flows** (ASCII white '~'): two small level white '~' strokes per tile, with layout and
  frame phase hashed from world position and 5 tiers from density. These draw with `fronts on`; the old foam
  blobs (the user's "pretend") stay behind `wash on`.
  - A ripple phase shift along the stroke turned '~' into '^' arcs that read as gulls (preview pass 1). The shape is
    now fixed and only bobs and slides.
  - Turned square to each tile's shore, the strokes jumbled into 'S' shapes round the island (e31-island). Now level
    as ASCII draws them (e31-island-level).
- **Live check (user fort, paused, 0 fronts in the world at the time):** 152 wave tiles drawn, wavelets correct on
  the island and coast (e31-island-level). Crests are not seen live yet: they need fronts in flight (unpause).
- **Not done:** fronts step a whole tile at a time. `move_timer` (DF `duration`) could slide the crest between
  tiles, but its count direction is unmeasured: the game was paused and the rig was down.

### E32. The white stage is the front itself at vis_duration 0 (user 5 Oct, screenshots 8.46.36-8.47.18; plugin follows a72462b)
- **User report:** the crest showed over the purple stage, then faded away and nothing was drawn for the white stage.
  It reappeared only as '~' wavelets and mist on the edge tiles. Wanted: purple faded, white bold.
- **Recorder** (30 samples while the game ran, `scratchpad/waves.jsonl`): `vis_duration` falls 120 → 0 while the front
  is still ~10 tiles from `dest`. The front then keeps moving at vis 0 over water 2 and then 1 deep, until it stops
  1-2 tiles short of the coast and is removed. `spawn_flows` is set within a few hundred ticks of creation, not "on
  reaching the coast" as the xml says. Beach OceanWave flows stay at 250-360 (all z128, dry) throughout, with no jump
  when fronts arrive: they are a standing beach population, not what a landing front leaves. So the E30 claim
  "white '~' = OceanWave flows" was wrong. The white stage is a front at vis 0, and the plugin skipped those
  (`vis_duration <= 0`).
- **Fix:** fronts with vis 0 are drawn at the boldest tier. While the counter runs they are faint (tiers 0-2, rising
  as it falls).
- **Rig cost lesson:** the recorder ran a full-map Lua scan (every block's flows plus getTileFlags) over RPC every
  0.6 s. That gave the user half-second freezes every few seconds, and it was stopped. Never poll the user's game
  with map-wide Lua.
- **Pending:** the user's eye on the bold white crest. The '~' wavelets on the beach OceanWave flows are kept as a
  placeholder for foam (user).

### E33. '~' only where a front lands, then fading (user 5 Oct, screenshots 9.00.46-9.01.25)
- **User:** the crests look really good. But the '~' foam placeholders were always present. They should appear only
  once a front reaches the last water tile before the edge, stay a few moments, and fade.
- **Cause:** the '~' hung on DF's OceanWave flows, which stand on the beach all the time (E32).
- **Fix:** the plugin tracks landings itself on the core pass (`track_landings`, about 240 fronts, a few tile reads
  each). A front lands when its next tile towards `dest` is shore. Fallback: it vanishes within 3 tiles of `dest`
  without that, and lands at the first shore tile along its last step. Each front lands once (pointer set; a pointer
  that jumps more than 2 tiles counts as a new front). The tile ahead and the two beside it (for a diagonal: ahead and
  the two sides of the corner) are marked. They show the '~' for 1.5 s, then fade over 2.5 s (8 baked tiers).
- **One-shot check** (user fort, paused): `dest` is a shore tile for 236 of 239 fronts, so every front sees shore
  ahead before it is removed. For 104 fronts the tile before `dest` is shore too, so they land at the last water
  tile on their straight path, as the user asked.
- **Pending:** the user's eye on a live landing (game paused at swap; nothing polled).

### E34. The blue square behind moving creatures (user 5 Oct, screenshots 9.15.35-9.17.00)
- **Symptom:** a fish that has just moved shows a solid square behind it that hides the bed. Measured colour
  (20,65,75), which is DF's own "dark water at its own level" look: DF's fill tile (2566) under its water layer,
  with no plugin tint. So DF drew that cell with no plugin swaps applied.
- **Ruled out, in order:**
  - a plan miss: the plan reads map tiles, not what DF printed;
  - the stand-in sprite: DEFAULTS(0,0) is a teal blob;
  - the mod re-binding water tiles: no mod touches UNDERWATER_*;
  - stray backgrounds at levels the plugin does not swap: 0 hits in 3.1M creature-cell checks, game running;
  - a liquid flag specific to creatures at the sheet level: every sheet cell has fill + liq 0x3c, creature or not;
  - any cell on main still holding fill under water after the swaps: 0 in 9,325 frames, running.
  A frame-exact pixel probe (60 SDL reads a frame) dropped the user's game to 7-11 GFPS and was withdrawn after
  about 200 frames. Never read pixels per creature per frame.
- **Found:** DF's full pass goes through the `update_viewport_tile` vmethod once per tile per level (73,440 calls a
  frame at 120x68x9). DF also calls it on its own, about 200 times per level per frame while the game runs, early in
  its frame before the full passes. The plugin's swaps existed only around full passes. With the fix counting:
  10,093 lone redraws in 2,027 frames would have drawn fill under water on a planned main cell, 2,813 of them on a
  creature's cell.
- **Fix (plugin, commit after f051398):** hook `update_viewport_tile`. A lone redraw of a planned cell gets the same
  per-cell swaps as a full pass: `swap_cell_bg`, factored out of `swap_for_level`, plus fog and placeholder. It uses
  the last plan while the camera has not moved. Once this frame's underlay is placed, the underlay, the creature
  layer and the shore tint go back around the tile. `tilefix on|off`; `status` counts lone redraws, fixed redraws and
  would-be dark-water draws. GFPS unchanged (62-66).
- **Pending:** the user's eye on moving fish.

### E35. The square was still there, now water over black (user 5 Oct)
- **User:** "blue background tile still seems visible". Capture e35-1: a 48x32 px block (3x2 tiles at 16 px) round a
  fish, colour (0,46,54): DF's water layer over black, no longer fill under water. So E34's swaps did reach the
  screen, which proves the lone redraws are what shows. But DF wipes the tile first, and most lone redraws come before
  the frame's underlay is placed, when E34 skipped putting the plugin's layers back.
- **The 3x2 shape:** the creature's tile, the two beside it and the row above. These are the left/right and
  upleft/up/upright creature layers, where a creature's sprite can spill, and DF redraws them together.
- **Fix:** on the first lone redraw of a planned cell per frame, the last composed underlay and creature layer go
  back under it (the shore tint after main) whenever plan corner, zoom and origin still hold.
- **Verified:** 6 captures of the running fort over 10 s, 0 blocks of either colour (detector: 12x12 windows, 70%
  within 5 of (20,64,74) or (0,45,53)). The same detector finds 26 hits on the pre-fix capture. 60 GFPS.
  **Withdrawn by E36:** six captures were too few. The squares came back with the game running (user, screenshots
  10.08.45, 10.09.48, 10.09.57).

### E36. The square's real cause: repeated lone redraws stack water (user 5 Oct)
- **User:** "background tile mismatches still remain": a dark square behind a moving fish in a cavern river, the sea
  and the shallows.
- **Twelve blind variants (A-P) failed.** They rebuilt the tile after main, skipped lone redraws, laid 1 or 4 copies
  of the bed, turned off the creature layer, DF shadows or the liquid flag, or corrected the origin. Captures counted
  0-9 squares per frame for each variant and for `tilefix off`, too noisy to rank.
- **Measured instead:** a render-thread tile probe (`tileprobe N`, armed for 4-6 frames only; see E34 on per-frame
  reads). It reads one pixel of each tracked creature tile after every step DF and the plugin draw, in order. The
  frame order is: full passes (underlay, levels 8..1, main, shore tint, waves) -> `update_all` (lone redraws) ->
  `render` (present). The target is the window back buffer throughout (`SDL_GetRenderTarget` null at frame start,
  main pass and render, 164/164). So what is shown is the full-pass picture plus that frame's lone redraws on top.
  E34/E35 had the order backwards.
- **Cause:** for a moving creature, DF blanks its tiles and redraws every level of each of them, some two or three
  times in one frame. In trace f488 tile (35,9): levels 8..1 twice each, then main three times. The first main
  redraw gives the right colour (3c584c, equal to the full pass after the shore tint). Each repeat lays DF's
  half-clear water layer and the shore tint over the last: 474f51, then 333f43. That is the dark square. It stays
  until the next full pass, after the present, so it follows the fish frame after frame.
- **Dead end:** a snapshot of the clean picture, put back before the present. It can't work: DF draws into the back
  buffer, which SDL cannot copy from.
- **Fix (plugin, commit after 289b1cc):** one lone redraw per (cell, level) per frame; repeats are dropped. `status`
  counts them ("lone redraws dropped as repeats ...": 56,029 in 846 frames, game running). Also: unknown or
  malformed `aquarium-plugin` commands (and `depth`/`tint` errors) return CR_FAILURE with a message, not
  CR_WRONG_USAGE, which hangs an RPC caller.
- **Verified (user's fort, game running, 60 creatures in water):** detector (a cell darker than its 8 neighbours by a
  near-uniform multiply, 3 static map features excluded) gives 0 squares in 15 captures with the fix vs 17 in 15
  with it off, back to back in one session (S / Soff). The final build gives 0 in 20 (T). Crops show fish and the
  dolphin on clean bed and water. GFPS 57.3, unchanged. Data: `data/aquarium-run/e36/` (tileprobe-1.tsv is the
  cause trace; S, Soff, T are the captures; detect.py).

### E37. The user's water art per body, plants, sponges (user 5 Oct)
- **Asked:** ocean = wind ripples (more alpha) -> soft crest (deep) -> whitecap (shallow) -> swash, out-and-fade ->
  wind wisps; rivers = 'simple water flow'; caverns, pools, reservoirs = caustic web (more alpha); seaweed on the
  ocean floor, seagrass on river floors, both shaded; nothing preys on sponges; sponges breed.
- **Done (plugin 619269f, live in the user's fort):**
  - Skins: sea = two periodic ripple fields (alpha 110); lake/pool/cavern = caustic web at 80 (was 45; cavern water
    had none); river = madmedicsoft's 'Simple water flow' (OGA, CC0). That art is an opaque teal tile, so its 7
    colours are mapped to highlights and faint shadows over transparency, turned to the current's heading, 2 px a
    frame, 8 frames, alpha 200.
  - Fronts: soft crest while vis > 0, whitecap at vis 0.
  - Landing: swash runs up 0.7 s (decelerating lip), then fades 1.9 s where it stopped. Landings now carry the
    front's direction. First cut drew a 0.30 film over the whole wet part: glassy blocks on every shore tile, so
    the film now thins away from the lip.
  - Wisps: the user's game draws mist from the aquarium mod's SW_AQ_MIST page (texpos 30011-30014), not vanilla
    EVENT_FLOWS (`status` now lists main's flow sprites); both are hidden in high_flow (full passes and lone
    redraws) and wisps drawn. At the sampler's strength 300 mist tiles at a river mouth read as a snowstorm:
    alpha per density 55-145.
  - Plants: vanilla has no seaweed. Seaweed = RICE (PLANT_CROPS 0,11) and HERB_VALLEY (PLANT_STANDARD 0,11)
    recoloured kelp, 14% of flat sea-floor beds. Seagrass = REED_ROPE (0,14) and GRASS_LONGLAND (0,10) tinted,
    24% of river beds. They sit in DF's plant slot (background_two) on the bed, so the water tint shades them;
    beds at the view level get them in the fill swap, tinted on the surface layer. Candidates:
    data/aquarium-run/plants/.
- **Seen (Kideturdin fort, river mouth at 105,81 z128, pool at 11,12; captures data/aquarium-run/e37/):** ripples,
  whitecaps in rows (S and W fronts), swash lip on the rocks, light wisps, flow overlay on the river with the bed
  showing, seaweed and seagrass shaded. GFPS 102-117 at 60x34. Cavern water not seen: no cavern revealed in that fort.
- **Sponges (seasonal-wildlife branch v7.1-sponge d5a98fe, NOT deployed):** vanilla SPONGE/GIANT_SPONGE/SPONGE_MAN
  are not vermin (DF's vermin hunting cannot take them) and have one sexless DEFAULT caste (cannot breed).
  `MODEL.NEVER_PREY` keeps them out of the food web, relation writes and lures; `V7.sweep` clears any
  predator relation DF writes onto a sponge. The aquarium mod adds `[SELECT_CREATURE:SPONGE][CASTE:FEMALE][FEMALE]
  [CASTE:MALE][MALE]`. Open: DF may keep DEFAULT as a third caste; GIANT_SPONGE copies tags from SPONGE, maybe before
  the mod edit; wild animals may not breed on the map at all; installing into a save that already holds sponges
  could remap their castes. Test on the rig on a new world before it goes to the user's game.

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

**Closed since (E17-E19):** the diagonal/headland surf shape (straight crests along the shore normal); the cavern
water-level look (brightness matched, smooth stone bed); mud in `--bake off` worlds (made in the plugin); lake
shimmer and river streaks (in the plugin, on by default); the Lua overlay stands down while the plugin is enabled.
**Packaged:** `sw-wt/aquarium-plugin/dist/aquarium-plugin-dfhack-53.16-r2-5fe7208c.zip` (crash fix + foam, E21-E22; 74f23fb4 is withdrawn: it can crash).
**Still open:** diagonal coasts get short slanted strokes rather than a joined line; the dll is tied to DFHack
53.16-r2 and must be rebuilt for each DFHack release.

### E37 reverted (user 5 Oct, evening)
- The user rejected the E37 art pass as a whole ("go back to how it was"); plugin master 3258b86 reverts 619269f and 900381d
  (source = 0a35dae). Work now follows the user's checklist one item at a time (water-graphics-v2 page).
- **B1, transparency missing (Shortsling, Boatsbowed):** E37's river-flow overlay at alpha 200 hid the bed and was also laid on
  the lake (the plugin classes most of Shortsling's lake as river: 1 lake / 866 river cells in view; moved to W3). A/B at one
  view: now / E37 / now (data/aquarium-run/b1/ab.png). User confirmed the rollback looks right.

### E38. B2: 2 FPS on unpause, blue blocks, no fronts (Learnedchanneled = AQUA_SHORE16, 768x768x131)
- **Speed is DF, not the plugin or the tool.** Fresh load, 20 s arms (ticks advanced): plugin on 29; tool + plugin both off
  25 (gfps 1). The second 20 s reach ~7-9 fps and the third ~37 whatever is on. The tool's own worst tick is 51 ms (1.1 s of
  Lua in 75 s). A 16x16 embark is 16x a 4x4's area; DF's first unpause warms up for ~40 s.
- **Blue blocks = hidden tiles under a visible sea.** A fresh embark hides the unseen sea floor (bed hidden in nearly every
  sampled column; lower levels hidden on the west side). plan_column returned false on ANY hidden tile (E13's cavern rule),
  so 148 of 8,160 cells in view were left to DF's dark water; `reveal` planned them, `unreveal` dropped them again
  (b2/reveal-ab.png). Fix: a hidden tile ends a column only above the first water; below a visible surface the water is
  drawn and a hidden bed gets the body's usual family (never real material or ramp). Unrevealed: 8,160 planned, blocks gone
  (b2/fix-ab.png). Hidden cavern water (704,392,66) still plans 0 cells.
- **Fronts:** drawing never filtered hidden tiles. None existed while the sim crawled; after 75 s unpaused the world had 1,032
  fronts and 233 landings, 152 drawn in reach at the coast (b2/s5-fronts.png).
- **Correction (user 5 Oct, 6.30 PM screenshots: still glitchy; "sounds like pure guesswork").** The "bed hidden" sample read
  the tile BELOW the lowest water level (solid ground, always hidden), so it was no evidence, and "nobody has seen the sea
  floor" was an inference. Measured after: no tile flagged `outside` is hidden anywhere at z 104-118 (stride 8); every sea tile
  z 108-112 is `outside` and visible; the water tiles at 200,718-766 that were hidden at the fresh load are visible after the
  game ran. The dark areas in the user's screenshots are UNEXPLAINED; item left open (user: move on). 6ffe06d kept: it only
  changes columns with a hidden tile under visible water, which a healthy map should not have.

### E39. B3: creatures one level down look like they float on top (Gilttrumpets, Flagcontains)
- **Cause (code + measurement).** Per column the plugin leaves levels 0..fp-1 to DF (fp = top + 1 when the camera is above the
  water), and `draw_creatures` skipped k < fp. A swimmer in the first water level was therefore DF's own sprite, printed after
  the plugin's underlay and over the water: no veil. Learnedchanneled, shark 12562 at 221,696,111 (top water level), camera z112:
  `drawn_below=1` of 8 swimmers in view.
- **Fix.** `first_creature_level(c)` = top when top >= 1; `swap_for_level` blanks DF's screentexpos for a swimmer whose cell's
  first water level is this viewport (after learning its sprite); the plugin draws it in its creature layer with the one-level
  tint. After: `drawn_below=8` of 8; the shark is teal under the water (b3/ab.png); 4 captures unpaused show no untinted frame
  (b3/run-grid.png).
- **Vermin missed (user 6.57 PM, a thornback ray bright from above, dimmed at its own level).** FISH_RAY_THORNBACK is a
  vermin (206,656,111, first water level); DF prints vermin in `screentexpos_vermin`, and the first fix blanked only
  `screentexpos`. Now the vermin layer is blanked for vermin marks. After the swap a thornback at 490,670,111 draws tinted
  under the water from z112 (b3/ray-ab.png, lower half; the "before" capture fired before the camera moved; the user's
  screenshot is the before).
- **User confirmed B3 (7.04 PM):** "no more surface-level renders that appear above water."

### E40. B7: items on a submerged bed invisible from above (user 5 Oct, 7.04 PM, osprey corpses)
- **Cause (code).** The plugin composes each bed cell itself (`compose_tile`), which zeroes every DF layer of that cell,
  item layer included, so corpses lying on the bed vanished under the water until the camera stood on their level.
- **Fix.** The underlay reads the item sprite DF printed for the bed level (`screentexpos_item` of that lower viewport) and
  composes it with the floor; the depth tint then shades it. Learnedchanneled: a spiny dogfish corpse at 353,692,108 now shows from z110
  (b7/after2-zoom.png); the grey row beside it is 11 LIVE sponges (units 12650-12660), drawn as swimmers before this change,
  not items. The user's dead sponge: no sponge item or killed sponge unit on the map at 7.15 PM. Limit: the underlay is recomposed when the plan changes, so an
  item that lands on the bed while the view stands still appears at the next pan or level change.
- **E40 WITHDRAWN (user 7.17 PM: the dogfish corpse still vanishes one level up).** A per-level counter on the render thread
  (DF's `screentexpos_item` on planned bed cells, levels 1-8) read 0 at every camera level z109-z112: DF prints NO item sprite
  into any lower level under water, so composing "the item DF printed" can never work. The z110 capture that seemed to show
  the corpse is unexplained and not relied on. 9272a86 reverted (fe0bd91); plugin source = 40fc7af (B3), live in the user's
  game. A real fix needs the plugin to collect items on submerged beds itself (core thread, like creatures) and resolve each
  item's sprite (a corpse: its creature's graphics). Not started; B7 parked for the user's call.
- **E40 redone (user: "why not corpses? live animals render"), plugin e13c67b.** New `probe X Y` records every non-zero
  layer DF printed at one map tile per viewport level, on the render thread. Osprey corpse 0,614,108: camera z108 ->
  level 0 `item=100747`; camera z109/110/111 -> every layer empty at every level 1-8 (corpse level included). DF prints
  nothing below view-level water, and swimmers render only because the plugin draws them itself from the unit list. The
  osprey's `creature_texture_texpos[0][CORPSE][0][0]` = 100747, the very value DF prints. Fix: ANY_CORPSE items in water
  (not in inventory, k 1..depth) join the creature marks with their creature's CORPSE sprite (DEFAULT if none), drawn and
  tinted like swimmers; at the first water level DF's item copy is blanked. Same corpse, same camera: visible and
  progressively tinted at z109, z110, z111 (b7/corpse-grid.png). Non-corpse items (stones, wood items) still not drawn.

### E41. B8: stones, logs, driftwood and bed art under water (user 5 Oct, ~7.40 PM: "do this now")
- **Measured first (probe).** DF prints only its water sheet over a submerged tile even at its own level (driftwood 330,678 and
  terrain boulder 356,672: `background=2566 liquid_flag=60`, no floor or overlay sprite), and nothing at all below view-level
  water. So terrain under water never showed, in vanilla or with the plugin (the plugin's bed was a generic family floor).
  The Learnedchanneled sea floor sample (330-380 x 670-720, z108): 2,358 pebble tiles, 135 driftwood, 2 boulders, 106 stone
  floors; only 1 loose item in water on the whole map.
- **Terrain (plugin c428733).** Driftwood (DRIFTWOOD 0,0) and terrain boulders (TERRAIN_BOULDERS, 8 variants by position) in
  the bed's second background; pebble beds use the full pebble floors FLOOR_PEBBLES 0-3 (cols 4-11 are edge pieces and drew a
  maze of lines); stone floors, boulders and driftwood on an open bed sit on pebbles (sand drew light squares).
- **Items.** Every item in the water, per map block in reach: corpses by CORPSE graphic; boulders, logs, rough gems, bars by
  their material's item sprite (granite boulder 183527); logs whose material has none (oak `wood_texpos` 0) use ITEM_WOOD
  (ITEM_CONSTRUCTION 0,2), boulders ITEM_BOULDER (BOULDERS 0,1). Test: 2 granite boulders + 2 oak logs placed at 336-340,682,108
  (createItem + moveToGround): 4 of 4 drawn from z110 and z109, matching DF's own drawing at z108 (b8/v2.png). An early "0
  collected" read was my error: the status was read before the camera move had reached DF.
- **Bed-art test grid (`decor`).** 27 sprites the user named (rope reed, papyrus, crops row 11, pool sprout; grass_other row 2;
  4 coral candidates; cavern grass last 3 cols x 3 rows; branch, driftwood, terrain boulder, 2 item boulders) on 330-348 x
  688-696, z108: all draw at their own level and under 1-2 levels of water (b8/grid.png); the depth tint fades them strongly
  (dark teal cavern grass nearly vanishes) -- a tuning call for the user. Decor is test-only, not saved with the game.

### E42. B8: pebbles off the sea floor, onto murky pool beds (user 5 Oct, ~8.20 PM)
- User: "I'm not convinced that I like the new seabed ... NOT do this for ocean floor tiles. Revert to the sand option. For
  'murky pools' do it."
- **Plugin 4a85b7a.** The sea floor and every other bed draw their family floor again (sand on the sea floor). Driftwood and
  terrain boulders are still drawn over it. A bed under stagnant water (`water_stagnant`) takes a full pebble floor: DF's
  variant where the tile really is pebbles, else one of FLOOR_PEBBLES 0-3 by position.
- **Measured:** DF's murky pool beds on Learnedchanneled are POOL floors (2,135) and POOL ramps (7,745), never pebbles. A rule
  of "pebbles where DF has pebbles" would therefore have changed nothing on screen.
- **Check** (b8b/): the sea floor at 315,665 from z110 is sand again, with driftwood kept (sea-ab.png). Pool 200,36,114, from
  z116, z115 and its own level: the 9 flat bed cells draw pebbles, and the 28 ramp cells keep the sand ramp sprite, so the
  pebbles sit in a sand rim (pool-abc.png). Whether ramps should change too is for the user to decide.

### E43. B8: murky pool beds are mud (user 5 Oct, ~8.30 PM)
- User, after seeing E42's pebble patch inside a sand rim: "Make all murky pool bottoms and ramps be drawn as muddy, not pebbles."
- **Plugin 5d96145.** A bed under stagnant water takes the mud family, the same one river beds use: the recoloured DIRT_FLOOR_5
  floor, SOIL_RAMPS ramps and the mud tint (#145a6e, alpha 50). The pebble floors are gone from pools. The FLOOR_PEBBLES
  lookups stay, for the brook (W7).
- **Check** (b8b/mud-abc.png): pool 200,36,114 from z116, z115 and its own level. All 37 bed cells draw mud: 9 floors and 28 ramps.

### E44. B9: ramps at their own level looked dry (user 5 Oct, 8.42 PM screenshots)
- User: the ramps "don't appear as if they are below water when at their same z-level". This held for sand ramps under the sea
  and for mud ramps in a murky pool. Ramps should take "about 50-75% of the tint that their adjacent bottom tiles are tinted".
- **Probe** (pool ramp 198,35 and floor 200,36, z114, view level): DF prints the same two layers on both cells, its dark fill
  (2566) and liquid_flag 60. The plugin swaps the floor into background and the ramp into background_two. On screen the floor
  is tinted and the ramp is not, so DF paints its water sheet after background and before background_two.
- **Fit** (the user's two screenshots, 32 px per tile, against the raw sprites): sand 205,171,104 shows as 68,91,76, and the
  plugin's mud 178,136,88 shows as 60,85,76. Both fit screen = (1-a)*raw + a*C with a = 0.79 and C = 30,71,71 (prediction
  within 2 points). Screen ramps sit near their raw colour.
- **Plugin 7dcb73c.** Each ramp sprite (all three ramp pages, every mask) gets a wet copy with C baked in at alpha 128/255, about
  63% of the floor's tint. The copies are made once per process, as the mud tile is (map load only flags start_pending). The
  wet copy is used only for a bed at the view level; deeper levels keep the compose tint as before.
- **Check** (b8b/): pool 200,36,114 at its own level, before and after (wet-pool-ab.png); sea shore ramps at 400,679,108
  (wet-sea.png). The ramps now read as submerged and stay lighter than the floor beside them. Still open: driftwood and
  boulders at the view level use the same layer, so they are untinted at their own level too.

### E45. B9: every sprite in view-level water drawn wet (user 5 Oct, ~9 PM)
- User: "yes, do the same for driftwood, boulders and any other sprites underwater".
- **Plugin 0e5a39e.** In each cell whose view level holds water (plan top == 0), the plugin swaps the sprites in background_two
  (driftwood, terrain boulders, decor), the item layer, the vermin layer and the creature layers (screentexpos, left, right,
  upleft, up, upright) for wet copies. It does this in full passes and in lone redraws. The copies use the ramps' recipe:
  30,71,71 at 128/255. The render thread queues the sprites it has no copy for. The core thread makes up to 64 per update in
  onupdate (Textures::createTile, the same thread as the mud and ramp tiles) and publishes a new table. A sprite that cannot
  be copied maps to itself. The table is cleared on world or map unload and reseeded with the ramps at start.
- **Check** (b8b/): the sea-floor test spot at z108 (wetall): terrain driftwood and boulders, the placed granite boulders and
  oak logs, and all 27 decor sprites now read under water. Sponges and driftwood at 474,745,z110 (sponge-ab: previous build
  vs this one): both were dry before, both wet now. Status after a few views: table 328, made 44, waiting 0.
- **Cost:** none measurable. Zoomed out to 120x68 (the user's zoom), the plugin's per-frame viewport time was 9.99 / 9.69 /
  9.99 ms (new / old / new), with gfps 44 in all three. The rise from 1.2 ms earlier is the zoom (4x the cells), not this change.
- **Seen, not caused by this:** one bright teal tile near 464,746,z110 (RampTop with the bed one level down). It is identical
  in the previous build. Not chased; noted for the user.

### E46. B10: no driftwood on the sea floor (user 5 Oct, ~9.05 PM)
- User: "I actually don't love the driftwood. Can you hide underwater driftwood in ocean water?"
- **Plugin b3a6783.** plan_column drops the DRIFTWOOD deco when the column's body is the sea (salt water). The bed's family floor
  (sand) shows instead. Lakes, rivers, pools and caverns keep their driftwood, and logs (items) are not touched. DF itself prints
  no driftwood under water (E41), so nothing else draws it.
- **Check** (b8b/nodrift.png, Learnedchanneled 295,665): z108 before and after, and z110 after. All 135-odd driftwood tiles are
  gone. The terrain boulders, the placed granite boulders and oak logs, and the decor grid remain.

### E47. B11: body parts in water drew on top of it (user 5 Oct, 9.23-9.24 PM, Granitephanton)
- Ducim Okilolin's foot and hands and Rakust's lower leg (CORPSEPIECE, DWARF) lie at 88-93,67-70,z113 in 7/7 water. From z114
  they showed bright on the water. The probe at level 1 (z113) printed item=129145 (BODYPARTS 2,21) over liquid_flag 60.
- **Cause:** a creature drawn from layers (dwarf) has no CORPSE or DEFAULT creature_texture, so item_sprite returned 0. The parts
  were never collected (creatures_in_water=2 of 6), and the B3 blanking never touched DF's copy.
- **Plugin 7cd9f97:** a CORPSEPIECE with no creature texture falls back to BODYPARTS 2,21. Every item in water is collected now. One
  with no sprite learns DF's printed item sprite at the column's first water level (seen_item, keyed by tile, render thread),
  is blanked there, and is drawn tinted. Check (falls/parts-ab.png): creatures_in_water=6, drawn_below=6, parts under water from
  z114.

### E48. B4: deep water read lighter than shallow (user 9.29 PM; cavern lake z95-97)
- Measured at z96: a deep cell (bed z95) read 18,91,106 (L71), a shallow cell (bed z96) 28,73,82 (L60). With the stone tint
  set to 0, both read 43,90,100, so DF's sheet treats them alike. The tint did the rest. Deep columns were tinted for 2 levels
  in the underlay, under DF's sheet, toward #00708e, which is brighter than DF's water. The shallow cell got one level on the
  glow layer over main, which darkens (the glow target holds premultiplied colour: out = rgb*a^2 + dst*(1-a), checked
  against 28,72,82).
- **Plugin 7cd9f97:** columns whose view level holds water are no longer tinted in the underlay. On the glow layer they get the
  one-level tint the shallows get, plus black at 1-(1-d)^k for the k levels the bed lies below (d = depthdark, 46/255). A cavern
  lake seen through air gets the same darkening for the levels below its first water level. Surface water seen through air is
  unchanged.
- **Measured:** z96 deep L52, shallow L60. z95 own-level bed L60. z97 deep (k2) L55-58, shallow (k1) L70-73. Before: z97 deep
  L67-71, shallow L70-73. Images: falls/cave-ab.png, falls/cave-z97-ab.png.

### E49. Falls: tags for a swift-current lip and a frothy base (user questions, 9.20-9.28 PM)
- **Lip (z137 river, view z138):** depth along y67 from x95 to x106 reads 1,3,5,4,4,6,7,7... and keeps changing.
  temp_flow_timer is 6-7 on x95-102 and 0 upstream. perm_flow_dir is 4/5 (no special value). DF sets each tile's sheet by
  depth (liquid_flag 60 = 7/7, 52 = 6/7, 36 = 3/7), hence the stepped light and dark blocks. The lip tile itself (x95) is open
  space with DF's high_flow sprite. Candidate tag: temp_flow_timer > 0, or (steadier) distance upstream to a tile whose
  downstream neighbour drops.
- **Base (z113-114):** the landing tiles are z113 x95 y67-70, under water falling from z114. DF keeps Mist flows over x92-96,
  y67-71 (412 mist flows near the falls). Candidate tag: water under falling water, plus under mist, fading with distance.
- Art for both is the user's pick (checklist W9, W10). Nothing is drawn yet.

### E50. W9/W10: falls lip streaks and froth (user 6 Oct: "lip-streaks and froth-spray. build into the plugin")
- **Tags (core thread, about 1 s, the view plus 8 cells, view level down through the shown depth):** a falling tile is open
  space holding water, with water below and at most 2 wet neighbours. DF's column is patchy, with gaps at z131-135, and a first
  build found false tops and landings in mid-air there. Rules now: a top has no falling water above it and is fed by water
  with a floor beside it, at its level or one above. A landing tile lies over a pool: a floor, or open water with 5 or more wet
  neighbours. A landing is never a top. The pool beside the column's last tile had made a false lip at the base.
  Granitephanton: 2 tops, 26 lip tiles, 0 landings in the z138 view. 0 tops, 2 landings, 11 froth tiles at z113-114.
  0.5-1.2 ms per build.
- **Lip:** this was the first fix to try. DF draws draining water by depth: liquid_flag 60/52/44/36 for depth 7/6/5/3. Swapping
  the flag to 60 ran (the counter climbed) but changed nothing on screen, because DF picks its depth sprite from the map.
  Instead, after DF's main level, the plugin lays DF's water colour (30,71,71) at 13% per missing level (capped at 70%), then
  draws 7 dashes per tile racing toward the drop: speed and length grow with the lip strength, and strength scales with tile
  size. At 16 px, 1 px dashes washed the lip white (L115). **Measured (z138, 16 px tiles):** lip L104 under DF alone, L115
  with the first build, L88 now; the river upstream is L81.
- **Froth:** a tileable foam texture (value noise, grid 4, the sampler's thresholds) at three strengths (landing 255, ring
  140, outer 64), drifting 8 px/s. DF's own mist over the falls is the mist half of froth-spray. Faint from z114 (under a level
  of water); clear at z113.
- 'aquarium-plugin falls on|off'; the status line counts tops, landings, tagged and drawn tiles. Images: falls/lip4-ab.png,
  falls/froth3-ab.png.
- **Slip, recovered:** during the A/B I ran 'streaks off' on the user's game. I restored it to 70 straight away (status
  confirms 'streaks 70').

### E51. W9: the lip blinked between the streaks and DF's tiles (user 6 Oct, 8.48 AM screenshots)
- 8.48.32 shows the lip as plain stepped DF water; 8.48.35 shows the streaks. The game was running.
- **Cause:** DF's falling water is patchy from tick to tick. E50 had already seen gaps make false tops mid-column. The tagger
  runs once a second, and in any pass the column's top tile (or the lip water) can be empty. Then every lip tag drops until a
  later pass finds them again.
- **Plugin ce74033:** tags are held for 8 s after they were last seen; seeing them again refreshes them. They are forgotten on map
  unload and on 'falls off'.
- **Not verified live yet:** by the time this was built, the user had left the fort (DF at the title screen, region17, no
  map). The build was swapped in at the title, where it is safe (no map, no texture race), and reports depth off, wanted yes.
  The check is to watch the lip for 20 s with the game running, once a fort is loaded.

### E52. W9: no streaks at the lip's own level; E51 confirmed live (user 6 Oct, 9.58 AM)
- User at z137, the river's own level with the camera in the water: "The flow effect is not needed on the underwater z-level
  view of the top of the falls."
- **Plugin ba26104:** the dashes are drawn only where the camera looks down onto the water (plan top >= 1). The even-sheet tone
  correction stays at every level.
- **E51 checked live** (Granitephanton, view centred on the lip at the user's zoom, 40x23 tiles, game running 20 s): the lip
  was drawn on 24-25 tiles in every second, while the tagged set moved between 25 and 32 tiles. At z137: 28 tagged, 0 drawn
  (falls/lip-final.png).
- **My error on the way:** the first 20 s run used the camera spot from the 16 px zoom (32,29). At the user's new zoom (40x23)
  that view held only sky, and the run read 0. Centre on the target from the live viewport size.

### E53. B4 follow-up: trees in the cavern lake; stray foam (user 6 Oct, 10.09-10.10 AM screenshots)
- **Pale squares round trunks (z96):** 146 BRANCH and 109 TWIG tiles at z96 hold 7/7 water over more water at z95. plan_column
  took them for the bed at the view level, so they got the shallow look, while the deep water round them darkened. Now
  BRANCH, TWIG and TRUNK_BRANCH tiles holding water continue the column like open water.
- **Bright squares behind trunks (z97):** trunk cells (TreeTrunkPillar at z97, TreeTrunkEW at z96, water at z95) were
  unplanned, because solid wood ended the column, so DF drew the water under them untinted. A column now passes through TREE
  or MUSHROOM material. Water under wood starts at the wood's level (the lake's surface): top = the wood, plan_cell.wood = 1.
  At that level DF prints liquid_flag 0x200200 ("trunk in water"), which draws pale. The plain sheet (water_value) is swapped
  in, in full passes and lone redraws, and the trunk cell takes one more depthdark level. **Measured** (trunk-cell corner vs
  open water, 15,75,88): before 33,113,131; planned 9,93,108 to 20,121,141; plain sheet 11,88,103; plus one level 10,80,94.
  A faint dark trace remains on the top and bottom pillar cells.
- **Canopy (z97):** the cavern darkening seen from above (E48) was drawn over main, so making canopy cells deeper would also
  have darkened the leaves. It now runs right after DF draws level 1 (before the view level), and for lone level-1 redraws.
  A canopy cell over plain water now reads like the water beside it (21,77,86 vs 15,74,87; was 33,92,102).
- **Stray foam (z95, z96):** 28 tiles of still 7/7 water in narrow cavern inlets passed the falling test (open space, water
  below, at most 2 wet neighbours) on one level only. The result was 26 false landings, 49 froth tiles, and foam along the
  walls. A falling tile now needs another falling tile within 3 levels in its column. The cavern now has 0 landings at
  z95-97, and the real falls are unchanged.
- Images: falls/trunk4.png, falls/tree-ab-z9{5,6,7}.png.

### E54. B12: the wrong water shade behind branches over water, from higher levels (user 6 Oct, 10.44-10.46 AM)
- Sequences: cavern trees from z97 to z99, and surface trees over the river below the falls from z114 to z121. Each level up
  showed squares of the wrong shade behind the branches.
- **Probe** (from z98): canopy cell 20,86 had plan top=1, bed=2; the open cell 24,86 beside it had top=2, bed=2. The canopy
  twig at z97 is dry, and the water starts at z96. **Cause: my E53 rule.** Any TREE or MUSHROOM tile above the water was taken
  for the lake's surface, so a canopy moved its column's top up by a level.
- **Plugin 8ecf478:**
  - Only a trunk tile (not a BRANCH, TWIG or TRUNK_BRANCH) resting directly on the first water tile sets top to its own level.
  - cave_dark is drawn right after DF's level holding each column's top water, in full passes and lone redraws. Drawn after
    level 1, it had darkened a canopy two levels down from z98.
  - water_value is learned as the commonest liquid_flag at the top level, with trunk cells left out. It had learned the
    trunk's 0x200200, which the E53 trunk swap then pasted. Status now shows water_value=0x3c.
- **Check** (trees/): the cavern from z97, z98 and z99, and the river from z115, z117 and z119, before and after. The dark
  squares under canopies are gone in the cavern (z98, z99) and over the river (z119). Canopies seen from above take DF's own
  haze like everything below the view.
