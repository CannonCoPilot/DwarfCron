"""Interaction monitoring — logs every LLM call with timing + token counts."""

import time
from dataclasses import dataclass, field

import asyncpg


@dataclass
class InteractionLog:
    """Tracks a single storyteller interaction through its lifecycle.

    Timing is split into 4 phases:
      1. Context retrieval (DB queries)
      2. Time to first token (TTFT — LLM warmup)
      3. LLM streaming (token generation)
      4. Total wall time (start to finish)
    """

    query: str
    world_id: int | None = None
    world_name: str | None = None
    keywords: list[str] = field(default_factory=list)
    context_records: int = 0
    context_chars: int = 0
    context_categories: dict[str, int] = field(default_factory=dict)
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    tokens_streamed: int = 0
    response_chars: int = 0
    status: str = "ok"
    error: str | None = None

    # Internal timing (monotonic nanoseconds)
    _t_start: float = 0.0
    _t_context_done: float = 0.0
    _t_llm_start: float = 0.0
    _t_first_token: float = 0.0
    _t_finish: float = 0.0

    def start(self) -> "InteractionLog":
        """Mark the beginning of the interaction."""
        self._t_start = time.monotonic()
        return self

    def context_done(self, records: list[dict], context_text: str) -> None:
        """Mark context retrieval complete and capture stats."""
        self._t_context_done = time.monotonic()
        self.context_records = len(records)
        self.context_chars = len(context_text)
        cats: dict[str, int] = {}
        for r in records:
            cat = r.get("category", "unknown")
            cats[cat] = cats.get(cat, 0) + 1
        self.context_categories = cats

    def llm_start(self) -> None:
        """Mark the start of the LLM request."""
        self._t_llm_start = time.monotonic()

    def first_token(self) -> None:
        """Mark receipt of the first streamed token."""
        if self._t_first_token == 0.0:
            self._t_first_token = time.monotonic()

    def count_token(self, text: str) -> None:
        """Count a streamed token chunk."""
        self.tokens_streamed += 1
        self.response_chars += len(text)

    def finish(self, status: str = "ok", error: str | None = None) -> None:
        """Mark the interaction complete."""
        self._t_finish = time.monotonic()
        self.status = status
        if error:
            self.error = error

    def _ms(self, start: float, end: float) -> int | None:
        """Convert a monotonic interval to milliseconds."""
        if start == 0.0 or end == 0.0:
            return None
        return int((end - start) * 1000)

    async def flush(self, pool: asyncpg.Pool) -> None:
        """INSERT this interaction's metrics into storyteller_log.

        Called after the SSE stream completes — zero user-facing latency.
        """
        import json

        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO storyteller_log (
                        query, world_id, world_name, keywords,
                        context_records, context_chars, context_categories,
                        model, temperature, max_tokens,
                        tokens_streamed, response_chars,
                        context_latency_ms, first_token_ms,
                        llm_latency_ms, total_latency_ms,
                        status, error
                    ) VALUES (
                        $1, $2, $3, $4,
                        $5, $6, $7::jsonb,
                        $8, $9, $10,
                        $11, $12,
                        $13, $14, $15, $16,
                        $17, $18
                    )
                    """,
                    self.query,
                    self.world_id,
                    self.world_name,
                    self.keywords,
                    self.context_records,
                    self.context_chars,
                    json.dumps(self.context_categories),
                    self.model,
                    self.temperature,
                    self.max_tokens,
                    self.tokens_streamed,
                    self.response_chars,
                    self._ms(self._t_start, self._t_context_done),
                    self._ms(self._t_llm_start, self._t_first_token),
                    self._ms(self._t_llm_start, self._t_finish),
                    self._ms(self._t_start, self._t_finish),
                    self.status,
                    self.error,
                )
        except Exception:
            pass  # Monitoring must never break the user experience
