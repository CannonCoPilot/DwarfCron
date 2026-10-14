# X7v75e notes (14 Oct 2026) -- sw f83d300, DFHack 53.16-r2

- T terrifying coast, shelter SEALED (V75_TERROR50L = V75_TERROR50S + scripts/shelter-lock.sh 93 94 127 123: hatch locked, burrow
  'Shelter' 84 tiles with all 50 citizens, room stockpile without refuse/corpses). Re-read of X7v75d first: its killers rose OUTDOORS
  (~139,72) and walked down the hatched stair (93,94 z127->126); dwarves going out to haul corpses held the hatch open.
- Result: OK PASS, full year (to y251 Spring), 677 managed arrivals, 0 off-cast late, 0 in-cast/gate send-offs, reserve kept, 0 hangs,
  103 t/s. Only failed check is the soft 'ocean on the map' (frozen at embark), as in X7v75d.
- Nothing came through the hatch. But citizens 50 -> 55 (migrants, stuck outside) -> 32. Cause: the fort's own animals were sealed in
  (2 horses, 2 dogs, cow, 2 cats in the room). A stray horse starved at 100,944,274; HORSE undead appeared at 91,93,123 at 100,997,774
  and 11 citizens were found dead by 101,000,274. Dwarves dying in the room then rose (DWARF kind 'other' ARRIVE inside, struck down by
  citizens ~100 ticks later). 3 ghosts, 4 lost to stress (2 mad, 2 melancholy; one mad peasant died of thirst -- sustain only waters
  citizens). Surface dwarf deaths are migrants who arrived outside the locked hatch.
- PENDING: take the animals out of the shelter before sealing (to the surface or off the map), so nothing in the room can die and rise.
