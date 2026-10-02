# Alpha Four 3.8: why out-of-season species arrived at the season boundary

**Scope.** This was desk work only; the rig was not touched. The code is seasonal-wildlife v7.1 on branch
`v7.1-a4fix`. The analysis was made at d995997, and the fix is commit **9e5aabe** on top of it, not deployed.
The evidence comes from Alpha Four rounds 20261002-003228 (round 1), -011754 (round 2, before 82f0c6d),
-013407 and -013808 (re-run with d995997), plus the vanilla raws.
Line numbers are for `scripts/seasonal-wildlife.lua` at 9e5aabe unless they say otherwise.

## Answer in one paragraph

Out-of-season cavern arrivals had three separate causes:

1. **The cavern layer was off in the lead's 01:40 session.** 82f0c6d made the first-run preset crash, and an
   unguarded crash leaves the cavern layer off for good (§1). With the layer off, the roster does not steer the
   caverns at all.
2. **In round 2 the layer was on, but the R44 cavern gate erased the season.** With every cavern at its cap, the
   gate held all 29 natural cavern species at frequency 1. The roster had already put its out-of-season species
   at 1, so every species had the same weight. DF still sends waves at weight 1, because 1 is a bias and not a
   ban (addendum 56). Those waves were drawn evenly from the whole cavern list. A Spring wave of seven RUTHERER
   was 1 of about 7 cavern waves, which is what an even draw gives.
   - **This is a limit of the frequency-1 hold as designed, not a crash bug.** It is fixable, and 9e5aabe fixes
     it (§3).
3. **The judge, not the tool, made some of the "out of season" calls:**
   - Round 1's HUNGRY_HEAD was judged at the sample tick.
   - Seasons borrowed by the water spill or by exhaustion are given back at the boundary, so the post-boundary
     roster calls their arrivals out of season.
   - The 3.8 driver now reads the borrows and records each arrival's source entry (§6).

**82f0c6d stays, with its rationale corrected** (§4).

## 1. Does the first-run preset turn the cavern layer on, and what turns it off?

- **Yes.** `applyPreset` (:3696) sets `cfg.layers[l] = true` for every layer in `ROSTER.presentLayers()` (:3681,
  :3699). That function lists `cavern` when any managed cave entry has `caveDepth <= 2`.
  - On RinghatchetsReady the ledger confirms it: round 2 shows "preset ...: 159 species active ...; layers turned
    on: cavern, deep, water". Status then read "Layers: cavern, deep, land, water" in rounds 1 and 2.
- **Nothing automatic turns it off.** The only writers of `cfg.layers.cavern` are:
  - the defaults (:655: `cavern=false`)
  - the preset and reset-all (on)
  - the window's layer toggle (gui :1453)
  - the Panel registry switch (:14098)
  - `seasonal-wildlife layer cavern on|off` (:15874)
  - `V7.WAT.autoLayer` writes `layers.water` only (:6444). `enable` (`enableSched`, :14022) does not touch layers.
  - The water `layer_mode` change (564c10b) touches only the water pair.
- **Why the 01:40 session showed `cavern=false`:**
  - `Win:init` saves `initialized = true` **before** the preset runs (`captureDefault(self.cfg);
    saveConfig(self.cfg)`, gui :376-377).
  - 82f0c6d's `buildPool` crash (fixed in d995997) raised inside `applyPreset`. The fort was left initialized,
    with the defaults `{land, water (auto), cavern=false, deep=false}`.
  - No later open retries the preset, because `firstRun = not cfg.initialized`. So `enable` ran on the default
    layers, which matches "Layers: land, water".
  - **Fixed in 9e5aabe** (gui :611): the preset now runs under `pcall`. On failure it puts `initialized` back to
    false, prints the error, and the next open retries.
- **With the cavern layer off, the roster does not steer the caverns at all.** `CAVERN.apply` lists a cavern key
  only when `cfg.layers.cavern` is on or the key has odds (:3527). DF's own odds apply underground, so
  out-of-season species arrive at full weight. With the layer off, that is intended.
  - The R44 gate is different: it runs whenever `groups.enabled and groups.cavern` are on (:11388), whatever the
    layer switch says.

## 2. Who wrote frequency 1 with the cavern layer off?

- **What was ruled out:**
  - The vanilla raws give RUTHERER, HUNGRY_HEAD and TOAD_GIANT_CAVE no FREQUENCY tag, so they default to 50.
    CRUNDLE and TROGLODYTE are 100, and CREEPY_CRAWLER is 10.
  - The save carries no seasonal-wildlife site data (no snapshot, no config).
  - Raws reload on a same-process unload and reload (addendum 53, measured).
  - So a 1 on a fresh load was written in that session.
- **Every raw-frequency writer** (`.frequency =` in all three scripts) is listed below. With the cavern layer
  off and no odds, only the gate can write a 1.

| writer | can write 1 with the cavern layer off? |
|---|---|
| `CAVERN.apply` held branch | only through odds (`cfg.odds`, written by `roster build` at :7371 or `odds`); a fresh config has none |
| `V7.GRP.cavernHold` (R44 gate) | **yes**: it holds every natural cavern-only species at 1 while any of its caverns is at the cap, whatever the layer switch says |
| R61 `freqFloorApply` | writes the floor only where the raw is 0 (animal people) |
| `V7.EXTINCT.writeFreq` | extinct species only |
| `ENGINE.call` / irruption hold | through `CAVERN.apply` with the layer on |

- **The status line counts `CACHE.capHeld` at the moment it is read.** "0 species at frequency 1" with raws at 1
  means one of two things:
  - **(a)** the status was read before the first groups pass after `enable`, so nothing was held yet; or
  - **(b)** the gate had held and then released without restoring.
- **Path (b) existed.** At d995997 the release restored only holds whose snapshot the gate had made itself
  (`own`, :10906 at d995997). It then relied on `CAVERN.apply` to re-hold or restore the rest, but only
  `if cfg.layers.cavern` (:10922 at d995997).
  - So with the layer off, any hold the gate had not made stayed at 1 for good: a roster hold from before the
    layer was switched off, or a stale snapshot.
  - Switching the layer off left every roster hold in place for the same reason: `CAVERN.apply` stopped listing
    those keys and never released them.
  - **Fixed in 9e5aabe** with `V7.GRP.orphans` (:10924). `CAVERN.apply` restores any snapshot entry that no key
    of its pass wants and the gate does not hold. The gate's release now calls `CAVERN.apply` whenever rotation
    is on.
- **Is the gate holding everything at 1 over the cap?** Yes, and it is **the main finding**:
  - Round 2's step 5.16 status read `hold any (29 species at frequency 1)  trim on (4 animal(s) on their way)
    natives counted`. Natives count against the cap (R44, `natives_cavern`), and 43 to 56 cavern units filled all
    three caverns.
  - At 1 for everyone, an in-season CROCODILE_CAVE weighs exactly what an out-of-season RUTHERER does.

## 3. The fix in 9e5aabe: the gate keeps the season's mix

- **Why scaling works:**
  - Frequency is a comparative weight (addendum 55), and 1 is the floor (addendum 54: never 0).
  - So the only way to hold a cavern's volume down and still keep the season is to scale the open species and
    leave the held ones at 1.
- **The new rule.** `V7.GRP.holdLevel` (:10900) and `holdFor` (:10907) set the level:
  - **Open species** (in season and active; with the cavern layer off, every species): `max(2, weight // 10)`,
    never above its weight. The weight is the player's odds, else the raw's original. A 50 becomes 5 and a 100
    becomes 10.
  - **Species the roster holds** (out of season, inactive, or passed over by a call): 1.
  - `CAVERN.apply` writes the same level for a gate-held open species, so the daily pass and the gate never flap.
  - The old ceiling (`limits cavern ceiling`, default off) keeps all-at-1.
- **What this does to the odds:**
  - In season still outweighs out of season 5:1 (weight 50) to 10:1 (weight 100).
  - For example, 15 open species at weight 50 and 14 held ones give an in-season share of about 84%, against
    about 52% with all at 1.
- **What it may cost:**
  - The held mass falls about 90% instead of about 98%.
  - T7b measured the brake at all-at-1 (arrivals −25% to −30%), and E21b showed the thinning is strongly
    non-linear (24% of the mass removed cut arrivals 44%). So the brake should mostly survive, but **it is
    unmeasured**.
- **How to turn it off and what changed around it:**
  - **Switch:** `groups.cavern_hold_mix` (default on); `groups cavern mix on|off`; Panel "Keep the season's mix".
    Off restores the v7.1 all-at-1 hold.
  - **Wording:** the status, ledger and verb lines say which hold is in force.
  - **Docs:** docs/v7.1/groups.md and USAGE.md are updated.
  - **Validation:** DwarfCron `scripts/validate-full.py` `mech.v71.cavern.hold` now expects the mix level.
- **Known gap:** the gate sets a held species' level once, when it holds it. Two things wait for the gate's
  release:
  - With the cavern layer on, the daily `CAVERN.apply` re-levels gate-held species, for example at a season
    change. With the layer off, nothing re-levels them.
  - A species held while the layer was on keeps its level after the layer is switched off.
- **Checks:** `luac53 -p` passes. luacheck shows 36 warnings, the same as HEAD; the diff is line shifts only. No new
  main-chunk locals were added (the new code sits in `V7.GRP`).

### Is it a bug or the floor's known limit?

**It is the floor's known limit, made worse by a design choice.**

- The limit: frequency 1 leaks, at about 15% of full rate (addendum 56).
- The design choice: the gate held in-season species at the same 1 as out-of-season ones, which turns that leak
  into an even draw over the whole cavern list.
- Fixable now: the even draw (9e5aabe).
- Not fixable: the 1-floor leak itself. Some out-of-season cavern arrivals will always come.

**Proposed player-facing text** (in USAGE.md as a new troubleshooting row):

> An out-of-season cavern species arrived. Frequency 1 is a strong bias, not a ban: measured, five species held at
> 1 still brought about 15% of what they brought at 100. Check that the cavern layer is on (`layer`); with it off,
> the roster does not steer the caverns and DF's own odds apply. A season borrowed by exhaustion (`exhaust`) also
> opens a species for the rest of that season.

**Boundary lag (intended):** the season pass runs at the next daily tick (:3917), up to 1,200 ticks after the
boundary. A wave in the first game day of a season can still be drawn from the last season's odds.

## 4. 82f0c6d (cave entries over the 3x3 neighbourhood): keep it, but correct its rationale

- **The commit message's mechanism is wrong.** It says rutherers came "from the unmanaged copies while every
  managed copy was held at 0". Cave entry quantities gate nothing underground (addenda 51 and 52: 109 local
  entries and all 914 cave masters held at 0 for 12,000 ticks, and arrivals continued). The frequency lever is
  per raw, not per entry. RUTHERER was already in the roster (`cavern:RUTHERER`) and was already held at 1 in
  Spring, so 82f0c6d could not have changed its odds.
- **It is still right, for roster completeness.**
  - DF does draw cavern waves from the neighbour tiles: 168:173 and 170:173 with caves 181 and 759 (round 2
    sources).
  - A species whose only cave entries sit on those tiles was missing from `managedPops`, the pool and
    `V7.GRP.species`. It had no `cfg.allow` key, so `CAVERN.apply` never held it and the gate never counted it.
    It arrived at full weight in every season.
  - With 82f0c6d such a species is `inEmbark` (buildPool :2263), the preset seasons it, and both levers reach
    its raw.
- **Costs:**
  - Quantity holds on more cave entries. These are inert for draws, but restored on disable.
  - d995997's `nil` biome guard was the only other lookup that assumed a managed entry's tile is in the block set
    (checked: buildPool :2268 is the only `regionSet[...region_x...]` read of an entry).
- **Keep 82f0c6d + d995997.** If anything, amend the commit note.

## 5. Other 3.8 items

- **Round 1, HUNGRY_HEAD x13 (Spring only), judged against Summer.** It was one wave: consecutive ids
  13012-13024. The round-1 driver judged at the sample tick (readout trap). The flip-id judge, added after round
  1, fixed it.
- **Round 2, RUTHERER x7 (one wave, source 168:173 cave 759), TOAD_GIANT_CAVE x1 and ELEMENTMAN_MUD x1 (no roster
  key).** These are §2 and §3: the gate held 29 species at 1. A second possibility the new driver will separate:
  - Exhaustion's niche replacement (`ROSTER.exhaustCheck`, :2975) also runs underground. It reads "stock 0" from
    managed cave entry quantities, which do not gate cavern draws (addendum 51).
  - So it can promote an out-of-season cavern species, which opens its frequency, for the rest of a season, for
    no real reason.
  - **Recommendation (not implemented; it needs a ruling on ECO N1):** keep exhaustion off the cavern layer, or
    read cavern exhaustion from arrivals rather than quantity.
- **Round 3 (013808), water:BEAVER x2 and water:ALLIGATOR SNAPPING TURTLE x1, tool-drawn, Spring, Autumn only.**
  These came from the season spill, as designed. The same species are in season in Summer in the same data
  (BEAVER x13 Summer, in season), which can only be a borrow.
  - `V7.WAT.spillCheck` (:6490) runs once a game day from the groups pass. When a body has fewer than
    `spill.min` (3) drawable in-season species, it adds the current season to active out-of-season water
    species (`setAssign`), restocks their entries, and logs "water season spill: the <body> has fewer than 3
    drawable species; <TOKEN> borrows <Season>".
  - `spillRoll` (:6473) takes the borrows back at the boundary.
  - "nothing borrowed" at load is consistent with this: the borrow happened after the calendar jump.
  - The tool then draws them (ENGINE candidates read `ROSTER.wants`).
  - The 3.8 judge reads the post-roll roster, so it called them out of season. **The driver now counts a
    borrowed season as in season** (§6).
- **Round 3, GIANT_PEACH-FACED_LOVEBIRD x8, DF land wave, Spring (roster: Autumn only), source 169:173 entry
  33.**
  - **Lever.** A land species out of season is held by its entry quantity (`holdOutOfSeason`, every 300 ticks,
    :11314) on the block region set. Frequency is not that hold: R26's giant multipliers only shape odds and
    pick weight, and a land wave is gated by quantity (E3, X1).
  - **Most likely cause: exhaustion.** The same data has five more lovebirds arriving in Summer and judged *in
    season*. That can only be a live borrow: Summer is not in its roster, so exhaustion must have promoted it
    again after the roll.
    - So the Spring wave most likely followed a Spring promotion. The ledger would say "<X> exhausted (stock 0):
      GIANT_PEACH-FACED_LOVEBIRD takes its niche for the rest of Spring", and the borrow is given back at the
      boundary.
  - **Other possibility:** an unmanaged or unzeroed entry on 169:173. The new driver records the entry's
    managed flag and quantity before and after, so the next run will say which.

## 6. Driver change (DwarfCron Dev, `scripts/alpha4-run.py`, step 3.8)

- **Before the boundary** (`PRE38_LUA`): every population entry on the site's region tiles and their 3x3
  neighbours whose key the roster does not want this season. For each, it records the `world.populations.all`
  index, quantity, extinct flag and whether it is managed (`sw.managedPop`).
- **After the boundary** (`ARR38_LUA`), for each arrival:
  - its own `u.animal.population` source key (`usrc`)
  - **borrowed seasons**, from ledger lines since the start of the season ("<TOKEN> borrows <Season>", "...
    takes its niche for the rest of <Season>") and the live `spill_state.borrowed` / `exhaust.promoted`
  - An arrival counts as in season by a borrow only if it arrived at or after the borrow's tick.
  - For each arrival still out of season: its entry (index, quantity, quantity max, extinct, managed) and, for
    cavern or deep species, the raw FREQUENCY, CAVERN snapshot and gate hold.
- **The mark's note:**
  - lists the borrowed in-season keys separately
  - explains each out-of-season key in one line, for example `land:GIANT_PEACH-FACED_LOVEBIRD x8 (DF wave,
    Spring; entry 169:173:-1:-1:-1:33; #<index> managed q <before>-><now> (max <qmax>) extinct <flag>)`
  - The full rows are in the mark's `data.arrivals`.
- **Checks:** the dry run plans the step, and both embedded Lua probes pass `luac53 -p`.

## 7. Rig check for the lead (deploy a4fix 9e5aabe first)

1. Restore and load RinghatchetsReady.preverify. Open the window once (the first-run preset), then close it.
   - **Expect:** status "Layers: cavern, deep, land, water"; ledger `build` "layers turned on: cavern, deep,
     water".
2. Step 3,000 ticks with the window closed so the groups pass engages the gate. `seasonal-wildlife groups
   layers` should show the cavern gate line reading `hold any (N species held: in season at 1/10 of their weight
   (at least 2), the rest at 1)`.
3. Probe (RPC Lua):
   ```lua
   local sw=reqscript('seasonal-wildlife'); local json=require('json'); local cfg=sw.loadConfig(); local s=df.global.cur_season
   local snap=sw.CAVERN.saved(); local gate=sw.CACHE.capHeld or {}; local n=0; for _ in pairs(gate) do n=n+1 end
   local o={season=s, cavern=cfg.layers.cavern, mix=cfg.groups.cavern_hold_mix, held=n, rows={}}
   for _,t in ipairs({'RUTHERER','TOAD_GIANT_CAVE','HUNGRY_HEAD','CROCODILE_CAVE','TROGLODYTE','CRUNDLE','SPIDER_CAVE_GIANT','CREEPY_CRAWLER'}) do
     local cr=sw.CAVERN.rawFor(t); local k='cavern:'..t
     o.rows[t]={freq=cr and cr.frequency, snap=snap[t], gate=gate[t] and true or false, allow=cfg.allow[k],
                wants=sw.ROSTER.wants(cfg,k,s), lvl=sw.V7.GRP.holdFor(cfg,t,snap)}
   end
   print(json.encode(o))
   ```
   - **Expected in Spring with the gate engaged:**
     - Every gate-held row has `freq == lvl`.
     - Rows with `wants=true`: `max(2, original // 10)`, so 50 gives 5, 100 gives 10, 20 gives 2, 10 gives 2.
       HUNGRY_HEAD is Spring only, so expect 5.
     - Rows with `wants=false` (RUTHERER, TOAD_GIANT_CAVE): 1.
     - Nothing at 0.
     - `snap` holds the originals: 50 for RUTHERER, TOAD_GIANT_CAVE, HUNGRY_HEAD and CROCODILE_CAVE; 100 for
       TROGLODYTE and CRUNDLE; 20 for SPIDER_CAVE_GIANT; 10 for CREEPY_CRAWLER.
4. `seasonal-wildlife ledger 30 cavern`. **Expect:** "cavern gate (R44): N species newly held (in season at 1/10
   ...)" and no line of the form "... newly held at frequency 1".
5. Orphan sweep: `seasonal-wildlife layer cavern off`, step 1,300 ticks (one daily pass), then re-run the probe.
   - **Expect:** no row at 1 unless the gate holds it. Ledger: "N frequency hold(s) no layer or gate owns any
     more put back".
   - Gate-held rows keep their level until the gate releases them (§3, known gap). Then
     `seasonal-wildlife layer cavern on`.
6. Fallback: `seasonal-wildlife groups cavern mix off`, step 1,300 ticks, then re-run the probe.
   - **Expect:** every gate-held row at 1, as in v7.1. Then run `groups cavern mix on`.
7. Re-run `alpha4-run.py --only 3.8`.
   - **Expect:** borrowed water and land keys listed under "in season by a borrowed season".
   - Any remaining out-of-season key comes with its entry, quantity and (underground) frequency.
8. **Measurement** (not a rig check, for the record): mix on vs mix off, n=5 per arm, one season each, the gate
   engaged.
   - Score: the cavern in-season share of arrivals, and total cavern arrivals (the brake).
   - The prediction: share rises from about 50% toward about 80%, and total arrivals change by no more than T7b's
     brake.

## Commits

- seasonal-wildlife `v7.1-a4fix`: **9e5aabe** (parent d995997). Not deployed, merged or pushed.
- DwarfCron Dev: this file, `scripts/alpha4-run.py` (step 3.8) and `scripts/validate-full.py`
  (`mech.v71.cavern.hold` expects the mix level).
