# Apex review (user questions, 12 Oct) — desk only

Sources: DF 53.16 vanilla raws as castsim reads them (`scripts/castsim/raws.py:22`), every creature classified through `engine.py` (967 tokens; inventory `scratchpad/inv.json`); rules in `scripts/castsim/design.py` and `engine_tables.json`; audit `data/castsim/apex_audit.json`; casts `data/castsim/design.json` (both regenerated 12 Oct 10:31, b9783340). No engine, rig or report changes.

How a species can hold an apex slot (`design.py:332-358`):
- **Ground:** guild AL/AW (LARGE_PREDATOR, `engine.py:138-140`), or a "boosted" predator (≥1,000,000 cm³, or any giant of a predator: `engine.py:227-230`), or REAL_APEX (`design.py:80-93`), or hand-wired.
- **Flying:** guild RP (a flier with a meat diet), not sentient, not a scavenger (FLY_SCAV: vulture, buzzard, kea, raven), and ≥2,000 cm³ (`engine.py:232-235`, `roster.fly_apex_min`); or REAL_APEX (peregrine).
- **Ocean and fresh:** only the curated `roster.aquatic_apex` table (or its giants and animal people), REAL_APEX, or wiring (`design.py:351-356`).

---

## Q1. Land-flying apexes. Is that all? And the harpy?

**Answer: yes for calm regions.** The raws have exactly 12 surface birds of prey (non-giant, not animal people), and the five you listed are the only ones that qualify. The harpy *is* in the casts. It is missing only from the audit's apex list, because of a bug in `apex_audit.py`. The sims were rerun after the evil wiring (09:42 wiring, 10:31 rerun).

| token | cm³ | biomes (raw) | why in / out |
|---|---|---|---|
| BIRD_EAGLE | 4,000 | ANY_DESERT/FOREST/GRASSLAND/SAVANNA/SHRUBLAND/WETLAND, MOUNTAIN, TUNDRA | in |
| BIRD_OSPREY | 2,000 | lakes, oceans, rivers, marshes | in |
| BIRD_OWL_GREAT_HORNED | 2,000 | deserts, forests, grass, savanna, shrub, mountain, mangrove, tundra | in |
| BIRD_OWL_SNOWY | 2,000 | TUNDRA | in |
| BIRD_FALCON_PEREGRINE | 1,100 | almost everything | in, via REAL_APEX (under the floor) |
| BIRD_VULTURE | 9,000 | deserts, tropical grass/savanna | out: FLY_SCAV (scavenger) |
| BIRD_BUZZARD | 1,400 | deserts, temperate grass/marsh/savanna | out: FLY_SCAV, under 2,000 |
| BIRD_KEA | 1,000 | temperate forest, mountain, shrub | out: FLY_SCAV |
| BIRD_OWL_BARN | 500 | wide | out: under 2,000 (correctly a mesopredator) |
| BIRD_KESTREL | 250 | open land | out: under 2,000 |
| HARPY | 60,000 | temperate and tropical grass, savanna, shrub, marsh | EVIL; out by the sentience rule (`engine.py:233`), back in by EVIL_APEX wiring (`design.py:119`) |
| NIGHTWING | 120,000 | ANY_DESERT | EVIL, LARGE_PREDATOR, sentient; eco "unliving" (NO_EAT+NO_DRINK), so filtered out; **not wired** |

The raws have no hawks, kites, condors or other eagles. The only larger raptors are the giant variants of these birds, which are SAVAGE and appear only on savage regions, and the extinct pterosaurs (Quetzalcoatlus, Sinopterus, Rhamphorhynchus: savage only).

**The harpy:**
- The casts include it. In `design.json` the evil synthetic embark's flying casts draw HARPY as apex in Winter (89%) and Spring (13%).
- The report's "Every true apex in DF's raws, by region type" table and the audit rows omit it because of a stale-state bug. `apex_audit.py` calls `D.pool()` for every biome and region type, then computes the roll (`apex_audit.py:123-130`) and each row's tiers (`apex_audit.py:83`) *after* that loop. `Design.promoted` (`design.py:276-277`) then holds only the wiring of the last embark pooled (savage-evil tropical river → `{('fresh','GRIMELING')}`).
- So GRIMELING shows as an evil fresh apex everywhere, and HARPY never shows as an evil flying apex. I reproduced this: after the last pool `promoted == {('fresh','GRIMELING')}`; after pooling an evil grassland, HARPY's tier is 'apex'.
- Effect: the evil flying rows in the audit undercount by one (and savage-evil flying too); the casts are unaffected.
- **Fix (sim only):** compute each row's tiers right after that row's `D.pool(spec)`, and build the roll from those per-row tiers. Rerun the audit and report.

**Optional addition (your call):** wire NIGHTWING as the evil *desert* flying apex, as the grimeling was let through the natural filter. Today the harpy covers grass, savanna, shrub and marsh but not deserts, so an evil desert gets no evil flier.

---

## Q2. Freshwater apexes. Is that all?

**Answer: almost.** The water apex slot is limited by design to the curated `aquatic_apex` table plus REAL_APEX. That table's non-savage freshwater members are ALLIGATOR and CROCODILE_SALTWATER, both rivers and marshes only (no LAKE tag in their raws), so they reach lakes only by wiring. That is why the saltwater crocodile was "added in": the audit's proposal wired it into tropical lakes. The raws do hold two more real candidates.

| token | cm³ | fresh biomes (raw) | status | real-world | recommendation |
|---|---|---|---|---|---|
| FISH_PIKE | 35,000 | temperate lake, river | REAL_APEX apex | top of northern lakes | keep |
| ALLIGATOR | 400,000 | temperate and tropical river, marsh, swamp | aquatic_apex | apex | keep; already wired to lakes |
| CROCODILE_SALTWATER | 800,000 | tropical river, marsh, swamp, mangrove | aquatic_apex | apex | keep; wired to tropical lakes |
| ALLIGATOR SNAPPING TURTLE | 80,000 | temperate lake, pool, river | REAL_APEX local | ambush apex | keep |
| FISH_GAR_LONGNOSE | 20,000 | temperate lake, river | REAL_APEX local | top of warm rivers | keep |
| **FISH_TIGERFISH** | 50,000 | **tropical lake, river** | REAL_CARNIVORE only (meso) | goliath tigerfish, apex of African rivers and lakes | **add REAL_APEX ('fresh','apex')**: the first native tropical-lake apex (today the tropical lake has 0 true apexes before wiring) |
| **ANACONDA** | 100,000 | ANY_TROPICAL_WETLAND (land layer) | ground apex (AL); never fresh | the anaconda is the apex of Amazon rivers and lakes | **wire to tropical lakes and rivers (fresh)** |
| SNAPPING TURTLE | 30,000 | temperate lake, pool, river | meso | mesopredator | optional REAL_APEX 'local' |
| FISH_LAMPREY_SEA | 20,000 | temperate lake, river, ocean | AW, LARGE_PREDATOR, kept meso (R49) | a parasite, not an apex | keep meso |
| HIPPO | 1,500,000 | tropical lake, river | shore herbivore | dominant, not a predator | no |
| FISH_STURGEON | 1,500,000 | temperate river, ocean | prey | bottom feeder | no |

Savage-only freshwater: CENOZOIC_TITANOBOA (aquatic_apex), SILURIAN_JAEKELOPTERUS, the spinosaurs (tropical rivers), and giant alligator and crocodile. The raws have no caiman, gharial, Nile crocodile, catfish, muskellunge or piranha.

---

## Q3. DINGO far too often; monitor lizard, tiger, cougar, python ranges

**Why DINGO dominates (numbers):**
- **Its range:** its raw biome is `[BIOME:NOT_FREEZING]`, which puts it in 23 of the 27 land biomes. Every other ground apex has 1–14.
- **Only apex in 8 biomes:** it is the sole true ground apex of 6 of them: temperate swamp ×2, temperate marsh ×2, temperate grassland and temperate savanna. It is drawn there 100% of the time. Temperate shrubland and both temperate forests add the wolf (and bears or cougar), and the four freezing biomes (glacier, tundra, taiga, mountain) do not list it.
- **The pack counts twice:** its pack (CLUSTER 3–12) enters the draw both as group size (20,000 cm³ × mean 7.5 = 150,000; `design.py:488-491`) and again as ×3 for a pack hunter (`design.py:440`, `CAST_DEF.pack = 3`). A 20 kg dog thus outweighs a solitary jaguar (75,000) or leopard (50,000) by about 3×√2.
- **First-draw share:** averaged equally over the 27 land biomes (wild, neutral, before wiring), DINGO takes 52% of the ground apex draws. Next come WOLF 10%, JAGUAR 6%, LEOPARD 5% and TIGER 4%.
- **The real forts:** in the three region19 forts, 7 of the 12 ground apex casts are DINGO and the other 5 are COYOTE (`design.json`). Once the dingo is drawn, its reuse weight (×0.01) leaves the promoted or local coyote as the only alternative.

**Your range points, checked against the raws:**
- **MONITOR_LIZARD:** `ANY_TROPICAL_FOREST, GRASSLAND/SAVANNA/SHRUBLAND_TROPICAL`, with no desert. Confirmed; it needs the deserts.
- **TIGER:** `ANY_TROPICAL_FOREST, SHRUBLAND_TROPICAL, SWAMP_MANGROVE, SWAMP_TROPICAL_*`, with no grassland and nothing temperate. Confirmed.
- **COUGAR:** `ANY_TEMPERATE_FOREST, ANY_TROPICAL_FOREST, SHRUBLAND_*`, with no MOUNTAIN. Confirmed. MOUNTAIN has **no true ground apex at all** today (only the local coyote and wolverine).
- **PYTHON:** `FOREST_TROPICAL_MOIST_BROADLEAF` only (1 biome). Confirmed.

**What each change does to the first-draw share** (same averaging; `scratchpad/q3b.txt`):

| variant | DINGO | others |
|---|---|---|
| A. as now | 52% | WOLF 10, JAGUAR 6, LEOPARD 5, TIGER 4 |
| B. drop the ×3 in the apex draw only (the pack is already in group size) | 40% | JAGUAR 10, LEOPARD 8, TIGER 6 |
| C. keep the dingo to arid, open and dry biomes (deserts, grass, savanna, shrub, dry tropical and temperate broadleaf forest) | 26% | WOLF 12, JAGUAR 11 (4 temperate wetlands lose their only apex) |
| D. the biome additions below | 35% | LION 10, HYENA 10, WOLF 8, COUGAR 7 |
| C+D (keep ×3) | 10% | COUGAR, LION, HYENA 11 each; WOLF 10; TIGER 9; PYTHON 8 |
| B+C+D | 7% | COUGAR 13, TIGER 12, PYTHON/LION/HYENA/JAGUAR 8 |

**Recommendation:** C + D. The temperate wetlands then need their own apex: BEAR_BLACK and WOLF (black bears and red wolves of the southern swamps), and COUGAR (the Florida panther; already in D). B is a separate weighting question you may prefer to keep, since pack hunters drawing more often was your x3 rule.

---

## Q4. Apex predators stuck in tropical-only biomes

**Context:**
- **How rare tropical biomes are:** tropical tiles are 18–28% of the land in the surveyed worlds (region19 23%, region10 24%, region11 28%, region6 18%).
- **Subtypes are rarer still:** in region19 tropical grassland is 59 of 3,435 land tiles (1.7%), and tropical savanna is 146 (4%).
- **Effect:** LION, HYENA and CHEETAH live *only* in tropical grassland, savanna and shrubland, so most forts never see them.

Non-savage, natural, tropical-only predators in the raws, with a recommended addition:

| token | cm³ (group) | raw biomes | add (realistic ecotype) |
|---|---|---|---|
| LION | 200,000 (pack 1–3) | GRASSLAND/SAVANNA/SHRUBLAND_TROPICAL | GRASSLAND/SAVANNA/SHRUBLAND_TEMPERATE, DESERT_BADLAND, DESERT_SAND (cave lions and Asiatic lions; desert lions of the Namib) |
| TIGER | 225,000 | ANY_TROPICAL_FOREST, SHRUBLAND_TROPICAL, tropical swamps, mangrove | GRASSLAND/SAVANNA_TROPICAL (terai), FOREST_TAIGA, FOREST_TEMPERATE_BROADLEAF/CONIFER (Siberian/Amur), GRASSLAND_TEMPERATE |
| HYENA | 60,000 (pack 5–15) | GRASSLAND/SAVANNA/SHRUBLAND_TROPICAL | DESERT_BADLAND/ROCK/SAND (striped hyena), SAVANNA_TEMPERATE |
| CHEETAH | 50,000 | GRASSLAND/SAVANNA/SHRUBLAND_TROPICAL | DESERT_SAND/ROCK (Saharan, Asiatic), SAVANNA_TEMPERATE |
| PYTHON | 200,000 | FOREST_TROPICAL_MOIST_BROADLEAF | SWAMP_TROPICAL_*, SWAMP_MANGROVE, MARSH_TROPICAL_*, FOREST_TROPICAL_DRY_BROADLEAF, GRASSLAND/SAVANNA_TROPICAL (Burmese and rock pythons) |
| MONITOR_LIZARD | 100,000 | tropical forest, grass, savanna, shrub | DESERT_BADLAND/ROCK/SAND (desert monitors, perentie), SWAMP_MANGROVE, MARSH_TROPICAL_FRESHWATER (water monitor) |
| ANACONDA | 100,000 | ANY_TROPICAL_WETLAND | the freshwater layer (Q2); land range is fine |
| STRANGLER (EVIL) | 40,000 (1–3) | FOREST_TROPICAL_MOIST_BROADLEAF | evil only: ANY_TROPICAL_FOREST, ANY_TEMPERATE_FOREST (see Q5) |
| CROCODILE_SALTWATER | 800,000 | tropical rivers, marsh, swamp, mangrove | leave (truly tropical); already wired to tropical lakes |
| JAGUAR, LEOPARD | 75,000 / 50,000 | ANY_TROPICAL + deserts | fine as is. Optional: LEOPARD to MOUNTAIN (snow and Persian leopards), JAGUAR to SWAMP/MARSH_TEMPERATE (historic US range) |
| meso: OCELOT, JACKAL, BLACK_MAMBA, KING_COBRA, BUSHMASTER, IGUANA, MONGOOSE | 25,000–3,000 | tropical only | not apexes. JACKAL → DESERT_* (golden jackal) is the only clear case |

Also: COUGAR → MOUNTAIN, DESERT_BADLAND/ROCK, GRASSLAND_TEMPERATE and SWAMP_TEMPERATE_FRESHWATER. This gives MOUNTAIN its first true apex.

**How to do it:** two routes.

1. **Tool-side (recommended):** add a species → extra biomes table, read by the pool builder in the sim and the engine. It works like the approved wiring, where a wired species is "treated as living in the biome" (`design.py:201-214, 276-288`). The v7.5 engine already creates population entries for cast species DF has not stocked, so DF itself draws them on the fort.
   - Works on existing worlds.
   - Scoped to forts running the tool.
   - Reversible; the `off` command removes the created entries.
   - Inherits the extinct, savage and alignment gates.
   - Cost: the audit and roll must read the table, and the giants follow their roots automatically via the root-token lookup in `apex_tier`.
2. **Raws edit in the mod:** add `[BIOME:…]` to the creature raws.
   - DF uses biome tags at worldgen to stock region populations, so only newly generated worlds would change; whether existing worlds restock is unverified.
   - Every DF system that reads biomes changes with it: adventure mode, civs, DF's own wave draws.
   - Per memory (mod-raws-reload-at-load), installed mod creature raws are re-read at load only with a version bump, and an older mod copy keeps its own info.txt.
   - Heavier, global and harder to undo. Use it only if you want DF's own worldgen to change.

**Your decision:** approve the additions table (or edit it), and choose route 1 or 2.

---

## Q5. Evil land-ground apex novelty

**Answer:** the raws' EVIL roster is small. Every EVIL surface creature:

| token | cm³ (group) | biomes | flags | evil ground apex today? |
|---|---|---|---|---|
| OGRE | 6,000,000 (1–3) | temperate and tropical grass, savanna, shrub | EVIL, LARGE_PREDATOR, sentient | yes |
| BLIZZARD_MAN | 300,000 | GLACIER, TUNDRA | EVIL, LARGE_PREDATOR, sentient | yes (cold only) |
| BEAK_DOG | 150,000 (3–7) | temperate and tropical marsh only | EVIL, LARGE_PREDATOR | yes (marsh only) |
| BLENDEC_FOUL | 60,000 (3–5) | FOREST_TEMPERATE_BROADLEAF, FOREST_TROPICAL_CONIFER, FOREST_TROPICAL_DRY_BROADLEAF | EVIL, LARGE_PREDATOR, sentient | yes |
| WOLF_ICE | 50,000 (3–7) | GLACIER, TUNDRA | EVIL, LARGE_PREDATOR | yes (cold only) |
| STRANGLER | 40,000 (1–3) | FOREST_TROPICAL_MOIST_BROADLEAF | EVIL, LARGE_PREDATOR | yes (one rare biome) |
| NIGHTWING | 120,000 | ANY_DESERT | EVIL, LARGE_PREDATOR, flier, sentient, NO_EAT+NO_DRINK | no: filtered as unliving (a flying candidate, Q1) |
| GRIMELING | 70,000 | marsh, swamp, mangrove | EVIL, LARGE_PREDATOR, amphibious | wired to evil freshwater |
| HARPY | 60,000 | grass, savanna, shrub, marsh | EVIL, LARGE_PREDATOR, flier | wired to evil flying |
| GNOME_DARK, WORM_KNUCKLE, RAT_DEMON, SPIDER_PHANTOM | ≤15,000 | various | EVIL, prey or vermin | no |

BLENDEC_FOUL looks like the only novelty because the others sit in narrow biomes. Beak dogs need a marsh, the strangler a tropical moist forest, and the blizzard man and ice wolf ice or tundra. The ogre's grass/savanna/shrub is shared with the common lions and dingoes.

**Giant bugs:** the GIANT variation makes every giant SAVAGE (`raws.py:5`), and none is EVIL. They are therefore already true ground apexes on *savage* regions, including terrifying ones (savage + evil), through the giant boost (`engine.py:227-230`). The audit roll for savage-evil ground lists GIANT_BARK_SCORPION, GIANT_BROWN_RECLUSE_SPIDER and GIANT_JUMPING_SPIDER. On a *calm* evil region DF itself never spawns giants.

| token | cm³ | biomes | role |
|---|---|---|---|
| GIANT_JUMPING_SPIDER | 200,007 | NOT_FREEZING | ML predator → apex on savage |
| GIANT_BARK_SCORPION | 200,021 | ANY_DESERT, FOREST_TROPICAL_CONIFER, tropical grass, savanna, shrub | ML predator → apex on savage |
| GIANT_BROWN_RECLUSE_SPIDER | 200,007 | FOREST_TEMPERATE_BROADLEAF | ML predator → apex on savage |
| GIANT_MANTIS | 200,007 | NOT_FREEZING | read as prey (the raw has no CARNIVORE). A REAL_CARNIVORE entry would make it a predator and a savage apex |
| SPIDER_CAVE_GIANT (cavern) | 200,000 (AL, SAVAGE) | SUBTERRANEAN_CHASM | a wiring candidate for evil surface forests (webs at the surface) |

**Recommendations, each your call:**
- **(a) Widen the evil species' own ranges tool-side, on evil regions only:**
  - BEAK_DOG → every wetland (swamps, mangrove).
  - STRANGLER → ANY_TROPICAL_FOREST + ANY_TEMPERATE_FOREST.
  - BLENDEC_FOUL → every forest (taiga included).
  - OGRE → MOUNTAIN, deserts.
- **(b) NIGHTWING as the evil desert flier** (let through the natural filter, like the grimeling).
- **(c) Giant bugs on calm evil regions** means overriding DF's own SAVAGE gate for giants. That is the larger rule change, so I'd keep giants savage-only and rely on (a) and (b). Alternatively, wire GIANT_JUMPING_SPIDER, GIANT_BARK_SCORPION and SPIDER_CAVE_GIANT into evil regions only as an explicit exception.
- **(d) GIANT_MANTIS** → REAL_CARNIVORE (it then joins the savage apex pool).

---

## Decision points for you
1. **The harpy:** fix the audit's stale-state bug (sim only) and rerun the audit and report. **Recommend: yes.**
2. **New freshwater apexes:** FISH_TIGERFISH as a fresh apex (tropical); ANACONDA wired to tropical lakes and rivers; SNAPPING TURTLE as a local apex?
3. **Dingo:** narrow its range (C) and/or drop the double pack count in the apex draw (B)? **Recommend C; B is your call.**
4. **Biome additions** for LION, TIGER, HYENA, CHEETAH, PYTHON, MONITOR_LIZARD, COUGAR (+MOUNTAIN), and optionally LEOPARD and JAGUAR, plus BEAR_BLACK and WOLF for the temperate wetlands: approve the table, and choose tool-side (recommended) or raws.
5. **Evil:** widen the evil species' ranges (a), add NIGHTWING (b), giant bugs savage-only or an evil exception (c), GIANT_MANTIS as a predator (d).
