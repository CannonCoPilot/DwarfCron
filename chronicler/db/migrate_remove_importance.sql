-- Migration: Remove importance_score, add scoring to new entity types
-- Date: 2026-03-02
-- Context: Unified Scoring v2.0 — two-score architecture (prominence + salience only)
-- Supersedes: migrate_importance_scores.sql, migrate_prominence_salience.sql

-- ── Step 1: Drop importance_score from 4 tables ──────────────────────────

-- Drop indexes first (they reference the columns)
DROP INDEX IF EXISTS idx_hf_importance;
DROP INDEX IF EXISTS idx_sites_importance;
DROP INDEX IF EXISTS idx_artifacts_importance;
DROP INDEX IF EXISTS idx_entities_importance;

-- Drop columns
ALTER TABLE historical_figures DROP COLUMN IF EXISTS importance_score;
ALTER TABLE entities DROP COLUMN IF EXISTS importance_score;
ALTER TABLE sites DROP COLUMN IF EXISTS importance_score;
ALTER TABLE artifacts DROP COLUMN IF EXISTS importance_score;

-- ── Step 2: Add scoring columns to 4 new tables ─────────────────────────

ALTER TABLE structures ADD COLUMN IF NOT EXISTS prominence_score REAL DEFAULT 0;
ALTER TABLE structures ADD COLUMN IF NOT EXISTS salience_score REAL DEFAULT 0;

ALTER TABLE history_event_collections ADD COLUMN IF NOT EXISTS prominence_score REAL DEFAULT 0;
ALTER TABLE history_event_collections ADD COLUMN IF NOT EXISTS salience_score REAL DEFAULT 0;

ALTER TABLE underground_regions ADD COLUMN IF NOT EXISTS prominence_score REAL DEFAULT 0;
ALTER TABLE underground_regions ADD COLUMN IF NOT EXISTS salience_score REAL DEFAULT 0;

ALTER TABLE mountain_peaks ADD COLUMN IF NOT EXISTS prominence_score REAL DEFAULT 0;
ALTER TABLE mountain_peaks ADD COLUMN IF NOT EXISTS salience_score REAL DEFAULT 0;

-- ── Step 3: Add prominence index for sites (was using importance) ────────

CREATE INDEX IF NOT EXISTS idx_sites_prominence ON sites(world_id, prominence_score DESC);
