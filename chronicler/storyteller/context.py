"""CDM context retriever — queries the database for relevant storytelling context.

Supports two data tiers:
1. Legends (historical): imported from XML exports — HFs, events, sites, entities
2. Live (current): polled from in-game memory via bridge — units, reports, emotions, squads
"""

import json
import asyncpg

# Categorical routing: maps conceptual keywords to structured queries.
# Without this, asking "tell me about deities" searches for name ILIKE '%deities%'
# which finds nothing — deities are identified by is_deity=TRUE, not by name.
_CATEGORY_ROUTES: dict[str, tuple[str, object]] = {
    # HF boolean flags
    "deity": ("hf_flag", "is_deity"),
    "deities": ("hf_flag", "is_deity"),
    "god": ("hf_flag", "is_deity"),
    "gods": ("hf_flag", "is_deity"),
    "divine": ("hf_flag", "is_deity"),
    "vampire": ("hf_flag", "is_vampire"),
    "vampires": ("hf_flag", "is_vampire"),
    "necromancer": ("hf_flag", "is_necromancer"),
    "necromancers": ("hf_flag", "is_necromancer"),
    "werebeast": ("hf_flag", "is_werebeast"),
    "werebeasts": ("hf_flag", "is_werebeast"),
    "ghost": ("hf_flag", "is_ghost"),
    "ghosts": ("hf_flag", "is_ghost"),
    # HF race patterns (DF canonical megabeasts, forgotten beasts, titans)
    "megabeast": ("hf_race", ("DRAGON", "HYDRA", "COLOSSUS%", "ROC_%", "CYCLOPS", "ETTIN")),
    "megabeasts": ("hf_race", ("DRAGON", "HYDRA", "COLOSSUS%", "ROC_%", "CYCLOPS", "ETTIN")),
    "dragon": ("hf_race", ("DRAGON", "CAVE_DRAGON")),
    "dragons": ("hf_race", ("DRAGON", "CAVE_DRAGON")),
    "forgotten": ("hf_race", ("FORGOTTEN_BEAST%",)),
    "beasts": ("hf_race", ("FORGOTTEN_BEAST%",)),
    "titan": ("hf_race", ("TITAN%",)),
    "titans": ("hf_race", ("TITAN%",)),
    # Entity types
    "religion": ("entity_type", "religion"),
    "religions": ("entity_type", "religion"),
    "civilization": ("entity_type", "civilization"),
    "civilizations": ("entity_type", "civilization"),
    "kingdom": ("entity_type", "civilization"),
    "kingdoms": ("entity_type", "civilization"),
    "empire": ("entity_type", "civilization"),
    "empires": ("entity_type", "civilization"),
    # Event collection types
    "war": ("collection_type", "war"),
    "wars": ("collection_type", "war"),
    "battle": ("collection_type", "battle"),
    "battles": ("collection_type", "battle"),
    # Artifact searches
    "artifact": ("artifacts", None),
    "artifacts": ("artifacts", None),
    "relic": ("artifacts", None),
    "relics": ("artifacts", None),
    # Written content searches
    "book": ("written_contents", None),
    "books": ("written_contents", None),
    "poem": ("written_contents", None),
    "poems": ("written_contents", None),
    "scroll": ("written_contents", None),
    "scrolls": ("written_contents", None),
    "composition": ("written_contents", None),
    "music": ("written_contents", None),
    "literature": ("written_contents", None),
    "writing": ("written_contents", None),
    "writings": ("written_contents", None),
    # v6: Fortress/live data routes
    "fortress": ("live_units", None),
    "dwarves": ("live_units", None),
    "inhabitants": ("live_units", None),
    "population": ("live_units", None),
    "stress": ("live_units", None),
    "mood": ("live_units", None),
    "moody": ("live_units", None),
    "tantrum": ("live_units", None),
    "squad": ("live_squads", None),
    "squads": ("live_squads", None),
    "military": ("live_squads", None),
    "army": ("live_armies", None),
    "armies": ("live_armies", None),
    "siege": ("live_armies", None),
    "recent": ("live_events", None),
    "today": ("live_events", None),
    "happened": ("live_events", None),
    "news": ("live_events", None),
    "announcement": ("live_reports", None),
    "announcements": ("live_reports", None),
    "report": ("live_reports", None),
    "reports": ("live_reports", None),
}

# Allowed column names for hf_flag queries (prevents SQL injection)
_VALID_HF_FLAGS = {"is_deity", "is_force", "is_vampire", "is_necromancer", "is_werebeast", "is_ghost"}


async def retrieve_context(
    pool: asyncpg.Pool,
    world_id: int,
    query: str,
) -> list[dict]:
    """Search CDM tables for records relevant to the user's question.

    Strategy: extract keywords, route categorical terms (e.g. "deity",
    "megabeast") to attribute queries, then search names via ILIKE for
    remaining keywords. Falls back to world overview if nothing matched.
    """
    keywords = extract_keywords(query)
    results: list[dict] = []

    async with pool.acquire() as conn:
        # Phase 1: Categorical routing — match keywords to structured queries
        name_keywords = []  # keywords that didn't match a category
        seen_routes = set()  # avoid duplicate category queries
        for kw in keywords:
            route = _CATEGORY_ROUTES.get(kw)
            if route and route not in seen_routes:
                seen_routes.add(route)
                cat_results = await _run_category_query(conn, world_id, route)
                results.extend(cat_results)
            else:
                name_keywords.append(kw)

        # Phase 2: Name-based ILIKE search for remaining keywords
        for kw in name_keywords:
            pattern = f"%{kw}%"
            hfs = await conn.fetch(
                """
                SELECT id, name, race, caste, birth_year, death_year,
                       death_cause, is_deity, is_force, is_vampire,
                       is_necromancer, is_werebeast, kill_count, entity_id
                FROM historical_figures
                WHERE world_id = $1 AND name ILIKE $2
                LIMIT 5
                """,
                world_id, pattern,
            )
            for hf in hfs:
                text = _format_hf(hf)
                results.append({"category": "Historical Figure", "text": text})

                # Pull related events with name resolution
                events = await conn.fetch(
                    """
                    SELECT e.year, e.event_type, e.details,
                           h1.name as hf1_name, h2.name as hf2_name,
                           s.name as site_name
                    FROM history_events e
                    LEFT JOIN historical_figures h1 ON h1.world_id = e.world_id AND h1.id = e.hf_id_1
                    LEFT JOIN historical_figures h2 ON h2.world_id = e.world_id AND h2.id = e.hf_id_2
                    LEFT JOIN sites s ON s.world_id = e.world_id AND s.id = e.site_id
                    WHERE e.world_id = $1 AND (e.hf_id_1 = $2 OR e.hf_id_2 = $2)
                    ORDER BY e.year DESC
                    LIMIT 10
                    """,
                    world_id, hf["id"],
                )
                for ev in events:
                    text = _format_event(ev)
                    results.append({"category": "Event", "text": text})

                # Cross-reference: check if this HF is alive in fortress
                alive = await conn.fetchrow(
                    """
                    SELECT id, name, profession, is_alive
                    FROM units
                    WHERE world_id = $1 AND hist_fig_id = $2
                    """,
                    world_id, hf["id"],
                )
                if alive and alive["is_alive"]:
                    results.append({
                        "category": "Live Status",
                        "text": f"{hf['name']} is currently alive in the fortress as {alive['profession'] or 'unknown profession'}",
                    })

                # Cross-reference: family/relationships via hf_links
                links = await conn.fetch(
                    """
                    SELECT hl.link_type, hl.target_hf_id, hf2.name as target_name
                    FROM hf_links hl
                    JOIN historical_figures hf2 ON hf2.world_id = hl.world_id AND hf2.id = hl.target_hf_id
                    WHERE hl.world_id = $1 AND hl.hf_id = $2
                    LIMIT 10
                    """,
                    world_id, hf["id"],
                )
                for link in links:
                    results.append({
                        "category": "Relationship",
                        "text": f"{hf['name']} — {link['link_type']} — {link['target_name'] or '(unknown)'}",
                    })

                # Cross-reference: entity memberships via hf_entity_links
                elinks = await conn.fetch(
                    """
                    SELECT hel.link_type, hel.position_name, e.name as entity_name
                    FROM hf_entity_links hel
                    LEFT JOIN entities e ON e.world_id = hel.world_id AND e.id = hel.entity_id
                    WHERE hel.world_id = $1 AND hel.hf_id = $2
                    LIMIT 5
                    """,
                    world_id, hf["id"],
                )
                for el in elinks:
                    pos = f" as {el['position_name']}" if el["position_name"] else ""
                    results.append({
                        "category": "Membership",
                        "text": f"{hf['name']} — {el['link_type']}{pos} of {el['entity_name'] or '(unknown entity)'}",
                    })

                # Cross-reference: associated sites via hf_site_links
                slinks = await conn.fetch(
                    """
                    SELECT hsl.link_type, s.name as site_name, s.type as site_type
                    FROM hf_site_links hsl
                    LEFT JOIN sites s ON s.world_id = hsl.world_id AND s.id = hsl.site_id
                    WHERE hsl.world_id = $1 AND hsl.hf_id = $2
                    LIMIT 5
                    """,
                    world_id, hf["id"],
                )
                for sl in slinks:
                    results.append({
                        "category": "Site Link",
                        "text": f"{hf['name']} — {sl['link_type']} at {sl['site_name'] or '(unknown site)'} ({sl['site_type'] or 'unknown type'})",
                    })

        # Search entities by name/type (use all keywords, not just name_keywords,
        # since entity type ILIKE catches category terms too)
        for kw in keywords:
            pattern = f"%{kw}%"
            ents = await conn.fetch(
                """
                SELECT id, name, type, race
                FROM entities
                WHERE world_id = $1 AND (name ILIKE $2 OR type ILIKE $2)
                LIMIT 5
                """,
                world_id, pattern,
            )
            for ent in ents:
                text = f"{ent['name'] or '(unnamed)'} — {ent['type'] or 'unknown type'}"
                if ent["race"]:
                    text += f" ({ent['race']})"
                results.append({"category": "Entity", "text": text})

        # Search sites by name
        for kw in name_keywords:
            pattern = f"%{kw}%"
            sites = await conn.fetch(
                """
                SELECT id, name, type, owner_entity_id
                FROM sites
                WHERE world_id = $1 AND name ILIKE $2
                LIMIT 5
                """,
                world_id, pattern,
            )
            for site in sites:
                text = f"{site['name']} — {site['type'] or 'unknown'}"
                results.append({"category": "Site", "text": text})

        # Search event collections (wars, battles) by name with entity resolution
        for kw in name_keywords:
            pattern = f"%{kw}%"
            colls = await conn.fetch(
                """
                SELECT hec.name, hec.type, hec.start_year, hec.end_year,
                       att.name as attacker_name, def.name as defender_name
                FROM history_event_collections hec
                LEFT JOIN entities att ON att.world_id = hec.world_id AND att.id = hec.attacker_entity_id
                LEFT JOIN entities def ON def.world_id = hec.world_id AND def.id = hec.defender_entity_id
                WHERE hec.world_id = $1 AND hec.name ILIKE $2
                LIMIT 5
                """,
                world_id, pattern,
            )
            for c in colls:
                years = f"year {c['start_year']}"
                if c["end_year"] and c["end_year"] != c["start_year"]:
                    years += f"–{c['end_year']}"
                text = f"{c['name'] or '(unnamed)'} ({c['type']}, {years})"
                if c["attacker_name"] or c["defender_name"]:
                    text += f" — {c['attacker_name'] or '?'} vs {c['defender_name'] or '?'}"
                results.append({"category": "Event Collection", "text": text})

        # Fallback: world overview if nothing matched
        if not results:
            results = await _world_overview(conn, world_id)

    # Deduplicate by text
    seen = set()
    unique = []
    for r in results:
        if r["text"] not in seen:
            seen.add(r["text"])
            unique.append(r)

    # Confidence signaling — prepend context density indicator
    if len(unique) < 3:
        unique.insert(0, {
            "category": "Context Note",
            "text": "Context is limited — be cautious about specific details not directly supported by the data below.",
        })
    elif len(unique) > 10:
        unique.insert(0, {
            "category": "Context Note",
            "text": "Rich context available — multiple data sources matched this query.",
        })

    return unique


async def _run_category_query(
    conn: asyncpg.Connection,
    world_id: int,
    route: tuple[str, object],
) -> list[dict]:
    """Execute a categorical query based on the route type."""
    query_type, param = route
    results: list[dict] = []

    if query_type == "hf_flag" and param in _VALID_HF_FLAGS:
        # Query HFs by boolean flag (is_deity, is_vampire, etc.)
        hfs = await conn.fetch(
            f"""
            SELECT id, name, race, caste, birth_year, death_year,
                   death_cause, is_deity, is_force, is_vampire,
                   is_necromancer, is_werebeast, kill_count, entity_id,
                   details
            FROM historical_figures
            WHERE world_id = $1 AND {param} = TRUE
            ORDER BY kill_count DESC NULLS LAST, birth_year ASC
            LIMIT 10
            """,
            world_id,
        )
        for hf in hfs:
            results.append({"category": "Historical Figure", "text": _format_hf(hf)})

    elif query_type == "hf_race":
        # Query HFs by race pattern list (megabeasts, forgotten beasts, etc.)
        race_patterns = param
        conditions = " OR ".join(f"race LIKE ${i+2}" for i in range(len(race_patterns)))
        hfs = await conn.fetch(
            f"""
            SELECT id, name, race, caste, birth_year, death_year,
                   death_cause, is_deity, is_force, is_vampire,
                   is_necromancer, is_werebeast, kill_count, entity_id
            FROM historical_figures
            WHERE world_id = $1 AND ({conditions})
            ORDER BY kill_count DESC NULLS LAST, birth_year ASC
            LIMIT 10
            """,
            world_id, *race_patterns,
        )
        for hf in hfs:
            results.append({"category": "Historical Figure", "text": _format_hf(hf)})

    elif query_type == "entity_type":
        ents = await conn.fetch(
            """
            SELECT id, name, type, race
            FROM entities
            WHERE world_id = $1 AND type = $2
            ORDER BY name
            LIMIT 10
            """,
            world_id, param,
        )
        for ent in ents:
            text = f"{ent['name'] or '(unnamed)'} — {ent['type'] or 'unknown type'}"
            if ent["race"]:
                text += f" ({ent['race']})"
            results.append({"category": "Entity", "text": text})

    elif query_type == "collection_type":
        colls = await conn.fetch(
            """
            SELECT hec.name, hec.type, hec.start_year, hec.end_year,
                   att.name as attacker_name, def.name as defender_name
            FROM history_event_collections hec
            LEFT JOIN entities att ON att.world_id = hec.world_id AND att.id = hec.attacker_entity_id
            LEFT JOIN entities def ON def.world_id = hec.world_id AND def.id = hec.defender_entity_id
            WHERE hec.world_id = $1 AND hec.type = $2 AND hec.name IS NOT NULL
            ORDER BY hec.start_year DESC
            LIMIT 10
            """,
            world_id, param,
        )
        for c in colls:
            years = f"year {c['start_year']}"
            if c["end_year"] and c["end_year"] != c["start_year"]:
                years += f"–{c['end_year']}"
            text = f"{c['name']} ({c['type']}, {years})"
            if c["attacker_name"] or c["defender_name"]:
                att = c["attacker_name"] or "unknown"
                dfn = c["defender_name"] or "unknown"
                text += f" — {att} vs {dfn}"
            results.append({"category": "Event Collection", "text": text})

    elif query_type == "artifacts":
        arts = await conn.fetch(
            """
            SELECT name, item_type, item_subtype, material
            FROM artifacts
            WHERE world_id = $1 AND name IS NOT NULL
            ORDER BY name
            LIMIT 10
            """,
            world_id,
        )
        for a in arts:
            text = a["name"]
            parts = []
            if a["material"]:
                parts.append(a["material"])
            if a["item_type"]:
                parts.append(a["item_type"])
            if a["item_subtype"]:
                parts.append(a["item_subtype"])
            if parts:
                text += f" ({', '.join(parts)})"
            results.append({"category": "Artifact", "text": text})

    elif query_type == "written_contents":
        wcs = await conn.fetch(
            """
            SELECT wc.id, wc.title, wc.form, wc.type, wc.styles,
                   hf.name as author_name
            FROM written_contents wc
            LEFT JOIN historical_figures hf ON hf.world_id = wc.world_id AND hf.id = wc.author_hf_id
            WHERE wc.world_id = $1 AND wc.title IS NOT NULL
            ORDER BY wc.id
            LIMIT 15
            """,
            world_id,
        )
        for wc in wcs:
            form = wc["form"] or wc["type"] or "work"
            text = f'"{wc["title"]}" ({form})'
            if wc["author_name"]:
                text += f" by {wc['author_name']}"
            if wc["styles"]:
                text += f" [{', '.join(wc['styles'][:3])}]"
            results.append({"category": "Written Content", "text": text})

    # v6: Live data routes
    elif query_type == "live_units":
        results.extend(await _retrieve_live_units(conn, world_id))

    elif query_type == "live_squads":
        results.extend(await _retrieve_live_squads(conn, world_id))

    elif query_type == "live_armies":
        results.extend(await _retrieve_live_armies(conn, world_id))

    elif query_type == "live_events":
        results.extend(await _retrieve_live_events(conn, world_id, limit=20))

    elif query_type == "live_reports":
        results.extend(await _retrieve_live_reports(conn, world_id, limit=20))

    return results


async def _build_emotion_map(
    conn: asyncpg.Connection, world_id: int
) -> dict[int, list[dict]]:
    """Build unit_id → sorted emotion list from latest dwarf_emotions probe."""
    probe = await conn.fetchval(
        """
        SELECT data FROM lua_probes
        WHERE world_id = $1 AND probe_name = 'dwarf_emotions'
        ORDER BY captured_at DESC LIMIT 1
        """,
        world_id,
    )
    if not probe:
        return {}
    data = json.loads(probe) if isinstance(probe, str) else probe
    dwarves = data.get("dwarves", [])
    result = {}
    for d in dwarves:
        uid = d.get("id")
        if uid is not None and d.get("emotions"):
            # Sort by strength descending so most intense emotion is first
            sorted_emo = sorted(d["emotions"], key=lambda e: e.get("strength", 0), reverse=True)
            result[uid] = sorted_emo
    return result


async def _build_zone_owner_map(
    conn: asyncpg.Connection, world_id: int
) -> dict[int, str]:
    """Build owner_unit_id → zone name from latest zones probe."""
    probe = await conn.fetchval(
        """
        SELECT data FROM lua_probes
        WHERE world_id = $1 AND probe_name = 'zones'
        ORDER BY captured_at DESC LIMIT 1
        """,
        world_id,
    )
    if not probe:
        return {}
    data = json.loads(probe) if isinstance(probe, str) else probe
    zones = data.get("zones", [])
    result = {}
    for z in zones:
        owner = z.get("owner_unit_id")
        name = z.get("name") or z.get("type") or "unnamed zone"
        if owner and owner > 0:
            result[owner] = name
    return result


async def _retrieve_live_units(
    conn: asyncpg.Connection, world_id: int
) -> list[dict]:
    """Retrieve current fortress inhabitants from units table.

    Enriches unit data with:
    - Historical figure cross-reference (vampires, kill counts, etc.)
    - Latest dwarf emotions from bridge probe
    - Zone assignments from bridge probe
    """
    results: list[dict] = []

    # Pre-fetch emotion and zone data for enrichment
    emotion_map = await _build_emotion_map(conn, world_id)
    zone_owner_map = await _build_zone_owner_map(conn, world_id)

    units = await conn.fetch(
        """
        SELECT u.id, u.name, u.race, u.profession, u.is_alive,
               u.hist_fig_id, u.details
        FROM units u
        WHERE u.world_id = $1 AND u.is_alive = TRUE
        ORDER BY u.name
        LIMIT 30
        """,
        world_id,
    )
    for u in units:
        text = f"{u['name'] or '(unnamed)'} — {u['race']}, {u['profession'] or 'no profession'}"
        details = u.get("details")
        if details:
            if isinstance(details, str):
                details = json.loads(details)
            if isinstance(details, dict):
                stress = details.get("stress")
                if stress is not None and stress > 100000:
                    text += f" [STRESSED: {stress:,}]"
                mood = details.get("mood")
                if mood is not None and mood >= 0:
                    text += f" [MOOD: {mood}]"
        # Emotion enrichment from bridge probe
        emo = emotion_map.get(u["id"])
        if emo:
            top_emotions = emo[:3]  # Show top 3 emotions
            emo_strs = [f"{e['thought']}({e['strength']})" for e in top_emotions if e.get('thought')]
            if emo_strs:
                text += f" [emotions: {', '.join(emo_strs)}]"

        # Zone assignment from bridge probe
        zone_name = zone_owner_map.get(u["id"])
        if zone_name:
            text += f" [zone: {zone_name}]"

        # Cross-reference with historical figure
        if u["hist_fig_id"]:
            hf = await conn.fetchrow(
                """
                SELECT name, birth_year, kill_count, is_deity, is_vampire,
                       is_necromancer, is_werebeast
                FROM historical_figures
                WHERE world_id = $1 AND id = $2
                """,
                world_id, u["hist_fig_id"],
            )
            if hf:
                traits = []
                if hf["is_vampire"]:
                    traits.append("vampire")
                if hf["is_necromancer"]:
                    traits.append("necromancer")
                if hf["is_werebeast"]:
                    traits.append("werebeast")
                if traits:
                    text += f" [{', '.join(traits)}]"
                if hf["kill_count"] and hf["kill_count"] > 0:
                    text += f" [{hf['kill_count']} kills]"
                if hf["birth_year"]:
                    text += f" [born year {hf['birth_year']}]"
        results.append({"category": "Fortress Inhabitant", "text": text})
    return results


async def _retrieve_live_events(
    conn: asyncpg.Connection, world_id: int, limit: int = 20
) -> list[dict]:
    """Retrieve recent unit change events from unit_events table."""
    results: list[dict] = []
    events = await conn.fetch(
        """
        SELECT ue.event_type, ue.old_value, ue.new_value,
               ue.game_year, ue.game_tick, u.name
        FROM unit_events ue
        LEFT JOIN units u ON u.id = ue.unit_id AND u.world_id = ue.world_id
        WHERE ue.world_id = $1
        ORDER BY ue.detected_at DESC
        LIMIT $2
        """,
        world_id, limit,
    )
    for ev in events:
        new_val = ev["new_value"]
        if isinstance(new_val, str):
            new_val = json.loads(new_val)
        name = ev["name"] or (new_val.get("name") if isinstance(new_val, dict) else None) or "(unknown)"
        time_str = f"year {ev['game_year']}" if ev["game_year"] else "unknown time"
        text = f"{ev['event_type']}: {name} ({time_str})"
        if isinstance(new_val, dict):
            detail_parts = []
            for k, v in new_val.items():
                if k not in ("name",) and v is not None:
                    detail_parts.append(f"{k}={v}")
            if detail_parts:
                text += f" — {', '.join(detail_parts[:5])}"
        results.append({"category": "Recent Event", "text": text})
    return results


async def _retrieve_live_reports(
    conn: asyncpg.Connection, world_id: int, limit: int = 20
) -> list[dict]:
    """Retrieve recent game announcements/reports."""
    results: list[dict] = []
    reports = await conn.fetch(
        """
        SELECT text, game_year, game_tick, report_type, is_announcement
        FROM game_reports
        WHERE world_id = $1
        ORDER BY detected_at DESC
        LIMIT $2
        """,
        world_id, limit,
    )
    for r in reports:
        time_str = f"year {r['game_year']}" if r["game_year"] else "unknown time"
        text = f"[{time_str}] {r['text']}"
        results.append({"category": "Game Report", "text": text})
    return results


async def _retrieve_live_squads(
    conn: asyncpg.Connection, world_id: int
) -> list[dict]:
    """Retrieve military squad info from latest lua_probes snapshot."""
    results: list[dict] = []
    probe = await conn.fetchval(
        """
        SELECT data FROM lua_probes
        WHERE world_id = $1 AND probe_name = 'squads'
        ORDER BY captured_at DESC LIMIT 1
        """,
        world_id,
    )
    if probe:
        data = json.loads(probe) if isinstance(probe, str) else probe
        squads = data.get("squads", [])
        for sq in squads:
            name = sq.get("alias") or sq.get("name") or "(unnamed)"
            text = f"Squad: {name} — {sq.get('member_count', 0)}/{sq.get('position_count', 0)} members"
            if sq.get("order_count", 0) > 0:
                text += f", {sq['order_count']} active orders"
            results.append({"category": "Military", "text": text})
    return results


async def _retrieve_live_armies(
    conn: asyncpg.Connection, world_id: int
) -> list[dict]:
    """Retrieve army info from latest lua_probes snapshot."""
    results: list[dict] = []
    probe = await conn.fetchval(
        """
        SELECT data FROM lua_probes
        WHERE world_id = $1 AND probe_name = 'armies'
        ORDER BY captured_at DESC LIMIT 1
        """,
        world_id,
    )
    if probe:
        data = json.loads(probe) if isinstance(probe, str) else probe
        armies = data.get("armies", [])
        if not armies:
            results.append({"category": "Military", "text": "No armies currently in the field."})
        for a in armies:
            text = f"Army #{a.get('id', '?')} — {a.get('member_count', '?')} members at ({a.get('pos_x', '?')}, {a.get('pos_y', '?')})"
            results.append({"category": "Military", "text": text})
    return results


async def _world_overview(conn: asyncpg.Connection, world_id: int) -> list[dict]:
    """Generate a general world overview when no specific matches found."""
    results = []

    # Top civilizations
    civs = await conn.fetch(
        """
        SELECT e.name, e.race, count(s.id) as site_count
        FROM entities e
        LEFT JOIN sites s ON s.owner_entity_id = e.id AND s.world_id = e.world_id
        WHERE e.world_id = $1 AND e.type = 'civilization'
        GROUP BY e.id, e.name, e.race
        ORDER BY site_count DESC
        LIMIT 5
        """,
        world_id,
    )
    for c in civs:
        results.append({
            "category": "Civilization",
            "text": f"{c['name']} ({c['race']}) — controls {c['site_count']} sites",
        })

    # Major wars with entity name resolution
    wars = await conn.fetch(
        """
        SELECT hec.name, hec.start_year, hec.end_year,
               att.name as attacker_name, def.name as defender_name
        FROM history_event_collections hec
        LEFT JOIN entities att ON att.world_id = hec.world_id AND att.id = hec.attacker_entity_id
        LEFT JOIN entities def ON def.world_id = hec.world_id AND def.id = hec.defender_entity_id
        WHERE hec.world_id = $1 AND hec.type = 'war' AND hec.name IS NOT NULL
        ORDER BY hec.start_year DESC
        LIMIT 5
        """,
        world_id,
    )
    for w in wars:
        years = f"year {w['start_year']}"
        if w["end_year"] and w["end_year"] != w["start_year"]:
            years += f"–{w['end_year']}"
        text = f"{w['name']} ({years})"
        if w["attacker_name"] or w["defender_name"]:
            text += f" — {w['attacker_name'] or '?'} vs {w['defender_name'] or '?'}"
        results.append({"category": "War", "text": text})

    # Notable figures (highest kill count)
    legends = await conn.fetch(
        """
        SELECT name, race, kill_count, birth_year, death_year
        FROM historical_figures
        WHERE world_id = $1 AND kill_count > 0
        ORDER BY kill_count DESC
        LIMIT 5
        """,
        world_id,
    )
    for l in legends:
        lifespan = f"born {l['birth_year']}"
        if l["death_year"] and l["death_year"] != -1:
            lifespan += f", died {l['death_year']}"
        results.append({
            "category": "Legend",
            "text": f"{l['name']} ({l['race']}) — {l['kill_count']} kills, {lifespan}",
        })

    return results


def extract_keywords(query: str) -> list[str]:
    """Extract meaningful search keywords from a user query.

    Filters out common stop words and short tokens.
    """
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "need", "dare", "ought",
        "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
        "as", "into", "through", "during", "before", "after", "above", "below",
        "between", "out", "off", "over", "under", "again", "further", "then",
        "once", "here", "there", "when", "where", "why", "how", "all", "each",
        "every", "both", "few", "more", "most", "other", "some", "such", "no",
        "nor", "not", "only", "own", "same", "so", "than", "too", "very",
        "just", "because", "but", "and", "or", "if", "while", "about", "up",
        "what", "which", "who", "whom", "this", "that", "these", "those",
        "am", "i", "me", "my", "myself", "we", "our", "ours", "ourselves",
        "you", "your", "yours", "yourself", "he", "him", "his", "himself",
        "she", "her", "hers", "herself", "it", "its", "itself", "they",
        "them", "their", "theirs", "themselves", "tell", "know", "about",
        "describe", "explain", "show", "give", "find", "look", "search",
        "dwarf", "fortress", "world", "history",
    }
    words = query.lower().split()
    keywords = [w.strip(".,!?;:'\"()") for w in words]
    keywords = [w for w in keywords if len(w) >= 3 and w not in stop_words]
    return keywords[:5]  # Limit to 5 keywords to avoid query explosion


def _format_hf(hf: asyncpg.Record) -> str:
    """Format a historical figure record into readable text."""
    parts = [hf["name"] or "(unnamed)"]
    if hf["race"]:
        parts.append(f"({hf['race']}")
        if hf["caste"]:
            parts[-1] += f" {hf['caste']}"
        parts[-1] += ")"

    traits = []
    if hf["is_deity"]:
        traits.append("deity")
    if hf["is_force"]:
        traits.append("force of nature")
    if hf["is_vampire"]:
        traits.append("vampire")
    if hf["is_necromancer"]:
        traits.append("necromancer")
    if hf["is_werebeast"]:
        traits.append("werebeast")
    if traits:
        parts.append(f"[{', '.join(traits)}]")

    # Include spheres from details JSONB (e.g., deity spheres like "fire", "war")
    details = hf.get("details")
    if details:
        if isinstance(details, str):
            try:
                details = json.loads(details)
            except (json.JSONDecodeError, TypeError):
                details = None
        if isinstance(details, dict) and "spheres" in details:
            parts.append(f"spheres: {', '.join(details['spheres'])}")

    if hf["birth_year"] is not None and hf["birth_year"] != -1:
        parts.append(f"born year {hf['birth_year']}")
    if hf["death_year"] is not None and hf["death_year"] != -1:
        death = f"died year {hf['death_year']}"
        if hf["death_cause"]:
            death += f" ({hf['death_cause']})"
        parts.append(death)
    if hf["kill_count"] and hf["kill_count"] > 0:
        parts.append(f"{hf['kill_count']} kills")

    return " — ".join(parts[:2]) + (", " + ", ".join(parts[2:]) if len(parts) > 2 else "")


def _format_event(ev: dict) -> str:
    """Format a history event with resolved names into readable text."""
    parts = [f"Year {ev['year']}"]
    etype = ev["event_type"] or "unknown event"

    # Build natural-language description based on event type
    hf1 = ev.get("hf1_name")
    hf2 = ev.get("hf2_name")
    site = ev.get("site_name")

    if etype == "hf died" and hf1:
        desc = f"{hf1} died"
        if hf2:
            desc += f", slain by {hf2}"
        if site:
            desc += f" at {site}"
    elif etype == "hf simple battle event" and hf1 and hf2:
        desc = f"{hf1} fought {hf2}"
        if site:
            desc += f" at {site}"
    elif etype == "add hf entity link" and hf1:
        desc = f"{hf1} joined an entity"
        if site:
            desc += f" at {site}"
    elif etype == "change hf state" and hf1:
        desc = f"{hf1} changed state"
        if site:
            desc += f" at {site}"
    elif etype == "created site" and hf1 and site:
        desc = f"{hf1} created {site}"
    elif etype == "artifact created" and hf1:
        desc = f"{hf1} created an artifact"
        if site:
            desc += f" at {site}"
    else:
        # Generic fallback with name substitution
        actors = []
        if hf1:
            actors.append(hf1)
        if hf2:
            actors.append(hf2)
        desc = etype
        if actors:
            desc += f" involving {' and '.join(actors)}"
        if site:
            desc += f" at {site}"

    parts.append(desc)
    extra = _summarize_details(ev["details"])
    if extra and extra != "(no details)":
        parts.append(extra)
    return ": ".join(parts[:2]) + (f" — {parts[2]}" if len(parts) > 2 else "")


def _summarize_details(details) -> str:
    """Summarize a JSONB details field into brief human-readable text."""
    if not details:
        return "(no details)"
    if isinstance(details, str):
        import json
        try:
            details = json.loads(details)
        except (json.JSONDecodeError, TypeError):
            return details[:100]
    if not isinstance(details, dict):
        return str(details)[:100]
    # Pick the most informative fields
    interesting = ["reason", "cause", "slayer_hf", "artifact", "circumstance",
                   "interaction", "knowledge", "skill", "method"]
    parts = []
    for key in interesting:
        if key in details and details[key]:
            parts.append(f"{key}: {details[key]}")
    if not parts:
        # Fallback: show first 3 keys
        for k, v in list(details.items())[:3]:
            if v is not None:
                parts.append(f"{k}: {v}")
    return ", ".join(parts) if parts else "(details available)"
