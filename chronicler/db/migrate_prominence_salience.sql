-- Migration: Add prominence_score and salience_score to HFs, entities, artifacts
-- Date: 2026-03-02
-- These columns supersede importance_score for display and sorting.
-- importance_score is retained as the base computation; prominence and salience
-- are derived from it in scoring.py.

-- Historical Figures: prominence = structural importance, salience = narrative interest
ALTER TABLE historical_figures ADD COLUMN IF NOT EXISTS prominence_score REAL DEFAULT 0;
ALTER TABLE historical_figures ADD COLUMN IF NOT EXISTS salience_score REAL DEFAULT 0;

-- Entities: prominence = IDF event score, salience = conflict participation
ALTER TABLE entities ADD COLUMN IF NOT EXISTS prominence_score REAL DEFAULT 0;
ALTER TABLE entities ADD COLUMN IF NOT EXISTS salience_score REAL DEFAULT 0;

-- Artifacts: prominence = event involvement, salience = holder/narrative activity
ALTER TABLE artifacts ADD COLUMN IF NOT EXISTS prominence_score REAL DEFAULT 0;
ALTER TABLE artifacts ADD COLUMN IF NOT EXISTS salience_score REAL DEFAULT 0;

-- Indexes for sorting by prominence (replaces importance-based sorting)
CREATE INDEX IF NOT EXISTS idx_hf_prominence ON historical_figures(world_id, prominence_score DESC);
CREATE INDEX IF NOT EXISTS idx_entities_prominence ON entities(world_id, prominence_score DESC);
CREATE INDEX IF NOT EXISTS idx_artifacts_prominence ON artifacts(world_id, prominence_score DESC);
