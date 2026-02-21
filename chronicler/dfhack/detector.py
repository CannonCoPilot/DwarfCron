"""Change detector — compares consecutive unit snapshots to emit events.

Uses two-level detection (pattern from Helper.lua in DF modding community):
1. Count-based: detect mass arrivals/departures by comparing set membership
2. Key-based: per-unit field diffing for profession, skills, squad, alive status

First call is a silent bootstrap — populates previous state, emits no events.
"""

import logging
from typing import Any

log = logging.getLogger(__name__)


class ChangeDetector:
    """Compares consecutive unit snapshots to emit structured events."""

    def __init__(self):
        self.previous: dict[int, dict] = {}
        self._bootstrapped = False

    def detect(self, current_units: list[dict]) -> list[dict]:
        """Compare current vs previous. First call = silent bootstrap (no events).

        Args:
            current_units: List of unit dicts from DFHackClient.list_units()

        Returns:
            List of event dicts with keys: unit_id, event_type, old_value, new_value
        """
        current_by_id = {u['id']: u for u in current_units}

        if not self._bootstrapped:
            self.previous = current_by_id
            self._bootstrapped = True
            log.info("Bootstrap: %d units in initial snapshot", len(current_by_id))
            return []

        events = []

        # New arrivals (in current but not previous)
        for uid, unit in current_by_id.items():
            if uid not in self.previous:
                events.append({
                    'unit_id': uid,
                    'event_type': 'ARRIVED',
                    'old_value': None,
                    'new_value': _unit_summary(unit),
                })

        # Departures (in previous but not current)
        for uid in self.previous:
            if uid not in current_by_id:
                events.append({
                    'unit_id': uid,
                    'event_type': 'DEPARTED',
                    'old_value': _unit_summary(self.previous[uid]),
                    'new_value': None,
                })

        # Per-unit diffs (units present in both snapshots)
        for uid, unit in current_by_id.items():
            if uid in self.previous:
                events.extend(_diff_unit(uid, self.previous[uid], unit))

        self.previous = current_by_id
        return events


def _unit_summary(unit: dict) -> dict[str, Any]:
    """Extract a compact summary of a unit for event payloads."""
    return {
        'name': unit.get('name'),
        'race': unit.get('race'),
        'race_name': unit.get('race_name'),
        'profession': unit.get('profession'),
        'is_alive': unit.get('is_alive'),
    }


def _diff_unit(uid: int, old: dict, new: dict) -> list[dict]:
    """Compare two snapshots of the same unit and emit change events."""
    events = []

    # Death detection
    if old.get('is_alive') and not new.get('is_alive'):
        events.append({
            'unit_id': uid,
            'event_type': 'DIED',
            'old_value': {'is_alive': True},
            'new_value': {'is_alive': False, 'name': new.get('name')},
        })

    # Profession change
    old_prof = old.get('profession')
    new_prof = new.get('profession')
    if old_prof != new_prof:
        events.append({
            'unit_id': uid,
            'event_type': 'PROFESSION_CHANGED',
            'old_value': {'profession': old_prof},
            'new_value': {'profession': new_prof},
        })

    # Squad change
    old_squad = old.get('details', {}).get('squad_id')
    new_squad = new.get('details', {}).get('squad_id')
    if old_squad != new_squad:
        events.append({
            'unit_id': uid,
            'event_type': 'SQUAD_CHANGED',
            'old_value': {'squad_id': old_squad},
            'new_value': {'squad_id': new_squad},
        })

    # Skill-ups (batch all level increases into one event per unit)
    old_skills = {s['id']: s['level'] for s in old.get('details', {}).get('skills', [])}
    new_skills = {s['id']: s for s in new.get('details', {}).get('skills', [])}
    skill_ups = []
    for sid, skill in new_skills.items():
        old_level = old_skills.get(sid, 0)
        if skill['level'] > old_level:
            skill_ups.append({
                'skill_id': sid,
                'skill_name': skill.get('name', f'SKILL_{sid}'),
                'old_level': old_level,
                'new_level': skill['level'],
            })
    if skill_ups:
        events.append({
            'unit_id': uid,
            'event_type': 'SKILL_UP',
            'old_value': None,
            'new_value': {'skills': skill_ups},
        })

    return events
