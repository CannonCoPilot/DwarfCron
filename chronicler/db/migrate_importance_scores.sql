-- Importance score migration
-- Adds importance_score columns to historical_figures, sites, and artifacts
-- Run against existing databases to add the columns

ALTER TABLE historical_figures ADD COLUMN IF NOT EXISTS importance_score FLOAT DEFAULT 0.0;
ALTER TABLE sites ADD COLUMN IF NOT EXISTS importance_score FLOAT DEFAULT 0.0;
ALTER TABLE artifacts ADD COLUMN IF NOT EXISTS importance_score FLOAT DEFAULT 0.0;

CREATE INDEX IF NOT EXISTS idx_hf_importance ON historical_figures(world_id, importance_score DESC);
CREATE INDEX IF NOT EXISTS idx_sites_importance ON sites(world_id, importance_score DESC);
CREATE INDEX IF NOT EXISTS idx_artifacts_importance ON artifacts(world_id, importance_score DESC);
