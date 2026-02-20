"""CDM context retriever — queries the database for relevant storytelling context."""

import asyncpg


async def retrieve_context(
    pool: asyncpg.Pool,
    world_id: int,
    query: str,
) -> list[dict]:
    """Search CDM tables for records relevant to the user's question.

    Strategy: extract keywords from query, search names via ILIKE,
    pull related events for matched entities. Falls back to world
    overview if no specific matches found.
    """
    keywords = _extract_keywords(query)
    results: list[dict] = []

    async with pool.acquire() as conn:
        # Search historical figures by name
        for kw in keywords:
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

                # Pull related events (most recent first)
                events = await conn.fetch(
                    """
                    SELECT year, event_type, details
                    FROM history_events
                    WHERE world_id = $1 AND (hf_id_1 = $2 OR hf_id_2 = $2)
                    ORDER BY year DESC
                    LIMIT 10
                    """,
                    world_id, hf["id"],
                )
                for ev in events:
                    results.append({
                        "category": "Event",
                        "text": f"Year {ev['year']}: {ev['event_type']} — {_summarize_details(ev['details'])}",
                    })

        # Search entities by name/type
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
        for kw in keywords:
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

        # Search event collections (wars, battles) by name
        for kw in keywords:
            pattern = f"%{kw}%"
            colls = await conn.fetch(
                """
                SELECT name, type, start_year, end_year,
                       attacker_entity_id, defender_entity_id
                FROM history_event_collections
                WHERE world_id = $1 AND name ILIKE $2
                LIMIT 5
                """,
                world_id, pattern,
            )
            for c in colls:
                years = f"year {c['start_year']}"
                if c["end_year"] and c["end_year"] != c["start_year"]:
                    years += f"–{c['end_year']}"
                text = f"{c['name'] or '(unnamed)'} ({c['type']}, {years})"
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
    return unique


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

    # Major wars
    wars = await conn.fetch(
        """
        SELECT name, start_year, end_year
        FROM history_event_collections
        WHERE world_id = $1 AND type = 'war' AND name IS NOT NULL
        ORDER BY start_year DESC
        LIMIT 5
        """,
        world_id,
    )
    for w in wars:
        years = f"year {w['start_year']}"
        if w["end_year"] and w["end_year"] != w["start_year"]:
            years += f"–{w['end_year']}"
        results.append({
            "category": "War",
            "text": f"{w['name']} ({years})",
        })

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


def _extract_keywords(query: str) -> list[str]:
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
