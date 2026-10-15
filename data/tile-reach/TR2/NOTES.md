# TR2 tile-reach test (15 Oct 2026) -- V75_SMALLSAV (region19 small savage lake), DFHack 53.16-r2

Question (user 15 Oct): does a flier with population entries on more region tiles get drawn more often?
Design: scripts/tile-reach.py + cx-tilereach.lua. Every surface Animal entry on the fort's 6 draw tiles closed (66-70), two solitary
fliers open at FREQUENCY 50 and quantity 200: one on a single site tile (118:56), the other on every draw tile its biomes allow (5: 117:55,
117:56, 118:55, 118:56, 119:57). Every wild surface arrival recorded with its source entry's tile and vanished at once. 4 replicates,
the one-tile species alternating (peregrine falcon / barn owl). Tool rotation disabled; fort never saved.
TR1 is invalid (tile-reach-TR1 data kept as TR1-invalid-seen-bug): the seen set outlived reloads, later arrivals with reused ids were
never vanished and held DF's surface gate shut (reps 2 and 4: 5 and 0 waves in 90,000 ticks).

Result: 5-tile species 124 waves, 1-tile species 37 (77%; per replicate 33/7, 31/10, 29/11, 31/9 -- both species, both roles;
two-sided binomial p 3.5e-12 against 0.5). A wave every ~350 ticks with the gate kept clear.
Per entry (pooled): 118:56 site -- many 43, one 37 (the same tile draws both species alike: 8/7, 14/10, 12/11, 9/9 per replicate);
119:57 site -- 58; neighbours 117:55 10, 118:55 8, 117:56 5.
Map footprint (outside surface tiles): 119:57 59%, 118:56 35%, 119:56 5% (lake, no entry), neighbours 0.3-0.4% each.
Reading: DF picks per entry, weighted by FREQUENCY and by the entry's tile. Site tiles carry most of the weight (roughly in line with their
share of the map); neighbour tiles a little, more than their tiny footprint (the exact neighbour rule is open: the three neighbours appear
only in blocks at other z levels). So a species' odds = FREQUENCY x the summed weight of its open entries.
Also: recorder vermin.tsv checked on this fort (vermin-sample-V75_SMALLSAV.tsv): 18 species rows in 2 samples.
