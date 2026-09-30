# Tool + rig capability map (Explore agent, 29 Sep 23:5x). SW = seasonal-wildlife/scripts/seasonal-wildlife.lua v6.8.0; DC = DwarfCron
## Tool
- Layer from pop entry (layerOf SW:759): cave_id -> cavern (depth<=2) / deep (3-4); feature_idx -> water; else land (incl. OCEAN surface species!).
- Habitat MODEL.habitat SW:1091: aquatic (IMMOBILE_LAND|CANNOT_BREATHE_AIR) > FLIER+water biome=waterbird / flier > CAN_BREATHE_WATER or all-water biomes = semiaquatic > land. Water biome = OCEAN*/POOL*/LAKE*/RIVER*/SUBTERRANEAN_WATER. CAN_SWIM_INNATE read, unused.
- Water bodies/salinity MODEL.waters SW:1109 from biome names; ENGINE.fits SW:3855. NO deep-water class; depth only flow>=4 placement, WET.NEAR=6, PLACE.BAND surface-12..+1.
- Vermin: VERMIN_GROUNDER/ROTTER/SOIL/FISH/EATER or SMALL_RACE (SW:1048). Families SW:1883.
- Role MODEL.role SW:1103: predator if any caste CARNIVORE|BONECARN|LARGE_PREDATOR|AMBUSHPREDATOR (MODEL.DIET SW:988) else prey; overrides ORCA/GIANT_ORCA/GIANT_CUTTLEFISH pred, SHARK_WHALE prey. GRAZER only a reason.
- Size band SW:978: <150k small, <1M medium, else large (cm3, x10 fix). Group = midpoint cluster_number.
- eats() SW:1374: take=mass*group^0.75*(1.5 LP/ambush) vs need=prey mass*(0.9 herd/0.6 solo); same class, same realm, habitat REACH SW:1361, water pair share a body, no eating pred >=0.5x mass. Pref lognormal ~0.4x.
- ecoWrite SW:3311: rel_map[sa][sb].ur=PREDATOR_OR_PREY both ways. Predators = land/cavern predator AND largePred (ecoArmed SW:3236). Targets = all other wild in realm not in predator set + non-fort animals; livestock opt-in. LARGE_PREDATOR never prey. Cadence 1500 t; 30 ms budget; memo, full rewrite every 8th; rel_map 500x500.
  Nudge: pred >40 tiles from targets for 3000 t teleported within 6 (SW:3458).
  Realm (ecoRealm SW:3224): land / cavern:<d> / NIL for water-layer units -> water units excluded from ecology. Surface ocean species are realm land -> pairable with land. ecoWrite does NOT call eats()/REACH (only coupling/matrix use them).
- Limits SW:384: land groups 3 ceiling 0; water 2/12; cavern 2/0. max_concurrent=3 legacy. Gate SW:4520. Nothing scales with embark size.
- Group size levers: groups.pack; trickle {2,1}; size KEY N (land/cavern only) PATTERN.sizeApply SW:4130; Driver B ENGINE.groupSize SW:3887.
- Leaders applyCohesion SW:4253: LOWEST-ID member leads; following=leader, owner_type PACK_LEADER, follow dist herd 8 pack 4 flock 12 school 5. E28: spread 5.0 vs 9.9.
- FREQUENCY: CAVERN.apply SW:2229 (clamp>=1, snapshot/restore); odds any layer; Driver B weights by frequency. POPULATION_NUMBER never read by name; works on pop.quantity/quantity_max/extinct. RESERVE SW:1758, applyLive SW:1801, holdOutOfSeason every 300 t.
- Scavenging PLAN.md:195-220 pinned: eats-bugs/fish/crawlers/fliers/remains; "eating remains works like a haul job ... remains deleted". Web page suggests remains if BONECARN or CARNIVORE and not small.
- Announcements: tool never reads reports/combat logs/incidents. Only announces season apply.
- Origins WILD.origin SW:2045 (wave/tool/resident/born/untracked/deep). No biogeography. Climate lean COLD/HOT/MILD for season dealing.
- D8 ecologyClass SW:926: generated, mega, night, unliving, mythic (FANCIFUL|GOOD|EVIL), unclassified, natural (only natural enabled).
## Rig
- Driver DC/scripts/cx-experiment.py run experiments/X.json [--reps N] [--arm A]; report <run>. Fields: id,title,fort,backup,fps,gfps,sample_every,tick_budget,combat,tool_must_be,predictions,kill_criterion,culling, arms[{name,replicates,pre[],every{ticks,do[],max},on_arrival[],stop_when{...},control}]. Manipulations 'probe:<args>' or raw Lua (no braces in on_arrival strings). manifest-lint.py (luac -p, refuses frequency=0). Example X4.json.
- Replicate: restore backup (sha256), load, popups, baseline, pre, assert tool_must_be, step+sample, pops all, quit w/o saving, re-hash.
- Samples: clock, units.tsv (id species caste pos ref6 layer countdown dead wild mother...), pops.tsv, events.tsv (arrival/departure/death flag, no killer), combat.tsv if combat:true (wild units' Combat log text). Incidents only in e41 drivers (e41-cavern-relation.py:71). probe:rel / relrow / lever relmap.
- Placement: `place` scatters (PLACE.tiles SW:3092, stride 3, first z with >=200 free tiles). Driver B clusters within 6 tiles. cx-probe gather teleports surface LPs within 3 tiles of first wild non-predator (cx-probe.lua:382). cx-load wild/constwild/clearwild/hold.
- Forts: CTRL (land, dingo/wolf/cougar/badger/wombat/kangaroo/emu..., caverns unopened, no animal people), BOATS (6x6 tropical shrubland+ocean+salt river), LAKE (tropical fresh lake 87% water), OCEAN2 (wet ocean shelf, shark blue), OCEAN (dry), RIVER3, RIVER4, MAGMA, SPLIT, FPS2E*. All have .preverify.
- Tallies per exp + tallylib.drop_incomplete; report writes waves.tsv. Readout traps apply.
- Time: 105-290 t/s; 24k t ~2-4 min/rep; 60k ~4-6 min; season 100.8k ~8-14 min; +1-3 min load.
## Prior results (for not repeating)
E11/E11b/E11c (written relation 19/19 kills; no lever 0/14; rival preds fight as STRANGER; DF sets relation ~2/450), E16/16b (relation persists, load clears), E17 (rewrite every 1500 -> 21 dead), T4 (BENIGN ignore; LP 3/3), E32b (LP flip on badger -> attacked dogs), E22 (caravan animal 1/2), E19 (held herd season: nothing starved/fought/bred), E28 leader, E29 agitated, E41/41b (croc not pulled from water), E41e (cavern kills via incidents), E41f (croc kills toads same water 2/3), E40 cavern gate, X1..X7 (X3 FREQUENCY weights surface pick 80/70% vs 23/24%; X4 {1,1} mostly 1 sometimes 2; X5 vermin hunt no effect low exposure; X6 albatross swim tags).
