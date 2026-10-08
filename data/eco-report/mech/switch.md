# Seasonal Wildlife: on/off, presets, defaults and the bundle (from the code)

Source: `/Users/nathanielcannon/Claude/Projects/sw-wt/plugin`, branch `v7.2-plugin`, HEAD `8185d85` (8 Oct 2026).
Everything here comes from reading the code. Nothing was run. Paths are relative to that worktree unless they start
with `/`. "Engine" means `scripts/seasonal-wildlife.lua`. "Plugin" means `plugin/src/seasonal-wildlife.cpp`, and
"plugin Lua" means `plugin/lua/seasonal-wildlife.lua`.

---

## (a) Every way to turn it on and off

### The chain

```
enable seasonal-wildlife
  -> C++ plugin_enable (cpp:7410)        want_depth = true; set_enabled() hooks the renderer (cpp:7365)
  -> Lua plugins.seasonal-wildlife.on_enable(false)  (plugin Lua:81)
  -> engine turn_on('command')  (engine:16219)
       - turns off the old stand-alone aquarium.plug.dll if it is on (16224-16228)
       - `aquarium depth on` if depth was switched off (16238-16240)
       - saves the autostart: dfhack-config/seasonal-wildlife.json {"autostart": true} (16241, PANEL.setAutostart 16146)
       - on a loaded fort: PANEL.fortOn() (16242-16245, 16086)
       - PANEL.modCheck(): builds the Aquarium mod, or rebuilds it when an older generator wrote it (16167)
       - PANEL.report(): renderer, graphics mode, lower elevations, whether this world has the mod, autostart (16188)
```

DFHack tries a plugin before a script for `enable X` (HANDOFF trap 18). So with the dll loaded, `enable` goes to C++.
Where the dll does not load, the script's `--@ enable = true` (engine:2) catches `enable seasonal-wildlife`, and the
script's tail calls `turn_on('tool')` / `turn_off('tool')` (engine:17693-17696).

### Every entry point

| How | Where | What it does |
|---|---|---|
| `enable seasonal-wildlife` | cpp:7410 -> plugin Lua:81 -> engine:16219 | Renderer on, autostart saved, `fortOn` on a loaded fort, mod check, report |
| `seasonal-wildlife on` / `seasonal-wildlife enable` | engine:18771-18772 -> `turn_on('tool')` | The same. The engine runs `enable seasonal-wildlife` itself (16229-16236). `PANEL.inner` keeps the plugin's callback from running a second time. |
| `disable seasonal-wildlife` | cpp:7410 -> plugin Lua:86 -> engine `turn_off('command')` 16257 | Renderer off (hooks stay as pass-throughs until unload, cpp:7383-7399), autostart cleared, fort off (below) |
| `seasonal-wildlife off` | engine:18773 -> `turn_off('tool')` | The same; runs `disable seasonal-wildlife` itself |
| `seasonal-wildlife enable rotation` | engine:18770 | The old `enable`: `enableSched()` only (15926), no renderer and no switches |
| `seasonal-wildlife disable` | engine:18775 | **Rotation-only off**: `disableSched()` (15950). This is NOT the same as `disable seasonal-wildlife`. |
| Autostart at DF start | cpp:7484-7490: `SC_CORE_INITIALIZED` -> plugin Lua `on_core_initialized` (76; reads the json) -> `set_enabled(true)` -> `on_enable(true)` -> `turn_on('autostart')` | Renderer on, mod check, a one-line report. **No fort work**, because no map is loaded yet (16242 skips it for 'autostart'). It also warns about old copies in `dfhack-config/scripts` and an old `aquarium.plug.dll` (plugin Lua:41-53). |
| A map loads | cpp:7491-7495 sets `bridge_pending`; the next frame calls plugin Lua `on_map_loaded` (cpp:7430-7436) -> engine `map_loaded()` (16280) | If the fort has no `seasonal-wildlife/config` site data (engine:521, 16283), it is a **new fort: `fortOn()`, everything on**. A fort that already has config keeps its own settings, and only gets `PANEL.onMapLoad` (re-arm jobs if `cfg.enabled`) when the engine missed the load. |
| Engine's own map-load hook | engine:17098-17114 | Every load: `PANEL.onMapLoad()` (16213: `enableSched()` if `cfg.enabled`; irruption masks). This runs **whether or not the plugin is enabled**. |
| World unload | engine:17099-17107 | Every raw write is restored (CURIOUS, V7.restore, trickle, sizes, HUNT) and every job is cancelled. |
| Panel **All on** (key A on the Panel tab, gui:434) | gui:2629 -> registry act `all_on` (controls:75, 911) -> `PANEL.allOn` (engine:16070) | Restores the switches saved by All off. With nothing saved, it turns on every **non-opt-in** switch and leaves opt-ins as they were; then parks the nudges. No renderer, no autostart, no roster. |
| Panel **All off** (key X, gui:435) | registry `all_off` -> `PANEL.allOff` (16061) | Saves the switches (`seasonal-wildlife/panel` site data), `PANEL.restoreAll` (16042: cavern frequencies, cluster sizes, hunting/curious flags, reformed thieves, scavenging walks, v7 raw writes, forager walks, irruption writes, coupling pool), then sets every switch off except the four layer switches. The renderer stays on. |
| Window Ctrl+E "Rotation on/off" | gui:502, `act_enable` gui:1779 | `enableSched` / `disableSched` only |
| Window first open on an uninitialised fort | gui:394-397, 625-645 | Applies the **biome preset** (`applyPreset`) and `enableSched`. It does not use v7.3 casts (see gap G4). |
| Web companion | web.lua:1185-1205 -> `C.runVerb` / `C.set` / `C.act` | Whatever the registry allows: All on/off, the rotation switch (`enable rotation`/`disable`, controls:79), every Panel switch. `/cmd` accepts the verbs in `VERBS` (controls:724-728). That list includes bare `enable` (now everything on, including opt-ins) and `disable` (rotation only). It does **not** include `on`, `off`, `preset` or `cast`. |
| Plugin `aquarium depth on/off` | cpp:6657-6678 | The water look only. It also sets `want_depth`, so it lasts across map loads until the next `enable` (cpp:7414). |
| Plugin shutdown | cpp:7515 | Renderer off; the autostart is left alone |

### What "everything on" turns on: `PANEL.fortOn()` (engine:16086-16129)

1. **Roster, on the fort's first full enable only** (`c.full_enable_roster` unset):
   - `captureDefault` snapshots worldgen stock.
   - If the v7.3 season casts are on, `ROSTER.castYear` grows this year's casts after the layers are on. Casts are
     on by default: `ROSTER.CAST_DEF.enabled = true`, engine:8299.
   - Otherwise `applyPreset` deals the biome preset (below).
   - After this, the roster is never reshuffled (16092-16101, 16104-16108).
2. **Every Panel switch is set on except the parked ones** (16102). There are 20 switches in `PANEL.SWITCHES`
   (engine:15998-16031). `V7.PARKED_SWITCHES = {nudge, coupling, forage}` (engine:1070) stay off. `V7.parkNudges`
   (1071-1081) also forces off the raptor stoop, bear fishing (`v7.fishers`) and panic flight. `cfg.parked = false`
   lifts the parking.
3. `ROSTER.normalize`, so the new layers' species join the roster (16109).
4. `extinct.fix = true`, `aquarium.enabled = true`, `aquarium.legend = true`, `enabled = true` (16110-16113).
5. `enableSched()` and `applyLive`, which start the jobs and write this season's stock (16114-16115).

The 20 switches after `enable`:

| id | Label | Fresh default (`defaultConfig`, engine:735) | After `enable` | Opt-in? |
|---|---|---|---|---|
| rotation | Seasonal rotation | off | **on** | |
| land | Layer: land | on | on | |
| water | Layer: water | off (auto-on where the map has water, `water.layer_auto`) | **on** | |
| cavern | Layer: caverns | off | **on** | |
| deep | Layer: deep | off | **on** | |
| groups | Groups and the arrival gate | on | on | |
| cavegate | Cavern gate | on | on | |
| cohesion | Cohesion | on | on | |
| ecology | Ecology | on | on | |
| waterjob | Water draws | on | on | |
| exhaust | Exhaustion and replacement | on | on | |
| curiousreform | Curious thieves stay | on | on | |
| quietfights | Quiet wildlife fights | on | on | |
| scavenge | Scavenging | off | **on** | yes |
| hunting | Vermin hunting | off | **on** | yes |
| livestock | Livestock as prey | off | **on** | yes |
| irruption | Cavern irruptions | off | **on** | yes |
| nudge | Nudge | off | off (parked) | yes |
| coupling | Coupling | off | off (parked) | yes |
| forage | Vermin foraging | on in `defaultConfig`, then parked | off (parked) | |

Also turned on: the extinct corrections and the Lua aquarium master and legend. The water renderer comes from the
plugin, not from `fortOn`.

The plugin's own water defaults are compiled in (cpp:302-396):
- depth on (`want_depth` true), shade `tint`, water `unified`, `deep` tint, `shallow` on;
- waves on, fronts crest art, surf off, wash off, glow rim 0, DF fog off;
- shimmer alpha 45, streaks alpha 70, depth darkening 46;
- falls on, bed art on, bed print on, fastdraw on, tilefix on, glide auto;
- per-kind tints for lake, river, pool, cave and sea (cpp:388-396).

### What `turn_off` restores (engine:16257-16278)

- Renderer off. If it is still on, the report says so and gives `disable seasonal-wildlife`.
- Autostart cleared (the json gets `autostart: false`).
- On a loaded fort **whose rotation is on**:
  - `disableSched()` (15950-15981) restores cavern frequencies, trickle and group-size cluster ranges,
    vermin-hunting and curious caste flags, reformed curious beasts, scavenging walks, V7 raw writes (seasons,
    solitary package, fishers, gobble, extinct, by `V7.rec` records, 13741), forager walks, the water spill's borrowed
    seasons, and irruption writes. It cancels every repeat job.
  - It also sets `aquarium.enabled = false` and writes a ledger line.
- The switches keep their values for the next `on`. That is the difference from All off, which turns the switches
  off and remembers them.

What `turn_off` does **not** do:
- It does not end a coupling's closed pool. Only `PANEL.restoreAll` (16056-16057) does that. Coupling is parked, so
  this matters only if someone lifts the parking.
- It does not stop the web server.
- It does not touch the mod.
- It does not reach **other forts**: their `cfg.enabled` stays true, and the engine's own map-load hook (17112)
  re-arms their jobs on load even though the renderer and autostart are off.

### Paths without the plugin, or without a fort

| Situation | Result |
|---|---|
| dll missing or wrong DFHack | `enable seasonal-wildlife` reaches the script. Same `turn_on`, Lua water layers stand in, **no autostart** (report line 16211). **No new-fort auto-on**: only the plugin bridge calls `map_loaded`. |
| `on` typed at the title screen | Renderer, autostart and mod only. Forts loaded later get `fortOn` only if they have never run the tool. A fort turned `off` earlier stays off. |
| Classic/ASCII | The renderer stands down and the report says so (16198). Wildlife runs. |

---

## (b) Presets

There are four unrelated kinds of "preset". None of them is a named on/off profile for the tool.

### 1. The biome roster preset: `seasonal-wildlife preset` (engine:18273-18279; `applyPreset` 3883-3904)

- Turns on every layer the map has (`ROSTER.presentLayers`, 3869).
- Every unlocked in-embark natural species gets `defaultAllow`, which mostly means active.
- Each active species gets one season from the climate matrix (`assignFromMatrix`).
- The land pattern is `steady`, and rotation is on.
- Its name comes from the embark's biomes (`presetName` 3857, e.g. "temperate shrubland, ...").

It is applied by:
- the console `preset`;
- the window's first open (gui:625-645);
- **R** on the Layers tab;
- `fortOn` when casts are off.

The web may not send it (controls:722-723).

Read it back from:
- each species' `why` entry, `preset: <name>`;
- the ledger `build` line;
- the Layers tab status line (gui, "Preset re-applied: ...").

### 2. v7.3 season casts (engine:8280-8305, verb 18333-18405)

- Each season has its own roster per layer (land, water, cavern), grown from a high-value seed through its prey and
  predators, with slot quotas in `ROSTER.CAST` (8281-8297).
- `ROSTER.CAST_DEF = {enabled=true, carry=0.25, giant=0.2, pack=3, hv_petvalue=200, hv_mass=1e6, salt=0}`.
- `cast restfreq 0|1` sets the frequency at which resting cavern species are held. The default is 1; vermin always
  stay at 1.

Verbs: `cast on|off`, `cast rebuild [SALT]`, `cast status`, `cast show SEASON [LAYER]`. They are console only: no
registry row, no Panel section and no web verb.

### 3. The Aquarium mod preset: alpha per tile water level (`GFX.PRESETS`, `scripts/seasonal-wildlife-aquarium-gfx.lua:26-33`)

| Preset | alpha, level 7 -> 1 | flows | mist | tint |
|---|---|---|---|---|
| vanilla | 255 255 255 255 230 204 179 | 1.0 | 1.0 | no |
| subtle | 215 205 195 185 175 165 150 | 1.0 | 0.9 | yes |
| **aquarium** (default, `V7.AQ.DEF.preset`, engine:661) | 150 140 130 120 110 100 90 | 0.75 | 0.75 | yes |
| clear | 105 95 85 75 65 58 50 | 0.5 | 0.6 | yes |
| shallows | 255 255 255 140 115 100 90 | 0.75 | 0.75 | yes |
| custom | `aquarium alpha A7..A1` (default as aquarium) | 0.75 | 0.75 | yes |

How a preset is set:
- `seasonal-wildlife aquarium preset NAME` only stores the name (engine:17680-17681).
- `seasonal-wildlife aquarium install [NAME]` builds the mod from the player's vanilla sheets into
  `mods/seasonal_wildlife_aquarium/`, and refreshes the `data/installed_mods/... (N)` copies
  (`install`, aquarium.lua:3170-3221).
- The Panel/web Aquarium section has a preset choice and an Install action (controls:315-316, 327).
- `turn_on` rebuilds the mod only when it is missing or stale. It keeps the stamped preset, and `vanilla` becomes
  `aquarium` (engine:16173-16176).

A world sees a change only after a save, quit and reload. A world made without the mod never sees it.

Read it back from:
- the stamp file `sw_aquarium_stamp.txt` (`preset=`, `alpha=`, `version=`, `build=`, gfx:856-863);
- `seasonal-wildlife aquarium status`;
- the turn_on report "water mod: up to date (preset X)".

### 4. The native renderer's look

There is no preset. Every value is a compiled default, changed only by `aquarium <verb>` console commands
(cpp:6531 onward: `tint`, `deeptint`, `veil`, `water unified|df`, `deep tint|off`, `waves`, `surf`, `shimmer`,
`streaks`, `falls`, `bedart`, ...). **Nothing is persisted**: there is no json and no site data in the cpp, so every
DF restart returns to the compiled defaults. Read back with `aquarium` / `aquarium status` (cpp:6286-6300).

### Defaults and readback in general

- The registry (`scripts/seasonal-wildlife-controls.lua`) reads every default from the engine's `defaultConfig()`
  by path (controls:43, `defaultOf` 631).
- The Panel marks a non-default value with `*` and offers a per-control reset.
- `seasonal-wildlife-controls list [SECTION]` / `json` print value, default and range.
- Window Alt+R asks "reset roster" or "reset everything". `ROSTER.resetAll` (engine:3954) copies `defaultConfig`
  back, then re-applies the present layers. It does not reset `cast`/`casts`, which are not in `defaultConfig`. It is
  window-only, not in the registry or on the web.

---

## (c) The bundle

### `plugin/scripts/package.sh`

1. Refuses to run with uncommitted changes in plugin/, scripts/ or USAGE.md (16).
2. Builds the release dll with `DEV=0` through `build-win64.sh` (Docker msvc-wine against
   `~/Claude/GitRepos/dfhack-53.16-r2`, which must describe as `53.16-r2-0-g02e77acf`, build-win64:22).
3. Checks that the dll names `53.16-r2` and does not contain the developer verbs (21-22).
4. Zips `dist/seasonal-wildlife-<VERSION:-7.2.0>-dfhack-53.16-r2-<commit8>.zip`.

| In the zip | Installs to | Role |
|---|---|---|
| `hack/plugins/seasonal-wildlife.plug.dll` | `DFHack/hack/plugins/` | Water renderer (`aquarium` command plus the old `aquarium-plugin` alias, cpp:7336-7361), autostart, map-load bridge, `scan_water` and `renderer_state` for Lua |
| `hack/lua/plugins/seasonal-wildlife.lua` | `hack/lua/plugins/` | `on_core_initialized`, `on_enable`, `on_disable`, `on_map_loaded`; old-copy warnings |
| `hack/scripts/seasonal-wildlife.lua` | `hack/scripts/` | Engine and console verb (18.8k lines) |
| `hack/scripts/seasonal-wildlife-controls.lua` | " | Control registry (Panel and web) |
| `hack/scripts/seasonal-wildlife-web.lua` + `.html` | " | Browser companion: 127.0.0.1:8642, token, 10 tabs: Overview, Map, Groups, Species, Food web, Seasons, Roster, Waters & caverns, Controls, Ledger (html:675) |
| `hack/scripts/seasonal-wildlife-aquarium.lua`, `-aquarium-gfx.lua` | " | Lua overlays (lens, legend, waves, bed, veil, streaks) and the mod builder |
| `hack/scripts/gui/seasonal-wildlife.lua` | `hack/scripts/gui/` | The window: 9 tabs plus the Panel |
| `README.md` (`plugin/package/README.md`), `USAGE.md`, `SHA256SUMS` | zip root | Docs |

- The CMake install rules are the same (`plugin/CMakeLists.txt:16-17`). `sync-into-dfhack.sh` copies the tree into
  `plugins/external/seasonal-wildlife/` and makes it the only external plugin.
- No art ships: the mod is built on the player's machine.
- No init-file lines are needed.

### Versions at HEAD

| String | Value | Where |
|---|---|---|
| Package zip | `7.2.0` (default `VERSION`) | package.sh:14 |
| Engine `CACHE.release` | `'7.2.0'` | engine:615-616 (was `'7.0.0'` at fce7d68) |
| Aquarium Lua module | `'7.2.0-aq15'` | aquarium.lua:51 |
| Mod `NUMERIC_VERSION` / generator build | `VERSION = 2`, `BUILD = 1` | gfx:20 |
| Web snapshot | reports `CACHE.release` | web.lua:419 |
| DFHack pin | 53.16-r2 | package.sh:21, README:14 |

None of these were bumped for the v7.3 casts (64f9972 onward) or the unified water (721f6d6 onward).

The newest zip in `plugin/dist/` is `...-749384b1.zip` (7 Oct 15:39). That predates every v7.3 cast commit and
every unified-water commit. **No package of HEAD exists.**

### The shadowing trap

- DFHack searches `dfhack-config/scripts/` before `hack/scripts/`.
- `cx-lifecycle.sh deploy-tool` (DwarfCron `scripts/cx-lifecycle.sh:276-312`) copies into `dfhack-config/scripts`,
  so its copies run instead of the package's.
- The plugin names any such copies at start-up (plugin Lua:20-32, 41-53), and `engine()` reports "too old" when the
  found script lacks `turn_on` (plugin Lua:61-70).
- README "Upgrading" (README:53-64) tells players to delete them.
- **On the rig now**, according to the Part 2 read, the `dfhack-config/scripts` copies match HEAD 8185d85 and the
  package copies in `hack/scripts` are older. So the rig runs hot-swapped scripts beside a dll from an older zip.

---

## (d) Gaps against "easily on/off with presets and defaults ready at the flip of a switch; one bundle: aquarium graphics + plugin + browser panel + ecological summary"

| # | Gap | Evidence |
|---|---|---|
| G1 | **There are four different "on"s and three different "off"s** with different meanings. `enable`/`on` turns everything on, opt-ins included, except parked. Panel All on restores the saved switches, or the non-opt-in set. `enable rotation` is rotation only. Off: `disable seasonal-wildlife`/`off` is global (renderer and autostart) but per-fort in the engine. Panel All off turns the switches off, remembers them, and leaves the renderer on. **`seasonal-wildlife disable` is rotation-only**, the opposite of `disable seasonal-wildlife`. A player cannot tell them apart. | engine:18770-18775, 16061-16081, 16086; controls:75-79 |
| G2 | **No named presets for the tool itself.** "Preset" means four unrelated things: the roster deal, the casts, the mod alpha and the renderer (which has none). There is no Calm/Default/Full-ecology profile, and no "factory defaults" action outside the window's Alt+R. | engine:3883, 8299, gfx:26, cpp:302-396 |
| G3 | **The Panel and web have no master switch.** Neither can do what `enable`/`off` do: renderer, autostart, mod. The web `VERBS` list lacks `on`, `off`, `cast` and `preset`. It still accepts bare `enable`, which since v7.2 turns on everything including irruptions and livestock-as-prey. | controls:724-728; web.lua:1185 |
| G4 | **First-run roster depends on the route.** `enable` or a new-fort load uses **casts** (`CAST_DEF.enabled = true`); the window's first open uses the **biome preset**. USAGE "Quick start" (USAGE:41-58) still promises the preset and never mentions casts. | engine:16092-16101; gui:625-645 |
| G5 | **The v7.3 casts have no controls outside the console**: no registry rows, no Panel section, no web. `cast restfreq` is experiment-only. | controls.lua (no `cast`); engine:18333 |
| G6 | **The water renderer's look is console-only and is not saved.** Tints, veils, waves, shimmer and falls reset at every DF start. None are in the registry, Panel or web. | cpp has no persistence; controls:289-335 hold only Lua-overlay keys |
| G7 | **Most Panel/web Aquarium controls do nothing while the plugin is on.** The lens, waves, bed, veil and streak overlays stand down (`pluginOn`, aquarium.lua:2171-2185). Only preset/install/restore/uninstall and the legend still act. The status line says "`aquarium depth off` hands it back", but `pluginOn` tests `isEnabled`, not depth, so `depth off` leaves both blank. | aquarium.lua:2171-2185, 3244-3246; cpp:6657-6678 |
| G8 | **`off` does not follow the player to other forts.** It clears `cfg.enabled` only on the loaded fort. Another fort with rotation on re-arms its jobs on load through the engine's own hook, renderer or no renderer. `on` at the title screen does not revive a fort turned off earlier. | engine:16268-16274, 17112, 16283 |
| G9 | **Without the plugin there is no autostart and no new-fort auto-on**, because only the plugin calls `map_loaded`. That covers Linux/macOS DF and any other DFHack. | engine:16211; cpp:7430-7436 |
| G10 | **"Everything on" includes the risky opt-ins.** Irruptions, which pause the game by default (HANDOFF trap 17b), and livestock-as-prey are switched on. PLAN R5's risk note still names the nudge, which v7.3 has parked. | engine:16102; PLAN:779 |
| G11 | **The web companion is not started by `enable`** and has no autostart. The player must type `seasonal-wildlife-web start`. luasocket on r2 is marked unchecked (USAGE:314-315, STATE:4374). | web.lua:1258-1270 |
| G12 | **No ecological summary in the bundle.** The zip has README and USAGE (user guides) only. The closest things are `seasonal-wildlife status`, `cast status`, `ecology pairs`, and the web Overview and Food-web tabs. No report or summary page is generated or shipped. | package.sh:25-31 |
| G13 | **Stale versions and no current zip.** Everything still says 7.2.0, and no zip of HEAD exists (newest 749384b1). The rig's package copies are shadowed by `dfhack-config/scripts`. | (c) above |
| G14 | **Stale help text in the dll.** `aquarium depth on` without the plugin says "enable aquarium" (cpp:6661). The command help and README/USAGE list `tint ... [sand|mud|stone|soil|surface|cavern|all]`, but the code accepts `lake|river|pool|cave|sea|all` (cpp:6687-6694). `water unified|df`, `deep tint|off` and `deeptint` are missing from the help string (cpp:7338-7344). | cpp; README:88; USAGE:654 |
| G15 | **Doc counts drift.** USAGE/PLAN say 356 controls in 13 sections. The registry now has 14 sections (Aquarium added) and about 26 more control rows, 5 actions, 3 readouts and 1 species row than at fce7d68. HANDOFF numbers traps 17 and 18 twice, and its release recipe still says "five scripts" (seven Lua/HTML files plus gui/). | USAGE:262-264; PLAN:88; HANDOFF:236-245 |
| G16 | **Undo does not cover on/off.** `turn_on`/`turn_off` push no undo step; only the registry's All on/All off do (controls:912-914). | engine:16219-16278 |

A short build list for the one-switch goal:

1. One verb pair, with every UI calling it. Rename the script's `disable` to `disable rotation`.
2. A named tool preset table, for example quiet / standard / full, mapping to switch sets, casts on/off and a mod
   preset. Expose it in registry, Panel and web.
3. Save the renderer settings (json beside the autostart) and give the native look 3-4 named presets in the registry.
4. Hide or relabel the Lua aquarium rows while the plugin is on.
5. Make `off` global through a json flag that `onMapLoad` respects.
6. Optionally autostart the web server.
7. Ship a generated ecology summary page or command.
8. Bump the versions and package HEAD.

---

## (e) User-visible changes since v7.1 @ fce7d68 (for the 109-step walkthrough)

There are 211 commits from `fce7d68` to `8185d85`. Note that fce7d68 is the v7.1-ui merge (1 Oct 17:57), before
`812e4d7`, so its `CACHE.release` still read **7.0.0**.

### Release strings

- Engine `7.0.0` becomes **`7.2.0`** (engine:615).
- New strings:
  - aquarium module `7.2.0-aq15`;
  - mod version 2, build 1;
  - package zip `7.2.0`;
  - plugin dll reports `DFHack 53.16-r2` in `aquarium status`.
- v7.3 work (casts, unified water) is under 7.2.0.

### Verbs: added, changed, removed (help header diff, engine:1-156 against fce7d68:1-119)

| Change | Verb |
|---|---|
| **Changed meaning** | `seasonal-wildlife enable`: rotation on becomes **everything on** (renderer, autostart, all switches including opt-ins, layers, extinct fix, aquarium, mod, report). The old behaviour is now `enable rotation`. |
| Unchanged name, now differs from `disable seasonal-wildlife` | `seasonal-wildlife disable` (rotation off only) |
| Added | `seasonal-wildlife on`, `seasonal-wildlife off`; `enable seasonal-wildlife` / `disable seasonal-wildlife` (DFHack enable) |
| Added | `cast [status|show SEASON [LAYER]|rebuild [SALT]|restfreq 0|1|on|off]` (v7.3) |
| Added | `ecology pairs [tsv]` |
| Added | `aquarium ...` (tool verb: `status`, `on/off`, lens, legend, schools, surf, foam, veil, depth, fade, rows, color, waves, bed..., streaks..., shimmer..., budget, trip, marks, hz, rearm, `preset`, `alpha`, `install`, `restore`, `uninstall`, `probe`) |
| Added | Plugin command `aquarium` (status, depth, shade, tint, deeptint, water unified|df, deep, surface, fog, waves, glow, depthdark, falls, foam, fronts, wash, tilefix, surf, shimmer, streaks, veil, shallow, bedart, bedprint, fastdraw, glide, cell, reset) plus its alias `aquarium-plugin` |
| Added | `water scan`, `water bodies [TYPE] | [min N] [pool_max N] [slice MS]`, `roster water TOKEN bodies TYPES|default` |
| Added | `groups cavern mix on|off`, `groups cavern trim_gated on|off`, `roster apex now ... force`, `irruption set mask_lever wound|syndrome` |
| **Removed** | `water guard ...` (now prints "removed", engine:17773-17776); `water pull seek|radius|standoff|shore|nodes|tries` |

### Defaults changed

- **Parked (v7.3, `parked = true`)**: ecology nudge, coupling, vermin foraging, raptor stoop, bear fishing and panic
  flight are forced off at every load and by `enable`/All on.
  - At fce7d68, foraging, stoop, fishing and panic defaulted on.
  - `cfg.parked = false` restores them.
- New keys: `groups.cavern_hold_mix = true`, `groups.cavern_trim_gated = true` (default on), `water.bodies`
  {min_tiles 9, pool_max 64, scan_ms 4}, `irruption.mask_lever = 'wound'`, `aquarium.*` (`V7.AQ.DEF`, engine:658-672).
  In the Aquarium defaults, overlays are on, lens and legend off, waves auto, preset `aquarium`, and bed auto.
- Removed keys: `water.guard.*`, `water.pull.seek*` and their siblings.
- Season casts are on by default for a new fort's first `enable`.
- `PANEL.SWITCHES` itself is unchanged (same 20 switches), but the `rotation` switch's verb is now `enable rotation`
  (controls:79).

### Window and Panel

- **New Panel section: Aquarium** (14 sections, was 13), with groups:
  - Lens and legend;
  - Waves;
  - Moving water;
  - Translucent water: preset, install, restore, uninstall;
  - Budget.
- Water section: the "Stranding guard" group is replaced by "Water bodies" (min tiles, pool under, scan slice,
  Re-scan action, bodies readout).
- Caverns section: "Keep the season's mix" and "Trim DF waves too".
- Irruption section: "Curse masks carried by".
- Species rows: "Water bodies".
- Some labels were shortened (controls diff).
- Alt+H has a second "v7.1 words" page.
- The Ledger K filter cycles every kind (`LEDGER.KINDS`).
- The Live tab leads with the release clock and per-layer rows.
- The first-run status line puts the outcome first and the biome names last.
- Every registry set is one undo step, and undo re-applies the raws and jobs.
- The Panel keeps the selected control across redraws.

### Web

The page was rebuilt (web 2): 10 tabs, a Map canvas, `/map.json` and `/history.json`, and a Replay/Offline-sim pill.
The Controls tab has the new Aquarium section, and the page's Waters view has aquarium toggles (html:1482). `enable`
sent from the page now means everything on.

### Package and installation

- Install: unzip `hack/` into `DFHack/hack`, then type `enable seasonal-wildlife` once.
- There are no init lines. Remove `enable aquarium` and `seasonal-wildlife enable` from `dfhack.init` and
  `onMapLoad.init`.
- There are start-up warnings for old copies.
- A new world needs the "Seasonal Wildlife - Aquarium" mod ticked.
