# Water checklist, autonomous run of 6-7 Oct: decisions for the user's review

Each entry: what was wrong, what changed, the judgement calls I made on my own, the evidence, and what to look at.

## B16 Pan cost (held 's')
- Changed: wrapped layers (no slide), bed tile sheet, one draw call per pass, heal pass removed, empty layers skipped (plugin 88e93e8, log E65).
- Result: plugin time over a 6 s held-'s' window -20% above the lake, -10% at the surface; still frames 34-52 -> 22-27 us; the 5-12 ms hitch after every pan is gone (worst still frame 0.12 ms). A camera move costs DF ~7 ms on its own; the plugin adds ~0.3-0.6 ms to it, and makes every other frame faster than DF alone (4.3 vs 5.7 ms).
- Judgement: the remaining per-move cost is mostly DF's own queued drawing that runs when the plugin first switches render target; I stopped there.
- Look at: hold 's' over any water; nothing should hitch after the camera stops.

## B14 Big swimmers
- Cause: a big creature is a 3x2 block (its tile plus left/right/up-left/up/up-right parts in the neighbouring tiles). The plugin took only the centre; DF drew the other five untinted over the water, and smooth-movement glid them while the centre waited.
- Changed: all five parts learned, hidden with the centre, drawn tinted and gliding with it (plugin af19a05, log E66).
- Evidence: B14/before-z36-parts-untinted.png, B14/after-z36-whole-body-tinted.png, B14/after-glide-frames-18-29.png (gliding as one body, sprite flipping on), B14/own-level-plugin-vs-df.png (0 px differ by more than 24).
- Judgement: a part that falls over a land tile is hidden by that tile (it is drawn under DF's view level, like the centre). No dimetrodon was on the maps I opened; the fix is generic for every big creature.
- Also fixed: the plugin's `probe` command crashed DF on any tile holding a creature (6 Oct 23:35; DF restarted, nothing saved).

## B15 Lakes filed as river
- Cause: the plugin (and the wildlife tool's water scan) took an active current as proof of a river; DF puts a current on lake water too. Shortsling's lake: 39,789 surfaces filed as river, 1,436 as lake.
- Changed: a river is DF's own river or brook tiles (at the top or the bed of the column) or falling water; nothing else. Now 39,102 lake, 2,123 river, which matches DF's river tiles (sampled). Same fix in the wildlife tool (rc 4c50356), so lake animals are no longer placed as river animals. Plugin bd7b16b, log E67.
- Evidence: B15/before-lake-filed-river.png (river streaks across the lake), B15/after-lake-shimmer.png.
- LAKE_RIVER was not affected (its lake current reads "down", which the old rule already ignored); the old classing only bit worlds like region10.

## W3 Lake surface
- Decision: kept the lake's surface as it is: two faint caustic webs drifting in different directions and trading places over ~4 s, world-anchored (seamless when scrolling), alpha 45. That is the "simple shimmer, two directions trading back and forth". With B15 a lake cell gets only this and a river cell only the river flow, so the lake never draws over the river.
- Evidence: W3/lake-meets-river-z56.png, W3/lake-meets-river.gif (Shortsling, where the river enters the lake).

## W4 River surface
- Changed: rivers get soft dashes drifting down the current, each laid along the river's local heading (a continuous angle smoothed over the channel), so a bend shows the dashes turning with it; the heading's sign is DF's own current, else the river tile's heading (RiverE etc.), else the world map's river course, so the flow runs source to mouth. Dashes never cross onto a bank or the lake. One draw call. Plugin bd7b16b, log E68.
- Judgement: my first try (short, thin, many) read as rain under Shortsling's own rain (W4/first-try-short-dashes-read-as-rain.png); the kept version is longer (~1 tile), softer, three cells in five, life 2.6 s, travel 1.7 tiles. Peak alpha follows the `streaks` setting.
- Evidence: W4/river-bend.png, W4/river-bend-zoom.png (dashes along the E-W reach and turned down the SE bend), W4/river-bend-flow.gif.
- Look at: Shortsling's river at about 262,168 z56 (the bend).

## W5 Pools
- Changed (plugin, log E69, E72): water gets a tint by its kind, not only by its bed: murky (stagnant) pools, cavern water (W6) and the sea (W2) have their own. Seen from above, DF draws its own teal water sprite over pool water; for pools that sprite is dropped and the plugin's tint (plus a "veil" strength) is the water's colour, drawn under DF's level so anything standing over the pool stays bright. Pools get the lake's shimmer at 55%, shifted green. Tunable: `aquarium-plugin tint RRGGBB ALPHA pool`, `aquarium-plugin veil pool ALPHA`.
- Judgement: first pass (veil over DF's sheet) picked an olive green-brown (W5/pool-tint-candidates-picked-middle.png); once DF's sheet was dropped that same tone read as a mud flat, so I re-picked greener (W5/pool-tint-final-candidates-picked-right.png, right: #3c6438, alpha 90, veil 70): murky green water over the brown mud bed, slopes visible. Final: P/shortsling-pools-final.png.
- B5 (shallow water): DF draws 1-3/7 water at the view level as the real floor (grass) under a bright near-opaque water sprite, so a puddle was a solid teal square. Now that sprite is dropped there and the plugin's water tint lies over the real floor (`aquarium-plugin shallow on|off`). Tested on a 59-tile test puddle made on grass in Shortsling (unsaved): W5/shallow-puddle-before-after.png.
- Evidence: W5/pool-from-above-before-after.png (Shortsling pools near 20,318).

## P1-P6, P11 Bed art (lake, river, pool, brook)
- Built (plugin, log E70): the plugin plants sprites on bare floor beds by kind of water, fixed to the map (they never move or flicker) and thinned by a cluster field so they lie in patches (~5 tiles), never where DF already put something. `aquarium-plugin bedart on|off`.
- Sprites, all DF's own (P/sprite-sheets-picked-rows.png):
  - P1 papyrus sedge (the real papyrus, PLANT_CROPS 0:33 and 6:33; not rope reed, sorghum or rice): river beds 20%, lake edges 35%.
  - P2 lake tufts: GRASS_OTHER row 2 (its four tufts) 7%. P3 lake sprigs: CAVERN_GRASS row 2 (the green row), last three columns, 5%. P4 fallen branch (ITEM_NATURE 0,0) 1%. P5 driftwood 0.3% (lakes, rivers; never the sea floor).
  - P6 pools: the small sprouts (PLANT_CROPS 7:0) 25%.
  - P11 brooks: only sprouts (wheat 7:0, papyrus 7:33) 10%.
- Judgement: plants only near the light: rivers and seas on beds at most 2 water levels down, lakes at most 3; my first densities (12% reeds, 14% sprouts) left the river and pools nearly bare because most of their beds are slopes (slopes carry their own sprite and take no art), so I raised them.
- Evidence: P/shortsling-river-and-lake-edge.png, P/shortsling-lake-bed.png, P/shortsling-pools.png, P/shortsling-river-bend.png.

## W7 Brook
- Changed (plugin a4f686a, log E71): the brook's walkable top is drawn clear (DF's opaque top sprite is blanked; the tile stays a walkable floor in the game); the bed is DF's own brook pebbles-under-water sprite; the surface gets the lake's light ripple instead of river dashes; brook sprouts (P11) grow on the bed. BROOK's 1,084 brook surfaces, all hidden under their tops before, are now drawn.
- Evidence: W7/brook-own-level-before-after.png, W7/brook-from-above-before-after.png (Smaksmo Oxdu BROOK, 54,4).

## W6 Cavern water
- Changed (plugin, log E72): cavern water gets its own tint, a flat silty olive-green (#4a5238), and no shimmer. Seen from above, DF's own translucent teal water sprite on the first water level is dropped there and the plugin's tint is the water's colour, under DF's level, so the fungus canopies standing over the lake stay bright.
- Judgement: my first version laid the colour over DF's whole level and dimmed the canopies; moved under. The same change applies to pools (W5): their colour now also comes from under DF's level.
- Evidence: W6/cavern-lake-from-above-before-after.png, W6/cavern-lake-own-level-before-after.png (AQUA_FALLS cavern lake, z96-97).

## W8 Waterfall column
- Decision: no change. DF draws the falling column as dark water with white streaming lines, which reads as falling water; the lip streaks (W9) above and the froth (W10) below are your earlier picks. The flat light-blue far below is the plunge pool 17 levels down, past the plugin's 8-level reach; DF draws it with its own far-level look. Extending the reach for open shafts is possible but costs every frame; I left it.
- Safeguard: the W5 shallow-water rule drops DF's sprite on 1-3/7 water; falling water (1-3/7 at most levels of a column) is exempt, so the falls never vanish (W8/column-three-builds-identical.png: unchanged across builds).
- Evidence: W8/falls-z138-130-122-115.png.

## W1 Ocean surface
- Changed (plugin 6c72e46, log E73): the sea no longer uses the lake's two cross-fading webs; it gets one web sliding steadily one way, toward the land of the shore edges in view (the last heading is kept when no shore is in view). Measured on Learnedchanneled's west coast: the pattern moved +34 px east, -28 px north in 3 s, toward the beach and the land to the north-east.
- Evidence: W1/sea-drifts-to-coast.gif.

## W2 Ocean wave fronts, landing foam, colour
- Reviewed running (867-1,098 DF wave fronts in the world): the crest lines and the landing swash (B6) read well; no change to them. Evidence: W2/coast-waves-running.gif, W2/coast-waves-frame.png.
- Colour: the sea now has its own tint (#0b8088) and, like pools and caverns, DF's own water sprite is dropped there so the plugin sets the colour (veil 50). Judgement: you asked for "slightly" more turquoise than river water; the subtle version (W2/sea-colour-candidates.png, left) left the coral grey, so I picked a middle setting (W2/coast-picked-colour.png): clearly turquoise, light over sandy shallows, darker with depth. If it is too much: `aquarium-plugin tint 0e7a82 80 sea` and `aquarium-plugin veil sea 0` give the subtle version.

## P7, P8, P9 Sea beds
- P7 coral: blood amaranth and red spinach (DF's PLANT_CROPS 0:17, 6:17, 0:19, 6:19), 4% of shallow sea beds, in patches. P8 sea grass: CAVERN_GRASS rows 2 and 3, last three columns (green and red sprigs), 5%. P9: plants and coral only on beds 1-2 water levels below the surface; deeper beds get none (sponges are the wildlife tool's: see C1-C3).
- Changed: the plugin's bed art is now its own layer, drawn after the water's tint with a light tint of its own, so its colours survive: the coral reads pink-red (P/sea-coral-before-after.png). Step 1 alone (light tint under DF's sheet) was not enough (P/coral-light-tint-only-step1.png).
- Evidence: P/sea-shallow-beds-coral-grass.png (before), P/sea-coral-before-after.png.

## B15 audit, all Smaksmo Oxdu saves (after the fix)
- LAKE_RIVER lake 23,295 / river 3,584; OCEAN_RIVER sea 21,752 / lake 364 / river 1,905; FALLS river 960 (its 6 "problems" are the known air gaps inside the falling column, E61); BROOK lake 710 / river 1,084 (brooks, now drawn: W7). Every surface planned from the level above, 0 wrong. These saves never had the B15 fault; region10's Shortsling did.

## P10 Boulders
- Decision: not built. DF already places its own boulders and pebbles on beds and the plugin draws them under the water (B8); you marked this one uncertain and lower than the plants, so no plugin-made boulder clusters.

## C1 Nothing preys on sponges / C2 Sponges breed
- Already built in the tool's release candidate (rc d5a98fe, 04ef25a; aquarium mod 2 gives sponges a female and a male caste): no food-web edge, written relation or lure ever takes a sponge, and the sweep clears any relation DF writes on one; on the rig a tame sponge was born and wild sponges with their own population record bred 5 of 5. They ship with the plugin package (see the codebase review), not as a separate install.
- P9 (sponges in clusters): a sponge ribbon now grows from a random earlier sponge 40% of the time and never onto a used tile, so it thickens into a clump two or three wide instead of a thin line (rc a955f91).

## C3 Brook water admits only the smaller freshwater animals
- Built (tool): a river body made of DF's brook tiles is a brook; it is offered only to animals whose adult size is at most 10,000 cm3 (otters, frogs, small fish yes; crocodiles, big fish no); `water.brook_max_mass` in the config changes the limit.
- Tested offline: the water harness (tests/water/harness.lua, host Lua, no DF) had gone stale on 4 Oct; repaired, with a brook on its map: 65 pass, 0 fail; the previous script fails the new cases (lakes became rivers under the old current rule: 6 rivers, 0 lakes). Not yet run in a live game (the rc is not installed in your DF).
