"""Storyteller chat endpoint — SSE streaming from Qwen3 via LiteLLM."""

import json
from typing import AsyncGenerator

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from chronicler.config import LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS
from chronicler.monitoring import InteractionLog
from chronicler.storyteller.context import retrieve_context, extract_keywords
from chronicler.storyteller.llm import stream_completion
from chronicler.storyteller.prompts import build_messages, format_context

router = APIRouter()


class AskRequest(BaseModel):
    query: str
    world_id: int


@router.post("/ask")
async def ask(body: AskRequest, request: Request):
    """Stream a storyteller response via SSE."""
    pool = request.app.state.pool

    log = InteractionLog(
        query=body.query,
        world_id=body.world_id,
        keywords=extract_keywords(body.query),
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
        max_tokens=LLM_MAX_TOKENS,
    ).start()

    # Retrieve world name
    async with pool.acquire() as conn:
        world_name = await conn.fetchval(
            "SELECT name FROM worlds WHERE id = $1", body.world_id
        )
    log.world_name = world_name

    # Build context
    records = await retrieve_context(pool, body.world_id, body.query)
    context_text = format_context(records)
    log.context_done(records, context_text)

    messages = build_messages(body.query, context_text, world_name or "the world")

    async def event_generator() -> AsyncGenerator[dict, None]:
        log.llm_start()
        try:
            async for token in stream_completion(
                messages,
                model=LLM_MODEL,
                temperature=LLM_TEMPERATURE,
                max_tokens=LLM_MAX_TOKENS,
            ):
                log.first_token()
                log.count_token(token)
                yield {"data": json.dumps({"token": token})}
        except Exception as e:
            log.finish(status="error", error=str(e))
            yield {"data": json.dumps({"error": str(e)})}
        else:
            log.finish()
        yield {"data": json.dumps({"done": True})}
        await log.flush(pool)

    return EventSourceResponse(event_generator())
