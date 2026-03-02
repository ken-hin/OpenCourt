# tests.py — Unit tests for the opencourt app.
#
# Write tests for your models, views, and any custom logic here.
# Run all tests with: python manage.py test
# Run just this app's tests with: python manage.py test opencourt

from django.test import TestCase
from opencourt import stats

# Tests will be defined here
class Win_percent(TestCase):
    def test_win_test(self):
        self.assertEqual(stats.win_percentage(36, 20), 64.29)