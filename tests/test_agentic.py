"""Tests for the agentic SQL storyteller (Stage 4.3).

Tests cover:
  - SQLSafetyLayer validation and execution
  - AgenticStoryteller prompt building and tool definition
  - InteractionLog agentic extensions
  - Mode toggle routing
"""

import asyncio
import json
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chronicler.storyteller.agentic import (
    SQL_TOOL,
    AgenticStoryteller,
    SQLSafetyLayer,
    build_agentic_prompt,
)
from chronicler.monitoring import InteractionLog


def _mock_pool(conn=None):
    """Create a mock asyncpg pool with proper async context manager for acquire()."""
    if conn is None:
        conn = AsyncMock()

    @asynccontextmanager
    async def _acquire():
        yield conn

    pool = MagicMock()
    pool.acquire = _acquire
    return pool


# ===========================================================================
# SQLSafetyLayer Validation Tests
# ===========================================================================


class TestSQLSafetyValidation:
    """Test SQL query validation (no DB required)."""

    def test_valid_select(self):
        ok, err = SQLSafetyLayer.validate(
            "SELECT name FROM historical_figures WHERE world_id = 1"
        )
        assert ok is True
        assert err == ""

    def test_valid_with_cte(self):
        ok, err = SQLSafetyLayer.validate(
            "WITH top AS (SELECT * FROM hf WHERE world_id = 1) SELECT * FROM top"
        )
        assert ok is True

    def test_rejects_insert(self):
        ok, err = SQLSafetyLayer.validate(
            "INSERT INTO historical_figures (world_id, id) VALUES (1, 999)"
        )
        assert ok is False
        assert err  # caught by SELECT-only or blocked keyword check

    def test_rejects_update(self):
        ok, err = SQLSafetyLayer.validate(
            "UPDATE historical_figures SET name = 'evil' WHERE world_id = 1"
        )
        assert ok is False

    def test_rejects_delete(self):
        ok, err = SQLSafetyLayer.validate(
            "DELETE FROM historical_figures WHERE world_id = 1"
        )
        assert ok is False

    def test_rejects_drop(self):
        ok, err = SQLSafetyLayer.validate("DROP TABLE historical_figures")
        assert ok is False

    def test_rejects_missing_world_id(self):
        ok, err = SQLSafetyLayer.validate(
            "SELECT * FROM historical_figures WHERE name = 'Urist'"
        )
        assert ok is False
        assert "world_id" in err

    def test_rejects_empty(self):
        ok, err = SQLSafetyLayer.validate("")
        assert ok is False
        assert "Empty" in err

    def test_rejects_whitespace_only(self):
        ok, err = SQLSafetyLayer.validate("   ")
        assert ok is False

    def test_case_insensitive_blocking(self):
        ok, err = SQLSafetyLayer.validate(
            "select * from hf where world_id = 1; drop table hf"
        )
        assert ok is False
        assert "DROP" in err

    def test_rejects_truncate(self):
        ok, err = SQLSafetyLayer.validate(
            "TRUNCATE historical_figures"
        )
        assert ok is False

    def test_enforces_limit_when_missing(self):
        sql = "SELECT * FROM hf WHERE world_id = 1"
        result = SQLSafetyLayer._enforce_limit(sql)
        assert "LIMIT 50" in result

    def test_preserves_existing_limit(self):
        sql = "SELECT * FROM hf WHERE world_id = 1 LIMIT 10"
        result = SQLSafetyLayer._enforce_limit(sql)
        assert result == sql
        assert "LIMIT 50" not in result


# ===========================================================================
# SQLSafetyLayer Execution Tests (mocked DB)
# ===========================================================================


class TestSQLSafetyExecution:
    """Test SQL execution with mocked asyncpg pool."""

    @pytest.mark.asyncio
    async def test_execute_valid_query(self):
        """Valid query returns rows."""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[{"name": "Urist", "race": "DWARF"}])
        pool = _mock_pool(mock_conn)

        result = await SQLSafetyLayer.execute(
            "SELECT name, race FROM historical_figures WHERE world_id = 1",
            pool,
        )
        assert result["count"] == 1
        assert result["rows"][0]["name"] == "Urist"
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_execute_invalid_query(self):
        """Invalid query returns error without hitting DB."""
        mock_conn = AsyncMock()
        pool = _mock_pool(mock_conn)
        result = await SQLSafetyLayer.execute(
            "DELETE FROM hf WHERE world_id = 1",
            pool,
        )
        assert "error" in result
        assert result["count"] == 0
        mock_conn.fetch.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_timeout(self):
        """Slow query returns timeout error."""
        async def slow_fetch(*args, **kwargs):
            await asyncio.sleep(10)
            return []

        mock_conn = AsyncMock()
        mock_conn.fetch = slow_fetch
        pool = _mock_pool(mock_conn)

        result = await SQLSafetyLayer.execute(
            "SELECT * FROM history_events WHERE world_id = 1",
            pool,
        )
        assert "error" in result
        assert "timed out" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_db_error(self):
        """DB error returns error dict, doesn't raise."""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(
            side_effect=Exception("relation does not exist")
        )
        pool = _mock_pool(mock_conn)

        result = await SQLSafetyLayer.execute(
            "SELECT * FROM nonexistent WHERE world_id = 1",
            pool,
        )
        assert "error" in result
        assert "relation" in result["error"]


# ===========================================================================
# Tool Definition Tests
# ===========================================================================


class TestToolDefinition:
    """Test the SQL_TOOL definition structure."""

    def test_tool_type(self):
        assert SQL_TOOL["type"] == "function"

    def test_tool_name(self):
        assert SQL_TOOL["function"]["name"] == "query_database"

    def test_tool_has_required_params(self):
        params = SQL_TOOL["function"]["parameters"]
        assert "sql" in params["properties"]
        assert "purpose" in params["properties"]
        assert set(params["required"]) == {"sql", "purpose"}

    def test_tool_params_are_strings(self):
        props = SQL_TOOL["function"]["parameters"]["properties"]
        assert props["sql"]["type"] == "string"
        assert props["purpose"]["type"] == "string"


# ===========================================================================
# Prompt Building Tests
# ===========================================================================


class TestPromptBuilding:
    """Test the agentic system prompt construction."""

    def test_includes_narrator_persona(self):
        prompt = build_agentic_prompt(1, "Tar Thran")
        assert "Chronicler" in prompt
        assert "historian" in prompt.lower() or "narrator" in prompt.lower()

    def test_includes_schema(self):
        prompt = build_agentic_prompt(1, "Tar Thran")
        assert "historical_figures" in prompt
        assert "history_events" in prompt
        assert "world_id" in prompt

    def test_includes_world_name(self):
        prompt = build_agentic_prompt(1, "The Destined World")
        assert "The Destined World" in prompt

    def test_includes_world_id_instruction(self):
        prompt = build_agentic_prompt(42, "Test World")
        assert "world_id = 42" in prompt

    def test_includes_query_limit(self):
        prompt = build_agentic_prompt(1, "Tar Thran")
        assert "query_database" in prompt


# ===========================================================================
# InteractionLog Agentic Extensions
# ===========================================================================


class TestInteractionLogAgentic:
    """Test agentic-mode fields on InteractionLog."""

    def test_default_mode_is_keyword(self):
        log = InteractionLog(query="test")
        assert log.mode == "keyword"

    def test_agentic_mode_set(self):
        log = InteractionLog(query="test", mode="agentic")
        assert log.mode == "agentic"

    def test_add_sql_query(self):
        log = InteractionLog(query="test", mode="agentic")
        log.add_sql_query({
            "sql": "SELECT * FROM hf WHERE world_id = 1",
            "purpose": "find figures",
            "duration_ms": 42,
            "row_count": 10,
        })
        assert log.sql_rounds == 1
        assert len(log.sql_queries) == 1
        assert log.sql_queries[0]["row_count"] == 10

    def test_multiple_sql_queries(self):
        log = InteractionLog(query="test", mode="agentic")
        for i in range(3):
            log.add_sql_query({"sql": f"q{i}", "purpose": f"p{i}"})
        assert log.sql_rounds == 3
        assert len(log.sql_queries) == 3


# ===========================================================================
# Mode Toggle Tests
# ===========================================================================


class TestModeToggle:
    """Test storyteller mode routing logic."""

    def test_keyword_mode_forces_keyword(self):
        from chronicler.api.routes.storyteller import _resolve_mode
        with patch("chronicler.api.routes.storyteller.STORYTELLER_MODE", "keyword"):
            assert _resolve_mode(None) == "keyword"
            assert _resolve_mode("agentic") == "keyword"

    def test_agentic_mode_forces_agentic(self):
        from chronicler.api.routes.storyteller import _resolve_mode
        with patch("chronicler.api.routes.storyteller.STORYTELLER_MODE", "agentic"):
            assert _resolve_mode(None) == "agentic"
            assert _resolve_mode("keyword") == "agentic"

    def test_hybrid_respects_request(self):
        from chronicler.api.routes.storyteller import _resolve_mode
        with patch("chronicler.api.routes.storyteller.STORYTELLER_MODE", "hybrid"):
            assert _resolve_mode("keyword") == "keyword"
            assert _resolve_mode("agentic") == "agentic"

    def test_hybrid_defaults_to_agentic(self):
        from chronicler.api.routes.storyteller import _resolve_mode
        with patch("chronicler.api.routes.storyteller.STORYTELLER_MODE", "hybrid"):
            assert _resolve_mode(None) == "agentic"


# ===========================================================================
# AgenticStoryteller Integration Tests (mocked LLM + DB)
# ===========================================================================


class TestAgenticStoryteller:
    """Test the agent loop with mocked LLM and DB."""

    @pytest.mark.asyncio
    async def test_single_round_no_tools(self):
        """LLM responds without tool calls — yields tokens directly."""
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value="Tar Thran")
        pool = _mock_pool(mock_conn)

        with patch(
            "chronicler.storyteller.agentic.collect_with_tools",
            return_value=("The necromancer Zefon was mighty.", []),
        ):
            storyteller = AgenticStoryteller(pool, world_id=1)
            events = []
            async for event in storyteller.ask("who is the strongest necromancer?"):
                events.append(event)

        types = [e["type"] for e in events]
        assert "token" in types
        assert "done" in types
        assert events[-1]["type"] == "done"

    @pytest.mark.asyncio
    async def test_multi_round_with_tool_call(self):
        """LLM makes a tool call, then responds with narrative."""
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value="Tar Thran")
        mock_conn.fetch = AsyncMock(return_value=[
            {"name": "Zefon", "race": "HUMAN", "kill_count": 42}
        ])
        pool = _mock_pool(mock_conn)

        call_count = 0

        async def mock_collect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return ("", [{
                    "id": "call_0",
                    "function": {
                        "name": "query_database",
                        "arguments": json.dumps({
                            "sql": "SELECT name, kill_count FROM historical_figures WHERE world_id = 1 AND is_necromancer = TRUE ORDER BY kill_count DESC LIMIT 5",
                            "purpose": "find top necromancers"
                        }),
                    },
                }])
            else:
                return ("Zefon the necromancer slew 42 souls.", [])

        with patch(
            "chronicler.storyteller.agentic.collect_with_tools",
            side_effect=mock_collect,
        ):
            storyteller = AgenticStoryteller(pool, world_id=1)
            events = []
            async for event in storyteller.ask("who is the strongest necromancer?"):
                events.append(event)

        types = [e["type"] for e in events]
        assert "progress" in types
        assert "sql" in types
        assert "token" in types
        assert "done" in types

        sql_events = [e for e in events if e["type"] == "sql"]
        assert len(sql_events) == 1
        assert sql_events[0]["data"]["row_count"] == 1

    @pytest.mark.asyncio
    async def test_max_rounds_enforcement(self):
        """Agent stops after AGENTIC_MAX_ROUNDS even with continuous tool calls."""
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value="Test")
        mock_conn.fetch = AsyncMock(return_value=[])
        pool = _mock_pool(mock_conn)

        async def always_tool_call(*args, **kwargs):
            return ("partial", [{
                "id": "call",
                "function": {
                    "name": "query_database",
                    "arguments": '{"sql": "SELECT 1 WHERE world_id = 1", "purpose": "test"}',
                },
            }])

        with patch(
            "chronicler.storyteller.agentic.collect_with_tools",
            side_effect=always_tool_call,
        ), patch("chronicler.storyteller.agentic.AGENTIC_MAX_ROUNDS", 3):
            storyteller = AgenticStoryteller(pool, world_id=1)
            events = []
            async for event in storyteller.ask("infinite loop test"):
                events.append(event)

        sql_events = [e for e in events if e["type"] == "sql"]
        assert len(sql_events) == 3
        assert events[-1]["type"] == "done"

    @pytest.mark.asyncio
    async def test_sql_error_doesnt_crash(self):
        """SQL execution error is captured, doesn't crash the agent loop."""
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value="Test")
        mock_conn.fetch = AsyncMock(
            side_effect=Exception("column does not exist")
        )
        pool = _mock_pool(mock_conn)

        call_count = 0

        async def mock_collect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return ("", [{
                    "id": "call_0",
                    "function": {
                        "name": "query_database",
                        "arguments": '{"sql": "SELECT bad_col FROM hf WHERE world_id = 1", "purpose": "test"}',
                    },
                }])
            else:
                return ("I encountered an error querying.", [])

        with patch(
            "chronicler.storyteller.agentic.collect_with_tools",
            side_effect=mock_collect,
        ):
            storyteller = AgenticStoryteller(pool, world_id=1)
            events = []
            async for event in storyteller.ask("test error handling"):
                events.append(event)

        assert events[-1]["type"] == "done"
        sql_events = [e for e in events if e["type"] == "sql"]
        assert sql_events[0]["data"]["error"] is not None
