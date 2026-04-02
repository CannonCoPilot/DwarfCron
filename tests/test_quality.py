"""Tests for Stage 4.7: Narrative Quality & Tuning.

Tests cover:
  - Entity mention extraction
  - Year validation
  - Name matching against CDM
  - Composite quality scoring
  - AccuracyReport and QualityReport serialization
"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest

from chronicler.storyteller.quality import (
    AccuracyReport,
    FactualAccuracyChecker,
    NarrativeQualityEvaluator,
    QualityReport,
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


# ── Entity Mention Extraction ────────────────────────────────────────


class TestMentionExtraction:
    def test_extracts_year_references(self):
        checker = FactualAccuracyChecker.__new__(FactualAccuracyChecker)
        mentions = checker._extract_mentions("In Year 200, the fortress fell.")
        years = [m for m in mentions if m.mention_type == "year"]
        assert len(years) >= 1
        assert any(m.text == "200" for m in years)

    def test_extracts_capitalized_names(self):
        checker = FactualAccuracyChecker.__new__(FactualAccuracyChecker)
        mentions = checker._extract_mentions("Dastot Manorhands led the defense.")
        names = [m for m in mentions if m.mention_type == "character"]
        assert len(names) >= 1
        assert any("Dastot" in m.text for m in names)

    def test_handles_empty_text(self):
        checker = FactualAccuracyChecker.__new__(FactualAccuracyChecker)
        mentions = checker._extract_mentions("")
        assert len(mentions) == 0


# ── Accuracy Checking ────────────────────────────────────────────────


class TestAccuracyChecker:
    @pytest.mark.asyncio
    async def test_verifies_known_names(self):
        pool, conn = _mock_pool()
        conn.fetch.side_effect = [
            [{"name": "Dastot Manorhands"}],  # HF names
            [{"name": "Girderpriced"}],  # site names
            [{"name": "Nation of Stability"}],  # entity names
        ]
        conn.fetchrow.return_value = {"min_y": 0, "max_y": 300}

        checker = FactualAccuracyChecker(pool)
        report = await checker.check(
            "Dastot Manorhands defended Girderpriced in Year 256.",
            world_id=1,
        )
        assert report.verified_count > 0
        assert report.accuracy_score > 0

    @pytest.mark.asyncio
    async def test_flags_invalid_years(self):
        pool, conn = _mock_pool()
        conn.fetch.side_effect = [[], [], []]  # no known names
        conn.fetchrow.return_value = {"min_y": 0, "max_y": 300}

        checker = FactualAccuracyChecker(pool)
        report = await checker.check("In Year 9999, something happened.", world_id=1)
        assert report.hallucinated_count > 0
        assert "Year 9999" in report.hallucinated_mentions


# ── Quality Evaluation ───────────────────────────────────────────────


class TestQualityEvaluator:
    @pytest.mark.asyncio
    async def test_evaluates_good_narrative(self):
        pool, conn = _mock_pool()
        conn.fetch.side_effect = [
            [{"name": "Dastot"}],  # HF names
            [{"name": "Girderpriced"}],  # site names
            [],  # entity names
        ]
        conn.fetchrow.return_value = {"min_y": 0, "max_y": 300}

        narrative = (
            "In Year 200, the fortress of Girderpriced entered its golden age. "
            "Dastot Manorhands led the military with distinction, repelling two "
            "goblin sieges in quick succession.\n\n"
            "The following decades saw unprecedented growth. New workshops sprang "
            "up across the fortress, and the population swelled to over fifty souls. "
            "Trade caravans from the mountainhomes arrived with increasing frequency.\n\n"
            "Yet beneath the surface, cracks were forming. The necromancer cult "
            "grew in power, and the dead began to stir in the catacombs below."
        )

        evaluator = NarrativeQualityEvaluator(pool)
        report = await evaluator.evaluate(narrative, world_id=1)

        assert report.word_count > 50
        assert report.paragraph_count == 3
        assert report.has_specific_names is True
        assert report.has_specific_dates is True
        assert report.composite_score > 50

    @pytest.mark.asyncio
    async def test_evaluates_poor_narrative(self):
        pool, conn = _mock_pool()
        conn.fetch.side_effect = [[], [], []]  # no known names
        conn.fetchrow.return_value = {"min_y": 0, "max_y": 300}

        evaluator = NarrativeQualityEvaluator(pool)
        report = await evaluator.evaluate("Stuff happened.", world_id=1)

        assert report.word_count < 50
        assert report.composite_score < 50


# ── Report Serialization ─────────────────────────────────────────────


class TestReportSerialization:
    def test_accuracy_report_to_dict(self):
        report = AccuracyReport(
            accuracy_score=85.5,
            verified_count=10,
            hallucinated_count=2,
            unverifiable_count=3,
            total_mentions=15,
        )
        d = report.to_dict()
        assert d["accuracy_score"] == 85.5
        assert d["verified"] == 10

    def test_quality_report_to_dict(self):
        report = QualityReport(
            word_count=200,
            sentence_count=10,
            avg_sentence_length=20.0,
            paragraph_count=3,
            composite_score=75.0,
        )
        d = report.to_dict()
        assert d["word_count"] == 200
        assert d["composite_score"] == 75.0
