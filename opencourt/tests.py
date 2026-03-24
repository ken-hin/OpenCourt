# tests.py — Unit tests for the opencourt app.
#
# Tests are organized by the module they cover (stats, models, views, etc.).
# Each test class groups related cases — add a new class for each new module.
#
# Run all tests: python manage.py test
# Run just this app: python manage.py test opencourt
# Run one class: python manage.py test opencourt.tests.WinPercentTest

from django.test import TestCase
from opencourt import stats


class WinPercentTest(TestCase):
    """
    Tests for stats.win_percentage(wins, losses).

    win_percentage returns a rounded float representing the percentage of
    games won. Expected behavior:
      - Normal case: wins / (wins + losses) * 100, rounded to 2 decimal places
      - Undefeated: 100 (no losses)
      - Winless: 0 (no wins)
    """

    def test_win_test(self):
        """Standard case: 36 wins, 20 losses → 64.29%."""
        self.assertEqual(
            stats.win_percentage(36, 20),
            64.29,
            msg="Win percentage is calculated correctly"
        )

    def test_win_test_2(self):
        """Undefeated team: 20 wins, 0 losses → 100%."""
        self.assertEqual(
            stats.win_percentage(20, 0),
            100,
            msg="Win percentage is calculated correctly"
        )

    def test_win_test_3(self):
        """Winless team: 0 wins, 20 losses → 0%."""
        self.assertEqual(
            stats.win_percentage(0, 20),
            0,
            msg="Win percentage is calculated correctly"
        )

    def test_win_test_4(self):
        """Team with no games: 0 wins, 0 losses → 0.0%."""
        self.assertEqual(
            stats.win_percentage(0, 0),
            0.0,
            msg="Win percentage handles zero games correctly"
        )
