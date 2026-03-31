"""Async LLM streaming client via LiteLLM (OpenAI-compatible)."""

import json
import logging
from typing import AsyncGenerator

import httpx

from chronicler.config import LITELLM_URL

log = logging.getLogger(__name__)


async def stream_completion(
    messages: list[dict],
    model: str = "qwen3-8b-nothink",
    temperature: float = 0.8,
    max_tokens: int = 2048,
) -> AsyncGenerator[str, None]:
    """Stream chat completion tokens from LiteLLM.

    Yields content delta strings as they arrive via SSE.
    """
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST",
            f"{LITELLM_URL}/v1/chat/completions",
            json=payload,
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data.strip() == "[DONE]":
                    return
                try:
                    chunk = json.loads(data)
                    delta = chunk["choices"][0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        yield content
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue


async def collect_with_tools(
    messages: list[dict],
    model: str = "qwen3-32b-nothink",
    temperature: float = 0.8,
    max_tokens: int = 4096,
    tools: list[dict] | None = None,
) -> tuple[str, list[dict]]:
    """Collect a full LLM response, handling tool calls.

    Unlike stream_completion which yields tokens, this collects the entire
    response to check for tool_calls before returning.

    Returns:
        (content_text, tool_calls_list) where tool_calls_list may be empty.
    """
    payload: dict = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    async with httpx.AsyncClient(timeout=180.0) as client:
        resp = await client.post(
            f"{LITELLM_URL}/v1/chat/completions",
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    choice = data.get("choices", [{}])[0]
    message = choice.get("message", {})

    content = message.get("content") or ""
    tool_calls = message.get("tool_calls") or []

    return content, tool_calls
