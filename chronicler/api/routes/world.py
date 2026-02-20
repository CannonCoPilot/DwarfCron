"""World data endpoints for the sidebar."""

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/worlds")
async def list_worlds(request: Request):
    """List all worlds with summary statistics."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        worlds = await conn.fetch("SELECT id, name FROM worlds ORDER BY id")
        result = []
        for w in worlds:
            stats = await conn.fetchrow(
                """
                SELECT
                    (SELECT count(*) FROM historical_figures WHERE world_id = $1) as hf_count,
                    (SELECT count(*) FROM entities WHERE world_id = $1) as entity_count,
                    (SELECT count(*) FROM sites WHERE world_id = $1) as site_count,
                    (SELECT count(*) FROM history_events WHERE world_id = $1) as event_count,
                    (SELECT count(*) FROM regions WHERE world_id = $1) as region_count
                """,
                w["id"],
            )
            result.append({
                "id": w["id"],
                "name": w["name"],
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
