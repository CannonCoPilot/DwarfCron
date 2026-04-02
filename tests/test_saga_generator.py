"""Tests for Stage 4.6: Fortress Saga Generator.

Tests cover:
  - Style presets definition
  - Chapter planner arc matching
  - SagaPlan serialization
  - SagaGenerator chapter context building
  - Cache integration
"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest

from chronicler.storyteller.saga_generator import (
    CHAPTER_ARCHETYPES,
    NARRATIVE_STYLE_PRESETS,
    SagaChapter,
    SagaChapterPlanner,
    SagaPlan,
    list_styles,
)


def _mock_pool(conn=None):
    if conn is None:
        conn = AsyncMock()
    pool = AsyncMock()

    @asynccontextmanager
    async def acquire():
        yield conn

    pool.acquire = acquire
    return pool, conn


# ── Style Presets ─────────────────────────────────────────────────────


class TestStylePresets:
    def test_all_presets_have_required_fields(self):
        for key, preset in NARRATIVE_STYLE_PRESETS.items():
            assert preset.name, f"{key} missing name"
            assert preset.description, f"{key} missing description"
            assert preset.system_instructions, f"{key} missing instructions"

    def test_list_styles_returns_all(self):
        styles = list_styles()
        assert len(styles) == len(NARRATIVE_STYLE_PRESETS)
        assert all("id" in s and "name" in s for s in styles)

    def test_known_presets_exist(self):
        expected = {"epic_saga", "war_correspondent", "personal_diary",
                    "academic_history", "bardic_tale", "dark_comedy"}
        assert set(NARRATIVE_STYLE_PRESETS.keys()) == expected


# ── Chapter Archetypes ────────────────────────────────────────────────


class TestChapterArchetypes:
    def test_all_archetypes_have_tone(self):
        for key, arch in CHAPTER_ARCHETYPES.items():
            assert "tone" in arch, f"{key} missing tone"

    def test_founding_is_hopeful(self):
        assert CHAPTER_ARCHETYPES["founding"]["tone"] == "hopeful"

    def test_last_stand_is_tragic(self):
        assert CHAPTER_ARCHETYPES["last_stand"]["tone"] == "tragic"


# ── SagaChapter / SagaPlan ───────────────────────────────────────────


class TestSagaPlan:
    def test_plan_serialization(self):
        chapter = SagaChapter(
            chapter_type="founding",
            title="The First Strike",
            year_start=0,
            year_end=50,
            narrative_tone="hopeful",
            arcs=[{"arc_type": "golden_age"}],
            characters=[{"hf_id": 1}],
        )
        plan = SagaPlan(
            world_id=1,
            world_name="Tar Thran",
            site_id=42,
            site_name="Girderpriced",
            chapters=[chapter],
            style="epic_saga",
        )
        d = plan.to_dict()
        assert d["world_id"] == 1
        assert d["chapter_count"] == 1
        assert d["chapters"][0]["type"] == "founding"
        assert d["chapters"][0]["title"] == "The First Strike"
        assert d["chapters"][0]["index"] == 1


# ── Chapter Planner ───────────────────────────────────────────────────


class TestSagaChapterPlanner:
    @pytest.mark.asyncio
    async def test_plans_chapters_from_arcs(self):
        pool, conn = _mock_pool()
        conn.fetchrow.side_effect = [
            {"name": "Tar Thran", "alt_name": "The Land of Dawning"},  # world
            {"min_year": 0, "max_year": 250},  # year range
        ]
        conn.fetchval.return_value = "Girderpriced"  # site name
        conn.fetch.side_effect = [
            # arcs
            [
                {"id": 1, "arc_type": "golden_age", "title": "Golden Years",
                 "start_year": 10, "end_year": 80, "key_events": [],
                 "characters": [], "resolution": "peaceful", "dramatic_weight": 5.0},
                {"id": 2, "arc_type": "siege_defense", "title": "The Siege",
                 "start_year": 100, "end_year": 110, "key_events": [],
                 "characters": [], "resolution": "survived", "dramatic_weight": 25.0},
                {"id": 3, "arc_type": "rise_and_fall", "title": "The Decline",
                 "start_year": 150, "end_year": 250, "key_events": [],
                 "characters": [], "resolution": "fell", "dramatic_weight": 40.0},
            ],
            # characters
            [],
            # fortress states
        ]

        planner = SagaChapterPlanner(pool)
        plan = await planner.plan_saga(1, site_id=42)

        assert plan.world_name == "Tar Thran"
        assert plan.site_name == "Girderpriced"
        assert len(plan.chapters) >= 3  # founding + matched arcs + epilogue
        types = [ch.chapter_type for ch in plan.chapters]
        assert "founding" in types
        assert "epilogue" in types

    @pytest.mark.asyncio
    async def test_skips_empty_chapters(self):
        pool, conn = _mock_pool()
        conn.fetchrow.side_effect = [
            {"name": "TestWorld", "alt_name": "TW"},
            {"min_year": 0, "max_year": 100},
        ]
        conn.fetchval.return_value = None
        conn.fetch.side_effect = [
            [],  # no arcs
            [],  # no characters
        ]

        planner = SagaChapterPlanner(pool)
        plan = await planner.plan_saga(1)

        # Should still have founding and epilogue
        types = [ch.chapter_type for ch in plan.chapters]
        assert "founding" in types
        assert "epilogue" in types
        # But no arc-dependent chapters
        assert "siege_and_war" not in types


# ── Saga Generator Context ───────────────────────────────────────────


class TestSagaGeneratorContext:
    @pytest.mark.asyncio
    async def test_build_chapter_messages(self):
        """Verify message structure for LLM calls."""
        from chronicler.storyteller.saga_generator import SagaGenerator

        pool, conn = _mock_pool()
        gen = SagaGenerator(pool)

        chapter = SagaChapter(
            chapter_type="founding",
            title="Bones of the Earth",
            year_start=0,
            year_end=50,
            narrative_tone="hopeful",
        )
        preset = NARRATIVE_STYLE_PRESETS["epic_saga"]
        plan = SagaPlan(
            world_id=1, world_name="Tar Thran",
            site_id=None, site_name=None,
            chapters=[chapter],
        )

        messages = gen._build_chapter_messages(
            chapter, "Some context", preset, 1, 1, plan
        )
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert "Chronicler" in messages[0]["content"]
        assert "epic" in messages[0]["content"].lower() or "saga" in messages[0]["content"].lower()
        assert messages[1]["role"] == "user"
        assert "Some context" in messages[1]["content"]
