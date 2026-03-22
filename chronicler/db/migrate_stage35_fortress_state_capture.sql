-- Stage 3.5: Comprehensive Fortress State Capture
-- Migration V5: 6 new tables + game_reports enhancement
-- Date: 2026-03-20

-- ═══════════════════════════════════════════════════════════════════════
-- 1. Enhance game_reports with category + structured combat fields
-- ═══════════════════════════════════════════════════════════════════════

ALTER TABLE game_reports ADD COLUMN IF NOT EXISTS category TEXT;
ALTER TABLE game_reports ADD COLUMN IF NOT EXISTS attacker_unit_id INT;
ALTER TABLE game_reports ADD COLUMN IF NOT EXISTS defender_unit_id INT;
ALTER TABLE game_reports ADD COLUMN IF NOT EXISTS body_part TEXT;
ALTER TABLE game_reports ADD COLUMN IF NOT EXISTS attack_type TEXT;
ALTER TABLE game_reports ADD COLUMN IF NOT EXISTS weapon TEXT;
ALTER TABLE game_reports ADD COLUMN IF NOT EXISTS result_flags JSONB DEFAULT '{}';

CREATE INDEX IF NOT EXISTS idx_game_reports_category
    ON game_reports(world_id, category);

-- ═══════════════════════════════════════════════════════════════════════
-- 2. High-frequency fortress state snapshots (complement season-based fortress_state)
-- ═══════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS fortress_state_snapshots (
    id                     SERIAL PRIMARY KEY,
    world_id               INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    tick                   BIGINT NOT NULL,
    year                   INT NOT NULL,
    season                 TEXT,
    population             INT,
    military_count         INT,
    food_stocks            INT,
    drink_stocks           INT,
    wealth                 BIGINT,
    happiness_distribution JSONB,
    threats                JSONB,
    captured_at            TIMESTAMPTZ DEFAULT now(),
    UNIQUE(world_id, tick)
);

CREATE INDEX IF NOT EXISTS idx_fss_world_tick
    ON fortress_state_snapshots(world_id, tick);

-- ═══════════════════════════════════════════════════════════════════════
-- 3. Hostile entity tracking (periodic threat population)
-- ═══════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS threat_tracking (
    id              SERIAL PRIMARY KEY,
    world_id        INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    tick            BIGINT NOT NULL,
    hostile_count   INT DEFAULT 0,
    undead_count    INT DEFAULT 0,
    invader_count   INT DEFAULT 0,
    megabeast_count INT DEFAULT 0,
    threat_details  JSONB,
    UNIQUE(world_id, tick)
);

CREATE INDEX IF NOT EXISTS idx_threat_world_tick
    ON threat_tracking(world_id, tick);

-- ═══════════════════════════════════════════════════════════════════════
-- 4. Character development tracking (delta-based per-unit snapshots)
-- ═══════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS character_arcs (
    id                         SERIAL PRIMARY KEY,
    world_id                   INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    unit_id                    INT NOT NULL,
    tick                       BIGINT NOT NULL,
    year                       INT NOT NULL,
    stress_level               INT,
    happiness                  TEXT,
    skill_snapshot             JSONB,
    profession                 TEXT,
    squad_id                   INT,
    notable_events_since_last  JSONB,
    UNIQUE(world_id, unit_id, tick)
);

CREATE INDEX IF NOT EXISTS idx_arcs_world_unit
    ON character_arcs(world_id, unit_id);
CREATE INDEX IF NOT EXISTS idx_arcs_world_tick
    ON character_arcs(world_id, tick);

-- ═══════════════════════════════════════════════════════════════════════
-- 5. Environmental state (fortress conditions)
-- ═══════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS environmental_state (
    id                  SERIAL PRIMARY KEY,
    world_id            INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    tick                BIGINT NOT NULL,
    year                INT NOT NULL,
    season              TEXT NOT NULL,
    temperature         INT,
    weather             TEXT,
    fortress_depth      INT,
    features_discovered JSONB,
    UNIQUE(world_id, tick)
);

CREATE INDEX IF NOT EXISTS idx_env_world_tick
    ON environmental_state(world_id, tick);

-- ═══════════════════════════════════════════════════════════════════════
-- 6. Death narrative enrichment (full incident chain per death)
-- ═══════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS death_narratives (
    id                 SERIAL PRIMARY KEY,
    world_id           INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    unit_id            INT NOT NULL,
    hf_id              INT,
    tick               BIGINT NOT NULL,
    year               INT NOT NULL,
    cause              TEXT NOT NULL,
    killer_unit_id     INT,
    killer_race        TEXT,
    weapon             TEXT,
    body_part          TEXT,
    combat_report_ids  JSONB,
    witness_unit_ids   JSONB,
    location           TEXT,
    narrative_text     TEXT,
    UNIQUE(world_id, unit_id, tick)
);

CREATE INDEX IF NOT EXISTS idx_death_narr_world
    ON death_narratives(world_id, year);

-- ═══════════════════════════════════════════════════════════════════════
-- 7. Session boundary markers (chapter breaks)
-- ═══════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS session_markers (
    id                       SERIAL PRIMARY KEY,
    world_id                 INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    tick                     BIGINT NOT NULL,
    event_type               TEXT NOT NULL,
    fortress_state_at_marker JSONB,
    UNIQUE(world_id, tick, event_type)
);

CREATE INDEX IF NOT EXISTS idx_session_world_tick
    ON session_markers(world_id, tick);
