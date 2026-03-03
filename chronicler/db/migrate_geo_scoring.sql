-- Migration: Add evilness + salience/prominence scoring columns to geo tables
-- Date: 2026-02-28

-- Regions: add evilness (parsed from legends_plus.xml) + scoring columns
ALTER TABLE regions ADD COLUMN IF NOT EXISTS evilness TEXT;
ALTER TABLE regions ADD COLUMN IF NOT EXISTS salience_score REAL DEFAULT 0;
ALTER TABLE regions ADD COLUMN IF NOT EXISTS prominence_score REAL DEFAULT 0;

-- Rivers: add scoring columns
ALTER TABLE rivers ADD COLUMN IF NOT EXISTS salience_score REAL DEFAULT 0;
ALTER TABLE rivers ADD COLUMN IF NOT EXISTS prominence_score REAL DEFAULT 0;

-- World constructions: add scoring columns
ALTER TABLE world_constructions ADD COLUMN IF NOT EXISTS salience_score REAL DEFAULT 0;
ALTER TABLE world_constructions ADD COLUMN IF NOT EXISTS prominence_score REAL DEFAULT 0;

-- Sites: add salience/prominence (mysterious type modifier)
ALTER TABLE sites ADD COLUMN IF NOT EXISTS salience_score REAL DEFAULT 0;
ALTER TABLE sites ADD COLUMN IF NOT EXISTS prominence_score REAL DEFAULT 0;
