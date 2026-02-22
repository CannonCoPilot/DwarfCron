"""Tests for chronicler.dfhack.detector — change detection across snapshots.

Tests the ChangeDetector class (RPC + bridge) and helper diff functions.
No database or network access required.
"""

import pytest

from chronicler.dfhack.detector import (
    ChangeDetector,
    _unit_summary,
    _diff_unit,
    _diff_bridge_unit,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_unit(uid=1, name="Urist", race="DWARF", profession="MINER",
               is_alive=True, **details_overrides):
    """Create a minimal unit dict for testing."""
    unit = {
        'id': uid, 'name': name, 'race': race,
        'profession': profession, 'is_alive': is_alive,
        'details': {},
    }
    unit['details'].update(details_overrides)
    return unit


def _make_bridge_unit(uid=1, first_name="Urist", has_mood=False, mood=None,
                      ghostly=False, pregnancy_timer=0, stress=0, **extras):
    """Create a minimal bridge fortress_unit dict for testing."""
    unit = {
        'id': uid, 'first_name': first_name,
        'has_mood': has_mood, 'mood': mood,
        'ghostly': ghostly, 'pregnancy_timer': pregnancy_timer,
        'stress': stress,
    }
    unit.update(extras)
    return unit


# ── _unit_summary ────────────────────────────────────────────────────────────

class TestUnitSummary:

    def test_extracts_key_fields(self):
        unit = _make_unit(name="Bomrek", race="DWARF", profession="MASON")
        s = _unit_summary(unit)
        assert s['name'] == "Bomrek"
        assert s['race'] == "DWARF"
        assert s['profession'] == "MASON"
        assert s['is_alive'] is True

    def test_missing_fields_are_none(self):
        s = _unit_summary({'id': 1})
        assert s['name'] is None
        assert s['race'] is None
        assert s['profession'] is None


# ── ChangeDetector.detect — bootstrap ────────────────────────────────────────

class TestDetectBootstrap:

    def test_first_call_returns_empty(self):
        """First call is silent bootstrap — no events."""
        det = ChangeDetector()
        events = det.detect([_make_unit(uid=1), _make_unit(uid=2)])
        assert events == []
        assert det._bootstrapped is True

    def test_second_call_detects_changes(self):
        det = ChangeDetector()
        det.detect([_make_unit(uid=1)])
        events = det.detect([_make_unit(uid=1), _make_unit(uid=2)])
        types = [e['event_type'] for e in events]
        assert 'ARRIVED' in types


# ── ChangeDetector.detect — arrivals & departures ────────────────────────────

class TestDetectArrivals:

    def test_new_unit_generates_arrived(self):
        det = ChangeDetector()
        det.detect([_make_unit(uid=1)])
        events = det.detect([_make_unit(uid=1), _make_unit(uid=2, name="Bomrek")])
        arrived = [e for e in events if e['event_type'] == 'ARRIVED']
        assert len(arrived) == 1
        assert arrived[0]['unit_id'] == 2
        assert arrived[0]['new_value']['name'] == "Bomrek"
        assert arrived[0]['old_value'] is None

    def test_removed_unit_generates_departed(self):
        det = ChangeDetector()
        det.detect([_make_unit(uid=1), _make_unit(uid=2)])
        events = det.detect([_make_unit(uid=1)])
        departed = [e for e in events if e['event_type'] == 'DEPARTED']
        assert len(departed) == 1
        assert departed[0]['unit_id'] == 2
        assert departed[0]['new_value'] is None

    def test_no_changes_no_events(self):
        det = ChangeDetector()
        unit = _make_unit(uid=1)
        det.detect([unit])
        events = det.detect([unit])
        assert events == []


# ── _diff_unit — per-unit field diffs ────────────────────────────────────────

class TestDiffUnit:

    def test_death_detected(self):
        old = _make_unit(is_alive=True)
        new = _make_unit(is_alive=False)
        events = _diff_unit(1, old, new)
        died = [e for e in events if e['event_type'] == 'DIED']
        assert len(died) == 1
        assert died[0]['new_value']['is_alive'] is False

    def test_alive_to_alive_no_death(self):
        old = _make_unit(is_alive=True)
        new = _make_unit(is_alive=True)
        events = _diff_unit(1, old, new)
        died = [e for e in events if e['event_type'] == 'DIED']
        assert len(died) == 0

    def test_profession_change(self):
        old = _make_unit(profession="MINER")
        new = _make_unit(profession="MASON")
        events = _diff_unit(1, old, new)
        prof = [e for e in events if e['event_type'] == 'PROFESSION_CHANGED']
        assert len(prof) == 1
        assert prof[0]['old_value'] == {'profession': 'MINER'}
        assert prof[0]['new_value'] == {'profession': 'MASON'}

    def test_same_profession_no_event(self):
        old = _make_unit(profession="MINER")
        new = _make_unit(profession="MINER")
        events = _diff_unit(1, old, new)
        prof = [e for e in events if e['event_type'] == 'PROFESSION_CHANGED']
        assert len(prof) == 0

    def test_squad_change(self):
        old = _make_unit(squad_id=1)
        new = _make_unit(squad_id=2)
        events = _diff_unit(1, old, new)
        sq = [e for e in events if e['event_type'] == 'SQUAD_CHANGED']
        assert len(sq) == 1
        assert sq[0]['old_value'] == {'squad_id': 1}
        assert sq[0]['new_value'] == {'squad_id': 2}

    def test_skill_up(self):
        old = _make_unit(skills=[{'id': 0, 'name': 'MINING', 'level': 3}])
        new = _make_unit(skills=[{'id': 0, 'name': 'MINING', 'level': 5}])
        events = _diff_unit(1, old, new)
        su = [e for e in events if e['event_type'] == 'SKILL_UP']
        assert len(su) == 1
        skills = su[0]['new_value']['skills']
        assert len(skills) == 1
        assert skills[0]['old_level'] == 3
        assert skills[0]['new_level'] == 5

    def test_no_skill_change_no_event(self):
        old = _make_unit(skills=[{'id': 0, 'name': 'MINING', 'level': 3}])
        new = _make_unit(skills=[{'id': 0, 'name': 'MINING', 'level': 3}])
        events = _diff_unit(1, old, new)
        su = [e for e in events if e['event_type'] == 'SKILL_UP']
        assert len(su) == 0

    def test_new_skill_detected(self):
        """A skill not present in old (level 0) appearing in new counts as skill-up."""
        old = _make_unit(skills=[])
        new = _make_unit(skills=[{'id': 5, 'name': 'WOODCUTTING', 'level': 1}])
        events = _diff_unit(1, old, new)
        su = [e for e in events if e['event_type'] == 'SKILL_UP']
        assert len(su) == 1
        assert su[0]['new_value']['skills'][0]['old_level'] == 0

    def test_multiple_events_same_unit(self):
        """A unit can die AND change profession in the same tick."""
        old = _make_unit(is_alive=True, profession="MINER")
        new = _make_unit(is_alive=False, profession="CORPSE")
        events = _diff_unit(1, old, new)
        types = {e['event_type'] for e in events}
        assert 'DIED' in types
        assert 'PROFESSION_CHANGED' in types


# ── _diff_bridge_unit — mood/flag/pregnancy ──────────────────────────────────

class TestDiffBridgeUnit:

    def test_mood_onset(self):
        old = _make_bridge_unit(has_mood=False)
        new = _make_bridge_unit(has_mood=True, mood="fey")
        events = _diff_bridge_unit(1, old, new)
        mood = [e for e in events if e['event_type'] == 'MOOD_CHANGED']
        assert len(mood) == 1
        assert mood[0]['new_value']['mood'] == "fey"

    def test_mood_resolution(self):
        old = _make_bridge_unit(has_mood=True, mood="fey")
        new = _make_bridge_unit(has_mood=False, had_mood=True, mood=None)
        events = _diff_bridge_unit(1, old, new)
        resolved = [e for e in events if e['event_type'] == 'MOOD_RESOLVED']
        assert len(resolved) == 1

    def test_no_mood_change_no_event(self):
        old = _make_bridge_unit(has_mood=False)
        new = _make_bridge_unit(has_mood=False)
        events = _diff_bridge_unit(1, old, new)
        mood = [e for e in events if e['event_type'] in ('MOOD_CHANGED', 'MOOD_RESOLVED')]
        assert len(mood) == 0

    def test_ghost_detection(self):
        old = _make_bridge_unit(ghostly=False)
        new = _make_bridge_unit(ghostly=True)
        events = _diff_bridge_unit(1, old, new)
        ghost = [e for e in events if e['event_type'] == 'GHOST']
        assert len(ghost) == 1

    def test_already_ghost_no_duplicate(self):
        old = _make_bridge_unit(ghostly=True)
        new = _make_bridge_unit(ghostly=True)
        events = _diff_bridge_unit(1, old, new)
        ghost = [e for e in events if e['event_type'] == 'GHOST']
        assert len(ghost) == 0

    def test_pregnancy_detected(self):
        old = _make_bridge_unit(pregnancy_timer=0)
        new = _make_bridge_unit(pregnancy_timer=300000, pregnancy_spouse=42)
        events = _diff_bridge_unit(1, old, new)
        preg = [e for e in events if e['event_type'] == 'PREGNANCY_DETECTED']
        assert len(preg) == 1
        assert preg[0]['new_value']['pregnancy_timer'] == 300000
        assert preg[0]['new_value']['pregnancy_spouse'] == 42

    def test_ongoing_pregnancy_no_duplicate(self):
        old = _make_bridge_unit(pregnancy_timer=300000)
        new = _make_bridge_unit(pregnancy_timer=250000)
        events = _diff_bridge_unit(1, old, new)
        preg = [e for e in events if e['event_type'] == 'PREGNANCY_DETECTED']
        assert len(preg) == 0

    def test_stress_spike(self):
        old = _make_bridge_unit(stress=10000)
        new = _make_bridge_unit(stress=80000)
        events = _diff_bridge_unit(1, old, new)
        spike = [e for e in events if e['event_type'] == 'STRESS_SPIKE']
        assert len(spike) == 1
        assert spike[0]['new_value']['delta'] == 70000

    def test_small_stress_change_no_event(self):
        """Stress increase < 50000 should not trigger."""
        old = _make_bridge_unit(stress=10000)
        new = _make_bridge_unit(stress=40000)
        events = _diff_bridge_unit(1, old, new)
        spike = [e for e in events if e['event_type'] == 'STRESS_SPIKE']
        assert len(spike) == 0

    def test_stress_decrease_no_event(self):
        old = _make_bridge_unit(stress=80000)
        new = _make_bridge_unit(stress=10000)
        events = _diff_bridge_unit(1, old, new)
        spike = [e for e in events if e['event_type'] == 'STRESS_SPIKE']
        assert len(spike) == 0


# ── ChangeDetector.detect_bridge — bootstrap ─────────────────────────────────

class TestDetectBridgeBootstrap:

    def test_first_call_returns_empty(self):
        det = ChangeDetector()
        events = det.detect_bridge([_make_bridge_unit(uid=1)])
        assert events == []
        assert det._bridge_bootstrapped is True

    def test_second_call_detects_changes(self):
        det = ChangeDetector()
        det.detect_bridge([_make_bridge_unit(uid=1, has_mood=False)])
        events = det.detect_bridge([_make_bridge_unit(uid=1, has_mood=True, mood="fey")])
        types = [e['event_type'] for e in events]
        assert 'MOOD_CHANGED' in types

    def test_rpc_and_bridge_bootstrap_independent(self):
        """RPC and bridge bootstraps are tracked separately."""
        det = ChangeDetector()
        assert not det._bootstrapped
        assert not det._bridge_bootstrapped
        det.detect([_make_unit(uid=1)])
        assert det._bootstrapped
        assert not det._bridge_bootstrapped
        det.detect_bridge([_make_bridge_unit(uid=1)])
        assert det._bridge_bootstrapped
