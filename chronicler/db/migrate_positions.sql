-- Entity position extraction migration
-- Run against existing chronicler databases to add position tables
-- Idempotent: safe to run multiple times

-- Position definitions per entity (from legends_plus <entity_position>)
CREATE TABLE IF NOT EXISTS entity_positions (
    id              SERIAL PRIMARY KEY,
    world_id        INT NOT NULL,
    entity_id       INT NOT NULL,
    position_id     INT NOT NULL,
    name            TEXT,
    name_male       TEXT,
    name_female     TEXT,
    spouse          TEXT,
    spouse_male     TEXT,
    spouse_female   TEXT,
    UNIQUE (world_id, entity_id, position_id),
    FOREIGN KEY (world_id, entity_id) REFERENCES entities(world_id, id)
);

CREATE INDEX IF NOT EXISTS idx_entity_positions_entity
    ON entity_positions(world_id, entity_id);

-- Who held which position, when (from legends <entity_position_link> +
-- <entity_former_position_link> + legends_plus <entity_position_assignment>)
CREATE TABLE IF NOT EXISTS hf_position_links (
    id              SERIAL PRIMARY KEY,
    world_id        INT NOT NULL,
    hf_id           INT NOT NULL,
    entity_id       INT NOT NULL,
    position_id     INT NOT NULL,
    start_year      INT,
    end_year        INT,
    UNIQUE (world_id, hf_id, entity_id, position_id, start_year),
    FOREIGN KEY (world_id, hf_id) REFERENCES historical_figures(world_id, id),
    FOREIGN KEY (world_id, entity_id) REFERENCES entities(world_id, id)
);

CREATE INDEX IF NOT EXISTS idx_hf_position_links_hf
    ON hf_position_links(world_id, hf_id);
CREATE INDEX IF NOT EXISTS idx_hf_position_links_entity
    ON hf_position_links(world_id, entity_id);
CREATE INDEX IF NOT EXISTS idx_hf_position_links_current
    ON hf_position_links(world_id, entity_id) WHERE end_year IS NULL;
-- Partial unique index: prevent duplicate active positions with NULL start_year
CREATE UNIQUE INDEX IF NOT EXISTS idx_hf_position_links_null_start_dedup
    ON hf_position_links(world_id, hf_id, entity_id, position_id) WHERE start_year IS NULL;
