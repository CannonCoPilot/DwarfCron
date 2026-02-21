"""Monitoring API — view logged LLM interactions and aggregate stats."""

from fastapi import APIRouter, Request

router = APIRouter()


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
                       first_token_ms, total_latency_ms, status
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
                       first_token_ms, total_latency_ms, status
                FROM storyteller_log
                ORDER BY timestamp DESC LIMIT $1
                """,
                limit,
            )
    return [dict(r) for r in rows]


@router.get("/monitoring/interactions/{interaction_id}")
async def get_interaction(interaction_id: int, request: Request):
    """Full detail for a single interaction."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM storyteller_log WHERE id = $1", interaction_id
        )
    if not row:
        return {"error": "not found"}
    return dict(row)


@router.get("/monitoring/summary")
async def summary(request: Request):
    """Aggregate stats across all logged interactions."""
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
                round(avg(tokens_streamed)) as avg_tokens,
                sum(tokens_streamed) as total_tokens
            FROM storyteller_log
            """
        )
    return dict(row) if row else {}
