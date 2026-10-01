# ECO findings so far (run data/experiments/ECO/20260929-235553; analysis scripts/eco-analyze.py <run> [block])

P1 (CTRL, 6 pred x 10 prey, 10 tiles apart, 3,000 t, 1 rep):
- DF only (no write): 0 attacks, 0 kills in all 40 cells. DF's own drive never acted within 3,000 t at 10 tiles.
- Written: every LP attacked (up to 306 attacks/cell), kills 1-3 of 10 in most cells; WATER_BUFFALO killed a LION (prey fights back).
- COYOTE (not LP, not BENIGN) acted on the written relation: 343 attacks on DEER, kills 2 RABBIT + 1 DEER. FOX (BENIGN+BONECARN): 0.
  => the drive to act on a written relation is "not BENIGN", not "LARGE_PREDATOR" (memory said LP; T4's badger is BENIGN).
- BEAR_GRIZZLY: 10/60 gone from the map in P1 cells, 6/6 in P2 (no other species lost any). Block B tests why.
P2 (pred vs pred, no write, 3,000 t): 0 attacks in all 8 incl. WOLF x WOLF groups.
T1 (flips, 1 rep):
- LP on COYOTE / off WOLF without write: 0 attacks either way (no drive without the relation in 3,000 t).
- BENIGN on WOLF + write: 0 attacks (control 64 attacks, 1 kill). BENIGN blocks acting on the relation.
- BENIGN off DEER + write: deer attacked wolves 46x and killed 2 wolves.
- FLEEQUICK on DEER + write: 2 attacks (control 64). Suggestive.
- AT_PEACE_WITH_WILDLIFE on WOLF + write: 328 attacks, 2 kills -> the written relation overrides AT_PEACE.
- PRONE_TO_RAGE=1 on DEER: no deer attacks (value 1 too low? not tested higher).
- CRAZED DEER: ignored rabbits, went 30+ tiles to the fort, killed 3 dwarves, all 6 deer killed by dwarves.
  OPPOSED_TO_LIFE DEER: 16 attacks on dwarves, 4/6 killed by dwarves. Both aim at the fort, never at wildlife.
- AMBUSHPREDATOR, NATURAL_ANIMAL off, CURIOUS_BEAST_EATER on WOLF: nothing in 3,000 t.
- MEANDERER off DEER spread 63 vs 44; LOOSE_CLUSTERS on KANGAROO 42.8 vs 36.0 (1 rep; weak).
S (scavenging): S1 corpses x6 beside VULTURE/HYENA/BEAR_BLACK/RACCOON/WOLF/DEER 4,000 t: no corpse moved or held.
  S3 HAUL_REFUSE labor on wolves: no job. S2 path.dest alone (with or without goal SeekStation): nobody moved; eaten 0.
  -> S2 block: walkto (full path) and tp+eat+save/reload.
L1 (leader, 3,000 t): herd DEER spread none 52.5 / lowest-id 1.7 / largest male 3.6; pack WOLF 45.6 / 10.0 / 3.4.
  Leader = cohesion (huge); which member leads made no consistent difference at n=1. Pred cells' kills unrecorded
  (watch after the steps) -> L2 rerun (watch first).
A1 (alert filter prototype, repeat-util every tick, drop COMBAT alerts with no citizen/own-civ/fort-controlled unit):
  wild fight: filter off 1 alert; on 0 alerts, 3 dropped. Fort fight (wolves written against citizens): alert kept.
  Save + reload with the filter on: fine; resumed.
Desk (eco/): T0-triage.tsv, W2-audit.md (ecoWrite ignores eats(): 58% of written pairs fail eats; ocean species realm
  land; 42 tool-'predators' never armed incl 16 BENIGN), Q6-setgroups.md (15 guilds), Q9-realms.md, Q2-scavenger-sets.md
  (23 candidates; pinned rule misses vulture/buzzard/jackal/hyena). Tool never reads BENIGN, LOOSE_CLUSTERS, NO_<season>
  (22 NO_WINTER species can be dealt Winter).
RIG TRAP (for df-rig skill): a newer save of the same fort (DF autosave at a season change, or a scratch save like ECOTMP)
hides the fort in the Continue list ('save list never showed Folder: CTRL'); the list is read once at DF start; save-delete
refuses while that save is loaded. eco-run prunes autosaves of the fort's world before each block and deletes temp saves
after title at block end; restart DF after any such deletion. Chain relaunched 00:3x (attempt 1 lost F1/T2 to this).
S2 (tool-driven scavenging): walkto (a full unit.path.path line + dest + goal SeekStation) moved hyenas 20 tiles: 0/6
  near at +100 t, 3/6 within 3 tiles at +300 t; eat (dfhack.items.remove of corpses within 2) removed 6/6. tp + eat
  removed 6/6; save + reload afterwards: corpses still 0, fort fine, hyenas alive. => "eating remains" = walk + delete, works.
USER ASK 2 (00:30): reason through imposed roster/food-web rules -> draft eco/roster-reasoning.md; prototype agent
  writing eco/roster/{rules.md, roster.py, bizarre.tsv, results.md}.
B (why grizzlies vanish): placed alone 3,000 t: BEAR_GRIZZLY 6/6 gone, BEAR_BLACK 6/6, RACCOON 6/6 (all CURIOUS_BEAST_*);
  grizzly with CURIOUS_BEAST, _EATER, _GUZZLER flags off: 0/6 gone. Gone = df.unit.find nil (removed from the world, not
  inactive/offmap). => curious beasts placed by the tool leave the map within ~3,000 t (DF's curious-beast visit
  behaviour); holding them as residents needs the flags off (species-wide) or re-placement.
L2 (herd 10 DEER + 6 WOLF written, 3,000 t, watch first, 1 rep): no leader 88 attacks, 1 kill (deer spread 69);
  lowest-id leader 1 attack, 0 kills (spread 11.7); largest male 1 attack, 0 kills (spread 41.9). A led herd was
  barely attacked -> cohesion protects prey (a balancing lever); which member leads: no difference seen.
F1 (ECO-F1 run $(ls ECO-F1), CTRL 60k t, tool disarmed, surface released every 1,500 t): 38 surface non-bird waves:
  KANGAROO f100 23 (60.5%; model f/sum 53.5%), PORCUPINE f50 9 (23.7%; 26.7%), WOMBAT f25 5 (13.2%; 13.4%), EMU f12 0
  (6.4% ~ 2.4 expected), BADGER f1 1. Shares proportional to FREQUENCY (wiki's uniform-pick + d100 accept) -> a clean
  balancing lever for the land/surface pick. (Fliers, caverns, deep are separate pools: 13 bird, 11 cavern, 3 deep waves.)
ROSTER PROTOTYPE (eco/roster/results.md; 68,000 webs, 7 embarks x 7 layers x 4 seasons x 20 seeds x 34 variants):
  caps never reached (step 4 needs a no-progress stop; per-layer caps); tool size bands make wolf/dingo/hyena/cougar/
  cheetah 'small' -> rule B makes them vermin-eaters; bands too coarse (5,756 pairs prey >=3x predator; ratio test ->
  601); only 43% of surface predator links DF-actable (vermin targets or BENIGN predators); 'high value' = giants
  (PETVALUE 500) in 75-100% of seeds; animal people 37-44% of surface pools, 30% of predator slots sentient; rule D
  (tag AND size) leaves cavern sentients uneaten (95% cav1); rule E strands large prey (13% flying webs single-species);
  step 6 connected none of 102 isolated nodes; pack bonus matters (isolation 6% -> 24% without); seed overlap 0.17;
  deep = always fire imp + magma crab; bizarre score r=0.49 with UNDERGROUND_DEPTH (3.3/5.1/8.7); cut with depth
  ceiling 25/32/21 candidates. Fixes 1,3-8 -> isolation 2%, pack/herd 71-75% (land 91%), DF-actable 77%, mutual 0%.
  Fix list: per-layer caps + stop guard; seed must have >=1 relation; eats() ratio not bands; D by LP tag; no BENIGN in
  predator slots; sentients never eat; pred-on-pred only if >=2x size; weight picks by FREQUENCY, giants not 'high value';
  vermin links = tool stock changes. DF limits: water-layer units unwritten by ecoWrite; one LP group per map (webs
  average 1.6 LPs -> tool must place the extra).
T2 (CTRL, 45k t, 1 rep/arm, surface non-bird waves): nospring_KANGAROO (f100 + NO_SPRING caste flag, others 1, spring):
  0 kangaroo of 19 waves (F1 without the flag: 60%) -> DF honours NO_<season> at the pick, set at run time.
  ubiq_WOMBAT (f5 + UBIQUITOUS, porcupine f5, others 25): wombat 0/13; ubiq_PORCUPINE: porcupine 0/23 -> UBIQUITOUS set
  at run time is NOT read at the fortress pick (would be ~40% if it acted as f100); its wiki role is worldgen territory.
N1 (CTRL 60k t): KANGAROO f100 entry 3: one wave of 3 at +2,400 t took the entry 3 -> 0 at arrival (debit), all killed;
  no kangaroo wave afterwards (extinct flag stayed FALSE: quantity 0 alone gates). Hook (entry==0 -> WOMBAT f100 +
  stock 500) fired at the next 1,500 t pass; first wombat wave +2,090 t later; wombats 27 of the next 29 surface waves.
  => exhaustion detection = entry quantity, not the extinct flag; niche replacement takes effect within ~2k ticks.
G1 (tool on, preset, 40k t, 1 rep; surface groups = distinct species x population per 1,500 t sample):
  4x4 limit 3: mean 1.75 max 2, 16 arrivals, 438 t/s; limit 5: mean 2.56 max 4, 20 arrivals, 402 t/s.
  6x6 limit 3: mean 2.04 max 3, 66 arrivals, 278 t/s; limit 7: mean 2.92 max 3, 46 arrivals, 285 t/s.
  => raising the limit adds ~1 concurrent group; DF's supply keeps it well under 5/7; speed cost within noise.
  sqrt(embark)+1 is safe and cheap but not a strong lever by itself (arrivals are supply-limited).
DEPTHL (LAKE 192x192): 31,047 water columns (84%): depth 1: 28,150 (91%), 2: 1,563, 3: 1,334, >=4: 0. Lakes are shallow.
W1L (LAKE shore 129,96,95; 5 pred x 8 prey same centre r5, pred/prey medium as named; 3,000 t; 1 rep): all DF-only arms 0.
  Written: ALLIGATOR(water)xDEER(land) 5/8 killed; ALLIGATOR(land)xDEER 2; ALLIGATOR x CAPYBARA 5/8; ALLIGATOR x PIKE
  (both water) 7 attacks 0 kills; CROCODILE_SALTWATER(water)xWATER_BUFFALO(land) 4/8 (338 attacks); FISH_LAMPREY_SEA
  (aquatic) x DEER(land) 0 attacks; WOLF x PIKE 0; WOLF(land) x CAPYBARA(water): capybara (not BENIGN) killed all 5
  wolves (132 vs 20 attacks); LION x CAPYBARA 3 kills, 1 lion killed.
  => amphibious predators cross the boundary both ways; aquatic (IMMOBILE_LAND) predators never leave water; land
  predators never enter water after fish; non-BENIGN prey can reverse the relation. The tool's 'water layer excluded
  from ecology' loses real amphibious predation (alligator/croc are water-biome, drawn/placed as water-layer units).
W1O (OCEAN2 shore 114,96,93; 1 rep): DF-only arms 0 (penguin/bear df arm: 2 penguins dead, bears gone 2 - not spawned killers).
  Written: SHARK_BLUE(water) x HARP_SEAL(land) 1 kill, 53 attacks (only seals that entered water); x HARP_SEAL(water) 4/8;
  x DEER(land) 0 attacks. SHARK_TIGER x FISH_MILKFISH 5/8 killed, 1 shark killed by milkfish. BEAR_POLAR x HARP_SEAL(land)
  2 kills then all 5 bears left the map (curious beast); BEAR_POLAR x BIRD_PENGUIN(in water) 0 attacks.
  SEA OTTER's raw id has a space ('SEA OTTER') -> verbs cannot name it; rerun as LEOPARD_SEAL.
  => aquatic predators take amphibious prey only in water; land predators never enter water; ocean species should not
  be realm 'land' in the tool's ecology (sharks written against deer do nothing).
O (OCEAN2 depth): 21,328 water columns: depth 1: 9,116, depth 2: 12,212, depth >=3: 0. The fortress-map ocean is 1-2
  levels deep everywhere. SHARK_WHALE x2 + SHARK_BLUE x3 placed in it: all alive, wet, moving (spread 13 / 43) after 3,000 t.
  => there is no deep water on this ocean embark; a deep/shallow split cannot key on column depth here (maybe distance
  from shore / ocean share of the map / region ocean tiles instead). BOATS and OD pending.
== ECO2 (30 Sep, run data/experiments/ECO/ECO2-*) ==
CURIOUS mechanism (BOATS trace, interactive): placed RACCOON goal WildernessCuriousStealTarget -> walked ~35 tiles to the
  fort's wagon pile (306 items), took 1 item (a rope), leave_countdown 199,600 -> 0, goal SeekStation to the map edge,
  walked off with it -> removed from the world. Grizzlies on BOATS wandered (MarauderMill) 2,400 t, no theft.
CB (CTRL, raccoons 12 tiles from a citizen, 3,000 t): default 4/4 gone; leave_countdown+goal reset every 300 t: 4/4
  gone anyway; CURIOUS_BEAST* flags off: 4/4 stay (wandering). => remedy = clear the flags species-wide while resident.
A2 (humanoid alert filter, CTRL): WOLF x DEER written: 3 dropped, 0 left; WOLF_MAN x DEER: kept (1, 0 dropped); GOBLIN x DEER: kept.
TV (CTRL, 10 tiles apart, 1 rep): control WOLF x DEER written 0 attacks (P1 273, T1 64) -> encounter noise dominates at 1 rep.
  PRONE_TO_RAGE on DEER (written wolves): 25 -> deer 17 attacks, 1 wolf killed; 50 -> 81, 1; 100 -> 98 attacks, 4 of 6
  wolves killed, 0 deer lost. Dose-response. VIEWRANGE 5/40 (1 vs 156 attacks), VISION_ARC narrow (89), FLEEQUICK r2
  (34 attacks, deer killed 2 wolves) -> inconclusive under the noise. GIANT_FOX written: 0 attacks; BENIGN off: 1.
  Vermin cells vacuous (0 vermin within 12 tiles of the spot). -> redo values co-located (same centre) x2 reps; vermin at
  a vermin-dense spot.
HC1 (BOATS cavern 72:64 z71, 3,000 t, 1 rep): caverns fight WITHOUT a written relation, unlike the surface (P1 df 0/40).
  TROLL x GORLAK df-only: 143 / 141 attacks, 0 kills; written: 180 / 107, trolls 4 dead, gorlaks 5 dead.
  TROLL x ELK_BIRD df-only: 4 attacks, 1 kill; written: 15, 4 kills. TOAD_GIANT_CAVE x ELK_BIRD df-only 0; written 9, 2 kills.
  BENIGN ON TROLL does NOT pacify it (df 85 troll attacks, written 57) -- surface BENIGN wolf made 0. Trolls/gorlaks fight
  as hostiles, not as predators; BENIGN is not the switch for them.
  Leaders (10 GORLAK): spread none 33.0 / lowest 9.3 / largest male 7.5 -> cohesion replicates underground. With 5 written
  TROLL: gorlaks killed all 5 trolls in every arm (led or not) -> the gorlak herd outguns its 'predator'.
  corpses x TROLL / RAT_GIANT 4,000 t: 0 held, 0 moved (surface result holds). walkeat_TROLL (460 t by design): walkto moved no
  troll within 3 tiles in 400 t (0/5 twice; surface hyenas 3/6) -> the cavern path failed; eat still removed 15 corpses
  that lay within 2 tiles of trolls (the cavern holds 70+ old corpses) -> walk-and-delete needs a path check underground. rage50 GORLAK: gorlak attacks 10 (written control 107) -> no rage effect
  at n=1 against trolls. Cavern vermin cells vacuous (vermin total 0-1) -> VRC (vspot) decides.
HC2 (BOATS cavern 2, 63:59): same as HC1 -- cavern hunting needs no written relation.
  TROGLODYTE x ELK_BIRD df-only: 101 attacks, 2 kills (trogs also 48 on each other); written: 36 attacks, 1 kill.
  VORACIOUS_CAVE_CRAWLER x CRUNDLE df-only: 8/8 crundles killed; written: 7/8. The write adds nothing underground.
  Leaders (8 TROGLODYTE): spread none 40.6 / lowest 5.2 / largest male 2.9.
  (HC3 overturns 'the write is redundant underground': see HC3.)
HC3 (BOATS cavern 3, 46:38): DF-only 0 attacks in both pairs; written: JABBERER x REACHER 7/8 reachers killed;
  BLIND_CAVE_OGRE x RUTHERER 3 killed. => native cavern fighting is species- or spot-dependent, NOT a cavern rule: keep
  the cavern relation write. Native fighters seen: TROLL, GORLAK (BENIGN + CAN_SPEAK!), TROGLODYTE (also each other),
  VORACIOUS_CAVE_CRAWLER x CRUNDLE (crundle not BENIGN, fought back); not: JABBERER, BLIND_CAVE_OGRE (CAN_LEARN, EVIL),
  TOAD_GIANT_CAVE. No single token separates them (CAN_LEARN on ogre too; NATURAL on both sides). Caverns 1-2 hold
  native wildlife that may start fights (spot) -- untested; n=1.
HCP (BOATS cavern pool 63:38 z60): cavern pools behave like surface water (W1L/W1O).
  CROCODILE_CAVE from the pool x ELK_BIRD on land: df 1 kill (7 attacks); written 5/8 killed -> amphibious crosses out.
  OLM_GIANT (pool) x CRUNDLE: df 0; written 8/8 crundles killed (crundles fought back 50 attacks).
  POND_GRABBER (aquatic; 5/5 stayed wet) x GORLAK: df 0, written 1 attack -> aquatic predators never leave cavern water.
  CROCODILE_CAVE x GORLAK (both land): df 98+50 attacks (gorlak a native fighter again); written: all 8 gorlaks killed.
  corpses beside a pool croc: 0 held/moved.
  => MODEL.reaches' habitat rules hold underground unchanged; cavern-pool species belong with the water rules (the
  user's 'cavern edge water = water layer'), gated by DF's cavern pick.
HR (RIVER4, 3,000 t, 1 rep): DF-only 0 attacks in every pair -> the surface rule (P1) holds on rivers.
  Written: SHARK_BULL x FISH_PIKE 8/8 killed (150 attacks); FISH_LAMPREY_SEA x PIKE 590 attacks, 0 kills (lamprey
  latches, never kills in 3,000 t -> not a real predator for the web's accounting); ALLIGATOR(water) x DEER 1 kill (17);
  WOLF x BEAVER 1 attack (beavers stayed ashore); WOLF given CAN_BREATHE_WATER + CAN_SWIM_INNATE x PIKE: 2 attacks,
  0 kills -> swim flags do not make a land predator fish.
  Schools: 10 PIKE spread none 47.3 / lowest 2.4 / largest male 4.3 -> cohesion works in water too.
  River vermin cells vacuous (1-2 vermin) -> VRR (vspot).
HO (OCEAN2 shore, 1 rep, written relations only):
  ORCA x HARP_SEAL (orca BENIGN in the raws): 0 attacks; with BENIGN cleared: 45 attacks, 4 of 8 seals killed ->
  BENIGN blocks even a curated apex; the apex boost must clear BENIGN (desk v2's 20 BENIGN apexes), as T1 showed on land.
  SHARK_BLUE made BENIGN x HARP_SEAL: 0 (seals stayed ashore, wet 0).
  Schools: 10 MILKFISH spread none 47.2 / lowest 2.1 / largest male 2.0. With 5 written TIGER sharks: killed 5 / 10 / 1
  -> in water a tight school is no protection (unlike the led deer herd, L2); n=1.
  VIEWRANGE on the prey: 5 -> 7 of 8 milkfish killed; 40 -> 4 of 8 (longer sight, fewer caught; direction as expected, n=1).
  corpses_SHARK_GREAT_WHITE / walkeat_SHARK_BLUE: 0 units placed (radius-2 water spawn found no tiles) -> vacuous.
HL (LAKE shore): 10 FISH_CARP spread none 34.3 / lowest 1.8 / largest male 2.3. Vermin cells (duck, peregrine, control)
  vacuous. corpses_ALLIGATOR (2 placed): 0 held/moved; walkeat_ALLIGATOR placed 0 -> vacuous.
ECO2-FC (CTRL, tool disarmed, 60k t, released every 1,500 t, 1 rep; 143 cavern waves after the first sample):
  FREQUENCY steers the cavern pick in proportion, PER CAVERN LAYER (each layer draws its own pool, gated by
  UNDERGROUND_DEPTH). Cavern 1 (cave 8): giant cave swallow f100 42 of 49 (others f1). Cavern 2 (cave 13): blind cave
  ogre f50 33 of 49 (swallow, depth 1:2, never came there). Cavern 3 (cave 25): ogre f50 21, blood man f25 10, cave blob
  f12 7 -> 55/26/18% of the named vs 57/29/14% predicted; the f1 species 7 of 45. Waves split evenly across the three
  layers (49/49/45) -> the layer is picked first, then the species within it.
  => FREQUENCY is the cavern balancing dial too; the tool's cavern ceiling-by-frequency (addendum 53) acts on a real lever.
ECO2-G (fresh 7-dwarf embarks FPS2E1..E6, tool on + preset, 40k t, 2 reps; groups = distinct species x population among
  live wild units per 1,500 t sample; limit default land 3 / cavern 2 vs sqrt(embark)+1 = 2,3,4,5,6,7):
  surface groups at once, mean (reps): 1x1 1.98 vs 1.77 (limit 2); 2x2 1.98 vs 2.09 (same limit 3); 3x3 1.76 vs 1.94;
  4x4 2.71 vs 2.60; 5x5 2.16 vs 3.28; 6x6 2.69 vs 3.46. At 5x5/6x6 every root+1 rep (3.16-3.81) beat every default rep
  (1.77-2.85) -> the gate binds on big maps (kill criterion 'within 0.5 at every size' FAILS -> the limit matters).
  Surface waves 5x5 4.0 -> 5.5, 6x6 3.0 -> 5.0. t/s no cost (6x6 223 vs 261). Cavern groups unchanged by the cavern
  limit (4.8-8.7, above the limit: residents and ungated sources count) -> the cavern limit is not binding.
  => DEFAULT land groups at once = sqrt(embark)+1 (v6.9); cavern left at 2.
VR (CTRL, vspot surface 134,42,104; 4,000 t, 1 rep): the densest vermin spot is a BUMBLEBEE colony (17,820 in the
  count); cat, peregrine, duck x4 each: count 17,820 -> 17,822 / 17,820 / 17,820 -> no catch visible. A colony is not
  hunted like loose vermin; vspot should skip colony vermin (VERMIN_SOIL_COLONY / hive) -> VR is vacuous for predation.
VRL / VRR (LAKE, RIVER4 vspot): the densest spots were TERMITE colonies (14,539 / 18,943); cat, peregrine, duck x4:
  colony counts unchanged; a fly swarm (145-193) came and went independently -> no catch visible, vacuous.
VRC (BOATS cavern vspot): 1-2 vermin at the spot and the predators failed to place (CAT x0, RAT_GIANT x0) -> vacuous.
  => all ECO2 vermin blocks vacuous: vspot must skip colony vermin and require loose vermin >= ~20 within 12 tiles;
  cavern vermin are sparse (<= 2 near any spot seen). Vermin predation stays untested; rule C remains bookkeeping.
TV2 (CTRL, every cell at one shared spot, 3,000 t, 2 reps; WOLF x6 written against DEER x10 unless noted):
  control: 7 / 3 wolf attacks, 0 kills (wolves barely engage at this spot).
  PRONE_TO_RAGE on DEER 25: deer 18 / 36 attacks, 2 / 1 wolves killed; 100: 98 / 94, 4 / 4 wolves killed -> REPLICATED dose.
  VIEWRANGE on DEER 5: 168 / 7 wolf attacks (3 / 0 kills); 40: 3 / 0 -> longer sight, fewer attacks in both reps.
  VISION_ARC narrow: 5 / 147 attacks; FLEEQUICK: 3 / 158 -> not replicated (T1's 2 vs 64 was noise).
  MEANDERER off (10 DEER alone): spread 71.9 / 64.7 vs control 39.4 / 42.2 -> REPLICATED: off = wider scatter.
  LOOSE_CLUSTERS on (10 KANGAROO): 37.2 / 38.8 vs 41.8 / 40.6 -> no effect.
  GIANT_FOX (BENIGN in raws) x DEER: 0 / 0; BENIGN off: 2 / 10 attacks, 0 / 1 kill -> BENIGN is the switch for giants too.
  GIANT_WOLF x DEER: 11 / 24 attacks, 1 / 1 kill. AMBUSHPREDATOR on WOLF: 0 / 0 (control 0 / 0) -> nothing.
ECO2-W rerun (CTRL set to Winter, tool disarmed, GROUNDHOG FREQUENCY 100 + stock 500, other land species f1; 45k t,
  2 reps; waves after the first sample): natural NO_WINTER: 0 of 42 and 0 of 44 surface waves were groundhogs;
  NO_WINTER cleared: 21 of 32 and 19 of 25. => the raw flag beats any roster/stock/FREQUENCY the tool writes; a
  NO_<season> species dealt that season never arrives by DF's draw (v6.9 fits seasons to the flags).
ECO3 PK (CTRL, n written WOLF vs 4 prey at one spot, 3,000 t, 2 reps; kills of prey / wolves lost, summed over reps;
  attacks rep1/rep2):
  DEER (gate needs 1):   n1 0 (0/0 att)  n3 0 (9/3)   n5 1 (141/0)  n7 1 (144/4)
  ELK (needs 2):         n1 0 (0/0)      n3 0, 2 wolves lost (3/1)  n5 0 (0/1)  n7 2 (4/345)
  MOOSE (needs 4):       n1 0 (1/0)      n3 0 (0/0)   n5 0 (6/158)  n7 1, 2 wolves lost (21/262)
  WATER_BUFFALO (9):     n1 0 (1/0)      n3 0 (62/8)  n5 0 (265/10) n7 2 (485/196)
  => DF's combat is driven by pack size, not prey size: a lone wolf does nothing even to deer; kills come at 5-7
  wolves on every prey up to buffalo (25x one wolf, which the 5x gate forbids). Attack counts rise steeply with n.
  The 5x upper bound is conservative against DF (buffalo fell to 7 wolves in both reps) and says nothing about the
  lower end (lone predators near-inert). Kill rates are low (<= 2 of 4 prey per 3,000 t) -> prey is not wiped out.
ECO3 WB (OCEAN2 shore, 4 SHARK_TIGER vs 6 birds placed in water, 3,000 t, 2 reps):
  BIRD_DUCK: DF alone 0 / 0 attacks; written 5 of 6 killed in both reps (25 / 27 attacks). Ducks end dry (wet 0) -> they
  are caught while swimming, then the survivors fly/walk out.
  BIRD_PENGUIN: DF alone 0 attacks (1 penguin died per rep, not by a spawned killer: cause unrecorded); written 2 and 3 of
  6 killed. => aquatic predators DO take swimming waterbirds (the reach table's 'untested' cell -> yes, in water).
ECO CAL (CTRL, one spot, 6 prey + n written predators, 30,000 t, sustain per cell, 2 reps; kills rep1/rep2):
  wolves    deer       moose      water buffalo  elephant (hunters lost)
    3       0/0        0/1        2/0            0/0 (1/1)
    5       0/0        0/1        1/0            0/0 (2/0)
    7       1/0        2/0        3/1            2/1 (1/0)
  hyenas 5: buffalo 0/0, elephant 1/1 (0/2 lost); hyenas 10: buffalo 0/1, elephant 5/3 (1/2 lost).
  solitary: cougar vs deer/elk/moose 0 in 6; lion vs giraffe 0/0, vs buffalo 0/1; tiger vs buffalo 0/0 -> 1 kill in 12.
  Rates: best 1.33 kills / 10k t (10 hyenas on elephants), 7 wolves 0.17-0.66, 3-5 wolves 0-0.33.
  => kills track group size, not prey mass: bigger prey died MORE (deer 1 in 6 wolf cell-reps, buffalo 7, elephants
  3 to wolves, 8 to 10 hyenas); deer escape. Solitary hunters are inert over 30k t. Predation thins, never wipes
  out (max 5 of 6 in 30k t). A mass-ratio gate has no basis in DF's combat; group size is the lever.
  Attempt 1 (withered by thirst at ~330k t) is data/experiments/ECO/CAL-20260930-135309 (rep 1 wolf cells valid).
ECO STL (CTRL, 1 COUGAR or LION vs 6 DEER / WATER_BUFFALO, written, 30,000 t, sustain per cell, 2 reps; per arm over
  8 cell-reps: hunter attacks on its prey / prey killed / hunters lost; scripts/stl-tally.py):
  ctl 17/0/0; sneak (unit SNEAK 10) 112/3/0; nslow (sneak + stealth_slows 0) 21/1/1; ambush (AMBUSHPREDATOR) 29/1/0.
  Hidden (flags1.hidden_in_ambush|hidden_ambusher) 0 of 186 samples in every arm -> wild AI never sneaks; the skill acts
  in the fight, not by hiding. All 5 kills by LION (deer 3, buffalo 2); COUGAR (speed 195, slower than both prey) 0.
  Cell-reps with a kill: treated 4/24, ctl 0/8 (CAL lone hunters 1/12) -> repeats, but small n; STL2 doubles it.
  OFF-TARGET: tool OFF on CTRL (probe tool: enabled 0, scheduled 0) and `rel` writes only spawned-a x spawned-b, yet
  over 30k t placed hunters attack natives never related: STL ambush 103 attacks / 5 native kills (ctl 0); CAL packs
  745 attacks / 53 native kills (BADGER 30, EMU 6, KANGAROO 6, WOMBAT 4, ...). P1's 'no relation, no hunting' was 3,000 t.
  STL2 (running) adds norel (no relation written), fight (MELEE_COMBAT, BITE, GRASP_STRIKE, WRESTLING, DODGING 10), all.
  Prey speed (ticks/100 tiles; lower faster): lion 109, elk 122, deer 137, wolf 149, moose 157, tiger 157, buffalo 183,
  cougar 195, elephant 488; CAL kills rose as prey slowed (deer 1, moose 4, buffalo 7, elephant 11).
ECO STL2 (data/experiments/ECO/STL2-20260930-164417; same pairs, 30k t, 2 reps; skills rating 10 on the placed hunter; att/kills/runs-with-kill per arm):
  ctl 53/4 (lion_DEER_ctl 3 then 1 -> STL's clean ctl was luck); norel (no rel) 0/0 in 8 runs; sneak 85/4; fight
  (MELEE_COMBAT BITE GRASP_STRIKE WRESTLING DODGING) 315/3 (cougar x deer 131 and 145 attacks, 1 kill each rep); all
  (+SNEAK, SITUATIONAL_AWARENESS, AMBUSHPREDATOR) 18/1. Hidden 0/240. POOLED STL+STL2: skilled or AMBUSH 10 of 48 runs
  with a kill vs unchanged 2 of 16 -> no lift; skills raise engagement (fight) at most. Lone hunters' limit = meeting prey.
  Skills-write rows say units=2: the previous cell's cleared hunter is still in units.active on that tick (hidden n=1 in
  every sample) -> harmless. norel off-target: LION killed 8 BADGER (104 att vs 4), COUGAR hit native WOLF/PORCUPINE/KAKAPO.
RELP (data/experiments/ECO/RELP-20260930-174328; CTRL, 1 run): enemy_status slots are assigned lazily (0 natives slotted at load). +100 t: 42 slotted, only
  SAME_RACE / SAME_CULTURE / STRANGER. +3,000 t: DF itself wrote PREDATOR_OR_PREY LION(placed, no rel)>BIRD_KESTREL(wild),
  and dwarves/yak/horse/pig/reindeer > kestrel. => DF writes PREDATOR_OR_PREY on its own over time; that is how placed
  hunters attack unrelated natives in 30k-t cells. P1 (3,000 t, 0 attacks without a write) stands as a short-run result.
ECO LONE (data/experiments/ECO/LONE-20260930-184842; CTRL tool off, 1 COUGAR among 6 x RABBIT HARE GROUNDHOG GOAT_MOUNTAIN KANGAROO DEER ELK WATER_BUFFALO r20,
  rel to all 8, 100,800 t, 5 reps): cougar alive in all 21 samples of all 10 runs (no early death). Placed-prey kills
  ctl 5 (2,0,1,0,2) vs pkg 11 (1,2,6,0,2); native kills 9 vs 11; attacks on placed prey 139 vs 290, all attacks 390 vs 472.
  One-sided permutation p: placed kills .25, all kills .13, placed attacks .20 -> direction favours pkg, n=5 too few.
  Kills: groundhog 8, goat 5, kangaroo 1, rabbit 1, elk 1 (pkg); no deer/buffalo kills. At density a lone hunter hunts
  (~3 kills/season unchanged): encounter, not ability, limited STL/CAL.
ECO REACH (data/experiments/ECO/REACH-20260930-193803; relation written, 3 pred vs 6 prey, 2 reps; kills summed of 12): CROCODILE_SALTWATER x swimming BEAVER
  12/12; x CAPYBARA placed r15 on land 10/12 (1-3 of 3 crocs on dry tiles in every 1k sample -> crocs go ashore; capybaras
  49 attacks back, 0 crocs lost). SHARK_TIGER x HARP_SEAL in water 4/12 (0,4), on shore 0/12. BIRD_KEA x GREY_PARROT 5/12;
  BIRD_EAGLE (BENIGN off) x RAVEN 2/12, x RABBIT 0/12 (0 attacks); OWL_GREAT_HORNED x STORK 1/12. BOATS cav1: BAT_GIANT x
  BUGBAT 1/12, x CRUNDLE 5/12 (1 bat lost each in rep 2); SWALLOW_CAVE_GIANT (BENIGN off) x BUGBAT 4/12. RIVER4 WOLF x5 vs
  PIKE x8: swim-only 0 att, swim+breathe 1 att/rep, ctl 0 -> 0/16 kills every arm: swim flags do NOT make a wolf fish.
ECO RELS (data/experiments/ECO/RELS-20260930-195031; CTRL tool off, rel_map sampled every 3k t; nat 100,800 t, lion / lion_benign / lion_nolp / lion_ambush /
  deer / 4 badgers 30k t, 2 reps): 370 PREDATOR_OR_PREY entries written by DF: dwarves > surface wild arrival 159,
  livestock/pets > arrival 107, script-placed units (roaming flag false) > arrival 57, cavern wild <> cavern wild 38,
  surface wild > surface wild 5 (3 = one wild great horned owl with a wombat and a skunk), cavern <> surface wild 4.
  Arrivals answer BENIGN_ANIMAL (662) or DANGEROUS_ANIMAL (15). Median first-seen distance 35-85 tiles; entries cleared
  again within a few 3k samples. Tokens irrelevant: lion as-is / BENIGN / no LP / AMBUSH, deer and badgers all got them.
  => DF aims every non-wild unit at each new wild arrival; surface wild-wild almost never (P1 holds for DF's arrivals);
  caverns write wild-wild (HC). The tool's releaseGroup (:3197) and placement (:3559) clear the roaming flag, so released
  groups become 'non-wild' to DF and get aimed at later arrivals; isWildlife reads population_idx, so the v7.0 sweep
  still sees them. The CAL/STL/LONE off-target kills are this placement artefact.
