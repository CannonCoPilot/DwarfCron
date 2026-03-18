-- Chronicler CDM Schema
-- Designed for Dwarf Fortress legends XML + DFHack RPC data
-- v2: Composite primary keys (world_id, id) for multi-world support

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS unaccent;

-- ─── World Metadata ──────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS worlds (
    id          SERIAL PRIMARY KEY,
    name        TEXT,
    alt_name    TEXT,
    import_path TEXT,
    imported_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS landmasses (
    id          INT NOT NULL,
    world_id    INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    name        TEXT,
    coord_1     TEXT,
    coord_2     TEXT,
    PRIMARY KEY (world_id, id)
);

CREATE TABLE IF NOT EXISTS mountain_peaks (
    id          INT NOT NULL,
    world_id    INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    name        TEXT,
    coords      TEXT,
    height      INT,
    is_volcano  BOOLEAN DEFAULT FALSE,
    prominence_score REAL DEFAULT 0,
    salience_score   REAL DEFAULT 0,
    PRIMARY KEY (world_id, id)
);

-- ─── Geography ───────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS regions (
    id          INT NOT NULL,
    world_id    INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    name        TEXT,
    type        TEXT,
    coords      TEXT,
    evilness    TEXT,
    salience_score   REAL DEFAULT 0,
    prominence_score REAL DEFAULT 0,
    PRIMARY KEY (world_id, id)
);

CREATE TABLE IF NOT EXISTS underground_regions (
    id          INT NOT NULL,
    world_id    INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    type        TEXT,
    depth       INT,
    coords      TEXT,
    prominence_score REAL DEFAULT 0,
    salience_score   REAL DEFAULT 0,
    PRIMARY KEY (world_id, id)
);

CREATE TABLE IF NOT EXISTS sites (
    id          INT NOT NULL,
    world_id    INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    name        TEXT,
    type        TEXT,
    coord_x     INT,
    coord_y     INT,
    coords      TEXT,
    owner_entity_id INT,
    founded_year    INT,
    founder_entity_id INT,
    salience_score   REAL DEFAULT 0,
    prominence_score REAL DEFAULT 0,
    details     JSONB DEFAULT '{}',
    PRIMARY KEY (world_id, id)
);

CREATE TABLE IF NOT EXISTS structures (
    id          INT NOT NULL,
    world_id    INT NOT NULL,
    site_id     INT NOT NULL,
    name        TEXT,
    type        TEXT,
    entity_id   INT,
    details     JSONB DEFAULT '{}',
    prominence_score REAL DEFAULT 0,
    salience_score   REAL DEFAULT 0,
    PRIMARY KEY (world_id, site_id, id),
    FOREIGN KEY (world_id, site_id) REFERENCES sites(world_id, id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS world_constructions (
    id          INT NOT NULL,
    world_id    INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    name        TEXT,
    type        TEXT,
    coords      TEXT,
    salience_score   REAL DEFAULT 0,
    prominence_score REAL DEFAULT 0,
    PRIMARY KEY (world_id, id)
);

CREATE TABLE IF NOT EXISTS art_forms (
    world_id    INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    id          INT NOT NULL,
    name        TEXT,
    form_type   TEXT NOT NULL,  -- 'dance', 'musical', 'poetic'
    description TEXT,
    details     JSONB DEFAULT '{}',
    prominence_score REAL DEFAULT 0,
    salience_score   REAL DEFAULT 0,
    PRIMARY KEY (world_id, id, form_type)
);

CREATE INDEX IF NOT EXISTS idx_art_forms_type ON art_forms(world_id, form_type);
CREATE INDEX IF NOT EXISTS idx_art_forms_name ON art_forms(world_id, name);

CREATE TABLE IF NOT EXISTS rivers (
    world_id     INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    id           INT NOT NULL,
    name         TEXT,
    name_english TEXT,
    path         TEXT,      -- pipe-delimited coordinate pairs for river path
    end_type     TEXT,      -- ocean, lake, underground, etc.
    details      JSONB DEFAULT '{}',
    salience_score   REAL DEFAULT 0,
    prominence_score REAL DEFAULT 0,
    PRIMARY KEY (world_id, id)
);

CREATE INDEX IF NOT EXISTS idx_rivers_name ON rivers(world_id, name);

-- ─── Creature Dictionary (Stage 1.5) ──────────────────────────────────────

CREATE TABLE IF NOT EXISTS creature_dictionary (
    world_id       INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    creature_id    TEXT NOT NULL,       -- matches historical_figures.race token
    name_singular  TEXT,                -- "dwarf", "forgotten beast", "midnight freak"
    name_plural    TEXT,                -- "dwarves", "forgotten beasts"
    flags          JSONB DEFAULT '{}',  -- all boolean tags from creature_raw
    PRIMARY KEY (world_id, creature_id)
);

CREATE INDEX IF NOT EXISTS idx_creature_dictionary_world
    ON creature_dictionary(world_id);

-- ─── Entity Populations ────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS entity_populations (
    id          INT NOT NULL,
    world_id    INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    race        TEXT,              -- creature race token (e.g. 'DWARF', 'goblin')
    count       INT,               -- population count for this race in this entity
    civ_id      INT,               -- entity/civilization ID this population belongs to
    PRIMARY KEY (world_id, id)
);

CREATE INDEX IF NOT EXISTS idx_entity_populations_civ
    ON entity_populations(world_id, civ_id);
CREATE INDEX IF NOT EXISTS idx_entity_populations_race
    ON entity_populations(world_id, race);

-- ─── Civilizations & Organizations ───────────────────────────────────────────

CREATE TABLE IF NOT EXISTS entities (
    id          INT NOT NULL,
    world_id    INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    name        TEXT,
    type        TEXT,
    race        TEXT,
    worship_id  INT,
    weapons     TEXT[],
    prominence_score REAL DEFAULT 0,
    salience_score   REAL DEFAULT 0,
    details     JSONB DEFAULT '{}',
    PRIMARY KEY (world_id, id)
);

-- ─── Entity-Entity Links ───────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS entity_entity_links (
    world_id            INT NOT NULL,
    source_entity_id    INT NOT NULL,
    target_entity_id    INT NOT NULL,
    link_type           TEXT NOT NULL,
    strength            SMALLINT DEFAULT 100,
    details             JSONB DEFAULT '{}',
    PRIMARY KEY (world_id, source_entity_id, target_entity_id, link_type),
    FOREIGN KEY (world_id, source_entity_id) REFERENCES entities(world_id, id) ON DELETE CASCADE,
    FOREIGN KEY (world_id, target_entity_id) REFERENCES entities(world_id, id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_eel_target ON entity_entity_links(world_id, target_entity_id);

-- ─── Entity-Site Links ────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS entity_site_links (
    world_id            INT NOT NULL,
    entity_id           INT NOT NULL,
    site_id             INT NOT NULL,
    link_type           TEXT NOT NULL,
    flags               JSONB DEFAULT '{}',
    start_year          INT,
    end_year            INT,
    link_strength       INT DEFAULT 100,
    details             JSONB DEFAULT '{}',
    PRIMARY KEY (world_id, entity_id, site_id, link_type),
    FOREIGN KEY (world_id, entity_id) REFERENCES entities(world_id, id) ON DELETE CASCADE,
    FOREIGN KEY (world_id, site_id) REFERENCES sites(world_id, id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_esl_site ON entity_site_links(world_id, site_id);

-- ─── Historical Figures ──────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS historical_figures (
    id              INT NOT NULL,
    world_id        INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    name            TEXT,
    race            TEXT,
    caste           TEXT,
    sex             SMALLINT,
    birth_year      INT,
    birth_seconds   INT,
    death_year      INT,
    death_seconds   INT,
    death_cause     TEXT,
    entity_id       INT,
    is_deity        BOOLEAN DEFAULT FALSE,
    is_force        BOOLEAN DEFAULT FALSE,
    is_vampire      BOOLEAN DEFAULT FALSE,
    is_necromancer  BOOLEAN DEFAULT FALSE,
    is_werebeast    BOOLEAN DEFAULT FALSE,
    is_ghost        BOOLEAN DEFAULT FALSE,
    is_author       BOOLEAN DEFAULT FALSE,
    is_auteur       BOOLEAN DEFAULT FALSE,
    kill_count      INT DEFAULT 0,
    event_count     INT DEFAULT 0,
    prominence_score REAL DEFAULT 0,
    salience_score   REAL DEFAULT 0,
    spheres         TEXT[],
    goals           JSONB DEFAULT '[]',
    skills          JSONB DEFAULT '[]',
    kills           JSONB DEFAULT '{}',
    whereabouts     JSONB DEFAULT '{}',
    entity_reputations JSONB DEFAULT '[]',
    intrigue_actors JSONB DEFAULT '[]',
    used_identities JSONB DEFAULT '[]',
    journey_pets    JSONB DEFAULT '[]',
    holds_artifact  INTEGER[],
    active_interactions TEXT[],
    associated_type TEXT,
    appeared        INT,
    first_ageless_year INT,
    current_identity_id INT,
    details         JSONB DEFAULT '{}',
    PRIMARY KEY (world_id, id)
);

CREATE INDEX IF NOT EXISTS idx_hf_spheres
    ON historical_figures USING gin(spheres);
CREATE INDEX IF NOT EXISTS idx_hf_interactions
    ON historical_figures USING gin(active_interactions);
CREATE INDEX IF NOT EXISTS idx_hf_associated_type
    ON historical_figures(associated_type);

CREATE TABLE IF NOT EXISTS hf_links (
    id           SERIAL PRIMARY KEY,
    world_id     INT NOT NULL,
    hf_id        INT NOT NULL,
    target_hf_id INT NOT NULL,
    link_type    TEXT,
    strength     SMALLINT,
    UNIQUE (world_id, hf_id, target_hf_id, link_type),
    FOREIGN KEY (world_id, hf_id) REFERENCES historical_figures(world_id, id) ON DELETE CASCADE,
    FOREIGN KEY (world_id, target_hf_id) REFERENCES historical_figures(world_id, id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS hf_entity_links (
    id              SERIAL PRIMARY KEY,
    world_id        INT NOT NULL,
    hf_id           INT NOT NULL,
    entity_id       INT NOT NULL,
    link_type       TEXT,
    position_name   TEXT,
    UNIQUE (world_id, hf_id, entity_id, link_type),
    FOREIGN KEY (world_id, hf_id) REFERENCES historical_figures(world_id, id) ON DELETE CASCADE,
    FOREIGN KEY (world_id, entity_id) REFERENCES entities(world_id, id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS hf_site_links (
    id          SERIAL PRIMARY KEY,
    world_id    INT NOT NULL,
    hf_id       INT NOT NULL,
    site_id     INT NOT NULL,
    link_type   TEXT,
    UNIQUE (world_id, hf_id, site_id, link_type),
    FOREIGN KEY (world_id, hf_id) REFERENCES historical_figures(world_id, id) ON DELETE CASCADE,
    FOREIGN KEY (world_id, site_id) REFERENCES sites(world_id, id) ON DELETE CASCADE
);

-- ─── HF Relationship Profiles (emotional scores toward other HFs) ─────────

CREATE TABLE IF NOT EXISTS hf_relationship_profiles (
    id              SERIAL PRIMARY KEY,
    world_id        INT NOT NULL,
    hf_id           INT NOT NULL,
    target_hf_id    INT NOT NULL,
    meet_count      INT DEFAULT 0,
    last_meet_year  INT,
    last_meet_seconds INT,
    known_identity_id INT,
    rep_friendly    INT DEFAULT 0,
    love            INT DEFAULT 0,
    respect         INT DEFAULT 0,
    trust           INT DEFAULT 0,
    loyalty         INT DEFAULT 0,
    fear            INT DEFAULT 0,
    UNIQUE (world_id, hf_id, target_hf_id),
    FOREIGN KEY (world_id, hf_id) REFERENCES historical_figures(world_id, id) ON DELETE CASCADE,
    FOREIGN KEY (world_id, target_hf_id) REFERENCES historical_figures(world_id, id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_hf_rel_profiles_hf
    ON hf_relationship_profiles(world_id, hf_id);
CREATE INDEX IF NOT EXISTS idx_hf_rel_profiles_target
    ON hf_relationship_profiles(world_id, target_hf_id);

-- ─── HF Vague Relationships (informal bonds: war_buddy, grudge, etc.) ─────

CREATE TABLE IF NOT EXISTS hf_vague_relationships (
    id              SERIAL PRIMARY KEY,
    world_id        INT NOT NULL,
    hf_id           INT NOT NULL,
    target_hf_id    INT NOT NULL,
    relationship_type TEXT NOT NULL,
    UNIQUE (world_id, hf_id, target_hf_id, relationship_type),
    FOREIGN KEY (world_id, hf_id) REFERENCES historical_figures(world_id, id) ON DELETE CASCADE,
    FOREIGN KEY (world_id, target_hf_id) REFERENCES historical_figures(world_id, id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_hf_vague_rel_hf
    ON hf_vague_relationships(world_id, hf_id);

-- ─── HF Intrigue Plots (political schemes) ───────────────────────────────

CREATE TABLE IF NOT EXISTS hf_intrigue_plots (
    id              SERIAL PRIMARY KEY,
    world_id        INT NOT NULL,
    hf_id           INT NOT NULL,
    local_id        INT,
    type            TEXT,
    entity_id       INT,
    on_hold         BOOLEAN DEFAULT FALSE,
    actor_hf_id     INT,
    details         JSONB DEFAULT '{}',
    UNIQUE (world_id, hf_id, local_id),
    FOREIGN KEY (world_id, hf_id) REFERENCES historical_figures(world_id, id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_hf_intrigue_hf
    ON hf_intrigue_plots(world_id, hf_id);

-- ─── HF Squad Links (military squad membership) ──────────────────────────

CREATE TABLE IF NOT EXISTS hf_squad_links (
    id              SERIAL PRIMARY KEY,
    world_id        INT NOT NULL,
    hf_id           INT NOT NULL,
    squad_id        INT NOT NULL,
    squad_position  INT,
    entity_id       INT,
    start_year      INT,
    UNIQUE (world_id, hf_id, squad_id, entity_id),
    FOREIGN KEY (world_id, hf_id) REFERENCES historical_figures(world_id, id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_hf_squad_links_hf
    ON hf_squad_links(world_id, hf_id);

-- ─── Site Properties (house/property ownership) ──────────────────────────

CREATE TABLE IF NOT EXISTS site_properties (
    world_id        INT NOT NULL,
    site_id         INT NOT NULL,
    id              INT NOT NULL,
    type            TEXT,
    owner_hfid      INT,
    structure_id    INT,
    PRIMARY KEY (world_id, site_id, id),
    FOREIGN KEY (world_id, site_id) REFERENCES sites(world_id, id) ON DELETE CASCADE
);

-- ─── Entity Honors (military honor definitions) ──────────────────────────

CREATE TABLE IF NOT EXISTS entity_honors (
    world_id        INT NOT NULL,
    entity_id       INT NOT NULL,
    id              INT NOT NULL,
    name            TEXT,
    gives_precedence INT,
    required_skill  TEXT,
    required_skill_ip_total INT,
    required_battles INT,
    exempt_epid     INT,
    exempt_former_epid INT,
    granted_to_everybody BOOLEAN DEFAULT FALSE,
    requires_any_melee_or_ranged_skill BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (world_id, entity_id, id),
    FOREIGN KEY (world_id, entity_id) REFERENCES entities(world_id, id) ON DELETE CASCADE
);

-- ─── Entity Occasions (festivals, celebrations — from legends_plus) ────────

CREATE TABLE IF NOT EXISTS entity_occasions (
    world_id    INT NOT NULL,
    entity_id   INT NOT NULL,
    occasion_id INT NOT NULL,
    name        TEXT,
    event_id    INT,
    PRIMARY KEY (world_id, entity_id, occasion_id),
    FOREIGN KEY (world_id, entity_id) REFERENCES entities(world_id, id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS occasion_schedules (
    world_id        INT NOT NULL,
    entity_id       INT NOT NULL,
    occasion_id     INT NOT NULL,
    schedule_id     INT NOT NULL,
    type            TEXT,
    reference       INT,
    reference2      INT,
    item_type       TEXT,
    item_subtype    TEXT,
    features        JSONB,
    PRIMARY KEY (world_id, entity_id, occasion_id, schedule_id),
    FOREIGN KEY (world_id, entity_id, occasion_id)
        REFERENCES entity_occasions(world_id, entity_id, occasion_id) ON DELETE CASCADE
);

-- ─── Entity Positions ───────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS entity_positions (
    id              SERIAL PRIMARY KEY,
    world_id        INT NOT NULL,
    entity_id       INT NOT NULL,
    position_id     INT NOT NULL,      -- local ID within entity (0, 1, 2...)
    name            TEXT,              -- generic name ("monarch", "general")
    name_male       TEXT,              -- gendered variant ("king")
    name_female     TEXT,              -- gendered variant ("queen")
    spouse          TEXT,              -- spouse title ("king consort")
    spouse_male     TEXT,
    spouse_female   TEXT,
    UNIQUE (world_id, entity_id, position_id),
    FOREIGN KEY (world_id, entity_id) REFERENCES entities(world_id, id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_entity_positions_entity
    ON entity_positions(world_id, entity_id);

CREATE TABLE IF NOT EXISTS hf_position_links (
    id              SERIAL PRIMARY KEY,
    world_id        INT NOT NULL,
    hf_id           INT NOT NULL,
    entity_id       INT NOT NULL,
    position_id     INT NOT NULL,      -- references entity_positions.position_id
    start_year      INT,
    end_year        INT,               -- NULL = currently held
    UNIQUE (world_id, hf_id, entity_id, position_id, start_year),
    FOREIGN KEY (world_id, hf_id) REFERENCES historical_figures(world_id, id) ON DELETE CASCADE,
    FOREIGN KEY (world_id, entity_id) REFERENCES entities(world_id, id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_hf_position_links_hf
    ON hf_position_links(world_id, hf_id);
CREATE INDEX IF NOT EXISTS idx_hf_position_links_entity
    ON hf_position_links(world_id, entity_id);
CREATE INDEX IF NOT EXISTS idx_hf_position_links_current
    ON hf_position_links(world_id, entity_id) WHERE end_year IS NULL;
-- Partial unique index: prevent duplicate active positions with NULL start_year
-- (PostgreSQL treats NULLs as distinct in UNIQUE constraints)
CREATE UNIQUE INDEX IF NOT EXISTS idx_hf_position_links_null_start_dedup
    ON hf_position_links(world_id, hf_id, entity_id, position_id) WHERE start_year IS NULL;

CREATE TABLE IF NOT EXISTS identities (
    id          INT NOT NULL,
    world_id    INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    name        TEXT,
    histfig_id  INT,
    birth_year  INT,
    birth_second INT,
    entity_id   INT,
    race        TEXT,
    caste       TEXT,
    profession  TEXT,
    details     JSONB DEFAULT '{}',
    PRIMARY KEY (world_id, id)
);

-- ─── Events ──────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS history_events (
    id              INT NOT NULL,
    world_id        INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    year            INT,
    seconds         INT,
    event_type      TEXT,
    -- Common FK columns covering ~95% of event subtypes
    hf_id_1         INT,
    hf_id_2         INT,
    site_id         INT,
    region_id       INT,
    entity_id_1     INT,
    entity_id_2     INT,
    artifact_id     INT,
    structure_id    INT,
    -- Overflow for unmapped fields
    details         JSONB DEFAULT '{}',
    source          TEXT DEFAULT 'legends_xml',
    PRIMARY KEY (world_id, id)
);

CREATE TABLE IF NOT EXISTS history_event_collections (
    id              INT NOT NULL,
    world_id        INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    type            TEXT,
    name            TEXT,
    parent_id       INT,
    start_year      INT,
    start_seconds   INT,
    end_year        INT,
    end_seconds     INT,
    attacker_entity_id INT,
    defender_entity_id INT,
    site_id         INT,
    region_id       INT,
    details         JSONB DEFAULT '{}',
    prominence_score REAL DEFAULT 0,
    salience_score   REAL DEFAULT 0,
    PRIMARY KEY (world_id, id)
);

CREATE TABLE IF NOT EXISTS collection_events (
    world_id        INT NOT NULL,
    collection_id   INT NOT NULL,
    event_id        INT NOT NULL,
    PRIMARY KEY (world_id, collection_id, event_id),
    FOREIGN KEY (world_id, collection_id) REFERENCES history_event_collections(world_id, id) ON DELETE CASCADE,
    FOREIGN KEY (world_id, event_id) REFERENCES history_events(world_id, id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS collection_subcollections (
    world_id    INT NOT NULL,
    parent_id   INT NOT NULL,
    child_id    INT NOT NULL,
    PRIMARY KEY (world_id, parent_id, child_id),
    FOREIGN KEY (world_id, parent_id) REFERENCES history_event_collections(world_id, id) ON DELETE CASCADE,
    FOREIGN KEY (world_id, child_id) REFERENCES history_event_collections(world_id, id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS event_relationships (
    id          SERIAL PRIMARY KEY,
    world_id    INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    event_id    INT,
    relationship TEXT,
    source_hf   INT,
    target_hf   INT,
    year        INT,
    details     JSONB
);

-- ─── Artifacts ───────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS artifacts (
    id              INT NOT NULL,
    world_id        INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    name            TEXT,
    item_type       TEXT,
    item_subtype    TEXT,
    material        TEXT,
    creator_hf_id   INT,
    holder_hf_id    INT,
    site_id         INT,
    prominence_score REAL DEFAULT 0,
    salience_score   REAL DEFAULT 0,
    details         JSONB DEFAULT '{}',
    PRIMARY KEY (world_id, id)
);

-- ─── Written Contents ───────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS written_contents (
    id              INT NOT NULL,
    world_id        INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    title           TEXT,
    author_hf_id    INT,
    form            TEXT,          -- "poem", "musical composition", "guide", etc.
    type            TEXT,          -- CamelCase from legends_plus: "Poem", "MusicalComposition"
    page_start      INT,
    page_end        INT,
    styles          TEXT[],        -- style tags (merged from both XML sources)
    details         JSONB DEFAULT '{}',
    prominence_score REAL DEFAULT 0,
    salience_score   REAL DEFAULT 0,
    PRIMARY KEY (world_id, id)
);

CREATE INDEX IF NOT EXISTS idx_written_contents_author ON written_contents(author_hf_id);

-- ─── Historical Eras ───────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS historical_eras (
    world_id        INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    start_year      INT,
    PRIMARY KEY (world_id, name)
);

-- ─── Live Data (DFHack RPC) ─────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS units (
    id              INT NOT NULL,
    world_id        INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    name            TEXT,
    english_name    TEXT,
    race            TEXT,
    caste           TEXT,
    profession      TEXT,
    pos_x           INT,
    pos_y           INT,
    pos_z           INT,
    is_alive        BOOLEAN DEFAULT TRUE,
    hist_fig_id     INT,
    civ_id          INT,
    birth_year      INT,
    sex             SMALLINT,
    death_cause     TEXT,
    details         JSONB DEFAULT '{}',
    last_synced_at  TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (world_id, id)
);

-- ─── Embeddings (Phase 2) ───────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS embeddings (
    id              SERIAL PRIMARY KEY,
    entity_type     TEXT NOT NULL,
    entity_id       INT NOT NULL,
    chunk_index     INT NOT NULL DEFAULT 0,
    chunk_text      TEXT NOT NULL,
    content_hash    TEXT NOT NULL,
    embedding       vector(2560),
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- ─── Indexes ─────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_events_year ON history_events(year);
CREATE INDEX IF NOT EXISTS idx_events_type ON history_events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_hf1 ON history_events(hf_id_1);
CREATE INDEX IF NOT EXISTS idx_events_hf2 ON history_events(hf_id_2);
CREATE INDEX IF NOT EXISTS idx_events_site ON history_events(site_id);
CREATE INDEX IF NOT EXISTS idx_events_entity1 ON history_events(entity_id_1);
CREATE INDEX IF NOT EXISTS idx_hf_name ON historical_figures(name);
CREATE INDEX IF NOT EXISTS idx_hf_race ON historical_figures(race);
CREATE INDEX IF NOT EXISTS idx_sites_name ON sites(name);
CREATE INDEX IF NOT EXISTS idx_sites_owner ON sites(world_id, owner_entity_id);
CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
CREATE INDEX IF NOT EXISTS idx_artifacts_name ON artifacts(name);
CREATE INDEX IF NOT EXISTS idx_hf_links_hf ON hf_links(hf_id);
CREATE INDEX IF NOT EXISTS idx_hf_links_target ON hf_links(target_hf_id);
CREATE INDEX IF NOT EXISTS idx_hf_entity_links_hf ON hf_entity_links(hf_id);
CREATE INDEX IF NOT EXISTS idx_hf_entity_links_entity ON hf_entity_links(world_id, entity_id);
CREATE INDEX IF NOT EXISTS idx_hf_site_links_hf ON hf_site_links(hf_id);
CREATE INDEX IF NOT EXISTS idx_hf_site_links_site ON hf_site_links(site_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_entity ON embeddings(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_event_rels_source ON event_relationships(source_hf);
CREATE INDEX IF NOT EXISTS idx_event_rels_target ON event_relationships(target_hf);
CREATE INDEX IF NOT EXISTS idx_hf_prominence ON historical_figures(world_id, prominence_score DESC);
CREATE INDEX IF NOT EXISTS idx_sites_prominence ON sites(world_id, prominence_score DESC);
CREATE INDEX IF NOT EXISTS idx_entities_prominence ON entities(world_id, prominence_score DESC);
CREATE INDEX IF NOT EXISTS idx_artifacts_prominence ON artifacts(world_id, prominence_score DESC);

-- ─── Event Cross-Reference Index ───────────────────────────────────────────

CREATE TABLE IF NOT EXISTS event_entity_xref (
    world_id    INT NOT NULL,
    event_id    INT NOT NULL,
    entity_type TEXT NOT NULL,   -- 'hf', 'entity', 'site', 'artifact', 'region'
    entity_id   INT NOT NULL,
    role        TEXT,            -- 'subject', 'object', 'location', 'participant'
    PRIMARY KEY (world_id, event_id, entity_type, entity_id),
    FOREIGN KEY (world_id, event_id) REFERENCES history_events(world_id, id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_event_entity_xref_entity
    ON event_entity_xref(world_id, entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_event_entity_xref_event
    ON event_entity_xref(world_id, event_id);

-- ─── System Tables ─────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS worldgen_snapshots (
    id          SERIAL PRIMARY KEY,
    world_id    INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    phase       TEXT NOT NULL,
    progress_pct FLOAT,
    year        INT,
    pop_count   INT,
    site_count  INT,
    hf_count    INT,
    entity_count INT,
    event_count INT,
    data        JSONB DEFAULT '{}',
    captured_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_worldgen_snapshots_world
    ON worldgen_snapshots(world_id);

CREATE TABLE IF NOT EXISTS world_modpacks (
    id          SERIAL PRIMARY KEY,
    world_id    INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    version     TEXT,
    source      TEXT,         -- 'steam_workshop', 'manual', 'dfhack'
    active      BOOLEAN DEFAULT TRUE,
    details     JSONB DEFAULT '{}',
    recorded_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_world_modpacks_world
    ON world_modpacks(world_id);

-- ─── Monitoring ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS storyteller_log (
    id                  SERIAL PRIMARY KEY,
    timestamp           TIMESTAMPTZ NOT NULL DEFAULT now(),
    query               TEXT NOT NULL,
    world_id            INT,
    world_name          TEXT,
    keywords            TEXT[],
    context_records     INT DEFAULT 0,
    context_chars       INT DEFAULT 0,
    context_categories  JSONB DEFAULT '{}',
    model               TEXT,
    temperature         REAL,
    max_tokens          INT,
    tokens_streamed     INT DEFAULT 0,
    response_chars      INT DEFAULT 0,
    context_latency_ms  INT,
    first_token_ms      INT,
    llm_latency_ms      INT,
    total_latency_ms    INT,
    status              TEXT DEFAULT 'ok',
    error               TEXT
);

CREATE INDEX IF NOT EXISTS idx_storyteller_log_ts ON storyteller_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_storyteller_log_world ON storyteller_log(world_id);

-- ── Live Sync: Unit Events ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS unit_events (
    id              SERIAL PRIMARY KEY,
    unit_id         INT NOT NULL,
    world_id        INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    event_type      TEXT NOT NULL,
    old_value       JSONB,
    new_value       JSONB,
    game_year       INT,
    game_tick       INT,
    detected_at     TIMESTAMPTZ DEFAULT now(),
    reconciled_event_id INTEGER,
    reconciled_at   TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_unit_events_unit ON unit_events(unit_id);
CREATE INDEX IF NOT EXISTS idx_unit_events_type ON unit_events(event_type);
CREATE INDEX IF NOT EXISTS idx_unit_events_time ON unit_events(detected_at);
CREATE INDEX IF NOT EXISTS idx_unit_events_reconciled ON unit_events(reconciled_event_id) WHERE reconciled_event_id IS NOT NULL;

-- ── Live Sync: Poll Cycle Snapshots ─────────────────────────────────
CREATE TABLE IF NOT EXISTS sync_snapshots (
    id              SERIAL PRIMARY KEY,
    world_id        INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    unit_count      INT NOT NULL,
    event_count     INT DEFAULT 0,
    game_year       INT,
    game_tick       INT,
    synced_at       TIMESTAMPTZ DEFAULT now()
);

-- ── Live Data: Game Reports (announcements, combat logs) ────────────
CREATE TABLE IF NOT EXISTS game_reports (
    id              SERIAL PRIMARY KEY,
    world_id        INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    report_id       INT NOT NULL,
    report_type     INT,
    text            TEXT NOT NULL,
    game_year       INT,
    game_tick       INT,
    pos_x           INT,
    pos_y           INT,
    pos_z           INT,
    is_announcement BOOLEAN DEFAULT FALSE,
    detected_at     TIMESTAMPTZ DEFAULT now(),
    UNIQUE (world_id, report_id)
);

CREATE INDEX IF NOT EXISTS idx_game_reports_world ON game_reports(world_id);
CREATE INDEX IF NOT EXISTS idx_game_reports_year ON game_reports(game_year);

-- ── Live Data: World Map Snapshots (geography) ──────────────────────
CREATE TABLE IF NOT EXISTS world_map_snapshots (
    id              SERIAL PRIMARY KEY,
    world_id        INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    world_width     INT NOT NULL,
    world_height    INT NOT NULL,
    name            TEXT,
    name_english    TEXT,
    geography       JSONB NOT NULL,
    captured_at     TIMESTAMPTZ DEFAULT now(),
    UNIQUE (world_id)
);

-- ── Live Data: Lua Probe Results ────────────────────────────────────
CREATE TABLE IF NOT EXISTS lua_probes (
    id              SERIAL PRIMARY KEY,
    world_id        INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    probe_name      TEXT NOT NULL,
    data            JSONB NOT NULL,
    game_year       INT,
    game_tick       INT,
    captured_at     TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_lua_probes_world ON lua_probes(world_id);
CREATE INDEX IF NOT EXISTS idx_lua_probes_name ON lua_probes(probe_name);

-- ─── Fortress Denizen Registry ────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS fortress_denizens (
    id              SERIAL PRIMARY KEY,
    world_id        INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    unit_id         INT,                -- NULL if HF-only (never had unit record)
    hf_id           INT,                -- NULL if unit-only (no HF match yet)
    name            TEXT NOT NULL,       -- Best available name
    english_name    TEXT,                -- English translation if available
    race            TEXT,
    status          TEXT NOT NULL DEFAULT 'unknown',
        -- 'resident'   : Currently living in fortress
        -- 'departed'   : Left alive (migrated out, caravan departed)
        -- 'deceased'   : Confirmed dead
        -- 'missing'    : Was resident, now absent (no departure/death event)
        -- 'visitor'    : Temporary presence (diplomat, merchant, performer)
        -- 'attacker'   : Hostile presence (siege, ambush)
        -- 'skulker'    : Covert presence (thief, snatcher)
        -- 'historical' : Known only from legends/relationships, never present
    embark          BOOLEAN DEFAULT FALSE,  -- TRUE if starting dwarf at embark
    arrival_year    INT,                -- Year first detected at fortress
    arrival_tick    INT,                -- Tick within year
    departure_year  INT,                -- Year departed/died (NULL if still present)
    departure_tick  INT,
    departure_cause TEXT,               -- 'death', 'departure', 'unknown'
    narrative_value FLOAT DEFAULT 0.0,  -- Storytelling importance score (0.0-100.0)
    last_seen_tick  INT,                -- Last watcher cycle tick where observed
    details         JSONB DEFAULT '{}', -- Extended metadata
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (world_id, unit_id),
    UNIQUE (world_id, hf_id)
);

CREATE INDEX IF NOT EXISTS idx_fortress_denizens_status
    ON fortress_denizens(world_id, status);
CREATE INDEX IF NOT EXISTS idx_fortress_denizens_narrative
    ON fortress_denizens(world_id, narrative_value DESC);
CREATE INDEX IF NOT EXISTS idx_fortress_denizens_hf
    ON fortress_denizens(world_id, hf_id) WHERE hf_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_fortress_denizens_embark
    ON fortress_denizens(world_id) WHERE embark = TRUE;
