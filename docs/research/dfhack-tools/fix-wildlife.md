# fix/wildlife (DFHack 53.16-r2)

Sources read: `scripts/fix/wildlife.lua` (202 lines), `scripts/docs/fix/wildlife.rst`, `scripts/exterminate.lua`,
`scripts/force.lua`, `scripts/internal/control-panel/registry.lua`, `library/modules/Units.cpp`, and df-structures.
Paths are relative to `/Users/nathanielcannon/Claude/GitRepos/dfhack-53.16-r2`.
Web doc: https://docs.dfhack.org/en/stable/docs/tools/fix/wildlife.html. The stable site is built from 53.16-r2 and its
text matches the local rst. The script is identical in `dfhack-latest`.

## What it does

It works around DF bug 12921: a wildlife group that fails to leave the map blocks every later wave. The tool finds
wildlife whose leave timer has run out, removes those units, and adds them back to their regional population count, as
if they had walked off the map.

### Commands and options

| Form | Source | Effect |
|---|---|---|
| `fix/wildlife` | :200-201 | removes every active wildlife unit whose `leave_countdown <= 0`, **immediately** |
| `-n`, `--dry-run` | :172 | list only (but see the dry-run bug below) |
| `-w`, `--week` | :173, `check_timeout` :84-93 | the first sighting records `cur_year_tick`. A later run removes the unit once 7 days (8400 ticks) have passed |
| `-q`, `--quiet` | :174 | prints nothing when nothing was affected |
| `-h`, `--help`, `help` | :171, :177-180 | help |
| `fix/wildlife ignore [unit_id]` | :182-199 | detaches the selected or given unit, so it stops blocking waves but stays on the map |
| *(not in docs)* module API `reqscript('fix/wildlife').free_all_wildlife(include_hidden)` | :107-116 | detaches **every** active wildlife unit. It backs `force Wildlife [all]` (force.lua:22-24) |

Control-panel entry (registry.lua:112-113): `repeat --time 2 --timeUnits days --command [ fix/wildlife -wq ]`. It is
**not** a default. The docs say wildlife is removed "after it has been stuck for 7 days". In practice the delay is
7-9 days, because the timeout is 7 days and the check runs every 2 days.

## How it works

### Selection (`is_active_wildlife` :100-105 plus `unstick_wildlife` :123-153)

A unit is a target when all of these hold:
- `not dfhack.units.isDead(u)` and `dfhack.units.isActive(u)`
- `dfhack.units.isWildlife(u)`, which means `unit.animal.population.population_idx >= 0`, not a merchant, not a forest
  visitor, and not fort-controlled (Units.cpp:601-607)
- `unit.flags2.roaming_wilderness_population_source` is set (df.unit.xml:1405)
- `unit.animal.leave_countdown <= 0` (df.unit.xml:2694, "once 0, it heads for the edge and leaves")
- not `flags1.caged` and not `flags1.chained`

"Stuck" is not detected. Any wildlife on its way out counts, including animals walking out normally. Without `-w`, the
tool also removes animals that would have left on their own a moment later.

### Removal (:141-146)

`exterminate.killUnit(unit, visible and nil or DISINTEGRATE)`:
- **off-screen** (based on `guidm.Viewport.get():isVisible`): `DISINTEGRATE` sets `animal.vanish_countdown = 1` and
  destroys the inventory (exterminate.lua:49-52, 97-102). There is no corpse.
- **on-screen**: the default `destroyUnit` sets `unit.body.blood_count = 0` plus `vanish_countdown = 2` as a fallback
  (exterminate.lua:55-58). The changelog says "kill them instead" (scripts/changelog.txt:460).

### Refund (`refund_population` :47-63)

For each population key (region_x, region_y, feature_idx, cave_id, site_id, population_idx), it scans
`df.global.world.populations.all`. The first entry that matches all six fields and has `quantity < 10000001` (that is,
not an infinite entry) gets `quantity = min(quantity + count, quantity_max)`. Units are grouped by the key `to_key(pop)`
(:95-98).

### `ignore` / `detach_unit` (:66-70)

It clears `flags2.roaming_wilderness_population_source` and `..._not_a_map_feature`, then refunds +1 to the unit's
population. The unit stays on the map.

### State and hooks

- `stuck_creatures[unit.id] = cur_year_tick` is kept **in memory only**. It is not persisted, and it is cleared on
  `SC_MAP_LOADED`/`SC_MAP_UNLOADED` (:11-19). Reloading a save restarts every 7-day clock.
- Year rollover is a heuristic (:78-79, :91-92): a timestamp later than the current tick and inside the last week of
  the year counts as expired.
- The tool has no timers or eventful hooks of its own. Repetition comes from the control panel's `repeat` entry.

## Side effects, gotchas, bugs

- **Bug: `--dry-run` still refunds populations.** The loop at :149-151 calls `refund_population` for every collected
  entry with no `dry_run` guard, and dry-run entries are collected (:137-140). So `fix/wildlife -n` adds quantity to
  `world.populations.all` every time it finds a candidate, while removing no units. `-n -w` also writes first-seen
  timestamps (the `check_timeout` call at :134 comes before the dry-run check).
- **`ignore` and `free_all_wildlife` double-count.** They refund +1 while the unit stays alive on the map. Our own
  measurement shows DF refunds a departing animal from its population reference *whether or not it still has the flag*
  (seasonal-wildlife.lua:3415-3420, E4-E9bc). So if an ignored unit later leaves, the population is credited twice.
- Every removal is permanent and lands in the save: units dead or vanished, populations increased (capped at
  `quantity_max`).
- With `-w`, an animal that walks out normally within 7 days never gets removed, which is the intended grace period.
  Without `-w`, the tool kills animals in the middle of a normal exit.
- Wildlife inside the viewport dies by blood loss. This shows up as a death with a corpse, and could be misread as a
  predation kill (see deathcause.md).
- Cost: one pass over `units.active`, plus one pass over `populations.all` for each distinct key. It is cheap.

## Relevance to seasonal-wildlife

- **Our placed and resident animals are invisible to it.** Headless placement clears
  `flags2.roaming_wilderness_population_source` (seasonal-wildlife.lua:3958-3960, memory "headless unit placement"
  step 3), and so does detaching a resident group (:3572-3573). Both fail `is_active_wildlife` (:104). The tool will not
  kill our animals, even when their `leave_countdown` reaches 0.
- **DF's own gated waves are its targets.** A DF wave whose `leave_countdown` has run out and that is still on the map
  will be removed and refunded. Our `sendoff` and scheduler cover the same case. If both run, the population ledger
  receives refunds that our tool did not make. Running `fix/wildlife` on a rig fort will move `populations.all`
  quantities that our STOCK and RESERVE ledgers track, and so will `fix/wildlife -n`, because of the dry-run bug.
  Treat it as a confound. Do not enable it from the control panel on test forts. Our README's "send off instead of
  fix/wildlife piling a new wave on the old" (seasonal-wildlife.lua:145-146) is the right stance.
- **Raising `leave_countdown` is the protection.** Our code that raises `leave_countdown`
  (seasonal-wildlife.lua:5942) keeps units out of its reach, because the target test is `leave_countdown > 0` → skip
  (:128).
- **Reusable**: `refund_population`'s six-field match (:51-57) is the canonical way to find a unit's pool entry from
  `unit.animal.population`. It agrees with our step 1, "copy a stocked pool entry's six-field reference". The pattern
  of a persisted timestamp plus a re-run (`check_timeout`) is weaker than ours, because its state is lost on reload.
- **`force Wildlife`** (force.lua:22-24) is the vanilla-adjacent "send a new wave now". It detaches all visible
  wildlife and refunds it, which double-counts against the live units. Our `call` verb should stay the way we trigger
  waves.
- Aquarium plugin: no interaction.
