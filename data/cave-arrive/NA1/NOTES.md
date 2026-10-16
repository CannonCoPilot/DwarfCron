# NA1 never-arrive test (15-16 Oct 2026) -- V75_SMALLSAV, control DRALTHA, F50 Q100, cavern 1 (MANERA cavern 2)

User 15 Oct: test why 15 cast cavern species never arrived in 16 fort-years; cover every no-show incl. all sentients.
Design: scripts/cave-arrive.py + chronicler/dfhack/scripts/cx-cavearrive.lua; DF restarted and fort loaded fresh per subject, tool disabled, never saved.

Result: all 9 cave animal people + manera arrive on equal footing (5-11 v 5-10). DRUNIAN, GREMLIN, MOLE_DOG_NAKED, MOLE_GIANT,
RAT_GIANT, RAT_LARGE never drawn (0 v 14-16, no stock debited, p<=1.2e-4). The six are exactly the cavern species with thief tags
(CURIOUSBEAST_EATER/GUZZLER/ITEM; gremlin MISCHIEVOUS/LOCKPICKER/TRAPAVOID); none of the 31 arrivers carries one.
Animal people's real-run absence = odds: one engine-created cave entry (template tile) at FREQUENCY ~1-2 v 10-20 DF entries.
Note: debit metric is net per step (refunds from vanished units offset), so it undercounts; zero debit with zero units is still clean.
Side note: waves of DEMON_* at depth 5 and magma crabs at depth 4 appeared and were vanished (unsaved fort).
