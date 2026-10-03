# Aquarium pre-flight review (desk, 2 Oct 2026, no rig touched)

The generator's raws and pages (sw-wt/rc `tools/aquarium/make_aquarium_mod.py`, `scripts/seasonal-wildlife-aquarium-gfx.lua`,
committed `mods/seasonal_wildlife_aquarium/`) were read against DF 53.16's own vanilla graphics on disk
(`$DF_DIR/data/vanilla/vanilla_environment/graphics/*.txt`, `images/*.png`), the rig's installed copies, the Workshop mods in the
user mods folder, and DFHack 53.16-r2's source. Read-only throughout.

## Fixed (proven from files) — sw-wt `v7.1-rc` 100f325

1. **A preset change never reached a world made with the mod.** DF copies a world's mods into
   `<user dir>/data/installed_mods/<id> (<numeric version>)/` when the world is created and loads that copy ever after:
   the rig has `data/installed_mods/seasonal_wildlife_aquarium (1)/` dated 14:24, four minutes after the mod (14:20), and
   DFHack's `script-manager.lua` (`get_mod_paths`) takes active mods' `object_load_order_src_dir` from there. `aquarium
   install <preset>` and the desk generator wrote only `mods/`, so T1/T2/T3's preset comparisons (vanilla v aquarium v
   clear) would all have shown the same pages, and `restore` would have restored nothing. Now both refresh every installed
   copy whose `info.txt` carries the mod's ID (byte-identical 10 files; `--no-installed` to opt out at the desk); `uninstall`
   never touches them; `aquarium status` prints the copy the loaded world came from and its preset. Tests: harness 96/0
   (+4), test_generator 0 failures (+3), web verbs 450/0, gui 0 fail, luac53 + luacheck clean. Doc section 2.4 updated.

## On the rig now (not code defects; the driver's SETUP rows catch each)

2. **Stale install.** Both `mods/seasonal_wildlife_aquarium/info.txt` and the installed copy carry
   `[NAME:Seasonal Wildlife: Aquarium]` (the repo changed it to a dash at 14:43). DF reads a token up to the colon: the
   genworld log names the mod "Seasonal Wildlife". Cosmetic (worlds match by ID and version). Cleared by the next
   `aquarium install` once 100f325 is deployed.
3. **Not deployed.** `sw-aquarium-watch.lua` is absent from `dfhack-config/scripts` (T4 needs it), and the deployed
   `seasonal-wildlife-aquarium.lua` predates 100f325. `aquarium-run.py --deploy` does both (deploy-tool + the watch script).

## Verified correct

- **Token names:** all 1,042 mod bindings (14 `UNDERWATER_n[_LABEL]`, 512 `RIVER_TO_*`, 512 `BROOK_TO_*`, 4
  `FLOW_WATER_MIST`) exist in vanilla and each points at exactly the cell vanilla uses (page mapped, column 0/2 -> 0/1 on
  `SW_AQ_LIQUIDS`, column 2 -> 0 on `SW_AQ_MIST`): 0 mismatches, 0 duplicate keys.
- **TILE_GRAPHICS syntax** matches vanilla field for field: 4 fields for LIQUIDS, `:variant:frame` for RIVER/BROOK_TO,
  `:frame` for FLOW_WATER_MIST. The Workshop mod *Flowing Water* (3419529410, installed here) re-binds `BROOK_TO_*` /
  `RIVER_TO_*` from a mod with the same syntax, so "a later mod's TILE_GRAPHICS overrides vanilla" is used in the wild.
- **Page dims:** raws 64x224, 4 x 512x256, 32x128 = the PNG sizes in both rig folders; no binding outside its page.
- **info.txt:** the same field set as `vanilla_environment` and the Workshop mods; ASCII; LF; first line of each raw = its
  file name.
- **Load order:** region10's mod list has `seasonal_wildlife_aquarium@1` 26th of 26, after `vanilla_environment@5301`
  (`data/logs/aqua-genworld.log`), so its bindings win.
- **Pixels on the rig:** water alpha 150..90 per level = stamp `aquarium`; depth digits kept at 255; flows 64 -> 48; mist
  199 -> 149 with the tint.

## Likely to fail or look wrong in game (not provable from files; the driver measures each)

- **Shore rims (T1).** `UNDERWATER_EDGE_*` (8 tiles, LIQUIDS columns 4-6) are not re-bound. Their alpha tops out at 179,
  exactly vanilla's level-1 water, so they were drawn to blend with shallow water; under the mod level-1 water is 90
  (aquarium) / 50 (clear), so a rim 2-3.5x denser than the water beside it is likely. Look at the shorelines in
  `t1-*-lake-boxes.png`. Fix if seen: re-bind the edges with alpha x A1/179 (extend `SW_AQ_LIQUIDS` to columns 4-6).
- **River animation thinned (T1).** The streaks are the only river/brook animation and the presets scale them to 0.75
  (alpha 48) / 0.5 (alpha 32). If `t1.river.streaks_animate` passes on vanilla but fails on aquarium, set `flows` to 1.0
  (section 2.1 already says the streaks are not what hides the bed).
- **Mist coverage.** The exe has 10 `FLOW_*` tokens and `FLOW_WATER_MIST` is the only water mist; `flow_type` has two:
  `Mist` (MIST_WATERFALL) and `Steam` (MIST_WATER). Files cannot say which DF draws with `FLOW_WATER_MIST`. The overlay's
  `scanWaves`, `aquarium probe` and `sw-aquarium-watch` count `Mist` only, never `Steam`: if this build's waterfalls make
  `Steam`, probe will say 0 mist. The driver's finder counts both and spawns one of each side by side
  (`mist.drawn.Mist` / `mist.drawn.Steam`).
- **Mist "animation" is density, not a loop.** The four mist frames cover 577/353/232/95 px (mean alpha 112/69/45/18):
  density tiers. Mist changes only as a flow decays and drifts, so it must be captured unpaused and fresh (the driver
  does); at x0.75 the thinnest tier (mean 14) is close to invisible.
- **Deep water needs a lower level drawn (T2/T3).** A translucent `UNDERWATER_7` over an open water cell shows whatever
  DF composites beneath it: nothing unless *lower elevations shown* >= 1 (setup row `setup.lower_elevations`).
- **Reload v restart.** Whether DF re-reads changed tile pages on title -> load inside one process is unknown;
  `--restart-escalate` restarts DF once if the aquarium arm shows no change and says which it was.
- **No load-order guard in info.txt.** `[REQUIRES_ID_BEFORE_ME:vanilla_environment]` is absent: harmless for region10
  (order proven above), recommended before release so a player's mod list cannot put vanilla after it. Not changed now:
  info.txt is part of version 1, which region10 already holds.
- **Waves:** no `FLOW_*` token exists for OceanWave/SeaFoam, so DF draws nothing for them; only the overlay can (T5).
