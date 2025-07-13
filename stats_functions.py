"""
Functions for Overwatch 2 statistics analysis and reporting.
"""

# stats_functions.py

import sqlite3
from datetime import datetime
from typing import List, Optional
from map_categories import GAME_MODES
from seasons import get_season_from_date
import config
import logging


def validate_seasons_param(seasons: Optional[List[int]]):
    """Helper function to validate seasons parameter"""
    if seasons is not None:
        if not isinstance(seasons, list):
            raise TypeError("seasons parameter must be a list (even for single season). "
                            "Example: use [16] instead of 16.")
        if not all(isinstance(s, int) for s in seasons):
            raise TypeError("All season values must be integers")


def validate_date_string(date_str, date_format="%Y-%m-%d"):
    """Validate a date string format"""
    try:
        datetime.strptime(date_str, date_format)
        return True
    except ValueError:
        return False


def validate_time_frame(start_date, end_date):
    """Validate that the time frame is valid (start before end)"""
    if not start_date and not end_date:
        return True

    try:
        start = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
        end = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None

        if start and end and start > end:
            return False
        return True
    except ValueError:
        return False


def filter_matches_by_time_and_season(rows, start_date: str | None, end_date: str | None, seasons: list[int] | None):
    """Filter iterable of rows by date and season."""
    filtered = []
    for row in rows:
        match_time = datetime.strptime(row['date'], config.DATE_OUTPUT_FORMAT)
        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            if match_time.date() < start_dt.date():
                continue
        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            if match_time.date() > end_dt.date():
                continue
        match_season = get_season_from_date(row['date'])
        if seasons and match_season not in seasons:
            continue
        filtered.append(row)
    return filtered


def delete_match_by_date(match_date: str) -> str:
    """Delete a match by its date"""
    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM matches WHERE date = ?", (match_date,))
            count = cursor.fetchone()[0]
            if count == 0:
                return f"No match found with date: {match_date}"
            cursor.execute("DELETE FROM matches WHERE date = ?", (match_date,))
            conn.commit()
        return f"Successfully deleted match with date: {match_date} (UTC)"
    except Exception as e:
        logging.error(f"Error deleting match: {e}")
        return f"Error deleting match: {str(e)}"


def print_win_percentages_by_season(seasons: Optional[List[int]] = None, min_matches=1, start_date=None, end_date=None) -> str:
    """Calculate win percentages, optionally filtered by season(s) and time frame"""
    output = []
    validate_seasons_param(seasons)

    if not validate_time_frame(start_date, end_date):
        raise ValueError("Invalid time frame - start date must be before end date")

    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT date, map, result FROM matches')
        rows = cursor.fetchall()

    filtered_rows = filter_matches_by_time_and_season(rows, start_date, end_date, seasons)

    title = "Win Percentage by Map"
    if seasons:
        if len(seasons) == 1:
            title += f" (Season {seasons[0]})"
        else:
            title += f" (Seasons {', '.join(map(str, sorted(seasons)))})"
    if start_date or end_date:
        title += f" ({start_date or 'Start'} to {end_date or 'Now'})"
    output.append(f"\n{title}:\n")
    output.append("-" * 70 + "\n")
    output.append(f"{'Map':<25} | {'Played':>7} | {'Wins':>6} | {'Losses':>7} | {'Draws':>7} | {'Win %':>6}\n")
    output.append("-" * 70 + "\n")

    map_stats = {}

    for row in filtered_rows:
        map_name = row['map']
        if map_name not in map_stats:
            map_stats[map_name] = {'wins': 0, 'losses': 0, 'draws': 0}

        if row['result'] == 'VICTORY':
            map_stats[map_name]['wins'] += 1
        elif row['result'] == 'DEFEAT':
            map_stats[map_name]['losses'] += 1
        elif row['result'] == 'DRAW':
            map_stats[map_name]['draws'] += 1

    valid_maps = []
    for map_name, stats in map_stats.items():
        total_played = stats['wins'] + stats['losses'] + stats['draws']
        if total_played >= min_matches and (stats['wins'] + stats['losses']) > 0:
            win_percent = (stats['wins'] / (stats['wins'] + stats['losses'])) * 100
            valid_maps.append((map_name, stats, win_percent))

    valid_maps.sort(key=lambda x: x[2], reverse=True)

    for map_name, stats, win_percent in valid_maps:
        total_played = stats['wins'] + stats['losses'] + stats['draws']
        output.append(
            f"{map_name:<25} | "
            f"{total_played:>7} | "
            f"{stats['wins']:>6} | "
            f"{stats['losses']:>7} | "
            f"{stats['draws']:>7} | "
            f"{win_percent:>5.1f}%\n"
        )

    excluded = [m for m in map_stats
                if (map_stats[m]['wins'] + map_stats[m]['losses'] + map_stats[m]['draws']) < min_matches]
    if excluded:
        output.append(f"\nNote: Excluded {len(excluded)} maps with fewer than {min_matches} matches\n")

    return "".join(output)


def print_hero_win_percentages_by_season(seasons: Optional[List[int]] = None, min_matches=1, start_date=None,
                                         end_date=None) -> str:
    """Calculate win percentages for each hero, weighted by playtime percentage"""
    output = []
    validate_seasons_param(seasons)

    if not validate_time_frame(start_date, end_date):
        raise ValueError("Invalid time frame - start date must be before end date")

    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT m.id, m.date, m.result, mh.hero_name, mh.play_percentage
            FROM matches m
            JOIN match_heroes mh ON m.id = mh.match_id
            ORDER BY m.date
        ''')
        rows = cursor.fetchall()

    filtered_rows = filter_matches_by_time_and_season(rows, start_date, end_date, seasons)

    title = "Hero Win Percentages (Weighted by Playtime)"
    if seasons:
        if len(seasons) == 1:
            title += f" (Season {seasons[0]})"
        else:
            title += f" (Seasons {', '.join(map(str, sorted(seasons)))})"
    if start_date or end_date:
        title += f" ({start_date or 'Start'} to {end_date or 'Now'})"
    output.append(f"\n{title}:\n")
    output.append("-" * 90 + "\n")
    output.append(f"{'Hero':<20} | {'Matches':>8} | {'Weighted Wins':>14} | {'Weighted Losses':>16} | {'Win %':>6}\n")
    output.append("-" * 90 + "\n")

    hero_stats = {}

    for row in filtered_rows:
        hero = row['hero_name']
        if hero not in hero_stats:
            hero_stats[hero] = {
                'weighted_wins': 0.0,
                'weighted_losses': 0.0,
                'matches': 0
            }

        # Calculate weighted contribution based on play percentage
        weight = row['play_percentage'] / 100.0
        hero_stats[hero]['matches'] += 1

        if row['result'] == 'VICTORY':
            hero_stats[hero]['weighted_wins'] += weight
        elif row['result'] == 'DEFEAT':
            hero_stats[hero]['weighted_losses'] += weight

    # Calculate win percentages and filter by minimum matches
    valid_heroes = []
    for hero, stats in hero_stats.items():
        total_weighted = stats['weighted_wins'] + stats['weighted_losses']
        if stats['matches'] >= min_matches and total_weighted > 0:
            win_percent = (stats['weighted_wins'] / total_weighted) * 100
            valid_heroes.append((hero, stats, win_percent))

    # Sort by win percentage (highest first)
    valid_heroes.sort(key=lambda x: x[2], reverse=True)

    for hero, stats, win_percent in valid_heroes:
        output.append(
            f"{hero:<20} | "
            f"{stats['matches']:>8} | "
            f"{stats['weighted_wins']:>14.1f} | "
            f"{stats['weighted_losses']:>16.1f} | "
            f"{win_percent:>5.1f}%\n"
        )

    excluded = [h for h in hero_stats
                if hero_stats[h]['matches'] < min_matches]
    if excluded:
        output.append(f"\nNote: Excluded {len(excluded)} heroes with fewer than {min_matches} matches\n")

    return "".join(output)


def print_hero_map_win_percentages(hero_name: str, seasons: Optional[List[int]] = None, min_matches=1, start_date=None,
                                   end_date=None) -> str:
    """Calculate win percentages for a specific hero across all maps"""
    output = []
    validate_seasons_param(seasons)

    if not validate_time_frame(start_date, end_date):
        raise ValueError("Invalid time frame - start date must be before end date")

    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT m.date, m.map, m.result, mh.play_percentage
            FROM matches m
            JOIN match_heroes mh ON m.id = mh.match_id
            WHERE mh.hero_name = ?
        ''', (hero_name,))
        rows = cursor.fetchall()

    filtered_rows = filter_matches_by_time_and_season(rows, start_date, end_date, seasons)

    title = f"Map Win Percentages for {hero_name}"
    if seasons:
        if len(seasons) == 1:
            title += f" (Season {seasons[0]})"
        else:
            title += f" (Seasons {', '.join(map(str, sorted(seasons)))})"
    if start_date or end_date:
        title += f" ({start_date or 'Start'} to {end_date or 'Now'})"
    output.append(f"\n{title}:\n")
    output.append("-" * 70 + "\n")
    output.append(f"{'Map':<25} | {'Played':>7} | {'Wins':>6} | {'Losses':>7} | {'Draws':>7} | {'Win %':>6}\n")
    output.append("-" * 70 + "\n")

    map_stats = {}

    for row in filtered_rows:
        map_name = row['map']
        if map_name not in map_stats:
            map_stats[map_name] = {'wins': 0, 'losses': 0, 'draws': 0}

        # Calculate weighted contribution based on play percentage
        weight = row['play_percentage'] / 100.0

        if row['result'] == 'VICTORY':
            map_stats[map_name]['wins'] += weight
        elif row['result'] == 'DEFEAT':
            map_stats[map_name]['losses'] += weight
        elif row['result'] == 'DRAW':
            map_stats[map_name]['draws'] += weight

    valid_maps = []
    for map_name, stats in map_stats.items():
        total_played = stats['wins'] + stats['losses'] + stats['draws']
        if total_played >= min_matches and (stats['wins'] + stats['losses']) > 0:
            win_percent = (stats['wins'] / (stats['wins'] + stats['losses'])) * 100
            valid_maps.append((map_name, stats, win_percent))

    valid_maps.sort(key=lambda x: x[2], reverse=True)

    for map_name, stats, win_percent in valid_maps:
        total_played = stats['wins'] + stats['losses'] + stats['draws']
        output.append(
            f"{map_name:<25} | "
            f"{total_played:>7.1f} | "
            f"{stats['wins']:>6.1f} | "
            f"{stats['losses']:>7.1f} | "
            f"{stats['draws']:>7.1f} | "
            f"{win_percent:>5.1f}%\n"
        )

    excluded = [m for m in map_stats
                if (map_stats[m]['wins'] + map_stats[m]['losses'] + map_stats[m]['draws']) < min_matches]
    if excluded:
        output.append(f"\nNote: Excluded {len(excluded)} maps with fewer than {min_matches} matches\n")

    return "".join(output) if valid_maps else f"\nNo data found for {hero_name} with the current filters\n"


def print_map_hero_win_percentages(map_name: str, seasons: Optional[List[int]] = None, min_matches=1, start_date=None,
                                   end_date=None) -> str:
    """Calculate win percentages for all heroes on a specific map"""
    output = []
    validate_seasons_param(seasons)

    if not validate_time_frame(start_date, end_date):
        raise ValueError("Invalid time frame - start date must be before end date")

    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT m.date, m.result, mh.hero_name, mh.play_percentage
            FROM matches m
            JOIN match_heroes mh ON m.id = mh.match_id
            WHERE m.map = ?
        ''', (map_name,))
        rows = cursor.fetchall()

    filtered_rows = filter_matches_by_time_and_season(rows, start_date, end_date, seasons)

    title = f"Hero Win Percentages on {map_name}"
    if seasons:
        if len(seasons) == 1:
            title += f" (Season {seasons[0]})"
        else:
            title += f" (Seasons {', '.join(map(str, sorted(seasons)))})"
    if start_date or end_date:
        title += f" ({start_date or 'Start'} to {end_date or 'Now'})"
    output.append(f"\n{title}:\n")
    output.append("-" * 90 + "\n")
    output.append(f"{'Hero':<20} | {'Matches':>8} | {'Weighted Wins':>14} | {'Weighted Losses':>16} | {'Win %':>6}\n")
    output.append("-" * 90 + "\n")

    hero_stats = {}

    for row in filtered_rows:
        hero = row['hero_name']
        if hero not in hero_stats:
            hero_stats[hero] = {
                'weighted_wins': 0.0,
                'weighted_losses': 0.0,
                'matches': 0
            }

        # Calculate weighted contribution based on play percentage
        weight = row['play_percentage'] / 100.0
        hero_stats[hero]['matches'] += 1

        if row['result'] == 'VICTORY':
            hero_stats[hero]['weighted_wins'] += weight
        elif row['result'] == 'DEFEAT':
            hero_stats[hero]['weighted_losses'] += weight

    valid_heroes = []
    for hero, stats in hero_stats.items():
        total_weighted = stats['weighted_wins'] + stats['weighted_losses']
        if stats['matches'] >= min_matches and total_weighted > 0:
            win_percent = (stats['weighted_wins'] / total_weighted) * 100
            valid_heroes.append((hero, stats, win_percent))

    valid_heroes.sort(key=lambda x: x[2], reverse=True)

    for hero, stats, win_percent in valid_heroes:
        output.append(
            f"{hero:<20} | "
            f"{stats['matches']:>8} | "
            f"{stats['weighted_wins']:>14.1f} | "
            f"{stats['weighted_losses']:>16.1f} | "
            f"{win_percent:>5.1f}%\n"
        )

    excluded = [h for h in hero_stats
                if hero_stats[h]['matches'] < min_matches]
    if excluded:
        output.append(f"\nNote: Excluded {len(excluded)} heroes with fewer than {min_matches} matches\n")

    return "".join(output) if valid_heroes else f"\nNo data found for {map_name} with the current filters\n"


def print_all_matches_by_season(seasons: Optional[List[int]] = None, start_date=None, end_date=None):
    """List all matches with hero data (sorted by percentage) using a single JOIN query"""
    output = []
    validate_seasons_param(seasons)

    if not validate_time_frame(start_date, end_date):
        raise ValueError("Invalid time frame - start date must be before end date")

    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        # Get all matches with their heroes sorted by percentage
        cursor.execute('''
            SELECT 
                m.id, m.date, m.map, m.result, m.length_sec,
                (
                    SELECT GROUP_CONCAT(hero_data, ', ')
                    FROM (
                        SELECT 
                            hero_name || ' (' || play_percentage || '%)' as hero_data
                        FROM match_heroes 
                        WHERE match_id = m.id
                        ORDER BY play_percentage DESC
                    )
                ) AS heroes
            FROM matches m
            ORDER BY m.date DESC
        ''')
        rows = cursor.fetchall()

    filtered_rows = filter_matches_by_time_and_season(rows, start_date, end_date, seasons)

    title = "Overwatch Match Database"
    if seasons:
        if len(seasons) == 1:
            title += f" (Season {seasons[0]})"
        else:
            title += f" (Seasons {', '.join(map(str, sorted(seasons)))})"
    if start_date or end_date:
        title += f" ({start_date or 'Start'} to {end_date or 'Now'})"
    output.append(f"\n{title} - {len(filtered_rows)} Matches\n")
    output.append("-" * 110 + "\n")
    output.append(f"{'Date':<12} | {'Time':<8} | {'Map':<22} | {'Result':<8} | {'Duration':<9} | {'Heroes'}\n")
    output.append("-" * 110 + "\n")

    for match in filtered_rows:
        utc_time = datetime.strptime(match['date'], config.DATE_OUTPUT_FORMAT).replace(tzinfo=config.UTC_TIMEZONE)
        local_time = utc_time.astimezone(config.LOCAL_TIMEZONE)
        minutes, seconds = divmod(match['length_sec'], 60)
        duration_str = f"{minutes}m{seconds:02d}s"

        output.append(
            f"{local_time.strftime('%Y-%m-%d'):<12} | "
            f"{local_time.strftime('%H:%M'):<8} | "
            f"{match['map']:<22} | "
            f"{match['result']:<8} | "
            f"{duration_str:>9} | "
            f"{match['heroes'] if match['heroes'] else 'No hero data'}\n"
        )

    return "".join(output)


def print_summary_stats_by_season(seasons: Optional[List[int]] = None, start_date=None, end_date=None):
    """Print summary statistics, optionally filtered by season(s) and time frame"""
    output = []
    validate_seasons_param(seasons)

    if not validate_time_frame(start_date, end_date):
        raise ValueError("Invalid time frame - start date must be before end date")

    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row  # Add this line
        cursor = conn.cursor()
        title = "Summary Statistics"
        if seasons:
            if len(seasons) == 1:
                title += f" (Season {seasons[0]})"
            else:
                title += f" (Seasons {', '.join(map(str, sorted(seasons)))})"
        if start_date or end_date:
            title += f" ({start_date or 'Start'} to {end_date or 'Now'})"
        output.append(f"\n{title}:\n")

        cursor.execute('SELECT date, result, map FROM matches')
        rows = cursor.fetchall()

    filtered_rows = filter_matches_by_time_and_season(rows, start_date, end_date, seasons)

    output.append(f"Total matches: {len(filtered_rows)}\n")

    results = {'VICTORY': 0, 'DEFEAT': 0, 'DRAW': 0}
    for row in filtered_rows:
        results[row['result']] += 1  # Change from row[1] to row['result']

    output.append("\nResults:\n")
    for result, count in sorted(results.items(), key=lambda x: x[1], reverse=True):
        if count > 0:
            output.append(f"- {result}: {count}\n")

    map_counts = {}
    for row in filtered_rows:
        map_name = row['map']  # Change from row[2] to row['map']
        map_counts[map_name] = map_counts.get(map_name, 0) + 1

    output.append("\nTop 5 Maps:\n")
    for map_name, count in sorted(map_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
        output.append(f"- {map_name}: {count} matches\n")

    return "".join(output)


def print_map_frequency_stats_by_season(seasons: Optional[List[int]] = None, start_date=None, end_date=None):
    """Show map frequency and win percentages, optionally filtered by season(s) and time frame"""
    output = []
    validate_seasons_param(seasons)

    if not validate_time_frame(start_date, end_date):
        raise ValueError("Invalid time frame - start date must be before end date")

    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row  # Add this line
        cursor = conn.cursor()
        title = "Map Frequency and Win Percentages"
        if seasons:
            if len(seasons) == 1:
                title += f" (Season {seasons[0]})"
            else:
                title += f" (Seasons {', '.join(map(str, sorted(seasons)))})"
        if start_date or end_date:
            title += f" ({start_date or 'Start'} to {end_date or 'Now'})"
        output.append(f"\n{title}:\n")
        output.append("-" * 70 + "\n")
        output.append(f"{'Map':<25} | {'Played':>7} | {'Win %':>6} | {'Wins':>6} | {'Losses':>7} | {'Draws':>7}\n")
        output.append("-" * 70 + "\n")

        cursor.execute('SELECT date, map, result FROM matches')
        rows = cursor.fetchall()

    filtered_rows = filter_matches_by_time_and_season(rows, start_date, end_date, seasons)

    map_stats = {}

    for row in filtered_rows:
        map_name = row['map']  # Change from row[1] to row['map']
        result = row['result']  # Change from row[2] to row['result']

        if map_name not in map_stats:
            map_stats[map_name] = {'wins': 0, 'losses': 0, 'draws': 0}

        if result == 'VICTORY':
            map_stats[map_name]['wins'] += 1
        elif result == 'DEFEAT':
            map_stats[map_name]['losses'] += 1
        elif result == 'DRAW':
            map_stats[map_name]['draws'] += 1

    # Calculate stats for each map
    map_data = []
    for map_name, stats in map_stats.items():
        total_played = stats['wins'] + stats['losses'] + stats['draws']
        win_percent = (stats['wins'] / (stats['wins'] + stats['losses'])) * 100 if (stats['wins'] + stats['losses']) > 0 else 0
        map_data.append((map_name, total_played, win_percent, stats['wins'], stats['losses'], stats['draws']))

    # Sort by most played to least played
    map_data.sort(key=lambda x: x[1], reverse=True)

    for map_name, total_played, win_percent, wins, losses, draws in map_data:
        output.append(
            f"{map_name:<25} | "
            f"{total_played:>7} | "
            f"{win_percent:>5.1f}% | "
            f"{wins:>6} | "
            f"{losses:>7} | "
            f"{draws:>7}\n"
        )

    return "".join(output)


def print_game_mode_stats_by_season(seasons: Optional[List[int]] = None, start_date=None, end_date=None):
    """Analyze by game mode, optionally filtered by season(s) and time frame"""
    output = []
    validate_seasons_param(seasons)

    if not validate_time_frame(start_date, end_date):
        raise ValueError("Invalid time frame - start date must be before end date")

    with sqlite3.connect(config.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row  # Add this line
        cursor = conn.cursor()
        title = "Win Percentage by Game Mode"
        if seasons:
            if len(seasons) == 1:
                title += f" (Season {seasons[0]})"
            else:
                title += f" (Seasons {', '.join(map(str, sorted(seasons)))})"
        if start_date or end_date:
            title += f" ({start_date or 'Start'} to {end_date or 'Now'})"
        output.append(f"\n{title}:\n")

        MAP_MODES = {}
        for mode, maps in GAME_MODES.items():
            for map_name in maps:
                MAP_MODES[map_name] = mode

        cursor.execute('SELECT date, map, result, length_sec FROM matches')
        rows = cursor.fetchall()

    filtered_rows = filter_matches_by_time_and_season(rows, start_date, end_date, seasons)

    mode_stats = {}
    for mode in GAME_MODES:
        mode_stats[mode] = {'matches': 0, 'wins': 0, 'losses': 0, 'total_time': 0}

    for row in filtered_rows:
        map_name = row['map']  # Change from row[1] to row['map']
        if map_name in MAP_MODES:
            mode = MAP_MODES[map_name]
            mode_stats[mode]['matches'] += 1
            mode_stats[mode]['total_time'] += row['length_sec']  # Change from row[3] to row['length_sec']
            if row['result'] == 'VICTORY':  # Change from row[2] to row['result']
                mode_stats[mode]['wins'] += 1
            elif row['result'] == 'DEFEAT':  # Change from row[2] to row['result']
                mode_stats[mode]['losses'] += 1

    output.append("-" * 90 + "\n")
    output.append(
        f"{'Game Mode':<15} | {'Matches':>8} | {'Wins':>6} | {'Losses':>7} | {'Win %':>6} | {'Avg Time':>9} | {'Sample Maps'}\n")
    output.append("-" * 90 + "\n")

    for mode, stats in sorted(mode_stats.items(), key=lambda x: x[1]['matches'], reverse=True):
        if stats['matches'] > 0:
            win_rate = (stats['wins'] / (stats['wins'] + stats['losses'])) * 100 if (stats['wins'] + stats['losses']) > 0 else 0
            avg_time = (stats['total_time'] / stats['matches']) / 60
            sample_maps = ", ".join(GAME_MODES[mode][:3])

            output.append(
                f"{mode:<15} | "
                f"{stats['matches']:>8} | "
                f"{stats['wins']:>6} | "
                f"{stats['losses']:>7} | "
                f"{win_rate:>5.1f}% | "
                f"{avg_time:>7.1f}m | "
                f"{sample_maps}\n"
            )

    return "".join(output)


# Lambda functions for simplified calling
print_win_percentages = lambda seasons=None, min_matches=1, start_date=None, end_date=None: print_win_percentages_by_season(seasons, min_matches, start_date, end_date)
print_all_matches = lambda seasons=None, start_date=None, end_date=None: print_all_matches_by_season(seasons, start_date, end_date)
print_summary_stats = lambda seasons=None, start_date=None, end_date=None: print_summary_stats_by_season(seasons, start_date, end_date)
print_map_frequency_stats = lambda seasons=None, start_date=None, end_date=None: print_map_frequency_stats_by_season(seasons, start_date, end_date)
print_game_mode_stats = lambda seasons=None, start_date=None, end_date=None: print_game_mode_stats_by_season(seasons, start_date, end_date)
print_hero_win_percentages = lambda seasons=None, min_matches=1, start_date=None, end_date=None: print_hero_win_percentages_by_season(seasons, min_matches, start_date, end_date)

def calculate_stats(data: list) -> dict:
    """
    Calculate statistics from the provided data.

    Args:
        data (list): List of data entries.

    Returns:
        dict: Calculated statistics.
    """
    try:
        # TODO: Implement calculation logic
        return {}
    except Exception as e:
        logging.error(f"Error calculating stats: {e}")
        return {}