"""Tests for chronicler.storyteller.context — keyword routing and formatting.

Tests pure functions that don't require database access.
"""

import pytest

from chronicler.storyteller.context import (
    extract_keywords,
    _format_hf,
    _format_event,
    _summarize_details,
    _CATEGORY_ROUTES,
)


# ── Keyword extraction ──────────────────────────────────────────────────────

class TestExtractKeywords:

    def test_basic_extraction(self):
        keywords = extract_keywords("Tell me about the vampire Stukos")
        assert "vampire" in keywords
        assert "stukos" in keywords

    def test_stop_words_filtered(self):
        keywords = extract_keywords("What is the history of this world?")
        assert "what" not in keywords
        assert "the" not in keywords
        assert "is" not in keywords

    def test_short_words_filtered(self):
        keywords = extract_keywords("Is it a big war?")
        assert "it" not in keywords
        assert "war" in keywords

    def test_limit_to_five(self):
        keywords = extract_keywords(
            "vampire necromancer werebeast deity ghost dragon titan forgotten beast"
        )
        assert len(keywords) <= 5

    def test_case_normalized(self):
        keywords = extract_keywords("VAMPIRE Dragon")
        assert "vampire" in keywords
        assert "dragon" in keywords

    def test_punctuation_stripped(self):
        keywords = extract_keywords("Who is Urist? What about Bomrek!")
        assert "urist" in keywords
        assert "bomrek" in keywords

    def test_dwarf_fortress_words_filtered(self):
        """'dwarf', 'fortress', 'world', 'history' are stop words."""
        keywords = extract_keywords("Tell me about this dwarf fortress world history")
        assert "dwarf" not in keywords
        assert "fortress" not in keywords
        assert "world" not in keywords
        assert "history" not in keywords


# ── Category routing coverage ────────────────────────────────────────────────

class TestCategoryRoutes:

    def test_deity_routes_to_hf_flag(self):
        for kw in ("deity", "deities", "god", "gods", "divine"):
            route = _CATEGORY_ROUTES[kw]
            assert route == ("hf_flag", "is_deity"), f"{kw} should route to is_deity"

    def test_vampire_routes_to_hf_flag(self):
        route = _CATEGORY_ROUTES["vampire"]
        assert route == ("hf_flag", "is_vampire")

    def test_war_routes_to_collection_type(self):
        route = _CATEGORY_ROUTES["war"]
        assert route == ("collection_type", "war")

    def test_battle_routes_to_collection_type(self):
        route = _CATEGORY_ROUTES["battle"]
        assert route == ("collection_type", "battle")

    def test_book_routes_to_written_contents(self):
        for kw in ("book", "books", "poem", "poems", "scroll", "scrolls",
                    "composition", "music", "literature", "writing", "writings"):
            route = _CATEGORY_ROUTES[kw]
            assert route[0] == "written_contents", f"{kw} should route to written_contents"

    def test_artifact_routes(self):
        route = _CATEGORY_ROUTES["artifact"]
        assert route == ("artifacts", None)

    def test_live_data_routes(self):
        assert _CATEGORY_ROUTES["fortress"] == ("live_units", None)
        assert _CATEGORY_ROUTES["squad"] == ("live_squads", None)
        assert _CATEGORY_ROUTES["army"] == ("live_armies", None)
        assert _CATEGORY_ROUTES["recent"] == ("live_events", None)
        assert _CATEGORY_ROUTES["report"] == ("live_reports", None)

    def test_megabeast_routes_to_race_patterns(self):
        route = _CATEGORY_ROUTES["megabeast"]
        assert route[0] == "hf_race"
        assert "DRAGON" in route[1]


# ── _format_hf ──────────────────────────────────────────────────────────────

class TestFormatHF:
    """Test historical figure formatting using dict-like mock records."""

    class MockRecord(dict):
        """Minimal mock that supports both dict[] and .get() access."""
        def __getitem__(self, key):
            return self.get(key)

    def _make_hf(self, **overrides):
        defaults = {
            "name": "Urist", "race": "DWARF", "caste": "FEMALE",
            "is_deity": False, "is_force": False, "is_vampire": False,
            "is_necromancer": False, "is_werebeast": False,
            "birth_year": 50, "death_year": None, "death_cause": None,
            "kill_count": 0, "details": None,
        }
        defaults.update(overrides)
        return self.MockRecord(defaults)

    def test_basic_format(self):
        hf = self._make_hf()
        text = _format_hf(hf)
        assert "Urist" in text
        assert "DWARF" in text

    def test_deity_tagged(self):
        hf = self._make_hf(name="Armok", is_deity=True)
        text = _format_hf(hf)
        assert "deity" in text

    def test_vampire_tagged(self):
        hf = self._make_hf(name="Stukos", is_vampire=True)
        text = _format_hf(hf)
        assert "vampire" in text

    def test_kill_count_shown(self):
        hf = self._make_hf(name="Wardog", kill_count=42)
        text = _format_hf(hf)
        assert "42 kills" in text

    def test_death_info(self):
        hf = self._make_hf(death_year=120, death_cause="old age")
        text = _format_hf(hf)
        assert "died year 120" in text
        assert "old age" in text

    def test_spheres_from_details(self):
        import json
        hf = self._make_hf(
            name="Armok", is_deity=True,
            details=json.dumps({"spheres": ["war", "fire"]})
        )
        text = _format_hf(hf)
        assert "war" in text
        assert "fire" in text


# ── _format_event ───────────────────────────────────────────────────────────

class TestFormatEvent:

    class MockRecord(dict):
        def __getitem__(self, key):
            return self.get(key)

    def _make_event(self, **overrides):
        defaults = {
            "year": 253, "event_type": "hf died", "details": None,
            "hf1_name": None, "hf2_name": None, "site_name": None,
        }
        defaults.update(overrides)
        return self.MockRecord(defaults)

    def test_death_event(self):
        ev = self._make_event(
            hf1_name="Bomrek", hf2_name="Urist", site_name="Goldenhall"
        )
        text = _format_event(ev)
        assert "Year 253" in text
        assert "Bomrek died" in text
        assert "slain by Urist" in text
        assert "Goldenhall" in text

    def test_battle_event(self):
        ev = self._make_event(
            event_type="hf simple battle event",
            hf1_name="Urist", hf2_name="Goblin",
        )
        text = _format_event(ev)
        assert "Urist fought Goblin" in text

    def test_generic_fallback(self):
        ev = self._make_event(
            event_type="some unknown type",
            hf1_name="Urist",
        )
        text = _format_event(ev)
        assert "some unknown type" in text
        assert "Urist" in text

    def test_no_names_still_works(self):
        ev = self._make_event(event_type="change hf state")
        text = _format_event(ev)
        assert "Year 253" in text
        assert "change hf state" in text


# ── _summarize_details ──────────────────────────────────────────────────────

class TestSummarizeDetails:

    def test_none_returns_no_details(self):
        assert _summarize_details(None) == "(no details)"

    def test_dict_with_interesting_keys(self):
        details = {"reason": "felt threatened", "noise": "ignored"}
        result = _summarize_details(details)
        assert "reason: felt threatened" in result

    def test_json_string_parsed(self):
        import json
        details = json.dumps({"cause": "old age"})
        result = _summarize_details(details)
        assert "cause: old age" in result

    def test_empty_dict(self):
        result = _summarize_details({})
        assert result == "(details available)" or result == "(no details)"

    def test_string_truncated(self):
        result = _summarize_details("x" * 200)
        assert len(result) <= 100
