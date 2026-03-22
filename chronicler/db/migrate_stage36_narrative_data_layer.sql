-- Stage 3.6: Narrative Data Layer
-- Migration V6: 7 new tables + indexes
-- Date: 2026-03-20

-- ═══════════════════════════════════════════════════════════════════════
-- 1. Narrative events — history_events enriched with storytelling metadata
-- ═══════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS narrative_events (
    id              SERIAL PRIMARY KEY,
    world_id        INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    event_id        INT NOT NULL,
    narrative_weight FLOAT DEFAULT 0,
    drama_score     FLOAT DEFAULT 0,
    irony_flags     JSONB,
    emotional_tone  TEXT,
    UNIQUE(world_id, event_id)
);

CREATE INDEX IF NOT EXISTS idx_narr_events_world
    ON narrative_events(world_id, narrative_weight DESC);

-- ═══════════════════════════════════════════════════════════════════════
-- 2. Causal links — cause → effect relationships between events
-- ═══════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS event_causal_links (
    id              SERIAL PRIMARY KEY,
    world_id        INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    cause_event_id  INT NOT NULL,
    effect_event_id INT NOT NULL,
    link_type       TEXT NOT NULL,
    confidence      FLOAT DEFAULT 0.5,
    UNIQUE(world_id, cause_event_id, effect_event_id)
);

CREATE INDEX IF NOT EXISTS idx_causal_cause
    ON event_causal_links(world_id, cause_event_id);
CREATE INDEX IF NOT EXISTS idx_causal_effect
    ON event_causal_links(world_id, effect_event_id);

-- ═══════════════════════════════════════════════════════════════════════
-- 3. Narrative arcs — detected story threads
-- ═══════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS narrative_arcs (
    id              SERIAL PRIMARY KEY,
    world_id        INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    arc_type        TEXT NOT NULL,
    title           TEXT,
    start_tick      BIGINT NOT NULL,
    end_tick        BIGINT,
    key_events      JSONB NOT NULL,
    characters      JSONB,
    resolution      TEXT,
    dramatic_weight FLOAT DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_arcs_world_type
    ON narrative_arcs(world_id, arc_type);

-- ═══════════════════════════════════════════════════════════════════════
-- 4. Event summaries — pre-computed text at multiple granularities
-- ═══════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS event_summaries (
    id              SERIAL PRIMARY KEY,
    world_id        INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    scope           TEXT NOT NULL,
    scope_id        INT,
    granularity     TEXT NOT NULL,
    summary_text    TEXT NOT NULL,
    key_events      JSONB,
    generated_at    TIMESTAMPTZ DEFAULT now(),
    UNIQUE(world_id, scope, scope_id, granularity)
);

CREATE INDEX IF NOT EXISTS idx_summaries_scope
    ON event_summaries(world_id, scope, scope_id);

-- ═══════════════════════════════════════════════════════════════════════
-- 5. Character narratives — pre-computed character profiles
-- ═══════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS character_narratives (
    id                  SERIAL PRIMARY KEY,
    world_id            INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    unit_id             INT,
    hf_id               INT,
    character_name      TEXT NOT NULL,
    role_description    TEXT,
    arc_summary         TEXT,
    key_moments         JSONB,
    personality_voice   TEXT,
    ironic_dimensions   JSONB,
    generated_at        TIMESTAMPTZ DEFAULT now()
);

-- COALESCE-based uniqueness: one row per (world, unit OR hf)
CREATE UNIQUE INDEX IF NOT EXISTS idx_char_narr_unique
    ON character_narratives(world_id, COALESCE(unit_id, -1), COALESCE(hf_id, -1));

CREATE INDEX IF NOT EXISTS idx_char_narr_world
    ON character_narratives(world_id);

-- ═══════════════════════════════════════════════════════════════════════
-- 6. Event clusters — temporally grouped related events
-- ═══════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS event_clusters (
    id              SERIAL PRIMARY KEY,
    world_id        INT NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    cluster_type    TEXT NOT NULL,
    start_tick      BIGINT NOT NULL,
    end_tick        BIGINT NOT NULL,
    event_ids       JSONB NOT NULL,
    summary         TEXT,
    UNIQUE(world_id, cluster_type, start_tick)
);

CREATE INDEX IF NOT EXISTS idx_clusters_world
    ON event_clusters(world_id, start_tick);
