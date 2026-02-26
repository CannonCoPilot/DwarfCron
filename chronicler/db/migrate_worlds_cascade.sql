-- Migration: Add ON DELETE CASCADE to all world_id foreign keys
-- This enables `DELETE FROM worlds WHERE id = N` to automatically cascade
-- to all child tables, eliminating the need for manual FK-ordered deletion.
--
-- Run: psql -d chronicler -f chronicler/db/migrate_worlds_cascade.sql

BEGIN;

-- Direct world_id → worlds(id) FKs (26 tables)
ALTER TABLE landmasses DROP CONSTRAINT IF EXISTS landmasses_world_id_fkey,
    ADD CONSTRAINT landmasses_world_id_fkey FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE;
ALTER TABLE mountain_peaks DROP CONSTRAINT IF EXISTS mountain_peaks_world_id_fkey,
    ADD CONSTRAINT mountain_peaks_world_id_fkey FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE;
ALTER TABLE regions DROP CONSTRAINT IF EXISTS regions_world_id_fkey,
    ADD CONSTRAINT regions_world_id_fkey FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE;
ALTER TABLE underground_regions DROP CONSTRAINT IF EXISTS underground_regions_world_id_fkey,
    ADD CONSTRAINT underground_regions_world_id_fkey FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE;
ALTER TABLE sites DROP CONSTRAINT IF EXISTS sites_world_id_fkey,
    ADD CONSTRAINT sites_world_id_fkey FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE;
ALTER TABLE world_constructions DROP CONSTRAINT IF EXISTS world_constructions_world_id_fkey,
    ADD CONSTRAINT world_constructions_world_id_fkey FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE;
ALTER TABLE art_forms DROP CONSTRAINT IF EXISTS art_forms_world_id_fkey,
    ADD CONSTRAINT art_forms_world_id_fkey FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE;
ALTER TABLE rivers DROP CONSTRAINT IF EXISTS rivers_world_id_fkey,
    ADD CONSTRAINT rivers_world_id_fkey FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE;
ALTER TABLE entities DROP CONSTRAINT IF EXISTS entities_world_id_fkey,
    ADD CONSTRAINT entities_world_id_fkey FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE;
ALTER TABLE historical_figures DROP CONSTRAINT IF EXISTS historical_figures_world_id_fkey,
    ADD CONSTRAINT historical_figures_world_id_fkey FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE;
ALTER TABLE identities DROP CONSTRAINT IF EXISTS identities_world_id_fkey,
    ADD CONSTRAINT identities_world_id_fkey FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE;
ALTER TABLE history_events DROP CONSTRAINT IF EXISTS history_events_world_id_fkey,
    ADD CONSTRAINT history_events_world_id_fkey FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE;
ALTER TABLE history_event_collections DROP CONSTRAINT IF EXISTS history_event_collections_world_id_fkey,
    ADD CONSTRAINT history_event_collections_world_id_fkey FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE;
ALTER TABLE event_relationships DROP CONSTRAINT IF EXISTS event_relationships_world_id_fkey,
    ADD CONSTRAINT event_relationships_world_id_fkey FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE;
ALTER TABLE artifacts DROP CONSTRAINT IF EXISTS artifacts_world_id_fkey,
    ADD CONSTRAINT artifacts_world_id_fkey FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE;
ALTER TABLE written_contents DROP CONSTRAINT IF EXISTS written_contents_world_id_fkey,
    ADD CONSTRAINT written_contents_world_id_fkey FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE;
ALTER TABLE historical_eras DROP CONSTRAINT IF EXISTS historical_eras_world_id_fkey,
    ADD CONSTRAINT historical_eras_world_id_fkey FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE;
ALTER TABLE units DROP CONSTRAINT IF EXISTS units_world_id_fkey,
    ADD CONSTRAINT units_world_id_fkey FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE;
ALTER TABLE unit_events DROP CONSTRAINT IF EXISTS unit_events_world_id_fkey,
    ADD CONSTRAINT unit_events_world_id_fkey FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE;
ALTER TABLE sync_snapshots DROP CONSTRAINT IF EXISTS sync_snapshots_world_id_fkey,
    ADD CONSTRAINT sync_snapshots_world_id_fkey FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE;
ALTER TABLE game_reports DROP CONSTRAINT IF EXISTS game_reports_world_id_fkey,
    ADD CONSTRAINT game_reports_world_id_fkey FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE;
ALTER TABLE world_map_snapshots DROP CONSTRAINT IF EXISTS world_map_snapshots_world_id_fkey,
    ADD CONSTRAINT world_map_snapshots_world_id_fkey FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE;
ALTER TABLE lua_probes DROP CONSTRAINT IF EXISTS lua_probes_world_id_fkey,
    ADD CONSTRAINT lua_probes_world_id_fkey FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE;
ALTER TABLE fortress_denizens DROP CONSTRAINT IF EXISTS fortress_denizens_world_id_fkey,
    ADD CONSTRAINT fortress_denizens_world_id_fkey FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE;
ALTER TABLE worldgen_snapshots DROP CONSTRAINT IF EXISTS worldgen_snapshots_world_id_fkey,
    ADD CONSTRAINT worldgen_snapshots_world_id_fkey FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE;
ALTER TABLE world_modpacks DROP CONSTRAINT IF EXISTS world_modpacks_world_id_fkey,
    ADD CONSTRAINT world_modpacks_world_id_fkey FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE;

-- Inter-child FKs (15 constraints) — add CASCADE so deleting parent rows cascades
ALTER TABLE structures DROP CONSTRAINT IF EXISTS structures_world_id_site_id_fkey,
    ADD CONSTRAINT structures_world_id_site_id_fkey FOREIGN KEY (world_id, site_id) REFERENCES sites(world_id, id) ON DELETE CASCADE;
ALTER TABLE entity_positions DROP CONSTRAINT IF EXISTS entity_positions_world_id_entity_id_fkey,
    ADD CONSTRAINT entity_positions_world_id_entity_id_fkey FOREIGN KEY (world_id, entity_id) REFERENCES entities(world_id, id) ON DELETE CASCADE;
ALTER TABLE hf_links DROP CONSTRAINT IF EXISTS hf_links_world_id_hf_id_fkey,
    ADD CONSTRAINT hf_links_world_id_hf_id_fkey FOREIGN KEY (world_id, hf_id) REFERENCES historical_figures(world_id, id) ON DELETE CASCADE;
ALTER TABLE hf_links DROP CONSTRAINT IF EXISTS hf_links_world_id_target_hf_id_fkey,
    ADD CONSTRAINT hf_links_world_id_target_hf_id_fkey FOREIGN KEY (world_id, target_hf_id) REFERENCES historical_figures(world_id, id) ON DELETE CASCADE;
ALTER TABLE hf_entity_links DROP CONSTRAINT IF EXISTS hf_entity_links_world_id_hf_id_fkey,
    ADD CONSTRAINT hf_entity_links_world_id_hf_id_fkey FOREIGN KEY (world_id, hf_id) REFERENCES historical_figures(world_id, id) ON DELETE CASCADE;
ALTER TABLE hf_entity_links DROP CONSTRAINT IF EXISTS hf_entity_links_world_id_entity_id_fkey,
    ADD CONSTRAINT hf_entity_links_world_id_entity_id_fkey FOREIGN KEY (world_id, entity_id) REFERENCES entities(world_id, id) ON DELETE CASCADE;
ALTER TABLE hf_site_links DROP CONSTRAINT IF EXISTS hf_site_links_world_id_hf_id_fkey,
    ADD CONSTRAINT hf_site_links_world_id_hf_id_fkey FOREIGN KEY (world_id, hf_id) REFERENCES historical_figures(world_id, id) ON DELETE CASCADE;
ALTER TABLE hf_site_links DROP CONSTRAINT IF EXISTS hf_site_links_world_id_site_id_fkey,
    ADD CONSTRAINT hf_site_links_world_id_site_id_fkey FOREIGN KEY (world_id, site_id) REFERENCES sites(world_id, id) ON DELETE CASCADE;
ALTER TABLE hf_position_links DROP CONSTRAINT IF EXISTS hf_position_links_world_id_hf_id_fkey,
    ADD CONSTRAINT hf_position_links_world_id_hf_id_fkey FOREIGN KEY (world_id, hf_id) REFERENCES historical_figures(world_id, id) ON DELETE CASCADE;
ALTER TABLE hf_position_links DROP CONSTRAINT IF EXISTS hf_position_links_world_id_entity_id_fkey,
    ADD CONSTRAINT hf_position_links_world_id_entity_id_fkey FOREIGN KEY (world_id, entity_id) REFERENCES entities(world_id, id) ON DELETE CASCADE;
ALTER TABLE collection_events DROP CONSTRAINT IF EXISTS collection_events_world_id_collection_id_fkey,
    ADD CONSTRAINT collection_events_world_id_collection_id_fkey FOREIGN KEY (world_id, collection_id) REFERENCES history_event_collections(world_id, id) ON DELETE CASCADE;
ALTER TABLE collection_events DROP CONSTRAINT IF EXISTS collection_events_world_id_event_id_fkey,
    ADD CONSTRAINT collection_events_world_id_event_id_fkey FOREIGN KEY (world_id, event_id) REFERENCES history_events(world_id, id) ON DELETE CASCADE;
ALTER TABLE collection_subcollections DROP CONSTRAINT IF EXISTS collection_subcollections_world_id_parent_id_fkey,
    ADD CONSTRAINT collection_subcollections_world_id_parent_id_fkey FOREIGN KEY (world_id, parent_id) REFERENCES history_event_collections(world_id, id) ON DELETE CASCADE;
ALTER TABLE collection_subcollections DROP CONSTRAINT IF EXISTS collection_subcollections_world_id_child_id_fkey,
    ADD CONSTRAINT collection_subcollections_world_id_child_id_fkey FOREIGN KEY (world_id, child_id) REFERENCES history_event_collections(world_id, id) ON DELETE CASCADE;
ALTER TABLE event_entity_xref DROP CONSTRAINT IF EXISTS event_entity_xref_world_id_event_id_fkey,
    ADD CONSTRAINT event_entity_xref_world_id_event_id_fkey FOREIGN KEY (world_id, event_id) REFERENCES history_events(world_id, id) ON DELETE CASCADE;

COMMIT;
