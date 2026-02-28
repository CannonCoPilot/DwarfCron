"""Importance scoring for Chronicler CDM entities.

Computes importance_score for historical_figures, sites, artifacts, and
entities (civilizations, religions, guilds, etc.) using a combination of
fixed formulas (HFs, sites, artifacts) and IDF-weighted event rarity
scoring (entities).

Entity scoring uses TF-IDF: each entity is scored by how many events it
has, weighted by the rarity of those event types *within its own entity
type*. A religion that claimed an artifact (1.1% of religions) scores
higher per-event than one that merely recruited members (100% of religions).
"""

import logging
import math

log = logging.getLogger(__name__)

# Floor weights for inherently significant event types.
# Actual weight = max(floor, computed IDF). The floor prevents narratively
# important but common events from scoring zero.
EVENT_FLOOR_WEIGHTS: dict[str, float] = {
    # Military conflict
    "attacked site": 5.0,
    "field battle": 5.0,
    "destroyed site": 5.0,
    "razed structure": 5.0,
    "plundered site": 5.0,
    "hf attacked site": 4.0,
    "hf destroyed site": 4.0,
    # Political change
    "entity overthrown": 4.0,
    "site taken over": 4.0,
    "new site leader": 3.0,
    "entity dissolved": 3.0,
    # Criminal/unusual
    "entity primary criminals": 4.0,
    "sneak into site": 4.0,
    # Structural creation
    "created site": 2.0,
    "created structure": 2.0,
    "created world construction": 2.0,
    # Cultural
    "artifact claim formed": 3.0,
}

# Floor weights for HF link types
LINK_FLOOR_WEIGHTS: dict[str, float] = {
    "criminal": 3.0,
    "prisoner": 3.0,
    "former prisoner": 2.0,
    "slave": 4.0,
    "former slave": 3.0,
    "enemy": 1.0,
}

# Fixed weights for event collection participation (wars, sieges, etc.)
COLLECTION_WEIGHTS: dict[str, dict[str, float]] = {
    "attacker": {
        "war": 15.0,
        "site conquered": 10.0,
        "abduction": 3.0,
        "theft": 3.0,
    },
    "defender": {
        "war": 12.0,
        "site conquered": 8.0,
        "beast attack": 5.0,
        "abduction": 3.0,
        "theft": 3.0,
    },
}


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

    # ── Entity importance (IDF-weighted event rarity) ─────────────────
    entity_count = await _compute_entity_scores(conn, world_id)
    counts["entities"] = entity_count
    log.info("  Entity importance scores: %d entities scored", entity_count)

    return counts


async def _compute_entity_scores(conn, world_id: int) -> int:
    """Compute IDF-weighted importance scores for all entities in a world.

    The scoring uses three signal sources:
    1. Event participation (event_entity_xref) — weighted by event type rarity
       within the entity's own type. Uses TF-IDF: rare events score higher.
    2. HF membership links (hf_entity_links) — weighted by link type rarity.
    3. Event collection participation (history_event_collections) — fixed
       weights for wars, sieges, beast attacks, etc.

    Scores are normalized per entity type to a 0–1000 range so that a top
    civilization and a top merchant company are comparable in the UI.
    """
    # Reset all entity scores to 0 before recomputing — entities with
    # no signals will correctly remain at 0.
    await conn.execute(
        "UPDATE entities SET importance_score = 0.0 WHERE world_id = $1",
        world_id,
    )

    # Get all entity types present in this world
    entity_types = await conn.fetch(
        "SELECT type, COUNT(*) as cnt FROM entities "
        "WHERE world_id = $1 GROUP BY type",
        world_id,
    )

    total_scored = 0

    for row in entity_types:
        etype = row["type"]
        n_entities = row["cnt"]

        if n_entities == 0:
            continue

        scored = await _score_entity_type(conn, world_id, etype, n_entities)
        total_scored += scored
        log.info("    %s: %d entities scored", etype, scored)

    return total_scored


async def _score_entity_type(
    conn, world_id: int, etype: str, n_entities: int
) -> int:
    """Score all entities of a single type using IDF-weighted event rarity.

    Returns the number of entities updated.
    """
    # ── Step 1: Compute IDF weights for event types ──────────────────
    event_idf = await _compute_event_idf(conn, world_id, etype, n_entities)

    # ── Step 2: Compute IDF weights for HF link types ────────────────
    link_idf = await _compute_link_idf(conn, world_id, etype, n_entities)

    # ── Step 3: Batch-query all per-entity signal counts ──────────────
    # Three queries total (not per-entity) to avoid O(n) round-trips.
    scores: dict[int, float] = {}

    # 3a: Event participation — one query for all entities of this type
    event_rows = await conn.fetch(
        """SELECT eex.entity_id, he.event_type, COUNT(*) as cnt
           FROM event_entity_xref eex
           JOIN history_events he ON eex.event_id = he.id
                AND eex.world_id = he.world_id
           JOIN entities e ON eex.entity_id = e.id
                AND eex.world_id = e.world_id
           WHERE eex.world_id = $1 AND eex.entity_type = 'entity'
                 AND e.type = $2
           GROUP BY eex.entity_id, he.event_type""",
        world_id, etype,
    )
    for er in event_rows:
        eid = er["entity_id"]
        evt = er["event_type"]
        idf = event_idf.get(evt, 0.0)
        floor = EVENT_FLOOR_WEIGHTS.get(evt, 0.0)
        scores[eid] = scores.get(eid, 0.0) + er["cnt"] * max(idf, floor)

    # 3b: HF link counts — one query for all entities of this type
    link_rows = await conn.fetch(
        """SELECT hel.entity_id, hel.link_type, COUNT(*) as cnt
           FROM hf_entity_links hel
           JOIN entities e ON hel.entity_id = e.id
                AND hel.world_id = e.world_id
           WHERE hel.world_id = $1 AND e.type = $2
           GROUP BY hel.entity_id, hel.link_type""",
        world_id, etype,
    )
    for lr in link_rows:
        eid = lr["entity_id"]
        lt = lr["link_type"]
        idf = link_idf.get(lt, 0.0)
        floor = LINK_FLOOR_WEIGHTS.get(lt, 0.0)
        scores[eid] = scores.get(eid, 0.0) + lr["cnt"] * max(idf, floor)

    # 3c: Event collection participation (attacker/defender roles)
    for role_col, role_weights in [
        ("attacker_entity_id", COLLECTION_WEIGHTS["attacker"]),
        ("defender_entity_id", COLLECTION_WEIGHTS["defender"]),
    ]:
        coll_rows = await conn.fetch(
            f"""SELECT hec.{role_col} as entity_id, hec.type, COUNT(*) as cnt
                FROM history_event_collections hec
                JOIN entities e ON hec.{role_col} = e.id
                     AND hec.world_id = e.world_id
                WHERE hec.world_id = $1 AND e.type = $2
                GROUP BY hec.{role_col}, hec.type""",
            world_id, etype,
        )
        for cr in coll_rows:
            eid = cr["entity_id"]
            weight = role_weights.get(cr["type"], 1.0)
            scores[eid] = scores.get(eid, 0.0) + cr["cnt"] * weight

    # ── Step 4: Normalize to 0–1000 range within this entity type ────
    if not scores:
        return 0

    max_score = max(scores.values())
    if max_score > 0:
        for eid in scores:
            scores[eid] = (scores[eid] / max_score) * 1000.0

    # ── Step 5: Batch update ─────────────────────────────────────────
    await conn.executemany(
        "UPDATE entities SET importance_score = $1 WHERE world_id = $2 AND id = $3",
        [(scores[eid], world_id, eid) for eid in scores],
    )

    return len(scores)


async def _compute_event_idf(
    conn, world_id: int, etype: str, n_entities: int
) -> dict[str, float]:
    """Compute IDF weights for event types within a given entity type.

    IDF = log2(N / n_i) where:
      N = total entities of this type
      n_i = entities of this type that have event type i

    Events that occur in 100% of entities get IDF = 0 (no signal).
    Events that occur in 1 entity get maximum IDF (very rare = very interesting).
    """
    rows = await conn.fetch(
        """SELECT he.event_type, COUNT(DISTINCT eex.entity_id) as entity_count
           FROM event_entity_xref eex
           JOIN history_events he ON eex.event_id = he.id
                AND eex.world_id = he.world_id
           JOIN entities e ON eex.entity_id = e.id AND eex.world_id = e.world_id
           WHERE eex.world_id = $1 AND eex.entity_type = 'entity' AND e.type = $2
           GROUP BY he.event_type""",
        world_id, etype,
    )

    idf: dict[str, float] = {}
    for r in rows:
        n_i = r["entity_count"]
        if n_i > 0 and n_entities > 0:
            idf[r["event_type"]] = math.log2(n_entities / n_i)
    return idf


async def _compute_link_idf(
    conn, world_id: int, etype: str, n_entities: int
) -> dict[str, float]:
    """Compute IDF weights for HF link types within a given entity type.

    Same formula as event IDF: log2(N / n_i).
    """
    rows = await conn.fetch(
        """SELECT hel.link_type, COUNT(DISTINCT hel.entity_id) as entity_count
           FROM hf_entity_links hel
           JOIN entities e ON hel.entity_id = e.id AND hel.world_id = e.world_id
           WHERE hel.world_id = $1 AND e.type = $2
           GROUP BY hel.link_type""",
        world_id, etype,
    )

    idf: dict[str, float] = {}
    for r in rows:
        n_i = r["entity_count"]
        if n_i > 0 and n_entities > 0:
            idf[r["link_type"]] = math.log2(n_entities / n_i)
    return idf
