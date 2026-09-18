# Hunting- and war-trained animals in DFHack (reference, 17 September 2026)

Supplied by the user as a correction; field names verified against df-structures `df.unit.xml` (master).

**A hunting-trained animal is marked by its profession, not by `training_level`.**

| Purpose | Data |
|---|---|
| Species can be hunting-trained | caste raw flag `[TRAINABLE_HUNTING]` (`[TRAINABLE]` = hunting + war) |
| Individual is marked for training | a `training_assignment` entry (not yet trained) |
| Individual is hunting-trained | `unit.profession` or `unit.profession2` == `df.profession.TRAINED_HUNTER` |
| Individual is war-trained | `unit.profession` or `unit.profession2` == `df.profession.TRAINED_WAR` |
| Individual is ordinary-trained | `unit.training_level` at `Trained` or higher (animal_training_level: WildUntamed, SemiWild, Trained, WellTrained, SkilfullyTrained, ExpertlyTrained, ExceptionallyTrained, MasterfullyTrained, Domesticated) |
| Individual is tame | `unit.flags1.tame` |

DFHack's own checks (library/modules/Units.cpp): `isHunter()` tests exactly `profession == TRAINED_HUNTER || profession2 == TRAINED_HUNTER`; `isTrainableHunting()` tests the caste flag; `isTrained()` returns true for war/hunter first ("those don't have a training level") and only then looks at `training_level`.

Verified in df.unit.xml: `profession` (original name `type`) and `profession2` (`origintype`) are int16 `profession` enums; `training_level` (`training_status`) is an `animal_training_level` enum, init `WildUntamed`; `flags1.tame`; `flags2.roaming_wilderness_population_source` (`ROMAING_WILDERPOP`).

Minimal conversion of a selected eligible animal (DFHack Lua):

```lua
local unit = dfhack.gui.getSelectedUnit()
if not unit then qerror("Select an animal unit first.") end
if not dfhack.units.isAnimal(unit) then qerror("Not an animal.") end
if not dfhack.units.isTrainableHunting(unit) then qerror("Caste lacks TRAINABLE_HUNTING.") end
unit.profession = df.profession.TRAINED_HUNTER
unit.flags1.tame = true
```

Do not represent hunting training with a `training_level` value, and do not add a `training_assignment` (that marks an animal waiting to be trained).

## Why it matters for the wildlife tool

This is the only **per-unit** aggression lever found so far: the caste flags that give a hunting drive
(`LARGE_PREDATOR`, `HUNTS_VERMIN`, `DIVE_HUNTS_VERMIN`, `ROOT_AROUND`) are species-wide and not in the
per-unit add-caste-flag mask (that mask is the syndrome set: CRAZED, OPPOSED_TO_LIFE, NOFEAR, BLOODSUCKER,
MISCHIEVOUS ...). Whether a *wild, untamed* unit with `profession = TRAINED_HUNTER` behaves any differently
toward wildlife is unmeasured; it is an arm for E32 (mid-predator behaviour), alongside the in-memory
caste-flag flips.
