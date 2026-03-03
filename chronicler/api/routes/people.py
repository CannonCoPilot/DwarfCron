"""People router — search and detail views for historical figures and units."""

import json
import re

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

# Collapsed race category keys (underscore-prefixed)
_COLLAPSED_CATEGORIES = {
    "_demigod", "_gods", "_forgotten_beast", "_titan",
    "_night_creature", "_demon", "_animated_dead", "_animal_people",
}


def _type_flags(row: dict) -> list[str]:
    return [label for col, label in _TYPE_FLAG_COLS if row.get(col)]


_VARIANT_FLAG_MAP = {
    "vampire": "h.is_vampire = TRUE",
    "necromancer": "h.is_necromancer = TRUE",
    "werebeast": "h.is_werebeast = TRUE",
    "ghost": "h.is_ghost = TRUE",
    "animated_dead": "h.race LIKE 'HFEXP%'",
}


def _build_variant_clause(variant_flags: str | None) -> str:
    """Build SQL WHERE clause for variant flag filtering (OR logic)."""
    if not variant_flags:
        return ""
    flags = [f.strip() for f in variant_flags.split(",") if f.strip() in _VARIANT_FLAG_MAP]
    if not flags:
        return ""
    conditions = [_VARIANT_FLAG_MAP[f] for f in flags]
    return "AND (" + " OR ".join(conditions) + ")"


def _is_animal_person(creature_id: str) -> bool:
    """Check if a creature_id follows the DF animal person pattern."""
    return bool(creature_id and (
        creature_id.endswith("_MAN") or creature_id == "RODENT MAN"
    ))


def _race_display_name(race: str | None, cd_name: str | None = None) -> str:
    """Resolve a raw race token to a human-readable display name.

    Priority: creature_dictionary name_singular > titlecased token.
    For HFEXP (necromancer experiment) races without a dictionary entry,
    returns "Experiment" instead of the cryptic code.
    """
    if not race:
        return "Unknown"
    if cd_name:
        # Capitalize first letter of each word, but respect apostrophe
        # contractions (e.g., "night's demon" → "Night's Demon", not "Night'S Demon")
        return " ".join(
            w[0].upper() + w[1:] if w else w
            for w in cd_name.split(" ")
        )
    if race.startswith("HFEXP"):
        return "Experiment"
    return race.replace("_", " ").title()


# ---------------------------------------------------------------------------
# 1. Unified search
# ---------------------------------------------------------------------------

@router.get("/people/search")
async def search_people(
    request: Request,
    q: str = Query(..., min_length=1),
    type: str = Query("all"),
    limit: int = Query(100, ge=1, le=500),
    world_id: int = Query(None),
    race_categories: str = Query(None),
    alive: str = Query(None),
    variant_flags: str = Query(None),
):
    """Search people by name with optional race, alive/dead, and variant filters.

    race_categories: comma-separated race keys (multi-select)
    alive: "alive", "dead", or None (all)
    variant_flags: comma-separated variant keys (vampire,necromancer,werebeast,ghost,animated_dead)
    """
    pool = request.app.state.pool
    pattern = f"%{q}%"
    results: list[dict] = []

    async with pool.acquire() as conn:
        if world_id is None:
            world_id = await _resolve_world_id(conn, None)

        if type in ("all", "unit"):
            unit_clauses = []
            unit_params = [pattern, limit]
            uidx = 3
            if alive == "alive":
                unit_clauses.append("AND u.is_alive = TRUE")
            elif alive == "dead":
                unit_clauses.append("AND u.is_alive = FALSE")
            unit_where = " ".join(unit_clauses)

            rows = await conn.fetch(
                f"""
                SELECT u.id, u.world_id, u.name, u.english_name, u.race, u.caste,
                       u.profession, u.is_alive,
                       cd.name_singular AS race_name
                FROM units u
                LEFT JOIN creature_dictionary cd
                       ON cd.world_id = u.world_id AND cd.creature_id = u.race
                WHERE (unaccent(u.name) ILIKE unaccent($1)
                   OR unaccent(COALESCE(u.english_name, '')) ILIKE unaccent($1))
                {unit_where}
                ORDER BY u.name
                LIMIT $2
                """,
                *unit_params,
            )
            for r in rows:
                results.append({
                    "source": "unit", "id": r["id"], "world_id": r["world_id"],
                    "name": r["name"], "english_name": r["english_name"],
                    "race": r["race"],
                    "race_display": _race_display_name(r["race"], r.get("race_name")),
                    "is_alive": r["is_alive"],
                    "profession": r["profession"], "type_flags": [],
                })

        if type in ("all", "hf"):
            remaining = limit - len(results)
            if remaining > 0:
                extra_clauses = []
                params = [pattern, remaining]
                next_idx = 3

                # Alive/dead filter
                if alive == "alive":
                    extra_clauses.append("AND h.death_year IS NULL")
                elif alive == "dead":
                    extra_clauses.append("AND h.death_year IS NOT NULL")

                # Multi-select race categories
                if race_categories:
                    cats = [c.strip() for c in race_categories.split(",") if c.strip()]
                    if cats:
                        race_parts = []
                        for cat in cats:
                            rc_clause, rc_params = _build_race_category_clause(cat, next_idx)
                            if rc_clause:
                                # Strip leading "AND " to combine with OR
                                race_parts.append(rc_clause.lstrip("AND "))
                                params.extend(rc_params)
                                next_idx += len(rc_params)
                        if race_parts:
                            extra_clauses.append("AND (" + " OR ".join(race_parts) + ")")

                # Variant flag filter (vampire, necromancer, etc.)
                vf_clause = _build_variant_clause(variant_flags)
                if vf_clause:
                    extra_clauses.append(vf_clause)

                where_extra = " ".join(extra_clauses)
                rows = await conn.fetch(
                    f"""
                    SELECT h.id, h.world_id, h.name, h.race, h.caste, h.death_year,
                           h.is_deity, h.is_force, h.is_vampire,
                           h.is_necromancer, h.is_werebeast, h.is_ghost,
                           h.prominence_score,
                           cd.name_singular AS race_name
                    FROM historical_figures h
                    LEFT JOIN creature_dictionary cd
                           ON cd.world_id = h.world_id AND cd.creature_id = h.race
                    WHERE unaccent(h.name) ILIKE unaccent($1)
                    {where_extra}
                    ORDER BY h.prominence_score DESC NULLS LAST, h.name
                    LIMIT $2
                    """,
                    *params,
                )
                for r in rows:
                    row = dict(r)
                    results.append({
                        "source": "hf", "id": row["id"], "world_id": row["world_id"],
                        "name": row["name"], "english_name": None,
                        "race": row["race"],
                        "race_display": _race_display_name(row["race"], row.get("race_name")),
                        "is_alive": row["death_year"] is None,
                        "profession": None, "type_flags": _type_flags(row),
                    })
    return results


# ---------------------------------------------------------------------------
# 1b. Browse (default listing — top HFs by importance)
# ---------------------------------------------------------------------------

async def _resolve_world_id(conn, world_id: int | None) -> int | None:
    if world_id is None:
        world_id = await conn.fetchval(
            "SELECT id FROM worlds ORDER BY id LIMIT 1"
        )
    return world_id


def _build_race_category_clause(race_category: str, param_idx: int) -> tuple[str, list]:
    """Build SQL WHERE clause fragment for a race_category filter.

    Returns (clause_string, extra_params). clause_string uses $N placeholders
    starting at param_idx.
    """
    if not race_category:
        return "", []

    rc = race_category.strip()

    if rc == "_demigod":
        # Exclude creatures with beast/titan/demon/night flags (they have
        # is_deity=TRUE in DF data but are categorized by creature type)
        return (
            "AND h.is_deity = TRUE AND h.death_year IS NULL "
            "AND NOT EXISTS (SELECT 1 FROM creature_dictionary cd "
            "WHERE cd.world_id = h.world_id AND cd.creature_id = h.race "
            "AND (cd.flags @> '{\"has_any_feature_beast\": true}'::jsonb "
            "OR cd.flags @> '{\"has_any_titan\": true}'::jsonb "
            "OR cd.flags @> '{\"has_any_unique_demon\": true}'::jsonb "
            "OR cd.flags @> '{\"has_any_night_creature\": true}'::jsonb))",
            [],
        )
    if rc == "_gods":
        return (
            "AND h.is_deity = TRUE AND h.death_year IS NOT NULL "
            "AND NOT EXISTS (SELECT 1 FROM creature_dictionary cd "
            "WHERE cd.world_id = h.world_id AND cd.creature_id = h.race "
            "AND (cd.flags @> '{\"has_any_feature_beast\": true}'::jsonb "
            "OR cd.flags @> '{\"has_any_titan\": true}'::jsonb "
            "OR cd.flags @> '{\"has_any_unique_demon\": true}'::jsonb "
            "OR cd.flags @> '{\"has_any_night_creature\": true}'::jsonb))",
            [],
        )
    if rc == "_animated_dead":
        return f"AND h.race LIKE ${param_idx}", ["HFEXP%"]
    if rc == "_animal_people":
        return (
            f"AND (h.race LIKE ${param_idx} OR h.race = ${param_idx + 1}) "
            "AND h.race NOT IN ('DWARF','ELF','GOBLIN','HUMAN','KOBOLD')",
            ["%\\_MAN", "RODENT MAN"],
        )
    if rc == "_forgotten_beast":
        return (
            f"AND EXISTS (SELECT 1 FROM creature_dictionary cd "
            f"WHERE cd.world_id = h.world_id AND cd.creature_id = h.race "
            f"AND cd.flags @> '{{\"has_any_feature_beast\": true}}'::jsonb)",
            [],
        )
    if rc == "_titan":
        return (
            f"AND EXISTS (SELECT 1 FROM creature_dictionary cd "
            f"WHERE cd.world_id = h.world_id AND cd.creature_id = h.race "
            f"AND cd.flags @> '{{\"has_any_titan\": true}}'::jsonb)",
            [],
        )
    if rc == "_night_creature":
        return (
            f"AND EXISTS (SELECT 1 FROM creature_dictionary cd "
            f"WHERE cd.world_id = h.world_id AND cd.creature_id = h.race "
            f"AND cd.flags @> '{{\"has_any_night_creature\": true}}'::jsonb)",
            [],
        )
    if rc == "_demon":
        return (
            f"AND EXISTS (SELECT 1 FROM creature_dictionary cd "
            f"WHERE cd.world_id = h.world_id AND cd.creature_id = h.race "
            f"AND cd.flags @> '{{\"has_any_unique_demon\": true}}'::jsonb)",
            [],
        )

    if rc == "_other":
        # Everything not caught by entity races, deity, beast/titan/demon/night,
        # animated dead, or animal people
        return (
            "AND h.is_deity = FALSE "
            "AND h.race NOT LIKE 'HFEXP%' "
            "AND h.race NOT LIKE '%\\_MAN' AND h.race != 'RODENT MAN' "
            "AND NOT EXISTS (SELECT 1 FROM creature_dictionary cd "
            "WHERE cd.world_id = h.world_id AND cd.creature_id = h.race "
            "AND (cd.flags @> '{\"occurs_as_entity_race\": true}'::jsonb "
            "OR cd.flags @> '{\"has_any_feature_beast\": true}'::jsonb "
            "OR cd.flags @> '{\"has_any_titan\": true}'::jsonb "
            "OR cd.flags @> '{\"has_any_unique_demon\": true}'::jsonb "
            "OR cd.flags @> '{\"has_any_night_creature\": true}'::jsonb))",
            [],
        )

    # Direct race token match (e.g. "DWARF", "ELF")
    return f"AND h.race = ${param_idx}", [rc]


@router.get("/people/browse")
async def browse_people(
    request: Request,
    world_id: int = Query(None),
    limit: int = Query(100, ge=1, le=500),
    flags: str = Query(None),
    race_category: str = Query(None),
    race_categories: str = Query(None),
    alive: str = Query(None),
    variant_flags: str = Query(None),
):
    """Return top historical figures by prominence score for default tab view.

    race_category: single race key (legacy, still supported)
    race_categories: comma-separated race keys (multi-select)
    alive: "alive", "dead", or None (all)
    variant_flags: comma-separated variant keys (vampire,necromancer,werebeast,ghost,animated_dead)
    """
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        world_id = await _resolve_world_id(conn, world_id)
        if not world_id:
            return []

        extra_clauses = []
        params = [world_id, limit]
        next_idx = 3  # $1=world_id, $2=limit

        # Alive/dead filter
        if alive == "alive":
            extra_clauses.append("AND h.death_year IS NULL")
        elif alive == "dead":
            extra_clauses.append("AND h.death_year IS NOT NULL")

        # Multi-select race categories (new)
        cats_to_filter = []
        if race_categories:
            cats_to_filter = [c.strip() for c in race_categories.split(",") if c.strip()]
        elif race_category:
            cats_to_filter = [race_category]

        if cats_to_filter:
            race_parts = []
            for cat in cats_to_filter:
                rc_clause, rc_params = _build_race_category_clause(cat, next_idx)
                if rc_clause:
                    race_parts.append(rc_clause.lstrip("AND "))
                    params.extend(rc_params)
                    next_idx += len(rc_params)
            if race_parts:
                extra_clauses.append("AND (" + " OR ".join(race_parts) + ")")

        # Legacy flag filter (backwards compat)
        if flags and not race_category:
            flag_map = {
                "deity": "is_deity", "force": "is_force",
                "vampire": "is_vampire", "necromancer": "is_necromancer",
                "werebeast": "is_werebeast", "ghost": "is_ghost",
            }
            active = [f.strip() for f in flags.split(",") if f.strip() in flag_map]
            if active:
                conditions = [f"h.{flag_map[f]} = TRUE" for f in active]
                extra_clauses.append("AND (" + " OR ".join(conditions) + ")")

        # Variant flag filter (vampire, necromancer, etc.)
        vf_clause = _build_variant_clause(variant_flags)
        if vf_clause:
            extra_clauses.append(vf_clause)

        where_extra = " ".join(extra_clauses)

        rows = await conn.fetch(
            f"""
            SELECT h.id, h.world_id, h.name, h.race, h.caste, h.death_year,
                   h.is_deity, h.is_force, h.is_vampire,
                   h.is_necromancer, h.is_werebeast, h.is_ghost,
                   h.prominence_score,
                   cd.name_singular AS race_name
            FROM historical_figures h
            LEFT JOIN creature_dictionary cd
                   ON cd.world_id = h.world_id AND cd.creature_id = h.race
            WHERE h.world_id = $1 AND h.name IS NOT NULL AND h.name != ''
            {where_extra}
            ORDER BY h.prominence_score DESC NULLS LAST, h.id
            LIMIT $2
            """,
            *params,
        )
        results = []
        for r in rows:
            row = dict(r)
            results.append({
                "source": "hf", "id": row["id"], "world_id": row["world_id"],
                "name": row["name"], "english_name": None,
                "race": row["race"],
                "race_display": _race_display_name(row["race"], row.get("race_name")),
                "is_alive": row["death_year"] is None,
                "profession": None, "type_flags": _type_flags(row),
            })
        return results


# ---------------------------------------------------------------------------
# 1c. Race summary (dynamic race categories with counts)
# ---------------------------------------------------------------------------

@router.get("/people/race-summary")
async def race_summary(
    request: Request,
    world_id: int = Query(None),
):
    """Return dynamically categorized race groups with HF counts.

    Categories are derived from creature_dictionary flags, not hardcoded.
    Deity alive→Demigod, dead→Gods. Animal people collapsed. Modded races
    auto-appear via occurs_as_entity_race flag.
    """
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        world_id = await _resolve_world_id(conn, world_id)
        if not world_id:
            return {"races": [], "total": 0}

        # Get creature_dictionary for classification
        cd_rows = await conn.fetch(
            "SELECT creature_id, name_singular, name_plural, flags "
            "FROM creature_dictionary WHERE world_id = $1",
            world_id,
        )
        cd_map = {}
        for r in cd_rows:
            raw_flags = r["flags"]
            flags = raw_flags if isinstance(raw_flags, dict) else json.loads(raw_flags or "{}")
            cd_map[r["creature_id"]] = {
                "name_singular": r["name_singular"],
                "name_plural": r["name_plural"],
                "flags": flags,
            }

        # Get all HF race/deity/death data in one query
        hf_rows = await conn.fetch(
            "SELECT race, is_deity, death_year "
            "FROM historical_figures "
            "WHERE world_id = $1 AND name IS NOT NULL AND name != ''",
            world_id,
        )

        # Categorize each HF
        category_counts: dict[str, int] = {}
        category_labels: dict[str, str] = {}
        for r in hf_rows:
            race = r["race"] or ""
            is_deity = r["is_deity"]
            death_year = r["death_year"]
            cd_entry = cd_map.get(race, {})
            cd_flags = cd_entry.get("flags", {})
            name_s = cd_entry.get("name_singular", race.lower().replace("_", " "))

            # Priority-ordered categorization
            # Creature-type flags first (beasts/titans/demons have is_deity=True
            # in DF data but should be categorized by creature type, not deity)
            if cd_flags.get("has_any_feature_beast"):
                key, label = "_forgotten_beast", "Forgotten Beast"
            elif cd_flags.get("has_any_titan"):
                key, label = "_titan", "Titan"
            elif cd_flags.get("has_any_unique_demon"):
                key, label = "_demon", "Demon"
            elif cd_flags.get("has_any_night_creature"):
                key, label = "_night_creature", "Night Creature"
            elif is_deity and death_year is None:
                key, label = "_demigod", "Demigod"
            elif is_deity and death_year is not None:
                key, label = "_gods", "Gods"
            elif race.startswith("HFEXP"):
                key, label = "_animated_dead", "Animated Dead"
            elif _is_animal_person(race):
                key, label = "_animal_people", "Animal People"
            elif cd_flags.get("occurs_as_entity_race") and not _is_animal_person(race):
                key = race
                label = name_s.title() if name_s else race.title()
            else:
                # Remaining creatures (wild animals, megabeasts, etc.)
                key, label = "_other", "Other"

            category_counts[key] = category_counts.get(key, 0) + 1
            category_labels[key] = label

        # Build sorted result
        races = [
            {"key": k, "label": category_labels[k], "count": v}
            for k, v in category_counts.items()
        ]
        races.sort(key=lambda x: x["count"], reverse=True)

        return {"races": races, "total": sum(r["count"] for r in races)}


# ---------------------------------------------------------------------------
# 1d. Biological variants summary (vampire/necromancer/werebeast/ghost/etc.)
# ---------------------------------------------------------------------------

@router.get("/people/variants-summary")
async def variants_summary(
    request: Request,
    world_id: int = Query(None),
    race_category: str = Query(None),
    race_categories: str = Query(None),
):
    """Return biological variant counts, optionally filtered by race category.

    Variants: vampire, necromancer, werebeast, ghost, animated dead.
    race_category: single race key (legacy)
    race_categories: comma-separated race keys (multi-select)
    """
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        world_id = await _resolve_world_id(conn, world_id)
        if not world_id:
            return {"variants": []}

        # Build optional race filter (multi-select or legacy single)
        params = [world_id]
        next_idx = 2
        rc_clause = ""
        cats_to_filter = []
        if race_categories:
            cats_to_filter = [c.strip() for c in race_categories.split(",") if c.strip()]
        elif race_category:
            cats_to_filter = [race_category]

        if cats_to_filter:
            race_parts = []
            for cat in cats_to_filter:
                clause, rc_params = _build_race_category_clause(cat, next_idx)
                if clause:
                    race_parts.append(clause.lstrip("AND "))
                    params.extend(rc_params)
                    next_idx += len(rc_params)
            if race_parts:
                rc_clause = "AND (" + " OR ".join(race_parts) + ")"

        # Count each variant type
        variant_defs = [
            ("vampire", "Vampire", "h.is_vampire = TRUE", "#ef4444"),
            ("necromancer", "Necromancer", "h.is_necromancer = TRUE", "#a855f7"),
            ("werebeast", "Werebeast", "h.is_werebeast = TRUE", "#f97316"),
            ("ghost", "Ghost", "h.is_ghost = TRUE", "#94a3b8"),
            ("animated_dead", "Animated Dead", "h.race LIKE 'HFEXP%'", "#6b7280"),
        ]

        variants = []
        for key, label, condition, color in variant_defs:
            count = await conn.fetchval(
                f"SELECT COUNT(*) FROM historical_figures h "
                f"WHERE h.world_id = $1 AND h.name IS NOT NULL AND h.name != '' "
                f"AND {condition} {rc_clause}",
                *params,
            )
            variants.append({
                "key": key, "label": label,
                "count": count, "color": color,
            })

        return {"variants": variants}


# ---------------------------------------------------------------------------
# 2. HF detail
# ---------------------------------------------------------------------------

@router.get("/people/hf/{world_id}/{hf_id}")
async def get_historical_figure(request: Request, world_id: int, hf_id: int):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        current_year = await conn.fetchval(
            "SELECT game_year FROM sync_snapshots WHERE world_id = $1 "
            "ORDER BY synced_at DESC LIMIT 1", world_id,
        )

        hf = await conn.fetchrow(
            """
            SELECT h.*, e.name AS entity_name,
                   cd.name_singular AS race_name
            FROM historical_figures h
            LEFT JOIN entities e ON e.world_id = h.world_id AND e.id = h.entity_id
            LEFT JOIN creature_dictionary cd
                   ON cd.world_id = h.world_id AND cd.creature_id = h.race
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
        "race": hf["race"],
        "race_display": _race_display_name(hf["race"], hf.get("race_name")),
        "caste": hf["caste"],
        "birth_year": hf["birth_year"], "death_year": hf["death_year"],
        "death_cause": hf["death_cause"],
        "kill_count": hf["kill_count"], "event_count": hf["event_count"],
        "type_flags": _type_flags(hf),
        "entity_id": hf["entity_id"], "entity_name": hf["entity_name"],
        "current_game_year": current_year,
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

        current_year = await conn.fetchval(
            "SELECT game_year FROM sync_snapshots WHERE world_id = $1 "
            "ORDER BY synced_at DESC LIMIT 1", row["world_id"],
        )

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

        # Resolve relationship HF IDs to names
        relationships = details.get("relationships", {})
        resolved_relationships = []
        if relationships:
            rel_ids = [v for v in relationships.values()
                       if isinstance(v, int) and v >= 0]
            name_map = {}
            if rel_ids:
                hf_names = await conn.fetch(
                    "SELECT id, name FROM historical_figures "
                    "WHERE world_id = $1 AND id = ANY($2::int[])",
                    row["world_id"], rel_ids,
                )
                name_map = {r["id"]: r["name"] for r in hf_names}
            for rel_type, hf_id in relationships.items():
                if isinstance(hf_id, int) and hf_id >= 0:
                    resolved_relationships.append({
                        "type": rel_type, "hf_id": hf_id,
                        "name": name_map.get(hf_id),
                    })

    personality = details.get("personality", {})

    return {
        "id": row["id"], "world_id": row["world_id"],
        "name": row["name"], "english_name": row["english_name"],
        "race": row["race"], "caste": row["caste"],
        "profession": row["profession"],
        "pos_x": row["pos_x"], "pos_y": row["pos_y"], "pos_z": row["pos_z"],
        "is_alive": row["is_alive"],
        "hist_fig_id": row["hist_fig_id"], "civ_id": row["civ_id"],
        "civ_name": row["civ_name"],
        "current_game_year": current_year,
        "birth_year": row.get("birth_year"),
        "sex": row.get("sex"),
        "death_cause": row.get("death_cause"),
        "old_year": details.get("old_year"),
        "cultural_identity": details.get("cultural_identity"),
        "relationships": resolved_relationships,
        "personality": {
            "traits": personality.get("traits", {}),
            "values": personality.get("values", []),
            "needs": personality.get("needs", []),
            "dreams": personality.get("dreams", []),
        } if personality else None,
        "physical_attrs": personality.get("physical_attrs", {}),
        "mental_attrs": personality.get("mental_attrs", {}),
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
