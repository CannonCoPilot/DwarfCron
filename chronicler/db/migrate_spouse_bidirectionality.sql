-- migrate_spouse_bidirectionality.sql
-- Fix one-directional romantic relationship links and deduplicate overlaps.
--
-- Issues fixed:
--   1. deceased spouse: 5,000 links with 0 reverses (XML only records on surviving side)
--   2. former spouse:   2 missing reverses (edge cases)
--   3. lover:           0 missing (safety net for future ingestions)
--   4. spouse+deceased spouse duplicates: 4,982 rows where post_parse added 'spouse'
--      but XML already had 'deceased spouse' for same pair — remove less-specific duplicate
--
-- Safe to run multiple times (ON CONFLICT DO NOTHING / EXISTS guard).

BEGIN;

-- 1. Add reverse deceased spouse links
INSERT INTO hf_links (world_id, hf_id, target_hf_id, link_type)
SELECT world_id, target_hf_id, hf_id, 'deceased spouse'
FROM hf_links
WHERE link_type = 'deceased spouse'
ON CONFLICT DO NOTHING;

-- 2. Add reverse former spouse links
INSERT INTO hf_links (world_id, hf_id, target_hf_id, link_type)
SELECT world_id, target_hf_id, hf_id, 'former spouse'
FROM hf_links
WHERE link_type = 'former spouse'
ON CONFLICT DO NOTHING;

-- 3. Add reverse lover links (safety)
INSERT INTO hf_links (world_id, hf_id, target_hf_id, link_type)
SELECT world_id, target_hf_id, hf_id, 'lover'
FROM hf_links
WHERE link_type = 'lover'
ON CONFLICT DO NOTHING;

-- 4. Remove duplicate 'spouse' where 'deceased spouse' already exists for same pair
--    (keep deceased spouse as the more specific/informative type)
DELETE FROM hf_links s
USING hf_links d
WHERE s.link_type = 'spouse'
  AND d.link_type = 'deceased spouse'
  AND s.world_id = d.world_id
  AND s.hf_id = d.hf_id
  AND s.target_hf_id = d.target_hf_id;

COMMIT;
