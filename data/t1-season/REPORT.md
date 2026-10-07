# Test item 1 (PLAN R5): one season change on five forts, everything on (7 Oct 2026)

User's spec: Smaksmo Oxdu (region19), "Start new game in existing world", default embark preparation ("Play now!";
the world exists, so no worldgen), `startdwarf 30`, 16x16 embark, `reveal`, one season change, every
seasonal-wildlife feature on at its default, all animal activity recorded, save and exit. Package
seasonal-wildlife 7.2.0 (branch v7.2-plugin), installed in the rig DF (DFHack 53.16-r2).

Every fort embarked at year 250, tick ~44,200 (spring day 37), and ran to summer day 2 (tick 102,800): 58,600 ticks.
At embark the plugin's map-load bridge set up each fort with no command (20 of 20 switches, 4 layers, 7 jobs,
renderer drawing). The in-game recorder (`sw-t1-recorder.lua`, every 100 ticks) logged every non-citizen unit's
arrival, departure, death (with DF's incident cause and killer), adoption into the tool's groups, positions every
1,000 ticks, and every report. Per fort: `<FORT>/summary.md` (`analyze.py`), raw TSVs, the tool's `ledger.txt`, and
`run.log`.

| Fort | Square (region tile, offset) | Saved as | Dwarves at summer |
|---|---|---|---|
| River + ocean | 54,45 +0,8 (shrubland, major river; temperate ocean) | T1END_OCEAN_RIVER | 30 of 30 (second attempt; see below) |
| Lake + river | 14,12 +8,12 (freshwater lake; marsh with a major river) | T1END_LAKE_RIVER | 30 of 30 |
| Brook | 51,22 +0,0 (conifer forest with a brook) | T1END_BROOK | 30 of 30 |
| River drop | 38,36 +0,8 (major river dropping 11 region levels; no falls, see 5) | T1END_FALLS | 30 of 30 |
| Waterfall (FALLS_2) | the user's embark, Whitepaged (Volalmorul), 6x6, tropical; a river falling into a gorge | T1END_WATERFALL | 30 of 30 |

FALLS_2 (added 15:00): embarked by the user; falls look fixed first (finding 8), then `reveal` and a run from spring day 51
(tick 61,036) to summer day 2 (102,828), 41,800 ticks, same recorder. Its roster was dumped before and after the change
(`roster-start.tsv`, `roster.tsv`); the four 16x16 forts' rosters were dumped from their end saves (`T1_*/roster.tsv`).
`build_report.py` builds the report page (`report-page.html`, published https://claude.ai/artifact/6sPcvuJAWB6FbRtkei78Cs) from each fort's `report.json` (`report_data.py`).

## Animal activity (underworld demons excluded: DF's own, sealed; any DEMON_ race or z <= 8)

| | River + ocean | Lake + river | Brook | River drop | Waterfall (FALLS_2) |
|---|---|---|---|---|---|
| Arrivals (surface / caverns) | 771 (375 / 396) | 602 (261 / 341) | 734 (261 / 473) | 589 (313 / 276) | 108 (64 / 44) |
| Left the map | 322 | 235 | 261 | 307 | 86 |
| Died (in caverns) | 256 (176) | 281 (173) | 326 (297) | 200 (150) | 30 (24) |
| Wild on the map, start -> end | 145 -> 401 | 178 -> 302 | 94 -> 328 | 271 -> 369 | 138 -> 128 |
| In the tool's groups, start -> end | 0 -> 268 | 0 -> 221 | 63 -> 245 | 134 -> 231 | 71 -> 78 |
| Top killers | jabberer 73, cave crocodile 34, magma man 28, hungry head 23, giant kea 16 | cave crocodile 83, crundle 18, snapping turtle 18, alligator snapping turtle 17, giant cave spider 15 | jabberer 79, cave crocodile 74, molemarian 62, reacher 44, helmet snake 20 | jabberer 43, cave crocodile 42, giant cave spider 21, alligator 16, reacher 14 | molemarian 13, jabberer 6, hyena 3, cave crocodile 3, reacher 2 |
| Fort's own animals killed | 9 of 11 (giant keas: dogs, cats, rabbits, duck, goose, cavy) | dogs 3, cats 2, duck | dogs 2, yak, chicken | none | cat 1 |
| Frame rate, median (lowest) | 29 (1) | 28 (2) | 18 (4) | 27 (2) | 86 (54) |
| Cavern <-> surface jumps | 0 | 0 | 0 | 0 | 0 |
| Season change: exhausted species handed on / lent seasons returned | 28 / 105 | 14 / 9 | 23 / 49 | 20 / 34 | 18 / 23 |

Corrected 7 Oct 15:40 (the first version of this table): "left the map" counted DF's removals of units already gone
from its unit list as `?` (1,403 rows), 4 removals of dead units, and underworld demons above z 8 (river drop fort);
killers with a space in their name were cut at the space ("alligator 32" was alligator 15 + alligator snapping turtle
17). `analyze.py`, `report_data.py` and `headlines.py` now name removals by unit id (`fill_removed`) and match whole
killer names; every summary.md is regenerated. The lowest frame rate is from every sample; the median is new.

## Findings

1. **FIXED: the ecology nudge teleported cavern predators to the surface, and the first river + ocean fort was lost.**
   With `enable` turning the opt-in "livestock as prey" on, the nudge's realm check let any non-wild target (the fort's
   animals) through in any realm. Cavern-2 jabberers (4) and crundles (4) were teleported ~80 levels up next to the
   fort's animals; the jabberers struck down all 30 dwarves at spring tick ~68,400 ("Your settlement has crumbled").
   Fix seasonal-wildlife e494d331: the nudge never moves a unit out of its realm (the relation write is unchanged).
   Proof: 9 cavern <-> surface jumps on attempt 1 (`T1_OCEAN_RIVER/attempt1-fort-lost/`), 0 on all four forts after.
2. **OPEN (test item 4): minks drown in the lake by the dozen.** The water layer draws MINK into the lake at the map
   edge (column depth 5); balance and feed multiply its weight x20 because the role is missing, each one drowns, so
   the role stays missing: 23 draws, 55 minks drowned on the lake fort. Ospreys also drown (2-4 per fort).
3. **OPEN (test item 4): the brook fort's water census lists no brook** (23 rivers, 282 pools). Whether C3's brook
   rule saw the brook is unverified; otters (59) and milkfish (41) arrived there, mostly DF's own.
4. **OPEN (test item 2): the cavern gate cannot hold DF's cavern waves.** Cap 5 groups per cavern; the ledger shows 23-31
   groups in cavern 2 while the gate sends off one gated wave per pass.
5. **NOT MET: the waterfall fort has no surface waterfall.** The river's 11-level drop comes down in steps: no surface
   mist and no falling column of 2+ levels at summer (one-shot scan of the moving-water blocks, z >= 100). Only cavern
   falls (mist at z 10-16 and 109). The user's own FALLS fort (Ponderedring) has one, but its footprint is a site.
   A waterfall needs a site found by inspection, not by region elevation.
6. Site picking: the region-level `site` flag misses small sites; the first lake square (21,8) overlapped elf forest
   retreats ("Cannot embark on another site"). Squares are now checked against every site's footprint.
7. Rig: `quicksave` writes DF's "autosave 1" slot (parked in df-snapshots/parked); two embarks timed out on the
   position read after load (DF busy ~5 min at 100% CPU) and were finished by hand; `open_site_screen` now clicks the
   "Folder: regionN" row when two worlds share a name (region18/19).
8. **FIXED: the waterfall drew streaks several ways at once, and the falling row looked like dry ground** (user, FALLS_2).
   Each lip tile pointed at its own nearest top and the river's sideways dashes crossed them; the falling water had no
   cell of its own, so DF's translucent sprite showed the gorge floor. seasonal-wildlife 749384b: one heading per edge
   (the mean of its feeders, reversed), true 8-way diagonal streaks, a white-water curtain over falling tiles, no river
   dashes off the lip. Before/after: `data/recordings/20261007-150353-falls2-initial`, `20261007-151408-falls2-curtain2`.
   Hot-swapped into the rig; packaged as seasonal-wildlife-7.2.0-dfhack-53.16-r2-749384b1.zip (not yet installed as a package).
9. **WORKS: the season change.** On summer 1 each fort applied the summer roster; 14-28 summer species per fort had no
   world stock left ("exhausted (stock 0)") and each handed its niche to an off-season species of the same layer and role
   for the season (FALLS_2: troll -> molemarian, hippo -> tigerfish, jaguar -> hyena, ...); the seasons lent in spring went
   back (9-105). FALLS_2's roster diff: 34 species changed seasons, all from those two rules.
10. **OPEN (tuning): frame rate on 16x16 forts** is a median 18-29 fps with lows of 1-4, against 86 on the 6x6 waterfall
   fort (tool's worst pass 543 ms there).
