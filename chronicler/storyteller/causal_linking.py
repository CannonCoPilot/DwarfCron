"""Stage 3.6.2: Causal Event Linking.

Detects cause→effect chains between history_events using temporal
proximity and logical rules. Populates event_causal_links table.

Link types:
  - cascading_death: military death within 200 ticks of next death
  - invasion_triggered: invasion/attack within 500 ticks before combat deaths
  - economic_collapse: food/drink depletion before starvation death
  - social_cascade: death of important figure before unhappiness/tantrum
  - military_weakened: >30% squad losses before next invasion
"""

import logging

log = logging.getLogger(__name__)


async def detect_causal_links(conn, world_id: int, force: bool = False) -> dict:
    """Detect and store causal links for all events in a world.

    Returns summary with link counts by type.
    """
    log.info("Causal linking: starting for world %d", world_id)

    if force:
        result = await conn.execute(
            "DELETE FROM event_causal_links WHERE world_id = $1", world_id)
        log.info("  Cleared existing: %s", result)

    counts = {}

    # Run each detection rule
    n = await _detect_cascading_deaths(conn, world_id)
    counts["cascading_death"] = n

    n = await _detect_invasion_triggered(conn, world_id)
    counts["invasion_triggered"] = n

    n = await _detect_economic_collapse(conn, world_id)
    counts["economic_collapse"] = n

    n = await _detect_social_cascade(conn, world_id)
    counts["social_cascade"] = n

    n = await _detect_military_weakened(conn, world_id)
    counts["military_weakened"] = n

    total = sum(counts.values())
    log.info("Causal linking complete: %d links (%s)", total, counts)
    return {"total_links": total, "by_type": counts}


async def _detect_cascading_deaths(conn, world_id: int) -> int:
    """Deaths within 200 years of each other at the same site = cascading.

    Uses year proximity since worldgen events don't have ticks.
    For each death at a site, link to the next death at the same site
    within 3 years.
    """
    result = await conn.execute("""
        INSERT INTO event_causal_links (world_id, cause_event_id, effect_event_id,
                                         link_type, confidence)
        SELECT DISTINCT ON (e2.id)
            $1, e1.id, e2.id, 'cascading_death', 0.6
        FROM history_events e1
        JOIN history_events e2
            ON e2.world_id = e1.world_id
            AND e2.event_type = 'hf died'
            AND e2.site_id = e1.site_id
            AND e2.site_id IS NOT NULL
            AND e2.year BETWEEN e1.year AND e1.year + 3
            AND e2.id > e1.id
            AND e2.id != e1.id
        WHERE e1.world_id = $1
            AND e1.event_type = 'hf died'
            AND e1.site_id IS NOT NULL
        ORDER BY e2.id, e1.id
        ON CONFLICT (world_id, cause_event_id, effect_event_id) DO NOTHING
    """, world_id)
    n = int(result.split()[-1]) if result else 0
    log.info("  cascading_death: %d links", n)
    return n


async def _detect_invasion_triggered(conn, world_id: int) -> int:
    """Attack/invasion events within 5 years before combat deaths at same site."""
    result = await conn.execute("""
        INSERT INTO event_causal_links (world_id, cause_event_id, effect_event_id,
                                         link_type, confidence)
        SELECT DISTINCT ON (death.id)
            $1, attack.id, death.id, 'invasion_triggered', 0.8
        FROM history_events attack
        JOIN history_events death
            ON death.world_id = attack.world_id
            AND death.event_type = 'hf died'
            AND death.site_id = attack.site_id
            AND death.site_id IS NOT NULL
            AND death.year BETWEEN attack.year AND attack.year + 5
            AND death.id > attack.id
        WHERE attack.world_id = $1
            AND attack.event_type IN ('attacked site', 'hf attacked site',
                                       'field battle', 'plundered site')
            AND attack.site_id IS NOT NULL
        ORDER BY death.id, attack.year DESC
        ON CONFLICT (world_id, cause_event_id, effect_event_id) DO NOTHING
    """, world_id)
    n = int(result.split()[-1]) if result else 0
    log.info("  invasion_triggered: %d links", n)
    return n


async def _detect_economic_collapse(conn, world_id: int) -> int:
    """Site destruction/plundering before starvation/thirst deaths.

    If a site is attacked/plundered and within 10 years someone starves
    or dies of thirst at the same site, link as economic_collapse.
    """
    result = await conn.execute("""
        INSERT INTO event_causal_links (world_id, cause_event_id, effect_event_id,
                                         link_type, confidence)
        SELECT DISTINCT ON (death.id)
            $1, attack.id, death.id, 'economic_collapse', 0.7
        FROM history_events attack
        JOIN history_events death
            ON death.world_id = attack.world_id
            AND death.event_type = 'hf died'
            AND death.site_id = attack.site_id
            AND death.site_id IS NOT NULL
            AND death.year BETWEEN attack.year AND attack.year + 10
            AND death.id > attack.id
            AND (death.details->>'death_cause') IN ('thirst', 'hunger',
                                                     'starved', 'starvation')
        WHERE attack.world_id = $1
            AND attack.event_type IN ('attacked site', 'plundered site',
                                       'destroyed site', 'razed structure')
            AND attack.site_id IS NOT NULL
        ORDER BY death.id, attack.year DESC
        ON CONFLICT (world_id, cause_event_id, effect_event_id) DO NOTHING
    """, world_id)
    n = int(result.split()[-1]) if result else 0
    log.info("  economic_collapse: %d links", n)
    return n


async def _detect_social_cascade(conn, world_id: int) -> int:
    """Death of important figure (prominence > 0.5) before entity upheaval.

    If a prominent HF dies and within 5 years the same entity experiences
    overthrow, dissolution, or leadership change, link as social_cascade.
    """
    result = await conn.execute("""
        INSERT INTO event_causal_links (world_id, cause_event_id, effect_event_id,
                                         link_type, confidence)
        SELECT DISTINCT ON (upheaval.id)
            $1, death.id, upheaval.id, 'social_cascade', 0.5
        FROM history_events death
        JOIN historical_figures hf
            ON hf.world_id = death.world_id
            AND hf.id = (death.details->>'hf_id')::int
            AND hf.prominence_score > 0.5
        JOIN hf_entity_links hel
            ON hel.world_id = death.world_id
            AND hel.hf_id = hf.id
        JOIN history_events upheaval
            ON upheaval.world_id = death.world_id
            AND upheaval.event_type IN ('entity overthrown', 'entity dissolved',
                                         'new site leader', 'site taken over')
            AND upheaval.year BETWEEN death.year AND death.year + 5
            AND upheaval.id > death.id
        JOIN event_entity_xref eex
            ON eex.world_id = upheaval.world_id
            AND eex.event_id = upheaval.id
            AND eex.entity_id = hel.entity_id
        WHERE death.world_id = $1
            AND death.event_type = 'hf died'
        ORDER BY upheaval.id, death.year DESC
        ON CONFLICT (world_id, cause_event_id, effect_event_id) DO NOTHING
    """, world_id)
    n = int(result.split()[-1]) if result else 0
    log.info("  social_cascade: %d links", n)
    return n


async def _detect_military_weakened(conn, world_id: int) -> int:
    """Multiple deaths at a site followed by attack = military_weakened.

    If 3+ deaths occur at a site within 5 years and then the site is
    attacked within 10 years, the deaths weakened the defense.
    """
    # Find sites with clustered deaths
    clusters = await conn.fetch("""
        SELECT site_id, MIN(id) AS first_death_id, MAX(year) AS last_death_year,
               COUNT(*) AS death_count
        FROM history_events
        WHERE world_id = $1
            AND event_type = 'hf died'
            AND site_id IS NOT NULL
        GROUP BY site_id, year / 5
        HAVING COUNT(*) >= 3
    """, world_id)

    total = 0
    for cluster in clusters:
        result = await conn.execute("""
            INSERT INTO event_causal_links (world_id, cause_event_id, effect_event_id,
                                             link_type, confidence)
            SELECT DISTINCT ON (attack.id)
                $1, $2, attack.id, 'military_weakened',
                LEAST(0.9, 0.3 + $5::float * 0.1)
            FROM history_events attack
            WHERE attack.world_id = $1
                AND attack.event_type IN ('attacked site', 'hf attacked site',
                                           'field battle', 'plundered site')
                AND attack.site_id = $3
                AND attack.year BETWEEN $4 AND $4 + 10
            ORDER BY attack.id
            ON CONFLICT (world_id, cause_event_id, effect_event_id) DO NOTHING
        """, world_id, cluster["first_death_id"], cluster["site_id"],
             cluster["last_death_year"], cluster["death_count"])
        n = int(result.split()[-1]) if result else 0
        total += n

    log.info("  military_weakened: %d links from %d death clusters", total, len(clusters))
    return total
