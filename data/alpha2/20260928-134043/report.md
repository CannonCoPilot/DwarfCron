# Seasonal Wildlife alpha trial two (UI, v6.6)

- Tester: W2:Urist (the rig, driven by scripts/alpha2-run.py)
- Fort: BOATS (the rig's copy of the alpha one fort, restored from BOATS.preverify)
- Game / DFHack / plugin: 53.16 · 53.16-r1.1 · v6.6.0 @ f22fa30
- Date: 2026-09-28 (run 20260928-134043)

Tally: 8 pass · 2 anomaly · 2 skipped · 50 unmarked of 62 steps.

## Anomalies
- **4.3 Odds for one row**: AARDVARK: row now ''.
- **17.1 Save, quit, reload**: saved to the new folder A2RELOAD and loaded it back: True; None still None; 1 stock setting(s) kept: True; ledger's last line survived: False.

## Skipped (and why)
- **2.3 Make a species inactive**: no active land species to select
- **2.4 Make it active again**: no species from 2.3

## Passes
- **0.1 Choose the fort**: BOATS (the rig's copy of the alpha one fort) restored from BOATS.preverify and loaded: 29 citizens, year 100 Summer, water tiles 9376 (river 7966, ocean 1410; salt 9087, fresh 289), caverns found 0
- **3.1 Open the detail**: GIANT_SPERM_WHALE: body 'adult 200,000,000 cm3, large' (the D4 band for that volume is large); rows present: habitat, role, body, stock, odds, group size, seasons, eats, eaten by.
- **3.3 Set its stock**: GIANT_SPERM_WHALE: prompt opened; stock line now 'FLY_ACORN        vermin  stock       0 in the region, 40 come back in season (you set it)'.
- **3.6 Call a wave**: called ELEPHANT; the next land arrival after 1538 ticks: ELEPHANT, ELEPHANT, ELEPHANT, ELEPHANT, ELEPHANT, ELEPHANT, ELEPHANT, ELEPHANT, ELEPHANT, ELEPHANT, ELEPHANT, ELEPHANT.
- **7.1 Reset the roster**: Choice offered: True; confirmation: True; 135 active, 0 with no season, 3 with a second season (the pair guarantee); 1 stock setting(s) kept: True.
- **7.2 Reset everything**: (run last, on the reload copy) confirmation 'Reset everything': True; stock settings left 0; 137 active, 0 with no season.
- **16.1 Inactive stays away**: 91581 ticks stepped, boundary at +71315; 150 wild arrivals (119 of managed species); the species made inactive in 2.3 (None): 0 arrival(s); inactive or out-of-season arrivals: none.
- **16.2 The boundary itself**: announcement: 'Autumn wildlife roster applied.'; ledger season line: present.
