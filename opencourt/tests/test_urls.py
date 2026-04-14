# test_urls.py — Unit tests for opencourt/urls.py.
#
# Tests URL routing: verifying that named routes resolve to the correct
# view classes, and that reverse() produces the expected URL paths.
# These tests catch regressions when URLs are reorganized or renamed.
#
# No database setup is needed — URL resolution is pure configuration
# matching, independent of any model data.
#
# Run just these tests:
#   uv run python manage.py test opencourt.tests.test_urls

from django.test import TestCase
from django.urls import reverse, resolve

from opencourt import views

class URLResolveTest(TestCase):
    """
    Tests that URL paths resolve to the correct view classes.

    Uses Django's resolve() to look up a URL path and verify the view
    function or class it maps to. This ensures the URL → view wiring
    in urls.py is correct.
    """

    def test_home_resolves(self):
        """/ should resolve to HomeView."""
        match = resolve('/')
        self.assertEqual(match.func.view_class, views.HomeView)

    def test_about_resolves(self):
        """/about/ should resolve to AboutView."""
        match = resolve('/about/')
        self.assertEqual(match.func.view_class, views.AboutView)

    def test_teams_resolves(self):
        """/teams/ should resolve to TeamListView."""
        match = resolve('/teams/')
        self.assertEqual(match.func.view_class, views.TeamListView)

    def test_conferences_resolves(self):
        """/conferences/ should resolve to ConferenceListView."""
        match = resolve('/conferences/')
        self.assertEqual(match.func.view_class, views.ConferenceListView)

    def test_rankings_resolves(self):
        """/rankings/ should resolve to RankingsListView."""
        match = resolve('/rankings/')
        self.assertEqual(match.func.view_class, views.RankingsListView)

    def test_upcoming_resolves(self):
        """/upcoming/ should resolve to UpcomingView."""
        match = resolve('/upcoming/')
        self.assertEqual(match.func.view_class, views.UpcomingView)

    def test_team_detail_resolves(self):
        """/<slug>/ should resolve to TeamDetailView."""
        match = resolve('/duke-blue-devils/')
        self.assertEqual(match.func.view_class, views.TeamDetailView)

    def test_team_detail_captures_slug(self):
        """The slug URL parameter should be captured and passed to the view."""
        match = resolve('/duke-blue-devils/')
        self.assertEqual(match.kwargs['slug'], 'duke-blue-devils')

class URLReverseTest(TestCase):
    """
    Tests that reverse() generates the correct URL paths from named routes.

    Uses Django's reverse() to build a URL from a view name and verify
    the output. This ensures templates using {% url 'opencourt:...' %}
    will generate working links.
    """

    def test_home_reverse(self):
        """reverse('opencourt:home') should produce '/'."""
        url = reverse('opencourt:home')
        self.assertEqual(url, '/')

    def test_about_reverse(self):
        """reverse('opencourt:about') should produce '/about/'."""
        url = reverse('opencourt:about')
        self.assertEqual(url, '/about/')

    def test_teams_reverse(self):
        """reverse('opencourt:teams') should produce '/teams/'."""
        url = reverse('opencourt:teams')
        self.assertEqual(url, '/teams/')

    def test_conferences_reverse(self):
        """reverse('opencourt:conferences') should produce '/conferences/'."""
        url = reverse('opencourt:conferences')
        self.assertEqual(url, '/conferences/')

    def test_rankings_reverse(self):
        """reverse('opencourt:rankings') should produce '/rankings/'."""
        url = reverse('opencourt:rankings')
        self.assertEqual(url, '/rankings/')

    def test_upcoming_reverse(self):
        """reverse('opencourt:upcoming') should produce '/upcoming/'."""
        url = reverse('opencourt:upcoming')
        self.assertEqual(url, '/upcoming/')

    def test_team_detail_reverse(self):
        """
        reverse('opencourt:team-detail', kwargs={'slug': 'duke-blue-devils'})
        should produce '/duke-blue-devils/'.
        """
        url = reverse('opencourt:team-detail', kwargs={'slug': 'duke-blue-devils'})
        self.assertEqual(url, '/duke-blue-devils/')

    def test_team_detail_reverse_different_slug(self):
        """Verify reverse works with any valid slug, not just a hardcoded one."""
        url = reverse('opencourt:team-detail', kwargs={'slug': 'tennessee-volunteers'})
        self.assertEqual(url, '/tennessee-volunteers/')
