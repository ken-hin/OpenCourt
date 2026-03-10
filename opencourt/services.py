# services.py — External API and data-fetching logic for the opencourt app.
#
# This file is the single place for all CBB data API calls and any web scraping.
# Keeping this separate from views.py means views stay clean and focused on
# HTTP logic, while all the data-fetching details live here.
#
# The `requests` library is already listed in pyproject.toml and installed by `uv sync`.
# No additional installation step is needed.
#
# The CBB_API_KEY is read from the .env file (never hardcode it here).
# See .env.example for setup instructions.
#
#   - fetch_teams()       : pull all teams from the CBB API
#   - fetch_conferences() : pull all conferences
#   - sync_teams()        : fetch from API and save to the database
#   - sync_conferences()  : fetch from API and save to the database
import logging
import time
from datetime import date
import os
import cbbd
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm
from django.db import IntegrityError
from .models import Team, Conference, TeamSeasonStats

# Module-level logger — use `logging.getLogger(__name__)` so log messages
# are tagged with 'opencourt.services', making them easy to filter in
# Django's LOGGING config or in the terminal.
logger = logging.getLogger(__name__)

# --- API Config ---
configuration = cbbd.Configuration(
  host = "https://api.collegebasketballdata.com",
  api_key = os.environ.get('CBB_API_KEY'),
  access_token = os.environ.get('CBB_API_KEY'),
)
# --- Constants ---
# API endpoints
TEAMS_ENDPOINT = 'TeamsApi'
CONFERENCES_ENDPOINT = 'ConferencesApi'
STATS_ENDPOINT = 'StatsApi'
RANKINGS_ENDPOINT = 'RankingsApi'
RATINGS_ENDPOINT = 'RatingsApi'
# Year constants
CURRENT_YEAR = date.today().year
LAST_YEAR = CURRENT_YEAR - 1
STATS_START_YEAR = CURRENT_YEAR - 25  # oldest season to sync (last 26 years inclusive)

def init_api_client(config, endpoint):
  """
  Create and return a typed CBBData API client for the given endpoint.
  Wraps the shared configuration in an ApiClient, then returns the
  correct endpoint-specific instance (TeamsApi, ConferencesApi, etc.).
  This keeps the API client setup in one place so fetch functions stay short.

  Args:
      config: cbbd.Configuration — pre-configured with host + API key.
      endpoint: str — one of 'TeamsApi', 'ConferencesApi', 'StatsApi',
                'RankingsApi', or 'RatingsApi'.
  Returns:
      The matching cbbd.*Api instance, ready to call .get_*() methods on.
  Raises:
      ValueError: If the endpoint doesn't match any known API class.
      ConnectionError: If the API client can't be created (bad key, bad host).
  """
  # Catch config-level errors (missing key, bad host) early so they don't surface as cryptic errors inside a fetch function.
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
    case 'RankingsApi':
      api_instance = cbbd.RankingsApi(api_client)
    case 'RatingsApi':
      api_instance = cbbd.RatingsApi(api_client)
    case _:
      raise ValueError(f"Invalid endpoint: {endpoint}")

  return api_instance

# --- Team Data ---
def fetch_teams():
  """
  Fetch all Division I teams for the current season from the CBBData API.

  Uses the TeamsApi endpoint with the current calendar year as the season
  parameter. Returns the raw API response (a list of cbbd team objects).
  Returns an empty list if the API call fails, so callers can safely
  iterate without checking for None.

  Error handling covers three failure modes:
    - ValueError: bad endpoint name passed to init_api_client
    - cbbd.ApiException: API-level errors (401 unauthorized, 403 forbidden, 429 rate limit, 500 server error)
    - ConnectionError: network issues (DNS failure, timeout, refused)

  Returns:
      list — cbbd team objects from the API, or [] on any error.
  """
  try:
    api_instance = init_api_client(configuration, TEAMS_ENDPOINT)
    teams = api_instance.get_teams(season = CURRENT_YEAR)
    return teams
  except cbbd.ApiException as exc:
    # API returned an error status code (401, 403, 429, 500, etc.)
    logger.error("CBBData API error fetching teams (HTTP %s): %s", exc.status, exc.reason)
    return []
  except ConnectionError as exc:
    # Client couldn't be created or the network is unreachable
    logger.error("Connection error fetching teams: %s", exc)
    return []
  except ValueError as exc:
    # Bad endpoint name — should never happen unless someone edits the call above
    logger.error("Configuration error in fetch_teams: %s", exc)
    return []

# --- Season Stats Data---
# Retry / backoff settings for rate-limited API calls.
MAX_RETRIES     = 4
RETRY_BASE_DELAY = 5   # seconds — doubles each attempt: 5, 10, 20, 40
BETWEEN_CALLS_DELAY = 1  # seconds to sleep between successful season fetches

def fetch_season_stats_bulk(season):
  """
  Fetch season stats for ALL teams in a single season from the CBBData API.

  One call returns every team's stats for that year — far more efficient
  than calling the API once per team (~362 calls). The caller loops over
  seasons (26 calls total) rather than over teams.

  Retries up to MAX_RETRIES times on HTTP 429, using exponential backoff.
  Respects the Retry-After response header when the API provides it.

  Returns a list of stat objects, or [] if all retries are exhausted.
  """

  for attempt in range(MAX_RETRIES + 1):

    try:
      api_instance = init_api_client(configuration, STATS_ENDPOINT)
      season_stats = api_instance.get_team_season_stats(season=season)
      return season_stats

    except cbbd.ApiException as exc:
      if exc.status == 429:
        if attempt < MAX_RETRIES:
          # Honor the Retry-After header if present, else use exponential backoff
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
          continue  # retry the loop
        else:
          logger.error("Rate limited on season %s — max retries exceeded.", season)
          return []
      # Non-429 API error — no point retrying
      logger.error("CBBData API error fetching bulk stats for season %s (HTTP %s): %s", season, exc.status, exc.reason)
      return []

    except ConnectionError as exc:
      logger.error("Connection error fetching bulk stats for season %s: %s", season, exc)
      return []

    except ValueError as exc:
      logger.error("Configuration error in fetch_season_stats_bulk: %s", exc)
      return []

# --- Conference Data ---
def fetch_conferences():
  """
  Fetch all conferences from the CBBData API.
  Returns the raw API response (a list of cbbd conference objects).
  Returns an empty list if the API call fails.
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

# --- Sync Functions ---
def sync_teams():
    """
    Fetch all teams from the CBBData API and upsert them into the Team model.

    Calls fetch_teams() then loops through the results, using Django's
    update_or_create() to insert new rows or update existing ones. The API's
    `id` field is used as the lookup key so records stay stable across syncs.

    Error handling:
      - If fetch_teams() returns [] (API down or error), logs a warning,
        and exits early — no database changes are made.
      - Each team is wrapped in its own try/except so a single bad record
        (missing required field, slug collision, etc.) is skipped without
        killing the entire sync.
      - Logs a summary at the end: created, updated, and skipped counts.

    Called by the sync_data management command: python manage.py sync_data
    """
    teams = fetch_teams()
    # Guard clause — if the API returned nothing, don't silently continue.
    if not teams:
      logger.warning("sync_teams: fetch_teams() returned no data — skipping sync.")
      return

    # Counters for the summary log at the end of the sync
    created_count = 0
    updated_count = 0
    skipped_count = 0

    with logging_redirect_tqdm():
      for team in tqdm(teams, desc='Syncing teams', unit='team', ncols=80):
        try:
          # Convert API object to dictionary
          team_dict = team.to_dict()
          # Then create/update the team
          team_obj, created = Team.objects.update_or_create(
            id = team_dict['id'],  # lookup — how Django finds the existing record
            defaults = {  # everything to set/update on that record
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
              # Raw API integer ID — kept for reference. The ForeignKey (conference)
              # is linked separately once sync_conferences() has run.
              'api_conference_id' : team_dict.get('conferenceId'),
            }
          )
          if created:
            created_count += 1
          else:
            updated_count += 1

        except (IntegrityError, KeyError) as exc:
          # IntegrityError — slug collision or NOT NULL violation on a required field
          # KeyError — API response missing the 'id' key entirely
          skipped_count += 1
          logger.warning("Skipped team (id=%s): %s", team_dict.get('id', '?'), exc)
          continue

    # Summary line so the management command gives clear feedback
    logger.info(
      "sync_teams complete — %d created, %d updated, %d skipped (of %d total).",
      created_count, updated_count, skipped_count, len(teams)
    )

def sync_conferences():
  """
  Fetch all conferences from the CBBData API and upsert them into the Conference model.
  Called by the sync_data management command: python manage.py sync_data
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

  # Link each team's conference FK using the raw api_conference_id
  for team in Team.objects.filter(conference__isnull = True, api_conference_id__isnull = False) :
    try :
      team.conference = Conference.objects.get(id = team.api_conference_id)
      team.save(update_fields = ['conference'])
    except Conference.DoesNotExist :
      logger.warning("No Conference found for api_conference_id=%s", team.api_conference_id)

  logger.info(
    "sync_conferences complete — %d created, %d updated, %d skipped (of %d total).",
    created_count, updated_count, skipped_count, len(conferences)
  )

def sync_all_season_stats():
  """
  Sync stats for every team across the last 26 seasons.

  Makes one API call per season (26 total) instead of one per team (~362).
  Each season response contains all teams — rows are matched to Team objects
  via school name rather than the stats API's teamId, which can differ from
  the teams API's id and cause FK constraint failures.

  Called as a separate step in the sync_data management command, after
  sync_teams() has already populated the teams table.
  """
  # Build a school-name -> Team lookup once before the outer loop.
  # Lower-cased for case-insensitive matching against API response values.
  team_lookup = {t.school.lower(): t for t in Team.objects.all()}
  if not team_lookup:
    logger.warning("sync_all_season_stats: no teams found — run sync_teams first.")
    return

  seasons = range(STATS_START_YEAR, CURRENT_YEAR + 1)
  created_count = 0
  updated_count = 0
  skipped_count = 0   # DB errors only
  ignored_count = 0   # non-D1 programs not in our team table

  with logging_redirect_tqdm():
    for season in tqdm(seasons, desc='Syncing season stats', unit='season', ncols=80):
      season_stats = fetch_season_stats_bulk(season)
      # Polite pause before the next API call, guards against hitting the API rate limit.
      time.sleep(BETWEEN_CALLS_DELAY)
      if not season_stats:
        logger.warning("No stats returned for season %s — skipping.", season)
        continue

      for season_stat in season_stats:
        # Keys use camelCase aliases (e.g. 'teamStats', 'fieldGoals', 'teamId')
        team_stat_dict = season_stat.to_dict()
        # Resolve FK via school name — more reliable than the API's teamId.
        school = (team_stat_dict.get('team') or '').lower()
        team_obj = team_lookup.get(school)
        if team_obj is None:
          ignored_count += 1
          # Non-D1 programs appear in bulk responses but aren't in our team table — expected, not an error.
          logger.debug("Ignoring non-D1 school '%s' in season %s.", school, season)
          continue

        # Offensive and opponent stat blocks (already plain dicts)
        stat_dict     = team_stat_dict.get('teamStats', {})
        opp_stat_dict = team_stat_dict.get('opponentStats', {})
        # Offensive sub-dicts
        fg_dict           = stat_dict.get('fieldGoals', {})
        fg_2pt_dict       = stat_dict.get('twoPointFieldGoals', {})
        fg_3pt_dict       = stat_dict.get('threePointFieldGoals', {})
        ft_dict           = stat_dict.get('freeThrows', {})
        points_dict       = stat_dict.get('points', {})
        rebounds_dict     = stat_dict.get('rebounds', {})
        turnovers_dict    = stat_dict.get('turnovers', {})
        four_factors_dict = stat_dict.get('fourFactors', {})
        # Opponent sub-dicts
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
            # Lookup — must match unique_together = ('team', 'season').
            team_id = team_obj.id,
            season  = team_stat_dict.get('season'),
            defaults = {
              'season_label' : team_stat_dict.get('seasonLabel'),
              'games'        : team_stat_dict.get('games'),
              'wins'         : team_stat_dict.get('wins'),
              'losses'       : team_stat_dict.get('losses'),
              'total_minutes': team_stat_dict.get('totalMinutes'),
              'pace'         : team_stat_dict.get('pace'),
              # --- Offensive shooting ---
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
              # --- Offensive counting stats ---
              'off_points'   : points_dict.get('total'),
              'off_assists'  : stat_dict.get('assists'),
              'off_steals'   : stat_dict.get('steals'),
              'off_blocks'   : stat_dict.get('blocks'),
              'off_turnovers': turnovers_dict.get('total'),
              # --- Offensive rebounds ---
              'off_reb_total'    : rebounds_dict.get('total'),
              'off_reb_offensive': rebounds_dict.get('offensive'),
              'off_reb_defensive': rebounds_dict.get('defensive'),
              # --- Offensive four factors (advanced) ---
              'off_eff_fg_pct'    : four_factors_dict.get('effectiveFieldGoalPct'),
              'off_ft_rate'       : four_factors_dict.get('freeThrowRate'),
              'off_oreb_pct'      : four_factors_dict.get('offensiveReboundPct'),
              'off_turnover_ratio': four_factors_dict.get('turnoverRatio'),
              'off_true_shooting' : stat_dict.get('trueShooting'),
              'off_rating'        : stat_dict.get('rating'),
              'off_possessions'   : stat_dict.get('possessions'),
              # --- Opponent / defensive stats ---
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
