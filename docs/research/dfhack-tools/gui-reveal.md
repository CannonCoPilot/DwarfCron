# gui/reveal (DFHack 53.16-r2)

- Docs: https://docs.dfhack.org/en/stable/docs/tools/gui/reveal.html (read 5 Oct 2026)
- r2 doc: `scripts/docs/gui/reveal.rst`. It matches the web page: event-trigger areas are kept hidden, the graphics-mode note, `hell`, and `-o/--aquifers-only`. No difference found.
- Source:
  - `scripts/gui/reveal.lua` (141 lines, the UI)
  - the C++ plugin `plugins/reveal.cpp` (543 lines), which does the actual work through the commands `reveal`/`unreveal`
  - `plugins/lua/reveal.lua` (an empty module; the native `unhideFlood` is exported at `reveal.cpp:540-543`)
  - aquifer markers come from `plugins/dig.cpp:2160+` (`paintScreenWarmDamp`)
  - plugin doc: `docs/plugins/reveal.rst`
- Tags: adventure, fort, armok, map.

## Commands and options

```
gui/reveal [hell] [-o|--aquifers-only] [-h|--help]
```

The argument parsing is at `reveal.lua:128-139`. `help` given as a positional also prints help. `hell` is matched only as the *first* positional.

The plugin's underlying commands, from `reveal.rst` and `reveal.cpp:101-122`:

- **`reveal [hell|demon]`**:
  - **`demon` is disabled** in this build: "currently disabled to prevent a hang due to a bug in the base game", and it returns `CR_FAILURE` (`:236-240`). The plugin doc still describes it as working. **This is an undocumented difference.**
  - `help`/`?` returns `CR_WRONG_USAGE` (`:242-243`).
- **`unreveal`**, **`revtoggle`**, **`revforget`**:
  - The plugin doc spells `revtoggle`'s summary "betwen" (`:112`), a typo only.
- **`revflood`**: hides the whole map, then flood-reveals from the keyboard cursor, else the selected unit, else the *first* citizen in `units.active` (`:487-499`). Fort mode only.

## How it works (file:line)

**The UI** (`gui/reveal.lua`):

- `RevealScreen:init` (`:104-115`): unless aquifers-only, it sets `force_pause=true` and runs `reveal` or `reveal hell`.
- `onDismiss` (`:117-122`) runs `unreveal` if the "Restore map on close" toggle (`CUSTOM_SHIFT_R`, default Yes) is on.
  - **With `hell` the toggle is disabled but stays Yes**, so closing always unreveals.
  - **In adventure mode the toggle is hidden but still Yes**, so closing unreveals there too.
- `Reveal:onRenderFrame` (`:83-91`) calls `dig.paintScreenWarmDamp(true, true)` **every frame**, even in full-reveal mode, so aquifer and damp markers always show.

**The plugin, fort reveal** (`do_reveal_fort`, `reveal.cpp:211-227`):

- For every block in `world->map.map_blocks` that passes `isSafe`, it snapshots `designation[x][y].bits.hidden` into an in-memory `hidesaved` vector, sets `hidden = 0`, and sets `game->minimap.update`/`mustmake = 1` (`:89-92`).
- `isSafe(block)` (`:62-87`) skips:
  - (a) blocks containing any tile of `world->event.encased_horrors`, `deep_vein_hollows` or `divine_treasures` (`initialize_trigger_cache`, `:158-165`, keyed by block x/y and tile z);
  - (b) blocks whose *local* feature is `deep_special_tube` (adamantine) or `deep_surface_portal`;
  - (c) blocks whose *global* feature is `underworld_from_layer` (HFS). Feature data comes from `Maps::ReadFeatures`.
- The granularity is the **block**: a whole 16×16 block stays hidden if one trigger tile is in it.

**State** (`revealstate`, `:41-48`):

- Plain `reveal` gives `SAFE_REVEALED`, and `is_active` stays false.
- `reveal hell` gives `REVEALED` with `is_active = true`. From then on **`plugin_onupdate` calls `World::SetPauseState(true)` every frame in fort mode** (`:125-135`) until `unreveal`.
- **Adventure mode:** with `is_active`, every new frame re-reveals the adventurer's 27-tile vision box and sets `pile = 1` ("lit") (`:193-209`).

**`unreveal`** (`:300-344`): in fort mode it writes each snapshot back as-is, then calls `reset_state()`. The snapshot is cleared on `SC_WORLD_UNLOADED` (`:142-146`).

## Side effects, persistence, gotchas

- **`hidden` is save data, but the snapshot is not.**
  - If a fort is saved while revealed, or the world unloads, the restore information is gone. Only `revflood` can approximate the hidden state again: it floods from one point and treats constructed walls as transparent, per bug 1871.
  - **Never let the rig save or quit while revealed**, unless the save is meant to stay revealed.
- **`unreveal` restores the snapshot blindly.** Tiles that became genuinely visible while revealed (dug, breached, flooded) are hidden again. `reveal.rst` says it reverts correctly only "if run immediately afterwards".
- **The pause behaviour has three levels:**
  - The `gui/reveal` window force-pauses while open (ZScreen).
  - `reveal hell` force-pauses **every frame** with no window at all, so a headless `cx-lifecycle step` would stall until `unreveal`.
  - Plain `reveal` does not pause.
- **A plain reveal can still trigger events.** `reveal.rst` caveats that a secret hollow already breached into a cavern fires when that tile is unhidden.
- **`reveal help` returns `CR_WRONG_USAGE`.** Our render-pipeline memory records that `CR_WRONG_USAGE` hangs RPC. Never send `help`/`?` to reveal-family commands over the rig.
- **Bug: the graphics note always shows.** `reveal.lua:54` tests `dfhack.screen.inGraphicsMode` *without calling it*, so the function value is always truthy and the "solid tiles not rendered in graphics" note appears in ASCII too. It is cosmetic.
- **Graphics mode does not draw buried tiles.** Solid tiles not adjacent to open space are not drawn, so "revealed" screenshots show less than the data does.
- **Cost:** reveal and unreveal each walk 256 × blocks in C++ and keep a 260-byte snapshot per block (about 22 MB on an 86k-block map).
- **Aquifers-only** (`-o`) changes no tiles. It only paints markers (`dig.cpp:2191-2215`), including on hidden tiles.

## Relevance to our work

- **Revealed is not discovered (this matches our measurement).**
  - The plugin only clears `designation.hidden`. It never touches feature or cavern discovery state.
  - fort-load-levers recorded that BOATS had every tile unhidden and about 70 cavern units while no cave feature was `Discovered`. The source agrees: reveal does not open cavern wildlife, a cavern breach or the cavern gate.
  - **Use the dig-now breach for "caverns open".** Reveal is display only.
- **Hell/cavern caveats for tests:**
  - `hell` reveals HFS and spires and pins the game paused, so it is useless for anything that steps ticks.
  - Plain `reveal` leaves trigger blocks, adamantine tubes and HFS hidden, so a cavern scan done "after reveal" still misses those blocks. Our scanners read memory directly and ignore `hidden` anyway.
- **It interacts with `force Wildlife` and `fix/wildlife`.** Reveal makes cavern units visible (`Units::isHidden` → `!isTileVisible`), so a plain `force Wildlife` would then release cavern groups as well as surface ones. It also changes fix/wildlife's "known vs hidden creature" reporting. **Unreveal before running wildlife release steps,** or always pass `all` so the arm does not depend on reveal state.
- **Aquarium:**
  - The aquarium "skips hidden" cells. Under reveal, every cavern lake, the magma sea and underground river becomes a candidate, so expect a frame-cost jump. A pass/fail look test must record reveal state.
  - `gui/reveal` also paints `paintScreenWarmDamp` markers each frame through `bump_layers` over map cells. That is another per-frame overlay over the same viewport the aquarium's texture swaps and `update_viewport_tile` hook manage. If a look run shows stray tiles while `gui/reveal` is open, suspect this before the aquarium.
- **What to reuse in the rig:**
  - Call the plugin commands directly: `reveal` → screenshot or scan → `unreveal` in the same step, with no save in between.
  - `plugins.reveal.unhideFlood(pos)` (Lua) is a targeted way to make one cave system visible for a screenshot without a global reveal. It is still not a breach.
