# never-arrive OOR3: V75_SMALLSAV, control ELK_BIRD, FREQUENCY 50, quantity 100

| subject | cavern | subject waves | control waves | share | p (v 0.5) | stock debited (subject / control) | ticks | verdict | other waves |
|---|---|---|---|---|---|---|---|---|---|
| BAT_GIANT | 3 | 9 | 7 | 0.56 | 0.804 | 7 / 44 | 46000 | arrives on equal footing (no bar: absence was odds) | {'POND_GRABBER@2': 1, 'MAGMA_CRAB@4': 8, 'DEMON_52@5': 6, 'CROCODILE_CAVE@1': 9, 'DEMON_7@5': 7, 'DEMON_51@5': 4, 'TROGLODYTE@2': 5, 'TOAD_GIANT_CAVE@1': 10, 'GORLAK@3': 1, 'TROLL@2': 1, 'CRUNDLE@2': 6, 'DEMON_40@5': 3, 'DEMON_42@5': 1, 'TOAD_GIANT_CAVE@2': 4, 'CRUNDLE@3': 2, 'DEMON_26@5': 4, 'PLUMP_HELMET_MAN@2': 2, 'TROLL@3': 1, 'OLM_GIANT@1': 6, 'DEMON_1@5': 2, 'OLM_GIANT@2': 1, 'GORLAK@2': 1, 'VORACIOUS_CAVE_CRAWLER@3': 1, 'CROCODILE_CAVE@2': 2, 'IMP_FIRE@4': 1, 'MOLEMARIAN@2': 1, 'REACHER@2': 1, 'BLIND_CAVE_OGRE@2': 1} |
| TOAD_GIANT_CAVE | 3 | 8 | 8 | 0.50 | 1 | 7 / 55 | 28000 | arrives on equal footing (no bar: absence was odds) | {'DEMON_26@5': 4, 'DEMON_7@5': 1, 'OLM_GIANT@1': 8, 'CRUNDLE@2': 5, 'DEMON_51@5': 4, 'MAGMA_CRAB@4': 6, 'PLUMP_HELMET_MAN@2': 1, 'REACHER@2': 1, 'DEMON_42@5': 3, 'POND_GRABBER@2': 1, 'TOAD_GIANT_CAVE@1': 3, 'DEMON_40@5': 4, 'VORACIOUS_CAVE_CRAWLER@3': 1, 'RUTHERER@3': 1, 'CROCODILE_CAVE@1': 2, 'CROCODILE_CAVE@2': 1, 'JABBERER@2': 1, 'OLM_GIANT@2': 3, 'TROGLODYTE@2': 1, 'SPIDER_CAVE_GIANT@2': 1, 'IMP_FIRE@4': 1} |
| TROGLODYTE | 3 | 6 | 10 | 0.38 | 0.454 | 43 / 72 | 46000 | arrives on equal footing (no bar: absence was odds) | {'DEMON_1@5': 5, 'CAVE_BLOB@3': 2, 'CROCODILE_CAVE@1': 7, 'CRUNDLE@2': 4, 'POND_GRABBER@1': 4, 'DEMON_40@5': 5, 'CROCODILE_CAVE@2': 5, 'OLM_GIANT@1': 9, 'MAGMA_CRAB@4': 7, 'DEMON_51@5': 5, 'TOAD_GIANT_CAVE@1': 6, 'TOAD_GIANT_CAVE@2': 3, 'DEMON_42@5': 4, 'DEMON_52@5': 2, 'DEMON_7@5': 6, 'OLM_GIANT@2': 3, 'IMP_FIRE@4': 1, 'TROGLODYTE@2': 2, 'PLUMP_HELMET_MAN@2': 1, 'TROLL@2': 1, 'REACHER@2': 1, 'SPIDER_CAVE_GIANT@2': 1, 'DEMON_26@5': 1, 'MOLEMARIAN@2': 1} |

Setup and raws:
- BAT_GIANT: SETUP cavern 3: BAT_GIANT and ELK_BIRD each on 6 tile x cave pair(s), FREQUENCY 50, quantity 100; 0 opened, 12 created, 0 failed, 114 other entries closed; 1 wild cavern animal(s) vanished
  - WARN BAT_GIANT raw UNDERGROUND_DEPTH 1:2 excludes cavern 3
  - RAW BAT_GIANT freq 50 (as loaded) cluster 1-1 depth 1-2 pop 20-10 flags LARGE_ROAMING,HAS_ANY_CAN_SWIM
  - RAW ELK_BIRD freq 50 (as loaded) cluster 10-5 depth 1-3 pop 50-25 flags LARGE_ROAMING,HAS_ANY_CAN_SWIM
- TOAD_GIANT_CAVE: SETUP cavern 3: TOAD_GIANT_CAVE and ELK_BIRD each on 6 tile x cave pair(s), FREQUENCY 50, quantity 100; 0 opened, 12 created, 0 failed, 114 other entries closed; 1 wild cavern animal(s) vanished
  - WARN TOAD_GIANT_CAVE raw UNDERGROUND_DEPTH 1:2 excludes cavern 3
  - RAW TOAD_GIANT_CAVE freq 50 (as loaded) cluster 1-1 depth 1-2 pop 20-10 flags LARGE_ROAMING,HAS_ANY_CAN_SWIM
  - RAW ELK_BIRD freq 50 (as loaded) cluster 10-5 depth 1-3 pop 50-25 flags LARGE_ROAMING,HAS_ANY_CAN_SWIM
- TROGLODYTE: SETUP cavern 3: TROGLODYTE and ELK_BIRD each on 6 tile x cave pair(s), FREQUENCY 50, quantity 100; 0 opened, 12 created, 0 failed, 114 other entries closed; 1 wild cavern animal(s) vanished
  - WARN TROGLODYTE raw UNDERGROUND_DEPTH 1:2 excludes cavern 3
  - RAW TROGLODYTE freq 100 (as loaded) cluster 10-5 depth 1-2 pop 30-15 flags LARGE_ROAMING,HAS_ANY_INTELLIGENT_LEARNS,HAS_ANY_CAN_SWIM
  - RAW ELK_BIRD freq 50 (as loaded) cluster 10-5 depth 1-3 pop 50-25 flags LARGE_ROAMING,HAS_ANY_CAN_SWIM
