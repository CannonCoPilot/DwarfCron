"""Demographics and interactive population analysis routes.

Provides aggregate demographic data, time-series membership curves,
race/entity breakdowns, and civilization comparison data for the
Demographics sub-tab in the Statistics panel.
"""

from fastapi import APIRouter, Query, Request

router = APIRouter()


@router.get("/demographics/overview")
async def demographics_overview(request: Request, world_id: int = Query(...)):
    """Global demographic overview: age distributions, race totals,
    entity type breakdown, alive/dead by race, lifespan statistics."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        # ── Race distribution (alive vs dead) ──
        race_rows = await conn.fetch("""
            SELECT hf.race,
                   COUNT(*) AS total,
                   COUNT(*) FILTER (WHERE hf.death_year IS NULL) AS alive,
                   COUNT(*) FILTER (WHERE hf.death_year IS NOT NULL) AS dead
            FROM historical_figures hf
            WHERE hf.world_id = $1
            GROUP BY hf.race
            ORDER BY total DESC
        """, world_id)

        # ── Entity type distribution (count of entities per type) ──
        entity_type_rows = await conn.fetch("""
            SELECT e.type,
                   COUNT(*) AS entity_count,
                   COALESCE(SUM(mc.cnt), 0) AS total_members,
                   COALESCE(SUM(mc.alive_cnt), 0) AS alive_members
            FROM entities e
            LEFT JOIN LATERAL (
                SELECT COUNT(*) AS cnt,
                       COUNT(*) FILTER (WHERE hf.death_year IS NULL) AS alive_cnt
                FROM hf_entity_links hel
                JOIN historical_figures hf ON hf.world_id = hel.world_id AND hf.id = hel.hf_id
                WHERE hel.world_id = e.world_id AND hel.entity_id = e.id
                  AND hel.link_type = 'member'
            ) mc ON true
            WHERE e.world_id = $1
            GROUP BY e.type
            ORDER BY entity_count DESC
        """, world_id)

        # ── Age distribution (living HFs, binned by decades) ──
        world_year = await conn.fetchval("""
            SELECT COALESCE(
                (SELECT MAX(year) FROM history_events WHERE world_id = $1),
                250
            )
        """, world_id)
        age_bins = await conn.fetch("""
            SELECT
                CASE
                    WHEN age < 20 THEN '0-19'
                    WHEN age < 50 THEN '20-49'
                    WHEN age < 100 THEN '50-99'
                    WHEN age < 200 THEN '100-199'
                    WHEN age < 500 THEN '200-499'
                    WHEN age < 1000 THEN '500-999'
                    ELSE '1000+'
                END AS age_bin,
                COUNT(*) AS cnt
            FROM (
                SELECT ($2 - hf.birth_year) AS age
                FROM historical_figures hf
                WHERE hf.world_id = $1 AND hf.death_year IS NULL
                  AND hf.birth_year IS NOT NULL AND hf.birth_year >= 0
            ) sub
            GROUP BY age_bin
            ORDER BY MIN(age)
        """, world_id, world_year)

        # ── Lifespan statistics for dead HFs ──
        lifespan = await conn.fetchrow("""
            SELECT
                COUNT(*) AS dead_count,
                ROUND(AVG(death_year - birth_year)::numeric, 1) AS avg_lifespan,
                MIN(death_year - birth_year) AS min_lifespan,
                MAX(death_year - birth_year) AS max_lifespan,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY death_year - birth_year) AS median_lifespan
            FROM historical_figures
            WHERE world_id = $1 AND death_year IS NOT NULL
              AND birth_year IS NOT NULL AND birth_year >= 0
              AND death_year >= birth_year
        """, world_id)

        # ── Caste (gender) distribution ──
        caste_rows = await conn.fetch("""
            SELECT COALESCE(caste, 'unknown') AS caste,
                   COUNT(*) AS total,
                   COUNT(*) FILTER (WHERE death_year IS NULL) AS alive
            FROM historical_figures
            WHERE world_id = $1
            GROUP BY caste
            ORDER BY total DESC
        """, world_id)

        # ── Top civilizations by living members ──
        top_civs = await conn.fetch("""
            SELECT e.id, e.name, e.race,
                   COUNT(DISTINCT hel.hf_id) AS total_members,
                   COUNT(DISTINCT hel.hf_id) FILTER (WHERE hf.death_year IS NULL) AS alive_members,
                   COALESCE(ep.pop, 0) AS df_population
            FROM entities e
            JOIN hf_entity_links hel ON hel.world_id = e.world_id AND hel.entity_id = e.id
                AND hel.link_type = 'member'
            JOIN historical_figures hf ON hf.world_id = hel.world_id AND hf.id = hel.hf_id
            LEFT JOIN (
                SELECT civ_id, SUM(count) AS pop
                FROM entity_populations WHERE world_id = $1
                GROUP BY civ_id
            ) ep ON ep.civ_id = e.id
            WHERE e.world_id = $1 AND e.type = 'civilization'
            GROUP BY e.id, e.name, e.race, ep.pop
            ORDER BY alive_members DESC
            LIMIT 20
        """, world_id)

        # ── Birth/death events per year (for population curve) ──
        birth_death_years = await conn.fetch("""
            SELECT year, births, deaths FROM (
                SELECT year, SUM(births) AS births, SUM(deaths) AS deaths FROM (
                    SELECT birth_year AS year, COUNT(*) AS births, 0 AS deaths
                    FROM historical_figures
                    WHERE world_id = $1 AND birth_year IS NOT NULL AND birth_year >= 0
                    GROUP BY birth_year
                    UNION ALL
                    SELECT death_year AS year, 0 AS births, COUNT(*) AS deaths
                    FROM historical_figures
                    WHERE world_id = $1 AND death_year IS NOT NULL
                    GROUP BY death_year
                ) combined
                GROUP BY year
            ) agg
            ORDER BY year
        """, world_id)

    return {
        "world_year": world_year,
        "race_distribution": [
            {"race": r["race"] or "unknown", "total": r["total"],
             "alive": r["alive"], "dead": r["dead"]}
            for r in race_rows
        ],
        "entity_types": [
            {"type": r["type"] or "unknown", "entity_count": r["entity_count"],
             "total_members": r["total_members"], "alive_members": r["alive_members"]}
            for r in entity_type_rows
        ],
        "age_distribution": [
            {"bin": r["age_bin"], "count": r["cnt"]} for r in age_bins
        ],
        "lifespan_stats": {
            "dead_count": lifespan["dead_count"],
            "avg_lifespan": float(lifespan["avg_lifespan"] or 0),
            "min_lifespan": lifespan["min_lifespan"],
            "max_lifespan": lifespan["max_lifespan"],
            "median_lifespan": float(lifespan["median_lifespan"] or 0),
        },
        "caste_distribution": [
            {"caste": r["caste"], "total": r["total"], "alive": r["alive"]}
            for r in caste_rows
        ],
        "top_civilizations": [
            {"id": r["id"], "name": r["name"], "race": r["race"],
             "total_members": r["total_members"], "alive_members": r["alive_members"],
             "df_population": r["df_population"]}
            for r in top_civs
        ],
        "birth_death_timeline": [
            {"year": r["year"], "births": r["births"], "deaths": r["deaths"]}
            for r in birth_death_years
        ],
    }


@router.get("/demographics/entity-list")
async def demographics_entity_list(request: Request, world_id: int = Query(...)):
    """Return all entities with member counts for the entity selector dropdown."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT e.id, e.name, e.type, e.race,
                   COALESCE(mc.total, 0) AS total_members,
                   COALESCE(mc.alive, 0) AS alive_members
            FROM entities e
            LEFT JOIN LATERAL (
                SELECT COUNT(*) AS total,
                       COUNT(*) FILTER (WHERE hf.death_year IS NULL) AS alive
                FROM hf_entity_links hel
                JOIN historical_figures hf ON hf.world_id = hel.world_id AND hf.id = hel.hf_id
                WHERE hel.world_id = e.world_id AND hel.entity_id = e.id
                  AND hel.link_type IN ('member', 'former member')
            ) mc ON true
            WHERE e.world_id = $1
            ORDER BY COALESCE(mc.total, 0) DESC
        """, world_id)
    return [
        {"id": r["id"], "name": r["name"], "type": r["type"], "race": r["race"],
         "total_members": r["total_members"], "alive_members": r["alive_members"]}
        for r in rows
    ]


@router.get("/demographics/time-series")
async def demographics_time_series(
    request: Request,
    world_id: int = Query(...),
    entity_id: int = Query(...),
):
    """Compute year-by-year living membership for an entity.

    For each year in the world's history, counts HFs that were:
    - Born on or before that year (birth_year <= year)
    - Not yet dead (death_year IS NULL OR death_year > year)
    - Had an active membership link (link_type = 'member')

    Since hf_entity_links don't have start/end dates in DF legends,
    we use hf_entity_links.link_type to determine current status and
    approximate membership start from the entity's founding or the HF's birth.

    Returns yearly data points for the line chart.
    """
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        # Get entity info
        entity = await conn.fetchrow(
            "SELECT id, name, type, race FROM entities WHERE world_id = $1 AND id = $2",
            world_id, entity_id,
        )
        if not entity:
            return {"error": "Entity not found", "years": []}

        # Get world year range
        year_range = await conn.fetchrow("""
            SELECT
                COALESCE(MIN(hf.birth_year), 0) AS min_year,
                COALESCE(MAX(GREATEST(
                    COALESCE(hf.death_year, 0),
                    COALESCE(hf.birth_year, 0)
                )), 250) AS max_year
            FROM hf_entity_links hel
            JOIN historical_figures hf ON hf.world_id = hel.world_id AND hf.id = hel.hf_id
            WHERE hel.world_id = $1 AND hel.entity_id = $2
              AND hel.link_type IN ('member', 'former member')
              AND hf.birth_year IS NOT NULL AND hf.birth_year >= 0
        """, world_id, entity_id)

        if not year_range or year_range["min_year"] is None:
            return {
                "entity": {"id": entity["id"], "name": entity["name"],
                           "type": entity["type"]},
                "years": [],
            }

        min_yr = max(0, year_range["min_year"])
        max_yr = year_range["max_year"]

        # Fetch all member HFs with birth/death years
        # Current members: alive at some point with link_type = 'member'
        # Former members: had membership but left (link_type = 'former member')
        members = await conn.fetch("""
            SELECT hf.id AS hf_id, hf.birth_year, hf.death_year,
                   hel.link_type
            FROM hf_entity_links hel
            JOIN historical_figures hf ON hf.world_id = hel.world_id AND hf.id = hel.hf_id
            WHERE hel.world_id = $1 AND hel.entity_id = $2
              AND hel.link_type IN ('member', 'former member')
              AND hf.birth_year IS NOT NULL AND hf.birth_year >= 0
        """, world_id, entity_id)

        if not members:
            return {
                "entity": {"id": entity["id"], "name": entity["name"],
                           "type": entity["type"]},
                "years": [],
            }

        # For former members, try to find when they left via events
        former_hf_ids = [m["hf_id"] for m in members if m["link_type"] == "former member"]
        leave_years: dict[int, int] = {}
        if former_hf_ids:
            # Look for 'change hf entity link' events that ended membership
            leave_rows = await conn.fetch("""
                SELECT DISTINCT ON (he.hf_id_1)
                       he.hf_id_1 AS hf_id, he.year
                FROM history_events he
                WHERE he.world_id = $1
                  AND he.event_type = 'change hf entity link'
                  AND he.hf_id_1 = ANY($2::int[])
                  AND he.entity_id_1 = $3
                ORDER BY he.hf_id_1, he.year DESC
            """, world_id, former_hf_ids, entity_id)
            for r in leave_rows:
                leave_years[r["hf_id"]] = r["year"]

        # Build year-by-year counts
        # Determine step size based on range to keep data manageable
        total_years = max_yr - min_yr + 1
        step = max(1, total_years // 500)  # Max ~500 data points

        years_data = []
        for year in range(min_yr, max_yr + 1, step):
            living_members = 0
            total_ever = 0
            for m in members:
                by = m["birth_year"]
                dy = m["death_year"]
                # Was this HF alive at this year?
                if by > year:
                    continue  # Not yet born
                if dy is not None and dy <= year:
                    continue  # Already dead

                total_ever += 1

                # Was this HF a member at this year?
                if m["link_type"] == "member":
                    # Current member: was a member from birth (approximation) until now
                    living_members += 1
                elif m["link_type"] == "former member":
                    # Former member: was a member until they left
                    left_yr = leave_years.get(m["hf_id"])
                    if left_yr is None or year < left_yr:
                        living_members += 1

            years_data.append({
                "year": year,
                "living_members": living_members,
                "living_total": total_ever,
            })

    return {
        "entity": {
            "id": entity["id"],
            "name": entity["name"],
            "type": entity["type"],
            "race": entity["race"],
        },
        "years": years_data,
    }


@router.get("/demographics/civilization-comparison")
async def civilization_comparison(request: Request, world_id: int = Query(...)):
    """Compare all civilizations side-by-side: members, citizens, residents,
    DF population, sites, races."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            WITH civ_members AS (
                SELECT hel.entity_id,
                       COUNT(DISTINCT hel.hf_id) AS total_members,
                       COUNT(DISTINCT hel.hf_id) FILTER (
                           WHERE hel.link_type = 'member'
                       ) AS current_members,
                       COUNT(DISTINCT hel.hf_id) FILTER (
                           WHERE hel.link_type = 'member' AND hf.death_year IS NULL
                       ) AS alive_current,
                       COUNT(DISTINCT hel.hf_id) FILTER (
                           WHERE hf.death_year IS NULL
                       ) AS alive_total
                FROM hf_entity_links hel
                JOIN historical_figures hf ON hf.world_id = hel.world_id AND hf.id = hel.hf_id
                WHERE hel.world_id = $1
                  AND hel.link_type IN ('member', 'former member')
                GROUP BY hel.entity_id
            ),
            civ_sites AS (
                SELECT cs.parent_id AS civ_id, COUNT(*) AS site_count
                FROM sites s
                JOIN (
                    SELECT sg.id AS sg_id, (el->>'target')::int AS parent_id
                    FROM entities sg, jsonb_array_elements(sg.details->'entity_links') el
                    WHERE sg.world_id = $1 AND sg.type = 'sitegovernment'
                      AND el->>'type' = 'PARENT'
                ) cs ON cs.sg_id = s.owner_entity_id
                WHERE s.world_id = $1
                GROUP BY cs.parent_id
            ),
            ep_totals AS (
                SELECT civ_id, SUM(count) AS pop
                FROM entity_populations WHERE world_id = $1
                GROUP BY civ_id
            ),
            race_counts AS (
                SELECT entity_id,
                       jsonb_agg(jsonb_build_object(
                           'race', race, 'count', cnt
                       ) ORDER BY cnt DESC) AS races
                FROM (
                    SELECT hel.entity_id, hf.race, COUNT(*) AS cnt
                    FROM hf_entity_links hel
                    JOIN historical_figures hf ON hf.world_id = hel.world_id AND hf.id = hel.hf_id
                    WHERE hel.world_id = $1 AND hel.link_type = 'member' AND hf.death_year IS NULL
                    GROUP BY hel.entity_id, hf.race
                ) sub
                GROUP BY entity_id
            )
            SELECT e.id, e.name, e.race AS primary_race,
                   COALESCE(cm.total_members, 0) AS total_members,
                   COALESCE(cm.current_members, 0) AS current_members,
                   COALESCE(cm.alive_current, 0) AS alive_current,
                   COALESCE(cm.alive_total, 0) AS alive_total,
                   COALESCE(cs.site_count, 0) AS site_count,
                   COALESCE(ep.pop, 0) AS df_population,
                   rc.races
            FROM entities e
            LEFT JOIN civ_members cm ON cm.entity_id = e.id
            LEFT JOIN civ_sites cs ON cs.civ_id = e.id
            LEFT JOIN ep_totals ep ON ep.civ_id = e.id
            LEFT JOIN race_counts rc ON rc.entity_id = e.id
            WHERE e.world_id = $1 AND e.type = 'civilization'
            ORDER BY COALESCE(cm.alive_current, 0) DESC
        """, world_id)

    return [
        {
            "id": r["id"],
            "name": r["name"],
            "primary_race": r["primary_race"],
            "total_members": r["total_members"],
            "current_members": r["current_members"],
            "alive_current": r["alive_current"],
            "alive_total": r["alive_total"],
            "site_count": r["site_count"],
            "df_population": r["df_population"],
            "races": r["races"],
        }
        for r in rows
    ]


@router.get("/demographics/race-lifespan")
async def race_lifespan(request: Request, world_id: int = Query(...)):
    """Lifespan statistics broken down by race — avg, min, max, median
    for each race with enough dead HFs."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT hf.race,
                   COUNT(*) AS sample_size,
                   ROUND(AVG(hf.death_year - hf.birth_year)::numeric, 1) AS avg_lifespan,
                   MIN(hf.death_year - hf.birth_year) AS min_lifespan,
                   MAX(hf.death_year - hf.birth_year) AS max_lifespan,
                   PERCENTILE_CONT(0.5) WITHIN GROUP (
                       ORDER BY hf.death_year - hf.birth_year
                   ) AS median_lifespan
            FROM historical_figures hf
            WHERE hf.world_id = $1
              AND hf.death_year IS NOT NULL
              AND hf.birth_year IS NOT NULL AND hf.birth_year >= 0
              AND hf.death_year >= hf.birth_year
            GROUP BY hf.race
            HAVING COUNT(*) >= 5
            ORDER BY AVG(hf.death_year - hf.birth_year) DESC
        """, world_id)

    return [
        {
            "race": r["race"] or "unknown",
            "sample_size": r["sample_size"],
            "avg_lifespan": float(r["avg_lifespan"] or 0),
            "min_lifespan": r["min_lifespan"],
            "max_lifespan": r["max_lifespan"],
            "median_lifespan": float(r["median_lifespan"] or 0),
        }
        for r in rows
    ]


@router.get("/demographics/death-causes")
async def death_causes(request: Request, world_id: int = Query(...)):
    """Death cause breakdown: how HFs die (struck, old age, murdered, etc.)
    plus death counts per year for a mortality timeline."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        # ── Cause of death distribution ──
        cause_rows = await conn.fetch("""
            SELECT COALESCE(details->>'cause', 'unknown') AS cause,
                   COUNT(*) AS cnt
            FROM history_events
            WHERE world_id = $1 AND event_type = 'hf died'
            GROUP BY details->>'cause'
            ORDER BY cnt DESC
        """, world_id)

        # ── Deaths by race (top 15) ──
        race_death_rows = await conn.fetch("""
            SELECT hf.race, COUNT(*) AS cnt,
                   ROUND(AVG(hf.death_year - hf.birth_year) FILTER (
                       WHERE hf.birth_year IS NOT NULL AND hf.birth_year >= 0
                   )::numeric, 1) AS avg_age_at_death
            FROM historical_figures hf
            WHERE hf.world_id = $1 AND hf.death_year IS NOT NULL
            GROUP BY hf.race
            ORDER BY cnt DESC
            LIMIT 15
        """, world_id)

        # ── Mortality timeline (deaths per decade) ──
        mortality_rows = await conn.fetch("""
            SELECT (death_year / 10) * 10 AS decade,
                   COUNT(*) AS deaths
            FROM historical_figures
            WHERE world_id = $1 AND death_year IS NOT NULL
            GROUP BY (death_year / 10) * 10
            ORDER BY decade
        """, world_id)

    return {
        "causes": [
            {"cause": r["cause"], "count": r["cnt"]} for r in cause_rows
        ],
        "deaths_by_race": [
            {"race": r["race"] or "unknown", "count": r["cnt"],
             "avg_age_at_death": float(r["avg_age_at_death"]) if r["avg_age_at_death"] else None}
            for r in race_death_rows
        ],
        "mortality_timeline": [
            {"decade": r["decade"], "deaths": r["deaths"]}
            for r in mortality_rows
        ],
    }


@router.get("/demographics/relationships")
async def relationships(request: Request, world_id: int = Query(...)):
    """Social relationship analysis: type distribution, family structure,
    romantic partnerships, and mentorship chains."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        # ── Relationship type distribution ──
        rel_rows = await conn.fetch("""
            SELECT link_type, COUNT(*) AS cnt
            FROM hf_links
            WHERE world_id = $1
            GROUP BY link_type
            ORDER BY cnt DESC
        """, world_id)

        # ── Family statistics ──
        family = await conn.fetchrow("""
            SELECT
                COUNT(*) FILTER (WHERE link_type = 'child') AS parent_child_links,
                COUNT(*) FILTER (WHERE link_type IN ('spouse', 'deceased spouse', 'former spouse')) AS marriage_links,
                COUNT(*) FILTER (WHERE link_type IN ('lover', 'former lover')) AS romantic_links,
                COUNT(*) FILTER (WHERE link_type IN ('master', 'apprentice', 'former master', 'former apprentice')) AS mentorship_links,
                COUNT(*) FILTER (WHERE link_type = 'deity') AS deity_worship_links
            FROM hf_links
            WHERE world_id = $1
        """, world_id)

        # ── Most connected HFs (by relationship count) ──
        connected = await conn.fetch("""
            SELECT hf.id, hf.name, hf.race,
                   COUNT(DISTINCT hl.id) AS relationship_count,
                   hf.death_year IS NULL AS is_alive
            FROM historical_figures hf
            JOIN hf_links hl ON hl.world_id = hf.world_id AND hl.hf_id = hf.id
            WHERE hf.world_id = $1
            GROUP BY hf.id, hf.name, hf.race, hf.death_year
            ORDER BY relationship_count DESC
            LIMIT 20
        """, world_id)

    return {
        "types": [
            {"type": r["link_type"], "count": r["cnt"]} for r in rel_rows
        ],
        "summary": {
            "parent_child": family["parent_child_links"],
            "marriages": family["marriage_links"],
            "romantic": family["romantic_links"],
            "mentorships": family["mentorship_links"],
            "deity_worship": family["deity_worship_links"],
        },
        "most_connected": [
            {"id": r["id"], "name": r["name"], "race": r["race"],
             "relationships": r["relationship_count"], "alive": r["is_alive"]}
            for r in connected
        ],
    }


@router.get("/demographics/conflicts")
async def conflicts(request: Request, world_id: int = Query(...)):
    """War and conflict analysis: wars over time, battle frequency,
    conflict types, and involved civilizations."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        # ── Conflict type distribution ──
        type_rows = await conn.fetch("""
            SELECT type, COUNT(*) AS cnt
            FROM history_event_collections
            WHERE world_id = $1
            GROUP BY type
            ORDER BY cnt DESC
        """, world_id)

        # ── Wars with details ──
        war_rows = await conn.fetch("""
            SELECT id, name, start_year, end_year,
                   COALESCE(end_year, (SELECT MAX(year) FROM history_events WHERE world_id = $1))
                       - start_year AS duration
            FROM history_event_collections
            WHERE world_id = $1 AND type = 'war'
            ORDER BY start_year
        """, world_id)

        # ── Conflicts per decade (wars + battles + sieges) ──
        conflict_timeline = await conn.fetch("""
            SELECT (start_year / 10) * 10 AS decade,
                   COUNT(*) FILTER (WHERE type = 'war') AS wars,
                   COUNT(*) FILTER (WHERE type = 'battle') AS battles,
                   COUNT(*) FILTER (WHERE type = 'site conquered') AS sieges,
                   COUNT(*) FILTER (WHERE type = 'beast attack') AS beast_attacks
            FROM history_event_collections
            WHERE world_id = $1 AND start_year IS NOT NULL
            GROUP BY (start_year / 10) * 10
            ORDER BY decade
        """, world_id)

    return {
        "event_types": [
            {"type": r["type"], "count": r["cnt"]} for r in type_rows
        ],
        "wars": [
            {"id": r["id"], "name": r["name"],
             "start": r["start_year"], "end": r["end_year"],
             "duration": r["duration"]}
            for r in war_rows
        ],
        "timeline": [
            {"decade": r["decade"], "wars": r["wars"], "battles": r["battles"],
             "sieges": r["sieges"], "beast_attacks": r["beast_attacks"]}
            for r in conflict_timeline
        ],
    }


@router.get("/demographics/culture")
async def culture(request: Request, world_id: int = Query(...)):
    """Cultural production analysis: written works, artifacts, art forms,
    site types, and geographic distribution."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        # ── Written content by type ──
        written_rows = await conn.fetch("""
            SELECT type, COUNT(*) AS cnt
            FROM written_contents
            WHERE world_id = $1
            GROUP BY type
            ORDER BY cnt DESC
        """, world_id)

        # ── Artifact types ──
        artifact_rows = await conn.fetch("""
            SELECT COALESCE(item_type, 'unknown') AS item_type, COUNT(*) AS cnt
            FROM artifacts
            WHERE world_id = $1
            GROUP BY item_type
            ORDER BY cnt DESC
            LIMIT 20
        """, world_id)

        # ── Site types distribution ──
        site_rows = await conn.fetch("""
            SELECT type, COUNT(*) AS cnt
            FROM sites
            WHERE world_id = $1
            GROUP BY type
            ORDER BY cnt DESC
        """, world_id)

        # ── Art form types ──
        artform_rows = await conn.fetch("""
            SELECT COALESCE(form_type, 'unknown') AS form_type, COUNT(*) AS cnt
            FROM art_forms
            WHERE world_id = $1
            GROUP BY form_type
            ORDER BY cnt DESC
        """, world_id)

    return {
        "written_works": [
            {"type": r["type"], "count": r["cnt"]} for r in written_rows
        ],
        "artifacts": [
            {"type": r["item_type"], "count": r["cnt"]}
            for r in artifact_rows
        ],
        "site_types": [
            {"type": r["type"], "count": r["cnt"]} for r in site_rows
        ],
        "art_forms": [
            {"type": r["form_type"], "count": r["cnt"]} for r in artform_rows
        ],
    }
