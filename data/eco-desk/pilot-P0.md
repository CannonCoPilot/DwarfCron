# P0 pilot (29 Sep 23:5x, CTRL fresh load y2 t16800, tool v6.7.0 deployed; CLI lacks stock/odds (v6.8 only))
- `seasonal-wildlife place KANGAROO 6 land` / `place DINGO 6 land` -> placed, but SCATTERED across the map (x 6..183, y 3..161), not grouped.
- 5074 ticks: dingo 149 killed a native GROUNDHOG (unit 152). Kangaroos untouched.
- Records of a fight: incident (world.incidents.all) type Death, victim 152, killer (criminal) 149, death_cause BLEED;
  unit.reports.log[0] (Combat) of 149 = 78 report ids; reports.last_year[0]=2; world.status.reports COMBAT_STRIKE_DETAILS/_2,
  COMBAT_EVENT_LATCH_GENERAL ("The dingo shakes the groundhog around by the head..."); status.announcement_alert: type COMBAT,
  report_unid = {149 DINGO, 152 GROUNDHOG}, categories Combat.
- eventful.onUnitAttack exists (plugins.eventful loads).
- announcements.txt (prefs): COMBAT_* types carry A_D:UCR (no D_D -> not in the fort announcement list, but unit combat reports + COMBAT alert still appear). Per-type only: no animal-vs-animal switch.
- Implications: predation metric = Death incidents with (killer race, victim race) + combat-log counts per unit; placement for pair tests must be custom (teleport both groups to adjacent tiles), not `place`.
