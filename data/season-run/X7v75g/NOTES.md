# X7v75g notes (14 Oct 2026) -- sw b180907, DFHack 53.16-r2

- B brook fort re-embarked (V77_BROOK, region19 6,56 off 7,7, startdwarf 50; user 14 Oct: new forts, no hand rebuilds) on the 25,000 cm3
  brook cap (my call per user). Casts built at embark: fresh = longnose gar + beaver (spring, winter) / platypus (summer, autumn), vermin trout,
  char, perch, shad, Drepanopterus.
- Water life every season (X7v75c: none in spring, ospreys and tree frogs otherwise): spring beaver 77 + gar 6, summer platypus 22, autumn
  platypus 20, winter beaver 73 + gar 1; on the water per day 31.6 / 10.4 / 9.9 / 25.9. Draws: pools 29 platypus + 18 beaver, the brook 4 gar
  + 2 beaver. Each season is one species (dominance 0.93-1.0): the in-cast odds issue (ecology diagnosis 2).
- FAIL: 8 in-cast send-offs, all PLATYPUS in autumn: DF sent it overland from its land entry; castTurnover filed it under its land key (not in
  the autumn ground cast) and sent it off on arrival, though the autumn fresh cast holds it under water:PLATYPUS. 3a212d7's either-key rule ran
  water -> land only. Fixed sw 4b57591 (land group cast if its water: key is); rerun X7v75h on the same fort.
- Otherwise: 758 managed arrivals, 0 off-cast late, 0 gate send-offs, reserve kept, 0 hangs, 190 t/s, all 7 receipts passed.
