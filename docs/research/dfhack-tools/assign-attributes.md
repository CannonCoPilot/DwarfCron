# assign-attributes (DFHack 53.16-r2)

Sources read: `scripts/assign-attributes.lua` (290 lines), `scripts/docs/assign-attributes.rst`,
`library/lua/argparse.lua` (`processArgs`), `library/lua/dfhack.lua` (script flags), `scripts/assign-profile.lua`, and
`library/xml/df.creature.xml`. Paths are relative to `/Users/nathanielcannon/Claude/GitRepos/dfhack-53.16-r2`.
Web doc: https://docs.dfhack.org/en/stable/docs/tools/assign-attributes.html. The stable site is built from 53.16-r2
and its text matches the local rst. The script is identical in `dfhack-latest`.

## What it does

It sets a unit's physical and mental attributes by **tier** (-4 to 4) instead of by raw value. Tier 0 is the race
median, and each tier is 250 points wide. Tags: fort, armok, units.

| Option | Source | Notes |
|---|---|---|
| `--unit <id>` | :245-251 | defaults to the selected unit (`dfhack.gui.getSelectedUnit(true)`, :151) |
| `--attributes [ NAME tier ... ]` | :258-283 | spaces around `[` and `]` are required. Names are upper-cased. Negative tiers parse correctly inside the brackets (argparse.lua:36-41) |
| `--reset` | :253-256, :197-208 | sets every attribute to tier 0 first |
| `--help` | :240-243 | prints the **old inline help** (:4-69), which shows single-dash forms |
| *(not in docs)* single-dash forms `-unit`, `-attributes`, `-reset`, `-help` | argparse.lua:44-45 | `processArgs` strips either `-` or `--` |
| *(not in docs)* module API `reqscript('assign-attributes').assign(attrs, unit_or_id, reset)` | :140-234 | `attrs = {STRENGTH=2, ...}`. This is how `assign-profile` uses it (assign-profile.lua:87) |

Valid names are the `df.physical_attribute_type` and `df.mental_attribute_type` enum tokens (for example STRENGTH,
AGILITY, TOUGHNESS, ENDURANCE, RECUPERATION, DISEASE_RESISTANCE, SPATIAL_SENSE). Invalid names and out-of-range tiers
print a yellow warning and are skipped (:219-232). They do not raise an error.

## How it works

- **Medians** (`generate_medians_table` :90-133): every attribute starts at 1000. The script then scans
  `df.global.world.raws.creatures.all[race].raws`, which holds the stored raw text lines (`current_definition`,
  df.creature.xml:1566), for `PHYS_ATT_RANGE` and `MENT_ATT_RANGE`, and takes the 4th number of each, which is the
  median.
- **Value per tier** (`convert_tier_to_value` :173-194): `value = max(0, median + 250*tier + rand(0..249)*sign)`. The
  sign is the tier's sign, or random for tier 0. Then `max_value = value + max(value, median)`, which is the training
  cap.
- **Writes** `unit.body.physical_attrs[ATTR].value/.max_value` and
  `unit.status.current_soul.mental_attrs[ATTR].value/.max_value` (:198-233).
- There are no hooks, timers or persistence of its own. The writes are one-shot, and they persist in the save as part
  of the unit.

## Gotchas

- **The median comes from the race-level raw text and ignores castes.** For a creature with caste-specific
  `*_ATT_RANGE`, the last matching line wins. If `creature.raws` is empty on a build, every median falls back to 1000.
  This was not verified on the 53.16 rig. The structured source is
  `caste_raw.attributes.phys_att_range[ATTR][3]` / `ment_att_range[ATTR][3]` (df.creature.xml:1106-1112, 7 values per
  attribute, index 3 being the median).
- There is no unit-type guard. It changes **any** unit, wild animals included. `--reset` and mental tiers dereference
  `unit.status.current_soul` with no nil check (:203, :225). A soulless unit raises a Lua error. Physical-only changes
  avoid that.
- Tier 4 is handled like any other tier (`median+1000..+1249`), not up to the 5000 maximum (:171-172). Values are
  floored at 0, with no upper bound.
- The values come from Lua's `math.random`, so they are not reproducible across runs.
- `assert(... tier >= -4 or tier <= 4)` (:175) is always true. The real range check happens at :215 and :223.
- The script header says `--@ module = true`, with a space. The flag parser accepts that (dfhack.lua:970-976), so
  `reqscript` works.

## Relevance to seasonal-wildlife and aquarium

- **A lever for predator-prey outcomes.** ECO found that non-BENIGN prey fight back: capybaras killed 5 of 5 wolves,
  and a buffalo killed a lion (memory "relation write needs non-BENIGN"). Changing STRENGTH, AGILITY, TOUGHNESS or
  ENDURANCE on placed units is a direct, per-unit way to tune who wins, without editing raws. Use the module API on
  units our tool placed: `reqscript('assign-attributes').assign({STRENGTH=2, AGILITY=1}, unit)`. Keep to physical
  attributes, so a missing soul cannot raise an error. Record the change in our ledger, because it persists in the save.
- **Better to compute tiers ourselves from `caste_raw.attributes`** if we need exact, caste-correct values. This
  script's raw-text median read is fragile (see Gotchas). Our tool already reads caste data such as body size
  (seasonal-wildlife.lua v6.4.1 notes), so the caste median is one more field to read.
- It is an armok change. Experiments that use it need their own control arm, because it changes the very combat
  results that the ECO relation tests measure.
- Aquarium plugin: no interaction.
