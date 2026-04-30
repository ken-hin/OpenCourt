# sync.py — Full database sync functions (API -> Database).
#
# Each sync function calls its corresponding fetch function, then loops
# through the results and upserts into the database using update_or_create().
#
# These are designed for initial DB setup or full backfills. For incremental
# daily updates, use the update_* functions in update.py instead.
#
# Sync order matters — foreign keys create dependencies:
#   1. sync_conferences()       -> populates Conference table
#   2. sync_teams()             -> populates Team table, links FK to Conference
#   3. sync_all_season_stats()  -> populates TeamSeasonStats, links FK to Team
#   4. sync_games()             -> populates Game table, links FKs to Team + Conference
#   5. sync_game_team_stats()   -> populates GameTeamStats, links FKs to Game + Team
#   6. sync_all_rankings()      -> populates Ranking table, links FKs to Team + Conference
#
# All sync functions are idempotent — running them multiple times produces
# the same result. update_or_create() handles this: first run creates rows,
# subsequent runs update them in place.

import logging
import time

from django.db import IntegrityError
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

from opencourt.models import (
    Team, Conference, TeamSeasonStats, Game, GameTeamStats, Ranking,
)
from .fetch import (
    fetch_teams,
    fetch_conferences,
    fetch_season_stats_bulk,
    fetch_rankings_bulk,
    fetch_games_bulk,
    fetch_game_team_stats_bulk,
)
from .helpers import (
    CURRENT_YEAR,
    STATS_START_YEAR,
    RANKINGS_START_YEAR,
    GAMES_HISTORY_START_YEAR,
    BETWEEN_CALLS_DELAY,
    _build_team_lookup,
    _build_conf_lookup,
    _build_season_stats_defaults,
    _build_game_defaults,
    _build_game_team_stats_defaults,
    _build_game_date_ranges,
)

logger = logging.getLogger('opencourt.services')


def sync_teams():
    """
    Fetch all teams from the CBBData API and upsert them into the Team model.

    Uses the API's `id` field as the lookup key so records stay stable
    across syncs. The conference ForeignKey is NOT set here — that happens
    in sync_conferences() after the Conference table is populated.

    Progress is displayed with a tqdm bar in the terminal. The
    logging_redirect_tqdm context manager ensures logger.warning() calls
    print cleanly above the progress bar without visual corruption.

    Called by: python manage.py sync_teams (or sync_data)
    """
    teams = fetch_teams()

    if not teams:
        logger.warning("sync_teams: fetch_teams() returned no data — skipping sync.")
        return

    created_count = 0
    updated_count = 0
    skipped_count = 0

    with logging_redirect_tqdm():
        for team in tqdm(teams, desc='Syncing teams', unit='team', ncols=80):
            try:
                team_dict = team.to_dict()

                team_obj, created = Team.objects.update_or_create(
                    id=team_dict['id'],
                    defaults={
                        'source_id': team_dict.get('sourceId'),
                        'school': team_dict.get('school', ''),
                        'abbrv': team_dict.get('abbreviation', ''),
                        'display_name': team_dict.get('displayName', ''),
                        'short_display_name': team_dict.get('shortDisplayName', ''),
                        'mascot': team_dict.get('mascot', ''),
                        'primary_color': team_dict.get('primaryColor', ''),
                        'secondary_color': team_dict.get('secondaryColor', ''),
                        'current_venue_id': team_dict.get('currentVenueId'),
                        'current_venue_name': team_dict.get('currentVenue', ''),
                        'current_city': team_dict.get('currentCity', ''),
                        'current_state': team_dict.get('currentState', ''),
                        'api_conference_id': team_dict.get('conferenceId'),
                    }
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1

            except (IntegrityError, KeyError) as exc:
                skipped_count += 1
                logger.warning("Skipped team (id=%s): %s", team_dict.get('id', '?'), exc)
                continue

    logger.info(
        "sync_teams complete — %d created, %d updated, %d skipped (of %d total).",
        created_count, updated_count, skipped_count, len(teams)
    )


def sync_conferences():
    """
    Fetch all conferences from the CBBData API and upsert into the Conference model.

    After upserting conferences, this function also links teams to their
    conferences by matching Team.api_conference_id -> Conference.id.

    Called by: python manage.py sync_conferences (or sync_data)
    """
    conferences = fetch_conferences()

    if not conferences:
        logger.warning("sync_conferences: fetch_conferences() returned no data — skipping sync.")
        return

    created_count = 0
    updated_count = 0
    skipped_count = 0

    for conference in conferences:
        try:
            conf_dict = conference.to_dict()
            conf_obj, created = Conference.objects.update_or_create(
                id=conf_dict['id'],
                defaults={
                    'source_id': conf_dict.get('sourceId'),
                    'name': conf_dict.get('name', ''),
                    'abbrv': conf_dict.get('abbreviation', ''),
                    'short_name': conf_dict.get('shortName', ''),
                }
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        except (IntegrityError, KeyError) as exc:
            skipped_count += 1
            logger.warning("Skipped conference (id=%s): %s", conf_dict.get('id', '?'), exc)

    # --- Link teams to conferences ---
    for team in Team.objects.filter(conference__isnull=True, api_conference_id__isnull=False):
        try:
            team.conference = Conference.objects.get(id=team.api_conference_id)
            team.save(update_fields=['conference'])
        except Conference.DoesNotExist:
            logger.warning("No Conference found for api_conference_id=%s", team.api_conference_id)

    logger.info(
        "sync_conferences complete — %d created, %d updated, %d skipped (of %d total).",
        created_count, updated_count, skipped_count, len(conferences)
    )


def sync_all_season_stats():
    """
    Sync season-level stats for every team across the last ~10 seasons.

    Makes one bulk API call per season (controlled by STATS_START_YEAR ->
    CURRENT_YEAR) rather than one per team.

    Called by: python manage.py sync_season_stats (or sync_data)
    Depends on: sync_teams() must have run first to populate the Team table.
    """
    team_lookup = _build_team_lookup()
    if not team_lookup:
        logger.warning("sync_all_season_stats: no teams found — run sync_teams first.")
        return

    seasons = range(STATS_START_YEAR, CURRENT_YEAR + 1)
    created_count = 0
    updated_count = 0
    skipped_count = 0
    ignored_count = 0

    with logging_redirect_tqdm():
        for season in tqdm(seasons, desc='Syncing season stats', unit='season', ncols=80):
            season_stats = fetch_season_stats_bulk(season)
            time.sleep(BETWEEN_CALLS_DELAY)

            if not season_stats:
                logger.warning("No stats returned for season %s — skipping.", season)
                continue

            for season_stat in season_stats:
                team_stat_dict = season_stat.to_dict()

                school = (team_stat_dict.get('team') or '').lower()
                team_obj = team_lookup.get(school)
                if team_obj is None:
                    ignored_count += 1
                    logger.debug("Ignoring non-D1 school '%s' in season %s.", school, season)
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
        "sync_all_season_stats complete — %d created, %d updated, %d skipped, %d non-D1 ignored (across %d seasons).",
        created_count, updated_count, skipped_count, ignored_count, len(seasons)
    )

    if ignored_count > 100:
        logger.warning(
            "High ignored count (%d) detected — check for school name mismatches between teams and stats APIs.",
            ignored_count
        )


def sync_all_rankings():
    """
    Sync poll rankings for every team across all seasons from RANKINGS_START_YEAR
    to CURRENT_YEAR.

    Called by: python manage.py sync_rankings (or sync_data)
    Depends on: sync_teams() and sync_conferences() must have run first.
    """
    team_lookup = _build_team_lookup()
    conf_lookup = _build_conf_lookup()

    if not team_lookup:
        logger.warning("sync_all_rankings: no teams found — run sync_teams first.")
        return

    seasons = range(RANKINGS_START_YEAR, CURRENT_YEAR + 1)
    created_count = 0
    updated_count = 0
    skipped_count = 0
    ignored_count = 0

    with logging_redirect_tqdm():
        for season in tqdm(seasons, desc='Syncing rankings', unit='season', ncols=80):
            rankings = fetch_rankings_bulk(season)
            time.sleep(BETWEEN_CALLS_DELAY)

            if not rankings:
                logger.warning("No rankings returned for season %s — skipping.", season)
                continue

            for ranking in rankings:
                ranking_dict = ranking.to_dict()

                school = (ranking_dict.get('team') or '').lower()
                team_obj = team_lookup.get(school)
                if team_obj is None:
                    ignored_count += 1
                    logger.debug("Ignoring non-D1 school '%s' in rankings season %s.", school, season)
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
        "sync_all_rankings complete — %d created, %d updated, %d skipped, %d non-D1 ignored (across %d seasons).",
        created_count, updated_count, skipped_count, ignored_count, len(seasons)
    )


def sync_games():
    """
    Fetch game results from the /games endpoint and upsert into the Game model.

    Syncs the current season only (not historical). Splits the fetch into
    monthly windows (Nov->May) to stay under the 3,000-row API cap per call.

    Called by: python manage.py sync_games (or sync_data)
    Depends on: sync_teams() and sync_conferences() must have run first.
    """
    team_lookup = _build_team_lookup()
    conf_lookup = _build_conf_lookup()

    if not team_lookup:
        logger.warning("sync_games: no teams found — run sync_teams first.")
        return

    season = CURRENT_YEAR
    date_ranges = _build_game_date_ranges(season)

    games_data = []
    for dr in date_ranges:
        batch = fetch_games_bulk(season, **dr)
        if batch:
            logger.info("Fetched %d games for date range %s.", len(batch), dr)
            games_data.extend(batch)
        time.sleep(BETWEEN_CALLS_DELAY)

    if not games_data:
        logger.warning("sync_games: no games returned for season %s.", season)
        return

    created_count = 0
    updated_count = 0
    skipped_count = 0
    ignored_count = 0

    with logging_redirect_tqdm():
        for game in tqdm(games_data, desc='Syncing games', unit='game', ncols=80):
            game_dict = game.to_dict()

            home_school = (game_dict.get('homeTeam') or '').lower()
            away_school = (game_dict.get('awayTeam') or '').lower()
            home_team_obj = team_lookup.get(home_school)
            away_team_obj = team_lookup.get(away_school)

            if home_team_obj is None or away_team_obj is None:
                ignored_count += 1
                logger.debug(
                    "Ignoring game %s: home='%s' away='%s' — one or both not in team table.",
                    game_dict.get('id'), home_school, away_school
                )
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
        "sync_games complete — %d created, %d updated, %d skipped, %d ignored (non-D1).",
        created_count, updated_count, skipped_count, ignored_count
    )


def sync_game_team_stats():
    """
    Fetch per-team box score stats from /games/teams and upsert into GameTeamStats.

    Syncs the current season only.

    Called by: python manage.py sync_games (or sync_data)
    Depends on: sync_games() must have run first to populate Game rows.
    """
    team_lookup = _build_team_lookup()
    game_lookup = {g.source_id: g for g in Game.objects.filter(season=CURRENT_YEAR)}

    if not team_lookup:
        logger.warning("sync_game_team_stats: no teams found — run sync_teams first.")
        return
    if not game_lookup:
        logger.warning("sync_game_team_stats: no games found — run sync_games first.")
        return

    season = CURRENT_YEAR
    date_ranges = _build_game_date_ranges(season)

    stats_data = []
    for dr in date_ranges:
        batch = fetch_game_team_stats_bulk(season, **dr)
        if batch:
            logger.info("Fetched %d game team stat rows for date range %s.", len(batch), dr)
            stats_data.extend(batch)
        time.sleep(BETWEEN_CALLS_DELAY)

    if not stats_data:
        logger.warning("sync_game_team_stats: no data returned for season %s.", season)
        return

    created_count = 0
    updated_count = 0
    skipped_count = 0
    ignored_count = 0

    with logging_redirect_tqdm():
        for stat in tqdm(stats_data, desc='Syncing game team stats', unit='row', ncols=80):
            stat_dict = stat.to_dict()

            game_id_str = str(stat_dict.get('gameId', ''))
            game_obj = game_lookup.get(game_id_str)
            if game_obj is None:
                ignored_count += 1
                logger.debug("Ignoring game team stats for unknown game ID %s.", game_id_str)
                continue

            school = (stat_dict.get('team') or '').lower()
            team_obj = team_lookup.get(school)
            if team_obj is None:
                ignored_count += 1
                logger.debug("Ignoring game team stats for non-D1 school '%s'.", school)
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
        "sync_game_team_stats complete — %d created, %d updated, %d skipped, %d ignored.",
        created_count, updated_count, skipped_count, ignored_count
    )


def sync_games_historical():
    """
    Fetch game results for every season from GAMES_HISTORY_START_YEAR through
    CURRENT_YEAR and upsert into the Game model.

    Mirrors sync_games() but loops across the last 3 seasons. Each season is
    still split into monthly windows (Nov->May) via _build_game_date_ranges()
    to stay under the API's 3,000-row cap per call.

    This is intended for one-time historical backfills. For incremental updates
    to the current season, use sync_games() or update_games().

    Called by: python manage.py sync_games_historical (or sync_data --historical)
    Depends on: sync_teams() and sync_conferences() must have run first.
    """
    team_lookup = _build_team_lookup()
    conf_lookup = _build_conf_lookup()

    if not team_lookup:
        logger.warning("sync_games_historical: no teams found — run sync_teams first.")
        return

    seasons = range(GAMES_HISTORY_START_YEAR, CURRENT_YEAR + 1)
    created_count = 0
    updated_count = 0
    skipped_count = 0
    ignored_count = 0

    with logging_redirect_tqdm():
        for season in tqdm(seasons, desc='Syncing historical games', unit='season', ncols=80):
            date_ranges = _build_game_date_ranges(season)

            games_data = []
            for dr in date_ranges:
                batch = fetch_games_bulk(season, **dr)
                if batch:
                    logger.info("Fetched %d games for season %s range %s.", len(batch), season, dr)
                    games_data.extend(batch)
                time.sleep(BETWEEN_CALLS_DELAY)

            if not games_data:
                logger.warning("sync_games_historical: no games returned for season %s — skipping.", season)
                continue

            for game in games_data:
                game_dict = game.to_dict()

                home_school = (game_dict.get('homeTeam') or '').lower()
                away_school = (game_dict.get('awayTeam') or '').lower()
                home_team_obj = team_lookup.get(home_school)
                away_team_obj = team_lookup.get(away_school)

                if home_team_obj is None or away_team_obj is None:
                    ignored_count += 1
                    logger.debug(
                        "Ignoring game %s (season %s): home='%s' away='%s' — one or both not in team table.",
                        game_dict.get('id'), season, home_school, away_school
                    )
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
                    logger.warning("Failed to upsert game %s (season %s): %s", game_dict.get('id'), season, exc)

    logger.info(
        "sync_games_historical complete — %d created, %d updated, %d skipped, %d ignored (across %d seasons).",
        created_count, updated_count, skipped_count, ignored_count, len(seasons)
    )


def sync_game_team_stats_historical():
    """
    Fetch per-team box score stats for every season from GAMES_HISTORY_START_YEAR
    through CURRENT_YEAR and upsert into the GameTeamStats model.

    Mirrors sync_game_team_stats() but loops across the last 3 seasons. Each
    season is split into monthly windows (Nov->May) via _build_game_date_ranges()
    to stay under the API's 3,000-row cap per call (each game produces two rows,
    one per team, so the effective cap is ~1,500 games/call).

    This is intended for one-time historical backfills. For incremental updates
    to the current season, use sync_game_team_stats() or update_game_team_stats().

    Called by: python manage.py sync_games_historical (or sync_data --historical)
    Depends on: sync_games_historical() must have run first to populate Game rows
                across the historical range.
    """
    team_lookup = _build_team_lookup()
    # Build a lookup of every Game row in the historical range so we can FK-resolve
    # stats rows to Games regardless of which season they came from.
    game_lookup = {
        g.source_id: g
        for g in Game.objects.filter(
            season__gte=GAMES_HISTORY_START_YEAR,
            season__lte=CURRENT_YEAR,
        )
    }

    if not team_lookup:
        logger.warning("sync_game_team_stats_historical: no teams found — run sync_teams first.")
        return
    if not game_lookup:
        logger.warning(
            "sync_game_team_stats_historical: no historical games found — run sync_games_historical first."
        )
        return

    seasons = range(GAMES_HISTORY_START_YEAR, CURRENT_YEAR + 1)
    created_count = 0
    updated_count = 0
    skipped_count = 0
    ignored_count = 0

    with logging_redirect_tqdm():
        for season in tqdm(seasons, desc='Syncing historical game team stats', unit='season', ncols=80):
            date_ranges = _build_game_date_ranges(season)

            stats_data = []
            for dr in date_ranges:
                batch = fetch_game_team_stats_bulk(season, **dr)
                if batch:
                    logger.info(
                        "Fetched %d game team stat rows for season %s range %s.",
                        len(batch), season, dr
                    )
                    stats_data.extend(batch)
                time.sleep(BETWEEN_CALLS_DELAY)

            if not stats_data:
                logger.warning(
                    "sync_game_team_stats_historical: no data returned for season %s — skipping.",
                    season
                )
                continue

            for stat in stats_data:
                stat_dict = stat.to_dict()

                game_id_str = str(stat_dict.get('gameId', ''))
                game_obj = game_lookup.get(game_id_str)
                if game_obj is None:
                    ignored_count += 1
                    logger.debug(
                        "Ignoring game team stats for unknown game ID %s (season %s).",
                        game_id_str, season
                    )
                    continue

                school = (stat_dict.get('team') or '').lower()
                team_obj = team_lookup.get(school)
                if team_obj is None:
                    ignored_count += 1
                    logger.debug(
                        "Ignoring game team stats for non-D1 school '%s' (season %s).",
                        school, season
                    )
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
                        "Failed to upsert game team stats for '%s' game %s (season %s): %s",
                        school, game_id_str, season, exc
                    )

    logger.info(
        "sync_game_team_stats_historical complete — %d created, %d updated, %d skipped, %d ignored (across %d seasons).",
        created_count, updated_count, skipped_count, ignored_count, len(seasons)
    )
