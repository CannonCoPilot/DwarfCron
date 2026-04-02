"""Stage 4.5: AI Narrative Generators.

Higher-order narrative content generated via LLM with caching:
  - World summary (2-3 paragraph overview)
  - Character obituary (newspaper-style for dead HFs)
  - Year-in-history (major events of a specific year)
  - Notable events highlight reel (top 20 by importance score)

All generators use the same pattern:
  1. Check narrative_cache for existing content
  2. If cached and not expired, return it
  3. Otherwise, gather data from DB, build prompt, call LLM, cache result
"""

import json
import logging
import time
from datetime import datetime, timedelta, timezone

import asyncpg

from chronicler.config import AGENTIC_MODEL, LLM_TEMPERATURE
from chronicler.storyteller.llm import collect_with_tools

log = logging.getLogger(__name__)


# ── Cache layer ───────────────────────────────────────────────────────


async def _get_cached(
    pool: asyncpg.Pool, world_id: int, cache_type: str, cache_key: str,
) -> str | None:
    """Return cached content if fresh, else None."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT content, generated_at, ttl_hours
            FROM narrative_cache
            WHERE world_id = $1 AND cache_type = $2 AND cache_key = $3
            """,
            world_id, cache_type, cache_key,
        )
    if not row:
        return None
    expires = row["generated_at"] + timedelta(hours=row["ttl_hours"])
    if datetime.now(timezone.utc) > expires:
        return None
    return row["content"]


async def _set_cached(
    pool: asyncpg.Pool, world_id: int, cache_type: str, cache_key: str,
    content: str, model: str,
) -> None:
    """Upsert content into the narrative cache."""
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO narrative_cache (world_id, cache_type, cache_key, content, model)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (world_id, cache_type, cache_key)
            DO UPDATE SET content = $4, model = $5, generated_at = now()
            """,
            world_id, cache_type, cache_key, content, model,
        )


async def _llm_generate(prompt: str, system: str = "") -> str:
    """Call LLM and return text content (no tool use)."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    content, _ = await collect_with_tools(
        messages, model=AGENTIC_MODEL, temperature=LLM_TEMPERATURE,
        max_tokens=2048,
    )
    return content


# ── 4.5.1: World Summary ─────────────────────────────────────────────


async def generate_world_summary(
    pool: asyncpg.Pool, world_id: int, *, force: bool = False,
) -> dict:
    """Generate a 2-3 paragraph world overview.

    Returns: {content, cached, model, latency_ms}
    """
    if not force:
        cached = await _get_cached(pool, world_id, "world_summary", "overview")
        if cached:
            return {"content": cached, "cached": True, "model": None, "latency_ms": 0}

    async with pool.acquire() as conn:
        stats = await conn.fetchrow("""
            SELECT
                (SELECT name FROM worlds WHERE id = $1) as world_name,
                (SELECT alt_name FROM worlds WHERE id = $1) as alt_name,
                (SELECT count(*) FROM historical_figures WHERE world_id = $1) as hf_count,
                (SELECT count(*) FROM historical_figures WHERE world_id = $1 AND death_year IS NULL) as living_hfs,
                (SELECT count(*) FROM entities WHERE world_id = $1 AND type = 'civilization') as civ_count,
                (SELECT count(*) FROM sites WHERE world_id = $1) as site_count,
                (SELECT count(*) FROM history_events WHERE world_id = $1) as event_count,
                (SELECT count(*) FROM history_event_collections WHERE world_id = $1 AND type = 'war') as war_count,
                (SELECT MAX(year) FROM history_events WHERE world_id = $1) as max_year,
                (SELECT count(*) FROM artifacts WHERE world_id = $1) as artifact_count
        """, world_id)

        # Top civilizations
        top_civs = await conn.fetch("""
            SELECT e.name, e.race, count(s.id) as sites
            FROM entities e
            LEFT JOIN sites s ON s.owner_entity_id = e.id AND s.world_id = e.world_id
            WHERE e.world_id = $1 AND e.type = 'civilization'
            GROUP BY e.id, e.name, e.race
            ORDER BY sites DESC LIMIT 5
        """, world_id)

        # Most notable events
        notable = await conn.fetch("""
            SELECT he.event_type, he.year, ne.narrative_weight
            FROM narrative_events ne
            JOIN history_events he ON he.world_id = ne.world_id AND he.id = ne.event_id
            WHERE ne.world_id = $1
            ORDER BY ne.narrative_weight DESC LIMIT 10
        """, world_id)

    s = dict(stats)
    civs_text = ", ".join(
        f"{c['name']} ({c['race']}, {c['sites']} sites)" for c in top_civs
    )
    notable_text = "\n".join(
        f"  - Year {n['year']}: {n['event_type']} (weight: {n['narrative_weight']:.1f})"
        for n in notable
    )

    prompt = f"""Write a 2-3 paragraph overview of the world "{s['world_name']}" (also known as "{s['alt_name']}").

Statistics:
- {s['hf_count']:,} historical figures ({s['living_hfs']:,} still living)
- {s['civ_count']} civilizations across {s['site_count']:,} sites
- {s['event_count']:,} recorded events spanning {s['max_year'] or 0} years
- {s['war_count']} wars fought
- {s['artifact_count']:,} artifacts created

Major civilizations: {civs_text}

Most notable events:
{notable_text}

Write in an evocative, historical chronicle style. Focus on the grand sweep of history — the rise and fall of civilizations, major conflicts, and the overall character of the world. Do not use bullet points or headers."""

    t0 = time.monotonic()
    content = await _llm_generate(prompt, system="You are a historian chronicling a fantasy world.")
    latency = round((time.monotonic() - t0) * 1000)

    await _set_cached(pool, world_id, "world_summary", "overview", content, AGENTIC_MODEL)
    return {"content": content, "cached": False, "model": AGENTIC_MODEL, "latency_ms": latency}


# ── 4.5.2: Character Obituary ────────────────────────────────────────


async def generate_obituary(
    pool: asyncpg.Pool, world_id: int, hf_id: int, *, force: bool = False,
) -> dict:
    """Generate a newspaper-style obituary for a dead HF.

    Returns: {content, cached, model, latency_ms, hf_name}
    """
    cache_key = str(hf_id)
    if not force:
        cached = await _get_cached(pool, world_id, "obituary", cache_key)
        if cached:
            return {"content": cached, "cached": True, "model": None, "latency_ms": 0, "hf_id": hf_id}

    async with pool.acquire() as conn:
        hf = await conn.fetchrow("""
            SELECT name, race, caste, birth_year, death_year, death_cause,
                   associated_type, kill_count, details
            FROM historical_figures
            WHERE world_id = $1 AND id = $2
        """, world_id, hf_id)

        if not hf:
            return {"error": f"HF {hf_id} not found", "content": "", "cached": False}

        if hf["death_year"] is None:
            return {"error": f"HF {hf_id} is still alive", "content": "", "cached": False}

        # Key relationships
        relationships = await conn.fetch("""
            SELECT hl.link_type, h2.name as linked_name, h2.race as linked_race
            FROM hf_links hl
            JOIN historical_figures h2 ON h2.world_id = hl.world_id AND h2.id = hl.target_hf_id
            WHERE hl.world_id = $1 AND hl.source_hf_id = $2
            ORDER BY hl.link_type
            LIMIT 10
        """, world_id, hf_id)

        # Positions held
        positions = await conn.fetch("""
            SELECT hel.link_type, hel.position, e.name as entity_name
            FROM hf_entity_links hel
            JOIN entities e ON e.world_id = hel.world_id AND e.id = hel.entity_id
            WHERE hel.world_id = $1 AND hel.hf_id = $2
            LIMIT 10
        """, world_id, hf_id)

        # Key life events
        events = await conn.fetch("""
            SELECT he.event_type, he.year, he.details
            FROM history_events he
            WHERE he.world_id = $1
              AND (he.details->>'hfid' = $2::text
                   OR he.details->>'hf_id_1' = $2::text
                   OR he.details->>'slayer_hfid' = $2::text)
            ORDER BY he.year
            LIMIT 15
        """, world_id, str(hf_id))

    h = dict(hf)
    details = h.get("details") or {}
    if isinstance(details, str):
        try:
            details = json.loads(details)
        except (json.JSONDecodeError, ValueError):
            details = {}

    rels_text = "\n".join(
        f"  - {r['link_type']}: {r['linked_name']} ({r['linked_race']})"
        for r in relationships
    ) or "  None recorded"

    pos_text = "\n".join(
        f"  - {p['link_type']}: {p['position'] or p['link_type']} of {p['entity_name']}"
        for p in positions
    ) or "  None recorded"

    events_text = "\n".join(
        f"  - Year {e['year']}: {e['event_type']}"
        for e in events
    ) or "  None recorded"

    prompt = f"""Write a newspaper-style obituary for the following historical figure.

Name: {h['name']}
Race: {h['race']} ({h['caste'] or 'unknown'})
Born: Year {h['birth_year']}
Died: Year {h['death_year']}
Cause of death: {h['death_cause'] or 'unknown'}
Kill count: {h['kill_count'] or 0}
Type: {h['associated_type'] or 'unknown'}

Relationships:
{rels_text}

Positions held:
{pos_text}

Key events:
{events_text}

Write 2-3 paragraphs in a formal obituary style. Include birth and death dates, notable achievements, important relationships, cause of death, and legacy. Use a respectful but engaging tone befitting a fantasy chronicle."""

    t0 = time.monotonic()
    content = await _llm_generate(prompt, system="You are a chronicler writing obituaries for a fantasy world newspaper.")
    latency = round((time.monotonic() - t0) * 1000)

    await _set_cached(pool, world_id, "obituary", cache_key, content, AGENTIC_MODEL)
    return {
        "content": content, "cached": False, "model": AGENTIC_MODEL,
        "latency_ms": latency, "hf_id": hf_id, "hf_name": h["name"],
    }


# ── 4.5.3: Year in History ───────────────────────────────────────────


async def generate_year_in_history(
    pool: asyncpg.Pool, world_id: int, year: int, *, force: bool = False,
) -> dict:
    """Generate a newspaper-style 'Year in History' summary.

    Returns: {content, cached, model, latency_ms, year, stats}
    """
    cache_key = str(year)
    if not force:
        cached = await _get_cached(pool, world_id, "year_history", cache_key)
        if cached:
            return {"content": cached, "cached": True, "model": None, "latency_ms": 0, "year": year}

    async with pool.acquire() as conn:
        world_name = await conn.fetchval("SELECT name FROM worlds WHERE id = $1", world_id)

        # Event counts by type
        event_types = await conn.fetch("""
            SELECT event_type, count(*) as cnt
            FROM history_events
            WHERE world_id = $1 AND year = $2
            GROUP BY event_type ORDER BY cnt DESC LIMIT 15
        """, world_id, year)

        total_events = await conn.fetchval(
            "SELECT count(*) FROM history_events WHERE world_id = $1 AND year = $2",
            world_id, year)

        # Notable births
        births = await conn.fetch("""
            SELECT name, race FROM historical_figures
            WHERE world_id = $1 AND birth_year = $2
            ORDER BY kill_count DESC NULLS LAST LIMIT 10
        """, world_id, year)

        # Notable deaths
        deaths = await conn.fetch("""
            SELECT name, race, death_cause FROM historical_figures
            WHERE world_id = $1 AND death_year = $2
            ORDER BY kill_count DESC NULLS LAST LIMIT 10
        """, world_id, year)

        # Wars active
        wars = await conn.fetch("""
            SELECT name, start_year, end_year
            FROM history_event_collections
            WHERE world_id = $1 AND type = 'war'
              AND start_year <= $2 AND (end_year IS NULL OR end_year >= $2)
            LIMIT 10
        """, world_id, year)

        # Sites founded/destroyed
        sites_founded = await conn.fetch("""
            SELECT name, type FROM sites
            WHERE world_id = $1 AND founded_year = $2 LIMIT 10
        """, world_id, year)

        # Top scored events for this year
        top_events = await conn.fetch("""
            SELECT he.event_type, he.details, ne.narrative_weight
            FROM narrative_events ne
            JOIN history_events he ON he.world_id = ne.world_id AND he.id = ne.event_id
            WHERE ne.world_id = $1 AND he.year = $2
            ORDER BY ne.narrative_weight DESC LIMIT 10
        """, world_id, year)

    stats = {
        "total_events": total_events,
        "births": len(births),
        "deaths": len(deaths),
        "active_wars": len(wars),
        "sites_founded": len(sites_founded),
    }

    events_text = "\n".join(f"  - {e['event_type']}: {e['cnt']}" for e in event_types)
    births_text = "\n".join(f"  - {b['name']} ({b['race']})" for b in births) or "  None notable"
    deaths_text = "\n".join(
        f"  - {d['name']} ({d['race']}, cause: {d['death_cause'] or 'unknown'})"
        for d in deaths
    ) or "  None notable"
    wars_text = "\n".join(f"  - {w['name']} (year {w['start_year']}-{w['end_year'] or 'ongoing'})" for w in wars) or "  None"
    founded_text = "\n".join(f"  - {s['name']} ({s['type']})" for s in sites_founded) or "  None"
    top_text = "\n".join(
        f"  - {e['event_type']} (weight: {e['narrative_weight']:.1f})"
        for e in top_events
    )

    prompt = f"""Write a newspaper-style "Year in History" summary for Year {year} in the world of {world_name}.

Total events: {total_events}

Event breakdown:
{events_text}

Notable births ({len(births)}):
{births_text}

Notable deaths ({len(deaths)}):
{deaths_text}

Active wars ({len(wars)}):
{wars_text}

Sites founded:
{founded_text}

Most significant events:
{top_text}

Write 3-4 paragraphs in a broadsheet newspaper style. Lead with the most dramatic events. Mention notable births and deaths. Describe the overall tone of the year — was it peaceful or turbulent? Do not use headers or bullet points."""

    t0 = time.monotonic()
    content = await _llm_generate(prompt, system="You are a newspaper editor summarizing a year's events in a fantasy world.")
    latency = round((time.monotonic() - t0) * 1000)

    await _set_cached(pool, world_id, "year_history", cache_key, content, AGENTIC_MODEL)
    return {
        "content": content, "cached": False, "model": AGENTIC_MODEL,
        "latency_ms": latency, "year": year, "stats": stats,
    }


# ── 4.5.4: Highlight Reel ────────────────────────────────────────────


async def generate_highlight_reel(
    pool: asyncpg.Pool, world_id: int, *, top_n: int = 20, force: bool = False,
) -> dict:
    """Generate a 'Greatest Moments' highlight reel of top-scored events.

    Returns: {content, cached, model, latency_ms, events: [...]}
    """
    cache_key = f"top{top_n}"
    if not force:
        cached = await _get_cached(pool, world_id, "highlight_reel", cache_key)
        if cached:
            return {"content": cached, "cached": True, "model": None, "latency_ms": 0}

    async with pool.acquire() as conn:
        world_name = await conn.fetchval("SELECT name FROM worlds WHERE id = $1", world_id)

        events = await conn.fetch("""
            SELECT he.id, he.event_type, he.year, he.details,
                   ne.narrative_weight, ne.drama_score, ne.emotional_tone,
                   s.name as site_name
            FROM narrative_events ne
            JOIN history_events he ON he.world_id = ne.world_id AND he.id = ne.event_id
            LEFT JOIN sites s ON s.world_id = he.world_id AND s.id = he.site_id
            WHERE ne.world_id = $1
            ORDER BY ne.narrative_weight DESC
            LIMIT $2
        """, world_id, top_n)

    events_list = []
    events_text = ""
    for i, e in enumerate(events, 1):
        d = e["details"] or {}
        if isinstance(d, str):
            try:
                d = json.loads(d)
            except (json.JSONDecodeError, ValueError):
                d = {}

        entry = {
            "rank": i,
            "event_id": e["id"],
            "event_type": e["event_type"],
            "year": e["year"],
            "site_name": e["site_name"],
            "narrative_weight": float(e["narrative_weight"]) if e["narrative_weight"] else 0,
            "drama_score": float(e["drama_score"]) if e["drama_score"] else 0,
            "emotional_tone": e["emotional_tone"],
        }
        events_list.append(entry)
        events_text += f"\n{i}. Year {e['year']}: {e['event_type']} at {e['site_name'] or 'unknown location'} (tone: {e['emotional_tone']}, drama: {e['drama_score']:.1f})"

    prompt = f"""Write a "Greatest Moments in History" article for the world of {world_name}, covering these {len(events_list)} most significant events:
{events_text}

Write 4-5 paragraphs in an epic, chronicle style. Group related events thematically. Highlight the most dramatic moments. Open with the single most impactful event, then weave through the others. End with a reflection on what these events say about the world. Do not use bullet points or numbered lists."""

    t0 = time.monotonic()
    content = await _llm_generate(prompt, system="You are a master chronicler writing the definitive history of a fantasy world.")
    latency = round((time.monotonic() - t0) * 1000)

    await _set_cached(pool, world_id, "highlight_reel", cache_key, content, AGENTIC_MODEL)
    return {
        "content": content, "cached": False, "model": AGENTIC_MODEL,
        "latency_ms": latency, "events": events_list,
    }
