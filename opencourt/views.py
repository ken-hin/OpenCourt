# views.py — View functions and classes for the opencourt app.
#
# Views receive HTTP requests and return HTTP responses.
# Wire each view up to a URL in opencourt/urls.py.
# Templates live in templates/opencourt/.

import json
from django.views.generic import TemplateView, ListView
from django.shortcuts import get_object_or_404
from opencourt.models import Team, Conference, TeamSeasonStats

class HomeView(TemplateView):
    """Renders the home page."""
    template_name = 'opencourt/home.html'

# Additional views will be defined here (e.g. TeamDetailView, ConferenceView)
class AboutView(TemplateView):
    """Renders the about page."""
    template_name = 'opencourt/about.html'

class TeamListView(ListView):
    """Renders the team list page."""
    model = Team
    template_name = 'opencourt/teams.html'

    def get_queryset(self):
      return Team.objects.all()

class ConferenceListView(ListView):
    """Renders the conference list page."""
    model = Conference
    template_name = 'opencourt/conferences.html'

    def get_queryset(self):
      return Conference.objects.all()

class TeamDetailView(TemplateView):
    """Renders the team detail page with season stats and chart data."""
    template_name = 'opencourt/team_details.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        team = get_object_or_404(Team, slug=self.kwargs['slug'])
        # Order ascending so chart x-axis runs oldest → newest
        season_stats = list(TeamSeasonStats.objects.filter(team=team).order_by('season'))

        # Build JSON-serializable lists for each chart series.
        # The template drops these straight into ApexCharts with {{ var|safe }}.
        season_labels = [f'{s.season}' for s in season_stats]
        # Basic stats
        wins       = [int(s.wins) if s.wins is not None else None for s in season_stats]
        losses     = [int(s.losses) if s.losses is not None else None for s in season_stats]
        win_pct    = [round(s.win_pct, 1) if s.win_pct else None for s in season_stats]
        off_rating = [round(s.off_rating, 1) if s.off_rating else None for s in season_stats]
        opp_rating = [round(s.opp_rating, 1) if s.opp_rating else None for s in season_stats]
        # Four Factors
        off_eff_fg_pct = [round(s.off_eff_fg_pct, 1) if s.off_eff_fg_pct else None for s in season_stats]
        off_to_ratio   = [round(s.off_turnover_ratio*100, 1) if s.off_turnover_ratio else None for s in season_stats]
        off_oreb_pct   = [round(s.off_oreb_pct, 1) if s.off_oreb_pct else None for s in season_stats]
        off_ft_rate    = [round(s.off_ft_rate, 1)  if s.off_ft_rate else None for s in season_stats]
        # Other Stats (will need to add more as the team view is built out)
        off_3pt_pct = [round(s.off_3pt_pct, 1) if s.off_3pt_pct else None for s in season_stats]
        off_pts     = [round(s.off_points / s.games, 1) if s.off_points and s.games else None for s in season_stats]
        opp_pts     = [round(s.opp_points / s.games, 1) if s.opp_points and s.games else None for s in season_stats]
        # Context passed to TeamDetailView. This is the data that is accessible from the html page.
        # Will need to update or add more as the team view is built out.
        context['team'] = team
        context['season_stats'] = season_stats
        context['stat_years'] = json.dumps(season_labels)

        context['wins'] = json.dumps(wins)
        context['losses'] = json.dumps(losses)
        context['win_pct'] = json.dumps(win_pct)
        context['off_rtg'] = json.dumps(off_rating)
        context['opp_rtg'] = json.dumps(opp_rating)

        context['eff_fg'] = json.dumps(off_eff_fg_pct)
        context['to_ratio'] = json.dumps(off_to_ratio)
        context['oreb_pct'] = json.dumps(off_oreb_pct)
        context['ft_rate'] = json.dumps(off_ft_rate)

        context['3pt_pct'] = json.dumps(off_3pt_pct)
        context['off_pts'] = json.dumps(off_pts)
        context['opp_pts'] = json.dumps(opp_pts)
        return context
