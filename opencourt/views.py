# views.py — View functions and classes for the opencourt app.
#
# Each view receives an HTTP request and returns a response (usually a
# rendered template). Django's class-based views handle the boilerplate —
# we just override the parts we need (queryset, context data, etc.).
#
# Wiring:
#   URL pattern  →  View class  →  Template
#   See opencourt/urls.py for the full URL ↔ view mapping.
#   Templates live in templates/opencourt/.
#
# Data flow for template rendering:
#   1. View fetches model data (Teams, Conferences, Stats) via the ORM
#   2. Data is packaged into a context dict
#   3. Django renders the template with that context
#   For chart-heavy pages (TeamDetailView), Python lists are serialized
#   to JSON so the template can drop them straight into ApexCharts config.
#
# Performance notes:
#   - Use prefetch_related() on any view that traverses FK relationships in
#     the template to avoid N+1 queries. See ConferenceListView for an example.
#   - The Team.current_season property works best with a Prefetch(..., to_attr=
#     '_current_stats') so stats are loaded in bulk rather than per-team.

import json
from datetime import date
from django.db.models import Prefetch, Q
from django.views.generic import TemplateView, ListView
from django.db.models import Case, When, Value, OuterRef, Subquery, FloatField, F, ExpressionWrapper
from django.shortcuts import get_object_or_404
from opencourt.models import Team, Conference, TeamSeasonStats, Game, GameTeamStats


class HomeView(TemplateView):
    """Landing page. No dynamic data — just renders the static home template."""
    template_name = 'opencourt/home.html'


class AboutView(TemplateView):
    """Static about/info page. No model data needed."""
    template_name = 'opencourt/about.html'


class TeamListView(ListView):
    """
    Displays all Division I teams in a filterable list.

    Template: teams.html
    Context variables:
      team_list        — all Team objects (auto-named by ListView from the model),
                         each with conference select_related to avoid N+1 on card rendering.
      conference_list  — all Conference objects, added via get_context_data for the
                         conference filter dropdown.

    The template supports client-side filtering by conference using JS —
    no server-side filtering is needed since the full team list is small
    enough (~360 teams) to send in one response.
    """
    model = Team
    template_name = 'opencourt/teams.html'

    def get_queryset(self):
      return Team.objects.select_related('conference').order_by('school')

    def get_context_data(self, **kwargs):
      context = super().get_context_data(**kwargs)
      context['conference_list'] = Conference.objects.order_by('abbrv')
      return context


class ConferenceListView(ListView):
    """
    Two-panel conference browser: left sidebar of conference buttons, right
    panel showing the selected conference's teams and current season stats.

    Template: conferences.html
    Context variable: conference_list (auto-named by ListView from the model)

    Queryset optimizations:
      - prefetch_related('teams') prevents an extra query per conference when
        the template loops over conference.teams.all.
      - Prefetch('teams__season_stats', ..., to_attr='_current_stats') loads
        only the current season's stats for every team in a single query.
        This feeds the Team.current_season property so the template can
        access {{ team.current_season.wins }} without any additional DB hits.

    The template filters out conferences with 0 teams (non-D1 or empty
    conferences that came from the API) using {% if conference.teams.count > 0 %}.
    """
    model = Conference
    template_name = 'opencourt/conferences.html'

    def get_queryset(self):
      current_year = date.today().year
      return Conference.objects.prefetch_related(
        'teams',
        Prefetch(
          'teams__season_stats',
          queryset=TeamSeasonStats.objects.filter(season=current_year),
          to_attr='_current_stats'
        )
      ).all()


class RankingsListView(ListView):
    """Renders the rankings page."""

    model = Team
    template_name = 'opencourt/rankings.html'

    def get_queryset(self):
        """Return teams ordered by their latest season performance.

        The queryset fetches each team's most recent season stats (by season)
        and annotates the Team queryset with those values, which keeps the
        template simple and avoids N+1 queries.
        """

        # Build a subquery for the most recent TeamSeasonStats row per team.
        latest_stats = (
            TeamSeasonStats.objects
            .filter(team=OuterRef('pk'))
            .order_by('-season')
        )

        # Small helper to pull a single scalar value from the latest stats row.
        def latest(field_name):
            return Subquery(latest_stats.values(field_name)[:1], output_field=FloatField())

        return (
            Team.objects
            .select_related('conference')
            .prefetch_related('season_stats')
            .annotate(
                latest_wins=latest('wins'),
                latest_losses=latest('losses'),
                latest_off_points=latest('off_points'),
                latest_opp_points=latest('opp_points'),
            )
            .annotate(
                # Point margin is useful for ranking and display purposes.
                latest_point_margin=ExpressionWrapper(
                    F('latest_off_points') - F('latest_opp_points'),
                    output_field=FloatField(),
                )
            )
            .order_by('-latest_wins')
        )

class TeamDetailView(TemplateView):
    """
    Detail page for a single team, showing historical stats, ApexCharts
    visualizations, and a current-season schedule with expandable box scores.

    Template: team_details.html
    URL pattern: /teams/<slug>/  (slug is e.g. "duke-blue-devils")

    Context variables:
      team          — the Team model instance (for name, colors, venue, etc.)
      season_stats  — raw QuerySet list for any template-side iteration
      schedule      — pre-processed list of dicts for the current season game table.
                      Each dict contains:
                        game        — Game object (date, venue, scores, etc.)
                        is_home     — bool, True if this team was home
                        opponent    — Team object for the other side
                        team_points — int, this team's final score
                        opp_points  — int, opponent's final score
                        won         — bool, True if this team won
                        home_stats  — GameTeamStats for the home team (or None)
                        away_stats  — GameTeamStats for the away team (or None)
                      Home/away logic is resolved here so the template doesn't
                      need to branch on home_team vs away_team. Box score stats
                      are prefetched via Prefetch('team_stats') and split into
                      home_stats / away_stats by matching team_id against the
                      Game's home_team_id.
      stat_years    — JSON array of season labels, used as chart x-axis categories
      wins/losses   — JSON arrays of per-season win/loss counts
      win_pct       — JSON array of win percentages (0-100 scale)
      off_rtg       — JSON array of offensive ratings (points per 100 possessions)
      opp_rtg       — JSON array of defensive ratings (points allowed per 100 poss.)
      eff_fg        — JSON array of effective FG% (Four Factors: shooting)
      to_ratio      — JSON array of turnover ratio (Four Factors: ball security)
      oreb_pct      — JSON array of offensive rebound % (Four Factors: rebounding)
      ft_rate       — JSON array of free throw rate (Four Factors: free throws)
      3pt_pct       — JSON array of 3-point shooting percentage
      off_pts       — JSON array of points scored per game
      opp_pts       — JSON array of points allowed per game

    How chart data flows to the frontend:
      1. This view builds Python lists from the season_stats QuerySet
      2. Each list is serialized with json.dumps() and added to context
      3. The template injects them into <script> tags via {{ var|safe }}
      4. ApexCharts reads the arrays directly as JS variables

    Query optimization:
      The games query uses select_related('home_team', 'away_team') to avoid
      N+1 hits when the template renders opponent names, and prefetch_related
      with Prefetch('team_stats') to batch-load all GameTeamStats rows in a
      single query rather than 2 per game row.

    Note: off_to_ratio is multiplied by 100 here because the API stores it
    as a decimal (e.g. 0.18) but we display it as a percentage (18.0).
    off_pts and opp_pts are computed as season totals divided by games
    played to get per-game averages, since the API only provides totals.
    """
    template_name = 'opencourt/team_details.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        team = get_object_or_404(Team, slug=self.kwargs['slug'])
        current_year = date.today().year

        # --- Build the current season game schedule with box scores ---
        # Uses a Q(home_team) | Q(away_team) filter to get all games regardless
        # of which side this team was on. select_related pre-loads both Team FKs
        # in a single JOIN, and Prefetch loads all GameTeamStats rows in one
        # separate query (2 rows per game × ~35 games = ~70 rows total).
        games = Game.objects.filter(
            Q(home_team=team) | Q(away_team=team),
            season=current_year
        ).select_related(
            'home_team', 'away_team'
        ).prefetch_related(
            Prefetch(
                'team_stats',
                queryset=GameTeamStats.objects.select_related('team'),
            )
        ).order_by('-start_date')

        # Pre-process each game into a flat dict so the template can render
        # the schedule table without any home/away conditional logic.
        # The box score accordion needs both teams' stats, so we split the
        # prefetched GameTeamStats into home_stats and away_stats by matching
        # team_id against the Game's home_team FK.
        schedule = []
        for game in games:
            is_home = game.home_team_id == team.id
            opponent = game.away_team if is_home else game.home_team

            # Split the two GameTeamStats rows into home/away for the template.
            # .all() uses the prefetch cache — no additional DB query.
            home_stats = None
            away_stats = None
            for stat in game.team_stats.all():
                if stat.team_id == game.home_team_id:
                    home_stats = stat
                else:
                    away_stats = stat

            schedule.append({
                'game': game,
                'is_home': is_home,
                'opponent': opponent,
                'team_points': game.home_points if is_home else game.away_points,
                'opp_points': game.away_points if is_home else game.home_points,
                'won': game.home_winner if is_home else game.away_winner,
                'home_stats': home_stats,   # GameTeamStats object or None
                'away_stats': away_stats,   # GameTeamStats object or None
            })
        context['schedule'] = schedule

        # Order ascending so chart x-axis runs oldest → newest (left to right)
        season_stats = list(
            TeamSeasonStats.objects.filter(team=team).order_by('season')
        )

        # --- Build JSON-serializable lists for each chart series ---
        # Each list is parallel to season_labels: index 0 = oldest season.
        # None values are preserved so ApexCharts can render gaps for missing data.
        season_labels = [f'{s.season}' for s in season_stats]

        # Basic record
        wins       = [int(s.wins) if s.wins is not None else None for s in season_stats]
        losses     = [int(s.losses) if s.losses is not None else None for s in season_stats]
        win_pct    = [round(s.win_pct, 1) if s.win_pct else None for s in season_stats]

        # Efficiency ratings (tempo-independent, best for cross-team comparison)
        off_rating = [round(s.off_rating, 1) if s.off_rating else None for s in season_stats]
        opp_rating = [round(s.opp_rating, 1) if s.opp_rating else None for s in season_stats]

        # Four Factors — the core predictive metrics in basketball analytics
        off_eff_fg_pct = [round(s.off_eff_fg_pct, 1) if s.off_eff_fg_pct else None for s in season_stats]
        off_to_ratio   = [round(s.off_turnover_ratio*100, 1) if s.off_turnover_ratio else None for s in season_stats]
        off_oreb_pct   = [round(s.off_oreb_pct, 1) if s.off_oreb_pct else None for s in season_stats]
        off_ft_rate    = [round(s.off_ft_rate, 1)  if s.off_ft_rate else None for s in season_stats]

        # Additional shooting & scoring (extend as the team view is built out)
        off_3pt_pct = [round(s.off_3pt_pct, 1) if s.off_3pt_pct else None for s in season_stats]
        off_pts     = [round(s.off_points / s.games, 1) if s.off_points and s.games else None for s in season_stats]
        opp_pts     = [round(s.opp_points / s.games, 1) if s.opp_points and s.games else None for s in season_stats]

        # --- Pack context ---
        # The template references these keys directly in {{ var|safe }} tags
        # inside ApexCharts config objects. Key names are kept short for
        # readability in the template JS.
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

        context['three_pt_pct'] = json.dumps(off_3pt_pct)
        context['off_pts'] = json.dumps(off_pts)
        context['opp_pts'] = json.dumps(opp_pts)
        return context


class UpcomingView(TemplateView):
    template_name = 'opencourt/head_head.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        games = (
            Game.objects
            .filter(status="scheduled")
            .select_related('home_team', 'away_team')
            .order_by('start_date')
        )

        context['games'] = games
        return context