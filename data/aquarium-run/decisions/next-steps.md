# Deliverable and next steps (7 Oct)

## Code review, what was fixed
- Plugin: disabling it leaked its whole texture set whenever no frame ran before the hooks came out (1 disable in 4 on the rig); the hooks now stay as pass-throughs until the plugin is unloaded, which waits for the render thread. `status` copied the render thread's plan across threads unguarded (a rare crash); now published under a lock. Plugin 6623060.
- Plugin: its `probe` debug command crashed DF on a creature's tile (fixed earlier tonight, af19a05). Command parsing is otherwise safe: DFHack catches exceptions thrown from plugin commands.
- Tool: each restore at the world unload now runs on its own, so one failure never leaves the others' raw edits in place (rc ebe5c5c). The water harness had gone stale on 4 Oct; repaired with B15 and C3 cases.
- Tests, all offline (host Lua): water 65/0, aquarium 416/0, web 459/0 (needs `MAP=1`), gui 0 fail.
- Found, not changed: `seasonal-wildlife enable` turns on every switch, including the opt-in ones (irruptions, your own livestock as prey, the nudge). That matches "defaults activate all features", but those three are built and never run on the rig on DFHack r2; they are first in the test plan below.

## The single plugin (proposed layout, ~5-6 days)
- One folder in the DFHack tree, `plugins/external/seasonal-wildlife/`: the C++ plugin, its Lua module (`hack/lua/plugins`), the tool's scripts (`hack/scripts`), docs, a README. No art ships: the aquarium mod is generated on the player's machine from their own DF sheets (Bay 12's art is not ours to redistribute).
- One command: `enable seasonal-wildlife` (synonym `seasonal-wildlife on`). In order: turns the water renderer on; saves "autostart" in `dfhack-config/seasonal-wildlife.json`; on a loaded fort, every feature and layer on with the roster preset; builds or refreshes the aquarium mod if it is missing or older than the plugin; prints one report (renderer, graphics mode, lower elevations, whether this world has the mod, and "new worlds: tick Seasonal Wildlife - Aquarium" when it does not). `seasonal-wildlife off` undoes the first three. The plugin turns itself on at start-up from the saved autostart, and every new fort gets everything on: no lines in the player's init files.
- Degrades without errors: Classic/ASCII (the renderer stands down, wildlife runs); another DF build or Linux (bed printing off with its reason, the rest runs; Linux needs its own build); another DFHack (the plugin does not load, the Lua water layers take over); a world made without the mod (the top water stays DF's).
- Work, in order: merge the two sources into one folder; CMake install rules; rename the command `aquarium-plugin` -> `aquarium` (alias one release); the plugin's Lua module (autostart, map-load bridge); make the engine enableable with the mod check; a start-up warning for old copies in `dfhack-config/scripts/` (they would shadow the new ones; your setup has them); package script (dll + Lua + scripts + README + checksums); docs; the test matrix below; gate the developer commands (probe, pantest, bedtest, composecheck debug, perf) behind a build flag.

## Testing and tuning the seasonal-wildlife features, in order
1. Install the packaged build on the rig and run a new fort for one game year with everything on, in saved chunks (the rig still hangs every 40-60k fast ticks): no errors, every layer active, frame cost logged.
2. Irruptions (PLAN Q40-Q43): cavern pressure, civ-race waves, agitation masks, never run live. Fort survival and wave sizes across 5 reps per arm, irruptions on vs off.
3. Your livestock as prey, and the nudge: pet and livestock losses per season, 5 reps per arm.
4. Water roster on real water: B15 changed what counts as a river, so lake species now go to lakes (Shortsling); C3 brooks (BROOK fort: no animal over 10,000 cm3 enters a brook); sponges (Learnedchanneled: clumps, nothing preys on them, they breed).
5. Leaders and panic, packs and the SNEAK bonus, solitary hunters' skill writes (Q11-Q13): the earlier skill-write result was p = 0.07; rerun at 5 reps per arm with the subject on the map in every rep (a receipt per rep).
6. Civ-race hunting and prey (Q14): first run on a fort next to a civ.
7. Validator: phase_v71 is a stub and ~140 claim ids are undefined; define them so every run above scores itself.
8. DFHack r2 changes the tool relies on (teleport occupancy, isCitizen excluding the dead, setPathGoal): one targeted check each.
9. Frame budget: plugin + tool on a 6x6 fort, wall time per frame with each on and off.
10. Tuning from your review of the Decisions section (tints, bed-art densities, sea colour, sponge clumps), then a release candidate.
