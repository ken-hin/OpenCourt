# services.py — External API and data-fetching logic for the opencourt app.
#
# This file is the single place for all CBB data API calls and any web scraping.
# Keeping this separate from views.py means views stay clean and focused on
# HTTP logic, while all the data-fetching details live here.
#
# Usage pattern — call these functions from views.py:
#   from opencourt.services import fetch_teams
#   teams = fetch_teams()
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
from datetime import date
import os
import cbbd
from django.db import IntegrityError
from .models import Team, Conference

# Module-level logger — use `logging.getLogger(__name__)` so log messages
# are tagged with 'opencourt.services', making them easy to filter in
# Django's LOGGING config or in the terminal.
logger = logging.getLogger(__name__)

# --- API Config ---
# Configure and create the client for calling CFBD API
configuration = cbbd.Configuration(
  host = "https://api.collegebasketballdata.com",
  api_key = os.environ.get('CBB_API_KEY'),
  access_token = os.environ.get('CBB_API_KEY'),
)

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
    api_instance = init_api_client(configuration, 'TeamsApi')
    current_year = date.today().year
    teams = api_instance.get_teams(season = current_year)
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

# --- Conference Data ---
def fetch_conferences():
  """
  Fetch all conferences from the CBBData API.
  Returns the raw API response (a list of cbbd conference objects).
  Returns an empty list if the API call fails.
  """
  try:
    api_instance = init_api_client(configuration, 'ConferencesApi')
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

    for team in teams:
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
