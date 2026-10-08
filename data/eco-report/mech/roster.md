# Roster building: how seasonal-wildlife decides who lives on a fort

**Source.** Read from the code only, on branch `v7.2-plugin` at HEAD `8185d85` in `sw-wt/plugin`. Nothing was run against
the game. Line numbers refer to `scripts/seasonal-wildlife.lua` (18,778 lines) unless another file is named. Other files
used: `scripts/seasonal-wildlife-controls.lua` (the control registry), `scripts/gui/seasonal-wildlife.lua` (the window) and
`plugin/lua/seasonal-wildlife.lua` (the plugin's Lua half), plus the docs `docs/v7.1/roster.md`, `docs/v7.1/extinct.md`,
`HANDOFF.md`, `PLAN.md` and `STATE.md`. Where a doc and the code disagree, the code is taken as true and the disagreement is
listed in section 7.

**Words.**
- **Pool**: every species the embark could hold.
- **Roster**: the species the tool lets on the map, each with its seasons.
- **Active / inactive**: `cfg.allow[key]` is true or false.
- **Key**: `TOKEN` on land, `water:TOKEN`, `cavern:TOKEN` or `deep:TOKEN` (`keyFor`, :1411).
- **Layer**: the population entry's layer: land, water, cavern or deep (`layerOf`, :1403).
- **Roster part**: the builder's own split of the pool: land, flying, water and cavern (`ROSTER.inPart`, :7720).

---

## 0. The three ways a roster is made

The code holds three roster builders. Only one of them runs by default on a new fort.

| Path | Code | When it runs | What it writes |
|---|---|---|---|
| **Preset / climate matrix** (v6.3+) | `applyPreset` :3883, `assignFromMatrix` :2733, `ROSTER.deal` :2665, `ROSTER.pairGuarantee` :2754, `ROSTER.normalize` :2699 | `preset` verb (:18273); the window's first run and its "Re-apply preset" button (gui :387-397, :1544); `PANEL.fortOn` on a new fort **only when casts are off** (:16093-16097) | Every in-embark natural species is active with **one** season, dealt by climate rank within its group (realm, habitat, role); a pair guarantee then adds seasons where needed |
| **Guild builder** `ROSTER.build` (v7.0, reworked in v7.1) | :8064-8256 | **Only** on the `roster build [layer]` verb (:18422) or the web "Build the roster" action (controls :188). It never runs on its own | Activates the chosen species and deactivates the rest of that part's slotted species; writes the FREQUENCY ladder into `cfg.odds`; writes `cfg.roster.apex_keys` for the apex scheduler |
| **Season casts** (v7.3, 7-8 Oct) | `ROSTER.CAST` :8282 to `ROSTER.castEdgeSet` :8673 | On `enable` on a **new** fort, with `cast.enabled` on by default (:16093, :16105); again at every new year (`V7.ST.turn` :4098); and on `cast rebuild` (:18359) | Per layer and per season, a cast. Cast species are active with exactly the seasons they are cast in. Every other species the cast layers manage **rests** (inactive, no season) |

So on a fort first enabled with v7.3, **the season casts are the roster.** The builder's FREQUENCY ladder and its apex keys
exist only if someone runs `roster build` by hand (see problem P1).

---

## 1. The pool: which species an embark can hold

### 1.1 The region tiles: `getEmbarkRegions` (:1311-1391)

The function returns `regionSet` (`"rx:ry"` → biome id) and `biomeSet` (biome id → true). It is cached per site and map
size in `CACHE.region`. It collects:

1. **The site record's tiles.** The site's global bounds divided by 16, from `df.world_site.find(site_id)` (:1316-1325).
2. **Every block's region tiles, all nine neighbours.** For each map block, all nine `region_offset[0..8]` values, giving
   `region_pos + (off % 3 - 1, off // 3 - 1)` (:1335-1343). The note at :1329-1334 records why all nine: X1 found cavies
   drawn from a neighbour tile that a one-offset read had missed.
3. **For cave entries only, a wider set.** The full 3×3 neighbourhood of every site tile (`CACHE.caveNum`, :1355-1366;
   from Alpha Four 3.8, where trolls and devourers came from 168:173 and 170:173). Surface entries keep the block set.

`regionSet` is also kept in numeric form (`CACHE.regionNum`, :1348-1350), so the membership test per entry does not
allocate.

### 1.2 Population entries and layers

- **`managedPop(pop, regionSet, layers)` (:1428-1438)** decides which regional entries the tool manages. An entry is
  managed when all four hold:
  - its type is Animal, Vermin, VerminInnumerable or ColonyInsect (`POP_TYPES`, :1424);
  - its region tile is in the set: the cave set for `cave_id >= 0`, the block set otherwise;
  - `quantity_max < INNUMERABLE` (10,000,001, :526): uncountable clouds are never touched;
  - its layer is in the asked-for layer set.
- **`layerOf(pop)` (:1403-1409):**
  - `cave_id ~= -1` → `cavern` if the cave's `layer_depth <= 2`, else `deep` (the magma sea and the underworld);
  - `feature_idx ~= -1` → `water`;
  - otherwise `land`.

  Ocean life and many river fish carry no feature index. The pool therefore files them under their **land** key; v7.3's
  turnover had to learn this (`8817eb4`, :12788-12791).
- **`CACHE.managedPops()` (:2959-2973)** indexes every managed entry of every layer once per map, as
  `{i, race, key, layer}`. It is rebuilt when `populations.all` grows (Add invasive). Every season pass walks this index.

### 1.3 `buildPool(cfg)` (:2327-2410)

The function returns `pool` (sorted by token), `biomeSet` and `regionSet`. Each entry `e` is made once per key by `ensure`
(:2332-2370), and there are two ways in:

| Flag | Set by | Meaning |
|---|---|---|
| `e.inEmbark = true` | the loop over managed entries of the **enabled** layers (:2375-2400) | DF stocked this species on this embark. `e.quantity` = the largest entry quantity; cavern entries record `e.depths[layer_depth]` (:2392-2394) |
| `e.eligible = true` | every raw (not `DOES_NOT_EXIST`, not `EQUIPMENT_WAGON`) whose BIOME flags meet `biomeSet` (`creatureEligible` :2298, loop :2401-2408) | it could live here; this is what Add invasive offers. These entries are made with the **land** key (`ensure(idx, craw)`, layer defaults to `'land'`) |

Every roster builder reads only `inEmbark` entries. `eligible` feeds only the Add-invasive view and `fillCategory`
(:2896).

An entry carries these fields:
- the climate lean (`climateRange` :2307; lean = (hot − cold) / total);
- habitat and role, with the player's overrides on top (:2349-2350);
- `viewLayer`;
- everything `classify` returns (§1.4);
- `eco` and `locked` (§1.5).

### 1.4 What `classify(craw)` reads (:1795-1880)

`classify` is memoized per world in `CACHE.class`.

| Field | Rule (line) |
|---|---|
| `gameVermin` | any of the creature flags VERMIN_GROUNDER, VERMIN_ROTTER, VERMIN_SOIL, VERMIN_FISH, VERMIN_EATER, SMALL_RACE (:1801-1802) |
| `habitat` | `MODEL.habitat` (:1893). IMMOBILE_LAND or CANNOT_BREATHE_AIR → aquatic. FLIER → waterbird (it has a water biome) or flier. CAN_BREATHE_WATER → semiaquatic. Water biomes only → semiaquatic. Otherwise land. `aquatic = habitat is aquatic or semiaquatic` |
| `role` | `MODEL.role` (:1905): the curated `MODEL.ROLE` table first (ORCA and GIANT_ORCA predators, GIANT_CUTTLEFISH predator, SHARK_WHALE prey; :1714-1719). Otherwise predator if any caste has CARNIVORE, BONECARN, LARGE_PREDATOR or AMBUSHPREDATOR; else prey |
| `mass`, `size` | adult body volume in cm³ (`adultSize` :1454, = caste `body_size` last value × 10). Bands: small < 150,000; medium < 1,000,000; large from there (`MODEL.band` :1721) |
| `cmin`, `cmax`, `group` | the raw `cluster_number`, in order (:1840-1841); `group` = floor of the midpoint, at least 1 (:1813-1814) |
| `giant` | the raw file applies `APPLY_CREATURE_VARIATION:GIANT`, or the token starts `GIANT_` (:1842) |
| `sentient` | CAN_SPEAK or CAN_LEARN (:1843) |
| `good`, `monster`, `savage`, `evil` | raw flags (:1816, :1844) |
| `depthLo`, `depthHi` | `underground_layer_min/max`, read under pcall (:1845-1846) |
| `fireOnly` | every BIOME the raw names is SUBTERRANEAN_LAVA (:1847-1852) |
| `gobble`, `cclass` | DF's own GOBBLE_VERMIN_CLASS list; for vermin, their creature classes (:1853-1864) |
| `root`, `ap`, `apVermin` | an animal person (`MODEL.rootOf` :1757, which reads COPY_TAGS_FROM and ANIMAL_PERSON from the raw files once per world). It takes the root's role, habitat, water, flier and diet flags, but keeps its own mass: if the compiled mass equals the root's, it becomes (root + 70,000) / 2 (:1865-1878). A person whose root is vermin becomes a small predator (`apVermin`), with mass optionally `roster.ap_vermin_mass` |
| `guild` | `MODEL.guild` (:1938-1966), tested in this order: V vermin; apVermin → RP, MW or ML; AW (LARGE_PREDATOR, not a flier, aquatic or amphibious); RP (a flier with a predator diet or LP); AL (LP); ML or MW (diet; MW when aquatic); GZ (GRAZER); WB or LB (fliers, by water biome); aquatic → PE (ocean, ≥ 1,000,000 cm³) or FC, else FF; SH (amphibious, or water biomes only); PL otherwise |
| extinct corrections | `V7.EXTINCT.model` (:14103) overrides LP, CARNIVORE, AMBUSH, BENIGN, habitat, guild, GRAZER (PL → GZ) and cluster for the 83 table rows when `extinct.fix` is on, **whether or not the raws are written** |
| `civ` | `V7.isCivRaw` (:2258): speaks or learns, not GOOD or EVIL, not an animal person of a non-vermin root, and has a SUBTERRANEAN biome |

### 1.5 Ecology class and locking

- `V7.ecologyClassRaw` (:1588-1615) sorts each raw into one class, testing in this order:
  - **generated** (GENERATED);
  - **mega** (MEGABEAST, SEMIMEGABEAST, TITAN);
  - **night** (the NIGHT_CREATURE_* flags);
  - **unliving** (NOT_LIVING, or NO_EAT + NO_DRINK without GRAZER or CARNIVORE);
  - **mythic** (FANCIFUL, GOOD, EVIL);
  - **unclassified** (no body size, or no BIOME);
  - **natural** (everything else).
- `ecoOf` (:1678-1688): a player override can only bring a creature in as `natural`. A `mythic` creature becomes natural
  through `V7.alignedNatural` (:1657) in three cases:
  - FANCIFUL alone, when v7 `fanciful` is on;
  - a cave-only GOOD or EVIL species, when `cave_aligned` is on;
  - surface GOOD or EVIL wildlife on a region of its own alignment, when `aligned` is on. `V7.alignment` (:1620) reads
    each region tile's evilness: < 33 is good, ≥ 66 is evil; the world_region's own flags count too.
- `e.locked = cfg.classes[eco] ~= true` (:2360). The defaults (:818) manage only `natural`.
  - A locked species is never allowed (`isAllowed` :2417).
  - `V7.sanitizeLocked` (:1742) drops a saved allow or assign for one at load.
- `defaultAllow(e)` = in the embark, not HAS_ANY_MEGABEAST or night, and not locked (:2416).

### 1.6 Savagery

- **Per species:** `e.savage` is the raw SAVAGE flag (:1816). No roster builder filters on it. A SAVAGE species is in the
  pool whenever DF stocked it.
- **Per map:** `ROSTER.savage(cfg)` (:7642-7665) reads each region tile's `savagery`. The map counts as savage if any tile
  is at or above `roster.apex.savage_cut` (default 66). It sets:
  - the builder's land APX slot maximum to 2 (:7770);
  - the apex scheduler's cap: `cap_savage` instead of `cap_calm` (:8905).
- **SAVAGE on a calm map (R36):** `addNewSpecies` (:4008) calls `ROSTER.invasiveAdded` (:8929). For a SAVAGE raw on a calm
  map, it places one group at once from the new entries' stock (`ROSTER.placeGroup`) and lists the species in
  `roster.invasive`. `ROSTER.placeTick` (:8915-8923) then keeps placing it toward `apex.invasive_presence` (25%).

### 1.7 Animal people and giants

They are pool members like any other. The rosters weigh them down:

| | At pick time | Once seated (FREQUENCY) |
|---|---|---|
| Builder (`ROSTER.pickWeight` :7829) | AP that is not civ ×`ap_pick` 0.1; else giant ×`giant_pick` 0.2 | `ROSTER.ladder` :7906: AP ×`ap_freq` 0.25, giant ×`giant_freq` 0.5, inside the trophic level |
| Casts (`castGrow` weight :8472) | AP that is not civ ×`roster.ap_pick` 0.1; giant ×`cast.giant` 0.2 (a separate knob) | the casts write no FREQUENCY |

- `ROSTER.boosted` (:7672): with `giant_boost` on, a predator-guild GIANT_* is an apex (APX) whatever its mass.
- `ROSTER.freqFloorApply` (:8952): an in-embark animal person whose raw FREQUENCY is 0 is written `ap_freq_floor` (1), so
  DF can draw it at all. This runs from `V7.apply` on every enable.

### 1.8 Extinct creatures

The pool adds no extinct species of its own. The 200 extinct creatures are in the pool only where worldgen gave them
regional populations (comment :13900-13906).

`V7.EXTINCT` (:13939-14069) is an **83-row** correction table, checked in this pass with Python:
- 21 FREQUENCY rows (apexes at 50, 100 or 30 brought to 2-5);
- 23 STANDARD_GRAZER rows;
- role rows (Titanoboa, Dimetrodon, Tiktaalik, Eoraptor);
- 3 cluster rows;
- fossil realms.

The model reads it at classify time (§1.4). The raws are written in `V7.EXTINCT.apply` (:14222). The builder's apex
FREQUENCY also reads the corrected value before it is written (:7944-7950).

### 1.9 Vermin

Vermin are in the pool (`cat = 'vermin'`) but never fill a trophic slot (`ROSTER.inPart` :7721 excludes them).

- **Builder:** a vermin draw for the GOBBLE edge table only (`ROSTER.gobbleEdges` :8007), at most `gobble_max` (3) per
  class per layer.
- **Casts:** 2-3 vermin per cast that a cast member eats (§3.5).
- **Vermin class** `ROSTER.vclass` (:7982), from `VERMIN.family` (:3222):

| Class | Family |
|---|---|
| VF | fish. Since `29a8a91`, this also covers IMMOBILE_LAND or CANNOT_BREATHE_AIR vermin: guppy, clown loach, knifefish |
| VC | colony |
| VB | flying vermin that are small birds or mammals |
| VI | other flying vermin, and flies |
| VG | everything else |

### 1.10 Which layer a species belongs to: `ROSTER.inPart(cfg, e, layer)` (:7720-7737)

No species is in a part unless it is in the embark, not locked, not vermin, and not mega or night.

| Roster part | Members |
|---|---|
| `cavern` | cavern-layer entries that are not lava-only, inside the raw depth range at one or more of their cave depths (`ROSTER.depthOk` :7711: raw depth = `layer_depth` + 1; `depth_near` widens it by one), or with no depth recorded |
| `water` | every water-layer entry, plus land-layer entries that are aquatic, or semiaquatic and on the curated list as `apex`/`pelagic`, or curated `fisher`s when v7 `fishers` is on |
| `flying` | land-layer fliers and waterbirds |
| `land` | the rest of the land layer |
| (deep) | never a roster part (R60) |

### 1.11 Depth and lava guards

- `fireOnly` species are out of the cavern part (:7723).
- `PLACE.fromEntry` refuses `deep` entries and cavern entries outside raw depth (:4899-4905).
- `ROSTER.placeGroup` does the same (:8753, :8761-8764) and puts lava-only species only beside magma (`ROSTER.magmaSide`
  :8729), or refuses.
- `ROSTER.placeBorrowed` (:9030) is the opt-in `roster depth place` path.

### 1.12 Realms (v7 `realms`, off by default)

- `V7.REALMS` (:2040-2154) is a curated table of real-world ranges. It can be extended by
  `dfhack-config/seasonal-wildlife-realms.json` and by the extinct fossil realms.
- `V7.realmOk` (:2202) is applied **only by the builder** (`ROSTER.candidatesFor` :7854, with `cfg.realm` resolved at
  :8073-8078). COS is always allowed, and OCE is allowed on the water part.
- The casts do not apply realms.

---

## 2. The guild builder, `ROSTER.build(cfg, layer)` (:8064-8256)

### 2.1 Slot tables

`ROSTER.SLOTS` (:7740-7749) sets min-max per slot. `ROSTER.slotTable` (:7766) then adjusts them to the map:

| Part | Slots (min-max) | Map adjustments |
|---|---|---|
| land | APX 1-1, GZ 1-2, PL 1-2, ML 1-2, SH 0-1 | APX 1-**2** on a savage map (:7770) |
| flying | APX 0-1, RP 1-1, LB 1-2, WB 0-2 | (R50: one raptor slot) |
| water | APX 1-1, APE 0-0, FC 1-3, FF 1-2, SH 1-2, MW 0-1, PE 0-1, WB 0-1 | ocean on the map: APE 1-1, PE 1-1, or PE 1-**2** when a deep column exists (:7772-7773) |
| cavern | APX 1-1, PL 1-3, ML 0-2, RP 0-1, LB 0-1, SH 0-2, MW 0-1, FF 0-2 | APX max = number of cavern depths the part's species occupy (:7771) |
| any | + SN 0-1, SNP 0-1 | only with `roster.sn_slots` on (off by default) (:7776-7778) |

`ROSTER.context` (:7752) reads the map facts behind these adjustments:
- `savage` from `ROSTER.savage`;
- `ocean`: any ocean tile (`ENGINE.waterTiles().sum.ocean > 0`);
- `deep`: `ENGINE.deepColumns(cfg).n > 0`, meaning at least one sampled ocean column holding `water.column_levels` (3)
  stacked water tiles at level ≥ 4/7;
- the cavern depths present.

### 2.2 How a species gets its slot: `ROSTER.slotOf(cfg, e, layer)` (:7685-7705)

The rules are tested in this order:
1. **Cavern civ race with `civ_prey` on:** AL or AW becomes ML, or MW when aquatic. A civ race never holds an apex slot.
2. **`sn_slots` on, sentient and not a monster:** SN (tier ≥ 2) or SNP.
3. **Water part:**
   - the curated `aquatic_apex` kind `pelagic` → APE;
   - `apex` or `fisher` → APX;
   - any other AW, AL or ML → **MW** (R49 demotes the sea lamprey);
   - otherwise the guild.
4. **Flying part:** APX if `ROSTER.flyApex` (:7679) holds: an RP that is not sentient, not a cave species, not a
   scavenger (vulture, buzzard, kea, raven), with mass ≥ `fly_apex_min` (2000) or boosted. Otherwise the guild.
5. **Land and cavern parts:** AL, AW or boosted → APX; otherwise the guild.

Tiers (`ROSTER.TIER` :7667): APX, APE, AL and AW are 3; ML, MW, RP and SN are 2; every other guild is 1; V is 0. Trophic
level (`ROSTER.LEVEL` :7668): apex slots are A, ML/MW/RP/SN are C, everything else is H.

### 2.3 Which pairs count as a food link: `ROSTER.linkable(e, p, cfg, layer)` (:7794)

Three tests must all pass:
- e's tier is strictly above p's;
- `MODEL.reaches(e, p)` holds (:2565): neither is mega or night, p is not a sponge, the same ecology class, the same realm
  (surface or cavern), the habitat REACH table (:2531) allows it, and shared water when both are aquatic;
- in the caverns, the two share a cavern depth.

There is **no size test.** Size enters only through `preference()` in the pick weight.

### 2.4 Seed and pick weight

**The weight.** `ROSTER.pickWeight(e, roster)` (:7829-7841) is:

`w = (pack ? pack_bonus : 1) × (AP not civ ? ap_pick : giant ? giant_pick : 1) × (1 + Σ preference over linkable pairs with the roster so far)`

- **The pack bonus** (`ROSTER.packBonus` :7789): tier ≥ 2, not BENIGN, and raw `cmax > 1` (R41).
- **`preference(e, p)`** (:2576): `exp(−ln(M_prey / (0.4 M_pred))² / (2 × 1.2²))`. Vermin score 0.05.

`ROSTER.weightedPick` (:7842) is a weighted random draw (`rng:drandom`).

**The seed** (:8107-8114): the first slot in table order that has candidates with any link in the layer's candidate set.
The seed is a weighted pick among those candidates, against an empty roster.

### 2.5 Fill passes, the fallback when filling stalls, and unfilled slots

1. **Minimum pass** (`fillPass(false)` :8116-8130). Each slot fills to its `min` by weighted picks from the candidates not
   yet used.
2. **When filling stalls** (:8133-8158). If a slot is still below its min and the last pass made no progress, the builder
   takes the first unused candidate of that slot that links to any unused candidate p. It seats the candidate, and seats p
   too if p's slot has room (`pairsSeeded`). The loop has a 200-iteration guard.
3. **Maximum pass** (`while fillPass(true)` :8159). Every slot fills to its `max`.
4. **Unfilled slots** (:8161-8172). Each slot still below its min is reported with one of three reasons: `no candidate in
   pool`, `no edge in pool`, or `pool exhausted or no partner seated`. The builder then carries on: an unfilled slot is
   never fatal.

### 2.6 Link guard and the vegetation link (:8175-8208)

The builder repeats this step until nothing changes, with a guard of 200 rounds. A seated species with no link to any other
seated species goes through three checks:
- If it is a herbivore (level H, not CARNIVORE) and `V7.vegSupports(e)` holds, it stays, "kept by the vegetation link".
- Otherwise it is swapped for an unused candidate of the same slot that does link.
- Failing that, it is dropped.

**The vegetation index** is `V7.vegSurvey` (:7438-7505): `(region vegetation mean + grass share %) / 2`.
- The region vegetation is read through `getRegionBiome`.
- The grass share is the grass floor tiles over the outdoor walkable floor of the surface band.
- Shrub and tree counts are reported but not used in the index.
- The survey has a 1000 ms deadline and is cached per map.

**The need** is `V7.vegSupports` (:7511): `need = clamp(20 + 15 × log10(mass / 100,000 cm³), 10, 90)`, and the species is
supported when `index ≥ need`.

### 2.7 Outgun check (:8211-8224)

`ROSTER.outgunPairs` (:7805) finds every seated predator-prey pair where the prey is not BENIGN and the prey's
`mass × group` is at least `v7.outgun` (2.0) × the predator's `mass × group`. Each such pair is logged as a `build` ledger
line.

With v7 `outgun_cap` on (it is off by default), the builder also sets `cfg.group_size[prey]` to
`floor(predMass × factor / preyUnitMass)`. `PATTERN.sizeApply` then writes that as the raw CLUSTER_NUMBER on the next
groups pass.

### 2.8 The FREQUENCY ladder: `ROSTER.ladder(cfg, layer, members, ctx)` (:7882-7971)

The builder turns the seated species into FREQUENCY values (1-100) for the prey (H) and meso-predator (C) levels. Apexes
are handled separately, at step 8.

1. **Group by slot.** Apex-level members (APX, APE, AL, AW) go to a separate list.
2. **Base weight for each H/C member.**
   - `b = LADDER22[part][slot]` (:7874-7879). For SN or SNP members the code looks up their guild instead; a slot code with
     no entry falls back to 5.
   - On water, a PE member's `b` is tripled when `ctx.deep` (:7900).
3. **Mass scaling within its slot.** `scale = clamp((mass / geometric-mean mass of its slot)^−0.75, 0.25, 4)` (:7901).
4. **Animal-people and giant multiplier.** ×`ap_freq` or ×`giant_freq`, applied inside the level (:7906).
5. **Split between levels.** The pyramid's H:C shares are normalised, from `roster.pyramid[pk]`, where `pk` is
   ocean/lake on water (by `ctx.ocean`) and otherwise the part's own name.
   - If a level is empty, the other level takes 100%.
6. **Biomass guard** (land and cavern only, :7918-7925). If `uC × meanMass_C > guard × uH × meanMass_H` (guard = 0.5),
   then the code sets `r = guard × mH / mC`, `uC = r / (1 + r)` and `uH = 1 − uC`, and reports `binding = biomass guard`.
7. **Unit share, then scaling to 0-100.**
   - Each member gets `x = levelShare × v / ΣlevelQ`.
   - With `roster.units` on, x is divided by `ROSTER.groupMean` (:7862): the player's group size, else the raw cluster
     midpoint, not floored.
   - The result is rescaled so the largest x becomes 100, then rounded, and **floored at 1** (:7935-7939).
8. **Apex members (R34: no step on the ladder).**
   - `apex_odds > 0` → that value is written.
   - Else a raw FREQUENCY above `apex_raw_cap` (5) is written as the cap.
   - Else nothing is written, and the raw's own FREQUENCY stands. The "raw" here is the snapshot's original if one is held
     (`CAVERN.saved`). An extinct apex reads its corrected value (:7944-7950).
9. **Report.** `info` holds the targets, the binding constraint, the floored tokens, and the predicted carnivore share in
   waves and in units.

Default weights (`ROSTER.LADDER22`, :7874-7879) and pyramid targets (`V7.rosterDefaults().pyramid`, :7556-7558):

| Part | Guild weights inside a level | Pyramid H / C / A (%) |
|---|---|---|
| land | GZ 10.5, PL 8.75, SH 7, LB 6, WB 6, ML 2, MW 2, RP 2 | 73 / 20 / 7 |
| flying | LB 30, WB 30, RP 2, ML 2 | 80 / 20 / 0 |
| water | FC 12, FF 12, WB 9, SH 6, GZ 6, PL 6, PE 2, MW 2, ML 2 | ocean 82 / 13 / 5; lake 87 / 13 / 3 |
| cavern | GZ 12, LB 12, WB 12, FF 12, PL 10, SH 8, ML 2, RP 2, MW 2 | 60 / 27 / 13 |

The A share is not used by the ladder. Apex presence is the scheduler's job, at its own targets (§2.10).

### 2.9 What the build writes (:8226-8251)

For every candidate in the part whose slot is in the table but was not chosen:
- `ROSTER.setActive(..., false)`, if it was active;
- `cfg.odds[key] = nil`.

For every member:
- `ROSTER.setActive(..., true)`. A member with no season gets **one** default season (`ROSTER.defaultSeason` :2675);
- `cfg.odds[key] = ladder[key]`;
- apex-level keys are added to `cfg.roster.apex_keys[part]`.

Then:
- `ROSTER.gobbleEdges` builds the vermin edge table for the part;
- one `build` ledger line is written;
- the verb pushes one undo step (:18470), saves, and runs `applyLive` when rotation is on.

The FREQUENCY values themselves reach the raws only through `CAVERN.apply` (§4).

### 2.10 Apex scheduler (R9, R34): `ROSTER.placeTick` (:8893) and `ROSTER.apex.decide` (:8845)

- **When it runs.** Once per game day from `tick()` (:4148-4152), for each part with `apex_keys`, then for the R36
  invasives (:8917-8923).
- **Presence.** It measures the share of time an apex group of those races is on the map, counted by population source
  (`ROSTER.apex.groupsOnMap` :8702). DF's own waves count.
- **When it stops.** Reached the cap (`cap_calm` 1 or `cap_savage` 2, chosen at :8905), or at target after 7 days of observation.
- **Otherwise.** It places with probability `1 − exp(−λ·dt)`, where `λ = P / ((1 − P) × residence)`, P = presence % / 100
  (capped at 0.95), and residence is 21,500 ticks (:8862-8867).
- **What it places.** A uniform random choice among the keys that are active, in season and stocked. The group is placed
  by `ROSTER.placeGroup` (:8749), which debits stock, enters land groups at the map edge and water groups by the
  water-body rule, and leads the group at once.
- **Presence targets:** land 25%, flying 0%, water 20%, cavern 70%.

### 2.11 What the builder does **not** do

- It does not run on enable, on load or on any timer.
- It does not set seasons beyond the one default.
- It does not touch other parts.
- Its realm filter, ladder and apex keys are not used by the casts.

---

## 3. The v7.3 season casts (commits `64f9972` .. `09ab266`, 7-8 Oct)

### 3.1 The rule

The header at :8259-8277 sets out the rule. The pool (the embark's species) is not the roster.

- Each season, the tool grows a **cast** for each of the three roster layers (land, water, cavern).
- **The cast is that season's roster.** A cast species is active in the seasons it is cast in.
- Every other species those layers manage **rests**: inactive, with no season.
- Only species that have a season may be on the map.

### 3.2 The cast layers and their slots (`ROSTER.CAST` :8282-8297)

| Layer | Parts merged | Slots (want) | Total slots | Vermin |
|---|---|---|---|---|
| land | land + flying | apex (APX) 1; meso (ML) 2; raptor (RP, or a flying APX recoded `FAPX`) 1; grazer (GZ) 2; ground prey (PL, SH) 2; bird (LB, WB) 1; sentient (SN, SNP) 1 | 10 | 3 |
| water | water | apex (APX, APE) 1; meso (MW) 1; fish (FC, FF) 3; pelagic (PE) 1; shore (SH) 2; waterbird (WB, LB) 1; sentient 1 | 10 | 2 |
| cavern | cavern | apex (APX) 1; meso (ML, MW) 2; ground prey (PL, GZ, FF) 3; flier (RP, LB) 1; shore (SH) 1; sentient 1 | 9 | 3 |

So a cast holds at most 13, 12 or 12 species, vermin included. With `sn_slots` off, the sentient slot can never fill
(problem P7), so the real ceiling is 12, 11 and 11. The header (:8276-8277) records the desk's means: land 8.8 + 2.7
vermin, water 8.2 + 2.0, cavern 9.0 + 2.8.

### 3.3 The season's candidates: `ROSTER.castPool(cfg, pool, layer, season)` (:8388-8414)

**Non-vermin.**
- Every entry in the layer's parts (`ROSTER.inPart`) qualifies, unless the **raw** has `NO_<season>` for this season
  (`e.noSeason`).
- Each candidate gets its cast slot and code from `ROSTER.castSlot` (:8373), which uses `slotOf` on its own part. A code
  that no cast slot names leaves the candidate with no slot.

**Vermin** (`castVerminOk` :8379):
- cavern: cavern-layer vermin;
- water: water-layer vermin, plus land-layer VF vermin;
- land: land-layer vermin that are not VF.

Since `29a8a91` there is one candidate per species token, with the layer's own entry taken first (:8402-8412). A mussel
with both a water and a land entry no longer fills both vermin slots.

### 3.4 Who eats whom, and who can never be cast

**`ROSTER.castEats(a, b)`** (:8416-8429).
- A vermin eats nothing.
- If b is vermin, a eats it when `ROSTER.vdiet(a.e, a.code, a.part)` covers b's class. `ROSTER.VDIET` (:7980):
  - ML eats VG, VC and VF; MW eats VF; an aquatic APX eats VF; RP eats VB and VI;
  - a cavern LB eats VB, VI and VG;
  - vermin-root animal people eat VG, VI and VF;
  - DF's own gobblers eat VG and VC.
- Otherwise a eats b under the builder's link rule: a higher tier, `MODEL.reaches`, and a shared cavern depth. Each species
  takes its tier from its **own** part, so a raptor (flying part) can take ground prey (land part).

**`ROSTER.castExcluded`** (:8431). A species is never castable this season if:
- it has no cast slot; or
- none of its food-web neighbours is castable. This check is repeated until stable.

### 3.5 Growing one cast: `ROSTER.castGrow(cfg, pool, layer, season, prev, r)` (:8451-8566)

1. **The food web.** Build `eats` and the undirected neighbour map `nb` over every pair of candidates.
2. **The weight of a candidate** (:8472-8479): `1` × `cast.pack` (3) if `packBonus` holds × `cast.carry` (0.25) if it was
   in the previous season's cast × `cast.giant` (0.2) if a giant × `roster.ap_pick` (0.1) if an animal person that is not
   civ. Unlike the builder, there is no preference sum over links.
3. **The seed** (:8495-8507). A weighted pick among non-vermin, non-excluded candidates for which `ROSTER.highValue` holds;
   if there are none, a weighted pick among all of them. `ROSTER.highValue` (:8349-8371) counts a species as high-value
   for any of:
   - **pet value** ≥ `cast.hv_petvalue` (200). For a giant, the root animal's pet value is read (DF gives every giant 500);
   - **training**: TRAINABLE_WAR or TRAINABLE_HUNTING;
   - **parts**: mass ≥ `cast.hv_mass` (1,000,000 cm³), or a creature material named IVORY, PEARL, SILK or SHELL.

   The answer is memoized in `CACHE.hv` by token.
4. **Growth** (:8509-8530), with a guard of 400 rounds:
   - Pick a random member that has not been set aside.
   - Its candidates are its neighbours that are not vermin, not already cast, not excluded, and whose slot still has room.
   - If it has none, set it aside.
   - Otherwise take the candidates whose slot has the largest fractional room (the emptiest slot first). Among those, make
     a weighted pick, and log `FROM -> TO (slot, its prey | its predator)`.
   - Stop when every slot is full, or every member is set aside.
5. **Unfilled slots** (:8531-8538): `"have of want: none in season in the pool"` or `"no link to the cast from the N in the
   pool"`.
6. **Vermin** (:8540-8561). Take the vermin that cast members eat, shuffled with `r`:
   - first, one per distinct class;
   - then by how many members eat them;
   - up to `L.vermin` in all.
7. **Edges** (:8562-8565): every cast-to-cast `eats` pair, kept as `{PRED, PREY}` tokens.

### 3.6 A year of casts: `ROSTER.castYear(cfg, pool, year, why)` (:8589-8633)

**Growing the casts.** For each layer that `cfg.layers` has on (land, water, cavern; deep never), for s = 0..3:
- **The random seed is fixed** by
  `seed = (site_id × 7919 + year × 104729 + s × 131 + #layer × 17 + cast.salt) % 2147483647` (:8602), so the same fort,
  year and salt always grow the same casts.
- **Carry-over:** `prev` for spring is the stored winter cast for that layer (:8599-8600). Each later season uses the
  season before it.

**Writing the roster.** For every pool entry that a cast layer manages (`ROSTER.castManages` :8576 — its parts and
vermin, and also locked or unpartitioned species of that layer, so that BLOOD_MAN and ELEMENTMAN_MUD rest instead of
leaking in at their raw odds):

| Case | What castYear writes |
|---|---|
| cast in ≥ 1 season | `allow = true`, `assign = those seasons`, why `cast <why>` |
| cast in no season | `allow = false`, `assign = nil`, why `resting: in no cast this year`; a locked one also goes into `casts.rest` (:8618-8625) |

`casts.rest` matters because `V7.sanitizeLocked` drops a locked key from `allow` at load. `ROSTER.managedKey` (:2723)
treats keys in `casts.rest` as held, so `applyLive` and `holdOutOfSeason` keep their stock at 0. `CAVERN.apply`
(:3716-3724) holds their FREQUENCY.

The result is stored as `cfg.casts = {year, built = absTick, layers = {land = {[1..4] = cast}, ...}, rest}`, and a
`season` ledger line is written.

### 3.7 What "resting" means on each layer

| Layer | Lever | Code |
|---|---|---|
| land, water | stock: every entry's `quantity = 0` and `flags.extinct = true`. The old quantity is remembered in the RESERVE (site data `seasonal-wildlife/reserve`), at the season apply and again by the daily hold | `applyLive` :3027-3067, `holdOutOfSeason` :3072-3092 |
| water (the tool's own draw) | `ENGINE.candidates` draws only keys that `ROSTER.wants` (active and in season) | :5978-5980 |
| cavern (and deep) | raw FREQUENCY held at `CAVERN.restLevel` | `CAVERN.apply` :3698-3760, `CAVERN.restLevel` :3683-3697 |

`CAVERN.restLevel(cfg, token)` reads `cast.cavern_rest_freq` (no default in `CAST_DEF`; `nil` means 1).
- **≥ 1:** that value. The comment at :3680-3682 notes that "frequency 1 still leaks ~15%".
- **0:** 0, unless the raw is vermin.
  - `classify().gameVermin` is one guard.
  - So is any of the creature flags VERMIN_FISH, VERMIN_SOIL_COLONY, VERMIN_ROTTER, VERMIN_GROUNDER, VERMIN_SOIL, or the
    caste flag VERMIN_MICRO (`09ab266`).
  - Vermin stay at 1 because zeroing CREEPY_CRAWLER froze DF (:3623-3630).
- **Scope.** `restLevel` applies to **any** token `CAVERN.apply` holds while casts are on (`not w.open`, :3753). That
  includes a cavern species that is cast but out of its season, and **deep-layer** keys (problem P5).

### 3.8 When casts are built, and how they are reloaded

| Moment | What happens | Line |
|---|---|---|
| `enable` / `on` on a fort with `full_enable_roster` unset | `captureDefault`; if `cast.enabled` (default true), every switch goes on, then `castYear(..., 'enable')`. The preset is skipped | `PANEL.fortOn` :16086-16123 |
| first frame on a fort the tool has never run on | `map_loaded` → `PANEL.fortOn` | :16280-16292 |
| every season change in a new year | `V7.ST.turn` calls `castYear(..., 'new year')` when `castOn` and `casts.year ~= cur_year`, before `applyLive` | :4093-4110 |
| `cast rebuild [SALT]` | sets `cast.enabled = true`, rebuilds this year, saves, then `applyLive` and `CAVERN.apply` | :18359-18369 |
| map load | **no rebuild.** Since `b0895b9`, `V7.castSanitize` (:8315-8347) reads back `full_enable_roster`, `migrated_v71`, the `cast` switches (by type) plus `cast.cavern_rest_freq`, and `casts` (year, built, the four seasons of each layer with members, vermin and seed, the rest of each record copied as is, and `rest`) | :1058 |
| an existing fort (`full_enable_roster` already true) | casts are **never** built automatically. `castOn` needs `cfg.casts`, so the fort stays on its old roster until `cast rebuild` | :16090, :8305 |

**When the season changes** (`34a3a4b`):
- `V7.ST.arm` (:4124) sets a one-shot timer for the boundary tick.
- `V7.ST.now` (:4111) runs the change, retrying every 10 ticks up to 12 times until DF flips the season.
- The groups pass (:13210-13218) is the fallback, and the daily `tick` (:4133) the last resort.

`V7.ST.turn` runs in this order: `exhaustRoll`, `spillRoll`, the new-year casts, `applyLive`, a ledger line, the trickle,
then `CAVERN.apply`.

### 3.9 What follows the cast while it runs

- **Turnover.** `V7.GRP.castTurnover` (:12778-12798), once per season stamp, sends off every tracked group whose key is
  not wanted this season. Since `8817eb4` it falls back to the land key for water groups.
- **Natives under casts.** Every land and water native is adopted as a group, so the turnover can reach it, and so are
  flagged fish seeded from a water feature (`V7.GRP.adoptNatives` :12809-12822).
- **Exhaustion swap.** An in-season species whose stock runs out can be swapped for a species in the same cast slot that
  is linked to this season's cast (`ROSTER.castReplaceOk` :8635). The stand-in may be a resting species; it rests again
  at the next change (`exhaustRoll` :3113). Since `6e1ffb2`, exhaustion waits until `applyLive` has stamped
  `CACHE.appliedStamp` for this season (:3127).
- **Water spill** is off under casts (:7362).
- **Ecology.** Relation writes between wild pairs are kept only for this season's cast edges (`ROSTER.castEdgeSet` :8673,
  used at :5128 and :5183).
- **Nudges** stay parked (`V7.parkNudges` :1071; `PANEL.fortOn` and `allOn` leave the parked switches off).

### 3.10 The `cast` verb (:18333-18405)

| Verb | Effect |
|---|---|
| `cast [status]` | each layer and season: member count + vermin count, seed, members and vermin |
| `cast show SEASON [LAYER]` | the seed and why, members by slot, vermin, unfilled slots and why, the growth log, the edges, and the never-castable species with their reasons |
| `cast rebuild [SALT]` | grow this year again, with a new salt if given; apply at once |
| `cast restfreq 0\|1` | `cast.cavern_rest_freq`; runs `CAVERN.apply` at once when rotation is on |
| `cast on\|off` | `cast.enabled` only. **It neither builds nor removes casts** (see P4) |

The verb is console-only. It is not in the controls registry or the web's verb whitelist (controls :724-728), and there
is no cast row in the window.

---

## 4. Raw and game fields the roster code writes, and how each is undone

| What is written | Writer | Undo path |
|---|---|---|
| **Population entry** `quantity`, `quantity_max` and `flags.extinct` (stock) | `applyLive` :3027, `holdOutOfSeason` :3072, `RESERVE.set` :3015, `ROSTER.exhaustCheck` :3121, `V7.WAT.spillCheck` :7397-7408 | The held quantity is kept in the RESERVE (site data) and given back when the key is wanted again with rotation on (:3045-3053). `reset everything` puts entries back to the worldgen snapshot (`resetToDefault` :3928). **Disable, `off` and `all off` do not restore stock** (P2) |
| **Creature raw `FREQUENCY`**: the builder's ladder (`cfg.odds`), holds at 1, `restLevel` (0 or 1), the cavern gate's hold | `CAVERN.apply` :3698, `CAVERN.write` :3647, `V7.GRP.cavernHold` :12723 | The first original value is saved in the snapshot (site data `seasonal-wildlife/cavern`). Put back by `CAVERN.restoreAll` (:3659) on disable (:15953) and `all off` (:16045). An orphaned hold is put back by `V7.GRP.orphans` (:12708) in every `CAVERN.apply`. **Not at world unload** (P10) |
| FREQUENCY floor for animal people at 0 (R61) | `ROSTER.freqFloorApply` :8952 | `V7.rec` → `V7.restore` (disable, all off, world unload, every `V7.apply`) |
| Extinct FREQUENCY, GRAZER plus `misc.grazer`, LP/CARNIVORE/BENIGN/AMBUSH, `HAS_ANY_*`, cluster, the wild units' `enemy.caste_flags` | `V7.EXTINCT.apply` :14222 | `V7.rec` → `V7.restore`; a value written into the CAVERN snapshot or a pattern snapshot follows those restores (:14157-14185) |
| `NO_SPRING`..`NO_WINTER` cleared on managed species (`seasons_own`) | `V7.apply` :13833-13835 | `V7.rec` |
| **CLUSTER_NUMBER** {n, n} from `cfg.group_size` (including the builder's `outgun_cap`), and the trickle's {2, 1} | `PATTERN.sizeApply` :10342, `PATTERN.trickleApply` :10318 | `PATTERN.sizeRestore` and `trickleRestore`: on disable, all off and world unload (:17102) |
| GOBBLE_VERMIN_CLASS / _CREATURE and the SWV_* classes | `VERMIN.gobbleApply` :14663 (reads `ROSTER.GOBBLE_EDGES` only if a build ran this session; else the rules) | `V7.rec` |
| **Config** `allow`, `assign`, `why`, `odds`, `group_size`, `roster.apex_keys`, `roster.invasive`, `casts` | builder, casts, preset, normalize | Not a game write. One undo step for `roster build`, `roster set`, `roster`/`seasons` edits and the preset (window). **`cast rebuild` pushes no undo** (P11) |
| **New units** (apex and invasive groups, `roster depth place`) | `ROSTER.placeGroup` :8749, `ROSTER.placeBorrowed` :9030 | None. They are visitors with a leave countdown (`apex.residence`); DF refunds departures |
| **New population entries** (Add invasive; `roster depth place` when DF stocked none) | `addNewSpecies` :4008, `ROSTER.caveEntryFor` :9005 | None. They stay in the world |

---

## 5. Config keys, their defaults, and where they are exposed

### 5.1 `cfg.roster`

Defaults are in `V7.rosterDefaults` (:7546-7589). They are sanitised by `V7.rosterLoad` (:7591): numbers 0..1e7, the pyramid
0..100, presence 0..95. **A saved `aquatic_apex` replaces the whole default list.**

| Key | Default | Panel / web control (controls.lua) |
|---|---|---|
| `units` | true | `roster.units` :163 |
| `apex_odds` | 0 (no apex step) | :177 |
| `apex_raw_cap` | 5 | :178 |
| `pyramid.{land,flying,ocean,lake,cavern}.{H,C,A}` | 73/20/7, 80/20/0, 82/13/5, 87/13/3, 60/27/13 | H and C per layer :164-167 (A not exposed) |
| `biomass_guard` | 0.5 | :168 |
| `ap_pick`, `giant_pick` | 0.1, 0.2 | :170, :174 |
| `ap_freq`, `giant_freq` | 0.25, 0.5 | :171, :175 |
| `ap_freq_floor` | 1 | :172 |
| `ap_vermin_mass` | 0 (the person's own size) | :173 |
| `pack_bonus` | 3 | :176 (1-5) |
| `sn_slots` | false | :179 |
| `giant_boost` | true | :180 |
| `fly_apex_min` | 2000 cm³ | :181 |
| `depth_near` | false | :182 |
| `gobble_max` | 3 | :183 |
| `aquatic_apex` | 33 tokens: 16 apex, 11 pelagic, 6 fisher (:7567-7580) | per species :569 (`roster aquatic`) |
| `apex.enabled` | true | :155 |
| `apex.presence.{land,flying,water,cavern}` | 25, 0, 20, 70 | :156-158 |
| `apex.cap_calm`, `apex.cap_savage` | 1, 2 | :159-160 |
| `apex.residence` | 21500 ticks | :161 |
| `apex.savage_cut` | 66 | not exposed |
| `apex.invasive_presence` | 25 | not exposed |
| `pred.{ideal,sigma,pack_exp,k_large,need_solo,need_herd}` | 0.4, 1.2, 0.75, 1.5, 0.6, 0.9 | :185-187; copied into the `PRED` upvalue by `V7.rosterSync` (:7629) |
| `apex_keys`, `invasive` | written by the build / Add invasive | readouts only |

Actions and readouts: `roster_build` (:188), `apex_now` (:189), `roster`, `roster apex status`, `roster gobble`,
`roster outgun`, `roster depth`, `roster aquatic` and `realm table` (:190-196).

### 5.2 `cfg.cast` and `cfg.casts` (v7.3)

Defaults are in `ROSTER.CAST_DEF` (:8298) and `castSanitize` (:8315). **None of these is in the controls registry or on
the web.**

| Key | Default | Meaning |
|---|---|---|
| `cast.enabled` | true | casts as the roster (`castOn` also needs `cfg.casts`) |
| `cast.carry` | 0.25 | weight × for last season's members |
| `cast.giant` | 0.2 | weight × for giants |
| `cast.pack` | 3 | weight × for a group hunter |
| `cast.hv_petvalue` | 200 | the pet-value bar for high value |
| `cast.hv_mass` | 1,000,000 cm³ | the body-size bar for high value ("parts") |
| `cast.salt` | 0 | added to the random seed (`cast rebuild SALT`) |
| `cast.cavern_rest_freq` | absent (= 1) | FREQUENCY of resting cavern species; the verb accepts only 0 or 1 |
| `casts` | built | `{year, built, layers.{land,water,cavern}[1..4], rest}` |
| `full_enable_roster` | absent | set by the first full enable; it stops a later enable from re-rostering |

There are also fixed per-layer constants, which are not config: the slot wants (`ROSTER.CAST`, :8282-8297), the vermin
counts (land 3, water 2, cavern 3) and the high-value materials (`ROSTER.HV_MATS`, :8299).

### 5.3 Other keys that shape the roster

| Key | Default | Exposed |
|---|---|---|
| `v7.builder` | true | controls :433 |
| `v7.outgun` / `v7.outgun_cap` | 2.0 / false | :446-447 |
| `v7.realms` / `realm` | false / `''` | :448-450 |
| `v7.civ_prey`, `civ_hunt` | true | v7 section |
| `v7.seasons_own` | true | v7 section |
| `v7.fishers` | true, but **parked to false** by `V7.parkNudges` (:1078) | v7 section |
| `v7.aligned`, `cave_aligned`, `fanciful` | true | v7 section |
| `classes.*` | only `natural` true (:818) | not shown (D8) |
| `extinct.{fix,freq,grazer,roles,cluster,realms,units,stand_down}` | all true; `grazer_g` 100 | controls :418-428 |
| `water.column_levels` | 3 (the "deep" column test for PE) | water section |
| `layers.{land,water,cavern,deep}` | land only by default; `enable` turns on every layer, **deep included** (:16011, :16101) | Panel switches |
| `exhaust.enabled` | true | Panel |
| `in_season_qty`, `weight` | 100, 50 (the restock when there is no reserve and no snapshot: `qtyFor` :2453) | window |

---

## 6. Problems, gaps and suspicious logic (with lines)

**P1. Under season casts, the FREQUENCY ladder and the apex scheduler are idle unless someone runs `roster build`.**
- `castYear` writes only `allow` and `assign` (:8617-8625). It never writes `cfg.odds` or `roster.apex_keys`.
- `ROSTER.placeTick` returns at once with no apex keys and no invasives (:8896-8899).
- `ROSTER.build` has exactly one caller, the verb (:18429). On a v7.3 fort, every species therefore runs at its raw
  FREQUENCY, and no apex is scheduled.
- If `roster build` *is* run, its `cfg.odds` and `apex_keys` survive every later `castYear`. The apex scheduler then
  places only keys the cast wants this season (:8871). A cast apex that the build did not pick is never scheduled.
- The registry's own help says this: "It acts only after `roster build` seats apexes" (controls :155).

**P2. Stock writes are not undone by `off`, `disable` or `all off`.**
- `disableSched` (:15950-15981) and `PANEL.restoreAll` (:16042-16059) restore FREQUENCY, cluster, flags and raws, but
  never population quantities.
- Every resting or out-of-season entry stays at `quantity = 0, extinct = true`. Its value is held in the RESERVE until
  the tool runs again.
- Yet `turn_off` prints "every job stopped and every write put back" (:16275), and the PANEL comment says "puts back
  everything the tool wrote" (:15994).

**P3. `cast off` does not survive a save and load.**
- `castSanitize` uses `c.cast[k] = (type(r) == type(v)) and r or v` (:8322). With a saved `enabled = false`, this gives
  `true and false or true`, which is **true**.
- So after a reload the casts are on again, and they rebuild at the next new year.
- The same trap would hit any future boolean in `CAST_DEF` that defaults to true.

**P4. `cast off` does not bring back "the preset roster" as its help says (:18340).**
- It only clears `cast.enabled` (:18347-18350). `allow` and `assign` stay as the casts left them: this year's casts become
  a fixed, all-year roster, and resting species stay inactive.
- `cast on` with no casts prints a hint, but `castOn` stays false until `cast rebuild`.

**P5. `restfreq 0` reaches past "resting cavern species".**
- `CAVERN.apply` applies `restLevel` to *every* held token while casts are on (:3753). That includes cast species out of
  their season, and **deep** keys.
- `PANEL.fortOn` turns the deep layer on (the `deep` switch is not opt-in, :16011, :16101).
- Under casts, deep species are made active with one default season by `ROSTER.normalize` in `enableSched`
  (:15933 — it runs whatever the casts say), because `castManages` never covers deep.
- So with `cast restfreq 0`, magma-sea non-vermin species out of their one season are written FREQUENCY 0. The verb and
  its ledger line say "resting cavern species" (:18351-18357).

**P6. The comment and commit on the vermin guard misstate the pool's vermin test.**
- `09ab266` and the comment at :3690-3691 say "the pool's vermin test reads only GROUNDER, ROTTER and SOIL".
- `classify` actually reads six flags: GROUNDER, ROTTER, SOIL, FISH, EATER and SMALL_RACE (:1801-1802).
- The added guard is harmless, but its stated reason is wrong.

**P7. The `sentient` cast slot can never fill with the default settings.**
- `ROSTER.slotOf` returns SN or SNP only when `roster.sn_slots` is on (:7693), and that defaults to false (:7562).
- Every cast's `sentient` slot therefore reports `0 of 1: none in season in the pool` (:8531-8538). The real cast size is
  one less than the table's want.

**P8. The cast and builder slot tables differ, and some guilds have no slot on some layers.**
- **Water casts:** no slot for GZ, PL or RP. A water-layer grazer, land prey or raptor is "no slot on this layer" and
  rests all year. `LADDER22.water` has GZ and PL weights (:7876), but `SLOTS.water` has no GZ or PL slot either.
- **Cavern:** the builder has no GZ slot (:7746-7747), but the cavern cast seats GZ under "ground prey" (:8293).
- **Flying apex:** recoded `FAPX` in the land cast (:8375). `ROSTER.VDIET` has no FAPX, so a flying apex in a land cast
  eats no vermin.

**P9. The cast honours the raw `NO_<season>` flags, and the outcome depends on when the species was classified.**
- `castPool` drops a species whose raw forbids the season (:8394, :8406).
- With `seasons_own` on (the default), the tool's season deal is meant to override the raws: `ROSTER.fitSeason` :2657;
  `ENGINE.candidates` :5999; `exhaustCheck` :3158. `V7.apply` clears those flags on managed raws (:13833-13835).
- `classify` reads `noSeason` from the raw at first classification and memoizes it. After `UNDO.after` (:15985), `extinct` edits (:14381) or
  `roster set ap_vermin_mass` (:9267) clears `CACHE.class` while the flags are still cleared, `noSeason` reads all false.
  The same fort can then grow different casts.

**P10. Cavern FREQUENCY writes are not restored at world unload.**
- The world-unload handler restores CURIOUS, V7, the trickle, sizes and HUNT (:17100-17106), but not
  `CAVERN.restoreAll`. Only disable and `all off` call it (:15953, :16045).
- The `CAVERN.restoreAll` comment says it is "Called on disable, on unload" (:3656-3658). That is not true of the code.
- The code relies on DF re-reading raws at load (:3619-3621). The snapshot stays in site data and is reused.

**P11. `cast rebuild` is a full roster rewrite with no undo step** (:18359-18369). `roster build` and the preset push one.

**P12. Manual edits under casts are temporary, and some of them break the food web.**
- `roster KEY active`, `seasons KEY ...`, the window's "Re-apply preset" (gui :1544), the `preset` verb (:18273),
  `roster build`, and a newly enabled layer (`layer` verb :18292-18298; controls :806, which runs `ROSTER.normalize`) all write
  `allow` and `assign` while `cfg.casts` stays. The next new year's `castYear` overwrites them without warning.
- The ecology keeps only cast edges (:5183). A species activated by hand, or by normalize, therefore gets no predator-prey
  relation writes.

**P13. Exhaustion stand-ins under casts get no relation writes.**
- `castReplaceOk` admits a stand-in because it links to the cast (:8635-8661).
- `castEdgeSet` holds only the edges grown into the cast (:8673-8684), so the stand-in's pairs are filtered out (:5183).

**P14. The cast turnover may skip a run after a reload.**
- The comment says "Once per season (and once after load)" (:12775). But `CACHE.castTurnStamp` (:12781-12782) is not
  cleared by `CACHE.drop` (:17078-17096).
- Reloading a save in the same year and season during one DFHack session skips the turnover. Only `cast rebuild` clears
  the stamp (:18365).

**P15. The high-value memo is stale across settings and worlds.**
- `CACHE.hv` is keyed by token only, and nothing clears it (:8350-8368; it is not in `CACHE.drop`).
- Changes to `cast.hv_petvalue` or `cast.hv_mass`, or a different world's raws in the same session, are ignored until
  DFHack restarts.

**P16. The cast record is saved in full to site data on every `saveConfig`.**
- `castYear` stores each season's `slots`, `log`, `edges`, `unfilled` and `excluded` (one reason string per
  never-castable species) for 3 layers × 4 seasons (:8603-8605). `castSanitize` copies these back as is (:8336).
- `saveConfig` writes the whole config (:1138) and is called from the groups pass, from exhaustion and from every edit.
  The code shows nothing that measures this cost.

**P17. The web's "Build the roster" with "all" builds land only.**
- The action maps `all` to `''` (controls :188, :905), so the verb runs as `roster build`.
- `layerArg = v or 'land'` (:18424) then builds just land. There is no "every layer" path.

**P18. Dead code.**
- No callers in the shipped scripts: `ROSTER.effectiveMax` (:7782), `ROSTER.slotGuild` (:7708).
- Kept "for reference only": `ROSTER.LADDER` (:8686-8690).
- Returns 0 but is still exported: `fillThinSeasons` (:2748, :17448).
- Mentioned as "the vermin stream's entry point" but only the `roster gobble` verb calls it: `ROSTER.gobbleEdgesActive`
  (:8053). `VERMIN.edges` (:14607) falls back to the rule table when no build ran this session, so the casts' vermin
  edges never reach GOBBLE writes.

**P19. Two knobs for one rule.** Giants are weighted ×0.2 by `roster.giant_pick` in the builder (:7832) and by
`cast.giant` in casts (:8477). Animal people use `roster.ap_pick` in both.

**P20. Weak range checks.**
- `roster set` accepts any number ≥ 0 for numeric keys, and any numbers for `pyramid` (:9249-9260). The load sanitiser
  bounds them later (0..1e7; pyramid 0..100).
- `castSanitize` takes any `cavern_rest_freq` number (:8324). A negative value falls into the 0 path of `restLevel`.

**P21. The cavern gate's hold can bump a FREQUENCY-0 resting species back to 1.**
- `V7.GRP.holdFor` (:12691-12699) knows nothing of `restLevel`. When a cavern reaches its cap, `cavernHold` writes 1
  (`CAVERN.SUPPRESSED`) for species not wanted this season (:12752-12757).
- With `restfreq 0`, those stay at 1 until the next daily `CAVERN.apply`.

**P22. Casts are never built on forts enabled before v7.3** (`full_enable_roster` already true, :16090). Those forts keep
their preset or builder roster until `cast rebuild`, with no notice.

**P23. No offline test covers the casts.** `tests/` holds `aquarium`, `gui`, `perf`, `rig`, `water` and `web`. None of
them names `castYear`, `castGrow` or `cast rebuild`.

---

## 7. Where the docs disagree with the code

| Doc claim | Code |
|---|---|
| `docs/v7.1/roster.md`: the curated water-apex list has "34 entries" and includes PERMIAN_DIMETRODON (river) | 33 entries. Dimetrodon was removed: the extinct fix seats it on land (comment :6168-6169) |
| `docs/v7.1/roster.md` line references (:5509, :5367, :5895-6060 ...) | Stale: `ROSTER.ladder` is now :7882, `ROSTER.SLOTS` :7740, `ROSTER.apex` :8700-8930 |
| Engine header :31-32: "A fort's first enable builds its roster with the preset (never reshuffled later)"; the same at :16083 | With `cast.enabled` (the default), the first enable builds **season casts** instead, and they are regrown every year (:16093-16106, :4098) |
| `cast on\|off` help: "off: the preset roster" (:18340) | `off` only flips the switch; the roster is not changed (P4) |
| `turn_off`: "every write put back" (:16275) | Stock is not restored (P2) |
| `CAVERN.restoreAll` comment: "Called on disable, on unload" (:3656) | Not called at unload (P10) |
| `09ab266` and :3690-3691: the pool's vermin test "reads only GROUNDER/ROTTER/SOIL" | It reads six flags (P6) |
| `castTurnover` comment "once after load" (:12775) | Not after an in-session reload (P14) |
| `HANDOFF.md` (dated 1 Oct), `PLAN.md`, `STATE.md`, `README.md`, `USAGE.md` | **None mentions v7.3 season casts, `cast`, `restfreq` or resting.** HANDOFF's architecture table (:89) lists the ROSTER table without casts. USAGE describes the builder as the roster path (:131, :227, :341) |
| `docs/v7.1/roster.md` "Panel / web exposure" lists only builder and apex controls | It is still accurate for those; nothing exposes casts (§3.10) |
| `docs/v7.1/extinct.md`: 83 rows | It matches the code: 83 rows, 21 FREQUENCY, 23 GRAZER, 3 cluster |
