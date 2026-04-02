"""Stage 3.6 + 4.2 Narrative API routes.

Provides:
  GET /api/narrative/timeline — Unified fortress timeline
  GET /api/narrative/arcs — Detected narrative arcs
  GET /api/narrative/status — Narrative data layer statistics
  GET /api/narrative/context — Assembled narrative context
  GET /api/narrative/war/{war_id} — War narrative
  GET /api/narrative/battle/{battle_id} — Battle detail
  GET /api/narrative/civilization/{entity_id} — Civilization narrative
  GET /api/narrative/biography/{hf_id} — Character biography
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel

from chronicler.db.connection import get_pool

router = APIRouter(tags=["narrative"])


@router.get("/narrative/timeline")
async def fortress_timeline(
    world_id: int = Query(1),
    start_year: int = Query(0),
    end_year: int = Query(9999),
    min_weight: float = Query(0.0),
    limit: int = Query(200),
):
    """Unified chronological stream of events with narrative metadata.

    Joins history_events + narrative_events for scored, filterable timeline.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT he.id AS event_id, he.event_type, he.year, he.site_id,
                   he.details,
                   ne.narrative_weight, ne.drama_score, ne.emotional_tone,
                   ne.irony_flags,
                   s.name AS site_name
            FROM history_events he
            JOIN narrative_events ne
                ON ne.world_id = he.world_id AND ne.event_id = he.id
            LEFT JOIN sites s
                ON s.world_id = he.world_id AND s.id = he.site_id
            WHERE he.world_id = $1
                AND he.year BETWEEN $2 AND $3
                AND ne.narrative_weight >= $4
            ORDER BY ne.narrative_weight DESC, he.year, he.id
            LIMIT $5
        """, world_id, start_year, end_year, min_weight, limit)

    return {
        "world_id": world_id,
        "count": len(rows),
        "events": [dict(r) for r in rows],
    }


@router.get("/narrative/arcs")
async def narrative_arcs(
    world_id: int = Query(1),
    arc_type: str | None = Query(None),
    min_weight: float = Query(0.0),
    limit: int = Query(50),
):
    """List detected narrative arcs, optionally filtered by type."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        if arc_type:
            rows = await conn.fetch("""
                SELECT id, arc_type, title,
                       start_tick / 403200 AS start_year,
                       end_tick / 403200 AS end_year,
                       key_events, characters, resolution, dramatic_weight
                FROM narrative_arcs
                WHERE world_id = $1 AND arc_type = $2
                    AND dramatic_weight >= $3
                ORDER BY dramatic_weight DESC LIMIT $4
            """, world_id, arc_type, min_weight, limit)
        else:
            rows = await conn.fetch("""
                SELECT id, arc_type, title,
                       start_tick / 403200 AS start_year,
                       end_tick / 403200 AS end_year,
                       key_events, characters, resolution, dramatic_weight
                FROM narrative_arcs
                WHERE world_id = $1 AND dramatic_weight >= $2
                ORDER BY dramatic_weight DESC LIMIT $3
            """, world_id, min_weight, limit)

    return {
        "world_id": world_id,
        "count": len(rows),
        "arcs": [dict(r) for r in rows],
    }


@router.get("/narrative/status")
async def narrative_status(world_id: int = Query(1)):
    """Show narrative data layer statistics."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        tables = {
            "narrative_events": "SELECT COUNT(*) FROM narrative_events WHERE world_id = $1",
            "event_causal_links": "SELECT COUNT(*) FROM event_causal_links WHERE world_id = $1",
            "narrative_arcs": "SELECT COUNT(*) FROM narrative_arcs WHERE world_id = $1",
            "event_summaries": "SELECT COUNT(*) FROM event_summaries WHERE world_id = $1",
            "character_narratives": "SELECT COUNT(*) FROM character_narratives WHERE world_id = $1",
            "event_clusters": "SELECT COUNT(*) FROM event_clusters WHERE world_id = $1",
        }
        counts = {}
        for name, sql in tables.items():
            counts[name] = await conn.fetchval(sql, world_id)

        # Tone distribution
        tones = await conn.fetch(
            "SELECT emotional_tone, COUNT(*) AS n FROM narrative_events "
            "WHERE world_id = $1 GROUP BY emotional_tone ORDER BY n DESC",
            world_id,
        )

        # Arc type distribution
        arc_types = await conn.fetch(
            "SELECT arc_type, COUNT(*) AS n FROM narrative_arcs "
            "WHERE world_id = $1 GROUP BY arc_type ORDER BY n DESC",
            world_id,
        )

        # Causal link types
        link_types = await conn.fetch(
            "SELECT link_type, COUNT(*) AS n FROM event_causal_links "
            "WHERE world_id = $1 GROUP BY link_type ORDER BY n DESC",
            world_id,
        )

    return {
        "world_id": world_id,
        "table_counts": counts,
        "tone_distribution": {r["emotional_tone"]: r["n"] for r in tones},
        "arc_types": {r["arc_type"]: r["n"] for r in arc_types},
        "causal_link_types": {r["link_type"]: r["n"] for r in link_types},
    }


@router.get("/narrative/context")
async def narrative_context(
    world_id: int = Query(1),
    query_type: str = Query("world_overview"),
    target_id: int | None = Query(None),
    year: int | None = Query(None),
    budget: int = Query(32000),
):
    """Assemble narrative context for LLM storytelling.

    Query types: fortress_saga, character_focus, year_chronicle,
    event_detail, world_overview.
    """
    from chronicler.storyteller.narrative_context import assemble_context

    pool = await get_pool()
    async with pool.acquire() as conn:
        ctx = await assemble_context(
            conn, world_id, query_type,
            target_id=target_id, year=year, token_budget=budget)

    return ctx.as_dict()


# ── Stage 4.2: Narrative Generator Endpoints ────────────────────────────────


@router.get("/narrative/war/{war_id}")
async def war_narrative(war_id: int, world_id: int = Query(1)):
    """Generate structured war narrative with battles, casualties, timeline."""
    from chronicler.storyteller.narrative_generators import generate_war_narrative

    pool = await get_pool()
    async with pool.acquire() as conn:
        return await generate_war_narrative(conn, world_id, war_id)


@router.get("/narrative/battle/{battle_id}")
async def battle_detail(battle_id: int, world_id: int = Query(1)):
    """Generate detailed battle narrative with squads, participants, events."""
    from chronicler.storyteller.narrative_generators import generate_battle_detail

    pool = await get_pool()
    async with pool.acquire() as conn:
        return await generate_battle_detail(conn, world_id, battle_id)


@router.get("/narrative/civilization/{entity_id}")
async def civilization_narrative(entity_id: int, world_id: int = Query(1)):
    """Generate civilization rise-and-fall narrative."""
    from chronicler.storyteller.narrative_generators import generate_civilization_narrative

    pool = await get_pool()
    async with pool.acquire() as conn:
        return await generate_civilization_narrative(conn, world_id, entity_id)


@router.get("/narrative/biography/{hf_id}")
async def character_biography(hf_id: int, world_id: int = Query(1)):
    """Generate comprehensive character biography."""
    from chronicler.storyteller.narrative_generators import generate_character_biography

    pool = await get_pool()
    async with pool.acquire() as conn:
        return await generate_character_biography(conn, world_id, hf_id)


# ── Stage 4.5: AI Narrative Generator Endpoints ───────────────────────────────


@router.get("/narrative/world-summary")
async def world_summary(world_id: int = Query(1), force: bool = Query(False)):
    """AI-generated world overview (cached, ~5s first generation)."""
    from chronicler.storyteller.ai_generators import generate_world_summary

    pool = await get_pool()
    return await generate_world_summary(pool, world_id, force=force)


@router.get("/narrative/obituary/{hf_id}")
async def obituary(hf_id: int, world_id: int = Query(1), force: bool = Query(False)):
    """AI-generated newspaper-style obituary for a dead HF."""
    from chronicler.storyteller.ai_generators import generate_obituary

    pool = await get_pool()
    return await generate_obituary(pool, world_id, hf_id, force=force)


@router.get("/narrative/year/{year}")
async def year_in_history(year: int, world_id: int = Query(1), force: bool = Query(False)):
    """AI-generated 'Year in History' newspaper-style summary."""
    from chronicler.storyteller.ai_generators import generate_year_in_history

    pool = await get_pool()
    return await generate_year_in_history(pool, world_id, year, force=force)


@router.get("/narrative/highlights")
async def highlight_reel(
    world_id: int = Query(1),
    top_n: int = Query(20),
    force: bool = Query(False),
):
    """AI-generated 'Greatest Moments' highlight reel."""
    from chronicler.storyteller.ai_generators import generate_highlight_reel

    pool = await get_pool()
    return await generate_highlight_reel(pool, world_id, top_n=top_n, force=force)


# ── Stage 4.6: Fortress Saga Generator Endpoints ─────────────────────────────


@router.get("/narrative/saga/styles")
async def saga_styles():
    """List available narrative style presets."""
    from chronicler.storyteller.saga_generator import list_styles

    return list_styles()


@router.get("/narrative/saga/plan")
async def saga_plan(
    world_id: int = Query(1),
    site_id: int | None = Query(None),
    style: str = Query("epic_saga"),
):
    """Plan a saga (chapter outline without generating content)."""
    from chronicler.storyteller.saga_generator import plan_saga as _plan_saga

    pool = await get_pool()
    return await _plan_saga(pool, world_id, site_id, style)


@router.get("/narrative/saga/generate")
async def saga_generate(
    world_id: int = Query(1),
    site_id: int | None = Query(None),
    style: str = Query("epic_saga"),
    force: bool = Query(False),
):
    """Generate a complete multi-chapter fortress saga (may take 30-60s)."""
    from chronicler.storyteller.saga_generator import generate_saga as _generate_saga

    pool = await get_pool()
    return await _generate_saga(pool, world_id, site_id, style, force)


@router.get("/narrative/saga/chapter/{chapter_index}")
async def saga_chapter_stream(
    chapter_index: int,
    world_id: int = Query(1),
    site_id: int | None = Query(None),
    style: str = Query("epic_saga"),
):
    """Stream a single saga chapter via SSE."""
    import json as json_mod

    from sse_starlette.sse import EventSourceResponse

    from chronicler.storyteller.saga_generator import SagaGenerator

    pool = await get_pool()
    generator = SagaGenerator(pool)

    async def event_gen():
        async for token in generator.generate_chapter_stream(
            world_id, chapter_index, site_id, style
        ):
            yield {"data": json_mod.dumps({"token": token})}
        yield {"data": json_mod.dumps({"done": True})}

    return EventSourceResponse(event_gen())


# ── Stage 4.7: Narrative Quality & Tuning Endpoints ──────────────────────────


class QualityCheckRequest(BaseModel):
    text: str
    world_id: int = 1


@router.post("/narrative/quality/accuracy")
async def check_accuracy(body: QualityCheckRequest):
    """Check factual accuracy of narrative text against CDM data."""
    from chronicler.storyteller.quality import check_accuracy as _check_accuracy

    pool = await get_pool()
    return await _check_accuracy(pool, body.text, body.world_id)


@router.post("/narrative/quality/evaluate")
async def evaluate_quality(body: QualityCheckRequest):
    """Full quality evaluation (accuracy + structure + specificity)."""
    from chronicler.storyteller.quality import evaluate_quality as _evaluate_quality

    pool = await get_pool()
    return await _evaluate_quality(pool, body.text, body.world_id)
