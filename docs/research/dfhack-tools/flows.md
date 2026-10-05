# flows (DFHack 53.16-r2)

- Docs: https://docs.dfhack.org/en/stable/docs/tools/flows.html (read 5 Oct 2026)
- r2 doc: `docs/plugins/flows.rst`. Its text matches the stable web page: a summary, the magma-sea/HFS sentence and bare usage. No difference found.
- Source: `plugins/flows.cpp` (70 lines, C++ plugin `flows`, built at `plugins/CMakeLists.txt:89`). Test: `test/plugins/flows.lua`.
- Tags: fort, inspection, map.

## What it does

The command is `flows`, with no options. The source never reads `parameters`, so any argument is silently ignored and nothing is undocumented. It prints five counts:

```
Counting flows and liquids ...
Blocks with liquid_1=true: N     <- map_block.flags.update_liquid
Blocks with liquid_2=true: N     <- map_block.flags.update_liquid_twice
Blocks with both:          N
Water tiles:               N     <- tiles with flow_size>0 and liquid_type==Water
Magma tiles:               N     <- tiles with flow_size>0 and liquid_type==Magma
```

**The name is misleading.** Despite the name and the doc's "flowing liquids", the tool never touches DF *flows* (`df::flow_info`: mist, smoke, miasma, OceanWave, SeaFoam and the rest). It reads two things, liquid-update flags and liquid depth.

## How it works (file:line)

| Line(s) | Read | Meaning (df-structures) |
|---|---|---|
| `flows.cpp:26-28` | `world->map.map_blocks` | every allocated block: all z-levels, hidden or not |
| `:29-34` | `block->flags.bits.update_liquid` / `update_liquid_twice` | `df.block.xml:5-6`: bay12 `FLOW_ADJUST` / `FLOW_MAINTAIN_ADJUST` ("Protects UpdateLiquid from being cleared the first time"). These mark the block as scheduled for DF's liquid-settling pass. |
| `:35-46` | `block->designation[x][y].bits.flow_size`, `.liquid_type` | depth 1-7 and `tile_liquid::Water`/`Magma`. Tiles with `flow_size == 0` are skipped. |

There are no hooks, timers or state. It runs once on the calling thread under Core suspend and returns `CR_OK`. It writes nothing, so it has no side effects and needs no persistence. The test only checks that the output strings are present.

## Gotchas

- **The labels are not the field names.** "liquid_1" is `update_liquid` and "liquid_2" is `update_liquid_twice`. A nonzero "liquid_1" count means DF still has liquid to settle in those blocks, so liquid is moving or unsettled. It does not mean "blocks containing liquid".
- **It does not reveal anything** (the doc's HFS point). It also does not check visibility, so the counts include hidden caverns, the magma sea and HFS. It cannot tell you *where* the liquid is. You get global counts only, with no z-level breakdown.
- **Water is not split by type.** Salt, stagnant and fresh water all count as Water. Frozen water does not count: ice is a tiletype with `flow_size` 0.
- **Cost.** Every tile of every block is visited in C++. That is 256 × blocks: about 22M designation reads on an 8×8 embark with roughly 86k blocks. This is cheap for a single call (not timed here) but it is a map-wide walk. Under our *no polling the user game* rule, use it as a one-shot only, never in a loop over RPC.
- **Nothing in the source verifies that rivers, oceans or aquifer blocks keep `update_liquid` set permanently.** If they do, "liquid_1" on a river or ocean fort would never reach 0 and would not mean "a leak". Measure on region9 before relying on it.

## Relevance to our work

- **Aquarium wave/mist scan: different data, so neither replaces the other.** `aquarium.cpp:1019-1031` walks `b->flows` (the per-block `stl-vector<flow_info*>`, `df.block.xml:247`) for `OceanWave`/`SeaFoam` with `density > 0` in the visible blocks. `flows` never looks at `block.flows`, `df.global.flows` (`df.game_v.xml:14`) or `world.orphaned_flows` (`df.world.xml:721`), so it cannot count our wave or mist flows. A real flow census needs about ten lines of Lua over `df.global.flows` grouped by `flow_info.type` (`df.flow.xml:26-36`: type, mat, density, pos, dest, expanding, flags DEAD/FAST/CREEPING, guide_id). Add it to the rig, not the user's game.
- **Possible use as a "water has settled" probe.** After the aquarium's raws-first edits (sand baked in standing water, mud river beds) or a dig-now breach, a falling `update_liquid` count shows DF has stopped re-flowing liquid. The rig could call it before and after. It is cheap and read-only. First establish its baseline on a river or ocean fort (see the last gotcha).
- **Tile counts as a sanity check.** The Water/Magma totals give a whole-map check for our `scan_water` water-body classification (2.7 ms native). The sum of our classified bodies should be no more than `Water tiles` and close to it.
- **A model to copy.** Our scanners can use the same pattern: plain C++ loops over `map_blocks` × 16 × 16 for map-wide counts, never Lua per tile. That is the 170 s trap in df-region-draw-tiles.
