"""Events & timeline routes for the Chronicler explorer."""

from fastapi import APIRouter, HTTPException, Query, Request

router = APIRouter()


@router.get("/events")
async def list_events(
    request: Request,
    year_from: int | None = Query(None),
    year_to: int | None = Query(None),
    type: str | None = Query(None),
    hf: int | None = Query(None, description="Filter by HF involvement"),
    site: int | None = Query(None),
    world_id: int = Query(8),
    limit: int = Query(100, ge=1, le=500),
):
    pool = request.app.state.pool
    conditions = ["ev.world_id = $1"]
    params: list = [world_id]
    idx = 2

    if year_from is not None:
        conditions.append(f"ev.year >= ${idx}")
        params.append(year_from)
        idx += 1
    if year_to is not None:
        conditions.append(f"ev.year <= ${idx}")
        params.append(year_to)
        idx += 1
    if type is not None:
        conditions.append(f"ev.event_type = ${idx}")
        params.append(type)
        idx += 1
    if hf is not None:
        conditions.append(f"(ev.hf_id_1 = ${idx} OR ev.hf_id_2 = ${idx})")
        params.append(hf)
        idx += 1
    if site is not None:
        conditions.append(f"ev.site_id = ${idx}")
        params.append(site)
        idx += 1

    where = " AND ".join(conditions)
    params.append(limit)

    query = f"""
        SELECT ev.id, ev.year, ev.event_type,
               ev.hf_id_1, ev.hf_id_2, ev.site_id,
               h1.name AS hf1_name, h2.name AS hf2_name,
               s.name AS site_name
        FROM history_events ev
        LEFT JOIN historical_figures h1
               ON h1.world_id = ev.world_id AND h1.id = ev.hf_id_1
        LEFT JOIN historical_figures h2
               ON h2.world_id = ev.world_id AND h2.id = ev.hf_id_2
        LEFT JOIN sites s ON s.world_id = ev.world_id AND s.id = ev.site_id
        WHERE {where}
        ORDER BY ev.year DESC, ev.id DESC
        LIMIT ${idx}
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *params)

    return [
        {
            "id": r["id"], "year": r["year"], "event_type": r["event_type"],
            "hf_id_1": r["hf_id_1"], "hf1_name": r["hf1_name"],
            "hf_id_2": r["hf_id_2"], "hf2_name": r["hf2_name"],
            "site_id": r["site_id"], "site_name": r["site_name"],
        }
        for r in rows
    ]


@router.get("/events/types")
async def list_event_types(
    request: Request,
    world_id: int = Query(8),
):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT event_type, COUNT(*) AS count
            FROM history_events
            WHERE world_id = $1
            GROUP BY event_type
            ORDER BY count DESC
            """, world_id,
        )
    return [{"type": r["event_type"], "count": r["count"]} for r in rows]


@router.get("/events/collections")
async def list_collections(
    request: Request,
    type: str | None = Query(None),
    world_id: int = Query(8),
    limit: int = Query(100, ge=1, le=500),
):
    pool = request.app.state.pool
    conditions = ["c.world_id = $1"]
    params: list = [world_id]
    idx = 2

    if type is not None:
        conditions.append(f"c.type = ${idx}")
        params.append(type)
        idx += 1

    where = " AND ".join(conditions)
    params.append(limit)

    query = f"""
        SELECT c.id, c.type, c.name, c.start_year, c.start_seconds, c.end_year, c.end_seconds,
               c.attacker_entity_id, c.defender_entity_id,
               att.name AS attacker_name, def.name AS defender_name,
               s.name AS site_name
        FROM history_event_collections c
        LEFT JOIN entities att ON att.world_id = c.world_id AND att.id = c.attacker_entity_id
        LEFT JOIN entities def ON def.world_id = c.world_id AND def.id = c.defender_entity_id
        LEFT JOIN sites s ON s.world_id = c.world_id AND s.id = c.site_id
        WHERE {where}
        ORDER BY c.start_year DESC
        LIMIT ${idx}
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *params)

    return [dict(r) for r in rows]


@router.get("/events/collections/{world_id}/{collection_id}")
async def get_collection(request: Request, world_id: int, collection_id: int):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        coll = await conn.fetchrow(
            """
            SELECT c.*, att.name AS attacker_name, def.name AS defender_name,
                   s.name AS site_name
            FROM history_event_collections c
            LEFT JOIN entities att ON att.world_id = c.world_id AND att.id = c.attacker_entity_id
            LEFT JOIN entities def ON def.world_id = c.world_id AND def.id = c.defender_entity_id
            LEFT JOIN sites s ON s.world_id = c.world_id AND s.id = c.site_id
            WHERE c.world_id = $1 AND c.id = $2
            """, world_id, collection_id,
        )
        if not coll:
            raise HTTPException(404, "Collection not found")

        events = await conn.fetch(
            """
            SELECT ev.id, ev.year, ev.event_type
            FROM collection_events ce
            JOIN history_events ev ON ev.world_id = ce.world_id AND ev.id = ce.event_id
            WHERE ce.world_id = $1 AND ce.collection_id = $2
            ORDER BY ev.year, ev.id
            """, world_id, collection_id,
        )

        subcollections = await conn.fetch(
            """
            SELECT c.id, c.type, c.name, c.start_year, c.end_year
            FROM collection_subcollections cs
            JOIN history_event_collections c ON c.world_id = cs.world_id AND c.id = cs.child_id
            WHERE cs.world_id = $1 AND cs.parent_id = $2
            ORDER BY c.start_year
            """, world_id, collection_id,
        )

    result = dict(coll)
    result["events"] = [dict(e) for e in events]
    result["subcollections"] = [dict(s) for s in subcollections]
    return result
