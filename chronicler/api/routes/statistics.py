"""Statistics and population-model analysis routes."""

from fastapi import APIRouter, Query, Request

router = APIRouter()


@router.get("/statistics/population-model")
async def population_model(request: Request, world_id: int = Query(...)):
    """Return comprehensive population-model statistics for a world.

    Covers hf_entity_links, hf_site_links, entity_populations,
    cross-reference breakdowns, race distributions, and special flags.
    """
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        # ── 1. Global totals ────────────────────────────────────────
        totals = await conn.fetchrow(
            "SELECT COUNT(*) AS total, "
            "       COUNT(*) FILTER (WHERE death_year IS NULL) AS alive "
            "FROM historical_figures WHERE world_id = $1",
            world_id,
        )

        total_entity_links = await conn.fetchval(
            "SELECT COUNT(*) FROM hf_entity_links WHERE world_id = $1", world_id
        )
        total_site_links = await conn.fetchval(
            "SELECT COUNT(*) FROM hf_site_links WHERE world_id = $1", world_id
        )

        # ── 2. hf_entity_links by link_type ─────────────────────────
        el_rows = await conn.fetch(
            """
            SELECT hel.link_type,
                   COUNT(*)                                         AS cnt,
                   COUNT(DISTINCT hel.hf_id)                        AS unique_hfs,
                   COUNT(DISTINCT hel.entity_id)                    AS unique_entities,
                   COUNT(*) FILTER (WHERE hf.death_year IS NULL)    AS alive,
                   COUNT(*) FILTER (WHERE hf.death_year IS NOT NULL) AS dead
            FROM hf_entity_links hel
            JOIN historical_figures hf
                ON hf.world_id = hel.world_id AND hf.id = hel.hf_id
            WHERE hel.world_id = $1
            GROUP BY hel.link_type
            ORDER BY cnt DESC
            """,
            world_id,
        )
        entity_link_types = [
            {
                "link_type": r["link_type"],
                "count": r["cnt"],
                "unique_hfs": r["unique_hfs"],
                "unique_entities": r["unique_entities"],
                "alive": r["alive"],
                "dead": r["dead"],
            }
            for r in el_rows
        ]

        # ── 3. hf_site_links by link_type ───────────────────────────
        sl_rows = await conn.fetch(
            """
            SELECT hsl.link_type,
                   COUNT(*)                                         AS cnt,
                   COUNT(DISTINCT hsl.hf_id)                        AS unique_hfs,
                   COUNT(DISTINCT hsl.site_id)                      AS unique_sites,
                   COUNT(*) FILTER (WHERE hf.death_year IS NULL)    AS alive,
                   COUNT(*) FILTER (WHERE hf.death_year IS NOT NULL) AS dead
            FROM hf_site_links hsl
            JOIN historical_figures hf
                ON hf.world_id = hsl.world_id AND hf.id = hsl.hf_id
            WHERE hsl.world_id = $1
            GROUP BY hsl.link_type
            ORDER BY cnt DESC
            """,
            world_id,
        )
        site_link_types = [
            {
                "link_type": r["link_type"],
                "count": r["cnt"],
                "unique_hfs": r["unique_hfs"],
                "unique_sites": r["unique_sites"],
                "alive": r["alive"],
                "dead": r["dead"],
            }
            for r in sl_rows
        ]

        # ── 4. Cross-reference: HFs with entity links, site links, or both
        cross = await conn.fetchrow(
            """
            WITH e AS (SELECT DISTINCT hf_id FROM hf_entity_links WHERE world_id = $1),
                 s AS (SELECT DISTINCT hf_id FROM hf_site_links  WHERE world_id = $1)
            SELECT
                (SELECT COUNT(*) FROM e INTERSECT SELECT COUNT(*) FROM s) AS dummy,
                (SELECT COUNT(*) FROM (SELECT hf_id FROM e INTERSECT SELECT hf_id FROM s) x) AS both_links,
                (SELECT COUNT(*) FROM (SELECT hf_id FROM e EXCEPT    SELECT hf_id FROM s) x) AS entity_only,
                (SELECT COUNT(*) FROM (SELECT hf_id FROM s EXCEPT    SELECT hf_id FROM e) x) AS site_only
            """,
            world_id,
        )

        # ── 5. Site coverage ────────────────────────────────────────
        site_coverage = await conn.fetch(
            """
            SELECT s.type,
                   COUNT(DISTINCT s.id) AS total_sites,
                   COUNT(DISTINCT hsl.site_id) AS sites_with_links,
                   COUNT(DISTINCT hsl.hf_id) FILTER (WHERE hf.death_year IS NULL) AS alive_residents
            FROM sites s
            LEFT JOIN hf_site_links hsl
                ON hsl.world_id = s.world_id AND hsl.site_id = s.id
            LEFT JOIN historical_figures hf
                ON hf.world_id = hsl.world_id AND hf.id = hsl.hf_id
            WHERE s.world_id = $1
            GROUP BY s.type
            ORDER BY total_sites DESC
            """,
            world_id,
        )
        site_coverage_data = [
            {
                "type": r["type"],
                "total_sites": r["total_sites"],
                "sites_with_links": r["sites_with_links"],
                "alive_residents": r["alive_residents"],
            }
            for r in site_coverage
        ]

        # ── 6. Race breakdown of site residents (top 20) ────────────
        race_breakdown = await conn.fetch(
            """
            SELECT hf.race, hsl.link_type, COUNT(*) AS cnt
            FROM hf_site_links hsl
            JOIN historical_figures hf
                ON hf.world_id = hsl.world_id AND hf.id = hsl.hf_id
            WHERE hsl.world_id = $1
            GROUP BY hf.race, hsl.link_type
            ORDER BY cnt DESC
            LIMIT 100
            """,
            world_id,
        )
        race_data = [
            {"race": r["race"], "link_type": r["link_type"], "count": r["cnt"]}
            for r in race_breakdown
        ]

        # ── 7. Special flags among site residents ────────────────────
        special = await conn.fetchrow(
            """
            SELECT
                COUNT(*) FILTER (WHERE hf.is_vampire)     AS vampires,
                COUNT(*) FILTER (WHERE hf.is_werebeast)   AS werebeasts,
                COUNT(*) FILTER (WHERE hf.is_necromancer)  AS necromancers,
                COUNT(*) FILTER (WHERE hf.is_deity)        AS deities,
                COUNT(*) FILTER (WHERE hf.is_ghost)        AS ghosts
            FROM hf_site_links hsl
            JOIN historical_figures hf
                ON hf.world_id = hsl.world_id AND hf.id = hsl.hf_id
            WHERE hsl.world_id = $1
            """,
            world_id,
        )

        # ── 8. entity_populations (DF-native counts by civ) ─────────
        ep_rows = await conn.fetch(
            """
            SELECT ep.civ_id, e.name AS civ_name, ep.race, ep.count
            FROM entity_populations ep
            LEFT JOIN entities e ON e.world_id = ep.world_id AND e.id = ep.civ_id
            WHERE ep.world_id = $1
            ORDER BY ep.count DESC
            """,
            world_id,
        )
        entity_pops = [
            {
                "civ_id": r["civ_id"],
                "civ_name": r["civ_name"],
                "race": r["race"],
                "count": r["count"],
            }
            for r in ep_rows
        ]

        # ── 9. Population vs Residents divergence per site ───────────
        pop_vs_res = await conn.fetch(
            """
            WITH entity_pop AS (
                SELECT s.id AS site_id, s.name AS site_name, s.type AS site_type,
                       COUNT(DISTINCT hel.hf_id) FILTER (WHERE hf.death_year IS NULL AND hel.link_type = 'member') AS population
                FROM sites s
                JOIN entities e ON e.world_id = s.world_id AND e.id = s.owner_entity_id
                JOIN hf_entity_links hel ON hel.world_id = e.world_id AND hel.entity_id = e.id
                JOIN historical_figures hf ON hf.world_id = hel.world_id AND hf.id = hel.hf_id
                WHERE s.world_id = $1
                GROUP BY s.id, s.name, s.type
            ),
            site_res AS (
                SELECT hsl.site_id,
                       COUNT(DISTINCT hsl.hf_id) FILTER (WHERE hf.death_year IS NULL) AS residents
                FROM hf_site_links hsl
                JOIN historical_figures hf ON hf.world_id = hsl.world_id AND hf.id = hsl.hf_id
                WHERE hsl.world_id = $1
                GROUP BY hsl.site_id
            )
            SELECT ep.site_id, ep.site_name, ep.site_type, ep.population,
                   COALESCE(sr.residents, 0) AS residents
            FROM entity_pop ep
            LEFT JOIN site_res sr ON sr.site_id = ep.site_id
            WHERE ep.population > 0 OR COALESCE(sr.residents, 0) > 0
            ORDER BY ABS(ep.population - COALESCE(sr.residents, 0)) DESC
            LIMIT 50
            """,
            world_id,
        )
        divergence = [
            {
                "site_id": r["site_id"],
                "site_name": r["site_name"],
                "site_type": r["site_type"],
                "population": r["population"],
                "residents": r["residents"],
            }
            for r in pop_vs_res
        ]

    return {
        "global": {
            "total_hfs": totals["total"],
            "alive_hfs": totals["alive"],
            "total_entity_links": total_entity_links,
            "total_site_links": total_site_links,
        },
        "entity_link_types": entity_link_types,
        "site_link_types": site_link_types,
        "cross_reference": {
            "both_links": cross["both_links"],
            "entity_only": cross["entity_only"],
            "site_only": cross["site_only"],
        },
        "site_coverage": site_coverage_data,
        "race_breakdown": race_data,
        "special_flags": {
            "vampires": special["vampires"],
            "werebeasts": special["werebeasts"],
            "necromancers": special["necromancers"],
            "deities": special["deities"],
            "ghosts": special["ghosts"],
        },
        "entity_populations": entity_pops,
        "divergence": divergence,
    }
