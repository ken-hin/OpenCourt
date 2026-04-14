# test_stats.py — Unit tests for opencourt/stats.py.
#
# Tests for the two pure helper functions used in model calculations
# and template rendering: win_percentage() and point_differential().
#
# These are the simplest tests in the suite — no database, no mocking,
# just input → output verification. The original 4 tests for
# win_percentage() are preserved here; point_differential() tests are new.
#
# Run just these tests:
#   uv run python manage.py test opencourt.tests.test_stats

from django.test import TestCase
from opencourt import stats

class WinPercentageTest(TestCase):
    """
    Tests for stats.win_percentage(wins, losses).

    win_percentage returns a rounded float representing the percentage of
    games won. Expected behavior:
      - Normal case: wins / (wins + losses) * 100, rounded to 2 decimal places
      - Undefeated: 100 (no losses)
      - Winless: 0 (no wins)
      - No games: 0.0 (guards against division by zero)
    """

    def test_standard_case(self):
        """Standard case: 36 wins, 20 losses → 64.29%."""
        self.assertEqual(
            stats.win_percentage(36, 20),
            64.29,
            msg="Win percentage should be 64.29 for a 36-20 record"
        )

    def test_undefeated(self):
        """Undefeated team: 20 wins, 0 losses → 100%."""
        self.assertEqual(
            stats.win_percentage(20, 0),
            100,
            msg="Win percentage should be 100 for an undefeated team"
        )

    def test_winless(self):
        """Winless team: 0 wins, 20 losses → 0%."""
        self.assertEqual(
            stats.win_percentage(0, 20),
            0,
            msg="Win percentage should be 0 for a winless team"
        )

    def test_no_games_played(self):
        """Team with no games: 0 wins, 0 losses → 0.0 (avoid division by zero)."""
        self.assertEqual(
            stats.win_percentage(0, 0),
            0.0,
            msg="Win percentage should handle zero games without crashing"
        )

    def test_float_inputs(self):
        """
        The CBBData API returns wins/losses as floats (e.g. 20.0, 10.0).
        Verify win_percentage handles float inputs correctly.
        """
        self.assertEqual(
            stats.win_percentage(20.0, 10.0),
            66.67,
            msg="Win percentage should work with float inputs from the API"
        )

    def test_single_game_win(self):
        """Edge case: 1 win, 0 losses → 100%."""
        self.assertEqual(
            stats.win_percentage(1, 0),
            100,
            msg="Win percentage should be 100 for a 1-0 record"
        )

    def test_single_game_loss(self):
        """Edge case: 0 wins, 1 loss → 0%."""
        self.assertEqual(
            stats.win_percentage(0, 1),
            0,
            msg="Win percentage should be 0 for a 0-1 record"
        )

    def test_even_record(self):
        """Even record: 15 wins, 15 losses → 50%."""
        self.assertEqual(
            stats.win_percentage(15, 15),
            50.0,
            msg="Win percentage should be exactly 50 for an even record"
        )

class PointDifferentialTest(TestCase):
    """
    Tests for stats.point_differential(scored_points, allowed_points).

    point_differential returns the difference between points scored and
    points allowed over a season. Positive means the team outscored its
    opponents; negative means they were outscored.
    """

    def test_positive_differential(self):
        """Team that outscores opponents: 2500 scored, 2200 allowed → +300."""
        self.assertEqual(
            stats.point_differential(2500, 2200),
            300,
            msg="Point differential should be positive when team outscores opponents"
        )

    def test_negative_differential(self):
        """Team that is outscored: 1800 scored, 2100 allowed → -300."""
        self.assertEqual(
            stats.point_differential(1800, 2100),
            -300,
            msg="Point differential should be negative when opponents outscore team"
        )

    def test_zero_differential(self):
        """Teams score equal points: 2000 scored, 2000 allowed → 0."""
        self.assertEqual(
            stats.point_differential(2000, 2000),
            0,
            msg="Point differential should be 0 when points are equal"
        )

    def test_zero_points(self):
        """Edge case: no points scored or allowed → 0."""
        self.assertEqual(
            stats.point_differential(0, 0),
            0,
            msg="Point differential should be 0 when no points are scored or allowed"
        )

    def test_float_inputs(self):
        """
        Season totals from the API are floats. Verify float arithmetic
        produces the expected result.
        """
        result = stats.point_differential(2500.0, 2200.0)
        self.assertAlmostEqual(
            result,
            300.0,
            places=1,
            msg="Point differential should work with float inputs"
        )
