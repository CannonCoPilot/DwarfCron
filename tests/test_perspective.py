"""Tests for PerspectiveRenderer, TemporalContextRenderer, and artifact claim synthesis.

Stage 4.1 — Phase 4: Narrative Engine
"""

import pytest

from chronicler.explorer.perspective import (
    EVENT_TEMPLATES,
    COLUMN_MAP_BY_EVENT,
    ENTITY_REF_FIELDS,
    PerspectiveRenderer,
    TemporalContextRenderer,
    synthesize_artifact_claim_lost_events,
)
from chronicler.explorer.linking import EntityLinkRenderer


# ── Fixtures ────────────────────────────────────────────────────────────────


class StubLinker(EntityLinkRenderer):
    """Linker stub that returns plain text instead of HTML links."""

    def __init__(self):
        pass  # skip parent __init__ which needs DB pool

    def link(self, entity_type: str, entity_id, name: str,
             world_id: int = 1) -> str:
        return f"[{entity_type}:{entity_id}:{name}]"


@pytest.fixture
def linker():
    return StubLinker()


@pytest.fixture
def renderer(linker):
    return PerspectiveRenderer(linker, world_id=1)


@pytest.fixture
def name_cache():
    """Name cache with a few test entities."""
    return {
        ('hf', 1): 'Urist McAxe',
        ('hf', 2): 'Dastot Manorhands',
        ('hf', 3): 'Etur Egendatan',
        ('site', 10): 'Girderpriced',
        ('entity', 20): 'The Bone Carvers',
        ('entity', 21): 'The Granite Halls',
        ('artifact', 30): 'Gleamingterror',
        ('artifact', 31): 'Shadowfang',
        ('structure', 40): 'The Great Hall',
    }


def _make_event(event_type: str, year: int = 100, **db_columns) -> dict:
    """Build a minimal event dict matching DB row shape."""
    ev = {
        'id': 1,
        'year': year,
        'seconds': 0,
        'event_type': event_type,
        'details': {},
        'hf_id_1': None,
        'hf_id_2': None,
        'site_id': None,
        'region_id': None,
        'entity_id_1': None,
        'entity_id_2': None,
        'artifact_id': None,
        'structure_id': None,
    }
    ev.update(db_columns)
    return ev


# ── Template Coverage Tests ─────────────────────────────────────────────────


class TestTemplateRegistration:
    """Verify template dict integrity."""

    def test_template_count_at_least_100(self):
        assert len(EVENT_TEMPLATES) >= 100

    def test_all_template_keys_are_space_separated(self):
        for key in EVENT_TEMPLATES:
            assert '_' not in key, f"Template key '{key}' uses underscores"

    def test_artifact_claim_lost_template_exists(self):
        assert 'artifact claim lost' in EVENT_TEMPLATES

    def test_artifact_claim_lost_column_map_exists(self):
        assert 'artifact claim lost' in COLUMN_MAP_BY_EVENT

    def test_new_claimant_hfid_in_entity_refs(self):
        assert 'new_claimant_hfid' in ENTITY_REF_FIELDS
        assert ENTITY_REF_FIELDS['new_claimant_hfid'] == 'hf'


# ── PerspectiveRenderer Basic Tests ─────────────────────────────────────────


class TestPerspectiveRenderer:
    """Core rendering tests."""

    def test_render_known_type(self, renderer, name_cache):
        event = _make_event('hf died', hf_id_1=1, site_id=10)
        result = renderer.render_event(event, 'hf', 99, name_cache)
        assert 'Urist McAxe' in result or 'hf:1' in result

    def test_render_unknown_type_uses_fallback(self, renderer):
        event = _make_event('totally_unknown_event_xyz')
        result = renderer.render_event(event, 'hf', 99)
        # Generic renderer should produce some output, not crash
        assert result is not None
        assert len(result) > 0

    def test_render_with_perspective_pronoun(self, renderer, name_cache):
        """When perspective entity is the subject, pronoun is used."""
        event = _make_event('hf travel', hf_id_1=1, site_id=10)
        result = renderer.render_event(event, 'hf', 1, name_cache)
        # Should contain a pronoun instead of the name
        assert '<em>' in result

    def test_render_artifact_claim_lost(self, renderer, name_cache):
        event = _make_event(
            'artifact claim lost',
            hf_id_1=1, hf_id_2=2, artifact_id=30,
        )
        result = renderer.render_event(event, 'hf', 99, name_cache)
        assert 'superseded' in result.lower() or 'claim' in result.lower()

    def test_render_artifact_claim_lost_with_perspective(self, renderer, name_cache):
        event = _make_event(
            'artifact claim lost',
            hf_id_1=1, hf_id_2=2, artifact_id=30,
        )
        result = renderer.render_event(event, 'hf', 1, name_cache)
        # Perspective entity should get pronoun
        assert '<em>' in result


# ── TemporalContextRenderer Tests ───────────────────────────────────────────


class TestTemporalContextRenderer:
    """Year-header injection tests."""

    def test_first_event_gets_year_header(self, renderer):
        temporal = TemporalContextRenderer(renderer)
        event = _make_event('hf travel', year=100, hf_id_1=1, site_id=10)
        result = temporal.render_event(event, 'hf', 99)
        assert result['year_header'] == 100

    def test_same_year_no_duplicate_header(self, renderer):
        temporal = TemporalContextRenderer(renderer)
        ev1 = _make_event('hf travel', year=100, hf_id_1=1, site_id=10)
        ev2 = _make_event('hf travel', year=100, hf_id_1=2, site_id=10)
        temporal.render_event(ev1, 'hf', 99)
        result = temporal.render_event(ev2, 'hf', 99)
        assert result['year_header'] is None

    def test_year_change_gets_new_header(self, renderer):
        temporal = TemporalContextRenderer(renderer)
        ev1 = _make_event('hf travel', year=100, hf_id_1=1, site_id=10)
        ev2 = _make_event('hf travel', year=105, hf_id_1=1, site_id=10)
        temporal.render_event(ev1, 'hf', 99)
        result = temporal.render_event(ev2, 'hf', 99)
        assert result['year_header'] == 105

    def test_reset_clears_state(self, renderer):
        temporal = TemporalContextRenderer(renderer)
        ev1 = _make_event('hf travel', year=100, hf_id_1=1, site_id=10)
        temporal.render_event(ev1, 'hf', 99)
        temporal.reset()
        ev2 = _make_event('hf travel', year=100, hf_id_1=1, site_id=10)
        result = temporal.render_event(ev2, 'hf', 99)
        assert result['year_header'] == 100  # header again after reset

    def test_output_contains_text_key(self, renderer):
        temporal = TemporalContextRenderer(renderer)
        event = _make_event('hf travel', year=100, hf_id_1=1, site_id=10)
        result = temporal.render_event(event, 'hf', 99)
        assert 'text' in result
        assert isinstance(result['text'], str)
        assert len(result['text']) > 0

    def test_output_preserves_event_keys(self, renderer):
        temporal = TemporalContextRenderer(renderer)
        event = _make_event('hf travel', year=100, hf_id_1=1, site_id=10)
        result = temporal.render_event(event, 'hf', 99)
        assert result['year'] == 100
        assert result['event_type'] == 'hf travel'
        assert result['id'] == 1


# ── Artifact Claim Chain Synthesis Tests ────────────────────────────────────


class TestArtifactClaimSynthesis:
    """Tests for synthesize_artifact_claim_lost_events."""

    def test_single_claim_no_synthetic(self):
        claims = [{'year': 100, 'hfid': 1, 'artifact_id': 30}]
        result = synthesize_artifact_claim_lost_events(1, claims)
        assert len(result) == 0

    def test_later_claim_by_different_hf_creates_lost(self):
        claims = [
            {'year': 100, 'hfid': 1, 'artifact_id': 30},
            {'year': 150, 'hfid': 2, 'artifact_id': 30},
        ]
        result = synthesize_artifact_claim_lost_events(1, claims)
        assert len(result) == 1
        assert result[0]['event_type'] == 'artifact claim lost'
        assert result[0]['year'] == 150
        assert result[0]['details']['new_claimant_hfid'] == 2
        assert result[0]['details']['artifact_id'] == 30

    def test_same_hf_reclaim_no_lost(self):
        claims = [
            {'year': 100, 'hfid': 1, 'artifact_id': 30},
            {'year': 150, 'hfid': 1, 'artifact_id': 30},  # same HF
        ]
        result = synthesize_artifact_claim_lost_events(1, claims)
        assert len(result) == 0

    def test_multiple_artifacts(self):
        claims = [
            {'year': 100, 'hfid': 1, 'artifact_id': 30},
            {'year': 150, 'hfid': 2, 'artifact_id': 30},
            {'year': 80, 'hfid': 1, 'artifact_id': 31},
            {'year': 200, 'hfid': 3, 'artifact_id': 31},
        ]
        result = synthesize_artifact_claim_lost_events(1, claims)
        assert len(result) == 2
        artifact_ids = {r['details']['artifact_id'] for r in result}
        assert artifact_ids == {30, 31}

    def test_synthetic_events_are_marked(self):
        claims = [
            {'year': 100, 'hfid': 1, 'artifact_id': 30},
            {'year': 150, 'hfid': 2, 'artifact_id': 30},
        ]
        result = synthesize_artifact_claim_lost_events(1, claims)
        assert result[0]['synthetic'] is True
        assert result[0]['id'] < 0  # negative synthetic ID

    def test_only_first_superseding_claim(self):
        """If artifact is claimed by HF2 then HF3, we only get one lost event."""
        claims = [
            {'year': 100, 'hfid': 1, 'artifact_id': 30},
            {'year': 150, 'hfid': 2, 'artifact_id': 30},
            {'year': 200, 'hfid': 3, 'artifact_id': 30},
        ]
        result = synthesize_artifact_claim_lost_events(1, claims)
        assert len(result) == 1
        assert result[0]['details']['new_claimant_hfid'] == 2

    def test_hf_not_claimant_produces_nothing(self):
        """If HF 1 never claimed artifact 30, no synthetic events."""
        claims = [
            {'year': 100, 'hfid': 2, 'artifact_id': 30},
            {'year': 150, 'hfid': 3, 'artifact_id': 30},
        ]
        result = synthesize_artifact_claim_lost_events(1, claims)
        assert len(result) == 0
