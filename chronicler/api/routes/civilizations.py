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


# ─── Sentience filter SQL fragment ───────────────────────────────────────
# A creature is sentient if creature_dictionary flags include
# has_any_intelligent_speaks OR has_any_intelligent_learns.
# Fallback for missing dictionary entries: exclude GIANT_* without _MAN suffix.
SENTIENCE_FILTER = """(
    cd.flags->>'has_any_intelligent_speaks' = 'true'
    OR cd.flags->>'has_any_intelligent_learns' = 'true'
    OR (cd.creature_id IS NULL AND NOT (
        hf.race LIKE 'GIANT_%' AND hf.race NOT LIKE '%_MAN'
    ))
)"""

SENTIENCE_JOIN = (
    "LEFT JOIN creature_dictionary cd "
    "ON cd.world_id = hf.world_id AND cd.creature_id = hf.race"
)


async def fetch_site_residents_batch(
    conn, world_id: int, site_ids: list[int],
) -> dict[int, int]:
    """Count living sentient HFs at each site.

    Uses UNION of:
    1. whereabouts->>'site_id' (physical presence)
    2. hf_site_links (structural links: home, occupation, seat of power, lair)
    Both filtered by death_year IS NULL + sentience (creature_dictionary).
    """
    if not site_ids:
        return {}
    rows = await conn.fetch(f"""
        SELECT site_id, COUNT(DISTINCT hf_id) AS cnt
        FROM (
            SELECT (hf.whereabouts->>'site_id')::int AS site_id, hf.id AS hf_id
            FROM historical_figures hf
            {SENTIENCE_JOIN}
            WHERE hf.world_id = $1 AND hf.death_year IS NULL
              AND (hf.whereabouts->>'site_id')::int = ANY($2::int[])
              AND {SENTIENCE_FILTER}
            UNION
            SELECT hsl.site_id, hsl.hf_id
            FROM hf_site_links hsl
            JOIN historical_figures hf ON hf.world_id = hsl.world_id AND hf.id = hsl.hf_id
            {SENTIENCE_JOIN}
            WHERE hsl.world_id = $1 AND hsl.site_id = ANY($2::int[])
              AND hf.death_year IS NULL
              AND {SENTIENCE_FILTER}
        ) sub
        GROUP BY site_id
    """, world_id, site_ids)
    return {r["site_id"]: r["cnt"] for r in rows}


async def fetch_site_residents_count(
    conn, world_id: int, site_id: int,
) -> int:
    """Single-site convenience wrapper."""
    result = await fetch_site_residents_batch(conn, world_id, [site_id])
    return result.get(site_id, 0)


# ─── Reusable helpers (shared by JSON API + detail page) ──────────────────


async def fetch_civilization_data(conn, world_id: int, entity_id: int) -> dict | None:
    """Fetch full civilization detail data. Returns dict or None if not found.

    Standalone helper so both the JSON API route and the detail page route
    can share the same logic without duplicating 270 lines of SQL.
    """
    entity = await conn.fetchrow(
        "SELECT id, world_id, name, type, race FROM entities "
        "WHERE world_id = $1 AND id = $2",
        world_id, entity_id,
    )
    if not entity:
        return None

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

    is_civ = entity["type"] == "civilization"

    # Batch-fetch data for all site govts in one pass
    sg_sites: dict[int, dict] = {}
    sg_structures: dict[int, list[str]] = {}
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
            # Map site_id->owner_entity_id for grouping
            site_to_sg = {s["id"]: s["owner_entity_id"] for s in site_rows}
            for st in struct_rows:
                sg_id = site_to_sg.get(st["site_id"])
                if sg_id:
                    sg_structures.setdefault(sg_id, []).append(st["type"])

    if sg_ids:
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
        civ_noble_sg_map = {}
        for cn in civ_noble_by_sg:
            title = _gender_title(dict(cn), cn["hf_caste"])
            civ_noble_sg_map[cn["sg_id"]] = {
                "hf_id": cn["hf_id"],
                "name": cn["hf_name"],
                "title": title or cn["pos_name"],
            }

    # ── Population counts ──
    # Deduplicated across civ + child SGs to avoid double-counting HFs
    # who belong to both a civilization and its child site government.
    all_entity_ids = [entity_id] + sg_ids
    population_stats = await conn.fetchrow(
        f"""
        SELECT
            COUNT(DISTINCT hel.hf_id) AS total_known_hfs,
            COUNT(DISTINCT hel.hf_id) FILTER (WHERE hel.link_type = 'member') AS current_members,
            COUNT(DISTINCT hel.hf_id) FILTER (
                WHERE hel.link_type = 'member' AND hf.death_year IS NULL
                AND {SENTIENCE_FILTER}
            ) AS citizens
        FROM hf_entity_links hel
        JOIN historical_figures hf ON hf.world_id = $1 AND hf.id = hel.hf_id
        {SENTIENCE_JOIN}
        WHERE hel.world_id = $1 AND hel.entity_id = ANY($2::int[])
          AND hel.link_type IN ('member', 'former member')
        """,
        world_id, all_entity_ids,
    )

    # DF native population (entity_populations) — civs only
    df_population = 0
    if is_civ:
        df_population = await conn.fetchval(
            "SELECT COALESCE(SUM(count), 0) FROM entity_populations "
            "WHERE world_id = $1 AND civ_id = $2",
            world_id, entity_id,
        ) or 0

    # Per-site residents via whereabouts + site_links (sentience-filtered)
    all_site_ids = [s["id"] for s in (site_rows if sg_ids else [])]
    if not is_civ:
        direct_site_rows_for_residents = await conn.fetch(
            "SELECT id FROM sites WHERE world_id = $1 AND owner_entity_id = $2",
            world_id, entity_id,
        )
        all_site_ids += [s["id"] for s in direct_site_rows_for_residents]
    site_residents = await fetch_site_residents_batch(conn, world_id, all_site_ids)
    total_residents = sum(site_residents.values())

    wars = await conn.fetch(
        """
        SELECT w.id, w.name, w.type, w.start_year, w.end_year,
            w.attacker_entity_id, w.defender_entity_id,
            CASE WHEN w.attacker_entity_id = $2 THEN 'attacker' ELSE 'defender' END AS role,
            -- Peace treaty: who requested it
            peace.requester AS peace_requester,
            -- Site conquest tallies
            COALESCE(conquests.atk_sites, 0) AS atk_conquests,
            COALESCE(conquests.def_sites, 0) AS def_conquests
        FROM history_event_collections w
        LEFT JOIN LATERAL (
            SELECT (p.details->>'source')::int AS requester
            FROM history_events p
            WHERE p.world_id = w.world_id AND p.event_type = 'peace accepted'
              AND p.year = w.end_year
              AND ((p.details->>'source' = w.attacker_entity_id::text
                    AND p.details->>'destination' = w.defender_entity_id::text)
                OR (p.details->>'source' = w.defender_entity_id::text
                    AND p.details->>'destination' = w.attacker_entity_id::text))
            LIMIT 1
        ) peace ON true
        LEFT JOIN LATERAL (
            SELECT
                COUNT(*) FILTER (WHERE sc.attacker_entity_id = w.attacker_entity_id) AS atk_sites,
                COUNT(*) FILTER (WHERE sc.attacker_entity_id = w.defender_entity_id) AS def_sites
            FROM history_event_collections sc
            WHERE sc.world_id = w.world_id AND sc.parent_id = w.id
              AND sc.type = 'site conquered'
        ) conquests ON true
        WHERE w.world_id = $1 AND w.type = 'war'
          AND (w.attacker_entity_id = $2 OR w.defender_entity_id = $2)
        ORDER BY w.start_year
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

    # Find which site govt the civ ruler resides in
    ruler_sg_id = None
    if ruler and sg_ids:
        ruler_sg_id = await conn.fetchval(
            "SELECT entity_id FROM hf_entity_links "
            "WHERE world_id = $1 AND hf_id = $2 AND entity_id = ANY($3::int[]) "
            "AND link_type = 'member' LIMIT 1",
            world_id, ruler["hf_id"], sg_ids,
        )

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
            "residents": site_residents.get(site["id"], 0) if site else 0,
            "ruler": sg_ruler,
            "positions": sg_pos,
            "is_ruler_site": sg_id == ruler_sg_id,
        })

    # For non-civilization entities, also fetch directly-owned sites.
    # Each owned site becomes a row in the Sites tab with this entity as the "govt".
    direct_site_rows = []
    if not is_civ:
        direct_site_rows = await conn.fetch(
            "SELECT id, name, type FROM sites "
            "WHERE world_id = $1 AND owner_entity_id = $2 ORDER BY name",
            world_id, entity_id,
        )
        if direct_site_rows:
            # Structures in those sites
            direct_site_ids = [s["id"] for s in direct_site_rows]
            direct_structs = await conn.fetch(
                "SELECT site_id, type FROM structures "
                "WHERE world_id = $1 AND site_id = ANY($2::int[]) ORDER BY type",
                world_id, direct_site_ids,
            )
            site_structs: dict[int, list[str]] = {}
            for st in direct_structs:
                site_structs.setdefault(st["site_id"], []).append(st["type"])

            # Entity's own positions/ruler already computed above
            own_pos = sg_positions_map.get(entity_id, [])
            own_ruler = None
            best_noble = None
            lord_fallback = None
            for sp in own_pos:
                if not sp.get("is_noble") or not sp.get("current_holder"):
                    continue
                title_lower = (sp.get("title") or sp["name"]).lower()
                if title_lower in _LORD_LADY:
                    if lord_fallback is None:
                        lord_fallback = sp
                else:
                    best_noble = sp
                    break
            chosen = best_noble or lord_fallback
            if chosen:
                own_ruler = {
                    "hf_id": chosen["current_holder"]["hf_id"],
                    "name": chosen["current_holder"]["name"],
                    "title": chosen.get("title") or chosen["name"],
                }

            for s in direct_site_rows:
                site_govts.append({
                    "id": entity_id,
                    "name": entity["name"],
                    "site": {"id": s["id"], "name": s["name"], "type": s["type"]},
                    "structures": site_structs.get(s["id"], []),
                    "residents": site_residents.get(s["id"], 0),
                    "ruler": own_ruler,
                    "positions": own_pos,
                    "is_ruler_site": False,
                })

    result["ruler"] = ruler
    result["citizens"] = int(population_stats["citizens"])
    result["total_known_hfs"] = int(population_stats["total_known_hfs"])
    result["current_members"] = int(population_stats["current_members"])
    result["is_civ"] = is_civ
    if is_civ:
        result["df_population"] = df_population
        result["total_residents"] = total_residents
    if is_civ:
        result["site_count"] = len(site_rows) if sg_ids else 0
    else:
        # Count all sites shown: child sg sites + directly-owned sites
        direct_count = len(direct_site_rows) if direct_site_rows else 0
        child_count = len(site_rows) if sg_ids else 0
        result["site_count"] = child_count + direct_count
    result["site_govts"] = site_govts
    # Compute perspectival outcome for each war relative to entity_id
    war_list = []
    for w in wars:
        wd = dict(w)
        is_attacker = wd["role"] == "attacker"
        my_conquests = wd["atk_conquests"] if is_attacker else wd["def_conquests"]
        their_conquests = wd["def_conquests"] if is_attacker else wd["atk_conquests"]

        if wd["end_year"] is None:
            outcome = "ongoing"
        elif wd["peace_requester"] is not None:
            outcome = "treaty"
        elif my_conquests > their_conquests:
            outcome = "victory"
        elif their_conquests > my_conquests:
            outcome = "defeat"
        elif my_conquests == their_conquests and my_conquests > 0:
            outcome = "stalemate"
        else:
            outcome = "inconclusive"

        wd["outcome"] = outcome
        wd["my_conquests"] = my_conquests
        wd["their_conquests"] = their_conquests
        # Clean up internal fields
        for k in ("peace_requester", "atk_conquests", "def_conquests",
                   "attacker_entity_id", "defender_entity_id"):
            wd.pop(k, None)
        war_list.append(wd)
    result["wars"] = war_list
    return result


async def fetch_civilization_members(
    conn, world_id: int, entity_id: int,
    limit: int = 50, offset: int = 0,
) -> dict:
    """Fetch paginated members with profession derivation. Returns {total, members}.

    Standalone helper shared by the JSON API route and the detail page route.
    """
    counts = await conn.fetchrow("""
        SELECT COUNT(*) AS total,
               COUNT(*) FILTER (WHERE hel.link_type = 'member') AS current_total,
               COUNT(*) FILTER (WHERE hel.link_type = 'former member') AS former_total,
               COUNT(*) FILTER (WHERE hf.death_year IS NULL) AS alive_total,
               COUNT(*) FILTER (WHERE hel.link_type = 'member' AND hf.death_year IS NULL) AS current_alive
        FROM hf_entity_links hel
        JOIN historical_figures hf ON hf.world_id = hel.world_id AND hf.id = hel.hf_id
        WHERE hel.world_id = $1 AND hel.entity_id = $2
          AND hel.link_type IN ('member', 'former member')
    """, world_id, entity_id)
    total = counts["total"]
    members = await conn.fetch(
        f"""
        SELECT hel.hf_id, hf.name, hf.race, hel.link_type,
               pos.position_name,
               (hf.death_year IS NULL) AS is_alive,
               hf.skills,
               (hel.link_type = 'member' AND hf.death_year IS NULL
                AND {SENTIENCE_FILTER}) AS is_citizen
        FROM hf_entity_links hel
        JOIN historical_figures hf ON hf.world_id = hel.world_id AND hf.id = hel.hf_id
        {SENTIENCE_JOIN}
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
    return {
        "total": total,
        "current_total": counts["current_total"],
        "former_total": counts["former_total"],
        "alive_total": counts["alive_total"],
        "current_alive": counts["current_alive"],
        "members": result_members,
    }


# ─── API routes (thin wrappers around helpers) ────────────────────────────


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
    # Two counting strategies depending on entity type:
    # - Civilizations: roll up members/sites from child site governments
    #   (civs own sites indirectly: civ -> site_govt PARENT link -> site)
    # - All other types: count direct members and directly-owned sites
    # member_count: direct members only (no roll-up to avoid double-counting)
    # site_count: civs use roll-up via child SGs; others use direct ownership
    query = f"""
        WITH child_sg AS (
            SELECT sg.id AS sg_id,
                   (el->>'target')::int AS parent_id
            FROM entities sg,
                 jsonb_array_elements(sg.details->'entity_links') el
            WHERE sg.world_id = $1 AND sg.type = 'sitegovernment'
              AND el->>'type' = 'PARENT'
        ),
        mem_counts AS (
            SELECT entity_id, COUNT(*) AS cnt
            FROM hf_entity_links WHERE world_id = $1
              AND link_type = 'member'
            GROUP BY entity_id
        ),
        civ_sites AS (
            SELECT cs.parent_id AS civ_id, COUNT(*) AS cnt
            FROM sites s
            JOIN child_sg cs ON cs.sg_id = s.owner_entity_id
            WHERE s.world_id = $1
            GROUP BY cs.parent_id
        ),
        direct_sites AS (
            SELECT owner_entity_id AS entity_id, COUNT(*) AS cnt
            FROM sites WHERE world_id = $1 AND owner_entity_id IS NOT NULL
            GROUP BY owner_entity_id
        ),
        ep_totals AS (
            SELECT civ_id, SUM(count) AS pop
            FROM entity_populations WHERE world_id = $1
            GROUP BY civ_id
        )
        SELECT e.id, e.world_id, e.name, e.type, e.race,
            COALESCE(mc.cnt, 0) AS member_count,
            CASE WHEN e.type = 'civilization'
                THEN COALESCE(csit.cnt, 0)
                ELSE COALESCE(ds.cnt, 0)
            END AS site_count,
            COALESCE(pos.cnt, 0) AS position_count,
            COALESCE(ept.pop, 0) AS entity_population
        FROM entities e
        LEFT JOIN mem_counts mc ON mc.entity_id = e.id
        LEFT JOIN civ_sites csit ON csit.civ_id = e.id
        LEFT JOIN direct_sites ds ON ds.entity_id = e.id
        LEFT JOIN (
            SELECT world_id, entity_id, COUNT(*) AS cnt
            FROM entity_positions WHERE world_id = $1
            GROUP BY world_id, entity_id
        ) pos ON pos.world_id = e.world_id AND pos.entity_id = e.id
        LEFT JOIN ep_totals ept ON ept.civ_id = e.id
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
        result = await fetch_civilization_data(conn, world_id, entity_id)
    if not result:
        raise HTTPException(404, "Entity not found")
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
        return await fetch_civilization_members(conn, world_id, entity_id, limit, offset)


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
