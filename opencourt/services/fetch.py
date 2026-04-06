# fetch.py — Pure API call functions.
#
# Each function hits a single CBBData endpoint, handles errors/retries,
# and returns raw data (or [] on failure). No database writes.
#
# Error handling covers three failure modes consistently:
#   - cbbd.ApiException: API-level HTTP errors (401, 403, 429, 500, etc.)
#   - ConnectionError:   network issues (DNS failure, timeout, refused) or bad client config
#   - ValueError:        invalid endpoint name passed to init_api_client()

import logging
import time

import cbbd

from .helpers import (
    configuration,
    init_api_client,
    TEAMS_ENDPOINT,
    CONFERENCES_ENDPOINT,
    STATS_ENDPOINT,
    GAMES_ENDPOINT,
    RANKINGS_ENDPOINT,
    CURRENT_YEAR,
    MAX_RETRIES,
    RETRY_BASE_DELAY,
)

logger = logging.getLogger('opencourt.services')


def fetch_teams():
    """
    Fetch all Division I teams for the current season from the CBBData API.

    Returns:
        list — cbbd team objects, or [] on any error.

    Notes:
        Uses CURRENT_YEAR as the season parameter, so only teams active in
        the current season are returned. Historically inactive programs won't
        appear.
    """
    try:
        api_instance = init_api_client(configuration, TEAMS_ENDPOINT)
        teams = api_instance.get_teams(season=CURRENT_YEAR)
        return teams
    except cbbd.ApiException as exc:
        logger.error("CBBData API error fetching teams (HTTP %s): %s", exc.status, exc.reason)
        return []
    except ConnectionError as exc:
        logger.error("Connection error fetching teams: %s", exc)
        return []
    except ValueError as exc:
        logger.error("Configuration error in fetch_teams: %s", exc)
        return []


def fetch_conferences():
    """
    Fetch all conferences from the CBBData API.

    Returns:
        list — cbbd conference objects, or [] on any error.

    Notes:
        Returns ALL conferences the API knows about, not just D1. The sync
        function handles filtering downstream.
    """
    try:
        api_instance = init_api_client(configuration, CONFERENCES_ENDPOINT)
        conferences = api_instance.get_conferences()
        return conferences
    except cbbd.ApiException as exc:
        logger.error("CBBData API error fetching conferences (HTTP %s): %s", exc.status, exc.reason)
        return []
    except ConnectionError as exc:
        logger.error("Connection error fetching conferences: %s", exc)
        return []
    except ValueError as exc:
        logger.error("Configuration error in fetch_conferences: %s", exc)
        return []


def fetch_season_stats_bulk(season):
    """
    Fetch season stats for ALL teams in a single season from the CBBData API.

    This is the "chunky" approach recommended by CBBData docs: one call per
    season returns every team's aggregate stats for that year.

    Includes built-in retry with exponential backoff for HTTP 429 responses.

    Args:
        season: int — the season year to fetch (e.g. 2024 for the 2024-25 season).

    Returns:
        list — cbbd stat objects for every team in that season, or [] if all
               retries are exhausted or a non-retryable error occurs.
    """
    for attempt in range(MAX_RETRIES + 1):
        try:
            api_instance = init_api_client(configuration, STATS_ENDPOINT)
            season_stats = api_instance.get_team_season_stats(season=season)
            return season_stats

        except cbbd.ApiException as exc:
            if exc.status == 429:
                if attempt < MAX_RETRIES:
                    retry_after = None
                    if exc.headers:
                        try:
                            retry_after = int(exc.headers.get('Retry-After', 0)) or None
                        except (ValueError, TypeError):
                            pass
                    wait = retry_after if retry_after else RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        "Rate limited on season %s — waiting %ds before retry %d/%d.",
                        season, wait, attempt + 1, MAX_RETRIES
                    )
                    time.sleep(wait)
                    continue
                else:
                    logger.error("Rate limited on season %s — max retries exceeded.", season)
                    return []
            logger.error(
                "CBBData API error fetching bulk stats for season %s (HTTP %s): %s",
                season, exc.status, exc.reason
            )
            return []

        except ConnectionError as exc:
            logger.error("Connection error fetching bulk stats for season %s: %s", season, exc)
            return []

        except ValueError as exc:
            logger.error("Configuration error in fetch_season_stats_bulk: %s", exc)
            return []
    return []


def fetch_rankings_bulk(season):
    """
    Fetch all poll rankings for every team in a single season from the CBBData API.

    One call per season returns every team's weekly ranking entries for that
    year across all poll types (AP, Coaches, etc.).

    Includes built-in retry with exponential backoff for HTTP 429 responses.

    Args:
        season: int — the season year to fetch (e.g. 2024 for the 2024-25 season).

    Returns:
        list — cbbd ranking objects for every ranked team in that season, or []
               if all retries are exhausted or a non-retryable error occurs.
    """
    for attempt in range(MAX_RETRIES + 1):
        try:
            api_instance = init_api_client(configuration, RANKINGS_ENDPOINT)
            rankings = api_instance.get_rankings(season=season)
            return rankings

        except cbbd.ApiException as exc:
            if exc.status == 429:
                if attempt < MAX_RETRIES:
                    retry_after = None
                    if exc.headers:
                        try:
                            retry_after = int(exc.headers.get('Retry-After', 0)) or None
                        except (ValueError, TypeError):
                            pass
                    wait = retry_after if retry_after else RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        "Rate limited fetching rankings for season %s — waiting %ds before retry %d/%d.",
                        season, wait, attempt + 1, MAX_RETRIES
                    )
                    time.sleep(wait)
                    continue
                else:
                    logger.error("Rate limited fetching rankings for season %s — max retries exceeded.", season)
                    return []
            logger.error(
                "CBBData API error fetching rankings for season %s (HTTP %s): %s",
                season, exc.status, exc.reason
            )
            return []

        except ConnectionError as exc:
            logger.error("Connection error fetching rankings for season %s: %s", season, exc)
            return []

        except ValueError as exc:
            logger.error("Configuration error in fetch_rankings_bulk: %s", exc)
            return []
    return []


def fetch_games_bulk(season, start_date_range=None, end_date_range=None):
    """
    Fetch games for a single season from the CBBData /games endpoint.

    The API caps responses at 3,000 games per call. A full D1 season has
    ~5,500 games, so callers should split by date range to get complete data.

    Args:
        season: int — the season year to fetch (e.g. 2025 for 2025-26).
        start_date_range: Optional[datetime] — ISO 8601 start timestamp filter.
        end_date_range: Optional[datetime] — ISO 8601 end timestamp filter.

    Returns:
        list — cbbd GameInfo objects, or [] on any error.
    """
    kwargs = {'season': season}
    if start_date_range:
        kwargs['start_date_range'] = start_date_range
    if end_date_range:
        kwargs['end_date_range'] = end_date_range

    for attempt in range(MAX_RETRIES + 1):
        try:
            api_instance = init_api_client(configuration, GAMES_ENDPOINT)
            games = api_instance.get_games(**kwargs)
            return games

        except cbbd.ApiException as exc:
            if exc.status == 429:
                if attempt < MAX_RETRIES:
                    retry_after = None
                    if exc.headers:
                        try:
                            retry_after = int(exc.headers.get('Retry-After', 0)) or None
                        except (ValueError, TypeError):
                            pass
                    wait = retry_after if retry_after else RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        "Rate limited fetching games for season %s — waiting %ds before retry %d/%d.",
                        season, wait, attempt + 1, MAX_RETRIES
                    )
                    time.sleep(wait)
                    continue
                else:
                    logger.error("Rate limited fetching games for season %s — max retries exceeded.", season)
                    return []
            logger.error(
                "CBBData API error fetching games for season %s (HTTP %s): %s",
                season, exc.status, exc.reason
            )
            return []

        except ConnectionError as exc:
            logger.error("Connection error fetching games for season %s: %s", season, exc)
            return []

        except ValueError as exc:
            logger.error("Configuration error in fetch_games_bulk: %s", exc)
            return []
    return []


def fetch_game_team_stats_bulk(season, start_date_range=None, end_date_range=None):
    """
    Fetch per-team box score stats for games in a single season from
    the CBBData /games/teams endpoint.

    The API caps responses at 3,000 objects per call. Each game produces
    two objects (one per team), so the effective limit is ~1,500 games.
    Callers should split by date range for complete data.

    Args:
        season: int — the season year to fetch.
        start_date_range: Optional[datetime] — ISO 8601 start timestamp filter.
        end_date_range: Optional[datetime] — ISO 8601 end timestamp filter.

    Returns:
        list — cbbd GameBoxScoreTeam objects, or [] on any error.
    """
    kwargs = {'season': season}
    if start_date_range:
        kwargs['start_date_range'] = start_date_range
    if end_date_range:
        kwargs['end_date_range'] = end_date_range

    for attempt in range(MAX_RETRIES + 1):
        try:
            api_instance = init_api_client(configuration, GAMES_ENDPOINT)
            stats = api_instance.get_game_teams(**kwargs)
            return stats

        except cbbd.ApiException as exc:
            if exc.status == 429:
                if attempt < MAX_RETRIES:
                    retry_after = None
                    if exc.headers:
                        try:
                            retry_after = int(exc.headers.get('Retry-After', 0)) or None
                        except (ValueError, TypeError):
                            pass
                    wait = retry_after if retry_after else RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        "Rate limited fetching game team stats for season %s — waiting %ds before retry %d/%d.",
                        season, wait, attempt + 1, MAX_RETRIES
                    )
                    time.sleep(wait)
                    continue
                else:
                    logger.error("Rate limited fetching game team stats for season %s — max retries exceeded.", season)
                    return []
            logger.error(
                "CBBData API error fetching game team stats for season %s (HTTP %s): %s",
                season, exc.status, exc.reason
            )
            return []

        except ConnectionError as exc:
            logger.error("Connection error fetching game team stats for season %s: %s", season, exc)
            return []

        except ValueError as exc:
            logger.error("Configuration error in fetch_game_team_stats_bulk: %s", exc)
            return []
    return []
