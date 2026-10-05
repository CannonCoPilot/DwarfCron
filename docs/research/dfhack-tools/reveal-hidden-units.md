# reveal-hidden-units (DFHack 53.16-r2)

Sources read: `scripts/reveal-hidden-units.lua` (30 lines), `scripts/docs/reveal-hidden-units.rst`, the `df.unit.xml`
flags1 bits, and the readers of the flag in `library/modules/Units.cpp`. Web doc:
https://docs.dfhack.org/en/stable/docs/tools/reveal-hidden-units.html. All paths are relative to
`/Users/nathanielcannon/Claude/GitRepos/dfhack-53.16-r2`.

## What it does

`reveal-hidden-units` takes no options or arguments, and the source parses none. It works in fort and adventure mode.
The whole tool is:

```lua
for _, unit in ipairs(df.global.world.units.active) do          -- :17
  if unit.flags1.hidden_in_ambush then
    unit.flags1.hidden_in_ambush = false
    count = count + 1
  end
end
```

It prints `Exposed N unit(s)!` or `No hidden units detected!`, but **only when `dfhack.is_interactive()`** (`:24-30`).
A call through `dfhack.run_script` or RPC from a non-interactive context prints nothing, which looks like an empty
result.

The web docs and the r2 `.rst` have the same substance. Both say "sneaking or waiting in ambush". The code touches one
bit only.

## Structures it reads and writes

- `world.units.active`, so inactive and off-map units (`units.all` minus active) are skipped.
- `unit.flags1.hidden_in_ambush` (DF `AMBUSH`, `df.unit.xml:1345`). This is the only write.
- It does **not** touch these related bits: `flags1.hidden_ambusher` (`MARAUDER_ACTIVE`, `:1349`),
  `flags3.just_sprung_ambush` (`:1431`), or anything to do with sneak skill or jobs.

What the bit controls, from DFHack's own reverse-engineered readers:

- **Visibility.** `Units::isHidden` (`Units.cpp:267-290`):
  - If DF's global `debug_showambush` is set, nothing is hidden.
  - In adventure mode, every unit except the adventurer with `hidden_in_ambush` is hidden.
  - In fort mode, hidden means `hidden_in_ambush && !isFortControlled(unit)`.
  - The arena hides nothing.
- **Speed.** `Units::computeMovementSpeed` (`Units.cpp:1505`, penalty at `:1632-1636`): while
  `hidden_in_ambush && !isMischievous`, speed gets `+2000 - 100*min(20, SNEAK skill)`. A hidden unit is slower unless
  its SNEAK skill is high.
- Other DFHack code that clears the same bit: `makeown.lua:149`, `fix/retrieve-units.lua:28`. `siege-engine.cpp:1349`
  skips targeting hidden units.

## Side effects, persistence, gotchas

- **One-shot.** There is no hook or timer. DF's own AI can put the unit back into ambush on a later tick (whether it
  does is not determined from source). The script does not stop it.
- **Persists.** The cleared bit is saved state.
- **Combat changes.** Revealing removes the sneak movement penalty and changes how the unit is perceived and targeted.
  It is **not** a view-only toggle.
- **Read-only alternative.** For viewing only, DF's global `debug_showambush` makes `Units::isHidden` return false for
  everyone without changing unit state. DFHack's check honours it (`Units.cpp:270`). DF's own renderer is assumed to
  honour it as well, since it is a bay12 debug global. That is unverified on our rig.
- **Cost.** One pass over active units. Negligible.

## Relevance to seasonal-wildlife

- **Conflict.** The ecology rulings of 1 Oct put SNEAK in force:
  - Solitary armed hunters get NATURAL_SKILL 10 in SNEAK, `stealth_slows 0` and AMBUSHPREDATOR
    (seasonal-wildlife.lua:61-64).
  - Hunting groups at or above `pack_sneak` (25 %) get SNEAK 10 (`:4176-4183`).
  Running `reveal-hidden-units` during a measured cell strips every ambusher's hidden state at once. That un-hides our
  predators, removes the sneak speed term and changes their hunt outcomes. **Never run it on a rig during an
  experiment.** If a user runs it in their own game, the ecology will look less stealthy for a while.
- **Reuse as a readout.** The same loop *without the write* is a cheap, one-shot metric: count units with
  `flags1.hidden_in_ambush` per race at the sample tick. This measures directly whether our SNEAK grant leads to DF
  putting hunters into ambush. Our tool does not read this bit today; grep finds no `hidden_in_ambush` in
  seasonal-wildlife.lua. Following the no-polling rule for the user's game, take it as a single read at the sample tick,
  on the rig only.
- **Speed confound.** The formula above means a SNEAK-10 hunter in ambush moves at +1000 against +2000 for an untrained
  one. Keep this in mind when comparing approach times between sneak and no-sneak arms.
- **Placed units.** Our placement does not set `hidden_in_ambush`, so a placed ambusher starts visible until DF's AI
  decides to hide it. If a "placed vs arrived" comparison involves ambush predators, record the bit at placement and at
  sampling.
