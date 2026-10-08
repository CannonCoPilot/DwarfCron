# Food web construction and enforcement — seasonal-wildlife, read from the code

Source: `/Users/nathanielcannon/Claude/Projects/sw-wt/plugin`, branch `v7.2-plugin`, HEAD `8185d85`, clean tree.
Read-only study. Nothing was run against the game. Line numbers below are in `scripts/seasonal-wildlife.lua` (called **SW**) unless another file is named.
The code is treated as the truth. Where a doc or a comment says something else, it is flagged.
The vanilla raw facts quoted in section 10 (which species are BENIGN, what MINK carries) come from a read of the installed DF 53.16 raw text files with Python. The game was not touched.

---

## 0. Short version

- **The relation write is the only lever that makes wild animals hunt.** Everything else either decides which species are on the map, or moves animals so they meet.
- **The code has four edge rules that do not agree.** (1) A mass rule `eats()`. (2) A tier rule `ROSTER.linkable` / `ROSTER.castEats`, used by the builder and the season casts. (3) The relation write's own filter, `ecoWrite`. (4) The vermin gobble wiring. The web companion draws a fifth picture: `eats()` plus a habitat table.
- **Who the write relates.** Each pass it pairs every *armed* predator (any food-web predator that is not wholly BENIGN, plus raptors and cavern civ races) with every *non-armed* wild animal in the same realm. A pair must pass a reach test, the raptor size cap, the pack-mass floor and, when casts are on, the season cast's edge list. The cell is written PREDATOR_OR_PREY in both directions.
- **Season casts (v7.3, on by default) narrow the web to the cast's edges.** Cast edges are built one layer at a time and only point down a tier. So with casts on:
  - no cross-layer predation is ever written (alligator × deer, bear × fish, osprey × fish);
  - no apex × mesopredator pair is written;
  - every cast edge whose predator is BENIGN (badger, fox, stoat, sperm whale…) is a dead edge.
- **Parking (v7.3).** `V7.parkNudges` forces nudge, coupling, vermin foraging, raptor stoop, the fishers master switch and panic **off at every config load**. No verb un-parks them, and the verbs that turn them on are reverted at the next reload. In some verbs that reload is immediate.
- **`enable` turns "Livestock as prey" ON.** `PANEL.fortOn` sets every non-parked Panel switch, opt-ins included. `ecology.livestock = true` then relates **every armed predator in every realm**, cavern 1–3 included, to the fort's livestock and pets. It also bypasses the `v7.domestic` guild rule.
- **Nothing undoes the relation cells.** Disable and All off leave every written PREDATOR_OR_PREY cell in DF's table. They also leave cohesion follow links, fishing paths and panic paths in place.

---

## 1. Inputs: how a species is read

`classify(craw)` (SW:~1790–1880) builds the per-species record that every rule reads. The fields that matter here:

| Field | Source | Line |
|---|---|---|
| `mass` | `adultSize(craw)`: the largest caste's last `body_size` × 10. DF stores 10 cm³ units, so this is cm³ and equals the raw BODY_SIZE (WOLF 40,000; ELK 300,000; BIRD_EAGLE 4,000) | SW:1454–1462 |
| `habitat` | `MODEL.habitat`: `aquatic` if IMMOBILE_LAND or CANNOT_BREATHE_AIR; flier → `waterbird`/`flier` by biome; `semiaquatic` if CAN_BREATHE_WATER **or every biome is water**; else `land` | SW:1893–1904 |
| `role` / `cat` | `MODEL.role`: predator if any caste has CARNIVORE, BONECARN, LARGE_PREDATOR or AMBUSHPREDATOR, or the curated `MODEL.ROLE` (ORCA, GIANT_ORCA, GIANT_CUTTLEFISH predator; SHARK_WHALE prey); vermin flags → `cat='vermin'` | SW:1708–1719, 1905–1910, 1801–1808 |
| `benign` | BENIGN on **all** castes, unless curated predator | SW:1821 |
| `guild` | `MODEL.guild`: V, AW, RP, AL, MW, ML, GZ, WB/LB, PE/FC/FF, SH, PL in that precedence | SW:1938–1962 |
| `largePred`, `ambush`, `cmin/cmax`, `group` | caste flags, cluster range | SW:1810–1830 |
| animal people | role, habitat and diet mirror the root animal; mass = own (gravitated toward 70,000 cm³); a vermin root → small predator (`apVermin`) | SW:1840–1872 |
| `civ` | `V7.isCivRaw`: CAN_SPEAK/LEARN, not GOOD/EVIL, not an animal person, subterranean | SW:2258 |

Size bands: small < 150,000 cm³, medium < 1,000,000, large ≥ 1,000,000 (`MODEL.SMALL/LARGE`, SW:1708).

---

## 2. Where predator–prey edges come from

### 2.1 Four rule sets (plus a fifth on the web page)

| Rule | Function | Test | Used by |
|---|---|---|---|
| **Mass rule** | `eats(e,p)` SW:2547–2563 | same eco class, same realm, predator `cat`, REACH, shared water, no eating a predator ≥ 0.5× own mass, `take ≥ need` | matrix roster pair guarantee SW:2778; co-align SW:2811; fill partners SW:2844; coupling `startCoupling` SW:4483; water coupling SW:6142; water pull and feed `V7.WAT.eats` SW:6262; species detail SW:17302; web page graph (`seasonal-wildlife-web.lua:132`) |
| **Reach only** | `MODEL.reaches(e,p)` SW:2565–2575 | no mega/night, not NEVER_PREY, same eco class, same realm (by the **entry's** layer, SW:2569), REACH, shared water. No size test | the relation write (species memo), cast edges, builder links |
| **Tier rule** | `ROSTER.linkable` SW:7794 / `ROSTER.castEats` SW:8416 | tier(pred) > tier(prey) strictly, `MODEL.reaches`, a shared cavern depth | builder `ROSTER.build` SW:8064; season casts `ROSTER.castGrow` SW:8451; exhaustion replacement `ROSTER.castReplaceOk` |
| **Relation-write filter** | `ecoWrite` SW:5077–5231 | armed predator (`ecoArmed`) × non-armed target (`ecoIsTarget`), reach, raptor cap, fisher exception, cast edge, pack floor (§3.4) | DF's relation table, which is the behaviour |
| **Vermin gobble** | `VERMIN.gobbleWants` SW:~14644 | guild rules + edge table → SWV classes | caste `gobble_vermin_class` writes (§2.6) |
| *(web graph)* | `poolAndPairs` `seasonal-wildlife-web.lua:80–137` | `sw.eats` for units; `huntsVermin` (HUNT flags + a habitat→family table, :62–73) for vermin | the browser's food-web picture only |

So the web page and the species detail page show `eats()` edges. The season cast is grown on tier edges. The animals act on `ecoWrite` pairs. These three sets differ (examples in §10).

### 2.2 The mass rule (`PRED`, SW:2496–2585)

```
take = M_pred × G_pred^pack_exp × k        k = k_large (1.5) if LARGE_PREDATOR or AMBUSHPREDATOR, else 1
need = M_prey × (need_herd 0.9 if prey group > 1, else need_solo 0.6)
can  = take ≥ need
preference = exp(−(ln(M_prey / (ideal·M_pred)))² / (2σ²))   ideal 0.4, σ 1.2; vermin 0.05
```

- `PRED = { pack_exp=0.75, k_large=1.5, need_solo=0.6, need_herd=0.9, ideal=0.4, sigma=1.2 }` (SW:2516).
- The config can override it through `cfg.roster.pred`, copied in once per load by `V7.rosterSync` (SW:~7625).
- `G` is the raw cluster midpoint (`group`), not the group that is actually on the map.
- The **×1.5** "large predator" factor lives only here, so it never reaches the relation write.
- Peers: a predator never eats another predator of ≥ 0.5× its own mass (SW:2561).

### 2.3 REACH (habitat × habitat), SW:2531–2537

| predator \ prey | land | flier | waterbird | semiaquatic | aquatic |
|---|---|---|---|---|---|
| land | ✓ | ✓ | ✓ | ✓ | — |
| flier | ✓ | ✓ | ✓ | ✓ | — |
| waterbird | ✓ | ✓ | ✓ | ✓ | ✓ |
| semiaquatic | ✓ | — | ✓ | ✓ | ✓ |
| aquatic | — | — | ✓ | ✓ | ✓ |

- Two aquatic animals must also share a water-body type from their raw biomes (`MODEL.sharesWater`, SW:2538).
- `MODEL.NEVER_PREY = {SPONGE, GIANT_SPONGE}` (SW:2546).

### 2.4 The builder (`ROSTER.build`, SW:8064–8262) — selection, not behaviour

- **Tiers** (`ROSTER.TIER`, SW:7667): APX/APE/AL/AW = 3; ML/MW/RP/SN = 2; prey guilds = 1; V = 0.
- **Slot** (`ROSTER.slotOf`, SW:7685):
  - on the water layer, a curated `aquatic_apex` 'pelagic' is APE and 'apex'/'fisher' is APX;
  - any other water predator is MW;
  - a civ race's AL/AW reads ML/MW (with civ_prey).
- **Links** (`ROSTER.linkable`): strictly down a tier, `MODEL.reaches`, and a shared cavern depth.
- **Pick weight** (`ROSTER.pickWeight`, SW:~7829): ×`roster.pack_bonus` (**3**) for a non-BENIGN group hunter in tier ≥ 2 (`ROSTER.packBonus`, SW:7789); ×0.1 for an animal person, ×0.2 for a giant; × (1 + Σ preference over linked members).
- **Outgun** (`ROSTER.outgunPairs`, SW:7805): warns when prey group mass ≥ `v7.outgun` (**2.0**) × predator group mass. With `outgun_cap` (off) it also caps the prey's `group_size`.
- **Output.** Allow flags and a FREQUENCY ladder (`ROSTER.ladder`). Then it builds the gobble edge table (`ROSTER.gobbleEdges`, SW:8007).

It writes **no** relations, and the relation write never reads the builder's links.

### 2.5 Season casts (v7.3) — the season's edges

- **Config.** `ROSTER.CAST` slots per layer (SW:8282–8297). `ROSTER.CAST_DEF = {enabled=true, carry=0.25, giant=0.2, pack=3, hv_petvalue=200, hv_mass=1,000,000}` (SW:8298).
- **Growth** (`ROSTER.castGrow`, SW:8451–8572), per layer and season:
  1. Seed with one high-value species (`ROSTER.highValue`, SW:8349: pet value ≥ 200, war/hunt trainable, ivory/pearl/silk/shell, or ≥ 1,000,000 cm³).
  2. Repeatedly add a prey or predator of a random member into the emptiest slot.
  3. Add up to 2–3 vermin that a member eats (`ROSTER.vdiet`).
  4. Last season's members are weighted ×0.25.
- **Edges.** `out.edges` lists every `castEats` pair among cast members (SW:8562–8564). `castEats` (SW:8416) is the tier rule plus `MODEL.reaches` and a shared cavern depth.
- **Layers are grown separately.** Land merges the `land` and `flying` partitions. Water and cavern each use only their own partition (`ROSTER.CAST[layer].parts`).
- **Enforcement.** `ROSTER.castEdgeSet(cfg, season)` (SW:8673–8684) unions the current season's edges from every layer into `{"PRED|PREY"}`. `ecoWrite` drops any wild pair whose species pair is not in that set (SW:5128, 5183).
- **The set changes every season**, since the cast does. Casts are rebuilt each new year (`V7.ST.turn`, SW:4098–4100), on `enable` (SW:16105) and on `cast rebuild` (SW:18362).
- **Cast on/off.** `ROSTER.castOn` needs `cfg.cast.enabled` **and** an existing `cfg.casts` (SW:8305). Before the first cast build, the write is not cast-gated.

### 2.6 Vermin: SWV classes and gobble wiring

Vermin are not units. "Eating" them is DF's gobble behaviour, which is keyed on creature classes.

- **SWV taxonomy** (`VERMIN.SWV`, SW:3351; `VERMIN.swvClass`, SW:3361–3382). Ten classes:
  - SWV_GROUND_BUG (DF's EDIBLE_GROUND_BUG members, plus VERMIN_GROUNDER without bones);
  - SWV_SMALL_FISH (VERMIN_FISH / AQUATIC_UNDERSWIM / IMMOBILE_LAND);
  - SWV_FLYING_INSECT (VERMIN_MICRO / ROTTER / non-egg fliers);
  - SWV_COLONY (VERMIN_SOIL_COLONY);
  - SWV_SOIL;
  - SWV_BAT / SWV_SMALL_MAMMAL (MAMMAL class);
  - SWV_SMALL_BIRD (egg-laying non-mammal flier);
  - SWV_HERP (AMPHIBIOUS, or a walker with bones);
  - SWV_OTHER.
- **Who eats what.** `VERMIN.gobbleWants` (SW:~14644) takes the union of two sources, chosen by `vermin_eat.source` (default `both`). Classes switched off in `vermin_eat.classes` are skipped.
  - **Rules** (`VERMIN.GOBBLE_RULES`, SW:14545–14556):

    | Rule | Consumers | Classes eaten |
    |---|---|---|
    | small land insectivore | ML/PL/SH < 10,000 cm³ (carnivore or not GRAZER) | GROUND_BUG, SOIL, COLONY |
    | waterbird / fish-eater | WB/FF/FC | SMALL_FISH |
    | raptor | RP | SMALL_BIRD, BAT, SMALL_MAMMAL |
    | land bird | LB | FLYING_INSECT |
    | snake | ML **and** `VERMIN.legless` | SMALL_MAMMAL, HERP (**dead rule**, §10.B4) |

  - **Edge table.** `VERMIN.GOBBLE_EDGES` (SW:14571–14583) is a guild → builder-vermin-class map:

    | Guild | Vermin classes |
    |---|---|
    | ML | VG, VC, VF |
    | AW | VF |
    | MW | VF |
    | RP | VB, VI |
    | LB (cave only) | VB, VI, VG |
    | native gobblers | nothing |

    After any `roster build`, `VERMIN.edges` (SW:14607) swaps this table for per-species rows taken from the builder's random `ROSTER.GOBBLE_EDGES` (`VERMIN.rosterRows`). `VERMIN.VCLASS` (SW:14568) maps VG/VC/VF/VB/VI onto SWV classes.
- **The writes** (`VERMIN.gobbleApply`, SW:14663–14699), done inside `V7.apply`:
  - Tag each in-embark vermin species, and each natural vermin species present on the map, with its `SWV_*` creature class (caste `creature_class`).
  - On each consumer caste, write `GOBBLE_VERMIN_CLASS:SWV_*` and the VERMIN_GOBBLER flag.
  - SWV_GROUND_BUG also gets `EDIBLE_GROUND_BUG`.
  - A class with ≤ `gobble_creature_fallback` (3) members also gets one `GOBBLE_VERMIN_CREATURE:<tok>` with caste `ALL` per member.
  - Consumers are every in-embark, unlocked, non-vermin pool species, whatever their roster state or season.
- **Cast vermin diet** (`ROSTER.VDIET`, SW:7980; `ROSTER.vdiet`): ML eats VG/VC/VF; MW eats VF; aquatic APX eats VF; RP eats VB/VI; cavern LB also eats VB/VI/VG. This only decides which vermin species are cast. It writes nothing.
- **HUNT flags** (opt-in `hunting.enabled`, `HUNT.apply`, SW:13387):
  - DIVE_HUNTS_VERMIN on waterbirds and predatory fliers;
  - HUNTS_VERMIN on small land/semiaquatic predators;
  - only for allowed, in-embark species.

### 2.7 Hard-coded species lists (none are predator–prey pair lists)

| List | Line | Effect |
|---|---|---|
| `MODEL.ROLE` | SW:1713–1718 | ORCA/GIANT_ORCA/GIANT_CUTTLEFISH are predators (and lose BENIGN, §3.2); SHARK_WHALE is prey |
| `MODEL.NEVER_PREY` | SW:2546 | sponges are never prey; the sweep also clears DF's writes onto them |
| `roster.aquatic_apex` / `V7.WAT.APEX` | SW:7570–7585 / 6172–6185 | curated water apex/pelagic/fisher slots, and pull level 'A' |
| `v7.fisher_list` | SW:846–848 | nine bears true; TIGER, JAGUAR, RACCOON false |
| `hunters.swim_scav_list` | SW:814–815 | five BENIGN sharks are scavengers; FISH_LAMPREY_SEA is not |
| `hunters.stoop.skip` | SW:812 | BIRD_VULTURE never stoops |
| `SCAV.TEXT` | SW:14811 | vulture, buzzard, black bear, jackal, hyena, raven, flesh ball are scavengers |
| `ROSTER.FLY_SCAV` | SW:7670 | scavenger birds are never the flying apex |
| `V7.H.POLAR` | SW:9613 | polar bears swim to fish |
| `V7.EXTINCT` table | SW:~13930–14100 | per-species corrections to LP/CARNIVORE/BENIGN/guild for extinct animals (model and raws) |

---

## 3. The ecology pass

### 3.1 Schedule and gate

- `scheduleGroups` (SW:13330) registers `ecologyJob` every `ecology.cadence` ticks (**3,000**) **only if `ecology.enabled` at schedule time**.
- `ecologyJob` (SW:9570–9578) returns unless `cfg.enabled and cfg.groups.enabled and cfg.ecology.enabled`. So turning groups off stops ecology too (`disableGroups` cancels the job, SW:13342).
- Each pass runs `ecologyRun` (SW:5468–5510), then `V7.soloUnits()` (skills onto new units), then saves the groups state.
- Order inside `ecologyRun`:
  1. `ecoClearDeparted` (SW:5024): every slot the tool recorded whose unit died, left or was re-slotted gets its whole row and column set to **NONE (-1)**. A slot DF has given to a non-natural unit is skipped (fb_safe).
  2. `ecoPredatorSet` (SW:4972): the armed set by token, rebuilt per `CACHE.ver`.
  3. Unit walk over `units.active`: a unit is a **predator** if `ecoIsPredator` (on map, natural, a realm, in the armed set); otherwise a **target** if `ecoIsTarget`.
  4. With `civ_prey` on, armed civ-race units are added to the target list as well (`wtargets`, SW:5485–5490).
  5. `ecoWrite` (§3.4).
  6. `V7.sweep` (§3.5).
  7. `V7.H.stoop` and `V7.H.fish` (§4.3, §4.4), each in a pcall.
  8. `ecoNudge` if `ecology.nudge` (§3.6).
  9. A ledger line, and `g.ecology.last` for status.

### 3.2 Who is armed (`ecoArmed`, SW:4958–4971)

An entry on the land, water or cavern layer, not locked, is armed if any of these holds:

- **civ race**: `civ` and `v7.civ_hunt` and guild in AL/AW/ML/MW/RP and not benign;
- **raptor**: guild RP, not civ, `hunters.raptors` on. RP castes have BENIGN cleared by `V7.apply` (SW:13837–13839);
- **ordinary**: `cat == 'predator' and not benign`.

Deep (magma sea, underworld) entries are never armed. The curated `MODEL.ROLE` predators (orca) count as not benign (SW:1821), and `CURIOUS.apply` clears their BENIGN castes while ecology is on (SW:13464–13476).

**Not armed:** every BENIGN predator-by-diet that is not RP and not in `MODEL.ROLE`. In vanilla 53.16 that includes BADGER, FOX, STOAT, MONGOOSE, WOLVERINE, CAT, SPERM_WHALE, BIRD_SWALLOW_CAVE_GIANT and several extinct species (raw read). Their prey are never related to them.

### 3.3 Targets (`ecoIsTarget`, SW:4994–5005)

- **Never a target:** dead or inactive units, non-natural units (fb_safe), citizens, and non-animal merchants.
- **Wild units** are targets if they have a realm, are not a sponge, and are **not of an armed species**. So armed predators never become prey of each other (except civ races under civ_prey).
- **Tame own-civ animals** (`V7.isDomestic`) are targets only if `ecology.livestock` or `v7.domestic`.
- **Any other animal** (caravan pack animals, visitor mounts, invaders' beasts) is always a target.

### 3.4 The write (`ecoWrite`, SW:5077–5231)

For each predator `a` (with `ea` = its species entry) × target `b`, the checks run in this order:

| Step | Rule | Line |
|---|---|---|
| realm | non-wild target (`rb==true`): **any realm**; wild: `ecoRealm(a)==ecoRealm(b)`. Realms: `land` (land and water layers), `cavern:0..2` | 5158, 4946–4951 |
| civ_prey | a civ-race target only for a non-civ AL/AW predator | 5161 |
| domestic | with `v7.domestic` on and `livestock` off: own livestock only for AL/ML guild or any cavern-layer predator (`V7.takesDomestic`) | 5162, 5011–5017 |
| non-wild target | predator not aquatic; raptor only if target's current size ≤ `stoop.prey_ratio` (2) × raptor mass | 5164–5175 |
| wild target with an entry | species memo: `MODEL.reaches`; raptor size cap; **fisher exception** (listed land predator × aquatic prey allowed when `v7.fishers`); **cast edge** required when casts are on | 5177–5186 |
| pack floor / SNEAK | `share = packN[a] × mass(a) / mass(b)`; `share < v7.pack_floor` (0.05) → drop; `share ≥ v7.pack_sneak` (0.25) → SNEAK `hunters.skills.pack_bonus` (10) on the unit's soul, once per predator a pass | 5187–5194 |
| wild target **with no entry** | allowed with **no reach, cast or floor test** | 5195 |

Then, for an allowed pair:

- `allow[a,b]` and `allow[b,a]` are recorded in `CACHE.ecoAllow` for the sweep, stoop and fishing (SW:5200).
- **Slotting.** A unit with `enemy_status_slot < 0` is given a free slot by `PLACE.enemySlot` (SW:4866–4883). That function marks `slot_used`, clears the new row and column to NONE, sets `enemy_status_slot` and bumps `next_slot`.
- **Write.** `rel_map[sa][sb].ur = PREDATOR_OR_PREY` **and** `rel_map[sb][sa].ur = PREDATOR_OR_PREY`, a symmetric pair (SW:5217).
- **Memo.** `CACHE.ecoDone[sa·65536+sb] = a.id·2²⁰+b.id`. A remembered pair is counted and skipped. The memo is cleared on every map load (SW:17091) and every `ECO.REFRESH` = 8th pass (SW:5085).
- **Record.** `g.ecology.pairs["PRED|PREY"]` counts each write; the `ecology pairs` verb shows it (SW:18700–18731). A target with no entry is labelled `DOMESTIC`, even a caravan animal.

**Budget** (`ECO`, SW:5076): write 30 ms, sweep 20 ms, the whole pass capped at `PASS_MS` 35 ms from its start, each part guaranteed `MIN_MS` 5 ms. Pairs past the deadline are counted `deferred` and wait for the next pass. **Cost** is O(predators × targets) per pass. The species verdict is memoised per (predator entry, target entry).

### 3.5 The sweep (`V7.sweep`, SW:5252–5325; `v7.sweep` default on)

- After the write, every PREDATOR_OR_PREY cell (either direction) between two **managed wild** units whose pair was not allowed this pass is set to **NONE**.
- "Managed wild" is `V7.managedWild`, SW:5243: alive, active, wild, not tame/citizen/merchant, natural, a non-locked pool species, not undead.
- It walks O(m²) in a 20 ms slice and resumes where it stopped.
- It counts `refought`: a pair DF wrote back within 4 passes.
- It also clears any non-BENIGN unit's PREDATOR_OR_PREY cell onto a sponge (SW:5300–5311).
- This is what makes casts and resting stick: DF's own wild-on-wild writes between managed species are removed every pass. Fort-side cells (tame, citizens, caravans) are never touched.

### 3.6 The nudge (`ecoNudge`, SW:5436–5466; `ecology.nudge` default false **and parked**)

- A predator farther than `far_tiles` (40) from its nearest same-realm target for `far_ticks` (3,000) is teleported to a ground tile, or a water tile for a water creature, within `radius` (6) of that target, at the target's z (`ecoPlaceNear`, SW:5408).
- Fix `e494d33` (SW:5442–5451): a non-wild target counts as realm `land`, so a cavern predator is never moved up to livestock.
- The relation itself may still be written across realms (SW:5158).
- The nudge's target list is `targets`, not the allowed pairs (see §10.A6).

### 3.7 Livestock as prey

| Switch | Default | Effect |
|---|---|---|
| `ecology.livestock` (Panel `livestock`, opt-in) | false | **every** armed predator, any realm, may be related to own-civ tame animals (the `dom[]` guard is skipped, SW:5094) |
| `v7.domestic` | false | own livestock is prey of AL, ML and cavern-layer predators only (SW:5011–5017) |

**`PANEL.fortOn` (`enable`) sets every Panel switch not in `V7.PARKED_SWITCHES`, opt-ins included (SW:16101–16102). So after `enable`, `ecology.livestock` is true.** See §10.A1.

---

## 4. Hunter mechanics

### 4.1 Skill profiles (`V7.H.profileOf`, SW:9668–9686; written by `V7.apply`, SW:13821–13897)

The scale is DF's 0–20 (15 Legendary). Only armed, non-civ, non-animal-person species get a profile.

| Profile | Who | SNEAK | Combat | Caste extras |
|---|---|---|---|---|
| species override | `hunters.skills.species[TOK]` | N | N | — |
| solitary apex | cohesion `solitary` (cluster max ≤ 1) and (AMBUSHPREDATOR, AL/AW, or ≥ 1,000,000 cm³); needs `v7.solo` | `solo_apex` 15 | 15 | AMBUSHPREDATOR + `stealth_slows = 0` on every gait |
| solitary | other solitary hunters (`v7.solo`) | `solo_meso` 12 | 12 | same |
| pack / group | non-solitary, `hunters.pack_on` | `pack_sneak` 5 | `pack` 10 | — |
| pack bonus (unit only) | pack share ≥ `v7.pack_sneak` 0.25 | `pack_bonus` 10 | — | — |

- Combat skills are MELEE_COMBAT, BITE, GRASP_STRIKE, WRESTLING, DODGING and SITUATIONAL_AWARENESS (`V7.SKILLS`, SW:13738).
- **Two halves.**
  - The caste `natural_skill_id/lvl/exp` vectors are raised, never lowered (`V7.naturalSkill`, SW:13757). Experience is DF's threshold total (`V7.H.ipFor`).
  - The unit's soul gets the same via `V7.unitSkills` (SW:13778–13816): rating = max(old, lvl), `rusty = 0`, and `natural_skill_lvl` (the rust floor) = lvl.
- Each unit/tag/level is written once per session. A unit with no soul is retried every pass (`V7.H.skillUnits`, SW:9698).
- Everything goes through `V7.rec` and is undone by `V7.restore`.
- Readback: `V7.H.readback` (`hunters readback`).

### 4.2 Packs and the ×3 / ×1.5 factors

- **Runtime pack size** (`V7.H.packSizes`, SW:9743–9789):
  - a tracked group with ≥ 2 live members gives that size;
  - otherwise armed same-race units within `pack_radius` (10) tiles and ±1 z, union-found, give the cluster size;
  - solitary species are never inferred into packs.
- It feeds only the pack floor and the SNEAK bonus in `ecoWrite`.
- **×3** is a *selection* weight: `roster.pack_bonus` in the builder (SW:7789, ~7831) and `cast.pack` in cast growth (SW:8474).
- **×1.5** is `PRED.k_large` in `eats()` (SW:2519).
- Neither factor touches the relation write.

### 4.3 Raptors and the stoop

- **Arming.** BENIGN is cleared on RP castes (SW:13837). `ecoArmed` arms RP (SW:4969).
- **Cap.** Prey must weigh ≤ `stoop.prey_ratio` (2) × the raptor's mass (`V7.H.raptorTooBig`, SW:9791). For a wild prey this uses the adult raw mass; for a non-wild one, the current size.
- **Stoop** (`V7.H.stoop`, SW:9821–9861; default enabled, **parked**). Each ecology pass, each RP predator not in `skip`, with `rng:random(100) < chance` (60):
  - cooldown 2,400 per raptor, at most 3 a pass;
  - target: the nearest *allowed* target that is ground-living, not swimming, within 40 tiles and ≤ 20 z;
  - action: the raptor is teleported to a dry tile 1–2 tiles from the prey at the prey's z (`V7.H.landNear`).
  - It runs only on the ecology cadence.

### 4.4 Bears fishing and polar bears (`V7.H.fish`, SW:9986–10048; `v7.fishers` default true, **parked**)

For each predator on `fisher_list` with an allowed aquatic target within `fish.range` (40) and ±6 z, rate-limited by `fish.cooldown` (1,200; halved in `fish.run` 'SuAu'):

1. Find a shore pair G/W near the bear, else near the fish (`V7.H.bankPair`, SW:~9905). This includes the ramp-bank case (`rampBank`).
2. Bear at G, or bear able to walk a straight line to it: up to `lure` (2; +1 in the run) fish are teleported into the water tiles beside G (`V7.H.lure`).
3. Otherwise the bear gets a straight walk, or DF's pathfinder (`setPathGoal` SeekStation). After `fish.wait` (600) it gets one hop.
4. **Polar bear** (`fish.polar`) with no shore pair near it: `goTo` with `water=true`, i.e. a path to the fish, then a hop into water beside it.

`V7.apply` also writes CAN_SWIM_INNATE and CAN_SWIM on listed fishers, and CAN_BREATHE_WATER only with `fish_breathe` (SW:13873–13881).

The relation that the fishing needs exists only through the fisher exception at SW:5182. That exception is gated by the same `v7.fishers` switch, and with casts on it is then cut by the cast-edge test (SW:5183; §10.A3).

### 4.5 Swimmer scavengers

`MODEL.swimScavenger` (SW:9644–9654): water habitat (aquatic or semiaquatic) and predator role, not vermin, civ or animal person. `swim_scav_list` overrides it. `SCAV.kind` makes such species `'swim'` scavengers (SW:14878–14888); see §5.1.

### 4.6 Cohesion, leaders, panic

- **Label.** `cohesionLabel` (SW:10442–10459) reads `MODEL.cohesionOf` (SW:9628: override → cluster-of-one solitary → school → flock → pack → herd). A raws-solitary species in a tracked group falls back to school/flock/pack/herd. Cetaceans are `pod`. Immobile species are never led.
- **Leader** (`V7.leaderOf`, SW:10486–10514, `v7.leader_male` on): the largest adult **male**; a water group needs a wet leader. No adult male means **no leader** (`grp.unled`). With `leader_male` off, the lowest id leads.
- **Cohere** (`V7.GRP.cohere`, SW:10520–10569, each groups pass of 300 ticks):
  - followers get `following = leader`, `owner_type = PACK_LEADER`, `follow_distance = follow_<label>`;
  - drawn/placed groups have their leave countdowns synced to the leader's once.
- **Leader lost** (`V7.GRP.leaderLost`, SW:12429–12447): the leader is missing from the live members (dead or inactive). Then:
  - cohesion is cleared and `grp.leader_lost` set, so the group stays unled (unless `reelect_after_panic`);
  - if `groups.panic` is on (default true, **parked**) and the label is herd/pack/school/pod (flock only with `panic_flocks`), a panic starts for `panic_days` (2).
- **Panic step** (`V7.GRP.panicStep`, SW:12493–12530): each pass, members **on the leader's z** within `panic_tiles` (12) of where it fell get a straight walk of ≤ 40 steps away from the spot (`scatter`), or toward the nearest edge (`edge`). Fliers are skipped (`walkToward`, SW:12469).

### 4.7 Curious beasts (R30 reform)

`CURIOUS.pass` (SW:13604–13660, every 50 ticks, `curious.reform` default on, **not parked**) watches wild units of thief species (CURIOUS_BEAST_EATER/_ITEM/_GUZZLER, not residents). When a unit's `leave_countdown == 0` (with `need_theft` off this is the only trigger), `CURIOUS.reform` (SW:13574–13601):

- drops hauled loot on the ground;
- clears the unit's `enemy.caste_flags` curious bits;
- sets the countdown to 20,000–30,000 and clears its path;
- makes its station a WildernessRoamer at its tile.

It repeats up to `max_rezero` (10) times if DF zeroes the countdown again. Residents (`curious.resident`) lose the caste flags species-wide (`CURIOUS.apply`). See §10.A5 for the conflict with season send-off.

---

## 5. Scavenging, vermin foraging, remains

### 5.1 Scavenging (`SCAV`, SW:14766–15452; `scavenge.enabled` default **false**, opt-in, but `enable` turns it on)

- **Scavengers** (`SCAV.kind`): BONECARN, CURIOUS_BEAST_EATER, `SCAV.TEXT`, or a swimmer scavenger. Never humanoid races. Wild and natural units only, ≤ 60 a pass, never the deep layer.
- **Remains** (`SCAV.edible`, SW:14906; `naturalRemains`): CORPSE or CORPSEPIECE items that are
  - loose, not forbidden, not in a job or building (so not on a stockpile);
  - not a historical figure's;
  - not a humanoid race;
  - not a citizen's, own-civ or tame unit's;
  - of a natural or unclassified race.
- **Natural cadence** (`SCAV.runNatural`, SW:15183, every `cadence` 200 ticks):
  - *Discovery delay.* Each remains gets a log-normal delay at first sight: medians small 18 h / medium 10 h / large 6 h, σ 0.6, clamped 2–96 h.
  - *Perception.* A scavenger notices it only after `delay + distance × scent_ticks` (10). Range is land 20, flier 40, swim 16 tiles; with `scav_mapwide` off it is capped at `radius` 20.
  - *Approach.* A straight walk on one level, re-issued every 400 ticks (`SCAV.walk`). Swimmers hop. Anyone that has not closed 2 tiles in `hop_wait` (600) hops `hop_tiles` (8), never from beyond `hop_max` (30), with `hops_day` 24 and `moves_day` 60 map-wide.
  - *Eating.* `eat_rate` (0.05 × own mass per hour), up to `gorge` (0.25 × own mass) a visit, then sated for 12 h. At most `feeders` (3) at once; a smaller species defers to a heavier one.
  - *Deletion.* The remains is deleted (`dfhack.items.remove`, SW:15086) only when its mass is gone. Mass is the race's **adult** size, or `piece_share` 0.15 of it for a piece.
- The legacy v7.0 sweep is kept behind `scavenge.natural = false` (`SCAV.runLegacy`).
- Discovery clocks live in `CACHE.scav7` (per session). Attribution stats persist in site data.

### 5.2 Vermin foraging (`VERMIN.FORAGE`, SW:15453–15855; `vermin_eat.forage` default true, **parked**)

- **Cadence.** A 100-tick step job plus a draw pass every `cadence` (1,200).
- **Index** (`VERMIN.index`, SW:15553–15609):
  - read the vermin objects (`world.event.vermin`) and bucket loose ones by 16×16 block;
  - colonies are weak attractors (`colony` 0.25);
  - `visible == false` objects are not targets;
  - the read stops at a 25 ms deadline (`idx.partial`).
- **Eligible eaters** (`VERMIN.forager`, SW:15661): wild, natural, on the map, not deep, not tame, idle, not a scavenger on a job, and whose caste carries any gobble class or creature.
- **Draw** (`VERMIN.forageOne`): up to `budget` (8) eaters a pass, each with `chance` 0.5, cooldown 3,600. Each picks a vermin within `radius` (20) that its live gobble classes match, weighted by nearness, amount and diversity. It gets a straight path (walk/swim/fly) to within REACH 2. **No teleport.**
- **Outcome** (`VERMIN.forageResolve`, SW:15740–15762), at each draw pass:
  - *eaten*: the target object id vanished and the forager had arrived;
  - *gone*: vanished, not arrived;
  - *missed*: arrived, still there at EXPIRE 1,500;
  - *expired*: never arrived.
- DF's own gobble does the eating; the tool only walks the eater.

### 5.3 Corpses

- Nothing in DF eats remains (header, SW:14769). Only SCAV deletes them.
- Kills made by related predators leave corpses that persist until a scavenger finishes them, or forever with scavenging off.

---

## 6. Layer-specific

### 6.1 Water

- **Realm.** Water-layer units are in the `land` realm (`ecoRealm`, SW:4946). Who reaches whom is REACH plus `sharesWater`.
- **Draw community weights** (`V7.WAT.mix`, SW:6394–6439), on top of the FREQUENCY base, for each candidate in a body:
  - *balance*: `((want+0.02)/(have+0.02))^balance`, clamped 1/4–4;
  - *feed*: prey with predators present, `1 + 0.5 × predator groups`, ≤ 4;
  - *pyramid*: `((target%+1)/(share%+1))^0.5`, clamped 0.25–4;
  - *apex limit*: weight 0 at `apex_max` (1) apex groups;
  - *pull*: below;
  - the product is clamped to `mix.cap` (**20**).
- **Pelagic pull** (`ENGINE.weight`, SW:6046–6059; mix pull term SW:6430–6434):
  - A predator with prey of it swimming in the body (`V7.WAT.ctxFor`, SW:6356–6372, using the mass rule `V7.WAT.eats` at SW:6362/6366) is weighted `1 + k × prey mass / own group mass`, between 1.5 and 4.
  - A pelagic predator (> `pelagic_ref` 1,000,000 cm³, ocean) with prey present loses the shallow-map floor (`lift_floor`). Without prey its weight is cut to `pelagic_floor` 0.1 on a shallow map.
- **Stranding guard: removed** in v7.1-place (`docs/v7.1/water.md:3–7`, SW:6156–6157).
  - Every swimmer enters by `V7.WAT.entry`: ocean/river edge columns, else the lake centroid.
  - The entry tile is the **lowest** free tile at 7/7 (`V7.WAT.colTile`, SW:7043–7055).
  - Air breathers are not told apart (§10.C1).
- **Curated aquatic apexes** (`aquatic_apex`, §2.7) set roster slots and pull level 'A'. They do **not** arm a BENIGN species: SPERM_WHALE and GIANT_SPERM_WHALE are curated 'pelagic' but stay unarmed.
- **Fishers.** §4.4.

### 6.2 Caverns

- **Realm.** `cavern:<depth>` (SW:4949), one realm per depth.
- **Arming and prey.** Cavern civ races are armed by guild (`civ_hunt`). They are prey of non-civ AL/AW only (`civ_prey`). Their slot reads ML/MW in the builder and casts.
- **Natives.** Adopted into tracked groups (`V7.GRP.adoptNatives`). Under casts, resting natives are dismissed (`castTurnover`).
- **Resting FREQUENCY.** Off-cast cavern species are held at `cast.cavern_rest_freq` (1; 0 for non-vermin as an experiment) (`CAVERN.restLevel`, SW:3683).
- **Animal-people cap** (`V7.GRP.apCap`, SW:12993–13031): every natural cavern-only person species (animal people and civ races) has its `cluster_number` capped at `groups.apcap` (5). The cap is lifted (original restored) while an irruption is active on a cavern it lives in. The originals are restored by `V7.GRP.restoreAll`.

### 6.3 Irruption v2 (`IRRUPT`, SW:10679–12313; `irruption.enabled` default false, opt-in, but `enable` turns it on)

- **Pressure** (`IRRUPT.pressurePass`, SW:11064), per cavern, every groups pass:
  - `p ← p(1−decay) + season_mult × fort × (0.02·citizens_in_band + 0.005·near + 0.01·dig_jobs) + breach 0.5 (once) + 0.003·scarcity + 0.004·U(0,1)`;
  - capped at `pmax × threshold` (4 × 1.0).
- **Phases** (`IRRUPT.step`, SW:11926): idle → warning (1–3 days; lapses below 0.6·threshold) → active → cooldown (30 days).
- **Event.** Up to 3 waves of one civ race chosen by stock (`IRRUPT.candidates`, SW:11125; admitted if `cfg.allow[key] ~= false`), or else cavern predators (`fallback`). Wave size is clamp(cluster max × 2, 4, 20), alive ≤ 60, spaced 1–3 days, entering at the cavern edge farthest from the fort's access.
- **Behaviour tokens** (`IRRUPT.TOKENS`, SW:10734–10746; `IRRUPT.applyUnit`, SW:11452): about 10% of a civ wave each, plus one champion carrying all.

  | Token | Write |
  |---|---|
  | CRAZED, MISCHIEVOUS, NOFEAR | curse masks via a wound or syndrome carrier |
  | rage | soldier_mood Enraged, PRONE_TO_RAGE at the unit's making |
  | thief | CURIOUS_BEAST(_ITEM) in the unit's caste cache, goal steal |
  | sneak | hidden_in_ambush + SNEAK 10 |
  | wander / meander | waypoint walks; meander also sets MEANDERER |
  | linger | 30-day countdown |
  | ambush | AMBUSHPREDATOR |
  | TRANCES | off by default |

- **Agitation** (`IRRUPT.agitate`, SW:11745): up to `agitate_cap` (30) non-civ natural cavern animals on that depth get `flags4.agitated_wilderness_creature`, re-written each pass.
- **End** (`IRRUPT.hold`, SW:11871): duration 10 days, repelled (≥ 50% of placed dead, min 2), none left, settled (3 days after the last wave), or pressure below calm 0.25 (no more waves).
- **Afterwards.** Everything is restored. Survivors get a 1–3 day leave (`end_mode leave`).
- **Food-web interaction.** Wave units are ordinary managed wild units, so the ecology pass relates them like any other. With casts on, only cast-edge pairs are written (§10.A4).

---

## 7. Season interaction

| Question | Answer from code |
|---|---|
| Does the relation web rebuild when the cast changes? | Yes, implicitly. `castEdgeSet` re-keys on `casts.built × 4 + season` (SW:8675), so the next pass writes only the new season's edges, and `V7.sweep` clears every managed wild pair not allowed this pass (SW:5280–5291). |
| With casts off? | No season structure in the relation rule at all: the same armed × target rule all year. Only which species are on the map changes, via allow/season stocks. |
| Sent-off species | `V7.GRP.castTurnover` (SW:12778–12801), once a season: tracked groups of species not wanted this season are dismissed (countdown 0, leader cleared). While they walk off: (a) their wild pairs are no longer cast edges, so the sweep clears them; (b) their non-wild pairs (livestock, caravans) are not cast-gated and stay; (c) after they leave, `ecoClearDeparted` NONEs their rows. Thief species are re-kept by CURIOUS reform (§10.A5). Irruption groups are exempt. |
| Resting species | `cfg.allow = false`, no season (`ROSTER.castYear`, SW:8613–8625); land stock held; cavern FREQUENCY at `cavern_rest_freq`. A resting unit on the map (leak, native, thief, walking off) is still armed if its raws say so. It gets no wild relations (no cast edges) but keeps livestock and caravan relations, and the sweep removes DF's wild ones. The web for a season with resting species is the cast's edge set, restricted to the armed members actually present, plus the non-wild targets. |
| Gobble wiring and the season | Gobble wiring and skill profiles go to every in-embark species regardless of cast (`VERMIN.gobbleApply`, SW:14678; `V7.apply`, SW:13829). HUNT flags follow `allow`. |

---

## 8. Every DF field the food web writes, and its undo

| What | Where written | Undone by | On disable / All off | On world unload |
|---|---|---|---|---|
| `enemy_status_cache.rel_map[*][*].ur = PREDATOR_OR_PREY` (both directions) | `ecoWrite` SW:5217 | **nothing** | **stays** | DF drops the cache at load |
| `rel_map` row/col → NONE | `ecoClearDeparted` SW:5048; `PLACE.enemySlot` SW:4876; `V7.sweep` SW:5286–5307 | n/a (clears) | — | — |
| `slot_used[i]`, `unit.enemy.enemy_status_slot`, `next_slot` | `PLACE.enemySlot` SW:4872–4878 | nothing | stays | reset by DF |
| caste BENIGN=false (RP species) | `V7.apply` SW:13838 via `V7.flag` | `V7.restore` | restored | restored (SW:17102) |
| caste BENIGN=false (MODEL.ROLE predators) | `CURIOUS.apply` SW:13466–13475 | `CURIOUS.restore` | restored | restored |
| caste AMBUSHPREDATOR, gait `stealth_slows=0`, `natural_skill_*` | `V7.apply` SW:13846–13867 | `V7.restore` | restored | restored |
| caste CAN_SWIM_INNATE, CAN_SWIM, CAN_BREATHE_WATER (fishers) | `V7.apply` SW:13876–13878 | `V7.restore` | restored | restored |
| caste NO_SPRING..WINTER cleared (`seasons_own`) | `V7.apply` SW:13834 | `V7.restore` | restored | restored |
| unit soul skills (rating, rusty, natural_skill_lvl) incl. pack SNEAK bonus | `V7.unitSkills` SW:13778 | `V7.restore` closures | restored (live units) | restored |
| caste `creature_class` += SWV_*; `gobble_vermin_class/creature/caste`; VERMIN_GOBBLER | `VERMIN.gobbleApply` SW:14671–14693 | `V7.restore` | restored | restored |
| caste DIVE_HUNTS_VERMIN / HUNTS_VERMIN | `HUNT.apply` SW:13412 | `HUNT.restore` | restored | restored |
| caste curious flags (residents) | `CURIOUS.apply` SW:13458 | `CURIOUS.restore` | restored | restored |
| `cluster_number` (apcap, coupling pack) | SW:13022; SW:4526 | `V7.GRP.restoreAll` / `endCoupling` | restored | restored (sizeRestore) |
| creature FREQUENCY (cavern rest, R61 floor, ladder) | CAVERN.apply / `ROSTER.freqFloorApply` | `CAVERN.restoreAll` | restored | restored |
| unit teleports: nudge, stoop, fishing lure/hop, SCAV hop, polar hop | SW:5415, 9809, 9970, 14974/14996 | irreversible | — | — |
| unit `path` / `dest` / `goal` (fish `goTo`/`walkLine`, panic `walkToward`, SCAV walk, forage walk, irruption walks) | SW:9917–9962, 12467–12490, 14945, 15634 | SCAV: `SCAV.release`; forage: `VERMIN.forageRelease`; **fish and panic: none** | partly | — |
| `following` / `owner_type=PACK_LEADER` / `follow_distance` | `V7.GRP.cohere` SW:10559 | `clearCohesion` only on dismiss, solitary, or leader loss | **stays** | saved with the units |
| `leave_countdown` (sync, hold, dismiss, curious stay, irruption linger) | SW:10567, 10588, 10596, 13570, 11480 | curious: `CURIOUS.unreform` (countdown → 0); irruption: `restoreUnit` | partly | — |
| `unit.enemy.caste_flags` curious bits (reform) | `CURIOUS.clearBits` SW:13547 | `CURIOUS.unreform` | restored | re-asserted next load from site data |
| `flags4.agitated_wilderness_creature`, curse masks, `uwss_add_caste_flag`, `hidden_in_ambush`, `soldier_mood`, SNEAK (irruption) | `IRRUPT.agitate` / `applyUnit` | `IRRUPT.restoreEvent` / `restoreUnit` via `IRRUPT.restoreAll` | restored | masks re-made on load |
| item deletion (remains) | `SCAV.finish` SW:15086 | irreversible | — | — |
| population `quantity` / extinct flag (stock, coupling window) | many | RESERVE / `endCoupling` | restored | — |

Disable path: `disableSched` (SW:15950–15983). All off: `PANEL.restoreAll` (SW:16042–16059). World unload: `dfhack.onStateChange` (SW:17098–17116).

---

## 9. Defaults, config keys and controls

### 9.1 Effective defaults

**Parked (v7.3).** `V7.parkNudges` (SW:1071–1081) runs at the end of every `loadConfigRaw` (SW:1057) unless `cfg.parked == false`. The default is `parked=true` (SW:736). It forces:

| Key | Default in `defaultConfig` | Effective while parked |
|---|---|---|
| `ecology.nudge` | false | false |
| `groups.coupling` | false | false |
| `vermin_eat.forage` | **true** | false (SW:1076) |
| `hunters.stoop.enabled` | **true** | false (SW:1077) |
| `v7.fishers` | **true** | false (SW:1078; also removes the fisher relation exception and the bears' water-roster move, `ROSTER.inPart` SW:7734) |
| `groups.panic` | **true** | false (SW:1079) |

No verb, Panel switch or control sets `parked`: grep finds only SW:736, 1056, 1072–1073.

### 9.2 Keys

| Key | Default | Line | Panel / control / verb |
|---|---|---|---|
| `ecology.enabled` | true | SW:806 | Panel `ecology`; `groups ecology on|off` |
| `ecology.cadence` | 3000 | SW:806 | control `ecology.cadence` 500–12000; `groups ecology cadence N` |
| `ecology.livestock` | false | SW:806 | Panel `livestock` (opt-in); `groups livestock` |
| `ecology.nudge`, `radius` 6, `far_tiles` 40, `far_ticks` 3000 | false | SW:806 | Panel `nudge`; radius/far_* only in the GUI Nudge prompt (`gui/seasonal-wildlife.lua:1530`) |
| `v7.pack_floor` / `pack_sneak` | 0.05 / 0.25 | SW:841 | controls; `v7 pack_floor X` |
| `v7.solo`, `civ_hunt`, `civ_prey`, `fb_safe`, `sweep`, `domestic`, `gobble`, `fishers`, `fish_breathe` | on, on, on, on, on, off, on, on, off | SW:840–843 | controls; `v7 KEY on|off` |
| `v7.gobble_creature_fallback` | 3 | SW:843 | control; `v7 …` |
| `v7.outgun` / `outgun_cap` | 2.0 / false | SW:843 | controls |
| `v7.fisher_list` | 9 bears | SW:845 | `v7 fisher TOK`, `hunters fish TOK` |
| `hunters.pack_on`, `pack_radius`, `raptors`, `swim_scav` | true, 10, true, true | SW:810 | controls, `hunters …` |
| `hunters.skills.*` | 15 / 12 / 10 / 5 / 10 | SW:811 | controls, `hunters skills` |
| `hunters.stoop.*` | enabled, cd 2400, range 40, max 3, chance 60, ratio 2, skip vulture | SW:812 | controls, `hunters stoop` |
| `hunters.fish.*` | run SuAu, cd 1200, range 40, spot 8, lure 2, wait 600, polar | SW:813 | controls, `hunters fish` |
| `hunters.cohesion` | {} | SW:816 | `hunters cohesion` |
| `groups.cohesion`, `follow_*` (herd 8, pack 4, flock 12, school 5, pod 5) | on | SW:796, 804 | Panel `cohesion` |
| `groups.panic*` | panic on, 2 d, 12 tiles, scatter, flocks off, reelect off | SW:803 | controls (`leaders` section) |
| `groups.apcap` | 5 | SW:804 | control, `groups apcap` |
| `scavenge.*` | enabled **false**, natural, swimmers, defer, cadence 200, … | SW:781–790 | Panel `scavenge` (opt-in); controls |
| `vermin_eat.*` | forage, source both, cadence 1200, radius 20, budget 8, chance 0.5, cd 3600, colony 0.25, diversity 0.5, all classes on | SW:856–860 | Panel `forage`; controls |
| `hunting.enabled` | false | SW:775 | Panel `hunting` (opt-in) |
| `curious.reform` etc. | on, cadence 50, stay 20k–30k, loot drop, max_rezero 10 | SW:777–783 | Panel `curiousreform` |
| `irruption.*` | `IRRUPT.defaults` SW:10751–10774 (enabled false) | | Panel `irruption` (opt-in); `irruption set` |
| `water.mix.*`, `water.pull.*` | mix on, balance 1, cap 4, feed 0.5, pyramid 0.5, apex_max 1, cap 20; pull on, k 1, min 1.5, cap 4, lift_floor | SW:748, 751 | controls |
| `roster.pack_bonus`, `pred.*`, `aquatic_apex`, `gobble_max` | 3, PRED, list, 3 | SW:7558–7600 | `roster set` |
| `cast.*` | enabled, carry 0.25, giant 0.2, pack 3, cavern_rest_freq 1 | SW:8298 | `cast …` verbs (SW:18340–18375); **not** in the controls registry |

The controls registry (`scripts/seasonal-wildlife-controls.lua:198–241, 336–414, 440–447`) exposes most hunter, scavenge, vermin, v7 and water keys. It does not expose the cast settings, `ecology.radius`/`far_*` or `parked`.

---

## 10. Gaps, dead code, contradictions, suspicious logic

### A. Behaviour-level problems (highest impact first)

**A1. `enable` turns livestock-as-prey on for every armed predator in every realm.**
- `PANEL.fortOn` (SW:16101–16102) sets every Panel switch not in `V7.PARKED_SWITCHES = {nudge, coupling, forage}` (SW:1070). `livestock` is not in that set (opt-in only matters for "all on").
- With `ecology.livestock` true, `dom[]` stays empty (SW:5094), so the `v7.domestic` guild restriction is bypassed. Every armed predator, cavern depth 1–3 included, is related to the fort's tame animals across realms (SW:5158).
- The user's startup runs `enable` on map load (memory: user-df-startup-config), so this is the live configuration.
- The nudge fix stops the teleport. Nothing stops the cross-realm relation. Whether DF's AI paths a related cavern predator up to its target is **unmeasured**; it would reproduce the test-item-1 outcome without any teleport.
- Caravan pack animals and visitor mounts are targets of every armed predator in every realm **regardless of any switch** (SW:5004).

**A2. With casts on, cross-layer predation is never written.**
- `ROSTER.castGrow` builds edges inside one layer's partitions only (`ROSTER.castPool` SW:8391; edges SW:8562–8564). Land = land + flying; water = water; cavern = cavern.
- `ecoWrite` then drops every wild pair not in the edge set (SW:5183).
- Blocked: alligator/crocodile (water roster) × deer (land); land carnivores × water-layer shore animals; waterbirds and ospreys × fish; otters × land prey. The code comment at SW:4945 cites ECO W1L: alligators killed 5 of 8 deer from the water.

**A3. With casts on, bears never fish.**
- The fisher exception (SW:5182) sets `sp = true` for land × aquatic, but the very next line requires a cast edge (SW:5183).
- Cast edges come from `castEats` → `MODEL.reaches`, which forbids land → aquatic (REACH).
- So the bear × fish pair is never allowed, `V7.H.fish` finds no `allow` (SW:10010), and the fishing lever is inert even if un-parked. Polar bears in water are inert the same way.

**A4. Cast edges include dead edges and omit live ones.**
- *Dead edges.* `castEats` and `linkable` never check BENIGN. A cast can seat BADGER, FOX, STOAT, MONGOOSE, WOLVERINE or CAT in the meso slot, or SPERM_WHALE in the pelagic apex slot (all BENIGN in all castes in vanilla 53.16, raw read). Each such member's prey edges are never written (`ecoArmed`, SW:4970). The desk's "every cast one connected web" is a tier graph, not the realised hunting graph.
- *Omitted edges.* Tier-down edges APX → ML/MW/RP exist in the cast, but `ecoIsTarget` excludes every armed species from the targets (SW:5000). So apex × mesopredator is never written, and intra-guild predation is impossible except for civ races under `civ_prey`.
- Irruption civ waves of a non-cast race get no wild-wild relations with cavern fauna. Their effect is only through the tokens and agitation.

**A5. CURIOUS reform re-keeps every thief that is sent off.**
- `castTurnover` → `dismissGroup` zeroes `leave_countdown` (SW:10596). So do `sendoff`, `call` and cavern trim.
- `CURIOUS.pass` (every 50 ticks, reform on, not parked) treats a thief-species unit with countdown 0 as a fresh thief. It sets a new 20k–30k countdown and repeats up to 10 times (SW:13653, 13622–13636).
- With `need_theft` off (default) no theft sign is needed (SW:13583).
- Result: bears and raccoons sent off at a season turnover stay for up to ~11 × 25,000 ticks, as resting species on the map. A natural end of stay is caught the same way.

**A6. The nudge ignores the allowed pairs.**
- `ecoNudge` picks the nearest same-realm target from the full `targets` list (SW:5441–5452), not `CACHE.ecoAllow`.
- A wolf can be teleported beside a fish, a shark, an off-cast species or a too-big prey, at the target's z. Only the tile type (ground or water by the mover) is checked.
- It also ignores the civ-prey extra targets. It is parked, but it is exposed as a Panel switch.

**A7. Parking makes the stoop, fishing, forage, nudge and panic switches unreliable.**
- `V7.parkNudges` runs on every config load (SW:1057), and there is no verb for `parked`.
- `hunters stoop on` saves and then reloads the config at once (`reapply`: `CACHE.cfg = nil; loadConfig()`, SW:10093–10094), so it is parked again before any pass runs. The same holds for `v7 fishers on` (SW:18683).
- `vermin forage on` and `groups panic on` survive until the next reload: any of the 9 `CACHE.cfg = nil` sites, a map load, or even `vermin forage now` (SW:18219–18222).
- The Panel/controls show these as normal switches.

**A8. The memo and the sweep can disagree, leaving a pair unwritten for up to 8 passes.**
- When a pair is written, `CACHE.ecoDone[slots] = ids`.
- If on a later pass the pair is not allowed, the sweep clears the cell (SW:5285–5288) but does **not** clear the memo. The pair can lose its allowance because the inferred pack shrank under `pack_floor`, a packmate stepped out of `pack_radius`, or the cast changed.
- When it is allowed again, `done[k] == pid` counts it as written (SW:5212) and it stays empty until the 8th-pass refresh (≈ 24,000 ticks).
- The pack-floor check is per pass and per pair (SW:5187–5189), so pairs near the floor can flicker.

**A9. The realm test inside `MODEL.reaches` uses the entry's layer, not the unit's.**
- `byTok[token]` is the first pool entry of a species (SW:4979). The memo test `MODEL.reaches(ea, eb)` compares `(e.layer=='cavern') ~= (p.layer=='cavern')` (SW:2569).
- A species with both surface and cavern entries (`V7.GRP.species` marks these `shared`) can therefore be refused against same-cavern prey when its first entry is the land one, or the reverse.
- The unit-level realm test already ran (SW:5158). Needs a rig check on a shared species.

**A10. Wild units with no pool entry bypass every test.**
- A wild unit whose species has no entry (`T.eb[i] == false`) gets `ok = true` with no reach, cast, raptor or floor test (SW:5195).
- Examples: placed from another region, an invasive, some apex-scheduler placements.
- Such units are also outside the sweep's managed set, and are recorded as `…|DOMESTIC` (SW:5219).

**A11. The skill profile can be promoted by the tool's own write.**
- `V7.apply` writes AMBUSHPREDATOR on solitary castes (SW:13846).
- `roster set ap_vermin_mass` resets `CACHE.class` while those writes are live and does not re-run `V7.apply` (SW:9267). Classification then reads `ambush=true` for solitary mesopredators.
- At the next `V7.apply`, the restore runs but the class cache is stale. `profileOf` promotes them to "solitary apex" (15 instead of 12) and `takeOf` gains ×1.5. This lasts until world unload.

**A12. Undo gaps.**
- Relation cells are not undone on disable or All off (§8).
- Cohesion follow links (PACK_LEADER) are not cleared on disable or All off: there is no `clearCohesion` in `disableSched` or `PANEL.restoreAll`.
- Fishing `goTo` paths and panic `walkToward` paths have no release.
- The sponge sweep clears any non-BENIGN unit's cell onto a sponge, citizens and forgotten beasts included (SW:5300–5308). This is a small exception to the fb_safe promise at SW:2236.

### B. Dead or ineffective code

- **B1. `eats()`, `takeOf`/`needOf`, `k_large` (×1.5) and `preference`** never reach the relation write. They drive only the matrix roster, co-align, coupling, the water pull/feed, the species page and the web graph. `PRED` comment (SW:2496–2515) describes a "can hunt" rule that the animals do not follow.
- **B2. The aquatic apex list does not arm.** SPERM_WHALE and GIANT_SPERM_WHALE are curated pelagic apexes (SW:7576–7577) and are pulled in by prey (`V7.WAT.eats` → `eats`, SW:6263). They are BENIGN, not in `MODEL.ROLE`, and so never hunt (SW:4970).
- **B3. Builder edges and the GOBBLE edge table are selection or data only**, except `VERMIN.rosterRows`. That turns builder 'write' edges into gobble class writes, using a *random* vermin draw per build (SW:8019–8024).
- **B4. The 'snake' gobble rule never fires.** `VERMIN.legless` (SW:14531–14543) reads `gi[i].name` where `gait_info[i]` is a vector of gaits; the struct has no `name` either. The pcall therefore fails and returns false. `docs/v7.1/vermin.md:163–164` still lists snakes as SWV_SMALL_MAMMAL and SWV_HERP eaters.
- **B5. The pull and feed use `V7.WAT.eats`**, the mass rule (SW:6362, 6366). A predator can be pulled into a body for prey that `ecoWrite` will not relate it to (cast edge, shared water, BENIGN).

### C. Field reports checked against the code

**C1. Minks drowning loop.**
- *Classification.* Vanilla MINK is BENIGN, has no diet token, and has only ANY_TEMPERATE_LAKE/RIVER biomes, with no AMPHIBIOUS or CAN_BREATHE_WATER (raw read). `MODEL.habitat` makes it `semiaquatic` (water-only biomes, SW:1902), guild SH, role prey, and a water-layer entry.
- *Draw.* `ENGINE.candidates` takes any water-layer entry regardless of habitat (SW:5978).
- *Placement.* `V7.WAT.colTile` puts every water entrant on the **lowest** free 7/7 tile of a column (SW:7043–7055). An air-breather starts submerged. The stranding guard that regrounded drowning air-breathers was removed in v7.1-place (`docs/v7.1/water.md:3–7, 34`).
- *Loop.* The minks die, so `have = 0`. `V7.WAT.mix` then rewards the absent species: balance up to ×4, pyramid H up to ×4, feed up to ×4, product clamped at `mix.cap` 20 (SW:6411–6438). The next draw picks minks again.
- *Fix shape.* Separate air-breathing semiaquatic entrants (surface tile or shore), or exclude them from Driver B.
- Related: `stuckSweep` (SW:10658–10677) regrounds any tracked **non-flier** unit, fish included, that has not moved for 5,000 ticks.

**C2. Stoop adds nothing over the ecology write.** Reasons in the code:
1. At HEAD the stoop is parked off and cannot be turned on persistently (A7). If the report predates 7 Oct the next points apply.
2. It only acts on pairs the write already allowed (SW:9838), so it adds proximity, never a relation.
3. The dose is small. It rides the 3,000-tick ecology pass, at a 60% chance, with a 2,400 cooldown (shorter than the cadence), so at most one stoop per raptor per pass and three map-wide.
4. It places a flier on the ground 1–2 tiles off. Nothing holds it there, and DF's flier AI takes off again; whether a landed raptor's next tick is an attack is unmeasured.
5. Raptors are capped to prey ≤ 2× their mass. Their prey is the same set the write relates, so with the relation present any meeting would happen without the stoop anyway if DF's AI closes the distance.

**C3. Lost-leader panic shows no detectable scatter.** Reasons in the code:
1. `groups.panic` is parked (SW:1079). With panic off, `leaderLost` only logs and leaves the group unled (SW:12436–12446).
2. Panic needs a leader to have existed. Leaders are adult males only (SW:10486–10514); groups without one are unled from the start, so there is nothing to lose.
3. Only members on the leader's z and within 12 tiles move (SW:12505). The move is one straight walk of ≤ 40 steps per 300-tick pass, toward a target ~12–17 tiles away. Fliers are skipped, and DF re-plans a wild roamer quickly.
4. After the panic the group stays unled (no reelect), so a control arm with an unled group spreads the same way. The measurable difference is only the ≤ 2-day flight.

**C4. Vermin forage (VF1) never recorded a meal.** Reasons in the code:
1. At HEAD forage is parked. `vermin forage on` holds only until a reload (A7), and `vermin forage now` itself triggers one.
2. An "eaten" result needs the target vermin **object** to vanish completely (`not idx.alive[p.vid]`, SW:15743–15751). A swarm whose amount is decremented by a gobble stays alive and is scored `missed`.
3. "Arrived" is measured against the vermin's position **at the draw** (`tx,ty`, SW:15705, 15729–15731). Loose vermin move, so an eater can reach the old spot while the vermin is elsewhere.
4. Resolution happens only at draw passes (1,200 ticks). It is skipped entirely when the index hit its 25 ms deadline (`idx.partial`, SW:15749). On a map with many vermin objects that can be every pass, and then only `missed`/`expired` are possible.
5. `visible == false` vermin are never targets (SW:15592).
6. The walk sets goal SeekStation (SW:15639). If DF's gobble runs only from idle wandering, the forced path may delay it. Unmeasured.

### D. Docs vs code disagreements

| Doc | Says | Code |
|---|---|---|
| `docs/v7.1/ecology.md:22–23, 50, 304–307` | stoop on by default; fishers on by default (bears fish) | both parked off at every load (SW:1077–1078) |
| `docs/v7.1/vermin.md:175` | foraging "on", not opt-in | parked off (SW:1076) |
| `docs/v7.1/vermin.md:163–164` | snakes (ML legless) eat small mammals and herps | `VERMIN.legless` always false (B4) |
| `docs/v7.1/ecology.md` "Profiles" | pack baseline for every pack member | true, but only for *armed* species (SW:9669); the doc omits that BENIGN pack hunters get nothing |
| SW:4563–4571 header | "write every ecology.cadence ticks (1,500)", "zero a departed unit's row" | cadence 3,000; cleared to NONE (-1), not zero/STRANGER |
| SW:4952–4957 comment | "Predators are the food web's land predators that carry LARGE_PREDATOR" | the rule is "not wholly BENIGN" since v6.9 (SW:4960–4970) |
| SW:2496–2515 PRED header | mass rule as "can these predators take that prey" | not used by the relation write (B1) |
| SW:8278–8280 cast header | "every cast one connected web" | connected in the tier graph; the realised web drops BENIGN members and apex × meso (A4) |
| PANEL comment SW:15995–15998 | `optin` switches are ones "all on leaves as they were" | true for All on; `enable` (fortOn) sets them all, livestock included (A1) |
| `docs/v7.1/water.md:33` | seed by prey, `water.pull.seek` | removed in v7.1-place (the doc's own banner says so) |

---

## 11. Function index (quick map)

| Topic | Functions |
|---|---|
| Classification | `classify` ~SW:1790, `MODEL.habitat` 1893, `MODEL.role` 1905, `MODEL.guild` 1938, `adultSize` 1454 |
| Rules | `eats` 2547, `MODEL.reaches` 2565, `preference` 2576, `ROSTER.linkable` 7794, `ROSTER.castEats` 8416 |
| Casts | `ROSTER.castGrow` 8451, `castYear` 8589, `castEdgeSet` 8673, `V7.GRP.castTurnover` 12778 |
| Ecology pass | `ecologyJob` 9570, `ecologyRun` 5468, `ecoArmed` 4958, `ecoIsTarget` 4994, `ecoWrite` 5077, `V7.sweep` 5252, `ecoClearDeparted` 5024, `PLACE.enemySlot` 4866, `ecoNudge` 5436 |
| Hunters | `V7.H.profileOf` 9668, `packSizes` 9743, `stoop` 9821, `fish` 9986, `V7.apply` 13821, `V7.unitSkills` 13778 |
| Groups | `V7.leaderOf` 10486, `V7.GRP.cohere` 10520, `leaderLost` 12429, `panicStep` 12493 |
| Vermin | `VERMIN.swvClass` 3361, `gobbleApply` 14663, `forageRun` 15765 |
| Scavenging | `SCAV.runNatural` 15183, `SCAV.turn` 15107 |
| Water | `V7.WAT.mix` 6394, `ENGINE.weight` 6046, `V7.WAT.colTile` 7043 |
| Irruption | `IRRUPT.pressurePass` 11064, `step` 11926, `applyUnit` 11452, `agitate` 11745 |
| Curious | `CURIOUS.pass` 13604 |
| Lifecycle | `PANEL.fortOn` 16086, `disableSched` 15950, `V7.parkNudges` 1071 |
