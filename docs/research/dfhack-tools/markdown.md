# markdown (DFHack 53.16-r2)

- Docs: https://docs.dfhack.org/en/stable/docs/tools/markdown.html (read 5 Oct 2026)
- r2 doc: `scripts/docs/markdown.rst`. It matches the web page: unit/item fields, append by default, `-o/--overwrite`, the two worked examples and the custom keybinding recipe. No difference found.
- Source: `scripts/markdown.lua` (142 lines). The default keybinding is at `data/init/dfhack.keybindings.init:40-42`. History: reinstated (`scripts/changelog.txt:692`); Ctrl-T added (`docs/changelog.txt:1425`).
- Tags: adventure, fort, items, units.

## Commands and options

```
markdown [<name>] [-o|--overwrite] [-h|--help]
```

- The output is `markdown_<name>.md`, or `markdown_<WorldName>.md` by default. The world name is translated, converted with `df2utf`, and has spaces replaced by `_` (`:9, :27`).
- `-o` opens the file with `'w'` instead of `'a'` (`:26`).
- Default key: **Ctrl-T** on `dwarfmode/ViewSheets/UNIT|ITEM` and `dungeonmode/ViewSheets/UNIT|ITEM`. It also appears in the DFHack logo menu, which lists the keybindings for the current focus.
- **Not in the docs:**
  - **The `<name>` is not sanitised**, so it can contain `/` or `..`. The path is relative to the process working directory, which is the DF root.
  - If both an item and a unit are selected, **the item wins** (`:86-93`).

## How it works (file:line)

**Item path** (`:86-92`):

- The heading is `dfhack.items.getDescription(item, 0, true)`.
- The body is **`df.global.game.main_interface.view_sheets.raw_description`**: whatever text the currently open item sheet holds.

**Unit path** (`:93-139`). This is UI automation:

1. It sets `df.global.gps.mouse_x/mouse_y` to hard-coded offsets from the right edge (Personality 48/68, Health 74, Health→Description 51/74; rows 11-17, with different values in adventure mode).
2. It fires `gui.simulateInput(screen, '_MOUSE_L')` three times so DF fills `view_sheets.unit_health_raw_str[0]` and `view_sheets.personality_raw_str`.
3. It then reads those vectors.

- This is the sanctioned replacement for the removed `Units::getPhysicalDescription` (`docs/changelog.txt:1302`: "navigate the unit info sheet and extract the description from the UI (see `markdown`)").
- **Header:** `getReadableName(unit)`, `cur_year - birth_year` and `getProfessionName` (`:60-64`). The age ignores `birth_time`, so it is off by one before the birthday.

**Text cleanup** (`reformat`, `:48-58`): `[B]` and `[R]` become paragraph breaks, `[P]` is removed, and `[C:f:b:br]` colour tags are stripped.

**Output:** each entry is written as `### title`, then `#### Description:`, then `#### Personality:` for units, then a closing `---`.

## Side effects, gotchas

- **It changes UI state.** It moves the mouse position and clicks through the unit sheet's tabs, so the sheet is left on Health→Description.
  - The clicks only land if the window layout matches the constants. Window size, interface scale or a DF UI patch break them silently: you get empty sections and no error.
  - This is the screen-check-traps class of failure.
- **The item text can be stale.** `raw_description` is the open sheet's buffer. If the item was selected some other way, it may hold the previous item's text.
- **"No selection" is not an error.** It uses `printerr` plus `return`, not `qerror` (`:70-79`), so `dfhack.run_command` and RPC see success with no file written.
- **Files persist and grow without bound** in the DF root (on the rig, inside the CrossOver bottle). It does not touch the save.
- It needs a loaded world: `world.world_data.name` is read at line 9 before any check.

## Relevance to our work

- **Low direct relevance.** No biome, flow or event code.
- **The one useful lesson:** DFHack has no API for a creature's physical or health description on 53.16. The only route is to drive the view sheet and read `main_interface.view_sheets.*_raw_str`.
  - If a seasonal-wildlife report or GUI wants DF's own prose about a wild animal, copy this approach. Then follow our screen-check rules: verify the tab text after the click, and never quote from memory.
- **Do not run it on the user's game unprompted.** It clicks their UI and moves their mouse state.
- **For rig evidence it is fragile but workable:** open a creature's sheet, run `markdown evidence-<run>`, and archive the `.md` with the run. Check the file is non-empty, because a mis-click yields headers only.
