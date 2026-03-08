"""Geography routes — sites, structures, regions."""

from fastapi import APIRouter, HTTPException, Query, Request

router = APIRouter()


@router.get("/geography/sites")
async def list_sites(
    request: Request,
    type: str | None = Query(None),
    owner: int | None = Query(None),
    world_id: int = Query(8),
    limit: int = Query(200, ge=1, le=1000),
):
    pool = request.app.state.pool
    conditions = ["s.world_id = $1"]
    params: list = [world_id]
    idx = 2

    if type is not None:
        conditions.append(f"s.type = ${idx}")
        params.append(type)
        idx += 1
    if owner is not None:
        conditions.append(f"s.owner_entity_id = ${idx}")
        params.append(owner)
        idx += 1

    where = " AND ".join(conditions)
    params.append(limit)

    query = f"""
        SELECT s.id, s.world_id, s.name, s.type, s.coord_x, s.coord_y,
            s.owner_entity_id, e.name AS owner_name,
            COALESCE(st.cnt, 0) AS structure_count,
            COALESCE(lk.cnt, 0) AS linked_hf_count
        FROM sites s
        LEFT JOIN entities e ON e.world_id = s.world_id AND e.id = s.owner_entity_id
        LEFT JOIN LATERAL (
            SELECT COUNT(*) AS cnt FROM structures
            WHERE world_id = s.world_id AND site_id = s.id
        ) st ON true
        LEFT JOIN LATERAL (
            SELECT COUNT(*) AS cnt FROM hf_site_links
            WHERE world_id = s.world_id AND site_id = s.id
        ) lk ON true
        WHERE {where}
        ORDER BY s.type, s.name
        LIMIT ${idx}
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *params)

    return [dict(r) for r in rows]


@router.get("/geography/sites/{world_id}/{site_id}")
async def get_site(request: Request, world_id: int, site_id: int):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        site = await conn.fetchrow(
            """
            SELECT s.id, s.world_id, s.name, s.type, s.coord_x, s.coord_y,
                   s.owner_entity_id, e.name AS owner_name, e.type AS owner_type
            FROM sites s
            LEFT JOIN entities e ON e.world_id = s.world_id AND e.id = s.owner_entity_id
            WHERE s.world_id = $1 AND s.id = $2
            """, world_id, site_id,
        )
        if not site:
            raise HTTPException(404, "Site not found")

        structures = await conn.fetch(
            "SELECT id, name, type, entity_id FROM structures "
            "WHERE world_id = $1 AND site_id = $2 ORDER BY id",
            world_id, site_id,
        )
        hf_rows = await conn.fetch(
            """
            SELECT l.hf_id, h.name, h.race, l.link_type
            FROM hf_site_links l
            JOIN historical_figures h ON h.world_id = l.world_id AND h.id = l.hf_id
            WHERE l.world_id = $1 AND l.site_id = $2
            ORDER BY h.name LIMIT 50
            """, world_id, site_id,
        )
        events = await conn.fetch(
            "SELECT id, year, event_type FROM history_events "
            "WHERE world_id = $1 AND site_id = $2 "
            "ORDER BY year DESC LIMIT 20",
            world_id, site_id,
        )

        from chronicler.api.routes.civilizations import fetch_site_residents_count
        residents_count = await fetch_site_residents_count(conn, world_id, site_id)

    owner = None
    if site["owner_entity_id"] is not None:
        owner = {"id": site["owner_entity_id"],
                 "name": site["owner_name"], "type": site["owner_type"]}

    return {
        "id": site["id"], "world_id": site["world_id"],
        "name": site["name"], "type": site["type"],
        "coord_x": site["coord_x"], "coord_y": site["coord_y"],
        "owner": owner,
        "structures": [dict(s) for s in structures],
        "linked_hfs": [
            {"hf_id": r["hf_id"], "name": r["name"],
             "race": r["race"], "link_type": r["link_type"]}
            for r in hf_rows
        ],
        "recent_events": [dict(e) for e in events],
        "residents_count": residents_count,
    }


@router.get("/geography/regions")
async def list_regions(
    request: Request,
    world_id: int = Query(8),
):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, world_id, name, type FROM regions "
            "WHERE world_id = $1 ORDER BY name",
            world_id,
        )
    return [dict(r) for r in rows]
