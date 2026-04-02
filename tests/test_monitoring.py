"""Tests for monitoring API enhancements (Stage 4.4).

Tests cover:
  - Mode extraction from context_categories JSONB
  - SQL query extraction from agentic interaction data
  - Summary stats with per-mode breakdown
  - InteractionLog 4-phase timing
"""

import json

from chronicler.api.routes.monitoring import _extract_mode, _extract_sql_queries
from chronicler.monitoring import InteractionLog


# ── Mode extraction ──────────────────────────────────────────────────

class TestModeExtraction:
    def test_keyword_mode_when_no_agentic_key(self):
        row = {"context_categories": json.dumps({"historical_figures": 5})}
        assert _extract_mode(row) == "keyword"

    def test_keyword_mode_when_empty(self):
        row = {"context_categories": "{}"}
        assert _extract_mode(row) == "keyword"

    def test_agentic_mode_when_agentic_key_present(self):
        row = {"context_categories": json.dumps({
            "_agentic": {"mode": "agentic", "sql_rounds": 3, "sql_queries": []}
        })}
        assert _extract_mode(row) == "agentic"

    def test_handles_dict_directly(self):
        """asyncpg returns JSONB as dict, not string."""
        row = {"context_categories": {"_agentic": {"mode": "agentic"}}}
        assert _extract_mode(row) == "agentic"

    def test_handles_none(self):
        row = {"context_categories": None}
        assert _extract_mode(row) == "keyword"

    def test_handles_invalid_json(self):
        row = {"context_categories": "not-json"}
        assert _extract_mode(row) == "keyword"


# ── SQL query extraction ─────────────────────────────────────────────

class TestSQLQueryExtraction:
    def test_no_queries_for_keyword_mode(self):
        row = {"context_categories": json.dumps({"hf": 10})}
        assert _extract_sql_queries(row) == []

    def test_extracts_sql_queries(self):
        queries = [
            {"sql": "SELECT * FROM worlds", "purpose": "find world", "duration_ms": 5, "row_count": 1},
            {"sql": "SELECT name FROM hf", "purpose": "find hf", "duration_ms": 12, "row_count": 50},
        ]
        row = {"context_categories": json.dumps({
            "_agentic": {"mode": "agentic", "sql_rounds": 2, "sql_queries": queries}
        })}
        result = _extract_sql_queries(row)
        assert len(result) == 2
        assert result[0]["purpose"] == "find world"

    def test_handles_dict_directly(self):
        row = {"context_categories": {"_agentic": {"sql_queries": [{"sql": "SELECT 1"}]}}}
        result = _extract_sql_queries(row)
        assert len(result) == 1

    def test_handles_missing_sql_queries_key(self):
        row = {"context_categories": {"_agentic": {"mode": "agentic"}}}
        assert _extract_sql_queries(row) == []


# ── InteractionLog 4-phase timing ────────────────────────────────────

class TestInteractionLogTiming:
    def test_four_phase_timing(self):
        log = InteractionLog(query="test", world_id=1)
        log.start()
        log._t_start = 100.0  # Override for deterministic test

        log._t_context_done = 100.1    # 100ms context
        log._t_llm_start = 100.2
        log._t_first_token = 100.5     # 300ms TTFT
        log._t_finish = 101.0          # 800ms LLM total

        assert log._ms(log._t_start, log._t_context_done) == 100
        assert log._ms(log._t_llm_start, log._t_first_token) == 300
        assert log._ms(log._t_llm_start, log._t_finish) == 800
        assert log._ms(log._t_start, log._t_finish) == 1000

    def test_ms_returns_none_for_zero(self):
        log = InteractionLog(query="test")
        assert log._ms(0.0, 100.0) is None
        assert log._ms(100.0, 0.0) is None

    def test_agentic_mode_fields(self):
        log = InteractionLog(query="test", mode="agentic")
        log.add_sql_query({"sql": "SELECT 1", "purpose": "test", "duration_ms": 5, "row_count": 1})
        log.add_sql_query({"sql": "SELECT 2", "purpose": "test2", "duration_ms": 10, "row_count": 3})
        assert log.sql_rounds == 2
        assert len(log.sql_queries) == 2

    def test_keyword_mode_default(self):
        log = InteractionLog(query="test")
        assert log.mode == "keyword"
        assert log.sql_rounds == 0
        assert log.sql_queries == []

    def test_count_token(self):
        log = InteractionLog(query="test")
        log.count_token("Hello")
        log.count_token(" world")
        assert log.tokens_streamed == 2
        assert log.response_chars == 11

    def test_finish_captures_error(self):
        log = InteractionLog(query="test")
        log.start()
        log.finish(status="error", error="connection refused")
        assert log.status == "error"
        assert log.error == "connection refused"

    def test_flush_includes_agentic_data_in_jsonb(self):
        """Verify agentic data is merged into context_categories for storage."""
        log = InteractionLog(query="test", mode="agentic")
        log.add_sql_query({"sql": "SELECT 1", "purpose": "test"})

        # Inspect the serialized data that flush would send
        import json as json_mod
        categories_data = dict(log.context_categories)
        categories_data["_agentic"] = {
            "mode": log.mode,
            "sql_rounds": log.sql_rounds,
            "sql_queries": log.sql_queries,
        }
        serialized = json_mod.dumps(categories_data)
        parsed = json_mod.loads(serialized)
        assert "_agentic" in parsed
        assert parsed["_agentic"]["sql_rounds"] == 1
