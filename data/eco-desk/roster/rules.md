# Roster / food-web rules: operational definitions (prototype, files only)

Code: `roster.py` (`Cfg` holds every knob below; `build(embark, layer, season, seed, cfg)` is pure).
Data: `eco/census.json` (DF 53.16 vanilla raws, inheritance resolved), `features.json` (from `feat.py`: body plan, syndromes,
physiology flags, re-resolved from the same raws), the tool's own classification `DwarfCron/data/fixtures/species-model.tsv`
(role, size band, mass, ecology class). Token effects come from `eco/wiki-tokens.md` and `eco/findings.md`, never from token names.

## 0. Universe

- Vanilla, not extinct, has BIOME, the tool's ecology class = `natural`, not IMMOBILE. 694 species.
- That set **includes giants (178) and animal people (284)**: the tool classes both `natural` and mirrors an animal
  person's role, habitat and mass from its root animal (SW v6.7.0). mega / night / unliving / mythic / generated /
  unclassified are excluded. No giant is in any of those classes, so "except where rule A/D mentions GIANT" needed
  no special case.
- `Cfg.ap=False` drops animal people and civ races. That is a variant, not the default.
- **Sentient** = animal person, or CAN_SPEAK, or CAN_LEARN on any caste. This covers civ races with a BIOME, e.g.
  AMPHIBIAN_MAN, TROGLODYTE, GREMLIN.
- **Giant** = census `kind == giant` (APPLY_CREATURE_VARIATION:GIANT).
- **Mass** = the tool's `mass` (adult cm3).
- **Size band** = the tool's: small < 150,000; medium < 1,000,000; large otherwise.
- **Role** = the tool's `MODEL.role`: predator if any caste has CARNIVORE, BONECARN, LARGE_PREDATOR or AMBUSHPREDATOR, plus
  its 4 overrides.
- **BENIGN** = BENIGN on all castes. **LP** = LARGE_PREDATOR on any caste.
- **Cluster max** = the second number of CLUSTER_NUMBER (default 1). **Pack** = cluster max > 1 (rule F, variant (a)).
- **Seasons**: a species is absent in season S if it carries NO_S (real raw flags). In practice only NO_WINTER matters
  (NO_SPRING 1 species, NO_AUTUMN 2, NO_SUMMER none).

## 1. Layers and candidate pools

Embark biome sets (surface):

| key | biomes |
|---|---|
| TEMP_GRASS_FOREST | GRASSLAND_TEMPERATE, FOREST_TEMPERATE_BROADLEAF, FOREST_TEMPERATE_CONIFER |
| TROP_SAVANNA_SHRUB | SAVANNA_TROPICAL, SHRUBLAND_TROPICAL |
| TAIGA_TUNDRA | FOREST_TAIGA, TUNDRA |
| DESERT | DESERT_SAND, DESERT_ROCK, DESERT_BADLAND |
| TROP_WETLAND | SWAMP_TROPICAL_FRESHWATER, MARSH_TROPICAL_FRESHWATER, POOL_TROPICAL_FRESHWATER |
| LAKE_RIVER | GRASSLAND_TEMPERATE, FOREST_TEMPERATE_BROADLEAF, LAKE_TEMPERATE_FRESHWATER, RIVER_TEMPERATE_FRESHWATER |
| OCEAN_SHORE | GRASSLAND_TEMPERATE, SHRUBLAND_TEMPERATE, OCEAN_TEMPERATE |

A species is a candidate if its expanded BIOME tokens (ANY_*, NOT_FREEZING … expanded as DF does) meet the set.

- **Surface land**: LARGE_ROAMING, not FLIER, not AQUATIC, with a non-water biome in the set. Non-flying, non-fish
  vermin with a land biome also count.
- **Surface flying**: LARGE_ROAMING FLIER (any matching biome), plus FLIER vermin.
- **Surface water** (the brief's "river"): LARGE_ROAMING AQUATIC with a lake/river/ocean biome in the set, or AMPHIBIOUS
  with such a biome or a matching wetland biome. Also fish/aquatic vermin, or vermin whose only matching biome is water.
  - Pools are excluded for LARGE_ROAMING (wiki: LARGE_ROAMING "cannot spawn in Pool biomes"); vermin may use pools.
  - The ocean fort's water layer is the sea. The four forts with no water biome have an **empty** water layer (320
    empty rosters of 560).
  - AMPHIBIOUS species can be in both land and water.
- **Caverns** cav1/cav2/cav3: a SUBTERRANEAN_CHASM or SUBTERRANEAN_WATER biome, and a BIZARRE band. The band is combined
  with DF's own depth by `Cfg.cav`:
  - `depth`: DF's UNDERGROUND_DEPTH range covers the layer.
  - `score`: the BIZARRE tertile band equals the layer number (depth ignored).
  - `depth+ceiling` (**default**): the depth range covers the layer **and** band ≤ layer. cav1 takes only band 1,
    cav2 bands 1-2, cav3 anything.
- **Deep** (magma sea): SUBTERRANEAN_LAVA, or a depth range that includes 4. Only IMP_FIRE and MAGMA_CRAB are natural.
- **Seasons** filter every pool. Caverns and deep carry no NO_* flags, so their pools are season-invariant.

## 2. Trophic classes

Non-vermin predators (role = predator):

| class | `cls=size` (default, the tool's bands) | `cls=tag+size` | `cls=lp+1` (used by FIX) |
|---|---|---|---|
| giant_pred | giant | giant | giant |
| large_pred | band large | band large **or LP** | band large, or LP of band medium |
| medium_pred | band medium | band medium, not LP | band medium non-LP, or LP of band small |
| small_pred | band small | band small, not LP | band small, not LP |

Non-vermin prey (role = prey):
- giant_large_prey = giant or band large;
- medium_prey = band medium;
- small_prey = band small.

Vermin:
- v_colony = VERMIN_SOIL_COLONY (ants, termites, bees; colony wins over flying).
- v_flybird = FLIER vermin with ≤2 stance parts or class MAMMAL (songbirds, bats, cave swallow).
- v_flyother = other FLIER vermin (insects).
- v_ground_fish = everything else (ground vermin and fish vermin share the brief's "ground/fish vermin 1-3" slot).

Caps (step 0, per layer):
- giant_pred 1, large_pred 1, medium_pred 1, small_pred 1;
- giant_large_prey 1, medium_prey 1, small_prey 2;
- v_ground_fish 3 (min 1), v_colony 1 (min 0), v_flybird 1, v_flyother 1.

"Strict caps reached" means every class is at its max. "Lenient" means every class is at its min.

## 3. The eats(P, X) model: rules A-F

Layer, season and co-presence come from the pool. Shared biome is **not** required for an edge; it is a selection
preference only (see step 2).

| # | rule | operational form |
|---|---|---|
| — | eaters | Non-vermin in a *_pred class, or a v_flybird (rule C). Nothing else eats. No self-predation. |
| C | vermin layer | v_flybird eats v_flyother, and nothing else. No other vermin eats. |
| A | predators as prey | Giant predators are never prey: the brief names only "non-giant predators" as edible, so nobody may eat a giant predator. A non-giant **PREDATOR** target may be eaten only by a giant predator or a PREDATOR. PREDATOR is read two ways (the same reading for eater and target): **A(i) `A=lp`** is the LARGE_PREDATOR tag (default); **A(ii) `A=role`** is the tool's role = predator. |
| D | sentients | A sentient target may be eaten only by a giant predator or a "large predator". The three readings: **`tag_and_size`** is LP and band large (default); **`tag`** is LP; **`size`** is band large and role predator. |
| B | small predators | A small_pred eats vermin only (size category 0). |
| E | medium/large | medium_pred eats small..medium prey (categories 1-2). large_pred and giant_pred eat small..medium ("medium to small" as written, `E_large_max=2`). Neither eats vermin. Giants use the large row because the brief gives giants no size rule. |
| F | packs | +1 to the top size category an eater may take. The variants: **(a) `F=cluster`** is cluster max > 1 (default); **(b) `F=lp_cluster`** is LP and cluster max > 1; `F=none` removes the bonus. So a pack small_pred eats vermin + small prey, and a pack medium/large pred eats up to large. |

Size category of a prey: vermin 0, small 1, medium 2, large 3, from the tool's band. A giant's category comes from its
own band: most giants are ~200k, i.e. medium.

## 4. Algorithm (steps 1-8) as implemented

1. **Step 1: seed.** Draw one non-vermin **high-value (HV)** species from the pool at random (`uniform`, or `frequency` =
   weighted by DF FREQUENCY). HV means any one of:
   - PETVALUE ≥ 200;
   - TRAINABLE or TRAINABLE_WAR (war value);
   - animal-parts proxy: mass ≥ 1,000,000, or an IVORY/PEARL/SILK material template.

   **Every one of the 178 giants carries PETVALUE 500, so every giant is HV.** `hv_mode=nogiant` removes giants from the
   HV set. If the pool has no HV species, draw any non-vermin (recorded as `no_hv_fallback`).
2. **Step 2.** If the seed is an eater, add one of its prey. Otherwise add one of its eaters. Only species with cap room
   are candidates. Selection weights:
   - shared biome: candidates that share a biome with the seed inside the embark set are used if any exist;
   - relative size: lognormal on the prey/predator mass ratio, centred at 0.4x (the tool's preference), sd 1.5 in ln;
   - shared layer and season are guaranteed by the pool.
3. **Step 3.** For every species already in the roster, add one **non-HV** eater and one **non-HV** prey (same weighting).
   `hv_fallback` allows HV candidates when no non-HV one exists.
4. **Step 4.** Repeat step 3 until the strict caps are reached. A **no-progress guard** stops the loop when a full pass adds
   nothing, plus a hard limit of 50 passes, which was never hit. Recorded: `caps_strict`, `caps_lenient` and `no_progress`,
   plus whether every unfilled class had zero pool candidates ("caps filled wherever the pool allowed").
5. **Step 5.** Add every ordered pair in the roster that eats() allows ("edges step5"). The steps 2-4 edges are "tree
   edges".
6. **Step 6.** For each node with no edge after step 5, look for a pool species with cap room that has an allowed
   relation both to the isolated node and to the largest component, and add it. Outcomes recorded:
   - `bridged_within_caps`;
   - `bridge_needs_cap_break`;
   - `impossible_under_A-F`;
   - `no_relation_in_pool` (the isolated species has no allowed relation with *any* pool species).

   Step 5 already adds every allowed relation, so an isolated node can only be joined through a new species.
7. **Step 7: frequency weight by class.**

   | class | weight |
   |---|---|
   | giant_pred | 1 |
   | large_pred | 3 |
   | giant_large_prey | 4 |
   | medium_pred | 5 |
   | medium_prey | 6 |
   | small_pred | 7 |
   | small_prey | 8 |
   | v_ground_fish | 9 |
   | v_colony | 9 |
   | v_flybird, v_flyother | 10 |

   The brief lists 8 numbers for 9 classes, so flying vermin get 10 (extrapolated) and colony vermin share 9 with
   ground/fish vermin.
8. **Step 8.** Pass if:
   - at least one pack predator (cluster max > 1, a *_pred class) has at least one prey edge; and
   - at least one herd prey (cluster max > 1, a *_prey class) has at least one eater edge.

   It is also scored on unit-only edges and on DF-actable edges only.

**DF-actable edge**: the eater is a non-vermin unit that is **not BENIGN**, and the target is a non-vermin unit. This
follows the measured facts:
- only non-BENIGN attackers act on a written relation (P1, T1);
- vermin are not units;
- no attack happens without a written relation.

"Fight-back prey" = the target is not BENIGN (P1: a water buffalo killed a lion; T1: BENIGN-off deer killed wolves).

## 5. BIZARRE score (caverns): see bizarre.py / bizarre.tsv

Integer points, raw facts only:

| component | points |
|---|---|
| no MUNDANE | 2 (MUNDANE = "actual real-life creature") |
| no MAMMAL class | 1 |
| stance parts ∉ {2, 4} (legless, 6/8-legged, tentacles) | 1 |
| no HEAD part | 2 |
| more than 1 HEAD part | 2 |
| no SIGHT part | 1 |
| SYNDROME / EXTRACT / SPECIALATTACK_INJECT_EXTRACT / any CE_ effect | 1 |
| each of NOBREATHE, NOT_LIVING, NO_EAT, NO_DRINK, NO_SLEEP, NOPAIN, NOEMOTION, NOTHOUGHT, NOFEAR, FIREIMMUNE | 1 each, cap 3 |
| WEBBER / THICKWEB | 1 |
| adult ≥ 1,000,000 cm3 | 1 |

Bands are tertiles of the 48 natural cavern species: band 1 ≤ 3, band 2 = 4, band 3 ≥ 5.

## 6. Fix knobs (tested, see results.md)

| knob | meaning |
|---|---|
| `cls=lp+1` | LP moves a predator up one class (small→medium, medium→large). |
| `E_large_max=3` | large/giant predators may eat large prey. |
| `B_small_extra=1` | small predators eat vermin + small prey. |
| `D=tag` | any LP may eat sentients. |
| `weight=frequency` | picks are weighted by DF FREQUENCY. |
| `hv_mode=nogiant` | giants are not "high value". |
| `hv_fallback` | step 3 may add an HV species when no non-HV candidate exists. |
| `benign_filter` | BENIGN predators are re-classed as prey; they never get a predator slot. |
| `seed_linked` | step 1 draws only species that have at least one relation in the pool. |
| `sentient_pred=False` | sentients are never eaters. |
| `peer` | a predator may eat another predator only if it has ≥ 2x its mass (the tool's own eats() peer rule). |
| `size=ratio` | replaces the B/E/F band windows for unit prey with the tool's eats() mass test: take = mass × group^0.75 × (1.5 if LP) ≥ need = prey mass × (0.9 herd / 0.6 solo). |
