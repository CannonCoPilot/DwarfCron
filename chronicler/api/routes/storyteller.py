"""Storyteller chat endpoint — SSE streaming from Qwen3 via LiteLLM.

Supports two modes:
  keyword  — traditional keyword routing (fast, deterministic context)
  agentic  — LLM with autonomous SQL tool use (flexible, multi-round)
  hybrid   — both available; caller picks via request body `mode` field
"""

import json
from typing import AsyncGenerator

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from chronicler.config import (
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
    STORYTELLER_MODE,
)
from chronicler.monitoring import InteractionLog
from chronicler.storyteller.agentic import AgenticStoryteller
from chronicler.storyteller.context import retrieve_context, extract_keywords
from chronicler.storyteller.llm import stream_completion
from chronicler.storyteller.prompts import build_messages, format_context

router = APIRouter()


class AskRequest(BaseModel):
    query: str
    world_id: int
    mode: str | None = None  # "keyword", "agentic", or None (use server default)


def _resolve_mode(requested: str | None) -> str:
    """Determine effective mode from request + server config."""
    if STORYTELLER_MODE == "keyword":
        return "keyword"
    if STORYTELLER_MODE == "agentic":
        return "agentic"
    # hybrid — respect caller preference, default to agentic
    if requested in ("keyword", "agentic"):
        return requested
    return "agentic"


@router.post("/ask")
async def ask(body: AskRequest, request: Request):
    """Stream a storyteller response via SSE.

    In hybrid mode, the `mode` field in the request body selects between
    keyword routing and agentic SQL exploration.
    """
    mode = _resolve_mode(body.mode)

    if mode == "agentic":
        return await _agentic_ask(body, request)
    return await _keyword_ask(body, request)


async def _keyword_ask(body: AskRequest, request: Request):
    """Keyword-routed storyteller (original implementation)."""
    pool = request.app.state.pool

    interaction_log = InteractionLog(
        query=body.query,
        world_id=body.world_id,
        keywords=extract_keywords(body.query),
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
        max_tokens=LLM_MAX_TOKENS,
        mode="keyword",
    ).start()

    # Retrieve world name
    async with pool.acquire() as conn:
        world_name = await conn.fetchval(
            "SELECT name FROM worlds WHERE id = $1", body.world_id
        )
    interaction_log.world_name = world_name

    # Build context
    records = await retrieve_context(pool, body.world_id, body.query)
    context_text = format_context(records)
    interaction_log.context_done(records, context_text)

    messages = build_messages(body.query, context_text, world_name or "the world")

    async def event_generator() -> AsyncGenerator[dict, None]:
        interaction_log.llm_start()
        try:
            async for token in stream_completion(
                messages,
                model=LLM_MODEL,
                temperature=LLM_TEMPERATURE,
                max_tokens=LLM_MAX_TOKENS,
            ):
                interaction_log.first_token()
                interaction_log.count_token(token)
                yield {"data": json.dumps({"token": token})}
        except Exception as e:
            interaction_log.finish(status="error", error=str(e))
            yield {"data": json.dumps({"error": str(e)})}
        else:
            interaction_log.finish()
        yield {"data": json.dumps({"done": True})}
        await interaction_log.flush(pool)

    return EventSourceResponse(event_generator())


@router.post("/agentic/ask")
async def agentic_ask(body: AskRequest, request: Request):
    """Dedicated agentic endpoint (always uses agentic mode)."""
    return await _agentic_ask(body, request)


async def _agentic_ask(body: AskRequest, request: Request):
    """Agentic SQL storyteller with autonomous database exploration."""
    pool = request.app.state.pool

    interaction_log = InteractionLog(
        query=body.query,
        world_id=body.world_id,
        model="agentic",
        mode="agentic",
    ).start()

    storyteller = AgenticStoryteller(pool, body.world_id)

    async def event_generator() -> AsyncGenerator[dict, None]:
        interaction_log.llm_start()
        try:
            async for event in storyteller.ask(body.query):
                if event["type"] == "token":
                    interaction_log.first_token()
                    interaction_log.count_token(event["data"])
                    yield {"data": json.dumps({"token": event["data"]})}
                elif event["type"] == "progress":
                    yield {"data": json.dumps({"progress": event["data"]})}
                elif event["type"] == "sql":
                    interaction_log.add_sql_query(event["data"])
                elif event["type"] == "done":
                    pass  # handled below
        except Exception as e:
            interaction_log.finish(status="error", error=str(e))
            yield {"data": json.dumps({"error": str(e)})}
        else:
            interaction_log.finish()
        yield {"data": json.dumps({"done": True})}
        await interaction_log.flush(pool)

    return EventSourceResponse(event_generator())
