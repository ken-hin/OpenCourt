# helpers.py — Shared constants, API configuration, client factory, and
# helper functions used across fetch, sync, and update modules.
#
# Everything in this file is internal plumbing. External callers (management
# commands, views) should import from opencourt.services (the __init__.py),
# not from this file directly.

import logging
import os
from datetime import date, datetime, timedelta

import cbbd

from opencourt.models import Team, Conference

logger = logging.getLogger('opencourt.services')


# =============================================================================
# API Configuration
# =============================================================================
# Shared config object used by every fetch function. The API key is read
# once at module import time from the environment. Both api_key and
# access_token are set because the cbbd client uses different auth headers
# depending on the endpoint.
configuration = cbbd.Configuration(
    host="https://api.collegebasketballdata.com",
    api_key=os.environ.get('CBB_API_KEY'),
    access_token=os.environ.get('CBB_API_KEY'),
)


# =============================================================================
# Constants
# =============================================================================
# --- API endpoint names ---
# Passed to init_api_client() to get the right typed client. These match
# the class names in the cbbd library (e.g. cbbd.TeamsApi).
TEAMS_ENDPOINT = 'TeamsApi'
CONFERENCES_ENDPOINT = 'ConferencesApi'
STATS_ENDPOINT = 'StatsApi'
GAMES_ENDPOINT = 'GamesApi'
RANKINGS_ENDPOINT = 'RankingsApi'
RATINGS_ENDPOINT = 'RatingsApi'

# --- Year constants ---
CURRENT_YEAR = date.today().year
LAST_YEAR = CURRENT_YEAR - 1
STATS_START_YEAR = CURRENT_YEAR - 9
RANKINGS_START_YEAR = CURRENT_YEAR - 9
GAMES_HISTORY_START_YEAR = CURRENT_YEAR - 9

# --- Rate limiting / retry ---
MAX_RETRIES = 4
RETRY_BASE_DELAY = 5
BETWEEN_CALLS_DELAY = 1


# =============================================================================
# API Client Factory
# =============================================================================

def init_api_client(config, endpoint):
    """
    Create and return a typed CBBData API client for the given endpoint.

    Wraps the shared configuration in an ApiClient, then returns the
    correct endpoint-specific instance (TeamsApi, ConferencesApi, etc.).
    Centralizing this means fetch functions don't repeat client setup.

    Args:
        config:   cbbd.Configuration — pre-configured with host + API key.
        endpoint: str — one of the *_ENDPOINT constants defined above.

    Returns:
        The matching cbbd.*Api instance, ready to call .get_*() methods on.

    Raises:
        ValueError:      If the endpoint string doesn't match any known API class.
        ConnectionError: If the API client can't be created (bad key, network issue).
    """
    try:
        api_client = cbbd.ApiClient(config)
    except Exception as exc:
        logger.error("Failed to create API client — check CBB_API_KEY and host: %s", exc)
        raise ConnectionError(f"Could not initialize CBBData API client: {exc}") from exc

    match endpoint:
        case 'ConferencesApi':
            api_instance = cbbd.ConferencesApi(api_client)
        case 'TeamsApi':
            api_instance = cbbd.TeamsApi(api_client)
        case 'StatsApi':
            api_instance = cbbd.StatsApi(api_client)
        case 'GamesApi':
            api_instance = cbbd.GamesApi(api_client)
        case 'RankingsApi':
            api_instance = cbbd.RankingsApi(api_client)
        case 'RatingsApi':
            api_instance = cbbd.RatingsApi(api_client)
        case _:
            raise ValueError(f"Invalid endpoint: {endpoint}")

    return api_instance


# =============================================================================
# Lookup Builders
# =============================================================================

def _build_team_lookup():
    """
    Build a lowercase school name -> Team object lookup dict.

    Returns:
        dict: {school_name_lower: Team} for fast FK resolution.
    """
    return {t.school.lower(): t for t in Team.objects.all()}


def _build_conf_lookup():
    """
    Build a lowercase conference abbreviation -> Conference object lookup dict.

    Returns:
        dict: {conf_abbrv_lower: Conference} for fast FK resolution.
    """
    return {c.abbrv.lower(): c for c in Conference.objects.all()}


# =============================================================================
# Defaults Builders (API dict -> ORM update_or_create defaults)
# =============================================================================

def _build_season_stats_defaults(team_stat_dict):
    """
    Extract the defaults dict for TeamSeasonStats.objects.update_or_create()
    from a raw API team stat response.

    Parses the nested teamStats and opponentStats sections, drilling down
    into fieldGoals, freeThrows, points, rebounds, turnovers, and fourFactors
    sub-objects to extract ~50 fields.

    Args:
        team_stat_dict: dict — the full response dict from fetch_season_stats_bulk(),
                              after .to_dict() conversion.

    Returns:
        dict: The defaults= dict ready for update_or_create().
    """
    stat_dict         = team_stat_dict.get('teamStats', {})
    fg_dict           = stat_dict.get('fieldGoals', {})
    fg_2pt_dict       = stat_dict.get('twoPointFieldGoals', {})
    fg_3pt_dict       = stat_dict.get('threePointFieldGoals', {})
    ft_dict           = stat_dict.get('freeThrows', {})
    points_dict       = stat_dict.get('points', {})
    rebounds_dict     = stat_dict.get('rebounds', {})
    turnovers_dict    = stat_dict.get('turnovers', {})
    four_factors_dict = stat_dict.get('fourFactors', {})

    opp_stat_dict         = team_stat_dict.get('opponentStats', {})
    opp_fg_dict           = opp_stat_dict.get('fieldGoals', {})
    opp_2pt_dict          = opp_stat_dict.get('twoPointFieldGoals', {})
    opp_3pt_dict          = opp_stat_dict.get('threePointFieldGoals', {})
    opp_ft_dict           = opp_stat_dict.get('freeThrows', {})
    opp_points_dict       = opp_stat_dict.get('points', {})
    opp_rebounds_dict     = opp_stat_dict.get('rebounds', {})
    opp_turnovers_dict    = opp_stat_dict.get('turnovers', {})
    opp_four_factors_dict = opp_stat_dict.get('fourFactors', {})

    return {
        'season_label' : team_stat_dict.get('seasonLabel'),
        'games'        : team_stat_dict.get('games'),
        'wins'         : team_stat_dict.get('wins'),
        'losses'       : team_stat_dict.get('losses'),
        'total_minutes': team_stat_dict.get('totalMinutes'),
        'pace'         : team_stat_dict.get('pace'),
        'off_fg_made'      : fg_dict.get('made'),
        'off_fg_attempted' : fg_dict.get('attempted'),
        'off_fg_pct'       : fg_dict.get('pct'),
        'off_2pt_made'     : fg_2pt_dict.get('made'),
        'off_2pt_attempted': fg_2pt_dict.get('attempted'),
        'off_2pt_pct'      : fg_2pt_dict.get('pct'),
        'off_3pt_made'     : fg_3pt_dict.get('made'),
        'off_3pt_attempted': fg_3pt_dict.get('attempted'),
        'off_3pt_pct'      : fg_3pt_dict.get('pct'),
        'off_ft_made'      : ft_dict.get('made'),
        'off_ft_attempted' : ft_dict.get('attempted'),
        'off_ft_pct'       : ft_dict.get('pct'),
        'off_points'   : points_dict.get('total'),
        'off_assists'  : stat_dict.get('assists'),
        'off_steals'   : stat_dict.get('steals'),
        'off_blocks'   : stat_dict.get('blocks'),
        'off_turnovers': turnovers_dict.get('total'),
        'off_reb_total'    : rebounds_dict.get('total'),
        'off_reb_offensive': rebounds_dict.get('offensive'),
        'off_reb_defensive': rebounds_dict.get('defensive'),
        'off_eff_fg_pct'    : four_factors_dict.get('effectiveFieldGoalPct'),
        'off_ft_rate'       : four_factors_dict.get('freeThrowRate'),
        'off_oreb_pct'      : four_factors_dict.get('offensiveReboundPct'),
        'off_turnover_ratio': four_factors_dict.get('turnoverRatio'),
        'off_true_shooting' : stat_dict.get('trueShooting'),
        'off_rating'        : stat_dict.get('rating'),
        'off_possessions'   : stat_dict.get('possessions'),
        'opp_fg_pct'        : opp_fg_dict.get('pct'),
        'opp_2pt_pct'       : opp_2pt_dict.get('pct'),
        'opp_3pt_pct'       : opp_3pt_dict.get('pct'),
        'opp_ft_pct'        : opp_ft_dict.get('pct'),
        'opp_points'        : opp_points_dict.get('total'),
        'opp_assists'       : opp_stat_dict.get('assists'),
        'opp_turnovers'     : opp_turnovers_dict.get('total'),
        'opp_reb_total'     : opp_rebounds_dict.get('total'),
        'opp_reb_offensive' : opp_rebounds_dict.get('offensive'),
        'opp_eff_fg_pct'    : opp_four_factors_dict.get('effectiveFieldGoalPct'),
        'opp_ft_rate'       : opp_four_factors_dict.get('freeThrowRate'),
        'opp_turnover_ratio': opp_four_factors_dict.get('turnoverRatio'),
        'opp_true_shooting' : opp_stat_dict.get('trueShooting'),
        'opp_rating'        : opp_stat_dict.get('rating'),
    }


def _build_game_defaults(game_dict, home_team_obj, away_team_obj, home_conf, away_conf):
    """
    Extract the defaults dict for Game.objects.update_or_create() from a raw
    API game dict.

    Args:
        game_dict: dict — the game response after .to_dict() conversion.
        home_team_obj: Team object for the home team (already FK-resolved).
        away_team_obj: Team object for the away team (already FK-resolved).
        home_conf: Conference object or None for the home team's conference.
        away_conf: Conference object or None for the away team's conference.

    Returns:
        dict: The defaults= dict ready for update_or_create().
    """
    return {
        'season': game_dict.get('season'),
        'season_label': game_dict.get('seasonLabel', ''),
        'season_type': game_dict.get('seasonType'),
        'tournament': game_dict.get('tournament'),
        'game_type': game_dict.get('gameType'),
        'game_notes': game_dict.get('gameNotes'),
        'status': game_dict.get('status'),
        'start_date': game_dict.get('startDate'),
        'start_time_tbd': game_dict.get('startTimeTbd', False),
        'home_team': home_team_obj,
        'home_conference': home_conf,
        'home_seed': game_dict.get('homeSeed'),
        'home_points': game_dict.get('homePoints'),
        'home_period_points': game_dict.get('homePeriodPoints'),
        'home_winner': game_dict.get('homeWinner'),
        'home_elo_start': game_dict.get('homeTeamEloStart'),
        'home_elo_end': game_dict.get('homeTeamEloEnd'),
        'away_team': away_team_obj,
        'away_conference': away_conf,
        'away_seed': game_dict.get('awaySeed'),
        'away_points': game_dict.get('awayPoints'),
        'away_period_points': game_dict.get('awayPeriodPoints'),
        'away_winner': game_dict.get('awayWinner'),
        'away_elo_start': game_dict.get('awayTeamEloStart'),
        'away_elo_end': game_dict.get('awayTeamEloEnd'),
        'neutral_site': game_dict.get('neutralSite', False),
        'conference_game': game_dict.get('conferenceGame', False),
        'attendance': game_dict.get('attendance'),
        'venue_id': game_dict.get('venueId'),
        'venue': game_dict.get('venue'),
        'city': game_dict.get('city'),
        'state': game_dict.get('state'),
        'excitement': game_dict.get('excitement'),
    }


def _build_game_team_stats_defaults(stat_dict):
    """
    Extract the defaults dict for GameTeamStats.objects.update_or_create()
    from a raw API game team stat dict.

    Args:
        stat_dict: dict — the game team stat response after .to_dict() conversion.

    Returns:
        dict: The defaults= dict ready for update_or_create().
    """
    ts = stat_dict.get('teamStats', {})
    fg = ts.get('fieldGoals', {})
    fg_2pt = ts.get('twoPointFieldGoals', {})
    fg_3pt = ts.get('threePointFieldGoals', {})
    ft = ts.get('freeThrows', {})
    pts = ts.get('points', {})
    reb = ts.get('rebounds', {})
    tov = ts.get('turnovers', {})
    ff = ts.get('fourFactors', {})
    fouls = ts.get('fouls', {})

    return {
        'is_home': stat_dict.get('isHome', False),
        'game_minutes': stat_dict.get('gameMinutes'),
        'pace': stat_dict.get('pace'),
        'possessions': ts.get('possessions'),
        'fg_made': fg.get('made'),
        'fg_attempted': fg.get('attempted'),
        'fg_pct': fg.get('pct'),
        'two_pt_made': fg_2pt.get('made'),
        'two_pt_attempted': fg_2pt.get('attempted'),
        'two_pt_pct': fg_2pt.get('pct'),
        'three_pt_made': fg_3pt.get('made'),
        'three_pt_attempted': fg_3pt.get('attempted'),
        'three_pt_pct': fg_3pt.get('pct'),
        'ft_made': ft.get('made'),
        'ft_attempted': ft.get('attempted'),
        'ft_pct': ft.get('pct'),
        'points': pts.get('total'),
        'assists': ts.get('assists'),
        'steals': ts.get('steals'),
        'blocks': ts.get('blocks'),
        'turnovers': tov.get('total'),
        'team_turnovers': tov.get('teamTotal'),
        'reb_total': reb.get('total'),
        'reb_offensive': reb.get('offensive'),
        'reb_defensive': reb.get('defensive'),
        'fouls_total': fouls.get('total'),
        'fouls_technical': fouls.get('technical'),
        'fouls_flagrant': fouls.get('flagrant'),
        'points_fast_break': pts.get('fastBreak'),
        'points_off_turnovers': pts.get('offTurnovers'),
        'points_in_paint': pts.get('inPaint'),
        'points_by_period': pts.get('byPeriod'),
        'largest_lead': pts.get('largestLead'),
        'eff_fg_pct': ff.get('effectiveFieldGoalPct'),
        'ft_rate': ff.get('freeThrowRate'),
        'oreb_pct': ff.get('offensiveReboundPct'),
        'turnover_ratio': ff.get('turnoverRatio'),
        'rating': ts.get('rating'),
        'true_shooting': ts.get('trueShooting'),
        'game_score': ts.get('gameScore'),
    }


# =============================================================================
# Date / Season Helpers
# =============================================================================

def _build_game_date_ranges(season):
    """
    Build monthly date-range windows from November through May for a season.

    The basketball season starts in November of year (season - 1) and runs
    through May of year (season). Returns 7 monthly windows to stay under
    the API's 3,000-row cap per call.

    Args:
        season: int — the season year (e.g., 2025 for 2024-25 season).

    Returns:
        list: [{'start_date_range': datetime, 'end_date_range': datetime}, ...]
    """
    date_ranges = []
    for month in range(11, 13):
        start = datetime(season - 1, month, 1)
        end = datetime(season - 1, month + 1, 1) if month < 12 else datetime(season, 1, 1)
        date_ranges.append({'start_date_range': start, 'end_date_range': end})
    for month in range(1, 6):
        start = datetime(season, month, 1)
        end = datetime(season, month + 1, 1)
        date_ranges.append({'start_date_range': start, 'end_date_range': end})
    return date_ranges


def _current_season_year():
    """
    Get the current basketball season year.

    The season field stores the starting year (e.g. 2025 for the 2025-26 season).
    If we're in Jul-Dec, the season started this year; Jan-Jun it's last year.

    Returns:
        int: The current season year.
    """
    today = date.today()
    return today.year if today.month >= 7 else today.year - 1
