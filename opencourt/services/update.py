# update.py — Incremental database update functions (last 30 days only).
#
# These are lighter-weight alternatives to the full sync_* functions in sync.py.
# Instead of pulling an entire season's data (many API calls, thousands of
# rows), they only fetch the last 30 days of games and the current season's
# stats/rankings. Ideal for daily/weekly cron jobs to keep the DB current
# without hammering the API.
#
# Total: ~5 API calls vs ~30+ for a full sync.
#
# These do NOT replace the sync_* functions. Use sync_* for initial DB setup
# or if you need to backfill historical data.
#
# Usage:
#   python manage.py update_data          (runs all update steps)

import logging
from datetime import date, datetime, timedelta

from django.db import IntegrityError
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

from opencourt.models import TeamSeasonStats, Game, GameTeamStats, Ranking
from .fetch import (
    fetch_season_stats_bulk,
    fetch_rankings_bulk,
    fetch_games_bulk,
    fetch_game_team_stats_bulk,
)
from .sync import sync_teams
from .helpers import (
    _build_team_lookup,
    _build_conf_lookup,
    _build_season_stats_defaults,
    _build_game_defaults,
    _build_game_team_stats_defaults,
    _current_season_year,
)

logger = logging.getLogger('opencourt.services')


def update_teams():
    """
    Fetch and upsert all current-season teams.

    This is the same as sync_teams() — the teams endpoint is cheap (one call,
    ~360 rows) so there's no benefit to narrowing the window. Included here
    so update_data can refresh team metadata (venue, colors, etc.) that may
    have changed mid-season.
    """
    sync_teams()


def update_season_stats():
    """
    Fetch and upsert season stats for the current season only.

    Unlike sync_all_season_stats() which loops over ~10 seasons, this makes
    a single API call for just the current year. Takes ~1 second.
    """
    season = _current_season_year()
    team_lookup = _build_team_lookup()

    if not team_lookup:
        logger.warning("update_season_stats: no teams found — run sync_teams first.")
        return

    season_stats = fetch_season_stats_bulk(season)
    if not season_stats:
        logger.warning("update_season_stats: no stats returned for season %s.", season)
        return

    created_count = 0
    updated_count = 0
    skipped_count = 0

    for season_stat in season_stats:
        team_stat_dict = season_stat.to_dict()

        school = (team_stat_dict.get('team') or '').lower()
        team_obj = team_lookup.get(school)
        if team_obj is None:
            continue

        try:
            stat_obj, created = TeamSeasonStats.objects.update_or_create(
                team_id=team_obj.id,
                season=team_stat_dict.get('season'),
                defaults=_build_season_stats_defaults(team_stat_dict)
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        except (IntegrityError, KeyError) as exc:
            skipped_count += 1
            logger.warning("Failed to upsert stats for '%s' season %s: %s", school, season, exc)

    logger.info(
        "update_season_stats complete — %d created, %d updated, %d skipped (season %s).",
        created_count, updated_count, skipped_count, season
    )


def update_games():
    """
    Fetch and upsert games from the last 30 days only.

    Instead of splitting Nov->May into 7 monthly windows like sync_games(),
    this makes a single API call with a 30-day date range. Well under the
    3,000-row cap (~200-400 games in a typical month).
    """
    team_lookup = _build_team_lookup()
    conf_lookup = _build_conf_lookup()

    if not team_lookup:
        logger.warning("update_games: no teams found — run sync_teams first.")
        return

    season = _current_season_year()
    end_dt = datetime(date.today().year, date.today().month, date.today().day)
    start_dt = end_dt - timedelta(days=30)

    games_data = fetch_games_bulk(season, start_date_range=start_dt, end_date_range=end_dt)
    if not games_data:
        logger.warning("update_games: no games returned for last 30 days.")
        return

    created_count = 0
    updated_count = 0
    skipped_count = 0
    ignored_count = 0

    with logging_redirect_tqdm():
        for game in tqdm(games_data, desc='Updating games', unit='game', ncols=80):
            game_dict = game.to_dict()

            home_school = (game_dict.get('homeTeam') or '').lower()
            away_school = (game_dict.get('awayTeam') or '').lower()
            home_team_obj = team_lookup.get(home_school)
            away_team_obj = team_lookup.get(away_school)

            if home_team_obj is None or away_team_obj is None:
                ignored_count += 1
                continue

            home_conf = conf_lookup.get((game_dict.get('homeConference') or '').lower())
            away_conf = conf_lookup.get((game_dict.get('awayConference') or '').lower())

            try:
                game_obj, created = Game.objects.update_or_create(
                    source_id=str(game_dict['id']),
                    defaults=_build_game_defaults(game_dict, home_team_obj, away_team_obj, home_conf, away_conf)
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1

            except (IntegrityError, KeyError) as exc:
                skipped_count += 1
                logger.warning("Failed to upsert game %s: %s", game_dict.get('id'), exc)

    logger.info(
        "update_games complete — %d created, %d updated, %d skipped, %d ignored.",
        created_count, updated_count, skipped_count, ignored_count
    )


def update_game_team_stats():
    """
    Fetch and upsert per-team box scores from the last 30 days only.

    Single API call for a 30-day window, well under the 3,000-row cap.
    """
    team_lookup = _build_team_lookup()

    season = _current_season_year()
    end_dt = datetime(date.today().year, date.today().month, date.today().day)
    start_dt = end_dt - timedelta(days=30)

    # Build game lookup for only recent games to keep memory low
    game_lookup = {
        g.source_id: g
        for g in Game.objects.filter(
            season=season,
            start_date__gte=start_dt,
        )
    }

    if not team_lookup:
        logger.warning("update_game_team_stats: no teams found — run sync_teams first.")
        return
    if not game_lookup:
        logger.warning("update_game_team_stats: no recent games found — run update_games first.")
        return

    stats_data = fetch_game_team_stats_bulk(season, start_date_range=start_dt, end_date_range=end_dt)
    if not stats_data:
        logger.warning("update_game_team_stats: no data returned for last 30 days.")
        return

    created_count = 0
    updated_count = 0
    skipped_count = 0
    ignored_count = 0

    with logging_redirect_tqdm():
        for stat in tqdm(stats_data, desc='Updating game team stats', unit='row', ncols=80):
            stat_dict = stat.to_dict()

            game_id_str = str(stat_dict.get('gameId', ''))
            game_obj = game_lookup.get(game_id_str)
            if game_obj is None:
                ignored_count += 1
                continue

            school = (stat_dict.get('team') or '').lower()
            team_obj = team_lookup.get(school)
            if team_obj is None:
                ignored_count += 1
                continue

            try:
                stat_obj, created = GameTeamStats.objects.update_or_create(
                    game=game_obj,
                    team=team_obj,
                    defaults=_build_game_team_stats_defaults(stat_dict)
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1

            except (IntegrityError, KeyError) as exc:
                skipped_count += 1
                logger.warning(
                    "Failed to upsert game team stats for '%s' game %s: %s",
                    school, game_id_str, exc
                )

    logger.info(
        "update_game_team_stats complete — %d created, %d updated, %d skipped, %d ignored.",
        created_count, updated_count, skipped_count, ignored_count
    )


def update_rankings():
    """
    Fetch and upsert rankings for the current season only.

    Single API call for just this season's polls. Picks up any new weekly
    poll releases since the last sync.
    """
    season = _current_season_year()
    team_lookup = _build_team_lookup()
    conf_lookup = _build_conf_lookup()

    if not team_lookup:
        logger.warning("update_rankings: no teams found — run sync_teams first.")
        return

    rankings = fetch_rankings_bulk(season)
    if not rankings:
        logger.warning("update_rankings: no rankings returned for season %s.", season)
        return

    created_count = 0
    updated_count = 0
    skipped_count = 0

    for ranking in rankings:
        ranking_dict = ranking.to_dict()

        school = (ranking_dict.get('team') or '').lower()
        team_obj = team_lookup.get(school)
        if team_obj is None:
            continue

        conf_obj = conf_lookup.get((ranking_dict.get('conference') or '').lower())

        try:
            ranking_obj, created = Ranking.objects.update_or_create(
                season=ranking_dict.get('season'),
                season_type=ranking_dict.get('seasonType', ''),
                week=ranking_dict.get('week'),
                poll_type=ranking_dict.get('pollType', ''),
                team=team_obj,
                defaults={
                    'poll_date': ranking_dict.get('pollDate'),
                    'conference': conf_obj,
                    'ranking': ranking_dict.get('ranking'),
                    'points': ranking_dict.get('points'),
                    'first_place_votes': ranking_dict.get('firstPlaceVotes'),
                }
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        except (IntegrityError, KeyError) as exc:
            skipped_count += 1
            logger.warning(
                "Failed to upsert ranking for '%s' season %s week %s: %s",
                school, season, ranking_dict.get('week'), exc
            )

    logger.info(
        "update_rankings complete — %d created, %d updated, %d skipped (season %s).",
        created_count, updated_count, skipped_count, season
    )
