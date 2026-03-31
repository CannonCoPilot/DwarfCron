"""Agentic SQL storyteller — LLM with autonomous database exploration.

The agentic storyteller replaces hardcoded keyword routing with an LLM that
formulates its own SQL queries against the Chronicler CDM. It uses OpenAI-
compatible tool calling via LiteLLM/Ollama (Qwen3 32B).

Components:
  SQLSafetyLayer — validates and executes SQL with defense in depth
  AgenticStoryteller — multi-round agent loop yielding SSE events
"""

import asyncio
import json
import logging
import re
import time
from typing import AsyncGenerator

import asyncpg

from chronicler.config import (
    AGENTIC_MAX_ROUNDS,
    AGENTIC_MODEL,
    LLM_TEMPERATURE,
)
from chronicler.storyteller.annotated_schema import ANNOTATED_SCHEMA
from chronicler.storyteller.llm import collect_with_tools
from chronicler.storyteller.prompts import SYSTEM_PROMPT

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SQL Tool Definition (OpenAI function-calling format)
# ---------------------------------------------------------------------------

SQL_TOOL = {
    "type": "function",
    "function": {
        "name": "query_database",
        "description": (
            "Execute a read-only SQL query against the Chronicler PostgreSQL "
            "database. Returns up to 50 rows. Use this to explore world data "
            "and find information for your narrative response."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": (
                        "A read-only SELECT query. Must include a "
                        "WHERE world_id = <N> filter."
                    ),
                },
                "purpose": {
                    "type": "string",
                    "description": (
                        "Brief explanation of what you're looking for "
                        "with this query."
                    ),
                },
            },
            "required": ["sql", "purpose"],
        },
    },
}


# ---------------------------------------------------------------------------
# SQL Safety Layer
# ---------------------------------------------------------------------------

class SQLSafetyLayer:
    """Validate and execute SQL queries with defense-in-depth."""

    BLOCKED_KEYWORDS = {
        "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE",
        "CREATE", "GRANT", "REVOKE", "COPY", "EXECUTE", "DO",
    }

    MAX_ROWS = 50
    TIMEOUT_SECONDS = 5

    @classmethod
    def validate(cls, sql: str) -> tuple[bool, str]:
        """Validate a SQL query.  Returns (is_valid, error_message)."""
        stripped = sql.strip()
        if not stripped:
            return False, "Empty query"

        upper = stripped.upper()

        # Must start with SELECT (or WITH ... SELECT)
        if not (upper.startswith("SELECT") or upper.startswith("WITH")):
            return False, "Only SELECT queries are allowed"

        # Tokenize and check for blocked keywords
        tokens = set(re.findall(r"\b[A-Z_]+\b", upper))
        blocked = tokens & cls.BLOCKED_KEYWORDS
        if blocked:
            return False, f"Blocked keyword(s): {', '.join(sorted(blocked))}"

        # Must reference world_id
        if "world_id" not in sql.lower():
            return False, "Query must include world_id filter"

        return True, ""

    @classmethod
    def _enforce_limit(cls, sql: str) -> str:
        """Ensure query has a LIMIT clause."""
        if "LIMIT" not in sql.upper():
            return f"{sql.rstrip(';')} LIMIT {cls.MAX_ROWS}"
        return sql

    @classmethod
    async def execute(
        cls,
        sql: str,
        pool: asyncpg.Pool,
    ) -> dict:
        """Validate, limit, and execute a SQL query with timeout."""
        is_valid, error = cls.validate(sql)
        if not is_valid:
            return {"error": error, "rows": [], "count": 0}

        limited = cls._enforce_limit(sql)

        try:
            async with pool.acquire() as conn:
                rows = await asyncio.wait_for(
                    conn.fetch(limited),
                    timeout=cls.TIMEOUT_SECONDS,
                )
            # Convert asyncpg Records to plain dicts
            result = [dict(r) for r in rows]
            return {"rows": result, "count": len(result)}
        except asyncio.TimeoutError:
            return {"error": "Query timed out (5s limit)", "rows": [], "count": 0}
        except Exception as e:
            return {"error": str(e), "rows": [], "count": 0}


# ---------------------------------------------------------------------------
# Agentic System Prompt Builder
# ---------------------------------------------------------------------------

AGENTIC_INSTRUCTIONS = """\

## Your Capabilities
You have access to a tool called `query_database` that lets you run read-only \
SQL queries against the database described above. You may call this tool up to \
{max_rounds} times per response to gather information before composing your \
narrative.

## Process
1. Analyze the user's question to determine what data you need
2. Use `query_database` to retrieve relevant records
3. If initial results are insufficient, run follow-up queries
4. Compose a narrative response citing specific names, dates, and events
5. If records do not contain information about what is asked, say so honestly

## Guidelines
- Always cite specific records (names, years, places) from query results
- If confidence is low (<3 records found), note this to the user
- Prefer multiple targeted queries over one complex query
- For name searches, use ILIKE with '%name%' patterns
- Always include world_id = {world_id} in WHERE clauses
"""


def build_agentic_prompt(world_id: int, world_name: str) -> str:
    """Build the full system prompt for the agentic storyteller."""
    return (
        SYSTEM_PROMPT.replace("the world", world_name, 1)
        + "\n\n"
        + ANNOTATED_SCHEMA
        + "\n\n"
        + AGENTIC_INSTRUCTIONS.format(
            max_rounds=AGENTIC_MAX_ROUNDS,
            world_id=world_id,
        )
    )


# ---------------------------------------------------------------------------
# Agentic Storyteller
# ---------------------------------------------------------------------------

class AgenticStoryteller:
    """Multi-round agentic storyteller with autonomous SQL exploration."""

    def __init__(self, pool: asyncpg.Pool, world_id: int):
        self.pool = pool
        self.world_id = world_id
        self._world_name: str | None = None

    async def _get_world_name(self) -> str:
        """Fetch the world name from the database."""
        if self._world_name is None:
            async with self.pool.acquire() as conn:
                name = await conn.fetchval(
                    "SELECT name FROM worlds WHERE id = $1", self.world_id
                )
            self._world_name = name or "the world"
        return self._world_name

    async def ask(self, query: str) -> AsyncGenerator[dict, None]:
        """Run the agentic storyteller loop, yielding SSE-ready events.

        Event types:
          {"type": "progress", "data": str}  — SQL execution status
          {"type": "sql",      "data": dict} — SQL query details (for logging)
          {"type": "token",    "data": str}  — narrative text token
          {"type": "done"}                   — stream complete
        """
        world_name = await self._get_world_name()
        system_prompt = build_agentic_prompt(self.world_id, world_name)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ]

        content = ""
        for round_num in range(AGENTIC_MAX_ROUNDS):
            # Call LLM with tool support — collect full response
            content, tool_calls = await collect_with_tools(
                messages,
                model=AGENTIC_MODEL,
                temperature=LLM_TEMPERATURE,
                tools=[SQL_TOOL],
            )

            if not tool_calls:
                # No tool calls — this is the final narrative answer
                if content:
                    yield {"type": "token", "data": content}
                break

            # Process tool calls
            # First, add the assistant message with tool calls to history
            assistant_msg: dict = {"role": "assistant", "content": content or ""}
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.get("id", f"call_{round_num}_{i}"),
                    "type": "function",
                    "function": {
                        "name": tc["function"]["name"],
                        "arguments": (
                            tc["function"]["arguments"]
                            if isinstance(tc["function"]["arguments"], str)
                            else json.dumps(tc["function"]["arguments"])
                        ),
                    },
                }
                for i, tc in enumerate(tool_calls)
            ]
            messages.append(assistant_msg)

            # Execute each tool call
            for i, tc in enumerate(tool_calls):
                func = tc.get("function", {})
                tc_id = tc.get("id", f"call_{round_num}_{i}")

                # Parse arguments
                args_raw = func.get("arguments", "{}")
                if isinstance(args_raw, str):
                    try:
                        args = json.loads(args_raw)
                    except json.JSONDecodeError:
                        args = {"sql": args_raw, "purpose": "unknown"}
                else:
                    args = args_raw

                sql = args.get("sql", "")
                purpose = args.get("purpose", "")

                yield {
                    "type": "progress",
                    "data": f"Querying database... ({purpose})",
                }

                # Execute SQL
                t0 = time.monotonic()
                result = await SQLSafetyLayer.execute(sql, self.pool)
                duration_ms = int((time.monotonic() - t0) * 1000)

                yield {
                    "type": "sql",
                    "data": {
                        "sql": sql,
                        "purpose": purpose,
                        "duration_ms": duration_ms,
                        "row_count": result.get("count", 0),
                        "error": result.get("error"),
                    },
                }

                # Serialize result for LLM context — handle non-JSON-
                # serializable types (dates, UUIDs, etc.)
                result_text = json.dumps(
                    result, default=str, ensure_ascii=False
                )

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc_id,
                    "content": result_text,
                })
        else:
            # Exhausted max rounds — yield whatever content we have
            if content:
                yield {"type": "token", "data": content}

        yield {"type": "done"}
