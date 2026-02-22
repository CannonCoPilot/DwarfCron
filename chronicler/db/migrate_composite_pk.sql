-- Migration: Single-column PKs → Composite PKs (world_id, id)
-- Run AFTER backing up: pg_dump -Fc chronicler > chronicler-pre-migration.dump
--
-- Strategy: Drop legends tables in dependency order, keep worlds + live tables.
-- After this migration, re-import XML files to repopulate legends data.

BEGIN;

-- ── Drop in reverse dependency order ────────────────────────────────────────

-- Junction tables (depend on events + collections)
DROP TABLE IF EXISTS collection_subcollections CASCADE;
DROP TABLE IF EXISTS collection_events CASCADE;

-- Relationship tables
DROP TABLE IF EXISTS event_relationships CASCADE;

-- Link tables (depend on HF, entities, sites)
DROP TABLE IF EXISTS hf_site_links CASCADE;
DROP TABLE IF EXISTS hf_entity_links CASCADE;
DROP TABLE IF EXISTS hf_links CASCADE;

-- Core legends tables
DROP TABLE IF EXISTS identities CASCADE;
DROP TABLE IF EXISTS artifacts CASCADE;
DROP TABLE IF EXISTS history_event_collections CASCADE;
DROP TABLE IF EXISTS history_events CASCADE;
DROP TABLE IF EXISTS historical_figures CASCADE;
DROP TABLE IF EXISTS structures CASCADE;
DROP TABLE IF EXISTS entities CASCADE;
DROP TABLE IF EXISTS sites CASCADE;
DROP TABLE IF EXISTS world_constructions CASCADE;
DROP TABLE IF EXISTS underground_regions CASCADE;
DROP TABLE IF EXISTS regions CASCADE;
DROP TABLE IF EXISTS mountain_peaks CASCADE;
DROP TABLE IF EXISTS landmasses CASCADE;

-- Embeddings (will be regenerated)
DROP TABLE IF EXISTS embeddings CASCADE;

-- ── Recreate with composite PKs ─────────────────────────────────────────────

CREATE TABLE landmasses (
    id          INT NOT NULL,
    world_id    INT NOT NULL REFERENCES worlds(id),
    name        TEXT,
    coord_1     TEXT,
    coord_2     TEXT,
    PRIMARY KEY (world_id, id)
);

CREATE TABLE mountain_peaks (
    id          INT NOT NULL,
    world_id    INT NOT NULL REFERENCES worlds(id),
    name        TEXT,
    coords      TEXT,
    height      INT,
    PRIMARY KEY (world_id, id)
);

CREATE TABLE regions (
    id          INT NOT NULL,
    world_id    INT NOT NULL REFERENCES worlds(id),
    name        TEXT,
    type        TEXT,
    coords      TEXT,
    PRIMARY KEY (world_id, id)
);

CREATE TABLE underground_regions (
    id          INT NOT NULL,
    world_id    INT NOT NULL REFERENCES worlds(id),
    type        TEXT,
    depth       INT,
    coords      TEXT,
    PRIMARY KEY (world_id, id)
);

CREATE TABLE sites (
    id          INT NOT NULL,
    world_id    INT NOT NULL REFERENCES worlds(id),
    name        TEXT,
    type        TEXT,
    coord_x     INT,
    coord_y     INT,
    coords      TEXT,
    owner_entity_id INT,
    details     JSONB DEFAULT '{}',
    PRIMARY KEY (world_id, id)
);

CREATE TABLE structures (
    id          INT NOT NULL,
    world_id    INT NOT NULL,
    site_id     INT NOT NULL,
    name        TEXT,
    type        TEXT,
    entity_id   INT,
    details     JSONB DEFAULT '{}',
    PRIMARY KEY (world_id, site_id, id),
    FOREIGN KEY (world_id, site_id) REFERENCES sites(world_id, id)
);

CREATE TABLE world_constructions (
    id          INT NOT NULL,
    world_id    INT NOT NULL REFERENCES worlds(id),
    name        TEXT,
    type        TEXT,
    coords      TEXT,
    PRIMARY KEY (world_id, id)
);

CREATE TABLE entities (
    id          INT NOT NULL,
    world_id    INT NOT NULL REFERENCES worlds(id),
    name        TEXT,
    type        TEXT,
    race        TEXT,
    details     JSONB DEFAULT '{}',
    PRIMARY KEY (world_id, id)
);

CREATE TABLE historical_figures (
    id              INT NOT NULL,
    world_id        INT NOT NULL REFERENCES worlds(id),
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
    details         JSONB DEFAULT '{}',
    PRIMARY KEY (world_id, id)
);

CREATE TABLE hf_links (
    id           SERIAL PRIMARY KEY,
    world_id     INT NOT NULL,
    hf_id        INT NOT NULL,
    target_hf_id INT NOT NULL,
    link_type    TEXT,
    UNIQUE (world_id, hf_id, target_hf_id, link_type),
    FOREIGN KEY (world_id, hf_id) REFERENCES historical_figures(world_id, id),
    FOREIGN KEY (world_id, target_hf_id) REFERENCES historical_figures(world_id, id)
);

CREATE TABLE hf_entity_links (
    id              SERIAL PRIMARY KEY,
    world_id        INT NOT NULL,
    hf_id           INT NOT NULL,
    entity_id       INT NOT NULL,
    link_type       TEXT,
    position_name   TEXT,
    UNIQUE (world_id, hf_id, entity_id, link_type),
    FOREIGN KEY (world_id, hf_id) REFERENCES historical_figures(world_id, id),
    FOREIGN KEY (world_id, entity_id) REFERENCES entities(world_id, id)
);

CREATE TABLE hf_site_links (
    id          SERIAL PRIMARY KEY,
    world_id    INT NOT NULL,
    hf_id       INT NOT NULL,
    site_id     INT NOT NULL,
    link_type   TEXT,
    UNIQUE (world_id, hf_id, site_id, link_type),
    FOREIGN KEY (world_id, hf_id) REFERENCES historical_figures(world_id, id),
    FOREIGN KEY (world_id, site_id) REFERENCES sites(world_id, id)
);

CREATE TABLE identities (
    id          INT NOT NULL,
    world_id    INT NOT NULL REFERENCES worlds(id),
    name        TEXT,
    histfig_id  INT,
    birth_year  INT,
    birth_second INT,
    entity_id   INT,
    PRIMARY KEY (world_id, id)
);

CREATE TABLE history_events (
    id              INT NOT NULL,
    world_id        INT NOT NULL REFERENCES worlds(id),
    year            INT,
    seconds         INT,
    event_type      TEXT,
    hf_id_1         INT,
    hf_id_2         INT,
    site_id         INT,
    region_id       INT,
    entity_id_1     INT,
    entity_id_2     INT,
    artifact_id     INT,
    structure_id    INT,
    details         JSONB DEFAULT '{}',
    PRIMARY KEY (world_id, id)
);

CREATE TABLE history_event_collections (
    id              INT NOT NULL,
    world_id        INT NOT NULL REFERENCES worlds(id),
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
    PRIMARY KEY (world_id, id)
);

CREATE TABLE collection_events (
    world_id        INT NOT NULL,
    collection_id   INT NOT NULL,
    event_id        INT NOT NULL,
    PRIMARY KEY (world_id, collection_id, event_id),
    FOREIGN KEY (world_id, collection_id) REFERENCES history_event_collections(world_id, id),
    FOREIGN KEY (world_id, event_id) REFERENCES history_events(world_id, id)
);

CREATE TABLE collection_subcollections (
    world_id    INT NOT NULL,
    parent_id   INT NOT NULL,
    child_id    INT NOT NULL,
    PRIMARY KEY (world_id, parent_id, child_id),
    FOREIGN KEY (world_id, parent_id) REFERENCES history_event_collections(world_id, id),
    FOREIGN KEY (world_id, child_id) REFERENCES history_event_collections(world_id, id)
);

CREATE TABLE event_relationships (
    id          SERIAL PRIMARY KEY,
    world_id    INT NOT NULL REFERENCES worlds(id),
    event_id    INT,
    relationship TEXT,
    source_hf   INT,
    target_hf   INT,
    year        INT
);

CREATE TABLE artifacts (
    id              INT NOT NULL,
    world_id        INT NOT NULL REFERENCES worlds(id),
    name            TEXT,
    item_type       TEXT,
    item_subtype    TEXT,
    material        TEXT,
    creator_hf_id   INT,
    holder_hf_id    INT,
    site_id         INT,
    details         JSONB DEFAULT '{}',
    PRIMARY KEY (world_id, id)
);

CREATE TABLE embeddings (
    id              SERIAL PRIMARY KEY,
    entity_type     TEXT NOT NULL,
    entity_id       INT NOT NULL,
    chunk_index     INT NOT NULL DEFAULT 0,
    chunk_text      TEXT NOT NULL,
    content_hash    TEXT NOT NULL,
    embedding       vector(2560),
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- ── Indexes ─────────────────────────────────────────────────────────────────

CREATE INDEX idx_events_year ON history_events(year);
CREATE INDEX idx_events_type ON history_events(event_type);
CREATE INDEX idx_events_hf1 ON history_events(hf_id_1);
CREATE INDEX idx_events_hf2 ON history_events(hf_id_2);
CREATE INDEX idx_events_site ON history_events(site_id);
CREATE INDEX idx_events_entity1 ON history_events(entity_id_1);
CREATE INDEX idx_hf_name ON historical_figures(name);
CREATE INDEX idx_hf_race ON historical_figures(race);
CREATE INDEX idx_sites_name ON sites(name);
CREATE INDEX idx_entities_name ON entities(name);
CREATE INDEX idx_artifacts_name ON artifacts(name);
CREATE INDEX idx_hf_links_hf ON hf_links(hf_id);
CREATE INDEX idx_hf_links_target ON hf_links(target_hf_id);
CREATE INDEX idx_hf_entity_links_hf ON hf_entity_links(hf_id);
CREATE INDEX idx_hf_site_links_hf ON hf_site_links(hf_id);
CREATE INDEX idx_embeddings_entity ON embeddings(entity_type, entity_id);
CREATE INDEX idx_event_rels_source ON event_relationships(source_hf);
CREATE INDEX idx_event_rels_target ON event_relationships(target_hf);

COMMIT;
