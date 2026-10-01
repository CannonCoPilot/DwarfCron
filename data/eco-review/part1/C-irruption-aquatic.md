# Review Part 1, items 7, 8 and 9: irruption, pelagic predators in shallow water, leaders for aquatic groups

W2:Urist desk review, 1 Oct 2026. No rig was used, no code was changed, no commits were made, and the report sources are untouched. All report revisions are **held** (section 4).

**Evidence tags.** **[MEASURED]** means a rig run, with its run id or findings line. **[DOCUMENTED]** means df-structures, DFHack source or docs, or a wiki quote. **[INFERRED]** means read from code or reasoned, and not yet run.

**Source abbreviations**
- `sw.lua:N` = `seasonal-wildlife/scripts/seasonal-wildlife.lua`, branch v7.0 @ 99c1ec8.
- `STATE:N` / `PLAN:N` = the same repo's STATE.md / PLAN.md.
- `findings:N` = `DwarfCron/data/eco-desk/findings.md`.
- `design:N` = `DwarfCron/data/eco-desk/v2/guilds/design.md`.
- `xml/…` = `GitRepos/dfhack-53.16-r2/library/xml/…`.
- `r2/…` = other files in the DFHack 53.16-r2 tree.
- `cx-eco` / `cx-probe` = `DwarfCron/chronicler/dfhack/scripts/cx-eco.lua` / `cx-probe.lua`.
- `tokens` = `DwarfCron/data/eco-desk/tokens-by-creature.tsv`.
- `wiki-tokens` = `DwarfCron/data/eco-desk/wiki-tokens.md`, which quotes the Creature_token page as CT#…

---

## Headlines

1. **Irruption today is a flag on whatever DF happens to send.** It never brings more animals and never picks the species. It arms the next cavern group that DF itself draws, once pressure crosses the threshold, with one lever: `flags4.agitated_wilderness_creature`. That flag makes the group lethal but not aimed, and it decays. The rebuild should be a tool-driven *wave* of cavern civilisation races, placed by the tool from that cavern's own population entries, carrying per-unit behaviour writes.
2. **The best per-unit lever already exists and was already used once.**
   - `unit.uwss_add_caste_flag` / `uwss_remove_caste_flag` is the 53.16 form of the old `unit.curse.add_tags1/rem_tags1` (xml/df.unit.xml:2904-2907).
   - It carries 31 tags, among them CRAZED, MISCHIEVOUS, OPPOSED_TO_LIFE and NOFEAR (xml/df.material.xml:459-494).
   - E11c wrote CRAZED and OPPOSED_TO_LIFE through it per unit (cx-probe:301-303). Re-applied every 1,500 t, both changed behaviour (STATE:965-980).
   - Whether DF recomputes the masks from syndromes, and so clears a bare write, is unmeasured. That is probe M1.
   - The 31 tags do **not** include MEANDERER, CURIOUS_BEAST_ITEM, AMBUSHPREDATOR or PRONE_TO_RAGE. For those the candidates are the unsaved per-unit cache `unit.enemy.caste_flags` (xml/df.unit.xml:3098, also unprobed) or a caste-wide raw write.
3. **Pelagic (item 8).** OCEAN2 really is 1-2 levels deep (ECO O). Three things together kept every pelagic predator off it:
   - The roster has one water apex slot. The saltwater crocodile won it on OCEAN2.
   - The PE slot is pelagic *prey*, with minimum 0.
   - The draw weight of every ocean animal over 1,000,000 cm³ is cut to 0.1× FREQUENCY whenever the survey finds no column 3 or more levels deep.

   **There is also probably a bug in the survey itself.** The water scan stops after the first z-level once it holds 3,000 sampled tiles, so `ENGINE.deepColumns` likely never sees a second level on a large ocean. On BOATS it would report 0 deep columns where the DEPTH survey counted 12,045 [INFERRED; sw.lua:4822].

   The redesign: a prey-presence pull on the draw weight, seeding the draw near the prey in the deepest water, a pelagic-apex slot on ocean forts, and a stranding guard.
4. **Leaders (item 9).**
   - The orcas that stranded were the harness's unled *control* arm in COHO, not anything the tool did. Its `lead` verb only sets `u.following` (cx-eco:548-567).
   - The tool's own cohesion would lead a pod that Driver B draws within 300 ticks (sw.lua:5906-5936).
   - Five real holes remain:
     - `place` creates no group record, so the animals are never led (sw.lua:7715).
     - `place` also scatters the animals across the map.
     - DF's embark-seeded water animals are never tracked (sw.lua:3511-3519).
     - Nothing checks that a water group's leader is in water.
     - A group of one, before its members arrive, is never led.
   - The tool's own water lever (PACK_LEADER owner type plus follow_distance 5) has never been measured in water. COHO measured the harness lever.

---

## Item 7: irruption

### 7.1 What the module does now (v6.1.0 to v7.0)

**Code [INFERRED from code; behaviour MEASURED where cited]**
- **Opt-in.** `irruption={ enabled=false, threshold=1.0, gain=0.02, decay=0.01, duration_days=10, cooldown_days=30 }` (sw.lua:471). It is sanitised at sw.lua:555-559 and listed on the Panel as "dwarves in a cavern raise pressure; a group turns agitated" (sw.lua:7086).
- **Pressure, one per cavern depth 0-2** (sw.lua:6038).
  - `IRRUPT.citizensInBands` counts live citizens whose z falls inside each cavern's band from `CAVE.get().bands` (sw.lua:6040-6051).
  - Every groups tick (300 ticks, sw.lua:3391): `p = p·(1−decay) + gain·citizens` (sw.lua:6088-6093). The steady state is gain·n/decay: 6.0 for three citizens.
  - `pressure_pin` overrides the value. T9 used it (sw.lua:6092).
- **The gate under pressure.** `IRRUPT.gapDays` halves the cavern gate's jittered gap once any cavern reaches threshold/2. It feeds both cavern gate paths (sw.lua:6073-6079, 6211, 6228).
- **Arming.**
  - It acts only when nothing is armed and the cooldown is over. It scans `fresh`, the groups DF drew this pass (sw.lua:6232 → discoverGroups sw.lua:3546-3564).
  - It takes the first cavern group whose depth is at or over the threshold and whose roster key is not blocked (sw.lua:6104-6117).
  - It writes `flags4.agitated_wilderness_creature = true` on every member (sw.lua:6053-6063).
  - It records `g.armed = {ids, token, depth, until_tick}` and resets that cavern's pressure to 0 (sw.lua:6112).
  - A blocked species is logged "not armed" (sw.lua:6115).
- **Holding.** The flag is re-written every groups tick because it decays (sw.lua:6100). The group stands down when `duration_days` ends or no member is left on the map (sw.lua:6098-6099).
- **Stand-down.** The flag is cleared and a ledger line written, then the cooldown starts (sw.lua:6064-6071). The units stay as ordinary cavern residents.
- **Off.** `irruption off`, disable and All off all disarm at once (sw.lua:7050, 7109, 7789).
- **Verb.** `irruption [on|off|threshold|gain|decay|duration|cooldown|pin|unpin]` (sw.lua:7785-7801). Status line at sw.lua:6120-6127.

**What it does *not* do [INFERRED from code]**
- It never adds animals. It never chooses or favours a species, and has no notion of civ races. Only one group is armed at a time.
- It never touches `plotinfo.invasions` or invasion fields (PLAN:407-409).
- It has no aim. There is no relation write toward citizens. That is open item "pairing the agitated flag with relation writes to citizens" (open-items.json:1044).
- Its only behaviour lever is the one flag.
- PLAN rev 2 §3.6b wanted pressure to also raise pack size and coupling. That was dropped because coupling is a surface lever (PLAN:408-409; STATE:3641-3650).

**What was measured**

| Run | What | Result | Source |
|---|---|---|---|
| E29 (20260918-192710) | agitated flag on every wild land unit vs control, CTRL, 2 reps | **Lethal, not aimed.** 2,121 and 1,108 combat rows against 0 and 0. Citizens 7→4 in one rep. Units within 15 tiles of the dwarves unchanged (0.3/0.4 vs 0.2/0.0). The flag decays, so it must be held as a job. | STATE:2561-2609 [MEASURED] |
| E23 (20260918-200458) | agitation maxed (irritation pinned), roster closed vs open, MAGMA | **The roster gates agitation completely.** 0 arrivals from 220 closed entries. The open roster destroyed one fort (7→0) and left another with one survivor. | STATE:2611-2654 [MEASURED] |
| T9 (20260921-203202) | pressure pinned at threshold; module on vs off, CTRL | **Arming path works.** 4 groups armed per rep (giant cave swallow, elk birds, troglodytes, …). Flag held at 28-29 of 34 samples. Off: 0 flagged. Citizens 7→7, because nothing aims and the dwarves stayed on the surface. | STATE:3660-3672 [MEASURED] |
| T9b (20260921-224702) | real pressure from 3 citizens teleported to cavern 1 | Pressure passed 1.0 on day 19 and reached 3.9-4.1. 3 armings per rep. Armed troglodytes fought the miner for two days. Teleported dwarves die at ~60 days of thirst. | STATE:3735-3755; memory ctrl-fort-facts [MEASURED] |
| T9c (20261001-023732) | the halved gate with room (cavern cap 6), CTRL | Gap 3-9 days vs 8-20, but waves sat overdue and cavern units were **not** more numerous (mean 18.4/20.2 vs 20.9/24.5). Armings 3 and 2. | findings:460-467 [MEASURED] |
| E23b/c/d/e | DF's own cavern invasion | None in two seasons by any route: irritation pinned (E23b), forced army (E23c), caverns opened with citizens on the floor (E23d), and BOATS with 334 cavern animal-person/civ populations (E23e). | STATE:2656-2745, 3789-3806; findings:510-517 [MEASURED] |

**Net result.** The pressure path and the arming path work, and off is inert (2 of 2 throughout). But irruption adds no traffic (T9c). Its only lever is lethal and unaimed (E29). It depends on DF sending a group at the right moment. Its "danger dial" is the roster (E23).

### 7.2 Invasion vs irruption: purpose

- **Invasion is DF's own machinery** [DOCUMENTED].
  - The wiki defines an ambush as "a small force of enemy humanoids [that] attempts a sneak attack on your fortress" and a siege as "large-scale assaults on your fortress by other civilizations" (wiki Ambush; Siege).
  - The cavern form: "Upon breaching the caverns, your fortress may occasionally be attacked by a large swarm of underground animal people … numbers … well into the dozens", "somewhere between an ambush and a siege", announced as "Cavern dwellers! Send them back to the darkness!" (wiki Ambush).
  - "Subterranean animal people may occasionally launch ambushes into a fortress from any of the cavern levels" (wiki Cavern, footnote 1).
  - The units carry `invasion_id >= 0` and an army/entity. The tool excludes them from every count (addendum 49; `WILD.invader`, sw.lua:2763-2774).
  - The player can turn invasions off: "changing 'civilizations can attack' … to NO in the difficulty settings" (wiki Siege). The user's game has them off (review item 7).
  - Rig: no flag, pin or teleport produced one (E23b-e).
- **Irruption is the ecological term.**
  - It is an irregular, non-cyclical mass movement of a population beyond its usual range, driven "under pressure of famine", by "overpopulation of a locality", or by "some more obscure influence" (Wikipedia, *Animal migration*: "Irregular (non-cyclical) migrations such as irruptions"). The classic cases are owls and crossbills irrupting when prey or cone crops fail, and lemmings at density peaks.
  - PLAN:407 already fixed the naming: "irruption, never a raid".
- **Purpose, restated for the rebuild.** A tool-driven ecological event: cavern-dwelling populations surge out of their normal range and toward the fort, in waves and in larger numbers than the ordinary cavern rotation. The surge is triggered by ecological pressure: crowding, food scarcity, disturbance by the fort, season.
  - The surging animals are still *wildlife*: population references, counted, recorded in the ledger, reversible.
  - They are **not** an army. No `invasion_id`, no entity, no siege AI, no `plotinfo.invasions`.
  - The behaviours are restlessness, ranging, sneaking, theft and, at the top tier and opt-in only, rage. Raid behaviour is not part of it.

### 7.3 Which cavern civilisation races exist and how they arrive

**Vanilla raws, from `tokens`** [DOCUMENTED: raw tokens; tool membership INFERRED from V7.isCivRaw, sw.lua:1681-1688]

`V7.isCivRaw` requires three things: CAN_SPEAK or CAN_LEARN; neither GOOD nor EVIL; and no animal-person root.

| Race | Biome / depth | Population : cluster | FREQ | Notable tokens | civ to the tool? |
|---|---|---|---|---|---|
| TROGLODYTE | CHASM, depth 1-2 | 15:30 : 5:10 | 100 | CAN_LEARN, LARGE_PREDATOR | yes |
| RODENT MAN (id has a space) | CHASM, 1-3 | 5:10 : 5:10 | 100 | SPEAK, LEARN, LP, CARNIVORE | yes (verbs cannot name it: W1O's SEA OTTER trap) |
| AMPHIBIAN_MAN | WATER, 1-3 | 5:10 : 5:10 | 100 | SPEAK, LEARN, LP, CARNIVORE, AMPHIBIOUS | yes |
| REPTILE_MAN | WATER, 1-3 | 5:10 : 5:10 | 100 | same as amphibian man | yes |
| SERPENT_MAN | WATER, 1-3 | 5:10 : 5:10 | 100 | same as amphibian man | yes |
| ANT_MAN | CHASM, 1-3 | 5:10 : 5:10 | 100 | SPEAK, LEARN, LP, FLIER | yes |
| GREMLIN | CHASM, 1-3 | 1:1 : – | (50) | SPEAK, LEARN, **MISCHIEVOUS**, TRAPAVOID | yes |
| PLUMP_HELMET_MAN | WATER, 2-3 | 15:30 : 3:5 | 20 | CAN_LEARN, **BENIGN** | yes |
| OLM_MAN, CAVE_FISH_MAN, CAVE_SWALLOW_MAN, BAT_MAN | 1-2 | 5:10 : 5:10 | 100 | animal people (root animal) | no (root) |
| GORLAK / BLIND_CAVE_OGRE, TROLL, MANERA | – | – | – | GOOD / EVIL | no (aligned) |

**How they arrive** [MEASURED]
- They arrive as ordinary cavern wildlife waves: a world-population entry and the roaming flag. `gatedLayer` therefore tracks them as cavern groups (sw.lua:3511-3519).
- FREQUENCY steers each cavern layer's pick in proportion (ECO2-FC: a giant cave swallow at f100 took 42 of 49 waves; findings:160-167).
- On BOATS, plump helmet men filled the cavern shore slot at about 15 per wave, 54 and 180 units in a season (S8B, findings:437-447).
- Troglodytes appear in BOATS cavern 2 (HC2, findings:124-127). Ant men are in BOATS's caverns (DEPTH incident list: CROCODILE_CAVE>ANT_MAN).
- E23e listed 334 cavern animal-person/civ populations on BOATS (findings:510-512).
- **CTRL's caverns hold no animal person** (E23d probe, STATE:3800-3806). Every civ-irruption experiment therefore needs BOATS or a newly surveyed 1×1 fort (item 10).

**Gremlins arrive differently** [DOCUMENTED; MEASURED]
- The wiki says they "are invisible until spotted" and cause trouble "by stepping on pressure plates, pulling levers, opening cages, picking locks and opening forbidden doors". Their raws carry LOCKPICKER, MISCHIEVOUS, CANOPENDOORS and NATURAL_SKILL:SNEAK:3 (wiki Gremlin).
- DF's own scheduler queues a `WildlifeMischievous` timed event (STATE:2716-2724, E23c logs).

### 7.4 Every lever for behaviour, per individual or per event

| # | Lever | Scope | Which behaviours it can carry | Does it stick or act? | Restore |
|---|---|---|---|---|---|
| L1 | **Caste raw flags** `cr.caste[i].flags[X]`, plus caste misc (`prone_to_rage` int32, `beach_frequency` int16) | Every unit of the caste on the map, the irruption's or not (and tame ones) | Any caste_raw_flags bit: MEANDERER, CURIOUS_BEAST_ITEM/EATER/GUZZLER, MISCHIEVOUS, AMBUSHPREDATOR, CRAZED, NOFEAR, TRAPAVOID, LOCKPICKER, BENIGN … (xml/df.creature.xml:801-980; misc :1057, :1085) | **[MEASURED]** for units *created after* the write: CRAZED deer walked 30+ tiles to the fort and killed 3 dwarves (T1, findings:17). MEANDERER off gave a wider scatter, replicated (TV2, findings:188). PRONE_TO_RAGE shows a replicated dose effect (findings:185). BENIGN is the switch (T1, HO, TV2). CURIOUS_BEAST* off keeps curious beasts on the map (B, CB). **Unmeasured for units already on the map**: DF may read the per-unit cache `enemy.caste_flags`, which is filled when the unit is made or loaded. That is probe M3. | `V7.flag` + `V7.rec`, restored on switch off, disable and unload (sw.lua:6421-6434). A raw edit also cannot outlive the world: DF re-reads raws on load (addendum 53, PLAN:374) |
| L2 | **Per-unit curse masks** `unit.uwss_add_caste_flag` / `uwss_remove_caste_flag` (and `_property`) | One unit | Only the 31 cie_add_tag_mask1 bits: EXTRAVISION, **OPPOSED_TO_LIFE**, NOT_LIVING, NOEXERT, NOPAIN, NOBREATHE, HAS_BLOOD, NOSTUN, NONAUSEA, NO_DIZZINESS, NO_FEVERS, **TRANCES**, NOEMOTION, NIGHT_CREATURE_EXPERIMENTER, PARALYZEIMMUNE, **NOFEAR**, NO_EAT, NO_DRINK, NO_SLEEP, **MISCHIEVOUS**, NO_PHYS_ATT_GAIN/RUST, NOTHOUGHT, NO_THOUGHT_CENTER_FOR_MOVEMENT, CAN_SPEAK, CAN_LEARN, UTTERANCES, **CRAZED**, BLOODSUCKER, NO_CONNECTIONS_FOR_MOVEMENT, SUPERNATURAL (xml/df.material.xml:459-494; xml/df.unit.xml:2904-2907; the same list is the wiki's CE_ADD_TAG list) | DFHack's own rule for the active flag is `!remove && (add || caste)` (r2/library/modules/Units.cpp:117-118; r2/scripts/immortal-cravings.lua:157-160). **Acts [MEASURED]:** E11c wrote CRAZED and OPPOSED_TO_LIFE per unit, re-applied every 1,500 t. CRAZED gave heavy fighting with predators (3,602 rows) and one stalled tick; OPPOSED quietened the predators (STATE:965-980; cx-probe:301-303). **Sticking is unmeasured:** whether DF rebuilds the masks from active syndromes and so zeroes a bare write is probe M1. The fields are in the saved part of `unit` (unlike `enemy.caste_flags`) [DOCUMENTED, xml/df.unit.xml:2902-2935] | Write the old value back per unit, keyed by unit id; clear at stand-down. **Side effect:** OPPOSED_TO_LIFE or NOT_LIVING makes `dfhack.units.isUndead` true (Units.cpp:622-626), which changes how fb_safe and the tool classify the unit. Never use either |
| L3 | **Per-unit caste-flag cache** `unit.enemy.caste_flags` (DF name `base_caste_flag`, a flag array over all caste_raw_flags) | One unit | **Every** caste flag, including MEANDERER, CURIOUS_BEAST_ITEM, AMBUSHPREDATOR | Marked "below here unsaved" (xml/df.unit.xml:3096-3098): rebuilt at load and perhaps on other events. DFHack reads it as the truth for NIGHT_CREATURE, MEGABEAST, CAN_LEARN and others (Units.cpp:575-656; makeown.lua:328; sandbox.lua:30). **Whether DF's behaviour code reads it, and whether a write survives, is unknown: probes M3 and M4.** If it works, it is the only per-unit route to MEANDERER and the CURIOUS flags | Lost on reload by construction. Write back at stand-down |
| L4 | **Syndrome with CE_ADD_TAG / CE_REMOVE_TAG** (`modtools/add-syndrome`, `syndrome-util.infectWithSyndrome`) | One unit, timed by START/PEAK/END | The same 31 tags as L2, plus CE_CHANGE_PERSONALITY, CE_SPEED_CHANGE, CE_FEEL_EMOTION, CE_ERRATIC_BEHAVIOR (wiki Syndrome) | **A syndrome must already exist** in `world.raws.syndromes.all`. add-syndrome takes a name or id (r2/scripts/modtools/add-syndrome.lua:1-37), and "syndromes aren't defined in their own raw file". They live in a material's or an interaction's raws (wiki Syndrome). **Creating one at run time** (`df.syndrome:new()` plus a `creature_interaction_effect_add_simple_flagst`, xml/df.material.xml:504-507) is possible in principle [INFERRED]. But a unit_syndrome pointing at a syndrome that will not exist after reload is a save-corruption risk. DFHack has no reliable pre-save hook for erasing it, and DF autosaves | **Reject runtime syndromes.** Allowed instead: any *vanilla* syndrome that already carries a suitable CE (desk check D1: search raws with Python, per memory "macOS grep misses tokens in DF raws"), or a mod raw installed per world, which is out of scope for the tool |
| L5 | **Unit flags** | One unit | `flags4.agitated_wilderness_creature` (rage at all; E29). `flags1.marauder`/`active_invader`/`invader_origin` (sandbox's *hostile* disposition for sentients, r2/scripts/gui/sandbox.lua:34-37; counted by `Units::isInvader`, Units.cpp:614-619). `flags1.hidden_in_ambush` / `hidden_ambusher` (sneaking; xml/df.unit.xml:1345-1349). `flags1.check_active_heist` (thief bookkeeping, :1339). `flags4.no_meandering` "FLEE_WHEN_JOBLESS — for active_invaders" (:1436) | agitated **acts and decays** [MEASURED, E29]. The hidden flags: wild AI never sets them itself (0 of 426 samples, STL/STL2, findings:226). A *written* hidden flag is untested (probe M7). marauder/active_invader turns the unit into an invader in DFHack's eyes and probably DF's: alerts, military, and the alert filter keeps it (A2) | Write back per unit |
| L6 | **Personality facets** `status.current_soul.personality` (`modtools/set-personality`) | One unit (civ races have souls; the skills write already uses the soul, sw.lua:6436-6483) | ANGER_PROPENSITY, IMMODERATION, … through emotions and brawls (CE_ERRATIC_BEHAVIOR: "people that like to brawl have a chance of starting a brawl-level fight", wiki Syndrome) | Unknown for wild, non-citizen units. Low prior: wild AI is driven by the goal and flag machinery. Probe M9, last | Write back |
| L7 | **unit.animal** `leave_countdown`, `vanish_countdown` (xml/df.unit.xml:2691-2697) | One unit | stay vs leave; "once 0, it heads for the edge and leaves" | **[MEASURED]** hold and dismiss (T5, STATE:1491-1497; holdGroup sw.lua:5938-5946). Resetting the countdown every 300 t did **not** keep curious beasts (CB, findings:104-105) | Natural |
| L8 | **Path and goal writes** `u.path.dest`, `u.path.path.x/y/z`, `u.path.goal`; `idle_area` | One unit | Wandering and meandering by waypoint. Goals include WildernessRoamer, MarauderMill, WildernessCuriousStealTarget, ThiefTarget, Mischief, SeekStation, LeaveWall (xml/df.d_basics.xml:3943-…) | **[MEASURED]** A full path line plus dest plus SeekStation moved hyenas 20 tiles on the surface (S2, findings:38-40). The same failed in a cavern (HC1 walkeat_TROLL, findings:120-121): a path check is needed. A wild roamer's `idle_area` station is **ignored** (E28, STATE:1440-1450). A placed raccoon on goal WildernessCuriousStealTarget walked 35 tiles, stole a rope and left (findings:101-103). Grizzlies on BOATS milled on MarauderMill | Path expires on its own |
| L9 | **Relations** `enemy_status_cache.rel_map` | One pair | **Aim**: toward citizens (`relfort`, the A1 fort cell: wolves written against citizens attacked, findings:31-33) or toward prey | **[MEASURED]** The write is the switch on the surface (E11c), in caverns (E41e) and in water (E41f). Cavern wild–wild pairs fight unwritten for some species (HC1-HC4). Arrivals answer dwarves with DANGEROUS_ANIMAL (RELS2b, findings:404-409) | ecoClearDeparted pattern (sw.lua:4110) |
| L10 | **Leader / following** (owner_type PACK_LEADER, follow_distance) | One group | Cohesion: a coherent wave vs scattered wanderers | **[MEASURED]** E28: spread 5.0 vs 9.9, same travel. HC2: troglodytes 40.6 unled vs 2.9 led | clearCohesion (sw.lua:5875-5885) |
| L11 | **Skills** `soul.skills` (SNEAK, AMBUSH, …) | One unit | Sneaking and fighting skill | **[MEASURED]** A SNEAK 10 hunter made 112 attacks and 3 kills vs control 17/0 in STL. Pooled STL+STL2 shows no reliable lift (findings:223-236). V7.unitSkills writes it per unit with restore (sw.lua:6453-6483) | V7.rec |
| L12 | **Numbers** | Event | More units than rotation | (a) Placement from the cavern's own population entry (`PLACE.fromEntry` in the cavern band, sw.lua:3994-4031; the STOCK.run machinery, sw.lua:4705-4746). Debits the entry; refunded on departure (E31b, STATE:2797). (b) `cluster_number` write: live at the draw (E12/T3, PLAN:300). (c) FREQUENCY steering per cavern layer (ECO2-FC). The gate alone adds no traffic (T9c) | (a) none needed. (b) and (c): the PATTERN.sizeRestore and CAVERN restore paths |

**Why the tool refused the agitated flag, and whether to reconsider.**
- **The refusal.** PLAN rev 2 §2: "The tool never sets `flags4.agitated_wilderness_creature`: that is DF's 'attack the fort' state" (PLAN:332, also :447). E29 sharpened it: the flag is lethal, unaimed and decaying — "an unpredictable tax on outdoor labour, not a directed event" (STATE:2585-2590). E23 showed it can destroy a fort when the roster is open (STATE:2637-2643).
- **The partial reversal.** v6.1 overrode the refusal, opt-in, bounded and reversible (PLAN:103, :409).
- **Recommendation for the rebuild.** Keep agitated only as the **top, opt-in "fury" tier**, on a *fraction* of a wave (a cap of N units), for a short window, held as a job. Prefer the per-unit CRAZED write (L2) only if M1 and M2 show it is steadier. Never use marauder/active_invader: that is the invasion machinery the user wants avoided, and it turns the units into invaders the tool's own counts exclude.

### 7.5 Requested behaviours mapped to levers

| Behaviour | Best candidate | Second | Feasibility |
|---|---|---|---|
| **Wandering** (range expansion, toward the fort) | L8 waypoint walks toward the fort's cavern access, re-issued every 300-1,500 t, plus L10 *off* (no leader) so the group spreads | L1/L3 MEANDERER *removed*: TV2 says off means wider scatter (findings:188), but civ races carry no MEANDERER (tokens), and the wiki says MEANDERER "no longer applies to animal people" since 52.05 (wiki-tokens:65) | **High** for the waypoint, once the cavern path check exists (HC1 failure) |
| **Meandering** (slow, local, aimless drift) | L1/L3 MEANDERER *added*: "Slowly stroll around, unless it's in combat or performing a job" (wiki-tokens:65). Its effect on CAN_LEARN races is doubtful | L8 short random waypoints near the entry; L7 long countdown so they linger | **Medium.** Measure the spread directly |
| **Rage** | L2 CRAZED per unit: "will attack all other creatures, except members of its own species that also have the CRAZED tag" (wiki-tokens:35). Acts per unit (E11c) | L1 PRONE_TO_RAGE (caste-wide, dose replicated; TV2); L5 agitated (E29). The NOFEAR or TRANCES masks as boosters | **High** to act. A safety cap is mandatory: E23's dead fort |
| **Sneaking** | L5 `hidden_in_ambush` written (M7) plus L11 SNEAK and AMBUSH skills | L2 MISCHIEVOUS: the gremlin path "spawns stealthed" (wiki-tokens:66) | **Low to medium**: wild AI never hid (0/426); written state untested |
| **Stealing** | L3 or L1 CURIOUS_BEAST_ITEM: steals "of the highest value it can find" and heads for the edge (wiki-tokens:39), proven on the raccoon (findings:101-103) | L2 MISCHIEVOUS (levers, doors, cages: wiki Gremlin); L8 goal WildernessCuriousStealTarget on its own (M6) | **Medium**: caste-wide with L1 works for arrivals made *after* the write. Pre-writing the caste just before the tool places a wave is a clean path: the wave is created after the write |

**The key design trick [INFERRED].** The tool *places* the wave, so caste-level writes made just before placement reach exactly the new units. Only units of that race already on the map are also exposed. Restore the caste when the wave ends; the units created during the window keep whatever the cache gave them (M3 settles this). This means L1 can serve as a near-per-event lever without L3.

### 7.6 Experiment programme

The rules come from memory: two reps per arm; a subject receipt; a fresh load per arm with the arm order reversed in rep 2; sustain citizens in long runs. Every probe prints its write *and* reads it back.

**Desk first (no rig)**
- **D1.** Python over the vanilla raws: every syndrome carrying CE_ADD_TAG / CE_REMOVE_TAG / CE_CHANGE_PERSONALITY, with its material or interaction.
- **D2.** List cavern civ-race population entries per fort (BOATS, GOODF, EVILF and new 1×1 embarks) from saved pops.tsv files.
- **D3.** Check how to target `RODENT MAN` (index, not token).

**Phase 1: manipulation checks.** BOATS, cavern 1 or 2, 3,000-6,000 t, 2 reps each. Each probe sets one variable on 4-6 placed troglodytes against 4-6 unwritten ones from the same draw.
- **M1 (mask sticks).** Write `uwss_add_caste_flag.CRAZED` once. Read it back every 100 t; save, reload, read again. Pass = still set at +3,000 t and after reload.
- **M2 (mask acts).** CRAZED once vs never. Count attacks by the subject on other species, and attacks on the subject. Pass = written ≥ 5× unwritten in 2 of 2.
- **M3 (caste write reaches existing units).** Flip a caste flag (MEANDERER add; CURIOUS_BEAST_ITEM add) with subjects already present. Read `enemy.caste_flags[X]` before, +100 and +3,000 t. Then spawn new units and read theirs.
- **M4 (cache write).** Write `enemy.caste_flags.CURIOUS_BEAST_ITEM` on two existing troglodytes. Read it back. Watch `path.goal` for WildernessCuriousStealTarget and items carried, with a wagon or stockpile reachable (BOATS needs a breach: memory fort-load-levers).
- **M5 (MISCHIEVOUS by mask).** One lever and one door reachable from the cavern. Record pull events, goal = Mischief, door state.
- **M6 (theft by goal).** Write goal WildernessCuriousStealTarget alone, without the flag.
- **M7 (hidden).** Write `flags1.hidden_in_ambush` on subjects. Sample the flag, the reveal announcement and the distance to the nearest citizen at reveal.
- **M8 (waypoint underground).** walkto with a path check (canWalkBetween) toward the breach. Pass = ≥ 3 of 6 within 5 tiles of the target at +600 t.
- **M9 (facets).** ANGER_PROPENSITY 100 vs default. Attacks. Expected null.

Each probe needs a receipt line: subject ids, race, and the written field read back at t0.

**Phase 2: main experiment** (only the levers that passed Phase 1)
- **Fort.** BOATS, or a surveyed 1×1 cavern fort with civ-race entries, cavern breached.
- **Load.** 3 citizens working in the band; `sustain` on.
- **Window.** One event plus observation: 36,000 t (30 days).
- **Arms.** 3 arms × 2 reps, in order A-B-C for rep 1 and C-B-A for rep 2, one fresh load per arm.
  - **A, normal rotation.** Irruption off. DF's cavern draws only, roster as built.
  - **B, irruption without tokens.** The rebuilt module's waves: 3 waves × (cluster max × 2) units of one civ race from the cavern's own entry, at the cavern edge, 2 days apart. No behaviour writes.
  - **C, irruption with tokens.** The same waves, with the package: waypoints toward the breach for "wandering", the theft flag by pre-write, CRAZED on at most 20% of each wave, hidden written on the rest.
  - **Optional D** (only if B=C is ambiguous): tokens on normal-rotation civ units, to separate dose from tokens.
- **Metrics,** per civ unit, sampled every 300 t: distance travelled (sum of steps); area covered (unique 4×4 cells visited; bounding box); minimum distance to the nearest citizen and to the breach tile; theft events (`path.goal` = steal or thief, items carried off the map, fort item count); attacks by and on the subject (combat reports); rage episodes (CRAZED or agitated read, combat bursts); share of samples hidden; levers pulled and doors opened; deaths both ways; **citizens alive, sampled directly** (E29's lesson: never infer from the combat log alone).
- **Receipts.**
  - The subject race's units on the map at each wave: arm A counts them too, as the rotation baseline.
  - The written fields read back.
  - The breach readable (`canWalkBetween`).
  - A replicate with zero subject units is a trigger failure, not a result (memory manifest-subject-receipt).
- **Predictions.** C > B > A on distance, area, approach and theft. C > B on attacks. B ≈ A per unit, with more units. Fort survival in C must be 2 of 2: that is the safety criterion.

**Phase 3: rebalance** on the Phase 2 numbers. Wave size, spacing, tier fractions and pressure gains, aimed at "noticeable, survivable" on a 7-dwarf fort.

### 7.7 Rebuilt module sketch (IRRUPT v2; v7.1, behind a switch, off by default)

**Purpose.** A cavern population surges beyond its range under ecological pressure, as waves of wildlife the player can read and respond to. It is never a raid.

**Triggers**: a pressure per cavern depth with additive sources, each config-weighted and decaying.
1. Citizens in the band (kept: T9b).
2. Fort disturbance in the band: dig designations and finished digs, cavern trees felled (plant count delta).
3. Food scarcity: the cavern's prey biomass on the map against the civ race's need. Same arithmetic as `PATTERN.biomassOnMap`, per layer.
4. Crowding: the civ race's population-entry quantity relative to its raw POPULATION_NUMBER.
5. A season multiplier (default: late autumn and winter ×1.5).
6. A minimum interval and a cooldown.

**Features**
- **Species choice.** Civ races (V7.isCivRaw) whose entry exists at that depth, are roster-admitted and are in season. Fall back to cavern predators when no civ race is present. Report "no civ race in cavern N" rather than staying silent.
- **Waves.** N waves (default 3). Size = clamp(cluster max × multiplier, cap). Spacing 1-3 days. Entry at the cavern band's map-edge tiles, farthest from the breach. Each wave is a tracked group (layer cavern, `irruption=true`) with a leader (L10).
- **Behaviour tiers.**
  - *Restless*: waypoints, meander.
  - *Bold*: theft, hidden, MISCHIEVOUS.
  - *Fury* (opt-in): CRAZED or agitated on ≤ 20% of a wave.
  - The player picks the highest tier allowed.
- **Aim (opt-in).** A relation write to citizens on the fury units only (open item 1044).
- **Stand-down.** At the end of the duration, or when none are left: clear every per-unit write, restore caste writes, set each surviving member's countdown to 1-3 days so they leave. Ledger lines throughout.

**Functions**
- `IRRUPT2.pressure(cfg, g)`, `IRRUPT2.sources(depth)`, `IRRUPT2.pick(cfg, depth)`
- `IRRUPT2.wave(cfg, g, ev)` (PLACE.fromEntry in the band plus the group record)
- `IRRUPT2.apply(ev, tier)` (writes recorded in `ev.writes = {uid, field, old}`)
- `IRRUPT2.hold(ev)` (re-apply what decays)
- `IRRUPT2.standDown(ev, why)`, `IRRUPT2.status`, `IRRUPT2.restoreAll()` (disable, All off, unload)

**Config**
```
irruption2 = { enabled=false, sources={citizens=0.02, dig=0.01, scarcity=0.5, crowd=0.3}, decay=0.01,
               threshold=1.0, season_mult={1,1,1.5,1.5}, waves=3, wave_mult=2, wave_cap=20, spacing_days={1,3},
               duration_days=10, cooldown_days=40, tier='restless', fury_share=0.2, aim=false, species='auto' }
```

**Safety**
- Never a permanent raw change: every caste write goes through V7.rec and is restored on stand-down, switch off, disable and unload. DF re-reads raws on load anyway.
- No runtime syndromes. No marauder or invader flags. No `plotinfo.invasions`.
- fb_safe: never pick or write FB, megabeast, night creature or undead.
- Never OPPOSED_TO_LIFE or NOT_LIVING: they flip `isUndead` (Units.cpp:622-626).
- Never write a citizen, a tame or fort unit, a merchant or a visitor.
- Unit and population caps. FUSE deadlines on every scan (memory fail-fast-mandate).
- `quiet_wildlife` alerts kept for non-fury tiers. Fury keeps alerts.

**GUI and console**
- `irruption now [depth] [species]`, `irruption tier restless|bold|fury`, `irruption waves N`, `irruption status`.
- Layers tab: a pressure row per cavern with its sources.
- Live tab: wave groups marked `IRR`.
- Ledger kind `irruption` (kept).

**Validator claims**
- `mech.v71.irr.trigger`: pressure crosses the threshold from a pinned source → a wave is placed within one pass.
- `mech.v71.irr.wave`: N groups, each counted ≤ cap, each led.
- `mech.v71.irr.writes`: every write appears in `ev.writes` and reads back.
- `mech.v71.irr.standdown`: 0 residual writes and caste flags equal to the snapshot.
- `mech.v71.irr.off`: off → nothing placed, nothing written.
- `mech.v71.irr.fbsafe`: never a FB race.
- `gui.irr.row`: the Layers and Live rows.

**Release fit**
- v7.1, after v7.0 is revalidated on DFHack r2 (STATE:4122-4128).
- v6.1's IRRUPT is kept as `tier=fury, waves=0` (legacy) until Phase 2 passes.
- Docs: USAGE "irruption" entry rewritten; the agitated definition (USAGE:64) kept for the fury tier.

---

## Item 8: pelagic predators into shallow water

### 8.1 Why fortress ocean water is shallow, and why the slot came out empty

**Measured depth** [MEASURED]

| Fort | Columns | 1 level | 2 levels | 3 levels | 4 levels | Source |
|---|---|---|---|---|---|---|
| OCEAN2 (192×192) | 21,328 | 9,116 | 12,212 | 0 | 0 | O, findings:96-99; ECO/20260929-235553/O.tsv |
| BOATS (288×288) | 36,650 | 14,846 | 9,759 | 8,564 | 3,481 (33% at ≥3) | DEPTH.tsv; reported in design:349-351 |
| LAKE | 31,047 | 28,150 (91%) | 1,563 | 1,334 | 0 | DEPTHL, findings:80 |

These come from the `cx-eco depth` histogram: levels with flow ≥ 4, counted down from the top water tile (cx-eco:86-100, :236-246).

**Why so shallow** [DOCUMENTED / INFERRED]
- The wiki gives no z-level depth for embark oceans (wiki Ocean: nothing on depth or on distance from shore). The raws have no depth token (wiki-tokens:238).
- So depth is a property of the embark's terrain generation and varies by site: OCEAN2 1-2 levels, BOATS up to 4. It is not a creature rule.
- Placed whale sharks and blue sharks lived, stayed wet and moved in 1-2 levels for 3,000 t (O and OS: spread 13/43 and 53/46). Shallow water holds pelagics physically.

**Why nothing pelagic arrived on OCEAN2** (S8O, findings:449-455; corrected at findings:597-599). Five causes stack:
1. **Roster.** v7.0's water slot table has **one** AW apex slot, min 1 max 1, shared by ocean, lake and river species (sw.lua:5081-5082).
   - ORCA is curated as a predator (sw.lua:1199), so it is MW, and becomes AW at ≥ 1,000,000 cm³ (sw.lua:5066-5071).
   - The great white is LP, so AW.
   - S8O's roster put CROCODILE_SALTWATER in that slot (findings:450), which leaves no pelagic apex to draw.
   - The desk design had a separate **APE** (pelagic apex) slot for oceans (design:135, :275). **It was not ported** [INFERRED, code vs design].
2. **PE is pelagic *prey*** (whale shark, basking shark, manta, sunfish …; guild test sw.lua:1393), with min 0 max 1 (sw.lua:5082). The builder left it empty.
3. **Draw weight.** Every ocean aquatic animal over `pelagic_ref` (1,000,000 cm³), the predators included, is weighted `FREQUENCY × 0.1` when the survey finds 0 deep columns (sw.lua:4900-4909). So even when present on the roster, it draws about one tenth as often.
4. **Survey bug** [INFERRED, high confidence; needs a rig read].
   - `ENGINE.waterTiles` scans z from the top down at stride 2 (sw.lua:4792, 4798-4799), and breaks after a z-level once it holds `TILE_CAP` = 3,000 tiles (sw.lua:4783, 4822).
   - OCEAN2's surface level alone holds ~21,328/4 ≈ 5,330 sampled tiles: the survey's own total was 5,374 (findings:451). So the scan stopped after the top level, and `ENGINE.deepColumns` (sw.lua:4870-4898) saw every column as 1 level deep.
   - OCEAN2's answer (0 at ≥ 3) happens to be right. BOATS (~9,160 sampled surface tiles) would also read 0, against 12,045 real columns at ≥ 3.
   - Check on the rig, read-only: `ENGINE.deepColumns(cfg,true)` on BOATS against DEPTH.
5. **Shared water ceiling** of 12 animals (sw.lua:462) and 2-5 groups per body (SW6): a pelagic predator competes with fish schools for room.

### 8.2 Rebalance: prey present pulls pelagic predators in (design)

| Option | How | Pro | Risk |
|---|---|---|---|
| **A. Prey-presence weight** (recommended core) | In `ENGINE.weight`, for an ocean predator: `w = FREQ × clamp(k × preyMass_ocean / predMass, floor, cap)`. preyMass counts live wet units of species the predator `eats()` in this body (FC, PE, SH, swimming WB per WB/REACH) | Directly "prey pulls predator"; deterministic; cheap | Overshoot when a big prey school is present: tiger sharks took 5/10/1 of 10 milkfish (HO, findings:154). Bound by the cap and the water ceiling |
| **B. Water coupling on by default for pelagics** | Already exists: a prey draw sets `g.water_couple` to its predators for 2 days (sw.lua:4950-4955), gated on `cfg.groups.coupling` (default off, sw.lua:472). Turn it on for the water layer only | Built; ledger-visible | The coupling restricts the next draw to the predators, so fish rotation slows |
| **C. Seed near prey, in the deepest water** | When a predator is drawn, pick the seed tile among ocean tiles ≥ 2 levels deep within R of the prey group's centroid, and ≥ 3 tiles from any dry tile. Today the seed is uniform (sw.lua:4930) | Arrives where the prey is, without teleports; less beaching | Needs a real per-column depth (fix 4) |
| **D. Water nudge** (like the land ecology nudge) | Teleport a predator within R of prey | — | Land result: no measurable effect (SW1/SW1R), and a teleport strands animals (T5, STATE:1500-1506). In water a teleport near shore risks beaching. **Not recommended** |
| **E. Relax the depth gate when prey is present** | Use `deep_levels` = 2 (OCEAN2 has 57% of columns at 2), or replace the binary gate with a suitability score (share of columns ≥ 2, max depth), and lift the 0.1 floor while prey is present | Brings sharks into a 2-level sea | Orca and sperm whale beaching (BEACH_FREQUENCY 10, tokens). Mitigate with the guard below |
| **F. Port the APE slot** (`{code='APE',min=0,max=1}` on maps with ocean tiles, separate from AW) | Lets a coastal apex and a pelagic apex coexist | Matches design:275 | One more predator: check the outgun and ladder shares |

**Recommended package:** fix 4 (survey) + F + A + C + E. B is kept as is.

**Stranding guard** (needed with any option)
- Each groups pass: an aquatic member (`MODEL.isWater`, AQUATIC) on a tile with flow < 4 for two consecutive passes is moved to the nearest suitable water tile within 6 (like `regroundNear`, sw.lua:4412) and logged `stranded→water`.
- Optionally, while a BEACH_FREQUENCY species is resident, write caste `misc.beach_frequency = 0` through V7.rec and restore it on leave or unload. The field is xml/df.creature.xml:1057. Beaching "immobile and unable to breathe", per the wiki Beaching page (flagged possibly outdated for 53.16).

**Experiment PELA**
- **Forts.** OCEAN2 (shallow) and BOATS (deep).
- **Arms.** 2 arms × 2 reps × 2 forts:
  - *v7.0 as shipped*
  - *pull package*
- **Pre.** Driver B `call` a FISH_MILKFISH school into the ocean at t0. The receipt is the school present and wet.
- **Window.** 30,000 t.
- **Metrics.**
  - Pelagic predator arrivals and resident time.
  - Distance from predator to prey.
  - Attacks and kills on prey (incidents).
  - Prey on the map over time.
  - Strandings (aquatic units on dry tiles, for two samples), DROWN deaths, guard moves.
  - The corrected deepColumns readout (manipulation check).
- **Kill criterion.** Any stranding death in the pull arm that the guard did not catch.

---

## Item 9: leaders for every aquatic group that groups

### 9.1 How leaders are assigned today [INFERRED from code; MEASURED where cited]

**The pass**
- `applyCohesion` runs on every tracked group each groups pass, every 300 t (sw.lua:5906-5936; cadence sw.lua:3391).
- Label (sw.lua:5857-5864): a water species (`MODEL.isWater`: aquatic or semiaquatic) gets **school** (there is no "pod" label; orcas get school), a flier gets flock, an LP gets pack, everything else herd.
- With `groups.cohesion` on (default, sw.lua:473), not dismissed, and **≥ 2 live, active members**:
  - The leader is chosen by `V7.leaderOf`: with `leader_male` on (default, sw.lua:499), the largest adult male, else the largest adult, else the lowest id. A living leader keeps the role (sw.lua:5889-5905).
  - Every other free member gets `following = leader`, `owner_type = PACK_LEADER`, `follow_distance = follow_school` (5; sw.lua:473).

**Re-election.** A dead or departed leader drops out of `liveMembers` (sw.lua:5865-5873), and the next pass picks a new one and re-points every follower. There is a gap of up to 300 t in which followers point at the old leader. E28 saw the same-pass re-pick work on land (STATE:1449-1451).

**Which groups exist**
- DF's arrivals that carry the roaming flag and `feature_idx == -1` (gatedLayer, sw.lua:3511-3519). An ocean surface wave arriving through the wet edge (addendum 23) is tracked as a `land` group, labelled school, and led.
- Driver B draws (ENGINE.draw, sw.lua:4920-4956): `resident=true, layer='water'`, placed within RADIUS 6 of one seed (sw.lua:4930-4945). Led on the next pass.

**Excluded by design.** Sponges are never a group or counted (sw.lua:2778, 5461-5557). Correct: they are scenery.

### 9.2 Why the stranded orcas were unled

- **COHO was a harness experiment.** It spawned orcas with `cx-eco spawn`, which makes no tool group. Its *none* arm ran `cx-eco lead ORCA none`, setting `following = nil` (cx-eco:548-567). The 3 of 12 DROWN deaths were all in that control arm: rep 1 one orca at dt 12,639, rep 2 two (COH-20261001-000915/COHO.tsv; log.txt:14-20; findings:456-459). [MEASURED]
- **No production path drew those orcas.** S8O's own Driver B draws were milkfish and stingrays (findings:452).
- **The harness's *led* arm is not the tool's lever.**
  - It sets only `u.following`, with no owner_type and no follow_distance.
  - The led pod was 100-126 tiles wide for the first 7,500 t and tight only from t9,000 (COHO.tsv rows t3000-t13500: width 109 → 2).
  - So "a leader holds an orca pod (44-49 vs 87-100)" is a **harness-lever** result. The tool's PACK_LEADER plus follow_distance 5 in water is **unmeasured**: E28 (land dingoes) is the only measurement of the tool's lever.

**Real holes in production** [INFERRED from code]
1. **`place` verb.** PLACE.fromEntry is called with no group record (sw.lua:7715-7720), so the animals are never led. It also scatters them: each animal goes to a random tile from the whole band's scan (sw.lua:4021-4027), not a cluster.
2. **DF's embark-seeded water life** (feature populations, `feature_idx ≠ -1`) is never tracked (sw.lua:3511-3519; E26/addendum 35), so it is never led. A school of carp seeded at embark roams unled.
3. **No wetness check on the leader.** A leader on a dry or shallow edge tile pulls the pod after it: a stranding cascade.
4. **A group with one live member** is never led. That is correct for one animal. But a group that arrives across two passes is unled for the first one.
5. **Uneven leave countdowns.** Driver B gives each member a countdown jittered ±20% (sw.lua:4941). The leader may leave first. Followers then re-elect, which is fine, or the pod splits across the edge.
6. **Mixed-species ids.** `liveMembers` requires `isActive` (sw.lua:5869), which is fine.

### 9.3 Fix (design)

- **F1.** Every tool placement of a cohesive species creates a tracked group: `place`, any future irruption waves, Driver B. Placement is clustered around one seed, as Driver B does it. Label `pod` for cetaceans (ORCA, NARWHAL, SPERM_WHALE: BEACH_FREQUENCY or the mammal class), with its own `follow_pod` setting (default 5; tighten to 3 after the test).
- **F2.** Apply cohesion **in the same pass as the draw or placement**, not the next one.
- **F3.** Leader eligibility for water groups: the leader must stand on a tile with flow ≥ 4 (and depth ≥ 2 where any exists). Else re-elect the wet member nearest the deepest water. If no member is wet, the stranding guard (item 8) runs first, then the election.
- **F4.** Re-elect immediately when the leader is dead, inactive, off the map, has leave_countdown ≤ 300, or has goal SeekStation/LeaveWall (leaving). Sync the group's countdowns to the leader's at draw time, so a pod leaves together.
- **F5.** Optionally adopt DF's seeded feature schools: track feature-population water units as `layer='water', seeded=true` groups for cohesion only. They are never gated and never counted against the water groups-at-once limit.
- **F6.** Never lead sponges, vermin, or anything with IMMOBILE.

**Validator claims**
- `mech.v71.lead.water`: after `water call ORCA` (or a Driver B draw of a species with cluster ≥ 2), in the same pass every member except the leader has `following == leader`, `owner_type == PACK_LEADER`, `follow_distance == follow_pod`.
- `mech.v71.lead.place`: `place ORCA 6 water` → one tracked group, clustered (max Chebyshev distance to the seed ≤ 6), led.
- `mech.v71.lead.reelect`: kill the leader (or zero its countdown) → at the next pass a new leader, and no follower pointing at a dead or departed unit.
- `mech.v71.lead.wet`: the leader of every water group stands on flow ≥ 4.
- `mech.v71.lead.sponge`: no sponge in any group.

**Test COHT** (the tool's lever, in water)
- **Fort.** OCEAN2.
- **Arms.** 6 orcas drawn by Driver B `call`: tool cohesion on vs off. 2 reps, 15,000 t, fresh load per arm.
- **Metrics.** Width; leader distance; strandings (dry tile for two samples); DROWN deaths; re-elections from the ledger.
- **Same block.** A milkfish school, to compare with COHO's harness numbers.
- **Receipt.** The group record present and the PACK_LEADER count read at t0+300.

---

## 4. Report revisions held (not applied)

1. **Item 7 block on the ECO page.** Replace "Flags don't start cavern invasions" with:
   - the invasion vs irruption definitions in 7.2;
   - the current-module summary (7.1 table);
   - a note that E23e closes DF invasions as unreachable by flags;
   - a pointer to the irruption rebuild programme.
2. **Item 8 block.** "Fortress water is shallow" stays. Add BOATS 33% ≥ 3 levels. Correct "the pelagic slot stayed empty" to the three causes (single AW slot, PE = prey with min 0, 0.1× weight). Flag the suspected survey truncation as INFERRED pending a rig read.
3. **Item 9 block.** "Placed orcas strand when unled" → "Harness-placed orcas in the unled control arm stranded (3 of 12). The harness's leader lever (following only) held them after ~9,000 t. The tool's own lever is unmeasured in water. The `place` verb creates unled, scattered animals."
4. **Findings line 457.** Make the same distinction (COHO harness lever vs tool lever).
