# teleport (DFHack 53.16-r2)

Sources read: `scripts/teleport.lua` (41 lines), `scripts/gui/teleport.lua` (392 lines), `scripts/docs/teleport.rst`,
`scripts/test/teleport.lua`, the engine `Units::teleport` in `library/modules/Units.cpp:778-867`, and
`docs/changelog.txt` (53.16-r2 section, from line 73). Web doc: https://docs.dfhack.org/en/stable/docs/tools/teleport.html.
All paths are relative to `/Users/nathanielcannon/Claude/GitRepos/dfhack-53.16-r2`.

## What it does

`teleport [--unit <id>] [-x <x> -y <y> -z <z>]` moves one unit to a map position.

- With no `--unit`, it uses `dfhack.gui.getSelectedUnit(true)`.
- With no complete x/y/z, it uses the keyboard cursor (`guidm.getCursorPos()`) (`teleport.lua:36-37`).
- If x, y and z are not all given, the cursor is used for the whole position. A partial set is ignored.

Options the docs omit:

- `-showunitid` prints the selected unit's id, and `-showpos` prints the cursor position (`:19-20`, `:29-34`). Both are
  undocumented and are mentioned only in the error text.
- `utils.processArgs` accepts both `-unit` and `--unit`. The docs show both spellings.
- x, y and z arrive as **strings**. They still work, because DFHack's integer field write uses `lua_tointegerx`, which
  coerces numeric strings (`library/LuaTypes.cpp:123-130`).

The script is `--@module = true` and exports `teleport(unit, pos)`, which is just `dfhack.units.teleport(unit, pos)`
(`:8-10`). `gui/teleport` is a window that multi-selects units and calls the same API for each one at the mouse tile
(`gui/teleport.lua:353-358`). It filters out dead, inactive and **caged** units (`:12-26`).

The web docs and the r2 `.rst` have the same substance.

## How it works: `Units::teleport` (Units.cpp:778-867)

1. **Source tile.** `getPosition(unit)` resolves through a containing cage. If either source or target
   `Maps::getTileOccupancy` is null, it returns **false** (`:782-786`). A unit whose `pos` is off-map, such as a freshly
   `dfhack.units.create`d one at −30000, therefore cannot be teleported. This matches our headless-placement finding.
2. **Footprint.** `EQUIPMENT_WAGON` races occupy 3×3. Every other unit occupies 1 tile (`:790-805`).
3. **Shared-tile scan.** It builds the set of tiles still held by *other* active units. Each tile is put in the grounded
   set or the standing set according to `flags1.on_ground`. Caged units and in-flight projectiles are skipped because they
   do not hold occupancy (`:810-822`). The cost is **O(active units) per call**.
4. **Clear the source.** It clears `occupancy.unit_grounded` or `occupancy.unit` at the source, but **only if no other unit
   of the same kind remains** (`:825-832`).
5. **Projectile.** If the unit is a projectile, it clears `flags1.projectile` and unlinks its `proj_unitst` from
   `world.projectiles.all` (`:835-844`).
6. **Occupied destination.** If the destination already has a standing unit (`new_occ->bits.unit`), the moved unit is
   **forced prone**: `flags1.on_ground = true` (`:847-848`).
7. **Set the destination.** It sets `unit` or `unit_grounded` on the destination footprint (`:851-856`).
8. **Position.** It writes `unit->pos = target` **and `unit->idle_area = target`** (`:859-860`).
9. **Riders.** If the unit is ridden, every unit in `units.other[ANY_RIDER]` whose RiderMount relationship is this unit
   gets `pos` set as well (`:863-865`).

What it does **not** do:

- validate the destination (walls, open space, deep water, magma and hidden tiles are all accepted)
- touch `path`, jobs, `units.active` membership or `flags1.inactive`
- clear `on_ground` when the unit lands on a free tile, so a prone unit stays prone
- take the unit out of a cage (a caged unit's `pos` is overwritten while it stays caged)
- write any tile or block flags other than occupancy

### r2 changes: our rig ran r1.1 before 1 Oct

The 53.16-r2 changelog (`docs/changelog.txt:100-101`; commits `3a250e073`, `c54cd5f1b`, `86463ce1d`) records three changes:

- The full 3×3 EQUIPMENT footprint is now updated.
- Source occupancy flags are cleared **only when no other unit of the same kind remains**.
- The source is resolved through `getPosition`, and non-occupying units are skipped.

**Under r1.1, teleport always cleared the source tile's flag.** So it could wipe the occupancy bit of a second unit
sharing that tile, and DF would then let something else path or build onto it.

## Side effects, persistence, performance, failure modes

- **Silent failure.** The CLI ignores the boolean return, so an invalid target or source prints nothing.
- **Slow when prone.** The forced prone state is real gameplay state. `Units::computeMovementSpeed` adds +2000 when
  `on_ground` (`Units.cpp:1505`, penalty at `:1624-1625`).
- **Wanderers pinned.** `idle_area` is overwritten. That is harmless for wild roamers, but a station-keeping unit's
  anchor moves to the target.
- **Persistence.** `pos`, `idle_area` and the occupancy bits are saved state. The move persists.
- **Cost.** The full `units.active` scan per call is negligible for one unit, but it is O(N·M) if you loop over many
  candidate tiles.
- **Tests.** The only test (`scripts/test/teleport.lua`) checks that the position changes by +1,+1.

## Relevance to seasonal-wildlife

Our headless placement (`PLACE.one`, seasonal-wildlife.lua:3948-3970) makes six writes after `dfhack.units.create`.
For position and occupancy it does:

```lua
u.pos:assign(pos); u.idle_area:assign(pos)
df.global.world.units.active:insert('#', u)
if blk then blk.occupancy[pos.x % 16][pos.y % 16].unit = true end
```

Compared with `Units::teleport`:

- **Same core writes.** Both set `pos`, `idle_area` and the occupancy bit. Our version is correct for a non-wagon,
  standing, unridden wild animal. Our tile pickers (`groundTile`/`waterTile`, `:4372-4395`) already refuse tiles with
  `occupancy.unit` set, so we never need teleport's force-prone branch.
- **What we skip.** The `unit_grounded` case, the 3×3 wagon footprint, riders and projectile cleanup. None of these apply
  to fresh wild animals.
- **Possible simplification (untested).** After `units.active:insert`, set `u.pos` to the target and then call
  `dfhack.units.teleport(u, target)` with source equal to target. The source clear and destination set land on the same
  tile and leave `unit=true`, using DFHack's maintained logic instead of our hand-written write. The gain is small, so
  keep the direct write unless the occupancy rules change again.
- **Moving existing units.** We already use `dfhack.units.teleport` for this: `ecoPlaceNear` and `regroundNear`
  (`:4398-4420`) and `:6855`. This is the right call.
  - **Results gathered on r1.1 may carry the old source-clear bug** (a shared-tile flag wiped). Re-check any r1.1 finding
    that depended on tiles shared after a teleport.
  - Our loops call teleport only on tiles we pre-filtered as free, so the force-prone branch never fires. Moving a
    hunter onto an occupied tile would slow it (+2000 speed) and change the hunt measurement.
- **Learn.** DFHack's teleport does not check the walkability of the destination. Validation stays our responsibility,
  as `groundTile`/`waterTile` already do: floor or ramp, no tree, no magma, and flow ≥ 4 for swimmers.
