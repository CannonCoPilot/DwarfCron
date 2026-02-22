-- Chronicler CDM Schema
-- Designed for Dwarf Fortress legends XML + DFHack RPC data
-- v2: Composite primary keys (world_id, id) for multi-world support

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
    id          INT NOT NULL,
    world_id    INT NOT NULL REFERENCES worlds(id),
    name        TEXT,
    coord_1     TEXT,
    coord_2     TEXT,
    PRIMARY KEY (world_id, id)
);

CREATE TABLE IF NOT EXISTS mountain_peaks (
    id          INT NOT NULL,
    world_id    INT NOT NULL REFERENCES worlds(id),
    name        TEXT,
    coords      TEXT,
    height      INT,
    PRIMARY KEY (world_id, id)
);

-- ─── Geography ───────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS regions (
    id          INT NOT NULL,
    world_id    INT NOT NULL REFERENCES worlds(id),
    name        TEXT,
    type        TEXT,
    coords      TEXT,
    PRIMARY KEY (world_id, id)
);

CREATE TABLE IF NOT EXISTS underground_regions (
    id          INT NOT NULL,
    world_id    INT NOT NULL REFERENCES worlds(id),
    type        TEXT,
    depth       INT,
    coords      TEXT,
    PRIMARY KEY (world_id, id)
);

CREATE TABLE IF NOT EXISTS sites (
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

CREATE TABLE IF NOT EXISTS structures (
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

CREATE TABLE IF NOT EXISTS world_constructions (
    id          INT NOT NULL,
    world_id    INT NOT NULL REFERENCES worlds(id),
    name        TEXT,
    type        TEXT,
    coords      TEXT,
    PRIMARY KEY (world_id, id)
);

-- ─── Civilizations & Organizations ───────────────────────────────────────────

CREATE TABLE IF NOT EXISTS entities (
    id          INT NOT NULL,
    world_id    INT NOT NULL REFERENCES worlds(id),
    name        TEXT,
    type        TEXT,
    race        TEXT,
    details     JSONB DEFAULT '{}',
    PRIMARY KEY (world_id, id)
);

-- ─── Historical Figures ──────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS historical_figures (
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

CREATE TABLE IF NOT EXISTS hf_links (
    id           SERIAL PRIMARY KEY,
    world_id     INT NOT NULL,
    hf_id        INT NOT NULL,
    target_hf_id INT NOT NULL,
    link_type    TEXT,
    UNIQUE (world_id, hf_id, target_hf_id, link_type),
    FOREIGN KEY (world_id, hf_id) REFERENCES historical_figures(world_id, id),
    FOREIGN KEY (world_id, target_hf_id) REFERENCES historical_figures(world_id, id)
);

CREATE TABLE IF NOT EXISTS hf_entity_links (
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

CREATE TABLE IF NOT EXISTS hf_site_links (
    id          SERIAL PRIMARY KEY,
    world_id    INT NOT NULL,
    hf_id       INT NOT NULL,
    site_id     INT NOT NULL,
    link_type   TEXT,
    UNIQUE (world_id, hf_id, site_id, link_type),
    FOREIGN KEY (world_id, hf_id) REFERENCES historical_figures(world_id, id),
    FOREIGN KEY (world_id, site_id) REFERENCES sites(world_id, id)
);

CREATE TABLE IF NOT EXISTS identities (
    id          INT NOT NULL,
    world_id    INT NOT NULL REFERENCES worlds(id),
    name        TEXT,
    histfig_id  INT,
    birth_year  INT,
    birth_second INT,
    entity_id   INT,
    PRIMARY KEY (world_id, id)
);

-- ─── Events ──────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS history_events (
    id              INT NOT NULL,
    world_id        INT NOT NULL REFERENCES worlds(id),
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
    PRIMARY KEY (world_id, id)
);

CREATE TABLE IF NOT EXISTS history_event_collections (
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

CREATE TABLE IF NOT EXISTS collection_events (
    world_id        INT NOT NULL,
    collection_id   INT NOT NULL,
    event_id        INT NOT NULL,
    PRIMARY KEY (world_id, collection_id, event_id),
    FOREIGN KEY (world_id, collection_id) REFERENCES history_event_collections(world_id, id),
    FOREIGN KEY (world_id, event_id) REFERENCES history_events(world_id, id)
);

CREATE TABLE IF NOT EXISTS collection_subcollections (
    world_id    INT NOT NULL,
    parent_id   INT NOT NULL,
    child_id    INT NOT NULL,
    PRIMARY KEY (world_id, parent_id, child_id),
    FOREIGN KEY (world_id, parent_id) REFERENCES history_event_collections(world_id, id),
    FOREIGN KEY (world_id, child_id) REFERENCES history_event_collections(world_id, id)
);

CREATE TABLE IF NOT EXISTS event_relationships (
    id          SERIAL PRIMARY KEY,
    world_id    INT NOT NULL REFERENCES worlds(id),
    event_id    INT,
    relationship TEXT,
    source_hf   INT,
    target_hf   INT,
    year        INT
);

-- ─── Artifacts ───────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS artifacts (
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

-- ─── Written Contents ───────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS written_contents (
    id              INT NOT NULL,
    world_id        INT NOT NULL REFERENCES worlds(id),
    title           TEXT,
    author_hf_id    INT,
    form            TEXT,          -- "poem", "musical composition", "guide", etc.
    type            TEXT,          -- CamelCase from legends_plus: "Poem", "MusicalComposition"
    page_start      INT,
    page_end        INT,
    styles          TEXT[],        -- style tags (merged from both XML sources)
    details         JSONB DEFAULT '{}',
    PRIMARY KEY (world_id, id)
);

CREATE INDEX IF NOT EXISTS idx_written_contents_author ON written_contents(author_hf_id);

-- ─── Historical Eras ───────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS historical_eras (
    world_id        INT NOT NULL REFERENCES worlds(id),
    name            TEXT NOT NULL,
    start_year      INT,
    PRIMARY KEY (world_id, name)
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
    world_id        INT NOT NULL REFERENCES worlds(id),
    event_type      TEXT NOT NULL,
    old_value       JSONB,
    new_value       JSONB,
    game_year       INT,
    game_tick       INT,
    detected_at     TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_unit_events_unit ON unit_events(unit_id);
CREATE INDEX IF NOT EXISTS idx_unit_events_type ON unit_events(event_type);
CREATE INDEX IF NOT EXISTS idx_unit_events_time ON unit_events(detected_at);

-- ── Live Sync: Poll Cycle Snapshots ─────────────────────────────────
CREATE TABLE IF NOT EXISTS sync_snapshots (
    id              SERIAL PRIMARY KEY,
    world_id        INT NOT NULL REFERENCES worlds(id),
    unit_count      INT NOT NULL,
    event_count     INT DEFAULT 0,
    game_year       INT,
    game_tick       INT,
    synced_at       TIMESTAMPTZ DEFAULT now()
);

-- ── Live Data: Game Reports (announcements, combat logs) ────────────
CREATE TABLE IF NOT EXISTS game_reports (
    id              SERIAL PRIMARY KEY,
    world_id        INT NOT NULL REFERENCES worlds(id),
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
    world_id        INT NOT NULL REFERENCES worlds(id),
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
    world_id        INT NOT NULL REFERENCES worlds(id),
    probe_name      TEXT NOT NULL,
    data            JSONB NOT NULL,
    game_year       INT,
    game_tick       INT,
    captured_at     TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_lua_probes_world ON lua_probes(world_id);
CREATE INDEX IF NOT EXISTS idx_lua_probes_name ON lua_probes(probe_name);
