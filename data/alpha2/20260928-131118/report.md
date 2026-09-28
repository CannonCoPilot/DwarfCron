# Seasonal Wildlife alpha trial two (UI, v6.6)

- Tester: W2:Urist (the rig, driven by scripts/alpha2-run.py)
- Fort: BOATS (the rig's copy of the alpha one fort, restored from BOATS.preverify)
- Game / DFHack / plugin: 53.16 · 53.16-r1.1 · v6.6.0 @ f22fa30
- Date: 2026-09-28 (run 20260928-131118)

Tally: 51 pass · 11 anomaly · 0 skipped · 0 unmarked of 62 steps.

## Anomalies
- **2.3 Make a species inactive**: AARDVARK: allow True -> False, seasons SpAu -> none; row now: 'Ecosystem balanced.   [AARDVARK: eaten by GIANT_COUGAR,...]'.
- **3.3 Set its stock**: GIANT_SPERM_WHALE: prompt did not open; stock line now 'FLY_ACORN        vermin  stock       0 in the region, 40 come back in season (you set it)'.
- **3.6 Call a wave**: the driver failed at this step: KeyError: 'allow'
- **4.3 Odds for one row**: ALBATROSS_MAN: row now 'Ecosystem balanced.   [ALBATROSS_MAN: eaten by GIANT_COUGAR,...]'.
- **5.1 Every tool asks**: Matrix assign: asked; Co-align: asked; Fill to targets: did not ask; Fill natural prey: asked; Fill natural predators: asked. Answering No left the roster unchanged.
- **7.1 Reset the roster**: the driver failed at this step: KeyError: 'stock'
- **7.2 Reset everything**: the driver failed at this step: KeyError: 'stock'
- **10.1 The pyramid**: Levels shown: prey, vermin.
- **16.1 Inactive stays away**: the driver failed at this step: KeyError: 'allow'
- **16.2 The boundary itself**: announcement: 'none in the last 20'; ledger season line: present.
- **17.1 Save, quit, reload**: the driver failed at this step: KeyError: 'stock'

## Passes
- **0.1 Choose the fort**: BOATS (the rig's copy of the alpha one fort) restored from BOATS.preverify and loaded: 29 citizens, year 100 Summer, water tiles 9376 (river 7966, ocean 1410; salt 9087, fresh 289), caverns found 0
- **0.2 Back it up**: The copy is BOATS.preverify, byte-restored before loading (the rig's save-restore checks the tree hash); the live region7 game is not touched.
- **0.3 Turn on the frame counter**: Baseline with the tool as saved: 3040 ticks in 14s = 217 ticks per second (tick cap 1000, graphics cap 10).
- **1.1 Open the window**: Title and nine tabs present; Overview blocks present; non-ASCII in the window: none.
- **1.2 Read the Panel**: 19 switch rows (15 on); JOBS table present; frame-rate line present. Off by default: Layer: deep, Livestock as prey, Vermin hunting, Map overlay.
- **1.3 Read the job timings**: Every fuse intact. season roster worst 65 ms over 2 of 302; groups and gate worst 196 ms over 38 of 424; ecology worst 149 ms over 20 of 115. Worst passes above the 50 ms budget are the known open item (X7).
- **1.4 All off, then all on**: Both asked first: True. Before {'eco': True, 'enabled': True, 'held': 21}; after All off {'eco': False, 'enabled': False, 'held': 0}; after All on {'eco': True, 'enabled': True, 'held': 20}.
- **2.1 Read the new columns**: Columns all present; header: '13 special left to DF'.
- **2.2 Filters**: View: Default -> ? -> Current; Cat: predator; Biome: ?; Season: Spring. The window was reopened to reset the filters.
- **2.4 Make it active again**: AARDVARK: active True, seasons Sp (1).
- **2.5 Cycle seasons**: ALBATROSS_MAN: AuWi -> Sp -> Su -> Au -> Wi -> SpSuAuWi -> Sp -> Su -> Au.
- **2.6 Try to remove the last season**: ALBATROSS_MAN on Autumn: pressed its key; seasons after Au; refusal on screen: True.
- **2.7 Cycle the layer**: Land (Alt+L) -> Water (Alt+L) -> Cavern (0 found) (Alt+L) -> Deep (layer off) (Alt+L) -> All layers (Alt+L). No macro recording started (Alt+L is not a DF key).
- **3.1 Open the detail**: GIANT_SPERM_WHALE: body 'adult 200,000,000 cm3, large' (the D4 band for that volume is large); rows present: habitat, role, body, stock, odds, group size, seasons, eats, eaten by.
- **3.2 Habitat and role come from the raws**: ORCA aquatic predator large; GIANT_ORCA aquatic predator large; BIRD_ALBATROSS waterbird prey small; DINGO land predator small.
- **3.4 Set its odds**: GIANT_SPERM_WHALE: odds line now 'GIANT_ALBATROSS  prey    odds        weight 20, 6% of the land layer (if it were in season) (you set it)'.
- **3.5 Set its group size**: GIANT_SPERM_WHALE: group size line now 'GIANT_CHEETAH    predat  group size  2 (you set it)'.
- **4.1 Stock for one row**: AARDVARK: prompt opened; stored stock 55.
- **4.2 Stock for the filter**: Cat filter 'predator': 67 species set to 44; outside the filter: none.
- **5.2 Matrix assign**: 73 active; per season {'Sp': 21, 'Su': 20, 'Au': 19, 'Wi': 17} (half is 36); with no season 0; all four 0; WHY on screen: matrix, pair.
- **5.3 Co-align**: 68 season cell(s) added; species on all four seasons 0 -> 0 of 73; any season removed: none.
- **5.4 Fill natural prey and predators**: Y activated 0, D activated 2, of 62 inactive before. Ledger: y100 Summer 28 edit      -       fill natural prey: 0 species activated for partners that  | y100 Summer 28 edit      -       fill natural predators: 2 species activated for partners 
- **5.5 Category targets**: Shift+P twice: target line 'prey: 2'; header shows Thin/balanced; Alt+F with Cat 'prey': prompt opened (cancelled).
- **6.1 Dry run**: the Dry-run season table (Sp Su Au Wi) opened; roster unchanged: True.
- **6.2 Apply now**: Announcement: 'Summer wildlife applied (85 active).'.
- **6.3 Send off and next**: wild land units still tied to their entry: 8 -> 0.
- **6.4 Rotation off and on**: rotation True -> False -> True; header 'rotation off' then 'rotation ON'.
- **8.1 Add invasive**: AARDVARK_MAN: on this embark after the add: True; active None seasons none. Ledger: y100 Summer 28 ecology   -       18 pair(s) for 5 predator(s) x 34 target(s); 2  | ledger: 3 of 258 recorded shown
- **9.1 Read it**: Four season columns: True; + and . marks drawn: True.
- **9.2 Edit from the grid**: cavern:BIRD_SWALLOW_CAVE_GIANT: Spring added (SuAuWi -> SpSuAuWi); header 'BIRD_SWALLOW_CAVE_GIANT: All'; removing AARDVARK_MAN's last season here refused: True.
- **10.2 Diet follows habitat**: Land predators eating aquatic species on this roster: none; fliers eating aquatic non-vermin: none.
- **10.3 The four modes**: G, G, L gave graph -> by season -> by layer; N shows a season: True.
- **11.1 Origins**: Origins DF wave 18, resident 8, untracked 18, deep 36 (sum 80); wild on the map by probe 80; lines present: ecology:, limits:, fuse:.
- **11.2 Groups**: 'Groups: ON   2 at once   gap 1-2 days   released 7   departed 25'; 15 group row(s), first 'cavern2:CRUNDLE x1 gated (day 36)'.
- **11.3 Hold and send off**: CRUNDLE: after Q 'held N more days' shown True; after X 'dismissed' shown True.
- **11.4 Follow and centre**: CRUNDLE: follow unit 2777; after Enter the view is at {'x': 66, 'y': 34}.
- **11.5 Herds and packs**: 9 tracked species: CRUNDLE herd, CROCODILE_CAVE school, TROLL pack, BIRD_KESTREL flock, CAVY herd, ELK_BIRD herd, PLUMP_HELMET_MAN school, POND_GRABBER school; every one has a reason.
- **12.1 Read the table**: Columns LAND, WATER, CAVERN, DEEP; 10 of 10 rows; drawn by: DF (gated)         the tool (engine)  DF (gated)         DF (frequency).
- **12.2 Change a limit**: land groups at once 2 -> 3; ledger: ledger: 2 of 262 recorded shown  kind=edit.
- **12.3 The water line**: 'water: draws on  0 of 2 group(s) at once, 5 of 5 animals; water ocean 1410 river 7966  (salt 9087 / fresh 289); next draw due' (the fort has 9376 water tiles).
- **12.4 Caverns**: cavern 1: not yet found  (nothing shown until your dwarves reach it); cavern 2: not yet found  (nothing shown until your dwarves reach it); cavern 3: not yet found  (nothing shown until your dwarves reach it)
- **13.1 Families**: Families: fish, flies, fliers, mammals, crawlers.
- **13.2 Open a family**: 2 species rows under the family: cavern:FISH_CAVE, cavern:LOBSTER_CAVE.
- **13.3 Edit one vermin species**: Shift+W on cavern:FISH_CAVE: stock set on ['cavern:FISH_CAVE'].
- **13.4 Vermin hunting on**: switch on: True; castes flagged: ALBATROSS_MAN:DIVE_HUNTS_VERMIN, BIRD_EAGLE:DIVE_HUNTS_VERMIN, BIRD_OSPREY:DIVE_HUNTS_VERMIN, BIRD_SWALLOW_CAVE_GIANT:DIVE_HUNTS_VERMIN, CRUNDLE:HUNTS_VERMIN, GIANT_EAGLE:DIVE_HUNTS_VERMIN, GIANT_OSPREY:DIVE_HUNTS_VERMIN, GREMLIN:HUNTS_VERMIN, HONEY BADGER:HUNTS_VERMIN, HUNGRY_HEAD:DIVE_HUNTS_VERMIN. Behaviour over the boundary is watched in 16.1.
- **14.1 Filter the ledger**: counts 200 of 265 recorded -> 171 of 265 recorded -> 23 of 265 recorded; Kind edit, Layer land.
- **14.2 Undo**: three edits on ['AARDVARK', 'AARDVARK_MAN', 'ALBATROSS_MAN'] (3 changed); after three Z all back as before: True; undo ring now holds 41; the tab says 'fifty deep': True.
- **14.3 Help on every tab**: Alt+H opened a help page with the vocabulary on every tab.
- **15.1 Turn it on**: Enabled by DFHack's overlay command (the control-panel menu is the player's route to the same switch): 'enabled widget seasonal-wildlife.groups'; predator-prey links it would draw now: 0. Left enabled until 17; disabled at the end of the round.
- **16.3 Water groups**: 3 water draw(s) in the ledger, e.g. 'y100 Summer 63 arrive    water   HIPPO x3 drawn into the river (salt); stock 270 -> 267'; drawn groups on the map now: HIPPO 1/1 here, 1 in water (river, salt), HIPPO 3/3 here, 3 in water (river, salt).
- **17.2 Frame rate on and off**: tool on 189 t/s, all off 203 t/s (+7% of the off rate; one reading each, so within the 10-15% load noise). FPS1 measures this with two runs per arm.
