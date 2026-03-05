"""Death cause rendering for historical figures.

Converts DF death cause codes (from both the HF record and event details)
into human-readable narrative text.  Supports weapon/slayer enrichment.

DF tracks two related fields:
  - historical_figures.death_cause: e.g. "struck_down", "murder", "old_age"
  - history_events (hf died).details.cause: e.g. "struck", "murdered", "old age"

This module normalizes both formats into readable English.
"""

from chronicler.explorer.calendar import DFCalendar


# ── HF-record death cause codes → human-readable phrases ─────────────────
# Keys are normalized (lowercased, underscores preserved) from the
# historical_figures.death_cause column.
_HF_DEATH_CAUSE_MAP = {
    'struck_down': 'struck down',
    'murder': 'murdered',
    'murdered': 'murdered',
    'old_age': 'died of old age',
    'old age': 'died of old age',
    'shot': 'shot',
    'thirst': 'died of thirst',
    'starved': 'starved to death',
    'infection': 'died of infection',
    'bled': 'bled to death',
    'drown': 'drowned',
    'drowned': 'drowned',
    'suffocate': 'suffocated',
    'scuttled': 'scuttled',
    'collision': 'died in a collision',
    'cave_in': 'crushed in a cave-in',
    'struck': 'struck down',
    'exec_hacked_to_pieces': 'executed (hacked to pieces)',
    'exec_beheaded': 'executed (beheaded)',
    'exec_drowned': 'executed (drowned)',
    'exec_fed_to_beasts': 'executed (fed to beasts)',
    'exec_burned_alive': 'executed (burned alive)',
    'exec_buried_alive': 'executed (buried alive)',
    'exec_crucified': 'executed (crucified)',
    'exec_generic': 'executed',
    'suicide_drowned': 'drowned (suicide)',
    'suicide_leaping': 'leapt to death',
    'heat': 'died of heat',
    'cold': 'died of cold',
    'trap': 'killed by a trap',
    'memorialize': 'memorialized',
    'ghost': 'became a ghost',
    'vanish': 'vanished',
    'retired': 'retired',
    'scared': 'scared to death',
    'slaughtered': 'slaughtered',
    'melted': 'melted',
    'frozen': 'frozen',
    'spikeball': 'killed by a spike ball',
}

# ── Event-level cause codes → human-readable phrases ─────────────────────
# Keys are from history_events.details->>'cause' (spaces, no underscores).
_EVENT_CAUSE_MAP = {
    'struck': 'was struck down',
    'old age': 'died of old age',
    'murdered': 'was murdered',
    'shot': 'was shot',
    'exec hacked to pieces': 'was executed (hacked to pieces)',
    'exec beheaded': 'was executed (beheaded)',
    'exec drowned': 'was executed (drowned)',
    'exec fed to beasts': 'was executed (fed to beasts)',
    'exec burned alive': 'was executed (burned alive)',
    'exec buried alive': 'was executed (buried alive)',
    'exec crucified': 'was executed (crucified)',
    'exec generic': 'was executed',
    'suicide drowned': 'drowned (suicide)',
    'suicide leaping': 'leapt to death',
    'thirst': 'died of thirst',
    'infection': 'died of infection',
    'bled': 'bled to death',
    'drown': 'drowned',
    'suffocate': 'suffocated',
    'collision': 'died in a collision',
    'cave in': 'was crushed in a cave-in',
    'heat': 'died of heat',
    'cold': 'died of cold',
    'trap': 'was killed by a trap',
    'scared': 'was scared to death',
    'slaughtered': 'was slaughtered',
    'melted': 'melted',
    'frozen': 'froze to death',
}


class DeathCauseRenderer:
    """Render death cause codes into human-readable narrative text."""

    @classmethod
    def render_hf_cause(cls, death_cause: str | None) -> str:
        """Render a death cause from the historical_figures table.

        Returns a past-tense phrase suitable for profile display:
        "struck down", "murdered", "died of old age", etc.
        """
        if not death_cause:
            return 'unknown causes'
        key = death_cause.strip().lower()
        return _HF_DEATH_CAUSE_MAP.get(key, key.replace('_', ' '))

    @classmethod
    def render_event_cause(cls, cause: str | None) -> str:
        """Render a cause from hf died event details.

        Returns a verb phrase suitable for event timeline:
        "was struck down", "died of old age", etc.
        """
        if not cause:
            return 'died'
        key = cause.strip().lower()
        return _EVENT_CAUSE_MAP.get(key, key.replace('_', ' '))

    @classmethod
    def render_age_at_death(cls, birth_year: int | None, death_year: int | None,
                            birth_seconds: int | None = None,
                            death_seconds: int | None = None) -> str | None:
        """Compute age at death with fractional precision when tick data exists.

        Returns a human-readable age string, or None if birth/death unknown.
        Examples: "71 years", "42 years, 3 months", "<1 year"
        """
        if birth_year is None or death_year is None:
            return None
        if death_year < 0 or birth_year < 0:
            return None

        have_ticks = (birth_seconds is not None and birth_seconds >= 0
                      and death_seconds is not None and death_seconds >= 0)

        if have_ticks:
            total_ticks = ((death_year - birth_year) * DFCalendar.TICKS_PER_YEAR
                           + death_seconds - birth_seconds)
            if total_ticks < 0:
                total_ticks = 0
            total_days = total_ticks // DFCalendar.TICKS_PER_DAY
            years = total_days // (DFCalendar.DAYS_PER_MONTH * DFCalendar.MONTHS_PER_YEAR)
            remaining = total_days % (DFCalendar.DAYS_PER_MONTH * DFCalendar.MONTHS_PER_YEAR)
            months = remaining // DFCalendar.DAYS_PER_MONTH

            if years == 0 and months == 0:
                return '<1 year'
            parts = []
            if years:
                parts.append(f"{years} year{'s' if years != 1 else ''}")
            if months:
                parts.append(f"{months} month{'s' if months != 1 else ''}")
            return ', '.join(parts)
        else:
            span = death_year - birth_year
            if span <= 0:
                return '<1 year'
            return f"{span} year{'s' if span != 1 else ''}"
