# DFHack C++ plugin build (Windows x64, DFHack 53.16-r2) and the aquarium render hook

Written 3 Oct 2026. Desk/build only: nothing here touches the running DF or its install folder.

## 0. What the rig runs (the build target)

- DFHack is the Steam "DFHack" app, not a `hack/` folder inside DF:
  `$DF_DIR/../DFHack/hack/` (`$DF_DIR` from `scripts/cx-config.sh`). DF loads it through
  `$DF_DIR/dfhooks_dfhack.ini` = `C:\Program Files (x86)\Steam\steamapps\common\DFHack\hack\dfhooks_dfhack.dll`.
- Version strings in the installed `hack/dfhack.dll` and in every stock `hack/plugins/*.plug.dll`
  (`strings -a`):
  - `53.16-r2` (DFHACK_VERSION), `53.16` (DF_VERSION)
  - `53.16-r2-0-g02e77acf` (git description = DFHACK_GIT_DESCRIPTION)
  - `https://github.com/DFHack/dfhack/actions/runs/36605190931` (DFHACK_RUN_URL)
  - stock plugins carry `D:\a\dfhack\dfhack\build\plugins\<name>\<name>.pdb`: built by the GitHub
    `windows-2022` MSVC runner (`.github/workflows/build-windows.yml`), Release, Ninja.
- The source checkout `/Users/nathanielcannon/Claude/GitRepos/dfhack-53.16-r2` is at the same commit:
  `git describe --tags --long` = `53.16-r2-0-g02e77acf1`; submodules `library/xml`, `scripts`,
  `plugins/stonesense` are at their `53.16-r2` tags, `depends/*` at the superproject's recorded commits
  (`git submodule status` shows no `+`/`-`).

### How the loader checks a plugin (why "same commit" matters)

`library/PluginManager.cpp:298-330`:
- `plugin_abi_version` must equal DFHack's (`DFHACK_ABI_VERSION 2`, `CMakeLists.txt:15`) or the load is refused.
- `plugin_version` must strcmp-equal `53.16-r2` or the load is refused
  ("Plugin X was not built for this version of DFHack.").
- `plugin_git_description` different from `53.16-r2-0-g02e77acf` only prints a warning.
- These values come from the static lib `dfhack-version` linked into every plugin
  (`plugins/Plugins.cmake:127`, `library/CMakeLists.txt:340-346`) via `DFHACK_PLUGIN()`
  (`library/include/PluginManager.h:301-311`), so they are baked into the plugin dll at build time.
- The version gate does not protect struct layout. Layout safety comes from compiling against the same
  `library/xml` (df-structures) commit, which `53.16-r2` pins.
- `plugins/external/*` is git-ignored (`plugins/external/.gitignore`), so adding our plugin there leaves
  `git describe` at `53.16-r2-0-g02e77acf` and the build embeds the exact installed string.

## 1. The cross-build (Docker, msvc-wine)

There is no `ci/build-win64-from-linux.sh` in r2; the script is `build/build-win64-from-linux.sh`. It runs DFHack's
official cross image `ghcr.io/dfhack/build-env:master` (`dfhack-configure` + `dfhack-make` inside). The release
itself was built natively on GitHub's `windows-2022` runner with MSVC (`.github/workflows/build-windows.yml`), so the
image is the same compiler family, not the same binary toolchain.

**Image** (amd64 only, run under emulation on this Apple Silicon Mac):
- `ghcr.io/dfhack/build-env@sha256:40f020d7e2fcde9d637ad9502e623130acac297e949eaca8ac6b10a6df4da673`
  (tag `master`, built 2025-04-13, source rev `DFHack/build-env@7482a76c`, 1.53 GB).
- Contents: MSVC 19.43.34810 (toolset 14.43.34808), Windows SDK 10.0.22621.0, wine64, cmake 3.22.1, ninja,
  git 2.34.1, ccache 4.8.3, prebuilt native host tools in `/home/buildmaster/dfhack-native` (protoc etc.).
- Pull: `docker pull --platform linux/amd64 ghcr.io/dfhack/build-env:master` took **23 min** (two ~650 MB layers;
  extraction is the slow part).

**Scripts** (versioned in `/Users/nathanielcannon/Claude/Projects/sw-wt/aquarium-plugin/`, git repo, commit `20b8057`):
- `scripts/sync-into-dfhack.sh` copies `src/` into the DFHack tree's `plugins/external/aquarium/` and adds
  `add_subdirectory(aquarium)` to `plugins/external/CMakeLists.txt` (r2's documented external-plugin hook,
  `plugins/CMakeLists.txt:165-194`; `CMakeLists.custom.txt` is still read for backwards compatibility,
  `:196-199`). A copy, not a symlink: inside the container a link that points outside the mounted tree would dangle.
- `scripts/build-win64.sh [targets...]` (default target `aquarium`; `CONFIGURE=1` to reconfigure) does the sync,
  refuses to build unless `git describe` = `53.16-r2-0-g02e77acf`, then runs (abridged):

```
docker run --rm -i --platform linux/amd64 \
  -v $SRC:$SRC -v $BUILD:$SRC/build -v $GITCOMMON:$GITCOMMON \
  -e BUILDER_UID=$(id -u) -e CCACHE_DIR=$SRC/build/ccache \
  ghcr.io/dfhack/build-env@sha256:40f020d7... \
  bash -c "git config --global --add safe.directory '*' && cd $SRC/build &&
           dfhack-configure windows 64 Release -DCMAKE_INSTALL_PREFIX=$SRC/build/output \
             -DBUILD_PDBS=ON -DBUILD_DOCS=0 -DBUILD_STONESENSE=0 -DBUILD_TESTS=0 -DBUILD_DFLAUNCH=0 \
             -DDFHACK_RUN_URL=https://github.com/DFHack/dfhack/actions/runs/36605190931 &&
           cmake -D dfhack_SOURCE_DIR:STRING=$SRC -D GIT_EXECUTABLE:STRING=/usr/bin/git -P $SRC/library/git-describe.cmake &&
           dfhack-make -j16 aquarium"
```
  with `SRC=/Users/nathanielcannon/Claude/GitRepos/dfhack-53.16-r2`,
  `BUILD=/Users/nathanielcannon/Claude/Projects/sw-wt/aquarium-plugin/.build-win64` (git-ignored; holds the ninja
  tree, ccache and outputs). Nothing is written into the DFHack checkout except git-ignored files
  (`plugins/external/*`, `library/include/git-describe.h`, `library/git-describe.cmake`); `git status` stays clean.
  `GITCOMMON=/Users/nathanielcannon/Claude/GitRepos/dfhack-latest/.git`.

**Two traps, both fixed in the script:**
1. The r2 checkout is a **git worktree** of `dfhack-latest`: its `.git` is a file with an absolute gitdir. Mounting
   only the tree (as `build-win64-from-linux.sh` does, at `/src`) leaves git blind inside the container. Fix: mount the
   tree and the parent repo's `.git` at their real host paths.
2. `library/CMakeLists.txt:356` only creates the rule that writes `include/git-describe.h` when `$SRC/.git/index`
   exists, which is false for any worktree. First attempt failed at generate time with:
   `CMake Error at library/CMakeLists.txt:340 (add_library): Cannot find source file: include/git-describe.h`
   Fix: run the same generator (`library/git-describe.cmake`, written by configure) ourselves. It writes
   `#define DFHACK_GIT_DESCRIPTION "53.16-r2-0-g02e77acf"`. (On a brand-new tree the first configure still fails
   once at generate; rerun the script.)

**Why BUILD_PDBS=ON:** the release CI sets it for `cache-id == 'release'` (`build-windows.yml`, `-DBUILD_PDBS`), and the
stock plugins embed a `.pdb` path. It adds `/Z7` + `/DEBUG` (`CMakeLists.txt:282-287`); `/DEBUG` switches the linker
default to `/OPT:NOREF`. Without it, our `smooth-movement.plug.dll` was 170,496 B vs stock 372,224 B and the run-URL
string was stripped from plugins; with it, 373,760 B vs 372,224 B (0.4 %, the MSVC minor-version gap) and our
`dfhack.dll` is 19,688,448 B vs the installed 19,627,008 B. Code generation and struct layout are the same either way.

**Timings (16 jobs, amd64 emulation):**

| step | wall |
|---|---|
| image pull (once) | 23 min |
| first configure + build of `aquarium` (161 ninja steps: deps, dfhack.dll, plugin) | 9 min 34 s |
| reconfigure with BUILD_PDBS=ON + rebuild `aquarium` + `smooth-movement` (158 steps) | 4 min 18 s |
| incremental `aquarium` after editing aquarium.cpp | ~50 s (it also relinks dfhack.dll) |

ccache is wired (`-- using ccache`, `CCACHE_DIR` in the build dir) but stayed under 1 MB, so it saves nothing with
wine `cl`; the ninja tree in `.build-win64` is what makes rebuilds fast. Keep that directory.

## 2. The proof plugin `aquarium`

Source: `/Users/nathanielcannon/Claude/Projects/sw-wt/aquarium-plugin/src/aquarium.cpp`.
- `plugin_init` registers `aquarium-plugin`: prints DFHack version, git description, DF version, and
  `gps->main_viewport->dim_x/dim_y`; then the hook stats. `aquarium-plugin reset` zeroes the counters.
- `enable aquarium` interposes `df::renderer_2d_base::update_all` (same vmethod and placement as smooth-movement,
  `SM:839-850`): counts frames, times the hook body with `steady_clock` (avg/max/last ns), samples main-viewport dims
  and how many `lower_viewport[]` have `flag.active`, then calls `INTERPOSE_NEXT(update_all)()`. No visual change.
  Counters are atomics (render thread writes, core thread reads).
- `disable aquarium` / plugin unload removes the hook.

## 3. Build output and evidence

- **dll:** `/Users/nathanielcannon/Claude/Projects/sw-wt/aquarium-plugin/.build-win64/plugins/external/aquarium/aquarium.plug.dll`
  - 233,984 bytes, `PE32+ executable (DLL) (GUI) x86-64, for MS Windows`
  - sha256 `5f563cd481a760fef3104a6a780a66ccd8776a4619dbbd01fe99fef43243e5fc`
  - pdb alongside: `aquarium.pdb` (4.4 MB), for crash triage only, not needed on the rig.
- **`strings -a aquarium.plug.dll`** shows the same four strings as the installed `dfhack.dll` and stock plugins:
  `53.16-r2`, `53.16`, `https://github.com/DFHack/dfhack/actions/runs/36605190931`, `53.16-r2-0-g02e77acf`.
- **Exports:** `plugin_name, plugin_version, plugin_git_description, plugin_abi_version, plugin_self, plugin_init,
  plugin_globals, plugin_enable, plugin_shutdown, plugin_is_enabled, plugin_dev` (every symbol the loader checks,
  `PluginManager.cpp:285-290`).
- **Imports:** `dfhack.dll, KERNEL32, MSVCP140, VCRUNTIME140, VCRUNTIME140_1, api-ms-win-crt-*`, the same set the
  stock plugins import. All 16 symbols it imports from `dfhack.dll` (e.g. `?_identity@renderer_2d_base@df@@...`,
  the `VMethodInterposeLinkBase` ctor, `PluginCommand` ctors) are present in the **installed** `dfhack.dll`'s export
  table (`llvm-objdump -p`, 0 of 16 missing).
- Not yet proven: loading in the running game (desk-only task). That is the deploy step below.

## 4. Deploy recipe (for the lead; DF must be stopped first)

Plugins live in the DFHack Steam app folder, not under `$DF_DIR`:

```
cd /Users/nathanielcannon/Claude/Projects/DwarfCron
source scripts/cx-config.sh
scripts/cx-lifecycle.sh stop
cp /Users/nathanielcannon/Claude/Projects/sw-wt/aquarium-plugin/.build-win64/plugins/external/aquarium/aquarium.plug.dll \
   "$DF_DIR/../DFHack/hack/plugins/"
scripts/cx-lifecycle.sh start            # then load a save as usual (the map must be on screen)
grep -a "aquarium" "$DF_DIR/stderr.log"  # expect: loaded plugin aquarium; DFHack build 53.16-r2-0-g02e77acf
python3 scripts/cx-rpc.py --cmd aquarium-plugin
python3 scripts/cx-rpc.py --cmd enable aquarium
python3 scripts/cx-rpc.py --cmd aquarium-plugin      # again after a few seconds of rendering
python3 scripts/cx-rpc.py --cmd disable aquarium
```
Pass the command as separate words; a single-string `--cmd` never replies.

Expected output:
```
# aquarium-plugin, before enable
aquarium: DFHack 53.16-r2 (53.16-r2-0-g02e77acf), DF 53.16
aquarium: main_viewport dim_x=<cols> dim_y=<rows>
aquarium: hook disabled frames=0 ns_avg=0 ns_max=0 ns_last=0
aquarium: hook saw dim=0x0 lower_viewports_active=0
# enable aquarium
aquarium: enabled
# aquarium-plugin, after enable
aquarium: hook enabled frames=<grows by about FPS x seconds> ns_avg=<hundreds to low thousands> ns_max=<...> ns_last=<...>
aquarium: hook saw dim=<same as main_viewport> lower_viewports_active=<0..8>
```
Failure signatures: `Plugin aquarium was not built for this version of DFHack` (version string mismatch, wrong tree);
`Warning: Plugin aquarium compiled for DFHack X` (git-describe drift; it loads anyway);
`aquarium: could not hook renderer_2d_base::update_all` (renderer vtable not found). To roll back, stop DF and delete
the dll.

## Render hook design for aquarium

Sources: `R2` = `/Users/nathanielcannon/Claude/GitRepos/dfhack-53.16-r2`; `SM` = `R2/plugins/smooth-movement/smooth-movement.cpp`;
`GX` = `R2/library/xml/df.g_src.graphics.xml`; `EN` = `R2/library/xml/df.g_src.enabler.xml`;
`RF` = `data/aquarium-run/FINDINGS/2026-10-03-render-internals.md` (rig results). [V] = read in source or measured
on the rig; [I] = inference, needs a rig probe.

### What the hook is and when it runs

- smooth-movement interposes `df::renderer_2d_base::update_all` (`SM:839-850`; vmethod `EN:105`). Its body runs the
  world work first and then `INTERPOSE_NEXT(update_all)()`, because "update_all is the existing UI stage, so world
  correction must run first" (`SM:847`). Hook applied/removed in `plugin_enable` (`SM:959`, `SM:965`). [V]
- It draws straight into the SDL target: binds `SDL_RenderCopyF/ExF/FillRect/Get|SetRenderDrawColor` from DF's SDL via
  `DFSDL::obtain_library_handle()` + `LookupPlugin` (`SM:860-877`); pixel position of a cell is
  `tile_size(zoom)*x + renderer->origin_x`, `tile_size = viewport_zoom_factor*32/128` (`SM:83-85, 194-200`). [V]
- The per-cell compositor DF itself uses is the vmethod `renderer->update_viewport_tile(vp, x, y)` (`EN:103`);
  smooth-movement calls it on any viewport after swapping layer values with scoped restores
  (`SM:216-240, 312-328, 388-412`), so DF's own state is untouched when the hook returns. [V]
- Buffers: `gps->main_viewport`, `gps->lower_viewport[8]` (`GX:727-728`), each a `graphic_viewportst` with
  `dim_x, dim_y, clipx[2], clipy[2]` and ~20 per-cell layers plus `_old` copies (`GX:355-428`). Cell index is
  `x*dim_y + y` (`SM:315`). Draw order is lower[7] -> ... -> lower[0] -> main (`SM:701-713`, "matching DF's
  lower-to-main draw order" `SM:765-767`). Each viewport's `screentexpos_interface` is the z-fog for what lies
  beneath it, so fog deepens once per level (`SM:321-323, 772-774`; fog tile = MULTILEVEL_AIR, `RF` 2.3). [V]
- DF repaints only what changed: a plugin-only change "changes the screen without changing anything DF knows, so DF
  will not repaint" and needs `++gps->force_full_display_count` (`SM:904-911, 968-969`; field `GX:805`); the screen
  persists in `renderer->screen_tex` (`R2/library/xml/df.g_src.renderer_2d.xml:14`), which is why smooth-movement
  blacks out and repaints its previous frame's cells (`SM:816-833`). Each layer's `_old` twin holds the last frame
  (used as "previous" in `SM:463, 507`). [V for the plugin's model; I for the exact DF diff rule]
- Thread: `update_all` runs on DF's render thread; smooth-movement never reads gameplay data there
  ("gameplay data is never read", `SM:48-49`). Map/unit reads belong in `plugin_onupdate` (core thread,
  sim-synchronous) and must reach the hook through a snapshot (double buffer + atomic index).
- Not available on this build: DF's map printer. `map-render.cpp:28` needs global `twbt_render_map`, which has no
  address in the `v0.53.16 win64 STEAM` table (`R2/library/xml/symbols.xml:126-1239`; only `map_renderer` at `:147`),
  so a plugin cannot ask DF to print another z-level into a viewport. Content for deeper levels has to be built by
  the plugin. [V]

### (a) Compositing deeper z-levels (lower_viewport[1..7])

Rig fact (`RF` sec. 9): over the sea, main background = RIVER_BED sheet, lower[0] = liquid flag lvl 7 + MULTILEVEL_AIR
fog, lower[1..7] all zero. DF stops at the first water level and never prints the bed or deeper creatures. [V]
`Gui::getDepthAt` treats "background != 0" as the depth at which a cell shows content
(`R2/library/modules/Gui.cpp:3026-3038`). Lua writes into `lower_viewport[k]` never reached the screen (`RF` F7).

Two routes, both inside the `update_all` hook before `INTERPOSE_NEXT`:

1. **Feed DF's compositor (cheapest if it works).** For each managed cell (x,y) whose water column continues below
   lower[0], write into lower[k] (k = depth-1): `screentexpos_liquid_flag` (copy lower[0]'s value so DF draws its own
   water sprite per level), `screentexpos_interface` = MULTILEVEL_AIR texpos (fog per level), at the bed level
   `screentexpos_background` = bed texpos and `screentexpos` (+ left/right/up* creature layers) = the creature's
   texpos from `unit->texpos[...]` (`R2/library/xml/df.unit.xml:3128-3130`). Then DF's own pass draws them with its
   fog. Open questions [I]: whether DF's pass composites lower[k] beyond `d_init.display.number_of_lower_elevations_shown`
   (`R2/library/xml/df.d_init.xml:67`) or with `flag.active` clear (`GX:350-353`); whether F7 failed for timing
   (Lua wrote on the core thread, DF reprinted before compositing; the C++ hook writes on the render thread just
   before the compositor, which removes that cause) or because the pass skips those viewports. Probe: write one
   cell's lower[1] background with a loud texpos in the hook, `++force_full_display_count`, look.
2. **Draw it ourselves (works regardless of DF's skip rules).** For each changed managed cell: black-fill the tile
   rect (`SM:818-828`), then, deepest first, call `renderer->update_viewport_tile(lower[k], x, y)` with the plugin's
   values swapped into lower[k]'s layers under scoped restore (`SM:216-240`), then lower[k-1] ... lower[0], then
   main (`SM:365-377, 751-759` do exactly this lower-to-main repaint). Each level's own `screentexpos_interface`
   fog is drawn by its `update_viewport_tile`, so depth fog stacks natively. Main must be redrawn last so the
   RIVER_BED sheet / UI-layer content stay on top (or swap main's background to 0 for those cells during the
   redraw so the lower stack shows through; `RF` sec. 9 showed that a transparent main background reveals lower[0]).

Content of the deeper levels (both routes): the bed texpos per bed tiletype comes from a small table filled by
sampling what DF prints into `main_viewport->screentexpos_background` for that tiletype when it is at the view
level (or from the aquarium's own baked bed tiles); creatures from `unit->texpos`. The water column depth per (x,y)
comes from the `plugin_onupdate` snapshot (map block designation `flow_size`/liquid type), refreshed only for blocks
whose liquid changed.

### (b) Translucent tint over underwater creatures

- Where: after DF's world draw of the cell and before `INTERPOSE_NEXT(update_all)` (so the UI stays on top), only
  for cells whose creature layers (`screentexpos`, `screentexpos_left/right_creature`, `up*_creature`; table
  `SM:130-155`) are non-zero and whose cell is underwater (main/lower `screentexpos_liquid_flag != 0`, `GX:369`, or
  the snapshot).
- How, option 1 (cheapest): `SDL_SetRenderDrawBlendMode(BLEND)` + `SDL_SetRenderDrawColor(r,g,b,a)` +
  `SDL_RenderFillRect` over the tile rect (pattern `SM:818-828`; add `SDL_SetRenderDrawBlendMode` to the bindings of
  `SM:860-877`), then re-apply the fog/interface for that cell like `draw_interface_only` (`SM:345-363`).
- Option 2 (DF-composited): swap a translucent veil texpos (made once with `Textures::createTile`,
  `R2/library/include/modules/Textures.h:56`; pixel order 0xAABBGGRR, aquarium finding 13) into
  `screentexpos_top_shadow` (layer above creatures, `GX:385`) for that cell and call `update_viewport_tile`; for
  creatures in lower[k] the same veil in main's `top_shadow` covers them from above (`RF` 2.2).
- Per frame O(visible underwater creatures): a list of candidate cells from the snapshot, never a full-viewport scan.

### (c) Per-frame cost O(changed cells), natively

- Because DF repaints only changed cells into a persistent `screen_tex`, anything the hook paints persists until DF
  repaints that cell. So per frame the hook needs to redo only: (1) cells DF repainted this frame, (2) cells whose
  plugin state changed (water level, creature moved, tint animation tick), (3) everything after a context change
  (z, zoom, viewport dims, clip, `force_full_display_count`), detected exactly as `update_visual_context` does
  (`SM:87-119`).
- Detecting (1): compare managed cells' layers with their `_old` twins (`GX:395-419`) before calling next; cost is
  O(managed cells) of integer compares (~a few µs for thousands of cells in C++), the redraws are O(changed).
  A full memcmp of all main layers (~100x50 cells x 20 layers) is ~100k ints, also well under 50 µs.
- Detecting (2): the core-thread snapshot carries a per-cell revision; the hook keeps last-drawn revision per cell.
- Budget check: the proof plugin records ns per hook call (`aquarium-plugin` prints avg/max/last); later stages keep
  the same counters so the lead can read cost on the rig without a stopwatch.
