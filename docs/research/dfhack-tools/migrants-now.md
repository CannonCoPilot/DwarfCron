# migrants-now (DFHack 53.16-r2)

- Docs: https://docs.dfhack.org/en/stable/docs/tools/migrants-now.html (read 5 Oct 2026)
- r2 doc: `scripts/docs/migrants-now.rst`. It matches the web page: "only works after at least one wave of migrants have arrived naturally", "no migrants are actually guaranteed", and bare usage. No difference found.
- Source: `scripts/migrants-now.lua` (9 lines).
- Tags: fort, armok, units.

## Commands and options

The command is `migrants-now`, with no options. Arguments are ignored and there is no help handling in the source.

## How it works (the whole script, `:3-9`)

```lua
df.global.timed_events:insert('#',{
    new = true,
    type = df.timed_event_type.Migrants,
    season = df.global.cur_season,
    season_ticks = df.global.cur_season_tick+1,
    entity = df.historical_entity.find(df.global.plotinfo.civ_id)
})
```

It appends one `timed_event` (bay12 `plot_eventst`, `df.plotinfo.xml:228-237`; the type is `INFLUX`, `:216`) to `df.global.timed_events` (`df.game_v.xml:18-19`). The event is stamped with the player civ and the next season tick.

## Differences from `force Migrants`

The two tools do the same thing in slightly different ways.

| Aspect | `force Migrants` (`force.lua:47-58`) | `migrants-now` |
|---|---|---|
| `season_ticks` | `cur_season_tick` | `cur_season_tick + 1` |
| `feature_ind` | `-1` | not set (the struct default, 0) |
| `entity` | `findCiv('player')` → `historical_entity.find(plotinfo.civ_id)` | same |
| Checks | enum validation | none: no map/mode check, and a missing civ gives `entity = nil` silently |

- Neither difference is known to matter, but they are not identical.
- **A wrap-around risk (theoretical, untested):** at the last tick of a season, `+1` produces a `season_ticks` beyond the season's range, with `season` unchanged.

## Side effects, gotchas

- **The queue entry persists in the save until DF consumes it.** Repeated runs stack duplicate entries. The doc's "especially if you've just run this command a few times" suggests DF throttles or discards them.
- **DF's preconditions are hidden from DFHack.** The script cannot know about the documented "after one natural wave" rule, or any size, wealth or population-cap rules. The return code is always success.
- **Measured on our rig** (seasonal-wildlife `STATE.md` addendum 37, E22, 17 Sep 2026, CTRL year 2, seven dwarves, DFHack 53.16-r1.1, runs `E22-migrants-now/20260917-195259`):
  - 2 × `migrants-now` and 2 × `force Migrants` were all accepted (rc 0).
  - **No migrant reached the map in 36,000 ticks.**
  - Whether the wave was deferred or refused was not measured.
  - The script is unchanged in r2, so expect the same result.

## Relevance to our work

- **Not a lever for the test rig.** For more citizens, use the verified route in fort-load-levers: `dfhack.units.create`, the six placement writes and `makeown.make_own`.
  - If migrant arrival itself is the subject (for example, migrants walking past armed predators), first confirm the fort has had a natural wave. Then queue the event and allow at least a season. Treat "nothing arrived" as censored, not as a FAIL (experiment-readout-traps).
- **Probing why it fails is cheap:**
  - After running it, read `df.global.timed_events` back. Does a `Migrants` entry still sit there, or does it vanish without effect?
  - A queued entry that is never consumed would mean deferral. One that vanishes would mean refusal.
  - The read is one-shot and small, so it is safe even on the user's game. Our `e23b-probe-breach.sh:56-59` already shows the pattern.
- **Seasonal-wildlife interaction:** none in the source. It writes only the timed-event queue and touches no wildlife or population fields.
