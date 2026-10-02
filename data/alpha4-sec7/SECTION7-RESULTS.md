# Alpha Four section 7: results ("What this page cannot check", 15 rows)

W2:Urist, 2 Oct 2026. Desk analysis only (no rig contact).

- **Tool:** seasonal-wildlife v7.1.
- **Fort:** RinghatchetsReady (region9: 8x8, lake + river + pool, 3 caverns, savagery 73, 7 citizens).
- **DFHack:** 53.16-r2.
- **Numbers:** every figure below comes from `scripts/sec7-tally.py`. The full printout is `data/alpha4-sec7/sec7-tally.txt`, the machine-readable copy is `sec7-tally.json`, and the figures are in `figs/`.

| run | build | what it holds |
|---|---|---|
| `20261002-015732` | 9e5aabe | stages FACTS, R2, VALIDATE (`data/validation/full/20261002-020031`), PANEL and WEBLOAD. Its eco blocks were no-ops (the S7() bug) and are ignored. |
| `20261002-024942` (core3) | 9e5aabe | FSH3 FSH4 PK2 STP1 COHT PAN1 SCV3 SCV3W VF1 GRD1 EXR1 EXU1 F1 PERF1 |
| `20261002-075328` (rerun) | a4fix 69e97a1 | SKL NAT IRRM IRRP2 IRRTSEQ PERF1 PERF2 PERF4 |
| `20261002-133843` (late rerun) | a4fix 69e97a1 | TRIM (aborted again: 0 dismissals), IRRR35 (complete, 5 v 5), VF4 (still running when this was written; PENDING) |

**Method.** Each arm has n = 5 reps, with a fresh DF load per arm. A cell counts only once eco-run has written it; MANIPFAIL cells are listed and never scored.
- **Means:** given with SD and a 95% t-interval.
- **Two-arm contrasts:** the **exact two-sided permutation test** on the difference of means, over all 252 splits of 5 v 5. Effect sizes are the mean difference and Hedges' g.
- **Cell-level yes/no outcomes:** **Fisher's exact test** (two-sided).
- **Smallest p:** with 5 v 5 an exact test cannot go below p = 0.008.

## Summary

| # | row | verdict | the numbers (n = 5 per arm) | what remains |
|---|---|---|---|---|
| 1 | Skill writes act on new arrivals and do not rust | **CONFIRMED** (stand-ins) | Units placed after the write carried caste SNEAK at once in 100% of cells (nopkg 0%).<br>Floored units dropped 0/50.<br>The no-floor positive control rusted 50/51 units in 5/5 cells (Fisher p = 0.008). | A DF-drawn wave (not `units.create`) and DF's real 30,000-t rust clock (FULL S7_SKL30K) |
| 2 | Packs, stoops and fishing change kills | **Packs CONFIRMED**; **stoops and fishing INCONCLUSIVE** (vacuous) | Packs: placed wolf>buffalo attacks 66 v 37 (p = 0.024, g = 1.7); kills 3.8 v 1.2 of 6 (p = 0.016, g = 2.8).<br>Stoops: placed eagles attacked 0 times in 10 cells.<br>Fishing: bears were never adjacent to pike (0/200 samples), and polar bears never swam. | STP1/FSH3/FSH4 need subjects that meet (see "harness defects") |
| 3 | The clock holds groups near the cap | **Land NOT CONFIRMED** (overshoots); **water CONFIRMED** | Land: def 10.8 groups (95% CI 9.9-11.6) v cap 9, so above the target band 7.5-9. Over the cap in 84% of samples; v70 6.9 (p = 0.008).<br>Water: lake 8.5 and river 8.4 per body in every rep; pool 0 in 2/5 reps; v70 1.3 per body (p = 0.008). | Why land overshoots (tool question 1) |
| 4 | The cavern gate holds five; natives trimmed walk off | **NOT CONFIRMED** (gate); **trim: partial** | Groups per cavern by the tool's own record: 7.1 (CI 5.4-8.7), max 9-13, against cap 5. v70 (gate off): 5.9 (p = 0.10).<br>The tool's end status reads cavern now 5-13 of cap 5.<br>Natives by population entry: 2.7 (max 6).<br>Trimmed natives did leave, within 3,000-30,000 t.<br>S7_TRIM (cap 1, a cavern at 5 groups) dismissed **0** in 3,000 t. | Tool question 2 (the trim cannot touch DF-wave groups) |
| 5 | A lost leader makes the group scatter | **NOT CONFIRMED** (no detectable effect at n = 5) | PAN1 mean pairwise distance, panic on v off: 25.9 v 20.7 tiles at t1200 (p = 0.33); 30.1 v 27.2 at t2400 (p = 0.52). Panic fired in 5/5 on cells and 0/5 off.<br>COHT: the led school spread *more* than the unled one (72 v 58 tiles at t3000, p = 0.41), and no member ever "followed". | More reps or a stronger contrast. The orca version needs an ocean fort (OCEAN). |
| 6 | Tokens act | **Partly CONFIRMED**; **CRAZED and MISCHIEVOUS NOT CONFIRMED**; **R35 vacuous** | Cache tokens (thief/meander) stuck on 852/852 subject-samples, and natives read 0 (M3).<br>SNEAK hid 80% of subject-samples v 0% (p = 0.048).<br>Every one of 8 end routes x 5 left 0 residue.<br>**The CRAZED mask read 1 in 0/556 unit-samples; MISCHIEVOUS in 6/319** (the reassert ran 60-72 times a cell).<br>R35: the raw's own max (5) equals apcap 5, so 0 raws were ever capped. | Tool question 3 (the masks); P2 never reached the fort; M9 not built; R35 with apcap below 5 |
| 7 | Scavenging takes days, swimmers eat from the water | **CONFIRMED** (both halves; the swimmer switch adds little) | Natural mode: 0/5 cells cleared the 6 corpses in 6 days, with 7 corpses left v 0.4 under sweep (p = 0.008); the placed scavengers ate 6-51 kg.<br>Pond grabbers ate 86 kg in the water with swimmers on and 77 kg off (p = 0.04), and were never dry. | Whether natural mode ever finishes a carcass (longer run) |
| 8 | Vermin eaters eat what they walk to | **VF1 INCONCLUSIVE** (vacuous); VF4 see row 8 | Grasshoppers gone, forage on v off: 0.8 v 0.4 of 20 (p = 0.68). No BADGER row appeared in the tool's own `vermin eats` table in any cell, and no distance receipt shows a badger reached them. | A reach receipt; VF4 if its rerun completes |
| 9 | Apex presence target; ladder 20% carnivores | **NOT CONFIRMED** (one month); AP1 and R28P CONFIRMED; INV3 NOT-TESTABLE-HERE | Apex presence (the scheduler's seen/total): def 0.17 (0, 0, 0, 0.16, 0.68) against a target of about 25%.<br>Land carnivore share 0.05 (CI -0.03 to 0.13) against 20%; v70 also 0.05 (p = 0.98).<br>AP1: AP share 0.10 at ap_pick 0.1 v 0.14 at 1. | APX1 over a whole season; INV3 needs a calm map |
| 10 | Pull, mix and guard shape the water | **SURV CONFIRMED**; **MIX1 descriptive only**; **GRD1 INCONCLUSIVE** (vacuous); **PELA NOT-TESTABLE-HERE** | SURV scan 130 ms (budget 1,000).<br>MIX1, def v v70: river 2-6 species v 3-4 (Shannon H 0.4-1.6 v 0.9-1.3).<br>GRD1: every pike read wet at the first sample in both arms, and the guard rescued 0. | An ocean fort (PELA); GRD1 with a t0 dry receipt |
| 11 | Extinct corrections change arrivals | **EXR1 CONFIRMED (weak)**; **EXU1 INCONCLUSIVE**; **EXF1 NOT-TESTABLE-HERE** | Fix on: BENIGN castes 0 v 2, and 5.0 v 0 relations written.<br>Eoraptor attacked hares in 3/5 v 0/5 cells (Fisher p = 0.17; attacks 8.2 v 0, p = 0.17).<br>EXU1: no attack in either arm and no per-unit receipt. | EXF1 needs an extinct land apex in the embark |
| 12 | Water auto-on and spill reach 3-5 groups | **Auto-on CONFIRMED**; **F2 give-back NOT SEEN** | F1: the layer came on in 5/5 (layer_off 0/5), at 4.2 groups per body by t2400 v 0 (p = 0.008).<br>NAT: def (spill on) 8.5/8.4 per body v v70 (every lever off, spill included) 1.7/2.2 (lake/river). | F2's borrowed-season give-back has no ledger receipt |
| 13 | Cost of every v7.1 change | **MEASURED**: the new paths are cheaper than legacy; the a4fix perf work shows | a4fix worst tick 52 v legacy 88 ms (p = 0.008); tool time 80 v 108 ms per 1,000 t (p = 0.008).<br>New paths 9e5aabe → a4fix: worst tick 71 → 52 ms, 112 → 80 ms per 1,000 t (both p = 0.008).<br>Web page: -4.8% t/s (p = 0.048).<br>Overlay: no measurable cost (p = 0.50), and its perf counter is unreadable. | PERF3 (OCEAN); a perf-counter key for the overlay |
| 14 | Panel and page round trips on a real screen | **gui/web claims CONFIRMED**; **the Panel round trip NOT TESTED** (harness) | validate-full gui.* 61 PASS / 1 FAIL (gui.k.layR, a display clip, fixed in dcd169b); web.* 14/14 PASS.<br>PANEL: 13/13 sections reached, no clipped row, clean stderr; but 0/13 Right steps changed a config path, and 13/13 screens were identical before and after. | Fix the PANEL harness focus and rerun; the narrow-screen check is manual |
| 15 | Anything at all on DFHack 53.16-r2 | **CONFIRMED** (no r2 regression found) | R2 checklist 6/6 PASS.<br>validate-full: 356 PASS, 7 FAIL, 41 NT. All 7 FAILs are triaged: 5 validator, 2 tool (a display clip, ecology cost), fixed; none is r2-specific. | none |

## What matters most

**Tool problems or contradictions of a design claim:**

1. **The CRAZED and MISCHIEVOUS masks do not stick. This is a tool defect.**
   - **What was read:** the tool writes `u.uwss_add_caste_flag[f] = true` (seasonal-wildlife.lua:10007 at a4fix). The probe read the same field back:
     - CRAZED: 0 of 556 unit-samples, including t0 (20 t after the write).
     - With `irruption.reassert` on (mischief arm, and P2 arm C), the reassert fired 60-72 times a cell. MISCHIEVOUS still read 1 in only 6 of 319 samples, all six at one sample (rep 4, t3000).
     - NOFEAR read 0 everywhere in P2.
   - **The likely cause:** DF recomputes the unit-wide syndrome flags itself and clears a write that no syndrome backs.
   - **Consequences:**
     - The M1/M2/M5 claims fail as built.
     - Every reassert is wasted work each pass.
     - The T-route "mask residue 0" is vacuous: there was never a mask to leave.
   - **What does work:** the cache-flag tokens (`enemy.caste_flags`: CURIOUS_BEAST*, MEANDERER, AMBUSHPREDATOR) stuck on every sample, and SNEAK (hidden_in_ambush) works.
   - **The likely fix:** carry these four tokens through a real syndrome (a curse/interaction with the CE tags), not a raw write to the uwss flags.
2. **The cavern gate does not bring a cavern down to five, and the trim cannot act on DF-wave groups.**
   - **What was measured:** with the gate on, the tool's own record held 7.1 groups per cavern (max 13) for 50,000 t, and its status line read `cavern:0 cap 5 ... now 10` at the end.
   - **Why:**
     - The gate stops new draws: every held raw was at its hold level at every sample (held_open = 0 in 85/85).
     - But it cannot remove the groups already there. `V7.GRP.trimOne` picks only `grp.resident` groups (seasonal-wildlife.lua:11138 at a4fix), and DF-wave groups found by `discoverGroups` are `resident=false`.
     - S7_TRIM shows it directly: cap 1, a cavern at 5 groups, 0 dismissals in 3,000 t (the risk BLOCK-FIXES predicted).
   - **Trimmed natives do walk off, but slowly.** trim_undo peaked at 6-14 units and drained to 0 within about 3,000-30,000 t of the trim. The countdown is 10, so "walk off" takes days, not ticks; this is the groups.md open risk.
   - **Natives by population entry stayed at 2.7 per cavern**, inside the target. The two counts disagree by about 2.6 times; the tool record splits one entry into several groups.
3. **The land clock overshoots its cap.**
   - **The finding:** def held 10.8 land groups against cap 9, above the cap in 84% of samples. At the end the tool's own line read `land cap 9 target 8.9 now 11 ... next release paused at the cap`.
   - **The likely cause:** the clock pauses its own releases, but DF's own surface waves keep arriving and are counted.
   - **The contrast:** v70 (no adaptive clock) held 6.9.
   - **Verdict:** the target band [cap-1.5, cap] is missed from above, and promptly (land 10-11 by t3000).
4. **The apex scheduler and the ladder missed their targets in this month.**
   - Apex presence was 0.17 (3 of 5 reps never placed an apex in 47,000 t of Spring); the tool's status reads `waiting (hazard)`.
   - Land carnivore share was 0.05 against 0.20, the same as v70. The ladder made no measurable difference to the unit share on land.
   - One month is the design's own stated shortcut, so this is a miss over a month, not a season.
5. **R35 (the animal-people cap) is vacuous on this fort.**
   - PLUMP_HELMET_MAN's raw cluster range is 3-5, and `groups.apcap` is 5, so `V7.GRP.apCap` never caps anything (capped = 0, `0 species capped now` in every cell).
   - The irruption's wave of 10 comes from the irruption's own sizing (size_cap 20), not from lifting the cap.
6. **Packs work, decisively.** Pack recognition (largest 5) raised placed wolf kills of buffalo from 1.2 to 3.8 of 6 (p = 0.016, g = 2.8).

**Harness defects found while reading (none is a tool bug):**
- **cx-sec7 `apraw` swaps the cluster range.** It prints `cluster_number[0]` as `min` and `[1]` as `max`, but the tool's convention is [0] = MAX (seasonal-wildlife.lua:1700). So the quiet arm's check `apraw[t600].max<=5` read the raw's MIN (3). It passes either way here; fix the labels.
- **PANEL.** The Right step went to the section list, not a control. All 13 before/after screens are identical apart from the FPS line, and the "read-back" it counted (11/13) is the stale status line from an earlier command (screen-check trap 1, label echo). The 0/13 is a harness result, not a Panel verdict.
- **Vacuous blocks: the subject was never reached.**
  - **STP1:** the placed eagles flew off (their group centroid ended 30-220 tiles from the prey). The last ecology pass recorded 1 stoop across the 5 on cells. The only eagle kills were by a native GIANT_EAGLE left after the wipe.
  - **FSH3/FSH4:** the bears' closest approach to the pike averaged 15-17 tiles (adjacency 0/200), and polar bears never entered water.
  - **GRD1:** no dry receipt after the teleport. At t200 all pike were wet in both arms.
  - **EXU1:** no attack and no per-unit BENIGN or relation receipt.
  - **VF1:** no badger appears as an eater.
- **M6 (goalonly).** The harness steal-goal write did not persist: 0 steal-goal samples, against 4% under the thief token (p = 0.008).
- **M1 (save/reload).** The crazed arm's event had ended (cooldown, at t500-t2900) before the save, so the reload read no subject.
- **P2.** `dacc` (the distance to the access point) is -1 everywhere: the event had no access point. No subject came within 124 tiles of a citizen, so the "approach" outcome is untested.

## Per row

### 1. Skills (S7_SKL, rerun, a4fix; 3 arms x 5)
- **Receipts:** 95/95 manipulation checks passed. pack_bonus read back 0 in every cell, so the arms are clean of the second writer.
- **SKL1 (new arrivals):** cougars and wolves placed after the write and read before any pass carried the caste level (15 and 5) in 100% of cells in both package arms, and 0% in nopkg (no SNEAK entry). Units placed before the write were at level too (the soul write).
- **SKL2 (rust):** after +200,000 on the unused/rust/demotion counters:
  - **pkg_nofloor:** 50/51 units rusted (15→14, 5→4, rusty flag set; DF consumed the counters), in 5/5 cells.
  - **pkg (floor kept):** 0/50 dropped, and DF left all 50 units' counters at 200,000, never running its rust step against the floor.
  - **The test:** Fisher exact on cells, 0/5 v 5/5, p = 0.008. The positive control engaged, so the floor result is not vacuous.
- **Aside:** DF-made cougars (ids not placed: 12954 pkg rep 4, 13010 nofloor rep 1) appeared at t2000 with SNEAK 15 and floor 15 under the package, and with no SNEAK under nopkg (13010 nopkg rep 4). This is suggestive evidence for the strict SKL1 form (a DF-created unit inherits the caste write), but the creation path is unverified.

### 2. Kills
- **PK2:** 5 wolves and 6 buffalo; placed>placed only.
  - Pack on: largest pack 5 in 5/5 cells (off 0/5); relation pairs 30 in both arms.
  - Attacks 66.0 (SD 17.0) v 37.4 (13.1), p = 0.024.
  - Kills 3.8 v 1.2, p = 0.016.
- **STP1:** vacuous; see "harness defects". 0 placed eagle attacks in 10 cells; 3 placed prey were killed by a native GIANT_EAGLE (on rep 3).
- **FSH3:** 0 adjacency in 200 samples; closest bear-pike approach 17.4 v 15.4 tiles (p = 0.75); 0 attacks.
- **FSH4:** 0/50 samples with a polar bear in water; 0 breathing faults; 0 attacks.

### 3, 4, 9, 10, 12. Natural arrivals (S7_NAT, rerun, a4fix; def v v70)
- **The run:** 50,055 t per cell, which crosses the Spring→Summer change at about t47,000 (the ledger reads "Summer roster applied" in 10/10). Sampled every 3,000 t.
- **Receipts:** 160/160 checks passed. In def, held_open = 0 at every sample and cavern_hold_mix was true. In v70, all ten levers read back off.
- **Figure:** `figs/nat-groups.png`.
- **Land (row 3):** see the summary. Per rep, def: 10.1, 11.3, 10.1, 11.7, 10.8.
- **Water (rows 3 and 12):** lake and river hold 8.2-8.6 per body in every def rep, near the per-body cap of 9. The pool (276 tiles, depth 1) got 0 groups in 2/5 def reps.
- **Cavern (row 4):** per cavern, def c1 5.8, c2 8.3, c3 7.1. trim_undo series per rep are in sec7-tally.txt. v70 has no trims (trim_undo 0).
- **H5 groups3, cavern layer:** 11-17 live groups with tool_groups 0 at the last sample. groups3's cavern view does not see the tool's groups, so it is not used as a gate measure.
- **Apex and ladder (row 9):** see the summary. The tool's end status: `apex:land ... waiting (hazard)`, `apex:cavern groups 6 ... cap 2 reached`. extinct_drawn = 0 in every sample: no extinct unit arrived.
- **MIX1 (row 10):** descriptive only, since the design gives no numeric target. At the last sample (species, top share, Shannon H):
  - def: lake 2-4 species, H 0.6-1.3; river 2-6 species, H 0.4-1.6.
  - v70: lake 1-3 species; river 3-4.

### 5. Leaders
- **PAN1:** leader male 10/10; killed 10/10; panic ledger 1-2 lines in on cells, 0 off.

| tick | panic on (mean pairwise distance) | panic off | p |
|---|---|---|---|
| t300 | 14.1 | 14.3 | 0.94 |
| t1200 | 25.9 | 20.7 | 0.33 |
| t2400 | 30.1 | 27.2 | 0.52 |

  Growth from t0 to t2400: 21.5 v 16.1 tiles (p = 0.26, g = 0.70). The direction is right, but the effect is not resolved at n = 5.
- **COHT:**
  - The tool adopted the school as `water:river` (the lake spot lies by the river).
  - The leader was lost in 1/5 led cells (t900).
  - DF's `following` was 0 in every sample, so cohesion does not use DF's follow field.
  - The led school's spread was 21/53/72 tiles at t600/t1500/t3000, v 16/42/58 unled (p ≥ 0.29).
  - No dry swimmers in either arm.

### 6. Tokens (rerun, a4fix)
- **IRRM:** 7 arms x 5. Every subject is TROGLODYTE (civ candidate TROGLODYTE in every cell), so the BLOCK-FIXES pick bug is gone.
  - **M7 sneak:** hidden 100% at t0 and 80% later, v 0% (p = 0.048).
  - **M4 thief:** steal goal 4% of samples v 0% (p = 0.008); items carried 0 everywhere, so no theft in 3,000 t (subjects stayed at least 150 tiles from citizens).
  - **M3:** natives outside the event read 0/0 on all four flags; the caste write stays on the subjects.
  - **M8 wander:** subjects ended 23 tiles closer to citizens than control (212 v 235, p = 0.095).
  - **M1/M2/M5:** see "What matters most", item 1.
- **IRRP2:** A / B / C.
  - **A:** no event.
  - **Waves:** B and C each sent 3 waves (50-60 subjects).
  - **Deaths:** C lost 24.0 subjects v 5.8 in B (p = 0.008, g = 3.5), almost all to native CROCODILE_CAVE. The R10 package's walks take subjects into crocodiles.
  - **Approach:** no subject came within 124 tiles of a citizen in any cell. Mean citizen distance C 227 v B 218 (p = 0.64).
  - **Citizens:** 7 at the end in every cell; 0 dwarf deaths.
  - **Verdict:** the main experiment's question (the threat to the fort) is untested on this fort, at this distance.
- **IRRTSEQ:** 8 routes x 5.
  - Every route's event started with 6 subjects whose cache flags read 12/12, ended (idle or cooldown), and left resid mask 0, cache 0, units 0 and active 0.
  - T-SAVE: after save and reload the event was still active with 6 subjects, and the reassert continued.
- **IRRR35:** `20261002-133843`, 5 v 5, complete.
  - In all 10 cells the raw range is 3-5 and capped = 0 at every sample (`0 species capped now`).
  - Irruption waves were 9-10 (the irruption's own sizing, size_cap 20).
  - The quiet arm's natural groups were 2-6. The one group of 6 is above the raw's max, so it is probably two draws recorded as one tool group (trap 11).
  - **Verdict:** vacuous at apcap 5 (see "What matters most", item 5). To test R35, rerun with `groups apcap 2` or a species whose max is above 5.

### 7. Scavenging
- **SCV3:** time to clear all 6 corpses:
  - natural: >7,200 in 5/5;
  - sweep: 2,400 / 3,600 / 4,200 in 3/5, >7,200 in 2/5.
- **SCV3W:**
  - `hunters swimscav` was on in both arms, which explains why swimmers_off still ate.
  - POND_GRABBER visits: 13-15 (on) v 12-16 (off). Every finish was in water; 0 dry grabber-samples.

### 8. Vermin
- **VF1:** see the summary.
- **VF4:** the late rerun was still running when this was written. Its rows appear in sec7-tally.txt once a cell completes; until then, PENDING.

### 11. Extinct
- **FACTS:** real_world_extinct = 1; 6 extinct rows in the embark, 0 of them an apex. That is why EXF1 is not testable here.
- **EXR1 and EXU1:** see the summary.

### 13. Performance

**PERF1:** new v legacy (all ten `legacy_*` and stagger off). 12,000 t from a fresh DF; 5 v 5, except core3 legacy n = 4.

| | 9e5aabe new | 9e5aabe legacy | a4fix new | a4fix legacy |
|---|---|---|---|---|
| t/s (stopwatch) | 96.2 ± 14.1 | 64.9 ± 6.4 | 81.7 ± 10.1 | 78.6 ± 13.4 |
| worst tick, ms | 71 ± 4 | 132 ± 13 | **52 ± 5** | 88 ± 21 |
| tool ms per 1,000 t | 111.6 | 131.1 | **80.2** | 107.8 |
| groups job, mean / worst / over-budget runs (summed over the cells) | 21.7 / 78 / 26 | 26.0 / 83 / 16 | **13.2 / 50 / 0** | 21.9 / 71 / 1 |
| ecology job, mean / worst / over | 35.7 / 52 / 3 | 74.1 / 111 / 14 | **25.3 / 59 / 3** | 48.1 / 76 / 7 |
| fps while stepping | 207 | 186 | 206 | 200 |

- **The excluded cell:** core3 legacy rep 5. It reached 10,845 of 12,000 t in 817 s (12.6 t/s): the 871-s cell, a DF-process-age artefact, not a tool cost.
- **Within a4fix:** new beats legacy on worst tick (p = 0.008) and tool ms (p = 0.008). t/s does not differ (p = 0.69): DF's own simulation dominates t/s on this fort.
- **Across builds (new arm):** the a4fix perf work cut the worst tick 71 → 52 ms and the tool time 112 → 80 ms per 1,000 t (both p = 0.008). The over-budget groups passes went from 26 to 0. The ecology pass mean fell 36 → 25 ms; it still ran over budget in 3 of about 20 passes (5 cells x 4).
- **t/s across builds:** 96 v 82 (p = 0.095, the other direction). This is load-to-load variance (trap 6: identical loads disagree by 10-16%), not a regression; tool ms fell.
- **PERF2 (a4fix):** t/s overlay new 96.2, legacy 90.9, off 101.8 (new v off p = 0.50); fps 219 v 223 (p = 0.78). DFHack's perf counters held no overlay key (rows = 0 in 30/30 reads), so the overlay's own ms is unmeasured.
- **PERF4 (a4fix):** 67 citizens. Events on v off: 83.6 v 80.7 t/s (p = 0.71); 84.0 v 84.7 tool ms per 1,000 t (p = 0.94). Events cost nothing measurable.
- **WEBLOAD (9e5aabe):**
  - Page polled v no page: 116.9 v 122.8 t/s (-4.8%, p = 0.048); fps 241 v 261.
  - Snapshot ms mean 0.2, worst 26 ms, so the web.v71.perf claim (under 50 ms) holds.
  - Status call worst 213 ms (mean 1.4).
  - 33-34 requests per rep, all 200.
- **Figure:** `figs/perf1-builds.png`.

### 14, 15. Real screen and r2
- **R2 checklist:**
  - version DFHack 53.16-r2;
  - a setting through save and reload;
  - 0 ghost or doubled tiles after a nudge;
  - 0 not-FINE units after a water draw;
  - smooth-movement and stockflow off;
  - sustain, makeown and tp.

  All PASS.
- **validate-full TRIAGE:** see `data/validation/full/20261002-020031/TRIAGE.md`.
  - Tool fixes: `dcd169b` (the status-line clip, a real defect on any multi-biome fort) and `72b5c25` (ecology per-pair cost; PERF1 above shows the effect).
  - FACTS probes: SURV 130 ms; AP1; R28P (magma crab refused on the surface and in a cavern).

## Not testable here, and what each needs

- **INV3:** a calm map (savagery 73 here).
- **EXF1:** an extinct land apex in the embark (this fort has 0).
- **OCEAN rows** (PELA, PEL1, COHT with orcas, PERF3, the ocean half of FSH4): a region9 shore 1x1.
- **The narrow-screen check:** manual.
- **SKL with a DF-drawn wave, F2 over two seasons, APX1 over a season:** these are FULL-tier runs, about 56 h per arm pair.

## Reproduce

```sh
python3 scripts/sec7-tally.py --figs    # needs matplotlib for --figs; reads the run dirs above, newest late rerun auto-detected
```
