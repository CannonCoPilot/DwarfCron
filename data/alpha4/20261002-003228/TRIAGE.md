# Alpha Four round 1: triage of the 19 ANOMALY steps (desk only)

Round `20261002-003228` (RinghatchetsReady, region9, DFHack 53.16-r2), seasonal-wildlife v7.1 @ e16eef2.
No rig use: nothing deployed, nothing merged into v7.1, nothing pushed.

- **Tool fixes:** branch `v7.1-a4fix` in worktree `/Users/nathanielcannon/Claude/Projects/sw-wt/a4fix`. There are 11 commits on e16eef2, one per logical fix.
- **Driver and page fixes:** DwarfCron `Dev` commit `61130b1`. It changes `scripts/alpha4-run.py`, `.claude/scratch/gen_alpha4.py` and the regenerated `.claude/scratch/alpha4-walkthrough.html`. The page is not republished.
- **Checks on every tool commit:**
  - `luac53 -p` passes on all four files.
  - luacheck is at its baseline: engine 33, gui 3, web 0, controls 38. The warning kinds are unchanged.
  - The offline GUI harness gives 0 fail.
  - The offline web harness gives 361 pass and 63 fail, the same as unchanged e16eef2. Its 63 failures are stale "no map loaded" guards.

Classes:
- **TOOL**: a tool bug.
- **DRIVER**: an `alpha4-run.py` check bug.
- **PAGE**: a page claim that v7.1 does not make, by ruling or design.
- **GAME**: DF-native behaviour.

## The 19 steps

| step | class | cause (file:line at e16eef2 unless noted) | fix | rig re-check |
|---|---|---|---|---|
| 1.2 | TOOL | `Detail:refresh` appended the `v7:` facts line after the history rows (gui/seasonal-wildlife.lua:2685). BARK_SCORPION_MAN's eats and eaten-by lists wrap to about 12 rows, so the line fell below the 20-row facts list. | a4fix `87ca63c`: the line is inserted before `eats`. | yes, `1.2` |
| 1.4 | DRIVER + TOOL | DRIVER: 1.4 runs before any `roster build`, so the readout correctly said `apex scheduler: no decision yet`. TOOL (latent): `PNL.TOP.roster` printed the state key `apex:land` cut to 8 cells (`apex apex:lan`) and looked the target up under the whole key, so every layer read target 0% (gui:2073-2075). | a4fix `700d509`: the row reads `apex     land  present P% (target T%)`. The driver accepts `no decision yet` before a build. | yes, `1.4` |
| 1.5 | TOOL | `refreshPanel` kept the cursor by row number (gui:2368-2376). The first Enter (Grazers off) re-wrapped the extinct status readout, and the second Enter flipped **Roles**, the next row down. 6.18 confirms it: `extinct.roles` was changed from its default. | a4fix `1a3038a`: the cursor is kept by control identity (`PNL.rowId`). | yes, `1.5` |
| 1.13 | PAGE + DRIVER | The tool prints `apex-state apex:land ...`, which matches docs/v7.1/roster.md:140 (`apex-state <tag:layer>`). The page and driver expected `apex-state land`. `groups=0 presence=0%` straight after `now` is the previous scheduler pass, not broken tracking: 3.10 later read `apex:land groups=1 units=3 presence=100%`. Hidden tool bug: `undo` said "undid: apex target land 25%" but restored nothing of `cfg.roster`, because `UNDO.FIELDS` lacks the v7.1 tables (engine:1107-1109). | Page and driver in `61130b1`. Undo fixed in a4fix `a138013`. | yes, `1.13` |
| 3.10 | DRIVER (+PAGE) | Same key as 1.13. Presence tracking works: land and water both read 100% with groups=1. | `61130b1` | yes, `3.10` |
| 2.4 | TOOL | The registry label "Drawn groups leave with their leader" (36 characters) drew as `Drawn groups leave with their~` in the Panel's 30-cell label column (controls:112, `PNL.fit`). The same problem hit `v7.seasons_own` (33) and `v7.scav_ext` (34). | a4fix `c97af89`: the labels are now "Groups leave with their leader", "Seasons override NO_<season>" and "Scavengers wade/swim/fallback". Driver and page updated. | yes, `2.4` |
| 2.12 | DRIVER + PAGE (+TOOL, minor) | DRIVER: the regex `water layer on \(follows the map\)` did not match the actual `(follows the map: a wet map edge)`. PAGE: on a fresh fort the first-open preset turns every present layer on and logs it as kind **build**, `layers turned on: ... water` (engine:3671, 3687). autoLayer's "water layer on by default" line only appears when auto itself turns the layer on. TOOL: the reason text came from `CACHE.watLayerWhy` left over from an earlier map, because `CACHE.drop` never cleared it. | a4fix `44cd18b` (drop the reason with the map). Driver and page in `61130b1`. | yes, `2.12` |
| 3.8 | GAME + DRIVER (one open) | DRIVER: the driver jumped the calendar to 2,400 ticks before the boundary. It then judged every unit made after the jump against **Summer's** roster. **HUNGRY_HEAD** is a Spring-only species (3.2-seasons: `+` in Sp only). Thirteen consecutive ids (13012-13024) in cavern 2 were adopted as natives by the cavern gate (`cavern2:HUNGRY_HEAD x4 gated ... flock led by #13024`). This is a DF-native cavern wave, very likely before the flip (the tool draws nothing in the caverns). The roster gates arrivals, not residents: a group that arrived in season stays until it leaves, and no ruling asks otherwise. **FISH_PIKE #13004** is still open: it has the water feature key, `water:FISH_PIKE` is out of season in Summer, while the land key `FISH_PIKE` was promoted for Summer by exhaustion (`FISH_PIKE (for water:FISH_CARP)`). Probe P1 below decides it. | The driver now steps to the flip, records the flip id, and judges each arrival in the season it arrived in, with its origin. | yes, `3.8` and probe P1 |
| 3.11 | PAGE + DRIVER | `ROSTER.exhaustCheck` skips any key whose stock the player set to 0 (engine:2958, `cfg.stock[r.key] ~= 0`). The design comment at engine:2930 says "A stock the player set to 0 is a choice, not exhaustion". The driver also picked BIRD_OSTRICH, which was already exhausted and replaced this season (`GIANT_HEDGEHOG (for BIRD_OSTRICH)`). So 0 new replacements is correct. | The driver picks a species not yet exhausted, empties its region entries in Lua, runs `exhaust now`, then restocks. The page says how exhaustion is made. | yes, `3.11` |
| 3.12 | PAGE + DRIVER | The spill works as designed. Spring's `OTTER_MAN` borrow was given back at the change. The pool was still under 3 drawable species, so it borrowed again **for Summer** (`borrowed: water:SNAPPING TURTLE (pool, Summer)`). The page's "(nothing borrowed)" ignores the re-borrow. The driver's regex (`borrowed the season`) matches no text the tool prints. | The driver checks the ledger line "given back at the season change" and that no past season is still borrowed. The page is updated. | yes, `3.12` |
| 4.17 | DRIVER | `\bSWV_[A-Z]+\b` stops at the `_` in SWV_GROUND_BUG, SWV_FLYING_INSECT, SWV_SMALL_BIRD, SWV_SMALL_MAMMAL and SWV_SMALL_FISH, so it counted 5. The tool lists **10** classes (SWV_OTHER has 0 members on this embark). The page is right. | `[A-Z_]+` | yes, `4.17` |
| 5.10 | DRIVER + PAGE (+TOOL readout) | DRIVER: `crazed.*on 10%` did not match the column-padded `crazed    on   10%`. PAGE: no "tokens on living units" row existed. The cavern line only carries `tokened N`, and docs/v7.1/irruption.md:282 promises only that. This round's wave was OLM_GIANT, a non-civ predator, so it carried 0 tokens by R10. | a4fix `a3a79b8` adds the row, so a tester can check R10: `tokens on living units (N alive, W wave(s)): crazed 1, ...; champion C`, or "none" for a predator wave. Driver regexes are now `\s+`. | yes, `5.9,5.10` |
| 5.12 | DRIVER | `cool all` worked: the cavern row went from `cooldown 30.0 d` to `quiet`. The check `cooldown \d` matched the config line `end: ... cooldown 30 d then: leave`. This is not the store mismatch the coordinator suspected. | The regex is anchored on the cavern row. | yes, `5.9,5.12` |
| 5.16 | DRIVER | The tool prints `On the map now: land 23  water 33  cavern 31` with two spaces between fields. `deep row in groups layers: False` is the pass condition. | `\s+` | yes, `5.16` |
| 6.3 | TOOL (most likely; re-check) | Shift+Right stepping 4 to 14 is what the page promises ("→ adds one, Shift+→ ten (clamped 1-20)"), and the driver passed it. The real failure was **Land pattern** burst, then Shift+Enter, still burst. Shift+Enter calls `act_panel_step(-1)` on the selected row (gui:426). After the Enter, the Limits readout redrew and the cursor came back by row number. Same root cause as 1.5. | a4fix `1a3038a` | yes, `6.3`. If it still fails, run probe P3. |
| 6.8 | TOOL + DRIVER | TOOL, three causes: (a) a Panel set goes through `controls.set`, which runs a console verb, and console verbs push no undo step. Only `Win:save`, `roster` edits and the registry's Panel and config paths did (controls:745-772). So Z undid three older edits (12, 11, 10) and stoop chance stayed at 63. (b) `UNDO.FIELDS` lacks hunters, roster, extinct, irruption, vermin_eat, scavenge, v7, realm and perf. (c) Neither undo path re-applied the raws. DRIVER: 20 K presses stopped before `irruption`; there are 24 kinds. | a4fix `a138013`: `set()` pushes one step unless the verb pushed its own, `FIELDS` covers v7.1, and `UNDO.after` re-applies. The driver now loops 40 times and the page kind list is updated. | yes, `6.8` |
| 6.10 | DRIVER (cascade of 6.8) | The driver expected `get` to return 60, assuming 6.8 had undone its sets. It read 63 because of the 6.8 tool bug. list, set and refuse all behaved. | The driver reads the value first. It also checks that `list` prints a false as false. | yes, `6.10` |
| 6.13 | DRIVER + TOOL | DRIVER: there are two spaces before `kind=` in `shown  kind=irruption`. TOOL: the registry set pushed no undo step, so `undo` took back `aquatic FISH_LAMPREY_SEA apex` instead. This is the same tool bug as 6.8. | `61130b1` and a4fix `a138013` | yes, `6.13` |
| 6.19 | TOOL | The Panel row read `Fixed cap 3` after a web `/set` to 4, even after R. The window drew the config it had loaded earlier: R calls `refreshPanel`, which never reloaded `self.cfg` (gui:2357). The undo depth stayed 8 to 8, which is the 6.8 bug. | a4fix `1a3038a` (reload the config when `CACHE.ver` moved) and `a138013` (undo step) | yes, `6.19` |

## Coordinator items (web-live)

| item | class | cause | fix | rig re-check |
|---|---|---|---|---|
| ctl.console_list_false | TOOL | `show(available(r) and valueOf(r, cfg) or 'n/a')` printed n/a for all 36 controls whose value is false (controls:1043). | a4fix `be49a6a` | web-live `ctl.console_list_false`, driver 6.10 |
| and-or audit | TOOL | Fixed: controls:1043 (above), and gui:2220 `PNL.ctlRow`'s `avail and PNL.value(win, r) or nil`, which turned a false into nil, so an off switch with an on default never showed `*`. Checked and left alone: engine:606 `V7.on` (false becomes nil, but every caller only tests truthiness), controls:542 `modField` (an availability test), controls:834 `a.arg.all` (always a string), gui:783 `defaultAllow` (false either way). There is no `and Y or true` anywhere in the four files. | a4fix `be49a6a` | none |
| act.irr_now.1 crash (engine:9922) | TOOL | `g.pressure` was created only by the tick's `pressurePass` (engine:9545), plus lazily by `finish`, a failed start and `pin`. `irruption now` on a fort whose irruption tick had not run yet went `start` → `hold` → `wave` → `placeWave` placed the units → `g.pressure[k]` on nil. The ledger line, token count, announcement and save never ran. | a4fix `dc372bf`: `IRRUPT.state(g)` creates the table; every forced and tick path calls it first (now, stir, end, cool, tick, restoreAll, disarm). I checked every `g.pressure` use. | web-live `act.irr_now.1`, driver 5.9 |
| "placed 20 alive 0" | TOOL | `IRRUPT.hold` takes its census before the wave it sends, so `ev.alive` read 0 until the next pass. | `dc372bf`: the wave adds its units to `ev.alive`. | the same |
| server errors 400,246 | TOOL | In DFHack r2's `plugins/luasocket.cpp`, `lua_server_accept` returns **0** when nobody is waiting. The Lua wrapper `server:accept()` wraps any non-nil id, so on every idle poll it returned `client{client_id=0}`. `handle()` then called `setBlocking`, the plugin threw "Client does with this id not exist", and the inner pcall counted it: 4 per idle poll (`MAX_ACCEPTS`), about 10 polls a second. `ERROR_LIMIT` never saw these because the outer pcall succeeded. web-live's own evidence agrees: 377,892 handler errors had piled up before its run started. | a4fix `8a61747`: an accept with id ≤ 0 means nobody is waiting. `ERROR_LIMIT` now counts polls whose every request failed; idle polls do not count. | driver 6.21, web-live `end.server_errors`. The counters live in `_G` and survive a deploy, so judge the change, or restart DF. |
| poll worst 5,107 ms | TOOL (fail-fast) | Each header line could wait 100 ms, for up to 60 lines. A `/cmd` or `/set` runs the verb inside DF's frame, and heavy verbs such as `roster build` take seconds; a verb cannot be cut short. | `8a61747`: a 50 ms per-poll budget (later clients wait a poll), a 300 ms request-read deadline (a stalled or silent client is dropped and counted), and `status` names the slowest request. | 6.21; read `slowest request ... (path)` |
| snapshot worst 835 ms | open (instrumented) | Most likely the first snapshot per world (sprite sheets read by `gfx()`) or a pool and pairs rebuild after a set (`poolAndPairs` rebuilds on every `CACHE.ver` change, which web-live's 1,192 sets cause). | `8a61747`: status prints the worst snapshot's parts (pool, census, gfx, species, rest) | 6.21 status line |
| ctl.registry_restored (switch.water) | TOOL (decision) | **Source of truth:** the stored `c.layers.water`, which every job reads and `switch.water` shows. `water.layer_mode` is the policy that writes it. On the disabled web-live fort (rotation off) autoLayer had never run, so the baseline was (auto, off). Restoring `water.layer_mode=auto` ran autoLayer at once and turned the layer on. | a4fix `564c10b`: `water layer auto` reads the map at once only while the tool runs. On a disabled fort it is read when the tool next runs, and the line says `follows the map; read when the tool runs`. Enabled forts behave as before. | web-live `ctl.registry_restored` |

Note for web-live: `seasonal-wildlife-web status` has new fields inside the parentheses:
`errors N, dropped silent/slow clients N, deferred to the next poll N`. It also adds `slowest request N ms (...)` and `[pool .., census .., gfx .., species .., rest .. ms]` after the snapshot worst. A parser that expects `errors N)` must accept `errors N,`. I changed the driver's 6.21 to do that; `web-live.py` is not my file, so I left it alone.

Not an anomaly, but noticed in 3.11: `exhausted this season` listed 40 keys at Summer day 4–6, including 13 cavern keys. Exhaustion reads the region's quantity, so this may simply be the region drawn down after the calendar jump. Probe P2 checks it.

## Rig probes (only if a re-check is still ambiguous)

Run with `cx-lifecycle.sh lua '<code>'` on the fort after the re-run of 3.8.

**P1: who brought FISH_PIKE / HUNGRY_HEAD, and was their entry pinned out of season?**
```lua
local sw=reqscript('seasonal-wildlife'); local all=df.global.world.populations.all
local man={}; for _,r in ipairs(sw.CACHE.managedPops()) do man[r.i]=r.key end
for i,p in ipairs(all) do local cr=df.creature_raw.find(p.race)
  if cr and (cr.creature_id=='HUNGRY_HEAD' or cr.creature_id=='FISH_PIKE') then
    print(i, cr.creature_id, 'feat', p.population.feature_idx, 'cave', p.population.cave_id, 'qty', p.quantity, 'extinct', p.flags.extinct, man[i] or 'UNMANAGED') end end
local g=sw.loadGroups(); local tr={}; for _,grp in ipairs(g.groups) do for _,id in ipairs(grp.ids) do tr[id]=grp end end
for _,u in ipairs(df.global.world.units.active) do local cr=df.creature_raw.find(u.race)
  if cr and (cr.creature_id=='HUNGRY_HEAD' or cr.creature_id=='FISH_PIKE') and sw.WILD.onMap(u) then local r=u.animal.population; local grp=tr[u.id]
    print(u.id, cr.creature_id, sw.WILD.layerOf(u), sw.WILD.origin(u,tr), r.feature_idx, r.cave_id, r.population_idx, grp and grp.arrived, grp and grp.src) end end
print(sw.ROSTER.wants(sw.loadConfig(),'water:FISH_PIKE',df.global.cur_season), sw.ROSTER.wants(sw.loadConfig(),'FISH_PIKE',df.global.cur_season))
```
How to read it:
- In Summer, an out-of-season managed entry must read `qty 0 extinct true`.
- A Summer HUNGRY_HEAD entry with qty > 0 is a tool bug (an entry was not pinned, for example cavern 2, which the fort has not reached). `UNMANAGED` on a cave entry would show why.
- FISH_PIKE: `ENGINE.candidates` (engine:5560-5573) only offers an in-season key. A Summer draw of the promoted land key `FISH_PIKE` places a unit on the land entry (`feat -1`, so layerOf says land). #13004 read layer **water**, so it came from a water-feature entry. It is game behaviour or a pre-flip draw if `grp.arrived` is before the flip, or if the origin is `DF wave`/`untracked` on an entry that reads qty 0 now. It is a tool bug if it is `tool-drawn` after the flip, or if the `water:FISH_PIKE` entries read qty > 0 in Summer.

**P2: exhaustion list sanity**
```lua
local sw=reqscript('seasonal-wildlife'); local c=sw.loadConfig(); local all=df.global.world.populations.all; local q={}
for _,r in ipairs(sw.CACHE.managedPops()) do local p=all[r.i]; if p and p.race==r.race then q[r.key]=(q[r.key] or 0)+p.quantity end end
for k in pairs(c.exhaust.done) do print(k, q[k], sw.ROSTER.wants(c,k,df.global.cur_season)) end
```
Every exhausted key should read quantity 0 and be in season.

**P3: only if 6.3 still fails.** After Enter and Shift+Enter on Land pattern, find which control moved:
```lua
local C=reqscript('seasonal-wildlife-controls'); for _,id in ipairs({'patterns.land','patterns.water','patterns.cavern','groups.adaptive','limits.fixed'}) do print(id, C.valueOf(C.find(id))) end
```

## Re-run after deploying v7.1-a4fix

The driver needs no flag. `--only` keeps the steps' own order. 5.9 and 3.8 are included because 5.10/5.12 and 3.11/3.12 read their results.

```
python3 scripts/alpha4-run.py --only 1.2,1.4,1.5,1.13,2.4,2.12,3.8,3.10,3.11,3.12,4.17,5.9,5.10,5.12,5.16,6.3,6.8,6.10,6.13,6.19,6.21
```

Then re-run web-live for `ctl.console_list_false`, `ctl.registry_restored`, `act.irr_now.1` and `end.server_errors`. Restart DF first, or judge only the change in the error count.
