# region-pops (DFHack 53.16-r2)

Sources read: `scripts/region-pops.lua` (182 lines), `scripts/docs/region-pops.rst`, struct XML
`library/xml/df.wilderpop.xml` and `df.regionpop.xml`. Web doc:
https://docs.dfhack.org/en/stable/docs/tools/region-pops.html. All paths are relative to
`/Users/nathanielcannon/Claude/GitRepos/dfhack-53.16-r2`.

## What it does

The tool lists and edits the populations of the **current map's** wildlife entries (`df.global.world.populations.all`).
It is a Lua script with no hooks, timers or persistence of its own. Each call is a single pass.

| Command | Effect (source) |
|---|---|
| `list [pattern]` | All plant tokens, plus the creature tokens with at least one `flags.discovered` entry. Prints the **known** count (`:91-112`). |
| `list-all [pattern]` | Same, but lists every creature token and prints the **total** count. |
| `boost <TOKEN> <factor>` | `quantity = floor(quantity * factor)` on every finite record of TOKEN. `factor >= 0` is required (`:115-123`, `:141-144`). |
| `boost-all <pattern> <factor>` | Same, for every token where `string.match(token, pattern)` is true. |
| `incr <TOKEN> <amount>` | `quantity = max(0, quantity + amount)`. The amount can be negative (`:125-133`). |
| `incr-all <pattern> <amount>` | Same, by pattern. |
| anything else | Prints the embedded legacy help text (`:2-25`), not the .rst. |

### Differences between the docs and the code

- **Plants are edited as well.** The web and r2 docs both say `boost-all .* .5` halves "all creature" populations. In the code,
  `pops.any` holds both plant tokens (Tree/Grass/Bush entries) and creature tokens (`:57`). So `boost-all .*` also scales
  tree, grass and bush population counts.
- **Patterns are Lua patterns** (`string.match`), not regexes, and they match a substring anywhere in the token. `BIRD` matches
  `BIRD_*` and also any token that contains BIRD.
- `list` prints **every plant entry** whatever its discovered flag. `list_poptable(stat_table.plants, true, …)` sets
  `all=true` for plants (`:109`).
- **Shared namespace.** Plant `obj.id` and creature `creature_id` share one key space in `pops.any` (`:57`). If a plant
  token equals a creature token, the later entry silently replaces the earlier one.
- **Doc versions match.** The web docs and the r2 `.rst` have the same substance. The script's built-in help is older
  wording (`incr <TOKEN> <factor>`).

## How it works: structures

`world.populations` is a `wilderpop_handlerst`, whose `all` vector is DF's `play` list (`df.world.xml:521`,
`df.wilderpop.xml:31-33`). Each element is a **`local_population` (`wilderpopst`)**:

```xml
<int32_t name="quantity" original-name='number'/>
<int32_t name="quantity_max" original-name='max_number' since='v0.40.01'/>
<bitfield ... name='flags'>  discovered | extinct (NULLIFIED) | already_removed | need_offload
<compound type-name='world_population_ref' name='population'/>   region_x, region_y, feature_idx, cave_id, site_id, population_idx
```

The regional master row is a different struct: `world_population` (`regionpopst`, `df.regionpop.xml:14-34`), reached
through `population.population_idx`. Its counts are named **`count_min`/`count_max`** (DF `number`/`max_number`, init
10000001). They are not called quantity. **region-pops never touches the master row**. It writes only
`local_population.quantity`.

Its enumeration:

```lua
for i,v in ipairs(df.global.world.populations.all) do          -- :73
    local typeid = df.world_population_type[v.type]             -- Animal, Vermin, VerminInnumerable, ColonyInsect, Tree, Grass, Bush
    ... is_plant -> df.plant_raw.find(v.plant) else df.creature_raw.find(v.race)
```

- It groups records **by token only**. Every entry type (Animal, Vermin, VerminInnumerable, ColonyInsect) and every layer
  (surface region entries, and cavern/feature entries with `feature_idx`/`cave_id` set) lands in one bucket. `boost TROLL 2`
  therefore scales surface and cavern rows, and the Vermin rows of the same race, together.
- **Innumerable test:** `v.quantity < 10000001` is treated as finite (`:63`, `:117`, `:127`). The test is on the **current
  quantity**, not on `quantity_max`.
- **`quantity_max` is never read or written**, and neither are `flags.extinct`, `discovered` or `need_offload`.
- `df.plant_raw.find(id)` or `df.creature_raw.find(id)` returning nil (a stale raw) would raise on `obj.id` (`:80`, `:84`).
  There is no guard.

## Side effects, persistence, performance, gotchas

- **Persistence.** The edits are to live map-state entries, which are saved with the fort. Our Check 10 (16 Sep) found
  that DF does not rebuild `populations.all` from the master on load (see seasonal-wildlife below), so the edits survive
  a save and reload. Nothing is written to the world master.
- **Performance.** One linear pass over `populations.all`. Negligible.
- **Sentinel collision.** Neither `boost` nor `incr` clamps the result. Two cases:
  - A large boost or incr can push a finite entry to 10,000,001 or more. Every later run, including region-pops itself,
    then treats it as **innumerable** and stops editing it.
  - The int32 write path (`integer_identity_base::lua_write` in `library/LuaTypes.cpp:123-130`) casts without a range
    check, so huge factors can wrap.
- **Above the cap.** `boost` with a factor above 1 can set `quantity > quantity_max`. The tool does not raise
  `quantity_max`. What DF does with such an entry is untested on our rig.
- **Cuts that may not stick.** A reduction (`boost .5`, `incr -N`) is only as durable as DF's regrowth. We have measured
  DF **regrowing feature fish toward `quantity_max`**, so a region-pops cut on a regrowing population drifts back.
- **No extinct flag.** `incr` to 0 leaves `flags.extinct` false.
- **Not a module.** The script has no `--@module` guard. `reqscript('region-pops')` runs the main body with no args and
  prints help, so its functions cannot be imported cleanly.

## Relevance to seasonal-wildlife

Our tool (`/Users/nathanielcannon/Claude/Projects/seasonal-wildlife/scripts/seasonal-wildlife.lua`) works on the same
vector but is stricter in every respect.

| Point | region-pops | seasonal-wildlife |
|---|---|---|
| Innumerable guard | `quantity < 10000001` | `pop.quantity_max >= INNUMERABLE` → skip (`:357`, `:932`). This is safer: the guard does not move when quantity is edited. |
| Scope | Token, all layers and types merged | `managedPop`: type in POP_TYPES, back-ref region in this embark's region set, layer filter (`:925-935`) |
| Raising quantity | Leaves `quantity_max` alone | Raises `quantity_max` to `q` whenever `q > quantity_max` (`:2394`, `:2418`, `:2538`, `:2925`), so DF's regrowth target follows the edit |
| Zeroing | `quantity = 0` only | `quantity = 0` **and** `flags.extinct = true`, two barriers (E8: either one stops a draw) (`:2426`, `:2454`, `:2918`) |
| Master rows | Untouched | Untouched by quantity edits. The master is used as the worldgen default baseline (`:328`) |

What we can take from it:

- **Reuse.** The `enum_populations` loop is a minimal, read-only diagnostic. `region-pops list-all <pat>` is safe to run
  by hand on the rig as an independent cross-check of our STOCK/RESERVE numbers. Note that it sums all layers and types
  per token, so compare it against our per-token sum over all layers, not against one layer.
- **Conflict.** Running `region-pops boost-all`/`incr-all` while seasonal-wildlife is enabled works against our ledger:
  - It edits entries we have zeroed for out-of-season keys, which un-zeroes them but leaves `extinct=true`, so they still
    cannot draw.
  - It edits entries whose snapshot we hold in RESERVE, so the remembered value and the live value disagree. The next
    season turn then restores our snapshot over the user's edit.
  - It also scales plant entries.
  The fix is to document "do not combine", or detect the drift (live quantity different from the expected value) and log it.
- **Learn.** region-pops' approach of multiplying `quantity` without touching `quantity_max` is the naive model. Our
  regrowth finding is why we keep `quantity_max` in step: an entry boosted above its max, or cut below it, is a different
  thing to DF's regrowth than one we set consistently.
