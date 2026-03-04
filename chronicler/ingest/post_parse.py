"""Post-parse processing pipeline for Chronicler CDM.

Runs after XML ingestion to resolve cross-references, derive computed flags,
build indexes, and validate referential integrity. 11 steps executed in order
(later steps depend on earlier steps).
"""

import json
import logging

import asyncpg

log = logging.getLogger(__name__)


class PostParseProcessor:
    """Runs after XML ingestion to resolve cross-references and derive computed data."""

    def __init__(self, conn: asyncpg.Connection, world_id: int):
        self.conn = conn
        self.world_id = world_id

    async def run_all(self) -> dict[str, any]:
        """Execute all 11 processing steps in order. Returns step results."""
        results = {}
        results["step_1"] = await self.step_1_resolve_family_links()
        results["step_2"] = await self.step_2_resolve_position_assignments()
        results["step_3"] = await self.step_3_derive_supernatural_flags()
        results["step_4"] = await self.step_4_compute_site_ruin_status()
        results["step_5"] = await self.step_5_build_entity_war_lists()
        results["step_6"] = await self.step_6_compute_hf_kill_lists()
        results["step_7"] = await self.step_7_calculate_scores()
        results["step_8"] = await self.step_8_build_event_entity_xref()
        results["step_9"] = await self.step_9_resolve_site_ownership_history()
        results["step_10"] = await self.step_10_materialize_hf_settlement_links()
        results["step_11"] = await self.step_11_validate_referential_integrity()
        return results

    async def step_1_resolve_family_links(self) -> dict:
        """Ensure bidirectional family & romantic relationships in hf_links.

        Enforces inverse links for: mother↔child, father↔child, spouse↔spouse,
        deceased spouse↔deceased spouse, former spouse↔former spouse, lover↔lover.
        Also deduplicates spouse where deceased spouse exists for the same pair.
        """
        log.info("Step 1: Resolving family links...")
        wid = self.world_id
        inserted = 0

        # For each mother link, ensure inverse child link exists
        r = await self.conn.execute("""
            INSERT INTO hf_links (world_id, hf_id, target_hf_id, link_type)
            SELECT world_id, target_hf_id, hf_id, 'child'
            FROM hf_links
            WHERE link_type = 'mother' AND world_id = $1
            ON CONFLICT DO NOTHING
        """, wid)
        inserted += _count(r)

        # For each father link, ensure inverse child link exists
        r = await self.conn.execute("""
            INSERT INTO hf_links (world_id, hf_id, target_hf_id, link_type)
            SELECT world_id, target_hf_id, hf_id, 'child'
            FROM hf_links
            WHERE link_type = 'father' AND world_id = $1
            ON CONFLICT DO NOTHING
        """, wid)
        inserted += _count(r)

        # For each child link, ensure inverse parent links exist
        # (child->parent: we don't know gender, so skip — already handled above)

        # Bidirectional enforcement for all romantic/partnership link types
        for link_type in ('spouse', 'deceased spouse', 'former spouse', 'lover'):
            r = await self.conn.execute("""
                INSERT INTO hf_links (world_id, hf_id, target_hf_id, link_type)
                SELECT world_id, target_hf_id, hf_id, $2
                FROM hf_links
                WHERE link_type = $2 AND world_id = $1
                ON CONFLICT DO NOTHING
            """, wid, link_type)
            inserted += _count(r)

        # Deduplicate: remove 'spouse' where 'deceased spouse' exists for same pair
        # (deceased spouse is more specific — keep it, drop the generic duplicate)
        r = await self.conn.execute("""
            DELETE FROM hf_links s
            USING hf_links d
            WHERE s.link_type = 'spouse'
              AND d.link_type = 'deceased spouse'
              AND s.world_id = d.world_id
              AND s.hf_id = d.hf_id
              AND s.target_hf_id = d.target_hf_id
              AND s.world_id = $1
        """, wid)
        deduped = _count(r)

        log.info("  Step 1 complete: %d inverse links inserted, %d spouse duplicates removed",
                 inserted, deduped)
        return {"inserted": inserted, "deduped": deduped}

    async def step_2_resolve_position_assignments(self) -> dict:
        """Resolve position names from entity_positions into HF details."""
        log.info("Step 2: Resolving position assignments...")
        wid = self.world_id

        # Build position history for each HF from hf_position_links + entity_positions
        rows = await self.conn.fetch("""
            SELECT pl.hf_id,
                   json_agg(json_build_object(
                       'entity_id', pl.entity_id,
                       'position_name', COALESCE(ep.name, ep.name_male, ep.name_female, 'Unknown'),
                       'start_year', pl.start_year,
                       'end_year', pl.end_year
                   ) ORDER BY pl.start_year NULLS FIRST) AS positions
            FROM hf_position_links pl
            LEFT JOIN entity_positions ep
                ON ep.world_id = pl.world_id
                AND ep.entity_id = pl.entity_id
                AND ep.position_id = pl.position_id
            WHERE pl.world_id = $1
            GROUP BY pl.hf_id
        """, wid)

        updated = 0
        for row in rows:
            positions = json.loads(row["positions"])
            await self.conn.execute("""
                UPDATE historical_figures
                SET details = COALESCE(details, '{}'::jsonb) || jsonb_build_object('positions', $3::jsonb)
                WHERE world_id = $1 AND id = $2
            """, wid, row["hf_id"], positions)
            updated += 1

        log.info("  Step 2 complete: %d HFs updated with position history", updated)
        return {"updated": updated}

    async def step_3_derive_supernatural_flags(self) -> dict:
        """Derive boolean flags from active_interactions array."""
        log.info("Step 3: Deriving supernatural flags...")
        wid = self.world_id

        # Derive from active_interactions column (additive — never overwrite
        # flags already set by the XML parser).
        # Vampires: DEITY_MAJOR_CURSE_<number> (numbered per deity)
        # Necromancers: SECRET_<N> only (SECRET_ANIMATE = caster, SECRET_UNDEAD_RES = target)
        # Werebeasts: DEITY_CURSE_WEREBEAST_<animal>[_BITE]
        r = await self.conn.execute("""
            UPDATE historical_figures
            SET is_vampire = is_vampire OR
                    (EXISTS (SELECT 1 FROM unnest(active_interactions) AS ai
                             WHERE ai ~ '^DEITY_MAJOR_CURSE_[0-9]+$')),
                is_necromancer = is_necromancer OR
                    (EXISTS (SELECT 1 FROM unnest(active_interactions) AS ai
                             WHERE ai ~ '^SECRET_[0-9]+$')),
                is_werebeast = is_werebeast OR
                    (EXISTS (SELECT 1 FROM unnest(active_interactions) AS ai
                             WHERE ai LIKE 'DEITY_CURSE_WEREBEAST_%'))
            WHERE world_id = $1
              AND active_interactions IS NOT NULL
              AND array_length(active_interactions, 1) > 0
        """, wid)
        from_interactions = _count(r)

        # Also derive from events: HfDoesInteraction type events
        r = await self.conn.execute("""
            UPDATE historical_figures hf
            SET is_vampire = TRUE
            WHERE hf.world_id = $1 AND hf.is_vampire = FALSE
              AND EXISTS (
                  SELECT 1 FROM history_events e
                  WHERE e.world_id = $1 AND e.event_type = 'hf does interaction'
                    AND e.hf_id_1 = hf.id
                    AND (e.details->>'interaction_type' ILIKE '%vampire%'
                         OR e.details->>'interaction' ILIKE '%vampire%')
              )
        """, wid)
        from_events_v = _count(r)

        r = await self.conn.execute("""
            UPDATE historical_figures hf
            SET is_necromancer = TRUE
            WHERE hf.world_id = $1 AND hf.is_necromancer = FALSE
              AND EXISTS (
                  SELECT 1 FROM history_events e
                  WHERE e.world_id = $1 AND e.event_type = 'hf does interaction'
                    AND e.hf_id_1 = hf.id
                    AND (e.details->>'interaction_type' ILIKE '%necromancer%'
                         OR e.details->>'interaction' ILIKE '%reanimate%'
                         OR e.details->>'interaction' ILIKE '%animate_dead%')
              )
        """, wid)
        from_events_n = _count(r)

        r = await self.conn.execute("""
            UPDATE historical_figures hf
            SET is_werebeast = TRUE
            WHERE hf.world_id = $1 AND hf.is_werebeast = FALSE
              AND EXISTS (
                  SELECT 1 FROM history_events e
                  WHERE e.world_id = $1 AND e.event_type = 'hf does interaction'
                    AND e.hf_id_1 = hf.id
                    AND (e.details->>'interaction_type' ILIKE '%werebeast%'
                         OR e.details->>'interaction' ILIKE '%werebeast%')
              )
        """, wid)
        from_events_w = _count(r)

        log.info("  Step 3 complete: %d from interactions, %d/%d/%d from events (v/n/w)",
                 from_interactions, from_events_v, from_events_n, from_events_w)
        return {
            "from_interactions": from_interactions,
            "from_events": from_events_v + from_events_n + from_events_w,
        }

    async def step_4_compute_site_ruin_status(self) -> dict:
        """Determine which sites are ruined vs active."""
        log.info("Step 4: Computing site ruin status...")
        wid = self.world_id

        # Sites destroyed and never reclaimed
        r = await self.conn.execute("""
            UPDATE sites
            SET details = COALESCE(details, '{}'::jsonb) || '{"is_ruin": true}'::jsonb
            WHERE world_id = $1 AND id IN (
                SELECT DISTINCT e.site_id
                FROM history_events e
                WHERE e.world_id = $1
                  AND e.event_type IN ('hf destroyed site', 'destroyed site')
                  AND e.site_id IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM history_events e2
                      WHERE e2.world_id = $1
                        AND e2.event_type IN ('reclaim site', 'site taken over')
                        AND e2.site_id = e.site_id
                        AND e2.year > e.year
                  )
            )
        """, wid)
        ruins = _count(r)

        # Explicitly mark non-ruins
        r = await self.conn.execute("""
            UPDATE sites
            SET details = COALESCE(details, '{}'::jsonb) || '{"is_ruin": false}'::jsonb
            WHERE world_id = $1
              AND (details IS NULL OR NOT (details ? 'is_ruin'))
        """, wid)

        log.info("  Step 4 complete: %d sites marked as ruins", ruins)
        return {"ruins": ruins}

    async def step_5_build_entity_war_lists(self) -> dict:
        """Extract war participation data and link to entities."""
        log.info("Step 5: Building entity war lists...")
        wid = self.world_id

        # Get all war collections with attacker/defender
        wars = await self.conn.fetch("""
            SELECT id, name, attacker_entity_id, defender_entity_id,
                   start_year, end_year
            FROM history_event_collections
            WHERE world_id = $1 AND type = 'war'
        """, wid)

        # Build war list per entity
        entity_wars: dict[int, list] = {}
        for war in wars:
            war_info = {
                "collection_id": war["id"],
                "name": war["name"],
                "start_year": war["start_year"],
                "end_year": war["end_year"],
            }
            if war["attacker_entity_id"]:
                entity_wars.setdefault(war["attacker_entity_id"], []).append(
                    {**war_info, "role": "aggressor"})
            if war["defender_entity_id"]:
                entity_wars.setdefault(war["defender_entity_id"], []).append(
                    {**war_info, "role": "defender"})

        updated = 0
        for entity_id, war_list in entity_wars.items():
            await self.conn.execute("""
                UPDATE entities
                SET details = COALESCE(details, '{}'::jsonb) || jsonb_build_object('wars', $3::jsonb)
                WHERE world_id = $1 AND id = $2
            """, wid, entity_id, war_list)
            updated += 1

        log.info("  Step 5 complete: %d wars, %d entities updated", len(wars), updated)
        return {"wars": len(wars), "entities_updated": updated}

    async def step_6_compute_hf_kill_lists(self) -> dict:
        """Build kill records from death events."""
        log.info("Step 6: Computing HF kill lists...")
        wid = self.world_id

        # Get all kills from events (hf_id_2 is killer in 'hf died' events)
        kills = await self.conn.fetch("""
            SELECT hf_id_2 AS killer_id,
                   json_agg(json_build_object(
                       'victim_id', hf_id_1,
                       'year', year,
                       'cause', details->>'cause'
                   ) ORDER BY year) AS kill_list
            FROM history_events
            WHERE world_id = $1
              AND event_type = 'hf died'
              AND hf_id_2 IS NOT NULL
            GROUP BY hf_id_2
        """, wid)

        updated = 0
        for row in kills:
            kill_list = json.loads(row["kill_list"])
            # Merge with existing kills JSONB from XML parsing
            await self.conn.execute("""
                UPDATE historical_figures
                SET kills = COALESCE(kills, '{}'::jsonb) ||
                            jsonb_build_object('event_kills', $3::jsonb)
                WHERE world_id = $1 AND id = $2
            """, wid, row["killer_id"], kill_list)
            updated += 1

        log.info("  Step 6 complete: %d HFs with event-derived kills", updated)
        return {"hfs_with_kills": updated}

    async def step_7_calculate_scores(self) -> dict:
        """Calculate prominence and salience scores using scoring module."""
        log.info("Step 7: Calculating prominence and salience scores...")
        from chronicler.scoring import compute_scores
        counts = await compute_scores(self.conn, self.world_id)
        log.info("  Step 7 complete: %s", counts)
        return counts

    async def step_8_build_event_entity_xref(self) -> dict:
        """Build event-to-entity cross-reference index."""
        log.info("Step 8: Building event-entity cross-reference index...")
        wid = self.world_id

        # Clear existing xref for this world
        await self.conn.execute(
            "DELETE FROM event_entity_xref WHERE world_id = $1", wid)

        # Insert from structured event columns (hf_id_1, hf_id_2, site_id, etc.)
        xref_sql = """
            INSERT INTO event_entity_xref (world_id, event_id, entity_type, entity_id, role)
            SELECT * FROM (
                -- HF as subject (hf_id_1)
                SELECT world_id, id, 'hf', hf_id_1, 'subject'
                FROM history_events WHERE world_id = $1 AND hf_id_1 IS NOT NULL
                UNION ALL
                -- HF as object (hf_id_2)
                SELECT world_id, id, 'hf', hf_id_2, 'object'
                FROM history_events WHERE world_id = $1 AND hf_id_2 IS NOT NULL
                UNION ALL
                -- Site
                SELECT world_id, id, 'site', site_id, 'location'
                FROM history_events WHERE world_id = $1 AND site_id IS NOT NULL
                UNION ALL
                -- Region
                SELECT world_id, id, 'region', region_id, 'location'
                FROM history_events WHERE world_id = $1 AND region_id IS NOT NULL
                UNION ALL
                -- Entity 1
                SELECT world_id, id, 'entity', entity_id_1, 'subject'
                FROM history_events WHERE world_id = $1 AND entity_id_1 IS NOT NULL
                UNION ALL
                -- Entity 2
                SELECT world_id, id, 'entity', entity_id_2, 'object'
                FROM history_events WHERE world_id = $1 AND entity_id_2 IS NOT NULL
                UNION ALL
                -- Artifact
                SELECT world_id, id, 'artifact', artifact_id, 'artifact'
                FROM history_events WHERE world_id = $1 AND artifact_id IS NOT NULL
                UNION ALL
                -- Structure
                SELECT world_id, id, 'structure', structure_id, 'structure'
                FROM history_events WHERE world_id = $1 AND structure_id IS NOT NULL
            ) refs
            ON CONFLICT DO NOTHING
        """
        r = await self.conn.execute(xref_sql, wid)
        from_columns = _count(r)

        # Also index entity references from event details JSONB
        # Extract HF references from details keys
        hf_detail_keys = [
            'slayer_hf_id', 'group_1_hfid', 'group_2_hfid',
            'winner_hfid', 'loser_hfid', 'hist_figure_id',
            'target_hfid', 'snatcher_hfid', 'changee_hfid',
            'changer_hfid', 'doer_hfid', 'student_hfid', 'teacher_hfid',
        ]
        from_details = 0
        for key in hf_detail_keys:
            r = await self.conn.execute(f"""
                INSERT INTO event_entity_xref (world_id, event_id, entity_type, entity_id, role)
                SELECT world_id, id, 'hf', (details->>'{key}')::INTEGER, 'participant'
                FROM history_events
                WHERE world_id = $1
                  AND details ? '{key}'
                  AND (details->>'{key}')::INTEGER IS NOT NULL
                ON CONFLICT DO NOTHING
            """, wid)
            from_details += _count(r)

        # Extract structure references from details keys
        struct_detail_keys = [
            'destroyed_structure_id', 'dest_structure_id',
            'source_structure_id', 'new_structure', 'old_structure',
        ]
        for key in struct_detail_keys:
            r = await self.conn.execute(f"""
                INSERT INTO event_entity_xref (world_id, event_id, entity_type, entity_id, role)
                SELECT world_id, id, 'structure', (details->>'{key}')::INTEGER, 'participant'
                FROM history_events
                WHERE world_id = $1
                  AND details ? '{key}'
                  AND (details->>'{key}')::INTEGER IS NOT NULL
                ON CONFLICT DO NOTHING
            """, wid)
            from_details += _count(r)

        total = from_columns + from_details
        log.info("  Step 8 complete: %d xref rows (%d from columns, %d from details)",
                 total, from_columns, from_details)
        return {"total": total, "from_columns": from_columns, "from_details": from_details}

    async def step_9_resolve_site_ownership_history(self) -> dict:
        """Build chronological ownership history for each site."""
        log.info("Step 9: Resolving site ownership history...")
        wid = self.world_id

        # Get all ownership-changing events for sites
        events = await self.conn.fetch("""
            SELECT site_id, year, event_type, entity_id_1, entity_id_2,
                   details->>'civ_id' AS civ_id,
                   details->>'site_civ_id' AS site_civ_id,
                   details->>'attacker_civ_id' AS attacker_civ_id,
                   details->>'defender_civ_id' AS defender_civ_id
            FROM history_events
            WHERE world_id = $1
              AND event_type IN ('created site', 'hf destroyed site', 'destroyed site',
                                 'reclaim site', 'site taken over', 'plundered site',
                                 'attacked site')
              AND site_id IS NOT NULL
            ORDER BY site_id, year
        """, wid)

        # Group by site
        site_history: dict[int, list] = {}
        for ev in events:
            sid = ev["site_id"]
            entry = {
                "year": ev["year"],
                "event": ev["event_type"],
            }
            # Determine entity_id based on event type
            if ev["event_type"] == "created site":
                entry["entity_id"] = ev["entity_id_1"] or _safe_int(ev["civ_id"])
            elif ev["event_type"] in ("site taken over", "reclaim site"):
                entry["entity_id"] = ev["entity_id_1"] or _safe_int(ev["attacker_civ_id"])
            elif ev["event_type"] in ("hf destroyed site", "destroyed site"):
                entry["entity_id"] = None  # destroyed = no owner
            site_history.setdefault(sid, []).append(entry)

        updated = 0
        for site_id, history in site_history.items():
            await self.conn.execute("""
                UPDATE sites
                SET details = COALESCE(details, '{}'::jsonb) ||
                              jsonb_build_object('ownership_history', $3::jsonb)
                WHERE world_id = $1 AND id = $2
            """, wid, site_id, history)
            updated += 1

        # Backfill owner_entity_id from ownership_history for sites with NULL owner
        # Use the last non-null entity_id that isn't a "destroyed" event
        status = await self.conn.execute("""
            WITH last_owners AS (
                SELECT s.id,
                       (SELECT (elem->>'entity_id')::int
                        FROM jsonb_array_elements(s.details->'ownership_history') elem
                        WHERE elem->>'entity_id' IS NOT NULL
                          AND elem->>'entity_id' != 'null'
                          AND elem->>'event' NOT LIKE '%%destroyed%%'
                        ORDER BY (elem->>'year')::int DESC
                        LIMIT 1) AS last_owner
                FROM sites s
                WHERE s.world_id = $1
                  AND s.owner_entity_id IS NULL
                  AND s.details ? 'ownership_history'
                  AND jsonb_array_length(s.details->'ownership_history') > 0
            )
            UPDATE sites s
            SET owner_entity_id = lo.last_owner
            FROM last_owners lo
            WHERE s.world_id = $1 AND s.id = lo.id AND lo.last_owner IS NOT NULL
        """, wid)
        backfilled = int(status.split()[-1]) if status else 0

        log.info("  Step 9 complete: %d sites with ownership history, %s backfilled owner_entity_id",
                 updated, backfilled or 0)
        return {"sites_updated": updated, "owners_backfilled": backfilled or 0}

    async def step_10_materialize_hf_settlement_links(self) -> dict:
        """Materialize resident/former resident links from change-hf-state events.

        For each HF, the site from their most recent 'settled' event becomes
        'resident'; all other HF-site settlement pairs become 'former resident'.
        """
        log.info("Step 10: Materializing HF settlement links...")
        wid = self.world_id

        # Clean any prior materialized settlement links for this world
        r = await self.conn.execute("""
            DELETE FROM hf_site_links
            WHERE world_id = $1 AND link_type IN ('settled', 'resident', 'former resident')
        """, wid)
        cleaned = _count(r)
        if cleaned:
            log.info("  Cleaned %d prior settlement links", cleaned)

        # CTE: for each HF, rank settlement events by year DESC per site,
        # then pick the most recent site overall as 'resident'
        status = await self.conn.execute("""
            WITH settlements AS (
                SELECT DISTINCT ON (hf_id_1, site_id)
                    world_id, hf_id_1, site_id, year
                FROM history_events
                WHERE world_id = $1
                  AND event_type = 'change hf state'
                  AND details->>'state' = 'settled'
                  AND hf_id_1 IS NOT NULL
                  AND site_id IS NOT NULL
                ORDER BY hf_id_1, site_id, year DESC
            ),
            ranked AS (
                SELECT *,
                    ROW_NUMBER() OVER (PARTITION BY hf_id_1 ORDER BY year DESC) AS rn
                FROM settlements
            )
            INSERT INTO hf_site_links (world_id, hf_id, site_id, link_type)
            SELECT world_id, hf_id_1, site_id,
                   CASE WHEN rn = 1 THEN 'resident' ELSE 'former resident' END
            FROM ranked
            ON CONFLICT DO NOTHING
        """, wid)
        inserted = _count(status)

        # Count breakdown
        residents = await self.conn.fetchval("""
            SELECT COUNT(*) FROM hf_site_links
            WHERE world_id = $1 AND link_type = 'resident'
        """, wid)
        former = await self.conn.fetchval("""
            SELECT COUNT(*) FROM hf_site_links
            WHERE world_id = $1 AND link_type = 'former resident'
        """, wid)

        log.info("  Step 10 complete: %d links (%d resident, %d former resident)",
                 inserted, residents, former)
        return {"inserted": inserted, "residents": residents, "former_residents": former}

    async def step_11_validate_referential_integrity(self) -> dict:
        """Verify FK-like references resolve to existing records."""
        log.info("Step 11: Validating referential integrity...")
        wid = self.world_id
        issues = {}

        # HF links referencing non-existent HFs
        r = await self.conn.fetchval("""
            SELECT COUNT(*) FROM hf_links
            WHERE world_id = $1
              AND target_hf_id NOT IN (SELECT id FROM historical_figures WHERE world_id = $1)
        """, wid)
        if r:
            issues["hf_links_broken_target"] = r
            log.warning("  %d hf_links reference non-existent HFs", r)

        # Entity links referencing non-existent entities
        r = await self.conn.fetchval("""
            SELECT COUNT(*) FROM hf_entity_links
            WHERE world_id = $1
              AND entity_id NOT IN (SELECT id FROM entities WHERE world_id = $1)
        """, wid)
        if r:
            issues["hf_entity_links_broken"] = r
            log.warning("  %d hf_entity_links reference non-existent entities", r)

        # Site links referencing non-existent sites
        r = await self.conn.fetchval("""
            SELECT COUNT(*) FROM hf_site_links
            WHERE world_id = $1
              AND site_id NOT IN (SELECT id FROM sites WHERE world_id = $1)
        """, wid)
        if r:
            issues["hf_site_links_broken"] = r
            log.warning("  %d hf_site_links reference non-existent sites", r)

        # Events with broken HF references
        r = await self.conn.fetchval("""
            SELECT COUNT(*) FROM history_events
            WHERE world_id = $1 AND hf_id_1 IS NOT NULL
              AND hf_id_1 NOT IN (SELECT id FROM historical_figures WHERE world_id = $1)
        """, wid)
        if r:
            issues["events_broken_hf1"] = r
            log.warning("  %d events reference non-existent HF (hf_id_1)", r)

        # Total reference counts for percentage
        total_refs = await self.conn.fetchval("""
            SELECT (SELECT COUNT(*) FROM hf_links WHERE world_id = $1)
                 + (SELECT COUNT(*) FROM hf_entity_links WHERE world_id = $1)
                 + (SELECT COUNT(*) FROM hf_site_links WHERE world_id = $1)
        """, wid)

        broken_total = sum(issues.values())
        pct = (broken_total / total_refs * 100) if total_refs > 0 else 0

        if not issues:
            log.info("  Step 11 complete: no referential integrity issues found")
        else:
            log.info("  Step 11 complete: %d broken references (%.2f%% of %d total)",
                     broken_total, pct, total_refs)

        return {"broken": issues, "broken_total": broken_total,
                "total_refs": total_refs, "broken_pct": round(pct, 4)}


def _count(result: str) -> int:
    """Extract row count from asyncpg execute result string like 'UPDATE 42'."""
    if result:
        parts = result.split()
        if len(parts) >= 2:
            try:
                return int(parts[-1])
            except ValueError:
                pass
    return 0


def _safe_int(val) -> int | None:
    """Convert a value to int, or None."""
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None
