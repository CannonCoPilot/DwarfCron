"""World data endpoints — sidebar, timeline, and state-at-year."""

from fastapi import APIRouter, Query, Request

router = APIRouter()


@router.get("/worlds")
async def list_worlds(request: Request):
    """List all worlds with summary statistics."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        worlds = await conn.fetch(
            "SELECT id, name, alt_name FROM worlds ORDER BY id")
        result = []
        for w in worlds:
            stats = await conn.fetchrow(
                """
                SELECT
                    (SELECT count(*) FROM historical_figures WHERE world_id = $1) as hf_count,
                    (SELECT count(*) FROM entities WHERE world_id = $1) as entity_count,
                    (SELECT count(*) FROM sites WHERE world_id = $1) as site_count,
                    (SELECT count(*) FROM history_events WHERE world_id = $1) as event_count,
                    (SELECT count(*) FROM regions WHERE world_id = $1) as region_count,
                    (SELECT MAX(year) FROM history_events WHERE world_id = $1) as max_year,
                    (SELECT count(*) FROM embeddings WHERE world_id = $1) as embedding_count
                """,
                w["id"],
            )
            result.append({
                "id": w["id"],
                "name": w["name"],
                "alt_name": w["alt_name"],
                "stats": dict(stats),
            })
    return result


@router.get("/world/{world_id}/stats")
async def world_stats(world_id: int, request: Request):
    """Detailed counts per table for a specific world."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        stats = await conn.fetchrow(
            """
            SELECT
                (SELECT count(*) FROM historical_figures WHERE world_id = $1) as historical_figures,
                (SELECT count(*) FROM entities WHERE world_id = $1) as entities,
                (SELECT count(*) FROM sites WHERE world_id = $1) as sites,
                (SELECT count(*) FROM regions WHERE world_id = $1) as regions,
                (SELECT count(*) FROM history_events WHERE world_id = $1) as events,
                (SELECT count(*) FROM history_event_collections WHERE world_id = $1) as collections,
                (SELECT count(*) FROM artifacts WHERE world_id = $1) as artifacts
            """,
            world_id,
        )
    return dict(stats)


@router.get("/world/{world_id}/civilizations")
async def world_civilizations(world_id: int, request: Request):
    """List civilizations for a world."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        civs = await conn.fetch(
            """
            SELECT e.id, e.name, e.race,
                   count(s.id) as site_count
            FROM entities e
            LEFT JOIN sites s ON s.owner_entity_id = e.id AND s.world_id = e.world_id
            WHERE e.world_id = $1 AND e.type = 'civilization'
            GROUP BY e.id, e.name, e.race
            ORDER BY site_count DESC
            """,
            world_id,
        )
    return [dict(c) for c in civs]


@router.get("/world/{world_id}/figures")
async def search_figures(world_id: int, request: Request, q: str = ""):
    """Search historical figures by name (for sidebar typeahead)."""
    pool = request.app.state.pool
    if not q or len(q) < 2:
        return []
    async with pool.acquire() as conn:
        figures = await conn.fetch(
            """
            SELECT id, name, race, caste, birth_year, death_year, kill_count
            FROM historical_figures
            WHERE world_id = $1 AND name ILIKE $2
            ORDER BY kill_count DESC NULLS LAST
            LIMIT 20
            """,
            world_id, f"%{q}%",
        )
    return [dict(f) for f in figures]


@router.get("/world/{world_id}/timeline")
async def world_timeline(world_id: int, request: Request):
    """Year-by-year world timeline from materialized snapshots.

    Returns both historical_backfill (from Legends) and live_capture
    (from worldgen monitoring) data, ordered by year.
    """
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT year, phase, progress_pct, hf_count, site_count,
                   entity_count, event_count, data
            FROM worldgen_snapshots
            WHERE world_id = $1
            ORDER BY year
            """,
            world_id,
        )
        if not rows:
            return {"world_id": world_id, "source": "none", "years": []}

        # Determine source type
        phases = {r["phase"] for r in rows}
        if "historical_backfill" in phases and len(phases) == 1:
            source = "historical_backfill"
        elif "historical_backfill" not in phases:
            source = "live_capture"
        else:
            source = "mixed"

        years = []
        for r in rows:
            entry = {
                "year": r["year"],
                "hf_count": r["hf_count"],
                "site_count": r["site_count"],
                "entity_count": r["entity_count"],
                "event_count": r["event_count"],
                "phase": r["phase"],
            }
            # Include extra data from JSONB if present
            data = r["data"]
            if isinstance(data, dict):
                for k in ("births", "deaths", "events_this_year",
                          "total_born", "total_died"):
                    if k in data:
                        entry[k] = data[k]
            years.append(entry)

        return {"world_id": world_id, "source": source, "years": years}


@router.get("/world/{world_id}/state")
async def world_state_at_year(
    world_id: int, request: Request,
    year: int = Query(..., description="Year to query state for"),
):
    """Compute the state of the world at a specific year.

    On-the-fly computation: living HFs, active sites, events that year,
    active wars, and top civilizations at that point in time.
    """
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        # Living HFs at this year
        living_hfs = await conn.fetchval(
            """
            SELECT COUNT(*) FROM historical_figures
            WHERE world_id = $1 AND birth_year <= $2
              AND (death_year IS NULL OR death_year > $2)
            """,
            world_id, year,
        )

        # Active sites (founded but not destroyed by this year)
        active_sites = await conn.fetchval(
            """
            SELECT COUNT(*) FROM sites
            WHERE world_id = $1
              AND founded_year IS NOT NULL AND founded_year <= $2
              AND (
                  details->>'destroyed_year' IS NULL
                  OR (details->>'destroyed_year')::int > $2
              )
            """,
            world_id, year,
        )

        # Total sites founded up to this year
        total_founded = await conn.fetchval(
            """
            SELECT COUNT(*) FROM sites
            WHERE world_id = $1 AND founded_year IS NOT NULL AND founded_year <= $2
            """,
            world_id, year,
        )

        # Events this year — grouped by type (top 10)
        event_types = await conn.fetch(
            """
            SELECT event_type, COUNT(*) as cnt
            FROM history_events
            WHERE world_id = $1 AND year = $2
            GROUP BY event_type
            ORDER BY cnt DESC
            LIMIT 10
            """,
            world_id, year,
        )

        # Total events this year
        events_this_year = await conn.fetchval(
            "SELECT COUNT(*) FROM history_events WHERE world_id = $1 AND year = $2",
            world_id, year,
        )

        # Active wars (collections of type 'war' spanning this year)
        wars = await conn.fetch(
            """
            SELECT id, name, start_year, end_year,
                   attacker_entity_id, defender_entity_id
            FROM history_event_collections
            WHERE world_id = $1
              AND type = 'war'
              AND start_year <= $2
              AND (end_year IS NULL OR end_year >= $2)
            ORDER BY start_year
            """,
            world_id, year,
        )

        # Top civilizations by site count at this year
        top_civs = await conn.fetch(
            """
            SELECT e.id, e.name, e.race,
                   COUNT(s.id) as site_count
            FROM entities e
            LEFT JOIN sites s ON s.owner_entity_id = e.id
                AND s.world_id = e.world_id
                AND s.founded_year IS NOT NULL AND s.founded_year <= $2
                AND (s.details->>'destroyed_year' IS NULL
                     OR (s.details->>'destroyed_year')::int > $2)
            WHERE e.world_id = $1 AND e.type = 'civilization'
            GROUP BY e.id, e.name, e.race
            ORDER BY site_count DESC
            LIMIT 10
            """,
            world_id, year,
        )

        # Deaths this year
        deaths_this_year = await conn.fetchval(
            "SELECT COUNT(*) FROM historical_figures WHERE world_id = $1 AND death_year = $2",
            world_id, year,
        )

        # Births this year
        births_this_year = await conn.fetchval(
            "SELECT COUNT(*) FROM historical_figures WHERE world_id = $1 AND birth_year = $2",
            world_id, year,
        )

        return {
            "world_id": world_id,
            "year": year,
            "living_hfs": living_hfs,
            "active_sites": active_sites,
            "total_sites_founded": total_founded,
            "events_this_year": events_this_year,
            "births": births_this_year,
            "deaths": deaths_this_year,
            "top_event_types": [{"type": e["event_type"], "count": e["cnt"]}
                                for e in event_types],
            "active_wars": [dict(w) for w in wars],
            "top_civilizations": [dict(c) for c in top_civs],
        }
