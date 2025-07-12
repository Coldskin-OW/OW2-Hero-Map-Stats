# seasons.py
from datetime import datetime

from config import UTC_TIMEZONE

# Season Definitions in UTC (originally 20:00 CEST = 18:00 UTC during summer time)
SEASON_DATES = {
    15: {
        'start': datetime(2025, 2, 18, 18, 0, tzinfo=UTC_TIMEZONE),
        'end': datetime(2025, 4, 22, 18, 0, tzinfo=UTC_TIMEZONE)
    },
    16: {
        'start': datetime(2025, 4, 22, 18, 0, tzinfo=UTC_TIMEZONE),
        'end': datetime(2025, 6, 24, 18, 0, tzinfo=UTC_TIMEZONE)
    },
    17: {
        'start': datetime(2025, 6, 24, 18, 0, tzinfo=UTC_TIMEZONE),
        'end': datetime(2025, 8, 26, 18, 0, tzinfo=UTC_TIMEZONE)
    }
}


def get_season_from_date(match_date):
    """
    Determine season from match date string ('YYYY-MM-DD HH:MM' format in UTC)
    Returns season number or None if outside defined seasons
    """
    if isinstance(match_date, str):
        match_time = datetime.strptime(match_date, "%Y-%m-%d %H:%M").replace(tzinfo=UTC_TIMEZONE)
    else:
        match_time = match_date  # Assume datetime object with timezone

    for season, dates in SEASON_DATES.items():
        if dates['start'] <= match_time < dates['end']:
            return season
    return None