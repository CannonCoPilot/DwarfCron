# Seasonal Wildlife alpha trial two (UI, v6.6)

- Tester: W2:Urist (the rig, driven by scripts/alpha2-run.py)
- Fort: BOATS (the rig's copy of the alpha one fort, restored from BOATS.preverify)
- Game / DFHack / plugin: 53.16 · 53.16-r1.1 · v6.6.0 @ f22fa30
- Date: 2026-09-28 (run 20260928-141723)

Tally: 4 pass · 2 anomaly · 0 skipped · 56 unmarked of 62 steps.

## Anomalies
- **4.3 Odds for one row**: ALBATROSS_MAN: row now 'ALBATROSS_MAN    prey     small  wbird OCE.TRO   AuWi    0      -    Y   matrix Sp36'.
- **10.1 The pyramid**: 5 tiers, top 'VORACIOUS_CAVE_CRAWLER', base 'Summer --'; aquatic chain lines: 2, e.g. 'RIVER OTTER ---->    PANGOLIN,    FLY_ACORN,    HAMSTER,    RAT'.

## Passes
- **0.1 Choose the fort**: BOATS (the rig's copy of the alpha one fort) restored from BOATS.preverify and loaded: 29 citizens, year 100 Summer, water tiles 9376 (river 7966, ocean 1410; salt 9087, fresh 289), caverns found 0
- **2.3 Make a species inactive**: AARDVARK: allow True -> False, seasons SpAu -> none; row now: 'AARDVARK         prey     small  land  SHR.TRO   -       0      -    -   you Su24'.
- **2.4 Make it active again**: AARDVARK: active True, seasons Sp (1).
- **17.1 Save, quit, reload**: saved to the new folder A2R141723 and loaded it back: True; AARDVARK still inactive; 0 stock setting(s) kept: True; ledger's last line survived: True.
