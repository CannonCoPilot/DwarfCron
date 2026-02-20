"""Async LLM streaming client via LiteLLM (OpenAI-compatible)."""

import json
from typing import AsyncGenerator

import httpx

from chronicler.config import LITELLM_URL


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
