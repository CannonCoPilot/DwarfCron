"""Tests for Stage 4.5: AI Narrative Generators.

Tests cover:
  - Cache layer (get/set with TTL)
  - World summary data gathering and prompt building
  - Obituary for dead/alive/missing HFs
  - Year-in-history data gathering
  - Highlight reel event ranking
  - LLM call mocking
"""

import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chronicler.storyteller.ai_generators import (
    _get_cached,
    _set_cached,
    generate_highlight_reel,
    generate_obituary,
    generate_world_summary,
    generate_year_in_history,
)


# ── Helpers ───────────────────────────────────────────────────────────


def _mock_pool(conn=None):
    """Create a mock asyncpg pool with proper async context manager."""
    if conn is None:
        conn = AsyncMock()
    pool = AsyncMock()

    @asynccontextmanager
    async def acquire():
        yield conn

    pool.acquire = acquire
    return pool, conn


# ── Cache Tests ───────────────────────────────────────────────────────


class TestNarrativeCache:
    @pytest.mark.asyncio
    async def test_cache_miss_returns_none(self):
        pool, conn = _mock_pool()
        conn.fetchrow.return_value = None
        result = await _get_cached(pool, 1, "world_summary", "overview")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_hit_returns_content(self):
        pool, conn = _mock_pool()
        conn.fetchrow.return_value = {
            "content": "Cached world text",
            "generated_at": datetime.now(timezone.utc),
            "ttl_hours": 168,
        }
        result = await _get_cached(pool, 1, "world_summary", "overview")
        assert result == "Cached world text"

    @pytest.mark.asyncio
    async def test_expired_cache_returns_none(self):
        pool, conn = _mock_pool()
        conn.fetchrow.return_value = {
            "content": "Old text",
            "generated_at": datetime.now(timezone.utc) - timedelta(hours=200),
            "ttl_hours": 168,
        }
        result = await _get_cached(pool, 1, "world_summary", "overview")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_cached_calls_execute(self):
        pool, conn = _mock_pool()
        await _set_cached(pool, 1, "world_summary", "overview", "content", "qwen3-32b")
        conn.execute.assert_called_once()
        args = conn.execute.call_args[0]
        assert "INSERT INTO narrative_cache" in args[0]
        assert args[1] == 1  # world_id
        assert args[4] == "content"


# ── World Summary Tests ───────────────────────────────────────────────


class TestWorldSummary:
    @pytest.mark.asyncio
    async def test_returns_cached_if_available(self):
        pool, conn = _mock_pool()
        # First call for cache check
        conn.fetchrow.return_value = {
            "content": "Cached summary",
            "generated_at": datetime.now(timezone.utc),
            "ttl_hours": 168,
        }
        result = await generate_world_summary(pool, 1)
        assert result["cached"] is True
        assert result["content"] == "Cached summary"

    @pytest.mark.asyncio
    @patch("chronicler.storyteller.ai_generators._llm_generate", return_value="LLM generated world text")
    async def test_generates_and_caches_on_miss(self, mock_llm):
        pool, conn = _mock_pool()
        # Cache miss
        conn.fetchrow.side_effect = [
            None,  # _get_cached
            {  # stats query
                "world_name": "Tar Thran", "alt_name": "The Land of Dawning",
                "hf_count": 48000, "living_hfs": 30000, "civ_count": 50,
                "site_count": 2000, "event_count": 400000, "war_count": 200,
                "max_year": 250, "artifact_count": 8000,
            },
        ]
        conn.fetch.side_effect = [
            [{"name": "Nation of Stability", "race": "dwarf", "sites": 50}],  # top civs
            [{"event_type": "hf_died", "year": 200, "narrative_weight": 9.5}],  # notable events
        ]
        conn.execute.return_value = None

        result = await generate_world_summary(pool, 1)
        assert result["cached"] is False
        assert result["content"] == "LLM generated world text"
        mock_llm.assert_called_once()

    @pytest.mark.asyncio
    @patch("chronicler.storyteller.ai_generators._llm_generate", return_value="Forced regeneration")
    async def test_force_bypasses_cache(self, mock_llm):
        pool, conn = _mock_pool()
        conn.fetchrow.return_value = {
            "world_name": "Tar Thran", "alt_name": "The Land of Dawning",
            "hf_count": 100, "living_hfs": 50, "civ_count": 5,
            "site_count": 20, "event_count": 500, "war_count": 3,
            "max_year": 100, "artifact_count": 10,
        }
        conn.fetch.side_effect = [[], []]  # empty civs and events
        conn.execute.return_value = None

        result = await generate_world_summary(pool, 1, force=True)
        assert result["cached"] is False
        mock_llm.assert_called_once()


# ── Obituary Tests ────────────────────────────────────────────────────


class TestObituary:
    @pytest.mark.asyncio
    async def test_not_found_hf(self):
        pool, conn = _mock_pool()
        conn.fetchrow.side_effect = [None, None]  # cache miss, then HF not found
        result = await generate_obituary(pool, 1, 99999)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_alive_hf_returns_error(self):
        pool, conn = _mock_pool()
        conn.fetchrow.side_effect = [
            None,  # cache miss
            {  # HF record — alive
                "name": "Urist", "race": "dwarf", "caste": "male",
                "birth_year": 100, "death_year": None, "death_cause": None,
                "associated_type": None, "kill_count": 0, "details": {},
            },
        ]
        result = await generate_obituary(pool, 1, 42)
        assert "still alive" in result.get("error", "")

    @pytest.mark.asyncio
    @patch("chronicler.storyteller.ai_generators._llm_generate", return_value="A solemn obituary")
    async def test_generates_obituary_for_dead_hf(self, mock_llm):
        pool, conn = _mock_pool()
        conn.fetchrow.side_effect = [
            None,  # cache miss
            {  # HF record — dead
                "name": "Dastot Manorhands", "race": "dwarf", "caste": "male",
                "birth_year": 100, "death_year": 256, "death_cause": "murder",
                "associated_type": "necromancer", "kill_count": 3, "details": {},
            },
        ]
        conn.fetch.side_effect = [
            [{"link_type": "spouse", "linked_name": "Aban", "linked_race": "dwarf"}],  # rels
            [{"link_type": "member", "position": "Necromancer", "entity_name": "Cult of Death"}],  # positions
            [{"event_type": "hf_died", "year": 256, "details": {}}],  # events
        ]
        conn.execute.return_value = None

        result = await generate_obituary(pool, 1, 42)
        assert result["content"] == "A solemn obituary"
        assert result["cached"] is False


# ── Year in History Tests ─────────────────────────────────────────────


class TestYearInHistory:
    @pytest.mark.asyncio
    @patch("chronicler.storyteller.ai_generators._llm_generate", return_value="Year 200 summary")
    async def test_generates_year_summary(self, mock_llm):
        pool, conn = _mock_pool()
        conn.fetchrow.return_value = None  # cache miss
        conn.fetchval.side_effect = [
            "Tar Thran",  # world name
            500,          # total events
        ]
        conn.fetch.side_effect = [
            [{"event_type": "hf_died", "cnt": 100}],  # event types
            [{"name": "Baby Dwarf", "race": "dwarf"}],  # births
            [{"name": "Old Dwarf", "race": "dwarf", "death_cause": "old age"}],  # deaths
            [{"name": "War of Hammers", "start_year": 195, "end_year": 210}],  # wars
            [{"name": "Newtown", "type": "town"}],  # sites founded
            [{"event_type": "hf_died", "details": {}, "narrative_weight": 8.5}],  # top events
        ]
        conn.execute.return_value = None

        result = await generate_year_in_history(pool, 1, 200)
        assert result["content"] == "Year 200 summary"
        assert result["year"] == 200
        assert "stats" in result


# ── Highlight Reel Tests ──────────────────────────────────────────────


class TestHighlightReel:
    @pytest.mark.asyncio
    @patch("chronicler.storyteller.ai_generators._llm_generate", return_value="Greatest moments text")
    async def test_generates_highlights(self, mock_llm):
        pool, conn = _mock_pool()
        conn.fetchrow.return_value = None  # cache miss
        conn.fetchval.return_value = "Tar Thran"  # world name
        conn.fetch.side_effect = [
            [  # top events
                {
                    "id": 1, "event_type": "hf_died", "year": 200,
                    "details": {}, "narrative_weight": 9.5,
                    "drama_score": 8.0, "emotional_tone": "tragic",
                    "site_name": "Deathgate",
                },
            ],
        ]
        conn.execute.return_value = None

        result = await generate_highlight_reel(pool, 1, top_n=20)
        assert result["content"] == "Greatest moments text"
        assert len(result["events"]) == 1
        assert result["events"][0]["rank"] == 1

    @pytest.mark.asyncio
    async def test_returns_cached_highlights(self):
        pool, conn = _mock_pool()
        conn.fetchrow.return_value = {
            "content": "Cached highlights",
            "generated_at": datetime.now(timezone.utc),
            "ttl_hours": 168,
        }
        result = await generate_highlight_reel(pool, 1)
        assert result["cached"] is True
