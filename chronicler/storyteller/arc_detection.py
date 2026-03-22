"""Stage 3.6.3 + 3.6.8: Narrative Arc Detection and Event Clustering.

Detects story arcs by clustering temporally/thematically related events:
  - siege_defense: combat + threat tracking + deaths at a site
  - last_stand: population decline + combat near end-of-fortress
  - golden_age: wealth growth + construction + low threats
  - founding_days: first N years of a fortress
  - rise_and_fall: site creation followed by destruction
  - megabeast_attack: beast attack event collection + related deaths
  - succession_crisis: leader death + political events
  - trade_prosperity: caravan/trade events clustered together

Also groups temporally adjacent events into clusters for narrative cohesion.
"""

import logging

log = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════
# Arc Detection
# ═══════════════════════════════════════════════════════════════════════

async def detect_arcs(conn, world_id: int, force: bool = False) -> dict:
    """Detect narrative arcs for a world. Populates narrative_arcs table.

    Returns summary with arc counts by type.
    """
    log.info("Arc detection: starting for world %d", world_id)

    if force:
        await conn.execute(
            "DELETE FROM narrative_arcs WHERE world_id = $1", world_id)

    counts = {}

    n = await _detect_siege_defense(conn, world_id)
    counts["siege_defense"] = n

    n = await _detect_rise_and_fall(conn, world_id)
    counts["rise_and_fall"] = n

    n = await _detect_golden_age(conn, world_id)
    counts["golden_age"] = n

    n = await _detect_megabeast_attack(conn, world_id)
    counts["megabeast_attack"] = n

    n = await _detect_succession_crisis(conn, world_id)
    counts["succession_crisis"] = n

    # Compute dramatic weight from constituent events
    await _compute_arc_weights(conn, world_id)

    total = sum(counts.values())
    log.info("Arc detection complete: %d arcs (%s)", total, counts)
    return {"total_arcs": total, "by_type": counts}


async def _detect_siege_defense(conn, world_id: int) -> int:
    """Detect siege_defense arcs: attack event + deaths at same site within 5 years."""
    arcs = await conn.fetch("""
        WITH siege_events AS (
            SELECT site_id, MIN(year) AS start_year, MAX(year) AS end_year,
                   array_agg(id ORDER BY year, id) AS event_ids,
                   COUNT(*) AS event_count
            FROM history_events
            WHERE world_id = $1
                AND event_type IN ('attacked site', 'hf attacked site',
                                    'field battle', 'plundered site',
                                    'destroyed site', 'razed structure')
                AND site_id IS NOT NULL
            GROUP BY site_id, year / 10
            HAVING COUNT(*) >= 2
        ),
        siege_deaths AS (
            SELECT se.site_id, se.start_year, se.end_year,
                   se.event_ids, se.event_count,
                   array_agg(d.id) AS death_ids,
                   COUNT(d.id) AS death_count
            FROM siege_events se
            LEFT JOIN history_events d
                ON d.world_id = $1
                AND d.event_type = 'hf died'
                AND d.site_id = se.site_id
                AND d.year BETWEEN se.start_year AND se.end_year + 2
            GROUP BY se.site_id, se.start_year, se.end_year,
                     se.event_ids, se.event_count
        )
        SELECT site_id, start_year, end_year,
               event_ids || COALESCE(death_ids, ARRAY[]::int[]) AS all_events,
               event_count + death_count AS total_events,
               death_count,
               CASE
                   WHEN death_count = 0 THEN 'fortress_survived'
                   WHEN death_count > event_count THEN 'pyrrhic_victory'
                   ELSE 'ongoing'
               END AS resolution
        FROM siege_deaths
        WHERE event_count + death_count >= 3
    """, world_id)

    count = 0
    for arc in arcs:
        # Convert year to pseudo-tick (year * 403200 for DF tick scale)
        start_tick = arc["start_year"] * 403200
        end_tick = (arc["end_year"] or arc["start_year"]) * 403200

        await conn.execute("""
            INSERT INTO narrative_arcs
                (world_id, arc_type, start_tick, end_tick, key_events,
                 resolution, dramatic_weight)
            VALUES ($1, 'siege_defense', $2, $3, $4, $5, 0)
            ON CONFLICT DO NOTHING
        """, world_id, start_tick, end_tick,
             list(arc["all_events"]), arc["resolution"])
        count += 1

    log.info("  siege_defense: %d arcs", count)
    return count


async def _detect_rise_and_fall(conn, world_id: int) -> int:
    """Detect rise_and_fall arcs: site creation followed by destruction."""
    arcs = await conn.fetch("""
        WITH created AS (
            SELECT id AS create_id, site_id, year AS create_year
            FROM history_events
            WHERE world_id = $1 AND event_type = 'created site'
                AND site_id IS NOT NULL
        ),
        destroyed AS (
            SELECT id AS destroy_id, site_id, year AS destroy_year
            FROM history_events
            WHERE world_id = $1 AND event_type = 'destroyed site'
                AND site_id IS NOT NULL
        )
        SELECT c.create_id, d.destroy_id, c.site_id,
               c.create_year, d.destroy_year,
               d.destroy_year - c.create_year AS lifespan
        FROM created c
        JOIN destroyed d ON d.site_id = c.site_id
            AND d.destroy_year > c.create_year
    """, world_id)

    count = 0
    for arc in arcs:
        start_tick = arc["create_year"] * 403200
        end_tick = arc["destroy_year"] * 403200
        events = [arc["create_id"], arc["destroy_id"]]

        resolution = "total_collapse"
        if arc["lifespan"] and arc["lifespan"] > 100:
            resolution = "total_collapse"  # long-lived then destroyed

        await conn.execute("""
            INSERT INTO narrative_arcs
                (world_id, arc_type, start_tick, end_tick, key_events,
                 resolution, dramatic_weight)
            VALUES ($1, 'rise_and_fall', $2, $3, $4, $5, 0)
            ON CONFLICT DO NOTHING
        """, world_id, start_tick, end_tick, events, resolution)
        count += 1

    log.info("  rise_and_fall: %d arcs", count)
    return count


async def _detect_golden_age(conn, world_id: int) -> int:
    """Detect golden_age arcs: decades with high construction, low conflict at a site."""
    arcs = await conn.fetch("""
        WITH site_decades AS (
            SELECT site_id, (year / 20) AS decade,
                   MIN(year) AS start_year, MAX(year) AS end_year,
                   COUNT(*) FILTER (WHERE event_type IN (
                       'created structure', 'artifact created',
                       'written content composed', 'knowledge discovered'
                   )) AS creative_events,
                   COUNT(*) FILTER (WHERE event_type IN (
                       'hf died', 'attacked site', 'destroyed site'
                   )) AS violent_events,
                   array_agg(id ORDER BY year) AS event_ids
            FROM history_events
            WHERE world_id = $1 AND site_id IS NOT NULL
            GROUP BY site_id, year / 20
            HAVING COUNT(*) >= 5
        )
        SELECT site_id, start_year, end_year, creative_events,
               violent_events, event_ids
        FROM site_decades
        WHERE creative_events >= 3 AND violent_events = 0
    """, world_id)

    count = 0
    for arc in arcs:
        start_tick = arc["start_year"] * 403200
        end_tick = arc["end_year"] * 403200
        # Limit event list to top 20 for storage
        events = list(arc["event_ids"])[:20]

        await conn.execute("""
            INSERT INTO narrative_arcs
                (world_id, arc_type, start_tick, end_tick, key_events,
                 resolution, dramatic_weight)
            VALUES ($1, 'golden_age', $2, $3, $4, 'ongoing', 0)
            ON CONFLICT DO NOTHING
        """, world_id, start_tick, end_tick, events)
        count += 1

    log.info("  golden_age: %d arcs", count)
    return count


async def _detect_megabeast_attack(conn, world_id: int) -> int:
    """Detect megabeast_attack arcs from beast attack event collections."""
    arcs = await conn.fetch("""
        SELECT hec.id AS collection_id, hec.site_id,
               hec.start_year, hec.end_year,
               array_agg(ce.event_id ORDER BY ce.event_id) AS event_ids,
               COUNT(ce.event_id) AS event_count
        FROM history_event_collections hec
        JOIN collection_events ce ON ce.world_id = hec.world_id
            AND ce.collection_id = hec.id
        WHERE hec.world_id = $1
            AND hec.type = 'beast attack'
        GROUP BY hec.id, hec.site_id, hec.start_year, hec.end_year
    """, world_id)

    count = 0
    for arc in arcs:
        start_tick = (arc["start_year"] or 0) * 403200
        end_tick = (arc["end_year"] or arc["start_year"] or 0) * 403200
        events = list(arc["event_ids"])[:50]

        await conn.execute("""
            INSERT INTO narrative_arcs
                (world_id, arc_type, start_tick, end_tick, key_events,
                 resolution, dramatic_weight)
            VALUES ($1, 'megabeast_attack', $2, $3, $4, 'ongoing', 0)
            ON CONFLICT DO NOTHING
        """, world_id, start_tick, end_tick, events)
        count += 1

    log.info("  megabeast_attack: %d arcs", count)
    return count


async def _detect_succession_crisis(conn, world_id: int) -> int:
    """Detect succession_crisis: leader death + political change within 5 years."""
    arcs = await conn.fetch("""
        WITH leader_deaths AS (
            SELECT he.id AS death_id, he.year, he.site_id,
                   (he.details->>'hf_id')::int AS hf_id
            FROM history_events he
            JOIN historical_figures hf
                ON hf.world_id = he.world_id
                AND hf.id = (he.details->>'hf_id')::int
            WHERE he.world_id = $1
                AND he.event_type = 'hf died'
                AND hf.prominence_score > 0.3
        ),
        political AS (
            SELECT ld.death_id, ld.year AS death_year, ld.hf_id,
                   array_agg(pe.id ORDER BY pe.year) AS political_ids,
                   MIN(pe.year) AS first_political_year,
                   MAX(pe.year) AS last_political_year
            FROM leader_deaths ld
            JOIN history_events pe
                ON pe.world_id = $1
                AND pe.event_type IN ('entity overthrown', 'new site leader',
                                       'site taken over', 'entity dissolved',
                                       'create entity position')
                AND pe.year BETWEEN ld.year AND ld.year + 5
                AND pe.site_id = ld.site_id
            WHERE ld.site_id IS NOT NULL
            GROUP BY ld.death_id, ld.year, ld.hf_id
        )
        SELECT death_id, death_year, hf_id, political_ids,
               first_political_year, last_political_year
        FROM political
    """, world_id)

    count = 0
    for arc in arcs:
        start_tick = arc["death_year"] * 403200
        end_tick = (arc["last_political_year"] or arc["death_year"]) * 403200
        events = [arc["death_id"]] + list(arc["political_ids"])
        characters = [{"hf_id": arc["hf_id"], "role": "fallen_leader"}]

        await conn.execute("""
            INSERT INTO narrative_arcs
                (world_id, arc_type, start_tick, end_tick, key_events,
                 characters, resolution, dramatic_weight)
            VALUES ($1, 'succession_crisis', $2, $3, $4, $5, 'ongoing', 0)
            ON CONFLICT DO NOTHING
        """, world_id, start_tick, end_tick, events, characters)
        count += 1

    log.info("  succession_crisis: %d arcs", count)
    return count


async def _compute_arc_weights(conn, world_id: int) -> None:
    """Set dramatic_weight for each arc based on its constituent events."""
    await conn.execute("""
        UPDATE narrative_arcs na SET dramatic_weight = sub.avg_weight
        FROM (
            SELECT na2.id,
                   COALESCE(AVG(ne.narrative_weight), 0) AS avg_weight
            FROM narrative_arcs na2
            LEFT JOIN LATERAL jsonb_array_elements_text(na2.key_events) AS eid_text ON TRUE
            LEFT JOIN narrative_events ne
                ON ne.world_id = na2.world_id AND ne.event_id = eid_text::int
            WHERE na2.world_id = $1
            GROUP BY na2.id
        ) sub
        WHERE na.id = sub.id AND na.world_id = $1
    """, world_id)
    log.info("  Arc weights computed from narrative_events")


# ═══════════════════════════════════════════════════════════════════════
# Event Clustering (3.6.8)
# ═══════════════════════════════════════════════════════════════════════

async def detect_clusters(conn, world_id: int, force: bool = False) -> dict:
    """Group temporally adjacent events into clusters. Populates event_clusters.

    Clusters events within 5 years at the same site by dominant type.
    """
    log.info("Event clustering: starting for world %d", world_id)

    if force:
        await conn.execute(
            "DELETE FROM event_clusters WHERE world_id = $1", world_id)

    counts = {}

    for cluster_type, event_types in [
        ("siege", ["attacked site", "hf attacked site", "field battle",
                   "plundered site", "destroyed site", "razed structure",
                   "hf died"]),
        ("combat_encounter", ["hf simple battle event", "hf wounded",
                               "creature devoured"]),
        ("construction", ["created structure", "created site",
                          "created world construction"]),
        ("diplomacy", ["trade", "agreement formed"]),
        ("cultural", ["ceremony", "competition", "performance",
                      "procession", "written content composed"]),
    ]:
        n = await _cluster_by_type(
            conn, world_id, cluster_type, event_types,
            window_years=5, min_events=3)
        counts[cluster_type] = n

    total = sum(counts.values())
    log.info("Event clustering complete: %d clusters (%s)", total, counts)
    return {"total_clusters": total, "by_type": counts}


async def _cluster_by_type(conn, world_id: int, cluster_type: str,
                           event_types: list[str], window_years: int,
                           min_events: int) -> int:
    """Cluster events of given types within a time window at the same site."""
    # Build IN clause for event types
    placeholders = ", ".join(f"${i+2}" for i in range(len(event_types)))

    query = f"""
        SELECT site_id, (year / {window_years}) AS window,
               MIN(year) AS start_year, MAX(year) AS end_year,
               array_agg(id ORDER BY year, id) AS event_ids,
               COUNT(*) AS event_count
        FROM history_events
        WHERE world_id = $1
            AND event_type IN ({placeholders})
            AND site_id IS NOT NULL
        GROUP BY site_id, year / {window_years}
        HAVING COUNT(*) >= {min_events}
    """

    clusters = await conn.fetch(query, world_id, *event_types)

    count = 0
    for cl in clusters:
        start_tick = cl["start_year"] * 403200
        end_tick = cl["end_year"] * 403200
        events = list(cl["event_ids"])[:100]  # Cap at 100 per cluster

        await conn.execute("""
            INSERT INTO event_clusters
                (world_id, cluster_type, start_tick, end_tick, event_ids)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (world_id, cluster_type, start_tick) DO NOTHING
        """, world_id, cluster_type, start_tick, end_tick, events)
        count += 1

    log.info("  %s: %d clusters", cluster_type, count)
    return count
