# test_models.py — Unit tests for opencourt/models.py.
#
# Tests the business logic baked into our Django models: auto-generated
# slugs, save()-time calculations (win_pct), computed properties
# (current_season, point_margin), string representations, unique
# constraints, and default ordering.
#
# Each test class targets one model. Tests create model instances
# directly using Django's ORM — the test runner provides a fresh
# temporary database for each test method, so there's no cross-test
# contamination.
#
# Run just these tests:
#   uv run python manage.py test opencourt.tests.test_models

from django.test import TestCase
from django.db import IntegrityError
from opencourt.models import (
    Team, Conference, TeamSeasonStats, Game, GameTeamStats, Ranking,
)
from datetime import datetime
from django.utils import timezone

# =============================================================================
# Test Data Factory Helpers
# =============================================================================
# Small helper functions to create model instances with sensible defaults.
# These reduce boilerplate across tests and make test setup self-documenting.

def make_conference(**overrides):
    """
    Create and save a Conference with default field values.

    Any field can be overridden by passing keyword arguments.
    Defaults produce the ACC as a representative conference.
    """
    defaults = {
        'source_id': 1,
        'name': 'Atlantic Coast Conference',
        'abbrv': 'ACC',
        'short_name': 'ACC',
    }
    defaults.update(overrides)
    return Conference.objects.create(**defaults)

def make_team(conference=None, **overrides):
    """
    Create and save a Team with default field values.

    Pass conference= to link to a Conference, or leave None.
    Defaults produce Duke Blue Devils as a representative team.
    """
    defaults = {
        'source_id': 150,
        'school': 'Duke',
        'abbrv': 'DUKE',
        'display_name': 'Duke Blue Devils',
        'short_display_name': 'Duke',
        'mascot': 'Blue Devils',
        'primary_color': '#001A57',
        'secondary_color': '#FFFFFF',
        'conference': conference,
    }
    defaults.update(overrides)
    return Team.objects.create(**defaults)

def make_season_stats(team, **overrides):
    """
    Create and save a TeamSeasonStats row with default field values.

    The team argument is required (it's a ForeignKey). Defaults produce
    a realistic 2025-26 season with stats typical of a competitive D1 team.
    """
    defaults = {
        'team': team,
        'season': 2025,
        'season_label': '2025-26',
        'games': 30,
        'wins': 20.0,
        'losses': 10.0,
        'pace': 68.5,
        'off_points': 2400.0,
        'opp_points': 2100.0,
        'off_rating': 112.5,
        'opp_rating': 98.3,
        'off_eff_fg_pct': 0.52,
        'off_turnover_ratio': 0.18,
        'off_oreb_pct': 0.32,
        'off_ft_rate': 0.35,
        'off_turnovers': 350.0,
        'off_possessions': 2000.0,
        'off_blocks': 120.0,
        'off_assists': 450.0,
        'off_fg_pct': 0.46,
        'off_3pt_pct': 0.36,
        'off_ft_pct': 0.75,
        'off_reb_total': 1100.0,
        'off_reb_offensive': 330.0,
    }
    defaults.update(overrides)
    return TeamSeasonStats.objects.create(**defaults)

def make_game(home_team, away_team, **overrides):
    """
    Create and save a Game between two teams with default field values.

    Both team arguments are required. Defaults produce a completed
    regular-season game from the 2025-26 season.
    """
    defaults = {
        'source_id': 'game-001',
        'season': 2025,
        'season_label': '2025-26',
        'season_type': 'regular',
        'status': 'final',
        'start_date': timezone.now(),
        'home_team': home_team,
        'away_team': away_team,
        'home_points': 78,
        'away_points': 72,
        'home_winner': True,
        'away_winner': False,
    }
    defaults.update(overrides)
    return Game.objects.create(**defaults)

# =============================================================================
# Conference Model Tests
# =============================================================================

class ConferenceModelTest(TestCase):
    """
    Tests for the Conference model.

    Covers: auto-slug generation from short_name, __str__ representation.
    """

    def test_slug_auto_generated_from_short_name(self):
        """
        Saving a Conference without a slug should auto-generate one from
        short_name. E.g. "Big Ten" → "big-ten".
        """
        conf = make_conference(short_name='Big Ten', slug='')
        self.assertEqual(conf.slug, 'big-ten')

    def test_slug_not_overwritten_on_subsequent_save(self):
        """
        Once a slug is set, re-saving the Conference should not change it.
        This protects URLs from breaking when the model is updated.
        """
        conf = make_conference(short_name='Big Ten', slug='')
        original_slug = conf.slug
        conf.name = 'Big Ten Conference Updated'
        conf.save()
        self.assertEqual(conf.slug, original_slug)

    def test_manual_slug_preserved(self):
        """
        If a slug is explicitly provided at creation time, it should be
        kept as-is rather than overwritten by the auto-generation logic.
        """
        conf = make_conference(slug='custom-slug')
        self.assertEqual(conf.slug, 'custom-slug')

    def test_str_returns_abbreviation(self):
        """Conference.__str__() should return the abbreviation (e.g. 'ACC')."""
        conf = make_conference(abbrv='SEC')
        self.assertEqual(str(conf), 'SEC')

# =============================================================================
# Team Model Tests
# =============================================================================

class TeamModelTest(TestCase):
    """
    Tests for the Team model.

    Covers: auto-slug generation from school + mascot, slug preservation,
    current_season property (both lazy and prefetched paths), and __str__.
    """

    def test_slug_auto_generated_from_school_and_mascot(self):
        """
        Saving a Team without a slug should auto-generate one from
        school + mascot. E.g. "Duke" + "Blue Devils" → "duke-blue-devils".
        """
        team = make_team(slug='')
        self.assertEqual(team.slug, 'duke-blue-devils')

    def test_slug_not_overwritten_on_subsequent_save(self):
        """
        Re-saving a Team should not change an already-set slug. URLs
        depend on slug stability across updates.
        """
        team = make_team(slug='')
        original_slug = team.slug
        team.school = 'Duke University'
        team.save()
        self.assertEqual(team.slug, original_slug)

    def test_manual_slug_preserved(self):
        """Explicitly provided slugs should not be overwritten."""
        team = make_team(slug='my-custom-slug')
        self.assertEqual(team.slug, 'my-custom-slug')

    def test_str_returns_school_name(self):
        """Team.__str__() should return the school name (e.g. 'Duke')."""
        team = make_team(school='Tennessee')
        self.assertEqual(str(team), 'Tennessee')

    def test_current_season_returns_most_recent(self):
        """
        The current_season property should return the TeamSeasonStats
        with the highest season value (most recent year).
        """
        team = make_team()
        # Create older season first, then current
        make_season_stats(team, season=2023, season_label='2023-24')
        current = make_season_stats(team, season=2025, season_label='2025-26')
        make_season_stats(team, season=2024, season_label='2024-25')

        self.assertEqual(team.current_season.pk, current.pk)

    def test_current_season_none_when_no_stats(self):
        """
        current_season should return None for a team with no
        TeamSeasonStats rows (e.g. newly synced team before stats sync).
        """
        team = make_team()
        self.assertIsNone(team.current_season)

    def test_current_season_with_prefetch_attr(self):
        """
        When the view sets _current_stats via Prefetch(to_attr=...),
        current_season should use that cached list instead of querying.
        """
        team = make_team()
        stats_obj = make_season_stats(team, season=2025)

        # Simulate what the view's Prefetch does
        team._current_stats = [stats_obj]
        self.assertEqual(team.current_season.pk, stats_obj.pk)

    def test_current_season_with_empty_prefetch_attr(self):
        """
        When _current_stats is an empty list (team has no stats for the
        filtered season), current_season should return None.
        """
        team = make_team()
        team._current_stats = []
        self.assertIsNone(team.current_season)

    def test_conference_fk_set_null_on_delete(self):
        """
        Deleting a Conference should set the team's conference FK to NULL
        rather than cascading the delete (on_delete=SET_NULL).
        """
        conf = make_conference()
        team = make_team(conference=conf)
        conf.delete()
        team.refresh_from_db()
        self.assertIsNone(team.conference)

# =============================================================================
# TeamSeasonStats Model Tests
# =============================================================================

class TeamSeasonStatsModelTest(TestCase):
    """
    Tests for the TeamSeasonStats model.

    Covers: auto-calculated win_pct on save(), point_margin property,
    unique_together constraint, default ordering, and __str__.
    """

    def setUp(self):
        """Create a team to attach stats to for every test in this class."""
        self.team = make_team()

    def test_win_pct_auto_calculated_on_save(self):
        """
        save() should auto-calculate win_pct from wins and losses using
        the win_percentage() helper. 20 wins, 10 losses → 66.67%.
        """
        stats_obj = make_season_stats(self.team, wins=20.0, losses=10.0)
        self.assertEqual(stats_obj.win_pct, 66.67)

    def test_win_pct_zero_games(self):
        """
        win_pct should be 0.0 when both wins and losses are 0 (team
        hasn't played yet in the season).
        """
        stats_obj = make_season_stats(self.team, wins=0.0, losses=0.0)
        self.assertEqual(stats_obj.win_pct, 0.0)

    def test_win_pct_undefeated(self):
        """Undefeated team (30-0) should have win_pct = 100."""
        stats_obj = make_season_stats(self.team, wins=30.0, losses=0.0)
        self.assertEqual(stats_obj.win_pct, 100)

    def test_win_pct_recalculated_on_update(self):
        """
        Updating wins/losses and re-saving should recalculate win_pct.
        This verifies the save() override runs on updates, not just creates.
        """
        stats_obj = make_season_stats(self.team, wins=20.0, losses=10.0)
        self.assertEqual(stats_obj.win_pct, 66.67)

        stats_obj.wins = 25.0
        stats_obj.losses = 5.0
        stats_obj.save()
        self.assertEqual(stats_obj.win_pct, 83.33)

    def test_point_margin_positive(self):
        """
        point_margin property should return the difference between
        offensive points and opponent points (2400 - 2100 = 300).
        """
        stats_obj = make_season_stats(
            self.team, off_points=2400.0, opp_points=2100.0
        )
        self.assertEqual(stats_obj.point_margin, 300.0)

    def test_point_margin_negative(self):
        """Negative margin when opponents outscore the team."""
        stats_obj = make_season_stats(
            self.team, off_points=1800.0, opp_points=2100.0
        )
        self.assertEqual(stats_obj.point_margin, -300.0)

    def test_point_margin_none_when_off_points_missing(self):
        """
        point_margin should return None when off_points is None
        (e.g. stats haven't been synced yet for this season).
        """
        stats_obj = make_season_stats(
            self.team, off_points=None, opp_points=2100.0
        )
        self.assertIsNone(stats_obj.point_margin)

    def test_point_margin_none_when_opp_points_missing(self):
        """point_margin should return None when opp_points is None."""
        stats_obj = make_season_stats(
            self.team, off_points=2400.0, opp_points=None
        )
        self.assertIsNone(stats_obj.point_margin)

    def test_unique_together_team_season(self):
        """
        The (team, season) pair must be unique. Creating two stats rows
        for the same team and season should raise IntegrityError.
        """
        make_season_stats(self.team, season=2025)
        with self.assertRaises(IntegrityError):
            make_season_stats(self.team, season=2025)

    def test_ordering_newest_first(self):
        """Default ordering is -season (newest season first in querysets)."""
        make_season_stats(self.team, season=2023, season_label='2023-24')
        make_season_stats(self.team, season=2025, season_label='2025-26')
        make_season_stats(self.team, season=2024, season_label='2024-25')

        seasons = list(
            TeamSeasonStats.objects.filter(team=self.team)
            .values_list('season', flat=True)
        )
        self.assertEqual(seasons, [2025, 2024, 2023])

    def test_str_format(self):
        """__str__() should be '{school} — {season_label}'."""
        stats_obj = make_season_stats(self.team, season_label='2025-26')
        self.assertEqual(str(stats_obj), 'Duke — 2025-26')

# =============================================================================
# Game Model Tests
# =============================================================================

class GameModelTest(TestCase):
    """
    Tests for the Game model.

    Covers: default ordering, string representation, and FK relationships.
    """

    def setUp(self):
        """Create two teams that will play against each other."""
        self.home_team = make_team(
            source_id=1, school='Duke', mascot='Blue Devils', slug='duke'
        )
        self.away_team = make_team(
            source_id=2, school='UNC', mascot='Tar Heels', slug='unc'
        )

    def test_str_format(self):
        """__str__() should be '{home_team} vs {away_team} — {season_label}'."""
        game = make_game(self.home_team, self.away_team)
        self.assertEqual(str(game), 'Duke vs UNC — 2025-26')

    def test_ordering_newest_first(self):
        """Default ordering is -start_date (most recent game first)."""
        older = make_game(
            self.home_team, self.away_team,
            source_id='game-old',
            start_date=timezone.make_aware(datetime(2025, 12, 1)),
        )
        newer = make_game(
            self.home_team, self.away_team,
            source_id='game-new',
            start_date=timezone.make_aware(datetime(2026, 1, 15)),
        )

        games = list(Game.objects.all())
        self.assertEqual(games[0].pk, newer.pk)
        self.assertEqual(games[1].pk, older.pk)

    def test_home_games_reverse_lookup(self):
        """team.home_games.all() should return games where the team was home."""
        game = make_game(self.home_team, self.away_team)
        self.assertIn(game, self.home_team.home_games.all())
        self.assertNotIn(game, self.home_team.away_games.all())

    def test_away_games_reverse_lookup(self):
        """team.away_games.all() should return games where the team was away."""
        game = make_game(self.home_team, self.away_team)
        self.assertIn(game, self.away_team.away_games.all())
        self.assertNotIn(game, self.away_team.home_games.all())

    def test_cascade_delete_with_home_team(self):
        """Deleting a home team should cascade-delete the game."""
        make_game(self.home_team, self.away_team)
        self.home_team.delete()
        self.assertEqual(Game.objects.count(), 0)

# =============================================================================
# GameTeamStats Model Tests
# =============================================================================

class GameTeamStatsModelTest(TestCase):
    """
    Tests for the GameTeamStats model.

    Covers: unique_together constraint (game, team), string
    representation, and FK relationships.
    """

    def setUp(self):
        """Create teams, a game, and a stats row for the home team."""
        self.home_team = make_team(
            source_id=1, school='Duke', mascot='Blue Devils', slug='duke'
        )
        self.away_team = make_team(
            source_id=2, school='UNC', mascot='Tar Heels', slug='unc'
        )
        self.game = make_game(self.home_team, self.away_team)

    def test_unique_together_game_team(self):
        """
        The (game, team) pair must be unique. Creating two stat rows for
        the same team in the same game should raise IntegrityError.
        """
        GameTeamStats.objects.create(
            game=self.game, team=self.home_team, is_home=True
        )
        with self.assertRaises(IntegrityError):
            GameTeamStats.objects.create(
                game=self.game, team=self.home_team, is_home=True
            )

    def test_two_stats_per_game(self):
        """
        Each game should have exactly two GameTeamStats rows (one per team).
        This mirrors the API's per-team box score structure.
        """
        GameTeamStats.objects.create(
            game=self.game, team=self.home_team, is_home=True
        )
        GameTeamStats.objects.create(
            game=self.game, team=self.away_team, is_home=False
        )
        self.assertEqual(self.game.team_stats.count(), 2)

    def test_str_format(self):
        """__str__() should be '{team} — Game {game_id}'."""
        gts = GameTeamStats.objects.create(
            game=self.game, team=self.home_team, is_home=True
        )
        self.assertEqual(str(gts), f'Duke — Game {self.game.pk}')

    def test_team_game_stats_reverse_lookup(self):
        """team.game_stats.all() should return all box score rows for a team."""
        gts = GameTeamStats.objects.create(
            game=self.game, team=self.home_team, is_home=True
        )
        self.assertIn(gts, self.home_team.game_stats.all())

# =============================================================================
# Ranking Model Tests
# =============================================================================

class RankingModelTest(TestCase):
    """
    Tests for the Ranking model.

    Covers: unique_together constraint (5-field composite), string
    representation, and default ordering.
    """

    def setUp(self):
        """Create a team for ranking entries."""
        self.team = make_team()

    def _make_ranking(self, **overrides):
        """Helper to create a Ranking with sensible defaults."""
        defaults = {
            'team': self.team,
            'season': 2025,
            'season_type': 'regular',
            'week': 10,
            'poll_type': 'AP Top 25',
            'ranking': 5,
            'points': 1200,
            'first_place_votes': 10,
        }
        defaults.update(overrides)
        return Ranking.objects.create(**defaults)

    def test_unique_together_five_fields(self):
        """
        The (season, season_type, week, poll_type, team) tuple must be
        unique. Duplicate rows should raise IntegrityError.
        """
        self._make_ranking()
        with self.assertRaises(IntegrityError):
            self._make_ranking()

    def test_different_poll_types_allowed(self):
        """
        The same team can be ranked in both AP and Coaches polls for the
        same week — the poll_type field differentiates them.
        """
        self._make_ranking(poll_type='AP Top 25')
        coaches = self._make_ranking(poll_type='Coaches Poll')
        self.assertEqual(Ranking.objects.count(), 2)
        self.assertEqual(coaches.poll_type, 'Coaches Poll')

    def test_str_format(self):
        """__str__() should include team, ranking, poll type, week, and season."""
        ranking = self._make_ranking(ranking=3, poll_type='AP Top 25', week=10)
        self.assertEqual(str(ranking), 'Duke — #3 (AP Top 25, Week 10, 2025)')

    def test_ordering_default(self):
        """
        Default ordering is [-season, -week, ranking] — newest season first,
        newest week first, then lowest ranking number first within a week.
        """
        self._make_ranking(season=2024, week=5, ranking=10, poll_type='AP 2024')
        self._make_ranking(season=2025, week=10, ranking=1, poll_type='AP W10 R1')
        self._make_ranking(season=2025, week=10, ranking=5, poll_type='AP W10 R5')

        rankings = list(Ranking.objects.values_list('ranking', flat=True))
        # 2025 week 10 rank 1, then 2025 week 10 rank 5, then 2024 week 5 rank 10
        self.assertEqual(rankings, [1, 5, 10])
