# deathcause (DFHack 53.16-r2)

Sources read: `scripts/deathcause.lua` (177 lines), `scripts/docs/deathcause.rst`,
`plugins/lua/sort/deathcause_button.lua` (78 lines; registered at `plugins/lua/sort.lua:1320`), the `DEATH_TYPES`
table in `scripts/gui/unit-info-viewer.lua:113-170`, and df-structures (`df.incident.xml`, `df.d_basics.xml`,
`df.unit.xml`). Paths are relative to `/Users/nathanielcannon/Claude/GitRepos/dfhack-53.16-r2`.
Web doc: https://docs.dfhack.org/en/stable/docs/tools/deathcause.html. The stable site is built from 53.16-r2 and its
text matches the local rst. The script is identical in `dfhack-latest`.

## What it does

It prints one sentence describing how a creature died, for example "The X bled to death in year N, killed by the Y".
It is read-only. Tags: fort, inspection, units.

| Form | Source | Notes |
|---|---|---|
| `deathcause` | :166-177 | target is the selected unit (**a living unit works too**: "... is not dead yet!"), else the selected item, else the first `ANY_CORPSE` item on the tile of the item shown in the `ViewSheets/ITEM_LIST` sheet (:130-151) |
| selected `item_remainsst` (vermin remains) | :144-146 | prints only "The <race> died." |
| API `reqscript('deathcause').getDeathCause(unit_or_histfig)` | :154-160 | the only exported function |
| *(not in docs)* overlay `sort.deathcause_button` | deathcause_button.lua:7-76 | a "Show death cause" button with hotkey `CUSTOM_D` on `dwarfmode/Info/CREATURES/DECEASED`, **enabled by default** |

**Error in the docs**: the rst example calls `dc.getDeathCauseFromUnit(...)`, but that function is `local`
(:30). Through `reqscript` it is `nil`, so the example raises "attempt to call a nil value". Use `getDeathCause(unit)`.

## How it works

Unit path (`getDeathCauseFromUnit` :30-56), used when `hist_figure_id == -1`, which is the case for almost all wild
animals:
- `unit.counters.death_cause` (df.unit.xml:2880, `original-name='temporary_projectile_killcause'`) → text from
  `DEATH_TYPES`.
- `unit.counters.death_id` (df.unit.xml:2881, `kill_incident_id`) → `df.incident.find()` → `incident.event_year`, and
  `incident.criminal` (the killer's unit id) → the killer's race name, plus the killer's name if it has one.

Historical-figure path (`getDeathCauseFromHistFig` :108-120): it scans `df.global.world.history.events` **backwards
over the whole world history** for a `HIST_FIGURE_DIED` event with `victim_hf == id` (:96-105). It then reports
`death_cause`, `year`, `slayer_hf` and the weapon (from `event.weapon.item` or `shooter_item`, using the item
description if the item still exists, otherwise the weapon itemdef name, :60-93).

The incident struct (`df.incident.xml:99-138`, instance-vector `world.incidents.all`) carries more than the tool
prints: `type` (`incident_type.Death`), `victim`, `victim_race`, `victim_caste`, `criminal`, `criminal_race`,
`criminal_caste`, `site`, `subregion`, `layer`, `event_year`, `event_time`, `death_cause` and `witnesses`.

## Bugs and gotchas

- **Crashes on 3 death types.** `death_type` in r2 runs from NONE=-1 and OLD_AGE=0 up to 54 (df.d_basics.xml:12012).
  `DEATH_TYPES` covers only 0-51 (unit-info-viewer.lua:113-166, 52 entries, ending at FALLING_OBJECT). deathcause
  calls `DEATH_TYPES[cause]:trim()` with no fallback (:25), so **LEAPT_FROM_HEIGHT (52), DROWN_SELF (53) and
  EXECUTION_GENERIC (54)** raise "attempt to index a nil value". unit-info-viewer itself falls back to
  "died of unknown causes" (:168-170).
- A histfig with no `HIST_FIGURE_DIED` event passes `nil` into `getDeathEventHistFigUnit`, which raises an error
  (:117-118). A histfig whose unit no longer exists produces `qerror("Cause of death not available")` (:110-112).
- The unit path reads `counters.death_cause`. Its original name says it is a temporary projectile kill cause, while
  `incident.death_cause` is the recorded one. They can differ, and the incident is the more authoritative source.
- If the killer unit is no longer in `world.units`, the killer is silently left out (:45-51).
- The history scan is O(number of world events) for each call on a histfig, which is slow on old worlds. The unit path
  costs one hash lookup.
- No side effects, nothing persisted, no hooks.

## Relevance to seasonal-wildlife and aquarium

- **Use incidents, not deathcause, for predation counts.** The tool shows where DF records a kill on a wild animal:
  `victim.counters.death_id` → `df.incident.find(id)` → `criminal` and `criminal_race`. A single pass over
  `df.global.world.incidents.all` filtered on `type == df.incident_type.Death`, keeping `victim_race`,
  `criminal_race`, `death_cause`, `event_year` and `event_time`, gives a cheap, one-shot predator→prey kill ledger. That
  fits the "one-shot small reads only" rule for the user's game, and it would replace inferring kills from corpses
  (which deteriorate may delete). Still to verify on the rig: that wildlife-on-wildlife kills create a Death incident
  with `criminal` set, which is what the unit path assumes.
- **Tool removals look like deaths.** `fix/wildlife` kills on-screen stuck wildlife by `blood_count = 0`
  (exterminate.lua:55-58). By the code path this should read as a bleed death with no criminal, but that is not
  verified on the rig. Off-screen removals and agitation-rebalance culls use `vanish_countdown`. A kill census must
  exclude deaths without a `criminal` (or with death types BLEED or VANISH and no incident) before counting
  "predator X killed prey Y".
- If our harness ever calls `getDeathCause`, wrap it in `pcall`, because of the death-type crash above. The three
  missing types (leapt from height, self-drowning, execution) rarely apply to animals.
- The `sort.deathcause_button` overlay is a compact example of reading DF's native widget tree with
  `dfhack.gui.getWidget` / `getWidgetChildren` (deathcause_button.lua:31-57). It is relevant if our GUI ever needs to
  read DF's own Creatures lists.
- Aquarium plugin: no interaction.
