-- Stage 3.3: Knowledge Horizon
-- Migration: Creates knowledge_horizon table and visible_* views
-- Date: 2026-03-18

-- ── Knowledge Horizon control table ──────────────────────────────────

CREATE TABLE IF NOT EXISTS knowledge_horizon (
    world_id    INTEGER NOT NULL,
    entity_type TEXT    NOT NULL,  -- 'hf', 'entity', 'site', 'region', 'artifact'
    entity_id   INTEGER NOT NULL,
    visible     BOOLEAN DEFAULT TRUE,
    reason      TEXT,              -- why this entity is visible (debugging)
    revealed_at TIMESTAMPTZ DEFAULT NOW(),
    revealed_by TEXT,              -- event or mechanism that revealed this
    PRIMARY KEY (world_id, entity_type, entity_id)
);

CREATE INDEX IF NOT EXISTS idx_kh_visible
    ON knowledge_horizon (world_id, entity_type) WHERE visible = TRUE;

CREATE INDEX IF NOT EXISTS idx_kh_entity_lookup
    ON knowledge_horizon (world_id, entity_id, entity_type);

-- ── Visible views (KH-filtered) ─────────────────────────────────────

CREATE OR REPLACE VIEW visible_historical_figures AS
SELECT hf.*
FROM historical_figures hf
JOIN knowledge_horizon kh
    ON kh.world_id = hf.world_id
   AND kh.entity_type = 'hf'
   AND kh.entity_id = hf.id
   AND kh.visible = TRUE;

CREATE OR REPLACE VIEW visible_entities AS
SELECT e.*
FROM entities e
JOIN knowledge_horizon kh
    ON kh.world_id = e.world_id
   AND kh.entity_type = 'entity'
   AND kh.entity_id = e.id
   AND kh.visible = TRUE;

CREATE OR REPLACE VIEW visible_sites AS
SELECT s.*
FROM sites s
JOIN knowledge_horizon kh
    ON kh.world_id = s.world_id
   AND kh.entity_type = 'site'
   AND kh.entity_id = s.id
   AND kh.visible = TRUE;

CREATE OR REPLACE VIEW visible_regions AS
SELECT r.*
FROM regions r
JOIN knowledge_horizon kh
    ON kh.world_id = r.world_id
   AND kh.entity_type = 'region'
   AND kh.entity_id = r.id
   AND kh.visible = TRUE;

CREATE OR REPLACE VIEW visible_artifacts AS
SELECT a.*
FROM artifacts a
JOIN knowledge_horizon kh
    ON kh.world_id = a.world_id
   AND kh.entity_type = 'artifact'
   AND kh.entity_id = a.id
   AND kh.visible = TRUE;

-- Events visible if ANY referenced entity is visible
CREATE OR REPLACE VIEW visible_events AS
SELECT DISTINCT he.*
FROM history_events he
JOIN event_entity_xref xref
    ON xref.world_id = he.world_id
   AND xref.event_id = he.id
JOIN knowledge_horizon kh
    ON kh.world_id = xref.world_id
   AND kh.entity_type = xref.entity_type
   AND kh.entity_id = xref.entity_id
   AND kh.visible = TRUE;
