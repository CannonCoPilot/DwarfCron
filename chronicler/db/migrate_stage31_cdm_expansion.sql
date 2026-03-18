-- Stage 3.1 CDM Expansion Migration
-- Adds 7 new tables for memory-only structures + live fortress data
-- Adds 3 new columns on existing tables
-- Date: 2026-03-17

BEGIN;

-- ═══════════════════════════════════════════════════════════════════════════════
-- NEW TABLES
-- ═══════════════════════════════════════════════════════════════════════════════

-- ─── Belief Systems (memory-only, ~1,502 records) ──────────────────────────────
-- Religious belief systems: deity worship, creation myths, cultural values
-- Source: df.global.world.belief_systems.all (NOT in legends XML)

CREATE TABLE IF NOT EXISTS belief_systems (
    world_id         INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    id               INT NOT NULL,
    deities          INTEGER[],
    worship_levels   INTEGER[],
    cultural_values  JSONB DEFAULT '{}',
    details          JSONB DEFAULT '{}',
    PRIMARY KEY (world_id, id)
);

CREATE INDEX IF NOT EXISTS idx_belief_systems_world ON belief_systems(world_id);

-- ─── Cultural Identities (memory-only, ~1,721 records) ────────────────────────
-- Ethics/values per identity — links to units via cultural_identity field
-- Source: df.global.world.cultural_identities.all (NOT in legends XML)

CREATE TABLE IF NOT EXISTS cultural_identities (
    world_id         INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    id               INT NOT NULL,
    site_id          INT,
    civ_id           INT,
    ethics           JSONB DEFAULT '{}',
    cultural_values  JSONB DEFAULT '{}',
    details          JSONB DEFAULT '{}',
    PRIMARY KEY (world_id, id),
    FOREIGN KEY (world_id, site_id) REFERENCES sites(world_id, id) ON DELETE SET NULL,
    FOREIGN KEY (world_id, civ_id) REFERENCES entities(world_id, id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_cultural_identities_civ ON cultural_identities(world_id, civ_id);

-- ─── Military Squads (~245 records) ───────────────────────────────────────────
-- Military squad composition, leader, orders
-- Source: bridge v8 get_squads() (already extracted, just needs CDM table)

CREATE TABLE IF NOT EXISTS squads (
    world_id         INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    id               INT NOT NULL,
    entity_id        INT,
    name             TEXT,
    name_english     TEXT,
    alias            TEXT,
    leader_hf_id     INT,
    position_count   INT DEFAULT 0,
    members          JSONB DEFAULT '[]',
    details          JSONB DEFAULT '{}',
    last_synced_at   TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (world_id, id),
    FOREIGN KEY (world_id, entity_id) REFERENCES entities(world_id, id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_squads_entity ON squads(world_id, entity_id);

-- ─── Occupations (memory-only, ~1,584 records) ────────────────────────────────
-- HF roles at specific locations: tavern keepers, scholars, performers
-- Source: df.global.world.occupations.all (NOT in legends XML)

CREATE TABLE IF NOT EXISTS occupations (
    world_id         INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    id               INT NOT NULL,
    occupation_type  TEXT NOT NULL,
    hf_id            INT,
    unit_id          INT,
    site_id          INT,
    location_id      INT,
    entity_id        INT,
    details          JSONB DEFAULT '{}',
    PRIMARY KEY (world_id, id),
    FOREIGN KEY (world_id, hf_id) REFERENCES historical_figures(world_id, id) ON DELETE SET NULL,
    FOREIGN KEY (world_id, site_id) REFERENCES sites(world_id, id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_occupations_hf ON occupations(world_id, hf_id);
CREATE INDEX IF NOT EXISTS idx_occupations_site ON occupations(world_id, site_id);

-- ─── Fortress State (append-only progression snapshots, 1/season) ─────────────
-- Fortress progression tracking: rank, infiltrators, invasions, wealth
-- Source: df.global.plotinfo (fortress mode only)

CREATE TABLE IF NOT EXISTS fortress_state (
    id               SERIAL PRIMARY KEY,
    world_id         INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    site_id          INT NOT NULL,
    fortress_age     INT,
    fortress_rank    INT,
    population       INT,
    king_arrived     BOOLEAN DEFAULT FALSE,
    infiltrators     INTEGER[],
    invasion_count   INT DEFAULT 0,
    wealth_created   BIGINT,
    wealth_imported  BIGINT,
    wealth_exported  BIGINT,
    game_year        INT,
    game_tick        INT,
    details          JSONB DEFAULT '{}',
    captured_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_fortress_state_world ON fortress_state(world_id);
CREATE INDEX IF NOT EXISTS idx_fortress_state_time ON fortress_state(captured_at DESC);

-- ─── Interaction Instances (memory-only, ~12 records, HIGH narrative value) ───
-- Active curses, vampirism, lycanthropy, necromancy
-- Source: df.global.world.interaction_instances.all (NOT in legends XML)

CREATE TABLE IF NOT EXISTS interaction_instances (
    world_id         INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    id               INT NOT NULL,
    interaction_type TEXT,
    source_hf_id     INT,
    affected_units   INTEGER[],
    details          JSONB DEFAULT '{}',
    PRIMARY KEY (world_id, id)
);

CREATE INDEX IF NOT EXISTS idx_interaction_inst_world ON interaction_instances(world_id);

-- ─── Agreements (memory-only, ~3,410 records, LOW priority) ───────────────────
-- Treaties, peace deals, tribute, vassalage
-- Source: df.global.world.agreements.all (NOT in legends XML)

CREATE TABLE IF NOT EXISTS agreements (
    world_id         INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    id               INT NOT NULL,
    agreement_type   TEXT,
    parties          JSONB DEFAULT '[]',
    flags            JSONB DEFAULT '{}',
    map_x            INT,
    map_y            INT,
    details          JSONB DEFAULT '{}',
    PRIMARY KEY (world_id, id)
);

CREATE INDEX IF NOT EXISTS idx_agreements_world ON agreements(world_id);

-- ═══════════════════════════════════════════════════════════════════════════════
-- ALTER EXISTING TABLES
-- ═══════════════════════════════════════════════════════════════════════════════

-- HF ↔ Unit bidirectional link (currently only unit→HF via units.hist_fig_id)
ALTER TABLE historical_figures ADD COLUMN IF NOT EXISTS unit_id INT;
CREATE INDEX IF NOT EXISTS idx_hf_unit_id
    ON historical_figures(world_id, unit_id) WHERE unit_id IS NOT NULL;

-- Family lineage root pointer
ALTER TABLE historical_figures ADD COLUMN IF NOT EXISTS family_head_id INT;

-- Region enrichment: fauna, evil flags, flora
ALTER TABLE regions ADD COLUMN IF NOT EXISTS details JSONB DEFAULT '{}';

COMMIT;
