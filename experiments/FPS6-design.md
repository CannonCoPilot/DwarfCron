# FPS6 — world size and history length on fortress speed (design, 29 Sep 2026)

**Question.** Does the world around a fort cost it speed — its area, and how many years of history were generated —
when the fort itself is held to one standard: a 3x3 embark, 7 dwarves, the same biome rules?

**Why it might.** Fortress mode still keeps the whole world in memory: historical figures, entities, sites,
artifacts, the event log, armies moving on the world map. A bigger or older world is more of all of these. If any of
it is touched per tick (army movement, world-level scheduling, historical-figure bookkeeping), it costs every fort.
If none is, the world only shows in load time, memory and save size.

## Factors

| Factor | Levels | How set |
| --- | --- | --- |
| World size | SMALLER (33x33), SMALL (65x65), MEDIUM (129x129) | the preset's dimensions (`cx-embark params <preset> ...`) |
| History length | 5, 125, 500 years | `end_year` on the same call |
| World seed | 2 per cell | numeric seeds, fixed list |
| Probe cell | LARGE (257x257) at 125 years, 2 seeds | to see whether the trend holds past MEDIUM |

That is 9 cells x 2 seeds + 2 probe worlds = **20 worlds**. Two seeds per cell separate the factors from one world's
idiosyncrasy (where civilizations sit, what lives nearby); each world is played in **2 sessions**, which separate
world-to-world variation from session noise.

## Held constant

- **Embark:** a 3x3 at a tile chosen by one rule on every world, from `cx-lifecycle survey`: temperate
  shrubland, grassland or savanna; savagery under 33; not evil; no river, lake or ocean on the tile or its ring; no
  site on the tile; at least 5 of 8 neighbours the same biome. Among tiles that qualify, the one nearest the world's
  centre. The tile, its distance to the nearest civilization site and that civilization's size are recorded, since
  history changes who lives nearby.
- **Fort:** 7 dwarves, default provisions, seasonal-wildlife on (as FPS5b), `cx-load sustain` at every sample
  (no dwarf dies of thirst), fresh DF process per session with the restored save touched before the restart.
- **Machine:** the host's load is recorded at every sample; runs go overnight when other lanes are quiet.

## Measured

Per session, at load: load wall time, save folder size, DF footprint after load, and the world's scale read in one
probe — historical figures (all and alive), events, entities, sites, artifacts, armies and army controllers, world
units, region dimensions.

During one in-game season (100,800 ticks; process age was FPS5's question): the stopwatch rate (3 x 6 s) every 16,800
ticks, with FPS5's full reading at each sample. That covers citizens, wild units by layer, items, jobs and dead
citizens. It also covers DF's CPU cores, system share, IPC, footprint, resident and peak memory, page-ins, disk read
and written, wineserver CPU, and host load. Migrants, visitors, merchants and invaders are counted too, because
longer histories may send more of them.

## Analysis

1. Cell means of ms/tick, fit as `log(ms/tick) = a + b·log(world area) + c·log(1 + history years)` with world as the
   unit of replication (the two sessions averaged first), so b and c are elasticities with honest standard errors.
2. The same with the world-scale counts (live historical figures, armies, events) in place of the design factors:
   which one carries the effect, if any.
3. Load time, footprint and save size against the same factors: the costs a player pays once per load, not per tick.
4. The season curve's slope per cell: does an older or bigger world make the process age faster?

## Budget and risks

- **World generation:** about 3 to 4 hours (seconds for SMALLER at 5 years, tens of minutes for MEDIUM or LARGE at
  500). A pilot generates MEDIUM at 500 years first to time it and to test the site rule.
- **Embarks:** 20 x about 90 s.
- **Sessions:** 40 x about 8 minutes, roughly 5.5 hours.
- **Total:** about 10 hours, run after FPS5b.
- **Risks:** worldgen rejections at the larger sizes (the verb tolerates one rejection type; a reject costs a
  re-seed); no qualifying tile on a small old world (relax to 'nearest qualifying biome, any savagery under 50',
  recorded); a 6x6 or 4x4 default in presets (the embark verb sets 3x3 by `CX_EMBARK_SIZE=3`).
