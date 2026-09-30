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
