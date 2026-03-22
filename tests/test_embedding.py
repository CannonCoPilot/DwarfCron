"""Tests for Stage 3.4: Embedding pipelines."""

import hashlib

import pytest

from chronicler.embedding.extractors import (
    extract_hf, extract_event, extract_site, extract_entity,
    extract_artifact, extract_written_content, extract_art_form,
    extract_unit, extract_announcement,
    BATCH_ENTITY_TYPES, LIVE_ENTITY_TYPES,
)
from chronicler.embedding.pipeline import chunk_text, _hash


# ═══════════════════════════════════════════════════════════════════════
# Unit tests — chunking
# ═══════════════════════════════════════════════════════════════════════

class TestChunking:
    def test_empty_text(self):
        assert chunk_text("") == []

    def test_short_text(self):
        chunks = chunk_text("hello world")
        assert len(chunks) == 1
        assert chunks[0]["chunk_index"] == 0
        assert chunks[0]["chunk_text"] == "hello world"
        assert len(chunks[0]["content_hash"]) == 16

    def test_long_text_splits(self):
        text = "A" * 3000  # > 2048 max_chars
        chunks = chunk_text(text)
        assert len(chunks) >= 2
        assert chunks[0]["chunk_index"] == 0
        assert chunks[1]["chunk_index"] == 1
        assert len(chunks[0]["chunk_text"]) <= 2048

    def test_overlap(self):
        text = "A" * 3000
        chunks = chunk_text(text, max_chars=2048, overlap_chars=256)
        assert len(chunks) >= 2
        # Second chunk should start before first chunk ends
        end_of_first = len(chunks[0]["chunk_text"])
        start_of_second = end_of_first - 256  # overlap
        assert start_of_second >= 0

    def test_content_hash_deterministic(self):
        chunks1 = chunk_text("test text")
        chunks2 = chunk_text("test text")
        assert chunks1[0]["content_hash"] == chunks2[0]["content_hash"]

    def test_content_hash_changes(self):
        chunks1 = chunk_text("text A")
        chunks2 = chunk_text("text B")
        assert chunks1[0]["content_hash"] != chunks2[0]["content_hash"]

    def test_hash_sha256_truncated(self):
        h = _hash("hello")
        assert len(h) == 16
        full = hashlib.sha256(b"hello").hexdigest()
        assert h == full[:16]


# ═══════════════════════════════════════════════════════════════════════
# Unit tests — extractors
# ═══════════════════════════════════════════════════════════════════════

class _FakeRecord(dict):
    """Dict subclass that mimics asyncpg.Record for testing."""
    def get(self, key, default=None):
        return super().get(key, default)


class TestExtractors:
    def test_extract_hf_basic(self):
        row = _FakeRecord(
            name="Urist", race="DWARF", caste="MALE",
            birth_year=1, death_year=50, death_cause="old age",
            kill_count=10, is_deity=False, is_force=False,
            is_vampire=False, is_necromancer=True, is_werebeast=False,
            is_ghost=False, is_author=False, is_auteur=False,
            spheres=None, goals=None, skills=None, entity_names=None,
        )
        text = extract_hf(row)
        assert "Urist" in text
        assert "DWARF" in text
        assert "necromancer" in text
        assert "10 kills" in text
        assert "born year 1" in text

    def test_extract_hf_deity_spheres(self):
        row = _FakeRecord(
            name="Armok", race="DEITY", caste=None,
            birth_year=-1, death_year=-1, death_cause=None,
            kill_count=0, is_deity=True, is_force=False,
            is_vampire=False, is_necromancer=False, is_werebeast=False,
            is_ghost=False, is_author=False, is_auteur=False,
            spheres=["war", "fire"], goals=None, skills=None,
            entity_names=None,
        )
        text = extract_hf(row)
        assert "deity" in text
        assert "war" in text
        assert "fire" in text

    def test_extract_event(self):
        row = _FakeRecord(
            year=42, event_type="hf died", site_id=5,
            narrative_weight=85.0, emotional_tone="tragic",
            hf1_name="Urist", hf2_name="Goblin Chief",
            site_name="Mountainhome",
        )
        text = extract_event(row)
        assert "Year 42" in text
        assert "Urist died" in text
        assert "slain by Goblin Chief" in text
        assert "Mountainhome" in text

    def test_extract_site(self):
        row = _FakeRecord(
            name="Boatmurdered", type="fortress",
            coords="50,60", founded_year=100,
            owner_name="The Dwarven Kingdom",
        )
        text = extract_site(row)
        assert "Boatmurdered" in text
        assert "fortress" in text
        assert "Dwarven Kingdom" in text

    def test_extract_entity(self):
        row = _FakeRecord(
            name="Nation of Stability", type="civilization",
            race="DWARF", site_count=15,
        )
        text = extract_entity(row)
        assert "Nation of Stability" in text
        assert "civilization" in text
        assert "15 sites" in text

    def test_extract_artifact(self):
        row = _FakeRecord(
            name="The Sword of Kings", item_type="weapon",
            item_subtype="short sword", material="iron",
            creator_name="Urist", site_name="Mountainhome",
        )
        text = extract_artifact(row)
        assert "Sword of Kings" in text
        assert "weapon" in text
        assert "iron" in text

    def test_extract_written_content(self):
        row = _FakeRecord(
            title="On the Nature of Dwarves", form="essay",
            type="philosophical", author_name="Urist",
            styles=["cynical", "rambling"],
        )
        text = extract_written_content(row)
        assert "Nature of Dwarves" in text
        assert "essay" in text
        assert "Urist" in text

    def test_extract_art_form(self):
        row = _FakeRecord(
            name="The Hammer Dance", form_type="dance",
            description="A vigorous dance mimicking hammer strikes",
        )
        text = extract_art_form(row)
        assert "Hammer Dance" in text
        assert "dance" in text
        assert "hammer strikes" in text

    def test_extract_unit(self):
        row = _FakeRecord(
            name="Urist McStonecrafter", english_name=None,
            race="DWARF", caste="FEMALE", profession="Stonecrafter",
            details={"personality_traits": ["creative", "patient"],
                     "stress": 50, "dream": "craft a masterwork"},
        )
        text = extract_unit(row)
        assert "Urist McStonecrafter" in text
        assert "DWARF" in text
        assert "creative" in text

    def test_extract_announcement(self):
        row = _FakeRecord(
            game_year=250, category="combat",
            text="The goblin punches the dwarf!",
        )
        text = extract_announcement(row)
        assert "Year 250" in text
        assert "goblin punches" in text


# ═══════════════════════════════════════════════════════════════════════
# Registry tests
# ═══════════════════════════════════════════════════════════════════════

class TestRegistry:
    def test_batch_types_complete(self):
        expected = {"art_form", "hf", "event", "site", "entity",
                    "artifact", "written_content"}
        assert set(BATCH_ENTITY_TYPES.keys()) == expected

    def test_batch_types_have_required_keys(self):
        for name, spec in BATCH_ENTITY_TYPES.items():
            assert "sql" in spec, f"{name} missing sql"
            assert "extract" in spec, f"{name} missing extract"
            assert "desc" in spec, f"{name} missing desc"
            assert "count_sql" in spec, f"{name} missing count_sql"
            assert callable(spec["extract"]), f"{name} extract not callable"

    def test_live_types(self):
        assert "unit" in LIVE_ENTITY_TYPES
        assert "announcement" in LIVE_ENTITY_TYPES
