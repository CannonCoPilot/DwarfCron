"""Stage 4.6: Fortress Saga Generator.

Multi-chapter narrative generation from pre-processed narrative data (arcs,
clusters, character profiles, state snapshots). The crown jewel of Phase 4.

Architecture:
  StylePreset       — narrative voice/tone configuration
  SagaChapter       — data container for a planned chapter
  SagaChapterPlanner— plans chapter structure from arcs + state
  SagaGenerator     — orchestrates LLM generation per chapter
"""

import json
import logging
import time
from dataclasses import dataclass, field
from typing import AsyncGenerator

import asyncpg

from chronicler.config import AGENTIC_MODEL, LLM_TEMPERATURE
from chronicler.storyteller.ai_generators import _get_cached, _set_cached
from chronicler.storyteller.llm import stream_completion, collect_with_tools

log = logging.getLogger(__name__)

# Ticks per year in DF (403,200 = 12 months * 28 days * 1200 ticks)
TICKS_PER_YEAR = 403200


# ── Style Presets (Stage 4.7 content, needed by 4.6) ─────────────────


@dataclass
class StylePreset:
    name: str
    description: str
    system_instructions: str
    vocabulary_hints: list[str] = field(default_factory=list)


NARRATIVE_STYLE_PRESETS = {
    "epic_saga": StylePreset(
        name="Epic Saga",
        description="Tolkien-esque high fantasy prose",
        system_instructions=(
            "Write in the style of a grand epic saga. Use elevated language, "
            "dramatic pacing, and sweeping descriptions. Treat dwarves as heroic "
            "figures in a mythic narrative. Deaths should be dramatic, battles "
            "sweeping, and quiet moments should carry weight."
        ),
        vocabulary_hints=["thus", "ere", "fell", "smote", "wrought"],
    ),
    "war_correspondent": StylePreset(
        name="War Correspondent",
        description="Journalistic, factual, AP-style reporting",
        system_instructions=(
            "Write as a war correspondent embedded in the fortress. Use clear, "
            "factual prose with specific numbers and dates. Quote announcements "
            "directly. Report on casualties with clinical precision but human "
            "empathy. Include logistics (food stores, military strength) as context."
        ),
    ),
    "personal_diary": StylePreset(
        name="Personal Diary",
        description="First-person journal entries from a fortress dwarf",
        system_instructions=(
            "Write as diary entries from a dwarf living in the fortress. Use "
            "first-person perspective, colloquial language, personal observations. "
            "Express emotions about events. Worry about food, complain about the "
            "weather, mourn the fallen."
        ),
    ),
    "academic_history": StylePreset(
        name="Academic History",
        description="Dry, scholarly historical analysis",
        system_instructions=(
            "Write as a scholarly historian analyzing the fortress. Use formal "
            "academic prose, cite specific dates and figures, discuss causes and "
            "effects. Maintain analytical distance."
        ),
    ),
    "bardic_tale": StylePreset(
        name="Bardic Tale",
        description="Oral tradition storytelling with rhythm and repetition",
        system_instructions=(
            "Write as a bard telling the tale around a fire. Use rhythmic prose, "
            "repetition for emphasis, direct dialogue, audience address. Make "
            "heroes larger than life and villains terrifying."
        ),
    ),
    "dark_comedy": StylePreset(
        name="Dark Comedy",
        description="Ironic, absurdist, gallows humor",
        system_instructions=(
            "Write with dry, ironic humor in the style of Pratchett or Adams. "
            "Find the absurdity in fortress life. Treat tragedy with understated "
            "wit. The fortress is simultaneously heroic and ridiculous."
        ),
    ),
}


# ── Data Types ────────────────────────────────────────────────────────


@dataclass
class SagaChapter:
    chapter_type: str
    title: str | None
    year_start: int
    year_end: int
    narrative_tone: str
    arcs: list[dict] = field(default_factory=list)
    characters: list[dict] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)
    state_snapshot: dict = field(default_factory=dict)
    content: str | None = None  # Filled after generation


@dataclass
class SagaPlan:
    world_id: int
    world_name: str
    site_id: int | None
    site_name: str | None
    chapters: list[SagaChapter]
    style: str = "epic_saga"

    def to_dict(self) -> dict:
        return {
            "world_id": self.world_id,
            "world_name": self.world_name,
            "site_id": self.site_id,
            "site_name": self.site_name,
            "style": self.style,
            "chapter_count": len(self.chapters),
            "chapters": [
                {
                    "index": i + 1,
                    "type": ch.chapter_type,
                    "title": ch.title,
                    "year_start": ch.year_start,
                    "year_end": ch.year_end,
                    "tone": ch.narrative_tone,
                    "arc_count": len(ch.arcs),
                    "character_count": len(ch.characters),
                    "event_count": len(ch.events),
                    "content": ch.content,
                }
                for i, ch in enumerate(self.chapters)
            ],
        }


# ── Chapter Type Mapping ──────────────────────────────────────────────

# Maps chapter types to arc types and tones
CHAPTER_ARCHETYPES = {
    "founding": {"tone": "hopeful", "arc_types": {"golden_age"}, "position": "start"},
    "golden_age": {"tone": "triumphant", "arc_types": {"golden_age"}, "position": "early"},
    "first_crisis": {"tone": "tense", "arc_types": {"megabeast_attack", "siege_defense"}, "position": "early"},
    "rise_to_power": {"tone": "ambitious", "arc_types": {"rise_and_fall"}, "position": "middle"},
    "siege_and_war": {"tone": "desperate", "arc_types": {"siege_defense"}, "position": "middle"},
    "decline": {"tone": "melancholy", "arc_types": {"rise_and_fall"}, "position": "late"},
    "last_stand": {"tone": "tragic", "arc_types": {"megabeast_attack", "siege_defense"}, "position": "late"},
    "epilogue": {"tone": "reflective", "arc_types": set(), "position": "end"},
}


# ── Saga Chapter Planner ─────────────────────────────────────────────


class SagaChapterPlanner:
    """Plans chapter structure from narrative arcs and world data."""

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def plan_saga(
        self,
        world_id: int,
        site_id: int | None = None,
        style: str = "epic_saga",
    ) -> SagaPlan:
        """Generate a chapter plan from narrative data."""
        async with self.pool.acquire() as conn:
            # World info
            world = await conn.fetchrow(
                "SELECT name, alt_name FROM worlds WHERE id = $1", world_id
            )
            world_name = world["name"] if world else "Unknown World"

            # Site info (if fortress-specific)
            site_name = None
            if site_id:
                site_name = await conn.fetchval(
                    "SELECT name FROM sites WHERE world_id = $1 AND id = $2",
                    world_id, site_id,
                )

            # Load arcs (sorted by time)
            arcs = await conn.fetch("""
                SELECT id, arc_type, title,
                       start_tick / $2 AS start_year,
                       end_tick / $2 AS end_year,
                       key_events, characters, resolution, dramatic_weight
                FROM narrative_arcs
                WHERE world_id = $1
                ORDER BY dramatic_weight DESC
                LIMIT 100
            """, world_id, TICKS_PER_YEAR)

            # Get year range
            year_range = await conn.fetchrow("""
                SELECT MIN(year) as min_year, MAX(year) as max_year
                FROM history_events WHERE world_id = $1
            """, world_id)

            # Load top characters
            characters = await conn.fetch("""
                SELECT hf_id, content, generated_at
                FROM character_narratives
                WHERE world_id = $1
                ORDER BY generated_at DESC
                LIMIT 20
            """, world_id)

        arcs_list = [dict(a) for a in arcs]
        chars_list = [dict(c) for c in characters]
        min_year = year_range["min_year"] or 0
        max_year = year_range["max_year"] or 250
        total_span = max(max_year - min_year, 1)

        # Plan chapters based on available arcs
        chapters = []
        for ch_type, archetype in CHAPTER_ARCHETYPES.items():
            matching_arcs = [
                a for a in arcs_list
                if a["arc_type"] in archetype["arc_types"]
            ]

            # Determine year range for this chapter
            pos = archetype["position"]
            if pos == "start":
                yr_start, yr_end = min_year, min_year + total_span // 5
            elif pos == "early":
                yr_start, yr_end = min_year + total_span // 5, min_year + 2 * total_span // 5
            elif pos == "middle":
                yr_start, yr_end = min_year + 2 * total_span // 5, min_year + 3 * total_span // 5
            elif pos == "late":
                yr_start, yr_end = min_year + 3 * total_span // 5, max_year
            else:  # end
                yr_start, yr_end = max_year - total_span // 10, max_year

            # Skip empty chapters (except founding and epilogue)
            if not matching_arcs and ch_type not in ("founding", "epilogue"):
                continue

            # Select relevant arcs (top by weight, within time range)
            chapter_arcs = sorted(
                [a for a in matching_arcs if (a.get("start_year") or 0) <= yr_end],
                key=lambda a: a.get("dramatic_weight", 0),
                reverse=True,
            )[:5]

            # Select characters involved in these arcs
            arc_char_ids = set()
            for a in chapter_arcs:
                chars_data = a.get("characters") or []
                if isinstance(chars_data, str):
                    try:
                        chars_data = json.loads(chars_data)
                    except (json.JSONDecodeError, ValueError):
                        chars_data = []
                if isinstance(chars_data, list):
                    arc_char_ids.update(chars_data)

            chapter_chars = [
                c for c in chars_list
                if c.get("hf_id") in arc_char_ids
            ][:5]

            chapters.append(SagaChapter(
                chapter_type=ch_type,
                title=None,  # Generated later by LLM
                year_start=yr_start,
                year_end=yr_end,
                narrative_tone=archetype["tone"],
                arcs=chapter_arcs,
                characters=chapter_chars,
            ))

        return SagaPlan(
            world_id=world_id,
            world_name=world_name,
            site_id=site_id,
            site_name=site_name,
            chapters=chapters,
            style=style,
        )


# ── Saga Generator ───────────────────────────────────────────────────


class SagaGenerator:
    """Orchestrates multi-chapter saga generation via LLM."""

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
        self.planner = SagaChapterPlanner(pool)

    async def generate_saga(
        self,
        world_id: int,
        site_id: int | None = None,
        style: str = "epic_saga",
        force: bool = False,
    ) -> dict:
        """Generate complete fortress saga. Returns plan with content."""
        cache_key = f"site_{site_id or 'world'}_{style}"
        if not force:
            cached = await _get_cached(self.pool, world_id, "saga", cache_key)
            if cached:
                try:
                    return {"cached": True, **json.loads(cached)}
                except (json.JSONDecodeError, ValueError):
                    pass

        # Plan the saga
        plan = await self.planner.plan_saga(world_id, site_id, style)

        # Generate each chapter
        preset = NARRATIVE_STYLE_PRESETS.get(style, NARRATIVE_STYLE_PRESETS["epic_saga"])
        total_t0 = time.monotonic()

        for i, chapter in enumerate(plan.chapters):
            context = await self._build_chapter_context(
                world_id, chapter, plan.world_name, plan.site_name,
            )

            # Generate title
            title_prompt = (
                f"Generate a short, evocative chapter title (3-6 words) for a "
                f"{chapter.narrative_tone} chapter about {chapter.chapter_type.replace('_', ' ')} "
                f"covering years {chapter.year_start}-{chapter.year_end} in {plan.world_name}. "
                f"Return ONLY the title, no quotes or explanation."
            )
            title, _ = await collect_with_tools(
                [{"role": "user", "content": title_prompt}],
                model=AGENTIC_MODEL, temperature=0.9, max_tokens=50,
            )
            chapter.title = title.strip().strip('"').strip("'")

            # Generate chapter content
            messages = self._build_chapter_messages(
                chapter, context, preset, i + 1, len(plan.chapters), plan,
            )
            content, _ = await collect_with_tools(
                messages, model=AGENTIC_MODEL,
                temperature=LLM_TEMPERATURE, max_tokens=2048,
            )
            chapter.content = content

        total_ms = round((time.monotonic() - total_t0) * 1000)
        result = plan.to_dict()
        result["latency_ms"] = total_ms
        result["model"] = AGENTIC_MODEL
        result["cached"] = False

        # Cache the result
        await _set_cached(
            self.pool, world_id, "saga", cache_key,
            json.dumps(result, default=str), AGENTIC_MODEL,
        )

        return result

    async def generate_chapter_stream(
        self,
        world_id: int,
        chapter_index: int,
        site_id: int | None = None,
        style: str = "epic_saga",
    ) -> AsyncGenerator[str, None]:
        """Stream a single saga chapter (for SSE)."""
        plan = await self.planner.plan_saga(world_id, site_id, style)
        if chapter_index < 0 or chapter_index >= len(plan.chapters):
            yield "Chapter not found."
            return

        chapter = plan.chapters[chapter_index]
        preset = NARRATIVE_STYLE_PRESETS.get(style, NARRATIVE_STYLE_PRESETS["epic_saga"])
        context = await self._build_chapter_context(
            world_id, chapter, plan.world_name, plan.site_name,
        )
        messages = self._build_chapter_messages(
            chapter, context, preset, chapter_index + 1, len(plan.chapters), plan,
        )

        async for token in stream_completion(
            messages, model=AGENTIC_MODEL,
            temperature=LLM_TEMPERATURE, max_tokens=2048,
        ):
            yield token

    async def _build_chapter_context(
        self, world_id: int, chapter: SagaChapter,
        world_name: str, site_name: str | None,
    ) -> str:
        """Gather contextual data for a chapter from the DB."""
        parts = []
        async with self.pool.acquire() as conn:
            # Key events in this time range
            events = await conn.fetch("""
                SELECT he.event_type, he.year, he.details,
                       ne.narrative_weight, ne.emotional_tone
                FROM narrative_events ne
                JOIN history_events he ON he.world_id = ne.world_id AND he.id = ne.event_id
                WHERE ne.world_id = $1 AND he.year BETWEEN $2 AND $3
                ORDER BY ne.narrative_weight DESC
                LIMIT 30
            """, world_id, chapter.year_start, chapter.year_end)

            if events:
                parts.append("Key events:")
                for e in events:
                    parts.append(
                        f"  Year {e['year']}: {e['event_type']} "
                        f"(tone: {e['emotional_tone']}, weight: {e['narrative_weight']:.1f})"
                    )

            # Population/death stats
            pop_stats = await conn.fetchrow("""
                SELECT
                    count(*) FILTER (WHERE birth_year BETWEEN $2 AND $3) as births,
                    count(*) FILTER (WHERE death_year BETWEEN $2 AND $3) as deaths,
                    count(*) FILTER (WHERE death_year IS NULL AND birth_year <= $3) as living
                FROM historical_figures
                WHERE world_id = $1
            """, world_id, chapter.year_start, chapter.year_end)

            if pop_stats:
                parts.append(f"\nPopulation: {pop_stats['living']:,} living, "
                             f"{pop_stats['births']:,} born, {pop_stats['deaths']:,} died "
                             f"(years {chapter.year_start}-{chapter.year_end})")

            # Active wars
            wars = await conn.fetch("""
                SELECT name, start_year, end_year
                FROM history_event_collections
                WHERE world_id = $1 AND type = 'war'
                  AND start_year <= $3 AND (end_year IS NULL OR end_year >= $2)
                LIMIT 5
            """, world_id, chapter.year_start, chapter.year_end)

            if wars:
                parts.append("\nActive wars:")
                for w in wars:
                    parts.append(f"  {w['name']} ({w['start_year']}-{w['end_year'] or 'ongoing'})")

        # Include arc summaries
        if chapter.arcs:
            parts.append("\nNarrative arcs:")
            for a in chapter.arcs:
                parts.append(
                    f"  {a.get('arc_type', '?')}: {a.get('title', 'untitled')} "
                    f"(weight: {a.get('dramatic_weight', 0):.1f}, "
                    f"resolution: {a.get('resolution', 'unknown')})"
                )

        # Include character profiles
        if chapter.characters:
            parts.append("\nKey characters:")
            for c in chapter.characters:
                content = c.get("content", "")
                if isinstance(content, str) and len(content) > 200:
                    content = content[:200] + "..."
                parts.append(f"  HF {c.get('hf_id', '?')}: {content}")

        return "\n".join(parts) if parts else "Limited data available for this period."

    def _build_chapter_messages(
        self, chapter: SagaChapter, context: str,
        preset: StylePreset, chapter_num: int, total_chapters: int,
        plan: SagaPlan,
    ) -> list[dict]:
        """Build LLM messages for chapter generation."""
        location = plan.site_name or plan.world_name

        system = (
            f"You are the Chronicler, a master storyteller recording the history "
            f"of {plan.world_name}.\n\n"
            f"{preset.system_instructions}\n\n"
            f"You are writing Chapter {chapter_num} of {total_chapters}: "
            f'"{chapter.title or chapter.chapter_type.replace("_", " ").title()}" '
            f"of the saga of {location}.\n"
            f"Narrative tone: {chapter.narrative_tone}\n"
            f"Time period: Year {chapter.year_start} to Year {chapter.year_end}\n\n"
            f"IMPORTANT: Only include facts present in the context below. Do not "
            f"invent events, characters, or details not supported by the data. "
            f"If information is sparse, let the narrative reflect that — silence "
            f"and mystery are powerful storytelling tools."
        )

        user = (
            f"Write this chapter using the following data:\n\n"
            f"{context}\n\n"
            f"Write a compelling narrative chapter of 3-5 paragraphs. Include specific "
            f"names, dates, and details from the data. Use vivid prose appropriate to "
            f"the {preset.name} style."
        )

        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]


# ── Public API ────────────────────────────────────────────────────────


async def plan_saga(
    pool: asyncpg.Pool, world_id: int,
    site_id: int | None = None, style: str = "epic_saga",
) -> dict:
    """Plan a saga without generating content. Returns chapter outline."""
    planner = SagaChapterPlanner(pool)
    plan = await planner.plan_saga(world_id, site_id, style)
    return plan.to_dict()


async def generate_saga(
    pool: asyncpg.Pool, world_id: int,
    site_id: int | None = None, style: str = "epic_saga",
    force: bool = False,
) -> dict:
    """Generate a complete fortress saga with all chapters."""
    generator = SagaGenerator(pool)
    return await generator.generate_saga(world_id, site_id, style, force)


def list_styles() -> list[dict]:
    """List available narrative style presets."""
    return [
        {"id": k, "name": v.name, "description": v.description}
        for k, v in NARRATIVE_STYLE_PRESETS.items()
    ]
