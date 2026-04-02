"""Stage 4.7: Narrative Quality & Tuning.

Factual accuracy checking and quality evaluation for generated narratives.

Components:
  FactualAccuracyChecker — validates entity mentions against CDM data
  NarrativeQualityEvaluator — composite quality scoring
"""

import logging
import re
import time
from dataclasses import dataclass, field

import asyncpg

log = logging.getLogger(__name__)


# ── Factual Accuracy Checker ─────────────────────────────────────────


@dataclass
class EntityMention:
    text: str
    mention_type: str  # 'character', 'site', 'entity', 'year'
    verified: bool = False


@dataclass
class AccuracyReport:
    accuracy_score: float  # 0-100
    verified_count: int
    hallucinated_count: int
    unverifiable_count: int
    total_mentions: int
    hallucinated_mentions: list[str] = field(default_factory=list)
    check_duration_ms: int = 0

    def to_dict(self) -> dict:
        return {
            "accuracy_score": round(self.accuracy_score, 1),
            "verified": self.verified_count,
            "hallucinated": self.hallucinated_count,
            "unverifiable": self.unverifiable_count,
            "total_mentions": self.total_mentions,
            "hallucinated_mentions": self.hallucinated_mentions[:20],
            "check_duration_ms": self.check_duration_ms,
        }


class FactualAccuracyChecker:
    """Validate generated narratives against CDM data."""

    # Patterns to extract potential entity references
    # Year references: "Year 123", "in 456", "year 789"
    YEAR_PATTERN = re.compile(r"\b[Yy]ear\s+(\d+)\b|\bin\s+(\d{1,4})\b")
    # Capitalized names (2+ words): "Urist McBuilder", "The Dark Fortress"
    NAME_PATTERN = re.compile(r"(?:(?:[A-Z][a-z]+)\s+){1,3}(?:[A-Z][a-z]+)")

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
        self._name_cache: dict[int, set[str]] = {}

    async def _load_name_cache(self, world_id: int) -> set[str]:
        """Load all known entity names for a world."""
        if world_id in self._name_cache:
            return self._name_cache[world_id]

        names = set()
        async with self.pool.acquire() as conn:
            # HF names
            rows = await conn.fetch(
                "SELECT DISTINCT name FROM historical_figures WHERE world_id = $1 AND name IS NOT NULL",
                world_id,
            )
            names.update(r["name"] for r in rows)

            # Site names
            rows = await conn.fetch(
                "SELECT DISTINCT name FROM sites WHERE world_id = $1 AND name IS NOT NULL",
                world_id,
            )
            names.update(r["name"] for r in rows)

            # Entity names
            rows = await conn.fetch(
                "SELECT DISTINCT name FROM entities WHERE world_id = $1 AND name IS NOT NULL",
                world_id,
            )
            names.update(r["name"] for r in rows)

        self._name_cache[world_id] = names
        return names

    async def _get_year_range(self, world_id: int) -> tuple[int, int]:
        """Get valid year range for the world."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT MIN(year) as min_y, MAX(year) as max_y FROM history_events WHERE world_id = $1",
                world_id,
            )
        return (row["min_y"] or 0, row["max_y"] or 9999) if row else (0, 9999)

    def _extract_mentions(self, text: str) -> list[EntityMention]:
        """Extract potential entity mentions from narrative text."""
        mentions = []

        # Extract year references
        for match in self.YEAR_PATTERN.finditer(text):
            year_str = match.group(1) or match.group(2)
            if year_str:
                mentions.append(EntityMention(
                    text=year_str, mention_type="year",
                ))

        # Extract name references
        for match in self.NAME_PATTERN.finditer(text):
            name = match.group(0)
            # Filter common English phrases
            if name.lower() not in {
                "the great", "the dark", "the first", "the last",
                "in the", "of the", "at the", "from the",
            }:
                mentions.append(EntityMention(
                    text=name, mention_type="character",
                ))

        return mentions

    async def check(self, narrative_text: str, world_id: int) -> AccuracyReport:
        """Check narrative for factual accuracy against CDM data."""
        t0 = time.monotonic()

        mentions = self._extract_mentions(narrative_text)
        known_names = await self._load_name_cache(world_id)
        min_year, max_year = await self._get_year_range(world_id)

        verified = 0
        hallucinated = 0
        unverifiable = 0
        hallucinated_list = []

        for mention in mentions:
            if mention.mention_type == "year":
                year = int(mention.text)
                if min_year <= year <= max_year:
                    verified += 1
                    mention.verified = True
                else:
                    hallucinated += 1
                    hallucinated_list.append(f"Year {mention.text}")
            elif mention.mention_type == "character":
                # Check if name (or part of name) matches known entities
                if any(mention.text.lower() in n.lower() for n in known_names):
                    verified += 1
                    mention.verified = True
                else:
                    # Could be a valid reference we don't recognize
                    unverifiable += 1

        total = verified + hallucinated + unverifiable
        score = (verified / max(verified + hallucinated, 1)) * 100

        duration = round((time.monotonic() - t0) * 1000)

        return AccuracyReport(
            accuracy_score=score,
            verified_count=verified,
            hallucinated_count=hallucinated,
            unverifiable_count=unverifiable,
            total_mentions=total,
            hallucinated_mentions=hallucinated_list,
            check_duration_ms=duration,
        )


# ── Narrative Quality Evaluator ──────────────────────────────────────


@dataclass
class QualityReport:
    """Composite quality assessment of a generated narrative."""
    accuracy: AccuracyReport | None = None
    word_count: int = 0
    sentence_count: int = 0
    avg_sentence_length: float = 0.0
    paragraph_count: int = 0
    has_specific_names: bool = False
    has_specific_dates: bool = False
    composite_score: float = 0.0  # 0-100

    def to_dict(self) -> dict:
        return {
            "composite_score": round(self.composite_score, 1),
            "word_count": self.word_count,
            "sentence_count": self.sentence_count,
            "avg_sentence_length": round(self.avg_sentence_length, 1),
            "paragraph_count": self.paragraph_count,
            "has_specific_names": self.has_specific_names,
            "has_specific_dates": self.has_specific_dates,
            "accuracy": self.accuracy.to_dict() if self.accuracy else None,
        }


class NarrativeQualityEvaluator:
    """Evaluate narrative quality across multiple dimensions."""

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
        self.accuracy_checker = FactualAccuracyChecker(pool)

    async def evaluate(self, narrative_text: str, world_id: int) -> QualityReport:
        """Run full quality evaluation."""
        report = QualityReport()

        # Basic text metrics
        words = narrative_text.split()
        report.word_count = len(words)

        sentences = re.split(r'[.!?]+', narrative_text)
        sentences = [s.strip() for s in sentences if s.strip()]
        report.sentence_count = len(sentences)
        report.avg_sentence_length = (
            report.word_count / max(report.sentence_count, 1)
        )

        paragraphs = [p.strip() for p in narrative_text.split("\n\n") if p.strip()]
        report.paragraph_count = len(paragraphs)

        # Specificity checks
        report.has_specific_names = bool(
            FactualAccuracyChecker.NAME_PATTERN.search(narrative_text)
        )
        report.has_specific_dates = bool(
            FactualAccuracyChecker.YEAR_PATTERN.search(narrative_text)
        )

        # Factual accuracy
        report.accuracy = await self.accuracy_checker.check(narrative_text, world_id)

        # Composite score (weighted)
        scores = []
        # Accuracy (40% weight)
        scores.append(report.accuracy.accuracy_score * 0.4)
        # Length appropriateness (20% weight): ideal 200-800 words
        if 200 <= report.word_count <= 800:
            scores.append(20.0)
        elif report.word_count < 50:
            scores.append(0.0)
        else:
            scores.append(10.0)
        # Specificity (20% weight)
        spec_score = 0.0
        if report.has_specific_names:
            spec_score += 10.0
        if report.has_specific_dates:
            spec_score += 10.0
        scores.append(spec_score)
        # Structure (20% weight): multiple paragraphs
        if report.paragraph_count >= 3:
            scores.append(20.0)
        elif report.paragraph_count >= 2:
            scores.append(15.0)
        else:
            scores.append(5.0)

        report.composite_score = sum(scores)
        return report


# ── Public API ────────────────────────────────────────────────────────


async def check_accuracy(
    pool: asyncpg.Pool, narrative_text: str, world_id: int,
) -> dict:
    """Check factual accuracy of a narrative. Returns AccuracyReport dict."""
    checker = FactualAccuracyChecker(pool)
    report = await checker.check(narrative_text, world_id)
    return report.to_dict()


async def evaluate_quality(
    pool: asyncpg.Pool, narrative_text: str, world_id: int,
) -> dict:
    """Full quality evaluation. Returns QualityReport dict."""
    evaluator = NarrativeQualityEvaluator(pool)
    report = await evaluator.evaluate(narrative_text, world_id)
    return report.to_dict()
