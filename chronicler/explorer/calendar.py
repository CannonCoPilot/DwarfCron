"""Dwarf Fortress calendar conversion utility.

DF uses a 12-month calendar with 28 days per month (336 days/year).
Time within a year is tracked as 'seconds72' (ticks at 72x speed).
1200 ticks = 1 day, 33600 ticks = 1 month, 403200 ticks = 1 year.
"""


class DFCalendar:
    """Convert between DF tick-based timestamps and human-readable dates."""

    MONTHS = [
        'Granite', 'Slate', 'Felsite',        # Spring
        'Hematite', 'Malachite', 'Galena',    # Summer
        'Limestone', 'Sandstone', 'Timber',    # Autumn
        'Moonstone', 'Opal', 'Obsidian',      # Winter
    ]

    SEASONS = ['Spring', 'Summer', 'Autumn', 'Winter']
    SEASON_PARTS = ['Early', 'Mid', 'Late']

    TICKS_PER_DAY = 1200
    DAYS_PER_MONTH = 28
    MONTHS_PER_YEAR = 12
    TICKS_PER_YEAR = TICKS_PER_DAY * DAYS_PER_MONTH * MONTHS_PER_YEAR  # 403,200

    @classmethod
    def from_seconds72(cls, year: int, seconds72: int) -> dict:
        """Convert year + seconds72 to structured date dict."""
        if seconds72 is None or seconds72 < 0:
            return {
                'year': year, 'month': None, 'month_idx': None,
                'day': None, 'season': None, 'season_part': None,
            }

        day_of_year = seconds72 // cls.TICKS_PER_DAY
        month_idx = min(day_of_year // cls.DAYS_PER_MONTH, 11)
        day_of_month = (day_of_year % cls.DAYS_PER_MONTH) + 1
        season_idx = month_idx // 3
        season_part_idx = month_idx % 3

        return {
            'year': year,
            'month': cls.MONTHS[month_idx],
            'month_idx': month_idx,
            'day': day_of_month,
            'season': cls.SEASONS[season_idx],
            'season_part': cls.SEASON_PARTS[season_part_idx],
        }

    @classmethod
    def format_date(cls, year: int, seconds72: int = None) -> str:
        """Format a DF date as human-readable string.

        Examples:
            format_date(42)           -> "Year 42"
            format_date(42, 0)        -> "the 1st of Granite, Year 42"
            format_date(42, 100800)   -> "the 1st of Limestone, Year 42"
        """
        if year is None:
            return "Unknown date"
        if seconds72 is None or seconds72 < 0:
            return f"Year {year}"
        if seconds72 == 0:
            return f"the 1st of Granite, Year {year}"
        date = cls.from_seconds72(year, seconds72)
        if date['month'] is None:
            return f"Year {year}"
        return f"the {cls._ordinal(date['day'])} of {date['month']}, Year {year}"

    @classmethod
    def format_season(cls, year: int, seconds72: int = None) -> str:
        """Format as season string.

        Examples:
            format_season(42, 0)      -> "Early Spring, Year 42"
            format_season(42, 100800) -> "Early Autumn, Year 42"
        """
        if year is None:
            return "Unknown"
        if seconds72 is None or seconds72 < 0:
            return f"Year {year}"
        date = cls.from_seconds72(year, seconds72)
        if date['season'] is None:
            return f"Year {year}"
        return f"{date['season_part']} {date['season']}, Year {year}"

    @classmethod
    def format_short(cls, year: int, seconds72: int = None) -> str:
        """Short date format for table columns.

        Examples:
            format_short(42)          -> "Y42"
            format_short(42, 0)       -> "Y42 Granite 1"
            format_short(42, 100800)  -> "Y42 Limestone 1"
        """
        if year is None:
            return "?"
        if seconds72 is None or seconds72 < 0:
            return f"Y{year}"
        date = cls.from_seconds72(year, seconds72)
        if date['month'] is None:
            return f"Y{year}"
        return f"Y{year} {date['month']} {date['day']}"

    @staticmethod
    def _ordinal(n: int) -> str:
        """Convert integer to ordinal string (1st, 2nd, 3rd, etc.)."""
        if n is None:
            return "?"
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(
            n % 10 if n % 100 not in (11, 12, 13) else 0, 'th'
        )
        return f"{n}{suffix}"
