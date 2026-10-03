# Aquarium: critical review after the user's play test (3 Oct 2026)

The user played Learnedchanneled (AQUA_SHORE16, ocean) and Shortsling (AQUA_LAKE, river + lake) on rc 4dfe9b7 and sent
29 screenshots (projects/urist/alpha_seasonalwildlife/screenshots/, 2 Oct 09:21 to 3 Oct 12:12). I had reported
"v1 passes on the rig" an hour earlier. The game says otherwise. This file lists each defect, its root cause, and the
process failure behind it.

## Defects and root causes

| # | What the user saw | Root cause (evidence) | My decision that caused it |
|---|---|---|---|
| 1 | Ocean surface looks like tan dry ground (11.32.29, 11.34.43, Learnedchanneled z-1) | The mod bakes DF's sand floor UNDER each UNDERWATER_1..7 tile and makes it opaque. Seen whole-screen, the alpha-150 water over sand reads as sand. | Judged the bake from a single-cell composite (the prototype strip), then from 40x23 shots where I looked for clipping, not for "does this read as water". |
| 2 | No translucent water surface at all | Same: the baked tile is opaque. The lift then copies the liquid flag up, so DF draws that opaque tile at the view level too. | Bake + lift. |
| 3 | Ocean edges should show as slopes | The ramps under water edges are DF sprites in `screentexpos_background_two`. I CLEARED that layer (4c60181, 4dfe9b7) to remove "pale squares", which were those slope sprites. | Treated slope art as a defect. |
| 4 | 16-24 FPS on the ocean (11.34.43: FPS 24, vs 152 the frame before) | Five overlay layers (bed/lift, flow, waves, veil, lens) each loop over the visible cells every frame in Lua. At the user's zoom (about 120x68 = 8,160 cells) that is tens of thousands of userdata accesses a frame. | I measured each layer's paint ms in a 40x23 view and never measured DF's FPS at the user's zoom. |
| 5 | Underwater view: good bed, no translucent hue | At the water's own level DF draws the baked opaque tile: a flat green with sand ripples, no depth. | Bake. |
| 6 | "Bubble" effect frantic | Animated overlays (shimmer/spray) with short frame times. To unload. | Built v3 animation before v1 was right. |
| 7 | Water boundaries don't match the minimap (11.40.43 at z-4: water drawn where the minimap shows none) | The lift copies water up from up to 8 levels down with NO fog, so open space over deep water draws as full water at the view level. | The lift throws away DF's own per-level fog. |
| 8 | Multi-level slopes under water not visible | Same as 3 and 7. | Lift + bg2 clearing. |
| 9 | Fish look on top of the water | DF draws creatures above the liquid layer; nothing tints them. | Not built. |
| 10 | Shimmer good on the lake, should be lake only; rivers need flow-directional motion | Shimmer is not tied to body type; river streak direction was never checked against DF's flow. | Not checked. |
| 11 | Shimmer disappears after a while | Most likely a fuse or the 10-frame liquid-flag self-check switching the layer off. To confirm. | Fuses that switch a layer off silently. |
| 12 | Cavern water surface looks like dirt floor | Cavern pools share UNDERWATER_1..7, so they show the same opaque bake. | Bake. |
| 13 | Predator-prey link overlay offset by several cells (2 Oct 09:21-09:40) | GroupsOverlay painted map-relative coordinates on the INTERFACE text grid (paintString without `map=true`, guidm.Viewport sized by the panel layout). In graphics mode the map tiles are a different grid. Links also refreshed once a second. | Fixed 6f64917 (map-tile painting, 250 ms refresh). |

## What went wrong in the process

1. **Over-design.** The aquarium grew to 4,285 lines and 151 functions, with slicing, fuses, degrade ladders, texture
   caches and 15 cache-key bumps in 36 hours. Most of that machinery patches the cost of a per-frame, per-cell design
   that was wrong from the start. The fix is a different architecture, not more patches.
2. **Self-graded validation.** "v1 passes" rested on my own captures at two hand-picked views, 40 cells wide, after
   fixing whatever showed in exactly those views. Not checked: DF FPS, the user's zoom, the minimap, multi-level
   views, caverns, slopes, a long run, or whether a full screen reads as water.
3. **The harness tested my model of DF, not DF.** 413 offline checks passed while the game looked wrong. Twice the model
   itself was wrong (pixel byte order; what the liquid flag makes DF draw).
4. **Patch-the-symptom fixes.** "Pale squares" -> clear background_two removed the slopes the user wants.

## Rules for the redesign

- No per-frame Lua work proportional to visible cells. Per frame: O(visible underwater creatures) at most.
- Prefer raws-level and one-time texture/texpos changes; anything the script does must not depend on the view staying put.
- Keep DF's own draw: fog per level, slopes, ramps, creatures. Add, never replace.
- Ocean (sand), river/lake/pool/cavern (mud): translucent water surface, bed visible beneath, depth by DF's fog.
- Validate against the user's screens: the user's zoom, DF FPS on (a) aquarium off, (b) each piece on, the minimap, a
  multi-level slope view, a cavern pool, a 5-minute unpaused run; compare side by side with the user's screenshots.
