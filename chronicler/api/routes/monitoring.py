"""Monitoring API — view logged LLM interactions and aggregate stats."""

import json

from fastapi import APIRouter, Request

router = APIRouter()


def _extract_mode(row: dict) -> str:
    """Extract the storyteller mode from context_categories JSONB."""
    cats = row.get("context_categories")
    if isinstance(cats, str):
        try:
            cats = json.loads(cats)
        except (json.JSONDecodeError, TypeError):
            cats = {}
    if isinstance(cats, dict) and "_agentic" in cats:
        return cats["_agentic"].get("mode", "agentic")
    return "keyword"


def _extract_sql_queries(row: dict) -> list[dict]:
    """Extract SQL queries from agentic interaction context_categories."""
    cats = row.get("context_categories")
    if isinstance(cats, str):
        try:
            cats = json.loads(cats)
        except (json.JSONDecodeError, TypeError):
            cats = {}
    if isinstance(cats, dict) and "_agentic" in cats:
        return cats["_agentic"].get("sql_queries", [])
    return []


@router.get("/monitoring/interactions")
async def list_interactions(request: Request, limit: int = 50, world_id: int | None = None):
    """Recent storyteller interactions, newest first."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        if world_id is not None:
            rows = await conn.fetch(
                """
                SELECT id, timestamp, query, world_id, world_name,
                       keywords, context_records, tokens_streamed,
                       context_latency_ms, first_token_ms,
                       llm_latency_ms, total_latency_ms,
                       status, context_categories
                FROM storyteller_log
                WHERE world_id = $1
                ORDER BY timestamp DESC LIMIT $2
                """,
                world_id, limit,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT id, timestamp, query, world_id, world_name,
                       keywords, context_records, tokens_streamed,
                       context_latency_ms, first_token_ms,
                       llm_latency_ms, total_latency_ms,
                       status, context_categories
                FROM storyteller_log
                ORDER BY timestamp DESC LIMIT $1
                """,
                limit,
            )
    result = []
    for r in rows:
        d = dict(r)
        d["mode"] = _extract_mode(d)
        sql_queries = _extract_sql_queries(d)
        d["sql_rounds"] = len(sql_queries)
        # Don't send full context_categories to list view
        del d["context_categories"]
        result.append(d)
    return result


@router.get("/monitoring/interactions/{interaction_id}")
async def get_interaction(interaction_id: int, request: Request):
    """Full detail for a single interaction, including SQL queries for agentic mode."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM storyteller_log WHERE id = $1", interaction_id
        )
    if not row:
        return {"error": "not found"}
    d = dict(row)
    d["mode"] = _extract_mode(d)
    d["sql_queries"] = _extract_sql_queries(d)
    d["sql_rounds"] = len(d["sql_queries"])
    return d


@router.get("/monitoring/summary")
async def summary(request: Request):
    """Aggregate stats across all logged interactions, with per-mode breakdown."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                count(*) as total,
                count(*) FILTER (WHERE status = 'error') as errors,
                round(avg(first_token_ms)) as avg_ttft_ms,
                round(avg(total_latency_ms)) as avg_latency_ms,
                round(avg(context_latency_ms)) as avg_context_ms,
                round(avg(llm_latency_ms)) as avg_llm_ms,
                round(avg(tokens_streamed)) as avg_tokens,
                sum(tokens_streamed) as total_tokens,
                count(*) FILTER (WHERE timestamp > now() - interval '24 hours') as today
            FROM storyteller_log
            """
        )
        # Per-mode breakdown from context_categories JSONB
        mode_rows = await conn.fetch(
            """
            SELECT
                CASE WHEN context_categories ? '_agentic' THEN 'agentic' ELSE 'keyword' END as mode,
                count(*) as count,
                round(avg(total_latency_ms)) as avg_latency_ms,
                round(avg(first_token_ms)) as avg_ttft_ms
            FROM storyteller_log
            GROUP BY 1
            """
        )
    result = dict(row) if row else {}
    result["by_mode"] = {r["mode"]: dict(r) for r in mode_rows}
    return result


@router.get("/monitoring/narrative-cache")
async def narrative_cache_stats(request: Request):
    """Narrative cache statistics — generated content breakdown."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT cache_type, count(*) as count,
                   max(generated_at) as latest
            FROM narrative_cache
            GROUP BY cache_type
            ORDER BY count DESC
            """
        )
        total = await conn.fetchval("SELECT count(*) FROM narrative_cache")
    return {
        "total": total or 0,
        "by_type": [dict(r) for r in rows],
    }


@router.get("/monitoring/quality")
async def quality_stats(request: Request, world_id: int | None = None):
    """Narrative quality dashboard — shows generated content with timing."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        query = """
            SELECT id, world_id, cache_type, cache_key, model,
                   generated_at, ttl_hours,
                   length(content) as content_chars
            FROM narrative_cache
        """
        params = []
        if world_id is not None:
            query += " WHERE world_id = $1"
            params.append(world_id)
        query += " ORDER BY generated_at DESC LIMIT 100"

        rows = await conn.fetch(query, *params)
    return [dict(r) for r in rows]


@router.get("/monitoring/latency-distribution")
async def latency_distribution(request: Request):
    """Latency phase breakdown for histogram visualization."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                context_latency_ms,
                first_token_ms,
                llm_latency_ms,
                total_latency_ms,
                CASE WHEN context_categories ? '_agentic' THEN 'agentic' ELSE 'keyword' END as mode
            FROM storyteller_log
            WHERE total_latency_ms IS NOT NULL
            ORDER BY timestamp DESC
            LIMIT 200
            """
        )
    return [dict(r) for r in rows]
