"""Stage 3.6: LLM-powered narrative generation.

Uses Qwen3 8B via Ollama direct (localhost:11434) for:
  3.6.3b: Arc title generation
  3.6.4:  Hierarchical event summaries
  3.6.6:  Character narrative profiles
  3.6.8:  Event cluster summaries

Key rule: think=false at payload ROOT (not inside options).
Use Ollama direct for latency (~0.25s vs ~13.7s via LiteLLM).
"""

import json
import logging

import httpx

log = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434"
MODEL = "qwen3:8b"


async def _generate(prompt: str, system: str = "", max_tokens: int = 256,
                    temperature: float = 0.7) -> str:
    """Call Ollama direct for non-streaming generation.

    Returns the generated text. Empty string on failure.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "think": False,  # MUST be at root, not in options
        "options": {
            "num_predict": max_tokens,
            "temperature": temperature,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "").strip()
    except Exception as e:
        log.warning("Ollama generation failed: %s", e)
        return ""


# ═══════════════════════════════════════════════════════════════════════
# 3.6.3b: Arc Title Generation
# ═══════════════════════════════════════════════════════════════════════

SYSTEM_ARC_TITLE = (
    "You are a fantasy historian naming chapters of a chronicle. "
    "Generate a short, evocative title (5-10 words) for the story arc described. "
    "Use dramatic fantasy language. No quotes or punctuation besides the title."
)


async def generate_arc_titles(conn, world_id: int) -> int:
    """Generate titles for arcs that don't have one yet."""
    arcs = await conn.fetch("""
        SELECT na.id, na.arc_type, na.start_tick / 403200 AS start_year,
               na.end_tick / 403200 AS end_year, na.resolution,
               na.dramatic_weight, jsonb_array_length(na.key_events) AS event_count
        FROM narrative_arcs na
        WHERE na.world_id = $1 AND (na.title IS NULL OR na.title = '')
        ORDER BY na.dramatic_weight DESC
        LIMIT 100
    """, world_id)

    if not arcs:
        log.info("Arc titles: no untitled arcs")
        return 0

    count = 0
    for arc in arcs:
        prompt = (
            f"Arc type: {arc['arc_type'].replace('_', ' ')}\n"
            f"Time period: Year {arc['start_year']} to Year {arc['end_year']}\n"
            f"Events: {arc['event_count']} key events\n"
            f"Resolution: {arc['resolution'] or 'ongoing'}\n"
            f"Dramatic weight: {arc['dramatic_weight']:.1f}/100\n\n"
            f"Generate a chapter title:"
        )

        title = await _generate(prompt, system=SYSTEM_ARC_TITLE, max_tokens=30)
        if title:
            # Clean: remove quotes, trailing periods
            title = title.strip('"\'').rstrip(".")
            await conn.execute(
                "UPDATE narrative_arcs SET title = $1 WHERE id = $2",
                title, arc["id"],
            )
            count += 1
            if count <= 5:
                log.info("  Arc %d: '%s' (%s)", arc["id"], title, arc["arc_type"])

    log.info("Arc titles: %d generated", count)
    return count


# ═══════════════════════════════════════════════════════════════════════
# 3.6.4: Hierarchical Event Summaries
# ═══════════════════════════════════════════════════════════════════════

SYSTEM_SUMMARY = (
    "You are a fantasy historian writing a chronicle. Summarize the events "
    "described in 2-4 sentences of dramatic prose. Focus on the most impactful "
    "events. Write in past tense, third person, formal chronicle style."
)


async def generate_year_summaries(conn, world_id: int, force: bool = False) -> int:
    """Generate year-level summaries from top-scored events per year."""
    if force:
        await conn.execute(
            "DELETE FROM event_summaries WHERE world_id = $1 AND granularity = 'year'",
            world_id,
        )

    # Get years with scored events, excluding already-summarized
    years = await conn.fetch("""
        SELECT DISTINCT he.year
        FROM history_events he
        JOIN narrative_events ne ON ne.world_id = he.world_id AND ne.event_id = he.id
        WHERE he.world_id = $1 AND ne.narrative_weight >= 5
        AND NOT EXISTS (
            SELECT 1 FROM event_summaries es
            WHERE es.world_id = $1 AND es.scope = 'world'
            AND es.scope_id = he.year AND es.granularity = 'year'
        )
        ORDER BY he.year
    """, world_id)

    count = 0
    for yr in years:
        year = yr["year"]

        # Get top 15 events for this year
        top_events = await conn.fetch("""
            SELECT he.event_type, he.year, ne.narrative_weight, ne.emotional_tone,
                   s.name AS site_name,
                   he.details->>'hf_id' AS hf_id
            FROM history_events he
            JOIN narrative_events ne ON ne.world_id = he.world_id AND ne.event_id = he.id
            LEFT JOIN sites s ON s.world_id = he.world_id AND s.id = he.site_id
            WHERE he.world_id = $1 AND he.year = $2
            ORDER BY ne.narrative_weight DESC
            LIMIT 15
        """, world_id, year)

        if not top_events:
            continue

        event_descriptions = []
        for ev in top_events:
            desc = f"- {ev['event_type'].replace('_', ' ')} (weight: {ev['narrative_weight']:.1f}, tone: {ev['emotional_tone']})"
            if ev["site_name"]:
                desc += f" at {ev['site_name']}"
            event_descriptions.append(desc)

        prompt = (
            f"Year {year} of the world chronicle. Key events:\n"
            + "\n".join(event_descriptions[:15])
            + "\n\nWrite a 2-4 sentence chronicle summary of this year:"
        )

        summary = await _generate(prompt, system=SYSTEM_SUMMARY, max_tokens=200)
        if summary:
            event_ids = [ev["hf_id"] for ev in top_events if ev["hf_id"]]
            await conn.execute("""
                INSERT INTO event_summaries
                    (world_id, scope, scope_id, granularity, summary_text, key_events)
                VALUES ($1, 'world', $2, 'year', $3, $4)
                ON CONFLICT (world_id, scope, scope_id, granularity) DO UPDATE
                SET summary_text = EXCLUDED.summary_text,
                    generated_at = now()
            """, world_id, year, summary,
                json.dumps(event_ids[:10]) if event_ids else None)
            count += 1

        if count >= 50:  # Cap per run
            break

    log.info("Year summaries: %d generated", count)
    return count


# ═══════════════════════════════════════════════════════════════════════
# 3.6.6: Character Narrative Profiles
# ═══════════════════════════════════════════════════════════════════════

SYSTEM_CHARACTER = (
    "You are a fantasy historian writing a character profile for a chronicle. "
    "Given the character's attributes and key events, write:\n"
    "1. A role description (1 sentence, what they are/were)\n"
    "2. An arc summary (2-3 sentences, their life story)\n"
    "3. A personality voice note (1 sentence, how this character would narrate)\n"
    "Output as JSON with keys: role_description, arc_summary, personality_voice"
)

# Personality facet to voice mapping (subset of 50 DF facets)
PERSONALITY_VOICE_HINTS = {
    "ANXIETY_PROPENSITY": {"high": "nervous, detail-obsessed", "low": "unflappable, calm"},
    "ANGER_PROPENSITY": {"high": "hot-headed, passionate", "low": "measured, even-tempered"},
    "DEPRESSION_PROPENSITY": {"high": "melancholic, reflective", "low": "optimistic, cheerful"},
    "IMMODERATION": {"high": "impulsive, dramatic", "low": "restrained, disciplined"},
    "EMOTIONALLY_OBSESSIVE": {"high": "intensely loyal, fixated", "low": "detached, pragmatic"},
    "CURIOUS": {"high": "inquisitive, wandering", "low": "focused, routine-bound"},
    "ABSTRACT_INCLINED": {"high": "philosophical, dreamy", "low": "practical, grounded"},
    "VENGEFUL": {"high": "grudge-holding, relentless", "low": "forgiving, graceful"},
}


def _build_voice_hints(personality: dict | None) -> str:
    """Build voice hints from DF personality facets."""
    if not personality:
        return ""
    hints = []
    for facet, mapping in PERSONALITY_VOICE_HINTS.items():
        val = personality.get(facet)
        if val is not None:
            if val > 60:
                hints.append(mapping["high"])
            elif val < 30:
                hints.append(mapping["low"])
    return ", ".join(hints[:4]) if hints else "balanced, unremarkable"


async def generate_character_profiles(conn, world_id: int,
                                       limit: int = 30) -> int:
    """Generate character narrative profiles for prominent HFs."""
    # Get top HFs by prominence that don't have profiles yet
    hfs = await conn.fetch("""
        SELECT hf.id, hf.name, hf.race, hf.caste, hf.birth_year, hf.death_year,
               hf.kill_count, hf.prominence_score, hf.salience_score,
               hf.is_necromancer, hf.is_vampire, hf.is_deity, hf.is_werebeast,
               hf.details AS hf_details
        FROM historical_figures hf
        WHERE hf.world_id = $1 AND hf.prominence_score > 0.3
        AND NOT EXISTS (
            SELECT 1 FROM character_narratives cn
            WHERE cn.world_id = $1 AND cn.hf_id = hf.id
        )
        ORDER BY hf.prominence_score DESC
        LIMIT $2
    """, world_id, limit)

    if not hfs:
        log.info("Character profiles: no unprocessed prominent HFs")
        return 0

    count = 0
    for hf in hfs:
        # Get key events for this HF
        events = await conn.fetch("""
            SELECT he.event_type, he.year, ne.narrative_weight
            FROM history_events he
            JOIN narrative_events ne ON ne.world_id = he.world_id AND ne.event_id = he.id
            WHERE he.world_id = $1
            AND (he.details->>'hf_id' = $2::text
                 OR he.details->>'hf_id_1' = $2::text
                 OR he.details->>'hf_id_2' = $2::text
                 OR he.details->>'slayer_hf_id' = $2::text)
            ORDER BY ne.narrative_weight DESC
            LIMIT 10
        """, world_id, str(hf["id"]))

        # Build prompt
        details = hf["hf_details"] if isinstance(hf["hf_details"], dict) else {}
        personality = details.get("personality")
        voice_hints = _build_voice_hints(
            personality if isinstance(personality, dict) else None)

        flags = []
        if hf["is_necromancer"]:
            flags.append("necromancer")
        if hf["is_vampire"]:
            flags.append("vampire")
        if hf["is_deity"]:
            flags.append("deity")
        if hf["is_werebeast"]:
            flags.append("werebeast")

        event_lines = []
        for ev in events:
            event_lines.append(
                f"  Y{ev['year']}: {ev['event_type'].replace('_', ' ')} "
                f"(weight: {ev['narrative_weight']:.1f})")

        prompt = (
            f"Character: {hf['name'] or 'Unknown'}\n"
            f"Race: {hf['race'] or '?'}, {hf['caste'] or '?'}\n"
            f"Born: Year {hf['birth_year'] or '?'}"
            f"{', Died: Year ' + str(hf['death_year']) if hf['death_year'] else ', Still living'}\n"
            f"Kills: {hf['kill_count'] or 0}\n"
            f"Special: {', '.join(flags) if flags else 'none'}\n"
            f"Prominence: {hf['prominence_score']:.2f}\n"
            f"Personality hints: {voice_hints}\n\n"
            f"Key events:\n" + "\n".join(event_lines) + "\n\n"
            f"Generate the character profile as JSON:"
        )

        text = await _generate(prompt, system=SYSTEM_CHARACTER, max_tokens=300)
        if not text:
            continue

        # Parse JSON from response
        role_desc = ""
        arc_summary = ""
        personality_voice = ""
        try:
            # Try to extract JSON from response
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                parsed = json.loads(text[start:end])
                role_desc = parsed.get("role_description", "")
                arc_summary = parsed.get("arc_summary", "")
                personality_voice = parsed.get("personality_voice", "")
        except (json.JSONDecodeError, TypeError):
            # Use raw text as arc_summary
            arc_summary = text[:500]

        key_moments = [
            {"year": ev["year"], "event": ev["event_type"].replace("_", " ")}
            for ev in events[:5]
        ]

        await conn.execute("""
            INSERT INTO character_narratives
                (world_id, hf_id, character_name, role_description,
                 arc_summary, key_moments, personality_voice)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (world_id, COALESCE(unit_id, -1), COALESCE(hf_id, -1))
            DO UPDATE SET
                role_description = EXCLUDED.role_description,
                arc_summary = EXCLUDED.arc_summary,
                key_moments = EXCLUDED.key_moments,
                personality_voice = EXCLUDED.personality_voice,
                generated_at = now()
        """, world_id, hf["id"], hf["name"] or "Unknown",
             role_desc, arc_summary, json.dumps(key_moments), personality_voice)
        count += 1

        if count <= 3:
            log.info("  Profile: %s — %s", hf["name"], role_desc[:60])

    log.info("Character profiles: %d generated", count)
    return count


# ═══════════════════════════════════════════════════════════════════════
# 3.6.8: Event Cluster Summaries
# ═══════════════════════════════════════════════════════════════════════

SYSTEM_CLUSTER = (
    "You are a fantasy historian. Name this group of events with a short, "
    "evocative title (3-8 words). No quotes."
)


async def generate_cluster_summaries(conn, world_id: int) -> int:
    """Generate summary titles for event clusters without one."""
    clusters = await conn.fetch("""
        SELECT id, cluster_type, start_tick / 403200 AS start_year,
               end_tick / 403200 AS end_year,
               jsonb_array_length(event_ids) AS event_count
        FROM event_clusters
        WHERE world_id = $1 AND (summary IS NULL OR summary = '')
        ORDER BY jsonb_array_length(event_ids) DESC
        LIMIT 100
    """, world_id)

    count = 0
    for cl in clusters:
        prompt = (
            f"Event cluster type: {cl['cluster_type']}\n"
            f"Time: Year {cl['start_year']} to Year {cl['end_year']}\n"
            f"Number of events: {cl['event_count']}\n\n"
            f"Generate a title:"
        )

        title = await _generate(prompt, system=SYSTEM_CLUSTER, max_tokens=20)
        if title:
            title = title.strip('"\'').rstrip(".")
            await conn.execute(
                "UPDATE event_clusters SET summary = $1 WHERE id = $2",
                title, cl["id"],
            )
            count += 1

    log.info("Cluster summaries: %d generated", count)
    return count
