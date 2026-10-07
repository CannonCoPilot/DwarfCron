# Seasonal Wildlife 7.2 package: rig install and checks (7 Oct 2026)

Package: `sw-wt/plugin/plugin/dist/seasonal-wildlife-7.2.0-dfhack-53.16-r2-c740264d.zip` (branch `v7.2-plugin`,
seasonal-wildlife repo). Rig: the user's DF 53.16 Steam + DFHack 53.16-r2 under CrossOver; RPC listened on 5555 this
session.

## What was changed on the rig

- Installed into `DFHack/hack/`: `plugins/seasonal-wildlife.plug.dll`, `lua/plugins/seasonal-wildlife.lua`,
  `scripts/seasonal-wildlife*.lua|.html`, `scripts/gui/seasonal-wildlife.lua` (cmp-identical to the zip).
- The README's upgrade steps, with everything backed up first in `backup/` beside this file:
  - removed the old copies in `Dwarf Fortress/dfhack-config/scripts/` (the six `seasonal-wildlife*` files and
    `gui/seasonal-wildlife.lua`), each `cmp`-checked against its backup before removal;
  - removed `DFHack/hack/plugins/aquarium.plug.dll`;
  - commented out `enable aquarium` (dfhack.init) and `seasonal-wildlife enable` (onMapLoad.init).
- `dfhack-config/seasonal-wildlife.json`: autostart true (left on).
- The Aquarium mod in `mods/` was rebuilt: version 1 -> 2 (sponge castes), generator build 1.
- No save was written. Autosave restored to SEMIANNUAL at every stop. DF is left at the title with the plugin on.

To undo: delete the package files above and the json, then copy `backup/` back to the same places.

## Checks

| # | Check | Result |
|---|---|---|
| 1 | Start with the package beside the old install | The start-up names the old dll and all seven shadowing copies (stderr.log). |
| 2 | `enable seasonal-wildlife` with the old copies still shadowing | Renderer on; "the script DFHack found is too old for this plugin" and the list of copies to delete. No autostart written. |
| 3 | Clean start (after the upgrade steps) | No warnings; plugin loaded, not enabled (no autostart yet). |
| 4 | `enable seasonal-wildlife` at the title | 3.7 s: mod rebuilt (14 files in 3.5 s; the installed copy refreshed), report, autostart saved. |
| 5 | Load a known fort (LAKE_RIVER) | Renderer drawing (depth on); the fort's 7 jobs scheduled. |
| 6 | Restart DF | Autostart: plugin enabled at start-up without a command. |
| 7 | Load BROOK | **FAILED: "Failed to find compatible mod: Seasonal Wildlife - Aquarium 1.0".** See below. Fixed; after the fix BROOK loads, draws, 7 jobs. |
| 8 | Forced rebuild after the fix (`seasonal-wildlife aquarium install`) | The version 1 copy took 12 files; its info.txt untouched; its stamp keeps version=1. BROOK loads. |
| 9 | `aquarium probe` (release build) | "a developer command; this build leaves it out". |
| 10 | `seasonal-wildlife off` on BROOK | Writes restored (59 + 4 + 1882), renderer off, autostart false, 0 jobs. |
| 11 | `seasonal-wildlife on` on BROOK | Every switch on (20/20), mod up to date, renderer drawing, autostart true, 7 jobs. |
| 12 | Load a fort the tool never ran on (AQ2_LAKE) | Site config created (enabled, full_enable_roster), 7 jobs, renderer drawing, with no command. |
| 13 | dll removed, `enable seasonal-wildlife` | The script's own enable ran: "water renderer: not available: the plugin is not installed; the Lua water layers stand in". The autostart line was misleading ("on"); fixed to "needs the plugin". |
| 14 | Crash logs | None new (last 6 Oct 23:35). |

Not run live: Classic (ASCII) mode, another DF build, the "dll present but did not load" message, a texture-leak
cycle count (the set_enabled code is the 7 Oct review's, unchanged).

## The bug found (check 7)

The rebuild in check 4 refreshed `data/installed_mods/seasonal_wildlife_aquarium (1)` with version 2's info.txt, so
DF no longer found a version 1 mod for worlds made with it. The refresh had this bug since mod version 2 (5 Oct);
the package's automatic rebuild is what reached a player's worlds with it. The copy was restored to the version 1
text (byte-identical to the 2 Oct copy in `data/aquarium-run/20261002-211755-dry/fake_user`), and the installer was
fixed in both generators (seasonal-wildlife 30b31cc): an older copy keeps its info.txt and its stamp's version. The
two harnesses now check this and fail on the old code.
