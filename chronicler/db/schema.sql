-- Chronicler CDM Schema
-- Designed for Dwarf Fortress legends XML + DFHack RPC data

CREATE EXTENSION IF NOT EXISTS vector;

-- ─── World Metadata ──────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS worlds (
    id          SERIAL PRIMARY KEY,
    name        TEXT,
    alt_name    TEXT,
    import_path TEXT,
    imported_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS landmasses (
    id          INT PRIMARY KEY,
    world_id    INT REFERENCES worlds(id),
    name        TEXT,
    coord_1     TEXT,
    coord_2     TEXT
);

CREATE TABLE IF NOT EXISTS mountain_peaks (
    id          INT PRIMARY KEY,
    world_id    INT REFERENCES worlds(id),
    name        TEXT,
    coords      TEXT,
    height      INT
);

-- ─── Geography ───────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS regions (
    id          INT PRIMARY KEY,
    world_id    INT REFERENCES worlds(id),
    name        TEXT,
    type        TEXT,
    coords      TEXT
);

CREATE TABLE IF NOT EXISTS underground_regions (
    id          INT PRIMARY KEY,
    world_id    INT REFERENCES worlds(id),
    type        TEXT,
    depth       INT,
    coords      TEXT
);

CREATE TABLE IF NOT EXISTS sites (
    id          INT PRIMARY KEY,
    world_id    INT REFERENCES worlds(id),
    name        TEXT,
    type        TEXT,
    coord_x     INT,
    coord_y     INT,
    coords      TEXT,
    owner_entity_id INT,
    details     JSONB DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS structures (
    site_id     INT REFERENCES sites(id),
    id          INT,
    name        TEXT,
    type        TEXT,
    entity_id   INT,
    details     JSONB DEFAULT '{}',
    PRIMARY KEY (site_id, id)
);

CREATE TABLE IF NOT EXISTS world_constructions (
    id          INT PRIMARY KEY,
    world_id    INT REFERENCES worlds(id),
    name        TEXT,
    type        TEXT,
    coords      TEXT
);

-- ─── Civilizations & Organizations ───────────────────────────────────────────

CREATE TABLE IF NOT EXISTS entities (
    id          INT PRIMARY KEY,
    world_id    INT REFERENCES worlds(id),
    name        TEXT,
    type        TEXT,
    race        TEXT,
    details     JSONB DEFAULT '{}'
);

-- ─── Historical Figures ──────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS historical_figures (
    id              INT PRIMARY KEY,
    world_id        INT REFERENCES worlds(id),
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
    kill_count      INT DEFAULT 0,
    event_count     INT DEFAULT 0,
    details         JSONB DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS hf_links (
    id          SERIAL PRIMARY KEY,
    hf_id       INT REFERENCES historical_figures(id),
    target_hf_id INT REFERENCES historical_figures(id),
    link_type   TEXT
);

CREATE TABLE IF NOT EXISTS hf_entity_links (
    id              SERIAL PRIMARY KEY,
    hf_id           INT REFERENCES historical_figures(id),
    entity_id       INT REFERENCES entities(id),
    link_type       TEXT,
    position_name   TEXT
);

CREATE TABLE IF NOT EXISTS hf_site_links (
    id          SERIAL PRIMARY KEY,
    hf_id       INT REFERENCES historical_figures(id),
    site_id     INT REFERENCES sites(id),
    link_type   TEXT
);

CREATE TABLE IF NOT EXISTS identities (
    id          INT PRIMARY KEY,
    world_id    INT REFERENCES worlds(id),
    name        TEXT,
    histfig_id  INT,
    birth_year  INT,
    birth_second INT,
    entity_id   INT
);

-- ─── Events ──────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS history_events (
    id              INT PRIMARY KEY,
    world_id        INT REFERENCES worlds(id),
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
    details         JSONB DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS history_event_collections (
    id              INT PRIMARY KEY,
    world_id        INT REFERENCES worlds(id),
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
    details         JSONB DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS collection_events (
    collection_id   INT REFERENCES history_event_collections(id),
    event_id        INT REFERENCES history_events(id),
    PRIMARY KEY (collection_id, event_id)
);

CREATE TABLE IF NOT EXISTS collection_subcollections (
    parent_id   INT REFERENCES history_event_collections(id),
    child_id    INT REFERENCES history_event_collections(id),
    PRIMARY KEY (parent_id, child_id)
);

CREATE TABLE IF NOT EXISTS event_relationships (
    id          SERIAL PRIMARY KEY,
    world_id    INT REFERENCES worlds(id),
    event_id    INT,
    relationship TEXT,
    source_hf   INT,
    target_hf   INT,
    year        INT
);

-- ─── Artifacts ───────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS artifacts (
    id              INT PRIMARY KEY,
    world_id        INT REFERENCES worlds(id),
    name            TEXT,
    item_type       TEXT,
    item_subtype    TEXT,
    material        TEXT,
    creator_hf_id   INT,
    holder_hf_id    INT,
    site_id         INT,
    details         JSONB DEFAULT '{}'
);

-- ─── Live Data (DFHack RPC) ─────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS units (
    id              INT PRIMARY KEY,
    world_id        INT REFERENCES worlds(id),
    name            TEXT,
    race            TEXT,
    caste           TEXT,
    profession      TEXT,
    pos_x           INT,
    pos_y           INT,
    pos_z           INT,
    is_alive        BOOLEAN DEFAULT TRUE,
    hist_fig_id     INT,
    civ_id          INT,
    details         JSONB DEFAULT '{}',
    last_synced_at  TIMESTAMPTZ DEFAULT now()
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
CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
CREATE INDEX IF NOT EXISTS idx_artifacts_name ON artifacts(name);
CREATE INDEX IF NOT EXISTS idx_hf_links_hf ON hf_links(hf_id);
CREATE INDEX IF NOT EXISTS idx_hf_links_target ON hf_links(target_hf_id);
CREATE INDEX IF NOT EXISTS idx_hf_entity_links_hf ON hf_entity_links(hf_id);
CREATE INDEX IF NOT EXISTS idx_hf_site_links_hf ON hf_site_links(hf_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_entity ON embeddings(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_event_rels_source ON event_relationships(source_hf);
CREATE INDEX IF NOT EXISTS idx_event_rels_target ON event_relationships(target_hf);
