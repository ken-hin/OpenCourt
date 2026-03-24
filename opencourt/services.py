# services.py — External API communication and database sync logic.
# -----------------------------------------------------------------------------
# This module is the bridge between the CBBData API and our Django models.
# It handles every outbound HTTP call, response parsing, retry logic, and
# ORM upsert. Views never talk to the API directly — they read from the
# database, which this module keeps in sync.

# =============================================================================
# Architecture:
# -----------------------------------------------------------------------------
#   fetch_*()  functions — pure API calls. Each one hits a single CBBData
#                          endpoint, handles errors, and returns raw data
#                          (or [] on failure). No database writes.
#   sync_*()   functions — orchestration layer. Call the matching fetch_*(),
#                          then loop through results and upsert into Django
#                          models via update_or_create().
#
# Sync order matters — foreign keys create dependencies:
#   1. sync_conferences()       → populates Conference table
#   2. sync_teams()             → populates Team table, links FK to Conference
#   3. sync_all_season_stats()  → populates TeamSeasonStats, links FK to Team
#   4. sync_games()             → populates Game table, links FKs to Team + Conference
#   5. sync_game_team_stats()   → populates GameTeamStats, links FKs to Game + Team
#   6. sync_all_rankings()      → populates Ranking table, links FKs to Team + Conference
#
# These are invoked by management commands in opencourt/management/commands/:
#   python manage.py sync_conferences
#   python manage.py sync_teams
#   python manage.py sync_season_stats
#   python manage.py sync_games          (runs steps 4 + 5 together)
#   python manage.py sync_rankings
#   python manage.py sync_data           (runs all steps in order)

# =============================================================================
# API docs & key:
# -----------------------------------------------------------------------------
#   The CBBData API is hosted at https://api.collegebasketballdata.com.
#   The API key is read from the CBB_API_KEY environment variable (loaded
#   from .env by django-environ). See .env.example for setup instructions.
#   NEVER hardcode the key in this file.

# =============================================================================
# Rate limiting & pagination:
# -----------------------------------------------------------------------------
#   The API enforces rate limits and will return HTTP 429 when exceeded.
#   The CBBData docs recommend "chunky" (bulk) requests over "chatty"
#   (per-entity) ones. We follow this: stats are fetched per-season (~10
#   calls) rather than per-team (~362 calls). Retry with exponential
#   backoff is built into every fetch_*() function.
#
#   The /games and /games/teams endpoints cap responses at 3,000 rows,
#   ordered by start date. A full D1 season has ~5,500 games, and
#   /games/teams returns 2 rows per game (~11,000 total). To get complete
#   data, fetch_games_bulk() and fetch_game_team_stats_bulk() accept
#   start_date_range / end_date_range filters. The sync functions split
#   fetches into monthly windows (Nov → May) so each call stays well
#   under the 3,000-row limit.

import logging
import time
from datetime import date, datetime
import os
import cbbd
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm
from django.db import IntegrityError
from .models import Team, Conference, TeamSeasonStats, Game, GameTeamStats, Ranking

# Module-level logger — tagged as 'opencourt.services' so log messages can
# be filtered independently in Django's LOGGING config. All sync functions
# log at INFO level for summary lines, WARNING for recoverable issues
# (skipped records, rate limits), and ERROR for failures that abort an
# entire fetch.
logger = logging.getLogger(__name__)


# =============================================================================
# API Configuration
# -----------------------------------------------------------------------------
# Shared config object used by every fetch function. The API key is read
# once at module import time from the environment. Both api_key and
# access_token are set because the cbbd client uses different auth headers
# depending on the endpoint.
configuration = cbbd.Configuration(
  host = "https://api.collegebasketballdata.com",
  api_key = os.environ.get('CBB_API_KEY'),
  access_token = os.environ.get('CBB_API_KEY'),
)


# =============================================================================
# Constants
# -----------------------------------------------------------------------------
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
STATS_START_YEAR = CURRENT_YEAR - 9  # the oldest season to sync — controls how many years of history we keep
RANKINGS_START_YEAR = CURRENT_YEAR - 9  # the oldest season to sync rankings for
# --- Rate limiting / retry ---
# These control the backoff behavior when the API returns HTTP 429. Delay doubles each attempt: 5s → 10s → 20s → 40s.
MAX_RETRIES = 4                # max number of retry attempts per API call
RETRY_BASE_DELAY = 5           # seconds — starting delay, doubled each retry
BETWEEN_CALLS_DELAY = 1        # seconds to pause between consecutive season fetches

# =============================================================================
# API Client Factory
# -----------------------------------------------------------------------------

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
# Fetch Functions (API → Python objects)
# -----------------------------------------------------------------------------
# Each fetch function makes a single API call and returns raw data. They
# never touch the database. On any failure they return [] so callers can
# safely iterate without None-checking.
#
# Error handling covers three failure modes consistently:
#   - cbbd.ApiException: API-level HTTP errors (401, 403, 429, 500, etc.)
#   - ConnectionError:   network issues (DNS failure, timeout, refused) or
#                        bad client config
#   - ValueError:        invalid endpoint name passed to init_api_client()

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
    teams = api_instance.get_teams(season = CURRENT_YEAR)
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
  season returns every team's aggregate stats for that year. The caller
  loops over seasons (~20 calls) rather than over teams (~362 calls).

  Includes built-in retry with exponential backoff for HTTP 429 responses.
  The Retry-After header is honored when the API provides it; otherwise
  the delay doubles each attempt (5s → 10s → 20s → 40s).

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
  year across all poll types (AP, Coaches, etc.). The caller loops over
  seasons to build historical data.

  Includes built-in retry with exponential backoff for HTTP 429 responses,
  matching the same pattern as fetch_season_stats_bulk().

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


# =============================================================================
# Sync Functions (API → Database)
# -----------------------------------------------------------------------------
# Each sync function calls its corresponding fetch function, then loops
# through the results and upserts into the database using update_or_create().
#
# Common patterns:
#   - Guard clause: if the fetch returns nothing, log a warning and bail
#     out early — no partial writes.
#   - Per-record try/except: one bad record (missing field, constraint
#     violation) doesn't kill the entire sync.
#   - Summary log: at the end, log created/updated/skipped counts so the
#     management command gives clear terminal output.
#
# All sync functions are idempotent — running them multiple times produces
# the same result. update_or_create() handles this: first run creates rows,
# subsequent runs update them in place.

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
            id = team_dict['id'],
            defaults = {
              'source_id' : team_dict.get('sourceId'),
              'school' : team_dict.get('school', ''),
              'abbrv' : team_dict.get('abbreviation', ''),
              'display_name' : team_dict.get('displayName', ''),
              'short_display_name' : team_dict.get('shortDisplayName', ''),
              'mascot' : team_dict.get('mascot', ''),
              'primary_color' : team_dict.get('primaryColor', ''),
              'secondary_color' : team_dict.get('secondaryColor', ''),
              'current_venue_id' : team_dict.get('currentVenueId'),
              'current_venue_name' : team_dict.get('currentVenue', ''),
              'current_city' : team_dict.get('currentCity', ''),
              'current_state' : team_dict.get('currentState', ''),
              'api_conference_id' : team_dict.get('conferenceId'),
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
  conferences by matching Team.api_conference_id → Conference.id. This
  two-step process exists because sync_teams() may run before conferences
  exist in the DB, so it stores the raw API conference ID and defers the
  FK linkage to here.

  Only teams with a null conference FK and a non-null api_conference_id are
  processed — teams already linked are left alone.

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
  for team in Team.objects.filter(conference__isnull = True, api_conference_id__isnull = False):
    try:
      team.conference = Conference.objects.get(id = team.api_conference_id)
      team.save(update_fields = ['conference'])
    except Conference.DoesNotExist:
      logger.warning("No Conference found for api_conference_id=%s", team.api_conference_id)

  logger.info(
    "sync_conferences complete — %d created, %d updated, %d skipped (of %d total).",
    created_count, updated_count, skipped_count, len(conferences)
  )


def sync_all_season_stats():
  """
  Sync season-level stats for every team across the last ~10 seasons.

  Makes one bulk API call per season (controlled by STATS_START_YEAR →
  CURRENT_YEAR) rather than one per team. Each response contains stats
  for every collegiate basketball program — not just D1 — so we filter
  by matching school names against our Team table.

  Team matching:
    The API's teamId in stat responses doesn't always match the id from
    the teams endpoint (a known quirk of the CBBData API). To avoid FK
    constraint failures, we match on school name instead. A lowercase
    dict lookup (team_lookup) is built once before the loop.

  Called by: python manage.py sync_season_stats (or sync_data)
  Depends on: sync_teams() must have run first to populate the Team table.
  """
  team_lookup = {t.school.lower(): t for t in Team.objects.all()}
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

        try:
          stat_obj, created = TeamSeasonStats.objects.update_or_create(
            team_id = team_obj.id,
            season  = team_stat_dict.get('season'),
            defaults = {
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


def sync_all_rankings():
  """
  Sync poll rankings for every team across all seasons from RANKINGS_START_YEAR
  to CURRENT_YEAR.

  Makes one bulk API call per season. Each response contains every team's
  weekly ranking entries for that year across all poll types (AP, Coaches, etc.).
  Only teams in our Team table are saved — non-D1 programs are silently ignored.

  Team matching:
    Matched by school name (lowercased) against the Team table, same pattern
    as sync_all_season_stats(). Rankings also carry a conference name string
    which is matched against Conference.abbrv for the FK.

  Keyed on (season, season_type, week, poll_type, team) via unique_together
  on the Ranking model, so re-running is safe and idempotent.

  Called by: python manage.py sync_rankings (or sync_data)
  Depends on: sync_teams() and sync_conferences() must have run first.
  """
  team_lookup = {t.school.lower(): t for t in Team.objects.all()}
  conf_lookup = {c.abbrv.lower(): c for c in Conference.objects.all()}

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

        # --- Resolve Team FK ---
        school = (ranking_dict.get('team') or '').lower()
        team_obj = team_lookup.get(school)
        if team_obj is None:
          ignored_count += 1
          logger.debug("Ignoring non-D1 school '%s' in rankings season %s.", school, season)
          continue

        # --- Resolve Conference FK ---
        conf_obj = conf_lookup.get((ranking_dict.get('conference') or '').lower())

        try:
          ranking_obj, created = Ranking.objects.update_or_create(
            # Composite lookup — matches unique_together on the Ranking model
            season      = ranking_dict.get('season'),
            season_type = ranking_dict.get('seasonType', ''),
            week        = ranking_dict.get('week'),
            poll_type   = ranking_dict.get('pollType', ''),
            team        = team_obj,
            defaults = {
              'poll_date'        : ranking_dict.get('pollDate'),
              'conference'       : conf_obj,
              'ranking'          : ranking_dict.get('ranking'),
              'points'           : ranking_dict.get('points'),
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


# =============================================================================
# Game Fetch Functions
# -----------------------------------------------------------------------------

def fetch_games_bulk(season, start_date_range=None, end_date_range=None):
  """
  Fetch games for a single season from the CBBData /games endpoint.

  The API caps responses at 3,000 games per call. A full D1 season has
  ~5,500 games, so callers should split by date range to get complete data
  (see sync_games() for example).

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


# =============================================================================
# Game Sync Functions
# -----------------------------------------------------------------------------

def sync_games():
  """
  Fetch game results from the /games endpoint and upsert into the Game model.

  Syncs the current season only (not historical). Splits the fetch at
  January 1st to stay under the 3,000-row API cap per call.

  Called by: python manage.py sync_games (or sync_data)
  Depends on: sync_teams() and sync_conferences() must have run first.
  """
  team_lookup = {t.school.lower(): t for t in Team.objects.all()}
  conf_lookup = {c.abbrv.lower(): c for c in Conference.objects.all()}

  if not team_lookup:
    logger.warning("sync_games: no teams found — run sync_teams first.")
    return

  season = CURRENT_YEAR

  date_ranges = []
  for month in range(11, 13):
    start = datetime(season - 1, month, 1)
    end = datetime(season - 1, month + 1, 1) if month < 12 else datetime(season, 1, 1)
    date_ranges.append({'start_date_range': start, 'end_date_range': end})
  for month in range(1, 6):
    start = datetime(season, month, 1)
    end = datetime(season, month + 1, 1)
    date_ranges.append({'start_date_range': start, 'end_date_range': end})

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
          defaults={
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

  Syncs the current season only. Each API row contains one team's stats
  for one game. We create two GameTeamStats rows per game — one for each team.

  Called by: python manage.py sync_games (or sync_data)
  Depends on: sync_games() must have run first to populate Game rows.
  """
  team_lookup = {t.school.lower(): t for t in Team.objects.all()}
  game_lookup = {g.source_id: g for g in Game.objects.filter(season=CURRENT_YEAR)}

  if not team_lookup:
    logger.warning("sync_game_team_stats: no teams found — run sync_teams first.")
    return
  if not game_lookup:
    logger.warning("sync_game_team_stats: no games found — run sync_games first.")
    return

  season = CURRENT_YEAR

  date_ranges = []
  for month in range(11, 13):
    start = datetime(season - 1, month, 1)
    end = datetime(season - 1, month + 1, 1) if month < 12 else datetime(season, 1, 1)
    date_ranges.append({'start_date_range': start, 'end_date_range': end})
  for month in range(1, 6):
    start = datetime(season, month, 1)
    end = datetime(season, month + 1, 1)
    date_ranges.append({'start_date_range': start, 'end_date_range': end})

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

      try:
        stat_obj, created = GameTeamStats.objects.update_or_create(
          game=game_obj,
          team=team_obj,
          defaults={
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