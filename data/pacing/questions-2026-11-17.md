# Read this first: Urist's verification and what it adds up to

**How these answers were made.** Each of your 38 questions had its own agent, which answered from the code (sw-wt/plugin v8.1-pacing @ 6dffef5), your past rulings, git history and the rig data. A second agent was given your question and that answer, checked the claims and revised it. One verifier per group then spot-checked the claims each conclusion rests on and resolved contradictions between answers. Nothing was run on the rig: B2 was using it. Where an answer needs a rig test, it names the test.

**What I checked myself, against the code and the rig, before publishing:**

| Claim | Check | Result |
|---|---|---|
| The tool's own cavern draw (P9) never places anything (C1–C4, A, G) | `V7.DRAW.members` strips the `cavern:` prefix; `keyFor` files cavern entries as `cavern:TOKEN`; `ROSTER.apex.entries` matches the key exactly. B2 ledgers: 0 cavern draws on every fort | **Confirmed: a bug in my P9 commit (sw 101c802).** B2's cavern results therefore measure DF's pick plus the P10 open stock, not the P9 draw. |
| Each kind of water gets the full map-size cap (B1) | Rig status P2_SAVR: `water:river cap 4 (map size)`, `water:pool cap 4 (map size)` | **Confirmed.** All ponds are one place with one cap, but that cap equals the river's. |
| Vermin hunting and scavenging are ON in your forts, not OFF (F1, F2) | Rig status P2_SAVR: `vermin hunting: on`, `scavenging: on`, `vermin forage: off` | **Confirmed.** My mechanics page said OFF. **Corrected on the page.** |
| "Land natives OFF" has no effect under season casts (F7) | `seasonal-wildlife.lua:16886`: `(L == 'land' and (gc.natives_land or cast))` | **Confirmed. Corrected on the page.** |
| Panel 2b step 5 says the pyramid split is "per season" (C) | `ROSTER.ladder` splits over the whole year's members | **The page was wrong. Corrected.** |
| Fort 1 spring odds (C6) | The ladder I published: weasel 44 + colepiocephale 30 of 99 among the non-apex spring members, so 25% are neither | **Consistent.** The ~70% answer adds the draw's least-seen rule and B2's real spring (8 of 11). |

**Bugs the swarm found (all confirmed in code by at least two agents; none fixed yet, because B2 is running and your 2 Oct rule says no mid-round fixes):**
1. **Cavern draw key bug** (above). One-line class of fix; it's what P9 was meant to do.
2. **One group per species stands down entirely while the land pause holds** (`:16234`). Flying and water-cast species can then double up: albatross ×2, giant dragonfly ×2, giant fly ×2, barn owl ×2 in B2 (B2, G1, G2).
3. **Stand-in bookkeeping** (E): every copy of a stand-in stays open; the tool's draws never place stand-ins; a cavern stand-in opens at every depth; a reload drops the `resting` mark.
4. **Caged and chained animals are not excluded** from the 7-day grace removal (E2).
5. **Reset everything quietly turns hunting and scavenging off**, because their built-in defaults are opt-in (F).
6. **Scavenging ignores realm**: cavern eaters can feed on sea carcasses, and surface fliers can be dropped into sealed caverns (F2).

**What your questions add up to.** Across the groups the answers agree on one picture. The tool runs two arrival systems side by side (DF's waves and its own draws) and spends much of its code stitching them together. Your instinct to suppress DF's waves is supported, but the agents recommend a **seal, not a deletion**:
- hold the extinct flag on every managed Animal entry all the time;
- leave stock alone, because the tool's draws read stock, not the flag;
- let the tool draw every layer on its own clock, the way water already works.

Deleting entries would break most of the tool. Zeroing stock stops the tool's own draws. FREQUENCY 0 has frozen DF. DF still simulates tool-placed animals fully (wander, fight, die, leave); see A3.

**Decisions only you can make** (each answer gives the trade-offs):
1. **Seal-and-draw** for land, flying and caverns (A1, A2). It's a design change: one switch, then a test season on new embarks.
2. **Water places:** one shared fresh place (lake, river, ponds) and one sea place, each with the map-size cap, in place of a full cap per kind (B1). This also settles your pending pond options (P11).
3. **The draw's pick rule** is now the real balance lever on land and flying, not FREQUENCY (C1, C6). Least-seen-first gives coverage but roughly quadruples the predator share. Options: count seen in groups, a soft least-seen weight, or pyramid-first.
4. **A ladder per cast** (layer × season) instead of per year (C4). It needs one call: is the biomass guard measured per cast or per year?
5. **Apex roles** (D1, C5): an apex-eligible species takes only the apex seat, or roles are read per season. Keep apexes off the FREQUENCY ladder either way.
6. **Seasonality model** (D5, D7). DF's raws carry almost no seasonal signal (23 tagged creatures), so today's seasons are a random draw kept for the fort's life. Choose maximum turnover, or a resident core plus seasonal visitors (migrants, hibernators). Either way, size slots to their candidates and use a soft two-season cap.
7. **Scavenging realm rule** (F2).

**Answers that push back on a proposal** (no change advised): flipping the √mass ratio (D2); a chance roll on the bonus predator (D4; it barely matters); a 600-tick stuck sweep (F5; it never touches fliers, so it wouldn't fix what you see); a 3-day grace (E2; fix the cage bug and find out why animals linger first); the cap−1 bird unpause as written (G2; fix the one-per-species leak instead); turning forage or panic back on (F3, F4).

---

# Contents

- **A. DF waves vs the tool's own placements**: [A1](#a1), [A2](#a2), [A3](#a3), [A4](#a4), [A5](#a5), [A6](#a6)
- **B. Caps, places and slots**: [B1](#b1), [B2](#b2), [B3](#b3), [B4](#b4), [B5](#b5), [B6](#b6)
- **C. The FREQUENCY ladder and odds**: [C1](#c1), [C2](#c2), [C3](#c3), [C4](#c4), [C5](#c5), [C6](#c6)
- **D. Building the casts**: [D1](#d1), [D2](#d2), [D3](#d3), [D4](#d4), [D5](#d5), [D6](#d6), [D7](#d7)
- **E. Resting, holding, stand-ins and grace**: [E1](#e1), [E2](#e2), [E3](#e3), [E4](#e4)
- **F. Behaviour switches and housekeeping**: [F1](#f1), [F2](#f2), [F3](#f3), [F4](#f4), [F5](#f5), [F6](#f6), [F7](#f7)
- **G. Surface gates: coupling and the bird pause**: [G1](#g1), [G2](#g2)

# A. DF waves vs the tool's own placements

*who places animals (DF's wave mechanic vs the tool), entries/stock, whether the tool could take over all placement, and whether DF still simulates tool-placed groups*

### What these six questions are after

Taken together, the questions ask one thing: **can the tool be the only author of what arrives, and if it is, will DF still bring those animals to life?** Behind that are your aims: diversity, a believable food web, even pacing and seasonal balance, and fewer workarounds that defer to DF.

- **A1 and A2** ask whether DF's wave mechanic can be blocked, wiped or zeroed so the tool places everything.
- **A3 and A4** ask whether DF still simulates and books tool-placed animals: wander, fight, die, leave, refund.
- **A5 and A6** ask what an \"entry\" really is, and whether the region or the cast decides who gets one.

### What the code and the rig say

1. **Today the tool runs two arrival systems side by side, and DF goes first.**
   - `discoverGroups` files DF's flagged waves as tool groups, and release just clears the flags.
   - A waiting DF wave takes the land turn (`:17421-17451`).
   - A flagged cavern group blocks the cavern draw, and every DF cavern arrival restarts a 4-day wait (`:15581`, `:15997`).
   - DF fliers restart the flying clock.
   - In the B2 ledger tails, the caverns were 100% DF's.
2. **\"Never release\" and \"wipe\" don't work.**
   - DF has already placed and debited the animals before the tool can see them.
   - Holding them only slows DF's next wave and starves the tool's draws.
   - Wiping them fights DF, costs stock, and breaks your \"pause, not trim\" rule.
3. **The lever that works already exists: the extinct flag, with stock left alone.**
   - The tool's draws read stock and never the flag (`ROSTER.apex.entries` `:11563`). The B2 SAVR ledger shows draws while land entries were closed.
   - The flag stops DF's surface waves (E8) and cavern waves (8b473b7: 2 v 82, no stall).
   - Deleting entries breaks the tool, which keys its records by entry position.
   - Stock 0 stops the tool's own draws, and is unsettled as a cavern lever.
   - FREQUENCY 0 has frozen DF.
4. **DF does simulate tool-placed animals.** They wander (given the copied reference), fight on written links, die, leave on their countdown, survive save and reload, and conceive when their reference is on this site.
   - DF runs no hunger for any wild animal, so \"eat\" in the diagram is really the tool's scavenging plus kills.
   - The tool already covers what `create` leaves out: the relation slot and the owner type.
   - **Still unmeasured:** DF's refund for placed land and cavern animals (INV3 never ran), whether DF also refunds animals the tool vanishes, and whether a placed dangerous animal threatens dwarves like a DF wave does.
5. **Entries are doors, not roles.** The cast (slots) decides who gets an open entry each season. The region decides only where that entry sits (the anchor tile), and gives DF-stocked species a small edge in reaching the candidate list.

### Combined recommendation

The direction you're leaning toward, fully suppressing DF's waves, does serve your aims. Build it as **a seal, not a deletion**:

1. **One switch** that holds the extinct flag on every Animal entry on the draw tiles (managed and innumerable) and every cavern Animal entry at depths 1-3, all the time.
   - Stock is never touched; Vermin and the deep are left alone.
   - It closes again after any of the 28 `V7.reopened()` writers.
   - `off` gives every flag back.
2. **Every layer on the water loop:** when the clock is due and the layer is under its cap, the tool draws (`groups cavern draw_grace 0`).
   - The ladder becomes draw weights only, so there are no more FREQUENCY writes and no freeze risk.
   - `discoverGroups` stays only as a leak alarm.
3. **Rework, not just switch off:**
   - land coupling, which today fires only on fresh DF waves, so it must trigger on drawn prey;
   - innumerable-only species, which the tool can't draw;
   - the draw's pick, which is least-seen-first and would flatten the trophic pyramid unless it gets the water draw's balance weights;
   - the candidate list per layer: compute coverage offline first, so a layer doesn't collapse to one species like the savage marsh's osprey-only ponds.
4. **Two decisions are yours:**
   - overriding D8 for caverns 1-3, because special-class cavern arrivals stop unless they are cast;
   - whether unbreached caverns should be filled by the tool. It can draw walkers into them today, and DF already sends waves there.
5. **Measure the refund before relying on it more.**
   - A free ledger line of the entry quantity before and after each placed animal leaves would settle A4 on every pacing run.
   - Do not add a just-in-case tool refund: that is the v5.3 double count.

The decisive rig test is A1/A2's two-arm comparison: v8.1 against the seal plus tool-only draws, on breached P2 forts, measuring leaks, days at 0, effective species by waves, over-cap, refunds, references, FPS and stalls. Its refund and field-comparison arms would also close A3 and A4's open points.

<details><summary>Cross-answer issues the verifier resolved</summary>

- Cavern stock as a lever. A1 said flatly that 'stock does not stop cavern waves (addendum 51)'; A2 said stock 0 in the caverns is 'unproven'. Resolution from STATE.md addenda 51-52 and RESEARCH-NOTES §9: the recorded finding (18 Sep) is that cavern waves ignore entry quantity. But that run zeroed only the 109 managed local entries in one arm and only the cave master lists in the other, and it came before the finding that DF draws from all 9 region tiles a map block names. The 17 Nov dominance finding (PENDING) also suggests stock weights DF's cavern pick. So it is unsettled. Both answers agree on the lever that works, the extinct flag (sw 8b473b7: 2 v 82 cavern waves, no stall). A1 has been softened to match.
- Surface gate: shared or per source? A3 said 'one arrival gate per source' as fact; A1 said it is unsettled. The evidence points both ways. E1 (STATE:673-680) held two animals from two different tiles (29,20 and 28,19) and nothing came for 12,000 ticks, which suggests one shared gate. Code comments (:5162, :5508-5511, :15641) assume per source, based on region9 NAT (flagged waves from 3 tiles at once) and X5v75. Resolved as unsettled in A3 too. What is solid is that the gate counts flagged animals: it stays open while at most one is on the map.
- Unbreached caverns: A4 said 'no cavern draws take place' there, which is wrong. The code has no breach or Discovered check anywhere on the cavern draw path. V7.GRP.cavernPass -> V7.DRAW.caveTick -> ROSTER.placeGroup -> CAVE.bandFor/PLACE.tiles. CAVE.survey (:5851) maps caverns from edge blocks' global_feature and the subterranean flag only. So walkers can be drawn into a cavern nobody has found, as long as it touches the map edge. Swimmers are refused, because cavern pools are registered only once the cavern is discovered (:8695). DF also sends cavern waves unrevealed (E13; NA1 per cavern-thief-tag-bar). A1, A4 and A6 now agree.
- Off-site population reference on a draw. A1 said V7.DRAW.pick's largest-stock entry 'may be on a neighbouring tile'. A2 and A5 said the draw lands on the chosen (anchor or site-tile) entry because held copies sit at 0. The code backs A2/A5. ROSTER.apex.entries (:11563) keeps only quantity > 0. holdOutOfSeason (:3931) moves held copies to 0 every pass. FP.materialise (:10606-10618) gives every cast ground or flying species a site-tile entry. So an off-site reference happens only with single_source off, or in the rare case where a DF refund lands on a held copy and is drawn within the ≤300-tick window before the hold pulls it back. A1 has been corrected.
- Line numbers for releaseGroup. A3 cited :5446-5458; the code has releaseGroup at :5456-5469 and detachOldest at :5471. Fixed in A3.
- Coupling under a full seal: missed by A1 and A2. Land coupling fires only on FRESH DF waves. The loop at :17375-17386 runs over `fresh` from discoverGroups, and drawn groups are never fresh. So with DF's sources sealed, land coupling would never fire. 'Draw the called predator next' therefore needs a new trigger on drawn prey, as the water draw already has (~:7510, 'coupling: %s drawn; its predators ... are the next draw'). Added to A1 and A2.
- Innumerable entries under a seal: missed by A1 and A2. The tool cannot draw from an innumerable entry. ROSTER.apex.entries reads CACHE.managedPops, and managedPop (:1711) skips quantity_max >= INNUMERABLE. Sealing the side rows (sideRows :15696) therefore removes such a species (for example Boardhelms' barn owl at 10000001) altogether, unless the cast gives it a countable entry. Added.
- Verb name: A1 and A2 wrote `cavern_draw_grace_days 0`. That is the setting name. The console verb is `groups cavern draw_grace 0` (:24083), and similarly `groups cavern open_stock 0` and `groups cavern leave N` (:24082-24084), which A4 used correctly.
- Irruptions: A2 said they are 'off by default'. That is true of the code: IRRUPT.defaults enabled=false (:13735). The user's 16 Oct beta ruling said irruptions on (memory beta-rulings-oct16). Noted in A2 so the user is not misled about the live configuration.
- The word 'slot': A4 and A5 agree, and the code confirms it. In panel 1, 'a slot frees' means room under a layer's group cap. It frees per GROUP, once the last member has died or left (reconcileGroups :5388-5404, ENGINE.count :7515). A cast slot is a different thing (NR.toRecord). Both answers recommend the same wording fix.

</details>

## A1

> What would happen if... since "DF sends a wave" has all of these underlying mechanics and it seems to block the tool draws because of the "when due and no DF wave is waiting" rule, what if the seasonal-wildlife tool watched for and blocked (or wiped) animal placements that come from the DF wave placement mechanic? Could we effectively replace it, and unblock the seasonal-wildlife draws for land, flying and cavern? Would we be able to directly manage those layers without having to use hackish fixes that defer to the DF wave mechanics? Since the DF wave "waits flagged at the gate until the tool releases it on the clock" could we just make it so that the tool never releases the gate? What would happen if we did it this way?

**Short answer.** No. 'Never release' doesn't stop DF: its animals are already on the map when the tool sees them, and holding them only slows DF's next wave and blocks the tool's draws. Wiping them fights DF and breaks your 'pause, not trim' rule. What gets you the tool alone choosing on land, flying and caverns is to keep DF's sources closed all the time with the extinct flag (the pauses' existing lever) and let the tool draw on every clock tick, as the water layers already do. It needs a small build and a rig test.

*Status: corrected · confidence medium · review verdict: minor fixes*

### A1. If the tool never released DF's waves, or removed them, could it take over land, flying and caverns?

**Short version.** "Never release" doesn't stop DF, and wiping DF's animals turns into a fight with DF that the tool can't win. Your aim is the tool alone choosing what arrives on every layer. You can get there another way: keep DF's sources closed all the time, with the lever the pauses already use (the extinct flag). Water already works that way.

### 1. What "waiting at the gate" really means

The diagram's phrase "it waits flagged at the gate" makes it sound as if the animals are held offstage. They aren't.

- **DF picks and places the animals first.** They walk in at the map edge carrying the flag `roaming_wilderness_population_source`.
- **The tool finds them afterwards.**
  - `gatedLayer` (`seasonal-wildlife.lua:5369`) spots flagged units.
  - `discoverGroups` (`:5414`) files them as a gated group.
  - This happens in the groups pass every 300 ticks (`GROUPS_CADENCE`, `:5152`).
- **"Releasing" only clears two flags.** That is `releaseGroup` (`:5456`) and `detachOldest` (`:5471`). The animals stay where they are.
- **What the flag does in DF** (rig): a new surface wave comes only while **at most one** flagged animal is on the map (E1, STATE addendum 12, "F1 = C"). With two held, nothing came in 12,000 ticks. The caverns have the same gate, kept separately for each depth.

So holding a wave never keeps DF's animals off the map. It only stops the next wave.

There is also no way to stop DF *before* it places a wave. The earliest DFHack notice, eventful's `UNIT_NEW_ACTIVE`, fires after the unit exists (DFHack mirror `repos/dfhack/plugins/eventful.cpp:98, :235`). By then DF has already debited the entry. So "block" can only mean closing the source beforehand, and "wipe" can only mean removing animals after they land.

### 2. Why DF's waves block the draws today (code)

- **Waiting groups take slots.** `ENGINE.count` (`:7515`) counts every group, flagged or not.
- **Land** (`:17421-17451`):
  - When the clock is due and land is under its cap, `detachOldest(g,'land')` runs first.
  - `V7.DRAW.one` draws only if no flagged group exists.
  - Either way it is one arrival per due tick. A waiting DF wave takes the turn, so DF chooses the species.
- **Caverns** (`V7.GRP.cavernPass`, `:15581`):
  - The draw runs only if `not gated[d]`.
  - `V7.DRAW.caveTick` (`:15997`) then also waits 4 quiet days (`GRACE_DAYS`).
  - Every DF arrival at that depth restarts the wait.
- **Flying:**
  - `V7.GRP.flyGroups` (`:16038`) releases DF fliers at once.
  - `V7.DRAW.flyTick` (`:15967`) restarts the flying clock from each DF flier's arrival.
  - DF still takes flying turns.

**What the B2 ledgers show** (last 300 lines of each, Summer 71/73 to about Autumn 15; arrival lines counted, which I re-checked):

| Fort | Land (DF / tool) | Flying (DF / tool) | Caverns (DF / tool) |
|---|---|---|---|
| P2_SAVR | 6 / 6 | 3 / 3 | 15 / 0 (+15 tail joins) |
| P2_COAST | 4 / 7 | 7 / 2 | 19 / 0 (+13 tail joins) |

**The tool's draws don't need the entries open.**
- `ROSTER.apex.entries` (`:11563`) keeps entries with stock above 0 and never reads `flags.extinct`.
- The ledger proves it. On P2_SAVR the land pause was on from Summer 74, yet the tool drew CRETACEOUS_IGUANODON x5 (Summer 78) and BEAR_BLACK x1 (Summer 81). Land only resumed at Autumn 1. This works because the pause reopens at cap − 2 (`resumeAt`, `:15673`), so draws run at cap − 1 with entries closed.
- `ROSTER.placeGroup` (`:11595`) places at the map edge and debits one per animal.
- `PLACE.one` (`:6045`) sets up each animal:
  - copies the entry's population reference;
  - sets a stay of 20,000-30,000 ticks (DF's own is 19,913-29,918, E9a);
  - clears both roaming flags, so drawn groups never hold the gate;
  - sets `owner_type` NONE;
  - gives an enemy-status slot.

### 3. Thought experiments

**(a) Never release, code otherwise unchanged.**
- Example: land cap 4, DF sends ravens x4. They are held, so the gate shuts, and the land draw is blocked while they stay (about 17-25 days, then they walk off and DF refunds them, E9b).
- A one-animal wave (opossum, kakapo, tiger x1 are common in B2) doesn't shut the gate, so DF sends a second behind it.
- Whether the gate is shared across the surface or kept per source is **not settled**:
  - E1 held animals from two tiles and nothing came, which suggests shared;
  - region9 NAT and X5v75 saw flagged waves from several tiles at once, and code comments `:5508`, `:15641` assume per source.
- **Result:** DF still picks the species, but less often, and the tool barely draws. Groups can also get stuck: on v5.4 a raven group held the gate for half a year. This goes against what you want.

**(b) Never release, but let the tool draw anyway.**
- Each source keeps one or two DF groups for a full stay. DF's choice stays wherever it holds a slot.
- B1 shows what DF's choice looked like: cavern 1 bugbats 56% counted by groups (about 40% counted by waves, since a bugbat wave splits into about 2.7 groups), and coast fliers ravens 58%.
- Over-cap bursts remain.
- **Result:** DF's share shrinks, but DF is not replaced.

**(c) Remove DF's arrivals as they land.**
- TR2 vanished every arrival and got a new wave about every 350 ticks, roughly 290 a season through one gate.
- Every wave is debited from stock. Removing animals by killing is never refunded (E4), which empties small entries. Vanishing them needs a hand refund (`refundUnit` `:16820`).
- With a pass every 300 ticks, a predator can act before it is removed.
- Inference: a constant churn of created units costs FPS (fps-load-facts: +500 wild animals cost −38%).
- It breaks your 13 Oct rule: close the sources, never send creatures off (pause-not-trim).
- **Result: don't.**

**(d) The better option: close DF's sources and keep them closed.**

Hold the extinct flag on, all the time:
- every managed surface entry, land and region-tile water rows;
- the innumerable side rows (`sideRows`, `:15696`);
- the flying cast's and water birds' entries (today `flyPause` `:16075` and `birdPause`);
- every cavern entry at depths 1-3 (`cavePause` `:16375`).

Evidence it stops DF:
- Surface: the flag alone stops a draw (E8).
- Caverns: the 13 Oct probe (sw 8b473b7: 622/831/886 entries closed, cap 1) let in 2 waves in 25 days against 82 with the trim, and DF did not stall.
- Stock is **not** a reliable cavern lever. Addenda 51-52 found cavern waves ignore quantity, but those runs zeroed only part of the entries and predate the 9-tile finding. The 17 Nov result suggests stock weights DF's pick (PENDING). The flag is the lever that works.

What changes:
- No flagged groups are ever present, so every due tick becomes a tool draw.
- `gated[d]` never triggers, and nothing restarts the flying clock.
- The rate comes from the existing clock: gap = W / target × catch-up (`gapFor` `:15380`, `releaseGap` `:15402`).
  - Example, cavern 1 on P2_SAVR: W 26.8 days, target 6.5, so one group about every 4.1 days, about 20 a season.
  - A season's cavern cast is about 7-8 members, so each comes round 2-3 times, least-seen first (`V7.DRAW.pick` `:15908`).
- Land already spreads well (B1 savage: 16.9 effective species of 19), so the count stays about the same and only the chooser changes.
- The biggest gains are in the caverns (dominance P10, the 171-day empty cavern 3 P9, over-cap bursts P12) and in flying (coast ravens, the evil fort's starved fliers).

### 4. Risks and what breaks in (d)

1. **Writers that reopen entries.** `V7.reopened()` has 28 call sites (`:677`): season apply, reserve, exhaustion, spill, coupling, cast entries, patterns. Between such a write and the next close, a wave can slip in; B1 saw 2 waves in a day after a reopen. In this mode they must leave the flag alone, or the seal must close again straight after, as `cavePause` does with its counter.
2. **Coupling stops working as written.** Land coupling fires only on *fresh* DF waves (`:17375-17386` loops over `fresh` from `discoverGroups`; drawn groups never appear there). Under a seal it never fires. It must become "after drawing prey, draw a called predator next", which the water draw already does (~`:7510`).
3. **Innumerable entries.** The tool cannot draw from them (`apex.entries` reads `managedPops`, which skips `quantity_max >= INNUMERABLE`, `:1711`). Sealing them removes that species (for example Boardhelms' barn owl at 10000001) unless it gets a countable entry.
4. **Turning off or uninstalling.** `disableGroups` (`:17506`) reopens the pauses. A save made while sealed and then played without the tool has no DF wildlife. This is true today while a pause is on; in this mode it is certain.
5. **Undiscovered caverns.** `CAVE.survey` (`:5851`) maps caverns from edge blocks' `global_feature` and the `subterranean` flag, and nothing on the draw path checks discovery. So walkers can be drawn into a cavern nobody has found, as DF's own waves are (E13). Swimmers are refused, because cavern pools register only on discovery (`:8695`). Whether DF is content with that should be checked on the rig.
6. **What DF's waves did that the tool now does:** the enemy slot, the stay, and the population reference DF refunds from on walk-off (E9b; for tool-placed animals still unmeasured, see A4). Breeding needs that reference on this site. With `single_source` on, held copies sit at 0, so the draw lands on the chosen anchor or site entry. An off-site reference happens only with that rule off, or when a refund to a held copy is drawn within the ≤300 ticks before the hold pulls it back.
7. **Leaks.** Animal entries on the draw tiles that the seal misses would still send waves. The test counts them by entry.
8. **Fliers arrive on foot.** They are placed on walkable edge tiles. That changes how they look arriving, not what they do (inference).
9. **The pick becomes the whole abundance model.**
   - `V7.DRAW.pick` is least-seen first, with ladder odds only breaking ties. That gives even coverage but flattens the pyramid you asked for on 1 Oct ("apex present but rare"; apexes stay with the apex scheduler).
   - Warning: in B1 the savage marsh's ponds drew 19 of 19 ospreys, because only one species fit the draw's mass filter (P11).
   - Inference: give land, flying and cavern draws the water draw's balance and pyramid weights before making this the default.

### 5. What it could retire

As I read the code, this could all go:
- the release clock and `drainGate` (`:5492`);
- the tail join (`JOIN_TICKS`, P12);
- the cavern 4-day wait;
- DF fliers restarting the flying clock;
- the trims;
- the staged-reopen problem;
- the cavern open-stock levelling (P10);
- the cavern hold at FREQUENCY 0 (`cavernHold` `:16713`; the B2 "cavern gate (R44)" lines);
- the ladder's raw FREQUENCY writes.

The ladder lives on as the draw's odds (`cfg.odds`). Inference: with no FREQUENCY-0 writes, the cavern-freeze risk (cavern-zero-freq-freeze) goes away. Keep `keepAlive` anyway.

One sign of why this helps: on P2_COAST the tool drew OPOSSUM at Autumn 2 and DF's own OPOSSUM wave came at Autumn 3 (KAKAPO did the same at Autumn 6). While entries are open, DF and the tool pick independently. The one-group-per-species pause also stands down when no other species has an open entry.

| Aim | Effect of closing DF's sources |
|---|---|
| Diversity | Every arrival comes from the cast with least-seen first; DF's stock- and tile-weighted pick stops mattering |
| Pacing | One clock per layer; no 4-15-day DF gaps; no empty cavern 3 |
| Caps | One group per draw under the cap; no bursts or tail joins |
| Ecology | Neutral to positive once the pick gets pyramid weights and coupling a draw trigger |

This uses an existing lever, not a new cap (16 Oct). It is "pause, not trim" (13 Oct). It makes real your 9 Oct F19, "it alone controls how many". It is still a design change and your call.

### 6. The rig test that would settle it (not run; the rig is busy)

**Setup:**
- New embarks on the P2_SAVR and P2_COAST tiles (region6), 50 dwarves, caverns 1-3 breached, one full season per arm, B2's light probe.
- **Arm A:** v8.1 as it is.
- **Arm B** (small build): every managed surface entry, flying and water-bird entry, innumerable side row and cavern entry held closed all the time; draws on; `groups cavern draw_grace 0`; coupling triggered on drawn prey. No setting can hold the pauses closed below the cap today: they start only at the cap.

**Measure per layer:**
- flagged DF arrivals (B should be 0; name the entry of any leak);
- arrivals per season and days at 0;
- cast coverage, top species' share counted in waves, effective species;
- times over the cap;
- refunds on walk-off, and where references point;
- whether animal people still arrive;
- FPS and stalls.

**Optional:**
- an unbreached arm (does DF accept walkers drawn into an undiscovered cavern?);
- a never-release arm counting held DF groups per layer, which also settles shared versus per-source.

**Rig test that would settle it:** Two new embarks on the P2_SAVR and P2_COAST tiles (region6), 50 dwarves, caverns 1-3 breached, one season per arm. Arm A v8.1; arm B: a small build holding every surface Animal entry on the draw tiles (land, flying, water birds, innumerable side rows) and every cavern entry at depths 1-3 extinct-flagged all the time, draws on, `groups cavern draw_grace 0`, coupling triggered on drawn prey. Measure flagged DF arrivals (target 0; name leaks), arrivals/season, days at 0, coverage, top share by waves, effective species, over-cap, refunds and reference tiles, animal people, FPS, stalls. Optional: unbreached arm; never-release arm counting held groups (settles shared v per-source gate).

<details><summary>Review and verification trail</summary>

- review: Added the key correction to the user's picture: a wave 'waiting at the gate' is already on the map. The flag only stops its source sending another, so 'never release' cannot keep DF's animals off the map (discoverGroups :5414 files units already in world.units.active; releaseGroup :5456 only clears two flags).
- review: Added: there is no DFHack hook that runs before DF spawns a wave. eventful's UNIT_NEW_ACTIVE fires after the unit exists (DwarfCron/repos/dfhack plugins/eventful.cpp:98, :235). So 'block' can only mean closing the source, and 'wipe' can only mean removing the animal after it lands.
- review: Short answer: removed the flat claim that DF sends a new wave 'within about 450 ticks'. 266-450 ticks was measured with every other wild animal gone (E1, addendum 12). PLAN-v8.1 P2 records 4-15-day gaps in normal play and says what holds the gate then is unmeasured.
- review: Thought experiment (a) corrected. A held one-animal wave does not shut the gate (F1=C: open while at most one flagged animal is on the map), and many land waves are x1 (B2 COAST: OPOSSUM, KAKAPO, TIGER). So 'never release' holds about two DF groups per source, not one. Land is not fully starved either: the draw branch (:17423 detachOldest, else V7.DRAW.one) runs whenever no flagged group is present. It is throttled, not zeroed.
- review: Thought experiment (c): marked TR2's ~350-tick refill as a clean-test upper bound, since TR2 removed every wild surface animal. In normal play, with drawn animals on the map, the refill rate is unknown (P2).
- review: Cavern closing: the evidence is the 13 Oct cavern-pause probe (sw commit 8b473b7: 2 cavern waves in 25 days against 82, no stall), not E8, which was surface only. Added that cavern stock does NOT stop cavern waves (STATE addendum 51), so in the caverns only the extinct flag (or FREQUENCY) acts.
- review: Risk 3 (unbreached caverns) resolved from the code. CAVE.survey (:5851) reads each edge block's global_feature and the subterranean flag, PLACE.tiles (:5992) has no hidden check, and nothing checks discovery. So the tool can place into undiscovered caverns, as DF's own waves do (E13). What is left is a rig check, not a code gap.
- review: Added real evidence that draws work with entries closed: B2 P2_SAVR land paused at Summer 74, and the tool still drew CRETACEOUS_IGUANODON x5 (Summer 78) and BEAR_BLACK x1 (Summer 81) before land resumed at Autumn 1 (ROSTER.apex.entries :11563 checks quantity, not flags.extinct).
- review: Corrected the count: 28 V7.reopened() call sites, not 29 (the 29th match is the function definition at :677).
- review: Added flying numbers from the B2 ledger tails: COAST had 7 DF flying waves and 2 draws, SAVR 3 and 3. Re-checked the cavern tallies: SAVR 15 waves, 15 joins, 0 draws; COAST 19, 13, 0. Land matched: SAVR 6/6, COAST 4/7.
- review: Fixed a misattribution: B1's 'cavern 11 of 7' came from P12's over-cap bursts (several groups on one tick, a wave in pieces), not from held groups per source.
- review: Caveated the bugbat 56% figure: it counts groups, and bugbats split each wave into about 2.7 groups (cavern-pick-stock-weighted).
- review: The pond example was cited as a success, but B1's pond was 19 of 19 tool draws and all ospreys (P11: POOL_MAX_MASS). Added the lesson: when the tool has full control, its own filters and pick rule set diversity.
- review: Added the levers that could retire beyond the gate code: cavernHold's FREQUENCY-0 and stock-0 holds (:16713, B2 'cavern gate (R44)' lines), the ladder's raw FREQUENCY writes (:4586 etc.), which only steer DF's pick, the trims, the staged-reopen problem and the cavern open_stock leveling. With nothing writing FREQUENCY 0, the zero-frequency freeze risk also falls away. Inference, to verify.
- review: Added a design note. In this mode V7.DRAW.pick (:15908) becomes the only abundance model: least-seen first, with ladder odds only breaking ties. That is near round-robin within a season, which serves coverage but flattens the trophic pyramid the user asked for on 1 Oct, unlike the water draw's balance/pyramid/pull weights.
- review: Added a B2 COAST observation: OPOSSUM was drawn Autumn 2 and a DF OPOSSUM wave arrived Autumn 3; KAKAPO was drawn and a DF KAKAPO arrived the same day. While entries are open, DF and the tool can pick the same species.
- review: Rig test: noted that arm B needs a small build, because no config holds the pauses on below the cap (landPause :15735 / cavePause :16375 start only at the cap; resumeAt has a floor of 0). Added checks: read back drawn units' population refs (breeding-population-ref), any leak from unmanaged entries, and whether animal people still come (casts include TICK_MAN, FLY_MAN).
- verifier: Softened: 'stock does not stop cavern waves (addendum 51)' is the recorded 18 Sep finding but is unsettled. Only managed locals or only masters were zeroed, before the 9-tile finding, and the 17 Nov PENDING result suggests stock weights the pick. The extinct flag is the proven lever.
- verifier: Corrected the off-site reference risk. With single_source on, held copies sit at 0, so a draw lands on the chosen (anchor or site) entry. A neighbour-tile reference happens only with single_source off, or with a refund drawn in the ≤300-tick window.
- verifier: Added: land coupling fires only on fresh DF waves (:17375-17386), so under a seal it never fires. 'Draw the predator next' needs a new trigger on drawn prey.
- verifier: Added: the tool cannot draw from innumerable entries (managedPop :1711 skips them), so sealing the side rows removes such species unless the cast gives them a countable entry.
- verifier: Added: cavern swimmers are refused in an undiscovered cavern (pools register on discovery, :8695); walkers are not.
- verifier: Verb is `groups cavern draw_grace 0` (setting groups.cavern_draw_grace_days).

Code refs: sw-wt/plugin/scripts/seasonal-wildlife.lua:5369 (gatedLayer); sw-wt/plugin/scripts/seasonal-wildlife.lua:5413-5450 (JOIN_TICKS, discoverGroups); sw-wt/plugin/scripts/seasonal-wildlife.lua:5456-5481 (releaseGroup, detachOldest); sw-wt/plugin/scripts/seasonal-wildlife.lua:5492-5513 (V7.drainGate); sw-wt/plugin/scripts/seasonal-wildlife.lua:5152 (GROUPS_CADENCE 300); sw-wt/plugin/scripts/seasonal-wildlife.lua:677 (V7.reopened; 28 call sites); sw-wt/plugin/scripts/seasonal-wildlife.lua:5851-5911 (CAVE.survey: global_feature + subterranean, no hidden check); sw-wt/plugin/scripts/seasonal-wildlife.lua:5931 (CAVE.bandFor); sw-wt/plugin/scripts/seasonal-wildlife.lua:5992 (PLACE.tiles); sw-wt/plugin/scripts/seasonal-wildlife.lua:6045-6070 (PLACE.one); sw-wt/plugin/scripts/seasonal-wildlife.lua:7414 (ENGINE.groupSize); sw-wt/plugin/scripts/seasonal-wildlife.lua:7515 (ENGINE.count); sw-wt/plugin/scripts/seasonal-wildlife.lua:11563 (ROSTER.apex.entries: quantity>0, no extinct check); sw-wt/plugin/scripts/seasonal-wildlife.lua:11595-11677 (ROSTER.placeGroup); sw-wt/plugin/scripts/seasonal-wildlife.lua:15380-15412 (gapFor, dueTick, releaseGap); sw-wt/plugin/scripts/seasonal-wildlife.lua:15581-15636 (V7.GRP.cavernPass, gated[d]); sw-wt/plugin/scripts/seasonal-wildlife.lua:15641-15651 (land pause comment: per source); sw-wt/plugin/scripts/seasonal-wildlife.lua:15696 (V7.GRP.sideRows); sw-wt/plugin/scripts/seasonal-wildlife.lua:15722-15786 (landResume, landPause); sw-wt/plugin/scripts/seasonal-wildlife.lua:15871-15943 (V7.DRAW header, pick: least-seen then cfg.odds); sw-wt/plugin/scripts/seasonal-wildlife.lua:15945-16025 (V7.DRAW.one, flyTick, caveTick); sw-wt/plugin/scripts/seasonal-wildlife.lua:16038 (V7.GRP.flyGroups); sw-wt/plugin/scripts/seasonal-wildlife.lua:16075 (V7.GRP.flyPause); sw-wt/plugin/scripts/seasonal-wildlife.lua:16375-16420 (V7.GRP.cavePause); sw-wt/plugin/scripts/seasonal-wildlife.lua:16616 (keepAlive), 16713 (cavernHold); sw-wt/plugin/scripts/seasonal-wildlife.lua:16820-16862 (refundUnit, leaveCheck); sw-wt/plugin/scripts/seasonal-wildlife.lua:17407-17451 (groups pass: release else draw); sw-wt/plugin/scripts/seasonal-wildlife.lua:17506 (disableGroups); sw-wt/plugin/RESEARCH-NOTES.md:262-290 (section 9: E1, E8, E9a, E9b, E13, addenda 51-53 correction); sw-wt/plugin/STATE.md:655-680 (addenda 11-12: F1=C, F8, F9, F11); sw-wt/plugin/STATE.md:1896 (addendum 51: cavern stock does not gate cavern waves); sw-wt/plugin/STATE.md:3203-3230 (addendum 77, E40 cavern gate per source); sw-wt git 8b473b7 (13 Oct cavern-pause probe: 2 v 82 waves, no stall); sw-wt/plugin/docs/pacing/PLAN-v8.1.md:21-22 (P1, P2), 75-81 (B1 table: paused 68-89%, P9, P10, P11 ospreys, P12); DwarfCron/repos/dfhack/plugins/eventful.cpp:98,235 (UNIT_NEW_ACTIVE fires after creation); DwarfCron/data/pacing/B2/P2_SAVR/ledger.txt, P2_COAST/ledger.txt (tallies; SAVR draws during land pause Summer 78/81; COAST opossum/kakapo draw then DF wave); DwarfCron/data/pacing/mechanics-diagram.html ('waits flagged at the gate', 'no DF wave is waiting'); memory: pause-not-trim.md, cavern-zero-freq-freeze.md, cavern-pick-stock-weighted.md, df-wave-pick-per-entry.md, breeding-population-ref.md, ecology-design-rulings-oct1.md

</details>

## A2

> What would happen if... we didn't use the DF 'entry' for the tool's placements at all? What if all DF entries were deleted by seasonal-wildlife, or were zeroed out? Would that halt all DF-native animal placements? If so, could we then simply use seasonal-wildlife to directly manage ALL layer placements? What would happen? How much of the seasonal-wildlife code would break? How much of the code is dependent on the DF objects of 'entry' 'stock' and so on? What would happen if we switched the design philosophy to have seasonal-wildlife control everything directly while blocking, ignoring/wiping, or zeroing out all of the native DF animal placement mechanics? Looking at "Discover DF's waves: every unit still carrying DF's wave flag and not yet tracked" makes me wonder whether it's the case that seasonal-wildlife is still somehow allowing DF waves and its own placements to run side-by-side, since this looks like a targeted measure for combining the two competing mechanisms into the appearance of one. I think that fully suppressing DF's own waves is the best way to accomplish the kind of balance, pacing, and diversity that I want.

**Short answer.** Yes, fully suppressing DF's surface and cavern waves fits your aims, and your reading is right: today the tool runs two arrival systems side by side and stitches DF's waves into its own groups. But do it as a seal, not a deletion. Hold the extinct flag on every Animal entry and leave stock alone: DF can't pick a flagged entry, and the tool's draws never read the flag. Deleting entries breaks most of the tool, zeroing stock stops the tool's own draws, and FREQUENCY 0 has frozen DF.

*Status: corrected · confidence medium · review verdict: minor fixes*

### A2. What if DF's entries were deleted or zeroed, and the tool did all placement?

### Short answer
Yes. You can shut off DF's own surface and cavern waves and let the tool make every arrival, and most of the machinery already exists. But **how** you shut DF off matters:

- **Deleting entries breaks the tool.** Its records are kept by entry position.
- **Zeroing stock stops the tool's own draws.** Whether it even stops DF's cavern waves is unsettled.
- **Zeroing FREQUENCY has frozen DF.**
- **What works: the extinct flag on every Animal entry, with stock left alone.** DF cannot pick a flagged entry. The tool's draws never read the flag.

This is not a new mechanism. It is the land and cavern pause made permanent. In B1 those pauses were already on 80-89% of the time on land and 68-87% in the caverns, with no stall.

### 1. Why the tool still needs entries (code)

**Each placed animal borrows the entry's population reference.**
- `PLACE.one` (`seasonal-wildlife.lua:6045-6068`) creates the unit, copies the entry's six-field reference (`:6052-6054`), and clears both wave flags (`:6059-6060`).
- That reference does four things:
  - it makes the unit wildlife;
  - it gives the unit its wandering: 30/30 moved with a reference, 0/30 without (memory headless-unit-placement);
  - it is where DF refunds a walk-off (comment `:5176-5185`);
  - it decides breeding: a reference to another region tile stopped conception (0/5), while no reference at all still bred (14/15) (memory breeding-population-ref).

**Each placed animal takes stock from the entry.**
- `PLACE.fromEntry` refuses an empty entry (`:6112`) and debits one per animal (`:6162`).
- `ROSTER.placeGroup` does the same (`:11666-11671`).

**The draws read stock, never the flag.**
- `ROSTER.apex.entries` keeps entries with stock above 0, biggest first (`:11563-11573`).
- `V7.DRAW.pick` takes the first (`:15908-15943`).
- The water draw's `ENGINE.candidates` also needs stock (`:7337`).

So **a closed entry with stock is open to the tool and shut to DF.** That gap is exactly what you need.

The draw lands on the fort's own site-tile entry because of the one-entry-per-species rule (`V7.SRC.chosen`, `:3349`). Every other copy is held at 0 with the flag on (`applyLive` `:3909-3913`, `holdOutOfSeason` `:3931`). Keep that rule, or placed animals may carry an off-site reference and never breed.

### 2. The four ways to turn DF off

**Delete the entries.**
- What DF does is untested. Units point at entries by list position, so deleting one shifts every later position. The code avoids that deliberately: `ROSTER.FP.removeCreated` (`:10738-10790`) strips references first and removes only the last row.
- For the tool: placed animals lose wandering, wildlife status and refunds; there is no stock to draw; and the reserve and pause records, all keyed by position (`:10736`), point at the wrong entries. **Most of the tool breaks.**

**Zero the stock.**
- Surface: stock 0 stops a wave (E8).
- Caverns: unsettled. Addendum 52 zeroed the 109 managed local entries in one arm and the cave master lists in the other, and 30 and 33 cavern animals still came. But neither arm zeroed every local entry on all 9 draw tiles. And on 17 Nov DF's cavern pick looked stock-weighted (PENDING).
- For the tool: every draw finds "the entry is empty". **The tool's arrivals stop.**

**Set FREQUENCY to 0.**
- This suppresses a species. But if every stocked open Animal entry of one tile in one cave reads 0, DF freezes (memory cavern-zero-freq-freeze). A surface species set all at 0 also froze DF on 13 Oct (comment `:15647`).
- The tool already needs `V7.GRP.keepAlive` (`:16616`) to guard against this. **This is the riskiest lever.**

**Extinct flag on, stock kept.**
- Surface: E8 (STATE addendum 12) shows an emu entry at stock 50 with the flag on sent nothing, 3/3.
- Caverns: the 13 Oct probe (sw 8b473b7: 622/831/886 entries closed, cap 1, 25 days) let in 2 waves against 82 with the old trim, with no stall. Both waves came within two days of cavern 2 reopening under the cap.
- For the tool: nothing breaks. Stock, refunds, the reserve and the exhaustion check read exactly as now.

### 3. Your reading of "Discover DF's waves" is right

Today there are two arrival systems, merged so they look like one:
- `discoverGroups` (`:5414-5454`) files every flagged unit as one of the tool's groups.
- `detachOldest` and `releaseGroup` (`:5456-5490`) let a waiting DF wave in on the tool's clock.
- `V7.drainGate` (`:5492`) works around DF's rule that a layer's next wave waits while more than one flagged animal is on the map.
- The P12 tail join (`JOIN_TICKS`) exists only because a DF wave walks in over several passes.
- **DF goes first.** The groups pass releases a waiting DF wave before drawing (`:17421-17451`), and the caverns draw only after 4 quiet days (`V7.DRAW.caveTick` `:15997`). PLAN-v8.1 says it outright: "DF's waves still count first."

That hybrid came from the 16 Oct ruling to tune existing code, not from a decision that it was the best design. Your 9 Oct F19 points the other way: "it alone controls how many" (comment `:15637`).

### 4. What a full seal would and would not stop (DF behaviour)

**It stops:**
- Every surface wave from managed and innumerable entries on the draw tiles. That includes the shore and water species DF walks in today: in B1, 9 of 43 coast ocean arrivals (albatross, osprey, crab) and 5 of 39 savage-marsh river arrivals.
- Every cavern wave at depths 1-3, including DF's special-class arrivals (trolls, gorlaks, reachers, creeping eyes; STATE addendum 94) unless they are cast. That overrides D8 ("special classes left to DF") for caverns 1-3: **your call.** The cavern pause already does this whenever a depth is at its cap.

**It does not stop:**
- Animals already on the map: embark wildlife and their births. Under casts the tool adopts natives (`:16864-16886`).
- Vermin and fish. These are Vermin entries, and DF's fishing reads them (`:1655-1665`). Leave them open; zeroing "all entries" would end fishing.
- The magma sea and the underworld (D8).
- Things that don't come from population entries: forgotten beasts, megabeasts, titans, night creatures, werebeasts, sieges, caravans.
- Savage agitation of animals already here. E23 showed agitated attacks arrive through entries, so a seal removes those. Whether DF agitates tool-placed animals is **unknown**. The tool's own replacement, irruptions, is `enabled=false` in the code default (`IRRUPT.defaults` `:13735`), although your 16 Oct beta ruling turned irruptions on.

### 5. How much code depends on entries and stock

A rough grep (not checked function by function) finds about 95 functions touching entries, stock, the flag, references or the wave flag. They fall into three groups:

- **Steering or absorbing DF's waves. These go dormant; nothing breaks.**
  - `gatedLayer`, `discoverGroups`, `releaseGroup`, `detachOldest`, `drainGate`, `JOIN_TICKS`;
  - coupling by closing entries;
  - the cavern FREQUENCY holds and `keepAlive`;
  - the trims and P10 open-stock levelling.
  - Writing the ladder into the raws also stops. The ladder already feeds the draw as `cfg.odds` (`:11076`).
- **Using entries as reference and stock. These stay as they are.**
  - `PLACE.*`, `ROSTER.placeGroup`, `V7.DRAW.*`, the water draw;
  - `RESERVE.*`, `applyLive`, `holdOutOfSeason`, exhaustion;
  - `FP.materialise`, `refundUnit`, irruptions, and `off`'s give-back (`:3846`).
- **The pauses themselves.** These become the seal.

**Two things need rework, not just switching off:**
- **Land coupling.** It fires only on fresh DF waves (`:17375-17386`), so under a seal it never fires. It needs a "drawn prey → draw a called predator next" trigger, as the water draw has (~`:7510`).
- **Innumerable entries.** The tool cannot draw them (`managedPop` skips `quantity_max >= INNUMERABLE`, `:1711`). Sealing them removes that species unless it gets a countable entry.

### 6. What it would look like (inference from B1)

**Land, savage marsh:**
- 49 arrivals in 171.7 days, already at its cap 89% of the time. The tool can add only a few: at about 3.9 of 4 on the map, about 58.
- It was already diverse: 16.9 effective species of 19.
- The gain is control: off-cast arrivals go from 5 to 0, and least-seen-first brings every member round (coverage was 6/8, 7/8, 5/8 by season).

**Caverns and flying:** this is where DF's pick hurt most.
- flesh balls 54% of cavern 3 at the savage marsh;
- creeping eyes 64% at the evil fort;
- ravens 58% of coast flying;
- coast cavern 3 got no DF wave in 171 days.

Bugbats (51-56%) are partly a counting artefact: about 2.7 groups per wave, about 40% counted by waves. A tool-only cavern draw needs a stocked entry for each member at that depth.

**Caps:**
- They get closer to exact. B2's 8/7 and 9/7 cavern overshoots came largely from DF waves in flight.
- Apex placements, irruptions, adopted natives and births still add groups.
- On the surface, one group per species (`presentRaces` `:16210-16216`) means a layer whose cast is smaller than its cap stays under it. The coast's flying cast was 3 against a cap of 4. The caverns are exempt from that rule.

**Warning:** tool-only draws are only as diverse as each layer's candidate list. The savage marsh's ponds (code name "pool") were tool-drawn in B1: 19 arrivals, all osprey, the only candidate (weight 10.8 of 10.8).

**Undiscovered caverns:** nothing on the draw path checks discovery (`CAVE.survey` `:5851`). So walkers would be drawn into caverns the fort hasn't found, as DF's waves already are. Swimmers wait for discovery (`:8695`).

### 7. Risks
1. **28 writers can reopen an entry** (`V7.reopened()` call sites). The seal needs one place that closes everything again after any of them, as `cavePause` does with its counter and its re-check every 3,000 ticks.
2. **Innumerable entries** must be in the seal (`sideRows`), with the draw caveat above.
3. **A save made while sealed stays sealed.** If the tool is removed without `off`, the fort gets no DF wildlife. `off` must give every flag back.
4. **Savage and evil agitation changes** (section 4).
5. **D8 changes for caverns 1-3.**
6. **Tool-made units may differ from DF's** in ways not yet measured. Owner type and the enemy slot are already fixed (`:6056`, `:6070`). DFHack's docs say a created unit has no historical figure or group associations (Lua API.rst:1869).
7. **Don't shortcut with stock 0 or FREQUENCY 0.**

### Recommendation
The proposal serves your aims: diversity, pacing, seasonal balance, the tool deciding, fewer hacks. Most of B1's imbalance came from DF's pick. Build it as **a seal, not a deletion**:

1. **A switch** (a new verb, for example `groups df_waves off`; no such verb exists yet). While on:
   - every Animal entry on the draw tiles (managed and innumerable) and every cavern Animal entry at depths 1-3 keeps the flag;
   - stock is never touched;
   - Vermin and the deep are left alone.
2. **Every layer on the water loop:** due and under its cap → the tool draws (`groups cavern draw_grace 0`).
3. **No more FREQUENCY writes into the raws.** The ladder becomes draw weights only.
4. **Keep `discoverGroups` as a leak alarm only.**
5. **Coupling as a direct "draw the predator next"** triggered by drawn prey.
6. **Compute coverage offline** for each layer's candidate list first.

### Rig test that would settle it (not run: the rig is busy)
- **Setup:**
  - new 3x3 embarks, 50 dwarves, caverns 1-3 breached, same seeds, n=5 per arm, one season each;
  - arm A is v8.1; arm B is the seal plus tool-only draws.
- **Measure:**
  - units carrying the wave flag (target 0);
  - no stall;
  - per layer: occupancy, days at 0, effective species by waves, coverage, off-cast arrivals;
  - refunds;
  - site-referenced placed pairs conceiving;
  - fishing;
  - shore and water species now drawn by the tool;
  - the seal surviving save and reload, and `off` giving every flag back.
- **Savage sub-arm:** irritation pinned as in E23.
- **For knowledge only:** a cavern arm with every local cavern entry on all 9 draw tiles at stock 0 and the flag off.

**Rig test that would settle it:** New 3x3 breached embarks, 50 dwarves, same seeds, n=5 per arm, one season. Arm A v8.1; arm B the seal (extinct flag on every Animal entry on the draw tiles incl. innumerable, every cavern Animal entry at depths 1-3; stock untouched; re-closed after every writer) plus tool-only draws, `groups cavern draw_grace 0`, coupling on drawn prey. Measure flagged units (0), stalls, per-layer occupancy/days at 0/effective species by waves/coverage/off-cast, refunds, site-ref pairs conceiving, fishing, seal across save/reload, `off` restores. Savage sub-arm with irritation pinned (E23). Optional knowledge arm: all local cavern entries on all 9 tiles at stock 0, flag off.

<details><summary>Review and verification trail</summary>

- review: E23 removed as evidence for the extinct-flag lever. E23 ran on 18 Sep. That was before v6.3 (26 Sep) made a hold write both barriers, and STATE.md:296 records that the out-of-season hold of that time set stock 0 and left the flag alone. The flag-alone evidence is E8 (STATE.md addendum 12: emu stock 50 with the flag on, nothing in 3 of 3) and the cavern pause probe (sw 8b473b7).
- review: Corrected the cause of the 2 waves in the 13 Oct cavern pause probe. Commit 8b473b7 says both came 'within two days of cavern 2 reopening', which the pause does on purpose under the cap. They were not writers reopening entries between passes, as the original guessed. 8b473b7 also gives the scale: 622, 831 and 886 entries closed, and no stall.
- review: Hedged addendum 52 ('zeroing stock does not stop cavern waves'). Arm 1 zeroed only the 109 managed local entries. Arm 2 zeroed the cave master lists with the local entries untouched. Both ran before the 26 Sep finding that DF draws from all 9 neighbouring region tiles (memory df-region-draw-tiles). On 17 Nov DF's cavern pick looked stock-weighted (cavern-pick-stock-weighted, PENDING). So it is not proven. Zeroing is still the wrong lever, because it stops the tool's own draws.
- review: Water correction: DF does bring arrivals onto the water layers, as ordinary surface waves of shore and water species. In B1 that was 9 of 43 ocean arrivals at the coast (albatross, osprey, crab) and 5 of 39 river arrivals at the savage marsh (giant capybara, giant dragonfly, meganeura man). The seal stops these too. The land pause comment at 15639-15640 already closes 'the water rows DF also walks in from'.
- review: Natives correction: under season casts every native is adopted, land natives included, whatever natives_land says (seasonal-wildlife.lua:16873-16886).
- review: Count of V7.reopened() call sites corrected from 29 to 28. There are 29 occurrences, but one is the definition at line 677.
- review: Added a cost of deleting entries that the original missed: the tool's own reserve, its pause records and its managed-row cache are keyed by row index in world.populations.all (comment at 10736: the give-back 'is keyed by entry index'). Erasing a row shifts every later index. Whether DF rebuilds local entries from the region list at the next load is untested.
- review: Refined the breeding claim using memory breeding-population-ref. An off-site reference blocks breeding (0 of 5). A unit with no reference still breeds (14 of 15). So the reference matters for wandering, wildlife status and refunds, and for breeding only in that an off-site one blocks it. V7.DRAW.pick takes the member's biggest stocked entry (ROSTER.apex.entries sorts by stock). That is the site-tile entry only because single_source zeroes the held copies into the reserve.
- review: Added the framing the original missed: the seal is already in force most of the time. In B1 the land pause was on 80-89% of the run and the cavern pauses 68-87%, with every managed and innumerable surface entry closed and no stall. The proposal makes the pause permanent.
- review: Added counter-evidence on diversity. At the savage marsh, the ponds were drawn entirely by the tool and gave 19 arrivals, all osprey: the only candidate, at weight 10.8 of 10.8 (ledger). Under DF, the land layer was already diverse (16.9 effective species of 19). The gains are in the caverns and flying, plus control: no off-cast arrivals.
- review: Added that the bugbat dominance is partly a counting artefact: about 2.7 groups per DF wave, and about 40% when counted by waves (dominance/FINDINGS.md).
- review: Added the one-group-per-species limit. V7.GRP.presentRaces (16210-16216) counts surface groups and skips the caverns. A surface layer whose cast is smaller than its cap cannot be filled by the tool: the coast's flying cast has 3 members against a cap of 4. Softened 'the cap becomes exact', because apex placements, irruptions and adopted natives and births still add groups.
- review: Noted that the cavern grace window is already a setting (groups.cavern_draw_grace_days, 15999), so dropping it needs no code.
- review: Added the D8 policy point. Sealing every cavern Animal entry also stops the special-class cavern arrivals DF sends today (trolls, gorlaks, reachers, creeping eyes: STATE addendum 94) unless they are cast. The cavern pause already does this at the cap.
- review: Removed the coast cavern 3 'fills in about a month / target 6.5 of 7' figure. It is unsupported, and the draw also needs a stocked cavern 3 entry for each member.
- review: Labelled the '~95 functions, ~1,730 lines' count as an unverified rough grep.
- verifier: Added: under a seal, land coupling would never fire (it triggers only on fresh DF waves, :17375-17386); 'draw the predator next' needs a trigger on drawn prey.
- verifier: Added: innumerable entries cannot be drawn by the tool (managedPop :1711), so sealing them removes such species unless they get a countable entry.
- verifier: Irruptions: code default is enabled=false (IRRUPT.defaults :13735), but the user's 16 Oct beta ruling turned them on; stated both.
- verifier: Verb is `groups cavern draw_grace 0`; `groups df_waves off` is a proposed name, not an existing verb.
- verifier: Added: the tool can draw walkers into an undiscovered cavern (no discovery check); swimmers are refused until discovery.

Code refs: sw-wt/plugin/scripts/seasonal-wildlife.lua:6045-6068 (PLACE.one: copies the entry's population reference, clears both wave flags); sw-wt/plugin/scripts/seasonal-wildlife.lua:6111-6165 (PLACE.fromEntry: refuses an empty entry at 6112, debits per animal at 6162); sw-wt/plugin/scripts/seasonal-wildlife.lua:11563-11573 (ROSTER.apex.entries: stock > 0, biggest first, no flag check); sw-wt/plugin/scripts/seasonal-wildlife.lua:11595-11665 (ROSTER.placeGroup: debits while stock > 0); sw-wt/plugin/scripts/seasonal-wildlife.lua:15876-15880 (V7.DRAW rationale, user 16 Nov); sw-wt/plugin/scripts/seasonal-wildlife.lua:15908-15943 (V7.DRAW.pick: least seen first, cfg.odds weights, one per species); sw-wt/plugin/scripts/seasonal-wildlife.lua:15983-16010 (V7.DRAW.caveTick: grace window, setting cavern_draw_grace_days); sw-wt/plugin/scripts/seasonal-wildlife.lua:16210-16216 (V7.GRP.presentRaces: surface groups only, caverns exempt); sw-wt/plugin/scripts/seasonal-wildlife.lua:17420-17450 (groupsTick: release a DF wave first, else draw); sw-wt/plugin/scripts/seasonal-wildlife.lua:5162-5185 (DF gate per source; DF refunds from the reference, v5.3); sw-wt/plugin/scripts/seasonal-wildlife.lua:5369-5530 (gatedLayer, discoverGroups + JOIN_TICKS, releaseGroup, detachOldest, V7.drainGate); sw-wt/plugin/scripts/seasonal-wildlife.lua:3242-3253, 3349-3380 (V7.SRC one entry per species; chosen = anchor or site tile); sw-wt/plugin/scripts/seasonal-wildlife.lua:3875-3925 (applyLive: in-season reopen, out-of-season stock 0 + flag into the reserve); sw-wt/plugin/scripts/seasonal-wildlife.lua:3846-3873 (RESERVE.giveBack); sw-wt/plugin/scripts/seasonal-wildlife.lua:15637-15650 (F19; land pause: flag alone stops a draw; surface FREQUENCY 0 froze DF; water rows closed too); sw-wt/plugin/scripts/seasonal-wildlife.lua:15682-15713 (V7.GRP.sideRows: innumerable entries, flag only); sw-wt/plugin/scripts/seasonal-wildlife.lua:16375-16420 (V7.GRP.cavePause: re-close on V7.reopened counter and periodic re-check); sw-wt/plugin/scripts/seasonal-wildlife.lua:16616-16660 (V7.GRP.keepAlive); sw-wt/plugin/scripts/seasonal-wildlife.lua:16864-16886 (adoptNatives: under casts land natives adopted too); sw-wt/plugin/scripts/seasonal-wildlife.lua:10735-10790 (ROSTER.FP.removeCreated; reserve keyed by entry index); sw-wt/plugin/scripts/seasonal-wildlife.lua:11076 (cfg.odds set from the ladder); sw-wt/plugin/scripts/seasonal-wildlife.lua:677 (V7.reopened; 28 call sites); sw-wt/plugin/scripts/seasonal-wildlife.lua:1655-1665 (DF sends no water-feature waves; fishing reads Vermin entries); sw-wt/plugin/scripts/seasonal-wildlife.lua:7322-7340 (ENGINE.candidates: stock, not flag); sw-wt/plugin/STATE.md:673ff (addendum 12, E8: flag alone stops a surface draw); sw-wt/plugin/STATE.md:296 (pre-v6.3 hold set stock 0, flag left alone); sw-wt/plugin/STATE.md:1969ff (addendum 52: managed locals or masters zeroed, cavern units still came); sw-wt/plugin/STATE.md:2611ff (addendum 63, E23: closed roster gates agitation); sw-wt/plugin STATE addendum 94 (off-roster special-class cavern arrivals, D8); sw-wt/plugin git 8b473b7 (cavern pause probe: 2 waves v 82, no stall, 622/831/886 entries closed); sw-wt/plugin/docs/pacing/PLAN-v8.1.md:51 (DF's waves still count first); DwarfCron/data/pacing/B1/summary.md (paused %, arrivals by source, effective species, off-cast); DwarfCron/data/pacing/B1/PC_COAST|PC_SAVR/probe.jsonl (DF-sourced water-layer groups); DwarfCron/data/pacing/B1/PC_SAVR/ledger.txt (pond draws: osprey weight 10.8 of 10.8); DwarfCron/data/pacing/B2/master.log (cavern 8/7, 9/7); DwarfCron/.claude/scratch/pacing/dominance/FINDINGS.md (bugbat ~2.7 groups per wave; stock-weighted cavern pick); DwarfCron/repos/dfhack/docs/dev/Lua API.rst:1869 (units.create: no historical figure or group associations)

</details>

## A3

> What would happen if... NONE of the species groups on the map had been placed by DF? Would that mean that the mechanics such as "DF: wander, fight, eat, breed, die" would never be handled for those groups by DF? Does this mean that the groups currently placed by the tool are not 'seen' by DF at all, and so are not being handled by these native DF mechanics?

**Short answer.** Yes, DF sees and simulates tool-placed animals like any other unit. They wander (with the copied population reference), fight on written links, die, leave on their countdown, and survive save/reload. The diagram's 'eat' overstates it: DF runs no hunger for any wild animal, whoever placed it. 'Breed' is rare for both. The real differences are small and known: the tool must give the relation slot and owner type itself, and DF aims its own hunter links at newcomers that still carry the wave flag. 'Group' is the tool's idea; DF only sees single animals.

*Status: corrected · confidence high · review verdict: minor fixes*

### A3. If no group on the map came from DF, would DF still run their lives?

**Short answer: yes.** DF sees a tool-placed animal and simulates it like any other unit. The purple box in the diagram ("DF: wander, fight, eat, breed, die") is right about *who* acts. But **DF doesn't make any wild animal eat**, and breeding is rare for animals of either origin.

First, a clarification: **DF has no "group".** It sees single animals, plus an arrival gate: no new wave while more than one animal carrying the roaming flag is on the map. Whether that gate is one for the whole surface or one per source tile is unsettled (E1 suggests shared; region9 NAT and X5v75 suggest per source). A "group" (leader, cast, slots) exists only in the tool's records (`g.groups`). So the real question is whether DF sees the tool's animals. It does.

### 1. How the tool makes an animal (code)

**Every route ends in `PLACE.one`** (`seasonal-wildlife.lua:6045-6075`):
- land and flying draws: `V7.DRAW.one` → `ROSTER.placeGroup` `:11595`;
- water draws: `ENGINE.draw` `:7477`;
- `PLACE.fromEntry`, apex and irruption placements, and sponges.

The one exception is `ROSTER.placeBorrowed` (`:11919`), the console's cavern placement. It repeats the same writes inline (`:11946-11962`).

**DF's own factory makes the unit.** In the DFHack source, `Units::create` simply calls `df::global::unitst_more_convenient_create` (`repos/dfhack/library/modules/Units.cpp:1054`). The unit comes back with a full body, already in `world.units.all`.

**The tool then writes eight things** (the comment at `:5785-5797` lists the original six):
1. The entry's six-field population reference. This alone makes `isWildlife` true.
2. `leave_countdown`.
3. `owner_type = NONE` (v7.1; `create` leaves `PET_MASTER`).
4. Both roaming flags cleared.
5. `pos` and `idle_area`.
6. Insertion into `world.units.active`.
7. The tile occupancy bit, and `inactive = false`.
8. A relation slot (`PLACE.enemySlot` `:6090`, v5.9.3).

**Countdown.** A draw passes 25,000 (`cfg.water.countdown`, `:948`), varied ±20% per animal (`:11670`). `V7.GRP.cohere` then gives every member the leader's value (`sync_countdown`, default on, `:1021`, `:13544-13548`). Cavern borrows use `apex.residence`, 21,500 (`:11952`, `:9113`).

**Entry point.** Land draws seed within 12 tiles of the map edge (`:11651-11657`).

After that, DF's main loop handles the unit like any other active unit.

### 2. What DF does for placed animals (rig evidence)

| Diagram word | Tool-placed animals | Evidence |
|---|---|---|
| **wander** | Yes, given the reference. | 30/30 placed cod moved with it, 0/30 hake without (memory headless-unit-placement). A placed carp swam 6,6,94 → 18,39,93 in 2,191 ticks (addendum 47). |
| **fight / die** | Yes. DF runs the combat and records the killer. | E41e: placed jabberers killed 1/4 and 4/4 placed crundles with the relation written, 0/4 without it. `world.incidents` named killers in unbreached caverns (addendum 80). |
| **hunt without the tool** | Sometimes (section 3). | A placed lion with no relation written killed 8 badgers (eco-desk findings.md:241). A placed grizzly made 165 attacks on a native hippo (docs/v7.1/ecology.md:186). |
| **leave** | Yes, on DF's countdown. | Countdowns read exactly 25,000 − 5,155 after 5,155 ticks, and all six had moved (addendum 47). Send-off sets `leave_countdown = 0` (`dismissGroup` `:13576`) and DF walks them off. |
| **save / reload** | They survive. | 6/6 (addendum 47). |
| **refund on leaving** | Very likely, but **not directly measured** for a land or cavern draw. | DF refunds by the reference a unit carries, flagged or not (F9, E9b). That was measured on DF-wave and embark animals. Placed *water* entries top themselves up anyway (E31b), so X2 is not clean proof. INV3 was never run. Deaths are never refunded (F4). See A4. |
| **breed** | They conceive if the reference points at an entry **on this site**. | Placed sponge pairs were 5/5 pregnant on their own entry and 5/5 on another species' entry in the same cave. 0/5 with a reference to another region tile (memory breeding-population-ref). |

Note on species entries: the tool does not use the species' own cave entry for fertility. The comment at `:11880-11884` says fertility doesn't depend on it. The own entry is there so the debit and the refund land on the right species.

### 3. Where "DF does it" promises too much

**Eat: DF doesn't feed wild animals at all.**
- E19 (addendum 42): a kangaroo herd held for a season. Hunger and thirst stayed at 0, fat never fell, and nothing died or bred.
- That herd was a DF wave the tool had released, so its flags were cleared, the same state as a placed animal. Applying this to placed animals is inference; it wasn't measured on them.
- On the map, "eat" means kills, plus the tool's scavenging (docs/v7.1/scav.md).

**Who starts a hunt (the real difference).** RESEARCH-NOTES.md:296-303 (eco-desk RELS, RELS2b, RELP) shows DF writes its own `PREDATOR_OR_PREY` links in a pattern:
- **from every non-wild unit toward each new wild arrival.** "Non-wild" includes dwarves, livestock, pets, and any animal whose roaming flag was cleared, by a placement or a release;
- **between two wild surface animals almost never** (5 of 370);
- **between cavern wild animals, yes.**

So a placed predator is treated like a fort animal: DF aims it at newcomers the tool never linked it to. A released DF wave is in exactly the same position.

**Hunting in general.** Outside those DF links, predation is the tool's food-web write (`ecoWrite`, `:6337-6348`). With no written link, no predator attacked in 48 pairs (memory relation-write-needs-large-predator). That holds for both origins.

**Breed: pregnancy yes, birth within one visit unlikely, for any origin.**
- The sponge run covered about 121k ticks with 0 births in every arm, tame ones included.
- The births on record come from long stays: an embark carp gave birth at tick 217,006 (addendum 35).
- Inference: a 20-30k-tick visit leaves little time for births, whatever placed the animal. Gestation length was not measured.

### 4. What DF doesn't give a placed animal, and how the tool covers it
1. **The arrival gate.** A placed animal's flag is cleared, so it never holds the gate (`gatedLayer` `:5369-5370`). A released DF wave is the same (`releaseGroup` `:5456-5469`).
2. **The relation slot.** DF never slots a created unit (addendum 79). The tool gives one at placement (`PLACE.enemySlot`) and again via `ecoWrite` after a load.
3. **owner_type.** `create` leaves `PET_MASTER`. Fixed at placement (`:6056-6058`); `cohere` frees older units (`:13530-13533`).
4. **Belonging together** (inference). DF doesn't know a placed set is a pack. The members start within `ENGINE.RADIUS` of one seed tile, then the tool's leader lever holds them together (E28 halved the spread from about 10 tiles to 5, addendum 39). The same lever runs on DF-wave groups.
5. **Threat to dwarves** (not measured). DF gives fresh arrivals BENIGN or DANGEROUS_ANIMAL rows toward the fort (RELS2b). Whether a placed dangerous animal is treated as a threat the same way hasn't been checked.

Items 2 and 3 were found by running into them. A field-by-field comparison has never been done, so a third such gap can't be ruled out.

### 5. Thought experiment: an all-tool land layer (3x3 embark, like Fort 1)

The land cap is ⌊√9⌋+1 = 4 (`QUOTA.autoGroups` `:4441-4446`). Suppose all four groups are tool draws.

- **Arrival.** Each group comes in near the map edge. The entry goes down 1 per animal. Each animal gets a slot and a 20-30k countdown, synced to the leader's.
- **The stay.** DF wanders them and runs every fight on a written link. Deaths are final. Nothing gets hungry. Births are unlikely.
- **What fades.** DF's own links toward *new flagged* arrivals need such arrivals. On an all-tool map there are almost none, so DF-started hunts (the lion and badgers, the grizzly and hippo) fade. What DF writes between two placed animals is unmeasured. The tool's food web carries all predation, which fits your aim.
- **Leaving.** DF walks each one off at countdown 0. Inference: +1 refund to the entry it carries.
- **The gate.** None of the four carries the flag, so DF's gate is open. Any open land or flying entry will still get a DF wave. "No group from DF" holds only while the tool keeps every entry closed with the extinct flag (see A1/A2).

Edge cases:
- **Ponds, lakes, rivers.** DF places an embark cohort from water-feature entries, then never sends another (E20, E26). Every later water animal is tool-placed, and that layer works: E33 held 12/12 on 72 passes. This is the best proof that "the tool places everything" works.
- **Unbreached caverns.** Placement works the same way (no discovery check on walkers; swimmers wait for discovery, `:8695`). Fights are hidden but recorded in `world.incidents`.
- **An off-site reference.** The animals wander and leave but never conceive. The one-entry rule keeps draws on this site's entries.

### 6. Does this serve your aims?
Yes. A tool group is as alive to DF as a DF wave, and the tool decides species, size, timing and entry point. Three cautions:
- Predation (apart from DF aiming settled animals at newcomers), cohesion and "eating" are already the tool's work, for both origins.
- The real risks of "the tool places everything" are the open gate (A1/A2), the untested threat to dwarves, and any field `create` leaves unset. DF ignoring the animals is not a risk.
- An all-tool map makes the food web *more* the tool's to control.

**Suggested diagram wording:** "DF: wander, fight on written links, die, leave on countdown (rarely breed)". Drop "eat", or credit it to the tool's scavenging.

### 7. Rig tests that would settle the open points (not run)
1. **Field comparison** (cheap and decisive). Dump every field of a tool-drawn animal and of a released DF-wave animal of the same species, at arrival and at +3,000 ticks.
2. **Threat to the fort.** Place a dangerous species (for example a cougar) near outdoor dwarves, against a DF wave of the same species. Compare the relation rows toward citizens and the attacks on dwarves.
3. **A tool-only land season.** All land and flying entries flagged closed, tool draws only, against a control. Measure spread with cohesion off, DF-written links toward and between placed animals, kills from `world.incidents`, and exactly +1 per departure to the named land entry (INV3).
4. **Births.** Hold a placed herd of a mobile species for a year, with a native embark herd as control.

**Rig test that would settle it:** (1) Field-by-field dump of a tool-drawn animal v a released DF-wave animal of the same species at arrival and +3,000 ticks. (2) A placed dangerous species (e.g. cougar) near outdoor dwarves v a DF wave of the same species: relation rows toward citizens, attacks. (3) A tool-only land season (land and flying entries extinct-flagged) v control: spread with cohesion off, DF-written links toward/between placed animals, kills from world.incidents, +1 per departure to the named land entry (INV3). (4) A placed mobile herd held a full year v a native embark herd: births.

<details><summary>Review and verification trail</summary>

- review: Wrong reason for the species' own cave entry. The answer says the tool picks the species' own cave entry for fertility. The code comment says the opposite (seasonal-wildlife.lua:11880-11884, above ROSTER.caveEntryFor): fertility does not depend on it, and the own entry exists so the arrival debit and departure refund land on the right species. In the retest, sponges on ANOTHER species' entry in the same cave (the OLD arm) were also pregnant 5/5 (data/wild-breed/retest.log; retest-pairs.lua header). Only a reference to an entry on a different region tile failed (0/5). Per breeding-population-ref.md, that arm is not yet separated from a plant-type entry.
- review: Births evidence reframed. The run covered 16,887 to 137,723, about 121k ticks, not 137k (run.log). The TAME sponges in that same run were also pregnant 5/5 with 0 births, so 'no births' says nothing about placed versus DF animals. The sponges are immobile and were teleported into adjacent pairs, which are ideal conditions and not roaming animals. Added the native counter-evidence: embark-resident river carp gave birth at tick 217,006, and fish linger 150,000+ ticks past countdown zero (STATE addendum 35, :1284, :1296).
- review: Refund evidence was overstated. X2 (STATE:3873) and E31b (addendum 67) are both WATER feature entries, and DF tops those up to their maximum within 2,000 ticks on its own (addendum 67, STATE:2797-2830). So a water 'refund' cannot be told apart from the top-up. The direct rule is F9 (STATE:659-661): DF refunds a departing unit to the reference it carries, flag or no flag. That was measured on DF-wave units. That a tool-drawn LAND group is refunded is an inference: the INV3 test that would show it (docs/v7.1/roster.md:241) has no recorded result.
- review: Countdown corrected. A draw passes 25,000 (cfg.water.countdown, :948), but ROSTER.placeGroup multiplies it by 0.8-1.2 (:11668), giving 20,000-30,000. V7.GRP.cohere then sets every member to the leader's value, because sync_countdown is on by default (:1021, :13544-13548). ROSTER.placeBorrowed uses apex.residence, default 21,500 (:11952, :9113), not 25,000.
- review: Biggest gap added: DF treats every animal whose roaming flag is cleared (tool-placed AND released DF waves) as fort-side when it writes relations. It writes PREDATOR_OR_PREY FROM them TOWARD each new wild arrival (RESEARCH-NOTES.md:300-307; eco-desk findings.md RELS :258-261, RELS2b :404-410). So placed predators DO hunt without the tool's write: a placed lion with no relation killed 8 badgers (findings.md:241), and a placed grizzly made 165 attacks on a native hippo (docs/v7.1/ecology.md:186). The original section 3 said 'DF almost never starts the hunt' without this. On an all-tool map the targets of those DF writes (fresh, still-flagged arrivals) mostly disappear.
- review: New open question flagged. Arrivals get BENIGN/DANGEROUS_ANIMAL rows toward the fort (RELS2b). Whether DF gives a PLACED dangerous animal the same hostility toward dwarves was never measured. It matters for threat pacing on an all-tool map.
- review: Strengthened the 'eat' point. The E19 kangaroo herd was a DF wave the tool had already released, with its roaming flags cleared (STATE:1514-1516). It was in the same flag state as a placed animal, so the inference that placed animals are fed the same way is closer than the original answer said.
- review: Water edge case corrected. Not 'every water animal is tool-placed'. DF places a generous embark cohort from the feature entries (22 on RIVER4), and those animals stay and can breed. Only replacements after embark are tool-placed (STATE addendum 35; code comment :5774-5776).
- review: Clarified that DF has no 'group' object for either origin. DF sees units, plus one gate per source keyed on the roaming flag. A 'group' is the tool's own record (g.groups). This answers the user's 'not seen by DF' worry directly.
- review: Line refs tightened. The six-writes comment is at :5785-5797. PLACE.one has eight writes in total: the original six, plus owner_type NONE (v7.1) and the enemy slot (v5.9.3). Verified QUOTA.autoGroups (:4441-4446): a 3x3 embark gives 4 groups. Verified the land-draw edge entry (:11651-11657) and gatedLayer (:5369-5378).
- verifier: releaseGroup is at :5456-5469 (not :5446-5458).
- verifier: The surface gate was stated as 'one per source'. Whether it is shared across the surface or per source is unsettled: E1's two-tile hold suggests shared, region9 NAT/X5v75 and the code comments assume per source. What is solid: it stays open while at most one flagged animal is on the map.

Code refs: /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:5785-5797 (headless placement comment: six writes); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:6045-6075 (PLACE.one: create + ref + countdown + owner_type + flags + pos + active + occupancy + enemySlot); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:6090-6106 (PLACE.enemySlot); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:11595-11686 (ROSTER.placeGroup: edge seed :11651-11657, countdown x0.8-1.2 :11668, placed=true resident group); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:11880-11884 (caveEntryFor comment: fertility does NOT depend on own-species entry; off-site ref is the infertile case); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:11919-11963 (ROSTER.placeBorrowed inline writes; apex.residence countdown); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:9113 (apex residence = 21500); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:15945-15966 (V7.DRAW.one -> placeGroup with cfg.water.countdown or 25000); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:948 (water.countdown=25000); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:1021 (sync_countdown=true); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:13499-13549 (V7.GRP.cohere: PET_MASTER freeing, leader lever, countdown sync); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:13573-13580 (dismissGroup: leave_countdown 0); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:5369-5378 (gatedLayer: unflagged units never gate); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:5446-5458 (releaseGroup clears roaming flags on DF waves); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:6337-6348 (ecoWrite: slots unslotted units, writes PREDATOR_OR_PREY); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:4441-4446 (QUOTA.autoGroups: floor(sqrt(embark tiles))+1); /Users/nathanielcannon/Claude/Projects/DwarfCron/repos/dfhack/library/modules/Units.cpp:1054-1060 (Units::create -> unitst_more_convenient_create); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/STATE.md:655-662 (F4 deaths never refund; F9 DF refunds by the unit's reference); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/STATE.md:1274-1305 (addendum 35: embark river cohort, carp births at 217,006, fish linger); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/STATE.md:1428-1445 (addendum 39 E28 leader lever); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/STATE.md:1512-1527 (addendum 42 E19: released DF wave, hunger/thirst never run); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/STATE.md:1666-1716 (addenda 47-48: placement measured; E33 12/12 on 72 passes); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/STATE.md:2797-2830 (addendum 67: feature entries topped up within 2,000 ticks); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/STATE.md:3268-3300 (addenda 79-80: no slot from DF; E41e incidents); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/STATE.md:3873 (X2 water draw debit/refund); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/RESEARCH-NOTES.md:300-307 (corrected rule: DF writes P_O_P from non-wild incl. placed/released units toward arrivals); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/docs/v7.1/ecology.md:186 (placed grizzly fort-side, 165 attacks on native hippo); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/docs/v7.1/roster.md:241,252 (INV3 refunds test; placed units fort-side to DF); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/eco-desk/findings.md:241-245, 258-261, 404-410 (placed lion killed 8 badgers unrelated; RELP; RELS; RELS2b); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/wild-breed/run.log, retest.log, retest-pairs.lua (0 births in all arms incl. tame over ~121k ticks; FIX and OLD both 5/5 pregnant); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/mechanics-diagram.html:243, 1273 (diagram wording)

</details>

## A4

> If "DF refunds +1 to its entry per animal that walks off; a slot frees" are we certain that DF is triggering this count and slot refund for animals from groups placed by seasonal-wildlife?

**Short answer.** No, not certain. 'A slot frees' is the tool's own bookkeeping, so that part is certain, but it frees per group when the last animal has died or left, not per animal. 'DF refunds +1' has been measured only on animals DF spawned itself (wave and embark animals, including ones the tool released or sent off). For tool-placed animals it is likely, since they carry the same copied reference, but no land or cavern entry has ever been read across a placed group's departure. The tool also hands back +1 by hand for animals it removes after a failed send-off, assuming DF doesn't also refund those, which is unmeasured too.

*Status: corrected · confidence medium · review verdict: minor fixes*

### A4. Does DF really refund +1, and free a slot, for animals the tool placed?

### The direct answer
**No, we can't be sure.** The diagram line "DF refunds +1 to its entry per animal that walks off; a slot frees" combines two mechanisms, and the evidence for each is different.

| Part of the line | Who does it | For tool-placed groups |
|---|---|---|
| "a slot frees" | **the tool** (its group list) | **Certain.** It is the tool's code. It frees per group, not per animal. |
| "DF refunds +1 to its entry" | **DF** | **Likely, never measured.** All measurements are on animals DF spawned. |

There is a third piece the diagram leaves out: the **tool refunds by hand** in one case, and that rests on a second unmeasured assumption.

### (a) What the code does

**Every placement copies the population reference.**
- `PLACE.one` (`seasonal-wildlife.lua:6045-6068`) copies the entry's six-field reference onto the animal, sets a leave countdown, and clears both roaming flags.
- These routes debit the entry they copy from:
  - land, flying and cavern draws (`V7.DRAW.one` → `ROSTER.placeGroup`, debit at `:11671`);
  - apex and invasive placements, which also go through `placeGroup`;
  - water draws (`ENGINE.draw` `:7477-7478`);
  - `PLACE.fromEntry` (`:6156`);
  - irruptions (`:14636-14642`: the live entry, then the reserve).
- Two minor routes don't debit:
  - the sponge trail (`:12351`);
  - `ROSTER.placeBorrowed` (`:11919-11962`). Its `caveEntryFor` creates a new entry at quantity 0, or reuses one without debiting.
  - On those routes a working refund would raise stock above where it started.
- So wherever DF refunds by reference, the refund lands on the entry that was debited. The design depends on that.

**The slot is the tool's own count.**
- `gone()` (`:5379`) marks an animal "departed" if it no longer exists, is inactive, or has left `units.active` (`WILD.left`). It marks it "dead" if it died.
- `reconcileGroups` (`:5388-5404`) drops those animals and removes a group once its last member is gone.
- `ENGINE.count` (`:7515`) counts the groups that remain.
- So a slot frees **per group, when the last animal has died or left.** A death frees it too, but deaths are never refunded.

**The tool's own hand refund.**
- `V7.GRP.leaveCheck` (`:16836-16862`, v7.4, commit d2261cf) handles a group the tool sent off (season change, cap trim, `dismiss`) that is still on the map 7 days later (`leave_grace_days`). These are typically swimmers with no edge to leave by.
- It removes them with DF's vanish timer (`vanish_countdown = 1`). `V7.GRP.refundUnit` (`:16820-16834`) then adds **+1 by hand** to the matching managed entry, raising `quantity_max` if needed.
- Example from B2: P2_SAVR, Autumn 8, "FISH_CARP x4 ... taken off the map, 4 handed back to its population".
- No run has checked that DF does *not* also refund a vanished animal. If it does, each one is counted twice: the v5.3 defect on a smaller path.

**Otherwise the tool trusts DF's refund.**
- v5.3 removed the tool's general departure refund because DF already refunds; it had counted every resident twice (`:5176-5183`).
- Code that depends on DF's refund:
  - the hold (`holdOutOfSeason` `:3931`, every pass), which moves a refund on a resting entry into the reserve;
  - the cavern open-stock leveller (P10, `:3814-3830`);
  - the exhaustion check (`:4017`): "DF refunds a departing animal (E9b), so this is a species whose animals died."

### (b) What DF does: the evidence and what it covers
All of it is on animals **DF spawned itself**:
1. **Wave animals, held or detached** (E4/E9b, STATE.md:653-670):
   - a held skunk and a detached skunk left together, and their entry went 14→16;
   - a detached raven's entry went 354→355;
   - deaths never refunded (3/3).
2. **Wave animals whose countdown the tool zeroed** (T5, addendum 41). A detached kangaroo herd of four read 100→96 on arrival, then exactly +4 after it left. So a countdown the tool writes doesn't stop the refund.
3. **Embark animals** (addendum 30, STATE.md:1137-1144). One refund per departing unit, on its departure tick (platypus 308→310; hippo 294→298). The addendum only *inferred* that placed units would be refunded too.
4. **DF's refund is not capped at the entry's max** (G3, STATE.md:466-472). DFHack's `fix/wildlife` matches the same six fields but does cap (`repos/dfhack/scripts/fix/wildlife.lua:47-60`). That is DFHack's model, not proof of DF.
5. **DF does act on a placed animal's copied reference in other ways:**
   - it moves only with the reference (30/30 v 0/30);
   - it never breeds with an off-site reference;
   - it leaves on its written countdown (E33, addendum 48).

**The closest evidence for tool-placed animals:**
- **E31b** (addendum 67): 5 loach placed, entry 8784→8779, back to 8784 within 2,000 ticks with no animal gone. That is water-feature entries topping themselves up. It says nothing about the refund.
- **X2** (STATE.md:3873; readout trap #16): +1/+2 steps lined up with tool-drawn water groups leaving, netted against regrowth. Weak support, on entries that refill themselves. Land and cavern entries don't regrow within a season (E6).
- **Never measured:** a land or cavern entry read across a tool-placed group's departure.
  - INV3 (docs/v7.1/roster.md:241) was skipped as "NOT-TESTABLE-HERE" (data/alpha4-sec7/SECTION7-RESULTS.md:35).
  - B1/B2 can't answer it: `probe.jsonl` has no stock, and the ledger shows stock only at placement ("WOLF x7 placed from stock (16 -> 9)").

### (c) Inference
A placed animal matches the refunded animals in every field we know the refund uses:
- the same six-field reference;
- flags cleared, like E9b's detached animals;
- an ordinary countdown, like T5;
- and addendum 30 shows DF refunds animals it didn't send as waves.

So a refund is **likely**, but not proven. `dfhack.units.create` is not DF's own spawner, and it already left `owner_type` and the enemy slot wrong (`:6056`, `:6066`). Assumptions like this have been wrong twice before (memory breeding-population-ref).

### Thought experiment (B2 P2_COAST, real line "WOLF x7 placed from stock (16 -> 9)")
A drawn group's countdown is 20,000-30,000 ticks, about 17-25 days. A season is about 84 days, so most drawn groups leave within their season. The refund is what lets the same member be drawn again.

**If DF refunds:**
- the pack leaves around day 17-25;
- with one wolf killed, the entry reads 15;
- "exhausted" really means the animals died.

**If it doesn't:**
- the next pack takes the entry 9→2, the one after 2→0;
- within a season or two, "WOLF exhausted (stock 0, none on the map)" fires with no wolf dead, and a stand-in takes the slot;
- big-group species drain first (one draw each took IGUANODON 9→4, WILD_BOAR 22→17, BIRD_BUZZARD 13→8);
- in the caverns, the leveller hides the drain until the reserve is empty.

**The opposite failure, on the vanish path:** if DF *also* refunds a vanished animal, each one adds +2. Stock creeps up, and `quantity_max` is raised each time.

**Edge cases:**
- Enclosed ponds and cavern pools: those animals never walk off. They come back only through the hand refund, 7 days after a send-off.
- **Undiscovered caverns: the question does arise.** Nothing on the cavern draw path checks discovery. Walkers can be drawn into a cavern that touches the map edge; swimmers wait for discovery (`:8695`).
- A refund onto a resting entry moves to the reserve on the next pass. That is consistent with the design.

### What this means for your aims
Stock as a ledger (debit on arrival, refund on departure, deaths are real losses) is the right model for diversity and a believable food web. It is also the low-hack one, because DF keeps the books. But two assumptions in it are unmeasured:
1. DF refunds tool-placed animals.
2. DF does *not* refund vanished ones.

Since v8.1 the tool does most surface placing, so assumption 1 now governs most surface arrivals. Do **not** add a tool-side refund "just in case": that is the v5.3 double count. Measure first. Only if DF skips placed animals should `reconcileGroups` refund `grp.placed` departures (not deaths).

**Low-cost route:** a ledger line per placed animal that leaves, with its entry's quantity before and after. Every pacing run would then measure this for free. It is a code change, so it needs your approval.

**Diagram fix:** "DF refunds +1 per animal that walks off (measured for DF's own animals; for tool-placed animals assumed, test pending). The tool frees the slot when a group's last animal has died or left, and hands back +1 itself for animals it removes after a failed send-off."

### The rig test that would settle it (not run)
- **Where:** a fresh region9 test fort, never your save. Tool on, `groups cavern open_stock 0`, caverns breached.
- **Subject:** an in-season ground cast member with one site-tile entry and stock under 30. Any DF wave of that species onto that entry voids the rep.
- **Steps:**
  1. Read the entry quantity.
  2. Place N animals (expect −N).
  3. Run `groups dismiss <TOKEN>`.
  4. Every 100 ticks, read the quantity and each id's presence in `units.active`.
- **Pass:** +1 on each animal's departure tick.
- **Arms:**
  - kill one (no +1 expected);
  - a DF-wave animal detached the same way (the E9b/T5 control);
  - a cavern draw;
  - a flier;
  - vanish: a swimmer in an enclosed pond, `groups cavern leave 1`, dismiss; expect exactly +1, not +2.
- **Size:** n=5 per arm, fresh load per arm, order reversed.

**Rig test that would settle it:** Fresh region9 test fort (never the user's save), tool on, `groups cavern open_stock 0`, caverns breached. Subject: an in-season ground cast member with one site-tile entry, stock < 30. Read quantity; place N (expect -N); `groups dismiss TOKEN`; every 100 ticks read quantity and each id's units.active presence; void reps hit by a DF wave of that species. Pass = +1 per departure tick. Arms: kill one (no +1); detached DF-wave control (E9b/T5); cavern draw; flier; vanish (swimmer in an enclosed pond, `groups cavern leave 1`, dismiss: expect exactly +1, not +2). n=5 per arm, fresh load each, order reversed.

<details><summary>Review and verification trail</summary>

- review: Corrected the claim that 'the tool never refunds anything itself'. V7.GRP.leaveCheck (seasonal-wildlife.lua:16836-16862) calls V7.GRP.refundUnit (:16820-16834) and adds +1 by hand for each member of a sent-off group still on the map 7 days later (vanish_countdown = 1, quantity_max raised). It runs in every B1/B2 fort: ledger lines read '...taken off the map, N handed back to its population'. This rests on a second untested assumption, that DF does not also refund a vanished unit. If it does, each one counts twice.
- review: Corrected 'every placement uses placeGroup'. Water draws use ENGINE.draw (:7477-7478, own debit). PLACE.fromEntry (:6156) and the irruption path (:14638) each do their own debit. The sponge trail (:12351) and `roster depth place` / ROSTER.placeBorrowed (:11919-11962) do not debit at all, and placeBorrowed builds its own entry at quantity 0. All of them still copy a six-field reference, so the refund question applies to all of them.
- review: Added evidence the first answer missed. In addendum 30, DF refunded embark-spawned units (not wave units) on their exact departure tick (platypus 308->310, hippo +1 per departure; STATE.md:1137-1144). That weakens the worry that DF treats non-wave animals differently.
- review: Added T5 (addendum 41, STATE.md:1491-1497, 1541): a detached DF-wave kangaroo herd was dismissed by the tool zeroing its leave countdown, and DF refunded exactly 4 (100->96->98->102). So a countdown the tool writes does not block the refund. Those units were still spawned by DF.
- review: Softened 'neither can tell a refund from the top-up' for X2. Readout trap #16 records +1/+2 steps lining up with departures of tool-drawn groups, netted against regrowth of about +1 per 4,000 ticks. That is weak positive evidence, not none.
- review: Fixed timing: holdOutOfSeason runs every groups pass (about 300 ticks, :17287-17291), not only daily.
- review: Checked that B1/B2 probe.jsonl records only casts/day/gated/groups/layers/season/t/wild/year, with no stock series. Ledger stock appears only at placement. No natural experiment exists in the current data.
- review: Added a low-cost route: a ledger line at each placed animal's departure giving its entry's quantity, so every pacing run measures this. Warned against adding a tool-side refund 'just in case', because that is exactly the v5.3 double-count defect.
- review: Added a vanish-path arm to the rig test, and a guard against DF waves debiting the same entry during the measurement window.
- verifier: The edge case 'Unbreached caverns: no cavern draws take place' was wrong. Nothing on the cavern draw path checks breach or discovery (cavernPass -> caveTick -> placeGroup; CAVE.survey reads edge blocks' global_feature and subterranean only), so walkers can be drawn into an undiscovered cavern that touches the map edge; only swimmers wait for discovery (:8695). The refund question does arise there.

Code refs: /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:6045-6068 (PLACE.one: six-field reference copy, flags cleared, countdown); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:11595-11690 (ROSTER.placeGroup; debit :11671); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:15871-15881,15954 (V7.DRAW header and draw -> placeGroup, countdown water.countdown 25000); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:7474-7478 (ENGINE.draw water draws, own debit); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:6150-6158 (PLACE.fromEntry debit); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:14610-14645 (irruption: debit live then reserve); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:11919-11962 (ROSTER.placeBorrowed: no debit, entry built at 0); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:12351 (sponge placement, no debit); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:16810-16862 (V7.GRP.refundUnit + leaveCheck: tool's own +1 on vanished sent-off animals); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:5172-5183,5379-5404 (v5.3 note; gone(); reconcileGroups); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:4352-4361 (WILD.activeIds / WILD.left); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:7515-7523 (ENGINE.count: slots = groups); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:3925-3936,17287-17291 (holdOutOfSeason, every groups pass); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:3814-3820 (cave_open_stock leveller); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:4013-4017 (exhaustion relies on E9b refund); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:13573-13582,24284-24300 (dismissGroup; groups dismiss verb); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/STATE.md:653-670 (addendum 11 E4/E9b/F11/F15); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/STATE.md:1137-1144 (addendum 30: embark units refunded on departure tick); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/STATE.md:1491-1497,1541 (addendum 41 T5: dismissed detached herd refunded exactly 4); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/STATE.md:466-472 (G3: DF refund uncapped); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/STATE.md:1666-1740 (addenda 47-48: headless placement, placed units leave on countdowns); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/STATE.md:2797-2825 (addendum 67 E31b: top-up, not refund); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/STATE.md:3873 (X2 Driver B: 'a leaving group refunds it'); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/docs/v7.1/roster.md:241,252,254 (INV3; desk R28.5); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/alpha4-sec7/SECTION7-RESULTS.md:35 (INV3 NOT-TESTABLE-HERE); /Users/nathanielcannon/Claude/Projects/DwarfCron/repos/dfhack/scripts/fix/wildlife.lua:47-61 (refund_population six-field match, capped); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/mechanics-diagram.html:251,275,1271,1306 (refund lines); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/B2/P2_COAST/ledger.txt (placed-from-stock lines; 'handed back to its population'; exhaustion lines); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/B2/P2_SAVR/ledger.txt (FISH_CARP x4 handed back); /Users/nathanielcannon/.claude/projects/-Users-nathanielcannon-Claude-Projects-DwarfCron/memory/experiment-readout-traps.md:61 (trap #16, X2 refund netting)

</details>

## A5

> Define "one open entry". Is an entry what points a species to a slot?

**Short answer.** No. An entry is DF's population record for one species in one place: where it can come from and how many are left, with an extinct flag that opens or closes it. A slot is a role in the tool's cast (apex, grazer, flier and so on), which is why that species is cast this season. 'One open entry' means that, of all the copies DF stocked for a cast species, the tool keeps exactly one open per season (one on the surface, plus one per cavern depth it is cast in) and holds the rest in its reserve. The two meet only when a member runs out and a stand-in for the same slot gets its own entries opened.

*Status: verified · confidence high · review verdict: minor fixes*

### A5. What is "one open entry"? Does an entry point a species to a slot?

### Short answer
**No.** Three different things live in three different places:

| | What it is | Where it lives | What it decides |
|---|---|---|---|
| **Entry** | One of DF's population records: one species in one place (a region tile, one cave on one tile, or a water feature) | DF's world (`world.populations.all`); the tool edits only its numbers | **Where** a species can come from and **how many** are left (stock), plus an **extinct flag** that opens or closes it |
| **Slot** | A role in one layer's cast for one season: apex, mid predator, grazer, ground prey, flier, sentient... | The tool's cast record (`NR.toRecord`, `seasonal-wildlife.lua:23355-23371`) | **Why** that species is in this season's cast |
| **FREQUENCY** | A number in the species' raws | The creature raw: one per species, not per entry | **How often** DF picks the species when a wave is due |

The SAVR_d1 dump shows the split. Cavern 1's spring slots read `APX: BLIND_CAVE_BEAR, PL: DRALTHA, SN: TROLL, …`, and nothing in that record names an entry.

**The order runs one way:**
1. The cast builder seats species in slots.
2. `ROSTER.FP.materialise` (`:10564`) makes sure each cast member has an entry where it is needed.
3. `V7.SRC.chosen` (`:3349`) keeps one of that species' entries open.

So an entry is the **door** a cast member comes through, plus a count of how many can still come.

**Where the two meet:** when a member's stock runs out, `ROSTER.exhaustCheck` (`:3996-4097`) picks a stand-in that fits the **same slot** (`castReplaceOk` checks the slot) and opens the stand-in's **own** entries. The slot decides who replaces whom; the entry is just the tap.

**The page blurs this in two places:**
- **Panel 1:** "DF refunds +1 to its entry...; **a slot frees**". This "slot" means room under the group cap, and it frees per group, when the last animal has died or left (`reconcileGroups` `:5388-5404`). It should say "room under the cap frees".
- **Gate 2:** "Its open entry has stock? no → exhausted after a day". The code counts the open entry **plus** the reserve held for the species' other copies. A species is exhausted only when that total is 0 **and** none is on the map, held for a full day (`:4007-4017`, `EXHAUST_SETTLE = TICKS_PER_DAY` `:3962`). Before that, `V7.SRC.topUp` (`:3766`) refills the open entry from a held copy.

### What "one open entry" means, exactly

**What DF does (rig):**
- DF often stocks one species in many entries: on the surface one per region tile (a straddling fort has 2-4 site tiles); in the caverns one per tile and per cave.
- X9c1 (16 Oct) counted **16-40 cavern entries** for each species DF stocked, against 1 for each the tool created (commit 9f7459f).
- DF picks a surface wave **per entry**, and FREQUENCY sits on the species, so every extra entry is another ticket. TR2 (15 Oct): a flier open on 5 tiles took **124 of 161 waves (77%)** against the same flier on 1. Big site tiles drew 40-58 waves per entry; neighbour tiles 5-10 (memory df-wave-pick-per-entry; comment `:3242-3247`).
- Walkers come only from the site's own tiles. Fliers also come from the 8 neighbours (X6xw2, `:10601-10603`).
- In the caverns, every one-entry species arrived **0 times** all year in X9c1.

**What the code does.** `groups.single_source` has been on by default since v7.5 (d1e198a), and `cave_single_source` since v7.6.1 (9f7459f) (`:1029-1030`).

**Surface.** `V7.SRC.chosen` scores each in-season surface Animal entry (`:3360-3363`):
- +3e9 if it is on the **anchor tile**;
- +1e9 if it is on any site tile;
- plus map area × 1000;
- plus stock (capped at 999).

The best score wins. The anchor is the site tile covering most of the map (`V7.SRC.footprint` `:3257-3291`). The result is **one open surface entry per species**, shared by the ground and flying casts. An anchor entry wins even when it is empty; `topUp` then moves a held copy's reserve into it.

**Caverns: one open entry per species per depth it is cast in.**
- Each depth has an anchor group: one tile's entries in one cave (`V7.SRC.caveAnchors` `:3318-3346`).
- That group is chosen first by the cave with the widest opening at the map edge, then by being on a site tile, then by having the most species.
- The cavern score is the anchor (3e9), site (1e9) and stock, with no area term.

**Every other copy is held.**
- `V7.SRC.isDup` (`:3381`) makes `ROSTER.wantsRow` refuse the duplicates.
- `holdOutOfSeason` (`:3931-3953`) moves their stock into the reserve and sets the flag. It runs at the season change, daily (`:5127`) and every groups pass (300 ticks, `:17292`).
- Nothing is deleted. `off` gives everything back (`RESERVE.held` `:3745`).

**Open also needs stock.**
- `topUp` refills a dry open entry from a held copy.
- In the caverns, the open entry is levelled to at most **30** animals and the rest waits in its reserve (P10, `:3812-3830`; PENDING, aimed at DF's stock-weighted cavern pick).

**Open doesn't always mean pickable.** These pauses close the open entry with the flag only (stock and FREQUENCY untouched):
- the land pause at the cap;
- one group per species (`V7.GRP.speciesPause` `:16190-16240`; not used in the caverns);
- the bird pause;
- the flying pause;
- the cavern pause.

**Entries the tool creates** (`FP.popCounts` `:10544-10551`, `materialise` `:10697-10715`) cover:
- cast members DF never stocked here;
- cast walkers or fliers with no entry on a site tile or the anchor (`:10606-10618`);
- cavern members missing from their depth's anchor group.

The stock is the midpoint of the raw's POPULATION_NUMBER, or 22 when the raws give none.

**Who uses the open entry:**
1. **DF's wave pick.** Each open entry is one ticket, weighted by FREQUENCY × tile weight.
2. **The tool's own draw** (`V7.DRAW.pick` `:15908-15943`), when DF has nothing waiting:
   - least-seen member first, ladder odds among those;
   - it takes that species' largest stocked entry (`ROSTER.apex.entries` `:11563`), at that depth for a cavern draw;
   - it doesn't read the flag. It lands on the open entry only because held copies sit at 0; a refund on a held copy is drawable for up to 300 ticks (rare);
   - `placeGroup` debits 1 per animal (`:11666-11671`), and `PLACE.one` copies the reference (`:6052-6054`).
   - That reference is where DF refunds the animal and what decides breeding: an off-site reference blocks conception (memory breeding-population-ref).

### Worked example (illustrative numbers, real rules)
A fort straddles site tiles **A** (70% of the map, the anchor) and **B** (30%). **N** is a neighbour tile.

- **Wolves.** DF stocked them on A (40), B (25) and N (60).
  - Without the rule, three tickets. Walking waves come from A and B; N counts only for fliers.
  - With the rule, A wins. B and N are held (85 in the reserve). One ticket on A.
- **Hares.** DF stocked them only on B (60). Materialise makes an A entry if A's biome suits hares; it wins, and B is held.

Wolf and hare now hold one ticket each on the same tile, so **FREQUENCY alone sets their odds**. In SAVR's winter ground cast, the wolf's ladder value is 1 and the giant hamster's is 44. When A's 40 wolves run out, `topUp` moves a held reserve in.

### Edge cases
- **The anchor's biome doesn't suit the species.** Materialise uses only site tiles whose biome fits (about `:10685-10688`). If only B fits, the hare stays open on B. TR2 suggests a smaller tile draws less, but that is inference; the exact tile weight is still open. If no site tile fits, the code falls back to all site tiles.
- **Ponds, lakes, rivers.** Water-feature entries are outside the rule (`V7.SRC.isRow` `:3292`). DF sends no waves from them; the water layer places from them.
- **Vermin** are outside the rule.
- **`groups single off`.** Every copy is open again, and the odds go back to FREQUENCY × summed tile weights.
- **Unbreached caverns.** Anchors and open entries are still chosen, and DF and the tool can both send walkers into an undiscovered cavern (no discovery check on the draw path).

### Does this serve your aims?
Yes. With one entry per species, the ladder decides the mix, not how many tiles DF happened to stock. That gives you direct control over diversity and pacing with no extra caps. The one soft spot is the off-anchor species, which holds one ticket on a lighter tile.

**Page fixes I'd make:**
1. Panel 1: "a slot frees" → "room under the cap frees (when a group's last animal has gone)".
2. Gate 2: count the whole stock (open entry + held copies) and the none-on-the-map condition.
3. Panel 6, "Pick": walkers come from site tiles only; fliers also from the 8 neighbours.
4. Glossary: "open entry = the one place DF may send this species from this season".

### Rig tests
The definition comes from the code, so it needs no test. One related point needs the rig:
- **Off-anchor odds.** On a straddling fort, read `V7.SRC.chosen` once to list each cast species' open entry tile. The `groups single` status line can't do this: it prints only the anchor and counts. Then run a season and compare waves per species at equal FREQUENCY, anchor against off-anchor.

Cavern stock-weighting is already PENDING in B2.

**Rig test that would settle it:** None for the definition. Optional: on a fort straddling two site tiles, one read of V7.SRC.chosen listing each cast species' open entry tile (not the `groups single` status line, which shows only the anchor and counts); then one season comparing waves per species at equal FREQUENCY, anchor v smaller site tile. Cavern stock-weighting is already PENDING in B2.

<details><summary>Review and verification trail</summary>

- review: Fixed the proposed rig test. The `groups single` status line (seasonal-wildlife.lua:24209-24225) prints only the anchor tile, its share of the map and counts (species open, copies held). It does not list each species' open entry tile, so the test as written could not be read off it. The test now uses a one-shot read of V7.SRC.chosen on the rig.
- review: Corrected the edge case about materialise. If none of the site tiles suits the species' biomes, the code falls back to ALL site tiles (`if #tiles == 0 then tiles = siteT end`, :10677), so the entry lands on the anchor anyway. If some site tiles suit but the anchor does not, no anchor entry is made and the species stays open off the anchor. The draft only described the second case.
- review: Corrected where DF's surface pick looks. Walking waves come only from the site's own region tiles. Fliers also come from the neighbours. Sources: the materialise comment at :10601-10603 (X6xw2) and memory df-region-draw-tiles. The draft said 'site tile and its neighbours' for everything, and panel 6 line 1269 of the page repeats that.
- review: Added the second place on the page that ties an entry to a slot: the 'How one species ends up on the map' gate 2 ('Its open entry has stock? no -> exhausted after a day; a stand-in takes the slot'). The code counts the species' whole stock: the open entry plus its held copies' reserve (exhaustCheck :4007-4008, topUp :3766). A species is exhausted only when that reads 0, none of it is on the map, and both have held for a day (EXHAUST_SETTLE = TICKS_PER_DAY, :3962). The gate wording oversimplifies this.
- review: Made explicit that three things live in three places. FREQUENCY is per species, in the creature raw. Stock and the extinct flag are per entry. The role is per cast slot. This is why the number of entries multiplied a species' odds.
- review: Added that the tool's own draw (V7.DRAW.pick :15918-15925 via ROSTER.apex.entries :11563) takes the stocked entry with the most animals and ignores the extinct flag. It equals the open entry only because held copies sit at 0. A refund onto a held copy is drawable for up to 300 ticks (an edge case).
- review: Made the tool's draw explicit: it also works in the caverns (P9, depth-matched entry, :15919-15923). It picks the least-seen member first and uses the ladder (cfg.odds) as weights.
- review: Labelled the SAVR numbers as the winter ground cast. The dump's live FREQUENCY column shows other values (wolf 5, giant hamster 50) because it was read in another season.
- review: Softened the water claim to what the code says: the V7.SRC header comment says DF draws no wave per tile from water-feature rows (:3253), and the water layer places from its own entry (:10660-10661).
- review: Fixed the TR2 wording. Two species swapped roles, one open on 5 tiles and one on 1, and the 5-tile side took 124 of 161 waves.
- verifier: Minor: FP.materialise's biome-matched site tiles and fallback are at about :10685-10688 (not :10672-10677). The cavern score in V7.SRC.chosen has no map-area term (anchor 3e9 + site 1e9 + stock). No change to the conclusions.

Code refs: sw-wt/plugin/scripts/seasonal-wildlife.lua:1029-1030 (single_source, cave_single_source defaults); sw-wt/plugin/scripts/seasonal-wildlife.lua:3240-3254 (V7.SRC header: TR2, why one entry); sw-wt/plugin/scripts/seasonal-wildlife.lua:3257-3291 (V7.SRC.footprint: anchor tile); sw-wt/plugin/scripts/seasonal-wildlife.lua:3292-3296 (V7.SRC.isRow); sw-wt/plugin/scripts/seasonal-wildlife.lua:3298-3346 (caveOn, caveAnchors: edge, site, species); sw-wt/plugin/scripts/seasonal-wildlife.lua:3349-3379 (V7.SRC.chosen scoring); sw-wt/plugin/scripts/seasonal-wildlife.lua:3381-3397 (isDup, ROSTER.wantsRow); sw-wt/plugin/scripts/seasonal-wildlife.lua:3678-3760 (RESERVE, mark, held); sw-wt/plugin/scripts/seasonal-wildlife.lua:3766-3830 (V7.SRC.topUp, cave open stock 30); sw-wt/plugin/scripts/seasonal-wildlife.lua:3931-3953 (holdOutOfSeason); sw-wt/plugin/scripts/seasonal-wildlife.lua:3962 (EXHAUST_SETTLE = TICKS_PER_DAY); sw-wt/plugin/scripts/seasonal-wildlife.lua:3996-4097 (ROSTER.exhaustCheck: held reserve counted, stand-in by cast slot); sw-wt/plugin/scripts/seasonal-wildlife.lua:11105-11113 (castReplaceOk slot check); sw-wt/plugin/scripts/seasonal-wildlife.lua:5127 (daily hold); sw-wt/plugin/scripts/seasonal-wildlife.lua:6045-6066 (PLACE.one copies population ref); sw-wt/plugin/scripts/seasonal-wildlife.lua:10544-10551 (FP.popCounts); sw-wt/plugin/scripts/seasonal-wildlife.lua:10561-10730 (FP.materialise: anchor need, biome-matched site tiles, fallback :10677); sw-wt/plugin/scripts/seasonal-wildlife.lua:11563-11573 (ROSTER.apex.entries: largest stock, no extinct check); sw-wt/plugin/scripts/seasonal-wildlife.lua:11666-11671 (placeGroup stock debit); sw-wt/plugin/scripts/seasonal-wildlife.lua:15900-15944 (V7.DRAW.pick: least seen, ladder weights, depth entry); sw-wt/plugin/scripts/seasonal-wildlife.lua:16190-16240 (one group per species pause); sw-wt/plugin/scripts/seasonal-wildlife.lua:17286-17292 (hold every 300 ticks); sw-wt/plugin/scripts/seasonal-wildlife.lua:23355-23371 (NR.toRecord: slots, codes); sw-wt/plugin/scripts/seasonal-wildlife.lua:24192-24226 (groups single verb; status shows anchor + counts only); DwarfCron/data/pacing/mechanics-diagram.html:117-118 (glossary), 250-253 (panel 1 'a slot frees'), 1269 (pick tiles), 1295 (gate 2), 1122-1124 (panel 3); DwarfCron/.claude/scratch/pacing/ladder/SAVR_d1.json (cavern1 spring slots; winter ground WOLF 1, GIANT_HAMSTER 44); memory: df-wave-pick-per-entry.md, df-region-draw-tiles.md, breeding-population-ref.md, cavern-pick-stock-weighted.md; git: d1e198a (v7.5 one entry per species), 9f7459f (v7.6.1 cavern one entry, X9c1 16-40 entries)

</details>

## A6

> Does "Active: entries stocked. One open entry per species: on the surface, the anchor tile's (the fort's own region tile)" mean that for each new season after the first that open entries are given to species based on the REGION? Or are entries given to species based on the candidate list that the tool generated?

**Short answer.** Entries go to species from the cast the tool built out of its candidate list, never from the region. At each season change only this season's cast members (plus exhaustion stand-ins and your pins) keep an open entry; every other species' entries are held at 0 with the flag on, re-checked every pass. The region only decides WHERE the one open entry sits (the anchor tile, the site tile covering most of the map), and it has a small say earlier in who gets onto the candidate list (biome filter; DF-stocked species skip some gates). The casts are built once and the same four seasons repeat every year.

*Status: verified · confidence high · review verdict: minor fixes*

### A6. Are open entries given by region, or by the tool's candidate list?

### Short answer
**The cast decides who gets an open entry. The region decides only where it is.**

You've read it right: entries go to species from the candidate list the tool built, through this season's cast, never from the region. The page line "One open entry per species: on the surface, the anchor tile's..." describes the *location* of each cast member's one open entry, not *which* species get one.

The same rule runs at every season change, the first included. The casts are built once, and the same four seasons repeat every year.

### (a) What the code does

**Who is open: this season's cast.**
- Casts are built once, at enable, `cast rebuild` or `roster build` (`ROSTER.castYear`, `seasonal-wildlife.lua:10817`; callers `:20926`, `:24916`, `:25024`; `:21215` only migrates old saves).
- No new casts are built at a new year ("no new casts at a new year (user 9 Oct)", `:9598`). The one exception: a water layer found later is added on its own (`castMissingLayers` `:10900`).
- `castYear` draws each layer's four season casts from the candidate list (`NR.listOf`), then writes the roster:
  - every species cast in any season gets `allow=true` and its cast seasons;
  - every other species those layers manage is set to resting (`:10871-10879`).
- At each season change, `applyLive` (`:3876`) asks `ROSTER.wantsRow` for every managed entry. That checks `allow` and the season (`ROSTER.wants` `:3216`).
- A "no" holds the entry: stock to the reserve, quantity 0, extinct flag set (`:3909-3913`).
- `holdOutOfSeason` (`:3931`) repeats the hold every pass (about 300 ticks) and daily, so a refund DF hands back to a resting entry is pulled back. This is the S1 dingo case (`:3920-3925`).
- **Only two kinds of non-cast species can be open:**
  - exhaustion stand-ins: members of another season's cast, borrowed when a member runs out ("Inactive species are never promoted", `:3952-3960`);
  - your pins (`ROSTER.applyPins` `:3100`, applied at `:10882`).
- Both come from your casts or your choices, never from DF's region list.

**Where the open entry sits: the anchor rule** (`groups.single_source` and `cave_single_source`, both on by default, `:1029-1030`).
- **Surface.** `V7.SRC.footprint` (`:3257-3291`) finds the anchor, the site tile covering the most of the map. On a straddling fort, "the fort's own region tile" means the biggest of its 2-4 site tiles.
- `V7.SRC.chosen` (`:3349-3379`) scores each in-season surface Animal entry of a cast species:
  - anchor +3e9;
  - any site tile +1e9;
  - then map share;
  - then stock.
- The best score stays open. `V7.SRC.isDup` (`:3381`) makes `wantsRow` refuse every other copy, so those are held. `V7.SRC.topUp` (`:3766`) moves a held copy's reserve in when the open one runs dry.
- **Caverns.** The same rule runs per depth. The anchor group is in the cave with the widest opening at the map edge, then a site tile, then the most species (`V7.SRC.caveAnchors` `:3318`). The open cavern entry holds at most 30 (P10, PENDING).

**Where entries come from when DF has none.** `ROSTER.FP.materialise` (`:10564`) runs once, inside `castYear` (its only caller), not at each season change. It creates entries for:
- cast species with no entry in the embark area;
- cast ground and flying species DF stocked only off the site tiles, or not on the anchor (`:10606-10618`);
- cavern cast species missing from their depth's anchor group.

New surface entries go on the site tiles whose biome fits the species, or on every site tile if none fits.

**Where the region still has a say** (three places):
1. **The candidate list's biome filter.** `FP.mark` (`:10114-10140`) admits a species only for the fort's own biomes.
2. **A small advantage for species DF stocked.** They skip the good, evil, savage and extinct gates (`:10134`). `FP.candidates` also prefers a DF-stocked entry when a species fits two layers (`:10300`). That affects who is a *candidate*, not who is cast. I found no DF-stocked preference in the cast draw itself, but I checked only `FP.candidates` and the builder's context, not every step of the builder.
3. **Where the one open entry sits** (above).

Only species with an entry in the embark area are "rested" (`castManages` `:10806`). That is bookkeeping: a species with no entries has nothing to hold.

### (b) Why the anchor exists (DF, from rig results)
TR2 (15 Oct, memory df-wave-pick-per-entry) showed DF picks surface waves per entry, weighted by FREQUENCY and the entry's tile:
- a flier open on 5 tiles took 77% of 161 waves against an equal flier on 1;
- big site tiles drew 40-58 waves per entry, neighbours 5-10.

So a species DF stocked on several tiles out-drew a single entry the tool created. Putting every cast member on one tile leaves the ladder's FREQUENCY as the only odds. X9c1 (16 Oct, comment `:3296-3300`) showed the same in the caverns: one-entry species arrived 0 times, while species with 16-40 entries took the caverns.

### Thought experiment (made-up numbers)
A straddling fort:
- A: site, forest, 60% of the map (the anchor);
- B: site, grassland, 35%;
- N: neighbour, 5%.

DF stocked wolf on A, B and N; elk on B only; badger on A and B. The spring ground cast is wolf, elk and platybelodon (a mod species DF didn't stock). Badger is cast only in autumn.

- **Wolf:** the A entry is open. B and N are held, and their reserve tops A up.
- **Elk:** materialise tries to create an A entry.
  - If elk fits forest, the A entry is created and becomes the open one.
  - If elk fits grassland only, nothing is created and its open entry stays on **B**.
  - So "on the anchor" is the usual case, not a guarantee (comment `:3248-3250`).
- **Platybelodon:** an entry is created once, at the build, on the fitting site tiles (normally A).
- **Badger:** stocked but not cast in spring, so both entries are held and it has **no** open entry. In autumn A opens and B stays held.

**Real fort, SAVR_d1** (`.claude/scratch/pacing/ladder/SAVR_d1.json`, year 100): 12 of the 32 ground members are mod species, 3 per season (e.g. CENOZOIC_PLATYBELODON, CRETACEOUS_TRICERATOPS_MAN in spring). The dump doesn't record which entries were DF's or the tool's, so it can't show the "who" rule on its own. The code above does.

### Edge cases
- **Biome mismatch with the anchor** (elk on B). Inference from TR2: a smaller site tile may draw less per entry, so the species may arrive less often than its ladder value implies. Not measured.
- **Only ponds, or no water.** Ponds play no part in choosing the anchor. The water layer draws its own cast. A water-cast species' surface entry (lake fish, mink) is still single-sourced and filed under its water key (`:3643-3656`).
- **Not single-sourced** (`V7.SRC.isRow` `:3292`): vermin, water-feature entries and non-Animal types. The cast still opens or holds them.
- **Never managed:** megabeasts, night creatures, locked classes, and innumerable entries (`managedPop` `:1711`). Innumerable entries are touched only by the pauses' flag (`sideRows` `:15696`).
- **Pauses** (land cap, one group per species, bird, flying, cavern) shut the chosen entry for a while. They don't change which entry is chosen.
- **Unbreached caverns.** The anchor rule still runs, and DF still sends cavern waves before a breach. DF sets a cavern's Discovered flag on its own (memory embark-site-traps), and the unbreached NA1 fort drew cavern waves of all but the thief-tagged species (memory cavern-thief-tag-bar). The tool's own draws have no discovery check either, so walkers can be drawn into an undiscovered cavern; swimmers wait until its pools are registered (`:8695`).

### Does it serve your aims?
Yes.
- **Ecology:** who arrives comes from your casts, with their slots and food web, not from DF's region list. A species DF stocked but you didn't cast can't slip in, because the hold re-closes it every pass.
- **Diversity and pacing:** the anchor rule removes DF's favouring of species stocked on many tiles, so the ladder's odds hold.

The one loose end is the biome-mismatch case. If you want every cast member on equal footing, always create the open entry on the anchor. The cost is realism: a grassland grazer would come from a forest tile's entry. That is your call, not a bug.

**Suggested panel 3 wording:** "One open entry for each species in this season's cast: on the surface, on the anchor tile (the site tile covering the most of the map) when it lives there..."

### What would confirm it live (not run; the rig is busy)
1. After a season change, run `seasonal-wildlife groups single`. It prints the anchor, the species picked and the held copies (`:24210-24227`). These are counts of picks, not of stocked entries.
2. Read the surface Animal entries. Those with quantity > 0 and the flag off should be exactly this season's ground, flying and water cast, plus stand-ins and pins, minus exhausted or paused members.
3. Check that no species DF stocked but did not cast is open.
4. List the cast members whose open entry is off the anchor (the biome-mismatch cases).
5. A separate longer run: compare those members' waves with their ladder share.

**Rig test that would settle it:** Not needed for the core answer (it is in the code). To confirm live after a season change: `seasonal-wildlife groups single`; then read surface Animal entries and check that those with quantity > 0 and extinct off are exactly this season's ground/flying/water cast plus stand-ins and pins, minus exhausted or paused members; no DF-stocked non-cast species open; list cast members whose open entry is off the anchor. Separate one-season run: off-anchor members' waves v their ladder share.

<details><summary>Review and verification trail</summary>

- review: Kept the core answer, which the code confirms: who is open comes from the season's cast (ROSTER.castYear 10817-10895 writes allow/assign; ROSTER.wants 3216 = allow and inSeason; applyLive 3876-3920 and holdOutOfSeason 3931-3950 hold every row wantsRow refuses). Where the open entry sits comes from the anchor rule (V7.SRC.footprint 3256-3291, V7.SRC.chosen 3348-3375 scores anchor +3e9 / site +1e9 / area / stock, V7.SRC.isDup 3377).
- review: CUT a wrong claim: the SAVR ground casts are not 'mostly mod species'. The dump shows 12 of the 32 ground members are the prehistoric mod's (3 per season), and SKINK_MAN is vanilla. Being a mod species also says nothing about whether DF stocked it, because DF stocks a region from every installed raw. The dump has no stocked or fp_created field, so it cannot show this point either way.
- review: FIXED a wrong claim: 'DF sends no cavern waves until a breach' is not supported. Memory embark-site-traps says DF sets a cavern's Discovered flag itself (unbreached is not the same as undiscovered). Memory cavern-thief-tag-bar says the unbreached NA1 fort drew cavern waves for every species except the thief-tagged ones, and that the thief rule was withdrawn.
- review: ADDED: the region has a small say in the candidate list. Species DF stocked skip the good/evil/savage/extinct gates (FP.mark 10134: `(not FP.stocked(e)) and FP.gate(...)`), and FP.candidates prefers a token's DF-stocked entry (10300). Only species with an entry in the embark area are rested by the cast (castManages 10806: `if not e.inEmbark then return false`).
- review: ADDED: open entries also go to exhaustion stand-ins. These are cast members borrowed from another season ('Inactive species are never promoted', comment 3952-3960). Player pins (applyPins 3100, called at 10882) also get open entries. Both stay inside the user's casts or choices, never DF's region list.
- review: ADDED: the casts are built once and the same four seasons repeat every year ('no new casts at a new year (user 9 Oct)', 9598). The only exceptions are cast rebuild and castMissingLayers adding a missing water layer (10900).
- review: CLARIFIED: 'the fort's own region tile' means the site tile covering the most of the map. A straddling fort has 2-4 site tiles, and the anchor is one of them (footprint 3288). A cast species whose biome is only on another site tile keeps its open entry there (materialise 10606-10618 and 10687-10689).
- review: TIGHTENED the rig check: the `groups single` count is of species the rule picked an entry for (the pick table), not of entries holding stock. The expected open set must include stand-ins and pins and exclude exhausted and paused members.
- verifier: Minor: added that land and cavern walkers can be drawn into an undiscovered cavern by the tool too (no discovery check on the draw path), not only that DF sends waves there. No change to the core answer.

Code refs: sw-wt/plugin/scripts/seasonal-wildlife.lua:1029-1030 (single_source, cave_single_source defaults); sw-wt/plugin/scripts/seasonal-wildlife.lua:1413 (inSeason); sw-wt/plugin/scripts/seasonal-wildlife.lua:1704-1713 (managedPop, innumerable skip); sw-wt/plugin/scripts/seasonal-wildlife.lua:2655-2720 (buildPool: inEmbark, dfStocked); sw-wt/plugin/scripts/seasonal-wildlife.lua:3100 (ROSTER.applyPins); sw-wt/plugin/scripts/seasonal-wildlife.lua:3216 (ROSTER.wants); sw-wt/plugin/scripts/seasonal-wildlife.lua:3240-3291 (V7.SRC comment, footprint, anchor); sw-wt/plugin/scripts/seasonal-wildlife.lua:3294 (V7.SRC.isRow); sw-wt/plugin/scripts/seasonal-wildlife.lua:3296-3346 (cavern one-entry comment, caveAnchors); sw-wt/plugin/scripts/seasonal-wildlife.lua:3348-3375 (V7.SRC.chosen scoring); sw-wt/plugin/scripts/seasonal-wildlife.lua:3377-3409 (isDup, wantsRow, wantsRowBase); sw-wt/plugin/scripts/seasonal-wildlife.lua:3638-3676 (CACHE.managedPops, water key for created entries); sw-wt/plugin/scripts/seasonal-wildlife.lua:3766-3840 (V7.SRC.topUp, cave_open_stock 30); sw-wt/plugin/scripts/seasonal-wildlife.lua:3876-3928 (applyLive); sw-wt/plugin/scripts/seasonal-wildlife.lua:3931-3950 (holdOutOfSeason); sw-wt/plugin/scripts/seasonal-wildlife.lua:3952-3960 (exhaustion stand-ins: inactive never promoted); sw-wt/plugin/scripts/seasonal-wildlife.lua:9598 (casts built once, no new casts at a new year); sw-wt/plugin/scripts/seasonal-wildlife.lua:10033 (FP.stocked); sw-wt/plugin/scripts/seasonal-wildlife.lua:10114-10140 (FP.mark biome filter; DF-stocked skip gates at 10134); sw-wt/plugin/scripts/seasonal-wildlife.lua:10296-10330 (FP.candidates prefers stocked entry); sw-wt/plugin/scripts/seasonal-wildlife.lua:10564-10720 (FP.materialise); sw-wt/plugin/scripts/seasonal-wildlife.lua:10797-10815 (castRestLayers, castManages); sw-wt/plugin/scripts/seasonal-wildlife.lua:10817-10895 (ROSTER.castYear); sw-wt/plugin/scripts/seasonal-wildlife.lua:10900 (castMissingLayers); sw-wt/plugin/scripts/seasonal-wildlife.lua:20926, 21215, 24916, 25024 (castYear callers); sw-wt/plugin/scripts/seasonal-wildlife.lua:24192-24228 (groups single command); DwarfCron/data/pacing/mechanics-diagram.html:1118-1125 (panel 3 step 2 text); DwarfCron/.claude/scratch/pacing/ladder/SAVR_d1.json (ground casts: 12 of 32 mod species); memory/df-wave-pick-per-entry.md (TR2); memory/embark-site-traps.md (unbreached != undiscovered); memory/cavern-thief-tag-bar.md (NA1 unbreached fort drew cavern waves)

</details>

# B. Caps, places and slots

*how caps are defined per place (lake/river/pond, cavern layers), one-group-per-species, what 'place at its cap' and 'slot room' mean, the water layer switch*

### What these six questions are really asking
Underneath, these questions ask: **what decides how many animals are on the map, where, and of which species, and are those limits shaped like the ecology you want?** You are checking whether each \"place\" (ground, flying, each kind of water, each cavern) and its cap are natural units, or leftovers from earlier code. You also want to know whether one-group-per-species is the diversity lever you think it is.

The code shows three layers, often confused:
1. **Casts and slots** (panel 2): who *may* appear this season. Room there means empty seats in a cast being built (B5).
2. **Places and caps** (panels 1 and 5): how many groups each place *may hold at once*. Places sit full most of the time, so caps and how long groups stay set the numbers (B3, B4).
3. **Who fills an opening:** the ladder, DF's pick (stock-weighted in caverns), the tool's least-seen draw, and the one-group-per-species rule (B2).

### Common findings
- **Places do not match the ecology in two spots:**
  - Water is split by *kind*, each kind with a full map-size cap. So ponds and stream scraps get as many slots as a huge lake (B1). In addition, DF's fresh-cast waves are filed under one kind (`casts.sub`) wherever they swim.
  - Caverns have one shared number but no species rule, so 7 slots hold about 3-4 species (B3).
- **Caps leak upward.** Causes: reopen-all at cap−2 with no re-close until the cap; two arrivals in one pass; apex placements and adopted natives that ignore the cap; tool draws that ignore the pause; and an unexplained jump after a reload (B3, B4).
- **The one-group-per-species rule has a hole.** It is off for fliers and water-cast species whenever the ground is paused (B2, proven in the P2_COAST ledger).
- **The page's words mislead:** \"place\" as noun vs verb, \"room\" with two meanings, the seed \"into the slot with the most room\", and \"on if the map has water\" for a switch that everything-on sets everywhere (B4, B5, B6).

### Combined recommendation (in order; all tune existing code, per your 16 Oct ruling)
1. **Fix the one-group-per-species leak** under the land pause (B2). It breaks a rule you already approved.
2. **Make water places follow the water casts:** one shared **fresh** place (lake + rivers + fresh ponds) and one **sea** place (ocean + salt ponds), each with the map-size cap. Pick the species first, then the body by size, with optional square-root damping per kind (B1). Ponds-only maps keep their animals; mixed maps stop being swamped by ponds.
3. **Make caps hold:** either tool draws respect the pause or the page says they refill at cap−1; apex placements respect the place's pause; reopen in stages; count draws before they land (P12 part 2); find the reload jump (B3, B4).
4. **Caverns:** read B2's P10 result. If repeats persist, add a **per-cavern** one-group-per-species rule with the switch-off (not map-wide, not strict). Treat per-cavern cap numbers as a crowding and danger dial chosen for ecology, after the above (B2, B3).
5. **Fix the page wording**, and optionally seat the seed in its habitat role first (B5). Let the water body registry, not the switch, decide when water casts exist (B6).

Items 1-3 serve diversity and pacing directly with fewer special cases. Item 4 serves diversity and the food-web pyramid underground.

<details><summary>Cross-answer issues the verifier resolved</summary>

- 'Water body' means a KIND of water in the groups code, not a single body. V7.GRP.BODIES = {'ocean','lake','river','pool'} (seasonal-wildlife.lua:902). V7.waterTick keys each place 'water:'..kind (:12193), and V7.WAT.bodyAt returns RB.type (:7690), so the tally is per kind too. B2 and B4 both wrote 'each water body keeps its own count' as if each pond were a place. The code agrees with B1: all ponds on the map are one place, with one cap, one clock, one tally and one one-group-per-species check. B2 and B4 are corrected to say this.
- Apex cap scope. B4 said '1 apex group per layer'. B3 said the cap is counted across all three caverns. Both are right. ROSTER.apex.decide (:11691) counts with ROSTER.apex.groupsOnMap(races, layer=='cavern') (:11548), which counts apex units in every cavern together. The scheduler's 'cavern' layer is one layer covering all three caverns, so cap_calm 1 / cap_savage 2 (:9113) is a total across the three. B4 now says so.
- Why places go over their cap. B3 and B4 each listed part of the cause; together the code gives this list. (1) After a pause, everything reopens at cap−2 (resumeAt :15673) and does not close again until the place reaches its cap (:16388 cavern, landPause same rule). (2) Two arrivals can land in one 300-tick pass (GROUPS_CADENCE :5152). (3) Apex placements check only the apex cap, not the place's cap or pause (only thieves skip a paused cavern, :11724). (4) Adopted natives are counted whenever they are found. (5) The tool's own draws check only n < cap and ignore the pause (17421 ground, flyTick :15979, caveTick :15998), so in effect they refill at cap−1. (6) Coupling calls predators right after their prey. (7) A jump after a reload is seen in B2 but not explained (inference only). Irruption groups show in status lines but are left out of the cap on purpose (:15587). B3 and B4 now point at each other.
- DF's own waves of water-cast species are filed under ONE kind: cfg.casts.sub, which is lake if there is a lake, else river, else ponds (V7.GRP.waterBirds :15800-15814, option A at :15793). They are not filed where the animal actually swims. On the lake fort, every DF fresh-cast wave counts against water:lake. B1 and B4 did not say this; it is added. It is one more reason the per-kind split is artificial.
- The one-group-per-species leak (B2) bears on B4's 'place at its cap'. While the ground is paused, V7.GRP.speciesPause returns early (:16234). Since 8fc1c32, though, the land pause no longer closes the flying cast's or the water casts' entries (:15749-15768). So whenever the ground is full, the species rule is off for those species. B2 P2_COAST ledger lines 145-166 confirm it: land paused on Autumn 3, a barn owl was drawn on Autumn 4, and a DF barn owl wave came on Autumn 5.
- 'Room' means two different things on the page. In panel 2 (B5) it means seats still empty in a cast while it is being built (frac = (want−have)/want, :22904). In panel 9 and in B3/B4 it means space under a place's cap on the map. The two have no connection in the code. All answers now keep them apart.
- Slots (B5) are not map places. A cavern's 6 cast seats and its cap of 7 groups are separate numbers. The 16 Oct reason for a cap of 7 ('six cast species each a group plus a thief') assumes one group per species. Caverns have no such rule (B2, B3), so in practice 7 groups hold about 3-4 species (B3).

</details>

## B1

> What would happen if... the Lake, River and Pool caps were a shared total, and animals would be drawn into any of those locations (if present on the map) rather than having a dedicated cap for each of those? I want to resolve the issues caused by giving murky pools their own caps. On the one hand there are maps with only murky pools, and I do want those to still get some water animals, but on the other hand I don't want murky pools to dominate the draws. Also, is every single murky pool being treated as a location with its own draws, caps and so on?

**Short answer.** No. Each pond does not get its own cap. All ponds on the map are one place ('water:pool') with one cap, one clock and one tally. The real problem is that each KIND of water (ocean, lake, river, ponds) gets the full map-size cap (4 on 3x3, 8 on 7x7). So a few hundred tiles of 1-deep ponds get the same cap as a 100,000-column lake. A shared fresh-water place (lake + rivers + fresh ponds) with one map-size cap fixes this. Ponds-only maps lose nothing. On mixed maps, ponds get at most their share by size.

*Status: verified · confidence high · review verdict: minor fixes*

### Short answer
- **No, each pond does not get its own cap.** All ponds on the map are **one place**. DF calls them murky pools; the code calls the place `water:pool`. That place has one cap, one release clock, one tally of what swims there, one apex limit and one "one group per species" check. A single pond only matters at the moment a drawn group has to enter somewhere. The tool then picks one of the ponds that fit, bigger ponds more often.
- **The real problem:** every *kind* of water gets a full cap of its own, ⌊√ embark tiles⌋ + 1. That is 4 on a 3x3 embark and 8 on a 7x7. The kinds are ocean, lake, river and ponds. So ponds get the same cap as a huge lake, and so does any scrap of stream, because all flowing water counts as "river" however small.
- **What your change would do:** a shared fresh-water total fixes this. Maps with only ponds lose nothing. On mixed maps, ponds get about their share by size and can never take more.

### 1. How it works now (code)
- **The cap is per kind.**
  - `V7.GRP.BODIES = {'ocean','lake','river','pool'}` (seasonal-wildlife.lua:902).
  - `V7.waterTick` (:12177) loops those kinds. For each it uses the place key `'water:'..body`, counts the groups whose `grp.body == body`, takes the cap from `QUOTA.groupsFor` and keeps a clock in `g.next_water_body[body]`.
  - `QUOTA.groupsFor` (:4458-4471) gives every water kind the land formula (`QUOTA.autoGroups` :4441).
  - This was on purpose: v7.0, 30 Sep: "every layer -- land, each water body (ocean, lake, river, pool) ... holds its own groups at once". Before v7, all water shared one count of 2.
- **The tally is per kind.**
  - `V7.WAT.census` files every wild water animal under `V7.WAT.bodyAt`, which returns the body's **type** (:7690), not which body it is.
  - So balance, pyramid, pull, feed, the apex limit and one-group-per-species (`V7.WAT.mix` :7853-7863) are all worked out per kind.
  - The tally also counts animals the tool did not draw: DF's arrivals and the schools DF seeded at embark.
  - Result: one species can hold groups in the lake, the river and the ponds at the same time.
- **DF's own waves are filed under one kind.** A DF surface wave of a fresh-cast species counts as a water group of the fresh cast's main kind, `cfg.casts.sub`, wherever it actually is. `casts.sub` is lake if there is one, else river, else ponds (`V7.GRP.waterBirds` :15800-15814). On the lake fort, every DF fresh-cast wave counts against the lake's cap.
- **What counts as a pond or a river** (`V7.WB.typeOf` :8019-8026):
  - A body needs at least 9 water tiles (`min_tiles`).
  - **Stagnant water is a pond at any size.** Pond #1 on the lake tile has 101 columns, more than `pool_max` 64.
  - Enclosed lake-type or sea water under 64 columns is also a pond.
  - **Any flowing water is a "river" at any size**, even a 6-column scrap.
- **Where a single pond matters:**
  - it is registered as a body;
  - it is checked for fit (`V7.WB.fitting` :8379): adults at most 20,000 cm³ (`POOL_MAX_MASS` :8355) unless you set that species' waters yourself, and the salt must match;
  - it is picked among the fitting ponds by breathable columns (`V7.WAT.entry` :8666-8686);
  - the group's entry tile is worked out inside it.
- **Salt and fresh ponds share one cap.** A salt tide pool draws from the sea cast (`castOfBody` :7663), but it counts against the same `water:pool` cap and tally as fresh ponds.

### 2. What the rig measured (B2, still running)
Tally of group ids from `data/pacing/B2/*/probe.jsonl`.

| fort | place | mean groups (cap) | % of time paused | groups seen | species |
|---|---|---|---|---|---|
| P2_LAKE 7x7 | lake | 4.19 (8) | 28% | 30 | pike 9, Gerrothorax 8, giant fly 4, ... |
| | "river" (4 stream scraps) | 7.53 (8) | 73% | 57 | carp 14, pike 9, Hibbertopterus 8, ... |
| | ponds (5) | 7.45 (8) | 67% | 34 | **mink 17, Diplocaulus 11, river otter 5, gar 1** |
| P2_SAVR 3x3 | river (1) | 3.71 (4) | 91% | 66 | carp 20, snapping turtle 9, ... |
| | ponds (11) | 2.09 (4) | 51% | 18 | **osprey 18** |

Lake-tile bodies (from the earlier embark there, `ladder/lake/thaw2.log`):
- lake: 101,433 breathable columns;
- 5 ponds: 260 columns, all 1 deep;
- 4 stream scraps: 48 columns, all 1 deep.

What that means:
- **Water outnumbers land.** On P2_LAKE there were 19.8 water groups on average against 7.0 land. On SAVR it was 6.2 against 3.7.
- **Tiny waters take most of the slots.** About 300 columns of 1-deep puddles and stream scraps held about 15 of the lake fort's ~20 water groups.
- **One species repeats everywhere.** Pike held up to 7 groups at once (lake plus stream scraps). One group per species works only inside a kind, and only while some candidate is still missing (:7853-7863). The ponds' candidate list is short (about 4 species on LAKE, 1 on SAVR), so their slots fill with repeats.
- **On SAVR the ponds sat at 0 of 4 all spring** (master.log checkpoints 7-28). The fresh cast there is built for the river, so its members are mostly big. In summer and autumn the osprey was the only member small enough for a pond, so all 18 pond groups were ospreys.

### 3. Thought experiment: one shared fresh-water place
This matches your 9 Oct ruling ("murky pool is no longer a layer"). Fresh water already has **one cast**; only the groups pass still splits it by kind.

How the shared draw would work:
1. One place: lake + rivers + fresh ponds, with one map-size cap, one clock and one tally.
2. The candidate list is the fresh cast members that fit **any** registered fresh body. `V7.WB.fitting(onlyType=nil)` with `castBodies` already gives this.
3. Pick the species first, using the ladder and the mix on the shared tally.
4. Then pick its body by breathable columns. That is the existing `V7.WAT.entry` rule, just used across kinds.
5. One group per species across all fresh water.

**Lake fort, shared cap 8:**
- A small species that fits everything enters a pond 260/101,741 = 0.26% of the time.
- Water drops from ~20 groups to at most 8. About 8-10 drawable summer species would fill those 8 slots, instead of 6-7 pike groups.
- **Optional:** to let ponds see an occasional group, damp each *kind's* total columns with a square root. That gives lake 93%, ponds 4.7% (~0.4 of 8 groups) and streams 2%.
- Do **not** damp per body. That rewards maps with many little fragments, which is the very problem.

**Savage marsh, shared cap 4:** the osprey is the only pond-sized member and is held to one group, so ponds hold at most 1 group. River species keep 3-4 slots, as now. Everything lost is osprey repeats.

**River plus bigger ponds:** small species (mink, otter) would mostly enter ponds. But one group per species limits ponds to as many groups as there are pond-sized members, and those take shared slots rather than adding new ones. So ponds cannot dominate.

**Ponds-only map:** the fresh cast is already built for ponds (`F.sub = 'pool'`, :9927), and the shared cap equals today's pond cap. **Nothing changes; these maps keep their water animals.** Whether 4 groups in a few hundred 1-deep columns is too dense is your call. A cap that grows with water area would thin it, but that pulls against your 1 Oct ruling (R45) that a fort should reach 3-5 water groups on its own.

**Coast:** keep the sea as its own place and move salt tide pools into it (`castOfBody` already sends them to the sea cast).

**Winter** (inference): bodies are rescanned each season. A shared place keeps its count and draws into whatever is still liquid.

### 4. Risks and code work
- **Less water life on mixed maps:** the lake fort goes from 24 slots to 8. That still meets R45. If 8 feels thin on a big lake, give the shared place its own cap setting rather than bringing back caps per kind.
- **The tally pools water that is not connected** (inference). A pike in the lake could get a prey boost from fish in a distant pond. This changes only the odds, not where the group lands.
- **Calling the draw with no body is not enough.** `ENGINE.candidates` with `body=nil` gets no tally (`B = nil`, :7346), and `V7.WAT.mix` then skips the whole mix, one-per-species included (:7811-7814). The tally has to be keyed by the new place.
- **Code that changes:**
  - `V7.GRP.lk` (:15312);
  - the `V7.waterTick` loop;
  - the `bodyAt`/census key;
  - the coupling table `wc[body]`;
  - the per-kind bird pause (:16145);
  - `layerState` rows;
  - `V7.GRP.waterBirds` (it already files under one fresh kind, which makes this simpler);
  - status, web and ledger text;
  - the water harness and DwarfCron probe parsing.
- **Saved groups:** adopted and native groups carry only the type, so they need a lookup to the new key (ocean → sea, lake/river → fresh, pond → its salt).

### 5. Does it serve your aims?
- **Diversity:** yes. Slots stop going to 1-4 small species in tiny waters.
- **Ecology:** yes. Balance and the pyramid work on the whole fresh-water community; the pyramid already uses 'lake' for all fresh water (:7783).
- **Pacing:** one clock instead of three.
- **Fewer hacks:** yes. It reuses the entry rule, and the place follows the cast.

**Recommendation:**
1. One shared place per water cast: **fresh** (lake + rivers + fresh ponds) and **sea** (ocean + salt ponds), each with the map-size cap.
2. Pick the species first, then the body by breathable columns.
3. Optional: square-root damping per kind.
4. Keep the 20,000 cm³ pond size limit.

### 6. What would settle it
1. **Offline:** replay the registered body sizes and season casts of SAVR_d1, LAKE3 and COAST through the shared draw, with and without damping. Report each kind's expected share and the distinct species at once.
2. **Rig, after the current run:**
   - re-embark region6 24,11 (savage marsh) and 16,17 (lake shore) with the shared-place build, plus one ponds-only 3x3 fort;
   - run the B2 probe for 2 seasons;
   - compare with B2: group-days per kind, distinct water species at once, effective species, water against land groups, most groups of one species at once, slots taken by DF's arrivals, and whether the ponds-only fort still holds 3-4 water groups.

**Rig test that would settle it:** Offline replay first (SAVR_d1, LAKE3, COAST body sizes + casts through a shared fresh/sea draw, with/without per-kind sqrt damping). Then on the rig after the current run: re-embark region6 24,11 and 16,17 plus a ponds-only 3x3 with the shared-place build, B2 probe for 2 seasons; compare group-days per kind, distinct water species at once, effective species, water v land groups, peak same-species groups, DF-sourced slots, ponds-only fort reaching 3-4 water groups.

<details><summary>Review and verification trail</summary>

- review: Updated the B2 numbers from the live probe files. The run is still going, so P2_LAKE now has 59 rows. Lake mean 4.19/8 (was 3.98), paused 28%. River 7.53/8, paused 73%, 57 groups. Ponds 7.45/8, paused 67%, 34 groups: mink 17, Diplocaulus 11, river otter 5, gar 1. Pike 9 lake / 9 river (was 7/8). SAVR is unchanged: river 3.71/4, ponds 2.09/4, osprey 18 of 18.
- review: Added the total water against land, averaged after the first 10 snapshots. P2_LAKE: 19.8 water groups against 7.0 land. P2_SAVR: 6.2 water against 3.7 land. SAVR's end status line reads 'water: draws on 8 of 4 per body group(s)' (B2/P2_SAVR/status-end.txt:20).
- review: Added that pike held up to 7 groups at once on the lake fort: 3-4 in the lake and 3 in the stream scraps on days 33-37. So the 'one group per species' rule is broken across places and also inside the lake once its drawable list runs out.
- review: Added that on SAVR the pond place sat at 0 of 4 all spring (master.log checkpoints 7-28). The spring fresh cast had nothing pond-sized, then ospreys filled it in summer and autumn. Also corrected the pond count: SAVR has 11 ponds and 1 river (SAVR_d1.json bodies; Autumn ledger line 145).
- review: Sharpened how body types work (V7.WB.typeOf :8019-8026). Stagnant water is a pond at ANY size (lake-fort pond #1 has 101 columns, above pool_max 64). Flowing water is a 'river' at ANY size, even enclosed. So the lake fort's 'river' place is 4 one-tile-deep scraps of 6-17 columns (thaw2.log lines 10-14). That is the same problem as ponds, and a shared total fixes both.
- review: Added a code fact the plan depends on: ENGINE.candidates called with body=nil gets B=nil from the census, and V7.WAT.mix then skips balance, pyramid, pull and 'one per species' (:7346, :7811-7814). Calling the draw with body=nil is not enough. The census has to be keyed by the shared place.
- review: Confirmed the salt gap the original answer left open. Adopted and native groups get grp.body = entry.body from V7.GRP.bodyAt, which returns only the type and no salt (:16920-16929, :17040). Drawn groups carry salt (:7483). A key worked out at load has to look the body up (V7.WB.at -> B.salt) for ponds.
- review: Added that groups DF delivers count against the water caps too: giant fly x4, giant loon x2, fly man, giant capybara in the lake; giant dragonfly x5, capybara x2, Meganeura man in the SAVR river. They would take shared slots, so the rig test should watch them.
- review: Square-root damping: added the per-body version for comparison (ponds 9.4%, streams 3.7%). Recommended per-kind damping (93/4.7/2.0%), because per-body damping rewards many small fragments, which is the very problem.
- review: Added an optional cap that grows with water area, for density on maps with only small ponds. Marked it as the user's call because it pulls against the 1 Oct R45 ruling (3-5 water groups at once).
- review: Cut the line about 'pond options A-D' not being in PLAN-v8.1. The user did not ask about it.
- review: Grounded the 'freshwater is one layer' argument in the user's own ruling (memory full-pool-design-oct9: 'murky pool is no longer a layer'; freshwater subtypes 'not compounding'). Also the diagram already says 'one cast for all fresh water'. Only the groups pass still splits by kind.
- verifier: Added: the tool files DF's own surface waves of fresh-cast species under one kind, the fresh cast's main water (cfg.casts.sub: lake > river > ponds; V7.GRP.waterBirds :15800-15814). On the lake fort, the giant fly and loon waves counted against water:lake wherever they swam. On SAVR they counted against the river.
- verifier: Line refs checked: V7.GRP.BODIES :902; waterTick lk/n/cap :12193-12195; bodyAt returns type :7690; mix one-per-species :7853-7863; typeOf :8019-8026; POOL_MAX_MASS :8355; entry by breathable columns :8666-8686; castOfBody :7663; F.sub :9927; pyramid uses 'lake' for all fresh water :7782-7783; candidates B=nil :7346.

Code refs: sw-wt/plugin/scripts/seasonal-wildlife.lua:902 (V7.GRP.BODIES); sw-wt/plugin/scripts/seasonal-wildlife.lua:961-963 (bodies min_tiles 9, pool_max 64); sw-wt/plugin/scripts/seasonal-wildlife.lua:4441-4471 (QUOTA.autoGroups, QUOTA.groupsFor; v7.0 per-kind comment); sw-wt/plugin/scripts/seasonal-wildlife.lua:12170-12250 (V7.waterTick: lk='water:'..body, n, cap, next_water_body); sw-wt/plugin/scripts/seasonal-wildlife.lua:17255-17261 (V7.PASS.WATER_BODIES = 1); sw-wt/plugin/scripts/seasonal-wildlife.lua:7322-7370 (ENGINE.candidates; B = census[body] or nil at :7346); sw-wt/plugin/scripts/seasonal-wildlife.lua:7434-7490 (ENGINE.draw, drawOne; drawn group record with salt at :7483); sw-wt/plugin/scripts/seasonal-wildlife.lua:7567 (V7.WAT.coupleTable per body); sw-wt/plugin/scripts/seasonal-wildlife.lua:7663-7670 (castOfBody, castBodies); sw-wt/plugin/scripts/seasonal-wildlife.lua:7686-7700 (V7.WAT.bodyAt returns type); sw-wt/plugin/scripts/seasonal-wildlife.lua:7706-7762 (V7.WAT.census keyed by type, counts untracked); sw-wt/plugin/scripts/seasonal-wildlife.lua:7795-7800 (V7.WAT.pyramid: 'lake' for all fresh); sw-wt/plugin/scripts/seasonal-wildlife.lua:7806-7863 (V7.WAT.mix; B=nil skips mix at :7811-7814; one-per-species :7853-7862); sw-wt/plugin/scripts/seasonal-wildlife.lua:7866-7896 (V7.WB header); sw-wt/plugin/scripts/seasonal-wildlife.lua:7976-7978 (stagnant -> class 3); sw-wt/plugin/scripts/seasonal-wildlife.lua:8019-8026 (V7.WB.typeOf: stagnant=pool any size, flowing=river any size); sw-wt/plugin/scripts/seasonal-wildlife.lua:8324-8336 (V7.WB.typesFor: small lake/river species fit pool); sw-wt/plugin/scripts/seasonal-wildlife.lua:8354-8355 (BROOK_MAX_MASS, POOL_MAX_MASS 20000); sw-wt/plugin/scripts/seasonal-wildlife.lua:8379-8396 (V7.WB.fitting); sw-wt/plugin/scripts/seasonal-wildlife.lua:8666-8686 (V7.WAT.entry: body by breathable columns); sw-wt/plugin/scripts/seasonal-wildlife.lua:9927 (F.sub); sw-wt/plugin/scripts/seasonal-wildlife.lua:15309-15316 (V7.GRP.lk); sw-wt/plugin/scripts/seasonal-wildlife.lua:16120-16127 (per-body water-bird pause); sw-wt/plugin/scripts/seasonal-wildlife.lua:16920-16929, 17040 (V7.GRP.bodyAt type only; adopted groups lack salt); sw-wt/plugin/scripts/seasonal-wildlife.lua:17141-17166 (V7.GRP.layerState rows per kind); sw-wt/plugin/docs/pacing/PLAN-v8.1.md:80,137 (P11); DwarfCron/data/pacing/B2/P2_LAKE/probe.jsonl, P2_SAVR/probe.jsonl (occupancy, groups, pike concurrency, DF-sourced water groups); DwarfCron/data/pacing/B2/master.log:3-6 (SAVR water:pool 0/4 through spring); DwarfCron/data/pacing/B2/P2_SAVR/status-end.txt:20 ('8 of 4 per body'; sampled river 66 pool 113); DwarfCron/data/pacing/B2/P2_SAVR/ledger.txt:145 (river 1, pool 11); DwarfCron/.claude/scratch/pacing/ladder/lake/thaw2.log:5-14 (lake fort body sizes); memory/full-pool-design-oct9.md:20-21 (freshwater one layer; 'murky pool is no longer a layer'); DwarfCron/.claude/scratch/sw-questions/b1_tally.py (tally script)

</details>

## B2

> What would happen if... instead of "one group per species (surface and water)" the tool enforced "one group MAXIMUM per species (surface, water, cavern)"? What would happen if the rule was changed in this way? Would the 1 group per species maximum apply to the caverns too? Would the maximum apply to layer B if a species already had a group in layer A? Does it already work that way? What would happen if it were changed?

**Short answer.** No, it does not work that way now. One group per species covers the surface only: ground, flying and water-group species share one list for DF's surface entries and the ground/flying draws, and each kind of water has its own check for the water draw. Caverns are left out on purpose. It is not a true maximum: it switches off once every candidate has a group. It also leaks: while the ground is paused, it is off for fliers and water-cast species. Fix the leak first. If caverns are added, do it per cavern with the same switch-off, not one map-wide count and not a strict maximum.

*Status: corrected · confidence high · review verdict: minor fixes*

### Short answer
**No, it does not work that way now.**
- **It covers only the surface.** Ground and flying share one list. Each **kind** of water (ocean, lake, river, ponds) has its own check for the water draw; all ponds count as one place. The caverns were left out on purpose: the commit that added the rule (670636d, 22 Oct, your "option A") says "Caverns not included", and so does the help text (:61-62).
- **It is not a true maximum.** It means "one group per species *while another species could still come*". Once every candidate has a group, it switches itself off and a repeat may come.
- **It leaks on the surface today** (below).

### (a) What the code does now
**Ground and flying** (`V7.GRP.speciesPause` :16230):
- It uses the list from `V7.GRP.presentRaces` (:16210): every species with a tracked ground, flying or water group. **Cavern groups are skipped** (:16213).
- Each listed species gets its surface entries closed with the extinct flag. Stock and FREQUENCY are untouched, and the entries reopen when its last group has gone.
- **Switch-off:** if no ground species without a group still has an open entry, it reopens everything it closed (:16285-16287).
- The tool's own ground and flying draws skip the same list (`V7.DRAW.pick` :15910, :15928).

**Water** (`V7.WAT.mix` :7853-7863):
- A species already in *this kind* of water weighs 0, as long as another candidate still weighs more than 0.
- "Already here" comes from that kind's tally (`V7.WAT.census`, keyed by type via `bodyAt` :7690).
- The water draw never reads the extinct flag; it only needs stock (`ENGINE.candidates` :7322ff).

**Caverns: no per-species rule.** Only these limit them:
- the cap of 7 per cavern, with the cavern pause closing the whole cavern at its cap;
- one open entry per species in each cavern (`cave_single_source` :1030);
- the cavern hold (`V7.GRP.cavernHold` :16713). Under the default `any`, it holds each species of a full cavern at FREQUENCY 0, and FREQUENCY belongs to the creature, so that reaches every cavern.

The tool's own cavern draw (P9, `V7.DRAW.caveTick` :15997) skips species with a surface or water group, but **not species already in that same cavern**. Its only steer away from repeats is "least seen this season" (:15916), and that runs only after 4 days with no DF wave. The repeats seen in the rig were DF waves.

**Does a group in place A block place B today?**

| Already has a group in... | Blocks the same species in... |
|---|---|
| ground or flying | ground and flying: **yes**, but **not while the land pause is on**. Water draws: no. Caverns: no. |
| one kind of water (e.g. a pond) | the same kind (any pond): **yes**. Its surface entries (DF's waves of it): **yes**, outside the land pause. Ground/flying draws: yes. Another kind (lake, river): **no**. |
| a cavern | **nothing**: not that cavern, not another cavern, not the surface. The only exception is the cap-driven FREQUENCY hold, which is not a per-species rule. |

Casts make the cross-layer question mostly moot. In SAVR_d1, COAST and LAKE3 the surface and cavern casts share no species. Caverns share 0 species with each other in spring and 1-2 in each other season.

**The leak.** `speciesPause` returns early while the land pause is on (:16234).
- That was correct on 22 Oct, when the land pause held every surface entry.
- Since 8fc1c32 (23 Oct) and option A, the flying cast's and water casts' entries are left out of the land pause (:15749-15768). They are closed only by the flying pause and the per-kind bird pause, each at its *own* cap.
- So whenever the ground is full, the rule is off for those species.
- **B2 P2_COAST ledger:** land paused on Autumn 3 (line 145). The tool drew a barn owl on Autumn 4 (156-157). A DF barn owl wave came on Autumn 5 (166). B1 PC_COAST (older code) had barn owls on Autumn 6, 7, 9, 9.

### (b) What DF does (evidence)
- **FREQUENCY belongs to the creature, not the place.** A per-cavern species limit must use the extinct flag on that species' one entry in that cavern.
- **The extinct flag stops cavern waves.** This was rig-tested on 13 Oct for whole caverns (pause-not-trim). Closing a single entry is proven on the surface, not yet in caverns.
- **Stall rule** (cavern-zero-freq-freeze): DF stalls if every stocked, open entry in one cave on one region tile reads FREQUENCY 0. A per-species closing is part of a tile's stock, so `V7.GRP.keepAlive` (:16616) must run after it.
- **DF's cavern pick seems to follow stock** (cavern-pick-stock-weighted, PENDING).
- **One DF wave can arrive in pieces.** P12 (`discoverGroups` :5414) joins a tail within one day, assuming "one_per_species has closed the species' entries". That holds on the surface, not in caverns.

### What the rig shows (B2, provisional)
| Fort, cavern | Top species | Share of arrival days |
|---|---|---|
| P2_SAVR cavern 3 | flesh ball | 46% |
| P2_SAVR cavern 2 | giant olm | 45% |
| P2_LAKE cavern 1 | helmet snake | 38% |
| P2_LAKE cavern 3 | flesh ball | 36% |

- P2_SAVR cavern 3 ended with 7 groups of only 3 species, 5 of them flesh balls, all DF waves.
- P2_EVIL had three blind cave bears (the apex) in cavern 1, on Spring 15, 19 and 21.
- B2 already had P10 (`open_stock`) and P12. PLAN-v8.1 makes a per-species pause conditional on those fixes failing to bring every species under ~35%. On this evidence they have not, but B2 is not formally analysed yet.

### What would happen if it changed
**1. Per cavern, with the same switch-off (the good version).**
- The first flesh ball group in cavern 3 closes the flesh ball entry *in cavern 3*. The other 6 slots go to the other autumn members.
- Up to 6 species in 7 slots, against 3 today. In P2_EVIL, at most one cave bear.
- It also makes P12's assumption true underground.
- **Unknown:** does DF keep sending waves once the heavily stocked entry is shut? If not, the 4-day fallback draw fills in. For that, `V7.DRAW.pick` must also count that cavern's own groups.

**2. A strict maximum with no switch-off.**
- In caverns it costs about one slot (casts of 5-6 against a cap of 7).
- Small casts lose much more: SAVR's ponds, where only the osprey fits, would drop from up to 4 groups to 1.
- It also flattens the prey base of the food pyramid.

**3. One count shared by all three caverns.** It shuts a species out of cavern 3 because it is in cavern 1. That gains nothing natural.

### Design points
- **Keep holding under the cavern pause.** Do not copy the surface version's early return. Re-assert every pass.
- **Run `keepAlive`** after every closing.
- **Count groups still waiting at the gate.**
- **Leave irruptions alone.** They are outside the cap by design (:15587).
- **Adopted natives count.** Young born to a tracked mother join her group (:16764).
- **A separate switch**, e.g. `groups onespecies cavern on|off`.

### Recommendation
1. **Fix the leak first.** Under the land pause, `speciesPause` should still close the flying cast's and water casts' surface entries.
2. **If you want caverns included:** per cavern, with the switch-off, and the cavern draw counting that cavern's own groups.
3. **Do not use** one count across all caverns, or a strict maximum.
4. **Optional food-web variant** (untested): predators and apexes at 1 group per cavern, prey at up to 2.

### Rig tests (not run)
1. **Cavern rule.** B2 forts (SAVR, COAST, EVIL), caverns breached, same probe, per-cavern rule on against B2.
   - Measure per cavern: species and effective species, top species' share, cast members seen, mean groups against the cap, days under the cap with no arrival, DF cavern waves per season, fallback draws, and a FREQUENCY-0 stall check every pass.
   - **Pass if:** top species ≤35%, effective species ≥60% of the cast, caverns no emptier than B2.
2. **Leak fix.** Replay the coast autumn with the land at its cap and the flying layer under its cap. Expect at most one barn owl group.

**Rig test that would settle it:** (1) Per-cavern one-group-per-species rule (extinct flag on that cavern's single entry, held under the cavern pause, keepAlive after each closing, switch-off when every in-season member is present, cavern draw counts that cavern's groups, irruptions exempt) on B2 forts SAVR/COAST/EVIL v B2: top-species share, effective species, cast seen, mean groups, empty days, DF waves/season, fallback draws, FREQUENCY-0 stall check. Pass: top <=35%, effective >=60% of cast, no emptier. (2) Leak fix: replay P2_COAST Autumn 3-6 (land at cap, flying under cap); expect at most one barn owl group.

<details><summary>Review and verification trail</summary>

- review: Confirmed against 6dffef5: the help line (:61-62), commit 670636d ('Caverns not included'), presentRaces skipping cavern groups (:16213), the switch-off in speciesPause (:16285-16287), the water rule (:7854-7863), water candidates ignoring the extinct flag (ENGINE.candidates :7322ff, only pop.quantity > 0), and the cavern draw's present list leaving out cavern groups (V7.DRAW.pick :15910, :15928).
- review: Leak evidence strengthened and caveated. B1 (PC_COAST) ran 987cffc, before P12 merged wave pieces, so its 4 barn owl groups may include pieces of one wave (two arrived on day 9). Added a case from the current code: in B2 P2_COAST (6dffef5) the land pause was on from Autumn 3 to 6, the tool drew a barn owl on Autumn 4, and DF sent another barn owl wave on Autumn 5. No 'one group per species' line exists for barn owls in either ledger. Added the history: speciesPause (22 Oct) was written to wait under a land pause that then held every surface entry; flyPause (8fc1c32, 23 Oct) took fliers and water-cast species out of the land pause, which opened the gap. The leak covers water-cast species' surface entries too, not only birds.
- review: Replaced the end-of-run snapshot with dominance counted over the whole run, by arrival days, from the B2 probe.jsonl group records. In P2_SAVR, flesh balls took 46% of cavern 3 and giant olms 45% of cavern 2. In P2_LAKE, flesh balls took 36% and helmet snakes 38%. Both runs had open_stock and P12. That is still above PLAN-v8.1's own 35% target, and that target is the plan's stated condition 'before any per-species pause is considered'. All of P2_SAVR's cavern 3 flesh ball groups were DF waves (src 'df'), not natives. A fifth flesh ball wave was released on Autumn 1 while four were already there.
- review: Corrected the inference about young born in a cavern. The adoption code (:16764) puts a calf, cub or fry whose mother is in a tracked group into her group, so it does not start a new one. Untracked natives do become counted groups and would hold their species closed.
- review: Added a design risk the answer missed. The cavern pause deliberately closes a whole cavern depth, 'never part of a tile's stock' (:16319; pause-not-trim.md), to keep away the FREQUENCY-0 stall. A per-species closing breaks that pattern, so keepAlive (:16616) must run after it. It also must not copy the surface flaw: it has to keep holding under the cavern pause, never open entries there, and re-assert every pass.
- review: Added: irruption waves sit outside the cavern cap (:15587), and irruption placement does not read the extinct flag (IRRUPT.candidates :14107). The rule has to leave irruptions alone, because an irruption is a surge of one species by design.
- review: Toned down 'a strict maximum would mostly leave slots empty'. In the caverns it costs about one slot of 7, because casts there have 5-6 members. It bites hard only where the cast is tiny: a pond with one fitting species, or a flying cast of 3 against a cap of 4.
- review: Cast overlap figures checked in SAVR_d1, COAST and LAKE3: caverns share 0 species in spring and 1-2 in the other seasons; the surface and cavern casts share none.
- review: Added a middle option for ecology, marked as my suggestion: predators and apexes at one group per cavern, prey at up to two.
- verifier: 'Each water body keeps its own' count corrected to 'each KIND of water': the census and mix are keyed by type (V7.WAT.bodyAt :7690). All ponds share one one-group-per-species check, and so do all river scraps.
- verifier: Table row for water corrected the same way: within one kind (two ponds) a group does block; across kinds (lake and ponds) it does not.
- verifier: Line refs checked: presentRaces skips caverns :16213; speciesPause early return under the land pause :16234; switch-off :16285-16287; DRAW.pick uses presentRaces :15910; caveTick has no same-cavern check :15997; landPause leaves the flying cast and the water casts out :15749-15768; config one_per_species :1028; commit 670636d says 'Caverns not included'.

Code refs: sw-wt/plugin/scripts/seasonal-wildlife.lua:61-62 (help: onespecies, land and each water); sw-wt/plugin/scripts/seasonal-wildlife.lua:1017 (cavern_cap=7, cavern_hold='any', natives_cavern=true, cavern_draw_grace_days=4, cave_open_stock=30); sw-wt/plugin/scripts/seasonal-wildlife.lua:1028 (one_per_species=true), :1030 (cave_single_source); sw-wt/plugin/scripts/seasonal-wildlife.lua:3297-3304 (one cavern entry per species, anchor group); sw-wt/plugin/scripts/seasonal-wildlife.lua:5406-5414 (P12 discoverGroups, JOIN_TICKS, 'one_per_species has closed the species' entries'); sw-wt/plugin/scripts/seasonal-wildlife.lua:7322 (ENGINE.candidates: stock only, no extinct check); sw-wt/plugin/scripts/seasonal-wildlife.lua:7706 (V7.WAT.census), :7854-7863 (V7.WAT.mix one per species); sw-wt/plugin/scripts/seasonal-wildlife.lua:15581-15590 (V7.GRP.cavernPass; irruption groups outside the cap at :15587); sw-wt/plugin/scripts/seasonal-wildlife.lua:15735-15768 (V7.GRP.landPause excludes fliers and water-cast species); sw-wt/plugin/scripts/seasonal-wildlife.lua:15908-15943 (V7.DRAW.pick: present = presentRaces, season tally steer :15916); sw-wt/plugin/scripts/seasonal-wildlife.lua:15997 (V7.DRAW.caveTick, P9 fallback); sw-wt/plugin/scripts/seasonal-wildlife.lua:16075 (V7.GRP.flyPause); sw-wt/plugin/scripts/seasonal-wildlife.lua:16194-16312 (design comment, presentRaces :16210-16216, speciesPause :16230, early return under land pause :16234, switch-off :16285-16287); sw-wt/plugin/scripts/seasonal-wildlife.lua:16313-16321 (cavern pause: close a whole depth, never part of a tile's stock); sw-wt/plugin/scripts/seasonal-wildlife.lua:16527-16546 (V7.GRP.holdFor: absolute gate holds at 0); sw-wt/plugin/scripts/seasonal-wildlife.lua:16616 (V7.GRP.keepAlive), :16713 (V7.GRP.cavernHold 'any'); sw-wt/plugin/scripts/seasonal-wildlife.lua:16764 (natives: young join the mother's group); sw-wt/plugin/scripts/seasonal-wildlife.lua:14107 (IRRUPT.candidates: no extinct check); sw-wt/plugin/scripts/seasonal-wildlife.lua:17410-17417 (pass order: bird, land, flying, species pause); sw-wt/plugin/docs/pacing/PLAN-v8.1.md:106-137 (P10, open_stock PENDING, 35%/60% target 'before any per-species pause'); git 670636d ('Caverns not included', 'waits under the land pause'); git 8fc1c32 (flying pause, fliers out of the land pause, 23 Oct); DwarfCron/data/pacing/B2/P2_COAST/ledger.txt (land paused Autumn 3-6; barn owl drawn Autumn 4, DF barn owl wave Autumn 5); DwarfCron/data/pacing/B1/PC_COAST/ledger.txt (barn owl x4 Autumn 6-9; code 987cffc, pre-P12); DwarfCron/data/pacing/B2/P2_SAVR/groups-end.txt, probe.jsonl, ledger.txt (flesh ball x5 in cavern 3, all src df; 5th released Autumn 1); P2_LAKE/probe.jsonl; P2_EVIL/ledger.txt (blind cave bear Spring 15, 19, 21); DwarfCron/.claude/scratch/pacing/ladder/SAVR_d1.json, COAST.json, LAKE3.json (cavern casts 5-6; cross-cavern overlap 0 in spring, 1-2 in the other seasons; no surface/cavern overlap); memory: pause-not-trim.md, cavern-zero-freq-freeze.md, cavern-pick-stock-weighted.md, df-wave-pick-per-entry.md, beta-rulings-oct16.md

</details>

## B3

> What would happen if... instead of "cavern 1 · 7" for the 3 cavern layers, it was set to a different number for each layer? How did the cavern caps get set to "cavern 1 · 7"? Can every cavern layer have up to 7 species groups placed at one time? What would happen if that cap number was changed?

**Short answer.** 'cavern 1 · 7 / 2 · 7 / 3 · 7' is one setting, groups.cavern_cap = 7, shown three times. Each cavern has its own count, pause and clock, but they share that number (5 from v7.1 R44, raised to 7 on 16 Oct so each of six cast species could have a group plus a thief). It allows up to 7 GROUPS per cavern, not 7 species. In B2, 7 groups held only about 3-4 species, and caverns went over 7 on ~1 in 5 checkpoints. Per-cavern numbers would need a small code change. They would act as a crowding and danger dial, not a diversity dial; repeats are what limit cavern diversity.

*Status: corrected · confidence medium · review verdict: minor fixes*

### Short answer
"cavern 1 · 7 / cavern 2 · 7 / cavern 3 · 7" is **one setting shown three times**: `groups.cavern_cap = 7` (seasonal-wildlife.lua:1017). Each cavern keeps its own count, its own pause and its own release clock; they just share the number.
- **Up to 7 groups per cavern, not 7 species.** Three flesh ball groups take three of the 7 slots.
- **7 is not a hard ceiling.** On B2's lake fort, caverns 2 and 3 were over 7 on about 1 in 5 checkpoints.
- **Different numbers per cavern** would mostly change crowding, danger and FPS cost. They would do little for diversity.

(The code numbers caverns 0/1/2; below they are 1/2/3, as on the diagram.)

### 1. How the cap is set (code)
- **Default:** `cavern_cap=7` (:1017). Settings are saved per fort, so a fort first set up before v7.6.1 keeps 5.
- **Where it is read:** `QUOTA.groupsFor` (:4458-4471) returns `max(1, cavern_cap)` for any cavern, whatever the map size. Under `limits fixed N` it returns the smaller number.
  - Every other place (ground, flying, ocean, lake, river, ponds) gets ⌊√embark tiles⌋+1.
- **Why per-cavern numbers are impossible today:**
  - `V7.GRP.cavernPass` asks for the cap **once**, as `'cavern'` (:15583), before looping over the three caverns.
  - `groupsFor` strips any depth from the key (:4459).
- **Ways to change it:** `groups cavern cap N`, `limits cavern groups N`, or the window's "Cavern cap" control (1-20, controls.lua:142).

**History:**
- **Until v7:** all three caverns shared one count of 2.
- **v7.1, R44 (7c45e53, 1 Oct):** each cavern got its own cap of 5, "universal and fixed". The earlier caps counted only the tool's groups, never DF's own 4-5 per cavern. *Inference:* 5 matched what DF already kept there.
- **v7.6.1 (c244e34, 16 Oct, your "raise the group cap of the caverns by 1-2"):** 5 → 7, "so the six cast species of a cavern can each have a group on the map with room for a placed thief".

**What counts toward the 7** (`cavernPass` :15586-15590): DF waves (waiting at the gate or let in), the tool's draws, apex and thief placements, and adopted natives. **Not counted:** irruption groups, and anything below cavern 3.

### 2. What happens at the cap
- **The pause** (`V7.GRP.cavePause` :16375): at 7, every cavern Animal entry at that depth gets the extinct flag.
- **It reopens only at 5** (`resumeAt` = cap − `pause_margin` 2, :15673). Then **every** closed entry reopens at once. The B2 COAST ledger shows "cavern 1 resumed (5 of 7 groups): 525 entries opened again".
- **Second brake: the FREQUENCY hold** (`V7.GRP.cavernHold` :16713). It sets each natural species of a full cavern to FREQUENCY 0 (vermin 1).
  - FREQUENCY belongs to the creature. Under the default `any`, a species is held in **every** cavern where it has a DF entry as soon as **any** of those caverns is full.
  - Species that also live on the surface are left alone. `keepAlive` guards against the zero-frequency stall.
- **Nothing is sent off.** Trimming is off while the pause switch is on (your 13 Oct "pause, not trim" ruling).
- **No one-group-per-species rule in caverns** (`presentRaces` skips them, :16213), so repeats are allowed.

### 3. How caverns end up over 7 (B2 lake fort, 6dffef5)
Checkpoints over 7: cavern 1 on 2 of 59, cavern 2 on 13 of 59, cavern 3 on 11 of 59. There are four paths:
1. **Reopen-all at 5, no re-close until 7.** `if not s.on and n < cap then return nil` (:16388). Cavern 3, spring days 49-51: it reopened at 5, then a manera arrived (6) and the pause did not close again.
2. **Two arrivals in one 300-tick pass** (`GROUPS_CADENCE` :5152). 300 ticks after the manera, a cave floater and a flesh ball came in one pass, making 8. P12 joins one species' wave, not two different species. 11 of 59 DF-arrival passes brought two groups.
3. **Apex placements ignore the pause and the cavern cap.** `ROSTER.apex.decide` (:11691) checks only the apex cap, 1 calm / 2 savage (:9113), counted across **all three caverns together**. Only thieves skip a paused cavern (:11724). Examples: a jabberer took cavern 3 to 9/7, and a blind cave bear took cavern 1 to 8/7.
4. **A jump after a reload, not explained.** Cavern 2 sat at 7/7, paused. After the run reloaded K07, two DF groups arrived 331 and 631 ticks after the load: 7 → 9. *Inference only:* something on load briefly opens entries, for example DF re-reading raws at load and wiping the FREQUENCY hold.

The tool's own draws (P9) also check only n < cap, not the pause (see B4).

**Readout trap:** status lines and the probe count irruption groups; the cap does not. Cavern 3's summer "9/7" was 6 counted groups plus 3 gremlin irruption groups. That is by design.

### 4. "Up to 7 species groups at one time?"
Up to 7 **groups**, yes, and caverns are almost always full. Up to 7 **species**, no.

| B2 lake fort, 59 checkpoints | mean groups* | species at once | cast species present | paused |
|---|---|---|---|---|
| cavern 1 | 6.5 | 3.5 | 3.4 of 6 | 93% |
| cavern 2 | 6.8 | 4.2 | 4.1 of 6 | 84% |
| cavern 3 | 6.6 | 3.2 | 3.0 of 6 | 93% |

*Irruption groups excluded.

- **B1 agrees:** caverns averaged 6.0-7.3 of 7. Exception: the coast fort's cavern 3 got no DF wave in 171 days. The cap means nothing where DF sends nothing.
- **Over a whole season, 4-6 of the 6 cast species show up at least once.** At any one moment, though, the 7 slots hold 3-4 species: helmet snake 10 of 28 arrivals in cavern 1; flesh ball 8, cave floater 5 and manera 4 in cavern 3.
- **"Six species plus a thief" does not hold in practice.** The slots are not tied to species. A thief is placed only while its cavern is not paused, and these caverns were paused 84-93% of the time. No thief was placed on this fort.

### 5. What a different number would do (thought experiment)
Expected distinct species at once, if slots filled by this fort's arrival shares. The model reads about 0.5 high.

| cap | 4 | 5 | 7 (now) | 10 | 12 |
|---|---|---|---|---|---|
| cavern 1 | 2.9 | 3.4 | 4.0 | 4.8 | 5.1 |
| cavern 2 | 3.1 | 3.6 | 4.4 | 5.3 | 5.8 |
| cavern 3 | 3.0 | 3.5 | 4.3 | 5.2 | 5.6 |

- **Cap 4:** about 1 species fewer and about 7 fewer animals per cavern. An apex takes 1 of 4 slots.
- **Cap 10:** about 1 species more, but most extra slots go to the same dominant species. About 7 more animals per cavern, about +1-2% FPS cost, and more cave beasts near an open breach. Empty caverns stay empty.
- **Cap 1-2:** resumes only at 0, so the cavern runs mostly empty.
- **Per-cavern numbers** (e.g. 9/7/5, "cavern 1 least weird"):
  - Mostly independent already: count, pause and clock are per cavern.
  - **Coupling 1** (inference): the FREQUENCY hold under `any` lets a tight cavern silence a shared species in another cavern (giant cave toad in caverns 1+2; rutherer in caverns 2+3). `cavern_hold all` avoids this.
  - **Coupling 2:** the apex cap is shared across all three caverns.
  - **Code work:** a `cavern_caps {c1,c2,c3}` setting; `groupsFor` keeps the depth; `cavernPass` looks up the cap inside its loop; the readers that print one cap; a verb; a controls-registry row with a reaches-the-engine check (20 Oct ruling).
  - None of this fixes the overshoot.

### 6. Does it serve your aims?
- **Diversity: barely.** The cap sets crowding. 7 → 10 buys about one species for about 40% more cave animals.
- **Ecology: yes, as a design choice.** Fewer, stranger animals deeper down is a fair naturalistic lever. Treat it as a crowding and danger dial.
- **Better first steps (tune existing code, 16 Oct ruling):**
  1. Make the cap hold: count draws before they land; make apex placements respect the cavern pause or count toward it; reopen a few entries at a time; find the reload leak.
  2. Read B2's P10 result. If repeats remain, decide on a per-cavern one-group-per-species rule (B2). That is what would turn 7 groups into about 6 species plus a thief.
  3. Then choose per-cavern numbers for ecology reasons.

### 7. Rig tests (not run)
1. **Cap alone:** `groups cavern cap 4/7/10` on new embarks of the B2 lake tile (region6 16,17, 7×7) and the B2 savage tile. 50 dwarves, caverns breached, one season, probe every 2 days, 5 reps per arm.
   - Measure per cavern, irruptions excluded: mean groups, distinct species (de-duplicated by arrival tick + species), cast covered, over-cap checkpoints by cause, paused %, days at 0, stopwatch FPS.
2. **Reload leak:** from a fort paused at its cap, reload and log counts, extinct flags and FREQUENCY for 1,200 ticks, against a no-reload control.
3. **Per-cavern caps** (after the code change): 9/7/5 against 7/7/7. Also log how often a two-cavern species is held at 0 while its other cavern is under its cap.

**Rig test that would settle it:** Test 1: groups cavern cap 4 v 7 v 10 on new embarks of B2 lake tile (region6 16,17, 7x7) and B2 savage tile, 50 dwarves, caverns breached, one season, probe every 2 days, 5 reps/arm; per cavern excluding irruptions: mean groups, distinct species (dedupe by arrival tick+species), cast covered, over-cap checkpoints by cause, paused %, days at 0, FPS. Test 2: reload a fort paused at its cavern cap, log counts/extinct flags/FREQUENCY for 1,200 ticks v no-reload control. Test 3 (after code change): per-cavern caps 9/7/5 v 7/7/7 plus cross-cavern FREQUENCY-0 hold frequency.

<details><summary>Review and verification trail</summary>

- review: Verb fix: `limits fixed N` does not set the cavern cap. It can only lower it, because groupsFor takes min(cavern_cap, fixed) at :4467. Line :23998 is a different verb, `limits cavern groups N`, and that one does set cavern_cap. Also added the window/registry control (internal/seasonal-wildlife/controls.lua:142, range 1-20).
- review: Wrong examples corrected. On the B2 lake fort the bugbat is cast only in cavern 1, and the giant cave toad is cast only in cavern 1. The hold's 'any' rule follows where a species has DF entries (V7.GRP.species s.d), not where it is cast. Real examples from the probe: giant cave toad groups arrived in caverns 1 and 2, and the rutherer is cast in both caverns 2 and 3 in summer.
- review: Added a fourth overshoot path. Cavern 2 went from 7 to 9 while paused, with no group leaving. The two arrivals came 331 and 631 ticks after the run reloaded K07 (save tick 33905, arrivals at 40354236 and 40354536). The mechanism is not proven.
- review: Readout trap added. The status/probe count includes irruption groups, because the status loop at :17165-17186 has no `not grp.irruption` test. The cap's own count excludes them (:15587). Cavern 3's summer '9/7' is really 6 counted groups plus 3 gremlin irruption groups.
- review: Added how often caverns go over the cap: cavern 1 on 2 of 59 checkpoints, cavern 2 on 13, cavern 3 on 11 (8 once irruptions are taken out). Two overshoots were apex placements: the jabberer in cavern 3 (spring) and a blind cave bear in cavern 1 on summer day 1.
- review: Apex claim fixed. The apex cap (cap_calm 1 / cap_savage 2, :9113) is counted across all three caverns together (groupsOnMap with cavern=true), not per cavern. 'A quarter to a third of the slots' was overstated.
- review: P10 is already in the B2 code (ec63e66 is an ancestor of 6dffef5), so the 3-4 species per cavern was measured with open_stock 30 on. The answer had treated P10 as a future fix.
- review: B1 range corrected to 6.0-7.3 groups (evil fort cavern 3 averaged 7.32). Noted that coast cavern 3 averaged 0.14 groups (146 days at 0).
- review: Test spec fixed: the B2 lake embark is 7x7 (embark.log), not 3x3. That is also why land shows a cap of 8.
- review: History made more precise. The 2-for-all-caverns count comes from the comment at :4450-4452 ('until v7'). cavern_max=7 at :1018 is now only a mirror. The link between choosing 5 and DF's own 4-5 groups per cavern (:15557-15559) is marked as inference. c244e34 says saved configs keep their own values; the config is per fort (site data, :1133).
- review: Recomputed on 59 checkpoints (the run has moved on). Mean groups 6.5 / 6.8 / 6.6. Species present at once 3.5 / 4.2 / 3.2. Model prediction for caps 4/7/10: about 3.0 / 4.2 / 5.1, which runs about 0.5 high at a cap of 7.
- review: Added that each cavern already behaves on its own apart from three links: the creature-wide FREQUENCY hold, the cavern-wide apex cap, and irruptions. So Test 1 (one cap at 4/7/10) already predicts most of what per-cavern caps would do. Test 2 is only needed for the hold link.
- verifier: The cavern pause's 'no re-close under cap' line is :16388 (inside V7.GRP.cavePause, which starts at :16375), not :16371.
- verifier: Checked and kept: cavernPass asks for the cap once as 'cavern' (:15583) before the depth loop; groupsFor strips the depth (:4459); irruption groups are left out of the count (:15587); resumeAt = cap − pause_margin (:15673); cavernHold 'any' by DF entries, shared species excluded (:16713-16722); holdFor 0, vermin 1 under the absolute gate (:16539); the apex cap is counted across all three caverns (groupsOnMap(races, true) :11548-11560); thieves skip a paused cavern (:11724).
- verifier: B2 P2_COAST ledger supports 'reopen everything at once': 'cavern 1 resumed (5 of 7 groups): 525 entries opened again' (line 146).

Code refs: /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:1017 (defaultConfig cavern_cap=7, cavern_hold='any'); :1036-1038 (cavern_pause, pause_margin=2); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:911-943 (V7.grpSanitize keeps cavern_cap, mirrors cavern_max); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:4447-4471 (QUOTA.groupsFor: depth stripped, cavern cap fixed, min with limits fixed); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:15557-15634 (V7.GRP.cavernPass: one cap, per-depth count excluding irruptions, draw, release, pause, trim off under pause); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:15673 (V7.GRP.resumeAt); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:16338-16408 (V7.GRP.caveResume / cavePause; :16371 no re-close under cap); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:16527-16541 (V7.GRP.holdFor: 0, vermin 1); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:16713-16759 (V7.GRP.cavernHold 'any' by DF entries); V7.GRP.species (s.d from population entries); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:16195-16217 (one_per_species excludes caverns; presentRaces); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:5152 (GROUPS_CADENCE 300); :5405-5451 (discoverGroups, P12 join); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:9112-9114 (apex presence cavern 70, cap_calm 1, cap_savage 2, thief_presence 50); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:11691-11737 (ROSTER.apex.decide: own cap only; thief skips paused depth :11724); ROSTER.apex.groupsOnMap (cavern-wide count); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:15380-15412 (gapFor/dueTick/releaseGap); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:15997-16026 (V7.DRAW.caveTick); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:17165-17186 (status count includes irruption groups); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:23965-23999 (limits fixed N vs limits cavern groups N); :24068-24091 (groups cavern cap N); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/internal/seasonal-wildlife/controls.lua:142 (Cavern cap control 1-20); git c244e34 (v7.6.1, 16 Oct: cavern cap 5 -> 7); git 7c45e53 (v7.1 R44 cap 5); ec63e66 (P10 open_stock, in 6dffef5); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/docs/pacing/PLAN-v8.1.md (B1 findings, P10, P12); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/B2/P2_LAKE/probe.jsonl (59 checkpoints; cavern 3 spring days 49-57; cavern 2 day 29-31 post-reload jump; summer gremlin irruption groups); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/B2/P2_LAKE/embark.log (7x7), saves.log (K07 load at tick 33905), run.log; /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/B2/master.log:50-59; /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/B1/summary.md; memory: cavern-pick-stock-weighted.md, cavern-zero-freq-freeze.md, pause-not-trim.md, beta-rulings-oct16.md, full-pool-design-oct9.md, fps-load-facts.md, breach-every-fort-test.md

</details>

## B4

> What does "place at its cap" mean? Does this mean that cap-number of groups are placed each time a placement occurs?

**Short answer.** No. A cap is the most groups one place may hold AT ONCE. It is never a number placed in one go. 'Place at its cap' (noun) means 'that place is full', e.g. 4 of 4 on a 3x3 ground or 7 of 7 in a cavern. When that happens, DF's entries for that place are closed (paused) and reopen at cap−2. Groups arrive one at a time on a clock. Bursts happen only through several DF sources, coupling, apex placements or adopted natives. One quirk: the tool's own draws ignore the pause and refill at cap−1.

*Status: corrected · confidence high · review verdict: minor fixes*

### Short answer
**No.** The cap is a **ceiling on how many groups one place may hold at the same time**, never a number of groups placed in one go. Your diagram says the same (panel 1, line 121): *"Cap: the most groups one place may hold at once."*

The confusion is probably the word **"place"**:
- In "place at its cap" (line 191), "place" is a **noun**: one of the boxes under "Places + caps" (ground, flying, ocean, lake, river, ponds, cavern 1/2/3). The phrase means **"that place is full"**, e.g. 4 of 4 groups on a 3×3 ground, or 7 of 7 in cavern 2.
- In the next box, "③ The tool **places** a group", it is a verb. Read together, the two make it look as if the tool places cap-many groups. It doesn't.

Suggested wording: **"a place that is full (holding its cap of groups) → its entries CLOSED (pause), reopened at cap − 2"**.

### (a) What the code does
**1. Places and caps** (`QUOTA.groupsFor` :4458-4471)
- **Ground, flying, and each kind of water** (ocean, lake, river, ponds): ⌊√(embark tiles)⌋ + 1. That is 4 on 3×3 and 5 on 4×4. All ponds on the map are one place with one cap (see B1).
- **Each cavern:** `cavern_cap = 7` (:1017), whatever the map size (your 16 Oct ruling).
- **It counts groups, not animals** (`ENGINE.count` :7515): one lone animal and a pack of nine each take one slot. DF's seeded water schools are not counted.
- **A DF wave still "waiting at the gate" already counts.** It is already on the map.

**2. Arrivals come one at a time, on a clock.** The groups job runs every 300 ticks, a quarter day (:5152). On the ground (:17421), if the count is under the cap and the clock is due, the tool does **one** of two things:
- **Release the oldest waiting DF wave** (`detachOldest` :5471), which lets that DF source send its next wave. `V7.drainGate` may release a few more, but only up to `cap − n − 1`.
- **If no DF wave is waiting, draw one ground cast member's group itself** (`V7.DRAW.one`, new in v8.1).

`V7.GRP.releaseGap` (:15402) then sets the next due time. The other places work the same way:
- flying: `V7.DRAW.flyTick`;
- water: `V7.waterTick`, one kind per pass;
- caverns: `V7.GRP.cavernPass`, where a draw also waits 4 days with no DF wave.

**3. When a place is full: the pause.**
- **Ground** (`V7.GRP.landPause`): at the cap, every open surface entry gets the extinct flag, so DF cannot pick it. Stock and FREQUENCY are untouched. Ledger: *"land at its cap (4 of 4 groups): paused, N entries closed until a group leaves."*
- **Reopening:** at cap − `pause_margin` 2 (:15673). The ground (cap 4) reopens at 2, a cavern (7) at 5.
- **The same rule covers:**
  - flying (`flyPause` :16075);
  - each kind of water's DF arrivals (`birdPause` :16145). DF does send water-cast species (birds, shore animals, swimmers, fish) through surface entries. The tool files them as water groups of the cast's main kind: fresh → lake if there is one, else river, else ponds; sea → ocean (`V7.GRP.waterBirds` :15800). They count toward that cap;
  - each cavern (`cavePause` :16375), plus the FREQUENCY-0 hold (vermin 1).
- **Nobody is sent off** while the pause switch is on (13 Oct, pause not trim).

**4. When several groups land close together.** None of these is "cap-many per placement":
- **Several DF sources.** DF's gate works per source. A place reopened with two free slots can take two waves before the next pass. That is why the margin of 2 was added (414d494, 13 Oct): reopening at cap−1 had let the ground reach 6 of 5.
- **Coupling.** When prey arrives, its predators are called next. B2 P2_SAVR, Autumn 1-2: the ground reopened at 1 of 4 and within about a day had an adder, a DF arthropleura and dingo men.
- **One DF wave filed as several groups** (B1 only). The current build (P12) joins a wave's tail.
- **Placed without checking the place's cap:**
  - **Apex placements** (`ROSTER.apex.decide` :11691) check only the apex limit, 1 calm or 2 savage (:9113). For caverns that limit is a total across all three caverns. They do not check the place's cap or pause.
  - **Adopted natives** count and can push a place over.
  - **Irruption groups** are outside the cavern count by design.

B2 still went over at some checkpoints: caverns at 8-9 of 7, the ocean at 5 of 4.

**5. The tool's own draws ignore the pause.** Draws check only `n < cap` and the clock (ground :17421, flying :15979, caverns `caveTick` :15998). The pause only closes DF's entries. So reopen-at-cap−2 applies to DF; the tool's draws in effect use cap−1.

B2 P2_SAVR shows it:
- The ground paused on Summer 74 and did not reopen until Autumn 1.
- The tool drew an iguanodon herd on day 78 and a black bear on day 81, each at 3 of 4 (the ledger prints "4 of 4", counting the new group).
- So DF's ground waves were shut out for about 11 days while draws kept the ground full. P2_COAST shows the same four times.

### (b) What DF does (evidence)
- DF picks waves only from **open** entries; the extinct flag alone stops a pick (E8).
- DF sends a new wave from a source only while none of that source's flagged animals are on the map (E1, E40).
- On the surface, the pick follows FREQUENCY per entry. In caverns it seems to follow stock (PENDING, P10).

### Thought experiment: 3×3 ground, cap 4
Gap after an arrival = W / L* × 1/(1 + (L* − n)) × jitter, where n counts the new group (`gapFor` :15380). W is how long groups stay; L* is the target, drawn between 3 and 4 (take 3.5).

| After arrival | W = 28.75 days (prior) | W = 9 days (learned on SAVR) |
|---|---|---|
| 1st (1 there) | 2.3 days | 0.7 days |
| 2nd (2 there) | 3.3 days | 1.0 day |
| 3rd (3 there) | 5.5 days | 1.7 days |
| 4th (4 there) | full: clock stops, DF's entries close | same |

So an empty ground fills **one group at a time** over about 3.5-11 days. Once full, departures set the pace. With a margin of 2, DF stays shut until two groups have left, while the tool's draw refills at 3.

### Does it serve your aims? (inference)
- Places sit full most of the time (B1: at the cap 68-89% of the time). So **the cap and how long groups stay set how many animals are on the map**. The ladder and the draw decide **who** fills a slot when one opens.
- The tool's draws pick the least-seen cast member, which helps diversity. DF's waves gave the bugbat, flesh ball and raven dominance. Draws refilling at cap−1 while DF waits for cap−2 may already help, but by accident, not by a rule you chose.
- **Options** (tune existing code, 16 Oct ruling):
  1. **Make it consistent on purpose.** Either draws also wait for the reopen (a one-condition change), or the page says draws refill at cap−1.
  2. **Margin 1 for DF.** This risks the 6-of-5 overshoot again, though part of that was the wave-in-pieces bug, which P12 now fixes.
  3. **Staged reopen:** reopen one slot at a time.
  4. **P12's second half:** releases and draws count against the cap before the wave lands. Not built yet.

### What would settle it
- **No rig needed:** count from the B2 ledgers how many arrivals were tool draws made while the place was paused, and how long DF stayed shut out.
- **Rig:** re-embark a 3×3 fort (ground, flying, a river, caverns breached) with `pause_margin 2` against `pause_margin 1` (or a staged reopen), n=5 runs per arm. Compare:
  - over-cap events;
  - same-tick bursts;
  - share of time full;
  - arrivals split DF/draw;
  - effective species per layer.

**Rig test that would settle it:** Meaning of the cap needs no test. Before any rig run, count from existing B2 ledgers the tool draws made into a paused place and how long DF's entries stayed shut. To settle the margin: re-embark one 3x3 fort (ground, flying, river, caverns breached) with pause margin 2 v margin 1 (or staged one-slot reopen), same season, n=5 per arm; measure over-cap events, same-tick bursts, share of time full, arrivals per season DF v draw, effective species per layer.

<details><summary>Review and verification trail</summary>

- review: Added the likely source of the confusion. In the diagram, 'place' is a noun: one of the nine boxes under 'Places + caps' (ground, flying, ocean, lake, river, pond, cavern 1-3). 'Place at its cap' (mechanics-diagram.html:191) sits in the entries box, next to box 3, 'The tool places a group', where 'places' is the verb. The cap is defined at line 121 as 'The most groups one place may hold at once.'
- review: Corrected 'DF sends no water waves'. That came from the 13 Oct memory note and the diagram ('water: always (DF sends none)'), and both are out of date. Since v7.6.1/v8, DF's waves of water-cast species (birds, shore animals, swimmers, fish) come in through surface entries. They are filed as water groups of their body and count toward that body's cap. V7.GRP.birdPause (seasonal-wildlife.lua:16145-16175) closes their entries at the body's cap and reopens them at cap - 2. B1 summary.md shows DF arrivals on water: ocean df 9, river df 5.
- review: Corrected what a 'waiting' DF wave is. A gated wave is already on the map with its roaming flag set, and ENGINE.count (7515-7522) already counts it. 'Releasing' it (releaseGroup 5456, detachOldest 5471) clears the flag so that source may send its next wave. So the release clock paces DF's next wave from that source, not the arrival of the one waiting.
- review: Re-attributed the ledger evidence. The B1 bursts after a reopen were mostly one DF wave counted as two groups, and the coupling. B1 ran on 987cffc, before P12. PC_SAVR day 80-81: RAT_MAN x4, then RAT_MAN x1 the next day, is one wave in pieces. Cavern 3 day 81: HUNGRY_HEAD x3, then x2, is the same pattern. Day 82: the T. rex was called by the coupling after the grasshopper (ledger lines 48-69). Under the current build (6965f34 and 6dffef5) a tail joins its wave, so the rat-men would have left the ground at 3 of 4, not 4.
- review: Added the over-cap cases the original left out. The apex scheduler (ROSTER.apex.decide, about 11800+) checks only its own apex cap (cap_calm 1, cap_savage 2, line 9113), not the place's cap or its pause. ROSTER.placeGroup has no cap check either. Irruption waves are left out of the cavern count (cavernPass 15587), and adopted natives count toward a cavern's cap. 'Nothing new arrives until cap - 2' was too absolute.
- review: Strengthened the draw-while-paused quirk with B2 data. In P2_SAVR the ground paused on Summer 74 and did not resume until Autumn 1. The tool drew groups at 3 of 4 on days 78 and 81 (ledger: 'drew CRETACEOUS_IGUANODON x5 ... (4 of 4 groups...)'), so DF's ground entries stayed closed about 11 days while draws kept the ground full. P2_COAST shows the same on days 74 and 78 and Autumn 8 and 10. The same applies to flying (flyTick 15985 checks only n >= cap) and to caverns (caveTick checks only n >= cap, after its 4-day grace).
- review: Fixed the thought-experiment table. Its rows were off by one: the gaps are computed after the 1st, 2nd and 3rd arrivals (releaseGap uses n+1, 15409). I also added the learned stay length. The prior is 28.75 days, but B1 and B2 learned 7-22 days for the ground, so a real ground fills in about 3.5-5 days, not 11. The gap floor is 0.5 days (gapFor 15389).
- review: P12 status. One wave counted as one group is built (6965f34, 6dffef5). 'Release and draw count against the cap before the wave lands' is still only a plan line (PLAN-v8.1.md:138). B2 still went over the cap at some of its 36 checkpoints: caverns 8 and 9 of 7, ocean 5 of 4 (B2/master.log).
- review: Added drain-gate extras to 'one per pass': V7.drainGate can release up to cap - n - 1 more waiting waves in the same pass. DF waves from open sources can also arrive between passes.
- review: Added the reason for the cavern cap of 7: the user ruled on 16 Oct that each of the six cast species should be able to have a group at once, with room for a thief (config comment at line 1007). This supports reading the cap as room for the cast, not a batch size.
- review: Recommendation reframed. The margin of 2 was itself the fix chosen on 13 Oct (414d494). The staged reopen in pause-not-trim.md was the alternative named that morning. I added a third tuning option: make the tool's draws respect the pause, or deliberately let them refill. I also noted that part of the question can be answered from the existing B2 ledgers without the rig.
- verifier: 'Each water body' corrected to 'each kind of water' (ocean, lake, river, ponds). All ponds share one cap and one bird pause (V7.GRP.BODIES :902; waterTick :12193).
- verifier: The apex limit is per scheduler layer, and the cavern layer covers all three caverns: 1 apex group (calm) or 2 (savage) across all caverns together (groupsOnMap(races, true) :11548). This now agrees with B3.
- verifier: Removed the reviewer's 'Correction to the earlier answer' aside. Added: DF's surface waves of water-cast species are filed under the water cast's main kind (cfg.casts.sub for fresh, ocean for sea; V7.GRP.waterBirds :15800), not the body they enter.
- verifier: Checked and kept: draws check only n < cap, not the pause (ground :17421, flyTick :15979, caveTick :15998); drainGate room = cap − n − 1; trim off under the pause switch (:17416); resumeAt :15673; gapFor formula and the table values (W 28.75 d: 2.3/3.3/5.5 days); B2 P2_SAVR ledger lines 55 and 84 (draws while paused, printed as '4 of 4' = 3 before the draw).

Code refs: /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/mechanics-diagram.html:121 (Cap definition), :191-192 (place at its cap), :216-230 (Places + caps boxes), box 3 'The tool places a group'; /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:4441-4469 (QUOTA.autoGroups, QUOTA.groupsFor); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:1007-1038 (cavern_cap=7 ruling, land_pause, cavern_pause, pause_margin=2); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:5152 (GROUPS_CADENCE 300); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:5454-5511 (releaseGroup, detachOldest, V7.drainGate room = cap - n - 1); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:7515-7522 (ENGINE.count); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:15340-15412 (ctl, observe, redraw, gapFor, dueTick, releaseGap); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:15581-15629 (V7.GRP.cavernPass; irruption outside the count at 15587); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:15640-15790 (landPause comment E8, resumeAt 15673, landResume, landPause); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:15908-16010 (V7.DRAW.pick, V7.DRAW.one, V7.DRAW.flyTick, V7.DRAW.caveTick: draws check n < cap only); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:16075 (flyPause), 16145-16175 (birdPause: water bodies' DF arrivals), 16375-16425 (cavePause), 16527-16545 (holdFor: FREQUENCY 0, vermin 1); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:17391-17455 (groupsTick ground step: pauses, trim off under pause, one release or draw); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:9113 (apex cap_calm 1, cap_savage 2) and ROSTER.apex.decide (no place-cap or pause check); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:24236-24241 (groups pause margin N verb); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/docs/pacing/PLAN-v8.1.md:75-81, 127-138 (B1 findings, P12); git 414d494 (pause margin 2, 13 Oct), 6965f34 + 6dffef5 (P12: one wave = one group); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/B1/summary.md (paused share, DF arrivals on water); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/B1/PC_SAVR/ledger.txt:48-69 (rat-man and hungry-head waves in pieces, coupling T. rex); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/B2/P2_SAVR/ledger.txt:20-28, 55, 84, 135-149 (draws at 3 of 4 while paused; reopen burst via coupling); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/B2/master.log (cavern 8-9 of 7, ocean 5 of 4 checkpoints)

</details>

## B5

> What does "into the slot with the most room" mean? Do slots have 'room'? And, what does 'slot room' have to do with the slot a seed creature is placed?

**Short answer.** Slots are seats in a cast, filled while the cast is being built, not places on the map. A role's 'room' = (seats it should have − seats filled) ÷ seats it should have. For the seed, 'the slot with the most room' never decides anything. Every role it could take is still 100% empty, so it takes the first role listed for its species: a predator seat before a flier, swimmer or shore seat. Room does real work only in growth (step 3), where it fills every role a little before any role a lot.

*Status: verified · confidence high · review verdict: minor fixes*

### Short answer
Yes, slots have room, but only while a cast is being built. Room has nothing to do with the map.

**Room of a role = (seats the role should have − seats already filled) ÷ seats the role should have.**

For the seed, "the slot with the most room" never decides anything. When the seed is placed, every role it could take is equally empty (100%). So in practice the seed takes the **first role listed for its species**: a mid-predator seat before a flier, swimmer or shore seat. Room does real work only in step 3 (growth), where it makes the roles fill evenly.

The page uses "room" for two unrelated things:
- **panel 2:** empty seats in a cast;
- **panel 9** (line 1106): space on the map under a place's cap.

Your question is about the first.

### (a) What the code does
**Slots are seats in a cast.** The table is `V7.RULES.roster.SLOTS` (seasonal-wildlife.lua:797-805):
- **Caverns:** apex, meso (mid predator), ground prey, flier, swimmer, sentient: 1 seat each.
- **Ground:** apex 1, meso 2, grazer 2, ground prey 2, sentient 1.
- **Lake:** apex 1, meso 1-2, fish 3, shore 1-2, waterbird 1-2, sentient 1.
- **Ponds** (code: `fresh:pool`) and **river:** no apex seat.

`NR.cast` (:22862) rolls each role's target `want` once per cast and starts `have` at 0. Two helpers define room:
- **`room(x)`** (:22899): the roles this species can fill that still have an empty seat. **The apex seat is never included.**
- **`frac(s)`** (:22904): `(want − have) / want`.

Room is a share, not a count. A 3-seat fish role with 1 filled has 0.67. A 2-seat meso role with 1 filled has 0.5. An untouched 1-seat cavern role has 1.0, the same as an untouched 3-seat role.

**Which roles can a species fill?** `ROSTER.FP.slotsFor` (:10198-10250) gives each candidate a list, always in the same order. Most species have only one non-apex role:
- **ground:** meso, grazer or ground prey;
- **flying layer:** flier;
- **sentients:** sentient;
- **ponds:** meso for a predator, otherwise fish.

Only two places give a real choice:
- **Caverns** (:10203-10211). The order is meso (if a predator), then ground prey, flier or swimmer. So the giant bat gets {meso, flier}, and the giant olm and giant cave toad get {meso, swimmer}.
- **Lake, river, ocean** (:10240-10244). A semiaquatic or land predator gets {meso, shore}, e.g. the alligator.

**The seed (step 2)** (:22933-22946; flying version :22948-22986):
1. The seed list is the free candidates that have room, which at this point is nearly everyone.
2. **Off the flying layer**, seeds come from the high-value set (`NR.hvSet` :22841): war-trainable species, plus the top 10% by pet value and the top 10% by size. Animal people and sentients are removed.
3. **On the flying layer**, the seed comes from the surroundings ladder: evil flier → good flier → savage with extinct species → savage flier → raptor.
4. **The species is drawn by weight** (:22877-22886): packs ×3, ×0.01 for each other cast already holding it, giants ×0.2, and so on. Room plays no part.
5. **Only then is its seat chosen** (:22944):
   `for _, y in ipairs(room(s)) do if best == nil or frac(y) > frac(best) then best = y end end`

   Only the apex seat is filled before the seed, and `room()` never offers it. So every role the seed could take has room 1.0, and with a strict `>` **the first role in its list wins**.

**Real forts** (SAVR_d1.json; LAKE3 and COAST have near-identical cavern casts, so they are not independent evidence):

| Cast | Seed | Seat taken | Same species when it joined in growth |
|---|---|---|---|
| Cavern 2, spring | giant bat | meso | flier (summer, autumn) |
| Cavern 2, autumn | giant olm | meso | swimmer (spring, summer, winter) |
| Cavern 1, autumn | giant cave toad | meso | swimmer (spring, winter) |
| Fresh, winter (SAVR, LAKE3) | alligator | meso, not shore | – |

The other 9 of 12 cavern seeds had only one choice. Every ground-layer seed took its only role.

**Growth (step 3)** is where room works (:22989-23042):
- **When some free candidates are linked on the food web**, the code:
  1. finds the largest room among the roles they can fill;
  2. keeps only the candidates that fit such a role;
  3. draws one by weight;
  4. seats it in its first role with that room.
- **When nothing is linked**, it takes the emptiest open role and fills it with any candidate that fits. If none fits, the role is closed short and recorded as unfilled (e.g. "all candidates used in other slots").

**Worked example: LAKE3, fresh cast, winter.** Targets: meso 2, fish 3, shore 2, waterbird 1, sentient 1.
1. Apex: giant alligator.
2. Seed: alligator, into meso. Meso room is 0.5; the rest are 1.0.
3. The 1.0 roles fill first: Hibbertopterus (fish), snapping turtle (shore), osprey (waterbird), mosquito man (sentient).
4. Fish (0.67) has the most room: sturgeon joins.
5. Meso and shore tie at 0.5: sea lamprey (meso), then alligator snapping turtle (shore).
6. The last fish seat goes to the carp.

The recorded order matches exactly. In growth, "most room" means **fill every role a little before any role a lot**, so no cast ends up as three fish and nothing on the shore.

### (b) What DF does
Nothing here. Slots and room exist only in the tool's cast builder. DF sees only who is in season and their FREQUENCY.

### (c) Reading and pushback
- **The page oversells step 2.** The seed cannot be steered to an under-filled role, because nothing but the apex is filled yet. The real rule is "first listed role".
- **It can cost a cast a seat.** SAVR_d1 cavern 1 in autumn has 5 of 6 members, and the swimmer seat is empty. The toad seed sat in meso, and no other free candidate could swim. Had it taken the swimmer seat, meso would have been open to another cavern-1 predator, if one was in season (unchecked; the dump has no candidate lists).
- **It quietly shuts land hunters out of cavern casts.** When a flying or swimming predator seed takes the one meso seat, a land predator such as the crundle has nowhere to go. In SAVR_d1, cavern 2 has the crundle in summer and winter only, exactly the seasons where the bat or olm did *not* seed into meso. That fits the mechanism but does not prove it.
- **How often it bites:** 3 of 12 cavern casts here, plus fresh casts seeded by an alligator-type species. Never on the ground, ponds or flying layer.
- **What the seed is for:** anchoring the food web. Its seat is a side effect, not a design choice.
- **Stale comment** at :9589-9591 describes the old v7.3 grower. The live builder is the v8 port of the Food Web Explorer's builder (65ef111).

### Recommendation
1. **Reword the page.**
   - Step 2: "Seed: one high-value species, drawn by weight; it takes the first role it can fill (a predator seat before a flier, swimmer or shore seat)."
   - Step 3: "prefer the role with the largest share of its seats still empty, so roles fill evenly."
   - Panel 9: say "space on the map", not "room".
2. **Optional code change:** seat the seed in its habitat role first (flier, swimmer or shore before meso), or in whichever of its roles leaves the most other candidates able to fit. No new cap or guard is needed. The explorer's builder must get the same change, since the two are kept line-for-line equal. The benefit is an inference I have not measured.

### What would settle it
No rig test; this is deterministic code. To size the effect, run the cast harness (MODE nrcast) or the Food Web Explorer, current rule against habitat-first, over many forts and years. Count:
- seeds with two roles;
- cavern casts with an unfilled seat;
- how often a land predator such as the crundle makes the cast.

**Rig test that would settle it:** None for the mechanism (deterministic). To size the effect: offline cast-harness (MODE nrcast) or Food Web Explorer count, current seed rule v habitat-first, over many forts/years: seeds with two roles, cavern casts with an unfilled seat, how often land predators like the crundle make the cast; rebuild SAVR cavern 1 autumn to see whether a meso candidate existed.

<details><summary>Review and verification trail</summary>

- review: Fixed the LAKE3 worked example. The first fish to join the winter fresh-water cast was DEVONIAN_HIBBERTOPTERUS_SCOULERI, not the sturgeon; the sturgeon came next (LAKE3.json fresh s3 member order). The order among roles tied at the same room is a weighted draw among food-web-linked candidates (lines 23015-23019). It is not table order and not a fixed sequence, so the trace now says that.
- review: Fixed the flying-seed description. The flying seed does not use the high-value set at all. It uses the surroundings ladder (rungs at 22966-22972, chosen from ctx.surroundings at 22973-22974). The rule 'no animal people or sentients as seed' is a filter on the seed list at 22941. NR.hvSet (22841-22860) does not exclude them.
- review: Added two weights the original answer left out: animal-person ap_pick (22883) and cavern depth 'weirdness' (22884). It already had pack x3, reuse x0.01 and giant x0.2 (22880-22882; CAST_DEF at 10339).
- review: Added that room() also requires the role to be in this layer's slot table (want[y] ~= nil, 22901), on top of excluding the apex seat.
- review: Added how often the rule actually decides anything. Most seeds have only one possible role. Every ground-layer species gets exactly one non-apex role (10220-10223). Pond species get one (10235-10238), flying species get flier only (10225-10229), and sentients get sentient only (10214-10218). Only cavern predators that fly or swim (10204-10211) and lake, river or ocean predators that are semiaquatic or land-dwelling (meso then shore, 10240-10244) have a real choice. In the real forts this was 3 of 12 cavern casts (toad cav1 autumn, giant bat cav2 spring, giant olm cav2 autumn), plus a few fresh-water seeds such as the alligator.
- review: Corrected 'same size, different mix'. In SAVR_d1 (and LAKE3/COAST), the cavern 1 autumn cast has only 5 members and an empty swimmer seat. The seed, the giant cave toad, took the meso seat, and no other free candidate could swim (growth gives up on a role only when nobody fits it: want[s] = have[s] at 23026-23028). So taking the predator seat first can cost the cast a seat. It does not only reshuffle the mix. Whether a meso candidate would have existed in that season cannot be read from the dump.
- review: Added real-fort support for the crundle knock-on. In cavern 2 the crundle sits in the meso seat in summer and winter, and is absent in spring and autumn, which are the seasons where the bat or olm seed took the meso seat. That fits the mechanism, but the dump has no candidate lists, so this is not proof.
- review: Added that the cavern food-web guarantee counts predators sitting in flier or swimmer seats as predators (isPred at 23047). Which seat the seed takes therefore never triggers or blocks the guarantee.
- review: Added a likely source of the user's confusion. The page uses 'room' for two different things: cast seats in panel 2 (lines 362 and 366) and room on the map under the place caps in panel 9 (line 1106: 'Odds only matter when there is room ... who fills an open slot'). These are unrelated.
- review: Noted that the three dumps have nearly identical cavern casts (same world and site), so they are not three independent pieces of evidence.
- verifier: Checked and kept: SLOTS table :797-805 (pond and river have no apex seat); room() leaves out the apex seat (:22899-22903); frac = (want−have)/want (:22904); the seed is picked by weight, then the seat by strict '>' over room(s) (:22933-22946); slotsFor role order, with caverns meso before flier/swimmer (:10203-10211) and water-edge predators {meso, shore} (:10240-10244); SAVR_d1 cavern1 autumn has 5 members, toad as seed, swimmer empty; cavern2 seeds bat (spring) and olm (autumn); crundle only in summer and winter.
- verifier: Added note: 'room' in panel 2 (cast seats) has nothing to do with space under a place's cap (B3/B4).

Code refs: /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:797-805 (V7.RULES.roster.SLOTS); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:22862-22868 (NR.cast: want rolled per cast, have = 0); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:22877-22886 (weight: pack, reuse, giant, ap_pick, weirdness); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:22899-22904 (room(x) excludes apex and roles not in the table; frac(s)); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:22933-22946 (seed: hv set, no sentients/animal people at 22941, pick by weight, then strict > over room(s)); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:22948-22986 (flying seed: surroundings ladder, no hv set; same seat rule at 22982); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:22989-23042 (growth: linked branch largest room, weighted draw; no-link branch; want[s]=have[s]; unfilled notes); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:23044-23066 (cavern guarantee; isPred counts flier/swimmer predators); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:22841-22860 (NR.hvSet); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:10198-10250 (ROSTER.FP.slotsFor role lists and order); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:10253-10266 (ROSTER.FP.codeFor: ML/MW/RP codes are ladder codes, not slot names); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:10339 (ROSTER.CAST_DEF); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:9589-9591 (stale v7.3 'emptiest slot first' comment); git 65ef111 (v8 Phase C: builder ported line for line from the explorer); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/mechanics-diagram.html:362,366 (panel 2 steps 2-3), :1106 (panel 9 'room' = map space); /Users/nathanielcannon/Claude/Projects/DwarfCron/.claude/scratch/pacing/ladder/SAVR_d1.json (layers.cavern1[2]: 5 members, swimmer []; cavern2 seeds bat/olm in meso; crundle only s1,s3); /Users/nathanielcannon/Claude/Projects/DwarfCron/.claude/scratch/pacing/ladder/LAKE3.json (layers.fresh[3] member order); /Users/nathanielcannon/Claude/Projects/DwarfCron/.claude/scratch/pacing/ladder/COAST.json

</details>

## B6

> What would happen if... given that "Water layer on if the map has water, unless the player set it" then what would happen if the player set it to 'on' but there is no water layer?

**Short answer.** Nothing breaks. The switch is a permission; the water body registry decides what happens. With no lake, river, pond or sea registered, no fresh or ocean cast is built, nothing is drawn, and the status reads 'water: dormant'. In practice 'everything on' sets the switch on, marked as the player's, on every new fort, so the 'on if the map has water' rule rarely decides anything. With the switch on a dry map still: (1) holds DF's water entries at 0; (2) can let water-only stocked species into the land and flying candidate lists; (3) adds a water cast at the next season if a 9+ tile open-air pond appears.

*Status: verified · confidence high · review verdict: minor fixes*

### Short answer
On a map with no surface water, setting the water switch to on does no harm. The switch is a **permission**; the water body list the tool scans decides what happens. With no lake, river, pond or sea in that list, the tool builds no fresh or ocean cast and draws nothing into water. The status line reads "water: dormant -- no open water on the surface".

This is not a rare case. On a new fort, "everything on" turns this switch on and marks it "set by the player", wet map or dry. So the rule "on if the map has water, unless the player set it" almost never gets to decide anything.

The switch does do three things beyond waiting:
1. **It takes charge of DF's water entries near the fort.** Those species rest, and their entries are held at 0.
2. **It can change the land and flying casts.** Species DF stocked only in water entries become stocked candidates for them.
3. **It catches water that appears later.** If a 9+ tile open-air pond appears, a fresh cast is added at the next season change. With the switch off, nothing happens until a reload.

### (a) What the code does
**1. The auto rule only ever turns the layer on.** `V7.WAT.autoLayer` (seasonal-wildlife.lua:8850-8865) acts only if all of these hold:
- the layer is off;
- the player has not set it;
- the map shows water: a wet map edge (`WET.get().near > 0`) or at least one sampled surface water tile.

`water layer auto` only clears the "set by the player" mark (:23850-23852); it never turns the layer off.

**2. "Everything on" marks the switch as the player's.**
- `PANEL.fortOn` sets every switch on (:20924). Water is not in the parked or left-alone lists.
- The water setter does `c.layers.water = v; c.water.layer_set = true` (:20816).
- `fortOn` runs for a new fort at map load and on `enable`. `autoLayer` then finds the layer already on and does nothing.
- Comment at :20923: "a layer with nothing on the map to manage simply stays idle".

**3. What the switch changes on a dry map:**
- **No water cast.** `ROSTER.castYear` treats a water cast as present only with an ocean body or a freshwater kind (`F.sub`) (:10829-10831). `F.sub` comes from a LAKE_ region tile or the registry's lake, river or pond counts (:9927). On EVIL the casts were ground, flying and caverns only.
- **No water draws.** `V7.waterTick` draws into a kind only `if (has[body] or 0) > 0`.
- **Cavern water is not the water layer's.** The registry types it `cavern_pool`.
- **The tool takes charge of DF's water entries.** With the switch on, fresh and ocean are "rest" layers (`castRestLayers` :10796-10803), so their species rest and the daily hold pins their entries to 0 with the extinct flag. With the switch off they are left to DF. DF sends no waves from water entries anyway (W1/E20 note :1660-1665), so on a dry map you would not notice.
- **The land and flying casts can change.** The candidate list takes water-keyed entries only when the water layer is on (`buildPool` via `enabledLayers` :1691). `FP.layersOf` can give such an entry a ground or flying layer, and `FP.candidates` prefers DF-stocked entries (:10296-10309).
  - With the switch on, a species DF stocked only on a nearby water entry (on EVIL: osprey, beaver, mink, river otter) becomes a stocked land or flying candidate.
  - None was cast in EVIL's draw, but the code allows it.
- **An extra water pass** every 300 ticks loops four empty kinds. The cost is small and has not been measured.

**4. Water that appears later.**
- The registry is rescanned every season, at load and when a cavern is found, whatever the switch says (daily job :5134-5140).
- The next `ROSTER.castAddCheck` calls `castMissingLayers`, which returns nothing `if not cfg.layers.water` (:10908).
- With the switch on, a fresh or ocean cast is grown for that layer alone. With it off, nothing happens until a load runs `autoLayer`.

### (b) What the rig shows
- **B1 PC_EVIL** (marsh + tundra, "water layer on (set by the player)", "water: dormant"): 55.6 days of spring, 0 water groups.
- **B2 P2_EVIL:**
  - registry "ocean 0, lake 0, river 0, pool 0";
  - casts without fresh or ocean, and 31 water rows all resting;
  - only Spring 15-22 before the fort was lost, so a one-week sample.
- **Not tested:** a dry fort crossing a season change.

### Scenarios
| Map | Switch on (usual) | Auto, never set |
|---|---|---|
| Dry | Idle. Water entries held. Land/flying candidates may include water-only stocked species | Layer off; water entries left to DF |
| Only puddles under 9 tiles | Idle (registry `min_tiles` 9) | Also turns on: one sampled tile is enough for auto, so it is "on with no body" too |
| Only cavern water | Idle | Same |
| Dwarves make a 9+ tile open-air pond | Next season the registry finds it and a pond-sized fresh cast is grown | Nothing until a reload |
| Roofed or underground cistern | Never registered (needs surface tiles, `V7.surfaceTile` :690) | Same |
| Frozen at first load | Lake region tile: cast built at once, draws after the thaw. River or pond only: cast after the thaw via the rescan | Stays off until a load after the thaw |
| Water gone after casts built | Fresh cast kept, draws stop; DF surface waves of its species are still filed under its kind | Same: auto never turns off |

**(c) Inference, not observed:** the region tiles include all nine `region_offset` neighbours (`getEmbarkRegions`). If a dry map's set held a LAKE_ or OCEAN_ tile, `castYear` would build a water cast with no body to draw into. That cast would use up species (×0.01 repeat weight for them elsewhere), and their DF waves would be filed against a missing body. EVIL had no such tile.

### Does it serve your aims?
**Mostly yes.** Idle costs no diversity or ecology. Arming means a fort that gains real open water gets a cast at the next season.

**What works against your aims:**
1. The rule as written ("on if the map has water, unless the player set it") does not match play. Everything-on sets it on everywhere, and the status says "set by the player" when the player never touched it.
2. One switch decides two things: whether water casts may exist, and whether land and flying candidate lists include water-only species.
3. A water cast can stay with no water.

### Recommendation
- **Fix the wording** (diagram panel 1 step 2, status line): "On for every fort the tool runs on. It draws only into ponds, lakes, rivers or sea the body registry finds, and is idle otherwise."
- **Let the registry, not the switch, decide when water casts exist.** Grow a fresh or ocean cast only when a registered body of that kind exists (or is frozen). Retire it once the body has been gone a full season.
- **Decide separately** whether DF's water-only stocked species may join land and flying casts.
- **Optional:** on a fort with no water body, hide the resting water rows and skip the extra pass.

### Rig tests (not run)
1. **Season change on a dry fort** (EVIL site), layer on. Expect a "bodies" line with 0 surface bodies, no "casts added", 0 water groups.
2. **Cast difference:** on K00_P2_EVIL, build casts with the layer on and off and compare ground and flying members.
3. **Arming:** on a dry fort with the layer on, fill an open-air 4×4 pond to 4/7+ and step past the season. Expect "bodies … pool 1", then "casts added for fresh", then "drew … into the pool". With auto/off, expect nothing until a reload.
4. **Cast with no water:** an embark whose region tiles include LAKE_/OCEAN_ but whose registry shows 0 bodies of that kind. Is a cast built?
5. **Idle cost:** the same dry save one season, layer on and off; compare FUSE `groups:engine` and `groups:water.save`.

**Readout trap:** P2_LAKE's start status also said "dormant", yet checkpoint 7 showed water:lake=2/8. Read the ledger's "bodies" line, not one "dormant" line.

**Rig test that would settle it:** Main answer needs none (code + B1 PC_EVIL 0 water groups in 55.6 d). Open: (1) dry fort past a season boundary, layer on: expect bodies line with 0 surface bodies, no casts added, 0 water groups; (2) K00_P2_EVIL casts with layer on v off, compare ground/flying members; (3) arming: dig/fill a 4x4 open-air pond to 4/7+, step past season: expect 'bodies ... pool 1', 'casts added for fresh', 'drew ... into the pool'; auto/off: nothing until reload; (4) embark with LAKE_/OCEAN_ region tile but 0 registered bodies: is a cast built?; (5) idle cost FUSE timings on v off.

<details><summary>Review and verification trail</summary>

- review: Evidence overstated: the B2 EVIL fort (P2_EVIL) ran only one game week. Its ledger runs y100 Spring 15 to Spring 22, and master.log shows 'fort LOST in chunk 5 (0 living citizens)'. Better evidence is B1 PC_EVIL, the same marsh and tundra site with 'water layer on (set by the player)' and 'water: dormant'. It ran 55.6 days with 0 water groups (B1/summary.md has no water rows for it). Neither run reached a season change.
- review: Wrong claim removed: 'the land, flying and cavern casts are the same as with the layer off'. The cavern casts are the same. The land and flying casts can differ. buildPool only adds water: entries when the water layer is on (enabledLayers, :2658; popList filter :2707-2709). FP.layersOf (:10040ff) gives a water-keyed entry the ground or flying layer if its raws fit a land biome of the fort. FP.candidates (:10296-10309) then prefers the DF-stocked entry. So with the layer on, a species DF stocked only on a water entry (EVIL: water:BIRD_OSPREY [TUN,...], water:BEAVER, water:MINK) is a stocked candidate for the land and flying casts. With the layer off, it is at most a raws-only candidate under FP.gate. In EVIL none of the 31 water rows was cast (all season=-), but the code allows it.
- review: Added what the switch actually changes on a dry map. castRestLayers (:10796-10803) puts 'fresh' and 'ocean' in the rest set whenever the switch is on. castYear (:10868-10880) then marks every water-keyed species allow=false (resting), so holdOutOfSeason (:3931-3953) pins their DF entries to 0 and flags them extinct each day. With the switch off, those entries are left to DF.
- review: Corrected 'a sealed dwarf cistern would get fish'. The body registry only starts a body on a surface tile: V7.surfaceTile (:690) means outside, or lit and not subterranean. A roofed or underground cistern is never registered. Only an open-air reservoir, moat or pond of 9 or more water tiles would get a cast.
- review: Added: `water layer auto` does not turn the layer off. It only clears layer_set (:23851-23852), and autoLayer can only switch the layer on (:8851). A dry fort set to on, then to auto, stays on, and the status line then says 'follows the map'.
- review: Added: the wet-edge test (WET.survey, :6895ff) counts water on map-edge tiles from 6 levels below the highest surface up to 1 above, open sky or not. Its result is saved once per site (saveSiteData). The auto rule is therefore not purely 'open water on the map'.
- review: Frozen-water row sharpened: the fresh cast is built at once only when a LAKE_ region tile is in the region set (FP.fort, :9840-9846 and F.sub, :9926). A frozen river or pond has no region tile. With the layer on, it gets its fresh cast only after the thaw, through the seasonal rescan and castAddCheck.
- review: Verified as written: autoLayer's conditions; fortOn setting every switch, including water, with layer_set=true (the PARKED/ENABLE_LEAVES lists at :1333/:1337 do not hold water); map_loaded runs fortOn on a new fort; castYear's presence test; waterTick's has[body] gate; spillCheck stands down under casts; castMissingLayers needs the switch on; the registry rescans every season whatever the switch (daily job :5135-5140); commit dates 941c348 (1 Oct) and 2a2410d (7 Oct); the diagram text at panel 1 step 2.
- review: Rig tests revised: dry-fort runs so far never crossed a season boundary; added a cast comparison with the layer on and off on the EVIL save.
- verifier: Checked and kept: autoLayer only ever turns the layer on (:8850-8865); the water switch setter sets layer_set (:20816); fortOn sets every switch on except parked/left-alone (:20924); 'water layer auto' never turns the layer off (:23850-23852); castYear needs F.sub or ocean bodies (:10829-10831); castRestLayers includes fresh/ocean when the switch is on (:10796-10803); castMissingLayers returns nothing without layers.water (:10906-10912); the daily job rescans the registry and runs castAddCheck whatever the switch (:5134-5140); buildPool takes water entries only with the water layer enabled (enabledLayers :1691); DF sends no water-entry waves (W1/E20 note :1660-1665).

Code refs: /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:8850-8865 (V7.WAT.autoLayer); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:6895-6992 (WET.survey edge band surf-6..surf+1, saved per site; WET.get); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:20816 (water switch setter sets layer_set); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:20908-20944 (PANEL.fortOn, every switch on); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:1333,1337 (PARKED_SWITCHES, ENABLE_LEAVES: water not listed); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:21284-21291 (map_loaded -> fortOn on a new fort); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:23847-23860 (water layer auto never turns the layer off); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:2655-2709 (buildPool: water: entries only with the water layer on); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:10040-10070 (FP.layersOf: water-keyed entry gets ground/flying from land biomes); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:10296-10309 (FP.candidates prefers the stocked entry); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:9830-9926 (FP.fort: F.sub from LAKE region tile or registry counts); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:10796-10803 (castRestLayers includes fresh/ocean when the switch is on); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:10826-10834,10866-10880 (castYear presence; resting allow=false); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:3931-3953 (holdOutOfSeason pins resting entries to 0 + extinct); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:10906-10912,11016-11028 (castMissingLayers needs layers.water; castAddCheck); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:5135-5140 (daily: registry rescan + cast-add check, whatever the switch); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:8209-8215 (V7.WB.swap sets castAddDue); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:690 (V7.surfaceTile: outside, or lit and not subterranean); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:8124-8135 (registry min_tiles, byType); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:12177-12248 (V7.waterTick has[body] gate); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:17262-17285 (V7.PASS.waterLater / V7.PASS.water); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:8898-8901 (spillCheck stands down under casts); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:1583-1640 (getEmbarkRegions: all nine region_offset neighbours); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:1660-1665 (DF sends no water-entry waves; fishing reads water vermin entries); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:15784-15796 (option A filing of water-cast species' surface waves); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/B2/P2_EVIL/status-start.txt; /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/B2/P2_EVIL/ledger.txt (y100 Spring 15-22 only); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/B2/master.log (P2_EVIL fort LOST in chunk 5; P2_LAKE water:lake=2/8 at checkpoint 7); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/B1/summary.md (PC_EVIL 55.6 d, no water rows); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/B1/PC_EVIL/status-start.txt; /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/mechanics-diagram.html:287

</details>

# C. The FREQUENCY ladder and odds

*how FREQUENCY odds are computed and used, family weights, size factor, per-year vs per-season ladders, apex off-ladder, and the real odds on Fort 1*

### What these six questions are really asking
Taken together, the questions ask: **is the FREQUENCY ladder the right control for how often each species arrives, and if so, how should it be shaped?** The options raised are:
- even odds;
- no size factor;
- different family weights;
- one ladder per season;
- apexes on the ladder.

Behind this sit your aims: seasonal casts that look natural (prey outnumber predators every season, not just over the year), every cast member seen, and the tool rather than DF's quirks deciding the outcome.

### The common finding (from the code, sw-wt 6dffef5)
In v8.1 the ladder is the main control **only for the water draw**. Elsewhere other mechanisms decide:
- **Ground and flying:** mostly the tool's draw (`V7.DRAW.pick`, `scripts/seasonal-wildlife.lua:15908-15943`). It takes the member with the fewest *animals* seen this season first (`V7.TALLY.note`, 11269), and the ladder only breaks ties. DF's remaining waves pick among absent species only, because one group per species is on. B1, where DF alone picked, showed arrivals barely tracking FREQUENCY: the giant skink at 1 came 5 times in summer, the coyote at 1 came 2 times in 12 spring waves.
- **Caverns:** DF's pick appears to follow stock more than FREQUENCY (PENDING). The tool's cavern draw is **broken in this build**. `V7.DRAW.members` strips `cavern:` from keys (15889), so `ROSTER.apex.entries` never finds a cave entry. B2 had 0 cavern draws on all four forts.

### What each answer adds
- **C4 (per-season ladder):** a real fix for the prey/predator split, per cast. Mean miss against the pyramid drops from 15 to 6 points. The biomass guard needs a decision first.
- **C3 (drop the size factor):** cleaner design; slot-mates get equal animals. Little change in play on land and flying.
- **C2 (family weights):** mostly cancel within a level. Clean the dead keys, add RP to water, and sort animal people into prey or predator by their guild.
- **C1 and C5:** argue against even odds and against apexes on the ladder.
- **C6:** shows the draw yields about 70% "neither weasel nor colepio" on Fort 1. Good for diversity, but it roughly quadruples the ladder's intended predator share.

### Combined recommendation, in order
1. **Fix the cavern draw key bug.** Without it, cavern odds and the P9 draw do nothing.
2. **Decide the draw's pick rule. This is the real lever for seasonal balance on ground and flying.** Options:
   - count the tally in groups, or make least-seen a soft weight (odds ÷ (1 + seen));
   - pick the level furthest below the pyramid first (the water mix's pyramid factor already does this).

   Also decide which aim wins when "every member seen" and "about 20% predators" collide under a cap of 4.
3. **If FREQUENCY keeps a role (DF's waves, water):**
   - build it per cast (C4);
   - drop or soften the size factor (C3);
   - set flying LB/WB to 6, remove dead keys, add water RP, and sort animal people by guild (C2);
   - do not flatten it outright (C1).
4. **Keep apexes off the ladder.** Move them into the draw under the layer cap and pause, with a presence-aware limit like water's `apex_max` (C5). Keep the scheduler for invasives, thieves and the stock-poor cavern apexes until the cavern draw works.
5. **Fix the page.** Panel 2 says \"most decides\", and panel 2b step 5 says \"per season\" where the code uses the whole year. Panel 2b should also say least-seen counts animals.

**First evidence step, with no rig cost:** score B1 (DF only) against B2 (draw) on the same tiles, counting waves by arrival per species against FREQUENCY. **Then the decisive rig test:** a surface pick A/B with one entry per species on the anchor tile (FREQUENCY 100 against 5, swapped, one_per_species on and off), together with the pending cavern stock-against-FREQUENCY A/B (pickab).

<details><summary>Cross-answer issues the verifier resolved</summary>

- Cavern draw (C1, C3 against C4): C1 and C3 say the tool draws cavern groups after 4 days without a DF wave (P9). C4 says that path is broken, and the code agrees. `V7.DRAW.members` (seasonal-wildlife.lua:15889) strips 'cavern:' from cast keys. `ROSTER.apex.entries` then looks up the bare token, but `CACHE.managedPops` files every cave entry under 'cavern:TOKEN' (`keyFor`, 1687; 3670). So no cave entry is ever found and the draw returns 'no stocked cavern N entry'. The rig agrees: there were 0 cavern draws across all four B2 forts (probe src counts: SAVR df 178/place 3, COAST df 154/place 1, LAKE df 113, EVIL df 25), and P2_COAST cavern 3 sat at 0 groups for 81 probes, 'waits on DF's next wave'. Resolved: the cavern draw is dead in 6dffef5. C1 and C3 are corrected. For the same reason, cavern odds and cavern apex exclusion never reach the draw.
- Giant coyote in B1 Fort 1 spring (C1 '3 days' against C3/C6 '2'): the probe shows DF arrivals at ticks 40338331, 40406131 and 40406431. The last two are 300 ticks apart but fall either side of a day boundary. Resolved: 2 waves, or 3 if counted by calendar day. Either way it is far above its 1% ladder share.
- Do family weights 'rule' flying? (C3 says yes, birds 30 against raptors 2; C2 says they cancel). `ROSTER.ladder` (9382-9443) divides each level's pyramid share among the members of that level only. Every flying prey member is LB at 30 and every predator is RP at 2 (animal people read their guild), so the 30 and the 2 cancel and the pyramid's 80:20 decides. Resolved in C2's favour; C3 corrected.
- Ground against flying in DF's surface pick (C4 point 4: the split between the two ladders is arbitrary because each is scaled to 100 separately). RESEARCH-NOTES.md:274 says fliers draw from their own list. B1 Fort 1 agrees: flying was about 41% of spring surface arrival days and 40% of autumn's, where the yearly FREQUENCY would give 20% and 3%. Resolved: the cross-ladder scale probably does not set the ground/flying split. C4 corrected (uncertain, rig-checkable).
- 'The whole cast comes round before a member repeats' (code comment at 15880; C4) against 'the draw evens out animal numbers' (C1, C6). Both hold. `V7.DRAW.pick` (15908-15943) takes the lowest season tally, and `V7.TALLY.note` (11269) counts animals by unit id, DF-wave animals included. The first round brings everyone once. After that, solitary species come back before herds or packs. C4 gets that nuance added.
- 'Coyote at odds 1 would almost never come from DF waves' (C6) contradicts B1, where DF sent it 2 times in 12 spring waves. C6 corrected. All answers agree that B1 shows DF's surface waves on this fort do not track the ladder (giant skink at 1 arrived 5 times in summer).
- Pyramid per season (panel 2b step 5; the V7.rosterDefaults comment at 9081) against the code: `ROSTER.castLadder` (11034-11089) builds one ladder per partition from all four seasons. C2 and C4 agree and both are right; the page's wording is wrong.
- Apex-on-ladder numbers: C2 option 1 and C5 give the same figures (land: T. rex 5, tick 12, recluse 12, scorpion 28; caverns: cave bear and giant cave spider 57, molemarian 52, pond grabber 32, jabberer and cave dragon 8). Consistent.

</details>

## C1

> What would happen if... we simply evened out the frequencies for all species? Since "FREQUENCY ladder (per layer) written into the raws: DF's odds" means that we rely on the DF odds, would we be able to instead just overwrite and apply our own odds? What would happen?

**Short answer.** Yes, the tool already overwrites every in-season cast member's FREQUENCY daily, so it could write even odds tomorrow. But in v8.1 the ladder decides little on ground and flying: the draw picks the member with the fewest animals seen; one-group-per-species takes present species out of DF's pick; and the caverns seem to follow stock, with the cavern draw itself currently broken. Evening odds would mostly change the water draw. The real control lever is the draw's pick rule, not FREQUENCY.

*Status: corrected · confidence medium · review verdict: major fixes*

### Short answer
**Can we write our own odds?** Yes, and the tool already does. `CAVERN.apply` (`scripts/seasonal-wildlife.lua:4645-4700`, sw-wt v8.1-pacing @ 6dffef5) writes every in-season cast member's ladder number into its raw FREQUENCY at each season turn and every day. That includes land members. When two layers want different values for the same raw, the higher wins (`math.max`, 4658). `CAVERN.restoreAll` puts the originals back on switch-off.

What the tool cannot change is how DF *uses* FREQUENCY. Its levers on DF are only:
- FREQUENCY;
- stock;
- which entries are open;
- which tile an entry sits on.

Otherwise it places the group itself (the draw).

**Would evening it out matter?** Much less than panel 2b suggests. In v8.1 three things take most of the choice away from the ladder:
1. **The tool's draw** (`V7.DRAW.pick`, 15908-15943) places most ground and flying groups. It takes the cast member with the **fewest animals seen this season** first; the ladder only breaks ties.
2. **One group per species** (`V7.GRP.speciesPause`, 16196+, default on at 1028) closes DF's surface entries for species already on the map. DF picks only among the absent members.
3. **Caverns:** DF's pick seems to follow stock more than FREQUENCY (memory cavern-pick-stock-weighted, PENDING).

### (a) What the code does
- **The ladder is built once a year.** `ROSTER.castLadder` (11034-11089) runs one ladder per partition (land, flying, water, cavern) over all four seasons' members and stores it in `cfg.odds` (11076). It runs only at a cast build (10893, 11007). A manual `odds KEY N` (verb near 24513) writes `cfg.odds` directly, so the next build overwrites it.
- **Inside `ROSTER.ladder` (9382-9475):**
  - family weight;
  - size factor (×0.25-4);
  - pyramid split between prey and predators;
  - biomass guard;
  - divide by mean group size;
  - scale so the top member is 100, floor 1.
  - Apexes are set aside and keep their raw FREQUENCY capped at 5 (9444-9461).

| Layer | Who chooses | Does FREQUENCY count? |
|---|---|---|
| Ground, flying: DF waves | DF, among open entries; present species closed | Yes, but only among absent members |
| Ground, flying: tool draw | `V7.DRAW.pick`: lowest season tally first, odds as the weight among ties | Only for ties (the first round, equal counts) |
| Water | Tool draw: base weight = live FREQUENCY (`ENGINE.weight`, 7399), × balance (want = share of base weights), × pyramid factor ((target+1)/(have+1))^0.5 clamped 0.25-4, × pull/feed, then one group per species (`V7.WAT.mix`, 7806-7860) | **Yes, directly** |
| Caverns | DF waves. The P9 cavern draw (`V7.DRAW.caveTick`, 15997) is meant to step in after 4 quiet days, but **it never places anything in this build**: `V7.DRAW.members` strips `cavern:` from the keys (15889), so `ROSTER.apex.entries` never finds a cave entry, because cave entries are filed as `cavern:TOKEN` (`keyFor`, 1687; `CACHE.managedPops`). B2 had **0 cavern draws on all four forts**, and P2_COAST cavern 3 sat empty for 81 probes. | Apparently little; see (b) |

**The tally counts animals, not groups.** `V7.TALLY.note` (11269) counts every wild unit on the map once a season by id, DF-wave animals included. A coyote pack of 9 counts 9, so it waits until the others catch up; a lone black bear counts 1, so it comes back often. In B2 summer on Fort 1 the black bear was drawn 5 times and the iguanodon (a herd) twice. So after the first round **the draw evens out animal numbers per species.** The prey/predator mix then follows how many prey and predator species the cast holds, not the ladder.

### (b) What DF does, with evidence
- **Surface, controlled test:** FREQUENCY weights DF's pick in proportion (X3/ECO F1, RESEARCH-NOTES.md:273). The pick is made per entry, so tiles weigh in too (TR2, memory df-wave-pick-per-entry), and it ignores stock (E3).
- **On a real fort it does not show.** B1 Fort 1 (987cffc, no tool draw; same tile and casts as the ladder dump) had only DF arrivals. Spring ground:

  | Member (ladder) | DF waves |
  |---|---|
  | giant weasel (44) | 3 |
  | giant brown recluse, apex (5) | 3 |
  | giant coyote (1) | 2 (3 by calendar day; one wave split across a day boundary) |
  | rattlesnake (9) | 2 |
  | colepiocephale (30) | 1 |
  | triceratops man (4) | 1 |
  | giant slug (8), platybelodon (3) | 0 |

  - Animals came out at about 36% prey / 50% predators / 14% apex, against a land target of 73/20/7.
  - In summer the giant skink (ladder 1) arrived on 5 days. In summer flying, bat man (1) came on 5 days against swan (50) on 3.
  - One cause is that one-group-per-species takes the high-ladder members out while they are on the map (inference). Tiles may also play a part: entry tiles were not logged.
- **Caverns:** flesh ball (stock 395, FREQUENCY 10) took 54% of cavern 3 in B1 (memory cavern-pick-stock-weighted; the A/B came out 4 of 5, still PENDING).
- **Who placed what in B2:**

  | Fort | Ground | Flying | Caverns |
  |---|---|---|---|
  | Savage marsh | mostly draws (about 30 draws / 18 DF) | about 34 draws / 18 DF | 178 DF, 3 scheduler placements, 0 draws |

### (c) Thought experiment: Fort 1 spring ground cast
Ladder: weasel 44, colepio 30 (herd about 4), rattlesnake 9, slug 8, triceratops man 4, platybelodon 3, coyote 1 (pack about 6), recluse apex 5. Script: `DwarfCron/.claude/scratch/sw-questions/c1_even.py`.

This is the **upper bound**, assuming DF picks among all members every time:

| | Current ladder | Non-apex all equal |
|---|---|---|
| Weasel / coyote share of waves | 42% / 1% | 14% / 14% |
| Animals: prey / predators / apex | 87 / 11 / 2 | 55 / 45 / 0 |
| Animals per wave | 2.07 | 2.83 |
| Members seen in 6 waves (of 7) | 3.1 | 4.2 |

What actually happened: B1 (DF only) 36/50/14; B2 (mostly the draw) about 46/50/4, with all 8 members seen. The ladder's prey protection already leaks away, and the draw replaces it with "even animals per species".

**Evening FREQUENCY would therefore:**
- **Land and flying:** shift DF's leftover picks somewhat toward pack predators and change the draw's first-round order. The end-of-season mix is already about what evening would give.
- **Caverns:** probably little while stock drives the pick (`cave_open_stock` 30 already evens stock). An even positive FREQUENCY cannot cause the zero-frequency freeze, and `V7.GRP.keepAlive` (16616) guards it anyway.
- **Water: the real change.** The balance target becomes equal groups per species. The pyramid factor still pulls toward the level split, and large ocean animals keep their size discount.
- **Apexes:** do not even them. At an equal value an apex would take about 1 in 8 of DF's leftover picks on top of the scheduler, and under pause-not-trim nothing could send the extras away.
- **Diversity:** a small gain only. Fully even odds topped out near 70% coverage (memory cast-coverage-drivers), and the draw already brings every member round.

### Does it serve your aims?
- **Diversity:** slightly; the draw already delivers it.
- **Ecology:** no, and neither does today's ladder on the surface. Predators are about half the ground animals in both B1 and B2.
- **"The tool controls outcomes":** control is split three ways (the ladder for water and DF's leftovers, fewest-animals-seen for the draw, stock for the caverns). Evening FREQUENCY does not join them up.

**A hard limit to face first.** B2 spring had about 26 ground animals, and one giant coyote pack (9) was 35% of them. With 3 predator species among 7 cast members, "every member seen each season" and "20% predators by animals" cannot both hold at today's arrival rate under a cap of 4 groups. You choose which wins. Otherwise the lever is the slot table (fewer predator slots per season), not FREQUENCY.

### Recommendation
1. **Fix the cavern draw key bug** (bare key against `cavern:` key) before judging any cavern odds.
2. **Let the draw own the prey/predator choice.** Pick the level (prey or predator) furthest below the season's pyramid from the tally's animal counts, then keep fewest-seen-first within it. This reuses the water mix's pyramid factor (`V7.WAT.mix`); it tunes existing code and adds no new cap.
3. **Leave FREQUENCY alone until the A/B below.** If DF's surface pick follows FREQUENCY among the open members, keep the ladder. If not, flatten it for simplicity. Decide water separately: there evening is a real design change.
4. **Keep apexes off the ladder** (see C5).
5. **Fix panel 2.** It says the ladder "most decides"; in v8.1 that is true only for water.

### Rig test that would settle it (not run)
**Desk step first, at no rig cost:** score B1 (DF only) against B2 (draw) on the same tile, counting waves by arrival.

**Then a same-tile A/B on new embarks:** region6 24,11 (savage marsh) and 29,42 (coast). Casts are seeded by site and year, so both arms get the same casts.
- **Setup:** 50 dwarves, caverns 1-3 breached, one season, probe every 2 days, n=5 per arm.
- **Arm A:** current ladder.
- **Arm B:** every in-season non-apex member at FREQUENCY 100.
- **Optional Arm C:** `groups draw off`, to see DF's pick alone.

**At each DF surface wave, log** which members' entries were open and each entry's tile. Then compare shares against FREQUENCY ÷ the total of the **open** members.

**Measure:**
- prey / predator / apex animals against the pyramid;
- cast coverage;
- water shares;
- DF wave rate;
- kills and losses;
- cavern shares under even stock.

**Rig test that would settle it:** Same-tile A/B on new embarks, region6 24,11 and 29,42; casts are seeded by site and year, so both arms get the same casts. Setup: 50 dwarves, caverns breached, one season, n=5 per arm. Arm A: current ladder. Arm B: all in-season non-apex members at FREQUENCY 100. Optional Arm C: groups draw off. At each DF surface wave log the open entries and their tiles, then compare shares to FREQUENCY over the open members. Measure prey/predator/apex animals, coverage, water shares, DF wave rate and kills. Fix the cavern-draw key bug first. Do the desk score of B1 against B2 before any rig time.

<details><summary>Review and verification trail</summary>

- review: Corrected how the tool's own draw works. Its 'least seen first' counts ANIMALS, not turns. V7.TALLY.note (seasonal-wildlife.lua:11269-11296) counts every wild unit on the map by unit id and creature token, DF-wave animals included, and V7.DRAW.pick (:15915-15926) reads that count. So the draw evens animals per species: pack and herd species get fewer turns and solitary species get more. B2 summer shows it: black bear x1 was drawn 5 times ('seen 4 times this season before', ledger line 83), while iguanodon x4-5 was drawn twice. The reviewed answer said packs 'get as many waves as solitary weasels'. That is true only for DF's waves at even FREQUENCY.
- review: Added a mechanism the reviewed answer missed: one group per species (V7.GRP.speciesPause, :16196-16310, default on at :1028). It closes DF's surface entries for any species that already has a group on the map. DF therefore picks only among cast members that are absent. 'FREQUENCY divided by the season total' (weasel 42%, coyote 1%) overstates the ladder's effect. The reviewed answer's table is an upper bound, not 'now'.
- review: Added direct evidence that the ladder is not holding the pyramid even when DF picks every arrival. B1 PC_SAVR (same tile, same casts, ladder in force, ground arrivals all DF waves). Spring ground arrival days: giant weasel (ladder 44) 3, giant coyote (ladder 1) 3, brown recluse apex (5) 3, rattlesnake 2, colepiocephale 1, triceratops man 1, slug 0, platybelodon 0. Animals were 36% prey, 50% predators, 14% apex. The reviewed answer predicted 87/11/2. In summer, giant skink (ladder 1) came on 5 days.
- review: Reframed the effect by layer. On land and flying, evening changes little: DF picks only among absent species, and the draw corrects toward even animals anyway. In the caverns, the pick looks stock-driven. The layer where FREQUENCY really enters the tool's own choice is water. ENGINE.weight (:7397-7411) uses the live raw FREQUENCY as the base weight, and V7.WAT.mix's balance target is each species' share of those base weights (:7809-7814). In the draw, the ladder also sets the order of the first round (everyone at 0 seen) and breaks ties (:15925-15933).
- review: Corrected the load estimate. The +37% animals per group applies only to DF-wave groups, which were 18 of 48 ground groups on the savage marsh and 12 of 50 on the coast in B2. That is roughly +10-15% overall (inference), not +30%.
- review: Cut most of the off-cast leak argument. B2 shows about 1 DF off-cast surface group per fort (WREN_MAN on the savage marsh; BIRD_RAVEN on the coast in autumn). B1's '5 of 49' includes giant coyote, which was in the spring cast, so it is likely a season-boundary carryover.
- review: Added a feasibility check on the pyramid itself. Spring B2 ground had about 26 animals. One giant coyote pack (9) is already 35% of them. 'Every cast member every season' and '20% predators by animals' cannot both hold for this cast at this arrival rate. The choice is the user's, or the slot tables are the lever.
- review: Softened the recommendation. Evening FREQUENCY is no longer step 3 of the fix. First make the draw level-aware by reusing the water mix's pyramid factor, which is existing code (fits the 16 Oct 'tune what exists' ruling). Then decide FREQUENCY from the A/B: keep the ladder if DF's surface pick follows it among open members, flatten it if not.
- review: Noted that the page overstates the ladder. Panel 2 (mechanics-diagram.html:381) says the ladder 'is the step that most decides how often each species shows up'. In v8.1 that is no longer true for land, flying or caverns.
- review: Kept the parts that check out against the code. Daily write in CAVERN.apply, higher-wins at :4658, restore at :4593. castLadder writes cfg.odds yearly (:11076), so the odds command is overwritten at the next build. Apex FREQUENCY is capped at 5 (:9444-9462). The arithmetic in c1_even.py (87/11/2 to 55/45/0; 2.07 to 2.83 animals per wave) is right for 'every member open'. The B2 source counts (SAVR ground 30 draws / 18 DF waves, flying 34/18, caverns 178 of 181 DF; coast 38/12 and 18/29) are right. B2 cavern 3 spring (Manera 4 of 20 groups at ladder 87, cave floater 7 at 37) is right.
- verifier: The cavern draw (P9) never fires in 6dffef5. V7.DRAW.members strips 'cavern:' (15889), so ROSTER.apex.entries finds no cave entry (managedPops keys are 'cavern:TOKEN'). There were 0 cavern draws across all four B2 forts. The table row 'tool draws after 4 days' is corrected.
- verifier: B1 giant coyote spring: 2 DF waves (3 by calendar day, because one wave split across a day boundary 300 ticks apart). It is not 3 waves.
- verifier: Added: B1 flying arrivals also ignore the ladder, which strengthens the conclusion.

Code refs: /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:9374 (ROSTER.LADDER22); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:9382-9470 (ROSTER.ladder; apex cap 9444-9462); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:9076-9090 (V7.rosterDefaults: units, apex_raw_cap 5, pyramid targets); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:11034-11086 (ROSTER.castLadder, cfg.odds write 11076; called at 10893/11007 on cast build); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:4580-4600 (CAVERN.write, CAVERN.restoreAll); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:4645-4700 (CAVERN.apply daily write, higher-wins 4658, keepAlive call); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:11261-11296 (V7.TALLY.note: counts every wild unit by id/token, DF waves included); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:15871-15940 (V7.DRAW comment and V7.DRAW.pick: least-seen by tally, odds only among ties 15925-15933); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:15997-16030 (V7.DRAW.caveTick, 4-day grace); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:16196-16310 (V7.GRP.speciesPause: a species on the map has its DF surface entries closed); :1028 one_per_species default on; /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:7397-7411 (ENGINE.weight reads live craw.frequency); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:7790-7860 (V7.WAT.mix balance/pyramid/feed/pull; defaults :956, :961); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:16520-16540 (V7.GRP.holdLevel/holdFor); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:16616 (V7.GRP.keepAlive); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:3240-3253 (V7.SRC single source: anchor tile, else site tile, else biggest); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:24513-24540 (odds KEY N command); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/STATE.md:3874 (X3: surface pick follows FREQUENCY); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/RESEARCH-NOTES.md:268-276 (surface pick ignores stock E3; FREQUENCY weights pick X3/ECO F1); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/docs/pacing/PLAN-v8.1.md:20-60, 98-140 (P3, unified draw design, P10 stock finding); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/B1/PC_SAVR/probe.jsonl (DF-only spring/summer ground arrivals v ladder); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/B1/summary.md:49-67; /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/B2/P2_SAVR/probe.jsonl and ledger.txt:82-84 (draw counts, black bear drawn 5th time); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/B2/P2_COAST/probe.jsonl; /Users/nathanielcannon/Claude/Projects/DwarfCron/.claude/scratch/pacing/ladder/SAVR_d1.json (via summarise.py: Fort 1 ladders, whole-year); /Users/nathanielcannon/Claude/Projects/DwarfCron/.claude/scratch/sw-questions/c1_even.py; /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/mechanics-diagram.html:173, 381 (panel 2/2b wording)

</details>

## C2

> What would happen if... "Family weight by slot: how common that kind of animal should be" which is '30' for LB land bird and for WB waterbird in the 'flying' ladder was set to about the same value as LB and WB in the 'land' ladder? Also, why do we have LB, WB, and RP weights in the 'land' ladder? Why do we have WB in land, flying, water and cavern? And what would happen if Apex was added to the ladders, hypothetically given a '2', and the ML/MW predators were bumped up to '4'?

**Short answer.** Flying LB/WB from 30 down to 6 changes nothing for today's casts, because all flying prey are LB and the weight cancels inside its level. It matters only for bird men, and there it helps. The land LB/WB/RP keys and flying WB are leftovers from the v7.0/v2.2 rosters before the flying layer and your 9 Oct slot tables; WB does real work only on the water ladder, which is missing an RP key. Putting apexes on the ladder at '2' does nothing as written. ML/MW at 4 moves weight inside the predator level only, and mostly inflates the gremlin.

*Status: verified · confidence high · review verdict: major fixes*

### How a family weight is used (code: `scripts/seasonal-wildlife.lua`, sw-wt 6dffef5)
`ROSTER.ladder` (9382-9475) runs once per partition per year (land, flying, water, cavern):
1. **Apexes are set aside first** (APX/APE/AL/AW; 9389-9391). They never read a family weight. They get their raw FREQUENCY capped at 5, or `roster.apex_odds` if that is set (9444-9461).
2. **Family weight:** `fam[guild]` for animal people (SN), otherwise `fam[code]`. **Any missing key falls back to 5** (9400).
3. **Size factor:** (mass ÷ the slot's geometric mean)^-0.75, clamped ×0.25-4.
4. **Level split.** Each level's total comes from the **pyramid**, not from the weights: land 73:20, flying 80:20, lake 87:13, ocean 82:13, caverns 60:27. These are normalised, so the real predator targets are 21.5%, 20%, 13%, 13.7% and 31%. On land and in the caverns a biomass guard can trim the predator share.
5. Divide by mean group size.
6. Scale so the top member is 100, floor 1.

**So a family weight only matters against other members of the same level on the same ladder.** The weights are a hard-coded table (`ROSTER.LADDER22`, 9374-9379), so changing one is a code edit.

**The page is wrong on one point.** `castLadder` (11034-11089) pools all four seasons, so the 80:20 is a whole-year target, not a per-season one as panel 2b step 5 says. On Fort 1 the flying prey share of FREQUENCY by season is:

| spring | summer | autumn | winter |
|---|---|---|---|
| 7% | 88% | 0% | 78% |

Autumn is 0% because that season's cast drew raptors into both flier slots (giant mantis and buzzard, plus fly man and the giant buzzard apex). No weight can fix that.

### Which code a cast member gets
`ROSTER.FP.codeFor` (10253-10266) applied to your slot tables (797-805):
- **Ground:** apex, meso, grazer, ground prey, sentient become APX, ML, GZ, PL, SN.
- **Flying:** a flier becomes **RP if it hunts, LB otherwise; never WB.**
- **Water:** the waterbird slot becomes WB or RP; fish become FC or FF; plus shore (SH) and pelagic (PE).
- **Caverns:** a flier becomes LB or RP; a swimmer becomes FF or MW.
- **Every layer:** a sentient is SN and reads its guild (`MODEL.guild`, 2264-2290).
- A species cast on two layers is laddered in the first partition met, in the order ground, flying, ocean, fresh, caverns.

### Q1: flying LB/WB from 30 down to land's 6
**For today's casts, no written FREQUENCY changes.**
- Fort 1's flying prey are duck, swan and giant sparrow, all LB. The coast fort's are raven and kea, also LB. The 30 cancels out.
- Re-running the ladder with 6 gives the same values: Fort 1 duck 100, swan 50, barn owl 21, kestrel 21, giant sparrow 2, giant kestrel 1.

**The one live case is bird men.** Animal people keep FLIER, and raven, swan, loon, albatross and puffin men have no CARNIVORE tag, so their guild is LB or WB. They then read 30 *inside the predator level*, against raptors at 2.
- Swapping Fort 1's mantis man for an LB-guild bird man: at 30 the bird man gets 21 and the owl and kestrel fall to 11; at 6 the bird man gets 7 and the owl and kestrel get 18.
- So 30 to 6 only matters on forts with bird men, and there it helps.

**Where the 30 came from:** the desk's v2.2 ladder (`DwarfCron/data/eco-desk/v2/guilds/roster2.py:113-118`). That ladder had **no levels**, and 30 was where the search stopped, not a value it settled on. The pyramid's levels now do the 30's old job, so it is a leftover.

### Q2/Q3: why LB/WB/RP are on the land ladder, and WB on all four
They are history:
- Land LB/WB/RP are v7.0's land ladder (11531-11536), from when birds were on land.
- Flying WB is the v7.1 waterbird slot (roster.md R50).
- Cavern LB/WB are the desk's cavern birds.

Your 9 Oct redesign moved birds into the flying slots (LB/RP only), but the old keys were never removed.

| ladder | keys that do work | dead keys, or reached only by an animal person's guild |
|---|---|---|
| land | GZ, PL, ML, SN | LB, WB, RP, MW; SH (animal people only) |
| flying | LB, RP, SN | WB (WB-guild bird men only); ML (dead) |
| water | FC, FF, SH, WB, PE, MW, ML | GZ, PL (animal people). **RP is missing**, so ospreys read the default 5 (osprey family 5 in the Fort 1 dump), as do RP-guild animal people |
| cavern | PL, LB, FF, ML, MW, RP | SH, GZ, WB (animal people: plump helmet man reads SH 8, manera PL 10) |

**The default 5 also hits predator-guild animal people with an AL guild.** Dingo man reads 5 in the dump, 2.5× real mid predators at 2.

Water is where the ladder matters most, because it is the base weight of the tool's water draw (`ENGINE.weight`, 7399; `V7.WAT.mix`). So the missing RP key has a direct effect there.

### Q4: ML/MW to 4, and apex at "2"
**ML/MW 2 → 4.** The predator level's whole-year total is fixed by the pyramid, so the predators' share does not grow. Weight shifts *inside* the predator level, toward ML/MW members, ML-guild animal people included. Fort 1, re-run with guilds:

| what | today | ML/MW = 4 |
|---|---|---|
| weasel, adder | 23 | 30 |
| rattlesnake | 9 | 12 |
| pachycephalosaurus man (GZ guild) | 13 | 9 |
| dingo man (AL, reads 5) | 7 | 4 |
| land predator share by season | 13 / 30 / 30 / 16% | 14 / 38 / 34 / 12% |
| **gremlin** (ML guild, small so ×4 size) | **58** | **90**, second only to the giant rat |
| helmet snake | 24 | 37 |
| manera | 87 | 67 |
| osprey (Fort 1 river) | 30 | 25 |
| dimetrodon (Fort 1 river) | 5 | 8 |

**Apex at "2".** Adding `APX = 2` to the table does nothing, because apexes are set aside before weights are read. To make it mean something you must pick one of three readings:
1. **Apexes as their own level at the pyramid's A share** (land 7, caverns 13, lake 3, ocean 5, flying 0). The 2 cancels inside the level.
   - Fort 1 land: T. rex 5, tick 12, recluse 12, scorpion 28. Apex share of each season's FREQUENCY goes from 0-5% to 11-13%.
   - Caverns: cave bear and giant cave spider 57, molemarian 52, pond grabber 32, jabberer and cave dragon 8.
   - Flying apexes would fall to 1, because the flying A share is 0.
2. **Apexes inside the predator level at 2.** The result swings with the cast: on the coast's flying ladder the peregrine gets 57 and the great horned owl 37.
3. **Literally 2:** `roster.apex_odds 2` already exists (9079, 9458). It would *lower* apexes from 5.

### What DF and the rig say
- **Surface:** FREQUENCY × tile weight per entry in controlled tests (RESEARCH-NOTES.md:273; memory df-wave-pick-per-entry). Fliers draw from their own list (:274).
- **Caverns:** stock seems to dominate (PENDING). The tool's cavern draw is broken in this build (it strips `cavern:` from keys; 0 cavern draws in B2), so cavern odds act only through DF.
- **The land/flying draw** (15908-15943) takes the least-seen member first; odds only break ties.
- **B1 Fort 1, DF waves only, by arrival day:**
  - Spring flying: sparrow (2) 3, barn owl (21) 3, roach man (1) 2.
  - Summer flying: bat man (1) 5 days, 11 groups; swan (50) 3 days.
  - Land apexes came from DF (recluse 3, T. rex 4, scorpion 2). Coupling may have called some (the ledger shows grasshopper, then T. rex 2 days later); not checked for every case.
  - Land sat paused at its cap 89% of the run.
- Memory cast-coverage-drivers: narrowing the ladder's spread moved coverage only from 58% to 57%.

Inference: on the surface, tuning between 2 and 4 is swamped by the caps, the draw and one group per species.

**Risks of putting apexes on the ladder:**
- The scheduler (`ROSTER.apex.decide`, 11691-11745) counts DF's apex groups toward its target but cannot hold DF back. Higher apex FREQUENCY would overshoot, and the scheduler would simply go quiet.
- More apexes take land-cap slots from prey.
- The cap of 5 exists because 16 extinct land apexes read 50 (R34).

### What serves diversity and ecology better
- **Flying 30 → 6:** do it. It costs nothing and fixes bird men.
- **Clean the tables:**
  - drop land LB/WB/RP/MW, flying WB/ML and cavern WB;
  - **add RP = 2 to the water ladder**;
  - give AL-guild animal people an explicit weight instead of the 5 fallback.
- **The real problem behind ML/MW = 4 is animal people.** Prey-guild animal people sit in the predator level with prey weights. Put each SN in prey or predator by its guild (GZ/PL/SH/LB/WB/FF/FC means prey). That gives real mid predators their share without making the gremlin the commonest cavern creature.
- **Seasonal balance comes from the cast:** for example, at least one non-raptor in the two flier slots.
- **Keep apexes off the ladder.** For more apexes, raise `roster apex target <layer> N`. Flying is the gap: its target and its A share are both 0.

### What would settle it (not run)
1. **Does the ladder steer at all?** Fort 1 (PC_SAVR), tool fully on. Arm A today's ladder, Arm B equal odds for in-season ground and flying members. n=5 per arm, one season each. Count waves per species and the predator share. If A and B match, family-weight tuning is moot on the surface.
2. **The proposed change.** Same save, ML/MW 4 plus apexes as their own level. n=5 per arm. Measure the predator and apex share of waves, the gremlin's cavern share, apex presence against target, scheduler placements and time at the cap. Read the caverns alongside pickab (stock against FREQUENCY).

**Rig test that would settle it:** Fort 1 (PC_SAVR) save, read-only until run. (1) Tool fully on; Arm A today's ladder, Arm B equal odds for in-season ground and flying members; n=5 per arm, one season each; count waves per species and the predator share of waves. (2) Today's ladder against ML/MW=4 plus apexes as their own level; n=5 per arm; measure predator and apex share of waves, the gremlin's cavern share, apex presence against target, scheduler placements and time at the cap. The cavern part depends on the pickab stock-against-FREQUENCY result and on fixing the cavern-draw key bug.

<details><summary>Review and verification trail</summary>

- review: Fixed the ML/MW=4 result. The earlier script kept every animal person at its dumped weight. In code (ROSTER.ladder 9405-9406), an animal person reads its own guild's weight, so ML-guild animal people go up along with ML. SKINK_MAN copies SKINK [CARNIVORE], so its guild is ML: it goes 7->9, not 7->5. In the caverns, GREMLIN [BONECARN] (ML guild, size factor x4) goes 58->90 and becomes the second-commonest cavern creature. The claim that raising ML/MW is 'exactly the same as halving every animal person's weight' was wrong and is gone. Rerun with each animal person's guild (inferred guilds match every dumped family value): .claude/scratch/sw-questions/C2-review/guildaware.py.
- review: Corrected the ML/MW=4 numbers. Land: weasel/adder 23->30 (not 32), rattlesnake 9->12 (not 13), dingo man 7->4. Land predator share: spring 13->14, summer 30->38, autumn 30->34, winter 16->12. Caverns: helmet snake 24->37 (not 40), toad/olm 19->29 (not 32), manera 87->67 (not 73), cavern 1 spring 64%->70% (not 72%). Osprey 30->25 (not 26).
- review: Corrected the apex-as-own-level ranges. Land apexes are 5-28, not 12-28 (T. rex stays at 5 from the size factor). Cavern apexes are 8-57, not 32-57 (jabberer and cave dragon get 8). Land apex share goes from 0-5% to 11-13%. Cavern 1 apex share is spring 35%, summer 25%.
- review: Fixed the history of the 30. results22.md section 2 says flying 'stays at 19% even at prey x5' and that lowering it needs a slot change (RP 1-1). So x5 was the furthest the search went, and it still did not get flying predators below 19%. The 30 was not 'found to hold predators at 19%'.
- review: Explained WB on flying with the R50 slot table. The v7.1 flying layer had a WB 0-2 slot (docs/v7.1/roster.md R50). The 9 Oct slot redesign (memory full-pool-design-oct9) moved birds and raptors off land-ground and made the flying slots '2 meso-or-prey fliers'. codeFor (10264) now codes those LB or RP.
- review: Added the hidden default of 5 (fam[baseKey] or fam[code] or 5 at 9406). It applies to AL-guild animal people (dingo man, troll, serpent/reptile/amphibian men, trogs, ogre: family 5 in the dumps). On the water ladder it applies to RP-guild animal people (FLY_MAN and MOSQUITO_MAN read 5 in LAKE3) as well as ospreys. All of these outweigh real mid predators at 2.
- review: Added that adding APX=2 to the family table does nothing in today's code. Apexes are set aside before family weights are read (9399-9400) and given raw FREQUENCY capped at 5 (9444-9461). The pyramid's A column is labelled 'the apex scheduler's, not the ladder's' (9081-9082).
- review: Added the biggest missed point. castLadder (11034-11096) pools all four seasons into one ladder call, so the pyramid split is a whole-year target, not a per-season one. Fort 1's flying prey share of FREQUENCY is 7% in spring, 88% in summer and 0% in autumn, because the autumn cast drew raptors into both flier slots. The user's slot table allows that ('2 meso-or-prey fliers'). No family weight can fix it. Diagram panel 2b step 5 says 'per season', which the code does not do.
- review: Fixed the B1 evidence. Fort 1 is now counted in waves (arrival days) as well as groups, per memory cavern-pick-stock-weighted ('count waves, not groups'). Summer flying: bat man (FREQUENCY 1) 11 groups on 5 days against swan (50) 5 groups on 3 days. Bat-man waves split into about 2 groups each. It is one short run (171 days), so suggestive, not proof.
- review: Balanced the claim that DF ignores FREQUENCY. On the surface DF does weight the pick by FREQUENCY x tile weight (RESEARCH-NOTES.md:273 X3/ECO F1; memory df-wave-pick-per-entry). The flat B1 arrivals come from the tool's caps (land paused 89%, flying 75%), coupling and entry counts. Memory cast-coverage-drivers also shows ladder spread barely moves cast coverage (58% vs 57%).
- review: Added that on the water ladder FREQUENCY feeds the tool's own weighted draw. Ledger: 'BIRD_OSPREY ... weight 10.8 (base 29 x 0.37 ...)'. So the missing RP key has a direct effect there.
- review: Confirmed: 30->6 changes no written FREQUENCY on Fort 1 or the coast fort. Bird-man numbers restated: at 30 the bird man gets 21 and owl/kestrel 11 (21 today with the mantis man); at 6 the bird man gets 7 and owl/kestrel 18.
- review: Corrected the coast-fort note: COAST's land ladder has no animal people; it is Fort 1's land ladder that does.
- verifier: Added: family weights for cavern members never reach the tool's cavern draw (that draw is dead in 6dffef5 because of the key bug), so cavern ladder edits act only through DF's pick, which is PENDING (stock).
- verifier: C3 claimed flying odds are ruled by the family weights; that is wrong. Within each level the weights cancel, as this answer shows.

Code refs: sw-wt/plugin/scripts/seasonal-wildlife.lua:9374-9379 (ROSTER.LADDER22, hard-coded family weights); sw-wt/plugin/scripts/seasonal-wildlife.lua:9382-9472 (ROSTER.ladder: apex set aside 9399-9400; fam[baseKey] or fam[code] or 5 at 9405-9406; pyramid split 9419-9421; biomass guard 9423-9433; rescale to 100 9434-9442; apex raw/cap/apex_odds 9444-9461); sw-wt/plugin/scripts/seasonal-wildlife.lua:9198-9201 (ROSTER.TIER, ROSTER.LEVEL: SN='C', APX='A'); sw-wt/plugin/scripts/seasonal-wildlife.lua:9076-9086 (V7.rosterDefaults: apex_odds 0, apex_raw_cap 5, pyramid; 'A is the apex scheduler's, not the ladder's'); sw-wt/plugin/scripts/seasonal-wildlife.lua:9112 (apex presence land 25 flying 0 water 20 cavern 70, cap_calm 1 / cap_savage 2); sw-wt/plugin/scripts/seasonal-wildlife.lua:797-805 (V7.RULES.roster.SLOTS: user's slot tables; flying = apex 1, flier 2, sentient 1); sw-wt/plugin/scripts/seasonal-wildlife.lua:10034-10066 (ROSTER.FP.layersOf: fliers to land-flying only from land biomes); sw-wt/plugin/scripts/seasonal-wildlife.lua:10198-10251 (ROSTER.FP.slotsFor); sw-wt/plugin/scripts/seasonal-wildlife.lua:10253-10266 (ROSTER.FP.codeFor: flier->RP/LB, waterbird->RP/WB, sentient->SN); sw-wt/plugin/scripts/seasonal-wildlife.lua:11034-11096 (ROSTER.castLadder: all four seasons pooled into one ladder call per partition; partition order 11043-11050; code fallback slotOf 11059 for casts without codes); sw-wt/plugin/scripts/seasonal-wildlife.lua:23355-23366 (NR.toRecord writes codes for every cast member); sw-wt/plugin/scripts/seasonal-wildlife.lua:11531-11536 (v7.0 ROSTER.LADDER, v2.1 values with land LB/WB/RP); sw-wt/plugin/scripts/seasonal-wildlife.lua:2264-2290 (MODEL.guild: apVermin flier->RP 2265; flier+diet->RP; LP->AL; flier->WB/LB by water biomes); sw-wt/plugin/scripts/seasonal-wildlife.lua:11691-11711 (ROSTER.apex.decide: counts any apex group on map toward presence; target 0 -> no placement); sw-wt/plugin/scripts/seasonal-wildlife.lua:12041-12042 (verb: roster apex target <layer> N); sw-wt/plugin/scripts/seasonal-wildlife.lua:15908-15943 (V7.DRAW.pick: least-seen first, cfg.odds as tie weight, apex excluded); sw-wt/plugin/scripts/seasonal-wildlife.lua:4646-4662 (CAVERN.apply: one FREQUENCY per raw, max of odds while open); sw-wt/plugin/scripts/seasonal-wildlife.lua:17377-17388, 1317 (coupling; default on); sw-wt/plugin/docs/v7.1/roster.md R34, R50, R57 (apex off ladder; flying slots APX/RP/LB/WB 0-2; v2.2 port); sw-wt/plugin/RESEARCH-NOTES.md:270-276 (FREQUENCY weights the surface pick; fliers draw from their own list); DwarfCron/data/eco-desk/v2/guilds/roster2.py:103-118 (LADDER, LADDER21, LADDER22 'prey x5: still ~19%'); DwarfCron/data/eco-desk/v2/guilds/results22.md:65-79 (flying stays 19% even at x5; needs slot change); DwarfCron/data/pacing/mechanics-diagram.html panel 2b (steps 1-7; step 5 says 'per season'); DwarfCron/.claude/scratch/pacing/ladder/SAVR_d1.json, COAST.json, LAKE3.json (ladder rows); DwarfCron/.claude/scratch/sw-questions/C2-review/guildaware.py, birdman.py, flat.py (review re-runs; reuse C2/ladder_whatif.py); DwarfCron/data/pacing/B1/PC_SAVR/probe.jsonl, ledger.txt, ../summary.md (arrivals by season, pause %); vanilla raws: SKINK [CARNIVORE], DINGO [LARGE_PREDATOR][BONECARN], GREMLIN [BONECARN], c_variation_default.txt ANIMAL_PERSON (FLIER not removed); memory: full-pool-design-oct9.md, cast-coverage-drivers.md, df-wave-pick-per-entry.md, cavern-pick-stock-weighted.md

</details>

## C3

> What would happen if... instead of "Size within its slot" was calculated to reweight the frequency of appearance we just set the frequency of cast members sharing a slot to be equal?

**Short answer.** Two readings. (A) Drop the size factor but keep ÷ group size: slot-mates get equal shares of animals. (B) Literally equal FREQUENCY: equal shares of waves, so packs and herds bring many times more animals. A is the better design: it removes an arbitrary comparison against this year's slot-mates, gives one rarity rule per species and steadier per-season predator shares on paper. Expect little change on land and flying in play (the draw and one-group-per-species dominate). Caverns move only if DF's cavern pick follows FREQUENCY (PENDING).

*Status: corrected · confidence medium · review verdict: major fixes*

### Short answer
There are two ways to read "set slot-mates equal":
- **A. Drop the size factor (step 4) and keep ÷ mean group size (step 6).** Every member of a slot gets an **equal share of animals**; a herd species gets fewer waves, because each wave brings more animals.
- **B. Literally equal FREQUENCY.** Equal share of **waves**, so a pack of 6 coyotes comes as often as one rattlesnake and brings 6× the animals.

**A is the better choice; B is not.** On land and flying, though, expect less change in play than the paper numbers suggest.

### What step 4 does (`scripts/seasonal-wildlife.lua`, sw-wt 6dffef5)
- `ROSTER.ladder` (9382) takes each slot code's geometric-mean mass (9393-9397) and applies `scale = (mass/geo)^-0.75`, clamped ×0.25-4 (9402-9403), multiplied into the family weight. The level split, the biomass guard, ÷ group size and the normalise-to-100 with floor 1 follow (9415-9443). Apexes skip all of it (cap 5, 9444-9461).
- **"Its slot" means the slot across the whole year** (`castLadder` pools all four seasons, 11034-11089), and across all three caverns for the cavern ladder.
  - Between two members of the same slot, the mean cancels: their ratio is just (size1/size2)^-0.75, unless the clamp bites.
  - The year-wide mean matters through the clamp and between different slots.
- **That makes the factor arbitrary in practice.** Fort 1 (`SAVR_d1.json`):
  - The 201 kg giant weasel gets **×1.74**, because its ground-prey slot mean (422 kg) is pulled up by 2-tonne giant beetles, slugs and grasshoppers.
  - The 204 kg giant skink gets **×0.25**, because its meso slot mean is 13 kg (weasel, adder).
  - Same size, 7× apart, only because of who else the builder cast in that slot this year.
- **Animal people** all take code SN and are sized against each other: a 4.5 t triceratops man against a 35 kg skink man.

**Who reads the result:**
1. **DF's surface waves.** Per open entry (memory df-wave-pick-per-entry); one open entry per species (`V7.SRC`, 3242-3253).
2. **The tool's ground/flying draw** (`V7.DRAW.pick`, 15908-15943). Least seen first; the ladder only breaks ties.
3. **The water draw.** The ladder value is the base weight, and its share is the balance target (`V7.WAT.mix`, 7806-7830).
4. **Caverns:** DF only. The P9 cavern draw never fires in this build (`V7.DRAW.members` strips `cavern:` from keys, so no cave entry is found; 0 cavern draws on all four B2 forts). DF's cavern pick may follow stock more than FREQUENCY (PENDING).

### On paper: Fort 1 recomputed (pure "DF picks by FREQUENCY")
Scripts: `DwarfCron/.claude/scratch/sw-questions/c3_nosize.py`, `c3_compare.py`.

**FREQUENCY under A:**
- giant beetle, slug and grasshopper 8 → 100;
- giant weasel and hamster 44 → 100;
- triceratops 2 → 30, triceratops man 4 → 58;
- black bear and giant skink 1 → 22;
- wolf and coyote 1 → 4.

| Season (7 non-apex) | Measure | Now | A | B |
|---|---|---|---|---|
| Spring | top share | weasel 44% | slug 30% | 22% |
| Spring | effective species | 3.3 | 4.5 | 5.7 |
| Spring | carnivores' share of animals | 11% | 27% | 23% |
| Summer | top share | beetle 27% | beetle 32% | 22% |
| Summer | carnivores' share | 39% | 13% | 22% |
| Autumn | top share | arthropleura 58% | 44% | 22% |
| Autumn | carnivores' share | 30% | 18% | 23% |
| Winter | top share | hamster 49% | 42% | 22% |
| Winter | carnivores' share | 18% | 27% | 19% |

- Expected species seen in 8 waves moves by −0.1 to +0.7 per season under A.
- **B breaks the balance in places:** coast winter carnivores reach 54% of animals; Fort 1 cavern 2 spring reaches 81%.

### What the rig shows: land and flying arrivals barely follow FREQUENCY
B1, same fort and same casts, DF waves only:

| Layer, season | Member (FREQUENCY) → waves |
|---|---|
| Ground, spring | weasel (44) 3 · coyote (1) 2 · rattlesnake (9) 2 · colepio (30) 1 · triceratops man (4) 1 · slug (8) 0 · platybelodon (3) 0 |
| Ground, summer | **giant skink (1) 5** · beetle (8) 3 · grasshopper (8) 3 · ankylosaurus (2) 2 · skink man (7) 1 · iguanodon (3) 1 · black bear (1) 0 |
| Flying, spring | barn owl (21, 88% of paper) 3 · giant sparrow (2) 3 · roach man (1) 2 |
| Flying, summer | swan (50, 96%) 3 · **bat man (1) 5** · giant kestrel (1) 1 |

Why (code):
- `groups.one_per_species` (1028) closes a present species' surface entries (`V7.GRP.speciesPause`, 16196+).
- Land and flying sat at their cap 75-89% of the time.
- Inference: when a slot frees, the high-odds species is often still on the map and closed.

This is one fort and one run, so the paper table is an **upper bound**, for the gains and for the costs (more triceratops, more black bears).

### Layer by layer, what A would really change
- **Land and flying:** little. DF's first wave after a departure tilts toward big species, and the draw's tie-breaks shift. On flying, note that the family weights (30/2) do *not* decide: they cancel inside each level, and the pyramid split plus the size factor decide.
- **Water:** A acts directly, because the ladder is the draw's own target there; it is damped by the balance clamp and one per species. Fort 1 spring fresh water on paper: snapping turtle 72% → sturgeon 59%.
- **Caverns:** on paper the biggest effect, because caverns are not under one-per-species (comment at 16205).
  - B1's dominant small swarmers lose their boost: bugbat 21 → 12, creeping eye 28 → 7.
  - Dangerous large species gain: troll 15 → 32, blind cave ogre 5 → 16, draltha 7 → 29.
  - If DF's cavern pick follows stock (PENDING), none of this moves.

### Ecology and design
- **Per-season carnivore share (paper):** 13-27% under A against 11-39% now; the land target is about 21%.
- **Biomass guard:** A moves land closer to it (Fort 1 0.10 → 0.14 of 0.5) but does not trip it.
- **Giants made rare twice:** the cast pick already gives giants ×0.2, and 8 of Fort 1's 14 non-apex giants also carry ×0.31 or less from size. Your 17 Oct ruling ("rarity is the pick's alone", comment at 9087) was about `giant_freq`, but the size factor has the same double effect.
- **Realism:** the −0.75 comes from design.md R13 ("small species live denser"). Against a year-wide slot mean it becomes "smaller than this year's slot-mates".

### Recommendation
- **Take A, not B**, for cleaner design: one rarity rule, no arbitrary year-wide comparison, steadier per-season balance. Do not expect it to fix swamping on land or flying.
- **Caverns:** settle stock against FREQUENCY first, and fix the cavern draw key bug. If stock rules, the lever is `cave_open_stock`, not the ladder.
- **To keep some "small is common":** a milder exponent (−0.25, clamp ×0.5-2).

### What would settle it (not run)
1. **Desk, no rig:** tabulate B1/B2 waves (by arrival) per species against the written FREQUENCY for every fort.
2. **Surface pick A/B (like pickab):** two in-season species, one entry each on the anchor tile, equal stock, FREQUENCY 100 against 5 and then swapped, with `one_per_species` on and off.
3. **The C3 A/B.** It needs a knob first (for example `roster.size_exp`, 0 = off; the dev switch also kills the other guards).
   - Fort 1 (region6 24,11) and Coast; current against A; 5 runs per arm; caverns breached; 50 dwarves; spring and summer.
   - Measure waves by species and source, top share, effective species, coverage, carnivores' share of animals, and kills involving large species.

**Rig test that would settle it:** (1) Desk, no rig: waves by arrival per species against FREQUENCY for every B1/B2 fort. (2) Surface pick A/B like pickab: two in-season species, one entry each on the anchor tile, equal stock, FREQUENCY 100 against 5 then swapped, one_per_species on and off. (3) Add a roster.size_exp knob; current against size-factor-off on Fort 1 (region6 24,11) and Coast, 5 runs per arm, caverns breached, 50 dwarves, spring and summer. Measure per layer and season: waves by species and source, top share, effective species, coverage, carnivore share of animals, kills by large species. Read caverns with pickab, after fixing the cavern-draw key bug.

<details><summary>Review and verification trail</summary>

- review: Biggest gap: the answer treats FREQUENCY shares as wave shares on land and flying, and leaves out the one-group-per-species pause. That pause is groups.one_per_species=true (seasonal-wildlife.lua:1028), V7.GRP.speciesPause at 16196-16270. It closes a species' surface entries while its group is on the map. Land and flying also sit at their cap 75-89% of the time (B1 summary). Added the rig evidence from the same fort (B1 PC_SAVR probe.jsonl, same casts as SAVR_d1). F=1 species were among the most frequent arrivals: giant skink 5 waves in summer, the top species; bat man 4-5 flying waves against the F=50 swan's 3; giant coyote 2. Some high-F species (giant slug F8) never came. Measured land balance was already even: top 10%, 16.9 effective species. So the paper table is an upper bound, not a forecast, for both the gains and the costs.
- review: Coverage gain corrected. 'Expected species seen in 8 waves' under A changes by -0.1 to +0.7 per season (summer falls 4.2 to 4.1), not +0.3 to +0.6. In a crude model with the one-per-species pause (scratch c3review/onepersp.py) the gain is only +0.1 to +0.4.
- review: Biomass-guard claim reversed. Recomputed uC*mC/(uH*mH): Fort 1 land 0.096 now against 0.135 under A, Coast land 0.205 against 0.240. Dropping step 4 moves land closer to the 0.5 guard, not further, though it is still far below. The caverns sit just under the guard either way (0.479 now, 0.461 under A). Code: ROSTER.ladder 9415-9429.
- review: 'Most giants sit near x0.25' is overstated. In Fort 1, 8 of 14 non-apex giants are at x0.31 or below, but giant weasel and giant hamster get x1.74. Their ground-prey slot's year-wide geometric mean (422 kg) is pulled up by 2-tonne giant bugs. Added the sharper point: the 201 kg giant weasel gets x1.74 and the 204 kg giant skink gets x0.25 (meso slot, geometric mean 13 kg). Same size, 7x apart, because the factor is relative to whoever else the builder put in that slot that year (SAVR_d1 rows: geo, scale).
- review: Clarified what 'year-wide' means. For two members of the same slot the geometric mean cancels: their ratio is (m1/m2)^-0.75 unless the clamp binds. The year-wide mean matters through the clamp and through comparisons across slots within the plant-eater and meat-eater groups.
- review: Caverns re-framed. They are NOT under the one-per-species pause (code comment at 16205: 'Caverns are not included'). If FREQUENCY counts there at all, the caverns are where A acts most. The B1 cavern dominators are small swarmers that step 4 boosts: bugbat 56%, flesh ball 54%, creeping eye 64% on the evil fort. A cuts bugbat 21 to 12 and creeping eye 28 to 7 on paper, which is a possible diversity gain, not only a cost. Costs added: troll 15 to 32 (top of cavern 1 spring), blind cave ogre 5 to 16, draltha 7 to 29. Stock-weighting is still PENDING.
- review: The tool's own draw also runs in the caverns (V7.DRAW.pick with depth, v8.1 P9). The answer said only ground and flying.
- review: B2 Fort 1 count corrected. The ledger window (summer day 73 to autumn) holds 6 DF land waves, not 7 (the seventh line is a straggler joining its wave). One was the wren man, which is not in the cast; one was an apex. There were 6 tool draws. Those draws brought the F=1 black bear and the F=3 iguanodon, and DF itself sent the F=2 Triceratops.
- review: Added the animal-people effect of A. Ground SN members lose the size factor: Triceratops man 4 to 58 (spring share 4% to 17%), Pachycephalosaurus man 13 to 58. Animal people are already made rare at the cast pick (ap_pick x0.1).
- review: Noted that the Coast dump's cavern ladder is identical to Fort 1's (both dumps read site 266, year 100), so it is not an independent second cavern check. LAKE3's land ladder is also identical to Fort 1's.
- review: Checked and kept: the ladder code lines (9382-9461), family weights, groupMean, castLadder year-wide gathering, SN slot code (10256), water base = ladder value (ledger 'base 6 x 13.72' = MEGANEURA_MAN F6), CAVERN.apply max over layers, P3/P10 text, the R13 origin, and the paper table numbers (all reproduced with c3_compare.py).
- verifier: The tool's cavern draw (P9) is not a reader of the ladder in 6dffef5. V7.DRAW.members strips 'cavern:' (15889), so no cave entry is found and B2 shows 0 cavern draws on all four forts. 'Who reads the result' is corrected.
- verifier: 'Flying is ruled by the family weights anyway (birds 30, raptors 2)' is wrong. Within each level the family weight cancels (all flying prey are LB at 30, all predators RP at 2), so the pyramid's 80:20 and the size factor decide flying odds (see C2).

Code refs: /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:9382-9461 (ROSTER.ladder: size factor 9394-9403, biomass guard 9415-9429, group division 9434, normalise/floor 9438-9443, apex cap 9444-9461); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:9374-9379 (ROSTER.LADDER22 family weights); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:9362-9367 (ROSTER.groupMean); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:9076-9100 (V7.rosterDefaults: units, apex_raw_cap 5, biomass_guard 0.5, ap_pick 0.1, giant_pick 0.2, giant_freq 1 with the 17 Oct note); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:11034-11085 (ROSTER.castLadder: one year-wide ladder per partition); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:10256 (sentient slot -> SN); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:1028 (groups.one_per_species=true), 1029-1030 (single_source, cave_single_source), 979 (land groups auto); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:16196-16270 (V7.GRP.speciesPause: closes present species' surface entries; caverns excluded); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:3242-3253 (V7.SRC one entry per species); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:15905-15942 (V7.DRAW.pick: least seen first, ladder breaks ties; cavern depth too); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:7806-7830 (V7.WAT.mix: ladder base and balance want); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:4646-4660 (CAVERN.apply: odds written, max over layers); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/docs/pacing/PLAN-v8.1.md:23 (P3), 125-140 (P10 target); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/eco-desk/v2/guilds/design.md:243-256 (R13 mass^-0.75); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/mechanics-diagram.html:418 (step 4 text); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/B1/summary.md and B1/PC_SAVR/probe.jsonl (measured arrivals per species, same casts as SAVR_d1); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/B2/P2_SAVR/ledger.txt (DF waves v tool draws); /Users/nathanielcannon/Claude/Projects/DwarfCron/.claude/scratch/pacing/ladder/SAVR_d1.json, COAST.json (ladder rows: mass, geo, scale, engine, live); /Users/nathanielcannon/Claude/Projects/DwarfCron/.claude/scratch/sw-questions/c3_nosize.py, c3_compare.py, c3review/onepersp.py (recomputes; one-per-species model)

</details>

## C4

> What would happen if... instead of "One ladder per partition, for the whole year" the ladders per partition were written per season? I think that the per-year representation is causing individual seasons to be swamped with or be absent of certain species which have a per-year frequency imposed onto the smaller seasonal foodweb subset of animals. This makes the seasonal frequencies wildly divergent from a naturalistic balance that we are looking for.

**Short answer.** You are partly right. The yearly ladder bends each season's prey/predator split away from the pyramid (a mean 15-point miss across 36 casts, against 6 points per cast) and floors some species at 1, so a ladder per cast (layer × season) is the right fix for DF's own waves and for water. It does not cause the swamping seen on the rig: that comes from cavern stock and wave-splitting, and on land and flying the draw's least-seen rule decides most picks. One decision for you first: whether the biomass guard is measured per cast (it would starve predators in 6 of Fort 1's 16 land and cavern casts) or per year.

*Status: corrected · confidence medium · review verdict: minor fixes*

### Short answer
You are partly right, and the part you are right about is worth fixing.

**What the yearly ladder gets wrong:**
- It pulls each season's **prey/predator split** away from your pyramid.
- It crushes some species to the floor of 1, because the whole year sets the scale.

Your pyramid defaults are even labelled "percent of units per season" (`V7.rosterDefaults`, `scripts/seasonal-wildlife.lua:9081`), but the code applies them to the whole year.

**What it does not cause:** the "one species takes most of the arrivals" problem on the rig. That happens mostly in the caverns, and comes from stock and wave-splitting.

**Recommendation:**
- Build one ladder per **cast** (each layer in each season, 28 ladders).
- Decide the biomass guard question below first.
- Fix the cavern draw key bug first.

### (a) What the code does now
- **`ROSTER.castLadder` (11034-11089)** pools all four seasons into four partitions (`ROSTER.FP.PART`, 9617):
  - ground → land;
  - flying → flying;
  - ocean + fresh → water;
  - caverns 1-3 → cavern.

  It runs `ROSTER.ladder` once per partition and stores one `cfg.odds[key]` per species (11076). A species cast on two layers is laddered only in the first partition it meets (v8.1 P5).
- **`ROSTER.ladder` (9382-9443):**
  1. Family weight.
  2. Size factor against the slot's **year-wide** geometric mean (9393-9403).
  3. Level split: prey get uH × q / the **year's** prey total, predators uC × q / the year's predator total. The targets are normalised: land 21.5%, flying 20%, caverns 31%, ocean 13.7%, lake 13% predators.
  4. Biomass guard (9423-9432).
  5. ÷ group size.
  6. The year's top member = 100, floor 1.
  7. Apexes stay off the ladder.
- **Why it is yearly:** inherited, not designed. v7.4 (commit 13ae6bd) carried the old once-a-year builder's ladder onto the casts.
- **How it reaches DF:** `CAVERN.apply` (4645) runs at each season turn and daily (5078, 5129). It writes each in-season species' odds into its raw. One raw serves every key of that species, and the higher value wins (4658). All three caverns share one `cavern:NAME` key.

### (b) Where the yearly ladder bends a season
1. **Prey against predators.** A season's members get their share of the *year's* level total. A season with 40% of the year's prey weight but 67% of its predator weight comes out predator-heavy, whatever the pyramid says.
2. **Size against other seasons' slot-mates.**
   - Fort 1's giant sparrow hits the 0.25 clamp against the year's land-bird mean; in its own season it would be 1.0.
   - The black bear in summer ground gets **1** on the yearly ladder and **49** on its own season's.
3. **Rounding to a year-wide 100.** Fort 1 summer flying: swan 50, giant kestrel 1, bat man 1, so the swan takes 96% of a FREQUENCY pick.
4. **Ground against flying (uncertain; probably not a real effect).** Each partition is scaled to 100 separately. But DF's fliers draw from their own list (RESEARCH-NOTES.md:274). B1 Fort 1 agrees: flying was about 41% of spring surface arrival days and 40% of autumn's, where the yearly FREQUENCY gives 20% and 3%. So the cross-ladder scale probably does not set the ground/flying split; each layer's own cap and pause do.

### (c) Thought experiment on real forts
**Method.** `DwarfCron/.claude/scratch/sw-questions/c4/perseason.py` reproduces the engine's yearly ladder exactly (89 of 89 Fort 1 rows), then reruns the ladder per cast. The aggregation is in `c4-review/agg_norm.py`, re-run for this check. "Share" means a plain FREQUENCY pick among the season's members.

**Fort 1 examples:**

| cast | yearly ladder | per-cast ladder |
|---|---|---|
| flying, spring | owl 88%, sparrow 8%; predators 62% of units (target 20%) | owl 42%, sparrow 45%; predators 20% |
| fresh, spring | snapping turtle 72%; predators 3% (target 13%) | turtle 28%, carp 29%, Jaekelopterus 19%; predators 13% |
| cavern 1, winter | predators 85% (target 31%) | 31% |
| ground, summer | predators 39% (target 21.5%); black bear 3% | 22%; black bear 14% |

**Where per-cast is worse: the biomass guard binds on small casts.**
- It binds on 6 of Fort 1's 16 land and cavern casts. In cavern 3 autumn, flesh ball goes 47% → 83% and predators fall to 1%.
- On the yearly ladders it binds nowhere.

**Totals over 36 casts** (all of Fort 1, plus the coast's ground, flying and ocean):

| measure | yearly | per cast |
|---|---|---|
| mean miss on predator share against target | 15 pts | 6 pts |
| casts more than 10 pts off | 18 | 7 |
| mean top share | 54% | 51% |
| casts with one species above 50% | 18 | 21 |
| effective species ÷ cast size | 67% | 72% |
| coverage at 8 waves | 63% | 66% |

**Caveats:**
- Hitting the pyramid on paper is close to automatic, because the ladder is built to hit it.
- All dumps are site 266, year 100. The cast seed is site + year (`NR.seedOf`, 23149), so the cavern casts are identical: this is really two forts.

### How much the ladder actually steers arrivals
- **Ground and flying, tool draw** (`V7.DRAW.pick`, 15908-15943): lowest season tally first, odds only among ties.
  - The tally counts **animals**, DF-wave animals included (`V7.TALLY.note`, 11269).
  - The first round brings every member once. After that, solitary species return before herds and packs.
  - So the season's balance there comes from the cast's slot make-up and the animal-count rule, not from the ladder.
- **DF's own surface waves:** FREQUENCY × tile weight among *open* entries (one group per species closes present species). A waiting DF wave is released before the tool draws. **This is where per-cast odds matter most on land.**
- **Water:** base weight = live FREQUENCY (`ENGINE.weight`, 7399). `V7.WAT.mix` (7806+) already applies a live pyramid correction, so per-cast odds help, but less than the paper suggests.
- **Caverns:** DF's pick looks stock-weighted (B1 flesh ball at FREQUENCY 10 took 54% of cavern 3; PENDING). Bugbats split each wave into about 2.7 groups. That is the swamping you see, not the ladder.
- **Bug to fix first (confirmed).** `V7.DRAW.members` strips `cavern:` from keys (15889), then looks up `ROSTER.apex.entries`, `cfg.odds` and the apex list under the bare name (15912-15938). Cave entries are filed as `cavern:NAME` (`keyFor`, 1687; `CACHE.managedPops`), so the cavern draw never finds an entry.
  - B2: 0 cavern draws on all four forts.
  - P2_COAST cavern 3 sat at 0 groups for 81 probes.
  - Until this is fixed, per-cast cavern odds cannot reach the tool's cavern draw.

### Risks and what breaks
1. **One raw per species per season.** Fort 1 has four species in two caverns in the same season. `cfg.odds` needs a season × layer dimension; keep higher-wins for the shared raw.
2. **Readers of `cfg.odds`:**
   - `CAVERN.apply`;
   - `ODDS.weight` (the window's shares);
   - the cavern hold level (16540);
   - `V7.DRAW.pick`;
   - the info line and `cast status`.

   A manual `odds KEY N` is overwritten at every build today; a per-cast design should let it override.
3. **Stand-ins** need a value for a season they were not laddered in (their slot's, or their yearly value).
4. **Small casts** (2-5 members): the guard and rounding get twitchy. An all-raptor cast (Fort 1 autumn flying) is 100% predators on any ladder; that is a cast-builder matter.
5. **Not partition × season.** That would still mix the three caverns, and ocean with fresh water.

### Does it serve your aims?
- **Ecology / seasonal balance:** yes, for DF's own waves and the water base weights.
- **Diversity:** a little (63% → 66%). You approved per-cast scaling on 16 Oct and it was shelved because coverage barely moved. That still holds; the new reason to build it is the predator balance.
- **Swamping:** no. For caverns the levers are stock (`cave_open_stock`) and counting waves rather than groups. On land and flying, the draw's pick rule and the slot make-up matter more.

### One decision for you: the biomass guard
- **Per cast:** "this season's predators fit this season's prey", the naturalistic reading, but it starves 6 of 16 Fort 1 casts (down to 1% predators).
- **Measured once per year:** never binds on these forts, so in practice it is off.
- Anything in between would be a new guard, which your 16 Oct ruling rules out.

### What would settle it (not run)
**First:** fix the cavern draw key bug, or leave caverns out.

**Setup:**
- Validation forts embarked fresh on the same tiles.
- Caverns breached, 50 dwarves, one full year, `cave_open_stock` on in both arms.
- Arms: yearly against per-cast ladders, n=5 per arm.

**Measure per cast:**
- predator share of **arrivals** against the pyramid;
- waves per species, effective species, top share;
- arrivals by source (DF wave against tool draw);
- the ground/flying split of DF's surface waves (this also checks the "fliers draw from their own list" note);
- how often the guard binds.

**Rig test that would settle it:** Fix the cavern-draw key bug first, or leave caverns out. Then validation forts embarked fresh on the same tiles: caverns breached, 50 dwarves, one full year, cave_open_stock on in both arms; yearly against per-cast ladders, n=5 per arm. Per cast measure: predator share of arrivals against the pyramid, waves per species, effective species, top share, arrivals by source (DF against draw), the ground/flying split of DF's surface waves (which also tests the fliers-own-list note), and guard binding.

<details><summary>Review and verification trail</summary>

- review: Corrected the 'same ratios inside a level' claim. ROSTER.ladder computes each member's size factor against its own slot's geometric-mean mass (seasonal-wildlife.lua:9393-9406). So ratios stay the same only between members of the SAME slot. Two species in different slots of the same level (say grazer vs browser) change ratio when the slot means change between the year and the season. The giant sparrow example is exactly this case.
- review: Corrected the pyramid targets. The ladder normalises H and C before splitting (9415-9418: uC = C/(H+C)), so the predator targets are land 21.5%, cavern 31%, ocean 13.7%, flying 20% and lake 13%, not the raw 20/27/13 the draft used. The draft's agg.py compared against the raw C/100. Rerun with the real targets (scratch c4-review/agg_norm.py): the yearly ladder misses by 15 points on average with 18 of 36 casts more than 10 points off; per-cast misses by 6 with 7 of 36. The case gets stronger, not weaker. Cavern 1 winter per-cast lands exactly on the 31% target, not '31% vs 27%'.
- review: Added how often the biomass guard binds. Per cast it binds on 6 of Fort 1's 16 land and cavern casts: ground spring, caverns 1 and 2 in autumn, cavern 3 in spring, autumn and winter. It never binds on the yearly ladders (SAVR_d1/COAST ladders.binding = 'pyramid target' for all four partitions). The draft named only cavern 3 autumn and winter, and missed that ground spring gets worse per cast (predator units 11% -> 7%). It also follows that the draft's 'yearly guard applied to every season' option means no guard at all on these forts.
- review: Added the history: memory cast-coverage-drivers records that on 16 Oct the user approved 'scale the ladder per cast'. It was not built because the offline counterfactual showed coverage would not move. The new argument (prey/predator balance per season) is different from the one that was shelved.
- review: Added the reality check the draft understated. The ladder's FREQUENCY steers only part of the arrivals. The tool's ground and flying draw picks the least-seen member first and uses the odds only to break ties (V7.DRAW.pick 15908-15943), so there the cast's make-up sets the season's balance. The water draw already corrects predator share live: V7.WAT.mix's pyramid factor ((target+1)/(have+1))^0.5, clamped 0.25-4 (7806-7870; default pyramid=0.5 at line 956), plus balance and one group per species. The draft's 'shows most clearly in the water draw' is overstated. Caverns follow stock (memory cavern-pick-stock-weighted: flesh ball at FREQUENCY 10 took 54% where a FREQUENCY pick predicts 6%).
- review: Side finding (code fact plus inference). The tool's cavern draw strips 'cavern:' from member keys (V7.DRAW.members, 15889-15905), then reads cfg.odds[bare name] and apex_keys by the bare name (V7.DRAW.pick 15912-15938). The ladder stores both under 'cavern:NAME' (castLadder 11076-11078; dump keys 'cavern:DRALTHA'). So cavern draws read every weight as 1 and do not exclude apexes. ROSTER.apex.entries(bare name) matches r.key, which keyFor sets to 'cavern:NAME' for cave entries (1687-1690, 3670). From that I infer the cavern draw may find no entry at all. The B2 ledger tails show 0 cavern draws among 47 draws. Per-cast cavern odds would not reach this draw until that is fixed.
- review: Fixed line numbers. The math.max in CAVERN.apply is at 4658, not 4660; floor-of-1 is at 9441; geo is at 9397. The math.max merges a species' land, water and cavern keys into one raw. All three caverns share ONE 'cavern:NAME' key, so per-cast cavern odds need an extra (layer) dimension before the max.
- review: Verified and kept: the reimplementation matches the engine (cavern 31/31, flying 12/12, land 28/28, water 18/18 on Fort 1; all rows on the coast fort). Black bear F 1 -> 49 and giant sparrow 8% -> 45%. The flying share of combined surface FREQUENCY in Fort 1 autumn is 3% -> 48%. The four same-season cavern double-casts are real. All three dumps are site 266, year 100. CAVERN.apply runs at each season's turn and daily (5078, 5129). holdOutOfSeason holds out-of-season species by stock (3931). presentRaces skips caverns (16210-16216). v7.4 commit 13ae6bd carried the yearly ladder onto the casts.
- verifier: Point (b)4, that the ground/flying split of DF's surface waves is set by each ladder's separate scaling, is probably wrong. RESEARCH-NOTES.md:274 says fliers draw from their own list, and B1 Fort 1 had flying at about 41% of spring surface arrival days and 40% of autumn's, where the yearly FREQUENCY gives 20% and 3%. It is downgraded to uncertain and dropped as a reason for the change.
- verifier: Added: 'everyone comes round before anyone repeats' holds for the first round only. The tally counts animals, so after that solitary species come back before herds and packs.
- verifier: The cavern draw key bug is confirmed from both the code and the rig: 0 cavern draws on all four B2 forts, and P2_COAST cavern 3 sat empty for 81 probes.

Code refs: /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:11034-11089 (ROSTER.castLadder: yearly per-partition ladder, cfg.odds per key); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:9382-9443 (ROSTER.ladder: slot geo 9393-9406, level split normalised 9415-9418, biomass guard 9423-9432, max-100 + floor 9434-9443); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:9081-9086 (V7.rosterDefaults pyramid 'percent of units per season', biomass_guard 0.5); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:9617 (ROSTER.FP.PART); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:4645-4705 (CAVERN.apply; math.max of odds at 4658); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:5078, 5129 (season-turn and daily CAVERN.apply); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:3931 (holdOutOfSeason); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:15889-15943 (V7.DRAW.members strips 'cavern:'; V7.DRAW.pick least-seen then cfg.odds[bare key]); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:15997-16027 (V7.DRAW.caveTick); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:1687-1690 (keyFor), 3638-3676 (CACHE.managedPops row keys), 11563 (ROSTER.apex.entries); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:7399-7413 (ENGINE.weight), 7806-7870 (V7.WAT.mix live pyramid/balance), 956 (mix defaults pyramid=0.5); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:16210-16216 (V7.GRP.presentRaces skips caverns); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:23149 (NR.seedOf); git 13ae6bd (v7.4: yearly ladder carried onto casts); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/B1/summary.md; /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/B2/P2_SAVR/ledger.txt (draw lines); /Users/nathanielcannon/Claude/Projects/DwarfCron/.claude/scratch/pacing/ladder/SAVR_d1.json, COAST.json, LAKE3.json; /Users/nathanielcannon/Claude/Projects/DwarfCron/.claude/scratch/sw-questions/c4/perseason.py, agg.py; /Users/nathanielcannon/Claude/Projects/DwarfCron/.claude/scratch/sw-questions/c4-review/agg_norm.py (normalised targets), savr.txt, coast.txt; memory: cast-coverage-drivers.md (16 Oct approval of per-cast scaling, shelved), cavern-pick-stock-weighted.md, df-wave-pick-per-entry.md, beta-rulings-oct16.md

</details>

## C5

> What would happen if... instead of apex predators "Not on the ladder. Their own raw FREQUENCY, capped at 5, so DF rarely sends them. The apex scheduler places them instead (its presence targets: land 25, water 20, caverns 70)" they were just given frequencies based on the ladder, and were sent in without their own special apex scheduler?

**Short answer.** It would not give you control. Today most apex visits come from DF waves, often called in by coupling, or from the water draw, not from the scheduler. Putting apexes on the FREQUENCY ladder would raise DF's apex odds 2-5×, so land apexes overshoot further where DF is generous (Fort 1 is already at 32-63% presence against your 20-30%), and summer apexes would go missing where the draw carries the layer. Better: make apexes ordinary members of the tool's draw under the layer cap and pause, with a presence-aware limit like water's apex_max, and keep the scheduler only for invasives, thieves and stock-poor cavern apexes.

*Status: corrected · confidence medium · review verdict: major fixes*

**Short version:** the swap would not remove much special logic and would not give you control. Most apexes today arrive as DF waves (often called in by coupling) or through the water draw, not from the scheduler. Making apexes ordinary members of the layer draw would serve your aims better than putting them on the FREQUENCY ladder.

### 1. What the code does today (`scripts/seasonal-wildlife.lua`, sw-wt 6dffef5)
- **The ladder leaves apexes out (R34).** `ROSTER.ladder` sets APX/APE/AL/AW aside (9389-9391). The apex block (9444-9461) writes one of:
  - `apex_raw_cap` 5, if the raw is higher;
  - `apex_odds`, if you set it (default 0 = off);
  - nothing, so the raw stands.

  `castLadder` hands the keys to the scheduler (11077).
- **The cap mostly lowers apexes.** Fort 1's land tick, scorpion and recluse go from 25-50 down to 5; T. rex keeps its raw 2. Jabberer and pond grabber have no FREQUENCY token in vanilla (default 50 → 5). Spider cave giant 20 → 5. The cave dragon keeps 5 (vanilla `creature_next_underground.txt`, `creature_subterranean.txt`).
- **The scheduler** (`ROSTER.apex.decide`, 11691-11745), once a game day:
  - It measures the share of the season an apex group of that layer has been on the map. DF's apex groups count.
  - It stops at its own cap (1 group calm, 2 savage), and stops at target once 7 days have been measured.
  - Otherwise it places with probability 1 − e^(−λ·dt), λ = P/((1−P)·21,500). On land that is about 1.8% a day while under target.
  - Targets: land 25, flying 0, water 20, caverns 70.
  - It can only **add** apexes, never hold DF back.
  - It ignores the layer's cap and pause (thieves excepted: 11724).
- **Invasives (R36) and cavern thieves** run in their own loops in `placeTick` (11786-11803). `roster apex off` (12035) stops only the apex loop.
- **The land/flying draw** (`V7.DRAW.pick`, 15908-15943) skips apex keys. The comment at 15880 says "Apexes stay with the apex scheduler". That was an implementation choice; PLAN-v8.1 has no ruling on it.
- **The water draw already handles apexes.** Base weight is the written FREQUENCY (7399). Curated apexes are level A (`V7.WAT.levelOf`, 7628). `V7.WAT.mix` sets their weight to 0 once a body holds `apex_max` = 1 apex group (956, 7847).
- **Coupling** (on, 1009/1317). When a fresh DF land wave arrives, `V7.GRP.coupleStart` (5569) closes other surface entries for up to 2 days and opens only that prey's predators, apexes included. Drawn **ground** groups are residents and do not call. A drawn **flier** carries `grp.fly` and can still call (trigger around 17379).

### 2. Layer by layer
Sources: B1/B2 probes and ledgers (7 runs), the SAVR_d1 and COAST dumps, and `DwarfCron/.claude/scratch/sw-questions/C5/apex_on_ladder.py` (apexes as a third level at the pyramid's A share).

**Land, Fort 1 (savage marsh)**
- On the ladder: recluse 12, T. rex 5, scorpion 28, tick 12. Their share of the season's FREQUENCY goes from about 3-6% to 11-14%.
- Every land apex came as a DF wave. The scheduler placed none, because presence was already over 25%.
- Apex presence was 63% / 51% (B1 spring/summer) and 60% / 32% (B2), against your R9 range of 20-30%.
- DF sent more apexes than FREQUENCY predicts (B1 spring: recluse 3 of 12 waves).
  - Coupling is one known route: the ledger shows grasshopper, then T. rex 2 days later, and arthropleura, then the scorpion.
  - Long stays add to presence: one recluse group stayed 41 days in B2.
- **With the swap (inference):** DF's ordinary picks would bring apexes 2-5× as often, coupling would still call them, and presence would rise further. One group per species limits apexes to one group at a time, not to fewer visits.

**Land, calm coast fort**
- B2: all three apex visits (black bear spring and autumn, cougar summer) were **scheduler placements**, at 3-22% presence. The draw carried most arrivals (38 draws, 12 DF, 3 placements).
- On the ladder: bear 15, cougar 25. With B2's few DF waves that is about 1.2 bear and 0.4 cougar visits, against 1 placement each today.
- **Inference:** about the same in spring, fewer apexes in summer.

**Water**
- Fort 1's river has no apex slot. Its curated apexes already sit on the ladder (Jaekelopterus MW 3, giant alligator SH 3). The water draw brought them, and presence ran 73-91%.
- The coast's ocean apexes are scheduler keys, but the water draw brought them all (83-90%), so the scheduler sat idle.
- Water is your proposal already running, and it shows the catch: **an apex limit caps how many apexes, not how often or how long.**

**Caverns**
- Across 7 runs: cave dragon placed 3 / DF 2; jabberer placed 4 / DF 3; pond grabber placed 2 / DF 0.
- On the ladder: jabberer 8, pond grabber 32, spider cave giant 57, blind cave bear 57, molemarian 52, cave dragon 8.
- Jabberer and pond grabber have stock (POPULATION_NUMBER 15:30), so higher odds may bring them more often.
- The cave dragon (2:5) and the giant cave spider (3:4) are stock-limited; FREQUENCY cannot fix that.
- Whether the cavern pick follows FREQUENCY or stock is **PENDING**.
- **A natural test already running:** the cave crocodile is cavern 1's autumn/winter apex, but it was first met as an MW in summer, so it sits on the ladder at 8 and is never scheduled. DF sent 6 groups in B1's autumn.

**Fliers**
- Target 0, so the scheduler never places them. DF sends flying apexes at 5.
- On the ladder with flying A = 0 they would floor at 1. That 0 is a placeholder ("shown for the record", 9081).

### 3. What changes, in one list
- **Lost:** scheduler placements on draw-fed calm land (some summer apexes), and the cave dragon (stock-limited).
- **More apexes:** DF-fed or coupled land (Fort 1 overshoots further); probably jabberer, pond grabber and spider cave giant (PENDING).
- **Same:** water, invasives, thieves.
- **Gained:** one route that ignores the layer cap and pause is gone, which fits "at the cap nothing new arrives".

### 4. Does it serve your aims?
- **Fewer hacks:** partly.
- **The tool controls outcomes:** no. FREQUENCY is open-loop (apex visits = odds × DF's picks + coupling's calls).
- **Naturalistic pacing:** no. Apexes overshoot where DF is generous and go missing where the draw dominates.
- The scheduler has the mirror flaw: it can add but never hold back. **Neither design meets R9 on both forts.**

### 5. Better route: one draw, apexes as ordinary members
1. **Lift the apex exclusion in `V7.DRAW.pick`.** The season's apex then comes under the layer clock, cap and pause. Keep coupling: it is the food-web link.
2. **Give the draw what water has:** `apex_max` 1 per layer plus a presence-aware weight (0 above target, boosted below). To hold DF back too, close the apex's entries while presence is above target; that is the existing pause lever, not a trim. Your 16 Oct "no new caps" ruling means this generalisation is your call.
3. **DF's own apex odds then matter little.** Keep the cap of 5.
4. **`roster apex off`**, keeping `decide`/`placeGroup` for invasives and thieves. In the caverns, keep the scheduler until the cavern draw is fixed (its key bug: 0 cavern draws in B2) and the stock question is settled. The cave dragon needs placement in any case.
5. **Fix the first-seen slot rule** (`castLadder` 11048-11062), so a season's apex (cave crocodile, wolf) is treated as an apex in that season.
6. **If fliers join,** give the flying pyramid a real A value.

Untested inference: with the draw rotating the cast, an apex would come about once per round (about 1.4-3.5 times a season on Fort 1). With stays of 2-6 weeks, presence stays high unless the limit in step 2 acts on presence.

### 6. Rig test that would settle it (not run)
**Setup:** Fort 1 (region6 24,11) and coast (29,42), fresh embarks, caverns breached, 5 reps per arm, spring + summer, probe every 2 days. Keep the **full** ledger (ledger.txt keeps only 300 lines).

**Arms:**
- **A:** today.
- **A′:** `roster apex off` only (shows what the scheduler actually adds).
- **B:** apexes as ladder level A, draw exclusion lifted.
- **C:** B plus `apex_max` 1 and apex entries closed above target.

**Measure:**
- apex presence against R9;
- apex arrivals by source (DF plain, DF after a coupling call, draw, placement);
- groups over cap;
- prey kills by apexes;
- cave dragon, jabberer and pond grabber seen.

**Separately:** FQ1/LPP1 and the cavern stock-against-FREQUENCY A/B (pickab, PENDING).

**Rig test that would settle it:** Fort 1 (region6 24,11) and coast (29,42), fresh embarks, caverns breached, 5 reps per arm, spring + summer, probe every 2 days, full ledger kept. Arms: A today; A' roster apex off; B apexes as ladder level A with the V7.DRAW apex exclusion lifted; C = B plus apex_max 1 and apex entries closed above target. Measure apex presence against R9, apex arrivals by source (DF plain, DF after coupling, draw, placement), groups over cap, prey kills by apexes, and cave dragon/jabberer/pond grabber seen. Separately: FQ1/LPP1 and the cavern stock-against-FREQUENCY A/B (pickab). Fix the cavern-draw key bug before any cavern arm.

<details><summary>Review and verification trail</summary>

- review: Wrong: 'Delete the scheduler and invasives and thieves stop.' The tool already has a switch, `roster apex off` (ROSTER.verb 12035, which sets R.apex.enabled). It stops only the apex loop: placeTick gates that loop on doApex (11765, 11777-11783), and the R36 invasive loop (11786-11792) and the thief loop (11797-11803) run either way. They stop only if ROSTER.apex.decide or placeGroup is deleted, and V7.DRAW.one (15945) also places through placeGroup.
- review: Overstated: 'you would lose the rare cavern apexes.' Today the apex cap lowers most cavern apexes. Jabberer and pond grabber have no FREQUENCY token, so they default to 50 (raws checked: POPULATION_NUMBER 15:30). Spider cave giant is FREQUENCY 20. All three are written 5 (ladder 9456-9459; SAVR_d1 'apex odds'). Ladder values would raise them (jabberer 8, pond grabber 32, spider cave giant 57). Stock: the B1/B2 ledgers show jabberer entries of 26, not 'lacking stock'. Only the cave dragon (2:5) and the spider cave giant (3:4) are stock-limited. Whether DF's cavern pick follows the higher FREQUENCY is the PENDING stock-weighting question.
- review: Corrected the cavern apex counts. There are seven B1/B2 runs, not five. Cave dragon: placed 3, DF 2. Jabberer: placed 4, DF 3. Pond grabber: placed 2, DF 0. Blind cave bear and molemarian came mostly from DF (B1 COAST: molemarian 10 DF waves).
- review: Corrected the cave crocodile 'natural experiment'. It is not '7 groups in autumn in each run, clustered on one day'. B1 PC_SAVR: 6 groups at 5 distinct arrival ticks on days 2-14 of a partial autumn. B2 P2_SAVR: 3 in autumn plus 4 in summer. The point still holds: it sits on the ladder at 8 (first met as MW in cavern1 summer, castLadder 11048-11062) and nothing apex-specific limits it. Added a second case: the voracious cave crawler (winter APX, on the ladder at 4). On the coast fort the wolf (winter APX) is on the ladder at 2 for the same reason.
- review: Fixed the water section. Fort 1 has NO water apex keys (status-end: 'apexes: land 4, flying 3, cavern 6'). Its curated water apexes are seated on the ladder as SILURIAN_JAEKELOPTERUS[MW]=3 and GIANT_ALLIGATOR[SH]=3, and the water draw treats them as level A through the curated list (V7.WAT.levelOf 7628) with apex_max=1 (956, 7847). So Fort 1's water is already a live instance of the proposal. Apex presence there was 73-91% in spring and summer, far over the scheduler's 20%. That shows an apex limit caps how many apexes, not how often.
- review: Promoted coupling from inference to code fact plus evidence. V7.GRP.coupleStart (5569) closes every other surface entry and opens only the called predators for up to 2 days, so DF's next wave can only be a called predator, whatever its FREQUENCY. The ledgers show apexes called and arriving 1-2 days later (B1 SAVR: arthropleura autumn 1, then scorpion day 2; triceratops autumn 7, then scorpion day 8; grasshopper summer 82, then T. rex day 84). This explains much of Fort 1's over-delivery against FREQUENCY share (9 apex waves observed v 2.65 expected in B1). Caveat added: only DF-sent prey calls (17379 skips resident groups, and drawn groups are resident, 11676).
- review: Corrected the coast numbers. B2 P2_COAST land arrivals were 38 draws, 12 DF, 3 placements (of 53), not 'about 44 of 53' draws. Added ladder values for the coast apexes (black bear 15, cougar 25; script in scratch C5-review/coast_ladder.py). Under the literal swap, expected DF-sent visits are about 1.2 black bear in spring and 0.4 cougar in summer, against 1 placement each today. So it is not 'mostly disappear': roughly the same in spring, less in summer.
- review: Corrected 'decide never looks at the pause'. That is true for apex and invasive placements. Thief placements skip a paused cavern (11724).
- review: Clarified 'caverns have no group-at-once limit for apexes'. One group per species excludes caverns (16204). The cavern cap (7 per depth) and the cavern pause still apply to DF's waves. What is missing is a per-species or per-apex limit.
- review: Reframed the fliers point. The drop to 1 follows from the flying pyramid's A=0, a number the comment at 9081-9082 says is 'shown for the record' because flying apexes had no scheduler target. It is a setting to choose, not a fundamental loss.
- review: Added: B2 Fort 1 land was also mostly draw-fed (spring 8 draws v 3 DF, summer 19 v 8), not 'DF-fed'. One recluse group stayed 41 days and alone gave 60% presence. Presence is driven by how long an apex stays at least as much as by how many waves come.
- review: Added a no-code rig arm: `roster apex off` keeps invasives and thieves running, and optionally `roster set apex_raw_cap 0` lets the raw FREQUENCY through. Added a harness note: ledger.txt keeps only the last 300 lines, so attributing arrivals to coupling calls needs the full ledger.
- review: Fixed the misquote of the pause rule. The ruling reads 'at the cap nothing new may arrive'.
- review: Noted that PLAN-v8.1 never mentions apexes. Leaving apexes out of the draw (15880) was an implementation choice, not a ruling, while R9 (apex on land 20-30% of the season) and R34 (drop the apex step, steer by placement) are rulings.
- verifier: Minor: 'drawn prey never call predators' holds for ground draws only. The coupling trigger is `(not grp.resident or grp.fly)` (around 17379), and V7.DRAW.one sets grp.fly on drawn fliers, so a drawn flying group can still start coupling.
- verifier: Added: the cavern draw is dead in 6dffef5 (key bug). 'Make apexes ordinary draw members' in the caverns therefore needs that fix first; its apex exclusion is also keyed wrongly there, though that has no effect while the draw finds nothing.

Code refs: sw-wt/plugin/scripts/seasonal-wildlife.lua:9063-9065 (ROSTER header: R34 apex out of the ladder); sw-wt/plugin/scripts/seasonal-wildlife.lua:9079-9085 (apex_odds, apex_raw_cap 5, pyramid; A 'shown for the record'); sw-wt/plugin/scripts/seasonal-wildlife.lua:9112-9115 (apex presence targets land 25/flying 0/water 20/cavern 70, cap_calm 1, cap_savage 2, residence); sw-wt/plugin/scripts/seasonal-wildlife.lua:9200 (ROSTER.LEVEL A slots); sw-wt/plugin/scripts/seasonal-wildlife.lua:9382-9474 (ROSTER.ladder; apex block 9444-9461 writes cap or nothing); sw-wt/plugin/scripts/seasonal-wildlife.lua:11034-11086 (ROSTER.castLadder; first-seen slot 11048-11062; apex_keys 11077); sw-wt/plugin/scripts/seasonal-wildlife.lua:11563-11574 (ROSTER.apex.entries: stock only, no closed-flag check); sw-wt/plugin/scripts/seasonal-wildlife.lua:11595-11688 (ROSTER.placeGroup; resident=true at 11676); sw-wt/plugin/scripts/seasonal-wildlife.lua:11691-11745 (ROSTER.apex.decide; thief cavePaused check 11724); sw-wt/plugin/scripts/seasonal-wildlife.lua:11762-11805 (ROSTER.placeTick: doApex 11765; invasive loop 11786-11792 and thief loop 11797-11803 not gated by apex.enabled); sw-wt/plugin/scripts/seasonal-wildlife.lua:12035 (ROSTER.verb: roster apex on|off); sw-wt/plugin/scripts/seasonal-wildlife.lua:5142-5146 (daily hook calls ROSTER.placeTick); sw-wt/plugin/scripts/seasonal-wildlife.lua:5569-5620 (V7.GRP.coupleStart: closes other surface entries, opens called predators, 2 days); sw-wt/plugin/scripts/seasonal-wildlife.lua:17377-17390 (coupling trigger: only non-resident DF land groups; ledger line 17385); sw-wt/plugin/scripts/seasonal-wildlife.lua:15871-15880 (V7.DRAW design comment: apexes stay with the scheduler); sw-wt/plugin/scripts/seasonal-wildlife.lua:15908-15943 (V7.DRAW.pick: apex exclusion 15911-15919, least seen then odds); sw-wt/plugin/scripts/seasonal-wildlife.lua:15945-15947 (V7.DRAW.one: coupling's called predators first, apexes still excluded); sw-wt/plugin/scripts/seasonal-wildlife.lua:15997-16024 (V7.DRAW.caveTick: cavern draw, P9); sw-wt/plugin/scripts/seasonal-wildlife.lua:16196-16216 (one group per species; 'Caverns are not included' 16204; presentRaces); sw-wt/plugin/scripts/seasonal-wildlife.lua:7399-7400 (ENGINE.weight: base = craw.frequency); sw-wt/plugin/scripts/seasonal-wildlife.lua:7628-7632 (V7.WAT.levelOf: curated list = level A); sw-wt/plugin/scripts/seasonal-wildlife.lua:7796-7860 (V7.WAT.mix: pyramid factor, apex_max 7847-7849; default apex_max=1 at 956); sw-wt/plugin/scripts/seasonal-wildlife.lua:1009, 1017, 1028-1030 (coupling on, cave_open_stock 30, one_per_species, single_source); DwarfCron/.claude/scratch/pacing/ladder/SAVR_d1.json + COAST.json via summarise.py (casts, ladder rows, apex odds; Fort 1 water apexes as MW/SH=3); DwarfCron/data/pacing/B1/PC_SAVR, B2/P2_SAVR, B1/PC_COAST, B2/P2_COAST, B1/PC_EVIL, B2/P2_EVIL, B2/P2_LAKE probe.jsonl (arrivals by source, presence); DwarfCron/data/pacing/B1/PC_SAVR/ledger.txt, B2/P2_SAVR/ledger.txt, B1/PC_COAST/ledger.txt (coupling calls of T. rex, scorpion, cougar, black bear; scheduler placements); DwarfCron/data/pacing/B1/PC_COAST/status-end.txt, B1/PC_SAVR/status-end.txt (apex keys per layer: Fort 1 has no water apexes); DwarfCron/data/eco-review/part2/USER-REVIEW-PART2.md:19,55 (R9 land 20-30%, R34); DwarfCron/data/eco-review/part1/D-frequency-figures.md:12-31 (desk: FREQUENCY works on apexes; do not drop the step, re-target it); DwarfCron/data/eco-report/open-items.json (ladder-drop-apx-step built untested; lp-separate-pool, apex-placement-stock-test, test-fq1-lpp1 at test stage); DF raws vanilla creature_next_underground.txt (CAVE_DRAGON POP 2:5 FREQ 5; JABBERER and POND_GRABBER POP 15:30, no FREQUENCY token = default 50) and creature_subterranean.txt (SPIDER_CAVE_GIANT FREQ 20 POP 3:4; CROCODILE_CAVE POP 10:20); memory: cavern-pick-stock-weighted.md (PENDING), pause-not-trim.md, beta-rulings-oct16.md; DwarfCron/.claude/scratch/sw-questions/C5/apex_on_ladder.py, C5-review/coast_ladder.py, C5-review/tally.py, C5-review/pres.py (thought-experiment and tally scripts)

</details>

## C6

> Assuming "Fort 1 · Savage marsh (region6 24,11; river + 11 ponds)", during Spring with a land-ground cap of 4, what proportion of the time will the next land-ground animal to be drawn onto the map NOT be a Giant weasel or Cretaceous colepiocephale?

**Short answer.** About 7 in 10. From the ladder alone 25% of picks would be neither giant weasel nor colepiocephale, but with the v8.1 draw (fewest animals seen first) the simulation gives 68%, and the B2 rig spring on this fort gave 8 of 11 (73%). For a single next arrival it depends on the moment: 25% at the very start of spring, 36-45% when one of the two is on the map, 100% when both are present or already ahead in this season's tally.

*Status: corrected · confidence medium · review verdict: minor fixes*

### Short answer
**About 7 in 10 of Fort 1's spring land-ground arrivals are neither a giant weasel nor a colepiocephale.**
- **Ladder alone:** 25%.
- **Code simulation:** 68%.
- **Rig, B2 spring on this fort:** 8 of 11 = 73%.

For **one** next arrival, it depends on the moment:
- 25% at the very start of spring;
- 36-45% when one of the two is on the map;
- 100% when both are on the map or both are ahead in this season's count.

### 1. What the ladder alone says
From `SAVR_d1.json`; the stored FREQUENCY equals the live FREQUENCY for every spring member.

| member | slot | FREQUENCY | mean group |
|---|---|---|---|
| giant weasel | ground prey | 44 | 1 |
| colepiocephale | grazer | 30 | 4 |
| rattlesnake | meso | 9 | 1 |
| giant slug | ground prey | 8 | 1 |
| triceratops man | sentient | 4 | 2 |
| platybelodon | grazer | 3 | 5 |
| giant coyote | meso | 1 | 6 |
| giant brown recluse | apex | 5 (capped) | 1 |

- Without the apex: 25 of 99 = **25%** neither.
- With it in DF's pick: 30 of 104 = **29%**.

That is panel 2b's picture. Even for DF's own waves it is an idealisation: in B1 (DF only) the coyote at odds 1 came in 2 of 12 spring waves.

### 2. What decides the next land arrival (`scripts/seasonal-wildlife.lua`, sw-wt 6dffef5, `groupsTick` around 17286)
1. **A DF wave held at the edge already takes a slot.** `ENGINE.count` (7515) counts every land group.
2. **Land pause.** At 4 of 4 it closes every land entry DF draws from. It reopens only at 2 (`V7.GRP.resumeAt` = cap − `pause_margin` 2; 15673, default 1038).
3. **One group per species** (`V7.GRP.speciesPause`, 16196+) closes a present species' entries. It is skipped while the land pause holds.
4. **Release** (17423-17449). When the land count is under 4 and the clock is due:
   - a waiting DF wave is let in first (`detachOldest`);
   - otherwise the tool draws (`V7.DRAW.one`; `groups.draw` is on by default, 1016).
5. **The draw ignores the pause.** `V7.DRAW.pick` (15908-15943) checks only stock > 0 (`ROSTER.apex.entries`, 11563), never whether the entry is closed.
6. **How the draw picks:**
   - it skips the apex and any species on the map;
   - it keeps the members with the **lowest season tally**, weighted by FREQUENCY among those;
   - the tally counts **animals** (`V7.TALLY.note`, 11269: every wild unit, once a season, by id). A colepio herd of 5 adds 5; a weasel adds 1.
7. **Coupling** (on, 1317). It starts on a fresh DF wave, never under the land pause (17377). For up to 2 days the draw takes only that prey's predators (`only`, 15946).
8. **Apex scheduler** (`ROSTER.apex.decide`, 11691). Land target 25%, about 1.8% a day placement chance while under target. It ignores the land cap, and a placed apex then counts toward it.

**At a cap of 4:** DF is shut out at 4 and stays shut at 3. At 3 the draw refills the 4th slot when the clock is due. DF gets another wave only if two groups leave before the next draw.

**The rig matches this** (B2 P2_SAVR, same code, same cast):
- The land count sat at 3-4 with the pause on from day 19 to day 84.
- The only DF land waves came on days 17-19 (rattlesnake, colepio ×5, recluse).
- Every later arrival was a tool draw.

### 3. The chance for the next arrival, by moment
**Tool draw (most of the season):**

| moment | P(neither) |
|---|---|
| start of spring, nothing seen, nobody on the map | 25/99 = **25%** |
| weasel on the map (only it seen) | 25/55 = **45%** |
| colepio on the map (only it seen) | 25/69 = **36%** |
| both on the map, or both already seen and others not | **100%** |
| after one full round, nobody on the map (lowest tally: weasel, rattlesnake, slug at 1 each) | 17/61 = **28%** |
| same moment, weasel on the map | **100%** |

After one round the tally reads roughly: weasel 1, rattlesnake 1, slug 1, triceratops man 2, colepio 4, platybelodon 5, coyote 6. Solitary animals come back first; herds wait.

**A DF wave** (only at 2 or fewer groups, or before the first fill; assumes all entries on one tile):

| moment | P(neither) |
|---|---|
| nobody on the map | 30/104 = **29%** |
| weasel on the map | 30/60 = **50%** |
| colepio on the map | 30/74 = **41%** |

### 4. Over the whole spring
**Simulation** (`DwarfCron/.claude/scratch/sw-questions/c6/sim.py`):
- **Draw on:** about 16.5 land arrivals a spring, **68%** neither.
  - Group shares: weasel 21-23%, rattlesnake about 20%, slug about 19%, triceratops man about 14%, colepio 9-10%, platybelodon 7%, coyote 6%, apex about 2%.
  - By arrival: the 1st is about 25% neither; the 3rd to 7th 61-100%; the 8th, which starts round two, 22-52%.
- **Draw off (DF only):** 52-54% neither; one group per species already keeps the two out while they are present.
- **Not modelled:** coupling, the scheduler, the real release clock.

**Rig:**
- **B2 (draw on), spring days 15-84:** weasel 2, colepio 1, rattlesnake 1, recluse 1, slug 2, platybelodon 1, triceratops man 2, coyote 1 = **8 of 11 (73%)**. The K21 save failed and the run replayed from K14.
- **B1 (987cffc, no draw), by DF wave:** weasel 3, colepio 1, rattlesnake 2, recluse 3, coyote 2, triceratops man 1 = **8 of 12 (67%)**. The recluse took 3 of 12 against about 9% expected; with so few waves that is not significant.

### 5. Caveats
- **Entry tiles** were assumed equal (`single_source`, `V7.SRC.chosen`, 3349). DF weights site tiles far above neighbours, so the DF-wave odds could shift. Not checkable without the rig.
- **Coupling's predator links** are not in the dump.
- **The tally counts every wild animal.** At B2 day 76 there were 20 wild land animals but only 12 in tracked groups, so hidden tally entries can reorder picks. A dead animal returns no stock.
- **Start of spring:** winter groups count toward the cap until they leave (`leave_grace_days` 7).

### 6. What this means for your aims
- **Diversity:** the draw serves it well. All seven members come round within about the first 7 draws. FREQUENCY alone would rarely pick the coyote (B1 still saw it twice from DF), but the draw guarantees it a turn.
- **The ladder matters less than panel 2b suggests.** Within a season, the lowest-tally tier decides most picks. Panel 2b should say "least seen" counts animals.
- **Ecology: it works against the pyramid** (inference from the simulation × group sizes). Counting animals evens out animals per species: about 58% prey / 42% predators and sentient in spring, against about 91% prey in the ladder's own shares.
- **Better alternative (tuning existing code, not a new cap):**
  1. Count the tally in **groups**, so a herd is one visit; or
  2. Make least-seen a **soft weight** (ladder odds ÷ (1 + seen)).

  Either keeps the cast coming round while the ladder still shapes how often each member returns. A level-first pick by pyramid deficit (C1) is a third option. Which matters more, every species seen or the pyramid's proportions, is your call.

### 7. Rig test that would settle it (not run)
1. Embark P2_SAVR fresh at spring day 1 (region6 24,11, 3x3).
2. Run the B2 probe through a full spring: 3-5 reps with the draw on, 3-5 with `groups draw off`.
3. For every land arrival, log its source, species and size, plus at that moment:
   - the season tally;
   - which species are on the map;
   - each member's open entry (stock and tile).
4. Read the fort's cast predator links once, for coupling.

Compare the "neither" share (predicted about 70% with the draw on, about 53% off) and each pick against the moment odds above. The entry tiles also settle whether DF's waves here follow FREQUENCY.

**Rig test that would settle it:** Embark P2_SAVR fresh at spring day 1 (region6 24,11, 3x3). Full spring, 3-5 reps with the draw on and 3-5 with it off. For each land arrival log source, species and size, plus at that moment the season tally, the species on the map, and each spring member's open entry (stock and tile). Read the cast predator links once for coupling. Compare the 'neither' share (predicted about 70% on, about 53% off) and check each pick against the moment odds.

<details><summary>Review and verification trail</summary>

- review: B1 rig count corrected. The original said 9 of 14 (64%), but it counted colepio as 2 and coyote as 3, which matches neither way of counting. B1 ran 987cffc, which is before the P12 join fix (6965f34), so one DF wave could be filed as several groups. B1/PC_SAVR/probe.jsonl lists 15 group records in spring: colepio 2295, 2296 and 2297 are one wave, and coyote 2407 and 2408 are one wave. Counted by wave that is 8 of 12 (67%); counted by record it is 9 of 15 (60%).
- review: Apex share in the simulation corrected from '~2-7%' to 1.5-2.4% with the draw on (sim.py output, rerun) and about 9% with the draw off. The simulation never models the apex scheduler (ROSTER.apex.decide), so it is a floor.
- review: Added: a DF wave counts toward the land cap as soon as it is waiting at the edge. ENGINE.count (seasonal-wildlife.lua:7515) counts every non-seeded land group, held or released. So one DF wave at 3 groups fills the 4th slot and turns the pause on. That is why the rig went 2 -> 3 -> 4 on days 17-19.
- review: Added an ecology finding the original only hinted at (an inference from the simulation's group shares x mean group sizes from the ladder dump). Counting least-seen by animals leaves prey at about 58% of spring ground animals and predators plus the sentient at about 42%. The ladder's own spring share column (SAVR_d1 'share') makes prey about 91%. So the draw roughly quadruples the predator share against what the ladder intends.
- review: Sharpened the day-76 puzzle with data. The probe's wild land count was 20 at day 76, against 12 animals in tracked groups, so the tally sees wild animals outside the groups. The rattlesnake's group vanished after about 6 days (day 17 to day 23), which suggests a death: no refund, and the entry may be empty. Both readings are marked as inference.
- review: Added a rig caveat: B2 P2_SAVR's spring was not one unbroken run. run.log shows the K21 save failed, the run reloaded K14 and replayed from chunk 15.
- review: Added a code caveat: an apex the scheduler places counts in the land count and ignores the cap (decide checks only the apex cap of 2). The simulation leaves this out.
- review: Confirmed against the code and left as they were: draw gated on nLand < cap and the clock (17423-17449, draw at 17437); detachOldest first; the pause reopens at cap - pause_margin (15673, default 2 at line 1038); V7.DRAW.pick takes the lowest tally, then FREQUENCY weights, skips the apex and present species, and checks stock only (11563); V7.TALLY.note counts wild units by id (11269); coupling never starts under the land pause (17377); apex hazard 1 - exp(-0.25/(0.75*21500)*1200) = 1.84% a day; dawn pattern not default (PATTERN.name defaults to 'steady'). Simulation numbers reproduced: 67.6/68.1/68.3% with the draw on, 51.7/53.6% with it off.
- review: Confirmed the B2 tally: 11 spring land arrivals, 8 neither (73%); DF waves only on days 17-19; land at 3-4 with the pause on from day 19 to day 84.
- verifier: 'The coyote, at odds 1, would almost never come from DF waves' is contradicted by B1 on this fort. DF sent the giant coyote 2 times in 12 spring waves (about 17%, against 1% predicted). The DF-wave odds tables are an idealisation; B1 shows DF's waves here deviate a lot from FREQUENCY.
- verifier: Everything else checked against the code: the 25/99, 45%, 36% and 28% draw odds; resumeAt = cap − 2; ENGINE.count including held waves; the draw ignoring closed entries; the tally counting animals; about 1.8% a day apex hazard; and B2 spring 8 of 11 'neither'.

Code refs: sw-wt/plugin/scripts/seasonal-wildlife.lua:15871-15943 (V7.DRAW comment, V7.DRAW.members, V7.DRAW.pick: least tally then ladder odds, skips apex and present species); sw-wt/plugin/scripts/seasonal-wildlife.lua:15945-15965 (V7.DRAW.one: coupling 'only' predators first, ENGINE.groupSize capped by stock); sw-wt/plugin/scripts/seasonal-wildlife.lua:11262-11296 (V7.TALLY.held / V7.TALLY.note: every wild unit counted once a season by id, per creature token); sw-wt/plugin/scripts/seasonal-wildlife.lua:11563-11573 (ROSTER.apex.entries: stock > 0 only, extinct flag not checked); sw-wt/plugin/scripts/seasonal-wildlife.lua:7515-7523 (ENGINE.count: held and released DF waves both count toward the land cap); sw-wt/plugin/scripts/seasonal-wildlife.lua:17286 (groupsTick), 17377 (coupling never starts under the land pause), 17412-17418 (land pause then species pause), 17423-17449 (detachOldest first, else V7.DRAW.one at 17437); sw-wt/plugin/scripts/seasonal-wildlife.lua:15673 (V7.GRP.resumeAt = cap - pause_margin), 15735-15780 (V7.GRP.landPause); sw-wt/plugin/scripts/seasonal-wildlife.lua:16210-16300 (V7.GRP.presentRaces, V7.GRP.speciesPause); sw-wt/plugin/scripts/seasonal-wildlife.lua:1009, 1016, 1026, 1027-1038, 1317 (coupling, draw=true, leave_grace_days=7, land_pause, one_per_species, single_source, pause_margin=2; coupling unparked v8); sw-wt/plugin/scripts/seasonal-wildlife.lua:5414-5482 (discoverGroups, releaseGroup, detachOldest); sw-wt/plugin/scripts/seasonal-wildlife.lua:11691-11745 (ROSTER.apex.decide: hazard P/((1-P)R), apex cap only), 9112-9113 (apex presence land 25, cap_savage 2, residence 21500); sw-wt/plugin/scripts/seasonal-wildlife.lua:3241-3256, 3349-3380 (V7.SRC one entry per species, anchor/site tile score); sw-wt/plugin/scripts/seasonal-wildlife.lua:13210, 13360 (PATTERN.name defaults to 'steady'; dawn table not active by default); DwarfCron/.claude/scratch/pacing/ladder/SAVR_d1.json + summarise.py (spring ground cast, land ladder, stored = live, share column); DwarfCron/data/pacing/B2/P2_SAVR/probe.jsonl, run.log (K14 reload/replay), embark.log, code.txt (v8.1-pacing@6dffef5), ledger.txt (draws at 3 of 4 under the pause); DwarfCron/data/pacing/B1/PC_SAVR/probe.jsonl, code.txt (987cffc, no V7.DRAW); sw-wt/plugin git log 987cffc..6dffef5 (P12 join fix 6965f34); DwarfCron/.claude/scratch/sw-questions/c6/sim.py (Monte Carlo, rerun in review); memory: df-wave-pick-per-entry.md, cavern-pick-stock-weighted.md, pause-not-trim.md, beta-rulings-oct16.md

</details>

# D. Building the casts

*the cast builder: apex pick, food-web growth weights, mass weighting, cavern food-web guarantee, bonus predator, seasons per species, unfilled slots, and biome x season species richness*

### What these seven questions are after
You are auditing the cast builder end to end. The question running through all seven: does each step earn its place, and do the steps together give believable, varied, seasonal food webs, or are they stacked fixes that fight each other?

The code answers it fairly clearly:

1. **The individual weights are not the problem.** x1.5 and x3 are the same pack edge used in two seats (D1). The √(group mass) in the apex draw does what you meant: it favours big hunters, and the divisor does nothing (D2).
2. **What really shapes outcomes is structure, not weights:**
   - **Seat eligibility.** Apex-class species keep a meso seat and can be the seed (D1). That gives two top predators in one cast. They never link, because nothing eats an apex-class species. The ladder and the apex scheduler then give each species a single role for the whole year.
   - **Slot pressure.** Seats a year ÷ the species that fit each slot (D5, D6, D7). Too many seats for the candidates gives all-year species (albatross, tapir and elephant, cavern 1) and unfilled seats. Many candidates give one random season each.
3. **Two after-the-fact steps are nearly dormant.**
   - The cavern food-web guarantee never fires today (D3).
   - The bonus predator fires rarely and supplies only 1-5% of the big theropods (D4).
   - A chance roll, a cap or a flip on either would add randomness without moving the outcome you care about.
4. **Seasonality is not in DF's raws.** Only 23 creatures are tagged (D7). The tool's seasonal turnover is a random draw, kept for the fort's life. It is varied but not naturalistic.
5. **Visibility gaps.** Unfilled notes, guarantee and bonus counts, and candidate counts are stored but barely shown, so these questions were hard to answer from the UI.

### Combined recommendation
Everything below is offered; nothing is built.

- **Roles first (D1, with D2 and D4).** Pick one:
  - (A) A species that can win a cast's apex draw takes only the apex seat in that cast.
  - (B) The ladder and the scheduler read each species' role per season.

  Either one removes the double-top-predator casts and the scheduler mismatch. For the size of apexes, add a size-exponent setting and an apex-only giant multiplier as tool controls. Do not flip the ratio.
- **Size slots to their candidates (D5, D6, D7).** Set each season's want from the candidate count. Add a *soft* two-season cap: filter capped species out, never weight them to 0, because a zero weight stops the whole cast. Log every forced repeat with its reason. Break seat ties toward the slot with the fewest other candidates (this fixes the cavern 1 swimmer).
- **Retire the silent fixes (D3, D4).** Turn the cavern guarantee into a visible warning, and correct the diagram and Controls wording. Either remove the bonus seat or make it prefer plausible hunters. Do not add a chance roll.
- **Seasonality is your ruling (D7).** Choose between maximum turnover and a resident core plus seasonal visitors. If visitors: per-season slot tables and a small seasonal-habits table (migrant waterbirds, hibernators, insects), applied only where biology has a season.
- **Make it visible.** Add a Seasons tab in the Food Web Explorer: richness by biome × season, season strips, and a slot-pressure chart. Show candidate counts and unfilled reasons by cause in the window and the page. Add a one-line build summary.
- **Test economy.** One offline `NR.year` sweep can cover the D1 rules A/B, the D2 exponent arms, the D5 cap arms and the D7 slot-table arms. The rig is only needed for arrivals. Note that the pacing forts share site 266 in one world, so their cavern casts are one sample. Vary `cast.salt` or use different worlds before trusting cavern comparisons.

<details><summary>Cross-answer issues the verifier resolved</summary>

- Do the cavern casts match across the three forts? D5 said the three ladder dumps have 'identical' cavern casts. D3 said they are identical in 10 of 12 cavern-seasons, and D7 said SAVR and LAKE3 are identical while COAST differs in 2 seats. I diffed the dumps. SAVR_d1 and LAKE3 match in all 12 cavern-seasons. COAST differs only in the sentient seat in 2 of them: cavern 2 spring (blind cave ogre instead of cave swallow man) and cavern 3 autumn (the reverse). D5 is corrected. All three dumps report site 266, year 100, so they are one cavern sample, not three.
- Ground and flying layers. D5 said no ground or flying species reaches 3+ seasons and that a cap of two changes nothing on those layers. D7's desk prototype shows thin biomes where ground species hold 3-4 seasons: tundra, glacier, and tropical moist forest, where only tapir and elephant fit the 2-seat grazer slot. Both are right for their samples. D5's claim holds only for forts with long candidate lists, and D5 is corrected to say so. A cap of two would empty grazer seats in a tropical moist forest.
- Ponds. D7's prototype gave ponds 5 candidates (2 in winter). D5's real probe (V8E_A1/A2) has 15 candidates (12 in winter). The engine's pond list admits any non-vermin species with lake, river or pool in its raws (seasonal-wildlife.lua:10091, FP.freshRaw): salmon, steelhead, shad, beaver, mink, river otter, platypus. So the prototype undercounts ponds, and D7 is corrected. Separately, D5 said pond slots fill 'even with a cap of one'. With 3 meso candidates for 4 meso seats a year, a cap of one would leave one meso seat empty. A cap of two fills everything, so D5's conclusion stands with corrected wording.
- D5's example of a species counted twice in one season named the bugbat on COAST. The bugbat is in cavern 1 spring and summer and cavern 2 winter, never two layers in the same season. The cave crocodile (cavern 1 and cavern 2 in autumn) and the giant cave toad (cavern 1 and cavern 3 in winter) are correct examples. Corrected.
- D1, D4 and the bonus seat. D4 said the bonus eater goes into 'its meso or apex slot' without saying which. The code takes the first of meso/apex in the species' slot list (23078), and slotsFor lists apex before meso for any apex-class species (10215-10220). So a T. rex or giant arachnid bonus eater opens a second apex seat, as D1 says. Added to D4.
- The repeat weight. D1 said x0.01 applies per cast holding the species 'in any seat'. A sentient seat is counted apart (usedKey, 22840; commit 6c79f93, user 17 Oct), and the apex draw always uses the plain key. Minor correction to D1. D5 and D7 are consistent with the code.
- D1 and D2 together. Nothing eats an apex-tier species: apexBar (22635) applies when the prey is apex-tier on any layer it lives on, and forcedDiet refuses it unless the eater has a sentients diet that names the prey's layer (22652-22655). So two apex-class species seated in one cast (D1's 'crowding', D2's flip, D4's bonus apex) never get a feeding link between them, and the tool writes no relation for them in DF. The answers agree; I made it explicit.
- D3, D5 and D6 on the unfilled-slot reasons. All three find the two reasons ('none in season', 'all candidates used in other slots') too coarse. D6 notes the second can be misleading. D5 notes a cap would get the wrong label. D3 notes that the cavern guarantee, which runs after the note, never contradicts it. The three agree, and I checked against 23037-23042.
- Where the giant predators come from. D2, D4 and D1 name the same sources: the apex draw's sqrt(group mass), the size-ranked seed (NR.hvSet), and apex-class species allowed into mid seats. The bonus seat is a small share of them (D4: 1-5% of big-theropod seats). The recommendations agree: tune the apex size weight or the apex-only giant multiplier, and the seed's eligibility. A chance roll on the bonus, or flipping the ratio, would not do it.

</details>

## D1

> If "Weights: pack predators x3" is applied at foodweb growth, but apex predators were already chosen using "1.5 for a pack hunter" then what is the purpose of each of these two weights in combination? Is the selected apex predator slotted into the foodweb at all? Is it replaced by another predator chosen at foodweb growth? More generally speaking, are the weights at cast building step 1 Apex replaced by, in conflict with, synergetic with the weights at cast building step 3 Grow the food web? Does one over write the other? Do they both write and end up crowding the cast? Should 1:Apex and 3:Grow be merged?

**Short answer.** The two weights don't conflict or overwrite each other. Step 1 fills the apex seat with x1.5 on top of group size, and growth (x3) can't fill that seat. Both give a pack hunter about a x3 edge. Crowding comes from apex-class species keeping a mid-predator seat and being allowed as the seed, and the FREQUENCY ladder then gives them one role for the whole year. Don't merge the steps. Either restrict apex-draw-eligible species to the apex seat (A) or give each species a role per season (B).

*Status: corrected · confidence high · review verdict: minor fixes*

### Short answers
- **Does one weight overwrite the other?** No. Step 1 (apex draw) fills the apex seat, and step 3 (growth) cannot fill it: `room()` skips `apex` (seasonal-wildlife.lua:22899-22903).
- **Is the drawn apex in the food web?** Yes. It is a member from the start, and every growth round looks for links to any member, the apex included (22989-23011). Nothing can eat an apex-class species (`apexBar`, 22635), so the apex only gets links as an eater.
- **Is it replaced by a predator chosen during growth?** Never as apex. But a *second* apex-class predator can join the same cast in a mid-predator seat, through growth or as the seed. The bonus predator for giant herbivores can open a second *apex* seat, because the bonus takes the first of apex/meso in the eater's slot list (23078) and apex comes first (10215-10220). The cavern web guarantee has the same code path, but it never fires today (D3).
- **Do the two weights conflict?** No. It is one weight function used twice, and both uses give a pack hunter about a x3 edge (below).
- **Do they crowd the cast?** Sometimes, but x3 is not the main cause. Eligibility and the seed are.
- **Should steps 1 and 3 be merged?** No. Change the rule for which seats apex-class species may hold.

"Apex-class" below means a species that can hold the apex seat on that layer (`ROSTER.FP.apexTier`, 10183). That covers 'local' apexes such as the coyote, lynx and wolverine (`REAL_APEX`, 780-794).

### 1. What the code does (sw-wt/plugin @ 6dffef5)
**One weight function**, `weight(x, pack, apexDraw)` in `NR.cast` (22876-22883). It multiplies:
- x `pack` for a non-BENIGN predator whose group can exceed 1 (3 by default);
- x0.01 for each cast already holding the species, on any layer or season. A sentient seat is counted apart (`usedKey`, 22840; user 17 Oct);
- x0.2 for giants and x0.1 for animal people;
- the cavern depth fit.

`pack=3` comes from `ROSTER.CAST_DEF` (10339). `apex_pack=1.5` comes from `V7.RULES.roster.APEX_PACK` (694, 10342).

**Step 1, the apex draw (22905-22932).**
- Eligible: candidates whose first slot is `apex`, at the true tier if one exists, otherwise the local tier.
- Weight: `sqrt(group mass ÷ largest) × weight(x, 1.5, true)`. For a pack hunter, group mass = adult size × mean pack size (22911-22915).
- So x1.5 *replaces* x3 here; it does not stack. You ruled this on 13 Oct (commit 7329f22: "the cast-wide pick keeps x3"; group size already counts the pack).

**Step 3, growth (22989-23036).**
- Each round it takes the free candidates that eat, or are eaten by, any member.
- It keeps those that fit the slot with the most room left, then picks among them by `weight(x)` with x3.
- The room rule decides first. The weight only chooses among species competing for the same open slot.

**The two weights, side by side.**
- Apex draw: a wolf pack (mean 5) against a lone hunter of the same adult size gets √5 × 1.5 ≈ **x3.4**.
- Growth: **x3**.
- So x1.5 did not weaken the pack edge. It stopped the pack being counted twice (√5 × 3 ≈ x6.7).
- Purpose of x1.5: choose which big hunter heads the cast by what it brings onto the map at once.
- Purpose of x3: favour pack hunters in mid seats, because DF kills follow group size (ECO CAL, 30 Sep).
- Same aim, two seats.

### 2. Where the crowding comes from
- **Apex-class species keep a mid seat.** `slotsFor` gives an apex-class predator `{apex, meso}` on the ground and in the caverns (10208-10220). Losing the apex draw leaves it eligible for meso. This is deliberate (castsim design.py:550, "eligible: can take meso").
- **The seed admits them.** The seed comes from the top 10% of free candidates by pet value or adult size (`NR.hvSet`, 22841-22858). Sentients and animal people are excluded; apex-class species are not (22936-22941). In the coast fort the tiger was the autumn seed and the grizzly the spring seed.
- **The repeat weight rotates the apex seat.** It is shared by every step and layer (23114). Once the wolf heads one season it drops to 1% in later apex draws, which is why the four seasons of a layer get different apexes. The other side: a species that headed one season is still eligible as a mid predator in another, so two roles in one year is the expected result.
- **x3 is a minor factor.** These are my simplified simulations: all candidates treated as linked, the same list every season (scratch d1_growth_sim.py, D1-review/year_sim*.py).

| Setting | x3 | x1 |
|---|---|---|
| One cast: a second apex-class species besides the apex | 70% | 60% |
| Year, small candidate list: casts with 2+ apex-class | 40% | 40% |
| Year, larger list: casts with 2+ apex-class | 15% | 14% |
| Year, larger list: apex-class species with two roles | 0.44 | 0.37 |

Barring apex-class species from mid seats takes the last two to 0. Read the numbers for direction, not exact values.

**Real forts** (.claude/scratch/pacing/ladder/; I checked these):
- **Coast fort, ground.**
  - Autumn: black bear apex, with tiger (seed) and wolf as meso.
  - Winter: wolf apex, with coyote meso. The coyote is apex-class at the local tier.
  - Spring and summer: grizzly as meso.
- **Savage marsh fort (Fort 1), ground.** The apex seats went to giant bugs and the T. rex. Black bear, wolf and giant coyote came in as meso (ladder ML 1).
- **Caverns (the same in both forts).**
  - The jabberer is apex in cavern 3 spring and meso in autumn.
  - The voracious cave crawler is the reverse.
  - The cave crocodile is a swimmer in cavern 1 summer and apex there in autumn and winter.

### 3. What breaks: the ladder keeps one role per species
- **One row per species.** `ROSTER.castLadder` (11034-11085) takes each species once, at its **first** seat in a fixed order: ground, flying, ocean, fresh, then caverns 1-3, spring to winter within each layer. That seat's code becomes its only ladder row. It also decides whether the species goes to the apex scheduler (`apex_keys`, 11077). Which seat it holds at that first appearance comes from the random build.
- **The scheduler ignores the seat.** `ROSTER.apex.decide` (11691-11745) places a listed species in any season it is cast, whatever seat it holds then (`ROSTER.wants`, `castDepths`, 3216-3240).
- **APX species keep their raw FREQUENCY**, capped at 5 (9446-9460).
- **Coast fort, winter.**
  - The wolf's first seat was autumn meso, so its row is ML at FREQUENCY 2. The low value comes from its pack-size divisor of 5.
  - The land apex list holds only the black bear and the cougar, and neither is in the winter cast.
  - Inference: winter gets no scheduled apex (the reason should read "no apex in season with stock"). The wolf arrives only as DF waves at FREQUENCY 2.
- **Caverns, winter.**
  - Cavern 1's apex (the crocodile) is MW 8 on the ladder, and cavern 3's apex (the voracious crawler) is ML 4.
  - The only cavern species the scheduler can place is the giant cave spider. It is apex in cavern 2 but meso in cavern 3.
- **Effect.** On the ground this mostly confuses roles. In the caverns, where the apex target is 70%, the scheduler places the wrong species.

### 4. Merge 1 and 3? No
Step 1 picks the head of the web by size. Step 3 grows the web by links, with room first. A single merged draw would either let mid-sized species win the apex seat or squeeze small mid predators out of growth.

Better options (pick one):
- **(A) A species that can win this cast's apex draw takes only the apex seat.** Bar it from mid seats and the seed in that cast. "Can win" means the same tier as the draw (`tierUse`). A blanket bar would also remove the coyote, lynx and wolverine, which never win where a true apex exists.
  - Result: a clean pyramid and no dual roles.
  - Cost: on savage or giant-heavy forts, wolves and bears may not appear at all in a year.
- **(B) Keep both kinds of seat, but give each species a role per season.** The seasons where it heads the cast go to the scheduler; its meso seasons get a ladder FREQUENCY.
  - Inference: this is feasible because `CAVERN.apply` already writes FREQUENCY at each season change (4648-4660).
  - Limit: a species on two layers still shares one raw FREQUENCY.
- **Not recommended:** damping x3 for apex-class species. It barely changes crowding.
- **Diagram:** panel 2 should say that species that lose the apex draw stay eligible for meso seats and the seed, and that x1.5 on top of group size is about the same pack edge as x3.

### 5. What would settle it
- **Offline:** run `NR.year` over many site seeds and biomes under today's rule, rule A and rule B. Count:
  - casts with 2+ apex-class species;
  - species holding two roles on one layer in a year;
  - under A, real apexes that never appear on savage forts.
- **Rig, for the arrival effect only:** coast fort, winter. Read `roster apex now` and count wolf waves and groups, against a copy whose wolf row is APX.

**Rig test that would settle it:** Cast side offline: NR.year over many seeds and biomes under today's rule, rule A and rule B; count casts with 2+ apex-class species, dual-role species, and real apexes never seen under A. Rig only for arrivals: coast fort through winter (wolf heads the cast, its ladder row is ML 2); read `roster apex now` and count wolf waves and groups, against a copy whose wolf row is APX.

<details><summary>Review and verification trail</summary>

- review: Corrected the claim that the wolf is in 'about 3 of 4' forest ground casts. The earlier sim (d1_growth_sim.py) models one cast with no reuse penalty. Across a year the shared x0.01 reuse counter (NR.cast weight, seasonal-wildlife.lua:22879) caps this. A year-level re-run (scratch/sw-questions/D1-review/year_sim.py, year_sim_big.py) puts the wolf in 2 of 4 seasons in 68-95% of years, typically once as apex and once as mid predator.
- review: Downgraded x3 as the cause of crowding. Both sims show x3 against x1 changes little: one cast 70% v 60% with a second apex-class species; per year 40% v 40% (small candidate list) and 15% v 14% (larger list). The real drivers are that slotsFor gives an apex-class species {apex, meso} (10218-10220) and that the seed admits it (22940). So option (a), damping x3 to x1.5 for apex-class species, would barely help, and it is removed as a fix.
- review: Added the mechanism behind dual roles. The x0.01 reuse counter is shared across steps and layers (22879, 23114). Panel 2 itself says it rotates the apex seat so each season gets a different head. A species that heads one season is then still eligible for a mid seat in another. Dual roles follow from rotation plus meso eligibility.
- review: Added that the two pack weights deliver about the same edge. In the apex draw a wolf pack's mean of 5 enters through sqrt(group mass), which is x2.24, and then the x1.5 is applied: about x3.4 against a same-size loner (22911-22921). Growth gives x3. They are not in conflict; the 13 Oct x1.5 just avoids counting the pack twice over.
- review: Coyote (and lynx, wolverine) are apex-class at the 'local' tier (REAL_APEX, 780-794). Where a true apex exists they can never win the apex draw (22908-22910), yet apexBar still keeps them from being prey (22634). A blanket 'bar apex-class from mid seats' would erase them, so the bar is redefined as 'eligible for this cast's apex draw'.
- review: Fixed the ladder detail. The wolf's FREQUENCY 2 comes from its group divisor x5 (scale 0.733), not the 0.25 size floor; the tiger and grizzly sit on the floor. The dump's 'live 5' is the raw value out of season. CAVERN.apply writes the ladder value per season (4648-4660). APX-coded species get no ladder value and keep their raw FREQUENCY (COAST: bear and cougar 'raw 5'), so in seasons where they sit in a mid seat they arrive as DF waves at raw odds and can also be scheduled.
- review: Added evidence that the apex scheduler is live on the rig forts: B2/P2_COAST/status-end.txt reads 'apex scheduler on ... land 2 (target 25%) ... cavern 6 (target 70%)', and the B1 ledgers show cavern apex placements.
- review: Added that NR.year builds the casts in a shuffled layer-season order (23151-23164), while castLadder picks the 'first seat' in a fixed ground-to-cavern, spring-to-winter order (11038-11061). Which role a species keeps on the ladder is therefore arbitrary with respect to how it was seated.
- review: Confirmed as accurate: room() excludes the apex slot (22899-22903); the apex is a growth anchor; x1.5 replaces x3 in the apex draw rather than stacking; 7329f22 message; reuse key shared by apex and mid seats; bonus predator and cavern guarantee can add a second apex seat (23063, 23078); one ladder row per species (11034-11085); ROSTER.apex.decide uses wants/castDepths regardless of seat (11691-11745, 3216-3240); COAST and SAVR_d1 cast contents and ladder rows.
- verifier: The x0.01 repeat weight counts a sentient seat apart (usedKey, seasonal-wildlife.lua:22840; commit 6c79f93), so it is not literally 'any seat'.
- verifier: The web guarantee's route to a second apex seat exists in code but never fires on current casts (see D3); I kept it only as a code path.
- verifier: Clarified that the ladder role is the species' seat at its first appearance in a fixed layer/season order. That order is deterministic, but which seat it holds there is a random result of the build.

Code refs: sw-wt/plugin/scripts/seasonal-wildlife.lua:22876-22883 (NR.cast weight); sw-wt/plugin/scripts/seasonal-wildlife.lua:22885-22892 (pick); sw-wt/plugin/scripts/seasonal-wildlife.lua:22899-22903 (room excludes apex); sw-wt/plugin/scripts/seasonal-wildlife.lua:22905-22932 (apex draw, gsize, apex_pack); sw-wt/plugin/scripts/seasonal-wildlife.lua:22934-22941 (seed: apex-class not excluded); sw-wt/plugin/scripts/seasonal-wildlife.lua:22841-22858 (NR.hvSet top 10% pet/size); sw-wt/plugin/scripts/seasonal-wildlife.lua:22989-23036 (growth: linked, room-first, weight pick); sw-wt/plugin/scripts/seasonal-wildlife.lua:23044-23086 (cavern guarantee, bonus predator: apex-first slot); sw-wt/plugin/scripts/seasonal-wildlife.lua:23114 (shared reuse counter); sw-wt/plugin/scripts/seasonal-wildlife.lua:23151-23164 (NR.year shuffled build order); sw-wt/plugin/scripts/seasonal-wildlife.lua:22634 (apexBar: apex-capable never prey); sw-wt/plugin/scripts/seasonal-wildlife.lua:22800-22830 (NR.apexOn: apex = apex on any layer); sw-wt/plugin/scripts/seasonal-wildlife.lua:780-794 (REAL_APEX: COYOTE/LYNX/WOLVERINE ground local); sw-wt/plugin/scripts/seasonal-wildlife.lua:10183-10220 (ROSTER.FP.apexTier, slotsFor {apex, meso}); sw-wt/plugin/scripts/seasonal-wildlife.lua:10339-10342, 23350-23353, 694 (pack 3, apex_pack 1.5); sw-wt/plugin/scripts/seasonal-wildlife.lua:11034-11085 (ROSTER.castLadder first seat, apex_keys); sw-wt/plugin/scripts/seasonal-wildlife.lua:11691-11745, 11761-11785 (ROSTER.apex.decide, placeTick); sw-wt/plugin/scripts/seasonal-wildlife.lua:3216-3240 (ROSTER.wants, castDepths); sw-wt/plugin/scripts/seasonal-wildlife.lua:4648-4660 (CAVERN.apply per season, cfg.odds); sw-wt/plugin/scripts/seasonal-wildlife.lua:9112-9114 (apex scheduler defaults: on, land 25%, cavern 70%); sw-wt/plugin git 7329f22 (13 Oct APEX_PACK 1.5; cast-wide pick keeps x3); DwarfCron/scripts/castsim/design.py:69, 525-550; DwarfCron/data/pacing/mechanics-diagram.html:350-367 (panel 2, reuse rotates apexes); DwarfCron/.claude/scratch/pacing/ladder/COAST.txt:45-51, 129-139; DwarfCron/.claude/scratch/pacing/ladder/SAVR_d1.json (via summarise.py: ground/cavern casts; CROCODILE_CAVE MW 8, VORACIOUS ML 4, JABBERER/SPIDER_CAVE_GIANT APX); DwarfCron/data/pacing/B2/P2_COAST/status-end.txt (apex scheduler on); DwarfCron/.claude/scratch/sw-questions/D1-review/year_sim.py, year_sim_big.py (year-level sims with reuse); memory/roster-builder-decisions.md (30 Sep x3 ruling, CAL group-size kills)

</details>

## D2

> What would happen if... instead of "sqrt(group mass / the largest group mass among the candidates)" we used "sqrt(the largest group mass among the candidates / group mass)"

**Short answer.** Flipping it turns the apex draw upside down: the smallest eligible hunter becomes the likeliest apex. The big hunters stay in the cast as mesos or fliers at FREQUENCY ~1, and they have no feeding link with the smaller 'apex', because nothing eats an apex-class species. Savage forts lose their giant character at the top and every savage fort draws the same few small apexes. Recommend against it. If giant apexes are the complaint, use a size-exponent setting or an apex-only giant multiplier.

*Status: verified · confidence high · review verdict: major fixes*

### Short answer
Flipping the ratio turns the apex draw upside down.
- **Today:** the weight is proportional to √(group mass), so the biggest hunter is the likeliest apex.
- **Flipped:** it is proportional to 1/√(group mass), so the smallest eligible hunter is.
- **The big hunters do not leave the cast.** They are seated anyway, in a meso slot on the ground or a flier slot in the air, where the ladder gives them about FREQUENCY 1 instead of the apex's 5. On savage flying layers the giant bugs also come back as the flier seed.
- **A big meso would *not* eat the small apex.** The tool's food web never lets anything eat an apex-class species, and DF hunts only along the relations the tool writes.
- **Result:** a cast with two top predators that ignore each other, with the smaller one labelled "apex". Every savage fort draws the same few small apexes, so variety per draw falls on every layer except wild ocean.

I recommend against it. Better levers are at the end.

### (a) What the code does now
**The apex draw** (`NR.cast`, seasonal-wildlife.lua:22905-22931):
- **Eligible:** candidates whose first slot is `apex`. True apexes come first; local ones only when no true apex is in season.
- **Group mass (`gsize`):** adult size × mean group size for a non-BENIGN predator whose group can exceed 1; adult size alone otherwise.
- **`mx`:** the largest group mass among the eligible.
- **Weight:** `sqrt(gsize/mx) × weight(x, apex_pack, true)`. `weight()` multiplies in: pack x1.5, x0.01 per other cast already holding the species, giant x0.2, animal person x0.1.
- **If nothing is eligible:** the heaviest candidate with a meso slot is promoted (22928-22930). Land-flying has no meso slot, so a flying cast with no eligible apex gets none.

The explorer (`foodweb_sim.js:729-732`) and the desk simulator (`design.py`) use the same formula. You chose it on 10 Oct (DwarfCron a330a7f2: "sqrt group size vs largest … no size floor").

**Big species that lose the draw still join.**
- On the ground an apex-class predator also has the `meso` slot; on flying it has `flier` (`slotsFor`, 10215-10227).
- Growth seats any free candidate linked to a member.
- A savage fort's flying seed starts at the "savage, extinct" rung, then "savage flier": an animal person or a giant flying bug (22966-22986).

**Nobody eats an apex-class species.**
- `apexBar` returns blocked whenever the prey is apex-class on any of its layers (22635; `y.apex` from `NR.apexOn`).
- `forcedDiet` refuses apex-class prey (22656). The one exception, a sentients diet, comes before that check and is narrow.
- `massWhy` and `engineEats` check the bar before any size rule.
- **DF follows the tool's web.** Under casts, PREDATOR_OR_PREY is written only for the season's cast edges and cross-layer links (`ecoWrite`, 6403-6412; `NR.seasonPairs`). The sweep clears DF's own relation cells between tool-managed wild animals (6545 on). ECO (30 Sep) found no predator attacked without a written relation, in 48 of 48 pairs.

**How often the apex arrives.**
- An apex keeps its raw FREQUENCY, capped at 5 (9446-9460). The T. rex reads 2 in Fort 1.
- Every other member gets the ladder's size scale (mass ÷ the slot's geometric mean)^-0.75, clamped to 0.25-4 (9402-9403), then normalised. A giant in a meso slot comes out at about 1.

### The divisor does nothing either way
√(g/mx) = √g/√mx, and every candidate shares the same √mx, so the odds go with √g. Flipped, they go with 1/√g. The real choice is between favouring big hunters by √size and favouring small ones by √size.

### Thought experiment 1: the diagram's forest (checked by hand)
| | group mass | today | flipped | + giant grizzly, today | + giant grizzly, flipped |
|---|---|---|---|---|---|
| Grizzly | 200,000 | 33% | 23% | 28% | 23% |
| Wolf (pack x1.5) | 200,000 | 49% | 35% | 41% | 34% |
| Cougar | 60,000 | 18% | **42%** | 15% | **42%** |
| Giant grizzly (x0.2) | 1,700,000 | – | – | 16% | **1.6%** |

In a calm forest the flip is mild, because the hunters are within about 3x of each other in size.

### Thought experiment 2: Fort 1 (savage marsh, real dump SAVR_d1, checked)
- **Today:**
  - Flying apexes: giant roach, giant dragonfly, giant buzzard, giant mosquito, all at 5.
  - Ground apexes: giant brown recluse spider, T. rex (raw 2), giant bark scorpion, giant tick.
  - Wolf and black bear are already ground mesos at FREQUENCY 1. Giant coyote and giant skink (meso) and giant kestrel and giant mantis (flier) also read 1.
- **Flipped:**
  - A wolf, jaguar or black bear takes the apex seat at 5. The T. rex and the giant bugs drop into meso or flier seats at about 1.
  - Neither the small apex nor the T. rex meso can eat the other, so DF gets no relation between them.

### Thought experiment 3: every biome (desk model, odds per single draw)
Scratch: `.claude/scratch/sw-questions/D2/flip.py`, `hill.py`, `out.txt`. Model numbers, not rig numbers.
- **Savage marsh ground:** today wolf 20%, giant dingo 15%, giant coyote 12%. Flipped: jaguar 29%, wolf 27%, black bear 23%.
- **Savage broadleaf ground:** T. rex is top today at 18%; flipped, 1%.
- **Savage marsh flying:** today giant roach 48%. Flipped: peregrine 43%, osprey 31%, eagle 22%.
- **Wild ocean:** today orca 50%. Flipped: each mako shark 31%.

**Variety per draw** (effective number of apex species, 1/Σp²):

| world, layer | today | no size weight | flipped |
|---|---|---|---|
| savage ground | 11.9 | 10.8 | **7.4** |
| savage flying | 4.1 | 5.0 | **2.6** |
| savage ocean | 6.7 | 10.7 | 6.2 |
| savage fresh | 3.0 | 2.7 | 2.2 |
| wild ground | 4.2 | 4.0 | 3.6 |
| wild flying | 2.4 | 2.9 | 2.2 |
| wild ocean | 2.9 | 4.9 | 3.4 |
| wild fresh | 2.0 | 1.8 | 1.75 |

**Why variety drops:**
- Savage candidate lists hold many giants and only a few small vanilla hunters, so 1/√g piles the odds onto the 3-5 smallest.
- Within one fort the x0.01 repeat weight still forces different apexes each season. The real effect is that every savage fort gets the *same* small apexes, and the savage/calm difference at the top disappears.

### What breaks
1. **"Apex" stops meaning "top predator".** (Code.) A T. rex or giant buzzard sits below a jaguar or falcon apex, with no link either way.
2. **Giants become rare, not just less often the apex.** (Code plus Fort 1.) In meso or flier seats they are written at about 1 instead of 5.
3. **Small apexes kill less.** (DF evidence plus inference.) ECO CAL found kills follow hunting group size: lone hunters made 1 kill in 12 cells. Wolf and dingo packs would still hunt.
4. **The fallback runs the other way.** (Code.) With nothing eligible, the *largest* meso is promoted.
5. **Divide by zero.** (Code.) A candidate with mass 0 gets an infinite weight, the draw goes NaN and falls through to the last candidate. A real change needs a mass floor.
6. **The apex's own arrival rate barely moves.** (Code.) The flip mostly changes *which* species arrives at 5.

### Better levers
- **A size-exponent setting:** weight ∝ (g/mx)^k. Today k = 0.5; 0.25 is gentler; 0 removes size; a negative k is the flip. Under your 20 Oct ruling it needs a registry row, a `cast set` verb and a check that it reaches the engine.
- **An apex-only giant multiplier.** `cast set giant` acts on every pick (seed, growth, apex). An apex-only one would damp giant apexes and keep giants as mesos and seeds.
- **Check giant-bug packs.** The giant roach counts as a predator pack of 7.5 (group mass 15M), which is why it wins 48% of savage flying draws. That is a rules question, not a formula one.

### What would settle it
- **Offline:** explorer or castsim, 200 years per biome at k = +0.5, +0.25, 0 and −0.5, plus an apex-only giant multiplier. Measure distinct apexes per fort-year and across forts, and how often a meso or flier outweighs the apex.
- **Rig, only to adopt a change:** the same savage fort (breached, startdwarf 50, n=5 per arm), one year per arm. Count apex-group kills, waves per species, and whether giants written at 1 still arrive.

**Rig test that would settle it:** Offline first: explorer or castsim, 200 years per biome at k = +0.5, +0.25, 0 and -0.5, plus an apex-only giant multiplier; distinct apexes per fort-year and across forts; how often a meso or flier outweighs the apex. Rig only to adopt a change: the same savage fort (breached, startdwarf 50, n=5 per arm), today's k against the candidate k for one year; apex-group kills, waves per species, whether giants written at FREQUENCY 1 still arrive.

<details><summary>Review and verification trail</summary>

- review: WRONG, removed: the claim that a big hunter in a meso slot would eat a small apex. In the tool's food web nothing eats a species that can hold an apex slot. apexBar (seasonal-wildlife.lua:22635-22636) has `if y and y.apex then return true end`, where y.apex is set when the species is apex-tier on any layer (NR.apexOn :22818). massWhy calls apexBar before its half-size rule (:22697). forcedDiet returns false for an apex-tier prey (:22656). engineEats/huntWhy add `tierOf(a) <= tierOf(b)` (:22735) with SLOT_TIER apex 3 > meso 2 (:9620). Cast edges come from eats1 = NR.eats (cast edge loop about :23113). Under casts, DF relations are written only for those edges (ecoWrite :6403-6412, NR.seasonPairs :23433-23451). ECO (memory relation-write-needs-large-predator.md) found that with no written relation, no predator attacked in 48 pairs. So the flip gives two top predators that never touch each other. It does not give a meso that eats its apex.
- review: Fixed the description of massWhy. A link is blocked first by apexBar (any apex-tier prey) and only after that by the 'predator prey at least half the eater's size' rule.
- review: ADDED: savage flying casts get giants back through the seed. For a savage fort the flier seed starts at rung 3 (the prehistoric fliers when the extinct rule is on), then rung 4: any flier animal person or giant flying bug (:22966-22986, start = 3 for savage). Under the flip the giant roach or giant mantis would often still be in the cast, as the seed in a flier slot.
- review: ADDED, real fort data (SAVR_d1, Fort 1 savage marsh). Today's mesos are wolf and black bear at FREQUENCY 1, and giants pushed into meso or flier slots (giant coyote, giant skink, giant mantis, giant kestrel) also read FREQUENCY 1, because the ladder's size scale clamps at 0.25 (ROSTER.ladder :9402-9403). Apexes read 5. So the flip roughly swaps who gets 5 and who gets 1: wolf or bear apex at 5, giants at 1.
- review: Corrected 'arrival rates do not move'. The apex's FREQUENCY is min(raw, apex_raw_cap 5) (:9457-9460). That is 5 for most species, but extinct prehistoric species read lower (T. rex raw 2 in Fort 1). So the apex's own rate barely changes. The species pushed out of the apex slot do change: they fall from 5 to about 1.
- review: ADDED the freshwater rows to the variety table (re-ran hill.py; the numbers reproduce). Noted that 'no size weight' slightly lowers variety on ground and fresh, so k=0 is not better everywhere.
- review: ADDED a caveat: the variety measure is per draw. Within one fort the ×0.01 reuse penalty already gives four different apexes a year whenever there are four or more candidates. What the flip mainly does is make every savage fort's apex set the same 3-4 small species.
- review: Corrected the forest-to-marsh claim. In the savage marsh model today's single likeliest ground apex is already the wolf (20%), so the flip shifts the mix toward jaguar, wolf and black bear rather than replacing giants outright.
- review: Corrected the lever note. `cast set giant` is used by every pick in NR.cast (weight() feeds pick() for the seed, growth and fill), not only the apex draw, so lowering it removes giants from every slot.
- review: Revised the rig test. Dropped 'apex deaths to mesos' (no relation would be written). Now it measures kills by the apex, waves per species (do giants still arrive at FREQUENCY 1?) and distinct species seen.
- review: Verified as accurate: the apex draw formula and gsize (:22913-22921); the forest table arithmetic (33/49/18, flipped 23/35/42; with the giant grizzly 28/41/15/16, flipped 23/34/42/1.6; wolf reused, flipped 34/0.5/63/2.4); that mx cancels; the divide-by-zero behaviour (an infinite weight makes every comparison NaN, so the draw falls to el[#el]); the largest-predator fallback (:22928-22930); commit a330a7f2 (10 Oct); design.py:70; foodweb_sim.js:729-732; Fort 1 surface apexes 8 of 8 giants or T. rex.
- verifier: Added: the 'largest predator promoted' fallback only exists on layers with a meso slot (ground, water, caverns). Land-flying has no meso slot, so a flying cast with no eligible apex gets no promotion.
- verifier: Minor: forcedDiet's sentients clause runs before the apex bar, so the 'nobody eats an apex-tier species' rule has one narrow exception. It is an eater whose rule lists sentients, eating an apex-tier animal person on a layer that rule names. It does not touch the flip's conclusions.

Code refs: /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:22904-22931 (NR.cast apex draw: gsize, mx, sqrt(gsize/mx) weight, el[#el] fallthrough, largest-meso fallback); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:22876-22893 (weight() and pick(): pack, reuse, giant, ap_pick; used by every pick in the cast); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:22620-22648 (apexBar: `if y and y.apex then return true end` at 22635-22636); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:22800-22830 (NR.apexOn: apex = #apexL > 0); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:22652-22657 (forcedDiet: apex-tier prey returns false); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:22695-22714 (massWhy: apexBar first, then the half-size predator rule); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:22512-22517, 22724-22740 (tierOf, engineEats tier test), 9620 (SLOT_TIER apex 3 > meso 2); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:22768-22778 (NR.eats), ~23113 (cast edges via eats1); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:6403-6412 (ecoWrite: under casts only New Rules cast edges are written), 23433-23451 (NR.seasonPairs); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:22948-22986 (flying seed rungs; savage starts at rung 3, giant flying bugs at rung 4); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:22990-23032 (growth on the food web); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:10183-10227 (ROSTER.FP.apexTier, slotsFor: apex-tier ground predator also meso, flying also flier); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:9382-9460 (ROSTER.ladder: size scale clamp 0.25-4 at 9402-9403; R34 apex = min(raw, apex_raw_cap 5) at 9457-9460); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:694 (APEX_PACK 1.5), 9087 (ap_pick 0.1), 10339-10351 (CAST_DEF, CAST_SET giant 0-5); /Users/nathanielcannon/Claude/Projects/DwarfCron/scripts/castsim/foodweb_sim.js:725-733 (explorer apex draw, same formula); /Users/nathanielcannon/Claude/Projects/DwarfCron/scripts/castsim/design.py:70 (APEX_FLOOR 0 rationale); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/mechanics-diagram.html:351-360 (panel 2 apex weight text and forest example); /Users/nathanielcannon/Claude/Projects/DwarfCron/.claude/scratch/pacing/ladder/SAVR_d1.json (Fort 1: giant apexes at 5, wolf/black bear/giant coyote/giant mantis at FREQUENCY 1 in meso/flier slots); /Users/nathanielcannon/Claude/Projects/DwarfCron/.claude/scratch/sw-questions/D2/flip.py, hill.py, out.txt (offline model; hill.py re-run, numbers reproduce); memory: relation-write-needs-large-predator.md (no written relation, no attack: 48/48), roster-builder-decisions.md (ECO CAL: kills follow group size; STL)

</details>

## D3

> What would happen if... we didn't apply "Caverns: food-web guarantee: a predator and its prey are forced in."? Are the cavern foodwebs not being built well? Why was this step added? What would happen if it were removed?

**Short answer.** Removing it changes nothing today. With the current cavern slot table and candidate lists, every cavern cast already has an apex, a meso and a ground prey, so the guarantee never fires. It drew no random numbers in 1,440 explorer casts or in the 36 real cavern casts. It was added on 16 Oct as insurance against two risks that later proved false: thief species never arriving, and out-of-range species never sent. Make it a visible warning, and fix the diagram and Controls wording, which overstate it.

*Status: verified · confidence high · review verdict: minor fixes*

### Short answer
- **Turning it off changes nothing today.** The step never fires with the current slot table and candidate lists. When it does not fire it draws no random numbers, so every cast comes out the same, member by member.
- **The cavern food webs are built well at the cast level.** Every cavern cast has an apex, a meso and a ground prey, linked through New Rules. The real cavern problems are elsewhere (section 6).
- **Why it was added:** insurance for your Cavern Layer Picks (16 Oct) against two risks that both later turned out false.
- **Recommendation:** turn it into a visible warning instead of a silent fix (section 5). Nothing is built yet.

### 1. What the code does
`NR.cast` (seasonal-wildlife.lua:22862) builds one season's cast for one layer, in this order:
1. apex draw;
2. seed;
3. growth;
4. unfilled notes (23037-23043);
5. **the guarantee** (23044-23066);
6. bonus predator (23068);
7. vermin.

The cavern slot table (`RO.SLOTS.cavern`, 798) has one seat each for apex, meso, ground prey, flier, swimmer and sentient, plus 2 vermin.

**The prey test** (`isPrey`) passes if a member sits in the ground-prey seat, or a non-predator sits in the flier or swimmer seat. "Predator" means guild AL/AW/ML/MW/RP. If it fails, one non-predator that fits ground prey, flier or swimmer is added at random. That pick ignores the x0.01 repeat weight.

**The predator test** passes if anything sits in apex or meso, or a predator sits in flier or swimmer. If it fails, the step adds the heaviest non-sentient predator, which is not random: the cave crocodile in cavern 1, the cave dragon in cavern 3. It goes to that predator's first apex or meso slot.

**Switch:** `seasonal-wildlife cast caverns guarantee on|off`, then `cast rebuild` (24583-24599). The setting is `cfg.cast.web_guarantee` (NR.prmOf, 23352).

**Where it shows:** almost nowhere. There is a count in the cast record (`NR.toRecord`, 23376) and a log line "web guarantee: prey". The view model carries the count (11352), but neither the game window nor the web page displays it.

**The wording overstates it.** Diagram panel 2 step 5 says "a predator and its prey are forced in". The Controls text (controls.lua:241) says "Every cavern cast holds a predator-prey link". The code never checks that the added predator eats the prey. It only makes sure *some* prey and *some* predator are present. The older v6.4 `ROSTER.pairGuarantee` (3427) did check eating, which is probably where the wording came from.

### 2. Why it was added
- **When:** commit ecc16cc (v7.6, 16 Oct), with your Cavern Layer Picks. It was carried into the New Rules builder by 65ef111 (20 Oct), with the comment "the cavern web guarantee as before" (22782).
- **The desk study behind it:** `data/castsim/cavern_assign.json`, 20 sites, old builder. It counted a cavern-season as complete only if its *arriving* members included a prey, a predator and 2 vermin.

| Arrangement | Seasons with prey | Members the guarantee added per site-year |
|---|---|---|
| Raw depth (before your picks) | cavern 1: 30-50% | not run |
| Your picks as entered | cavern 2: 55-75% | not run |
| Review (11 species changed) | 100% | not run |
| **Review + guarantee (shipped)** | 100% | **0** |
| Review + guarantee, out-of-range never sent | 100% | 1.6 |

**Both risks it covered turned out false:**
- **Thief-tagged species never arriving.** That came from NA1, a single unbreached rig fort. You rejected it on 16 Oct, and the tool now places cast thieves itself.
- **Out-of-range species never sent.** OOR tests showed DF sends them (8 of 8).

The 16 Oct report itself said "the guarantee is rarely needed once the empty slots are gone".

### 3. Why it never fires now
Cavern candidate lists come from all raws plus your assignment, so they barely change by fort or season. In the explorer fixture they hold 18 / 36 / 43 non-vermin candidates for caverns 1 / 2 / 3.

| Seat | Cav 1 | Cav 2 | Cav 3 |
|---|---|---|---|
| Ground prey | 7 | 8 | 10 |
| Apex | 4 | 8 | 11 |
| Meso | 5 | 11 | 15 |
| Flier | 2 | 3 | 4 |
| Swimmer | 2 | 4 | 5 |

- **Prey:** growth keeps filling open seats while any free candidate fits. There are always 7+ ground-prey species, so that seat fills and `isPrey` passes.
- **Predator:** the apex seat is always filled, and so is meso, so `isPred` passes.
- **Explorer, 1,440 cavern casts:** the guarantee fired 0 times. The harness `nrcast` mode matches the engine to the explorer, cast for cast.
- **Real forts:** SAVR_d1, COAST and LAKE3 hold 36 cavern casts at the current code. All have an apex, a meso and a ground prey.
- **The only test that makes it fire has to break the slot table first.** The harness (tests/web/harness.lua:1355-1381) cuts the cavern table to apex + meso, then calls `FP.grow` → `NR.cast`.

### 4. If it were removed
**Today: nothing.** Each cast has its own seeded random stream (`NR.seedOf`). The guarantee draws from it only when it adds a prey, and the predator pick uses none. The repeat counter is unchanged too.

**When it would matter** (inferred from the code, not run):
1. **You trim the cavern slot table**, for example by dropping the ground-prey seat. In cavern 1 it would then fire whenever the giant cave swallow, not the bugbat, takes the flier seat, because both cavern 1 swimmers are predators.
2. **You set a pick weight to 0.** `cast set reuse 0`, `giant 0` and `ap_pick 0` are allowed (10345). If every remaining weight is 0, growth stops (`if not x then break end`) and can leave the ground-prey seat empty.
3. **Mods** that remove cavern prey species.
4. **Assignment off.** I expect it still would not fire; untested.

**No effect:** maps with only ponds or no water, savage or evil land, and unbreached caverns. The cavern lists do not depend on the surface.

### 5. Does it serve your aims?
- **Fewer hacks:** it is a hidden after-the-fact override that does nothing today.
- **Control:** where it would fire, it hides a design problem, and its fix runs against your aims:
  - its prey pick is random and skips the repeat weight;
  - its predator is always the heaviest (the crocodile in the cavern you wanted calmer);
  - it never checks a link;
  - no UI shows that it fired.

**Suggested** (nothing built):
- **Preferred:** a warning. When a cavern-season lacks prey or a predator, write a ledger line and show it in the Casts view next to the unfilled seats. Correct the diagram and the Controls text.
- **If you keep it as insurance:** require the added predator to eat a member (`eats1`), pick it by the normal weights, and show the count.

### 6. Are the cavern food webs built well?
**At the cast level, yes.** The weak points:
- **Cavern 1 has too few swimmers.** Only the cave crocodile and the giant cave toad can swim there, and both can also take apex or meso. In autumn the toad (the seed) took meso and the crocodile took apex, so the swimmer seat stayed empty. This is one draw, seen in all three forts. The draltha is the ground prey in 3 of 4 cavern 1 seasons.
- **Delivery matters more than building.** DF's cavern pick seems to follow entry stock more than FREQUENCY: flesh balls took 54% of cavern 3 groups (PENDING, dominance/FINDINGS.md). The B2 `open_stock` arm is measuring this.
- **The pacing forts share their cavern casts.** All three dumps are site 266, year 100 in region6. Casts are seeded by site and year, and cavern lists don't depend on the fort. SAVR_d1 and LAKE3 are identical in all 12 cavern-seasons. COAST differs only in the sentient seat in 2. So B1/B2 cavern results are close to one cast set repeated. A different `cast.salt` per fort, or different worlds, would give independent samples.

### 7. What would settle it
No rig test is needed.
- Run harness `nrcast` with `prm.guarantee` true and false and diff the casts; expect identical.
- To size the edge cases, rerun with (a) no ground-prey seat, (b) reuse = 0, (c) assignment off. Count `out.guarantee` and casts with no prey or no predator.

Whether a complete cast arrives as a working food web is a separate rig question: the B2 `open_stock` A/B.

**Rig test that would settle it:** None for the question itself; it is settled offline. Harness MODE nrcast with prm.guarantee true vs false; diff the casts (expect identical). Edge cases: cavern table minus ground prey, reuse 0, assignment off; count out.guarantee and casts with no prey or no predator. Arrival as a working web is the separate B2 open_stock A/B (PENDING). Use a per-fort cast.salt or different worlds for independent cavern samples.

<details><summary>Review and verification trail</summary>

- review: Date fixed: commit 65ef111 (v8 Phase C, which carried the guarantee into the New Rules builder) is dated 20 Oct 2026, not 27 Oct. The words 'as before' come from the code comment at seasonal-wildlife.lua:22782, not from the commit message.
- review: 'Three different worlds' was wrong. data/pacing/B2/master.log shows P2_SAVR, P2_COAST and P2_EVIL all embarked in region6, and all three dumps report site_id 266 and year 100. Casts are seeded from plotinfo.site_id and year (castYear calls NR.year at line 10849; NR.seedOf is at 23150). My recount: the cavern casts are seat-for-seat identical across SAVR_d1, COAST and LAKE3 in 10 of 12 cavern-seasons (cavern 2 spring and cavern 3 autumn differ). So the pacing forts share almost one set of cavern casts.
- review: Largest-predator pick corrected. In cavern 1 it is the cave crocodile (m=600000 against the bear's 200000 in the candidate list), not 'bear or crocodile'. In cavern 3 it is the cave dragon (15,000,000). Added the fact that the predator half can only fire if both the apex and meso seats are empty, which the current table and lists never allow.
- review: Edge case 1 made precise. Dropping the ground-prey seat triggers the guarantee only when the flier and swimmer seats also hold predators. predator() at line 22453 uses guilds AL/AW/ML/MW/RP: the giant cave swallow, giant bat and hungry head are predators; the bugbat, cave floater and flesh ball are not. The harness test (harness.lua:1357) removes the flier and swimmer seats too, not just ground prey.
- review: New edge case found in the code: pick weights can reach 0. `cast set reuse 0` is allowed (ROSTER.CAST_SET, line 10345: reuse min 0, giant 0, ap_pick 0). When every weight is 0, pick() returns nil and growth stops at `if not x then break end`, which can leave the ground-prey seat empty. The guarantee ignores weights and would then refill it. This is inference; I did not run it.
- review: Apex fallback corrected. The apex draw first falls back from the 'apex' tier to the 'local' tier (lines 22918-22921). Only when neither has a candidate is the largest meso candidate promoted (22935-22938).
- review: Hidden-ness confirmed and widened. The view model carries the guarantee count (line 11352), but neither the window (scripts/gui/seasonal-wildlife.lua) nor the web page (seasonal-wildlife-web.html, 0 mentions) shows it. The controls registry text (scripts/internal/seasonal-wildlife/controls.lua:241) says 'Every cavern cast holds a predator-prey link', which overstates the code just as the diagram does.
- review: 'Why it was added' sharpened. Both risks it insured against turned out not to hold. The thief-tagged species were counted as never arriving because of NA1, which was one unbreached rig fort; you rejected that on 16 Oct and the bar was withdrawn in v7.6.1 (memory note cavern-thief-tag-bar.md). Out-of-range species were counted as never sent, but the OOR1/OOR3 rig tests had already shown them sent (8 of 8).
- review: Desk figure clarified. In the 'never drawn' arm the guarantee added about 1.6 members per site-year across the 12 cavern casts, 1.5 of them in cavern 1 (cavern_assign.json 'guar' is a per-cast mean over 20 sites). It added 0 in the arm that shipped.
- review: Verified as stated: the order of steps, the isPrey/isPred tests, the uniform prey pick that skips the repeat weight, the rg.below call made only when it fires, the switch and verb, the 1,440 fixture casts with 0 fired (the guarantee field is present in all 1,440, so the count is real), the 36 real-fort casts all holding apex, meso and ground prey, and the cavern 1 swimmer gap in autumn with draltha as prey in 3 of 4 seasons. The fixture dates from 27 Oct; the dumps are current.

Code refs: /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:798 (RO.SLOTS.cavern); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:22453 (predator(): PREDG guilds AL/AW/ML/MW/RP); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:22782 (comment: 'the cavern web guarantee as before'); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:22862-22895 (NR.cast setup, weight(), pick() returns nil at total 0); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:22905-22938 (apex draw: apex tier, else local tier, else largest meso promoted); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:22989-23036 (growth on New Rules; 'if not x then break end'); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:23037-23043 (unfilled seats); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:23044-23066 (cavern food-web guarantee); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:23068-23085 (BONUS_PREDATOR); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:23114 (used counter incremented per member); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:23150-23168 (NR.seedOf / NR.year: seeded by site and year); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:10849 (castYear: site = plotinfo.site_id); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:10345-10352 (ROSTER.CAST_SET: reuse/giant/ap_pick min 0); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:11347-11352 (view model carries guarantee; not rendered); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:23349-23353 (NR.prmOf guarantee switch); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:23376 (NR.toRecord guarantee count); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:24583-24599 (verb cast caverns guarantee on|off); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:3427-3475 (older v6.4 ROSTER.pairGuarantee, which checks eats); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/internal/seasonal-wildlife/controls.lua:241 (Controls text overstates: 'predator-prey link'); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/tests/web/harness.lua:1355-1381 (guarantee test with cavern table cut to apex+meso); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/tests/web/harness.lua:3222-3230 (MODE nrcast, prm.guarantee = true); git ecc16cc (v7.6, 16 Oct: guarantee added); git 65ef111 (v8 Phase C, 20 Oct: carried into New Rules); /Users/nathanielcannon/Claude/Projects/DwarfCron/scripts/castsim/cavern_assign.py:56-90 (ensure_web, web_state counts arriving members only); /Users/nathanielcannon/Claude/Projects/DwarfCron/scripts/castsim/design_report.py:572-600 (16 Oct report); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/castsim/cavern_assign.json (7 arms; guar 0 in shipped arm, 1.6 in out-of-range-never-sent arm); /Users/nathanielcannon/Claude/Projects/DwarfCron/.claude/scratch/flier-seeds/nr_fixture.lua (1,440 cavern casts, guarantee field present, 0 fired); /Users/nathanielcannon/Claude/Projects/DwarfCron/.claude/scratch/pacing/ladder/SAVR_d1.json, COAST.json, LAKE3.json (site 266, year 100; cavern casts identical in 10 of 12 seasons); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/B2/master.log (P2_SAVR, P2_COAST, P2_EVIL all embarked in region6); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/mechanics-diagram.html:371 (panel 2 step 5 wording); /Users/nathanielcannon/Claude/Projects/DwarfCron/.claude/scratch/pacing/dominance/FINDINGS.md (stock-weighted cavern pick, PENDING); memory: cavern-thief-tag-bar.md, cavern-out-of-range-draws.md, cavern-pick-stock-weighted.md; /Users/nathanielcannon/Claude/Projects/DwarfCron/.claude/scratch/sw-questions/d3/fx.lua, slots.lua, rev_pred.lua, rev_gkey.lua (tally scripts)

</details>

## D4

> What would happen if... this step "Bonus predator: a giant herbivore that nothing in the cast eats gets one of its eaters in an extra seat" was given a roll of chance so that a mega-predator wasn't necessarily added every single time that a giant herbivore had no in-cast predator? Would that work? Would anything break?

**Short answer.** It would work, and nothing would break, but it would barely reduce mega-predators. The bonus seat fires rarely and supplies only about 1-5% of the big theropods in casts. Most come from the size-weighted apex draw, the size-ranked seed and growth. A coin flip would mostly leave a giant herbivore unhunted in a few more seasons. To cut mega-predators, change the apex draw or the seed. For the bonus itself, either remove it or make it prefer plausible hunters.

*Status: corrected · confidence high · review verdict: minor fixes*

### Short answer
It would work and nothing would break, but it would barely touch the mega-predator problem. The bonus seat fires rarely and supplies only about 1-5% of the T. rex-class predators in your casts. A chance roll would mostly leave a giant herbivore with no hunter in a few extra seasons. The levers that matter are in section 6.

### 1. What the step does now (code)
`NR.cast`, seasonal-wildlife.lua:23068-23086. It runs after growth and the cavern guarantee, just before vermin.
- **Trigger list:** 12 species in `BONUS_PREDATOR` (698; rules/new-rules.json, your 20 Oct ruling): Deinotherium, woolly mammoth, Ankylosaurus, Iguanodon, Parasaurolophus, Therizinosaurus, Triceratops, Tsintaosaurus, Brachiosaurus, Brontosaurus, Diplodocus, Stegosaurus. The same day you left elephant, rhino, giant elephant, giant rhino and giant giraffe free to go unhunted.
- **When it fires:** for each listed giant in the cast, the step checks whether **any** member eats it (`eats1`, 23072). If none does, it collects not-yet-seated candidates that could eat it and draws one with the ordinary weights (x3 pack, x0.2 giant, x0.1 animal person, x0.01 repeat). **There is no size term.**
- **Which seat:** the first of meso/apex in the eater's slot list, else its first slot (23078). Apex-class species list apex first (`slotsFor`, 10215-10220), so a T. rex or giant arachnid bonus eater gets a **second apex seat**, outside the slot table.
- **One eater can cover two giants.** The check reads the growing member list.
- **After the build** (`NR.toRecord`), the bonus eater is an ordinary member. `rec.bonus` is stored (11351, 24757), but no window, page or engine step reads it back.
- **Where the giants can appear at all** depends on the world's extinct setting (`ROSTER.FP.gate`, 9984-9989):
  - "extinct": never;
  - "untamed wilds" (the fallback): savage biomes only;
  - "isolated": small regions, savage or not;
  - "wilderness" or "domesticated": no savagery bar in the code.
- **The explorer copy** (`foodweb_sim.js:853-865`) is the same step. Harness `nrcast` catches a "no bonus" mutant (75 differences, commit 65ef111).

### 2. How often it fires (explorer builder, 200 years × 8 forts)
| fort (800 seasons) | giant seats | already eaten | bonus fired |
|---|---|---|---|
| terrifying broadleaf river | 604 | 558 | 46 |
| savage tropical coast | 368 | 348 | 20 |
| evil tundra ponds (wilderness world, mammoth only) | 208 | 171 | 37 |
| savage good arctic coast (mammoth) | 269 | 264 | 5 |
| savage marsh | 339 | 323 | 16 |
| savage grassland | 345 | 330 | 15 |
| calm lake, good brook | 0 | n/a | 0 |

**Fort 1's real casts agree** (I checked SAVR_d1):
- Autumn ground holds Triceratops and Parasaurolophus with no bonus seat, because the apex (giant bark scorpion) already eats them.
- Summer holds Iguanodon and Ankylosaurus, with the T. rex as the drawn apex.
- Triceratops and Iguanodon got in as the cast's **seed**, which is ranked by size.

**The 139 bonus seats went to:** big theropods 41 (about 29%), giant arachnids 30, polar bear 14, giant coyote 12, giant dingo 7, hyena 6, and others.

### 3. The bonus is not where the mega-predators come from
Big-theropod seats in ground casts over the same 200 years (scratch `d4-review/how.js`):

| fort | casts with a big theropod | theropod seats | from the bonus |
|---|---|---|---|
| terrifying broadleaf | 462 of 800 | 559 | 25 (4.5%) |
| savage tropical coast | 222 | 243 | 6 (2.5%) |
| savage marsh | 207 | 211 | 4 (1.9%) |
| savage grassland | 463 | 557 | 6 (1.1%) |

The rest come from:
- **the apex draw**, weighted by √(group mass), so a T. rex is the favourite whenever it is eligible and not yet used that year;
- **the seed**, ranked by size;
- **growth links.**

### 4. What a chance roll would do
I ran a scratch copy of the builder with a roll just before the bonus draw. The table counts giant herbivores with **no feeding link at all** in that season's joined surface web (seasons out of 800):

| fort | always (now) | 50% | 0% (step removed) |
|---|---|---|---|
| terrifying broadleaf | 0 | 26 | 43 |
| savage tropical coast | 0 | 12 | 19 |
| evil tundra ponds | 0 | 16 | 25 |
| savage arctic coast | 0 | 3 | 3 |
| savage marsh | 0 | 3 | 5 |
| savage grassland | 0 | 8 | 13 |

Some skipped giants are fed by an eater on another layer that season. Even with the step gone, the gap shows in at most about 5% of seasons.

### 5. What breaks, what changes
- **Nothing crashes.** An empty bonus list is already handled.
- **Engine and explorer must change together**, with a new `nrcast` baseline. Under your 20 Oct ruling the setting also needs a `ROSTER.CAST_SET` row, a verb with its default, and a check that it reaches the engine.
- **Use a seeded stream, never `math.random`.** Otherwise a rebuild gives different casts and the explorer stops matching the fort.
  - Rolling on the cast's own stream shifts that cast's vermin draw.
  - A skipped seat also changes the year's repeat counts, which shifts casts built later. A separate stream avoids the first effect, not the second.
- **In DF.** Vanilla raws name no prey, and without a written relation no predator attacked (ECO, 48 pairs). So an unhunted giant meets only your dwarves, the waves and the tool's caps.
  - Many bonus eaters are eaters only on paper. A lone giant tick against a mammoth herd (3-7 animals, about 6 t each) is not a believable hunt, and prey that fight back win: capybaras killed 5 of 5 wolves. That is my inference; it is untested.

### 6. Does a chance roll serve your aims?
Not well. It reopens the hole the step closes, barely changes the mega-predator load, and adds randomness you cannot steer.

Better options, depending on what bothers you:
1. **"Too many T. rexes"** → tune the apex draw's size weight (see D2) or keep big predators out of the seed.
2. **"The bonus is a hack"** → remove the step. The cost is about 1-5% of seasons with an unhunted giant, the same trade you already accepted for elephants, rhinos and the giant giraffe.
3. **"Silly eaters"** → make the bonus prefer plausible hunters, such as pack hunters or a size ratio. This is deterministic and adds no new hole.
4. **"This giant needs no hunter"** → drop it from `BONUS_PREDATOR`. The mammoth on evil tundra fires the bonus most often.
5. **"Skip it if another layer feeds it"** → move the check to after all of a season's casts are built.

### 7. What only the rig can settle
The cast side is settled offline. For DF: a savage Jurassic/Cretaceous fort at a site and year where the explorer predicts a bonus seat, bonus on vs off, 5 one-year runs per arm. Measure:
- whether the relation is written;
- the eater's attacks and kills on the giant, and who wins;
- the giant's head count and breeding;
- the eater's kills on other cast members and livestock.

**Rig test that would settle it:** Cast side offline (done). DF side: a savage Jurassic/Cretaceous fort where the explorer predicts a bonus seat; casts built with the bonus on vs off, 5 one-year runs per arm. Measure: the relation written; the eater's attacks, kills and losses against the giant; the giant's head count and breeding; the eater's kills on other members and livestock.

<details><summary>Review and verification trail</summary>

- review: FIXED a wrong claim. The draft said the bonus 'never fires on calm, good or non-savage maps'. Whether the 12 giants appear is set by the world's REAL_WORLD_EXTINCT setting in ROSTER.FP.gate (seasonal-wildlife.lua:9984-9989). EXTINCT means they never appear. UNTAMED_WILDS (the fallback at 9773) admits them only in savage biomes. ISOLATED admits them in small regions, savage or not. WILDERNESS and DOMESTICATED set no savagery bar. The draft's own 'evil tundra ponds' fort is savagery 50 under WILDERNESS (d4/run.js) and fired 37 times. Good alignment does not matter either: the good arctic coast fired 5 times.
- review: ADDED the main missing point: the bonus seat is a tiny source of mega-predators. I counted big-theropod seats in ground casts over 200 years on 4 of the forts (d4-review/how.js). The bonus seat gave 25 of 559, 6 of 243, 4 of 211 and 6 of 557 (1-5%). Most came from the apex draw, which is weighted by sqrt(size) (seasonal-wildlife.lua:22912-22925). The rest came from growth links and the high-value seed, which ranks candidates by size (NR.hvSet, 22854-22874). Big theropods sat in 26-58% of ground casts. A chance roll on the bonus would barely change that.
- review: CORRECTED the eater counts from out_always.json. Big theropods were 41 of 139 (about 29%), not 37 (27%): the draft left out Ceratosaurus (4). The giant arachnids (jumping spider 12, bark scorpion 7, giant tick 6, brown recluse 5) total 30.
- review: CLARIFIED what the section 3 table counts. It is giant herbivores with no feeding link at all in the season's joined surface web (R.unlinkedBon in run.js), summed over 800 seasons. It is not 'surface members'. Added the scale: even with the step removed, that is 3-43 seasons out of 800 per fort.
- review: CORRECTED the slot detail. The bonus eater goes in its meso or apex slot if it has one, otherwise in its first listed slot (x.slots[1], line 23078). So an animal person can take a sentient seat.
- review: CORRECTED the 20 Oct carve-out list from the memory note: giant elephant, giant rhino, elephant, rhino and giant giraffe. The draft left out rhino. The same note says big ocean giants are 'sometimes unhunted OK'.
- review: ADDED the DF-side mismatch, checked in the raws. The woolly mammoth (3-7 a group, about 6 t adults) and Triceratops are BENIGN. A lone giant tick (CLUSTER 1:1) is a paper eater for a mammoth herd. ECO 30 Sep found that prey which is not BENIGN fights back (capybaras killed 5/5 wolves). Whether a bonus eater really hunts its giant is an open rig question.
- review: REFRAMED the options around what the user wants. Removing the step entirely is a fair 'fewer hacks' choice. It matches the user's own acceptance of unhunted elephants, rhinos and ocean giants, and it costs about 1-5% of seasons with an unhunted giant. If the worry is mega-predators, the levers are the apex draw's size weighting and the size-ranked seed, not the bonus seat.
- review: CONFIRMED that nothing breaks. out.bonus is only stored (seasonal-wildlife.lua:11351, 23359, 24757). The diagram only labels the step (mechanics-diagram.html:373). Every weight in the draft checks out (CAST_DEF at 10339: giant 0.2, pack 3, reuse 0.01; ap_pick 0.1 in NR.prmOf at 23349). Parity with the explorer and the 'no bonus' mutant (75 differences) are confirmed in commit 65ef111.
- verifier: Added: the bonus eater goes to the first of apex/meso in its slot list, and apex comes first for apex-class species (10215-10220, 23078). So a T. rex or giant arachnid bonus eater opens a *second apex seat* and can land on the ladder as APX.
- verifier: Clarified: each cast has its own seeded random stream (NR.seedOf), so a roll on that stream moves only that cast's later draws (the vermin shuffle). The year-wide effect comes through the repeat counter.

Code refs: sw-wt/plugin/scripts/seasonal-wildlife.lua:698 (V7.RULES.roster.BONUS_PREDATOR, 12 species); sw-wt/plugin/scripts/seasonal-wildlife.lua:9771-9773 (extinct rule read, UNTAMED_WILDS fallback); sw-wt/plugin/scripts/seasonal-wildlife.lua:9984-9989 (ROSTER.FP.gate: EXTINCT / UNTAMED_WILDS savage-only / ISOLATED small regions; WILDERNESS/DOMESTICATED no bar); sw-wt/plugin/scripts/seasonal-wildlife.lua:10339 (ROSTER.CAST_DEF giant 0.2, pack 3, reuse 0.01); sw-wt/plugin/scripts/seasonal-wildlife.lua:10345-10352 (ROSTER.CAST_SET); sw-wt/plugin/scripts/seasonal-wildlife.lua:22854-22874 (NR.hvSet: seed ranked by pet value and size); sw-wt/plugin/scripts/seasonal-wildlife.lua:22876-22892 (NR.cast weight()/pick(): no size term); sw-wt/plugin/scripts/seasonal-wildlife.lua:22906-22925 (apex draw weighted by sqrt(size)); sw-wt/plugin/scripts/seasonal-wildlife.lua:23046-23066 (cavern web guarantee); sw-wt/plugin/scripts/seasonal-wildlife.lua:23068-23086 (bonus predator seat; slot fallback x.slots[1] at 23078); sw-wt/plugin/scripts/seasonal-wildlife.lua:23087-23103 (vermin shuffle after bonus, shared used counter); sw-wt/plugin/scripts/seasonal-wildlife.lua:23151-23166 (NR.year shuffled order, per-cast seeds); sw-wt/plugin/scripts/seasonal-wildlife.lua:23349-23352 (NR.prmOf ap_pick 0.1); sw-wt/plugin/scripts/seasonal-wildlife.lua:23355-23370 (NR.toRecord: bonus stored); sw-wt/plugin/scripts/seasonal-wildlife.lua:11351, 24757 (bonus only stored, never read back); sw-wt/plugin/tests/web/harness.lua:3219 (MODE nrcast); commit 65ef111 (no-bonus mutant 75); sw-wt/plugin/rules/new-rules.json:9, :236 (BONUS_PREDATOR + note user 20 Oct); DwarfCron/scripts/castsim/foodweb_sim.js:853-865 (explorer bonus seat); DwarfCron/data/pacing/mechanics-diagram.html:373 (step 6 label); DwarfCron/.claude/scratch/sw-questions/d4/out_always.json, out_0.5.json, out_0.json, run.js; DwarfCron/.claude/scratch/sw-questions/d4-review/how.js (theropod seats by origin); DwarfCron/.claude/scratch/pacing/ladder/SAVR_d1.json via summarise.py (Fort 1 ground casts); DF raws vanilla_creatures_extinct/objects/creature_cenozoic.txt (mammoth REAL_WORLD_EXTINCT, SAVAGE, BENIGN, CLUSTER 3:7); memory newrules-port-decisions.md (20 Oct BONUS_PREDATOR, carve-outs); relation-write-needs-large-predator.md (ECO 30 Sep); no-food-web-in-raws.md

</details>

## D5

> What would happen if... the selection of a species for season casts was limited to a maximum of two seasons, instead of allowing outcomes like "Bird albatross Ocean Sp/Su/Au/Wi"? What unintended consequences could arise? What would be the likely impact?

**Short answer.** A hard cap of two would mostly leave seats empty: ocean fish, waterbirds, cavern 1 predators, and grazers in thin biomes. Which seasons go empty would depend on build order, not nature. It would add only about 3-4 new species a year, all in caverns 2 and 3. The albatross repeats because the waterbird slot asks for more birds than exist. Better: size thin slots to their candidate count, add a soft cap (filter, never weight 0) and record forced repeats.

*Status: corrected · confidence medium · review verdict: minor fixes*

### Short answer
A hard cap of two would mostly leave seats empty: ocean fish, waterbirds, cavern 1 predators and, on thin biomes, ground grazers. They would empty in whichever seasons happen to be built last. It would add only a few new species, all in the caverns. Your albatross example comes from a slot asking for more birds than exist. The better fix is to size that slot correctly and add a *soft* cap.

### 1. How seasons are decided today (code)
- **A species' seasons = every cast that holds it.** `ROSTER.castYear` (seasonal-wildlife.lua:10817) builds all casts at once. 10855-10859 give each species every season in which any cast holds it, on any layer.
- **There is no season cap, only a repeat weight.** `weight()` (22879) multiplies by `reuse^(casts already holding it)`, with reuse = 0.01 (10339). `pick()` draws by relative weight. If only an already-used species fits, it still wins every time.
- **The weight counts casts, not seasons.** `used` rises once per cast that holds the species (23114). A sentient seat is counted apart. So a species on two layers in the same season counts twice. On COAST: the cave crocodile (caverns 1 and 2 in autumn) and the giant cave toad (caverns 1 and 3 in winter). A two-season cap needs its own set of seasons per species.
- **Some picks ignore the weight or get around it.**
  - **Seed:** drawn from a tiny high-value set (`NR.hvSet`, 22841). On COAST the draltha seeds cavern 1 in three seasons.
  - **Growth:** picks only among *linked* candidates, so a used linked species beats an unused unlinked one.
  - **Promotion and guarantee predator:** "largest predator promoted" (22930) and the web guarantee's predator (23064) take the largest outright.
  - **Vermin:** no repeat weight at all.
- **Build order and duration.** The build order is a seeded shuffle (`NR.year`, 23151; your 12 Oct ruling against spring-first). Casts are built once and kept until `cast rebuild`, so the same seasons repeat every year.

### 2. Who reaches three or four seasons
| Fort | species in 1 / 2 / 3 / 4 seasons (no vermin) | three- and four-season species |
|---|---|---|
| SAVR_d1 (savage marsh) | 77 / 17 / 8 / 1 | caverns only |
| COAST | 49 / 28 / 10 / 3 | caverns, plus ocean: osprey 4, **albatross 4**, bluefish 3, stingray 3 |
| LAKE3 | 86 / 13 / 12 / 1 | caverns, plus 4 lake fish |
| Good-alignment probe (nrprobe) | 13 at 3+ | ocean fish and waterbirds; cavern 1 (bugbat, rutherer, helmet snake, blind cave bear, crocodile); giant olm (cav 2); flesh ball, voracious crawler (cav 3) |

- SAVR_d1 and LAKE3 have identical cavern casts; COAST differs in two sentient seats. They are one cavern sample.
- **Ground and flying:** no species above two seasons *in these forts*. Thin biomes differ. In D7's desk prototype, tundra and glacier ground species and the tropical moist forest's two grazers (tapir, elephant) hold all four seasons.
- **Why they repeat (probe, 13 species):** 9 are forced by too few candidates. The ocean fish slot is fixed at 3 a season and has 3 candidates; waterbirds have 2; cavern 1 has 6 species for 16 apex/meso/flier/swimmer seats a year. The other 4 are unforced: the rutherer comes back through the seed, the olm, flesh ball and crawler through linked growth.

### 3. Thought experiment: seats fillable under a cap of two
Upper bound by max-flow over the probe's real candidate lists (`.claude/scratch/sw-questions/d5_flow.py`). Links are ignored, so the real builder can only do worse.

| Layer (probe) | No cap | Cap 2 | What empties |
|---|---|---|---|
| Ground | 28/32 | 28/32 | nothing new |
| Flying | 15/16 | 14/16 | one sentient seat |
| Ocean (top of ranges) | 44/48 | **32/48** | 6 fish, 4 waterbird, 2 shore |
| Ocean (low end of ranges) | 32/36 | 26/36 | 6 fish |
| Cavern 1 | 24/24 | **20/24** | 4 flier/swimmer seats |
| Caverns 2, 3 | 24/24 | 24/24 | nothing |

- **Waterbirds:** COAST drew 2 a season in all four seasons, from only the osprey and the albatross. Under a hard cap, the first two ocean casts built use both birds and the other two seasons get **none**. Which seasons lose out depends on the shuffle.
- **Fish:** the probe has 3 candidates for 12 seats, so a cap allows 6. COAST has 5 for 12, so at most 10.
- **Thin ground biomes** (desk prototype): in tropical moist forest, tapir and elephant can fill only 4 of the 8 grazer seats.
- **Gains** (inference): about +3-4 new species a year, all in caverns 2 and 3, which have 36 and 43 candidates but only 17 and 16 cast. Nothing is gained in the ocean or cavern 1.

### 4. Unintended consequences
1. **Holes, not variety, wherever candidates are few.** This breaks your rule that every unfilled slot has a reason and a fallback. Today's note (23041) knows only "none in season" and "all candidates used in other slots", so a capped slot gets the wrong label.
2. **A code trap if the cap is a zero weight.** When all weights are 0, `pick()` returns nil (22885-22887), and growth's `if not x then break end` (23020, 23032) stops the **whole cast**, not one slot. The apex draw does the opposite: it picks the first eligible apex, so the cap is silently ignored there. `cast set reuse 0` already behaves this way: a cap of one with the same trap. A real cap must *filter* species out.
3. **Gaps follow the build order.** That brings back the order effect you removed on 12 Oct.
4. **One layer starves another.** Shared cavern species get used up by whichever cavern is built first. `castAddMissing` (a freshwater cast added when water is found late, 1d3db1d) is built last and would find its shared species capped.
5. **Weaker apexes and fallbacks.** Capped species drop the apex draw to a local apex or promotion. The guarantee and the bonus predator need an uncapped predator. Growth falls back to "no link: filled anyway" (23033).
6. **Arrivals concentrate.** Fewer species share the same water draws and DF cavern waves. DF's cavern pick seems to follow stock (PENDING).
7. **The map changes less than the list suggests.** Out-of-season species only have their entries closed (pause, not trim). Groups already on the map stay until they leave.
8. **Small effects:** the ladder shifts slightly, and the harpy's sentient seat (about 1 season a year) is seldom hit.

**Where nothing changes:**
- **Ground and flying on forts with long lists.**
- **Forts with only ponds.** On the real pond fort probed (V8E_A1/A2), the pond list admits any species with lake, river or pool in its raws (10091). It holds 15 candidates (12 in winter), so a cap of two binds nothing.
- **No water:** no water casts.
- **Savage and evil forts:** longer lists, so the cap binds less.
- **Unbreached caverns:** the casts are built either way.

**One real benefit:** the flesh ball loses its third cavern 3 season. It took 54% of cavern 3 groups in B1. `open_stock` already targets that, and B2 is measuring it.

### 5. Does it serve your aims?
- **Diversity:** slightly, caverns 2-3 only.
- **Ecology:** worse, with empty fish, waterbird and predator seats and looser links.
- **Natural seasons:** it depends on the species.
  - Albatross and osprey really are seasonal, so your instinct is right for them.
  - Fish, cave fauna and resident grazers live there all year.
  - A plain cap does not give a continuous stay: a bird could get spring and autumn with a gap in summer.
  - The raws carry no migration tag, and I found no code that reads one.

### 6. What I would do instead
1. **Size thin slots to their candidates.** Want = `min(slot range, ceil(2 × candidates ÷ 4))`, never below the minimum. With 2 waterbirds, each season asks for 1, so each bird gets 2 seasons and there is no hole. Fish are fixed at 3; lowering that is your call.
2. **Soft cap of two.** *Filter out* species already at 2 seasons while anything else is eligible; fall back to x0.01 only when nothing else is left. Apply it to the seed, the apex draw, growth (an unused unlinked species beats a capped linked one), promotion and the guarantee. Count seasons, not casts.
3. **Record every forced third or fourth season with its reason** ("albatross: only waterbird candidate").
4. **Fix the seed repeats:** take a species out of the seed set after it has seeded twice.
5. **Optional:** prefer neighbouring seasons for a species' second season.
6. **Decide** whether vermin get any repeat weight.

### 7. What would settle it
- **Desk first:** `NR.year` over about 200 site/year seeds in three worlds (good coast, savage marsh, lake), plus a thin biome (tropical moist or tundra). Arms: today, hard cap 2 (filter), soft cap 2, soft cap + right-sizing. Count:
  - distinct species a year;
  - empty seats by layer, slot and season;
  - seasons with no apex, prey or waterbird;
  - `NR.seasonHoles`;
  - forced 3rd and 4th seasons;
  - species whose two seasons are not neighbours.
- **Rig second:** a COAST-like ocean fort, today vs soft cap + right-sizing, n=5 per arm, startdwarf 50, breached. Count distinct species arriving per season, by layer.

**Rig test that would settle it:** Desk first: V7.NR.year over about 200 site/year seeds in good coast, savage marsh, lake and one thin biome (tropical moist or tundra); arms today / hard cap 2 (filter) / soft cap 2 / soft cap + right-sized thin slots; count distinct species, empty seats by layer/slot/season, seasons with no apex/prey/waterbird, NR.seasonHoles, forced 3rd-4th seasons, non-neighbouring seasons. Then rig: COAST-like ocean fort, today vs soft cap + right-sizing, n=5 per arm, startdwarf 50, breached at the outset; distinct species arriving per season by layer.

<details><summary>Review and verification trail</summary>

- review: Cavern 1 empty seats under a cap of 2 in the good-alignment world are 2 flier + 2 swimmer (d5_flow.py on nrprobe-V83NR_GOOD), not '3 swimmer, 1 flier' (3 swimmer + 1 apex is the V8E_A2 world). Max-flow has several optimal answers, so the honest statement is '4 seats among the apex/meso/flier/swimmer group'.
- review: The 'today' ocean column (44/48) was the top of each slot range, not what the builder did. The real GOOD build filled 37 ocean seats, because the waterbird, meso and shore wants are drawn per cast from their ranges (NR.cast line 22865 rg.int(x[2], x[3]); SLOTS line 805: waterbird {1,2}). COAST wanting 2 waterbirds in all four seasons was verified in COAST.json, but it is the worst case. In GOOD the wants were 1,2,1,2.
- review: Added a worked GOOD example from the real build order. Ocean casts were built 11 (Au), 12 (Wi), 16 (Sp), 24 (Su). Under a hard cap the summer cast, built last and wanting 2 birds, gets no waterbird.
- review: Corrected the apex fallback claim. hasTrue (22908) is decided from eligibility, not from weights. If the cap were done by setting a weight to 0, the apex draw would still pick a capped true apex: with tot=0 and r=0, the first eligible is chosen at 22922. It falls back to a local apex only if capped species are filtered out of the eligible list.
- review: Added the trap the original answer missed. A hard cap done as weight 0 makes pick() return nil (22885-22887), and growth then runs `if not x then break end` (23020, 23032). That stops the WHOLE cast, not just the capped slot. The later slots go unfilled and are labelled 'all candidates used in other slots' (23041). A hard cap has to be a filter on the free and eligible lists.
- review: Added that `cast set reuse 0` already exists (CAST_SET min 0, line 10349; 0^0=1, 0^n=0). It amounts to a hard cap of one cast per species per year, and it has the same break trap. It should not be used as a quick test of this idea.
- review: Added that the repeat brake counts casts, not seasons (used[] incremented once per cast at 23114). A species on two layers in one season (bugbat cavern1+2, cave crocodile cavern1+2, giant cave toad cavern1+3 in COAST) is counted twice. A 'two seasons' cap needs a per-species season set.
- review: Fixed the naturalism point. The albatross (a far-ranging seabird that comes ashore mainly to breed) and the osprey (migratory in temperate zones) are the user's example, and for them a seasonal presence is more natural, not less. Fish and cave fauna are the year-round residents. Also added that the builder has no notion of contiguous seasons: a capped bird could get Sp+Au with a gap in summer, which is less natural for a migrant than a contiguous stretch.
- review: Corrected 'about 4 new species a year' to 'about 4 seats moved'. In caverns 2 and 3 these very likely go to never-cast species (cavern2: 36 candidates, 17 cast; cavern3: 43 candidates, 16 cast; an unused one weighs 1 against 0.01). In cavern 1 only the rutherer's seat can move. The ocean gains nothing, because all 3 fish and both waterbirds are already cast.
- review: Cut the unverified claim that vanilla has 'only 6 temperate or cold true land apexes'.
- review: Toned down the claimed conflict with the 17 Oct sentient exemption. Commit 6c79f93 measured the harpy at 25% of flying casts, about 1 season a year, so a cap of 2 seldom binds there. The exemption is about how seats are counted, not a promise of recurrence.
- review: Verified: the random build order rationale (memory full-pool-design-oct9: Spring-first overweighted Spring, pack hunters 30.8% Spring vs 22.5% Winter); the reuse 0.01 default from 12 Oct (10419, edf27f2); castAddMissing building after all other casts and counting them (10900-10950, 1d3db1d); one_per_species in the water draw (7796, 1028); the roster-builder ruling 'every unfilled slot must be reported with its reason and have a fallback'.
- review: Classified the three-and-four-season species by cause in the GOOD world: 9 of 13 are supply-forced (3 ocean fish, 2 waterbirds, and in cavern 1 bugbat, helmet snake, blind cave bear and cave crocodile, where 6 species fill 16 apex/meso/flier/swimmer seats). 4 of 13 are not forced: the rutherer (seed set), the giant olm, the voracious cave crawler and the flesh ball. Added targeted fixes for the unforced repeats, such as a wider seed set or a seed brake.
- verifier: The three ladder dumps' cavern casts are not all identical. SAVR_d1 and LAKE3 match in all 12 cavern-seasons; COAST differs in the sentient seat of cavern 2 spring and cavern 3 autumn. They are still one cavern sample.
- verifier: The bugbat was a wrong example of 'two layers, same season'. On COAST it is in cavern 1 spring and summer and cavern 2 winter. Correct examples: the cave crocodile (cavern 1 and 2 in autumn) and the giant cave toad (cavern 1 and 3 in winter).
- verifier: 'Ground and flying: nothing changes' holds only for forts with long candidate lists. On thin biomes (desk prototype, D7) ground species hold 3-4 seasons: tapir and elephant are the only grazers in tropical moist forest, plus tundra and glacier. A cap of two would empty grazer seats there.
- verifier: Ponds: on the real pond fort probed (V8E_A1/A2), 15 candidates (12 in winter) fill every seat under a cap of two. A cap of one would leave one meso seat empty (3 meso candidates for 4 seats), so the earlier 'even with a cap of one' was wrong.

Code refs: /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:10817 (ROSTER.castYear; seasons = union over casts, 10855-10859); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:3088 (ROSTER.castSeasonsOf); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:10339 (CAST_DEF reuse 0.01); 10349 (CAST_SET reuse min 0); 10419 (0.1 -> 0.01 migration); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:805-808 (V7.RULES SLOTS: ocean waterbird 1-2, fish 3-3); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:22841 (NR.hvSet seed set); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:22862-22865 (NR.cast; want drawn per cast rg.int); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:22879 (weight: reuse ^ used); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:22885-22891 (pick: nil when total weight 0); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:22905-22930 (apex draw: tier from eligibility; zero weights pick first; largest predator promoted); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:23020, 23032 (growth: `if not x then break end` stops the whole cast); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:23033 (no link: filled anyway); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:23041 (unfilled reasons); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:23044-23066 (cavern web guarantee); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:23068-23084 (bonus predator); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:23087-23110 (vermin: no repeat weight); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:23114 (used counted per cast); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:23151 (NR.year shuffled build order); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:23208 (NR.seasonHoles); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:10900-10950 (castAddMissing, built after all casts); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:7796, 1028 (water draw one_per_species); git 6c79f93 (sentient seats counted apart; harpy 10% -> 25% of casts); git 1d3db1d (castAddMissing), edf27f2 (reuse 0.01); /Users/nathanielcannon/Claude/Projects/DwarfCron/.claude/scratch/pacing/ladder/COAST.json (ocean waterbird 2 per season: osprey+albatross); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/nrprobe/nrprobe-V83NR_GOOD.json (candidate lists, casts, build order); /Users/nathanielcannon/Claude/Projects/DwarfCron/.claude/scratch/sw-questions/d5_flow.py, d5_seasons.py; memory: full-pool-design-oct9.md (random order rationale), roster-builder-decisions.md (unfilled slot needs reason + fallback), pause-not-trim.md, cavern-pick-stock-weighted.md

</details>

## D6

> How often does this happen "Unfilled slots are recorded (\"none in season\", \"all candidates used in other slots\")."? Can I find that information in the DFhack UI or browser UI somewhere?

**Short answer.** It depends on the fort, and a gap repeats every year until `cast rebuild`, because casts are built once and kept. Real forts: savage marsh 1 of 24 casts, savage lake 1 certain, calm coast 13 of 24 (mostly the empty animal-person seat). In simulation, 20% of casts have a gap, mostly harmless. Two gaps are real losses: the cavern 1 swimmer and the evil-fort harpy seat. You can see gaps in the game window (Year tab 'u', This season Lanes), on the browser page (Year 'N unfilled' chip, Members view) and with `cast show`. Nothing totals them.

*Status: verified · confidence high · review verdict: minor fixes*

### Short answer
How often depends on the fort, and once a fort has a gap it keeps it. The tool builds a fort's casts (up to 28: 7 layers × 4 seasons) once, at `enable`, and keeps them every year (seasonal-wildlife.lua:9598; your 9 Oct ruling). Only `cast rebuild` changes them. Most gaps are harmless: no species exists for that slot. Two kinds are real losses. You can see every gap in the game window, the browser page and the console, but nothing adds them up.

### (a) What the code does
**When a gap is recorded** (`NR.cast`, 22862 on):
1. Each slot gets its "want" from the slot table (797-805). Only lake and ocean meso, shore and waterbird are drawn as 1-2; the rest are fixed. The want is kept as `wantFixed`.
2. Apex draw, seed, then growth.
3. Growth gives up on a slot when no candidate not yet in the cast still fits it (`want[s] = have[s]`, 23029). It stops when no such candidate remains (22998).
4. Each slot holding fewer than wanted gets the note `"<have> of <want>: all candidates used in other slots"` if anything in the season's list can take that slot, or `"none in season"` otherwise (23037-23042).
5. `NR.toRecord` saves the note (23358).

**What the wording really means.** By step 3, every candidate for that slot is already in *this* cast, in that slot or another. The one exception is a zero-weight setting that stops growth early.
- "All candidates used in other slots" can mislead. A calm lake whose only fish is carp shows `fish: 1 of 3: all candidates used in other slots`, though the carp sits in the fish slot itself. The truth is "there is only one fish".
- "Other slots" means this cast only. Other casts never block a species; they only lower its odds (x0.01 per cast already holding it, 22879, 10339). The comment at 9593 still says 0.1 and is out of date.
- The cavern guarantee (23044) and the bonus predator (23068) run after the note. They take only candidates not yet in the cast, so they never fill a slot that was noted unfilled.

**Where you can see it**

| Place | What it shows | Code |
|---|---|---|
| Game window, **Year** tab | cells like `5+2 1u`. The u is dark grey (only holes turn a cell red), so it is easy to miss | gui/seasonal-wildlife.lua:2777-2778, legend 511 |
| Game window, **This season** → Lanes | a yellow line `unfilled swimmer: 0 of 1: …` (not in the Links view) | gui 2683 |
| Browser page (127.0.0.1:8642), **The year** | amber chip "N unfilled"; hover for the reasons | seasonal-wildlife-web.html:2239 |
| Browser page, **This season** → Members | "Unfilled: slot: n of m: reason" (not in the default Lanes graph) | web.html:2192, 2216 |
| Console | `seasonal-wildlife cast show autumn [cavern1]` prints `unfilled <slot> <why>` | 24974 |
| Log | the cast-build line gives **spring** member counts only, with no reasons | 10896 |
| Food Web Explorer | a "casts with an unfilled slot" tile per layer, and "unfilled: slot n of m" per cell | foodweb_app.js:797, 873 |

Undiscovered caverns are hidden in the window and the page but shown in the console. Don't confuse gaps with **holes** ("h", red): a hole is a cast member with no food link. A gap is an empty seat.

### How often
**Real forts** (`.claude/scratch/pacing/ladder/`). The record files lack the note and the drawn want, so gaps were worked out against the slot table (`d6/count_unfilled.py`):
- **SAVR_d1** (savage): 1 of 24 casts, the cavern 1 autumn swimmer.
- **COAST** (calm): 13 of 24. The animal-person seat is empty on ground, flying and ocean in all four seasons (12), plus the same cavern 1 swimmer gap.
- **LAKE3** (savage): 1 certain (the cavern 1 swimmer). Seven range slots hold 1 where the want may have been 2; the record can't settle these.

All three are site 266, year 100 in one world, so the cavern 1 swimmer gap is **one draw seen three times**. How it happened (I checked the record):
- The cave crocodile was drawn apex.
- The giant cave toad was the seed. The seed takes the first of its tied open slots, and a cave predator lists meso before swimmer (22944, 10205-10209), so the toad went to meso.
- Those two are the only cavern 1 swimmers, so the seat stayed empty.

**Simulation** (the explorer's builder, 6 test forts × 200 builds; read it as 200 forts per site): **20.1%** of casts have at least one gap.
- **Animal-person seat, "none in season":** always empty on ground and flying on calm forts that are not evil. DF only stocks animal people on savage land (ANIMAL_PERSON adds `[SAVAGE]`, c_variation_default.txt).
- **Fresh-water fish and waterbirds:** the brook's list has none; the calm lake has one fish (carp) for 3 seats; the evil tundra ponds drop to one fish (leech) in winter. The real savage LAKE3 fills fish 3 of 3.
- **Flying animal-person seat, "all candidates used": 32% of the evil fort's flying casts.** The harpy is the only sentient flier and can also hold apex (your 17 Oct ruling). When it is drawn apex, nobody is left for the sentient seat.
- **Cavern 1 swimmer:** about 2% of cavern 1 casts on every fort.
- Caverns 2-3 and savage surface layers were always full.

### (b) What DF does
DF has no slots. A gap is just one species fewer opened that season, and one fewer for the FREQUENCY ladder to share out. That last part is my inference; it is not rig-checked.

### (c) Does this serve diversity and ecology?
- **Animal-person gaps on calm forts are correct, but noisy.** About 12 "u" marks on every calm fort bury the gaps that matter. Hide a slot that is "none in season" in all four seasons, or leave it out of the table on calm forts.
- **Water gaps on brooks, ponds and calm lakes are honest shortages.** If you want fuller water casts, change those slot tables.
- **The cavern 1 swimmer gap is caused by the builder.** Breaking ties toward the slot with the fewest other candidates would put the toad in swimmer and let a meso-only predator take meso: +1 species. It is a proposal, untested.
- **The harpy gap comes from your ruling, not the tie-break.** Your options:
  - accept it;
  - move the harpy to the sentient seat when it is the only one, and redraw the apex;
  - lower its apex odds.
- **Wording:** say "only N candidates" when they all sit in this slot, and "taken by apex/meso: X" when they went elsewhere. Add one build-log line, "K unfilled slots, by reason", to answer "how often" at a glance.

### What would settle it on the rig
Not run. When the rig is free, on each B2 fort (CALM, COAST, EVIL, LAKE, SAVR): `seasonal-wildlife cast show spring|summer|autumn|winter` (four read-only calls), or open The year tab. That gives the exact reasons and the drawn wants. The notes live in the save's DFHack site data and can't be read off disk without DF.

**Rig test that would settle it:** When the rig is free, on each B2 fort (CALM, COAST, EVIL, LAKE, SAVR): `seasonal-wildlife cast show spring|summer|autumn|winter` (read-only) or open The year tab, to read the stored reasons and drawn wants and check the simulator's rates against real forts.

<details><summary>Review and verification trail</summary>

- review: Quirk 3 corrected from 'rare' to 'does not happen in practice'. NR.cast's growth loop (seasonal-wildlife.lua:22989-23035) gives up on a slot only when no candidate that is not yet in the cast still fits it (:23026-23029), and it stops when no such candidate is left (:22998). So when the note is written (:23037-23042), every candidate for that slot is already in this cast. The web guarantee (:23048-23054) and the bonus predator (:23076) only take candidates not yet in the cast, so neither can later fill a slot that was noted as unfilled.
- review: The same reasoning sharpens quirk 1. 'all candidates used in other slots' really means 'every candidate for this slot is already in this cast, in this slot or in another one' (n counts has(x.slots, s) over the whole season list, :23039).
- review: 'On every calm fort (sav 50)' was wrong. evil_tundra_pools is also sav 50, yet its ground sentient slot is 0% unfilled and its flying sentient slot 32%. The 100% ground and flying sentient gaps are on the two calm forts that are not evil (calm lake, good brook). The fresh-water sentient gap is on three forts (those two plus the evil tundra ponds): 2400 = 3 x 800, 1600 = 2 x 800. I re-ran sim_unfilled.js and detail.js and got identical totals.
- review: Framing fix. The simulator's '200 years' are 200 different builds (NR.year is seeded by site and year, :23155), because a fort builds its casts once and keeps them (:9598; ROSTER.castYear called only at enable :20926, cast rebuild :24916, roster build :25024, migration :21215). So the percentages are the chance that a given fort's cast has the gap. They are not how often it recurs in one fort. In one fort a gap is either there every year or never, until a rebuild.
- review: The real-fort swimmer gap is no longer an inference. SAVR_d1.json cavern1 autumn has seed = TOAD_GIANT_CAVE. The seed step (:22944) keeps the first slot in the species' own list when slots tie (strict >), and slotsFor lists meso before swimmer (:10205-10209), so the toad went to meso. The giant cave crocodile was drawn apex. By the invariant above, every swimmer candidate is in that cast, and its only water animals are the crocodile and the toad. With n > 0 the stored reason must be 'all candidates used in other slots'. Verified that both are [AMPHIBIOUS] [BIOME:SUBTERRANEAN_WATER] in the vanilla raws.
- review: Animal people only on savage land is now grounded in the raws, not inferred: the ANIMAL_PERSON creature variation adds [CV_NEW_TAG:SAVAGE] (vanilla_creatures/objects/c_variation_default.txt).
- review: UI precision. In the game window, This season shows the yellow 'unfilled' line only in the Lanes view, not in Links (gui/seasonal-wildlife.lua:2665 vs :2683). On the web page, This season shows 'Unfilled:' only in the Members view, not in the default Lanes graph (seasonal-wildlife-web.html:2208 vs 2216, castsListHtml :2192). The Year tab's 'Nu' is drawn in dark grey unless the cell also has holes (:2777-2778), so it is easy to miss.
- review: Undiscovered caverns are hidden in both UIs (gui :2659-2661 and :2770; web laneList :2085), but the console `cast show` prints them (:24966-24974). The explorer's cell line shows only 'slot have of want' without the reason (foodweb_app.js:873 keeps only the text before the first ':').
- review: Ledger nuance added: the build line does carry spring member counts per layer (:10896), so a count below full hints at a gap, but it covers spring only and gives no reason. Example: P2_EVIL ledger 'spring ground 8+3, flying 4+2, cavern1 6+2 ...' are all full.
- review: Added that 'holes' (h, red) are a different thing from unfilled: a hole is a cast member with no food link in its realm (gui holeWord :2493; castsViewLive :11436-11441).
- review: The harpy gap is a side effect of a ruling, not just a builder flaw. User 17 Oct: a curated evil apex keeps its apex seat (slotsFor :10212-10216, commit 1dc3d42). The proposed 'fewest alternatives' tie-break fixes the cavern swimmer (seed and growth) but not the harpy, which is placed by the apex draw (:22907-22931). Moving the harpy also changes which seat (and so which ladder treatment) it gets, so it is the user's call.
- review: The sim's calm-lake fish shortage depends on the fort type. In the explorer's data, carp is the only fish candidate on a calm temperate lake (detail.js output). The real savage LAKE3 fills fish 3 of 3 (prehistoric species, sturgeon, carp).
- review: Stale doc noted: the header at :9593 says repeat weight x0.1, but the live default is reuse = 0.01 (ROSTER.CAST_DEF :10339; old 0.1 configs migrated at :10419; NR.prmOf :23351).
- verifier: Wording: a fort has up to 28 casts (7 layers x 4 seasons). The three real forts have 24, because each lacks either ocean or fresh water.

Code refs: sw-wt/plugin/scripts/seasonal-wildlife.lua:797-805 (RO.SLOTS slot tables and want ranges); sw-wt/plugin/scripts/seasonal-wildlife.lua:9590-9598 (casts built once at enable and kept; header still says x0.1); sw-wt/plugin/scripts/seasonal-wildlife.lua:10205-10216 (ROSTER.FP.slotsFor: cavern order apex, meso, ..., swimmer; sentient-only; evil apex gets apex+sentient); sw-wt/plugin/scripts/seasonal-wildlife.lua:10339 (ROSTER.CAST_DEF reuse = 0.01); sw-wt/plugin/scripts/seasonal-wildlife.lua:10817-10898 (ROSTER.castYear; ledger line :10896 spring counts only); sw-wt/plugin/scripts/seasonal-wildlife.lua:11347-11351 (ROSTER.castsView unfilled list); sw-wt/plugin/scripts/seasonal-wildlife.lua:11436-11441 (holes = unfed/unlinked members); sw-wt/plugin/scripts/seasonal-wildlife.lua:22862-22867 (NR.cast want and wantFixed); sw-wt/plugin/scripts/seasonal-wildlife.lua:22879 (repeat weight prm.reuse^n); sw-wt/plugin/scripts/seasonal-wildlife.lua:22907-22931 (apex draw); sw-wt/plugin/scripts/seasonal-wildlife.lua:22939-22946 (seed: first tied slot, strict >); sw-wt/plugin/scripts/seasonal-wildlife.lua:22989-23035 (growth; :22998 stop; :23029 give up a slot); sw-wt/plugin/scripts/seasonal-wildlife.lua:23037-23042 (unfilled note and its two reasons); sw-wt/plugin/scripts/seasonal-wildlife.lua:23044-23085 (guarantee and bonus take only candidates not yet in the cast); sw-wt/plugin/scripts/seasonal-wildlife.lua:23153-23155 (NR.year seeded by site and year); sw-wt/plugin/scripts/seasonal-wildlife.lua:23355-23358 (NR.toRecord stores unfilled, want); sw-wt/plugin/scripts/seasonal-wildlife.lua:20926, 21215, 24916, 25024 (only cast build call sites); sw-wt/plugin/scripts/seasonal-wildlife.lua:24963-24974 (console cast show prints unfilled); sw-wt/plugin/scripts/gui/seasonal-wildlife.lua:511, 2659-2683, 2770-2778 (Year 'u', This season Lanes view unfilled line, hidden caverns); sw-wt/plugin/scripts/seasonal-wildlife-web.html:2085, 2181-2192, 2216, 2239 (hidden lanes; Members view Unfilled line; Year chip); DwarfCron/scripts/castsim/foodweb_sim.js:831-833; foodweb_app.js:747, 797, 873; DwarfCron/.claude/scratch/pacing/ladder/SAVR_d1.json (cavern1 autumn seed TOAD_GIANT_CAVE, swimmer []); DwarfCron/.claude/scratch/sw-questions/d6/count_unfilled.py, sim_unfilled.js, detail.js (re-run, same totals); DwarfCron/data/pacing/B2/P2_EVIL/ledger.txt (cast-build line, spring counts); DF vanilla raws: vanilla_creatures/objects/c_variation_default.txt ANIMAL_PERSON adds [SAVAGE]

</details>

## D7

> BIG QUESTION: How can I see and understand the distribution of species seasonal availability per biome? I need something like frequency graphs for "species in the candidate list that can live on this layer in this season" for each biome. What I want is to view, at the biome level, all species that can be in that biome, and see the seasons that they are available in. I need to see and understand two things really: how species-rich is each season relative to the others, at the biome level and how seasonally ubiquitous is each animal species within the given biome that I am viewing. I guess that creature tags for seasonal presence are not conditional on biome. On the other hand, the subset of species available in a given biome differs from other biomes. Therefore each biome has its own distribution of species richness, and the set of species of any given biome may include fewer or more species which are seasonally ubiquitous. I believe that these two things (biome presence and seasonal presence) are part of the DF mechanics which unintentionally swamp out potential seasonal and biome diversity of species. How can I see and understand these distributions? Can we think about how to work around or modify these distributions to enforce greater inter-biome and inter-seasonal diversity?

**Short answer.** Today you can see it only in pieces: `cast show` prints each cast's candidate count, and `cast nrprobe` exports the full lists. Nothing draws biome x season. A desk prototype shows the raws carry almost no seasonal signal: only 23 vanilla creatures have a NO_<season> tag, so spring = summer = autumn and winter is 0-25% thinner. All-year species come from slots with too few fitting species, not from tags. Which season a species lands in is a random draw kept for the fort's life. Proposed: a Seasons tab in the Food Web Explorer. Levers: per-season slot tables, slot wants sized to their candidates, and a small seasonal-habits table or lean for migrants and hibernators. Each needs your ruling.

*Status: corrected · confidence high · review verdict: minor fixes*

### Short answer
**Can you see it now?** Only in pieces:
- `seasonal-wildlife cast show <season> [layer]` prints how many candidates each cast was drawn from ("pool N"; the code's name for the candidate list).
- `cast nrprobe PATH` writes a fort's full candidate lists, per layer and season, as JSON.

Nothing draws the biome × season × species picture. I built a desk prototype from the vanilla raws with the desk copy of the cast builder. It partly overturns your hypothesis:
- **Seasons:** the raws carry almost no seasonal signal. Only **23** vanilla creatures have any NO_<season> tag (verified: 23 NO_WINTER, 2 NO_AUTUMN, 1 NO_SPRING). So in every biome the spring, summer and autumn lists are the same, and winter is 0-25% thinner. In DF, almost every species can come in every season.
- **Biomes:** ground lists differ a lot between biomes. Flying is the layer full of generalists.
- **All-year species in a cast** come from a slot with too few fitting species, not from list size. Tropical moist forest has 43 ground candidates but only tapir and elephant fit the 2-seat grazer slot, so both are cast in all four seasons.
- **Flat richness across seasons** comes from the slot tables: every season gets the same table.
- **Which season a species lands in** is a random draw, kept for the fort's whole life.

### 1. What the code does (v8.1-pacing @ 6dffef5)
**The candidate list.**
- `buildPool` (2655) walks every creature in the raws.
- `ROSTER.FP.mark` (10114) keeps the wild ones and places them by:
  - `FP.biomesOf` (9726): raw biomes, narrowed by BIOME_LIMIT;
  - `FP.gate` (9976): savage, good/evil and extinct rules;
  - `FP.layersOf` (10034): which of the 7 layers.
- `ROSTER.FP.candidates` (10296) has one season test (10306): the raw's own NO_<season> on all castes (`classify`, 2134-2139). That is read before `seasons_own` clears the flags in DF (18020-18025).
- **So:** the biome decides *whether* a species is a candidate, and almost never *when*.

**The casts.**
- All casts are built **once**, at enable or embark (`NR.year`, 23151), in an order shuffled by site and year.
- They are kept for the fort's life (your 9 Oct ruling, 5068-5071, 9598). Only `cast rebuild` redraws.
- `weight()` (22876-22885) applies pack x3, the repeat weight 0.01^(casts already holding it), giant x0.2, animal person x0.1 and cavern weirdness. **It has no season factor.**
- The slot tables (`RO.SLOTS`, 797) are keyed by layer only. Ground, for example, is apex 1, meso 2, grazer 2, ground prey 2, sentient 1, plus 3 vermin, every season.
- The shuffled order is your 12 Oct ruling (spring-first had given spring the pick of the all-year species).

**Older season code, now dormant.** The climate lean (`SEASON_SETS` 602, `climateRange` 2635, `buildPool` 2668-2673) still computes, but the cast build overwrites its result. `VERMIN.defaultSeasons` (4150), insects in spring-autumn, now runs only as a manual verb. It is a precedent for a small seasonal-habits rule.

**What you can look at today.**

| Where | What it shows |
|---|---|
| `cast show <season> [layer]` (24963-24975) | candidate count per cast, unfilled slots and why |
| `cast pool [TOKEN]` (24667) | entries per layer, no season split |
| `cast nrprobe PATH` (24713) | every layer × season candidate list, as JSON (one-shot, safe) |
| Web casts view | receives the count (11352) but doesn't show it; shows "Unfilled" |
| Food Web Explorer | season buttons switch "by raws" / "by casts" (foodweb_app.js:184-195); no richness chart |

### 2. What the distributions look like (desk prototype, vanilla raws)
Setup: one land biome per fort under calm/savage/evil/good, extinct rule UNTAMED_WILDS, 40 different forts per row (not 40 years). Files: `.claude/scratch/sw-questions/d7/richness.json`, `casts.json`.

**Seasons in the raws.**
- The tagged creatures: black and grizzly bear, badger, groundhog, rabbit, weasel, two squirrels, chipmunk, hedgehog, lizard, toad, tree frog, pond turtle, bat, six insects, hoary marmot (no autumn or winter) and moghopper (summer only). Giant and animal-person copies inherit the tag.
- Across all 27 land biomes, spring = summer = autumn. The one exception is mountain (11/11/10/10).
- Winter is 0-25% thinner for animals and up to 50% thinner for flying vermin.
- Examples, ground: temperate broadleaf calm 32/32/32/28; tropical moist 43/43/43/42; glacier 2/2/2/2.

**Biomes.**
- **Calm ground:** 106 species across 27 biomes. 68 live in 4 or fewer biomes; 25 of the 27 lists are different; mean overlap (Jaccard) 0.22.
- **Calm flying:** mean overlap 0.46, only 19 distinct lists. The eagle is in 27/27 biomes, the peregrine in 25, the barn owl in 22.
- **Savage** lists are 2.9-8.2x longer, through giants and animal people (mountain 11 → 32; temperate broadleaf 32 → 182). They are weighted x0.2 and x0.1 in the draw.

**What the casts make of it** (40 forts per row)

| Fort, layer | Candidates | Seats a year | Species cast | Seasons each holds |
|---|---|---|---|---|
| Temperate broadleaf, calm, ground | 32 | 28 | 24.1 | 84% one, 16% two |
| Temperate broadleaf, savage, ground | 182 | 32 | 31.9 | 99.7% one |
| Tropical moist, calm, ground | 43 | 28 | 21.8 | **tapir and elephant all 4 in 40/40** |
| Tundra, calm, ground | 9 | 24 | 9 | per fort ≈1 one, 3 two, 3 three, 2 four |
| Glacier, calm, ground | 2 | 8 | 2 | wolf and polar bear all 4 |
| Temperate grassland, flying | 8 | 12 | 8 | 4 one season, 4 two |
| Temperate ocean | 32 | 37.8 | 19.4 | ≈3.4 species all year |

**Ponds: the prototype's pond list was wrong, so I dropped it.** The engine admits any species with lake, river or pool in its raws to the pond list (10091). The real pond fort probed (nrprobe V8E_A1/A2) has **15** candidates, 12 in winter (frog, turtle and toad drop out). Its pond casts hold every species in one season, except the sea lamprey in two. The prototype's other water rows may share the same gap.

**Real forts agree on the surface.**
- SAVR_d1 ground: 32 animal seats, 32 species, each in one season.
- COAST: the albatross and osprey hold all four ocean seasons; 6 birds fill 12 flying seats, two seasons each.

**The rule:** seasons per species ≈ **the slot's seats a year ÷ the species that fit it**. Many fit → x0.01 puts each in one random season. Few fit (tundra, glacier, the ocean waterbird slot, a 2-grazer forest) → the same species every season.

### 3. Your hypothesis, checked
- **"Seasonal presence swamps seasonal diversity."** Not through tags; there are almost none. Vanilla DF has no seasonal turnover. The tool creates turnover, but at random, and keeps it for the fort's life: a moose drawn into winter is a winter-only moose for good.
- **"Biome presence swamps biome diversity."**
  - Mostly not on the ground.
  - Yes on flying: the same raptors and owls everywhere.
  - Caverns don't follow the surface at all, by your assignment (5817-5830).
  - The real biome-level problem is **slot fit and list length**: glacier, tundra and mountain lists are too short to vary, and savage lists are padded with copies.
- **Is "all year" bad?** In nature many residents (deer, wolves, owls) stay all year. Turnover comes from migrants, hibernators and insects. Today's builder pushes every species into one season, which serves diversity, not naturalism. The all-year species it does produce come from slot shortage, not biology. The real choice is **maximum turnover vs a resident core plus seasonal visitors**, and it is yours.

### 4. How to see it
**Proposed:** a "Seasons" tab in the Food Web Explorer, which already has the desk builder and the biome and surroundings pickers. Label it as computed from raws plus the desk builder, not a live fort. It would show:
1. **Bars per biome:** candidate counts per layer for spring/summer/autumn/winter, split apex/predator/prey/vermin, with a calm/savage/evil/good switch.
2. **A season strip per biome:** one row per species, four cells. Outline = the raws allow it; fill = the share of forts casting it then. Sorted by seasons held, with the slot that caused it.
3. **Slot pressure per biome:** seats a year ÷ fitting species. This predicts the all-year species.
4. **Histograms** of seasons allowed vs cast, a biome-similarity heatmap, and biomes per species.

For a real fort: show the candidate count the web casts view already receives, next to "Unfilled". `cast nrprobe` already exports the lists. I have not published the prototype; I'll show it only if you want it.

### 5. Ways to get more variety
1. **A slot table per season**, for example thinner winter prey and vermin. This is the only lever that sets how rich each season is. It changes your 9 Oct slot tables and the 7 Oct "~10-12 per layer per season" ruling. Caveat: fewer winter species may not mean fewer winter waves, just more waves for each species (rig test below).
2. **A season preference where biology has one.** Revive the climate lean as a factor in `weight()`, only for flying and waterbird slots. Keep NO_<season> as a hard bar. For resident carnivores it would invent migrations, and it breaks your 12 Oct season symmetry, so it needs your ruling.
3. **A small seasonal-habits table** in the rules file for clear cases: waterbird migrants, hibernators the raws missed, insects (`VERMIN.defaultSeasons` is the precedent).
4. **Size slot wants to their candidates.** When a slot has fewer fitting species than seats a year, lower the want (D5's right-sizing) or pass seats to a sister slot (grazer → ground prey). The tapir and elephant would then hold 2 seasons, not 4.
5. **Specialist weighting** for flying: weight ∝ (land biomes in its raws)^−a, or narrow the eagle-type generalists with BIOME_LIMIT.
6. **Very short lists** (glacier 2, tundra 9) can't vary by weighting. Accept empty seats, or (inference) admit species from DF's neighbouring draw tiles.

**Advise against:** blaming the raw season tags, or trimming all-year species without changing seats. Either gives unfilled slots or odd substitutes.

### 6. Limits
Vanilla raws only. Python desk copy, not the Lua. One biome per fort. Savagery 80, UNTAMED_WILDS. The pond list was wrong (above), and the other water rows may be too. Casts are not arrivals: DF's per-entry pick, the ladder, caps and borrowed seasons decide what you see.

### 7. What only the rig can settle
Whether a seasonal pattern in the casts reaches **arrivals**, and whether fewer winter species means fewer winter waves.
- **Setup:** current pacing world, one fort re-embarked per arm (startdwarf 50, breached; same site and year → same seed). Arms: flat slot tables vs winter-thin, optionally a season-preference arm for flying and waterbird slots only.
- **Size:** n=5 one-year runs per arm.
- **Score** after the manifest check:
  - distinct species arrived per season;
  - waves and groups per season;
  - arrivals from DF waves vs the tool's own draw (`V7.DRAW.pick`, 15908).
- Mark PENDING if the data is thin.

The cast-level effect needs no rig.

**Rig test that would settle it:** Current pacing world, one fort re-embarked per arm (startdwarf 50, breached; same site and year → same cast seed). Arms: flat slot tables vs winter-thin, optionally a season-preference arm for flying and waterbird slots only; n=5 one-year runs per arm. After the manifest check: distinct species arrived per season, waves and groups per season, arrivals from DF waves vs V7.DRAW. PENDING if thin. The cast-level effect is computed on the desk first; rerun the desk pond and water rows with the engine's freshRaw rule.

<details><summary>Review and verification trail</summary>

- review: Creature count corrected from 24 to 23. A grep of every vanilla raw file (grep -a, since some files read as binary) finds 23 creatures with a season tag: 23 NO_WINTER, 2 NO_AUTUMN (hoary marmot, moghopper), 1 NO_SPRING (moghopper), 0 NO_SUMMER. The answer's own species list also adds up to 23.
- review: Savage multiplier corrected from 'x4-6' to x2.9-8.2 (richness.json: mountain 11->32, taiga 18->58, temperate freshwater marsh 8->66). The answer also left out that giants are weighted x0.2 and animal people x0.1 in the draw (seasonal-wildlife.lua:22876-22885), so the extra savage candidates take fewer seats than their numbers suggest.
- review: Flying row corrected. In temperate grassland the desk build gives 4 birds one season and 4 birds two seasons per fort (casts.json hist 1:160, 2:160 over 40 forts), not 'every bird in 2 seasons'.
- review: SAVR_d1 numbers corrected. '38 one-season + 3 two-season' counts vermin. Animals alone: 32 ground seats, 32 different species, each in one season. The 3 repeats are vermin (bumblebee, thrips, honey bee).
- review: Mountain corrected: the hoary marmot is missing in autumn AND winter (11/11/10/10), not only autumn.
- review: Cavern claim corrected. SAVR_d1 and LAKE3 cavern casts are identical. COAST differs in 2 seats (cave swallow man and blind cave ogre swap places), because the shared x0.01 repeat count and the build order depend on which layers exist (ocean vs fresh; NR.year :23151-23165). Cavern candidate lists do not follow the surface biome by design: the cavern assignment (:5817-5830) holds the 56 cavern species as the user picked them. Same site id and year give the same seed (NR.seedOf :23150).
- review: Overreach removed: 'fewer open entries in winter means fewer waves'. TR2 (df-wave-pick-per-entry) measured how waves are SHARED between entries, not how many waves come. With the same waves and fewer cast species, each winter species would arrive more often, so a thinner winter cast alone may not make winter feel lean. That is now the rig question.
- review: Added: casts are built once per fort and kept for its whole life (user 9 Oct 'no year-to-year variety, not even as an option'; :5068-5071, :9598). The random season a species lands in is permanent for that fort. The prototype's '40 simulated years' are really 40 different forts (site seeds 1-40 at year 250).
- review: Added: the random build order is the user's own 12 Oct ruling (so no season gets first pick; full-pool-design-oct9; desk design.py:89). A season-preference weight deliberately breaks that symmetry, so it needs the user's ruling.
- review: Added a concrete slot-shortage case from the desk build. Tropical moist forest has 43 ground candidates, but tapir and elephant are the only species that fit the 2-seat grazer slot, so both are cast in all 4 seasons in 40/40 forts. All-year species come from slot fit, not list size.
- review: Added the v8.1 tool draw. V7.DRAW.pick (:15908-15943) picks the least-seen in-season cast member first. When the tool draws (not DF), the cast's seasonal makeup carries into arrivals more directly. The rig test should split arrivals by source.
- review: 'Dormant' corrected. The climate-lean deal (assignFromMatrix :3410, via ROSTER.deal) still runs at preset/reset (:4862, :4915), but the cast build then overwrites every species' seasons (:10868-10876). VERMIN.defaultSeasons (:4150: land insects spring-autumn, summer-autumn on a cold embark) is live only as a manual verb (:24432, gui :1765). It is an existing precedent for a seasonal-habits rule.
- review: Added a naturalism reframe. In real ecology many residents are present all year, and seasonal turnover comes mostly from migrant birds, hibernators and insects. The climate lean is a migration proxy, so it suits the flying and waterbird slots and is wrong for resident carnivores. The design choice is maximum turnover (current) vs a resident core plus visitors.
- review: Added a per-slot repeat limit as a lever: when a slot has fewer fitting species than seats across the year, leave the extra seats empty or pass them to a sister slot instead of recasting the same species. This targets 'seasonally ubiquitous' directly.
- review: View proposal adjusted: a Seasons tab in the Food Web Explorer, which already holds the desk builder and biome picker, labelled as computed from the raws, plus cast nrprobe for a real fort. This follows the no-mocks rule: offered, not shown.
- review: Rig test refined: the same fort re-embarked per arm (same site and year means the same seed, so only the slot table differs), arrivals split DF wave vs tool draw, and waves per season measured to settle the share-vs-count question.
- verifier: Ponds: the prototype's 5 candidates (2 in winter, about 1 species all year) undercounts. The engine's pond list admits any non-vermin species with lake, river or pool in its raws (seasonal-wildlife.lua:10091). The real pond fort probed (nrprobe V8E_A1/A2) has 15 candidates (12 in winter), and no pond species is cast all year. The pond row is removed from the conclusions; other water rows of the prototype may share this gap.
- verifier: Minor: a pond cast has 3 non-sentient seats a season (12 a year), not 11.

Code refs: sw-wt/plugin/scripts/seasonal-wildlife.lua:2134-2139 (classify: noSeason from raw NO_<season>); sw-wt/plugin/scripts/seasonal-wildlife.lua:18020-18025 (seasons_own: CACHE.noSeasonRaw read before flags cleared); sw-wt/plugin/scripts/seasonal-wildlife.lua:2655-2692 (buildPool; lean/affinity computed); sw-wt/plugin/scripts/seasonal-wildlife.lua:602 (SEASON_SETS), :2635 (climateRange); sw-wt/plugin/scripts/seasonal-wildlife.lua:3410-3420 (assignFromMatrix -> ROSTER.deal), :4862, :4915 (preset/reset callers); sw-wt/plugin/scripts/seasonal-wildlife.lua:3033-3048 (ROSTER.fitSeason, ROSTER.deal); sw-wt/plugin/scripts/seasonal-wildlife.lua:4150-4153 (VERMIN.defaultSeasons), :24432 and gui/seasonal-wildlife.lua:1765 (manual callers); sw-wt/plugin/scripts/seasonal-wildlife.lua:5066-5071 (V7.ST.turn: casts kept, no yearly regrow, user 9 Oct; exhaustRoll); sw-wt/plugin/scripts/seasonal-wildlife.lua:9598 (built once, kept); sw-wt/plugin/scripts/seasonal-wildlife.lua:797-805 (RO.SLOTS slot tables, per layer only); sw-wt/plugin/scripts/seasonal-wildlife.lua:5817-5830 (cavern assignment); sw-wt/plugin/scripts/seasonal-wildlife.lua:9726-9738 (FP.biomesOf, BIOME_LIMIT); sw-wt/plugin/scripts/seasonal-wildlife.lua:10114-10150 (FP.mark); sw-wt/plugin/scripts/seasonal-wildlife.lua:10296-10327 (FP.candidates: season test :10306); sw-wt/plugin/scripts/seasonal-wildlife.lua:10339 (CAST_DEF reuse 0.01); sw-wt/plugin/scripts/seasonal-wildlife.lua:10836-10849 (live build via NR.year); sw-wt/plugin/scripts/seasonal-wildlife.lua:10868-10876 (cast build writes each species' seasons); sw-wt/plugin/scripts/seasonal-wildlife.lua:15908-15943 (V7.DRAW.pick: least-seen in-season cast member); sw-wt/plugin/scripts/seasonal-wildlife.lua:22862-22885 (NR.cast, weight(): no season factor); sw-wt/plugin/scripts/seasonal-wildlife.lua:23036-23042 (unfilled reasons); sw-wt/plugin/scripts/seasonal-wildlife.lua:23150-23165 (NR.seedOf, NR.year shuffled order, shared used counter); sw-wt/plugin/scripts/seasonal-wildlife.lua:23355-23357 (NR.toRecord pool count); sw-wt/plugin/scripts/seasonal-wildlife.lua:11352 (casts view sends pool); sw-wt/plugin/scripts/seasonal-wildlife-web.html:2192 (Unfilled shown, pool not); sw-wt/plugin/scripts/seasonal-wildlife.lua:24667, :24713, :24963-24975 (cast pool / nrprobe / show verbs); DwarfCron/scripts/castsim/foodweb_app.js:184-195 (explorer season buttons); DwarfCron/scripts/castsim/design.py:58,89 (REUSE 0.01; random order rationale); DwarfCron/.claude/scratch/sw-questions/d7/richness.json, casts.json (prototype outputs); DwarfCron/.claude/scratch/pacing/ladder/SAVR_d1.json, COAST.json, LAKE3.json (real casts; site 266 year 100); DF vanilla raws: 23 creatures with NO_<season> (grep -a across data/vanilla); memory: full-pool-design-oct9.md (12 Oct random order, reuse), season-cast-rulings-oct7.md, df-wave-pick-per-entry.md, cast-coverage-drivers.md, no-mocks-for-user.md

</details>

# E. Resting, holding, stand-ins and grace

*what resting/held mean, how stand-ins are chosen, the 7-day grace, and their interactions*

### What these four questions are really after
All four ask about one thing: the machinery that handles a species when it is **off stage** (resting, held), **gone** (exhausted, then a stand-in) or **leaving** (sent off, then the 7-day grace). The user wants to know whether each piece is natural and under the tool's control, or a patch that fires blindly.

Their aims:
- **diversity:** a slot should not sit empty or be filled by a stand-in that never shows up;
- **ecology:** the same guild and a real food-web link, with the species' own stock and nothing invented;
- **naturalistic seasonal balance:** an old cast drifts out while the new one arrives, and a die-off reads as recolonisation, not a respawn;
- **fewer hacks, with the tool in control:** hand-overs at the season boundary at the slot's rung, rather than removals and swaps whenever a check happens to fire.

### What the code shows across the group
- **Resting and held are sound.** Stock moves to the reserve, the entry is set to 0 and flagged, and cavern FREQUENCY goes to 0. The run-out check reads stock (live plus held) and only after the season's apply, so holding does not break it.
- **The weak spots are all after a promotion.** They are bookkeeping, not design:
  1. the one-entry pick is cached before the promotion (`CACHE.castSig` is never set), so every copy of the stand-in stays open and a cavern stand-in is not capped at 30;
  2. the ground, flying and cavern draws read only the cast lists, so the tool never places a stand-in there, and it arrives only if DF sends a wave;
  3. a flying stand-in is filed as land;
  4. a cavern stand-in opens at every depth;
  5. a save and reload drops the `resting` mark, so the stand-in stays in that season every year.
- **Two answers needed correcting from the code:** apex stand-ins from another season are scheduled as apex, and animals are removed (not only sent off) at the grace deadline.
- **The 7-day grace is a removal deadline, not a delay.** In the pacing forts, the animals that lingered were river and ocean fish, cavern animals, birds, a deer and a boar. None was in a closed pond, so the X3 explanation (no path to the edge) does not cover them, and the real cause is unknown. Caged and chained animals are not excluded from removal.

### Combined recommendation
1. **Keep resting and held as they are.** Fix the wording on the page: \"resting this season\" / \"resting all year\" / \"held\", and \"if that entry is shut this season\".
2. **Fix the stand-in bookkeeping before any redesign:**
   - clear `CACHE.srcPick` at a promotion;
   - keep `resting` when the config is loaded;
   - add this season's stand-ins to `V7.DRAW.members` and `V7.GRP.flyers` in the slot they cover;
   - open a cavern stand-in only at the depth with the gap;
   - give the stand-in the slot's ladder rung.
3. **The user's E1 idea is workable, in this form:** record the die-off after 1 day as now; optionally leave the gap for the rest of the season; hand the slot over **inside the next cast season's apply** if the species is still at 0 with none on the map. Most of this already happens today, one day late. With item 2 fixed, the hand-over is controlled by the tool and natural-looking.
4. **Do not shorten the grace to 3 days yet.** First skip caged and chained animals (a bug fix). Then run the leave 7 / 3 / 0 probe to learn why animals linger. If tuning is still wanted, 4-5 days or counting sent-off groups as \"leaving\" in the caps serves the aims better than 3.
5. **Rig tests, none run.** All on test copies, never the user's fort, and none while the current rig run is in progress:
   - DF regrowth from 0;
   - two arms for the gap cost;
   - the stand-in bookkeeping and the reload leak;
   - the grace arms with the cage and double-refund side checks;
   - whether the extinct flag alone holds a refunded entry.

<details><summary>Cross-answer issues the verifier resolved</summary>

- Do stand-ins actually arrive? E1's thought experiment says today's stand-in 'holds days 21-84'. E3 shows that on the ground, flying and cavern layers the v8.1 tool draws take their candidates only from the cast lists (V7.DRAW.members :15889, V7.GRP.flyers :15854), and a promotion changes allow/assign, not the casts. So a stand-in there comes only if DF sends a wave. Resolved from the code in E3's favour: E1 now says the stand-in holds the slot on paper, and the variety it adds is at most one species and often less. The user's proposal therefore costs less than E1 first said.
- Apex stand-ins: E1 said an apex stand-in is 'probably just an ordinary entry'. castLadder (:11071-11084) puts every apex-rung member of every season into apex_keys, and placeTick takes any of those keys that is wanted now (:11716). So a stand-in that is the apex in its own season is scheduled as apex while it stands in. Only a stand-in that was resting all year is not. E1 corrected.
- 'Nothing is deleted' (E4) against the 7-day removal (E2): E4 said 'the only thing that ever sends groups off is cast turnover at the season change'. In the code, castTurnover is a standing rule that runs on every groups pass (:16770-16773), not only at the change. leaveCheck also takes stuck animals off the map after leave_grace_days. And with the pauses switched off, the absolute land gate and the cavern trim also send groups off (:17418, :15624). Resolved: no stock is ever deleted (vanished animals are refunded), but animals are removed. E4's wording is corrected.
- Resting-flag leak (E1 and E3 agree, verified): loadConfigRaw (:1261-1264) rebuilds promoted entries with season and for_key only. exhaustRoll (:3988) sends a seasonless stand-in back to rest only if p.resting is set, then wipes x.promoted. Added consequence: after the leak, the stand-in is an in-season non-cast species every year, so exhaustCheck can judge it and even find a stand-in for it.
- Caching of the one-entry pick (E3, verified): the V7.SRC.chosen signature is rows, season, casts_year and CACHE.castSig. castSig is never assigned in scripts/, and CACHE.managedPops is not rebuilt on a config change. So the pick made before a promotion stands until the season changes or the map reloads, and every copy of the stand-in stays open.
- E2's line references and E4's both put leave_grace_days and absolute=true on :1026. Both are correct: they share that line.
- Smaller fixes: E2's straggler list gives cave floater x2 where the data has x3, and the ledger shows two removals at 7.0 days (BIRD_RAVEN on PC_COAST, GIANT_DRAGONFLY on P2_SAVR) that the probe table misses, so probe-based counts are approximate. E1's 'PANDA had no arrival or death earlier' is limited by the ledger, which keeps only its last 300 lines (P2_COAST's starts on Summer 71). E4's gate hold level is at least 2, not 1. RESERVE.giveBack is at :3846. Water spill never borrows under casts (:8899), so E4's 'spill works the same way' applies only with casts off. E4's 'DF sends no water waves' is narrowed to river and lake (feature) entries (E26).

</details>

## E1

> What would happen if... instead of "stock 0 for a day, none on the map -> a stand-in from the same slot" the tool did "stock 0 for a season -> a stand-in from the same slot for the next season in which that species was part of the season cast"?

**Short answer.** Half of it already happens. A dead species gets no stock back, so in its next cast season it reads 0 again, is declared exhausted a day in, and a stand-in is chosen then. Your change removes the stand-in for the rest of the current season and moves the hand-over to the season boundary. The cost is at most one species of variety for the rest of that season, and in practice less, because the tool's own draws never place stand-ins on ground, flying or caverns. It is workable as 'still 0 with none on the map at the season apply'. Do it in the apply, and give the stand-in the slot's FREQUENCY rung.

*Status: corrected · confidence medium · review verdict: minor fixes*

### E1: "Stock 0 for a season, then a stand-in in the species' next cast season" instead of "stock 0 for a day, then a stand-in now"

### Short answer
**About half of your proposal is already what the tool does.** Once every animal of a species has died, nothing gives it stock back. At the season change, `applyLive` refills an entry only from that entry's own held stock (`res[id] or 0`, seasonal-wildlife.lua:3893; your 12 Oct rule "entries deplete naturally"). So in the species' next cast season it reads 0 again. A day later it is declared exhausted again, and a stand-in from the same slot is chosen against *that* season's cast.

The rig shows this. SEA OTTER on the coast fort: one ocean draw took its whole stock ("stock 4 -> 0", Summer 61). It was exhausted on Summer 68, and again on Autumn 2 (B1/PC_COAST ledger lines 33, 82, 171).

**So your change does two things:**
1. **No stand-in for the rest of the current season.** The slot stays empty until the season changes.
2. **The hand-over happens at the season boundary**, which removes the 1-day gap at the start of later cast seasons.

**The cost is smaller than it looks.** At most it is one species of variety for the rest of that season. Often it is less, because today's stand-in frequently never shows up (see "What the stand-in actually gets" below). Waves and groups barely change, because the land cap holds them.

**Exception:** a species whose stock you set by hand is refilled at every season apply (:3888-3889, :3916), so it is never exhausted for long.

---

### (a) What the code does today (sw-wt @ 6dffef5, `scripts/seasonal-wildlife.lua`)

**Trigger** (`ROSTER.exhaustCheck`, :3996-4101; on by default, :991). It runs in the groups pass every 300 ticks. An in-season cast member counts as exhausted when both of these have held for one day (`EXHAUST_SETTLE = TICKS_PER_DAY`, :3962):
- its stock is 0, live plus the held stock on its extra copies (:4010);
- none of its race is on the map (the pass's census, :4022).

**Why one day** (comment :4014-4017; your ruling of 13 Oct):
- DF takes a wave's stock when the wave starts, so a one-wave entry reads 0 before its animals walk in.
- DF gives stock back for an animal that walks off, so "exhausted" means its animals died.

**Other details:**
- The one-day clock is not saved (`CACHE.exhaustZero`, :3970-3974).
- The check waits for the season's apply (`CACHE.appliedStamp`, :4003). Before that fix it swapped 17 of 22 Autumn cast members at the boundary.

**Who can stand in** (:4045-4068; `castReplaceOk` :11096-11139; `FP.standInStock` :11144-11164). The candidate must:
- not be in season now, and not be vermin;
- hold the same cast slot on that layer;
- be in the same guild (no fallback to another guild);
- be within 4x the adult size (`EXHAUST_MASS_RATIO = 4`, :11095);
- on ground and flying layers, share a fort biome; on ocean and fresh-water layers, fit a water body (`V7.WB.fitting`);
- eat, or be eaten by, a member of this season's cast;
- have stock DF can send on that layer (ground: a site tile).

The nearest in size wins. If no candidate passes, the slot stays empty and the ledger names the closest candidate and the check it failed. That is your 13 Oct ruling.

**The promotion** (:4069-4088):
- The stand-in gets this season added to its seasons. If it was resting all year, it is switched on and marked `resting`.
- Its entries are refilled from their own reserve.
- The exhausted species is marked `done`, and `exhaustHolds` blocks every refill of it for the rest of the season.

**At the season change** (`exhaustRoll` :3980-3995, called before the apply at :5067):
- The borrowed season is taken back.
- A resting stand-in rests again.
- `done` and the promotions are cleared.

**Casts are fixed.** They are built only at enable, `cast rebuild` or `roster build` (comment :5070-5072). So "the next season it is cast" is well defined.

### What the stand-in actually gets (this changes the comparison)
- **It is often not placed at all.** On the ground, flying and cavern layers, the v8.1 tool draws pick only from the cast lists (`V7.DRAW.members` :15889; `V7.GRP.flyers` :15854). A promotion changes the roster, not the casts. So a stand-in arrives only when DF itself sends a wave, and on the ground DF waves can be rare (0 ground waves in 22 days on SW-LAKE-THAW).
- **Its odds are not the slot's.** `cfg.odds` holds one value per species, set by the casts' ladder (:11068-11076):
  - a stand-in cast in another season keeps that season's rung;
  - a stand-in that was resting all year has no odds and runs at its raw FREQUENCY (`ODDS.weight` :4752).
- **All of its copies are open.** The one-entry pick was cached before the promotion, so every copy of the stand-in stays open (see E3). On the ground that makes it more likely to be picked whenever DF does send a wave.
- **Apex** (corrected). A stand-in that is the apex in its own season is already in the apex scheduler's keys (`castLadder` :11071-11084), and the scheduler takes any key wanted now (:11716). So it is scheduled as apex. A stand-in that was resting all year is not.

### (b) What DF itself does (evidence, not code)
- **Walk-offs are refunded and deaths are not** (Wilderpop E9b/E15). So only deaths exhaust a species.
- **DF grows entries that still have stock:** 100 -> 112 over one season on region1 (comment :3929-3930).
- **Whether DF ever regrows an entry from 0 has not been measured.** ECO N1: a kangaroo entry of 3 went to 0 with one wave, and no kangaroo came for the rest of that season. Treat "0 stays 0 across seasons" as likely, not proven.

### (c) Thought experiment: Fort 1, savage marsh (`SAVR_d1.json`)

How many seasons each cast species is cast in (I re-counted these from the dumps):

| Fort | Cast species | 1 season | 2 seasons | 3 seasons | 4 seasons |
|---|---|---|---|---|---|
| Fort 1 | 103 | 77 | 17 | 8 | 1 |
| COAST | 90 | 49 | 28 | 10 | 3 |
| LAKE3 | 112 | 86 | 13 | 12 | 1 |

For a one-season species, "its next cast season" is the same season next year, both today and under your version.

**Scenario.** The giant beetle is ground prey, cast in Summer only. Its one group arrives on Summer day 10, and black bears kill it by day 20.

**Today:**
- Day 21: a stand-in (say giant weasel or wild boar, if it passes the checks) holds the slot on paper for days 21-84.
- It shows up only if DF sends it a wave.
- Next Summer, day 2: the beetle reads 0 again, and a stand-in is chosen again.

**Your version:**
- Days 21-84: the slot is empty, and the giant grasshopper is the only ground prey.
- Next Summer, day 1: the hand-over happens at the apply.

**What the rig shows.** There were six exhaustions in B1/B2:
- two stand-ins: TIGER for BEAR_GRIZZLY on Summer 76, OSPREY_MAN for MEGANEURA_MAN on Summer 78;
- four with no stand-in: SEA OTTER three times (failed guild), PANDA once (failed size).

PANDA was exhausted on Autumn 2. The ledger's 300 visible lines (from Summer 71) show no arrival of it, so it probably began Autumn with an empty entry. That would be the "next cast season" check firing on its own, but earlier events are not visible. These runs start late in Summer, so they say little about how much of a season is usually lost.

### What changes, and what could break
1. **Variety: at most one species fewer in that slot for the rest of the season.** Waves and groups mostly do not change:
   - an entry at 0 cannot be picked, so DF's per-entry pick goes to the other members;
   - the land cap holds the group count ("adaptive: target 3.3-3.8 of 4").

   The loss weighs more in small casts (flying about 4 members, each cavern depth 5-6). I have not measured that.
2. **"Stock 0 for a season" has two readings, and only one works.**
   - **(i) Zero for a whole season in a row.** This needs a saved clock. It delays one-season species by about two years. It must count held stock, because out of season the tool holds every entry at 0.
   - **(ii) Still zero, with none on the map, at the species' next cast-season apply.** A single reading with no clock to save. This is the workable form.
3. **A stand-in chosen when the species dies can be stale by the time it is used.** Its own stock may be spent, water bodies change, and `cast rebuild` replaces the casts. So choose the stand-in at the target season's apply.
4. **Other parts are unaffected:**
   - pairing prey with predators calls only predators with stock (:5590);
   - water spill is off under casts (:8899);
   - the 7-day send-off grace works the same either way.
5. **A bug that bites in both designs, and more often under yours.**
   - `loadConfigRaw` (:1261-1264) reloads promotions without the `resting` flag.
   - If you save and reload while a resting species stands in, `exhaustRoll` (:3988) does not rest it again, and the promotion record is wiped.
   - From then on it is switched on in that season every year until `cast rebuild`. It is a non-cast species that DF can send, and the exhaustion check can judge it.
   - This is read from the code, not reproduced on the rig.
6. **Edge cases:**
   - **Savage or evil maps:** more die-offs, so more empty slots under your version.
   - **Caverns:** the pass refills a dry chosen cave entry from its reserve before the check runs (:17292, then :17317). Cavern exhaustion is rare, so little changes.
   - **Ponds only:** a fresh-water stand-in must fit a pond, so "no stand-in" is common in both designs.

### Does it serve your aims?
- **Natural feel and fewer hacks: yes.** A local die-off that stays a gap until the season turns, then gets a successor, reads as recolonisation. A same-guild species turning up a day after the last group died reads as a respawn.
- **Variety: a small loss, partly not real today,** since today's stand-in often never arrives.
- **The tool controlling outcomes: yes, if the hand-over happens in the season apply** and the stand-in is given the slot's rung.

### Recommendation
Keep the detection; change the timing.
1. Keep the 1-day test to *record* the die-off.
2. Add one setting for the current season: "fill now" (today) or "leave the gap" (your proposal).
3. In each later cast season, hand the slot over **inside the season apply** if the species still reads 0 (live plus held) with none on the map.
4. Give the stand-in the slot's FREQUENCY rung. Add it to this season's draw list, so the tool can place it. If the slot is the apex, add it to the apex keys.
5. Optionally, keep the same successor every year, as a visible cast edit.
6. Fix the dropped `resting` flag whatever you decide.

If what you want is the same species coming back, that means giving it new stock, which your 12 Oct rule forbids. That is a separate decision.

### Rig tests (not run)
1. **Does DF regrow an entry from 0?** Kill one cast member's group early in its season. Read its entry once at each season boundary for a year, using one-shot reads only.
2. **What does the gap cost?** Same save, two arms (today / leave the gap), n=5 each, with a manifest receipt first. Kill the same member on Summer day 10. Score the rest of Summer:
   - distinct cast species seen;
   - waves and groups per layer;
   - whether the stand-in arrives at all, and its share of waves.
3. **The resting-flag leak:** promote a resting stand-in, save, reload, cross the season change, then read its allow and assign.

**Rig test that would settle it:** (1) Kill one cast member's group early in its season and read its entry once at each season boundary for a year (one-shot reads): does DF ever regrow it from 0? (2) Same save, two arms (today / leave the gap), n=5 short runs, manifest receipt first. Kill the same member on Summer day 10 and score distinct cast species, waves and groups per layer, and whether the stand-in arrives at all. (3) Promote a resting stand-in, save, reload, cross the season change, then read its allow and assign.

<details><summary>Review and verification trail</summary>

- review: Confirmed the core claim in code. applyLive (seasonal-wildlife.lua:3890-3896) refills a spent entry only from its own held stock (res[id] or 0). exhaustRoll (3980-3995) clears `done` at the season change. So in the species' next cast season it reads 0 again, and exhaustCheck (3996-4101) declares it exhausted again after ROSTER.EXHAUST_SETTLE = 1200 ticks (3962). Exhaustion is on by default (cfg default, line 991).
- review: Fixed a citation. B1/PC_COAST/ledger.txt:33 is not an exhaustion line. It is the SEA OTTER arrival, 'stock 4 -> 0': the species' whole stock went in one draw. I now use it to show that exhaustion mostly hits tiny entries. The real exhaustion lines are 82 (Summer 68) and 171 (Autumn 2).
- review: Added the PANDA case. B2/P2_COAST/ledger.txt:130 has PANDA exhausted on Autumn day 2, with no PANDA arrival or death earlier in that run. That is a cast member that began its season already empty. Under the 'zero for a whole season' reading, its slot would sit empty for a full season before the rule even counted it.
- review: Added an exception to 'nothing refills a spent entry'. A species with stock the player set by hand (cfg.stock) is refilled at every season apply by RESERVE.set (3888-3889, 3916). Only species with no hand-set stock stay spent.
- review: Added a gap the first answer missed. A stand-in keeps its own FREQUENCY, not the rung of the member it replaces. cfg.odds holds one value per species from castLadder (11068-11076), and a resting species' odds are cleared, so it falls back to its raw FREQUENCY (ODDS.weight 4752; CAVERN.apply 4645-4660). DF's surface pick is FREQUENCY x tile weight (df-wave-pick-per-entry), so a stand-in can draw much harder or softer than the slot was tuned for. A hand-over at the boundary is the natural point to give it the slot's rung.
- review: Added that an apex stand-in is probably not placed by the apex scheduler. ROSTER.placeTick (11762-11785) places only the keys in cfg.roster.apex_keys, and those are written once by castLadder (11072-11084). This is an inference from the code; I did not run it. I replaced the first answer's 'today the slot gets an apex stand-in'.
- review: Confirmed the resting-flag leak and stated its exact effect. loadConfigRaw (1261-1266) rebuilds `promoted` without `resting`. After a save and reload in the middle of a stand-in, exhaustRoll's second branch (3989) needs p.resting and does not fire. The species keeps allow=true and assign={that season}, and exhaustRoll then wipes `promoted`. It becomes an extra cast member in that season every year until `cast rebuild`. Nothing else rebuilds assign from the casts (castYear runs only at 20926, 21215, 24916, 25024).
- review: Added the user's own 13 Oct ruling (commit 52cdfcb): 'Design the whole set of checks to fail if no close match is found, leaving the slot empty'. An empty slot is already an accepted outcome, and 4 of the 6 rig exhaustions ended that way.
- review: Softened unsupported numbers. The rig shows the land cap as 4 groups ('adaptive: target 3.3-3.8 of 4' in B1/PC_SAVR/ledger.txt). The first answer's 'flying capped at 2 concurrent groups' was an inference about the flying cap, so it is removed.
- review: Noted that the mechanics page's line 1154 ('It returns at the season change') can be misread. The exhausted species does not come back. Its slot comes back to it with 0 stock, and it is exhausted again a day later.
- review: Cavern side note. exhaustCheck counts held stock only for duplicate copies (isDup 3381-3391), not the chosen cave entry's own reserve from the 30-animal level (3820-3836). But holdOutOfSeason, which calls topUp, runs before exhaustCheck in every 300-tick pass (17292 then 17317), so the entry refills first. 'Rare in caverns' holds; the code comment at 3822 ('the exhaustion check counts it') is loosely worded.
- review: Verified the cast counts by script on the three dumps. Fort 1 has 103 cast species (77/17/8/1 by seasons cast), COAST 90 (49/28/10/3), LAKE3 112 (86/13/12/1). Fort 1's Summer ground cast and slots are as stated.
- review: Verified that v8 coupling (V7.GRP.coupleStart 5569-5600, reached via startCoupling 5647 under casts) opens only predators with pop.quantity > 0, and that coupling is on by default (1009). Spill is off under casts (8901).
- verifier: Apex: a stand-in that is the apex in its own season IS in cfg.roster.apex_keys (castLadder :11071-11084 adds every apex-rung member of every season) and placeTick takes any wanted key (:11716), so it is scheduled as apex. Only a stand-in that was resting all year is not.
- verifier: Today's stand-in may never arrive: on the ground, flying and cavern layers the tool's own draws read the cast lists only (V7.DRAW.members :15889, V7.GRP.flyers :15854). So the 'extra 63 days of one species' is an upper bound, and the cost of the proposal is smaller than first stated.
- verifier: PANDA: the P2_COAST ledger keeps only its last 300 lines (it starts on Summer 71), so 'no arrival or death earlier in that run' is only true of what the ledger still shows.
- verifier: Added: after the resting-flag leak, the leaked species is an in-season non-cast member, so exhaustCheck can judge it too.

Code refs: /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:991 (exhaust on by default); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:1261-1266 (loadConfigRaw drops promoted.resting); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:3381-3391 (V7.SRC.isDup); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:3766-3845 (V7.SRC.topUp, cave_open_stock level, exhaustHolds guards); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:3875-3922 (applyLive: cfg.stock refill, spent entry res[id] or 0, appliedStamp); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:3929-3957 (holdOutOfSeason; DF breeds in-season entries; ECO N1 comment); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:3962 (EXHAUST_SETTLE = TICKS_PER_DAY); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:3970-3995 (exhaustZero, exhaustHolds, exhaustRoll incl. resting branch 3989); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:3996-4101 (ROSTER.exhaustCheck); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:4645-4660 (CAVERN.apply odds per key); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:4752 (ODDS.weight falls back to the raw FREQUENCY); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:5066-5067 (V7.ST.turn calls exhaustRoll before applyLive); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:5569-5600, 5646-5647 (v8 coupling: only predators with stock); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:8901 (spill off under casts); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:11068-11084 (castLadder: cfg.odds per key, apex_keys); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:11096-11164 (castReplaceOk, FP.standInStock); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:11762-11785 (ROSTER.placeTick: apex scheduler uses apex_keys only); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:16774-16850 (castTurnover, refundUnit, leaveCheck); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:17292, 17317 (hold+topUp before exhaustCheck in each groups pass); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:20926, 21215, 24916, 25024 (castYear call sites); git 52cdfcb (13 Oct: checks fail -> slot left empty), 6e1ffb2 (wait for the apply), 661cbaa (ECO N1); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/B1/PC_COAST/ledger.txt:33 (SEA OTTER stock 4 -> 0), :82, :171 (exhaustions); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/B2/P2_COAST/ledger.txt:42, :130 (PANDA, no prior arrival), :131; B2/P2_SAVR/ledger.txt:52; /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/B1/PC_SAVR/ledger.txt (land 'adaptive: target 3.3-3.8 of 4'); /Users/nathanielcannon/Claude/Projects/DwarfCron/.claude/scratch/pacing/ladder/SAVR_d1.json, COAST.json, LAKE3.json (seasons-per-cast-species counts, Summer ground cast); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/mechanics-diagram.html:190, 1154, 1295

</details>

## E2

> What would happen if... instead of "7-day grace" we changed it to 3-day grace? Any unintentional consequences?

**Short answer.** The send-off is immediate at the season change. The 7 days is only a deadline after which animals still on the map are removed (no corpse) and refunded to their entry. At 3 days, about 1.5 more groups per season change per fort would be removed that were already walking off on their own, mostly in caverns and at sea. In return, the few that never leave would free their cap slots 4 days sooner, but a paused layer only reopens at 2 under its cap, so that gain is small. One existing problem gets worse: caged and chained animals are not excluded (DFHack's exterminate skips them). Fix that first, and find out why animals linger before you tune the number.

*Status: corrected · confidence medium · review verdict: minor fixes*

### What changing the 7-day grace to 3 days would do

**Short version:**
- **Cost:** about 1.5 more groups per season change per fort would be removed that were already walking off on their own. Most are in caverns or at sea, so few would vanish where you would see them.
- **Gain:** the few animals that never leave would free their slots 4 days sooner. Because of the pause margin, that gain is small.
- **A side effect gets worse:** caged and chained wild animals are not excluded from the removal.
- **Unknown:** why the animals linger in the first place.

### What the "7-day grace" actually is (code, `scripts/seasonal-wildlife.lua`)

**1. The send-off is immediate.**
- `V7.GRP.castTurnover` (:16774) is a standing rule run on every groups pass. On the first pass after a season change, it calls `dismissGroup` (:13573-13582) for every group whose species is not cast this season.
- `dismissGroup` sets each member's leave countdown to 0, clears the leader, and stamps `dismissed_at`. DF then walks the animals to the map edge.

**2. The grace is a deadline for animals still here.**
- `V7.GRP.leaveCheck` (:16836-16862) runs on every groups pass.
- Any member still on the map `leave_grace_days` after the send-off gets `vanish_countdown = 1`: it disappears with no corpse and no death.
- `refundUnit` (:16820-16835) gives +1 back to its entry, as DF does for an animal that walks off.
- **Who is removed:** only wild natural units. Citizens, tame animals and undead are never removed (:16848).
- **Caged or chained animals are not excluded.** `grep` finds no `caged` or `chained` check anywhere in the file.
- Each group is removed only once (`grp.vanished`).

**3. The setting.**
- Default 7 (:1026), range 0-60, 0 = never remove (:924).
- Command: `groups cavern leave N` (:24082). Panel row: "Take off a stuck send-off after".
- Despite "cavern" in the command, it applies to every layer.

**4. Why 7** (commit d2261cf, 9 Oct; comment :16809-16818).
- In the X3 lake fort, animals that could walk off did so in a median of 1.2 days, and all within 6.1 days.
- The ones that stayed were in water with no way to the edge: giant cave toads in closed cavern pools, and a sea lamprey in an enclosed lake.
- 7 was set just past the slowest walker, based on that one fort.

**5. A separate setting.** `cavern_draw_grace_days=4` is how long a cavern must go without a DF wave before the tool draws there itself. Changing the leave grace does not touch it.

### Why the grace matters: sent-off groups still count against the caps
A sent-off group stays in the group list until its last member is gone (`reconcileGroups`, :5386-5401). Until then it counts:
- `ENGINE.count` (:7515) counts every group, sent off or not, for land, flying and water;
- `cavernPass` counts it per depth (:15581-15589);
- on the surface, `presentRaces` (:16211-16216) counts it for one-group-per-species.

So a leftover animal holds one of the new cast's slots until the deadline.

The trims treat sent-off groups as "on their way out" (:16436, :16476). But the trims are off while the pauses are on (:15624, :17418), and the pauses are on by default.

### What the pacing forts show (rig data, re-derived)
This covers groups of species no longer cast, across 8 season changes in B1 PC_SAVR/PC_COAST and B2 P2_SAVR/P2_COAST (probe.jsonl). Caveats:
- snapshots are about 2 days apart;
- "sent off" is inferred from the new casts;
- each ledger keeps only its last 300 lines.

| | Sent off | Still here day 3-4 | Still here day 5-7 | Day 8 |
|---|---|---|---|---|
| 8 changes, 4 forts | ~132 | 35 | 23 | 0 |

**The 23 still here at day 6-7:**
- cavern: cave floater x3, rutherer x2, elk bird, jabberer, crundle, bugbat, blind cave ogre;
- river and ocean, which do reach the map edge: giant sea scorpion x2, carp, sperm whale x2, crab, ocean sunfish;
- birds: swan x2, eagle x2;
- land: deer, wild boar.

**None was in a closed pond.** The 12 removal lines still in the ledgers all read exactly "7.0 days". Two of them (raven on PC_COAST, giant dragonfly on P2_SAVR) do not appear in the probe table, so the probe undercounts a little. The data cannot say whether any of these animals would have left on day 8 or day 10.

**The 12 that left on their own between day 3-4 and day 7.** A 3-day grace would have removed these:
- 9 in caverns, rivers or the sea: elk bird, blind cave bear, helmet snake x2, draltha, crundle, giant alligator, two sharks;
- 3 on the surface: raven, turkey, bobcat.

### Thought experiment: 3 days instead of 7
1. **Walkers cut short: about 12 groups over 8 changes, about 1.5 per change per fort.** This is a lower bound, because half the forts' snapshots are on day 4, not day 3.
   - About three quarters are out of sight. The Aquarium view does show fish, though.
   - It works against the natural overlap of the old cast drifting out while the new one arrives.
2. **Slots freed 4 days sooner: about 23 groups x 4 days, roughly 11 slot-days per change per fort.** The gain is smaller than it looks:
   - a paused layer reopens DF's entries only at **2 under its cap** (`pause_margin=2` :1038; `resumeAt` :15673; land :15742; caverns :16385), so removing one leftover (4/4 to 3/4) does not let DF's waves back in;
   - only the tool's own draw can use the freed slot, and in a cavern only after 4 days with no DF wave there (:16007-16009);
   - a layer that is over its cap (PC_SAVR's cavern at 10/7) gains nothing.
3. **Release clock: a tiny change.** A removed leftover's stay feeds the layer's average stay (`observe` :15361-15373, weight 0.2), so the release gaps shrink by a few percent.
4. **Stock: the same total, refunded sooner.** It is still open whether DF *also* refunds an animal that vanishes this way. If it does, every removal is counted twice, and a shorter grace means more removals.
5. **Changing it mid-game acts at once.** `leaveCheck` uses the current setting (:16845), so every group sent off 3 or more days earlier is removed on the next pass.

### Scenarios
- **Ponds only:** pond fish cannot leave, so all of them reach the deadline. 3 days is strictly better here (the X3 case).
- **No water:** only birds, land and cavern leftovers. Mostly you get the downside: slow walkers cut short.
- **Caverns:** the largest group of leftovers, and one freed slot rarely reopens a paused depth.
- **Savage or evil maps:** undead are never removed (`V7.natural` :2569-2582). A removed animal leaves no corpse to raise.
- **Cage traps (inference from the code, not seen on the rig):**
  - the removal copies DFHack's exterminate, but exterminate skips caged and chained creatures (repos/dfhack/scripts/exterminate.lua:19-20);
  - this tool does not skip them, so a trapped wild animal whose season has ended would vanish from its cage at the deadline unless it was tamed first;
  - 3 days leaves the player less than half the time.

### Does it serve your aims?
| Aim | 3 days instead of 7 |
|---|---|
| Diversity | Small gain: the new cast is seen slightly sooner (land, flying, water) |
| Ecology | Neutral to slightly negative: more animals removed mid-chase |
| Naturalistic seasonal balance | Slightly negative: about 1.5 more vanishings per change, mostly out of sight |
| Fewer hacks / tool in control | Negative: the removal fires more often, without knowing why animals stay |

### What I'd do instead
1. **Skip `flags1.caged` and `flags1.chained` in `leaveCheck`**, as exterminate does. This is a bug fix, not a new guard.
2. **Find out why animals stay.** River and ocean fish, cavern animals, birds, a deer and a boar all stayed 6-7 days, and none were in closed water. A "closed water only" rule would catch almost none of them.
3. **If you want to tune without adding code** (your 16 Oct rule):
   - **(a) Change the number to 4-5 days.** That keeps most walkers and trims the tail.
   - **(b) Count sent-off groups as "on their way out" in the caps,** as the cavern trim already does (:16476). Nobody would vanish sooner. The cost is a layer sitting 1-3 over its cap for up to a week, which is inference and needs the rig.

### Rig test that would settle it (not run)
**Setup:** one pacing fort saved just before a season change. Three arms: `groups cavern leave 7`, `leave 3`, `leave 0`. n=5 each, 14 days each.

**Measure:**
- the removal lines and which animals they cover;
- in the 7-day arm, animals alive at day 3 that walked off by day 7, split into surface and cavern/sea;
- new-cast groups per layer on days 1-14, split into tool draws and DF waves;
- days each layer spent paused.

In the 0 arm, log each leftover's position daily, to see whether the deer, birds and ocean fish ever leave and what holds them.

**Side checks:**
- Cage-trap an animal from a group about to be sent off, and watch it at the deadline. Also watch for any DF error.
- Read the entry's stock just before and after one removal, with no arrivals in between. +1 means correct; +2 means DF refunded too.

**Rig test that would settle it:** One pacing fort save from just before a season change. Arms leave 7 / 3 / 0, n=5 each, 14 days each. Measure removals; animals alive at day 3 that walked off by day 7 (surface v cavern/sea); new-cast groups added per layer on days 1-14 (tool draw v DF wave); days paused. In the 0 arm, log each leftover's position daily. Side checks: a cage-trapped sent-off animal at the deadline; entry stock before and after one removal (+1 correct, +2 double refund).

<details><summary>Review and verification trail</summary>

- review: Recommendation (a) was wrong for the data it rests on. It proposed removing at once any sent-off animal in water with no map-edge contact (B.edge). But of the 23 groups still here at day 6-7 in the pacing forts, the water ones were in rivers and the ocean (SILURIAN_JAEKELOPTERUS and FISH_CARP in rivers; SPERM_WHALE, CRAB and FISH_SUNFISH_OCEAN in the ocean), and those touch the edge. The rest were cavern animals (CAVE_FLOATER x2, RUTHERER x2, ELK_BIRD, JABBERER, CRUNDLE, BUGBAT, BLIND_CAVE_OGRE), birds (SWAN, EAGLE) and land walkers (DEER, WILD_BOAR). An edge test would catch almost none of them. Closed water explained X3 (the 9 Oct lake fort), not these forts.
- review: 'Vanish in sight' was overstated. I re-derived the 12 groups that left on their own between day 3-4 and day 7. 9 of the 12 were in caverns or at sea / in rivers (ELK_BIRD, BLIND_CAVE_BEAR, HELMET_SNAKE x2, DRALTHA, CRUNDLE, GIANT_ALLIGATOR, SHARK_REEF_WHITETIP, SHARK_HAMMERHEAD). Only 3 were surface animals a player is likely to watch: BIRD_RAVEN, BIRD_TURKEY, BOBCAT. Probe: data/pacing/{B1,B2}/*/probe.jsonl. My scratch script is under .claude/scratch/sw-questions/e2_strag.py.
- review: The slot gain was overstated. The answer missed pause_margin=2 (seasonal-wildlife.lua:1038; V7.GRP.resumeAt :15673; landPause :15742; cavePause :16385). A paused layer reopens DF's entries only at 2 groups under the cap. So one freed slot (4/4 to 3/4, 7/7 to 6/7) does not let DF's waves back in. Only the tool's own draw or release can use it. That means the land/flying draw (n<cap, when its clock is due, :17418 onward) and the water draw. In caverns, V7.DRAW.caveTick also needs 4 days with no DF wave at that depth (:16007-16009). Some cavern layers were over the cap anyway (PC_SAVR cavern 3 at 10/7), where one removal frees nothing.
- review: The cage-trap finding is now stronger and wider, and it is grounded in code. The comment at :16817 says removal works 'as DFHack's exterminate vaporizes'. But exterminate skips caged and chained units (repos/dfhack/scripts/exterminate.lua:16-22; docs/exterminate.rst:8-9 'Caged and chained creatures are ignored'). leaveCheck (:16846-16852), V7.natural (:2569) and liveMembers (:13436) have no such check; grep finds no 'caged' anywhere in the file. WILD.left (:4360) does not drop caged units from a group either. So any wild animal from a tool group that the player traps in a cage is removed at the grace after its season ends, unless tamed first. A 3-day grace shortens the player's window from 7 days to 3.
- review: Data caveats added. The probe snapshots are about 2 days apart, not daily. 'Sent off' in the table is approximated from the new casts. Turnover counts from the ledger: PC_SAVR 20 (not 21); P2_COAST 15+1. ledger.txt keeps only its last 300 lines, so the 12 'did not walk off' lines are all Autumn 8 and none are from the summer change. Every group still here at day 7 was removed at exactly 7.0 days, so the data cannot show whether they would ever have left. 'Cannot leave' is unproven for them.
- review: Added: the setting is named 'groups cavern leave' (:24082; panel row 'Take off a stuck send-off after', internal/seasonal-wildlife/controls.lua:163), but it applies to every layer.
- review: Added: lowering it mid-game acts at once. leaveCheck compares now - dismissed_at with the new grace (:16845), so any group sent off 3 or more days earlier is removed on the next pass.
- review: Added: a group is checked only once (grp.vanished, :16855). A member skipped at that check (tame, undead, not 'natural') is never checked again and keeps its group in the count until it dies or leaves. This is the same at 3 or 7 days.
- review: Added the user's 16 Oct ruling ('tune existing code, no new caps/guards', beta-rulings-oct16.md) and the 13 Oct 'pause, not trim' principle. Changing one number is a tuning. A tiered rule split by water body is new code. I also offered a different tuning: count sent-off groups as 'on their way out' in the cap counts, as trimOne already does (:16476). I flag it as inference with its costs.
- review: Kept and verified: send-off is immediate (castTurnover :16774-16807 -> dismissGroup :13573-13582); the grace is a deadline (leaveCheck :16836-16862, called each pass :17359); vanish_countdown=1 plus +1 refund (refundUnit :16820-16835); default 7, range 0-60, 0 = off (:1026, :924, :24082); ENGINE.count counts sent-off groups (:7515); cavernPass counts them (:15581-15589); presentRaces counts them on the surface only, not in caverns (:16211-16216); the X3 basis 'median 1.2 d, all within 6.1 d' (commit d2261cf); cavern_draw_grace_days=4 is a separate setting (:1017); observe/W effect (:15361-15373, w_alpha 0.2).
- review: Kept as open: whether DF also refunds a unit removed by vanish_countdown. wilderpop-research.md: 'death never refunded, departure always'. Neither the DFHack xml nor the scripts say what happens to the population on a vanish.
- verifier: castTurnover is a standing rule that runs on every groups pass (comment :16770-16773), not only at the season change. In practice the turnover's send-offs happen on the first pass after the change, and any late arrival of a species no longer cast is sent off the same way.
- verifier: Straggler list: cave floater x3, not x2 (23 groups in total). The ledger also shows two removals at 7.0 days (BIRD_RAVEN on PC_COAST, GIANT_DRAGONFLY on P2_SAVR) that the probe-based table misses, so the probe counts are approximate.
- verifier: The removal from a cage is an inference from the code, unchanged; it is now stated as such.

Code refs: /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:1026 (leave_grace_days=7); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:924 (sanitize 0-60, 0=off); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:1038 (pause_margin=2); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:1017 (cavern_draw_grace_days=4, separate); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:13436 (liveMembers: no caged filter); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:13573-13582 (dismissGroup); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:16774-16807 (V7.GRP.castTurnover); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:16809-16835 (rationale; refundUnit); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:16836-16862 (V7.GRP.leaveCheck; grp.vanished once); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:17359 (leaveCheck each groups pass); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:7515 (ENGINE.count counts sent-off groups); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:15581-15589 (cavernPass per-depth count); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:15673 (resumeAt = cap - pause_margin); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:15735-15746 (landPause resume rule); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:16375-16388 (cavePause resume rule); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:15997-16009 (V7.DRAW.caveTick: n<cap and 4-day no-DF-wave grace); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:16211-16216 (presentRaces: surface only, includes sent-off); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:16432-16440, 16476 (trims treat sent-off as leaving); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:15361-15373 (V7.GRP.observe stay -> W); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:2569-2582 (V7.natural: no caged check; undead excluded); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:4360 (WILD.left); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:5386-5401 (reconcileGroups); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:24082 (verb groups cavern leave DAYS); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/internal/seasonal-wildlife/controls.lua:163 (panel row); git d2261cf (v7.4: grace introduced; walk-offs median 1.2 d, all within 6.1 d, X3); /Users/nathanielcannon/Claude/Projects/DwarfCron/repos/dfhack/scripts/exterminate.lua:16-22 (skips caged/chained); /Users/nathanielcannon/Claude/Projects/DwarfCron/repos/dfhack/scripts/docs/exterminate.rst:8-9; /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/B1/PC_SAVR, B1/PC_COAST, B2/P2_SAVR, B2/P2_COAST (probe.jsonl, ledger.txt); /Users/nathanielcannon/Claude/Projects/DwarfCron/.claude/scratch/sw-questions/e2_strag.py (straggler re-derivation); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/mechanics-diagram.html:247, 1173; memory: beta-rulings-oct16.md, pause-not-trim.md, wilderpop-research.md (refund rules)

</details>

## E3

> If 'held' means "Stock set to 0 and flagged extinct" does this interfere with the check for placing stand-in species?

**Short answer.** No. Holding does not break the stand-in check. The run-out test reads stock (live plus the held copies' reserve) and only after the season's apply. The candidate test counts held stock (quantity plus reserve) and never reads the extinct flag. The one real clash (7 Oct, 17 of 22 swapped) was fixed in v7.3. The problems come after a stand-in is chosen: every copy of it stays open for the rest of the season, the tool's ground, flying and cavern draws never place it, a cavern stand-in opens at every depth, and a save and reload makes it stay in that season every year.

*Status: verified · confidence high · review verdict: minor fixes*

### Short answer
**No. "Held" (stock 0 plus the extinct flag) does not break the stand-in check.**
- The run-out test cannot mistake a held cast member for one that has run out.
- The candidate test does not lose a held candidate's stock.
- The one clash, on 7 Oct, was fixed in v7.3.

**The problems are in what happens after a stand-in is chosen.** The code shows four, and none has been seen on the rig yet:
1. every copy of the stand-in stays open;
2. the tool's own draws do not place it;
3. a cavern stand-in opens at every depth;
4. a save and reload keeps it in that season every year.

### 1. What "held" means in the code
**A held entry has:**
- its stock moved to the tool's reserve;
- its stock set to 0;
- the extinct flag set;
- a record in `RESERVE.held`.

This is done at the season change (`applyLive`, seasonal-wildlife.lua:3907-3911, "both barriers") and on every groups pass (`holdOutOfSeason`, :3931-3950).

**Three kinds of entry are held:**
- every entry of a species that is out of season;
- every copy of a cast species except its one chosen entry (`V7.SRC.isDup` :3381, `ROSTER.wantsRow` :3392);
- cavern entries at depths the species is not cast for (`ROSTER.castDepths` :3223).

**"Paused" is different.** A pause sets only the flag and leaves the stock alone.

### 2. The check, step by step (`ROSTER.exhaustCheck`, :3996-4100)

**Step 1: has a cast member run out?**
- **It waits for this season's apply** (`appliedStamp`, :4003). Before that fix, the first pass of a season found the new cast still held at 0 and swapped 17 of Autumn's 22 for stand-ins. That was holding breaking the check, fixed in 6e1ffb2. The stamp is cleared on map load (:22129), so the check also waits for the first apply after a load.
- **It judges only in-season members whose stock you have not set to 0** (:4007).
- **It adds the held copies' reserve** (:4010). A species whose chosen entry is dry but whose copies hold stock has not run out.
- **It reads stock, never the flag.** It fires after stock reads 0 with none on the map for a full day (:4021-4027). A paused entry (flag set, stock untouched) never reads as run out.
- **Cavern stock above 30** (P10) waits in the chosen entry's own reserve, which the check does not add directly. It still works, because `holdOutOfSeason` runs first in the same pass (:17292, before :17317), and its `topUp` refills a dry chosen cave entry from that reserve (:3829-3837). This depends on the order of the steps alone.

**Step 2: is a candidate eligible, and does it have stock?**
- **The candidates are species out of season this season:** those resting all year, or those cast in another season (:4045-4051). Both kinds are held.
- **The extinct flag is never read.**
  - `inEmbark` is set by the entry existing at all (:2717).
  - `castReplaceOk` (:11096-11139) checks slot, guild, size, biome and the food-web link.
- **`FP.standInStock` (:11144-11164) counts quantity plus reserve** on the entries DF can send from:
  - ground: site tiles only;
  - flying and water: any surface entry;
  - caverns: that depth only.
  - A resting species with 0 on its entries and 120 in reserve counts as 120.

**Step 3: the promotion** (:4067-4089). The stand-in borrows the season. Every one of its entries gets its reserve back, and the flag comes off wherever stock is above 0. A pause that is on closes them again later in the same pass.

### 3. What goes wrong after a stand-in is placed

**All of the stand-in's copies stay open** (code).
- `V7.SRC.chosen` caches its one-entry picks under the key `rows:season:casts_year:castSig` (:3351).
- `CACHE.castSig` is never assigned anywhere in scripts/.
- `CACHE.managedPops` is not rebuilt when the config changes.
- So the pick made before the promotion, when the stand-in was out of season and had no chosen entry, stands until the season changes or the map reloads.
- Until then `isDup` returns false for every copy, and `holdOutOfSeason` never holds them.
- `topUp` and the 30-per-entry cavern cap act only on picked species (:3772, :3820), so a cavern stand-in is not capped at 30.

**How much does that matter?** (inference)
- DF picks surface waves per entry (TR2: 40-58 waves per site-tile entry, 5-10 per neighbour tile). So a stand-in with four open copies is picked more often than a one-entry member at the same FREQUENCY.
- One group per species is on (:1028), so it still has at most one group at a time; it simply returns sooner.
- In caverns the pick appears to follow stock (flesh ball at 395 took 54%, PENDING), so the missing 30 cap could matter more there.

**The tool's own draws do not place the stand-in** (code).
- The v8.1 ground, flying and cavern draws read only the cast lists (`V7.DRAW.members` :15889). A promotion changes allow/assign, not the casts.
- The exhausted member stays on the list but is skipped, because it has no stocked entry (`ROSTER.apex.entries` :11563).
- So the stand-in comes only if DF sends a wave, and ground waves can be rare (0 in 22 days on SW-LAKE-THAW). "A stand-in takes the slot" is often not true in practice.
- I did not check the water draw for this.

**A flying stand-in is filed as land** (code; the effect is inferred). The flying layer is built from the flying cast list (`V7.GRP.flyers` :15854, `flyGroups` :16038). So a flying stand-in's DF wave becomes a land group: it takes a land slot and goes through the land gate.

**A save and reload keeps the stand-in in that season every year** (code).
- Config load rebuilds `x.promoted` with only the season and the species it covers for; the `resting` mark is dropped (:1261-1264).
- `exhaustRoll` sends a seasonless stand-in back to rest only if that mark is set (:3988), then wipes the record.
- The season turn never resets the roster from the casts (:5065-5080).

**A cavern stand-in opens in every cavern** (code). A borrowed season opens every depth (`castDepths` returns nil, :3216-3220, "as before"). But the stock test counted only the depth with the gap, so the stand-in can also come into caverns with no empty slot.

**Run-out is judged per species, not per slot** (code). A cavern member cast at two depths, dry at one and stocked at the other, is not judged run out, so the dry depth's slot stays empty.

**Rig so far:**
- two promotions, too late in the season to show any of this: TIGER for BEAR_GRIZZLY (COAST, Summer 76) and OSPREY_MAN for MEGANEURA_MAN (SAVR, Summer 78);
- PANDA and SEA OTTER found no stand-in on Autumn 2 (failed size and guild). The otters had died in Summer, which fits real exhaustion.

### Does this serve your aims?
**The check does.** A slot changes hands only when its animals are really gone. The stand-in comes from the same slot, is linked into the food web, and uses its own real stock, with nothing invented.

**What follows a promotion does not, yet.** The stand-in can be picked more often than cast members, can fail to arrive at all, or can stay in a season it was never cast for. Each of these works against pacing, seasonal balance and the tool being in control.

**The fixes are bookkeeping, not new mechanisms:**
1. clear `CACHE.srcPick` at a promotion, so the next hold leaves one open entry and the 30 cap applies;
2. keep `resting` when the config is loaded;
3. let `V7.DRAW.members` and `V7.GRP.flyers` include this season's stand-ins in the slot they cover;
4. open a cavern stand-in only at the depth with the gap.

### Rig test (on a test copy, never your fort)
1. Choose a ground or flying cast member with copies on several draw tiles. Set its entries and reserve to 0, kill its animals, and step one day plus a pass. Wait for the ledger line "X takes its niche".
2. After the next pass, list each of the stand-in's entries: stock, flag, and whether it is the chosen entry. The code predicts several open entries; one is intended.
3. Step to the end of the season. The code predicts no "drawn ... (no DF wave waiting)" line for the stand-in, and that a flying stand-in's arrivals are filed as land.
4. Repeat steps 1-2, then save, reload and cross the season change. The code predicts the stand-in keeps allow=true and the borrowed season. Without the reload it should be resting again.
5. Repeat with a cavern stand-in. The code predicts its open stock is above 30 and that it is open at every depth.

**Rig test that would settle it:** On a test copy, not the user's fort. (1) Exhaust a ground or flying cast member that has copies on several tiles. After 'X takes its niche', list the stand-in's entries (stock, flag, chosen). The code predicts several open. (2) Step to the end of the season. The code predicts no tool-drawn line for the stand-in, and a flying stand-in filed as land. (3) Repeat with save, reload and season change. The code predicts allow=true and the borrowed season are kept. (4) Repeat with a cavern stand-in. The code predicts open stock is not capped at 30 and it is open at every depth.

<details><summary>Review and verification trail</summary>

- review: Confirmed the core claims in code. exhaustCheck waits for the season's apply (:4003, commit 6e1ffb2, V73_WATERFALL). It reads stock, never the flag (:3954, :4021-4027). It counts the reserve of the copies the one-entry rule holds (:4010, isDup). The candidate stock test counts quantity plus reserve (standInStock :11144-11165). The candidate list comes from inEmbark, which is set whenever an entry exists, whatever its stock or flag (:2717), so holding cannot hide a candidate.
- review: Wording fix: the candidates are not 'exactly the resting species'. The filter at :4045-4051 admits every species out of season this season: those resting all year (allow=false under casts) and those cast in another season (allow=true). Both kinds are held.
- review: Confirmed the cached one-entry pick. CACHE.castSig is read at :3351 and assigned nowhere in scripts/. srcPick is cleared only by the `groups single` verbs (:24197, :24202). Gap filled: the key also changes when the map reloads, because CACHE.drop sets CACHE.pops=nil (:22129) and managedPops then builds a new rows table. So the extra open copies last until the season change or a reload, not only until the population list changes size.
- review: Qualified the wave estimate of about 2.2x. One group per species is on by default (:1028, speciesPause :16230). It closes all of a species' surface entries while it has a group on the map, so the stand-in still has at most one group at a time. The extra open entries raise its share of DF's picks only while it is absent. The land, flying and cavern pauses also close every entry at the cap.
- review: NEW defect, missed in the original: a save and reload between the promotion and the season change drops the stand-in's 'resting' mark. loadConfigRaw rebuilds x.promoted as {season, for_key} only (:1261-1264). exhaustRoll returns a resting stand-in to rest only if p.resting is set (:3988), so the stand-in keeps allow=true and its borrowed season. The season turn never rewrites allow from the casts (V7.ST.turn :5065-5080). It then comes back every year in that season, outside the cast. The original's 'it rests again at the season change' was too strong.
- review: NEW gap, missed in the original: the tool never places a stand-in itself. V7.DRAW.members (:15889-15905) reads only the casts' member lists, and the promotion edits allow/assign, not the casts. So the v8.1 ground, flying and cavern draws never pick the stand-in. They skip the exhausted member, because ROSTER.apex.entries (:11563) needs quantity > 0. The stand-in comes only through DF's own waves. The diagram's 'A stand-in counts while it covers an exhausted member' overstates this.
- review: NEW, inferred from code: a flying stand-in is not in V7.GRP.flyers (:15854, built from the cast lists). Its DF waves therefore stay land groups: they count against the land cap, the land pause holds them, and flyGroups (:16038) never re-files them as flying.
- review: Cavern note sharpened. castDepths returns nil for a borrowed season, which opens every depth. The comment at :3216-3218 says this is deliberate ('as before'). But the candidate's stock is counted only at the depth with the gap (standInStock), so a cavern stand-in can also come into caverns that have no empty slot.
- review: Confirmed the P10 note: the chosen cave entry's own reserve is not added at :4010. topUp, run earlier in the same pass from holdOutOfSeason (:3946; pass order :17292 then :17317), refills it first, so the count still comes out right, through ordering alone and inside a pcall.
- review: Rig evidence checked: COAST ledger:42 TIGER for BEAR_GRIZZLY (Summer 76) and SAVR ledger:52 OSPREY_MAN (Summer 78). Both came too late in the season to show any after-effect. PANDA and SEA OTTER were exhausted on Autumn 2, the day after the apply. Sea otters had died in Summer (corpse lines), which fits a real exhaustion, but it is not proven.
- review: Rig test extended to cover the reload case, the draw ledger lines and the flying-layer filing.
- verifier: Scope note: the claim that the tool's draws never place a stand-in is verified for the ground, flying and cavern draws (V7.DRAW.members, V7.GRP.flyers). I did not check the water engine's draw here, and SEA OTTER was placed by a tool water draw, so water stand-ins may be placed.
- verifier: Added: the cached pick lasts only until the season changes or the map reloads (the season and the rows table are in its signature), so the extra open copies last for the rest of that season.

Code refs: /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:3996-4100 (ROSTER.exhaustCheck); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:4003 (appliedStamp gate, commit 6e1ffb2); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:4007-4010 (in-season members; held copies' reserve via isDup); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:3954, 4021-4027 (quantity not flag; one-day zero clock); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:4045-4051 (candidates: out of season, resting or cast elsewhere); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:4067-4089 (promotion opens every entry); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:2717 (inEmbark set by entry existence); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:11104-11140 (ROSTER.castReplaceOk); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:11144-11165 (ROSTER.FP.standInStock); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:3907-3911 (applyLive hold), 3931-3950 (holdOutOfSeason); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:3349-3378 (V7.SRC.chosen cache; CACHE.castSig never assigned); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:3384-3396 (isDup, wantsRow); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:3766-3845 (V7.SRC.topUp, P10 level 3814-3838); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:3216-3238, 3397-3405 (castDepths nil = every depth); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:1261-1264 (config load drops promoted.resting); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:3980-3995 (exhaustRoll needs p.resting); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:5065-5080 (V7.ST.turn: no roster reset from casts); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:15881-15943 (V7.DRAW.members/pick read casts only); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:11563 (ROSTER.apex.entries: stocked only); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:15854, 16038 (flyers / flyGroups from casts); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:1028, 16196-16320 (one group per species, default on); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:15735-15790 (land pause); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:17292, 17317, 17410-17416 (groups pass order); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:22129 (CACHE.drop clears CACHE.pops), 24197, 24202 (srcPick cleared); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/B2/P2_COAST/ledger.txt:42, 130-131; /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/B2/P2_SAVR/ledger.txt:52; /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/mechanics-diagram.html (legend 'Held'; 'A stand-in counts while it covers an exhausted member')

</details>

## E4

> Define 'resting' in the context of the statement: "if its species is resting now".

**Short answer.** 'Resting now' means the species is not in the current season's cast, so the tool keeps its entries shut this season. Either it is cast in another season (resting this season, still on the ladder), or the cast builder put it in no cast (resting all year, off the ladder). Code: ROSTER.wants = allow and the season in assign. A shut entry is held: its stock goes to the reserve, the entry is set to 0 and the extinct flag set; a resting cavern species also has its FREQUENCY set to 0 (vermin 1). The hold works per entry, so the page's 'if its species is resting now' is better worded as 'if that entry is shut this season'.

*Status: corrected · confidence high · review verdict: minor fixes*

**"Resting now" means the species is not in this season's cast, so the tool keeps it shut for this season.** There are two ways to be resting:

1. **Resting this season.** The species is cast in another season.
   - Fort 1 (savage marsh): WOLF is cast on the ground in Winter only, so it rests in Spring, Summer and Autumn.
   - GREMLIN is cast in cavern 1 in Summer only. Read in Spring, it shows a ladder value of 58 but a live FREQUENCY of 0 (`summarise.py SAVR_d1.json`).
2. **Resting all year.** The species is on the fort's candidate list, but the cast builder put it in no cast. The evil fort's ledger says "106 species cast in at least one season, 69 resting" (B2/P2_EVIL).

At any given moment the code treats both the same way, and the page's sentence covers both.

### (a) What the code does (`scripts/seasonal-wildlife.lua`)

**The test.** `ROSTER.wants(cfg, key, season)` is `cfg.allow[key] == true and inSeason(...)` (:3216; `inSeason` :1413 checks `cfg.assign[key]`). A managed species (`ROSTER.managedKey` :3213) is resting when `wants` is false.

**Who decides: the cast builder** (`ROSTER.castYear`, :10866-10892).
- A cast species gets `allow = true` and the seasons it is cast in.
- Every other species that a cast layer manages gets `allow = false`, no seasons, and the reason "resting: in no cast this year" (:10878).
- Locked classes (BLOOD_MAN, ELEMENTMAN_MUD) go in `casts.rest`, so they rest too and do not leak in at their raw odds.
- `castRestLayers` (:10797): every layer of a part the tool runs rests what it does not cast, even with no water body on the fort. This is the river-otter fix: 68 otters had been drawn into ponds found after the casts were built.
- Megabeasts and night creatures are not managed (`castManages` :10808). They are outside the tool, so they never "rest".

**What resting does to the entries.**
- **At the season change** (`V7.ST.turn` → `applyLive`, :5072, :3875-3928), each managed entry the season does not want:
  - has its stock added to the reserve;
  - is set to 0 with the extinct flag set ("both barriers (E8: either stops a draw)");
  - is recorded as held.
  - Nothing is deleted; `off` gives it all back (`RESERVE.giveBack`, :3846).
- **Every 300 ticks and every day** (`holdOutOfSeason`, :3931-3951; called from the groups pass :17292 and the daily job :5127). Any shut entry whose stock has risen above 0 has that stock moved to the reserve and is set back to 0 with the flag. **This is the "next hold" in the page's sentence.**
- **Caverns have a third barrier.** A resting cavern species also has its FREQUENCY set to its rest level (`CAVERN.restLevel`, :4623-4630):
  - 0 by default, because the absolute gate is on (:1026);
  - 1 for anything with a vermin tag, because 0 once froze DF on CREEPY_CRAWLER (`CAVERN.zeroLevel`, :4632).
  - The first line of the comment at :4614 still says "default 1"; the lines below it and the code use 0.
- **Surface FREQUENCY is not touched.** A resting surface species is held by its stock, not by its raw value.
- **The apex scheduler** places only species that are wanted now and have stock (:11716), unless the placement is forced.

**When resting ends.** At the species' cast season, `applyLive` gives each of its entries its reserve, plus anything DF refunded meanwhile (:3887-3909), and clears the flag. The daily cavern pass writes its ladder FREQUENCY. A spent entry with nothing held stays spent: the tool does not invent stock.

**The hold works per entry, not per species.** `holdOutOfSeason` tests `ROSTER.wantsRow` (:3392), which also shuts entries of an **active** species that this season does not want open:
- extra copies under the one-entry-per-species rule (`V7.SRC.isDup`, :3381);
- cavern depths whose cast does not hold the species this season (`ROSTER.castDepths`, :3223).

So the page's "if its species is resting now" is a bit narrow. The accurate wording is **"if that entry is shut this season"**. A resting species is the case where every one of its entries is shut.

**The reserve is not only for resting species.** Since v8.1 (P10), `V7.SRC.topUp` limits each in-season cavern member's open entry to 30 animals, moves the excess to the reserve (:3815-3830), and refills a dry open entry from the held copies (:3777-3812). So stock in the reserve does not by itself mean "resting".

**Stand-ins come from resting species.**
- When an in-season cast member is exhausted, `exhaustCheck` (:4045-4051) looks for a stand-in among species not in season, including those resting all year.
- It counts their stock from the reserve (`FP.standInStock`).
- A stand-in that was resting all year is marked `resting = true` (:4073), and `exhaustRoll` rests it again at the next season change (:3988). Note: that mark is lost on a save and reload (:1261-1264), which is a bug.
- Water spill borrowings use the same pattern (`spillRoll`, :5068), but spill is off whenever casts are on (:8899).

### Do not confuse resting with its neighbours
| Term | Applies to | Stock | Extinct flag | Cavern FREQUENCY |
|---|---|---|---|---|
| **Resting** | not in this season's cast | moved to the reserve, entry at 0 | set | 0 (vermin 1) |
| **Exhausted** | in season; stock 0 and none on the map for a day (:3962) | 0, not refilled this season (`exhaustHolds`, :3975) | not forced | ladder value |
| **Paused** (layer or depth at its cap) | in season | untouched | set while at the cap (pause-not-trim, 13 Oct) | untouched |
| **Gate-held** (cavern gate R44) | in season, one of its caverns at its cap | untouched | – | about a tenth of its weight, at least 2 and never above the weight itself (`V7.GRP.holdLevel`, :16520) |

An exhausted species is **not** resting: `wants` is still true. Its slot goes to a stand-in, which usually comes from a resting species.

### (b) What DF does (evidence, not code)
- **Animals that leave are refunded; deaths are not.** DF adds one to the entry for every animal that leaves the map, even detached ones (Wilderpop E15, `wilderpop-research.md`).
- **What stops a draw:** a stock of 0 **or** the extinct flag (E8). DF does not set the flag itself in play (ECO N1).
- **Water:** DF never sends river or lake (feature) entries as waves; it reads them only at embark (E26). For those, resting means the tool's water draw does not pick the species, and the held entries are bookkeeping.

### (c) Thought experiment (inference, labelled)
A Spring group of 6 GIANT_COYOTE is still on the map when Summer starts.
1. At the turn, the coyote entry (say 40) goes to the reserve; the entry is set to 0 with the flag.
2. Cast turnover zeroes the group's leave countdown, so the coyotes walk off. DF refunds 6, and the entry reads 6.
3. Within 300 ticks, `holdOutOfSeason` moves the 6 into the reserve (now 46) and sets the entry back to 0.
4. Next Spring, `applyLive` gives the entry 46 and opens it.
5. If a coyote is still on the map 7 days after the send-off, it is removed and refunded instead (`leaveCheck`), and the hold moves that stock to the reserve the same way.

During those 300 ticks, the extinct flag alone should stop a coyote wave (E8). That holds only if DF leaves the flag set when it refunds, which has not been measured.

**History (git).** Commit bf1440c (v6.3.0) added the flag on held entries and the 300-tick hold together, after the X1 rerun saw cavies drawn from refunds before the daily hold. So the flag alone has never been tested on its own.

**Edge cases:**
- **Caverns not breached:** resting works the same; the entries exist either way.
- **No water, or ponds only:** layers of a part the tool runs still rest what they do not cast.
- **Resting all year:** the species never appears unless it becomes a stand-in for one season. That matches the 7 Oct ruling that a species with no season never comes on the map.

### Does this serve your aims?
Yes. Resting is the "off stage, not gone" state:
- **Seasonal balance:** only this season's cast can arrive.
- **Ecology and pacing:** each species keeps its own stock while away and comes back with its own numbers.
- **Fewer hacks:** no stock is ever deleted.

Animals are a different matter. Cast turnover sends off groups of species no longer cast on every pass, and any still here after the grace are removed and refunded (see E2).

**The weakness is the wording, on the page and in the code:**
- the ledger and the `why` text use "resting" for the all-year case ("69 resting");
- panel 2b's "Resting species: Not on the ladder" (diagram :400) is true only of that case; GREMLIN rests in Spring but is on the ladder at 58;
- the refund sentence (:275) uses "resting" to mean "not cast this season".

**Suggested wording for the page:**
- **resting this season** = cast in another season (on the ladder, shut now);
- **resting all year** = in no cast (off the ladder);
- **held** = how a shut entry is kept closed (stock in the reserve, entry at 0, flag set);
- the refund sentence: "if that entry is shut this season (its species is resting, or it is an extra copy or an uncast cavern depth), the next hold moves it back into the reserve."

### Rig test (not run)
**Question:** does the extinct flag alone keep a resting entry shut after DF refunds a departed animal?
1. On a 1x1 fort, put one out-of-season land group on the map, with `holdOutOfSeason` switched off in the test build only.
2. Set the group's leave countdown to 0.
3. Read the entry's quantity and `flags.extinct` on the departure tick and every 50 ticks for about 2,000 ticks, and log any wave of that species.

**Pass** = quantity above 0, flag still set, and no wave.

**Rig test that would settle it:** The definition needs no rig test. One open point: does the extinct flag alone keep a resting entry shut after DF refunds a departed animal? On a 1x1 fort, with holdOutOfSeason off in the test build only, set an out-of-season group's leave countdown to 0. Read the entry's quantity and flags.extinct on the departure tick and every 50 ticks for about 2,000 ticks, and log any wave of that species. Pass = quantity above 0, flag set, no wave.

<details><summary>Review and verification trail</summary>

- review: Gate-held row was wrong. An in-season cavern species held by the cavern gate is not written to FREQUENCY 0. With cavern_hold_mix on (the default, :1017), V7.GRP.holdLevel (:16520-16523, HOLD_DIV = 10 at :16519) keeps about a tenth of its weight, with a minimum of 1. Only the over-the-ceiling hold and the roster's own holds write CAVERN.SUPPRESSED = 1 (:4564, :4700-4705). The resting level of 0 (vermin 1) comes from CAVERN.restLevel (:4623-4630; also holdFor :16532-16534).
- review: X1 history is settled, not an inference. Git commit bf1440c (v6.3.0) added the extinct flag on held entries and the 300-tick hold together, after the X1 rerun saw cavies drawn from refunds. So the leak happened before the flag existed. Nobody has tested whether the flag alone is enough.
- review: Added that the diagram uses 'resting' in two senses. Panel 2b's row 'Resting species: Not on the ladder' (mechanics-diagram.html:400) is true only of species resting all year. A species resting this season is still on the ladder: GREMLIN is ladder 58 and live 0 in spring on Fort 1 (summarise.py SAVR_d1.json; diagram :437, :547).
- review: Added that the reserve is not only for resting species. Since v8.1 (P10), V7.SRC.topUp (:3815-3830) caps each in-season cavern member's chosen entry at 30 and moves the excess into the reserve, every time the hold runs. It also moves stock between an active species' held copies and its chosen entry (:3777-3812). So 'stock in the reserve' does not by itself mean 'resting'.
- review: Sharpened the point that the hold works per entry. holdOutOfSeason (:3931-3951) tests ROSTER.wantsRow (:3392). The diagram's sentence 'if its species is resting now' is therefore too narrow: a refund into a held extra copy, or into a cavern depth whose cast lacks the species this season, is also moved back.
- review: Apex scheduler: wanted-this-season is required unless the placement is forced (`ROSTER.wants(...) or force`, :11716).
- review: Pause row: the cavern pause is on by default (cavern_pause = true, :1035; V7.GRP.cavePauseOn :16325). The pause works through the extinct flag (pause-not-trim.md). topUp leaves the flag set on a paused layer or depth (:3784, :3810).
- review: Noted a small comment/code mismatch. The comment at :4614-4616 says cavern_rest_freq defaults to 1, but CAVERN.restLevel defaults to 0 under the absolute gate (absolute = true by default, :1026). The code wins.
- review: Checked and kept: ROSTER.wants (:3216), inSeason (:1413), managedKey (:3213), the castYear 'resting: in no cast this year' text (:10882) and casts.rest (:10883, :10891), castRestLayers/castManages (:10797-10815), applyLive (:3875-3928), RESERVE.giveBack (:3836), exhaustCheck stand-in filter (:4045-4051) and promoted.resting (:4073), exhaustRoll rests again (:3988), the B2 evil ledger '106 cast, 69 resting'.
- verifier: 'Nothing is deleted; the only thing that ever sends groups off is cast turnover at the season change' was overstated. castTurnover runs on every groups pass. leaveCheck removes stuck animals after leave_grace_days (refunding them). With the pauses off, the absolute land gate and the cavern trim also send groups off. What is true is that no stock is ever deleted.
- verifier: The cavern gate's hold level is about a tenth of the weight but at least 2, and never above the weight itself (V7.GRP.holdLevel :16520-16524). It is 1 only with cavern_hold_mix off or a weight below 2.
- verifier: RESERVE.giveBack is at :3846, not :3836.
- verifier: Water spill never borrows under casts (spillCheck returns at :8899), so 'spill borrowings work the same way' applies only with casts off.
- verifier: 'DF sends no water waves' is narrowed to river and lake (feature-index) entries (E26).

Code refs: sw-wt/plugin/scripts/seasonal-wildlife.lua:1413 (inSeason); sw-wt/plugin/scripts/seasonal-wildlife.lua:3213-3218 (ROSTER.managedKey, ROSTER.wants); sw-wt/plugin/scripts/seasonal-wildlife.lua:3223-3240 (ROSTER.castDepths); sw-wt/plugin/scripts/seasonal-wildlife.lua:3349-3408 (V7.SRC.chosen, isDup, ROSTER.wantsRow, wantsRowBase); sw-wt/plugin/scripts/seasonal-wildlife.lua:3678-3760 (RESERVE comment, RESERVE.of/set/mark); sw-wt/plugin/scripts/seasonal-wildlife.lua:3766-3835 (V7.SRC.topUp incl. v8.1 P10 cavern open stock 30 -> reserve); sw-wt/plugin/scripts/seasonal-wildlife.lua:3836-3865 (RESERVE.giveBack); sw-wt/plugin/scripts/seasonal-wildlife.lua:3875-3928 (applyLive: hold with both barriers; refund+reserve on reopening); sw-wt/plugin/scripts/seasonal-wildlife.lua:3931-3951 (holdOutOfSeason); sw-wt/plugin/scripts/seasonal-wildlife.lua:3962-3992 (EXHAUST_SETTLE, exhaustHolds, exhaustRoll: stand-in rests again); sw-wt/plugin/scripts/seasonal-wildlife.lua:4045-4073 (exhaustCheck stand-in filter, promoted.resting); sw-wt/plugin/scripts/seasonal-wildlife.lua:4564 (CAVERN.SUPPRESSED = 1); sw-wt/plugin/scripts/seasonal-wildlife.lua:4614-4640 (CAVERN.restSetting/restLevel/zeroLevel; comment says default 1, code 0); sw-wt/plugin/scripts/seasonal-wildlife.lua:4645-4710 (CAVERN.apply: open/held/gate levels); sw-wt/plugin/scripts/seasonal-wildlife.lua:1017,1026,1035 (cavern_hold_mix, absolute, cavern_pause defaults); sw-wt/plugin/scripts/seasonal-wildlife.lua:16519-16534 (HOLD_DIV 10, V7.GRP.holdLevel, holdFor); sw-wt/plugin/scripts/seasonal-wildlife.lua:5065-5080 (V7.ST.turn); sw-wt/plugin/scripts/seasonal-wildlife.lua:5118-5131 (daily tick hold); sw-wt/plugin/scripts/seasonal-wildlife.lua:10792-10815 (ROSTER.castRestLayers, castManages); sw-wt/plugin/scripts/seasonal-wildlife.lua:10866-10892 (ROSTER.castYear: 'resting: in no cast this year', casts.rest); sw-wt/plugin/scripts/seasonal-wildlife.lua:11713-11727 (apex scheduler: wants or force); sw-wt/plugin/scripts/seasonal-wildlife.lua:17286-17292 (groupsTick 300-tick hold, X1 history); sw-wt git bf1440c (v6.3.0: extinct flag + 300-tick hold added together after X1 rerun); DwarfCron/data/pacing/mechanics-diagram.html:119,275,400,437,547,1117-1154; DwarfCron/data/pacing/B2/P2_EVIL/ledger.txt (106 cast, 69 resting); DwarfCron/.claude/scratch/pacing/ladder/SAVR_d1.json via summarise.py (GREMLIN 58 summer-only, WOLF winter-only); memory/wilderpop-research.md (E8 zero OR extinct stops a draw; departure refunded, death never); memory/pause-not-trim.md (pause = extinct flag, stock and FREQUENCY untouched)

</details>

# F. Behaviour switches and housekeeping

*vermin hunting, scavenging, vermin forage, panic, stuck sweep, group packs, land natives: what each does and why it is on/off*

### What these questions are really after
All seven ask one thing: **does each behaviour switch on the mechanics page do what its chip says, and is it worth having for diversity, a believable food web and paced arrivals?** The page does not reliably show what runs in your forts. Checked against the code, the switches fall into four kinds:

| Switch | Page says | What actually runs | Why |
|---|---|---|---|
| Vermin hunting | OFF | **ON** in every fort the tool started since early Oct | opt-in default, but `enable` and a new fort's first load turn on every non-parked switch (`PANEL.fortOn` :20924) |
| Scavenging | OFF | **ON** (same reason) | same |
| Vermin forage | OFF | OFF | parked by your 7 Oct and 16 Oct nudge rulings |
| Panic | OFF | OFF | parked by the same rulings; not a Panel switch at all |
| Stuck sweep 5,000 | on | on, but narrower than described | \"not a nudge\"; skips fliers and only checks tracked groups |
| groups pack 0 | OFF | OFF, and coupling itself is ON | 0 = natural group sizes |
| Land natives | OFF | **adopted and counted anyway** under season casts | `natives_land or cast` (:16886) |

Also, the window's **Reset everything** copies the built-in defaults, so it quietly turns hunting, scavenging and irruptions off in a running fort.

### The common thread
None of the seven switches changes **which species are cast or how many arrive**. Diversity comes from the casts, slots and FREQUENCY, not from these behaviours. They matter for ecology and pacing only at the margins, and in three places they work against your aims:
- Scavenging teleports animals across realms: cavern eaters feed at the sea, and surface fliers can be dropped into sealed caverns.
- Forage's re-point step and panic's \"leader left\" case can hold departing animals on the map, against the v8.1 pacing caps.
- A 600-tick stuck sweep would add constant hops and could put swimmers on the bank.

The levers that make vermin eating real without steering animals are already on: the gobble wiring (a raw write DF honours) and the casts' food-web pairs.

### Combined recommendation
1. **Make the page and the readouts tell the truth.**
   - Hunting and scavenging: ON (\"opt-in default, turned on by enable / new fort\").
   - Land natives: \"adopted and counted under casts\".
   - Stuck sweep: \"tracked non-fliers only; moved to the nearest floor\".
   - Pack: under coupling, not step e.
   - Fix the stale code notes (hunting \"small predators\", the stuck_ticks help, the `status` / `groups natives` natives lines).
2. **Set the defaults to match the forts:** `scavenge.enabled=true` (and decide on hunting) so Reset everything stops switching them off. If hunting really should be opt-in, add it to `V7.ENABLE_LEAVES`.
3. **Keep forage and panic parked, and pack at 0.** None helps diversity or pacing, and forage and panic are path-write hacks of the kind you ruled off. If panic returns, return it narrowed to \"leader died\" only. If forage returns, fix the re-point busy check first.
4. **Leave stuck_ticks at 5,000.** First make the sweep name what it moves (read-only). Then retarget it to animals off valid ground, and make its move water-aware.
5. **The one real ecology decision:** give scavenging a same-realm rule, and drop \"a flier reaches everything\". Settle it with the unbreached-fort realm-leak test after the pacing round. No mid-round changes, per your 2 Oct ruling.

<details><summary>Cross-answer issues the verifier resolved</summary>

- Opt-in vs actually on (F1, F2; consistent, now cross-referenced). The code confirms that vermin hunting and scavenging are both `optin=true` Panel switches with default `enabled=false` (seasonal-wildlife.lua:982, :992). `PANEL.fortOn` (:20924) still turns them on, and it runs from both `enable`/`on` (turn_on :21247-21250) and a new fort's first load (map_loaded :21286-21291). Only `PANEL.allOn` (:20891) respects opt-in. Every B1/B2 status-start reads 'vermin hunting: on' and 'scavenging: on'. One effect is shared and is now stated in both answers: the window's Reset everything (`ROSTER.resetAll` :4919-4924 copies `defaultConfig()`) silently turns off hunting, scavenging and irruptions (`IRRUPT.defaults` enabled=false) in a running fort.
- Turned off by a ruling vs never turned off (F1/F2 vs F3/F4). The questions assume the same history for all four switches, and the code says otherwise. Vermin hunting and scavenging were never switched off; the page shows their built-in default, but forts run with them on. Vermin foraging and panic really are off, by your 7 Oct and 16 Oct rulings (`V7.parkNudges` :1338-1347 sets `vermin_eat.forage=false` and `groups.panic=false`; `V7.PARKED_SWITCHES` = {nudge, forage} :1333). Panic is not a Panel switch at all, so `enable` never touches it.
- Nudge vs not a nudge (F3, F4, F5). All three answers agree with the code comment at :1328-1330: forage walks and panic flight are nudges and stay parked; the stuck sweep and cohesion are 'not nudges' and stay on. Scavenging is the one ruled exception that keeps walks and hops (:1325-1327). F2's teleport finding sits under that exception.
- Coupling status (F3, F6). Both say coupling is ON (unparked 23 Oct, `coupling_v8` :1316-1318). F6's 'pack OFF' is only the pack size, not coupling. Consistent.
- Dismissed groups and panic (F4, F7). `V7.GRP.cohere` returns early for `grp.dismissed` (:13502), so a native sent off by cast turnover never panics, even with panic on. Added to F4 as a scope note.
- Teleports (F2, F5). Both describe unit moves as `dfhack.units.teleport`. F2 covers scavenging hops; their level change comes only through `fallbackMove` near the target. F5 covers the sweep's `regroundNear`, which never keeps the animal's own tile. No contradiction.

</details>

## F1

> What would happen if... instead of "Vermin hunting flags for predatory birds and small land predators OFF" it was set to 'ON'? Was vermin hunting turned off for the tool at some point? I don't remember why. What would happen if it were set to 'ON'?

**Short answer.** Vermin hunting is already ON in your forts. `enable` and every new fort's first load turn it on, even though the switch is marked opt-in and its default is off. Nobody turned it off. On 20 Oct the 'small land predators' half was removed (v7.6.2), so today it flags fliers only: predatory birds and every flier the tool reads as a waterbird. It changes no cast, slot, wave or group. On wild animals no effect has been measured. Its likely visible effect is on your own tame ducks, geese and raptors, which would hunt vermin around food like cats.

*Status: corrected · confidence high · review verdict: major fixes*

### Short answer
**It is already on.** The setting's *default* is off (`hunting={ enabled=false }`, `scripts/seasonal-wildlife.lua:982`), and the Panel marks it opt-in (`:20838`). But two paths turn on every switch except the parked ones (nudge, forage; `:1333`) and deep/livestock (`:1337`), whatever `optin` says (`PANEL.fortOn`, loop at `:20924`):
- `enable` / `on` (`turn_on` `:21247-21250`), since your 4 Oct request (commit 33d72ab);
- the **first load of a new fort** (`map_loaded` `:21286-21291`, v7.2, 7 Oct).

Only the Panel's "All on" respects opt-in (`PANEL.allOn` `:20891`). Every pacing fort's status file reads `vermin hunting: on  dive-hunts 10-27 ... hunts 0` (e.g. `data/pacing/B2/P2_LAKE/status-start.txt`). The one exception: a fort that predates both paths and never had `enable` run keeps the default, off.

**Nobody turned it off.** What changed, on 20 Oct (v7.6.2, 11af873), is that the *small land predators* half was taken out. It enforced your rule "No flying vermin should be eaten by non-flying creatures" (`HUNT.wants` `:17540-17543`). That is probably what you half-remember. The mechanics page line is wrong twice over: it is on, and it covers fliers only.

**A trap:** the window's *Reset everything* copies the built-in defaults over the fort's settings (`ROSTER.resetAll` `:4919-4924`). So it silently turns vermin hunting off, along with scavenging and irruptions.

### (a) What the code does
- **Who gets the flag** (`HUNT.wants` `:17536-17544`). Every species the model calls a *waterbird* gets DIVE_HUNTS_VERMIN, and so does every flier read as a predator. Vermin and locked classes get nothing.
  - "Waterbird" means any FLIER whose raw biomes include an ocean, pond, lake, river or underground-water biome (`MODEL.habitat` `:2215-2224`, `:1782`). That takes in ducks, geese and loons, and possibly giant flying insects.
  - Animal people take their root animal's habitat. That is why ant men and bat men show up in the flagged lists.
- **How it writes** (`HUNT.apply` `:17559-17590`). It covers every allowed species on the candidate list that lives on this embark, not just this season's cast. It sets the flag on each caste that lacks it and records it in `CACHE.hunt`. The flags are undone on off, disable and unload.
- **The casts never see it.** `rawLists` (`:23241-23254`) deliberately ignores the flags the tool wrote. So on or off changes no cast, slot, FREQUENCY value, wave or group.
- **Out-of-date wording.** These still say "small predators hunt them": the Panel note `:20838`, the header `:348`, `internal/seasonal-wildlife/controls.lua:464` and `seasonal-wildlife-web.lua:102`.

### (b) What DF does
- DIVE_HUNTS_VERMIN: the creature dives on vermin from the air. On a *tame* creature it acts like HUNTS_VERMIN, the cat's habit of patrolling food and stockpiles (`DwarfCron/docs/reference/df-creature-tokens.md:91,139`). In vanilla only the peregrine has DIVE and only the cat has HUNTS (memory: no-food-web-in-raws).
- **X5 is the only test, and it is weak.** In the valid rerun (20260926-235757, 2 reps per arm, 3 kestrels and 3 badgers) vermin rose 77-98 -> 353-359 in both arms. But only 0.05-0.08 vermin were within 6 tiles of the subjects. So the result is "no effect seen, with almost no exposure". The first run is void (trap #14: the probe read a field that does not exist).
- Vermin are not units. Even a real effect only thins the loose vermin; it never becomes a hunt of cast prey (`STATE.md:1419-1420`).

### (c) What it means in play (inference)
- **Wild animals:** very likely no visible change either way.
- **Your own animals:** ducks, geese (both [PET]) and any tamed raptor or giant bat would patrol stockpiles killing vermin. That is harmless, but it is a side effect on the fort, not wild ecology.
- **Odd targets:** a dive-hunting duck, goose or loon is not believable. The flagged animal people are intelligent, and the docs warn the flag can stop an intelligent creature you play as from feeding itself. That matters only if one ever joins the fort; it is untested.
- **Pacing results:** hunting was on in every B1/B2 arm, so it does not skew those comparisons.

### Does it serve your aims?
- **Diversity:** no effect.
- **Ecology:** none measured on wild animals.
- **Fewer hacks:** it is a species-wide raw flip labelled "opt-in, OFF" that is in fact running. The believable vermin links already reach DF through the gobble classes (`VERMIN.gobbleApply` `:19194`, on by default `:1079`), and DF honours those (VRM4: 4 and 6 grasshoppers eaten, against 0 in the control).

### Recommendation (your call)
1. **Decide whether it is really opt-in.** If yes, add `hunting` to `V7.ENABLE_LEAVES` (`:1337`) so new forts leave it off, as the page claims.
2. **If you keep it, narrow it** to true raptors (predatory fliers). Drop waterbirds, [PET] species and animal people.
3. **Fix the wording** in the code sites above and on the mechanics page: "predatory and water birds dive for vermin; on via enable / new fort".

### Rig test that would settle it (not run)
- **Fort:** a pacing save with many flagged species, e.g. P2_LAKE. Arms `hunting on` vs `off`, n=5, about 5,000 ticks each.
- **Wild arms:** put vermin near the wild kestrels and owls so exposure is far above X5's. Count vermin removed within about 10 tiles of each flagged unit, plus catch reports. Hand-check each sample line first so it prints a real number.
- **Tame arm:** the fort's ducks or geese by a food stockpile with vermin, on vs off. Count vermin kills and stockpile patrols.
- **Settled if** wild removals clearly beat the off arm. Otherwise the flag does nothing for wild ecology.

**Rig test that would settle it:** Hunting on vs off, n=5 per arm, about 5,000 ticks, on a pacing save with many flagged species (P2_LAKE). Wild arms with vermin placed near the flagged wild fliers (far above X5's exposure); count vermin removed within about 10 tiles plus catch reports, with each sample line hand-checked first. Tame arm: fort ducks or geese by a food stockpile with vermin. Settled if wild removals clearly beat the off arm.

<details><summary>Review and verification trail</summary>

- review: CORE CLAIM WRONG: the earlier answer said hunting was 'never on'. In fact it is ON in every fort you play. The default table has hunting={ enabled=false } (scripts/seasonal-wildlife.lua:982), but two things override it. First, the full `enable` (your request of 4 Oct, commit 33d72ab, 'every panel switch incl. opt-ins'). Second, the v7.2 package (2a2410d, 7 Oct), which runs PANEL.fortOn() on every new fort's first load (map_loaded, :21286-21291). PANEL.fortOn's loop at :20924 sets every switch to true except V7.PARKED_SWITCHES {nudge, forage} (:1333) and V7.ENABLE_LEAVES {deep, livestock, livestockfb} (:1337). 'hunting' is in neither list.
- review: ADDED rig evidence that it is on: every B1/B2 pacing fort's status file reads 'vermin hunting: on'. P2_SAVR has dive-hunts 23, P2_COAST 10, P2_EVIL 14 and P2_LAKE 27, with hunts 0 on all (data/pacing/B2/P2_*/status-start.txt; B1 the same).
- review: ADDED that your own memory note backs this up: user-df-startup-config.md lists vermin hunting among what `enable` turns on. Your onMapLoad.init line was commented out on 7 Oct because the package now does this for every new fort.
- review: ADDED why the page says OFF: the mechanics page and the 'optin' mark show the default table. Panel 'all on' (PANEL.allOn :20887-20891) does skip opt-ins, but `enable`/`on` and the new-fort path do not. Two 'on' paths that behave differently are the likely source of the confusion.
- review: REPLACED the guessed species lists with the real flagged species from the rig status lines: ANT_MAN, BAT_MAN (animal people), BAT_GIANT, BIRD_SWALLOW_CAVE_GIANT, BIRD_DUCK, BIRD_GOOSE, BIRD_LOON, BIRD_OSPREY, BIRD_ALBATROSS, eagle, kestrel, buzzard, owls. Cavern species and sentients are included, so the earlier 'caverns mostly untouched' was wrong. The status line is cut at 90 characters, so these lists are partial.
- review: ADDED the waterbird rule from the code. MODEL.habitat (:2215-2224) calls any FLIER whose raw biomes include a LAKE/RIVER/OCEAN/POOL/SUBTERRANEAN_WATER biome (:1782) a 'waterbird'. HUNT.wants (:17535-17537) then gives every waterbird DIVE_HUNTS_VERMIN whatever its role. A raws scan puts duck, loon, albatross, puffin, osprey and the giant damselfly, dragonfly, fly and mosquito in this group (my reading of the raws, not run in the tool). The only overrides are giant mantis and roach (:814).
- review: ADDED the tame side: DUCK and GOOSE are [PET] in vanilla, and the token reference says DIVE_HUNTS_VERMIN on a tame creature works like HUNTS_VERMIN. So the fort's own ducks and geese probably act like cats while this is on. That is inferred from the docs, not observed.
- review: SHARPENED X5. The first X5 run (20260926-225752) was void: its vermin probe read a field that does not exist and printed -1 (memory: experiment-readout-traps #14). The rerun (20260926-235757) is the one STATE.md reports. It used 2 reps per arm, a 6-tile radius, and 0.05-0.08 vermin near the subjects in both arms. So it shows 'no effect seen at very low exposure', and the 'hunt job' measure may not apply to wild units at all.
- review: KEPT, checked: v7.6.2 (11af873, 20 Oct) dropped HUNTS_VERMIN on small land predators (:17541-17543). HUNT.status still prints 'hunts 0'. rawLists (:23241-23252) keeps the tool's own flags out of the cast builder, and nothing else in the code reads these flags. Gobble is on (:1079).
- review: ADDED the stale wording sites: controls.lua:464, web.lua:102 and the snapshot-only vermin-hunter links in web.lua:184-195, which ignore the switch. Also the Panel note at :20838 and the header at :348.
- review: REVISED the recommendation: the real choice is whether to switch it OFF or narrow it, not whether to switch it on. Options are given in plain terms.
- verifier: Qualified 'on in every fort you play'. It is on in every fort the tool first loaded since 7 Oct (map_loaded -> PANEL.fortOn), and in older forts where `enable` was run (from 4 Oct). A fort that predates both and never had `enable` run keeps the default, off.
- verifier: Added the Reset everything effect (shared with F2): `ROSTER.resetAll` copies `defaultConfig()`, so the window's Reset everything turns vermin hunting off in a running fort.

Code refs: /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:982 (default hunting={ enabled=false }); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:1333 (V7.PARKED_SWITCHES = { nudge, forage }); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:1337 (V7.ENABLE_LEAVES = { deep, livestock, livestockfb } -- hunting absent); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:20838 (Panel row 'hunting', optin=true, stale note); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:20887-20891 (PANEL.allOn skips opt-ins); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:20908-20924 (PANEL.fortOn sets every switch on except parked/ENABLE_LEAVES); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:21221-21249 (turn_on -> fortOn: 'this fort: every feature on'); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:21286-21291 (map_loaded: new fort -> fortOn); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:25344 (enable/on verb -> turn_on); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:17535-17544 (HUNT.wants; v7.6.2 HUNTS_VERMIN dropped); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:17559-17590 (HUNT.apply over allowed in-embark candidate list); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:2215-2224 and :1782 (MODEL.habitat: any flier with a water biome = waterbird); :814 (HABITAT_OVERRIDE); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:23241-23252 (rawLists ignores tool-written hunting flags); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:18618-18627 (HUNT.status); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/internal/seasonal-wildlife/controls.lua:464 (stale note); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife-web.lua:102-114, 184-195 (stale comment; snapshot vermin-hunter links ungated); git 33d72ab (4 Oct: enable turns every switch incl. opt-ins on), 2a2410d (7 Oct v7.2: every new fort), 674c05a (v6.6.0 HUNT), 11af873 (v7.6.2); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/B2/P2_SAVR/status-start.txt, P2_COAST, P2_EVIL, P2_LAKE ('vermin hunting: on dive-hunts 23/10/14/27, hunts 0'); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/experiments/X5/20260926-235757/tally.txt (valid X5 rerun); X5/20260926-225752/tally.txt (void, vermin -1); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/STATE.md:3877-3879 (X5 summary), :1419-1420 (vermin flags act on vermin objects); /Users/nathanielcannon/Claude/Projects/DwarfCron/docs/reference/df-creature-tokens.md:91,139; /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/mechanics-diagram.html:297,1340 (page says OFF); memory: user-df-startup-config.md (enable turns on vermin hunting), experiment-readout-traps.md #14-15, no-food-web-in-raws.md

</details>

## F2

> What would happen if... instead of "scavenging 200 ticks OFF" we set it to 'ON'? I don't remember why we turned it off. What would happen if we turned it back on?

**Short answer.** Scavenging was never turned off. It was written as opt-in (v6.9.0, 30 Sep), but `enable` and every new fort's first load turn it on, and every rig fort reads 'scavenging: on'. Setting the default to ON would mostly just make the page true. It would also stop the window's Reset everything from silently switching scavenging off. The real issues are how it moves animals. A flier counts as able to reach every remains on the map at any depth. Every change of level is a teleport. Nothing checks realm, so cavern eaters feed on sea and surface carcasses and surface fliers can be dropped into sealed caverns.

*Status: verified · confidence high · review verdict: major fixes*

### Short answer
**Scavenging was never turned off. It is already on in every fort the tool starts.**
- The page shows the built-in default: `scavenge={ enabled=false ... }`, commented "opt-in" (`scripts/seasonal-wildlife.lua:992`). That default dates from v6.9.0 (de98161, 30 Sep) and has never changed. No ruling ever switched it off.
- `PANEL.fortOn` turns on every switch except the parked ones and deep/livestock, and it ignores `optin` (`:20924`). It runs from `enable`/`on` (`:21247-21250`) and on a new fort's first load (`:21286-21291`). Only the Panel's "All on" respects opt-in (`:20891`).
- **Rig proof:** every B1/B2 `status-start.txt` reads `scavenging: on`.

**Where the default still bites:** the window's *Reset everything* (`ROSTER.resetAll` `:4919-4924`) copies `defaultConfig()` over the fort. That turns scavenging off in a running fort, along with vermin hunting and irruptions (`IRRUPT.defaults` enabled=false). Setting `enabled=true` in the default would fix that and make the page true.

### What it does (rev 2, after your 27 Oct "scavenging needs to work faster")
It runs every 200 ticks (`SCAV.run` `:20091`, `SCAV.runNatural` `:19919`).
- **Remains it takes:** loose wild corpses and pieces. It skips citizens, tame animals, historical figures, civilised races and animal people, anything in a building or stockpile, forbidden items, items a dwarf has a job on, and forgotten beasts, demons and undead (`SCAV.edible` `:19599`).
- **Who scavenges:** your 27 Oct list (`SCAV.kind` `:19554`).
- **Finding a meal:** a random discovery delay (median 6/3/2 h for small/medium/large remains), plus 3 ticks per tile of distance. A remains counts if it is within perception, **or** "reachable": a walkable path for land animals, the same water body for swimmers, and **always, for any flier** (`SCAV.reachable` `:19787`). Remains are ranked by horizontal distance only (`SCAV.pick` `:19801-19810`), so a corpse many levels below counts as close.
- **Getting there:**
  - **Walking** is a written straight line on the animal's own level only (`SCAV.walk` refuses another level, `:19639`).
  - **Otherwise it hops:** an 8-tile teleport after 200 ticks without progress. Swimmers move only by hops (`:19904`).
  - The 30-tile hop limit is lifted for any "reachable" remains (`:19893`), which means every flier.
  - A hop that ends within 10 tiles lands beside the target **on the target's level** (`SCAV.hop` -> `SCAV.fallbackMove` `:19660-19676`). So **every change of level is a teleport.**
- **Eating:** 15% of the scavenger's own mass an hour, up to 25% a visit, then 6 h sated. At most 5 feeders; smaller species wait for larger ones. The item is deleted when it is used up.
- **Budget:** 12 moves a pass x 6 passes a day = **72 a day**, the real ceiling. `hops_day 200` and `moves_day 300` never bind.

### What DF does on its own
Nothing eats remains. In ECO S, six corpses lay beside vultures, hyenas, bears, raccoons and wolves for 4,000 ticks untouched (code header `:19406-19411`). With scavenging off, remains stay until dwarves haul them or they rot. Rotting is general DF knowledge, not tested here.

### Rig numbers (2-season forts)
| Fort | Hops (teleports) | Per day | Remains finished (lower bound) |
|---|---|---|---|
| B1 PC_COAST | 6,028 | ~36 | ≥60 |
| B1 PC_SAVR | 4,504 | ~27 | ≥43 |
| B2 P2_COAST | 5,605 | ~33 | ≥92 |
| B2 P2_SAVR | ≥6,792 | ≥40 | ≥45 |

- The finished counts are lower bounds because the ledger keeps only its last 300 lines.
- Median time from first sighting to gone: about 5.5 days.
- **Evil maps: no data.** P2_EVIL was lost (0 citizens) in chunk 5 (`B2/P2_EVIL/run.log`).

### Problems worth your decision
1. **Realms mix.**
   - (a) Code: nothing in SCAV checks realm. It only skips the magma sea and underworld (`:19949`), while the ecology's own rule is "one realm" (`:486`).
   - (b) Ledgers: roughly 68 of 244 finished meals had a cavern eater on a surface or ocean species. Examples: a giant olm on grizzlies and sea otters, a giant cave swallow on bluefish.
   - (c) Inference: since level changes only happen by teleport, those cavern animals were hopped there.
2. **Unbreached forts (inference, untested).** A surface raven directly above a cavern-1 corpse ranks it first. It cannot walk there (different level), so after 200 ticks it hops beside the corpse, **inside the sealed cavern**. It is then stuck there, still counted as surface wildlife (`WILD.layerOf` `:4378-4383`). The reverse happens for cavern fliers.
3. **Hunting kills** are fair game until a haul or butcher job claims them (`:19601`).
4. **Ponds or no water:** swimmers only eat in their own water body. Land and flier scavenging is unchanged.
5. **Cost:** never measured per pass. The B1 COAST worst tick was 84 ms overall.

### Does it serve your aims?
- **Ecology: yes in principle.** Carrion feeders make the food web believable.
- **But as tuned it breaks the ecology's own realm rule, and it moves animals mostly by teleport.** Your 27 Oct ruling asked for remains "it can **path** to"; it did not ask for fliers to ignore paths.
- **Diversity:** no effect.
- **Pacing (inference):** a stranded animal may hold a group's place.

### Recommendation
1. **Leave it on.** Fix the page to show ON, with "opt-in default, turned on by `enable` and for every new fort".
2. **Set `enabled=true` in `defaultConfig`** so Reset everything does not turn it off. Check hunting and irruptions the same way.
3. **Your call, code changes:**
   - a same-realm rule for picking remains;
   - drop "a flier always reaches";
   - no hop onto a level outside the scavenger's realm.
4. **To cut teleports, use settings that bind:** `scavenge set hop_wait 600`, `scavenge set moves_pass 4`, `scavenge set hops_day 12`.
5. **In your own game:** `seasonal-wildlife scavenge stats` shows who ate what, and `status` shows hops under `fallbacks:`.

### What would settle it on the rig (not run)
- **Realm leak:** an unbreached fort with scavenging on. Put a surface raven above a fresh wild corpse in cavern 1 and step 2,000 ticks. A leak shows as the raven's z becoming the cavern level, plus a ledger line crediting BIRD_RAVEN. Run the reverse arm too: a cavern flier and a surface corpse.
- **Teleport share:** two forts on the same seed, rev 2 defaults vs `hop_wait 600`/`moves_pass 4`. Compare remains finished per season against hops.
- **Offline:** add the remains' z to the ledger line.

**Rig test that would settle it:** Realm leak: an unbreached fort with scavenging on; a surface raven above a fresh wild corpse in cavern 1; step 2,000 ticks; check whether the raven's z becomes the cavern level and a ledger line credits BIRD_RAVEN. Reverse arm: a cavern flier and a surface corpse. Teleport share: same-seed forts, rev 2 vs hop_wait 600 / moves_pass 4, comparing remains finished per season against hops. Evil-map scavenging needs a fort that survives 2 seasons.

<details><summary>Review and verification trail</summary>

- review: Core claim confirmed: scavenge.enabled=false has been the default since de98161 (30 Sep, 'opt-in'), and `git log -S` shows nobody changed it later. PANEL.fortOn (seasonal-wildlife.lua:20924) turns on every switch except PARKED_SWITCHES and ENABLE_LEAVES without checking optin, and map_loaded (:21285-21292) runs it for every new fort. B1/B2 status files read 'scavenging: on'.
- review: ADDED the one place the default really matters: the window's 'Reset everything' (gui/seasonal-wildlife.lua:1652 -> ROSTER.resetAll :4919-4930) copies defaultConfig, so it silently turns scavenging (and hunting and irruptions) OFF in a running fort. Flipping the default is more than cleanup.
- review: FIXED the evil-map claim. B2 P2_EVIL did not run 2 seasons: it was LOST (0 living citizens) in chunk 5, with 5 checkpoints at about tick 25,600 (run.log, hangs.txt). B1 PC_EVIL has no end status. '125 hops / 4 eaten / too few scavengers on evil maps' rests on a dying fort's first ~10 days, so the claim is withdrawn as unsupported.
- review: FIXED the meal-speed framing, which picked out slow meals. Across all 244 finished meals in the B1/B2 ledger windows, the median is 5.5 days from first sighting to gone, p90 43, max 141.5. Some 200 kg olm corpses went in 1.7-2.8 days.
- review: FIXED the hop budget. hops_day 200 and moves_day 300 never bind, because moves_pass 12 x 6 passes a day (cadence 200, 1,200 t/day) caps walks plus hops at 72 a day. The observed 27-40 hops a day are about half that ceiling. The suggested `hops_day 50` would barely bite, so it was replaced with levers that do.
- review: SHARPENED the realm-leak trace from 'may' to what the code does. SCAV.pick (:19804-19807) ranks remains by horizontal distance only and lets a flier take any remains on the map (SCAV.reachable :19787 returns true), so the 40-tile flier perception does nothing. SCAV.walk refuses any other level (:19639). hop() skips hop_max for reachable remains (:19893). SCAV.hop/fallbackMove land on the target's z (:19684, fallbackMove dz order 0,-1,+1). So every cross-level move the tool makes is a teleport, breached or not. The draft's 'a walkable path existed, so (b)-backed' was misleading: the breach shaft lets canWalkBetween pass, but the tool never walks that path; it hops.
- review: ADDED a ledger tally (my rough species lists, approximate): about 68 of 244 finished meals had a cavern eater on a surface or ocean species, and 12 the reverse. Examples: giant olm on a grizzly bear 28 times, giant olm on sea otters and a hammerhead lying in sea water. The ledger does not record where the remains lay, so this shows realms mixing, not which mover did it.
- review: ADDED the design conflict. The ecology code's own rule is 'Ecology pairs only within one realm (the surface, or one cavern depth)' (:486) and 'no eagle a sea fish' (:381). Scavenging has no such check. The ledger shows a giant cave swallow eating an ocean bluefish.
- review: CORRECTED 'never a humanoid's'. The block is civilised (entity) races and animal people (ALERTS.humanoids :19300). Troglodytes are not an entity race in vanilla and their corpses are eaten (PC_COAST ledger).
- review: CORRECTED the R18 framing. Your own 27 Oct ruling ('any remains it can path to') replaced R18's perception-only rule on purpose. What no ruling asked for is that 'path to' is honoured by teleport chains, and that fliers skip the path test entirely.
- review: ADDED inference (c): a surface raven teleported into an unbreached cavern cannot fly out, and WILD.layerOf (:4380) still counts it as surface wildlife by its population. A unit that never leaves could hold a surface group's place. Not tested.
- review: Kept the page-legend correction: 'Opt-in: enable / All on leaves it as the player set it' is true only for All on (PANEL.allOn :20891), not for enable or a new fort. The same applies to the Vermin hunting and Irruptions rows.

Code refs: /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:992-1003 (defaultConfig scavenge: enabled=false, opt-in, rev 2 values); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:1238-1255 (sanitize: saved enabled kept; rev1->rev2 migration); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:1322-1337 (7 Oct parking 'except for scavenging'; PARKED_SWITCHES, ENABLE_LEAVES); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:20805-20833 (PANEL.SWITCHES scavenge optin=true); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:20887-20895 (PANEL.allOn skips opt-ins); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:20901-20924 (PANEL.fortOn turns opt-ins on); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:21247-21250, 21282-21292 (turn_on and map_loaded -> fortOn); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:4919-4930 (ROSTER.resetAll copies defaultConfig: Reset everything turns scavenging off); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/gui/seasonal-wildlife.lua:1648-1653 (window 'Reset everything' -> ROSTER.resetAll); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:19406-19495 (SCAV header: ECO S evidence, R18 natural cadence, RANGE); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:19300-19316 (ALERTS.humanoids: entity races + animal people only); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:19554-19575 (SCAV.kind); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:19599-19613 (SCAV.edible, in_job check); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:19638-19648 (SCAV.walk: same level only, :19639); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:19660-19695 (SCAV.fallbackMove lands on target z; SCAV.hop z order incl. target z :19684); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:19786-19816 (SCAV.reachable flier always true :19787; SCAV.pick horizontal distance, near-or-reachable :19804-19807); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:19839-19918 (SCAV.turn: budgets, hop() hop_max bypass :19893, swimmers hop :19904, hop after hop_wait :19917); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:19919-19966 (SCAV.runNatural: only 'deep' excluded :19949, no realm check); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:381, 486 (ecology design: one realm; no eagle a sea fish); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:4378-4383 (WILD.layerOf by population origin); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:20091-20117 (SCAV.run, SCAV.schedule); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/docs/v7.1/scav.md:94-135 (R18 history: v7.0 'zap', natural-cadence design); git de98161 (30 Sep, opt-in), 1e04310 (27 Oct rev 2: faster, path-to-any, hop_max bypass); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/mechanics-diagram.html:312,1258,1341,1349 (OFF chips, legend); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/B1/PC_SAVR/status-start.txt:34; B1/PC_COAST/status-end.txt:33; B2/P2_EVIL/status-end.txt:31 (scavenging: on, fallbacks); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/B2/P2_EVIL/run.log (fort LOST in chunk 5, 5 checkpoints); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/B1/*/ledger.txt, B2/*/ledger.txt (244 finished meals; cross-realm pairs); /Users/nathanielcannon/Library/Application Support/CrossOver/Bottles/Win10/drive_c/Program Files (x86)/Steam/steamapps/common/Dwarf Fortress/dfhack-config/init/onMapLoad.init (enable line commented 7 Oct)

</details>

## F3

> What would happen if... instead of "vermin forage 100 ticks OFF" we set it to 'ON'? I don't remember why we turned it off. What would happen if we turned it back on?

**Short answer.** You turned vermin foraging off on purpose. It was parked with the other nudges on 7 Oct and covered by your 16 Oct 'all nudges off' ruling. When it was on (1-2 Oct) it gave a handful of straight-line walks a day, and about 4 of 76 settled walks (~5%) ended in a likely eat. It does not touch casts, waves or groups. Its 100-tick re-point step does not re-check whether the animal has since started fleeing or leaving, so it can override departures, which works against pacing. The gobble wiring, which is on, already makes DF's own vermin eating happen. Keep it off.

*Status: verified · confidence high · review verdict: minor fixes*

### Short answer
You switched it off on purpose:
- **7 Oct:** "Park all nudges ... except where scavenging needs them" (memory season-cast-rulings-oct7).
- **16 Oct:** "ALL nudges of any kind OFF by default", and forage walks are named (memory beta-rulings-oct16; `PLAN.md` R6.1).

Foraging is a nudge because the tool writes a walk toward a target. You can overrule a ruling for one lever, as you did for coupling on 23 Oct (`:1316-1318`). But the evidence says foraging has not earned that.

### (a) What the code does
**The switch**
- Default `vermin_eat={ forage=false ...}`, "v7.3 (F15): parked" (`scripts/seasonal-wildlife.lua:1093`).
- It is listed in `V7.PARKED_SWITCHES` (`:1333`), and `V7.parkNudges` sets it off (`:1342`).
- Parking happens once per config (`:1315`). So `seasonal-wildlife vermin forage on` (`:24408-24415`) sticks after a reload.
- `enable` and All on leave it alone (`:20891`, `:20924`).

**"100 ticks" on the page** is only the follow-up step (`VERMIN.FORAGE.STEP`). Walks are handed out once a day (`cadence=1200`, `VERMIN.forageRun` `:20524-20571`).

**One daily pass**
1. It reads DF's vermin objects (`VERMIN.index` `:20312`). Loose vermin are targets; colonies are a weak 0.25 pull; hidden vermin are skipped.
2. **Eligible eaters** (`VERMIN.forager` `:20418-20428`): wild, natural, not tame, not from the magma sea, not a scavenger busy on remains, idle (`VERMIN.busy`: no job and no Flee/Attack/Leave/... path goal), and carrying a gobble token.
3. Shuffle the eaters and give each a 50% roll, up to 8 walks a pass. Every eater whose roll succeeds gets a 3-day cooldown, even if no walk follows.
4. Find a matching vermin within 20 tiles **on the eater's own level** (`forageOne`, dzMax 0 for walkers).
5. Write a straight-line path to it (`VERMIN.approach`/`walkPath`). It walks, swims or flies; nothing is teleported.
6. **Every 100 ticks, re-point** any forager whose destination changed, up to 3 times (`VERMIN.forageStep` `:20483-20497`). **It does not re-check `VERMIN.busy`.** So if DF has since sent the animal fleeing or leaving, the tool can turn it back toward the vermin. (Code fact; the effect on departures is inference.)
7. DF's own gobble does any eating. The tool scores each walk as likely eaten, missed, gone or expired (`forageResolve` `:20499`).

The forage code is unchanged since 1 Oct; only its default changed (fc27ffa, 9 Oct). It has never run alongside v8 groups, flying counts, pauses or v8.1 pacing.

### (b) What DF does
- **Gobble is real and selective, but the eater must be close.** In VRM2/VRM4, badgers took the written class: 4 and 6 grasshoppers against 0 in the control, all in the first 250 ticks (`DwarfCron/data/eco-desk/findings.md:281-317`).
- Near the fort, cats do most vermin killing: 19-39 per run.
- Colonies are never hunted (`findings.md:175-182`).

### When it was on (1-2 Oct)
Across seven readouts:
| | Total |
|---|---|
| Walks | 97 |
| Arrived | 42 |
| Likely eaten | 4 |
| Missed | 28 |
| Gone first | 3 |
| Expired | 33 |

That is **4 likely eats in 76 settled walks, about 5%**. FALLS_2 alone (41,700 ticks): 16 walks, 0 eaten, 40 "no line" attempts. The budget was never the limit. What limited it was finding a matching vermin on the same level with an unbroken straight line to it.

Two caveats pull in opposite directions:
- some "likely eats" may be another gobbler or a despawn;
- partial swarm eating scores as "missed".

The per-class trace from `vermin eats` would be the honest measure, and no one has read it on a long run.

### Edge cases (inference)
- **Ponds and rivers:** waterbirds walk to the bank. It is unknown whether DF gobbles across the edge, and fish vermin may not restock.
- **Fort:** stockpile rats are targets too, so wild eaters can be walked toward dwarves and livestock.
- **Pacing:** the re-point can hold back a departing group a little. Departures are what free room under the v8.1 caps.
- **Groups:** a member walks off from its leader; never tested with v8 groups.
- **Caverns:** vermin are sparse, so expect almost nothing.
- **Cost:** one scan a day under a 25 ms limit. Cheap.

### Does it serve your aims?
- **Diversity and seasonal balance:** no.
- **Ecology:** a little, at about a 5% hit rate.
- **Fewer hacks, tool in control:** no. It adds unit steering, and it can override flight and departure.
- **The better lever is already on:** the gobble wiring (`v7.gobble=true` `:1079`, `VERMIN.gobbleApply` `:19194`). It is a raw write that DF honours whenever eater and vermin share ground.

### Recommendation
**Leave it parked.** One command turns it back on, and it would stick.

Do not flip it during the pacing round: every B1/B2 result was gathered with it off. If you later want vermin predation to show, first make `forageStep` re-check `VERMIN.busy`, then test.

### What a rig test would settle (not run)
On region9 or the pacing forts, 5 reps per arm, a fresh load per arm, cats penned, and a receipt that the subjects are on the map.
- **VF1** (`docs/v7.1/vermin.md:223-234`): 4 badgers and 20 wired grasshoppers, 15 tiles apart. Forage off vs on (budget 8, chance 1, cooldown 600), 3,000 ticks. Score grasshoppers removed plus forage arrivals.
- **VF6:** a 12,000-tick natural run, on vs off. Score the loose vermin amount per class from `vermin eats`.
- **Add a readout:** re-points on units whose goal was Flee or Leave.

Keep it parked unless "on" clearly beats "off" in both.

**Rig test that would settle it:** Only if the user wants vermin predation to show, and not during the pacing round. First make forageStep re-check VERMIN.busy. Then run VF1 (4 badgers + 20 wired grasshoppers 15 tiles apart, forage off vs on, budget 8 / chance 1 / cooldown 600, 3,000 ticks) and VF6 (12,000-tick natural run, scored by loose vermin amount per class from `vermin eats`). 5 reps per arm, fresh load per arm, cats penned, subject receipt, plus a readout of re-points on Flee/Leave units.

<details><summary>Review and verification trail</summary>

- review: Line refs corrected: v7.gobble=true is at seasonal-wildlife.lua:1079 (not 1083); the parked-once check `if raw.parked == nil then V7.parkNudges(c)` is at :1315 (not 1316).
- review: Added a missed precedent. Coupling was also parked under the same rulings and was unparked on 23 Oct ('Unpark it and finish', comment at :1332). So the 16 Oct ruling can be revisited. The real question is whether foraging pays off, not only that a ruling exists.
- review: Added a code fact the original missed. VERMIN.forageStep (:20483-20497) puts a pending forager back on its line, up to 3 times, whenever its destination changed. It does NOT re-run the VERMIN.busy check. A forager that DF has since sent fleeing, attacking or leaving can be turned back toward its target. The busy/DENY check runs only when eaters are chosen (VERMIN.forager :20420-20428). Inference: this could hold a departing group on the map a little longer, which matters to the v8.1 pacing caps.
- review: Added a measurement limit. 'Likely eaten' counts only a whole vermin object disappearing (forageResolve :20499-20522, idx.alive). If DF takes part of a swarm, that walk is scored 'missed'. So the 4% may understate eating. The per-class loose-amount trace (forageRun :20539-20543) is the real readout, which is why VF6 exists.
- review: Reconciled the totals. The 97 walks use FALLS_2's since-load total (25), not the 16 walks given during the run. Two of the seven readouts (validation/full) were forced `forage now` with walks still pending. Settled outcomes are 76, and 4 of them were eats, about 5%. Checked every readout's numbers against the files.
- review: Clarified 'no line'. It counts attempts (up to 4 per eater, F.TRIES), not eaters. Walkers only consider vermin on their own level (dzMax 0, :20438), and the line must stay in one walk group, so slopes and ramps break it.
- review: Added: the 3-day cooldown is spent when an eater's 50% roll succeeds, even if it then finds no target (st.next set before forageOne, :20556-20557).
- review: Added rig evidence for proximity. VRM2: badgers placed among grasshoppers took 9-15 in 6,000 ticks. VRM2/VRM3b: the fort's own cats took 19-39 and dominate vermin removal near the fort (findings.md:281-291).
- review: Added timing. Every B1/B2 pacing result was gathered with foraging off. Turning it on now would confound the pacing round in progress. Memory inconclusive-mark-pending says no mid-round design changes.
- review: Added: the forage code is unchanged since 1 Oct (git log -G shows nothing after e803e33/33ddedf), but v8 groups, flying counts, pauses and pacing were all built around it since. It has never run alongside them.
- review: Softened the 'better alternative'. Whether the cast's choice of vermin changes which vermin DF actually puts on the map is not verified in code or on the rig, so it is now marked as inference. The gobble wiring (a raws write, on by default) is the proven, nudge-free lever.
- review: Test world. vermin.md names region8. The region9 memory says region9 superseded it on 1 Oct, so the test is placed on region9 or the current pacing forts.

Code refs: /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:1079 (v7.gobble=true); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:1086-1098 (vermin_eat defaults: forage=false, cadence 1200, radius 20, budget 8, chance 0.5, cooldown 3600); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:1281-1296 (loadConfigRaw vermin_eat sanitise); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:1315 (parked once per config); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:1322-1345 (7 Oct park comment, coupling unparked 23 Oct, V7.PARKED_SWITCHES, V7.parkNudges); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:19194 (VERMIN.gobbleApply); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:20213-20238 (VERMIN.FORAGE header, STEP 100, REACH 2, EXPIRE 1500, REISSUE 3, TRIES 4, DENY); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:20312-20366 (VERMIN.index: loose vs colony, weights, hidden skipped); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:20373-20406 (VERMIN.approach, walkPath, moveMode); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:20408-20428 (VERMIN.busy, VERMIN.forager); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:20430-20474 (VERMIN.forageOne, dzMax 0 for walkers); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:20483-20497 (VERMIN.forageStep: re-point up to 3 times with no busy re-check); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:20499-20522 (VERMIN.forageResolve: likely eaten = whole object vanished); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:20524-20571 (VERMIN.forageRun: cadence, trace, cooldown set before forageOne); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:20574-20599 (VERMIN.forageRelease, forageSchedule); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:20891, 20924 (enable / all on leave parked switches); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:24408-24415 (vermin forage on|off verb); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/docs/v7.1/vermin.md (design decisions 1-10, rig tests VF1-VF8, open risks); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/PLAN.md:25-31 (R6.1 every nudge off); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/eco-desk/findings.md:175-182, 281-317 (VR/VRL/VRR, VRM2/VRM3b, VRM4); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/t1-season/FALLS_2/status-start.txt, status-end.txt, summary.md (41,700 ticks); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/web2-live/20261002-192002/fixtures/status.json, 20261002-220129/fixtures/status.json; /Users/nathanielcannon/Claude/Projects/DwarfCron/data/alpha4/20261002-003228/results.json, 20261002-011754/results.json; /Users/nathanielcannon/Claude/Projects/DwarfCron/data/validation/full/20261002-002611/results.json, 20261002-144629/results.json; /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/mechanics-diagram.html:313, 1259, 1342; memory: season-cast-rulings-oct7.md, beta-rulings-oct16.md, inconclusive-mark-pending.md, test-world-region9.md; git: fc27ffa (9 Oct, F15 default off), e803e33 / 33ddedf (1 Oct, last changes to the forage code)

</details>

## F4

> What would happen if... "Panic (scatter from where it fell) OFF." was set to 'ON' by default? Why was it turned off as the default?

**Short answer.** Panic was your 1 Oct idea (R32). It was parked with every other path-writing nudge on 7 Oct (`V7.parkNudges` sets `groups.panic=false`), and your 16 Oct ruling named 'panic flight' among the nudges to keep off. Its one rig test, PAN1, found no clear difference in spread. Turned on, it would push herd, pack, school and pod members outward for 2 days after a leader is lost. That includes a leader that merely walked off the map, which can keep the followers on the map longer and works slightly against pacing. It does not change arrivals, casts or diversity. Keep it off.

*Status: verified · confidence high · review verdict: minor fixes*

### Short answer
**Why it is off**
- **1 Oct, R32:** you ruled "If the leader dies, no leader -- this causes a panic-shock behaviour". It was built and on in v7.1.
- **7 Oct:** you parked every nudge. `V7.parkNudges` sets `groups.panic=false` (`scripts/seasonal-wildlife.lua:1338-1347`; the ruling is quoted at `:1324-1331`).
- **9 Oct (fc27ffa):** the default itself became `panic=false`, "v7.3 (F15): parked" (`:1019`).
- **16 Oct:** you ruled "every nudge off", naming *panic flight*.
- **The rig test was inconclusive.** PAN1 found no clear effect.

**Turning it on** changes only the 2 days after a leader is lost. Arrivals, waves, caps, casts and diversity are untouched.

### (a) What the code does
- **Settings:** `panic=false, panic_days=2, panic_tiles=12, panic_mode='scatter', panic_flocks=false, reelect_after_panic=false` (`:1019-1020`).
- **It is not a Panel switch,** so `enable` and All on never turn it on. Only `groups panic on` does.
- **A saved fort keeps its own value** (`grpSanitize` `:916-917`). Changing the code default alone would not reach existing forts.

**Step by step**
1. **Detection.** The 300-tick groups pass calls `V7.GRP.cohere` (`:13499`) for each group.
   - With cohesion off, a solitary label, or a **dismissed** group, it returns early: no leader, no panic (`:13502-13505`). So groups sent off by cast turnover never panic.
2. **Leader lost** (`V7.GRP.leaderLost` `:15419-15436`). Runs if the leader is no longer a live, active member.
   - It records `died` or `left`.
   - With `panic` on and the group a herd, pack, school or pod (flocks only with `panic_flocks`), it starts a 2-day panic.
   - The flee point is where the leader died, or its last recorded position if it left (`grp.lpos`, up to 300 ticks old).
3. **Each pass** (`panicStep` `:15483-15513`): every member on that level within 12 tiles is aimed 12-16 tiles further out, with about 2 tiles of jitter (`fleeTarget`).
   - It walks a written path of up to 40 steps. Fliers are skipped; swimmers only through water.
4. **No new leader is chosen** whether panic is on or off, unless `reelect_after_panic` is on (`:13514`).

### (b) What the rig showed
PAN1, 2 Oct, 53.16-r2 (`DwarfCron/data/alpha4-sec7/SECTION7-RESULTS.md` row 5): a 6-deer herd, the leader killed with no attacker, 5 reps per arm.
- Panic fired in 5/5 on-cells and 0/5 off-cells. It made 5-14 walks per panic.
- **Spread did not clearly differ:**

| Tick | Panic on (tiles) | Panic off (tiles) | p |
|---|---|---|---|
| t1200 | 25.9 | 20.7 | 0.33 |
| t2400 | 30.1 | 27.2 | 0.52 |

**Caveats:**
- DF's `following` read 0 even with a live leader, so the test compared "unled" with "unled plus pushes".
- The same path lever moved only 3 of 6 hyenas in S2 (`:19409-19411`).
- Path overwrites by DF are an open risk (`docs/v7.1/groups.md:258`).
- It has never been run on 53.17.

### Thought experiment: panic on
1. **A predator kills a stag.** DF animals already flee attackers (DF behaviour; my inference that it covers most of this). The tool's push is radial from the carcass and ignores the killer, so a deer between the hunter and the carcass is sent toward the hunter.
2. **The leader walks off the map. This is the case that matters.**
   - The code panics on `left` too (`:15424-15428`). Your R32 spoke only of a leader that dies.
   - In DF's own waves each animal has its own leave timer, so the leader is often not last to go (memory: wilderpop-research, readout trap #11).
   - The followers, trailing near it, are pushed **back into the map** for 2 days.
   - Groups the tool drew or placed are safe: `sync_countdown` gives every member the leader's timer (`:13543-13547`).
   - Inference: a DF wave could hold its land slot up to about 2 days longer while the land pause holds the next arrival. That is small against a ~29-day stay, but it works against pacing.
3. **Other cases:**
   - Ponds: a school often has no room to flee, so nothing happens.
   - Caverns: walls stop the walks, and `edge` mode means nothing underground.
   - Flocks and fliers: unaffected.
   - Cost: negligible.

### Does it serve your aims?
- **Diversity and pacing:** no gain, and a slight loss in the "leader left" case.
- **Realism:** a little, but DF's own fleeing covers most of it, and the radial direction is unrealistic.
- **Fewer hacks:** it is a path-write hack of the kind you ruled off.

### Recommendation
**Keep panic off for the beta.**

If you want R32 back later, build the narrow version: panic only when the leader **died**, never when it **left** (one condition in `leaderLost`), and ideally flee away from the killer. Neither is built. Rig-test it first.

### Rig test that would settle it
Rerun PAN1 on 53.17, 5 reps per arm, on vs off, three arms:
- (i) the leader killed by a predator placed next to the herd;
- (ii) the leader killed with no attacker;
- (iii) `sync_countdown` off, with the leader's leave timer set to run out first: ticks until the last member is off the map.

In every arm record spread at t300/t1200/t2400, `panic_moves`, and whether a written path is still in place one tick later.

**Rig test that would settle it:** PAN1 rerun on DFHack 53.17, 5 reps per arm, panic on vs off, three arms: (i) leader killed by a placed predator; (ii) leader killed with no attacker; (iii) sync_countdown off, leader's leave_countdown set to run out first, measuring ticks until the last member is off the map. Record mean pairwise spread at t300/t1200/t2400, panic_moves, and whether the written path persists one tick after writing.

<details><summary>Review and verification trail</summary>

- review: Corrected the PAN1 explanation, which had it backwards. The draft said 'only 3-6 forced walks; by the first pass most deer were already more than 12 tiles from the spot'. S7_PAN1.tsv shows the first pass walked 3-4 of the 5 deer in every on-rep, and each panic made 5-14 walks in total (rep 3: 4, 10, 14). Most deer were in range. The walks happened and spread still did not differ clearly.
- review: Fixed the citation for 'never tested on 53.17'. PLAN.md:20 actually says 'Never run on DFHack r2: ... leaders and panic', and SECTION7-RESULTS.md:7 contradicts it (PAN1 ran on 53.16-r2). Restated as: tested once on 53.16-r2 on 2 Oct, never on 53.17. PLAN.md's line is stale.
- review: Made the flight distance exact. fleeTarget (:15437-15455) aims each deer 12-16 tiles further out from where it stands (R + random 0-4), with +-2 tiles of jitter. 'Within 12 tiles' means fewer than 12 tiles in a square measure (panicStep :15497, '< R').
- review: Upgraded the 'leader left the map' case from 'no evidence' to likely. Memory notes give per-unit random leave countdowns of 20k-30k ticks (wilderpop-research.md; experiment-readout-traps.md #11). So in a group DF sent, the leader is often not the last to go. With cohesion on, followers trail within 8 tiles, so they will be near where it walks off. In scatter mode they get pushed back inland. sync_countdown only covers groups the tool drew or placed (cohere :13543-13547).
- review: Added that panicking when the leader LEFT goes beyond the user's own R32 words ('If the leader dies, no leader -- panic-shock'). leaderLost (:15424-15428) panics for 'left' as well as 'died'.
- review: Added that changing the default in code only affects new forts. grpSanitize (:916-917) keeps a saved fort's panic=false. Coupling needed a one-time flag (coupling_v8, :1316-1318) when it was unparked.
- review: Added the precedent: the user unparked coupling on 23 Oct (comment at :1332), even though the 16 Oct ruling said all nudges off. So that ruling can be revised one lever at a time.
- review: Added the realism flaw: scatter is radial from the carcass and ignores where the killer is (fleeTarget). A herd member standing between the hunter and the carcass is sent toward the hunter.
- review: Added evidence on the path-write lever: scavenging finding S2 (:19409-19411) had 3 of 6 hyenas walk 20 tiles under the same kind of written path. The lever works, but only partly. groups.md:258 notes swimmer water paths are untested.
- review: Added that panic needs cohesion on (cohere :13502-13505 returns early otherwise) and runs in place of re-leading (:13513). Added that PAN1's 'following' field read 0 even at t0 with a live leader, so the comparison was 'unled' against 'unled plus pushes'.
- review: Kept the history and code trace that checked out: R32 1 Oct, parked 7 Oct (64f9972), default false plus park-once 9 Oct (fc27ffa, F15), ruled off 16 Oct, not a Panel switch (PANEL.allOn :20887-20891; panic absent from PANEL.SWITCHES), 300-tick pass, 2,400 ticks, flocks and fliers excluded.
- verifier: Added a scope note: a group sent off by cast turnover (`grp.dismissed`) never panics, because `V7.GRP.cohere` returns before the leader check (seasonal-wildlife.lua:13502).

Code refs: /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:905 (V7.GRP.PANICS herd/pack/school/pod); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:916-917 (grpSanitize keeps a saved panic value); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:1019-1020 (panic=false default, F15); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:1315-1318 (park once; coupling_v8 one-time unpark); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:1324-1347 (7 Oct ruling comment, V7.parkNudges sets groups.panic=false); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:13436-13444 (liveMembers: alive and active); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:13499-13549 (V7.GRP.cohere: cohesion gate, leaderLost, panicStep, never re-elect, lpos, sync_countdown for drawn/placed only); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:13551 (applyCohesion), :17361 (called by the 300-tick groups pass); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:15413-15436 (R32 comment; leaderLost panics on died or left); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:15437-15455 (fleeTarget: radial 12-16 tiles from the unit, +-2 jitter; edge mode); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:15456-15482 (walkToward: 40 steps, SeekStation, fliers skipped, swimmers in water); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:15483-15513 (panicStep: < panic_tiles, 8-heading fallback); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:19408-19412 (scavenging S2: path writes moved 3 of 6 hyenas); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:20887-20891 (PANEL.allOn; panic not in PANEL.SWITCHES); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:24136-24151 (groups panic verb); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/internal/seasonal-wildlife/controls.lua:174-181,729 (panic controls; parked status); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/docs/v7.1/groups.md:90-102,143,258 (R32 design; old default true; path-overwrite risk; swimmer paths untested); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/PLAN.md:20 (stale 'never run on r2'), :24-27 (16 Oct ruling: every nudge off incl. panic flight); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/STATE.md:4387 (risk: panic path writes may be overwritten); git 64f9972 (7 Oct, nudges parked), fc27ffa (9 Oct, F15 panic=false default, park once); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/alpha4-sec7/SECTION7-RESULTS.md:7,31,127-142 (53.16-r2; PAN1 and COHT); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/alpha4-sec7/20261002-024942/eco/S7_PAN1.tsv (panic_moves 3-4 at the first pass, 5-14 per panic; following=0 at t0); memory/ecology-design-rulings-oct1.md:31 (R32), memory/season-cast-rulings-oct7.md:26 (park nudges), memory/beta-rulings-oct16.md:17 (all nudges off incl. panic flight); memory/wilderpop-research.md:16 and memory/experiment-readout-traps.md #11 (per-unit random leave countdowns)

</details>

## F5

> What would happen if... "Stuck sweep: animals stuck for 5,000 ticks (in walls, in the air) are put back on the ground" was set to 600 ticks instead? I have seen a lot of stuck animals, especially if they are fliers trying to swim or things like that. This might need more frequent clears.

**Short answer.** 600 ticks would not fix the animals you are seeing. The sweep never touches fliers, at any setting. It only checks members of the tool's own groups. It only knows 'has not changed tile', and its fix is to move the animal to the nearest free floor tile, usually one tile over. At 600 the same chronically still animals (most likely flesh balls in the savage-marsh caverns) would be moved about 8 times as often, resting animals would start being moved too, and swimmers could be put on the bank. Find out what is stuck first; if a shorter timer is still wanted, about 2,500 is defensible, 600 is not.

*Status: verified · confidence medium · review verdict: minor fixes*

### Short answer
600 would not fix what you describe.
- **Fliers are never swept**, at any value (`stuckSweep`, `scripts/seasonal-wildlife.lua:13644,13649`). A bird stuck in water is skipped at 5,000 and at 600 alike.
- **Only tracked group members are checked** (`liveMembers` `:13436-13444`). DF's own unadopted wildlife, pets, livestock and vermin are invisible to it.
- **"Stuck" just means "same tile for `stuck_ticks`".** The fix (`regroundNear(u, 8)` `:6758-6770`) moves the animal to the nearest free floor or ramp tile, never its own tile. That is usually the tile next to it.

### 1. What the sweep does
- **Setting:** `groups.stuck_ticks=5000` (`:1010`). A config accepts any whole number of 1 or more; the Controls tab steps by 500 from 500.
- **When:** every groups pass (300 ticks). It is called right after cohesion (`:17363`).
- **Memory only:** the record is not saved, so the clock restarts at every reload.
- **Ground** (`groundTile` `:6714-6728`): a floor or ramp tile, not a tree, not magma, no unit on it. **Water is allowed.**
- **The search** checks rings 1-8 on the animal's own level first, then each level below, down to 12. So an animal on normal ground moves one tile; only one in a canopy drops down. The canopy is what the sweep was built for, in v5.7, when the old ecology nudge put wolves in trees.
- **The clock restarts after every attempt**, whether or not the move worked.
- **The ledger line** reads only "N stuck animal(s)", labelled `land`, with no names (`:17365`).
- **Wrong descriptions:**
  - The page's "in walls, in the air": the code never checks for walls, and it skips fliers.
  - The Controls help text ("a follower that cannot reach its leader is moved beside it", `internal/seasonal-wildlife/controls.lua:175`): the code moves any tracked non-flier to a tile beside *itself*.

### 2. What is being swept (rig)
| Fort (84 days) | swept | flesh-ball groups at end |
|---|---|---|
| B1 SAVR | 148 | 4 |
| B2 SAVR | 177 | 5 |
| B1 / B2 COAST | 6 / 6 | 0 |
| B2 EVIL | 0 | 0 |

- B1 SAVR shows sweeps of exactly 3 every ~4.17 days. That is the 5,000-tick cycle, so the same animals sit still right after each move.
- B2 SAVR: about 9 chronically still animals.
- **Inference, not proven: mostly flesh balls.** High counts appear only on forts with flesh balls. The vanilla raw describes a very slow creeper (GAIT 6900, NOBREATHE) living near underground ponds. Moving one a tile neither helps nor harms it.
- Water animals rarely trip the 5,000-tick sweep: COAST had only 6 sweeps in 84 days.

### 3. Thought experiment at 600
- **Chronic animals:** each is swept about every 600 ticks, not every ~4.2 days. On SAVR that is about **17-18 moves a day instead of ~2**, and none of them gets better.
- **Fliers:** no change.
- **Pacers:** an animal stepping between two tiles is never caught at any value.
- **Resting animals (inference):** anything holding one tile for half a day gets a pointless one-tile hop.
- **Caged wild animals:** they stay tracked (`reconcileGroups` drops only dead or departed units). What a teleport does to a caged unit is unknown.
- **Water animals:**
  - Unlike `ecoPlaceNear` (`:6743-6755`), which uses `waterTile` for aquatic animals, the sweep only looks for ground.
  - In a pond the tile is floor-shaped water, so a fish usually moves to the next pond tile.
  - In a deeper river, lake or sea, a swimmer above the bottom has no floor on its level, so a **bank within 8 tiles is picked before the bed below**. A gill-breather put on the bank would suffocate (DF behaviour; never seen here). Each loss would empty a water group and trigger a fresh water draw.
- **Cost:** a failed search checks about 3,800 tiles, and at 600 that happens about 8 times as often.

### 4. The fliers you see in water
The tool does not put fliers in water:
- air-breathing arrivals for a water body are placed on the shore (`V7.WAT.entryIn` `:8593-8605`);
- water-cast birds and the flying cast are DF's waves, relabelled where they stand, not moved (`:15822-15840`, `:16038`).

So what you see is DF movement, or a bird hovering or perched, or webbed or wounded, or something untracked (inference). The old stranding rescue was removed by your 2 Oct ruling, "real beaching is DF's" (`:8461-8468`). A new flier rescue would be the kind of guard your 16 Oct ruling forbids.

### 5. Does 600 serve your aims?
- **Diversity and pacing:** no.
- **Naturalism:** no; animals visibly hop.
- **Fewer hacks:** no; it turns a rare safety net into a constant teleporter.

### 6. Better plan
1. **Find out what is stuck.** Make the sweep line name each animal (species, layer, tile kind, water level). Add a one-time read of still fliers. In your own game: one read, no polling.
2. **If they are flesh balls,** stop sweeping animals already on valid ground. That puts the sweep back on canopies (and walls, if you want the page's promise).
3. **Make the move water-aware** (`waterTile` for aquatic animals, as `ecoPlaceNear` does). This tunes existing code; it adds no guard.
4. **Decide about the fliers** after step 1.
5. **If you still want a shorter timer:** about 2,500 ticks.

### 7. Rig test (not run; the rig is busy)
- **Step A, read-only:** load a B2 SAVR save (K70/K77) on a build that names swept animals and step about 10 days. List every tracked unit still for 600+ and 5,000+ ticks, with species, layer, tile kind, water level, flier flag and breathing state. Do the same on a COAST save as the control.
- **Step B, only if A finds a harmful cause:** 5,000 vs the proposed value, n=5, one season, on new SAVR embarks with the caverns breached. Score sweeps per day by species, deaths within 1 day of a sweep, water draws, and `groups:sweep` ms.

**Rig test that would settle it:** Step A (read-only): load a B2 SAVR save (K70/K77) on a build whose sweep line names each animal, step about 10 days, and list every tracked unit still for 600+ and 5,000+ ticks with species, layer, tile kind, water level, flier flag and breathing state; repeat on a COAST save as a control. One one-time read (no polling) of stuck fliers in the user's own game. Step B, only if A finds a harmful cause: 5,000 vs the proposed value, n=5, one season, new breached SAVR embarks; score sweeps per day by species, deaths within 1 day of a sweep, water draws, groups:sweep ms.

<details><summary>Review and verification trail</summary>

- review: Identified what is most likely being re-swept on SAVR, which the first answer left as unknown. The high counts only appear on forts that have flesh balls. B1 SAVR has 10 flesh balls and swept=148. B2 SAVR has 14 and swept=177. B1 and B2 COAST have none and swept=6, and B2 EVIL has none and swept=0. The sweeps of exactly 3, every 4.17 days, fit the 'cavern2:FLESH_BALL x3' groups. Evidence: data/pacing/B1/PC_SAVR/groups-end.txt, data/pacing/B2/P2_SAVR/groups-end.txt, the COAST and EVIL groups-end.txt files, and the ledger.txt files. Raw: creature_next_underground.txt FLESH_BALL is a slow creeper (GAIT 6900), NOBREATHE, NO_SLEEP, CANNOT_JUMP. This is labelled as an inference.
- review: Corrected the reground search. It never uses the animal's own tile: `(dz ~= 0 or r > 0)` at seasonal-wildlife.lua:6764. groundTile rejects any tile with a unit on it (:6726). So the first candidate is a neighbouring tile, and for an idle animal on ordinary ground the 'rescue' is a one-tile hop.
- review: Corrected the claim that pond fish are 'usually' put on the dry bank. A murky pool tile has shape FLOOR (DFHack df.d_basics.xml:6166-6169, MurkyPool shape FLOOR, material POOL). groundTile only rejects magma (:6725), so it accepts a pond tile. A pond fish is usually moved to the next pond tile. Only a fish on the edge can land on the bank, depending on scan order. The real beaching risk is for swimmers higher up a river or lake column. The search covers all 8 rings at the animal's own z before it goes down (:6760-6766), so a bank tile at that z is chosen before the bed.
- review: Added that on COAST (sharks, stingray, crab, olms, cave crocodiles, toads) only 6 sweeps happened in 84 days. So at 5,000 ticks, water animals almost never hold one tile. Nobody has measured what happens at 600.
- review: Removed option (a), 'fix where the tool puts fliers'. The tool already puts air-breathing water arrivals on the shore (V7.WAT.entryIn air branch, :8593-8605, F17; airBreather :8702). Water-cast birds are DF's own waves that are relabelled in place, not moved (V7.GRP.waterBirdGroups :15822-15840). flyGroups (:16038) only relabels. So any flier you see in water was not put there by the tool's placement.
- review: Marked option (b), a flier-drowning rescue, as against the 16 Oct beta ruling: 'tune existing code ... not by imposing additional hard-coded caps or guards; never propose a new cap or guard as the first answer' (memory beta-rulings-oct16.md). The 2 Oct 'beaching is DF's' ruling (:8461-8468, :12459-12461) points the same way.
- review: Removed an unsupported reason. The first answer said the sweep was kept because it was rare. The code note (:1328-1330) only says the sweep and cohesion 'are not nudges and stay'.
- review: Added that the sweep only sees animals in the tool's own groups (g.groups through liveMembers :13436-13444). Animals the tool does not track are never swept at any setting: DF's own wildlife it has not adopted, pets and livestock, and vermin.
- review: Kept and confirmed these: default 5000 (:1010); any whole number of 1 or more accepted from a config (:1179-1181); Controls row min 500, step 500, help text wrong (controls.lua:175); fliers skipped (:13644, :13649); clock restarted after every attempt (:13651); stuck positions not saved (:5351-5354); ledger line hard-coded 'land' with no animal named (:17365); a two-tile back-and-forth is never caught; the B1 pattern of 3 every 4.17 days; about 9 animals still on B2 SAVR (55 sweeps over about 26 days); page wording at mechanics-diagram.html:1177.
- review: Replaced the first rig test, which changed behaviour across two arms with n=5. The first step is now a read-only list of the tracked animals that have been still 600+ and 5,000+ ticks on an existing SAVR save, plus a one-time read of the stuck fliers in your own game. An arm test only follows if a real harmful cause turns up.

Code refs: sw-wt/plugin/scripts/seasonal-wildlife.lua:1010 (stuck_ticks=5000 default); sw-wt/plugin/scripts/seasonal-wildlife.lua:1179-1181 (config accepts any int >=1); sw-wt/plugin/scripts/internal/seasonal-wildlife/controls.lua:175 (min 500, step 500; help text wrong); sw-wt/plugin/scripts/seasonal-wildlife.lua:13636-13657 (stuckSweep: fliers skipped :13644/:13649, re-anchor :13651); sw-wt/plugin/scripts/seasonal-wildlife.lua:13436-13444 (liveMembers: tracked groups only); sw-wt/plugin/scripts/seasonal-wildlife.lua:6714-6728 (groundTile: floor/ramp, water allowed, magma refused, occupied refused); sw-wt/plugin/scripts/seasonal-wildlife.lua:6758-6770 (regroundNear: own tile skipped, own z rings 1-8 first, then down 12); sw-wt/plugin/scripts/seasonal-wildlife.lua:6743-6755 (ecoPlaceNear uses waterTile for aquatic; sweep does not); sw-wt/plugin/scripts/seasonal-wildlife.lua:17363-17365 (groups pass calls sweep; ledger line 'land', no animal named); sw-wt/plugin/scripts/seasonal-wildlife.lua:5351-5354 (stuck positions not persisted); sw-wt/plugin/scripts/seasonal-wildlife.lua:5380-5400 (gone/reconcileGroups: caged units stay tracked); sw-wt/plugin/scripts/seasonal-wildlife.lua:1325-1330 (nudges parked; sweep 'not a nudge', stays); sw-wt/plugin/scripts/seasonal-wildlife.lua:8461-8468, 12457-12462 (stranding guard removed 2 Oct; beaching is DF's); sw-wt/plugin/scripts/seasonal-wildlife.lua:8577-8613, 8702 (V7.WAT.entryIn: air-breathers placed on shore; airBreather); sw-wt/plugin/scripts/seasonal-wildlife.lua:15822-15840 (waterBirdGroups relabels DF waves, no move); sw-wt/plugin/scripts/seasonal-wildlife.lua:16038-16058 (flyGroups relabels only); sw-wt/plugin/STATE.md:1498-1510 (addendum 41: why the sweep, ravens perch, 5000); DwarfCron/repos/dfhack/library/xml/df.d_basics.xml:6166-6169 (MurkyPool shape FLOOR); Dwarf Fortress data/vanilla/vanilla_creatures/objects/creature_next_underground.txt FLESH_BALL (GAIT 6900, NOBREATHE, NO_SLEEP, CANNOT_JUMP, near underground ponds); DwarfCron/data/pacing/B1/PC_SAVR/{ledger.txt,groups-end.txt} (swept=148, 10 flesh balls, 3-every-4.17-days); DwarfCron/data/pacing/B2/P2_SAVR/{ledger.txt,groups-end.txt} (swept=177, 14 flesh balls, 55 in ~26 days); DwarfCron/data/pacing/B1/PC_COAST, B2/P2_COAST, B2/P2_EVIL groups-end.txt (swept 6/6/0, no flesh balls); DwarfCron/data/pacing/mechanics-diagram.html:1177 (panel i wording); memory/beta-rulings-oct16.md (no new caps/guards; all nudges off)

</details>

## F6

> What does "groups pack N OFF (0)" mean?

**Short answer.** `groups pack N` sets the size of a predator wave that coupling calls in, where a prey arrival calls its cast predators. At 0 (the default, shown as OFF) the tool writes nothing and each predator arrives in its own raw group size. At N > 0 every called predator's group size is written to exactly N for the length of the call (rig: pack 5 gave BADGER x5, and a coupled cougar group of 6). Coupling itself is ON. Keep pack at 0: one fixed number erases the species' natural group sizes. Use `size KEY N` for a single species.

*Status: verified · confidence high · review verdict: minor fixes*

### What it means
`groups pack N` sets how many animals come in a **predator wave that coupling calls in**. Coupling is the step where a prey arrival calls in its cast predators.
- **0 (default, shown as OFF):** the tool writes nothing. Each called predator arrives in its own raw group size.
- **N > 0:** each called predator's raw group size is written to {N, N} while the call is open.

The OFF chip is about the pack size only. **Coupling itself is ON.**

### What the code does
- **Stored** as `groups.pack`, default 0 (`scripts/seasonal-wildlife.lua:1009`). Loading accepts any whole number of 0 or more (`:1169`).
- **Ways to set it:**
  - console `seasonal-wildlife groups pack N` (`:24266-24268`);
  - the window's **Live tab K key**, which steps it 0 -> 3 -> 5 -> 8 -> 12 (`gui/seasonal-wildlife.lua:1179-1186`), so a stray K press turns it on;
  - the web page refuses it.
- **Used only when a coupling call starts** (`V7.GRP.coupleStart` `:5571-5622`):
  - it picks the prey's cast predators for this season that are not already on the map and have stock in a surface entry;
  - it closes the other surface entries;
  - if pack > 0, it saves each called predator's `cluster_number` and writes {N, N} (`:5608-5614`).
  - The casts-off path does the same (`:5687-5698`).
- **Restored** by `endCoupling` (`:5719-5722`) when the first called predator arrives, or after 2 days (`:17367-17373`), and on off/disable. So normally only the first called wave comes at size N.
- **Nothing else uses it.** A comment at `PATTERN.openOnly` (`:13248-13250`) says otherwise, but that function writes no size (`raws = {}`).
- **History:** added in v5.5 (8d76f40, 17 Sep) as "sized packs for the piggy-back", default 0 ever since. Kept as-is in the v8 coupling rewrite (9eb6678, 23 Oct).
- **Diagram fix:** panel 5 lists `groups pack N` under step e. It belongs under step j (coupling). Step e (`:17322-17324`) writes the trickle size, the animal-people cap and your per-species sizes.

### What DF does (rig)
- DF reads the group size at the moment it draws a wave. Writing {7,7} gave seven and {2,2} gave two (E12). The value is creature-wide (`RESEARCH-NOTES.md:108-112`).
- **T3** (STATE.md Addendum 22): `groups pack 5` gave "BADGER x5, exactly the configured pack size" against the badger's raw 4-12. The raws read back as the originals afterwards.
- **T5** (Addendum 41): a coupled cougar group of six arrived, though cougars are 1:1 in the raws.
- DF may draw one over the maximum (E42b: trios under {2,1}). This is untested at a fixed size.

### Thought experiment: pack 7
| Called predator | Raw group size | At pack 0 | At pack 7 |
|---|---|---|---|
| Hyena | 5-15 | 5-15 | 7 |
| Coyote | 2-10 | 2-10 | 7 |
| Lion | 1-3 | 1-3 | 7 |
| Bobcat | 1 (stock 2-3) | 1 | 7 |

- **Every called predator looks alike.** Lone hunters become packs and big packs shrink. That erases a believable difference between species.
- **Small stock is an open question.** `coupleStart` only checks that stock is above 0 (`:5597`). What DF does when stock is below N is not in the code or the evidence; only the rig can say.
- **Species-wide write (inference):** a cavern entry for the same species, which coupling does not close, would also draw at N during the call.
- **Your per-species sizes win.** `PATTERN.sizeApply` runs every pass, before coupling (`:17324`, `:13324-13342`), so `size KEY N` overrides the pack size within one pass.

### Not to be confused with
- `groups cohesion ... pack 4`: how far pack members follow their leader.
- `hunters pack on|off`: pack hunting.
- `cast set pack 3`: the x3 pick weight for pack predators in the cast builder.
- `groups apcap 5`: the size cap for animal-people groups in the caverns.

### Recommendation
**Keep it at 0.** It was a blunt v5 test lever, and 0 lets each species arrive in its natural group size. That serves diversity, a believable food web and fewer hacks.
- For one species, use `size KEY N`.
- If you ever want a global rule, make it a scaled one (e.g. x0.5 of the raw range, at least 1), not one fixed number.

### Rig test (only if you want to use it)
One coupling fort, `pack 0` vs `pack 5`, n=5, including a called predator whose stock is below 5. Score each called wave's size by the stock lost. This settles whether DF caps the wave at the stock, skips it, or draws N; whether the one-over happens; and that the raws are restored.

**Rig test that would settle it:** Not needed to answer the question. Only if the user wants to use it: one coupling fort, pack 0 vs pack 5, n=5, including a called predator with stock below 5 (e.g. bobcat at 2-3). Score each called wave's size by stock lost; settles whether DF caps at stock, skips or draws N, whether the one-over occurs at a fixed size, and that raw ranges are restored after each call.

<details><summary>Review and verification trail</summary>

- review: Added direct rig proof that the lever works, which the draft did not cite. STATE.md Addendum 22 (T3, 17 Sep) records that with `groups pack 5` the called wave was 'BADGER x5 -- exactly the configured pack size', against raws of 4-12, and that the raws were restored afterwards (BADGER 12/4, COUGAR 1/1). STATE.md Addendum 41 (T5) records that 'a coupled cougar group of six' arrived although the cougar's raws are 1:1, so the lever really turns a solitary hunter into a pack. The draft's evidence was only E12 and E42b.
- review: Marked '7 (sometimes 8)' as inference. E42b measured the one-over at {2,1} only. The code's own comment at seasonal-wildlife.lua:13320-13323 (PATTERN.sizeApply) says X4 is still to measure whether the one-over holds at a fixed size. T3's pack 5 gave exactly 5. T5's six cougars is consistent with one-over, but T5's pack setting is not recorded, so it proves nothing either way.
- review: Made clear that the OFF chip refers to the pack size only. Coupling itself is ON by default (config 1009 `coupling=true`; v8 unparked it in 9eb6678; diagram step j shows 'Coupling ON'). With pack 0, coupling still calls predators, at their own raw sizes.
- review: Added that the call ends as soon as the first called predator is discovered (17367-17373), and endCoupling then restores every saved range (5717-5722). So normally only the first predator wave of a call is drawn at size N.
- review: Added the second way to switch it on, which the draft missed: in the window's Live tab the K key cycles pack size through 0, 3, 5, 8, 12 (gui/seasonal-wildlife.lua:1179-1186, labels at 523/547). It is also shown on the Layers tab (1265). The controls registry lists it as console/Live-only (internal/seasonal-wildlife/controls.lua:1087-1088). An accidental K press therefore turns it on.
- review: Flagged a stale code comment. PATTERN.openOnly (13248-13250) says pattern tables also write {pack, pack}, but the function stores `raws = {}` and writes no cluster range (13275-13276). The draft's 'only coupling uses it' is right in behaviour, and the comment is misleading.
- review: Added that the raw write is creature-wide (RESEARCH-NOTES.md:108-112: cluster_number is creature-wide). During the window, any draw of that species from an entry still open would also come at N. This is inference: v8 closes every other surface entry, but cavern entries are not touched by coupleStart.
- review: Checked the order of writers in the groups pass: trickleApply, then apCap, then sizeApply (17322-17324), then coupling start (17377-17390). A per-species `size KEY N` therefore overwrites the pack write at the next pass, and that pass is at most 300 ticks later (the 300-tick GROUPS_JOB, STATE Addendum 22). Confirmed.
- review: Softened the food-web-model point. classify() is memoized once per world (CACHE.class, 2107-2109), so the model would read N only if the first classification of that world happened inside a window. That risk is small.
- review: Dropped the IRRUPT.clusterMax point. Irruptions are a cavern mechanism, and coupling only touches surface predators, so the overlap is not relevant here.
- review: Checked the vanilla raws: lion CLUSTER 1:3 (POP 5:10), hyena 5:15, coyote 2:10, jackal 1:5, bobcat 1:1 (POP 2:3). The table is right.
- review: Checked the history: `git log -S'pack=0'` returns only 8d76f40 (17 Sep, v5.5), so the default has always been 0. PLAN.md:823 logs the decision 'Wave size is a lever now (groups pack N), reversing the v4 decision'.

Code refs: /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:1009 (groups defaults: coupling=true, pack=0); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:1169 (config load groups.pack); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:5520-5533 (v8 coupling header: sizes packs from groups.pack, 0 = the raw's); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:5571-5622 (V7.GRP.coupleStart; want filter 5590-5598; pack write 5608-5614); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:5646-5703 (startCoupling, casts-off path; pack write 5687-5698); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:5704-5745 (endCoupling restores cluster_number); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:17322-17324 (step e: trickleApply, apCap, sizeApply); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:17367-17390 (coupling end on first predator arrival or timeout; start); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:13248-13276 (PATTERN.openOnly: stale pack comment, raws = {}); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:13320-13342 (PATTERN.sizeApply; X4 one-over comment); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:2107-2109, 2121-2123, 2146-2147 (classify memoized per world; model reads cluster_number); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:20769, 20873 (coupling restored on disable/off); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:24266-24268 (groups pack verb); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/gui/seasonal-wildlife.lua:1179-1186, 523, 547, 1265 (Live tab K cycles 0/3/5/8/12; Layers row); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/internal/seasonal-wildlife/controls.lua:1087-1088 (groups.pack console/Live only); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/STATE.md Addendum 22 (T3: pack 5 -> BADGER x5, raws restored) and Addendum 41 (T5: coupled cougar group of six, raws 1:1); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/RESEARCH-NOTES.md:108-112 (cluster_number creature-wide, read at draw, [0]=max); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/PLAN.md:823 (decision: wave size is a lever); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/USAGE.md:359, 573; git 8d76f40 (17 Sep 2026, v5.5, sole commit with pack=0); git 9eb6678 (23 Oct, v8 coupling, groups.pack as before); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/mechanics-diagram.html:1162 (panel 5 step e lists groups pack N; belongs under step j); DF vanilla raws: LION 1:3 pop 5:10, HYENA 5:15, COYOTE 2:10, JACKAL 1:5, BOBCAT 1:1 pop 2:3

</details>

## F7

> What is "land natives OFF" and what does it do?

**Short answer.** Land natives are wild surface animals already on your map without DF's wave flag and outside any tracked group. The tool assumes they are DF's embark animals. The switch `groups.natives_land` (default off) is meant to decide whether the tool adopts them as groups that count against the land cap. Under season casts, which are on by default, the code adopts and counts them whatever the switch says (`gc.natives_land or cast`). So 'land natives OFF' has no effect in normal play, and the status line 'land natives not counted' is wrong. The behaviour fits your aims (only cast species on the map); the readouts need fixing.

*Status: verified · confidence high · review verdict: minor fixes*

### Short answer
**Land natives** are wild, natural surface animals on your map that:
- carry no DF wave flag, and
- belong to no group the tool tracks.

The tool assumes these are animals DF placed at embark. The switch `groups.natives_land` (default **off**, `scripts/seasonal-wildlife.lua:1018`) is meant to decide whether the tool takes them in as groups that count against the land cap.

**Under season casts the switch does nothing.** The deciding line in `V7.GRP.adoptNatives` (`:16886`) is:
`(L == 'land' and (gc.natives_land or cast)) or (L == 'water' and (gc.seeded_water or cast))`
where `cast = ROSTER.castOn(cfg)` (`:10375`). That is true once casts are built, which is the default for a new fort. The code says it outright (`:16873-16875`): "land natives whatever natives_land says (only cast species may be on the map)". It came in with v7.3 (64f9972, 7 Oct).

The same `or cast` overrides seeded water schools. Cavern natives have no override: `natives_cavern` really works.

### How an animal becomes a land native
`adoptNatives` runs every 1,200 ticks and on the first pass after a load.
- Flagged wave animals are skipped. Group discovery handles them as DF waves, except flagged water-feature fish under casts.
- A young animal whose mother is in a group joins her group.
- Everything else is filed by its population source (`WILD.layerOf` `:4378-4383`): a cave source makes a cavern native, a water-feature source a seeded school, **anything else a land native**. So under casts, an unflagged sea animal on an ocean fort is also filed as a land native.

**Caveat (DF side):** the 7 Oct probe listed only animals in the water. Whether DF's embark *land* animals carry the wave flag was never measured. If they do, they enter as DF waves instead, and count against the land cap either way.

### What adoption does
1. **It counts.** The group is marked `native, resident, layer='land'`. `ENGINE.count` counts every non-seeded land group (`:7515-7522`), and that count drives the land pause and the release clock.
   - A species in this season's *flying* cast is moved to the flying count by `flyGroups`.
   - Water-cast birds stay on land, because `waterBirdGroups` skips natives (`:15827`).
2. **It gets a leader**, like any herd.
3. **A resting species is sent off in the same pass.** `castTurnover` runs right after adoption (`:17357-17358`) and zeroes the leave countdowns (`dismissGroup`). A dismissed group is also never led and never panics (`cohere` `:13502`).
4. **Still there 7 days later, it is removed** and returned to its population (`leaveCheck` `:16833-16862`).

**Code fact:** a sent-off group holds its land slot until its last member is gone. `ENGINE.count` has no dismissed filter, and `reconcileGroups` drops a group only when it has no live members.

**Unmeasured (DF):** whether an unflagged native actually walks off when its countdown is zeroed (open risk in `docs/v7.1/groups.md:254-255`). If not, the 7-day removal clears it.

### Thought experiment (land cap 4, as on the B2 forts)
Suppose DF left an unflagged herd at embark.
- **Its species is cast this season:**
  - It is adopted at the first pass, and land goes to 1/4.
  - Unlike DF's waves, which stay about 7 days and leave, a native simply stays until the cast drops its species.
  - At 4/4 the land pause (on by default, `:1027`) closes the surface entries.
  - Inference: one species could hold a quarter of the land capacity all season. That matters only if embark natives are common. The B1/B2 end-of-run snapshots cannot tell, because natives of resting species were dismissed long before.
- **Its species is resting:** it is adopted and dismissed in the same pass. It holds a slot until it walks off, or for up to 7 days.
- **Switch ON:** identical.
- **Casts off:** the only case where the switch matters. Off, natives stay DF's: no group, no count, never sent off. On, they are adopted and counted.

### What is wrong today
The readouts report the stored switch, not what the code does:
- `status` prints "land natives not counted" (`:17247-17248`). That line is in 17 B1/B2 status and groups files, all from forts with casts on.
- `groups natives` prints "land not adopted" (`:24164-24165`).
- The diagram (panel 5, step g) shows "land natives OFF". Its "seeded water schools ON" is also overridden by casts.

### Does it serve your aims?
**The behaviour does; the readouts do not.** Adopting natives under casts keeps out-of-cast species off the map and leaves the tool in control. Making OFF really work under casts would reopen that leak, so do not.

### Recommendation (no change made)
1. Show the effective state ("land natives: adopted and counted, under season casts") in `status`, in `groups natives` and on the diagram. Do the same for seeded water schools.
2. Retire `natives_land`, or relabel it "applies only with season casts off".
3. **Optional, only if the rig shows natives are common:** give an in-cast native the same stay and turnover as a released wave.

### Rig test (not run)
On a fresh embark with casts on:
1. **Before the first groups pass:** list every wild unit whose source is not a cave or water feature, with its wave flag. This shows whether DF flags embark land animals, and how many there are.
2. **After the first pass:** read the ledger's 'adopt' and 'dismiss' lines.
3. **Follow one sent-off native:** does it walk off, or is it removed at day 7? Does the land row count it until then?
4. Run `groups natives land on`, reload, and repeat step 2. Expect identical results.

**Rig test that would settle it:** Fresh embark, casts on: (1) before the first groups pass, list every wild unit whose source is not a cave or water feature, with its wave flag (does DF flag embark land animals, and how many are there?); (2) after the first pass read the ledger adopt/dismiss lines; (3) follow one sent-off native: walks off, or removed by leaveCheck at day 7, and is it counted until then; (4) `groups natives land on`, reload, repeat (2); expect identical results.

<details><summary>Review and verification trail</summary>

- review: Evidence location corrected: the status line 'land natives not counted' is not in B2/master.log (0 hits there). It is in the per-fort status-start/status-end/groups-end.txt files: 20 files across B1 and B2, every one with casts on.
- review: Upgraded from inference to code fact: a dismissed group keeps its land slot until its last member is gone. ENGINE.count (:7515-7522) has no dismissed filter, and reconcileGroups (:5388-5403) only drops a group once it has no live members.
- review: Added a gap the first answer missed: the 7 Oct probe only looked at animals in the water (all 218 rows in the natives-*.tsv files are sw_layer=water). 'Embark land animals carry no wave flag' was never measured for land. If DF flags them the way it flags embark fish, discoverGroups (:5414) files them as a DF wave at the gate and counts them, and the switch never sees them.
- review: Added: under casts the 'or cast' also overrides seeded_water (:16886, the diagram shows ON for it), but not natives_cavern. Turning cavern natives off really does leave cavern natives to DF, even under casts.
- review: Added: a land native of a flying-cast species is moved to the flying count on the next pass, because V7.GRP.flyGroups does not exclude natives. A land native of a water-cast species stays on the land count, because waterBirdGroups excludes natives.
- review: Added: the land pause is on by default (land_pause=true, :1027), so a native that puts land over its cap is never trimmed. A native of a cast species never leaves on its own, so it holds its slot until the season turnover. Pacing cost: 1 of 4 land slots on the B2 forts (cap 4, map size).
- review: Added: groups.md open risk (:254-255) says it is unmeasured whether DF walks an embark native off when leave_countdown hits 0. The 1.2-day median at :16820 comes from groups that were sent off in general, not from natives. leaveCheck's 7-day removal is the backstop.
- review: Added: the control row 'Count surface natives' (controls.lua:166) is the only one of its neighbours with no help text.
- review: Wording: the eco report states 'land natives always adopted' as part of the land row, not as a known gap. Removed the '3x3-ish embark' claim, which nothing supports.
- review: Rig test sharpened: list the wave flag of every surface-source wild unit at load (the flag is the open question). Count natives through the ledger 'adopt' lines, not end-of-run land rows, because natives of resting species are dismissed in the same pass.

Code refs: /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:1018 (natives_cavern=true, natives_land=false, seeded_water=true); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:1027 (land_pause=true); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:4378-4383 (WILD.layerOf); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:5388-5403 (reconcileGroups keeps a group while any member lives); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:5414-5452 (discoverGroups: flagged surface units become DF waves); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:7515-7522 (ENGINE.count, no dismissed filter); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:3213 (ROSTER.managedKey); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:10339,10375 (CAST_DEF.enabled, ROSTER.castOn); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:13573-13582 (dismissGroup); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:16762-16811 (natives comment, V7.GRP.castTurnover); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:16833-16862 (V7.GRP.leaveCheck); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:16864-16927 (V7.GRP.adoptNatives; :16886 natives_land or cast); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua V7.GRP.flyGroups (natives re-filed to flying) and V7.GRP.waterBirdGroups (natives excluded); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:17247-17248 (status line from switch alone); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:17357-17359 (adopt, turnover, leaveCheck order); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:17391-17421 (nLand feeds land pause and release); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:24154-24165 (groups natives verb); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/internal/seasonal-wildlife/controls.lua:166; /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/docs/v7.1/groups.md:104-107,133,187,254-255; git 64f9972 (v7.3: land natives adopted under casts); git 7c45e53 (v7.1: switch introduced off); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/t1-season/natives.part.html and natives-*.tsv (water animals only); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/mechanics-diagram.html:1171 (panel 5 step g); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/B2/P2_SAVR/status-end.txt and groups-end.txt (status line; land cap 4)

</details>

# G. Surface gates: coupling and the bird pause

*rules that hold surface entries closed and whether they can starve arrivals*

### What these two questions are really asking
Both questions ask the same thing: **are the tool's surface gates working against what the tool is for?** Both the coupling hold and the bird pause work the same way: they set the extinct flag on DF's surface entries so DF's next wave goes where the tool wants. You are asking whether that steering ever:
- starves arrivals;
- crowds a body;
- lets DF, rather than the tool, decide who shows up.

Underneath that is the aim you set on 16 Nov: the tool should pace arrivals with its own draws, with fewer side effects across layers.

### What the code shows (checked for both answers)
- **The tool's own draws ignore every one of these flags** (`ENGINE.candidates` 7322, `ROSTER.placeGroup` 11595, `ROSTER.apex.entries` 11563). Neither rule can stop the tool's land, flying, water or apex draws, and neither touches the caverns. All they can do is hold back or let through **DF's** surface waves.
- **Each rule's side effects come from the same habit: closing broadly to steer narrowly.**
  - A land coupling call closes fliers' and water-cast species' entries too, for up to 2 days. It does so even when the predator can't come: the prey filled the land cap, the flying pause holds the predator, or the predator is already here by a draw or the apex scheduler.
  - The bird pause's 2-slot margin exists because opening entries invites DF overshoot.
- **One real gap sits under both.** The one-group-per-species rule stands down completely while the land pause is on (seasonal-wildlife.lua:16234). Since v8 the land pause no longer covers water-cast or flying entries, so the land is paused 80-95% of the time on these forts and nothing stops DF doubling a water-cast or flying species. That gap explains:
  - albatross x2 (coast);
  - giant dragonfly x2 (savage river);
  - giant fly x2 (lake, Spring 31-47, all under the land pause);
  - barn owl x2 (P2_COAST).

### Combined recommendation
1. **Fix the gap first (small, no new rule).** Keep the one-group-per-species rule closing water-cast and flying entries while the land pause holds, and re-run it right after each tool draw. That removes the doubles G2 is trying to fix, keeps the cap−2 margin, and adds no state.
2. **Move land coupling to \"next draw\", as water has done since 23/26 Oct.**
   - A prey arrival of any kind, DF's or the tool's, names the land's next draw from its predators.
   - Nothing is closed, and the call takes priority over a waiting DF wave.
   - Apex predators go to the apex scheduler (needs a new hook).
   - If you keep the hold for now, at minimum: no call when there's no free slot, leave out predators another pause holds, end the call when a predator is here by any route, and close only ground-cast entries.
3. **Don't adopt the cap−1 bird unpause as written.** If you want DF held to one per body, use the guarded form: n < cap, a DF group counts as present, re-close after each draw. Expect it to give the coast's albatross-heavy DF pick more time, and to leave a body the tool isn't filling with just one group.
4. **Longer term,** the \"tool decides\" end state is DF's surface entries for water-cast species closed for good, with the tool delivering them.
   - The coast is ready for that.
   - Fresh water isn't yet: five lake and river species have never been tool-drawn, and the lake took no draws all spring (frozen surface suspected).
   - Check those offline before any rig time.

**Rig work (not run, the rig is busy):**
- G1's two-arm coupling test, plus the engine check of whether a narrowed set of open entries makes DF skip waves.
- G2's four-arm bird test on the B2 saves after P2_LAKE finishes.
- Both measure species seen per layer per season alongside timing, so the diversity effect is visible, not just the pacing effect.

<details><summary>Cross-answer issues the verifier resolved</summary>

- Both answers depend on the same fact, checked in code: the tool's own draws ignore the extinct flag. ENGINE.candidates (seasonal-wildlife.lua:7322-7345) checks only `quantity > 0`. ROSTER.apex.entries (11563) and ROSTER.placeGroup (11595) never read flags.extinct. So neither the coupling hold nor the bird pause can starve the tool's land, flying, water or apex draws. Both rules only hold back DF's own surface waves. The two answers agree on this.
- Both describe the same interaction: coupleStart closes water-cast species' surface entries too, because it loops over every surfaceRows() row with layer 'land' or 'water' (5582-5606). G1 counts this as part of the hold's cost, and G2 lists it as a coupling-window edge case. They agree. Water-cast birds' DF waves are held during a land call even when their body has room.
- The same-species doubles in G2 and one double in G1 have different causes, so they must not be merged. G2's water doubles (lake giant fly x2 from Spring 31 to 47) and the P2_COAST barn owl double (tool draw Autumn 4, DF wave Autumn 5) both happened while the land pause was on. The cause is that V7.GRP.speciesPause returns at once under the land pause (16234). G1's P2_COAST opossum double happened with the land unpaused: it resumed at 2 of 4, then the tool drew at 3 of 4. Its cause is different. Most likely the pauses run before the land draw in the same pass (17410-17418 before 17436), so a just-drawn species' entry stays open for up to 300 ticks. Or DF had already picked that wave. This is inference.
- Same window, two layers. G2's '3-to-300-tick window' (entries reopen, then a tool draw fills the last slot after that pass's pauses) also applies to the land draw: the groups pass runs every pause before V7.DRAW.one. Both answers' fixes ('re-run the pause after each draw') apply to land and water alike.
- Line-number fix shared by both answers. The land-pause stand-down in speciesPause is at seasonal-wildlife.lua:16234, not ~16213. The coupling-window branch of speciesPause starts at about 16251. The code is as described.
- Page accuracy: mechanics-diagram.html says 'DF sends no water waves' in two places, line 397 and panel 5k at line 1181. Both are wrong for water-cast species, which arrive by DF surface waves and are filed into their body (V7.GRP.waterBirdGroups 15822-15841).

</details>

## G1

> What would happen if... instead of "Coupling ON: a prey group arriving on land calls its predators. Every other surface source is closed until one arrives, 2 days at most. Never while the land pause holds" the other surface sources weren't held closed? Is it possible that holding closed all other surface entries, slots or whatever could be accidentally holding closed everything from coming in cases where a prey group's predator cannot be found?

**Short answer.** If no predator is found, nothing is closed. If a predator is found but can't come (the prey filled the land cap, the flying pause holds it, or DF just doesn't send it), every DF surface wave, including fliers and water-cast birds, is held for up to 2 days. The tool's own draws and the caverns are never held. The better design is a land 'next draw' call like the water one: it closes nothing and fires on any prey arrival.

*Status: verified · confidence high · review verdict: minor fixes*

### Short answer
- **If no predator can be found, nothing is held closed.** `V7.GRP.coupleStart` returns before it closes anything if:
  - the prey has no cast predators this season (seasonal-wildlife.lua:5573);
  - every predator belongs to a water cast (5578);
  - no predator is in season, stocked on a surface entry and not already on the map (5590).
- **A predator is found but can't arrive.** Then yes: the hold can shut **every DF surface wave** for up to **2 days**. That includes the flying cast's waves and the water casts' birds and shore animals. It never holds the **tool's own draws** (land, flying, water, apex) or the **caverns**. It can't last longer than 2 days, and a new call needs a new DF prey wave.
- **You already fixed one form of this** on 26 Oct (option C, sw 9b2809f): a capybara closed 26 land entries for 2 days for a shark that could only come by water. Water-only predators now go to their body's next draw and close nothing (`V7.GRP.coupleWater` 5553). The same problem is still there in the forms below.
- **Just removing the hold** would leave coupling as roughly a 1-in-6 nudge. The better change is for land calls to work like the water ones: the predators become the land's **next draw**, nothing is closed, and the call fires on any prey arrival, not only DF's.

### 1. What the code does now (sw-wt v8.1-pacing @ 6dffef5)
**What starts a call** (groups pass, 17367-17390):
- A *fresh DF* land or flying group whose species has cast predators this season starts a call. It never starts while the land pause is on (17378).
- "Fresh" only comes from `discoverGroups` (5414-5452): units the tool hasn't seen yet.
- Groups the tool places itself (land/flying draws, apex) are known the moment they are placed. So **a drawn prey never calls its predators on land**.
- The water coupling does fire on the tool's own draws (the ledgers' 'coupling: X drawn; its predators ... are the next draw in this ocean').

**Who is called** (`couplePredators` 5533, `coupleStart` 5569). The prey's predators by this season's cast links and cross-layer links. Then:
- predators that only a water cast holds go to `coupleWater`;
- predators already on the map are dropped (`presentRaces`);
- predators with no stocked, wanted surface entry are dropped.

**The hold:**
- Every other open surface entry gets the extinct flag (5596-5605). Stock and FREQUENCY are not touched.
- That covers ground-cast entries, **flying-cast entries** (fliers are 'land' rows), water-cast species' surface entries, and the innumerable side entries (`surfaceRows` 15714).
- `coupleHold` (5626) re-closes anything that reopens, every pass, but does nothing while the land pause is on.
- **What ends it** (17369-17370): a *fresh DF group* of a called predator, or 2 days (`until_tick`). `endCoupling` (5704) reopens only what the call closed.

**What keeps running during the window:**
- The land draw tries the called predators first (`V7.DRAW.one` 15945-15947, `only` = called predators), then any ground member. It never draws an apex (`V7.DRAW.pick` 15919).
- `ROSTER.placeGroup`, `ROSTER.apex.entries` and the water candidates (`ENGINE.candidates` 7322) read stock, not the extinct flag. So all the tool's draws ignore the hold.

### 2. When the hold blocks with no predator coming
### 1. The prey fills the land cap (the common case)
- `nLand` is counted after the prey joins (17391). `landPause` runs later in the same pass (17412) and closes every entry still open, which by then are only the predators'. The tool's land draw needs `nLand < cap`, so the call is dead from the start.
- **It is not harmless.** The land pause leaves fliers and water-cast species alone (15766-15767). The flying and bird pauses only act at their own caps. So the coupling alone keeps *their* DF entries shut for the 2 days.
- P2_COAST, Autumn 3: opossum calls BEAR_BLACK, TIGER, WOLF. The ledger then shows "land at its cap (4 of 4 groups): paused, 3 entries closed". On Autumn 5 it shows "restored 14 entries (timed out)", and in the same day a DF BIRD_OWL_GREAT_HORNED and a DF BIRD_OWL_BARN flying wave arrived.
- The kakapo call and the second opossum call went the same way. In PC_COAST the panda call (BEAR_BLACK, TIGER) also timed out.
- The land reopens only at cap − 2 (`resumeAt` 15673, pause_margin 2), so two groups must leave first.

### 2. A flying-cast predator while the flying pause is on
- `coupleStart` opens its entry. Then `flyPause` (16075, run after the land pause at 17414) closes it again. `coupleHold` doesn't reopen predators.
- The land draw can't place it either: it draws only from the ground cast (`V7.DRAW.members`).
- Result: every DF surface source is shut for 2 days. **Found in the code; not seen in the ledgers.**

### 3. The predator's entry is open, but DF doesn't send it within 2 days
- PC_COAST, Summer 64-66: red panda calls BEAR_GRIZZLY with land at 3 of 4. No land wave came in 2 days. After the restore, a turkey wave and then a bobcat came the same day.
- (c) DF probably had waves to give that the hold held back.
- Not measured: whether DF stretches its wave timer when only one or two entries are open (possibly on a low-weight neighbour tile; see your note on DF's per-entry pick).
- E10 (comment 5513-5518) saw the predator wave 298-430 ticks later in 5 of 5 tries, on CTRL.

### 4. The predator is already here, but the window keeps running
- The end test reads fresh DF groups only.
- P2_COAST: the apex scheduler placed BEAR_BLACK on Autumn 4 inside the opossum window, and the hold still ran to its timeout on Autumn 5.
- The same happens when the coupling's own preferred land draw places the predator.

**Leaks inside windows** (same P2_COAST stretch):
- **Opossum, Autumn 2-3:** the tool drew an opossum at 3 of 4 with the land unpaused, and a DF opossum wave came the next day, which started the call. The cause is not established. Most likely (inference) the pauses run *before* the land draw in the same pass (17410-17418 before 17436), so a just-drawn species' entry stays open for up to 300 ticks.
- **Barn owl, Autumn 4-5:** the tool drew a BIRD_OWL_BARN on Autumn 4 and a DF barn owl wave arrived on Autumn 5. This was under the land pause, where the one-group-per-species rule stands down (16234). See G2.

**Scorecard** (ledgers B1 PC_COAST/PC_SAVR, B2 P2_COAST/P2_EVIL/P2_SAVR; I recounted these):
- 14 land calls in all.
- 9 ended with the predator arriving, mostly the same or the next day.
- 5 timed out: 4 cap cases and 1 genuine 2-day block (the grizzly).
- These are ledger excerpts (~300 lines per fort), not whole runs.

### 3. If the other entries simply weren't closed: Fort 1 (savage marsh), autumn ground cast
**Ladder** (stored values, SAVR_d1 via summarise.py): ARTHROPLEURA 100, ADDER 23, WEASEL 23, WILD_BOAR 12, DINGO_MAN 7, GIANT_BARK_SCORPION 5 (apex), PARASAUROLOPHUS 4, TRICERATOPS 2.

**The real event** (P2_SAVR, Autumn 1): ARTHROPLEURA arrives and calls DINGO_MAN and GIANT_BARK_SCORPION.

**With no hold:**
- The one-group-per-species rule closes ARTHROPLEURA, leaving 76 FREQUENCY open.
- The two predators then hold 12/76, about **16%** of the odds on DF's next surface wave.
- That is a rough figure. DF's pick also weighs tiles per entry, and open fliers and water-cast entries dilute it further.
- So it takes about six DF waves for one predator. In play DF sends a surface wave every 4-15 days (comment 15871-15874), so the land cap would usually fill first.

**With the hold:** DINGO_MAN x9 came the next day ("restored 10 entries (predators arrived)", Autumn 2).

**In play,** where DF's waves are slow, a 2-day hold mostly times out with no DF wave at all. It costs little and achieves little. The predator then comes only if the land draw's preference fires inside the 2 days.

### 4. Does dropping the hold serve what you want?
**Your aims:** predators following prey (ecology), arrivals paced by the tool rather than by DF (your 16 Nov point), fewer hacks.

**The hold works against those aims:**
- It shuts all of DF's surface supply to steer one wave.
- It cuts across the flying and water layers.
- It misses every prey the tool draws itself.

**Dropping it alone isn't enough:** coupling becomes roughly a 1-in-6 nudge.

**Better: land coupling as "next draw", as water has done since 23 Oct (b3fb66e) and 26 Oct (9b2809f):**
- Record the call (predators, season, prey) and close nothing.
- **Fire it on any prey arrival**, a DF wave or a tool draw.
- The land's next draw comes from the called predators. `V7.DRAW.one` already takes `only` and falls back to any member.
- Give the call priority over a DF wave waiting at the gate. Today `detachOldest` (17422) runs before the draw (17436), so a waiting wave beats the predator.
- Hand an apex predator to the apex scheduler. That needs new code; there is no hook today.
- If the prey filled the cap, keep the call until a slot opens, or drop it at the season change.
- **Cost:** the predator comes when the release clock is next due, not within a day. It stays inside the cap and the clock.
- **Evidence it works:** on water, Boardhelms 23 Oct, 20 of 34 calls hit, 13 fell back and 1 was dropped at the season change.

**If you keep the hold, the minimum fixes are:**
- no call when the prey's arrival leaves no free slot;
- leave out predators another pause is holding (the flying pause);
- end the window when a called predator is here by any route (draw, apex, DF);
- close only ground-cast entries, and leave the flying cast and water-cast species open.

**History:** coupling went off with all nudges on 16 Oct and was unparked at your request on 23 Oct ("Unpark it and finish"). Option C on 26 Oct already treated this exact symptom for water predators.

### 5. What only the rig can settle
**Test design:** two arms, the current hold vs. the next-draw version (any prey arrival, nothing closed). Run them on breached region9-class forts with 50 dwarves, n=5 per arm, one in-season year each.

**Measure:**
- time from prey arrival to predator arrival;
- DF surface waves per day inside vs. outside call windows;
- flying and water-cast arrivals during windows;
- species seen per layer per season;
- the share of calls ending 'predators arrived' vs. 'timed out'.

**Engine check:** with every surface entry flagged extinct except one predator entry (site tile vs. neighbour tile), does DF's surface wave interval lengthen compared with all entries open?

**Rig test that would settle it:** Two arms: the current hold vs. a land next-draw coupling that closes nothing, fires on any prey arrival (DF or drawn) and takes priority over a waiting DF wave. n=5 per arm, one in-season year each, on breached region9-class forts with 50 dwarves. Measure: time from prey to predator arrival; DF surface waves per day inside vs. outside call windows; flying and water-cast arrivals during windows; species seen per layer per season; share of calls ending 'predators arrived' vs. 'timed out'. Engine check: with every surface entry flagged extinct except one predator entry (site tile vs. neighbour tile), does DF's surface wave interval lengthen compared with all entries open?

<details><summary>Review and verification trail</summary>

- review: Corrected the cap case. The draft said 'arrivals didn't lose much because the land pause would have held everything anyway'. That is wrong for the flying cast and the water casts' birds and shore animals. coupleStart (seasonal-wildlife.lua:5599-5605) closes every open surface row: flying-cast entries are layer 'land' rows (layerOf at 1679, so they are in managedPops at 3638). landPause skips fliers and water-cast birds (15766-15767: flyRace/birdBody). So in a 'dead' window the coupling alone keeps the flying cast's and water birds' DF entries shut for 2 days. Ledger: in P2_COAST, flying was at 3 of 4 (not paused) on Autumn 4. The window timed out on Autumn 5 ('restored 14 entries') while the land pause had recorded only 3, and a BIRD_OWL_GREAT_HORNED flying wave arrived the same day.
- review: Corrected the land-resume claim. It needs the count to fall to cap minus pause_margin (V7.GRP.resumeAt 15673, pause_margin=2 at 1038). On a cap of 4 that is 2 of 4, so two groups have to leave, not one.
- review: Cut the unsupported 'about 6 days at the rig's pace'. In the B1/B2 ledger tails, DF surface waves came about once every 2.5-3 days on average, pauses included (PC_COAST 20 in ~48 days; P2_COAST 11 in ~30; P2_SAVR 9 in ~29). Without the hold, the land cap would usually fill before six waves come.
- review: Fixed a misused citation. E11 (comment at 5517-5518) says coupled predators do NOT hunt. Hunting comes from the ecology relation write (any non-BENIGN attacker, per memory relation-write-needs-large-predator) and from the T-run addenda in STATE.md (~1380-1414), not from coupling.
- review: Added a gap the draft missed. The land call fires only on DF waves: the trigger loops over `fresh`, which only discoverGroups fills (17376-17378, 5414-5452). The tool's own land draws (V7.DRAW.one appends straight to g.groups, 15950-15960) never call predators. In B2 P2_COAST and P2_SAVR, about half of surface arrivals were tool draws (9 of 20 and 9 of 18). The water coupling, by contrast, fires on draws (7492-7511).
- review: Added: a predator that the coupling's own preferred land draw places (V7.DRAW.one with `only`, 15945-15947) does not end the window. The end test reads fresh DF groups only (17369-17370), the same as the apex case.
- review: Added the history. The user switched coupling off with all nudges on 16 Oct (beta-rulings-oct16) and unparked it on 23 Oct (9eb6678). On 26 Oct option C (9b2809f) fixed exactly one instance of this question: a capybara closed 26 land entries for 2 days for a shark that could not come by land. The remaining cases are the same problem in other forms.
- review: Added the play-pace consequence. In play DF sends a surface wave every 4-15 days (comment at 15871-15874), so the 2-day hold mostly times out with no DF wave at all. Its cost in play is small, and so is its benefit.
- review: Qualified the 16% figure. The autumn values are the ladder's stored values; the SAVR_d1 dump is from spring, and its 'live' column shows raw defaults for out-of-season species. The share rises if other cast species already have a group here (the one-group-per-species rule closes them) and falls with flying-cast and water-bird entries. Kept it as an illustration only.
- review: Added evidence that a next-draw design works. Water next-draw coupling on Boardhelms, 23 Oct: 20 of 34 calls hit, 13 fell back to another member, 1 was dropped at the season change (memory experiment-readout-traps #45).
- review: Added design caveats for the next-draw version. A DF wave waiting at the gate is released before any tool draw (detachOldest at 17422 comes before V7.DRAW at 17436), so a call needs priority. The release clock sets the delay (water: 2-9 days, comment at 7502-7504). The apex scheduler has no hook to take a call (needs new code).
- review: Verified the scorecard from the ledger tails: 14 land calls; 9 predators arrived; 5 timed out (4 cap cases: PC_COAST panda, P2_COAST opossum/kakapo/opossum; 1 open window: the grizzly). Added that in 7 of the 9 successes the predator's arrival filled the land cap at once.
- review: Noted a side leak. P2_COAST's dead opossum call was triggered by a second opossum group: the DF wave came the day after the tool drew one, despite the one-group-per-species rule.
- verifier: speciesPause's land-pause stand-down is at seasonal-wildlife.lua:16234. Its coupling branch starts at about 16251, not 16258.
- verifier: The P2_COAST opossum double was not the land-pause gap: the land had resumed at 2 of 4 and the opossum was drawn at 3 of 4. The cause is not established. Most likely the pauses run before the land draw in the same pass, which leaves the drawn species' entry open for up to 300 ticks (inference).
- verifier: Added a second leak in the same window: in P2_COAST the tool drew BIRD_OWL_BARN (flying) on Autumn 4 inside the opossum call, and a DF BIRD_OWL_BARN wave also arrived on Autumn 5. That one happened under the land pause, so it is the speciesPause gap (see G2).
- verifier: On the pass where a call starts or ends, `landBlocked` (17392) also skips the tool's land draw for that one pass. This is a small extra cost the reviewed answer didn't list.

Code refs: /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:5513-5532 (coupling header: E10 5/5, E11 co-presence only, v8 design); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:5533 V7.GRP.couplePredators; /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:5553 V7.GRP.coupleWater (option C: next draw, closes nothing); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:5569-5624 V7.GRP.coupleStart (nil returns 5570/5573/5578/5590; closes all other surface rows 5599-5605); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:5626-5645 V7.GRP.coupleHold (no-op under land pause); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:5701-5724 endCoupling (v8 branch); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:5414-5452 discoverGroups (only DF units are fresh); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:1679,3638 layerOf / CACHE.managedPops (fliers are 'land' rows); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:15673 V7.GRP.resumeAt (cap - pause_margin); 1038 pause_margin=2; /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:15714 V7.GRP.surfaceRows; /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:15735-15790 V7.GRP.landPause (skips fliers and water birds at 15766-15767); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:15871-15884 V7.DRAW header (DF surface wave every 4-15 days in play); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:15908-15947 V7.DRAW.pick / V7.DRAW.one (apex excluded; `only` = called predators, fallback); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:16075-16120 V7.GRP.flyPause; /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:16258-16272 V7.GRP.speciesPause exclusion branch (spares called predators); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:7322-7345 ENGINE.candidates (stock, not extinct flag); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:7492-7511 water coupling fires on the tool's own water draws; /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:11563 ROSTER.apex.entries; 11595 ROSTER.placeGroup (no extinct check); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:12187-12205 water draw honours the per-body coupling table, falls back; /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:17367-17392 groups pass: end test (fresh DF only), coupleHold, trigger on fresh only, nLand after prey, landBlocked; /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:17410-17418 pause order: bird, land, flying, species; /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:17420-17447 detachOldest before V7.DRAW.one (a waiting DF wave beats the draw); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:1009,1316-1318 coupling default on; coupling_v8 unpark; sw-wt git 9eb6678 (coupling unparked 23 Oct), b3fb66e (water coupling per body, next draw), 9b2809f (option C, capybara/shark 26 entries), 8fc1c32 (flying counts on its own), 6b74260 (land pause); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/B1/PC_COAST/ledger.txt:54-77 (red panda -> BEAR_GRIZZLY timeout with room), 262-293 (panda dead window); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/B2/P2_COAST/ledger.txt:138-262 (three dead windows; apex BEAR_BLACK placed inside one; flying wave right after restore); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/B2/P2_SAVR/ledger.txt:137-149 (ARTHROPLEURA -> DINGO_MAN x9 next day); /Users/nathanielcannon/Claude/Projects/DwarfCron/.claude/scratch/pacing/ladder/SAVR_d1.json via summarise.py (land ladder stored values); memory: beta-rulings-oct16.md (coupling off as a nudge), experiment-readout-traps.md #45 (water next-draw 20/34 hits), df-wave-pick-per-entry.md, relation-write-needs-large-predator.md

</details>

## G2

> What would happen if... instead of "bird pause: at the body's cap, its water-cast birds' surface entries are closed, reopening at cap - 2" we changed it to be "bird unpause: if the body's group count reaches cap-1 AND no water-cast bird group is already present. Water-cast birds' surface entries are closed again if any water-cast bird group is present."

**Short answer.** Your rule (with a cap guard, and 'present' meaning a group DF sent) would hold DF to about one water-cast group per body and stop same-species doubles. But reopening at cap-1 brings back the overshoot that the 2-slot margin was added to stop. It hands the coast's albatross-heavy DF pick more time, and on a body the tool isn't filling (the lake in spring) it leaves just one group. The cheaper, cleaner fix: let the one-group-per-species rule keep closing water-cast and flying entries while the land pause holds. Today it stands down entirely (16234), which is where the doubles come from.

*Status: corrected · confidence medium · review verdict: major fixes*

### Short answer
Your rule would hold DF's own water-cast waves to about **one group per water body** and let them back in one slot sooner (at cap−1 instead of cap−2).

**What it fixes.** DF has been putting two groups of the same species in one body: albatross x2 in the ocean, giant dragonfly x2 in the savage river, giant fly x2 in the lake. The one-group-per-species rule should stop that, but it switches off while the land pause holds, which is most of the time.

**Three problems as written:**
1. Nothing closes the entries at the cap.
2. Read literally, "water-cast bird" covers every fish too, so it would block almost always.
3. Reopening at cap−1 brings back the overshoot that the 2-slot margin was added to stop.

**The cheaper fix:** close the gap in the one-group-per-species rule (section 8).

Labels: (a) = what the code does, (b) = what DF or the rig shows, (c) = my inference.

### 1. How it works now (a)
**Who counts as a "water-cast bird":**
- `V7.GRP.waterBirds` (seasonal-wildlife.lua:15800) returns this season's ocean-cast and fresh-cast species that are on neither the ground nor the flying cast.
- Since v8 option A (your call, 23 Oct) that means **any habitat**: albatross, osprey, crab, bluefish, giant capybara, giant fly, fly man, giant dragonfly, giant loon, and every fish.
- Ocean-cast species belong to the ocean. Every fresh-cast species belongs to **one** body, `cfg.casts.sub`. On the lake fort that body is the lake, so the river and the ponds never get a DF group.

**How a DF wave is filed:**
- `V7.GRP.waterBirdGroups` (15822-15841) turns a DF wave of such a species into a water group of that body (`grp.wbird = true`).
- The group counts toward that body's cap.
- It is released at once: its roaming flags are cleared, so it never holds DF's surface gate shut.

**The bird pause** (`V7.GRP.birdPause` 16145-16195):
- `n` = the body's water groups, not counting seeded schools. That is the tool's draws plus DF's filed waves.
- **Closing:** at n ≥ cap it sets the extinct flag on those species' surface entries. Stock and FREQUENCY are untouched.
- **Reopening:** at n ≤ cap − pause_margin (`resumeAt` 15673; margin 2, never below 0).
- **Why the margin is 2** (config comment 1036-1038, 13 Oct): "opening every entry at once let DF send two waves within a day (land 4 -> 6 of 5 ...)".
- It works only while the land-pause switch is on (16148: `birds = {}` otherwise).

**The cap** is ⌊√(embark size in 48-tile blocks)⌋ + 1 (`QUOTA.autoGroups` 4441, `QUOTA.groupsFor` 4460). Every water body gets the same cap: on the lake fort the lake, the river and the ponds each have 8 slots.

**The tool's water draw ignores the flag.** `ENGINE.candidates` (7322-7345) checks only `quantity > 0`, never `flags.extinct`. So the bird pause holds back DF only. Example: the B1 coast's ocean paused on Summer 70, and the tool drew an osprey on Summer 72.

**Timing:**
- The groups pass runs every 300 ticks (`GROUPS_CADENCE` 5152).
- The water draw runs 3 ticks later as its own step (`V7.PASS.waterLater` 17262).
- Pause order in each pass: bird, land, flying, one-per-species (17410-17417).

**The gap.** `V7.GRP.speciesPause` returns at once while the land is paused (16234). Its comment still says "the land pause holds every surface entry", but since v7.6.1 and v8 the land pause skips water-cast and flying entries (15766-15767). So **while the land is paused, nothing stops a second DF group of the same water-cast or flying species** until the body or the flying layer reaches its cap. (a)

The rig shows it (b). Land was paused in 80% of snapshots on B1 coast, 95% on B2 coast and 94% on B2 savage. Same-species DF doubles:
- B1 coast: 14 of 14 body-snapshots with 2+ DF groups were albatross x2. That run was before P12, so some were a wave's tail.
- B2 savage river: 5 of 5 were giant dragonfly x2.
- B2 lake: giant fly x2 from Spring 31 to 47, with the land paused at every one of those snapshots.
- Same gap, flying: P2_COAST barn owl, a tool draw on Autumn 4 then a DF wave on Autumn 5, under the land pause.

### 2. What the rig shows (b)
From probe.jsonl, one snapshot every 2 days. I re-ran the tally script `DwarfCron/.claude/scratch/sw-questions/G2/occ.py`.

| fort, body | cap | mean groups | mean DF groups | DF = 0 | DF ≥ 2 | over cap |
|---|---|---|---|---|---|---|
| B1 coast, ocean | 4 | 3.67 | 0.68 | 48% | 16% | 2% |
| B2 coast, ocean | 4 | 3.73 | 0.66 | 48% | 13% | 1% |
| B1 savage, river | 4 | 3.61 | 0.44 | 59% | 2% | 0% |
| B2 savage, river | 4 | 3.71 | 0.60 | 46% | 6% | 0% |
| B2 lake, lake (run in progress) | 8 | 4.60 | 1.92 | 0% | 71% | 0% |

**The lake in spring:**
- The tool drew **nothing** into the lake all spring. Every lake group was a DF group (1-3: giant fly, fly man).
- Meanwhile, from about Spring 31, the tool filled the river and the ponds to 8 of 8.
- The fort started with "water: dormant -- no open water on the surface" (status-start.txt:18). (c) A frozen lake is the leading suspect, but this is not established.

**The lake in summer:** the tool's draws filled the lake to 8 of 8. DF held 2-4 groups early in the season (fly man, giant fly, giant capybara, giant loon), then 1-2.

**How fast DF refills after a reopen.** Few cases, so treat these as examples:
- Coast, same day both times. Summer 70: resumed at 2 of 4, the tool drew a stingray, then a DF osprey made 4 of 4. Autumn 8: albatross x6, then a tail x2 made **5 of 4**.
- Savage river: 4-6 days.

**Which species came only by DF wave.** The tool never drew giant fly, fly man, giant loon or giant capybara on the lake fort, or giant dragonfly or giant capybara on the savage fort. On the coast it did draw albatross, osprey, crab and bluefish.

**Who DF picks on the coast.** Albatross won 7 of 9 DF ocean waves on B1, despite FREQUENCY 5 against crab 17 and osprey 9. (c) It probably has more or bigger open entries, in line with your note that DF's odds per entry are FREQUENCY x tile weight. Not checked.

### 3. Your rule, read closely
- **"Present" has to mean a group DF sent** (`grp.wbird` of that body). Read as "any water-cast group", it would hold the entries shut almost always: the coast ocean never held 0 groups in 85 snapshots.
- **Add "and under the cap".** As worded, the only reason to close is "a DF group is present". When the tool's draws fill a body, the entries would stay open and DF's next wave would make cap+1. The coast sat at (4 groups, 0 DF) in 23-34% of snapshots.
- **Reopening at cap−1 brings back the overshoot**, two ways:
  1. The entries open at cap−1. Three ticks later the tool's draw takes the last slot, and the entries stay open until the next pass (up to 300 ticks).
  2. Two DF waves land in one pass. On B1 savage, Autumn 7, giant capybara x3 and x6 arrived in the same pass.
- Today's rule has the same window, but only once, on the way up through cap−1. Yours opens it at every departure from the cap. P12 merges a wave's tail into it; it does not merge two separate waves.

### 4. Thought experiments
**Coast, cap 4:**
- Most departures are the tool's short-stay groups, so the body drops from 4 to 3 often. With no DF group present, each drop reopens the entries, and DF refilled the same day both times we saw it.
- (c) DF's share likely rises toward one slot almost all the time, and that slot is mostly albatross.
- So it ends the albatross doubles, but it does not cut DF's uncontrolled share or help diversity.

**Lake, cap 8:**
- Summer: DF is held to 1, so the tool gets up to 3 slots back early in summer and about 1 later.
- Spring, with no tool draws: DF's giant fly and fly man were the lake's only animals. Your rule cuts the lake to 1 group, which loses life rather than removing a hog.

**Savage river, cap 4:** little changes. DF had 2+ groups only 2-6% of the time, and those were dragonfly doubles. DF refills slowly here, so the tool usually takes the cap−1 slot first.

### 5. Can it starve arrivals?
- **Bodies the tool keeps filling (ocean, river, ponds): no.** The tool's draw ignores the flag.
- **A body the tool isn't filling: yes, down to one group.** That covers a frozen or dormant body, one with no species that fit, or a body whose cast species only DF delivers. The lake in spring is that case.
- **Land:** (c) the water-cast entries would be open more often, so they compete more with land entries in DF's pick. That only matters while the land is unpaused: 5-20% of the time on these forts, more on the lake fort.

### 6. Edge cases
- **Cap 2 (1x1 embark):** your rule reopens at 1, so a DF group can hold half the body. Today's rule reopens at 0.
- **Land-pause switch off:** the bird pause does nothing (16148), so DF's water-cast waves are unlimited. Your rule inherits that unless it gets its own switch.
- **Several fresh bodies:** "one per body" is really "one per fresh cast", because every fresh-cast DF wave is filed to `casts.sub`.
- **Season change:** "present" must be read from the group's own record (`grp.wbird`, `grp.body`), not this season's cast list.
- **Coupling window:** a land call (`coupleStart` 5569) closes these entries too, whatever the body's count (see G1).
- **Your page** says "DF sends no water waves" at mechanics-diagram.html:397 and in panel 5k (1181). That is wrong for water-cast species, which arrive by DF's surface waves and are counted in their body.

### 7. Does it serve your aims?
Partly.
- **It serves** "DF shouldn't crowd a body or double up".
- **It cuts against** "the tool controls outcomes" on the coast, because it hands DF's albatross-heavy pick more time.
- **It cuts diversity** where DF is the only source (the lake in spring).
- **It reopens the overshoot** that 13 Oct's margin closed.

### 8. Recommendation
1. **Cheapest fix (closes a gap, adds no new rule).** Let the one-group-per-species rule keep closing **water-cast and flying** entries while the land pause holds. Today it stands down entirely (16234), although the land pause no longer covers those entries.
   - This alone ends the albatross, dragonfly, giant fly and barn owl doubles.
   - It keeps the cap−2 margin and adds no state.
   - Re-run it straight after each tool draw (land, flying and water). That closes the window where a just-drawn species' entry stays open.
2. **If you still want DF held to one per body,** use this form:
   - open only if n ≤ cap−1 **and** n < cap **and** no `grp.wbird` group of that body is present;
   - re-run that body's pause straight after each tool draw;
   - keep the same switch.
   - Two waves landing in one pass can still make cap+1.
3. **Closing these entries for good, with the tool delivering everything,** is the most "tool decides" option.
   - It already works on the coast: albatross, osprey, crab and bluefish are all tool-drawn there.
   - **Not yet on fresh water:** giant fly, fly man, giant loon, giant capybara and giant dragonfly were never tool-drawn. First check offline why (`MODEL.entry(...,'water')`, `V7.WB.fitting` 8378-8395, `castBodies` 7664).
   - Also find out why the lake took no draws all spring.

### 9. Rig test that would settle it (not run)
**Setup:** after P2_LAKE finishes, use the B2 saves P2_COAST, P2_LAKE (start in spring and again in summer) and P2_SAVR. Two seasons each, n=5 short reps per arm. Four arms:
1. Current rule.
2. Current rule + one-per-species kept on for water-cast and flying entries during the land pause, re-run after each draw.
3. Your rule with the cap guard, DF-only "present" and a re-close after each draw.
4. Entries closed for good. Run this only if the offline check shows the fresh-cast DF-only species can be placed.

**Measure, per body:**
- mean DF groups;
- % of time with DF ≥ 2, and with the same species twice;
- snapshots over the cap;
- effective species and the top species' share;
- days at 0 groups;
- the tool's draws per season.

**Also measure:** land DF waves while the land is unpaused.

**Rig test that would settle it:** After P2_LAKE finishes: on the B2 saves P2_COAST, P2_LAKE (spring start and summer start) and P2_SAVR, run two seasons each with n=5 short reps per arm. Arms: (1) the current bird pause; (2) the current rule plus the one-group-per-species rule kept on for water-cast and flying entries while the land is paused, re-run after each tool draw; (3) the proposed rule with an n<cap guard, 'present' = a grp.wbird group of the body, and a re-close after each tool draw; (4) water-cast entries closed for good, run only if an offline check shows the tool can place giant fly, fly man, giant loon, giant capybara and giant dragonfly. Per body measure: mean DF groups; % of time with DF >= 2 and with the same species twice; snapshots over the cap; effective species and the top species' share; days at 0 groups; the tool's draws per season. Also measure land DF waves while the land is unpaused. Separately, find out why the lake took no tool draws all spring (frozen surface suspected).

<details><summary>Review and verification trail</summary>

- review: WRONG CLAIM REMOVED: the draft said the one-group-per-species pause already stops two albatross groups at once. V7.GRP.speciesPause (seasonal-wildlife.lua:16212-16215) does nothing while the land pause holds ('if V7.GRP.landPaused() then return 0'), and on these forts the land pause held 80-95% of snapshots (B1 coast 68/85, B2 coast 81/85, B2 savage 80/85). The rig shows same-species DF doubles: B1 coast 14 of 14 body-snapshots with 2+ DF groups were albatross x2; B2 savage river 5 of 5 were giant dragonfly x2; B2 lake 9 of 46 were giant fly x2. Your rule closes that gap for water-cast species, and the draft missed this point in its favour.
- review: LAKE NUMBERS CORRECTED: P2_LAKE is the run in progress (probe.jsonl still growing at 15:37, checkpoint 56/84), so the draft's 4.19 / 2.03 / 79% are already stale. They now read 4.44 / 1.97 / 74% from 63 snapshots covering spring and summer only.
- review: LAKE SPRING FINDING ADDED: through all of spring the tool drew nothing into the lake. The (groups, DF groups) states were (1,1), (2,2) and (3,3) in 54% of snapshots, so DF's giant fly and fly man waves were the lake's only animals. The fort started with 'water: dormant -- no open water on the surface' (status-start.txt:18), and the cause of the empty spring is not established. Under your rule the lake would hold 1 group in spring. Under the draft's 'close for good' it would hold 0. The draft's 'no water body starves' and 'the tool gains a slot on the lake' are true only once the lake is at its cap (summer).
- review: SPECIES CHECK CORRECTED: meganeura man IS drawn by the tool (savage river, 2 and 4 draws), so it is not at risk. Giant loon and giant capybara were never tool-drawn on any fort and were missing from the draft's list. Never tool-drawn: giant fly, fly man, giant loon, giant capybara (lake) and giant dragonfly, giant capybara (savage). That is 4 of the lake's 8 species. On the coast, albatross, osprey, crab and bluefish are all tool-drawn.
- review: LITERAL-READING TRAP ADDED: in the code a 'water-cast bird' (V7.GRP.waterBirds :15800, v8 option A) is ANY water-cast species not on the ground or flying cast. That includes every fish the tool draws. Read literally, 'no water-cast bird group present' is almost never true, since the coast never had an ocean with 0 groups in 85 snapshots, so the rule would amount to closing the entries for good. 'Present' has to mean a group DF sent (grp.wbird).
- review: Coast estimate softened: the draft's ~0.9 DF slots rested on 2 observed refills. The direction (more DF time, not less) stands; the number does not.
- review: Cap formula clarified: floor(sqrt(EMBARK tiles))+1 (QUOTA.autoGroups :4441), the same for every body. A pond gets the same 8 slots as the lake on that fort; it is not sized by the body's own tiles.
- review: Added a second overshoot path: two DF waves landing inside one 300-tick pass (B1 savage: giant capybara x3 then x6 on Autumn 7). This is what pause_margin=2 absorbs, and at cap-1 it means cap+1.
- review: Added the engine context (b): DF's surface gate is per source. Water-cast DF groups are released at once (waterBirdGroups :15822-15841, the roaming flags cleared), so they never hold DF's gate shut.
- review: Flagged that mechanics-diagram.html panel 5k says 'DF sends no water waves; every water arrival is this draw'. That is not true for water-cast species, which arrive by DF's surface waves and are filed as water groups.
- review: Rig test revised: added a cheap arm (the species pause applied to water-cast entries during the land pause). Made the 'close for good' arm conditional on an offline placement check. Noted that P2_LAKE must finish first.
- verifier: speciesPause's stand-down under the land pause is at seasonal-wildlife.lua:16234 (`if V7.GRP.landPaused() then return 0`), not about 16213.
- verifier: Lake figures updated as the run moves on: lake mean 4.60 groups, 1.92 DF groups, DF >= 2 in 71% of snapshots (was 4.44 / 1.97 / 74%).
- verifier: Summer on the lake: DF held 2-4 groups early in summer (fly man, giant fly, giant capybara, giant loon), then 1-2. It was not 1-2 throughout. So the proposed rule frees up to 3 lake slots for the tool early in summer, not about 1.
- verifier: Stronger evidence for the gap: the lake's giant fly x2 (Spring 31-47) happened entirely while the land pause was on (probe land pause=True at every one of those snapshots), as the gap predicts.
- verifier: The P2_COAST barn owl double (tool draw Autumn 4, DF wave Autumn 5 under the land pause) is another case of the same gap, this time for a flying-cast species.
- verifier: Why the lake took no tool draws all spring: the leading suspect is a frozen lake surface. status-start says 'water: dormant -- no open water on the surface' at Spring 15, while the river and ponds filled from about Spring 31. Still inference; not established.
- verifier: The page's 'DF sends no water waves' also appears at mechanics-diagram.html:397, not only in panel 5k (1181).

Code refs: /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:16145-16195 (V7.GRP.birdPause; 16149 birds={} when the land-pause switch is off); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:16196-16215 (V7.GRP.speciesPause header; returns 0 while V7.GRP.landPaused()); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:15784-15841 (v7.6.1/v8-A comment, V7.GRP.waterBirds any habitat, birdBody, waterBirdGroups: wbird, released at once); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:15673 (V7.GRP.resumeAt = max(0, cap - pause_margin)); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:1036-1038 (pause_margin=2 rationale, 13 Oct); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:15640-15651, 15735-15783 (land pause: per-source DF surface gate; excludes water-cast and flying entries); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:17410-17417 (pause order bird, land, flying, species); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:7322-7365 (ENGINE.candidates: quantity>0, no extinct check; castBodies/WB.fitting); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:7650-7670 (castWaterKeys, castBodies); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:8378-8395 (V7.WB.fitting, pond mass limit); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:4437-4471 (QUOTA.autoGroups floor(sqrt(embark tiles))+1, QUOTA.groupsFor); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:5152 (GROUPS_CADENCE 300), 17255-17270 (V7.PASS GAP 3, waterLater); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:5405-5420 (P12 JOIN_TICKS: a wave's tail joins it); /Users/nathanielcannon/Claude/Projects/sw-wt/plugin/scripts/seasonal-wildlife.lua:5569-5645 (coupleStart / coupleHold); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/B1/PC_COAST/ledger.txt:85-90, 233-241 (resume at 2 -> tool draw -> DF osprey; albatross x6 + x2 = 5 of 4); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/B1/PC_SAVR/ledger.txt:111-196 (giant capybara x3 and x6 in one pass); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/B2/P2_LAKE/probe.jsonl (run in progress; spring: lake groups = DF groups only); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/B2/P2_LAKE/status-start.txt:18 ('water: dormant -- no open water on the surface'); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/B2/master.log:47-61 (P2_LAKE resumed 13:28, checkpoints to 56/84); /Users/nathanielcannon/Claude/Projects/DwarfCron/.claude/scratch/sw-questions/G2/occ.py, water_df.py, stay.py (tallies); /Users/nathanielcannon/Claude/Projects/DwarfCron/.claude/scratch/pacing/ladder/COAST.txt:54-61,144-158 (ocean casts; albatross FREQUENCY 5, crab 17, osprey 9); /Users/nathanielcannon/Claude/Projects/DwarfCron/data/pacing/mechanics-diagram.html:1179-1190 (panel 5k: 'DF sends no water waves' is inaccurate)

</details>
