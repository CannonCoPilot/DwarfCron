-- Stage 3.0: CDM Schema Fixes — 4 APPEND violations + supplementary columns
-- Run once against live chronicler DB before Stage 3.1 (Bridge Enhancements)

BEGIN;

-- ═══ V1: Units PK fix — single-column → composite (world_id, id) ═══════════
-- The units table was the only live-data table with a non-composite PK,
-- breaking multi-world isolation and ON CONFLICT semantics.

ALTER TABLE units DROP CONSTRAINT units_pkey;
ALTER TABLE units ALTER COLUMN world_id SET NOT NULL;
ALTER TABLE units ADD PRIMARY KEY (world_id, id);

-- ═══ V2: Unit Events reconciliation columns ════════════════════════════════
-- Needed for Stage 3.1 event reconciliation: linking live unit_events
-- back to legends history_events after export.

ALTER TABLE unit_events ADD COLUMN IF NOT EXISTS reconciled_event_id INTEGER;
ALTER TABLE unit_events ADD COLUMN IF NOT EXISTS reconciled_at TIMESTAMPTZ;

-- ═══ V3: Entity-Entity Links table (new) ═══════════════════════════════════
-- Models entity-to-entity relationships (PARENT, CHILD, WAR, TRADE, etc.)
-- that were previously flattened into entities.details JSONB.

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

-- ═══ V4: Entity-Site Links table (new) ═════════════════════════════════════
-- Models entity-to-site relationships (SEAT_OF_POWER, OCCUPIED, TRADED, etc.)
-- replacing ad-hoc owner_entity_id lookups with proper link records.

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

-- ═══ Supplementary columns (needed by Stage 3.1 bridge) ═══════════════════

ALTER TABLE hf_links ADD COLUMN IF NOT EXISTS strength SMALLINT;
ALTER TABLE sites ADD COLUMN IF NOT EXISTS founded_year INT;
ALTER TABLE sites ADD COLUMN IF NOT EXISTS founder_entity_id INT;
ALTER TABLE history_events ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'legends_xml';

-- ═══ Indexes ═══════════════════════════════════════════════════════════════

CREATE INDEX IF NOT EXISTS idx_eel_target ON entity_entity_links(world_id, target_entity_id);
CREATE INDEX IF NOT EXISTS idx_esl_site ON entity_site_links(world_id, site_id);
CREATE INDEX IF NOT EXISTS idx_unit_events_reconciled ON unit_events(reconciled_event_id) WHERE reconciled_event_id IS NOT NULL;

COMMIT;
