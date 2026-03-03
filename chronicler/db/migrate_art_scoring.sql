-- Migration: Add art scoring columns
-- Date: 2026-03-02
-- Adds prominence_score/salience_score to written_contents and art_forms,
-- and is_author/is_auteur flags to historical_figures.

-- Written contents: prominence = copy spread, salience = quality × style
ALTER TABLE written_contents ADD COLUMN IF NOT EXISTS prominence_score REAL DEFAULT 0;
ALTER TABLE written_contents ADD COLUMN IF NOT EXISTS salience_score REAL DEFAULT 0;

-- Art forms: prominence = unique authors, salience = avg work quality
ALTER TABLE art_forms ADD COLUMN IF NOT EXISTS prominence_score REAL DEFAULT 0;
ALTER TABLE art_forms ADD COLUMN IF NOT EXISTS salience_score REAL DEFAULT 0;

-- Historical figures: author/auteur flags for art-based prominence bonuses
ALTER TABLE historical_figures ADD COLUMN IF NOT EXISTS is_author BOOLEAN DEFAULT FALSE;
ALTER TABLE historical_figures ADD COLUMN IF NOT EXISTS is_auteur BOOLEAN DEFAULT FALSE;

-- Indexes for sorting
CREATE INDEX IF NOT EXISTS idx_written_contents_prominence ON written_contents(world_id, prominence_score DESC);
CREATE INDEX IF NOT EXISTS idx_art_forms_prominence ON art_forms(world_id, prominence_score DESC);
