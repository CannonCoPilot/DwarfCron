-- Migration: add ON DELETE CASCADE to embeddings.world_id
--
-- migrate_worlds_cascade.sql states the invariant: every direct world_id FK
-- cascades, so `DELETE FROM worlds WHERE id = N` cleans up child rows without
-- manual FK-ordered deletion. The `embeddings` table was added later (embedding
-- pipeline, Stage 3.2-3.4) and was never covered, so its FK was left at the
-- PostgreSQL default of NO ACTION.
--
-- Effect before this migration (verified 2026-08-25, 189,516 embedding rows):
--   DELETE FROM worlds WHERE id=1;
--   ERROR: update or delete on table "worlds" violates foreign key constraint
--          "fk_embeddings_world" on table "embeddings"
--
-- The invariant was silently broken. `TRUNCATE worlds CASCADE` (the path
-- delete_all_worlds actually uses) masked it, so nothing surfaced until
-- tests/test_worlds.py::TestCascadeConstraints was run.
--
-- Run: psql -d chronicler -f chronicler/db/migrate_embeddings_cascade.sql

BEGIN;

ALTER TABLE embeddings DROP CONSTRAINT IF EXISTS fk_embeddings_world,
    ADD CONSTRAINT fk_embeddings_world FOREIGN KEY (world_id)
        REFERENCES worlds(id) ON DELETE CASCADE;

COMMIT;

-- NOT changed, deliberately: the composite FKs on cultural_identities,
-- occupations, and squads use ON DELETE SET NULL. Those point at child tables
-- (sites, entities, historical_figures), not at worlds. SET NULL is correct
-- there — deleting a site should null the reference, not destroy the
-- occupation record. They are reached transitively when a world cascades.
