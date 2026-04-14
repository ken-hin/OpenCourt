# test_services.py — Unit tests for the opencourt/services/ package.
#
# Tests the data pipeline layer that sits between the CBBData API and our
# database: helper utilities, API response → ORM field mappers, the API
# client factory, and the fetch functions (with mocked network calls).
#
# IMPORTANT: No test in this file makes a real HTTP request. All CBBData
# API calls are mocked with unittest.mock so the test suite stays fast
# and runs offline. Each test targets a specific function and verifies
# one behavior at a time.
#
# Organized into four sections:
#   1. Lookup Builders  — _build_team_lookup(), _build_conf_lookup()
#   2. Defaults Builders — _build_season_stats_defaults(), _build_game_defaults(), etc.
#   3. Date/Season Helpers — _build_game_date_ranges(), _current_season_year()
#   4. API Client Factory — init_api_client()
#   5. Fetch Functions   — fetch_teams(), fetch_conferences(), retry logic, etc.
#
# Run just these tests:
#   uv run python manage.py test opencourt.tests.test_services

from datetime import date, datetime
from unittest.mock import patch, MagicMock

from django.test import TestCase

from opencourt.models import Team, Conference
from opencourt.services.helpers import (
    _build_team_lookup,
    _build_conf_lookup,
    _build_season_stats_defaults,
    _build_game_defaults,
    _build_game_team_stats_defaults,
    _build_game_date_ranges,
    _current_season_year,
    init_api_client,
    configuration,
    TEAMS_ENDPOINT,
    CONFERENCES_ENDPOINT,
    STATS_ENDPOINT,
    GAMES_ENDPOINT,
    RANKINGS_ENDPOINT,
)

# =============================================================================
# Test Data: Mock API Responses
# =============================================================================
# These dicts simulate what the CBBData API returns after .to_dict()
# conversion. They're used by the _build_*_defaults() tests.

SAMPLE_SEASON_STATS_RESPONSE = {
    'seasonLabel': '2025-26',
    'games': 30,
    'wins': 20.0,
    'losses': 10.0,
    'totalMinutes': 6000.0,
    'pace': 68.5,
    'teamStats': {
        'fieldGoals': {'made': 800.0, 'attempted': 1700.0, 'pct': 0.47},
        'twoPointFieldGoals': {'made': 500.0, 'attempted': 1000.0, 'pct': 0.50},
        'threePointFieldGoals': {'made': 300.0, 'attempted': 700.0, 'pct': 0.43},
        'freeThrows': {'made': 400.0, 'attempted': 530.0, 'pct': 0.75},
        'points': {'total': 2400.0},
        'rebounds': {'total': 1100.0, 'offensive': 330.0, 'defensive': 770.0},
        'turnovers': {'total': 350.0},
        'fourFactors': {
            'effectiveFieldGoalPct': 0.52,
            'freeThrowRate': 0.35,
            'offensiveReboundPct': 0.32,
            'turnoverRatio': 0.18,
        },
        'assists': 450.0,
        'steals': 200.0,
        'blocks': 120.0,
        'trueShooting': 0.56,
        'rating': 112.5,
        'possessions': 2000.0,
    },
    'opponentStats': {
        'fieldGoals': {'pct': 0.42},
        'twoPointFieldGoals': {'pct': 0.45},
        'threePointFieldGoals': {'pct': 0.33},
        'freeThrows': {'pct': 0.70},
        'points': {'total': 2100.0},
        'rebounds': {'total': 950.0, 'offensive': 280.0},
        'turnovers': {'total': 400.0},
        'fourFactors': {
            'effectiveFieldGoalPct': 0.46,
            'freeThrowRate': 0.30,
            'turnoverRatio': 0.20,
        },
        'assists': 380.0,
        'trueShooting': 0.50,
        'rating': 98.3,
    },
}

SAMPLE_GAME_RESPONSE = {
    'season': 2025,
    'seasonLabel': '2025-26',
    'seasonType': 'regular',
    'tournament': None,
    'gameType': 'regular',
    'gameNotes': None,
    'status': 'final',
    'startDate': '2026-01-15T19:00:00Z',
    'startTimeTbd': False,
    'homeSeed': None,
    'homePoints': 78,
    'homePeriodPoints': [35, 43],
    'homeWinner': True,
    'homeTeamEloStart': 1650.0,
    'homeTeamEloEnd': 1665.0,
    'awaySeed': None,
    'awayPoints': 72,
    'awayPeriodPoints': [30, 42],
    'awayWinner': False,
    'awayTeamEloStart': 1600.0,
    'awayTeamEloEnd': 1585.0,
    'neutralSite': False,
    'conferenceGame': True,
    'attendance': 9314,
    'venueId': 100,
    'venue': 'Cameron Indoor Stadium',
    'city': 'Durham',
    'state': 'NC',
    'excitement': 6.8,
}

SAMPLE_GAME_TEAM_STATS_RESPONSE = {
    'isHome': True,
    'gameMinutes': 40.0,
    'pace': 70.2,
    'teamStats': {
        'possessions': 72.0,
        'fieldGoals': {'made': 28.0, 'attempted': 60.0, 'pct': 0.467},
        'twoPointFieldGoals': {'made': 18.0, 'attempted': 35.0, 'pct': 0.514},
        'threePointFieldGoals': {'made': 10.0, 'attempted': 25.0, 'pct': 0.400},
        'freeThrows': {'made': 12.0, 'attempted': 16.0, 'pct': 0.750},
        'points': {
            'total': 78,
            'fastBreak': 12,
            'offTurnovers': 14,
            'inPaint': 30,
            'byPeriod': [35, 43],
            'largestLead': 15,
        },
        'rebounds': {'total': 35, 'offensive': 10, 'defensive': 25},
        'turnovers': {'total': 12, 'teamTotal': 2},
        'fourFactors': {
            'effectiveFieldGoalPct': 0.55,
            'freeThrowRate': 0.267,
            'offensiveReboundPct': 0.30,
            'turnoverRatio': 0.16,
        },
        'fouls': {'total': 18, 'technical': 0, 'flagrant': 0},
        'assists': 16,
        'steals': 7,
        'blocks': 4,
        'rating': 108.3,
        'trueShooting': 0.58,
        'gameScore': 25.3,
    },
}

# =============================================================================
# Lookup Builder Tests
# =============================================================================

class BuildTeamLookupTest(TestCase):
    """
    Tests for helpers._build_team_lookup().

    This function builds a {lowercase_school_name: Team} dict used by
    sync functions to resolve team ForeignKeys without repeated DB queries.
    """

    def test_empty_database_returns_empty_dict(self):
        """When no teams exist, the lookup should be an empty dict."""
        lookup = _build_team_lookup()
        self.assertEqual(lookup, {})

    def test_lookup_keyed_by_lowercase_school(self):
        """
        Keys should be the team's school name lowercased, so that
        case-insensitive matching works during sync.
        """
        Team.objects.create(
            source_id=1, school='Duke', abbrv='DUKE',
            display_name='Duke', short_display_name='Duke',
            mascot='Blue Devils', slug='duke'
        )
        lookup = _build_team_lookup()
        self.assertIn('duke', lookup)
        self.assertNotIn('Duke', lookup)

    def test_lookup_values_are_team_objects(self):
        """Values should be Team model instances."""
        team = Team.objects.create(
            source_id=1, school='Duke', abbrv='DUKE',
            display_name='Duke', short_display_name='Duke',
            mascot='Blue Devils', slug='duke'
        )
        lookup = _build_team_lookup()
        self.assertEqual(lookup['duke'].pk, team.pk)

    def test_multiple_teams(self):
        """Lookup should include all teams in the database."""
        Team.objects.create(
            source_id=1, school='Duke', abbrv='DUKE',
            display_name='Duke', short_display_name='Duke',
            mascot='Blue Devils', slug='duke'
        )
        Team.objects.create(
            source_id=2, school='UNC', abbrv='UNC',
            display_name='UNC', short_display_name='UNC',
            mascot='Tar Heels', slug='unc'
        )
        lookup = _build_team_lookup()
        self.assertEqual(len(lookup), 2)
        self.assertIn('unc', lookup)

class BuildConfLookupTest(TestCase):
    """
    Tests for helpers._build_conf_lookup().

    Builds a {lowercase_abbreviation: Conference} dict for FK resolution.
    """

    def test_empty_database_returns_empty_dict(self):
        """When no conferences exist, the lookup should be empty."""
        lookup = _build_conf_lookup()
        self.assertEqual(lookup, {})

    def test_lookup_keyed_by_lowercase_abbreviation(self):
        """Keys should be the conference abbreviation lowercased."""
        Conference.objects.create(
            source_id=1, name='Atlantic Coast Conference',
            abbrv='ACC', short_name='ACC', slug='acc'
        )
        lookup = _build_conf_lookup()
        self.assertIn('acc', lookup)
        self.assertNotIn('ACC', lookup)

    def test_multiple_conferences(self):
        """Lookup should include all conferences in the database."""
        Conference.objects.create(
            source_id=1, name='ACC', abbrv='ACC', short_name='ACC', slug='acc'
        )
        Conference.objects.create(
            source_id=2, name='SEC', abbrv='SEC', short_name='SEC', slug='sec'
        )
        lookup = _build_conf_lookup()
        self.assertEqual(len(lookup), 2)

# =============================================================================
# Defaults Builder Tests
# =============================================================================

class BuildSeasonStatsDefaultsTest(TestCase):
    """
    Tests for helpers._build_season_stats_defaults().

    Extracts ~50 ORM fields from a nested API response dict. Tests verify
    that both the happy path (full data) and degraded path (missing keys)
    produce correct results.
    """

    def test_extracts_top_level_fields(self):
        """Top-level fields like games, wins, losses should map correctly."""
        result = _build_season_stats_defaults(SAMPLE_SEASON_STATS_RESPONSE)
        self.assertEqual(result['season_label'], '2025-26')
        self.assertEqual(result['games'], 30)
        self.assertEqual(result['wins'], 20.0)
        self.assertEqual(result['losses'], 10.0)
        self.assertEqual(result['pace'], 68.5)

    def test_extracts_offensive_shooting(self):
        """Offensive field goal stats should be extracted from the nested dict."""
        result = _build_season_stats_defaults(SAMPLE_SEASON_STATS_RESPONSE)
        self.assertEqual(result['off_fg_made'], 800.0)
        self.assertEqual(result['off_fg_attempted'], 1700.0)
        self.assertAlmostEqual(result['off_fg_pct'], 0.47, places=2)

    def test_extracts_four_factors(self):
        """The Four Factors (shooting, turnovers, rebounding, free throws) should map."""
        result = _build_season_stats_defaults(SAMPLE_SEASON_STATS_RESPONSE)
        self.assertAlmostEqual(result['off_eff_fg_pct'], 0.52, places=2)
        self.assertAlmostEqual(result['off_ft_rate'], 0.35, places=2)
        self.assertAlmostEqual(result['off_oreb_pct'], 0.32, places=2)
        self.assertAlmostEqual(result['off_turnover_ratio'], 0.18, places=2)

    def test_extracts_opponent_stats(self):
        """Opponent/defensive stats should be extracted from opponentStats."""
        result = _build_season_stats_defaults(SAMPLE_SEASON_STATS_RESPONSE)
        self.assertAlmostEqual(result['opp_fg_pct'], 0.42, places=2)
        self.assertEqual(result['opp_points'], 2100.0)
        self.assertAlmostEqual(result['opp_rating'], 98.3, places=1)

    def test_missing_nested_keys_return_none(self):
        """
        When the API omits a nested sub-dict (e.g. no 'fourFactors'),
        the builder should return None for those fields — not crash.
        This handles partial data from early-season or exhibition games.
        """
        sparse_response = {
            'seasonLabel': '2025-26',
            'games': 5,
            'wins': 3.0,
            'losses': 2.0,
            'teamStats': {},       # no sub-dicts
            'opponentStats': {},   # no sub-dicts
        }
        result = _build_season_stats_defaults(sparse_response)
        self.assertIsNone(result['off_fg_pct'])
        self.assertIsNone(result['off_eff_fg_pct'])
        self.assertIsNone(result['opp_rating'])

    def test_completely_empty_dict(self):
        """
        An empty response dict should produce all-None defaults without
        crashing. This guards against malformed API responses.
        """
        result = _build_season_stats_defaults({})
        self.assertIsNone(result['season_label'])
        self.assertIsNone(result['games'])
        self.assertIsNone(result['off_fg_pct'])

class BuildGameDefaultsTest(TestCase):
    """
    Tests for helpers._build_game_defaults().

    Maps a raw API game dict + resolved FK objects into the defaults dict
    for Game.objects.update_or_create().
    """

    def test_extracts_game_metadata(self):
        """Season, status, and venue fields should map correctly."""
        result = _build_game_defaults(
            SAMPLE_GAME_RESPONSE,
            home_team_obj=None, away_team_obj=None,
            home_conf=None, away_conf=None,
        )
        self.assertEqual(result['season'], 2025)
        self.assertEqual(result['season_label'], '2025-26')
        self.assertEqual(result['status'], 'final')
        self.assertEqual(result['venue'], 'Cameron Indoor Stadium')
        self.assertEqual(result['attendance'], 9314)

    def test_extracts_scores_and_winner(self):
        """Home/away points and winner flags should map correctly."""
        result = _build_game_defaults(
            SAMPLE_GAME_RESPONSE,
            home_team_obj=None, away_team_obj=None,
            home_conf=None, away_conf=None,
        )
        self.assertEqual(result['home_points'], 78)
        self.assertEqual(result['away_points'], 72)
        self.assertTrue(result['home_winner'])
        self.assertFalse(result['away_winner'])

    def test_passes_through_fk_objects(self):
        """
        The resolved Team and Conference objects should be passed through
        directly to the defaults dict (not the raw API IDs).
        """
        mock_home = MagicMock(name='HomeTeam')
        mock_away = MagicMock(name='AwayTeam')
        mock_conf = MagicMock(name='HomeConf')

        result = _build_game_defaults(
            SAMPLE_GAME_RESPONSE,
            home_team_obj=mock_home, away_team_obj=mock_away,
            home_conf=mock_conf, away_conf=None,
        )
        self.assertIs(result['home_team'], mock_home)
        self.assertIs(result['away_team'], mock_away)
        self.assertIs(result['home_conference'], mock_conf)
        self.assertIsNone(result['away_conference'])

    def test_elo_ratings_extracted(self):
        """Elo start/end ratings for both teams should be extracted."""
        result = _build_game_defaults(
            SAMPLE_GAME_RESPONSE,
            home_team_obj=None, away_team_obj=None,
            home_conf=None, away_conf=None,
        )
        self.assertEqual(result['home_elo_start'], 1650.0)
        self.assertEqual(result['home_elo_end'], 1665.0)
        self.assertEqual(result['away_elo_start'], 1600.0)
        self.assertEqual(result['away_elo_end'], 1585.0)

class BuildGameTeamStatsDefaultsTest(TestCase):
    """
    Tests for helpers._build_game_team_stats_defaults().

    Maps a raw API per-team box score dict into the defaults dict for
    GameTeamStats.objects.update_or_create().
    """

    def test_extracts_shooting_stats(self):
        """Field goal made/attempted/pct should be extracted."""
        result = _build_game_team_stats_defaults(SAMPLE_GAME_TEAM_STATS_RESPONSE)
        self.assertEqual(result['fg_made'], 28.0)
        self.assertEqual(result['fg_attempted'], 60.0)
        self.assertAlmostEqual(result['fg_pct'], 0.467, places=3)

    def test_extracts_counting_stats(self):
        """Points, assists, steals, blocks, turnovers should be extracted."""
        result = _build_game_team_stats_defaults(SAMPLE_GAME_TEAM_STATS_RESPONSE)
        self.assertEqual(result['points'], 78)
        self.assertEqual(result['assists'], 16)
        self.assertEqual(result['steals'], 7)
        self.assertEqual(result['blocks'], 4)
        self.assertEqual(result['turnovers'], 12)

    def test_extracts_four_factors(self):
        """Game-level Four Factors should be extracted."""
        result = _build_game_team_stats_defaults(SAMPLE_GAME_TEAM_STATS_RESPONSE)
        self.assertAlmostEqual(result['eff_fg_pct'], 0.55, places=2)
        self.assertAlmostEqual(result['oreb_pct'], 0.30, places=2)
        self.assertAlmostEqual(result['turnover_ratio'], 0.16, places=2)

    def test_extracts_points_breakdown(self):
        """Points breakdown (fast break, off turnovers, in paint) should map."""
        result = _build_game_team_stats_defaults(SAMPLE_GAME_TEAM_STATS_RESPONSE)
        self.assertEqual(result['points_fast_break'], 12)
        self.assertEqual(result['points_off_turnovers'], 14)
        self.assertEqual(result['points_in_paint'], 30)
        self.assertEqual(result['largest_lead'], 15)

    def test_extracts_is_home_flag(self):
        """The is_home boolean should be extracted from the top level."""
        result = _build_game_team_stats_defaults(SAMPLE_GAME_TEAM_STATS_RESPONSE)
        self.assertTrue(result['is_home'])

    def test_missing_nested_keys_return_none(self):
        """Missing sub-dicts should result in None values, not crashes."""
        sparse = {'isHome': True, 'teamStats': {}}
        result = _build_game_team_stats_defaults(sparse)
        self.assertIsNone(result['fg_pct'])
        self.assertIsNone(result['eff_fg_pct'])
        self.assertIsNone(result['points'])

# =============================================================================
# Date / Season Helper Tests
# =============================================================================

class BuildGameDateRangesTest(TestCase):
    """
    Tests for helpers._build_game_date_ranges().

    Generates monthly date-range windows (Nov → May) for a given season
    to stay under the API's 3,000-row cap per call.
    """

    def test_returns_seven_windows(self):
        """
        A basketball season spans Nov through May (7 months), so there
        should be exactly 7 date-range windows.
        """
        ranges = _build_game_date_ranges(2025)
        self.assertEqual(len(ranges), 7)

    def test_first_window_starts_in_november(self):
        """The first window should start November 1 of the previous year."""
        ranges = _build_game_date_ranges(2025)
        self.assertEqual(ranges[0]['start_date_range'], datetime(2024, 11, 1))

    def test_last_window_ends_in_june(self):
        """The last window should end June 1 of the season year."""
        ranges = _build_game_date_ranges(2025)
        self.assertEqual(ranges[-1]['end_date_range'], datetime(2025, 6, 1))

    def test_windows_are_contiguous(self):
        """
        Each window's end date should equal the next window's start date,
        ensuring no gaps in coverage.
        """
        ranges = _build_game_date_ranges(2025)
        for i in range(len(ranges) - 1):
            self.assertEqual(
                ranges[i]['end_date_range'],
                ranges[i + 1]['start_date_range'],
                msg=f"Gap between window {i} end and window {i+1} start"
            )

    def test_different_season_year(self):
        """
        Verify the function adjusts correctly for a different season year.
        Season 2020 should span Nov 2019 → May 2020.
        """
        ranges = _build_game_date_ranges(2020)
        self.assertEqual(ranges[0]['start_date_range'], datetime(2019, 11, 1))
        self.assertEqual(ranges[-1]['end_date_range'], datetime(2020, 6, 1))

class CurrentSeasonYearTest(TestCase):
    """
    Tests for helpers._current_season_year().

    The basketball season year is the year the season started:
      - Jul–Dec → current calendar year (season starts this fall)
      - Jan–Jun → previous calendar year (season started last fall)
    """

    @patch('opencourt.services.helpers.date')
    def test_fall_returns_current_year(self, mock_date):
        """In October 2025, the current season is 2025 (started this fall)."""
        mock_date.today.return_value = date(2025, 10, 15)
        mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)
        self.assertEqual(_current_season_year(), 2025)

    @patch('opencourt.services.helpers.date')
    def test_spring_returns_previous_year(self, mock_date):
        """In March 2026, the current season is 2025 (started last fall)."""
        mock_date.today.return_value = date(2026, 3, 15)
        mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)
        self.assertEqual(_current_season_year(), 2025)

    @patch('opencourt.services.helpers.date')
    def test_july_boundary(self, mock_date):
        """July is the boundary — season year equals the calendar year."""
        mock_date.today.return_value = date(2025, 7, 1)
        mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)
        self.assertEqual(_current_season_year(), 2025)

    @patch('opencourt.services.helpers.date')
    def test_june_boundary(self, mock_date):
        """June is still the previous season."""
        mock_date.today.return_value = date(2026, 6, 30)
        mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)
        self.assertEqual(_current_season_year(), 2025)

# =============================================================================
# API Client Factory Tests
# =============================================================================

class InitApiClientTest(TestCase):
    """
    Tests for helpers.init_api_client().

    The factory creates a typed cbbd API client (TeamsApi, GamesApi, etc.)
    from a shared configuration + endpoint name string.
    """

    @patch('opencourt.services.helpers.cbbd.ApiClient')
    @patch('opencourt.services.helpers.cbbd.TeamsApi')
    def test_teams_endpoint_returns_teams_api(self, mock_teams_api, mock_client):
        """Passing 'TeamsApi' should return a cbbd.TeamsApi instance."""
        init_api_client(configuration, TEAMS_ENDPOINT)
        mock_teams_api.assert_called_once()

    @patch('opencourt.services.helpers.cbbd.ApiClient')
    @patch('opencourt.services.helpers.cbbd.ConferencesApi')
    def test_conferences_endpoint(self, mock_conf_api, mock_client):
        """Passing 'ConferencesApi' should return a cbbd.ConferencesApi."""
        init_api_client(configuration, CONFERENCES_ENDPOINT)
        mock_conf_api.assert_called_once()

    @patch('opencourt.services.helpers.cbbd.ApiClient')
    @patch('opencourt.services.helpers.cbbd.GamesApi')
    def test_games_endpoint(self, mock_games_api, mock_client):
        """Passing 'GamesApi' should return a cbbd.GamesApi."""
        init_api_client(configuration, GAMES_ENDPOINT)
        mock_games_api.assert_called_once()

    @patch('opencourt.services.helpers.cbbd.ApiClient')
    def test_invalid_endpoint_raises_value_error(self, mock_client):
        """
        Passing an unrecognized endpoint string should raise ValueError.
        This catches typos in endpoint constants.
        """
        with self.assertRaises(ValueError):
            init_api_client(configuration, 'NonExistentApi')

    @patch('opencourt.services.helpers.cbbd.ApiClient', side_effect=Exception('bad key'))
    def test_bad_config_raises_connection_error(self, mock_client):
        """
        If cbbd.ApiClient() itself fails (bad API key, invalid host),
        init_api_client should wrap the exception in a ConnectionError.
        """
        with self.assertRaises(ConnectionError):
            init_api_client(configuration, TEAMS_ENDPOINT)

# =============================================================================
# Fetch Function Tests
# =============================================================================

class FetchTeamsTest(TestCase):
    """
    Tests for fetch.fetch_teams().

    Verifies that the function calls the CBBData API, returns data on
    success, and returns an empty list on various error types.
    """

    @patch('opencourt.services.fetch.init_api_client')
    def test_success_returns_list(self, mock_init):
        """On success, fetch_teams() should return the API's team list."""
        from opencourt.services.fetch import fetch_teams

        mock_api = MagicMock()
        mock_api.get_teams.return_value = ['team1', 'team2']
        mock_init.return_value = mock_api

        result = fetch_teams()
        self.assertEqual(result, ['team1', 'team2'])

    @patch('opencourt.services.fetch.init_api_client')
    def test_api_exception_returns_empty(self, mock_init):
        """On cbbd.ApiException, fetch_teams() should return []."""
        import cbbd
        from opencourt.services.fetch import fetch_teams

        mock_api = MagicMock()
        mock_api.get_teams.side_effect = cbbd.ApiException(status=500, reason='Internal Server Error')
        mock_init.return_value = mock_api

        result = fetch_teams()
        self.assertEqual(result, [])

    @patch('opencourt.services.fetch.init_api_client')
    def test_connection_error_returns_empty(self, mock_init):
        """On ConnectionError, fetch_teams() should return []."""
        from opencourt.services.fetch import fetch_teams

        mock_init.side_effect = ConnectionError('DNS failure')

        result = fetch_teams()
        self.assertEqual(result, [])

    @patch('opencourt.services.fetch.init_api_client')
    def test_value_error_returns_empty(self, mock_init):
        """On ValueError (bad endpoint config), fetch_teams() should return []."""
        from opencourt.services.fetch import fetch_teams

        mock_init.side_effect = ValueError('Invalid endpoint')

        result = fetch_teams()
        self.assertEqual(result, [])

class FetchConferencesTest(TestCase):
    """
    Tests for fetch.fetch_conferences().

    Same error-handling pattern as fetch_teams().
    """

    @patch('opencourt.services.fetch.init_api_client')
    def test_success_returns_list(self, mock_init):
        """On success, fetch_conferences() should return the conference list."""
        from opencourt.services.fetch import fetch_conferences

        mock_api = MagicMock()
        mock_api.get_conferences.return_value = ['conf1', 'conf2']
        mock_init.return_value = mock_api

        result = fetch_conferences()
        self.assertEqual(result, ['conf1', 'conf2'])

    @patch('opencourt.services.fetch.init_api_client')
    def test_api_exception_returns_empty(self, mock_init):
        """On cbbd.ApiException, should return []."""
        import cbbd
        from opencourt.services.fetch import fetch_conferences

        mock_api = MagicMock()
        mock_api.get_conferences.side_effect = cbbd.ApiException(status=403, reason='Forbidden')
        mock_init.return_value = mock_api

        result = fetch_conferences()
        self.assertEqual(result, [])

class FetchSeasonStatsBulkRetryTest(TestCase):
    """
    Tests for fetch.fetch_season_stats_bulk() retry logic.

    When the API returns HTTP 429 (Too Many Requests), the function
    retries with exponential backoff. These tests verify the retry
    behavior by mocking time.sleep() so tests run instantly.
    """

    @patch('opencourt.services.fetch.time.sleep')
    @patch('opencourt.services.fetch.init_api_client')
    def test_retries_on_429(self, mock_init, mock_sleep):
        """
        On HTTP 429, the function should retry up to MAX_RETRIES times
        before giving up and returning [].
        """
        import cbbd
        from opencourt.services.fetch import fetch_season_stats_bulk

        mock_api = MagicMock()
        exc = cbbd.ApiException(status=429, reason='Too Many Requests')
        exc.headers = {}
        mock_api.get_team_season_stats.side_effect = exc
        mock_init.return_value = mock_api

        result = fetch_season_stats_bulk(2025)
        self.assertEqual(result, [])
        # Should have called sleep for retries (MAX_RETRIES = 4)
        self.assertGreaterEqual(mock_sleep.call_count, 1)

    @patch('opencourt.services.fetch.time.sleep')
    @patch('opencourt.services.fetch.init_api_client')
    def test_succeeds_after_retry(self, mock_init, mock_sleep):
        """
        If the API returns 429 once then succeeds on retry, the function
        should return the successful response.
        """
        import cbbd
        from opencourt.services.fetch import fetch_season_stats_bulk

        mock_api = MagicMock()
        exc = cbbd.ApiException(status=429, reason='Rate limited')
        exc.headers = {}

        # Fail once, then succeed
        mock_api.get_team_season_stats.side_effect = [exc, ['stats1', 'stats2']]
        mock_init.return_value = mock_api

        result = fetch_season_stats_bulk(2025)
        self.assertEqual(result, ['stats1', 'stats2'])

    @patch('opencourt.services.fetch.init_api_client')
    def test_non_429_api_error_no_retry(self, mock_init):
        """
        Non-429 API errors (e.g. 500, 403) should NOT trigger retries —
        they should return [] immediately.
        """
        import cbbd
        from opencourt.services.fetch import fetch_season_stats_bulk

        mock_api = MagicMock()
        mock_api.get_team_season_stats.side_effect = cbbd.ApiException(
            status=500, reason='Internal Server Error'
        )
        mock_init.return_value = mock_api

        result = fetch_season_stats_bulk(2025)
        self.assertEqual(result, [])
        # Should have been called only once (no retries)
        mock_api.get_team_season_stats.assert_called_once()

class FetchGamesBulkTest(TestCase):
    """
    Tests for fetch.fetch_games_bulk().

    Verifies that date-range parameters are forwarded to the API call
    correctly.
    """

    @patch('opencourt.services.fetch.init_api_client')
    def test_date_range_params_forwarded(self, mock_init):
        """
        start_date_range and end_date_range should be passed through to
        the API call as keyword arguments.
        """
        from opencourt.services.fetch import fetch_games_bulk

        mock_api = MagicMock()
        mock_api.get_games.return_value = []
        mock_init.return_value = mock_api

        start = datetime(2025, 11, 1)
        end = datetime(2025, 12, 1)
        fetch_games_bulk(2025, start_date_range=start, end_date_range=end)

        mock_api.get_games.assert_called_once_with(
            season=2025, start_date_range=start, end_date_range=end
        )

    @patch('opencourt.services.fetch.init_api_client')
    def test_no_date_range_params(self, mock_init):
        """
        When no date range is given, only the season param should be
        passed to the API.
        """
        from opencourt.services.fetch import fetch_games_bulk

        mock_api = MagicMock()
        mock_api.get_games.return_value = []
        mock_init.return_value = mock_api

        fetch_games_bulk(2025)

        mock_api.get_games.assert_called_once_with(season=2025)
