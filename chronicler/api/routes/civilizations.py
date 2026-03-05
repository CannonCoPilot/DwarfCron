"""Civilization (entity) exploration routes."""

from fastapi import APIRouter, HTTPException, Query, Request

router = APIRouter()

_MEMBER_LINK_TYPES = ("member", "former member")

_NOBLE_KEYWORDS = frozenset([
    "king", "queen", "duke", "duchess", "baron", "baroness", "count", "countess",
    "lord", "lady", "monarch", "emperor", "empress", "consort", "prince", "princess",
])
_MILITARY_KEYWORDS = frozenset([
    "general", "captain", "militia", "commander", "sheriff", "champion", "marshal",
    "soldier", "guard", "war", "hammerer", "executioner",
])
_ADMIN_KEYWORDS = frozenset([
    "manager", "bookkeeper", "broker", "expedition", "mayor", "chief", "medical",
    "administrator", "diplomat", "outpost", "liaison",
])
_LORD_LADY = frozenset(["lord", "lady"])


def _categorize_position(name: str | None) -> str:
    if not name:
        return "other"
    words = set(name.lower().split())
    if words & _NOBLE_KEYWORDS:
        return "noble"
    if words & _MILITARY_KEYWORDS:
        return "military"
    if words & _ADMIN_KEYWORDS:
        return "admin"
    return "other"


def _gender_title(pos: dict, holder_caste: str | None) -> str | None:
    """Pick the gender-appropriate title variant for a position holder."""
    is_female = holder_caste and holder_caste.lower() == "female"
    if is_female and pos.get("name_female"):
        return pos["name_female"]
    if not is_female and pos.get("name_male"):
        return pos["name_male"]
    return pos.get("name_male") or pos.get("name_female")


def _is_animal_person(creature_id: str) -> bool:
    """Check if a creature_id follows the DF animal person pattern."""
    if not creature_id:
        return False
    upper = creature_id.upper()
    return upper.endswith("_MAN") or upper == "RODENT MAN"


@router.get("/civilizations/race-summary")
async def civ_race_summary(
    request: Request,
    world_id: int = Query(8),
):
    """Return dynamically categorized race groups with entity counts.

    Races are derived from the entities table and creature_dictionary.
    Animal people are collapsed into a single group. All other races
    get their own pill — modded civ races auto-appear.
    """
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT e.race, COUNT(*) AS cnt, cd.name_singular
            FROM entities e
            LEFT JOIN creature_dictionary cd
                ON cd.world_id = e.world_id AND cd.creature_id = e.race
            WHERE e.world_id = $1
            GROUP BY e.race, cd.name_singular
            ORDER BY cnt DESC
            """,
            world_id,
        )

    category_counts: dict[str, int] = {}
    category_labels: dict[str, str] = {}
    for r in rows:
        race = r["race"] or "unknown"
        count = r["cnt"]
        name_s = r["name_singular"]

        if _is_animal_person(race):
            key = "_animal_men"
            label = "Animal Men"
        else:
            key = race
            if name_s:
                # Capitalize respecting apostrophes
                label = " ".join(
                    w[0].upper() + w[1:] if w else w
                    for w in name_s.split(" ")
                )
            else:
                label = race.replace("_", " ").title()

        category_counts[key] = category_counts.get(key, 0) + count
        category_labels[key] = label

    races = [
        {"key": k, "label": category_labels[k], "count": v}
        for k, v in category_counts.items()
    ]
    races.sort(key=lambda x: x["count"], reverse=True)
    return {"races": races, "total": sum(r["count"] for r in races)}


@router.get("/civilizations")
async def list_civilizations(
    request: Request,
    type: str | None = Query(None),
    world_id: int = Query(8),
):
    pool = request.app.state.pool
    conditions = ["e.world_id = $1"]
    params: list = [world_id]

    if type is not None:
        conditions.append("e.type = $2")
        params.append(type)

    where = " AND ".join(conditions)
    query = f"""
        SELECT e.id, e.world_id, e.name, e.type, e.race,
            COALESCE(mem.cnt, 0) AS member_count,
            COALESCE(sit.cnt, 0) AS site_count,
            COALESCE(pos.cnt, 0) AS position_count
        FROM entities e
        LEFT JOIN (
            SELECT world_id, entity_id, COUNT(*) AS cnt
            FROM hf_entity_links WHERE world_id = $1
              AND link_type IN ('member', 'former member')
            GROUP BY world_id, entity_id
        ) mem ON mem.world_id = e.world_id AND mem.entity_id = e.id
        LEFT JOIN (
            SELECT world_id, owner_entity_id, COUNT(*) AS cnt
            FROM sites WHERE world_id = $1
            GROUP BY world_id, owner_entity_id
        ) sit ON sit.world_id = e.world_id AND sit.owner_entity_id = e.id
        LEFT JOIN (
            SELECT world_id, entity_id, COUNT(*) AS cnt
            FROM entity_positions WHERE world_id = $1
            GROUP BY world_id, entity_id
        ) pos ON pos.world_id = e.world_id AND pos.entity_id = e.id
        WHERE {where}
        ORDER BY e.type, e.name
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *params)

    grouped: dict[str, list[dict]] = {}
    for r in rows:
        entry = dict(r)
        grouped.setdefault(entry.get("type") or "unknown", []).append(entry)
    return {"groups": grouped, "total": len(rows)}


@router.get("/civilizations/{world_id}/{entity_id}")
async def get_civilization(request: Request, world_id: int, entity_id: int):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        entity = await conn.fetchrow(
            "SELECT id, world_id, name, type, race FROM entities "
            "WHERE world_id = $1 AND id = $2",
            world_id, entity_id,
        )
        if not entity:
            raise HTTPException(404, "Entity not found")

        positions = await conn.fetch(
            """
            SELECT ep.position_id, ep.name, ep.name_male, ep.name_female,
                   h.hf_id AS holder_hf_id, h.holder_name, h.holder_caste
            FROM entity_positions ep
            LEFT JOIN LATERAL (
                SELECT hpl.hf_id, hf.name AS holder_name, hf.caste AS holder_caste
                FROM hf_position_links hpl
                JOIN historical_figures hf
                    ON hf.world_id = hpl.world_id AND hf.id = hpl.hf_id
                WHERE hpl.world_id = ep.world_id AND hpl.entity_id = ep.entity_id
                  AND hpl.position_id = ep.position_id AND hpl.end_year IS NULL
                ORDER BY hpl.start_year DESC
                LIMIT 1
            ) h ON true
            WHERE ep.world_id = $1 AND ep.entity_id = $2
            ORDER BY ep.name
            """, world_id, entity_id,
        )

        # ── Child site governments via JSONB containment ──
        site_govt_rows = await conn.fetch(
            """
            SELECT id, name FROM entities
            WHERE world_id = $1 AND type = 'sitegovernment'
              AND details->'entity_links' @> ('[{"type":"PARENT","target":' || $2 || '}]')::jsonb
            ORDER BY name
            """, world_id, str(entity_id),
        )
        sg_ids = [r["id"] for r in site_govt_rows]

        # Batch-fetch data for all site govts in one pass
        sg_sites: dict[int, dict] = {}
        sg_structures: dict[int, list[str]] = {}
        sg_populations: dict[int, int] = {}
        sg_positions_map: dict[int, list] = {}
        civ_noble_sg_map: dict[int, dict] = {}

        if sg_ids:
            # Sites owned by site govts
            site_rows = await conn.fetch(
                "SELECT id, name, type, owner_entity_id FROM sites "
                "WHERE world_id = $1 AND owner_entity_id = ANY($2::int[]) ORDER BY name",
                world_id, sg_ids,
            )
            for s in site_rows:
                sg_sites[s["owner_entity_id"]] = {
                    "id": s["id"], "name": s["name"], "type": s["type"],
                }
            site_ids = [s["id"] for s in site_rows]

            # Structures in those sites
            if site_ids:
                struct_rows = await conn.fetch(
                    "SELECT site_id, type FROM structures "
                    "WHERE world_id = $1 AND site_id = ANY($2::int[]) ORDER BY type",
                    world_id, site_ids,
                )
                # Map site_id→owner_entity_id for grouping
                site_to_sg = {s["id"]: s["owner_entity_id"] for s in site_rows}
                for st in struct_rows:
                    sg_id = site_to_sg.get(st["site_id"])
                    if sg_id:
                        sg_structures.setdefault(sg_id, []).append(st["type"])

            # Population counts per site govt
            pop_rows = await conn.fetch(
                "SELECT entity_id, COUNT(*) AS cnt FROM hf_entity_links "
                "WHERE world_id = $1 AND entity_id = ANY($2::int[]) "
                "AND link_type IN ('member', 'former member') "
                "GROUP BY entity_id",
                world_id, sg_ids,
            )
            for pr in pop_rows:
                sg_populations[pr["entity_id"]] = pr["cnt"]

            # Positions + current holders for all site govts
            sg_pos_rows = await conn.fetch(
                """
                SELECT ep.entity_id, ep.position_id, ep.name, ep.name_male, ep.name_female,
                       h.hf_id AS holder_hf_id, h.holder_name, h.holder_caste
                FROM entity_positions ep
                LEFT JOIN LATERAL (
                    SELECT hpl.hf_id, hf.name AS holder_name, hf.caste AS holder_caste
                    FROM hf_position_links hpl
                    JOIN historical_figures hf
                        ON hf.world_id = hpl.world_id AND hf.id = hpl.hf_id
                    WHERE hpl.world_id = ep.world_id AND hpl.entity_id = ep.entity_id
                      AND hpl.position_id = ep.position_id AND hpl.end_year IS NULL
                    ORDER BY hpl.start_year DESC
                    LIMIT 1
                ) h ON true
                WHERE ep.world_id = $1 AND ep.entity_id = ANY($2::int[])
                ORDER BY ep.entity_id, ep.name
                """, world_id, sg_ids,
            )
            for sp in sg_pos_rows:
                is_noble = bool(sp["name_male"] or sp["name_female"])
                pos_dict = {
                    "position_id": sp["position_id"],
                    "name": sp["name"],
                    "category": _categorize_position(sp["name"]),
                    "is_noble": is_noble,
                }
                if sp["holder_hf_id"] is not None:
                    title = _gender_title(dict(sp), sp["holder_caste"])
                    pos_dict["title"] = title
                    pos_dict["current_holder"] = {
                        "hf_id": sp["holder_hf_id"],
                        "name": sp["holder_name"],
                    }
                else:
                    pos_dict["title"] = sp["name_male"] or sp["name_female"]
                    pos_dict["current_holder"] = None
                sg_positions_map.setdefault(sp["entity_id"], []).append(pos_dict)

            # ── Civ-level nobles mapped to site govts ──
            # Barons/dukes/counts are civ-level positions; find which site
            # govt each holder currently belongs to
            civ_noble_by_sg = await conn.fetch(
                """
                SELECT DISTINCT ON (hel.entity_id)
                    hel.entity_id AS sg_id,
                    ep.name AS pos_name, ep.name_male, ep.name_female,
                    hpl.hf_id, hf.name AS hf_name, hf.caste AS hf_caste
                FROM entity_positions ep
                JOIN hf_position_links hpl
                    ON hpl.world_id = ep.world_id
                    AND hpl.entity_id = ep.entity_id
                    AND hpl.position_id = ep.position_id
                    AND hpl.end_year IS NULL
                JOIN historical_figures hf
                    ON hf.world_id = hpl.world_id AND hf.id = hpl.hf_id
                JOIN hf_entity_links hel
                    ON hel.world_id = hpl.world_id AND hel.hf_id = hpl.hf_id
                    AND hel.entity_id = ANY($2::int[])
                    AND hel.link_type = 'member'
                WHERE ep.world_id = $1 AND ep.entity_id = $3
                  AND (ep.name_male IS NOT NULL OR ep.name_female IS NOT NULL)
                  AND ep.name NOT IN ('monarch')
                ORDER BY hel.entity_id,
                    CASE WHEN LOWER(ep.name) NOT IN ('lord') THEN 0 ELSE 1 END,
                    ep.position_id
                """, world_id, sg_ids, entity_id,
            )
            civ_noble_sg_map: dict[int, dict] = {}
            for cn in civ_noble_by_sg:
                title = _gender_title(dict(cn), cn["hf_caste"])
                civ_noble_sg_map[cn["sg_id"]] = {
                    "hf_id": cn["hf_id"],
                    "name": cn["hf_name"],
                    "title": title or cn["pos_name"],
                }

        # ── Direct member count for civ itself ──
        civ_member_count = await conn.fetchval(
            "SELECT COUNT(*) FROM hf_entity_links "
            "WHERE world_id = $1 AND entity_id = $2 "
            "AND link_type IN ('member', 'former member')",
            world_id, entity_id,
        )

        wars = await conn.fetch(
            """
            SELECT id, name, type, start_year, end_year,
                CASE WHEN attacker_entity_id = $2 THEN 'attacker' ELSE 'defender' END AS role
            FROM history_event_collections
            WHERE world_id = $1 AND type = 'war'
              AND (attacker_entity_id = $2 OR defender_entity_id = $2)
            ORDER BY start_year
            """, world_id, entity_id,
        )

    # ── Build response ──
    result = dict(entity)

    # Civ-level positions
    civ_positions = []
    for p in positions:
        pos_dict = {
            "position_id": p["position_id"],
            "name": p["name"],
            "name_male": p["name_male"],
            "name_female": p["name_female"],
            "category": _categorize_position(p["name"]),
        }
        if p["holder_hf_id"] is not None:
            title = _gender_title(dict(p), p["holder_caste"])
            pos_dict["current_holder"] = {
                "hf_id": p["holder_hf_id"],
                "name": p["holder_name"],
            }
            pos_dict["title"] = title
        else:
            pos_dict["current_holder"] = None
            pos_dict["title"] = p["name_male"] or p["name_female"]
        civ_positions.append(pos_dict)
    result["positions"] = civ_positions

    # Find civ ruler: position_id 0 is always the ruler in DF
    # (monarch for dwarves, law-giver for humans, master for goblins)
    ruler = None
    for p in civ_positions:
        if p["position_id"] == 0 and p["current_holder"]:
            ruler = {
                "hf_id": p["current_holder"]["hf_id"],
                "name": p["current_holder"]["name"],
                "title": p.get("title") or p["name"],
            }
            break

    # Site govts with enriched data
    site_govts = []
    for sg in site_govt_rows:
        sg_id = sg["id"]
        site = sg_sites.get(sg_id)
        sg_pos = sg_positions_map.get(sg_id, [])
        # Find site govt ruler: best noble with a holder
        # Prefer non-lord/lady nobles (baron, duke, count, etc.),
        # fall back to lord/lady if that's the only noble present
        sg_ruler = None
        best_noble = None
        lord_fallback = None
        for sp in sg_pos:
            if not sp.get("is_noble") or not sp.get("current_holder"):
                continue
            title_lower = (sp.get("title") or sp["name"]).lower()
            if title_lower in _LORD_LADY:
                if lord_fallback is None:
                    lord_fallback = sp
            else:
                best_noble = sp
                break  # first non-lord/lady noble wins
        chosen = best_noble or lord_fallback
        if chosen:
            sg_ruler = {
                "hf_id": chosen["current_holder"]["hf_id"],
                "name": chosen["current_holder"]["name"],
                "title": chosen.get("title") or chosen["name"],
            }
        elif sg_id in civ_noble_sg_map:
            # Fallback: civ-level noble (baron/duke/count) mapped to this site govt
            sg_ruler = civ_noble_sg_map[sg_id]
        site_govts.append({
            "id": sg_id,
            "name": sg["name"],
            "site": site,
            "structures": sg_structures.get(sg_id, []),
            "population": sg_populations.get(sg_id, 0),
            "ruler": sg_ruler,
            "positions": sg_pos,
        })

    total_population = civ_member_count + sum(sg["population"] for sg in site_govts)

    result["ruler"] = ruler
    result["total_population"] = total_population
    result["site_count"] = len([sg for sg in site_govts if sg["site"]])
    result["site_govts"] = site_govts
    result["wars"] = [dict(w) for w in wars]
    return result


@router.get("/civilizations/{world_id}/{entity_id}/members")
async def list_members(
    request: Request, world_id: int, entity_id: int,
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        exists = await conn.fetchval(
            "SELECT 1 FROM entities WHERE world_id = $1 AND id = $2",
            world_id, entity_id,
        )
        if not exists:
            raise HTTPException(404, "Entity not found")

        total = await conn.fetchval(
            "SELECT COUNT(*) FROM hf_entity_links "
            "WHERE world_id = $1 AND entity_id = $2 "
            "AND link_type IN ('member', 'former member')",
            world_id, entity_id,
        )
        members = await conn.fetch(
            """
            SELECT hel.hf_id, hf.name, hf.race, hel.link_type,
                   pos.position_name,
                   (hf.death_year IS NULL) AS is_alive,
                   hf.skills
            FROM hf_entity_links hel
            JOIN historical_figures hf ON hf.world_id = hel.world_id AND hf.id = hel.hf_id
            LEFT JOIN LATERAL (
                SELECT ep.name AS position_name
                FROM hf_position_links hpl
                JOIN entity_positions ep
                    ON ep.world_id = hpl.world_id AND ep.entity_id = hpl.entity_id
                    AND ep.position_id = hpl.position_id
                WHERE hpl.world_id = hel.world_id AND hpl.hf_id = hel.hf_id
                  AND hpl.entity_id = hel.entity_id
                ORDER BY hpl.end_year IS NULL DESC, hpl.start_year DESC
                LIMIT 1
            ) pos ON true
            WHERE hel.world_id = $1 AND hel.entity_id = $2
              AND hel.link_type IN ('member', 'former member')
            ORDER BY hf.name LIMIT $3 OFFSET $4
            """, world_id, entity_id, limit, offset,
        )

    result_members = []
    for m in members:
        d = dict(m)
        # Derive profession from highest-IP skill
        skills = d.pop("skills", None)
        profession = None
        if skills and isinstance(skills, list):
            top = max(skills, key=lambda s: s.get("total_ip", 0), default=None)
            if top:
                profession = top["name"].replace("_", " ").title()
        d["profession"] = profession
        result_members.append(d)
    return {"total": total, "members": result_members}


@router.get("/civilizations/{world_id}/{entity_id}/positions")
async def list_positions(request: Request, world_id: int, entity_id: int):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        positions = await conn.fetch(
            "SELECT position_id, name, name_male, name_female FROM entity_positions "
            "WHERE world_id = $1 AND entity_id = $2 ORDER BY name",
            world_id, entity_id,
        )
        holders = await conn.fetch(
            """
            SELECT hpl.position_id, hpl.hf_id, hf.name, hpl.start_year, hpl.end_year
            FROM hf_position_links hpl
            JOIN historical_figures hf ON hf.world_id = hpl.world_id AND hf.id = hpl.hf_id
            WHERE hpl.world_id = $1 AND hpl.entity_id = $2
            ORDER BY hpl.position_id, hpl.start_year
            """, world_id, entity_id,
        )

    holders_by_pos: dict[int, list[dict]] = {}
    for h in holders:
        holders_by_pos.setdefault(h["position_id"], []).append({
            "hf_id": h["hf_id"], "name": h["name"],
            "start_year": h["start_year"], "end_year": h["end_year"],
        })

    return [
        {"position_id": p["position_id"], "name": p["name"],
         "name_male": p["name_male"], "name_female": p["name_female"],
         "holders": holders_by_pos.get(p["position_id"], [])}
        for p in positions
    ]
