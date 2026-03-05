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

    @classmethod
    def format_duration(cls, start_year: int, start_seconds: int,
                        end_year: int, end_seconds: int) -> str:
        """Compute and format the duration between two DF timestamps.

        Uses tick-level precision when available, falls back to year-level.

        Examples:
            (100, 0, 100, 1200)       -> "1 day"
            (100, 0, 100, 33600)      -> "1 month"
            (100, 0, 100, 100800)     -> "3 months"
            (100, 0, 102, 0)          -> "2 years"
            (100, 0, 100, 0)          -> "<1 day"
            (100, None, 105, None)    -> "5 years"
        """
        if start_year is None or end_year is None:
            return None

        have_ticks = (start_seconds is not None and start_seconds >= 0
                      and end_seconds is not None and end_seconds >= 0)

        if have_ticks:
            total_ticks = ((end_year - start_year) * cls.TICKS_PER_YEAR
                           + end_seconds - start_seconds)
            if total_ticks < 0:
                total_ticks = 0

            total_days = total_ticks // cls.TICKS_PER_DAY

            if total_days == 0:
                return "<1 day"

            years = total_days // (cls.DAYS_PER_MONTH * cls.MONTHS_PER_YEAR)
            remaining_days = total_days % (cls.DAYS_PER_MONTH * cls.MONTHS_PER_YEAR)
            months = remaining_days // cls.DAYS_PER_MONTH
            days = remaining_days % cls.DAYS_PER_MONTH

            parts = []
            if years:
                parts.append(f"{years} year{'s' if years != 1 else ''}")
            if months:
                parts.append(f"{months} month{'s' if months != 1 else ''}")
            if days and not years:  # skip days when showing years (too granular)
                parts.append(f"{days} day{'s' if days != 1 else ''}")
            return ", ".join(parts) if parts else "<1 day"
        else:
            # Year-level only
            span = end_year - start_year
            if span == 0:
                return "<1 year"
            return f"{span} year{'s' if span != 1 else ''}"

    @classmethod
    def format_timespan(cls, start_year: int, start_seconds: int,
                        end_year: int, end_seconds: int) -> str:
        """Format a full timespan: 'start_date – end_date (duration)'.

        Returns a rich string combining the date range with computed duration.
        """
        start_str = cls.format_date(start_year, start_seconds)
        end_str = cls.format_date(end_year, end_seconds)
        duration = cls.format_duration(start_year, start_seconds,
                                       end_year, end_seconds)
        if start_str == end_str:
            return f"{start_str} ({duration})"
        return f"{start_str} – {end_str} ({duration})"

    @staticmethod
    def _ordinal(n: int) -> str:
        """Convert integer to ordinal string (1st, 2nd, 3rd, etc.)."""
        if n is None:
            return "?"
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(
            n % 10 if n % 100 not in (11, 12, 13) else 0, 'th'
        )
        return f"{n}{suffix}"
