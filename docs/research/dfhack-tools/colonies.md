# colonies (DFHack 53.16-r2)

Sources read: `scripts/colonies.lua` (65 lines), `scripts/docs/colonies.rst`, `library/lua/gui/dwarfmode.lua`
(getCursorPos), `library/lua/dfhack.lua` (script flags), and `library/xml/df.event.xml`. Vanilla DF 53.16 raws were read
from the CrossOver install (`data/vanilla/*/objects/creature_*.txt`). Paths are relative to
`/Users/nathanielcannon/Claude/GitRepos/dfhack-53.16-r2`.
Web doc: https://docs.dfhack.org/en/stable/docs/tools/colonies.html. The stable site is built from 53.16-r2 and its text
matches the local rst. The script is identical in `dfhack-latest`.

## What it does

It lists, places or converts vermin colonies: ant hills, termite mounds and wild bee hives. These are not the
beekeeping hive *building*. Tags: adventure, fort, armok, map.

| Form | Source | Effect |
|---|---|---|
| `colonies` | :60-65 | prints `RACE at x, y, z` for each colony. Prints "There are no colonies on the map." to stderr when there are none |
| `colonies place [<CREATURE_ID>]` | :35-49 | creates a colony at the **cursor**. The default is `HONEY_BEE` |
| `colonies convert [<CREATURE_ID>]` | :22-33 | changes **every** colony on the map to that race |
| *(not in docs)* `colonies help` / `colonies ?` | :54-55 | help |

`CREATURE_ID` must be an exact, case-sensitive `creature_id` (`findVermin` :6-13). It is not checked to be vermin or
colony-forming. Any creature id is accepted. Colony-forming species in vanilla 53.16 raws (`[VERMIN_SOIL_COLONY]`):
**ANT, TERMITE, HONEY_BEE, BUMBLEBEE**. Only HONEY_BEE is `[ARTIFICIAL_HIVEABLE]`. HONEY_BEE and BUMBLEBEE also carry
`[COLONY_EXTERNAL]` and `[HIVE_PRODUCT]`.

## How it works

DF structures (df.event.xml):
- `df.global.world.event.vermin_colonies` (:223) and `df.global.world.event.vermin` (:222). Both are vectors of
  `df.vermin` (`event_verminst`, :113-130). `df.vermin`'s instance-vector is `world.event.vermin`, which is what
  `df.vermin.get_vector()` returns.
- `df.vermin` fields: `race`, `caste`, `pos`, `visible`, `countdown` (original name `fuel`), `item`, `flags`
  (`vermin_flags`: `already_deleting`, `is_colony`, `triggerable`, `is_roaming_colony`, :93-98), `amount` (the xml says
  10000001 means infinite), `population` (`world_population_ref`), `category` (`vermin_category`: Eater, Grounder,
  Rotter, Swamper, Colony, Triggered, Item, Sphere, FromColony; :100-111), and `id` (assigned during save).

`place_vermin` (:35-49) runs `df.vermin:new()` and sets `race`, `flags.is_colony = true`, `caste = -1`,
`amount = 18826`, `visible = true` and `pos`. It then **inserts the same object into both** `vermin_colonies` and
`vermin`. It leaves `category`, `population`, `countdown` and `item` at their constructor defaults.

`convert_vermin_to` (:22-33) sets, on every colony, `race = new`, `caste = -1`, `amount = 18826` and `visible = true`.

There are no hooks, timers or persistent state. Every write is direct and happens once.

## Side effects, gotchas

- **Permanent**: the new or converted colonies are saved with the map. There is no undo and no `remove` subcommand.
- **`place` needs a real cursor.** `guidm.getCursorPos()` returns the adventure look cursor, or `df.global.cursor`
  only when `cursor.x >= 0` (gui/dwarfmode.lua:41-49). Otherwise it fails with `qerror("Cursor must be pointing
  somewhere")`. In DF 53 fort mode the keyboard cursor is usually unset. A headless rig would have to write
  `df.global.cursor` first, or copy the 8 lines of `place_vermin` with an explicit position.
- **It cannot be imported.** The script has no `--@module` line, so `reqscript('colonies')` fails the module flag
  check (dfhack.lua:994-1000). Our code would have to copy the logic.
- A placed colony has **no world population reference** (`population` is left at its defaults), so it is not tied to
  any `world.populations.all` entry. Its `category` is not set to `Colony`, unlike colonies DF creates. How DF treats
  such a colony over time has not been verified.
- `convert` resets `amount` to 18826 on every colony, so it also refills depleted ones, and it reveals hidden colonies
  (`visible = true`). It does not touch vermin already out roaming from the old colonies (`category FromColony` /
  `is_roaming_colony`).
- `convert` to a non-colony creature id (for example `DRAGON`) is accepted without complaint, and the result is
  undefined.
- Cost: trivial, a single pass over the colony vector.

## Relevance to seasonal-wildlife and aquarium

- **Vermin census: colonies are inside `df.vermin.get_vector()`.** `place` inserts each colony into `world.event.vermin`
  as well (:47-48), and DF keeps its own colonies there too. A colony carries `amount = 18826` or more, so a raw sum of
  `amount` over the vector is dominated by any ant hill or bee hive nearby. `scripts/validate-full.py:6393` already
  excludes `flags.is_colony` and infinite amounts. **`scripts/alpha4_sec7_blocks.py:824-826` does not** (its `near()`
  sums `amount` over the whole vector). A colony within the 12-tile window would swamp the shore-vermin reading. Add the
  `is_colony` filter there.
- **Our vermin lever does not reach colonies.** seasonal-wildlife controls vermin through `world.populations.all`
  quantity (the VERMIN family roster, seasonal-wildlife.lua:2564-2566). Colonies, and especially script-placed ones with
  no population reference, are a separate source that our seasons and abundance cannot turn off. If the roster or a
  vermin family says "ants off", a colony will keep ants on the map. The roster could list colonies by race from
  `world.event.vermin_colonies` so the player can see them.
- **Reusable**: the `place_vermin` recipe (:40-48) is the minimal way to put a colony at a known position without the
  UI, with the extra step of setting `category = df.vermin_category.Colony` to match DF. `findVermin` shows the
  race-id lookup. Do not adopt the magic `18826`. Read the amount DF gives colonies on a real map instead.
- **Aquarium, indirectly**: the same `event_handlerst` struct (`world.event`, df.world.xml:518) holds
  `ocean_wave_makers` and `ocean_waves` (df.event.xml:228-229) and `dirty_waters`, "for making blood flow downstream in
  rivers" (:224). These are DF's own wave and river-flow event lists. They could drive where the plugin draws crests
  and flow, instead of inferring them from tiles.
