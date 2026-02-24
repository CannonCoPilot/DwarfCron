"""Importance scoring for Chronicler CDM entities.

Computes importance_score for historical_figures, sites, and artifacts
using formulas adapted from df-narrator. Scores are used by the LLM
storyteller for context selection — top-N entities by score, optionally
filtered by region, civilization, or site.
"""

import logging

log = logging.getLogger(__name__)


async def compute_importance_scores(conn, world_id: int) -> dict[str, int]:
    """Compute and store importance_score for all entities in a world.

    Returns dict with count of updated rows per entity type.
    """
    counts = {}

    # ── Historical Figure importance ──────────────────────────────────
    # Formula (adapted from df-narrator):
    #   LEAST(event_count * 2, 500)
    #   + kill_count * 15
    #   + is_vampire * 80 + is_necromancer * 100 + is_deity * 120
    #   + is_force * 90 + is_werebeast * 70
    #   + LEAST(hf_links_count * 3, 100)
    #   + leadership_positions * 20
    #   + artifacts_held * 30
    #   + LEAST(site_links * 5, 50)
    #   + LEAST(entity_links * 3, 60)
    #   + (death_year IS NOT NULL) * 5
    result = await conn.execute("""
        UPDATE historical_figures hf SET importance_score = (
            LEAST(COALESCE(hf.event_count, 0) * 2, 500)
            + COALESCE(hf.kill_count, 0) * 15
            + (hf.is_vampire::int) * 80
            + (hf.is_necromancer::int) * 100
            + (hf.is_deity::int) * 120
            + (hf.is_force::int) * 90
            + (hf.is_werebeast::int) * 70
            + LEAST(COALESCE(links.cnt, 0) * 3, 100)
            + COALESCE(positions.cnt, 0) * 20
            + COALESCE(artifacts.cnt, 0) * 30
            + LEAST(COALESCE(site_links.cnt, 0) * 5, 50)
            + LEAST(COALESCE(entity_links.cnt, 0) * 3, 60)
            + (CASE WHEN hf.death_year IS NOT NULL THEN 5 ELSE 0 END)
        )
        FROM (SELECT id FROM historical_figures WHERE world_id = $1) ids
        LEFT JOIN LATERAL (
            SELECT COUNT(*) AS cnt FROM hf_links
            WHERE world_id = $1 AND hf_id = ids.id
        ) links ON TRUE
        LEFT JOIN LATERAL (
            SELECT COUNT(*) AS cnt FROM hf_position_links
            WHERE world_id = $1 AND hf_id = ids.id AND end_year IS NULL
        ) positions ON TRUE
        LEFT JOIN LATERAL (
            SELECT COUNT(*) AS cnt FROM artifacts
            WHERE world_id = $1 AND holder_hf_id = ids.id
        ) artifacts ON TRUE
        LEFT JOIN LATERAL (
            SELECT COUNT(*) AS cnt FROM hf_site_links
            WHERE world_id = $1 AND hf_id = ids.id
        ) site_links ON TRUE
        LEFT JOIN LATERAL (
            SELECT COUNT(*) AS cnt FROM hf_entity_links
            WHERE world_id = $1 AND hf_id = ids.id
        ) entity_links ON TRUE
        WHERE hf.world_id = $1 AND hf.id = ids.id
    """, world_id)
    counts["historical_figures"] = int(result.split()[-1]) if result else 0
    log.info("  HF importance scores: %s", result)

    # ── Site importance ───────────────────────────────────────────────
    # Formula: events + deaths * 2 + event_collections * 5 + structures * 3
    result = await conn.execute("""
        UPDATE sites s SET importance_score = (
            COALESCE(events.cnt, 0)
            + COALESCE(deaths.cnt, 0) * 2
            + COALESCE(collections.cnt, 0) * 5
            + COALESCE(structs.cnt, 0) * 3
        )
        FROM (SELECT id FROM sites WHERE world_id = $1) ids
        LEFT JOIN LATERAL (
            SELECT COUNT(*) AS cnt FROM history_events
            WHERE world_id = $1 AND site_id = ids.id
        ) events ON TRUE
        LEFT JOIN LATERAL (
            SELECT COUNT(*) AS cnt FROM history_events
            WHERE world_id = $1 AND site_id = ids.id
              AND event_type = 'hf died'
        ) deaths ON TRUE
        LEFT JOIN LATERAL (
            SELECT COUNT(*) AS cnt FROM history_event_collections
            WHERE world_id = $1 AND site_id = ids.id
        ) collections ON TRUE
        LEFT JOIN LATERAL (
            SELECT COUNT(*) AS cnt FROM structures
            WHERE world_id = $1 AND site_id = ids.id
        ) structs ON TRUE
        WHERE s.world_id = $1 AND s.id = ids.id
    """, world_id)
    counts["sites"] = int(result.split()[-1]) if result else 0
    log.info("  Site importance scores: %s", result)

    # ── Artifact importance ───────────────────────────────────────────
    # Formula: events * 10 + named(50) + has_holder(20)
    # Note: unique_holders and lost_or_stolen would require event scanning;
    # we approximate with has_holder and event count.
    result = await conn.execute("""
        UPDATE artifacts a SET importance_score = (
            COALESCE(events.cnt, 0) * 10
            + (CASE WHEN a.name IS NOT NULL AND a.name != '' THEN 50 ELSE 0 END)
            + (CASE WHEN a.holder_hf_id IS NOT NULL THEN 20 ELSE 0 END)
        )
        FROM (SELECT id FROM artifacts WHERE world_id = $1) ids
        LEFT JOIN LATERAL (
            SELECT COUNT(*) AS cnt FROM history_events
            WHERE world_id = $1 AND artifact_id = ids.id
        ) events ON TRUE
        WHERE a.world_id = $1 AND a.id = ids.id
    """, world_id)
    counts["artifacts"] = int(result.split()[-1]) if result else 0
    log.info("  Artifact importance scores: %s", result)

    return counts
