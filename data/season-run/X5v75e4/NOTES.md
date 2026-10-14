# X5v75e4 notes (13 Oct 2026)

Sheltered 50-dwarf evil coast (V75_EVIL50S), full year y100 Spring 54 -> y101 Spring 17, engine sw 6b74260 (walker fix + land pause). OK, 1 hang (reloaded), 132.5 t/s.

- Land pause: 62 pause/resume lines, 0 land send-offs. First pause y100 Spring 57 (6 of 5 groups, 57 entries closed); one groundhog arrived the next day (a wave already in flight), none after during the pause; resumed Spring 65 at 4 of 5 and two groups (GROUNDHOG x2, BIRD_KIWI) walked in the same day -> 6 of 5 again (reopening every entry at once lets DF send from more than one source in a pass).
- Gate send-offs 132: all cavern (the cavern trim; the cavern pause was not yet written).
- Verdict FAIL = one criterion, "every dismissed group off the map within 10 days": BIRD_EMU group (units 13913, 13916; a DF wave that arrived a day before winter, sent off at the season change). Checked live on chunk save c017: both alive, flagged, leave_countdown 0, and UNDEAD (dfhack.units.isUndead true) -- raised by the evil coast's weather. V7.natural excludes the undead, so the leave check (fired at day 7, vanished set) took none off. Not a tool defect; the recorder now writes undead wildlife as kind 'undead' (outside wild/wild-group) so the analyser no longer scores them.
- Fort alive all year in the shelter (past the summer ash that lost X5v75e/e2).
