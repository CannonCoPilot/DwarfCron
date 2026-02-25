-- Phase 1: Data Foundation — CDM Schema Extensions
-- Migration for Stage 1.1 tasks (1.1.1 through 1.1.9)
-- Date: 2026-02-25
-- Prerequisites: schema.sql v2 (composite PKs) already applied

BEGIN;

-- ── Task 1.1.1: art_forms table ──────────────────────────────────────────────
-- Three DF XML sections (dance_forms, musical_forms, poetic_forms) unified
-- into one table with form_type discriminator.

CREATE TABLE IF NOT EXISTS art_forms (
    world_id    INT NOT NULL REFERENCES worlds(id),
    id          INT NOT NULL,
    name        TEXT,
    form_type   TEXT NOT NULL,  -- 'dance', 'musical', 'poetic'
    description TEXT,
    details     JSONB DEFAULT '{}',
    PRIMARY KEY (world_id, id)
);

CREATE INDEX IF NOT EXISTS idx_art_forms_type ON art_forms(world_id, form_type);
CREATE INDEX IF NOT EXISTS idx_art_forms_name ON art_forms(world_id, name);

-- ── Task 1.1.2: rivers table ─────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS rivers (
    world_id     INT NOT NULL REFERENCES worlds(id),
    id           INT NOT NULL,
    name         TEXT,
    name_english TEXT,
    path         TEXT,      -- pipe-delimited coordinate pairs for river path
    end_type     TEXT,      -- ocean, lake, underground, etc.
    details      JSONB DEFAULT '{}',
    PRIMARY KEY (world_id, id)
);

CREATE INDEX IF NOT EXISTS idx_rivers_name ON rivers(world_id, name);

-- ── Task 1.1.3: mountain_peaks.is_volcano ────────────────────────────────────

ALTER TABLE mountain_peaks ADD COLUMN IF NOT EXISTS is_volcano BOOLEAN DEFAULT FALSE;

-- ── Task 1.1.4: identities table extensions ──────────────────────────────────
-- Existing: id, world_id, name, histfig_id, birth_year, birth_second, entity_id
-- Adding: race, caste, profession, details JSONB

ALTER TABLE identities ADD COLUMN IF NOT EXISTS race TEXT;
ALTER TABLE identities ADD COLUMN IF NOT EXISTS caste TEXT;
ALTER TABLE identities ADD COLUMN IF NOT EXISTS profession TEXT;
ALTER TABLE identities ADD COLUMN IF NOT EXISTS details JSONB DEFAULT '{}';

-- ── Task 1.1.5: historical_figures field extensions ──────────────────────────
-- Current: 22 columns. Adding ~10 new columns for high-priority HF data.

ALTER TABLE historical_figures
    ADD COLUMN IF NOT EXISTS spheres TEXT[],
    ADD COLUMN IF NOT EXISTS goals JSONB DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS skills JSONB DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS kills JSONB DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS whereabouts JSONB DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS entity_reputations JSONB DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS intrigue_actors JSONB DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS used_identities JSONB DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS journey_pets JSONB DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS holds_artifact INTEGER[];

CREATE INDEX IF NOT EXISTS idx_hf_spheres
    ON historical_figures USING gin(spheres);

-- ── Task 1.1.6: active_interactions for supernatural detection ───────────────

ALTER TABLE historical_figures
    ADD COLUMN IF NOT EXISTS active_interactions TEXT[];

CREATE INDEX IF NOT EXISTS idx_hf_interactions
    ON historical_figures USING gin(active_interactions);

-- ── Task 1.1.7: worldgen_snapshots table ─────────────────────────────────────
-- For future worldgen monitoring (P2 — schema created now, populated later)

CREATE TABLE IF NOT EXISTS worldgen_snapshots (
    id          SERIAL PRIMARY KEY,
    world_id    INT NOT NULL REFERENCES worlds(id),
    phase       TEXT NOT NULL,        -- worldgen phase name (12 states)
    progress_pct FLOAT,
    year        INT,
    pop_count   INT,
    site_count  INT,
    hf_count    INT,
    entity_count INT,
    event_count INT,
    data        JSONB DEFAULT '{}',   -- full snapshot data
    captured_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_worldgen_snapshots_world
    ON worldgen_snapshots(world_id);

-- ── Task 1.1.8: world_modpacks table ─────────────────────────────────────────
-- Tracks which mods were active when a world was generated/played

CREATE TABLE IF NOT EXISTS world_modpacks (
    id          SERIAL PRIMARY KEY,
    world_id    INT NOT NULL REFERENCES worlds(id),
    name        TEXT NOT NULL,
    version     TEXT,
    source      TEXT,         -- 'steam_workshop', 'manual', 'dfhack'
    active      BOOLEAN DEFAULT TRUE,
    details     JSONB DEFAULT '{}',
    recorded_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_world_modpacks_world
    ON world_modpacks(world_id);

-- ── Task 1.1.9: event_entity_xref table ──────────────────────────────────────
-- Cross-reference index: which entities are mentioned in which events.
-- Populated by post-parse processing pipeline (Stage 1.3, Step 7).

CREATE TABLE IF NOT EXISTS event_entity_xref (
    world_id    INT NOT NULL,
    event_id    INT NOT NULL,
    entity_type TEXT NOT NULL,   -- 'hf', 'entity', 'site', 'artifact', 'region'
    entity_id   INT NOT NULL,
    role        TEXT,            -- 'subject', 'object', 'location', 'participant'
    PRIMARY KEY (world_id, event_id, entity_type, entity_id),
    FOREIGN KEY (world_id, event_id) REFERENCES history_events(world_id, id)
);

CREATE INDEX IF NOT EXISTS idx_event_entity_xref_entity
    ON event_entity_xref(world_id, entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_event_entity_xref_event
    ON event_entity_xref(world_id, event_id);

COMMIT;
