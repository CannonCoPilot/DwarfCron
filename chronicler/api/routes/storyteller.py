"""Storyteller chat endpoint — SSE streaming from Qwen3 via LiteLLM."""

import json
from typing import AsyncGenerator

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from chronicler.config import LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS
from chronicler.storyteller.context import retrieve_context
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

    # Retrieve world name
    async with pool.acquire() as conn:
        world_name = await conn.fetchval(
            "SELECT name FROM worlds WHERE id = $1", body.world_id
        )

    # Build context
    records = await retrieve_context(pool, body.world_id, body.query)
    context_text = format_context(records)
    messages = build_messages(body.query, context_text, world_name or "the world")

    async def event_generator() -> AsyncGenerator[dict, None]:
        try:
            async for token in stream_completion(
                messages,
                model=LLM_MODEL,
                temperature=LLM_TEMPERATURE,
                max_tokens=LLM_MAX_TOKENS,
            ):
                yield {"data": json.dumps({"token": token})}
        except Exception as e:
            yield {"data": json.dumps({"error": str(e)})}
        yield {"data": json.dumps({"done": True})}

    return EventSourceResponse(event_generator())
