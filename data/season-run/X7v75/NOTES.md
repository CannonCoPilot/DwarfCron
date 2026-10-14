# X7v75 notes (13-14 Oct 2026) -- validation year on sw 414d494 + plugin 37baf8d

- B brook (V76_BROOK): PASS. Pauses 57 (6 began one over, none two over), 0 over-cap send-offs. FINDING: the tool drew nothing into the brook all year (every water arrival a DF osprey wave): fresh casts all over the brook cap (10,000 cm3) but the platypus, which has only a land entry the water draw ignored. Fixed sw 38c2fa8 (rerun X7v75c).
- X extinct wilds (50): PASS after the analyser learned mid-run cast additions (6d65b6f4). 49 extinct arrivals (ankylosaurus 10, kelenken 9, triceratops 9, kosmoceratops 7, megacerops 5, nodosaurus 4, allosaurus 2, torvosaurus, glyptodon, smilodon). One exhaustion (longnose gar): no stand-in passed (closest failed guild), slot left empty.
- E sheltered evil coast: LOST at 300,730 (autumn). A pool-drawn mink raised as an infernal ash zombie walked down the shelter's open stair and bit the mayor; the infection took the fort. Fix: a hatch cover on the stair (scripts/shelter-hatch.sh), rerun X7v75c.
- G good coast: never ran here (DF stuck in E's Options menu; runner fixed to restart DF on a failed quit) -> X7v75b.
