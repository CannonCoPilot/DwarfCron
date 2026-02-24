"""Annotated CDM schema for the agentic storyteller.

This module contains the database knowledge that an LLM needs to autonomously
generate SQL queries against the Chronicler CDM (Common Data Model). It is
injected into the storyteller system prompt so the LLM can retrieve its own
context rather than relying on hardcoded keyword routing.

Design goals:
  - Concise: fits in ~3000 tokens alongside the narrative persona prompt
  - Complete: covers all 33 tables, FKs, common query patterns, enum values
  - Safe: documents read-only constraints and parameterization requirements
"""

ANNOTATED_SCHEMA = """\
## Chronicler CDM — Database Schema Reference

You have read-only access to a PostgreSQL database containing Dwarf Fortress \
world history (legends XML) and live fortress data (DFHack bridge). All queries \
MUST use parameterized values ($1, $2, ...) for user-supplied inputs. Never \
interpolate strings directly. Always include `world_id = $1` in WHERE clauses.

### Composite Primary Keys

Most tables use `(world_id, id)` as the primary key. When joining, always match \
on BOTH columns: `ON a.world_id = b.world_id AND a.id = b.some_id`.

---

### Core Tables

**worlds** — One row per imported world (usually 1).
  `id SERIAL PK, name TEXT, alt_name TEXT, imported_at TIMESTAMPTZ`

**historical_figures** — Every named person, creature, deity, or spirit (~35K rows).
  `id INT, world_id INT` (PK: world_id, id)
  `name TEXT, race TEXT, caste TEXT, sex SMALLINT` (0=female, 1=male)
  `birth_year INT, death_year INT` (NULL or -1 = alive/unknown)
  `death_cause TEXT` — e.g. "old age", "struck down", "murdered"
  `entity_id INT` — primary civilization FK (→ entities.id)
  `is_deity BOOL, is_force BOOL, is_vampire BOOL, is_necromancer BOOL, \
is_werebeast BOOL, is_ghost BOOL`
  `kill_count INT, event_count INT` — precomputed aggregates
  `importance_score FLOAT` — 0-1000+, higher = more narratively significant
  `details JSONB` — overflow fields (spheres, goals, journey_pets, etc.)
  Common races: HUMAN, GOBLIN, ELF, DWARF, KOBOLD, FORGOTTEN_BEAST*, TITAN*, \
DRAGON, GIANT_*

**entities** — Civilizations, religions, guilds, military units (~3.7K rows).
  `id INT, world_id INT` (PK: world_id, id)
  `name TEXT, type TEXT, race TEXT, details JSONB`
  Types: civilization, religion, sitegovernment, nomadicgroup, guild, outcast, \
performancetroupe, migratinggroup, militaryunit, merchantcompany

**sites** — Named locations on the world map (~2K rows).
  `id INT, world_id INT` (PK: world_id, id)
  `name TEXT, type TEXT, coord_x INT, coord_y INT, coords TEXT`
  `owner_entity_id INT` — current owner (→ entities.id)
  `importance_score FLOAT, details JSONB`
  Types: cave, hamlet, forest retreat, lair, dark pits, monastery, camp, \
hillocks, mountain halls, fortress, fort, dark fortress, town, tower, tomb, \
castle, shrine, labyrinth, vault

**artifacts** — Named objects of significance (~6K rows).
  `id INT, world_id INT` (PK: world_id, id)
  `name TEXT, item_type TEXT, item_subtype TEXT, material TEXT`
  `creator_hf_id INT` (→ historical_figures.id)
  `holder_hf_id INT` (→ historical_figures.id, NULL if stored/lost)
  `site_id INT, importance_score FLOAT, details JSONB`

---

### Relationship Tables (Join Tables)

**hf_links** — HF-to-HF relationships (~208K rows).
  `hf_id INT, target_hf_id INT, link_type TEXT`
  UNIQUE(world_id, hf_id, target_hf_id, link_type)
  link_type values: "mother", "father", "child", "spouse", "former spouse", \
"deity", "master", "apprentice", "companion"

**hf_entity_links** — HF membership in entities (~135K rows).
  `hf_id INT, entity_id INT, link_type TEXT, position_name TEXT`
  link_type values: "member", "former member", "position", "former position", \
"enemy", "prisoner", "slave"

**hf_site_links** — HF connections to sites (~1.6K rows).
  `hf_id INT, site_id INT, link_type TEXT`
  link_type values: "home site", "seat of power", "lair", "home structure"

**hf_position_links** — Political/military positions held (~15K rows).
  `hf_id INT, entity_id INT, position_id INT, start_year INT, end_year INT`
  end_year IS NULL = currently held. Join with entity_positions for title names.

**entity_positions** — Position definitions per entity (~7.6K rows).
  `entity_id INT, position_id INT, name TEXT, name_male TEXT, name_female TEXT`
  `spouse TEXT, spouse_male TEXT, spouse_female TEXT`

---

### Event Tables

**history_events** — Individual historical events (~313K rows).
  `id INT, world_id INT` (PK: world_id, id)
  `year INT, seconds INT, event_type TEXT`
  `hf_id_1 INT, hf_id_2 INT` — primary and secondary figures
  `site_id INT, region_id INT, entity_id_1 INT, entity_id_2 INT`
  `artifact_id INT, structure_id INT`
  `details JSONB` — overflow fields specific to event type
  Top event types by frequency:
    change hf state (53K), change hf job (50K), add hf entity link (34K), \
written content composed (27K), hf died (21K), add hf hf link (19K), \
hf simple battle event (17K), performance (7K), artifact created (6K), \
creature devoured (5K), hf abducted (3K), hf wounded (3K)

**history_event_collections** — Grouped events: wars, battles, sieges (~29K rows).
  `id INT, world_id INT` (PK: world_id, id)
  `type TEXT, name TEXT, parent_id INT`
  `start_year INT, end_year INT`
  `attacker_entity_id INT, defender_entity_id INT` (→ entities.id)
  `site_id INT, region_id INT, details JSONB`
  Types: war, battle, site conquered, beast attack, duel, abduction, theft, \
persecution, purge, entity overthrown, occasion, ceremony, performance, \
competition, procession, journey

**collection_events** — Maps events to collections (M:N, ~71K rows).
  `collection_id INT, event_id INT` (PK: world_id, collection_id, event_id)

**collection_subcollections** — Nested collections (~18K rows).
  `parent_id INT, child_id INT` (PK: world_id, parent_id, child_id)
  Example: a war contains battles, which contain individual combat events.

**event_relationships** — Extracted relationship changes from events (~82K rows).
  `event_id INT, relationship TEXT, source_hf INT, target_hf INT, year INT`

---

### Geography

**regions** — Named biome regions (~2.6K rows).
  `id INT, world_id INT, name TEXT, type TEXT, coords TEXT`

**underground_regions** — Cavern layers (~1.4K rows).
  `id INT, world_id INT, type TEXT, depth INT, coords TEXT`

**structures** — Buildings within sites (~1.4K rows).
  `id INT, world_id INT, site_id INT, name TEXT, type TEXT, entity_id INT`
  PK: (world_id, site_id, id)

**landmasses**, **mountain_peaks**, **world_constructions** — Geography features.

---

### Written Content & Cultural

**written_contents** — Books, poems, musical compositions (~27K rows).
  `id INT, world_id INT, title TEXT, author_hf_id INT`
  `form TEXT` — "poem", "musical composition", "guide", "letter", etc.
  `type TEXT, styles TEXT[], details JSONB`

**historical_eras** — Named ages of the world.
  PK: (world_id, name). `start_year INT`

**identities** — Alternate identities / secret names (~1.9K rows).
  `id INT, world_id INT, name TEXT, histfig_id INT, entity_id INT`

---

### Live Fortress Data (from DFHack bridge)

**units** — Currently loaded game units (~155 rows, refreshed by watcher).
  `id INT PK, world_id INT, name TEXT, english_name TEXT`
  `race TEXT, profession TEXT, pos_x/y/z INT`
  `is_alive BOOL, hist_fig_id INT` (→ historical_figures.id for cross-ref)
  `civ_id INT, birth_year INT, sex SMALLINT, death_cause TEXT`
  `details JSONB` — stress, mood, happiness, labors, skills, etc.

**fortress_denizens** — Denizen registry tracking arrivals/departures.
  `unit_id INT, hf_id INT, name TEXT, race TEXT`
  `status TEXT` — resident, departed, deceased, missing, visitor, attacker, \
skulker, historical
  `embark BOOL, arrival_year INT, departure_year INT, narrative_value FLOAT`

**unit_events** — Detected changes in unit state (~254 rows).
  `unit_id INT, event_type TEXT, old_value JSONB, new_value JSONB`
  `game_year INT, game_tick INT, detected_at TIMESTAMPTZ`

**game_reports** — In-game announcements and combat logs.
  `report_id INT, text TEXT, game_year INT, is_announcement BOOL`

**lua_probes** — Raw bridge snapshots (squads, emotions, zones, armies).
  `probe_name TEXT, data JSONB, game_year INT, game_tick INT`
  probe_name values: "squads", "dwarf_emotions", "zones", "armies", \
"creature_raws", "game_time"

**sync_snapshots** — Watcher poll cycle metadata.
**world_map_snapshots** — Geographic snapshot with elevation/biome data.

---

### Key Query Patterns

**Find a figure by name:**
```sql
SELECT * FROM historical_figures
WHERE world_id = $1 AND name ILIKE '%' || $2 || '%'
ORDER BY importance_score DESC LIMIT 5
```

**Get a figure's relationships:**
```sql
SELECT hl.link_type, hf2.name
FROM hf_links hl
JOIN historical_figures hf2 ON hf2.world_id = hl.world_id AND hf2.id = hl.target_hf_id
WHERE hl.world_id = $1 AND hl.hf_id = $2
```

**Get a figure's current positions (political titles):**
```sql
SELECT ep.name, ep.name_male, ep.name_female, e.name as entity_name
FROM hf_position_links hpl
JOIN entity_positions ep ON ep.world_id = hpl.world_id
  AND ep.entity_id = hpl.entity_id AND ep.position_id = hpl.position_id
JOIN entities e ON e.world_id = hpl.world_id AND e.id = hpl.entity_id
WHERE hpl.world_id = $1 AND hpl.hf_id = $2 AND hpl.end_year IS NULL
```

**Get events involving a figure (with name resolution):**
```sql
SELECT e.year, e.event_type, e.details,
       h1.name as actor, h2.name as target, s.name as site_name
FROM history_events e
LEFT JOIN historical_figures h1 ON h1.world_id = e.world_id AND h1.id = e.hf_id_1
LEFT JOIN historical_figures h2 ON h2.world_id = e.world_id AND h2.id = e.hf_id_2
LEFT JOIN sites s ON s.world_id = e.world_id AND s.id = e.site_id
WHERE e.world_id = $1 AND (e.hf_id_1 = $2 OR e.hf_id_2 = $2)
ORDER BY e.year DESC LIMIT 20
```

**Top figures by importance:**
```sql
SELECT name, race, kill_count, importance_score,
       is_deity, is_vampire, is_necromancer
FROM historical_figures
WHERE world_id = $1 AND importance_score > 100
ORDER BY importance_score DESC LIMIT 20
```

**Wars between civilizations:**
```sql
SELECT hec.name, hec.start_year, hec.end_year,
       att.name as attacker, def.name as defender
FROM history_event_collections hec
LEFT JOIN entities att ON att.world_id = hec.world_id AND att.id = hec.attacker_entity_id
LEFT JOIN entities def ON def.world_id = hec.world_id AND def.id = hec.defender_entity_id
WHERE hec.world_id = $1 AND hec.type = 'war'
ORDER BY hec.start_year DESC
```

**Cross-reference: is an HF alive in the fortress?**
```sql
SELECT u.name, u.profession, u.is_alive, u.details
FROM units u
WHERE u.world_id = $1 AND u.hist_fig_id = $2
```

**Fortress current inhabitants:**
```sql
SELECT name, race, profession, details
FROM units WHERE world_id = $1 AND is_alive = TRUE
ORDER BY name
```

### Importance Score Formulas

HF score = min(events*2, 500) + kills*15 + vampire(80) + necromancer(100) \
+ deity(120) + force(90) + werebeast(70) + min(links*3, 100) \
+ positions*20 + artifacts*30 + min(site_links*5, 50) \
+ min(entity_links*3, 60) + dead(5)

Site score = events + deaths*2 + collections*5 + structures*3

Artifact score = events*10 + named(50) + has_holder(20)

### Safety Rules

1. All queries MUST be SELECT only — no INSERT, UPDATE, DELETE, DROP, ALTER
2. Always parameterize user inputs — never string-interpolate into SQL
3. Always include world_id = $1 in WHERE clauses
4. Use LIMIT to cap results (max 50 rows per query)
5. For ILIKE searches, wrap patterns: '%' || $2 || '%'
"""
