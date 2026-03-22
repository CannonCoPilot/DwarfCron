"""Deity analysis statistics routes.

Provides per-deity data with spheres, race grouping, worshipper counts,
religion memberships, and civilization linkages for interactive charting.
"""

import re

from fastapi import APIRouter, Query, Request

router = APIRouter()

_RACE_GROUP_PATTERNS = [
    (re.compile(r"^FORGOTTEN_BEAST_"), "Forgotten Beast"),
    (re.compile(r"^TITAN_"), "Titan"),
    (re.compile(r"^DEMON_"), "Demon"),
    (re.compile(r"^NIGHT_CREATURE_"), "Night Creature"),
    (re.compile(r"^BIRD_"), "Giant Bird"),
    (re.compile(r"^FISH_"), "Giant Fish"),
    (re.compile(r"^HFEXP"), "Experiment"),
]


def _race_group(raw: str | None) -> str:
    if not raw:
        return "Unknown"
    for pat, group in _RACE_GROUP_PATTERNS:
        if pat.match(raw):
            return group
    return raw.replace("_", " ").title()


@router.get("/statistics/deity-analysis")
async def deity_analysis(request: Request, world_id: int = Query(...)):
    """Return comprehensive deity data for interactive visualization.

    Includes per-deity records with spheres, race, age, worshipper counts,
    religion count, and civilization affiliations — all needed for
    client-side filtering and chart rendering.
    """
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        # Current world year for age calculation — derive from latest event
        world_year = await conn.fetchval(
            "SELECT MAX(year) FROM history_events WHERE world_id = $1",
            world_id,
        ) or 250

        # ── All deities ──
        deity_rows = await conn.fetch("""
            SELECT hf.id, hf.name, hf.race, hf.spheres,
                   hf.birth_year, hf.death_year, hf.associated_type, hf.caste
            FROM historical_figures hf
            WHERE hf.world_id = $1 AND hf.is_deity = TRUE
            ORDER BY hf.name
        """, world_id)

        deity_ids = [r["id"] for r in deity_rows]

        # ── Worshipper counts (individual hf_links with link_type='deity') ──
        worshipper_rows = await conn.fetch("""
            SELECT target_hf_id AS deity_id, COUNT(*) AS cnt
            FROM hf_links
            WHERE world_id = $1 AND link_type = 'deity' AND target_hf_id = ANY($2)
            GROUP BY target_hf_id
        """, world_id, deity_ids)
        worshipper_map = {r["deity_id"]: r["cnt"] for r in worshipper_rows}

        # ── Religion entities per deity (worship_id) ──
        religion_rows = await conn.fetch("""
            SELECT e.worship_id AS deity_id, COUNT(*) AS cnt
            FROM entities e
            WHERE e.world_id = $1 AND e.worship_id = ANY($2)
            GROUP BY e.worship_id
        """, world_id, deity_ids)
        religion_map = {r["deity_id"]: r["cnt"] for r in religion_rows}

        # ── Civilization links: religion -> civ via entity_entity_links RELIGIOUS ──
        civ_rows = await conn.fetch("""
            SELECT DISTINCT e.worship_id AS deity_id,
                   eel.target_entity_id AS civ_id
            FROM entities e
            JOIN entity_entity_links eel
                ON eel.world_id = $1
                AND eel.source_entity_id = e.id
                AND eel.link_type = 'RELIGIOUS'
            WHERE e.world_id = $1 AND e.worship_id = ANY($2)
        """, world_id, deity_ids)
        # deity_id -> set of civ_ids
        civ_map: dict[int, list[int]] = {}
        all_civ_ids = set()
        for r in civ_rows:
            civ_map.setdefault(r["deity_id"], []).append(r["civ_id"])
            all_civ_ids.add(r["civ_id"])

        # ── Civilization names ──
        civ_name_rows = await conn.fetch("""
            SELECT id, name FROM entities
            WHERE world_id = $1 AND id = ANY($2)
            ORDER BY name
        """, world_id, list(all_civ_ids)) if all_civ_ids else []
        civilizations = [
            {"id": r["id"], "name": r["name"]} for r in civ_name_rows
        ]

        # ── Assemble deity records ──
        deities = []
        for r in deity_rows:
            race_raw = r["race"]
            rg = _race_group(race_raw)
            birth = r["birth_year"]
            death = r["death_year"]
            alive = death is None
            age = None
            if birth is not None:
                age = (world_year if alive else death) - birth
                if age < 0:
                    age = None
            spheres = list(r["spheres"]) if r["spheres"] else []
            deities.append({
                "id": r["id"],
                "name": r["name"],
                "race_group": rg,
                "spheres": spheres,
                "alive": alive,
                "age": age,
                "caste": r["caste"],
                "worshippers": worshipper_map.get(r["id"], 0),
                "religions": religion_map.get(r["id"], 0),
                "civ_ids": civ_map.get(r["id"], []),
            })

    return {
        "deities": deities,
        "civilizations": civilizations,
        "world_year": world_year,
    }
