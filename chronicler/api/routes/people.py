"""People router — search and detail views for historical figures and units."""

import json

from fastapi import APIRouter, HTTPException, Query, Request

router = APIRouter()

_TYPE_FLAG_COLS = [
    ("is_deity", "deity"),
    ("is_force", "force"),
    ("is_vampire", "vampire"),
    ("is_necromancer", "necromancer"),
    ("is_werebeast", "werebeast"),
    ("is_ghost", "ghost"),
]


def _type_flags(row: dict) -> list[str]:
    return [label for col, label in _TYPE_FLAG_COLS if row.get(col)]


# ---------------------------------------------------------------------------
# 1. Unified search
# ---------------------------------------------------------------------------

@router.get("/people/search")
async def search_people(
    request: Request,
    q: str = Query(..., min_length=1),
    type: str = Query("all"),
    limit: int = Query(50, ge=1, le=200),
):
    pool = request.app.state.pool
    pattern = f"%{q}%"
    results: list[dict] = []

    async with pool.acquire() as conn:
        if type in ("all", "unit"):
            rows = await conn.fetch(
                """
                SELECT id, world_id, name, english_name, race, caste,
                       profession, is_alive
                FROM units
                WHERE name ILIKE $1 OR english_name ILIKE $1
                ORDER BY name
                LIMIT $2
                """,
                pattern, limit,
            )
            for r in rows:
                results.append({
                    "source": "unit", "id": r["id"], "world_id": r["world_id"],
                    "name": r["name"], "english_name": r["english_name"],
                    "race": r["race"], "is_alive": r["is_alive"],
                    "profession": r["profession"], "type_flags": [],
                })

        if type in ("all", "hf"):
            remaining = limit - len(results)
            if remaining > 0:
                rows = await conn.fetch(
                    """
                    SELECT id, world_id, name, race, caste, death_year,
                           is_deity, is_force, is_vampire,
                           is_necromancer, is_werebeast, is_ghost
                    FROM historical_figures
                    WHERE name ILIKE $1
                    ORDER BY name
                    LIMIT $2
                    """,
                    pattern, remaining,
                )
                for r in rows:
                    row = dict(r)
                    results.append({
                        "source": "hf", "id": row["id"], "world_id": row["world_id"],
                        "name": row["name"], "english_name": None,
                        "race": row["race"], "is_alive": row["death_year"] is None,
                        "profession": None, "type_flags": _type_flags(row),
                    })
    return results


# ---------------------------------------------------------------------------
# 2. HF detail
# ---------------------------------------------------------------------------

@router.get("/people/hf/{world_id}/{hf_id}")
async def get_historical_figure(request: Request, world_id: int, hf_id: int):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        hf = await conn.fetchrow(
            """
            SELECT h.*, e.name AS entity_name
            FROM historical_figures h
            LEFT JOIN entities e ON e.world_id = h.world_id AND e.id = h.entity_id
            WHERE h.world_id = $1 AND h.id = $2
            """, world_id, hf_id,
        )
        if not hf:
            raise HTTPException(404, "Historical figure not found")
        hf = dict(hf)

        unit_row = await conn.fetchrow(
            "SELECT id, name, english_name, profession FROM units "
            "WHERE world_id = $1 AND hist_fig_id = $2 LIMIT 1",
            world_id, hf_id,
        )

        rel_rows = await conn.fetch(
            """
            SELECT l.target_hf_id, l.link_type,
                   t.name AS target_name, t.race AS target_race
            FROM hf_links l
            LEFT JOIN historical_figures t
                   ON t.world_id = l.world_id AND t.id = l.target_hf_id
            WHERE l.world_id = $1 AND l.hf_id = $2
            """, world_id, hf_id,
        )

        ent_rows = await conn.fetch(
            """
            SELECT l.entity_id, l.link_type, l.position_name,
                   e.name AS entity_name, e.type AS entity_type
            FROM hf_entity_links l
            LEFT JOIN entities e ON e.world_id = l.world_id AND e.id = l.entity_id
            WHERE l.world_id = $1 AND l.hf_id = $2
            """, world_id, hf_id,
        )

        site_rows = await conn.fetch(
            """
            SELECT l.site_id, l.link_type,
                   s.name AS site_name, s.type AS site_type
            FROM hf_site_links l
            LEFT JOIN sites s ON s.world_id = l.world_id AND s.id = l.site_id
            WHERE l.world_id = $1 AND l.hf_id = $2
            """, world_id, hf_id,
        )

        pos_rows = await conn.fetch(
            """
            SELECT p.entity_id, p.position_id, p.start_year, p.end_year,
                   e.name AS entity_name,
                   ep.name AS position_name
            FROM hf_position_links p
            LEFT JOIN entities e ON e.world_id = p.world_id AND e.id = p.entity_id
            LEFT JOIN entity_positions ep
                   ON ep.world_id = p.world_id
                  AND ep.entity_id = p.entity_id
                  AND ep.position_id = p.position_id
            WHERE p.world_id = $1 AND p.hf_id = $2
            ORDER BY p.start_year
            """, world_id, hf_id,
        )

        id_rows = await conn.fetch(
            "SELECT id, name FROM identities "
            "WHERE world_id = $1 AND histfig_id = $2",
            world_id, hf_id,
        )

    return {
        "id": hf["id"], "world_id": hf["world_id"], "name": hf["name"],
        "race": hf["race"], "caste": hf["caste"],
        "birth_year": hf["birth_year"], "death_year": hf["death_year"],
        "death_cause": hf["death_cause"],
        "kill_count": hf["kill_count"], "event_count": hf["event_count"],
        "type_flags": _type_flags(hf),
        "entity_id": hf["entity_id"], "entity_name": hf["entity_name"],
        "linked_unit": dict(unit_row) if unit_row else None,
        "relationships": [
            {"target_id": r["target_hf_id"], "target_name": r["target_name"],
             "link_type": r["link_type"], "target_race": r["target_race"]}
            for r in rel_rows
        ],
        "entity_links": [
            {"entity_id": r["entity_id"], "entity_name": r["entity_name"],
             "entity_type": r["entity_type"], "link_type": r["link_type"],
             "position_name": r["position_name"]}
            for r in ent_rows
        ],
        "site_links": [
            {"site_id": r["site_id"], "site_name": r["site_name"],
             "site_type": r["site_type"], "link_type": r["link_type"]}
            for r in site_rows
        ],
        "positions": [
            {"entity_id": r["entity_id"], "entity_name": r["entity_name"],
             "position_name": r["position_name"],
             "start_year": r["start_year"], "end_year": r["end_year"]}
            for r in pos_rows
        ],
        "identities": [{"id": r["id"], "name": r["name"]} for r in id_rows],
    }


# ---------------------------------------------------------------------------
# 3. Unit detail
# ---------------------------------------------------------------------------

@router.get("/people/unit/{unit_id}")
async def get_unit(request: Request, unit_id: int):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT u.*, e.name AS civ_name
            FROM units u
            LEFT JOIN entities e ON e.world_id = u.world_id AND e.id = u.civ_id
            WHERE u.id = $1
            """, unit_id,
        )
        if not row:
            raise HTTPException(404, "Unit not found")
        row = dict(row)

        details = row.get("details") or {}
        if isinstance(details, str):
            details = json.loads(details)

        linked_hf = None
        if row.get("hist_fig_id") is not None:
            hf_row = await conn.fetchrow(
                "SELECT id, name, race, birth_year FROM historical_figures "
                "WHERE world_id = $1 AND id = $2",
                row["world_id"], row["hist_fig_id"],
            )
            if hf_row:
                linked_hf = dict(hf_row)

    return {
        "id": row["id"], "world_id": row["world_id"],
        "name": row["name"], "english_name": row["english_name"],
        "race": row["race"], "caste": row["caste"],
        "profession": row["profession"],
        "pos_x": row["pos_x"], "pos_y": row["pos_y"], "pos_z": row["pos_z"],
        "is_alive": row["is_alive"],
        "hist_fig_id": row["hist_fig_id"], "civ_id": row["civ_id"],
        "civ_name": row["civ_name"],
        "skills": details.get("skills", []),
        "labors": details.get("labors", []),
        "linked_hf": linked_hf,
        "last_synced_at": str(row["last_synced_at"]) if row.get("last_synced_at") else None,
    }


# ---------------------------------------------------------------------------
# 4. HF events
# ---------------------------------------------------------------------------

@router.get("/people/hf/{world_id}/{hf_id}/events")
async def get_hf_events(
    request: Request, world_id: int, hf_id: int,
    limit: int = Query(50, ge=1, le=200),
):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        exists = await conn.fetchval(
            "SELECT 1 FROM historical_figures WHERE world_id = $1 AND id = $2",
            world_id, hf_id,
        )
        if not exists:
            raise HTTPException(404, "Historical figure not found")

        rows = await conn.fetch(
            """
            SELECT ev.id, ev.year, ev.event_type,
                   ev.hf_id_1, ev.hf_id_2, ev.site_id,
                   s.name AS site_name,
                   h1.name AS hf1_name, h2.name AS hf2_name
            FROM history_events ev
            LEFT JOIN sites s ON s.world_id = ev.world_id AND s.id = ev.site_id
            LEFT JOIN historical_figures h1
                   ON h1.world_id = ev.world_id AND h1.id = ev.hf_id_1
            LEFT JOIN historical_figures h2
                   ON h2.world_id = ev.world_id AND h2.id = ev.hf_id_2
            WHERE ev.world_id = $1
              AND (ev.hf_id_1 = $2 OR ev.hf_id_2 = $2)
            ORDER BY ev.year DESC, ev.id DESC
            LIMIT $3
            """, world_id, hf_id, limit,
        )

    results = []
    for r in rows:
        other_id = r["hf_id_2"] if r["hf_id_1"] == hf_id else r["hf_id_1"]
        other_name = r["hf2_name"] if r["hf_id_1"] == hf_id else r["hf1_name"]
        results.append({
            "id": r["id"], "year": r["year"], "event_type": r["event_type"],
            "other_hf_id": other_id, "other_hf_name": other_name,
            "site_id": r["site_id"], "site_name": r["site_name"],
        })
    return results
